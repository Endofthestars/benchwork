"""Pure RFC-0015 Execution Job Outcome contract helpers.

This module validates the closed public record and facts decidable from one
supplied Outcome.  It does not replay an Execution Journal, resolve current
storage or control records, decide acceptance eligibility from live evidence,
accept a Result, or grant execution or scientific authority.
"""

from __future__ import annotations

import hashlib
import math
import unicodedata
from typing import Any, NoReturn
from urllib.parse import urldefrag

from .athanor import AthanorError, canonical_json, content_sigil
from .execution_contracts import validate_execution_budget_ledger_v1
from .schema_validation import validate_instance


_SCHEMA_NAME = "execution-job-outcome-1.0.json"
_SCHEMA_ID = "https://benchwork.dev/schemas/execution-job-outcome/1.0"
_ROOT_MEMBERS = {
    "schema_version",
    "outcome_id",
    "job_id",
    "job_binding_sigil",
    "job_terminal",
    "task_binding",
    "program_id",
    "capability_binding",
    "snapshot_binding",
    "circle_binding",
    "approval_binding",
    "execution_specification_binding",
    "attempt_summaries",
    "selected_attempt_binding",
    "result_binding",
    "completion_anchor_binding",
    "first_stop_or_fence_binding",
    "lease_terminal_binding",
    "authority_binding",
    "final_fence_binding",
    "runtime_outcome",
    "terminal_source_binding",
    "terminal_source_observation",
    "assurance_context_binding",
    "attempt_assurance_binding",
    "job_assurance_binding",
    "control_evidence_set_binding",
    "quarantine_binding_set_binding",
    "terminalization_storage_manifest_binding",
    "output_root_protection",
    "budget_binding",
    "outputs",
    "storage_observation_binding",
    "logs",
    "resource_evidence",
    "acceptance_eligible",
    "ineligibility_reasons",
    "derivation_profile",
    "terminal_recorded_at",
    "outcome_sigil",
}
_DERIVED_MEMBERS = {
    "schema_version",
    "outcome_id",
    "acceptance_eligible",
    "ineligibility_reasons",
    "derivation_profile",
    "outcome_sigil",
}
_REPLAY_FACT_MEMBERS = (_ROOT_MEMBERS - _DERIVED_MEMBERS) | {
    "expected_ineligibility_reasons",
    "output_storage_observation_set",
}
_REASON_ORDER = (
    "JOB_NOT_SUCCEEDED",
    "ATTEMPT_ABSENT",
    "ATTEMPT_NOT_SUCCEEDED",
    "RESULT_REQUIREMENT_UNMET",
    "COMPLETION_NOT_ESTABLISHED",
    "AUTHORITY_LOST_BEFORE_COMPLETION",
    "ATTEMPT_AUTHORIZATION_INVALID",
    "WORKER_SESSION_EVIDENCE_MISSING",
    "LEASE_TERMINAL_EVIDENCE_MISSING",
    "FINAL_FENCE_EVIDENCE_MISSING",
    "BUDGET_UNSETTLED",
    "BUDGET_EXCEEDED",
    "ACCOUNTING_UNVERIFIED",
    "TERMINATION_UNVERIFIED",
    "HANDLE_REVOCATION_UNVERIFIED",
    "CLEANUP_UNVERIFIED",
    "MUTABLE_RESOURCE_UNSAFE",
    "OUTPUT_INVALID",
    "OUTPUT_UNAVAILABLE",
    "OUTPUT_QUARANTINED",
    "TERMINAL_SOURCE_INVALID",
    "TERMINAL_SOURCE_QUARANTINED",
    "ASSURANCE_UNMET",
    "ASSURANCE_UNVERIFIABLE",
    "CONTROL_EVIDENCE_INVALID",
    "STORAGE_OBSERVATION_INVALID",
    "INTEGRITY_FAILURE",
)
_REASON_RANK = {reason: rank for rank, reason in enumerate(_REASON_ORDER)}
_ALGORITHM_PREIMAGE = [
    "execution-job-outcome-derivation-algorithm/1.0",
    "VALIDATE_SOURCE_PREFIX",
    "COPY_CLOSED_BINDINGS",
    "RECONSTRUCT_SELECTED_OBSERVATION",
    "EVALUATE_ALL_REASONS_IN_ENUM_ORDER",
    "SET_ELIGIBLE_IFF_EMPTY",
    "DERIVE_OJ_ID",
    "DERIVE_OUTCOME_SIGIL",
]
_NO_ATTEMPT_RUNTIME = {
    "kind": "NO_ATTEMPT",
    "computation_status": "NOT_STARTED",
    "worker_status": "NOT_REPORTED",
    "process_termination_status": "NOT_STARTED",
    "handle_revocation_status": "NOT_APPLICABLE",
    "cleanup_status": "NOT_APPLICABLE",
    "mutable_resource_isolation_status": "NOT_APPLICABLE",
    "output_publication_status": "NOT_APPLICABLE",
    "quarantine_status": "NOT_REQUIRED",
    "termination_evidence_sigil": None,
    "handle_disposition_evidence_sigil": None,
    "cleanup_summary_sigil": None,
    "quarantine_evidence_sigil": None,
    "log_closure_sigil": None,
    "output_closure_sigil": None,
    "accounting_capture_event_id": None,
    "accounting_capture_event_sigil": None,
}
_RESOURCE_PHASE_RANK = {
    value: rank
    for rank, value in enumerate(("PREFLIGHT", "RUNTIME", "TERMINATION", "CLEANUP"))
}
_RESOURCE_EVIDENCE_KIND_RANK = {
    value: rank
    for rank, value in enumerate(
        (
            "TASK_BINDING",
            "CAPABILITY_BINDING",
            "SNAPSHOT_BINDING",
            "WARD_DECISION",
            "APPROVAL_RECEIPT",
            "BACKEND_CONFIGURATION",
            "HOST_IDENTITY",
            "POLICY_RESOLUTION",
            "BASE_IDENTITY",
            "INPUT_IDENTITY",
            "MATERIALIZATION_IDENTITY",
            "ENVIRONMENT_CONSTRUCTION",
            "FILESYSTEM_POLICY",
            "NETWORK_POLICY",
            "EXECUTABLE_SELECTION",
            "PROCESS_TREE",
            "WALL_TIME_ENFORCEMENT",
            "RESOURCE_ACCOUNTING",
            "CREDENTIAL_NONINHERITANCE",
            "LOG_CAPTURE",
            "OUTPUT_VALIDATION",
            "STORAGE_OBSERVATION",
            "FENCE_TOMBSTONE",
            "TERMINATION",
            "HANDLE_REVOCATION",
            "CLEANUP",
            "QUARANTINE",
            "TERMINAL_SOURCE_VERIFICATION",
            "CONFORMANCE_FIXTURE",
        )
    )
}


