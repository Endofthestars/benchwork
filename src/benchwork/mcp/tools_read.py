"""Read-only MCP tool registration."""

from __future__ import annotations

from .registration import register_tools
from .runtime import BenchworkTools

READ_TOOLS = (
    "benchwork_status",
    "benchwork_list_programs",
    "benchwork_get_program",
    "benchwork_get_object",
    "benchwork_get_review",
    "benchwork_trace",
    "benchwork_next_actions",
    "benchwork_get_schema",
    "benchwork_doctor",
)


def register_read_tools(server: object, tools: BenchworkTools) -> None:
    register_tools(server, tools, READ_TOOLS)
