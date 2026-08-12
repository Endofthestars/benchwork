from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.execution_contracts import (
    build_execution_journal_event_v1,
    replay_execution_journal_prefix_v1,
    replay_execution_supplied_state_suffix_v1,
    validate_execution_job_v1,
)


ROOT = Path(__file__).parents[1]
INITIAL = json.loads(
    (
        ROOT / "tests/fixtures/phase3/rfc0012/execution-journal-event-v1/valid-initial.json"
    ).read_text()
)
SIGIL = "sha256:" + "a" * 64
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
            "causation_event_id": None,
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
            "causation_event_id": None,
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
    preflight = _preflight_event(allocated)
    preflight_state = replay_execution_journal_prefix_v1(
        [INITIAL, event, queued, allocated, preflight],
        supplied_jobs=[job], supplied_attempts=[attempt],
    )
    assert preflight_state["attempts"][0]["state"] == "PREFLIGHTING"
    preflight_passed = _preflight_passed_event(preflight)
    ready_state = replay_execution_journal_prefix_v1(
        [INITIAL, event, queued, allocated, preflight, preflight_passed],
        supplied_jobs=[job], supplied_attempts=[attempt],
    )
    assert ready_state["attempts"][0]["state"] == "READY"

    combined = deepcopy(ready_state)
    session_id = "WS-00000000000000000000000000"
    combined["workers"] = [{"worker_id": "WK-ONE", "revision": 1, "state": "ENABLED", "worker_binding_sigil": SIGIL, "definition_revision": 0, "worker_session_ids": [session_id], "last_event_id": "JE-SIX", "last_event_sigil": preflight_passed["event_sigil"]}]
    combined["worker_sessions"] = [{"worker_session_id": session_id, "revision": 1, "state": "READY", "worker_id": "WK-ONE", "worker_binding_sigil": SIGIL, "worker_session_binding_sigil": SIGIL, "executor_epoch": 1, "worker_session_heartbeat_policy_id": "WSHP-" + "A" * 64, "worker_session_heartbeat_policy_sigil": SIGIL, "capacity": 1, "capacity_in_use": 0, "last_heartbeat_sequence": None, "last_heartbeat_message_sigil": None, "last_resource_sample_sigil": None, "resource_counter_floors": {"cpu_time_seconds": None, "storage_bytes_written": None, "network_egress_bytes": None}, "next_heartbeat_due_at": "2026-08-06T00:00:30Z", "lease_ids": [], "last_event_id": "JE-SIX", "last_event_sigil": preflight_passed["event_sigil"]}]
    combined["deadlines"].append({"deadline_kind": "HEARTBEAT_TIMEOUT", "due_at": "2026-08-06T00:00:30Z", "fixed_priority": 30, "entity_id": session_id, "source_event_id": "JE-SIX", "source_event_sigil": preflight_passed["event_sigil"]})
    combined["deadlines"].sort(key=lambda item: (item["due_at"], item["fixed_priority"], item["entity_id"]))
    combined["state_sigil"] = content_sigil({key: value for key, value in combined.items() if key != "state_sigil"})
    lease: dict[str, Any] = {"schema_version": "execution-lease/1.0", "lease_id": "LS-00000000000000000000000000", "job_id": JOB_ID, "attempt_id": "AT-ONE", "worker_id": "WK-ONE", "worker_binding_sigil": SIGIL, "worker_session_id": session_id, "worker_session_binding_sigil": SIGIL, "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "fencing_generation": 1, "offered_at": "2026-08-06T00:00:05Z", "claim_due_at": "2026-08-06T00:00:06Z", "initial_expiry_due_at": "2026-08-06T00:00:07Z", "maximum_expiry_due_at": "2026-08-06T00:00:08Z", "heartbeat_policy": {"heartbeat_interval_seconds": 1, "heartbeat_timeout_seconds": 1}, "lease_credential_digest": SIGIL, "lease_binding_sigil": ""}
    lease["lease_binding_sigil"] = content_sigil({key: value for key, value in lease.items() if key != "lease_binding_sigil"})
    offered = build_execution_journal_event_v1({"schema_version": "execution-journal-event/1.0", "journal_id": INITIAL["journal_id"], "event_id": "JE-SEVEN", "sequence": 7, "event_type": "lease.offered", "executor_instance_id": INITIAL["executor_instance_id"], "executor_epoch": 1, "executor_build_sigil": INITIAL["executor_build_sigil"], "recorded_at": lease["offered_at"], "observed_at": None, "entity_revisions": [{"entity_kind": "WORKER_SESSION", "entity_id": session_id, "preceding_revision": 1, "next_revision": 2}, {"entity_kind": "ATTEMPT", "entity_id": "AT-ONE", "preceding_revision": 2, "next_revision": 3}, {"entity_kind": "LEASE", "entity_id": lease["lease_id"], "preceding_revision": None, "next_revision": 0}], "causation_event_id": None, "idempotency_key_sigil": None, "recovery_action_binding": None, "payload": {"lease_binding_sigil": lease["lease_binding_sigil"], "credential_digest": SIGIL, "claim_due_at": lease["claim_due_at"], "initial_expiry_due_at": lease["initial_expiry_due_at"], "maximum_expiry_due_at": lease["maximum_expiry_due_at"]}, "previous_event_sigil": preflight_passed["event_sigil"]})
    offered_state = replay_execution_supplied_state_suffix_v1(combined, [offered], supplied_leases=[lease])
    assert offered_state["leases"][0]["state"] == "OFFERED"
    assert offered_state["attempts"][0]["lease_id"] == lease["lease_id"]

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

    altered = deepcopy(job)
    altered["deadline_due_at"] = "2026-08-06T00:02:00Z"
    altered["job_binding_sigil"] = content_sigil(
        {key: value for key, value in altered.items() if key != "job_binding_sigil"}
    )
    with pytest.raises(AthanorError, match="does not exactly copy"):
        replay_execution_journal_prefix_v1([INITIAL, event], supplied_jobs=[altered])
    with pytest.raises(AthanorError, match="requires exactly one supplied Job"):
        replay_execution_journal_prefix_v1([INITIAL, event])