def _fail(message: str) -> NoReturn:
    raise AthanorError(message)


def _validate_authority_equalities(outcome: dict[str, Any]) -> None:
    selected = outcome["selected_attempt_binding"]
    authority = outcome["authority_binding"]
    fence = outcome["final_fence_binding"]
    lease = outcome["lease_terminal_binding"]
    if authority["kind"] == "NO_ATTEMPT":
        return
    if selected["kind"] != "SELECTED":
        _fail("Outcome authority exists without a selected Attempt")
    if authority["kind"] == "ASSIGNED_NO_LEASE":
        if (
            authority["job_id"] != outcome["job_id"]
            or authority["attempt_id"] != selected["attempt_id"]
            or fence["attempt_id"] != selected["attempt_id"]
            or fence["attempt_terminal_event_sigil"]
            != selected["attempt_terminal_event_sigil"]
            or fence["final_fence_floor"] != authority["fencing_generation"]
        ):
            _fail("Outcome assigned-no-Lease authority bindings disagree")
        return

    public_fence = authority["public_fence_tuple"]
    if (
        authority["executor_epoch"] != public_fence["executor_epoch"]
        or public_fence["job_id"] != outcome["job_id"]
        or public_fence["attempt_id"] != selected["attempt_id"]
        or public_fence["lease_id"] != lease["lease_id"]
        or lease["lease_id"] != fence["lease_id"]
        or lease["terminal_event_sigil"] != fence["lease_terminal_event_sigil"]
        or lease["tombstone_event_sigil"] != fence["tombstone_event_sigil"]
        or lease["final_fence_floor"] != fence["final_fence_floor"]
        or public_fence["fencing_generation"] > fence["final_fence_floor"]
    ):
        _fail("Outcome leased authority, Lease terminal, or final fence bindings disagree")


def _validate_terminal_source_copy(outcome: dict[str, Any]) -> None:
    if outcome["selected_attempt_binding"]["kind"] == "NONE":
        return
    binding = outcome["terminal_source_binding"]
    observation = outcome["terminal_source_observation"]
    if binding["kind"] == "NOT_APPLICABLE":
        if observation != {"kind": "TERMINAL_SOURCE_NOT_APPLICABLE"}:
            _fail("Outcome terminal-source observation contradicts NOT_APPLICABLE")
        return
    nullable = (
        binding["terminal_source_identity"],
        binding["terminal_source_sigil"],
        binding["storage_blob"],
    )
    if binding["kind"] == "QUARANTINED" and nullable == (None, None, None):
        if observation != {
            "kind": "TERMINAL_SOURCE_NONE",
            "reason_codes": binding["reason_codes"],
        }:
            _fail("Outcome absent terminal-source observation contradicts its binding")
        return
    if any(value is None for value in nullable) or observation["kind"] != "TERMINAL_SOURCE":
        _fail("Outcome terminal-source observation has an invalid identity matrix")
    copied = (
        "terminal_source_identity",
        "terminal_source_sigil",
        "storage_blob",
        "retention_policy_sigil",
        "file_count",
        "byte_count",
    )
    if observation["disposition"] != binding["kind"] or any(
        observation[member] != binding[member] for member in copied
    ):
        _fail("Outcome terminal-source observation contradicts its direct binding")


