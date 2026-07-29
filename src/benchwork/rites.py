"""Versioned Rites for reproducible Benchwork workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .athanor import AthanorError


DEFAULT_RITES: dict[str, dict[str, Any]] = {
    "computational-study@0.1.0": {
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
        return rites

    def get(self, rite_id: str) -> dict[str, Any]:
        try:
            return self.rites()[rite_id]
        except KeyError as error:
            raise AthanorError(f"unknown Rite: {rite_id}") from error
