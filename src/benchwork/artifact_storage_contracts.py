"""Fail-closed local validators for RFC-0013 Storage Journal wire contracts.

These helpers check canonical documents and caller-supplied prefix relations.
They never append, replay, repair, or authorize an Artifact Storage Journal.
"""

from __future__ import annotations

import json
import math
import unicodedata
from datetime import datetime
from typing import Any, NoReturn

from .athanor import AthanorError, content_sigil
from .schema_validation import validate_instance


def _fail(message: str) -> NoReturn:
    raise AthanorError(message)


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, member in pairs:
        if key in value:
            _fail(f"duplicate JSON key: {key}")
        value[key] = member
    return value


def _reject_nonfinite(token: str) -> NoReturn:
    _fail(f"non-finite JSON number is forbidden: {token}")


def _load_strict_object(raw: str | bytes | bytearray, label: str) -> dict[str, Any]:
    if isinstance(raw, (bytes, bytearray)):
        raw_bytes = bytes(raw)
        if raw_bytes.startswith(b"\xef\xbb\xbf"):
            _fail(f"invalid {label} JSON: UTF-8 BOM is forbidden")
        try:
            raw = raw_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _fail(f"invalid {label} JSON: non-UTF-8 encoding is forbidden")
    if raw.startswith("\ufeff"):
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


def _check_nfc_and_numbers(value: Any) -> None:
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            _fail("JSON string contains a non-Unicode-scalar value")
        if unicodedata.normalize("NFC", value) != value:
            _fail("JSON string is not NFC-normalized")
    elif isinstance(value, dict):
        for key, member in value.items():
            _check_nfc_and_numbers(key)
            _check_nfc_and_numbers(member)
    elif isinstance(value, list):
        for member in value:
            _check_nfc_and_numbers(member)
    elif isinstance(value, float):
        if not math.isfinite(value):
            _fail("non-finite JSON number is forbidden")
        _fail("JSON float is forbidden by canonical Storage wire")


def _without(value: dict[str, Any], member: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != member}


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _upper_digest(prefix: str, preimage: list[Any]) -> str:
    return prefix + content_sigil(preimage).removeprefix("sha256:").upper()


def derive_artifact_storage_reference_set_id_v1(reference_set: dict[str, Any]) -> str:
    """Derive the RFC-0013 deterministic Reference Set identifier."""
    return _upper_digest("RS-", [
        "artifact-storage-reference-set-id/1.0", reference_set["source"],
        reference_set["extractor"], reference_set["edges"], reference_set["validation"],
    ])


def _derive_reference_set_registration_event_id(reference_set: dict[str, Any]) -> str:
    source = reference_set["source"]
    if (
        source["kind"] == "OPERATIONAL_CONTROL_RECORD"
        and source["schema_version"] == "execution-storage-root-manifest/1.0"
    ):
        return _upper_digest("SE-", [
            "artifact-storage-execution-root-reference-set-registration-event-id/1.0",
            source["identity"],
        ])
    return _upper_digest("SE-", [
        "artifact-storage-reference-set-registration-event-id/1.0",
        reference_set["reference_set_id"],
    ])


def validate_artifact_storage_reference_set_v1(reference_set: dict[str, Any]) -> None:
    """Validate a Reference Set locally without resolving its graph."""
    validate_instance("artifact-storage-reference-set-1.0.json", reference_set)
    _check_nfc_and_numbers(reference_set)
    if reference_set["reference_set_id"] != derive_artifact_storage_reference_set_id_v1(reference_set):
        _fail("Artifact Storage Reference Set ID mismatch")
    if reference_set["registration_event_id"] != _derive_reference_set_registration_event_id(reference_set):
        _fail("Artifact Storage Reference Set registration Event ID mismatch")
    if reference_set["reference_set_sigil"] != content_sigil(
        _without(reference_set, "reference_set_sigil")
    ):
        _fail("Artifact Storage Reference Set self-Sigil mismatch")
    edges = reference_set["edges"]
    edge_keys = [
        (edge["relationship"], edge["target_kind"], edge["target_identity"], edge["target_sigil"])
        for edge in edges
    ]
    if edge_keys != sorted(edge_keys):
        _fail("Artifact Storage Reference Set edges are not sorted")
    evidence = reference_set["validation"]["evidence_sigils"]
    if evidence != sorted(evidence):
        _fail("Artifact Storage Reference Set validation evidence is not sorted")


def load_artifact_storage_reference_set_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    reference_set = _load_strict_object(raw, "Artifact Storage Reference Set")
    validate_artifact_storage_reference_set_v1(reference_set)
    return reference_set


def derive_artifact_storage_reference_intent_id_v1(intent: dict[str, Any]) -> str:
    """Derive the RFC-0013 deterministic Reference Intent identifier."""
    return _upper_digest("RI-", [
        "artifact-storage-reference-intent-id/1.0", intent["canonical_event_type"],
        intent["transition_request_id"],
    ])


def validate_artifact_storage_reference_intent_v1(intent: dict[str, Any]) -> None:
    """Validate an immutable Reference Intent without resolving its closure."""
    validate_instance("artifact-storage-reference-intent-1.0.json", intent)
    _check_nfc_and_numbers(intent)
    if intent["reference_intent_id"] != derive_artifact_storage_reference_intent_id_v1(intent):
        _fail("Artifact Storage Reference Intent ID mismatch")
    if intent["record_sigil"] != content_sigil(_without(intent, "record_sigil")):
        _fail("Artifact Storage Reference Intent self-Sigil mismatch")
    references = intent["reference_sets"]
    reference_ids = [reference["reference_set_id"] for reference in references]
    if reference_ids != sorted(reference_ids) or len(set(reference_ids)) != len(reference_ids):
        _fail("Artifact Storage Reference Intent Reference Sets are not uniquely sorted")
    if intent["blob_sigils"] != sorted(intent["blob_sigils"]):
        _fail("Artifact Storage Reference Intent Blob Sigils are not sorted")


def load_artifact_storage_reference_intent_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    intent = _load_strict_object(raw, "Artifact Storage Reference Intent")
    validate_artifact_storage_reference_intent_v1(intent)
    return intent


def validate_canonical_reference_commit_supplied_facts_v1(
    intent: dict[str, Any], chronicle_event: dict[str, Any],
    chronicle_commit: dict[str, Any],
) -> None:
    """Compare a candidate canonical pin with supplied Chronicle Event facts.

    This verifies only the local Event/Receipt chain and the immutable intent
    head binding.  It does not resolve an event-family payload to the request,
    authenticate a Chronicle prefix, or grant Chronicle commit authority.
    """
    validate_artifact_storage_reference_intent_v1(intent)
    validate_instance("chronicle-event-1.1.json", chronicle_event)
    _check_nfc_and_numbers(chronicle_event)
    receipt = chronicle_event["receipt"]
    event_body = {
        key: value for key, value in chronicle_event.items()
        if key not in {"event_body_sigil", "receipt"}
    }
    receipt_body = {key: value for key, value in receipt.items() if key != "receipt_sigil"}
    if intent["expected_chronicle_head"]["event_count"] == 9223372036854775807:
        _fail("Canonical Reference supplied Chronicle commit exceeds the U63 head domain")
    expected_head = {
        "schema_version": "chronicle-head/1.1",
        "event_count": intent["expected_chronicle_head"]["event_count"] + 1,
        "terminal_receipt_sigil": receipt["receipt_sigil"],
    }
    if (
        chronicle_event["event_body_sigil"] != content_sigil(event_body)
        or receipt["receipt_sigil"] != content_sigil(receipt_body)
        or chronicle_event["type"] != intent["canonical_event_type"]
        or chronicle_event["sequence"] != expected_head["event_count"]
        or chronicle_event["previous_receipt_sigil"]
        != intent["expected_chronicle_head"]["terminal_receipt_sigil"]
        or receipt["event_id"] != chronicle_event["event_id"]
        or receipt["event_body_sigil"] != chronicle_event["event_body_sigil"]
        or receipt["previous_receipt_sigil"] != chronicle_event["previous_receipt_sigil"]
        or receipt["accepted_at"] != chronicle_event["occurred_at"]
        or chronicle_commit != {
            "event_id": chronicle_event["event_id"],
            "event_body_sigil": chronicle_event["event_body_sigil"],
            "receipt_id": receipt["receipt_id"],
            "receipt_sigil": receipt["receipt_sigil"],
            "head": expected_head,
        }
    ):
        _fail("Canonical Reference supplied Chronicle commit disagrees with immutable intent")


def validate_canonical_reference_release_supplied_facts_v1(
    intent: dict[str, Any], abort_authority: dict[str, Any], reason: dict[str, Any],
) -> None:
    """Close the local portion of an aborted canonical-reference pin.

    The caller must separately prove by complete authoritative Chronicle replay
    that no bound event exists after the expected Head.  This helper verifies
    the immutable bindings and deterministic absence/authority Sigils only.
    """
    validate_artifact_storage_reference_intent_v1(intent)
    required = {
        "kind", "reference_intent_id", "reference_intent_record_sigil",
        "transition_request_id", "transition_request_sigil", "expected_chronicle_head",
        "verified_chronicle_head", "absence_evidence_sigil", "authority_sigil",
    }
    if set(abort_authority) != required:
        _fail("Canonical Reference abort authority has an invalid closed shape")
    _check_nfc_and_numbers(abort_authority)
    verified_head = abort_authority["verified_chronicle_head"]
    if (
        set(verified_head) != {"schema_version", "event_count", "terminal_receipt_sigil"}
        or verified_head["schema_version"] != "chronicle-head/1.1"
        or not isinstance(verified_head["event_count"], int)
        or isinstance(verified_head["event_count"], bool)
        or not 0 <= verified_head["event_count"] <= 9223372036854775807
        or (
            verified_head["terminal_receipt_sigil"] is not None
            and (
                not isinstance(verified_head["terminal_receipt_sigil"], str)
                or len(verified_head["terminal_receipt_sigil"]) != 71
                or not verified_head["terminal_receipt_sigil"].startswith("sha256:")
                or any(
                    character not in "0123456789abcdef"
                    for character in verified_head["terminal_receipt_sigil"][7:]
                )
            )
        )
    ):
        _fail("Canonical Reference abort authority has an invalid verified Chronicle Head")
    if set(reason) != {"code", "evidence_sigils"}:
        _fail("Canonical Reference release Reason has an invalid closed shape")
    _check_nfc_and_numbers(reason)
    absence_preimage = [
        "artifact-storage-canonical-precommit-absence/1.0",
        intent["reference_intent_id"], intent["record_sigil"],
        intent["transition_request_id"], intent["transition_request_sigil"],
        intent["expected_chronicle_head"], abort_authority["verified_chronicle_head"],
    ]
    expected_evidence = sorted([
        abort_authority["authority_sigil"], abort_authority["absence_evidence_sigil"],
        intent["record_sigil"], intent["transition_request_sigil"],
    ])
    if (
        abort_authority["kind"] != "HEAD_SUPERSEDED_WITHOUT_BOUND_EVENT"
        or abort_authority["reference_intent_id"] != intent["reference_intent_id"]
        or abort_authority["reference_intent_record_sigil"] != intent["record_sigil"]
        or abort_authority["transition_request_id"] != intent["transition_request_id"]
        or abort_authority["transition_request_sigil"] != intent["transition_request_sigil"]
        or abort_authority["expected_chronicle_head"] != intent["expected_chronicle_head"]
        or abort_authority["verified_chronicle_head"]["schema_version"] != "chronicle-head/1.1"
        or abort_authority["verified_chronicle_head"]["event_count"]
        <= intent["expected_chronicle_head"]["event_count"]
        or abort_authority["absence_evidence_sigil"] != content_sigil(absence_preimage)
        or abort_authority["authority_sigil"] != content_sigil({
            key: value for key, value in abort_authority.items() if key != "authority_sigil"
        })
        or reason["code"] != "CHRONICLE_REFERENCE_CHANGED"
        or reason["evidence_sigils"] != expected_evidence
    ):
        _fail("Canonical Reference release facts disagree with immutable intent")


def validate_artifact_storage_legacy_protection_v1(protection: dict[str, Any]) -> None:
    """Validate a Legacy Protection record without resolving its evidence."""
    validate_instance("artifact-storage-legacy-protection-1.0.json", protection)
    _check_nfc_and_numbers(protection)
    if protection["record_sigil"] != content_sigil(_without(protection, "record_sigil")):
        _fail("Artifact Storage Legacy Protection self-Sigil mismatch")


def load_artifact_storage_legacy_protection_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    protection = _load_strict_object(raw, "Artifact Storage Legacy Protection")
    validate_artifact_storage_legacy_protection_v1(protection)
    return protection


def validate_artifact_storage_tail_evidence_v1(evidence: dict[str, Any]) -> None:
    """Validate immutable recovery evidence without reading its raw bytes."""
    validate_instance("artifact-storage-tail-evidence-1.0.json", evidence)
    _check_nfc_and_numbers(evidence)
    if evidence["record_sigil"] != content_sigil(_without(evidence, "record_sigil")):
        _fail("Artifact Storage Tail Evidence self-Sigil mismatch")


