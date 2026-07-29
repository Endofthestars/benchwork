"""Alembic: deterministic aggregation of canonical experimental Runs."""

from __future__ import annotations

import math
import os
import statistics
from pathlib import Path
from typing import Any

from .athanor import AthanorError, canonical_json


def build_result_bundle(
    bundle_id: str,
    program_id: str,
    protocol_id: str,
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic result bundle without interpreting its meaning."""
    selected_records = (
        run.copy()
        for run in runs
        if run["program_id"] == program_id and run["protocol_id"] == protocol_id
    )
    selected = sorted(
        (
            {
                "schema_version": "run/1.0",
                "run_id": run["run_id"],
                "program_id": run["program_id"],
                "protocol_id": run["protocol_id"],
                "experiment_id": run["experiment_id"],
                "status": run["status"],
                "analysis_included": run["analysis_disposition"]["included"],
                "seed": run["seed"],
                "metrics": run["metrics"],
                "artifacts": run["artifacts"],
            }
            if run["schema_version"] == "run/1.1"
            else run
            for run in selected_records
        ),
        key=lambda run: run["run_id"],
    )
    included = [
        run
        for run in selected
        if run["status"] == "COMPLETED"
        and (
            run["analysis_disposition"]["included"]
            if "analysis_disposition" in run
            else run["analysis_included"]
        )
    ]
    if not included:
        raise AthanorError("analysis requires at least one completed, included Run")

    metric_names = set(included[0]["metrics"])
    if not metric_names:
        raise AthanorError("included Runs must contain at least one metric")
    if any(set(run["metrics"]) != metric_names for run in included[1:]):
        raise AthanorError("included Runs must report the same metric set")

    summaries: dict[str, dict[str, float | int | None]] = {}
    for metric in sorted(metric_names):
        values = [run["metrics"][metric] for run in included]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
            raise AthanorError(f"metric {metric} must contain only numeric values")
        numeric = [float(value) for value in values]
        if not all(math.isfinite(value) for value in numeric):
            raise AthanorError(f"metric {metric} must contain only finite values")
        mean = statistics.fmean(numeric)
        sample_stddev = statistics.stdev(numeric) if len(numeric) > 1 else None
        margin = 1.96 * sample_stddev / math.sqrt(len(numeric)) if sample_stddev is not None else None
        summaries[metric] = {
            "n": len(numeric),
            "mean": mean,
            "sample_stddev": sample_stddev,
            "ci95_lower": mean - margin if margin is not None else None,
            "ci95_upper": mean + margin if margin is not None else None,
        }

    included_ids = [run["run_id"] for run in included]
    included_set = set(included_ids)
    return {
        "schema_version": "result-bundle/1.0",
        "bundle_id": bundle_id,
        "program_id": program_id,
        "protocol_id": protocol_id,
        "runs": selected,
        "included_run_ids": included_ids,
        "excluded_run_ids": [run["run_id"] for run in selected if run["run_id"] not in included_set],
        "metrics": summaries,
    }


def export_result_bundle(root: Path, bundle: dict[str, Any]) -> Path:
    """Atomically export a replayable Bundle projection."""
    directory = root / ".benchwork" / "results"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{bundle['bundle_id']}.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(canonical_json(bundle) + "\n", encoding="utf-8")
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, destination)
    directory_handle = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(directory_handle)
    finally:
        os.close(directory_handle)
    return destination
