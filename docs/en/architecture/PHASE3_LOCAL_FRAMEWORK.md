---
language: en
canonical: true
---

# Phase 3 local framework

Status: **experimental scaffold, not Phase 3 acceptance**.

`LocalSanctumRuntime` is an in-memory conformance aid that models a bounded
Job/Lease lifecycle without executing commands. It uses the independent
`sanctum-local-*/0.1` records, not the RFC-0012 `execution-*/1.0` contracts or
the production-facing local-execution contracts. It can issue a bounded
`sanctum-local-worker-result/0.1` Proposal, but it cannot create a scientific
Run, Artifact, Assessment, or Decision. Only a separately authorised Athanor
transition may do that.

## Implemented framework boundary

- Task Capsule and Circle Sigils are bound when a Job is submitted.
- A Job has a fenced, expiring Lease and a monotonic local lifecycle.
- Expired Leases fail closed; stale completion is rejected.
- Worker outputs are schema-bounded Proposals.
- `sanctum-local-patch-proposal/0.1` records a patch's base and validation
  evidence; it does not apply or promote the patch.

## Explicitly deferred

The following are intentionally `DEFERRED`, not implied by this framework:

| Capability | Status |
| --- | --- |
| Process, container, filesystem, and network execution | `DEFERRED` |
| Remote Workers and transport | `DEFERRED` |
| Queueing, scheduling, quotas, and GPU allocation | `DEFERRED` |
| Persistent or production Artifact Storage | `DEFERRED` |
| Automatic patch application or promotion | `DEFERRED` |
| Automatic conversion of a Worker Result into science | `FORBIDDEN` |

These features require the corresponding Phase 3 RFC, threat model, and
conformance evidence before implementation.