def _validate_terminalization_copies(outcome: dict[str, Any]) -> None:
    if outcome["selected_attempt_binding"]["kind"] == "NONE":
        return
    protection = outcome["output_root_protection"]
    if (
        protection["terminalization_storage_manifest_binding"]
        != outcome["terminalization_storage_manifest_binding"]
    ):
        _fail("Outcome output-root protection contradicts its frozen manifest")


def _check_nfc_and_numbers(value: Any, label: str) -> None:
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            _fail(f"{label} contains a non-Unicode-scalar string")
        if unicodedata.normalize("NFC", value) != value:
            _fail(f"{label} contains a non-NFC string")
    elif isinstance(value, dict):
        for key, member in value.items():
            _check_nfc_and_numbers(key, label)
            _check_nfc_and_numbers(member, label)
    elif isinstance(value, list):
        for member in value:
            _check_nfc_and_numbers(member, label)
    elif isinstance(value, float):
        if not math.isfinite(value):
            _fail(f"{label} contains a non-finite JSON number")
        _fail(f"{label} contains a float where the closed wire permits no float")


def _load_strict_object(raw: str | bytes | bytearray) -> dict[str, Any]:
    from .execution_contracts import _load_strict_object as load_strict_object

    decoded: str
    if isinstance(raw, (bytes, bytearray)):
        encoded = bytes(raw)
        if encoded.startswith(
            (b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff", b"\xff\xfe\x00\x00")
        ):
            _fail("invalid Execution Job Outcome JSON: non-UTF-8 encoding is forbidden")
        try:
            decoded = encoded.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _fail("invalid Execution Job Outcome JSON: non-UTF-8 encoding is forbidden")
    else:
        decoded = raw
    return load_strict_object(decoded, "Execution Job Outcome")


def derive_execution_job_outcome_id_v1(job_id: str, terminal_event_sigil: str) -> str:
    """Derive the canonical OJ-ID from Job identity and terminal Event Sigil."""
    preimage = ["execution-job-outcome-id/1.0", job_id, terminal_event_sigil]
    digest = hashlib.sha256(canonical_json(preimage).encode("utf-8")).hexdigest().upper()
    return f"OJ-{digest}"


def derive_execution_job_outcome_sigil_v1(outcome: dict[str, Any]) -> str:
    """Derive the Outcome self-Sigil over every member except outcome_sigil."""
    return content_sigil(
        {key: value for key, value in outcome.items() if key != "outcome_sigil"}
    )


def execution_job_outcome_algorithm_sigil_v1() -> str:
    """Return the canonical RFC-0015 derivation-algorithm Sigil."""
    return content_sigil(_ALGORITHM_PREIMAGE)


def _resolve_pointer(document: Any, fragment: str) -> Any:
    if not fragment:
        return document
    if not fragment.startswith("/"):
        _fail(f"unsupported non-JSON-Pointer Schema fragment #{fragment}")
    current = document
    for token in fragment[1:].split("/"):
        decoded = token.replace("~1", "/").replace("~0", "~")
        try:
            current = current[int(decoded)] if isinstance(current, list) else current[decoded]
        except (KeyError, IndexError, ValueError, TypeError):
            _fail(f"unresolvable Schema fragment #{fragment}")
    return current


def execution_job_outcome_imported_schema_set_v1() -> list[dict[str, str]]:
    """Return every unique external Schema transitively reachable by ``$ref``."""
    from .schema_validation import _schemas

    schemas, _ = _schemas()
    by_id = {schema["$id"]: schema for schema in schemas.values()}
    try:
        root = schemas[_SCHEMA_NAME]
    except KeyError:
        _fail("installed execution-job-outcome/1.0 Schema is missing")

    imported: set[str] = set()
    visited: set[tuple[str, str]] = set()

    def walk(value: Any, document_id: str, location: str) -> None:
        visit_key = (document_id, location)
        if visit_key in visited:
            return
        visited.add(visit_key)
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str):
                base, fragment = urldefrag(reference)
                target_id = base or document_id
                if target_id not in by_id:
                    _fail(f"Outcome imports an unavailable Schema {target_id}")
                if target_id != _SCHEMA_ID:
                    imported.add(target_id)
                target = _resolve_pointer(by_id[target_id], fragment)
                walk(target, target_id, f"#{fragment}")
            for key, member in value.items():
                if key != "$ref":
                    walk(member, document_id, f"{location}/{key}")
        elif isinstance(value, list):
            for index, member in enumerate(value):
                walk(member, document_id, f"{location}/{index}")

    walk(root, _SCHEMA_ID, "#")
    return [
        {"schema_id": schema_id, "schema_sigil": content_sigil(by_id[schema_id])}
        for schema_id in sorted(imported, key=lambda item: item.encode("utf-8"))
    ]


