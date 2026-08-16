---
language: en
canonical: true
---

# Phase 3 local framework

Status: **experimental scaffold, not Phase 3 acceptance**.

The first Phase 3 slice defines operational execution state without executing
commands. `LocalSanctumRuntime` is an in-memory conformance aid that manages
versioned `execution-job/1.0` and `execution-lease/1.0` records. It can issue a
bounded `worker-result/1.0` Proposal, but it cannot create a scientific Run,
Artifact, Assessment, or Decision. Only a separately authorised Athanor
transition may do that.

## Implemented framework boundary

- Task Capsule and Circle Sigils are bound when a Job is submitted.
- A Job has a fenced, expiring Lease and a monotonic local lifecycle.
- Expired Leases fail closed; stale completion is rejected.
- Worker outputs are schema-bounded Proposals.
- `patch-proposal/1.0` records a patch's base and validation evidence; it does
  not apply or promote the patch.

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
