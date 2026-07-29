---
title: "RFC-0003: Scientific Gate Semantics"
document_id: BW-RFC-0003
version: 1.0
status: accepted
owner: Endofthestars
date: 2026-07-29
language: en
canonical: true
---

# RFC-0003: Scientific Gate Semantics

## Status

This RFC defines the M10 separation between recording, proposing, verifying,
and sealing scientific state. It supersedes automatic semantic promotion in
the v0.2 reference kernel.

## Program stages

The monotonic Program stages are:

```text
IDEA
EVIDENCE_RECORDED
CLAIMS_REGISTERED
HYPOTHESES_REGISTERED
RQ_FROZEN
DESIGN_FROZEN
IMPLEMENTED
PILOTED
RUNNING
RESULT_READY
EVALUATED
CLOSED
```

`GAP_SUPPORTED` is removed. Benchwork has no formal Gap object or Gate in M10
and therefore makes no general Program-level Gap support claim.

## Evidence and Claim relations

The evidence verification chain is:

```text
evidence.source_resolved
    -> evidence.content_inspected
        -> claim_relation.verified
```

`evidence.recorded` creates both checks as false. `claim.created` registers a
Claim but does not verify any relation. `claim_relation.proposed` and
`claim_relation.verified` are separate Chronicle events. A verified relation
requires the referenced source to be resolved and its content inspected.

Historical `evidence.verified` events remain replayable, but only source and
content checks have scientific meaning in the M10 projection.

## Hypothesis and Research Question

`hypothesis.created` advances a Program only to `HYPOTHESES_REGISTERED`. An
explicit `research_question.sealed` event is the sole transition to
`RQ_FROZEN`. The Program projection stores the statement, timestamp, Receipt,
and Actor of the Seal.

## Reproduction

`locally_reproduced` is not a boolean check. `reproduction-record/1.0` binds an
Evidence record to existing Runs, a Result Bundle, one or more canonical
Artifacts, and an Assessment. Its status is `REPRODUCED`, `NOT_REPRODUCED`, or
`INCONCLUSIVE`. All referenced objects must belong to the same Program.

## Actors

Research Question, Protocol, and Decision Seals store the Actor from their
Chronicle Event. An Actor records an ID, type, Host, and authentication
mechanism. `local-session` is audit provenance, not cryptographic identity.
Migrated legacy Seals identify the migration tool and do not claim a
historically authenticated human.

## Decision Gates

- `CONTINUE` is rejected while any CRITICAL Issue remains open.
- `REPAIR` requires one or more concrete required actions and may preserve
  open Issues.
- `PIVOT` requires parent Program and reason lineage.
- `STOP` records all currently open Issue IDs and Assessment limitations.
- `INSUFFICIENT_EVIDENCE` does not require a positive Claim finding.
- `REVIEW_REQUIRED` requires and preserves at least two competing
  Assessments.

Every Decision preserves open Issue IDs and unresolved Assessment limitations
at its Seal point. Gate rules are checked both before append and during replay.

## Compatibility

The published v1.0 and v1.1 scientific schemas remain available. Existing
events replay through the corrected M10 projection, but automatic Claim
verification, automatic RQ freezing, and boolean reproduction assertions are
not carried forward as verified scientific facts.
