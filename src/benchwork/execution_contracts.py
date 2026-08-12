"""Pure, fail-closed validators for RFC-0012 State and Journal Event wires.

These helpers validate closed bytes and deterministic projections only.  They
do not append an Event, replay a Journal, acknowledge a request, or grant any
runtime, storage, Result, assurance, or scientific authority.
"""

from __future__ import annotations

import json
import math
import unicodedata
from datetime import datetime
from typing import Any, NoReturn

from .athanor import AthanorError, content_sigil
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
        if unicodedata.normalize("NFC", value) != value:
            _fail("JSON string is not NFC-normalized")
    elif isinstance(value, dict):
        for key, member in value.items():
            _check_nfc(key)
            _check_nfc(member)
    elif isinstance(value, list):
        for member in value:
            _check_nfc(member)
    elif isinstance(value, float) and not math.isfinite(value):
        _fail("non-finite JSON number is forbidden")


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


def _idempotency_projection(record: dict[str, Any]) -> tuple[int, str, str]:
    owner = record if "operation_kind" in record else record["core"]
    operation = owner["operation_kind"]
    try:
        rank = _IDEMPOTENCY_RANK[operation]
    except KeyError:
        _fail(f"unknown idempotency operation: {operation}")
    return rank, owner["scope_id"], owner["idempotency_key_sigil"]


def validate_execution_state_v1(state: dict[str, Any]) -> None:
    """Validate a State cache as bytes/projections, never as replay authority."""
    validate_instance("execution-state-1.0.json", state)
    _check_nfc(state)
    worker_ids: set[str] = set()
    for session in state["worker_sessions"]:
        session_id = session["worker_session_id"]
        if session_id in worker_ids:
            _fail("duplicate Worker-Session projection identity")
        worker_ids.add(session_id)
        capacity = session["capacity"]
        if capacity is not None and session["capacity_in_use"] > capacity:
            _fail("Worker-Session capacity_in_use exceeds capacity")
        if session["lease_ids"] != sorted(session["lease_ids"]):
            _fail("Worker-Session lease_ids are not unsigned-ASCII sorted")
    lease_ids = [lease["lease_id"] for lease in state["leases"]]
    if len(lease_ids) != len(set(lease_ids)):
        _fail("duplicate Lease projection identity")
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
    revisions = [(item["entity_kind"], item["entity_id"]) for item in event["entity_revisions"]]
    if revisions != sorted(revisions) or len(revisions) != len(set(revisions)):
        _fail("entity_revisions are not strictly sorted and unique")
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
