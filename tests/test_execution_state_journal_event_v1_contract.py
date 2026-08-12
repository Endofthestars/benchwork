import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from benchwork.athanor import content_sigil
from benchwork.execution_contracts import (
    EXECUTION_EVENT_TYPES_V1,
    IDEMPOTENCY_OPERATION_KINDS_V1,
    build_execution_journal_event_v1,
    derive_observation_evidence_id_v1,
    derive_observation_evidence_subject_sigil_v1,
    derive_execution_observation_cursor_sigil_v1,
    derive_execution_storage_root_manifest_id_v1,
    derive_execution_root_hold_release_authorization_id_v1,
    derive_execution_control_evidence_set_id_v1,
    derive_execution_quarantine_binding_set_id_v1,
    derive_execution_output_storage_observation_set_id_v1,
    derive_result_ingress_receipt_id_v1,
    expected_event_causation_v1,
    expected_event_idempotency_v1,
    load_execution_journal_event_v1,
    load_execution_journal_head_v1,
    load_execution_observation_evidence_v1,
    load_execution_request_v1,
    load_execution_result_ingress_receipt_v1,
    load_execution_result_ingress_index_v1,
    load_execution_recovery_action_set_v1,
    load_execution_state_v1,
    load_execution_storage_root_manifest_v1,
    load_execution_root_hold_release_authorization_v1,
    load_execution_control_evidence_set_v1,
    load_execution_quarantine_binding_set_v1,
    load_execution_output_storage_observation_set_v1,
    replay_execution_initial_prefix_v1,
    replay_execution_journal_prefix_v1,
    replay_execution_empty_recovery_phase_prefix_v1,
    validate_execution_journal_prefix_wire_v1,
    validate_execution_observation_evidence_v1,
    validate_execution_observation_evidence_supplied_receipt_v1,
    validate_execution_journal_head_v1,
    validate_execution_initial_state_supplied_facts_v1,
    validate_execution_request_v1,
    validate_execution_result_ingress_receipt_v1,
    validate_execution_result_ingress_index_v1,
    validate_execution_recovery_action_set_v1,
    validate_execution_recovery_action_set_supplied_prefix_v1,
    validate_execution_recovery_start_supplied_action_set_v1,
    validate_execution_recovery_phase_advance_supplied_action_sets_v1,
    validate_execution_recovery_rebase_supplied_action_sets_v1,
    validate_execution_recovery_completion_supplied_action_set_v1,
    validate_execution_state_supplied_recovery_action_set_v1,
    validate_execution_recovery_action_supplied_event_v1,
    validate_execution_storage_root_manifest_v1,
    validate_execution_root_hold_release_authorization_v1,
    validate_execution_control_evidence_set_v1,
    validate_execution_quarantine_binding_set_v1,
    validate_execution_output_storage_observation_set_v1,
)
ROOT = Path(__file__).parents[1]
SCHEMAS = ROOT / "schemas"
FIXTURES = ROOT / "tests" / "fixtures" / "phase3" / "rfc0012"
SIGIL = "sha256:" + "a" * 64
SIGIL_B = "sha256:" + "b" * 64
STAMP = "2026-08-06T00:00:00Z"
JOB_ID = "JB-" + "A" * 64
SESSION_ID = "WS-" + "0" * 26
LEASE_ID = "LS-" + "0" * 26


def _reseal_state(state: dict[str, Any]) -> None:
    state["state_sigil"] = content_sigil(
        {key: member for key, member in state.items() if key != "state_sigil"}
    )


def _state_with_session_and_lease() -> dict[str, Any]:
    state = json.loads((FIXTURES / "execution-state-v1" / "valid-initial.json").read_text())
    state["workers"] = [{
        "worker_id": "WK-ONE", "revision": 0, "state": "ENABLED",
        "worker_binding_sigil": SIGIL, "definition_revision": 0,
        "worker_session_ids": [SESSION_ID], "last_event_id": "JE-ONE", "last_event_sigil": SIGIL,
    }]
    state["worker_sessions"] = [{
        "worker_session_id": SESSION_ID, "revision": 0, "state": "READY", "worker_id": "WK-ONE",
        "worker_binding_sigil": SIGIL, "worker_session_binding_sigil": SIGIL, "executor_epoch": 1,
        "worker_session_heartbeat_policy_id": "WSHP-" + "A" * 64,
        "worker_session_heartbeat_policy_sigil": SIGIL, "capacity": 1, "capacity_in_use": 1,
        "last_heartbeat_sequence": 1, "last_heartbeat_message_sigil": SIGIL,
        "last_resource_sample_sigil": SIGIL,
        "resource_counter_floors": {"cpu_time_seconds": None, "storage_bytes_written": None, "network_egress_bytes": None},
        "next_heartbeat_due_at": STAMP, "lease_ids": [LEASE_ID], "last_event_id": "JE-ONE", "last_event_sigil": SIGIL,
    }]
    state["leases"] = [{
        "lease_id": LEASE_ID, "revision": 0, "state": "ACTIVE", "lease_binding_sigil": SIGIL,
        "job_id": JOB_ID, "attempt_id": "AT-ONE", "worker_id": "WK-ONE", "worker_session_id": SESSION_ID,
        "executor_epoch": 1, "fencing_generation": 0, "claim_due_at": STAMP, "expiry_due_at": STAMP,
        "maximum_expiry_due_at": STAMP, "last_heartbeat_sequence": 1,
        "last_heartbeat_message_sigil": SIGIL, "last_resource_sample_sigil": SIGIL,
        "resource_counter_floors": {"cpu_time_seconds": None, "storage_bytes_written": None, "network_egress_bytes": None},
        "next_heartbeat_due_at": STAMP, "renewal_counter": 0, "terminal_event_binding": {"kind": "NONE"},
        "tombstone_generation": None, "tombstone_event_sigil": None, "last_event_id": "JE-ONE", "last_event_sigil": SIGIL,
    }]
    _reseal_state(state)
    return state


def _event_unsigned() -> dict[str, Any]:
    return {
        "schema_version": "execution-journal-event/1.0",
        "journal_id": "EJ-ONE",
        "event_id": "JE-TWO",
        "sequence": 2,
        "event_type": "log.chunk_committed",
        "executor_instance_id": "XI-ONE",
        "executor_epoch": 1,
        "executor_build_sigil": SIGIL,
        "recorded_at": STAMP,
        "observed_at": None,
        "entity_revisions": [
            {
                "entity_kind": "LOG_STREAM",
                "entity_id": "LG-ONE",
                "preceding_revision": 0,
                "next_revision": 1,
            }
        ],
        "causation_event_id": None,
            "idempotency_key_sigil": SIGIL,
        "recovery_action_binding": None,
        "payload": {
            "intake_kind": "CHUNK",
            "intake_id": "LCI-ONE",
            "intake_record_sigil": SIGIL,
            "disposition_intent_id": "LDI-ONE",
            "log_stream_id": "LG-ONE",
            "chunk_record_sigil": SIGIL,
            "stream": "STDOUT",
            "sequence": 0,
            "blob_sigil": SIGIL,
            "captured_bytes_after": 1,
        },
        "previous_event_sigil": SIGIL_B,
    }


def _clock_uncertain_event(initial: dict[str, Any]) -> dict[str, Any]:
    event = {
        "schema_version": "execution-journal-event/1.0", "journal_id": initial["journal_id"],
        "event_id": "JE-TWO", "sequence": 2, "event_type": "executor.clock_uncertain",
        "executor_instance_id": initial["executor_instance_id"],
        "executor_epoch": initial["executor_epoch"],
        "executor_build_sigil": initial["executor_build_sigil"],
        "recorded_at": "2026-08-06T00:00:01Z", "observed_at": None,
        "entity_revisions": [{
            "entity_kind": "EXECUTOR", "entity_id": initial["executor_instance_id"],
            "preceding_revision": 0, "next_revision": 1,
        }],
        "causation_event_id": None, "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {
            "last_trusted_utc": initial["recorded_at"],
            "detected_utc": "2026-08-06T00:00:01Z", "monotonic_status": "RESET",
            "divergence_seconds": 0, "affected_lease_ids": [],
        },
        "previous_event_sigil": initial["event_sigil"],
    }
    event["event_sigil"] = content_sigil(event)
    return event


def _recovery_started_event(clock_uncertain: dict[str, Any]) -> dict[str, Any]:
    event = {
        "schema_version": "execution-journal-event/1.0", "journal_id": clock_uncertain["journal_id"],
        "event_id": "JE-THREE", "sequence": 3, "event_type": "recovery.started",
        "executor_instance_id": clock_uncertain["executor_instance_id"],
        "executor_epoch": clock_uncertain["executor_epoch"],
        "executor_build_sigil": clock_uncertain["executor_build_sigil"],
        "recorded_at": "2026-08-06T00:00:02Z", "observed_at": None,
        "entity_revisions": [
            {"entity_kind": "EXECUTOR", "entity_id": clock_uncertain["executor_instance_id"],
             "preceding_revision": 1, "next_revision": 2},
            {"entity_kind": "RECOVERY", "entity_id": "RY-ONE",
             "preceding_revision": None, "next_revision": 0},
        ],
        "causation_event_id": None, "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {
            "recovery_id": "RY-ONE", "prior_recovery_id": None,
            "replay_through_sequence": 2,
            "replay_through_event_sigil": clock_uncertain["event_sigil"],
            "old_epoch": clock_uncertain["executor_epoch"],
            "new_epoch": clock_uncertain["executor_epoch"],
            "nonterminal_job_ids": [], "nonterminal_attempt_ids": [],
            "nonterminal_lease_ids": [], "nonterminal_worker_session_ids": [],
            "initial_action_set_sigil": SIGIL,
        },
        "previous_event_sigil": clock_uncertain["event_sigil"],
    }
    event["event_sigil"] = content_sigil(event)
    return event


def _recovery_action_set() -> dict[str, Any]:
    action_set = {
        "schema_version": "execution-recovery-action-set/1.0", "recovery_id": "RY-ONE",
        "phase": "STARTED", "derived_from_journal_id": "EJ-ONE",
        "derived_through_sequence": 2, "derived_through_event_sigil": SIGIL,
        "supersedes_action_set_sigil": None,
        "actions": [{
            "ordinal": 0, "action_kind": "COMMIT_DUE_EVENT", "entity_kind": "JOB",
            "entity_id": "JB-ONE", "expected_revision": 0, "target_event_id": "JE-FOUR",
            "target_sequence": 4, "target_event_type": "job.stop_latched",
            "prerequisite_event_ids": ["JE-ONE", "JE-TWO"],
            "parameters": {"deadline_kind": "JOB_DEADLINE", "due_at": STAMP, "deadline_entity_id": "JB-ONE"},
        }],
    }
    action_set["action_set_sigil"] = content_sigil(action_set)
    return action_set


def _empty_recovery_action_set(
    phase: str, prefix: list[dict[str, Any]],
) -> dict[str, Any]:
    action_set = {
        "schema_version": "execution-recovery-action-set/1.0", "recovery_id": "RY-ONE",
        "phase": phase, "derived_from_journal_id": prefix[-1]["journal_id"],
        "derived_through_sequence": prefix[-1]["sequence"],
        "derived_through_event_sigil": prefix[-1]["event_sigil"],
        "supersedes_action_set_sigil": None, "actions": [], "action_set_sigil": "",
    }
    action_set["action_set_sigil"] = content_sigil({
        key: member for key, member in action_set.items() if key != "action_set_sigil"
    })
    return action_set


def _recovery_phase_event(
    prior_event: dict[str, Any], completed_set: dict[str, Any], next_set: dict[str, Any],
    event_id: str,
) -> dict[str, Any]:
    event = {
        "schema_version": "execution-journal-event/1.0", "journal_id": prior_event["journal_id"],
        "event_id": event_id, "sequence": prior_event["sequence"] + 1,
        "event_type": "recovery.phase_advanced",
        "executor_instance_id": prior_event["executor_instance_id"],
        "executor_epoch": prior_event["executor_epoch"],
        "executor_build_sigil": prior_event["executor_build_sigil"],
        "recorded_at": f"2026-08-06T00:00:0{prior_event['sequence']}Z", "observed_at": None,
        "entity_revisions": [{"entity_kind": "RECOVERY", "entity_id": "RY-ONE",
                              "preceding_revision": prior_event["sequence"] - 3,
                              "next_revision": prior_event["sequence"] - 2}],
        "causation_event_id": None, "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {"recovery_id": "RY-ONE", "from_phase": completed_set["phase"],
                    "to_phase": next_set["phase"],
                    "completed_action_set_sigil": completed_set["action_set_sigil"],
                    "next_action_set_sigil": next_set["action_set_sigil"],
                    "completed_entity_ids": [], "quarantined_entity_ids": []},
        "previous_event_sigil": prior_event["event_sigil"],
    }
    event["event_sigil"] = content_sigil(event)
    return event


def _recovery_action_event(action_set: dict[str, Any]) -> dict[str, Any]:
    action = action_set["actions"][0]
    event = {
        "schema_version": "execution-journal-event/1.0", "journal_id": "EJ-ONE",
        "event_id": action["target_event_id"], "sequence": action["target_sequence"],
        "event_type": action["target_event_type"], "executor_instance_id": "XI-ONE",
        "executor_epoch": 1, "executor_build_sigil": SIGIL,
        "recorded_at": "2026-08-06T00:00:02Z", "observed_at": None,
        "entity_revisions": [{"entity_kind": action["entity_kind"], "entity_id": action["entity_id"],
                              "preceding_revision": action["expected_revision"],
                              "next_revision": action["expected_revision"] + 1}],
        "causation_event_id": "JE-TWO", "idempotency_key_sigil": None,
        "recovery_action_binding": {"recovery_id": action_set["recovery_id"],
                                    "phase": action_set["phase"],
                                    "action_set_sigil": action_set["action_set_sigil"],
                                    "action_ordinal": action["ordinal"]},
        "payload": {"transition_cause": {"code": "JOB_DEADLINE",
                                            "trigger_kind": "RECOVERY_DERIVATION",
                                            "trigger_event_id": action["target_event_id"],
                                            "effective_sequence": action["target_sequence"],
                                            "evidence_sigil": SIGIL}, "request_binding": None},
        "previous_event_sigil": SIGIL_B,
    }
    event["event_sigil"] = content_sigil(event)
    return event


