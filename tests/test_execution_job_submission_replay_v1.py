from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from benchwork.athanor import AthanorError, canonical_json, content_sigil
from benchwork.execution_contracts import (
    build_execution_state_v1,
    build_execution_journal_event_v1,
    derive_observation_evidence_id_v1,
    derive_observation_evidence_subject_sigil_v1,
    derive_result_ingress_receipt_id_v1,
    replay_execution_journal_prefix_v1,
    replay_execution_journal_supplied_facts_v1,
    replay_execution_supplied_state_suffix_v1,
    load_agent_result_acceptance_authorization_v1,
    load_sanctum_assurance_claim_v1,
    validate_agent_result_acceptance_authorization_v1,
    validate_sanctum_assurance_claim_v1,
    validate_execution_job_v1,
    validate_sanctum_assurance_claim_supplied_attempt_facts_v1,
)


ROOT = Path(__file__).parents[1]
INITIAL = json.loads(
    (
        ROOT / "tests/fixtures/phase3/rfc0012/execution-journal-event-v1/valid-initial.json"
    ).read_text()
)
SIGIL = "sha256:" + "a" * 64
SIGIL_B = "sha256:" + "b" * 64
JOB_ID = "JB-" + "A" * 64


def _job() -> dict[str, Any]:
    evidence = {
        "profile": "PHASE3_CHRONICLE_HEAD_ADMISSION_V1",
        "job_id": JOB_ID,
        "start_request_sigil": SIGIL,
        "observed_chronicle_head": {
            "schema_version": "chronicle-head/1.1",
            "event_count": 0,
            "terminal_receipt_sigil": None,
        },
        "observed_at": "2026-08-06T00:00:00Z",
        "validator_build_sigil": SIGIL,
        "evidence_sigil": "",
    }
    evidence["evidence_sigil"] = content_sigil(
        {key: value for key, value in evidence.items() if key != "evidence_sigil"}
    )
    job: dict[str, Any] = {
        "schema_version": "execution-job/1.0",
        "job_id": JOB_ID,
        "submitted_at": "2026-08-06T00:00:00Z",
        "submission_idempotency_key_sigil": SIGIL,
        "start_request_sigil": SIGIL,
        "task_id": "TK-ONE",
        "task_capsule_sigil": SIGIL,
        "specification_id": "ES-ONE",
        "specification_sigil": SIGIL,
        "admission_chronicle_head": evidence["observed_chronicle_head"],
        "admission_chronicle_head_evidence": evidence,
        "assurance_requirement": {
            "requested_level": "SANCTUM-A0",
            "profile_version": "1.0",
            "profile_sigil": SIGIL,
            "conformance_suite_id": "CS-ONE",
            "conformance_suite_sigil": SIGIL,
        },
        "deadline_due_at": "2026-08-06T00:01:00Z",
        "job_budget": {
            "attempts": 1,
            "cpu_time_seconds": 1,
            "storage_bytes_written": 1,
            "output_bytes": 1,
            "log_bytes": 1,
            "process_starts": 1,
            "network_egress_bytes": 1,
            "network_requests": 1,
        },
        "job_storage_roots": [],
        "job_binding_sigil": "",
    }
    job["job_binding_sigil"] = content_sigil(
        {key: value for key, value in job.items() if key != "job_binding_sigil"}
    )
    return job


def _submitted_event(job: dict[str, Any]) -> dict[str, Any]:
    event = {
        "schema_version": "execution-journal-event/1.0",
        "journal_id": INITIAL["journal_id"],
        "event_id": "JE-TWO",
        "sequence": 2,
        "event_type": "job.submitted",
        "executor_instance_id": INITIAL["executor_instance_id"],
        "executor_epoch": INITIAL["executor_epoch"],
        "executor_build_sigil": INITIAL["executor_build_sigil"],
        "recorded_at": job["submitted_at"],
        "observed_at": None,
        "entity_revisions": [
            {
                "entity_kind": "JOB",
                "entity_id": job["job_id"],
                "preceding_revision": None,
                "next_revision": 0,
            }
        ],
        "causation_event_id": None,
        "idempotency_key_sigil": job["submission_idempotency_key_sigil"],
        "recovery_action_binding": None,
        "payload": {
            key: job[key]
            for key in (
                "job_binding_sigil",
                "start_request_sigil",
                "submission_idempotency_key_sigil",
                "admission_chronicle_head",
                "admission_chronicle_head_evidence",
                "deadline_due_at",
                "job_budget",
                "job_storage_roots",
            )
        },
        "previous_event_sigil": INITIAL["event_sigil"],
    }
    return build_execution_journal_event_v1(event)


def _queued_event(submitted: dict[str, Any]) -> dict[str, Any]:
    return build_execution_journal_event_v1(
        {
            "schema_version": "execution-journal-event/1.0",
            "journal_id": submitted["journal_id"],
            "event_id": "JE-THREE",
            "sequence": 3,
            "event_type": "job.queued",
            "executor_instance_id": submitted["executor_instance_id"],
            "executor_epoch": submitted["executor_epoch"],
            "executor_build_sigil": submitted["executor_build_sigil"],
            "recorded_at": "2026-08-06T00:00:01Z",
            "observed_at": None,
            "entity_revisions": [
                {
                    "entity_kind": "JOB",
                    "entity_id": JOB_ID,
                    "preceding_revision": 0,
                    "next_revision": 1,
                }
            ],
            "causation_event_id": submitted["event_id"],
            "idempotency_key_sigil": None,
            "recovery_action_binding": None,
            "payload": {
                "admission_evidence_sigil": SIGIL,
                "queue_key": {"ready_sequence": 3, "job_id": JOB_ID},
            },
            "previous_event_sigil": submitted["event_sigil"],
        }
    )


def _attempt() -> dict[str, Any]:
    attempt: dict[str, Any] = {
        "schema_version": "execution-attempt/1.0",
        "attempt_id": "AT-ONE",
        "job_id": JOB_ID,
        "job_binding_sigil": _job()["job_binding_sigil"],
        "retry_ordinal": 1,
        "fencing_generation": 1,
        "assurance_requirement": {
            "requested_level": "SANCTUM-A0",
            "profile_version": "1.0",
            "profile_sigil": SIGIL,
            "conformance_suite_id": "CS-ONE",
            "conformance_suite_sigil": SIGIL,
        },
        "backend_identity": "LOCAL",
        "backend_version": "1.0",
        "backend_implementation_sigil": SIGIL,
        "backend_configuration_sigil": SIGIL,
        "base_identity": None,
        "base_sigil": None,
        "input_identities": [],
        "resume_mode": "FRESH",
        "crucible_id": "CU-ONE",
        "output_namespace_id": "ON-ONE",
        "log_stream_ids": {"STDOUT": "LG-ONE", "STDERR": "LG-TWO", "STRUCTURED": "LG-THREE"},
        "budget_reservation": {
            "attempts": 1,
            "cpu_time_seconds": 1,
            "storage_bytes_written": 1,
            "output_bytes": 1,
            "log_bytes": 1,
            "process_starts": 1,
            "network_egress_bytes": 1,
            "network_requests": 1,
        },
        "attempt_authorization_requirement": {"kind": "NONE", "effects": []},
        "created_at": "2026-08-06T00:00:02Z",
        "deadline_due_at": "2026-08-06T00:00:30Z",
        "attempt_binding_sigil": "",
    }
    attempt["attempt_binding_sigil"] = content_sigil(
        {key: value for key, value in attempt.items() if key != "attempt_binding_sigil"}
    )
    return attempt


def _reseal_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    attempt["attempt_binding_sigil"] = content_sigil(
        {key: value for key, value in attempt.items() if key != "attempt_binding_sigil"}
    )
    return attempt


def _assurance_claim() -> dict[str, Any]:
    claim: dict[str, Any] = {
        "schema_version": "sanctum-assurance-claim/1.0",
        "assurance_claim_id": "AC-0" + "0" * 25,
        "job_id": JOB_ID, "attempt_id": "AT-ONE", "attempt_binding_sigil": SIGIL,
        "attempt_terminal_event": {"journal_id": INITIAL["journal_id"], "sequence": 1,
                                   "event_id": "JE-ONE", "event_sigil": SIGIL},
        "requested_assurance": "SANCTUM-A0", "realized_level": "SANCTUM-A0",
        "satisfies_request": True,
        "assurance_profile_binding": {"profile_version": "1.0", "profile_sigil": SIGIL,
                                      "conformance_suite_id": "CS-ONE", "conformance_suite_sigil": SIGIL},
        "backend_identity": "LOCAL", "backend_configuration_sigil": SIGIL,
        "host_binding": {"kind": "NONE"}, "policy_set_sigil": SIGIL,
        "result_binding": {"kind": "NONE"},
        "control_evidence_set_binding": {"kind": "FROZEN", "control_evidence_set_id": "CES-" + "A" * 64,
                                        "control_evidence_set_sigil": SIGIL},
        "terminal_status": {"attempt_state": "FAILED", "process_termination_status": "EXITED",
                            "handle_revocation_status": "REVOKED", "cleanup_status": "VERIFIED",
                            "quarantine_status": "NOT_REQUIRED"},
        "evidence_cut": {
            "journal_prefix": {"journal_id": INITIAL["journal_id"], "ending_sequence": 1,
                               "ending_event_id": "JE-ONE", "ending_event_sigil": SIGIL},
            "state_sigil": SIGIL,
            "accounting_capture_event": {"journal_id": INITIAL["journal_id"], "sequence": 1,
                                         "event_id": "JE-ONE", "event_sigil": SIGIL},
            "budget_settlement_event": {"journal_id": INITIAL["journal_id"], "sequence": 1,
                                        "event_id": "JE-ONE", "event_sigil": SIGIL},
            "control_evidence_allocation_commit_sigil": SIGIL,
            "control_evidence_inventory_sigil": SIGIL,
            "control_evidence_set_binding": {"kind": "FROZEN", "control_evidence_set_id": "CES-" + "A" * 64,
                                             "control_evidence_set_sigil": SIGIL},
            "predicate_result_set_binding": {"schema_version": "sanctum-assurance-predicate-result-set/1.0",
                                             "predicate_result_set_id": "PRS-" + "A" * 64, "predicate_result_set_sigil": SIGIL},
            "verification_bundle_binding": {"schema_version": "sanctum-assurance-verification-bundle/1.0",
                                            "verification_bundle_id": "AVB-" + "A" * 64, "verification_bundle_sigil": SIGIL},
            "verification_started_at": "2026-08-06T00:00:00Z",
            "verification_completed_at": "2026-08-06T00:00:01Z",
        },
        "verifier_binding": {
            "verifier_identity": {"verifier_id": "VERIFIER", "verifier_build_sigil": SIGIL,
                                  "verifier_profile_id": "PROFILE", "verifier_profile_sigil": SIGIL},
            "registry_authority_binding": {"schema_version": "sanctum-verifier-registry-authority-binding/1.0",
                                            "authority_policy_id": "VAP-" + "A" * 64, "authority_policy_sigil": SIGIL,
                                            "installed_head_id": "VRH-" + "A" * 64, "installed_head_sigil": SIGIL,
                                            "active_transition_id": "VAT-" + "A" * 64, "active_transition_sigil": SIGIL},
            "registry_snapshot_binding": {"schema_version": "sanctum-trusted-verifier-registry-snapshot/1.0",
                                          "registry_snapshot_id": "VRS-0" + "0" * 25, "registry_snapshot_sigil": SIGIL},
            "authorization_binding": {"schema_version": "sanctum-verifier-authorization/1.0",
                                      "authorization_record_id": "VAU-" + "A" * 64, "authorization_record_sigil": SIGIL},
            "authentication_binding": {"schema_version": "sanctum-verifier-authentication-evidence/1.0",
                                        "authentication_evidence_id": "VAE-" + "A" * 64, "authentication_evidence_sigil": SIGIL},
        },
        "issued_at": "2026-08-06T00:00:02Z", "assurance_claim_sigil": "",
    }
    claim["assurance_claim_sigil"] = content_sigil(
        {key: value for key, value in claim.items() if key != "assurance_claim_sigil"}
    )
    return claim


def test_assurance_claim_loader_checks_local_integrity_only() -> None:
    claim = _assurance_claim()
    validate_sanctum_assurance_claim_v1(claim)
    assert load_sanctum_assurance_claim_v1(json.dumps(claim)) == claim
    stale = deepcopy(claim)
    stale["issued_at"] = "2026-08-06T00:00:03Z"
    with pytest.raises(AthanorError, match="self-Sigil"):
        validate_sanctum_assurance_claim_v1(stale)
    impossible = deepcopy(claim)
    impossible["requested_assurance"] = "SANCTUM-A2"
    impossible["assurance_claim_sigil"] = content_sigil({
        key: value for key, value in impossible.items() if key != "assurance_claim_sigil"
    })
    with pytest.raises(AthanorError, match="below its request"):
        validate_sanctum_assurance_claim_v1(impossible)


