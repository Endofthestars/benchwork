"""Fail-closed local validators for RFC-0014 Promotion Journal wires.

These helpers validate immutable wire and caller-supplied prefix facts only.
They neither replay promotion state nor authorize a target mutation, recovery,
Storage operation, Chronicle write, or Patch promotion.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Any, NoReturn

from .athanor import AthanorError, content_sigil
from .execution_contracts import _check_nfc, _load_strict_object
from .schema_validation import validate_instance


def _fail(message: str) -> NoReturn:
    raise AthanorError(message)


def _without(value: dict[str, Any], member: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != member}


def _time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AthanorError("Patch Promotion Journal Event recorded_at is invalid") from error


def _blob_key(blob: dict[str, Any]) -> bytes:
    return blob["sigil"].encode("ascii")


def _require_sorted_unique_blobs(blobs: list[dict[str, Any]], name: str) -> None:
    keys = [_blob_key(blob) for blob in blobs]
    if keys != sorted(keys) or len(set(keys)) != len(keys):
        _fail(f"Patch Bundle {name} must be sorted and unique by Sigil")


def _entry_payload(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Return the one RFC-0014 payload Blob required by a postimage entry."""
    kind = entry["kind"]
    if kind == "FILE":
        return {
            "sigil": entry["blob_sigil"],
            "size_bytes": entry["size_bytes"],
            "media_type": "application/octet-stream",
        }
    if kind == "SYMLINK":
        target = entry["target"].encode("utf-8")
        sigil = "sha256:" + hashlib.sha256(target).hexdigest()
        if entry["target_sigil"] != sigil:
            _fail("Patch Bundle SYMLINK target Sigil does not match UTF-8 target bytes")
        return {
            "sigil": sigil,
            "size_bytes": len(target),
            "media_type": "application/octet-stream",
        }
    return None


def validate_patch_bundle_v1(bundle: dict[str, Any]) -> None:
    """Validate local RFC-0014 Patch Bundle invariants without resolving Blobs."""
    validate_instance("patch-bundle-1.0.json", bundle)
    _check_nfc(bundle)
    if bundle["bundle_sigil"] != content_sigil(_without(bundle, "bundle_sigil")):
        _fail("Patch Bundle self-Sigil mismatch")

    operations = bundle["operations"]
    paths = [operation["path_bytes"].encode("utf-8") for operation in operations]
    if paths != sorted(paths) or len(set(paths)) != len(paths):
        _fail("Patch Bundle operations must be sorted and unique by path_bytes")
    if len(operations) > bundle["limits"]["max_paths"]:
        _fail("Patch Bundle operation count exceeds max_paths")

    expected_payloads: dict[str, dict[str, Any]] = {}
    for operation in operations:
        before = operation["preimage"]["kind"]
        after = operation["postimage"]["kind"]
        transition = operation["operation"]
        valid_transition = (
            (transition == "ADD" and before == "ABSENT" and after != "ABSENT")
            or (transition == "DELETE" and before != "ABSENT" and after == "ABSENT")
            or (transition == "MODIFY" and before != "ABSENT" and before == after)
            or (
                transition == "TYPE_CHANGE"
                and before != "ABSENT"
                and after != "ABSENT"
                and before != after
            )
        )
        if not valid_transition:
            _fail("Patch Bundle operation disagrees with its preimage and postimage kinds")
        payload = _entry_payload(operation["postimage"])
        if (operation["payload_sigil"] is None) != (payload is None):
            _fail("Patch Bundle operation payload presence disagrees with postimage kind")
        if payload is not None:
            if operation["payload_sigil"] != payload["sigil"]:
                _fail("Patch Bundle operation payload Sigil disagrees with postimage")
            previous = expected_payloads.setdefault(payload["sigil"], payload)
            if previous != payload:
                _fail("Patch Bundle reuses one payload Sigil with inconsistent Blob metadata")

    payloads = bundle["payloads"]
    renderings = bundle["renderings"]
    attachments = bundle["attachments"]
    _require_sorted_unique_blobs(payloads, "payloads")
    _require_sorted_unique_blobs(renderings, "renderings")
    _require_sorted_unique_blobs(attachments, "attachments")
    actual_payloads = {blob["sigil"]: blob for blob in payloads}
    if actual_payloads != expected_payloads:
        _fail("Patch Bundle payloads are not the exact postimage payload set")
    if len(payloads) > bundle["limits"]["max_blobs"]:
        _fail("Patch Bundle payload count exceeds max_blobs")
    if any(blob["size_bytes"] > bundle["limits"]["max_payload_bytes"] for blob in payloads):
        _fail("Patch Bundle payload exceeds max_payload_bytes")

    blob_union: dict[str, dict[str, Any]] = {}
    for blob in payloads + renderings + attachments:
        previous = blob_union.setdefault(blob["sigil"], blob)
        if previous != blob:
            _fail("Patch Bundle Blob union has inconsistent metadata for one Sigil")
    if (
        sum(blob["size_bytes"] for blob in blob_union.values())
        > bundle["limits"]["max_total_bytes"]
    ):
        _fail("Patch Bundle Blob union exceeds max_total_bytes")


