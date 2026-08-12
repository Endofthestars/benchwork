"""Pure, fail-closed validators for RFC-0012 State and Journal Event wires.

These helpers validate closed bytes and deterministic projections only.  They
do not append an Event, replay a Journal, acknowledge a request, or grant any
runtime, storage, Result, assurance, or scientific authority.
"""

from __future__ import annotations

import json
import math
import unicodedata
from copy import deepcopy
from datetime import datetime
from typing import Any, NoReturn

from .athanor import AthanorError, canonical_json, content_sigil
from .schema_validation import validate_instance


EXECUTION_EVENT_TYPES_V1 = (
    "executor.epoch_started",
    "executor.clock_uncertain",
    "executor.clock_restored",
    "execution.heartbeat_collision_authority_closed",
    "recovery.started",
    "recovery.action_set_rebased",
    "recovery.phase_advanced",
    "recovery.completed",
    "worker.definition_registered",
    "worker.enabled",
    "worker.draining",
    "worker.quarantined",
    "worker.retired",
    "worker_session.registered",
    "worker_session.ready",
    "worker_session.draining",
    "worker_session.offline",
    "worker_session.quarantined",
    "worker_session.closed",
    "worker_session.heartbeat_accepted",
    "worker_session.message_rejected",
    "job.submitted",
    "job.queued",
    "job.attempt_allocated",
    "job.budget_settled",
    "job.retry_scheduled",
    "job.retry_ready",
    "job.stop_latched",
    "job.cancellation_observed",
    "job.assurance_evaluated",
    "job.succeeded",
    "job.failed",
    "job.cancelled",
    "job.timed_out",
    "job.policy_violated",
    "storage_root.hold_release_observed",
    "job.message_rejected",
    "attempt.authorization_bound",
    "attempt.preflight_started",
    "attempt.preflight_progressed",
    "attempt.preflight_passed",
    "attempt.starting",
    "attempt.running",
    "attempt.output_staging_preallocated",
    "attempt.result_ingress_received",
    "attempt.result_accepted",
    "attempt.result_rejected",
    "attempt.draining",
    "attempt.stop_latched",
    "attempt.stop_progressed",
    "attempt.cleaning",
    "attempt.cleanup_progressed",
    "attempt.succeeded",
    "attempt.failed",
    "attempt.cancelled",
    "attempt.timed_out",
    "attempt.policy_violated",
    "attempt.lease_expired",
    "attempt.lost",
    "attempt.fenced",
    "attempt.rejected",
    "attempt.assurance_evaluated",
    "lease.offered",
    "lease.claimed",
    "lease.heartbeat_accepted",
    "lease.renewed",
    "lease.released",
    "lease.revoked",
    "lease.expired",
    "lease.fenced",
    "lease.tombstone_republished",
    "lease.message_rejected",
    "log.chunk_committed",
    "log.chunk_duplicate_observed",
    "log.chunk_rejected",
    "log.truncated",
    "log.eof_accepted",
    "log.eof_rejected",
    "log.closed",
    "log.closure_recovery_closed",
    "log.intake_recovery_terminalized",
)

IDEMPOTENCY_OPERATION_KINDS_V1 = (
    "START_JOB",
    "CANCEL_JOB",
    "REGISTER_WORKER_SESSION",
    "CLAIM_LEASE",
    "RENEW_LEASE",
    "RELEASE_LEASE",
    "PREALLOCATE_OUTPUT_STAGING",
    "RECEIVE_RESULT_INGRESS",
    "SUBMIT_RESULT",
    "APPEND_LOG_CHUNK",
    "CLOSE_LOG_STREAM",
)
_ENTITY_KIND_ORDER = (
    "EXECUTOR",
    "RECOVERY",
    "WORKER",
    "WORKER_SESSION",
    "JOB",
    "ATTEMPT",
    "LEASE",
    "LOG_STREAM",
)
_ENTITY_KIND_RANK = {value: rank for rank, value in enumerate(_ENTITY_KIND_ORDER)}
_RECOVERY_ACTION_KIND_ORDER = (
    "COMMIT_DUE_EVENT",
    "RESTORE_CLOCK",
    "FENCE_LEASE",
    "REPUBLISH_TOMBSTONE",
    "OFFLINE_SESSION",
    "TERMINATE_PROCESS_TREE",
    "REVOKE_HANDLES",
    "CLOSE_SESSION",
    "CLOSE_LOG",
    "VERIFY_OUTPUT_STORAGE",
    "VERIFY_TERMINAL_SOURCE",
    "BIND_DURABLE_ATTEMPT_AUTHORIZATION",
    "RELEASE_INACTIVE_EXECUTION_INPUT_HOLD",
    "RELEASE_DUE_EXECUTION_HOLD",
    "QUARANTINE_RESOURCE",
    "ADVANCE_ATTEMPT",
    "CLEAN_RESOURCE",
    "COLLECT_ACCOUNTING",
    "SETTLE_BUDGET",
    "EVALUATE_ATTEMPT_ASSURANCE",
    "EVALUATE_JOB_ASSURANCE",
    "ADVANCE_JOB",
)
_RECOVERY_ACTION_KIND_RANK = {value: rank for rank, value in enumerate(_RECOVERY_ACTION_KIND_ORDER)}
_RECOVERY_PHASE_KINDS = {
    "STARTED": {"COMMIT_DUE_EVENT"},
    "FENCING": {
        "FENCE_LEASE",
        "REPUBLISH_TOMBSTONE",
        "OFFLINE_SESSION",
        "BIND_DURABLE_ATTEMPT_AUTHORIZATION",
        "ADVANCE_ATTEMPT",
        "ADVANCE_JOB",
    },
    "RECONCILING": {
        "TERMINATE_PROCESS_TREE",
        "REVOKE_HANDLES",
        "CLOSE_SESSION",
        "CLOSE_LOG",
        "VERIFY_OUTPUT_STORAGE",
        "VERIFY_TERMINAL_SOURCE",
        "QUARANTINE_RESOURCE",
        "ADVANCE_ATTEMPT",
        "CLEAN_RESOURCE",
        "COLLECT_ACCOUNTING",
    },
    "FINALIZING": {
        "RESTORE_CLOCK",
        "ADVANCE_ATTEMPT",
        "SETTLE_BUDGET",
        "EVALUATE_ATTEMPT_ASSURANCE",
        "EVALUATE_JOB_ASSURANCE",
        "ADVANCE_JOB",
        "RELEASE_INACTIVE_EXECUTION_INPUT_HOLD",
        "RELEASE_DUE_EXECUTION_HOLD",
    },
}
_RECOVERY_NEXT_PHASE = {
    "STARTED": "FENCING",
    "FENCING": "RECONCILING",
    "RECONCILING": "FINALIZING",
}
_ATTEMPT_TERMINAL_EVENT_TYPES = {
    "attempt.succeeded",
    "attempt.failed",
    "attempt.cancelled",
    "attempt.timed_out",
    "attempt.policy_violated",
    "attempt.lease_expired",
    "attempt.lost",
    "attempt.fenced",
    "attempt.rejected",
}
_CONTROL_DIMENSION_ORDER = (
    "IDENTITY_AUTHORIZATION",
    "FILESYSTEM",
    "NETWORK",
    "PROCESS_EXECUTABLE",
    "RESOURCE",
    "ENVIRONMENT_CREDENTIAL",
    "LOG_OUTPUT_CAPTURE",
    "RUNTIME_INPUT_OUTPUT_IDENTITY",
    "CANCELLATION_FENCING",
    "TERMINATION_CLEANUP",
)
_CONTROL_PHASE_ORDER = ("PREFLIGHT", "RUNTIME", "TERMINATION", "CLEANUP")
_CONTROL_PHASE_RANK = {value: rank for rank, value in enumerate(_CONTROL_PHASE_ORDER)}
_CONTROL_EVIDENCE_KIND_ORDER = (
    "TASK_BINDING",
    "CAPABILITY_BINDING",
    "SNAPSHOT_BINDING",
    "WARD_DECISION",
    "APPROVAL_RECEIPT",
    "BACKEND_CONFIGURATION",
    "HOST_IDENTITY",
    "POLICY_RESOLUTION",
    "BASE_IDENTITY",
    "INPUT_IDENTITY",
    "MATERIALIZATION_IDENTITY",
    "ENVIRONMENT_CONSTRUCTION",
    "FILESYSTEM_POLICY",
    "NETWORK_POLICY",
    "EXECUTABLE_SELECTION",
    "PROCESS_TREE",
    "WALL_TIME_ENFORCEMENT",
    "RESOURCE_ACCOUNTING",
    "CREDENTIAL_NONINHERITANCE",
    "LOG_CAPTURE",
    "OUTPUT_VALIDATION",
    "STORAGE_OBSERVATION",
    "FENCE_TOMBSTONE",
    "TERMINATION",
    "HANDLE_REVOCATION",
    "CLEANUP",
    "QUARANTINE",
    "TERMINAL_SOURCE_VERIFICATION",
    "CONFORMANCE_FIXTURE",
)
_CONTROL_EVIDENCE_KIND_RANK = {
    value: rank for rank, value in enumerate(_CONTROL_EVIDENCE_KIND_ORDER)
}
_AUTHORITY_GATE_ORDER = ("INTEGRITY_FAILURE", "CLOCK_UNCERTAIN", "RECOVERY_ACTIVE")
_AUTHORITY_GATE_RANK = {value: rank for rank, value in enumerate(_AUTHORITY_GATE_ORDER)}
_DEADLINE_PRIORITY = {
    "JOB_DEADLINE": 10,
    "ATTEMPT_DEADLINE": 20,
    "HEARTBEAT_TIMEOUT": 30,
    "LEASE_EXPIRY": 40,
    "LEASE_CLAIM_DEADLINE": 50,
    "CANCELLATION_GRACE": 60,
    "RETRY_ELIGIBILITY": 70,
}
_EXECUTION_REQUEST_SCHEMAS_V1 = {
    "start": "execution-start-request-1.0.json",
    "observe": "execution-observe-request-1.0.json",
    "cancel": "execution-cancel-request-1.0.json",
    "get_result": "execution-get-result-request-1.0.json",
    "accept_result": "execution-accept-result-request-1.0.json",
}
_IDEMPOTENCY_RANK = {value: rank for rank, value in enumerate(IDEMPOTENCY_OPERATION_KINDS_V1)}
_MISSING = object()


def _fail(message: str) -> NoReturn:
    raise AthanorError(message)


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> NoReturn:
    _fail(f"non-finite JSON number is forbidden: {token}")


def _load_strict_object(raw: str | bytes | bytearray, label: str) -> dict[str, Any]:
    if isinstance(raw, (bytes, bytearray)):
        encoded = bytes(raw)
        if encoded.startswith(b"\xef\xbb\xbf"):
            _fail(f"invalid {label} JSON: UTF-8 BOM is forbidden")
        try:
            raw = encoded.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _fail(f"invalid {label} JSON: non-UTF-8 encoding is forbidden")
    if isinstance(raw, str) and raw.startswith("\ufeff"):
        _fail(f"invalid {label} JSON: UTF-8 BOM is forbidden")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite,
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        _fail(f"invalid {label} JSON: {error}")
    if not isinstance(value, dict):
        _fail(f"{label} JSON root must be an object")
    return value


def _check_nfc(value: Any) -> None:
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            _fail("JSON string contains a non-Unicode-scalar value")
        if unicodedata.normalize("NFC", value) != value:
            _fail("JSON string is not NFC-normalized")
    elif isinstance(value, dict):
        for key, member in value.items():
            _check_nfc(key)
            _check_nfc(member)
    elif isinstance(value, list):
        for member in value:
            _check_nfc(member)
    elif isinstance(value, float):
        if not math.isfinite(value):
            _fail("non-finite JSON number is forbidden")
        _fail("JSON float is forbidden by canonical execution wire")


def _without(value: dict[str, Any], member: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != member}


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def derive_execution_observation_cursor_sigil_v1(cursor: dict[str, Any]) -> str:
    """Derive the public fixed-prefix cursor Sigil from its other members."""
    if "cursor_sigil" in cursor:
        cursor = _without(cursor, "cursor_sigil")
    return content_sigil(cursor)


def validate_execution_request_v1(kind: str, request: dict[str, Any]) -> None:
    """Validate one closed RFC-0015 request without performing its operation."""
    try:
        schema_name = _EXECUTION_REQUEST_SCHEMAS_V1[kind]
    except KeyError:
        _fail(f"unknown Execution API request kind: {kind}")
    validate_instance(schema_name, request)
    _check_nfc(request)
    cursor = request.get("cursor")
    if cursor is not None:
        if cursor["job_id"] != request["job_id"]:
            _fail("Execution observation cursor Job does not match request Job")
        if cursor["last_returned_sequence"] > cursor["through_journal_sequence"]:
            _fail("Execution observation cursor sequence range is invalid")
        if cursor["cursor_sigil"] != derive_execution_observation_cursor_sigil_v1(cursor):
            _fail("Execution observation cursor Sigil mismatch")


def load_execution_request_v1(kind: str, raw: str | bytes | bytearray) -> dict[str, Any]:
    """Strictly decode a closed RFC-0015 request without dispatching it."""
    request = _load_strict_object(raw, f"Execution API {kind} request")
    validate_execution_request_v1(kind, request)
    return request


def _idempotency_projection(record: dict[str, Any]) -> tuple[int, bytes, str]:
    owner = record if "operation_kind" in record else record["core"]
    operation = owner["operation_kind"]
    try:
        rank = _IDEMPOTENCY_RANK[operation]
    except KeyError:
        _fail(f"unknown idempotency operation: {operation}")
    return (
        rank,
        _unsigned_ascii(owner["scope_id"], "Idempotency scope ID"),
        owner["idempotency_key_sigil"],
    )


def _unsigned_ascii(value: str, label: str) -> bytes:
    try:
        return value.encode("ascii", errors="strict")
    except UnicodeEncodeError:
        _fail(f"{label} must be unsigned ASCII")


def validate_execution_budget_ledger_v1(ledger: dict[str, Any]) -> None:
    """Validate RFC-0012 budget arithmetic and its local self-Sigil."""
    if ledger["budget_ledger_sigil"] != content_sigil(_without(ledger, "budget_ledger_sigil")):
        _fail("Execution budget ledger self-Sigil mismatch")
    for name, dimension in ledger.items():
        if name == "budget_ledger_sigil":
            continue
        total = dimension["consumed"] + dimension["reserved"]
        expected_status = (
            "AVAILABLE"
            if total < dimension["limit"]
            else "EXHAUSTED"
            if total == dimension["limit"]
            else "EXCEEDED"
        )
        if dimension["exhaustion_status"] != expected_status:
            _fail(f"Execution budget dimension {name} has incorrect exhaustion status")


def validate_execution_state_v1(state: dict[str, Any]) -> None:
    """Validate a State cache as bytes/projections, never as replay authority."""
    validate_instance("execution-state-1.0.json", state)
    _check_nfc(state)
    build = state["executor"]["executor_build_binding"]
    if build["executor_build_sigil"] != content_sigil(_without(build, "executor_build_sigil")):
        _fail("Execution State executor build self-Sigil mismatch")
    executor = state["executor"]
    gates = executor["authority_gates"]
    if gates != sorted(gates, key=_AUTHORITY_GATE_RANK.__getitem__):
        _fail("Execution State authority gates are not in canonical order")
    if (executor["clock_state"] == "UNCERTAIN") != ("CLOCK_UNCERTAIN" in gates):
        _fail("Execution State clock uncertainty gate disagrees with clock state")
    if (executor["active_recovery_id"] is not None) != ("RECOVERY_ACTIVE" in gates):
        _fail("Execution State recovery gate disagrees with active recovery")
    recovery_ids = [recovery["recovery_id"] for recovery in state["recoveries"]]
    if len(recovery_ids) != len(set(recovery_ids)):
        _fail("duplicate Recovery projection identity")
    if state["recoveries"]:
        if state["recoveries"][0]["prior_recovery_id"] is not None:
            _fail("first Recovery projection must not name a prior Recovery")
        for index, recovery in enumerate(state["recoveries"][1:], 1):
            prior_recovery = state["recoveries"][index - 1]
            if recovery["prior_recovery_id"] != prior_recovery["recovery_id"]:
                _fail("Recovery projection does not name its immediately prior Recovery")
            if prior_recovery["state"] != "COMPLETED":
                _fail("Recovery projection follows a Recovery that is not completed")
    active_recoveries = [
        recovery for recovery in state["recoveries"] if recovery["state"] != "COMPLETED"
    ]
    if len(active_recoveries) > 1:
        _fail("Execution State has more than one active Recovery")
    active_recovery_id = executor["active_recovery_id"]
    if active_recovery_id is None:
        if active_recoveries:
            _fail("Execution State active Recovery is missing from executor projection")
    elif len(active_recoveries) != 1 or active_recoveries[0]["recovery_id"] != active_recovery_id:
        _fail("Execution State executor active Recovery does not match recovery projection")
    workers_by_id: dict[str, dict[str, Any]] = {}
    for worker in state["workers"]:
        worker_id = worker["worker_id"]
        if worker_id in workers_by_id:
            _fail("duplicate Worker projection identity")
        workers_by_id[worker_id] = worker
        session_ids = worker["worker_session_ids"]
        if session_ids != sorted(
            session_ids, key=lambda value: _unsigned_ascii(value, "Worker session ID")
        ):
            _fail("Worker worker_session_ids are not unsigned-ASCII sorted")
    for job in state["jobs"]:
        validate_execution_budget_ledger_v1(job["budget_ledger"])
    sessions_by_id: dict[str, dict[str, Any]] = {}
    for session in state["worker_sessions"]:
        session_id = session["worker_session_id"]
        if session_id in sessions_by_id:
            _fail("duplicate Worker-Session projection identity")
        sessions_by_id[session_id] = session
        try:
            worker = workers_by_id[session["worker_id"]]
        except KeyError:
            _fail("Worker-Session projection has no matching Worker")
        if session_id not in worker["worker_session_ids"]:
            _fail("Worker-Session projection is missing from its Worker")
        if session["worker_binding_sigil"] != worker["worker_binding_sigil"]:
            _fail("Worker-Session binding Sigil does not match its Worker")
        capacity = session["capacity"]
        if (capacity is None) != (session["state"] == "REGISTERED"):
            _fail("Worker-Session capacity nullability disagrees with Session state")
        if capacity is not None and session["capacity_in_use"] > capacity:
            _fail("Worker-Session capacity_in_use exceeds capacity")
        if (session["last_heartbeat_sequence"] is None) != (
            session["last_heartbeat_message_sigil"] is None
        ):
            _fail("Worker-Session heartbeat fields must be jointly null or present")
        if session["state"] in {"REGISTERED", "OFFLINE", "QUARANTINED", "CLOSED"} and (
            session["next_heartbeat_due_at"] is not None
        ):
            _fail("Worker-Session terminal or unready state must not have a heartbeat due time")
        if session["lease_ids"] != sorted(
            session["lease_ids"], key=lambda value: _unsigned_ascii(value, "Lease ID")
        ):
            _fail("Worker-Session lease_ids are not unsigned-ASCII sorted")
    if {
        session_id for worker in state["workers"] for session_id in worker["worker_session_ids"]
    } != set(sessions_by_id):
        _fail("Worker projection session IDs do not exactly match Worker-Session projections")
    lease_ids = [lease["lease_id"] for lease in state["leases"]]
    if len(lease_ids) != len(set(lease_ids)):
        _fail("duplicate Lease projection identity")
    terminal_lease_states = {"RELEASED", "REVOKED", "EXPIRED", "FENCED"}
    for lease in state["leases"]:
        heartbeat_members = (
            lease["last_heartbeat_sequence"],
            lease["last_heartbeat_message_sigil"],
            lease["last_resource_sample_sigil"],
        )
        if any(member is None for member in heartbeat_members) and not all(
            member is None for member in heartbeat_members
        ):
            _fail("Lease heartbeat fields must be jointly null or present")
        terminal = lease["state"] in terminal_lease_states
        if (lease["next_heartbeat_due_at"] is None) != (lease["state"] != "ACTIVE"):
            _fail("Lease heartbeat due time disagrees with lease state")
        tombstone_members = (lease["tombstone_generation"], lease["tombstone_event_sigil"])
        if (all(member is not None for member in tombstone_members)) != terminal:
            _fail("Lease tombstone fields disagree with terminal lease state")
        if _parse_time(lease["expiry_due_at"]) > _parse_time(lease["maximum_expiry_due_at"]):
            _fail("Lease expiry due time exceeds its maximum expiry")
        try:
            session = sessions_by_id[lease["worker_session_id"]]
        except KeyError:
            _fail("Lease projection has no matching Worker-Session")
        if lease["worker_id"] != session["worker_id"]:
            _fail("Lease Worker does not match its Worker-Session")
        if lease["lease_id"] not in session["lease_ids"]:
            _fail("Lease projection is missing from its Worker-Session")
    if {
        lease_id for session in state["worker_sessions"] for lease_id in session["lease_ids"]
    } != set(lease_ids):
        _fail("Worker-Session lease IDs do not exactly match Lease projections")
    log_stream_ids: set[str] = set()
    for log_stream in state["log_streams"]:
        log_stream_id = log_stream["log_stream_id"]
        if log_stream_id in log_stream_ids:
            _fail("duplicate Log-stream projection identity")
        log_stream_ids.add(log_stream_id)
        final_sequence = log_stream["final_sequence"]
        stream_set_sigil = log_stream["stream_set_sigil"]
        if log_stream["state"] == "OPEN":
            if final_sequence is not None or stream_set_sigil is not None:
                _fail("Open Log stream must not have terminal stream fields")
        elif stream_set_sigil is None:
            _fail("Closed Log stream must have a stream-set Sigil")
        elif final_sequence is not None and final_sequence >= log_stream["next_sequence"]:
            _fail("Closed Log stream final sequence must precede next sequence")
    deadline_keys: list[tuple[datetime, int, bytes]] = []
    for deadline in state["deadlines"]:
        if deadline["fixed_priority"] != _DEADLINE_PRIORITY[deadline["deadline_kind"]]:
            _fail("Deadline fixed priority disagrees with deadline kind")
        deadline_keys.append(
            (
                _parse_time(deadline["due_at"]),
                deadline["fixed_priority"],
                _unsigned_ascii(deadline["entity_id"], "Deadline entity ID"),
            )
        )
    if deadline_keys != sorted(deadline_keys):
        _fail("Deadlines are not sorted by canonical deadline key")
    if len(deadline_keys) != len(set(deadline_keys)):
        _fail("duplicate Deadline projection key")
    keys = [_idempotency_projection(record) for record in state["idempotency_records"]]
    if keys != sorted(keys):
        _fail("idempotency_records are not sorted by the canonical 11-rank key")
    if len(keys) != len(set(keys)):
        _fail("duplicate mixed idempotency comparison tuple")
    if state["state_sigil"] != content_sigil(_without(state, "state_sigil")):
        _fail("Execution State self-Sigil mismatch")


