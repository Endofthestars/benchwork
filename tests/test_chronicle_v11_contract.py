import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from benchwork.schema_validation import FORMAT_CHECKER


class ChronicleV11ContractTest(unittest.TestCase):
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

    def _receipt(self) -> dict:
        return {
            "schema_version": "receipt/1.1",
            "receipt_id": "RC-001",
            "event_id": "CE-001",
            "event_body_sigil": "sha256:" + "1" * 64,
            "previous_receipt_sigil": None,
            "accepted_at": "2026-07-29T00:00:00Z",
            "receipt_sigil": "sha256:" + "2" * 64,
        }

    def _event(self) -> dict:
        return {
            "schema_version": "chronicle-event/1.1",
            "event_id": "CE-001",
            "sequence": 1,
            "type": "program.created",
            "object_id": "RP-001",
            "occurred_at": "2026-07-29T00:00:00Z",
            "previous_receipt_sigil": None,
            "actor": {
                "actor_id": "local-user",
                "actor_type": "human",
                "host": "cli",
                "authenticated_by": "local-session",
            },
            "payload": {},
            "event_body_sigil": "sha256:" + "1" * 64,
            "receipt": self._receipt(),
        }

    def _validator(self, name: str) -> Draft202012Validator:
        return Draft202012Validator(
            self.schemas[name],
            registry=self.registry,
            format_checker=FORMAT_CHECKER,
        )

    def test_event_receipt_and_head_contracts_accept_complete_records(self) -> None:
        self._validator("chronicle-event-1.1.json").validate(self._event())
        self._validator("receipt-1.1.json").validate(self._receipt())
        self._validator("chronicle-head-1.1.json").validate(
            {
                "schema_version": "chronicle-head/1.1",
                "event_count": 1,
                "terminal_receipt_sigil": "sha256:" + "2" * 64,
            }
        )

    def test_unknown_event_and_receipt_fields_are_rejected(self) -> None:
        event = self._event()
        event["unknown"] = True
        self.assertFalse(self._validator("chronicle-event-1.1.json").is_valid(event))

        receipt = self._receipt()
        receipt["unknown"] = True
        self.assertFalse(self._validator("receipt-1.1.json").is_valid(receipt))

    def test_invalid_date_time_is_rejected_with_format_checker(self) -> None:
        event = self._event()
        event["occurred_at"] = "not-a-date"
        self.assertFalse(self._validator("chronicle-event-1.1.json").is_valid(event))

        receipt = self._receipt()
        receipt["accepted_at"] = "2026-99-99"
        self.assertFalse(self._validator("receipt-1.1.json").is_valid(receipt))

    def test_sequence_must_start_at_one(self) -> None:
        event = self._event()
        event["sequence"] = 0
        self.assertFalse(self._validator("chronicle-event-1.1.json").is_valid(event))
