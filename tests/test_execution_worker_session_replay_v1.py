from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchwork.athanor import content_sigil
from benchwork.execution_contracts import (
    build_execution_journal_event_v1,
    replay_execution_journal_prefix_v1,
)


ROOT = Path(__file__).parents[1]
INITIAL = json.loads(
    (
        ROOT / "tests/fixtures/phase3/rfc0012/execution-journal-event-v1/valid-initial.json"
    ).read_text()
)
SIGIL = "sha256:" + "a" * 64
SESSION_ID = "WS-00000000000000000000000000"


def _worker() -> dict[str, Any]:
    value: dict[str, Any] = {
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
        "definition_created_at": "2026-08-06T00:00:01Z",
        "worker_binding_sigil": "",
    }
    value["worker_binding_sigil"] = content_sigil(
        {key: item for key, item in value.items() if key != "worker_binding_sigil"}
    )
    return value


def _session(worker: dict[str, Any]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "execution-worker-session/1.0",
        "worker_session_id": SESSION_ID,
        "worker_id": worker["worker_id"],
        "worker_binding_sigil": worker["worker_binding_sigil"],
        "executor_instance_id": INITIAL["executor_instance_id"],
        "executor_epoch": INITIAL["executor_epoch"],
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
        "opened_at": "2026-08-06T00:00:03Z",
        "worker_session_binding_sigil": "",
    }
    value["worker_session_binding_sigil"] = content_sigil(
        {key: item for key, item in value.items() if key != "worker_session_binding_sigil"}
    )
    return value


def _event(
    prior: dict[str, Any],
    event_id: str,
    event_type: str,
    revisions: list[dict[str, Any]],
    payload: dict[str, Any],
) -> dict[str, Any]:
    return build_execution_journal_event_v1(
        {
            "schema_version": "execution-journal-event/1.0",
            "journal_id": INITIAL["journal_id"],
            "event_id": event_id,
            "sequence": prior["sequence"] + 1,
            "event_type": event_type,
            "executor_instance_id": INITIAL["executor_instance_id"],
            "executor_epoch": INITIAL["executor_epoch"],
            "executor_build_sigil": INITIAL["executor_build_sigil"],
            "recorded_at": f"2026-08-06T00:00:0{prior['sequence']}Z",
            "observed_at": None,
            "entity_revisions": revisions,
            "causation_event_id": None,
            "idempotency_key_sigil": None,
            "recovery_action_binding": None,
            "payload": payload,
            "previous_event_sigil": prior["event_sigil"],
        }
    )


def test_worker_session_registration_prefix_replays_to_ready() -> None:
    worker = _worker()
    registered = _event(
        INITIAL,
        "JE-TWO",
        "worker.definition_registered",
        [
            {
                "entity_kind": "WORKER",
                "entity_id": "WK-ONE",
                "preceding_revision": None,
                "next_revision": 0,
            }
        ],
        {
            "worker_binding_sigil": worker["worker_binding_sigil"],
            "definition_revision": 0,
                "supersedes_worker_binding_sigil": SIGIL,
        },
    )
    enabled = _event(
        registered,
        "JE-THREE",
        "worker.enabled",
        [
            {
                "entity_kind": "WORKER",
                "entity_id": "WK-ONE",
                "preceding_revision": 0,
                "next_revision": 1,
            }
        ],
        {
            "worker_binding_sigil": worker["worker_binding_sigil"],
            "verification_evidence_set_sigil": SIGIL,
        },
    )
    session = _session(worker)
    session_registered = _event(
        enabled,
        "JE-FOUR",
        "worker_session.registered",
        [
            {
                "entity_kind": "WORKER_SESSION",
                "entity_id": SESSION_ID,
                "preceding_revision": None,
                "next_revision": 0,
            }
        ],
        {
            "worker_session_binding_sigil": session["worker_session_binding_sigil"],
            "worker_binding_sigil": worker["worker_binding_sigil"],
            "backend_session_identity": session["backend_session_identity"],
            "control_channel_identity_sigil": SIGIL,
        },
    )
    ready = _event(
        session_registered,
        "JE-FIVE",
        "worker_session.ready",
        [
            {
                "entity_kind": "WORKER_SESSION",
                "entity_id": SESSION_ID,
                "preceding_revision": 0,
                "next_revision": 1,
            }
        ],
        {
            "verification_evidence_set_sigil": SIGIL,
            "capacity": 1,
            "worker_session_heartbeat_policy_id": "WSHP-" + "A" * 64,
            "worker_session_heartbeat_policy_sigil": SIGIL,
            "initial_heartbeat_due_at": "2026-08-06T00:01:00Z",
        },
    )
    state = replay_execution_journal_prefix_v1(
        [INITIAL, registered, enabled, session_registered, ready],
        supplied_workers=[worker],
        supplied_worker_sessions=[session],
    )
    assert state["workers"][0]["state"] == "ENABLED"
    assert state["worker_sessions"][0]["state"] == "READY"
    assert state["worker_sessions"][0]["capacity"] == 1
