"""Experiment and deterministic analysis MCP tool registration."""

from __future__ import annotations

from .registration import register_tools
from .runtime import BenchworkTools

EXPERIMENT_TOOLS = (
    "benchwork_start_working",
    "benchwork_register_artifact",
    "benchwork_create_experiment",
    "benchwork_transition_experiment",
    "benchwork_record_run",
    "benchwork_compute_analysis",
)


def register_experiment_tools(server: object, tools: BenchworkTools) -> None:
    register_tools(server, tools, EXPERIMENT_TOOLS)
