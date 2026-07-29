---
language: en
canonical: true
---

# Alembic

Alembic is the deterministic analysis layer. It consumes canonical Run records
and produces a versioned `result-bundle/1.0`; it does not decide whether a
result has scientific importance.

## Required provenance

A bundle records its Program, Protocol, all selected Runs, each Run's execution
status, and whether that Run was included in the primary analysis. Failed,
cancelled, lost, excluded, and negative runs remain in the bundle rather than
being silently filtered.

## Computation boundary

Python calculates summary statistics, uncertainty, and resource measurements.
An Agent may later read the Bundle when performing scientific review, but it
must not invent a metric or edit the computed artifact.

## Initial aggregation

The first implementation will calculate per-metric `n`, arithmetic mean,
sample standard deviation, and a normal-approximation 95% confidence interval
over completed Runs explicitly marked for primary analysis. It will reject an
analysis that has no such Runs. With one eligible Run, the mean is reported but
sample standard deviation and confidence bounds are `null`, because they are
not estimable from one observation.
