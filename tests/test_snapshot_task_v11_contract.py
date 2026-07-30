import json
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from benchwork.schema_validation import FORMAT_CHECKER


class SnapshotTaskV11ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema_dir = Path(__file__).parents[1] / "schemas"
        cls.schemas = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in schema_dir.glob("*.json")
        }
        cls.registry = Registry()
        for schema in cls.schemas.values():
            cls.registry = cls.registry.with_resource(
                schema["$id"],
                Resource.from_contents(schema),
            )

    def _validator(self, name: str) -> Draft202012Validator:
        return Draft202012Validator(
            self.schemas[name],
            registry=self.registry,
            format_checker=FORMAT_CHECKER,
        )

    def _result(self, status: str = "COMPLETED") -> dict:
        return {
            "schema_version": "agent-result/1.1",
            "task_id": "TK-001",
            "snapshot_sigil": "sha256:" + "1" * 64,
            "capability_contract_sigil": "sha256:" + "2" * 64,
            "status": status,
            "outputs": [
                {
                    "schema": "study-audit-result/1.0",
                    "uri": "proposals/study-audit.json",
                    "blob_sigil": "sha256:" + "3" * 64,
                }
            ],
        }

    def test_snapshot_and_capsule_contracts_accept_complete_records(self) -> None:
        snapshot = {
            "schema_version": "research-snapshot/1.0",
            "snapshot_id": "SS-001",
            "program_id": "RP-001",
            "chronicle_head_sigil": "sha256:" + "1" * 64,
            "objects": [
                {
                    "object_id": "RP-001",
                    "object_type": "research-program",
                    "object_sigil": "sha256:" + "2" * 64,
                }
            ],
            "created_at": "2026-07-29T00:00:00Z",
        }
        capsule = {
            "schema_version": "task-capsule/1.1",
            "task_id": "TK-001",
            "host": "codex",
            "program_id": "RP-001",
            "objective": "Review the registered study design",
            "capability": {
                "id": "bench.study.audit",
                "contract_version": "1.0",
                "contract_sigil": "sha256:" + "3" * 64,
            },
            "snapshot": {
                "snapshot_id": "SS-001",
                "snapshot_sigil": "sha256:" + "4" * 64,
            },
            "expected_outputs": [{"schema": "study-audit-result/1.0"}],
            "circle": {
                "tools": ["read"],
                "time_budget_seconds": 900,
                "network": False,
            },
            "capsule_sigil": "sha256:" + "5" * 64,
        }
        self._validator("research-snapshot-1.0.json").validate(snapshot)
        self._validator("task-capsule-1.1.json").validate(capsule)

    def test_completed_result_requires_output(self) -> None:
        result = self._result()
        result["outputs"] = []
        self.assertFalse(self._validator("agent-result-1.1.json").is_valid(result))

        for status in ("FAILED", "CANCELLED"):
            result["status"] = status
            self.assertTrue(
                self._validator("agent-result-1.1.json").is_valid(result)
            )

    def test_result_rejects_unknown_fields_and_invalid_provenance(self) -> None:
        result = self._result()
        result["unexpected"] = True
        self.assertFalse(self._validator("agent-result-1.1.json").is_valid(result))

        result = self._result()
        result["provenance"] = {}
        self.assertFalse(self._validator("agent-result-1.1.json").is_valid(result))

    def test_contract_and_expected_outputs_are_closed(self) -> None:
        contract = {
            "contract_version": "1.0",
            "allowed_tools": ["read"],
            "network": False,
            "max_time_seconds": 900,
            "requires_approval": False,
            "expected_outputs": [{"schema": "study-audit-result/1.0"}],
        }
        validator = self._validator("capability-contract-1.0.json")
        validator.validate(contract)
        mutated = deepcopy(contract)
        mutated["expected_outputs"][0]["description"] = "unbound field"
        self.assertFalse(validator.is_valid(mutated))
