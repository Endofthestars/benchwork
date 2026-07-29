"""Athanor: deterministic canonical transitions for Benchwork."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


class AthanorError(ValueError):
    """Raised when a proposed state transition violates an Athanor invariant."""


IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_]*-[A-Z0-9][A-Z0-9_-]*$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sigil(value: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode()).hexdigest()


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    event_id: str
    sigil: str
    previous_sigil: str | None
    accepted_at: str

    def as_dict(self) -> dict[str, str | None]:
        return self.__dict__.copy()


class Chronicle:
    """A locked, append-only JSONL event chain with verifiable receipts."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / ".benchwork" / "chronicle.jsonl"

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        previous_sigil: str | None = None
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise AthanorError(f"invalid Chronicle event at line {line_number}") from error
            receipt = event.get("receipt", {})
            expected = _sigil({key: value for key, value in event.items() if key != "receipt"})
            if receipt.get("sigil") != expected:
                raise AthanorError(f"invalid Sigil at Chronicle line {line_number}")
            if event.get("previous_sigil") != previous_sigil:
                raise AthanorError(f"broken Chronicle chain at line {line_number}")
            if receipt.get("previous_sigil") != event.get("previous_sigil"):
                raise AthanorError(f"Receipt chain reference mismatch at line {line_number}")
            if receipt.get("event_id") != event.get("event_id"):
                raise AthanorError(f"Receipt does not match event at line {line_number}")
            previous_sigil = expected
            events.append(event)
        return events

    def append(self, event_type: str, object_id: str, payload: dict[str, Any]) -> Receipt:
        self.initialize()
        with self.path.open("a+", encoding="utf-8") as ledger:
            fcntl.flock(ledger.fileno(), fcntl.LOCK_EX)
            try:
                ledger.seek(0)
                existing = self.events()
                previous_sigil = existing[-1]["receipt"]["sigil"] if existing else None
                accepted_at = datetime.now(UTC).replace(microsecond=0).isoformat()
                event = {
                    "schema_version": "chronicle-event/1.0",
                    "event_id": f"EV-{uuid4().hex[:12].upper()}",
                    "type": event_type,
                    "object_id": object_id,
                    "occurred_at": accepted_at,
                    "previous_sigil": previous_sigil,
                    "payload": payload,
                }
                receipt = Receipt(
                    receipt_id=f"RC-{uuid4().hex[:12].upper()}",
                    event_id=event["event_id"],
                    sigil=_sigil(event),
                    previous_sigil=previous_sigil,
                    accepted_at=accepted_at,
                )
                event["receipt"] = receipt.as_dict()
                ledger.seek(0, os.SEEK_END)
                ledger.write(_canonical_json(event) + "\n")
                ledger.flush()
                os.fsync(ledger.fileno())
            finally:
                fcntl.flock(ledger.fileno(), fcntl.LOCK_UN)
        return receipt


