---
language: en
canonical: true
---

# Roadmap

## Strategic direction

Benchwork is evolving from a trusted scientific control plane into a trusted
execution platform, then into a research operating system and an infrastructure
ecosystem.

```text
Trusted Research Control Plane
    -> Trusted Research Execution Platform
    -> Research Operating System
    -> Research Infrastructure
```

The roadmap is capability-gated rather than date-driven. A phase advances only
when its contracts, failure behavior, and acceptance evidence are complete.
Adding more Skills, Agents, or prompts is not a strategic milestone by itself.
The durable advantages are trusted state, safe execution, reproducibility,
scientific lineage, and a governed extension ecosystem.

## Current baseline

- Phase 2 was sealed by M17 in `0.3.0rc1` as
  `PASS_WITH_ACCEPTED_EXCEPTIONS` and `FROZEN_ALPHA`. Kernel, MCP, Plugin, and
  Codex CLI gates passed. Claude Code CLI remains
  `PENDING_HOST_VALIDATION`.
- `main` is prepared as the `0.3.0rc2` candidate. M18 installer implementation
  is present, but the exact `v0.3.0rc2` tag and retained installer acceptance
  evidence are still pending. Its acceptance decision remains `REPAIR`.
- The Phase 2 contracts remain Alpha. Existing identifiers must never be
  silently reinterpreted, but breaking Alpha changes remain possible through
  an accepted RFC, migration guidance, and replay or contract coverage.
- Phase 3's RFC gate is open. No current release claims executor-enforced
  isolation, remote jobs, GPU scheduling, or a production Artifact store.

See the [Phase 2 acceptance matrix](PHASE2_ACCEPTANCE.md),
[Compatibility Policy](COMPATIBILITY.md), and
[Installer RC acceptance](install/ACCEPTANCE.md) for the normative status.

## Non-negotiable boundaries

- Athanor remains the only authority for canonical transitions. Agent,
  Provider, Executor, and Observatory outputs remain Proposals until Athanor
  accepts them and issues a Receipt.
- Chronicle remains the canonical research source. Research Graphs, memory,
  indexes, and recommendations must be rebuildable projections.
- Executor Job state is separate from immutable scientific Run state. A
  successful Job does not automatically create a Run, Artifact, Assessment, or
  Decision.
- Failed Jobs, Attempts, patches, Runs, negative results, Deviations, and open
  Issues remain part of the record.
- Human confirmation remains mandatory for RQ, Protocol, and Decision Seals.
- The MCP control plane does not gain a universal shell, filesystem, Git, web,
  or `execute anything` escape hatch.
- Third-party executable code is not trusted merely because it is packaged as
  a Plugin or Grimoire.

## Evolution

| Release line | Phase | Codename | Strategic capability |
| --- | --- | --- | --- |
| `0.1` | Phase 0 | Foundation | Project language, governance, and initial contracts |
| `0.2` | Phase 1 | Athanor Kernel | Deterministic scientific state and provenance |
| `0.3.0rc1` | Phase 2 | Instrumentarium | Sealed host-neutral scientific control-plane baseline |
| post-rc1 `0.3.x` | Phase 2.5 | Consolidation | Long-lived control-plane foundation |
| `0.4` | Phase 3 | Sanctum | Experimental trusted-execution contracts and reference runtime |
| `0.5` | Phase 4 | Forge | Production-grade experiment runtime |
| `0.6-0.7` | Phase 5 | Observatory | Research-state intelligence |
| `0.8` | Phase 6 | Grimoire Ecosystem | Trusted research extension ecosystem |
| `1.0` | Phase 7 | Research Runtime | Complete Research Operating System |
| `2.0` | North star | Research Infrastructure | Product form defined from post-1.0 evidence |

## Phase 2.5 — Consolidation (`0.3.x`)

### Objective

Make the Phase 2 control plane a durable foundation before expanding the
execution surface.

### Capability gates

1. **Release closure**
   - Complete the exact `v0.3.0rc2` installer acceptance across its declared
     platforms and backends.
   - Run equivalent source-state gates on pull requests and `main`, validate
     immutable candidate assets from the exact tag, and complete public-URL
     smoke tests after publication but before channel promotion or final
     acceptance.
   - Retain release assets, checksums, SBOM, provenance, rollback, uninstall,
     and `Project state: NOT_TOUCHED` evidence.

