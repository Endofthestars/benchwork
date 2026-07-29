---
title: "RFC-0002: Capability, Snapshot, and Task Protocol"
document_id: BW-RFC-0002
version: 1.0
status: accepted
owner: Endofthestars
date: 2026-07-29
language: en
canonical: true
---

# RFC-0002: Capability, Snapshot, and Task Protocol

## Status

This RFC defines the M10 task boundary formed by `capability-contract/1.0`,
`research-snapshot/1.0`, `task-capsule/1.1`, and `agent-result/1.1`. It
supersedes the single-input boundary in Task Capsule v1.0.

## Decision

A Task is valid only against a pinned Capability Contract and an immutable
snapshot of one Research Program. Provider execution remains outside Athanor.
Claude Code and Codex are symmetric Hosts and submit the same Agent Result
contract.

## Capability identity

Each Capability Registry entry declares a `contract_version`, Circle limits,
approval policy, and one or more expected output schemas. Its Contract Sigil is
the canonical content Sigil of:

```json
{
  "id": "bench.study.audit",
  "contract": {
    "contract_version": "1.0",
    "allowed_tools": ["read"],
    "network": false,
    "max_time_seconds": 900,
    "requires_approval": false,
    "expected_outputs": [{"schema": "study-audit-result/1.0"}]
  }
}
```

The Task Capsule stores the Capability ID, Contract Version, and Contract
Sigil. Ward and Agent Result acceptance reload the Registry and require the
same Contract Sigil. Additive or mutating Registry changes therefore cannot
silently alter an existing Task.

## Research Snapshot

A Research Snapshot records:

- the Program ID;
- the Chronicle Head Receipt Sigil at creation;
- the sorted set of canonical Program objects and their content Sigils;
- the creation timestamp.

The Snapshot Sigil is the content Sigil of the complete Snapshot document and
is stored in the Task Capsule. Snapshot files are immutable.

Freshness compares the pinned set of `(object_id, object_type, object_sigil)`
tuples with a new projection of the same Program. The recorded Chronicle Head
must remain an ancestor of the current verified chain, but Head equality is not
the freshness rule. This distinction allows a Task approval or unrelated
Program event to be appended without making the Task stale.

Any addition, removal, or content change to an object in the Task's Program
makes its Result stale. M10 rejects stale Results; no merge policy is defined.

## Task Capsule

Task Capsule v1.1 binds:

- one explicit Program;
- a non-empty objective;
- one Host;
- the pinned Capability identity;
- the pinned Snapshot identity;
- expected output schemas copied from the Capability Contract;
- Circle tool, time, and network bounds.

The Capsule Sigil covers every field except itself. Direct phase commands must
receive an explicit Program or use an explicitly configured active Program.
Creation time, dictionary order, or "last Program" selection conveys no
authority.

## Approval

An approval records the Capsule Sigil and Capability Contract Sigil. Ward
requires both to match the Capsule and the current Registry. Approval does not
replace Snapshot freshness validation.

## Agent Result

Agent Result v1.1 repeats the Snapshot and Capability Contract Sigils. Each
output declares a schema, URI, and byte-level Blob Sigil. `COMPLETED` requires
at least one output; `FAILED` and `CANCELLED` may have none.

Acceptance requires:

1. the Agent Result schema is valid;
2. the Task Capsule and Snapshot are intact;
3. Result and Capsule Sigils match;
4. the current Capability Contract Sigil still matches;
5. the Program Snapshot is fresh;
6. Ward passes;
7. every output schema is expected by the Capability;
8. each referenced output exists, matches its Blob Sigil, and validates
   against its declared installed schema.

Acceptance records Host plus any supplied Provider, model, runtime, and
invocation provenance. Such provenance describes execution; it does not grant
scientific authority.

## Compatibility

Published v1.0 contracts remain available for inspection. New M10 Tasks use
v1.1. Existing v1.0 Tasks may be read but cannot be accepted through the v1.1
path because they lack a complete Snapshot and pinned Capability Contract.
There is no lossy automatic Task upgrade.
