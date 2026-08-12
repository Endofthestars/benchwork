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
    "executor.epoch_started", "executor.clock_uncertain", "executor.clock_restored",
    "execution.heartbeat_collision_authority_closed", "recovery.started",
    "recovery.action_set_rebased", "recovery.phase_advanced", "recovery.completed",
    "worker.definition_registered", "worker.enabled", "worker.draining",
    "worker.quarantined", "worker.retired", "worker_session.registered",
    "worker_session.ready", "worker_session.draining", "worker_session.offline",
    "worker_session.quarantined", "worker_session.closed",
    "worker_session.heartbeat_accepted", "worker_session.message_rejected",
    "job.submitted", "job.queued", "job.attempt_allocated", "job.budget_settled",
    "job.retry_scheduled", "job.retry_ready", "job.stop_latched",
    "job.cancellation_observed", "job.assurance_evaluated", "job.succeeded",
    "job.failed", "job.cancelled", "job.timed_out", "job.policy_violated",
    "storage_root.hold_release_observed", "job.message_rejected",
    "attempt.authorization_bound", "attempt.preflight_started",
    "attempt.preflight_progressed", "attempt.preflight_passed", "attempt.starting",
    "attempt.running", "attempt.output_staging_preallocated",
    "attempt.result_ingress_received", "attempt.result_accepted",
    "attempt.result_rejected", "attempt.draining", "attempt.stop_latched",
    "attempt.stop_progressed", "attempt.cleaning", "attempt.cleanup_progressed",
    "attempt.succeeded", "attempt.failed", "attempt.cancelled", "attempt.timed_out",
    "attempt.policy_violated", "attempt.lease_expired", "attempt.lost",
    "attempt.fenced", "attempt.rejected", "attempt.assurance_evaluated",
    "lease.offered", "lease.claimed", "lease.heartbeat_accepted", "lease.renewed",
    "lease.released", "lease.revoked", "lease.expired", "lease.fenced",
    "lease.tombstone_republished", "lease.message_rejected", "log.chunk_committed",
    "log.chunk_duplicate_observed", "log.chunk_rejected", "log.truncated",
    "log.eof_accepted", "log.eof_rejected", "log.closed",
    "log.closure_recovery_closed", "log.intake_recovery_terminalized",
)