2. **Alpha contract baseline**
   - Maintain the existing Alpha policy rather than claiming Stable
     compatibility.
   - Add machine-checkable baselines for the 38 MCP tools, seven Skills,
     published Schema identifiers, Capability identifiers, old request/result
     fixtures, and Chronicle replay.
   - Require an accepted RFC, migration guidance, and compatibility evidence
     for every breaking Alpha change.

3. **Claude Host acceptance**
   - Preserve the existing Host-neutral Capability, Capsule, Result, approval,
     and Receipt contracts.
   - Complete a real Claude Code CLI trial covering discovery, a bounded Task
     lifecycle, Seal/actor provenance, Athanor acceptance, and retained
     evidence before claiming Host parity.

4. **Declarative developer experience**
   - Expand `CONTRIBUTING.md` and publish a Developer Guide, declarative Plugin
     SDK, Capability SDK, and validation workflow for Capability contracts,
     data-only Rites, Skills, and Host packaging.
   - Provide clean-project examples and conformance checks that a third party
     can run without editing the Benchwork kernel.
   - Keep arbitrary executable Worker, Storage, and Executor adapters outside
     the `0.3.x` SDK.

5. **Research dogfood**
   - Complete independent Paper Reproduction, Model Improvement, and Research
     Direction Discovery cases.
   - Each case must preserve inputs, environment identity, Receipts, failed and
     excluded Runs, restart replay, Deep Doctor evidence, and a final explicit
     Decision where scientifically appropriate.

### Exit gate

Consolidation closes only when the release candidate, Claude Host, compatibility
baseline, declarative SDK, and three dogfood cases all have retained,
reproducible evidence. No additional Agent or Skill count can substitute for
these gates.

## Phase 3 — Sanctum (`0.4`)

### Objective

Define how an approved task may act in a real environment without weakening
the scientific control plane, and publish an experimental local reference
runtime for controlled dogfood.

The accepted Arcana meanings remain unchanged:

- **Sanctum** is the isolated Agent context.
- **Circle** declares the per-task boundary.
- **Ward** evaluates and enforces policy.
- **Crucible** is the mutable worktree, container, sandbox, or remote
  workspace where change is tested.

```text
Task Capsule
    -> Sanctum context
    -> Circle policy + Ward enforcement
    -> Execution Job + Lease
    -> Crucible workspace
    -> Worker result Proposal
    -> Athanor validation
    -> Chronicle Receipt
```

### RFC sequence

1. `RFC-0011: Sanctum Execution Model`
   - Control-plane and execution-plane ownership, terminology, threat model,
     assurance levels, and operational versus canonical state.
2. `RFC-0012: Job, Lease, and Worker Protocol`
   - Worker identity and capability, claim, heartbeat, fencing, renewal,
     cancellation, timeout, retry identity, logs, terminal states, and crash
     recovery.
3. `RFC-0013: Artifact Storage Model`
   - Logical Artifact versus physical Blob or Replica, content identity,
     transfer integrity, provenance, retention, and backend boundaries.
4. `RFC-0014: Patch Promotion Protocol`
   - Base identity, Patch Proposal, validation evidence, stale/conflict
     handling, explicit human promotion, idempotency, and recovery.
5. `RFC-0015: Experiment Executor API`
   - Typed start, observe, cancel, and result operations built on the accepted
     Job, Lease, Worker, and Artifact contracts.

### Reference runtime

`0.4` may expose experimental local execution for controlled use. It must:

- use new versioned execution contracts rather than reinterpret frozen Phase 2
  fields;
- keep Job, Lease, Attempt, and Worker state separate from scientific Runs;
- return bounded results and patches as Proposals;
- demonstrate expiration, cancellation, duplicate delivery, stale-result
  rejection, and restart recovery;
- state its assurance level and avoid production-grade isolation claims.

Remote Workers, cluster scheduling, automatic Provider invocation, and broad
GPU support are non-goals for `0.4`.

### Exit gate

All five RFCs, executable Schemas and examples, threat-model review,
conformance suite, and the local reference vertical slice must agree on the
same state and trust boundaries. A successful prototype alone is insufficient.

## Phase 4 — Forge (`0.5`)

### Objective

Move from defining trusted execution to operating reproducible experiments.

### Capabilities

- Production-grade local and container execution with explicit filesystem,
  network, CPU, memory, time, cancellation, and log controls.
- Resource queues, quotas, priorities, and auditable scheduling decisions.
- A local content-addressed Artifact Registry with pluggable remote backend
  contracts.
