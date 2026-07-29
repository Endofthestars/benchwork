---
language: en
canonical: true
---

# Athanor Foundation

## Authority boundary

The Athanor accepts only deterministic, local transitions. It writes a locked,
fsync-backed append-only Chronicle event and emits a content-addressed Sigil
Receipt for every accepted transition. Receipts form a hash chain, so mutation,
insertion, and reordering are detectable during replay. Agent output is a
Proposal, never a direct mutation.

## First projections

`program.created` creates a `Research Program` in `IDEA` state.
`protocol.drafted` requires an existing Program, a title, and a deterministic
analysis plan. Only a `DRAFT` Protocol can emit `protocol.sealed`, which moves
its Program projection to `DESIGN_FROZEN`; the projection records the seal time
and Receipt ID.

## Invariants

1. A Chronicle Receipt hashes every event field other than the Receipt itself.
2. Each event and its Receipt name the preceding event Sigil; replay verifies the whole chain.
3. Appends are serialized with an exclusive lock and committed with `fsync`.
4. Corrupt or altered events fail `bwork doctor` and all subsequent projections.
5. A Protocol Seal requires an existing DRAFT with a deterministic analysis plan.
6. The projection is rebuildable solely from Chronicle events.
7. Failed and future Run events will remain append-only; no event type implies deletion.

The next milestone adds explicit Gate policy and the full Experiment, Run,
Assessment, and Decision schemas.
