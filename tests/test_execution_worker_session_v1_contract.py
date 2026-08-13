from __future__ import annotations

from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.execution_contracts import (
    validate_execution_lease_supplied_bindings_v1,
    validate_execution_lease_v1,
    validate_execution_worker_session_supplied_worker_v1,
    validate_execution_worker_session_v1,
    validate_execution_worker_v1,
)


SIGIL = "sha256:" + "a" * 64


def _worker() -> dict[str, object]:
    worker: dict[str, object] = {
        "schema_version": "execution-worker/1.0",
        "worker_id": "WK-ONE",
        "definition_revision": 0,
        "implementation_name": "local",
        "implementation_version": "1.0",
        "supported_runtimes": [
            {"runtime_id": "RT-ONE", "runtime_version": "1.0", "runtime_sigil": SIGIL}
        ],
        "resource_ceilings": {
            "attempt_budget": {
                "cpu_time_seconds": 1,
                "peak_memory_bytes": 1,
                "storage_bytes_written": 1,
                "output_bytes": 1,
                "log_bytes": 1,
                "process_starts": 1,
                "network_egress_bytes": 1,
                "network_requests": 1,
            },
            "maximum_open_files": 1,
            "maximum_file_count": 1,
            "maximum_concurrent_threads": 1,
        },
        "declared_backend_capabilities": [],
        "verified_capability_tuples": [],
        "maximum_concurrency": 1,
        "definition_created_at": "2026-08-06T00:00:00Z",
        "worker_binding_sigil": "",
    }
    worker["worker_binding_sigil"] = content_sigil(
        {key: value for key, value in worker.items() if key != "worker_binding_sigil"}
    )
    return worker


def _session(worker: dict[str, object]) -> dict[str, object]:
    session: dict[str, object] = {
        "schema_version": "execution-worker-session/1.0",
        "worker_session_id": "WS-00000000000000000000000000",
        "worker_id": worker["worker_id"],
        "worker_binding_sigil": worker["worker_binding_sigil"],
        "executor_instance_id": "XI-ONE",
        "executor_epoch": 1,
        "host_identity_sigil": SIGIL,
        "backend_session_identity": {
            "backend_id": "local",
            "backend_version": "1.0",
            "backend_implementation_sigil": SIGIL,
            "backend_configuration_sigil": SIGIL,
            "process_identity_sigil": SIGIL,
            "session_nonce_sigil": SIGIL,
        },
        "control_channel_identity_sigil": SIGIL,
        "verified_capability_tuple_sigil": SIGIL,
        "maximum_concurrency": 1,
        "opened_at": "2026-08-06T00:00:01Z",
        "worker_session_binding_sigil": "",
    }
    session["worker_session_binding_sigil"] = content_sigil(
        {key: value for key, value in session.items() if key != "worker_session_binding_sigil"}
    )
    return session


def test_worker_and_session_self_bindings_are_closed() -> None:
    worker = _worker()
    session = _session(worker)
    validate_execution_worker_v1(worker)
    validate_execution_worker_session_v1(session)
    validate_execution_worker_session_supplied_worker_v1(session, worker)

    wrong = deepcopy(session)
    wrong["maximum_concurrency"] = 2
    wrong["worker_session_binding_sigil"] = content_sigil(
        {key: value for key, value in wrong.items() if key != "worker_session_binding_sigil"}
    )
    with pytest.raises(AthanorError, match="disagrees"):
        validate_execution_worker_session_supplied_worker_v1(wrong, worker)


def test_lease_binds_exact_attempt_worker_and_session() -> None:
    worker = _worker()
    session = _session(worker)
    attempt = {
        "schema_version": "execution-attempt/1.0",
        "attempt_id": "AT-ONE",
        "job_id": "JB-" + "A" * 64,
        "job_binding_sigil": SIGIL,
        "retry_ordinal": 1,
        "fencing_generation": 1,
        "assurance_requirement": {
            "requested_level": "SANCTUM-A0",
            "profile_version": "1.0",
            "profile_sigil": SIGIL,
            "conformance_suite_id": "CS-ONE",
            "conformance_suite_sigil": SIGIL,
        },
        "backend_identity": "local",
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
        "created_at": "2026-08-06T00:00:00Z",
        "deadline_due_at": "2026-08-06T01:00:00Z",
        "attempt_binding_sigil": "",
    }
    attempt["attempt_binding_sigil"] = content_sigil(
        {key: value for key, value in attempt.items() if key != "attempt_binding_sigil"}
    )
    lease = {
        "schema_version": "execution-lease/1.0",
        "lease_id": "LS-00000000000000000000000000",
        "job_id": attempt["job_id"],
        "attempt_id": attempt["attempt_id"],
        "worker_id": worker["worker_id"],
        "worker_binding_sigil": worker["worker_binding_sigil"],
        "worker_session_id": session["worker_session_id"],
        "worker_session_binding_sigil": session["worker_session_binding_sigil"],
        "executor_instance_id": "XI-ONE",
        "executor_epoch": 1,
        "fencing_generation": 1,
        "offered_at": "2026-08-06T00:00:01Z",
        "claim_due_at": "2026-08-06T00:00:02Z",
        "initial_expiry_due_at": "2026-08-06T00:00:03Z",
        "maximum_expiry_due_at": "2026-08-06T00:00:04Z",
        "heartbeat_policy": {"heartbeat_interval_seconds": 1, "heartbeat_timeout_seconds": 1},
        "lease_credential_digest": SIGIL,
        "lease_binding_sigil": "",
    }
    lease["lease_binding_sigil"] = content_sigil(
        {key: value for key, value in lease.items() if key != "lease_binding_sigil"}
    )
    validate_execution_lease_v1(lease)
    validate_execution_lease_supplied_bindings_v1(lease, attempt, worker, session)
