"""Deep integrity diagnostics across canonical and file-backed project state."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .athanor import Athanor, AthanorError, content_sigil
from .circle import CapsuleStore, CapabilityRegistry
from .project import ProjectContext
from .rites import RiteRegistry
from .schema_validation import validate_instance
from .snapshots import SnapshotStore


def _project_path(root: Path, uri: str, label: str) -> Path:
    path = (root / uri).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise AthanorError(f"{label} escapes the project: {uri}") from error
    if not path.is_file():
        raise AthanorError(f"{label} is missing: {uri}")
    return path


def _blob_sigil(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def deep_doctor(root: Path) -> dict[str, Any]:
    athanor = Athanor(root)
    registry = CapabilityRegistry(root)
    rites = RiteRegistry(root)
    capsules = CapsuleStore(root)
    snapshots = SnapshotStore(root)
    context = ProjectContext(root)
    checks: dict[str, dict[str, Any]] = {}
    events: list[dict[str, Any]] | None = None
    state: dict[str, Any] | None = None

    def check(name: str, operation: Callable[[], dict[str, Any]]) -> None:
        try:
            checks[name] = {"status": "PASS", **operation()}
        except (ValueError, OSError, json.JSONDecodeError) as error:
            checks[name] = {"status": "FAIL", "message": str(error)}

    def verify_chronicle() -> dict[str, Any]:
        nonlocal events
        events = athanor.chronicle.events()
        return {"event_count": len(events)}

    def verify_projection() -> dict[str, Any]:
        nonlocal state
        if events is None:
            raise AthanorError("Chronicle verification did not produce events")
        state = athanor._project(events)
        object_count = sum(
            len(collection)
            for collection in state.values()
            if isinstance(collection, dict)
        )
        return {"object_count": object_count}

    def verify_snapshots() -> dict[str, Any]:
        snapshot_paths = sorted(snapshots.path.glob("*.json")) if snapshots.path.exists() else []
        verified: dict[str, str] = {}
        for path in snapshot_paths:
            snapshot_id = path.stem
            _, sigil = snapshots.get(snapshot_id)
            verified[snapshot_id] = sigil
        return {"verified_count": len(verified)}

    def verify_capsules() -> dict[str, Any]:
        capsule_paths = sorted(capsules.path.glob("*.json")) if capsules.path.exists() else []
        for path in capsule_paths:
            capsule = capsules.get(path.stem)
            snapshots.get(
                capsule["snapshot"]["snapshot_id"],
                capsule["snapshot"]["snapshot_sigil"],
            )
        return {"verified_count": len(capsule_paths)}

    def verify_capabilities() -> dict[str, Any]:
        capabilities = registry.verify_existing()
        return {"verified_count": len(capabilities)}

    def verify_rites() -> dict[str, Any]:
        definitions = rites.verify_existing()
        return {"verified_count": len(definitions)}

    def verify_grimoires() -> dict[str, Any]:
        installed = rites.grimoire_registry.verify_existing()
        return {"verified_count": len(installed)}

    def verify_agent_outputs() -> dict[str, Any]:
        if state is None:
            raise AthanorError("Projection is unavailable")
        output_count = 0
        for task_id, record in state["agent_results"].items():
            if record["schema_version"] != "agent-result-record/1.1":
                continue
            capsule = capsules.get(task_id)
            if record["capsule_sigil"] != capsule["capsule_sigil"]:
                raise AthanorError(f"accepted Agent Result Capsule mismatch: {task_id}")
            for output in record["outputs"]:
                path = _project_path(root, output["uri"], "Agent Result output")
                if _blob_sigil(path) != output["blob_sigil"]:
                    raise AthanorError(
                        f"Agent Result output Blob Sigil mismatch: {output['uri']}"
                    )
                document = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(document, dict):
                    raise AthanorError(
                        f"Agent Result output must be an object: {output['uri']}"
                    )
                validate_instance(output["schema"].replace("/", "-") + ".json", document)
                if document.get("task_id") != task_id:
                    raise AthanorError(
                        f"Agent Result output Task ID mismatch: {output['uri']}"
                    )
                output_count += 1
        return {"verified_count": output_count}

    def verify_artifacts() -> dict[str, Any]:
        if state is None:
            raise AthanorError("Projection is unavailable")
        for artifact in state["artifacts"].values():
            location = artifact["location"]
            path = _project_path(root, location["uri"], "Artifact Blob")
            if _blob_sigil(path) != location["sigil"]:
                raise AthanorError(
                    f"Artifact Blob Sigil mismatch: {artifact['artifact_id']}"
                )
        return {"verified_count": len(state["artifacts"])}

    def verify_result_exports() -> dict[str, Any]:
        if state is None:
            raise AthanorError("Projection is unavailable")
        for bundle_id, bundle in state["result_bundles"].items():
            relative = f".benchwork/results/{bundle_id}.json"
            path = _project_path(root, relative, "Result Bundle export")
            try:
                exported = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                raise AthanorError(f"invalid Result Bundle export: {bundle_id}") from error
            if exported != bundle or content_sigil(exported) != content_sigil(bundle):
                raise AthanorError(f"Result Bundle export mismatch: {bundle_id}")
        return {"verified_count": len(state["result_bundles"])}

    def verify_context() -> dict[str, Any]:
        active_program = context.active_program()
        if active_program is not None and (
            state is None or active_program not in state["programs"]
        ):
            raise AthanorError(
                f"Project Context references an unknown Program: {active_program}"
            )
        return {"active_program_id": active_program}

    def verify_migration_state() -> dict[str, Any]:
        residuals = []
        if athanor.chronicle.migration_path.exists():
            residuals.append(athanor.chronicle.migration_path.name)
        residuals.extend(
            path.name for path in root.joinpath(".benchwork").glob("*.migration.tmp")
        )
        if residuals:
            raise AthanorError(
                "unfinished Chronicle migration state: " + ", ".join(sorted(residuals))
            )
        return {"residual_count": 0}

    check("chronicle", verify_chronicle)
    check("projection", verify_projection)
    check("snapshots", verify_snapshots)
    check("capsules", verify_capsules)
    check("capability_registry", verify_capabilities)
    check("rite_registry", verify_rites)
    check("grimoire_registry", verify_grimoires)
    check("agent_outputs", verify_agent_outputs)
    check("artifacts", verify_artifacts)
    check("result_exports", verify_result_exports)
    check("project_context", verify_context)
    check("migration_state", verify_migration_state)
    ok = all(result["status"] == "PASS" for result in checks.values())
    return {
        "schema_version": "doctor-report/1.1",
        "mode": "deep",
        "ok": ok,
        "chronicle_verified": checks["chronicle"]["status"] == "PASS",
        "all_objects_replayable": checks["projection"]["status"] == "PASS",
        "checks": checks,
    }
