#!/usr/bin/env python3
"""Build the canonical M10 repair-study acceptance project."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from benchwork.athanor import Athanor, AthanorError
from benchwork.rites import RiteRegistry


def sigil(blob: bytes) -> str:
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def build(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    if (root / ".benchwork").exists():
        raise RuntimeError(f"refusing to replace existing project: {root}")

    source_blob = b'{"title":"Registered repair evidence","inspected":true}\n'
    implementation_blob = b'{"implementation":"m10-reference-kernel"}\n'
    (root / "source.json").write_bytes(source_blob)
    (root / "implementation.json").write_bytes(implementation_blob)

    athanor = Athanor(root)
    athanor.initialize()
    RiteRegistry(root).initialize()
    program_id, _ = athanor.create_program(
        "m10-repair-study",
        "M10 repair study",
        {"statement": "Can a complete research chain fail closed and replay?"},
    )
    athanor.record_evidence(
        "EV-001",
        program_id,
        {"uri": "source.json", "sigil": sigil(source_blob)},
        "Registered source inspection identified a reproducible repair signal.",
    )
    athanor.verify_evidence("EV-001", ["source_resolved", "content_inspected"])
    athanor.create_claim(
        "CL-001",
        program_id,
        "empirical",
        "The registered treatment improves the repair score.",
        [{"evidence_id": "EV-001", "relation": "SUPPORTS"}],
    )
    athanor.verify_claim_relation("CL-001", "EV-001")
    athanor.create_hypothesis(
        "HY-001",
        program_id,
        ["CL-001"],
        "The treatment increases mean repair score under the sealed Protocol.",
        "The paired treatment mean exceeds the paired baseline mean.",
    )
    athanor.seal_research_question(
        program_id,
        "Does the treatment improve the registered repair score?",
    )
    analysis_spec = {
        "schema_version": "analysis-spec/1.0",
        "comparisons": [
            {
                "comparison_id": "CMP-001",
                "experiment_id": "EX-001",
                "arms": ["baseline", "treatment"],
                "metric": "score",
                "estimand": "mean_difference",
                "pairing": "paired",
                "uncertainty_method": "student_t",
                "confidence_level": 0.95,
            }
        ],
        "multiple_comparison_policy": "none",
        "practical_significance_thresholds": {"score": 0.02},
        "expected_run_ids": [
            "RUN-B1",
            "RUN-T1",
            "RUN-B2",
            "RUN-T2",
            "RUN-X1",
            "RUN-F1",
        ],
    }
    athanor.draft_protocol(
        "PT-001",
        program_id,
        "Sealed M10 repair comparison",
        "Compare paired included Runs and preserve failed and excluded inventory.",
        ["HY-001"],
        "confirmatory",
        analysis_spec,
    )
    athanor.seal_protocol("PT-001")
    working_id, _ = athanor.create_working(
        "computational-study@0.2.0",
        program_id,
        "PT-001",
    )
    athanor.register_artifact(
        "AR-001",
        program_id,
        "implementation",
        {"uri": "implementation.json", "sigil": sigil(implementation_blob)},
        working_id,
        ["PT-001"],
    )
    athanor.create_experiment(
        "EX-001",
        program_id,
        "PT-001",
        "Does the registered implementation improve repair score?",
        "HY-001",
    )
    athanor.transition_experiment("EX-001", "implemented")
    athanor.transition_experiment("EX-001", "pilot-started")
    athanor.record_run(
        "RUN-B1", "EX-001", "COMPLETED", True, {"score": 0.80},
        seed=1, phase="PILOT", arm="baseline",
    )
    athanor.record_run(
        "RUN-T1", "EX-001", "COMPLETED", True, {"score": 0.86},
        seed=1, phase="PILOT", arm="treatment",
    )
    athanor.transition_experiment("EX-001", "pilot-completed")
    athanor.transition_experiment("EX-001", "formal-started")
    athanor.record_run(
        "RUN-B2", "EX-001", "COMPLETED", True, {"score": 0.82},
        seed=2, arm="baseline",
    )
    athanor.record_run(
        "RUN-T2", "EX-001", "COMPLETED", True, {"score": 0.91},
        seed=2, arm="treatment",
    )
    athanor.record_run(
        "RUN-X1",
        "EX-001",
        "COMPLETED",
        False,
        {"score": 0.99},
        seed=3,
        exclusion_reason="Registered environment mismatch exclusion.",
        policy_reference="PT-001#analysis-plan",
        arm="treatment",
    )
    athanor.record_run(
        "RUN-F1",
        "EX-001",
        "FAILED",
        False,
        seed=4,
        arm="baseline",
    )
    athanor.transition_experiment("EX-001", "completed")
    bundle, _, _, _ = athanor.compute_analysis(program_id, "PT-001")
    assessment_id, _ = athanor.review_result(
        bundle["bundle_id"],
        "The registered comparison is positive but evidence repair remains required.",
        ["One critical registered evidence inventory issue remains unresolved."],
        [
            {
                "claim_id": "CL-001",
                "status": "SUPPORTED",
                "rationale": "Included paired Runs moved in the registered direction.",
            }
        ],
        [
            {
                "hypothesis_id": "HY-001",
                "status": "SUPPORTED",
                "rationale": "The treatment mean exceeded the baseline mean.",
            }
        ],
    )
    athanor.open_issue(
        "IS-001",
        program_id,
        ["EV-001"],
        "CRITICAL",
        "Incomplete registered evidence inventory",
        "A registered evidence dependency requires repair before continuation.",
    )
    event_count = len(athanor.chronicle.events())
    try:
        athanor.seal_decision(
            program_id,
            "CONTINUE",
            [assessment_id],
            "Continue without repairing the critical issue.",
        )
    except AthanorError as error:
        if "CRITICAL" not in str(error):
            raise
    else:
        raise AssertionError("CONTINUE unexpectedly passed the CRITICAL Issue Gate")
    if len(athanor.chronicle.events()) != event_count:
        raise AssertionError("rejected CONTINUE mutated Chronicle")

    decision_id, _ = athanor.seal_decision(
        program_id,
        "REPAIR",
        [assessment_id],
        "Repair the registered evidence dependency before another study cycle.",
        ["Resolve IS-001 and repeat the registered evidence assessment."],
    )
    report = {
        "program_id": program_id,
        "working_id": working_id,
        "bundle_id": bundle["bundle_id"],
        "assessment_id": assessment_id,
        "decision_id": decision_id,
        "continue_rejected": True,
    }
    (root / "scenario-report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.root.resolve()), indent=2))


if __name__ == "__main__":
    main()
