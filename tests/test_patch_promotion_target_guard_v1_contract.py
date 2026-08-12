from __future__ import annotations

from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.patch_promotion_contracts import validate_patch_promotion_target_guard_v1


SIGIL = "sha256:" + "a" * 64


def _seal(guard: dict[str, object]) -> dict[str, object]:
    guard["guard_sigil"] = content_sigil({key: value for key, value in guard.items() if key != "guard_sigil"})
    return guard


def _guard() -> dict[str, object]:
    return _seal({
        "schema_version": "patch-promotion-target-guard/1.0", "guard_id": "PG-ONE", "target_id": "PT-ONE",
        "owner_kind": "PROMOTION", "owner_attempt_id": "PAT-ONE", "coordinator_id": "PC-ONE",
        "coordinator_epoch": 1, "state": "HELD", "backend_generation": "generation-1",
        "fencing_generation": 2, "fence_floor": 1, "target_content_generation": "target-generation",
        "deadline_policy_sigil": SIGIL, "clock_anchor_evidence_sigil": SIGIL, "original_remaining_ns": 1,
        "acquired_at": "2026-08-06T00:00:00Z", "expires_at": "2026-08-06T00:00:01Z",
        "recovery_of_guard_id": None, "revision": 1, "guard_sigil": "",
    })


def test_target_guard_checks_self_sigil_deadlines_and_fences() -> None:
    guard = _guard()
    validate_patch_promotion_target_guard_v1(guard)

    missing_anchor = deepcopy(guard)
    missing_anchor["original_remaining_ns"] = None
    _seal(missing_anchor)
    with pytest.raises(AthanorError, match="anchor fields"):
        validate_patch_promotion_target_guard_v1(missing_anchor)

    reverse_time = deepcopy(guard)
    reverse_time["expires_at"] = "2026-08-05T23:59:59Z"
    _seal(reverse_time)
    with pytest.raises(AthanorError, match="expires before"):
        validate_patch_promotion_target_guard_v1(reverse_time)

    bad_fence = deepcopy(guard)
    bad_fence["fence_floor"] = 3
    _seal(bad_fence)
    with pytest.raises(AthanorError, match="fence floor"):
        validate_patch_promotion_target_guard_v1(bad_fence)


def test_none_target_guard_has_no_physical_fields() -> None:
    guard = _guard()
    guard.update({
        "state": "NONE", "backend_generation": None, "clock_anchor_evidence_sigil": None,
        "original_remaining_ns": None, "acquired_at": None, "expires_at": None,
    })
    _seal(guard)
    validate_patch_promotion_target_guard_v1(guard)

    invalid = deepcopy(guard)
    invalid["backend_generation"] = "generation-1"
    _seal(invalid)
    with pytest.raises(AthanorError, match="empty Target Guard"):
        validate_patch_promotion_target_guard_v1(invalid)
