"""Shared, deterministic product guidance over canonical research state."""

from __future__ import annotations

from typing import Any


def next_step(state: dict[str, Any], program_id: str | None) -> dict[str, Any]:
    """Return one bounded next step for the selected Program."""
    if program_id is None:
        return {
            "program_id": None,
            "action": "START_OR_SELECT_PROGRAM",
            "reason": "No active Research Program is selected.",
            "command": 'bwork start "<research objective>"',
            "attention": [],
        }
    program = state["programs"].get(program_id)
    if program is None:
        return {
            "program_id": program_id,
            "action": "SELECT_PROGRAM",
            "reason": "The selected Research Program does not exist.",
            "command": "bwork program use <PROGRAM-ID>",
            "attention": [],
        }
    if program["status"] == "CLOSED":
        return {
            "program_id": program_id,
            "action": "DONE",
            "reason": "The Research Program is closed.",
            "command": "",
            "attention": [],
        }

    issues = [
        issue
        for issue in state["issues"].values()
        if issue["program_id"] == program_id and issue["status"] == "OPEN"
    ]
    critical = sorted(
        issue["issue_id"] for issue in issues if issue["severity"] == "CRITICAL"
    )
    failed_runs = sorted(
        run["run_id"]
        for run in state["runs"].values()
        if run["program_id"] == program_id and run["status"] != "COMPLETED"
    )
    attention = [
        *([{"kind": "CRITICAL_ISSUES", "object_ids": critical}] if critical else []),
        *([{"kind": "FAILED_OR_INCOMPLETE_RUNS", "object_ids": failed_runs}] if failed_runs else []),
    ]
    if critical:
        return {
            "program_id": program_id,
            "action": "RESOLVE_CRITICAL_ISSUE",
            "reason": "A critical Issue blocks a trustworthy scientific decision.",
            "command": f"bwork issue show {critical[0]}",
            "attention": attention,
        }

    evidence = [
        record for record in state["evidence"].values() if record["program_id"] == program_id
    ]
    if not evidence:
        return {
            "program_id": program_id,
            "action": "INVESTIGATE",
            "reason": "The Program has no recorded Evidence.",
            "command": f"bwork investigate --program {program_id}",
            "attention": attention,
        }
    unverified = sorted(
        record["evidence_id"]
        for record in evidence
        if not record["verification"]["source_resolved"]
        or not record["verification"]["content_inspected"]
    )
    if unverified:
        return {
            "program_id": program_id,
            "action": "VERIFY_EVIDENCE",
            "reason": "Evidence must be inspected before it can support a Claim.",
            "command": f"bwork evidence show {unverified[0]}",
            "attention": attention,
        }
    if program["research_question"] is None:
        return {
            "program_id": program_id,
            "action": "DESIGN_RESEARCH_QUESTION",
            "reason": "Evidence exists, but the Research Question is not sealed.",
            "command": f"bwork design --program {program_id}",
            "attention": attention,
        }

    protocols = sorted(
        (
            protocol
            for protocol in state["protocols"].values()
            if protocol["program_id"] == program_id
        ),
        key=lambda item: item["protocol_id"],
    )
    if not protocols:
        return {
            "program_id": program_id,
            "action": "DRAFT_PROTOCOL",
            "reason": "The sealed question has no Protocol.",
            "command": "bwork protocol draft <PROTOCOL-ID> ...",
            "attention": attention,
        }
    drafts = [protocol for protocol in protocols if protocol["status"] == "DRAFT"]
    if drafts:
        return {
            "program_id": program_id,
            "action": "REVIEW_PROTOCOL",
            "reason": "A draft Protocol requires human review before execution.",
            "command": f"bwork protocol seal {drafts[0]['protocol_id']}",
            "attention": attention,
        }

    experiments = sorted(
        (
            experiment
            for experiment in state["experiments"].values()
            if experiment["program_id"] == program_id
        ),
        key=lambda item: item["experiment_id"],
    )
    if not experiments:
        return {
            "program_id": program_id,
            "action": "CREATE_EXPERIMENT",
            "reason": "The frozen Protocol has no Experiment.",
            "command": f"bwork experiment create <EXPERIMENT-ID> --program {program_id} ...",
            "attention": attention,
        }
    active = next(
        (item for item in reversed(experiments) if item["status"] not in {"COMPLETED", "CANCELLED"}),
        None,
    )
    if active is not None:
        experiment_runs = [
            run
            for run in state["runs"].values()
            if run["experiment_id"] == active["experiment_id"]
        ]
        action: str
        reason: str
        command: str
        if active["status"] == "PLANNED":
            action = "IMPLEMENT_EXPERIMENT"
            reason = f"Experiment {active['experiment_id']} is ready for implementation."
            command = f"bwork experiment transition {active['experiment_id']} implemented"
        elif active["status"] == "IMPLEMENTED":
            action = "START_PILOT"
            reason = f"Experiment {active['experiment_id']} is implemented."
            command = f"bwork experiment transition {active['experiment_id']} pilot-started"
        elif active["status"] == "PILOT_RUNNING":
            pilot_runs = [run for run in experiment_runs if run.get("phase") == "PILOT"]
            protocol = state["protocols"][active["protocol_id"]]
            analysis_spec = protocol.get("analysis_spec")
            if analysis_spec is None and pilot_runs:
                action = "REVIEW_UNREGISTERED_PILOT"
                reason = (
                    "Pilot Runs are preserved, but the frozen Protocol has no "
                    "registered analysis specification. Review the capture before choosing "
                    "a registered follow-up or cancelling the Experiment."
                )
                command = "bwork status"
            elif analysis_spec is None:
                action = "EXECUTE_PILOT"
                reason = "The Pilot has no registered Run."
                command = (
                    f"bwork run local <RUN-ID> --experiment {active['experiment_id']} "
                    "--phase PILOT -- <command>"
                )
            else:
                expected = set(analysis_spec.get("pilot_run_ids", []))
                recorded = {run["run_id"] for run in pilot_runs}
                missing = sorted(expected - recorded)
                registered = [state["runs"].get(run_id) for run_id in sorted(expected)]
                invalid_registered = any(
                    run is not None
                    and (
                        run["experiment_id"] != active["experiment_id"]
                        or run["program_id"] != program_id
                        or run["protocol_id"] != active["protocol_id"]
                        or run.get("phase") != "PILOT"
                    )
                    for run in registered
                )
                required_arms = {
                    arm
                    for comparison in analysis_spec.get("comparisons", [])
                    if comparison["experiment_id"] == active["experiment_id"]
                    for arm in comparison["arms"]
                }
                recorded_arms = {
                    run.get("arm")
                    for run in registered
                    if run is not None and run.get("arm") is not None
                }
                missing_arms = sorted(required_arms - recorded_arms)
                if expected and not missing and not invalid_registered and not missing_arms:
                    action = "COMPLETE_PILOT"
                    reason = "All registered Pilot Runs have been recorded."
                    command = (
                        f"bwork experiment transition {active['experiment_id']} pilot-completed"
                    )
                elif expected and not missing and (invalid_registered or missing_arms):
                    action = "REPAIR_PILOT_REGISTRATION"
                    reason = (
                        "Registered Pilot Runs do not satisfy the frozen comparison arms: "
                        + ", ".join(missing_arms)
                        if missing_arms
                        else "Registered Pilot Runs do not match the frozen Experiment lineage."
                    )
                    command = (
                        f"bwork issue open <ISSUE-ID> --program {program_id} "
                        f"--subject {active['experiment_id']} ..."
                    )
                else:
                    action = "EXECUTE_PILOT"
                    reason = (
                        f"Registered Pilot Runs are still missing: {', '.join(missing)}."
                        if missing
                        else "The Pilot analysis specification has no registered Run IDs."
                    )
                    run_id = missing[0] if missing else "<RUN-ID>"
                    command = (
                        f"bwork run local {run_id} --experiment {active['experiment_id']} "
                        "--phase PILOT --arm <ARM> -- <command>"
                    )
        elif active["status"] == "PILOT_COMPLETED":
            action = "START_FORMAL_RUN"
            reason = f"Experiment {active['experiment_id']} completed its Pilot."
            command = f"bwork experiment transition {active['experiment_id']} formal-started"
        else:
            formal_runs = [run for run in experiment_runs if run.get("phase") == "FORMAL"]
            if formal_runs:
                action = "COMPLETE_EXPERIMENT"
                reason = "At least one Formal Run has been preserved for review."
                command = f"bwork experiment transition {active['experiment_id']} completed"
            else:
                action = "EXECUTE_FORMAL_RUN"
                reason = f"Experiment {active['experiment_id']} is ready for a Formal Run."
                command = (
                    f"bwork run local <RUN-ID> --experiment {active['experiment_id']} "
                    "--phase FORMAL --arm <ARM> -- <command>"
                )
        return {
            "program_id": program_id,
            "action": action,
            "reason": reason,
            "command": command,
            "attention": attention,
        }

    bundles = [
        bundle
        for bundle in state["result_bundles"].values()
        if bundle["program_id"] == program_id
    ]
    if not bundles:
        protocol_id = experiments[-1]["protocol_id"]
        return {
            "program_id": program_id,
            "action": "ANALYZE",
            "reason": "Experiment Runs exist, but no Result Bundle has been computed.",
            "command": f"bwork analyze --program {program_id} --protocol {protocol_id}",
            "attention": attention,
        }
    assessments = [
        assessment
        for assessment in state["assessments"].values()
        if assessment["program_id"] == program_id
    ]
    if not assessments:
        return {
            "program_id": program_id,
            "action": "ASSESS",
            "reason": "The Result Bundle still needs scientific interpretation.",
            "command": f"bwork review {bundles[-1]['bundle_id']} ...",
            "attention": attention,
        }
    if not program["decisions"]:
        return {
            "program_id": program_id,
            "action": "DECIDE",
            "reason": "Assessment is complete and awaits a human Decision.",
            "command": f"bwork decide --program {program_id} ...",
            "attention": attention,
        }
    return {
        "program_id": program_id,
        "action": "CONTINUE_OR_CLOSE",
        "reason": "The current research loop has a sealed Decision.",
        "command": f"bwork program close {program_id}",
        "attention": attention,
    }


def program_summary(state: dict[str, Any], program_id: str | None) -> dict[str, Any]:
    program = state["programs"].get(program_id) if program_id else None
    collections = (
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
        "issues",
    )
    counts = {
        collection: sum(
            1
            for identifier, record in state[collection].items()
            if identifier == program_id
            or (isinstance(record, dict) and record.get("program_id") == program_id)
        )
        for collection in collections
    }
    return {
        "active_program_id": program_id,
        "title": program.get("title") if program else None,
        "stage": program.get("status") if program else None,
        "counts": counts,
        "next": next_step(state, program_id),
    }
