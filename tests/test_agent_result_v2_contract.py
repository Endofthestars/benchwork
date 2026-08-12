from __future__ import annotations

from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.execution_contracts import (
    validate_agent_result_acceptance_transition_request_v1,
    validate_agent_result_v2,
)
from benchwork.schema_validation import validate_instance


SIGIL = "sha256:" + "a" * 64


def _result() -> dict[str, object]:
    manifest = {"kind": "FROZEN", "storage_root_manifest_id": "ESM-" + "A" * 64, "storage_root_manifest_sigil": SIGIL}
    return {
        "schema_version": "agent-result/2.0", "task_id": "TK-ONE", "program_id": "RP-ONE",
        "task_capsule_sigil": SIGIL, "host_identity_sigil": SIGIL,
        "capability_binding": {"capability_id": "bench.work.exec", "contract_version": "2.0", "capability_contract_sigil": SIGIL},
        "snapshot_binding": {"snapshot_id": "SS-ONE", "snapshot_sigil": SIGIL},
        "job_binding": {"job_id": "JB-" + "A" * 64, "job_binding_sigil": SIGIL},
        "execution_specification_binding": {"specification_id": "ES-" + "0" * 26, "specification_sigil": SIGIL},
        "job_outcome_binding": {"outcome_id": "OJ-" + "A" * 64, "outcome_sigil": SIGIL},
        "terminal_event_sigil": SIGIL, "selected_attempt_id": "AT-" + "0" * 26,
        "assurance_claim_sigil": SIGIL, "terminal_source_binding": {"kind": "NOT_APPLICABLE"},
        "status": "COMPLETED", "outputs": [
            {"task_output_id": "alpha", "declared_schema_id": "result/1.0", "declared_schema_sigil": SIGIL, "blob_sigil": "sha256:" + "b" * 64, "size_bytes": 1, "source_observation_member_sigil": SIGIL, "storage_integrity_evidence_sigil": SIGIL},
            {"task_output_id": "beta", "declared_schema_id": "result/1.0", "declared_schema_sigil": SIGIL, "blob_sigil": "sha256:" + "c" * 64, "size_bytes": 1, "source_observation_member_sigil": SIGIL, "storage_integrity_evidence_sigil": SIGIL},
        ],
        "provenance": {
            "executor_instance_id": "XI-ONE", "executor_epoch": 1, "executor_build_sigil": SIGIL,
            "worker_id": "WK-ONE", "worker_binding_sigil": SIGIL, "worker_session_id": "WS-0123456789ABCDEFGHJKMNPQRS",
            "worker_session_binding_sigil": SIGIL, "backend_identity": "BACKEND", "backend_configuration_sigil": SIGIL,
            "requested_assurance_level": "SANCTUM-A1", "assurance_profile_sigil": SIGIL,
            "conformance_suite_sigil": SIGIL, "attempt_authorization_state": {"kind": "NONE"},
            "budget_settlement_event_sigil": SIGIL, "job_budget_ledger_sigil": SIGIL,
            "storage_observation_binding": {"kind": "FROZEN", "storage_journal_id": "SJ-ONE", "through_sequence": 1, "through_event_sigil": SIGIL, "output_storage_observation_set_id": "OS-ONE", "output_storage_observation_set_sigil": SIGIL},
            "control_evidence_set_binding": {"kind": "FROZEN", "control_evidence_set_id": "CES-" + "A" * 64, "control_evidence_set_sigil": SIGIL},
            "quarantine_binding_set_binding": {"kind": "FROZEN", "quarantine_binding_set_id": "QBS-" + "A" * 64, "quarantine_binding_set_sigil": SIGIL},
            "terminalization_storage_manifest_binding": manifest,
            "output_root_protection": {"kind": "NO_HOLD", "terminalization_storage_manifest_binding": manifest},
        }, "result_sigil": "",
    }


def _seal_result(result: dict[str, object]) -> dict[str, object]:
    result["result_sigil"] = content_sigil({key: value for key, value in result.items() if key != "result_sigil"})
    return result


