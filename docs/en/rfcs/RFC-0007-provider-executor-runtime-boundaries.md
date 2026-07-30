---
title: "RFC-0007: Provider and Executor Runtime Boundaries"
document_id: BW-RFC-0007
version: 0.2
status: accepted
owner: Endofthestars
date: 2026-07-29
language: en
canonical: true
---

# RFC-0007: Provider and Executor Runtime Boundaries

## Status

This RFC authorizes no automatic Provider invocation, remote transport,
cluster execution, or autonomous research loop. Phase 2 adds an implemented
Review disclosure boundary without authorizing Benchwork to launch a Provider.

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

## Phase 2 external Review amendment

Codex, Claude Code, and future Hosts keep Review local by default. A Host may
transmit repository content to an external reviewer only when the exact Review
Request has a disclosure approval Receipt and the `bench.review.external` Task
passes Ward. General Host, network, execution, IDE, or scientific Seal approval
does not authorize disclosure.

Benchwork records `review.requested`, `review.approved`, `review.completed`,
and `review.accepted`, but does not execute the provider call. Requests that
include credentials fail closed. The completed Review Artifact remains
advisory until explicitly accepted. Completion is valid only when the
Artifact's `task_id` resolves to an accepted Agent Result whose immutable Task
Capsule binds the same `review_id`.

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
- automatically uploading repository content for Review.

## Entry gate

Any future automatic Provider or remote Executor implementation still requires
a new RFC version specifying executable schemas, threat model, and conformance
tests.
