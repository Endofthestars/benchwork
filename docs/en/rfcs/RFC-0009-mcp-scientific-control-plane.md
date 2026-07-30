---
title: "RFC-0009: MCP as the Scientific Control Plane"
document_id: BW-RFC-0009
version: 1.0
status: accepted
owner: Endofthestars
date: 2026-07-30
language: en
canonical: true
---

# RFC-0009: MCP as the Scientific Control Plane

## Problem

RFC-0007 reserved a future Provider and Executor boundary. It did not define
how an already-running interactive Host should read and change Benchwork state.
Treating MCP as another Provider layer would duplicate Codex-native execution
and blur the proposal/canonical boundary.

## Decision

MCP is the host-neutral scientific control plane. `bwork mcp serve` exposes
STDIO tools for canonical reads, bounded Tasks, scientific objects,
preview/commit Seals, Experiment facts, Runs, and Alembic analysis.

MCP does not launch a model, execute research shell commands, edit repository
files, perform Git operations, or search the web. The interactive Host performs
those actions and submits structured facts or proposals.

This amends RFC-0007 for interactive use: ordinary Codex sessions do not use a
Benchwork-launched Provider or Executor. RFC-0007 remains applicable to a
future non-interactive remote Executor.

## Invariants

- Every tool returns `mcp-tool-result/1.0`.
- Errors reuse stable CLI codes when semantics match and never return a stack
  trace.
- Read tools are non-mutating and damaged state fails closed.
- Task completion validates the Capability output, creates and hashes the
  project-relative blob, binds Host Session provenance, and submits one Agent
  Result to Athanor.
- Seal previews bind the operation, arguments, Chronicle head, content Sigil,
  Gate result, and confirmation token.
- Any canonical event invalidates an outstanding preview.
- Commit calls require preview ID, preview Sigil, idempotency key, and the exact
  confirmation token.
- Alembic computes registered statistics; Codex only interprets its Result
  Bundle.

## Compatibility and migration

Phase 2 supports STDIO only. The server uses the official Python MCP SDK v2 for
tool schemas, in-memory transport, metadata, and dispatch. A small asyncio pipe
binding works around the SDK 2.0.0 Python 3.13 piped-STDIO stall while retaining
newline-framed MCP JSON-RPC compatibility.

Adding HTTP or remote transport requires a new RFC version and does not alter
the canonical tool semantics.

## Security and integrity

Server instructions place the native-tool/canonical-state boundary in the
first 512 characters. Project discovery is explicit and paths returned to the
Host are project-relative. Preview and idempotency records are operational
state under `.benchwork/mcp/`; Chronicle remains the canonical source.

## Alternatives

- CLI text scraping: rejected as the public MCP contract.
- direct Chronicle mutation: rejected because it bypasses Athanor.
- one generic `benchwork_execute` tool: rejected because typed names and
  schemas improve selection, approval, and auditability.

## Non-goals

- scientific judgment inside the MCP server
- general filesystem or command tools
- secret storage
- remote authentication
- chain-of-thought capture

## Acceptance tests

- Every tool advertises a typed input schema.
- Read results paginate and maintain stable ordering.
- Semantic Task output is accepted and visible with its Receipt.
- Fresh Seal commits are idempotent.
- Stale Seal previews fail with `STALE_PREVIEW`.
- A spawned STDIO client initializes, lists all tools, and calls
  `benchwork_status`.
