"""Versioned Rites for reproducible Benchwork workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .athanor import AthanorError, content_sigil
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
    }
}


class RiteRegistry:
    """Project-local registry of pinned, inspectable workflow definitions."""

    def __init__(self, root: Path) -> None:
        self.path = root / ".benchwork" / "rites.json"
        self.grimoire_registry = GrimoireRegistry(root)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(
                json.dumps(
                    {"schema_version": "rite-registry/1.0", "rites": DEFAULT_RITES},
                    ensure_ascii=True,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        self.grimoire_registry.initialize()

    def rites(self) -> dict[str, dict[str, Any]]:
        self.initialize()
        try:
            registry = json.loads(self.path.read_text())
        except json.JSONDecodeError as error:
            raise AthanorError("invalid Rite Registry") from error
        if registry.get("schema_version") != "rite-registry/1.0":
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
            validate_instance("rite-definition-1.0.json", definition)
            stages = [stage["name"] for stage in definition["stages"]]
            if len(stages) != len(set(stages)):
                raise AthanorError(f"Rite has duplicate stage names: {rite_id}")
            normalized[rite_id] = definition
        validate_instance(
            "rite-registry-1.0.json",
            {"schema_version": "rite-registry/1.0", "rites": normalized},
        )
        for rite_id, entry in self.grimoire_registry.rite_entries().items():
            if rite_id in normalized:
                raise AthanorError(f"installed Grimoire overrides a built-in Rite: {rite_id}")
            if entry["sigil"] != content_sigil(entry["definition"]):
                raise AthanorError(f"installed Grimoire Rite Sigil mismatch: {rite_id}")
            normalized[rite_id] = entry["definition"]
        return normalized

    def install_grimoire(self, source: Path) -> tuple[str, str, bool]:
        return self.grimoire_registry.install(source, set(DEFAULT_RITES))

    def grimoires(self) -> dict[str, dict[str, Any]]:
        return self.grimoire_registry.grimoires()

    def get(self, rite_id: str) -> dict[str, Any]:
        try:
            return self.rites()[rite_id]
        except KeyError as error:
            raise AthanorError(f"unknown Rite: {rite_id}") from error
