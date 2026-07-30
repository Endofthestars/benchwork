"""Task-loop MCP tool registration."""

from __future__ import annotations

from .registration import register_tools
from .runtime import BenchworkTools
from .tool_registry import tool_names

TASK_TOOLS = tool_names("task")


def register_task_tools(server: object, tools: BenchworkTools) -> None:
    register_tools(server, tools, TASK_TOOLS)
