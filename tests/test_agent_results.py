import json
import tempfile
import unittest
from pathlib import Path

from benchwork.athanor import Athanor, AthanorError
from benchwork.circle import CapsuleStore, CapabilityRegistry, DEFAULT_CAPABILITIES


class AgentResultTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)
        self.registry = CapabilityRegistry(self.root)
        self.capsules = CapsuleStore(self.root)
        self.registry.initialize()

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _capsule(self, capability: str = "bench.code.inspect") -> dict:
        contract = self.registry.get(capability)
        return self.capsules.create(
            capability,
            "sha256:" + "1" * 64,
            {
                "tools": contract["allowed_tools"],
                "time_budget_seconds": 60,
                "network": False,
            },
        )

    def _result(self, task_id: str, input_sigil: str) -> dict:
        return {
            "schema_version": "agent-result/1.0",
            "task_id": task_id,
            "input_sigil": input_sigil,
            "artifacts": [
                {
                    "uri": "proposals/inspection.json",
                    "sigil": "sha256:" + "2" * 64,
                }
            ],
            "status": "COMPLETED",
        }

    def test_agent_result_is_accepted_once_and_replayable(self) -> None:
        capsule = self._capsule()
        result = self._result(capsule["task_id"], capsule["input_sigil"])
        receipt = self.athanor.accept_agent_result(result)

        accepted = self.athanor.agent_results()[capsule["task_id"]]
        self.assertEqual(accepted["capability"], "bench.code.inspect")
        self.assertEqual(accepted["capsule_sigil"], capsule["capsule_sigil"])
        self.assertEqual(accepted["acceptance_receipt"], receipt.receipt_id)
        self.assertEqual(
            [event["type"] for event in self.athanor.trace(capsule["task_id"])],
            ["agent-result.accepted"],
        )

        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "already has"):
            self.athanor.accept_agent_result(result)
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

    def test_result_requires_matching_input_and_passing_ward(self) -> None:
        capsule = self._capsule()
        mismatched = self._result(capsule["task_id"], "sha256:" + "3" * 64)
        with self.assertRaisesRegex(AthanorError, "input Sigil"):
            self.athanor.accept_agent_result(mismatched)
        self.assertEqual(self.athanor.chronicle.events(), [])

        gated = self._capsule("bench.code.modify")
        result = self._result(gated["task_id"], gated["input_sigil"])
        with self.assertRaisesRegex(AthanorError, "WAITING_FOR_APPROVAL"):
            self.athanor.accept_agent_result(result)
        self.assertEqual(self.athanor.chronicle.events(), [])

        approval = self.athanor.grant_approval(gated, "Reviewed bounded write access.")
        accepted = self.athanor.accept_agent_result(result)
        self.assertNotEqual(approval.receipt_id, accepted.receipt_id)
        self.assertEqual(self.athanor.agent_results()[gated["task_id"]]["status"], "COMPLETED")

    def test_invalid_result_schema_fails_before_append(self) -> None:
        capsule = self._capsule()
        result = self._result(capsule["task_id"], capsule["input_sigil"])
        result["unexpected"] = True
        with self.assertRaisesRegex(AthanorError, "validation failed"):
            self.athanor.accept_agent_result(result)
        self.assertEqual(self.athanor.chronicle.events(), [])

    def test_registry_additively_migrates_legacy_capabilities(self) -> None:
        legacy_contract = {
            "allowed_tools": ["read"],
            "network": False,
            "max_time_seconds": 123,
            "requires_approval": False,
        }
        path = self.root / ".benchwork" / "capabilities.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": "capability-registry/1.0",
                    "capabilities": {"bench.code.inspect": legacy_contract},
                }
            ),
            encoding="utf-8",
        )

        capabilities = self.registry.capabilities()
        self.assertEqual(set(capabilities), set(DEFAULT_CAPABILITIES))
        self.assertEqual(capabilities["bench.code.inspect"], legacy_contract)

    def test_default_capabilities_match_rfc_0000(self) -> None:
        expected = {
            "bench.research.orchestrate",
            "bench.evidence.discover",
            "bench.evidence.synthesize",
            "bench.evidence.verify",
            "bench.hypothesis.frame",
            "bench.hypothesis.challenge",
            "bench.study.design",
            "bench.study.audit",
            "bench.code.inspect",
            "bench.code.modify",
            "bench.experiment.plan",
            "bench.experiment.execute",
            "bench.experiment.collect",
            "bench.analysis.compute",
            "bench.analysis.interpret",
            "bench.decision.review",
            "bench.decision.propose",
        }
        self.assertEqual(set(DEFAULT_CAPABILITIES), expected)
