---
language: en
canonical: true
---

# Scientific Canon

M7 closes the first canonical research loop:

```text
Evidence -> Claim -> Hypothesis -> Protocol -> Experiment -> Run
         -> Result Bundle -> Assessment -> Decision
```

## Evidence and Claims

An `evidence/1.2` record binds a sourced observation to a content-addressed
Artifact. Source resolution and content inspection are separate, monotonic
events. A Claim relation is first proposed and then explicitly verified; Claim
creation itself never verifies Evidence. Verification requires the source to
be resolved and the content inspected.

## Hypotheses and Protocols

A Hypothesis must trace to one or more Claims and include a falsifiable
prediction. Creating it does not freeze a Research Question. Only
`research_question.sealed` reaches `RQ_FROZEN`, with Actor and Receipt
provenance. Protocols may register exact Hypothesis IDs. A Protocol Seal also
stores its Actor.

Local reproduction is represented by `reproduction-record/1.0`, not a
manually toggled Evidence boolean. The record binds Evidence to canonical
Runs, a Result Bundle, Artifacts, and an Assessment.

## Assessment and Decision

An `assessment/1.1` record binds interpretation to a canonical Result Bundle
and its Sigil. It records limitations and explicit Claim and Hypothesis
findings. Replay checks that every finding belongs to the same Program and
that each Hypothesis was registered by the analyzed Protocol.

A `decision/1.2` object references one or more complete Assessments and stores
its Actor. Outcome-specific Gates prevent CONTINUE with an open CRITICAL Issue,
require actions for REPAIR, require lineage for PIVOT, and preserve unresolved
Issues and Assessment limitations. Decisions are immutable in this version.

## Lineage

`bwork trace OBJECT-ID` includes both events owned by the object and later
events whose payload references it. A Claim trace therefore includes its
creation, dependent Hypotheses, and later Assessment findings.

Earlier Evidence, Claim, Protocol, and Decision Schemas remain published
unchanged. M10 projections use the corrected additive contracts.
