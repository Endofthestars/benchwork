"""Local pre-conformance execution and storage primitives.

This module deliberately owns operational state only.  It never appends a
Chronicle event, creates an Artifact, or interprets an executable command.
The public executor API can therefore submit, observe, cancel, and derive an
outcome without turning MCP into a generic command runner.

The wire values in this module intentionally use the ``benchwork-local-*``
namespace.  RFC-0012 through RFC-0015 reserve their published ``*/1.0``
contract identifiers for the complete schema family and conformance suite;
this pre-conformance foundation must not impersonate those contracts.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .athanor import AthanorError, _exclusive_lock, canonical_json, content_sigil


SIGIL = re.compile(r"^sha256:[0-9a-f]{64}$")
JOB_ID = re.compile(r"^JB-[A-F0-9]{64}$")
SPECIFICATION_ID = re.compile(r"^ES-[A-Z0-9][A-Z0-9._-]*$")
MAX_PAGE_SIZE = 256
TERMINAL_STATES = frozenset(
    {
        "SUCCEEDED",
        "FAILED",
        "CANCELLED",
        "TIMED_OUT",
        "POLICY_VIOLATION",
        "LEASE_EXPIRED",
        "LOST",
        "FENCED",
        "REJECTED",
    }
)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(canonical_json(value))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class LocalBlobStore:
    """The built-in Phase 3 content-addressed backend.

    Bytes are never accepted as canonical Artifacts here.  A successful import
    produces only an operational Blob and immutable local Replica metadata.
    """

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.path = self.root / ".benchwork" / "storage"
        self._lock_path = self.path / "locks" / "storage.lock"

    def initialize(self) -> None:
        with _exclusive_lock(self._lock_path):
            for name in ("records", "blobs", "staging", "quarantine", "locks", "recovery"):
                (self.path / name).mkdir(parents=True, exist_ok=True)
            format_path = self.path / "format.json"
            expected = {
                "schema_version": "benchwork-local-artifact-storage-format/0.1",
                "backend_id": "BE-LOCAL-V1",
                "layout": "BENCHWORK_LOCAL_STORAGE_V1",
            }
            if format_path.exists():
                try:
                    actual = json.loads(format_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as error:
                    raise AthanorError("managed storage format is invalid") from error
                if actual != expected:
                    raise AthanorError("managed storage format is incompatible")
            else:
                _atomic_json(format_path, expected)

    @staticmethod
    def _sigil_for_bytes(value: bytes) -> str:
        return "sha256:" + hashlib.sha256(value).hexdigest()

    def _blob_path(self, sigil: str) -> Path:
        if not isinstance(sigil, str) or not SIGIL.fullmatch(sigil):
            raise AthanorError("Blob Sigil must be canonical sha256")
        return self.path / "blobs" / sigil.removeprefix("sha256:")

    def import_bytes(self, value: bytes, *, media_type: str = "application/octet-stream") -> dict[str, Any]:
        """Commit one immutable Blob, deduplicating only after independent readback."""
        if not isinstance(value, bytes):
            raise AthanorError("Blob import requires bytes")
        if not isinstance(media_type, str) or not media_type or len(media_type) > 128:
            raise AthanorError("Blob media type is invalid")
        self.initialize()
        sigil = self._sigil_for_bytes(value)
        blob_path = self._blob_path(sigil)
        with _exclusive_lock(self._lock_path):
            if blob_path.exists():
                existing = blob_path.read_bytes()
                if self._sigil_for_bytes(existing) != sigil or len(existing) != len(value):
                    raise AthanorError("Blob collision or storage integrity failure")
            else:
                _atomic_bytes(blob_path, value)
                readback = blob_path.read_bytes()
                if self._sigil_for_bytes(readback) != sigil or len(readback) != len(value):
                    blob_path.unlink(missing_ok=True)
                    raise AthanorError("Blob readback verification failed")
            record = {
                "schema_version": "benchwork-local-artifact-blob/0.1",
                "blob_sigil": sigil,
                "size_bytes": len(value),
                "media_type": media_type,
                "backend_id": "BE-LOCAL-V1",
                "availability": "AVAILABLE",
            }
            record["record_sigil"] = content_sigil(record)
            record_path = self.path / "records" / f"blob-{sigil.removeprefix('sha256:')}.json"
            if record_path.exists():
                prior = json.loads(record_path.read_text(encoding="utf-8"))
                if prior["blob_sigil"] != sigil or prior["size_bytes"] != len(value):
                    raise AthanorError("Blob record conflict")
            else:
                _atomic_json(record_path, record)
            return record

    def read_bytes(self, sigil: str) -> bytes:
        self.initialize()
        blob_path = self._blob_path(sigil)
        try:
            value = blob_path.read_bytes()
        except OSError as error:
            raise AthanorError(f"Blob is unavailable: {sigil}") from error
        if self._sigil_for_bytes(value) != sigil:
            raise AthanorError(f"Blob integrity failure: {sigil}")
        return value


class ExecutionService:
    """Durable, non-executing local executor control plane.

    The worker-facing adapter is intentionally separate.  This service only
    records typed Jobs and terminal observations; no request field can carry a
    command, a path to execute, a shell, credentials, or arbitrary backend
    configuration.
    """

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.path = self.root / ".benchwork" / "execution"
        self._journal_path = self.path / "journal.jsonl"
        self._head_path = self.path / "journal-head.json"
        self._lock_path = self.path / "locks" / "execution.lock"

    def initialize(self) -> None:
        with _exclusive_lock(self._lock_path):
            self.path.mkdir(parents=True, exist_ok=True)
            (self.path / "locks").mkdir(parents=True, exist_ok=True)
            if not self._journal_path.exists():
                self._journal_path.touch()
            events = self._events_unlocked()
            if not events:
                instance_id = f"XI-{uuid4().hex.upper()}"
                build_sigil = content_sigil(
                    {"schema_version": "benchwork-executor-build/1.0", "implementation": "local-v1"}
                )
                self._append_unlocked(
                    "executor.epoch-started",
                    {
                        "executor_instance_id": instance_id,
                        "executor_epoch": 1,
                        "executor_build_sigil": build_sigil,
                    },
                )
            else:
                self._write_head_unlocked(events)

    def _events_unlocked(self) -> list[dict[str, Any]]:
        if not self._journal_path.exists():
            return []
        events: list[dict[str, Any]] = []
        previous: str | None = None
        for line_number, line in enumerate(self._journal_path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise AthanorError(f"execution journal contains invalid JSON at line {line_number}") from error
            if not isinstance(event, dict) or set(event) != {
                "schema_version",
                "journal_id",
                "event_id",
                "sequence",
                "event_type",
                "recorded_at",
                "previous_event_sigil",
                "payload",
                "event_sigil",
            }:
                raise AthanorError("execution journal Event shape is invalid")
            if event["schema_version"] != "benchwork-local-execution-journal-event/0.1":
                raise AthanorError("execution journal Event version is invalid")
            if event["sequence"] != len(events) + 1 or event["previous_event_sigil"] != previous:
                raise AthanorError("execution journal chain is broken")
            expected = content_sigil({key: value for key, value in event.items() if key != "event_sigil"})
            if event["event_sigil"] != expected:
                raise AthanorError("execution journal Event Sigil is invalid")
            events.append(event)
            previous = event["event_sigil"]
        return events

    def _write_head_unlocked(self, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        head = {
            "schema_version": "benchwork-local-execution-journal-head/0.1",
            "journal_id": "EJ-LOCAL-V1",
            "last_sequence": events[-1]["sequence"],
            "last_event_id": events[-1]["event_id"],
            "last_event_sigil": events[-1]["event_sigil"],
            "updated_at": _utc_now(),
        }
        head["head_sigil"] = content_sigil(head)
        _atomic_json(self._head_path, head)

    def _append_unlocked(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        events = self._events_unlocked()
        if event_type not in {
            "executor.epoch-started",
            "job.submitted",
            "job.queued",
            "job.cancellation_requested",
            "job.cancellation_observed",
            "job.terminal",
        }:
            raise AthanorError(f"unsupported execution Event type: {event_type}")
        sequence = len(events) + 1
        event = {
            "schema_version": "benchwork-local-execution-journal-event/0.1",
            "journal_id": "EJ-LOCAL-V1",
            "event_id": f"JE-{sequence:016X}-{uuid4().hex[:16].upper()}",
            "sequence": sequence,
            "event_type": event_type,
            "recorded_at": _utc_now(),
            "previous_event_sigil": events[-1]["event_sigil"] if events else None,
            "payload": payload,
        }
        event["event_sigil"] = content_sigil(event)
        with self._journal_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(event))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._write_head_unlocked([*events, event])
        return event

    @staticmethod
    def _validate_specification(specification: dict[str, Any]) -> None:
        required = {"schema_version", "specification_id", "task_binding", "specification_sigil"}
        if not isinstance(specification, dict) or not required.issubset(specification):
            raise AthanorError("execution specification is incomplete")
        if specification["schema_version"] != "benchwork-local-execution-specification/0.1":
            raise AthanorError("execution specification version is invalid")
        if not isinstance(specification["specification_id"], str) or not SPECIFICATION_ID.fullmatch(
            specification["specification_id"]
        ):
            raise AthanorError("execution specification ID is invalid")
        task = specification["task_binding"]
        if not isinstance(task, dict) or set(task) != {"task_id", "task_capsule_sigil"}:
            raise AthanorError("execution specification Task binding is invalid")
        if not isinstance(task["task_id"], str) or not task["task_id"]:
            raise AthanorError("execution specification Task ID is invalid")
        if not isinstance(task["task_capsule_sigil"], str) or not SIGIL.fullmatch(task["task_capsule_sigil"]):
            raise AthanorError("execution specification Task Sigil is invalid")
        if not isinstance(specification["specification_sigil"], str) or not SIGIL.fullmatch(
            specification["specification_sigil"]
        ):
            raise AthanorError("execution specification Sigil is invalid")
        expected = content_sigil(
            {key: value for key, value in specification.items() if key != "specification_sigil"}
        )
        if specification["specification_sigil"] != expected:
            raise AthanorError("execution specification Sigil mismatch")

    @staticmethod
    def _job_id(specification: dict[str, Any], idempotency_key: str) -> tuple[str, str]:
        if not isinstance(idempotency_key, str) or not idempotency_key or len(idempotency_key) > 256:
            raise AthanorError("Start idempotency key is invalid")
        if "\x00" in idempotency_key:
            raise AthanorError("Start idempotency key is invalid")
        key_sigil = content_sigil(["execution-start-idempotency-key/1.0", idempotency_key])
        identity = canonical_json(
            ["execution-job-id/1.0", specification["task_binding"]["task_id"], key_sigil]
        ).encode("utf-8")
        return "JB-" + hashlib.sha256(identity).hexdigest().upper(), key_sigil

    @staticmethod
    def _project(events: list[dict[str, Any]]) -> dict[str, Any]:
        if not events or events[0]["event_type"] != "executor.epoch-started":
            raise AthanorError("execution journal has no executor epoch")
        executor = dict(events[0]["payload"])
        jobs: dict[str, dict[str, Any]] = {}
        starts: dict[tuple[str, str], tuple[str, str]] = {}
        cancellations: dict[tuple[str, str], str] = {}
        for event in events[1:]:
            payload = event["payload"]
            event_type = event["event_type"]
            if event_type == "job.submitted":
                job_id = payload.get("job_id")
                task_id = payload.get("task_id")
                key_sigil = payload.get("idempotency_key_sigil")
                if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id) or job_id in jobs:
                    raise AthanorError("invalid or duplicate execution Job")
                if not isinstance(task_id, str) or not isinstance(key_sigil, str):
                    raise AthanorError("execution Job idempotency binding is invalid")
                scope = (task_id, key_sigil)
                request_sigil = payload.get("start_request_sigil")
                if scope in starts:
                    raise AthanorError("duplicate execution Job idempotency binding")
                starts[scope] = (job_id, request_sigil)
                jobs[job_id] = {
                    "job_id": job_id,
                    "job_binding_sigil": payload["job_binding_sigil"],
                    "task_id": task_id,
                    "specification_id": payload["specification"]["specification_id"],
                    "specification_sigil": payload["specification"]["specification_sigil"],
                    "state": "SUBMITTED",
                    "revision": 1,
                    "submitted_event_id": event["event_id"],
                    "terminal_event_id": None,
                    "terminal_event_sigil": None,
                    "terminal_reason": None,
                    "start_request_sigil": request_sigil,
                    "idempotency_key_sigil": key_sigil,
                }
            elif event_type == "job.queued":
                job = jobs.get(payload.get("job_id"))
                if job is None or job["state"] != "SUBMITTED":
                    raise AthanorError("invalid execution Job queue transition")
                job["state"] = "QUEUED"
                job["revision"] += 1
            elif event_type == "job.cancellation_requested":
                job = jobs.get(payload.get("job_id"))
                key = payload.get("idempotency_key_sigil")
                if job is None or not isinstance(key, str):
                    raise AthanorError("invalid execution Job cancellation")
                scope = (job["job_id"], key)
                if scope in cancellations:
                    raise AthanorError("duplicate execution cancellation binding")
                cancellations[scope] = event["event_sigil"]
                if job["state"] in TERMINAL_STATES:
                    raise AthanorError("terminal Job cannot receive cancellation request")
                job["state"] = "CANCEL_REQUESTED"
                job["revision"] += 1
            elif event_type == "job.cancellation_observed":
                job = jobs.get(payload.get("job_id"))
                key = payload.get("idempotency_key_sigil")
                if job is None or job["state"] not in TERMINAL_STATES or not isinstance(key, str):
                    raise AthanorError("invalid terminal cancellation observation")
                scope = (job["job_id"], key)
                if scope in cancellations:
                    raise AthanorError("duplicate execution cancellation binding")
                cancellations[scope] = event["event_sigil"]
            elif event_type == "job.terminal":
                job = jobs.get(payload.get("job_id"))
                state = payload.get("state")
                if job is None or job["state"] in TERMINAL_STATES or state not in TERMINAL_STATES:
                    raise AthanorError("invalid execution Job terminal transition")
                if job["state"] == "CANCEL_REQUESTED" and state != "CANCELLED":
                    raise AthanorError("cancelled execution Job cannot accept a worker terminal result")
                job["state"] = state
                job["revision"] += 1
                job["terminal_event_id"] = event["event_id"]
                job["terminal_event_sigil"] = event["event_sigil"]
                job["terminal_reason"] = payload.get("reason")
            else:
                raise AthanorError(f"unsupported execution Event in journal: {event_type}")
        return {"executor": executor, "jobs": jobs, "starts": starts, "cancellations": cancellations}

    def _existing_events(self) -> list[dict[str, Any]]:
        """Read an existing journal without making a read operation mutating."""
        if not self._journal_path.exists():
            raise AthanorError("unknown execution Job")
        with _exclusive_lock(self._lock_path):
            return self._events_unlocked()

    def start(self, execution_specification: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        """Durably submit one typed Job without launching a process."""
        self._validate_specification(execution_specification)
        job_id, key_sigil = self._job_id(execution_specification, idempotency_key)
        request = {
            "schema_version": "benchwork-local-execution-start-request/0.1",
            "execution_specification": execution_specification,
            "idempotency_key": idempotency_key,
        }
        request_sigil = content_sigil(request)
        self.initialize()
        with _exclusive_lock(self._lock_path):
            events = self._events_unlocked()
            state = self._project(events)
            scope = (execution_specification["task_binding"]["task_id"], key_sigil)
            existing = state["starts"].get(scope)
            if existing is not None:
                existing_job_id, existing_request_sigil = existing
                if existing_request_sigil != request_sigil:
                    raise AthanorError("execution Start idempotency conflict")
                return self._observation_unlocked(events, existing_job_id, MAX_PAGE_SIZE, None)
            binding = content_sigil(
                ["execution-job-binding/1.0", job_id, execution_specification["specification_sigil"], request_sigil]
            )
            self._append_unlocked(
                "job.submitted",
                {
                    "job_id": job_id,
                    "job_binding_sigil": binding,
                    "task_id": execution_specification["task_binding"]["task_id"],
                    "specification": execution_specification,
                    "start_request_sigil": request_sigil,
                    "idempotency_key_sigil": key_sigil,
                },
            )
            return self._observation_unlocked(self._events_unlocked(), job_id, MAX_PAGE_SIZE, None)

    def _observation_unlocked(
        self,
        events: list[dict[str, Any]],
        job_id: str,
        limit: int,
        cursor: dict[str, Any] | None,
    ) -> dict[str, Any]:
        state = self._project(events)
        job = state["jobs"].get(job_id)
        if job is None:
            raise AthanorError(f"unknown execution Job: {job_id}")
        if not isinstance(limit, int) or not 1 <= limit <= MAX_PAGE_SIZE:
            raise AthanorError(f"observation limit must be in 1..{MAX_PAGE_SIZE}")
        through_sequence = events[-1]["sequence"]
        through_sigil = events[-1]["event_sigil"]
        last_returned = 0
        if cursor is not None:
            if not isinstance(cursor, dict) or set(cursor) != {
                "job_id",
                "last_returned_sequence",
                "through_journal_sequence",
                "through_event_sigil",
                "cursor_sigil",
            }:
                raise AthanorError("execution observation cursor is invalid")
            expected = content_sigil({key: value for key, value in cursor.items() if key != "cursor_sigil"})
            if cursor["cursor_sigil"] != expected or cursor["job_id"] != job_id:
                raise AthanorError("execution observation cursor is stale")
            fixed_sequence = cursor["through_journal_sequence"]
            last_returned = cursor["last_returned_sequence"]
            if (
                not isinstance(fixed_sequence, int)
                or not isinstance(last_returned, int)
                or fixed_sequence < 1
                or fixed_sequence > len(events)
                or last_returned < 0
                or last_returned > fixed_sequence
            ):
                raise AthanorError("execution observation cursor is stale")
            if events[fixed_sequence - 1]["event_sigil"] != cursor["through_event_sigil"]:
                raise AthanorError("execution observation cursor is stale")
            through_sequence = fixed_sequence
            through_sigil = cursor["through_event_sigil"]
        matching = [
            event
            for event in events
            if event["sequence"] > last_returned
            and event["sequence"] <= through_sequence
            and event["payload"].get("job_id") == job_id
        ]
        page = matching[:limit]
        next_cursor = None
        if len(matching) > len(page):
            next_cursor = {
                "job_id": job_id,
                "last_returned_sequence": page[-1]["sequence"],
                "through_journal_sequence": through_sequence,
                "through_event_sigil": through_sigil,
            }
            next_cursor["cursor_sigil"] = content_sigil(next_cursor)
        return {
            "schema_version": "benchwork-local-execution-observation/0.1",
            "job": dict(job),
            "executor": state["executor"],
            "events": page,
            "through_journal_sequence": through_sequence,
            "through_event_sigil": through_sigil,
            "next_cursor": next_cursor,
        }

    def observe(
        self,
        job_id: str,
        *,
        limit: int = MAX_PAGE_SIZE,
        cursor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
            raise AthanorError("execution Job ID is invalid")
        events = self._existing_events()
        return self._observation_unlocked(events, job_id, limit, cursor)

    def cancel(
        self,
        job_id: str,
        job_binding_sigil: str,
        expected_job_revision: int,
        idempotency_key: str,
        reason: str,
    ) -> dict[str, Any]:
        if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
            raise AthanorError("execution Job ID is invalid")
        if not isinstance(job_binding_sigil, str) or not SIGIL.fullmatch(job_binding_sigil):
            raise AthanorError("execution Job binding is invalid")
        if not isinstance(expected_job_revision, int) or expected_job_revision < 1:
            raise AthanorError("execution cancellation revision is invalid")
        if not isinstance(reason, str) or not reason or len(reason) > 4096:
            raise AthanorError("execution cancellation reason is invalid")
        if not isinstance(idempotency_key, str) or not idempotency_key or len(idempotency_key) > 256:
            raise AthanorError("execution cancellation idempotency key is invalid")
        key_sigil = content_sigil(["execution-cancel-idempotency-key/1.0", idempotency_key])
        if not self._journal_path.exists():
            raise AthanorError(f"unknown execution Job: {job_id}")
        with _exclusive_lock(self._lock_path):
            events = self._events_unlocked()
            state = self._project(events)
            job = state["jobs"].get(job_id)
            if job is None or job["job_binding_sigil"] != job_binding_sigil:
                raise AthanorError("execution Job binding is invalid")
            if (job_id, key_sigil) in state["cancellations"]:
                return self._observation_unlocked(events, job_id, MAX_PAGE_SIZE, None)
            if expected_job_revision != job["revision"]:
                raise AthanorError("execution cancellation revision conflict")
            payload = {
                "job_id": job_id,
                "job_binding_sigil": job_binding_sigil,
                "expected_job_revision": expected_job_revision,
                "idempotency_key_sigil": key_sigil,
                "reason": reason,
            }
            if job["state"] in TERMINAL_STATES:
                self._append_unlocked("job.cancellation_observed", payload)
            else:
                self._append_unlocked("job.cancellation_requested", payload)
                self._append_unlocked(
                    "job.terminal",
                    {"job_id": job_id, "state": "CANCELLED", "reason": "CANCELLATION_REQUESTED"},
                )
            return self._observation_unlocked(self._events_unlocked(), job_id, MAX_PAGE_SIZE, None)

    def record_terminal(self, job_id: str, state: str, reason: str) -> dict[str, Any]:
        """Trusted local worker adapter hook; it cannot be reached from MCP."""
        if state not in TERMINAL_STATES:
            raise AthanorError("execution terminal state is invalid")
        if not isinstance(reason, str) or not reason:
            raise AthanorError("execution terminal reason is invalid")
        if not self._journal_path.exists():
            raise AthanorError(f"unknown execution Job: {job_id}")
        with _exclusive_lock(self._lock_path):
            events = self._events_unlocked()
            job = self._project(events)["jobs"].get(job_id)
            if job is None or job["state"] in TERMINAL_STATES:
                raise AthanorError("execution Job is not terminalizable")
            if job["state"] == "CANCEL_REQUESTED" and state != "CANCELLED":
                raise AthanorError("cancelled execution Job cannot accept a worker terminal result")
            self._append_unlocked("job.terminal", {"job_id": job_id, "state": state, "reason": reason})
            return self._observation_unlocked(self._events_unlocked(), job_id, MAX_PAGE_SIZE, None)

    def get_outcome(self, job_id: str) -> dict[str, Any]:
        if not self._journal_path.exists():
            raise AthanorError(f"unknown execution Job: {job_id}")
        with _exclusive_lock(self._lock_path):
            events = self._events_unlocked()
            job = self._project(events)["jobs"].get(job_id)
            if job is None:
                raise AthanorError(f"unknown execution Job: {job_id}")
            if job["state"] not in TERMINAL_STATES:
                raise AthanorError("execution Job has no terminal outcome")
            outcome = {
                "schema_version": "benchwork-local-execution-job-outcome/0.1",
                "outcome_id": "OJ-" + hashlib.sha256(
                    canonical_json(
                        ["benchwork-local-execution-job-outcome/0.1", job_id, job["terminal_event_sigil"]]
                    ).encode()
                ).hexdigest().upper(),
                "job_id": job_id,
                "job_binding_sigil": job["job_binding_sigil"],
                "terminal_state": job["state"],
                "terminal_reason": job["terminal_reason"],
                "terminal_event_id": job["terminal_event_id"],
                "terminal_event_sigil": job["terminal_event_sigil"],
                "eligible_for_acceptance": False,
            }
            outcome["outcome_sigil"] = content_sigil(outcome)
            return outcome
