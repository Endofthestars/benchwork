"""Host-neutral implementation of Benchwork MCP operations."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from ..athanor import Athanor, AthanorError, _exclusive_lock, content_sigil
from ..circle import CapsuleStore, CapabilityRegistry, Ward
from ..doctor import deep_doctor
from ..hosts import HOSTS
from ..execution import ExecutionService
from ..project import ProjectContext, discover_project_root
from ..schema_validation import _schema_directory, validate_instance
from ..tasks import TaskService
from .envelopes import failure, success
from .pagination import page


DEFAULT_HOST = "codex"

CODEX_HUMAN_ACTOR = {
    "actor_id": "interactive-user",
    "actor_type": "human",
    "host": "codex",
    "authenticated_by": "codex-explicit-confirmation",
}

COLLECTIONS = (
    "programs",
    "evidence",
    "claims",
    "hypotheses",
    "protocols",
    "approvals",
    "workings",
    "experiments",
    "runs",
    "result_bundles",
    "assessments",
    "decisions",
    "reproduction_records",
    "artifacts",
    "issues",
    "deviations",
    "agent_results",
    "review_requests",
    "review_artifacts",
)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class BenchworkTools:
    """Typed operations used by both the MCP server and deterministic tests."""

    def __init__(self, root: Path | None = None) -> None:
        self._configured_root = root.resolve() if root is not None else None

    def _root(self) -> Path:
        return discover_project_root(self._configured_root or Path.cwd())

    def _athanor(self) -> Athanor:
        return Athanor(self._root())

    def _execution(self) -> ExecutionService:
        return ExecutionService(self._root())

    def _execution_run(
        self,
        tool: str,
        operation: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        """Render closed executor failures without leaking local runtime detail."""
        try:
            return success(tool, operation())
        except AthanorError as error:
            message = str(error)
            lowered = message.lower()
            if "unknown execution job" in lowered:
                code = "EXECUTION_NOT_FOUND"
            elif "no terminal outcome" in lowered:
                code = "EXECUTION_NOT_READY"
            elif "idempotency conflict" in lowered:
                code = "IDEMPOTENCY_CONFLICT"
            elif "cursor" in lowered:
                code = "STALE_CURSOR"
            elif "outcome is ineligible" in lowered:
                code = "RESULT_INELIGIBLE"
            elif "revision conflict" in lowered or "not terminalizable" in lowered:
                code = "EXECUTION_CONFLICT"
            else:
                code = "EXECUTION_POLICY_REJECTED"
            return failure(tool, error, code=code, project_root=self._configured_root or Path.cwd())

    def _run(
        self,
        tool: str,
        operation: Callable[[], dict[str, Any]],
        *,
        stale_preview_action: bool = False,
    ) -> dict[str, Any]:
        try:
            return operation()
        except json.JSONDecodeError:
            return failure(
                tool,
                ValueError("Project state contains invalid JSON"),
                project_root=self._configured_root or Path.cwd(),
            )
        except OSError:
            return failure(
                tool,
                ValueError("Project state could not be read or written"),
                project_root=self._configured_root or Path.cwd(),
            )
        except ValueError as error:
            actions = (
                [f"Create a new {tool.removeprefix('benchwork_commit_').replace('_', ' ')} preview"]
                if stale_preview_action and "STALE_PREVIEW" in str(error)
                else []
            )
            return failure(
                tool,
                error,
                project_root=self._configured_root or Path.cwd(),
                next_actions=actions,
            )
        except Exception:
            return failure(
                tool,
                ValueError("Internal Benchwork tool failure"),
                code="INTERNAL_ERROR",
                project_root=self._configured_root or Path.cwd(),
            )

    @staticmethod
    def _head(athanor: Athanor) -> str | None:
        events = athanor.chronicle.events()
        return events[-1]["receipt"]["receipt_sigil"] if events else None

    @staticmethod
    def _program_objects(state: dict[str, Any], program_id: str) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for collection in COLLECTIONS:
            records = state.get(collection, {})
            identifiers = sorted(
                identifier
                for identifier, record in records.items()
                if identifier == program_id
                or (
                    isinstance(record, dict)
                    and record.get("program_id") == program_id
                )
            )
            if identifiers:
                result[collection] = identifiers
        return result

    def benchwork_status(self) -> dict[str, Any]:
        """Read a concise project and active-Program status summary."""
        tool = "benchwork_status"

        def operation() -> dict[str, Any]:
            root = self._root()
            athanor = Athanor(root)
            state = athanor.replay()
            active = ProjectContext(root).active_program()
            program = state["programs"].get(active) if active else None
            critical = sorted(
                issue["issue_id"]
                for issue in state["issues"].values()
                if issue["status"] == "OPEN"
                and issue["severity"] == "CRITICAL"
                and (active is None or issue["program_id"] == active)
            )
            return success(
                tool,
                {
                    "project_root": ".",
                    "active_program_id": active,
                    "stage": program["status"] if program else None,
                    "program_count": len(state["programs"]),
                    "open_critical_issue_ids": critical,
                    "chronicle_head_sigil": self._head(athanor),
                },
                next_actions=self._next_actions(state, active),
            )

        return self._run(tool, operation)

    def benchwork_list_programs(
        self,
        cursor: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List Research Programs with stable ordering and cursor pagination."""
        tool = "benchwork_list_programs"

        def operation() -> dict[str, Any]:
            programs = self._athanor().programs()
            return success(
                tool,
                page(
                    (programs[key] for key in sorted(programs)),
                    cursor=cursor,
                    limit=limit,
                ),
            )

        return self._run(tool, operation)

    def benchwork_get_program(self, program_id: str) -> dict[str, Any]:
        """Read one Program and its canonical object inventory."""
        tool = "benchwork_get_program"

        def operation() -> dict[str, Any]:
            state = self._athanor().replay()
            if program_id not in state["programs"]:
                raise AthanorError(f"unknown Research Program: {program_id}")
            return success(
                tool,
                {
                    "program": state["programs"][program_id],
                    "objects": self._program_objects(state, program_id),
                },
                next_actions=self._next_actions(state, program_id),
            )

        return self._run(tool, operation)

    def benchwork_get_object(self, object_id: str) -> dict[str, Any]:
        """Read one canonical object by identifier."""
        tool = "benchwork_get_object"

        def operation() -> dict[str, Any]:
            state = self._athanor().replay()
            for collection in COLLECTIONS:
                record = state.get(collection, {}).get(object_id)
                if record is not None:
                    return success(
                        tool,
                        {"collection": collection, "object": record},
                    )
            raise AthanorError(f"unknown object: {object_id}")

        return self._run(tool, operation)

    def benchwork_get_review(self, review_id: str) -> dict[str, Any]:
        """Read a Review Request and its completed Artifact, when present."""
        tool = "benchwork_get_review"

        def operation() -> dict[str, Any]:
            state = self._athanor().replay()
            request = state["review_requests"].get(review_id)
            if request is None:
                raise AthanorError(f"unknown Review Request: {review_id}")
            return success(
                tool,
                {
                    "request": request,
                    "artifact": state["review_artifacts"].get(review_id),
                },
            )

        return self._run(tool, operation)

    def benchwork_trace(
        self,
        object_id: str,
        cursor: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Trace canonical events referencing an object."""
        tool = "benchwork_trace"
        return self._run(
            tool,
            lambda: success(
                tool,
                page(
                    self._athanor().trace(object_id),
                    cursor=cursor,
                    limit=limit,
                ),
            ),
        )

    def _next_actions(
        self,
        state: dict[str, Any],
        program_id: str | None,
    ) -> list[str]:
        if program_id is None:
            return ["Create or select an active Research Program"]
        program = state["programs"].get(program_id)
        if program is None:
            return ["Select an existing Research Program"]
        critical = [
            issue["issue_id"]
            for issue in state["issues"].values()
            if issue["program_id"] == program_id
            and issue["status"] == "OPEN"
            and issue["severity"] == "CRITICAL"
        ]
        if critical:
            return [f"Resolve CRITICAL Issues: {', '.join(sorted(critical))}"]
        if not program["evidence"]:
            return ["Investigate and record inspected Evidence"]
        if program["research_question"] is None:
            return ["Frame Hypotheses, then preview the Research Question Seal"]
        protocols = [
            protocol
            for protocol in state["protocols"].values()
            if protocol["program_id"] == program_id
        ]
        if not protocols:
            return ["Draft a Protocol"]
        if any(protocol["status"] == "DRAFT" for protocol in protocols):
            return ["Review and preview the Protocol Seal"]
        if not any(
            experiment["program_id"] == program_id
            for experiment in state["experiments"].values()
        ):
            return ["Start a Working and create the registered Experiment"]
        if not any(
            bundle["program_id"] == program_id
            for bundle in state["result_bundles"].values()
        ):
            return ["Register all Runs, then invoke Alembic analysis"]
        if not any(
            assessment["program_id"] == program_id
            for assessment in state["assessments"].values()
        ):
            return ["Interpret the Result Bundle and record an Assessment"]
        if not program["decisions"]:
            return ["Preview a scientific Decision for human confirmation"]
        return ["Continue from unresolved Issues and the latest sealed Decision"]

    def benchwork_next_actions(self, program_id: str | None = None) -> dict[str, Any]:
        """Return deterministic next-action guidance from canonical state."""
        tool = "benchwork_next_actions"

        def operation() -> dict[str, Any]:
            root = self._root()
            state = Athanor(root).replay()
            selected = program_id or ProjectContext(root).active_program()
            return success(
                tool,
                {"program_id": selected, "actions": self._next_actions(state, selected)},
            )

        return self._run(tool, operation)

    def benchwork_get_schema(self, schema: str) -> dict[str, Any]:
        """Read a published Benchwork JSON Schema by name or schema version."""
        tool = "benchwork_get_schema"

        def operation() -> dict[str, Any]:
            name = schema.replace("/", "-")
            if not name.endswith(".json"):
                name += ".json"
            if Path(name).name != name:
                raise AthanorError("schema name must not contain a path")
            path = _schema_directory() / name
            if not path.is_file():
                raise AthanorError(f"unknown schema: {schema}")
            document = json.loads(path.read_text(encoding="utf-8"))
            return success(tool, {"name": name, "schema": document})

        return self._run(tool, operation)

    def benchwork_doctor(self, deep: bool = False) -> dict[str, Any]:
        """Verify Chronicle integrity, optionally checking every projection and blob."""
        tool = "benchwork_doctor"

        def operation() -> dict[str, Any]:
            root = self._root()
            if deep:
                report = deep_doctor(root)
                if not report["ok"]:
                    raise AthanorError("Chronicle integrity failure")
                return success(tool, report)
            events = Athanor(root).chronicle.events()
            return success(
                tool,
                {
                    "mode": "standard",
                    "ok": True,
                    "chronicle_verified": True,
                    "event_count": len(events),
                },
            )

        return self._run(tool, operation)

    def benchwork_start_job(
        self,
        execution_specification: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Submit a typed pre-conformance Job without accepting a command or shell.

        This Host-neutral adapter is intentionally absent from the published
        MCP registry until RFC-0012 through RFC-0015 schemas and conformance
        requirements are implemented.
        """
        return self._execution_run(
            "benchwork_start_job",
            lambda: self._execution().start(execution_specification, idempotency_key),
        )

    def benchwork_observe_job(
        self,
        job_id: str,
        limit: int = 50,
        cursor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Read a bounded, fixed-prefix operational Job observation."""
        return self._execution_run(
            "benchwork_observe_job",
            lambda: self._execution().observe(job_id, limit=limit, cursor=cursor),
        )

    def benchwork_cancel_job(
        self,
        job_id: str,
        job_binding_sigil: str,
        expected_job_revision: int,
        idempotency_key: str,
        reason: str,
    ) -> dict[str, Any]:
        """Record an idempotent stop request; no request is a process signal."""
        return self._execution_run(
            "benchwork_cancel_job",
            lambda: self._execution().cancel(
                job_id,
                job_binding_sigil,
                expected_job_revision,
                idempotency_key,
                reason,
            ),
        )

    def benchwork_get_job_result(self, job_id: str) -> dict[str, Any]:
        """Derive a terminal operational Outcome without canonical acceptance."""
        return self._execution_run(
            "benchwork_get_job_result",
            lambda: self._execution().get_outcome(job_id),
        )

    def benchwork_accept_job_result(
        self,
        job_id: str,
        execution_job_outcome_sigil: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Fail closed until an Outcome has complete Agent Result v2 evidence."""
        def operation() -> dict[str, Any]:
            if not isinstance(idempotency_key, str) or not idempotency_key:
                raise AthanorError("execution acceptance idempotency key is invalid")
            outcome = self._execution().get_outcome(job_id)
            if execution_job_outcome_sigil != outcome["outcome_sigil"]:
                raise AthanorError("execution Outcome is ineligible")
            if not outcome["eligible_for_acceptance"]:
                raise AthanorError("execution Outcome is ineligible")
            raise AthanorError("execution Outcome is ineligible")

        return self._execution_run("benchwork_accept_job_result", operation)

    def benchwork_open_task(
        self,
        capability: str,
        program_id: str,
        objective: str,
        tools: list[str] | None = None,
        time_budget_seconds: int | None = None,
        network: bool | None = None,
        approval_reason: str | None = None,
        review_id: str | None = None,
        host_session: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Open a bounded Host Task Capsule and evaluate it through Ward."""
        tool = "benchwork_open_task"

        def operation() -> dict[str, Any]:
            root = self._root()
            athanor = Athanor(root)
            registry = CapabilityRegistry(root)
            contract = registry.get(capability)
            bindings = None
            if capability in {
                "bench.review.local",
                "bench.review.external",
                "bench.review.accept",
            }:
                if review_id is None:
                    raise AthanorError(f"{capability} requires a Review Request ID")
                state = athanor.replay()
                request = state["review_requests"].get(review_id)
                artifact = state["review_artifacts"].get(review_id)
                if request is None:
                    raise AthanorError(f"unknown Review Request: {review_id}")
                if capability == "bench.review.local" and (
                    request["type"] != "local_review"
                    or request["status"] != "PREPARED"
                ):
                    raise AthanorError(
                        f"Local Review Request is not prepared: {review_id}"
                    )
                if capability == "bench.review.external" and (
                    request["type"] != "external_diff_review"
                    or request["status"] != "APPROVED"
                    or request["approval"]["status"] != "APPROVED"
                ):
                    raise AthanorError(
                        f"Review is waiting for disclosure authorization: {review_id}"
                    )
                if capability == "bench.review.accept" and (
                    artifact is None or artifact["status"] != "COMPLETED"
                ):
                    raise AthanorError(
                        f"Review is not awaiting acceptance: {review_id}"
                    )
                bindings = {"review_id": review_id}
            capsule = TaskService(
                athanor,
                registry,
                CapsuleStore(root),
            ).create(
                capability,
                program_id,
                objective,
                {
                    "tools": tools if tools is not None else contract["allowed_tools"],
                    "time_budget_seconds": (
                        time_budget_seconds
                        if time_budget_seconds is not None
                        else contract["max_time_seconds"]
                    ),
                    "network": network if network is not None else contract["network"],
                },
                host=self._acting_host(host_session),
                bindings=bindings,
            )
            receipt = None
            if approval_reason is not None:
                receipt = athanor.grant_approval(capsule, approval_reason)
            ward = Ward(registry, athanor.approvals()).evaluate(capsule)
            return success(
                tool,
                {"task": capsule, "ward": ward.as_dict()},
                receipt=receipt,
                next_actions=(
                    ["Obtain explicit user approval before completing this Task"]
                    if ward.status == "WAITING_FOR_APPROVAL"
                    else ["Use native tools, then submit structured Task output"]
                ),
            )

        return self._run(tool, operation)

    def benchwork_get_task(self, task_id: str) -> dict[str, Any]:
        """Read a Task Capsule, Ward status, and accepted Agent Result if present."""
        tool = "benchwork_get_task"

        def operation() -> dict[str, Any]:
            root = self._root()
            athanor = Athanor(root)
            registry = CapabilityRegistry(root)
            capsule = CapsuleStore(root).get(task_id)
            return success(
                tool,
                {
                    "task": capsule,
                    "ward": Ward(registry, athanor.approvals()).evaluate(capsule).as_dict(),
                    "result": athanor.agent_results().get(task_id),
                },
            )

        return self._run(tool, operation)

    @staticmethod
    def _acting_host(host_session: dict[str, Any] | None) -> str:
        """Resolve the Host driving a Task, defaulting to the primary CLI Host."""
        if host_session is None:
            return DEFAULT_HOST
        validate_instance("host-session-provenance-1.0.json", host_session)
        host = str(host_session["host"])
        if host not in HOSTS:
            raise AthanorError(f"unknown Task Host: {host}")
        return host

    @staticmethod
    def _agent_provenance(host_session: dict[str, Any] | None) -> dict[str, str]:
        if host_session is None:
            return {"host": DEFAULT_HOST, "runtime": "interactive-session"}
        validate_instance("host-session-provenance-1.0.json", host_session)
        provenance = {
            "host": host_session["host"],
            "invocation_id": host_session["session_id"],
        }
        for key in ("provider", "model", "runtime"):
            if key in host_session:
                provenance[key] = host_session[key]
        return provenance

    def benchwork_complete_task(
        self,
        task_id: str,
        summary: str,
        output: dict[str, Any],
        host_session: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate structured semantic output, build its blob, and accept the Task."""
        tool = "benchwork_complete_task"

        def operation() -> dict[str, Any]:
            root = self._root()
            athanor = Athanor(root)
            capsule = CapsuleStore(root).get(task_id)
            expected = capsule["expected_outputs"]
            if len(expected) != 1:
                raise AthanorError("MCP Task completion currently requires one expected output")
            schema_version = expected[0]["schema"]
            if output.get("schema_version") is not None:
                document = output
            else:
                document = {
                    "schema_version": schema_version,
                    "task_id": task_id,
                    "summary": summary,
                    "data": output,
                }
            if document.get("task_id") != task_id:
                raise AthanorError("Task output Task ID does not match the Task Capsule")
            schema_name = schema_version.replace("/", "-") + ".json"
            validate_instance(schema_name, document)
            blob = (
                json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
            ).encode()
            blob_sigil = "sha256:" + hashlib.sha256(blob).hexdigest()
            relative = Path(".benchwork") / "mcp" / "task-results" / (
                f"{task_id}-{blob_sigil.removeprefix('sha256:')[:12]}.json"
            )
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(blob)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
            result = {
                "schema_version": "agent-result/1.1",
                "task_id": task_id,
                "snapshot_sigil": capsule["snapshot"]["snapshot_sigil"],
                "capability_contract_sigil": capsule["capability"]["contract_sigil"],
                "status": "COMPLETED",
                "outputs": [
                    {
                        "schema": schema_version,
                        "uri": relative.as_posix(),
                        "blob_sigil": blob_sigil,
                    }
                ],
                "provenance": self._agent_provenance(host_session),
            }
            receipt = athanor.accept_agent_result(result)
            return success(
                tool,
                {"task_id": task_id, "status": "COMPLETED", "outputs": result["outputs"]},
                receipt=receipt,
            )

        return self._run(tool, operation)

    def benchwork_fail_task(
        self,
        task_id: str,
        reason: str,
        host_session: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Accept a failed Task outcome without erasing the Task Capsule."""
        tool = "benchwork_fail_task"

        def operation() -> dict[str, Any]:
            if not reason.strip():
                raise AthanorError("Task failure reason cannot be empty")
            athanor = self._athanor()
            capsule = CapsuleStore(self._root()).get(task_id)
            result = {
                "schema_version": "agent-result/1.1",
                "task_id": task_id,
                "snapshot_sigil": capsule["snapshot"]["snapshot_sigil"],
                "capability_contract_sigil": capsule["capability"]["contract_sigil"],
                "status": "FAILED",
                "outputs": [],
                "provenance": self._agent_provenance(host_session),
            }
            receipt = athanor.accept_agent_result(result)
            return success(
                tool,
                {"task_id": task_id, "status": "FAILED", "reason": reason},
                receipt=receipt,
                warnings=["The canonical Agent Result records FAILED; the reason is advisory."],
            )

        return self._run(tool, operation)

    def benchwork_create_program(
        self,
        slug: str,
        title: str,
        problem: dict[str, Any] | None = None,
        activate: bool = False,
    ) -> dict[str, Any]:
        """Create a Research Program through Athanor."""
        tool = "benchwork_create_program"

        def operation() -> dict[str, Any]:
            root = self._root()
            program_id, receipt = Athanor(root).create_program(slug, title, problem)
            if activate:
                ProjectContext(root).use_program(program_id)
            return success(tool, {"program_id": program_id, "active": activate}, receipt=receipt)

        return self._run(tool, operation)

    def benchwork_record_evidence(
        self,
        evidence_id: str,
        program_id: str,
        source_uri: str,
        source_sigil: str,
        observation: str,
        source_resolved: bool = False,
        content_inspected: bool = False,
    ) -> dict[str, Any]:
        """Record content-addressed Evidence after native source inspection."""
        tool = "benchwork_record_evidence"
        return self._run(
            tool,
            lambda: success(
                tool,
                {"evidence_id": evidence_id},
                receipt=self._athanor().record_evidence(
                    evidence_id,
                    program_id,
                    {"uri": source_uri, "sigil": source_sigil},
                    observation,
                    {
                        "source_resolved": source_resolved,
                        "content_inspected": content_inspected,
                    },
                ),
            ),
        )

    def benchwork_verify_evidence(
        self,
        evidence_id: str,
        checks: list[str],
    ) -> dict[str, Any]:
        """Record completed Evidence source verification checks."""
        tool = "benchwork_verify_evidence"
        return self._run(
            tool,
            lambda: success(
                tool,
                {"evidence_id": evidence_id, "checks": checks},
                receipt=self._athanor().verify_evidence(evidence_id, checks),
            ),
        )

    def benchwork_create_claim(
        self,
        claim_id: str,
        program_id: str,
        claim_type: str,
        statement: str,
        evidence_relations: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Create a typed Claim and proposed Evidence relations."""
        tool = "benchwork_create_claim"
        return self._run(
            tool,
            lambda: success(
                tool,
                {"claim_id": claim_id},
                receipt=self._athanor().create_claim(
                    claim_id,
                    program_id,
                    claim_type,
                    statement,
                    evidence_relations,
                ),
            ),
        )

    def benchwork_verify_claim_relation(
        self,
        claim_id: str,
        evidence_id: str,
    ) -> dict[str, Any]:
        """Verify one proposed Claim-Evidence relation."""
        tool = "benchwork_verify_claim_relation"
        return self._run(
            tool,
            lambda: success(
                tool,
                {"claim_id": claim_id, "evidence_id": evidence_id},
                receipt=self._athanor().verify_claim_relation(claim_id, evidence_id),
            ),
        )

    def benchwork_create_hypothesis(
        self,
        hypothesis_id: str,
        program_id: str,
        claim_ids: list[str],
        statement: str,
        prediction: str,
    ) -> dict[str, Any]:
        """Create a Claim-backed falsifiable Hypothesis."""
        tool = "benchwork_create_hypothesis"
        return self._run(
            tool,
            lambda: success(
                tool,
                {"hypothesis_id": hypothesis_id},
                receipt=self._athanor().create_hypothesis(
                    hypothesis_id,
                    program_id,
                    claim_ids,
                    statement,
                    prediction,
                ),
            ),
        )

    def benchwork_draft_protocol(
        self,
        protocol_id: str,
        program_id: str,
        title: str,
        analysis_plan: str,
        hypothesis_ids: list[str] | None = None,
        study_mode: str | None = None,
        analysis_spec: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Draft an unsealed Protocol through Athanor."""
        tool = "benchwork_draft_protocol"
        return self._run(
            tool,
            lambda: success(
                tool,
                {"protocol_id": protocol_id, "status": "DRAFT"},
                receipt=self._athanor().draft_protocol(
                    protocol_id,
                    program_id,
                    title,
                    analysis_plan,
                    hypothesis_ids,
                    study_mode,
                    analysis_spec,
                ),
                next_actions=["Review the draft and create a Protocol Seal preview"],
            ),
        )

    def benchwork_open_issue(
        self,
        issue_id: str,
        program_id: str,
        subject_ids: list[str],
        severity: str,
        title: str,
        description: str,
    ) -> dict[str, Any]:
        """Open a canonical, traceable research Issue."""
        tool = "benchwork_open_issue"
        return self._run(
            tool,
            lambda: success(
                tool,
                {"issue_id": issue_id, "status": "OPEN"},
                receipt=self._athanor().open_issue(
                    issue_id,
                    program_id,
                    subject_ids,
                    severity,
                    title,
                    description,
                ),
            ),
        )

    def benchwork_record_assessment(
        self,
        result_bundle_id: str,
        summary: str,
        limitations: list[str],
        claim_findings: list[dict[str, str]],
        hypothesis_findings: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Record a scientific Assessment of an Alembic Result Bundle."""
        tool = "benchwork_record_assessment"

        def operation() -> dict[str, Any]:
            assessment_id, receipt = self._athanor().review_result(
                result_bundle_id,
                summary,
                limitations,
                claim_findings,
                hypothesis_findings,
            )
            return success(tool, {"assessment_id": assessment_id}, receipt=receipt)

        return self._run(tool, operation)

    def benchwork_prepare_review(
        self,
        review_id: str,
        program_id: str,
        review_type: str,
        target: dict[str, Any],
        scope: dict[str, Any],
        disclosure: dict[str, Any],
        destination: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare a local or external Review Request without invoking a reviewer."""
        tool = "benchwork_prepare_review"

        def operation() -> dict[str, Any]:
            receipt = self._athanor().prepare_review(
                review_id,
                program_id,
                review_type,
                target,
                scope,
                disclosure,
                destination,
            )
            request = self._athanor().review_requests()[review_id]
            external = review_type == "external_diff_review"
            return success(
                tool,
                {"review": request},
                receipt=receipt,
                warnings=(
                    [
                        "No repository content has been disclosed. "
                        "Explicit disclosure authorization is still required."
                    ]
                    if external
                    else []
                ),
                next_actions=(
                    ["Request explicit disclosure authorization for this Review Request"]
                    if external
                    else ["Open a bench.review.local Task and perform a read-only local review"]
                ),
            )

        return self._run(tool, operation)

    def benchwork_approve_external_review(
        self,
        review_id: str,
        approved_by: str,
        rationale: str,
    ) -> dict[str, Any]:
        """Record explicit human disclosure approval for one external Review Request."""
        tool = "benchwork_approve_external_review"
        actor = {
            "actor_id": approved_by,
            "actor_type": "human",
            "host": "codex",
            "authenticated_by": "codex-explicit-disclosure-confirmation",
        }

        def operation() -> dict[str, Any]:
            receipt = self._athanor().approve_external_review(
                review_id,
                approved_by,
                rationale,
                actor=actor,
            )
            return success(
                tool,
                {"review": self._athanor().review_requests()[review_id]},
                receipt=receipt,
                next_actions=[
                    "Open the Ward-gated bench.review.external Task before disclosure"
                ],
            )

        return self._run(tool, operation)

    def benchwork_record_review(
        self,
        review_id: str,
        task_id: str,
        reviewer_kind: str,
        reviewer_name: str,
        summary: str,
        findings: list[str],
        residual_risks: list[str],
        recommendation: str,
        host: str = "codex",
    ) -> dict[str, Any]:
        """Record a completed Review; this tool never invokes the reviewer."""
        tool = "benchwork_record_review"

        def operation() -> dict[str, Any]:
            receipt = self._athanor().record_review(
                review_id,
                task_id,
                {"kind": reviewer_kind, "name": reviewer_name},
                {
                    "summary": summary,
                    "findings": findings,
                    "residual_risks": residual_risks,
                    "recommendation": recommendation,
                },
                host,
            )
            return success(
                tool,
                {"review": self._athanor().review_artifacts()[review_id]},
                receipt=receipt,
                warnings=["A completed Review remains advisory until explicitly accepted."],
                next_actions=["Request human acceptance of the Review Artifact"],
            )

        return self._run(tool, operation)

    def benchwork_accept_review(
        self,
        review_id: str,
        rationale: str,
        accepted_by: str,
    ) -> dict[str, Any]:
        """Accept a completed Review Artifact with an explicit human actor."""
        tool = "benchwork_accept_review"
        actor = {
            "actor_id": accepted_by,
            "actor_type": "human",
            "host": "codex",
            "authenticated_by": "codex-explicit-review-acceptance",
        }

        def operation() -> dict[str, Any]:
            receipt = self._athanor().accept_review(
                review_id,
                rationale,
                actor=actor,
            )
            return success(
                tool,
                {"review": self._athanor().review_artifacts()[review_id]},
                receipt=receipt,
            )

        return self._run(tool, operation)

    def _preview_path(self, preview_id: str) -> Path:
        return self._root() / ".benchwork" / "mcp" / "previews" / f"{preview_id}.json"

    @staticmethod
    def _apply_seal(
        athanor: Athanor,
        operation: str,
        arguments: dict[str, Any],
    ) -> tuple[str, Any]:
        if operation == "rq_seal":
            receipt = athanor.seal_research_question(
                arguments["program_id"],
                arguments["statement"],
                actor=CODEX_HUMAN_ACTOR,
            )
            return arguments["program_id"], receipt
        if operation == "protocol_seal":
            receipt = athanor.seal_protocol(
                arguments["protocol_id"],
                actor=CODEX_HUMAN_ACTOR,
            )
            return arguments["protocol_id"], receipt
        if operation == "decision_seal":
            decision_id, receipt = athanor.seal_decision(
                arguments["program_id"],
                arguments["outcome"],
                arguments["assessment_ids"],
                arguments["rationale"],
                arguments.get("required_actions"),
                arguments.get("lineage"),
                actor=CODEX_HUMAN_ACTOR,
            )
            return decision_id, receipt
        raise AthanorError(f"unknown preview operation: {operation}")

    def _create_preview(
        self,
        tool: str,
        operation_name: str,
        target_id: str,
        arguments: dict[str, Any],
        changed_fields: list[str],
    ) -> dict[str, Any]:
        root = self._root()
        athanor = Athanor(root)
        with tempfile.TemporaryDirectory(prefix="benchwork-preview-") as directory:
            preview_root = Path(directory) / "project"
            preview_root.mkdir()
            shutil.copytree(root / ".benchwork", preview_root / ".benchwork")
            self._apply_seal(Athanor(preview_root), operation_name, arguments)
        operation_sigil = content_sigil(
            {
                "operation": operation_name,
                "target_id": target_id,
                "arguments": arguments,
            }
        )
        preview_id = f"PV-{uuid4().hex[:16].upper()}"
        confirmation = (
            f"CONFIRM {operation_name.upper()} {target_id} "
            f"{operation_sigil.removeprefix('sha256:')[:12]}"
        )
        preview = {
            "schema_version": "operation-preview/1.0",
            "preview_id": preview_id,
            "operation": operation_name,
            "target_id": target_id,
            "arguments": arguments,
            "chronicle_head_sigil": self._head(athanor),
            "content_sigil": operation_sigil,
            "changed_fields": changed_fields,
            "gate": {"status": "PASS", "checks": ["Athanor dry-run accepted"]},
            "required_approval": {
                "kind": "explicit-human-confirmation",
                "confirmation_token": confirmation,
            },
        }
        preview["preview_sigil"] = content_sigil(preview)
        validate_instance("operation-preview-1.0.json", preview)
        _atomic_json(self._preview_path(preview_id), preview)
        return success(
            tool,
            preview,
            next_actions=[
                "Show the preview to the user and ask for explicit confirmation",
                "Commit only with the exact confirmation token after the user confirms",
            ],
        )

    def benchwork_preview_rq_seal(
        self,
        program_id: str,
        statement: str,
    ) -> dict[str, Any]:
        """Validate and persist an immutable Research Question Seal preview."""
        tool = "benchwork_preview_rq_seal"
        return self._run(
            tool,
            lambda: self._create_preview(
                tool,
                "rq_seal",
                program_id,
                {"program_id": program_id, "statement": statement},
                ["research_question", "status"],
            ),
        )

    def benchwork_preview_protocol_seal(self, protocol_id: str) -> dict[str, Any]:
        """Validate and persist an immutable Protocol Seal preview."""
        tool = "benchwork_preview_protocol_seal"
        return self._run(
            tool,
            lambda: self._create_preview(
                tool,
                "protocol_seal",
                protocol_id,
                {"protocol_id": protocol_id},
                ["status"],
            ),
        )

    def benchwork_preview_decision_seal(
        self,
        program_id: str,
        outcome: str,
        assessment_ids: list[str],
        rationale: str,
        required_actions: list[str] | None = None,
        lineage: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Validate and persist an immutable scientific Decision preview."""
        tool = "benchwork_preview_decision_seal"
        arguments: dict[str, Any] = {
            "program_id": program_id,
            "outcome": outcome,
            "assessment_ids": assessment_ids,
            "rationale": rationale,
        }
        if required_actions is not None:
            arguments["required_actions"] = required_actions
        if lineage is not None:
            arguments["lineage"] = lineage
        return self._run(
            tool,
            lambda: self._create_preview(
                tool,
                "decision_seal",
                program_id,
                arguments,
                ["decisions", "status"],
            ),
        )

    def _commit_preview(
        self,
        tool: str,
        expected_operation: str,
        preview_id: str,
        preview_sigil: str,
        idempotency_key: str,
        confirmation_token: str,
    ) -> dict[str, Any]:
        request = {
            "schema_version": "operation-commit/1.0",
            "preview_id": preview_id,
            "preview_sigil": preview_sigil,
            "idempotency_key": idempotency_key,
            "confirmation_token": confirmation_token,
        }
        validate_instance("operation-commit-1.0.json", request)
        path = self._preview_path(preview_id)
        try:
            preview = json.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise AthanorError(f"unknown operation preview: {preview_id}") from error
        validate_instance("operation-preview-1.0.json", preview)
        if preview["operation"] != expected_operation:
            raise AthanorError("operation preview type does not match commit tool")
        if preview["preview_sigil"] != preview_sigil or content_sigil(
            {key: value for key, value in preview.items() if key != "preview_sigil"}
        ) != preview_sigil:
            raise AthanorError("operation preview Sigil mismatch")
        if confirmation_token != preview["required_approval"]["confirmation_token"]:
            raise AthanorError("INVALID_CONFIRMATION: confirmation token does not match preview")
        root = self._root()
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        idempotency_path = root / ".benchwork" / "mcp" / "idempotency" / f"{key_hash}.json"
        lock_path = root / ".benchwork" / "mcp" / "commit.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(lock_path):
            if idempotency_path.is_file():
                previous = json.loads(idempotency_path.read_text(encoding="utf-8"))
                if previous["preview_sigil"] != preview_sigil:
                    raise AthanorError("idempotency key was already used for another preview")
                return success(
                    tool,
                    previous["data"],
                    receipt=previous["receipt"],
                    warnings=["Idempotent replay returned the original commit Receipt."],
                )
            athanor = Athanor(root)
            if self._head(athanor) != preview["chronicle_head_sigil"]:
                raise AthanorError(
                    "STALE_PREVIEW: Canonical state changed after preview creation"
                )
            object_id, receipt = self._apply_seal(
                athanor,
                expected_operation,
                preview["arguments"],
            )
            data = {
                "preview_id": preview_id,
                "operation": expected_operation,
                "object_id": object_id,
                "content_sigil": preview["content_sigil"],
            }
            _atomic_json(
                idempotency_path,
                {
                    "schema_version": "operation-commit/1.0",
                    "idempotency_key_sigil": f"sha256:{key_hash}",
                    "preview_sigil": preview_sigil,
                    "data": data,
                    "receipt": receipt.as_dict(),
                },
            )
            return success(tool, data, receipt=receipt)

    def benchwork_commit_rq_seal(
        self,
        preview_id: str,
        preview_sigil: str,
        idempotency_key: str,
        confirmation_token: str,
    ) -> dict[str, Any]:
        """Commit a confirmed, fresh Research Question Seal preview."""
        tool = "benchwork_commit_rq_seal"
        return self._run(
            tool,
            lambda: self._commit_preview(
                tool,
                "rq_seal",
                preview_id,
                preview_sigil,
                idempotency_key,
                confirmation_token,
            ),
            stale_preview_action=True,
        )

    def benchwork_commit_protocol_seal(
        self,
        preview_id: str,
        preview_sigil: str,
        idempotency_key: str,
        confirmation_token: str,
    ) -> dict[str, Any]:
        """Commit a confirmed, fresh Protocol Seal preview."""
        tool = "benchwork_commit_protocol_seal"
        return self._run(
            tool,
            lambda: self._commit_preview(
                tool,
                "protocol_seal",
                preview_id,
                preview_sigil,
                idempotency_key,
                confirmation_token,
            ),
            stale_preview_action=True,
        )

    def benchwork_commit_decision_seal(
        self,
        preview_id: str,
        preview_sigil: str,
        idempotency_key: str,
        confirmation_token: str,
    ) -> dict[str, Any]:
        """Commit a confirmed, fresh scientific Decision preview."""
        tool = "benchwork_commit_decision_seal"
        return self._run(
            tool,
            lambda: self._commit_preview(
                tool,
                "decision_seal",
                preview_id,
                preview_sigil,
                idempotency_key,
                confirmation_token,
            ),
            stale_preview_action=True,
        )

    def benchwork_start_working(
        self,
        rite_id: str,
        program_id: str,
        protocol_id: str,
    ) -> dict[str, Any]:
        """Start a sealed-Protocol Working from an installed Rite."""
        tool = "benchwork_start_working"

        def operation() -> dict[str, Any]:
            working_id, receipt = self._athanor().create_working(
                rite_id,
                program_id,
                protocol_id,
            )
            return success(tool, {"working_id": working_id}, receipt=receipt)

        return self._run(tool, operation)

    def benchwork_register_artifact(
        self,
        artifact_id: str,
        program_id: str,
        kind: str,
        uri: str,
        sigil: str,
        producer_id: str,
        input_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Register a project-relative, content-addressed implementation artifact."""
        tool = "benchwork_register_artifact"
        return self._run(
            tool,
            lambda: success(
                tool,
                {"artifact_id": artifact_id},
                receipt=self._athanor().register_artifact(
                    artifact_id,
                    program_id,
                    kind,
                    {"uri": uri, "sigil": sigil},
                    producer_id,
                    input_ids,
                ),
            ),
        )

    def benchwork_create_experiment(
        self,
        experiment_id: str,
        program_id: str,
        protocol_id: str,
        question: str,
        hypothesis_id: str | None = None,
        working_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a Protocol-bound Experiment."""
        tool = "benchwork_create_experiment"
        return self._run(
            tool,
            lambda: success(
                tool,
                {"experiment_id": experiment_id},
                receipt=self._athanor().create_experiment(
                    experiment_id,
                    program_id,
                    protocol_id,
                    question,
                    hypothesis_id,
                    working_id,
                ),
            ),
        )

    def benchwork_transition_experiment(
        self,
        experiment_id: str,
        transition: str,
    ) -> dict[str, Any]:
        """Apply one validated monotonic Experiment transition."""
        tool = "benchwork_transition_experiment"
        return self._run(
            tool,
            lambda: success(
                tool,
                {"experiment_id": experiment_id, "transition": transition},
                receipt=self._athanor().transition_experiment(experiment_id, transition),
            ),
        )

    def benchwork_record_run(
        self,
        run_id: str,
        experiment_id: str,
        status: str,
        analysis_included: bool,
        metrics: dict[str, float],
        seed: int | None = None,
        artifacts: list[dict[str, str]] | None = None,
        phase: str = "FORMAL",
        exclusion_reason: str | None = None,
        policy_reference: str | None = None,
        arm: str | None = None,
    ) -> dict[str, Any]:
        """Record every completed, failed, cancelled, or negative experimental Run."""
        tool = "benchwork_record_run"
        return self._run(
            tool,
            lambda: success(
                tool,
                {"run_id": run_id, "status": status},
                receipt=self._athanor().record_run(
                    run_id,
                    experiment_id,
                    status,
                    analysis_included,
                    metrics,
                    seed,
                    artifacts,
                    phase,
                    exclusion_reason,
                    policy_reference,
                    arm,
                ),
            ),
        )

    def benchwork_compute_analysis(
        self,
        program_id: str,
        protocol_id: str,
    ) -> dict[str, Any]:
        """Invoke deterministic Alembic analysis; do not substitute hand calculations."""
        tool = "benchwork_compute_analysis"

        def operation() -> dict[str, Any]:
            bundle, bundle_sigil, receipt, path = self._athanor().compute_analysis(
                program_id,
                protocol_id,
            )
            relative = path.resolve().relative_to(self._root()).as_posix()
            return success(
                tool,
                {
                    "result_bundle": bundle,
                    "bundle_sigil": bundle_sigil,
                    "artifact_uri": relative,
                },
                receipt=receipt,
            )

        return self._run(tool, operation)
