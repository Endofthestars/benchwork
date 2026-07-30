import asyncio
import hashlib
import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import Client, ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from benchwork.athanor import Athanor
from benchwork.circle import CapabilityRegistry
from benchwork.mcp.runtime import BenchworkTools
from benchwork.mcp.server import BenchworkMCPServer, create_server
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
                self.assertEqual(len(names), 38)
                self.assertIn("benchwork_compute_analysis", names)
                result = await client.call_tool("benchwork_status", {})
                self.assertTrue(result.structured_content["ok"])

        asyncio.run(exercise())

    def test_json_rpc_dispatch_covers_protocol_control_messages(self) -> None:
        async def exercise() -> None:
            server = create_server(self.root)
            self.assertIsInstance(server, BenchworkMCPServer)
            assert isinstance(server, BenchworkMCPServer)
            initialized = await server._dispatch_stdio(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2025-11-25"},
                }
            )
            self.assertEqual(
                initialized["result"]["protocolVersion"],
                "2025-11-25",
            )
            self.assertIn("canonical", initialized["result"]["instructions"])
            ping = await server._dispatch_stdio(
                {"jsonrpc": "2.0", "id": 2, "method": "ping"}
            )
            self.assertEqual(ping["result"], {})
            notification = await server._dispatch_stdio(
                {"jsonrpc": "2.0", "method": "notifications/initialized"}
            )
            self.assertIsNone(notification)
            listed = await server._dispatch_stdio(
                {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
            )
            self.assertEqual(len(listed["result"]["tools"]), 38)
            called = await server._dispatch_stdio(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "benchwork_status",
                        "arguments": {},
                    },
                }
            )
            self.assertFalse(called["result"]["isError"])
            missing = await server._dispatch_stdio(
                {"jsonrpc": "2.0", "id": 5, "method": "unknown"}
            )
            self.assertEqual(missing["error"]["code"], -32601)
            with self.assertRaisesRegex(ValueError, "tool name"):
                await server._dispatch_stdio(
                    {
                        "jsonrpc": "2.0",
                        "id": 6,
                        "method": "tools/call",
                        "params": {},
                    }
                )
            with self.assertRaisesRegex(ValueError, "invalid JSON-RPC"):
                await server._dispatch_stdio(
                    {"jsonrpc": "1.0", "id": 7, "method": "ping"}
                )

        asyncio.run(exercise())

    def test_read_tools_are_non_mutating_paginated_and_fail_closed(self) -> None:
        program_ids = []
        for index in range(3):
            result = self.tools.benchwork_create_program(
                f"read-only-{index}",
                f"Read-only Program {index}",
                {"statement": "Verify the read surface without state mutation."},
                activate=index == 0,
            )
            self.assertTrue(result["ok"])
            program_ids.append(result["data"]["program_id"])

        def state_files() -> dict[str, str]:
            state_root = self.root / ".benchwork"
            return {
                path.relative_to(self.root).as_posix(): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in sorted(state_root.rglob("*"))
                if path.is_file()
            }

        before = state_files()
        first_page = self.tools.benchwork_list_programs(limit=2)
        self.assertTrue(first_page["ok"])
        self.assertEqual(len(first_page["data"]["items"]), 2)
        cursor = first_page["data"]["next_cursor"]
        self.assertIsNotNone(cursor)
        second_page = self.tools.benchwork_list_programs(cursor=cursor, limit=2)
        self.assertTrue(second_page["ok"])
        self.assertEqual(len(second_page["data"]["items"]), 1)
        results = [
            self.tools.benchwork_status(),
            self.tools.benchwork_get_program(program_ids[0]),
            self.tools.benchwork_get_object(program_ids[0]),
            self.tools.benchwork_trace(program_ids[0], limit=1),
            self.tools.benchwork_next_actions(),
            self.tools.benchwork_next_actions(program_ids[0]),
            self.tools.benchwork_get_schema("research-program/1.1"),
            self.tools.benchwork_doctor(),
            self.tools.benchwork_doctor(deep=True),
        ]
        self.assertTrue(all(result["ok"] for result in results))
        rejected = [
            self.tools.benchwork_get_program("RP-404"),
            self.tools.benchwork_get_object("EV-404"),
            self.tools.benchwork_get_schema("missing/1.0"),
            self.tools.benchwork_list_programs(cursor="not-a-cursor"),
            self.tools.benchwork_list_programs(limit=0),
        ]
        self.assertTrue(all(not result["ok"] for result in rejected))
        self.assertEqual(before, state_files())

        head_path = self.root / ".benchwork" / "chronicle.head"
        head_path.write_text(
            '{"schema_version":"chronicle-head/1.1","receipt_sigil":"sha256:'
            + "0" * 64
            + '"}\n',
            encoding="utf-8",
        )
        damaged = self.tools.benchwork_status()
        self.assertFalse(damaged["ok"])
        self.assertEqual(damaged["error"]["code"], "INTEGRITY_FAILURE")

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

    def test_complete_repair_cycle_uses_only_control_plane_tools(self) -> None:
        scenario = json.loads(
            (
                Path(__file__).parents[2]
                / "examples"
                / "phase2-final"
                / "scenario.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            scenario["required_facts"]["audit_capability"],
            "bench.study.audit",
        )
        self.assertEqual(scenario["required_facts"]["decision"], "REPAIR")
        program_id = self.tools.benchwork_create_program(
            "mcp-repair-cycle",
            "MCP repair cycle",
            {"statement": "Exercise the complete Phase 2 control plane."},
        )["data"]["program_id"]
        self.assertTrue(
            self.tools.benchwork_record_evidence(
                "EV-001",
                program_id,
                "https://example.test/repair-evidence",
                "sha256:" + "1" * 64,
                "The inspected source motivates the registered comparison.",
            )["ok"]
        )
        self.assertTrue(
            self.tools.benchwork_verify_evidence(
                "EV-001",
                ["source_resolved", "content_inspected"],
            )["ok"]
        )
        self.assertTrue(
            self.tools.benchwork_create_claim(
                "CL-001",
                program_id,
                "empirical",
                "The treatment improves the registered score.",
                [{"evidence_id": "EV-001", "relation": "SUPPORTS"}],
            )["ok"]
        )
        self.assertTrue(
            self.tools.benchwork_verify_claim_relation("CL-001", "EV-001")["ok"]
        )
        self.assertTrue(
            self.tools.benchwork_create_hypothesis(
                "HY-001",
                program_id,
                ["CL-001"],
                "The treatment increases the registered score.",
                "Treatment Runs exceed paired baseline Runs.",
            )["ok"]
        )

        rq_preview = self.tools.benchwork_preview_rq_seal(
            program_id,
            "Does the treatment improve the registered score?",
        )["data"]
        rq_commit = self.tools.benchwork_commit_rq_seal(
            rq_preview["preview_id"],
            rq_preview["preview_sigil"],
            "mcp-cycle-rq",
            rq_preview["required_approval"]["confirmation_token"],
        )
        self.assertTrue(rq_commit["ok"])

        draft = self.tools.benchwork_draft_protocol(
            "PT-DRAFT",
            program_id,
            "Protocol requiring audit repair",
            "Compare treatment and baseline scores without a registered estimand.",
            ["HY-001"],
            "confirmatory",
        )
        self.assertTrue(draft["ok"])
        audit = self.tools.benchwork_open_task(
            "bench.study.audit",
            program_id,
            "Audit PT-DRAFT before experimentation.",
        )
        self.assertTrue(audit["ok"])
        audit_task_id = audit["data"]["task"]["task_id"]
        audit_result = self.tools.benchwork_complete_task(
            audit_task_id,
            "The draft requires a registered estimand and complete Run inventory.",
            {
                "protocol_id": "PT-DRAFT",
                "findings": [
                    "The analysis plan does not identify a registered estimand."
                ],
                "validity_threats": [
                    "Outcome selection could drift after observing Runs."
                ],
                "open_issues": [
                    "Register the comparison, uncertainty method, and Run inventory."
                ],
                "recommendation": "REPAIR",
            },
            {
                "schema_version": "host-session-provenance/1.0",
                "host": "codex",
                "session_id": "phase2-golden-audit",
                "runtime": "deterministic-host-simulation",
            },
        )
        self.assertTrue(audit_result["ok"])
        self.assertIsNotNone(audit_result["receipt"])
        accepted_audit = self.tools.benchwork_get_task(audit_task_id)
        self.assertEqual(
            accepted_audit["data"]["result"]["status"],
            "COMPLETED",
        )

        analysis_spec = {
            "schema_version": "analysis-spec/1.0",
            "comparisons": [
                {
                    "comparison_id": "CMP-001",
                    "experiment_id": "EX-001",
                    "arms": ["baseline", "treatment"],
                    "metric": "score",
                    "estimand": "mean_difference",
                    "pairing": "paired",
                    "uncertainty_method": "student_t",
                    "confidence_level": 0.95,
                }
            ],
            "multiple_comparison_policy": "none",
            "practical_significance_thresholds": {"score": 0.02},
            "pilot_run_ids": ["RUN-B1", "RUN-T1"],
            "expected_run_ids": [
                "RUN-B1",
                "RUN-T1",
                "RUN-B2",
                "RUN-T2",
                "RUN-X1",
                "RUN-F1",
            ],
        }
        self.assertTrue(
            self.tools.benchwork_draft_protocol(
                "PT-001",
                program_id,
                "MCP repair protocol",
                "Compare paired included Runs and retain the full inventory.",
                ["HY-001"],
                "confirmatory",
                analysis_spec,
            )["ok"]
        )
        protocol_preview = self.tools.benchwork_preview_protocol_seal("PT-001")["data"]
        protocol_commit = self.tools.benchwork_commit_protocol_seal(
            protocol_preview["preview_id"],
            protocol_preview["preview_sigil"],
            "mcp-cycle-protocol",
            protocol_preview["required_approval"]["confirmation_token"],
        )
        self.assertTrue(protocol_commit["ok"])

        working_id = self.tools.benchwork_start_working(
            "computational-study@0.2.1",
            program_id,
            "PT-001",
        )["data"]["working_id"]
        implementation = b'{"implementation":"registered"}\n'
        (self.root / "implementation.json").write_bytes(implementation)
        self.assertTrue(
            self.tools.benchwork_register_artifact(
                "AR-001",
                program_id,
                "implementation",
                "implementation.json",
                "sha256:" + hashlib.sha256(implementation).hexdigest(),
                working_id,
                ["PT-001"],
            )["ok"]
        )
        self.assertTrue(
            self.tools.benchwork_create_experiment(
                "EX-001",
                program_id,
                "PT-001",
                "Does the registered implementation improve score?",
                "HY-001",
                working_id,
            )["ok"]
        )
        for transition in ("implemented", "pilot-started"):
            self.assertTrue(
                self.tools.benchwork_transition_experiment(
                    "EX-001",
                    transition,
                )["ok"]
            )
        for run_id, arm, score in (
            ("RUN-B1", "baseline", 0.80),
            ("RUN-T1", "treatment", 0.86),
        ):
            self.assertTrue(
                self.tools.benchwork_record_run(
                    run_id,
                    "EX-001",
                    "COMPLETED",
                    True,
                    {"score": score},
                    seed=1,
                    phase="PILOT",
                    arm=arm,
                )["ok"]
            )
        for transition in ("pilot-completed", "formal-started"):
            self.assertTrue(
                self.tools.benchwork_transition_experiment(
                    "EX-001",
                    transition,
                )["ok"]
            )
        for run_id, arm, score in (
            ("RUN-B2", "baseline", 0.82),
            ("RUN-T2", "treatment", 0.91),
        ):
            self.assertTrue(
                self.tools.benchwork_record_run(
                    run_id,
                    "EX-001",
                    "COMPLETED",
                    True,
                    {"score": score},
                    seed=2,
                    arm=arm,
                )["ok"]
            )
        self.assertTrue(
            self.tools.benchwork_record_run(
                "RUN-X1",
                "EX-001",
                "COMPLETED",
                False,
                {"score": 0.99},
                seed=3,
                exclusion_reason="Registered environment mismatch exclusion.",
                arm="treatment",
            )["ok"]
        )
        self.assertTrue(
            self.tools.benchwork_record_run(
                "RUN-F1",
                "EX-001",
                "FAILED",
                False,
                {},
                seed=4,
                arm="baseline",
            )["ok"]
        )
        self.assertTrue(
            self.tools.benchwork_transition_experiment(
                "EX-001",
                "completed",
            )["ok"]
        )

        analysis = self.tools.benchwork_compute_analysis(program_id, "PT-001")
        self.assertTrue(analysis["ok"])
        bundle_id = analysis["data"]["result_bundle"]["bundle_id"]
        assessment = self.tools.benchwork_record_assessment(
            bundle_id,
            "The registered result is positive but repair remains required.",
            ["A critical evidence inventory issue remains unresolved."],
            [
                {
                    "claim_id": "CL-001",
                    "status": "SUPPORTED",
                    "rationale": "Included paired Runs moved in the registered direction.",
                }
            ],
            [
                {
                    "hypothesis_id": "HY-001",
                    "status": "SUPPORTED",
                    "rationale": "Treatment Runs exceeded baseline Runs.",
                }
            ],
        )
        self.assertTrue(assessment["ok"])
        assessment_id = assessment["data"]["assessment_id"]
        self.assertTrue(
            self.tools.benchwork_open_issue(
                "IS-001",
                program_id,
                ["EV-001"],
                "CRITICAL",
                "Incomplete registered evidence inventory",
                "Repair the evidence dependency before continuing.",
            )["ok"]
        )
        decision_preview = self.tools.benchwork_preview_decision_seal(
            program_id,
            "REPAIR",
            [assessment_id],
            "Repair the registered evidence dependency before another cycle.",
            ["Resolve IS-001 and repeat the evidence assessment."],
        )["data"]
        decision = self.tools.benchwork_commit_decision_seal(
            decision_preview["preview_id"],
            decision_preview["preview_sigil"],
            "mcp-cycle-decision",
            decision_preview["required_approval"]["confirmation_token"],
        )
        self.assertTrue(decision["ok"])
        state = Athanor(self.root).replay()
        self.assertEqual(state["programs"][program_id]["status"], "EVALUATED")
        self.assertEqual(state["protocols"]["PT-DRAFT"]["status"], "DRAFT")
        self.assertEqual(state["protocols"]["PT-001"]["status"], "FROZEN")
        decisions = [
            decision
            for decision in state["decisions"].values()
            if decision["program_id"] == program_id
        ]
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["outcome"], scenario["required_facts"]["decision"])
        self.assertEqual(state["runs"]["RUN-F1"]["status"], "FAILED")
        self.assertEqual(
            state["runs"]["RUN-X1"]["analysis_disposition"]["included"],
            False,
        )
        self.assertTrue(self.tools.benchwork_doctor(deep=True)["ok"])

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
                    self.assertEqual(len(names), 38)
                    result = await session.call_tool("benchwork_status", {})
                    self.assertTrue(result.structured_content["ok"])

        asyncio.run(exercise())