def load_artifact_storage_tail_evidence_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    evidence = _load_strict_object(raw, "Artifact Storage Tail Evidence")
    validate_artifact_storage_tail_evidence_v1(evidence)
    return evidence


_RECOVERY_MARKER_PREPARED_PHASES = {
    "RECOVERY_EVENT_PREPARED",
    "RECOVERY_EVENT_RETRY_EVIDENCE_DURABLE",
    "RECOVERY_EVENT_COMMITTED",
}


def validate_artifact_storage_recovery_marker_v1(marker: dict[str, Any]) -> None:
    """Validate a Recovery Marker locally without inspecting journal frames."""
    validate_instance("artifact-storage-recovery-marker-1.0.json", marker)
    _check_nfc_and_numbers(marker)
    if marker["record_sigil"] != content_sigil(_without(marker, "record_sigil")):
        _fail("Artifact Storage Recovery Marker self-Sigil mismatch")
    if marker["last_complete_byte_length"] > marker["old_committed_byte_length"]:
        _fail("Artifact Storage Recovery Marker last complete length exceeds old committed length")
    if marker["discarded_suffix_size"] != (
        marker["old_committed_byte_length"] - marker["last_complete_byte_length"]
    ):
        _fail("Artifact Storage Recovery Marker discarded suffix size mismatch")
    event_fields = (
        "recovery_event_id", "recovery_event_sigil", "recovery_event_seed_record_sigil",
    )
    frame_fields = (
        "recovery_frame_start", "recovery_frame_size", "recovery_frame_sigil",
        "prepared_frame_evidence_record_sigil",
    )
    phase = marker["phase"]
    if phase in {"EVIDENCE_DURABLE", "TAIL_TRUNCATED"}:
        if any(marker[field] is not None for field in event_fields + frame_fields):
            _fail("Artifact Storage Recovery Marker early phase has recovery Event fields")
    elif phase == "RECOVERY_EVENT_ID_DURABLE":
        if any(marker[field] is None for field in event_fields) or any(
            marker[field] is not None for field in frame_fields
        ):
            _fail("Artifact Storage Recovery Marker ID-durable phase fields are inconsistent")
    elif phase in _RECOVERY_MARKER_PREPARED_PHASES and any(
        marker[field] is None for field in event_fields + frame_fields
    ):
        _fail("Artifact Storage Recovery Marker prepared phase lacks fixed frame fields")
    if marker["retry_count"] == 0:
        if marker["latest_retry_evidence_record_sigil"] is not None:
            _fail("Artifact Storage Recovery Marker zero retry count has retry evidence")
    elif marker["latest_retry_evidence_record_sigil"] is None:
        _fail("Artifact Storage Recovery Marker retry count lacks retry evidence")


def load_artifact_storage_recovery_marker_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    marker = _load_strict_object(raw, "Artifact Storage Recovery Marker")
    validate_artifact_storage_recovery_marker_v1(marker)
    return marker


def validate_artifact_storage_disposition_v1(disposition: dict[str, Any]) -> None:
    """Validate a Disposition wire record without resolving its authorization."""
    validate_instance("artifact-storage-disposition-1.0.json", disposition)
    _check_nfc_and_numbers(disposition)
    if disposition["record_sigil"] != content_sigil(_without(disposition, "record_sigil")):
        _fail("Artifact Storage Disposition self-Sigil mismatch")
    if _parse_time(disposition["authorized_at"]) >= _parse_time(disposition["expires_at"]):
        _fail("Artifact Storage Disposition expiry must follow authorization")


def load_artifact_storage_disposition_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    disposition = _load_strict_object(raw, "Artifact Storage Disposition")
    validate_artifact_storage_disposition_v1(disposition)
    return disposition


def validate_artifact_retention_policy_v1(policy: dict[str, Any]) -> None:
    """Validate a Retention Policy locally without deciding its applicability."""
    validate_instance("artifact-retention-policy-1.0.json", policy)
    _check_nfc_and_numbers(policy)
    if policy["record_sigil"] != content_sigil(_without(policy, "record_sigil")):
        _fail("Artifact Retention Policy self-Sigil mismatch")
    for member in ("required_backends", "required_failure_domains"):
        if policy[member] != sorted(policy[member]):
            _fail(f"Artifact Retention Policy {member} is not sorted")


def load_artifact_retention_policy_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    policy = _load_strict_object(raw, "Artifact Retention Policy")
    validate_artifact_retention_policy_v1(policy)
    return policy


def validate_artifact_gc_plan_v1(plan: dict[str, Any]) -> None:
    """Validate a GC Plan's closed local bindings without redoing traversal."""
    validate_instance("artifact-gc-plan-1.0.json", plan)
    _check_nfc_and_numbers(plan)
    if plan["record_sigil"] != content_sigil(_without(plan, "record_sigil")):
        _fail("Artifact GC Plan self-Sigil mismatch")
    if _parse_time(plan["created_at"]) >= _parse_time(plan["grace_ends_at"]):
        _fail("Artifact GC Plan grace deadline must follow creation")
    root_snapshot = plan["root_snapshot"]
    proof = plan["closure_proof"]
    if (
        proof["root_set_sigil"] != root_snapshot["execution_roots"]["root_set_sigil"]
        or proof["extractor_suite_sigil"] != plan["extractor_suite_sigil"]
        or proof["bounds"] != plan["bounds"]
    ):
        _fail("Artifact GC Plan Closure Proof disagrees with plan bindings")
    for collection in (
        root_snapshot["reference_set_sigils"], proof["reachable_blob_sigils"],
        proof["reachable_replica_ids"], [target["target_id"] for target in plan["targets"]],
    ):
        if collection != sorted(collection) or len(set(collection)) != len(collection):
            _fail("Artifact GC Plan collections must be uniquely sorted")
    for target in plan["targets"]:
        remaining = target["expected_remaining_replica_ids"]
        if remaining != sorted(remaining) or len(set(remaining)) != len(remaining):
            _fail("Artifact GC Plan target remaining replicas must be uniquely sorted")


def load_artifact_gc_plan_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    plan = _load_strict_object(raw, "Artifact GC Plan")
    validate_artifact_gc_plan_v1(plan)
    return plan


def validate_artifact_provenance_v1(provenance: dict[str, Any]) -> None:
    """Validate an immutable Provenance record without resolving its lineage."""
    validate_instance("artifact-provenance-1.0.json", provenance)
    _check_nfc_and_numbers(provenance)
    if provenance["record_sigil"] != content_sigil(_without(provenance, "record_sigil")):
        _fail("Artifact Provenance self-Sigil mismatch")


def load_artifact_provenance_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    provenance = _load_strict_object(raw, "Artifact Provenance")
    validate_artifact_provenance_v1(provenance)
    return provenance


def validate_artifact_storage_backend_v1(backend: dict[str, Any]) -> None:
    """Validate a Backend Profile record without probing its declared capabilities."""
    validate_instance("artifact-storage-backend-1.0.json", backend)
    _check_nfc_and_numbers(backend)
    if backend["record_sigil"] != content_sigil(_without(backend, "record_sigil")):
        _fail("Artifact Storage Backend self-Sigil mismatch")
    if backend["verification_methods"] != sorted(backend["verification_methods"]):
        _fail("Artifact Storage Backend verification methods are not sorted")


def load_artifact_storage_backend_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    backend = _load_strict_object(raw, "Artifact Storage Backend")
    validate_artifact_storage_backend_v1(backend)
    return backend


def validate_artifact_provenance_policy_v1(policy: dict[str, Any]) -> None:
    """Validate a Provenance Policy record without deciding Transfer admission."""
    validate_instance("artifact-provenance-policy-1.0.json", policy)
    _check_nfc_and_numbers(policy)
    if policy["record_sigil"] != content_sigil(_without(policy, "record_sigil")):
        _fail("Artifact Provenance Policy self-Sigil mismatch")


def load_artifact_provenance_policy_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    policy = _load_strict_object(raw, "Artifact Provenance Policy")
    validate_artifact_provenance_policy_v1(policy)
    return policy


def validate_artifact_storage_doctor_report_v1(report: dict[str, Any]) -> None:
    """Validate a read-only Doctor report without trusting its observations."""
    validate_instance("artifact-storage-doctor-report-1.0.json", report)
    _check_nfc_and_numbers(report)
    if report["report_sigil"] != content_sigil(_without(report, "report_sigil")):
        _fail("Artifact Storage Doctor Report self-Sigil mismatch")
    if _parse_time(report["completed_at"]) < _parse_time(report["started_at"]):
        _fail("Artifact Storage Doctor Report completes before it starts")


def load_artifact_storage_doctor_report_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    report = _load_strict_object(raw, "Artifact Storage Doctor Report")
    validate_artifact_storage_doctor_report_v1(report)
    return report


def validate_artifact_transfer_v1(transfer: dict[str, Any]) -> None:
    """Validate immutable Transfer bytes without admitting backend work."""
    validate_instance("artifact-transfer-1.0.json", transfer)
    _check_nfc_and_numbers(transfer)
    if transfer["record_sigil"] != content_sigil(_without(transfer, "record_sigil")):
        _fail("Artifact Transfer self-Sigil mismatch")
    if transfer["purpose"] == "ATTEMPT_OUTPUT":
        if (
            transfer["direction"] != "INGEST"
            or transfer["source"]["kind"] != "ATTEMPT_OUTPUT"
            or transfer["source"]["execution"] != transfer["execution"]
            or transfer["destination"]["kind"] != "MANAGED_BACKEND"
            or transfer["destination"]["backend"] != transfer["backend"]
            or transfer["expected_blob_sigil"] is None
        ):
            _fail("Artifact Transfer ATTEMPT_OUTPUT local bindings are inconsistent")


def load_artifact_transfer_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    transfer = _load_strict_object(raw, "Artifact Transfer")
    validate_artifact_transfer_v1(transfer)
    return transfer


def validate_artifact_storage_state_supplied_transfers_v1(
    state: dict[str, Any], *, transfers: list[dict[str, Any]],
) -> None:
    """Compare State Transfer request projections with supplied immutable records."""
    validate_artifact_storage_state_v1(state)
    supplied: dict[str, str] = {}
    for transfer in transfers:
        validate_artifact_transfer_v1(transfer)
        if transfer["transfer_id"] in supplied:
            _fail("Artifact Storage supplied Transfers have duplicate IDs")
        supplied[transfer["transfer_id"]] = transfer["record_sigil"]
    for projection in state["transfer_requests"]:
        if supplied.get(projection["transfer_id"]) != projection["request_record_sigil"]:
            _fail("Artifact Storage State Transfer projection lacks matching supplied record")
    if set(supplied) != {projection["transfer_id"] for projection in state["transfer_requests"]}:
        _fail("Artifact Storage supplied Transfers do not exactly match State projections")


def validate_artifact_storage_state_supplied_transfer_attempts_v1(
    state: dict[str, Any], *, transfers: list[dict[str, Any]],
) -> None:
    """Check supplied Transfer ownership for the Attempt records embedded in State.

    This does not replay attempt transitions, reservations, or backend effects.
    """
    validate_artifact_storage_state_v1(state)
    supplied: dict[str, str] = {}
    for transfer in transfers:
        validate_artifact_transfer_v1(transfer)
        if transfer["transfer_id"] in supplied:
            _fail("Artifact Storage supplied Transfers have duplicate IDs")
        supplied[transfer["transfer_id"]] = transfer["record_sigil"]
    requests = {request["transfer_id"]: request for request in state["transfer_requests"]}
    for wrapper in state["transfer_attempts"]:
        attempt = wrapper["record"]
        request = requests.get(attempt["transfer_id"])
        if request is None or supplied.get(attempt["transfer_id"]) != request["request_record_sigil"]:
            _fail("Artifact Storage Transfer Attempt lacks matching supplied Transfer request")
        if attempt["transfer_attempt_id"] not in request["attempt_ids"]:
            _fail("Artifact Storage Transfer Attempt is absent from its State request projection")


def validate_artifact_storage_state_supplied_provenance_policies_v1(
    state: dict[str, Any], *, policies: list[dict[str, Any]],
) -> None:
    """Compare State Provenance Policy projections with supplied record bytes."""
    validate_artifact_storage_state_v1(state)
    supplied: dict[str, str] = {}
    for policy in policies:
        validate_artifact_provenance_policy_v1(policy)
        if policy["provenance_policy_id"] in supplied:
            _fail("Artifact Storage supplied Provenance Policies have duplicate IDs")
        supplied[policy["provenance_policy_id"]] = policy["record_sigil"]
    for projection in state["provenance_policies"]:
        if supplied.get(projection["provenance_policy_id"]) != projection["record_sigil"]:
            _fail("Artifact Storage State Provenance Policy projection lacks matching supplied record")
    if set(supplied) != {
        projection["provenance_policy_id"] for projection in state["provenance_policies"]
    }:
        _fail("Artifact Storage supplied Provenance Policies do not exactly match State projections")


