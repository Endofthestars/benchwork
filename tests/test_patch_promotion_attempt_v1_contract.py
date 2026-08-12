from __future__ import annotations

from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.patch_promotion_contracts import validate_patch_promotion_attempt_v1


SIGIL = "sha256:" + "a" * 64


def _seal(attempt: dict[str, object]) -> dict[str, object]:
    attempt["attempt_sigil"] = content_sigil({key: value for key, value in attempt.items() if key != "attempt_sigil"})
    return attempt


def _attempt() -> dict[str, object]:
    return _seal({
        "schema_version": "patch-promotion-attempt/1.0", "attempt_id": "PAT-ONE",
        "authorization": {"id": "PAU-ONE", "sigil": SIGIL}, "operation_sigil": SIGIL,
        "target": {"target_id": "PT-ONE", "target_class": "DIRECTORY",
                   "identity_profile": {"id": "PBIP-ONE", "sigil": SIGIL},
                   "root_identity": {"root_object_sigil": SIGIL, "root_generation": "generation", "topology_sigil": SIGIL},
                   "selection_authorization_sigil": SIGIL},
        "target_content_generation": "generation", "adapter": {"id": "PPA-ONE", "sigil": SIGIL},
        "mode": "FULL_TREE_ATOMIC_CAS", "created_at": "2026-08-06T00:00:00Z",
        "state": "CREATED", "revision": 0, "attempt_sigil": "",
    })


def test_promotion_attempt_checks_closed_wire_and_self_sigil() -> None:
    attempt = _attempt()
    validate_patch_promotion_attempt_v1(attempt)

    tampered = deepcopy(attempt)
    tampered["state"] = "MUTATING"
    with pytest.raises(AthanorError, match="self-Sigil"):
        validate_patch_promotion_attempt_v1(tampered)

    malformed = deepcopy(attempt)
    malformed["revision"] = True
    _seal(malformed)
    with pytest.raises(AthanorError, match="validation failed"):
        validate_patch_promotion_attempt_v1(malformed)
