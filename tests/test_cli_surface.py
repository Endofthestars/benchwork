import hashlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from benchwork.athanor import Athanor
from benchwork.cli import _parser, main


class CliSurfaceTest(unittest.TestCase):
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

    def test_rfc_command_forms_parse(self) -> None:
        cases = (
            ["scry", "literature", "--program", "RP-001"],
            ["distill", "evidence", "--program", "RP-001"],
            ["invoke", "bench.evidence.verify", "--program", "RP-001"],
            ["seal", "protocol", "PT-001"],
            ["working", "inspect", "WK-001"],
            ["working", "resume", "WK-001"],
            ["chronicle", "verify"],
            ["chronicle", "recover", "--dry-run"],
            ["migrate", "chronicle-v1.0-to-v1.1"],
            ["sigil", "show", "RC-001"],
            ["trace", "claim", "CL-001"],
        )
        for arguments in cases:
            with self.subTest(arguments=arguments):
                self.assertEqual(_parser().parse_args(arguments).command, arguments[0])

    def test_direct_verbs_create_bounded_task_proposals(self) -> None:
        self.assertEqual(self._run("init")[0], 0)
        code, _ = self._run("start", "研究可恢复命令")
        self.assertEqual(code, 0)
        self.assertEqual(Athanor(self.root).programs()["RP-001"]["slug"], "research-program")

        code, output = self._run("investigate", "--program", "RP-001")
        self.assertEqual(code, 0)
        task_id = json.loads(output)["task_id"]
        capsule = json.loads(
            (self.root / ".benchwork" / "capsules" / f"{task_id}.json").read_text()
        )
        self.assertEqual(capsule["capability"]["id"], "bench.evidence.discover")
        self.assertTrue(capsule["circle"]["network"])

        code, output = self._run("implement", "--program", "RP-001")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["ward"]["status"], "WAITING_FOR_APPROVAL")

        code, output = self._run("run", "--program", "RP-001")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["ward"]["status"], "WAITING_FOR_APPROVAL")

    def test_aliases_and_agent_result_acceptance(self) -> None:
        self._run("init")
        self._run("start", "Alias study", "--slug", "alias-study")
        code, output = self._run("investigate", "--program", "RP-001")
        self.assertEqual(code, 0)
        task_id = json.loads(output)["task_id"]
        capsule_path = self.root / ".benchwork" / "capsules" / f"{task_id}.json"
        capsule = json.loads(capsule_path.read_text())
        output_path = self.root / "proposals" / "discovery.json"
        output_path.parent.mkdir()
        output_document = {
            "schema_version": "evidence-discovery-result/1.0",
            "task_id": task_id,
            "summary": "Discovery proposal completed.",
            "data": {},
        }
        blob = json.dumps(output_document, sort_keys=True).encode()
        output_path.write_bytes(blob)
        result_path = self.root / "agent-result.json"
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": "agent-result/1.1",
                    "task_id": task_id,
                    "snapshot_sigil": capsule["snapshot"]["snapshot_sigil"],
                    "capability_contract_sigil": capsule["capability"]["contract_sigil"],
                    "outputs": [
                        {
                            "schema": "evidence-discovery-result/1.0",
                            "uri": "proposals/discovery.json",
                            "blob_sigil": (
                                "sha256:" + hashlib.sha256(blob).hexdigest()
                            ),
                        }
                    ],
                    "status": "COMPLETED",
                }
            ),
            encoding="utf-8",
        )
        self.assertEqual(self._run("task", "accept", str(result_path))[0], 0)
        self.assertIn(task_id, Athanor(self.root).agent_results())

        self.assertEqual(
            self._run(
                "protocol",
                "draft",
                "PT-001",
                "--program",
                "RP-001",
                "--title",
                "Alias protocol",
                "--analysis-plan",
                "Compute registered metrics.",
            )[0],
            0,
        )
        self.assertEqual(self._run("seal", "protocol", "PT-001")[0], 0)
        self.assertEqual(
            self._run(
                "rite",
                "run",
                "computational-study@0.1.0",
                "--program",
                "RP-001",
                "--protocol",
                "PT-001",
            )[0],
            0,
        )
        self.assertEqual(self._run("working", "inspect", "WK-001")[0], 0)
        self.assertEqual(self._run("resume")[0], 0)
        self.assertEqual(self._run("chronicle", "verify")[0], 0)
        self.assertEqual(self._run("trace", "protocol", "PT-001")[0], 0)

    def test_file_sigil_verification(self) -> None:
        path = self.root / "artifact.bin"
        path.write_bytes(b"benchwork")
        expected = "sha256:" + hashlib.sha256(b"benchwork").hexdigest()
        code, output = self._run("sigil", "verify", str(path), "--expected", expected)
        self.assertEqual(code, 0)
        self.assertEqual(output.strip(), expected)