def derive_execution_job_outcome_derivation_profile_v1() -> dict[str, str]:
    """Derive the one installed RFC-0015 Outcome profile."""
    from .schema_validation import _schemas

    schemas, _ = _schemas()
    try:
        schema = schemas[_SCHEMA_NAME]
    except KeyError:
        _fail("installed execution-job-outcome/1.0 Schema is missing")
    return {
        "profile_id": "execution-job-outcome-v1",
        "profile_version": "1.0",
        "algorithm_sigil": execution_job_outcome_algorithm_sigil_v1(),
        "outcome_schema_sigil": content_sigil(schema),
        "imported_schema_set_sigil": content_sigil(
            execution_job_outcome_imported_schema_set_v1()
        ),
    }


def _validate_attempt_selection(outcome: dict[str, Any]) -> None:
    summaries = outcome["attempt_summaries"]
    ordinals = [row["retry_ordinal"] for row in summaries]
    if (
        any(ordinal < 1 for ordinal in ordinals)
        or ordinals != sorted(ordinals)
        or len(ordinals) != len(set(ordinals))
    ):
        _fail("Outcome Attempt summaries are not unique and ordered by retry ordinal")
    ids = [row["attempt_id"] for row in summaries]
    if len(ids) != len(set(ids)):
        _fail("Outcome Attempt summaries contain a duplicate Attempt identity")

    selected = outcome["selected_attempt_binding"]
    if not summaries:
        if selected != {"kind": "NONE"}:
            _fail("Outcome without Attempt summaries must select NONE")
        return
    if selected["kind"] != "SELECTED":
        _fail("Outcome with Attempt summaries must select an Attempt")
    summary = summaries[-1]
    copied = {
        "attempt_id": "attempt_id",
        "attempt_binding_sigil": "attempt_binding_sigil",
        "attempt_terminal_event_id": "terminal_event_id",
        "attempt_terminal_event_sigil": "terminal_event_sigil",
        "attempt_authorization_state": "attempt_authorization_state",
        "worker_session_binding": "worker_session_binding",
    }
    for selected_member, summary_member in copied.items():
        if selected[selected_member] != summary[summary_member]:
            _fail(f"Outcome selected Attempt contradicts summary {summary_member}")
    for member in (
        "result_binding",
        "completion_anchor_binding",
        "first_stop_or_fence_binding",
        "storage_observation_binding",
    ):
        if outcome[member] != selected[member]:
            _fail(f"Outcome direct {member} does not equal the selected Attempt copy")


def _validate_no_attempt_matrix(outcome: dict[str, Any]) -> None:
    if outcome["attempt_summaries"]:
        return
    exact = {
        "result_binding": {"kind": "NONE"},
        "completion_anchor_binding": {"kind": "NOT_ESTABLISHED"},
        "lease_terminal_binding": {"kind": "NONE"},
        "authority_binding": {"kind": "NO_ATTEMPT"},
        "final_fence_binding": {"kind": "NO_ATTEMPT", "final_fence_floor": 0},
        "runtime_outcome": _NO_ATTEMPT_RUNTIME,
        "terminal_source_observation": {"kind": "NO_ATTEMPT"},
        "attempt_assurance_binding": {"kind": "NONE"},
        "control_evidence_set_binding": {"kind": "NOT_APPLICABLE"},
        "quarantine_binding_set_binding": {"kind": "NOT_APPLICABLE"},
        "terminalization_storage_manifest_binding": {"kind": "NOT_APPLICABLE"},
        "output_root_protection": {"kind": "NOT_APPLICABLE"},
        "storage_observation_binding": {"kind": "NOT_APPLICABLE"},
    }
    for member, expected in exact.items():
        if outcome[member] != expected:
            _fail(f"Outcome no-Attempt {member} is not the canonical branch")
    if outcome["job_assurance_binding"]["kind"] != "NOT_APPLICABLE":
        _fail("Outcome no-Attempt Job assurance is not NOT_APPLICABLE")
    for member in ("outputs", "logs", "resource_evidence"):
        if outcome[member]:
            _fail(f"Outcome no-Attempt {member} must be empty")
    if outcome["assurance_context_binding"]["kind"] != "NO_ATTEMPT":
        _fail("Outcome no-Attempt assurance context is not NO_ATTEMPT")
    if outcome["budget_binding"]["selected_attempt_settlement"] != {"kind": "NONE"}:
        _fail("Outcome no-Attempt budget settlement is not NONE")