def _owner() -> dict[str, Any]:
    return {
        "job_id": JOB_ID,
        "job_binding_sigil": SIGIL,
        "attempt_id": "AT-ONE",
        "attempt_binding_sigil": SIGIL,
        "lease_id": LEASE_ID,
        "lease_binding_sigil": SIGIL,
        "worker_id": "WK-ONE",
        "worker_binding_sigil": SIGIL,
        "worker_session_id": SESSION_ID,
        "worker_session_binding_sigil": SIGIL,
        "executor_epoch": 1,
        "fence_tuple": {
            "journal_id": "EJ-ONE",
            "executor_epoch": 1,
            "job_id": JOB_ID,
            "attempt_id": "AT-ONE",
            "lease_id": LEASE_ID,
            "fencing_generation": 1,
        },
    }


def _result_observation(owner: dict[str, Any]) -> dict[str, Any]:
    binding = {
        "runtime_observation": {
            "started_at": STAMP,
            "ended_at": STAMP,
            "cpu_time_seconds": 0,
            "peak_memory_bytes": 0,
            "process_count": 0,
        },
        "termination_observation": {
            "kind": "EXITED",
            "exit_code": 0,
            "observed_at": STAMP,
            "observation_source": "WORKER",
        },
        "observation_evidence_subject_sigil": "",
    }
    binding["observation_evidence_subject_sigil"] = derive_observation_evidence_subject_sigil_v1(owner, binding)
    return binding


def _receipt() -> dict[str, Any]:
    owner = _owner()
    value: dict[str, Any] = {
        "schema_version": "execution-result-ingress-receipt/1.0",
        "ingress_receipt_id": "",
        "owner_binding": owner,
        "result_sigil": SIGIL_B,
        "result_observation_binding": _result_observation(owner),
        "received_at": STAMP,
        "control_channel_identity_sigil": SIGIL,
        "credential_verification": {
            "kind": "VERIFIED",
            "lease_credential_digest": SIGIL,
            "verification_profile_sigil": SIGIL,
            "verified_at": STAMP,
            "verification_sigil": "",
        },
        "receiver_identity": {
            "executor_instance_id": "XI-ONE",
            "executor_epoch": 1,
            "implementation_sigil": SIGIL,
        },
        "created_at": STAMP,
        "ingress_receipt_sigil": "",
    }
    value["ingress_receipt_id"] = derive_result_ingress_receipt_id_v1(value)
    verification = value["credential_verification"]
    verification["verification_sigil"] = content_sigil(
        [
            "execution-result-ingress-credential-verification/1.0",
            owner,
            value["result_sigil"],
            value["received_at"],
            value["control_channel_identity_sigil"],
            verification["lease_credential_digest"],
            verification["verification_profile_sigil"],
            verification["verified_at"],
        ]
    )
    value["ingress_receipt_sigil"] = content_sigil(
        {key: member for key, member in value.items() if key != "ingress_receipt_sigil"}
    )
    return value


def _result_ingress_index() -> dict[str, Any]:
    receipt = _receipt()
    candidate = _event_unsigned()
    candidate.update({
        "event_type": "attempt.result_ingress_received", "event_id": "JE-THREE",
        "sequence": 3, "previous_event_sigil": SIGIL,
        "entity_revisions": [{
            "entity_kind": "ATTEMPT", "entity_id": receipt["owner_binding"]["attempt_id"],
            "preceding_revision": 4, "next_revision": 5,
        }],
        "idempotency_key_sigil": content_sigil([
            "execution-result-ingress-key/1.0", receipt["owner_binding"]["attempt_id"], receipt["result_sigil"],
        ]),
        "payload": {
            "ingress_receipt_id": receipt["ingress_receipt_id"],
            "ingress_receipt_sigil": receipt["ingress_receipt_sigil"],
            "result_sigil": receipt["result_sigil"],
            "observation_evidence_subject_sigil": receipt["result_observation_binding"]["observation_evidence_subject_sigil"],
            "received_at": receipt["received_at"],
        },
    })
    candidate["event_sigil"] = content_sigil(candidate)
    intent = {
        "schema_version": "execution-result-ingress-event-intent/1.0",
        "ingress_event_intent_id": "OII-" + "A" * 64,
        "result_ingress_receipt_binding": {
            "ingress_receipt_id": receipt["ingress_receipt_id"],
            "ingress_receipt_sigil": receipt["ingress_receipt_sigil"],
        },
        "event_candidate": candidate, "created_at": STAMP, "intent_sigil": "",
    }
    intent["intent_sigil"] = content_sigil(
        {key: member for key, member in intent.items() if key != "intent_sigil"}
    )
    head = {
        "schema_version": "execution-journal-head/1.0", "limit_profile": "EXECUTION_JOURNAL_V1_FIXED_LIMITS",
        "journal_id": candidate["journal_id"], "last_sequence": 2, "last_event_id": "JE-TWO",
        "last_event_sigil": candidate["previous_event_sigil"], "updated_at": STAMP, "head_sigil": "",
    }
    head["head_sigil"] = content_sigil({key: member for key, member in head.items() if key != "head_sigil"})
    index = {
        "schema_version": "execution-result-ingress-index/1.0", "ingress_index_id": "OIX-" + "A" * 64,
        "attempt_id": receipt["owner_binding"]["attempt_id"], "result_sigil": receipt["result_sigil"],
        "idempotency_key_sigil": candidate["idempotency_key_sigil"], "event_id": candidate["event_id"],
        "result_ingress_receipt": receipt, "ingress_event_intent": intent,
        "status": {"kind": "PENDING_EVENT", "expected_prior_index_sigil": None,
                   "expected_journal_head": head, "installed_at": STAMP},
        "created_at": STAMP, "index_sigil": "",
    }
    index["index_sigil"] = content_sigil({key: member for key, member in index.items() if key != "index_sigil"})
    return index


def _storage_root_manifest() -> dict[str, Any]:
    subject = {
        "kind": "JOB_INPUT", "input_ordinal": 0,
        "input_identity": {"logical_name": "input", "object_id": "RP-ONE", "object_type": "research-program",
                           "object_sigil": SIGIL, "media_type": "application/json", "maximum_bytes": 1,
                           "mount_path": "input.json"},
        "input_sigil": SIGIL,
    }
    entry = {
        "storage_subject_id": content_sigil([
            "execution-storage-subject-id/1.0", "JOB_INPUT", JOB_ID, None, subject,
        ]),
        "subject": subject, "claimed_blob": None,
        "storage_origin": {"kind": "NOT_STORED", "transfer": None,
                           "terminal_reason": {"code": "BACKEND_UNAVAILABLE", "evidence_sigils": []},
                           "evidence_sigil": SIGIL},
        "entry_sigil": "",
    }
    entry["entry_sigil"] = content_sigil({key: member for key, member in entry.items() if key != "entry_sigil"})
    manifest = {
        "schema_version": "execution-storage-root-manifest/1.0", "manifest_id": "",
        "root_kind": "JOB_INPUT", "job_id": JOB_ID, "attempt_id": None,
        "owner_binding": {"kind": "JOB_INPUT", "start_request_sigil": SIGIL, "task_id": "TK-ONE",
                          "task_capsule_sigil": SIGIL, "specification_id": "ES-0" + "0" * 25,
                          "specification_sigil": SIGIL, "input_set_sigil": SIGIL},
        "entries": [entry], "blob_refs": [], "protection_plan": {"kind": "NONE"},
        "created_at": STAMP, "manifest_sigil": "",
    }
    manifest["manifest_id"] = derive_execution_storage_root_manifest_id_v1(manifest)
    manifest["manifest_sigil"] = content_sigil({key: member for key, member in manifest.items() if key != "manifest_sigil"})
    return manifest


def _root_hold_release_authorization() -> dict[str, Any]:
    root = {
        "root_kind": "JOB_INPUT", "job_id": JOB_ID, "attempt_id": None,
        "storage_root_manifest_id": "ESM-" + "A" * 64, "storage_root_manifest_sigil": SIGIL,
        "reference_set_id": "RS-ONE", "reference_set_sigil": SIGIL, "hold_id": "SH-ONE",
        "hold_set_event": {"journal_id": "EJ-ONE", "event_id": "JE-ONE", "sequence": 1, "event_sigil": SIGIL},
    }
    head = {
        "schema_version": "execution-journal-head/1.0", "limit_profile": "EXECUTION_JOURNAL_V1_FIXED_LIMITS",
        "journal_id": "EJ-ONE", "last_sequence": 3, "last_event_id": "JE-THREE",
        "last_event_sigil": SIGIL, "updated_at": STAMP, "head_sigil": "",
    }
    head["head_sigil"] = content_sigil({key: member for key, member in head.items() if key != "head_sigil"})
    authorization = {
        "schema_version": "execution-root-hold-release-authorization/1.0", "release_authorization_id": "",
        "execution_journal_id": "EJ-ONE", "storage_root": root,
        "policy": {"policy_id": "SP-EXECUTION-ROOT-HOLD-V1", "policy_sigil": SIGIL},
        "hold_set_authorization_sigil": SIGIL,
        "basis": {"kind": "OWNER_TERMINAL", "activation_event_id": "JE-ONE", "activation_event_sequence": 1,
                  "activation_event_sigil": SIGIL, "terminal_event_id": "JE-TWO", "terminal_event_sequence": 2,
                  "terminal_event_sigil": SIGIL_B, "terminal_event_type": "job.succeeded",
                  "verification_head": head, "verification_state_sigil": SIGIL},
        "release_authorization_sigil": "",
    }
    authorization["release_authorization_id"] = derive_execution_root_hold_release_authorization_id_v1(authorization)
    authorization["release_authorization_sigil"] = content_sigil({
        key: member for key, member in authorization.items() if key != "release_authorization_sigil"
    })
    return authorization


def _control_evidence_set() -> dict[str, Any]:
    dimensions = [
        "IDENTITY_AUTHORIZATION", "FILESYSTEM", "NETWORK", "PROCESS_EXECUTABLE", "RESOURCE",
        "ENVIRONMENT_CREDENTIAL", "LOG_OUTPUT_CAPTURE", "RUNTIME_INPUT_OUTPUT_IDENTITY",
        "CANCELLATION_FENCING", "TERMINATION_CLEANUP",
    ]
    evidence_set = {
        "schema_version": "execution-control-evidence-set/1.0", "control_evidence_set_id": "",
        "job_id": JOB_ID, "attempt_id": "AT-ONE", "attempt_binding_sigil": SIGIL,
        "control_evidence_refs": [
            {"control_dimension": dimension, "control_evidence_id": "CVE-0" + "0" * 25,
             "control_evidence_sigil": SIGIL if index == 0 else SIGIL_B}
            for index, dimension in enumerate(dimensions)
        ],
        "control_evidence_set_sigil": "",
    }
    for index, reference in enumerate(evidence_set["control_evidence_refs"]):
        reference["control_evidence_id"] = f"CVE-0{index:025d}"[-30:]
    evidence_set["control_evidence_set_id"] = derive_execution_control_evidence_set_id_v1(evidence_set)
    evidence_set["control_evidence_set_sigil"] = content_sigil({
        key: member for key, member in evidence_set.items() if key != "control_evidence_set_sigil"
    })
    return evidence_set


def _quarantine_binding_set() -> dict[str, Any]:
    binding_set = {
        "schema_version": "execution-quarantine-binding-set/1.0", "quarantine_binding_set_id": "",
        "job_id": JOB_ID, "attempt_id": "AT-ONE", "attempt_binding_sigil": SIGIL,
        "quarantine_plan_sigil": SIGIL,
        "terminalization_storage_manifest_binding": {
            "kind": "FROZEN", "storage_root_manifest_id": "ESM-" + "A" * 64,
            "storage_root_manifest_sigil": SIGIL,
        },
        "storage_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1, "event_sigil": SIGIL},
        "storage_state_sigil": SIGIL, "bindings": [], "quarantine_binding_set_sigil": "",
    }
    binding_set["quarantine_binding_set_id"] = derive_execution_quarantine_binding_set_id_v1(binding_set)
    binding_set["quarantine_binding_set_sigil"] = content_sigil({
        key: member for key, member in binding_set.items() if key != "quarantine_binding_set_sigil"
    })
    return binding_set


