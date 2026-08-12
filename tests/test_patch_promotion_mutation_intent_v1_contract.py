from __future__ import annotations

from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.patch_promotion_contracts import validate_patch_promotion_mutation_intent_v1


SIGIL = "sha256:" + "a" * 64


def _seal(intent: dict[str, object]) -> dict[str, object]:
    intent["intent_sigil"] = content_sigil(
        {key: value for key, value in intent.items() if key != "intent_sigil"},
    )
    return intent


def _intent() -> dict[str, object]:
    root = {"root_object_sigil": SIGIL, "root_generation": "generation-1", "topology_sigil": SIGIL}
    tree = {"manifest_sigil": SIGIL, "root_entry_sigil": SIGIL, "entry_count": 1, "total_bytes": 1}
    postimage = {
        "identity_profile": {"id": "PBIP-ONE", "sigil": SIGIL},
        "tree": tree,
        "manifest_blob": {"sigil": SIGIL, "size_bytes": 1, "media_type": "application/octet-stream"},
    }
    return _seal({
        "schema_version": "patch-promotion-mutation-intent/1.0",
        "intent_id": "PMI-ONE",
        "attempt_id": "PAT-ONE",
        "authorization": {"id": "PAU-ONE", "sigil": SIGIL},
        "operation_sigil": SIGIL,
        "guard": {"id": "PG-ONE", "sigil": SIGIL},
        "fencing_generation": 1,
        "fence_floor": 1,
        "target_content_generation": "generation-1",
        "checkpoint": {"id": "PCK-ONE", "sigil": SIGIL},
        "base": {"id": "PB-ONE", "sigil": SIGIL},
        "postimage": postimage,
        "operations_sigil": SIGIL,
        "topology_plan": {
            "mode": "FULL_TREE_ATOMIC_CAS",
            "target_wide_generation": "generation-1",
            "root_identity": root,
            "ancestor_set_sigil": SIGIL,
            "operation_order": ["file.txt"],
            "plan_sigil": SIGIL,
        },
        "root_identity": root,
        "ancestor_identities": [{
            "path_bytes": "parent",
            "object_identity_sigil": SIGIL,
            "generation": "generation-1",
        }],
        "adapter": {"id": "PPA-ONE", "sigil": SIGIL},
        "verification_method": {
            "kind": "FULL_TREE_IDENTITY",
            "identity_profile": {"id": "PBIP-ONE", "sigil": SIGIL},
            "expected_tree": tree,
            "verifier_profile_sigil": SIGIL,
        },
        "committed_at": "2026-08-06T00:00:00Z",
        "intent_sigil": "",
    })


def test_mutation_intent_checks_self_sigil_and_cross_record_identity() -> None:
    intent = _intent()
    validate_patch_promotion_mutation_intent_v1(intent)

    wrong_root = deepcopy(intent)
    wrong_root["root_identity"] = {  # type: ignore[index]
        **wrong_root["root_identity"], "root_generation": "generation-2",
    }
    _seal(wrong_root)
    with pytest.raises(AthanorError, match="topology root"):
        validate_patch_promotion_mutation_intent_v1(wrong_root)

    wrong_tree = deepcopy(intent)
    wrong_tree["verification_method"]["expected_tree"] = {  # type: ignore[index]
        **wrong_tree["verification_method"]["expected_tree"], "entry_count": 2,
    }
    _seal(wrong_tree)
    with pytest.raises(AthanorError, match="verification method"):
        validate_patch_promotion_mutation_intent_v1(wrong_tree)


def test_mutation_intent_checks_topology_generation_and_ancestor_order() -> None:
    intent = _intent()
    wrong_generation = deepcopy(intent)
    wrong_generation["topology_plan"]["target_wide_generation"] = "generation-2"  # type: ignore[index]
    _seal(wrong_generation)
    with pytest.raises(AthanorError, match="topology generation"):
        validate_patch_promotion_mutation_intent_v1(wrong_generation)

    duplicate_order = deepcopy(intent)
    duplicate_order["topology_plan"]["operation_order"] = ["file.txt", "file.txt"]  # type: ignore[index]
    _seal(duplicate_order)
    with pytest.raises(AthanorError, match="operation_order|operation order"):
        validate_patch_promotion_mutation_intent_v1(duplicate_order)
