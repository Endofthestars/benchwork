---
title: "RFC-0001: Chronicle and Receipt Protocol"
document_id: BW-RFC-0001
version: 1.0
status: accepted
owner: Endofthestars
date: 2026-07-29
language: en
canonical: true
---

# RFC-0001: Chronicle and Receipt Protocol

## Status

This RFC defines the M10 integrity boundary for `chronicle-event/1.1`,
`receipt/1.1`, and `chronicle-head/1.1`. It supersedes the integrity mechanics
of Chronicle v1.0 without deleting the published v1.0 contracts.

## Decision

Chronicle is an append-only JSONL ledger. Each accepted transition has two
separately verifiable content identities:

1. `event_body_sigil` identifies every Event field except
   `event_body_sigil` and `receipt`.
2. `receipt_sigil` identifies every Receipt field except `receipt_sigil`.

Chronicle order is expressed by contiguous `sequence` numbers and a
`previous_receipt_sigil` chain. The independently persisted head records the
event count and terminal Receipt Sigil.

## Event body

An Event body contains:

```text
schema_version
event_id
sequence
type
object_id
occurred_at
previous_receipt_sigil
actor
payload
```

The canonical JSON encoding uses sorted keys, ASCII escapes, compact
separators, and rejects non-finite numbers. SHA-256 over those bytes produces
`event_body_sigil`.

## Receipt

A Receipt contains:

```text
schema_version
receipt_id
event_id
event_body_sigil
previous_receipt_sigil
accepted_at
```

SHA-256 over the same canonical encoding produces `receipt_sigil`. Receipt
identity therefore covers `receipt_id`, `accepted_at`, and every binding field.

## Invariants

For every Event:

- the Event and Receipt pass their Draft 2020-12 Schemas with format checking;
- unknown Event, Actor, Receipt, and Head fields are rejected;
- `sequence` starts at 1 and increases by exactly one;
- Event and Receipt `previous_receipt_sigil` values match the prior Receipt;
- the first Event has a null previous Receipt Sigil;
- `receipt.event_id == event.event_id`;
- `receipt.event_body_sigil == event.event_body_sigil`;
- `receipt.accepted_at == event.occurred_at`;
- both computed Sigils match their stored values.

The Head must equal:

```json
{
  "schema_version": "chronicle-head/1.1",
  "event_count": 1,
  "terminal_receipt_sigil": "sha256:..."
}
```

## Actor

Every transition records an Actor with an ID, type, Host, and authentication
mechanism. M10 uses `local-session` as the minimum authentication statement.
This is audit provenance, not cryptographic identity.

## Commit protocol

Within the Chronicle lock, Athanor:

1. verifies the ledger and Head;
2. builds and validates the proposed transition;
3. appends and fsyncs the complete Event line;
4. atomically replaces and fsyncs the Head.

A crash between steps 3 and 4 leaves a valid tail that recovery may accept. No
other mismatch is automatically repaired.

## Recovery

`bwork chronicle recover --dry-run` reports whether the ledger contains a
recoverable tail. `--accept-valid-tail` updates only the Head and only when:

- the prefix committed by the old Head remains valid;
- the tail is a contiguous, schema-valid append;
- no Event was removed or rewritten;
- complete Athanor projection replay succeeds.

Recovery never edits `chronicle.jsonl`.

## Migration

`bwork migrate chronicle-v1.0-to-v1.1` is an explicit, offline migration. It:

- rejects mixed, malformed, or already-v1.1 ledgers;
- verifies the complete v1.0 ledger and Head;
- preserves Event order, type, object ID, timestamps, and payloads;
- assigns contiguous sequences and the local migration Actor;
- creates a backup before atomic replacement;
- emits a machine-readable migration report;
- verifies that pre- and post-migration scientific projections are equal.

Receipt and Event IDs are preserved. Sigils and chain references necessarily
change because v1.1 covers more data.

## Compatibility

The v1.0 Schemas remain published for inspection and migration. A project uses
one Chronicle protocol version at a time. New M10 projects write v1.1.
Automatic mixed-version replay is forbidden.
