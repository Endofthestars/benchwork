"""Open Grimoire: pinned, data-only extension manifests."""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

from .athanor import AthanorError, _exclusive_lock, canonical_json, content_sigil
from .schema_validation import validate_instance


BENCHWORK_API = "0.1"
MAX_EXTENSION_JSON_BYTES = 1_000_000


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AthanorError(f"duplicate JSON key in Grimoire content: {key}")
        result[key] = value
    return result


def _load_extension_json(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_EXTENSION_JSON_BYTES:
            raise AthanorError(f"{label} exceeds the 1 MB data-only limit: {path}")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except AthanorError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AthanorError(f"cannot read {label}: {path}") from error
    if not isinstance(value, dict):
        raise AthanorError(f"{label} must be a JSON object: {path}")
    return value


def load_rite_definition(path: Path) -> dict[str, Any]:
    definition = _load_extension_json(path, "Grimoire Rite")
    schema_name = (
        "rite-definition-1.1.json"
        if definition.get("schema_version") == "rite/1.1"
        else "rite-definition-1.0.json"
    )
    validate_instance(schema_name, definition)
    stages = [stage["name"] for stage in definition["stages"]]
    if len(stages) != len(set(stages)):
        raise AthanorError(f"Grimoire Rite has duplicate stage names: {definition['rite_id']}")
    if definition["schema_version"] == "rite/1.1" and (
        any("exit_contract" not in stage for stage in definition["stages"][:-1])
        or "exit_contract" in definition["stages"][-1]
    ):
        raise AthanorError(
            "Grimoire Rite v1.1 requires exits on non-terminal stages only: "
            f"{definition['rite_id']}"
        )
    return definition


def rite_definition_sigil(path: Path) -> str:
    return content_sigil(load_rite_definition(path))


class GrimoireRegistry:
    """Project-local copies of verified Grimoire manifests and Rite definitions."""

    def __init__(self, root: Path) -> None:
        base = root / ".benchwork"
        self.path = base / "grimoires.json"
        self.lock_path = base / "grimoires.lock"

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(self.lock_path):
            if not self.path.exists():
                self._write({"schema_version": "grimoire-registry/1.0", "grimoires": {}})

    def _write(self, registry: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(canonical_json(registry) + "\n", encoding="utf-8")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)
        directory = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def _read_unlocked(self) -> dict[str, Any]:
        try:
            registry = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AthanorError("invalid Grimoire Registry") from error
        validate_instance("grimoire-registry-1.0.json", registry)
        occupied: set[str] = set()
        for grimoire_ref, record in registry["grimoires"].items():
            manifest = record["manifest"]
            expected_ref = f"{manifest['grimoire_id']}@{manifest['version']}"
            if grimoire_ref != expected_ref or record["manifest_sigil"] != content_sigil(manifest):
                raise AthanorError(f"invalid installed Grimoire identity: {grimoire_ref}")
            declared = {item["rite_id"]: item for item in manifest["rites"]}
            if set(declared) != set(record["rites"]):
                raise AthanorError(f"installed Grimoire Rite set does not match manifest: {grimoire_ref}")
            for rite_id, rite in record["rites"].items():
                definition = rite["definition"]
                stages = [stage["name"] for stage in definition["stages"]]
                if (
                    definition["rite_id"] != rite_id
                    or rite["sigil"] != declared[rite_id]["sigil"]
                    or rite["sigil"] != content_sigil(definition)
                    or len(stages) != len(set(stages))
                ):
                    raise AthanorError(f"invalid installed Grimoire Rite: {rite_id}")
                if rite_id in occupied:
                    raise AthanorError(f"Rite collision between installed Grimoires: {rite_id}")
                occupied.add(rite_id)
        return registry

    def grimoires(self) -> dict[str, dict[str, Any]]:
        self.initialize()
        with _exclusive_lock(self.lock_path):
            return self._read_unlocked()["grimoires"]

    def rite_entries(self) -> dict[str, dict[str, Any]]:
        entries: dict[str, dict[str, Any]] = {}
        for grimoire_ref, record in self.grimoires().items():
            for rite_id, rite in record["rites"].items():
                if rite_id in entries:
                    raise AthanorError(f"Rite collision between installed Grimoires: {rite_id}")
                entries[rite_id] = {
                    "definition": rite["definition"],
                    "sigil": rite["sigil"],
                    "grimoire": grimoire_ref,
                    "manifest_sigil": record["manifest_sigil"],
                }
        return entries

    def install(
        self, source: Path, reserved_rite_ids: set[str] | None = None
    ) -> tuple[str, str, bool]:
        source_root = source.resolve()
        manifest_path = source_root / "grimoire.json"
        manifest = _load_extension_json(manifest_path, "Grimoire manifest")
        validate_instance("grimoire-manifest-1.0.json", manifest)
        if manifest["benchwork_api"] != BENCHWORK_API:
            raise AthanorError(
                f"Grimoire requires Benchwork API {manifest['benchwork_api']}; supported API is {BENCHWORK_API}"
            )

        grimoire_ref = f"{manifest['grimoire_id']}@{manifest['version']}"
        installed_rites: dict[str, dict[str, Any]] = {}
        seen_paths: set[str] = set()
        for item in manifest["rites"]:
            rite_id = item["rite_id"]
            relative = PurePosixPath(item["path"])
            if relative.is_absolute() or ".." in relative.parts or item["path"] in seen_paths:
                raise AthanorError(f"unsafe or duplicate Grimoire Rite path: {item['path']}")
            seen_paths.add(item["path"])
            rite_path = source_root.joinpath(*relative.parts).resolve()
            try:
                rite_path.relative_to(source_root)
            except ValueError as error:
                raise AthanorError(f"Grimoire Rite escapes its source directory: {item['path']}") from error
            if not rite_path.is_file():
                raise AthanorError(f"Grimoire Rite is not a regular file: {item['path']}")
            definition = load_rite_definition(rite_path)
            if definition["rite_id"] != rite_id:
                raise AthanorError(f"Grimoire Rite ID does not match manifest: {rite_id}")
            actual_sigil = content_sigil(definition)
            if actual_sigil != item["sigil"]:
                raise AthanorError(f"Grimoire Rite Sigil mismatch: {rite_id}")
            if rite_id in installed_rites:
                raise AthanorError(f"duplicate Rite in Grimoire manifest: {rite_id}")
            installed_rites[rite_id] = {"definition": definition, "sigil": actual_sigil}

        reserved = reserved_rite_ids or set()
        collision = reserved.intersection(installed_rites)
        if collision:
            raise AthanorError(f"Grimoire cannot override reserved Rite: {sorted(collision)[0]}")
        record: dict[str, Any] = {
            "manifest": manifest,
            "manifest_sigil": content_sigil(manifest),
            "rites": installed_rites,
        }

        self.initialize()
        with _exclusive_lock(self.lock_path):
            registry = self._read_unlocked()
            existing = registry["grimoires"].get(grimoire_ref)
            if existing is not None:
                if existing == record:
                    return grimoire_ref, record["manifest_sigil"], False
                raise AthanorError(f"installed Grimoire version has different content: {grimoire_ref}")
            occupied = {
                rite_id
                for installed in registry["grimoires"].values()
                for rite_id in installed["rites"]
            }
            collision = occupied.intersection(installed_rites)
            if collision:
                raise AthanorError(f"Rite already provided by another Grimoire: {sorted(collision)[0]}")
            registry["grimoires"][grimoire_ref] = record
            validate_instance("grimoire-registry-1.0.json", registry)
            self._write(registry)
        return grimoire_ref, record["manifest_sigil"], True
