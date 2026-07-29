import json
import math
import tempfile
import unittest
from pathlib import Path

from benchwork.athanor import Athanor, AthanorError, content_sigil
from benchwork.schema_validation import validate_instance


class AlembicTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)
        self.program_id, _ = self.athanor.create_program("alembic-study", "Alembic study")
        self.athanor.draft_protocol(
            "PT-001",
            self.program_id,
            "Registered comparison",
            "Aggregate the registered metrics over included completed runs.",
        )
        self.athanor.seal_protocol("PT-001")
        self.athanor.create_experiment(
            "EX-001",
            self.program_id,
            "PT-001",
            "Does the treatment improve the registered score?",
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_experiment_requires_a_matching_frozen_protocol(self) -> None:
        other_program, _ = self.athanor.create_program("other-study", "Other study")
        with self.assertRaisesRegex(AthanorError, "does not match Protocol"):
            self.athanor.create_experiment(
                "EX-002",
                other_program,
                "PT-001",
                "Mismatched?",
            )
        with self.assertRaisesRegex(AthanorError, "already exists"):
            self.athanor.create_experiment(
                "EX-001",
                self.program_id,
                "PT-001",
                "Duplicate?",
            )
        experiment = self.athanor.experiments()["EX-001"]
        self.assertEqual(experiment["status"], "PLANNED")
        self.assertIsNone(experiment["hypothesis_id"])

    def test_run_inclusion_requires_completed_status_and_metrics(self) -> None:
        with self.assertRaisesRegex(AthanorError, "only a completed Run"):
            self.athanor.record_run("RUN-001", "EX-001", "FAILED", True, {"score": 1.0})
        with self.assertRaisesRegex(AthanorError, "at least one metric"):
            self.athanor.record_run("RUN-001", "EX-001", "COMPLETED", True)
        with self.assertRaisesRegex(AthanorError, "finite numeric"):
            self.athanor.record_run(
                "RUN-001",
                "EX-001",
                "COMPLETED",
                True,
                {"score": math.inf},
            )
        with self.assertRaisesRegex(AthanorError, "seed must be an integer"):
            self.athanor.record_run(
                "RUN-001",
                "EX-001",
                "COMPLETED",
                True,
                {"score": 1.0},
                seed=1.5,
            )

        with self.assertRaisesRegex(AthanorError, "validation failed"):
            validate_instance(
                "run-1.0.json",
                {
                    "schema_version": "run/1.0",
                    "run_id": "RUN-INVALID",
                    "program_id": self.program_id,
                    "protocol_id": "PT-001",
                    "experiment_id": "EX-001",
                    "status": "FAILED",
                    "analysis_included": True,
                    "seed": None,
                    "metrics": {},
                    "artifacts": [],
                },
            )

    def test_analysis_is_deterministic_and_preserves_all_run_outcomes(self) -> None:
        self.athanor.record_run(
            "RUN-002",
            "EX-001",
            "COMPLETED",
            True,
            {"score": 3.0, "latency": 7.0},
            seed=2,
        )
        self.athanor.record_run(
            "RUN-001",
            "EX-001",
            "COMPLETED",
            True,
            {"score": 1.0, "latency": 5.0},
            seed=1,
        )
        self.athanor.record_run("RUN-003", "EX-001", "FAILED", False)
        self.athanor.record_run(
            "RUN-004",
            "EX-001",
            "COMPLETED",
            False,
            {"score": -10.0, "latency": 99.0},
            seed=4,
            exclusion_reason="Registered outlier policy.",
        )

        bundle, sigil, receipt, path = self.athanor.compute_analysis(self.program_id, "PT-001")

        self.assertEqual(bundle["bundle_id"], "RB-001")
        self.assertEqual([run["run_id"] for run in bundle["runs"]], ["RUN-001", "RUN-002", "RUN-003", "RUN-004"])
        self.assertEqual(bundle["included_run_ids"], ["RUN-001", "RUN-002"])
        self.assertEqual(bundle["excluded_run_ids"], ["RUN-003", "RUN-004"])
        self.assertEqual(bundle["metrics"]["score"]["n"], 2)
        self.assertEqual(bundle["metrics"]["score"]["mean"], 2.0)
        self.assertAlmostEqual(bundle["metrics"]["score"]["sample_stddev"], math.sqrt(2.0))
        self.assertAlmostEqual(bundle["metrics"]["score"]["ci95_lower"], 0.04)
        self.assertAlmostEqual(bundle["metrics"]["score"]["ci95_upper"], 3.96)
        self.assertEqual(sigil, content_sigil(bundle))
        self.assertTrue(receipt.sigil.startswith("sha256:"))
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), bundle)
        self.assertEqual(self.athanor.result_bundles()["RB-001"], bundle)

    def test_analysis_rejects_no_eligible_runs_without_writing_event(self) -> None:
        self.athanor.record_run("RUN-001", "EX-001", "FAILED", False)
        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "at least one completed"):
            self.athanor.compute_analysis(self.program_id, "PT-001")
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)
        self.assertFalse((self.root / ".benchwork" / "results").exists())

    def test_analysis_rejects_inconsistent_metric_sets(self) -> None:
        self.athanor.record_run("RUN-001", "EX-001", "COMPLETED", True, {"score": 1.0})
        self.athanor.record_run(
            "RUN-002",
            "EX-001",
            "COMPLETED",
            True,
            {"score": 2.0, "latency": 5.0},
        )
        with self.assertRaisesRegex(AthanorError, "same metric set"):
            self.athanor.compute_analysis(self.program_id, "PT-001")

    def test_single_run_marks_uncertainty_as_unavailable(self) -> None:
        self.athanor.record_run("RUN-001", "EX-001", "COMPLETED", True, {"score": 2.0})
        bundle, _, _, _ = self.athanor.compute_analysis(self.program_id, "PT-001")
        summary = bundle["metrics"]["score"]
        self.assertEqual(summary["mean"], 2.0)
        self.assertIsNone(summary["sample_stddev"])
        self.assertIsNone(summary["ci95_lower"])
        self.assertIsNone(summary["ci95_upper"])

    def test_run_records_are_immutable(self) -> None:
        self.athanor.record_run("RUN-001", "EX-001", "FAILED", False)
        with self.assertRaisesRegex(AthanorError, "already exists"):
            self.athanor.record_run("RUN-001", "EX-001", "COMPLETED", True, {"score": 1.0})
