---
language: en
canonical: true
---

# Host Support Matrix

Benchwork grades Host acceptance separately from Kernel and MCP correctness.
An unavailable optional Host is an explicit exception, not a failed lower
tier.

## Acceptance tiers

| Tier | Boundary | Phase 2 release rule |
| --- | --- | --- |
| Tier 0 — Kernel | Chronicle, Schema, Ward, Capability, replay | Required; automated |
| MCP | STDIO protocol, discovery, tool contracts, envelopes | Required; automated |
| Tier 1 — CLI Host | Declared primary interactive CLI Host | Required |
| Tier 2 — IDE Host | Graphical IDE or desktop Host | Optional; environment exception allowed |

Tier 1 is evaluated per declared release Host. Codex CLI is the primary Phase
2 Host. Host-neutral compatibility with another CLI is not the same as an
interactive PASS for that Host.

## Current acceptance

| Host or boundary | Tier | Status | Phase 2 effect |
| --- | --- | --- | --- |
| Core Runtime | 0 | PASS | Required gate satisfied |
| MCP STDIO | MCP | PASS | Required gate satisfied |
| Codex CLI | 1 | PASS | Primary CLI gate satisfied |
| Claude Code CLI | 1 | PENDING_HOST_VALIDATION | Host-neutral contract only; not a claimed interactive PASS |
| Codex IDE extension | 2 | BLOCKED_BY_ENVIRONMENT | Accepted exception `HOST-IDE-001` |
| Claude Desktop | 2 | OPTIONAL_NOT_RUN | No Phase 2 release impact |
| External Review | disclosure | WAITING_FOR_DISCLOSURE_AUTHORIZATION | Correctly denied; not a failure |

## HOST-IDE-001

```yaml
id: HOST-IDE-001
status: BLOCKED_BY_ENVIRONMENT
owner: Benchwork release owner
reason: No graphical IDE extension host is available on the acceptance machine.
impact: None on Kernel, MCP, or Codex CLI acceptance.
required_before: Public Codex IDE integration release.
```

Reproduction and closure:

1. Use a machine with a display, authenticated Codex IDE extension, and the
   Benchwork plugin installed from a fresh local marketplace.
2. Open a new IDE conversation in a Benchwork project.
3. Explicitly select `$benchwork-orchestrate`, then issue a representative
   implicit orchestration request.
4. Verify the IDE discovers the same MCP tool names as Codex CLI.
5. Open and complete a bounded Task and retain the Athanor Receipt.
6. Record Host version, plugin version, tool count, Receipt identifier, and
   any exception without copying secrets or conversation reasoning.

## Evidence policy

PASS requires a dated, reproducible Host trial. Contract inspection or shared
configuration alone is insufficient. `BLOCKED_BY_ENVIRONMENT` requires an
identifier, owner, reason, impact, reproduction steps, and the boundary before
which it must be closed.

See the [Phase 2 acceptance matrix](PHASE2_ACCEPTANCE.md) and
[Acceptance Exception Policy](plugins/acceptance-exception-policy.md).
