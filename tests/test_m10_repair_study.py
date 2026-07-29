import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class M10RepairStudyTest(unittest.TestCase):
    def test_fixture_builds_deep_checks_and_replays_in_fresh_processes(self) -> None:
        repository = Path(__file__).parents[1]
        fixture = repository / "examples" / "m10-repair-study"
        environment = os.environ.copy()
        source_path = str(repository / "src")
        environment["PYTHONPATH"] = os.pathsep.join(
            value
            for value in (source_path, environment.get("PYTHONPATH", ""))
            if value
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "study"
            build = subprocess.run(
                [sys.executable, str(fixture / "scenario.py"), str(root)],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertTrue(json.loads(build.stdout)["continue_rejected"])

            doctor = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "benchwork.cli",
                    "--json",
                    "doctor",
                    "--deep",
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )
            doctor_report = json.loads(doctor.stdout)
            self.assertTrue(doctor_report["ok"])
            self.assertTrue(doctor_report["result"]["chronicle_verified"])
            self.assertTrue(doctor_report["result"]["all_objects_replayable"])

            replay = subprocess.run(
                [sys.executable, str(fixture / "verify.py"), str(root)],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )
            report = json.loads(replay.stdout)
            self.assertEqual(report["program_status"], "EVALUATED")
            self.assertEqual(report["working_status"], "COMPLETED")
            self.assertEqual(report["decision"], "REPAIR")


if __name__ == "__main__":
    unittest.main()