def load_patch_bundle_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    bundle = _load_strict_object(raw, "Patch Bundle")
    validate_patch_bundle_v1(bundle)
    return bundle


def validate_patch_promotion_checkpoint_v1(checkpoint: dict[str, Any]) -> None:
    """Validate local checkpoint/blob closure without resolving target observations."""
    validate_instance("patch-promotion-checkpoint-1.0.json", checkpoint)
    _check_nfc(checkpoint)
    if checkpoint["checkpoint_sigil"] != content_sigil(_without(checkpoint, "checkpoint_sigil")):
        _fail("Patch Promotion Checkpoint self-Sigil mismatch")
    if _time(checkpoint["verified_at"]) < _time(checkpoint["created_at"]):
        _fail("Patch Promotion Checkpoint verified_at precedes created_at")

    affected_paths = [path.encode("utf-8") for path in checkpoint["affected_paths"]]
    entries = checkpoint["entries"]
    entry_paths = [entry["path_bytes"].encode("utf-8") for entry in entries]
    if affected_paths != sorted(affected_paths) or len(set(affected_paths)) != len(affected_paths):
        _fail("Patch Promotion Checkpoint affected_paths must be sorted and unique")
    if entry_paths != sorted(entry_paths) or len(set(entry_paths)) != len(entry_paths):
        _fail("Patch Promotion Checkpoint entries must be sorted and unique by path_bytes")
    if entry_paths != affected_paths:
        _fail("Patch Promotion Checkpoint entries are not the exact affected path set")

    expected_blobs: dict[str, dict[str, Any]] = {}
    for entry in entries:
        expected = _entry_payload(entry["preimage"])
        actual = entry["checkpoint_blob"]
        if (actual is None) != (expected is None):
            _fail("Patch Promotion Checkpoint Blob presence disagrees with preimage kind")
        if actual is not None:
            if actual != expected:
                _fail("Patch Promotion Checkpoint Blob disagrees with preimage")
            previous = expected_blobs.setdefault(actual["sigil"], actual)
            if previous != actual:
                _fail("Patch Promotion Checkpoint reuses one Blob Sigil with inconsistent metadata")
    blobs = checkpoint["checkpoint_blobs"]
    _require_sorted_unique_blobs(blobs, "checkpoint_blobs")
    if {blob["sigil"]: blob for blob in blobs} != expected_blobs:
        _fail("Patch Promotion Checkpoint blobs are not the exact preimage Blob set")


def load_patch_promotion_checkpoint_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    checkpoint = _load_strict_object(raw, "Patch Promotion Checkpoint")
    validate_patch_promotion_checkpoint_v1(checkpoint)
    return checkpoint


