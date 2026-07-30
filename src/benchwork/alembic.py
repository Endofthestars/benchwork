"""Alembic: deterministic descriptive aggregation of canonical Runs."""

from __future__ import annotations

import hashlib
import math
import os
import statistics
from pathlib import Path
from typing import Any

from .athanor import AthanorError, canonical_json


def build_legacy_result_bundle(
    bundle_id: str,
    program_id: str,
    protocol_id: str,
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Rebuild result-bundle/1.0 exactly for historical Chronicle replay."""
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
            if run["schema_version"] in {"run/1.1", "run/1.2"}
            else run
            for run in selected_records
        ),
        key=lambda run: run["run_id"],
    )
    included = [
        run
        for run in selected
        if run["status"] == "COMPLETED" and run["analysis_included"]
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
        values = _numeric_values(included, metric)
        mean = statistics.fmean(values)
        sample_stddev = statistics.stdev(values) if len(values) > 1 else None
        margin = (
            1.96 * sample_stddev / math.sqrt(len(values))
            if sample_stddev is not None
            else None
        )
        summaries[metric] = {
            "n": len(values),
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
        "excluded_run_ids": [
            run["run_id"] for run in selected if run["run_id"] not in included_set
        ],
        "metrics": summaries,
    }


def _numeric_values(runs: list[dict[str, Any]], metric: str) -> list[float]:
    values: list[float] = []
    for run in runs:
        if metric not in run["metrics"]:
            raise AthanorError(
                f"Run {run['run_id']} is missing registered metric {metric}"
            )
        value = run["metrics"][metric]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise AthanorError(f"metric {metric} must contain only finite numbers")
        values.append(float(value))
    return values


def _descriptive(values: list[float]) -> dict[str, float | int | None]:
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "sample_stddev": statistics.stdev(values) if len(values) > 1 else None,
        "min": min(values),
        "max": max(values),
    }


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    maximum_iterations = 200
    epsilon = 3e-14
    floor = 1e-300
    qab = a + b
    qap = a + 1
    qam = a - 1
    c = 1.0
    d = 1.0 - qab * x / qap
    d = floor if abs(d) < floor else d
    d = 1.0 / d
    result = d
    for iteration in range(1, maximum_iterations + 1):
        doubled = 2 * iteration
        coefficient = iteration * (b - iteration) * x / (
            (qam + doubled) * (a + doubled)
        )
        d = 1.0 + coefficient * d
        d = floor if abs(d) < floor else d
        c = 1.0 + coefficient / c
        c = floor if abs(c) < floor else c
        d = 1.0 / d
        result *= d * c
        coefficient = -(a + iteration) * (qab + iteration) * x / (
            (a + doubled) * (qap + doubled)
        )
        d = 1.0 + coefficient * d
        d = floor if abs(d) < floor else d
        c = 1.0 + coefficient / c
        c = floor if abs(c) < floor else c
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) <= epsilon:
            return result
    raise AthanorError("Student-t interval failed to converge")


def _regularized_beta(x: float, a: float, b: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    factor = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return factor * _beta_continued_fraction(a, b, x) / a
    return 1.0 - factor * _beta_continued_fraction(b, a, 1.0 - x) / b


def _student_t_cdf(value: float, degrees_of_freedom: float) -> float:
    x = degrees_of_freedom / (degrees_of_freedom + value * value)
    tail = 0.5 * _regularized_beta(
        x,
        degrees_of_freedom / 2.0,
        0.5,
    )
    return 1.0 - tail if value >= 0 else tail


def _student_t_critical(level: float, degrees_of_freedom: float) -> float:
    target = 0.5 + level / 2.0
    lower = 0.0
    upper = 1.0
    while _student_t_cdf(upper, degrees_of_freedom) < target:
        upper *= 2.0
        if upper > 1_000_000:
            raise AthanorError("Student-t critical value is not finite")
    for _ in range(100):
        midpoint = (lower + upper) / 2.0
        if _student_t_cdf(midpoint, degrees_of_freedom) < target:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0


def _effective_level(level: float, policy: str, comparison_count: int) -> float:
    if policy == "bonferroni":
        return 1.0 - (1.0 - level) / comparison_count
    return level


def _unavailable(
    requested_level: float,
    effective_level: float,
    reason: str,
) -> dict[str, Any]:
    return {
        "method": "unavailable",
        "requested_level": requested_level,
        "effective_level": effective_level,
        "lower": None,
        "upper": None,
        "degrees_of_freedom": None,
        "seed": None,
        "samples": None,
        "reason": reason,
    }


def _paired_values(
    treatment_runs: list[dict[str, Any]],
    control_runs: list[dict[str, Any]],
    metric: str,
) -> list[float]:
    treatment_by_seed = {
        run["seed"]: run
        for run in treatment_runs
        if run["seed"] is not None
    }
    control_by_seed = {
        run["seed"]: run
        for run in control_runs
        if run["seed"] is not None
    }
    if (
        len(treatment_by_seed) != len(treatment_runs)
        or len(control_by_seed) != len(control_runs)
        or set(treatment_by_seed) != set(control_by_seed)
    ):
        raise AthanorError(
            "paired comparison requires identical unique non-null Run seeds"
        )
    return [
        _numeric_values([treatment_by_seed[seed]], metric)[0]
        - _numeric_values([control_by_seed[seed]], metric)[0]
        for seed in sorted(treatment_by_seed)
    ]


def _standardized_effect(
    pairing: str,
    estimate: float,
    treatment_values: list[float],
    control_values: list[float],
    paired_differences: list[float] | None,
) -> dict[str, Any]:
    if pairing == "paired":
        if paired_differences is None or len(paired_differences) < 2:
            return {
                "method": "unavailable",
                "estimate": None,
                "reason": "paired standardized effect requires two pairs",
            }
        denominator = statistics.stdev(paired_differences)
        if denominator == 0:
            return {
                "method": "unavailable",
                "estimate": None,
                "reason": "paired differences have zero variance",
            }
        return {
            "method": "paired_dz",
            "estimate": estimate / denominator,
            "reason": None,
        }
    if len(treatment_values) < 2 or len(control_values) < 2:
        return {
            "method": "unavailable",
            "estimate": None,
            "reason": "Cohen's d requires two observations per arm",
        }
    degrees = len(treatment_values) + len(control_values) - 2
    pooled_variance = (
        (len(treatment_values) - 1) * statistics.variance(treatment_values)
        + (len(control_values) - 1) * statistics.variance(control_values)
    ) / degrees
    if pooled_variance == 0:
        return {
            "method": "unavailable",
            "estimate": None,
            "reason": "pooled variance is zero",
        }
    return {
        "method": "cohens_d",
        "estimate": estimate / math.sqrt(pooled_variance),
        "reason": None,
    }


def _student_t_interval(
    comparison: dict[str, Any],
    estimate: float,
    treatment_values: list[float],
    control_values: list[float],
    paired_differences: list[float] | None,
    effective_level: float,
) -> dict[str, Any]:
    requested_level = comparison["confidence_level"]
    if comparison["pairing"] == "none":
        return _unavailable(
            requested_level,
            effective_level,
            "pairing none does not define a Student-t sampling model",
        )
    if comparison["pairing"] == "paired":
        if paired_differences is None or len(paired_differences) < 2:
            return _unavailable(
                requested_level,
                effective_level,
                "Student-t interval requires at least two paired observations",
            )
        degrees = float(len(paired_differences) - 1)
        standard_error = statistics.stdev(paired_differences) / math.sqrt(
            len(paired_differences)
        )
    else:
        if len(treatment_values) < 2 or len(control_values) < 2:
            return _unavailable(
                requested_level,
                effective_level,
                "Welch Student-t interval requires two observations per arm",
            )
        treatment_variance = statistics.variance(treatment_values)
        control_variance = statistics.variance(control_values)
        treatment_term = treatment_variance / len(treatment_values)
        control_term = control_variance / len(control_values)
        standard_error = math.sqrt(treatment_term + control_term)
        denominator = (
            treatment_term * treatment_term / (len(treatment_values) - 1)
            + control_term * control_term / (len(control_values) - 1)
        )
        degrees = (
            (treatment_term + control_term) ** 2 / denominator
            if denominator > 0
            else float(len(treatment_values) + len(control_values) - 2)
        )
    margin = (
        _student_t_critical(effective_level, degrees) * standard_error
        if standard_error > 0
        else 0.0
    )
    return {
        "method": "student_t",
        "requested_level": requested_level,
        "effective_level": effective_level,
        "lower": estimate - margin,
        "upper": estimate + margin,
        "degrees_of_freedom": degrees,
        "seed": None,
        "samples": None,
        "reason": None,
    }


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


class _DeterministicSampler:
    def __init__(self, seed: int) -> None:
        self.seed = str(seed).encode("ascii")
        self.counter = 0

    def index(self, length: int) -> int:
        ceiling = 1 << 256
        limit = ceiling - ceiling % length
        while True:
            material = self.seed + b":" + str(self.counter).encode("ascii")
            self.counter += 1
            value = int.from_bytes(hashlib.sha256(material).digest(), "big")
            if value < limit:
                return value % length


def _bootstrap_interval(
    comparison: dict[str, Any],
    treatment_values: list[float],
    control_values: list[float],
    paired_differences: list[float] | None,
    effective_level: float,
) -> dict[str, Any]:
    requested_level = comparison["confidence_level"]
    if comparison["pairing"] == "none":
        return _unavailable(
            requested_level,
            effective_level,
            "pairing none does not define a bootstrap sampling model",
        )
    if comparison["pairing"] == "paired":
        if paired_differences is None or len(paired_differences) < 2:
            return _unavailable(
                requested_level,
                effective_level,
                "bootstrap interval requires at least two paired observations",
            )
    elif len(treatment_values) < 2 or len(control_values) < 2:
        return _unavailable(
            requested_level,
            effective_level,
            "bootstrap interval requires two observations per arm",
        )

    seed = comparison["bootstrap_seed"]
    samples = comparison["bootstrap_samples"]
    sampler = _DeterministicSampler(seed)
    estimates: list[float] = []
    for _ in range(samples):
        if comparison["pairing"] == "paired":
            assert paired_differences is not None
            resampled = [
                paired_differences[sampler.index(len(paired_differences))]
                for _ in paired_differences
            ]
            estimates.append(statistics.fmean(resampled))
        else:
            treatment = [
                treatment_values[sampler.index(len(treatment_values))]
                for _ in treatment_values
            ]
            control = [
                control_values[sampler.index(len(control_values))]
                for _ in control_values
            ]
            estimates.append(statistics.fmean(treatment) - statistics.fmean(control))
    alpha = 1.0 - effective_level
    return {
        "method": "bootstrap",
        "requested_level": requested_level,
        "effective_level": effective_level,
        "lower": _quantile(estimates, alpha / 2.0),
        "upper": _quantile(estimates, 1.0 - alpha / 2.0),
        "degrees_of_freedom": None,
        "seed": seed,
        "samples": samples,
        "reason": None,
    }


def build_result_bundle(
    bundle_id: str,
    protocol: dict[str, Any],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a registered, deterministic descriptive aggregation."""
    analysis_spec = protocol.get("analysis_spec")
    if analysis_spec is None:
        raise AthanorError(
            "Alembic v1.1 requires a Protocol with a registered analysis_spec"
        )
    program_id = protocol["program_id"]
    protocol_id = protocol["protocol_id"]
    selected = sorted(
        (
            run
            for run in runs
            if run["program_id"] == program_id and run["protocol_id"] == protocol_id
        ),
        key=lambda run: run["run_id"],
    )
    selected_ids = {run["run_id"] for run in selected}
    included = [
        run
        for run in selected
        if run["status"] == "COMPLETED"
        and run.get("analysis_disposition", {}).get("included", False)
    ]
    included_ids = [run["run_id"] for run in included]
    excluded_runs = []
    for run in selected:
        if run["run_id"] in included_ids:
            continue
        disposition = run.get("analysis_disposition", {})
        excluded_runs.append(
            {
                "run_id": run["run_id"],
                "status": run["status"],
                "reason": disposition.get("reason")
                or f"Run status is {run['status']}",
                "policy_reference": disposition.get("policy_reference")
                or f"{protocol_id}#analysis-plan",
            }
        )

    comparisons: list[dict[str, Any]] = []
    policy = analysis_spec["multiple_comparison_policy"]
    comparison_count = len(analysis_spec["comparisons"])
    for comparison in analysis_spec["comparisons"]:
        control_arm, treatment_arm = comparison["arms"]
        experiment_id = comparison["experiment_id"]
        metric = comparison["metric"]
        control_runs = [
            run
            for run in included
            if run["experiment_id"] == experiment_id
            and run.get("arm") == control_arm
        ]
        treatment_runs = [
            run
            for run in included
            if run["experiment_id"] == experiment_id
            and run.get("arm") == treatment_arm
        ]
        if not control_runs or not treatment_runs:
            raise AthanorError(
                f"comparison {comparison['comparison_id']} is missing a registered arm"
            )
        control_values = _numeric_values(control_runs, metric)
        treatment_values = _numeric_values(treatment_runs, metric)
        paired_differences = (
            _paired_values(treatment_runs, control_runs, metric)
            if comparison["pairing"] == "paired"
            else None
        )
        estimate = (
            statistics.fmean(paired_differences)
            if paired_differences is not None
            else statistics.fmean(treatment_values)
            - statistics.fmean(control_values)
        )
        effective_level = _effective_level(
            comparison["confidence_level"],
            policy,
            comparison_count,
        )
        if policy in {"holm", "fdr"}:
            uncertainty = _unavailable(
                comparison["confidence_level"],
                effective_level,
                f"{policy} requires ordered test statistics not produced by "
                "deterministic descriptive aggregation",
            )
        elif comparison["uncertainty_method"] == "student_t":
            uncertainty = _student_t_interval(
                comparison,
                estimate,
                treatment_values,
                control_values,
                paired_differences,
                effective_level,
            )
        elif comparison["uncertainty_method"] == "bootstrap":
            uncertainty = _bootstrap_interval(
                comparison,
                treatment_values,
                control_values,
                paired_differences,
                effective_level,
            )
        else:
            uncertainty = _unavailable(
                comparison["confidence_level"],
                effective_level,
                "Protocol registered uncertainty as unavailable",
            )
        threshold = analysis_spec["practical_significance_thresholds"].get(metric)
        comparisons.append(
            {
                "comparison_id": comparison["comparison_id"],
                "experiment_id": experiment_id,
                "estimand": "mean_difference",
                "treatment_arm": treatment_arm,
                "control_arm": control_arm,
                "pairing": comparison["pairing"],
                "run_ids": {
                    "treatment": sorted(run["run_id"] for run in treatment_runs),
                    "control": sorted(run["run_id"] for run in control_runs),
                },
                "metrics": {
                    metric: {
                        "descriptive": {
                            "treatment": _descriptive(treatment_values),
                            "control": _descriptive(control_values),
                        },
                        "effect": {
                            "method": "mean_difference",
                            "estimate": estimate,
                            "standardized": _standardized_effect(
                                comparison["pairing"],
                                estimate,
                                treatment_values,
                                control_values,
                                paired_differences,
                            ),
                        },
                        "uncertainty": uncertainty,
                        "practical_significance": {
                            "threshold": threshold,
                            "exceeds_threshold": (
                                abs(estimate) >= threshold
                                if threshold is not None
                                else None
                            ),
                        },
                    }
                },
            }
        )

    return {
        "schema_version": "result-bundle/1.1",
        "analysis_kind": "deterministic-descriptive-aggregation",
        "bundle_id": bundle_id,
        "program_id": program_id,
        "protocol_id": protocol_id,
        "run_inventory": {
            "all_run_ids": [run["run_id"] for run in selected],
            "included_run_ids": included_ids,
            "excluded_runs": excluded_runs,
            "failed_run_ids": [
                run["run_id"] for run in selected if run["status"] == "FAILED"
            ],
            "missing_run_ids": sorted(
                set(analysis_spec["expected_run_ids"]) - selected_ids
            ),
        },
        "multiple_comparison_policy": policy,
        "comparisons": comparisons,
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