def _validate_selected_observation_groups(outcome: dict[str, Any]) -> None:
    if not outcome["attempt_summaries"]:
        return
    if outcome["runtime_outcome"]["kind"] != "ATTEMPT":
        _fail("Outcome selected Attempt lacks ATTEMPT runtime evidence")
    if outcome["assurance_context_binding"]["kind"] != "ATTEMPT":
        _fail("Outcome selected Attempt lacks ATTEMPT assurance context")
    if outcome["attempt_assurance_binding"]["kind"] in {"NONE", "PENDING"}:
        _fail("Outcome selected Attempt lacks terminal Attempt assurance")
    if outcome["job_assurance_binding"]["kind"] in {"NOT_APPLICABLE", "PENDING"}:
        _fail("Outcome selected Attempt lacks terminal Job assurance")
    for member in (
        "control_evidence_set_binding",
        "quarantine_binding_set_binding",
        "terminalization_storage_manifest_binding",
    ):
        if outcome[member]["kind"] != "FROZEN":
            _fail(f"Outcome selected Attempt {member} is not FROZEN")
    if outcome["output_root_protection"]["kind"] not in {"NO_HOLD", "HELD"}:
        _fail("Outcome selected Attempt output-root protection is not terminal")
    if outcome["budget_binding"]["selected_attempt_settlement"]["kind"] != "SETTLED":
        _fail("Outcome selected Attempt budget settlement is not SETTLED")

    outputs = outcome["outputs"]
    if not outputs:
        _fail("Outcome selected Attempt has no output observation group")
    output_kinds = [member["kind"] for member in outputs]
    if output_kinds == ["ATTEMPT_OUTPUTS_NONE"]:
        pass
    elif any(kind != "ATTEMPT_OUTPUT" for kind in output_kinds):
        _fail("Outcome output group mixes the NONE sentinel with output members")
    else:
        logical_names = [member["logical_name"] for member in outputs]
        if logical_names != sorted(logical_names, key=lambda item: item.encode("utf-8")):
            _fail("Outcome output observations are not ordered by logical_name")
        if len(logical_names) != len(set(logical_names)):
            _fail("Outcome output observations contain duplicate logical names")

    if [member["stream"] for member in outcome["logs"]] != [
        "STDOUT",
        "STDERR",
        "STRUCTURED",
    ]:
        _fail("Outcome selected Attempt must expose exactly three ordered Log streams")

    resources = outcome["resource_evidence"]
    if resources[0]["kind"] == "RESOURCE_EVIDENCE":
        keys = [
            (
                member["control_evidence_id"],
                _RESOURCE_PHASE_RANK[member["phase"]],
                _RESOURCE_EVIDENCE_KIND_RANK[member["evidence_kind"]],
                member["phase_evidence_entry_sigil"],
            )
            for member in resources
        ]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            _fail("Outcome resource-evidence observations are not sorted and unique")
    if len(outputs) + len(outcome["logs"]) + len(resources) + 1 > 4096:
        _fail("Outcome observation-member reconstruction exceeds 4096 members")


