import json
from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.artifact_storage_contracts import (
    load_artifact_storage_journal_event_v1,
    load_artifact_storage_journal_head_v1,
    load_artifact_storage_state_v1,
    require_artifact_storage_journal_replay_authority_v1,
    require_artifact_storage_runtime_authority_v1,
    validate_artifact_storage_journal_event_v1,
    validate_artifact_storage_journal_head_supplied_event_v1,
    validate_artifact_storage_journal_head_supplied_prefix_v1,
    validate_artifact_storage_journal_head_v1,
    validate_artifact_storage_journal_prefix_v1,
    validate_artifact_storage_head_supplied_state_v1,
    validate_artifact_storage_state_v1,
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


def _next_event(previous: dict[str, object]) -> dict[str, object]:
    event = _event()
    event.update({
        "event_id": "SE-TWO", "sequence": 2, "recorded_at": "2026-08-06T00:00:01Z",
        "previous_event_sigil": previous["event_sigil"],
    })
    event["event_sigil"] = content_sigil({
        key: member for key, member in event.items() if key != "event_sigil"
    })
    return event


def _initial_event() -> dict[str, object]:
    event = _event()
    event.update({
        "event_type": "storage.initialized",
        "payload": {
            "project_id": "PROJECT", "storage_format_version": "1.0",
            "backend": {"schema_version": "backend/1.0", "record_id": "BACKEND", "record_sigil": SIGIL},
            "conformance_profile_id": "PROFILE", "conformance_suite_sigil": SIGIL,
            "quota_snapshots": [], "tail_recovery": None,
            "clock": {
                "utc": STAMP, "monotonic_anchor_id": "CLOCK", "monotonic_ticks": 0,
                "monotonic_frequency_hz": 1, "uncertainty_micros": 0,
                "observation_sigil": SIGIL,
            },
        },
    })
    event["event_sigil"] = content_sigil({
        key: member for key, member in event.items() if key != "event_sigil"
    })
    return event


def _state() -> dict[str, object]:
    quota_pairs = (
        ("JOURNAL", "JOURNAL_BYTE"), ("CONTROL_RECORD", "CONTROL_RECORD_BYTE"),
        ("STAGING", "BYTE"), ("STAGING", "OBJECT"), ("QUARANTINE", "BYTE"),
        ("QUARANTINE", "OBJECT"), ("COMMITTED", "BYTE"), ("COMMITTED", "OBJECT"),
        ("MATERIALIZATION", "BYTE"), ("MATERIALIZATION", "OBJECT"),
        ("STREAM", "STREAM"), ("INODE", "INODE"),
    )
    clock = {
        "utc": STAMP, "monotonic_anchor_id": "CLOCK", "monotonic_ticks": 0,
        "monotonic_frequency_hz": 1, "uncertainty_micros": 0, "observation_sigil": SIGIL,
    }
    state: dict[str, object] = {
        "schema_version": "artifact-storage-state/1.0", "journal_id": "SJ-ONE",
        "storage_format_version": "1.0", "project_id": "PROJECT", "backend_profile_id": "BACKEND",
        "backend_profile_sigil": SIGIL, "conformance_profile_id": "PROFILE",
        "conformance_suite_sigil": SIGIL, "store_status": "INITIALIZING",
        "active_recovery_id": None, "recovery_origin_status": None, "clock_status": "TRUSTED",
        "clock_anchor": clock, "current_epoch": 1, "applied_event_count": 1,
        "last_event_sigil": SIGIL_B,
        "recoveries": [], "blobs": [], "replicas": [], "transfer_requests": [],
        "transfer_attempts": [], "materializations": [], "quarantines": [], "provenance": [],
        "provenance_policies": [], "retention_policies": [], "holds": [], "reference_sets": [],
        "legacy_v1_protections": [], "gc_plans": [], "canonical_reference_intents": [],
        "dispositions": [], "quota_reservations": [], "open_intents": [], "incidents": [],
        "availability_counters": {
            "available_blobs": 0, "degraded_blobs": 0, "unavailable_blobs": 0,
            "incident_blobs": 0,
        }, "quota_counters": [
            {"quota_class": kind, "dimension": dimension, "limit": 0, "used": 0,
             "reserved": 0, "pressure_state": "CLEAR"}
            for kind, dimension in quota_pairs
        ], "state_sigil": "",
    }
    state["state_sigil"] = content_sigil({
        key: member for key, member in state.items() if key != "state_sigil"
    })
    return state


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


def test_storage_journal_prefix_checks_chain_sequence_and_fixed_head() -> None:
    first = _initial_event()
    second = _next_event(first)
    head = _head(second)
    head.update({"event_count": 2, "last_sequence": 2})
    validate_artifact_storage_journal_prefix_v1([first, second])
    validate_artifact_storage_journal_head_supplied_prefix_v1(head, [first, second], SIGIL)

    broken_chain = deepcopy(second)
    broken_chain["previous_event_sigil"] = SIGIL_B
    broken_chain["event_sigil"] = content_sigil({
        key: member for key, member in broken_chain.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="chain Sigil"):
        validate_artifact_storage_journal_prefix_v1([first, broken_chain])

    gap = deepcopy(second)
    gap["sequence"] = 3
    gap["event_sigil"] = content_sigil({
        key: member for key, member in gap.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="not contiguous"):
        validate_artifact_storage_journal_prefix_v1([first, gap])

    not_initialized = _event()
    with pytest.raises(AthanorError, match="does not start"):
        validate_artifact_storage_journal_prefix_v1([not_initialized])

    old_epoch = deepcopy(second)
    old_epoch["epoch"] = 0
    old_epoch["event_sigil"] = content_sigil({
        key: member for key, member in old_epoch.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError):
        validate_artifact_storage_journal_prefix_v1([first, old_epoch])


def test_storage_state_checks_self_identity_order_and_head_binding() -> None:
    state = _state()
    validate_artifact_storage_state_v1(state)
    assert load_artifact_storage_state_v1(json.dumps(state)) == state
    head = _head(_event())
    head.update({
        "last_event_sigil": state["last_event_sigil"],
        "state_sigil": state["state_sigil"],
    })
    validate_artifact_storage_head_supplied_state_v1(head, state)

    stale = deepcopy(state)
    stale["project_id"] = "CHANGED"
    with pytest.raises(AthanorError, match="self-Sigil"):
        validate_artifact_storage_state_v1(stale)

    wrong_head = deepcopy(head)
    wrong_head["current_epoch"] = 2
    with pytest.raises(AthanorError, match="contradicts supplied State"):
        validate_artifact_storage_head_supplied_state_v1(wrong_head, state)

    ordered = deepcopy(state)
    ordered["transfer_requests"] = [
        {"transfer_id": "ST-ONE", "request_record_sigil": SIGIL, "state": "ACTIVE",
         "attempt_ids": [], "selected_attempt_id": None, "revision": 1,
         "last_event_sigil": SIGIL},
        {"transfer_id": "ST-TWO", "request_record_sigil": SIGIL, "state": "ACTIVE",
         "attempt_ids": [], "selected_attempt_id": None, "revision": 1,
         "last_event_sigil": SIGIL},
    ]
    ordered["state_sigil"] = content_sigil({
        key: member for key, member in ordered.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(ordered)

    out_of_order = deepcopy(ordered)
    out_of_order["transfer_requests"].reverse()
    out_of_order["state_sigil"] = content_sigil({
        key: member for key, member in out_of_order.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="identity sorted"):
        validate_artifact_storage_state_v1(out_of_order)

    duplicate_identity = deepcopy(ordered)
    duplicate_identity["transfer_requests"][1]["transfer_id"] = "ST-ONE"
    duplicate_identity["state_sigil"] = content_sigil({
        key: member for key, member in duplicate_identity.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="non-unique|identities must be unique"):
        validate_artifact_storage_state_v1(duplicate_identity)

    object_ref = {
        "backend_id": "BACKEND", "object_identity_sigil": SIGIL, "locator_sigil": SIGIL,
        "generation": "GENERATION", "size_bytes": 0, "blob_sigil": None,
    }
    open_ids = deepcopy(state)
    open_ids["open_intents"] = [
        {"intent_kind": "MATERIALIZATION_COMMIT", "intent_id": "INTENT", "owner_id": "SM-ONE",
         "source_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
                          "event_sigil": SIGIL}, "intent_sigil": SIGIL, "revision": 1,
         "last_event_sigil": SIGIL, "authorization_expires_at": None,
         "staging_object": object_ref, "target_object": object_ref},
        {"intent_kind": "TRANSFER_COMMIT", "intent_id": "INTENT", "owner_id": "SA-ONE",
         "source_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
                          "event_sigil": SIGIL}, "intent_sigil": SIGIL, "revision": 1,
         "last_event_sigil": SIGIL, "authorization_expires_at": None,
         "staging_object": object_ref, "target_object": object_ref},
    ]
    open_ids["state_sigil"] = content_sigil({
        key: member for key, member in open_ids.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="globally unique"):
        validate_artifact_storage_state_v1(open_ids)

    wrong_open_sigil = deepcopy(open_ids)
    wrong_open_sigil["open_intents"] = [wrong_open_sigil["open_intents"][0]]
    wrong_open_sigil["open_intents"][0]["intent_sigil"] = SIGIL_B
    wrong_open_sigil["state_sigil"] = content_sigil({
        key: member for key, member in wrong_open_sigil.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Open Intent Sigils disagree"):
        validate_artifact_storage_state_v1(wrong_open_sigil)

    selected_unknown = deepcopy(ordered)
    selected_unknown["transfer_requests"][0]["selected_attempt_id"] = "SA-UNKNOWN"
    selected_unknown["state_sigil"] = content_sigil({
        key: member for key, member in selected_unknown.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="selects an unknown Attempt"):
        validate_artifact_storage_state_v1(selected_unknown)

    replica_state = deepcopy(state)
    replica = {
        "schema_version": "artifact-replica/1.0", "replica_id": "SR-ONE",
        "blob_sigil": SIGIL, "size_bytes": 0,
        "backend": {"backend_id": "BACKEND", "backend_profile_version": "1.0",
                    "backend_profile_sigil": SIGIL},
        "object": {"backend_id": "BACKEND", "object_identity_sigil": SIGIL,
                   "locator_sigil": SIGIL, "generation": "GENERATION", "size_bytes": 0,
                   "blob_sigil": SIGIL}, "state": "COMMITTING",
        "created_by_transfer_attempt_id": "SA-ONE", "verification": None,
        "retention_policy_ids": [], "revision": 1, "record_sigil": "",
    }
    replica["record_sigil"] = content_sigil({
        key: member for key, member in replica.items() if key != "record_sigil"
    })
    replica_state["replicas"] = [{"record": replica, "last_event_sigil": SIGIL}]
    replica_state["state_sigil"] = content_sigil({
        key: member for key, member in replica_state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(replica_state)

    wrong_replica = deepcopy(replica_state)
    wrong_replica["replicas"][0]["record"]["object"]["size_bytes"] = 1
    wrong_replica["replicas"][0]["record"]["record_sigil"] = content_sigil({
        key: member for key, member in wrong_replica["replicas"][0]["record"].items()
        if key != "record_sigil"
    })
    wrong_replica["state_sigil"] = content_sigil({
        key: member for key, member in wrong_replica.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Replica object disagrees"):
        validate_artifact_storage_state_v1(wrong_replica)