def validate_patch_promotion_mutation_intent_v1(intent: dict[str, Any]) -> None:
    """Validate local write-ahead Intent consistency without a target mutation."""
    validate_instance("patch-promotion-mutation-intent-1.0.json", intent)
    _check_nfc(intent)
    if intent["intent_sigil"] != content_sigil(_without(intent, "intent_sigil")):
        _fail("Patch Promotion Mutation Intent self-Sigil mismatch")
    plan = intent["topology_plan"]
    if plan["root_identity"] != intent["root_identity"]:
        _fail("Patch Promotion Mutation Intent topology root disagrees with root identity")
    if plan["target_wide_generation"] != intent["target_content_generation"]:
        _fail("Patch Promotion Mutation Intent topology generation disagrees with target")
    operation_order = [path.encode("utf-8") for path in plan["operation_order"]]
    if len(operation_order) != len(set(operation_order)):
        _fail("Patch Promotion Mutation Intent topology operation order has duplicates")
    ancestors = intent["ancestor_identities"]
    ancestor_paths = [ancestor["path_bytes"].encode("utf-8") for ancestor in ancestors]
    if ancestor_paths != sorted(ancestor_paths) or len(ancestor_paths) != len(set(ancestor_paths)):
        _fail("Patch Promotion Mutation Intent ancestors must be sorted and unique")
    method = intent["verification_method"]
    if (
        method["identity_profile"] != intent["postimage"]["identity_profile"]
        or method["expected_tree"] != intent["postimage"]["tree"]
    ):
        _fail("Patch Promotion Mutation Intent verification method disagrees with postimage")


def load_patch_promotion_mutation_intent_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    intent = _load_strict_object(raw, "Patch Promotion Mutation Intent")
    validate_patch_promotion_mutation_intent_v1(intent)
    return intent


def validate_patch_promotion_target_guard_v1(guard: dict[str, Any]) -> None:
    """Validate local target-guard invariants without asserting physical ownership."""
    validate_instance("patch-promotion-target-guard-1.0.json", guard)
    _check_nfc(guard)
    if guard["guard_sigil"] != content_sigil(_without(guard, "guard_sigil")):
        _fail("Patch Promotion Target Guard self-Sigil mismatch")
    anchors = (guard["clock_anchor_evidence_sigil"], guard["original_remaining_ns"])
    if any(value is None for value in anchors) and not all(value is None for value in anchors):
        _fail("Patch Promotion Target Guard anchor fields must be jointly null or present")
    times = (guard["acquired_at"], guard["expires_at"])
    if any(value is None for value in times) and not all(value is None for value in times):
        _fail("Patch Promotion Target Guard acquisition times must be jointly null or present")
    if times[0] is not None and _time(times[1]) < _time(times[0]):
        _fail("Patch Promotion Target Guard expires before acquisition")
    active = {"HELD", "RENEWING", "RELEASING", "FENCING", "RECOVERING"}
    if guard["state"] in active and (
        any(value is None for value in anchors) or any(value is None for value in times)
    ):
        _fail("Patch Promotion active Target Guard lacks a deadline anchor")
    if guard["fence_floor"] > guard["fencing_generation"]:
        _fail("Patch Promotion Target Guard fence floor exceeds fencing generation")
    if guard["state"] == "NONE" and any((guard["backend_generation"], *anchors, *times)):
        _fail("Patch Promotion empty Target Guard has active physical fields")


def load_patch_promotion_target_guard_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    guard = _load_strict_object(raw, "Patch Promotion Target Guard")
    validate_patch_promotion_target_guard_v1(guard)
    return guard


