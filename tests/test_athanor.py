import hashlib
import tempfile
import unittest
from pathlib import Path
import json
import multiprocessing as mp
from jsonschema import Draft202012Validator

from benchwork.athanor import Athanor, AthanorError
from benchwork.circle import CapsuleStore, CapabilityRegistry, Ward
from benchwork.schema_validation import validate_instance
from benchwork.tasks import TaskService


def _concurrent_program(argument: tuple[str, str]) -> str:
    root, slug = argument
    return Athanor(Path(root)).create_program(slug, slug)[0]


class AthanorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_program_protocol_and_replay(self) -> None:
        program_id, receipt = self.athanor.create_program("robust-agent-memory", "Reliable agent memory")
        self.assertEqual(program_id, "RP-001")
        self.assertTrue(receipt.sigil.startswith("sha256:"))

        self.athanor.draft_protocol("PT-001", program_id, "Memory study", "Compute effect sizes by seed.")
        self.athanor.seal_protocol("PT-001")
        replay = self.athanor.replay()
        self.assertEqual(replay["programs"][program_id]["status"], "DESIGN_FROZEN")
        self.assertEqual(replay["protocols"]["PT-001"]["status"], "FROZEN")
        self.assertIsNotNone(replay["protocols"]["PT-001"]["sealed_at"])
        self.assertTrue(replay["protocols"]["PT-001"]["seal_receipt"].startswith("RC-"))
        self.assertEqual(len(self.athanor.trace("PT-001")), 2)

    def test_protocol_must_be_drafted_and_cannot_reseal(self) -> None:
        with self.assertRaisesRegex(AthanorError, "not an unsealed draft"):
            self.athanor.seal_protocol("PT-001")

        program_id, _ = self.athanor.create_program("memory", "Memory")
        with self.assertRaisesRegex(AthanorError, "deterministic analysis plan"):
            self.athanor.draft_protocol("PT-001", program_id, "Memory", "")
        self.athanor.draft_protocol("PT-001", program_id, "Memory", "Pre-register the comparison.")
        self.athanor.seal_protocol("PT-001")
        with self.assertRaisesRegex(AthanorError, "not an unsealed draft"):
            self.athanor.seal_protocol("PT-001")

    def test_altered_or_reordered_event_fails_verification(self) -> None:
        program_id, _ = self.athanor.create_program("memory", "Memory")
        self.athanor.draft_protocol("PT-001", program_id, "Memory", "Compute a confidence interval.")
        ledger = self.root / ".benchwork" / "chronicle.jsonl"
        lines = ledger.read_text().splitlines()
        ledger.write_text("\n".join(reversed(lines)) + "\n")
        with self.assertRaisesRegex(AthanorError, "invalid Sigil|broken Chronicle chain"):
            self.athanor.chronicle.events()

    def test_duplicate_program_slug_is_rejected(self) -> None:
        self.athanor.create_program("memory", "Memory")
        with self.assertRaisesRegex(AthanorError, "slug already exists"):
            self.athanor.create_program("memory", "Another memory project")

    def test_working_requires_frozen_protocol_and_replays_lifecycle(self) -> None:
        program_id, _ = self.athanor.create_program("memory", "Memory")
        with self.assertRaisesRegex(AthanorError, "frozen Protocol"):
            self.athanor.create_working("computational-study@0.2.1", program_id, "PT-001")
        self.athanor.draft_protocol("PT-001", program_id, "Memory", "Compute pre-registered metrics.")
        with self.assertRaisesRegex(AthanorError, "frozen Protocol"):
            self.athanor.create_working("computational-study@0.2.1", program_id, "PT-001")
        self.athanor.seal_protocol("PT-001")
        working_id, _ = self.athanor.create_working("computational-study@0.2.1", program_id, "PT-001")
        artifact_path = self.root / "artifact.json"
        artifact_path.write_text("implementation", encoding="utf-8")
        self.athanor.register_artifact(
            "AR-001",
            program_id,
            "implementation",
            {
                "uri": "artifact.json",
                "sigil": "sha256:" + hashlib.sha256(b"implementation").hexdigest(),
            },
            working_id,
        )
        self.assertEqual(self.athanor.workings()[working_id]["stage"], "PILOT")
        self.assertEqual(len(self.athanor.workings()[working_id]["history"]), 2)

    def test_schema_files_are_versioned_json_contracts(self) -> None:
        schemas = Path(__file__).parents[1] / "schemas"
        for schema_path in schemas.glob("*.json"):
            schema = json.loads(schema_path.read_text())
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            version = schema_path.stem.rsplit("-", 1)[1]
            self.assertTrue(schema["$id"].endswith(f"/{version}"))
            Draft202012Validator.check_schema(schema)

    def test_ward_requires_approval_before_gated_task_can_pass(self) -> None:
        registry = CapabilityRegistry(self.root)
        program_id, _ = self.athanor.create_program("ward-approval", "Ward approval")
        capsule = TaskService(
            self.athanor,
            registry,
            CapsuleStore(self.root),
        ).create(
            "bench.code.modify",
            program_id,
            "Modify code within the approved boundary.",
            {"tools": ["read", "write"], "time_budget_seconds": 300, "network": False},
        )
        ward = Ward(registry, {})
        self.assertEqual(ward.evaluate(capsule).status, "WAITING_FOR_APPROVAL")
        self.athanor.grant_approval(capsule, "Reviewed requested code boundary.")
        self.assertEqual(Ward(registry, self.athanor.approvals()).evaluate(capsule).status, "PASS")

    def test_ward_rejects_tool_and_network_escalation(self) -> None:
        registry = CapabilityRegistry(self.root)
        ward = Ward(registry, {})
        capsule = {
            "schema_version": "task-capsule/1.0",
            "task_id": "TK-EXAMPLE",
            "capability": "bench.code.inspect",
            "input_sigil": "sha256:" + "0" * 64,
            "circle": {"tools": ["read", "write"], "time_budget_seconds": 60, "network": False},
        }
        self.assertEqual(ward.evaluate(capsule).status, "REJECTED")
        capsule["circle"] = {"tools": ["read"], "time_budget_seconds": 60, "network": True}
        self.assertEqual(ward.evaluate(capsule).status, "REJECTED")

    def test_concurrent_program_creation_is_one_transaction(self) -> None:
        context = mp.get_context("fork")
        with context.Pool(2) as pool:
            identifiers = pool.map(
                _concurrent_program,
                [(str(self.root), "alpha"), (str(self.root), "beta")],
            )
        self.assertEqual(sorted(identifiers), ["RP-001", "RP-002"])
        self.assertEqual(len(self.athanor.programs()), 2)

    def test_chronicle_tail_truncation_is_detected(self) -> None:
        self.athanor.create_program("alpha", "Alpha")
        self.athanor.create_program("beta", "Beta")
        ledger = self.root / ".benchwork" / "chronicle.jsonl"
        ledger.write_text(ledger.read_text().splitlines()[0] + "\n")
        with self.assertRaisesRegex(AthanorError, "head mismatch"):
            self.athanor.chronicle.events()

    def test_approval_cannot_be_reused_after_capsule_mutation(self) -> None:
        registry = CapabilityRegistry(self.root)
        program_id, _ = self.athanor.create_program(
            "approval-mutation",
            "Approval mutation",
        )
        capsule = TaskService(
            self.athanor,
            registry,
            CapsuleStore(self.root),
        ).create(
            "bench.code.modify",
            program_id,
            "Modify code within the approved boundary.",
            {"tools": ["read", "write"], "time_budget_seconds": 300, "network": False},
        )
        self.athanor.grant_approval(capsule, "Approve code modification.")
        capsule["capability"]["id"] = "bench.experiment.execute"
        capsule["circle"]["tools"] = ["execute"]
        self.assertEqual(Ward(registry, self.athanor.approvals()).evaluate(capsule).status, "REJECTED")

    def test_manual_working_transition_is_deprecated(self) -> None:
        program_id, _ = self.athanor.create_program("memory", "Memory")
        self.athanor.draft_protocol("PT-001", program_id, "Memory", "Compute metrics.")
        self.athanor.seal_protocol("PT-001")
        working_id, _ = self.athanor.create_working("computational-study@0.2.1", program_id, "PT-001")
        with self.assertRaisesRegex(AthanorError, "manual Working advancement is deprecated"):
            self.athanor.advance_working(working_id, "skip", [])

    def test_working_rejects_unregistered_rite(self) -> None:
        program_id, _ = self.athanor.create_program("memory", "Memory")
        self.athanor.draft_protocol("PT-001", program_id, "Memory", "Compute metrics.")
        self.athanor.seal_protocol("PT-001")
        with self.assertRaisesRegex(AthanorError, "unknown Rite"):
            self.athanor.create_working("anything@9", program_id, "PT-001")

    def test_agent_contract_rejects_empty_object(self) -> None:
        with self.assertRaisesRegex(AthanorError, "validation failed"):
            validate_instance("agent-contract-1.0.json", {})