def _acceptance_authorization() -> dict[str, Any]:
    blobs = ["sha256:" + "a" * 64, "sha256:" + "b" * 64]
    policy: dict[str, Any] = {
        "schema_version": "agent-result-acceptance-policy/1.0",
        "policy_id": "agent-result-acceptance", "policy_version": "1.0",
        "canonical_event_type": "agent-result.accepted",
        "transition_request_schema": "agent-result-acceptance-transition-request/1.0",
        "authorization_schema": "agent-result-acceptance-authorization/1.0",
        "agent_result_schema": "agent-result/2.0", "job_outcome_schema": "execution-job-outcome/1.0",
        "reference_intent_schema": "artifact-storage-reference-intent/1.0",
        "chronicle_event_schema": "chronicle-event/1.1", "receipt_schema": "receipt/1.1",
        "ward_evaluator_profile": "sanctum-authority-intersection/1.0",
        "actor_authentication_profile": "mcp-authenticated-invocation/1.0",
        "predicate_profile": "agent-result-acceptance-predicates/1.0",
        "predicates": [
            "EXPECTED_HEAD_ADMISSIBLE", "AUTHENTICATED_INVOCATION_MATCH",
            "TASK_AUTHORITY_CHAIN_VALID", "CURRENT_WARD_PASS", "APPROVAL_CHAIN_VALID",
            "OUTCOME_REDERIVATION_MATCH", "TERMINAL_SUCCESS_ELIGIBLE",
            "EXECUTION_EVIDENCE_VALID", "BUDGET_SETTLED", "ASSURANCE_EVIDENCE_VALID",
            "STORAGE_OBSERVATION_VALID", "TERMINAL_SOURCE_VALID", "EVIDENCE_SELECTION_FINAL",
            "AGENT_RESULT_DERIVATION_MATCH", "REFERENCE_SET_CLOSURE_VALID",
            "ACCEPTANCE_STORAGE_PREFIX_VALID",
        ],
        "policy_sigil": "",
    }
    policy["policy_sigil"] = content_sigil({key: value for key, value in policy.items() if key != "policy_sigil"})
    head = {"schema_version": "chronicle-head/1.1", "event_count": 1, "terminal_receipt_sigil": SIGIL}
    evidence = [
        {"blob_sigil": blob, "size_bytes": 1, "replica_id": f"SR-{index}", "backend_id": "BACKEND",
         "backend_generation": "1", "availability_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1, "event_sigil": SIGIL},
         "integrity_evidence_sigil": SIGIL, "quarantine_status": "CLEAR"}
        for index, blob in enumerate(blobs)
    ]
    authorization: dict[str, Any] = {
        "schema_version": "agent-result-acceptance-authorization/1.0",
        "transition_request_id": "", "event_type": "agent-result.accepted",
        "expected_chronicle_head": head,
        "authority_subject": {
            "registry_binding": {"registry_id": "CR-ONE", "registry_revision": 1, "registry_sigil": SIGIL},
            "task_binding": {"task_id": "TK-ONE", "task_capsule_sigil": SIGIL}, "program_id": "RP-ONE",
            "capability_binding": {"capability_id": "bench.work.exec", "contract_version": "2.0", "capability_contract_sigil": SIGIL},
            "snapshot_binding": {"snapshot_id": "SS-ONE", "snapshot_sigil": SIGIL},
            "circle_binding": {"circle_id": "CI-ONE", "circle_sigil": SIGIL},
            "execution_specification_binding": {"specification_id": "ES-" + "0" * 26, "specification_sigil": SIGIL},
            "job_binding": {"job_id": JOB_ID, "job_binding_sigil": SIGIL},
            "job_outcome_binding": {"outcome_id": "OJ-" + "A" * 64, "outcome_sigil": SIGIL},
            "agent_result_sigil": SIGIL,
        },
        "ward_pass": {"status": "PASS", "ward_decision_id": "WD-ONE", "ward_decision_sigil": SIGIL,
                      "resolved_permission_set_sigil": SIGIL, "evaluated_chronicle_head": head,
                      "evaluated_at": "2026-08-06T00:00:00Z"},
        "approval": {"kind": "NOT_REQUIRED", "ward_decision_id": "WD-ONE", "ward_decision_sigil": SIGIL},
        "acceptance_policy": policy, "acceptance_request_sigil": SIGIL, "idempotency_key_sigil": SIGIL,
        "reference_sets": [{"reference_set_id": "RS-ONE", "reference_set_sigil": SIGIL}],
        "managed_blob_sigils": blobs,
        "acceptance_storage_binding": {"storage_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1, "event_sigil": SIGIL},
                                       "storage_state_sigil": SIGIL, "validated_blob_sigils": blobs,
                                       "validation_evidence": evidence, "validation_evidence_set_sigil": content_sigil(evidence)},
        "actor": {"kind": "AGENT", "actor_id": "ACTOR", "authentication_context_sigil": SIGIL, "actor_sigil": ""},
        "host_invocation": {"host_identity_sigil": SIGIL, "invocation_id": "INVOCATION", "authentication_context_sigil": SIGIL, "invocation_sigil": ""},
        "chronicle_actor": {"actor_id": "ACTOR", "actor_type": "agent", "host": "codex", "authenticated_by": "MCP"},
        "requested_at": "2026-08-06T00:00:00Z", "authorization_sigil": "",
    }
    authorization["transition_request_id"] = "ATR-" + content_sigil([
        "agent-result-acceptance-transition-id/1.0", "TK-ONE", SIGIL,
    ]).removeprefix("sha256:").upper()
    authorization["actor"]["actor_sigil"] = content_sigil({
        key: value for key, value in authorization["actor"].items() if key != "actor_sigil"
    })
    authorization["host_invocation"]["invocation_sigil"] = content_sigil({
        key: value for key, value in authorization["host_invocation"].items()
        if key != "invocation_sigil"
    })
    authorization["authorization_sigil"] = content_sigil({key: value for key, value in authorization.items() if key != "authorization_sigil"})
    return authorization


def test_agent_result_acceptance_authorization_checks_local_closure_only() -> None:
    authorization = _acceptance_authorization()
    validate_agent_result_acceptance_authorization_v1(authorization)
    assert load_agent_result_acceptance_authorization_v1(json.dumps(authorization)) == authorization
    unsorted = deepcopy(authorization)
    unsorted["managed_blob_sigils"] = list(reversed(unsorted["managed_blob_sigils"]))
    unsorted["acceptance_storage_binding"]["validated_blob_sigils"] = list(
        reversed(unsorted["acceptance_storage_binding"]["validated_blob_sigils"])
    )
    unsorted["acceptance_storage_binding"]["validation_evidence"] = list(
        reversed(unsorted["acceptance_storage_binding"]["validation_evidence"])
    )
    unsorted["acceptance_storage_binding"]["validation_evidence_set_sigil"] = content_sigil(unsorted["acceptance_storage_binding"]["validation_evidence"])
    unsorted["authorization_sigil"] = content_sigil({key: value for key, value in unsorted.items() if key != "authorization_sigil"})
    with pytest.raises(AthanorError, match="ASCII-sorted"):
        validate_agent_result_acceptance_authorization_v1(unsorted)
    mismatched = deepcopy(authorization)
    mismatched["acceptance_storage_binding"]["validation_evidence_set_sigil"] = SIGIL
    mismatched["authorization_sigil"] = content_sigil({key: value for key, value in mismatched.items() if key != "authorization_sigil"})
    with pytest.raises(AthanorError, match="evidence-set Sigil"):
        validate_agent_result_acceptance_authorization_v1(mismatched)
    wrong_id = deepcopy(authorization)
    wrong_id["transition_request_id"] = "ATR-" + "A" * 64
    wrong_id["authorization_sigil"] = content_sigil({key: value for key, value in wrong_id.items() if key != "authorization_sigil"})
    with pytest.raises(AthanorError, match="request ID"):
        validate_agent_result_acceptance_authorization_v1(wrong_id)
    wrong_actor = deepcopy(authorization)
    wrong_actor["chronicle_actor"]["actor_type"] = "human"
    wrong_actor["authorization_sigil"] = content_sigil({key: value for key, value in wrong_actor.items() if key != "authorization_sigil"})
    with pytest.raises(AthanorError, match="Actor type"):
        validate_agent_result_acceptance_authorization_v1(wrong_actor)
    wrong_context = deepcopy(authorization)
    wrong_context["host_invocation"]["authentication_context_sigil"] = "sha256:" + "c" * 64
    wrong_context["host_invocation"]["invocation_sigil"] = content_sigil({
        key: value for key, value in wrong_context["host_invocation"].items()
        if key != "invocation_sigil"
    })
    wrong_context["authorization_sigil"] = content_sigil({key: value for key, value in wrong_context.items() if key != "authorization_sigil"})
    with pytest.raises(AthanorError, match="authentication contexts"):
        validate_agent_result_acceptance_authorization_v1(wrong_context)
    outside_prefix = deepcopy(authorization)
    outside_prefix["acceptance_storage_binding"]["validation_evidence"][0]["availability_event"]["sequence"] = 2
    outside_prefix["acceptance_storage_binding"]["validation_evidence_set_sigil"] = content_sigil(
        outside_prefix["acceptance_storage_binding"]["validation_evidence"]
    )
    outside_prefix["authorization_sigil"] = content_sigil({
        key: value for key, value in outside_prefix.items() if key != "authorization_sigil"
    })
    with pytest.raises(AthanorError, match="frozen Storage prefix"):
        validate_agent_result_acceptance_authorization_v1(outside_prefix)


def _allocated_event(queued: dict[str, Any], attempt: dict[str, Any]) -> dict[str, Any]:
    ledger = {
        name: {"limit": value, "reserved": value, "consumed": 0, "exhaustion_status": "EXHAUSTED"}
        for name, value in attempt["budget_reservation"].items()
    }
    ledger["budget_ledger_sigil"] = content_sigil(ledger)
    return build_execution_journal_event_v1(
        {
            "schema_version": "execution-journal-event/1.0",
            "journal_id": queued["journal_id"],
            "event_id": "JE-FOUR",
            "sequence": 4,
            "event_type": "job.attempt_allocated",
            "executor_instance_id": queued["executor_instance_id"],
            "executor_epoch": queued["executor_epoch"],
            "executor_build_sigil": queued["executor_build_sigil"],
            "recorded_at": attempt["created_at"],
            "observed_at": None,
            "entity_revisions": [
                {
                    "entity_kind": "JOB",
                    "entity_id": JOB_ID,
                    "preceding_revision": 1,
                    "next_revision": 2,
                },
                {
                    "entity_kind": "ATTEMPT",
                    "entity_id": "AT-ONE",
                    "preceding_revision": None,
                    "next_revision": 0,
                },
                *sorted(
                    (
                        {
                            "entity_kind": "LOG_STREAM",
                            "entity_id": attempt["log_stream_ids"][stream],
                            "preceding_revision": None,
                            "next_revision": 0,
                        }
                        for stream in ("STDOUT", "STDERR", "STRUCTURED")
                    ),
                    key=lambda item: item["entity_id"],
                ),
            ],
            "causation_event_id": queued["event_id"],
            "idempotency_key_sigil": None,
            "recovery_action_binding": None,
            "payload": {
                "attempt_binding_sigil": attempt["attempt_binding_sigil"],
                "retry_ordinal": 1,
                "fencing_generation": 1,
                "prior_fencing_counter": 0,
                "resulting_fence_floor": 1,
                "budget_reservation": attempt["budget_reservation"],
                "resulting_budget_ledger_sigil": ledger["budget_ledger_sigil"],
            },
            "previous_event_sigil": queued["event_sigil"],
        }
    )


