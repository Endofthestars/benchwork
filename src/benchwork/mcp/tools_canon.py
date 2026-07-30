"""Canonical research and Seal MCP tool registration."""

from __future__ import annotations

from .registration import register_tools
from .runtime import BenchworkTools
from .tool_registry import tool_names

CANON_TOOLS = tool_names("canonical")


def register_canon_tools(server: object, tools: BenchworkTools) -> None:
    register_tools(server, tools, CANON_TOOLS)
