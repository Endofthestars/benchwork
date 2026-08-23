import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from benchwork.athanor import Athanor, AthanorError
from benchwork.cli import _parser, main
from benchwork.local_runner import LocalExperimentRunner
from benchwork.project import ProjectContext


class LocalExperimentRunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)
        program_id, _ = self.athanor.create_program("local-runner", "Local runner")
        self.athanor.draft_protocol(
            "PT-001",
            program_id,
            "Local runner protocol",
            "Record the metric emitted by the local command.",
            study_mode="exploratory",
        )
        self.athanor.seal_protocol("PT-001")
        self.athanor.create_experiment(
            "EX-001",
            program_id,
            "PT-001",
            "Can a trusted local command produce a durable Run?",
        )
        self.athanor.transition_experiment("EX-001", "implemented")
        self.athanor.transition_experiment("EX-001", "pilot-started")
        self.runner = LocalExperimentRunner(self.root)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_success_records_metrics_logs_output_and_canonical_run(self) -> None:
        result = self.runner.execute(
            run_id="RUN-SUCCESS",
            experiment_id="EX-001",
            command=[
                sys.executable,
                "-c",
                (
                    "from pathlib import Path; "
                    "Path('result.txt').write_text('answer'); "
                    "print('completed')"
                ),
            ],
            phase="PILOT",
            inline_metrics={"score": 0.75},
            output_files=[Path("result.txt")],
        )

        run = Athanor(self.root).runs()["RUN-SUCCESS"]
        self.assertEqual(run["status"], "COMPLETED")
        self.assertTrue(run["analysis_disposition"]["included"])
        self.assertEqual(run["metrics"], {"score": 0.75})
        self.assertEqual(result["run"], run)
        self.assertEqual((self.root / result["stdout"]).read_text().strip(), "completed")
        record = json.loads((self.root / result["execution_record"]).read_text())
        self.assertEqual(record["return_code"], 0)
        self.assertFalse(record["timed_out"])
        self.assertEqual(record["missing_outputs"], [])
        self.assertIn("result.txt", [item["uri"] for item in record["artifacts"]])
        execution_uri = result["execution_record"]
        self.assertIn(execution_uri, [item["uri"] for item in run["artifacts"]])

    def test_nonzero_exit_is_preserved_as_failed_run(self) -> None:
        result = self.runner.execute(
            run_id="RUN-FAILED",
            experiment_id="EX-001",
            command=[sys.executable, "-c", "import sys; print('bad', file=sys.stderr); sys.exit(7)"],
            phase="PILOT",
        )

        run = Athanor(self.root).runs()["RUN-FAILED"]
        self.assertEqual(run["status"], "FAILED")
        self.assertFalse(run["analysis_disposition"]["included"])
        self.assertIn("bad", (self.root / result["stderr"]).read_text())
        record = json.loads((self.root / result["execution_record"]).read_text())
        self.assertEqual(record["return_code"], 7)
        self.assertFalse(record["timed_out"])

    def test_timeout_is_preserved_as_failed_run(self) -> None:
        result = self.runner.execute(
            run_id="RUN-TIMEOUT",
            experiment_id="EX-001",
            command=[sys.executable, "-c", "import time; time.sleep(5)"],
            timeout_seconds=1,
            phase="PILOT",
        )

        run = Athanor(self.root).runs()["RUN-TIMEOUT"]
        self.assertEqual(run["status"], "FAILED")
        record = json.loads((self.root / result["execution_record"]).read_text())
        self.assertTrue(record["timed_out"])
        self.assertIsNone(record["return_code"])

    @unittest.skipUnless(os.name == "posix", "process-group assertion is POSIX-specific")
    def test_timeout_stops_descendants_before_artifacts_are_sealed(self) -> None:
        child = "import time; from pathlib import Path; time.sleep(2); Path('late.txt').write_text('late')"
        self.runner.execute(
            run_id="RUN-TREE-TIMEOUT",
            experiment_id="EX-001",
            command=[
                sys.executable,
                "-c",
                (
                    "import subprocess,sys,time; "
                    f"subprocess.Popen([sys.executable, '-c', {child!r}]); "
                    "time.sleep(10)"
                ),
            ],
            timeout_seconds=1,
            phase="PILOT",
        )
        import time

        time.sleep(2)
        self.assertFalse(self.root.joinpath("late.txt").exists())

    def test_working_directory_cannot_escape_project(self) -> None:
        with self.assertRaisesRegex(AthanorError, "must stay inside the project"):
            self.runner.execute(
                run_id="RUN-ESCAPE",
                experiment_id="EX-001",
                command=[sys.executable, "-c", "pass"],
                working_directory=Path(".."),
                phase="PILOT",
            )
        self.assertNotIn("RUN-ESCAPE", Athanor(self.root).runs())
        self.assertFalse(self.root.joinpath(".benchwork/local-runs/RUN-ESCAPE").exists())

    def test_exclusion_reason_requires_exclusion_before_execution(self) -> None:
        with self.assertRaisesRegex(AthanorError, "requires --exclude"):
            self.runner.execute(
                run_id="RUN-BAD-EXCLUSION",
                experiment_id="EX-001",
                command=[sys.executable, "-c", "raise SystemExit('must not run')"],
                phase="PILOT",
                inline_metrics={"score": 1.0},
                exclusion_reason="not selected",
            )
        self.assertFalse(
            self.root.joinpath(".benchwork/local-runs/RUN-BAD-EXCLUSION").exists()
        )

    def test_missing_declared_output_fails_and_records_why(self) -> None:
        result = self.runner.execute(
            run_id="RUN-MISSING",
            experiment_id="EX-001",
            command=[sys.executable, "-c", "print('no artifact')"],
            phase="PILOT",
            inline_metrics={"score": 1.0},
            output_files=[Path("missing.json")],
        )

        run = Athanor(self.root).runs()["RUN-MISSING"]
        self.assertEqual(run["status"], "FAILED")
        self.assertFalse(run["analysis_disposition"]["included"])
        record = json.loads((self.root / result["execution_record"]).read_text())
        self.assertEqual(record["status"], "FAILED")
        self.assertEqual(record["missing_outputs"], ["missing.json"])

    def test_command_cannot_publish_a_symlinked_external_output(self) -> None:
        with tempfile.NamedTemporaryFile() as external:
            external.write(b"outside")
            external.flush()
            result = self.runner.execute(
                run_id="RUN-SYMLINK",
                experiment_id="EX-001",
                command=[
                    sys.executable,
                    "-c",
                    "import os,sys; os.symlink(sys.argv[1], 'linked.txt')",
                    external.name,
                ],
                phase="PILOT",
                inline_metrics={"score": 1.0},
                output_files=[Path("linked.txt")],
            )

        run = Athanor(self.root).runs()["RUN-SYMLINK"]
        self.assertEqual(run["status"], "FAILED")
        self.assertNotIn("linked.txt", [item["uri"] for item in run["artifacts"]])
        record = json.loads((self.root / result["execution_record"]).read_text())
        self.assertEqual(record["missing_outputs"], ["linked.txt"])


class LocalProductCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.previous_cwd = Path.cwd()
        os.chdir(self.root)

    def tearDown(self) -> None:
        os.chdir(self.previous_cwd)
        self.directory.cleanup()

    def _run(self, *arguments: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(arguments)
        return code, output.getvalue()

    def test_run_local_parser_preserves_command_after_separator(self) -> None:
        arguments = _parser().parse_args(
            [
                "run",
                "local",
                "RUN-001",
                "--experiment",
                "EX-001",
                "--metric",
                "score=1",
                "--",
                sys.executable,
                "-c",
                "print('ok')",
            ]
        )
        self.assertEqual(arguments.run_command, "local")
        self.assertEqual(arguments.argv, [sys.executable, "-c", "print('ok')"])

    def test_start_auto_selects_program_for_next_and_direct_commands(self) -> None:
        self.assertEqual(self._run("init")[0], 0)
        self.assertEqual(self._run("start", "A first usable research loop")[0], 0)
        self.assertEqual(ProjectContext(self.root).active_program(), "RP-001")

        code, output = self._run("next")
        self.assertEqual(code, 0)
        step = json.loads(output)
        self.assertEqual(step["program_id"], "RP-001")
        self.assertEqual(step["action"], "INVESTIGATE")

        code, output = self._run("investigate")
        self.assertEqual(code, 0)
        task_id = json.loads(output)["task_id"]
        capsule = json.loads(
            self.root.joinpath(".benchwork", "capsules", f"{task_id}.json").read_text()
        )
        self.assertEqual(capsule["program_id"], "RP-001")

        code, output = self._run("overview")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["active_program_id"], "RP-001")

    def test_cli_executes_and_records_a_local_run_end_to_end(self) -> None:
        self.assertEqual(self._run("init")[0], 0)
        self.assertEqual(self._run("start", "CLI local execution")[0], 0)
        athanor = Athanor(self.root)
        athanor.draft_protocol(
            "PT-001",
            "RP-001",
            "CLI local protocol",
            "Record the emitted score.",
            study_mode="exploratory",
        )
        athanor.seal_protocol("PT-001")
        athanor.create_experiment("EX-001", "RP-001", "PT-001", "Does it execute?")
        athanor.transition_experiment("EX-001", "implemented")
        athanor.transition_experiment("EX-001", "pilot-started")

        code, output = self._run(
            "run",
            "local",
            "RUN-CLI",
            "--experiment",
            "EX-001",
            "--phase",
            "PILOT",
            "--metric",
            "score=0.9",
            "--",
            sys.executable,
            "-c",
            "print('cli executed')",
        )

        self.assertEqual(code, 0)
        result = json.loads(output)
        self.assertEqual(result["run"]["status"], "COMPLETED")
        self.assertEqual(Athanor(self.root).runs()["RUN-CLI"]["metrics"], {"score": 0.9})
        self.assertIn("cli executed", (self.root / result["stdout"]).read_text())


if __name__ == "__main__":
    unittest.main()
