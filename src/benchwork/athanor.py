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


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_sigil(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode()).hexdigest()


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
                    "protocols": [],
                }
            elif event["type"] == "protocol.drafted":
                if payload["program_id"] not in programs or object_id in protocols:
                    raise AthanorError(f"invalid Protocol draft: {object_id}")
                protocols[object_id] = {
                    "schema_version": "study-protocol/1.0",
                    "protocol_id": object_id,
                    "program_id": payload["program_id"],
                    "title": payload["title"],
                    "analysis_plan": payload["analysis_plan"],
                    "status": "DRAFT",
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
                program["status"] = "DESIGN_FROZEN"
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
                if (
                    object_id in experiments
                    or protocol is None
                    or protocol["status"] != "FROZEN"
                    or protocol["program_id"] != payload["program_id"]
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
        return {
            "programs": programs,
            "protocols": protocols,
            "approvals": approvals,
            "workings": workings,
            "experiments": experiments,
            "runs": runs,
            "result_bundles": result_bundles,
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

    def draft_protocol(self, protocol_id: str, program_id: str, title: str, analysis_plan: str) -> Receipt:
        if not IDENTIFIER.fullmatch(protocol_id) or not protocol_id.startswith("PT-"):
            raise AthanorError("Protocol ID must use the form PT-<identifier>")
        if not title.strip() or not analysis_plan.strip():
            raise AthanorError("Protocol requires a title and deterministic analysis plan")

        def build(events: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any]]:
            state = self._project(events)
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            if protocol_id in state["protocols"]:
                raise AthanorError(f"Protocol already exists: {protocol_id}")
            return "protocol.drafted", protocol_id, {
                "program_id": program_id,
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

    def trace(self, object_id: str) -> list[dict[str, Any]]:
        return [event for event in self.chronicle.events() if event["object_id"] == object_id]
