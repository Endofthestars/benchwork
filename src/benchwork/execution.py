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
LOCAL_EXECUTION_EVENT_ID = re.compile(r"^JE-[0-9A-F]{16}-[0-9A-F]{16}$")
LOCAL_EXECUTION_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
MAX_PAGE_SIZE = 256
LOCAL_EXECUTION_JOURNAL_ID = "EJ-LOCAL-V1"
LOCAL_EXECUTION_EVENT_TYPES = frozenset(
    {
        "executor.epoch-started",
        "job.submitted",
        "job.queued",
        "job.cancellation_requested",
        "job.cancellation_observed",
        "job.terminal",
    }
)
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


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, member in pairs:
        if key in value:
            raise AthanorError(f"duplicate JSON key: {key}")
        value[key] = member
    return value


def _reject_nonfinite_json_number(token: str) -> None:
    raise AthanorError(f"non-finite JSON number is forbidden: {token}")


def _validate_local_json_numbers(value: Any) -> None:
    if isinstance(value, float):
        raise AthanorError("local JSON float is forbidden")
    if isinstance(value, dict):
        for member in value.values():
            _validate_local_json_numbers(member)
    elif isinstance(value, list):
        for member in value:
            _validate_local_json_numbers(member)


def _load_strict_local_json_object(raw: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite_json_number,
        )
    except json.JSONDecodeError as error:
        raise AthanorError(f"{label} contains invalid JSON") from error
    if not isinstance(value, dict):
        raise AthanorError(f"{label} must be an object")
    _validate_local_json_numbers(value)
    return value


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
                directory = self.path / name
                if directory.exists() and not directory.is_dir():
                    raise AthanorError(f"managed storage path is not a directory: {name}")
                try:
                    directory.mkdir(parents=True, exist_ok=True)
                except OSError as error:
                    raise AthanorError(f"managed storage directory is unavailable: {name}") from error
            format_path = self.path / "format.json"
            expected = {
                "schema_version": "benchwork-local-artifact-storage-format/0.1",
                "backend_id": "BE-LOCAL-V1",
                "layout": "BENCHWORK_LOCAL_STORAGE_V1",
            }
            if format_path.exists():
                if not format_path.is_file():
                    raise AthanorError("managed storage format is invalid")
                try:
                    actual = _load_strict_local_json_object(
                        format_path.read_text(encoding="utf-8"), "managed storage format",
                    )
                except (OSError, UnicodeDecodeError) as error:
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

    def _record_path(self, sigil: str) -> Path:
        self._blob_path(sigil)
        return self.path / "records" / f"blob-{sigil.removeprefix('sha256:')}.json"

    @staticmethod
    def _validate_record(record: Any, sigil: str, size_bytes: int) -> None:
        if not isinstance(record, dict) or set(record) != {
            "schema_version", "blob_sigil", "size_bytes", "media_type",
            "backend_id", "availability", "record_sigil",
        }:
            raise AthanorError("Blob record is invalid")
        if (
            record["schema_version"] != "benchwork-local-artifact-blob/0.1"
            or record["blob_sigil"] != sigil
            or record["size_bytes"] != size_bytes
            or not isinstance(record["media_type"], str)
            or not record["media_type"]
            or len(record["media_type"]) > 128
            or record["backend_id"] != "BE-LOCAL-V1"
            or record["availability"] != "AVAILABLE"
            or record["record_sigil"] != content_sigil(
                {key: value for key, value in record.items() if key != "record_sigil"}
            )
        ):
            raise AthanorError("Blob record conflict or integrity failure")

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
            record_path = self._record_path(sigil)
            if record_path.exists():
                try:
                    prior = _load_strict_local_json_object(
                        record_path.read_text(encoding="utf-8"), "Blob record",
                    )
                except (OSError, UnicodeDecodeError) as error:
                    raise AthanorError("Blob record is invalid") from error
                self._validate_record(prior, sigil, len(value))
                if prior != record:
                    raise AthanorError("Blob record conflict or integrity failure")
                return prior
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
        record_path = self._record_path(sigil)
        try:
            record = _load_strict_local_json_object(
                record_path.read_text(encoding="utf-8"), "Blob record",
            )
        except (OSError, UnicodeDecodeError) as error:
            raise AthanorError(f"Blob record is unavailable or invalid: {sigil}") from error
        self._validate_record(record, sigil, len(value))
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
        if not self._journal_path.is_file():
            raise AthanorError("execution journal is unreadable")
        events: list[dict[str, Any]] = []
        previous: str | None = None
        previous_recorded_at: datetime | None = None
        event_ids: set[str] = set()
        try:
            journal_bytes = self._journal_path.read_bytes()
            journal_text = journal_bytes.decode("utf-8", errors="strict")
        except (OSError, UnicodeDecodeError) as error:
            raise AthanorError("execution journal is unreadable") from error
        if journal_text and not journal_text.endswith("\n"):
            raise AthanorError("execution journal has an incomplete tail")
        lines = journal_text.splitlines()
        for line_number, line in enumerate(lines, 1):
            try:
                event = _load_strict_local_json_object(
                    line, f"execution journal Event at line {line_number}",
                )
            except UnicodeDecodeError as error:
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
            if event["journal_id"] != LOCAL_EXECUTION_JOURNAL_ID:
                raise AthanorError("execution journal identity is invalid")
            if event["event_type"] not in LOCAL_EXECUTION_EVENT_TYPES:
                raise AthanorError("execution journal Event type is invalid")
            if (
                not isinstance(event["event_id"], str)
                or not LOCAL_EXECUTION_EVENT_ID.fullmatch(event["event_id"])
                or not isinstance(event["sequence"], int)
                or isinstance(event["sequence"], bool)
                or not isinstance(event["recorded_at"], str)
                or not isinstance(event["payload"], dict)
                or not isinstance(event["event_sigil"], str)
                or not SIGIL.fullmatch(event["event_sigil"])
            ):
                raise AthanorError("execution journal Event scalar fields are invalid")
            try:
                recorded_at = datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00"))
            except ValueError as error:
                raise AthanorError("execution journal Event recorded_at is invalid") from error
            if not LOCAL_EXECUTION_TIMESTAMP.fullmatch(event["recorded_at"]) or recorded_at.tzinfo != UTC:
                raise AthanorError("execution journal Event recorded_at is invalid")
            if previous_recorded_at is not None and recorded_at < previous_recorded_at:
                raise AthanorError("execution journal Event time is decreasing")
            if previous is None:
                if event["previous_event_sigil"] is not None:
                    raise AthanorError("execution journal chain is broken")
            elif not isinstance(event["previous_event_sigil"], str) or not SIGIL.fullmatch(
                event["previous_event_sigil"]
            ):
                raise AthanorError("execution journal chain is broken")
            if event["event_id"] in event_ids:
                raise AthanorError("execution journal has a duplicate Event identity")
            if event["sequence"] != len(events) + 1 or event["previous_event_sigil"] != previous:
                raise AthanorError("execution journal chain is broken")
            if not events and event["event_type"] != "executor.epoch-started":
                raise AthanorError("execution journal has no executor epoch")
            if events and event["event_type"] == "executor.epoch-started":
                raise AthanorError("execution journal has a duplicate executor epoch")
            expected = content_sigil({key: value for key, value in event.items() if key != "event_sigil"})
            if event["event_sigil"] != expected:
                raise AthanorError("execution journal Event Sigil is invalid")
            events.append(event)
            event_ids.add(event["event_id"])
            previous = event["event_sigil"]
            previous_recorded_at = recorded_at
        return events

    def _write_head_unlocked(self, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        head = {
            "schema_version": "benchwork-local-execution-journal-head/0.1",
            "journal_id": LOCAL_EXECUTION_JOURNAL_ID,
            "last_sequence": events[-1]["sequence"],
            "last_event_id": events[-1]["event_id"],
            "last_event_sigil": events[-1]["event_sigil"],
            "updated_at": _utc_now(),
        }
        head["head_sigil"] = content_sigil(head)
        _atomic_json(self._head_path, head)

    def _append_unlocked(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        events = self._events_unlocked()
        if event_type not in LOCAL_EXECUTION_EVENT_TYPES:
            raise AthanorError(f"unsupported execution Event type: {event_type}")
        sequence = len(events) + 1
        event = {
            "schema_version": "benchwork-local-execution-journal-event/0.1",
            "journal_id": LOCAL_EXECUTION_JOURNAL_ID,
            "event_id": f"JE-{sequence:016X}-{uuid4().hex[:16].upper()}",
            "sequence": sequence,
            "event_type": event_type,
            "recorded_at": _utc_now(),
            "previous_event_sigil": events[-1]["event_sigil"] if events else None,
            "payload": payload,
        }
        event["event_sigil"] = content_sigil(event)
        # Validate the complete candidate prefix before publishing any bytes.
        # This remains a local pre-conformance projection, not RFC replay
        # authority, but it prevents an internal caller from durably writing a
        # transition that the same runtime can never recover.
        self._project([*events, event])
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
        executor = events[0]["payload"]
        if (
            set(executor) != {
                "executor_instance_id", "executor_epoch", "executor_build_sigil"
            }
            or not isinstance(executor["executor_instance_id"], str)
            or not executor["executor_instance_id"]
            or not isinstance(executor["executor_epoch"], int)
            or isinstance(executor["executor_epoch"], bool)
            or executor["executor_epoch"] < 1
            or not isinstance(executor["executor_build_sigil"], str)
            or not SIGIL.fullmatch(executor["executor_build_sigil"])
        ):
            raise AthanorError("execution executor epoch payload is invalid")
        executor = dict(executor)
        jobs: dict[str, dict[str, Any]] = {}
        starts: dict[tuple[str, str], tuple[str, str]] = {}
        cancellations: dict[tuple[str, str], dict[str, Any]] = {}
        for event in events[1:]:
            payload = event["payload"]
            event_type = event["event_type"]
            if event_type == "job.submitted":
                if set(payload) != {
                    "job_id", "job_binding_sigil", "task_id", "specification",
                    "start_request_sigil", "idempotency_key_sigil",
                }:
                    raise AthanorError("execution Job submission payload is invalid")
                job_id = payload["job_id"]
                task_id = payload["task_id"]
                key_sigil = payload["idempotency_key_sigil"]
                if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id) or job_id in jobs:
                    raise AthanorError("invalid or duplicate execution Job")
                if (
                    not isinstance(task_id, str)
                    or not task_id
                    or not isinstance(key_sigil, str)
                    or not SIGIL.fullmatch(key_sigil)
                    or not isinstance(payload["start_request_sigil"], str)
                    or not SIGIL.fullmatch(payload["start_request_sigil"])
                    or not isinstance(payload["job_binding_sigil"], str)
                    or not SIGIL.fullmatch(payload["job_binding_sigil"])
                ):
                    raise AthanorError("execution Job idempotency binding is invalid")
                specification = payload["specification"]
                ExecutionService._validate_specification(specification)
                if task_id != specification["task_binding"]["task_id"]:
                    raise AthanorError("execution Job submission Task binding is invalid")
                expected_job_id = "JB-" + hashlib.sha256(canonical_json([
                    "execution-job-id/1.0", task_id, key_sigil,
                ]).encode("utf-8")).hexdigest().upper()
                expected_binding = content_sigil([
                    "execution-job-binding/1.0", job_id,
                    specification["specification_sigil"], payload["start_request_sigil"],
                ])
                if job_id != expected_job_id or payload["job_binding_sigil"] != expected_binding:
                    raise AthanorError("execution Job submission binding is invalid")
                scope = (task_id, key_sigil)
                request_sigil = payload["start_request_sigil"]
                if scope in starts:
                    raise AthanorError("duplicate execution Job idempotency binding")
                starts[scope] = (job_id, request_sigil)
                jobs[job_id] = {
                    "job_id": job_id, "job_binding_sigil": payload["job_binding_sigil"],
                    "task_id": task_id,
                    "specification_id": specification["specification_id"],
                    "specification_sigil": specification["specification_sigil"],
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
                if set(payload) != {"job_id"}:
                    raise AthanorError("execution Job queue payload is invalid")
                if not isinstance(payload["job_id"], str):
                    raise AthanorError("execution Job queue payload is invalid")
                job = jobs.get(payload["job_id"])
                if job is None or job["state"] != "SUBMITTED":
                    raise AthanorError("invalid execution Job queue transition")
                job["state"] = "QUEUED"
                job["revision"] += 1
            elif event_type == "job.cancellation_requested":
                if set(payload) != {
                    "job_id", "job_binding_sigil", "expected_job_revision",
                    "idempotency_key_sigil", "reason",
                }:
                    raise AthanorError("execution Job cancellation payload is invalid")
                if (
                    not isinstance(payload["job_id"], str)
                    or not isinstance(payload["expected_job_revision"], int)
                    or isinstance(payload["expected_job_revision"], bool)
                    or payload["expected_job_revision"] < 1
                ):
                    raise AthanorError("execution Job cancellation payload is invalid")
                job = jobs.get(payload["job_id"])
                key = payload["idempotency_key_sigil"]
                if (
                    job is None
                    or not isinstance(key, str)
                    or not SIGIL.fullmatch(key)
                    or payload["job_binding_sigil"] != job["job_binding_sigil"]
                    or payload["expected_job_revision"] != job["revision"]
                    or not isinstance(payload["reason"], str)
                    or not payload["reason"]
                    or len(payload["reason"]) > 4096
                ):
                    raise AthanorError("invalid execution Job cancellation")
                scope = (job["job_id"], key)
                if scope in cancellations:
                    raise AthanorError("duplicate execution cancellation binding")
                cancellations[scope] = dict(payload)
                if job["state"] in TERMINAL_STATES:
                    raise AthanorError("terminal Job cannot receive cancellation request")
                job["state"] = "CANCEL_REQUESTED"
                job["revision"] += 1
            elif event_type == "job.cancellation_observed":
                if set(payload) != {
                    "job_id", "job_binding_sigil", "expected_job_revision",
                    "idempotency_key_sigil", "reason",
                }:
                    raise AthanorError("execution terminal cancellation payload is invalid")
                if (
                    not isinstance(payload["job_id"], str)
                    or not isinstance(payload["expected_job_revision"], int)
                    or isinstance(payload["expected_job_revision"], bool)
                    or payload["expected_job_revision"] < 1
                ):
                    raise AthanorError("execution terminal cancellation payload is invalid")
                job = jobs.get(payload["job_id"])
                key = payload["idempotency_key_sigil"]
                if (
                    job is None
                    or job["state"] not in TERMINAL_STATES
                    or not isinstance(key, str)
                    or not SIGIL.fullmatch(key)
                    or payload["job_binding_sigil"] != job["job_binding_sigil"]
                    or payload["expected_job_revision"] != job["revision"]
                    or not isinstance(payload["reason"], str)
                    or not payload["reason"]
                    or len(payload["reason"]) > 4096
                ):
                    raise AthanorError("invalid terminal cancellation observation")
                scope = (job["job_id"], key)
                if scope in cancellations:
                    raise AthanorError("duplicate execution cancellation binding")
                cancellations[scope] = dict(payload)
            elif event_type == "job.terminal":
                if set(payload) != {"job_id", "state", "reason"}:
                    raise AthanorError("execution Job terminal payload is invalid")
                if not isinstance(payload["job_id"], str) or not isinstance(payload["state"], str):
                    raise AthanorError("execution Job terminal payload is invalid")
                job = jobs.get(payload["job_id"])
                state = payload["state"]
                if (
                    job is None
                    or job["state"] in TERMINAL_STATES
                    or state not in TERMINAL_STATES
                    or not isinstance(payload["reason"], str)
                    or not payload["reason"]
                    or len(payload["reason"]) > 4096
                ):
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
            prior_cancellation = state["cancellations"].get((job_id, key_sigil))
            if prior_cancellation is not None:
                if (
                    prior_cancellation["job_binding_sigil"] != job_binding_sigil
                    or prior_cancellation["reason"] != reason
                ):
                    raise AthanorError("execution cancellation idempotency conflict")
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
        if not isinstance(reason, str) or not reason or len(reason) > 4096:
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
