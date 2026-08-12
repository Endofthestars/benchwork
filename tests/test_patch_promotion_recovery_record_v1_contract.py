from __future__ import annotations

from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.patch_promotion_contracts import (
    derive_patch_promotion_recovery_record_id_v1,
    validate_patch_promotion_recovery_record_supplied_attempt_v1,
    validate_patch_promotion_recovery_record_v1,
)


SIGIL = "sha256:" + "a" * 64
RECEIPT = {
    "receipt_id": "RC-ONE",
    "receipt_sigil": SIGIL,
    "event_id": "CE-ONE",
    "event_body_sigil": SIGIL,
}
TREE = {"manifest_sigil": SIGIL, "root_entry_sigil": SIGIL, "entry_count": 1, "total_bytes": 1}
LINEAGE = {
    "target_id": "PT-ONE",
    "logical_fence_generation": 1,
    "logical_fence_revision": 1,
    "logical_fence_sigil": SIGIL,
    "predecessor_head_sigil": SIGIL,
    "predecessor": {
        "kind": "PROMOTION_PARTIAL",
        "parent_attempt_id": "PAT-ONE",
        "outcome_id": "PO-ONE",
        "outcome_sigil": SIGIL,
        "receipt": RECEIPT,
    },
}


def _seal(record: dict[str, object]) -> dict[str, object]:
    record["recovery_record_id"] = derive_patch_promotion_recovery_record_id_v1(
        str(record["recovery_attempt_id"]),
        str(record["terminal_journal_event_id"]),
        str(record["terminal_journal_event_sigil"]),
    )
    record["recovery_record_sigil"] = content_sigil(
        {key: value for key, value in record.items() if key != "recovery_record_sigil"}
    )
    return record


def _record() -> dict[str, object]:
    return _seal(
        {
            "schema_version": "patch-promotion-recovery-record/1.0",
            "recovery_record_id": "",
            "recovery_attempt_id": "PRA-ONE",
            "authorization_receipt": RECEIPT,
            "parent_attempt_id": "PAT-ONE",
            "parent_outcome_receipt": RECEIPT,
            "action": "RESTORE_BASE",
            "guard": {"id": "PG-ONE", "sigil": SIGIL},
            "checkpoint": {"id": "PCK-ONE", "sigil": SIGIL},
            "recovery_intent": {"id": "PRI-ONE", "sigil": SIGIL},
            "lineage": LINEAGE,
            "before_identity": TREE,
            "after_identity": TREE,
            "before_generation": "generation",
            "after_generation": "generation",
            "resulting_logical_fence_generation": 1,
            "verifier_evidence": [
                {"sigil": SIGIL, "size_bytes": 1, "media_type": "application/octet-stream"}
            ],
            "terminal_journal_event_id": "PJE-ONE",
            "terminal_journal_event_sigil": SIGIL,
            "status": "BASE_RESTORED",
            "abandonment_disposition": None,
            "recovery_record_sigil": "",
        }
    )


def _attempt(record: dict[str, object]) -> dict[str, object]:
    attempt = {
        "schema_version": "patch-promotion-recovery-attempt/1.0",
        "recovery_attempt_id": record["recovery_attempt_id"],
        "parent_attempt_id": record["parent_attempt_id"],
        "parent_outcome_receipt": record["parent_outcome_receipt"],
        "authorization": {"id": "PAU-ONE", "sigil": SIGIL},
        "action": record["action"],
        "target": {
            "target_id": "PT-ONE",
            "target_class": "DIRECTORY",
            "identity_profile": {"id": "PBIP-ONE", "sigil": SIGIL},
            "root_identity": {
                "root_object_sigil": SIGIL,
                "root_generation": "generation",
                "topology_sigil": SIGIL,
            },
            "selection_authorization_sigil": SIGIL,
        },
        "bound_before_identity": TREE,
        "bound_before_generation": "generation",
        "checkpoint": record["checkpoint"],
        "lineage": record["lineage"],
        "created_at": "2026-08-06T00:00:00Z",
        "state": record["status"],
        "revision": 1,
        "recovery_attempt_sigil": "",
    }
    attempt["recovery_attempt_sigil"] = content_sigil(
        {key: value for key, value in attempt.items() if key != "recovery_attempt_sigil"}
    )
    return attempt


def test_recovery_record_checks_identity_and_supplied_attempt() -> None:
    record = _record()
    validate_patch_promotion_recovery_record_v1(record)
    validate_patch_promotion_recovery_record_supplied_attempt_v1(record, _attempt(record))

    changed = deepcopy(record)
    changed["terminal_journal_event_id"] = "PJE-TWO"
    changed["recovery_record_sigil"] = content_sigil(
        {key: value for key, value in changed.items() if key != "recovery_record_sigil"}
    )
    with pytest.raises(AthanorError, match="ID"):
        validate_patch_promotion_recovery_record_v1(changed)

    nonterminal = _attempt(record)
    nonterminal["state"] = "READY"
    nonterminal["recovery_attempt_sigil"] = content_sigil(
        {key: value for key, value in nonterminal.items() if key != "recovery_attempt_sigil"}
    )
    with pytest.raises(AthanorError, match="terminal supplied Attempt"):
        validate_patch_promotion_recovery_record_supplied_attempt_v1(record, nonterminal)
