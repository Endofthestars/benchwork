"""Symmetric host adapters for Codex and Claude Code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .athanor import Athanor
from .circle import CapsuleStore, CapabilityRegistry, Ward, WardDecision


HOSTS = ("codex", "claude-code")


@dataclass(frozen=True)
class HostProposal:
    """A host-facing view of a Ward-evaluated Task Capsule."""

    host: str
    capsule: dict[str, Any]
    ward: WardDecision

    def as_dict(self) -> dict[str, Any]:
        next_action = {
            "PASS": "delegate_to_host",
            "WAITING_FOR_APPROVAL": "await_human_approval",
            "REJECTED": "correct_task_boundary",
        }[self.ward.status]
        return {
            "host": self.host,
            "task_id": self.capsule["task_id"],
            "capability": self.capsule["capability"],
            "ward": self.ward.as_dict(),
            "next_action": next_action,
        }


class HostAdapter:
    """Converts a host request into a bounded, provider-neutral proposal."""

    def __init__(
        self, host: str, athanor: Athanor, registry: CapabilityRegistry, capsules: CapsuleStore
    ) -> None:
        if host not in HOSTS:
            raise ValueError(f"unsupported Benchwork host: {host}")
        self.host = host
        self.athanor = athanor
        self.registry = registry
        self.capsules = capsules

    def propose(
        self, capability: str, input_sigil: str, tools: list[str], time_budget_seconds: int, network: bool
    ) -> HostProposal:
        self.registry.get(capability)
        capsule = self.capsules.create(
            capability,
            input_sigil,
            {"tools": tools, "time_budget_seconds": time_budget_seconds, "network": network},
            host=self.host,
        )
        ward = Ward(self.registry, set(self.athanor.approvals())).evaluate(capsule)
        return HostProposal(self.host, capsule, ward)


class CodexHostAdapter(HostAdapter):
    def __init__(self, athanor: Athanor, registry: CapabilityRegistry, capsules: CapsuleStore) -> None:
        super().__init__("codex", athanor, registry, capsules)


class ClaudeCodeHostAdapter(HostAdapter):
    def __init__(self, athanor: Athanor, registry: CapabilityRegistry, capsules: CapsuleStore) -> None:
        super().__init__("claude-code", athanor, registry, capsules)