def _output_storage_observation_set() -> dict[str, Any]:
    storage_event = {
        "journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1,
        "event_sigil": SIGIL,
    }
    blob_storage = {
        "kind": "BLOB", "terminal_storage_status": "AVAILABLE", "blob_sigil": SIGIL,
        "size_bytes": 0, "blob_record_sigil": SIGIL_B, "availability": "AVAILABLE",
        "availability_as_of": storage_event, "availability_basis_sigil": SIGIL,
        "integrity_event_sigils": [], "quarantine": {"kind": "NONE"},
        "replica": {"kind": "NONE"},
    }
    origin = {
        "kind": "COMMITTED_BLOB", "transfer": {
            "transfer_id": "ST-ONE", "transfer_attempt_id": "SA-ONE",
            "request_record_sigil": SIGIL, "attempt_record_sigil": SIGIL_B,
            "terminal_event": storage_event,
        }, "provenance_id": "PROVENANCE", "provenance_sigil": SIGIL,
        "blob_record_sigil": SIGIL_B, "terminal_event": storage_event,
    }
    members = [{"kind": "ATTEMPT_OUTPUTS_NONE", "reason": "NO_RESULT"}]
    for stream in ("STDOUT", "STDERR", "STRUCTURED"):
        members.append({
            "kind": "LOG_STREAM", "storage_subject_id": SIGIL,
            "manifest_entry_sigil": SIGIL_B, "stream": stream,
            "log_stream_id": f"LG-{stream}", "final_sequence": None,
            "captured_bytes": 0, "dropped_bytes": 0, "truncated": False,
            "stream_set_sigil": SIGIL, "closure_event_id": "JE-ONE",
            "closure_event_sigil": SIGIL_B, "storage_origin": origin,
            "content": {"kind": "EMPTY", "blob_sigil": SIGIL, "storage": blob_storage},
        })
    members.extend([
        {"kind": "RESOURCE_EVIDENCE_NONE"},
        {"kind": "TERMINAL_SOURCE_NOT_APPLICABLE"},
    ])
    manifest = {
        "kind": "FROZEN", "storage_root_manifest_id": "ESM-" + "A" * 64,
        "storage_root_manifest_sigil": SIGIL,
    }
    observation_set = {
        "schema_version": "execution-output-storage-observation-set/1.0",
        "observation_set_id": "", "job_id": JOB_ID, "attempt_id": "AT-ONE",
        "attempt_binding_sigil": SIGIL, "result_binding": {"kind": "NONE"},
        "log_closure_sigil": SIGIL, "output_closure_sigil": SIGIL_B,
        "control_evidence_set_binding": {
            "kind": "FROZEN", "control_evidence_set_id": "CES-" + "A" * 64,
            "control_evidence_set_sigil": SIGIL,
        }, "quarantine_binding_set_binding": {
            "kind": "FROZEN", "quarantine_binding_set_id": "QBS-" + "A" * 64,
            "quarantine_binding_set_sigil": SIGIL,
        }, "terminalization_storage_manifest_binding": manifest,
        "output_root_protection": {
            "kind": "NO_HOLD", "terminalization_storage_manifest_binding": manifest,
        }, "terminal_source_binding": {"kind": "NOT_APPLICABLE"},
        "storage_event": storage_event, "storage_state_sigil": SIGIL,
        "members": members, "blob_sigils": [SIGIL], "observation_set_sigil": "",
    }
    observation_set["observation_set_id"] = derive_execution_output_storage_observation_set_id_v1(observation_set)
    observation_set["observation_set_sigil"] = content_sigil({
        key: member for key, member in observation_set.items() if key != "observation_set_sigil"
    })
    return observation_set


def _evidence(receipt: dict[str, Any]) -> dict[str, Any]:
    owner = _owner()
    runtime = receipt["result_observation_binding"]["runtime_observation"]
    termination = receipt["result_observation_binding"]["termination_observation"]
    source = {
        "source_kind": "WORKER",
        "source_identity_id": "SOURCE",
        "source_identity_sigil": SIGIL,
        "source_identity_profile_sigil": SIGIL,
        "source_channel_sigil": SIGIL,
        "source_channel_profile_sigil": SIGIL,
        "source_registry_id": "REGISTRY",
        "source_registry_version": "1.0",
        "source_registry_snapshot_sigil": SIGIL,
    }
    value = {
        "schema_version": "execution-observation-evidence/1.0",
        "observation_evidence_id": "",
        **owner,
        "result_observation_binding": receipt["result_observation_binding"],
        "result_ingress_receipt_binding": {
            "ingress_receipt_id": receipt["ingress_receipt_id"],
            "ingress_receipt_sigil": receipt["ingress_receipt_sigil"],
        },
        "producer_evidence_binding": {
            "raw_evidence_id": "ORE-" + "A" * 64,
            "raw_evidence_record_sigil": SIGIL,
        },
        "verifier_evidence_binding": {
            "raw_evidence_id": "ORE-" + "B" * 64,
            "raw_evidence_record_sigil": SIGIL_B,
        },
        "evidence_profile_binding": {
            "evidence_profile_id": "PROFILE",
            "evidence_profile_version": "1.0",
            "evidence_profile_sigil": SIGIL,
        },
        "assessment": {
            "kind": "MATCHED",
            "verified_runtime_observation": runtime,
            "verified_termination_observation": termination,
            "verified_source_binding": source,
            "reason_bindings": [],
        },
        "created_at": STAMP,
        "observation_evidence_sigil": "",
    }
    value["observation_evidence_id"] = derive_observation_evidence_id_v1(value)
    value["observation_evidence_sigil"] = content_sigil(
        {key: member for key, member in value.items() if key != "observation_evidence_sigil"}
    )
    return value


def _reseal_receipt(receipt: dict[str, Any]) -> None:
    receipt["ingress_receipt_id"] = derive_result_ingress_receipt_id_v1(receipt)
    verification = receipt["credential_verification"]
    verification["verification_sigil"] = content_sigil(
        [
            "execution-result-ingress-credential-verification/1.0",
            receipt["owner_binding"],
            receipt["result_sigil"],
            receipt["received_at"],
            receipt["control_channel_identity_sigil"],
            verification["lease_credential_digest"],
            verification["verification_profile_sigil"],
            verification["verified_at"],
        ]
    )
    receipt["ingress_receipt_sigil"] = content_sigil(
        {key: member for key, member in receipt.items() if key != "ingress_receipt_sigil"}
    )


def _reseal_evidence(evidence: dict[str, Any]) -> None:
    owner = {
        member: evidence[member]
        for member in (
            "job_id", "job_binding_sigil", "attempt_id", "attempt_binding_sigil",
            "lease_id", "lease_binding_sigil", "worker_id", "worker_binding_sigil",
            "worker_session_id", "worker_session_binding_sigil", "executor_epoch", "fence_tuple",
        )
    }
    binding = evidence["result_observation_binding"]
    binding["observation_evidence_subject_sigil"] = derive_observation_evidence_subject_sigil_v1(owner, binding)
    evidence["observation_evidence_id"] = derive_observation_evidence_id_v1(evidence)
    evidence["observation_evidence_sigil"] = content_sigil(
        {key: member for key, member in evidence.items() if key != "observation_evidence_sigil"}
    )


def test_state_closes_19_24_projection_members_and_all_11_ranks() -> None:
    schema = json.loads((SCHEMAS / "execution-state-1.0.json").read_text())
    assert len(schema["$defs"]["worker_session_projection"]["required"]) == 19
    assert len(schema["$defs"]["lease_projection"]["required"]) == 24
    assert "anyOf" in schema["$defs"]["terminal_event_binding"]["oneOf"][1]["properties"]["terminal_state"]
    assert schema["$defs"]["idempotency_operation_kind"]["enum"] == list(
        IDEMPOTENCY_OPERATION_KINDS_V1
    )
    raw = (FIXTURES / "execution-state-v1" / "invalid-duplicate-key.json").read_text()
    with pytest.raises(Exception, match="duplicate JSON key"):
        load_execution_state_v1(raw)


def test_recovery_action_set_is_strictly_sealed_and_ordered() -> None:
    action_set = _recovery_action_set()
    assert load_execution_recovery_action_set_v1(json.dumps(action_set)) == action_set

    bad_ordinal = deepcopy(action_set)
    bad_ordinal["actions"][0]["ordinal"] = 1
    bad_ordinal["action_set_sigil"] = content_sigil(
        {key: member for key, member in bad_ordinal.items() if key != "action_set_sigil"}
    )
    with pytest.raises(Exception, match="ordinals must be contiguous"):
        validate_execution_recovery_action_set_v1(bad_ordinal)

    bad_target = deepcopy(action_set)
    bad_target["actions"][0]["target_sequence"] = 5
    bad_target["action_set_sigil"] = content_sigil(
        {key: member for key, member in bad_target.items() if key != "action_set_sigil"}
    )
    with pytest.raises(Exception, match="target sequence"):
        validate_execution_recovery_action_set_v1(bad_target)

    stale_sigil = deepcopy(action_set)
    stale_sigil["actions"][0]["expected_revision"] = 1
    with pytest.raises(Exception, match="self-Sigil"):
        validate_execution_recovery_action_set_v1(stale_sigil)

    unordered_prerequisites = deepcopy(action_set)
    unordered_prerequisites["actions"][0]["prerequisite_event_ids"].reverse()
    unordered_prerequisites["action_set_sigil"] = content_sigil(
        {key: member for key, member in unordered_prerequisites.items() if key != "action_set_sigil"}
    )
    with pytest.raises(Exception, match="prerequisite Event IDs"):
        validate_execution_recovery_action_set_v1(unordered_prerequisites)

    two_actions = deepcopy(action_set)
    second = deepcopy(two_actions["actions"][0])
    second.update({
        "ordinal": 1, "target_event_id": "JE-FIVE", "target_sequence": 5,
        "parameters": {
            "deadline_kind": "ATTEMPT_DEADLINE", "due_at": "2026-08-06T00:00:01Z",
            "deadline_entity_id": "JB-ONE",
        },
    })
    two_actions["actions"].append(second)
    two_actions["action_set_sigil"] = content_sigil(
        {key: member for key, member in two_actions.items() if key != "action_set_sigil"}
    )
    validate_execution_recovery_action_set_v1(two_actions)

    wrong_phase = deepcopy(action_set)
    wrong_phase["phase"] = "FENCING"
    wrong_phase["action_set_sigil"] = content_sigil(
        {key: member for key, member in wrong_phase.items() if key != "action_set_sigil"}
    )
    with pytest.raises(Exception, match="not allowed in its phase"):
        validate_execution_recovery_action_set_v1(wrong_phase)

    unordered_actions = deepcopy(two_actions)
    unordered_actions["actions"].reverse()
    for ordinal, action in enumerate(unordered_actions["actions"]):
        action["ordinal"] = ordinal
        action["target_sequence"] = unordered_actions["derived_through_sequence"] + 2 + ordinal
    unordered_actions["action_set_sigil"] = content_sigil(
        {key: member for key, member in unordered_actions.items() if key != "action_set_sigil"}
    )
    with pytest.raises(Exception, match="canonical order"):
        validate_execution_recovery_action_set_v1(unordered_actions)

    duplicate = deepcopy(two_actions)
    duplicate["actions"][1]["parameters"] = deepcopy(duplicate["actions"][0]["parameters"])
    duplicate["action_set_sigil"] = content_sigil(
        {key: member for key, member in duplicate.items() if key != "action_set_sigil"}
    )
    with pytest.raises(Exception, match="duplicate logical actions"):
        validate_execution_recovery_action_set_v1(duplicate)

    self_referential = deepcopy(action_set)
    self_referential["phase"] = "FENCING"
    self_referential["actions"][0].update({
        "action_kind": "ADVANCE_ATTEMPT", "entity_kind": "ATTEMPT", "entity_id": "AT-ONE",
        "target_event_type": "attempt.stop_latched",
        "parameters": {"attempt_id": "AT-ONE", "from_state": "RUNNING", "transition_cause": {
            "code": "RECOVERY_FENCE", "trigger_kind": "RECOVERY_DERIVATION",
            "trigger_event_id": "JE-FOUR", "effective_sequence": 4, "evidence_sigil": SIGIL,
        }},
    })
    self_referential_second = deepcopy(self_referential["actions"][0])
    self_referential_second.update({"ordinal": 1, "target_event_id": "JE-FIVE", "target_sequence": 5})
    self_referential_second["parameters"]["transition_cause"].update({
        "trigger_event_id": "JE-FIVE", "effective_sequence": 5,
    })
    self_referential["actions"].append(self_referential_second)
    self_referential["action_set_sigil"] = content_sigil(
        {key: member for key, member in self_referential.items() if key != "action_set_sigil"}
    )
    with pytest.raises(Exception, match="duplicate logical actions"):
        validate_execution_recovery_action_set_v1(self_referential)


def test_active_recovery_projection_matches_one_supplied_action_set() -> None:
    action_set = _recovery_action_set()
    state = json.loads((FIXTURES / "execution-state-v1" / "valid-initial.json").read_text())
    state["recoveries"] = [{
        "recovery_id": action_set["recovery_id"], "revision": 0, "state": "STARTED",
        "prior_recovery_id": None, "started_event_sigil": SIGIL,
        "current_action_set_sigil": action_set["action_set_sigil"],
        "last_event_id": "JE-ONE", "last_event_sigil": SIGIL,
    }]
    state["executor"]["active_recovery_id"] = action_set["recovery_id"]
    state["executor"]["authority_gates"] = ["RECOVERY_ACTIVE"]
    _reseal_state(state)
    validate_execution_state_supplied_recovery_action_set_v1(state, action_set)

    wrong_set = deepcopy(action_set)
    wrong_set["recovery_id"] = "RY-TWO"
    wrong_set["action_set_sigil"] = content_sigil({
        key: member for key, member in wrong_set.items() if key != "action_set_sigil"
    })
    with pytest.raises(Exception, match="disagrees with supplied"):
        validate_execution_state_supplied_recovery_action_set_v1(state, wrong_set)


