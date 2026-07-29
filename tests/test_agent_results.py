import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from benchwork.athanor import Athanor, AthanorError
from benchwork.circle import CapsuleStore, CapabilityRegistry, DEFAULT_CAPABILITIES
from benchwork.tasks import TaskService


class AgentResultTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)
        self.registry = CapabilityRegistry(self.root)
        self.capsules = CapsuleStore(self.root)
        self.registry.initialize()
        self.program_id, _ = self.athanor.create_program(
            "agent-results",
            "Agent Results",
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _capsule(self, capability: str = "bench.code.inspect", host: str = "cli") -> dict:
        contract = self.registry.get(capability)
        return TaskService(
            self.athanor,
            self.registry,
            self.capsules,
        ).create(
            capability,
            self.program_id,
            f"Execute {capability}",
            {
                "tools": contract["allowed_tools"],
                "time_budget_seconds": 60,
                "network": False,
            },
            host=host,
        )

    def _result(
        self,
        capsule: dict,
        *,
        status: str = "COMPLETED",
        schema: str | None = None,
        provenance: dict | None = None,
    ) -> dict:
        outputs = []
        if status == "COMPLETED":
            output_schema = schema or capsule["expected_outputs"][0]["schema"]
            semantic_data = {
                "code-inspection-result/1.0": {
                    "inspected_files": ["src/benchwork/athanor.py"],
                    "findings": ["The inspected transition is deterministic."],
                    "tests_considered": ["tests/test_agent_results.py"],
                    "residual_risks": [],
                },
                "code-modification-result/1.0": {
                    "patch": "diff --git a/example.py b/example.py",
                    "changed_files": ["example.py"],
                    "tests_run": ["python -m unittest"],
                    "validation": "The bounded validation passed.",
                    "residual_risks": [],
                },
                "evidence-discovery-result/1.0": {
                    "queries": ["registered evidence query"],
                    "sources": [
                        {"uri": "https://example.test/source", "title": "Source"}
                    ],
                    "screened_count": 1,
                    "candidate_evidence": [
                        {
                            "source_uri": "https://example.test/source",
                            "claim": "A candidate claim.",
                            "relevance": "Directly addresses the query.",
                            "uncertainty": "Requires local inspection.",
                        }
                    ],
                    "unresolved_queries": [],
                    "limitations": ["Single-source proposal."],
                },
                "study-design-result/1.0": {
                    "protocol_proposal": {"title": "Registered study proposal"},
                    "hypotheses": ["The intervention changes the registered metric."],
                    "estimand": "mean difference",
                    "validity_threats": ["Measurement drift."],
                    "open_issues": [],
                },
            }.get(output_schema, {"finding": "inspection complete"})
            output = {
                "schema_version": output_schema,
                "task_id": capsule["task_id"],
                "summary": "A bounded Provider-neutral proposal.",
                "data": semantic_data,
            }
            path = self.root / "proposals" / f"{capsule['task_id']}.json"
            path.parent.mkdir(exist_ok=True)
            blob = json.dumps(output, sort_keys=True).encode()
            path.write_bytes(blob)
            outputs.append(
                {
                    "schema": output_schema,
                    "uri": str(path.relative_to(self.root)),
                    "blob_sigil": "sha256:" + hashlib.sha256(blob).hexdigest(),
                }
            )
        result = {
            "schema_version": "agent-result/1.1",
            "task_id": capsule["task_id"],
            "snapshot_sigil": capsule["snapshot"]["snapshot_sigil"],
            "capability_contract_sigil": capsule["capability"]["contract_sigil"],
            "status": status,
            "outputs": outputs,
        }
        if provenance is not None:
            result["provenance"] = provenance
        return result

    def _replace_output_data(self, result: dict, data: dict) -> None:
        output_path = self.root / result["outputs"][0]["uri"]
        document = json.loads(output_path.read_text(encoding="utf-8"))
        document["data"] = data
        blob = json.dumps(document, sort_keys=True).encode()
        output_path.write_bytes(blob)
        result["outputs"][0]["blob_sigil"] = (
            "sha256:" + hashlib.sha256(blob).hexdigest()
        )

    def test_agent_result_is_accepted_once_and_replayable(self) -> None:
        capsule = self._capsule()
        result = self._result(
            capsule,
            provenance={
                "provider": "local-fixture",
                "runtime": "unittest",
                "host": "cli",
            },
        )
        receipt = self.athanor.accept_agent_result(result)

        accepted = self.athanor.agent_results()[capsule["task_id"]]
        self.assertEqual(accepted["capability"]["id"], "bench.code.inspect")
        self.assertEqual(accepted["capsule_sigil"], capsule["capsule_sigil"])
        self.assertEqual(accepted["acceptance_receipt"], receipt.receipt_id)
        self.assertEqual(accepted["provenance"]["runtime"], "unittest")
        self.assertEqual(
            [event["type"] for event in self.athanor.trace(capsule["task_id"])],
            ["agent-result.accepted"],
        )

        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "already has"):
            self.athanor.accept_agent_result(result)
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

    def test_result_requires_matching_bindings_and_passing_ward(self) -> None:
        capsule = self._capsule()
        mismatched = self._result(capsule)
        mismatched["snapshot_sigil"] = "sha256:" + "3" * 64
        with self.assertRaisesRegex(AthanorError, "Snapshot Sigil"):
            self.athanor.accept_agent_result(mismatched)

        gated = self._capsule("bench.code.modify")
        result = self._result(gated)
        with self.assertRaisesRegex(AthanorError, "WAITING_FOR_APPROVAL"):
            self.athanor.accept_agent_result(result)

        approval = self.athanor.grant_approval(
            gated,
            "Reviewed bounded write access.",
        )
        approval_record = self.athanor.approvals()[gated["task_id"]]
        self.assertEqual(
            approval_record["capability_contract_sigil"],
            gated["capability"]["contract_sigil"],
        )
        accepted = self.athanor.accept_agent_result(result)
        self.assertNotEqual(approval.receipt_id, accepted.receipt_id)
        self.assertEqual(
            self.athanor.agent_results()[gated["task_id"]]["status"],
            "COMPLETED",
        )

    def test_program_change_makes_result_stale(self) -> None:
        capsule = self._capsule()
        result = self._result(capsule)
        self.athanor.draft_protocol(
            "PT-001",
            self.program_id,
            "Later protocol",
            "This canonical object was added after Task creation.",
        )

        with self.assertRaisesRegex(AthanorError, "STALE_TASK"):
            self.athanor.accept_agent_result(result)

    def test_unrelated_program_event_does_not_make_result_stale(self) -> None:
        capsule = self._capsule()
        result = self._result(capsule)
        self.athanor.create_program("unrelated", "Unrelated Program")

        self.athanor.accept_agent_result(result)
        self.assertIn(capsule["task_id"], self.athanor.agent_results())

    def test_failed_result_may_be_accepted_without_outputs(self) -> None:
        capsule = self._capsule()
        result = self._result(capsule, status="FAILED")

        self.athanor.accept_agent_result(result)
        accepted = self.athanor.agent_results()[capsule["task_id"]]
        self.assertEqual(accepted["status"], "FAILED")
        self.assertEqual(accepted["outputs"], [])

    def test_snapshot_file_mutation_is_rejected(self) -> None:
        capsule = self._capsule()
        result = self._result(capsule)
        snapshot_path = (
            self.root
            / ".benchwork"
            / "snapshots"
            / f"{capsule['snapshot']['snapshot_id']}.json"
        )
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot["objects"][0]["object_sigil"] = "sha256:" + "7" * 64
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

        with self.assertRaisesRegex(AthanorError, "Snapshot Sigil mismatch"):
            self.athanor.accept_agent_result(result)

    def test_capability_change_invalidates_result_acceptance(self) -> None:
        capsule = self._capsule()
        result = self._result(capsule)
        path = self.root / ".benchwork" / "capabilities.json"
        registry = json.loads(path.read_text(encoding="utf-8"))
        registry["capabilities"]["bench.code.inspect"]["max_time_seconds"] += 1
        path.write_text(json.dumps(registry), encoding="utf-8")

        with self.assertRaisesRegex(AthanorError, "Capability Contract changed"):
            self.athanor.accept_agent_result(result)

    def test_completed_and_output_contracts_fail_closed(self) -> None:
        capsule = self._capsule()
        mismatched_contract = self._result(capsule)
        mismatched_contract["capability_contract_sigil"] = "sha256:" + "8" * 64
        with self.assertRaisesRegex(AthanorError, "Capability Contract Sigil"):
            self.athanor.accept_agent_result(mismatched_contract)

        empty = self._result(capsule, status="FAILED")
        empty["status"] = "COMPLETED"
        with self.assertRaisesRegex(AthanorError, "validation failed"):
            self.athanor.accept_agent_result(empty)

        wrong_schema = self._result(
            capsule,
            schema="study-audit-result/1.0",
        )
        with self.assertRaisesRegex(AthanorError, "not expected"):
            self.athanor.accept_agent_result(wrong_schema)

    def test_output_blob_and_schema_are_verified(self) -> None:
        capsule = self._capsule()
        result = self._result(capsule)
        result["outputs"][0]["blob_sigil"] = "sha256:" + "9" * 64
        with self.assertRaisesRegex(AthanorError, "Blob Sigil mismatch"):
            self.athanor.accept_agent_result(result)

        result = self._result(capsule)
        output_path = self.root / result["outputs"][0]["uri"]
        document = json.loads(output_path.read_text(encoding="utf-8"))
        document["schema_version"] = "study-audit-result/1.0"
        blob = json.dumps(document, sort_keys=True).encode()
        output_path.write_bytes(blob)
        result["outputs"][0]["blob_sigil"] = (
            "sha256:" + hashlib.sha256(blob).hexdigest()
        )
        with self.assertRaisesRegex(AthanorError, "validation failed"):
            self.athanor.accept_agent_result(result)

    def test_capability_outputs_reject_semantically_empty_data(self) -> None:
        evidence_capsule = self._capsule("bench.evidence.discover")
        evidence_result = self._result(evidence_capsule)
        self._replace_output_data(evidence_result, {})
        with self.assertRaisesRegex(AthanorError, "validation failed"):
            self.athanor.accept_agent_result(evidence_result)

        design_capsule = self._capsule("bench.study.design")
        valid_design = {
            "protocol_proposal": {"title": "Registered study proposal"},
            "hypotheses": ["The intervention changes the metric."],
            "estimand": "mean difference",
            "validity_threats": ["Measurement drift."],
            "open_issues": [],
        }
        for missing in ("hypotheses", "estimand", "validity_threats"):
            with self.subTest(missing=missing):
                design_result = self._result(design_capsule)
                self._replace_output_data(
                    design_result,
                    {
                        key: value
                        for key, value in valid_design.items()
                        if key != missing
                    },
                )
                with self.assertRaisesRegex(AthanorError, "validation failed"):
                    self.athanor.accept_agent_result(design_result)

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
        migrated = capabilities["bench.code.inspect"]
        self.assertEqual(migrated["max_time_seconds"], 123)
        self.assertEqual(migrated["contract_version"], "1.0")
        self.assertEqual(
            migrated["expected_outputs"],
            [{"schema": "code-inspection-result/1.0"}],
        )

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