- Dataset versions bound to content identity, provenance, and license
  metadata.
- Versioned Protocol, Analysis Spec, and Rite contracts for multi-Experiment
  studies, ablation matrices, Pilot/Formal readiness, and completion
  aggregation without changing existing v1 replay semantics.
- Promotion of validated patches and execution outputs through explicit
  Athanor acceptance rather than direct canonical mutation.

Slurm, Kubernetes, cloud, and remote Artifact adapters may be added behind the
accepted interfaces, but no particular remote backend is a `0.5` release
blocker.

### Exit gate

Forge closes only when every capability above has conformance evidence. That
evidence must include the trusted local/container lifecycle; queue, quota, and
priority enforcement; the local Artifact Registry and pluggable backend
contract; Dataset identity, provenance, and license handling; and the new
Protocol, Analysis Spec, and Rite versions in a reproducible multi-Experiment
study. Every failed Attempt must remain preserved, and Executor success must
never be confused with scientific acceptance.

## Phase 5 — Observatory (`0.6-0.7`)

### Objective

Understand research state, surface weaknesses, and propose the next
scientifically useful action without taking scientific authority from the
researcher.

### Capabilities

- A Research Graph relating Papers, Evidence, Claims, Hypotheses, Protocols,
  Experiments, Runs, Assessments, Decisions, Artifacts, Issues, and
  Deviations.
- Scientific Memory that preserves why a design was chosen, why a direction
  was abandoned, and what failed or remained uncertain.
- A Next Action Engine whose recommendations include their supporting state,
  missing evidence, uncertainty, and disconfirming conditions.
- Provider-neutral scientific Review Capabilities that may be served by
  Claude, GPT, local models, or deterministic tools under the same disclosure
  and acceptance boundaries.

### Exit gate

Every graph edge, memory item, and recommendation must trace back to canonical
state or be labelled as an unaccepted Proposal. Observatory may recommend
`CONTINUE`, `REPAIR`, `PIVOT`, or `STOP`; it may not Seal the Decision.

## Phase 6 — Grimoire Ecosystem (`0.8`)

### Objective

Evolve the existing local, data-only Open Grimoire into a trusted research
extension ecosystem.

### Capabilities

- Publisher identity, signatures, provenance, compatibility resolution, and
  an auditable Registry.
- Domain Grimoires for machine learning, bioinformatics, robotics,
  reproduction, benchmarking, and surveys.
- Distribution of validated Rites, Capability Packs, Policy Packs, Schemas,
  examples, and benchmarks.
- Executable Worker, Storage, or Executor adapters only after signature,
  isolation, permission, and supply-chain policies are enforced.

### Exit gate

Remote installation must fail closed on unknown publishers, invalid
signatures, incompatible contracts, path escapes, dependency conflicts, and
untrusted executable content. Installing a Grimoire must never grant scientific
approval or canonical authority.

## Phase 7 — Research Runtime (`1.0`)

### Objective

Deliver Benchwork as a complete Research Operating System.

```text
Research intent
    -> Evidence and Claim map
    -> Research Question and Protocol
    -> Human Seal
    -> Sanctum and Forge execution
    -> Alembic analysis
    -> Observatory interpretation
    -> Human Decision
    -> Continue | Repair | Pivot | Stop
```

`1.0` requires stable, documented contracts for the supported control,
execution, intelligence, and ecosystem surfaces; explicit migrations from
supported prerelease state; and end-to-end reproduction evidence from multiple
research domains.

## Research Infrastructure (`2.0` north star)

`2.0` intentionally remains a north star rather than a committed feature list.
Its product form will be defined from evidence gathered after `1.0`, while
preserving portable research state, verifiable lineage, bounded execution, and
researcher authority.

## Technology direction

Python remains the implementation language throughout `0.x` while semantics
and protocols are evolving. A Rust Athanor may be evaluated after `1.0` only
when profiling, deployment, integrity, or concurrency evidence shows that a
kernel rewrite solves a measured problem.

## Historical milestone ledger

### M0: Foundation

Completed: repository structure, RFC-0000, public terminology, and project
governance.

### M1: Athanor

Completed: a local Chronicle with chained receipts, replayed projections,
Protocol drafting and sealing, and a Schema-validated CLI. The published Schema
contracts define scientific objects before provider integration begins.

### M2: Circle

Completed: local Capability registration, Task Capsule validation, Circle
boundaries, Ward evaluation, and canonical human approval receipts. Agent
Results remain proposals until accepted by Athanor.

