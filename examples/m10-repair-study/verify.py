#!/usr/bin/env python3
"""Verify the M10 repair study after reopening it in a fresh process."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchwork.athanor import Athanor


CHAIN = (
    "EV-001",
    "CL-001",
    "HY-001",
    "PT-001",
    "EX-001",
    "RUN-B1",
    "RUN-T1",
    "RUN-B2",
    "RUN-T2",
    "RB-001",
    "AS-001",
    "DE-001",
)


def verify(root: Path) -> dict:
    fixture = Path(__file__).resolve().parent
    expected = json.loads((fixture / "expected-state.json").read_text(encoding="utf-8"))
    athanor = Athanor(root)
    events = athanor.chronicle.events()
    state = athanor.replay()
    program = state["programs"]["RP-001"]
    working = state["workings"]["WK-001"]
    decision = state["decisions"]["DE-001"]
    bundle = state["result_bundles"]["RB-001"]
    inventory = bundle["run_inventory"]
    effect = bundle["comparisons"][0]["metrics"]["score"]["effect"]["estimate"]

    actual = {
        "program_status": program["status"],
        "working_status": working["status"],
        "working_stage": working["stage"],
        "decision": decision["outcome"],
        "open_issue": decision["unresolved_issue_ids"][0],
        "included_run_ids": inventory["included_run_ids"],
        "failed_run_ids": inventory["failed_run_ids"],
        "excluded_run_ids": [
            item["run_id"]
            for item in inventory["excluded_runs"]
            if state["runs"][item["run_id"]]["status"] == "COMPLETED"
        ],
        "effect_estimate": round(effect, 6),
    }
    if actual != expected:
        raise AssertionError(f"projection mismatch:\n{actual}\n!=\n{expected}")
    missing_trace = [object_id for object_id in CHAIN if not athanor.trace(object_id)]
    if missing_trace:
        raise AssertionError(f"objects have no Chronicle trace: {missing_trace}")
    if state["claims"]["CL-001"]["evidence_relations"][0]["status"] != "VERIFIED":
        raise AssertionError("Claim relation was not explicitly verified")
    if state["claims"]["CL-001"]["evidence_relations"][0]["evidence_id"] != "EV-001":
        raise AssertionError("Evidence to Claim lineage is broken")
    if state["hypotheses"]["HY-001"]["claim_ids"] != ["CL-001"]:
        raise AssertionError("Claim to Hypothesis lineage is broken")
    if state["protocols"]["PT-001"]["hypothesis_ids"] != ["HY-001"]:
        raise AssertionError("Hypothesis to Protocol lineage is broken")
    if any(
        run["experiment_id"] != "EX-001"
        for run in state["runs"].values()
    ):
        raise AssertionError("Protocol Experiment to Run lineage is broken")
    if bundle["protocol_id"] != "PT-001":
        raise AssertionError("Run to Result Bundle lineage is broken")
    if state["assessments"]["AS-001"]["result_bundle_id"] != "RB-001":
        raise AssertionError("Result Bundle to Assessment lineage is broken")
    if decision["assessment_ids"] != ["AS-001"]:
        raise AssertionError("Assessment to Decision lineage is broken")
    if working["history"][-1]["object_id"] != "DE-001":
        raise AssertionError("Decision did not complete the Working")

    return {
        "program_status": program["status"],
        "working_status": working["status"],
        "decision": decision["outcome"],
        "chronicle_verified": bool(events),
        "all_objects_replayable": True,
        "traced_object_ids": list(CHAIN),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.root.resolve()), indent=2))


if __name__ == "__main__":
    main()