def validate_artifact_storage_state_supplied_provenance_v1(
    state: dict[str, Any], *, records: list[dict[str, Any]],
) -> None:
    """Compare State Provenance projections with complete supplied records."""
    validate_artifact_storage_state_v1(state)
    supplied: dict[str, str] = {}
    for provenance in records:
        validate_artifact_provenance_v1(provenance)
        if provenance["provenance_id"] in supplied:
            _fail("Artifact Storage supplied Provenance records have duplicate IDs")
        supplied[provenance["provenance_id"]] = provenance["record_sigil"]
    for projection in state["provenance"]:
        if supplied.get(projection["provenance_id"]) != projection["record_sigil"]:
            _fail("Artifact Storage State Provenance projection lacks matching supplied record")
    if set(supplied) != {projection["provenance_id"] for projection in state["provenance"]}:
        _fail("Artifact Storage supplied Provenance records do not exactly match State projections")


def validate_artifact_storage_state_supplied_retention_policies_v1(
    state: dict[str, Any], *, policies: list[dict[str, Any]],
) -> None:
    """Compare State retention-policy projections with supplied record bytes."""
    validate_artifact_storage_state_v1(state)
    supplied: dict[str, str] = {}
    for policy in policies:
        validate_artifact_retention_policy_v1(policy)
        if policy["policy_id"] in supplied:
            _fail("Artifact Storage supplied Retention Policies have duplicate IDs")
        supplied[policy["policy_id"]] = policy["record_sigil"]
    for projection in state["retention_policies"]:
        if supplied.get(projection["policy_id"]) != projection["record_sigil"]:
            _fail("Artifact Storage State Retention Policy projection lacks matching supplied record")
    if set(supplied) != {projection["policy_id"] for projection in state["retention_policies"]}:
        _fail("Artifact Storage supplied Retention Policies do not exactly match State projections")


def validate_artifact_storage_state_supplied_control_records_v1(
    state: dict[str, Any], *, reference_sets: list[dict[str, Any]],
    reference_intents: list[dict[str, Any]],
) -> None:
    """Compare State control-record projections with exact supplied documents.

    This verifies supplied immutable bytes only; callers still own durable
    resolution, graph closure, Storage replay, and Chronicle authority.
    """
    validate_artifact_storage_state_v1(state)
    set_pairs: dict[str, tuple[str, str]] = {}
    for reference_set in reference_sets:
        validate_artifact_storage_reference_set_v1(reference_set)
        if reference_set["reference_set_id"] in set_pairs:
            _fail("Artifact Storage supplied Reference Sets have duplicate IDs")
        set_pairs[reference_set["reference_set_id"]] = (
            reference_set["reference_set_sigil"], reference_set["source"]["identity"],
        )
    for projection in state["reference_sets"]:
        expected = set_pairs.get(projection["reference_set_id"])
        if expected != (projection["reference_set_sigil"], projection["source_identity"]):
            _fail("Artifact Storage State Reference Set projection lacks matching supplied record")
    projected_set_ids = {projection["reference_set_id"] for projection in state["reference_sets"]}
    if set(set_pairs) != projected_set_ids:
        _fail("Artifact Storage supplied Reference Sets do not exactly match State projections")
    intent_pairs: dict[str, str] = {}
    for intent in reference_intents:
        validate_artifact_storage_reference_intent_v1(intent)
        if intent["reference_intent_id"] in intent_pairs:
            _fail("Artifact Storage supplied Reference Intents have duplicate IDs")
        intent_pairs[intent["reference_intent_id"]] = intent["record_sigil"]
    for projection in state["canonical_reference_intents"]:
        expected_intent_sigil = intent_pairs.get(projection["reference_intent_id"])
        if expected_intent_sigil != projection["record_sigil"]:
            _fail("Artifact Storage State Reference Intent projection lacks matching supplied record")
    projected_intent_ids = {
        projection["reference_intent_id"] for projection in state["canonical_reference_intents"]
    }
    if set(intent_pairs) != projected_intent_ids:
        _fail("Artifact Storage supplied Reference Intents do not exactly match State projections")


def validate_artifact_storage_journal_event_v1(event: dict[str, Any]) -> None:
    """Validate a closed, self-authenticating Storage Journal Event locally."""
    validate_instance("artifact-storage-journal-event-1.0.json", event)
    _check_nfc_and_numbers(event)
    if event["event_sigil"] != content_sigil(_without(event, "event_sigil")):
        _fail("Artifact Storage Journal Event self-Sigil mismatch")
    revisions = event["entity_revisions"]
    keys = [(item["entity_type"], item["entity_id"]) for item in revisions]
    if len(set(keys)) != len(keys):
        _fail("Artifact Storage Journal Event entity revisions must be unique")


def load_artifact_storage_journal_event_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    event = _load_strict_object(raw, "Artifact Storage Journal Event")
    validate_artifact_storage_journal_event_v1(event)
    return event


def validate_artifact_storage_journal_prefix_v1(events: list[dict[str, Any]]) -> None:
    """Validate a supplied contiguous Storage Event prefix without replaying it."""
    if not events:
        _fail("Artifact Storage Journal prefix must contain an initial Event")
    previous: dict[str, Any] | None = None
    event_ids: set[str] = set()
    for expected_sequence, event in enumerate(events, start=1):
        validate_artifact_storage_journal_event_v1(event)
        if event["event_id"] in event_ids:
            _fail("Artifact Storage Journal prefix has duplicate Event identity")
        event_ids.add(event["event_id"])
        if expected_sequence == 1 and event["event_type"] != "storage.initialized":
            _fail("Artifact Storage Journal prefix does not start with storage.initialized")
        if expected_sequence == 1 and event["epoch"] != 1:
            _fail("Artifact Storage Journal initial Event must use epoch one")
        if event["sequence"] != expected_sequence:
            _fail("Artifact Storage Journal prefix sequence is not contiguous")
        if previous is not None:
            if event["journal_id"] != previous["journal_id"]:
                _fail("Artifact Storage Journal prefix changes Journal ID")
            if event["previous_event_sigil"] != previous["event_sigil"]:
                _fail("Artifact Storage Journal prefix chain Sigil mismatch")
            if _parse_time(event["recorded_at"]) < _parse_time(previous["recorded_at"]):
                _fail("Artifact Storage Journal prefix recorded time regresses")
            if event["epoch"] < previous["epoch"]:
                _fail("Artifact Storage Journal prefix epoch regresses")
        previous = event


def validate_artifact_storage_journal_head_v1(head: dict[str, Any]) -> None:
    """Validate the local empty/non-empty Head matrix, never its durable bytes."""
    validate_instance("artifact-storage-journal-head-1.0.json", head)
    _check_nfc_and_numbers(head)
    empty = head["event_count"] == 0
    if empty:
        if (
            head["last_sequence"] != 0
            or head["committed_byte_length"] != 0
            or head["last_event_sigil"] is not None
            or head["state_sigil"] is not None
        ):
            _fail("Artifact Storage empty Journal Head has terminal fields")
    elif (
        head["event_count"] != head["last_sequence"]
        or head["last_event_sigil"] is None
        or head["state_sigil"] is None
    ):
        _fail("Artifact Storage non-empty Journal Head is inconsistent")


def load_artifact_storage_journal_head_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    head = _load_strict_object(raw, "Artifact Storage Journal Head")
    validate_artifact_storage_journal_head_v1(head)
    return head


def validate_artifact_storage_journal_head_supplied_event_v1(
    head: dict[str, Any], event: dict[str, Any], state_sigil: str,
) -> None:
    """Compare a Head with supplied final Event and State identity only.

    Callers remain responsible for authenticating journal frames and replaying
    state; successful comparison grants no append, resolver, or storage power.
    """
    validate_artifact_storage_journal_head_v1(head)
    validate_artifact_storage_journal_event_v1(event)
    if (
        head["event_count"] != event["sequence"]
        or head["last_sequence"] != event["sequence"]
        or head["journal_id"] != event["journal_id"]
        or head["last_event_sigil"] != event["event_sigil"]
        or head["state_sigil"] != state_sigil
    ):
        _fail("Artifact Storage Journal Head contradicts supplied final Event or State")


def validate_artifact_storage_journal_head_supplied_prefix_v1(
    head: dict[str, Any], events: list[dict[str, Any]], state_sigil: str,
) -> None:
    """Compare a Head with a complete caller-supplied contiguous Event prefix."""
    validate_artifact_storage_journal_prefix_v1(events)
    validate_artifact_storage_journal_head_supplied_event_v1(head, events[-1], state_sigil)


