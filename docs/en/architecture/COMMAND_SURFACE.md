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

Each direct verb requires `--program`. It creates an immutable Research
Snapshot and pins the complete Capability Contract Sigil; there is no
creation-order or "latest Program" fallback. Tool, time, and network boundaries
default to the Capability contract and can be narrowed on the command line.
Ward evaluates every proposal. Write and execution Capabilities remain
`WAITING_FOR_APPROVAL` until a matching approval Receipt exists.

These verbs prepare bounded work; they do not claim that a Provider ran.
Automatic Provider invocation remains an open design decision.

## Agent Result acceptance

An Agent returns an `agent-result/1.1` Proposal. `bwork task accept FILE`
validates the result, reloads the immutable Task Capsule and Snapshot, rechecks
the Capability Contract Sigil and Program freshness, verifies each output Blob
Sigil and Capability-specific schema, reevaluates Ward, and rejects duplicate
acceptance. Athanor then appends `agent-result.accepted` and projects an
`agent-result-record/1.1` with the pinned boundaries, Host, outputs, available
runtime provenance, status, timestamp, and Receipt.

Replay validates the embedded output contract without depending on the
non-canonical Capsule file. The accepted Result remains a proposal record until
a later, object-specific Athanor transition uses its artifacts.

## Inspection and aliases

`chronicle show|verify` exposes the verified event chain. `chronicle recover`
inspects or accepts only a valid uncommitted tail, and `migrate
chronicle-v1.0-to-v1.1` performs the explicit backed-up ledger migration.
`sigil show` resolves objects, events, and Receipts; `sigil verify` computes a
file-byte SHA-256 Sigil. Typed Trace forms such as `trace claim CL-001`
coexist with the original `trace CL-001`.

The RFC names `grimoire add|inspect`, `rite search|install|run`, and
`working list|inspect|resume` are available as local, inspectable operations.
Remote Grimoire sources remain disabled until publisher identity and signature
policy are defined.