def validate_patch_promotion_authorization_v1(authorization: dict[str, Any]) -> None:
    """Validate local immutable Authorization bytes, without resolving its Preview."""
    validate_instance("patch-promotion-authorization-1.0.json", authorization)
    _check_nfc(authorization)
    if authorization["authorization_sigil"] != content_sigil(
        _without(authorization, "authorization_sigil")
    ):
        _fail("Patch Promotion Authorization self-Sigil mismatch")
    paths = [path.encode("utf-8") for path in authorization["affected_paths"]]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        _fail("Patch Promotion Authorization affected paths must be sorted and unique")
    evidence = authorization["validation"]["evidence"]
    evidence_ids = [item["id"].encode("ascii") for item in evidence]
    if evidence_ids != sorted(evidence_ids) or len(evidence_ids) != len(set(evidence_ids)):
        _fail("Patch Promotion Authorization validation evidence must be sorted and unique")
    if authorization["decision_at"] > authorization["expires_at"]:
        _fail("Patch Promotion Authorization expires before its decision")


def validate_patch_promotion_attempt_v1(attempt: dict[str, Any]) -> None:
    """Validate one immutable Promotion Attempt without replaying its transitions."""
    validate_instance("patch-promotion-attempt-1.0.json", attempt)
    _check_nfc(attempt)
    if attempt["attempt_sigil"] != content_sigil(_without(attempt, "attempt_sigil")):
        _fail("Patch Promotion Attempt self-Sigil mismatch")


def validate_patch_promotion_attempt_supplied_authorization_v1(
    attempt: dict[str, Any],
    authorization: dict[str, Any],
) -> None:
    """Bind an allocated Attempt to its exact supplied Authorization document."""
    validate_patch_promotion_attempt_v1(attempt)
    validate_patch_promotion_authorization_v1(authorization)
    if (
        attempt["authorization"]
        != {"id": authorization["authorization_id"], "sigil": authorization["authorization_sigil"]}
        or attempt["operation_sigil"] != authorization["operation_sigil"]
        or attempt["target"] != authorization["target"]
        or attempt["target_content_generation"] != authorization["target_content_generation"]
        or attempt["adapter"] != authorization["adapter"]
        or attempt["mode"] != authorization["mode"]
    ):
        _fail("Patch Promotion Attempt disagrees with supplied Authorization")


def validate_patch_promotion_outcome_v1(outcome: dict[str, Any]) -> None:
    """Validate local terminal Outcome closure without resolving its Journal Event."""
    validate_instance("patch-promotion-outcome-1.0.json", outcome)
    _check_nfc(outcome)
    if outcome["outcome_sigil"] != content_sigil(_without(outcome, "outcome_sigil")):
        _fail("Patch Promotion Outcome self-Sigil mismatch")
    times = outcome["timestamps"]
    ordered_times = [times["created_at"]]
    ordered_times.extend(
        value
        for value in (times["mutation_started_at"], times["verification_started_at"])
        if value is not None
    )
    ordered_times.append(times["terminal_at"])
    if [_time(value) for value in ordered_times] != sorted(_time(value) for value in ordered_times):
        _fail("Patch Promotion Outcome timestamps are not non-decreasing")
    observations = outcome["path_observations"]
    paths = [item["path_bytes"].encode("utf-8") for item in observations]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        _fail("Patch Promotion Outcome path observations must be sorted and unique")
    verifier = outcome["verifier_evidence"]
    verifier_sigils = [item["sigil"].encode("ascii") for item in verifier]
    if verifier_sigils != sorted(verifier_sigils) or len(verifier_sigils) != len(
        set(verifier_sigils)
    ):
        _fail("Patch Promotion Outcome verifier evidence must be sorted and unique")
    adapter_evidence = outcome["adapter_write_evidence"]
    if adapter_evidence is not None:
        receipts = adapter_evidence["receipt_sigils"]
        if receipts != sorted(receipts) or len(receipts) != len(set(receipts)):
            _fail("Patch Promotion Outcome adapter receipt Sigils must be sorted and unique")
        if adapter_evidence["mode"] != "FULL_TREE_ATOMIC_CAS" and len(receipts) != len(
            observations
        ):
            _fail("Patch Promotion Outcome per-entry evidence must cover every path observation")