### M3: Twin Gate

Completed: host-neutral Codex and Claude Code adapters that produce proposals
through the same Capability contracts and local canonical state. This adapter
symmetry does not claim a completed Claude Code interactive Host trial.

### M4: First Rite

Completed: `computational-study@0.1.0` and its protocol-bound Working state
machine.

### M5: Alembic

Completed: canonical Experiment and Run provenance plus schema-validated
`result-bundle/1.1` deterministic descriptive aggregation.

### M6: Open Grimoire

Completed for public Alpha: local, data-only Grimoire manifests; exact API and
SemVer pins; canonical Rite Sigils; collision and path-escape protection; and
Working execution from copied, inspectable definitions.

### M7: Scientific Canon

Completed: sourced and monotonically verified Evidence; explicit Claim
relations; Claim-backed, Protocol-registered Hypotheses; Result Bundle
Assessments; human-Sealed Decisions; and cross-object Chronicle lineage.

### M8: Integrity and Recovery

Completed: canonical, content-addressed Artifacts with producer and input
lineage; open-to-resolved research Issues; and immutable Deviations that record
post-Seal changes without rewriting the Protocol commitment.

### M9: Command Surface and Agent Handoff

Completed: all RFC Capability contracts; direct research verbs that create
Ward-checked Task Proposals; canonical Agent Result acceptance bound to the
original Capsule and input Sigil; Chronicle and Sigil inspection; and the
documented Grimoire, Rite, Working, Seal, and typed Trace command forms.

### M10: The Seal

Release candidate implemented: Phase 1 hardening for Receipt integrity,
state-bound Tasks, explicit scientific Gates, canonical Working and Run
lifecycles, registered Alembic comparisons, deterministic CLI project context,
governance, and golden release acceptance. Automatic Provider execution remains
outside M10.

### M11: The Grimoire

Implemented: Codex Plugin-first RFCs, the repository marketplace, seven
trigger-specific Skills, and concise repository agent rules.

### M12: The Instrument

Implemented: `bwork mcp serve`, STDIO transport, server instructions, stable
response envelopes, cursor pagination, and read-only project tools.

### M12.5: Host Boundary Verification

Implemented: tiered Kernel, CLI, and IDE Host acceptance; a machine-readable
Host capability matrix; environment-blocked IDE exceptions that do not weaken
Core/MCP gates; and a host-neutral external disclosure policy.

### M13: The Familiar

Implemented: the interactive Task open/get/complete/fail loop with automatic
semantic output blobs, Sigils, Host Session provenance, Athanor acceptance, and
same-session Receipts.

### M13.5: Review Provenance

Implemented: local and external Review Capability boundaries, Review Request
and Review Artifact Schemas, a fail-closed disclosure Gate, and Chronicle
events for request, approval, completion, and acceptance. Benchwork records
Review provenance but does not invoke or upload content to a provider.

### M14: The Wards

Implemented: trusted SessionStart, PreToolUse, and PostToolUse hooks with
bounded output, direct `.benchwork/` write protection, and adversarial
fixtures.

### M15: The Working

Implemented: canonical scientific write tools, immutable preview/commit Seals,
Experiment and Run tools, deterministic Alembic invocation, and specialized
implementation, pilot, evaluation, and recovery Skills.

### M16: Trial of the Familiar

Prerelease candidate: local marketplace packaging, Plugin and Skill validation,
in-memory and spawned-STDIO protocol tests, and the Phase 2 acceptance matrix.
Codex CLI acceptance is complete. IDE validation is an accepted
`BLOCKED_BY_ENVIRONMENT` Tier 2 exception until a graphical extension Host is
available; external diff review remains
`WAITING_FOR_DISCLOSURE_AUTHORIZATION`.

### M17: The Instrumentarium Seal

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

### M18: The Invitation

Implemented on `main` for the `0.3.0rc2` candidate: an auditable POSIX
installer; exact release and channel manifests; uv-first and pipx-isolated
bootstrap; installation-level diagnostics; safe versioned Plugin staging;
opt-in Codex and experimental Claude MCP setup; PATH, repair, rollback, and
uninstall ownership; release-asset, SBOM, provenance, and Pages-publication
automation; and installer CI.

M18 does not change the Phase 2 scientific state machine. Installer operations
must continue to report `Project state: NOT_TOUCHED`. M18 is not a completed
tagged release until the exact-tag acceptance report records all required
evidence and changes its final decision from `REPAIR`.