def test_recovery_action_set_anchors_to_its_supplied_prefix() -> None:
    initial = json.loads(
        (FIXTURES / "execution-journal-event-v1" / "valid-initial.json").read_text()
    )
    clock_uncertain = _clock_uncertain_event(initial)
    action_set = _recovery_action_set()
    action_set["derived_through_event_sigil"] = clock_uncertain["event_sigil"]
    action_set["action_set_sigil"] = content_sigil({
        key: member for key, member in action_set.items() if key != "action_set_sigil"
    })
    validate_execution_recovery_action_set_supplied_prefix_v1(
        action_set, [initial, clock_uncertain],
    )

    stale_anchor = deepcopy(action_set)
    stale_anchor["derived_through_sequence"] = 1
    stale_anchor["actions"][0]["target_sequence"] = 3
    stale_anchor["action_set_sigil"] = content_sigil({
        key: member for key, member in stale_anchor.items() if key != "action_set_sigil"
    })
    with pytest.raises(Exception, match="disagrees with supplied prefix"):
        validate_execution_recovery_action_set_supplied_prefix_v1(
            stale_anchor, [initial, clock_uncertain],
        )

    broken_prefix = deepcopy(clock_uncertain)
    broken_prefix["previous_event_sigil"] = None
    broken_prefix["event_sigil"] = content_sigil({
        key: member for key, member in broken_prefix.items() if key != "event_sigil"
    })
    with pytest.raises(Exception, match="previous_event_sigil"):
        validate_execution_recovery_action_set_supplied_prefix_v1(
            action_set, [initial, broken_prefix],
        )

    later = _event_unsigned()
    later.update({
        "event_id": "JE-FOUR", "sequence": 4, "event_type": "log.chunk_committed",
        "executor_instance_id": initial["executor_instance_id"],
        "executor_epoch": initial["executor_epoch"],
        "executor_build_sigil": initial["executor_build_sigil"],
        "recorded_at": "2026-08-06T00:00:03Z",
        "previous_event_sigil": _recovery_started_event(clock_uncertain)["event_sigil"],
    })
    later["event_sigil"] = content_sigil({
        key: member for key, member in later.items() if key != "event_sigil"
    })
    recovery_started = _recovery_started_event(clock_uncertain)
    later["previous_event_sigil"] = recovery_started["event_sigil"]
    later["event_sigil"] = content_sigil({
        key: member for key, member in later.items() if key != "event_sigil"
    })
    later_action_set = deepcopy(action_set)
    later_action_set["derived_through_sequence"] = 4
    later_action_set["derived_through_event_sigil"] = later["event_sigil"]
    later_action_set["actions"][0]["target_sequence"] = 6
    later_action_set["action_set_sigil"] = content_sigil({
        key: member for key, member in later_action_set.items() if key != "action_set_sigil"
    })
    validate_execution_journal_prefix_wire_v1([initial, clock_uncertain, recovery_started, later])
    validate_execution_recovery_action_set_supplied_prefix_v1(
        later_action_set, [initial, clock_uncertain, recovery_started, later],
    )
    with pytest.raises(Exception, match="reducer is unavailable"):
        replay_execution_journal_prefix_v1([initial, clock_uncertain, recovery_started, later])


def test_recovery_start_binds_its_started_action_set_and_prefix() -> None:
    initial = json.loads(
        (FIXTURES / "execution-journal-event-v1" / "valid-initial.json").read_text()
    )
    clock_uncertain = _clock_uncertain_event(initial)
    action_set = _recovery_action_set()
    action_set["derived_through_event_sigil"] = clock_uncertain["event_sigil"]
    action_set["action_set_sigil"] = content_sigil({
        key: member for key, member in action_set.items() if key != "action_set_sigil"
    })
    recovery_started = _recovery_started_event(clock_uncertain)
    recovery_started["payload"]["initial_action_set_sigil"] = action_set["action_set_sigil"]
    recovery_started["event_sigil"] = content_sigil({
        key: member for key, member in recovery_started.items() if key != "event_sigil"
    })
    validate_execution_recovery_start_supplied_action_set_v1(
        recovery_started, action_set, [initial, clock_uncertain],
    )

    wrong_set = deepcopy(action_set)
    wrong_set["supersedes_action_set_sigil"] = SIGIL
    wrong_set["action_set_sigil"] = content_sigil({
        key: member for key, member in wrong_set.items() if key != "action_set_sigil"
    })
    with pytest.raises(Exception, match="start disagrees"):
        validate_execution_recovery_start_supplied_action_set_v1(
            recovery_started, wrong_set, [initial, clock_uncertain],
        )


def test_execution_journal_prefix_rejects_resealed_duplicate_event_identity() -> None:
    initial = json.loads(
        (FIXTURES / "execution-journal-event-v1" / "valid-initial.json").read_text()
    )
    clock_uncertain = _clock_uncertain_event(initial)
    clock_uncertain["event_id"] = initial["event_id"]
    clock_uncertain["event_sigil"] = content_sigil({
        key: member for key, member in clock_uncertain.items() if key != "event_sigil"
    })
    with pytest.raises(Exception, match="duplicate Event identity"):
        validate_execution_journal_prefix_wire_v1([initial, clock_uncertain])


def test_recovery_phase_advance_binds_state_and_sealed_action_sets() -> None:
    initial = json.loads(
        (FIXTURES / "execution-journal-event-v1" / "valid-initial.json").read_text()
    )
    clock_uncertain = _clock_uncertain_event(initial)
    recovery_started = _recovery_started_event(clock_uncertain)
    completed_set = _recovery_action_set()
    completed_set["derived_through_event_sigil"] = clock_uncertain["event_sigil"]
    completed_set["action_set_sigil"] = content_sigil({
        key: member for key, member in completed_set.items() if key != "action_set_sigil"
    })
    next_set = deepcopy(completed_set)
    next_set.update({
        "phase": "FENCING", "derived_through_sequence": 3,
        "derived_through_event_sigil": recovery_started["event_sigil"], "actions": [],
    })
    next_set["action_set_sigil"] = content_sigil({
        key: member for key, member in next_set.items() if key != "action_set_sigil"
    })
    state = json.loads((FIXTURES / "execution-state-v1" / "valid-initial.json").read_text())
    state["journal_binding"] = {
        "journal_id": recovery_started["journal_id"], "through_sequence": 3,
        "through_event_id": recovery_started["event_id"],
        "through_event_sigil": recovery_started["event_sigil"],
    }
    state["executor"].update({
        "revision": 2, "clock_state": "UNCERTAIN", "clock_uncertain_event_id": "JE-TWO",
        "active_recovery_id": "RY-ONE", "authority_gates": ["CLOCK_UNCERTAIN", "RECOVERY_ACTIVE"],
        "last_event_id": recovery_started["event_id"], "last_event_sigil": recovery_started["event_sigil"],
    })
    state["recoveries"] = [{
        "recovery_id": "RY-ONE", "revision": 0, "state": "STARTED",
        "prior_recovery_id": None, "started_event_sigil": recovery_started["event_sigil"],
        "current_action_set_sigil": completed_set["action_set_sigil"],
        "last_event_id": recovery_started["event_id"], "last_event_sigil": recovery_started["event_sigil"],
    }]
    _reseal_state(state)
    event = {
        "schema_version": "execution-journal-event/1.0", "journal_id": "EJ-ONE",
        "event_id": "JE-FOUR", "sequence": 4, "event_type": "recovery.phase_advanced",
        "executor_instance_id": initial["executor_instance_id"], "executor_epoch": initial["executor_epoch"],
        "executor_build_sigil": initial["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:03Z",
        "observed_at": None,
        "entity_revisions": [{"entity_kind": "RECOVERY", "entity_id": "RY-ONE",
                              "preceding_revision": 0, "next_revision": 1}],
        "causation_event_id": None, "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {"recovery_id": "RY-ONE", "from_phase": "STARTED", "to_phase": "FENCING",
                    "completed_action_set_sigil": completed_set["action_set_sigil"],
                    "next_action_set_sigil": next_set["action_set_sigil"],
                    "completed_entity_ids": [], "quarantined_entity_ids": []},
        "previous_event_sigil": recovery_started["event_sigil"],
    }
    event["event_sigil"] = content_sigil({key: member for key, member in event.items() if key != "event_sigil"})
    validate_execution_recovery_phase_advance_supplied_action_sets_v1(
        state, event, completed_set, next_set,
    )

    wrong_next = deepcopy(next_set)
    wrong_next["recovery_id"] = "RY-TWO"
    wrong_next["action_set_sigil"] = content_sigil({
        key: member for key, member in wrong_next.items() if key != "action_set_sigil"
    })
    with pytest.raises(Exception, match="phase advance disagrees"):
        validate_execution_recovery_phase_advance_supplied_action_sets_v1(
            state, event, completed_set, wrong_next,
        )


def test_empty_recovery_phase_replay_projects_each_control_phase() -> None:
    initial = json.loads(
        (FIXTURES / "execution-journal-event-v1" / "valid-initial.json").read_text()
    )
    clock_uncertain = _clock_uncertain_event(initial)
    started_set = _empty_recovery_action_set("STARTED", [initial, clock_uncertain])
    recovery_started = _recovery_started_event(clock_uncertain)
    recovery_started["payload"]["initial_action_set_sigil"] = started_set["action_set_sigil"]
    recovery_started["event_sigil"] = content_sigil({
        key: member for key, member in recovery_started.items() if key != "event_sigil"
    })
    fencing_set = _empty_recovery_action_set("FENCING", [initial, clock_uncertain, recovery_started])
    fencing = _recovery_phase_event(recovery_started, started_set, fencing_set, "JE-FOUR")
    reconciling_set = _empty_recovery_action_set(
        "RECONCILING", [initial, clock_uncertain, recovery_started, fencing],
    )
    reconciling = _recovery_phase_event(fencing, fencing_set, reconciling_set, "JE-FIVE")
    finalizing_set = _empty_recovery_action_set(
        "FINALIZING", [initial, clock_uncertain, recovery_started, fencing, reconciling],
    )
    finalizing = _recovery_phase_event(reconciling, reconciling_set, finalizing_set, "JE-SIX")

    state = replay_execution_empty_recovery_phase_prefix_v1(
        [initial, clock_uncertain, recovery_started, fencing, reconciling, finalizing],
        [started_set, fencing_set, reconciling_set, finalizing_set],
    )

    assert state["journal_binding"]["through_sequence"] == 6
    assert state["recoveries"] == [{
        "recovery_id": "RY-ONE", "revision": 3, "state": "FINALIZING",
        "prior_recovery_id": None, "started_event_sigil": recovery_started["event_sigil"],
        "current_action_set_sigil": finalizing_set["action_set_sigil"],
        "last_event_id": finalizing["event_id"], "last_event_sigil": finalizing["event_sigil"],
    }]
    assert state["executor"]["authority_gates"] == ["CLOCK_UNCERTAIN", "RECOVERY_ACTIVE"]

    malformed = deepcopy(fencing_set)
    malformed["actions"] = _recovery_action_set()["actions"]
    malformed["action_set_sigil"] = content_sigil({
        key: member for key, member in malformed.items() if key != "action_set_sigil"
    })
    with pytest.raises(Exception, match="action kind is not allowed|initial empty action sets"):
        replay_execution_empty_recovery_phase_prefix_v1(
            [initial, clock_uncertain, recovery_started, fencing, reconciling, finalizing],
            [started_set, malformed, reconciling_set, finalizing_set],
        )


def test_recovery_rebase_binds_state_and_sealed_action_sets() -> None:
    prior_set = _recovery_action_set()
    state = json.loads((FIXTURES / "execution-state-v1" / "valid-initial.json").read_text())
    state["journal_binding"] = {
        "journal_id": "EJ-ONE", "through_sequence": 3, "through_event_id": "JE-THREE",
        "through_event_sigil": SIGIL_B,
    }
    state["executor"].update({
        "revision": 2, "clock_state": "UNCERTAIN", "clock_uncertain_event_id": "JE-TWO",
        "active_recovery_id": "RY-ONE", "authority_gates": ["CLOCK_UNCERTAIN", "RECOVERY_ACTIVE"],
        "last_event_id": "JE-THREE", "last_event_sigil": SIGIL_B,
    })
    state["recoveries"] = [{
        "recovery_id": "RY-ONE", "revision": 0, "state": "STARTED",
        "prior_recovery_id": None, "started_event_sigil": SIGIL,
        "current_action_set_sigil": prior_set["action_set_sigil"],
        "last_event_id": "JE-THREE", "last_event_sigil": SIGIL_B,
    }]
    _reseal_state(state)
    replacement_set = deepcopy(prior_set)
    replacement_set["supersedes_action_set_sigil"] = prior_set["action_set_sigil"]
    replacement_set["action_set_sigil"] = content_sigil({
        key: member for key, member in replacement_set.items() if key != "action_set_sigil"
    })
    event = {
        "schema_version": "execution-journal-event/1.0", "journal_id": "EJ-ONE",
        "event_id": "JE-FOUR", "sequence": 4, "event_type": "recovery.action_set_rebased",
        "executor_instance_id": "XI-ONE", "executor_epoch": 1, "executor_build_sigil": SIGIL,
        "recorded_at": "2026-08-06T00:00:03Z", "observed_at": None,
        "entity_revisions": [{"entity_kind": "RECOVERY", "entity_id": "RY-ONE",
                              "preceding_revision": 0, "next_revision": 1}],
        "causation_event_id": None, "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {"recovery_id": "RY-ONE", "phase": "STARTED",
                    "prior_action_set_sigil": prior_set["action_set_sigil"],
                    "replacement_action_set_sigil": replacement_set["action_set_sigil"],
                    "reason_event_id": "JE-TWO", "new_epoch": 1,
                    "carried_completion_event_ids": []},
        "previous_event_sigil": SIGIL_B,
    }
    event["event_sigil"] = content_sigil({key: member for key, member in event.items() if key != "event_sigil"})
    validate_execution_recovery_rebase_supplied_action_sets_v1(
        state, event, prior_set, replacement_set,
    )

    wrong_replacement = deepcopy(replacement_set)
    wrong_replacement["supersedes_action_set_sigil"] = SIGIL
    wrong_replacement["action_set_sigil"] = content_sigil({
        key: member for key, member in wrong_replacement.items() if key != "action_set_sigil"
    })
    with pytest.raises(Exception, match="rebase disagrees"):
        validate_execution_recovery_rebase_supplied_action_sets_v1(
            state, event, prior_set, wrong_replacement,
        )