def validate_patch_promotion_journal_event_v1(event: dict[str, Any]) -> None:
    """Validate one closed self-authenticating Promotion Journal Event."""
    validate_instance("patch-promotion-journal-event-1.0.json", event)
    _check_nfc(event)
    if event["event_sigil"] != content_sigil(_without(event, "event_sigil")):
        _fail("Patch Promotion Journal Event self-Sigil mismatch")


def load_patch_promotion_journal_event_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    event = _load_strict_object(raw, "Patch Promotion Journal Event")
    validate_patch_promotion_journal_event_v1(event)
    return event


def validate_patch_promotion_journal_head_v1(head: dict[str, Any]) -> None:
    """Validate one closed Head cache record without reading frames."""
    validate_instance("patch-promotion-journal-head-1.0.json", head)
    _check_nfc(head)
    if head["head_sigil"] != content_sigil(_without(head, "head_sigil")):
        _fail("Patch Promotion Journal Head self-Sigil mismatch")
    empty = head["event_count"] == 0
    if empty != (head["last_sequence"] == 0 and head["last_event_sigil"] is None):
        _fail("Patch Promotion Journal Head empty fields disagree")
    if not empty and (
        head["last_sequence"] != head["event_count"] or head["last_event_sigil"] is None
    ):
        _fail("Patch Promotion Journal Head terminal fields disagree")


def load_patch_promotion_journal_head_v1(raw: str | bytes | bytearray) -> dict[str, Any]:
    head = _load_strict_object(raw, "Patch Promotion Journal Head")
    validate_patch_promotion_journal_head_v1(head)
    return head


def validate_patch_promotion_journal_prefix_v1(
    events: list[dict[str, Any]],
    *,
    head: dict[str, Any] | None = None,
) -> None:
    """Validate one complete caller-supplied contiguous Promotion prefix."""
    if not events:
        _fail("Patch Promotion Journal prefix requires a nonempty sequence")
    journal_id: str | None = None
    coordinator: tuple[str, int] | None = None
    previous_sigil: str | None = None
    previous_time: datetime | None = None
    event_ids: set[str] = set()
    for sequence, event in enumerate(events, 1):
        validate_patch_promotion_journal_event_v1(event)
        if sequence == 1 and event["event_type"] != "coordinator.epoch-started":
            _fail("Patch Promotion Journal prefix must begin with coordinator.epoch-started")
        if journal_id is None:
            journal_id = event["journal_id"]
            coordinator = (event["coordinator_id"], event["coordinator_epoch"])
        if (
            event["journal_id"] != journal_id
            or (event["coordinator_id"], event["coordinator_epoch"]) != coordinator
        ):
            _fail("Patch Promotion Journal prefix has inconsistent identity or coordinator epoch")
        if event["event_id"] in event_ids:
            _fail("Patch Promotion Journal prefix has a duplicate Event identity")
        if event["sequence"] != sequence or event["previous_event_sigil"] != previous_sigil:
            _fail("Patch Promotion Journal prefix has a sequence gap or broken Event chain")
        recorded_at = _time(event["recorded_at"])
        if previous_time is not None and recorded_at < previous_time:
            _fail("Patch Promotion Journal prefix has decreasing recorded_at time")
        event_ids.add(event["event_id"])
        previous_sigil = event["event_sigil"]
        previous_time = recorded_at
    if head is not None:
        validate_patch_promotion_journal_head_v1(head)
        last = events[-1]
        if coordinator is None:
            _fail("Patch Promotion Journal prefix has no coordinator")
        if (
            head["journal_id"] != journal_id
            or head["coordinator_epoch"] != coordinator[1]
            or head["event_count"] != last["sequence"]
            or head["last_sequence"] != last["sequence"]
            or head["last_event_sigil"] != last["event_sigil"]
        ):
            _fail("Patch Promotion Journal Head disagrees with supplied prefix")


def require_patch_promotion_runtime_authority_v1() -> NoReturn:
    """Fail closed: local Promotion wire validation authorizes no mutation."""
    _fail("Patch Promotion runtime authority is unavailable in contract-only scope")
