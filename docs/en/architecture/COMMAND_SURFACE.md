---
language: en
canonical: true
---

# Command Surface and Agent Handoff

M9 makes the RFC command language operational without treating an unavailable
Provider as completed work.

## Direct research verbs

`start` creates a Research Program. `investigate`, `design`, `implement`,
`pilot`, and bare `run` create Task Capsules for their corresponding
Capabilities. `scry`, `distill`, and `invoke` expose the same mechanism through
Arcana and explicit Capability language.

When `--input-sigil` is omitted, the CLI derives it from the latest canonical
Research Program projection. Tool, time, and network boundaries default to the
Capability contract and can be narrowed on the command line. Ward evaluates
every proposal. Write and execution Capabilities remain
`WAITING_FOR_APPROVAL` until a matching approval Receipt exists.

These verbs prepare bounded work; they do not claim that a Provider ran.
Automatic Provider invocation remains an open design decision.

## Agent Result acceptance

An Agent returns an `agent-result/1.0` Proposal. `bwork task accept FILE`
validates the result, reloads the immutable Task Capsule, checks its input
Sigil, reevaluates Ward against current approvals, and rejects duplicate
acceptance. Athanor then appends `agent-result.accepted` and projects an
`agent-result-record/1.0` with the Capability, Host, Capsule Sigil, artifacts,
status, timestamp, and Receipt.

Replay validates the embedded output contract without depending on the
non-canonical Capsule file. The accepted Result remains a proposal record until
a later, object-specific Athanor transition uses its artifacts.

## Inspection and aliases

`chronicle show|verify` exposes the verified event chain. `sigil show` resolves
objects, events, and Receipts; `sigil verify` computes a file-byte SHA-256
Sigil. Typed Trace forms such as `trace claim CL-001` coexist with the original
`trace CL-001`.

The RFC names `grimoire add|inspect`, `rite search|install|run`, and
`working list|inspect|resume` are available as local, inspectable operations.
Remote Grimoire sources remain disabled until publisher identity and signature
policy are defined.