IDEMPOTENCY_OPERATION_KINDS_V1 = (
    "START_JOB", "CANCEL_JOB", "REGISTER_WORKER_SESSION", "CLAIM_LEASE",
    "RENEW_LEASE", "RELEASE_LEASE", "PREALLOCATE_OUTPUT_STAGING",
    "RECEIVE_RESULT_INGRESS", "SUBMIT_RESULT", "APPEND_LOG_CHUNK",
    "CLOSE_LOG_STREAM",
)
_ENTITY_KIND_ORDER = (
    "EXECUTOR", "RECOVERY", "WORKER", "WORKER_SESSION", "JOB", "ATTEMPT", "LEASE", "LOG_STREAM",
)
_ENTITY_KIND_RANK = {value: rank for rank, value in enumerate(_ENTITY_KIND_ORDER)}
_RECOVERY_ACTION_KIND_ORDER = (
    "COMMIT_DUE_EVENT", "RESTORE_CLOCK", "FENCE_LEASE", "REPUBLISH_TOMBSTONE",
    "OFFLINE_SESSION", "TERMINATE_PROCESS_TREE", "REVOKE_HANDLES", "CLOSE_SESSION",
    "CLOSE_LOG", "VERIFY_OUTPUT_STORAGE", "VERIFY_TERMINAL_SOURCE",
    "BIND_DURABLE_ATTEMPT_AUTHORIZATION", "RELEASE_INACTIVE_EXECUTION_INPUT_HOLD",
    "RELEASE_DUE_EXECUTION_HOLD", "QUARANTINE_RESOURCE", "ADVANCE_ATTEMPT",
    "CLEAN_RESOURCE", "COLLECT_ACCOUNTING", "SETTLE_BUDGET",
    "EVALUATE_ATTEMPT_ASSURANCE", "EVALUATE_JOB_ASSURANCE", "ADVANCE_JOB",
)
_RECOVERY_ACTION_KIND_RANK = {
    value: rank for rank, value in enumerate(_RECOVERY_ACTION_KIND_ORDER)
}
_RECOVERY_PHASE_KINDS = {
    "STARTED": {"COMMIT_DUE_EVENT"},
    "FENCING": {
        "FENCE_LEASE", "REPUBLISH_TOMBSTONE", "OFFLINE_SESSION",
        "BIND_DURABLE_ATTEMPT_AUTHORIZATION", "ADVANCE_ATTEMPT", "ADVANCE_JOB",
    },
    "RECONCILING": {
        "TERMINATE_PROCESS_TREE", "REVOKE_HANDLES", "CLOSE_SESSION", "CLOSE_LOG",
        "VERIFY_OUTPUT_STORAGE", "VERIFY_TERMINAL_SOURCE", "QUARANTINE_RESOURCE",
        "ADVANCE_ATTEMPT", "CLEAN_RESOURCE", "COLLECT_ACCOUNTING",
    },
    "FINALIZING": {
        "RESTORE_CLOCK", "ADVANCE_ATTEMPT", "SETTLE_BUDGET",
        "EVALUATE_ATTEMPT_ASSURANCE", "EVALUATE_JOB_ASSURANCE", "ADVANCE_JOB",
        "RELEASE_INACTIVE_EXECUTION_INPUT_HOLD", "RELEASE_DUE_EXECUTION_HOLD",
    },
}
_ATTEMPT_TERMINAL_EVENT_TYPES = {
    "attempt.succeeded", "attempt.failed", "attempt.cancelled", "attempt.timed_out",
    "attempt.policy_violated", "attempt.lease_expired", "attempt.lost", "attempt.fenced",
    "attempt.rejected",
}
_CONTROL_DIMENSION_ORDER = (
    "IDENTITY_AUTHORIZATION", "FILESYSTEM", "NETWORK", "PROCESS_EXECUTABLE", "RESOURCE",
    "ENVIRONMENT_CREDENTIAL", "LOG_OUTPUT_CAPTURE", "RUNTIME_INPUT_OUTPUT_IDENTITY",
    "CANCELLATION_FENCING", "TERMINATION_CLEANUP",
)
_CONTROL_PHASE_ORDER = ("PREFLIGHT", "RUNTIME", "TERMINATION", "CLEANUP")
_CONTROL_PHASE_RANK = {value: rank for rank, value in enumerate(_CONTROL_PHASE_ORDER)}
_CONTROL_EVIDENCE_KIND_ORDER = (
    "TASK_BINDING", "CAPABILITY_BINDING", "SNAPSHOT_BINDING", "WARD_DECISION",
    "APPROVAL_RECEIPT", "BACKEND_CONFIGURATION", "HOST_IDENTITY", "POLICY_RESOLUTION",
    "BASE_IDENTITY", "INPUT_IDENTITY", "MATERIALIZATION_IDENTITY", "ENVIRONMENT_CONSTRUCTION",
    "FILESYSTEM_POLICY", "NETWORK_POLICY", "EXECUTABLE_SELECTION", "PROCESS_TREE",
    "WALL_TIME_ENFORCEMENT", "RESOURCE_ACCOUNTING", "CREDENTIAL_NONINHERITANCE",
    "LOG_CAPTURE", "OUTPUT_VALIDATION", "STORAGE_OBSERVATION", "FENCE_TOMBSTONE",
    "TERMINATION", "HANDLE_REVOCATION", "CLEANUP", "QUARANTINE",
    "TERMINAL_SOURCE_VERIFICATION", "CONFORMANCE_FIXTURE",
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
    if ledger["budget_ledger_sigil"] != content_sigil(
        _without(ledger, "budget_ledger_sigil")
    ):
        _fail("Execution budget ledger self-Sigil mismatch")
    for name, dimension in ledger.items():
        if name == "budget_ledger_sigil":
            continue
        total = dimension["consumed"] + dimension["reserved"]
        expected_status = (
            "AVAILABLE" if total < dimension["limit"]
            else "EXHAUSTED" if total == dimension["limit"]
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
        if any(
            recovery["prior_recovery_id"] is None for recovery in state["recoveries"][1:]
        ):
            _fail("non-first Recovery projection must name a prior Recovery")
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
        if session_ids != sorted(session_ids, key=lambda value: _unsigned_ascii(value, "Worker session ID")):
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
        deadline_keys.append((
            _parse_time(deadline["due_at"]),
            deadline["fixed_priority"],
            _unsigned_ascii(deadline["entity_id"], "Deadline entity ID"),
        ))
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
        "recoveries", "workers", "worker_sessions", "jobs", "attempts",
        "leases", "log_streams", "deadlines", "idempotency_records",
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
    state = build_execution_state_v1({
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
        "recoveries": [], "workers": [], "worker_sessions": [], "jobs": [],
        "attempts": [], "leases": [], "log_streams": [], "deadlines": [],
        "idempotency_records": [],
    })
    if head is not None:
        validate_execution_initial_state_supplied_facts_v1(event, state, head)
    return state


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
        or event["executor_build_sigil"] != executor["executor_build_binding"]["executor_build_sigil"]
    ):
        _fail("Clock uncertainty Event disagrees with replayed Executor identity")
    if executor["clock_state"] != "TRUSTED" or executor["authority_gates"]:
        _fail("Clock uncertainty Event requires an ungated trusted Executor")
    revision = event["entity_revisions"]
    expected_revision = [{
        "entity_kind": "EXECUTOR", "entity_id": executor["executor_instance_id"],
        "preceding_revision": executor["revision"], "next_revision": executor["revision"] + 1,
    }]
    if revision != expected_revision:
        _fail("Clock uncertainty Event has invalid Executor revision effect")
    payload = event["payload"]
    if payload["last_trusted_utc"] != executor["last_trusted_utc"]:
        _fail("Clock uncertainty Event disagrees with replayed trusted-time anchor")
    if payload["affected_lease_ids"]:
        _fail("Clock uncertainty reducer requires no live Lease authority")
    if any(state[member] for member in (
        "workers", "worker_sessions", "jobs", "attempts", "leases", "log_streams",
        "deadlines", "idempotency_records", "recoveries",
    )):
        _fail("Clock uncertainty reducer requires the initial empty projections")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced_executor = {**executor,
        "revision": executor["revision"] + 1,
        "clock_state": "UNCERTAIN",
        "clock_uncertain_event_id": event["event_id"],
        "authority_gates": ["CLOCK_UNCERTAIN"],
        "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"],
    }
    reduced["executor"] = reduced_executor
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"], "through_sequence": event["sequence"],
        "through_event_id": event["event_id"], "through_event_sigil": event["event_sigil"],
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
        or event["executor_build_sigil"] != executor["executor_build_binding"]["executor_build_sigil"]
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
    if any(payload[member] for member in (
        "nonterminal_job_ids", "nonterminal_attempt_ids", "nonterminal_lease_ids",
        "nonterminal_worker_session_ids",
    )):
        _fail("Recovery start reducer requires empty nonterminal projections")
    if any(state[member] for member in (
        "workers", "worker_sessions", "jobs", "attempts", "leases", "log_streams",
        "deadlines", "idempotency_records",
    )):
        _fail("Recovery start reducer requires the initial empty projections")
    expected_revisions = [
        {
            "entity_kind": "EXECUTOR", "entity_id": executor["executor_instance_id"],
            "preceding_revision": executor["revision"], "next_revision": executor["revision"] + 1,
        },
        {
            "entity_kind": "RECOVERY", "entity_id": payload["recovery_id"],
            "preceding_revision": None, "next_revision": 0,
        },
    ]
    if event["entity_revisions"] != expected_revisions:
        _fail("Recovery start Event has invalid revision effects")
    reduced = {key: value for key, value in state.items() if key != "state_sigil"}
    reduced["executor"] = {
        **executor, "revision": executor["revision"] + 1,
        "active_recovery_id": payload["recovery_id"],
        "authority_gates": ["CLOCK_UNCERTAIN", "RECOVERY_ACTIVE"],
        "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"],
    }
    reduced["recoveries"] = [{
        "recovery_id": payload["recovery_id"], "revision": 0, "state": "STARTED",
        "prior_recovery_id": None, "started_event_sigil": event["event_sigil"],
        "current_action_set_sigil": payload["initial_action_set_sigil"],
        "last_event_id": event["event_id"], "last_event_sigil": event["event_sigil"],
    }]
    reduced["journal_binding"] = {
        "journal_id": event["journal_id"], "through_sequence": event["sequence"],
        "through_event_id": event["event_id"], "through_event_sigil": event["event_sigil"],
    }
    return build_execution_state_v1(reduced)


