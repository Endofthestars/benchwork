"""Stable command-line error contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CommandError:
    code: str
    message: str
    exit_code: int
    details: dict[str, Any] = field(default_factory=dict)

    def envelope(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
        }


class ProjectContextError(ValueError):
    """A stable failure raised while resolving local project context."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        exit_code: int = 2,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code
        self.details = details or {}


def classify_error(error: ValueError) -> CommandError:
    if isinstance(error, ProjectContextError):
        return CommandError(
            error.code,
            str(error),
            error.exit_code,
            error.details,
        )

    message = str(error)
    lowered = message.lower()
    if "stale_task" in lowered or "snapshot no longer matches" in lowered:
        return CommandError("STALE_TASK", message, 5)
    if (
        "unsupported" in lowered
        and ("version" in lowered or "registry" in lowered or "chronicle" in lowered)
    ) or "requires explicit migration" in lowered:
        return CommandError("UNSUPPORTED_VERSION", message, 8)
    if any(
        marker in lowered
        for marker in (
            "chronicle",
            "receipt sigil",
            "event body sigil",
            "broken chain",
            "head mismatch",
            "truncation",
            "rewritten committed prefix",
        )
    ):
        return CommandError("INTEGRITY_FAILURE", message, 4)
    if lowered.startswith(("unknown ", "no working", "cannot read file")):
        return CommandError("NOT_FOUND", message, 6)
    if any(marker in lowered for marker in ("already exists", "duplicate ", "collision")):
        return CommandError("CONFLICT", message, 7)
    return CommandError("VALIDATION_REJECTED", message, 2)
