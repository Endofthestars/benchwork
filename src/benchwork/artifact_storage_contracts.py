"""Fail-closed local validators for RFC-0013 Storage Journal wire contracts.

These helpers check canonical documents and caller-supplied prefix relations.
They never append, replay, repair, or authorize an Artifact Storage Journal.
"""

from __future__ import annotations

import json
import math
import unicodedata
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


def require_artifact_storage_journal_replay_authority_v1() -> NoReturn:
    """Fail closed: this module does not replay or repair a Storage Journal."""
    _fail("Artifact Storage Journal replay authority is unavailable in contract-only scope")


def require_artifact_storage_runtime_authority_v1() -> NoReturn:
    """Fail closed: local Storage wire validation authorizes no operation."""
    _fail("Artifact Storage runtime authority is unavailable in contract-only scope")