def _validate_reason_order_and_local_predicates(outcome: dict[str, Any]) -> None:
    reasons = outcome["ineligibility_reasons"]
    if reasons != sorted(reasons, key=_REASON_RANK.__getitem__) or len(reasons) != len(
        set(reasons)
    ):
        _fail("Outcome ineligibility reasons are not unique and in canonical order")
    if outcome["acceptance_eligible"] != (reasons == []):
        _fail("Outcome acceptance eligibility does not equal an empty reason set")

    exact_predicates = {
        "JOB_NOT_SUCCEEDED": outcome["job_terminal"]["state"] != "SUCCEEDED",
        "ATTEMPT_ABSENT": outcome["selected_attempt_binding"]["kind"] == "NONE",
    }
    required_predicates: dict[str, bool] = {}
    selected_attempt_id = outcome["selected_attempt_binding"].get("attempt_id")
    required_predicates["ATTEMPT_AUTHORIZATION_INVALID"] = any(
        (
            summary["attempt_authorization_requirement"]["kind"] == "NONE"
            and summary["attempt_authorization_state"]["kind"] != "NONE"
        )
        or (
            summary["attempt_authorization_requirement"]["kind"] == "REQUIRED"
            and summary["attempt_authorization_state"]["kind"] == "NONE"
        )
        or (
            summary["attempt_authorization_state"]["kind"] == "PENDING"
            and (
                summary["attempt_id"] == selected_attempt_id
                or summary["terminal_state"] == "SUCCEEDED"
            )
        )
        for summary in outcome["attempt_summaries"]
    )
    if outcome["selected_attempt_binding"]["kind"] == "SELECTED":
        selected_id = outcome["selected_attempt_binding"]["attempt_id"]
        summary = next(row for row in outcome["attempt_summaries"] if row["attempt_id"] == selected_id)
        exact_predicates["ATTEMPT_NOT_SUCCEEDED"] = (
            summary["terminal_state"] != "SUCCEEDED"
        )
        completion = outcome["completion_anchor_binding"]
        result = outcome["result_binding"]
        if result["kind"] == "ACCEPTED":
            completion_invalid = completion["kind"] != "RESULT_ACCEPTED" or any(
                completion.get(completion_member) != result[result_member]
                for completion_member, result_member in (
                    ("event_id", "disposition_event_id"),
                    ("event_sigil", "disposition_event_sigil"),
                    ("sequence", "disposition_sequence"),
                    ("result_sigil", "result_sigil"),
                )
            )
        elif result["kind"] == "NONE":
            completion_invalid = completion["kind"] != "NO_RESULT"
        else:
            completion_invalid = True
        required_predicates["COMPLETION_NOT_ESTABLISHED"] = (
            completion_invalid
            or (
                completion["kind"] != "NOT_ESTABLISHED"
                and completion["sequence"] > outcome["job_terminal"]["event_sequence"]
            )
        )
        required_predicates["AUTHORITY_LOST_BEFORE_COMPLETION"] = (
            completion["kind"] != "NOT_ESTABLISHED"
            and outcome["first_stop_or_fence_binding"]["kind"] == "PRESENT"
            and outcome["first_stop_or_fence_binding"]["effective_sequence"]
            <= completion["sequence"]
        )
        selected_succeeded = summary["terminal_state"] == "SUCCEEDED"
        required_predicates["WORKER_SESSION_EVIDENCE_MISSING"] = (
            selected_succeeded
            and outcome["selected_attempt_binding"]["worker_session_binding"]["kind"]
            != "BOUND"
        )
        required_predicates["LEASE_TERMINAL_EVIDENCE_MISSING"] = (
            selected_succeeded and outcome["lease_terminal_binding"]["kind"] != "TERMINAL"
        )
    else:
        exact_predicates["ATTEMPT_NOT_SUCCEEDED"] = False
    exact_predicates["BUDGET_EXCEEDED"] = any(
        dimension["exhaustion_status"] == "EXCEEDED"
        for name, dimension in outcome["budget_binding"]["job_budget_ledger"].items()
        if name != "budget_ledger_sigil"
    )
    if outcome["selected_attempt_binding"]["kind"] == "SELECTED":
        runtime = outcome["runtime_outcome"]
        settlement = outcome["budget_binding"]["selected_attempt_settlement"]
        required_predicates["ACCOUNTING_UNVERIFIED"] = (
            settlement["usage_status"] != "MEASURED"
            or settlement["accounting_capture_event_id"]
            != runtime["accounting_capture_event_id"]
            or settlement["accounting_capture_event_sigil"]
            != runtime["accounting_capture_event_sigil"]
        )
        required_predicates["TERMINATION_UNVERIFIED"] = runtime[
            "process_termination_status"
        ] not in {"EXITED", "TERMINATED"}
        required_predicates["HANDLE_REVOCATION_UNVERIFIED"] = runtime[
            "handle_revocation_status"
        ] not in {"NOT_APPLICABLE", "REVOKED", "FENCED"}
        required_predicates["CLEANUP_UNVERIFIED"] = (
            runtime["cleanup_status"] != "VERIFIED"
        )
        exact_predicates["MUTABLE_RESOURCE_UNSAFE"] = runtime[
            "mutable_resource_isolation_status"
        ] not in {"NOT_APPLICABLE", "VERIFIED_ISOLATED"}
        outputs = outcome["outputs"]
        if outputs[0]["kind"] == "ATTEMPT_OUTPUTS_NONE":
            output_group_invalid = outputs[0]["reason"] != {
                "NONE": "NO_RESULT",
                "REJECTED": "RESULT_REJECTED",
                "ACCEPTED": "OUTPUT_ARRAY_EMPTY",
            }[result["kind"]]
        else:
            output_group_invalid = result["kind"] != "ACCEPTED"
        required_predicates["OUTPUT_INVALID"] = (
            runtime["output_publication_status"] == "FAILED"
            or output_group_invalid
            or any(
            member["kind"] == "ATTEMPT_OUTPUT"
            and (
                member["storage"]["kind"] == "NONE"
                or (
                    member["storage"]["kind"] == "BLOB"
                    and (
                        member["storage"]["blob_sigil"] != member["blob_sigil"]
                        or member["storage"]["size_bytes"] != member["byte_size"]
                    )
                )
            )
            for member in outputs
            )
        )
        output_storages = [
            member["storage"]
            for member in outputs
            if member["kind"] == "ATTEMPT_OUTPUT"
        ]
        required_predicates["OUTPUT_UNAVAILABLE"] = any(
            storage["kind"] == "QUARANTINE_TERMINAL_NEGATIVE"
            or (
                storage["kind"] == "BLOB"
                and (
                    storage["terminal_storage_status"] != "AVAILABLE"
                    or storage["availability"] != "AVAILABLE"
                    or storage["replica"]["kind"] != "SELECTED"
                )
            )
            for storage in output_storages
        )
        required_predicates["OUTPUT_QUARANTINED"] = (
            runtime["output_publication_status"] == "QUARANTINED"
            or any(storage["kind"] == "QUARANTINED" for storage in output_storages)
        )

        evidence_storages = [
            member["content"]["storage"] for member in outcome["logs"]
        ] + [
            member["storage"]
            for member in outcome["resource_evidence"]
            if member["kind"] == "RESOURCE_EVIDENCE"
        ]
        required_predicates["STORAGE_OBSERVATION_INVALID"] = any(
            storage["kind"] in {
                "NONE",
                "QUARANTINED",
                "QUARANTINE_TERMINAL_NEGATIVE",
            }
            or (
                storage["kind"] == "BLOB"
                and (
                    storage["terminal_storage_status"] != "AVAILABLE"
                    or storage["availability"] != "AVAILABLE"
                    or storage["replica"]["kind"] != "SELECTED"
                )
            )
            for storage in evidence_storages
        )
        all_storages = [*output_storages, *evidence_storages]
        terminal_observation = outcome["terminal_source_observation"]
        if terminal_observation["kind"] == "TERMINAL_SOURCE":
            all_storages.append(terminal_observation["storage"])
        required_predicates["INTEGRITY_FAILURE"] = any(
            storage["kind"] == "BLOB"
            and (
                storage["terminal_storage_status"] == "INCIDENT"
                or storage["availability"] == "INCIDENT"
            )
            for storage in all_storages
        )

    exact_predicates["TERMINAL_SOURCE_QUARANTINED"] = (
        outcome["terminal_source_binding"]["kind"] == "QUARANTINED"
        or (
            outcome["terminal_source_observation"]["kind"] == "TERMINAL_SOURCE"
            and outcome["terminal_source_observation"]["disposition"]
            == "QUARANTINED"
        )
    )
    required_predicates["ASSURANCE_UNMET"] = (
        outcome["attempt_assurance_binding"]["kind"] == "UNMET"
        or outcome["job_assurance_binding"]["kind"] == "UNMET"
    )
    exact_predicates["ASSURANCE_UNVERIFIABLE"] = (
        outcome["attempt_assurance_binding"]["kind"] == "UNVERIFIABLE"
        or outcome["job_assurance_binding"]["kind"] == "UNVERIFIABLE"
    )
    present = set(reasons)
    for reason, expected in exact_predicates.items():
        if (reason in present) != expected:
            _fail(f"Outcome reason {reason} contradicts its locally decidable predicate")
    for reason, required in required_predicates.items():
        if required and reason not in present:
            _fail(f"Outcome omits locally required reason {reason}")


