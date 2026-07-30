---
language: en
canonical: true
---

# Plugin API Policy

The Benchwork plugin is the Codex-native workflow and distribution layer over
the host-neutral Python runtime and MCP server. It owns reusable instructions,
Host integration, and defense-in-depth hooks; it does not own canonical
research state or scientific acceptance.

## Codex-owned contract

`.codex-plugin/plugin.json` contains only fields accepted by the current Codex
plugin manifest contract. Host discovery uses:

- the plugin manifest for identity, presentation, Skills, and MCP connection;
- `SKILL.md` for each Skill's native name, trigger description, and workflow;
- optional `agents/openai.yaml` for UI metadata and MCP dependency
  declarations;
- the bundled hook configuration for trusted lifecycle guardrails.

Benchwork does not add private fields such as `benchwork_api`, `min_runtime`,
or `skills_api` to the Codex manifest. Benchwork-owned compatibility metadata
belongs in a separately versioned and validated companion manifest.

Likewise, a per-Skill `skill.yaml` is Benchwork compatibility metadata, not a
replacement for `SKILL.md` or `agents/openai.yaml`.

## Frozen Phase 2 workflows

The seven Skill names are:

- `benchwork-orchestrate`
- `benchwork-investigate`
- `benchwork-design`
- `benchwork-implement`
- `benchwork-pilot`
- `benchwork-evaluate`
- `benchwork-resume`

Renaming or removing one is an Alpha breaking change. Refining instructions is
non-breaking only when the Skill retains its trigger boundary, required
approval points, canonical-state rules, and MCP dependencies.

## Version mapping

The Python distribution uses PEP 440, for example `0.3.0rc1`. The plugin uses
strict Semantic Versioning, for example `0.3.0-rc.1`. A local Codex cachebuster
may append build metadata without changing compatibility, for example
`0.3.0-rc.1+codex.<token>`.

The companion manifest pins the supported Benchwork API line, minimum runtime,
Skill metadata version, and MCP registry version. Its schema is versioned
independently.

## Security and lifecycle

- Plugin install, upgrade, rollback, and removal must not create, migrate,
  repair, or delete `.benchwork/`.
- Hooks are trusted defense in depth and never implement canonical state
  transitions.
- Direct canonical writes remain invalid even if hooks are disabled.
- Skills may request structured proposals but must not request, store, or
  expose hidden chain-of-thought.
- A Provider or subagent result remains advisory until Athanor accepts the
  bounded proposal and returns a Receipt.
- Scientific Seals and external disclosure require their own explicit human
  confirmation.

## Host portability

Codex-native files may evolve with Codex, but the MCP tools, Capability
contracts, Task outputs, Receipts, and canonical schemas remain Host-neutral.
Host-specific changes must not silently alter scientific semantics.
