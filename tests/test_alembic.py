import json
import math
import tempfile
import unittest
from pathlib import Path

from benchwork.alembic import build_result_bundle
from benchwork.athanor import Athanor, AthanorError, content_sigil


class AlembicTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)
        self.program_id, _ = self.athanor.create_program(
            "alembic-study",
            "Alembic study",
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _analysis_spec(
        self,
        *,
        experiment_id: str = "EX-001",
        pairing: str = "paired",
        method: str = "student_t",
        expected_run_ids: list[str] | None = None,
        bootstrap_seed: int = 17,
    ) -> dict:
        comparison = {
            "comparison_id": "CMP-001",
            "experiment_id": experiment_id,
            "arms": ["baseline", "treatment"],
            "metric": "score",
            "estimand": "mean_difference",
            "pairing": pairing,
            "uncertainty_method": method,
            "confidence_level": 0.95,
        }
        if method == "bootstrap":
            comparison["bootstrap_seed"] = bootstrap_seed
            comparison["bootstrap_samples"] = 1000
        return {
            "schema_version": "analysis-spec/1.0",
            "comparisons": [comparison],
            "multiple_comparison_policy": "none",
            "practical_significance_thresholds": {"score": 0.2},
            "expected_run_ids": expected_run_ids or [],
        }

    def _prepare(
        self,
        *,
        pairing: str = "paired",
        method: str = "student_t",
        expected_run_ids: list[str] | None = None,
    ) -> None:
        self.athanor.draft_protocol(
            "PT-001",
            self.program_id,
            "Registered comparison",
            "Compare treatment and baseline score without pooling Experiments.",
            study_mode="exploratory",
            analysis_spec=self._analysis_spec(
                pairing=pairing,
                method=method,
                expected_run_ids=expected_run_ids,
            ),
        )
        self.athanor.seal_protocol("PT-001")
        self.athanor.create_experiment(
            "EX-001",
            self.program_id,
            "PT-001",
            "Does the treatment improve the registered score?",
        )

    def _run(
        self,
        run_id: str,
        arm: str,
        score: float,
        seed: int,
        *,
        experiment_id: str = "EX-001",
        included: bool = True,
        reason: str | None = None,
    ) -> None:
        self.athanor.record_run(
            run_id,
            experiment_id,
            "COMPLETED",
            included,
            {"score": score},
            seed=seed,
            exclusion_reason=reason,
            arm=arm,
        )

    def test_student_t_interval_is_explicit_and_not_normal_approximation(self) -> None:
        self._prepare()
        for seed, baseline, treatment in (
            (1, 1.0, 1.4),
            (2, 2.0, 2.8),
            (3, 3.0, 3.9),
        ):
            self._run(f"RUN-B{seed}", "baseline", baseline, seed)
            self._run(f"RUN-T{seed}", "treatment", treatment, seed)

        bundle, sigil, receipt, path = self.athanor.compute_analysis(
            self.program_id,
            "PT-001",
        )
        metric = bundle["comparisons"][0]["metrics"]["score"]
        uncertainty = metric["uncertainty"]
        self.assertEqual(bundle["schema_version"], "result-bundle/1.1")
        self.assertEqual(
            bundle["analysis_kind"],
            "deterministic-descriptive-aggregation",
        )
        self.assertEqual(uncertainty["method"], "student_t")
        self.assertEqual(uncertainty["degrees_of_freedom"], 2.0)
        self.assertGreater(
            metric["effect"]["estimate"] - uncertainty["lower"],
            1.96 * statistics_stderr([0.4, 0.8, 0.9]),
        )
        self.assertEqual(sigil, content_sigil(bundle))
        self.assertTrue(receipt.sigil.startswith("sha256:"))
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), bundle)

    def test_total_n_two_reports_uncertainty_unavailable(self) -> None:
        self._prepare(pairing="unpaired")
        self._run("RUN-B1", "baseline", 1.0, 1)
        self._run("RUN-T1", "treatment", 1.5, 2)
        bundle, _, _, _ = self.athanor.compute_analysis(
            self.program_id,
            "PT-001",
        )
        uncertainty = bundle["comparisons"][0]["metrics"]["score"]["uncertainty"]
        self.assertEqual(uncertainty["method"], "unavailable")
        self.assertIn("two observations per arm", uncertainty["reason"])
        self.assertNotIn("ci95", json.dumps(bundle))

    def test_missing_comparison_arm_fails_before_append(self) -> None:
        self._prepare(pairing="unpaired")
        self._run("RUN-T1", "treatment", 1.5, 1)
        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "missing a registered arm"):
            self.athanor.compute_analysis(self.program_id, "PT-001")
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

    def test_bootstrap_is_deterministic_under_registered_seed(self) -> None:
        self._prepare(pairing="unpaired", method="bootstrap")
        for index, value in enumerate((1.0, 1.2, 1.4), start=1):
            self._run(f"RUN-B{index}", "baseline", value, index)
        for index, value in enumerate((1.5, 1.9, 2.1), start=1):
            self._run(f"RUN-T{index}", "treatment", value, index + 10)
        protocol = self.athanor.protocols()["PT-001"]
        runs = list(self.athanor.runs().values())
        first = build_result_bundle("RB-001", protocol, runs)
        second = build_result_bundle("RB-001", protocol, list(reversed(runs)))
        self.assertEqual(first, second)
        uncertainty = first["comparisons"][0]["metrics"]["score"]["uncertainty"]
        self.assertEqual(uncertainty["method"], "bootstrap")
        self.assertEqual(uncertainty["seed"], 17)
        self.assertEqual(uncertainty["samples"], 1000)
        self.assertAlmostEqual(uncertainty["lower"], 0.3)
        self.assertAlmostEqual(uncertainty["upper"], 0.9666666666666666)

    def test_paired_comparison_requires_matching_unique_seeds(self) -> None:
        self._prepare()
        self._run("RUN-B1", "baseline", 1.0, 1)
        self._run("RUN-B2", "baseline", 1.2, 2)
        self._run("RUN-T1", "treatment", 1.5, 1)
        self._run("RUN-T2", "treatment", 1.8, 3)
        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "identical unique non-null"):
            self.athanor.compute_analysis(self.program_id, "PT-001")
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

    def test_bonferroni_policy_adjusts_effective_interval_level(self) -> None:
        analysis_spec = self._analysis_spec(pairing="unpaired")
        second = analysis_spec["comparisons"][0].copy()
        second["comparison_id"] = "CMP-002"
        analysis_spec["comparisons"].append(second)
        analysis_spec["multiple_comparison_policy"] = "bonferroni"
        self.athanor.draft_protocol(
            "PT-001",
            self.program_id,
            "Registered family",
            "Apply a registered family-wise interval adjustment.",
            analysis_spec=analysis_spec,
        )
        self.athanor.seal_protocol("PT-001")
        self.athanor.create_experiment(
            "EX-001",
            self.program_id,
            "PT-001",
            "Registered comparison family.",
        )
        for index, value in enumerate((1.0, 1.2), start=1):
            self._run(f"RUN-B{index}", "baseline", value, index)
        for index, value in enumerate((1.5, 1.7), start=1):
            self._run(f"RUN-T{index}", "treatment", value, index + 10)
        bundle, _, _, _ = self.athanor.compute_analysis(
            self.program_id,
            "PT-001",
        )
        levels = [
            comparison["metrics"]["score"]["uncertainty"]["effective_level"]
            for comparison in bundle["comparisons"]
        ]
        self.assertEqual(levels, [0.975, 0.975])

    def test_multiple_experiments_are_not_pooled(self) -> None:
        self._prepare(pairing="unpaired")
        self.athanor.create_experiment(
            "EX-002",
            self.program_id,
            "PT-001",
            "A separate replication Experiment.",
        )
        self._run("RUN-B1", "baseline", 1.0, 1)
        self._run("RUN-B2", "baseline", 1.2, 2)
        self._run("RUN-T1", "treatment", 1.6, 3)
        self._run("RUN-T2", "treatment", 1.8, 4)
        self._run("RUN-OTHER-B", "baseline", -100.0, 5, experiment_id="EX-002")
        self._run("RUN-OTHER-T", "treatment", 100.0, 6, experiment_id="EX-002")
        bundle, _, _, _ = self.athanor.compute_analysis(
            self.program_id,
            "PT-001",
        )
        comparison = bundle["comparisons"][0]
        self.assertEqual(comparison["run_ids"]["control"], ["RUN-B1", "RUN-B2"])
        self.assertEqual(comparison["run_ids"]["treatment"], ["RUN-T1", "RUN-T2"])
        self.assertAlmostEqual(
            comparison["metrics"]["score"]["effect"]["estimate"],
            0.6,
        )
        self.assertIn("RUN-OTHER-B", bundle["run_inventory"]["all_run_ids"])

    def test_failed_excluded_and_missing_runs_remain_in_inventory(self) -> None:
        self._prepare(
            pairing="unpaired",
            expected_run_ids=[
                "RUN-B1",
                "RUN-B2",
                "RUN-T1",
                "RUN-T2",
                "RUN-FAILED",
                "RUN-MISSING",
            ],
        )
        self._run("RUN-B1", "baseline", 1.0, 1)
        self._run("RUN-B2", "baseline", 1.2, 2)
        self._run("RUN-T1", "treatment", 1.5, 3)
        self._run("RUN-T2", "treatment", 1.7, 4)
        self._run(
            "RUN-EXCLUDED",
            "treatment",
            99.0,
            5,
            included=False,
            reason="Registered exclusion rule.",
        )
        self.athanor.record_run(
            "RUN-FAILED",
            "EX-001",
            "FAILED",
            False,
            seed=6,
            arm="treatment",
        )
        bundle, _, _, _ = self.athanor.compute_analysis(
            self.program_id,
            "PT-001",
        )
        inventory = bundle["run_inventory"]
        self.assertEqual(inventory["failed_run_ids"], ["RUN-FAILED"])
        self.assertEqual(inventory["missing_run_ids"], ["RUN-MISSING"])
        excluded = {item["run_id"]: item for item in inventory["excluded_runs"]}
        self.assertEqual(
            excluded["RUN-EXCLUDED"]["reason"],
            "Registered exclusion rule.",
        )
        self.assertIn("RUN-FAILED", excluded)

    def test_invalid_analysis_spec_and_unknown_experiment_fail_closed(self) -> None:
        invalid = self._analysis_spec()
        invalid["comparisons"][0]["arms"] = ["same", "same"]
        with self.assertRaisesRegex(AthanorError, "arms must be distinct"):
            self.athanor.draft_protocol(
                "PT-001",
                self.program_id,
                "Invalid analysis",
                "Invalid comparison.",
                analysis_spec=invalid,
            )

        self.athanor.draft_protocol(
            "PT-002",
            self.program_id,
            "Missing Experiment",
            "Registered comparison.",
            analysis_spec=self._analysis_spec(experiment_id="EX-MISSING"),
        )
        self.athanor.seal_protocol("PT-002")
        with self.assertRaisesRegex(AthanorError, "unknown matching Experiment"):
            self.athanor.compute_analysis(self.program_id, "PT-002")

    def test_new_analysis_without_registered_spec_fails_closed(self) -> None:
        self.athanor.draft_protocol(
            "PT-001",
            self.program_id,
            "Descriptive prose only",
            "This prose is not a machine-checkable comparison.",
        )
        self.athanor.seal_protocol("PT-001")
        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "registered analysis_spec"):
            self.athanor.compute_analysis(self.program_id, "PT-001")
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)


def statistics_stderr(values: list[float]) -> float:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance) / math.sqrt(len(values))


if __name__ == "__main__":
    unittest.main()
