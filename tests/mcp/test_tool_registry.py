import asyncio
import unittest

from mcp import Client

from benchwork.mcp.server import create_server
from benchwork.mcp.tool_registry import (
    TOOL_CATEGORIES,
    load_tool_registry,
    tool_metadata,
    tool_names,
)
from benchwork.schema_validation import validate_instance


class MCPToolRegistryTest(unittest.TestCase):
    def test_registry_is_schema_valid_and_frozen_at_38_tools(self) -> None:
        registry = load_tool_registry()
        validate_instance("mcp-tool-registry-1.0.json", registry)
        self.assertEqual(registry["stability"], "alpha")
        self.assertEqual(len(registry["tools"]), 38)
        self.assertEqual(len(tool_names()), 38)
        self.assertEqual(
            {category: len(tool_names(category)) for category in TOOL_CATEGORIES},
            {"read": 9, "task": 4, "canonical": 19, "experiment": 6},
        )
        self.assertEqual(len(set(tool_names())), 38)

    def test_registry_is_the_server_inventory(self) -> None:
        async def exercise() -> None:
            async with Client(create_server()) as client:
                result = await client.list_tools()
                listed = tuple(tool.name for tool in result.tools)
                self.assertEqual(listed, tool_names())
                self.assertTrue(all(tool.input_schema for tool in result.tools))

        asyncio.run(exercise())

    def test_registry_records_high_risk_boundaries(self) -> None:
        protocol = tool_metadata("benchwork_commit_protocol_seal")
        self.assertEqual(protocol["approval"], "human_confirmation")
        self.assertEqual(protocol["risk"], "high")
        disclosure = tool_metadata("benchwork_approve_external_review")
        self.assertEqual(disclosure["approval"], "disclosure_gate")
        self.assertEqual(disclosure["risk"], "high")

    def test_registry_accessors_do_not_expose_mutable_entries(self) -> None:
        metadata = tool_metadata("benchwork_status")
        metadata["name"] = "changed"
        self.assertEqual(tool_metadata("benchwork_status")["name"], "benchwork_status")
        snapshot = load_tool_registry()
        snapshot["tools"][0]["name"] = "changed"
        self.assertEqual(load_tool_registry()["tools"][0]["name"], "benchwork_status")

    def test_unknown_registry_queries_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown MCP tool category"):
            tool_names("universal")
        with self.assertRaises(KeyError):
            tool_metadata("benchwork_execute")
