import hashlib
import tempfile
import unittest
from pathlib import Path

from benchwork.athanor import Athanor, AthanorError


class LifecycleV11Test(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _exploratory_study(self) -> tuple[str, str, str, str]:
        program_id, _ = self.athanor.create_program("lifecycle-study", "Lifecycle study")
        self.athanor.draft_protocol(
            "PT-001",
            program_id,
            "Exploratory lifecycle",
            "Aggregate included completed runs.",
            study_mode="exploratory",
        )
        self.athanor.seal_protocol("PT-001")
        working_id, _ = self.athanor.create_working(
            "computational-study@0.2.0",
            program_id,
            "PT-001",
        )
        self.athanor.create_experiment(
            "EX-001",
            program_id,
            "PT-001",
            "What does the registered pilot show?",
        )
        return program_id, "PT-001", working_id, "EX-001"

    def test_working_advances_only_from_matching_canonical_events(self) -> None:
        program_id, protocol_id, working_id, experiment_id = self._exploratory_study()
        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "cannot be read"):
            self.athanor.register_artifact(
                "AR-FAKE",
                program_id,
                "implementation",
                {"uri": "missing.bin", "sigil": "sha256:" + "1" * 64},
                working_id,
            )
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)
        self.assertEqual(self.athanor.workings()[working_id]["stage"], "IMPLEMENTATION")

        implementation = self.root / "implementation.bin"
        implementation.write_bytes(b"registered implementation")
        self.athanor.register_artifact(
            "AR-001",
            program_id,
            "implementation",
            {
                "uri": "implementation.bin",
                "sigil": "sha256:"
                + hashlib.sha256(b"registered implementation").hexdigest(),
            },
            working_id,
            [protocol_id],
        )
        self.assertEqual(self.athanor.workings()[working_id]["stage"], "PILOT")
        self.assertEqual(self.athanor.programs()[program_id]["status"], "IMPLEMENTED")

        self.athanor.transition_experiment(experiment_id, "implemented")
        self.athanor.transition_experiment(experiment_id, "pilot-started")
        self.athanor.record_run(
            "RUN-001",
            experiment_id,
            "COMPLETED",
            True,
            {"score": 0.75},
            seed=7,
            phase="PILOT",
        )
        self.assertEqual(self.athanor.workings()[working_id]["stage"], "ANALYSIS")
        self.assertEqual(self.athanor.programs()[program_id]["status"], "PILOTED")
        self.athanor.transition_experiment(experiment_id, "pilot-completed")
        self.athanor.transition_experiment(experiment_id, "formal-started")
        self.assertEqual(self.athanor.programs()[program_id]["status"], "RUNNING")

        bundle, _, _, _ = self.athanor.compute_analysis(program_id, protocol_id)
        self.assertEqual(self.athanor.workings()[working_id]["stage"], "REVIEW")
        assessment_id, _ = self.athanor.review_result(
            bundle["bundle_id"],
            "The exploratory pilot produced an inspectable result.",
            ["Formal replication remains outstanding."],
            [],
            [],
        )
        self.assertEqual(self.athanor.workings()[working_id]["stage"], "DECISION")
        decision_id, _ = self.athanor.seal_decision(
            program_id,
            "STOP",
            [assessment_id],
            "The exploratory objective is complete.",
        )
        working = self.athanor.workings()[working_id]
        self.assertEqual(working["stage"], "COMPLETED")
        self.assertEqual(working["status"], "COMPLETED")
        self.assertEqual(working["history"][-1]["object_id"], decision_id)
        self.assertEqual(self.athanor.programs()[program_id]["status"], "EVALUATED")

        self.athanor.close_program(program_id)
        self.assertEqual(self.athanor.programs()[program_id]["status"], "CLOSED")

    def test_experiment_transitions_are_monotonic(self) -> None:
        _, _, _, experiment_id = self._exploratory_study()
        with self.assertRaisesRegex(AthanorError, "invalid Experiment transition"):
            self.athanor.transition_experiment(experiment_id, "pilot-started")
        for transition, status in (
            ("implemented", "IMPLEMENTED"),
            ("pilot-started", "PILOT_RUNNING"),
            ("pilot-completed", "PILOT_COMPLETED"),
            ("formal-started", "FORMAL_RUNNING"),
            ("completed", "COMPLETED"),
        ):
            self.athanor.transition_experiment(experiment_id, transition)
            self.assertEqual(self.athanor.experiments()[experiment_id]["status"], status)
        with self.assertRaisesRegex(AthanorError, "invalid Experiment transition"):
            self.athanor.transition_experiment(experiment_id, "cancelled")

    def test_confirmatory_and_exploratory_hypothesis_contracts(self) -> None:
        program_id, _ = self.athanor.create_program("study-modes", "Study modes")
        with self.assertRaisesRegex(AthanorError, "requires at least one Hypothesis"):
            self.athanor.draft_protocol(
                "PT-001",
                program_id,
                "Invalid confirmatory protocol",
                "Compare registered groups.",
                study_mode="confirmatory",
            )
        self.athanor.draft_protocol(
            "PT-002",
            program_id,
            "Exploratory protocol",
            "Describe registered observations.",
            study_mode="exploratory",
        )
        self.athanor.seal_protocol("PT-002")
        with self.assertRaisesRegex(AthanorError, "not registered by Protocol"):
            self.athanor.create_experiment(
                "EX-001",
                program_id,
                "PT-002",
                "Can an unknown hypothesis be referenced?",
                "HY-MISSING",
            )

    def test_terminal_run_and_exclusion_contracts(self) -> None:
        _, _, _, experiment_id = self._exploratory_study()
        for transient in ("QUEUED", "RUNNING"):
            with self.assertRaisesRegex(AthanorError, "status must be terminal"):
                self.athanor.record_run(
                    f"RUN-{transient}",
                    experiment_id,
                    transient,
                    False,
                )
        with self.assertRaisesRegex(AthanorError, "requires an exclusion reason"):
            self.athanor.record_run(
                "RUN-EXCLUDED",
                experiment_id,
                "COMPLETED",
                False,
                {"score": 0.1},
            )
        self.athanor.record_run(
            "RUN-EXCLUDED",
            experiment_id,
            "COMPLETED",
            False,
            {"score": 0.1},
            exclusion_reason="Registered exclusion rule.",
        )
        disposition = self.athanor.runs()["RUN-EXCLUDED"]["analysis_disposition"]
        self.assertFalse(disposition["included"])
        self.assertEqual(disposition["reason"], "Registered exclusion rule.")


if __name__ == "__main__":
    unittest.main()