def validate_execution_job_outcome_v1(outcome: dict[str, Any]) -> None:
    """Validate the RFC-0015 wire plus all locally decidable invariants."""
    validate_instance(_SCHEMA_NAME, outcome)
    if set(outcome) != _ROOT_MEMBERS:
        _fail("Execution Job Outcome is not the exact closed 40-member object")
    _check_nfc_and_numbers(outcome, "Execution Job Outcome")
    validate_execution_budget_ledger_v1(outcome["budget_binding"]["job_budget_ledger"])
    expected_id = derive_execution_job_outcome_id_v1(
        outcome["job_id"], outcome["job_terminal"]["event_sigil"]
    )
    if outcome["outcome_id"] != expected_id:
        _fail("Execution Job Outcome ID does not match the canonical preimage")
    if outcome["derivation_profile"] != derive_execution_job_outcome_derivation_profile_v1():
        _fail("Execution Job Outcome derivation profile is not the installed profile")
    if outcome["outcome_sigil"] != derive_execution_job_outcome_sigil_v1(outcome):
        _fail("Execution Job Outcome self-Sigil is invalid")
    _validate_attempt_selection(outcome)
    _validate_no_attempt_matrix(outcome)
    _validate_selected_observation_groups(outcome)
    _validate_authority_equalities(outcome)
    _validate_terminal_source_copy(outcome)
    _validate_terminalization_copies(outcome)
    _validate_reason_order_and_local_predicates(outcome)


def load_execution_job_outcome_v1(
    raw: str | bytes | bytearray,
) -> dict[str, Any]:
    """Strictly decode and validate one Execution Job Outcome."""
    outcome = _load_strict_object(raw)
    validate_execution_job_outcome_v1(outcome)
    return outcome