def load_execution_state_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    state = _load_strict_object(raw, "Execution State")
    validate_execution_state_v1(state)
    return state


def build_execution_state_v1(unsigned_state: dict[str, Any]) -> dict[str, Any]:
    if "state_sigil" in unsigned_state:
        _fail("unsigned Execution State must not contain state_sigil")
    state = {**unsigned_state, "state_sigil": content_sigil(unsigned_state)}
    validate_execution_state_v1(state)
    return state


def validate_execution_journal_head_v1(head: dict[str, Any]) -> None:
    """Validate the closed Head cache record, never its claimed Journal prefix."""
    validate_instance("execution-journal-head-1.0.json", head)
    _check_nfc(head)
    if head["head_sigil"] != content_sigil(_without(head, "head_sigil")):
        _fail("Execution Journal Head self-Sigil mismatch")


def load_execution_journal_head_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    head = _load_strict_object(raw, "Execution Journal Head")
    validate_execution_journal_head_v1(head)
    return head


def validate_execution_initial_state_supplied_facts_v1(
    event: dict[str, Any], state: dict[str, Any], head: dict[str, Any]
) -> None:
    """Compare an ISR3 initial State with caller-supplied Event and Head bytes.

    This does not authenticate the supplied records or establish a durable
    prefix; it only verifies the exact RFC-0012 initial-projection equations.
    """
    validate_execution_journal_event_v1(event)
    validate_execution_state_v1(state)
    validate_execution_journal_head_v1(head)
    if event["sequence"] != 1 or event["event_type"] != "executor.epoch_started":
        _fail("ISR3 supplied Event is not the sequence-one executor epoch start")
    if event["previous_event_sigil"] is not None:
        _fail("ISR3 sequence-one Event must have null predecessor")
    expected_journal = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    if state["journal_binding"] != expected_journal:
        _fail("ISR3 State journal binding disagrees with supplied Event")
    expected_head = {
        "journal_id": event["journal_id"],
        "last_sequence": event["sequence"],
        "last_event_id": event["event_id"],
        "last_event_sigil": event["event_sigil"],
    }
    if any(head[member] != value for member, value in expected_head.items()):
        _fail("ISR3 Head disagrees with supplied Event")
    payload = event["payload"]
    executor = state["executor"]
    expected_executor = {
        "executor_instance_id": event["executor_instance_id"],
        "executor_epoch": event["executor_epoch"],
        "executor_build_binding": payload["executor_build_binding"],
        "revision": 0,
        "clock_state": "TRUSTED",
        "last_trusted_utc": event["recorded_at"],
        "clock_uncertain_event_id": None,
        "active_recovery_id": None,
        "authority_gates": [],
        "last_event_id": event["event_id"],
        "last_event_sigil": event["event_sigil"],
    }
    if executor != expected_executor:
        _fail("ISR3 State executor projection disagrees with supplied Event")
    arrays = (
        "recoveries",
        "workers",
        "worker_sessions",
        "jobs",
        "attempts",
        "leases",
        "log_streams",
        "deadlines",
        "idempotency_records",
    )
    if any(state[member] for member in arrays):
        _fail("ISR3 State contains a noninitial projection member")


