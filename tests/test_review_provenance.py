import tempfile
import unittest
from pathlib import Path

from benchwork.athanor import Athanor, AthanorError
from benchwork.circle import CapabilityRegistry
from benchwork.mcp.runtime import BenchworkTools
from benchwork.rites import RiteRegistry


class ReviewProvenanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)
        self.registry = CapabilityRegistry(self.root)
        self.registry.initialize()
        RiteRegistry(self.root).initialize()
        self.program_id, _ = self.athanor.create_program(
            "review-provenance",
            "Review provenance",
        )
        self.target = {
            "repository": "Endofthestars/benchwork",
            "commit": None,
            "files": ["src/benchwork/athanor.py"],
        }
        self.scope = {
            "summary": "Review the bounded transition implementation.",
            "checks": ["correctness", "tests", "disclosure"],
        }
        self.disclosure = {
            "includes_source_code": True,
            "includes_private_data": False,
            "includes_credentials": False,
            "includes_unpublished_results": False,
        }
        self.result = {
            "summary": "The bounded review completed.",
            "findings": ["The transition is replayable."],
            "residual_risks": ["IDE validation remains environment-dependent."],
            "recommendation": "Accept after targeted tests pass.",
        }

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _complete_review_task(
        self,
        review_id: str,
        capability: str,
        *,
        approval_reason: str | None = None,
    ) -> str:
        tools = BenchworkTools(self.root)
        opened = tools.benchwork_open_task(
            capability,
            self.program_id,
            f"Perform the bounded Review {review_id}.",
            approval_reason=approval_reason,
            review_id=review_id,
        )
        self.assertTrue(opened["ok"])
        self.assertEqual(opened["data"]["ward"]["status"], "PASS")
        task_id = opened["data"]["task"]["task_id"]
        completed = tools.benchwork_complete_task(
            task_id,
            "Review result proposed.",
            {
                "review_id": review_id,
                "reviewer": {"kind": "agent", "name": "review-agent"},
                "result": self.result,
            },
        )
        self.assertTrue(completed["ok"])
        return task_id

    def test_local_review_completes_without_disclosure_approval(self) -> None:
        self.athanor.prepare_review(
            "RV-LOCAL",
            self.program_id,
            "local_review",
            self.target,
            self.scope,
            self.disclosure,
            {"execution": "local", "provider": None},
        )
        request = self.athanor.review_requests()["RV-LOCAL"]
        self.assertEqual(request["status"], "PREPARED")
        self.assertEqual(request["approval"]["status"], "NOT_REQUIRED")

        task_id = self._complete_review_task(
            "RV-LOCAL",
            "bench.review.local",
        )
        self.athanor.record_review(
            "RV-LOCAL",
            task_id,
            {"kind": "agent", "name": "local-codex"},
            self.result,
            "codex",
        )
        artifact = self.athanor.review_artifacts()["RV-LOCAL"]
        self.assertEqual(artifact["task_id"], task_id)
        self.assertEqual(artifact["source"]["execution"], "local")
        self.assertEqual(artifact["status"], "COMPLETED")

        self.athanor.accept_review("RV-LOCAL", "Targeted validation passed.")
        accepted = self.athanor.review_artifacts()["RV-LOCAL"]
        self.assertEqual(accepted["status"], "ACCEPTED")
        self.assertIsNotNone(accepted["acceptance_receipt"])
        self.assertEqual(
            [event["type"] for event in self.athanor.trace("RV-LOCAL")],
            [
                "review.requested",
                "agent-result.accepted",
                "review.completed",
                "review.accepted",
            ],
        )

    def test_external_review_fails_closed_until_explicit_disclosure_approval(self) -> None:
        self.athanor.prepare_review(
            "RV-EXTERNAL",
            self.program_id,
            "external_diff_review",
            self.target,
            self.scope,
            self.disclosure,
            {"execution": "external", "provider": "codex"},
        )
        request = self.athanor.review_requests()["RV-EXTERNAL"]
        self.assertEqual(
            request["status"],
            "WAITING_FOR_DISCLOSURE_AUTHORIZATION",
        )

        with self.assertRaisesRegex(
            AthanorError,
            "waiting for disclosure authorization",
        ):
            self.athanor.record_review(
                "RV-EXTERNAL",
                "TK-MISSING",
                {"kind": "agent", "name": "remote-codex"},
                self.result,
                "codex",
            )
        with self.assertRaisesRegex(AthanorError, "requires approved_by"):
            self.athanor.approve_external_review(
                "RV-EXTERNAL",
                "",
                "Approve only the declared source file.",
            )

        self.athanor.approve_external_review(
            "RV-EXTERNAL",
            "researcher",
            "Approve only the declared source file.",
        )
        approved = self.athanor.review_requests()["RV-EXTERNAL"]
        self.assertEqual(approved["approval"]["status"], "APPROVED")
        self.assertEqual(approved["approval"]["approved_by"], "researcher")

        with self.assertRaisesRegex(AthanorError, "accepted bound Task"):
            self.athanor.record_review(
                "RV-EXTERNAL",
                "TK-MISSING",
                {"kind": "agent", "name": "remote-codex"},
                self.result,
                "codex",
            )
        task_id = self._complete_review_task(
            "RV-EXTERNAL",
            "bench.review.external",
            approval_reason="The user approved this bounded external Task.",
        )
        self.athanor.record_review(
            "RV-EXTERNAL",
            task_id,
            {"kind": "agent", "name": "remote-codex"},
            self.result,
            "codex",
        )
        artifact = self.athanor.review_artifacts()["RV-EXTERNAL"]
        self.assertEqual(artifact["source"]["execution"], "external")
        self.assertEqual(
            [event["type"] for event in self.athanor.trace("RV-EXTERNAL")],
            [
                "review.requested",
                "review.approved",
                "agent-result.accepted",
                "review.completed",
            ],
        )

    def test_external_review_rejects_credentials_and_escaping_paths(self) -> None:
        credentials = {**self.disclosure, "includes_credentials": True}
        with self.assertRaisesRegex(AthanorError, "cannot disclose credentials"):
            self.athanor.prepare_review(
                "RV-CREDENTIALS",
                self.program_id,
                "external_diff_review",
                self.target,
                self.scope,
                credentials,
                {"execution": "external", "provider": "codex"},
            )
        with self.assertRaisesRegex(AthanorError, "validation failed"):
            self.athanor.prepare_review(
                "RV-ESCAPE",
                self.program_id,
                "local_review",
                {**self.target, "files": ["../secret.txt"]},
                self.scope,
                self.disclosure,
                {"execution": "local", "provider": None},
            )

    def test_review_capabilities_separate_local_and_external_approval(self) -> None:
        tools = BenchworkTools(self.root)
        self.athanor.prepare_review(
            "RV-TASK-LOCAL",
            self.program_id,
            "local_review",
            self.target,
            self.scope,
            self.disclosure,
            {"execution": "local", "provider": None},
        )
        self.athanor.prepare_review(
            "RV-TASK-EXTERNAL",
            self.program_id,
            "external_diff_review",
            self.target,
            self.scope,
            self.disclosure,
            {"execution": "external", "provider": "codex"},
        )
        blocked = tools.benchwork_open_task(
            "bench.review.external",
            self.program_id,
            "Do not perform this unapproved external review.",
            review_id="RV-TASK-EXTERNAL",
        )
        self.assertFalse(blocked["ok"])
        self.athanor.approve_external_review(
            "RV-TASK-EXTERNAL",
            "researcher",
            "Approve only the declared source file.",
        )
        local = tools.benchwork_open_task(
            "bench.review.local",
            self.program_id,
            "Perform a local read-only review.",
            review_id="RV-TASK-LOCAL",
        )
        external = tools.benchwork_open_task(
            "bench.review.external",
            self.program_id,
            "Perform the separately approved external review.",
            review_id="RV-TASK-EXTERNAL",
        )
        approved_external = tools.benchwork_open_task(
            "bench.review.external",
            self.program_id,
            "Perform a second separately approved external review.",
            approval_reason="The user approved this bounded external Task.",
            review_id="RV-TASK-EXTERNAL",
        )
        self.assertEqual(local["data"]["ward"]["status"], "PASS")
        self.assertEqual(
            local["data"]["task"]["bindings"]["review_id"],
            "RV-TASK-LOCAL",
        )
        self.assertEqual(
            external["data"]["ward"]["status"],
            "WAITING_FOR_APPROVAL",
        )
        self.assertEqual(approved_external["data"]["ward"]["status"], "PASS")

        external_task = approved_external["data"]["task"]
        completed = tools.benchwork_complete_task(
            external_task["task_id"],
            "External review result proposed.",
            {
                "review_id": "RV-TASK-EXTERNAL",
                "reviewer": {"kind": "agent", "name": "remote-codex"},
                "result": self.result,
            },
        )
        self.assertTrue(completed["ok"])

        mismatched_task = tools.benchwork_open_task(
            "bench.review.external",
            self.program_id,
            "Perform another bounded external review.",
            approval_reason="The user approved this bounded external Task.",
            review_id="RV-TASK-EXTERNAL",
        )["data"]["task"]
        mismatched = tools.benchwork_complete_task(
            mismatched_task["task_id"],
            "Mismatched external review result.",
            {
                "review_id": "RV-OTHER",
                "reviewer": {"kind": "agent", "name": "remote-codex"},
                "result": self.result,
            },
        )
        self.assertFalse(mismatched["ok"])
        self.assertIn("bound Review Request", mismatched["error"]["message"])

    def test_mcp_review_lifecycle_returns_receipts_without_invoking_provider(self) -> None:
        tools = BenchworkTools(self.root)
        prepared = tools.benchwork_prepare_review(
            "RV-MCP",
            self.program_id,
            "external_diff_review",
            self.target,
            self.scope,
            self.disclosure,
            {"execution": "external", "provider": "codex"},
        )
        self.assertTrue(prepared["ok"])
        self.assertIsNotNone(prepared["receipt"])
        self.assertEqual(
            prepared["data"]["review"]["status"],
            "WAITING_FOR_DISCLOSURE_AUTHORIZATION",
        )

        denied = tools.benchwork_record_review(
            "RV-MCP",
            "TK-MISSING",
            "agent",
            "remote-codex",
            self.result["summary"],
            self.result["findings"],
            self.result["residual_risks"],
            self.result["recommendation"],
        )
        self.assertFalse(denied["ok"])

        approved = tools.benchwork_approve_external_review(
            "RV-MCP",
            "researcher",
            "Approve only the declared source file.",
        )
        self.assertTrue(approved["ok"])
        task = tools.benchwork_open_task(
            "bench.review.external",
            self.program_id,
            "Perform the approved external Review.",
            approval_reason="The user approved this bounded external Task.",
            review_id="RV-MCP",
        )["data"]["task"]
        task_result = tools.benchwork_complete_task(
            task["task_id"],
            "External Review result proposed.",
            {
                "review_id": "RV-MCP",
                "reviewer": {"kind": "agent", "name": "remote-codex"},
                "result": self.result,
            },
        )
        self.assertTrue(task_result["ok"])
        completed = tools.benchwork_record_review(
            "RV-MCP",
            task["task_id"],
            "agent",
            "remote-codex",
            self.result["summary"],
            self.result["findings"],
            self.result["residual_risks"],
            self.result["recommendation"],
        )
        self.assertTrue(completed["ok"])
        fetched = tools.benchwork_get_review("RV-MCP")
        self.assertEqual(fetched["data"]["artifact"]["status"], "COMPLETED")
        accepted = tools.benchwork_accept_review(
            "RV-MCP",
            "The review was inspected and accepted.",
            "researcher",
        )
        self.assertTrue(accepted["ok"])
        self.assertEqual(accepted["data"]["review"]["status"], "ACCEPTED")
        self.assertTrue(tools.benchwork_doctor(deep=True)["ok"])
