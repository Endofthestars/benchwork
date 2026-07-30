# Benchwork Acceptance Exception Policy v0.1

Benchwork distinguishes product failures from unavailable Host surfaces and
properly denied disclosure. Neither exception may be rewritten as a passing
test, but neither automatically invalidates a lower acceptance tier.

## Host acceptance tiers

| Tier | Boundary | Release status | Required evidence |
| --- | --- | --- | --- |
| Tier 0 — Kernel | Core Runtime | Required and automated | Chronicle, Schema, Ward, Capability, MCP protocol and tool contracts, replay |
| Tier 1 — CLI Host | Codex CLI and Claude Code CLI | Required before a Phase release | interactive MCP discovery, representative Task loop, Athanor Receipt |
| Tier 2 — IDE Host | graphical IDE and desktop Hosts | Optional Host Validation | graphical lifecycle, interactive chat, MCP tool call |

Tier 0 runs without Claude, Codex, or an IDE. It is Benchwork's permanent trust
base. Tier 1 demonstrates the required interactive Host contract. Tier 2
depends on GUI, extension runtime, login state, and Host lifecycle that
Benchwork does not control.

An unavailable Tier 2 environment is recorded as `BLOCKED_BY_ENVIRONMENT`, not
`FAILED`. The record must include an exception identifier, reason, impact, and
the release boundary before which validation becomes required.

The current exception is:

```yaml
id: HOST-IDE-001
status: BLOCKED_BY_ENVIRONMENT
reason: No graphical IDE extension host is available.
impact: None on Core, MCP, or CLI acceptance.
required_before: Public IDE integration release.
```

The machine-readable policy is bundled as
[`host-capability-matrix.yaml`](../../../plugins/benchwork/assets/host-capability-matrix.yaml).

## External Review Disclosure Policy

Local Review reads the current worktree inside the approved project boundary.
It is read-only and does not disclose repository content to another provider.

External Review includes any workflow that uploads or transmits a diff, source
files, unpublished results, private data, or related repository information to
a remote reviewer. It requires explicit disclosure approval for the exact
Review Request. General permission to use a CLI, IDE, network, or review
feature is not disclosure approval.

The lifecycle is:

```text
Review Request -> Ward -> Disclosure Check -> Provider -> Review Artifact -> Acceptance
```

Benchwork records but does not execute the provider call. A Host may execute
the external review only when both conditions hold:

1. the `bench.review.external` Task passes Ward; and
2. the matching Review Request has a `review.approved` Receipt.

`review.completed` additionally requires the accepted Agent Result from that
same Task. The immutable Task Capsule binds `bindings.review_id`, the semantic
output repeats it, and the Review Artifact records the accepted `task_id`.

A request with `includes_credentials: true` is rejected rather than approved.
Without a non-empty `approved_by`, the Disclosure Gate remains
`WAITING_FOR_DISCLOSURE_AUTHORIZATION`.

The four Capability boundaries are:

- `bench.review.prepare`: create a bounded Review Request proposal;
- `bench.review.local`: perform a read-only local review;
- `bench.review.external`: perform the approved external review;
- `bench.review.accept`: accept a completed Review Artifact.

Chronicle records `review.requested`, `review.approved`, `review.completed`,
and `review.accepted`. Provider output remains advisory until the final
acceptance Receipt exists.

The request format is published as `review-request/1.0`, the canonical result
as `review-artifact/1.0`, and an editable example is bundled as
[`review-request-template.yaml`](../../../plugins/benchwork/assets/review-request-template.yaml).
When a Host needs a workspace-visible manifest, it may copy that template to
`.review/review-request.yaml`. This file is an operational request document,
not canonical state; only Chronicle events and Receipts establish approval.

## Host-neutral enforcement

Codex, Claude Code, and future Hosts use the same Disclosure Gate. A Host must
not infer approval from prior conversation, a broad execution authorization,
or an attempted provider call. A denied call is evidence that the boundary
worked; the Host records the pending status and continues with local review or
requests explicit disclosure authorization.
