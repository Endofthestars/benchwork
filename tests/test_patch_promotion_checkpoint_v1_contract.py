from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.patch_promotion_contracts import validate_patch_promotion_checkpoint_v1


SIGIL = "sha256:" + "a" * 64
FILE_SIGIL = "sha256:" + hashlib.sha256(b"x").hexdigest()


def _seal(checkpoint: dict[str, object]) -> dict[str, object]:
    checkpoint["checkpoint_sigil"] = content_sigil(
        {key: value for key, value in checkpoint.items() if key != "checkpoint_sigil"},
    )
    return checkpoint


def _checkpoint() -> dict[str, object]:
    blob = {"sigil": FILE_SIGIL, "size_bytes": 1, "media_type": "application/octet-stream"}
    return _seal({
        "schema_version": "patch-promotion-checkpoint/1.0",
        "checkpoint_id": "PCK-ONE",
        "attempt_id": "PAT-ONE",
        "target_id": "PT-ONE",
        "base": {"id": "PB-ONE", "sigil": SIGIL},
        "affected_paths": ["file.txt"],
        "entries": [{
            "path_bytes": "file.txt",
            "preimage": {"kind": "FILE", "blob_sigil": FILE_SIGIL, "size_bytes": 1, "executable": False},
            "checkpoint_blob": blob,
            "verification_sigil": SIGIL,
        }],
        "checkpoint_blobs": [blob],
        "created_at": "2026-08-06T00:00:00Z",
        "verified_at": "2026-08-06T00:00:01Z",
        "checkpoint_sigil": "",
    })


def test_checkpoint_checks_self_sigil_paths_and_exact_preimage_blobs() -> None:
    checkpoint = _checkpoint()
    validate_patch_promotion_checkpoint_v1(checkpoint)

    extra_path = deepcopy(checkpoint)
    extra_path["affected_paths"] = ["file.txt", "other.txt"]
    _seal(extra_path)
    with pytest.raises(AthanorError, match="exact affected path set"):
        validate_patch_promotion_checkpoint_v1(extra_path)

    wrong_blob = deepcopy(checkpoint)
    wrong_blob["entries"][0]["checkpoint_blob"]["size_bytes"] = 2
    wrong_blob["checkpoint_blobs"][0]["size_bytes"] = 2
    _seal(wrong_blob)
    with pytest.raises(AthanorError, match="Blob disagrees"):
        validate_patch_promotion_checkpoint_v1(wrong_blob)


def test_checkpoint_requires_no_blob_for_absent_or_directory_preimage() -> None:
    checkpoint = _checkpoint()
    checkpoint["entries"][0]["preimage"] = {"kind": "ABSENT"}
    checkpoint["entries"][0]["checkpoint_blob"] = None
    checkpoint["checkpoint_blobs"] = []
    _seal(checkpoint)
    validate_patch_promotion_checkpoint_v1(checkpoint)

    unexpected = deepcopy(checkpoint)
    unexpected["entries"][0]["checkpoint_blob"] = {
        "sigil": FILE_SIGIL, "size_bytes": 1, "media_type": "application/octet-stream",
    }
    unexpected["checkpoint_blobs"] = [unexpected["entries"][0]["checkpoint_blob"]]
    _seal(unexpected)
    with pytest.raises(AthanorError, match="Blob presence"):
        validate_patch_promotion_checkpoint_v1(unexpected)


def test_checkpoint_rejects_reverse_time() -> None:
    checkpoint = _checkpoint()
    checkpoint["verified_at"] = "2026-08-05T23:59:59Z"
    _seal(checkpoint)
    with pytest.raises(AthanorError, match="precedes"):
        validate_patch_promotion_checkpoint_v1(checkpoint)
