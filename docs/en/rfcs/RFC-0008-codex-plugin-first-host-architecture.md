---
title: "RFC-0008: Codex Plugin-first Host Architecture"
document_id: BW-RFC-0008
version: 1.0
status: accepted
owner: Endofthestars
date: 2026-07-30
language: en
canonical: true
---

# RFC-0008: Codex Plugin-first Host Architecture

## Problem

Benchwork needs an interactive research experience without rebuilding the
repository, patch, shell, Git, web, review, planning, and user-approval
capabilities already provided by Codex. Launching another model process from
Benchwork would split context and weaken approval UX and observability.

## Decision

Codex is the interactive conductor and intelligent worker. The installable
unit is `plugins/benchwork/`, containing seven workflow Skills, a bundled
STDIO MCP connection, trusted lifecycle hooks, and templates. The Python
package remains the runtime and source of truth.

Codex native tools own repository reads, patches, shell, Git, web search, and
review. Benchwork MCP tools own typed reads and canonical operation requests.
Ward enforces Task boundaries. Athanor validates transitions. Chronicle stores
only accepted events and Receipts.

The repository-local marketplace is
`.agents/plugins/marketplace.json`. Plugin installation, update, disablement,
or removal has no canonical research-state effect.

## Invariants

- Native tools never write `.benchwork/`.
- Canonical changes pass through Benchwork MCP and Athanor.
- Agent Results remain proposals until accepted with a Receipt.
- RQ, Protocol, and Decision Seals require a fresh immutable preview and
  explicit human confirmation.
- Failed, cancelled, excluded, and negative Runs remain registered.
- Skills contain workflow policy, not canonical transition logic.
- Hooks are defense in depth and may never substitute for Ward or Athanor.
- Subagents are advisory and read-only unless a user explicitly delegates a
  separate mutation boundary.
- No scientific capability is bound to one provider or model.

## Compatibility and migration

The host-neutral Capability, Task Capsule, Agent Result, Snapshot, Sigil, and
Receipt contracts remain unchanged. Codex Host Session metadata is recorded as
provenance. Claude Code and future Hosts may use the same MCP control-plane
contract without adopting Codex Skills or hooks.

The plugin manifest uses `mcpServers: "./.mcp.json"`. Hooks are discovered from
the standard `hooks/hooks.json` location and therefore require no manifest
field. Project-scoped direct development uses `.codex/config.toml.example`.

## Security and integrity

Plugin hooks require explicit trust and have bounded time and output. They
block obvious native writes and destructive commands targeting `.benchwork/`,
but specialized tool paths may bypass hooks. Athanor therefore revalidates
every canonical transition.

MCP results contain stable envelopes, finite JSON values, project-relative
paths, bounded output, and cursor pagination. No response contains secrets,
conversation history, or hidden reasoning.

## Alternatives

- Background Provider launch: rejected for ordinary interactive work because
  it duplicates Codex and splits context.
- MCP wrappers for files, patches, shell, Git, or web: rejected because they
  reduce native capability and approval quality.
- Hooks as the canonical transition engine: rejected because PostToolUse
  cannot undo side effects and hook execution is optional.

## Non-goals

- HTTP transport, OAuth, or remote MCP deployment
- automatic model selection or Provider routing
- autonomous scientific Seals
- transcript parsing as a stable state API
- replacement of Alembic with model-computed statistics

## Acceptance tests

- Explicit and implicit skill-selection fixtures cover representative prompts.
- Plugin validation accepts the manifest and bundled MCP configuration.
- Install packaging does not read or mutate `.benchwork/`.
- In-memory and subprocess clients discover the same 33 tools.
- Direct native writes to `.benchwork/` are denied by hook fixtures.
- Disabling hooks does not weaken Athanor validation.
