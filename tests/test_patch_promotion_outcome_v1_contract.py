from __future__ import annotations

from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.patch_promotion_contracts import (
    derive_patch_promotion_outcome_id_v1,
    validate_patch_promotion_outcome_supplied_attempt_v1,
    validate_patch_promotion_outcome_v1,
)


SIGIL = "sha256:" + "a" * 64


def _seal(outcome: dict[str, object]) -> dict[str, object]:
    outcome["outcome_id"] = derive_patch_promotion_outcome_id_v1(
        str(outcome["attempt_id"]),
        str(outcome["terminal_journal_event_id"]),
        str(outcome["terminal_journal_event_sigil"]),
    )
    outcome["outcome_sigil"] = content_sigil(
        {key: value for key, value in outcome.items() if key != "outcome_sigil"}
    )
    return outcome


def _outcome() -> dict[str, object]:
    tree = {"manifest_sigil": SIGIL, "root_entry_sigil": SIGIL, "entry_count": 1, "total_bytes": 1}
    blob = {"sigil": SIGIL, "size_bytes": 1, "media_type": "application/octet-stream"}
    return _seal(
        {
            "schema_version": "patch-promotion-outcome/1.0",
            "outcome_id": "",
            "authorization_receipt": {
                "receipt_id": "RC-ONE",
                "receipt_sigil": SIGIL,
                "event_id": "CE-ONE",
                "event_body_sigil": SIGIL,
            },
            "attempt_id": "PAT-ONE",
            "terminal_journal_event_id": "PJE-ONE",
            "terminal_journal_event_sigil": SIGIL,
            "operation_sigil": SIGIL,
            "adapter": {"id": "PPA-ONE", "sigil": SIGIL},
            "before_identity": tree,
            "after_identity": tree,
            "before_generation": "generation",
            "after_generation": "generation",
            "checkpoint": None,
            "mutation_intent": None,
            "guard": None,
            "timestamps": {
                "created_at": "2026-08-06T00:00:00Z",
                "mutation_started_at": None,
                "verification_started_at": None,
                "terminal_at": "2026-08-06T00:00:01Z",
            },
            "status": "CANCELLED",
            "path_observations": [
                {
                    "path_bytes": "file",
                    "expected_preimage_sigil": SIGIL,
                    "observed_preimage_sigil": SIGIL,
                    "expected_postimage_sigil": SIGIL,
                    "observed_postimage_sigil": SIGIL,
                    "status": "MATCH",
                }
            ],
            "adapter_write_evidence": None,
            "verifier_evidence": [blob],
            "diagnostics": "cancelled",
            "outcome_sigil": "",
        }
    )


def test_promotion_outcome_checks_self_sigil_time_and_path_order() -> None:
    outcome = _outcome()
    validate_patch_promotion_outcome_v1(outcome)

    reverse_time = deepcopy(outcome)
    reverse_time["timestamps"]["terminal_at"] = "2026-08-05T23:59:59Z"
    _seal(reverse_time)
    with pytest.raises(AthanorError, match="timestamps"):
        validate_patch_promotion_outcome_v1(reverse_time)

    duplicate_paths = deepcopy(outcome)
    duplicate_paths["path_observations"].append(deepcopy(duplicate_paths["path_observations"][0]))
    _seal(duplicate_paths)
    with pytest.raises(AthanorError, match="validation failed|path observations"):
        validate_patch_promotion_outcome_v1(duplicate_paths)


def test_promotion_outcome_requires_per_entry_evidence_for_each_path() -> None:
    outcome = _outcome()
    outcome["status"] = "APPLIED"
    outcome["checkpoint"] = {"id": "PCK-ONE", "sigil": SIGIL}
    outcome["mutation_intent"] = {"id": "PMI-ONE", "sigil": SIGIL}
    outcome["guard"] = {"id": "PG-ONE", "sigil": SIGIL}
    outcome["adapter_write_evidence"] = {
        "mode": "PER_ENTRY_GENERATIONAL_CAS",
        "transaction_id_sigil": SIGIL,
        "receipt_sigils": [SIGIL],
        "before_generation": "generation",
        "after_generation": "generation",
        "causal_evidence_sigil": SIGIL,
    }
    _seal(outcome)
    validate_patch_promotion_outcome_v1(outcome)

    extra_path = deepcopy(outcome)
    extra_path["path_observations"].append(
        {**extra_path["path_observations"][0], "path_bytes": "other"}
    )
    _seal(extra_path)
    with pytest.raises(AthanorError, match="per-entry evidence"):
        validate_patch_promotion_outcome_v1(extra_path)

    wrong_generation = deepcopy(outcome)
    wrong_generation["adapter_write_evidence"]["after_generation"] = "other"
    _seal(wrong_generation)
    with pytest.raises(AthanorError, match="evidence disagrees with generations"):
        validate_patch_promotion_outcome_v1(wrong_generation)


def _attempt_for(outcome: dict[str, object]) -> dict[str, object]:
    attempt = {
        "schema_version": "patch-promotion-attempt/1.0",
        "attempt_id": outcome["attempt_id"],
        "authorization": {"id": "PAU-ONE", "sigil": SIGIL},
        "operation_sigil": outcome["operation_sigil"],
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
        "target_content_generation": "generation",
        "adapter": outcome["adapter"],
        "mode": "FULL_TREE_ATOMIC_CAS",
        "created_at": outcome["timestamps"]["created_at"],
        "state": outcome["status"],
        "revision": 1,
        "attempt_sigil": "",
    }
    attempt["attempt_sigil"] = content_sigil(
        {key: value for key, value in attempt.items() if key != "attempt_sigil"}
    )
    return attempt


def test_promotion_outcome_binds_to_a_terminal_supplied_attempt() -> None:
    outcome = _outcome()
    attempt = _attempt_for(outcome)
    validate_patch_promotion_outcome_supplied_attempt_v1(outcome, attempt)

    nonterminal = deepcopy(attempt)
    nonterminal["state"] = "READY"
    nonterminal["attempt_sigil"] = content_sigil(
        {key: value for key, value in nonterminal.items() if key != "attempt_sigil"}
    )
    with pytest.raises(AthanorError, match="terminal supplied Attempt"):
        validate_patch_promotion_outcome_supplied_attempt_v1(outcome, nonterminal)
