"""Experiment and deterministic analysis MCP tool registration."""

from __future__ import annotations

from .registration import register_tools
from .runtime import BenchworkTools
from .tool_registry import tool_names

EXPERIMENT_TOOLS = tool_names("experiment")


def register_experiment_tools(server: object, tools: BenchworkTools) -> None:
    register_tools(server, tools, EXPERIMENT_TOOLS)
