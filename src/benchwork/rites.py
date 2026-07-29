"""Versioned Rites for reproducible Benchwork workflows."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .athanor import AthanorError, _exclusive_lock, canonical_json, content_sigil
from .grimoire import GrimoireRegistry
from .schema_validation import validate_instance


DEFAULT_RITES: dict[str, dict[str, Any]] = {
    "computational-study@0.1.0": {
        "schema_version": "rite/1.0",
        "rite_id": "computational-study@0.1.0",
        "stages": [
            {"name": "IMPLEMENTATION", "exit_artifact": "implementation"},
            {"name": "PILOT", "exit_artifact": "pilot-result"},
            {"name": "RUN", "exit_artifact": "run-record"},
            {"name": "ANALYSIS", "exit_artifact": "result-bundle"},
            {"name": "REVIEW", "exit_artifact": "assessment"},
            {"name": "DECISION", "exit_artifact": "decision"}
        ],
        "description": "A protocol-bound computational research study.",
    },
    "computational-study@0.2.0": {
        "schema_version": "rite/1.1",
        "rite_id": "computational-study@0.2.0",
        "stages": [
            {
                "name": "IMPLEMENTATION",
                "exit_contract": {
                    "event_type": "artifact.registered",
                    "object_type": "artifact",
                    "kind": "implementation",
                    "same_program": True,
                    "same_protocol": True,
                },
            },
            {
                "name": "PILOT",
                "exit_contract": {
                    "event_type": "run.recorded",
                    "object_type": "run",
                    "phase": "PILOT",
                    "status": "COMPLETED",
                    "same_program": True,
                    "same_protocol": True,
                },
            },
            {
                "name": "ANALYSIS",
                "exit_contract": {
                    "event_type": "analysis.computed",
                    "object_type": "result-bundle",
                    "same_program": True,
                    "same_protocol": True,
                },
            },
            {
                "name": "REVIEW",
                "exit_contract": {
                    "event_type": "assessment.recorded",
                    "object_type": "assessment",
                    "same_program": True,
                    "same_protocol": True,
                },
            },
            {
                "name": "DECISION",
                "exit_contract": {
                    "event_type": "decision.sealed",
                    "object_type": "decision",
                    "same_program": True,
                    "same_protocol": True,
                },
            },
            {"name": "COMPLETED"},
        ],
        "description": "Legacy per-Run Pilot exit retained for replay compatibility.",
    },
    "computational-study@0.2.1": {
        "schema_version": "rite/1.1",
        "rite_id": "computational-study@0.2.1",
        "stages": [
            {
                "name": "IMPLEMENTATION",
                "exit_contract": {
                    "event_type": "artifact.registered",
                    "object_type": "artifact",
                    "kind": "implementation",
                    "same_program": True,
                    "same_protocol": True,
                },
            },
            {
                "name": "PILOT",
                "exit_contract": {
                    "event_type": "experiment.pilot_completed",
                    "object_type": "experiment",
                    "same_program": True,
                    "same_protocol": True,
                },
            },
            {
                "name": "ANALYSIS",
                "exit_contract": {
                    "event_type": "analysis.computed",
                    "object_type": "result-bundle",
                    "same_program": True,
                    "same_protocol": True,
                },
            },
            {
                "name": "REVIEW",
                "exit_contract": {
                    "event_type": "assessment.recorded",
                    "object_type": "assessment",
                    "same_program": True,
                    "same_protocol": True,
                },
            },
            {
                "name": "DECISION",
                "exit_contract": {
                    "event_type": "decision.sealed",
                    "object_type": "decision",
                    "same_program": True,
                    "same_protocol": True,
                },
            },
            {"name": "COMPLETED"},
        ],
        "description": "A Working-bound canonical-event computational research study.",
    }
}


class RiteRegistry:
    """Project-local registry of pinned, inspectable workflow definitions."""

    def __init__(self, root: Path) -> None:
        self.path = root / ".benchwork" / "rites.json"
        self.lock_path = root / ".benchwork" / "rites.lock"
        self.grimoire_registry = GrimoireRegistry(root)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(self.lock_path):
            if not self.path.exists():
                temporary = self.path.with_suffix(".json.tmp")
                temporary.write_text(
                    canonical_json({"schema_version": "rite-registry/1.1", "rites": DEFAULT_RITES}) + "\n",
                    encoding="utf-8",
                )
                with temporary.open("rb") as handle:
                    os.fsync(handle.fileno())
                os.replace(temporary, self.path)
                directory = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            else:
                try:
                    registry = json.loads(self.path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as error:
                    raise AthanorError("invalid Rite Registry") from error
                if registry.get("schema_version") == "rite-registry/1.0":
                    if not isinstance(registry.get("rites"), dict):
                        raise AthanorError("Rite Registry is missing rites")
                    normalized_legacy: dict[str, dict[str, Any]] = {}
                    for rite_id, raw_definition in registry["rites"].items():
                        if not isinstance(raw_definition, dict):
                            raise AthanorError(f"invalid Rite definition: {rite_id}")
                        definition = raw_definition.copy()
                        definition.setdefault("schema_version", "rite/1.0")
                        definition.setdefault("rite_id", rite_id)
                        normalized_legacy[rite_id] = definition
                    registry["rites"] = normalized_legacy
                    validate_instance("rite-registry-1.0.json", registry)
                    registry["schema_version"] = "rite-registry/1.1"
                    for rite_id, definition in DEFAULT_RITES.items():
                        registry["rites"].setdefault(rite_id, definition)
                    validate_instance("rite-registry-1.1.json", registry)
                    temporary = self.path.with_suffix(".json.tmp")
                    temporary.write_text(
                        canonical_json(registry) + "\n",
                        encoding="utf-8",
                    )
                    with temporary.open("rb") as handle:
                        os.fsync(handle.fileno())
                    os.replace(temporary, self.path)
                    directory = os.open(self.path.parent, os.O_RDONLY)
                    try:
                        os.fsync(directory)
                    finally:
                        os.close(directory)
        self.grimoire_registry.initialize()

    def rites(self) -> dict[str, dict[str, Any]]:
        self.initialize()
        with _exclusive_lock(self.lock_path):
            try:
                registry = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise AthanorError("invalid Rite Registry") from error
        registry_version = registry.get("schema_version")
        if registry_version not in {"rite-registry/1.0", "rite-registry/1.1"}:
            raise AthanorError("unsupported Rite Registry version")
        rites = registry.get("rites")
        if not isinstance(rites, dict):
            raise AthanorError("Rite Registry is missing rites")
        normalized: dict[str, dict[str, Any]] = {}
        for rite_id, raw_definition in rites.items():
            if not isinstance(raw_definition, dict):
                raise AthanorError(f"invalid Rite definition: {rite_id}")
            definition = raw_definition.copy()
            definition.setdefault("schema_version", "rite/1.0")
            definition.setdefault("rite_id", rite_id)
            schema_name = (
                "rite-definition-1.1.json"
                if definition["schema_version"] == "rite/1.1"
                else "rite-definition-1.0.json"
            )
            validate_instance(schema_name, definition)
            stages = [stage["name"] for stage in definition["stages"]]
            if len(stages) != len(set(stages)):
                raise AthanorError(f"Rite has duplicate stage names: {rite_id}")
            if definition["schema_version"] == "rite/1.1" and (
                any("exit_contract" not in stage for stage in definition["stages"][:-1])
                or "exit_contract" in definition["stages"][-1]
            ):
                raise AthanorError(
                    f"Rite v1.1 requires exits on non-terminal stages only: {rite_id}"
                )
            normalized[rite_id] = definition
        validate_instance(
            "rite-registry-1.1.json"
            if registry_version == "rite-registry/1.1"
            else "rite-registry-1.0.json",
            {"schema_version": registry_version, "rites": normalized},
        )
        for rite_id, entry in self.grimoire_registry.rite_entries().items():
            if rite_id in normalized:
                raise AthanorError(f"installed Grimoire overrides a built-in Rite: {rite_id}")
            if entry["sigil"] != content_sigil(entry["definition"]):
                raise AthanorError(f"installed Grimoire Rite Sigil mismatch: {rite_id}")
            normalized[rite_id] = entry["definition"]
        return normalized

    def verify_existing(self) -> dict[str, dict[str, Any]]:
        """Validate stored Rites and extensions without initializing either Registry."""
        if not self.path.is_file():
            raise AthanorError("Rite Registry is missing")
        try:
            registry = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AthanorError("invalid Rite Registry") from error
        registry_version = registry.get("schema_version")
        if registry_version == "rite-registry/1.0":
            raise AthanorError(
                "MIGRATION_REQUIRED: Rite Registry v1.0 must be migrated"
            )
        if registry_version != "rite-registry/1.1":
            raise AthanorError("unsupported Rite Registry version")
        validate_instance("rite-registry-1.1.json", registry)
        rites = registry["rites"]
        missing = sorted(set(DEFAULT_RITES) - set(rites))
        if missing:
            raise AthanorError(
                "Rite Registry is missing default Rites: " + ", ".join(missing)
            )
        verified: dict[str, dict[str, Any]] = {}
        for rite_id, definition in rites.items():
            if definition["rite_id"] != rite_id:
                raise AthanorError(f"Rite Registry key does not match Rite ID: {rite_id}")
            schema_name = (
                "rite-definition-1.1.json"
                if definition["schema_version"] == "rite/1.1"
                else "rite-definition-1.0.json"
            )
            validate_instance(schema_name, definition)
            stages = [stage["name"] for stage in definition["stages"]]
            if len(stages) != len(set(stages)):
                raise AthanorError(f"Rite has duplicate stage names: {rite_id}")
            if definition["schema_version"] == "rite/1.1" and (
                any("exit_contract" not in stage for stage in definition["stages"][:-1])
                or "exit_contract" in definition["stages"][-1]
            ):
                raise AthanorError(
                    f"Rite v1.1 requires exits on non-terminal stages only: {rite_id}"
                )
            verified[rite_id] = definition
        for rite_id, entry in self.grimoire_registry.verify_existing_rite_entries().items():
            if rite_id in verified:
                raise AthanorError(f"installed Grimoire overrides a built-in Rite: {rite_id}")
            if entry["sigil"] != content_sigil(entry["definition"]):
                raise AthanorError(f"installed Grimoire Rite Sigil mismatch: {rite_id}")
            verified[rite_id] = entry["definition"]
        return verified

    def install_grimoire(self, source: Path) -> tuple[str, str, bool]:
        return self.grimoire_registry.install(source, set(DEFAULT_RITES))

    def grimoires(self) -> dict[str, dict[str, Any]]:
        return self.grimoire_registry.grimoires()

    def get(self, rite_id: str) -> dict[str, Any]:
        try:
            return self.rites()[rite_id]
        except KeyError as error:
            raise AthanorError(f"unknown Rite: {rite_id}") from error