def _preflight_event(allocated: dict[str, Any]) -> dict[str, Any]:
    return build_execution_journal_event_v1(
        {
            "schema_version": "execution-journal-event/1.0", "journal_id": allocated["journal_id"],
            "event_id": "JE-FIVE", "sequence": 5, "event_type": "attempt.preflight_started",
            "executor_instance_id": allocated["executor_instance_id"], "executor_epoch": allocated["executor_epoch"],
            "executor_build_sigil": allocated["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:03Z",
            "observed_at": None,
            "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 0, "next_revision": 1}],
            "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None,
            "payload": {"preflight_plan_sigil": SIGIL, "freshness_evidence_sigil": SIGIL},
            "previous_event_sigil": allocated["event_sigil"],
        }
    )


def _preflight_passed_event(preflight: dict[str, Any]) -> dict[str, Any]:
    return build_execution_journal_event_v1(
        {
            "schema_version": "execution-journal-event/1.0", "journal_id": preflight["journal_id"],
            "event_id": "JE-SIX", "sequence": 6, "event_type": "attempt.preflight_passed",
            "executor_instance_id": preflight["executor_instance_id"], "executor_epoch": preflight["executor_epoch"],
            "executor_build_sigil": preflight["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:04Z",
            "observed_at": None,
            "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 1, "next_revision": 2}],
            "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None,
            "payload": {"materialization_identity": "MATERIALIZATION", "materialization_sigil": SIGIL,
                        "preflight_evidence_set_sigil": SIGIL, "input_storage_roots": []},
            "previous_event_sigil": preflight["event_sigil"],
        }
    )


def test_job_submission_replay_requires_exact_supplied_job() -> None:
    job = _job()
    validate_execution_job_v1(job)
    event = _submitted_event(job)
    state = replay_execution_journal_prefix_v1([INITIAL, event], supplied_jobs=[job])
    assert state["jobs"][0]["state"] == "SUBMITTED"
    assert state["jobs"][0]["budget_ledger"]["attempts"]["limit"] == 1
    assert state["deadlines"][0]["deadline_kind"] == "JOB_DEADLINE"
    assert state["idempotency_records"][0]["scope_id"] == "TK-ONE"

    queued = _queued_event(event)
    queued_state = replay_execution_journal_prefix_v1([INITIAL, event, queued], supplied_jobs=[job])
    assert queued_state["jobs"][0]["state"] == "QUEUED"
    assert queued_state["jobs"][0]["queue_key"] == {"ready_sequence": 3, "job_id": JOB_ID}

    attempt = _attempt()
    allocated = _allocated_event(queued, attempt)
    allocated_state = replay_execution_journal_prefix_v1(
        [INITIAL, event, queued, allocated], supplied_jobs=[job], supplied_attempts=[attempt]
    )
    assert allocated_state["jobs"][0]["state"] == "ACTIVE"
    assert allocated_state["attempts"][0]["state"] == "CREATED"
    assert [stream["stream"] for stream in allocated_state["log_streams"]] == [
        "STDOUT",
        "STDERR",
        "STRUCTURED",
    ]
    future_attempt = _reseal_attempt({
        **deepcopy(attempt),
        "attempt_id": "AT-TWO",
        "retry_ordinal": 2,
        "fencing_generation": 2,
        "crucible_id": "CU-TWO",
        "output_namespace_id": "ON-TWO",
        "log_stream_ids": {
            "STDOUT": "LG-FOUR",
            "STDERR": "LG-FIVE",
            "STRUCTURED": "LG-SIX",
        },
        "created_at": "2026-08-06T00:00:04Z",
    })
    assert replay_execution_journal_supplied_facts_v1(
        [INITIAL, event, queued, allocated],
        supplied_jobs=[job],
        supplied_attempts=[attempt, future_attempt],
    ) == allocated_state
    unrelated_allocation = deepcopy(allocated)
    unrelated_allocation["causation_event_id"] = event["event_id"]
    unrelated_allocation = build_execution_journal_event_v1({
        key: value for key, value in unrelated_allocation.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="queued Job projection"):
        replay_execution_journal_supplied_facts_v1(
            [INITIAL, event, queued, unrelated_allocation],
            supplied_jobs=[job],
            supplied_attempts=[attempt],
        )
    preflight = _preflight_event(allocated)
    preflight_state = replay_execution_journal_prefix_v1(
        [INITIAL, event, queued, allocated, preflight],
        supplied_jobs=[job], supplied_attempts=[attempt],
    )
    assert preflight_state["attempts"][0]["state"] == "PREFLIGHTING"
    preflight_progress = build_execution_journal_event_v1({
        "schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"],
        "event_id": "JE-PREFLIGHTPROGRESS", "sequence": 6,
        "event_type": "attempt.preflight_progressed",
        "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1,
        "executor_build_sigil": INITIAL["executor_build_sigil"],
        "recorded_at": "2026-08-06T00:00:03Z", "observed_at": None,
        "entity_revisions": [{
            "entity_kind": "ATTEMPT", "entity_id": "AT-ONE",
            "preceding_revision": 1, "next_revision": 2,
        }],
        "causation_event_id": preflight["event_id"], "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {"step": "TASK_BINDINGS_VERIFIED", "progress_evidence_sigil": SIGIL},
        "previous_event_sigil": preflight["event_sigil"],
    })
    progressed_state = replay_execution_supplied_state_suffix_v1(
        preflight_state, [preflight_progress]
    )
    assert progressed_state["attempts"][0]["revision"] == 2
    invalid_progress = deepcopy(preflight_progress)
    invalid_progress["payload"]["step"] = "NOT_A_PREFLIGHT_STEP"
    invalid_progress = build_execution_journal_event_v1({
        key: value for key, value in invalid_progress.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="Preflight progress Event disagrees"):
        replay_execution_supplied_state_suffix_v1(preflight_state, [invalid_progress])
    preflight_passed = _preflight_passed_event(preflight)
    ready_state = replay_execution_journal_prefix_v1(
        [INITIAL, event, queued, allocated, preflight, preflight_passed],
        supplied_jobs=[job], supplied_attempts=[attempt],
    )
    assert ready_state["attempts"][0]["state"] == "READY"
    assert replay_execution_journal_supplied_facts_v1(
        [INITIAL, event, queued, allocated, preflight, preflight_passed],
        supplied_jobs=[job], supplied_attempts=[attempt],
    ) == ready_state

    wrong_supplied = deepcopy(attempt)
    wrong_supplied["attempt_binding_sigil"] = SIGIL
    with pytest.raises(AthanorError, match="self-Sigil mismatch"):
        replay_execution_journal_supplied_facts_v1(
            [INITIAL, event, queued, allocated, preflight, preflight_passed],
            supplied_jobs=[job], supplied_attempts=[wrong_supplied],
        )

    required_attempt = _attempt()
    required_attempt["attempt_authorization_requirement"] = {
        "kind": "REQUIRED", "effects": [{"side_effect_id": "SE-ONE", "authority_sigil": SIGIL}],
    }
    required_attempt["attempt_binding_sigil"] = content_sigil({
        key: value for key, value in required_attempt.items() if key != "attempt_binding_sigil"
    })
    required_allocated = _allocated_event(queued, required_attempt)
    required_state = replay_execution_journal_supplied_facts_v1(
        [INITIAL, event, queued, required_allocated],
        supplied_jobs=[job], supplied_attempts=[required_attempt],
    )
    effects = required_attempt["attempt_authorization_requirement"]["effects"]
    subject: dict[str, Any] = {
        "schema_version": "attempt-authorization-subject/1.0", "authorization_subject_id": "",
        "job_id": JOB_ID, "job_binding_sigil": job["job_binding_sigil"],
        "attempt_id": required_attempt["attempt_id"],
        "attempt_binding_sigil": required_attempt["attempt_binding_sigil"],
        "retry_ordinal": 1, "specification_id": job["specification_id"],
        "specification_sigil": job["specification_sigil"], "effects": effects,
        "authorization_subject_sigil": "",
    }
    subject["authorization_subject_id"] = "AA-" + hashlib.sha256(canonical_json([
        "attempt-authorization-subject-id/1.0", subject["job_id"], subject["job_binding_sigil"],
        subject["attempt_id"], subject["attempt_binding_sigil"], subject["retry_ordinal"],
        subject["specification_id"], subject["specification_sigil"], subject["effects"],
    ]).encode()).hexdigest().upper()
    subject["authorization_subject_sigil"] = content_sigil({
        key: value for key, value in subject.items() if key != "authorization_subject_sigil"
    })
    binding = {
        "authorization_subject_id": subject["authorization_subject_id"],
        "authorization_subject_sigil": subject["authorization_subject_sigil"],
        "authorization_transition_request_id": "AAT-" + "A" * 64,
        "authorization_transition_request_sigil": SIGIL,
        "authorization_event_id": "AUTH-EVENT", "authorization_event_body_sigil": SIGIL,
        "authorization_receipt_id": "RC-ONE", "authorization_receipt_sigil": SIGIL,
    }
    binding["authorization_binding_sigil"] = content_sigil(binding)
    bound = build_execution_journal_event_v1({
        "schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"],
        "event_id": "JE-AUTH", "sequence": 5, "event_type": "attempt.authorization_bound",
        "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1,
        "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:03Z",
        "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 0, "next_revision": 1}],
        "causation_event_id": required_allocated["event_id"], "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {"authorization_subject": subject, "attempt_authorization_binding": binding},
        "previous_event_sigil": required_allocated["event_sigil"],
    })
    bound_state = replay_execution_supplied_state_suffix_v1(
        required_state, [bound], supplied_jobs=[job], supplied_attempts=[required_attempt],
    )
    assert bound_state["attempts"][0]["attempt_authorization_state"]["kind"] == "BOUND"
    assert replay_execution_journal_supplied_facts_v1(
        [INITIAL, event, queued, required_allocated, bound],
        supplied_jobs=[job], supplied_attempts=[required_attempt],
    ) == bound_state

    wrong_binding = deepcopy(bound)
    wrong_binding["payload"]["authorization_subject"]["specification_id"] = "ES-TWO"
    wrong_binding = build_execution_journal_event_v1({
        key: value for key, value in wrong_binding.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="Subject identity"):
        replay_execution_supplied_state_suffix_v1(
            required_state, [wrong_binding], supplied_jobs=[job], supplied_attempts=[required_attempt],
        )

    duplicate_effect = deepcopy(bound)
    duplicate_subject = duplicate_effect["payload"]["authorization_subject"]
    duplicate_subject["effects"] = [
        *effects,
        {"side_effect_id": "SE-ONE", "authority_sigil": "sha256:" + "b" * 64},
    ]
    duplicate_subject["authorization_subject_id"] = "AA-" + hashlib.sha256(
        canonical_json([
            "attempt-authorization-subject-id/1.0", duplicate_subject["job_id"],
            duplicate_subject["job_binding_sigil"], duplicate_subject["attempt_id"],
            duplicate_subject["attempt_binding_sigil"], duplicate_subject["retry_ordinal"],
            duplicate_subject["specification_id"], duplicate_subject["specification_sigil"],
            duplicate_subject["effects"],
        ]).encode()
    ).hexdigest().upper()
    duplicate_subject["authorization_subject_sigil"] = content_sigil({
        key: value for key, value in duplicate_subject.items()
        if key != "authorization_subject_sigil"
    })
    duplicate_binding = duplicate_effect["payload"]["attempt_authorization_binding"]
    duplicate_binding["authorization_subject_id"] = duplicate_subject["authorization_subject_id"]
    duplicate_binding["authorization_subject_sigil"] = duplicate_subject["authorization_subject_sigil"]
    duplicate_binding["authorization_binding_sigil"] = content_sigil({
        key: value for key, value in duplicate_binding.items()
        if key != "authorization_binding_sigil"
    })
    duplicate_effect = build_execution_journal_event_v1({
        key: value for key, value in duplicate_effect.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="effects are not uniquely sorted"):
        replay_execution_supplied_state_suffix_v1(
            required_state, [duplicate_effect], supplied_jobs=[job], supplied_attempts=[required_attempt],
        )

    rejected_cancel = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-JOBREJECT", "sequence": 7, "event_type": "job.message_rejected", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:05Z", "observed_at": None, "entity_revisions": [{"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 2, "next_revision": 3}], "causation_event_id": allocated["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"message_kind": "CANCEL_REQUEST", "message_sigil": SIGIL, "reason_codes": ["CONTROL_CHANNEL_LOST"], "historical_disposition_event_id": None}, "previous_event_sigil": preflight_passed["event_sigil"]})
    rejected_cancel_state = replay_execution_supplied_state_suffix_v1(ready_state, [rejected_cancel])
    assert rejected_cancel_state["jobs"][0]["state"] == "ACTIVE"
    assert rejected_cancel_state["jobs"][0]["revision"] == 3

    wrong_cancel = deepcopy(rejected_cancel)
    wrong_cancel["payload"]["message_kind"] = "LEASE_RELEASE"
    wrong_cancel = build_execution_journal_event_v1({key: value for key, value in wrong_cancel.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(ready_state, [wrong_cancel])

    combined = deepcopy(ready_state)
    session_id = "WS-00000000000000000000000000"
    combined["workers"] = [{"worker_id": "WK-ONE", "revision": 1, "state": "ENABLED", "worker_binding_sigil": SIGIL, "definition_revision": 0, "worker_session_ids": [session_id], "last_event_id": "JE-SIX", "last_event_sigil": preflight_passed["event_sigil"]}]
    combined["worker_sessions"] = [{"worker_session_id": session_id, "revision": 1, "state": "READY", "worker_id": "WK-ONE", "worker_binding_sigil": SIGIL, "worker_session_binding_sigil": SIGIL, "executor_epoch": 1, "worker_session_heartbeat_policy_id": "WSHP-" + "A" * 64, "worker_session_heartbeat_policy_sigil": SIGIL, "capacity": 1, "capacity_in_use": 0, "last_heartbeat_sequence": None, "last_heartbeat_message_sigil": None, "last_resource_sample_sigil": None, "resource_counter_floors": {"cpu_time_seconds": None, "storage_bytes_written": None, "network_egress_bytes": None}, "next_heartbeat_due_at": "2026-08-06T00:00:30Z", "lease_ids": [], "last_event_id": "JE-SIX", "last_event_sigil": preflight_passed["event_sigil"]}]
    combined["deadlines"].append({"deadline_kind": "HEARTBEAT_TIMEOUT", "due_at": "2026-08-06T00:00:30Z", "fixed_priority": 30, "entity_id": session_id, "source_event_id": "JE-SIX", "source_event_sigil": preflight_passed["event_sigil"]})
    combined["deadlines"].sort(key=lambda item: (item["due_at"], item["fixed_priority"], item["entity_id"]))
    combined["state_sigil"] = content_sigil({key: value for key, value in combined.items() if key != "state_sigil"})
    session_heartbeat = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-SESSIONHEARTBEAT", "sequence": 7, "event_type": "worker_session.heartbeat_accepted", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:05Z", "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 1, "next_revision": 2}], "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"heartbeat_message_sigil": SIGIL, "sequence": 0, "prior_accepted_sequence": None, "received_at": "2026-08-06T00:00:05Z", "next_heartbeat_due_at": "2026-08-06T00:00:06Z", "worker_session_heartbeat_policy_id": "WSHP-" + "A" * 64, "worker_session_heartbeat_policy_sigil": SIGIL, "resource_sample_sigil": SIGIL, "resource_counter_floors_after": {"cpu_time_seconds": 0, "storage_bytes_written": 0, "network_egress_bytes": 0}}, "previous_event_sigil": preflight_passed["event_sigil"]})
    session_heartbeat_state = replay_execution_supplied_state_suffix_v1(combined, [session_heartbeat])
    assert session_heartbeat_state["worker_sessions"][0]["last_heartbeat_sequence"] == 0
    assert session_heartbeat_state["worker_sessions"][0]["next_heartbeat_due_at"] == "2026-08-06T00:00:06Z"

    wrong_session_heartbeat = deepcopy(session_heartbeat)
    wrong_session_heartbeat["payload"]["sequence"] = 1
    wrong_session_heartbeat = build_execution_journal_event_v1({key: value for key, value in wrong_session_heartbeat.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(combined, [wrong_session_heartbeat])

    rejected_session_message = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-SESSIONREJECT", "sequence": 7, "event_type": "worker_session.message_rejected", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:05Z", "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 1, "next_revision": 2}], "causation_event_id": "JE-SIX", "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"message_kind": "WORKER_SESSION_HEARTBEAT", "message_sigil": SIGIL, "identity_binding": {"kind": "NONE"}, "reason_codes": ["CONTROL_CHANNEL_LOST"], "historical_disposition_event_id": None}, "previous_event_sigil": preflight_passed["event_sigil"]})
    rejected_session_state = replay_execution_supplied_state_suffix_v1(combined, [rejected_session_message])
    assert rejected_session_state["worker_sessions"][0]["state"] == "READY"
    assert rejected_session_state["worker_sessions"][0]["revision"] == 2

    wrong_session_message = deepcopy(rejected_session_message)
    wrong_session_message["payload"]["message_kind"] = "LEASE_HEARTBEAT"
    wrong_session_message = build_execution_journal_event_v1({key: value for key, value in wrong_session_message.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(combined, [wrong_session_message])

    worker_draining = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-WORKERDRAIN", "sequence": 7, "event_type": "worker.draining", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:05Z", "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER", "entity_id": "WK-ONE", "preceding_revision": 1, "next_revision": 2}], "causation_event_id": "JE-SIX", "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"reason_code": "ADMIN_DRAIN", "affected_worker_session_ids": [session_id]}, "previous_event_sigil": preflight_passed["event_sigil"]})
    worker_draining_state = replay_execution_supplied_state_suffix_v1(combined, [worker_draining])
    assert worker_draining_state["workers"][0]["state"] == "DRAINING"

    worker_quarantined = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-WORKERQUAR", "sequence": 8, "event_type": "worker.quarantined", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:05Z", "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER", "entity_id": "WK-ONE", "preceding_revision": 2, "next_revision": 3}], "causation_event_id": worker_draining["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"reason_codes": ["VERIFICATION_FAILED"], "evidence_set_sigil": SIGIL, "affected_worker_session_ids": [session_id]}, "previous_event_sigil": worker_draining["event_sigil"]})
    worker_quarantined_state = replay_execution_supplied_state_suffix_v1(worker_draining_state, [worker_quarantined])
    assert worker_quarantined_state["workers"][0]["state"] == "QUARANTINED"

    wrong_worker_drain = deepcopy(worker_draining)
    wrong_worker_drain["payload"]["affected_worker_session_ids"] = []
    wrong_worker_drain = build_execution_journal_event_v1({key: value for key, value in wrong_worker_drain.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(combined, [wrong_worker_drain])

    retired_input = deepcopy(worker_quarantined_state)
    retired_input["worker_sessions"][0].update({"revision": 2, "state": "CLOSED", "capacity_in_use": 0, "next_heartbeat_due_at": None, "last_event_id": worker_quarantined["event_id"], "last_event_sigil": worker_quarantined["event_sigil"]})
    retired_input["state_sigil"] = content_sigil({key: value for key, value in retired_input.items() if key != "state_sigil"})
    worker_retired = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-WORKERRETIRED", "sequence": 9, "event_type": "worker.retired", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:05Z", "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER", "entity_id": "WK-ONE", "preceding_revision": 3, "next_revision": 4}], "causation_event_id": worker_quarantined["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"reason_code": "ADMIN_RETIRE", "closed_worker_session_ids": [session_id]}, "previous_event_sigil": worker_quarantined["event_sigil"]})
    worker_retired_state = replay_execution_supplied_state_suffix_v1(retired_input, [worker_retired])
    assert worker_retired_state["workers"][0]["state"] == "RETIRED"

    wrong_worker_retired = deepcopy(worker_retired)
    wrong_worker_retired["payload"]["closed_worker_session_ids"] = []
    wrong_worker_retired = build_execution_journal_event_v1({key: value for key, value in wrong_worker_retired.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(retired_input, [wrong_worker_retired])

    session_draining = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-SESSIONDRAIN", "sequence": 7, "event_type": "worker_session.draining", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:05Z", "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 1, "next_revision": 2}], "causation_event_id": "JE-SIX", "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"reason_code": "ADMIN_DRAIN", "active_lease_ids": []}, "previous_event_sigil": preflight_passed["event_sigil"]})
    session_draining_state = replay_execution_supplied_state_suffix_v1(combined, [session_draining])
    assert session_draining_state["worker_sessions"][0]["state"] == "DRAINING"

    session_offline = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-SESSIONOFFLINE", "sequence": 8, "event_type": "worker_session.offline", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:05Z", "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 2, "next_revision": 3}], "causation_event_id": session_draining["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"transition_cause": {"code": "SESSION_CHANNEL_LOST", "trigger_kind": "PRIOR_EVENT", "trigger_event_id": session_draining["event_id"], "effective_sequence": session_draining["sequence"], "evidence_sigil": SIGIL}, "last_heartbeat_sequence": None, "active_lease_ids": []}, "previous_event_sigil": session_draining["event_sigil"]})
    session_offline_state = replay_execution_supplied_state_suffix_v1(session_draining_state, [session_offline])
    assert session_offline_state["worker_sessions"][0]["next_heartbeat_due_at"] is None

    wrong_session_offline = deepcopy(session_offline)
    wrong_session_offline["payload"]["active_lease_ids"] = ["LS-ONE"]
    wrong_session_offline = build_execution_journal_event_v1({key: value for key, value in wrong_session_offline.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(session_draining_state, [wrong_session_offline])

    lease: dict[str, Any] = {"schema_version": "execution-lease/1.0", "lease_id": "LS-00000000000000000000000000", "job_id": JOB_ID, "attempt_id": "AT-ONE", "worker_id": "WK-ONE", "worker_binding_sigil": SIGIL, "worker_session_id": session_id, "worker_session_binding_sigil": SIGIL, "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "fencing_generation": 1, "offered_at": "2026-08-06T00:00:05Z", "claim_due_at": "2026-08-06T00:00:06Z", "initial_expiry_due_at": "2026-08-06T00:00:07Z", "maximum_expiry_due_at": "2026-08-06T00:00:08Z", "heartbeat_policy": {"heartbeat_interval_seconds": 1, "heartbeat_timeout_seconds": 1}, "lease_credential_digest": SIGIL, "lease_binding_sigil": ""}
    lease["lease_binding_sigil"] = content_sigil({key: value for key, value in lease.items() if key != "lease_binding_sigil"})
    offered = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-SEVEN", "sequence": 7, "event_type": "lease.offered", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": lease["offered_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 1, "next_revision": 2}, {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 2, "next_revision": 3}, {"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": None, "next_revision": 0}], "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"lease_binding_sigil": lease["lease_binding_sigil"], "credential_digest": SIGIL, "claim_due_at": lease["claim_due_at"], "initial_expiry_due_at": lease["initial_expiry_due_at"], "maximum_expiry_due_at": lease["maximum_expiry_due_at"]}, "previous_event_sigil": preflight_passed["event_sigil"]})
    offered_state = replay_execution_supplied_state_suffix_v1(combined, [offered], supplied_leases=[lease])
    assert offered_state["leases"][0]["state"] == "OFFERED"
    assert offered_state["attempts"][0]["lease_id"] == lease["lease_id"]

    claim_expired = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-CLAIMEXPIRED", "sequence": 8, "event_type": "lease.expired", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": lease["claim_due_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 2, "next_revision": 3}, {"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 2, "next_revision": 3}, {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 3, "next_revision": 4}, {"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": 0, "next_revision": 1}], "causation_event_id": offered["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"deadline_kind": "LEASE_CLAIM_DEADLINE", "due_at": lease["claim_due_at"], "prior_fence_floor": 1, "tombstone_generation": 2, "tombstone_publication_sigil": SIGIL, "session_capacity_after": 0}, "previous_event_sigil": offered["event_sigil"]})
    claim_expired_state = replay_execution_supplied_state_suffix_v1(offered_state, [claim_expired])
    assert claim_expired_state["leases"][0]["state"] == "EXPIRED"
    assert claim_expired_state["attempts"][0]["state"] == "READY"
    assert claim_expired_state["worker_sessions"][0]["next_heartbeat_due_at"] == "2026-08-06T00:00:30Z"

    claim_stop = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-CLAIMSTOP", "sequence": 9, "event_type": "attempt.stop_latched", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": lease["claim_due_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 3, "next_revision": 3}, {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 4, "next_revision": 5}], "causation_event_id": claim_expired["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"transition_cause": {"code": "LEASE_CLAIM_EXPIRED", "trigger_kind": "PRIOR_EVENT", "trigger_event_id": claim_expired["event_id"], "effective_sequence": claim_expired["sequence"], "evidence_sigil": SIGIL}, "grace_due_at": "2026-08-06T00:00:07Z"}, "previous_event_sigil": claim_expired["event_sigil"]})
    claim_stopped_state = replay_execution_supplied_state_suffix_v1(claim_expired_state, [claim_stop])
    assert claim_stopped_state["attempts"][0]["state"] == "STOPPING"
    assert claim_stopped_state["attempts"][0]["first_stop_or_fence_binding"]["event_id"] == claim_expired["event_id"]

    claimed = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-EIGHT", "sequence": 8, "event_type": "lease.claimed", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:06Z", "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 2, "next_revision": 3}, {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 3, "next_revision": 4}, {"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": 0, "next_revision": 1}], "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"credential_proof_sigil": SIGIL, "claimed_at": "2026-08-06T00:00:06Z", "next_heartbeat_due_at": "2026-08-06T00:00:09Z", "session_capacity_after": 1}, "previous_event_sigil": offered["event_sigil"]})
    claimed_state = replay_execution_supplied_state_suffix_v1(offered_state, [claimed])
    assert claimed_state["leases"][0]["state"] == "ACTIVE"
    assert claimed_state["attempts"][0]["state"] == "LEASED"
    assert claimed_state["worker_sessions"][0]["capacity_in_use"] == 1

    fenced = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-FENCED", "sequence": 9, "event_type": "lease.fenced", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:07Z", "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 3, "next_revision": 4}, {"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 2, "next_revision": 3}, {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 4, "next_revision": 5}, {"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": 1, "next_revision": 2}], "causation_event_id": claimed["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"transition_cause": {"code": "RECOVERY_FENCE", "trigger_kind": "PRIOR_EVENT", "trigger_event_id": claimed["event_id"], "effective_sequence": claimed["sequence"], "evidence_sigil": SIGIL}, "prior_fence_floor": 1, "tombstone_generation": 2, "tombstone_publication_sigil": SIGIL, "session_capacity_after": 0}, "previous_event_sigil": claimed["event_sigil"]})
    fenced_state = replay_execution_supplied_state_suffix_v1(claimed_state, [fenced])
    assert fenced_state["leases"][0]["state"] == "FENCED"
    assert fenced_state["attempts"][0]["lease_terminal_binding"]["lease_state"] == "FENCED"
    assert fenced_state["worker_sessions"][0]["capacity_in_use"] == 0

    wrong_fence = deepcopy(fenced)
    wrong_fence["payload"]["transition_cause"]["code"] = "CANCEL_REQUESTED"
    wrong_fence = build_execution_journal_event_v1({
        key: value for key, value in wrong_fence.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="Lease fencing Event disagrees"):
        replay_execution_supplied_state_suffix_v1(claimed_state, [wrong_fence])

    nonadvancing_fence = deepcopy(claimed_state)
    nonadvancing_fence["jobs"][0]["fence_floor"] = 2
    nonadvancing_fence["state_sigil"] = content_sigil(
        {key: value for key, value in nonadvancing_fence.items() if key != "state_sigil"}
    )
    with pytest.raises(AthanorError, match="Lease fencing Event disagrees"):
        replay_execution_supplied_state_suffix_v1(nonadvancing_fence, [fenced])

    revocation_input = deepcopy(claimed_state)
    first_stop = {"kind": "PRESENT", "event_id": claimed["event_id"], "event_type": "lease.claimed", "event_sigil": claimed["event_sigil"], "effective_sequence": claimed["sequence"]}
    revocation_input["jobs"][0].update({"revision": 3, "state": "STOPPING", "first_stop_or_fence_binding": first_stop, "last_event_id": "JE-STOPLATCHED", "last_event_sigil": SIGIL})
    revocation_input["attempts"][0].update({"revision": 5, "state": "STOPPING", "first_stop_or_fence_binding": first_stop, "grace_due_at": "2026-08-06T00:00:08Z", "last_event_id": "JE-STOPLATCHED", "last_event_sigil": SIGIL})
    revocation_input["state_sigil"] = content_sigil({key: value for key, value in revocation_input.items() if key != "state_sigil"})
    revoked = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-REVOKED", "sequence": 9, "event_type": "lease.revoked", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:07Z", "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 3, "next_revision": 4}, {"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 3, "next_revision": 4}, {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 5, "next_revision": 6}, {"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": 1, "next_revision": 2}], "causation_event_id": "JE-STOPLATCHED", "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"transition_cause": {"code": "CANCEL_REQUESTED", "trigger_kind": "PRIOR_EVENT", "trigger_event_id": claimed["event_id"], "effective_sequence": claimed["sequence"], "evidence_sigil": SIGIL}, "prior_fence_floor": 1, "tombstone_generation": 2, "tombstone_publication_sigil": SIGIL, "session_capacity_after": 0}, "previous_event_sigil": claimed["event_sigil"]})
    revoked_state = replay_execution_supplied_state_suffix_v1(revocation_input, [revoked])
    assert revoked_state["leases"][0]["state"] == "REVOKED"
    assert revoked_state["attempts"][0]["lease_terminal_binding"]["lease_state"] == "REVOKED"
    assert revoked_state["worker_sessions"][0]["capacity_in_use"] == 0

    republished = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-REPUBLISHED", "sequence": 10, "event_type": "lease.tombstone_republished", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:07Z", "observed_at": None, "entity_revisions": [{"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": 2, "next_revision": 3}], "causation_event_id": revoked["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"tombstone_generation": 2, "original_terminal_event_sigil": revoked["event_sigil"], "sink_ids": ["SINK"], "publication_evidence_sigil": SIGIL}, "previous_event_sigil": revoked["event_sigil"]})
    republished_state = replay_execution_supplied_state_suffix_v1(revoked_state, [republished])
    assert republished_state["leases"][0]["revision"] == 3
    assert republished_state["leases"][0]["state"] == "REVOKED"

    rejected_lease_message = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-LEASEREJECT", "sequence": 11, "event_type": "lease.message_rejected", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:07Z", "observed_at": None, "entity_revisions": [{"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": 3, "next_revision": 4}], "causation_event_id": republished["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"message_kind": "LEASE_HEARTBEAT", "message_sigil": SIGIL, "identity_binding": {"kind": "NONE"}, "reason_codes": ["LEASE_TERMINAL"], "historical_disposition_event_id": None}, "previous_event_sigil": republished["event_sigil"]})
    lease_message_state = replay_execution_supplied_state_suffix_v1(republished_state, [rejected_lease_message])
    assert lease_message_state["leases"][0]["state"] == "REVOKED"
    assert lease_message_state["leases"][0]["revision"] == 4

    wrong_lease_message = deepcopy(rejected_lease_message)
    wrong_lease_message["payload"]["message_kind"] = "CANCEL_REQUEST"
    wrong_lease_message = build_execution_journal_event_v1({key: value for key, value in wrong_lease_message.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(republished_state, [wrong_lease_message])

    wrong_republish = deepcopy(republished)
    wrong_republish["payload"]["tombstone_generation"] = 3
    wrong_republish = build_execution_journal_event_v1({key: value for key, value in wrong_republish.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(revoked_state, [wrong_republish])

    unlatched = deepcopy(claimed_state)
    unlatched["state_sigil"] = content_sigil({key: value for key, value in unlatched.items() if key != "state_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(unlatched, [revoked])

    expired = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-EXPIRED", "sequence": 9, "event_type": "lease.expired", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": lease["initial_expiry_due_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 3, "next_revision": 4}, {"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 2, "next_revision": 3}, {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 4, "next_revision": 5}, {"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": 1, "next_revision": 2}], "causation_event_id": claimed["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"deadline_kind": "LEASE_EXPIRY", "due_at": lease["initial_expiry_due_at"], "prior_fence_floor": 1, "tombstone_generation": 2, "tombstone_publication_sigil": SIGIL, "session_capacity_after": 0}, "previous_event_sigil": claimed["event_sigil"]})
    expired_state = replay_execution_supplied_state_suffix_v1(claimed_state, [expired])
    assert expired_state["leases"][0]["state"] == "EXPIRED"
    assert expired_state["attempts"][0]["state"] == "LEASED"
    assert expired_state["attempts"][0]["lease_terminal_binding"]["lease_state"] == "EXPIRED"
    assert expired_state["jobs"][0]["fence_floor"] == 2
    assert expired_state["worker_sessions"][0]["capacity_in_use"] == 0

    stop = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-STOP", "sequence": 10, "event_type": "attempt.stop_latched", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:07Z", "observed_at": None, "entity_revisions": [{"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 3, "next_revision": 3}, {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 5, "next_revision": 6}], "causation_event_id": expired["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"transition_cause": {"code": "LEASE_ACTIVE_EXPIRED", "trigger_kind": "PRIOR_EVENT", "trigger_event_id": expired["event_id"], "effective_sequence": expired["sequence"], "evidence_sigil": SIGIL}, "grace_due_at": "2026-08-06T00:00:08Z"}, "previous_event_sigil": expired["event_sigil"]})
    stopped_state = replay_execution_supplied_state_suffix_v1(expired_state, [stop])
    assert stopped_state["attempts"][0]["state"] == "STOPPING"
    assert stopped_state["jobs"][0]["state"] == "ACTIVE"
    assert stopped_state["jobs"][0]["revision"] == expired_state["jobs"][0]["revision"]
    assert stopped_state["attempts"][0]["first_stop_or_fence_binding"]["event_type"] == "lease.expired"
    assert any(item["deadline_kind"] == "CANCELLATION_GRACE" for item in stopped_state["deadlines"])

    wrong_stop = deepcopy(stop)
    wrong_stop["payload"]["transition_cause"]["code"] = "CANCEL_REQUESTED"
    wrong_stop = build_execution_journal_event_v1({key: value for key, value in wrong_stop.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(expired_state, [wrong_stop])

    stop_progress = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-STOPPROGRESS", "sequence": 11, "event_type": "attempt.stop_progressed", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:07Z", "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 6, "next_revision": 7}], "causation_event_id": stop["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"step": "PROCESS_TREE_TERMINATED", "termination_evidence_sigil": SIGIL, "remaining_handle_ids": []}, "previous_event_sigil": stop["event_sigil"]})
    progressed_state = replay_execution_supplied_state_suffix_v1(stopped_state, [stop_progress])
    assert progressed_state["attempts"][0]["state"] == "STOPPING"

    stopping_cleaning = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-STOPCLEAN", "sequence": 12, "event_type": "attempt.cleaning", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:07Z", "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 7, "next_revision": 8}], "causation_event_id": stop_progress["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"log_closure_sigil": SIGIL, "output_closure_sigil": SIGIL, "termination_evidence_sigil": SIGIL, "quarantine_plan_sigil": SIGIL, "terminal_source_binding": {"kind": "NOT_APPLICABLE"}}, "previous_event_sigil": stop_progress["event_sigil"]})
    stopping_clean_state = replay_execution_supplied_state_suffix_v1(progressed_state, [stopping_cleaning])
    assert stopping_clean_state["attempts"][0]["state"] == "CLEANING"

    wrong_expiry = deepcopy(expired)
    wrong_expiry["payload"]["due_at"] = "2026-08-06T00:00:08Z"
    wrong_expiry = build_execution_journal_event_v1({key: value for key, value in wrong_expiry.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(claimed_state, [wrong_expiry])

    starting = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-NINE", "sequence": 9, "event_type": "attempt.starting", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:07Z", "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 4, "next_revision": 5}], "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"backend_start_handle_sigil": SIGIL, "start_request_sigil": SIGIL}, "previous_event_sigil": claimed["event_sigil"]})
    running = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-TEN", "sequence": 10, "event_type": "attempt.running", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:08Z", "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 5, "next_revision": 6}], "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"process_tree_identity": "PROCESS", "process_tree_evidence_sigil": SIGIL, "side_effect_handle_set_sigil": SIGIL}, "previous_event_sigil": starting["event_sigil"]})
    running_state = replay_execution_supplied_state_suffix_v1(claimed_state, [starting, running])
    assert running_state["attempts"][0]["state"] == "RUNNING"

    stdout_stream = next(stream for stream in running_state["log_streams"] if stream["stream"] == "STDOUT")
    chunk = {"schema_version": "execution-log-chunk/1.0", "chunk_id": "LC-ONE", "log_stream_id": stdout_stream["log_stream_id"], "job_id": JOB_ID, "attempt_id": "AT-ONE", "lease_id": lease["lease_id"], "worker_id": "WK-ONE", "worker_session_id": session_id, "executor_epoch": 1, "attempt_binding_sigil": attempt["attempt_binding_sigil"], "lease_binding_sigil": lease["lease_binding_sigil"], "worker_session_binding_sigil": SIGIL, "fence_tuple": running_state["attempts"][0]["public_fence_tuple"], "stream": "STDOUT", "sequence": 0, "byte_length": 1, "media_type": "application/octet-stream", "encoding": "BINARY", "blob_sigil": SIGIL, "staging_reference": {"kind": "EXECUTION_LOG_SPOOL_RECORD", "staging_record_id": "LSR-" + "A" * 64, "staging_record_sigil": SIGIL}, "observed_at": "2026-08-06T00:00:08Z", "received_at": "2026-08-06T00:00:08Z", "split_utf8_boundary": False, "split_line": False, "chunk_record_sigil": SIGIL}
    chunk_committed = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-LOGCOMMIT", "sequence": 11, "event_type": "log.chunk_committed", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:08Z", "observed_at": None, "entity_revisions": [{"entity_kind": "LOG_STREAM", "entity_id": stdout_stream["log_stream_id"], "preceding_revision": 0, "next_revision": 1}], "causation_event_id": None, "idempotency_key_sigil": SIGIL, "recovery_action_binding": None, "payload": {"intake_kind": "RAW_CHUNK", "intake_id": "LCI-ONE", "intake_record_sigil": SIGIL, "disposition_intent_id": "LDI-ONE", "log_stream_id": stdout_stream["log_stream_id"], "chunk_record_sigil": SIGIL, "stream": "STDOUT", "sequence": 0, "blob_sigil": SIGIL, "captured_bytes_after": 1}, "previous_event_sigil": running["event_sigil"]})
    chunked_state = replay_execution_supplied_state_suffix_v1(running_state, [chunk_committed], supplied_log_chunks=[chunk])
    assert next(stream for stream in chunked_state["log_streams"] if stream["stream"] == "STDOUT")["captured_bytes"] == 1

    wrong_chunk = deepcopy(chunk)
    wrong_chunk["sequence"] = 1
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(running_state, [chunk_committed], supplied_log_chunks=[wrong_chunk])

    duplicate_chunk = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-LOGDUP", "sequence": 12, "event_type": "log.chunk_duplicate_observed", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:08Z", "observed_at": None, "entity_revisions": [{"entity_kind": "LOG_STREAM", "entity_id": stdout_stream["log_stream_id"], "preceding_revision": 1, "next_revision": 2}], "causation_event_id": None, "idempotency_key_sigil": SIGIL, "recovery_action_binding": None, "payload": {"intake_kind": "RAW_CHUNK", "intake_id": "LCI-TWO", "intake_record_sigil": SIGIL, "disposition_intent_id": "LDI-TWO", "log_stream_id": stdout_stream["log_stream_id"], "stream": "STDOUT", "sequence": 0, "original_chunk_id": chunk["chunk_id"], "original_chunk_record_sigil": SIGIL, "original_disposition_event": {"event_id": chunk_committed["event_id"], "event_sigil": chunk_committed["event_sigil"]}}, "previous_event_sigil": chunk_committed["event_sigil"]})
    duplicate_chunk_state = replay_execution_supplied_state_suffix_v1(chunked_state, [duplicate_chunk])
    duplicate_stream = next(stream for stream in duplicate_chunk_state["log_streams"] if stream["stream"] == "STDOUT")
    assert (duplicate_stream["next_sequence"], duplicate_stream["captured_bytes"]) == (1, 1)

    wrong_duplicate = deepcopy(duplicate_chunk)
    wrong_duplicate["payload"]["sequence"] = 1
    wrong_duplicate = build_execution_journal_event_v1({key: value for key, value in wrong_duplicate.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(chunked_state, [wrong_duplicate])

    heartbeat = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-HEARTBEAT", "sequence": 11, "event_type": "lease.heartbeat_accepted", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:08Z", "observed_at": None, "entity_revisions": [{"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": 1, "next_revision": 2}], "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"heartbeat_message_sigil": SIGIL, "sequence": 1, "prior_accepted_sequence": None, "received_at": "2026-08-06T00:00:06Z", "next_heartbeat_due_at": "2026-08-06T00:00:09Z", "resource_sample_sigil": SIGIL, "resource_counter_floors_after": {"cpu_time_seconds": 0, "storage_bytes_written": 0, "network_egress_bytes": 0}}, "previous_event_sigil": running["event_sigil"]})
    heartbeat_state = replay_execution_supplied_state_suffix_v1(running_state, [heartbeat])
    assert heartbeat_state["leases"][0]["last_heartbeat_sequence"] == 1
    renewal = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-RENEWAL", "sequence": 12, "event_type": "lease.renewed", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": "2026-08-06T00:00:08Z", "observed_at": None, "entity_revisions": [{"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": 2, "next_revision": 3}], "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"renewal_request_sigil": SIGIL, "prior_expiry_due_at": lease["initial_expiry_due_at"], "new_expiry_due_at": lease["maximum_expiry_due_at"], "renewal_counter": 1}, "previous_event_sigil": heartbeat["event_sigil"]})
    renewed_state = replay_execution_supplied_state_suffix_v1(heartbeat_state, [renewal])
    assert renewed_state["leases"][0]["renewal_counter"] == 1

    owner = {
        "job_id": JOB_ID, "job_binding_sigil": job["job_binding_sigil"], "attempt_id": "AT-ONE",
        "attempt_binding_sigil": attempt["attempt_binding_sigil"], "lease_id": lease["lease_id"],
        "lease_binding_sigil": lease["lease_binding_sigil"], "worker_id": "WK-ONE",
        "worker_binding_sigil": SIGIL, "worker_session_id": session_id,
        "worker_session_binding_sigil": SIGIL, "executor_epoch": 1,
        "fence_tuple": running_state["attempts"][0]["public_fence_tuple"],
    }
    observation = {
        "runtime_observation": {"started_at": "2026-08-06T00:00:07Z", "ended_at": "2026-08-06T00:00:08Z", "cpu_time_seconds": 0, "peak_memory_bytes": 0, "process_count": 0},
        "termination_observation": {"kind": "EXITED", "exit_code": 0, "observed_at": "2026-08-06T00:00:08Z", "observation_source": "WORKER"},
        "observation_evidence_subject_sigil": "",
    }
    observation["observation_evidence_subject_sigil"] = derive_observation_evidence_subject_sigil_v1(owner, observation)
    receipt: dict[str, Any] = {
        "schema_version": "execution-result-ingress-receipt/1.0", "ingress_receipt_id": "", "owner_binding": owner,
        "result_sigil": SIGIL, "result_observation_binding": observation, "received_at": "2026-08-06T00:00:08Z",
        "control_channel_identity_sigil": SIGIL,
        "credential_verification": {"kind": "VERIFIED", "lease_credential_digest": SIGIL, "verification_profile_sigil": SIGIL, "verified_at": "2026-08-06T00:00:08Z", "verification_sigil": ""},
        "receiver_identity": {"executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "implementation_sigil": SIGIL},
        "created_at": "2026-08-06T00:00:08Z", "ingress_receipt_sigil": "",
    }
    receipt["ingress_receipt_id"] = derive_result_ingress_receipt_id_v1(receipt)
    verification = receipt["credential_verification"]
    verification["verification_sigil"] = content_sigil(["execution-result-ingress-credential-verification/1.0", owner, SIGIL, receipt["received_at"], SIGIL, SIGIL, SIGIL, verification["verified_at"]])
    receipt["ingress_receipt_sigil"] = content_sigil({key: value for key, value in receipt.items() if key != "ingress_receipt_sigil"})
    ingress = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-ELEVEN", "sequence": 11, "event_type": "attempt.result_ingress_received", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": receipt["received_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 6, "next_revision": 7}], "causation_event_id": running["event_id"], "idempotency_key_sigil": content_sigil(["execution-result-ingress-key/1.0", "AT-ONE", SIGIL]), "recovery_action_binding": None, "payload": {"ingress_receipt_id": receipt["ingress_receipt_id"], "ingress_receipt_sigil": receipt["ingress_receipt_sigil"], "result_sigil": SIGIL, "observation_evidence_subject_sigil": observation["observation_evidence_subject_sigil"], "received_at": receipt["received_at"]}, "previous_event_sigil": running["event_sigil"]})
    intent: dict[str, Any] = {"schema_version": "execution-result-ingress-event-intent/1.0", "ingress_event_intent_id": "OII-" + "A" * 64, "result_ingress_receipt_binding": {"ingress_receipt_id": receipt["ingress_receipt_id"], "ingress_receipt_sigil": receipt["ingress_receipt_sigil"]}, "event_candidate": ingress, "created_at": receipt["received_at"], "intent_sigil": ""}
    intent["intent_sigil"] = content_sigil({key: value for key, value in intent.items() if key != "intent_sigil"})
    ingress_state = replay_execution_supplied_state_suffix_v1(running_state, [ingress], supplied_result_ingress_receipts=[receipt], supplied_result_ingress_intents=[intent])
    assert ingress_state["attempts"][0]["result_intake"]["kind"] == "RECEIVED"

    source = {"source_kind": "WORKER", "source_identity_id": "SOURCE", "source_identity_sigil": SIGIL, "source_identity_profile_sigil": SIGIL, "source_channel_sigil": SIGIL, "source_channel_profile_sigil": SIGIL, "source_registry_id": "REGISTRY", "source_registry_version": "1.0", "source_registry_snapshot_sigil": SIGIL}
    evidence: dict[str, Any] = {"schema_version": "execution-observation-evidence/1.0", "observation_evidence_id": "", **owner, "result_observation_binding": observation, "result_ingress_receipt_binding": intent["result_ingress_receipt_binding"], "producer_evidence_binding": {"raw_evidence_id": "ORE-" + "A" * 64, "raw_evidence_record_sigil": SIGIL}, "verifier_evidence_binding": {"raw_evidence_id": "ORE-" + "B" * 64, "raw_evidence_record_sigil": SIGIL}, "evidence_profile_binding": {"evidence_profile_id": "PROFILE", "evidence_profile_version": "1.0", "evidence_profile_sigil": SIGIL}, "assessment": {"kind": "MATCHED", "verified_runtime_observation": observation["runtime_observation"], "verified_termination_observation": observation["termination_observation"], "verified_source_binding": source, "reason_bindings": []}, "created_at": receipt["received_at"], "observation_evidence_sigil": ""}
    evidence["observation_evidence_id"] = derive_observation_evidence_id_v1(evidence)
    evidence["observation_evidence_sigil"] = content_sigil({key: value for key, value in evidence.items() if key != "observation_evidence_sigil"})
    disposition = {"result_ingress_receipt_binding": intent["result_ingress_receipt_binding"], "observation_evidence_subject_sigil": observation["observation_evidence_subject_sigil"], "observation_evidence_id": evidence["observation_evidence_id"], "observation_evidence_sigil": evidence["observation_evidence_sigil"]}

    mismatched = deepcopy(evidence)
    mismatched["assessment"]["kind"] = "MISMATCHED"
    mismatched["assessment"]["reason_bindings"] = [{"field": "TERMINATION_KIND", "reason_code": "MISMATCH", "detail_sigil": SIGIL}]
    mismatched["observation_evidence_id"] = derive_observation_evidence_id_v1(mismatched)
    mismatched["observation_evidence_sigil"] = content_sigil({key: value for key, value in mismatched.items() if key != "observation_evidence_sigil"})
    rejection_disposition = {"result_ingress_receipt_binding": intent["result_ingress_receipt_binding"], "observation_evidence_subject_sigil": observation["observation_evidence_subject_sigil"], "observation_evidence_id": mismatched["observation_evidence_id"], "observation_evidence_sigil": mismatched["observation_evidence_sigil"]}
    rejected = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-REJECTED", "sequence": 12, "event_type": "attempt.result_rejected", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": receipt["received_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 7, "next_revision": 8}], "causation_event_id": ingress["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"disposition_kind": "FIRST_DISPOSITION_REJECTION", "message_sigil": SIGIL, "claimed_result_sigil": SIGIL, "received_at": receipt["received_at"], "reason_codes": ["OBSERVATION_MISMATCH"], "historical_disposition_event_id": None, "observation_evidence_disposition_binding": rejection_disposition}, "previous_event_sigil": ingress["event_sigil"]})
    rejected_state = replay_execution_supplied_state_suffix_v1(ingress_state, [rejected], supplied_result_ingress_receipts=[receipt], supplied_observation_evidence=[mismatched])
    assert rejected_state["attempts"][0]["result_binding"]["kind"] == "REJECTED"

    accepted = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-TWELVE", "sequence": 12, "event_type": "attempt.result_accepted", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": receipt["received_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 7, "next_revision": 8}], "causation_event_id": ingress["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"result_sigil": SIGIL, "lease_revision": 1, "fence_tuple": owner["fence_tuple"], "received_at": receipt["received_at"], "validation_evidence_sigil": evidence["observation_evidence_sigil"], "observation_evidence_disposition_binding": disposition}, "previous_event_sigil": ingress["event_sigil"]})
    accepted_state = replay_execution_supplied_state_suffix_v1(ingress_state, [accepted], supplied_result_ingress_receipts=[receipt], supplied_observation_evidence=[evidence])
    assert accepted_state["attempts"][0]["result_binding"]["kind"] == "ACCEPTED"
    assert accepted_state["attempts"][0]["result_intake"]["outcome"] == "ACCEPTED"

    draining = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-THIRTEEN", "sequence": 13, "event_type": "attempt.draining", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": receipt["received_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 8, "next_revision": 9}], "causation_event_id": accepted["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"result_binding": accepted_state["attempts"][0]["result_binding"], "process_exit_observation_sigil": SIGIL}, "previous_event_sigil": accepted["event_sigil"]})
    draining_state = replay_execution_supplied_state_suffix_v1(accepted_state, [draining])
    assert draining_state["attempts"][0]["state"] == "DRAINING"
    assert draining_state["attempts"][0]["completion_anchor_binding"] == {"kind": "RESULT_ACCEPTED", "event_id": accepted["event_id"], "event_sigil": accepted["event_sigil"], "sequence": accepted["sequence"], "result_sigil": SIGIL}

    wrong_draining = deepcopy(draining)
    wrong_draining["payload"]["result_binding"] = {"kind": "NONE"}
    wrong_draining = build_execution_journal_event_v1({key: value for key, value in wrong_draining.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(accepted_state, [wrong_draining])

    cleaning = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-FOURTEEN", "sequence": 14, "event_type": "attempt.cleaning", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": receipt["received_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 9, "next_revision": 10}], "causation_event_id": draining["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"log_closure_sigil": SIGIL, "output_closure_sigil": SIGIL, "termination_evidence_sigil": SIGIL, "quarantine_plan_sigil": SIGIL, "terminal_source_binding": {"kind": "NOT_APPLICABLE"}}, "previous_event_sigil": draining["event_sigil"]})
    cleaning_state = replay_execution_supplied_state_suffix_v1(draining_state, [cleaning])
    assert cleaning_state["attempts"][0]["state"] == "CLEANING"
    assert cleaning_state["attempts"][0]["terminal_source_binding"] == {"kind": "NOT_APPLICABLE"}

    closed = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-FIFTEEN", "sequence": 15, "event_type": "attempt.cleanup_progressed", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": receipt["received_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 10, "next_revision": 11}], "causation_event_id": cleaning["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"step": "LOGS_CLOSED", "cleanup_evidence_sigil": SIGIL, "remaining_resource_ids": [], "finalization_bindings": {"kind": "NONE"}}, "previous_event_sigil": cleaning["event_sigil"]})
    closed_state = replay_execution_supplied_state_suffix_v1(cleaning_state, [closed])
    assert closed_state["attempts"][0]["revision"] == 11

    capture_finalization = {
        "kind": "FROZEN",
        "control_evidence_set_binding": {
            "kind": "FROZEN", "control_evidence_set_id": "CES-" + "A" * 64,
            "control_evidence_set_sigil": SIGIL,
        },
        "quarantine_binding_set_binding": {
            "kind": "FROZEN", "quarantine_binding_set_id": "QBS-" + "A" * 64,
            "quarantine_binding_set_sigil": SIGIL,
        },
        "terminalization_storage_manifest_binding": {
            "kind": "FROZEN", "storage_root_manifest_id": "ESM-" + "A" * 64,
            "storage_root_manifest_sigil": SIGIL,
        },
        "output_root_protection": {
            "kind": "NO_HOLD", "terminalization_storage_manifest_binding": {
                "kind": "FROZEN", "storage_root_manifest_id": "ESM-" + "A" * 64,
                "storage_root_manifest_sigil": SIGIL,
            },
        },
    }
    accounting_capture = build_execution_journal_event_v1({
        "schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"],
        "event_id": "JE-ACCOUNTING", "sequence": 16, "event_type": "attempt.cleanup_progressed",
        "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1,
        "executor_build_sigil": INITIAL["executor_build_sigil"],
        "recorded_at": receipt["received_at"], "observed_at": None,
        "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE",
                              "preceding_revision": 11, "next_revision": 12}],
        "causation_event_id": closed["event_id"], "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {"step": "ACCOUNTING_CAPTURED", "cleanup_evidence_sigil": SIGIL,
                    "remaining_resource_ids": [], "finalization_bindings": capture_finalization},
        "previous_event_sigil": closed["event_sigil"],
    })
    captured_state = replay_execution_supplied_state_suffix_v1(closed_state, [accounting_capture])
    assert captured_state["attempts"][0]["accounting_capture_binding"]["event_id"] == accounting_capture["event_id"]

    terminal_attempt = captured_state["attempts"][0]
    terminal_evidence = {
        "transition_cause": {
            "code": "COMPLETION_ESTABLISHED", "trigger_kind": "PRIOR_EVENT",
            "trigger_event_id": accepted["event_id"], "effective_sequence": accepted["sequence"],
            "evidence_sigil": SIGIL,
        },
        "computation_status": "COMPLETED", "worker_status": "COMPLETED",
        "process_termination_status": "EXITED", "handle_revocation_status": "NOT_APPLICABLE",
        "cleanup_status": "VERIFIED", "mutable_resource_isolation_status": "NOT_APPLICABLE",
        "output_publication_status": "VERIFIED", "quarantine_status": "NOT_REQUIRED",
        "termination_evidence_sigil": SIGIL, "handle_disposition_evidence_sigil": SIGIL,
        "cleanup_summary_sigil": SIGIL, "quarantine_evidence_sigil": SIGIL,
        "log_closure_sigil": SIGIL, "output_closure_sigil": SIGIL,
        "result_binding": terminal_attempt["result_binding"],
        "attempt_authorization_state": terminal_attempt["attempt_authorization_state"],
        "completion_anchor_binding": terminal_attempt["completion_anchor_binding"],
        "worker_session_binding": terminal_attempt["worker_session_binding"],
        "lease_terminal_binding": terminal_attempt["lease_terminal_binding"] or {"kind": "NONE"},
        "first_stop_or_fence_binding": terminal_attempt["first_stop_or_fence_binding"],
        "storage_observation_binding": {
            "kind": "FROZEN", "storage_journal_id": "SJ-ONE", "through_sequence": 1,
            "through_event_sigil": SIGIL, "output_storage_observation_set_id": "OS-ONE",
            "output_storage_observation_set_sigil": SIGIL,
        },
            "accounting_capture_event_id": accounting_capture["event_id"],
            "accounting_capture_event_sigil": accounting_capture["event_sigil"],
            "control_evidence_set_binding": capture_finalization["control_evidence_set_binding"],
            "quarantine_binding_set_binding": capture_finalization["quarantine_binding_set_binding"],
            "terminalization_storage_manifest_binding": capture_finalization["terminalization_storage_manifest_binding"],
            "output_root_protection": capture_finalization["output_root_protection"],
        "assurance_input_set_sigil": SIGIL,
        "terminal_source_binding": terminal_attempt["terminal_source_binding"],
    }
    terminal = build_execution_journal_event_v1({
        "schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"],
            "event_id": "JE-TERMINAL", "sequence": 17, "event_type": "attempt.succeeded",
        "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1,
        "executor_build_sigil": INITIAL["executor_build_sigil"],
        "recorded_at": receipt["received_at"], "observed_at": None,
        "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE",
                                  "preceding_revision": 12, "next_revision": 13}],
            "causation_event_id": accounting_capture["event_id"], "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {"attempt_terminal_evidence": terminal_evidence,
                    "fencing_generation": 1, "final_fence_floor": 1,
                    "output_storage_roots": []},
            "previous_event_sigil": accounting_capture["event_sigil"],
        })
    terminal_state = replay_execution_supplied_state_suffix_v1(captured_state, [terminal])
    assert terminal_state["attempts"][0]["state"] == "SUCCEEDED"
    assert terminal_state["attempts"][0]["terminal_event_binding"]["terminal_event_sigil"] == terminal["event_sigil"]

    reservation = attempt["budget_reservation"]
    settled_ledger = {
        name: {
            "limit": value, "reserved": 0, "consumed": value,
            "exhaustion_status": "EXHAUSTED",
        }
        for name, value in reservation.items()
    }
    settled_ledger["budget_ledger_sigil"] = content_sigil(settled_ledger)
    settled = build_execution_journal_event_v1({
        "schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"],
        "event_id": "JE-SETTLED", "sequence": 18, "event_type": "job.budget_settled",
        "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1,
        "executor_build_sigil": INITIAL["executor_build_sigil"],
        "recorded_at": receipt["received_at"], "observed_at": None,
        "entity_revisions": [
            {"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 2, "next_revision": 3},
            {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 13, "next_revision": 14},
        ],
        "causation_event_id": terminal["event_id"], "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {
            "attempt_id": "AT-ONE", "reservation": reservation,
            "accounting_capture_event_id": accounting_capture["event_id"],
            "accounting_capture_event_sigil": accounting_capture["event_sigil"], "usage_status": "UNAVAILABLE",
            "measured": reservation, "charged": reservation,
            "accounting_started_at": receipt["received_at"],
            "accounting_ended_at": receipt["received_at"],
            "supervisor_identity": {"kind": "EXECUTOR", "identity_sigil": SIGIL},
            "accounting_evidence_set_sigil": accounting_capture["payload"]["cleanup_evidence_sigil"],
            "resulting_budget_ledger_sigil": settled_ledger["budget_ledger_sigil"],
        },
        "previous_event_sigil": terminal["event_sigil"],
    })
    settled_state = replay_execution_supplied_state_suffix_v1(
        terminal_state, [settled], supplied_attempts=[attempt]
    )
    assert settled_state["jobs"][0]["budget_ledger"] == settled_ledger
    assert settled_state["attempts"][0]["budget_settlement_binding"]["kind"] == "SETTLED"

    supplied_claim = _assurance_claim()
    supplied_claim.update({
        "attempt_binding_sigil": attempt["attempt_binding_sigil"],
        "attempt_terminal_event": {
            "journal_id": INITIAL["journal_id"],
            "sequence": terminal["sequence"],
            "event_id": terminal["event_id"],
            "event_sigil": terminal["event_sigil"],
        },
        "assurance_profile_binding": {
            key: value for key, value in job["assurance_requirement"].items()
            if key != "requested_level"
        },
        "result_binding": {
            "kind": "ACCEPTED",
            "result_sigil": SIGIL,
            "disposition_event": {
                "journal_id": INITIAL["journal_id"],
                "sequence": accepted["sequence"],
                "event_id": accepted["event_id"],
                "event_sigil": accepted["event_sigil"],
            },
        },
        "control_evidence_set_binding": capture_finalization[
            "control_evidence_set_binding"
        ],
        "terminal_status": {
            "attempt_state": "SUCCEEDED",
            "process_termination_status": "EXITED",
            "handle_revocation_status": "NOT_APPLICABLE",
            "cleanup_status": "VERIFIED",
            "quarantine_status": "NOT_REQUIRED",
        },
    })
    supplied_claim["evidence_cut"].update({
        "journal_prefix": {
            "journal_id": INITIAL["journal_id"],
            "ending_sequence": settled["sequence"],
            "ending_event_id": settled["event_id"],
            "ending_event_sigil": settled["event_sigil"],
        },
        "state_sigil": settled_state["state_sigil"],
        "accounting_capture_event": {
            "journal_id": INITIAL["journal_id"],
            "sequence": accounting_capture["sequence"],
            "event_id": accounting_capture["event_id"],
            "event_sigil": accounting_capture["event_sigil"],
        },
        "budget_settlement_event": {
            "journal_id": INITIAL["journal_id"],
            "sequence": settled["sequence"],
            "event_id": settled["event_id"],
            "event_sigil": settled["event_sigil"],
        },
        "control_evidence_set_binding": capture_finalization[
            "control_evidence_set_binding"
        ],
    })
    supplied_claim["assurance_claim_sigil"] = content_sigil({
        key: value for key, value in supplied_claim.items()
        if key != "assurance_claim_sigil"
    })
    validate_sanctum_assurance_claim_supplied_attempt_facts_v1(
        supplied_claim,
        job,
        settled_state,
        "AT-ONE",
        accounting_capture,
        settled,
    )
    forged_claim = deepcopy(supplied_claim)
    forged_claim["evidence_cut"]["state_sigil"] = SIGIL_B
    forged_claim["assurance_claim_sigil"] = content_sigil({
        key: value for key, value in forged_claim.items()
        if key != "assurance_claim_sigil"
    })
    with pytest.raises(AthanorError, match="terminal Attempt facts"):
        validate_sanctum_assurance_claim_supplied_attempt_facts_v1(
            forged_claim,
            job,
            settled_state,
            "AT-ONE",
            accounting_capture,
            settled,
        )

    forged_claim = deepcopy(supplied_claim)
    forged_claim["evidence_cut"]["control_evidence_set_binding"]["control_evidence_set_sigil"] = SIGIL_B
    forged_claim["assurance_claim_sigil"] = content_sigil({
        key: value for key, value in forged_claim.items()
        if key != "assurance_claim_sigil"
    })
    with pytest.raises(AthanorError, match="terminal Attempt facts"):
        validate_sanctum_assurance_claim_supplied_attempt_facts_v1(
            forged_claim,
            job,
            settled_state,
            "AT-ONE",
            accounting_capture,
            settled,
        )

    forged_claim = deepcopy(supplied_claim)
    forged_claim["evidence_cut"]["accounting_capture_event"]["sequence"] = 15
    forged_claim["assurance_claim_sigil"] = content_sigil({
        key: value for key, value in forged_claim.items()
        if key != "assurance_claim_sigil"
    })
    with pytest.raises(AthanorError, match="terminal Attempt facts"):
        validate_sanctum_assurance_claim_supplied_attempt_facts_v1(
            forged_claim,
            job,
            settled_state,
            "AT-ONE",
            accounting_capture,
            settled,
        )

    partial_undercharge = deepcopy(settled)
    partial_undercharge["payload"].update({
        "usage_status": "PARTIAL",
        "measured": {name: 0 for name in reservation},
        "charged": {name: 0 for name in reservation},
    })
    partial_undercharge = build_execution_journal_event_v1({
        key: value for key, value in partial_undercharge.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="Partial budget settlement must charge"):
        replay_execution_supplied_state_suffix_v1(
            terminal_state, [partial_undercharge], supplied_attempts=[attempt]
        )

    attempt_assurance = build_execution_journal_event_v1({
        "schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"],
        "event_id": "JE-ATTEMPTASSURANCE", "sequence": 19,
        "event_type": "attempt.assurance_evaluated",
        "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1,
        "executor_build_sigil": INITIAL["executor_build_sigil"],
        "recorded_at": receipt["received_at"], "observed_at": None,
        "entity_revisions": [
            {"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 3, "next_revision": 4},
            {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 14, "next_revision": 15},
        ],
        "causation_event_id": settled["event_id"], "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {"evaluation": "CLAIMED", "assurance_claim_sigil": supplied_claim["assurance_claim_sigil"],
                    "reason_codes": [], "evidence_set_sigil": SIGIL},
        "previous_event_sigil": settled["event_sigil"],
    })
    assured_state = replay_execution_supplied_state_suffix_v1(
        settled_state,
        [attempt_assurance],
        supplied_jobs=[job],
        supplied_assurance_claims=[supplied_claim],
        supplied_accounting_capture_events=[accounting_capture],
        supplied_budget_settlement_events=[settled],
    )
    assert assured_state["jobs"][0]["current_attempt_id"] is None
    assert assured_state["attempts"][0]["attempt_assurance_binding"]["kind"] == "CLAIMED"
    assert assured_state["jobs"][0]["attempt_summaries"][0]["attempt_id"] == "AT-ONE"

    with pytest.raises(AthanorError, match="Claimed Attempt assurance"):
        replay_execution_supplied_state_suffix_v1(settled_state, [attempt_assurance])

    unsatisfied_claim = deepcopy(supplied_claim)
    unsatisfied_claim["satisfies_request"] = False
    unsatisfied_claim["assurance_claim_sigil"] = content_sigil(
        {key: value for key, value in unsatisfied_claim.items() if key != "assurance_claim_sigil"}
    )
    unsatisfied_assurance = deepcopy(attempt_assurance)
    unsatisfied_assurance["payload"]["assurance_claim_sigil"] = unsatisfied_claim[
        "assurance_claim_sigil"
    ]
    unsatisfied_assurance = build_execution_journal_event_v1(
        {key: value for key, value in unsatisfied_assurance.items() if key != "event_sigil"}
    )
    with pytest.raises(AthanorError, match="satisfies its request"):
        replay_execution_supplied_state_suffix_v1(
            settled_state,
            [unsatisfied_assurance],
            supplied_jobs=[job],
            supplied_assurance_claims=[unsatisfied_claim],
            supplied_accounting_capture_events=[accounting_capture],
            supplied_budget_settlement_events=[settled],
        )

    unmet_attempt_assurance = deepcopy(attempt_assurance)
    unmet_attempt_assurance["payload"].update({
        "evaluation": "UNMET", "assurance_claim_sigil": None,
        "reason_codes": ["ASSURANCE_UNMET"],
    })
    unmet_attempt_assurance = build_execution_journal_event_v1({
        key: value for key, value in unmet_attempt_assurance.items() if key != "event_sigil"
    })
    unmet_state = replay_execution_supplied_state_suffix_v1(settled_state, [unmet_attempt_assurance])
    assert unmet_state["attempts"][0]["attempt_assurance_binding"]["kind"] == "UNMET"
    assert unmet_state["jobs"][0]["attempt_summaries"][0]["assurance_evaluation_event_sigil"] == unmet_attempt_assurance["event_sigil"]

    retry_state_unsigned = deepcopy(assured_state)
    retry_state_unsigned.pop("state_sigil")
    retry_job = retry_state_unsigned["jobs"][0]
    retry_job.update({
        "state": "QUEUED",
        "queue_key": {"ready_sequence": 20, "job_id": JOB_ID},
    })
    retry_ledger = {
        name: {
            "limit": 2,
            "reserved": 0,
            "consumed": 1,
            "exhaustion_status": "AVAILABLE",
        }
        for name in reservation
    }
    retry_ledger["budget_ledger_sigil"] = content_sigil(retry_ledger)
    retry_job["budget_ledger"] = retry_ledger
    retry_state = build_execution_state_v1(retry_state_unsigned)

    retry_attempt = _reseal_attempt({
        **deepcopy(attempt),
        "attempt_id": "AT-TWO",
        "retry_ordinal": 2,
        "fencing_generation": 2,
        "crucible_id": "CU-TWO",
        "output_namespace_id": "ON-TWO",
        "log_stream_ids": {
            "STDOUT": "LG-FOUR",
            "STDERR": "LG-FIVE",
            "STRUCTURED": "LG-SIX",
        },
        "created_at": "2026-08-06T00:00:04Z",
    })

    def retry_allocation_event(candidate: dict[str, Any]) -> dict[str, Any]:
        resulting_ledger = {
            name: {
                "limit": 2,
                "reserved": 1,
                "consumed": 1,
                "exhaustion_status": "EXHAUSTED",
            }
            for name in reservation
        }
        resulting_ledger["budget_ledger_sigil"] = content_sigil(resulting_ledger)
        return build_execution_journal_event_v1({
            "schema_version": "execution-journal-event/1.0",
            "journal_id": INITIAL["journal_id"],
            "event_id": "JE-RETRYALLOCATED",
            "sequence": 20,
            "event_type": "job.attempt_allocated",
            "executor_instance_id": INITIAL["executor_instance_id"],
            "executor_epoch": 1,
            "executor_build_sigil": INITIAL["executor_build_sigil"],
            "recorded_at": candidate["created_at"],
            "observed_at": None,
            "entity_revisions": [
                {"entity_kind": "JOB", "entity_id": JOB_ID,
                 "preceding_revision": 4, "next_revision": 5},
                {"entity_kind": "ATTEMPT", "entity_id": candidate["attempt_id"],
                 "preceding_revision": None, "next_revision": 0},
                *[
                    {"entity_kind": "LOG_STREAM", "entity_id": stream_id,
                     "preceding_revision": None, "next_revision": 0}
                    for stream_id in sorted(candidate["log_stream_ids"].values())
                ],
            ],
            "causation_event_id": retry_state["jobs"][0]["last_event_id"],
            "idempotency_key_sigil": None,
            "recovery_action_binding": None,
            "payload": {
                "attempt_binding_sigil": candidate["attempt_binding_sigil"],
                "retry_ordinal": 2,
                "fencing_generation": 2,
                "prior_fencing_counter": 1,
                "resulting_fence_floor": 2,
                "budget_reservation": candidate["budget_reservation"],
                "resulting_budget_ledger_sigil": resulting_ledger["budget_ledger_sigil"],
            },
            "previous_event_sigil": retry_state["journal_binding"]["through_event_sigil"],
        })

    allocated_retry_state = replay_execution_supplied_state_suffix_v1(
        retry_state,
        [retry_allocation_event(retry_attempt)],
        supplied_attempts=[attempt, retry_attempt],
    )
    assert [item["attempt_id"] for item in allocated_retry_state["attempts"]] == [
        "AT-ONE", "AT-TWO"
    ]

    for field, old_value in (
        ("crucible_id", attempt["crucible_id"]),
        ("output_namespace_id", attempt["output_namespace_id"]),
        ("log_stream_ids", attempt["log_stream_ids"]),
    ):
        reused = _reseal_attempt({**deepcopy(retry_attempt), field: old_value})
        with pytest.raises(AthanorError, match="queued Job projection"):
            replay_execution_supplied_state_suffix_v1(
                retry_state,
                [retry_allocation_event(reused)],
                supplied_attempts=[attempt, reused],
            )

    job_assurance = build_execution_journal_event_v1({
        "schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"],
        "event_id": "JE-JOBASSURANCE", "sequence": 20, "event_type": "job.assurance_evaluated",
        "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1,
        "executor_build_sigil": INITIAL["executor_build_sigil"],
        "recorded_at": receipt["received_at"], "observed_at": None,
        "entity_revisions": [{"entity_kind": "JOB", "entity_id": JOB_ID,
                              "preceding_revision": 4, "next_revision": 5}],
        "causation_event_id": attempt_assurance["event_id"], "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {"evaluation": "CLAIMED", "attempt_id": "AT-ONE",
                    "attempt_assurance_event_sigil": attempt_assurance["event_sigil"],
                        "assurance_claim_sigil": supplied_claim["assurance_claim_sigil"], "reason_codes": [],
                    "evidence_set_sigil": SIGIL},
        "previous_event_sigil": attempt_assurance["event_sigil"],
    })
    job_assured_state = replay_execution_supplied_state_suffix_v1(assured_state, [job_assurance])
    assert job_assured_state["jobs"][0]["job_assurance_binding"]["kind"] == "CLAIMED"

    selected_attempt = job_assured_state["attempts"][0]
    selected_binding = {
        "kind": "SELECTED", "attempt_id": "AT-ONE",
        "attempt_binding_sigil": attempt["attempt_binding_sigil"],
        "attempt_terminal_event_id": terminal["event_id"],
        "attempt_terminal_event_sigil": terminal["event_sigil"],
        "attempt_authorization_state": selected_attempt["attempt_authorization_state"],
        "worker_session_binding": selected_attempt["worker_session_binding"],
        "result_binding": selected_attempt["result_binding"],
        "completion_anchor_binding": selected_attempt["completion_anchor_binding"],
        "first_stop_or_fence_binding": selected_attempt["first_stop_or_fence_binding"],
        "storage_observation_binding": selected_attempt["storage_observation_binding"],
    }
    job_terminal = build_execution_journal_event_v1({
        "schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"],
        "event_id": "JE-JOBSUCCEEDED", "sequence": 21, "event_type": "job.succeeded",
        "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1,
        "executor_build_sigil": INITIAL["executor_build_sigil"],
        "recorded_at": receipt["received_at"], "observed_at": None,
        "entity_revisions": [{"entity_kind": "JOB", "entity_id": JOB_ID,
                              "preceding_revision": 5, "next_revision": 6}],
        "causation_event_id": job_assurance["event_id"], "idempotency_key_sigil": None,
        "recovery_action_binding": None,
        "payload": {
            "transition_cause": {"code": "COMPLETION_ESTABLISHED", "trigger_kind": "PRIOR_EVENT",
                                 "trigger_event_id": job_assurance["event_id"], "effective_sequence": 20,
                                 "evidence_sigil": SIGIL},
            "attempt_summaries": job_assured_state["jobs"][0]["attempt_summaries"],
            "selected_attempt_binding": selected_binding,
            "completion_anchor_binding": selected_attempt["completion_anchor_binding"],
            "first_stop_or_fence_binding": selected_attempt["first_stop_or_fence_binding"],
            "job_assurance_event_sigil": job_assurance["event_sigil"],
            "budget_ledger_sigil": settled_ledger["budget_ledger_sigil"],
            "final_fence_binding": {"kind": "ASSIGNED_NO_LEASE", "final_fence_floor": 1,
                                    "attempt_id": "AT-ONE", "attempt_terminal_event_sigil": terminal["event_sigil"]},
            "cleanup_summary_sigil": SIGIL,
            "storage_observation_binding": selected_attempt["storage_observation_binding"],
            "terminal_source_binding": selected_attempt["terminal_source_binding"],
            "output_hold_release_schedules": [],
        },
        "previous_event_sigil": job_assurance["event_sigil"],
    })
    terminal_job_state = replay_execution_supplied_state_suffix_v1(job_assured_state, [job_terminal])
    assert terminal_job_state["jobs"][0]["state"] == "SUCCEEDED"

    duplicate_settlement = deepcopy(settled)
    duplicate_settlement["event_id"] = "JE-SETTLEDTWO"
    duplicate_settlement["sequence"] = 19
    duplicate_settlement["entity_revisions"][0].update({"preceding_revision": 3, "next_revision": 4})
    duplicate_settlement["entity_revisions"][1].update({"preceding_revision": 14, "next_revision": 15})
    duplicate_settlement["previous_event_sigil"] = settled["event_sigil"]
    duplicate_settlement = build_execution_journal_event_v1({
        key: value for key, value in duplicate_settlement.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(
            settled_state, [duplicate_settlement], supplied_attempts=[attempt]
        )

    forged_terminal = deepcopy(terminal)
    forged_terminal["payload"]["attempt_terminal_evidence"]["result_binding"] = {"kind": "NONE"}
    forged_terminal = build_execution_journal_event_v1({
        key: value for key, value in forged_terminal.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(captured_state, [forged_terminal])

    late_rejection = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-LATEREJECT", "sequence": 16, "event_type": "attempt.result_rejected", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": receipt["received_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 11, "next_revision": 12}], "causation_event_id": closed["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"disposition_kind": "LATE_OR_CONFLICTING_REJECTION", "message_sigil": SIGIL, "claimed_result_sigil": SIGIL, "received_at": receipt["received_at"], "reason_codes": ["LEASE_TERMINAL"], "historical_disposition_event_id": accepted["event_id"]}, "previous_event_sigil": closed["event_sigil"]})
    late_rejected_state = replay_execution_supplied_state_suffix_v1(closed_state, [late_rejection])
    assert late_rejected_state["attempts"][0]["result_binding"] == accepted_state["attempts"][0]["result_binding"]
    assert late_rejected_state["attempts"][0]["revision"] == 12

    stdout_stream = next(stream for stream in closed_state["log_streams"] if stream["stream"] == "STDOUT")
    log_closed = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-LOGCLOSED", "sequence": 16, "event_type": "log.closed", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": receipt["received_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "LOG_STREAM", "entity_id": stdout_stream["log_stream_id"], "preceding_revision": 0, "next_revision": 1}], "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"log_stream_id": stdout_stream["log_stream_id"], "stream": "STDOUT", "final_sequence": None, "captured_bytes": 0, "dropped_bytes": 0, "stream_set_sigil": SIGIL, "freeze_binding": {"kind": "NONE"}, "closure_intent_id": "LCI-ONE"}, "previous_event_sigil": closed["event_sigil"]})
    log_closed_state = replay_execution_supplied_state_suffix_v1(closed_state, [log_closed])
    assert next(stream for stream in log_closed_state["log_streams"] if stream["stream"] == "STDOUT")["state"] == "CLOSED"

    wrong_log_close = deepcopy(log_closed)
    wrong_log_close["payload"]["captured_bytes"] = 1
    wrong_log_close = build_execution_journal_event_v1({key: value for key, value in wrong_log_close.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(closed_state, [wrong_log_close])

    log_rejected = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-LOGREJECT", "sequence": 16, "event_type": "log.chunk_rejected", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": receipt["received_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "LOG_STREAM", "entity_id": stdout_stream["log_stream_id"], "preceding_revision": 0, "next_revision": 1}], "causation_event_id": None, "idempotency_key_sigil": SIGIL, "recovery_action_binding": None, "payload": {"intake_kind": "RAW_CHUNK", "intake_id": "LCI-ONE", "intake_record_sigil": SIGIL, "disposition_intent_id": "LDI-ONE", "log_stream_id": stdout_stream["log_stream_id"], "stream": "STDOUT", "sequence": 0, "message_sigil": SIGIL, "reason_codes": ["LEASE_TERMINAL"], "historical_disposition_event_id": None}, "previous_event_sigil": closed["event_sigil"]})
    log_rejected_state = replay_execution_supplied_state_suffix_v1(closed_state, [log_rejected])
    rejected_stream = next(stream for stream in log_rejected_state["log_streams"] if stream["stream"] == "STDOUT")
    assert (rejected_stream["captured_bytes"], rejected_stream["next_sequence"]) == (0, 0)

    wrong_log_rejection = deepcopy(log_rejected)
    wrong_log_rejection["payload"]["stream"] = "STDERR"
    wrong_log_rejection = build_execution_journal_event_v1({key: value for key, value in wrong_log_rejection.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(closed_state, [wrong_log_rejection])

    log_truncated = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-LOGTRUNCATED", "sequence": 16, "event_type": "log.truncated", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": receipt["received_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "LOG_STREAM", "entity_id": stdout_stream["log_stream_id"], "preceding_revision": 0, "next_revision": 1}], "causation_event_id": None, "idempotency_key_sigil": SIGIL, "recovery_action_binding": None, "payload": {"intake_kind": "RAW_CHUNK", "intake_id": "LCI-ONE", "intake_record_sigil": SIGIL, "disposition_intent_id": "LDI-ONE", "log_stream_id": stdout_stream["log_stream_id"], "stream": "STDOUT", "limit_kind": "PER_STREAM", "limit_bytes": 0, "captured_bytes": 0, "dropped_bytes": 1, "overflow_behavior": "TRUNCATE", "structured_truncation_status": "NOT_APPLICABLE", "accepted_prefix_length": 0, "capture_cutoff_ordinal": 0}, "previous_event_sigil": closed["event_sigil"]})
    log_truncated_state = replay_execution_supplied_state_suffix_v1(closed_state, [log_truncated])
    truncated_stream = next(stream for stream in log_truncated_state["log_streams"] if stream["stream"] == "STDOUT")
    assert (truncated_stream["truncated"], truncated_stream["dropped_bytes"]) == (True, 1)

    duplicate_truncation = deepcopy(log_truncated)
    duplicate_truncation["event_id"] = "JE-LOGTRUNCATED2"
    duplicate_truncation["sequence"] = 17
    duplicate_truncation["entity_revisions"][0].update({"preceding_revision": 1, "next_revision": 2})
    duplicate_truncation["previous_event_sigil"] = log_truncated["event_sigil"]
    duplicate_truncation = build_execution_journal_event_v1({key: value for key, value in duplicate_truncation.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(log_truncated_state, [duplicate_truncation])

    wrong_late_rejection = deepcopy(late_rejection)
    wrong_late_rejection["payload"]["historical_disposition_event_id"] = None
    wrong_late_rejection = build_execution_journal_event_v1({key: value for key, value in wrong_late_rejection.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(closed_state, [wrong_late_rejection])

    premature_capture = deepcopy(closed)
    premature_capture["payload"]["step"] = "ACCOUNTING_CAPTURED"
    premature_capture = build_execution_journal_event_v1({key: value for key, value in premature_capture.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(cleaning_state, [premature_capture])

    released = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-SIXTEEN", "sequence": 16, "event_type": "lease.released", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": receipt["received_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 3, "next_revision": 4}, {"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 2, "next_revision": 3}, {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 11, "next_revision": 12}, {"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": 1, "next_revision": 2}], "causation_event_id": closed["event_id"], "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"release_evidence_sigil": SIGIL, "prior_fence_floor": 1, "tombstone_generation": 2, "tombstone_publication_sigil": SIGIL, "session_capacity_after": 0}, "previous_event_sigil": closed["event_sigil"]})
    released_state = replay_execution_supplied_state_suffix_v1(closed_state, [released])
    assert released_state["leases"][0]["state"] == "RELEASED"
    assert released_state["attempts"][0]["lease_terminal_binding"]["lease_state"] == "RELEASED"
    assert released_state["jobs"][0]["fence_floor"] == 2

    malformed = deepcopy(ingress)
    malformed["payload"]["result_sigil"] = "sha256:" + "b" * 64
    malformed = build_execution_journal_event_v1({key: value for key, value in malformed.items() if key != "event_sigil"})
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_supplied_state_suffix_v1(running_state, [malformed], supplied_result_ingress_receipts=[receipt], supplied_result_ingress_intents=[intent])

    wrong_attempt = deepcopy(attempt)
    wrong_attempt["retry_ordinal"] = 2
    wrong_attempt["attempt_binding_sigil"] = content_sigil(
        {key: value for key, value in wrong_attempt.items() if key != "attempt_binding_sigil"}
    )
    with pytest.raises(AthanorError, match="disagrees"):
        replay_execution_journal_prefix_v1(
            [INITIAL, event, queued, allocated],
            supplied_jobs=[job],
            supplied_attempts=[wrong_attempt],
        )

    duplicate_attempt = deepcopy(attempt)
    duplicate_attempt.update({
        "attempt_id": "AT-TWO",
        "retry_ordinal": 2,
        "fencing_generation": 2,
        "created_at": "2026-08-06T00:00:04Z",
    })
    duplicate_attempt["attempt_binding_sigil"] = content_sigil({
        key: value for key, value in duplicate_attempt.items() if key != "attempt_binding_sigil"
    })
    retry_allocation = deepcopy(allocated)
    retry_allocation.update({
        "event_id": "JE-ALLOCATEDTWO", "sequence": 4,
        "recorded_at": duplicate_attempt["created_at"],
        "previous_event_sigil": queued["event_sigil"],
        "entity_revisions": [
            {"entity_kind": "JOB", "entity_id": JOB_ID, "preceding_revision": 1, "next_revision": 2},
            {"entity_kind": "ATTEMPT", "entity_id": "AT-TWO", "preceding_revision": None, "next_revision": 0},
            *[
                {"entity_kind": "LOG_STREAM", "entity_id": stream_id, "preceding_revision": None, "next_revision": 0}
                for stream_id in sorted(duplicate_attempt["log_stream_ids"].values())
            ],
        ],
        "payload": {
            "attempt_binding_sigil": duplicate_attempt["attempt_binding_sigil"],
            "retry_ordinal": 2, "fencing_generation": 2, "prior_fencing_counter": 1,
            "resulting_fence_floor": 2, "budget_reservation": duplicate_attempt["budget_reservation"],
            "resulting_budget_ledger_sigil": SIGIL,
        },
    })
    retry_allocation["event_sigil"] = content_sigil({
        key: value for key, value in retry_allocation.items() if key != "event_sigil"
    })
    with pytest.raises(AthanorError, match="queued Job projection"):
        replay_execution_journal_prefix_v1(
            [INITIAL, event, queued, retry_allocation],
            supplied_jobs=[job], supplied_attempts=[attempt, duplicate_attempt],
        )

    altered = deepcopy(job)
    altered["deadline_due_at"] = "2026-08-06T00:02:00Z"
    altered["job_binding_sigil"] = content_sigil(
        {key: value for key, value in altered.items() if key != "job_binding_sigil"}
    )
    with pytest.raises(AthanorError, match="does not exactly copy"):
        replay_execution_journal_prefix_v1([INITIAL, event], supplied_jobs=[altered])
    with pytest.raises(AthanorError, match="requires exactly one supplied immutable record"):
        replay_execution_journal_prefix_v1([INITIAL, event])
