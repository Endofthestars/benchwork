import tempfile
import unittest
from pathlib import Path

from benchwork.athanor import Athanor, AthanorError, content_sigil


class ScientificCanonTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)
        self.source = {
            "uri": "papers/source.json",
            "sigil": "sha256:" + "1" * 64,
        }

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _prepare_bundle(self) -> tuple[str, dict]:
        program_id, _ = self.athanor.create_program("canon-study", "Canon study")
        self.athanor.record_evidence(
            "EV-001",
            program_id,
            self.source,
            "The treatment improved the registered score in prior work.",
            {
                "source_resolved": True,
                "content_inspected": True,
                "claim_relation_verified": False,
                "locally_reproduced": False,
            },
        )
        self.athanor.create_claim(
            "CL-001",
            program_id,
            "empirical",
            "The treatment can improve the registered score.",
            [{"evidence_id": "EV-001", "relation": "SUPPORTS"}],
        )
        self.athanor.create_hypothesis(
            "HY-001",
            program_id,
            ["CL-001"],
            "The treatment improves score under the registered conditions.",
            "Mean score is greater than the baseline mean.",
        )
        self.athanor.draft_protocol(
            "PT-001",
            program_id,
            "Registered treatment comparison",
            "Compute the registered score across included completed runs.",
            ["HY-001"],
        )
        self.athanor.seal_protocol("PT-001")
        self.athanor.create_experiment(
            "EX-001",
            program_id,
            "PT-001",
            "Does the treatment improve score?",
            "HY-001",
        )
        self.athanor.record_run(
            "RUN-001",
            "EX-001",
            "COMPLETED",
            True,
            {"score": 0.82},
            seed=1,
        )
        bundle, _, _, _ = self.athanor.compute_analysis(program_id, "PT-001")
        return program_id, bundle

    def test_evidence_to_sealed_decision_is_replayable(self) -> None:
        program_id, bundle = self._prepare_bundle()
        assessment_id, assessment_receipt = self.athanor.review_result(
            bundle["bundle_id"],
            "The registered result supports the hypothesis.",
            ["Only one completed run is available."],
            [
                {
                    "claim_id": "CL-001",
                    "status": "SUPPORTED",
                    "rationale": "The registered score moved in the predicted direction.",
                }
            ],
            [
                {
                    "hypothesis_id": "HY-001",
                    "status": "SUPPORTED",
                    "rationale": "The observed score satisfies the registered prediction.",
                }
            ],
        )
        decision_id, decision_receipt = self.athanor.seal_decision(
            program_id,
            "CONTINUE",
            [assessment_id],
            "Collect more runs while preserving the registered design.",
        )

        state = self.athanor.replay()
        program = state["programs"][program_id]
        self.assertEqual(program["status"], "EVALUATED")
        self.assertEqual(program["evidence"], ["EV-001"])
        self.assertEqual(program["claims"], ["CL-001"])
        self.assertEqual(program["hypotheses"], ["HY-001"])
        self.assertEqual(program["assessments"], ["AS-001"])
        self.assertEqual(program["decisions"], ["DE-001"])

        evidence = state["evidence"]["EV-001"]
        self.assertTrue(evidence["verification"]["claim_relation_verified"])
        self.assertEqual(
            evidence["claim_relations"],
            [{"claim_id": "CL-001", "relation": "SUPPORTS"}],
        )
        self.assertEqual(state["claims"]["CL-001"]["status"], "SUPPORTED")
        self.assertEqual(state["hypotheses"]["HY-001"]["status"], "SUPPORTED")
        self.assertEqual(state["protocols"]["PT-001"]["hypothesis_ids"], ["HY-001"])

        assessment = state["assessments"][assessment_id]
        self.assertEqual(assessment["result_bundle_id"], "RB-001")
        self.assertEqual(assessment["result_bundle"]["sigil"], content_sigil(bundle))
        self.assertEqual(assessment["review_receipt"], assessment_receipt.receipt_id)
        decision = state["decisions"][decision_id]
        self.assertEqual(decision["status"], "SEALED")
        self.assertEqual(decision["seal_receipt"], decision_receipt.receipt_id)

        claim_trace = self.athanor.trace("CL-001")
        self.assertEqual(
            [event["type"] for event in claim_trace],
            ["claim.created", "hypothesis.created", "assessment.recorded"],
        )

    def test_unverified_evidence_cannot_support_a_claim(self) -> None:
        program_id, _ = self.athanor.create_program("verification-study", "Verification")
        self.athanor.record_evidence(
            "EV-001",
            program_id,
            self.source,
            "An unresolved observation.",
        )
        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "resolved and inspected"):
            self.athanor.create_claim(
                "CL-001",
                program_id,
                "empirical",
                "A premature claim.",
                [{"evidence_id": "EV-001", "relation": "SUPPORTS"}],
            )
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

        self.athanor.verify_evidence(
            "EV-001",
            ["source_resolved", "content_inspected"],
        )
        self.athanor.create_claim(
            "CL-001",
            program_id,
            "empirical",
            "A now traceable claim.",
            [{"evidence_id": "EV-001", "relation": "SUPPORTS"}],
        )
        with self.assertRaisesRegex(AthanorError, "already verified"):
            self.athanor.verify_evidence("EV-001", ["source_resolved"])

    def test_cross_program_references_fail_before_append(self) -> None:
        first, _ = self.athanor.create_program("first-study", "First")
        second, _ = self.athanor.create_program("second-study", "Second")
        self.athanor.record_evidence(
            "EV-001",
            first,
            self.source,
            "A verified observation.",
            {
                "source_resolved": True,
                "content_inspected": True,
                "claim_relation_verified": False,
                "locally_reproduced": False,
            },
        )
        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "unknown Program Evidence"):
            self.athanor.create_claim(
                "CL-001",
                second,
                "empirical",
                "A cross-program claim.",
                [{"evidence_id": "EV-001", "relation": "SUPPORTS"}],
            )
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

    def test_assessment_requires_registered_hypothesis_and_unique_findings(self) -> None:
        _, bundle = self._prepare_bundle()
        duplicate = {
            "hypothesis_id": "HY-001",
            "status": "SUPPORTED",
            "rationale": "Registered result.",
        }
        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "must be unique"):
            self.athanor.review_result(
                bundle["bundle_id"],
                "Duplicate review.",
                [],
                [],
                [duplicate, duplicate],
            )
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

        with self.assertRaisesRegex(AthanorError, "not registered"):
            self.athanor.review_result(
                bundle["bundle_id"],
                "Unregistered review.",
                [],
                [],
                [
                    {
                        "hypothesis_id": "HY-999",
                        "status": "INCONCLUSIVE",
                        "rationale": "Not registered.",
                    }
                ],
            )
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

    def test_late_evidence_does_not_regress_program_status(self) -> None:
        program_id, bundle = self._prepare_bundle()
        self.assertEqual(self.athanor.programs()[program_id]["status"], "RESULT_READY")
        self.athanor.record_evidence(
            "EV-002",
            program_id,
            {
                "uri": "papers/late.json",
                "sigil": "sha256:" + "2" * 64,
            },
            "A late observation.",
        )
        self.assertEqual(self.athanor.programs()[program_id]["status"], "RESULT_READY")
        self.assertEqual(bundle["bundle_id"], "RB-001")
