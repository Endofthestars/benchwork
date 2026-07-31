---
language: en
canonical: true
---

# Roadmap

## M0: Foundation

Completed: repository structure, RFC-0000, public terminology, and project governance.

## M1: Athanor

Completed: a local Chronicle with chained receipts, replayed projections,
Protocol drafting and sealing, and a Schema-validated CLI. The published Schema
contracts define scientific objects before provider integration begins.

## M2: Circle

Completed: local Capability registration, Task Capsule validation, Circle
boundaries, Ward evaluation, and canonical human approval receipts. Agent
Results remain proposals until accepted by Athanor.

## M3: Twin Gate

Completed: symmetric Codex and Claude Code Host adapters, both operating
through the same Capability contracts and local canonical state.

## M4: First Rite

Completed: `computational-study@0.1.0` and its protocol-bound Working state
machine.

## M5: Alembic

Completed: canonical Experiment and Run provenance plus schema-validated
`result-bundle/1.1` deterministic descriptive aggregation.

## M6: Open Grimoire

Completed for public Alpha: local, data-only Grimoire manifests; exact API and
SemVer pins; canonical Rite Sigils; collision and path-escape protection; and
Working execution from copied, inspectable definitions.

## M7: Scientific Canon

Completed: sourced and monotonically verified Evidence; explicit Claim
relations; Claim-backed, Protocol-registered Hypotheses; Result Bundle
Assessments; human-Sealed Decisions; and cross-object Chronicle lineage.

## M8: Integrity and Recovery

Completed: canonical, content-addressed Artifacts with producer and input
lineage; open-to-resolved research Issues; and immutable Deviations that record
post-Seal changes without rewriting the Protocol commitment.

## M9: Command Surface and Agent Handoff

Completed: all RFC Capability contracts; direct research verbs that create
Ward-checked Task Proposals; canonical Agent Result acceptance bound to the
original Capsule and input Sigil; Chronicle and Sigil inspection; and the
documented Grimoire, Rite, Working, Seal, and typed Trace command forms.

## M10: The Seal

Release candidate implemented: Phase 1 hardening for Receipt integrity,
state-bound Tasks, explicit scientific Gates, canonical Working and Run
lifecycles, registered Alembic comparisons, deterministic CLI project context,
governance, and golden release acceptance. Automatic Provider execution remains
outside M10. Final acceptance requires the complete stacked CI suite to pass.

## M11: The Grimoire

Implemented: Codex Plugin-first RFCs, the repository marketplace, seven
trigger-specific Skills, and concise repository agent rules.

## M12: The Instrument

Implemented: `bwork mcp serve`, STDIO transport, server instructions, stable
response envelopes, cursor pagination, and read-only project tools.

## M12.5: Host Boundary Verification

Implemented: tiered Kernel, CLI, and IDE Host acceptance; a machine-readable
Host capability matrix; environment-blocked IDE exceptions that do not weaken
Core/MCP gates; and a host-neutral external disclosure policy.

## M13: The Familiar

Implemented: the interactive Task open/get/complete/fail loop with automatic
semantic output blobs, Sigils, Host Session provenance, Athanor acceptance, and
same-session Receipts.

## M13.5: Review Provenance

Implemented: local and external Review Capability boundaries, Review Request
and Review Artifact Schemas, a fail-closed disclosure Gate, and Chronicle
events for request, approval, completion, and acceptance. Benchwork records
Review provenance but does not invoke or upload content to a provider.

## M14: The Wards

Implemented: trusted SessionStart, PreToolUse, and PostToolUse hooks with
bounded output, direct `.benchwork/` write protection, and adversarial fixtures.

## M15: The Working

Implemented: canonical scientific write tools, immutable preview/commit Seals,
Experiment and Run tools, deterministic Alembic invocation, and specialized
implementation, pilot, evaluation, and recovery Skills.

## M16: Trial of the Familiar

Prerelease candidate: local marketplace packaging, plugin and Skill validation,
in-memory and spawned-STDIO protocol tests, and the Phase 2 acceptance matrix.
Codex CLI acceptance is complete. IDE validation is an accepted
`BLOCKED_BY_ENVIRONMENT` Tier 2 exception until a graphical extension Host is
available; external diff review remains
`WAITING_FOR_DISCLOSURE_AUTHORIZATION`.

## M17: The Instrumentarium Seal

Completed for `0.3.0rc1`: Phase 2 API and protocol freeze; 38-tool
machine-readable MCP Registry; versioned Plugin and Skill compatibility
metadata; Host Support Matrix; Review Disclosure Policy; deterministic golden
audit-to-`REPAIR` acceptance; migration and release documentation; and
release-gated CI coverage.

Phase 2 is sealed with Kernel, MCP, Plugin, and Codex CLI gates passing.
`HOST-IDE-001` remains an accepted `BLOCKED_BY_ENVIRONMENT` Tier 2 exception
and External Review remains `WAITING_FOR_DISCLOSURE_AUTHORIZATION`. These
states are not reclassified as failures or fabricated PASS results.

Claude Code CLI was `PENDING_HOST_VALIDATION` at the rc1 seal and recorded its
own Tier 1 PASS on 2026-07-31, after its trial found and repaired a Task
Capsule Host defect. See the
[Host Support Matrix](HOST_SUPPORT_MATRIX.md).

## M18: The Invitation

Implemented for `0.3.0rc2`: an auditable POSIX installer; exact release and
channel manifests; uv-first and pipx-isolated bootstrap; installation-level
diagnostics; safe versioned plugin staging; opt-in Codex and experimental
Claude MCP setup; PATH, repair, rollback, and uninstall ownership; release
assets, SBOM, provenance, Pages publication, and installer CI.

M18 does not change the Phase 2 scientific state machine. Installer operations
must continue to report `Project state: NOT_TOUCHED`.

Phase 3 — The Sanctum may now begin through new RFCs for sandboxing,
filesystem isolation, execution policy, patch promotion, experiment executors,
GPU/remote jobs, and Artifact storage. Phase 3 must not weaken the frozen
Phase 2 scientific control-plane boundary.
