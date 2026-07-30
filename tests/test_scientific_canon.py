import hashlib
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
        self.athanor.verify_claim_relation("CL-001", "EV-001")
        self.athanor.create_hypothesis(
            "HY-001",
            program_id,
            ["CL-001"],
            "The treatment improves score under the registered conditions.",
            "Mean score is greater than the baseline mean.",
        )
        self.athanor.seal_research_question(
            program_id,
            "Does the treatment improve the registered score?",
        )
        self.athanor.draft_protocol(
            "PT-001",
            program_id,
            "Registered treatment comparison",
            "Compute the registered score across included completed runs.",
            ["HY-001"],
            analysis_spec={
                "schema_version": "analysis-spec/1.0",
                "comparisons": [
                    {
                        "comparison_id": "CMP-001",
                        "experiment_id": "EX-001",
                        "arms": ["baseline", "treatment"],
                        "metric": "score",
                        "estimand": "mean_difference",
                        "pairing": "none",
                        "uncertainty_method": "unavailable",
                        "confidence_level": 0.95,
                    }
                ],
                "multiple_comparison_policy": "none",
                "practical_significance_thresholds": {"score": 0.01},
                "expected_run_ids": ["RUN-000", "RUN-001"],
            },
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
            "RUN-000",
            "EX-001",
            "COMPLETED",
            True,
            {"score": 0.80},
            seed=1,
            arm="baseline",
        )
        self.athanor.record_run(
            "RUN-001",
            "EX-001",
            "COMPLETED",
            True,
            {"score": 0.82},
            seed=1,
            arm="treatment",
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
        self.assertEqual(
            evidence["claim_relations"],
            [
                {
                    "claim_id": "CL-001",
                    "relation": "SUPPORTS",
                    "status": "VERIFIED",
                }
            ],
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
        self.assertEqual(decision["seal_actor"]["actor_type"], "human")
        self.assertEqual(
            state["protocols"]["PT-001"]["seal_actor"]["actor_type"],
            "human",
        )
        self.assertEqual(
            program["research_question"]["actor"]["actor_type"],
            "human",
        )

        claim_trace = self.athanor.trace("CL-001")
        self.assertEqual(
            [event["type"] for event in claim_trace],
            [
                "claim.created",
                "claim_relation.proposed",
                "claim_relation.verified",
                "hypothesis.created",
                "assessment.recorded",
            ],
        )

    def test_claim_relation_requires_explicit_verification(self) -> None:
        program_id, _ = self.athanor.create_program("verification-study", "Verification")
        self.athanor.record_evidence(
            "EV-001",
            program_id,
            self.source,
            "An unresolved observation.",
        )
        self.athanor.create_claim(
            "CL-001",
            program_id,
            "empirical",
            "A proposed claim.",
            [{"evidence_id": "EV-001", "relation": "SUPPORTS"}],
        )
        relation = self.athanor.claims()["CL-001"]["evidence_relations"][0]
        self.assertEqual(relation["status"], "PROPOSED")
        with self.assertRaisesRegex(AthanorError, "resolved and inspected"):
            self.athanor.verify_claim_relation("CL-001", "EV-001")

        self.athanor.verify_evidence(
            "EV-001",
            ["source_resolved", "content_inspected"],
        )
        self.athanor.verify_claim_relation("CL-001", "EV-001")
        self.assertEqual(
            self.athanor.claims()["CL-001"]["evidence_relations"][0]["status"],
            "VERIFIED",
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

    def test_hypothesis_does_not_freeze_research_question(self) -> None:
        program_id, _ = self.athanor.create_program("rq-gate", "RQ Gate")
        self.athanor.record_evidence(
            "EV-001",
            program_id,
            self.source,
            "A registered observation.",
        )
        self.athanor.create_claim(
            "CL-001",
            program_id,
            "empirical",
            "A proposed relationship.",
            [{"evidence_id": "EV-001", "relation": "UNRESOLVED"}],
        )
        self.athanor.create_hypothesis(
            "HY-001",
            program_id,
            ["CL-001"],
            "A falsifiable hypothesis.",
            "The registered metric differs from baseline.",
        )
        self.assertEqual(
            self.athanor.programs()[program_id]["status"],
            "HYPOTHESES_REGISTERED",
        )

        self.athanor.seal_research_question(
            program_id,
            "Does the registered metric differ from baseline?",
            actor={
                "actor_id": "gate-policy",
                "actor_type": "policy",
                "host": "cli",
                "authenticated_by": "local-session",
            },
        )
        self.assertEqual(
            self.athanor.programs()[program_id]["status"],
            "RQ_FROZEN",
        )
        self.assertEqual(
            self.athanor.programs()[program_id]["research_question"]["actor"][
                "actor_type"
            ],
            "policy",
        )

    def test_locally_reproduced_cannot_be_manually_toggled(self) -> None:
        program_id, _ = self.athanor.create_program(
            "reproduction-gate",
            "Reproduction Gate",
        )
        with self.assertRaisesRegex(AthanorError, "canonical relation objects"):
            self.athanor.record_evidence(
                "EV-001",
                program_id,
                self.source,
                "A claimed local reproduction.",
                {
                    "source_resolved": True,
                    "content_inspected": True,
                    "claim_relation_verified": False,
                    "locally_reproduced": True,
                },
            )
        self.assertEqual(self.athanor.evidence(), {})

    def test_decision_gates_block_continue_and_allow_repair(self) -> None:
        program_id, bundle = self._prepare_bundle()
        assessment_id, _ = self.athanor.review_result(
            bundle["bundle_id"],
            "The result needs evidence repair.",
            ["One registered evidence source remains incomplete."],
            [],
            [
                {
                    "hypothesis_id": "HY-001",
                    "status": "INCONCLUSIVE",
                    "rationale": "The evidence inventory is incomplete.",
                }
            ],
        )
        self.athanor.open_issue(
            "IS-001",
            program_id,
            ["EV-001"],
            "CRITICAL",
            "Incomplete registered evidence",
            "A critical source must be inspected before continuation.",
        )

        with self.assertRaisesRegex(AthanorError, "CRITICAL"):
            self.athanor.seal_decision(
                program_id,
                "CONTINUE",
                [assessment_id],
                "Continue despite the issue.",
            )

        decision_id, _ = self.athanor.seal_decision(
            program_id,
            "REPAIR",
            [assessment_id],
            "Repair the registered evidence inventory.",
            ["Resolve IS-001 and repeat the registered assessment."],
        )
        decision = self.athanor.decisions()[decision_id]
        self.assertEqual(decision["outcome"], "REPAIR")
        self.assertEqual(decision["unresolved_issue_ids"], ["IS-001"])
        self.assertTrue(decision["required_actions"])

        with self.assertRaisesRegex(AthanorError, "lineage"):
            self.athanor.seal_decision(
                program_id,
                "PIVOT",
                [assessment_id],
                "Pivot without lineage.",
            )
        pivot_id, _ = self.athanor.seal_decision(
            program_id,
            "PIVOT",
            [assessment_id],
            "Pivot with preserved lineage.",
            lineage={
                "parent_program_id": program_id,
                "reason": "The registered evidence challenges the original framing.",
            },
        )
        self.assertEqual(
            self.athanor.decisions()[pivot_id]["lineage"]["parent_program_id"],
            program_id,
        )

        with self.assertRaisesRegex(AthanorError, "competing Assessments"):
            self.athanor.seal_decision(
                program_id,
                "REVIEW_REQUIRED",
                [assessment_id],
                "One Assessment is not a competition.",
            )

        stop_id, _ = self.athanor.seal_decision(
            program_id,
            "STOP",
            [assessment_id],
            "Stop while preserving uncertainty.",
        )
        stop = self.athanor.decisions()[stop_id]
        self.assertEqual(stop["unresolved_issue_ids"], ["IS-001"])
        self.assertEqual(
            stop["unresolved_uncertainties"],
            ["One registered evidence source remains incomplete."],
        )

        insufficient_id, _ = self.athanor.seal_decision(
            program_id,
            "INSUFFICIENT_EVIDENCE",
            [assessment_id],
            "No positive Claim finding is required.",
        )
        self.assertEqual(
            self.athanor.decisions()[insufficient_id]["outcome"],
            "INSUFFICIENT_EVIDENCE",
        )

    def test_reproduction_status_requires_canonical_objects(self) -> None:
        program_id, bundle = self._prepare_bundle()
        assessment_id, _ = self.athanor.review_result(
            bundle["bundle_id"],
            "Reproduction assessment.",
            [],
            [],
            [
                {
                    "hypothesis_id": "HY-001",
                    "status": "SUPPORTED",
                    "rationale": "The registered run matched the prediction.",
                }
            ],
        )
        reproduction = self.root / "artifacts" / "reproduction.json"
        reproduction.parent.mkdir(exist_ok=True)
        reproduction.write_text("reproduction", encoding="utf-8")
        self.athanor.register_artifact(
            "AR-001",
            program_id,
            "reproduction",
            {
                "uri": "artifacts/reproduction.json",
                "sigil": "sha256:" + hashlib.sha256(b"reproduction").hexdigest(),
            },
            assessment_id,
            ["RUN-001", bundle["bundle_id"]],
        )
        self.athanor.record_reproduction(
            "RR-001",
            "EV-001",
            ["RUN-001"],
            bundle["bundle_id"],
            ["AR-001"],
            assessment_id,
            "REPRODUCED",
        )

        reproduction = self.athanor.reproduction_records()["RR-001"]
        self.assertEqual(reproduction["status"], "REPRODUCED")
        self.assertEqual(
            self.athanor.evidence()["EV-001"]["reproduction_ids"],
            ["RR-001"],
        )

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
