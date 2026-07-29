"""Athanor: deterministic canonical transitions for Benchwork."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterator
from uuid import uuid4

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None
    import msvcrt


class AthanorError(ValueError):
    """Raised when a proposed state transition violates an Athanor invariant."""


IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_]*-[A-Z0-9][A-Z0-9_-]*$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SIGIL = re.compile(r"^sha256:[a-f0-9]{64}$")
EVIDENCE_RELATIONS = {"SUPPORTS", "CONTRADICTS", "LIMITS", "REPRODUCES", "UNRESOLVED"}
EVIDENCE_VERIFICATION_KEYS = {
    "source_resolved",
    "content_inspected",
    "claim_relation_verified",
    "locally_reproduced",
}
ISSUE_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
DEVIATION_KINDS = {"PLANNED", "UNPLANNED"}
DEVIATION_IMPACTS = {"NONE", "MINOR", "MAJOR", "INVALIDATING"}
PROGRAM_OBJECT_COLLECTIONS = (
    "evidence",
    "claims",
    "hypotheses",
    "protocols",
    "workings",
    "experiments",
    "runs",
    "result_bundles",
    "assessments",
    "decisions",
    "artifacts",
    "issues",
    "deviations",
)
PROGRAM_STATUS_ORDER = {
    status: index
    for index, status in enumerate(
        (
            "IDEA",
            "EVIDENCE_READY",
            "GAP_SUPPORTED",
            "RQ_FROZEN",
            "DESIGN_FROZEN",
            "IMPLEMENTED",
            "PILOTED",
            "RUNNING",
            "RESULT_READY",
            "EVALUATED",
        )
    )
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_sigil(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _advance_program(program: dict[str, Any], status: str) -> None:
    if PROGRAM_STATUS_ORDER[status] > PROGRAM_STATUS_ORDER[program["status"]]:
        program["status"] = status


def _object_program_id(
    object_id: str,
    programs: dict[str, dict[str, Any]],
    *collections: dict[str, dict[str, Any]],
) -> str | None:
    if object_id in programs:
        return object_id
    for collection in collections:
        record = collection.get(object_id)
        if record is not None:
            return record.get("program_id")
    return None


def _state_object_program_id(state: dict[str, Any], object_id: str) -> str | None:
    return _object_program_id(
        object_id,
        state["programs"],
        *(state[name] for name in PROGRAM_OBJECT_COLLECTIONS),
    )


@contextmanager
def _exclusive_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        else:  # pragma: no cover - Windows
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            else:  # pragma: no cover - Windows
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    event_id: str
    sigil: str
    previous_sigil: str | None
    accepted_at: str

    def as_dict(self) -> dict[str, str | None]:
        return self.__dict__.copy()


TransitionBuilder = Callable[[list[dict[str, Any]]], tuple[str, str, dict[str, Any]]]


class Chronicle:
    """A transactional JSONL event chain with an independently checked head."""

    def __init__(self, root: Path) -> None:
        base = root / ".benchwork"
        self.path = base / "chronicle.jsonl"
        self.head_path = base / "chronicle.head"
        self.lock_path = base / "chronicle.lock"

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(self.lock_path):
            self.path.touch(exist_ok=True)
            if not self.head_path.exists():
                if self.path.stat().st_size:
                    raise AthanorError("Chronicle head is missing for a non-empty ledger")
                self._write_head(0, None)

    def _write_head(self, count: int, sigil: str | None) -> None:
        temporary = self.head_path.with_suffix(".head.tmp")
        temporary.write_text(canonical_json({"count": count, "sigil": sigil}) + "\n", encoding="utf-8")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, self.head_path)
        directory = os.open(self.head_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def _parse(self, text: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        previous_sigil: str | None = None
        for line_number, line in enumerate(text.splitlines(), start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise AthanorError(f"invalid Chronicle event at line {line_number}") from error
            receipt = event.get("receipt", {})
            expected = content_sigil({key: value for key, value in event.items() if key != "receipt"})
            if receipt.get("sigil") != expected:
                raise AthanorError(f"invalid Sigil at Chronicle line {line_number}")
            if event.get("previous_sigil") != previous_sigil:
                raise AthanorError(f"broken Chronicle chain at line {line_number}")
            if receipt.get("previous_sigil") != previous_sigil:
                raise AthanorError(f"Receipt chain reference mismatch at line {line_number}")
            if receipt.get("event_id") != event.get("event_id"):
                raise AthanorError(f"Receipt does not match event at line {line_number}")
            previous_sigil = expected
            events.append(event)
        return events

    def _read_locked(self) -> list[dict[str, Any]]:
        if not self.path.exists() or not self.head_path.exists():
            return []
        events = self._parse(self.path.read_text(encoding="utf-8"))
        try:
            head = json.loads(self.head_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise AthanorError("invalid Chronicle head") from error
        actual_sigil = events[-1]["receipt"]["sigil"] if events else None
        if head != {"count": len(events), "sigil": actual_sigil}:
            raise AthanorError("Chronicle head mismatch; truncation or incomplete commit detected")
        return events

    def events(self) -> list[dict[str, Any]]:
        self.initialize()
        with _exclusive_lock(self.lock_path):
            return self._read_locked()

    def transact(self, build: TransitionBuilder) -> tuple[dict[str, Any], Receipt]:
        self.initialize()
        with _exclusive_lock(self.lock_path):
            events = self._read_locked()
            event_type, object_id, payload = build(events)
            previous_sigil = events[-1]["receipt"]["sigil"] if events else None
            accepted_at = datetime.now(UTC).isoformat()
            event = {
                "schema_version": "chronicle-event/1.0",
                "event_id": f"CE-{uuid4().hex[:12].upper()}",
                "type": event_type,
                "object_id": object_id,
                "occurred_at": accepted_at,
                "previous_sigil": previous_sigil,
                "payload": payload,
            }
            receipt = Receipt(
                receipt_id=f"RC-{uuid4().hex[:12].upper()}",
                event_id=event["event_id"],
                sigil=content_sigil(event),
                previous_sigil=previous_sigil,
                accepted_at=accepted_at,
            )
            event["receipt"] = receipt.as_dict()
            from .schema_validation import validate_instance

            validate_instance("chronicle-event-1.0.json", event)
            with self.path.open("a", encoding="utf-8") as ledger:
                ledger.write(canonical_json(event) + "\n")
                ledger.flush()
                os.fsync(ledger.fileno())
            self._write_head(len(events) + 1, receipt.sigil)
            return event, receipt


class Athanor:
    """Validates canonical research transitions and rebuilds their projections."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.chronicle = Chronicle(root)

    def initialize(self) -> None:
        self.chronicle.initialize()

    def _project(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        programs: dict[str, dict[str, Any]] = {}
        protocols: dict[str, dict[str, Any]] = {}
        approvals: dict[str, dict[str, Any]] = {}
        workings: dict[str, dict[str, Any]] = {}
        experiments: dict[str, dict[str, Any]] = {}
        runs: dict[str, dict[str, Any]] = {}
        result_bundles: dict[str, dict[str, Any]] = {}
        evidence: dict[str, dict[str, Any]] = {}
        claims: dict[str, dict[str, Any]] = {}
        hypotheses: dict[str, dict[str, Any]] = {}
        assessments: dict[str, dict[str, Any]] = {}
        decisions: dict[str, dict[str, Any]] = {}
        artifacts: dict[str, dict[str, Any]] = {}
        issues: dict[str, dict[str, Any]] = {}
        deviations: dict[str, dict[str, Any]] = {}
        for event in events:
            payload = event["payload"]
            object_id = event["object_id"]
            if event["type"] == "program.created":
                if object_id in programs:
                    raise AthanorError(f"duplicate Research Program: {object_id}")
                programs[object_id] = {
                    "schema_version": "research-program/1.0",
                    "program_id": object_id,
                    "slug": payload["slug"],
                    "title": payload["title"],
                    "problem": payload["problem"],
                    "status": "IDEA",
                    "evidence": [],
                    "claims": [],
                    "hypotheses": [],
                    "protocols": [],
                    "assessments": [],
                    "decisions": [],
                    "artifacts": [],
                    "issues": [],
                    "deviations": [],
                }
            elif event["type"] == "evidence.recorded":
                program = programs.get(payload["program_id"])
                if program is None or object_id in evidence:
                    raise AthanorError(f"invalid Evidence record: {object_id}")
                evidence[object_id] = {
                    "schema_version": "evidence/1.1",
                    "evidence_id": object_id,
                    "program_id": payload["program_id"],
                    "source": payload["source"],
                    "observation": payload["observation"],
                    "claim_relations": [],
                    "verification": payload["verification"],
                }
                program["evidence"].append(object_id)
                _advance_program(program, "EVIDENCE_READY")
            elif event["type"] == "evidence.verified":
                record = evidence.get(object_id)
                verification = payload["verification"]
                if record is None or any(
                    record["verification"][key] and not verification[key]
                    for key in EVIDENCE_VERIFICATION_KEYS
                ):
                    raise AthanorError(f"invalid Evidence verification: {object_id}")
                record["verification"] = verification
            elif event["type"] == "claim.created":
                program = programs.get(payload["program_id"])
                relations = payload["evidence_relations"]
                related_evidence = [evidence.get(relation["evidence_id"]) for relation in relations]
                if (
                    program is None
                    or object_id in claims
                    or len({relation["evidence_id"] for relation in relations}) != len(relations)
                    or any(
                        record is None
                        or record["program_id"] != payload["program_id"]
                        or not record["verification"]["source_resolved"]
                        or not record["verification"]["content_inspected"]
                        for record in related_evidence
                    )
                ):
                    raise AthanorError(f"invalid Claim creation: {object_id}")
                claims[object_id] = {
                    "schema_version": "claim/1.1",
                    "claim_id": object_id,
                    "program_id": payload["program_id"],
                    "type": payload["type"],
                    "statement": payload["statement"],
                    "status": "PROPOSED",
                    "evidence_relations": relations,
                }
                for relation, record in zip(relations, related_evidence, strict=True):
                    record["claim_relations"].append(
                        {"claim_id": object_id, "relation": relation["relation"]}
                    )
                    record["verification"]["claim_relation_verified"] = True
                program["claims"].append(object_id)
                if any(
                    relation["relation"] in {"SUPPORTS", "REPRODUCES"}
                    for relation in relations
                ):
                    _advance_program(program, "GAP_SUPPORTED")
            elif event["type"] == "hypothesis.created":
                program = programs.get(payload["program_id"])
                related_claims = [claims.get(claim_id) for claim_id in payload["claim_ids"]]
                if (
                    program is None
                    or object_id in hypotheses
                    or len(set(payload["claim_ids"])) != len(payload["claim_ids"])
                    or any(
                        claim is None or claim["program_id"] != payload["program_id"]
                        for claim in related_claims
                    )
                ):
                    raise AthanorError(f"invalid Hypothesis creation: {object_id}")
                hypotheses[object_id] = {
                    "schema_version": "hypothesis/1.0",
                    "hypothesis_id": object_id,
                    "program_id": payload["program_id"],
                    "claim_ids": payload["claim_ids"],
                    "statement": payload["statement"],
                    "prediction": payload["prediction"],
                    "status": "PROPOSED",
                }
                program["hypotheses"].append(object_id)
                _advance_program(program, "RQ_FROZEN")
            elif event["type"] == "protocol.drafted":
                hypothesis_ids = payload.get("hypothesis_ids", [])
                if (
                    payload["program_id"] not in programs
                    or object_id in protocols
                    or len(set(hypothesis_ids)) != len(hypothesis_ids)
                    or any(
                        hypothesis_id not in hypotheses
                        or hypotheses[hypothesis_id]["program_id"] != payload["program_id"]
                        for hypothesis_id in hypothesis_ids
                    )
                ):
                    raise AthanorError(f"invalid Protocol draft: {object_id}")
                protocols[object_id] = {
                    "schema_version": "study-protocol/1.0",
                    "protocol_id": object_id,
                    "program_id": payload["program_id"],
                    "hypothesis_ids": hypothesis_ids,
                    "title": payload["title"],
                    "analysis_plan": payload["analysis_plan"],
                    "status": "DRAFT",
                    "deviations": [],
                    "sealed_at": None,
                    "seal_receipt": None,
                }
            elif event["type"] == "protocol.sealed":
                protocol = protocols.get(object_id)
                if protocol is None or protocol["status"] != "DRAFT":
                    raise AthanorError(f"invalid Protocol Seal: {object_id}")
                protocol["status"] = "FROZEN"
                protocol["sealed_at"] = event["occurred_at"]
                protocol["seal_receipt"] = event["receipt"]["receipt_id"]
                program = programs[protocol["program_id"]]
                program["protocols"].append(object_id)
                _advance_program(program, "DESIGN_FROZEN")
            elif event["type"] == "approval.granted":
                if object_id in approvals:
                    raise AthanorError(f"duplicate approval for Task: {object_id}")
                approvals[object_id] = {
                    "task_id": object_id,
                    **payload,
                    "receipt_id": event["receipt"]["receipt_id"],
                    "granted_at": event["occurred_at"],
                }
            elif event["type"] == "working.created":
                protocol = protocols.get(payload["protocol_id"])
                rite = payload["rite"]
                if (
                    object_id in workings
                    or protocol is None
                    or protocol["status"] != "FROZEN"
                    or protocol["program_id"] != payload["program_id"]
                    or payload["rite_sigil"] != content_sigil(rite)
                ):
                    raise AthanorError(f"invalid Working creation: {object_id}")
                first_stage = rite["stages"][0]["name"]
                workings[object_id] = {
                    "schema_version": "working/1.0",
                    "working_id": object_id,
                    "rite_id": payload["rite_id"],
                    "rite_sigil": payload["rite_sigil"],
                    "rite": rite,
                    "program_id": payload["program_id"],
                    "protocol_id": payload["protocol_id"],
                    "stage": first_stage,
                    "history": [{"stage": first_stage, "at": event["occurred_at"], "reason": "created", "artifacts": []}],
                }
            elif event["type"] == "working.advanced":
                working = workings.get(object_id)
                if working is None or payload["from_stage"] != working["stage"]:
                    raise AthanorError(f"invalid Working transition: {object_id}")
                stages = [stage["name"] for stage in working["rite"]["stages"]]
                index = stages.index(working["stage"])
                if index + 1 >= len(stages) or payload["to_stage"] != stages[index + 1]:
                    raise AthanorError(f"invalid Working transition: {object_id}")
                working["stage"] = payload["to_stage"]
                working["history"].append(
                    {
                        "stage": payload["to_stage"],
                        "at": event["occurred_at"],
                        "reason": payload["reason"],
                        "artifacts": payload["artifacts"],
                    }
                )
            elif event["type"] == "experiment.created":
                protocol = protocols.get(payload["protocol_id"])
                hypothesis_id = payload["hypothesis_id"]
                hypothesis = hypotheses.get(hypothesis_id) if hypothesis_id is not None else None
                if (
                    object_id in experiments
                    or protocol is None
                    or protocol["status"] != "FROZEN"
                    or protocol["program_id"] != payload["program_id"]
                    or (
                        hypothesis_id is not None
                        and protocol["hypothesis_ids"]
                        and (
                            hypothesis is None
                            or hypothesis["program_id"] != payload["program_id"]
                            or hypothesis_id not in protocol["hypothesis_ids"]
                        )
                    )
                ):
                    raise AthanorError(f"invalid Experiment creation: {object_id}")
                experiments[object_id] = {
                    "schema_version": "experiment/1.0",
                    "experiment_id": object_id,
                    "program_id": payload["program_id"],
                    "protocol_id": payload["protocol_id"],
                    "hypothesis_id": payload["hypothesis_id"],
                    "question": payload["question"],
                    "status": "PLANNED",
                }
                if hypothesis is not None:
                    hypothesis["status"] = "ACTIVE"
            elif event["type"] == "run.recorded":
                experiment = experiments.get(payload["experiment_id"])
                if (
                    object_id in runs
                    or experiment is None
                    or experiment["program_id"] != payload["program_id"]
                    or experiment["protocol_id"] != payload["protocol_id"]
                ):
                    raise AthanorError(f"invalid Run record: {object_id}")
                if payload["analysis_included"] and payload["status"] != "COMPLETED":
                    raise AthanorError(f"non-completed Run cannot be included: {object_id}")
                runs[object_id] = {
                    "schema_version": "run/1.0",
                    "run_id": object_id,
                    "program_id": payload["program_id"],
                    "protocol_id": payload["protocol_id"],
                    "experiment_id": payload["experiment_id"],
                    "status": payload["status"],
                    "analysis_included": payload["analysis_included"],
                    "seed": payload["seed"],
                    "metrics": payload["metrics"],
                    "artifacts": payload["artifacts"],
                }
                _advance_program(programs[payload["program_id"]], "RUNNING")
            elif event["type"] == "analysis.computed":
                from .alembic import build_result_bundle

                bundle = payload["bundle"]
                expected = build_result_bundle(
                    object_id,
                    bundle["program_id"],
                    bundle["protocol_id"],
                    list(runs.values()),
                )
                if (
                    object_id in result_bundles
                    or bundle != expected
                    or payload["bundle_sigil"] != content_sigil(bundle)
                ):
                    raise AthanorError(f"invalid Result Bundle: {object_id}")
                result_bundles[object_id] = bundle
                _advance_program(programs[bundle["program_id"]], "RESULT_READY")
            elif event["type"] == "assessment.recorded":
                bundle = result_bundles.get(payload["result_bundle_id"])
                program = programs.get(payload["program_id"])
                protocol = protocols.get(payload["protocol_id"])
                claim_findings = payload["claim_findings"]
                hypothesis_findings = payload["hypothesis_findings"]
                if (
                    object_id in assessments
                    or bundle is None
                    or program is None
                    or protocol is None
                    or bundle["program_id"] != payload["program_id"]
                    or bundle["protocol_id"] != payload["protocol_id"]
                    or len({finding["claim_id"] for finding in claim_findings}) != len(claim_findings)
                    or len({finding["hypothesis_id"] for finding in hypothesis_findings})
                    != len(hypothesis_findings)
                    or any(
                        finding["claim_id"] not in claims
                        or claims[finding["claim_id"]]["program_id"] != payload["program_id"]
                        for finding in claim_findings
                    )
                    or any(
                        finding["hypothesis_id"] not in hypotheses
                        or hypotheses[finding["hypothesis_id"]]["program_id"] != payload["program_id"]
                        or finding["hypothesis_id"] not in protocol["hypothesis_ids"]
                        for finding in hypothesis_findings
                    )
                ):
                    raise AthanorError(f"invalid Assessment: {object_id}")
                assessments[object_id] = {
                    "schema_version": "assessment/1.1",
                    "assessment_id": object_id,
                    "program_id": payload["program_id"],
                    "protocol_id": payload["protocol_id"],
                    "result_bundle_id": payload["result_bundle_id"],
                    "result_bundle": {
                        "uri": f".benchwork/results/{payload['result_bundle_id']}.json",
                        "sigil": content_sigil(bundle),
                    },
                    "summary": payload["summary"],
                    "limitations": payload["limitations"],
                    "claim_findings": claim_findings,
                    "hypothesis_findings": hypothesis_findings,
                    "status": "COMPLETE",
                    "reviewed_at": event["occurred_at"],
                    "review_receipt": event["receipt"]["receipt_id"],
                }
                for finding in claim_findings:
                    claims[finding["claim_id"]]["status"] = finding["status"]
                for finding in hypothesis_findings:
                    hypotheses[finding["hypothesis_id"]]["status"] = finding["status"]
                program["assessments"].append(object_id)
                _advance_program(program, "EVALUATED")
            elif event["type"] == "decision.sealed":
                program = programs.get(payload["program_id"])
                related_assessments = [
                    assessments.get(assessment_id) for assessment_id in payload["assessment_ids"]
                ]
                if (
                    object_id in decisions
                    or program is None
                    or len(set(payload["assessment_ids"])) != len(payload["assessment_ids"])
                    or any(
                        assessment is None
                        or assessment["program_id"] != payload["program_id"]
                        or assessment["status"] != "COMPLETE"
                        for assessment in related_assessments
                    )
                ):
                    raise AthanorError(f"invalid Decision Seal: {object_id}")
                decisions[object_id] = {
                    "schema_version": "decision/1.1",
                    "decision_id": object_id,
                    "program_id": payload["program_id"],
                    "outcome": payload["outcome"],
                    "assessment_ids": payload["assessment_ids"],
                    "rationale": payload["rationale"],
                    "status": "SEALED",
                    "sealed_at": event["occurred_at"],
                    "seal_receipt": event["receipt"]["receipt_id"],
                }
                program["decisions"].append(object_id)
            elif event["type"] == "artifact.registered":
                program = programs.get(payload["program_id"])
                related_ids = [payload["producer_id"], *payload["input_ids"]]
                collections = (
                    evidence,
                    claims,
                    hypotheses,
                    protocols,
                    workings,
                    experiments,
                    runs,
                    result_bundles,
                    assessments,
                    decisions,
                    artifacts,
                    issues,
                    deviations,
                )
                if (
                    object_id in artifacts
                    or program is None
                    or len(set(payload["input_ids"])) != len(payload["input_ids"])
                    or any(
                        _object_program_id(reference_id, programs, *collections)
                        != payload["program_id"]
                        for reference_id in related_ids
                    )
                ):
                    raise AthanorError(f"invalid Artifact registration: {object_id}")
                artifacts[object_id] = {
                    "schema_version": "artifact/1.0",
                    "artifact_id": object_id,
                    "program_id": payload["program_id"],
                    "kind": payload["kind"],
                    "location": payload["location"],
                    "producer_id": payload["producer_id"],
                    "input_ids": payload["input_ids"],
                    "status": "REGISTERED",
                    "registered_at": event["occurred_at"],
                    "registration_receipt": event["receipt"]["receipt_id"],
                }
                program["artifacts"].append(object_id)
            elif event["type"] == "issue.opened":
                program = programs.get(payload["program_id"])
                collections = (
                    evidence,
                    claims,
                    hypotheses,
                    protocols,
                    workings,
                    experiments,
                    runs,
                    result_bundles,
                    assessments,
                    decisions,
                    artifacts,
                    issues,
                    deviations,
                )
                if (
                    object_id in issues
                    or program is None
                    or len(set(payload["subject_ids"])) != len(payload["subject_ids"])
                    or any(
                        _object_program_id(subject_id, programs, *collections)
                        != payload["program_id"]
                        for subject_id in payload["subject_ids"]
                    )
                ):
                    raise AthanorError(f"invalid Issue opening: {object_id}")
                issues[object_id] = {
                    "schema_version": "issue/1.0",
                    "issue_id": object_id,
                    "program_id": payload["program_id"],
                    "subject_ids": payload["subject_ids"],
                    "severity": payload["severity"],
                    "title": payload["title"],
                    "description": payload["description"],
                    "status": "OPEN",
                    "opened_at": event["occurred_at"],
                    "open_receipt": event["receipt"]["receipt_id"],
                    "resolution": None,
                    "resolved_at": None,
                    "resolution_receipt": None,
                }
                program["issues"].append(object_id)
            elif event["type"] == "issue.resolved":
                issue = issues.get(object_id)
                if (
                    issue is None
                    or issue["status"] != "OPEN"
                    or payload["program_id"] != issue["program_id"]
                ):
                    raise AthanorError(f"invalid Issue resolution: {object_id}")
                issue["status"] = "RESOLVED"
                issue["resolution"] = payload["resolution"]
                issue["resolved_at"] = event["occurred_at"]
                issue["resolution_receipt"] = event["receipt"]["receipt_id"]
            elif event["type"] == "deviation.recorded":
                program = programs.get(payload["program_id"])
                protocol = protocols.get(payload["protocol_id"])
                collections = (
                    evidence,
                    claims,
                    hypotheses,
                    protocols,
                    workings,
                    experiments,
                    runs,
                    result_bundles,
                    assessments,
                    decisions,
                    artifacts,
                    issues,
                    deviations,
                )
                if (
                    object_id in deviations
                    or program is None
                    or protocol is None
                    or protocol["program_id"] != payload["program_id"]
                    or protocol["status"] != "FROZEN"
                    or len(set(payload["affected_object_ids"]))
                    != len(payload["affected_object_ids"])
                    or any(
                        _object_program_id(affected_id, programs, *collections)
                        != payload["program_id"]
                        for affected_id in payload["affected_object_ids"]
                    )
                ):
                    raise AthanorError(f"invalid Deviation record: {object_id}")
                deviations[object_id] = {
                    "schema_version": "deviation/1.0",
                    "deviation_id": object_id,
                    "program_id": payload["program_id"],
                    "protocol_id": payload["protocol_id"],
                    "kind": payload["kind"],
                    "summary": payload["summary"],
                    "rationale": payload["rationale"],
                    "impact": payload["impact"],
                    "affected_object_ids": payload["affected_object_ids"],
                    "status": "RECORDED",
                    "recorded_at": event["occurred_at"],
                    "record_receipt": event["receipt"]["receipt_id"],
                }
                protocol["deviations"].append(object_id)
                program["deviations"].append(object_id)
            else:
                raise AthanorError(f"unsupported Chronicle event type: {event['type']}")
        from .schema_validation import validate_instance

        for program in programs.values():
            validate_instance("research-program-1.0.json", program)
        for protocol in protocols.values():
            validate_instance("protocol-1.0.json", protocol)
        for working in workings.values():
            validate_instance("working-1.0.json", working)
        for experiment in experiments.values():
            validate_instance("experiment-1.0.json", experiment)
        for run in runs.values():
            validate_instance("run-1.0.json", run)
        for bundle in result_bundles.values():
            validate_instance("result-bundle-1.0.json", bundle)
        for record in evidence.values():
            validate_instance("evidence-1.1.json", record)
        for claim in claims.values():
            validate_instance("claim-1.1.json", claim)
        for hypothesis in hypotheses.values():
            validate_instance("hypothesis-1.0.json", hypothesis)
        for assessment in assessments.values():
            validate_instance("assessment-1.1.json", assessment)
        for decision in decisions.values():
            validate_instance("decision-1.1.json", decision)
        for artifact in artifacts.values():
            validate_instance("artifact-1.0.json", artifact)
        for issue in issues.values():
            validate_instance("issue-1.0.json", issue)
        for deviation in deviations.values():
            validate_instance("deviation-1.0.json", deviation)
        return {
            "programs": programs,
            "protocols": protocols,
            "approvals": approvals,
            "workings": workings,
            "experiments": experiments,
            "runs": runs,
            "result_bundles": result_bundles,
            "evidence": evidence,
            "claims": claims,
            "hypotheses": hypotheses,
            "assessments": assessments,
            "decisions": decisions,
            "artifacts": artifacts,
            "issues": issues,
            "deviations": deviations,
        }

    def replay(self) -> dict[str, Any]:
        return self._project(self.chronicle.events())

    def programs(self) -> dict[str, dict[str, Any]]:
        return self.replay()["programs"]

    def protocols(self) -> dict[str, dict[str, Any]]:
        return self.replay()["protocols"]

    def approvals(self) -> dict[str, dict[str, Any]]:
        return self.replay()["approvals"]

    def workings(self) -> dict[str, dict[str, Any]]:
        return self.replay()["workings"]

    def experiments(self) -> dict[str, dict[str, Any]]:
        return self.replay()["experiments"]

    def runs(self) -> dict[str, dict[str, Any]]:
        return self.replay()["runs"]

    def result_bundles(self) -> dict[str, dict[str, Any]]:
        return self.replay()["result_bundles"]

    def evidence(self) -> dict[str, dict[str, Any]]:
        return self.replay()["evidence"]

    def claims(self) -> dict[str, dict[str, Any]]:
        return self.replay()["claims"]

    def hypotheses(self) -> dict[str, dict[str, Any]]:
        return self.replay()["hypotheses"]

    def assessments(self) -> dict[str, dict[str, Any]]:
        return self.replay()["assessments"]

    def decisions(self) -> dict[str, dict[str, Any]]:
        return self.replay()["decisions"]

    def artifacts(self) -> dict[str, dict[str, Any]]:
        return self.replay()["artifacts"]

    def issues(self) -> dict[str, dict[str, Any]]:
        return self.replay()["issues"]

    def deviations(self) -> dict[str, dict[str, Any]]:
        return self.replay()["deviations"]

    def create_program(self, slug: str, title: str, problem: dict[str, Any] | None = None) -> tuple[str, Receipt]:
        if not SLUG.fullmatch(slug) or not title.strip():
            raise AthanorError("Program requires a lowercase hyphenated slug and non-empty title")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            programs = self._project(events)["programs"]
            if any(program["slug"] == slug for program in programs.values()):
                raise AthanorError(f"program slug already exists: {slug}")
            program_id = f"RP-{len(programs) + 1:03d}"
            return "program.created", program_id, {"slug": slug, "title": title, "problem": problem or {}}

        event, receipt = self.chronicle.transact(build)
        return event["object_id"], receipt

    def record_evidence(
        self,
        evidence_id: str,
        program_id: str,
        source: dict[str, str],
        observation: str,
        verification: dict[str, bool] | None = None,
    ) -> Receipt:
        if not isinstance(evidence_id, str) or not IDENTIFIER.fullmatch(evidence_id) or not evidence_id.startswith("EV-"):
            raise AthanorError("Evidence ID must use the form EV-<identifier>")
        if (
            not isinstance(source, dict)
            or set(source) != {"uri", "sigil"}
            or not isinstance(source["uri"], str)
            or not source["uri"]
            or not isinstance(source["sigil"], str)
            or not SIGIL.fullmatch(source["sigil"])
        ):
            raise AthanorError("Evidence source must be a content-addressed URI reference")
        if not isinstance(observation, str) or not observation.strip():
            raise AthanorError("Evidence requires a non-empty observation")
        normalized_verification = (
            verification
            if verification is not None
            else {key: False for key in EVIDENCE_VERIFICATION_KEYS}
        )
        if (
            not isinstance(normalized_verification, dict)
            or set(normalized_verification) != EVIDENCE_VERIFICATION_KEYS
            or any(not isinstance(value, bool) for value in normalized_verification.values())
        ):
            raise AthanorError("Evidence verification requires all four boolean checks")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if evidence_id in state["evidence"]:
                raise AthanorError(f"Evidence already exists: {evidence_id}")
            return "evidence.recorded", evidence_id, {
                "program_id": program_id,
                "source": source,
                "observation": observation,
                "verification": normalized_verification,
            }

        return self.chronicle.transact(build)[1]

    def verify_evidence(self, evidence_id: str, checks: list[str]) -> Receipt:
        requested = set(checks)
        if not requested or not requested.issubset(EVIDENCE_VERIFICATION_KEYS):
            raise AthanorError("Evidence verification requires one or more known checks")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            record = self._project(events)["evidence"].get(evidence_id)
            if record is None:
                raise AthanorError(f"unknown Evidence: {evidence_id}")
            verification = record["verification"].copy()
            for check in requested:
                verification[check] = True
            if verification == record["verification"]:
                raise AthanorError(f"Evidence checks are already verified: {evidence_id}")
            return "evidence.verified", evidence_id, {"verification": verification}

        return self.chronicle.transact(build)[1]

    def create_claim(
        self,
        claim_id: str,
        program_id: str,
        claim_type: str,
        statement: str,
        evidence_relations: list[dict[str, str]],
    ) -> Receipt:
        claim_types = {"empirical", "theoretical", "methodological", "operational"}
        if not isinstance(claim_id, str) or not IDENTIFIER.fullmatch(claim_id) or not claim_id.startswith("CL-"):
            raise AthanorError("Claim ID must use the form CL-<identifier>")
        if claim_type not in claim_types:
            raise AthanorError(f"unknown Claim type: {claim_type}")
        if not isinstance(statement, str) or not statement.strip():
            raise AthanorError("Claim requires a non-empty statement")
        if not evidence_relations or any(
            not isinstance(relation, dict)
            or set(relation) != {"evidence_id", "relation"}
            or not isinstance(relation["evidence_id"], str)
            or not relation["evidence_id"].startswith("EV-")
            or relation["relation"] not in EVIDENCE_RELATIONS
            for relation in evidence_relations
        ):
            raise AthanorError("Claim requires typed Evidence relations")
        if len({relation["evidence_id"] for relation in evidence_relations}) != len(
            evidence_relations
        ):
            raise AthanorError("Claim Evidence relations must be unique")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if claim_id in state["claims"]:
                raise AthanorError(f"Claim already exists: {claim_id}")
            for relation in evidence_relations:
                record = state["evidence"].get(relation["evidence_id"])
                if record is None or record["program_id"] != program_id:
                    raise AthanorError(f"unknown Program Evidence: {relation['evidence_id']}")
                if not (
                    record["verification"]["source_resolved"]
                    and record["verification"]["content_inspected"]
                ):
                    raise AthanorError(
                        f"Claim requires resolved and inspected Evidence: {relation['evidence_id']}"
                    )
            return "claim.created", claim_id, {
                "program_id": program_id,
                "type": claim_type,
                "statement": statement,
                "evidence_relations": evidence_relations,
            }

        return self.chronicle.transact(build)[1]

    def create_hypothesis(
        self,
        hypothesis_id: str,
        program_id: str,
        claim_ids: list[str],
        statement: str,
        prediction: str,
    ) -> Receipt:
        if (
            not isinstance(hypothesis_id, str)
            or not IDENTIFIER.fullmatch(hypothesis_id)
            or not hypothesis_id.startswith("HY-")
        ):
            raise AthanorError("Hypothesis ID must use the form HY-<identifier>")
        if (
            not isinstance(claim_ids, list)
            or not claim_ids
            or any(
                not isinstance(claim_id, str) or not claim_id.startswith("CL-")
                for claim_id in claim_ids
            )
            or len(set(claim_ids)) != len(claim_ids)
        ):
            raise AthanorError("Hypothesis requires one or more Claim IDs")
        if not isinstance(statement, str) or not statement.strip() or not isinstance(prediction, str) or not prediction.strip():
            raise AthanorError("Hypothesis requires a statement and falsifiable prediction")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if hypothesis_id in state["hypotheses"]:
                raise AthanorError(f"Hypothesis already exists: {hypothesis_id}")
            if any(
                claim_id not in state["claims"]
                or state["claims"][claim_id]["program_id"] != program_id
                for claim_id in claim_ids
            ):
                raise AthanorError("Hypothesis Claims must belong to its Research Program")
            return "hypothesis.created", hypothesis_id, {
                "program_id": program_id,
                "claim_ids": claim_ids,
                "statement": statement,
                "prediction": prediction,
            }

        return self.chronicle.transact(build)[1]

    def draft_protocol(
        self,
        protocol_id: str,
        program_id: str,
        title: str,
        analysis_plan: str,
        hypothesis_ids: list[str] | None = None,
    ) -> Receipt:
        if not IDENTIFIER.fullmatch(protocol_id) or not protocol_id.startswith("PT-"):
            raise AthanorError("Protocol ID must use the form PT-<identifier>")
        if not title.strip() or not analysis_plan.strip():
            raise AthanorError("Protocol requires a title and deterministic analysis plan")

        if hypothesis_ids is not None and not isinstance(hypothesis_ids, list):
            raise AthanorError("Protocol Hypotheses must be a list")
        normalized_hypotheses = hypothesis_ids or []
        if any(
            not isinstance(hypothesis_id, str)
            or not hypothesis_id.startswith("HY-")
            for hypothesis_id in normalized_hypotheses
        ):
            raise AthanorError("Protocol Hypotheses must use HY- identifiers")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if protocol_id in state["protocols"]:
                raise AthanorError(f"Protocol already exists: {protocol_id}")
            if len(set(normalized_hypotheses)) != len(normalized_hypotheses) or any(
                hypothesis_id not in state["hypotheses"]
                or state["hypotheses"][hypothesis_id]["program_id"] != program_id
                for hypothesis_id in normalized_hypotheses
            ):
                raise AthanorError("Protocol Hypotheses must belong to its Research Program")
            return "protocol.drafted", protocol_id, {
                "program_id": program_id,
                "hypothesis_ids": normalized_hypotheses,
                "title": title,
                "analysis_plan": analysis_plan,
            }

        return self.chronicle.transact(build)[1]

    def seal_protocol(self, protocol_id: str) -> Receipt:
        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            protocol = self._project(events)["protocols"].get(protocol_id)
            if protocol is None or protocol["status"] != "DRAFT":
                raise AthanorError(f"Protocol is not an unsealed draft: {protocol_id}")
            return "protocol.sealed", protocol_id, {"program_id": protocol["program_id"], "status": "FROZEN"}

        return self.chronicle.transact(build)[1]

    def grant_approval(self, capsule: dict[str, Any], reason: str) -> Receipt:
        if not reason.strip():
            raise AthanorError("approval reason cannot be empty")
        required = {"task_id", "capsule_sigil", "capability", "input_sigil", "circle"}
        if not required.issubset(capsule):
            raise AthanorError("approval requires a complete verified Task Capsule")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            approvals = self._project(events)["approvals"]
            task_id = capsule["task_id"]
            if task_id in approvals:
                raise AthanorError(f"Task already has an approval: {task_id}")
            return "approval.granted", task_id, {
                "reason": reason,
                "capsule_sigil": capsule["capsule_sigil"],
                "capability": capsule["capability"],
                "input_sigil": capsule["input_sigil"],
                "circle": capsule["circle"],
            }

        return self.chronicle.transact(build)[1]

    def create_working(self, rite_id: str, program_id: str, protocol_id: str) -> tuple[str, Receipt]:
        from .rites import RiteRegistry

        rite = RiteRegistry(self.root).get(rite_id)
        rite_sigil = content_sigil(rite)

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            protocol = state["protocols"].get(protocol_id)
            if protocol is None or protocol["status"] != "FROZEN":
                raise AthanorError(f"Working requires a frozen Protocol: {protocol_id}")
            if protocol["program_id"] != program_id:
                raise AthanorError(f"Working Program does not match Protocol: {program_id}")
            working_id = f"WK-{len(state['workings']) + 1:03d}"
            return "working.created", working_id, {
                "rite_id": rite_id,
                "rite_sigil": rite_sigil,
                "rite": rite,
                "program_id": program_id,
                "protocol_id": protocol_id,
            }

        event, receipt = self.chronicle.transact(build)
        return event["object_id"], receipt

    def advance_working(self, working_id: str, reason: str, artifacts: list[dict[str, str]]) -> Receipt:
        if not reason.strip():
            raise AthanorError("Working transition requires a reason")
        if not artifacts or any(
            set(artifact) != {"kind", "uri", "sigil"} or not SIGIL.fullmatch(artifact["sigil"])
            for artifact in artifacts
        ):
            raise AthanorError("Working transition requires typed, content-addressed artifacts")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            working = self._project(events)["workings"].get(working_id)
            if working is None:
                raise AthanorError(f"unknown Working: {working_id}")
            stages = working["rite"]["stages"]
            names = [stage["name"] for stage in stages]
            index = names.index(working["stage"])
            if index + 1 >= len(stages):
                raise AthanorError(f"Working is already terminal: {working_id}")
            required_kind = stages[index]["exit_artifact"]
            if not any(artifact["kind"] == required_kind for artifact in artifacts):
                raise AthanorError(f"Working stage {working['stage']} requires artifact kind {required_kind}")
            return "working.advanced", working_id, {
                "from_stage": working["stage"],
                "to_stage": names[index + 1],
                "reason": reason,
                "artifacts": artifacts,
            }

        return self.chronicle.transact(build)[1]

    def create_experiment(
        self,
        experiment_id: str,
        program_id: str,
        protocol_id: str,
        question: str,
        hypothesis_id: str | None = None,
    ) -> Receipt:
        if not IDENTIFIER.fullmatch(experiment_id) or not experiment_id.startswith("EX-"):
            raise AthanorError("Experiment ID must use the form EX-<identifier>")
        if hypothesis_id is not None and (
            not IDENTIFIER.fullmatch(hypothesis_id) or not hypothesis_id.startswith("HY-")
        ):
            raise AthanorError("Hypothesis ID must use the form HY-<identifier>")
        if not question.strip():
            raise AthanorError("Experiment requires a non-empty question")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            protocol = state["protocols"].get(protocol_id)
            if protocol is None or protocol["status"] != "FROZEN":
                raise AthanorError(f"Experiment requires a frozen Protocol: {protocol_id}")
            if protocol["program_id"] != program_id:
                raise AthanorError(f"Experiment Program does not match Protocol: {program_id}")
            if experiment_id in state["experiments"]:
                raise AthanorError(f"Experiment already exists: {experiment_id}")
            if hypothesis_id is not None and protocol["hypothesis_ids"]:
                hypothesis = state["hypotheses"].get(hypothesis_id)
                if (
                    hypothesis is None
                    or hypothesis["program_id"] != program_id
                    or hypothesis_id not in protocol["hypothesis_ids"]
                ):
                    raise AthanorError(
                        f"Experiment Hypothesis was not registered by Protocol: {hypothesis_id}"
                    )
            return "experiment.created", experiment_id, {
                "program_id": program_id,
                "protocol_id": protocol_id,
                "hypothesis_id": hypothesis_id,
                "question": question,
            }

        return self.chronicle.transact(build)[1]

    def record_run(
        self,
        run_id: str,
        experiment_id: str,
        status: str,
        analysis_included: bool,
        metrics: dict[str, float | int] | None = None,
        seed: int | None = None,
        artifacts: list[dict[str, str]] | None = None,
    ) -> Receipt:
        statuses = {"QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "LOST"}
        if not IDENTIFIER.fullmatch(run_id) or not run_id.startswith("RUN-"):
            raise AthanorError("Run ID must use the form RUN-<identifier>")
        if status not in statuses:
            raise AthanorError(f"unknown Run status: {status}")
        if analysis_included and status != "COMPLETED":
            raise AthanorError("only a completed Run can be included in analysis")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise AthanorError("Run seed must be an integer or null")
        if metrics is not None and not isinstance(metrics, dict):
            raise AthanorError("Run metrics must be a name-to-number object")
        normalized_metrics = metrics or {}
        if analysis_included and not normalized_metrics:
            raise AthanorError("an included Run requires at least one metric")
        if any(
            not isinstance(name, str)
            or not name.strip()
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for name, value in normalized_metrics.items()
        ):
            raise AthanorError("Run metrics require non-empty names and finite numeric values")
        normalized_artifacts = artifacts or []
        if any(
            not isinstance(artifact, dict)
            or set(artifact) != {"uri", "sigil"}
            or not isinstance(artifact["uri"], str)
            or not artifact["uri"]
            or not isinstance(artifact["sigil"], str)
            or not SIGIL.fullmatch(artifact["sigil"])
            for artifact in normalized_artifacts
        ):
            raise AthanorError("Run artifacts must be content-addressed URI references")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            experiment = state["experiments"].get(experiment_id)
            if experiment is None:
                raise AthanorError(f"unknown Experiment: {experiment_id}")
            if run_id in state["runs"]:
                raise AthanorError(f"Run already exists: {run_id}")
            return "run.recorded", run_id, {
                "program_id": experiment["program_id"],
                "protocol_id": experiment["protocol_id"],
                "experiment_id": experiment_id,
                "status": status,
                "analysis_included": analysis_included,
                "seed": seed,
                "metrics": normalized_metrics,
                "artifacts": normalized_artifacts,
            }

        return self.chronicle.transact(build)[1]

    def compute_analysis(
        self, program_id: str, protocol_id: str
    ) -> tuple[dict[str, Any], str, Receipt, Path]:
        from .alembic import build_result_bundle, export_result_bundle

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            protocol = state["protocols"].get(protocol_id)
            if protocol is None or protocol["program_id"] != program_id:
                raise AthanorError(f"Protocol {protocol_id} does not belong to Program {program_id}")
            bundle_id = f"RB-{len(state['result_bundles']) + 1:03d}"
            bundle = build_result_bundle(bundle_id, program_id, protocol_id, list(state["runs"].values()))
            return "analysis.computed", bundle_id, {
                "bundle": bundle,
                "bundle_sigil": content_sigil(bundle),
            }

        event, receipt = self.chronicle.transact(build)
        bundle = event["payload"]["bundle"]
        path = export_result_bundle(self.root, bundle)
        return bundle, event["payload"]["bundle_sigil"], receipt, path

    def review_result(
        self,
        result_bundle_id: str,
        summary: str,
        limitations: list[str],
        claim_findings: list[dict[str, str]],
        hypothesis_findings: list[dict[str, str]],
    ) -> tuple[str, Receipt]:
        claim_statuses = {"SUPPORTED", "CONTESTED", "REJECTED", "UNRESOLVED"}
        hypothesis_statuses = {"SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE", "REJECTED"}
        if not isinstance(summary, str) or not summary.strip():
            raise AthanorError("Assessment requires a non-empty summary")
        if not isinstance(limitations, list) or any(
            not isinstance(item, str) or not item.strip() for item in limitations
        ):
            raise AthanorError("Assessment limitations must be non-empty strings")
        if not isinstance(claim_findings, list) or any(
            not isinstance(finding, dict)
            or set(finding) != {"claim_id", "status", "rationale"}
            or not isinstance(finding["claim_id"], str)
            or not finding["claim_id"].startswith("CL-")
            or finding["status"] not in claim_statuses
            or not isinstance(finding["rationale"], str)
            or not finding["rationale"].strip()
            for finding in claim_findings
        ):
            raise AthanorError("Assessment Claim findings are invalid")
        if (
            len({finding["claim_id"] for finding in claim_findings})
            != len(claim_findings)
        ):
            raise AthanorError("Assessment Claim findings must be unique")
        if not isinstance(hypothesis_findings, list) or not hypothesis_findings or any(
            not isinstance(finding, dict)
            or set(finding) != {"hypothesis_id", "status", "rationale"}
            or not isinstance(finding["hypothesis_id"], str)
            or not finding["hypothesis_id"].startswith("HY-")
            or finding["status"] not in hypothesis_statuses
            or not isinstance(finding["rationale"], str)
            or not finding["rationale"].strip()
            for finding in hypothesis_findings
        ):
            raise AthanorError("Assessment requires valid Hypothesis findings")
        if (
            len({finding["hypothesis_id"] for finding in hypothesis_findings})
            != len(hypothesis_findings)
        ):
            raise AthanorError("Assessment Hypothesis findings must be unique")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            bundle = state["result_bundles"].get(result_bundle_id)
            if bundle is None:
                raise AthanorError(f"unknown Result Bundle: {result_bundle_id}")
            for finding in claim_findings:
                claim = state["claims"].get(finding["claim_id"])
                if claim is None or claim["program_id"] != bundle["program_id"]:
                    raise AthanorError(f"unknown Program Claim: {finding['claim_id']}")
            protocol = state["protocols"][bundle["protocol_id"]]
            for finding in hypothesis_findings:
                hypothesis = state["hypotheses"].get(finding["hypothesis_id"])
                if (
                    hypothesis is None
                    or hypothesis["program_id"] != bundle["program_id"]
                    or finding["hypothesis_id"] not in protocol["hypothesis_ids"]
                ):
                    raise AthanorError(
                        f"Hypothesis was not registered by Protocol: {finding['hypothesis_id']}"
                    )
            assessment_id = f"AS-{len(state['assessments']) + 1:03d}"
            return "assessment.recorded", assessment_id, {
                "program_id": bundle["program_id"],
                "protocol_id": bundle["protocol_id"],
                "result_bundle_id": result_bundle_id,
                "summary": summary,
                "limitations": limitations,
                "claim_findings": claim_findings,
                "hypothesis_findings": hypothesis_findings,
            }

        event, receipt = self.chronicle.transact(build)
        return event["object_id"], receipt

    def seal_decision(
        self,
        program_id: str,
        outcome: str,
        assessment_ids: list[str],
        rationale: str,
    ) -> tuple[str, Receipt]:
        outcomes = {
            "CONTINUE",
            "REPAIR",
            "PIVOT",
            "STOP",
            "INSUFFICIENT_EVIDENCE",
            "REVIEW_REQUIRED",
        }
        if outcome not in outcomes:
            raise AthanorError(f"unknown Decision outcome: {outcome}")
        if (
            not isinstance(assessment_ids, list)
            or not assessment_ids
            or any(
                not isinstance(assessment_id, str)
                or not assessment_id.startswith("AS-")
                for assessment_id in assessment_ids
            )
            or len(set(assessment_ids)) != len(assessment_ids)
        ):
            raise AthanorError("Decision requires unique Assessment IDs")
        if not isinstance(rationale, str) or not rationale.strip():
            raise AthanorError("Decision requires a non-empty rationale")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if any(
                assessment_id not in state["assessments"]
                or state["assessments"][assessment_id]["program_id"] != program_id
                or state["assessments"][assessment_id]["status"] != "COMPLETE"
                for assessment_id in assessment_ids
            ):
                raise AthanorError("Decision Assessments must be complete and belong to the Program")
            decision_id = f"DE-{len(state['decisions']) + 1:03d}"
            return "decision.sealed", decision_id, {
                "program_id": program_id,
                "outcome": outcome,
                "assessment_ids": assessment_ids,
                "rationale": rationale,
            }

        event, receipt = self.chronicle.transact(build)
        return event["object_id"], receipt

    def register_artifact(
        self,
        artifact_id: str,
        program_id: str,
        kind: str,
        location: dict[str, str],
        producer_id: str,
        input_ids: list[str] | None = None,
    ) -> Receipt:
        normalized_inputs = [] if input_ids is None else input_ids
        if (
            not isinstance(artifact_id, str)
            or not IDENTIFIER.fullmatch(artifact_id)
            or not artifact_id.startswith("AR-")
        ):
            raise AthanorError("Artifact ID must use the form AR-<identifier>")
        if not isinstance(kind, str) or not kind.strip():
            raise AthanorError("Artifact requires a non-empty kind")
        if (
            not isinstance(location, dict)
            or set(location) != {"uri", "sigil"}
            or not isinstance(location["uri"], str)
            or not location["uri"].strip()
            or not isinstance(location["sigil"], str)
            or not SIGIL.fullmatch(location["sigil"])
        ):
            raise AthanorError("Artifact location must be a content-addressed URI reference")
        if not isinstance(producer_id, str) or not producer_id:
            raise AthanorError("Artifact requires a producer object")
        if (
            not isinstance(normalized_inputs, list)
            or any(not isinstance(input_id, str) or not input_id for input_id in normalized_inputs)
            or len(set(normalized_inputs)) != len(normalized_inputs)
        ):
            raise AthanorError("Artifact input IDs must be unique object references")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if artifact_id in state["artifacts"]:
                raise AthanorError(f"Artifact already exists: {artifact_id}")
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            for reference_id in [producer_id, *normalized_inputs]:
                if _state_object_program_id(state, reference_id) != program_id:
                    raise AthanorError(
                        f"Artifact reference does not belong to Program {program_id}: {reference_id}"
                    )
            return "artifact.registered", artifact_id, {
                "program_id": program_id,
                "kind": kind,
                "location": location,
                "producer_id": producer_id,
                "input_ids": normalized_inputs,
            }

        return self.chronicle.transact(build)[1]

    def open_issue(
        self,
        issue_id: str,
        program_id: str,
        subject_ids: list[str],
        severity: str,
        title: str,
        description: str,
    ) -> Receipt:
        if (
            not isinstance(issue_id, str)
            or not IDENTIFIER.fullmatch(issue_id)
            or not issue_id.startswith("IS-")
        ):
            raise AthanorError("Issue ID must use the form IS-<identifier>")
        if severity not in ISSUE_SEVERITIES:
            raise AthanorError(f"unknown Issue severity: {severity}")
        if not isinstance(title, str) or not title.strip():
            raise AthanorError("Issue requires a non-empty title")
        if not isinstance(description, str) or not description.strip():
            raise AthanorError("Issue requires a non-empty description")
        if (
            not isinstance(subject_ids, list)
            or not subject_ids
            or any(not isinstance(subject_id, str) or not subject_id for subject_id in subject_ids)
            or len(set(subject_ids)) != len(subject_ids)
        ):
            raise AthanorError("Issue requires unique subject object IDs")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if issue_id in state["issues"]:
                raise AthanorError(f"Issue already exists: {issue_id}")
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            for subject_id in subject_ids:
                if _state_object_program_id(state, subject_id) != program_id:
                    raise AthanorError(
                        f"Issue subject does not belong to Program {program_id}: {subject_id}"
                    )
            return "issue.opened", issue_id, {
                "program_id": program_id,
                "subject_ids": subject_ids,
                "severity": severity,
                "title": title,
                "description": description,
            }

        return self.chronicle.transact(build)[1]

    def resolve_issue(self, issue_id: str, resolution: str) -> Receipt:
        if not isinstance(resolution, str) or not resolution.strip():
            raise AthanorError("Issue resolution cannot be empty")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            issue = self._project(events)["issues"].get(issue_id)
            if issue is None:
                raise AthanorError(f"unknown Issue: {issue_id}")
            if issue["status"] != "OPEN":
                raise AthanorError(f"Issue is not open: {issue_id}")
            return "issue.resolved", issue_id, {
                "program_id": issue["program_id"],
                "resolution": resolution,
            }

        return self.chronicle.transact(build)[1]

    def record_deviation(
        self,
        deviation_id: str,
        protocol_id: str,
        kind: str,
        summary: str,
        rationale: str,
        impact: str,
        affected_object_ids: list[str] | None = None,
    ) -> Receipt:
        normalized_affected = [] if affected_object_ids is None else affected_object_ids
        if (
            not isinstance(deviation_id, str)
            or not IDENTIFIER.fullmatch(deviation_id)
            or not deviation_id.startswith("DV-")
        ):
            raise AthanorError("Deviation ID must use the form DV-<identifier>")
        if kind not in DEVIATION_KINDS:
            raise AthanorError(f"unknown Deviation kind: {kind}")
        if impact not in DEVIATION_IMPACTS:
            raise AthanorError(f"unknown Deviation impact: {impact}")
        if not isinstance(summary, str) or not summary.strip():
            raise AthanorError("Deviation requires a non-empty summary")
        if not isinstance(rationale, str) or not rationale.strip():
            raise AthanorError("Deviation requires a non-empty rationale")
        if (
            not isinstance(normalized_affected, list)
            or any(
                not isinstance(object_id, str) or not object_id
                for object_id in normalized_affected
            )
            or len(set(normalized_affected)) != len(normalized_affected)
        ):
            raise AthanorError("Deviation affected object IDs must be unique")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            protocol = state["protocols"].get(protocol_id)
            if protocol is None or protocol["status"] != "FROZEN":
                raise AthanorError(f"Deviation requires a frozen Protocol: {protocol_id}")
            if deviation_id in state["deviations"]:
                raise AthanorError(f"Deviation already exists: {deviation_id}")
            for affected_id in normalized_affected:
                if _state_object_program_id(state, affected_id) != protocol["program_id"]:
                    raise AthanorError(
                        "Deviation affected objects must belong to the Protocol Program: "
                        f"{affected_id}"
                    )
            return "deviation.recorded", deviation_id, {
                "program_id": protocol["program_id"],
                "protocol_id": protocol_id,
                "kind": kind,
                "summary": summary,
                "rationale": rationale,
                "impact": impact,
                "affected_object_ids": normalized_affected,
            }

        return self.chronicle.transact(build)[1]

    def trace(self, object_id: str) -> list[dict[str, Any]]:
        def contains(value: Any) -> bool:
            if value == object_id:
                return True
            if isinstance(value, dict):
                return any(contains(item) for item in value.values())
            if isinstance(value, list):
                return any(contains(item) for item in value)
            return False

        return [
            event
            for event in self.chronicle.events()
            if event["object_id"] == object_id or contains(event["payload"])
        ]
