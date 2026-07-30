"""Canonical research and Seal MCP tool registration."""

from __future__ import annotations

from .registration import register_tools
from .runtime import BenchworkTools

CANON_TOOLS = (
    "benchwork_create_program",
    "benchwork_record_evidence",
    "benchwork_verify_evidence",
    "benchwork_create_claim",
    "benchwork_verify_claim_relation",
    "benchwork_create_hypothesis",
    "benchwork_draft_protocol",
    "benchwork_open_issue",
    "benchwork_record_assessment",
    "benchwork_prepare_review",
    "benchwork_approve_external_review",
    "benchwork_record_review",
    "benchwork_accept_review",
    "benchwork_preview_rq_seal",
    "benchwork_commit_rq_seal",
    "benchwork_preview_protocol_seal",
    "benchwork_commit_protocol_seal",
    "benchwork_preview_decision_seal",
    "benchwork_commit_decision_seal",
)


def register_canon_tools(server: object, tools: BenchworkTools) -> None:
    register_tools(server, tools, CANON_TOOLS)