def test_recovery_completion_binds_finalizing_state_and_action_set() -> None:
    action_set = _recovery_action_set()
    action_set.update({"phase": "FINALIZING", "actions": []})
    action_set["action_set_sigil"] = content_sigil({
        key: member for key, member in action_set.items() if key != "action_set_sigil"
    })
    state = json.loads((FIXTURES / "execution-state-v1" / "valid-initial.json").read_text())
    state["journal_binding"] = {"journal_id": "EJ-ONE", "through_sequence": 3,
                                "through_event_id": "JE-THREE", "through_event_sigil": SIGIL_B}
    state["executor"].update({"revision": 2, "clock_state": "UNCERTAIN",
        "clock_uncertain_event_id": "JE-TWO", "active_recovery_id": "RY-ONE",
        "authority_gates": ["CLOCK_UNCERTAIN", "RECOVERY_ACTIVE"],
        "last_event_id": "JE-THREE", "last_event_sigil": SIGIL_B})
    state["recoveries"] = [{"recovery_id": "RY-ONE", "revision": 3, "state": "FINALIZING",
        "prior_recovery_id": None, "started_event_sigil": SIGIL,
        "current_action_set_sigil": action_set["action_set_sigil"],
        "last_event_id": "JE-THREE", "last_event_sigil": SIGIL_B}]
    _reseal_state(state)
    event = {"schema_version": "execution-journal-event/1.0", "journal_id": "EJ-ONE",
        "event_id": "JE-FOUR", "sequence": 4, "event_type": "recovery.completed",
        "executor_instance_id": "XI-ONE", "executor_epoch": 1, "executor_build_sigil": SIGIL,
        "recorded_at": "2026-08-06T00:00:03Z", "observed_at": None,
        "entity_revisions": [
            {"entity_kind": "EXECUTOR", "entity_id": "XI-ONE", "preceding_revision": 2, "next_revision": 3},
            {"entity_kind": "RECOVERY", "entity_id": "RY-ONE", "preceding_revision": 3, "next_revision": 4},
        ], "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None,
        "payload": {"recovery_id": "RY-ONE", "completed_action_set_sigil": action_set["action_set_sigil"],
                    "recovered_state_sigil": SIGIL, "fence_tombstone_event_ids": [],
                    "quarantined_entity_ids": [], "resumable_job_ids": []},
        "previous_event_sigil": SIGIL_B}
    event["event_sigil"] = content_sigil({key: member for key, member in event.items() if key != "event_sigil"})
    validate_execution_recovery_completion_supplied_action_set_v1(state, event, action_set)

    wrong_set = deepcopy(action_set)
    wrong_set["phase"] = "RECONCILING"
    wrong_set["action_set_sigil"] = content_sigil({
        key: member for key, member in wrong_set.items() if key != "action_set_sigil"
    })
    with pytest.raises(Exception, match="completion disagrees"):
        validate_execution_recovery_completion_supplied_action_set_v1(state, event, wrong_set)


def test_recovery_action_event_matches_its_supplied_frozen_envelope() -> None:
    action_set = _recovery_action_set()
    event = _recovery_action_event(action_set)
    validate_execution_recovery_action_supplied_event_v1(action_set, event)

    multi_owner = deepcopy(event)
    multi_owner["entity_revisions"] = [
        {"entity_kind": "EXECUTOR", "entity_id": "XI-ONE", "preceding_revision": 1,
         "next_revision": 2},
        *event["entity_revisions"],
    ]
    multi_owner["event_sigil"] = content_sigil({
        key: member for key, member in multi_owner.items() if key != "event_sigil"
    })
    validate_execution_recovery_action_supplied_event_v1(action_set, multi_owner)

    wrong_envelope = deepcopy(event)
    wrong_envelope["event_id"] = "JE-WRONG"
    wrong_envelope["event_sigil"] = content_sigil({
        key: member for key, member in wrong_envelope.items() if key != "event_sigil"
    })
    with pytest.raises(Exception, match="envelope disagrees"):
        validate_execution_recovery_action_supplied_event_v1(action_set, wrong_envelope)


def test_state_locally_binds_session_and_lease_heartbeat_projections() -> None:
    state = _state_with_session_and_lease()
    assert load_execution_state_v1(json.dumps(state)) == state

    bad_session = deepcopy(state)
    bad_session["worker_sessions"][0]["last_heartbeat_message_sigil"] = None
    _reseal_state(bad_session)
    with pytest.raises(Exception, match="Worker-Session heartbeat fields"):
        load_execution_state_v1(json.dumps(bad_session))

    bad_session_due = deepcopy(state)
    bad_session_due["worker_sessions"][0]["state"] = "OFFLINE"
    _reseal_state(bad_session_due)
    with pytest.raises(Exception, match="Worker-Session terminal or unready"):
        load_execution_state_v1(json.dumps(bad_session_due))

    missing_capacity = deepcopy(state)
    missing_capacity["worker_sessions"][0].update({
        "capacity": None, "capacity_in_use": 0,
        "worker_session_heartbeat_policy_id": None,
        "worker_session_heartbeat_policy_sigil": None,
    })
    _reseal_state(missing_capacity)
    with pytest.raises(Exception, match="capacity nullability"):
        load_execution_state_v1(json.dumps(missing_capacity))

    bad_lease = deepcopy(state)
    bad_lease["leases"][0]["last_resource_sample_sigil"] = None
    _reseal_state(bad_lease)
    with pytest.raises(Exception, match="Lease heartbeat fields"):
        load_execution_state_v1(json.dumps(bad_lease))

    bad_lease_due = deepcopy(state)
    bad_lease_due["leases"][0]["next_heartbeat_due_at"] = None
    _reseal_state(bad_lease_due)
    with pytest.raises(Exception, match="Lease heartbeat due time"):
        load_execution_state_v1(json.dumps(bad_lease_due))

    bad_tombstone = deepcopy(state)
    bad_tombstone["leases"][0]["tombstone_generation"] = 0
    bad_tombstone["leases"][0]["tombstone_event_sigil"] = SIGIL
    _reseal_state(bad_tombstone)
    with pytest.raises(Exception, match="Lease tombstone fields"):
        load_execution_state_v1(json.dumps(bad_tombstone))

    terminal_lease = deepcopy(state)
    terminal_lease["leases"][0].update({
        "state": "RELEASED", "next_heartbeat_due_at": None,
        "tombstone_generation": 0, "tombstone_event_sigil": SIGIL,
        "terminal_event_binding": {
            "kind": "PRESENT", "terminal_state": "RELEASED", "terminal_event_id": "JE-TWO",
            "terminal_event_sigil": SIGIL, "terminal_sequence": 2, "terminal_recorded_at": STAMP,
        },
    })
    _reseal_state(terminal_lease)
    assert load_execution_state_v1(json.dumps(terminal_lease)) == terminal_lease

    missing_worker = deepcopy(state)
    missing_worker["workers"] = []
    _reseal_state(missing_worker)
    with pytest.raises(Exception, match="no matching Worker"):
        load_execution_state_v1(json.dumps(missing_worker))

    missing_session = deepcopy(state)
    missing_session["worker_sessions"] = []
    _reseal_state(missing_session)
    with pytest.raises(Exception, match="no matching Worker-Session"):
        load_execution_state_v1(json.dumps(missing_session))

    mismatched_lease_worker = deepcopy(state)
    mismatched_lease_worker["leases"][0]["worker_id"] = "WK-TWO"
    _reseal_state(mismatched_lease_worker)
    with pytest.raises(Exception, match="Lease Worker does not match"):
        load_execution_state_v1(json.dumps(mismatched_lease_worker))

    mismatched_worker_binding = deepcopy(state)
    mismatched_worker_binding["worker_sessions"][0]["worker_binding_sigil"] = SIGIL_B
    _reseal_state(mismatched_worker_binding)
    with pytest.raises(Exception, match="binding Sigil does not match"):
        load_execution_state_v1(json.dumps(mismatched_worker_binding))

    excess_lease_expiry = deepcopy(state)
    excess_lease_expiry["leases"][0]["expiry_due_at"] = "2026-08-06T00:00:01Z"
    _reseal_state(excess_lease_expiry)
    with pytest.raises(Exception, match="exceeds its maximum expiry"):
        load_execution_state_v1(json.dumps(excess_lease_expiry))


def test_state_locally_binds_log_stream_closure_projections() -> None:
    state = _state_with_session_and_lease()
    log_stream = {
        "log_stream_id": "LG-ONE", "revision": 0, "state": "OPEN", "attempt_id": "AT-ONE",
        "stream": "STDOUT", "next_sequence": 0, "captured_bytes": 0, "dropped_bytes": 0,
        "truncated": False, "final_sequence": None, "stream_set_sigil": None,
        "last_event_id": "JE-ONE", "last_event_sigil": SIGIL,
    }
    state["log_streams"] = [log_stream]
    _reseal_state(state)
    assert load_execution_state_v1(json.dumps(state)) == state

    open_with_terminal_fields = deepcopy(state)
    open_with_terminal_fields["log_streams"][0]["stream_set_sigil"] = SIGIL
    _reseal_state(open_with_terminal_fields)
    with pytest.raises(Exception, match="Open Log stream"):
        load_execution_state_v1(json.dumps(open_with_terminal_fields))

    closed_without_sigil = deepcopy(state)
    closed_without_sigil["log_streams"][0]["state"] = "CLOSED"
    _reseal_state(closed_without_sigil)
    with pytest.raises(Exception, match="Closed Log stream must have"):
        load_execution_state_v1(json.dumps(closed_without_sigil))

    closed_empty = deepcopy(state)
    closed_empty["log_streams"][0].update({"state": "CLOSED", "stream_set_sigil": SIGIL})
    _reseal_state(closed_empty)
    assert load_execution_state_v1(json.dumps(closed_empty)) == closed_empty

    closed_past_next = deepcopy(closed_empty)
    closed_past_next["log_streams"][0]["final_sequence"] = 0
    _reseal_state(closed_past_next)
    with pytest.raises(Exception, match="final sequence must precede"):
        load_execution_state_v1(json.dumps(closed_past_next))


def test_state_locally_binds_deadline_priority_and_order() -> None:
    state = _state_with_session_and_lease()
    state["deadlines"] = [
        {"deadline_kind": "JOB_DEADLINE", "due_at": STAMP, "fixed_priority": 10,
         "entity_id": JOB_ID, "source_event_id": "JE-ONE", "source_event_sigil": SIGIL},
        {"deadline_kind": "LEASE_EXPIRY", "due_at": STAMP, "fixed_priority": 40,
         "entity_id": LEASE_ID, "source_event_id": "JE-ONE", "source_event_sigil": SIGIL},
    ]
    _reseal_state(state)
    assert load_execution_state_v1(json.dumps(state)) == state

    wrong_priority = deepcopy(state)
    wrong_priority["deadlines"][0]["fixed_priority"] = 20
    _reseal_state(wrong_priority)
    with pytest.raises(Exception, match="fixed priority"):
        load_execution_state_v1(json.dumps(wrong_priority))

    wrong_order = deepcopy(state)
    wrong_order["deadlines"].reverse()
    _reseal_state(wrong_order)
    with pytest.raises(Exception, match="canonical deadline key"):
        load_execution_state_v1(json.dumps(wrong_order))

    duplicate_key = deepcopy(state)
    duplicate_key["deadlines"].append(deepcopy(duplicate_key["deadlines"][1]))
    _reseal_state(duplicate_key)
    with pytest.raises(Exception, match="duplicate Deadline"):
        load_execution_state_v1(json.dumps(duplicate_key))


