"""Immutable, Program-scoped Research Snapshots."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from .athanor import AthanorError, content_sigil
from .schema_validation import validate_instance


OBJECT_TYPES = {
    "programs": "research-program",
    "evidence": "evidence",
    "claims": "claim",
    "hypotheses": "hypothesis",
    "protocols": "protocol",
    "workings": "working",
    "experiments": "experiment",
    "runs": "run",
    "result_bundles": "result-bundle",
    "assessments": "assessment",
    "decisions": "decision",
    "artifacts": "artifact",
    "issues": "issue",
    "deviations": "deviation",
    "reproduction_records": "reproduction-record",
    "review_requests": "review-request",
    "review_artifacts": "review-artifact",
}


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


class SnapshotStore:
    """Creates and verifies immutable snapshots outside the canonical ledger."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / ".benchwork" / "snapshots"

    @staticmethod
    def inventory(program_id: str, state: dict[str, Any]) -> list[dict[str, str]]:
        if program_id not in state["programs"]:
            raise AthanorError(f"unknown Research Program: {program_id}")
        objects: list[dict[str, str]] = []
        for collection_name, object_type in OBJECT_TYPES.items():
            collection = state.get(collection_name, {})
            for object_id, record in collection.items():
                belongs = (
                    object_id == program_id
                    if collection_name == "programs"
                    else record.get("program_id") == program_id
                )
                if belongs:
                    objects.append(
                        {
                            "object_id": object_id,
                            "object_type": object_type,
                            "object_sigil": content_sigil(record),
                        }
                    )
        return sorted(
            objects,
            key=lambda item: (item["object_type"], item["object_id"]),
        )

    def create(
        self,
        program_id: str,
        state: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], str]:
        if not events:
            raise AthanorError("Research Snapshot requires a non-empty Chronicle")
        snapshot = {
            "schema_version": "research-snapshot/1.0",
            "snapshot_id": f"SS-{uuid4().hex[:12].upper()}",
            "program_id": program_id,
            "chronicle_head_sigil": events[-1]["receipt"]["receipt_sigil"],
            "objects": self.inventory(program_id, state),
            "created_at": events[-1]["occurred_at"],
        }
        validate_instance("research-snapshot-1.0.json", snapshot)
        snapshot_sigil = content_sigil(snapshot)
        self.path.mkdir(parents=True, exist_ok=True)
        target = self.path / f"{snapshot['snapshot_id']}.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(_json(snapshot), encoding="utf-8")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        return snapshot, snapshot_sigil

    def get(
        self,
        snapshot_id: str,
        expected_sigil: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        path = self.path / f"{snapshot_id}.json"
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise AthanorError(f"unknown Research Snapshot: {snapshot_id}") from error
        except json.JSONDecodeError as error:
            raise AthanorError(f"invalid Research Snapshot: {snapshot_id}") from error
        if not isinstance(snapshot, dict):
            raise AthanorError(f"Research Snapshot must be an object: {snapshot_id}")
        validate_instance("research-snapshot-1.0.json", snapshot)
        if snapshot["snapshot_id"] != snapshot_id:
            raise AthanorError(f"Research Snapshot identity mismatch: {snapshot_id}")
        snapshot_sigil = content_sigil(snapshot)
        if expected_sigil is not None and snapshot_sigil != expected_sigil:
            raise AthanorError(f"Research Snapshot Sigil mismatch: {snapshot_id}")
        return snapshot, snapshot_sigil

    def require_fresh(
        self,
        snapshot: dict[str, Any],
        state: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> None:
        ancestor_sigils = {
            event["receipt"]["receipt_sigil"]
            for event in events
        }
        if snapshot["chronicle_head_sigil"] not in ancestor_sigils:
            raise AthanorError("Research Snapshot Chronicle head is not an ancestor")
        current = self.inventory(snapshot["program_id"], state)
        if current != snapshot["objects"]:
            raise AthanorError("STALE_TASK: Research Snapshot no longer matches canonical state")
