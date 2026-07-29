---
title: "RFC-0006: Alembic Analysis Contract"
document_id: BW-RFC-0006
version: 1.0
status: accepted
owner: Endofthestars
date: 2026-07-29
language: en
canonical: true
---

# RFC-0006: Alembic Analysis Contract

## Positioning

Alembic v1.1 is a deterministic descriptive aggregator with narrowly
registered uncertainty calculations. It is not a complete statistical
analysis engine and does not choose comparisons, metrics, exclusions, or
scientific interpretations.

New analysis requires a sealed Protocol containing `analysis-spec/1.0`.
Protocols without that contract fail closed. Historical
`result-bundle/1.0` events remain replayable, but Athanor does not create new
v1.0 Bundles.

## Registered Comparison

Every comparison declares one Experiment ID, two distinct arms ordered as
control then treatment, one metric, the `mean_difference` estimand, a pairing
mode, an uncertainty method, and a confidence level.

Runs carry an explicit arm. Alembic selects only included, completed Runs that
match both the registered Experiment and arm. Runs from another Experiment
remain in the inventory and are never pooled implicitly. A missing arm aborts
analysis before Chronicle append.

## Descriptive and Effect Output

Each arm reports `n`, mean, sample standard deviation, minimum, and maximum.
The effect is treatment mean minus control mean. Standardized effect metadata
uses paired `dz` or unpaired Cohen's `d` when prerequisites are met, otherwise
it records why the value is unavailable. Practical significance compares the
absolute mean difference with the Protocol threshold without interpreting its
scientific importance.

## Uncertainty

Paired Student-t intervals use differences matched by identical, unique,
non-null Run seeds. Unpaired intervals use Welch's standard error and degrees
of freedom. Student-t critical values are computed from the registered level;
Alembic never substitutes the normal constant `1.96`.

Bootstrap intervals use deterministic percentile resampling with the exact
Protocol seed and sample count. Paired bootstrap resamples paired differences;
unpaired bootstrap resamples each arm independently.

One observation per arm, one pair, missing pairing keys, or a pairing mode of
`none` produces explicit `unavailable` uncertainty. It does not produce a
numeric interval.

## Multiple Comparisons

`none` preserves the requested level. `bonferroni` adjusts the effective
interval level by the number of registered comparisons. `holm` and `fdr` are
recorded policies, but v1.1 reports uncertainty as unavailable because those
procedures require ordered test statistics outside this descriptive contract.

## Run Inventory

The Bundle retains all recorded Run IDs, included Run IDs, failed Run IDs,
excluded Runs with reasons and policy references, and expected but missing Run
IDs. Inventory membership is independent from whether a Run contributes to a
particular comparison.

## Determinism

Inputs are sorted by canonical Run ID. Bootstrap indices come from a
runtime-independent SHA-256 counter sampler initialized by the registered
seed. Bundle reconstruction during Chronicle replay must reproduce the complete
JSON object and Sigil byte-for-byte.
