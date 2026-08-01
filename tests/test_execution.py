import tempfile
import unittest
from pathlib import Path

from benchwork.athanor import Athanor, AthanorError, content_sigil
from benchwork.execution import ExecutionService, LocalBlobStore
from benchwork.mcp.runtime import BenchworkTools


def _specification(task_id: str = "TK-001", specification_id: str = "ES-001") -> dict:
    value = {
        "schema_version": "benchwork-local-execution-specification/0.1",
        "specification_id": specification_id,
        "task_binding": {
            "task_id": task_id,
            "task_capsule_sigil": "sha256:" + "1" * 64,
        },
    }
    value["specification_sigil"] = content_sigil(value)
    return value


class LocalBlobStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store = LocalBlobStore(Path(self.directory.name))

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_import_is_content_addressed_and_readback_verified(self) -> None:
        first = self.store.import_bytes(b"phase-three", media_type="text/plain")
        second = self.store.import_bytes(b"phase-three", media_type="text/plain")
        self.assertEqual(first["blob_sigil"], second["blob_sigil"])
        self.assertEqual(self.store.read_bytes(first["blob_sigil"]), b"phase-three")
        self.assertTrue((Path(self.directory.name) / ".benchwork" / "storage" / "format.json").exists())

    def test_invalid_blob_sigil_fails_closed(self) -> None:
        with self.assertRaisesRegex(AthanorError, "canonical sha256"):
            self.store.read_bytes("sha256:BAD")


class ExecutionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.service = ExecutionService(Path(self.directory.name))

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_start_is_idempotent_and_cancel_preserves_negative_outcome(self) -> None:
        first = self.service.start(_specification(), "start-001")
        second = self.service.start(_specification(), "start-001")
        self.assertEqual(first["job"]["job_id"], second["job"]["job_id"])
        self.assertEqual(first["job"]["state"], "SUBMITTED")
        cancelled = self.service.cancel(
            first["job"]["job_id"],
            first["job"]["job_binding_sigil"],
            first["job"]["revision"],
            "cancel-001",
            "operator requested cancellation",
        )
        self.assertEqual(cancelled["job"]["state"], "CANCELLED")
        outcome = self.service.get_outcome(first["job"]["job_id"])
        self.assertEqual(outcome["terminal_state"], "CANCELLED")
        self.assertFalse(outcome["eligible_for_acceptance"])

    def test_changed_request_under_same_task_key_is_a_conflict(self) -> None:
        self.service.start(_specification(), "start-001")
        with self.assertRaisesRegex(AthanorError, "idempotency conflict"):
            self.service.start(_specification(specification_id="ES-002"), "start-001")

    def test_observe_cursor_uses_a_fixed_prefix(self) -> None:
        observation = self.service.start(_specification(), "start-001")
        job = observation["job"]
        self.service.cancel(
            job["job_id"],
            job["job_binding_sigil"],
            job["revision"],
            "cancel-001",
            "operator requested cancellation",
        )
        first_page = self.service.observe(job["job_id"], limit=1)
        self.assertIsNotNone(first_page["next_cursor"])
        second_page = self.service.observe(
            job["job_id"], limit=1, cursor=first_page["next_cursor"]
        )
        self.assertLessEqual(second_page["through_journal_sequence"], first_page["through_journal_sequence"])
        self.assertEqual(second_page["through_event_sigil"], first_page["through_event_sigil"])

    def test_terminal_cancellation_is_idempotent_and_cancelled_jobs_reject_success(self) -> None:
        observation = self.service.start(_specification(), "start-001")
        job = observation["job"]
        self.service.cancel(
            job["job_id"],
            job["job_binding_sigil"],
            job["revision"],
            "cancel-001",
            "operator requested cancellation",
        )
        terminal = self.service.observe(job["job_id"])["job"]
        replayed = self.service.cancel(
            job["job_id"],
            job["job_binding_sigil"],
            terminal["revision"],
            "cancel-001",
            "operator requested cancellation",
        )
        self.assertEqual(replayed["job"]["revision"], terminal["revision"])
        with self.assertRaisesRegex(AthanorError, "not terminalizable|cancelled"):
            self.service.record_terminal(job["job_id"], "SUCCEEDED", "late worker result")

    def test_tampered_journal_fails_closed(self) -> None:
        observation = self.service.start(_specification(), "start-001")
        journal = Path(self.directory.name) / ".benchwork" / "execution" / "journal.jsonl"
        journal.write_text(journal.read_text(encoding="utf-8").replace("job.submitted", "job.queued"), encoding="utf-8")
        with self.assertRaisesRegex(AthanorError, "Sigil|journal"):
            self.service.observe(observation["job"]["job_id"])

    def test_read_of_unknown_job_does_not_initialize_execution_state(self) -> None:
        with self.assertRaisesRegex(AthanorError, "unknown execution Job"):
            self.service.observe("JB-" + "A" * 64)
        self.assertFalse((Path(self.directory.name) / ".benchwork" / "execution").exists())

    def test_host_neutral_runtime_returns_stable_execution_errors(self) -> None:
        Athanor(Path(self.directory.name)).initialize()
        tools = BenchworkTools(Path(self.directory.name))
        missing = tools.benchwork_observe_job("JB-" + "A" * 64)
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "EXECUTION_NOT_FOUND")
        started = tools.benchwork_start_job(_specification(), "start-001")
        self.assertTrue(started["ok"])
        not_ready = tools.benchwork_get_job_result(started["data"]["job"]["job_id"])
        self.assertFalse(not_ready["ok"])
        self.assertEqual(not_ready["error"]["code"], "EXECUTION_NOT_READY")
        cancelled = tools.benchwork_cancel_job(
            started["data"]["job"]["job_id"],
            started["data"]["job"]["job_binding_sigil"],
            started["data"]["job"]["revision"],
            "cancel-001",
            "operator requested cancellation",
        )
        outcome = tools.benchwork_get_job_result(cancelled["data"]["job"]["job_id"])
        rejected = tools.benchwork_accept_job_result(
            cancelled["data"]["job"]["job_id"],
            outcome["data"]["outcome_sigil"],
            "accept-001",
        )
        self.assertFalse(rejected["ok"])
        self.assertEqual(rejected["error"]["code"], "RESULT_INELIGIBLE")
