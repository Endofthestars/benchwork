"""Circle task boundaries and Ward policy evaluation."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from .athanor import AthanorError, _exclusive_lock, content_sigil


TASK_ID = re.compile(r"^TK-[A-Z0-9]+$")

DEFAULT_CAPABILITIES: dict[str, dict[str, Any]] = {
    "bench.research.orchestrate": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": False,
    },
    "bench.evidence.discover": {
        "allowed_tools": ["read", "web"],
        "network": True,
        "max_time_seconds": 900,
        "requires_approval": False,
    },
    "bench.evidence.synthesize": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": False,
    },
    "bench.evidence.verify": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 900,
        "requires_approval": False,
    },
    "bench.hypothesis.frame": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": False,
    },
    "bench.hypothesis.challenge": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": False,
    },
    "bench.study.design": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": False,
    },
    "bench.study.audit": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 1800,
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
    "bench.experiment.plan": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": False,
    },
    "bench.experiment.collect": {
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
    "bench.analysis.interpret": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": False,
    },
    "bench.decision.review": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": False,
    },
    "bench.decision.propose": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": False,
    },
    "bench.review.prepare": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 900,
        "requires_approval": False,
    },
    "bench.review.local": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 1800,
        "requires_approval": False,
    },
    "bench.review.external": {
        "allowed_tools": ["read", "web"],
        "network": True,
        "max_time_seconds": 1800,
        "requires_approval": True,
    },
    "bench.review.accept": {
        "allowed_tools": ["read"],
        "network": False,
        "max_time_seconds": 900,
        "requires_approval": True,
    },
}

DEFAULT_OUTPUT_SCHEMAS = {
    "bench.research.orchestrate": "research-orchestration-result/1.0",
    "bench.evidence.discover": "evidence-discovery-result/1.0",
    "bench.evidence.synthesize": "evidence-synthesis-result/1.0",
    "bench.evidence.verify": "evidence-verification-result/1.0",
    "bench.hypothesis.frame": "hypothesis-framing-result/1.0",
    "bench.hypothesis.challenge": "hypothesis-challenge-result/1.0",
    "bench.study.design": "study-design-result/1.0",
    "bench.study.audit": "study-audit-result/1.0",
    "bench.code.inspect": "code-inspection-result/1.0",
    "bench.code.modify": "code-modification-result/1.0",
    "bench.experiment.execute": "experiment-execution-result/1.0",
    "bench.experiment.plan": "experiment-plan-result/1.0",
    "bench.experiment.collect": "experiment-collection-result/1.0",
    "bench.analysis.compute": "analysis-computation-result/1.0",
    "bench.analysis.interpret": "analysis-interpretation-result/1.0",
    "bench.decision.review": "decision-review-result/1.0",
    "bench.decision.propose": "decision-proposal-result/1.0",
    "bench.review.prepare": "review-preparation-result/1.0",
    "bench.review.local": "review-execution-result/1.0",
    "bench.review.external": "review-execution-result/1.0",
    "bench.review.accept": "review-acceptance-result/1.0",
}

DEFAULT_CAPABILITIES = {
    capability_id: {
        "contract_version": "1.0",
        **contract,
        "expected_outputs": [{"schema": DEFAULT_OUTPUT_SCHEMAS[capability_id]}],
    }
    for capability_id, contract in DEFAULT_CAPABILITIES.items()
}


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


class CapabilityRegistry:
    """Project-local, reviewable definitions of stable Capability contracts."""

    def __init__(self, root: Path) -> None:
        self.path = root / ".benchwork" / "capabilities.json"
        self.lock_path = root / ".benchwork" / "capabilities.lock"

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(self.lock_path):
            registry = {
                "schema_version": "capability-registry/1.1",
                "capabilities": DEFAULT_CAPABILITIES,
            }
            if self.path.exists():
                try:
                    existing = json.loads(self.path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as error:
                    raise AthanorError("invalid Capability Registry") from error
                capabilities = existing.get("capabilities")
                if (
                    existing.get("schema_version")
                    not in {"capability-registry/1.0", "capability-registry/1.1"}
                    or not isinstance(capabilities, dict)
                ):
                    raise AthanorError("unsupported Capability Registry version")
                unknown = set(capabilities) - set(DEFAULT_CAPABILITIES)
                if existing["schema_version"] == "capability-registry/1.0" and unknown:
                    raise AthanorError(
                        "legacy custom Capabilities require explicit v1.1 output contracts"
                    )
                migrated: dict[str, dict[str, Any]] = {}
                for capability_id, contract in capabilities.items():
                    default = DEFAULT_CAPABILITIES.get(capability_id)
                    if default is None:
                        migrated[capability_id] = contract
                    else:
                        migrated[capability_id] = {**default, **contract}
                registry = {
                    "schema_version": "capability-registry/1.1",
                    "capabilities": migrated,
                }
                changed = False
                for capability, contract in DEFAULT_CAPABILITIES.items():
                    if capability not in migrated:
                        migrated[capability] = contract
                        changed = True
                if not changed and registry == existing:
                    return
            from .schema_validation import validate_instance

            validate_instance("capability-registry-1.1.json", registry)
            temporary = self.path.with_suffix(".json.tmp")
            temporary.write_text(_json(registry), encoding="utf-8")
            with temporary.open("rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)

    def capabilities(self) -> dict[str, dict[str, Any]]:
        self.initialize()
        with _exclusive_lock(self.lock_path):
            try:
                registry = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise AthanorError("invalid Capability Registry") from error
        if registry.get("schema_version") != "capability-registry/1.1":
            raise AthanorError("unsupported Capability Registry version")
        capabilities = registry.get("capabilities")
        if not isinstance(capabilities, dict):
            raise AthanorError("Capability Registry is missing capabilities")
        from .schema_validation import validate_instance

        validate_instance("capability-registry-1.1.json", registry)
        return capabilities

    def verify_existing(self) -> dict[str, dict[str, Any]]:
        """Validate the stored Registry without initializing or repairing it."""
        if not self.path.is_file():
            raise AthanorError("Capability Registry is missing")
        try:
            registry = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AthanorError("invalid Capability Registry") from error
        registry_version = registry.get("schema_version")
        if registry_version == "capability-registry/1.0":
            raise AthanorError(
                "MIGRATION_REQUIRED: Capability Registry v1.0 must be migrated"
            )
        if registry_version != "capability-registry/1.1":
            raise AthanorError("unsupported Capability Registry version")
        from .schema_validation import validate_instance

        validate_instance("capability-registry-1.1.json", registry)
        capabilities = registry["capabilities"]
        missing = sorted(set(DEFAULT_CAPABILITIES) - set(capabilities))
        if missing:
            raise AthanorError(
                "Capability Registry is missing default Capabilities: "
                + ", ".join(missing)
            )
        return capabilities

    def get(self, capability: str) -> dict[str, Any]:
        try:
            return self.capabilities()[capability]
        except KeyError as error:
            raise AthanorError(f"unknown Capability: {capability}") from error

    def contract_sigil(self, capability: str) -> str:
        return content_sigil(
            {"id": capability, "contract": self.get(capability)}
        )


class CapsuleStore:
    """Stores non-canonical immutable Task Capsules under the project boundary."""

    def __init__(self, root: Path) -> None:
        self.path = root / ".benchwork" / "capsules"

    def create(
        self,
        capability: str,
        program_id: str,
        objective: str,
        contract: dict[str, Any],
        contract_sigil: str,
        snapshot: dict[str, Any],
        snapshot_sigil: str,
        circle: dict[str, Any],
        host: str = "cli",
        bindings: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not objective.strip():
            raise AthanorError("Task Capsule objective cannot be empty")
        task_id = f"TK-{uuid4().hex[:12].upper()}"
        capsule = {
            "schema_version": "task-capsule/1.1",
            "task_id": task_id,
            "host": host,
            "program_id": program_id,
            "objective": objective,
            "capability": {
                "id": capability,
                "contract_version": contract["contract_version"],
                "contract_sigil": contract_sigil,
            },
            "snapshot": {
                "snapshot_id": snapshot["snapshot_id"],
                "snapshot_sigil": snapshot_sigil,
            },
            "expected_outputs": contract["expected_outputs"],
            "circle": circle,
        }
        if bindings is not None:
            capsule["bindings"] = bindings
        capsule["capsule_sigil"] = content_sigil(capsule)
        from .schema_validation import validate_instance

        validate_instance("task-capsule-1.1.json", capsule)
        self.path.mkdir(parents=True, exist_ok=True)
        path = self.path / f"{task_id}.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(_json(capsule), encoding="utf-8")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        return capsule

    def get(self, task_id: str) -> dict[str, Any]:
        if not TASK_ID.fullmatch(task_id):
            raise AthanorError("Task ID must use the form TK-<identifier>")
        path = self.path / f"{task_id}.json"
        if not path.exists():
            raise AthanorError(f"unknown Task Capsule: {task_id}")
        try:
            capsule = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            raise AthanorError(f"invalid Task Capsule: {task_id}") from error
        expected = content_sigil(
            {
                key: value
                for key, value in capsule.items()
                if key != "capsule_sigil"
            }
        )
        if capsule.get("capsule_sigil") != expected:
            raise AthanorError(f"Task Capsule Sigil mismatch: {task_id}")
        from .schema_validation import validate_instance

        validate_instance("task-capsule-1.1.json", capsule)
        return capsule


@dataclass(frozen=True)
class WardDecision:
    status: str
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "reasons": self.reasons}


class Ward:
    """Checks a Task Capsule against its Capability contract and approvals."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        approvals: dict[str, dict[str, Any]],
    ) -> None:
        self.registry = registry
        self.approvals = approvals

    def evaluate(self, capsule: dict[str, Any]) -> WardDecision:
        from .schema_validation import validate_instance

        try:
            validate_instance("task-capsule-1.1.json", capsule)
        except AthanorError as error:
            return WardDecision("REJECTED", [str(error)])
        if (
            not TASK_ID.fullmatch(capsule["task_id"])
            or capsule["host"] not in {"cli", "codex", "claude-code"}
        ):
            return WardDecision("REJECTED", ["Task Capsule identifiers are invalid"])
        expected_sigil = content_sigil(
            {
                key: value
                for key, value in capsule.items()
                if key != "capsule_sigil"
            }
        )
        if capsule["capsule_sigil"] != expected_sigil:
            return WardDecision("REJECTED", ["Task Capsule content does not match its Sigil"])

        capability = capsule["capability"]
        contract = self.registry.get(capability["id"])
        current_contract_sigil = self.registry.contract_sigil(capability["id"])
        if (
            capability["contract_version"] != contract["contract_version"]
            or capability["contract_sigil"] != current_contract_sigil
            or capsule["expected_outputs"] != contract["expected_outputs"]
        ):
            return WardDecision(
                "REJECTED",
                ["Capability contract no longer matches the Task Capsule"],
            )
        circle = capsule["circle"]
        tools = set(circle.get("tools", []))
        allowed_tools = set(contract.get("allowed_tools", []))
        if not tools.issubset(allowed_tools):
            return WardDecision(
                "REJECTED",
                ["Circle requests tools outside the Capability contract"],
            )
        if (
            not isinstance(circle.get("time_budget_seconds"), int)
            or circle["time_budget_seconds"] < 1
        ):
            return WardDecision("REJECTED", ["Circle requires a positive time budget"])
        if circle["time_budget_seconds"] > contract.get("max_time_seconds", 0):
            return WardDecision("REJECTED", ["Circle exceeds the Capability time budget"])
        if bool(circle.get("network", False)) and not contract.get("network", False):
            return WardDecision(
                "REJECTED",
                ["Circle requests network access outside the Capability contract"],
            )
        if contract.get("requires_approval", False):
            approval = self.approvals.get(capsule["task_id"])
            binding = {
                "capsule_sigil": capsule["capsule_sigil"],
                "capability": capability["id"],
                "capability_contract_sigil": capability["contract_sigil"],
                "circle": capsule["circle"],
            }
            if approval is None:
                return WardDecision(
                    "WAITING_FOR_APPROVAL",
                    ["human approval receipt required"],
                )
            if any(approval.get(key) != value for key, value in binding.items()):
                return WardDecision(
                    "REJECTED",
                    ["approval does not match the current Task Capsule"],
                )
        return WardDecision("PASS", [])