def _authorization(result: dict[str, object]) -> dict[str, object]:
    blobs = ["sha256:" + "b" * 64]
    head = {"schema_version": "chronicle-head/1.1", "event_count": 1, "terminal_receipt_sigil": SIGIL}
    evidence = [{"blob_sigil": blobs[0], "size_bytes": 1, "replica_id": "SR-ONE", "backend_id": "BACKEND", "backend_generation": "1", "availability_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1, "event_sigil": SIGIL}, "integrity_evidence_sigil": SIGIL, "quarantine_status": "CLEAR"}]
    policy = {"schema_version": "agent-result-acceptance-policy/1.0", "policy_id": "agent-result-acceptance", "policy_version": "1.0", "canonical_event_type": "agent-result.accepted", "transition_request_schema": "agent-result-acceptance-transition-request/1.0", "authorization_schema": "agent-result-acceptance-authorization/1.0", "agent_result_schema": "agent-result/2.0", "job_outcome_schema": "execution-job-outcome/1.0", "reference_intent_schema": "artifact-storage-reference-intent/1.0", "chronicle_event_schema": "chronicle-event/1.1", "receipt_schema": "receipt/1.1", "ward_evaluator_profile": "sanctum-authority-intersection/1.0", "actor_authentication_profile": "mcp-authenticated-invocation/1.0", "predicate_profile": "agent-result-acceptance-predicates/1.0", "predicates": ["EXPECTED_HEAD_ADMISSIBLE", "AUTHENTICATED_INVOCATION_MATCH", "TASK_AUTHORITY_CHAIN_VALID", "CURRENT_WARD_PASS", "APPROVAL_CHAIN_VALID", "OUTCOME_REDERIVATION_MATCH", "TERMINAL_SUCCESS_ELIGIBLE", "EXECUTION_EVIDENCE_VALID", "BUDGET_SETTLED", "ASSURANCE_EVIDENCE_VALID", "STORAGE_OBSERVATION_VALID", "TERMINAL_SOURCE_VALID", "EVIDENCE_SELECTION_FINAL", "AGENT_RESULT_DERIVATION_MATCH", "REFERENCE_SET_CLOSURE_VALID", "ACCEPTANCE_STORAGE_PREFIX_VALID"], "policy_sigil": ""}
    policy["policy_sigil"] = content_sigil({key: value for key, value in policy.items() if key != "policy_sigil"})
    authorization: dict[str, object] = {
        "schema_version": "agent-result-acceptance-authorization/1.0", "transition_request_id": "", "event_type": "agent-result.accepted", "expected_chronicle_head": head,
        "authority_subject": {"registry_binding": {"registry_id": "CR-ONE", "registry_revision": 1, "registry_sigil": SIGIL}, "task_binding": {"task_id": result["task_id"], "task_capsule_sigil": result["task_capsule_sigil"]}, "program_id": result["program_id"], "capability_binding": result["capability_binding"], "snapshot_binding": result["snapshot_binding"], "circle_binding": {"circle_id": "CI-ONE", "circle_sigil": SIGIL}, "execution_specification_binding": result["execution_specification_binding"], "job_binding": result["job_binding"], "job_outcome_binding": result["job_outcome_binding"], "agent_result_sigil": result["result_sigil"]},
        "ward_pass": {"status": "PASS", "ward_decision_id": "WD-ONE", "ward_decision_sigil": SIGIL, "resolved_permission_set_sigil": SIGIL, "evaluated_chronicle_head": head, "evaluated_at": "2026-08-06T00:00:00Z"},
        "approval": {"kind": "NOT_REQUIRED", "ward_decision_id": "WD-ONE", "ward_decision_sigil": SIGIL}, "acceptance_policy": policy, "acceptance_request_sigil": SIGIL, "idempotency_key_sigil": SIGIL, "reference_sets": [{"reference_set_id": "RS-ONE", "reference_set_sigil": SIGIL}], "managed_blob_sigils": blobs,
        "acceptance_storage_binding": {"storage_event": {"journal_id": "SJ-ONE", "event_id": "SE-ONE", "sequence": 1, "event_sigil": SIGIL}, "storage_state_sigil": SIGIL, "validated_blob_sigils": blobs, "validation_evidence": evidence, "validation_evidence_set_sigil": content_sigil(evidence)},
        "actor": {"kind": "AGENT", "actor_id": "ACTOR", "authentication_context_sigil": SIGIL, "actor_sigil": ""}, "host_invocation": {"host_identity_sigil": SIGIL, "invocation_id": "INVOCATION", "authentication_context_sigil": SIGIL, "invocation_sigil": ""}, "chronicle_actor": {"actor_id": "ACTOR", "actor_type": "agent", "host": "codex", "authenticated_by": "MCP"}, "requested_at": "2026-08-06T00:00:00Z", "authorization_sigil": "",
    }
    authorization["transition_request_id"] = "ATR-" + content_sigil(["agent-result-acceptance-transition-id/1.0", result["task_id"], SIGIL]).removeprefix("sha256:").upper()
    authorization["actor"]["actor_sigil"] = content_sigil({key: value for key, value in authorization["actor"].items() if key != "actor_sigil"})  # type: ignore[index,union-attr]
    authorization["host_invocation"]["invocation_sigil"] = content_sigil({key: value for key, value in authorization["host_invocation"].items() if key != "invocation_sigil"})  # type: ignore[index,union-attr]
    authorization["authorization_sigil"] = content_sigil({key: value for key, value in authorization.items() if key != "authorization_sigil"})
    return authorization


def _request() -> dict[str, object]:
    result = _seal_result(_result())
    authorization = _authorization(result)
    request: dict[str, object] = {"schema_version": "agent-result-acceptance-transition-request/1.0", "transition_request_id": authorization["transition_request_id"], "event_type": "agent-result.accepted", "expected_chronicle_head": authorization["expected_chronicle_head"], "agent_result": result, "job_outcome_binding": result["job_outcome_binding"], "acceptance_request_sigil": SIGIL, "idempotency_key_sigil": SIGIL, "reference_sets": authorization["reference_sets"], "managed_blob_sigils": authorization["managed_blob_sigils"], "acceptance_storage_binding": authorization["acceptance_storage_binding"], "actor": authorization["actor"], "host_invocation": authorization["host_invocation"], "chronicle_actor": authorization["chronicle_actor"], "acceptance_authorization": authorization, "authorization_sigil": authorization["authorization_sigil"], "requested_at": authorization["requested_at"], "transition_request_sigil": ""}
    request["transition_request_sigil"] = content_sigil({key: value for key, value in request.items() if key != "transition_request_sigil"})
    return request


def test_agent_result_v2_local_closure_rejects_reordered_outputs_and_pending_authorization() -> None:
    result = _seal_result(_result())
    validate_agent_result_v2(result)
    pending = deepcopy(result)
    pending["provenance"]["attempt_authorization_state"] = {"kind": "PENDING"}  # type: ignore[index]
    pending["result_sigil"] = content_sigil({key: value for key, value in pending.items() if key != "result_sigil"})
    with pytest.raises(AthanorError, match="pending"):
        validate_agent_result_v2(pending)
    unordered = deepcopy(result)
    unordered["outputs"] = list(reversed(unordered["outputs"]))  # type: ignore[index]
    unordered["result_sigil"] = content_sigil({key: value for key, value in unordered.items() if key != "result_sigil"})
    with pytest.raises(AthanorError, match="ordered"):
        validate_agent_result_v2(unordered)


def test_transition_request_requires_exact_authorization_and_result_bindings() -> None:
    request = _request()
    validate_agent_result_acceptance_transition_request_v1(request)
    mismatch = deepcopy(request)
    mismatch["managed_blob_sigils"] = ["sha256:" + "c" * 64]
    mismatch["transition_request_sigil"] = content_sigil({key: value for key, value in mismatch.items() if key != "transition_request_sigil"})
    with pytest.raises(AthanorError, match="managed_blob_sigils"):
        validate_agent_result_acceptance_transition_request_v1(mismatch)


def test_agent_result_record_v2_receipt_domain_is_closed() -> None:
    record = {"schema_version": "agent-result-record/2.0", "task_id": "TK-ONE", "program_id": "RP-ONE", "task_capsule_sigil": SIGIL, "host_identity_sigil": SIGIL, "capability_binding": _result()["capability_binding"], "snapshot_binding": _result()["snapshot_binding"], "job_binding": _result()["job_binding"], "execution_specification_binding": _result()["execution_specification_binding"], "job_outcome_binding": _result()["job_outcome_binding"], "terminal_event_sigil": SIGIL, "selected_attempt_id": "AT-" + "0" * 26, "assurance_claim_sigil": SIGIL, "canonical_reference_binding": {"reference_intent_id": "RI-ONE", "reference_intent_record_sigil": SIGIL, "transition_request_id": "ATR-" + "A" * 64, "transition_request_sigil": SIGIL, "acceptance_storage_binding": _authorization(_seal_result(_result()))["acceptance_storage_binding"], "reference_set_id": "RS-ONE", "reference_set_sigil": SIGIL}, "terminal_source_binding": {"kind": "NOT_APPLICABLE"}, "outputs": _result()["outputs"], "provenance": _result()["provenance"], "status": "COMPLETED", "agent_result_sigil": SIGIL, "accepted_at": "2026-08-06T00:00:00Z", "acceptance_receipt": "RC-ABC1"}
    validate_instance("agent-result-record-2.0.json", record)
    record["acceptance_receipt"] = "RC-lower.case"
    with pytest.raises(AthanorError, match="validation failed"):
        validate_instance("agent-result-record-2.0.json", record)
