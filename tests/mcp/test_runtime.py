import asyncio
import inspect
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import Client, ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from benchwork.athanor import Athanor
from benchwork.circle import CapabilityRegistry
from benchwork.mcp.runtime import BenchworkTools
from benchwork.mcp.server import create_server
from benchwork.rites import RiteRegistry


class MCPRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        Athanor(self.root).initialize()
        CapabilityRegistry(self.root).initialize()
        RiteRegistry(self.root).initialize()
        self.tools = BenchworkTools(self.root)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _program_with_hypothesis(self) -> str:
        athanor = Athanor(self.root)
        program_id, _ = athanor.create_program(
            "seal-preview",
            "Seal preview",
            {"statement": "Test immutable previews."},
        )
        athanor.record_evidence(
            "EV-001",
            program_id,
            {
                "uri": "https://example.test/evidence",
                "sigil": "sha256:" + "1" * 64,
            },
            "Inspected evidence.",
            {"source_resolved": True, "content_inspected": True},
        )
        athanor.create_claim(
            "CL-001",
            program_id,
            "empirical",
            "The preview path is testable.",
            [{"evidence_id": "EV-001", "relation": "SUPPORTS"}],
        )
        athanor.verify_claim_relation("CL-001", "EV-001")
        athanor.create_hypothesis(
            "HY-001",
            program_id,
            ["CL-001"],
            "Fresh previews commit.",
            "A fresh preview yields one Receipt.",
        )
        return program_id

    def test_task_completion_builds_and_accepts_semantic_blob(self) -> None:
        program = self.tools.benchwork_create_program(
            "task-loop",
            "Task loop",
            {"statement": "Exercise MCP Task completion."},
        )["data"]["program_id"]
        opened = self.tools.benchwork_open_task(
            "bench.evidence.discover",
            program,
            "Find one candidate source.",
        )
        self.assertTrue(opened["ok"])
        task_id = opened["data"]["task"]["task_id"]

        completed = self.tools.benchwork_complete_task(
            task_id,
            "Discovery proposal completed.",
            {
                "queries": ["test evidence"],
                "sources": [
                    {"uri": "https://example.test/source", "title": "Test source"}
                ],
                "screened_count": 1,
                "candidate_evidence": [
                    {
                        "source_uri": "https://example.test/source",
                        "claim": "Candidate observation.",
                        "relevance": "Matches the bounded Task.",
                        "uncertainty": "Requires canonical inspection.",
                    }
                ],
                "unresolved_queries": [],
                "limitations": [],
            },
            {
                "schema_version": "host-session-provenance/1.0",
                "host": "codex",
                "session_id": "session-test",
                "runtime": "pytest",
            },
        )

        self.assertTrue(completed["ok"])
        self.assertIsNotNone(completed["receipt"])
        output = completed["data"]["outputs"][0]
        self.assertTrue((self.root / output["uri"]).is_file())
        task = self.tools.benchwork_get_task(task_id)
        self.assertEqual(task["data"]["result"]["status"], "COMPLETED")

    def test_seal_preview_is_idempotent_and_stale_state_fails_closed(self) -> None:
        program_id = self._program_with_hypothesis()
        preview_result = self.tools.benchwork_preview_rq_seal(
            program_id,
            "Does a fresh preview commit exactly once?",
        )
        self.assertTrue(preview_result["ok"])
        preview = preview_result["data"]
        arguments = {
            "preview_id": preview["preview_id"],
            "preview_sigil": preview["preview_sigil"],
            "idempotency_key": "rq-seal-test",
            "confirmation_token": preview["required_approval"]["confirmation_token"],
        }
        committed = self.tools.benchwork_commit_rq_seal(**arguments)
        replayed = self.tools.benchwork_commit_rq_seal(**arguments)
        self.assertTrue(committed["ok"])
        self.assertEqual(committed["receipt"], replayed["receipt"])
        self.assertEqual(
            Athanor(self.root).programs()[program_id]["research_question"]["statement"],
            "Does a fresh preview commit exactly once?",
        )

        Athanor(self.root).draft_protocol(
            "PT-001",
            program_id,
            "Stale preview protocol",
            "Apply the deterministic registered plan.",
            ["HY-001"],
            "confirmatory",
        )
        protocol_preview = self.tools.benchwork_preview_protocol_seal("PT-001")["data"]
        Athanor(self.root).open_issue(
            "IS-001",
            program_id,
            [program_id],
            "LOW",
            "Concurrent canonical change",
            "Invalidate the outstanding preview.",
        )
        stale = self.tools.benchwork_commit_protocol_seal(
            protocol_preview["preview_id"],
            protocol_preview["preview_sigil"],
            "protocol-stale-test",
            protocol_preview["required_approval"]["confirmation_token"],
        )
        self.assertFalse(stale["ok"])
        self.assertEqual(stale["error"]["code"], "STALE_PREVIEW")

    def test_in_memory_server_exposes_the_complete_tool_surface(self) -> None:
        async def exercise() -> None:
            async with Client(create_server(self.root)) as client:
                tools = await client.list_tools()
                names = {tool.name for tool in tools.tools}
                self.assertEqual(len(names), 33)
                self.assertIn("benchwork_compute_analysis", names)
                result = await client.call_tool("benchwork_status", {})
                self.assertTrue(result.structured_content["ok"])

        asyncio.run(exercise())

    def test_run_default_matches_athanor_formal_phase(self) -> None:
        parameter = inspect.signature(
            self.tools.benchwork_record_run
        ).parameters["phase"]
        self.assertEqual(parameter.default, "FORMAL")

    def test_unexpected_failures_use_a_bounded_internal_error(self) -> None:
        result = self.tools._run(
            "benchwork_status",
            lambda: 1 / 0,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "INTERNAL_ERROR")
        self.assertNotIn("Traceback", str(result))

    def test_stdio_subprocess_serves_the_same_tools(self) -> None:
        async def exercise() -> None:
            executable = Path(sys.executable).with_name("bwork")
            if not executable.is_file():
                self.skipTest("editable Phase 2 test environment is unavailable")
            parameters = StdioServerParameters(
                command=str(executable),
                args=["mcp", "serve"],
                cwd=self.root,
            )
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = {tool.name for tool in tools.tools}
                    self.assertEqual(len(names), 33)
                    result = await session.call_tool("benchwork_status", {})
                    self.assertTrue(result.structured_content["ok"])

        asyncio.run(exercise())
