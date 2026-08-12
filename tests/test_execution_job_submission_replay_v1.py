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


def test_job_submission_replay_requires_exact_supplied_job() -> None:
    job = _job()
    validate_execution_job_v1(job)
    event = _submitted_event(job)
    state = replay_execution_journal_prefix_v1([INITIAL, event], supplied_jobs=[job])
    assert state["jobs"][0]["state"] == "SUBMITTED"
    assert state["jobs"][0]["budget_ledger"]["attempts"]["limit"] == 1
    assert state["deadlines"][0]["deadline_kind"] == "JOB_DEADLINE"
    assert state["idempotency_records"][0]["scope_id"] == "TK-ONE"

    altered = deepcopy(job)
    altered["deadline_due_at"] = "2026-08-06T00:02:00Z"
    altered["job_binding_sigil"] = content_sigil(
        {key: value for key, value in altered.items() if key != "job_binding_sigil"}
    )
    with pytest.raises(AthanorError, match="does not exactly copy"):
        replay_execution_journal_prefix_v1([INITIAL, event], supplied_jobs=[altered])
    with pytest.raises(AthanorError, match="requires exactly one supplied Job"):
        replay_execution_journal_prefix_v1([INITIAL, event])
