---
language: en
canonical: true
---

# Integrity and Recovery

M8 makes implementation outputs, research problems, and post-Seal changes
first-class Chronicle objects.

## Canonical Artifacts

An `artifact/1.0` record binds an Artifact ID to a URI and SHA-256 Sigil. It
also records the producing object and zero or more input objects. Every
reference must already exist in the same Research Program. Registration is
immutable and carries its Chronicle timestamp and Receipt.

Inline Artifact references in Runs and Working transitions remain valid. A
canonical Artifact is the stronger form used when an output needs a stable ID,
cross-object lineage, or later Issue and Deviation references.

## Issues

An `issue/1.0` object identifies one or more existing Program objects, assigns a
severity, and records a concrete problem. Its lifecycle is monotonic:
`OPEN -> RESOLVED`. Resolution is a separate event with its own timestamp and
Receipt; a resolved Issue cannot be reopened or resolved again in this
contract.

## Deviations

A `deviation/1.0` object records a planned or unplanned departure from an
already Sealed Protocol. It includes rationale, impact, and affected objects.
Recording a Deviation appends its ID to both the Protocol and Program
projections, but never edits the Protocol title, analysis plan, hypotheses, or
Seal. This preserves the original commitment and makes later context explicit.

All Artifact, Issue, and Deviation references fail before Chronicle append when
an object is absent or belongs to another Program.
