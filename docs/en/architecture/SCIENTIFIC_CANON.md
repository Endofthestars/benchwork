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

An `evidence/1.1` record binds a sourced observation to a content-addressed
Artifact. Verification checks are monotonic: a completed check cannot later be
removed. A Claim can only reference Evidence whose source was resolved and
whose content was inspected. Each relation states whether the Evidence
supports, contradicts, limits, reproduces, or leaves the Claim unresolved.

## Hypotheses and Protocols

A Hypothesis must trace to one or more Claims and include a falsifiable
prediction. Protocols may register exact Hypothesis IDs. Once a Protocol is
Sealed, an Experiment can activate only a Hypothesis registered by that
Protocol. Legacy Protocols without Hypothesis IDs remain replayable.

## Assessment and Decision

An `assessment/1.1` record binds interpretation to a canonical Result Bundle
and its Sigil. It records limitations and explicit Claim and Hypothesis
findings. Replay checks that every finding belongs to the same Program and
that each Hypothesis was registered by the analyzed Protocol.

A `decision/1.1` object references one or more complete Assessments. The CLI
invocation is the human commitment point; Athanor appends `decision.sealed`
and embeds the Receipt and timestamp in the projection. Decisions are
immutable in this version.

## Lineage

`bwork trace OBJECT-ID` includes both events owned by the object and later
events whose payload references it. A Claim trace therefore includes its
creation, dependent Hypotheses, and later Assessment findings.

The original 1.0 Evidence, Claim, Assessment, and Decision Schemas remain
published unchanged. M7 projections use the additive 1.1 contracts.
