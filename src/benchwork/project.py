"""Project-root discovery and explicit local Program context."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .errors import ProjectContextError
from .schema_validation import validate_instance

PROJECT_DIRECTORY = ".benchwork"
PROJECT_MANIFEST = "benchwork.toml"
CONTEXT_SCHEMA_VERSION = "project-context/1.0"


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate project context key: {key}")
        value[key] = item
    return value


def discover_project_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if (directory / PROJECT_DIRECTORY).is_dir() or (
            directory / PROJECT_MANIFEST
        ).is_file():
            return directory
    raise ProjectContextError(
        "PROJECT_NOT_FOUND",
        f"no Benchwork project found from {candidate}",
        exit_code=6,
        details={"start": str(candidate)},
    )


class ProjectContext:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.path = self.root / PROJECT_DIRECTORY / "context.json"

    def active_program(self) -> str | None:
        if not self.path.exists():
            return None
        try:
            value = json.loads(
                self.path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
            )
        except (OSError, ValueError) as error:
            raise ProjectContextError(
                "INVALID_PROJECT_CONTEXT",
                f"cannot read project context: {self.path}",
                details={"path": str(self.path)},
            ) from error
        if not isinstance(value, dict):
            raise ProjectContextError(
                "INVALID_PROJECT_CONTEXT",
                f"invalid project context: {self.path}",
                details={"path": str(self.path)},
            )
        try:
            validate_instance("project-context-1.0.json", value)
        except ValueError as error:
            raise ProjectContextError(
                "INVALID_PROJECT_CONTEXT",
                f"invalid project context: {self.path}",
                details={"path": str(self.path)},
            ) from error
        return value["active_program_id"]

    def use_program(self, program_id: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "schema_version": CONTEXT_SCHEMA_VERSION,
            "active_program_id": program_id,
        }
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=".context.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(document, handle, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary_path.unlink(missing_ok=True)
