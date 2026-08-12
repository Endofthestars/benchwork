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
