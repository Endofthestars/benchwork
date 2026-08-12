import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.execution_job_outcome import (
    derive_execution_job_outcome_derivation_profile_v1,
    derive_execution_job_outcome_id_v1,
    derive_execution_job_outcome_sigil_v1,
    execution_job_outcome_algorithm_sigil_v1,
    execution_job_outcome_imported_schema_set_v1,
    load_execution_job_outcome_v1,
    require_execution_job_outcome_acceptance_eligibility_authority_v1,
    require_execution_job_outcome_journal_derivation_v1,
    require_execution_job_outcome_runtime_authority_v1,
    validate_execution_job_outcome_fixed_retry_v1,
    validate_execution_job_outcome_replayed_facts_v1,
    validate_execution_job_outcome_v1,
)
from benchwork.schema_validation import validate_instance


ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "schemas" / "execution-job-outcome-1.0.json"
FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "phase3"
    / "rfc0015"
    / "execution-job-outcome-v1"
    / "valid-no-attempt.json"
)
OS_FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "phase3"
    / "rfc0012"
    / "execution-output-storage-observation-set-v1"
    / "valid-minimal.json"
)
DERIVED_MEMBERS = {
    "schema_version",
    "outcome_id",
    "acceptance_eligible",
    "ineligibility_reasons",
    "derivation_profile",
    "outcome_sigil",
}


def _load() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _seal(outcome: dict[str, Any]) -> dict[str, Any]:
    outcome["outcome_id"] = derive_execution_job_outcome_id_v1(
        outcome["job_id"], outcome["job_terminal"]["event_sigil"]
    )
    outcome["derivation_profile"] = derive_execution_job_outcome_derivation_profile_v1()
    outcome["outcome_sigil"] = derive_execution_job_outcome_sigil_v1(outcome)
    return outcome


def _facts(outcome: dict[str, Any]) -> dict[str, Any]:
    facts = {
        key: deepcopy(value)
        for key, value in outcome.items()
        if key not in DERIVED_MEMBERS
    }
    facts["expected_ineligibility_reasons"] = deepcopy(
        outcome["ineligibility_reasons"]
    )
    facts["output_storage_observation_set"] = None
    return facts


