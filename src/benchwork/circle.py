"""Circle task boundaries and Ward policy evaluation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from .athanor import AthanorError


TASK_ID = re.compile(r"^TK-[A-Z0-9]+$")
SIGIL = re.compile(r"^sha256:[a-f0-9]{64}$")

DEFAULT_CAPABILITIES: dict[str, dict[str, Any]] = {
    "bench.evidence.discover": {
        "allowed_tools": ["read", "web"],
        "network": True,
        "max_time_seconds": 900,
        "requires_approval": False,
    },
    "bench.code.inspect": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 900,
        "requires_approval": False,
    },
    "bench.code.modify": {
        "allowed_tools": ["read", "write"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": True,
    },
    "bench.experiment.execute": {
        "allowed_tools": ["read", "write", "execute"],
        "network": False,
        "max_time_seconds": 14400,
        "requires_approval": True,
    },
    "bench.analysis.compute": {
        "allowed_tools": ["read", "execute"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": False,
    },
}


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


class CapabilityRegistry:
    """Project-local, reviewable definitions of stable Capability contracts."""

    def __init__(self, root: Path) -> None:
        self.path = root / ".benchwork" / "capabilities.json"

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(_json({"schema_version": "capability-registry/1.0", "capabilities": DEFAULT_CAPABILITIES}))

    def capabilities(self) -> dict[str, dict[str, Any]]:
        self.initialize()
        try:
            registry = json.loads(self.path.read_text())
        except json.JSONDecodeError as error:
            raise AthanorError("invalid Capability Registry") from error
        if registry.get("schema_version") != "capability-registry/1.0":
            raise AthanorError("unsupported Capability Registry version")
        capabilities = registry.get("capabilities")
        if not isinstance(capabilities, dict):
            raise AthanorError("Capability Registry is missing capabilities")
        return capabilities

    def get(self, capability: str) -> dict[str, Any]:
        try:
            return self.capabilities()[capability]
        except KeyError as error:
            raise AthanorError(f"unknown Capability: {capability}") from error


class CapsuleStore:
    """Stores non-canonical immutable Task Capsules under the project boundary."""

    def __init__(self, root: Path) -> None:
        self.path = root / ".benchwork" / "capsules"

    def create(self, capability: str, input_sigil: str, circle: dict[str, Any]) -> dict[str, Any]:
        if not SIGIL.fullmatch(input_sigil):
            raise AthanorError("Task Capsule input Sigil must be a sha256 digest")
        task_id = f"TK-{uuid4().hex[:12].upper()}"
        capsule = {
            "schema_version": "task-capsule/1.0",
            "task_id": task_id,
            "capability": capability,
            "input_sigil": input_sigil,
            "circle": circle,
        }
        self.path.mkdir(parents=True, exist_ok=True)
        path = self.path / f"{task_id}.json"
        path.write_text(_json(capsule))
        return capsule

    def get(self, task_id: str) -> dict[str, Any]:
        if not TASK_ID.fullmatch(task_id):
            raise AthanorError("Task ID must use the form TK-<identifier>")
        path = self.path / f"{task_id}.json"
        if not path.exists():
            raise AthanorError(f"unknown Task Capsule: {task_id}")
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError as error:
            raise AthanorError(f"invalid Task Capsule: {task_id}") from error


@dataclass(frozen=True)
class WardDecision:
    status: str
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "reasons": self.reasons}


class Ward:
    """Checks a Task Capsule against its Capability contract and approvals."""

    def __init__(self, registry: CapabilityRegistry, approvals: set[str]) -> None:
        self.registry = registry
        self.approvals = approvals

    def evaluate(self, capsule: dict[str, Any]) -> WardDecision:
        required = {"schema_version", "task_id", "capability", "input_sigil", "circle"}
        if not required.issubset(capsule):
            return WardDecision("REJECTED", ["Task Capsule is missing required fields"])
        if capsule["schema_version"] != "task-capsule/1.0":
            return WardDecision("REJECTED", ["unsupported Task Capsule version"])
        if not TASK_ID.fullmatch(capsule["task_id"]) or not SIGIL.fullmatch(capsule["input_sigil"]):
            return WardDecision("REJECTED", ["Task Capsule identifiers are invalid"])

        contract = self.registry.get(capsule["capability"])
        circle = capsule["circle"]
        tools = set(circle.get("tools", []))
        allowed_tools = set(contract.get("allowed_tools", []))
        if not tools.issubset(allowed_tools):
            return WardDecision("REJECTED", ["Circle requests tools outside the Capability contract"])
        if not isinstance(circle.get("time_budget_seconds"), int) or circle["time_budget_seconds"] < 1:
            return WardDecision("REJECTED", ["Circle requires a positive time budget"])
        if circle["time_budget_seconds"] > contract.get("max_time_seconds", 0):
            return WardDecision("REJECTED", ["Circle exceeds the Capability time budget"])
        if bool(circle.get("network", False)) and not contract.get("network", False):
            return WardDecision("REJECTED", ["Circle requests network access outside the Capability contract"])
        if contract.get("requires_approval", False) and capsule["task_id"] not in self.approvals:
            return WardDecision("WAITING_FOR_APPROVAL", ["human approval receipt required"])
        return WardDecision("PASS", [])
