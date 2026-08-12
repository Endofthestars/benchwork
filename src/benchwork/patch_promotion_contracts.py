"""Fail-closed local validators for RFC-0014 Promotion Journal wires.

These helpers validate immutable wire and caller-supplied prefix facts only.
They neither replay promotion state nor authorize a target mutation, recovery,
Storage operation, Chronicle write, or Patch promotion.
"""

from __future__ import annotations

from datetime import datetime
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
    events: list[dict[str, Any]], *, head: dict[str, Any] | None = None,
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
