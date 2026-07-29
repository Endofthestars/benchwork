---
title: "RFC-0005: Experiment and Run Lifecycle"
document_id: BW-RFC-0005
version: 1.0
status: accepted
owner: Endofthestars
date: 2026-07-29
language: en
canonical: true
---

# RFC-0005: Experiment and Run Lifecycle

## Experiment Lifecycle

Experiments use monotonic Chronicle transitions:

```text
PLANNED -> IMPLEMENTED -> PILOT_RUNNING -> PILOT_COMPLETED
        -> FORMAL_RUNNING -> COMPLETED
```

`experiment.cancelled` may terminate any non-terminal state. Re-entry,
skipping, and transitions from a terminal state fail before append.

`experiment.pilot_completed` is the only Pilot exit for a v1.1 Working. It
requires the Protocol to register `pilot_run_ids`, every registered Pilot Run
to exist in the same Experiment, Program, Protocol, and PILOT phase, and every
Arm required by the Experiment comparisons to be represented. Individual Run
records never declare the Pilot complete.

The event vocabulary is:

- `experiment.planned`
- `experiment.implemented`
- `experiment.pilot_started`
- `experiment.pilot_completed`
- `experiment.formal_started`
- `experiment.completed`
- `experiment.cancelled`

## Run Simplification

M10 retains `run.recorded` as an immutable observation, but permits only
terminal statuses: `COMPLETED`, `FAILED`, `CANCELLED`, and `LOST`. `QUEUED` and
`RUNNING` belong to a future Executor Job projection and are not Run states.
This is the explicit simplified option allowed by the M10 brief.

Every Run declares `phase: PILOT | FORMAL` and an `analysis_disposition`.
Included Runs must be completed and contain metrics. A completed Run excluded
from analysis must state a non-empty reason and a Protocol policy reference.
Failed and other terminal Runs remain in the canonical inventory.

## Study Modes

Protocols declare `study_mode: confirmatory | exploratory`.

- A confirmatory Protocol requires at least one existing Hypothesis.
- Any Experiment Hypothesis reference must exist, belong to the Program, and
  be registered by the Protocol.
- An exploratory Protocol may omit Hypotheses.
- An exploratory Assessment may contain no Hypothesis findings.
- A confirmatory Assessment requires at least one registered Hypothesis
  finding.

## Program Reachability

Canonical events make all terminal phase-one statuses reachable:

- implementation Artifact: `IMPLEMENTED`
- explicit Experiment pilot completion: `PILOTED`
- formal start or formal Run: `RUNNING`
- Result Bundle: `RESULT_READY`
- Assessment: `EVALUATED`
- explicit `program.closed` after a sealed Decision: `CLOSED`

A Decision completes a matching Working but leaves the Program `EVALUATED`.
Closure is a separate explicit transition so the M10 repair fixture can finish
with an evaluated, repairable Program.
