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
    load_execution_observation_evidence_v1,
    load_execution_request_v1,
    load_execution_result_ingress_receipt_v1,
    load_execution_state_v1,
    validate_execution_observation_evidence_v1,
    validate_execution_observation_evidence_supplied_receipt_v1,
    validate_execution_request_v1,
    validate_execution_result_ingress_receipt_v1,
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
    assert schema["$defs"]["idempotency_operation_kind"]["enum"] == list(
        IDEMPOTENCY_OPERATION_KINDS_V1
    )
    raw = (FIXTURES / "execution-state-v1" / "invalid-duplicate-key.json").read_text()
    with pytest.raises(Exception, match="duplicate JSON key"):
        load_execution_state_v1(raw)


def test_rfc0015_request_loaders_are_strict_and_cursor_bound_to_fixed_prefix() -> None:
    cursor = {
        "job_id": JOB_ID,
        "last_returned_sequence": 2,
        "through_journal_sequence": 3,
        "through_event_sigil": SIGIL,
    }
    cursor["cursor_sigil"] = derive_execution_observation_cursor_sigil_v1(cursor)
    observe = {
        "schema_version": "execution-observe-request/1.0",
        "job_id": JOB_ID,
        "limit": 2,
        "cursor": cursor,
    }
    validate_execution_request_v1("observe", observe)
    assert load_execution_request_v1("observe", json.dumps(observe)) == observe
    for raw in (
        b'\xef\xbb\xbf{}',
        b'{"schema_version":"execution-observe-request/1.0","limit":1,"limit":2}',
    ):
        with pytest.raises(Exception):
            load_execution_request_v1("observe", raw)
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


def test_state_rejects_split_policy_legacy_shapes_unknowns_and_duplicate_bytes() -> None:
    raw = (FIXTURES / "execution-state-v1" / "invalid-duplicate-key.json").read_text()
    with pytest.raises(Exception, match="duplicate JSON key"):
        load_execution_state_v1(raw)
    with pytest.raises(Exception, match="BOM"):
        load_execution_state_v1(b"\xef\xbb\xbf{}")


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
    raw = (FIXTURES / "execution-journal-event-v1" / "invalid-duplicate-key.json").read_text()
    with pytest.raises(Exception, match="duplicate JSON key"):
        load_execution_journal_event_v1(raw)

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

    mismatched_assessment = deepcopy(evidence)
    mismatched_assessment["assessment"]["verified_runtime_observation"] = {
        **mismatched_assessment["assessment"]["verified_runtime_observation"],
        "process_count": 1,
    }
    _reseal_evidence(mismatched_assessment)
    with pytest.raises(Exception, match="copy the Result observation"):
        validate_execution_observation_evidence_v1(mismatched_assessment)

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