def validate_execution_job_outcome_fixed_retry_v1(
    prior: dict[str, Any], candidate: dict[str, Any]
) -> None:
    """Require one terminal Job prefix to produce identical canonical bytes."""
    validate_execution_job_outcome_v1(prior)
    validate_execution_job_outcome_v1(candidate)
    if prior["outcome_id"] != candidate["outcome_id"]:
        _fail("Execution Job Outcome retry changed deterministic Outcome identity")
    if canonical_json(prior) != canonical_json(candidate):
        _fail("Execution Job Outcome retry is not byte-for-byte deterministic")


def validate_execution_job_outcome_replayed_facts_v1(
    outcome: dict[str, Any], replayed_facts: dict[str, Any]
) -> None:
    """Compare an Outcome with a complete caller-supplied replay result.

    The caller remains responsible for authenticating and replaying the fixed
    Journal prefix and resolving every referenced immutable record.  Passing
    arbitrary dictionaries here grants no Journal, storage, acceptance,
    runtime, Result, or scientific authority.
    """
    validate_execution_job_outcome_v1(outcome)
    if set(replayed_facts) != _REPLAY_FACT_MEMBERS:
        _fail("Outcome replay facts do not have the exact closed field set")
    _check_nfc_and_numbers(replayed_facts, "Execution Job Outcome replay facts")
    for member in _ROOT_MEMBERS - _DERIVED_MEMBERS:
        if outcome[member] != replayed_facts[member]:
            _fail(f"Execution Job Outcome contradicts replayed {member}")
    expected_reasons = replayed_facts["expected_ineligibility_reasons"]
    if expected_reasons != outcome["ineligibility_reasons"]:
        _fail("Execution Job Outcome contradicts replayed ineligibility predicates")

    observation_set = replayed_facts["output_storage_observation_set"]
    if outcome["selected_attempt_binding"]["kind"] == "NONE":
        if observation_set is not None:
            _fail("No-Attempt Outcome must not resolve an observation set")
        return
    if not isinstance(observation_set, dict):
        _fail("Selected-Attempt Outcome replay facts omit the observation set")
    from . import execution_contracts

    validator = getattr(
        execution_contracts,
        "validate_execution_output_storage_observation_set_v1",
        None,
    )
    if not callable(validator):
        _fail("Outcome Observation Set validator is unavailable")
    validator(observation_set)
    selected = outcome["selected_attempt_binding"]
    runtime = outcome["runtime_outcome"]
    copied_observation_fields = {
        "job_id": outcome["job_id"],
        "attempt_id": selected["attempt_id"],
        "attempt_binding_sigil": selected["attempt_binding_sigil"],
        "result_binding": outcome["result_binding"],
        "log_closure_sigil": runtime["log_closure_sigil"],
        "output_closure_sigil": runtime["output_closure_sigil"],
        "control_evidence_set_binding": outcome["control_evidence_set_binding"],
        "quarantine_binding_set_binding": outcome[
            "quarantine_binding_set_binding"
        ],
        "terminalization_storage_manifest_binding": outcome[
            "terminalization_storage_manifest_binding"
        ],
        "output_root_protection": outcome["output_root_protection"],
        "terminal_source_binding": outcome["terminal_source_binding"],
    }
    for member, expected in copied_observation_fields.items():
        if observation_set[member] != expected:
            _fail(f"Outcome contradicts observation-set {member}")
    binding = outcome["storage_observation_binding"]
    if binding["kind"] != "FROZEN":
        _fail("Selected-Attempt Outcome lacks a frozen observation binding")
    expected_binding = {
        "kind": "FROZEN",
        "storage_journal_id": observation_set["storage_event"]["journal_id"],
        "through_sequence": observation_set["storage_event"]["sequence"],
        "through_event_sigil": observation_set["storage_event"]["event_sigil"],
        "output_storage_observation_set_id": observation_set["observation_set_id"],
        "output_storage_observation_set_sigil": observation_set[
            "observation_set_sigil"
        ],
    }
    if binding != expected_binding:
        _fail("Outcome storage-observation binding contradicts the supplied set")
    reconstructed = [
        *outcome["outputs"],
        *outcome["logs"],
        *outcome["resource_evidence"],
        outcome["terminal_source_observation"],
    ]
    if reconstructed != observation_set["members"]:
        _fail("Outcome observation groups do not reconstruct the supplied set")


def require_execution_job_outcome_journal_derivation_v1() -> NoReturn:
    """Fail closed: this contract module never replays an Execution Journal."""
    _fail("Execution Job Outcome Journal derivation is unavailable in contract-only scope")


def require_execution_job_outcome_acceptance_eligibility_authority_v1() -> NoReturn:
    """Fail closed: local validation is not acceptance-eligibility authority."""
    _fail("Execution Job Outcome validation grants no acceptance-eligibility authority")


def require_execution_job_outcome_runtime_authority_v1() -> NoReturn:
    """Fail closed: a valid public Outcome is not execution authority."""
    _fail("Execution Job Outcome validation grants no runtime authority")
