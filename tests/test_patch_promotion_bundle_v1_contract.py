from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.patch_promotion_contracts import validate_patch_bundle_v1


SIGIL = "sha256:" + "a" * 64
FILE_SIGIL = "sha256:" + hashlib.sha256(b"x").hexdigest()


def _seal(bundle: dict[str, object]) -> dict[str, object]:
    bundle["bundle_sigil"] = content_sigil(
        {key: value for key, value in bundle.items() if key != "bundle_sigil"},
    )
    return bundle


def _bundle() -> dict[str, object]:
    payload = {
        "sigil": FILE_SIGIL,
        "size_bytes": 1,
        "media_type": "application/octet-stream",
    }
    return _seal({
        "schema_version": "patch-bundle/1.0",
        "bundle_id": "PBU-ONE",
        "base": {"id": "PB-ONE", "sigil": SIGIL},
        "postimage": {
            "identity_profile": {"id": "PBIP-ONE", "sigil": SIGIL},
            "tree": {
                "manifest_sigil": SIGIL,
                "root_entry_sigil": SIGIL,
                "entry_count": 1,
                "total_bytes": 1,
            },
            "manifest_blob": payload,
        },
        "operations": [{
            "path_bytes": "file.txt",
            "operation": "ADD",
            "preimage": {"kind": "ABSENT"},
            "postimage": {
                "kind": "FILE",
                "blob_sigil": FILE_SIGIL,
                "size_bytes": 1,
                "executable": False,
            },
            "payload_sigil": FILE_SIGIL,
        }],
        "payloads": [payload],
        "renderings": [],
        "attachments": [],
        "source": {
            "kind": "RETAINED_TERMINAL_SOURCE",
            "terminal_source_sigil": SIGIL,
            "execution_event_sigil": SIGIL,
            "frozen_at": "2026-08-06T00:00:00Z",
        },
        "agent_result_receipt": {
            "receipt_id": "RC-ONE",
            "receipt_sigil": SIGIL,
            "event_id": "CE-ONE",
            "event_body_sigil": SIGIL,
        },
        "limits": {
            "max_paths": 1,
            "max_blobs": 1,
            "max_total_bytes": 1,
            "max_payload_bytes": 1,
        },
        "bundle_sigil": "",
    })


def test_patch_bundle_checks_self_sigil_operations_and_exact_payloads() -> None:
    bundle = _bundle()
    validate_patch_bundle_v1(bundle)

    invalid_transition = deepcopy(bundle)
    invalid_transition["operations"][0]["operation"] = "MODIFY"  # type: ignore[index]
    _seal(invalid_transition)
    with pytest.raises(AthanorError, match="operation disagrees"):
        validate_patch_bundle_v1(invalid_transition)

    missing_payload = deepcopy(bundle)
    missing_payload["payloads"] = []
    _seal(missing_payload)
    with pytest.raises(AthanorError, match="exact postimage payload set"):
        validate_patch_bundle_v1(missing_payload)


def test_patch_bundle_checks_payload_limits_and_blob_union_metadata() -> None:
    bundle = _bundle()
    over_limit = deepcopy(bundle)
    over_limit["limits"]["max_payload_bytes"] = 0  # type: ignore[index]
    _seal(over_limit)
    with pytest.raises(AthanorError, match="max_payload_bytes"):
        validate_patch_bundle_v1(over_limit)

    inconsistent = deepcopy(bundle)
    inconsistent["attachments"] = [{  # type: ignore[index]
        "sigil": FILE_SIGIL,
        "size_bytes": 2,
        "media_type": "application/octet-stream",
    }]
    inconsistent["limits"]["max_total_bytes"] = 3  # type: ignore[index]
    _seal(inconsistent)
    with pytest.raises(AthanorError, match="inconsistent metadata"):
        validate_patch_bundle_v1(inconsistent)


def test_patch_bundle_recomputes_symlink_target_identity() -> None:
    bundle = _bundle()
    target = "target"
    target_sigil = "sha256:" + hashlib.sha256(target.encode()).hexdigest()
    bundle["operations"] = [{  # type: ignore[index]
        "path_bytes": "link",
        "operation": "ADD",
        "preimage": {"kind": "ABSENT"},
        "postimage": {"kind": "SYMLINK", "target": target, "target_sigil": target_sigil},
        "payload_sigil": target_sigil,
    }]
    bundle["payloads"] = [{  # type: ignore[index]
        "sigil": target_sigil,
        "size_bytes": len(target.encode()),
        "media_type": "application/octet-stream",
    }]
    bundle["limits"] = {"max_paths": 1, "max_blobs": 1, "max_total_bytes": 6, "max_payload_bytes": 6}
    _seal(bundle)
    validate_patch_bundle_v1(bundle)

    wrong = deepcopy(bundle)
    wrong["operations"][0]["postimage"]["target_sigil"] = SIGIL  # type: ignore[index]
    wrong["operations"][0]["payload_sigil"] = SIGIL  # type: ignore[index]
    wrong["payloads"][0]["sigil"] = SIGIL  # type: ignore[index]
    _seal(wrong)
    with pytest.raises(AthanorError, match="target Sigil"):
        validate_patch_bundle_v1(wrong)