def replay_execution_initial_prefix_v1(
    events: list[dict[str, Any]], *, head: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Reduce exactly the ISR3 sequence-one prefix, otherwise fail closed.

    This is a deterministic cache construction primitive only.  It neither
    authenticates storage nor grants Journal append, runtime, or resolver
    authority.  Later Event reducers must be installed explicitly rather than
    being inferred from their Schema shape.
    """
    if len(events) != 1:
        _fail("Execution Journal replay supports only the initial one-Event prefix")
    event = events[0]
    validate_execution_journal_event_v1(event)
    if event["sequence"] != 1 or event["event_type"] != "executor.epoch_started":
        _fail("Execution Journal initial replay requires sequence-one executor epoch start")
    if event["previous_event_sigil"] is not None:
        _fail("Execution Journal initial replay requires a null predecessor")
    state = build_execution_state_v1(
        {
            "schema_version": "execution-state/1.0",
            "limit_profile": "EXECUTION_JOURNAL_V1_FIXED_LIMITS",
            "journal_binding": {
                "journal_id": event["journal_id"],
                "through_sequence": event["sequence"],
                "through_event_id": event["event_id"],
                "through_event_sigil": event["event_sigil"],
            },
            "executor": {
                "executor_instance_id": event["executor_instance_id"],
                "executor_epoch": event["executor_epoch"],
                "executor_build_binding": event["payload"]["executor_build_binding"],
                "revision": 0,
                "clock_state": "TRUSTED",
                "last_trusted_utc": event["recorded_at"],
                "clock_uncertain_event_id": None,
                "active_recovery_id": None,
                "authority_gates": [],
                "last_event_id": event["event_id"],
                "last_event_sigil": event["event_sigil"],
            },
            "recoveries": [],
            "workers": [],
            "worker_sessions": [],
            "jobs": [],
            "attempts": [],
            "leases": [],
            "log_streams": [],
            "deadlines": [],
            "idempotency_records": [],
        }
    )
    if head is not None:
        validate_execution_initial_state_supplied_facts_v1(event, state, head)
    return state


def validate_execution_job_v1(job: dict[str, Any]) -> None:
    """Validate one immutable Job wire without resolving its external bindings."""
    validate_instance("execution-job-1.0.json", job)
    _check_nfc(job)
    if job["job_binding_sigil"] != content_sigil(_without(job, "job_binding_sigil")):
        _fail("Execution Job self-Sigil mismatch")
    evidence = job["admission_chronicle_head_evidence"]
    if (
        evidence["job_id"] != job["job_id"]
        or evidence["start_request_sigil"] != job["start_request_sigil"]
        or evidence["observed_chronicle_head"] != job["admission_chronicle_head"]
        or evidence["evidence_sigil"] != content_sigil(_without(evidence, "evidence_sigil"))
    ):
        _fail("Execution Job admission evidence disagrees with Job binding")


def _initial_budget_ledger_v1(job_budget: dict[str, Any]) -> dict[str, Any]:
    ledger: dict[str, Any] = {}
    for dimension, limit in job_budget.items():
        ledger[dimension] = {
            "limit": limit,
            "reserved": 0,
            "consumed": 0,
            "exhaustion_status": "EXHAUSTED" if limit == 0 else "AVAILABLE",
        }
    ledger["budget_ledger_sigil"] = content_sigil(ledger)
    return ledger


def _reduce_job_submitted_v1(
    state: dict[str, Any], event: dict[str, Any], job: dict[str, Any]
) -> dict[str, Any]:
    """Reduce the supplied immutable Job's one-way submission projection."""
    validate_execution_job_v1(job)
    executor = state["executor"]
    if event["event_type"] != "job.submitted":
        _fail("internal reducer dispatch does not match Job submission")
    if (
        event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["executor_build_sigil"]
        != executor["executor_build_binding"]["executor_build_sigil"]
        or executor["clock_state"] != "TRUSTED"
        or executor["authority_gates"]
        or any(
            state[member]
            for member in (
                "recoveries",
                "workers",
                "worker_sessions",
                "jobs",
                "attempts",
                "leases",
                "log_streams",
                "deadlines",
                "idempotency_records",
            )
        )
    ):
        _fail("Job submission requires the ungated initial execution projection")
    payload = event["payload"]
    copied = (
        "job_binding_sigil",
        "start_request_sigil",
        "submission_idempotency_key_sigil",
        "admission_chronicle_head",
        "admission_chronicle_head_evidence",
        "deadline_due_at",
        "job_budget",
        "job_storage_roots",
    )
    if any(payload[member] != job[member] for member in copied):
        _fail("Job submission Event does not exactly copy its supplied Job")
    expected_revisions = [
        {
            "entity_kind": "JOB",
            "entity_id": job["job_id"],
            "preceding_revision": None,
            "next_revision": 0,
        }
    ]
    if event["entity_revisions"] != expected_revisions:
        _fail("Job submission Event has invalid Job creation revision")
    if event["idempotency_key_sigil"] != job["submission_idempotency_key_sigil"]:
        _fail("Job submission Event idempotency key disagrees with Job")
    ledger = _initial_budget_ledger_v1(job["job_budget"])
    if event["recorded_at"] != job["submitted_at"]:
        _fail("Job submission recorded_at disagrees with Job submitted_at")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["jobs"] = [
        {
            "job_id": job["job_id"],
            "revision": 0,
            "state": "SUBMITTED",
            "job_binding_sigil": job["job_binding_sigil"],
            "job_storage_roots": job["job_storage_roots"],
            "attempt_ids": [],
            "current_attempt_id": None,
            "fencing_counter": 0,
            "fence_floor": 0,
            "budget_ledger": ledger,
            "deadline_due_at": job["deadline_due_at"],
            "retry_eligible_due_at": None,
            "queue_key": None,
            "attempt_summaries": [],
            "selected_attempt_binding": None,
            "completion_anchor_binding": None,
            "first_stop_or_fence_binding": {"kind": "NONE"},
            "final_fence_binding": None,
            "storage_observation_binding": None,
            "terminal_source_binding": None,
            "output_hold_release_schedules": [],
            "job_assurance_binding": {"kind": "PENDING"},
            "terminal_event_binding": {"kind": "NONE"},
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
    ]
    reduced["deadlines"] = [
        {
            "deadline_kind": "JOB_DEADLINE",
            "due_at": job["deadline_due_at"],
            "fixed_priority": _DEADLINE_PRIORITY["JOB_DEADLINE"],
            "entity_id": job["job_id"],
            "source_event_id": event["event_id"],
            "source_event_sigil": event["event_sigil"],
        }
    ]
    reduced["idempotency_records"] = [
        {
            "operation_kind": "START_JOB",
            "scope_id": job["task_id"],
            "idempotency_key_sigil": job["submission_idempotency_key_sigil"],
            "request_sigil": job["start_request_sigil"],
            "disposition_event_id": event["event_id"],
            "disposition_event_sigil": event["event_sigil"],
        }
    ]
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def _reduce_job_queued_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Reduce a submitted Job to its deterministic ready-queue projection."""
    if event["event_type"] != "job.queued" or len(state["jobs"]) != 1:
        _fail("Job queue reducer requires exactly one submitted Job")
    job = state["jobs"][0]
    executor = state["executor"]
    if (
        job["state"] != "SUBMITTED"
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["executor_build_sigil"]
        != executor["executor_build_binding"]["executor_build_sigil"]
        or event["entity_revisions"]
        != [
            {
                "entity_kind": "JOB",
                "entity_id": job["job_id"],
                "preceding_revision": job["revision"],
                "next_revision": job["revision"] + 1,
            }
        ]
    ):
        _fail("Job queue Event disagrees with submitted Job projection")
    payload = event["payload"]
    if payload["queue_key"] != {"ready_sequence": event["sequence"], "job_id": job["job_id"]}:
        _fail("Job queue Event has an invalid queue key")
    if not isinstance(payload["admission_evidence_sigil"], str):
        _fail("Job queue Event admission evidence is invalid")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["jobs"] = [
        {
            **job,
            "revision": job["revision"] + 1,
            "state": "QUEUED",
            "queue_key": payload["queue_key"],
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
    ]
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def validate_execution_attempt_v1(attempt: dict[str, Any]) -> None:
    """Validate one immutable fresh Attempt without resolving its dependencies."""
    validate_instance("execution-attempt-1.0.json", attempt)
    _check_nfc(attempt)
    if attempt["attempt_binding_sigil"] != content_sigil(
        _without(attempt, "attempt_binding_sigil")
    ):
        _fail("Execution Attempt self-Sigil mismatch")


def validate_execution_worker_v1(worker: dict[str, Any]) -> None:
    """Validate one immutable Worker definition revision locally."""
    validate_instance("execution-worker-1.0.json", worker)
    _check_nfc(worker)
    if worker["worker_binding_sigil"] != content_sigil(_without(worker, "worker_binding_sigil")):
        _fail("Execution Worker self-Sigil mismatch")


def validate_execution_worker_session_v1(session: dict[str, Any]) -> None:
    """Validate one immutable Worker Session binding locally."""
    validate_instance("execution-worker-session-1.0.json", session)
    _check_nfc(session)
    if session["worker_session_binding_sigil"] != content_sigil(
        _without(session, "worker_session_binding_sigil")
    ):
        _fail("Execution Worker Session self-Sigil mismatch")


def validate_execution_worker_session_supplied_worker_v1(
    session: dict[str, Any], worker: dict[str, Any]
) -> None:
    """Bind a supplied Session to its exact immutable Worker definition."""
    validate_execution_worker_session_v1(session)
    validate_execution_worker_v1(worker)
    if (
        session["worker_id"] != worker["worker_id"]
        or session["worker_binding_sigil"] != worker["worker_binding_sigil"]
        or session["maximum_concurrency"] != worker["maximum_concurrency"]
    ):
        _fail("Execution Worker Session disagrees with supplied Worker")


def validate_execution_lease_v1(lease: dict[str, Any]) -> None:
    """Validate one immutable Lease offer without granting lease authority."""
    validate_instance("execution-lease-1.0.json", lease)
    _check_nfc(lease)
    if lease["lease_binding_sigil"] != content_sigil(_without(lease, "lease_binding_sigil")):
        _fail("Execution Lease self-Sigil mismatch")
    if not (
        _parse_time(lease["offered_at"])
        <= _parse_time(lease["claim_due_at"])
        <= _parse_time(lease["initial_expiry_due_at"])
        <= _parse_time(lease["maximum_expiry_due_at"])
    ):
        _fail("Execution Lease deadlines are not non-decreasing")


def validate_execution_lease_supplied_bindings_v1(
    lease: dict[str, Any],
    attempt: dict[str, Any],
    worker: dict[str, Any],
    session: dict[str, Any],
) -> None:
    """Compare a Lease offer to its exact supplied Attempt, Worker, and Session."""
    validate_execution_lease_v1(lease)
    validate_execution_attempt_v1(attempt)
    validate_execution_worker_session_supplied_worker_v1(session, worker)
    if (
        lease["job_id"] != attempt["job_id"]
        or lease["attempt_id"] != attempt["attempt_id"]
        or lease["fencing_generation"] != attempt["fencing_generation"]
        or lease["worker_id"] != worker["worker_id"]
        or lease["worker_binding_sigil"] != worker["worker_binding_sigil"]
        or lease["worker_session_id"] != session["worker_session_id"]
        or lease["worker_session_binding_sigil"] != session["worker_session_binding_sigil"]
        or lease["executor_instance_id"] != session["executor_instance_id"]
        or lease["executor_epoch"] != session["executor_epoch"]
    ):
        _fail("Execution Lease disagrees with supplied Attempt, Worker, or Session")


def _advance_journal_binding_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"], "through_sequence": event["sequence"],
        "through_event_id": event["event_id"], "through_event_sigil": event["event_sigil"],
    }
    return reduced


def _reduce_lease_offered_v1(state: dict[str, Any], event: dict[str, Any], lease: dict[str, Any]) -> dict[str, Any]:
    """Record one offered Lease without granting Worker execution authority."""
    validate_execution_lease_v1(lease)
    attempt = next((item for item in state["attempts"] if item["attempt_id"] == lease["attempt_id"]), None)
    session = next((item for item in state["worker_sessions"] if item["worker_session_id"] == lease["worker_session_id"]), None)
    worker = next((item for item in state["workers"] if item["worker_id"] == lease["worker_id"]), None)
    if attempt is None or session is None or worker is None:
        _fail("Lease offer requires a replayed Attempt, Worker, and Session")
    executor = state["executor"]
    expected_revisions = [
        {"entity_kind": "WORKER_SESSION", "entity_id": session["worker_session_id"], "preceding_revision": session["revision"], "next_revision": session["revision"] + 1},
        {"entity_kind": "ATTEMPT", "entity_id": attempt["attempt_id"], "preceding_revision": attempt["revision"], "next_revision": attempt["revision"] + 1},
        {"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": None, "next_revision": 0},
    ]
    payload = event["payload"]
    if (
        event["event_type"] != "lease.offered" or attempt["state"] != "READY" or session["state"] not in {"READY", "BUSY"}
        or session["capacity"] is None or session["capacity_in_use"] >= session["capacity"]
        or lease["job_id"] != attempt["job_id"] or lease["attempt_id"] != attempt["attempt_id"]
        or lease["fencing_generation"] != attempt["fencing_generation"]
        or lease["worker_id"] != worker["worker_id"] or lease["worker_binding_sigil"] != worker["worker_binding_sigil"]
        or lease["worker_session_id"] != session["worker_session_id"] or lease["worker_session_binding_sigil"] != session["worker_session_binding_sigil"]
        or lease["executor_epoch"] != session["executor_epoch"]
        or event["executor_instance_id"] != executor["executor_instance_id"] or event["executor_epoch"] != executor["executor_epoch"]
        or event["entity_revisions"] != expected_revisions
        or payload["lease_binding_sigil"] != lease["lease_binding_sigil"] or payload["credential_digest"] != lease["lease_credential_digest"]
        or any(payload[key] != lease[{"claim_due_at": "claim_due_at", "initial_expiry_due_at": "initial_expiry_due_at", "maximum_expiry_due_at": "maximum_expiry_due_at"}[key]] for key in ("claim_due_at", "initial_expiry_due_at", "maximum_expiry_due_at"))
    ):
        _fail("Lease offer Event disagrees with replayed state or supplied Lease")
    reduced = _advance_journal_binding_v1(state, event)
    reduced["attempts"] = [{**attempt, "revision": attempt["revision"] + 1, "worker_session_binding": {"kind": "BOUND", "worker_id": lease["worker_id"], "worker_binding_sigil": lease["worker_binding_sigil"], "worker_session_id": lease["worker_session_id"], "worker_session_binding_sigil": lease["worker_session_binding_sigil"]}, "lease_id": lease["lease_id"], "lease_terminal_binding": None, "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    reduced["worker_sessions"] = [{**session, "revision": session["revision"] + 1, "lease_ids": sorted([*session["lease_ids"], lease["lease_id"]], key=lambda value: _unsigned_ascii(value, "Lease ID")), "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    reduced["leases"] = [{"lease_id": lease["lease_id"], "revision": 0, "state": "OFFERED", "lease_binding_sigil": lease["lease_binding_sigil"], "job_id": lease["job_id"], "attempt_id": lease["attempt_id"], "worker_id": lease["worker_id"], "worker_session_id": lease["worker_session_id"], "executor_epoch": lease["executor_epoch"], "fencing_generation": lease["fencing_generation"], "claim_due_at": lease["claim_due_at"], "expiry_due_at": lease["initial_expiry_due_at"], "maximum_expiry_due_at": lease["maximum_expiry_due_at"], "last_heartbeat_sequence": None, "last_heartbeat_message_sigil": None, "last_resource_sample_sigil": None, "resource_counter_floors": {"cpu_time_seconds": None, "storage_bytes_written": None, "network_egress_bytes": None}, "next_heartbeat_due_at": None, "renewal_counter": 0, "terminal_event_binding": {"kind": "NONE"}, "tombstone_generation": None, "tombstone_event_sigil": None, "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    reduced["deadlines"] = sorted([*state["deadlines"], {"deadline_kind": "LEASE_CLAIM_DEADLINE", "due_at": lease["claim_due_at"], "fixed_priority": _DEADLINE_PRIORITY["LEASE_CLAIM_DEADLINE"], "entity_id": lease["lease_id"], "source_event_id": event["event_id"], "source_event_sigil": event["event_sigil"]}], key=lambda item: (_parse_time(item["due_at"]), item["fixed_priority"], _unsigned_ascii(item["entity_id"], "Deadline entity ID")))
    return build_execution_state_v1(reduced)


def _reduce_lease_claimed_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Atomically activate an offered Lease and its READY Attempt."""
    if len(state["leases"]) != 1 or len(state["attempts"]) != 1 or len(state["worker_sessions"]) != 1:
        _fail("Lease claim reducer requires one offered Lease, Attempt, and Session")
    lease, attempt, session = state["leases"][0], state["attempts"][0], state["worker_sessions"][0]
    executor = state["executor"]
    payload = event["payload"]
    expected_revisions = [
        {"entity_kind": "WORKER_SESSION", "entity_id": session["worker_session_id"], "preceding_revision": session["revision"], "next_revision": session["revision"] + 1},
        {"entity_kind": "ATTEMPT", "entity_id": attempt["attempt_id"], "preceding_revision": attempt["revision"], "next_revision": attempt["revision"] + 1},
        {"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": lease["revision"], "next_revision": lease["revision"] + 1},
    ]
    if (
        event["event_type"] != "lease.claimed" or lease["state"] != "OFFERED" or attempt["state"] != "READY"
        or session["state"] not in {"READY", "BUSY"} or session["capacity"] is None
        or session["capacity_in_use"] + 1 > session["capacity"]
        or attempt["lease_id"] != lease["lease_id"] or attempt["worker_session_binding"]["kind"] != "BOUND"
        or event["executor_instance_id"] != executor["executor_instance_id"] or event["executor_epoch"] != lease["executor_epoch"]
        or event["entity_revisions"] != expected_revisions
        or payload["claimed_at"] != event["recorded_at"] or _parse_time(payload["claimed_at"]) > _parse_time(lease["claim_due_at"])
        or payload["session_capacity_after"] != session["capacity_in_use"] + 1
    ):
        _fail("Lease claim Event disagrees with offered Lease state")
    fence = {"journal_id": event["journal_id"], "executor_epoch": lease["executor_epoch"], "job_id": lease["job_id"], "attempt_id": lease["attempt_id"], "lease_id": lease["lease_id"], "fencing_generation": lease["fencing_generation"]}
    reduced = _advance_journal_binding_v1(state, event)
    reduced["attempts"] = [{**attempt, "revision": attempt["revision"] + 1, "state": "LEASED", "lease_executor_epoch": lease["executor_epoch"], "public_fence_tuple": fence, "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    capacity_after = session["capacity_in_use"] + 1
    reduced["worker_sessions"] = [{**session, "revision": session["revision"] + 1, "state": "BUSY", "capacity_in_use": capacity_after, "next_heartbeat_due_at": payload["next_heartbeat_due_at"], "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    reduced["leases"] = [{**lease, "revision": lease["revision"] + 1, "state": "ACTIVE", "expiry_due_at": lease["initial_expiry_due_at"] if "initial_expiry_due_at" in lease else lease["expiry_due_at"], "next_heartbeat_due_at": payload["next_heartbeat_due_at"], "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    reduced["deadlines"] = sorted([item for item in state["deadlines"] if not (item["deadline_kind"] == "LEASE_CLAIM_DEADLINE" and item["entity_id"] == lease["lease_id"])] + [
        {"deadline_kind": "LEASE_EXPIRY", "due_at": lease["expiry_due_at"], "fixed_priority": _DEADLINE_PRIORITY["LEASE_EXPIRY"], "entity_id": lease["lease_id"], "source_event_id": event["event_id"], "source_event_sigil": event["event_sigil"]},
        {"deadline_kind": "HEARTBEAT_TIMEOUT", "due_at": payload["next_heartbeat_due_at"], "fixed_priority": _DEADLINE_PRIORITY["HEARTBEAT_TIMEOUT"], "entity_id": session["worker_session_id"], "source_event_id": event["event_id"], "source_event_sigil": event["event_sigil"]},
    ], key=lambda item: (_parse_time(item["due_at"]), item["fixed_priority"], _unsigned_ascii(item["entity_id"], "Deadline entity ID")))
    return build_execution_state_v1(reduced)


def _reduce_attempt_starting_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Advance a leased Attempt only while its exact Lease remains active."""
    if len(state["attempts"]) != 1 or len(state["leases"]) != 1:
        _fail("Attempt start reducer requires one leased Attempt and active Lease")
    attempt, lease = state["attempts"][0], state["leases"][0]
    executor = state["executor"]
    if (
        event["event_type"] != "attempt.starting" or attempt["state"] != "LEASED" or lease["state"] != "ACTIVE"
        or attempt["lease_id"] != lease["lease_id"] or attempt["lease_executor_epoch"] != lease["executor_epoch"]
        or attempt["public_fence_tuple"] != {"journal_id": event["journal_id"], "executor_epoch": lease["executor_epoch"], "job_id": lease["job_id"], "attempt_id": lease["attempt_id"], "lease_id": lease["lease_id"], "fencing_generation": lease["fencing_generation"]}
        or event["executor_instance_id"] != executor["executor_instance_id"] or event["executor_epoch"] != lease["executor_epoch"]
        or event["entity_revisions"] != [{"entity_kind": "ATTEMPT", "entity_id": attempt["attempt_id"], "preceding_revision": attempt["revision"], "next_revision": attempt["revision"] + 1}]
    ):
        _fail("Attempt start Event disagrees with active Lease authority")
    reduced = _advance_journal_binding_v1(state, event)
    reduced["attempts"] = [{**attempt, "revision": attempt["revision"] + 1, "state": "STARTING", "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    return build_execution_state_v1(reduced)


def _reduce_attempt_running_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Record that an already-started Attempt has entered its running phase."""
    if len(state["attempts"]) != 1 or len(state["leases"]) != 1:
        _fail("Attempt running reducer requires one starting Attempt and active Lease")
    attempt, lease = state["attempts"][0], state["leases"][0]
    executor = state["executor"]
    if (
        event["event_type"] != "attempt.running" or attempt["state"] != "STARTING" or lease["state"] != "ACTIVE"
        or event["executor_instance_id"] != executor["executor_instance_id"] or event["executor_epoch"] != lease["executor_epoch"]
        or event["entity_revisions"] != [{"entity_kind": "ATTEMPT", "entity_id": attempt["attempt_id"], "preceding_revision": attempt["revision"], "next_revision": attempt["revision"] + 1}]
    ):
        _fail("Attempt running Event disagrees with starting Attempt")
    reduced = _advance_journal_binding_v1(state, event)
    reduced["attempts"] = [{**attempt, "revision": attempt["revision"] + 1, "state": "RUNNING", "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    return build_execution_state_v1(reduced)


def _reduce_result_ingress_received_v1(
    state: dict[str, Any], event: dict[str, Any], receipt: dict[str, Any], intent: dict[str, Any]
) -> dict[str, Any]:
    """Record one immutable Worker-result receipt for a running Attempt.

    The supplied intent is deliberately compared, rather than treated as an
    append permission.  A caller still has to establish the durable Index and
    Journal Head separately.
    """
    validate_execution_result_ingress_receipt_v1(receipt)
    validate_execution_result_ingress_event_intent_v1(intent)
    if len(state["attempts"]) != 1 or len(state["leases"]) != 1:
        _fail("Result ingress reducer requires one running Attempt and active Lease")
    attempt, lease = state["attempts"][0], state["leases"][0]
    executor, payload = state["executor"], event["payload"]
    owner = receipt["owner_binding"]
    receipt_binding = {
        "ingress_receipt_id": receipt["ingress_receipt_id"],
        "ingress_receipt_sigil": receipt["ingress_receipt_sigil"],
    }
    expected_owner = {
        "job_id": attempt["job_id"], "job_binding_sigil": state["jobs"][0]["job_binding_sigil"],
        "attempt_id": attempt["attempt_id"], "attempt_binding_sigil": attempt["attempt_binding_sigil"],
        "lease_id": lease["lease_id"], "lease_binding_sigil": lease["lease_binding_sigil"],
        "worker_id": attempt["worker_session_binding"].get("worker_id"),
        "worker_binding_sigil": attempt["worker_session_binding"].get("worker_binding_sigil"),
        "worker_session_id": attempt["worker_session_binding"].get("worker_session_id"),
        "worker_session_binding_sigil": attempt["worker_session_binding"].get("worker_session_binding_sigil"),
        "executor_epoch": lease["executor_epoch"], "fence_tuple": attempt["public_fence_tuple"],
    }
    expected_payload = {
        "ingress_receipt_id": receipt["ingress_receipt_id"],
        "ingress_receipt_sigil": receipt["ingress_receipt_sigil"],
        "result_sigil": receipt["result_sigil"],
        "observation_evidence_subject_sigil": receipt["result_observation_binding"]["observation_evidence_subject_sigil"],
        "received_at": receipt["received_at"],
    }
    if (
        event["event_type"] != "attempt.result_ingress_received"
        or attempt["state"] != "RUNNING" or lease["state"] != "ACTIVE"
        or attempt["result_intake"] != {"kind": "NONE"}
        or owner != expected_owner
        or receipt["receiver_identity"]["executor_instance_id"] != executor["executor_instance_id"]
        or intent["result_ingress_receipt_binding"] != receipt_binding
        or intent["event_candidate"] != event
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != lease["executor_epoch"]
        or event["causation_event_id"] != attempt["last_event_id"]
        or event["entity_revisions"] != [{"entity_kind": "ATTEMPT", "entity_id": attempt["attempt_id"], "preceding_revision": attempt["revision"], "next_revision": attempt["revision"] + 1}]
        or payload != expected_payload
    ):
        _fail("Result ingress Event disagrees with running Attempt or supplied Receipt")
    reduced = _advance_journal_binding_v1(state, event)
    reduced["attempts"] = [{**attempt, "revision": attempt["revision"] + 1,
        "result_intake": {"kind": "RECEIVED", "result_ingress_receipt_binding": receipt_binding,
            "observation_evidence_subject_sigil": expected_payload["observation_evidence_subject_sigil"],
            "result_sigil": receipt["result_sigil"], "received_at": receipt["received_at"],
            "ingress_event_intent_id": intent["ingress_event_intent_id"], "ingress_event_id": event["event_id"],
            "ingress_event_sigil": event["event_sigil"]},
        "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    return build_execution_state_v1(reduced)


def _reduce_result_accepted_v1(
    state: dict[str, Any], event: dict[str, Any], evidence: dict[str, Any], receipt: dict[str, Any]
) -> dict[str, Any]:
    """Accept a received Result only from MATCHED supplied Observation Evidence."""
    validate_execution_observation_evidence_supplied_receipt_v1(evidence, receipt)
    if len(state["attempts"]) != 1 or len(state["leases"]) != 1:
        _fail("Result acceptance reducer requires one running Attempt and active Lease")
    attempt, lease = state["attempts"][0], state["leases"][0]
    executor, payload, intake = state["executor"], event["payload"], attempt["result_intake"]
    disposition = {"result_ingress_receipt_binding": intake["result_ingress_receipt_binding"],
        "observation_evidence_subject_sigil": intake["observation_evidence_subject_sigil"],
        "observation_evidence_id": evidence["observation_evidence_id"],
        "observation_evidence_sigil": evidence["observation_evidence_sigil"]}
    if (
        event["event_type"] != "attempt.result_accepted" or attempt["state"] != "RUNNING"
        or lease["state"] != "ACTIVE" or intake["kind"] != "RECEIVED"
        or evidence["assessment"]["kind"] != "MATCHED"
        or event["executor_instance_id"] != executor["executor_instance_id"] or event["executor_epoch"] != lease["executor_epoch"]
        or event["causation_event_id"] != intake["ingress_event_id"]
        or event["entity_revisions"] != [{"entity_kind": "ATTEMPT", "entity_id": attempt["attempt_id"], "preceding_revision": attempt["revision"], "next_revision": attempt["revision"] + 1}]
        or payload != {"result_sigil": intake["result_sigil"], "lease_revision": lease["revision"],
            "fence_tuple": attempt["public_fence_tuple"], "received_at": intake["received_at"],
            "validation_evidence_sigil": evidence["observation_evidence_sigil"],
            "observation_evidence_disposition_binding": disposition}
    ):
        _fail("Result acceptance Event disagrees with received Result or Observation Evidence")
    reduced = _advance_journal_binding_v1(state, event)
    result = {"kind": "ACCEPTED", "result_sigil": intake["result_sigil"],
        "disposition_event_id": event["event_id"], "disposition_event_sigil": event["event_sigil"],
        "disposition_sequence": event["sequence"]}
    reduced["attempts"] = [{**attempt, "revision": attempt["revision"] + 1, "result_binding": result,
        "result_intake": {**intake, "kind": "DISPOSED", "observation_evidence_id": evidence["observation_evidence_id"],
            "observation_evidence_sigil": evidence["observation_evidence_sigil"], "outcome": "ACCEPTED",
            "disposition_event_id": event["event_id"], "disposition_event_sigil": event["event_sigil"]},
        "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    return build_execution_state_v1(reduced)


def _reduce_result_rejected_v1(
    state: dict[str, Any], event: dict[str, Any], evidence: dict[str, Any], receipt: dict[str, Any]
) -> dict[str, Any]:
    """Freeze the first non-matching Result disposition before draining."""
    validate_execution_observation_evidence_supplied_receipt_v1(evidence, receipt)
    if len(state["attempts"]) != 1:
        _fail("Result rejection reducer requires one running Attempt")
    attempt, payload, executor = state["attempts"][0], event["payload"], state["executor"]
    intake = attempt["result_intake"]
    disposition = {"result_ingress_receipt_binding": intake["result_ingress_receipt_binding"],
        "observation_evidence_subject_sigil": intake["observation_evidence_subject_sigil"],
        "observation_evidence_id": evidence["observation_evidence_id"],
        "observation_evidence_sigil": evidence["observation_evidence_sigil"]}
    if (
        event["event_type"] != "attempt.result_rejected" or attempt["state"] != "RUNNING"
        or intake["kind"] != "RECEIVED" or attempt["result_binding"] != {"kind": "NONE"}
        or evidence["assessment"]["kind"] == "MATCHED"
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != attempt["lease_executor_epoch"]
        or event["causation_event_id"] != intake["ingress_event_id"]
        or event["entity_revisions"] != [{"entity_kind": "ATTEMPT", "entity_id": attempt["attempt_id"], "preceding_revision": attempt["revision"], "next_revision": attempt["revision"] + 1}]
        or payload.get("disposition_kind") != "FIRST_DISPOSITION_REJECTION"
        or payload.get("claimed_result_sigil") != intake["result_sigil"]
        or payload.get("received_at") != intake["received_at"]
        or payload.get("historical_disposition_event_id") is not None
        or payload.get("observation_evidence_disposition_binding") != disposition
        or not payload.get("reason_codes")
    ):
        _fail("Result rejection Event disagrees with received Result or Observation Evidence")
    reduced = _advance_journal_binding_v1(state, event)
    result = {"kind": "REJECTED", "message_sigil": payload["message_sigil"],
        "disposition_event_id": event["event_id"], "disposition_event_sigil": event["event_sigil"],
        "disposition_sequence": event["sequence"], "reason_codes": payload["reason_codes"]}
    reduced["attempts"] = [{**attempt, "revision": attempt["revision"] + 1, "result_binding": result,
        "result_intake": {**intake, "kind": "DISPOSED", "observation_evidence_id": evidence["observation_evidence_id"],
            "observation_evidence_sigil": evidence["observation_evidence_sigil"], "outcome": "REJECTED",
            "disposition_event_id": event["event_id"], "disposition_event_sigil": event["event_sigil"]},
        "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    return build_execution_state_v1(reduced)


def _reduce_attempt_draining_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Close a running Attempt after its immutable result disposition."""
    if len(state["attempts"]) != 1:
        _fail("Attempt draining reducer requires one running Attempt")
    attempt, payload = state["attempts"][0], event["payload"]
    executor = state["executor"]
    result = attempt["result_binding"]
    if result["kind"] == "ACCEPTED":
        anchor = {"kind": "RESULT_ACCEPTED", "event_id": result["disposition_event_id"],
            "event_sigil": result["disposition_event_sigil"], "sequence": result["disposition_sequence"],
            "result_sigil": result["result_sigil"]}
    elif result["kind"] == "NONE":
        anchor = {"kind": "NO_RESULT", "event_id": event["event_id"], "event_sigil": event["event_sigil"],
            "sequence": event["sequence"], "process_exit_observation_sigil": payload["process_exit_observation_sigil"]}
    elif result["kind"] == "REJECTED":
        anchor = {"kind": "NOT_ESTABLISHED"}
    else:
        _fail("Attempt draining Event has an unknown Result disposition")
    if (
        event["event_type"] != "attempt.draining" or attempt["state"] != "RUNNING"
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != attempt["lease_executor_epoch"]
        or event["causation_event_id"] != attempt["last_event_id"]
        or event["entity_revisions"] != [{"entity_kind": "ATTEMPT", "entity_id": attempt["attempt_id"], "preceding_revision": attempt["revision"], "next_revision": attempt["revision"] + 1}]
        or payload["result_binding"] != result
    ):
        _fail("Attempt draining Event disagrees with Result disposition")
    reduced = _advance_journal_binding_v1(state, event)
    reduced["attempts"] = [{**attempt, "revision": attempt["revision"] + 1, "state": "DRAINING",
        "completion_anchor_binding": anchor, "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    return build_execution_state_v1(reduced)


def _reduce_attempt_cleaning_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Freeze the terminal-source disposition before cleanup progresses."""
    if len(state["attempts"]) != 1:
        _fail("Attempt cleaning reducer requires one draining Attempt")
    attempt, payload, executor = state["attempts"][0], event["payload"], state["executor"]
    if (
        event["event_type"] != "attempt.cleaning" or attempt["state"] != "DRAINING"
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != attempt["lease_executor_epoch"]
        or event["causation_event_id"] != attempt["last_event_id"]
        or event["entity_revisions"] != [{"entity_kind": "ATTEMPT", "entity_id": attempt["attempt_id"], "preceding_revision": attempt["revision"], "next_revision": attempt["revision"] + 1}]
        or attempt["terminal_source_binding"] is not None
    ):
        _fail("Attempt cleaning Event disagrees with draining Attempt")
    reduced = _advance_journal_binding_v1(state, event)
    reduced["attempts"] = [{**attempt, "revision": attempt["revision"] + 1, "state": "CLEANING",
        "terminal_source_binding": payload["terminal_source_binding"], "last_event_id": event["event_id"],
        "last_event_sigil": event["event_sigil"]}]
    return build_execution_state_v1(reduced)


_NONFINAL_CLEANUP_STEPS_V1 = {
    "LOGS_CLOSED", "OUTPUTS_CLOSED", "TERMINATION_VERIFIED", "RESOURCES_CLEANED", "QUARANTINE_VERIFIED",
}


def _reduce_cleanup_progressed_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Replay a bounded non-final cleanup step without fabricating accounting."""
    if len(state["attempts"]) != 1:
        _fail("Cleanup progress reducer requires one Attempt")
    attempt, payload, executor = state["attempts"][0], event["payload"], state["executor"]
    if (
        event["event_type"] != "attempt.cleanup_progressed"
        or attempt["state"] not in {"DRAINING", "STOPPING", "CLEANING"}
        or payload["step"] not in _NONFINAL_CLEANUP_STEPS_V1
        or payload["finalization_bindings"] != {"kind": "NONE"}
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != attempt["lease_executor_epoch"]
        or event["causation_event_id"] != attempt["last_event_id"]
        or event["entity_revisions"] != [{"entity_kind": "ATTEMPT", "entity_id": attempt["attempt_id"], "preceding_revision": attempt["revision"], "next_revision": attempt["revision"] + 1}]
    ):
        _fail("Cleanup progress Event disagrees with Attempt state")
    reduced = _advance_journal_binding_v1(state, event)
    reduced["attempts"] = [{**attempt, "revision": attempt["revision"] + 1,
        "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    return build_execution_state_v1(reduced)


def _reduce_lease_released_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Close active Worker authority and publish its higher fence tombstone."""
    if len(state["jobs"]) != 1 or len(state["attempts"]) != 1 or len(state["leases"]) != 1 or len(state["worker_sessions"]) != 1:
        _fail("Lease release reducer requires one Job, Attempt, Lease, and Session")
    job, attempt, lease, session = state["jobs"][0], state["attempts"][0], state["leases"][0], state["worker_sessions"][0]
    executor, payload = state["executor"], event["payload"]
    expected_revisions = [
        {"entity_kind": "WORKER_SESSION", "entity_id": session["worker_session_id"], "preceding_revision": session["revision"], "next_revision": session["revision"] + 1},
        {"entity_kind": "JOB", "entity_id": job["job_id"], "preceding_revision": job["revision"], "next_revision": job["revision"] + 1},
        {"entity_kind": "ATTEMPT", "entity_id": attempt["attempt_id"], "preceding_revision": attempt["revision"], "next_revision": attempt["revision"] + 1},
        {"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": lease["revision"], "next_revision": lease["revision"] + 1},
    ]
    final_floor = attempt["fencing_generation"] + 1
    if (
        event["event_type"] != "lease.released" or lease["state"] != "ACTIVE"
        or attempt["lease_id"] != lease["lease_id"] or session["capacity_in_use"] < 1
        or event["executor_instance_id"] != executor["executor_instance_id"] or event["executor_epoch"] != lease["executor_epoch"]
        or event["causation_event_id"] != attempt["last_event_id"] or event["entity_revisions"] != expected_revisions
        or payload["prior_fence_floor"] != job["fence_floor"] or payload["tombstone_generation"] != final_floor
        or payload["session_capacity_after"] != session["capacity_in_use"] - 1
    ):
        _fail("Lease release Event disagrees with active Lease authority")
    reduced = _advance_journal_binding_v1(state, event)
    capacity_after = session["capacity_in_use"] - 1
    reduced["worker_sessions"] = [{**session, "revision": session["revision"] + 1,
        "state": "READY" if capacity_after == 0 else "BUSY", "capacity_in_use": capacity_after,
        "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    reduced["jobs"] = [{**job, "revision": job["revision"] + 1, "fence_floor": final_floor,
        "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    reduced["attempts"] = [{**attempt, "revision": attempt["revision"] + 1,
        "lease_terminal_binding": {"kind": "TERMINAL", "lease_id": lease["lease_id"], "lease_state": "RELEASED",
            "terminal_event_id": event["event_id"], "terminal_event_sigil": event["event_sigil"],
            "final_fence_floor": final_floor, "tombstone_event_sigil": payload["tombstone_publication_sigil"]},
        "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    reduced["leases"] = [{**lease, "revision": lease["revision"] + 1, "state": "RELEASED",
        "next_heartbeat_due_at": None, "tombstone_generation": final_floor,
        "tombstone_event_sigil": payload["tombstone_publication_sigil"], "last_event_id": event["event_id"],
        "last_event_sigil": event["event_sigil"]}]
    reduced["deadlines"] = [item for item in state["deadlines"] if not (
        item["entity_id"] in {lease["lease_id"], session["worker_session_id"]}
        and item["deadline_kind"] in {"LEASE_EXPIRY", "HEARTBEAT_TIMEOUT"}
    )]
    return build_execution_state_v1(reduced)


def _reduce_lease_heartbeat_accepted_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Advance one active Lease's monotonic supervisor-observed heartbeat."""
    if len(state["leases"]) != 1:
        _fail("Lease heartbeat reducer requires one active Lease")
    lease, payload, executor = state["leases"][0], event["payload"], state["executor"]
    prior = lease["last_heartbeat_sequence"]
    floors = payload["resource_counter_floors_after"]
    if (
        event["event_type"] != "lease.heartbeat_accepted" or lease["state"] != "ACTIVE"
        or event["executor_instance_id"] != executor["executor_instance_id"] or event["executor_epoch"] != lease["executor_epoch"]
        or event["entity_revisions"] != [{"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": lease["revision"], "next_revision": lease["revision"] + 1}]
        or payload["prior_accepted_sequence"] != prior or payload["sequence"] <= (prior or 0)
        or _parse_time(payload["received_at"]) > _parse_time(payload["next_heartbeat_due_at"])
        or _parse_time(payload["received_at"]) > _parse_time(lease["expiry_due_at"])
        or any(value is not None and value < (lease["resource_counter_floors"][key] or 0) for key, value in floors.items())
    ):
        _fail("Lease heartbeat Event disagrees with active Lease state")
    reduced = _advance_journal_binding_v1(state, event)
    reduced["leases"] = [{**lease, "revision": lease["revision"] + 1,
        "last_heartbeat_sequence": payload["sequence"], "last_heartbeat_message_sigil": payload["heartbeat_message_sigil"],
        "last_resource_sample_sigil": payload["resource_sample_sigil"], "resource_counter_floors": floors,
        "next_heartbeat_due_at": payload["next_heartbeat_due_at"], "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    reduced["deadlines"] = sorted([item for item in state["deadlines"] if not (item["deadline_kind"] == "HEARTBEAT_TIMEOUT" and item["entity_id"] == lease["worker_session_id"])] + [{"deadline_kind": "HEARTBEAT_TIMEOUT", "due_at": payload["next_heartbeat_due_at"], "fixed_priority": _DEADLINE_PRIORITY["HEARTBEAT_TIMEOUT"], "entity_id": lease["worker_session_id"], "source_event_id": event["event_id"], "source_event_sigil": event["event_sigil"]}], key=lambda item: (_parse_time(item["due_at"]), item["fixed_priority"], _unsigned_ascii(item["entity_id"], "Deadline entity ID")))
    return build_execution_state_v1(reduced)


def _reduce_lease_renewed_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Extend an active Lease only within its immutable maximum expiry."""
    if len(state["leases"]) != 1:
        _fail("Lease renewal reducer requires one active Lease")
    lease, payload, executor = state["leases"][0], event["payload"], state["executor"]
    if (
        event["event_type"] != "lease.renewed" or lease["state"] != "ACTIVE"
        or event["executor_instance_id"] != executor["executor_instance_id"] or event["executor_epoch"] != lease["executor_epoch"]
        or event["entity_revisions"] != [{"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": lease["revision"], "next_revision": lease["revision"] + 1}]
        or payload["prior_expiry_due_at"] != lease["expiry_due_at"]
        or not (_parse_time(lease["expiry_due_at"]) < _parse_time(payload["new_expiry_due_at"]) <= _parse_time(lease["maximum_expiry_due_at"]))
        or payload["renewal_counter"] != lease["renewal_counter"] + 1
    ):
        _fail("Lease renewal Event disagrees with active Lease state")
    reduced = _advance_journal_binding_v1(state, event)
    reduced["leases"] = [{**lease, "revision": lease["revision"] + 1, "expiry_due_at": payload["new_expiry_due_at"], "renewal_counter": payload["renewal_counter"], "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"]}]
    reduced["deadlines"] = sorted([item for item in state["deadlines"] if not (item["deadline_kind"] == "LEASE_EXPIRY" and item["entity_id"] == lease["lease_id"])] + [{"deadline_kind": "LEASE_EXPIRY", "due_at": payload["new_expiry_due_at"], "fixed_priority": _DEADLINE_PRIORITY["LEASE_EXPIRY"], "entity_id": lease["lease_id"], "source_event_id": event["event_id"], "source_event_sigil": event["event_sigil"]}], key=lambda item: (_parse_time(item["due_at"]), item["fixed_priority"], _unsigned_ascii(item["entity_id"], "Deadline entity ID")))
    return build_execution_state_v1(reduced)


def replay_execution_supplied_state_suffix_v1(
    state: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    supplied_leases: list[dict[str, Any]] | None = None,
    supplied_result_ingress_receipts: list[dict[str, Any]] | None = None,
    supplied_result_ingress_intents: list[dict[str, Any]] | None = None,
    supplied_observation_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Reduce installed suffix Events from one caller-supplied verified State.

    This is a deterministic supplied-facts comparator.  It does not prove that
    ``state`` is current, that its prefix is complete, or that an Event may be
    appended to a durable Journal.
    """
    validate_execution_state_v1(state)
    if not events:
        _fail("Execution supplied-state suffix requires at least one Event")
    current = state
    for event in events:
        validate_execution_journal_event_v1(event)
        prior = current["journal_binding"]
        if (
            event["journal_id"] != prior["journal_id"]
            or event["sequence"] != prior["through_sequence"] + 1
            or event["previous_event_sigil"] != prior["through_event_sigil"]
        ):
            _fail("Execution supplied-state suffix Event does not continue State")
        if event["event_type"] == "lease.offered":
            lease_id = event["entity_revisions"][-1]["entity_id"]
            lease = _find_supplied_v1(supplied_leases, lease_id, "lease_id", "Lease offer")
            current = _reduce_lease_offered_v1(current, event, lease)
        elif event["event_type"] == "lease.claimed":
            current = _reduce_lease_claimed_v1(current, event)
        elif event["event_type"] == "attempt.starting":
            current = _reduce_attempt_starting_v1(current, event)
        elif event["event_type"] == "attempt.running":
            current = _reduce_attempt_running_v1(current, event)
        elif event["event_type"] == "attempt.result_ingress_received":
            receipt = _find_supplied_v1(supplied_result_ingress_receipts, event["payload"]["ingress_receipt_id"], "ingress_receipt_id", "Result ingress")
            intent = _find_supplied_v1(supplied_result_ingress_intents, event["event_id"], "event_candidate.event_id", "Result ingress intent")
            current = _reduce_result_ingress_received_v1(current, event, receipt, intent)
        elif event["event_type"] == "attempt.result_accepted":
            evidence = _find_supplied_v1(supplied_observation_evidence, event["payload"]["observation_evidence_disposition_binding"]["observation_evidence_id"], "observation_evidence_id", "Result acceptance")
            intake = current["attempts"][0]["result_intake"]
            receipt = _find_supplied_v1(supplied_result_ingress_receipts, intake.get("result_ingress_receipt_binding", {}).get("ingress_receipt_id", ""), "ingress_receipt_id", "Result acceptance")
            current = _reduce_result_accepted_v1(current, event, evidence, receipt)
        elif event["event_type"] == "attempt.result_rejected":
            evidence = _find_supplied_v1(supplied_observation_evidence, event["payload"].get("observation_evidence_disposition_binding", {}).get("observation_evidence_id", ""), "observation_evidence_id", "Result rejection")
            intake = current["attempts"][0]["result_intake"]
            receipt = _find_supplied_v1(supplied_result_ingress_receipts, intake.get("result_ingress_receipt_binding", {}).get("ingress_receipt_id", ""), "ingress_receipt_id", "Result rejection")
            current = _reduce_result_rejected_v1(current, event, evidence, receipt)
        elif event["event_type"] == "attempt.draining":
            current = _reduce_attempt_draining_v1(current, event)
        elif event["event_type"] == "attempt.cleaning":
            current = _reduce_attempt_cleaning_v1(current, event)
        elif event["event_type"] == "attempt.cleanup_progressed":
            current = _reduce_cleanup_progressed_v1(current, event)
        elif event["event_type"] == "lease.released":
            current = _reduce_lease_released_v1(current, event)
        elif event["event_type"] == "lease.heartbeat_accepted":
            current = _reduce_lease_heartbeat_accepted_v1(current, event)
        elif event["event_type"] == "lease.renewed":
            current = _reduce_lease_renewed_v1(current, event)
        else:
            _fail("Execution supplied-state suffix reducer is unavailable for this Event")
    return current


def _find_supplied_v1(
    records: list[dict[str, Any]] | None, identifier: str, member: str, label: str
) -> dict[str, Any]:
    if records is None:
        _fail(f"{label} replay requires supplied immutable records")
    def member_value(record: dict[str, Any]) -> Any:
        value: Any = record
        for part in member.split("."):
            if not isinstance(value, dict):
                return _MISSING
            value = value.get(part, _MISSING)
        return value

    matches = [record for record in records if member_value(record) == identifier]
    if len(matches) != 1:
        _fail(f"{label} replay requires exactly one supplied immutable record")
    return matches[0]


def _reduce_worker_registered_v1(
    state: dict[str, Any], event: dict[str, Any], worker: dict[str, Any]
) -> dict[str, Any]:
    validate_execution_worker_v1(worker)
    executor = state["executor"]
    if (
        event["event_type"] != "worker.definition_registered"
        or any(item["worker_id"] == worker["worker_id"] for item in state["workers"])
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["executor_build_sigil"]
        != executor["executor_build_binding"]["executor_build_sigil"]
        or worker["definition_revision"] != 0
        or event["payload"]["worker_binding_sigil"] != worker["worker_binding_sigil"]
        or event["payload"]["definition_revision"] != 0
        or not isinstance(event["payload"]["supersedes_worker_binding_sigil"], str)
        or event["entity_revisions"]
        != [
            {
                "entity_kind": "WORKER",
                "entity_id": worker["worker_id"],
                "preceding_revision": None,
                "next_revision": 0,
            }
        ]
    ):
        _fail("Worker registration Event disagrees with supplied Worker")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["workers"] = [
        *state["workers"],
        {
            "worker_id": worker["worker_id"],
            "revision": 0,
            "state": "REGISTERED",
            "worker_binding_sigil": worker["worker_binding_sigil"],
            "definition_revision": 0,
            "worker_session_ids": [],
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        },
    ]
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def _reduce_worker_enabled_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    if event["event_type"] != "worker.enabled" or len(state["workers"]) != 1:
        _fail("Worker enable reducer requires one registered Worker")
    worker = state["workers"][0]
    executor = state["executor"]
    if (
        worker["state"] != "REGISTERED"
        or event["payload"]["worker_binding_sigil"] != worker["worker_binding_sigil"]
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["executor_build_sigil"]
        != executor["executor_build_binding"]["executor_build_sigil"]
        or event["entity_revisions"]
        != [
            {
                "entity_kind": "WORKER",
                "entity_id": worker["worker_id"],
                "preceding_revision": worker["revision"],
                "next_revision": worker["revision"] + 1,
            }
        ]
    ):
        _fail("Worker enable Event disagrees with registered Worker")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["workers"] = [
        {
            **worker,
            "revision": worker["revision"] + 1,
            "state": "ENABLED",
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
    ]
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def _reduce_worker_session_registered_v1(
    state: dict[str, Any], event: dict[str, Any], session: dict[str, Any]
) -> dict[str, Any]:
    worker = next(
        (item for item in state["workers"] if item["worker_id"] == session["worker_id"]), None
    )
    executor = state["executor"]
    if (
        event["event_type"] != "worker_session.registered"
        or worker is None
        or worker["state"] != "ENABLED"
        or any(
            item["worker_session_id"] == session["worker_session_id"]
            for item in state["worker_sessions"]
        )
        or session["worker_binding_sigil"] != worker["worker_binding_sigil"]
        or session["executor_instance_id"] != executor["executor_instance_id"]
        or session["executor_epoch"] != executor["executor_epoch"]
        or event["payload"]["worker_session_binding_sigil"]
        != session["worker_session_binding_sigil"]
        or event["payload"]["worker_binding_sigil"] != session["worker_binding_sigil"]
        or event["payload"]["backend_session_identity"] != session["backend_session_identity"]
        or event["payload"]["control_channel_identity_sigil"]
        != session["control_channel_identity_sigil"]
        or event["entity_revisions"]
        != [
            {
                "entity_kind": "WORKER_SESSION",
                "entity_id": session["worker_session_id"],
                "preceding_revision": None,
                "next_revision": 0,
            }
        ]
    ):
        _fail("Worker Session registration Event disagrees with supplied Session")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["workers"] = [
        {
            **worker,
            "worker_session_ids": sorted(
                [*worker["worker_session_ids"], session["worker_session_id"]],
                key=lambda value: _unsigned_ascii(value, "Worker session ID"),
            ),
        }
    ]
    reduced["worker_sessions"] = [
        {
            "worker_session_id": session["worker_session_id"],
            "revision": 0,
            "state": "REGISTERED",
            "worker_id": session["worker_id"],
            "worker_binding_sigil": session["worker_binding_sigil"],
            "worker_session_binding_sigil": session["worker_session_binding_sigil"],
            "executor_epoch": session["executor_epoch"],
            "worker_session_heartbeat_policy_id": None,
            "worker_session_heartbeat_policy_sigil": None,
            "capacity": None,
            "capacity_in_use": 0,
            "last_heartbeat_sequence": None,
            "last_heartbeat_message_sigil": None,
            "last_resource_sample_sigil": None,
            "resource_counter_floors": {
                "cpu_time_seconds": None,
                "storage_bytes_written": None,
                "network_egress_bytes": None,
            },
            "next_heartbeat_due_at": None,
            "lease_ids": [],
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
    ]
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def _reduce_worker_session_ready_v1(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    if event["event_type"] != "worker_session.ready" or len(state["worker_sessions"]) != 1:
        _fail("Worker Session ready reducer requires one registered Session")
    session = state["worker_sessions"][0]
    executor = state["executor"]
    payload = event["payload"]
    if (
        session["state"] != "REGISTERED"
        or payload["capacity"] < 1
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["entity_revisions"]
        != [
            {
                "entity_kind": "WORKER_SESSION",
                "entity_id": session["worker_session_id"],
                "preceding_revision": session["revision"],
                "next_revision": session["revision"] + 1,
            }
        ]
    ):
        _fail("Worker Session ready Event disagrees with registered Session")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["worker_sessions"] = [
        {
            **session,
            "revision": session["revision"] + 1,
            "state": "READY",
            "capacity": payload["capacity"],
            "worker_session_heartbeat_policy_id": payload["worker_session_heartbeat_policy_id"],
            "worker_session_heartbeat_policy_sigil": payload[
                "worker_session_heartbeat_policy_sigil"
            ],
            "next_heartbeat_due_at": payload["initial_heartbeat_due_at"],
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
    ]
    reduced["deadlines"] = [
        {
            "deadline_kind": "HEARTBEAT_TIMEOUT",
            "due_at": payload["initial_heartbeat_due_at"],
            "fixed_priority": _DEADLINE_PRIORITY["HEARTBEAT_TIMEOUT"],
            "entity_id": session["worker_session_id"],
            "source_event_id": event["event_id"],
            "source_event_sigil": event["event_sigil"],
        }
    ]
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def _reserved_budget_ledger_v1(
    ledger: dict[str, Any], reservation: dict[str, Any]
) -> dict[str, Any]:
    reduced: dict[str, Any] = {
        name: dict(value) for name, value in ledger.items() if name != "budget_ledger_sigil"
    }
    for dimension, value in reservation.items():
        updated = reduced[dimension]
        updated["reserved"] += value
        total = updated["reserved"] + updated["consumed"]
        updated["exhaustion_status"] = (
            "AVAILABLE"
            if total < updated["limit"]
            else "EXHAUSTED"
            if total == updated["limit"]
            else "EXCEEDED"
        )
        if total > updated["limit"]:
            _fail("Attempt allocation exceeds the Job budget")
    reduced["budget_ledger_sigil"] = content_sigil(reduced)
    return reduced


def _reduce_job_attempt_allocated_v1(
    state: dict[str, Any], event: dict[str, Any], attempt: dict[str, Any]
) -> dict[str, Any]:
    """Atomically allocate one fresh Attempt, budget reservation, and log streams."""
    validate_execution_attempt_v1(attempt)
    if event["event_type"] != "job.attempt_allocated" or len(state["jobs"]) != 1:
        _fail("Attempt allocation reducer requires exactly one queued Job")
    job = state["jobs"][0]
    executor = state["executor"]
    if (
        job["state"] != "QUEUED"
        or state["attempts"]
        or state["log_streams"]
        or attempt["job_id"] != job["job_id"]
        or attempt["job_binding_sigil"] != job["job_binding_sigil"]
        or attempt["retry_ordinal"] != 1
        or attempt["fencing_generation"] != 1
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["executor_build_sigil"]
        != executor["executor_build_binding"]["executor_build_sigil"]
    ):
        _fail("Attempt allocation disagrees with the queued Job projection")
    payload = event["payload"]
    if (
        payload["attempt_binding_sigil"] != attempt["attempt_binding_sigil"]
        or payload["retry_ordinal"] != attempt["retry_ordinal"]
        or payload["fencing_generation"] != attempt["fencing_generation"]
        or payload["budget_reservation"] != attempt["budget_reservation"]
        or payload["prior_fencing_counter"] != job["fencing_counter"]
        or payload["resulting_fence_floor"] != attempt["fencing_generation"]
        or event["recorded_at"] != attempt["created_at"]
    ):
        _fail("Attempt allocation Event does not exactly copy Attempt allocation facts")
    ledger = _reserved_budget_ledger_v1(job["budget_ledger"], attempt["budget_reservation"])
    if payload["resulting_budget_ledger_sigil"] != ledger["budget_ledger_sigil"]:
        _fail("Attempt allocation Event budget ledger Sigil mismatch")
    log_ids = attempt["log_stream_ids"]
    log_revisions = sorted(
        (
            {
                "entity_kind": "LOG_STREAM",
                "entity_id": log_ids[stream],
                "preceding_revision": None,
                "next_revision": 0,
            }
            for stream in ("STDOUT", "STDERR", "STRUCTURED")
        ),
        key=lambda item: _unsigned_ascii(item["entity_id"], "Log stream ID"),
    )
    expected_revisions = [
        {
            "entity_kind": "JOB",
            "entity_id": job["job_id"],
            "preceding_revision": job["revision"],
            "next_revision": job["revision"] + 1,
        },
        {
            "entity_kind": "ATTEMPT",
            "entity_id": attempt["attempt_id"],
            "preceding_revision": None,
            "next_revision": 0,
        },
        *log_revisions,
    ]
    if event["entity_revisions"] != expected_revisions:
        _fail("Attempt allocation Event has invalid atomic revision effects")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["jobs"] = [
        {
            **job,
            "revision": job["revision"] + 1,
            "state": "ACTIVE",
            "attempt_ids": [attempt["attempt_id"]],
            "current_attempt_id": attempt["attempt_id"],
            "fencing_counter": attempt["fencing_generation"],
            "fence_floor": attempt["fencing_generation"],
            "budget_ledger": ledger,
            "queue_key": None,
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
    ]
    reduced["attempts"] = [
        {
            "attempt_id": attempt["attempt_id"],
            "revision": 0,
            "state": "CREATED",
            "attempt_binding_sigil": attempt["attempt_binding_sigil"],
            "job_id": job["job_id"],
            "retry_ordinal": attempt["retry_ordinal"],
            "fencing_generation": attempt["fencing_generation"],
            "lease_executor_epoch": None,
            "public_fence_tuple": None,
            "worker_session_binding": {"kind": "NONE"},
            "lease_id": None,
            "result_binding": {"kind": "NONE"},
            "result_intake": {"kind": "NONE"},
            "output_staging_preallocations": [],
            "attempt_authorization_requirement": attempt["attempt_authorization_requirement"],
            "attempt_authorization_state": {"kind": "NONE"}
            if attempt["attempt_authorization_requirement"]["kind"] == "NONE"
            else {"kind": "PENDING"},
            "completion_anchor_binding": {"kind": "NOT_ESTABLISHED"},
            "lease_terminal_binding": None,
            "first_stop_or_fence_binding": {"kind": "NONE"},
            "storage_observation_binding": None,
            "terminal_source_binding": None,
            "accounting_capture_binding": {"kind": "PENDING"},
            "budget_settlement_binding": {"kind": "PENDING"},
            "attempt_assurance_binding": {"kind": "PENDING"},
            "input_storage_roots": [],
            "output_storage_roots": [],
            "control_evidence_set_binding": {"kind": "PENDING"},
            "quarantine_binding_set_binding": {"kind": "PENDING"},
            "terminalization_storage_manifest_binding": {"kind": "PENDING"},
            "output_root_protection": {"kind": "PENDING"},
            "deadline_due_at": attempt["deadline_due_at"],
            "grace_due_at": None,
            "terminal_event_binding": {"kind": "NONE"},
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
    ]
    reduced["log_streams"] = [
        {
            "log_stream_id": log_ids[stream],
            "revision": 0,
            "state": "OPEN",
            "attempt_id": attempt["attempt_id"],
            "stream": stream,
            "next_sequence": 0,
            "captured_bytes": 0,
            "dropped_bytes": 0,
            "truncated": False,
            "final_sequence": None,
            "stream_set_sigil": None,
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
        for stream in ("STDOUT", "STDERR", "STRUCTURED")
    ]
    reduced["deadlines"] = [
        *state["deadlines"],
        {
            "deadline_kind": "ATTEMPT_DEADLINE",
            "due_at": attempt["deadline_due_at"],
            "fixed_priority": _DEADLINE_PRIORITY["ATTEMPT_DEADLINE"],
            "entity_id": attempt["attempt_id"],
            "source_event_id": event["event_id"],
            "source_event_sigil": event["event_sigil"],
        },
    ]
    reduced["deadlines"].sort(
        key=lambda item: (
            _parse_time(item["due_at"]),
            item["fixed_priority"],
            _unsigned_ascii(item["entity_id"], "Deadline entity ID"),
        )
    )
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def _reduce_attempt_preflight_started_v1(
    state: dict[str, Any], event: dict[str, Any]
) -> dict[str, Any]:
    """Reduce a CREATED Attempt after its immutable bindings have been rechecked."""
    if event["event_type"] != "attempt.preflight_started" or len(state["attempts"]) != 1:
        _fail("Attempt preflight reducer requires exactly one created Attempt")
    attempt = state["attempts"][0]
    executor = state["executor"]
    if (
        attempt["state"] != "CREATED"
        or (
            attempt["attempt_authorization_requirement"]["kind"] == "REQUIRED"
            and attempt["attempt_authorization_state"]["kind"] != "BOUND"
        )
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["executor_build_sigil"]
        != executor["executor_build_binding"]["executor_build_sigil"]
        or event["entity_revisions"]
        != [
            {
                "entity_kind": "ATTEMPT",
                "entity_id": attempt["attempt_id"],
                "preceding_revision": attempt["revision"],
                "next_revision": attempt["revision"] + 1,
            }
        ]
    ):
        _fail("Attempt preflight Event disagrees with created Attempt projection")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["attempts"] = [
        {
            **attempt,
            "revision": attempt["revision"] + 1,
            "state": "PREFLIGHTING",
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
    ]
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def _reduce_attempt_preflight_passed_v1(
    state: dict[str, Any], event: dict[str, Any]
) -> dict[str, Any]:
    """Reduce a completed preflight while retaining only its immutable root bindings."""
    if event["event_type"] != "attempt.preflight_passed" or len(state["attempts"]) != 1:
        _fail("Attempt preflight-pass reducer requires exactly one preflighting Attempt")
    attempt = state["attempts"][0]
    executor = state["executor"]
    roots = event["payload"]["input_storage_roots"]
    if (
        attempt["state"] != "PREFLIGHTING"
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["executor_build_sigil"]
        != executor["executor_build_binding"]["executor_build_sigil"]
        or event["entity_revisions"]
        != [
            {
                "entity_kind": "ATTEMPT",
                "entity_id": attempt["attempt_id"],
                "preceding_revision": attempt["revision"],
                "next_revision": attempt["revision"] + 1,
            }
        ]
        or any(
            root["root_kind"] != "ATTEMPT_INPUT"
            or root["job_id"] != attempt["job_id"]
            or root["attempt_id"] != attempt["attempt_id"]
            for root in roots
        )
    ):
        _fail("Attempt preflight-pass Event disagrees with preflighting Attempt projection")
    if len(roots) > 1:
        _fail("Attempt preflight-pass Event has too many input storage roots")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["attempts"] = [
        {
            **attempt,
            "revision": attempt["revision"] + 1,
            "state": "READY",
            "input_storage_roots": roots,
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
    ]
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def _reduce_executor_clock_uncertain_after_initial_v1(
    state: dict[str, Any], event: dict[str, Any]
) -> dict[str, Any]:
    """Reduce the no-live-authority clock gate immediately after ISR3."""
    executor = state["executor"]
    if event["event_type"] != "executor.clock_uncertain":
        _fail("internal reducer dispatch does not match executor clock uncertainty")
    if (
        event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["executor_build_sigil"]
        != executor["executor_build_binding"]["executor_build_sigil"]
    ):
        _fail("Clock uncertainty Event disagrees with replayed Executor identity")
    if executor["clock_state"] != "TRUSTED" or executor["authority_gates"]:
        _fail("Clock uncertainty Event requires an ungated trusted Executor")
    revision = event["entity_revisions"]
    expected_revision = [
        {
            "entity_kind": "EXECUTOR",
            "entity_id": executor["executor_instance_id"],
            "preceding_revision": executor["revision"],
            "next_revision": executor["revision"] + 1,
        }
    ]
    if revision != expected_revision:
        _fail("Clock uncertainty Event has invalid Executor revision effect")
    payload = event["payload"]
    if payload["last_trusted_utc"] != executor["last_trusted_utc"]:
        _fail("Clock uncertainty Event disagrees with replayed trusted-time anchor")
    if payload["affected_lease_ids"]:
        _fail("Clock uncertainty reducer requires no live Lease authority")
    if any(
        state[member]
        for member in (
            "workers",
            "worker_sessions",
            "jobs",
            "attempts",
            "leases",
            "log_streams",
            "deadlines",
            "idempotency_records",
            "recoveries",
        )
    ):
        _fail("Clock uncertainty reducer requires the initial empty projections")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced_executor = {
        **executor,
        "revision": executor["revision"] + 1,
        "clock_state": "UNCERTAIN",
        "clock_uncertain_event_id": event["event_id"],
        "authority_gates": ["CLOCK_UNCERTAIN"],
        "last_event_id": event["event_id"],
        "last_event_sigil": event["event_sigil"],
    }
    reduced["executor"] = reduced_executor
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def _reduce_recovery_started_after_clock_uncertain_v1(
    state: dict[str, Any], event: dict[str, Any]
) -> dict[str, Any]:
    """Reduce the empty-projection Recovery start after the clock gate."""
    executor = state["executor"]
    if event["event_type"] != "recovery.started":
        _fail("internal reducer dispatch does not match Recovery start")
    if (
        event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["executor_build_sigil"]
        != executor["executor_build_binding"]["executor_build_sigil"]
    ):
        _fail("Recovery start Event disagrees with replayed Executor identity")
    if (
        executor["clock_state"] != "UNCERTAIN"
        or executor["active_recovery_id"] is not None
        or executor["authority_gates"] != ["CLOCK_UNCERTAIN"]
        or state["recoveries"]
    ):
        _fail("Recovery start requires the clock-gated initial projection")
    if event["recovery_action_binding"] is not None:
        _fail("Recovery start must not carry a Recovery action binding")
    payload = event["payload"]
    if (
        payload["replay_through_sequence"] != state["journal_binding"]["through_sequence"]
        or payload["replay_through_event_sigil"] != state["journal_binding"]["through_event_sigil"]
        or payload["old_epoch"] != executor["executor_epoch"]
        or payload["new_epoch"] != executor["executor_epoch"]
        or payload["prior_recovery_id"] is not None
    ):
        _fail("Recovery start payload disagrees with clock-gated prefix")
    if any(
        payload[member]
        for member in (
            "nonterminal_job_ids",
            "nonterminal_attempt_ids",
            "nonterminal_lease_ids",
            "nonterminal_worker_session_ids",
        )
    ):
        _fail("Recovery start reducer requires empty nonterminal projections")
    if any(
        state[member]
        for member in (
            "workers",
            "worker_sessions",
            "jobs",
            "attempts",
            "leases",
            "log_streams",
            "deadlines",
            "idempotency_records",
        )
    ):
        _fail("Recovery start reducer requires the initial empty projections")
    expected_revisions = [
        {
            "entity_kind": "EXECUTOR",
            "entity_id": executor["executor_instance_id"],
            "preceding_revision": executor["revision"],
            "next_revision": executor["revision"] + 1,
        },
        {
            "entity_kind": "RECOVERY",
            "entity_id": payload["recovery_id"],
            "preceding_revision": None,
            "next_revision": 0,
        },
    ]
    if event["entity_revisions"] != expected_revisions:
        _fail("Recovery start Event has invalid revision effects")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["executor"] = {
        **executor,
        "revision": executor["revision"] + 1,
        "active_recovery_id": payload["recovery_id"],
        "authority_gates": ["CLOCK_UNCERTAIN", "RECOVERY_ACTIVE"],
        "last_event_id": event["event_id"],
        "last_event_sigil": event["event_sigil"],
    }
    reduced["recoveries"] = [
        {
            "recovery_id": payload["recovery_id"],
            "revision": 0,
            "state": "STARTED",
            "prior_recovery_id": None,
            "started_event_sigil": event["event_sigil"],
            "current_action_set_sigil": payload["initial_action_set_sigil"],
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
    ]
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def validate_execution_journal_prefix_wire_v1(
    events: list[dict[str, Any]],
    *,
    head: dict[str, Any] | None = None,
) -> None:
    """Validate a caller-supplied Journal chain without reducing its State.

    This checks only closed Event bytes, ordering, and an optionally supplied
    Head endpoint.  It does not establish completeness, durability, currentness,
    replay equivalence, append authority, or any runtime authority.
    """
    if not events:
        _fail("Execution Journal prefix requires a nonempty sequence")
    if not all(isinstance(event, dict) for event in events):
        _fail("Execution Journal prefix contains a nonobject Event")
    if events[0].get("event_type") != "executor.epoch_started":
        _fail("Execution Journal prefix must begin with executor epoch start")
    journal_id = events[0].get("journal_id")
    previous_sigil: str | None = None
    previous_recorded_at: datetime | None = None
    event_ids: set[str] = set()
    epoch_build_sigils: dict[tuple[str, int], str] = {}
    for expected_sequence, event in enumerate(events, 1):
        validate_execution_journal_event_v1(event)
        if event["journal_id"] != journal_id:
            _fail("Execution Journal prefix contains multiple journal identities")
        if event["event_id"] in event_ids:
            _fail("Execution Journal prefix contains a duplicate Event identity")
        if event["sequence"] != expected_sequence:
            _fail("Execution Journal prefix has a sequence gap")
        if event["previous_event_sigil"] != previous_sigil:
            _fail("Execution Journal prefix has a broken Event chain")
        recorded_at = _parse_time(event["recorded_at"])
        if previous_recorded_at is not None and recorded_at < previous_recorded_at:
            _fail("Execution Journal prefix has decreasing recorded_at time")
        epoch_key = (event["executor_instance_id"], event["executor_epoch"])
        prior_build_sigil = epoch_build_sigils.setdefault(epoch_key, event["executor_build_sigil"])
        if event["executor_build_sigil"] != prior_build_sigil:
            _fail("Execution Journal prefix has conflicting Executor build Sigils")
        previous_sigil = event["event_sigil"]
        previous_recorded_at = recorded_at
        event_ids.add(event["event_id"])
    if head is not None:
        validate_execution_journal_head_v1(head)
        last = events[-1]
        if (
            head["journal_id"] != journal_id
            or head["last_sequence"] != last["sequence"]
            or head["last_event_id"] != last["event_id"]
            or head["last_event_sigil"] != last["event_sigil"]
        ):
            _fail("Execution Journal Head disagrees with supplied prefix")


def replay_execution_journal_prefix_v1(
    events: list[dict[str, Any]],
    *,
    head: dict[str, Any] | None = None,
    recovery_action_sets: list[dict[str, Any]] | None = None,
    supplied_jobs: list[dict[str, Any]] | None = None,
    supplied_attempts: list[dict[str, Any]] | None = None,
    supplied_workers: list[dict[str, Any]] | None = None,
    supplied_worker_sessions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Verify a v1 Journal prefix and reduce its installed bounded suffixes.

    Prefix integrity is checked before reducer dispatch.  A syntactically valid
    Event outside the explicitly installed ISR3/clock-gate/empty-Recovery path
    fails closed rather than being interpreted as a no-op or guessed transition.
    ``recovery_action_sets`` is required only for the six-Event, action-free
    Recovery control path; it is not an authority to derive or execute actions.
    """
    if not events:
        _fail("Execution Journal replay requires a nonempty prefix")
    if recovery_action_sets is not None:
        if supplied_jobs is not None:
            _fail("Execution Journal replay cannot combine Recovery action sets and supplied Jobs")
        if supplied_attempts is not None:
            _fail(
                "Execution Journal replay cannot combine Recovery action sets and supplied Attempts"
            )
        if supplied_workers is not None or supplied_worker_sessions is not None:
            _fail(
                "Execution Journal replay cannot combine Recovery action sets and supplied Worker records"
            )
        empty_recovery_types = [
            "executor.epoch_started",
            "executor.clock_uncertain",
            "recovery.started",
            "recovery.phase_advanced",
            "recovery.phase_advanced",
            "recovery.phase_advanced",
        ]
        if [
            event.get("event_type") if isinstance(event, dict) else None for event in events
        ] != empty_recovery_types:
            _fail(
                "Execution Journal recovery action sets are only supported for the empty Recovery path"
            )
        return replay_execution_empty_recovery_phase_prefix_v1(
            events,
            recovery_action_sets,
            head=head,
        )
    validate_execution_journal_prefix_wire_v1(events, head=head)
    initial_state = replay_execution_initial_prefix_v1([events[0]])
    if len(events) == 1:
        if head is not None:
            validate_execution_initial_state_supplied_facts_v1(events[0], initial_state, head)
        return initial_state
    worker_prefix = [event["event_type"] for event in events[1:]]
    if worker_prefix and worker_prefix[0] == "worker.definition_registered":
        if len(events) > 5:
            _fail("Worker/Session replay supports only the installed registration prefix")
        worker_id = events[1]["entity_revisions"][0]["entity_id"]
        worker = _find_supplied_v1(supplied_workers, worker_id, "worker_id", "Worker registration")
        state = _reduce_worker_registered_v1(initial_state, events[1], worker)
        if len(events) >= 3:
            state = _reduce_worker_enabled_v1(state, events[2])
        if len(events) >= 4:
            session_id = events[3]["entity_revisions"][0]["entity_id"]
            session = _find_supplied_v1(
                supplied_worker_sessions,
                session_id,
                "worker_session_id",
                "Worker Session registration",
            )
            validate_execution_worker_session_supplied_worker_v1(session, worker)
            state = _reduce_worker_session_registered_v1(state, events[3], session)
        if len(events) == 5:
            state = _reduce_worker_session_ready_v1(state, events[4])
        if head is not None and (
            head["journal_id"] != state["journal_binding"]["journal_id"]
            or head["last_sequence"] != events[-1]["sequence"]
            or head["last_event_id"] != events[-1]["event_id"]
            or head["last_event_sigil"] != events[-1]["event_sigil"]
        ):
            _fail("Execution Journal Head disagrees with replay prefix")
        return state
    if len(events) in {2, 3, 4, 5, 6} and events[1]["event_type"] == "job.submitted":
        if supplied_jobs is None or len(supplied_jobs) != 1:
            _fail("Job submission replay requires exactly one supplied Job")
        state = _reduce_job_submitted_v1(initial_state, events[1], supplied_jobs[0])
        if len(events) == 3:
            state = _reduce_job_queued_v1(state, events[2])
        if len(events) == 4:
            if (
                events[2]["event_type"] != "job.queued"
                or supplied_attempts is None
                or len(supplied_attempts) != 1
            ):
                _fail("Attempt allocation replay requires one supplied Attempt after job.queued")
            state = _reduce_job_queued_v1(state, events[2])
            state = _reduce_job_attempt_allocated_v1(state, events[3], supplied_attempts[0])
        if len(events) == 5:
            if (
                events[2]["event_type"] != "job.queued"
                or supplied_attempts is None
                or len(supplied_attempts) != 1
            ):
                _fail("Attempt preflight replay requires one supplied Attempt after allocation")
            state = _reduce_job_queued_v1(state, events[2])
            state = _reduce_job_attempt_allocated_v1(state, events[3], supplied_attempts[0])
            state = _reduce_attempt_preflight_started_v1(state, events[4])
        if len(events) == 6:
            if (
                events[2]["event_type"] != "job.queued"
                or supplied_attempts is None
                or len(supplied_attempts) != 1
            ):
                _fail(
                    "Attempt preflight-pass replay requires one supplied Attempt after allocation"
                )
            state = _reduce_job_queued_v1(state, events[2])
            state = _reduce_job_attempt_allocated_v1(state, events[3], supplied_attempts[0])
            state = _reduce_attempt_preflight_started_v1(state, events[4])
            state = _reduce_attempt_preflight_passed_v1(state, events[5])
        if head is not None and (
            head["journal_id"] != state["journal_binding"]["journal_id"]
            or head["last_sequence"] != events[-1]["sequence"]
            or head["last_event_id"] != events[-1]["event_id"]
            or head["last_event_sigil"] != events[-1]["event_sigil"]
        ):
            _fail("Execution Journal Head disagrees with replay prefix")
        return state
    if supplied_jobs is not None:
        _fail("supplied Jobs are unsupported for this Execution Journal replay prefix")
    if supplied_attempts is not None:
        _fail("supplied Attempts are unsupported for this Execution Journal replay prefix")
    if supplied_workers is not None or supplied_worker_sessions is not None:
        _fail("supplied Worker records are unsupported for this Execution Journal replay prefix")
    if len(events) >= 2 and events[1]["event_type"] == "executor.clock_uncertain":
        state = _reduce_executor_clock_uncertain_after_initial_v1(initial_state, events[1])
        if len(events) == 3 and events[2]["event_type"] == "recovery.started":
            state = _reduce_recovery_started_after_clock_uncertain_v1(state, events[2])
        elif len(events) != 2:
            _fail("Execution Journal replay reducer is unavailable for later Events")
        if head is not None:
            last = events[-1]
            if (
                head["journal_id"] != state["journal_binding"]["journal_id"]
                or head["last_sequence"] != last["sequence"]
                or head["last_event_id"] != last["event_id"]
                or head["last_event_sigil"] != last["event_sigil"]
            ):
                _fail("Execution Journal Head disagrees with replay prefix")
        return state
    _fail("Execution Journal replay reducer is unavailable for later Events")


def _reduce_empty_recovery_phase_advance_v1(
    state: dict[str, Any],
    event: dict[str, Any],
    completed_action_set: dict[str, Any],
    next_action_set: dict[str, Any],
) -> dict[str, Any]:
    """Reduce one action-free Recovery phase transition.

    Callers establish sealed action-set availability separately.  This reducer
    deliberately accepts only empty action sets and empty completion effects,
    so it cannot mistake an omitted operational consequence for a completed
    Recovery action.
    """
    validate_execution_recovery_phase_advance_supplied_action_sets_v1(
        state,
        event,
        completed_action_set,
        next_action_set,
    )
    executor = state["executor"]
    recovery_id = executor["active_recovery_id"]
    if recovery_id is None:
        _fail("empty Recovery phase reducer requires an active Recovery")
    recovery = next(item for item in state["recoveries"] if item["recovery_id"] == recovery_id)
    if (
        event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["executor_build_sigil"]
        != executor["executor_build_binding"]["executor_build_sigil"]
        or completed_action_set["actions"]
        or next_action_set["actions"]
        or event["payload"]["completed_entity_ids"]
        or event["payload"]["quarantined_entity_ids"]
    ):
        _fail("empty Recovery phase reducer received operational action effects")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["recoveries"] = [
        {
            **recovery,
            "revision": recovery["revision"] + 1,
            "state": event["payload"]["to_phase"],
            "current_action_set_sigil": next_action_set["action_set_sigil"],
            "last_event_id": event["event_id"],
            "last_event_sigil": event["event_sigil"],
        }
    ]
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"],
        "through_sequence": event["sequence"],
        "through_event_id": event["event_id"],
        "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def replay_execution_empty_recovery_phase_prefix_v1(
    events: list[dict[str, Any]],
    recovery_action_sets: list[dict[str, Any]],
    *,
    head: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reduce the action-free ``STARTED -> FINALIZING`` Recovery control path.

    This narrow deterministic projection is intentionally not a general
    Journal replay: it requires the initial empty State, an uncertain clock,
    four sealed empty action sets, and exactly the three phase transitions.
    It neither establishes durable action-set availability nor handles
    ``recovery.completed``, whose post-State assertion needs the complete
    installed reducer and external durable facts.
    """
    if len(events) != 6 or len(recovery_action_sets) != 4:
        _fail("empty Recovery phase replay requires six Events and four action sets")
    validate_execution_journal_prefix_wire_v1(events, head=head)
    if [event["event_type"] for event in events] != [
        "executor.epoch_started",
        "executor.clock_uncertain",
        "recovery.started",
        "recovery.phase_advanced",
        "recovery.phase_advanced",
        "recovery.phase_advanced",
    ]:
        _fail("empty Recovery phase replay has an unsupported Event sequence")
    for action_set in recovery_action_sets:
        validate_execution_recovery_action_set_v1(action_set)
        if action_set["actions"] or action_set["supersedes_action_set_sigil"] is not None:
            _fail("empty Recovery phase replay requires initial empty action sets")
    state = replay_execution_journal_prefix_v1(events[:3])
    started_set = recovery_action_sets[0]
    validate_execution_recovery_start_supplied_action_set_v1(
        events[2],
        started_set,
        events[:2],
    )
    if state["recoveries"][0]["current_action_set_sigil"] != started_set["action_set_sigil"]:
        _fail("empty Recovery phase replay start State disagrees with action set")
    for index, event in enumerate(events[3:], 1):
        completed_set = recovery_action_sets[index - 1]
        next_set = recovery_action_sets[index]
        validate_execution_recovery_action_set_supplied_prefix_v1(
            completed_set,
            events[: index + 1],
        )
        validate_execution_recovery_action_set_supplied_prefix_v1(
            next_set,
            events[: index + 2],
        )
        state = _reduce_empty_recovery_phase_advance_v1(
            state,
            event,
            completed_set,
            next_set,
        )
    return state


def validate_execution_recovery_action_set_v1(action_set: dict[str, Any]) -> None:
    """Validate a frozen Recovery action set without deriving or executing it."""
    validate_instance("execution-recovery-action-set-1.0.json", action_set)
    _check_nfc(action_set)
    if action_set["action_set_sigil"] != content_sigil(_without(action_set, "action_set_sigil")):
        _fail("Execution Recovery action-set self-Sigil mismatch")
    actions = action_set["actions"]
    if action_set["derived_through_sequence"] < 1:
        _fail("Execution Recovery action set requires a positive derived-through sequence")
    if [action["ordinal"] for action in actions] != list(range(len(actions))):
        _fail("Execution Recovery action ordinals must be contiguous from zero")
    if len({action["target_event_id"] for action in actions}) != len(actions):
        _fail("Execution Recovery action target Event IDs must be unique")
    logical_actions: set[bytes] = set()
    ordering_keys: list[tuple[Any, ...]] = []
    for action in actions:
        _validate_execution_recovery_action_phase_v1(action_set["phase"], action)
        if (
            action["target_sequence"]
            != action_set["derived_through_sequence"] + 2 + action["ordinal"]
        ):
            _fail("Execution Recovery action target sequence disagrees with ordinal")
        prerequisites = action["prerequisite_event_ids"]
        if prerequisites != sorted(
            prerequisites,
            key=lambda value: _unsigned_ascii(value, "Recovery prerequisite Event ID"),
        ):
            _fail("Execution Recovery prerequisite Event IDs are not unsigned-ASCII sorted")
        logical_action = _canonical_execution_recovery_logical_action_v1(action)
        if logical_action in logical_actions:
            _fail("Execution Recovery action set contains duplicate logical actions")
        logical_actions.add(logical_action)
        ordering_keys.append(_execution_recovery_action_ordering_key_v1(action, logical_action))
    if ordering_keys != sorted(ordering_keys):
        _fail("Execution Recovery actions are not in canonical order")


def _validate_execution_recovery_action_phase_v1(phase: str, action: dict[str, Any]) -> None:
    kind = action["action_kind"]
    if kind not in _RECOVERY_PHASE_KINDS[phase]:
        _fail("Execution Recovery action kind is not allowed in its phase")
    event_type = action["target_event_type"]
    if kind == "ADVANCE_ATTEMPT":
        if phase == "FENCING" and event_type != "attempt.stop_latched":
            _fail("FENCING Attempt advancement must target STOPPING")
        if phase == "RECONCILING" and event_type != "attempt.cleaning":
            _fail("RECONCILING Attempt advancement must target CLEANING")
        if phase == "FINALIZING" and event_type not in _ATTEMPT_TERMINAL_EVENT_TYPES:
            _fail("FINALIZING Attempt advancement must target an Attempt terminal state")
    if kind == "ADVANCE_JOB" and phase == "FENCING" and event_type != "job.stop_latched":
        _fail("FENCING Job advancement must target STOPPING")


def _execution_recovery_action_ordering_key_v1(
    action: dict[str, Any], logical_action: bytes
) -> tuple[Any, ...]:
    kind = action["action_kind"]
    action_kind_rank = _RECOVERY_ACTION_KIND_RANK[kind]
    if kind == "COMMIT_DUE_EVENT":
        parameters = action["parameters"]
        return (
            action_kind_rank,
            _parse_time(parameters["due_at"]),
            _DEADLINE_PRIORITY[parameters["deadline_kind"]],
            _unsigned_ascii(parameters["deadline_entity_id"], "Recovery deadline entity ID"),
            _unsigned_ascii(action["target_event_type"], "Recovery target Event type"),
        )
    return (
        action_kind_rank,
        _ENTITY_KIND_RANK[action["entity_kind"]],
        _unsigned_ascii(action["entity_id"], "Recovery entity ID"),
        _unsigned_ascii(action["target_event_type"], "Recovery target Event type"),
        logical_action,
    )


def _canonical_execution_recovery_logical_action_v1(action: dict[str, Any]) -> bytes:
    """Return RFC-0012's reservation-independent logical-action bytes."""
    logical = {
        key: deepcopy(value)
        for key, value in action.items()
        if key not in {"ordinal", "target_event_id", "target_sequence"}
    }

    def normalize_transition_causes(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("trigger_kind") == "RECOVERY_DERIVATION":
                value["trigger_event_id"] = "SELF_EVENT"
                value["effective_sequence"] = "SELF_SEQUENCE"
            for member in value.values():
                normalize_transition_causes(member)
        elif isinstance(value, list):
            for member in value:
                normalize_transition_causes(member)

    normalize_transition_causes(logical)
    return canonical_json(logical).encode("ascii")


def load_execution_recovery_action_set_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    action_set = _load_strict_object(raw, "Execution Recovery action set")
    validate_execution_recovery_action_set_v1(action_set)
    return action_set


def validate_execution_recovery_action_set_supplied_prefix_v1(
    action_set: dict[str, Any],
    events: list[dict[str, Any]],
) -> None:
    """Anchor one sealed action set to a caller-supplied verified prefix.

    The supplied sequence is checked only for its closed wire chain and the
    explicitly installed bounded reducer path.  It does not establish that the
    prefix is complete, current, durable, or authoritative for derivation.
    """
    validate_execution_recovery_action_set_v1(action_set)
    if not events:
        _fail("Execution Recovery action set requires a nonempty supplied prefix")
    validate_execution_journal_prefix_wire_v1(events)
    last = events[-1]
    if (
        action_set["derived_from_journal_id"] != last["journal_id"]
        or action_set["derived_through_sequence"] != last["sequence"]
        or action_set["derived_through_event_sigil"] != last["event_sigil"]
    ):
        _fail("Execution Recovery action set disagrees with supplied prefix")


def validate_execution_recovery_start_supplied_action_set_v1(
    event: dict[str, Any],
    action_set: dict[str, Any],
    prefix: list[dict[str, Any]],
) -> None:
    """Compare a Recovery start with its sealed STARTED set and supplied prefix.

    This is a closed-record relation only: it neither persists the action set,
    derives actions, nor grants recovery or append authority.
    """
    validate_execution_journal_event_v1(event)
    validate_execution_recovery_action_set_supplied_prefix_v1(action_set, prefix)
    last = prefix[-1]
    payload = event["payload"]
    if event["event_type"] != "recovery.started":
        _fail("Execution Recovery start binding requires a recovery.started Event")
    if (
        event["journal_id"] != last["journal_id"]
        or event["sequence"] != last["sequence"] + 1
        or event["previous_event_sigil"] != last["event_sigil"]
        or payload["recovery_id"] != action_set["recovery_id"]
        or payload["initial_action_set_sigil"] != action_set["action_set_sigil"]
        or payload["replay_through_sequence"] != action_set["derived_through_sequence"]
        or payload["replay_through_event_sigil"] != action_set["derived_through_event_sigil"]
        or action_set["phase"] != "STARTED"
        or action_set["supersedes_action_set_sigil"] is not None
    ):
        _fail("Execution Recovery start disagrees with supplied action set or prefix")


def validate_execution_recovery_phase_advance_supplied_action_sets_v1(
    state: dict[str, Any],
    event: dict[str, Any],
    completed_action_set: dict[str, Any],
    next_action_set: dict[str, Any],
) -> None:
    """Check one Recovery phase event against supplied before/after action sets.

    Completion of every action, durable action-set availability, and the next
    set's derivation prefix remain replay and storage authority concerns.  This
    helper only compares the closed State, Event, and sealed documents supplied
    by the caller.
    """
    validate_execution_state_v1(state)
    validate_execution_journal_event_v1(event)
    validate_execution_recovery_action_set_v1(completed_action_set)
    validate_execution_recovery_action_set_v1(next_action_set)
    active_recovery_id = state["executor"]["active_recovery_id"]
    if active_recovery_id is None:
        _fail("Execution Recovery phase advance requires an active Recovery")
    recovery = next(
        item for item in state["recoveries"] if item["recovery_id"] == active_recovery_id
    )
    payload = event["payload"]
    expected_next = _RECOVERY_NEXT_PHASE.get(recovery["state"])
    expected_revision = [
        {
            "entity_kind": "RECOVERY",
            "entity_id": recovery["recovery_id"],
            "preceding_revision": recovery["revision"],
            "next_revision": recovery["revision"] + 1,
        }
    ]
    if (
        event["event_type"] != "recovery.phase_advanced"
        or event["recovery_action_binding"] is not None
        or event["journal_id"] != state["journal_binding"]["journal_id"]
        or event["sequence"] != state["journal_binding"]["through_sequence"] + 1
        or event["previous_event_sigil"] != state["journal_binding"]["through_event_sigil"]
        or event["entity_revisions"] != expected_revision
        or payload["recovery_id"] != recovery["recovery_id"]
        or payload["from_phase"] != recovery["state"]
        or payload["to_phase"] != expected_next
        or payload["completed_action_set_sigil"] != recovery["current_action_set_sigil"]
        or payload["completed_action_set_sigil"] != completed_action_set["action_set_sigil"]
        or completed_action_set["recovery_id"] != recovery["recovery_id"]
        or completed_action_set["phase"] != recovery["state"]
        or payload["next_action_set_sigil"] != next_action_set["action_set_sigil"]
        or next_action_set["recovery_id"] != recovery["recovery_id"]
        or next_action_set["phase"] != payload["to_phase"]
        or next_action_set["supersedes_action_set_sigil"] is not None
    ):
        _fail("Execution Recovery phase advance disagrees with supplied State or action sets")


def validate_execution_recovery_rebase_supplied_action_sets_v1(
    state: dict[str, Any],
    event: dict[str, Any],
    prior_action_set: dict[str, Any],
    replacement_action_set: dict[str, Any],
) -> None:
    """Check one Recovery rebase against supplied State and sealed action sets.

    This verifies closed bindings only.  It does not determine whether carried
    completion events remain valid, derive replacement actions, or establish
    durable/current action-set availability.
    """
    validate_execution_state_v1(state)
    validate_execution_journal_event_v1(event)
    validate_execution_recovery_action_set_v1(prior_action_set)
    validate_execution_recovery_action_set_v1(replacement_action_set)
    active_recovery_id = state["executor"]["active_recovery_id"]
    if active_recovery_id is None:
        _fail("Execution Recovery rebase requires an active Recovery")
    recovery = next(
        item for item in state["recoveries"] if item["recovery_id"] == active_recovery_id
    )
    payload = event["payload"]
    expected_revision = [
        {
            "entity_kind": "RECOVERY",
            "entity_id": recovery["recovery_id"],
            "preceding_revision": recovery["revision"],
            "next_revision": recovery["revision"] + 1,
        }
    ]
    if (
        event["event_type"] != "recovery.action_set_rebased"
        or event["recovery_action_binding"] is not None
        or event["journal_id"] != state["journal_binding"]["journal_id"]
        or event["sequence"] != state["journal_binding"]["through_sequence"] + 1
        or event["previous_event_sigil"] != state["journal_binding"]["through_event_sigil"]
        or event["entity_revisions"] != expected_revision
        or payload["recovery_id"] != recovery["recovery_id"]
        or payload["phase"] != recovery["state"]
        or payload["prior_action_set_sigil"] != recovery["current_action_set_sigil"]
        or payload["prior_action_set_sigil"] != prior_action_set["action_set_sigil"]
        or prior_action_set["recovery_id"] != recovery["recovery_id"]
        or prior_action_set["phase"] != recovery["state"]
        or payload["replacement_action_set_sigil"] != replacement_action_set["action_set_sigil"]
        or replacement_action_set["recovery_id"] != recovery["recovery_id"]
        or replacement_action_set["phase"] != recovery["state"]
        or replacement_action_set["supersedes_action_set_sigil"]
        != prior_action_set["action_set_sigil"]
        or payload["new_epoch"] != event["executor_epoch"]
    ):
        _fail("Execution Recovery rebase disagrees with supplied State or action sets")


def validate_execution_recovery_completion_supplied_action_set_v1(
    state: dict[str, Any],
    event: dict[str, Any],
    finalizing_action_set: dict[str, Any],
) -> None:
    """Check a Recovery completion Event against supplied pre-completion facts.

    The payload's recovered State Sigil is only an asserted postcondition here;
    recomputing it requires the complete installed reducer and remains outside
    this contract-only helper.
    """
    validate_execution_state_v1(state)
    validate_execution_journal_event_v1(event)
    validate_execution_recovery_action_set_v1(finalizing_action_set)
    active_recovery_id = state["executor"]["active_recovery_id"]
    if active_recovery_id is None:
        _fail("Execution Recovery completion requires an active Recovery")
    recovery = next(
        item for item in state["recoveries"] if item["recovery_id"] == active_recovery_id
    )
    executor = state["executor"]
    payload = event["payload"]
    expected_revisions = [
        {
            "entity_kind": "EXECUTOR",
            "entity_id": executor["executor_instance_id"],
            "preceding_revision": executor["revision"],
            "next_revision": executor["revision"] + 1,
        },
        {
            "entity_kind": "RECOVERY",
            "entity_id": recovery["recovery_id"],
            "preceding_revision": recovery["revision"],
            "next_revision": recovery["revision"] + 1,
        },
    ]
    if (
        event["event_type"] != "recovery.completed"
        or event["recovery_action_binding"] is not None
        or event["journal_id"] != state["journal_binding"]["journal_id"]
        or event["sequence"] != state["journal_binding"]["through_sequence"] + 1
        or event["previous_event_sigil"] != state["journal_binding"]["through_event_sigil"]
        or event["executor_instance_id"] != executor["executor_instance_id"]
        or event["executor_epoch"] != executor["executor_epoch"]
        or event["executor_build_sigil"]
        != executor["executor_build_binding"]["executor_build_sigil"]
        or event["entity_revisions"] != expected_revisions
        or recovery["state"] != "FINALIZING"
        or payload["recovery_id"] != recovery["recovery_id"]
        or payload["completed_action_set_sigil"] != recovery["current_action_set_sigil"]
        or payload["completed_action_set_sigil"] != finalizing_action_set["action_set_sigil"]
        or finalizing_action_set["recovery_id"] != recovery["recovery_id"]
        or finalizing_action_set["phase"] != "FINALIZING"
    ):
        _fail("Execution Recovery completion disagrees with supplied State or action set")


def validate_execution_state_supplied_recovery_action_set_v1(
    state: dict[str, Any],
    action_set: dict[str, Any],
) -> None:
    """Compare an active Recovery projection with one supplied sealed action set.

    This checks an immutable binding only.  It neither establishes the supplied
    set's durable availability nor treats any action as completed or executable.
    """
    validate_execution_state_v1(state)
    validate_execution_recovery_action_set_v1(action_set)
    active_recovery_id = state["executor"]["active_recovery_id"]
    if active_recovery_id is None:
        _fail("Execution State has no active Recovery action-set binding")
    recovery = next(
        item for item in state["recoveries"] if item["recovery_id"] == active_recovery_id
    )
    if (
        action_set["recovery_id"] != recovery["recovery_id"]
        or action_set["phase"] != recovery["state"]
        or action_set["action_set_sigil"] != recovery["current_action_set_sigil"]
    ):
        _fail("Execution State Recovery projection disagrees with supplied action set")


def validate_execution_recovery_action_supplied_event_v1(
    action_set: dict[str, Any],
    event: dict[str, Any],
) -> None:
    """Compare one caller-supplied Event with its frozen Recovery action.

    Causation, idempotency, durable action-set retrieval, and the Event's
    business postcondition remain external authorities; this only checks the
    closed action-to-envelope relation RFC-0012 assigns to replay.
    """
    validate_execution_recovery_action_set_v1(action_set)
    validate_execution_journal_event_v1(event)
    binding = event["recovery_action_binding"]
    if binding is None:
        _fail("Recovery action Event lacks a Recovery action binding")
    if (
        binding["recovery_id"] != action_set["recovery_id"]
        or binding["phase"] != action_set["phase"]
        or binding["action_set_sigil"] != action_set["action_set_sigil"]
    ):
        _fail("Recovery action Event binding disagrees with supplied action set")
    ordinal = binding["action_ordinal"]
    if ordinal >= len(action_set["actions"]):
        _fail("Recovery action Event ordinal is outside supplied action set")
    action = action_set["actions"][ordinal]
    if (
        event["event_id"] != action["target_event_id"]
        or event["sequence"] != action["target_sequence"]
        or event["event_type"] != action["target_event_type"]
    ):
        _fail("Recovery action Event envelope disagrees with supplied action")
    expected_revision = {
        "entity_kind": action["entity_kind"],
        "entity_id": action["entity_id"],
        "preceding_revision": action["expected_revision"],
        "next_revision": action["expected_revision"] + 1,
    }
    if expected_revision not in event["entity_revisions"]:
        _fail("Recovery action Event revision effect disagrees with supplied action")


def derive_result_ingress_receipt_id_v1(receipt: dict[str, Any]) -> str:
    owner = receipt["owner_binding"]
    digest = (
        content_sigil(
            [
                "execution-result-ingress-receipt-id/1.0",
                owner["job_id"],
                owner["attempt_id"],
                receipt["result_sigil"],
            ]
        )
        .removeprefix("sha256:")
        .upper()
    )
    return "OIR-" + digest


def validate_execution_result_ingress_receipt_v1(receipt: dict[str, Any]) -> None:
    validate_instance("execution-result-ingress-receipt-1.0.json", receipt)
    _check_nfc(receipt)
    _validate_observation_owner_binding(receipt["owner_binding"])
    if receipt["receiver_identity"]["executor_epoch"] != receipt["owner_binding"]["executor_epoch"]:
        _fail("Result ingress receiver epoch disagrees with owner binding")
    observation = receipt["result_observation_binding"]
    if observation[
        "observation_evidence_subject_sigil"
    ] != derive_observation_evidence_subject_sigil_v1(receipt["owner_binding"], observation):
        _fail("Result ingress receipt observation subject Sigil mismatch")
    if receipt["ingress_receipt_id"] != derive_result_ingress_receipt_id_v1(receipt):
        _fail("Result ingress receipt ID mismatch")
    verification = receipt["credential_verification"]
    expected_verification = content_sigil(
        [
            "execution-result-ingress-credential-verification/1.0",
            receipt["owner_binding"],
            receipt["result_sigil"],
            receipt["received_at"],
            receipt["control_channel_identity_sigil"],
            verification["lease_credential_digest"],
            verification["verification_profile_sigil"],
            verification["verified_at"],
        ]
    )
    if verification["verification_sigil"] != expected_verification:
        _fail("Result ingress credential verification Sigil mismatch")
    if not (
        _parse_time(receipt["received_at"])
        <= _parse_time(verification["verified_at"])
        <= _parse_time(receipt["created_at"])
    ):
        _fail("Result ingress receipt time order mismatch")
    if receipt["ingress_receipt_sigil"] != content_sigil(
        _without(receipt, "ingress_receipt_sigil")
    ):
        _fail("Result ingress receipt self-Sigil mismatch")


def load_execution_result_ingress_receipt_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    receipt = _load_strict_object(raw, "Result ingress receipt")
    validate_execution_result_ingress_receipt_v1(receipt)
    return receipt


def validate_execution_result_ingress_event_intent_v1(intent: dict[str, Any]) -> None:
    """Validate a sealed O2 Event candidate without reserving or appending it."""
    validate_instance("execution-result-ingress-event-intent-1.0.json", intent)
    _check_nfc(intent)
    candidate = intent["event_candidate"]
    validate_execution_journal_event_v1(candidate)
    if candidate["event_type"] != "attempt.result_ingress_received":
        _fail("Result ingress Event intent candidate has the wrong Event type")
    if intent["intent_sigil"] != content_sigil(_without(intent, "intent_sigil")):
        _fail("Result ingress Event intent self-Sigil mismatch")


def load_execution_result_ingress_event_intent_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    intent = _load_strict_object(raw, "Result ingress Event intent")
    validate_execution_result_ingress_event_intent_v1(intent)
    return intent


def validate_execution_result_ingress_index_v1(index: dict[str, Any]) -> None:
    """Validate a sealed O2 Index row, never its canonical-path visibility."""
    validate_instance("execution-result-ingress-index-1.0.json", index)
    _check_nfc(index)
    receipt = index["result_ingress_receipt"]
    intent = index["ingress_event_intent"]
    validate_execution_result_ingress_receipt_v1(receipt)
    validate_execution_result_ingress_event_intent_v1(intent)
    receipt_binding = {
        "ingress_receipt_id": receipt["ingress_receipt_id"],
        "ingress_receipt_sigil": receipt["ingress_receipt_sigil"],
    }
    if intent["result_ingress_receipt_binding"] != receipt_binding:
        _fail("Result ingress Index intent binding disagrees with receipt")
    candidate = intent["event_candidate"]
    payload = candidate["payload"]
    expected_payload = {
        "ingress_receipt_id": receipt["ingress_receipt_id"],
        "ingress_receipt_sigil": receipt["ingress_receipt_sigil"],
        "result_sigil": receipt["result_sigil"],
        "observation_evidence_subject_sigil": receipt["result_observation_binding"][
            "observation_evidence_subject_sigil"
        ],
        "received_at": receipt["received_at"],
    }
    if payload != expected_payload:
        _fail("Result ingress Index candidate payload disagrees with receipt")
    if (
        index["attempt_id"] != receipt["owner_binding"]["attempt_id"]
        or index["result_sigil"] != receipt["result_sigil"]
        or index["event_id"] != candidate["event_id"]
        or index["idempotency_key_sigil"] != candidate["idempotency_key_sigil"]
    ):
        _fail("Result ingress Index top-level binding disagrees with Receipt or candidate")
    owner = receipt["owner_binding"]
    if (
        candidate["executor_instance_id"] != receipt["receiver_identity"]["executor_instance_id"]
        or candidate["executor_epoch"] != owner["executor_epoch"]
        or ("ATTEMPT", owner["attempt_id"])
        not in {
            (revision["entity_kind"], revision["entity_id"])
            for revision in candidate["entity_revisions"]
        }
    ):
        _fail("Result ingress candidate Event disagrees with Receipt owner")
    expected_key = content_sigil(
        [
            "execution-result-ingress-key/1.0",
            owner["attempt_id"],
            receipt["result_sigil"],
        ]
    )
    if index["idempotency_key_sigil"] != expected_key:
        _fail("Result ingress Index idempotency key disagrees with Receipt")
    status = index["status"]
    if status["kind"] == "PENDING_EVENT":
        head = status["expected_journal_head"]
        validate_execution_journal_head_v1(head)
        if (
            head["journal_id"] != candidate["journal_id"]
            or head["last_sequence"] + 1 != candidate["sequence"]
            or head["last_event_sigil"] != candidate["previous_event_sigil"]
        ):
            _fail("Result ingress pending Index Head disagrees with candidate Event")
    elif status["kind"] == "COMMITTED":
        event_ref = status["actual_event_ref"]
        if event_ref != {
            "journal_id": candidate["journal_id"],
            "event_id": candidate["event_id"],
            "sequence": candidate["sequence"],
            "event_sigil": candidate["event_sigil"],
        }:
            _fail("Result ingress committed Index Event reference disagrees with candidate")
    if index["index_sigil"] != content_sigil(_without(index, "index_sigil")):
        _fail("Result ingress Index self-Sigil mismatch")


def load_execution_result_ingress_index_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    index = _load_strict_object(raw, "Result ingress Index")
    validate_execution_result_ingress_index_v1(index)
    return index


def derive_execution_storage_root_manifest_id_v1(manifest: dict[str, Any]) -> str:
    """Derive an ESM-ID from its immutable owner tuple."""
    digest = (
        content_sigil(
            [
                "execution-storage-root-manifest-id/1.0",
                manifest["root_kind"],
                manifest["job_id"],
                manifest["attempt_id"],
                manifest["owner_binding"],
            ]
        )
        .removeprefix("sha256:")
        .upper()
    )
    return f"ESM-{digest}"


def validate_execution_storage_root_manifest_v1(manifest: dict[str, Any]) -> None:
    """Validate an ESM's local immutable closure, never Storage authority."""
    validate_instance("execution-storage-root-manifest-1.0.json", manifest)
    _check_nfc(manifest)
    if manifest["manifest_id"] != derive_execution_storage_root_manifest_id_v1(manifest):
        _fail("Execution Storage Root Manifest ID mismatch")
    if manifest["manifest_sigil"] != content_sigil(_without(manifest, "manifest_sigil")):
        _fail("Execution Storage Root Manifest self-Sigil mismatch")
    entries = manifest["entries"]
    if len({entry["storage_subject_id"] for entry in entries}) != len(entries):
        _fail("Execution Storage Root Manifest storage subject IDs must be unique")
    if manifest["root_kind"] in {"JOB_INPUT", "ATTEMPT_INPUT"}:
        ordinals = [entry["subject"]["input_ordinal"] for entry in entries]
        if ordinals != list(range(len(entries))):
            _fail("Execution Storage Root Manifest input ordinals must be contiguous")
    expected_blobs: list[dict[str, Any]] = []
    for entry in entries:
        if entry["entry_sigil"] != content_sigil(_without(entry, "entry_sigil")):
            _fail("Execution Storage Root Manifest entry self-Sigil mismatch")
        subject = entry["subject"]
        if subject["kind"] != "ATTEMPT_OUTPUT":
            expected_subject_id = content_sigil(
                [
                    "execution-storage-subject-id/1.0",
                    manifest["root_kind"],
                    manifest["job_id"],
                    manifest["attempt_id"],
                    subject,
                ]
            )
            if entry["storage_subject_id"] != expected_subject_id:
                _fail("Execution Storage Root Manifest storage subject ID mismatch")
        origin_kind = entry["storage_origin"]["kind"]
        claimed_blob = entry["claimed_blob"]
        if (origin_kind == "NOT_STORED") != (claimed_blob is None):
            _fail("Execution Storage Root Manifest claimed Blob disagrees with origin")
        subject_blob = _execution_storage_subject_blob_ref_v1(subject)
        if (
            subject_blob is not None
            and origin_kind in {"COMMITTED_BLOB", "QUARANTINE"}
            and subject_blob != claimed_blob
        ):
            _fail("Execution Storage Root Manifest claimed Blob disagrees with subject")
        if origin_kind == "COMMITTED_BLOB":
            expected_blobs.append(claimed_blob)
    expected_blobs.sort(key=lambda blob: (blob["blob_sigil"], blob["size_bytes"]))
    if manifest["blob_refs"] != expected_blobs:
        _fail("Execution Storage Root Manifest Blob refs disagree with committed entries")
    if (manifest["protection_plan"]["kind"] == "NONE") != (not expected_blobs):
        _fail("Execution Storage Root Manifest protection plan disagrees with Blob refs")


def _execution_storage_subject_blob_ref_v1(subject: dict[str, Any]) -> dict[str, Any] | None:
    kind = subject["kind"]
    if kind in {"ATTEMPT_OUTPUT", "LOG_STREAM", "RESOURCE_EVIDENCE"}:
        return {"blob_sigil": subject["blob_sigil"], "size_bytes": subject["byte_size"]}
    if kind == "TERMINAL_SOURCE":
        return subject["storage_blob"]
    return None


def load_execution_storage_root_manifest_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    manifest = _load_strict_object(raw, "Execution Storage Root Manifest")
    validate_execution_storage_root_manifest_v1(manifest)
    return manifest


def derive_execution_root_hold_release_authorization_id_v1(
    authorization: dict[str, Any],
) -> str:
    """Derive the immutable EHR-ID from the held execution root."""
    digest = (
        content_sigil(
            [
                "execution-root-hold-release-authorization-id/1.0",
                authorization["storage_root"]["hold_id"],
            ]
        )
        .removeprefix("sha256:")
        .upper()
    )
    return f"EHR-{digest}"


def validate_execution_root_hold_release_authorization_v1(
    authorization: dict[str, Any],
) -> None:
    """Validate an EHR's local bindings without authorizing a Storage release."""
    validate_instance("execution-root-hold-release-authorization-1.0.json", authorization)
    _check_nfc(authorization)
    if authorization[
        "release_authorization_id"
    ] != derive_execution_root_hold_release_authorization_id_v1(authorization):
        _fail("Execution Root Hold Release Authorization ID mismatch")
    if authorization["release_authorization_sigil"] != content_sigil(
        _without(authorization, "release_authorization_sigil")
    ):
        _fail("Execution Root Hold Release Authorization self-Sigil mismatch")
    basis = authorization["basis"]
    if basis["kind"] == "OWNER_TERMINAL":
        validate_execution_journal_head_v1(basis["verification_head"])
        if basis["activation_event_sequence"] >= basis["terminal_event_sequence"]:
            _fail("Execution Root Hold Release owner-terminal event order is invalid")
        if basis["verification_head"]["last_sequence"] < basis["terminal_event_sequence"]:
            _fail("Execution Root Hold Release verification Head predates terminal Event")
    elif basis["kind"] == "OUTPUT_DEADLINE":
        validate_execution_journal_head_v1(basis["verification_head"])
        if basis["activation_event_sequence"] >= basis["terminal_event_sequence"]:
            _fail("Execution Root Hold Release output-deadline event order is invalid")
        if basis["verification_head"]["last_sequence"] < basis["terminal_event_sequence"]:
            _fail("Execution Root Hold Release verification Head predates terminal Event")
    else:
        validate_execution_journal_head_v1(basis["absence_head"])


def load_execution_root_hold_release_authorization_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    authorization = _load_strict_object(raw, "Execution Root Hold Release Authorization")
    validate_execution_root_hold_release_authorization_v1(authorization)
    return authorization


def derive_execution_control_evidence_set_id_v1(evidence_set: dict[str, Any]) -> str:
    """Derive the immutable CES-ID from its Attempt owner binding."""
    digest = (
        content_sigil(
            [
                "execution-control-evidence-set-id/1.0",
                evidence_set["job_id"],
                evidence_set["attempt_id"],
                evidence_set["attempt_binding_sigil"],
            ]
        )
        .removeprefix("sha256:")
        .upper()
    )
    return f"CES-{digest}"


def validate_execution_control_evidence_set_v1(evidence_set: dict[str, Any]) -> None:
    """Validate a frozen CES locally without resolving its evidence records."""
    validate_instance("execution-control-evidence-set-1.0.json", evidence_set)
    _check_nfc(evidence_set)
    if evidence_set["control_evidence_set_id"] != derive_execution_control_evidence_set_id_v1(
        evidence_set
    ):
        _fail("Execution Control Evidence Set ID mismatch")
    if evidence_set["control_evidence_set_sigil"] != content_sigil(
        _without(evidence_set, "control_evidence_set_sigil")
    ):
        _fail("Execution Control Evidence Set self-Sigil mismatch")
    refs = evidence_set["control_evidence_refs"]
    if [reference["control_dimension"] for reference in refs] != list(_CONTROL_DIMENSION_ORDER):
        _fail("Execution Control Evidence Set dimensions are not in matrix order")
    ids = [reference["control_evidence_id"] for reference in refs]
    if len(set(ids)) != len(ids):
        _fail("Execution Control Evidence Set evidence IDs must be unique")


def load_execution_control_evidence_set_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    evidence_set = _load_strict_object(raw, "Execution Control Evidence Set")
    validate_execution_control_evidence_set_v1(evidence_set)
    return evidence_set


def derive_execution_quarantine_binding_set_id_v1(binding_set: dict[str, Any]) -> str:
    """Derive the immutable QBS-ID from frozen Attempt and storage inputs."""
    digest = (
        content_sigil(
            [
                "execution-quarantine-binding-set-id/1.0",
                binding_set["job_id"],
                binding_set["attempt_id"],
                binding_set["attempt_binding_sigil"],
                binding_set["quarantine_plan_sigil"],
                binding_set["terminalization_storage_manifest_binding"],
            ]
        )
        .removeprefix("sha256:")
        .upper()
    )
    return f"QBS-{digest}"


def validate_execution_quarantine_binding_set_v1(binding_set: dict[str, Any]) -> None:
    """Validate a frozen QBS locally without resolving the Storage projection."""
    validate_instance("execution-quarantine-binding-set-1.0.json", binding_set)
    _check_nfc(binding_set)
    if binding_set["quarantine_binding_set_id"] != derive_execution_quarantine_binding_set_id_v1(
        binding_set
    ):
        _fail("Execution Quarantine Binding Set ID mismatch")
    if binding_set["quarantine_binding_set_sigil"] != content_sigil(
        _without(binding_set, "quarantine_binding_set_sigil")
    ):
        _fail("Execution Quarantine Binding Set self-Sigil mismatch")
    bindings = binding_set["bindings"]
    if len({binding["storage_subject_id"] for binding in bindings}) != len(bindings):
        _fail("Execution Quarantine Binding Set storage subject IDs must be unique")
    if len({binding["quarantine_ref"]["quarantine_id"] for binding in bindings}) != len(bindings):
        _fail("Execution Quarantine Binding Set Quarantine IDs must be unique")
    for binding in bindings:
        if binding["quarantine_binding_sigil"] != content_sigil(
            _without(binding, "quarantine_binding_sigil")
        ):
            _fail("Execution Quarantine Binding Set binding self-Sigil mismatch")
        origin = binding["storage_origin"]
        quarantine = binding["quarantine_ref"]
        if (
            origin["quarantine_id"] != quarantine["quarantine_id"]
            or origin["transfer"]["transfer_attempt_id"] != quarantine["owner_id"]
        ):
            _fail("Execution Quarantine Binding Set origin disagrees with Quarantine owner")
        if quarantine["origin_event"] != origin["quarantine_origin_event"]:
            _fail("Execution Quarantine Binding Set origin Event disagrees with storage origin")
        if quarantine["observation_event"]["sequence"] < quarantine["origin_event"]["sequence"]:
            _fail("Execution Quarantine Binding Set observation predates origin Event")


def load_execution_quarantine_binding_set_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    binding_set = _load_strict_object(raw, "Execution Quarantine Binding Set")
    validate_execution_quarantine_binding_set_v1(binding_set)
    return binding_set


def validate_execution_terminalization_supplied_records_v1(
    *,
    job_id: str,
    attempt_id: str,
    attempt_binding_sigil: str,
    terminalization_storage_manifest_binding: dict[str, Any],
    control_evidence_set_binding: dict[str, Any],
    quarantine_binding_set_binding: dict[str, Any],
    output_root_protection: dict[str, Any],
    manifest: dict[str, Any],
    control_evidence_set: dict[str, Any],
    quarantine_binding_set: dict[str, Any],
) -> None:
    """Compare terminalization's complete caller-supplied immutable records.

    This is intentionally not a Storage resolver or replay authority.  It
    checks only the exact records the caller already supplied.
    """
    validate_execution_storage_root_manifest_v1(manifest)
    validate_execution_control_evidence_set_v1(control_evidence_set)
    validate_execution_quarantine_binding_set_v1(quarantine_binding_set)
    expected_manifest = {
        "kind": "FROZEN", "storage_root_manifest_id": manifest["manifest_id"],
        "storage_root_manifest_sigil": manifest["manifest_sigil"],
    }
    expected_ces = {
        "kind": "FROZEN", "control_evidence_set_id": control_evidence_set["control_evidence_set_id"],
        "control_evidence_set_sigil": control_evidence_set["control_evidence_set_sigil"],
    }
    expected_qbs = {
        "kind": "FROZEN", "quarantine_binding_set_id": quarantine_binding_set["quarantine_binding_set_id"],
        "quarantine_binding_set_sigil": quarantine_binding_set["quarantine_binding_set_sigil"],
    }
    if (
        terminalization_storage_manifest_binding != expected_manifest
        or control_evidence_set_binding != expected_ces
        or quarantine_binding_set_binding != expected_qbs
        or manifest["root_kind"] != "ATTEMPT_OUTPUT" or manifest["job_id"] != job_id
        or manifest["attempt_id"] != attempt_id
        or manifest["owner_binding"]["attempt_binding_sigil"] != attempt_binding_sigil
        or manifest["owner_binding"]["control_evidence_set_binding"] != expected_ces
        or control_evidence_set["job_id"] != job_id or control_evidence_set["attempt_id"] != attempt_id
        or control_evidence_set["attempt_binding_sigil"] != attempt_binding_sigil
        or quarantine_binding_set["job_id"] != job_id or quarantine_binding_set["attempt_id"] != attempt_id
        or quarantine_binding_set["attempt_binding_sigil"] != attempt_binding_sigil
        or quarantine_binding_set["terminalization_storage_manifest_binding"] != expected_manifest
        or output_root_protection.get("kind") not in {"NO_HOLD", "HELD"}
        or output_root_protection["terminalization_storage_manifest_binding"] != expected_manifest
    ):
        _fail("Terminalization supplied records disagree with frozen Attempt bindings")
    if output_root_protection["kind"] == "NO_HOLD" and manifest["blob_refs"]:
        _fail("Terminalization NO_HOLD protection requires an empty output Manifest")


def derive_execution_output_storage_observation_set_id_v1(
    observation_set: dict[str, Any],
) -> str:
    """Derive the immutable OS-ID from its terminal Attempt inputs."""
    digest = (
        content_sigil(
            [
                "execution-output-storage-observation-set-id/1.0",
                observation_set["job_id"],
                observation_set["attempt_id"],
                observation_set["attempt_binding_sigil"],
                observation_set["result_binding"],
                observation_set["log_closure_sigil"],
                observation_set["output_closure_sigil"],
                observation_set["control_evidence_set_binding"],
                observation_set["quarantine_binding_set_binding"],
                observation_set["terminalization_storage_manifest_binding"],
                observation_set["output_root_protection"],
                observation_set["terminal_source_binding"],
            ]
        )
        .removeprefix("sha256:")
        .upper()
    )
    return f"OS-{digest}"


def _observation_member_blob_refs_v1(member: dict[str, Any]) -> list[str]:
    kind = member["kind"]
    if kind in {"ATTEMPT_OUTPUT", "RESOURCE_EVIDENCE"}:
        return [member["blob_sigil"]]
    if kind == "LOG_STREAM":
        return [member["content"]["blob_sigil"]]
    if kind == "TERMINAL_SOURCE":
        return [member["storage_blob"]["blob_sigil"]]
    return []


def _validate_observation_storage_v1(
    storage: dict[str, Any],
    blob_sigil: str,
    size_bytes: int,
    storage_event: dict[str, Any],
) -> None:
    kind = storage["kind"]
    if kind == "NONE":
        _fail("Output Storage Observation member with a claimed Blob cannot use NONE storage")
    if kind == "BLOB":
        if storage["blob_sigil"] != blob_sigil or storage["size_bytes"] != size_bytes:
            _fail("Output Storage Observation BLOB storage disagrees with member Blob")
        if storage["terminal_storage_status"] != storage["availability"]:
            _fail("Output Storage Observation BLOB terminal status disagrees with availability")
        integrity = storage["integrity_event_sigils"]
        if integrity != sorted(
            integrity, key=lambda value: _unsigned_ascii(value, "integrity Event Sigil")
        ):
            _fail("Output Storage Observation integrity Event Sigils are not unsigned-ASCII sorted")
        available_at = storage["availability_as_of"]
        if (
            available_at["journal_id"] != storage_event["journal_id"]
            or available_at["sequence"] > storage_event["sequence"]
        ):
            _fail("Output Storage Observation availability is outside the frozen Storage prefix")
        return
    if storage["claimed_blob_sigil"] != blob_sigil or storage["claimed_size_bytes"] != size_bytes:
        _fail("Output Storage Observation Quarantine storage disagrees with member Blob")
    if kind == "QUARANTINE_TERMINAL_NEGATIVE":
        if storage["origin_event"]["sequence"] > storage["observation_event"]["sequence"]:
            _fail("Output Storage Observation Quarantine observation predates its origin")
        observed = storage["observation_event"]
    else:
        observed = storage["quarantine_event"]
    if (
        observed["journal_id"] != storage_event["journal_id"]
        or observed["sequence"] > storage_event["sequence"]
    ):
        _fail("Output Storage Observation Quarantine is outside the frozen Storage prefix")


def validate_execution_output_storage_observation_set_v1(
    observation_set: dict[str, Any],
) -> None:
    """Validate an OS document locally, never resolving Storage or Execution history."""
    validate_instance("execution-output-storage-observation-set-1.0.json", observation_set)
    _check_nfc(observation_set)
    if observation_set[
        "observation_set_id"
    ] != derive_execution_output_storage_observation_set_id_v1(observation_set):
        _fail("Execution Output Storage Observation Set ID mismatch")
    if observation_set["observation_set_sigil"] != content_sigil(
        _without(observation_set, "observation_set_sigil")
    ):
        _fail("Execution Output Storage Observation Set self-Sigil mismatch")
    protection = observation_set["output_root_protection"]
    if protection["kind"] not in {"NO_HOLD", "HELD"}:
        _fail("Output Storage Observation requires a terminal output-root protection branch")
    if (
        protection["terminalization_storage_manifest_binding"]
        != observation_set["terminalization_storage_manifest_binding"]
    ):
        _fail("Output Storage Observation protection disagrees with terminalization manifest")

    members = observation_set["members"]
    cursor = 0
    result_kind = observation_set["result_binding"]["kind"]
    if members[cursor]["kind"] == "ATTEMPT_OUTPUTS_NONE":
        expected_reason = {
            "NONE": "NO_RESULT",
            "REJECTED": "RESULT_REJECTED",
        }.get(result_kind, "OUTPUT_ARRAY_EMPTY")
        if members[cursor]["reason"] != expected_reason:
            _fail("Output Storage Observation output sentinel disagrees with Result binding")
        cursor += 1
    else:
        start = cursor
        while cursor < len(members) and members[cursor]["kind"] == "ATTEMPT_OUTPUT":
            cursor += 1
        outputs = members[start:cursor]
        if not outputs or result_kind != "ACCEPTED":
            _fail("Output Storage Observation output members require an accepted Result")
        output_keys = [
            (_unsigned_ascii(member["logical_name"], "output logical name"), member["blob_sigil"])
            for member in outputs
        ]
        if output_keys != sorted(output_keys) or len(set(output_keys)) != len(output_keys):
            _fail("Output Storage Observation output members are not uniquely sorted")

    logs = members[cursor : cursor + 3]
    if len(logs) != 3 or [member["kind"] for member in logs] != ["LOG_STREAM"] * 3:
        _fail("Output Storage Observation must contain exactly three Log streams")
    if [member["stream"] for member in logs] != ["STDOUT", "STDERR", "STRUCTURED"]:
        _fail("Output Storage Observation Log streams are not in fixed order")
    if len({member["log_stream_id"] for member in logs}) != 3:
        _fail("Output Storage Observation Log stream IDs must be unique")
    for log in logs:
        content = log["content"]
        if content["kind"] == "EMPTY":
            if log["final_sequence"] is not None or log["captured_bytes"] != 0:
                _fail("Output Storage Observation empty Log has non-empty closure")
        elif log["final_sequence"] is None or log["captured_bytes"] == 0:
            _fail("Output Storage Observation captured Log lacks a non-empty closure")
    cursor += 3

    if cursor >= len(members):
        _fail("Output Storage Observation omits its resource-evidence group")
    if members[cursor]["kind"] == "RESOURCE_EVIDENCE_NONE":
        cursor += 1
    else:
        start = cursor
        while cursor < len(members) and members[cursor]["kind"] == "RESOURCE_EVIDENCE":
            cursor += 1
        resources = members[start:cursor]
        if not resources:
            _fail("Output Storage Observation resource-evidence group is invalid")
        keys = [
            (
                _unsigned_ascii(member["control_evidence_id"], "control evidence ID"),
                _CONTROL_PHASE_RANK[member["phase"]],
                _CONTROL_EVIDENCE_KIND_RANK[member["evidence_kind"]],
                member["phase_evidence_entry_sigil"],
            )
            for member in resources
        ]
        if keys != sorted(keys) or len(set(keys)) != len(keys):
            _fail("Output Storage Observation resource evidence is not uniquely sorted")

    terminal_members = members[cursor:]
    if len(terminal_members) != 1:
        _fail("Output Storage Observation must end with one terminal-source member")
    terminal = terminal_members[0]
    terminal_binding = observation_set["terminal_source_binding"]
    if terminal["kind"] == "TERMINAL_SOURCE_NOT_APPLICABLE":
        if terminal_binding["kind"] != "NOT_APPLICABLE":
            _fail("Output Storage Observation terminal-source sentinel disagrees with binding")
    elif terminal["kind"] == "TERMINAL_SOURCE_NONE":
        if (
            terminal_binding["kind"] != "QUARANTINED"
            or any(
                terminal_binding[field] is not None
                for field in (
                    "terminal_source_identity",
                    "terminal_source_sigil",
                    "storage_blob",
                )
            )
            or terminal_binding["file_count"] != 0
            or terminal_binding["byte_count"] != 0
            or terminal["reason_codes"] != terminal_binding["reason_codes"]
        ):
            _fail("Output Storage Observation terminal-source NONE disagrees with binding")
    else:
        if terminal_binding["kind"] not in {"VERIFIED", "QUARANTINED"}:
            _fail("Output Storage Observation terminal source lacks a compatible binding")
        copied = (
            "terminal_source_identity",
            "terminal_source_sigil",
            "storage_blob",
            "retention_policy_sigil",
            "file_count",
            "byte_count",
        )
        if any(terminal[field] != terminal_binding[field] for field in copied):
            _fail("Output Storage Observation terminal source disagrees with binding")
        if terminal["disposition"] != terminal_binding["kind"]:
            _fail("Output Storage Observation terminal source disposition disagrees with binding")
        if terminal_binding["kind"] == "VERIFIED" and terminal["storage"]["kind"] != "BLOB":
            _fail("Output Storage Observation verified terminal source requires BLOB storage")

    for member in members:
        kind = member["kind"]
        if kind in {"ATTEMPT_OUTPUT", "RESOURCE_EVIDENCE"}:
            _validate_observation_storage_v1(
                member["storage"],
                member["blob_sigil"],
                member["byte_size"],
                observation_set["storage_event"],
            )
        elif kind == "LOG_STREAM":
            _validate_observation_storage_v1(
                member["content"]["storage"],
                member["content"]["blob_sigil"],
                member["captured_bytes"],
                observation_set["storage_event"],
            )
        elif kind == "TERMINAL_SOURCE":
            _validate_observation_storage_v1(
                member["storage"],
                member["storage_blob"]["blob_sigil"],
                member["storage_blob"]["size_bytes"],
                observation_set["storage_event"],
            )

    expected_blob_sigils = sorted(
        {
            blob_sigil
            for member in members
            for blob_sigil in _observation_member_blob_refs_v1(member)
        },
        key=lambda value: _unsigned_ascii(value, "Blob Sigil"),
    )
    if observation_set["blob_sigils"] != expected_blob_sigils:
        _fail("Output Storage Observation Blob Sigils disagree with members")


def load_execution_output_storage_observation_set_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    observation_set = _load_strict_object(raw, "Execution Output Storage Observation Set")
    validate_execution_output_storage_observation_set_v1(observation_set)
    return observation_set


def derive_observation_evidence_subject_sigil_v1(
    owner_binding: dict[str, Any], result_observation_binding: dict[str, Any]
) -> str:
    return content_sigil(
        [
            "execution-result-observation-subject/1.0",
            owner_binding,
            result_observation_binding["runtime_observation"],
            result_observation_binding["termination_observation"],
        ]
    )


def derive_observation_evidence_id_v1(evidence: dict[str, Any]) -> str:
    digest = (
        content_sigil(
            [
                "execution-observation-evidence-id/1.0",
                evidence["job_id"],
                evidence["attempt_id"],
                evidence["result_ingress_receipt_binding"]["ingress_receipt_id"],
                evidence["result_observation_binding"]["observation_evidence_subject_sigil"],
            ]
        )
        .removeprefix("sha256:")
        .upper()
    )
    return "OVE-" + digest


def _observation_owner(evidence: dict[str, Any]) -> dict[str, Any]:
    members = (
        "job_id",
        "job_binding_sigil",
        "attempt_id",
        "attempt_binding_sigil",
        "lease_id",
        "lease_binding_sigil",
        "worker_id",
        "worker_binding_sigil",
        "worker_session_id",
        "worker_session_binding_sigil",
        "executor_epoch",
        "fence_tuple",
    )
    return {member: evidence[member] for member in members}


def _validate_observation_owner_binding(owner: dict[str, Any]) -> None:
    """Check local equality inside an O1/O2 owner binding.

    This is deliberately a closed-record check only: it does not resolve any
    Job, Attempt, Lease, Worker, or Journal record.
    """
    fence = owner["fence_tuple"]
    for member in ("job_id", "attempt_id", "lease_id", "executor_epoch"):
        if fence[member] != owner[member]:
            _fail(f"Observation owner binding disagrees with fence_tuple: {member}")


def validate_execution_observation_evidence_v1(evidence: dict[str, Any]) -> None:
    validate_instance("execution-observation-evidence-1.0.json", evidence)
    _check_nfc(evidence)
    owner = _observation_owner(evidence)
    _validate_observation_owner_binding(owner)
    binding = evidence["result_observation_binding"]
    if binding[
        "observation_evidence_subject_sigil"
    ] != derive_observation_evidence_subject_sigil_v1(owner, binding):
        _fail("Observation Evidence subject Sigil mismatch")
    if evidence["observation_evidence_id"] != derive_observation_evidence_id_v1(evidence):
        _fail("Observation Evidence ID mismatch")
    runtime = binding["runtime_observation"]
    termination = binding["termination_observation"]
    if not (
        _parse_time(runtime["started_at"])
        <= _parse_time(runtime["ended_at"])
        <= _parse_time(termination["observed_at"])
        <= _parse_time(evidence["created_at"])
    ):
        _fail("Observation Evidence time order mismatch")
    assessment = evidence["assessment"]
    if assessment["kind"] == "MATCHED":
        if assessment["reason_bindings"]:
            _fail("MATCHED Observation Evidence must have no reasons")
        if (
            assessment["verified_runtime_observation"] != runtime
            or assessment["verified_termination_observation"] != termination
        ):
            _fail("MATCHED Observation Evidence must copy the Result observation")
        if (
            assessment["verified_source_binding"]["source_kind"]
            != termination["observation_source"]
        ):
            _fail("MATCHED Observation Evidence source does not match termination observation")
    if assessment["kind"] == "MISMATCHED" and any(
        reason["reason_code"] != "MISMATCH" for reason in assessment["reason_bindings"]
    ):
        _fail("MISMATCHED Observation Evidence contains a non-MISMATCH reason")
    if evidence["observation_evidence_sigil"] != content_sigil(
        _without(evidence, "observation_evidence_sigil")
    ):
        _fail("Observation Evidence self-Sigil mismatch")


def load_execution_observation_evidence_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    evidence = _load_strict_object(raw, "Observation Evidence")
    validate_execution_observation_evidence_v1(evidence)
    return evidence


def validate_execution_observation_evidence_supplied_receipt_v1(
    evidence: dict[str, Any], receipt: dict[str, Any]
) -> None:
    """Compare an O1 record with one complete caller-supplied O2 receipt.

    It intentionally grants no acceptance, append, replay, or resolver
    authority; callers must independently establish that the supplied receipt
    is the applicable durable record.
    """
    validate_execution_observation_evidence_v1(evidence)
    validate_execution_result_ingress_receipt_v1(receipt)
    binding = evidence["result_ingress_receipt_binding"]
    expected_binding = {
        "ingress_receipt_id": receipt["ingress_receipt_id"],
        "ingress_receipt_sigil": receipt["ingress_receipt_sigil"],
    }
    if binding != expected_binding:
        _fail("Observation Evidence ingress receipt binding disagrees with supplied receipt")
    if _observation_owner(evidence) != receipt["owner_binding"]:
        _fail("Observation Evidence owner binding disagrees with supplied receipt")
    if evidence["result_observation_binding"] != receipt["result_observation_binding"]:
        _fail("Observation Evidence result observation disagrees with supplied receipt")


def _context_value(context: dict[str, Any], key: str) -> Any:
    value = context.get(key, _MISSING)
    if value is _MISSING:
        _fail(f"Journal Event semantic dependency is unresolved: {key}")
    return value


def expected_event_causation_v1(event: dict[str, Any], context: dict[str, Any]) -> str | None:
    """Evaluate JEW2 in priority order from explicit authenticated dependencies."""
    event_type = event["event_type"]
    payload = event["payload"]
    candidates: list[str | None] = []
    if event_type == "attempt.output_staging_preallocated":
        candidates.append(_context_value(context, "attempt_running_event_id"))
    if event_type == "attempt.result_ingress_received":
        candidates.append(_context_value(context, "attempt_running_event_id"))
    if event_type == "attempt.result_accepted" or (
        event_type == "attempt.result_rejected"
        and payload.get("disposition_kind") == "FIRST_DISPOSITION_REJECTION"
    ):
        candidates.append(_context_value(context, "result_ingress_event_id"))
    if (
        event_type == "attempt.result_rejected"
        and payload.get("disposition_kind") == "LATE_OR_CONFLICTING_REJECTION"
    ):
        candidates.append(_context_value(context, "pre_event_attempt_last_event_id"))
    if context.get("heartbeat_collision_dependent", False):
        candidates.append(_context_value(context, "heartbeat_collision_event_id"))
    if context.get("ordinary_l12_suffix", False):
        candidates.append(
            None
            if context.get("ordinary_l12_anchor", False)
            else _context_value(context, "l12_preceding_event_id")
        )
    if context.get("missing_intent_recovery", False) or event_type in {
        "log.closure_recovery_closed",
        "log.intake_recovery_terminalized",
    }:
        candidates.append(_context_value(context, "recovery_opening_event_id"))
    elif event["recovery_action_binding"] is not None:
        candidates.append(_context_value(context, "recovery_opening_event_id"))
    cause = payload.get("transition_cause")
    if isinstance(cause, dict):
        if cause["trigger_kind"] == "PRIOR_EVENT":
            candidates.append(cause["trigger_event_id"])
        elif event["recovery_action_binding"] is None:
            if (
                cause["trigger_event_id"] != event["event_id"]
                or cause["effective_sequence"] != event["sequence"]
            ):
                _fail("non-prior transition cause does not bind the enclosing Event")
            candidates.append(None)
    if len({candidate for candidate in candidates}) > 1:
        _fail("contradictory JEW2 causation rules")
    return candidates[0] if candidates else None


def expected_event_idempotency_v1(event: dict[str, Any], context: dict[str, Any]) -> str | None:
    """Evaluate JEW3 from locally derivable fields and explicit durable resolvers."""
    event_type = event["event_type"]
    payload = event["payload"]
    if event_type == "execution.heartbeat_collision_authority_closed" or context.get(
        "heartbeat_collision_dependent", False
    ):
        return _context_value(context, "candidate_inventory_bytes_sigil")
    if event_type == "attempt.output_staging_preallocated":
        return content_sigil(
            [
                "execution-output-staging-preallocation-key/1.0",
                payload["job_id"],
                payload["attempt_id"],
                payload["output_handle_id"],
            ]
        )
    attempt_id = context.get("attempt_id")
    if event_type == "attempt.result_ingress_received":
        return content_sigil(
            [
                "execution-result-ingress-key/1.0",
                _context_value(context, "attempt_id"),
                payload["result_sigil"],
            ]
        )
    if event_type == "attempt.result_accepted" or (
        event_type == "attempt.result_rejected"
        and payload.get("disposition_kind") == "FIRST_DISPOSITION_REJECTION"
    ):
        result_sigil = payload.get("result_sigil", payload.get("claimed_result_sigil"))
        return content_sigil(
            [
                "execution-result-disposition-key/1.0",
                _context_value(context, "attempt_id"),
                result_sigil,
            ]
        )
    if (
        event_type == "attempt.result_rejected"
        and payload.get("disposition_kind") == "LATE_OR_CONFLICTING_REJECTION"
    ):
        return content_sigil(
            [
                "execution-result-rejection-message-key/1.0",
                _context_value(context, "attempt_id"),
                payload["message_sigil"],
            ]
        )
    del attempt_id
    if context.get("ordinary_l12_suffix", False):
        return (
            _context_value(context, "l12_idempotency_key_sigil")
            if context.get("ordinary_l12_anchor", False)
            else None
        )
    if context.get("missing_intent_recovery", False) and event_type in {
        "log.chunk_rejected",
        "log.eof_rejected",
    }:
        return _context_value(context, "original_idempotency_key_sigil")
    if event_type == "log.intake_recovery_terminalized":
        return (
            None
            if context.get("original_anchor_survived", False)
            else _context_value(context, "original_idempotency_key_sigil")
        )
    if event_type in {"log.closed", "log.closure_recovery_closed"}:
        return None
    if event_type in {"log.eof_accepted", "log.eof_rejected"}:
        return _context_value(context, "close_log_stream_idempotency_key_sigil")
    if context.get("state_disposition_event", False):
        return _context_value(context, "state_idempotency_key_sigil")
    return None


_ATTEMPT_TERMINAL_EVENT_STATES_V1 = {
    "attempt.succeeded": "SUCCEEDED", "attempt.failed": "FAILED", "attempt.cancelled": "CANCELLED",
    "attempt.timed_out": "TIMED_OUT", "attempt.policy_violated": "POLICY_VIOLATION",
    "attempt.lease_expired": "LEASE_EXPIRED", "attempt.lost": "LOST", "attempt.fenced": "FENCED",
    "attempt.rejected": "REJECTED",
}


def _validate_attempt_terminal_evidence_v1(event: dict[str, Any]) -> None:
    """Check terminal payload self-consistency before any replay authority."""
    state = _ATTEMPT_TERMINAL_EVENT_STATES_V1.get(event["event_type"])
    if state is None:
        return
    payload = event["payload"]
    evidence = payload["attempt_terminal_evidence"]
    frozen = evidence["storage_observation_binding"]
    manifest = evidence["terminalization_storage_manifest_binding"]
    protection = evidence["output_root_protection"]
    if (
        evidence["control_evidence_set_binding"].get("kind") != "FROZEN"
        or evidence["quarantine_binding_set_binding"].get("kind") != "FROZEN"
        or manifest.get("kind") != "FROZEN" or frozen.get("kind") != "FROZEN"
        or evidence["accounting_capture_event_id"] == event["event_id"]
        or evidence["accounting_capture_event_sigil"] == event["event_sigil"]
        or payload["fencing_generation"] < 0
        or payload["final_fence_floor"] < payload["fencing_generation"]
        or evidence["output_root_protection"] .get("kind") not in {"NO_HOLD", "HELD"}
        or protection["terminalization_storage_manifest_binding"] != manifest
    ):
        _fail("Attempt terminal Event has invalid frozen finalization evidence")
    roots = payload["output_storage_roots"]
    if protection["kind"] == "NO_HOLD":
        if roots:
            _fail("Attempt terminal Event NO_HOLD must not activate output roots")
    elif roots != [protection["storage_root_binding"]]:
        _fail("Attempt terminal Event HELD root disagrees with protection")
    cause = evidence["transition_cause"]
    if state == "SUCCEEDED":
        anchor = evidence["completion_anchor_binding"]
        if (
            cause["code"] != "COMPLETION_ESTABLISHED" or cause["trigger_kind"] != "PRIOR_EVENT"
            or anchor.get("kind") not in {"RESULT_ACCEPTED", "NO_RESULT"}
            or cause["trigger_event_id"] != anchor["event_id"]
            or cause["effective_sequence"] != anchor["sequence"]
        ):
            _fail("Succeeded Attempt terminal cause must bind its completion anchor")
    elif cause["code"] == "COMPLETION_ESTABLISHED":
        _fail("Only succeeded Attempt terminal events may establish completion")


def validate_execution_journal_event_v1(
    event: dict[str, Any], *, context: dict[str, Any] | None = None
) -> None:
    """Validate a closed Event and, when supplied, the JEW2/JEW3 dependency matrix."""
    validate_instance("execution-journal-event-1.0.json", event)
    _check_nfc(event)
    revisions = [
        (
            _ENTITY_KIND_RANK[item["entity_kind"]],
            _unsigned_ascii(item["entity_id"], "entity revision ID"),
        )
        for item in event["entity_revisions"]
    ]
    if revisions != sorted(revisions) or len(revisions) != len(set(revisions)):
        _fail("entity_revisions are not strictly sorted and unique")
    for revision in event["entity_revisions"]:
        preceding = revision["preceding_revision"]
        following = revision["next_revision"]
        if preceding is None:
            if following != 0:
                _fail("created entity revision must be null then zero")
        elif following not in (preceding, preceding + 1):
            _fail("entity revision must be unchanged or advance by exactly one")
    if event["sequence"] == 1:
        if event["previous_event_sigil"] is not None:
            _fail("sequence-one Event must have null previous_event_sigil")
    elif event["previous_event_sigil"] is None:
        _fail("noninitial Event must bind previous_event_sigil")
    if event["causation_event_id"] == event["event_id"]:
        _fail("Event self-causation is forbidden")
    _validate_attempt_terminal_evidence_v1(event)
    if context is not None:
        if event["causation_event_id"] != expected_event_causation_v1(event, context):
            _fail("Journal Event causation_event_id violates JEW2")
        if event["idempotency_key_sigil"] != expected_event_idempotency_v1(event, context):
            _fail("Journal Event idempotency_key_sigil violates JEW3")
    if event["event_sigil"] != content_sigil(_without(event, "event_sigil")):
        _fail("Execution Journal Event self-Sigil mismatch")


def load_execution_journal_event_v1(
    raw: str | bytes | bytearray, *, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    event = _load_strict_object(raw, "Execution Journal Event")
    validate_execution_journal_event_v1(event, context=context)
    return event


def build_execution_journal_event_v1(
    unsigned_event: dict[str, Any], *, context: dict[str, Any] | None = None
) -> dict[str, Any]:
    if "event_sigil" in unsigned_event:
        _fail("unsigned Execution Journal Event must not contain event_sigil")
    event = {**unsigned_event, "event_sigil": content_sigil(unsigned_event)}
    validate_execution_journal_event_v1(event, context=context)
    return event
