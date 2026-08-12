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
    load_artifact_storage_backend_v1,
    load_artifact_retention_policy_v1,
    load_artifact_storage_legacy_protection_v1,
    load_artifact_storage_recovery_marker_v1,
    load_artifact_storage_reference_intent_v1,
    load_artifact_storage_reference_set_v1,
    load_artifact_storage_tail_evidence_v1,
    load_artifact_storage_state_v1,
    require_artifact_storage_journal_replay_authority_v1,
    require_artifact_storage_runtime_authority_v1,
    validate_artifact_storage_journal_event_v1,
    validate_artifact_storage_journal_head_supplied_event_v1,
    validate_artifact_storage_journal_head_supplied_prefix_v1,
    validate_artifact_storage_journal_head_v1,
    validate_artifact_storage_journal_prefix_v1,
    validate_artifact_storage_disposition_v1,
    validate_artifact_gc_plan_v1,
    validate_artifact_provenance_v1,
    validate_artifact_storage_backend_v1,
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