class Athanor:
    """Validates canonical research transitions and rebuilds their projections."""

    def __init__(self, root: Path) -> None:
        self.chronicle = Chronicle(root)

    def initialize(self) -> None:
        self.chronicle.initialize()

    def replay(self) -> dict[str, Any]:
        """Rebuild durable Program and Protocol state from the complete Chronicle."""
        programs: dict[str, dict[str, Any]] = {}
        protocols: dict[str, dict[str, Any]] = {}
        approvals: dict[str, dict[str, Any]] = {}
        for event in self.chronicle.events():
            payload = event["payload"]
            if event["type"] == "program.created":
                if event["object_id"] in programs:
                    raise AthanorError(f"duplicate Research Program: {event['object_id']}")
                programs[event["object_id"]] = {
                    "program_id": event["object_id"],
                    "slug": payload["slug"],
                    "title": payload["title"],
                    "status": "IDEA",
                    "protocols": [],
                }
            elif event["type"] == "protocol.drafted":
                if payload["program_id"] not in programs:
                    raise AthanorError(f"Protocol references unknown Program: {payload['program_id']}")
                if event["object_id"] in protocols:
                    raise AthanorError(f"duplicate Protocol: {event['object_id']}")
                protocols[event["object_id"]] = {
                    "protocol_id": event["object_id"],
                    "program_id": payload["program_id"],
                    "title": payload["title"],
                    "analysis_plan": payload["analysis_plan"],
                    "status": "DRAFT",
                    "sealed_at": None,
                    "seal_receipt": None,
                }
            elif event["type"] == "protocol.sealed":
                protocol = protocols.get(event["object_id"])
                if protocol is None:
                    raise AthanorError(f"sealed unknown Protocol: {event['object_id']}")
                if protocol["status"] != "DRAFT":
                    raise AthanorError(f"Protocol Seal requires DRAFT state: {event['object_id']}")
                protocol["status"] = "FROZEN"
                protocol["sealed_at"] = event["occurred_at"]
                protocol["seal_receipt"] = event["receipt"]["receipt_id"]
                program = programs[protocol["program_id"]]
                program["protocols"].append(event["object_id"])
                program["status"] = "DESIGN_FROZEN"
            elif event["type"] == "approval.granted":
                if event["object_id"] in approvals:
                    raise AthanorError(f"duplicate approval for Task: {event['object_id']}")
                if not payload.get("reason", "").strip():
                    raise AthanorError(f"approval is missing a reason: {event['object_id']}")
                approvals[event["object_id"]] = {
                    "task_id": event["object_id"],
                    "reason": payload["reason"],
                    "receipt_id": event["receipt"]["receipt_id"],
                    "granted_at": event["occurred_at"],
                }
            else:
                raise AthanorError(f"unsupported Chronicle event type: {event['type']}")
        return {"programs": programs, "protocols": protocols, "approvals": approvals}

    def programs(self) -> dict[str, dict[str, Any]]:
        return self.replay()["programs"]

    def protocols(self) -> dict[str, dict[str, Any]]:
        return self.replay()["protocols"]

    def approvals(self) -> dict[str, dict[str, Any]]:
        return self.replay()["approvals"]

    def create_program(self, slug: str, title: str) -> tuple[str, Receipt]:
        if not SLUG.fullmatch(slug):
            raise AthanorError("program slug must use lowercase letters, digits, and hyphens")
        if not title.strip():
            raise AthanorError("program title cannot be empty")
        programs = self.programs()
        if any(program["slug"] == slug for program in programs.values()):
            raise AthanorError(f"program slug already exists: {slug}")
        program_id = f"RP-{len(programs) + 1:03d}"
        receipt = self.chronicle.append("program.created", program_id, {"slug": slug, "title": title})
        return program_id, receipt

    def draft_protocol(
        self, protocol_id: str, program_id: str, title: str, analysis_plan: str
    ) -> Receipt:
        if not IDENTIFIER.fullmatch(protocol_id) or not protocol_id.startswith("PT-"):
            raise AthanorError("Protocol ID must use the form PT-<identifier>")
        if program_id not in self.programs():
            raise AthanorError(f"unknown Research Program: {program_id}")
        if protocol_id in self.protocols():
            raise AthanorError(f"Protocol already exists: {protocol_id}")
        if not title.strip() or not analysis_plan.strip():
            raise AthanorError("Protocol requires a title and deterministic analysis plan")
        return self.chronicle.append(
            "protocol.drafted",
            protocol_id,
            {"program_id": program_id, "title": title, "analysis_plan": analysis_plan},
        )

    def seal_protocol(self, protocol_id: str) -> Receipt:
        protocol = self.protocols().get(protocol_id)
        if protocol is None:
            raise AthanorError(f"unknown Protocol: {protocol_id}")
        if protocol["status"] == "FROZEN":
            raise AthanorError(f"Protocol already sealed: {protocol_id}")
        return self.chronicle.append(
            "protocol.sealed", protocol_id, {"program_id": protocol["program_id"], "status": "FROZEN"}
        )

    def grant_approval(self, task_id: str, reason: str) -> Receipt:
        if not task_id.startswith("TK-"):
            raise AthanorError("approval requires a Task Capsule ID")
        if not reason.strip():
            raise AthanorError("approval reason cannot be empty")
        if task_id in self.approvals():
            raise AthanorError(f"Task already has an approval: {task_id}")
        return self.chronicle.append("approval.granted", task_id, {"reason": reason})

    def trace(self, object_id: str) -> list[dict[str, Any]]:
        return [event for event in self.chronicle.events() if event["object_id"] == object_id]
