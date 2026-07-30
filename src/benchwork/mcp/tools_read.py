"""Read-only MCP tool registration."""

from __future__ import annotations

from .registration import register_tools
from .runtime import BenchworkTools
from .tool_registry import tool_names

READ_TOOLS = tool_names("read")


def register_read_tools(server: object, tools: BenchworkTools) -> None:
    register_tools(server, tools, READ_TOOLS)
