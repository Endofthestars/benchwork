"""Task-loop MCP tool registration."""

from __future__ import annotations

from .registration import register_tools
from .runtime import BenchworkTools

TASK_TOOLS = (
    "benchwork_open_task",
    "benchwork_get_task",
    "benchwork_complete_task",
    "benchwork_fail_task",
)


def register_task_tools(server: object, tools: BenchworkTools) -> None:
    register_tools(server, tools, TASK_TOOLS)