def test_isr3_initial_event_state_head_triplet_is_closed_and_cross_bound() -> None:
    event = json.loads(
        (FIXTURES / "execution-journal-event-v1" / "valid-initial.json").read_text()
    )
    state = json.loads(
        (FIXTURES / "execution-state-v1" / "valid-initial.json").read_text()
    )
    head = json.loads(
        (FIXTURES / "execution-journal-head-v1" / "valid-initial.json").read_text()
    )
    assert load_execution_journal_event_v1(json.dumps(event)) == event
    assert load_execution_state_v1(json.dumps(state)) == state
    validate_execution_journal_head_v1(head)
    assert load_execution_journal_head_v1(json.dumps(head)) == head
    validate_execution_initial_state_supplied_facts_v1(event, state, head)
    assert replay_execution_initial_prefix_v1([event], head=head) == state
    assert replay_execution_journal_prefix_v1([event], head=head) == state
    with pytest.raises(Exception, match="nonempty prefix"):
        replay_execution_journal_prefix_v1([])
    with pytest.raises(Exception, match="nonobject Event"):
        replay_execution_journal_prefix_v1([event, None])  # type: ignore[list-item]

    wrong_first_kind = deepcopy(event)
    wrong_first_kind["event_type"] = "executor.clock_uncertain"
    wrong_first_kind["event_sigil"] = content_sigil(
        {key: member for key, member in wrong_first_kind.items() if key != "event_sigil"}
    )
    with pytest.raises(Exception, match="must begin with executor epoch start"):
        replay_execution_journal_prefix_v1([wrong_first_kind])
    with pytest.raises(Exception, match="only the initial one-Event prefix"):
        replay_execution_initial_prefix_v1([event, event])
    with pytest.raises(Exception, match="duplicate Event identity|sequence gap"):
        replay_execution_journal_prefix_v1([event, event])

    wrong_head = deepcopy(head)
    wrong_head["last_event_id"] = "JE-TWO"
    wrong_head["head_sigil"] = content_sigil(
        {key: member for key, member in wrong_head.items() if key != "head_sigil"}
    )
    with pytest.raises(Exception, match="Head disagrees"):
        replay_execution_journal_prefix_v1([event], head=wrong_head)

    wrong_initial_event = deepcopy(event)
    wrong_initial_event["event_type"] = "executor.clock_uncertain"
    wrong_initial_event["event_sigil"] = content_sigil(
        {key: member for key, member in wrong_initial_event.items() if key != "event_sigil"}
    )
    with pytest.raises(Exception, match="execution-journal-event"):
        replay_execution_initial_prefix_v1([wrong_initial_event])

    clock_uncertain = _clock_uncertain_event(event)
    reduced = replay_execution_journal_prefix_v1([event, clock_uncertain])
    assert reduced["executor"]["clock_state"] == "UNCERTAIN"
    assert reduced["executor"]["authority_gates"] == ["CLOCK_UNCERTAIN"]
    assert reduced["executor"]["clock_uncertain_event_id"] == "JE-TWO"
    assert reduced["journal_binding"]["through_event_sigil"] == clock_uncertain["event_sigil"]

    recovery_started = _recovery_started_event(clock_uncertain)
    recovered = replay_execution_journal_prefix_v1([event, clock_uncertain, recovery_started])
    assert recovered["executor"]["active_recovery_id"] == "RY-ONE"
    assert recovered["executor"]["authority_gates"] == ["CLOCK_UNCERTAIN", "RECOVERY_ACTIVE"]
    assert recovered["recoveries"] == [{
        "recovery_id": "RY-ONE", "revision": 0, "state": "STARTED",
        "prior_recovery_id": None, "started_event_sigil": recovery_started["event_sigil"],
        "current_action_set_sigil": SIGIL, "last_event_id": "JE-THREE",
        "last_event_sigil": recovery_started["event_sigil"],
    }]

    mismatched_prefix = deepcopy(recovery_started)
    mismatched_prefix["payload"]["replay_through_sequence"] = 1
    mismatched_prefix["event_sigil"] = content_sigil({
        key: member for key, member in mismatched_prefix.items() if key != "event_sigil"
    })
    with pytest.raises(Exception, match="payload disagrees"):
        replay_execution_journal_prefix_v1([event, clock_uncertain, mismatched_prefix])

    changed_anchor = deepcopy(clock_uncertain)
    changed_anchor["payload"]["last_trusted_utc"] = "2026-08-06T00:00:01Z"
    changed_anchor["event_sigil"] = content_sigil(
        {key: member for key, member in changed_anchor.items() if key != "event_sigil"}
    )
    with pytest.raises(Exception, match="trusted-time anchor"):
        replay_execution_journal_prefix_v1([event, changed_anchor])

    decreasing_time = deepcopy(clock_uncertain)
    decreasing_time["recorded_at"] = "2026-08-05T23:59:59Z"
    decreasing_time["event_sigil"] = content_sigil(
        {key: member for key, member in decreasing_time.items() if key != "event_sigil"}
    )
    with pytest.raises(Exception, match="decreasing recorded_at"):
        replay_execution_journal_prefix_v1([event, decreasing_time])

    conflicting_build = deepcopy(clock_uncertain)
    conflicting_build["executor_build_sigil"] = SIGIL
    conflicting_build["event_sigil"] = content_sigil(
        {key: member for key, member in conflicting_build.items() if key != "event_sigil"}
    )
    with pytest.raises(Exception, match="conflicting Executor build"):
        replay_execution_journal_prefix_v1([event, conflicting_build])
    assert head["head_sigil"] == content_sigil(
        {key: member for key, member in head.items() if key != "head_sigil"}
    )
    for record in (state["journal_binding"], head):
        assert record["journal_id"] == event["journal_id"]
        assert record["through_sequence" if record is state["journal_binding"] else "last_sequence"] == event["sequence"]
        assert record["through_event_id" if record is state["journal_binding"] else "last_event_id"] == event["event_id"]
        assert record["through_event_sigil" if record is state["journal_binding"] else "last_event_sigil"] == event["event_sigil"]
    assert state["executor"]["executor_build_binding"] == event["payload"]["executor_build_binding"]
    assert state["executor"]["last_event_sigil"] == event["event_sigil"]
    for member in (
        "recoveries", "workers", "worker_sessions", "jobs", "attempts",
        "leases", "log_streams", "deadlines", "idempotency_records",
    ):
        assert state[member] == []

    tampered = deepcopy(state)
    tampered["executor"]["executor_build_binding"]["implementation_version"] = "V2"
    tampered["state_sigil"] = content_sigil(
        {key: member for key, member in tampered.items() if key != "state_sigil"}
    )
    with pytest.raises(Exception, match="executor build self-Sigil"):
        load_execution_state_v1(json.dumps(tampered))

    wrong_gate = deepcopy(state)
    wrong_gate["executor"]["authority_gates"] = ["CLOCK_UNCERTAIN"]
    wrong_gate["state_sigil"] = content_sigil(
        {key: member for key, member in wrong_gate.items() if key != "state_sigil"}
    )
    with pytest.raises(Exception, match="clock uncertainty gate"):
        load_execution_state_v1(json.dumps(wrong_gate))

    wrong_order = deepcopy(state)
    wrong_order["executor"]["authority_gates"] = ["RECOVERY_ACTIVE", "INTEGRITY_FAILURE"]
    wrong_order["state_sigil"] = content_sigil(
        {key: member for key, member in wrong_order.items() if key != "state_sigil"}
    )
    with pytest.raises(Exception, match="canonical order"):
        load_execution_state_v1(json.dumps(wrong_order))

    recovery = deepcopy(state)
    recovery_id = "RY-" + "A" * 64
    recovery["recoveries"] = [{
        "recovery_id": recovery_id, "revision": 0, "state": "STARTED",
        "prior_recovery_id": None, "started_event_sigil": SIGIL,
        "current_action_set_sigil": None, "last_event_id": "JE-ONE", "last_event_sigil": SIGIL,
    }]
    recovery["executor"]["active_recovery_id"] = recovery_id
    recovery["executor"]["authority_gates"] = ["RECOVERY_ACTIVE"]
    _reseal_state(recovery)
    assert load_execution_state_v1(json.dumps(recovery)) == recovery

    missing_recovery = deepcopy(recovery)
    missing_recovery["recoveries"] = []
    _reseal_state(missing_recovery)
    with pytest.raises(Exception, match="active Recovery does not match"):
        load_execution_state_v1(json.dumps(missing_recovery))

    unprojected_recovery = deepcopy(recovery)
    unprojected_recovery["executor"]["active_recovery_id"] = None
    unprojected_recovery["executor"]["authority_gates"] = []
    _reseal_state(unprojected_recovery)
    with pytest.raises(Exception, match="active Recovery is missing"):
        load_execution_state_v1(json.dumps(unprojected_recovery))

    invalid_first_recovery = deepcopy(recovery)
    invalid_first_recovery["recoveries"][0]["prior_recovery_id"] = "RY-" + "B" * 64
    _reseal_state(invalid_first_recovery)
    with pytest.raises(Exception, match="first Recovery projection"):
        load_execution_state_v1(json.dumps(invalid_first_recovery))

    invalid_later_recovery = deepcopy(recovery)
    invalid_later_recovery["recoveries"].append({
        "recovery_id": "RY-" + "B" * 64, "revision": 0, "state": "COMPLETED",
        "prior_recovery_id": None, "started_event_sigil": SIGIL,
        "current_action_set_sigil": None, "last_event_id": "JE-TWO", "last_event_sigil": SIGIL,
    })
    _reseal_state(invalid_later_recovery)
    with pytest.raises(Exception, match="non-first Recovery projection"):
        load_execution_state_v1(json.dumps(invalid_later_recovery))

    changed_executor = deepcopy(state)
    changed_executor["executor"]["revision"] = 1
    changed_executor["state_sigil"] = content_sigil(
        {key: member for key, member in changed_executor.items() if key != "state_sigil"}
    )
    with pytest.raises(Exception, match="executor projection"):
        validate_execution_initial_state_supplied_facts_v1(event, changed_executor, head)

    changed_head = deepcopy(head)
    changed_head["updated_at"] = "2026-08-06T00:00:01Z"
    changed_head["head_sigil"] = content_sigil(
        {key: member for key, member in changed_head.items() if key != "head_sigil"}
    )
    validate_execution_initial_state_supplied_facts_v1(event, state, changed_head)

    invalid_head = deepcopy(head)
    invalid_head["last_sequence"] = 2
    with pytest.raises(Exception, match="Head self-Sigil"):
        load_execution_journal_head_v1(json.dumps(invalid_head))
    with pytest.raises(Exception, match="duplicate JSON key"):
        load_execution_journal_head_v1(
            b'{"schema_version":"execution-journal-head/1.0","schema_version":"x"}'
        )


def test_rfc0015_request_loaders_are_strict_and_cursor_bound_to_fixed_prefix() -> None:
    cursor: dict[str, Any] = {
        "job_id": JOB_ID,
        "last_returned_sequence": 2,
        "through_journal_sequence": 3,
        "through_event_sigil": SIGIL,
    }
    cursor["cursor_sigil"] = derive_execution_observation_cursor_sigil_v1(cursor)
    observe: dict[str, Any] = {
        "schema_version": "execution-observe-request/1.0",
        "job_id": JOB_ID,
        "limit": 2,
        "cursor": cursor,
    }
    validate_execution_request_v1("observe", observe)
    assert load_execution_request_v1("observe", json.dumps(observe)) == observe
    for raw in (
        b'\xef\xbb\xbf{}',
        "{}".encode("utf-16"),
        "{}".encode("utf-32"),
        b'{"schema_version":"execution-observe-request/1.0","limit":1,"limit":2}',
    ):
        with pytest.raises(Exception):
            load_execution_request_v1("observe", raw)
    for invalid_limit in (1.0, True):
        noncanonical = {**observe, "limit": invalid_limit}
        with pytest.raises(Exception):
            validate_execution_request_v1("observe", noncanonical)
    wrong_job = deepcopy(observe)
    wrong_job["cursor"]["job_id"] = "JB-" + "B" * 64
    wrong_job["cursor"]["cursor_sigil"] = derive_execution_observation_cursor_sigil_v1(wrong_job["cursor"])
    with pytest.raises(Exception, match="does not match"):
        validate_execution_request_v1("observe", wrong_job)
    bad_range = deepcopy(observe)
    bad_range["cursor"]["last_returned_sequence"] = 4
    bad_range["cursor"]["cursor_sigil"] = derive_execution_observation_cursor_sigil_v1(bad_range["cursor"])
    with pytest.raises(Exception, match="sequence range"):
        validate_execution_request_v1("observe", bad_range)
    with pytest.raises(Exception, match="unknown Execution API"):
        validate_execution_request_v1("dispatch", observe)

    get_result = {"schema_version": "execution-get-result-request/1.0", "job_id": JOB_ID}
    validate_execution_request_v1("get_result", get_result)
    get_result["job_id"] = "JB-" + "Z" * 64
    with pytest.raises(Exception):
        validate_execution_request_v1("get_result", get_result)


def test_rfc0015_cancel_and_accept_requests_close_nested_and_scalar_fields() -> None:
    cancel: dict[str, Any] = {
        "schema_version": "execution-cancel-request/1.0",
        "cancellation_request_id": "cancel-001",
        "idempotency_key": "cancel-key",
        "job_id": JOB_ID,
        "job_binding_sigil": SIGIL,
        "expected_job_revision": 1,
        "reason": "operator-requested",
        "actor": {
            "kind": "USER",
            "actor_id": "user-001",
            "authentication_context_sigil": SIGIL,
            "actor_sigil": SIGIL,
        },
        "host_invocation": {
            "host_identity_sigil": SIGIL,
            "invocation_id": "invoke-001",
            "authentication_context_sigil": SIGIL,
            "invocation_sigil": SIGIL,
        },
        "caller_observed_at": STAMP,
    }
    validate_execution_request_v1("cancel", cancel)
    assert load_execution_request_v1("cancel", json.dumps(cancel)) == cancel
    nested_extra = deepcopy(cancel)
    nested_extra["actor"]["authority"] = "ambient"
    with pytest.raises(Exception):
        validate_execution_request_v1("cancel", nested_extra)
    with pytest.raises(Exception):
        validate_execution_request_v1("cancel", {**cancel, "expected_job_revision": True})

    accept: dict[str, Any] = {
        "schema_version": "execution-accept-result-request/1.0",
        "job_id": JOB_ID,
        "execution_job_outcome_sigil": SIGIL,
        "idempotency_key": "accept-key",
    }
    validate_execution_request_v1("accept_result", accept)
    assert load_execution_request_v1("accept_result", json.dumps(accept)) == accept
    with pytest.raises(Exception):
        validate_execution_request_v1("accept_result", {**accept, "idempotency_key": "\x00"})


def test_state_rejects_split_policy_legacy_shapes_unknowns_and_duplicate_bytes() -> None:
    raw = (FIXTURES / "execution-state-v1" / "invalid-duplicate-key.json").read_text()
    with pytest.raises(Exception, match="duplicate JSON key"):
        load_execution_state_v1(raw)
    with pytest.raises(Exception, match="BOM"):
        load_execution_state_v1(b"\xef\xbb\xbf{}")
    for encoding in ("utf-16", "utf-32"):
        with pytest.raises(Exception, match="non-UTF-8"):
            load_execution_state_v1("{}".encode(encoding))


def test_event_schema_exposes_81_ordered_closed_payload_branches_and_l12_closure() -> None:
    schema = json.loads((SCHEMAS / "execution-journal-event-1.0.json").read_text())
    assert schema["$defs"]["event_type"]["enum"] == list(EXECUTION_EVENT_TYPES_V1)
    assert len(schema["allOf"]) == 81
    for rank, branch in enumerate(schema["allOf"]):
        assert branch["if"]["properties"]["event_type"]["const"] == EXECUTION_EVENT_TYPES_V1[rank]
        payload = branch["then"]["properties"]["payload"]
        candidates = payload.get("oneOf", [payload])
        assert all(candidate["additionalProperties"] is False for candidate in candidates)
    log_members = schema["allOf"][72]["then"]["properties"]["payload"]["required"]
    assert log_members[:4] == ["intake_kind", "intake_id", "intake_record_sigil", "disposition_intent_id"]
    assert "intake_kind" not in schema["allOf"][76]["then"]["properties"]["payload"]["required"]
    assert schema["allOf"][48]["then"]["properties"]["payload"]["required"] == ["transition_cause", "grace_due_at"]