def replay_artifact_storage_initial_prefix_v1(
    events: list[dict[str, Any]], *, head: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild the exact empty Storage State from one initialization Event.

    This is the installed initial reducer only.  It checks the fixed twelve
    quota snapshots and creates no handles, blobs, or runtime authority.
    Later Storage Events remain unavailable until their reducers are installed.
    """
    if len(events) != 1:
        _fail("Artifact Storage initial replay requires exactly one Event")
    event = events[0]
    validate_artifact_storage_journal_prefix_v1([event])
    if event["event_type"] != "storage.initialized":
        _fail("Artifact Storage initial replay requires storage.initialized")
    payload = event["payload"]
    snapshots = payload["quota_snapshots"]
    expected_pairs = (
        ("JOURNAL", "JOURNAL_BYTE"), ("CONTROL_RECORD", "CONTROL_RECORD_BYTE"),
        ("STAGING", "BYTE"), ("STAGING", "OBJECT"), ("QUARANTINE", "BYTE"),
        ("QUARANTINE", "OBJECT"), ("COMMITTED", "BYTE"), ("COMMITTED", "OBJECT"),
        ("MATERIALIZATION", "BYTE"), ("MATERIALIZATION", "OBJECT"),
        ("STREAM", "STREAM"), ("INODE", "INODE"),
    )
    if [(item["quota_class"], item["dimension"]) for item in snapshots] != list(expected_pairs):
        _fail("Artifact Storage initialization quota snapshots are not the fixed twelve counters")
    if any(item["used"] or item["reserved"] or item["pressure_state"] != "CLEAR" for item in snapshots):
        _fail("Artifact Storage initialization quota snapshots must be unspent and clear")
    effects = event["quota_effects"]
    if effects != [{"kind": "INITIALIZE", "snapshot": item} for item in snapshots]:
        _fail("Artifact Storage initialization quota effects disagree with snapshots")
    if payload["tail_recovery"] is not None:
        _fail("Artifact Storage initial replay does not install tail recovery")
    backend = payload["backend"]
    state: dict[str, Any] = {
        "schema_version": "artifact-storage-state/1.0", "journal_id": event["journal_id"],
        "storage_format_version": payload["storage_format_version"], "project_id": payload["project_id"],
        "backend_profile_id": backend["record_id"], "backend_profile_sigil": backend["record_sigil"],
        "conformance_profile_id": payload["conformance_profile_id"],
        "conformance_suite_sigil": payload["conformance_suite_sigil"],
        "store_status": "INITIALIZING", "active_recovery_id": None, "recovery_origin_status": None,
        "clock_status": "TRUSTED", "clock_anchor": payload["clock"], "current_epoch": event["epoch"],
        "applied_event_count": 1, "last_event_sigil": event["event_sigil"],
        "recoveries": [], "blobs": [], "replicas": [], "transfer_requests": [], "transfer_attempts": [],
        "materializations": [], "quarantines": [], "provenance": [], "provenance_policies": [],
        "retention_policies": [], "holds": [], "reference_sets": [], "legacy_v1_protections": [],
        "gc_plans": [], "canonical_reference_intents": [], "dispositions": [],
        "quota_reservations": [], "open_intents": [], "incidents": [],
        "availability_counters": {"available_blobs": 0, "degraded_blobs": 0, "unavailable_blobs": 0, "incident_blobs": 0},
        "quota_counters": snapshots, "state_sigil": "",
    }
    state["state_sigil"] = content_sigil(_without(state, "state_sigil"))
    validate_artifact_storage_state_v1(state)
    if head is not None:
        validate_artifact_storage_journal_head_supplied_event_v1(head, event, state["state_sigil"])
    return state


def _reduce_artifact_storage_activation_v1(
    state: dict[str, Any], event: dict[str, Any],
) -> dict[str, Any]:
    """Apply the empty-protection activation branch after initialization."""
    if state["store_status"] != "INITIALIZING" or event["event_type"] != "storage.activation_completed":
        _fail("Artifact Storage activation reducer has an invalid source state or Event")
    if (
        event["journal_id"] != state["journal_id"]
        or event["epoch"] != state["current_epoch"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
    ):
        _fail("Artifact Storage activation Event disagrees with prior State")
    expected_revisions = [{
        "entity_type": "STORE", "entity_id": "STORE", "previous_revision": 1, "next_revision": 2,
    }]
    if event["entity_revisions"] != expected_revisions:
        _fail("Artifact Storage activation Event has invalid Store revision")
    payload = event["payload"]
    protection_ids = [item["protection_id"] for item in state["legacy_v1_protections"]]
    if payload["legacy_protection_ids"] != sorted(protection_ids):
        _fail("Artifact Storage activation protections disagree with State")
    if any(item["state"] != "PROTECTED" for item in state["legacy_v1_protections"]):
        _fail("Artifact Storage activation cannot proceed with failed legacy protection")
    if _parse_time(payload["clock"]["utc"]) < _parse_time(state["clock_anchor"]["utc"]):
        _fail("Artifact Storage activation clock regresses")
    reduced = _without(state, "state_sigil")
    reduced.update({
        "store_status": "ACTIVE", "clock_anchor": payload["clock"],
        "applied_event_count": event["sequence"], "last_event_sigil": event["event_sigil"],
    })
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _reduce_artifact_storage_clock_gate_v1(
    state: dict[str, Any], event: dict[str, Any], *, restoring: bool,
) -> dict[str, Any]:
    """Apply the action-free Storage clock gate for an otherwise empty State."""
    required_type = "storage.clock_restored" if restoring else "storage.clock_uncertain"
    if event["event_type"] != required_type or state["store_status"] != "ACTIVE":
        _fail("Artifact Storage clock reducer has an invalid source state or Event")
    if (
        event["journal_id"] != state["journal_id"]
        or event["epoch"] != state["current_epoch"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
        or event["entity_revisions"] != [{
            "entity_type": "STORE", "entity_id": "STORE",
            "previous_revision": event["sequence"] - 1, "next_revision": event["sequence"],
        }]
    ):
        _fail("Artifact Storage clock Event disagrees with prior State")
    payload = event["payload"]
    if state["quota_reservations"] or state["open_intents"]:
        _fail("Artifact Storage clock reducer requires no outstanding timed authority")
    if restoring:
        if state["clock_status"] != "UNCERTAIN" or payload["previous_observation_sigil"] != state["clock_anchor"]["observation_sigil"]:
            _fail("Artifact Storage clock restoration disagrees with uncertain State")
        clock = payload["new_clock"]
        if event["observed_at"] != clock["utc"]:
            _fail("Artifact Storage clock restoration observed_at disagrees with new clock")
    else:
        if state["clock_status"] != "TRUSTED" or payload["previous_clock"] != state["clock_anchor"]:
            _fail("Artifact Storage clock uncertainty disagrees with trusted State")
        if event["observed_at"] != payload["detected_clock"]["utc"]:
            _fail("Artifact Storage clock uncertainty observed_at disagrees with detected clock")
        clock = payload["detected_clock"]
    if _parse_time(clock["utc"]) < _parse_time(state["clock_anchor"]["utc"]):
        _fail("Artifact Storage clock Event regresses trusted time")
    reduced = _without(state, "state_sigil")
    reduced.update({
        "clock_status": "TRUSTED" if restoring else "UNCERTAIN", "clock_anchor": clock,
        "applied_event_count": event["sequence"], "last_event_sigil": event["event_sigil"],
    })
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _reduce_artifact_storage_epoch_started_v1(
    state: dict[str, Any], event: dict[str, Any],
) -> dict[str, Any]:
    """Apply a coordinator restart, retaining any active Recovery identity."""
    if event["event_type"] != "storage.epoch_started" or state["store_status"] not in {
        "INITIALIZING", "ACTIVE", "RECOVERING"
    }:
        _fail("Artifact Storage epoch reducer has an invalid source state or Event")
    payload = event["payload"]
    recovering = state["store_status"] == "RECOVERING"
    active_recovery_id = state["active_recovery_id"]
    if (
        event["journal_id"] != state["journal_id"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
        or event["epoch"] != payload["next_epoch"]
        or payload["previous_epoch"] != state["current_epoch"]
        or payload["next_epoch"] != state["current_epoch"] + 1
        or (recovering and payload["active_recovery_id"] != active_recovery_id)
        or (not recovering and payload["active_recovery_id"] is not None)
        or (not recovering and payload["tail_recovery"] is not None)
        or event["entity_revisions"] != [{
            "entity_type": "STORE", "entity_id": "STORE",
            "previous_revision": event["sequence"] - 1, "next_revision": event["sequence"],
        }]
    ):
        _fail("Artifact Storage epoch Event disagrees with prior State")
    if event["observed_at"] != payload["clock"]["utc"]:
        _fail("Artifact Storage epoch observed_at disagrees with clock")
    if _parse_time(payload["clock"]["utc"]) < _parse_time(state["clock_anchor"]["utc"]):
        _fail("Artifact Storage epoch clock regresses")
    reduced = _without(state, "state_sigil")
    reduced.update({
        "current_epoch": payload["next_epoch"], "clock_anchor": payload["clock"],
        "applied_event_count": event["sequence"], "last_event_sigil": event["event_sigil"],
        "recoveries": [
            {**recovery, "epoch_ids": [*recovery["epoch_ids"], payload["next_epoch"]]}
            if recovery["recovery_id"] == active_recovery_id else recovery
            for recovery in state["recoveries"]
        ] if recovering else state["recoveries"],
    })
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _reduce_artifact_storage_recovery_started_v1(
    state: dict[str, Any], event: dict[str, Any]
) -> dict[str, Any]:
    """Enter a new Storage Recovery without inferring any open-intent result."""
    payload = event["payload"]
    if state["store_status"] not in {"INITIALIZING", "ACTIVE"}:
        _fail("Artifact Storage recovery start has an invalid source State")
    open_intent_ids = [item["intent_id"] for item in state["open_intents"]]
    if (
        event["event_type"] != "storage.recovery_started"
        or event["journal_id"] != state["journal_id"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
        or event["epoch"] != payload["next_epoch"]
        or payload["origin_status"] != state["store_status"]
        or payload["previous_epoch"] != state["current_epoch"]
        or payload["next_epoch"] != state["current_epoch"] + 1
        or payload["open_intent_ids"] != open_intent_ids
        or event["observed_at"] != payload["clock"]["utc"]
        or _parse_time(payload["clock"]["utc"]) < _parse_time(state["clock_anchor"]["utc"])
        or event["entity_revisions"] != [{
            "entity_type": "STORE", "entity_id": "STORE",
            "previous_revision": event["sequence"] - 1,
            "next_revision": event["sequence"],
        }]
        or event["quota_effects"]
    ):
        _fail("Artifact Storage recovery start Event disagrees with prior State")
    reduced = _without(state, "state_sigil")
    reduced.update({
        "store_status": "RECOVERING",
        "active_recovery_id": payload["recovery_id"],
        "recovery_origin_status": state["store_status"],
        "clock_anchor": payload["clock"],
        "current_epoch": payload["next_epoch"],
        "applied_event_count": event["sequence"],
        "last_event_sigil": event["event_sigil"],
        "recoveries": [*state["recoveries"], {
            "recovery_id": payload["recovery_id"],
            "origin_status": state["store_status"],
            "state": "ACTIVE",
            "started_event_sigil": event["event_sigil"],
            "epoch_ids": [payload["next_epoch"]],
            "tail_recovery_evidence_record_sigils": [],
            "completed_event_sigil": None,
            "resume_status": None,
        }],
    })
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _reduce_artifact_storage_recovery_completed_v1(
    state: dict[str, Any], event: dict[str, Any]
) -> dict[str, Any]:
    """Return Storage to its frozen origin after every open intent is resolved."""
    payload = event["payload"]
    active_id = state["active_recovery_id"]
    if active_id is None:
        _fail("Artifact Storage recovery completion requires an active Recovery")
    recovery = next(item for item in state["recoveries"] if item["recovery_id"] == active_id)
    remaining_intents = [item["intent_id"] for item in state["open_intents"]]
    if (
        event["event_type"] != "storage.recovery_completed"
        or state["store_status"] != "RECOVERING"
        or recovery["state"] != "ACTIVE"
        or event["journal_id"] != state["journal_id"]
        or event["epoch"] != state["current_epoch"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
        or payload["recovery_id"] != active_id
        or payload["epoch"] != state["current_epoch"]
        or payload["resume_status"] != state["recovery_origin_status"]
        or remaining_intents
        or payload["resolved_intent_ids"] != sorted(payload["resolved_intent_ids"])
        or payload["evidence_sigils"] != sorted(payload["evidence_sigils"])
        or event["observed_at"] != payload["clock"]["utc"]
        or _parse_time(payload["clock"]["utc"]) < _parse_time(state["clock_anchor"]["utc"])
        or event["entity_revisions"] != [{
            "entity_type": "STORE", "entity_id": "STORE",
            "previous_revision": event["sequence"] - 1,
            "next_revision": event["sequence"],
        }]
        or event["quota_effects"]
    ):
        _fail("Artifact Storage recovery completion Event disagrees with Recovery State")
    origin = state["recovery_origin_status"]
    assert origin is not None
    reduced = _without(state, "state_sigil")
    reduced.update({
        "store_status": origin,
        "active_recovery_id": None,
        "recovery_origin_status": None,
        "clock_anchor": payload["clock"],
        "applied_event_count": event["sequence"],
        "last_event_sigil": event["event_sigil"],
        "recoveries": [
            {
                **item,
                "state": "COMPLETED",
                "completed_event_sigil": event["event_sigil"],
                "resume_status": origin,
            }
            if item["recovery_id"] == active_id else item
            for item in state["recoveries"]
        ],
    })
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _reduce_artifact_storage_message_rejected_v1(
    state: dict[str, Any], event: dict[str, Any],
) -> dict[str, Any]:
    """Replay a bounded rejected message without changing Storage objects."""
    if event["event_type"] != "storage.message_rejected":
        _fail("Artifact Storage message rejection reducer has the wrong Event")
    if (
        event["journal_id"] != state["journal_id"]
        or event["epoch"] != state["current_epoch"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
        or event["entity_revisions"]
        or event["quota_effects"]
        or event["observed_at"] is not None
        or event["causation_event_id"] is not None
        or event["idempotency_key_sigil"] is not None
    ):
        _fail("Artifact Storage message rejection Event disagrees with prior State")
    reduced = _without(state, "state_sigil")
    reduced.update({"applied_event_count": event["sequence"], "last_event_sigil": event["event_sigil"]})
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _reduce_artifact_storage_legacy_protection_failed_v1(
    state: dict[str, Any], event: dict[str, Any],
) -> dict[str, Any]:
    """Retain one failed v1 compatibility protection during initialization.

    A failed historical-artifact copy is durable negative evidence.  It never
    activates the store and cannot be overwritten by a later success record.
    """
    payload = event["payload"]
    if state["store_status"] != "INITIALIZING" or event["event_type"] != "legacy_v1.protection_failed":
        _fail("Artifact Storage legacy protection failure has an invalid source State or Event")
    existing = [
        item for item in state["legacy_v1_protections"]
        if item["protection_id"] == payload["protection_id"]
        or item["artifact_id"] == payload["artifact_id"]
    ]
    expected_revisions = [{
        "entity_type": "LEGACY_PROTECTION", "entity_id": payload["protection_id"],
        "previous_revision": None, "next_revision": 1,
    }]
    reason = payload["reason"]
    if (
        event["journal_id"] != state["journal_id"]
        or event["epoch"] != state["current_epoch"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
        or event["entity_revisions"] != expected_revisions
        or event["quota_effects"]
        or event["observed_at"] is not None
        or event["causation_event_id"] is not None
        or event["idempotency_key_sigil"] is not None
        or existing
        or reason["evidence_sigils"] != sorted(set(reason["evidence_sigils"]))
    ):
        _fail("Artifact Storage legacy protection failure Event disagrees with prior State")
    reduced = _without(state, "state_sigil")
    reduced.update({
        "legacy_v1_protections": [
            *state["legacy_v1_protections"],
            {
                "protection_id": payload["protection_id"],
                "artifact_id": payload["artifact_id"],
                "state": "FAILED", "record": None,
                "receipt_sigil": payload["receipt_sigil"], "reason": reason,
                "revision": 1, "last_event_sigil": event["event_sigil"],
            },
        ],
        "applied_event_count": event["sequence"], "last_event_sigil": event["event_sigil"],
    })
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _reduce_artifact_storage_reference_set_registered_v1(
    state: dict[str, Any], event: dict[str, Any], reference_set: dict[str, Any]
) -> dict[str, Any]:
    """Project one immutable Reference Set after its exact registration Event.

    The caller supplies the durable record so this reducer can close the
    Event-to-record relation without claiming source validation, graph closure,
    Journal append, or Storage authority.
    """
    validate_artifact_storage_reference_set_v1(reference_set)
    payload = event["payload"]
    if state["store_status"] != "ACTIVE":
        _fail("Artifact Storage Reference Set registration requires an active Store")
    if any(
        item["reference_set_id"] == reference_set["reference_set_id"]
        for item in state["reference_sets"]
    ):
        _fail("Artifact Storage Reference Set registration duplicates a State projection")
    expected_revisions = [{
        "entity_type": "REFERENCE_SET",
        "entity_id": reference_set["reference_set_id"],
        "previous_revision": None,
        "next_revision": 1,
    }]
    if (
        event["event_type"] != "reference_set.registered"
        or event["journal_id"] != state["journal_id"]
        or event["epoch"] != state["current_epoch"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
        or event["entity_revisions"] != expected_revisions
        or event["quota_effects"]
        or event["observed_at"] is not None
        or event["causation_event_id"] is not None
        or event["idempotency_key_sigil"] is not None
        or event["event_id"] != reference_set["registration_event_id"]
        or event["recorded_at"] != reference_set["created_at"]
        or payload["reference_set_id"] != reference_set["reference_set_id"]
        or payload["reference_set_sigil"] != reference_set["reference_set_sigil"]
        or payload["source_identity"] != reference_set["source"]["identity"]
        or payload["source_sigil"] != reference_set["source"]["sigil"]
    ):
        _fail("Artifact Storage Reference Set registration Event disagrees with record")
    reduced = _without(state, "state_sigil")
    reduced.update({
        "reference_sets": sorted(
            [
                *state["reference_sets"],
                {
                    "reference_set_id": reference_set["reference_set_id"],
                    "reference_set_sigil": reference_set["reference_set_sigil"],
                    "source_identity": reference_set["source"]["identity"],
                    "revision": 1,
                    "last_event_sigil": event["event_sigil"],
                },
            ],
            key=lambda item: item["reference_set_id"].encode("ascii"),
        ),
        "applied_event_count": event["sequence"],
        "last_event_sigil": event["event_sigil"],
    })
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _reduce_artifact_storage_provenance_policy_registered_v1(
    state: dict[str, Any], event: dict[str, Any], policy: dict[str, Any],
) -> dict[str, Any]:
    """Project one immutable Provenance Policy after exact registration.

    This closes only the Event-to-record and State-projection relations.  In
    particular, it does not resolve the policy's authorization or use the
    policy to admit a Transfer.
    """
    validate_artifact_provenance_policy_v1(policy)
    payload = event["payload"]
    if state["store_status"] != "ACTIVE":
        _fail("Artifact Storage Provenance Policy registration requires an active Store")
    if policy["scope"]["project_id"] != state["project_id"]:
        _fail("Artifact Storage Provenance Policy scope disagrees with State project")
    if any(
        item["provenance_policy_id"] == policy["provenance_policy_id"]
        for item in state["provenance_policies"]
    ):
        _fail("Artifact Storage Provenance Policy registration duplicates a State projection")
    expected_revisions = [{
        "entity_type": "PROVENANCE_POLICY",
        "entity_id": policy["provenance_policy_id"],
        "previous_revision": None,
        "next_revision": 1,
    }]
    expected_ref = {
        "schema_version": "artifact-provenance-policy/1.0",
        "record_id": policy["provenance_policy_id"],
        "record_sigil": policy["record_sigil"],
    }
    if (
        event["event_type"] != "provenance.policy_registered"
        or event["journal_id"] != state["journal_id"]
        or event["epoch"] != state["current_epoch"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
        or event["entity_revisions"] != expected_revisions
        or event["quota_effects"]
        or event["observed_at"] is not None
        or event["causation_event_id"] is not None
        or event["idempotency_key_sigil"] is not None
        or event["recorded_at"] != policy["registered_at"]
        or payload["provenance_policy"] != expected_ref
    ):
        _fail("Artifact Storage Provenance Policy registration Event disagrees with record")
    reduced = _without(state, "state_sigil")
    reduced.update({
        "provenance_policies": sorted(
            [
                *state["provenance_policies"],
                {
                    "provenance_policy_id": policy["provenance_policy_id"],
                    "record_sigil": policy["record_sigil"],
                    "revision": 1,
                    "last_event_sigil": event["event_sigil"],
                },
            ],
            key=lambda item: item["provenance_policy_id"].encode("ascii"),
        ),
        "applied_event_count": event["sequence"],
        "last_event_sigil": event["event_sigil"],
    })
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _reduce_artifact_storage_retention_policy_registered_v1(
    state: dict[str, Any], event: dict[str, Any], policy: dict[str, Any],
) -> dict[str, Any]:
    """Project an exact active-Store PROJECT retention-policy registration.

    This is deliberately narrower than policy applicability: it accepts only a
    PROJECT scope which is locally closed against this Storage State.  BLOB and
    Reference Set scopes need their exact projected objects, PROGRAM needs an
    external Program-to-Project resolver, and INITIALIZING requires the two
    RFC-fixed policies.  Those branches remain unavailable rather than
    treating a self-Sigiled policy as authorization.
    """
    validate_artifact_retention_policy_v1(policy)
    payload = event["payload"]
    if state["store_status"] != "ACTIVE":
        _fail("Artifact Storage Retention Policy registration requires an active Store")
    if (
        policy["scope"].get("kind") != "PROJECT"
        or policy["scope"].get("project_id") != state["project_id"]
    ):
        _fail("Artifact Storage Retention Policy scope is not locally closed to State project")
    if any(item["policy_id"] == policy["policy_id"] for item in state["retention_policies"]):
        _fail("Artifact Storage Retention Policy registration duplicates a State projection")
    expected_revisions = [{
        "entity_type": "RETENTION_POLICY",
        "entity_id": policy["policy_id"],
        "previous_revision": None,
        "next_revision": 1,
    }]
    expected_ref = {
        "schema_version": "artifact-retention-policy/1.0",
        "record_id": policy["policy_id"],
        "record_sigil": policy["record_sigil"],
    }
    if (
        event["event_type"] != "retention.policy_registered"
        or event["journal_id"] != state["journal_id"]
        or event["epoch"] != state["current_epoch"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
        or event["entity_revisions"] != expected_revisions
        or event["quota_effects"]
        or event["observed_at"] is not None
        or event["causation_event_id"] is not None
        or event["idempotency_key_sigil"] is not None
        or event["recorded_at"] != policy["registered_at"]
        or payload["policy"] != expected_ref
    ):
        _fail("Artifact Storage Retention Policy registration Event disagrees with record")
    reduced = _without(state, "state_sigil")
    reduced.update({
        "retention_policies": sorted(
            [
                *state["retention_policies"],
                {
                    "policy_id": policy["policy_id"],
                    "record_sigil": policy["record_sigil"],
                    "revision": 1,
                    "last_event_sigil": event["event_sigil"],
                },
            ],
            key=lambda item: item["policy_id"].encode("ascii"),
        ),
        "applied_event_count": event["sequence"],
        "last_event_sigil": event["event_sigil"],
    })
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _quota_counter_updates_for_claims_v1(
    counters: list[dict[str, Any]], claims: list[dict[str, Any]], *, reserve: bool,
) -> list[dict[str, Any]]:
    """Apply one checked Reservation claim vector to the twelve counters."""
    by_class = {claim["quota_class"]: claim for claim in claims}
    dimensions = {
        ("JOURNAL", "JOURNAL_BYTE"): "journal_bytes",
        ("CONTROL_RECORD", "CONTROL_RECORD_BYTE"): "control_record_bytes",
        ("STAGING", "BYTE"): "byte_count",
        ("STAGING", "OBJECT"): "object_count",
        ("QUARANTINE", "BYTE"): "byte_count",
        ("QUARANTINE", "OBJECT"): "object_count",
        ("COMMITTED", "BYTE"): "byte_count",
        ("COMMITTED", "OBJECT"): "object_count",
        ("MATERIALIZATION", "BYTE"): "byte_count",
        ("MATERIALIZATION", "OBJECT"): "object_count",
        ("STREAM", "STREAM"): "stream_count",
        ("INODE", "INODE"): "inode_count",
    }
    updated: list[dict[str, Any]] = []
    for counter in counters:
        amount = by_class.get(counter["quota_class"], {}).get(
            dimensions[(counter["quota_class"], counter["dimension"])], 0
        )
        next_reserved = counter["reserved"] + amount if reserve else counter["reserved"] - amount
        if next_reserved < 0 or counter["used"] + next_reserved > counter["limit"]:
            _fail("Artifact Storage Reservation exceeds a quota counter")
        updated.append({**counter, "reserved": next_reserved})
    return updated


def _quota_counter_settlement_v1(
    counters: list[dict[str, Any]], original: list[dict[str, Any]],
    consumed: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Settle a reservation: release all reserve, retain consumed usage."""
    dimensions = {
        ("JOURNAL", "JOURNAL_BYTE"): "journal_bytes",
        ("CONTROL_RECORD", "CONTROL_RECORD_BYTE"): "control_record_bytes",
        ("STAGING", "BYTE"): "byte_count", ("STAGING", "OBJECT"): "object_count",
        ("QUARANTINE", "BYTE"): "byte_count", ("QUARANTINE", "OBJECT"): "object_count",
        ("COMMITTED", "BYTE"): "byte_count", ("COMMITTED", "OBJECT"): "object_count",
        ("MATERIALIZATION", "BYTE"): "byte_count", ("MATERIALIZATION", "OBJECT"): "object_count",
        ("STREAM", "STREAM"): "stream_count", ("INODE", "INODE"): "inode_count",
    }
    original_by_class = {claim["quota_class"]: claim for claim in original}
    consumed_by_class = {claim["quota_class"]: claim for claim in consumed}
    updated: list[dict[str, Any]] = []
    for counter in counters:
        quota_class = counter["quota_class"]
        field = dimensions[(quota_class, counter["dimension"])]
        reserved_amount = original_by_class.get(quota_class, {}).get(field, 0)
        consumed_amount = consumed_by_class.get(quota_class, {}).get(field, 0)
        next_reserved = counter["reserved"] - reserved_amount
        next_used = counter["used"] + consumed_amount
        if next_reserved < 0 or next_used + next_reserved > counter["limit"]:
            _fail("Artifact Storage Reservation settlement exceeds a quota counter")
        updated.append({**counter, "used": next_used, "reserved": next_reserved})
    return updated


def _canonical_reference_blob_closure_v1(
    roots: list[dict[str, Any]], reference_sets: list[dict[str, Any]],
    state: dict[str, Any],
) -> list[str]:
    """Recompute the bounded typed Reference Set closure for an intent pin."""
    records = {record["reference_set_id"]: record for record in reference_sets}
    if len(records) != len(reference_sets):
        _fail("Canonical Reference closure has duplicate supplied Reference Sets")
    replica_blobs = {
        wrapper["record"]["replica_id"]: wrapper["record"]["blob_sigil"]
        for wrapper in state["replicas"]
    }
    storage_blobs = {
        wrapper["record"]["blob_sigil"] for wrapper in state["blobs"]
    }
    state_sets = {
        projection["reference_set_id"]: projection["reference_set_sigil"]
        for projection in state["reference_sets"]
    }
    relationship_matrix = {
        "BUNDLE_RETAINS_MEMBER": ("BLOB_MANIFEST", {"BLOB"}),
        "CANONICAL_BINDS_BLOB": ("CANONICAL_OBJECT", {"BLOB"}),
        "CANONICAL_RETAINS_OBJECT": (
            "CANONICAL_OBJECT", {"CANONICAL_OBJECT", "OPERATIONAL_CONTROL_RECORD", "REFERENCE_SET"}
        ),
        "CONTROL_RETAINS_BLOB": ("OPERATIONAL_CONTROL_RECORD", {"BLOB"}),
        "CONTROL_RETAINS_CONTROL": ("OPERATIONAL_CONTROL_RECORD", {"OPERATIONAL_CONTROL_RECORD"}),
        "HOLD_PROTECTS_BLOB": ("OPERATIONAL_CONTROL_RECORD", {"BLOB"}),
        "JOB_REQUIRES_BLOB": ("OPERATIONAL_CONTROL_RECORD", {"BLOB"}),
        "PATCH_RETAINS_BASE": ("BLOB_MANIFEST", {"BLOB"}),
        "PATCH_RETAINS_POSTIMAGE": ("BLOB_MANIFEST", {"BLOB"}),
        "REFERENCE_SET_RETAINS_SET": ("OPERATIONAL_CONTROL_RECORD", {"REFERENCE_SET"}),
        "TRANSFER_PINS_REPLICA": ("OPERATIONAL_CONTROL_RECORD", {"REPLICA"}),
    }
    pending = [("REFERENCE_SET", item["reference_set_id"], item["reference_set_sigil"], 0)
               for item in roots]
    seen: set[tuple[str, str, str]] = set()
    edge_keys: set[tuple[str, str, str, str]] = set()
    blobs: set[str] = set()
    while pending:
        kind, identity, sigil, depth = pending.pop()
        node = (kind, identity, sigil)
        if node in seen:
            continue
        if len(seen) >= 4096 or depth >= 4096:
            _fail("Canonical Reference closure exceeds its traversal bounds")
        seen.add(node)
        if kind != "REFERENCE_SET":
            continue
        record = records.get(identity)
        if (
            record is None
            or record["reference_set_sigil"] != sigil
            or state_sets.get(identity) != sigil
        ):
            _fail("Canonical Reference closure lacks an exact Reference Set")
        for edge in record["edges"]:
            edge_key = (
                edge["relationship"], edge["target_kind"], edge["target_identity"],
                edge["target_sigil"],
            )
            if edge_key in edge_keys:
                continue
            if len(edge_keys) >= 4096:
                _fail("Canonical Reference closure exceeds its edge bound")
            edge_keys.add(edge_key)
            target_kind = edge["target_kind"]
            target_id = edge["target_identity"]
            target_sigil = edge["target_sigil"]
            expected_source, expected_targets = relationship_matrix[edge["relationship"]]
            if record["source"]["kind"] != expected_source or target_kind not in expected_targets:
                _fail("Canonical Reference closure has an illegal typed edge")
            if (
                edge["relationship"] == "REFERENCE_SET_RETAINS_SET"
                and record["source"]["schema_version"]
                != "artifact-storage-reference-set/1.0"
            ):
                _fail("Canonical Reference closure Reference Set edge has an invalid source")
            if target_kind == "BLOB":
                if target_id != target_sigil or target_sigil not in storage_blobs:
                    _fail("Canonical Reference Blob edge identity disagrees with Sigil")
                blobs.add(target_sigil)
            elif target_kind == "REPLICA":
                blob_sigil = replica_blobs.get(target_id)
                if blob_sigil is None or target_sigil != next(
                    (wrapper["record"]["record_sigil"] for wrapper in state["replicas"]
                     if wrapper["record"]["replica_id"] == target_id), None
                ):
                    _fail("Canonical Reference closure lacks an exact Replica")
                blobs.add(blob_sigil)
            elif target_kind == "REFERENCE_SET":
                pending.append((target_kind, target_id, target_sigil, depth + 1))
            else:
                _fail("Canonical Reference closure has an unresolved typed target")
            if len(blobs) > 4096:
                _fail("Canonical Reference closure exceeds its Blob bound")
    return sorted(blobs)


def _validate_canonical_lifecycle_reservation_v1(reservation: dict[str, Any]) -> None:
    """Close the capacity arithmetic required before a canonical pin is durable."""
    plan = reservation["capacity_plan"]
    if plan["allowed_event_types"] != [
        "canonical_reference.committed", "canonical_reference.released"
    ]:
        _fail("Canonical Reference lifecycle Reservation has an invalid terminal plan")
    required_journal = plan["max_event_frame_count"] * plan["max_event_frame_bytes"]
    required_control = (
        plan["max_control_record_count"] * plan["max_control_record_bytes"]
        + plan["max_recovery_evidence_count"] * plan["max_recovery_evidence_bytes"]
    )
    if required_journal > 9223372036854775807 or required_control > 9223372036854775807:
        _fail("Canonical Reference lifecycle Reservation capacity arithmetic overflows")
    claims = {claim["quota_class"]: claim for claim in reservation["claims"]}
    if (
        claims.get("JOURNAL", {}).get("journal_bytes", 0) < required_journal
        or claims.get("CONTROL_RECORD", {}).get("control_record_bytes", 0) < required_control
    ):
        _fail("Canonical Reference lifecycle Reservation lacks terminal capacity")


def _reduce_artifact_storage_canonical_reference_intent_v1(
    state: dict[str, Any], event: dict[str, Any], intent: dict[str, Any],
    reference_sets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Project a canonical-reference pin from exact supplied control records.

    This closes the immutable Storage portion of write-ahead intent admission,
    including the bounded Reference Set closure. Chronicle authority remains
    external and is deliberately not inferred here.
    """
    validate_artifact_storage_reference_intent_v1(intent)
    for reference_set in reference_sets:
        validate_artifact_storage_reference_set_v1(reference_set)
    payload = event["payload"]
    reservation = payload["lifecycle_reservation"]
    if state["store_status"] != "ACTIVE" or state["clock_status"] != "TRUSTED":
        _fail("Canonical Reference intent requires an active trusted Store")
    reference_pairs = {
        record["reference_set_id"]: record["reference_set_sigil"]
        for record in reference_sets
    }
    if len(reference_pairs) != len(reference_sets):
        _fail("Canonical Reference intent supplied Reference Sets have duplicate IDs")
    intent_set_pairs = [
        (reference["reference_set_id"], reference["reference_set_sigil"])
        for reference in intent["reference_sets"]
    ]
    if any(reference_pairs.get(identifier) != sigil for identifier, sigil in intent_set_pairs):
        _fail("Canonical Reference intent lacks a supplied immutable Reference Set")
    state_set_pairs = {
        projection["reference_set_id"]: projection["reference_set_sigil"]
        for projection in state["reference_sets"]
    }
    if any(state_set_pairs.get(identifier) != sigil for identifier, sigil in intent_set_pairs):
        _fail("Canonical Reference intent Reference Set is absent from Storage State")
    if any(
        item["reference_intent_id"] == intent["reference_intent_id"]
        for item in state["canonical_reference_intents"]
    ) or any(
        item["intent_id"] == intent["reference_intent_id"]
        for item in state["open_intents"]
    ) or any(
        item["reservation"]["reservation_id"] == reservation["reservation_id"]
        for item in state["quota_reservations"]
    ):
        _fail("Canonical Reference intent duplicates a Storage projection")
    _validate_quota_claim_array(reservation["claims"], "Canonical Reference Reservation claims")
    closure_blobs = _canonical_reference_blob_closure_v1(
        intent["reference_sets"], reference_sets, state
    )
    if (
        reservation["expires_at"] is not None
        or reservation["remaining_micros_at_creation"] is not None
        or reservation["created_clock"] != state["clock_anchor"]
    ):
        _fail("Canonical Reference lifecycle Reservation is not the fixed nonexpiring plan")
    _validate_canonical_lifecycle_reservation_v1(reservation)
    expected_revisions = [
        {"entity_type": "REFERENCE_INTENT", "entity_id": intent["reference_intent_id"],
         "previous_revision": None, "next_revision": 1},
        {"entity_type": "QUOTA", "entity_id": reservation["reservation_id"],
         "previous_revision": None, "next_revision": 1},
    ]
    expected_effect = {
        "kind": "RESERVE", "reservation": reservation,
        "owner_kind": "CANONICAL_REFERENCE", "owner_id": intent["reference_intent_id"],
        "purpose": "CANONICAL_PIN_LIFECYCLE",
    }
    expected_set_sigils = [sigil for _, sigil in intent_set_pairs]
    if (
        event["event_type"] != "canonical_reference.intent_recorded"
        or event["journal_id"] != state["journal_id"]
        or event["epoch"] != state["current_epoch"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
        or event["entity_revisions"] != expected_revisions
        or event["observed_at"] is not None
        or event["causation_event_id"] is not None
        or event["idempotency_key_sigil"] != intent["idempotency_key_sigil"]
        or event["quota_effects"] != [expected_effect]
        or payload["reference_intent"] != {
            "schema_version": "artifact-storage-reference-intent/1.0",
            "record_id": intent["reference_intent_id"], "record_sigil": intent["record_sigil"],
        }
        or payload["expected_chronicle_head"] != intent["expected_chronicle_head"]
        or intent["blob_sigils"] != closure_blobs
        or payload["blob_sigils"] != closure_blobs
        or payload["reference_set_sigils"] != expected_set_sigils
    ):
        _fail("Canonical Reference intent Event disagrees with immutable records")
    reduced = _without(state, "state_sigil")
    reduced.update({
        "canonical_reference_intents": sorted([
            *state["canonical_reference_intents"], {
                "reference_intent_id": intent["reference_intent_id"], "record_sigil": intent["record_sigil"],
                "state": "OPEN", "chronicle_commit": None, "release_kind": None,
                "release_authority_sigil": None, "release_reason": None, "revision": 1,
                "last_event_sigil": event["event_sigil"],
            },
        ], key=lambda item: item["reference_intent_id"].encode("ascii")),
        "quota_reservations": sorted([
            *state["quota_reservations"], {
                "reservation": reservation, "owner_kind": "CANONICAL_REFERENCE",
                "owner_id": intent["reference_intent_id"], "purpose": "CANONICAL_PIN_LIFECYCLE",
                "state": "ACTIVE", "consumed_claims": [], "released_claims": [],
                "remaining_claims": reservation["claims"], "retained_for_event_types": [],
                "revision": 1, "last_event_sigil": event["event_sigil"],
            },
        ], key=lambda item: item["reservation"]["reservation_id"].encode("ascii")),
        "open_intents": sorted([
            *state["open_intents"], {
                "intent_kind": "CANONICAL_REFERENCE", "intent_id": intent["reference_intent_id"],
                "owner_id": intent["reference_intent_id"], "source_event": {
                    "journal_id": event["journal_id"], "sequence": event["sequence"],
                    "event_id": event["event_id"], "event_sigil": event["event_sigil"],
                }, "intent_sigil": event["event_sigil"], "revision": 1,
                "last_event_sigil": event["event_sigil"], "authorization_expires_at": None,
                "expected_chronicle_head": intent["expected_chronicle_head"],
                "blob_sigils": intent["blob_sigils"], "reference_set_sigils": expected_set_sigils,
            },
        ], key=lambda item: (item["intent_kind"].encode("ascii"), item["intent_id"].encode("ascii"))),
        "quota_counters": _quota_counter_updates_for_claims_v1(
            state["quota_counters"], reservation["claims"], reserve=True
        ),
        "applied_event_count": event["sequence"], "last_event_sigil": event["event_sigil"],
    })
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _reduce_artifact_storage_canonical_reference_committed_v1(
    state: dict[str, Any], event: dict[str, Any], intent: dict[str, Any],
    chronicle_event: dict[str, Any],
) -> dict[str, Any]:
    """Close one OPEN canonical-reference pin from supplied Chronicle facts.

    This reducer closes the durable Storage projection and Reservation only.
    The caller is responsible for authoritative Chronicle replay and the
    event-family request resolver; this function never appends or authorizes a
    Chronicle Event.
    """
    projection = next(
        (item for item in state["canonical_reference_intents"]
         if item["reference_intent_id"] == intent["reference_intent_id"]),
        None,
    )
    reservation = next(
        (item for item in state["quota_reservations"]
         if item["owner_kind"] == "CANONICAL_REFERENCE"
         and item["owner_id"] == intent["reference_intent_id"]),
        None,
    )
    open_intent = next(
        (item for item in state["open_intents"]
         if item["intent_kind"] == "CANONICAL_REFERENCE"
         and item["intent_id"] == intent["reference_intent_id"]),
        None,
    )
    if (
        projection is None or projection["state"] != "OPEN"
        or projection["record_sigil"] != intent["record_sigil"]
        or reservation is None or reservation["state"] != "ACTIVE"
        or open_intent is None
    ):
        _fail("Canonical Reference commit requires one OPEN intent and active Reservation")
    commit = event["payload"]["chronicle_commit"]
    validate_canonical_reference_commit_supplied_facts_v1(intent, chronicle_event, commit)
    expected_revisions = [
        {"entity_type": "REFERENCE_INTENT", "entity_id": intent["reference_intent_id"],
         "previous_revision": 1, "next_revision": 2},
        {"entity_type": "QUOTA", "entity_id": reservation["reservation"]["reservation_id"],
         "previous_revision": 1, "next_revision": 2},
    ]
    effects = event["quota_effects"]
    if len(effects) != 1 or effects[0]["kind"] != "SETTLE":
        _fail("Canonical Reference commit requires one Reservation settlement")
    settlement = effects[0]
    if (
        event["event_type"] != "canonical_reference.committed"
        or event["journal_id"] != state["journal_id"]
        or event["epoch"] != state["current_epoch"]
        or event["sequence"] != state["applied_event_count"] + 1
        or event["previous_event_sigil"] != state["last_event_sigil"]
        or event["entity_revisions"] != expected_revisions
        or event["observed_at"] is not None
        or event["causation_event_id"] != open_intent["source_event"]["event_id"]
        or event["idempotency_key_sigil"] != intent["idempotency_key_sigil"]
        or event["payload"]["reference_intent_id"] != intent["reference_intent_id"]
        or settlement["reservation_id"] != reservation["reservation"]["reservation_id"]
        or settlement["state_after"] != "SETTLED"
        or settlement["remaining_claims"]
        or settlement["retained_for_event_types"]
        or settlement["usage_additions"] != settlement["consumed_claims"]
    ):
        _fail("Canonical Reference commit Event disagrees with OPEN pin")
    original = reservation["reservation"]["claims"]
    consumed_by_class = {claim["quota_class"]: claim for claim in settlement["consumed_claims"]}
    if consumed_by_class.get("JOURNAL", {}).get("journal_bytes", 0) <= 0:
        _fail("Canonical Reference commit must account for its Journal frame usage")
    reduced = _without(state, "state_sigil")
    reduced["canonical_reference_intents"] = [
        {
            **item, "state": "COMMITTED", "chronicle_commit": commit,
            "release_kind": None, "release_authority_sigil": None,
            "release_reason": None, "revision": 2,
            "last_event_sigil": event["event_sigil"],
        } if item["reference_intent_id"] == intent["reference_intent_id"] else item
        for item in state["canonical_reference_intents"]
    ]
    reduced["quota_reservations"] = [
        {
            **item, "state": "SETTLED", "consumed_claims": settlement["consumed_claims"],
            "released_claims": settlement["released_claims"], "remaining_claims": [],
            "retained_for_event_types": [], "revision": 2,
            "last_event_sigil": event["event_sigil"],
        } if item["reservation"]["reservation_id"] == reservation["reservation"]["reservation_id"] else item
        for item in state["quota_reservations"]
    ]
    reduced["open_intents"] = [
        item for item in state["open_intents"]
        if not (item["intent_kind"] == "CANONICAL_REFERENCE" and item["intent_id"] == intent["reference_intent_id"])
    ]
    reduced["quota_counters"] = _quota_counter_settlement_v1(
        state["quota_counters"], original, settlement["consumed_claims"]
    )
    reduced["applied_event_count"] = event["sequence"]
    reduced["last_event_sigil"] = event["event_sigil"]
    reduced["state_sigil"] = content_sigil(reduced)
    validate_artifact_storage_state_v1(reduced)
    return reduced


def _reduce_artifact_storage_canonical_reference_released_v1(
    state: dict[str, Any], event: dict[str, Any], intent: dict[str, Any],
) -> dict[str, Any]:
    """Reject untrusted abort facts pending an authoritative Chronicle resolver.

    A self-consistent supplied head and absence Sigil cannot prove the required
    negative fact: that the complete Chronicle suffix contains no Event bound
    to this immutable request.  Generic Storage replay has no Chronicle
    authority, therefore it must retain the OPEN pin rather than project a
    RELEASED state.  The local fact checker remains available for the future
    authoritative resolver boundary.
    """
    _fail(
        "Canonical Reference release replay requires authoritative Chronicle "
        "absence proof and remains fail-closed"
    )


def replay_artifact_storage_journal_prefix_v1(
    events: list[dict[str, Any]], *, head: dict[str, Any] | None = None,
    supplied_reference_sets: list[dict[str, Any]] | None = None,
    supplied_reference_intents: list[dict[str, Any]] | None = None,
    supplied_chronicle_events: list[dict[str, Any]] | None = None,
    supplied_provenance_policies: list[dict[str, Any]] | None = None,
    supplied_retention_policies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Replay installed Storage Journal reducers, failing closed for all others.

    This is deliberately a dispatcher over the installed reducer set rather
    than a catalog of fixed-length prefixes. It still rejects every Event type
    without a reducer and grants no append or Storage authority.
    """
    validate_artifact_storage_journal_prefix_v1(events)
    state = replay_artifact_storage_initial_prefix_v1([events[0]])
    for event in events[1:]:
        if event["event_type"] == "storage.activation_completed":
            state = _reduce_artifact_storage_activation_v1(state, event)
        elif event["event_type"] == "storage.epoch_started":
            state = _reduce_artifact_storage_epoch_started_v1(state, event)
        elif event["event_type"] == "storage.clock_uncertain":
            state = _reduce_artifact_storage_clock_gate_v1(state, event, restoring=False)
        elif event["event_type"] == "storage.clock_restored":
            state = _reduce_artifact_storage_clock_gate_v1(state, event, restoring=True)
        elif event["event_type"] == "storage.recovery_started":
            state = _reduce_artifact_storage_recovery_started_v1(state, event)
        elif event["event_type"] == "storage.recovery_completed":
            state = _reduce_artifact_storage_recovery_completed_v1(state, event)
        elif event["event_type"] == "storage.message_rejected":
            state = _reduce_artifact_storage_message_rejected_v1(state, event)
        elif event["event_type"] == "legacy_v1.protection_failed":
            state = _reduce_artifact_storage_legacy_protection_failed_v1(state, event)
        elif event["event_type"] == "provenance.policy_registered":
            if supplied_provenance_policies is None:
                _fail("Provenance Policy registration replay requires its supplied record")
            matches = [
                record
                for record in supplied_provenance_policies
                if record.get("provenance_policy_id")
                == event["payload"]["provenance_policy"]["record_id"]
            ]
            if len(matches) != 1:
                _fail("Provenance Policy registration replay requires exactly one supplied record")
            state = _reduce_artifact_storage_provenance_policy_registered_v1(
                state, event, matches[0]
            )
        elif event["event_type"] == "retention.policy_registered":
            if supplied_retention_policies is None:
                _fail("Retention Policy registration replay requires its supplied record")
            matches = [
                record
                for record in supplied_retention_policies
                if record.get("policy_id") == event["payload"]["policy"]["record_id"]
            ]
            if len(matches) != 1:
                _fail("Retention Policy registration replay requires exactly one supplied record")
            state = _reduce_artifact_storage_retention_policy_registered_v1(
                state, event, matches[0]
            )
        elif event["event_type"] == "reference_set.registered":
            if supplied_reference_sets is None:
                _fail("Reference Set registration replay requires its supplied record")
            matches = [
                record
                for record in supplied_reference_sets
                if record.get("reference_set_id") == event["payload"]["reference_set_id"]
            ]
            if len(matches) != 1:
                _fail("Reference Set registration replay requires exactly one supplied record")
            state = _reduce_artifact_storage_reference_set_registered_v1(
                state, event, matches[0]
            )
        elif event["event_type"] == "canonical_reference.intent_recorded":
            if supplied_reference_intents is None or supplied_reference_sets is None:
                _fail("Canonical Reference intent replay requires supplied control records")
            matches = [
                record for record in supplied_reference_intents
                if record.get("reference_intent_id") == event["payload"]["reference_intent"]["record_id"]
            ]
            if len(matches) != 1:
                _fail("Canonical Reference intent replay requires exactly one supplied record")
            state = _reduce_artifact_storage_canonical_reference_intent_v1(
                state, event, matches[0], supplied_reference_sets
            )
        elif event["event_type"] == "canonical_reference.committed":
            if supplied_reference_intents is None or supplied_chronicle_events is None:
                _fail("Canonical Reference commit replay requires supplied control and Chronicle records")
            intent_matches = [record for record in supplied_reference_intents if record.get("reference_intent_id") == event["payload"]["reference_intent_id"]]
            commit_matches = [record for record in supplied_chronicle_events if record.get("event_id") == event["payload"]["chronicle_commit"]["event_id"]]
            if len(intent_matches) != 1 or len(commit_matches) != 1:
                _fail("Canonical Reference commit replay requires exactly one supplied record")
            state = _reduce_artifact_storage_canonical_reference_committed_v1(
                state, event, intent_matches[0], commit_matches[0]
            )
        elif event["event_type"] == "canonical_reference.released":
            if supplied_reference_intents is None:
                _fail("Canonical Reference release replay requires its supplied control record")
            matches = [record for record in supplied_reference_intents if record.get("reference_intent_id") == event["payload"]["reference_intent_id"]]
            if len(matches) != 1:
                _fail("Canonical Reference release replay requires exactly one supplied record")
            state = _reduce_artifact_storage_canonical_reference_released_v1(state, event, matches[0])
        else:
            _fail("Artifact Storage Journal replay reducer is unavailable for this Event")
    if head is not None:
        validate_artifact_storage_journal_head_supplied_event_v1(
            head, events[-1], state["state_sigil"]
        )
    if supplied_provenance_policies is not None:
        validate_artifact_storage_state_supplied_provenance_policies_v1(
            state, policies=supplied_provenance_policies
        )
    if supplied_retention_policies is not None:
        validate_artifact_storage_state_supplied_retention_policies_v1(
            state, policies=supplied_retention_policies
        )
    return state


def _state_identity(value: dict[str, Any], collection: str) -> str | tuple[str, str]:
    if collection == "open_intents":
        return value["intent_kind"], value["intent_id"]
    if collection == "quota_reservations":
        return value["reservation"]["reservation_id"]
    if collection in {"blobs", "replicas", "transfer_attempts", "materializations"}:
        record = value["record"]
        return record[{"blobs": "blob_sigil", "replicas": "replica_id", "transfer_attempts": "transfer_attempt_id", "materializations": "materialization_id"}[collection]]
    identity_member = {
        "recoveries": "recovery_id", "transfer_requests": "transfer_id",
        "quarantines": "quarantine_id", "provenance": "provenance_id",
        "provenance_policies": "provenance_policy_id", "retention_policies": "policy_id",
        "holds": "hold_id", "reference_sets": "reference_set_id",
        "legacy_v1_protections": "protection_id", "gc_plans": "gc_plan_id",
        "canonical_reference_intents": "reference_intent_id", "dispositions": "disposition_id",
        "incidents": "incident_id",
    }[collection]
    return value[identity_member]


_STATE_IDENTITY_COLLECTIONS = (
    "recoveries", "blobs", "replicas", "transfer_requests", "transfer_attempts",
    "materializations", "quarantines", "provenance", "provenance_policies",
    "retention_policies", "holds", "reference_sets", "legacy_v1_protections",
    "gc_plans", "canonical_reference_intents", "dispositions", "quota_reservations",
    "open_intents", "incidents",
)

_STATE_WRAPPER_SCHEMAS = {
    "blobs": "artifact-blob-1.0.json",
    "replicas": "artifact-replica-1.0.json",
    "transfer_attempts": "artifact-transfer-attempt-1.0.json",
    "materializations": "artifact-materialization-1.0.json",
}

_QUOTA_CLAIM_FIELDS = (
    "byte_count", "object_count", "inode_count", "stream_count", "journal_bytes",
    "control_record_bytes",
)
_QUOTA_CLASS_ALLOWED_FIELDS = {
    "JOURNAL": {"journal_bytes"},
    "CONTROL_RECORD": {"control_record_bytes"},
    "STAGING": {"byte_count", "object_count"},
    "QUARANTINE": {"byte_count", "object_count"},
    "COMMITTED": {"byte_count", "object_count"},
    "MATERIALIZATION": {"byte_count", "object_count"},
    "STREAM": {"stream_count"},
    "INODE": {"inode_count"},
}


def _validate_quota_claim_array(claims: list[dict[str, Any]], label: str) -> None:
    classes = [claim["quota_class"] for claim in claims]
    if len(set(classes)) != len(classes):
        _fail(f"Artifact Storage {label} has duplicate quota classes")
    if classes != sorted(classes):
        _fail(f"Artifact Storage {label} is not quota-class sorted")
    for claim in claims:
        allowed = _QUOTA_CLASS_ALLOWED_FIELDS[claim["quota_class"]]
        if not any(claim[field] for field in allowed):
            _fail(f"Artifact Storage {label} has an empty quota claim")
        if any(claim[field] for field in set(_QUOTA_CLAIM_FIELDS) - allowed):
            _fail(f"Artifact Storage {label} has an illegal quota dimension")


def _identity_sort_key(value: str | tuple[str, str]) -> bytes | tuple[bytes, bytes]:
    if isinstance(value, tuple):
        return value[0].encode("ascii"), value[1].encode("ascii")
    return value.encode("ascii")


def validate_artifact_storage_state_v1(state: dict[str, Any]) -> None:
    """Validate a Storage State's local identity projection, never its replay."""
    validate_instance("artifact-storage-state-1.0.json", state)
    _check_nfc_and_numbers(state)
    if state["state_sigil"] != content_sigil(_without(state, "state_sigil")):
        _fail("Artifact Storage State self-Sigil mismatch")
    for collection in _STATE_IDENTITY_COLLECTIONS:
        identities = [_state_identity(value, collection) for value in state[collection]]
        if len(set(identities)) != len(identities):
            _fail(f"Artifact Storage State {collection} identities must be unique")
        if identities != sorted(identities, key=_identity_sort_key):
            _fail(f"Artifact Storage State {collection} is not identity sorted")
    recoveries = {recovery["recovery_id"]: recovery for recovery in state["recoveries"]}
    for recovery in recoveries.values():
        if recovery["epoch_ids"] != sorted(recovery["epoch_ids"]):
            _fail("Artifact Storage State Recovery epochs are not strictly increasing")
        if recovery["state"] == "COMPLETED" and recovery["resume_status"] != recovery["origin_status"]:
            _fail("Artifact Storage State completed Recovery resume status disagrees with origin")
    active_recoveries = [
        recovery for recovery in recoveries.values() if recovery["state"] == "ACTIVE"
    ]
    active_recovery = recoveries.get(state["active_recovery_id"])
    if state["store_status"] == "RECOVERING" and (
        active_recovery is None
        or active_recovery["state"] != "ACTIVE"
        or len(active_recoveries) != 1
        or active_recovery["origin_status"] != state["recovery_origin_status"]
        or active_recovery["epoch_ids"][-1] != state["current_epoch"]
    ):
        _fail("Artifact Storage State active Recovery disagrees with Store projection")
    if state["store_status"] != "RECOVERING" and any(
        active_recoveries
    ):
        _fail("Artifact Storage State nonrecovering Store retains an active Recovery")
    for collection, schema_name in _STATE_WRAPPER_SCHEMAS.items():
        for wrapper in state[collection]:
            record = wrapper["record"]
            validate_instance(schema_name, record)
            if record["record_sigil"] != content_sigil(_without(record, "record_sigil")):
                _fail(f"Artifact Storage State {collection} record self-Sigil mismatch")
            if collection == "replicas" and (
                record["object"]["blob_sigil"] != record["blob_sigil"]
                or record["object"]["size_bytes"] != record["size_bytes"]
                or record["backend"]["backend_id"] != record["object"]["backend_id"]
            ):
                _fail("Artifact Storage State Replica object disagrees with record")
    for quarantine in state["quarantines"]:
        if quarantine["record_sigil"] != content_sigil(_without(quarantine, "record_sigil")):
            _fail("Artifact Storage State Quarantine record self-Sigil mismatch")
    for protection in state["legacy_v1_protections"]:
        if protection["state"] != "PROTECTED":
            continue
        record = protection["record"]
        validate_artifact_storage_legacy_protection_v1(record)
        if (
            record["protection_id"] != protection["protection_id"]
            or record["artifact_id"] != protection["artifact_id"]
            or record["artifact_receipt_sigil"] != protection["receipt_sigil"]
        ):
            _fail("Artifact Storage State Legacy Protection disagrees with its record")
    for hold in state["holds"]:
        released = hold["state"] == "RELEASED"
        if released != (hold["release_authorization_sigil"] is not None):
            _fail("Artifact Storage State Hold release authorization disagrees with state")
    replicas = {
        wrapper["record"]["replica_id"]: wrapper["record"] for wrapper in state["replicas"]
    }
    replica_ids_by_blob: dict[str, list[str]] = {}
    for replica in replicas.values():
        replica_ids_by_blob.setdefault(replica["blob_sigil"], []).append(replica["replica_id"])
    blob_sigils = {wrapper["record"]["blob_sigil"] for wrapper in state["blobs"]}
    if any(blob_sigil not in blob_sigils for blob_sigil in replica_ids_by_blob):
        _fail("Artifact Storage State Replica has no matching Blob projection")
    for wrapper in state["blobs"]:
        blob = wrapper["record"]
        expected_known = sorted(replica_ids_by_blob.get(blob["blob_sigil"], []))
        if blob["known_replica_ids"] != expected_known:
            _fail("Artifact Storage Blob known Replicas disagree with State Replica projections")
        if not set(blob["eligible_replica_ids"]).issubset(expected_known):
            _fail("Artifact Storage Blob eligible Replicas are not known Replica projections")
    for wrapper in state["transfer_attempts"]:
        attempt = wrapper["record"]
        if attempt["state"] != "COMMITTED":
            continue
        selected = replicas.get(attempt["selected_replica_id"])
        if selected is None:
            _fail("Artifact Storage committed Transfer Attempt lacks its selected Replica")
        computed = attempt["commit_intent"]["computed_blob"]
        if (
            attempt["computed_blob_sigil"] != computed["blob_sigil"]
            or attempt["computed_size_bytes"] != computed["size_bytes"]
            or selected["blob_sigil"] != computed["blob_sigil"]
            or selected["size_bytes"] != computed["size_bytes"]
            or selected["object"] != attempt["commit_intent"]["target_object"]
            or selected["state"] != "AVAILABLE"
        ):
            _fail("Artifact Storage committed Transfer Attempt disagrees with selected Replica")
    for wrapper in state["materializations"]:
        materialization = wrapper["record"]
        source = replicas.get(materialization["source_replica_id"])
        if source is None:
            _fail("Artifact Storage Materialization lacks its source Replica")
        if source["blob_sigil"] != materialization["source_blob_sigil"]:
            _fail("Artifact Storage Materialization source Replica disagrees with Blob")
    request_ids = {request["transfer_id"] for request in state["transfer_requests"]}
    attempt_ids_by_transfer: dict[str, set[str]] = {}
    for wrapper in state["transfer_attempts"]:
        attempt = wrapper["record"]
        if attempt["transfer_id"] not in request_ids:
            _fail("Artifact Storage State Transfer Attempt lacks its request projection")
        attempt_ids_by_transfer.setdefault(attempt["transfer_id"], set()).add(
            attempt["transfer_attempt_id"]
        )
    for request in state["transfer_requests"]:
        attempt_ids = set(request["attempt_ids"])
        if attempt_ids != attempt_ids_by_transfer.get(request["transfer_id"], set()):
            _fail("Artifact Storage State Transfer Request Attempts disagree with projections")
        selected = request["selected_attempt_id"]
        if selected is not None and selected not in attempt_ids:
            _fail("Artifact Storage State Transfer Request selects an unknown Attempt")
    for intent in state["open_intents"]:
        source_sigil = intent["source_event"]["event_sigil"]
        if (
            intent["source_event"]["journal_id"] != state["journal_id"]
            or intent["source_event"]["sequence"] > state["applied_event_count"]
            or intent["intent_sigil"] != source_sigil
            or intent["last_event_sigil"] != source_sigil
        ):
            _fail("Artifact Storage State Open Intent disagrees with source Event")
    open_intent_ids = [value["intent_id"] for value in state["open_intents"]]
    if len(set(open_intent_ids)) != len(open_intent_ids):
        _fail("Artifact Storage State open-intent IDs must be globally unique")
    quarantine_intents = {
        intent["intent_id"]: intent for intent in state["open_intents"]
        if intent["intent_kind"] == "QUARANTINE_MOVE"
    }
    for quarantine in state["quarantines"]:
        intent = quarantine_intents.pop(quarantine["quarantine_id"], None)
        intent_recorded = quarantine["state"] == "INTENT_RECORDED"
        if (intent_recorded != (intent is not None)):
            _fail("Artifact Storage State Quarantine move Intent disagrees with projection")
        if intent is not None and (
            intent["owner_id"] != quarantine["owner_id"]
            or intent["source_object"] != quarantine["source_object"]
            or intent["target_object"] != quarantine["destination_object"]
        ):
            _fail("Artifact Storage State Quarantine move Intent disagrees with projection")
    if quarantine_intents:
        _fail("Artifact Storage State Quarantine move Intent lacks a projection")
    intents_by_owner: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for intent in state["open_intents"]:
        intents_by_owner.setdefault((intent["intent_kind"], intent["owner_id"]), []).append(intent)
    for collection, intent_kind, id_member, staging_member in (
        ("transfer_attempts", "TRANSFER_COMMIT", "transfer_attempt_id", "staging_object"),
        ("materializations", "MATERIALIZATION_COMMIT", "materialization_id", "destination_staging_object"),
    ):
        for wrapper in state[collection]:
            record = wrapper["record"]
            intents = intents_by_owner.get((intent_kind, record[id_member]), [])
            committing = record["state"] == "COMMITTING"
            if (committing and len(intents) != 1) or (not committing and intents):
                _fail(f"Artifact Storage State {collection} commit Intent disagrees with record state")
            if not committing:
                continue
            intent = intents[0]
            commit_intent = record["commit_intent"]
            if commit_intent is None:
                _fail(f"Artifact Storage State {collection} committing record lacks a commit Intent")
            if (
                intent["intent_id"] != commit_intent["intent_id"]
                or intent["staging_object"] != record[staging_member]
                or intent["staging_object"] != commit_intent["staging_object"]
                or intent["target_object"] != commit_intent["target_object"]
            ):
                _fail(f"Artifact Storage State {collection} commit Intent disagrees with record")
    disposition_intents_by_owner: dict[str, list[dict[str, Any]]] = {}
    for intent in state["open_intents"]:
        if intent["intent_kind"] == "DISPOSITION":
            disposition_intents_by_owner.setdefault(intent["owner_id"], []).append(intent)
    for disposition in state["dispositions"]:
        intents = disposition_intents_by_owner.pop(disposition["disposition_id"], [])
        executing = disposition["state"] == "EXECUTING"
        if (
            (executing and (
                len(intents) != 1 or intents[0]["intent_id"] != disposition["execution_intent_id"]
            ))
            or (not executing and intents)
        ):
            _fail("Artifact Storage State Disposition execution Intent disagrees with projection")
    if disposition_intents_by_owner:
        _fail("Artifact Storage State Disposition execution Intent lacks a projection")
    gc_intents = [intent for intent in state["open_intents"] if intent["intent_kind"] == "GC_DELETE"]
    gc_intent_keys: set[tuple[str, str]] = set()
    for plan in state["gc_plans"]:
        for target in plan["target_states"]:
            intents = [
                intent for intent in gc_intents
                if intent["intent_id"] == target["deletion_intent_id"]
            ]
            deleting = target["state"] == "DELETING"
            if (
                (deleting and (
                    len(intents) != 1
                    or intents[0]["owner_id"] != plan["gc_plan_id"]
                    or intents[0]["target_id"] != target["target_id"]
                ))
                or (not deleting and intents)
            ):
                _fail("Artifact Storage State GC deletion Intent disagrees with projection")
            if deleting:
                gc_intent_keys.add((plan["gc_plan_id"], target["deletion_intent_id"]))
    if gc_intent_keys != {(intent["owner_id"], intent["intent_id"]) for intent in gc_intents}:
        _fail("Artifact Storage State GC deletion Intent lacks a target projection")
    canonical_intents = {
        intent["intent_id"]: intent for intent in state["open_intents"]
        if intent["intent_kind"] == "CANONICAL_REFERENCE"
    }
    for projection in state["canonical_reference_intents"]:
        intent = canonical_intents.pop(projection["reference_intent_id"], None)
        if (
            (projection["state"] == "OPEN") != (intent is not None)
            or (intent is not None and intent["owner_id"] != projection["reference_intent_id"])
        ):
            _fail("Artifact Storage State canonical-reference Intent disagrees with projection")
    if canonical_intents:
        _fail("Artifact Storage State canonical-reference Intent lacks a projection")
    availability_counts = {
        "AVAILABLE": 0, "DEGRADED": 0, "UNAVAILABLE": 0, "INCIDENT": 0,
    }
    for wrapper in state["blobs"]:
        availability_counts[wrapper["record"]["availability"]] += 1
    expected_availability_counters = {
        "available_blobs": availability_counts["AVAILABLE"],
        "degraded_blobs": availability_counts["DEGRADED"],
        "unavailable_blobs": availability_counts["UNAVAILABLE"],
        "incident_blobs": availability_counts["INCIDENT"],
    }
    if state["availability_counters"] != expected_availability_counters:
        _fail("Artifact Storage State availability counters disagree with Blob records")
    for counter in state["quota_counters"]:
        if counter["used"] + counter["reserved"] > counter["limit"]:
            _fail("Artifact Storage quota counter exceeds its limit")
    for reservation in state["quota_reservations"]:
        for field in ("consumed_claims", "released_claims", "remaining_claims"):
            _validate_quota_claim_array(reservation[field], f"Quota Reservation {field}")
        _validate_quota_claim_array(reservation["reservation"]["claims"], "Reservation claims")
        claimed_by_class = {
            claim["quota_class"]: claim for claim in reservation["reservation"]["claims"]
        }
        for field in ("consumed_claims", "released_claims", "remaining_claims"):
            for claim in reservation[field]:
                original = claimed_by_class.get(claim["quota_class"])
                if original is None or any(
                    claim[dimension] > original[dimension]
                    for dimension in _QUOTA_CLAIM_FIELDS
                ):
                    _fail("Artifact Storage Quota Reservation exceeds its original claim")
        partition_by_class = {
            field: {claim["quota_class"]: claim for claim in reservation[field]}
            for field in ("consumed_claims", "released_claims", "remaining_claims")
        }
        for quota_class, original in claimed_by_class.items():
            if any(
                sum(
                    partition_by_class[field].get(quota_class, {}).get(dimension, 0)
                    for field in ("consumed_claims", "released_claims", "remaining_claims")
                ) != original[dimension]
                for dimension in _QUOTA_CLAIM_FIELDS
            ):
                _fail("Artifact Storage Quota Reservation claims do not partition original claim")
        reservation_state = reservation["state"]
        if reservation_state == "ACTIVE" and (
            reservation["consumed_claims"]
            or reservation["released_claims"]
            or reservation["remaining_claims"] != reservation["reservation"]["claims"]
            or reservation["retained_for_event_types"]
        ):
            _fail("Artifact Storage active Quota Reservation is not unspent")
        if reservation_state == "RETAINED" and (
            not reservation["remaining_claims"] or not reservation["retained_for_event_types"]
        ):
            _fail("Artifact Storage retained Quota Reservation lacks remaining claims or events")
        if reservation_state == "SETTLED" and (
            reservation["remaining_claims"] or reservation["retained_for_event_types"]
        ):
            _fail("Artifact Storage settled Quota Reservation retains claims or events")


def load_artifact_storage_state_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    state = _load_strict_object(raw, "Artifact Storage State")
    validate_artifact_storage_state_v1(state)
    return state


def validate_artifact_storage_head_supplied_state_v1(
    head: dict[str, Any], state: dict[str, Any],
) -> None:
    """Compare a Head with a caller-supplied State projection exactly."""
    validate_artifact_storage_journal_head_v1(head)
    validate_artifact_storage_state_v1(state)
    if (
        head["journal_id"] != state["journal_id"]
        or head["storage_format_version"] != state["storage_format_version"]
        or head["event_count"] != state["applied_event_count"]
        or head["last_sequence"] != state["applied_event_count"]
        or head["last_event_sigil"] != state["last_event_sigil"]
        or head["current_epoch"] != state["current_epoch"]
        or head["state_sigil"] != state["state_sigil"]
    ):
        _fail("Artifact Storage Journal Head contradicts supplied State")


def require_artifact_storage_journal_replay_authority_v1() -> NoReturn:
    """Fail closed: this module does not replay or repair a Storage Journal."""
    _fail("Artifact Storage Journal replay authority is unavailable in contract-only scope")


def require_artifact_storage_runtime_authority_v1() -> NoReturn:
    """Fail closed: local Storage wire validation authorizes no operation."""
    _fail("Artifact Storage runtime authority is unavailable in contract-only scope")
