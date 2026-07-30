---
language: en
canonical: true
---

# Alembic

Alembic is the deterministic descriptive aggregation layer. It consumes
canonical Run records under a registered `analysis-spec/1.0` and produces a
versioned `result-bundle/1.1`; it does not decide whether a result has
scientific importance.

## Required provenance

A bundle records its Program, Protocol, complete Run inventory, registered
comparisons, arm membership, exclusions with reasons, failed Runs, and expected
but missing Runs. Runs from different Experiments remain separate unless the
Protocol explicitly defines a comparison for each Experiment.

## Computation boundary

Python calculates descriptive statistics, mean differences, narrowly
registered uncertainty, and standardized effect metadata. An Agent may later
read the Bundle when performing scientific review, but it must not invent a
metric or edit the computed artifact.

## Initial aggregation

M10 supports paired and Welch Student-t intervals plus deterministic percentile
bootstrap intervals with a registered seed. A single observation per arm
reports uncertainty as unavailable. Alembic never labels a normal
approximation as a generic confidence interval.

See [RFC-0006](../rfcs/RFC-0006-alembic-analysis-contract.md) for the complete
contract and its deliberate limits.
