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


def _abandoned_record() -> dict[str, object]:
    record = _record()
    record["status"] = "ABANDONED"
    record["action"] = "ABANDON"
    disposition: dict[str, object] = {
        "kind": "ABANDONED_OPERATIONAL_ROOT_DISPOSITION",
        "recovery_attempt_id": record["recovery_attempt_id"],
        "parent_attempt_id": record["parent_attempt_id"],
        "authorization_receipt": record["authorization_receipt"],
        "actor": {
            "actor_id": "ACTOR", "actor_kind": "HUMAN",
            "authentication_context_sigil": SIGIL,
        },
        "disposition_policy_id": "PDP-ABANDONED-ROOT-DISPOSITION-V1",
        "disposition_policy_sigil": SIGIL,
        "terminal_event": {
            "protocol_id": "benchwork.patch-promotion", "protocol_version": "1.0",
            "journal_id": "PJ-ONE", "event_id": record["terminal_journal_event_id"],
            "sequence": 1, "event_type": "recovery.abandoned",
            "event_sigil": record["terminal_journal_event_sigil"],
        },
        "observed_partial_identity": record["before_identity"],
        "observed_generation": record["before_generation"],
        "logical_fence_generation": record["resulting_logical_fence_generation"],
        "guard_completion": {
            "kind": "TERMINAL_GUARD", "guard": record["guard"],
            "terminal_event": {
                "protocol_id": "benchwork.patch-promotion", "protocol_version": "1.0",
                "journal_id": "PJ-ONE", "event_id": "PJE-GUARD", "sequence": 2,
                "event_type": "target.guard-released", "event_sigil": SIGIL,
            }, "terminal_state": "RELEASED",
        },
        "root_dispositions": [{
            "operational_root_id": "PROOT-ONE", "active_operational_root_sigil": SIGIL,
            "operational_root_plan": {"schema_version": "control-record/1.0", "record_id": "PLAN", "record_sigil": SIGIL},
            "hold_id": "SH-ONE", "reference_set": {"reference_set_id": "RS-ONE", "reference_set_sigil": SIGIL},
            "policy_id": "SP-ONE", "policy_sigil": SIGIL,
            "disposition": "RELEASE_OPERATIONAL_HOLD_AFTER_CANONICAL_ABANDONMENT",
        }],
        "physical_byte_authority": "NONE", "logical_fence_disposition": "PRESERVE",
        "disposition_sigil": "",
    }
    disposition["disposition_sigil"] = content_sigil({
        key: value for key, value in disposition.items() if key != "disposition_sigil"
    })
    record["abandonment_disposition"] = disposition
    return _seal(record)


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


def test_abandoned_recovery_record_closes_nested_disposition() -> None:
    record = _abandoned_record()
    validate_patch_promotion_recovery_record_v1(record)

    tampered = deepcopy(record)
    tampered["abandonment_disposition"]["observed_generation"] = "other"
    tampered["recovery_record_sigil"] = content_sigil({
        key: value for key, value in tampered.items() if key != "recovery_record_sigil"
    })
    with pytest.raises(AthanorError, match="abandonment disposition self-Sigil mismatch"):
        validate_patch_promotion_recovery_record_v1(tampered)

    wrong_terminal = deepcopy(record)
    wrong_terminal["abandonment_disposition"]["terminal_event"]["event_type"] = "recovery.failed"
    wrong_terminal["abandonment_disposition"]["disposition_sigil"] = content_sigil({
        key: value for key, value in wrong_terminal["abandonment_disposition"].items()
        if key != "disposition_sigil"
    })
    wrong_terminal["recovery_record_sigil"] = content_sigil({
        key: value for key, value in wrong_terminal.items() if key != "recovery_record_sigil"
    })
    with pytest.raises(AthanorError, match="terminal Event type is invalid"):
        validate_patch_promotion_recovery_record_v1(wrong_terminal)

    wrong_guard = deepcopy(record)
    wrong_guard["abandonment_disposition"]["guard_completion"]["terminal_event"]["event_type"] = "target.guard-fenced"
    wrong_guard["abandonment_disposition"]["disposition_sigil"] = content_sigil({
        key: value for key, value in wrong_guard["abandonment_disposition"].items()
        if key != "disposition_sigil"
    })
    wrong_guard["recovery_record_sigil"] = content_sigil({
        key: value for key, value in wrong_guard.items() if key != "recovery_record_sigil"
    })
    with pytest.raises(AthanorError, match="guard completion Event type is invalid"):
        validate_patch_promotion_recovery_record_v1(wrong_guard)
