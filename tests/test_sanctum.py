import unittest
from datetime import UTC, datetime, timedelta

from benchwork.sanctum import JobState, LocalSanctumRuntime, SanctumError
from benchwork.schema_validation import validate_instance


SIGIL = "sha256:" + "a" * 64


class LocalSanctumRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = LocalSanctumRuntime()
        self.now = datetime(2026, 8, 14, tzinfo=UTC)

    def test_local_lifecycle_yields_a_result_proposal_not_a_run(self) -> None:
        job = self.runtime.submit("JB-001", SIGIL, SIGIL, now=self.now)
        validate_instance("sanctum-local-job-0.1.json", job)
        lease = self.runtime.claim("JB-001", "LS-001", "WK-001", 30, now=self.now)
        validate_instance("sanctum-local-lease-0.1.json", lease)
        self.runtime.start("JB-001", "LS-001", now=self.now)
        result = self.runtime.finish(
            "JB-001",
            "LS-001",
            JobState.COMPLETED,
            "Produced a bounded proposal.",
            [{"schema": "code-modification-result/1.0", "uri": "proposal.json", "blob_sigil": SIGIL}],
            now=self.now + timedelta(seconds=1),
        )
        validate_instance("sanctum-local-worker-result-0.1.json", result)
        self.assertEqual(self.runtime.job("JB-001")["status"], "COMPLETED")
        self.assertNotIn("run_id", result)

    def test_expired_lease_rejects_a_stale_completion(self) -> None:
        self.runtime.submit("JB-001", SIGIL, SIGIL, now=self.now)
        self.runtime.claim("JB-001", "LS-001", "WK-001", 1, now=self.now)
        self.runtime.start("JB-001", "LS-001", now=self.now)
        expired = self.runtime.expire_leases(now=self.now + timedelta(seconds=1))
        self.assertEqual(expired[0]["status"], "EXPIRED")
        with self.assertRaisesRegex(SanctumError, "no longer active"):
            self.runtime.finish(
                "JB-001", "LS-001", JobState.FAILED, "stale", [], now=self.now + timedelta(seconds=2)
            )

    def test_completed_result_requires_a_bounded_output(self) -> None:
        self.runtime.submit("JB-001", SIGIL, SIGIL, now=self.now)
        self.runtime.claim("JB-001", "LS-001", "WK-001", 30, now=self.now)
        self.runtime.start("JB-001", "LS-001", now=self.now)
        with self.assertRaisesRegex(SanctumError, "requires at least one output"):
            self.runtime.finish("JB-001", "LS-001", JobState.COMPLETED, "nothing", [], now=self.now)

    def test_runtime_rejects_records_that_cannot_match_the_contract(self) -> None:
        with self.assertRaisesRegex(SanctumError, "job_id"):
            self.runtime.submit("JB-unsafe!", SIGIL, SIGIL, now=self.now)
