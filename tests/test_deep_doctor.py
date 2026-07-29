import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from benchwork.athanor import Athanor
from benchwork.circle import CapabilityRegistry
from benchwork.cli.main import main
from benchwork.doctor import deep_doctor
from benchwork.rites import RiteRegistry


class DeepDoctorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)
        self.athanor.initialize()
        CapabilityRegistry(self.root).initialize()
        RiteRegistry(self.root).initialize()
        self.program_id, _ = self.athanor.create_program(
            "deep-doctor",
            "Deep doctor",
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_modified_artifact_blob_is_reported(self) -> None:
        artifact = self.root / "artifact.bin"
        artifact.write_bytes(b"registered")
        self.athanor.register_artifact(
            "AR-001",
            self.program_id,
            "implementation",
            {
                "uri": "artifact.bin",
                "sigil": "sha256:" + hashlib.sha256(b"registered").hexdigest(),
            },
            self.program_id,
        )
        artifact.write_bytes(b"tampered")

        report = deep_doctor(self.root)
        self.assertFalse(report["ok"])
        self.assertEqual(report["checks"]["artifacts"]["status"], "FAIL")
        self.assertIn("Sigil mismatch", report["checks"]["artifacts"]["message"])

        output = io.StringIO()
        with (
            patch(
                "benchwork.cli.main.discover_project_root",
                return_value=self.root,
            ),
            redirect_stdout(output),
        ):
            code = main(("--json", "doctor", "--deep"))
        envelope = json.loads(output.getvalue())
        self.assertEqual(code, 4)
        self.assertFalse(envelope["ok"])
        self.assertEqual(envelope["error"]["code"], "INTEGRITY_FAILURE")
        self.assertEqual(
            envelope["error"]["details"]["report"]["checks"]["artifacts"]["status"],
            "FAIL",
        )

    def test_missing_result_bundle_export_is_reported(self) -> None:
        analysis_spec = {
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
            "expected_run_ids": ["RUN-B", "RUN-T"],
        }
        self.athanor.draft_protocol(
            "PT-001",
            self.program_id,
            "Doctor comparison",
            "Verify the exported Result Bundle.",
            study_mode="exploratory",
            analysis_spec=analysis_spec,
        )
        self.athanor.seal_protocol("PT-001")
        self.athanor.create_experiment(
            "EX-001",
            self.program_id,
            "PT-001",
            "Does the registered treatment differ?",
        )
        self.athanor.record_run(
            "RUN-B",
            "EX-001",
            "COMPLETED",
            True,
            {"score": 1.0},
            arm="baseline",
        )
        self.athanor.record_run(
            "RUN-T",
            "EX-001",
            "COMPLETED",
            True,
            {"score": 1.2},
            arm="treatment",
        )
        bundle, _, _, path = self.athanor.compute_analysis(
            self.program_id,
            "PT-001",
        )
        path.unlink()

        report = deep_doctor(self.root)
        self.assertFalse(report["ok"])
        self.assertEqual(report["checks"]["result_exports"]["status"], "FAIL")
        self.assertIn(bundle["bundle_id"], report["checks"]["result_exports"]["message"])


if __name__ == "__main__":
    unittest.main()
