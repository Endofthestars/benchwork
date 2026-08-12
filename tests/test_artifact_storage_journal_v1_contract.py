import json
from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.artifact_storage_contracts import (
    derive_artifact_storage_reference_intent_id_v1,
    derive_artifact_storage_reference_set_id_v1,
    load_artifact_storage_journal_event_v1,
    load_artifact_storage_journal_head_v1,
    load_artifact_storage_disposition_v1,
    load_artifact_gc_plan_v1,
    load_artifact_provenance_v1,
    load_artifact_provenance_policy_v1,
    load_artifact_storage_backend_v1,
    load_artifact_storage_doctor_report_v1,
    load_artifact_transfer_v1,
    load_artifact_retention_policy_v1,
    load_artifact_storage_legacy_protection_v1,
    load_artifact_storage_recovery_marker_v1,
    load_artifact_storage_reference_intent_v1,
    load_artifact_storage_reference_set_v1,
    load_artifact_storage_tail_evidence_v1,
    load_artifact_storage_state_v1,
    require_artifact_storage_journal_replay_authority_v1,
    require_artifact_storage_runtime_authority_v1,
    replay_artifact_storage_initial_prefix_v1,
    replay_artifact_storage_journal_prefix_v1,
    validate_artifact_storage_journal_event_v1,
    validate_artifact_storage_journal_head_supplied_event_v1,
    validate_artifact_storage_journal_head_supplied_prefix_v1,
    validate_artifact_storage_journal_head_v1,
    validate_artifact_storage_journal_prefix_v1,
    validate_artifact_storage_disposition_v1,
    validate_artifact_gc_plan_v1,
    validate_artifact_provenance_v1,
    validate_artifact_provenance_policy_v1,
    validate_artifact_storage_state_supplied_provenance_policies_v1,
    validate_artifact_storage_backend_v1,
    validate_artifact_storage_doctor_report_v1,
    validate_artifact_transfer_v1,
    validate_artifact_storage_state_supplied_transfers_v1,
    validate_artifact_storage_state_supplied_transfer_attempts_v1,
    validate_artifact_storage_state_supplied_provenance_v1,
    validate_artifact_retention_policy_v1,
    validate_artifact_storage_state_supplied_retention_policies_v1,
    validate_artifact_storage_legacy_protection_v1,
    validate_artifact_storage_recovery_marker_v1,
    validate_artifact_storage_head_supplied_state_v1,
    validate_artifact_storage_state_v1,
    validate_artifact_storage_reference_intent_v1,
    validate_artifact_storage_reference_set_v1,
    validate_artifact_storage_state_supplied_control_records_v1,
    validate_artifact_storage_tail_evidence_v1,
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


def _initial_replay_event() -> dict[str, object]:
    event = _initial_event()
    pairs = (
        ("JOURNAL", "JOURNAL_BYTE"), ("CONTROL_RECORD", "CONTROL_RECORD_BYTE"),
        ("STAGING", "BYTE"), ("STAGING", "OBJECT"), ("QUARANTINE", "BYTE"),
        ("QUARANTINE", "OBJECT"), ("COMMITTED", "BYTE"), ("COMMITTED", "OBJECT"),
        ("MATERIALIZATION", "BYTE"), ("MATERIALIZATION", "OBJECT"),
        ("STREAM", "STREAM"), ("INODE", "INODE"),
    )
    snapshots = [
        {"quota_class": quota_class, "dimension": dimension, "limit": 0, "used": 0,
         "reserved": 0, "pressure_state": "CLEAR"}
        for quota_class, dimension in pairs
    ]
    event["payload"]["quota_snapshots"] = snapshots  # type: ignore[index]
    event["quota_effects"] = [{"kind": "INITIALIZE", "snapshot": snapshot} for snapshot in snapshots]
    event["entity_revisions"] = [
        {"entity_type": "STORE", "entity_id": "STORE", "previous_revision": None, "next_revision": 1},
        *[
            {"entity_type": "QUOTA", "entity_id": f"quota-counter:{quota_class}:{dimension}",
             "previous_revision": None, "next_revision": 1}
            for quota_class, dimension in pairs
        ],
    ]
    event["event_sigil"] = content_sigil({key: value for key, value in event.items() if key != "event_sigil"})
    return event


def test_storage_initial_replay_builds_the_exact_empty_state() -> None:
    event = _initial_replay_event()
    state = replay_artifact_storage_initial_prefix_v1([event])
    assert state["journal_id"] == event["journal_id"]
    assert state["store_status"] == "INITIALIZING"
    assert state["current_epoch"] == 1
    assert state["last_event_sigil"] == event["event_sigil"]
    assert state["quota_counters"] == event["payload"]["quota_snapshots"]
    assert state["blobs"] == []

    wrong_effects = deepcopy(event)
    wrong_effects["quota_effects"] = []
    wrong_effects["event_sigil"] = content_sigil({
        key: value for key, value in wrong_effects.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="quota effects"):
        replay_artifact_storage_initial_prefix_v1([wrong_effects])

    recovered = deepcopy(event)
    recovered["payload"]["tail_recovery"] = {"recovery_id": "RECOVERY"}  # type: ignore[index]
    recovered["event_sigil"] = content_sigil({
        key: value for key, value in recovered.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="validation failed|tail recovery"):
        replay_artifact_storage_initial_prefix_v1([recovered])


def test_storage_replay_activates_the_empty_initialized_store() -> None:
    initial = _initial_replay_event()
    activation = _next_event(initial)
    activation["event_type"] = "storage.activation_completed"
    activation["entity_revisions"] = [{
        "entity_type": "STORE", "entity_id": "STORE", "previous_revision": 1, "next_revision": 2,
    }]
    activation["payload"] = {
        "legacy_protection_ids": [], "activation_evidence_sigil": SIGIL,
        "clock": initial["payload"]["clock"],
    }
    activation["quota_effects"] = []
    activation["event_sigil"] = content_sigil({
        key: value for key, value in activation.items() if key != "event_sigil"
    })
    state = replay_artifact_storage_journal_prefix_v1([initial, activation])
    assert state["store_status"] == "ACTIVE"
    assert state["applied_event_count"] == 2
    assert state["last_event_sigil"] == activation["event_sigil"]

    wrong_revision = deepcopy(activation)
    wrong_revision["entity_revisions"][0]["next_revision"] = 3
    wrong_revision["event_sigil"] = content_sigil({
        key: value for key, value in wrong_revision.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="invalid Store revision"):
        replay_artifact_storage_journal_prefix_v1([initial, wrong_revision])


def test_storage_replay_retains_failed_legacy_protection_and_blocks_activation() -> None:
    initial = _initial_replay_event()
    failed = _next_event(initial)
    failed["event_type"] = "legacy_v1.protection_failed"
    failed["entity_revisions"] = [{
        "entity_type": "LEGACY_PROTECTION", "entity_id": "PROTECTION",
        "previous_revision": None, "next_revision": 1,
    }]
    failed["quota_effects"] = []
    failed["payload"] = {
        "protection_id": "PROTECTION", "artifact_id": "ARTIFACT",
        "receipt_sigil": None,
        "reason": {"code": "BACKEND_UNAVAILABLE", "evidence_sigils": []},
    }
    failed["event_sigil"] = content_sigil({
        key: value for key, value in failed.items() if key != "event_sigil"
    })
    failed_state = replay_artifact_storage_journal_prefix_v1([initial, failed])
    assert failed_state["legacy_v1_protections"] == [{
        "protection_id": "PROTECTION", "artifact_id": "ARTIFACT",
        "state": "FAILED", "record": None, "receipt_sigil": None,
        "reason": failed["payload"]["reason"], "revision": 1,
        "last_event_sigil": failed["event_sigil"],
    }]

    activation = _next_event(failed)
    activation["event_id"] = "SE-THREE"
    activation["sequence"] = 3
    activation["event_type"] = "storage.activation_completed"
    activation["entity_revisions"] = [{
        "entity_type": "STORE", "entity_id": "STORE", "previous_revision": 1, "next_revision": 2,
    }]
    activation["quota_effects"] = []
    activation["payload"] = {
        "legacy_protection_ids": ["PROTECTION"], "activation_evidence_sigil": SIGIL,
        "clock": initial["payload"]["clock"],
    }
    activation["event_sigil"] = content_sigil({
        key: value for key, value in activation.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="failed legacy protection"):
        replay_artifact_storage_journal_prefix_v1([initial, failed, activation])

    duplicate = deepcopy(failed)
    duplicate["event_id"] = "SE-FOUR"
    duplicate["sequence"] = 3
    duplicate["previous_event_sigil"] = failed["event_sigil"]
    duplicate["event_sigil"] = content_sigil({
        key: value for key, value in duplicate.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="disagrees"):
        replay_artifact_storage_journal_prefix_v1([initial, failed, duplicate])


def test_storage_replay_completes_an_empty_recovery_to_its_frozen_origin() -> None:
    initial = _initial_replay_event()
    activation = _next_event(initial)
    activation["event_type"] = "storage.activation_completed"
    activation["entity_revisions"] = [{
        "entity_type": "STORE", "entity_id": "STORE",
        "previous_revision": 1, "next_revision": 2,
    }]
    activation["payload"] = {
        "legacy_protection_ids": [], "activation_evidence_sigil": SIGIL,
        "clock": initial["payload"]["clock"],
    }
    activation["quota_effects"] = []
    activation["event_sigil"] = content_sigil({
        key: value for key, value in activation.items() if key != "event_sigil"
    })
    started = _next_event(activation)
    started.update({
        "event_id": "SE-THREE", "sequence": 3, "event_type": "storage.recovery_started",
        "epoch": 2, "recorded_at": "2026-08-06T00:00:02Z",
        "observed_at": "2026-08-06T00:00:01Z",
        "entity_revisions": [{
            "entity_type": "STORE", "entity_id": "STORE",
            "previous_revision": 2, "next_revision": 3,
        }],
        "quota_effects": [],
        "payload": {
            "recovery_id": "RECOVERY", "origin_status": "ACTIVE",
            "previous_epoch": 1, "next_epoch": 2, "tail_recovery": None,
            "open_intent_ids": [],
            "clock": {**initial["payload"]["clock"], "utc": "2026-08-06T00:00:01Z"},
        },
    })
    started["event_sigil"] = content_sigil({
        key: value for key, value in started.items() if key != "event_sigil"
    })
    recovering = replay_artifact_storage_journal_prefix_v1([initial, activation, started])
    assert recovering["store_status"] == "RECOVERING"
    assert recovering["active_recovery_id"] == "RECOVERY"
    restarted = _next_event(started)
    restarted.update({
        "event_id": "SE-RESTART", "sequence": 4, "event_type": "storage.epoch_started",
        "epoch": 3, "recorded_at": "2026-08-06T00:00:03Z",
        "observed_at": "2026-08-06T00:00:02Z",
        "entity_revisions": [{
            "entity_type": "STORE", "entity_id": "STORE",
            "previous_revision": 3, "next_revision": 4,
        }], "quota_effects": [],
        "payload": {
            "previous_epoch": 2, "next_epoch": 3, "active_recovery_id": "RECOVERY",
            "tail_recovery": None,
            "reason": {"code": "BACKEND_UNAVAILABLE", "evidence_sigils": []},
            "clock": {**started["payload"]["clock"], "utc": "2026-08-06T00:00:02Z"},
        },
    })
    restarted["event_sigil"] = content_sigil({
        key: value for key, value in restarted.items() if key != "event_sigil"
    })
    restarted_state = replay_artifact_storage_journal_prefix_v1(
        [initial, activation, started, restarted]
    )
    assert restarted_state["current_epoch"] == 3
    assert restarted_state["recoveries"][0]["epoch_ids"] == [2, 3]
    completed = _next_event(started)
    completed.update({
        "event_id": "SE-FOUR", "sequence": 4, "event_type": "storage.recovery_completed",
        "epoch": 2, "recorded_at": "2026-08-06T00:00:03Z",
        "observed_at": "2026-08-06T00:00:02Z",
        "entity_revisions": [{
            "entity_type": "STORE", "entity_id": "STORE",
            "previous_revision": 3, "next_revision": 4,
        }],
        "quota_effects": [],
        "payload": {
            "recovery_id": "RECOVERY", "epoch": 2, "resume_status": "ACTIVE",
            "resolved_intent_ids": [], "evidence_sigils": [],
            "clock": {**started["payload"]["clock"], "utc": "2026-08-06T00:00:02Z"},
        },
    })
    completed["event_sigil"] = content_sigil({
        key: value for key, value in completed.items() if key != "event_sigil"
    })
    state = replay_artifact_storage_journal_prefix_v1(
        [initial, activation, started, completed]
    )
    assert state["store_status"] == "ACTIVE"
    assert state["active_recovery_id"] is None
    assert state["recoveries"][0]["state"] == "COMPLETED"

    wrong_origin = deepcopy(completed)
    wrong_origin["payload"]["resume_status"] = "INITIALIZING"
    wrong_origin["event_sigil"] = content_sigil({
        key: value for key, value in wrong_origin.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="recovery completion"):
        replay_artifact_storage_journal_prefix_v1(
            [initial, activation, started, wrong_origin]
        )

    later_rejection = _next_event(completed)
    later_rejection.update({
        "event_id": "SE-FIVE", "sequence": 5,
        "recorded_at": "2026-08-06T00:00:04Z", "epoch": 2,
        "entity_revisions": [], "quota_effects": [], "observed_at": None,
        "payload": {
            "message_class": "test", "message_sigil": None,
            "reason": {"code": "BACKEND_UNAVAILABLE", "evidence_sigils": []},
        },
    })
    later_rejection["event_sigil"] = content_sigil({
        key: value for key, value in later_rejection.items() if key != "event_sigil"
    })
    assert replay_artifact_storage_journal_prefix_v1(
        [initial, activation, started, completed, later_rejection]
    )["applied_event_count"] == 5


def test_storage_replay_applies_empty_clock_gate_round_trip() -> None:
    initial = _initial_replay_event()
    activation = _next_event(initial)
    activation["event_type"] = "storage.activation_completed"
    activation["entity_revisions"] = [{
        "entity_type": "STORE", "entity_id": "STORE", "previous_revision": 1, "next_revision": 2,
    }]
    activation["payload"] = {"legacy_protection_ids": [], "activation_evidence_sigil": SIGIL, "clock": initial["payload"]["clock"]}
    activation["quota_effects"] = []
    activation["event_sigil"] = content_sigil({key: value for key, value in activation.items() if key != "event_sigil"})
    uncertain = _next_event(activation)
    uncertain["event_type"] = "storage.clock_uncertain"
    uncertain["event_id"] = "SE-THREE"
    uncertain["sequence"] = 3
    uncertain["recorded_at"] = "2026-08-06T00:00:02Z"
    detected_clock = {**initial["payload"]["clock"], "utc": "2026-08-06T00:00:01Z"}
    uncertain.update({
        "observed_at": detected_clock["utc"],
        "entity_revisions": [{"entity_type": "STORE", "entity_id": "STORE", "previous_revision": 2, "next_revision": 3}],
        "quota_effects": [],
        "payload": {"previous_clock": initial["payload"]["clock"], "detected_clock": detected_clock,
                    "divergence_micros": 1, "affected_reservation_ids": [],
                    "reason": {"code": "CLOCK_UNCERTAIN", "evidence_sigils": []}},
    })
    uncertain["event_sigil"] = content_sigil({key: value for key, value in uncertain.items() if key != "event_sigil"})
    restored = _next_event(uncertain)
    restored["event_type"] = "storage.clock_restored"
    restored["event_id"] = "SE-FOUR"
    restored["sequence"] = 4
    restored["recorded_at"] = "2026-08-06T00:00:03Z"
    restored.update({
        "observed_at": "2026-08-06T00:00:02Z",
        "entity_revisions": [{"entity_type": "STORE", "entity_id": "STORE", "previous_revision": 3, "next_revision": 4}],
        "quota_effects": [],
        "payload": {"previous_observation_sigil": detected_clock["observation_sigil"],
                    "new_clock": {**detected_clock, "utc": "2026-08-06T00:00:02Z"},
                    "expired_entity_ids": [], "evidence_sigils": []},
    })
    restored["event_sigil"] = content_sigil({key: value for key, value in restored.items() if key != "event_sigil"})
    uncertain_state = replay_artifact_storage_journal_prefix_v1([initial, activation, uncertain])
    assert uncertain_state["clock_status"] == "UNCERTAIN"
    state = replay_artifact_storage_journal_prefix_v1([initial, activation, uncertain, restored])
    assert state["clock_status"] == "TRUSTED"
    assert state["clock_anchor"] == restored["payload"]["new_clock"]
    head = _head(restored)
    head.update({"event_count": 4, "last_sequence": 4, "current_epoch": 1, "state_sigil": state["state_sigil"]})
    replay_artifact_storage_journal_prefix_v1([initial, activation, uncertain, restored], head=head)

    wrong_anchor = deepcopy(uncertain)
    wrong_anchor["payload"]["previous_clock"]["utc"] = "2026-08-06T00:00:01Z"
    wrong_anchor["event_sigil"] = content_sigil({key: value for key, value in wrong_anchor.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="clock uncertainty"):
        replay_artifact_storage_journal_prefix_v1([initial, activation, wrong_anchor])


def test_storage_replay_advances_a_no_recovery_epoch() -> None:
    initial = _initial_replay_event()
    activation = _next_event(initial)
    activation["event_type"] = "storage.activation_completed"
    activation["entity_revisions"] = [{"entity_type": "STORE", "entity_id": "STORE", "previous_revision": 1, "next_revision": 2}]
    activation["payload"] = {"legacy_protection_ids": [], "activation_evidence_sigil": SIGIL, "clock": initial["payload"]["clock"]}
    activation["quota_effects"] = []
    activation["event_sigil"] = content_sigil({key: value for key, value in activation.items() if key != "event_sigil"})
    epoch = _next_event(activation)
    epoch.update({
        "event_id": "SE-THREE", "sequence": 3, "event_type": "storage.epoch_started", "epoch": 2,
        "recorded_at": "2026-08-06T00:00:02Z", "observed_at": "2026-08-06T00:00:01Z",
        "entity_revisions": [{"entity_type": "STORE", "entity_id": "STORE", "previous_revision": 2, "next_revision": 3}],
        "quota_effects": [],
        "payload": {"previous_epoch": 1, "next_epoch": 2, "active_recovery_id": None,
                    "tail_recovery": None, "reason": {"code": "BACKEND_UNAVAILABLE", "evidence_sigils": []},
                    "clock": {**initial["payload"]["clock"], "utc": "2026-08-06T00:00:01Z"}},
    })
    epoch["event_sigil"] = content_sigil({key: value for key, value in epoch.items() if key != "event_sigil"})
    state = replay_artifact_storage_journal_prefix_v1([initial, activation, epoch])
    assert state["current_epoch"] == 2
    assert state["clock_anchor"] == epoch["payload"]["clock"]

    wrong_epoch = deepcopy(epoch)
    wrong_epoch["payload"]["next_epoch"] = 3
    wrong_epoch["event_sigil"] = content_sigil({key: value for key, value in wrong_epoch.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="epoch Event"):
        replay_artifact_storage_journal_prefix_v1([initial, activation, wrong_epoch])


def test_storage_replay_records_an_auditable_rejected_message() -> None:
    initial = _initial_replay_event()
    activation = _next_event(initial)
    activation["event_type"] = "storage.activation_completed"
    activation["entity_revisions"] = [{"entity_type": "STORE", "entity_id": "STORE", "previous_revision": 1, "next_revision": 2}]
    activation["payload"] = {"legacy_protection_ids": [], "activation_evidence_sigil": SIGIL, "clock": initial["payload"]["clock"]}
    activation["quota_effects"] = []
    activation["event_sigil"] = content_sigil({key: value for key, value in activation.items() if key != "event_sigil"})
    rejected = _next_event(activation)
    rejected.update({
        "event_id": "SE-THREE", "sequence": 3, "event_type": "storage.message_rejected",
        "recorded_at": "2026-08-06T00:00:02Z", "observed_at": None, "entity_revisions": [], "quota_effects": [],
        "causation_event_id": None, "idempotency_key_sigil": None,
        "payload": {"message_class": "untrusted", "message_sigil": None,
                    "reason": {"code": "INVALID_MESSAGE", "evidence_sigils": []}},
    })
    rejected["event_sigil"] = content_sigil({key: value for key, value in rejected.items() if key != "event_sigil"})
    state = replay_artifact_storage_journal_prefix_v1([initial, activation, rejected])
    assert state["applied_event_count"] == 3
    assert state["last_event_sigil"] == rejected["event_sigil"]
    assert state["blobs"] == []

    unexpected_effect = deepcopy(rejected)
    unexpected_effect["quota_effects"] = [{"kind": "INITIALIZE", "snapshot": initial["payload"]["quota_snapshots"][0]}]
    unexpected_effect["event_sigil"] = content_sigil({key: value for key, value in unexpected_effect.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="message rejection Event"):
        replay_artifact_storage_journal_prefix_v1([initial, activation, unexpected_effect])


def _reference_set() -> dict[str, object]:
    reference_set: dict[str, object] = {
        "schema_version": "artifact-storage-reference-set/1.0", "reference_set_id": "",
        "source": {"kind": "CANONICAL_OBJECT", "identity": "SOURCE",
                   "schema_version": "artifact/1.0", "sigil": SIGIL},
        "extractor": {"extractor_id": "EXTRACTOR", "extractor_version": "1.0",
                      "extractor_sigil": SIGIL}, "edges": [],
        "validation": {"validator_id": "VALIDATOR", "validator_version": "1.0",
                       "validator_sigil": SIGIL, "source_validation_sigil": SIGIL,
                       "evidence_sigils": [SIGIL]}, "registration_event_id": "",
        "created_at": STAMP, "reference_set_sigil": "",
    }
    reference_set["reference_set_id"] = derive_artifact_storage_reference_set_id_v1(reference_set)
    reference_set["registration_event_id"] = "SE-" + content_sigil([
        "artifact-storage-reference-set-registration-event-id/1.0",
        reference_set["reference_set_id"],
    ]).removeprefix("sha256:").upper()
    reference_set["reference_set_sigil"] = content_sigil({
        key: member for key, member in reference_set.items() if key != "reference_set_sigil"
    })
    return reference_set


def _legacy_protection() -> dict[str, object]:
    protection: dict[str, object] = {
        "schema_version": "artifact-storage-legacy-protection/1.0", "protection_id": "PROTECTION",
        "artifact_id": "ARTIFACT", "program_id": "PROGRAM", "artifact_receipt_sigil": SIGIL,
        "recorded_uri_sigil": SIGIL, "lexical_identity_sigil": SIGIL,
        "resolved_file_identity_sigil": SIGIL, "anchor_observation_sigil": SIGIL,
        "blob": {"blob_sigil": SIGIL, "size_bytes": 1}, "protected_replica_id": "SR-ONE",
        "transfer": {"transfer_id": "ST-ONE", "transfer_attempt_id": "SA-ONE",
                     "request_record_sigil": SIGIL, "attempt_record_sigil": SIGIL,
                     "terminal_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE",
                                        "sequence": 1, "event_sigil": SIGIL}},
        "verification": {"method": "FULL_READBACK_SHA256", "evidence_sigil": SIGIL,
                         "verified_at": STAMP, "next_due_at": None},
        "exclusion": {"anchor_disposition": "PERMANENTLY_EXCLUDED",
                      "managed_copy_gc": "PERMANENTLY_PROTECTED", "policy_id": "SP-ONE",
                      "authorization_sigil": SIGIL}, "registered_at": STAMP, "record_sigil": "",
    }
    protection["record_sigil"] = content_sigil({
        key: member for key, member in protection.items() if key != "record_sigil"
    })
    return protection


def _tail_evidence() -> dict[str, object]:
    evidence: dict[str, object] = {
        "schema_version": "artifact-storage-tail-evidence/1.0", "evidence_id": "EVIDENCE",
        "recovery_id": "RECOVERY", "journal_id": "SJ-ONE",
        "kind": "ORIGINAL_INTERRUPTED_APPEND", "frame_start": 1, "observed_size": 1,
        "observed_bytes_sigil": SIGIL, "previous_evidence_record_sigil": None,
        "created_at": STAMP, "record_sigil": "",
    }
    evidence["record_sigil"] = content_sigil({
        key: member for key, member in evidence.items() if key != "record_sigil"
    })
    return evidence


def _disposition() -> dict[str, object]:
    disposition: dict[str, object] = {
        "schema_version": "artifact-storage-disposition/1.0", "disposition_id": "SD-ONE",
        "target_kind": "STAGING", "target_id": "SA-ONE", "target_generation": "GENERATION",
        "expected_blob_sigil": None,
        "expected_size_or_bound": {"kind": "UPPER_BOUND", "max_size_bytes": 1},
        "reason_code": "POLICY_REJECTED", "actor_id": "ACTOR", "policy_sigil": SIGIL,
        "approval_evidence_sigil": SIGIL, "authorization_sigil": SIGIL,
        "authorized_at": STAMP, "expires_at": "2026-08-06T00:00:01Z",
        "idempotency_key_sigil": SIGIL, "record_sigil": "",
    }
    disposition["record_sigil"] = content_sigil({
        key: member for key, member in disposition.items() if key != "record_sigil"
    })
    return disposition


def _retention_policy() -> dict[str, object]:
    policy: dict[str, object] = {
        "schema_version": "artifact-retention-policy/1.0", "policy_id": "SP-ONE",
        "scope": {"kind": "PROJECT", "project_id": "PROJECT"}, "minimum_replica_count": 0,
        "required_backends": [], "required_failure_domains": [],
        "maximum_integrity_age_seconds": None, "deletion_grace_seconds": 0,
        "retain_until": None, "automatic_gc_allowed": True, "authorization_sigil": SIGIL,
        "registered_at": STAMP, "record_sigil": "",
    }
    policy["record_sigil"] = content_sigil({
        key: member for key, member in policy.items() if key != "record_sigil"
    })
    return policy


def _gc_plan() -> dict[str, object]:
    bounds = {
        "max_roots": 1, "max_nodes": 1, "max_edges": 1, "max_depth": 1,
        "max_control_record_bytes": 1, "max_wall_millis": 1,
    }
    plan: dict[str, object] = {
        "schema_version": "artifact-gc-plan/1.0", "gc_plan_id": "SG-ONE", "policy_id": "SP-ONE",
        "root_snapshot": {
            "chronicle_head": {"schema_version": "chronicle-head/1.1", "event_count": 0,
                               "terminal_receipt_sigil": None},
            "storage_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
                              "event_sigil": SIGIL},
            "execution_roots": {"execution_journal_id": "EXECUTION", "execution_event_count": 0,
                                "execution_last_event_sigil": None, "roots": [], "root_set_sigil": SIGIL},
            "hold_set_sigil": SIGIL, "legacy_protection_set_sigil": SIGIL,
            "reference_intent_set_sigil": SIGIL, "reference_set_sigils": [], "policy_set_sigil": SIGIL,
        }, "extractor_suite_sigil": SIGIL, "bounds": bounds,
        "closure_proof": {"root_set_sigil": SIGIL, "extractor_suite_sigil": SIGIL,
                          "bounds": bounds, "visited_node_count": 0, "visited_edge_count": 0,
                          "cycle_summary_sigil": SIGIL, "reachable_blob_sigils": [],
                          "reachable_replica_ids": [], "proof_sigil": SIGIL},
        "targets": [], "created_at": STAMP, "grace_ends_at": "2026-08-06T00:00:01Z",
        "record_sigil": "",
    }
    plan["record_sigil"] = content_sigil({
        key: member for key, member in plan.items() if key != "record_sigil"
    })
    return plan


def _provenance() -> dict[str, object]:
    backend = {"backend_id": "BACKEND", "backend_profile_version": "1.0",
               "backend_profile_sigil": SIGIL}
    object_ref = {"backend_id": "BACKEND", "object_identity_sigil": SIGIL,
                  "locator_sigil": SIGIL, "generation": "GENERATION", "size_bytes": 1,
                  "blob_sigil": SIGIL}
    event = {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
             "event_sigil": SIGIL}
    provenance: dict[str, object] = {
        "schema_version": "artifact-provenance/1.0", "provenance_id": "PROVENANCE",
        "relation": "IMPORTED", "blob": {"blob_sigil": SIGIL, "size_bytes": 1},
        "source": {"kind": "EXTERNAL", "source_class": "SOURCE",
                   "sanitized_identity_sigil": SIGIL, "authorization_sigil": SIGIL},
        "destination": {"kind": "MANAGED_BACKEND", "backend": backend}, "actor_id": "ACTOR",
        "authorization_sigil": SIGIL, "execution": {"kind": "NONE"}, "backend": backend,
        "transfer": {"transfer_id": "ST-ONE", "transfer_attempt_id": "SA-ONE",
                     "request_record_sigil": SIGIL, "attempt_record_sigil": SIGIL,
                     "terminal_event": event},
        "provenance_policy": {"provenance_policy_id": "SPP-ONE", "provenance_policy_sigil": SIGIL},
        "verifications": [{"event": event, "replica_id": "SR-ONE",
                            "blob": {"blob_sigil": SIGIL, "size_bytes": 1}, "backend": backend,
                            "backend_object": object_ref,
                            "verification": {"method": "FULL_READBACK_SHA256",
                                             "evidence_sigil": SIGIL, "verified_at": STAMP,
                                             "next_due_at": None}}],
        "transformation": {"kind": "NONE"},
        "times": {"observed_at": None, "started_at": STAMP, "committed_at": STAMP,
                  "verified_at": STAMP, "terminal_at": STAMP}, "terminal_reason": None,
        "record_sigil": "",
    }
    provenance["record_sigil"] = content_sigil({
        key: member for key, member in provenance.items() if key != "record_sigil"
    })
    return provenance


def _backend_profile() -> dict[str, object]:
    reserve_classes = (
        "INITIALIZATION", "COORDINATOR_LIVENESS", "CLOCK_PRESSURE",
        "CATALOG_ADMINISTRATION", "VERIFICATION_INCIDENT", "RETENTION_REFERENCE",
        "GC_ADMINISTRATION", "RECOVERY",
    )
    profile: dict[str, object] = {
        "schema_version": "artifact-storage-backend/1.0", "backend_id": "BACKEND",
        "adapter_id": "ADAPTER", "adapter_version": "1.0", "protocol_version": "1.0",
        "adapter_sigil": SIGIL, "configuration_sigil": SIGIL, "namespace_sigil": SIGIL,
        "isolation": {"scope": "SINGLE_PROJECT", "namespace_enforcement": "ADAPTER_SCOPED",
                      "worker_access": "NONE", "worker_credentials_exposed": False},
        "limits": {"max_object_bytes": 1,
                   "transfer_bounds": {"max_bytes": 1, "max_duration_millis": 1,
                                       "max_file_count": None, "max_chunk_count": 1, "buffer_bytes": 1},
                   "max_concurrent_streams": 1, "max_inventory_entries": 1,
                   "max_tail_recovery_retries": 1,
                   "system_reserve_limits": [{"reserve_class": item, "max_event_frame_count": 1,
                                              "max_control_record_count": 0,
                                              "max_recovery_evidence_count": 0,
                                              "max_event_frame_bytes": 56,
                                              "max_control_record_bytes": 1,
                                              "max_recovery_evidence_bytes": 1}
                                             for item in reserve_classes],
                   "system_journal_reserve_bytes": 1, "system_control_record_reserve_bytes": 1,
                   "system_recovery_reserve_bytes": 1},
        "consistency": {"read_after_write": "STRONG", "list_consistency": "STRONG",
                        "atomic_visibility": True, "immutable_generation": True,
                        "exact_generation_reads": True},
        "durability": {"commit_semantics": "FSYNC_FILE_AND_PARENT", "logical_readback": True,
                       "transparent_encryption": False, "transparent_compression": False},
        "verification_methods": ["CONFORMANCE_END_TO_END", "FULL_READBACK_SHA256"],
        "range_resume": {"range_reads": False, "resumable_stage_writes": False,
                         "resume_binding": "UNSUPPORTED"},
        "conditional_operations": {"conditional_create": True, "no_overwrite_finalize": True,
                                   "exact_generation_stat": True, "exact_generation_delete": True},
        "deletion_capabilities": {"exact_generation_delete": True, "wildcard_delete": False,
                                  "retention_lock": "NONE", "verification": "POST_DELETE_STAT"},
        "credential_class": "COORDINATOR_HOST_LOCAL",
        "fencing": {"mode": "COORDINATOR_PRECOMMIT", "attempt_staging_isolated": True,
                    "executor_epoch_checked": True, "job_fence_floor_checked": True,
                    "tombstone_checked": True},
        "conformance": {"profile_id": "LOCAL-PHASE3/1.0", "suite_version": "1.0",
                        "suite_sigil": SIGIL, "host_platform_sigil": SIGIL, "evidence_sigil": SIGIL},
        "record_sigil": "",
    }
    profile["record_sigil"] = content_sigil({
        key: member for key, member in profile.items() if key != "record_sigil"
    })
    return profile


def _provenance_policy() -> dict[str, object]:
    policy: dict[str, object] = {
        "schema_version": "artifact-provenance-policy/1.0", "provenance_policy_id": "SPP-ONE",
        "policy_version": "1.0", "scope": {"kind": "PROJECT", "project_id": "PROJECT"},
        "allowed_directions": ["INGEST"], "allowed_purposes": ["ARTIFACT_IMPORT"],
        "allowed_source_kinds": ["EXTERNAL"], "allowed_destination_kinds": ["MANAGED_BACKEND"],
        "allowed_relations": ["IMPORTED"], "execution_requirement": "OPTIONAL",
        "allowed_verification_methods": ["FULL_READBACK_SHA256"],
        "minimum_verification_evidence": 1, "transformation_mode": "NONE_ONLY",
        "required_retention_policy_ids": [], "authorization_sigil": SIGIL,
        "registered_at": STAMP, "record_sigil": "",
    }
    policy["record_sigil"] = content_sigil({
        key: member for key, member in policy.items() if key != "record_sigil"
    })
    return policy


def _doctor_report() -> dict[str, object]:
    check = {"check_id": "CHECK", "status": "INCOMPLETE", "subject_kind": "JOURNAL",
             "subject_id": "SJ-ONE", "evidence_sigils": [], "reason": None}
    report: dict[str, object] = {
        "schema_version": "artifact-storage-doctor-report/1.0", "report_id": "REPORT",
        "mode": "NORMAL", "project_id": "PROJECT", "storage_journal_id": None,
        "journal_head_sigil": None, "chronicle_head_sigil": None,
        "storage_format_version": None, "backend_profile_id": None,
        "backend_profile_sigil": None, "conformance_profile_id": None,
        "conformance_suite_sigil": None, "coordinator_epoch": None,
        "journal_verification": check, "state_verification": check,
        "backend_inventory": [], "replica_checks": [], "legacy_checks": [],
        "quarantine_checks": [], "quota_checks": [], "reference_checks": [],
        "open_intent_checks": [],
        "bounds": {"max_inventory_entries": 0, "max_control_records": 0,
                   "max_rehash_bytes": 0, "max_wall_millis": 0,
                   "inventory_truncated": False, "rehash_truncated": False},
        "incomplete_reasons": [], "overall_status": "INCOMPLETE",
        "started_at": STAMP, "completed_at": STAMP, "report_sigil": "",
    }
    report["report_sigil"] = content_sigil({
        key: member for key, member in report.items() if key != "report_sigil"
    })
    return report


def _transfer() -> dict[str, object]:
    backend = {"backend_id": "BACKEND", "backend_profile_version": "1.0",
               "backend_profile_sigil": SIGIL}
    execution = {
        "kind": "LEASED", "execution_journal_id": "EXECUTION", "executor_epoch": 1,
        "job_id": "JOB", "attempt_id": "ATTEMPT", "lease_id": "LEASE", "worker_id": "WORKER",
        "worker_session_id": "SESSION",
        "fence": {"execution_journal_id": "EXECUTION", "executor_epoch": 1, "job_id": "JOB",
                  "attempt_id": "ATTEMPT", "lease_id": "LEASE", "fencing_generation": 0,
                  "execution_event_sigil": SIGIL, "job_fence_floor": 0, "tombstone_present": False},
    }
    transfer: dict[str, object] = {
        "schema_version": "artifact-transfer/1.0", "transfer_id": "ST-ONE", "direction": "INGEST",
        "purpose": "ATTEMPT_OUTPUT",
        "source": {"kind": "ATTEMPT_OUTPUT", "execution": execution, "output_handle_id": "OUTPUT"},
        "destination": {"kind": "MANAGED_BACKEND", "backend": backend}, "expected_blob_sigil": SIGIL,
        "bounds": {"max_bytes": 1, "max_duration_millis": 1, "max_file_count": None,
                   "max_chunk_count": 1, "buffer_bytes": 1}, "backend": backend,
        "authorization_sigil": SIGIL, "idempotency_key_sigil": SIGIL, "execution": execution,
        "verification_method": "FULL_READBACK_SHA256",
        "provenance_policy": {"provenance_policy_id": "SPP-ONE", "provenance_policy_sigil": SIGIL},
        "retention_policy_ids": [], "created_at": STAMP, "record_sigil": "",
    }
    transfer["record_sigil"] = content_sigil({
        key: member for key, member in transfer.items() if key != "record_sigil"
    })
    return transfer


def _transfer_attempt() -> dict[str, object]:
    clock = {"utc": STAMP, "monotonic_anchor_id": "CLOCK", "monotonic_ticks": 0,
             "monotonic_frequency_hz": 1, "uncertainty_micros": 0,
             "observation_sigil": SIGIL}
    attempt: dict[str, object] = {
        "schema_version": "artifact-transfer-attempt/1.0", "transfer_attempt_id": "SA-ONE",
        "transfer_id": "ST-ONE", "attempt_number": 1, "state": "PREPARED",
        "staging_state": "NOT_CREATED",
        "reservation": {"reservation_id": "RESERVATION", "claims": [],
                        "capacity_plan": {"allowed_event_types": [], "max_event_frame_count": 1,
                                          "max_control_record_count": 0,
                                          "max_recovery_evidence_count": 0, "max_event_frame_bytes": 1,
                                          "max_control_record_bytes": 1, "max_recovery_evidence_bytes": 1},
                        "expires_at": None, "created_clock": clock,
                        "remaining_micros_at_creation": None},
        "staging_object": None, "commit_intent": None,
        "residual_staging_cleanup": {"state": "NOT_REQUIRED", "staging_object": None,
                                     "evidence_sigil": None, "reason": None},
        "computed_blob_sigil": None, "computed_size_bytes": None, "selected_replica_id": None,
        "quarantine_id": None, "terminal_reason": None, "started_at": STAMP, "terminal_at": None,
        "revision": 1, "record_sigil": "",
    }
    attempt["record_sigil"] = content_sigil({
        key: member for key, member in attempt.items() if key != "record_sigil"
    })
    return attempt


def _materialization() -> dict[str, object]:
    clock = {"utc": STAMP, "monotonic_anchor_id": "CLOCK", "monotonic_ticks": 0,
             "monotonic_frequency_hz": 1, "uncertainty_micros": 0,
             "observation_sigil": SIGIL}
    materialization: dict[str, object] = {
        "schema_version": "artifact-materialization/1.0", "materialization_id": "SM-ONE",
        "source_blob_sigil": SIGIL, "source_replica_id": "SR-ONE",
        "source_verification_sigil": SIGIL, "destination_class": "SANCTUM_INPUT",
        "destination_sigil": SIGIL, "task_id": None, "attempt_id": None,
        "access_mode": "READ_ONLY",
        "bounds": {"max_bytes": 0, "max_duration_millis": 1, "max_file_count": None,
                   "max_chunk_count": 1, "buffer_bytes": 1},
        "reservation": {"reservation_id": "RESERVATION", "claims": [],
                        "capacity_plan": {"allowed_event_types": [], "max_event_frame_count": 1,
                                          "max_control_record_count": 0,
                                          "max_recovery_evidence_count": 0, "max_event_frame_bytes": 1,
                                          "max_control_record_bytes": 1, "max_recovery_evidence_bytes": 1},
                        "expires_at": None, "created_clock": clock,
                        "remaining_micros_at_creation": None},
        "destination_staging_object": None, "commit_intent": None,
        "residual_staging_cleanup": {"state": "NOT_REQUIRED", "staging_object": None,
                                     "evidence_sigil": None, "reason": None},
        "state": "PREPARED", "verification": None,
        "cleanup": {"state": "NOT_REQUIRED", "evidence_sigil": None, "reason": None},
        "created_at": STAMP, "terminal_at": None, "revision": 1, "record_sigil": "",
    }
    materialization["record_sigil"] = content_sigil({
        key: member for key, member in materialization.items() if key != "record_sigil"
    })
    return materialization


def _recovery_marker() -> dict[str, object]:
    marker: dict[str, object] = {
        "schema_version": "artifact-storage-recovery-marker/1.0", "recovery_id": "RECOVERY",
        "journal_id": "SJ-ONE", "prior_head_sigil": SIGIL, "old_committed_byte_length": 2,
        "last_complete_byte_length": 1, "discarded_suffix_size": 1,
        "discarded_suffix_sigil": SIGIL, "evidence_record_sigil": SIGIL,
        "phase": "EVIDENCE_DURABLE", "recovery_event_id": None, "recovery_event_sigil": None,
        "recovery_event_seed_record_sigil": None, "recovery_frame_start": None,
        "recovery_frame_size": None, "recovery_frame_sigil": None,
        "prepared_frame_evidence_record_sigil": None, "retry_count": 0,
        "latest_retry_evidence_record_sigil": None, "created_at": STAMP, "updated_at": STAMP,
        "record_sigil": "",
    }
    marker["record_sigil"] = content_sigil({
        key: member for key, member in marker.items() if key != "record_sigil"
    })
    return marker


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


def test_reference_set_and_intent_close_ids_sigils_and_order() -> None:
    reference_set = _reference_set()
    validate_artifact_storage_reference_set_v1(reference_set)
    assert load_artifact_storage_reference_set_v1(json.dumps(reference_set)) == reference_set

    stale_set = deepcopy(reference_set)
    stale_set["reference_set_id"] = "RS-" + "A" * 64
    stale_set["reference_set_sigil"] = content_sigil({
        key: member for key, member in stale_set.items() if key != "reference_set_sigil"
    })
    with pytest.raises(AthanorError, match="Reference Set ID mismatch"):
        validate_artifact_storage_reference_set_v1(stale_set)

    execution_root_set = deepcopy(reference_set)
    execution_root_set["source"] = {
        "kind": "OPERATIONAL_CONTROL_RECORD", "identity": "ESM-ONE",
        "schema_version": "execution-storage-root-manifest/1.0", "sigil": SIGIL,
    }
    execution_root_set["reference_set_id"] = derive_artifact_storage_reference_set_id_v1(
        execution_root_set
    )
    execution_root_set["registration_event_id"] = "SE-" + content_sigil([
        "artifact-storage-execution-root-reference-set-registration-event-id/1.0", "ESM-ONE",
    ]).removeprefix("sha256:").upper()
    execution_root_set["reference_set_sigil"] = content_sigil({
        key: member for key, member in execution_root_set.items() if key != "reference_set_sigil"
    })
    validate_artifact_storage_reference_set_v1(execution_root_set)

    intent = {
        "schema_version": "artifact-storage-reference-intent/1.0", "reference_intent_id": "",
        "transition_request_id": "REQUEST", "transition_request_sigil": SIGIL,
        "canonical_event_type": "patch.proposed",
        "expected_chronicle_head": {"schema_version": "chronicle-head/1.1", "event_count": 0,
                                    "terminal_receipt_sigil": None},
        "reference_sets": [{"reference_set_id": reference_set["reference_set_id"],
                            "reference_set_sigil": reference_set["reference_set_sigil"]}],
        "blob_sigils": [], "actor_id": "ACTOR", "authorization_sigil": SIGIL,
        "idempotency_key_sigil": SIGIL, "requested_at": STAMP, "record_sigil": "",
    }
    intent["reference_intent_id"] = derive_artifact_storage_reference_intent_id_v1(intent)
    intent["record_sigil"] = content_sigil({
        key: member for key, member in intent.items() if key != "record_sigil"
    })
    validate_artifact_storage_reference_intent_v1(intent)
    assert load_artifact_storage_reference_intent_v1(json.dumps(intent)) == intent

    stale_intent = deepcopy(intent)
    stale_intent["reference_intent_id"] = "RI-" + "A" * 64
    stale_intent["record_sigil"] = content_sigil({
        key: member for key, member in stale_intent.items() if key != "record_sigil"
    })
    with pytest.raises(AthanorError, match="Reference Intent ID mismatch"):
        validate_artifact_storage_reference_intent_v1(stale_intent)

    state = _state()
    state["reference_sets"] = [{
        "reference_set_id": reference_set["reference_set_id"],
        "reference_set_sigil": reference_set["reference_set_sigil"], "source_identity": "SOURCE",
        "revision": 1, "last_event_sigil": SIGIL,
    }]
    state["canonical_reference_intents"] = [{
        "reference_intent_id": intent["reference_intent_id"], "record_sigil": intent["record_sigil"],
        "state": "OPEN", "chronicle_commit": None, "release_kind": None,
        "release_authority_sigil": None, "release_reason": None, "revision": 1,
        "last_event_sigil": SIGIL,
    }]
    state["open_intents"] = [{
        "intent_kind": "CANONICAL_REFERENCE", "intent_id": intent["reference_intent_id"],
        "owner_id": intent["reference_intent_id"],
        "source_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
                         "event_sigil": SIGIL}, "intent_sigil": SIGIL, "revision": 1,
        "last_event_sigil": SIGIL, "authorization_expires_at": None,
        "expected_chronicle_head": intent["expected_chronicle_head"],
        "blob_sigils": intent["blob_sigils"], "reference_set_sigils": [],
    }]
    state["state_sigil"] = content_sigil({
        key: member for key, member in state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_supplied_control_records_v1(
        state, reference_sets=[reference_set], reference_intents=[intent]
    )

    missing_set = deepcopy(state)
    with pytest.raises(AthanorError, match="Reference Set projection lacks"):
        validate_artifact_storage_state_supplied_control_records_v1(
            missing_set, reference_sets=[], reference_intents=[intent]
        )
    wrong_source = deepcopy(state)
    wrong_source["reference_sets"][0]["source_identity"] = "OTHER"  # type: ignore[index]
    wrong_source["state_sigil"] = content_sigil({
        key: member for key, member in wrong_source.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Reference Set projection lacks"):
        validate_artifact_storage_state_supplied_control_records_v1(
            wrong_source, reference_sets=[reference_set], reference_intents=[intent]
        )
    with pytest.raises(AthanorError, match="Reference Intent projection lacks"):
        validate_artifact_storage_state_supplied_control_records_v1(
            state, reference_sets=[reference_set], reference_intents=[]
        )


def test_storage_replay_projects_exact_registered_reference_set() -> None:
    initial = _initial_replay_event()
    activation = _next_event(initial)
    activation.update({
        "event_type": "storage.activation_completed",
        "entity_revisions": [{
            "entity_type": "STORE", "entity_id": "STORE",
            "previous_revision": 1, "next_revision": 2,
        }],
        "payload": {
            "legacy_protection_ids": [], "activation_evidence_sigil": SIGIL,
            "clock": initial["payload"]["clock"],
        },
        "quota_effects": [],
    })
    activation["event_sigil"] = content_sigil({
        key: value for key, value in activation.items() if key != "event_sigil"
    })
    reference_set = _reference_set()
    registered = _next_event(activation)
    registered.update({
        "event_id": reference_set["registration_event_id"],
        "sequence": 3,
        "event_type": "reference_set.registered",
        "recorded_at": "2026-08-06T00:00:01Z",
        "observed_at": None,
        "entity_revisions": [{
            "entity_type": "REFERENCE_SET",
            "entity_id": reference_set["reference_set_id"],
            "previous_revision": None,
            "next_revision": 1,
        }],
        "causation_event_id": None,
        "idempotency_key_sigil": None,
        "quota_effects": [],
        "payload": {
            "reference_set_id": reference_set["reference_set_id"],
            "reference_set_sigil": reference_set["reference_set_sigil"],
            "source_identity": reference_set["source"]["identity"],
            "source_sigil": reference_set["source"]["sigil"],
        },
    })
    reference_set["created_at"] = registered["recorded_at"]
    reference_set["reference_set_sigil"] = content_sigil({
        key: value for key, value in reference_set.items()
        if key != "reference_set_sigil"
    })
    registered["payload"]["reference_set_sigil"] = reference_set["reference_set_sigil"]
    registered["event_sigil"] = content_sigil({
        key: value for key, value in registered.items() if key != "event_sigil"
    })
    state = replay_artifact_storage_journal_prefix_v1(
        [initial, activation, registered], supplied_reference_sets=[reference_set]
    )
    assert state["reference_sets"] == [{
        "reference_set_id": reference_set["reference_set_id"],
        "reference_set_sigil": reference_set["reference_set_sigil"],
        "source_identity": reference_set["source"]["identity"],
        "revision": 1,
        "last_event_sigil": registered["event_sigil"],
    }]

    distinct_set = deepcopy(reference_set)
    distinct_set["extractor"]["extractor_sigil"] = SIGIL_B
    distinct_set["reference_set_id"] = derive_artifact_storage_reference_set_id_v1(
        distinct_set
    )
    distinct_set["registration_event_id"] = "SE-" + content_sigil([
        "artifact-storage-reference-set-registration-event-id/1.0",
        distinct_set["reference_set_id"],
    ]).removeprefix("sha256:").upper()
    distinct_set["reference_set_sigil"] = content_sigil({
        key: value for key, value in distinct_set.items()
        if key != "reference_set_sigil"
    })
    second_registered = _next_event(registered)
    second_registered.update({
        "event_id": distinct_set["registration_event_id"],
        "sequence": 4,
        "event_type": "reference_set.registered",
        "recorded_at": "2026-08-06T00:00:02Z",
        "entity_revisions": [{
            "entity_type": "REFERENCE_SET",
            "entity_id": distinct_set["reference_set_id"],
            "previous_revision": None,
            "next_revision": 1,
        }],
        "payload": {
            "reference_set_id": distinct_set["reference_set_id"],
            "reference_set_sigil": distinct_set["reference_set_sigil"],
            "source_identity": distinct_set["source"]["identity"],
            "source_sigil": distinct_set["source"]["sigil"],
        },
    })
    distinct_set["created_at"] = second_registered["recorded_at"]
    distinct_set["reference_set_sigil"] = content_sigil({
        key: value for key, value in distinct_set.items()
        if key != "reference_set_sigil"
    })
    second_registered["payload"]["reference_set_sigil"] = distinct_set[
        "reference_set_sigil"
    ]
    second_registered["event_sigil"] = content_sigil({
        key: value for key, value in second_registered.items() if key != "event_sigil"
    })
    second_state = replay_artifact_storage_journal_prefix_v1(
        [initial, activation, registered, second_registered],
        supplied_reference_sets=[reference_set, distinct_set],
    )
    assert [item["reference_set_id"] for item in second_state["reference_sets"]] == sorted([
        reference_set["reference_set_id"], distinct_set["reference_set_id"]
    ])

    wrong_record = deepcopy(reference_set)
    wrong_record["source"]["identity"] = "OTHER"
    wrong_record["reference_set_id"] = derive_artifact_storage_reference_set_id_v1(
        wrong_record
    )
    wrong_record["reference_set_sigil"] = content_sigil({
        key: value for key, value in wrong_record.items() if key != "reference_set_sigil"
    })
    with pytest.raises(AthanorError, match="requires exactly one supplied record"):
        replay_artifact_storage_journal_prefix_v1(
            [initial, activation, registered], supplied_reference_sets=[wrong_record]
        )
    with pytest.raises(AthanorError, match="requires its supplied record"):
        replay_artifact_storage_journal_prefix_v1([initial, activation, registered])


def test_legacy_protection_is_self_signed_and_matches_state_projection() -> None:
    protection = _legacy_protection()
    validate_artifact_storage_legacy_protection_v1(protection)
    assert load_artifact_storage_legacy_protection_v1(json.dumps(protection)) == protection

    stale = deepcopy(protection)
    stale["program_id"] = "OTHER"
    with pytest.raises(AthanorError, match="Legacy Protection self-Sigil"):
        validate_artifact_storage_legacy_protection_v1(stale)

    state = _state()
    state["legacy_v1_protections"] = [{
        "protection_id": "PROTECTION", "artifact_id": "ARTIFACT", "state": "PROTECTED",
        "record": protection, "receipt_sigil": SIGIL, "reason": None, "revision": 1,
        "last_event_sigil": SIGIL,
    }]
    state["state_sigil"] = content_sigil({
        key: member for key, member in state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(state)

    mismatched = deepcopy(state)
    mismatched["legacy_v1_protections"][0]["receipt_sigil"] = SIGIL_B  # type: ignore[index]
    mismatched["state_sigil"] = content_sigil({
        key: member for key, member in mismatched.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Legacy Protection disagrees"):
        validate_artifact_storage_state_v1(mismatched)


def test_recovery_evidence_and_marker_phase_matrix() -> None:
    evidence = _tail_evidence()
    validate_artifact_storage_tail_evidence_v1(evidence)
    assert load_artifact_storage_tail_evidence_v1(json.dumps(evidence)) == evidence

    marker = _recovery_marker()
    validate_artifact_storage_recovery_marker_v1(marker)
    assert load_artifact_storage_recovery_marker_v1(json.dumps(marker)) == marker

    id_durable = deepcopy(marker)
    id_durable.update({
        "phase": "RECOVERY_EVENT_ID_DURABLE", "recovery_event_id": "SE-RECOVERY",
        "recovery_event_sigil": SIGIL, "recovery_event_seed_record_sigil": evidence["record_sigil"],
    })
    id_durable["record_sigil"] = content_sigil({
        key: member for key, member in id_durable.items() if key != "record_sigil"
    })
    validate_artifact_storage_recovery_marker_v1(id_durable)

    malformed = deepcopy(id_durable)
    malformed["recovery_frame_start"] = 1
    malformed["record_sigil"] = content_sigil({
        key: member for key, member in malformed.items() if key != "record_sigil"
    })
    with pytest.raises(AthanorError, match="ID-durable phase"):
        validate_artifact_storage_recovery_marker_v1(malformed)

    retried = deepcopy(id_durable)
    retried.update({
        "phase": "RECOVERY_EVENT_RETRY_EVIDENCE_DURABLE", "recovery_frame_start": 1,
        "recovery_frame_size": 1, "recovery_frame_sigil": SIGIL,
        "prepared_frame_evidence_record_sigil": SIGIL, "retry_count": 1,
        "latest_retry_evidence_record_sigil": SIGIL_B,
    })
    retried["record_sigil"] = content_sigil({
        key: member for key, member in retried.items() if key != "record_sigil"
    })
    validate_artifact_storage_recovery_marker_v1(retried)

    zero_retry = deepcopy(retried)
    zero_retry["retry_count"] = 0
    zero_retry["record_sigil"] = content_sigil({
        key: member for key, member in zero_retry.items() if key != "record_sigil"
    })
    with pytest.raises(AthanorError, match="zero retry"):
        validate_artifact_storage_recovery_marker_v1(zero_retry)


def test_disposition_is_self_signed_and_has_a_positive_authorization_window() -> None:
    disposition = _disposition()
    validate_artifact_storage_disposition_v1(disposition)
    assert load_artifact_storage_disposition_v1(json.dumps(disposition)) == disposition

    expired = deepcopy(disposition)
    expired["expires_at"] = STAMP
    expired["record_sigil"] = content_sigil({
        key: member for key, member in expired.items() if key != "record_sigil"
    })
    with pytest.raises(AthanorError, match="expiry must follow"):
        validate_artifact_storage_disposition_v1(expired)


def test_retention_policy_and_hold_projection_matrix() -> None:
    policy = _retention_policy()
    validate_artifact_retention_policy_v1(policy)
    assert load_artifact_retention_policy_v1(json.dumps(policy)) == policy

    state = _state()
    state["retention_policies"] = [{
        "policy_id": policy["policy_id"], "record_sigil": policy["record_sigil"],
        "revision": 1, "last_event_sigil": SIGIL,
    }]
    state["holds"] = [{
        "hold_id": "SH-ONE", "target_kind": "BLOB", "target_id": SIGIL,
        "policy_id": policy["policy_id"], "state": "ACTIVE", "set_authorization_sigil": SIGIL,
        "release_authorization_sigil": None, "revision": 1, "last_event_sigil": SIGIL,
    }]
    state["state_sigil"] = content_sigil({
        key: member for key, member in state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_supplied_retention_policies_v1(state, policies=[policy])

    invalid_hold = deepcopy(state)
    invalid_hold["holds"][0]["release_authorization_sigil"] = SIGIL_B  # type: ignore[index]
    invalid_hold["state_sigil"] = content_sigil({
        key: member for key, member in invalid_hold.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Hold release authorization"):
        validate_artifact_storage_state_v1(invalid_hold)


def test_gc_plan_closes_local_proof_bindings_and_sorting() -> None:
    plan = _gc_plan()
    validate_artifact_gc_plan_v1(plan)
    assert load_artifact_gc_plan_v1(json.dumps(plan)) == plan

    wrong_proof = deepcopy(plan)
    wrong_proof["closure_proof"]["bounds"] = {  # type: ignore[index]
        **wrong_proof["bounds"], "max_depth": 2  # type: ignore[index]
    }
    wrong_proof["record_sigil"] = content_sigil({
        key: member for key, member in wrong_proof.items() if key != "record_sigil"
    })
    with pytest.raises(AthanorError, match="Closure Proof disagrees"):
        validate_artifact_gc_plan_v1(wrong_proof)


def test_provenance_is_self_signed_and_matches_state_projection() -> None:
    provenance = _provenance()
    validate_artifact_provenance_v1(provenance)
    assert load_artifact_provenance_v1(json.dumps(provenance)) == provenance

    state = _state()
    state["provenance"] = [{"provenance_id": provenance["provenance_id"],
                            "record_sigil": provenance["record_sigil"], "revision": 1,
                            "last_event_sigil": SIGIL}]
    state["state_sigil"] = content_sigil({
        key: member for key, member in state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_supplied_provenance_v1(state, records=[provenance])

    missing = deepcopy(state)
    with pytest.raises(AthanorError, match="Provenance projection lacks"):
        validate_artifact_storage_state_supplied_provenance_v1(missing, records=[])


def test_backend_profile_is_self_signed_and_canonically_orders_methods() -> None:
    profile = _backend_profile()
    validate_artifact_storage_backend_v1(profile)
    assert load_artifact_storage_backend_v1(json.dumps(profile)) == profile

    unordered = deepcopy(profile)
    unordered["verification_methods"].reverse()  # type: ignore[index]
    unordered["record_sigil"] = content_sigil({
        key: member for key, member in unordered.items() if key != "record_sigil"
    })
    with pytest.raises(AthanorError, match="verification methods are not sorted"):
        validate_artifact_storage_backend_v1(unordered)


def test_provenance_policy_is_self_signed_and_matches_state_projection() -> None:
    policy = _provenance_policy()
    validate_artifact_provenance_policy_v1(policy)
    assert load_artifact_provenance_policy_v1(json.dumps(policy)) == policy

    state = _state()
    state["provenance_policies"] = [{
        "provenance_policy_id": policy["provenance_policy_id"],
        "record_sigil": policy["record_sigil"], "revision": 1, "last_event_sigil": SIGIL,
    }]
    state["state_sigil"] = content_sigil({
        key: member for key, member in state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_supplied_provenance_policies_v1(state, policies=[policy])

    missing = deepcopy(state)
    with pytest.raises(AthanorError, match="Provenance Policy projection lacks"):
        validate_artifact_storage_state_supplied_provenance_policies_v1(missing, policies=[])


def test_doctor_report_is_self_signed_and_nonnegative_in_duration() -> None:
    report = _doctor_report()
    validate_artifact_storage_doctor_report_v1(report)
    assert load_artifact_storage_doctor_report_v1(json.dumps(report)) == report

    reversed_times = deepcopy(report)
    reversed_times["completed_at"] = "2026-08-05T23:59:59Z"
    reversed_times["report_sigil"] = content_sigil({
        key: member for key, member in reversed_times.items() if key != "report_sigil"
    })
    with pytest.raises(AthanorError, match="completes before"):
        validate_artifact_storage_doctor_report_v1(reversed_times)


def test_attempt_output_transfer_is_self_signed_and_matches_state_projection() -> None:
    transfer = _transfer()
    validate_artifact_transfer_v1(transfer)
    assert load_artifact_transfer_v1(json.dumps(transfer)) == transfer

    state = _state()
    state["transfer_requests"] = [{
        "transfer_id": transfer["transfer_id"], "request_record_sigil": transfer["record_sigil"],
        "state": "ACTIVE", "attempt_ids": [], "selected_attempt_id": None,
        "revision": 1, "last_event_sigil": SIGIL,
    }]
    state["state_sigil"] = content_sigil({
        key: member for key, member in state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_supplied_transfers_v1(state, transfers=[transfer])

    invalid = deepcopy(transfer)
    invalid["destination"]["backend"] = deepcopy(invalid["destination"]["backend"])  # type: ignore[index]
    invalid["destination"]["backend"]["backend_id"] = "OTHER"  # type: ignore[index]
    invalid["record_sigil"] = content_sigil({
        key: member for key, member in invalid.items() if key != "record_sigil"
    })
    with pytest.raises(AthanorError, match="ATTEMPT_OUTPUT local bindings"):
        validate_artifact_transfer_v1(invalid)


def test_transfer_attempt_state_record_matches_its_supplied_request() -> None:
    transfer = _transfer()
    attempt = _transfer_attempt()
    state = _state()
    state["transfer_requests"] = [{
        "transfer_id": transfer["transfer_id"], "request_record_sigil": transfer["record_sigil"],
        "state": "ACTIVE", "attempt_ids": [attempt["transfer_attempt_id"]],
        "selected_attempt_id": None, "revision": 1, "last_event_sigil": SIGIL,
    }]
    state["transfer_attempts"] = [{"record": attempt, "last_event_sigil": SIGIL}]
    state["state_sigil"] = content_sigil({
        key: member for key, member in state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_supplied_transfer_attempts_v1(state, transfers=[transfer])

    unlisted = deepcopy(state)
    unlisted["transfer_requests"][0]["attempt_ids"] = []  # type: ignore[index]
    unlisted["state_sigil"] = content_sigil({
        key: member for key, member in unlisted.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Request Attempts disagree"):
        validate_artifact_storage_state_v1(unlisted)
    with pytest.raises(AthanorError, match="Request Attempts disagree"):
        validate_artifact_storage_state_supplied_transfer_attempts_v1(unlisted, transfers=[transfer])

    wrong_request = deepcopy(state)
    wrong_request["transfer_attempts"][0]["record"]["transfer_id"] = "ST-OTHER"  # type: ignore[index]
    wrong_request["transfer_attempts"][0]["record"]["record_sigil"] = content_sigil({  # type: ignore[index]
        key: member for key, member in wrong_request["transfer_attempts"][0]["record"].items()  # type: ignore[index]
        if key != "record_sigil"
    })
    wrong_request["state_sigil"] = content_sigil({
        key: member for key, member in wrong_request.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="lacks its request projection"):
        validate_artifact_storage_state_v1(wrong_request)


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

    duplicate_identity = deepcopy(second)
    duplicate_identity["event_id"] = first["event_id"]
    duplicate_identity["event_sigil"] = content_sigil({
        key: member for key, member in duplicate_identity.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="duplicate Event identity"):
        validate_artifact_storage_journal_prefix_v1([first, duplicate_identity])

    not_initialized = _event()
    with pytest.raises(AthanorError, match="does not start"):
        validate_artifact_storage_journal_prefix_v1([not_initialized])

    wrong_initial_epoch = deepcopy(first)
    wrong_initial_epoch["epoch"] = 2
    wrong_initial_epoch["event_sigil"] = content_sigil({
        key: member for key, member in wrong_initial_epoch.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="must use epoch one"):
        validate_artifact_storage_journal_prefix_v1([wrong_initial_epoch])

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

    recovering = deepcopy(state)
    recovering.update({
        "store_status": "RECOVERING", "active_recovery_id": "RECOVERY",
        "recovery_origin_status": "INITIALIZING", "current_epoch": 2,
        "recoveries": [{
            "recovery_id": "RECOVERY", "origin_status": "INITIALIZING", "state": "ACTIVE",
            "started_event_sigil": SIGIL, "epoch_ids": [1, 2],
            "tail_recovery_evidence_record_sigils": [], "completed_event_sigil": None,
            "resume_status": None,
        }],
    })
    recovering["state_sigil"] = content_sigil({
        key: member for key, member in recovering.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(recovering)

    duplicate_active_recovery = deepcopy(recovering)
    duplicate_active_recovery["recoveries"].append({  # type: ignore[index]
        "recovery_id": "RECOVERY-TWO", "origin_status": "INITIALIZING", "state": "ACTIVE",
        "started_event_sigil": SIGIL, "epoch_ids": [1, 2],
        "tail_recovery_evidence_record_sigils": [], "completed_event_sigil": None,
        "resume_status": None,
    })
    duplicate_active_recovery["state_sigil"] = content_sigil({
        key: member for key, member in duplicate_active_recovery.items()
        if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="active Recovery disagrees"):
        validate_artifact_storage_state_v1(duplicate_active_recovery)

    stale_recovery = deepcopy(recovering)
    stale_recovery["recoveries"][0]["epoch_ids"] = [1]  # type: ignore[index]
    stale_recovery["state_sigil"] = content_sigil({
        key: member for key, member in stale_recovery.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="active Recovery disagrees"):
        validate_artifact_storage_state_v1(stale_recovery)

    unprojected_active_recovery = deepcopy(recovering)
    unprojected_active_recovery.update({
        "store_status": "INITIALIZING", "active_recovery_id": None,
        "recovery_origin_status": None,
    })
    unprojected_active_recovery["state_sigil"] = content_sigil({
        key: member for key, member in unprojected_active_recovery.items()
        if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="nonrecovering Store retains"):
        validate_artifact_storage_state_v1(unprojected_active_recovery)

    over_limit_counter = deepcopy(state)
    over_limit_counter["quota_counters"][0].update({  # type: ignore[index]
        "limit": 1, "used": 1, "reserved": 1,
    })
    over_limit_counter["state_sigil"] = content_sigil({
        key: member for key, member in over_limit_counter.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="quota counter exceeds"):
        validate_artifact_storage_state_v1(over_limit_counter)

    wrong_open_sigil = deepcopy(open_ids)
    wrong_open_sigil["open_intents"] = [wrong_open_sigil["open_intents"][0]]
    wrong_open_sigil["open_intents"][0]["intent_sigil"] = SIGIL_B
    wrong_open_sigil["state_sigil"] = content_sigil({
        key: member for key, member in wrong_open_sigil.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Open Intent disagrees"):
        validate_artifact_storage_state_v1(wrong_open_sigil)

    wrong_open_journal = deepcopy(open_ids)
    wrong_open_journal["open_intents"][0]["source_event"]["journal_id"] = "SJ-OTHER"
    wrong_open_journal["state_sigil"] = content_sigil({
        key: member for key, member in wrong_open_journal.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Open Intent disagrees"):
        validate_artifact_storage_state_v1(wrong_open_journal)

    future_open_intent = deepcopy(open_ids)
    future_open_intent["open_intents"][0]["source_event"]["sequence"] = 2
    future_open_intent["state_sigil"] = content_sigil({
        key: member for key, member in future_open_intent.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Open Intent disagrees"):
        validate_artifact_storage_state_v1(future_open_intent)

    quarantine_state = deepcopy(state)
    quarantine = {
        "quarantine_id": "SQ-ONE", "owner_kind": "TRANSFER_ATTEMPT", "owner_id": "SA-ONE",
        "state": "INTENT_RECORDED", "source_object": object_ref,
        "destination_object": object_ref,
        "source_cleanup": {"state": "NOT_REQUIRED", "staging_object": None,
                           "evidence_sigil": None, "reason": None},
        "reservation": _transfer_attempt()["reservation"],
        "reason": {"code": "BACKEND_UNAVAILABLE", "evidence_sigils": []},
        "revision": 1, "last_event_sigil": SIGIL, "record_sigil": "",
    }
    quarantine["record_sigil"] = content_sigil({
        key: member for key, member in quarantine.items() if key != "record_sigil"
    })
    quarantine_state["quarantines"] = [quarantine]
    quarantine_state["open_intents"] = [{
        "intent_kind": "QUARANTINE_MOVE", "intent_id": "SQ-ONE", "owner_id": "SA-ONE",
        "source_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
                         "event_sigil": SIGIL}, "intent_sigil": SIGIL, "revision": 1,
        "last_event_sigil": SIGIL, "authorization_expires_at": None,
        "source_object": object_ref, "target_object": object_ref,
    }]
    quarantine_state["state_sigil"] = content_sigil({
        key: member for key, member in quarantine_state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(quarantine_state)

    mismatched_quarantine_owner = deepcopy(quarantine_state)
    mismatched_quarantine_owner["open_intents"][0]["owner_id"] = "SA-OTHER"
    mismatched_quarantine_owner["state_sigil"] = content_sigil({
        key: member for key, member in mismatched_quarantine_owner.items()
        if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Quarantine move Intent disagrees"):
        validate_artifact_storage_state_v1(mismatched_quarantine_owner)

    missing_quarantine_intent = deepcopy(quarantine_state)
    missing_quarantine_intent["open_intents"] = []
    missing_quarantine_intent["state_sigil"] = content_sigil({
        key: member for key, member in missing_quarantine_intent.items()
        if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Quarantine move Intent disagrees"):
        validate_artifact_storage_state_v1(missing_quarantine_intent)

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
    with pytest.raises(AthanorError, match="has no matching Blob projection"):
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

    committed_state = deepcopy(state)
    committed_attempt = _transfer_attempt()
    target = {
        "backend_id": "BACKEND", "object_identity_sigil": SIGIL,
        "locator_sigil": SIGIL, "generation": "GENERATION", "size_bytes": 0,
        "blob_sigil": SIGIL,
    }
    committed_attempt.update({
        "state": "COMMITTED", "staging_state": "MISSING", "staging_object": target,
        "commit_intent": {
            "intent_id": "INTENT", "provisional_replica_id": "SR-ONE",
            "staging_object": target, "target_object": target,
            "computed_blob": {"blob_sigil": SIGIL, "size_bytes": 0},
            "execution_fence": None, "reservation": committed_attempt["reservation"],
            "recorded_clock": committed_attempt["reservation"]["created_clock"],
        },
        "residual_staging_cleanup": {"state": "NOT_REQUIRED", "staging_object": None,
                                     "evidence_sigil": None, "reason": None},
        "computed_blob_sigil": SIGIL, "computed_size_bytes": 0,
        "selected_replica_id": "SR-ONE", "terminal_at": STAMP,
    })
    committed_attempt["record_sigil"] = content_sigil({
        key: member for key, member in committed_attempt.items() if key != "record_sigil"
    })
    selected_replica = deepcopy(replica)
    selected_replica.update({
        "state": "AVAILABLE", "verification": {
            "method": "FULL_READBACK_SHA256", "evidence_sigil": SIGIL,
            "verified_at": STAMP, "next_due_at": None,
        },
    })
    selected_replica["record_sigil"] = content_sigil({
        key: member for key, member in selected_replica.items() if key != "record_sigil"
    })
    committed_state["replicas"] = [{"record": selected_replica, "last_event_sigil": SIGIL}]
    committed_blob = {
        "schema_version": "artifact-blob/1.0", "blob_sigil": SIGIL, "size_bytes": 0,
        "first_verified_at": None, "availability": "AVAILABLE",
        "availability_as_of": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
                              "event_sigil": SIGIL}, "availability_basis_sigil": SIGIL,
        "effective_policy_set_sigil": SIGIL, "next_verification_due_at": None,
        "known_replica_ids": ["SR-ONE"], "eligible_replica_ids": [],
        "integrity_event_sigils": [], "media_type_observations": [],
        "filename_observations": [], "revision": 1, "record_sigil": "",
    }
    committed_blob["record_sigil"] = content_sigil({
        key: member for key, member in committed_blob.items() if key != "record_sigil"
    })
    committed_state["blobs"] = [{"record": committed_blob, "last_event_sigil": SIGIL}]
    committed_state["availability_counters"]["available_blobs"] = 1
    committed_state["transfer_attempts"] = [{
        "record": committed_attempt, "last_event_sigil": SIGIL,
    }]
    committed_state["transfer_requests"] = [{
        "transfer_id": committed_attempt["transfer_id"], "request_record_sigil": SIGIL,
        "state": "ACTIVE", "attempt_ids": [committed_attempt["transfer_attempt_id"]],
        "selected_attempt_id": None, "revision": 1, "last_event_sigil": SIGIL,
    }]
    committed_state["state_sigil"] = content_sigil({
        key: member for key, member in committed_state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(committed_state)

    missing_selected = deepcopy(committed_state)
    missing_selected["replicas"] = []
    missing_selected["blobs"][0]["record"]["known_replica_ids"] = []
    missing_selected["blobs"][0]["record"]["record_sigil"] = content_sigil({
        key: member for key, member in missing_selected["blobs"][0]["record"].items()
        if key != "record_sigil"
    })
    missing_selected["state_sigil"] = content_sigil({
        key: member for key, member in missing_selected.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="lacks its selected Replica"):
        validate_artifact_storage_state_v1(missing_selected)

    committing_state = deepcopy(state)
    committing_attempt = _transfer_attempt()
    committing_object = {
        "backend_id": "BACKEND", "object_identity_sigil": SIGIL,
        "locator_sigil": SIGIL, "generation": "GENERATION", "size_bytes": 0,
        "blob_sigil": None,
    }
    committing_attempt.update({
        "state": "COMMITTING", "staging_state": "PRESENT", "staging_object": committing_object,
        "commit_intent": {
            "intent_id": "INTENT", "provisional_replica_id": "SR-ONE",
            "staging_object": committing_object, "target_object": committing_object,
            "computed_blob": {"blob_sigil": SIGIL, "size_bytes": 0},
            "execution_fence": None, "reservation": committing_attempt["reservation"],
            "recorded_clock": committing_attempt["reservation"]["created_clock"],
        },
    })
    committing_attempt["record_sigil"] = content_sigil({
        key: member for key, member in committing_attempt.items() if key != "record_sigil"
    })
    committing_state["transfer_attempts"] = [{"record": committing_attempt, "last_event_sigil": SIGIL}]
    committing_state["transfer_requests"] = [{
        "transfer_id": committing_attempt["transfer_id"], "request_record_sigil": SIGIL,
        "state": "ACTIVE", "attempt_ids": [committing_attempt["transfer_attempt_id"]],
        "selected_attempt_id": None, "revision": 1, "last_event_sigil": SIGIL,
    }]
    committing_state["open_intents"] = [{
        "intent_kind": "TRANSFER_COMMIT", "intent_id": "INTENT",
        "owner_id": committing_attempt["transfer_attempt_id"],
        "source_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
                         "event_sigil": SIGIL}, "intent_sigil": SIGIL, "revision": 1,
        "last_event_sigil": SIGIL, "authorization_expires_at": None,
        "staging_object": committing_object, "target_object": committing_object,
    }]
    committing_state["state_sigil"] = content_sigil({
        key: member for key, member in committing_state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(committing_state)

    missing_intent = deepcopy(committing_state)
    missing_intent["open_intents"] = []
    missing_intent["state_sigil"] = content_sigil({
        key: member for key, member in missing_intent.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="commit Intent disagrees with record state"):
        validate_artifact_storage_state_v1(missing_intent)

    disposition_state = deepcopy(state)
    disposition_state["dispositions"] = [{
        "disposition_id": "SD-ONE", "record_sigil": SIGIL, "state": "EXECUTING",
        "execution_intent_id": "INTENT", "outcome_sigil": None,
        "revision": 1, "last_event_sigil": SIGIL,
    }]
    disposition_state["open_intents"] = [{
        "intent_kind": "DISPOSITION", "intent_id": "INTENT", "owner_id": "SD-ONE",
        "source_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
                         "event_sigil": SIGIL}, "intent_sigil": SIGIL, "revision": 1,
        "last_event_sigil": SIGIL, "authorization_expires_at": STAMP,
        "target_kind": "STAGING", "target_object": committing_object,
    }]
    disposition_state["state_sigil"] = content_sigil({
        key: member for key, member in disposition_state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(disposition_state)

    missing_disposition_intent = deepcopy(disposition_state)
    missing_disposition_intent["open_intents"] = []
    missing_disposition_intent["state_sigil"] = content_sigil({
        key: member for key, member in missing_disposition_intent.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="Disposition execution Intent disagrees"):
        validate_artifact_storage_state_v1(missing_disposition_intent)

    canonical_state = deepcopy(state)
    canonical_state["canonical_reference_intents"] = [{
        "reference_intent_id": "RI-ONE", "record_sigil": SIGIL, "state": "OPEN",
        "chronicle_commit": None, "release_kind": None, "release_authority_sigil": None,
        "release_reason": None, "revision": 1, "last_event_sigil": SIGIL,
    }]
    canonical_state["open_intents"] = [{
        "intent_kind": "CANONICAL_REFERENCE", "intent_id": "RI-ONE", "owner_id": "RI-ONE",
        "source_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
                         "event_sigil": SIGIL}, "intent_sigil": SIGIL, "revision": 1,
        "last_event_sigil": SIGIL, "authorization_expires_at": None,
        "expected_chronicle_head": {"schema_version": "chronicle-head/1.1", "event_count": 0,
                                     "terminal_receipt_sigil": None},
        "blob_sigils": [], "reference_set_sigils": [],
    }]
    canonical_state["state_sigil"] = content_sigil({
        key: member for key, member in canonical_state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(canonical_state)

    missing_canonical_intent = deepcopy(canonical_state)
    missing_canonical_intent["open_intents"] = []
    missing_canonical_intent["state_sigil"] = content_sigil({
        key: member for key, member in missing_canonical_intent.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="canonical-reference Intent disagrees"):
        validate_artifact_storage_state_v1(missing_canonical_intent)

    wrong_canonical_owner = deepcopy(canonical_state)
    wrong_canonical_owner["open_intents"][0]["owner_id"] = "RI-OTHER"  # type: ignore[index]
    wrong_canonical_owner["state_sigil"] = content_sigil({
        key: member for key, member in wrong_canonical_owner.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="canonical-reference Intent disagrees"):
        validate_artifact_storage_state_v1(wrong_canonical_owner)

    mismatched_selected = deepcopy(committed_state)
    mismatched_selected["replicas"][0]["record"]["object"]["generation"] = "OTHER"
    mismatched_selected["replicas"][0]["record"]["record_sigil"] = content_sigil({
        key: member for key, member in mismatched_selected["replicas"][0]["record"].items()
        if key != "record_sigil"
    })
    mismatched_selected["state_sigil"] = content_sigil({
        key: member for key, member in mismatched_selected.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="disagrees with selected Replica"):
        validate_artifact_storage_state_v1(mismatched_selected)

    materialization_state = deepcopy(replica_state)
    source_blob = {
        "schema_version": "artifact-blob/1.0", "blob_sigil": SIGIL, "size_bytes": 0,
        "first_verified_at": None, "availability": "AVAILABLE",
        "availability_as_of": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
                              "event_sigil": SIGIL}, "availability_basis_sigil": SIGIL,
        "effective_policy_set_sigil": SIGIL, "next_verification_due_at": None,
        "known_replica_ids": ["SR-ONE"], "eligible_replica_ids": [],
        "integrity_event_sigils": [], "media_type_observations": [],
        "filename_observations": [], "revision": 1, "record_sigil": "",
    }
    source_blob["record_sigil"] = content_sigil({
        key: member for key, member in source_blob.items() if key != "record_sigil"
    })
    materialization_state["blobs"] = [{"record": source_blob, "last_event_sigil": SIGIL}]
    materialization_state["availability_counters"]["available_blobs"] = 1
    materialization_state["materializations"] = [{
        "record": _materialization(), "last_event_sigil": SIGIL,
    }]
    materialization_state["state_sigil"] = content_sigil({
        key: member for key, member in materialization_state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(materialization_state)

    missing_source = deepcopy(materialization_state)
    missing_source["replicas"] = []
    missing_source["blobs"][0]["record"]["known_replica_ids"] = []
    missing_source["blobs"][0]["record"]["record_sigil"] = content_sigil({
        key: member for key, member in missing_source["blobs"][0]["record"].items()
        if key != "record_sigil"
    })
    missing_source["state_sigil"] = content_sigil({
        key: member for key, member in missing_source.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="lacks its source Replica"):
        validate_artifact_storage_state_v1(missing_source)

    wrong_source_blob = deepcopy(materialization_state)
    wrong_source_blob["materializations"][0]["record"]["source_blob_sigil"] = SIGIL_B
    wrong_source_blob["materializations"][0]["record"]["record_sigil"] = content_sigil({
        key: member for key, member in wrong_source_blob["materializations"][0]["record"].items()
        if key != "record_sigil"
    })
    wrong_source_blob["state_sigil"] = content_sigil({
        key: member for key, member in wrong_source_blob.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="source Replica disagrees with Blob"):
        validate_artifact_storage_state_v1(wrong_source_blob)

    blob_state = deepcopy(state)
    blob = {
        "schema_version": "artifact-blob/1.0", "blob_sigil": SIGIL, "size_bytes": 0,
        "first_verified_at": None, "availability": "AVAILABLE",
        "availability_as_of": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
                              "event_sigil": SIGIL}, "availability_basis_sigil": SIGIL,
        "effective_policy_set_sigil": SIGIL, "next_verification_due_at": None,
        "known_replica_ids": [], "eligible_replica_ids": [], "integrity_event_sigils": [],
        "media_type_observations": [], "filename_observations": [], "revision": 1,
        "record_sigil": "",
    }
    blob["record_sigil"] = content_sigil({
        key: member for key, member in blob.items() if key != "record_sigil"
    })
    blob_state["blobs"] = [{"record": blob, "last_event_sigil": SIGIL}]
    blob_state["availability_counters"]["available_blobs"] = 1
    blob_state["state_sigil"] = content_sigil({
        key: member for key, member in blob_state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(blob_state)

    linked_blob_state = deepcopy(blob_state)
    linked_replica = deepcopy(replica)
    linked_replica["state"] = "AVAILABLE"
    linked_replica["verification"] = {
        "method": "FULL_READBACK_SHA256", "evidence_sigil": SIGIL,
        "verified_at": STAMP, "next_due_at": None,
    }
    linked_replica["record_sigil"] = content_sigil({
        key: member for key, member in linked_replica.items() if key != "record_sigil"
    })
    linked_blob_state["replicas"] = [{"record": linked_replica, "last_event_sigil": SIGIL}]
    linked_blob_state["blobs"][0]["record"]["known_replica_ids"] = ["SR-ONE"]
    linked_blob_state["blobs"][0]["record"]["record_sigil"] = content_sigil({
        key: member for key, member in linked_blob_state["blobs"][0]["record"].items()
        if key != "record_sigil"
    })
    linked_blob_state["state_sigil"] = content_sigil({
        key: member for key, member in linked_blob_state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(linked_blob_state)

    missing_known = deepcopy(linked_blob_state)
    missing_known["blobs"][0]["record"]["known_replica_ids"] = []
    missing_known["blobs"][0]["record"]["record_sigil"] = content_sigil({
        key: member for key, member in missing_known["blobs"][0]["record"].items()
        if key != "record_sigil"
    })
    missing_known["state_sigil"] = content_sigil({
        key: member for key, member in missing_known.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="known Replicas disagree"):
        validate_artifact_storage_state_v1(missing_known)

    unknown_eligible = deepcopy(linked_blob_state)
    unknown_eligible["blobs"][0]["record"]["eligible_replica_ids"] = ["SR-UNKNOWN"]
    unknown_eligible["blobs"][0]["record"]["record_sigil"] = content_sigil({
        key: member for key, member in unknown_eligible["blobs"][0]["record"].items()
        if key != "record_sigil"
    })
    unknown_eligible["state_sigil"] = content_sigil({
        key: member for key, member in unknown_eligible.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="eligible Replicas are not known"):
        validate_artifact_storage_state_v1(unknown_eligible)

    orphan_replica = deepcopy(replica_state)
    with pytest.raises(AthanorError, match="has no matching Blob projection"):
        validate_artifact_storage_state_v1(orphan_replica)

    bad_counters = deepcopy(blob_state)
    bad_counters["availability_counters"]["available_blobs"] = 0
    bad_counters["state_sigil"] = content_sigil({
        key: member for key, member in bad_counters.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="availability counters disagree"):
        validate_artifact_storage_state_v1(bad_counters)

    quota_state = deepcopy(state)
    claim = {
        "quota_class": "STAGING", "byte_count": 1, "object_count": 0,
        "inode_count": 0, "stream_count": 0, "journal_bytes": 0,
        "control_record_bytes": 0,
    }
    quota_state["quota_reservations"] = [{
        "reservation": {
            "reservation_id": "RESERVATION", "claims": [claim],
            "capacity_plan": {
                "allowed_event_types": ["transfer.prepared"], "max_event_frame_count": 1,
                "max_control_record_count": 0, "max_recovery_evidence_count": 0,
                "max_event_frame_bytes": 1, "max_control_record_bytes": 1,
                "max_recovery_evidence_bytes": 1,
            }, "expires_at": None, "created_clock": state["clock_anchor"],
            "remaining_micros_at_creation": None,
        }, "owner_kind": "TRANSFER_ATTEMPT", "owner_id": "SA-ONE",
        "purpose": "PAYLOAD_LIFECYCLE", "state": "ACTIVE", "consumed_claims": [],
        "released_claims": [], "remaining_claims": [deepcopy(claim)], "retained_for_event_types": [],
        "revision": 1, "last_event_sigil": SIGIL,
    }]
    quota_state["state_sigil"] = content_sigil({
        key: member for key, member in quota_state.items() if key != "state_sigil"
    })
    validate_artifact_storage_state_v1(quota_state)

    bad_claim = deepcopy(quota_state)
    bad_claim["quota_reservations"][0]["remaining_claims"][0]["journal_bytes"] = 1
    bad_claim["state_sigil"] = content_sigil({
        key: member for key, member in bad_claim.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="illegal quota dimension"):
        validate_artifact_storage_state_v1(bad_claim)

    exceeds_claim = deepcopy(quota_state)
    exceeds_claim["quota_reservations"][0]["remaining_claims"][0]["byte_count"] = 2
    exceeds_claim["state_sigil"] = content_sigil({
        key: member for key, member in exceeds_claim.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="exceeds its original claim"):
        validate_artifact_storage_state_v1(exceeds_claim)

    unpartitioned = deepcopy(quota_state)
    unpartitioned["quota_reservations"][0]["remaining_claims"] = []
    unpartitioned["state_sigil"] = content_sigil({
        key: member for key, member in unpartitioned.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="do not partition original claim"):
        validate_artifact_storage_state_v1(unpartitioned)

    retained_without_events = deepcopy(quota_state)
    retained_without_events["quota_reservations"][0]["state"] = "RETAINED"
    retained_without_events["state_sigil"] = content_sigil({
        key: member for key, member in retained_without_events.items() if key != "state_sigil"
    })
    with pytest.raises(AthanorError, match="retained Quota Reservation lacks"):
        validate_artifact_storage_state_v1(retained_without_events)
