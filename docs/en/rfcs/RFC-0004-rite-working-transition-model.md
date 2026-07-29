---
title: "RFC-0004: Rite and Working Transition Model"
document_id: BW-RFC-0004
version: 1.0
status: accepted
owner: Endofthestars
date: 2026-07-29
language: en
canonical: true
---

# RFC-0004: Rite and Working Transition Model

## Decision

A Working is a replayed view over canonical Chronicle events. A `rite/1.1`
definition assigns an `exit_contract` to every non-terminal stage. Athanor
advances a matching Working when, and only when, an accepted event satisfies
the declared event type, object type, Program, Protocol, and optional kind,
phase, or status constraints.

The built-in `computational-study@0.2.1` Rite uses this sequence:

| Stage | Required canonical event |
| --- | --- |
| `IMPLEMENTATION` | `artifact.registered`, kind `implementation` |
| `PILOT` | `experiment.pilot_completed` |
| `ANALYSIS` | `analysis.computed` |
| `REVIEW` | `assessment.recorded` |
| `DECISION` | `decision.sealed` |
| `COMPLETED` | terminal |

Each Working history entry records the canonical Event ID and Object ID that
satisfied the contract. The projected status becomes `COMPLETED` only at the
terminal stage.

## Integrity Rules

- Rite content is pinned by its Sigil when the Working is created.
- A v1.1 exit event must belong to the same Program and Protocol.
- An Experiment records its owning `working_id`. If multiple matching Workings
  are active, Experiment creation requires that ID explicitly.
- An exit event advances only the single Working identified by Artifact
  producer or Experiment-derived lineage. Ambiguous or absent lineage advances
  no Working.
- Artifact registration verifies the referenced local blob and Sigil before
  Chronicle accepts the event.
- One canonical event can advance a Working by at most one stage.
- `working.advanced` remains replayable for legacy ledgers only.
- `bwork working advance` is a rejecting compatibility alias. It cannot append
  an event or accept inline Artifact claims.

## Compatibility

`rite/1.0` definitions and legacy Workings remain readable. They do not gain
event exit contracts retroactively. Authors should publish a new Rite version
using `rite/1.1`; changing an installed Rite in place remains forbidden.
`computational-study@0.2.0` remains available for replay compatibility, while
new M10 Workings use `computational-study@0.2.1`.

The supported M10 profile for `computational-study@0.2.1` binds one Working to
one Pilot Experiment. Multiple comparisons may refer to that Experiment, but a
single Working spanning multiple Pilot Experiments is outside the v0.2.1
contract. Such studies must use separate Workings until the analysis contract
scopes Pilot Run registration by Experiment.

## Rejected Alternatives

Inline URI and hash claims are not sufficient evidence of canonical progress.
Emitting a second synthetic Working event for every scientific event was also
rejected because it creates avoidable partial-commit and drift risks.