def test_event_round_trip_unknown_duplicate_and_jew_matrix_helpers() -> None:
    context = {
        "ordinary_l12_suffix": True,
        "ordinary_l12_anchor": True,
        "l12_idempotency_key_sigil": SIGIL,
    }
    event = build_execution_journal_event_v1(_event_unsigned(), context=context)
    assert load_execution_journal_event_v1(json.dumps(event), context=context) == event
    extra = deepcopy(event)
    extra["payload"]["intent_sigil"] = SIGIL
    extra["event_sigil"] = content_sigil({key: value for key, value in extra.items() if key != "event_sigil"})
    with pytest.raises(Exception):
        load_execution_journal_event_v1(json.dumps(extra), context=context)
    for preceding, following, expected in ((None, 1, "null then zero"), (1, 3, "exactly one")):
        invalid_revision = _event_unsigned()
        invalid_revision["entity_revisions"][0]["preceding_revision"] = preceding
        invalid_revision["entity_revisions"][0]["next_revision"] = following
        invalid_revision["event_sigil"] = content_sigil(
            {key: value for key, value in invalid_revision.items() if key != "event_sigil"}
        )
        with pytest.raises(Exception, match=expected):
            load_execution_journal_event_v1(json.dumps(invalid_revision), context=context)
    raw = (FIXTURES / "execution-journal-event-v1" / "invalid-duplicate-key.json").read_text()
    with pytest.raises(Exception, match="duplicate JSON key"):
        load_execution_journal_event_v1(raw)
    non_scalar = _event_unsigned()
    non_scalar["payload"]["intake_id"] = "\ud800"
    non_scalar["event_sigil"] = content_sigil(
        {key: value for key, value in non_scalar.items() if key != "event_sigil"}
    )
    with pytest.raises(Exception, match="non-Unicode-scalar"):
        load_execution_journal_event_v1(json.dumps(non_scalar, ensure_ascii=True))

    non_ascii_identity = _event_unsigned()
    non_ascii_identity["entity_revisions"][0]["entity_id"] = "LG-\u00e9"
    non_ascii_identity["event_sigil"] = content_sigil(
        {key: value for key, value in non_ascii_identity.items() if key != "event_sigil"}
    )
    with pytest.raises(Exception, match="unsigned ASCII"):
        load_execution_journal_event_v1(json.dumps(non_ascii_identity), context=context)

    reversed_kinds = _event_unsigned()
    reversed_kinds["entity_revisions"] = [
        {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 0, "next_revision": 1},
        {"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 0, "next_revision": 1},
    ]
    reversed_kinds["event_sigil"] = content_sigil(
        {key: value for key, value in reversed_kinds.items() if key != "event_sigil"}
    )
    with pytest.raises(Exception, match="strictly sorted"):
        load_execution_journal_event_v1(json.dumps(reversed_kinds), context=context)

    output = {
        "event_type": "attempt.output_staging_preallocated",
        "payload": {"job_id": JOB_ID, "attempt_id": "AT-ONE", "output_handle_id": "OUT"},
        "recovery_action_binding": None,
        "event_id": "JE-TWO",
        "sequence": 2,
    }
    assert expected_event_causation_v1(output, {"attempt_running_event_id": "JE-ONE"}) == "JE-ONE"
    assert expected_event_idempotency_v1(output, {}) == content_sigil(
        ["execution-output-staging-preallocation-key/1.0", JOB_ID, "AT-ONE", "OUT"]
    )
    prior = {
        "event_type": "attempt.stop_latched",
        "payload": {"transition_cause": {"trigger_kind": "PRIOR_EVENT", "trigger_event_id": "JE-ONE"}},
        "recovery_action_binding": None,
        "event_id": "JE-TWO",
        "sequence": 2,
    }
    assert expected_event_causation_v1(prior, {}) == "JE-ONE"
    contradictory = deepcopy(prior)
    with pytest.raises(Exception, match="contradictory"):
        expected_event_causation_v1(
            contradictory,
            {"ordinary_l12_suffix": True, "ordinary_l12_anchor": False, "l12_preceding_event_id": "JE-OTHER"},
        )


def test_jew4_owners_are_resolvable_direct_refs_and_validate_complete_roots() -> None:
    event_schema = json.loads((SCHEMAS / "execution-journal-event-1.0.json").read_text())
    result_payload = event_schema["allOf"][45]["then"]["properties"]["payload"]
    assert result_payload["properties"]["observation_evidence_disposition_binding"]["$ref"] == (
        "https://benchwork.dev/schemas/execution-observation-evidence/1.0#/$defs/observation_evidence_disposition_binding"
    )
    owner_schema = json.loads((SCHEMAS / "execution-observation-evidence-1.0.json").read_text())
    receipt_ref = owner_schema["$defs"]["observation_evidence_disposition_binding"]["properties"]["result_ingress_receipt_binding"]["$ref"]
    assert receipt_ref == "https://benchwork.dev/schemas/execution-result-ingress-receipt/1.0#/$defs/result_ingress_receipt_binding"

    receipt = _receipt()
    validate_execution_result_ingress_receipt_v1(receipt)
    assert load_execution_result_ingress_receipt_v1(json.dumps(receipt)) == receipt
    evidence = _evidence(receipt)
    validate_execution_observation_evidence_v1(evidence)
    assert load_execution_observation_evidence_v1(json.dumps(evidence)) == evidence
    validate_execution_observation_evidence_supplied_receipt_v1(evidence, receipt)


def test_result_ingress_index_seals_receipt_candidate_and_status_bindings() -> None:
    index = _result_ingress_index()
    validate_execution_result_ingress_index_v1(index)
    assert load_execution_result_ingress_index_v1(json.dumps(index)) == index

    bad_payload = deepcopy(index)
    bad_payload["ingress_event_intent"]["event_candidate"]["payload"]["result_sigil"] = SIGIL
    bad_payload["ingress_event_intent"]["event_candidate"]["event_sigil"] = content_sigil(
        {key: member for key, member in bad_payload["ingress_event_intent"]["event_candidate"].items() if key != "event_sigil"}
    )
    bad_payload["ingress_event_intent"]["intent_sigil"] = content_sigil(
        {key: member for key, member in bad_payload["ingress_event_intent"].items() if key != "intent_sigil"}
    )
    bad_payload["index_sigil"] = content_sigil(
        {key: member for key, member in bad_payload.items() if key != "index_sigil"}
    )
    with pytest.raises(Exception, match="candidate payload"):
        validate_execution_result_ingress_index_v1(bad_payload)

    bad_pending = deepcopy(index)
    bad_pending["status"]["expected_journal_head"]["last_sequence"] = 1
    bad_pending["status"]["expected_journal_head"]["head_sigil"] = content_sigil({
        key: member for key, member in bad_pending["status"]["expected_journal_head"].items() if key != "head_sigil"
    })
    bad_pending["index_sigil"] = content_sigil(
        {key: member for key, member in bad_pending.items() if key != "index_sigil"}
    )
    with pytest.raises(Exception, match="pending Index Head"):
        validate_execution_result_ingress_index_v1(bad_pending)

    bad_owner = deepcopy(index)
    bad_owner["ingress_event_intent"]["event_candidate"]["executor_epoch"] = 2
    bad_owner["ingress_event_intent"]["event_candidate"]["event_sigil"] = content_sigil(
        {key: member for key, member in bad_owner["ingress_event_intent"]["event_candidate"].items() if key != "event_sigil"}
    )
    bad_owner["ingress_event_intent"]["intent_sigil"] = content_sigil(
        {key: member for key, member in bad_owner["ingress_event_intent"].items() if key != "intent_sigil"}
    )
    bad_owner["index_sigil"] = content_sigil(
        {key: member for key, member in bad_owner.items() if key != "index_sigil"}
    )
    with pytest.raises(Exception, match="candidate Event disagrees with Receipt owner"):
        validate_execution_result_ingress_index_v1(bad_owner)

    committed = deepcopy(index)
    candidate = committed["ingress_event_intent"]["event_candidate"]
    committed["status"] = {"kind": "COMMITTED", "expected_prior_index_sigil": SIGIL,
                           "actual_event_ref": {"journal_id": candidate["journal_id"], "event_id": candidate["event_id"],
                                                "sequence": candidate["sequence"], "event_sigil": candidate["event_sigil"]},
                           "committed_at": STAMP}
    committed["index_sigil"] = content_sigil(
        {key: member for key, member in committed.items() if key != "index_sigil"}
    )
    validate_execution_result_ingress_index_v1(committed)


def test_storage_root_manifest_closes_local_owner_and_blob_integrity() -> None:
    manifest = _storage_root_manifest()
    validate_execution_storage_root_manifest_v1(manifest)
    assert load_execution_storage_root_manifest_v1(json.dumps(manifest)) == manifest

    bad_subject_id = deepcopy(manifest)
    bad_subject_id["entries"][0]["storage_subject_id"] = SIGIL
    bad_subject_id["entries"][0]["entry_sigil"] = content_sigil({
        key: member for key, member in bad_subject_id["entries"][0].items() if key != "entry_sigil"
    })
    bad_subject_id["manifest_sigil"] = content_sigil({
        key: member for key, member in bad_subject_id.items() if key != "manifest_sigil"
    })
    with pytest.raises(Exception, match="storage subject ID mismatch"):
        validate_execution_storage_root_manifest_v1(bad_subject_id)

    bad_protection = deepcopy(manifest)
    bad_protection["protection_plan"] = {
        "kind": "PLANNED", "reference_set_registration_event_id": "SE-ONE", "hold_id": "SH-ONE",
        "hold_set_event_id": "SE-TWO", "policy_id": "SP-EXECUTION-ROOT-HOLD-V1", "policy_sigil": SIGIL,
        "hold_lifetime": {"kind": "OWNER_TERMINAL"},
    }
    bad_protection["manifest_sigil"] = content_sigil({
        key: member for key, member in bad_protection.items() if key != "manifest_sigil"
    })
    with pytest.raises(Exception, match="protection plan"):
        validate_execution_storage_root_manifest_v1(bad_protection)

    committed_blob = deepcopy(manifest)
    blob = {"blob_sigil": SIGIL_B, "size_bytes": 1}
    committed_blob["entries"][0]["claimed_blob"] = blob
    committed_blob["entries"][0]["storage_origin"] = {
        "kind": "COMMITTED_BLOB",
        "transfer": {"transfer_id": "ST-ONE", "transfer_attempt_id": "SA-ONE",
                     "request_record_sigil": SIGIL, "attempt_record_sigil": SIGIL, "terminal_event": {
            "journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1, "event_sigil": SIGIL,
        }},
        "provenance_id": "SP-ONE", "provenance_sigil": SIGIL, "blob_record_sigil": SIGIL,
        "terminal_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1, "event_sigil": SIGIL},
    }
    committed_blob["entries"][0]["entry_sigil"] = content_sigil({
        key: member for key, member in committed_blob["entries"][0].items() if key != "entry_sigil"
    })
    committed_blob["blob_refs"] = [blob]
    committed_blob["protection_plan"] = {
        "kind": "PLANNED", "reference_set_registration_event_id": "SE-ONE", "hold_id": "SH-ONE",
        "hold_set_event_id": "SE-TWO", "policy_id": "SP-EXECUTION-ROOT-HOLD-V1", "policy_sigil": SIGIL,
        "hold_lifetime": {"kind": "OWNER_TERMINAL"},
    }
    committed_blob["manifest_sigil"] = content_sigil({
        key: member for key, member in committed_blob.items() if key != "manifest_sigil"
    })
    validate_execution_storage_root_manifest_v1(committed_blob)

    missing_blob = deepcopy(committed_blob)
    missing_blob["blob_refs"] = []
    missing_blob["manifest_sigil"] = content_sigil({
        key: member for key, member in missing_blob.items() if key != "manifest_sigil"
    })
    with pytest.raises(Exception, match="Blob refs"):
        validate_execution_storage_root_manifest_v1(missing_blob)

    output_manifest = deepcopy(manifest)
    output_manifest.update({
        "root_kind": "ATTEMPT_OUTPUT", "attempt_id": "AT-ONE",
        "owner_binding": {
            "kind": "ATTEMPT_OUTPUT", "job_binding_sigil": SIGIL, "attempt_binding_sigil": SIGIL,
            "result_binding": {"kind": "NONE"}, "log_set_sigil": SIGIL, "output_set_sigil": SIGIL,
            "control_evidence_set_binding": {"kind": "PENDING"},
            "terminal_source_binding": {"kind": "NOT_APPLICABLE"}, "quarantine_plan_sigil": SIGIL,
        },
    })
    output_subject = {
        "kind": "ATTEMPT_OUTPUT", "logical_name": "output", "schema_id": "result/1.0",
        "schema_sigil": SIGIL, "staging_reference_sigil": SIGIL, "byte_size": 1, "blob_sigil": SIGIL_B,
    }
    output_entry = deepcopy(committed_blob["entries"][0])
    output_entry["storage_subject_id"] = SIGIL
    output_entry["subject"] = output_subject
    output_entry["claimed_blob"] = {"blob_sigil": SIGIL_B, "size_bytes": 1}
    output_entry["entry_sigil"] = content_sigil({
        key: member for key, member in output_entry.items() if key != "entry_sigil"
    })
    output_manifest["entries"] = [output_entry]
    output_manifest["blob_refs"] = [output_entry["claimed_blob"]]
    output_manifest["protection_plan"] = {
        **committed_blob["protection_plan"],
        "hold_lifetime": {"kind": "OUTPUT_RETENTION", "maximum_duration_seconds": 0},
    }
    output_manifest["manifest_id"] = derive_execution_storage_root_manifest_id_v1(output_manifest)
    output_manifest["manifest_sigil"] = content_sigil({
        key: member for key, member in output_manifest.items() if key != "manifest_sigil"
    })
    validate_execution_storage_root_manifest_v1(output_manifest)

    mismatched_output_blob = deepcopy(output_manifest)
    mismatched_output_blob["entries"][0]["claimed_blob"] = {"blob_sigil": SIGIL, "size_bytes": 2}
    mismatched_output_blob["entries"][0]["entry_sigil"] = content_sigil({
        key: member for key, member in mismatched_output_blob["entries"][0].items() if key != "entry_sigil"
    })
    mismatched_output_blob["blob_refs"] = [mismatched_output_blob["entries"][0]["claimed_blob"]]
    mismatched_output_blob["manifest_sigil"] = content_sigil({
        key: member for key, member in mismatched_output_blob.items() if key != "manifest_sigil"
    })
    with pytest.raises(Exception, match="claimed Blob disagrees with subject"):
        validate_execution_storage_root_manifest_v1(mismatched_output_blob)


def test_root_hold_release_authorization_closes_id_sigil_and_prefix_bounds() -> None:
    authorization = _root_hold_release_authorization()
    validate_execution_root_hold_release_authorization_v1(authorization)
    assert load_execution_root_hold_release_authorization_v1(json.dumps(authorization)) == authorization

    stale_id = deepcopy(authorization)
    stale_id["release_authorization_id"] = "EHR-" + "A" * 64
    stale_id["release_authorization_sigil"] = content_sigil({
        key: member for key, member in stale_id.items() if key != "release_authorization_sigil"
    })
    with pytest.raises(Exception, match="Authorization ID mismatch"):
        validate_execution_root_hold_release_authorization_v1(stale_id)

    reversed_events = deepcopy(authorization)
    reversed_events["basis"]["terminal_event_sequence"] = 1
    reversed_events["release_authorization_sigil"] = content_sigil({
        key: member for key, member in reversed_events.items() if key != "release_authorization_sigil"
    })
    with pytest.raises(Exception, match="event order"):
        validate_execution_root_hold_release_authorization_v1(reversed_events)

    short_head = deepcopy(authorization)
    short_head["basis"]["verification_head"]["last_sequence"] = 1
    short_head["basis"]["verification_head"]["head_sigil"] = content_sigil({
        key: member for key, member in short_head["basis"]["verification_head"].items() if key != "head_sigil"
    })
    short_head["release_authorization_sigil"] = content_sigil({
        key: member for key, member in short_head.items() if key != "release_authorization_sigil"
    })
    with pytest.raises(Exception, match="Head predates"):
        validate_execution_root_hold_release_authorization_v1(short_head)


def test_control_evidence_set_closes_owner_id_and_ten_dimension_matrix() -> None:
    evidence_set = _control_evidence_set()
    validate_execution_control_evidence_set_v1(evidence_set)
    assert load_execution_control_evidence_set_v1(json.dumps(evidence_set)) == evidence_set

    wrong_order = deepcopy(evidence_set)
    wrong_order["control_evidence_refs"][0], wrong_order["control_evidence_refs"][1] = (
        wrong_order["control_evidence_refs"][1], wrong_order["control_evidence_refs"][0]
    )
    wrong_order["control_evidence_set_sigil"] = content_sigil({
        key: member for key, member in wrong_order.items() if key != "control_evidence_set_sigil"
    })
    with pytest.raises(Exception, match="matrix order"):
        validate_execution_control_evidence_set_v1(wrong_order)

    duplicate_id = deepcopy(evidence_set)
    duplicate_id["control_evidence_refs"][1]["control_evidence_id"] = (
        duplicate_id["control_evidence_refs"][0]["control_evidence_id"]
    )
    duplicate_id["control_evidence_set_sigil"] = content_sigil({
        key: member for key, member in duplicate_id.items() if key != "control_evidence_set_sigil"
    })
    with pytest.raises(Exception, match="evidence IDs"):
        validate_execution_control_evidence_set_v1(duplicate_id)


def test_quarantine_binding_set_closes_frozen_owner_and_self_identity() -> None:
    binding_set = _quarantine_binding_set()
    validate_execution_quarantine_binding_set_v1(binding_set)
    assert load_execution_quarantine_binding_set_v1(json.dumps(binding_set)) == binding_set

    stale_id = deepcopy(binding_set)
    stale_id["quarantine_binding_set_id"] = "QBS-" + "A" * 64
    stale_id["quarantine_binding_set_sigil"] = content_sigil({
        key: member for key, member in stale_id.items() if key != "quarantine_binding_set_sigil"
    })
    with pytest.raises(Exception, match="Binding Set ID mismatch"):
        validate_execution_quarantine_binding_set_v1(stale_id)

    populated = deepcopy(binding_set)
    event = {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1, "event_sigil": SIGIL}
    backend_object = {
        "backend_id": "BACKEND", "object_identity_sigil": SIGIL, "locator_sigil": SIGIL,
        "generation": "GENERATION", "size_bytes": 1, "blob_sigil": SIGIL_B,
    }
    subject = {
        "kind": "ATTEMPT_OUTPUT", "logical_name": "output", "schema_id": "result/1.0",
        "schema_sigil": SIGIL, "staging_reference_sigil": SIGIL, "byte_size": 1, "blob_sigil": SIGIL_B,
    }
    binding = {
        "storage_subject_id": SIGIL, "manifest_entry_sigil": SIGIL, "subject": subject,
        "storage_origin": {"kind": "QUARANTINE", "transfer": {
            "transfer_id": "ST-ONE", "transfer_attempt_id": "SA-ONE", "request_record_sigil": SIGIL,
            "attempt_record_sigil": SIGIL, "terminal_event": event,
        }, "provenance_id": "PROVENANCE", "provenance_sigil": SIGIL, "quarantine_id": "SQ-ONE",
            "quarantine_origin_event": event},
        "quarantine_ref": {"quarantine_id": "SQ-ONE", "owner_kind": "TRANSFER_ATTEMPT", "owner_id": "SA-ONE",
                           "quarantine_record_sigil": SIGIL, "origin_event": event,
                           "observation_event": {**event, "event_id": "SE-TWO", "sequence": 2, "event_sigil": SIGIL_B},
                           "state": "HELD", "source_object": backend_object, "destination_object": backend_object,
                           "source_cleanup": {"state": "NOT_REQUIRED", "staging_object": None, "evidence_sigil": None, "reason": None},
                           "reason": {"code": "BACKEND_UNAVAILABLE", "evidence_sigils": []}},
        "disposition": "RETAINED", "quarantine_binding_sigil": "",
    }
    binding["quarantine_binding_sigil"] = content_sigil({
        key: member for key, member in binding.items() if key != "quarantine_binding_sigil"
    })
    populated["bindings"] = [binding]
    populated["quarantine_binding_set_sigil"] = content_sigil({
        key: member for key, member in populated.items() if key != "quarantine_binding_set_sigil"
    })
    validate_execution_quarantine_binding_set_v1(populated)

    mismatched_owner = deepcopy(populated)
    mismatched_owner["bindings"][0]["quarantine_ref"]["owner_id"] = "SA-TWO"
    mismatched_owner["bindings"][0]["quarantine_binding_sigil"] = content_sigil({
        key: member for key, member in mismatched_owner["bindings"][0].items() if key != "quarantine_binding_sigil"
    })
    mismatched_owner["quarantine_binding_set_sigil"] = content_sigil({
        key: member for key, member in mismatched_owner.items() if key != "quarantine_binding_set_sigil"
    })
    with pytest.raises(Exception, match="origin disagrees with Quarantine owner"):
        validate_execution_quarantine_binding_set_v1(mismatched_owner)


def test_output_storage_observation_set_closes_id_members_and_blob_union() -> None:
    observation_set = _output_storage_observation_set()
    validate_execution_output_storage_observation_set_v1(observation_set)
    assert load_execution_output_storage_observation_set_v1(json.dumps(observation_set)) == observation_set

    stale_id = deepcopy(observation_set)
    stale_id["observation_set_id"] = "OS-" + "A" * 64
    stale_id["observation_set_sigil"] = content_sigil({
        key: member for key, member in stale_id.items() if key != "observation_set_sigil"
    })
    with pytest.raises(Exception, match="Observation Set ID mismatch"):
        validate_execution_output_storage_observation_set_v1(stale_id)

    wrong_log_order = deepcopy(observation_set)
    wrong_log_order["members"][1], wrong_log_order["members"][2] = (
        wrong_log_order["members"][2], wrong_log_order["members"][1]
    )
    wrong_log_order["observation_set_sigil"] = content_sigil({
        key: member for key, member in wrong_log_order.items() if key != "observation_set_sigil"
    })
    with pytest.raises(Exception, match="Log streams are not in fixed order"):
        validate_execution_output_storage_observation_set_v1(wrong_log_order)

    missing_blob = deepcopy(observation_set)
    missing_blob["blob_sigils"] = []
    missing_blob["observation_set_sigil"] = content_sigil({
        key: member for key, member in missing_blob.items() if key != "observation_set_sigil"
    })
    with pytest.raises(Exception, match="Blob Sigils disagree"):
        validate_execution_output_storage_observation_set_v1(missing_blob)

    mismatched_protection = deepcopy(observation_set)
    mismatched_protection["output_root_protection"] = {
        "kind": "NO_HOLD",
        "terminalization_storage_manifest_binding": {
            "kind": "FROZEN", "storage_root_manifest_id": "ESM-" + "B" * 64,
            "storage_root_manifest_sigil": SIGIL_B,
        },
    }
    mismatched_protection["observation_set_id"] = derive_execution_output_storage_observation_set_id_v1(
        mismatched_protection
    )
    mismatched_protection["observation_set_sigil"] = content_sigil({
        key: member for key, member in mismatched_protection.items() if key != "observation_set_sigil"
    })
    with pytest.raises(Exception, match="protection disagrees"):
        validate_execution_output_storage_observation_set_v1(mismatched_protection)

    pending_protection = deepcopy(observation_set)
    pending_protection["output_root_protection"] = {"kind": "PENDING"}
    pending_protection["observation_set_id"] = derive_execution_output_storage_observation_set_id_v1(
        pending_protection
    )
    pending_protection["observation_set_sigil"] = content_sigil({
        key: member for key, member in pending_protection.items() if key != "observation_set_sigil"
    })
    with pytest.raises(Exception, match="requires a terminal output-root protection"):
        validate_execution_output_storage_observation_set_v1(pending_protection)



def test_jew4_owner_fences_and_supplied_receipt_comparison_fail_closed() -> None:
    receipt = _receipt()
    evidence = _evidence(receipt)

    bad_owner = deepcopy(evidence)
    bad_owner["fence_tuple"]["executor_epoch"] = 2
    _reseal_evidence(bad_owner)
    with pytest.raises(Exception, match="fence_tuple: executor_epoch"):
        validate_execution_observation_evidence_v1(bad_owner)

    bad_receipt = deepcopy(receipt)
    bad_receipt["receiver_identity"]["executor_epoch"] = 2
    _reseal_receipt(bad_receipt)
    with pytest.raises(Exception, match="receiver epoch"):
        validate_execution_observation_evidence_supplied_receipt_v1(evidence, bad_receipt)

    bad_subject = deepcopy(receipt)
    bad_subject["result_observation_binding"]["observation_evidence_subject_sigil"] = SIGIL
    _reseal_receipt(bad_subject)
    with pytest.raises(Exception, match="observation subject Sigil"):
        validate_execution_result_ingress_receipt_v1(bad_subject)

    mismatched_assessment = deepcopy(evidence)
    mismatched_assessment["assessment"]["verified_runtime_observation"] = {
        **mismatched_assessment["assessment"]["verified_runtime_observation"],
        "process_count": 1,
    }
    _reseal_evidence(mismatched_assessment)
    with pytest.raises(Exception, match="copy the Result observation"):
        validate_execution_observation_evidence_v1(mismatched_assessment)

    mismatched_source = deepcopy(evidence)
    mismatched_source["assessment"]["verified_source_binding"]["source_kind"] = "EXECUTOR_SUPERVISOR"
    _reseal_evidence(mismatched_source)
    with pytest.raises(Exception, match="source does not match"):
        validate_execution_observation_evidence_v1(mismatched_source)

    mismatched_receipt = deepcopy(evidence)
    mismatched_receipt["result_ingress_receipt_binding"]["ingress_receipt_sigil"] = SIGIL
    _reseal_evidence(mismatched_receipt)
    with pytest.raises(Exception, match="ingress receipt binding"):
        validate_execution_observation_evidence_supplied_receipt_v1(mismatched_receipt, receipt)


@pytest.mark.parametrize(
    "loader,fixture",
    [
        (load_execution_result_ingress_receipt_v1, "execution-result-ingress-receipt-v1"),
        (load_execution_observation_evidence_v1, "execution-observation-evidence-v1"),
    ],
)
def test_jew4_owner_loaders_reject_duplicate_bom_and_unknown_fields(loader: Any, fixture: str) -> None:
    raw = (FIXTURES / fixture / "invalid-duplicate-key.json").read_text()
    with pytest.raises(Exception, match="duplicate JSON key"):
        loader(raw)
    with pytest.raises(Exception, match="BOM"):
        loader(b"\xef\xbb\xbf{}")
    valid = _receipt() if "receipt" in fixture else _evidence(_receipt())
    valid["append_authority"] = True
    self_member = "ingress_receipt_sigil" if "receipt" in fixture else "observation_evidence_sigil"
    valid[self_member] = content_sigil({key: value for key, value in valid.items() if key != self_member})
    with pytest.raises(Exception):
        loader(json.dumps(valid))
