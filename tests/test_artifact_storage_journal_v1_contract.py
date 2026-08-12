import json
from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.artifact_storage_contracts import (
    load_artifact_storage_journal_event_v1,
    load_artifact_storage_journal_head_v1,
    require_artifact_storage_journal_replay_authority_v1,
    require_artifact_storage_runtime_authority_v1,
    validate_artifact_storage_journal_event_v1,
    validate_artifact_storage_journal_head_supplied_event_v1,
    validate_artifact_storage_journal_head_v1,
)


SIGIL = "sha256:" + "a" * 64
SIGIL_B = "sha256:" + "b" * 64
STAMP = "2026-08-06T00:00:00Z"


def _event() -> dict[str, object]:
    event: dict[str, object] = {
        "schema_version": "artifact-storage-journal-event/1.0",
        "journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
        "event_type": "storage.message_rejected", "coordinator_id": "COORDINATOR",
        "epoch": 1, "recorded_at": STAMP, "observed_at": None,
        "entity_revisions": [{
            "entity_type": "STORE", "entity_id": "STORE", "previous_revision": None,
            "next_revision": 1,
        }], "causation_event_id": None, "idempotency_key_sigil": None,
        "quota_effects": [], "payload": {
            "message_class": "test", "message_sigil": None,
            "reason": {"code": "BACKEND_UNAVAILABLE", "evidence_sigils": []},
        }, "previous_event_sigil": None, "event_sigil": "",
    }
    event["event_sigil"] = content_sigil({
        key: member for key, member in event.items() if key != "event_sigil"
    })
    return event


def _head(event: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "artifact-storage-journal-head/1.0", "journal_id": "SJ-ONE",
        "storage_format_version": "1.0", "event_count": 1, "last_sequence": 1,
        "last_event_sigil": event["event_sigil"], "committed_byte_length": 1,
        "current_epoch": 1, "state_sigil": SIGIL, "updated_at": STAMP,
    }


def test_storage_journal_event_checks_self_sigil_order_and_strict_loading() -> None:
    event = _event()
    validate_artifact_storage_journal_event_v1(event)
    assert load_artifact_storage_journal_event_v1(json.dumps(event)) == event

    stale = deepcopy(event)
    stale["payload"]["message_class"] = "changed"  # type: ignore[index]
    with pytest.raises(AthanorError, match="self-Sigil"):
        validate_artifact_storage_journal_event_v1(stale)

    with pytest.raises(AthanorError, match="BOM"):
        load_artifact_storage_journal_event_v1(b"\xef\xbb\xbf" + json.dumps(event).encode())
    duplicate = json.dumps(event).replace(
        '"journal_id": "SJ-ONE",',
        '"journal_id": "SJ-ONE", "journal_id": "SJ-TWO",',
        1,
    )
    with pytest.raises(AthanorError, match="duplicate JSON key"):
        load_artifact_storage_journal_event_v1(duplicate)


def test_storage_journal_head_matrix_and_supplied_final_event() -> None:
    event = _event()
    head = _head(event)
    validate_artifact_storage_journal_head_v1(head)
    assert load_artifact_storage_journal_head_v1(json.dumps(head)) == head
    validate_artifact_storage_journal_head_supplied_event_v1(head, event, SIGIL)

    bad_empty = deepcopy(head)
    bad_empty.update({"event_count": 0, "last_sequence": 0})
    with pytest.raises(AthanorError, match="empty Journal Head"):
        validate_artifact_storage_journal_head_v1(bad_empty)

    wrong_event = deepcopy(event)
    wrong_event["journal_id"] = "SJ-TWO"
    wrong_event["event_sigil"] = content_sigil({
        key: member for key, member in wrong_event.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="contradicts supplied"):
        validate_artifact_storage_journal_head_supplied_event_v1(head, wrong_event, SIGIL)

    with pytest.raises(AthanorError, match="replay authority"):
        require_artifact_storage_journal_replay_authority_v1()
    with pytest.raises(AthanorError, match="runtime authority"):
        require_artifact_storage_runtime_authority_v1()
