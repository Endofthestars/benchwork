from __future__ import annotations

from copy import deepcopy

import pytest

from benchwork.athanor import AthanorError, content_sigil
from benchwork.execution_contracts import (
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
