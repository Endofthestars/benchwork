"""Athanor: deterministic canonical transitions for Benchwork."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterator
from uuid import uuid4

_fcntl: Any = None
_msvcrt: Any = None
try:
    import fcntl as _fcntl_module
except ImportError:  # pragma: no cover - Windows
    import msvcrt as _msvcrt_module

    _msvcrt = _msvcrt_module
else:
    _fcntl = _fcntl_module

fcntl: Any = _fcntl
msvcrt: Any = _msvcrt


class AthanorError(ValueError):
    """Raised when a proposed state transition violates an Athanor invariant."""


IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_]*-[A-Z0-9][A-Z0-9_-]*$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SIGIL = re.compile(r"^sha256:[a-f0-9]{64}$")
EVIDENCE_RELATIONS = {"SUPPORTS", "CONTRADICTS", "LIMITS", "REPRODUCES", "UNRESOLVED"}
EVIDENCE_VERIFICATION_KEYS = {
    "source_resolved",
    "content_inspected",
}
ISSUE_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
DEVIATION_KINDS = {"PLANNED", "UNPLANNED"}
DEVIATION_IMPACTS = {"NONE", "MINOR", "MAJOR", "INVALIDATING"}
PROGRAM_OBJECT_COLLECTIONS = (
    "evidence",
    "claims",
    "hypotheses",
    "protocols",
    "workings",
    "experiments",
    "runs",
    "result_bundles",
    "assessments",
    "decisions",
    "artifacts",
    "issues",
    "deviations",
    "reproduction_records",
)
PROGRAM_STATUS_ORDER = {
    status: index
    for index, status in enumerate(
        (
            "IDEA",
            "EVIDENCE_RECORDED",
            "CLAIMS_REGISTERED",
            "HYPOTHESES_REGISTERED",
            "RQ_FROZEN",
            "DESIGN_FROZEN",
            "IMPLEMENTED",
            "PILOTED",
            "RUNNING",
            "RESULT_READY",
            "EVALUATED",
            "CLOSED",
        )
    )
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_sigil(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _advance_program(program: dict[str, Any], status: str) -> None:
    if PROGRAM_STATUS_ORDER[status] > PROGRAM_STATUS_ORDER[program["status"]]:
        program["status"] = status


def _object_program_id(
    object_id: str,
    programs: dict[str, dict[str, Any]],
    *collections: dict[str, dict[str, Any]],
) -> str | None:
    if object_id in programs:
        return object_id
    for collection in collections:
        record = collection.get(object_id)
        if record is not None:
            return record.get("program_id")
    return None


def _state_object_program_id(state: dict[str, Any], object_id: str) -> str | None:
    return _object_program_id(
        object_id,
        state["programs"],
        *(state[name] for name in PROGRAM_OBJECT_COLLECTIONS),
    )


def _record_protocol_id(
    object_id: str,
    protocols: dict[str, dict[str, Any]],
    workings: dict[str, dict[str, Any]],
    experiments: dict[str, dict[str, Any]],
    runs: dict[str, dict[str, Any]],
    result_bundles: dict[str, dict[str, Any]],
    assessments: dict[str, dict[str, Any]],
    artifacts: dict[str, dict[str, Any]],
) -> str | None:
    if object_id in protocols:
        return object_id
    for collection in (workings, experiments, runs, result_bundles, assessments):
        record = collection.get(object_id)
        if record is not None:
            return record.get("protocol_id")
    artifact = artifacts.get(object_id)
    if artifact is not None:
        return _record_protocol_id(
            artifact["producer_id"],
            protocols,
            workings,
            experiments,
            runs,
            result_bundles,
            assessments,
            artifacts,
        )
    return None


def _advance_workings_for_event(
    event: dict[str, Any],
    workings: dict[str, dict[str, Any]],
    protocols: dict[str, dict[str, Any]],
    experiments: dict[str, dict[str, Any]],
    runs: dict[str, dict[str, Any]],
    result_bundles: dict[str, dict[str, Any]],
    assessments: dict[str, dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    artifacts: dict[str, dict[str, Any]],
) -> None:
    payload = event["payload"]
    event_type = event["type"]
    object_id = event["object_id"]
    object_types = {
        "artifact.registered": "artifact",
        "run.recorded": "run",
        "analysis.computed": "result-bundle",
        "assessment.recorded": "assessment",
        "decision.sealed": "decision",
    }
    object_type = object_types.get(event_type)
    if object_type is None:
        return

    record_collections = {
        "artifact": artifacts,
        "run": runs,
        "result-bundle": result_bundles,
        "assessment": assessments,
        "decision": decisions,
    }
    record = record_collections[object_type].get(object_id)
    if record is None:
        return
    program_id = record["program_id"]
    protocol_ids: set[str] = set()
    direct_protocol = record.get("protocol_id")
    if direct_protocol is not None:
        protocol_ids.add(direct_protocol)
    if object_type == "artifact":
        inferred = _record_protocol_id(
            record["producer_id"],
            protocols,
            workings,
            experiments,
            runs,
            result_bundles,
            assessments,
            artifacts,
        )
        if inferred is not None:
            protocol_ids.add(inferred)
    elif object_type == "decision":
        protocol_ids.update(
            assessments[assessment_id]["protocol_id"]
            for assessment_id in record["assessment_ids"]
        )

    for working in workings.values():
        if working["schema_version"] != "working/1.1" or working["status"] != "ACTIVE":
            continue
        stages = working["rite"]["stages"]
        names = [stage["name"] for stage in stages]
        index = names.index(working["stage"])
        contract = stages[index].get("exit_contract")
        if (
            contract is None
            or contract["event_type"] != event_type
            or contract["object_type"] != object_type
            or working["program_id"] != program_id
            or working["protocol_id"] not in protocol_ids
            or ("kind" in contract and payload.get("kind") != contract["kind"])
            or ("phase" in contract and payload.get("phase") != contract["phase"])
            or ("status" in contract and payload.get("status") != contract["status"])
        ):
            continue
        next_stage = stages[index + 1]["name"]
        working["stage"] = next_stage
        working["status"] = "COMPLETED" if index + 1 == len(stages) - 1 else "ACTIVE"
        working["history"].append(
            {
                "stage": next_stage,
                "at": event["occurred_at"],
                "reason": f"exit contract satisfied by {event_type}",
                "canonical_event_id": event["event_id"],
                "object_id": object_id,
            }
        )


@contextmanager
def _exclusive_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        else:  # pragma: no cover - Windows
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            else:  # pragma: no cover - Windows
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


@dataclass(frozen=True)
class Receipt:
    schema_version: str
    receipt_id: str
    event_id: str
    event_body_sigil: str
    previous_receipt_sigil: str | None
    accepted_at: str
    receipt_sigil: str

    def as_dict(self) -> dict[str, str | None]:
        return self.__dict__.copy()

    @property
    def sigil(self) -> str:
        """Compatibility alias for callers written against Receipt v1.0."""
        return self.receipt_sigil

    @property
    def previous_sigil(self) -> str | None:
        """Compatibility alias for callers written against Receipt v1.0."""
        return self.previous_receipt_sigil


TransitionBuilder = Callable[[list[dict[str, Any]]], tuple[str, str, dict[str, Any]]]
ProjectionBuilder = Callable[[list[dict[str, Any]]], dict[str, Any]]

LOCAL_ACTOR = {
    "actor_id": "local-user",
    "actor_type": "human",
    "host": "cli",
    "authenticated_by": "local-session",
}


class Chronicle:
    """A transactional JSONL event chain with an independently checked head."""

    def __init__(self, root: Path) -> None:
        base = root / ".benchwork"
        self.path = base / "chronicle.jsonl"
        self.head_path = base / "chronicle.head"
        self.lock_path = base / "chronicle.lock"

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(self.lock_path):
            self.path.touch(exist_ok=True)
            if not self.head_path.exists():
                if self.path.stat().st_size:
                    raise AthanorError("Chronicle head is missing for a non-empty ledger")
                self._write_head(0, None)

    def _write_head(self, count: int, sigil: str | None) -> None:
        from .schema_validation import validate_instance

        head = {
            "schema_version": "chronicle-head/1.1",
            "event_count": count,
            "terminal_receipt_sigil": sigil,
        }
        validate_instance("chronicle-head-1.1.json", head)
        temporary = self.head_path.with_suffix(".head.tmp")
        temporary.write_text(canonical_json(head) + "\n", encoding="utf-8")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, self.head_path)
        directory = os.open(self.head_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    @staticmethod
    def _decode_event(line: str, line_number: int) -> dict[str, Any]:
        def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise AthanorError(
                        f"duplicate JSON key at Chronicle line {line_number}: {key}"
                    )
                result[key] = value
            return result

        try:
            event = json.loads(line, object_pairs_hook=reject_duplicates)
        except json.JSONDecodeError as error:
            raise AthanorError(f"invalid Chronicle event at line {line_number}") from error
        if not isinstance(event, dict):
            raise AthanorError(f"Chronicle event at line {line_number} must be an object")
        return event

    def _parse_v11(self, text: str) -> list[dict[str, Any]]:
        from .schema_validation import validate_instance

        events: list[dict[str, Any]] = []
        previous_receipt_sigil: str | None = None
        for line_number, line in enumerate(text.splitlines(), start=1):
            event = self._decode_event(line, line_number)
            validate_instance("chronicle-event-1.1.json", event)
            receipt = event["receipt"]
            event_body = {
                key: value
                for key, value in event.items()
                if key not in {"event_body_sigil", "receipt"}
            }
            expected_event_sigil = content_sigil(event_body)
            receipt_body: dict[str, Any] = {
                key: value for key, value in receipt.items() if key != "receipt_sigil"
            }
            expected_receipt_sigil = content_sigil(receipt_body)
            if event["sequence"] != line_number:
                raise AthanorError(
                    f"broken Chronicle chain: non-contiguous sequence at line {line_number}"
                )
            if event["event_body_sigil"] != expected_event_sigil:
                raise AthanorError(f"invalid Event body Sigil at Chronicle line {line_number}")
            if receipt["receipt_sigil"] != expected_receipt_sigil:
                raise AthanorError(f"invalid Receipt Sigil at Chronicle line {line_number}")
            if event["previous_receipt_sigil"] != previous_receipt_sigil:
                raise AthanorError(f"broken Chronicle chain at line {line_number}")
            if receipt["previous_receipt_sigil"] != previous_receipt_sigil:
                raise AthanorError(f"Receipt chain reference mismatch at line {line_number}")
            if receipt["event_id"] != event["event_id"]:
                raise AthanorError(f"Receipt does not match event at line {line_number}")
            if receipt["event_body_sigil"] != event["event_body_sigil"]:
                raise AthanorError(f"Receipt body binding mismatch at line {line_number}")
            if receipt["accepted_at"] != event["occurred_at"]:
                raise AthanorError(f"Receipt acceptance time mismatch at line {line_number}")
            previous_receipt_sigil = receipt["receipt_sigil"]
            events.append(event)
        return events

    def _parse_v10(self, text: str) -> list[dict[str, Any]]:
        from .schema_validation import validate_instance

        events: list[dict[str, Any]] = []
        previous_sigil: str | None = None
        event_fields = {
            "schema_version",
            "event_id",
            "type",
            "object_id",
            "occurred_at",
            "previous_sigil",
            "payload",
            "receipt",
        }
        receipt_fields = {
            "receipt_id",
            "event_id",
            "sigil",
            "previous_sigil",
            "accepted_at",
        }
        for line_number, line in enumerate(text.splitlines(), start=1):
            event = self._decode_event(line, line_number)
            validate_instance("chronicle-event-1.0.json", event)
            receipt = event["receipt"]
            if set(event) != event_fields or set(receipt) != receipt_fields:
                raise AthanorError(
                    f"unsupported v1.0 fields at Chronicle line {line_number}; "
                    "migration refused"
                )
            expected = content_sigil(
                {key: value for key, value in event.items() if key != "receipt"}
            )
            if receipt["sigil"] != expected:
                raise AthanorError(f"invalid v1.0 Sigil at Chronicle line {line_number}")
            if event["previous_sigil"] != previous_sigil:
                raise AthanorError(f"broken v1.0 Chronicle chain at line {line_number}")
            if receipt["previous_sigil"] != previous_sigil:
                raise AthanorError(
                    f"v1.0 Receipt chain reference mismatch at line {line_number}"
                )
            if receipt["event_id"] != event["event_id"]:
                raise AthanorError(f"v1.0 Receipt does not match event at line {line_number}")
            if receipt["accepted_at"] != event["occurred_at"]:
                raise AthanorError(
                    f"v1.0 Receipt acceptance time mismatch at line {line_number}"
                )
            previous_sigil = expected
            events.append(event)
        return events

    def _read_head_v11(self) -> dict[str, Any]:
        from .schema_validation import validate_instance

        try:
            head = json.loads(self.head_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise AthanorError("invalid Chronicle head") from error
        if not isinstance(head, dict):
            raise AthanorError("Chronicle head must be an object")
        if head.get("schema_version") != "chronicle-head/1.1":
            raise AthanorError(
                "Chronicle v1.0 requires explicit migration: "
                "bwork migrate chronicle-v1.0-to-v1.1"
            )
        validate_instance("chronicle-head-1.1.json", head)
        return head

    def _read_locked(self) -> list[dict[str, Any]]:
        if not self.path.exists() or not self.head_path.exists():
            return []
        head = self._read_head_v11()
        events = self._parse_v11(self.path.read_text(encoding="utf-8"))
        actual_sigil = events[-1]["receipt"]["receipt_sigil"] if events else None
        if (
            head["event_count"] != len(events)
            or head["terminal_receipt_sigil"] != actual_sigil
        ):
            raise AthanorError("Chronicle head mismatch; truncation or incomplete commit detected")
        return events

    def events(self) -> list[dict[str, Any]]:
        self.initialize()
        with _exclusive_lock(self.lock_path):
            return self._read_locked()

    def transact(
        self,
        build: TransitionBuilder,
        actor: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], Receipt]:
        self.initialize()
        with _exclusive_lock(self.lock_path):
            events = self._read_locked()
            event_type, object_id, payload = build(events)
            previous_sigil = (
                events[-1]["receipt"]["receipt_sigil"] if events else None
            )
            accepted_at = datetime.now(UTC).isoformat()
            event = {
                "schema_version": "chronicle-event/1.1",
                "event_id": f"CE-{uuid4().hex[:12].upper()}",
                "sequence": len(events) + 1,
                "type": event_type,
                "object_id": object_id,
                "occurred_at": accepted_at,
                "previous_receipt_sigil": previous_sigil,
                "actor": dict(actor or LOCAL_ACTOR),
                "payload": payload,
            }
            event_body_sigil = content_sigil(event)
            event["event_body_sigil"] = event_body_sigil
            receipt_body: dict[str, Any] = {
                "schema_version": "receipt/1.1",
                "receipt_id": f"RC-{uuid4().hex[:12].upper()}",
                "event_id": event["event_id"],
                "event_body_sigil": event_body_sigil,
                "previous_receipt_sigil": previous_sigil,
                "accepted_at": accepted_at,
            }
            receipt = Receipt(
                schema_version="receipt/1.1",
                receipt_id=receipt_body["receipt_id"],
                event_id=receipt_body["event_id"],
                event_body_sigil=event_body_sigil,
                previous_receipt_sigil=previous_sigil,
                accepted_at=accepted_at,
                receipt_sigil=content_sigil(receipt_body),
            )
            event["receipt"] = receipt.as_dict()
            from .schema_validation import validate_instance

            validate_instance("chronicle-event-1.1.json", event)
            with self.path.open("a", encoding="utf-8") as ledger:
                ledger.write(canonical_json(event) + "\n")
                ledger.flush()
                os.fsync(ledger.fileno())
            self._write_head(len(events) + 1, receipt.sigil)
            return event, receipt

    def recover(
        self,
        projector: ProjectionBuilder,
        *,
        accept_valid_tail: bool,
    ) -> dict[str, Any]:
        self.initialize()
        with _exclusive_lock(self.lock_path):
            text = self.path.read_text(encoding="utf-8")
            events = self._parse_v11(text)
            head = self._read_head_v11()
            committed_count = head["event_count"]
            if committed_count > len(events):
                raise AthanorError("Chronicle recovery cannot restore removed events")
            committed_sigil = (
                events[committed_count - 1]["receipt"]["receipt_sigil"]
                if committed_count
                else None
            )
            if committed_sigil != head["terminal_receipt_sigil"]:
                raise AthanorError("Chronicle recovery found a rewritten committed prefix")
            projector(events)
            tail_count = len(events) - committed_count
            terminal_sigil = (
                events[-1]["receipt"]["receipt_sigil"] if events else None
            )
            if accept_valid_tail and tail_count:
                self._write_head(len(events), terminal_sigil)
            return {
                "schema_version": "chronicle-recovery-report/1.0",
                "status": "RECOVERED" if accept_valid_tail and tail_count else (
                    "RECOVERABLE" if tail_count else "HEALTHY"
                ),
                "committed_event_count": committed_count,
                "tail_event_count": tail_count,
                "terminal_receipt_sigil": terminal_sigil,
                "head_updated": bool(accept_valid_tail and tail_count),
            }

    def migrate_v10_to_v11(self, projector: ProjectionBuilder) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(self.lock_path):
            if not self.path.exists() or not self.head_path.exists():
                raise AthanorError("Chronicle v1.0 ledger and head are required for migration")
            text = self.path.read_text(encoding="utf-8")
            try:
                raw_head = json.loads(self.head_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as error:
                raise AthanorError("invalid Chronicle v1.0 head") from error
            if (
                isinstance(raw_head, dict)
                and raw_head.get("schema_version") == "chronicle-head/1.1"
            ):
                raise AthanorError("Chronicle is already v1.1; migration refused")
            old_events = self._parse_v10(text)
            expected_old_sigil = old_events[-1]["receipt"]["sigil"] if old_events else None
            if raw_head != {"count": len(old_events), "sigil": expected_old_sigil}:
                raise AthanorError("Chronicle v1.0 head mismatch; migration refused")
            old_projection = projector(old_events)

            new_events: list[dict[str, Any]] = []
            previous_receipt_sigil: str | None = None
            migration_actor = {
                "actor_id": "benchwork-migration",
                "actor_type": "tool",
                "host": "cli",
                "authenticated_by": "local-session",
            }
            for sequence, old_event in enumerate(old_events, start=1):
                event_body = {
                    "schema_version": "chronicle-event/1.1",
                    "event_id": old_event["event_id"],
                    "sequence": sequence,
                    "type": old_event["type"],
                    "object_id": old_event["object_id"],
                    "occurred_at": old_event["occurred_at"],
                    "previous_receipt_sigil": previous_receipt_sigil,
                    "actor": migration_actor,
                    "payload": old_event["payload"],
                }
                event_body_sigil = content_sigil(event_body)
                receipt_body = {
                    "schema_version": "receipt/1.1",
                    "receipt_id": old_event["receipt"]["receipt_id"],
                    "event_id": old_event["event_id"],
                    "event_body_sigil": event_body_sigil,
                    "previous_receipt_sigil": previous_receipt_sigil,
                    "accepted_at": old_event["occurred_at"],
                }
                receipt_sigil = content_sigil(receipt_body)
                new_events.append(
                    {
                        **event_body,
                        "event_body_sigil": event_body_sigil,
                        "receipt": {
                            **receipt_body,
                            "receipt_sigil": receipt_sigil,
                        },
                    }
                )
                previous_receipt_sigil = receipt_sigil

            migrated_text = "".join(canonical_json(event) + "\n" for event in new_events)
            verified_events = self._parse_v11(migrated_text)
            if projector(verified_events) != old_projection:
                raise AthanorError("migration changed the scientific projection")

            migration_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            backup_directory = self.path.parent / "migrations" / migration_id
            backup_directory.mkdir(parents=True)
            shutil.copy2(self.path, backup_directory / "chronicle.jsonl.v1.0")
            shutil.copy2(self.head_path, backup_directory / "chronicle.head.v1.0")

            report = {
                "schema_version": "chronicle-migration-report/1.0",
                "migration": "chronicle-v1.0-to-v1.1",
                "event_count": len(new_events),
                "source_terminal_sigil": expected_old_sigil,
                "target_terminal_receipt_sigil": previous_receipt_sigil,
                "backup_directory": str(backup_directory.relative_to(self.path.parent)),
                "projection_preserved": True,
            }
            report_path = backup_directory / "migration-report.json"
            report_path.write_text(canonical_json(report) + "\n", encoding="utf-8")

            ledger_temporary = self.path.with_suffix(".jsonl.tmp")
            ledger_temporary.write_text(migrated_text, encoding="utf-8")
            with ledger_temporary.open("rb") as handle:
                os.fsync(handle.fileno())
            os.replace(ledger_temporary, self.path)
            self._write_head(len(new_events), previous_receipt_sigil)
            return report


class Athanor:
    """Validates canonical research transitions and rebuilds their projections."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.chronicle = Chronicle(root)

    def initialize(self) -> None:
        self.chronicle.initialize()

    def recover_chronicle(self, *, accept_valid_tail: bool = False) -> dict[str, Any]:
        return self.chronicle.recover(
            self._project,
            accept_valid_tail=accept_valid_tail,
        )

    def migrate_chronicle_v10_to_v11(self) -> dict[str, Any]:
        return self.chronicle.migrate_v10_to_v11(self._project)

    def _project(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        programs: dict[str, dict[str, Any]] = {}
        protocols: dict[str, dict[str, Any]] = {}
        approvals: dict[str, dict[str, Any]] = {}
        workings: dict[str, dict[str, Any]] = {}
        experiments: dict[str, dict[str, Any]] = {}
        runs: dict[str, dict[str, Any]] = {}
        result_bundles: dict[str, dict[str, Any]] = {}
        evidence: dict[str, dict[str, Any]] = {}
        claims: dict[str, dict[str, Any]] = {}
        hypotheses: dict[str, dict[str, Any]] = {}
        assessments: dict[str, dict[str, Any]] = {}
        decisions: dict[str, dict[str, Any]] = {}
        artifacts: dict[str, dict[str, Any]] = {}
        issues: dict[str, dict[str, Any]] = {}
        deviations: dict[str, dict[str, Any]] = {}
        reproduction_records: dict[str, dict[str, Any]] = {}
        agent_results: dict[str, dict[str, Any]] = {}
        for event in events:
            payload = event["payload"]
            object_id = event["object_id"]
            event_actor = event.get(
                "actor",
                {
                    "actor_id": "benchwork-migration",
                    "actor_type": "tool",
                    "host": "cli",
                    "authenticated_by": "local-session",
                },
            )
            if event["type"] == "program.created":
                if object_id in programs:
                    raise AthanorError(f"duplicate Research Program: {object_id}")
                programs[object_id] = {
                    "schema_version": "research-program/1.1",
                    "program_id": object_id,
                    "slug": payload["slug"],
                    "title": payload["title"],
                    "problem": payload["problem"],
                    "status": "IDEA",
                    "research_question": None,
                    "evidence": [],
                    "claims": [],
                    "hypotheses": [],
                    "protocols": [],
                    "assessments": [],
                    "decisions": [],
                    "artifacts": [],
                    "issues": [],
                    "deviations": [],
                    "reproduction_records": [],
                }
            elif event["type"] == "evidence.recorded":
                program = programs.get(payload["program_id"])
                if program is None or object_id in evidence:
                    raise AthanorError(f"invalid Evidence record: {object_id}")
                evidence[object_id] = {
                    "schema_version": "evidence/1.2",
                    "evidence_id": object_id,
                    "program_id": payload["program_id"],
                    "source": payload["source"],
                    "observation": payload["observation"],
                    "claim_relations": [],
                    "verification": {
                        key: bool(payload.get("verification", {}).get(key, False))
                        for key in EVIDENCE_VERIFICATION_KEYS
                    },
                    "reproduction_ids": [],
                }
                program["evidence"].append(object_id)
                _advance_program(program, "EVIDENCE_RECORDED")
            elif event["type"] == "evidence.verified":
                record = evidence.get(object_id)
                verification = {
                    key: bool(payload["verification"].get(key, False))
                    for key in EVIDENCE_VERIFICATION_KEYS
                }
                if record is None or any(
                    record["verification"][key] and not verification[key]
                    for key in EVIDENCE_VERIFICATION_KEYS
                ):
                    raise AthanorError(f"invalid Evidence verification: {object_id}")
                record["verification"] = verification
            elif event["type"] == "evidence.source_resolved":
                record = evidence.get(object_id)
                if record is None or record["verification"]["source_resolved"]:
                    raise AthanorError(f"invalid Evidence source resolution: {object_id}")
                record["verification"]["source_resolved"] = True
            elif event["type"] == "evidence.content_inspected":
                record = evidence.get(object_id)
                if (
                    record is None
                    or not record["verification"]["source_resolved"]
                    or record["verification"]["content_inspected"]
                ):
                    raise AthanorError(f"invalid Evidence content inspection: {object_id}")
                record["verification"]["content_inspected"] = True
            elif event["type"] == "claim.created":
                program = programs.get(payload["program_id"])
                relations = payload.get("evidence_relations", [])
                related_evidence = [
                    evidence.get(relation["evidence_id"]) for relation in relations
                ]
                if (
                    program is None
                    or object_id in claims
                    or len({relation["evidence_id"] for relation in relations}) != len(relations)
                    or any(
                        record is None
                        or record["program_id"] != payload["program_id"]
                        or not record["verification"]["source_resolved"]
                        or not record["verification"]["content_inspected"]
                        for record in related_evidence
                    )
                ):
                    raise AthanorError(f"invalid Claim creation: {object_id}")
                claims[object_id] = {
                    "schema_version": "claim/1.2",
                    "claim_id": object_id,
                    "program_id": payload["program_id"],
                    "type": payload["type"],
                    "statement": payload["statement"],
                    "status": "PROPOSED",
                    "evidence_relations": [
                        {**relation, "status": "PROPOSED"}
                        for relation in relations
                    ],
                }
                for relation, record in zip(relations, related_evidence, strict=True):
                    assert record is not None
                    record["claim_relations"].append(
                        {
                            "claim_id": object_id,
                            "relation": relation["relation"],
                            "status": "PROPOSED",
                        }
                    )
                program["claims"].append(object_id)
                _advance_program(program, "CLAIMS_REGISTERED")
            elif event["type"] == "claim_relation.proposed":
                claim = claims.get(object_id)
                record = evidence.get(payload["evidence_id"])
                if (
                    claim is None
                    or record is None
                    or claim["program_id"] != record["program_id"]
                    or any(
                        relation["evidence_id"] == payload["evidence_id"]
                        for relation in claim["evidence_relations"]
                    )
                ):
                    raise AthanorError(f"invalid Claim relation proposal: {object_id}")
                relation = {
                    "evidence_id": payload["evidence_id"],
                    "relation": payload["relation"],
                    "status": "PROPOSED",
                }
                claim["evidence_relations"].append(relation)
                record["claim_relations"].append(
                    {
                        "claim_id": object_id,
                        "relation": payload["relation"],
                        "status": "PROPOSED",
                    }
                )
            elif event["type"] == "claim_relation.verified":
                claim = claims.get(object_id)
                record = evidence.get(payload["evidence_id"])
                if (
                    claim is None
                    or record is None
                    or not record["verification"]["source_resolved"]
                    or not record["verification"]["content_inspected"]
                ):
                    raise AthanorError(f"invalid Claim relation verification: {object_id}")
                claim_relation = next(
                    (
                        relation
                        for relation in claim["evidence_relations"]
                        if relation["evidence_id"] == payload["evidence_id"]
                    ),
                    None,
                )
                evidence_relation = next(
                    (
                        relation
                        for relation in record["claim_relations"]
                        if relation["claim_id"] == object_id
                    ),
                    None,
                )
                if (
                    claim_relation is None
                    or evidence_relation is None
                    or claim_relation["status"] != "PROPOSED"
                    or evidence_relation["status"] != "PROPOSED"
                ):
                    raise AthanorError(f"invalid Claim relation verification: {object_id}")
                claim_relation["status"] = "VERIFIED"
                evidence_relation["status"] = "VERIFIED"
            elif event["type"] == "hypothesis.created":
                program = programs.get(payload["program_id"])
                related_claims = [claims.get(claim_id) for claim_id in payload["claim_ids"]]
                if (
                    program is None
                    or object_id in hypotheses
                    or len(set(payload["claim_ids"])) != len(payload["claim_ids"])
                    or any(
                        claim is None or claim["program_id"] != payload["program_id"]
                        for claim in related_claims
                    )
                ):
                    raise AthanorError(f"invalid Hypothesis creation: {object_id}")
                hypotheses[object_id] = {
                    "schema_version": "hypothesis/1.0",
                    "hypothesis_id": object_id,
                    "program_id": payload["program_id"],
                    "claim_ids": payload["claim_ids"],
                    "statement": payload["statement"],
                    "prediction": payload["prediction"],
                    "status": "PROPOSED",
                }
                program["hypotheses"].append(object_id)
                _advance_program(program, "HYPOTHESES_REGISTERED")
            elif event["type"] == "research_question.sealed":
                program = programs.get(object_id)
                if program is None or program["research_question"] is not None:
                    raise AthanorError(f"invalid Research Question Seal: {object_id}")
                program["research_question"] = {
                    "statement": payload["statement"],
                    "sealed_at": event["occurred_at"],
                    "seal_receipt": event["receipt"]["receipt_id"],
                    "actor": event_actor,
                }
                _advance_program(program, "RQ_FROZEN")
            elif event["type"] == "protocol.drafted":
                hypothesis_ids = payload.get("hypothesis_ids", [])
                study_mode = payload.get("study_mode")
                analysis_spec = payload.get("analysis_spec")
                if (
                    payload["program_id"] not in programs
                    or object_id in protocols
                    or (study_mode == "confirmatory" and not hypothesis_ids)
                    or len(set(hypothesis_ids)) != len(hypothesis_ids)
                    or any(
                        hypothesis_id not in hypotheses
                        or hypotheses[hypothesis_id]["program_id"] != payload["program_id"]
                        for hypothesis_id in hypothesis_ids
                    )
                ):
                    raise AthanorError(f"invalid Protocol draft: {object_id}")
                protocol = {
                    "schema_version": (
                        "study-protocol/1.3"
                        if analysis_spec is not None
                        else (
                            "study-protocol/1.2"
                            if study_mode is not None
                            else "study-protocol/1.1"
                        )
                    ),
                    "protocol_id": object_id,
                    "program_id": payload["program_id"],
                    "hypothesis_ids": hypothesis_ids,
                    "title": payload["title"],
                    "analysis_plan": payload["analysis_plan"],
                    "status": "DRAFT",
                    "deviations": [],
                    "sealed_at": None,
                    "seal_receipt": None,
                    "seal_actor": None,
                }
                if study_mode is not None:
                    protocol["study_mode"] = study_mode
                if analysis_spec is not None:
                    protocol["analysis_spec"] = analysis_spec
                protocols[object_id] = protocol
            elif event["type"] == "protocol.sealed":
                sealed_protocol = protocols.get(object_id)
                if sealed_protocol is None or sealed_protocol["status"] != "DRAFT":
                    raise AthanorError(f"invalid Protocol Seal: {object_id}")
                sealed_protocol["status"] = "FROZEN"
                sealed_protocol["sealed_at"] = event["occurred_at"]
                sealed_protocol["seal_receipt"] = event["receipt"]["receipt_id"]
                sealed_protocol["seal_actor"] = event_actor
                program = programs[sealed_protocol["program_id"]]
                program["protocols"].append(object_id)
                _advance_program(program, "DESIGN_FROZEN")
            elif event["type"] == "approval.granted":
                if object_id in approvals:
                    raise AthanorError(f"duplicate approval for Task: {object_id}")
                approvals[object_id] = {
                    "task_id": object_id,
                    **payload,
                    "receipt_id": event["receipt"]["receipt_id"],
                    "granted_at": event["occurred_at"],
                }
            elif event["type"] == "agent-result.accepted":
                result = payload["result"]
                from .schema_validation import validate_instance

                result_version = result.get("schema_version")
                if result_version not in {"agent-result/1.0", "agent-result/1.1"}:
                    raise AthanorError(f"invalid Agent Result acceptance: {object_id}")
                if result_version == "agent-result/1.0":
                    validate_instance("agent-contract-1.0.json", result)
                    if (
                        object_id in agent_results
                        or result["task_id"] != object_id
                        or result["input_sigil"] != payload["input_sigil"]
                    ):
                        raise AthanorError(
                            f"invalid Agent Result acceptance: {object_id}"
                        )
                    agent_results[object_id] = {
                        "schema_version": "agent-result-record/1.0",
                        "task_id": object_id,
                        "host": payload["host"],
                        "capability": payload["capability"],
                        "input_sigil": payload["input_sigil"],
                        "capsule_sigil": payload["capsule_sigil"],
                        "artifacts": result["artifacts"],
                        "status": result["status"],
                        "accepted_at": event["occurred_at"],
                        "acceptance_receipt": event["receipt"]["receipt_id"],
                    }
                else:
                    validate_instance("agent-result-1.1.json", result)
                    capability = payload["capability"]
                    snapshot = payload["snapshot"]
                    if (
                        object_id in agent_results
                        or result["task_id"] != object_id
                        or result["snapshot_sigil"] != snapshot["snapshot_sigil"]
                        or result["capability_contract_sigil"]
                        != capability["contract_sigil"]
                    ):
                        raise AthanorError(
                            f"invalid Agent Result acceptance: {object_id}"
                        )
                    record = {
                        "schema_version": "agent-result-record/1.1",
                        "task_id": object_id,
                        "host": payload["host"],
                        "program_id": payload["program_id"],
                        "capability": capability,
                        "snapshot": snapshot,
                        "capsule_sigil": payload["capsule_sigil"],
                        "outputs": result["outputs"],
                        "status": result["status"],
                        "accepted_at": event["occurred_at"],
                        "acceptance_receipt": event["receipt"]["receipt_id"],
                    }
                    if "provenance" in result:
                        record["provenance"] = result["provenance"]
                    agent_results[object_id] = record
            elif event["type"] == "working.created":
                working_protocol = protocols.get(payload["protocol_id"])
                rite = payload["rite"]
                if (
                    object_id in workings
                    or working_protocol is None
                    or working_protocol["status"] != "FROZEN"
                    or working_protocol["program_id"] != payload["program_id"]
                    or payload["rite_sigil"] != content_sigil(rite)
                ):
                    raise AthanorError(f"invalid Working creation: {object_id}")
                first_stage = rite["stages"][0]["name"]
                if rite.get("schema_version") == "rite/1.1":
                    workings[object_id] = {
                        "schema_version": "working/1.1",
                        "working_id": object_id,
                        "rite_id": payload["rite_id"],
                        "rite_sigil": payload["rite_sigil"],
                        "rite": rite,
                        "program_id": payload["program_id"],
                        "protocol_id": payload["protocol_id"],
                        "stage": first_stage,
                        "status": "ACTIVE",
                        "history": [
                            {
                                "stage": first_stage,
                                "at": event["occurred_at"],
                                "reason": "created",
                                "canonical_event_id": event["event_id"],
                                "object_id": object_id,
                            }
                        ],
                    }
                else:
                    workings[object_id] = {
                        "schema_version": "working/1.0",
                        "working_id": object_id,
                        "rite_id": payload["rite_id"],
                        "rite_sigil": payload["rite_sigil"],
                        "rite": rite,
                        "program_id": payload["program_id"],
                        "protocol_id": payload["protocol_id"],
                        "stage": first_stage,
                        "history": [
                            {
                                "stage": first_stage,
                                "at": event["occurred_at"],
                                "reason": "created",
                                "artifacts": [],
                            }
                        ],
                    }
            elif event["type"] == "working.advanced":
                working = workings.get(object_id)
                if (
                    working is None
                    or working["schema_version"] != "working/1.0"
                    or payload["from_stage"] != working["stage"]
                ):
                    raise AthanorError(f"invalid Working transition: {object_id}")
                stages = [stage["name"] for stage in working["rite"]["stages"]]
                index = stages.index(working["stage"])
                if index + 1 >= len(stages) or payload["to_stage"] != stages[index + 1]:
                    raise AthanorError(f"invalid Working transition: {object_id}")
                working["stage"] = payload["to_stage"]
                working["history"].append(
                    {
                        "stage": payload["to_stage"],
                        "at": event["occurred_at"],
                        "reason": payload["reason"],
                        "artifacts": payload["artifacts"],
                    }
                )
            elif event["type"] in {"experiment.created", "experiment.planned"}:
                experiment_protocol = protocols.get(payload["protocol_id"])
                hypothesis_id = payload["hypothesis_id"]
                hypothesis = hypotheses.get(hypothesis_id) if hypothesis_id is not None else None
                if (
                    object_id in experiments
                    or experiment_protocol is None
                    or experiment_protocol["status"] != "FROZEN"
                    or experiment_protocol["program_id"] != payload["program_id"]
                    or (
                        hypothesis_id is not None
                        and (
                            hypothesis is None
                            or hypothesis["program_id"] != payload["program_id"]
                            or hypothesis_id not in experiment_protocol["hypothesis_ids"]
                        )
                    )
                ):
                    raise AthanorError(f"invalid Experiment creation: {object_id}")
                planned_experiment = {
                    "schema_version": (
                        "experiment/1.1"
                        if event["type"] == "experiment.planned"
                        else "experiment/1.0"
                    ),
                    "experiment_id": object_id,
                    "program_id": payload["program_id"],
                    "protocol_id": payload["protocol_id"],
                    "hypothesis_id": payload["hypothesis_id"],
                    "question": payload["question"],
                    "status": "PLANNED",
                }
                if event["type"] == "experiment.planned":
                    planned_experiment["history"] = [
                        {
                            "status": "PLANNED",
                            "event_id": event["event_id"],
                            "at": event["occurred_at"],
                        }
                    ]
                experiments[object_id] = planned_experiment
                if hypothesis is not None:
                    hypothesis["status"] = "ACTIVE"
            elif event["type"].startswith("experiment."):
                transitioned_experiment = experiments.get(object_id)
                transitions = {
                    "experiment.implemented": ("PLANNED", "IMPLEMENTED"),
                    "experiment.pilot_started": ("IMPLEMENTED", "PILOT_RUNNING"),
                    "experiment.pilot_completed": ("PILOT_RUNNING", "PILOT_COMPLETED"),
                    "experiment.formal_started": ("PILOT_COMPLETED", "FORMAL_RUNNING"),
                    "experiment.completed": ("FORMAL_RUNNING", "COMPLETED"),
                }
                if event["type"] == "experiment.cancelled":
                    valid = (
                        transitioned_experiment is not None
                        and transitioned_experiment["schema_version"] == "experiment/1.1"
                        and transitioned_experiment["status"]
                        not in {"COMPLETED", "CANCELLED"}
                    )
                    next_status: str | None = "CANCELLED"
                else:
                    expected, next_status = transitions.get(event["type"], (None, None))
                    valid = (
                        transitioned_experiment is not None
                        and transitioned_experiment["schema_version"] == "experiment/1.1"
                        and transitioned_experiment["status"] == expected
                    )
                if not valid or next_status is None:
                    raise AthanorError(f"invalid Experiment transition: {object_id}")
                assert transitioned_experiment is not None
                transitioned_experiment["status"] = next_status
                transitioned_experiment["history"].append(
                    {
                        "status": next_status,
                        "event_id": event["event_id"],
                        "at": event["occurred_at"],
                    }
                )
                program = programs[transitioned_experiment["program_id"]]
                if event["type"] == "experiment.implemented":
                    _advance_program(program, "IMPLEMENTED")
                elif event["type"] == "experiment.pilot_completed":
                    _advance_program(program, "PILOTED")
                elif event["type"] == "experiment.formal_started":
                    _advance_program(program, "RUNNING")
            elif event["type"] == "run.recorded":
                run_experiment = experiments.get(payload["experiment_id"])
                if (
                    object_id in runs
                    or run_experiment is None
                    or run_experiment["program_id"] != payload["program_id"]
                    or run_experiment["protocol_id"] != payload["protocol_id"]
                ):
                    raise AthanorError(f"invalid Run record: {object_id}")
                disposition = payload.get("analysis_disposition")
                analysis_included = (
                    disposition["included"]
                    if disposition is not None
                    else payload["analysis_included"]
                )
                if analysis_included and payload["status"] != "COMPLETED":
                    raise AthanorError(f"non-completed Run cannot be included: {object_id}")
                run = {
                    "schema_version": (
                        "run/1.2"
                        if "arm" in payload
                        else ("run/1.1" if disposition is not None else "run/1.0")
                    ),
                    "run_id": object_id,
                    "program_id": payload["program_id"],
                    "protocol_id": payload["protocol_id"],
                    "experiment_id": payload["experiment_id"],
                    "status": payload["status"],
                    "seed": payload["seed"],
                    "metrics": payload["metrics"],
                    "artifacts": payload["artifacts"],
                }
                if disposition is None:
                    run["analysis_included"] = payload["analysis_included"]
                else:
                    run["phase"] = payload["phase"]
                    run["analysis_disposition"] = disposition
                    if "arm" in payload:
                        run["arm"] = payload["arm"]
                runs[object_id] = run
                _advance_program(
                    programs[payload["program_id"]],
                    "PILOTED" if payload.get("phase") == "PILOT" else "RUNNING",
                )
            elif event["type"] == "analysis.computed":
                from .alembic import (
                    build_legacy_result_bundle,
                    build_result_bundle,
                )

                analysis_bundle = payload["bundle"]
                analysis_protocol = protocols.get(analysis_bundle["protocol_id"])
                expected_bundle = (
                    build_result_bundle(
                        object_id,
                        analysis_protocol,
                        list(runs.values()),
                    )
                    if analysis_bundle.get("schema_version") == "result-bundle/1.1"
                    and analysis_protocol is not None
                    else build_legacy_result_bundle(
                        object_id,
                        analysis_bundle["program_id"],
                        analysis_bundle["protocol_id"],
                        list(runs.values()),
                    )
                )
                if (
                    object_id in result_bundles
                    or analysis_bundle != expected_bundle
                    or payload["bundle_sigil"] != content_sigil(analysis_bundle)
                ):
                    raise AthanorError(f"invalid Result Bundle: {object_id}")
                result_bundles[object_id] = analysis_bundle
                _advance_program(
                    programs[analysis_bundle["program_id"]],
                    "RESULT_READY",
                )
            elif event["type"] == "assessment.recorded":
                assessed_bundle = result_bundles.get(payload["result_bundle_id"])
                program = programs.get(payload["program_id"])
                assessment_protocol = protocols.get(payload["protocol_id"])
                claim_findings = payload["claim_findings"]
                hypothesis_findings = payload["hypothesis_findings"]
                if (
                    object_id in assessments
                    or assessed_bundle is None
                    or program is None
                    or assessment_protocol is None
                    or assessed_bundle["program_id"] != payload["program_id"]
                    or assessed_bundle["protocol_id"] != payload["protocol_id"]
                    or len({finding["claim_id"] for finding in claim_findings}) != len(claim_findings)
                    or len({finding["hypothesis_id"] for finding in hypothesis_findings})
                    != len(hypothesis_findings)
                    or any(
                        finding["claim_id"] not in claims
                        or claims[finding["claim_id"]]["program_id"] != payload["program_id"]
                        for finding in claim_findings
                    )
                    or any(
                        finding["hypothesis_id"] not in hypotheses
                        or hypotheses[finding["hypothesis_id"]]["program_id"] != payload["program_id"]
                        or finding["hypothesis_id"]
                        not in assessment_protocol["hypothesis_ids"]
                        for finding in hypothesis_findings
                    )
                ):
                    raise AthanorError(f"invalid Assessment: {object_id}")
                study_mode = payload.get("study_mode")
                if (
                    study_mode == "confirmatory"
                    and not hypothesis_findings
                ):
                    raise AthanorError(f"invalid Assessment: {object_id}")
                assessment = {
                    "schema_version": (
                        "assessment/1.2"
                        if study_mode is not None
                        else "assessment/1.1"
                    ),
                    "assessment_id": object_id,
                    "program_id": payload["program_id"],
                    "protocol_id": payload["protocol_id"],
                    "result_bundle_id": payload["result_bundle_id"],
                    "result_bundle": {
                        "uri": f".benchwork/results/{payload['result_bundle_id']}.json",
                        "sigil": content_sigil(assessed_bundle),
                    },
                    "summary": payload["summary"],
                    "limitations": payload["limitations"],
                    "claim_findings": claim_findings,
                    "hypothesis_findings": hypothesis_findings,
                    "status": "COMPLETE",
                    "reviewed_at": event["occurred_at"],
                    "review_receipt": event["receipt"]["receipt_id"],
                }
                if study_mode is not None:
                    assessment["study_mode"] = study_mode
                assessments[object_id] = assessment
                for finding in claim_findings:
                    claims[finding["claim_id"]]["status"] = finding["status"]
                for finding in hypothesis_findings:
                    hypotheses[finding["hypothesis_id"]]["status"] = finding["status"]
                program["assessments"].append(object_id)
                _advance_program(program, "EVALUATED")
            elif event["type"] == "reproduction.assessed":
                record = evidence.get(payload["evidence_id"])
                program = programs.get(payload["program_id"])
                if (
                    object_id in reproduction_records
                    or record is None
                    or program is None
                    or record["program_id"] != payload["program_id"]
                    or any(
                        run_id not in runs
                        or runs[run_id]["program_id"] != payload["program_id"]
                        for run_id in payload["run_ids"]
                    )
                    or payload["result_bundle_id"] not in result_bundles
                    or result_bundles[payload["result_bundle_id"]]["program_id"]
                    != payload["program_id"]
                    or any(
                        artifact_id not in artifacts
                        or artifacts[artifact_id]["program_id"] != payload["program_id"]
                        for artifact_id in payload["artifact_ids"]
                    )
                    or payload["assessment_id"] not in assessments
                    or assessments[payload["assessment_id"]]["program_id"]
                    != payload["program_id"]
                ):
                    raise AthanorError(f"invalid Reproduction Record: {object_id}")
                reproduction_records[object_id] = {
                    "schema_version": "reproduction-record/1.0",
                    "reproduction_id": object_id,
                    "program_id": payload["program_id"],
                    "evidence_id": payload["evidence_id"],
                    "run_ids": payload["run_ids"],
                    "result_bundle_id": payload["result_bundle_id"],
                    "artifact_ids": payload["artifact_ids"],
                    "assessment_id": payload["assessment_id"],
                    "status": payload["status"],
                    "recorded_at": event["occurred_at"],
                    "record_receipt": event["receipt"]["receipt_id"],
                }
                record["reproduction_ids"].append(object_id)
                program["reproduction_records"].append(object_id)
            elif event["type"] == "decision.sealed":
                program = programs.get(payload["program_id"])
                related_assessments = [
                    assessments.get(assessment_id) for assessment_id in payload["assessment_ids"]
                ]
                if (
                    object_id in decisions
                    or program is None
                    or len(set(payload["assessment_ids"])) != len(payload["assessment_ids"])
                    or any(
                        assessment is None
                        or assessment["program_id"] != payload["program_id"]
                        or assessment["status"] != "COMPLETE"
                        for assessment in related_assessments
                    )
                ):
                    raise AthanorError(f"invalid Decision Seal: {object_id}")
                verified_assessments = [
                    assessment
                    for assessment in related_assessments
                    if assessment is not None
                ]
                open_issue_ids = sorted(
                    issue_id
                    for issue_id, issue in issues.items()
                    if issue["program_id"] == payload["program_id"]
                    and issue["status"] == "OPEN"
                )
                unresolved_uncertainties = sorted(
                    {
                        limitation
                        for assessment in verified_assessments
                        for limitation in assessment["limitations"]
                    }
                )
                required_actions = payload.get("required_actions", [])
                lineage = payload.get("lineage")
                if (
                    (
                        payload["outcome"] == "CONTINUE"
                        and any(
                            issues[issue_id]["severity"] == "CRITICAL"
                            for issue_id in open_issue_ids
                        )
                    )
                    or (
                        payload["outcome"] == "REPAIR"
                        and not required_actions
                    )
                    or (
                        payload["outcome"] == "PIVOT"
                        and (
                            not isinstance(lineage, dict)
                            or lineage.get("parent_program_id")
                            != payload["program_id"]
                        )
                    )
                    or (
                        payload["outcome"] == "REVIEW_REQUIRED"
                        and len(payload["assessment_ids"]) < 2
                    )
                    or payload.get("unresolved_issue_ids", open_issue_ids)
                    != open_issue_ids
                    or payload.get(
                        "unresolved_uncertainties",
                        unresolved_uncertainties,
                    )
                    != unresolved_uncertainties
                ):
                    raise AthanorError(f"invalid Decision Gate: {object_id}")
                decisions[object_id] = {
                    "schema_version": "decision/1.2",
                    "decision_id": object_id,
                    "program_id": payload["program_id"],
                    "outcome": payload["outcome"],
                    "assessment_ids": payload["assessment_ids"],
                    "rationale": payload["rationale"],
                    "required_actions": required_actions,
                    "lineage": lineage,
                    "unresolved_issue_ids": open_issue_ids,
                    "unresolved_uncertainties": payload.get(
                        "unresolved_uncertainties",
                        unresolved_uncertainties,
                    ),
                    "status": "SEALED",
                    "sealed_at": event["occurred_at"],
                    "seal_receipt": event["receipt"]["receipt_id"],
                    "seal_actor": event_actor,
                }
                program["decisions"].append(object_id)
            elif event["type"] == "artifact.registered":
                program = programs.get(payload["program_id"])
                related_ids = [payload["producer_id"], *payload["input_ids"]]
                collections = (
                    evidence,
                    claims,
                    hypotheses,
                    protocols,
                    workings,
                    experiments,
                    runs,
                    result_bundles,
                    assessments,
                    decisions,
                    artifacts,
                    issues,
                    deviations,
                )
                if (
                    object_id in artifacts
                    or program is None
                    or len(set(payload["input_ids"])) != len(payload["input_ids"])
                    or any(
                        _object_program_id(reference_id, programs, *collections)
                        != payload["program_id"]
                        for reference_id in related_ids
                    )
                ):
                    raise AthanorError(f"invalid Artifact registration: {object_id}")
                artifacts[object_id] = {
                    "schema_version": "artifact/1.0",
                    "artifact_id": object_id,
                    "program_id": payload["program_id"],
                    "kind": payload["kind"],
                    "location": payload["location"],
                    "producer_id": payload["producer_id"],
                    "input_ids": payload["input_ids"],
                    "status": "REGISTERED",
                    "registered_at": event["occurred_at"],
                    "registration_receipt": event["receipt"]["receipt_id"],
                }
                program["artifacts"].append(object_id)
                if payload["kind"] == "implementation":
                    _advance_program(program, "IMPLEMENTED")
            elif event["type"] == "program.closed":
                program = programs.get(object_id)
                if (
                    program is None
                    or program["status"] != "EVALUATED"
                    or not program["decisions"]
                ):
                    raise AthanorError(f"invalid Program closure: {object_id}")
                program["status"] = "CLOSED"
            elif event["type"] == "issue.opened":
                program = programs.get(payload["program_id"])
                collections = (
                    evidence,
                    claims,
                    hypotheses,
                    protocols,
                    workings,
                    experiments,
                    runs,
                    result_bundles,
                    assessments,
                    decisions,
                    artifacts,
                    issues,
                    deviations,
                )
                if (
                    object_id in issues
                    or program is None
                    or len(set(payload["subject_ids"])) != len(payload["subject_ids"])
                    or any(
                        _object_program_id(subject_id, programs, *collections)
                        != payload["program_id"]
                        for subject_id in payload["subject_ids"]
                    )
                ):
                    raise AthanorError(f"invalid Issue opening: {object_id}")
                issues[object_id] = {
                    "schema_version": "issue/1.0",
                    "issue_id": object_id,
                    "program_id": payload["program_id"],
                    "subject_ids": payload["subject_ids"],
                    "severity": payload["severity"],
                    "title": payload["title"],
                    "description": payload["description"],
                    "status": "OPEN",
                    "opened_at": event["occurred_at"],
                    "open_receipt": event["receipt"]["receipt_id"],
                    "resolution": None,
                    "resolved_at": None,
                    "resolution_receipt": None,
                }
                program["issues"].append(object_id)
            elif event["type"] == "issue.resolved":
                issue = issues.get(object_id)
                if (
                    issue is None
                    or issue["status"] != "OPEN"
                    or payload["program_id"] != issue["program_id"]
                ):
                    raise AthanorError(f"invalid Issue resolution: {object_id}")
                issue["status"] = "RESOLVED"
                issue["resolution"] = payload["resolution"]
                issue["resolved_at"] = event["occurred_at"]
                issue["resolution_receipt"] = event["receipt"]["receipt_id"]
            elif event["type"] == "deviation.recorded":
                program = programs.get(payload["program_id"])
                deviation_protocol = protocols.get(payload["protocol_id"])
                collections = (
                    evidence,
                    claims,
                    hypotheses,
                    protocols,
                    workings,
                    experiments,
                    runs,
                    result_bundles,
                    assessments,
                    decisions,
                    artifacts,
                    issues,
                    deviations,
                )
                if (
                    object_id in deviations
                    or program is None
                    or deviation_protocol is None
                    or deviation_protocol["program_id"] != payload["program_id"]
                    or deviation_protocol["status"] != "FROZEN"
                    or len(set(payload["affected_object_ids"]))
                    != len(payload["affected_object_ids"])
                    or any(
                        _object_program_id(affected_id, programs, *collections)
                        != payload["program_id"]
                        for affected_id in payload["affected_object_ids"]
                    )
                ):
                    raise AthanorError(f"invalid Deviation record: {object_id}")
                deviations[object_id] = {
                    "schema_version": "deviation/1.0",
                    "deviation_id": object_id,
                    "program_id": payload["program_id"],
                    "protocol_id": payload["protocol_id"],
                    "kind": payload["kind"],
                    "summary": payload["summary"],
                    "rationale": payload["rationale"],
                    "impact": payload["impact"],
                    "affected_object_ids": payload["affected_object_ids"],
                    "status": "RECORDED",
                    "recorded_at": event["occurred_at"],
                    "record_receipt": event["receipt"]["receipt_id"],
                }
                protocol["deviations"].append(object_id)
                program["deviations"].append(object_id)
            else:
                raise AthanorError(f"unsupported Chronicle event type: {event['type']}")
            _advance_workings_for_event(
                event,
                workings,
                protocols,
                experiments,
                runs,
                result_bundles,
                assessments,
                decisions,
                artifacts,
            )
        from .schema_validation import validate_instance

        for program in programs.values():
            validate_instance("research-program-1.1.json", program)
        for protocol in protocols.values():
            validate_instance(
                {
                    "study-protocol/1.1": "protocol-1.1.json",
                    "study-protocol/1.2": "protocol-1.2.json",
                    "study-protocol/1.3": "protocol-1.3.json",
                }[protocol["schema_version"]],
                protocol,
            )
        for working in workings.values():
            validate_instance(
                "working-1.1.json"
                if working["schema_version"] == "working/1.1"
                else "working-1.0.json",
                working,
            )
        for experiment in experiments.values():
            validate_instance(
                "experiment-1.1.json"
                if experiment["schema_version"] == "experiment/1.1"
                else "experiment-1.0.json",
                experiment,
            )
        for run in runs.values():
            validate_instance(
                {
                    "run/1.0": "run-1.0.json",
                    "run/1.1": "run-1.1.json",
                    "run/1.2": "run-1.2.json",
                }[run["schema_version"]],
                run,
            )
        for bundle in result_bundles.values():
            validate_instance(
                "result-bundle-1.1.json"
                if bundle["schema_version"] == "result-bundle/1.1"
                else "result-bundle-1.0.json",
                bundle,
            )
        for record in evidence.values():
            validate_instance("evidence-1.2.json", record)
        for claim in claims.values():
            validate_instance("claim-1.2.json", claim)
        for hypothesis in hypotheses.values():
            validate_instance("hypothesis-1.0.json", hypothesis)
        for assessment in assessments.values():
            validate_instance(
                "assessment-1.2.json"
                if assessment["schema_version"] == "assessment/1.2"
                else "assessment-1.1.json",
                assessment,
            )
        for decision in decisions.values():
            validate_instance("decision-1.2.json", decision)
        for artifact in artifacts.values():
            validate_instance("artifact-1.0.json", artifact)
        for issue in issues.values():
            validate_instance("issue-1.0.json", issue)
        for deviation in deviations.values():
            validate_instance("deviation-1.0.json", deviation)
        for reproduction in reproduction_records.values():
            validate_instance("reproduction-record-1.0.json", reproduction)
        for result in agent_results.values():
            schema_name = (
                "agent-result-record-1.1.json"
                if result["schema_version"] == "agent-result-record/1.1"
                else "agent-result-record-1.0.json"
            )
            validate_instance(schema_name, result)
        return {
            "programs": programs,
            "protocols": protocols,
            "approvals": approvals,
            "workings": workings,
            "experiments": experiments,
            "runs": runs,
            "result_bundles": result_bundles,
            "evidence": evidence,
            "claims": claims,
            "hypotheses": hypotheses,
            "assessments": assessments,
            "decisions": decisions,
            "artifacts": artifacts,
            "issues": issues,
            "deviations": deviations,
            "reproduction_records": reproduction_records,
            "agent_results": agent_results,
        }

    def replay(self) -> dict[str, Any]:
        return self._project(self.chronicle.events())

    def programs(self) -> dict[str, dict[str, Any]]:
        return self.replay()["programs"]

    def protocols(self) -> dict[str, dict[str, Any]]:
        return self.replay()["protocols"]

    def approvals(self) -> dict[str, dict[str, Any]]:
        return self.replay()["approvals"]

    def workings(self) -> dict[str, dict[str, Any]]:
        return self.replay()["workings"]

    def experiments(self) -> dict[str, dict[str, Any]]:
        return self.replay()["experiments"]

    def runs(self) -> dict[str, dict[str, Any]]:
        return self.replay()["runs"]

    def result_bundles(self) -> dict[str, dict[str, Any]]:
        return self.replay()["result_bundles"]

    def evidence(self) -> dict[str, dict[str, Any]]:
        return self.replay()["evidence"]

    def claims(self) -> dict[str, dict[str, Any]]:
        return self.replay()["claims"]

    def hypotheses(self) -> dict[str, dict[str, Any]]:
        return self.replay()["hypotheses"]

    def assessments(self) -> dict[str, dict[str, Any]]:
        return self.replay()["assessments"]

    def decisions(self) -> dict[str, dict[str, Any]]:
        return self.replay()["decisions"]

    def reproduction_records(self) -> dict[str, dict[str, Any]]:
        return self.replay()["reproduction_records"]

    def artifacts(self) -> dict[str, dict[str, Any]]:
        return self.replay()["artifacts"]

    def issues(self) -> dict[str, dict[str, Any]]:
        return self.replay()["issues"]

    def deviations(self) -> dict[str, dict[str, Any]]:
        return self.replay()["deviations"]

    def agent_results(self) -> dict[str, dict[str, Any]]:
        return self.replay()["agent_results"]

    def create_program(
        self,
        slug: str,
        title: str,
        problem: dict[str, Any] | None = None,
    ) -> tuple[str, Receipt]:
        if not SLUG.fullmatch(slug) or not title.strip():
            raise AthanorError("Program requires a lowercase hyphenated slug and non-empty title")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            programs = self._project(events)["programs"]
            if any(program["slug"] == slug for program in programs.values()):
                raise AthanorError(f"program slug already exists: {slug}")
            program_id = f"RP-{len(programs) + 1:03d}"
            return "program.created", program_id, {
                "slug": slug,
                "title": title,
                "problem": problem or {},
            }

        event, receipt = self.chronicle.transact(build)
        return event["object_id"], receipt

    def record_evidence(
        self,
        evidence_id: str,
        program_id: str,
        source: dict[str, str],
        observation: str,
        verification: dict[str, bool] | None = None,
    ) -> Receipt:
        if (
            not isinstance(evidence_id, str)
            or not IDENTIFIER.fullmatch(evidence_id)
            or not evidence_id.startswith("EV-")
        ):
            raise AthanorError("Evidence ID must use the form EV-<identifier>")
        if (
            not isinstance(source, dict)
            or set(source) != {"uri", "sigil"}
            or not isinstance(source["uri"], str)
            or not source["uri"]
            or not isinstance(source["sigil"], str)
            or not SIGIL.fullmatch(source["sigil"])
        ):
            raise AthanorError("Evidence source must be a content-addressed URI reference")
        if not isinstance(observation, str) or not observation.strip():
            raise AthanorError("Evidence requires a non-empty observation")
        normalized_verification = (
            verification
            if verification is not None
            else {key: False for key in EVIDENCE_VERIFICATION_KEYS}
        )
        allowed_verification_keys = EVIDENCE_VERIFICATION_KEYS | {
            "claim_relation_verified",
            "locally_reproduced",
        }
        if (
            not isinstance(normalized_verification, dict)
            or not set(normalized_verification).issubset(allowed_verification_keys)
            or any(not isinstance(value, bool) for value in normalized_verification.values())
        ):
            raise AthanorError("Evidence verification contains invalid checks")
        if normalized_verification.get(
            "claim_relation_verified"
        ) or normalized_verification.get("locally_reproduced"):
            raise AthanorError(
                "Claim relation and reproduction status require canonical relation objects"
            )
        requested_source_resolution = normalized_verification.get(
            "source_resolved",
            False,
        )
        requested_content_inspection = normalized_verification.get(
            "content_inspected",
            False,
        )
        if requested_content_inspection and not requested_source_resolution:
            raise AthanorError("Evidence content inspection requires source resolution")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if evidence_id in state["evidence"]:
                raise AthanorError(f"Evidence already exists: {evidence_id}")
            return "evidence.recorded", evidence_id, {
                "program_id": program_id,
                "source": source,
                "observation": observation,
            }

        receipt = self.chronicle.transact(build)[1]
        if requested_source_resolution:
            self.resolve_evidence_source(evidence_id)
        if requested_content_inspection:
            self.inspect_evidence_content(evidence_id)
        return receipt

    def resolve_evidence_source(self, evidence_id: str) -> Receipt:
        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            record = self._project(events)["evidence"].get(evidence_id)
            if record is None:
                raise AthanorError(f"unknown Evidence: {evidence_id}")
            if record["verification"]["source_resolved"]:
                raise AthanorError(f"Evidence source is already resolved: {evidence_id}")
            return "evidence.source_resolved", evidence_id, {
                "program_id": record["program_id"],
            }

        return self.chronicle.transact(build)[1]

    def inspect_evidence_content(self, evidence_id: str) -> Receipt:
        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            record = self._project(events)["evidence"].get(evidence_id)
            if record is None:
                raise AthanorError(f"unknown Evidence: {evidence_id}")
            if not record["verification"]["source_resolved"]:
                raise AthanorError(
                    f"Evidence source must be resolved before inspection: {evidence_id}"
                )
            if record["verification"]["content_inspected"]:
                raise AthanorError(f"Evidence content is already inspected: {evidence_id}")
            return "evidence.content_inspected", evidence_id, {
                "program_id": record["program_id"],
            }

        return self.chronicle.transact(build)[1]

    def verify_evidence(self, evidence_id: str, checks: list[str]) -> Receipt:
        requested = set(checks)
        if not requested or not requested.issubset(EVIDENCE_VERIFICATION_KEYS):
            raise AthanorError(
                "Evidence verification supports only source_resolved and content_inspected"
            )
        record = self.evidence().get(evidence_id)
        if record is None:
            raise AthanorError(f"unknown Evidence: {evidence_id}")
        receipts: list[Receipt] = []
        if (
            "source_resolved" in requested
            and not record["verification"]["source_resolved"]
        ):
            receipts.append(self.resolve_evidence_source(evidence_id))
        if (
            "content_inspected" in requested
            and not record["verification"]["content_inspected"]
        ):
            receipts.append(self.inspect_evidence_content(evidence_id))
        if not receipts:
            raise AthanorError(f"Evidence checks are already verified: {evidence_id}")
        return receipts[-1]

    def create_claim(
        self,
        claim_id: str,
        program_id: str,
        claim_type: str,
        statement: str,
        evidence_relations: list[dict[str, str]],
    ) -> Receipt:
        claim_types = {"empirical", "theoretical", "methodological", "operational"}
        if (
            not isinstance(claim_id, str)
            or not IDENTIFIER.fullmatch(claim_id)
            or not claim_id.startswith("CL-")
        ):
            raise AthanorError("Claim ID must use the form CL-<identifier>")
        if claim_type not in claim_types:
            raise AthanorError(f"unknown Claim type: {claim_type}")
        if not isinstance(statement, str) or not statement.strip():
            raise AthanorError("Claim requires a non-empty statement")
        if not evidence_relations or any(
            not isinstance(relation, dict)
            or set(relation) != {"evidence_id", "relation"}
            or not isinstance(relation["evidence_id"], str)
            or not relation["evidence_id"].startswith("EV-")
            or relation["relation"] not in EVIDENCE_RELATIONS
            for relation in evidence_relations
        ):
            raise AthanorError("Claim requires typed Evidence relations")
        if len({relation["evidence_id"] for relation in evidence_relations}) != len(
            evidence_relations
        ):
            raise AthanorError("Claim Evidence relations must be unique")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if claim_id in state["claims"]:
                raise AthanorError(f"Claim already exists: {claim_id}")
            for relation in evidence_relations:
                record = state["evidence"].get(relation["evidence_id"])
                if record is None or record["program_id"] != program_id:
                    raise AthanorError(f"unknown Program Evidence: {relation['evidence_id']}")
            return "claim.created", claim_id, {
                "program_id": program_id,
                "type": claim_type,
                "statement": statement,
            }

        receipt = self.chronicle.transact(build)[1]
        for relation in evidence_relations:
            self.propose_claim_relation(
                claim_id,
                relation["evidence_id"],
                relation["relation"],
            )
        return receipt

    def propose_claim_relation(
        self,
        claim_id: str,
        evidence_id: str,
        relation: str,
    ) -> Receipt:
        if relation not in EVIDENCE_RELATIONS:
            raise AthanorError(f"unknown Evidence relation: {relation}")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            claim = state["claims"].get(claim_id)
            record = state["evidence"].get(evidence_id)
            if (
                claim is None
                or record is None
                or claim["program_id"] != record["program_id"]
            ):
                raise AthanorError("Claim and Evidence must belong to the same Program")
            if any(
                item["evidence_id"] == evidence_id
                for item in claim["evidence_relations"]
            ):
                raise AthanorError(
                    f"Claim relation already exists: {claim_id} -> {evidence_id}"
                )
            return "claim_relation.proposed", claim_id, {
                "program_id": claim["program_id"],
                "evidence_id": evidence_id,
                "relation": relation,
            }

        return self.chronicle.transact(build)[1]

    def verify_claim_relation(self, claim_id: str, evidence_id: str) -> Receipt:
        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            claim = state["claims"].get(claim_id)
            record = state["evidence"].get(evidence_id)
            if (
                claim is None
                or record is None
                or claim["program_id"] != record["program_id"]
            ):
                raise AthanorError("Claim and Evidence must belong to the same Program")
            relation = next(
                (
                    item
                    for item in claim["evidence_relations"]
                    if item["evidence_id"] == evidence_id
                ),
                None,
            )
            if relation is None:
                raise AthanorError(
                    f"Claim relation is not proposed: {claim_id} -> {evidence_id}"
                )
            if relation["status"] == "VERIFIED":
                raise AthanorError(
                    f"Claim relation is already verified: {claim_id} -> {evidence_id}"
                )
            if not (
                record["verification"]["source_resolved"]
                and record["verification"]["content_inspected"]
            ):
                raise AthanorError(
                    f"Claim relation requires resolved and inspected Evidence: {evidence_id}"
                )
            return "claim_relation.verified", claim_id, {
                "program_id": claim["program_id"],
                "evidence_id": evidence_id,
            }

        return self.chronicle.transact(build)[1]

    def create_hypothesis(
        self,
        hypothesis_id: str,
        program_id: str,
        claim_ids: list[str],
        statement: str,
        prediction: str,
    ) -> Receipt:
        if (
            not isinstance(hypothesis_id, str)
            or not IDENTIFIER.fullmatch(hypothesis_id)
            or not hypothesis_id.startswith("HY-")
        ):
            raise AthanorError("Hypothesis ID must use the form HY-<identifier>")
        if (
            not isinstance(claim_ids, list)
            or not claim_ids
            or any(
                not isinstance(claim_id, str) or not claim_id.startswith("CL-")
                for claim_id in claim_ids
            )
            or len(set(claim_ids)) != len(claim_ids)
        ):
            raise AthanorError("Hypothesis requires one or more Claim IDs")
        if (
            not isinstance(statement, str)
            or not statement.strip()
            or not isinstance(prediction, str)
            or not prediction.strip()
        ):
            raise AthanorError("Hypothesis requires a statement and falsifiable prediction")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if hypothesis_id in state["hypotheses"]:
                raise AthanorError(f"Hypothesis already exists: {hypothesis_id}")
            if any(
                claim_id not in state["claims"]
                or state["claims"][claim_id]["program_id"] != program_id
                for claim_id in claim_ids
            ):
                raise AthanorError("Hypothesis Claims must belong to its Research Program")
            return "hypothesis.created", hypothesis_id, {
                "program_id": program_id,
                "claim_ids": claim_ids,
                "statement": statement,
                "prediction": prediction,
            }

        return self.chronicle.transact(build)[1]

    def seal_research_question(
        self,
        program_id: str,
        statement: str,
        actor: dict[str, str] | None = None,
    ) -> Receipt:
        if not isinstance(statement, str) or not statement.strip():
            raise AthanorError("Research Question requires a non-empty statement")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            program = self._project(events)["programs"].get(program_id)
            if program is None:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if program["research_question"] is not None:
                raise AthanorError(f"Research Question is already sealed: {program_id}")
            if not program["hypotheses"]:
                raise AthanorError(
                    "Research Question Seal requires a registered Hypothesis"
                )
            return "research_question.sealed", program_id, {
                "statement": statement,
            }

        return self.chronicle.transact(build, actor=actor)[1]

    def draft_protocol(
        self,
        protocol_id: str,
        program_id: str,
        title: str,
        analysis_plan: str,
        hypothesis_ids: list[str] | None = None,
        study_mode: str | None = None,
        analysis_spec: dict[str, Any] | None = None,
    ) -> Receipt:
        if not IDENTIFIER.fullmatch(protocol_id) or not protocol_id.startswith("PT-"):
            raise AthanorError("Protocol ID must use the form PT-<identifier>")
        if not title.strip() or not analysis_plan.strip():
            raise AthanorError("Protocol requires a title and deterministic analysis plan")

        if hypothesis_ids is not None and not isinstance(hypothesis_ids, list):
            raise AthanorError("Protocol Hypotheses must be a list")
        normalized_hypotheses = hypothesis_ids or []
        study_mode = study_mode or (
            "confirmatory" if normalized_hypotheses else "exploratory"
        )
        if study_mode not in {"confirmatory", "exploratory"}:
            raise AthanorError("Protocol study mode must be confirmatory or exploratory")
        if study_mode == "confirmatory" and not normalized_hypotheses:
            raise AthanorError("confirmatory Protocol requires at least one Hypothesis")
        if any(
            not isinstance(hypothesis_id, str)
            or not hypothesis_id.startswith("HY-")
            for hypothesis_id in normalized_hypotheses
        ):
            raise AthanorError("Protocol Hypotheses must use HY- identifiers")
        if analysis_spec is not None:
            if not isinstance(analysis_spec, dict):
                raise AthanorError("Protocol analysis_spec must be an object")
            from .schema_validation import validate_instance

            validate_instance("analysis-spec-1.0.json", analysis_spec)
            comparisons = analysis_spec["comparisons"]
            comparison_ids = [
                comparison["comparison_id"] for comparison in comparisons
            ]
            if len(comparison_ids) != len(set(comparison_ids)):
                raise AthanorError("Protocol comparison IDs must be unique")
            if any(
                comparison["arms"][0] == comparison["arms"][1]
                for comparison in comparisons
            ):
                raise AthanorError("Protocol comparison arms must be distinct")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if protocol_id in state["protocols"]:
                raise AthanorError(f"Protocol already exists: {protocol_id}")
            if len(set(normalized_hypotheses)) != len(normalized_hypotheses) or any(
                hypothesis_id not in state["hypotheses"]
                or state["hypotheses"][hypothesis_id]["program_id"] != program_id
                for hypothesis_id in normalized_hypotheses
            ):
                raise AthanorError("Protocol Hypotheses must belong to its Research Program")
            payload: dict[str, Any] = {
                "program_id": program_id,
                "study_mode": study_mode,
                "hypothesis_ids": normalized_hypotheses,
                "title": title,
                "analysis_plan": analysis_plan,
            }
            if analysis_spec is not None:
                payload["analysis_spec"] = analysis_spec
            return "protocol.drafted", protocol_id, payload

        return self.chronicle.transact(build)[1]

    def seal_protocol(
        self,
        protocol_id: str,
        actor: dict[str, str] | None = None,
    ) -> Receipt:
        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            protocol = state["protocols"].get(protocol_id)
            if protocol is None or protocol["status"] != "DRAFT":
                raise AthanorError(f"Protocol is not an unsealed draft: {protocol_id}")
            return "protocol.sealed", protocol_id, {
                "program_id": protocol["program_id"],
                "status": "FROZEN",
            }

        return self.chronicle.transact(build, actor=actor)[1]

    def grant_approval(self, capsule: dict[str, Any], reason: str) -> Receipt:
        if not reason.strip():
            raise AthanorError("approval reason cannot be empty")
        required = {"task_id", "capsule_sigil", "capability", "snapshot", "circle"}
        if not required.issubset(capsule):
            raise AthanorError("approval requires a complete verified Task Capsule")
        from .schema_validation import validate_instance

        validate_instance("task-capsule-1.1.json", capsule)
        from .circle import CapabilityRegistry

        capability = capsule["capability"]
        current_contract_sigil = CapabilityRegistry(self.root).contract_sigil(
            capability["id"]
        )
        if current_contract_sigil != capability["contract_sigil"]:
            raise AthanorError("Capability Contract changed after Task creation")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            approvals = self._project(events)["approvals"]
            task_id = capsule["task_id"]
            if task_id in approvals:
                raise AthanorError(f"Task already has an approval: {task_id}")
            return "approval.granted", task_id, {
                "reason": reason,
                "capsule_sigil": capsule["capsule_sigil"],
                "capability": capsule["capability"]["id"],
                "capability_contract_sigil": capsule["capability"]["contract_sigil"],
                "circle": capsule["circle"],
            }

        return self.chronicle.transact(build)[1]

    def accept_agent_result(self, result: dict[str, Any]) -> Receipt:
        from .circle import CapsuleStore, CapabilityRegistry, Ward
        from .schema_validation import validate_instance
        from .snapshots import SnapshotStore

        if not isinstance(result, dict) or result.get("schema_version") != "agent-result/1.1":
            raise AthanorError("Agent Result must use agent-result/1.1")
        validate_instance("agent-result-1.1.json", result)

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            task_id = result["task_id"]
            if task_id in state["agent_results"]:
                raise AthanorError(f"Task already has an accepted Agent Result: {task_id}")
            capsule = CapsuleStore(self.root).get(task_id)
            capability = capsule["capability"]
            snapshot_reference = capsule["snapshot"]
            if result["snapshot_sigil"] != snapshot_reference["snapshot_sigil"]:
                raise AthanorError(
                    "Agent Result Snapshot Sigil does not match its Task Capsule"
                )
            if (
                result["capability_contract_sigil"]
                != capability["contract_sigil"]
            ):
                raise AthanorError(
                    "Agent Result Capability Contract Sigil does not match its Task Capsule"
                )
            registry = CapabilityRegistry(self.root)
            current_contract_sigil = registry.contract_sigil(capability["id"])
            if current_contract_sigil != capability["contract_sigil"]:
                raise AthanorError(
                    "Capability Contract changed after Task creation"
                )
            snapshots = SnapshotStore(self.root)
            snapshot, _ = snapshots.get(
                snapshot_reference["snapshot_id"],
                snapshot_reference["snapshot_sigil"],
            )
            if snapshot["program_id"] != capsule["program_id"]:
                raise AthanorError("Task Capsule and Research Snapshot Program mismatch")
            snapshots.require_fresh(snapshot, state, events)
            ward = Ward(registry, state["approvals"]).evaluate(capsule)
            if ward.status != "PASS":
                raise AthanorError(
                    f"Agent Result cannot be accepted while Ward is {ward.status}"
                )
            expected_schemas = {
                output["schema"] for output in capsule["expected_outputs"]
            }
            provenance = result.get("provenance")
            if (
                provenance is not None
                and "host" in provenance
                and provenance["host"] != capsule["host"]
            ):
                raise AthanorError(
                    "Agent Result provenance Host does not match its Task Capsule"
                )
            for output in result["outputs"]:
                if output["schema"] not in expected_schemas:
                    raise AthanorError(
                        f"Agent Result output schema is not expected: {output['schema']}"
                    )
                uri = Path(output["uri"])
                if uri.is_absolute():
                    raise AthanorError("Agent Result output URI must be project-relative")
                path = (self.root / uri).resolve()
                try:
                    path.relative_to(self.root.resolve())
                except ValueError as error:
                    raise AthanorError(
                        "Agent Result output URI escapes the project"
                    ) from error
                try:
                    blob = path.read_bytes()
                except OSError as error:
                    raise AthanorError(
                        f"Agent Result output is unavailable: {output['uri']}"
                    ) from error
                actual_sigil = "sha256:" + hashlib.sha256(blob).hexdigest()
                if actual_sigil != output["blob_sigil"]:
                    raise AthanorError(
                        f"Agent Result output Blob Sigil mismatch: {output['uri']}"
                    )
                try:
                    document = json.loads(blob)
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise AthanorError(
                        f"Agent Result output is not valid JSON: {output['uri']}"
                    ) from error
                if not isinstance(document, dict):
                    raise AthanorError(
                        f"Agent Result output must be an object: {output['uri']}"
                    )
                schema_name = output["schema"].replace("/", "-") + ".json"
                validate_instance(schema_name, document)
                if document.get("task_id") != task_id:
                    raise AthanorError(
                        f"Agent Result output Task ID mismatch: {output['uri']}"
                    )
            return "agent-result.accepted", task_id, {
                "host": capsule["host"],
                "program_id": capsule["program_id"],
                "capability": capsule["capability"],
                "snapshot": capsule["snapshot"],
                "capsule_sigil": capsule["capsule_sigil"],
                "result": result,
            }

        return self.chronicle.transact(build)[1]

    def create_working(self, rite_id: str, program_id: str, protocol_id: str) -> tuple[str, Receipt]:
        from .rites import RiteRegistry

        rite = RiteRegistry(self.root).get(rite_id)
        rite_sigil = content_sigil(rite)

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            protocol = state["protocols"].get(protocol_id)
            if protocol is None or protocol["status"] != "FROZEN":
                raise AthanorError(f"Working requires a frozen Protocol: {protocol_id}")
            if protocol["program_id"] != program_id:
                raise AthanorError(f"Working Program does not match Protocol: {program_id}")
            working_id = f"WK-{len(state['workings']) + 1:03d}"
            return "working.created", working_id, {
                "rite_id": rite_id,
                "rite_sigil": rite_sigil,
                "rite": rite,
                "program_id": program_id,
                "protocol_id": protocol_id,
            }

        event, receipt = self.chronicle.transact(build)
        return event["object_id"], receipt

    def advance_working(self, working_id: str, reason: str, artifacts: list[dict[str, str]]) -> Receipt:
        del working_id, reason, artifacts
        raise AthanorError(
            "manual Working advancement is deprecated; accept the canonical event "
            "declared by the current Rite exit contract"
        )

    def create_experiment(
        self,
        experiment_id: str,
        program_id: str,
        protocol_id: str,
        question: str,
        hypothesis_id: str | None = None,
    ) -> Receipt:
        if not IDENTIFIER.fullmatch(experiment_id) or not experiment_id.startswith("EX-"):
            raise AthanorError("Experiment ID must use the form EX-<identifier>")
        if hypothesis_id is not None and (
            not IDENTIFIER.fullmatch(hypothesis_id) or not hypothesis_id.startswith("HY-")
        ):
            raise AthanorError("Hypothesis ID must use the form HY-<identifier>")
        if not question.strip():
            raise AthanorError("Experiment requires a non-empty question")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            protocol = state["protocols"].get(protocol_id)
            if protocol is None or protocol["status"] != "FROZEN":
                raise AthanorError(f"Experiment requires a frozen Protocol: {protocol_id}")
            if protocol["program_id"] != program_id:
                raise AthanorError(f"Experiment Program does not match Protocol: {program_id}")
            if experiment_id in state["experiments"]:
                raise AthanorError(f"Experiment already exists: {experiment_id}")
            if hypothesis_id is not None:
                hypothesis = state["hypotheses"].get(hypothesis_id)
                if (
                    hypothesis is None
                    or hypothesis["program_id"] != program_id
                    or hypothesis_id not in protocol["hypothesis_ids"]
                ):
                    raise AthanorError(
                        f"Experiment Hypothesis was not registered by Protocol: {hypothesis_id}"
                    )
            return "experiment.planned", experiment_id, {
                "program_id": program_id,
                "protocol_id": protocol_id,
                "hypothesis_id": hypothesis_id,
                "question": question,
            }

        return self.chronicle.transact(build)[1]

    def transition_experiment(self, experiment_id: str, transition: str) -> Receipt:
        event_types = {
            "implemented": "experiment.implemented",
            "pilot-started": "experiment.pilot_started",
            "pilot-completed": "experiment.pilot_completed",
            "formal-started": "experiment.formal_started",
            "completed": "experiment.completed",
            "cancelled": "experiment.cancelled",
        }
        try:
            event_type = event_types[transition]
        except KeyError as error:
            raise AthanorError(f"unknown Experiment transition: {transition}") from error
        expected_statuses = {
            "implemented": {"PLANNED"},
            "pilot-started": {"IMPLEMENTED"},
            "pilot-completed": {"PILOT_RUNNING"},
            "formal-started": {"PILOT_COMPLETED"},
            "completed": {"FORMAL_RUNNING"},
            "cancelled": {
                "PLANNED",
                "IMPLEMENTED",
                "PILOT_RUNNING",
                "PILOT_COMPLETED",
                "FORMAL_RUNNING",
            },
        }

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            experiment = self._project(events)["experiments"].get(experiment_id)
            if experiment is None:
                raise AthanorError(f"unknown Experiment: {experiment_id}")
            if experiment["status"] not in expected_statuses[transition]:
                raise AthanorError(
                    f"invalid Experiment transition from {experiment['status']}: "
                    f"{transition}"
                )
            return event_type, experiment_id, {
                "program_id": experiment["program_id"],
                "protocol_id": experiment["protocol_id"],
            }

        return self.chronicle.transact(build)[1]

    def record_run(
        self,
        run_id: str,
        experiment_id: str,
        status: str,
        analysis_included: bool,
        metrics: dict[str, float | int] | None = None,
        seed: int | None = None,
        artifacts: list[dict[str, str]] | None = None,
        phase: str = "FORMAL",
        exclusion_reason: str | None = None,
        policy_reference: str | None = None,
        arm: str | None = None,
    ) -> Receipt:
        statuses = {"COMPLETED", "FAILED", "CANCELLED", "LOST"}
        if not IDENTIFIER.fullmatch(run_id) or not run_id.startswith("RUN-"):
            raise AthanorError("Run ID must use the form RUN-<identifier>")
        if status not in statuses:
            raise AthanorError(
                f"Run status must be terminal ({', '.join(sorted(statuses))}): {status}"
            )
        if phase not in {"PILOT", "FORMAL"}:
            raise AthanorError("Run phase must be PILOT or FORMAL")
        if analysis_included and status != "COMPLETED":
            raise AthanorError("only a completed Run can be included in analysis")
        if status == "COMPLETED" and not analysis_included and (
            not isinstance(exclusion_reason, str) or not exclusion_reason.strip()
        ):
            raise AthanorError("an excluded completed Run requires an exclusion reason")
        if exclusion_reason is not None and (
            not isinstance(exclusion_reason, str) or not exclusion_reason.strip()
        ):
            raise AthanorError("Run exclusion reason must be a non-empty string")
        if analysis_included and exclusion_reason is not None:
            raise AthanorError("an included Run cannot have an exclusion reason")
        if policy_reference is not None and (
            not isinstance(policy_reference, str) or "#" not in policy_reference
        ):
            raise AthanorError("Run policy reference must identify a Protocol section")
        if arm is not None and (not isinstance(arm, str) or not arm.strip()):
            raise AthanorError("Run arm must be a non-empty string")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise AthanorError("Run seed must be an integer or null")
        if metrics is not None and not isinstance(metrics, dict):
            raise AthanorError("Run metrics must be a name-to-number object")
        normalized_metrics = metrics or {}
        if analysis_included and not normalized_metrics:
            raise AthanorError("an included Run requires at least one metric")
        if any(
            not isinstance(name, str)
            or not name.strip()
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for name, value in normalized_metrics.items()
        ):
            raise AthanorError("Run metrics require non-empty names and finite numeric values")
        normalized_artifacts = artifacts or []
        if any(
            not isinstance(artifact, dict)
            or set(artifact) != {"uri", "sigil"}
            or not isinstance(artifact["uri"], str)
            or not artifact["uri"]
            or not isinstance(artifact["sigil"], str)
            or not SIGIL.fullmatch(artifact["sigil"])
            for artifact in normalized_artifacts
        ):
            raise AthanorError("Run artifacts must be content-addressed URI references")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            experiment = state["experiments"].get(experiment_id)
            if experiment is None:
                raise AthanorError(f"unknown Experiment: {experiment_id}")
            if run_id in state["runs"]:
                raise AthanorError(f"Run already exists: {run_id}")
            protocol = state["protocols"][experiment["protocol_id"]]
            if protocol.get("analysis_spec") is not None and arm is None:
                raise AthanorError(
                    "Run arm is required by the Protocol analysis_spec"
                )
            reference = policy_reference or f"{experiment['protocol_id']}#analysis-plan"
            if not reference.startswith(f"{experiment['protocol_id']}#"):
                raise AthanorError(
                    "Run policy reference must belong to the Experiment Protocol"
                )
            payload = {
                "program_id": experiment["program_id"],
                "protocol_id": experiment["protocol_id"],
                "experiment_id": experiment_id,
                "phase": phase,
                "status": status,
                "analysis_disposition": {
                    "included": analysis_included,
                    "reason": exclusion_reason,
                    "policy_reference": reference,
                },
                "seed": seed,
                "metrics": normalized_metrics,
                "artifacts": normalized_artifacts,
            }
            if arm is not None:
                payload["arm"] = arm
            return "run.recorded", run_id, payload

        return self.chronicle.transact(build)[1]

    def compute_analysis(
        self, program_id: str, protocol_id: str
    ) -> tuple[dict[str, Any], str, Receipt, Path]:
        from .alembic import build_result_bundle, export_result_bundle

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            protocol = state["protocols"].get(protocol_id)
            if protocol is None or protocol["program_id"] != program_id:
                raise AthanorError(f"Protocol {protocol_id} does not belong to Program {program_id}")
            if protocol.get("analysis_spec") is None:
                raise AthanorError(
                    "Alembic v1.1 requires a Protocol with a registered analysis_spec"
                )
            for comparison in protocol["analysis_spec"]["comparisons"]:
                experiment = state["experiments"].get(comparison["experiment_id"])
                if (
                    experiment is None
                    or experiment["program_id"] != program_id
                    or experiment["protocol_id"] != protocol_id
                ):
                    raise AthanorError(
                        "Protocol comparison references an unknown matching Experiment: "
                        f"{comparison['experiment_id']}"
                    )
            bundle_id = f"RB-{len(state['result_bundles']) + 1:03d}"
            bundle = build_result_bundle(
                bundle_id,
                protocol,
                list(state["runs"].values()),
            )
            return "analysis.computed", bundle_id, {
                "bundle": bundle,
                "bundle_sigil": content_sigil(bundle),
            }

        event, receipt = self.chronicle.transact(build)
        bundle = event["payload"]["bundle"]
        path = export_result_bundle(self.root, bundle)
        return bundle, event["payload"]["bundle_sigil"], receipt, path

    def review_result(
        self,
        result_bundle_id: str,
        summary: str,
        limitations: list[str],
        claim_findings: list[dict[str, str]],
        hypothesis_findings: list[dict[str, str]],
    ) -> tuple[str, Receipt]:
        claim_statuses = {"SUPPORTED", "CONTESTED", "REJECTED", "UNRESOLVED"}
        hypothesis_statuses = {"SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE", "REJECTED"}
        if not isinstance(summary, str) or not summary.strip():
            raise AthanorError("Assessment requires a non-empty summary")
        if not isinstance(limitations, list) or any(
            not isinstance(item, str) or not item.strip() for item in limitations
        ):
            raise AthanorError("Assessment limitations must be non-empty strings")
        if not isinstance(claim_findings, list) or any(
            not isinstance(finding, dict)
            or set(finding) != {"claim_id", "status", "rationale"}
            or not isinstance(finding["claim_id"], str)
            or not finding["claim_id"].startswith("CL-")
            or finding["status"] not in claim_statuses
            or not isinstance(finding["rationale"], str)
            or not finding["rationale"].strip()
            for finding in claim_findings
        ):
            raise AthanorError("Assessment Claim findings are invalid")
        if (
            len({finding["claim_id"] for finding in claim_findings})
            != len(claim_findings)
        ):
            raise AthanorError("Assessment Claim findings must be unique")
        if not isinstance(hypothesis_findings, list) or any(
            not isinstance(finding, dict)
            or set(finding) != {"hypothesis_id", "status", "rationale"}
            or not isinstance(finding["hypothesis_id"], str)
            or not finding["hypothesis_id"].startswith("HY-")
            or finding["status"] not in hypothesis_statuses
            or not isinstance(finding["rationale"], str)
            or not finding["rationale"].strip()
            for finding in hypothesis_findings
        ):
            raise AthanorError("Assessment requires valid Hypothesis findings")
        if (
            len({finding["hypothesis_id"] for finding in hypothesis_findings})
            != len(hypothesis_findings)
        ):
            raise AthanorError("Assessment Hypothesis findings must be unique")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            bundle = state["result_bundles"].get(result_bundle_id)
            if bundle is None:
                raise AthanorError(f"unknown Result Bundle: {result_bundle_id}")
            for finding in claim_findings:
                claim = state["claims"].get(finding["claim_id"])
                if claim is None or claim["program_id"] != bundle["program_id"]:
                    raise AthanorError(f"unknown Program Claim: {finding['claim_id']}")
            protocol = state["protocols"][bundle["protocol_id"]]
            study_mode = protocol.get("study_mode", "confirmatory")
            if study_mode == "confirmatory" and not hypothesis_findings:
                raise AthanorError(
                    "confirmatory Assessment requires at least one Hypothesis finding"
                )
            for finding in hypothesis_findings:
                hypothesis = state["hypotheses"].get(finding["hypothesis_id"])
                if (
                    hypothesis is None
                    or hypothesis["program_id"] != bundle["program_id"]
                    or finding["hypothesis_id"] not in protocol["hypothesis_ids"]
                ):
                    raise AthanorError(
                        f"Hypothesis was not registered by Protocol: {finding['hypothesis_id']}"
                    )
            assessment_id = f"AS-{len(state['assessments']) + 1:03d}"
            return "assessment.recorded", assessment_id, {
                "program_id": bundle["program_id"],
                "protocol_id": bundle["protocol_id"],
                "study_mode": study_mode,
                "result_bundle_id": result_bundle_id,
                "summary": summary,
                "limitations": limitations,
                "claim_findings": claim_findings,
                "hypothesis_findings": hypothesis_findings,
            }

        event, receipt = self.chronicle.transact(build)
        return event["object_id"], receipt

    def close_program(self, program_id: str) -> Receipt:
        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            program = self._project(events)["programs"].get(program_id)
            if program is None:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if program["status"] != "EVALUATED" or not program["decisions"]:
                raise AthanorError(
                    "Program closure requires an evaluated Program with a sealed Decision"
                )
            return "program.closed", program_id, {}

        return self.chronicle.transact(build)[1]

    def record_reproduction(
        self,
        reproduction_id: str,
        evidence_id: str,
        run_ids: list[str],
        result_bundle_id: str,
        artifact_ids: list[str],
        assessment_id: str,
        status: str,
    ) -> Receipt:
        if (
            not IDENTIFIER.fullmatch(reproduction_id)
            or not reproduction_id.startswith("RR-")
        ):
            raise AthanorError("Reproduction ID must use the form RR-<identifier>")
        if status not in {"REPRODUCED", "NOT_REPRODUCED", "INCONCLUSIVE"}:
            raise AthanorError(f"unknown Reproduction status: {status}")
        if (
            not run_ids
            or len(set(run_ids)) != len(run_ids)
            or not artifact_ids
            or len(set(artifact_ids)) != len(artifact_ids)
        ):
            raise AthanorError(
                "Reproduction requires unique Runs and canonical Artifacts"
            )

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if reproduction_id in state["reproduction_records"]:
                raise AthanorError(
                    f"Reproduction Record already exists: {reproduction_id}"
                )
            evidence = state["evidence"].get(evidence_id)
            if evidence is None:
                raise AthanorError(f"unknown Evidence: {evidence_id}")
            program_id = evidence["program_id"]
            if (
                any(
                    run_id not in state["runs"]
                    or state["runs"][run_id]["program_id"] != program_id
                    for run_id in run_ids
                )
                or result_bundle_id not in state["result_bundles"]
                or state["result_bundles"][result_bundle_id]["program_id"]
                != program_id
                or any(
                    artifact_id not in state["artifacts"]
                    or state["artifacts"][artifact_id]["program_id"] != program_id
                    for artifact_id in artifact_ids
                )
                or assessment_id not in state["assessments"]
                or state["assessments"][assessment_id]["program_id"] != program_id
            ):
                raise AthanorError(
                    "Reproduction references must be canonical objects in one Program"
                )
            return "reproduction.assessed", reproduction_id, {
                "program_id": program_id,
                "evidence_id": evidence_id,
                "run_ids": run_ids,
                "result_bundle_id": result_bundle_id,
                "artifact_ids": artifact_ids,
                "assessment_id": assessment_id,
                "status": status,
            }

        return self.chronicle.transact(build)[1]

    def seal_decision(
        self,
        program_id: str,
        outcome: str,
        assessment_ids: list[str],
        rationale: str,
        required_actions: list[str] | None = None,
        lineage: dict[str, str] | None = None,
        actor: dict[str, str] | None = None,
    ) -> tuple[str, Receipt]:
        outcomes = {
            "CONTINUE",
            "REPAIR",
            "PIVOT",
            "STOP",
            "INSUFFICIENT_EVIDENCE",
            "REVIEW_REQUIRED",
        }
        if outcome not in outcomes:
            raise AthanorError(f"unknown Decision outcome: {outcome}")
        if (
            not isinstance(assessment_ids, list)
            or not assessment_ids
            or any(
                not isinstance(assessment_id, str)
                or not assessment_id.startswith("AS-")
                for assessment_id in assessment_ids
            )
            or len(set(assessment_ids)) != len(assessment_ids)
        ):
            raise AthanorError("Decision requires unique Assessment IDs")
        if not isinstance(rationale, str) or not rationale.strip():
            raise AthanorError("Decision requires a non-empty rationale")
        normalized_actions = required_actions or []
        if any(
            not isinstance(action, str) or not action.strip()
            for action in normalized_actions
        ):
            raise AthanorError("Decision required actions must be non-empty strings")
        if outcome == "REPAIR" and not normalized_actions:
            raise AthanorError("REPAIR requires one or more required actions")
        if outcome == "PIVOT" and (
            not isinstance(lineage, dict)
            or set(lineage) != {"parent_program_id", "reason"}
            or lineage.get("parent_program_id") != program_id
            or not isinstance(lineage.get("reason"), str)
            or not lineage["reason"].strip()
        ):
            raise AthanorError("PIVOT requires Program lineage metadata")
        if outcome != "PIVOT" and lineage is not None:
            raise AthanorError("Decision lineage is only valid for PIVOT")
        if outcome == "REVIEW_REQUIRED" and len(assessment_ids) < 2:
            raise AthanorError(
                "REVIEW_REQUIRED must preserve at least two competing Assessments"
            )

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if any(
                assessment_id not in state["assessments"]
                or state["assessments"][assessment_id]["program_id"] != program_id
                or state["assessments"][assessment_id]["status"] != "COMPLETE"
                for assessment_id in assessment_ids
            ):
                raise AthanorError(
                    "Decision Assessments must be complete and belong to the Program"
                )
            open_issues = sorted(
                issue_id
                for issue_id, issue in state["issues"].items()
                if issue["program_id"] == program_id and issue["status"] == "OPEN"
            )
            if outcome == "CONTINUE" and any(
                state["issues"][issue_id]["severity"] == "CRITICAL"
                for issue_id in open_issues
            ):
                raise AthanorError(
                    "CONTINUE is blocked by an unresolved CRITICAL Issue"
                )
            unresolved_uncertainties = sorted(
                {
                    limitation
                    for assessment_id in assessment_ids
                    for limitation in state["assessments"][assessment_id][
                        "limitations"
                    ]
                }
            )
            decision_id = f"DE-{len(state['decisions']) + 1:03d}"
            return "decision.sealed", decision_id, {
                "program_id": program_id,
                "outcome": outcome,
                "assessment_ids": assessment_ids,
                "rationale": rationale,
                "required_actions": normalized_actions,
                "lineage": lineage,
                "unresolved_issue_ids": open_issues,
                "unresolved_uncertainties": unresolved_uncertainties,
            }

        event, receipt = self.chronicle.transact(build, actor=actor)
        return event["object_id"], receipt

    def register_artifact(
        self,
        artifact_id: str,
        program_id: str,
        kind: str,
        location: dict[str, str],
        producer_id: str,
        input_ids: list[str] | None = None,
    ) -> Receipt:
        normalized_inputs = [] if input_ids is None else input_ids
        if (
            not isinstance(artifact_id, str)
            or not IDENTIFIER.fullmatch(artifact_id)
            or not artifact_id.startswith("AR-")
        ):
            raise AthanorError("Artifact ID must use the form AR-<identifier>")
        if not isinstance(kind, str) or not kind.strip():
            raise AthanorError("Artifact requires a non-empty kind")
        if (
            not isinstance(location, dict)
            or set(location) != {"uri", "sigil"}
            or not isinstance(location["uri"], str)
            or not location["uri"].strip()
            or not isinstance(location["sigil"], str)
            or not SIGIL.fullmatch(location["sigil"])
        ):
            raise AthanorError("Artifact location must be a content-addressed URI reference")
        if not isinstance(producer_id, str) or not producer_id:
            raise AthanorError("Artifact requires a producer object")
        if (
            not isinstance(normalized_inputs, list)
            or any(not isinstance(input_id, str) or not input_id for input_id in normalized_inputs)
            or len(set(normalized_inputs)) != len(normalized_inputs)
        ):
            raise AthanorError("Artifact input IDs must be unique object references")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if artifact_id in state["artifacts"]:
                raise AthanorError(f"Artifact already exists: {artifact_id}")
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            for reference_id in [producer_id, *normalized_inputs]:
                if _state_object_program_id(state, reference_id) != program_id:
                    raise AthanorError(
                        f"Artifact reference does not belong to Program {program_id}: {reference_id}"
                    )
            artifact_path = (self.root / location["uri"]).resolve()
            try:
                artifact_path.relative_to(self.root.resolve())
            except ValueError as error:
                raise AthanorError("Artifact location URI escapes the project") from error
            try:
                artifact_blob = artifact_path.read_bytes()
            except OSError as error:
                raise AthanorError(
                    f"Artifact location cannot be read: {location['uri']}"
                ) from error
            actual_sigil = "sha256:" + hashlib.sha256(artifact_blob).hexdigest()
            if actual_sigil != location["sigil"]:
                raise AthanorError(
                    f"Artifact location Sigil mismatch: {location['uri']}"
                )
            return "artifact.registered", artifact_id, {
                "program_id": program_id,
                "kind": kind,
                "location": location,
                "producer_id": producer_id,
                "input_ids": normalized_inputs,
            }

        return self.chronicle.transact(build)[1]

    def open_issue(
        self,
        issue_id: str,
        program_id: str,
        subject_ids: list[str],
        severity: str,
        title: str,
        description: str,
    ) -> Receipt:
        if (
            not isinstance(issue_id, str)
            or not IDENTIFIER.fullmatch(issue_id)
            or not issue_id.startswith("IS-")
        ):
            raise AthanorError("Issue ID must use the form IS-<identifier>")
        if severity not in ISSUE_SEVERITIES:
            raise AthanorError(f"unknown Issue severity: {severity}")
        if not isinstance(title, str) or not title.strip():
            raise AthanorError("Issue requires a non-empty title")
        if not isinstance(description, str) or not description.strip():
            raise AthanorError("Issue requires a non-empty description")
        if (
            not isinstance(subject_ids, list)
            or not subject_ids
            or any(not isinstance(subject_id, str) or not subject_id for subject_id in subject_ids)
            or len(set(subject_ids)) != len(subject_ids)
        ):
            raise AthanorError("Issue requires unique subject object IDs")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if issue_id in state["issues"]:
                raise AthanorError(f"Issue already exists: {issue_id}")
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            for subject_id in subject_ids:
                if _state_object_program_id(state, subject_id) != program_id:
                    raise AthanorError(
                        f"Issue subject does not belong to Program {program_id}: {subject_id}"
                    )
            return "issue.opened", issue_id, {
                "program_id": program_id,
                "subject_ids": subject_ids,
                "severity": severity,
                "title": title,
                "description": description,
            }

        return self.chronicle.transact(build)[1]

    def resolve_issue(self, issue_id: str, resolution: str) -> Receipt:
        if not isinstance(resolution, str) or not resolution.strip():
            raise AthanorError("Issue resolution cannot be empty")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            issue = self._project(events)["issues"].get(issue_id)
            if issue is None:
                raise AthanorError(f"unknown Issue: {issue_id}")
            if issue["status"] != "OPEN":
                raise AthanorError(f"Issue is not open: {issue_id}")
            return "issue.resolved", issue_id, {
                "program_id": issue["program_id"],
                "resolution": resolution,
            }

        return self.chronicle.transact(build)[1]

    def record_deviation(
        self,
        deviation_id: str,
        protocol_id: str,
        kind: str,
        summary: str,
        rationale: str,
        impact: str,
        affected_object_ids: list[str] | None = None,
    ) -> Receipt:
        normalized_affected = [] if affected_object_ids is None else affected_object_ids
        if (
            not isinstance(deviation_id, str)
            or not IDENTIFIER.fullmatch(deviation_id)
            or not deviation_id.startswith("DV-")
        ):
            raise AthanorError("Deviation ID must use the form DV-<identifier>")
        if kind not in DEVIATION_KINDS:
            raise AthanorError(f"unknown Deviation kind: {kind}")
        if impact not in DEVIATION_IMPACTS:
            raise AthanorError(f"unknown Deviation impact: {impact}")
        if not isinstance(summary, str) or not summary.strip():
            raise AthanorError("Deviation requires a non-empty summary")
        if not isinstance(rationale, str) or not rationale.strip():
            raise AthanorError("Deviation requires a non-empty rationale")
        if (
            not isinstance(normalized_affected, list)
            or any(
                not isinstance(object_id, str) or not object_id
                for object_id in normalized_affected
            )
            or len(set(normalized_affected)) != len(normalized_affected)
        ):
            raise AthanorError("Deviation affected object IDs must be unique")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            protocol = state["protocols"].get(protocol_id)
            if protocol is None or protocol["status"] != "FROZEN":
                raise AthanorError(f"Deviation requires a frozen Protocol: {protocol_id}")
            if deviation_id in state["deviations"]:
                raise AthanorError(f"Deviation already exists: {deviation_id}")
            for affected_id in normalized_affected:
                if _state_object_program_id(state, affected_id) != protocol["program_id"]:
                    raise AthanorError(
                        "Deviation affected objects must belong to the Protocol Program: "
                        f"{affected_id}"
                    )
            return "deviation.recorded", deviation_id, {
                "program_id": protocol["program_id"],
                "protocol_id": protocol_id,
                "kind": kind,
                "summary": summary,
                "rationale": rationale,
                "impact": impact,
                "affected_object_ids": normalized_affected,
            }

        return self.chronicle.transact(build)[1]

    def trace(self, object_id: str) -> list[dict[str, Any]]:
        def contains(value: Any) -> bool:
            if value == object_id:
                return True
            if isinstance(value, dict):
                return any(contains(item) for item in value.values())
            if isinstance(value, list):
                return any(contains(item) for item in value)
            return False

        return [
            event
            for event in self.chronicle.events()
            if event["object_id"] == object_id or contains(event["payload"])
        ]
