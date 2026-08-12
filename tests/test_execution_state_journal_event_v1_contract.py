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
    replay_execution_initial_prefix_v1,
    replay_execution_journal_prefix_v1,
    validate_execution_observation_evidence_v1,
    validate_execution_observation_evidence_supplied_receipt_v1,
    validate_execution_journal_head_v1,
    validate_execution_initial_state_supplied_facts_v1,
    validate_execution_request_v1,
    validate_execution_result_ingress_receipt_v1,
    validate_execution_result_ingress_index_v1,
    validate_execution_recovery_action_set_v1,
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
        "idempotency_key_sigil": SIGIL,
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
    with pytest.raises(Exception, match="sequence gap"):
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
