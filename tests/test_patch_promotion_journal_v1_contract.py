from __future__ import annotations

from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.patch_promotion_contracts import (
    require_patch_promotion_runtime_authority_v1,
    validate_patch_promotion_journal_event_v1,
    validate_patch_promotion_journal_head_v1,
    validate_patch_promotion_journal_prefix_v1,
)


SIGIL = "sha256:" + "a" * 64


def _head() -> dict[str, object]:
    head: dict[str, object] = {
        "schema_version": "patch-promotion-journal-head/1.0", "journal_id": "PJ-ONE",
        "coordinator_epoch": 1, "event_count": 0, "last_sequence": 0,
        "last_event_sigil": None, "committed_offset": 0,
        "frames_file_sigil_prefix": SIGIL, "projected_state_sigil": SIGIL,
        "head_generation": 0, "head_sigil": "",
    }
    head["head_sigil"] = content_sigil({key: value for key, value in head.items() if key != "head_sigil"})
    return head


def _event(sequence: int, previous: str | None, event_id: str) -> dict[str, object]:
    event: dict[str, object] = {
        "schema_version": "patch-promotion-journal-event/1.0", "journal_id": "PJ-ONE",
        "event_id": event_id, "sequence": sequence, "coordinator_id": "PC-ONE",
        "coordinator_epoch": 1, "event_type": "coordinator.epoch-started",
        "recorded_at": f"2026-08-06T00:00:0{sequence}Z",
        "entity_revisions": [{"entity_type": "COORDINATOR", "entity_id": "PC-ONE", "prior_revision": sequence - 1, "next_revision": sequence}],
        "causation_event_id": None, "idempotency_key_sigil": None,
        "payload": {
            "prior_epoch": 0, "new_epoch": 1, "replayed_head": _head(),
            "replayed_state_sigil": SIGIL, "clock_evidence_sigil": SIGIL,
            "completed_tail_recovery_id": None, "deactivated_operational_root_ids": [],
            "started_at": f"2026-08-06T00:00:0{sequence}Z",
        },
        "previous_event_sigil": previous, "event_sigil": "",
    }
    event["event_sigil"] = content_sigil({key: value for key, value in event.items() if key != "event_sigil"})
    return event


def test_patch_promotion_journal_event_and_head_self_sigils_are_checked() -> None:
    event = _event(1, None, "PJE-ONE")
    validate_patch_promotion_journal_event_v1(event)
    validate_patch_promotion_journal_head_v1(_head())

    wrong = deepcopy(event)
    wrong["event_sigil"] = SIGIL
    with pytest.raises(AthanorError, match="self-Sigil"):
        validate_patch_promotion_journal_event_v1(wrong)


def test_patch_promotion_prefix_and_head_require_one_contiguous_chain() -> None:
    first = _event(1, None, "PJE-ONE")
    second = _event(2, first["event_sigil"], "PJE-TWO")
    head = _head()
    head.update({"event_count": 2, "last_sequence": 2, "last_event_sigil": second["event_sigil"]})
    head["head_sigil"] = content_sigil({key: value for key, value in head.items() if key != "head_sigil"})
    validate_patch_promotion_journal_prefix_v1([first, second], head=head)

    broken = deepcopy(second)
    broken["previous_event_sigil"] = SIGIL
    broken["event_sigil"] = content_sigil({key: value for key, value in broken.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="broken Event chain"):
        validate_patch_promotion_journal_prefix_v1([first, broken])

    noninitial = deepcopy(first)
    noninitial["event_type"] = "coordinator.replay-started"
    with pytest.raises(AthanorError):
        validate_patch_promotion_journal_prefix_v1([noninitial])

    wrong_head = deepcopy(head)
    wrong_head["last_sequence"] = 1
    wrong_head["head_sigil"] = content_sigil({key: value for key, value in wrong_head.items() if key != "head_sigil"})
    with pytest.raises(AthanorError, match="Head terminal fields disagree"):
        validate_patch_promotion_journal_prefix_v1([first, second], head=wrong_head)


def test_patch_promotion_contract_validation_grants_no_runtime_authority() -> None:
    with pytest.raises(AthanorError, match="authority is unavailable"):
        require_patch_promotion_runtime_authority_v1()
