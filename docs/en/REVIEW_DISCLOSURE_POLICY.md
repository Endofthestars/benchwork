---
language: en
canonical: true
---

# Review Disclosure Policy

Code review is advisory work with an explicit information boundary. Benchwork
records the request, authorization, provenance, result, and acceptance; it
does not silently transmit source code or make a reviewer authoritative over
scientific state.

## Review classes

### Local Review

Local Review stays inside the trust boundary already authorized for the
current interactive Host and project. It may inspect the worktree, patch,
tests, and architecture read-only. “Local” does not claim that a hosted Agent
model runs on-device; it means the review introduces no additional provider,
destination, export, or disclosure beyond the active Host session.

The Host opens `bench.review.local`, performs the review, completes the bound
Task, and records the Review Artifact. Local review never grants source-write
or scientific-Seal permission.

### External Review

External Review sends material to a destination outside the current Host trust
boundary. The material may include a private diff, source files, unpublished
algorithms, data structures, user data, or experimental results.

External Review requires explicit disclosure authorization for the exact
Review Request. Permission to use Codex, Claude, a CLI, an IDE, the network, a
test command, or a local review is not external disclosure authorization.

Benchwork forbids automatic upload of:

- source or private diffs;
- private or identifying data;
- unpublished experimental results; or
- credentials or secret values.

A request declaring credentials is rejected and cannot be approved through
the normal disclosure gate.

## Canonical lifecycle

```text
Review Request
  -> Disclosure Gate
  -> approved external Task
  -> Host/provider execution
  -> accepted Task result
  -> Review Artifact
  -> explicit Review acceptance
```

The lifecycle is represented in Chronicle:

| Event | Meaning |
| --- | --- |
| `review.requested` | Exact target, scope, disclosure flags, and destination recorded |
| `review.approved` | A named human approved that exact external disclosure |
| `review.completed` | Bound Task result was accepted and its advisory Review Artifact recorded |
| `review.accepted` | A human accepted the Review Artifact for the recorded rationale |

`review.completed` requires the accepted Agent Result from the same Task. The
immutable Task Capsule binds `review_id`, the semantic output repeats it, and
the Review Artifact records the accepted `task_id`. A Review Artifact cannot
be manufactured from provider text alone.

## Required Review Request fields

`review-request/1.0` records:

- `review_id` and `program_id`;
- review type;
- repository, commit, and exact files;
- requested checks and bounded scope;
- source, private-data, credential, and unpublished-result disclosure flags;
- execution class and provider destination; and
- approval status, approver, time, and rationale.

The editable
[`review-request-template.yaml`](../../plugins/benchwork/assets/review-request-template.yaml)
may be copied to `.review/review-request.yaml`. That operational file is not
canonical state and is safe to delete or regenerate. Only Athanor Receipts and
Chronicle events prove authorization.

## Host policy

| Host action | Allowed without a new disclosure grant? |
| --- | --- |
| Read-only review inside the already authorized Codex session | Yes |
| Read-only review inside the already authorized Claude session | Yes |
| Send a diff to another Codex/Claude session, model, account, or service | No |
| Invoke a third-party remote reviewer | No |
| Export a Review Request with no source payload | Yes, within the project boundary |
| Upload credentials | Never |

Codex and Claude are examples of Hosts or destinations, not special authority
classes. The same policy applies to any Provider.

## Pending authorization is an accepted state

`WAITING_FOR_DISCLOSURE_AUTHORIZATION` means the gate correctly withheld
private material. It is neither `FAILED` nor a license to retry through another
tool. The Host may continue with Local Review, narrow the requested disclosure,
or ask the user to authorize the exact request.

External Review is optional for the Phase 2 release. Local review, Kernel, MCP,
and primary CLI acceptance remain independently valid.
