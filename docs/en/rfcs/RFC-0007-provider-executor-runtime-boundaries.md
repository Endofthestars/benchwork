---
title: "RFC-0007: Provider and Executor Runtime Boundaries"
document_id: BW-RFC-0007
version: 0.1
status: design-only
owner: Endofthestars
date: 2026-07-29
language: en
canonical: true
---

# RFC-0007: Provider and Executor Runtime Boundaries

## Status

This RFC is design-only during M10. It authorizes no automatic Provider
invocation, remote transport, cluster execution, or autonomous research loop.

## Boundary

A Host translates between a Provider-facing interaction and Benchwork
contracts. A Provider may propose an `agent-result/1.1`. An Executor may later
run a Ward-approved Task Capsule inside an enforced Circle. Neither component
may append Chronicle events or mutate canonical projections.

Athanor remains the only canonical transition authority. Chronicle remains the
research-state source. Provider output remains a Proposal until Athanor
rechecks the pinned Capability contract, Snapshot freshness, expected output
schemas, Blob Sigils, approval binding, and runtime provenance.

## Symmetry

Codex and Claude Code use the same Capability, Capsule, Result, and approval
contracts. Provider-specific metadata belongs only in provenance. No Host may
receive a scientific transition unavailable to the other Host under the same
contract.

## Future Executor contract

A future Executor design must define leases, cancellation, timeouts, isolated
filesystem and network enforcement, logs, terminal job states, result
transport, retry identity, and crash recovery. Executor Job state must remain
separate from immutable scientific Run state.

## Trust and failure

Provider text is untrusted input. Executor success does not imply scientific
acceptance. Transport retries must be idempotent, stale Results must fail
closed, and loss of runtime provenance must never be silently reconstructed
from conversation state.

## Non-goals

- implementing a Provider client;
- selecting or routing models;
- distributed scheduling;
- remote Grimoire execution;
- automatically converting Agent output into Claims, Protocols, or Decisions.

## Entry gate

Implementation may begin only after all M10 acceptance checks pass and a new
RFC version specifies executable schemas, threat model, and conformance tests.
