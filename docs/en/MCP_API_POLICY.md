---
language: en
canonical: true
---

# MCP API Policy

The Benchwork MCP server is the Phase 2 scientific control plane. It exposes
typed, bounded operations over canonical research state and deliberately does
not wrap Host-native file, patch, shell, Git, web, or review capabilities.

## Frozen surface

The public MCP names are the existing `benchwork_<verb>` names returned by
`tools/list`. Phase 2 freezes 38 names in four categories:

| Category | Count | Responsibility |
| --- | ---: | --- |
| Read | 9 | Status, projections, objects, traces, schemas, and doctor |
| Task | 4 | Open, inspect, complete, or fail a bounded Task |
| Canonical | 19 | Research proposals, Review provenance, and scientific Seals |
| Experiment | 6 | Working, Artifact, Experiment, Run, and Alembic operations |

The machine-readable registry introduced by M17 is the authoritative
inventory. Until it is present, the four registration modules are the
executable inventory.

New universal escape hatches are prohibited. In particular, Benchwork will not
add `benchwork_execute`, `benchwork_run_anything`, file-edit, shell, Git, or web
proxy tools.

## Stability

Every Phase 2 tool is `alpha`.

A breaking change includes:

- removing or renaming a tool;
- changing a read operation into a mutation;
- weakening an approval, Ward, Athanor, disclosure, or Seal boundary;
- changing the meaning of an existing request field, result field, error code,
  Receipt, or schema identifier;
- returning an unbounded or non-JSON-safe result where the contract was
  bounded and JSON-safe.

A breaking Alpha change requires an accepted RFC, a migration note, updated
contract tests, and replay coverage where persisted state is affected.
Additive optional fields and new tools are non-breaking only when old clients
continue to behave correctly.

## Requests and results

Tool input is defined by the MCP SDK input schema generated from the typed
runtime signature. Every domain result uses `mcp-tool-result/1.0`.

Successful results contain `ok`, `tool`, `schema_version`, `data`, `receipt`,
`warnings`, and `next_actions`. Failed results contain the same stable
identity plus a structured `error`. Results must not contain raw stack traces,
secrets, hidden reasoning, absolute project paths, non-finite numbers, or
unbounded collections.

Lists and traces use stable ordering and pagination. Missing, stale, damaged,
or unauthorized state fails closed.

## Mutation and approval

Read tools are non-mutating. Canonical changes pass through Athanor and return
Receipts. RQ, Protocol, and Decision Seals use immutable preview/commit pairs;
commit requires the preview identifier, preview Sigil, idempotency key, and
explicit confirmation token. Any relevant state change invalidates the
preview.

External Review approval is a separate disclosure grant. General Host,
network, CLI, or review permission does not satisfy it.

## Discovery

MCP `tools/list` and `tools/call` remain protocol operations implemented by
the MCP SDK/server. Benchwork does not expose meta-tools named `tools_list`,
`tools_call`, or `tools_schema`. Hosts discover input schemas through the
standard MCP tool descriptors.
