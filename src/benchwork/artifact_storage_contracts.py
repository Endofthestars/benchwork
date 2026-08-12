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
    for expected_sequence, event in enumerate(events, start=1):
        validate_artifact_storage_journal_event_v1(event)
        if expected_sequence == 1 and event["event_type"] != "storage.initialized":
            _fail("Artifact Storage Journal prefix does not start with storage.initialized")
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
    for request in state["transfer_requests"]:
        selected = request["selected_attempt_id"]
        if selected is not None and selected not in request["attempt_ids"]:
            _fail("Artifact Storage State Transfer Request selects an unknown Attempt")
    for intent in state["open_intents"]:
        source_sigil = intent["source_event"]["event_sigil"]
        if intent["intent_sigil"] != source_sigil or intent["last_event_sigil"] != source_sigil:
            _fail("Artifact Storage State Open Intent Sigils disagree with source Event")
    open_intent_ids = [value["intent_id"] for value in state["open_intents"]]
    if len(set(open_intent_ids)) != len(open_intent_ids):
        _fail("Artifact Storage State open-intent IDs must be globally unique")
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