def _selected() -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a contract-only selected-Attempt Outcome from frozen fixtures."""
    outcome = _load()
    observation = json.loads(OS_FIXTURE.read_text(encoding="utf-8"))
    sigil = "sha256:" + "d" * 64
    attempt_id = observation["attempt_id"]
    attempt_sigil = observation["attempt_binding_sigil"]
    worker = {"kind": "NONE"}
    authorization = {"kind": "NONE"}
    storage_binding = {
        "kind": "FROZEN",
        "storage_journal_id": observation["storage_event"]["journal_id"],
        "through_sequence": observation["storage_event"]["sequence"],
        "through_event_sigil": observation["storage_event"]["event_sigil"],
        "output_storage_observation_set_id": observation["observation_set_id"],
        "output_storage_observation_set_sigil": observation["observation_set_sigil"],
    }
    first_stop = {
        "kind": "PRESENT", "event_id": "JE-STOP", "event_type": "attempt.failed",
        "event_sigil": "sha256:" + "8" * 64, "effective_sequence": 8,
    }
    summary = {
        "attempt_id": attempt_id, "attempt_binding_sigil": attempt_sigil,
        "retry_ordinal": 1, "terminal_state": "FAILED",
        "terminal_event_id": "JE-ATTEMPTFAILED", "terminal_event_sigil": "sha256:" + "9" * 64,
        "worker_session_binding": worker,
        "attempt_authorization_requirement": {"kind": "NONE", "effects": []},
        "attempt_authorization_state": authorization,
        "budget_settlement_event_sigil": "sha256:" + "a" * 64,
        "assurance_evaluation_event_sigil": "sha256:" + "b" * 64,
    }
    selected = {
        "kind": "SELECTED", "attempt_id": attempt_id, "attempt_binding_sigil": attempt_sigil,
        "attempt_terminal_event_id": summary["terminal_event_id"],
        "attempt_terminal_event_sigil": summary["terminal_event_sigil"],
        "attempt_authorization_state": authorization, "worker_session_binding": worker,
        "result_binding": observation["result_binding"],
        "completion_anchor_binding": {"kind": "NOT_ESTABLISHED"},
        "first_stop_or_fence_binding": first_stop,
        "storage_observation_binding": storage_binding,
    }
    outcome["job_terminal"] = {
        **outcome["job_terminal"], "job_revision": 12, "event_id": "JE-JOBFAILED",
        "event_sequence": 12, "event_sigil": "sha256:" + "f" * 64,
    }
    outcome["attempt_summaries"] = [summary]
    outcome["selected_attempt_binding"] = selected
    outcome["result_binding"] = selected["result_binding"]
    outcome["completion_anchor_binding"] = selected["completion_anchor_binding"]
    outcome["first_stop_or_fence_binding"] = first_stop
    outcome["lease_terminal_binding"] = {"kind": "NONE"}
    outcome["authority_binding"] = {
        "kind": "ASSIGNED_NO_LEASE", "allocation_executor_instance_id": "XI-ONE",
        "allocation_executor_epoch": 1, "allocation_executor_build_sigil": sigil,
        "job_id": outcome["job_id"], "attempt_id": attempt_id, "fencing_generation": 1,
    }
    outcome["final_fence_binding"] = {
        "kind": "ASSIGNED_NO_LEASE", "final_fence_floor": 1, "attempt_id": attempt_id,
        "attempt_terminal_event_sigil": summary["terminal_event_sigil"],
    }
    outcome["runtime_outcome"] = {
        "kind": "ATTEMPT", "computation_status": "FAILED", "worker_status": "FAILED",
        "process_termination_status": "EXITED", "handle_revocation_status": "NOT_APPLICABLE",
        "cleanup_status": "VERIFIED", "mutable_resource_isolation_status": "VERIFIED_ISOLATED",
        "output_publication_status": "FAILED", "quarantine_status": "NOT_REQUIRED",
        "termination_evidence_sigil": sigil, "handle_disposition_evidence_sigil": sigil,
        "cleanup_summary_sigil": sigil, "quarantine_evidence_sigil": sigil,
        "log_closure_sigil": observation["log_closure_sigil"],
        "output_closure_sigil": observation["output_closure_sigil"],
        "accounting_capture_event_id": "JE-ACCOUNTING", "accounting_capture_event_sigil": sigil,
    }
    outcome["terminal_source_binding"] = observation["terminal_source_binding"]
    outcome["terminal_source_observation"] = observation["members"][-1]
    outcome["assurance_context_binding"] = {
        **{key: value for key, value in outcome["assurance_context_binding"].items() if key != "kind"},
        "kind": "ATTEMPT", "backend_identity": "local-backend",
        "backend_configuration_sigil": sigil, "host_identity_sigil": sigil,
    }
    outcome["attempt_assurance_binding"] = {
        "kind": "UNMET", "evaluation_event_id": "JE-ATTEMPTASSURANCE",
        "evaluation_event_sigil": summary["assurance_evaluation_event_sigil"],
        "evaluation_sequence": 10, "reason_codes": ["ASSURANCE_UNMET"], "evidence_set_sigil": sigil,
    }
    outcome["job_assurance_binding"] = {
        "kind": "UNMET", "evaluation_event_id": "JE-JOBASSURANCE",
        "evaluation_event_sigil": "sha256:" + "c" * 64, "evaluation_sequence": 11,
        "attempt_id": attempt_id,
        "attempt_assurance_event_sigil": summary["assurance_evaluation_event_sigil"],
        "reason_codes": ["ASSURANCE_UNMET"], "evidence_set_sigil": sigil,
    }
    for member in (
        "control_evidence_set_binding", "quarantine_binding_set_binding",
        "terminalization_storage_manifest_binding", "output_root_protection",
    ):
        outcome[member] = observation[member]
    outcome["budget_binding"]["selected_attempt_settlement"] = {
        "kind": "SETTLED", "event_id": "JE-BUDGETSETTLED",
        "event_sigil": summary["budget_settlement_event_sigil"],
        "accounting_capture_event_id": "JE-ACCOUNTING", "accounting_capture_event_sigil": sigil,
        "usage_status": "MEASURED",
    }
    outcome["outputs"] = observation["members"][:1]
    outcome["logs"] = observation["members"][1:4]
    outcome["resource_evidence"] = observation["members"][4:5]
    outcome["storage_observation_binding"] = storage_binding
    outcome["ineligibility_reasons"] = [
        "JOB_NOT_SUCCEEDED", "ATTEMPT_NOT_SUCCEEDED", "COMPLETION_NOT_ESTABLISHED",
        "OUTPUT_INVALID", "ASSURANCE_UNMET", "STORAGE_OBSERVATION_INVALID",
    ]
    outcome["terminal_recorded_at"] = "2026-08-06T00:00:12Z"
    return _seal(outcome), observation


def test_valid_no_attempt_fixture_and_strict_loader() -> None:
    outcome = _load()
    validate_execution_job_outcome_v1(outcome)
    assert load_execution_job_outcome_v1(FIXTURE.read_bytes()) == outcome
    validate_instance("execution-job-outcome-1.0.json", outcome)


def test_budget_ledger_requires_exact_arithmetic_status_and_self_sigil() -> None:
    outcome = _load()
    ledger = outcome["budget_binding"]["job_budget_ledger"]
    assert ledger["budget_ledger_sigil"] == content_sigil(
        {key: value for key, value in ledger.items() if key != "budget_ledger_sigil"}
    )

    wrong_status = deepcopy(outcome)
    wrong_status["budget_binding"]["job_budget_ledger"]["attempts"]["exhaustion_status"] = "EXHAUSTED"
    _seal(wrong_status)
    with pytest.raises(Exception, match="budget ledger self-Sigil"):
        validate_execution_job_outcome_v1(wrong_status)

    arithmetic_mismatch = deepcopy(outcome)
    arithmetic_mismatch["budget_binding"]["job_budget_ledger"]["attempts"]["exhaustion_status"] = "EXHAUSTED"
    ledger = arithmetic_mismatch["budget_binding"]["job_budget_ledger"]
    ledger["budget_ledger_sigil"] = content_sigil(
        {key: value for key, value in ledger.items() if key != "budget_ledger_sigil"}
    )
    _seal(arithmetic_mismatch)
    with pytest.raises(Exception, match="incorrect exhaustion status"):
        validate_execution_job_outcome_v1(arithmetic_mismatch)


def test_schema_has_exact_closed_root_and_public_rfc0014_defs() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$id"] == "https://benchwork.dev/schemas/execution-job-outcome/1.0"
    assert schema["additionalProperties"] is False
    assert len(schema["required"]) == len(schema["properties"]) == 40
    assert set(schema["required"]) == set(schema["properties"])
    for public_definition in (
        "authority_binding",
        "assurance_context_binding",
        "worker_session_binding",
    ):
        assert public_definition in schema["$defs"]


def test_schema_imports_owner_defs_without_unpublished_result_schema() -> None:
    source = SCHEMA_PATH.read_text(encoding="utf-8")
    assert "execution-result/1.0" not in source
    for reference in (
        "execution-state/1.0#/$defs/public_fence_tuple",
        "execution-journal-event/1.0#/$defs/attempt_summary",
        "execution-journal-event/1.0#/$defs/result_binding",
        "execution-output-storage-observation-set/1.0#/$defs/attempt_output_member",
        "execution-output-storage-observation-set/1.0#/$defs/log_stream_member",
        "execution-output-storage-observation-set/1.0#/$defs/resource_evidence_member",
        "execution-output-storage-observation-set/1.0#/$defs/terminal_source_member",
    ):
        assert reference in source


def test_id_sigil_and_derivation_profile_known_answers() -> None:
    outcome = _load()
    assert outcome["outcome_id"] == (
        "OJ-D7AFDAE5DDE0D4F74D68AA4ACDBA07FB14FAAD4C9B96C3DB5536992BB62B3015"
    )
    assert outcome["outcome_sigil"] == derive_execution_job_outcome_sigil_v1(outcome)
    assert execution_job_outcome_algorithm_sigil_v1() == (
        "sha256:2bec4db5be71e36d9b5019b30e1d58a4990d2cc3ae6a8f0c124311195aca964f"
    )
    assert outcome["derivation_profile"] == (
        derive_execution_job_outcome_derivation_profile_v1()
    )


def test_imported_schema_set_is_complete_sorted_and_unique() -> None:
    imported = execution_job_outcome_imported_schema_set_v1()
    ids = [entry["schema_id"] for entry in imported]
    assert ids == sorted(ids, key=lambda item: item.encode("utf-8"))
    assert len(ids) == len(set(ids)) == 25
    assert all(set(entry) == {"schema_id", "schema_sigil"} for entry in imported)
    assert "https://benchwork.dev/schemas/execution-job-outcome/1.0" not in ids
    assert "https://benchwork.dev/schemas/execution-journal-event/1.0" in ids
    assert "https://benchwork.dev/schemas/execution-output-storage-observation-set/1.0" in ids


def test_no_attempt_matrix_and_directly_decidable_reasons_are_enforced() -> None:
    outcome = _load()
    assert outcome["attempt_summaries"] == []
    assert outcome["selected_attempt_binding"] == {"kind": "NONE"}
    assert outcome["authority_binding"] == {"kind": "NO_ATTEMPT"}
    assert outcome["final_fence_binding"] == {
        "kind": "NO_ATTEMPT",
        "final_fence_floor": 0,
    }
    assert outcome["runtime_outcome"]["kind"] == "NO_ATTEMPT"
    assert outcome["outputs"] == outcome["logs"] == outcome["resource_evidence"] == []
    assert outcome["ineligibility_reasons"] == [
        "JOB_NOT_SUCCEEDED",
        "ATTEMPT_ABSENT",
    ]

    missing_reason = deepcopy(outcome)
    missing_reason["ineligibility_reasons"] = ["ATTEMPT_ABSENT"]
    _seal(missing_reason)
    with pytest.raises(AthanorError, match="JOB_NOT_SUCCEEDED"):
        validate_execution_job_outcome_v1(missing_reason)

    wrong_runtime = deepcopy(outcome)
    wrong_runtime["runtime_outcome"]["worker_status"] = "FAILED"
    _seal(wrong_runtime)
    with pytest.raises(AthanorError):
        validate_execution_job_outcome_v1(wrong_runtime)


def test_selected_attempt_direct_copies_and_observation_reconstruction() -> None:
    outcome, observation = _selected()
    validate_execution_job_outcome_v1(outcome)
    facts = _facts(outcome)
    facts["output_storage_observation_set"] = observation
    validate_execution_job_outcome_replayed_facts_v1(outcome, facts)
    assert [member["stream"] for member in outcome["logs"]] == [
        "STDOUT", "STDERR", "STRUCTURED",
    ]
    assert [
        *outcome["outputs"], *outcome["logs"], *outcome["resource_evidence"],
        outcome["terminal_source_observation"],
    ] == observation["members"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("selected_copy", "direct result_binding"),
        ("authority_job", "authority bindings disagree"),
        ("final_fence", "authority bindings disagree"),
        ("manifest_copy", "frozen manifest"),
        ("terminal_source", "terminal-source observation"),
    ],
)
def test_selected_cross_object_equalities_fail_closed(mutation: str, message: str) -> None:
    outcome, _ = _selected()
    if mutation == "selected_copy":
        outcome["result_binding"] = {
            "kind": "REJECTED", "message_sigil": "sha256:" + "1" * 64,
            "disposition_event_id": "JE-REJECTED", "disposition_event_sigil": "sha256:" + "2" * 64,
            "disposition_sequence": 6, "reason_codes": ["RESULT_CONFLICT"],
        }
    elif mutation == "authority_job":
        outcome["authority_binding"]["job_id"] = "JB-" + "B" * 64
    elif mutation == "final_fence":
        outcome["final_fence_binding"]["final_fence_floor"] = 2
    elif mutation == "manifest_copy":
        outcome["output_root_protection"]["terminalization_storage_manifest_binding"][
            "storage_root_manifest_sigil"
        ] = "sha256:" + "0" * 64
    else:
        outcome["terminal_source_observation"] = {
            "kind": "TERMINAL_SOURCE_NONE", "reason_codes": ["SOURCE_ABSENT"],
        }
    _seal(outcome)
    with pytest.raises(AthanorError, match=message):
        validate_execution_job_outcome_v1(outcome)


@pytest.mark.parametrize(
    "reason",
    ("COMPLETION_NOT_ESTABLISHED", "OUTPUT_INVALID", "ASSURANCE_UNMET", "STORAGE_OBSERVATION_INVALID"),
)
def test_selected_outcome_cannot_omit_a_locally_required_reason(reason: str) -> None:
    outcome, _ = _selected()
    outcome["ineligibility_reasons"].remove(reason)
    _seal(outcome)
    with pytest.raises(AthanorError, match=reason):
        validate_execution_job_outcome_v1(outcome)


def test_reason_order_and_eligibility_equivalence_are_enforced() -> None:
    outcome = _load()
    reversed_reasons = deepcopy(outcome)
    reversed_reasons["ineligibility_reasons"].reverse()
    _seal(reversed_reasons)
    with pytest.raises(AthanorError, match="canonical order"):
        validate_execution_job_outcome_v1(reversed_reasons)

    wrong_eligibility = deepcopy(outcome)
    wrong_eligibility["acceptance_eligible"] = True
    _seal(wrong_eligibility)
    with pytest.raises(AthanorError):
        validate_execution_job_outcome_v1(wrong_eligibility)


def test_supplied_facts_compare_every_nonderived_field_but_grant_no_authority() -> None:
    outcome = _load()
    facts = _facts(outcome)
    validate_execution_job_outcome_replayed_facts_v1(outcome, facts)

    wrong = deepcopy(facts)
    wrong["terminal_recorded_at"] = "2026-08-06T00:00:04Z"
    with pytest.raises(AthanorError, match="terminal_recorded_at"):
        validate_execution_job_outcome_replayed_facts_v1(outcome, wrong)

    extra = deepcopy(facts)
    extra["journal_is_current"] = True
    with pytest.raises(AthanorError, match="exact closed field set"):
        validate_execution_job_outcome_replayed_facts_v1(outcome, extra)


def test_retry_requires_same_id_and_identical_canonical_record() -> None:
    outcome = _load()
    validate_execution_job_outcome_fixed_retry_v1(outcome, deepcopy(outcome))

    changed = deepcopy(outcome)
    changed["terminal_recorded_at"] = "2026-08-06T00:00:04Z"
    _seal(changed)
    with pytest.raises(AthanorError, match="byte-for-byte"):
        validate_execution_job_outcome_fixed_retry_v1(outcome, changed)

    different = deepcopy(outcome)
    different["job_terminal"]["event_sigil"] = "sha256:" + "0" * 64
    _seal(different)
    with pytest.raises(AthanorError, match="identity"):
        validate_execution_job_outcome_fixed_retry_v1(outcome, different)


@pytest.mark.parametrize(
    "raw",
    [
        b'\xff\xfe{\x00}\x00',
        b'{"schema_version":"execution-job-outcome/1.0","schema_version":"x"}',
        b'[]',
        b'{} trailing',
        b'{"x":NaN}',
    ],
)
def test_strict_loader_rejects_noncanonical_json_inputs(raw: bytes) -> None:
    with pytest.raises(AthanorError):
        load_execution_job_outcome_v1(raw)


@pytest.mark.parametrize(
    "guard",
    [
        require_execution_job_outcome_journal_derivation_v1,
        require_execution_job_outcome_acceptance_eligibility_authority_v1,
        require_execution_job_outcome_runtime_authority_v1,
    ],
)
def test_contract_only_authority_surfaces_fail_closed(guard: Any) -> None:
    with pytest.raises(AthanorError):
        guard()
