import tempfile
import unittest
from pathlib import Path

from benchwork.athanor import Athanor
from benchwork.guidance import next_step, program_summary


class ProductGuidanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_next_starts_or_selects_when_no_program_is_active(self) -> None:
        step = next_step(self.athanor.replay(), None)
        self.assertEqual(step["action"], "START_OR_SELECT_PROGRAM")
        self.assertIn("bwork start", step["command"])
        self.assertEqual(step["attention"], [])

    def test_new_program_is_summarized_with_one_investigation_step(self) -> None:
        program_id, _ = self.athanor.create_program("guidance", "Guidance")
        state = self.athanor.replay()

        step = next_step(state, program_id)
        self.assertEqual(step["action"], "INVESTIGATE")
        self.assertEqual(step["command"], f"bwork investigate --program {program_id}")
        summary = program_summary(state, program_id)
        self.assertEqual(summary["active_program_id"], program_id)
        self.assertEqual(summary["title"], "Guidance")
        self.assertEqual(summary["counts"]["evidence"], 0)
        self.assertEqual(summary["next"], step)

    def test_unknown_selected_program_requests_a_valid_selection(self) -> None:
        step = next_step(self.athanor.replay(), "RP-404")
        self.assertEqual(step["action"], "SELECT_PROGRAM")
        self.assertEqual(step["program_id"], "RP-404")

    def test_closed_program_is_terminal(self) -> None:
        program_id, _ = self.athanor.create_program("closed", "Closed")
        state = self.athanor.replay()
        state["programs"][program_id]["status"] = "CLOSED"
        step = next_step(state, program_id)
        self.assertEqual(step["action"], "DONE")
        self.assertEqual(step["command"], "")

    def test_registered_pilot_runs_advance_instead_of_recommending_duplicates(self) -> None:
        program_id, _ = self.athanor.create_program("pilot-guidance", "Pilot guidance")
        self.athanor.record_evidence(
            "EV-001",
            program_id,
            {"uri": "note.txt", "sigil": "sha256:" + "0" * 64},
            "The pilot has a testable signal.",
            {"source_resolved": True, "content_inspected": True},
        )
        self.athanor.create_claim(
            "CL-001",
            program_id,
            "empirical",
            "The treatment changes the score.",
            [{"evidence_id": "EV-001", "relation": "SUPPORTS"}],
        )
        self.athanor.verify_claim_relation("CL-001", "EV-001")
        self.athanor.create_hypothesis(
            "HY-001",
            program_id,
            ["CL-001"],
            "The treatment changes the score.",
            "Treatment and baseline scores differ.",
        )
        self.athanor.seal_research_question(program_id, "Does treatment change the score?")
        self.athanor.draft_protocol(
            "PT-001",
            program_id,
            "Pilot guidance",
            "Compare the registered pilot arms.",
            study_mode="exploratory",
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
                "practical_significance_thresholds": {},
                "pilot_run_ids": ["RUN-BASE", "RUN-TREAT"],
                "expected_run_ids": ["RUN-BASE", "RUN-TREAT"],
            },
        )
        self.athanor.seal_protocol("PT-001")
        self.athanor.create_experiment("EX-001", program_id, "PT-001", "Does it work?")
        self.athanor.transition_experiment("EX-001", "implemented")
        self.athanor.transition_experiment("EX-001", "pilot-started")

        missing = next_step(self.athanor.replay(), program_id)
        self.assertEqual(missing["action"], "EXECUTE_PILOT")
        self.assertIn("RUN-BASE", missing["command"])
        for run_id, arm, score in (
            ("RUN-BASE", "baseline", 0.5),
            ("RUN-TREAT", "treatment", 0.7),
        ):
            self.athanor.record_run(
                run_id,
                "EX-001",
                "COMPLETED",
                True,
                {"score": score},
                phase="PILOT",
                arm=arm,
            )

        complete = next_step(self.athanor.replay(), program_id)
        self.assertEqual(complete["action"], "COMPLETE_PILOT")
        self.assertIn("pilot-completed", complete["command"])

    def test_wrong_registered_pilot_arms_require_repair(self) -> None:
        self.test_registered_pilot_runs_advance_instead_of_recommending_duplicates()
        # Rebuild a state variant to exercise guidance without rewriting canonical history.
        state = self.athanor.replay()
        state["runs"]["RUN-TREAT"]["arm"] = "baseline"
        program_id = next(iter(state["programs"]))
        step = next_step(state, program_id)
        self.assertEqual(step["action"], "REPAIR_PILOT_REGISTRATION")
        self.assertIn("treatment", step["reason"])


if __name__ == "__main__":
    unittest.main()