def replay_execution_journal_prefix_v1(
    events: list[dict[str, Any]], *, head: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Verify a v1 Journal prefix and reduce its installed bounded suffixes.

    Prefix integrity is checked before reducer dispatch.  A syntactically valid
    Event outside the explicitly installed ISR3/clock-gate/empty-Recovery path
    fails closed rather than being interpreted as a no-op or guessed transition.
    """
    if not events:
        _fail("Execution Journal replay requires a nonempty prefix")
    if not all(isinstance(event, dict) for event in events):
        _fail("Execution Journal replay prefix contains a nonobject Event")
    if events[0].get("event_type") != "executor.epoch_started":
        _fail("Execution Journal replay prefix must begin with executor epoch start")
    journal_id = events[0].get("journal_id")
    previous_sigil: str | None = None
    previous_recorded_at: datetime | None = None
    epoch_build_sigils: dict[tuple[str, int], str] = {}
    for expected_sequence, event in enumerate(events, 1):
        validate_execution_journal_event_v1(event)
        if event["journal_id"] != journal_id:
            _fail("Execution Journal replay prefix contains multiple journal identities")
        if event["sequence"] != expected_sequence:
            _fail("Execution Journal replay prefix has a sequence gap")
        if event["previous_event_sigil"] != previous_sigil:
            _fail("Execution Journal replay prefix has a broken Event chain")
        recorded_at = _parse_time(event["recorded_at"])
        if previous_recorded_at is not None and recorded_at < previous_recorded_at:
            _fail("Execution Journal replay prefix has decreasing recorded_at time")
        epoch_key = (event["executor_instance_id"], event["executor_epoch"])
        prior_build_sigil = epoch_build_sigils.setdefault(epoch_key, event["executor_build_sigil"])
        if event["executor_build_sigil"] != prior_build_sigil:
            _fail("Execution Journal replay prefix has conflicting Executor build Sigils")
        previous_sigil = event["event_sigil"]
        previous_recorded_at = recorded_at
    if head is not None:
        validate_execution_journal_head_v1(head)
        last = events[-1]
        if (
            head["journal_id"] != journal_id
            or head["last_sequence"] != last["sequence"]
            or head["last_event_id"] != last["event_id"]
            or head["last_event_sigil"] != last["event_sigil"]
        ):
            _fail("Execution Journal Head disagrees with replay prefix")
    initial_state = replay_execution_initial_prefix_v1([events[0]])
    if len(events) == 1:
        if head is not None:
            validate_execution_initial_state_supplied_facts_v1(events[0], initial_state, head)
        return initial_state
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


def validate_execution_recovery_action_set_v1(action_set: dict[str, Any]) -> None:
    """Validate a frozen Recovery action set without deriving or executing it."""
    validate_instance("execution-recovery-action-set-1.0.json", action_set)
    _check_nfc(action_set)
    if action_set["action_set_sigil"] != content_sigil(
        _without(action_set, "action_set_sigil")
    ):
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
        if action["target_sequence"] != action_set["derived_through_sequence"] + 2 + action["ordinal"]:
            _fail("Execution Recovery action target sequence disagrees with ordinal")
        prerequisites = action["prerequisite_event_ids"]
        if prerequisites != sorted(
            prerequisites, key=lambda value: _unsigned_ascii(value, "Recovery prerequisite Event ID")
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
            action_kind_rank, _parse_time(parameters["due_at"]),
            _DEADLINE_PRIORITY[parameters["deadline_kind"]],
            _unsigned_ascii(parameters["deadline_entity_id"], "Recovery deadline entity ID"),
            _unsigned_ascii(action["target_event_type"], "Recovery target Event type"),
        )
    return (
        action_kind_rank, _ENTITY_KIND_RANK[action["entity_kind"]],
        _unsigned_ascii(action["entity_id"], "Recovery entity ID"),
        _unsigned_ascii(action["target_event_type"], "Recovery target Event type"), logical_action,
    )


def _canonical_execution_recovery_logical_action_v1(action: dict[str, Any]) -> bytes:
    """Return RFC-0012's reservation-independent logical-action bytes."""
    logical = {
        key: deepcopy(value) for key, value in action.items()
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


def validate_execution_state_supplied_recovery_action_set_v1(
    state: dict[str, Any], action_set: dict[str, Any],
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
    action_set: dict[str, Any], event: dict[str, Any],
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
    expected_revision = [{
        "entity_kind": action["entity_kind"], "entity_id": action["entity_id"],
        "preceding_revision": action["expected_revision"],
        "next_revision": action["expected_revision"] + 1,
    }]
    if event["entity_revisions"] != expected_revision:
        _fail("Recovery action Event revision effect disagrees with supplied action")


def derive_result_ingress_receipt_id_v1(receipt: dict[str, Any]) -> str:
    owner = receipt["owner_binding"]
    digest = content_sigil([
        "execution-result-ingress-receipt-id/1.0", owner["job_id"],
        owner["attempt_id"], receipt["result_sigil"],
    ]).removeprefix("sha256:").upper()
    return "OIR-" + digest


def validate_execution_result_ingress_receipt_v1(receipt: dict[str, Any]) -> None:
    validate_instance("execution-result-ingress-receipt-1.0.json", receipt)
    _check_nfc(receipt)
    _validate_observation_owner_binding(receipt["owner_binding"])
    if receipt["receiver_identity"]["executor_epoch"] != receipt["owner_binding"]["executor_epoch"]:
        _fail("Result ingress receiver epoch disagrees with owner binding")
    observation = receipt["result_observation_binding"]
    if observation["observation_evidence_subject_sigil"] != derive_observation_evidence_subject_sigil_v1(
        receipt["owner_binding"], observation
    ):
        _fail("Result ingress receipt observation subject Sigil mismatch")
    if receipt["ingress_receipt_id"] != derive_result_ingress_receipt_id_v1(receipt):
        _fail("Result ingress receipt ID mismatch")
    verification = receipt["credential_verification"]
    expected_verification = content_sigil([
        "execution-result-ingress-credential-verification/1.0",
        receipt["owner_binding"], receipt["result_sigil"], receipt["received_at"],
        receipt["control_channel_identity_sigil"], verification["lease_credential_digest"],
        verification["verification_profile_sigil"], verification["verified_at"],
    ])
    if verification["verification_sigil"] != expected_verification:
        _fail("Result ingress credential verification Sigil mismatch")
    if not (_parse_time(receipt["received_at"]) <= _parse_time(verification["verified_at"]) <= _parse_time(receipt["created_at"])):
        _fail("Result ingress receipt time order mismatch")
    if receipt["ingress_receipt_sigil"] != content_sigil(_without(receipt, "ingress_receipt_sigil")):
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
        "observation_evidence_subject_sigil": receipt["result_observation_binding"]["observation_evidence_subject_sigil"],
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
        or ("ATTEMPT", owner["attempt_id"]) not in {
            (revision["entity_kind"], revision["entity_id"])
            for revision in candidate["entity_revisions"]
        }
    ):
        _fail("Result ingress candidate Event disagrees with Receipt owner")
    expected_key = content_sigil([
        "execution-result-ingress-key/1.0", owner["attempt_id"], receipt["result_sigil"],
    ])
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
            "journal_id": candidate["journal_id"], "event_id": candidate["event_id"],
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
    digest = content_sigil([
        "execution-storage-root-manifest-id/1.0", manifest["root_kind"],
        manifest["job_id"], manifest["attempt_id"], manifest["owner_binding"],
    ]).removeprefix("sha256:").upper()
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
            expected_subject_id = content_sigil([
                "execution-storage-subject-id/1.0", manifest["root_kind"],
                manifest["job_id"], manifest["attempt_id"], subject,
            ])
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
    digest = content_sigil([
        "execution-root-hold-release-authorization-id/1.0",
        authorization["storage_root"]["hold_id"],
    ]).removeprefix("sha256:").upper()
    return f"EHR-{digest}"


def validate_execution_root_hold_release_authorization_v1(
    authorization: dict[str, Any],
) -> None:
    """Validate an EHR's local bindings without authorizing a Storage release."""
    validate_instance("execution-root-hold-release-authorization-1.0.json", authorization)
    _check_nfc(authorization)
    if authorization["release_authorization_id"] != derive_execution_root_hold_release_authorization_id_v1(authorization):
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
    digest = content_sigil([
        "execution-control-evidence-set-id/1.0", evidence_set["job_id"],
        evidence_set["attempt_id"], evidence_set["attempt_binding_sigil"],
    ]).removeprefix("sha256:").upper()
    return f"CES-{digest}"


def validate_execution_control_evidence_set_v1(evidence_set: dict[str, Any]) -> None:
    """Validate a frozen CES locally without resolving its evidence records."""
    validate_instance("execution-control-evidence-set-1.0.json", evidence_set)
    _check_nfc(evidence_set)
    if evidence_set["control_evidence_set_id"] != derive_execution_control_evidence_set_id_v1(evidence_set):
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
    digest = content_sigil([
        "execution-quarantine-binding-set-id/1.0", binding_set["job_id"],
        binding_set["attempt_id"], binding_set["attempt_binding_sigil"],
        binding_set["quarantine_plan_sigil"],
        binding_set["terminalization_storage_manifest_binding"],
    ]).removeprefix("sha256:").upper()
    return f"QBS-{digest}"


def validate_execution_quarantine_binding_set_v1(binding_set: dict[str, Any]) -> None:
    """Validate a frozen QBS locally without resolving the Storage projection."""
    validate_instance("execution-quarantine-binding-set-1.0.json", binding_set)
    _check_nfc(binding_set)
    if binding_set["quarantine_binding_set_id"] != derive_execution_quarantine_binding_set_id_v1(binding_set):
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


def derive_execution_output_storage_observation_set_id_v1(
    observation_set: dict[str, Any],
) -> str:
    """Derive the immutable OS-ID from its terminal Attempt inputs."""
    digest = content_sigil([
        "execution-output-storage-observation-set-id/1.0",
        observation_set["job_id"], observation_set["attempt_id"],
        observation_set["attempt_binding_sigil"], observation_set["result_binding"],
        observation_set["log_closure_sigil"], observation_set["output_closure_sigil"],
        observation_set["control_evidence_set_binding"],
        observation_set["quarantine_binding_set_binding"],
        observation_set["terminalization_storage_manifest_binding"],
        observation_set["output_root_protection"], observation_set["terminal_source_binding"],
    ]).removeprefix("sha256:").upper()
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
    storage: dict[str, Any], blob_sigil: str, size_bytes: int,
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
        if integrity != sorted(integrity, key=lambda value: _unsigned_ascii(value, "integrity Event Sigil")):
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
    if observation_set["observation_set_id"] != derive_execution_output_storage_observation_set_id_v1(observation_set):
        _fail("Execution Output Storage Observation Set ID mismatch")
    if observation_set["observation_set_sigil"] != content_sigil(
        _without(observation_set, "observation_set_sigil")
    ):
        _fail("Execution Output Storage Observation Set self-Sigil mismatch")
    protection = observation_set["output_root_protection"]
    if protection["kind"] not in {"NO_HOLD", "HELD"}:
        _fail("Output Storage Observation requires a terminal output-root protection branch")
    if protection["terminalization_storage_manifest_binding"] != observation_set[
        "terminalization_storage_manifest_binding"
    ]:
        _fail("Output Storage Observation protection disagrees with terminalization manifest")

    members = observation_set["members"]
    cursor = 0
    result_kind = observation_set["result_binding"]["kind"]
    if members[cursor]["kind"] == "ATTEMPT_OUTPUTS_NONE":
        expected_reason = {
            "NONE": "NO_RESULT", "REJECTED": "RESULT_REJECTED",
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

    logs = members[cursor:cursor + 3]
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
            (_unsigned_ascii(member["control_evidence_id"], "control evidence ID"),
             _CONTROL_PHASE_RANK[member["phase"]],
             _CONTROL_EVIDENCE_KIND_RANK[member["evidence_kind"]],
             member["phase_evidence_entry_sigil"])
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
            or any(terminal_binding[field] is not None for field in (
                "terminal_source_identity", "terminal_source_sigil", "storage_blob",
            ))
            or terminal_binding["file_count"] != 0
            or terminal_binding["byte_count"] != 0
            or terminal["reason_codes"] != terminal_binding["reason_codes"]
        ):
            _fail("Output Storage Observation terminal-source NONE disagrees with binding")
    else:
        if terminal_binding["kind"] not in {"VERIFIED", "QUARANTINED"}:
            _fail("Output Storage Observation terminal source lacks a compatible binding")
        copied = (
            "terminal_source_identity", "terminal_source_sigil", "storage_blob",
            "retention_policy_sigil", "file_count", "byte_count",
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
                member["storage"], member["blob_sigil"], member["byte_size"],
                observation_set["storage_event"],
            )
        elif kind == "LOG_STREAM":
            _validate_observation_storage_v1(
                member["content"]["storage"], member["content"]["blob_sigil"],
                member["captured_bytes"], observation_set["storage_event"],
            )
        elif kind == "TERMINAL_SOURCE":
            _validate_observation_storage_v1(
                member["storage"], member["storage_blob"]["blob_sigil"],
                member["storage_blob"]["size_bytes"], observation_set["storage_event"],
            )

    expected_blob_sigils = sorted({
        blob_sigil for member in members
        for blob_sigil in _observation_member_blob_refs_v1(member)
    }, key=lambda value: _unsigned_ascii(value, "Blob Sigil"))
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
    return content_sigil([
        "execution-result-observation-subject/1.0", owner_binding,
        result_observation_binding["runtime_observation"],
        result_observation_binding["termination_observation"],
    ])


def derive_observation_evidence_id_v1(evidence: dict[str, Any]) -> str:
    digest = content_sigil([
        "execution-observation-evidence-id/1.0", evidence["job_id"],
        evidence["attempt_id"], evidence["result_ingress_receipt_binding"]["ingress_receipt_id"],
        evidence["result_observation_binding"]["observation_evidence_subject_sigil"],
    ]).removeprefix("sha256:").upper()
    return "OVE-" + digest


def _observation_owner(evidence: dict[str, Any]) -> dict[str, Any]:
    members = (
        "job_id", "job_binding_sigil", "attempt_id", "attempt_binding_sigil",
        "lease_id", "lease_binding_sigil", "worker_id", "worker_binding_sigil",
        "worker_session_id", "worker_session_binding_sigil", "executor_epoch",
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
    if binding["observation_evidence_subject_sigil"] != derive_observation_evidence_subject_sigil_v1(owner, binding):
        _fail("Observation Evidence subject Sigil mismatch")
    if evidence["observation_evidence_id"] != derive_observation_evidence_id_v1(evidence):
        _fail("Observation Evidence ID mismatch")
    runtime = binding["runtime_observation"]
    termination = binding["termination_observation"]
    if not (_parse_time(runtime["started_at"]) <= _parse_time(runtime["ended_at"]) <= _parse_time(termination["observed_at"]) <= _parse_time(evidence["created_at"])):
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
        if assessment["verified_source_binding"]["source_kind"] != termination["observation_source"]:
            _fail("MATCHED Observation Evidence source does not match termination observation")
    if assessment["kind"] == "MISMATCHED" and any(reason["reason_code"] != "MISMATCH" for reason in assessment["reason_bindings"]):
        _fail("MISMATCHED Observation Evidence contains a non-MISMATCH reason")
    if evidence["observation_evidence_sigil"] != content_sigil(_without(evidence, "observation_evidence_sigil")):
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
    if event_type == "attempt.result_rejected" and payload.get("disposition_kind") == "LATE_OR_CONFLICTING_REJECTION":
        candidates.append(_context_value(context, "pre_event_attempt_last_event_id"))
    if context.get("heartbeat_collision_dependent", False):
        candidates.append(_context_value(context, "heartbeat_collision_event_id"))
    if context.get("ordinary_l12_suffix", False):
        candidates.append(None if context.get("ordinary_l12_anchor", False) else _context_value(context, "l12_preceding_event_id"))
    if context.get("missing_intent_recovery", False) or event_type in {"log.closure_recovery_closed", "log.intake_recovery_terminalized"}:
        candidates.append(_context_value(context, "recovery_opening_event_id"))
    elif event["recovery_action_binding"] is not None:
        candidates.append(_context_value(context, "recovery_opening_event_id"))
    cause = payload.get("transition_cause")
    if isinstance(cause, dict):
        if cause["trigger_kind"] == "PRIOR_EVENT":
            candidates.append(cause["trigger_event_id"])
        elif event["recovery_action_binding"] is None:
            if cause["trigger_event_id"] != event["event_id"] or cause["effective_sequence"] != event["sequence"]:
                _fail("non-prior transition cause does not bind the enclosing Event")
            candidates.append(None)
    if len({candidate for candidate in candidates}) > 1:
        _fail("contradictory JEW2 causation rules")
    return candidates[0] if candidates else None


def expected_event_idempotency_v1(event: dict[str, Any], context: dict[str, Any]) -> str | None:
    """Evaluate JEW3 from locally derivable fields and explicit durable resolvers."""
    event_type = event["event_type"]
    payload = event["payload"]
    if event_type == "execution.heartbeat_collision_authority_closed" or context.get("heartbeat_collision_dependent", False):
        return _context_value(context, "candidate_inventory_bytes_sigil")
    if event_type == "attempt.output_staging_preallocated":
        return content_sigil(["execution-output-staging-preallocation-key/1.0", payload["job_id"], payload["attempt_id"], payload["output_handle_id"]])
    attempt_id = context.get("attempt_id")
    if event_type == "attempt.result_ingress_received":
        return content_sigil(["execution-result-ingress-key/1.0", _context_value(context, "attempt_id"), payload["result_sigil"]])
    if event_type == "attempt.result_accepted" or (
        event_type == "attempt.result_rejected" and payload.get("disposition_kind") == "FIRST_DISPOSITION_REJECTION"
    ):
        result_sigil = payload.get("result_sigil", payload.get("claimed_result_sigil"))
        return content_sigil(["execution-result-disposition-key/1.0", _context_value(context, "attempt_id"), result_sigil])
    if event_type == "attempt.result_rejected" and payload.get("disposition_kind") == "LATE_OR_CONFLICTING_REJECTION":
        return content_sigil(["execution-result-rejection-message-key/1.0", _context_value(context, "attempt_id"), payload["message_sigil"]])
    del attempt_id
    if context.get("ordinary_l12_suffix", False):
        return _context_value(context, "l12_idempotency_key_sigil") if context.get("ordinary_l12_anchor", False) else None
    if context.get("missing_intent_recovery", False) and event_type in {"log.chunk_rejected", "log.eof_rejected"}:
        return _context_value(context, "original_idempotency_key_sigil")
    if event_type == "log.intake_recovery_terminalized":
        return None if context.get("original_anchor_survived", False) else _context_value(context, "original_idempotency_key_sigil")
    if event_type in {"log.closed", "log.closure_recovery_closed"}:
        return None
    if event_type in {"log.eof_accepted", "log.eof_rejected"}:
        return _context_value(context, "close_log_stream_idempotency_key_sigil")
    if context.get("state_disposition_event", False):
        return _context_value(context, "state_idempotency_key_sigil")
    return None


def validate_execution_journal_event_v1(event: dict[str, Any], *, context: dict[str, Any] | None = None) -> None:
    """Validate a closed Event and, when supplied, the JEW2/JEW3 dependency matrix."""
    validate_instance("execution-journal-event-1.0.json", event)
    _check_nfc(event)
    revisions = [
        (_ENTITY_KIND_RANK[item["entity_kind"]], _unsigned_ascii(item["entity_id"], "entity revision ID"))
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
