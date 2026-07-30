---
title: "RFC-0000: The Arcana of Benchwork"
subtitle: Language, Philosophy, and Design Bible
document_id: BW-RFC-0000
version: 0.2
status: accepted
owner: Endofthestars
date: 2026-07-29
language: en
canonical: true
translation_key: BW-RFC-0000
---

# RFC-0000: The Arcana of Benchwork

[English](RFC-0000-arcana.md) | [Simplified Chinese](../../zh-CN/rfcs/RFC-0000-arcana.md)

> **Rigor in every rite. Every piece of evidence leaves a trace.**

## Preface

Benchwork is a workbench for computational research. Here, researchers pose questions, organize evidence, form claims, design protocols, implement systems, run experiments, interpret results, and decide what to do next. Every piece of work has provenance, boundaries, versions, and history; every advance can be understood, reviewed, and continued.

**Arcana** is the language of Benchwork. Drawing on laboratories, alchemical craft, manuscripts, star charts, and precision instruments, it gives observation, distillation, shaping, trial, recording, and commitment a shared vocabulary.

Its character is attention to process, respect for evidence, awareness of boundaries, care with commitments, honest records of failure and deviation, openness to the unknown, and sustained commitment to reviewability.

# 1. The Bench

A bench holds materials, instruments, sketches, measurements, trials, and records. It permits exploration while requiring order; it makes room for creation while preserving traces. A researcher may step away and later return to the same work, or invite another researcher to continue from the existing record.

Research develops along this path:

```text
Idea → Evidence → Claim → Hypothesis → Protocol → Implementation
→ Experiment → Analysis → Review → Decision
```

The path may loop, branch, pause, and backtrack. Each loop produces new evidence, every branch preserves lineage, and every decision becomes the starting point for later work. Benchwork treats research as a continuing **Working**: work that is observed, shaped, tested, and open to renewed understanding.

# 2. The Language of Arcana

Arcana has three layers.

## 2.1 Scientific Canon

The Scientific Canon names formal research objects:

```text
Research Program, Claim, Evidence, Hypothesis, Protocol, Experiment,
Run, Assessment, Issue, Decision, Deviation, Artifact, Receipt
```

These terms belong in schemas, APIs, research exports, audit records, and formal methods documentation. They are direct, stable, and comparable, so Benchwork connects naturally to existing research practice, statistical tools, and external systems.

## 2.2 Arcana Mechanics

Arcana Mechanics names how Benchwork works:

```text
Athanor, Chronicle, Ward, Sigil, Alembic, Sanctum, Crucible,
Grimoire, Rite, Working, Circle, Seal
```

These terms form the product's runtime language across its CLI, terminal, documentation navigation, extension ecosystem, and architecture diagrams.

## 2.3 Capability Language

Capabilities name model-independent, executable research actions:

```text
bench.research.orchestrate       bench.evidence.discover
bench.evidence.synthesize        bench.evidence.verify
bench.hypothesis.frame           bench.hypothesis.challenge
bench.study.design               bench.study.audit
bench.code.inspect               bench.code.modify
bench.experiment.plan            bench.experiment.execute
bench.experiment.collect         bench.analysis.compute
bench.analysis.interpret         bench.decision.review
bench.decision.propose
bench.review.prepare             bench.review.local
bench.review.external            bench.review.accept
```

Claude, Codex, and future models participate through the same Capability contracts. The Scientific Canon names research objects; Arcana Mechanics names research craft; Capability Language names executable actions.

# 3. The Philosophy of the Working

## 3.1 Research leaves a trace

Research gains continuity through traces. A Claim traces to Evidence; Evidence traces to a source location, data, or Run; a Decision traces to analysis, review, objections, and authorization. Benchwork writes this continuity into Chronicle and maintains object identity through Sigils.

## 3.2 Evidence forms a constellation

Evidence is distributed among papers, code, data, experimental results, and expert judgment. Benchwork relates it as support, contradiction, limitation, reproduction, extension, and open question. A source supplies an observation; many observations form a constellation that clarifies a problem's boundaries and direction.

## 3.3 Protocols shape intention

A Protocol turns research intent into an executable commitment. It connects Claims, Hypotheses, data, controls, measurements, run matrices, analysis plans, and decision rules. Once Sealed, it receives a stable version; later changes enter Chronicle as Deviations.

## 3.4 Computation and interpretation are complementary crafts

Alembic computes descriptive statistics, effect sizes, uncertainty, robustness, resource use, and run completeness. Agents and researchers interpret what results support or constrain, which competing explanations remain, and what the next experiment can reveal. Computation provides repeatable scale; interpretation provides scientific context.

## 3.5 Capabilities outlive providers

A Capability is the stable unit of ability. Claude, Codex, local models, remote models, and deterministic executors may provide it; task needs, tools, permissions, budget, quality, and user policy determine routing. Providers may change while Capability contracts, research objects, and Chronicle remain continuous.

## 3.6 Human judgment seals commitment

Researchers retain final authority over scientific commitments. Agents explore, organize, challenge, design, and interpret; Athanor validates structure and state; Ward checks permission and conditions; researchers confirm direction, protocols, formal experiments, and decisions at critical points.

## 3.7 Failure is part of the record

Failed Runs, negative results, cancelled tasks, protocol deviations, and unresolved Issues belong to research history. Chronicle preserves them so later judgment can understand why work continued, was repaired, pivoted, or stopped. Failure becomes information; deviation becomes context; stopping becomes an evidence-based scientific decision.

## 3.8 Research grows through lineage

Research Programs can branch and form lineage. A direction can yield new questions, a failed mechanism can become a new hypothesis, and a PIVOT can create a new Program while retaining its relation to earlier work. Research is a continuously growing tree of knowledge.

# 4. The Core Arcana

| Name | Standard meaning | Responsibility |
|---|---|---|
| **Athanor** | Deterministic core furnace | Receives Proposals; validates schemas, references, digests, Gates, and authorization; writes accepted changes to Chronicle and issues Receipts. It owns all canonical transitions. |
| **Chronicle** | Append-only research event ledger | Records Programs, Claims, Evidence, Protocols, Runs, Assessments, and Decisions; supports state reconstruction, historical replay, auditing, and comparison. |
| **Ward** | Protective layer | Establishes permission, budget, lease, integrity, and approval boundaries before action, then checks postconditions. |
| **Sigil** | Stable identity | Connects content digests, provenance, inputs, outputs, actors, Policy, and Receipts. |
| **Alembic** | Deterministic analysis engine | Distills Runs, measurements, and resource records into machine-readable statistical products. |
| **Sanctum** | Isolated Agent context | Holds a specific goal, visible material, tools, budget, and output contract. |
| **Crucible** | Mutable workspace | Hosts change, debugging, configuration, and trials in a Git worktree, container, sandbox, or remote directory. |
| **Grimoire** | Versioned extension source | Collects Rites, Capability Packs, adapters, Policy Packs, Schema Extensions, examples, and Benchmarks. |
| **Rite** | Versioned research workflow | Arranges goals, Capabilities, I/O, Gates, Ward, human approvals, and stopping conditions into reusable process. |
| **Working** | Recoverable Rite execution | Binds a Program, Rite version, input, Policy, Provider, and Task Graph; records state, Receipts, failure, retry, and checkpoints. |
| **Circle** | Per-task boundary | Declares visible Artifacts, files, network, tools, execution permission, time and cost budgets, and output Schema. |
| **Seal** | Commitment-freezing operation | Gives Protocols, Analysis Plans, Decisions, and external export packages a stable version and Sigil. |

# 5. The Grammar of Benchwork

```text
A Grimoire contains reusable Rites.
A Rite instantiates a Working.
A Working advances through a set of Tasks.
Each Task receives its own Circle.
An Agent reasons inside a Sanctum.
Implementation and experiments evolve inside a Crucible.
Alembic computes from complete Run records.
Ward checks policy, permission, and resources.
Athanor accepts canonical state transitions.
Chronicle preserves accepted events.
Sigils identify objects, artifacts, and receipts.
Seals stabilize a stage of scientific commitment.
```

# 6. The Commands of the Bench

The ordinary research path uses direct verbs:

```bash
bwork init
bwork start
bwork investigate
bwork design
bwork implement
bwork pilot
bwork run
bwork analyze
bwork review
bwork decide
bwork resume
bwork status
bwork doctor
```

Arcana operations express Benchwork-specific craft:

```bash
bwork scry literature
bwork distill evidence
bwork invoke bench.evidence.verify
bwork seal protocol PT-001
bwork ward check
bwork trace claim CL-001
```

Scry explores literature, code, and the evidence space. Distill turns checked material into structured Proposals. Invoke calls an explicit Capability. Seal stabilizes scientific commitments. Ward checks permissions, budgets, integrity, and approval conditions. Trace reconstructs the lineage of objects, events, Artifacts, and Decisions.

Extension commands bring this language into daily practice:

```bash
bwork grimoire add endofthestars/ml-research
bwork grimoire inspect endofthestars/ml-research

bwork rite search computational-study
bwork rite install ml-computational-study@0.1.0
bwork rite run ml-computational-study

bwork working list
bwork working inspect WK-014
bwork working resume WK-014

bwork chronicle show
bwork chronicle verify

bwork sigil show RC-031
bwork sigil verify artifact.json
```

# 7. Agents, Hosts, and Providers

Benchwork organizes intelligence around Capabilities. Claude, Codex, and future models can serve as research interfaces, execute `bench.research.orchestrate`, call the same Capabilities, and return results to Athanor through a common output contract.

A **Host** is the environment where the researcher interacts. A **Provider** is the model or Agent backend that executes a Capability. A **Capability** is a stably defined research action. One Host may call several Providers, and several Providers may implement one Capability.

**Conductor** is the product name for `bench.research.orchestrate`. It reads Program state, understands the researcher's objective, forms Task Proposals, invokes Capabilities, summarizes a Working, and asks the researcher to confirm when a scientific commitment is required.

| Area | Arcana title | Capability scope |
|---|---|---|
| Evidence | **Archivist** | `bench.evidence.*` |
| Method | **Adept** | `bench.hypothesis.*`, `bench.study.*` |
| Challenge | **Adversary** | challenge and audit |
| Code | **Artificer** | `bench.code.*` |
| Execution | **Hand** | `bench.experiment.*` |
| Integrity | **Warden** | policy and assessment |
| Maintenance | **Keeper** | configuration and extensions |

# 8. Voice and Tone

Benchwork sounds like precision instrumentation, laboratory records, and a composed research partner: clear, restrained, stable, and instrument-like; able to express uncertainty; attentive to object, state, provenance, and next action; and explicit about consequences and context before critical commitments.

```text
BENCHWORK · ATHANOR
Project       /work/robust-memory
Program       RP-001
Working       WK-014
Rite          ml-computational-study@0.1.0
State         WAITING_FOR_APPROVAL

Ward          approval required: protocol.seal
Object        PT-003
Sigil         sha256:3d8b…9a21

Next action   review protocol and confirm seal
```

When a Working completes:

```text
Working WK-014 completed.
Tasks          7 completed · 1 failed
Chronicle      12 events appended
Receipts       RC-031 … RC-042
Decision       REVIEW_REQUIRED
Next action    scientific review
```

Benchwork language should always make four things clear: what happened, what remains on record, what is still missing, and who decides the next step.

# 9. Visual Language

The visual world is a laboratory both modern and old: dark benches, brass precision instruments, parchment-like reading surfaces, manuscript marginalia, star-chart relationship networks, geometric graduations, sealing wax and marks, controlled containers, and traceable paths.

| Name | Use | Example |
|---|---|---|
| Obsidian | Primary background | `#111318` |
| Ash | Secondary background | `#2C3038` |
| Parchment | Light reading surface | `#F3EFE5` |
| Brass | Brand emphasis | `#B78A3B` |
| Lapis | Information and links | `#4B5FA8` |
| Verdigris | Verified and complete | `#4F8A7B` |
| Cinnabar | Critical and Stop | `#B74A3D` |

Rectangles denote deterministic components; rounded rectangles, Capabilities or Adapters; circles, Gates and Approval Points; hexagons, Artifacts or research objects. Solid arrows are committed state flow; dashed arrows are Proposals and candidate data; double borders denote Sealed Objects. The visual system serves reading, state comprehension, and lineage tracing.

# 10. Grimoires, Rites, and Community

Grimoires and Rites form Benchwork's open ecosystem. A Grimoire may collect domain methods, Capabilities, Provider Adapters, Policies, Schemas, examples, and Benchmarks, such as `endofthestars/ml-research`. A Rite describes a reusable research path, such as `ml-computational-study`, `paper-reproduction`, `benchmark-audit`, `systematic-evidence-map`, or `ablation-study`.

Contributors collaborate as Owners, Maintainers, Reviewers, Contributors, Security Contacts, and Rite Maintainers. Community headings can naturally include New Rites, Changes in the Athanor, Chronicle Compatibility, Ward and Security Notes, Grimoire Updates, and Breaking Seals.

Arcana gives the community shared memory; engineering conventions give it a shared rhythm. Work remains searchable and automatable:

```text
feat(chronicle): add atomic append receipt
fix(ward): handle expired approval token
docs(arcana): refine seal semantics
```

# 11. Releases as Chapters

Benchwork uses SemVer and Schema Version for compatibility, and codenames for project history.

| Milestone | Codename | Theme |
|---|---|---|
| M0 | **Foundation** | Repository, specification, and governance |
| M1 | **Athanor** | Kernel and Chronicle |
| M2 | **Circle** | Capability Runtime and permission boundary |
| M3 | **Twin Gate** | Symmetric Claude/Codex Host |
| M4 | **First Rite** | First computational-research workflow |
| M5 | **Alembic** | Deterministic analysis and assessment loop |
| M6 | **Open Grimoire** | Extension ecosystem and public Alpha |

A version number answers “what is this compatible with?” A codename answers “what does this chapter build?”

# 12. The Arcana Lexicon

| Arcana | Standard meaning | Core expression |
|---|---|---|
| **Benchwork** | Product and research workbench | Research has a place to unfold. |
| **Arcana** | Product language and design culture | The craft has a language. |
| **Athanor** | Deterministic kernel | Canonical transitions have a single authority. |
| **Chronicle** | Append-only event ledger | Research has a memory. |
| **Ward** | Policy and permission layer | Automation has a boundary. |
| **Sigil** | Identity, digest, and receipt | Artifacts have an identity. |
| **Alembic** | Deterministic analysis engine | Measurements become analysis. |
| **Sanctum** | Isolated Agent context | Reasoning has a place. |
| **Crucible** | Mutable implementation and experiment workspace | Change has a place to be tested. |
| **Grimoire** | Versioned extension source | Reusable knowledge has a home. |
| **Rite** | Versioned research workflow | Method becomes a reusable path. |
| **Working** | Recoverable Rite execution | Research moves through a recorded process. |
| **Circle** | Per-task permission and context boundary | Every task has a horizon. |
| **Seal** | Scientific commitment operation | Commitment takes a stable form. |

# 13. The Arcana in Motion

In a typical Benchwork flow, a researcher begins a Research Program; Conductor selects a Rite from a pinned Grimoire; the Rite creates a Working; the Working opens a Circle for evidence discovery; an Agent reasons inside a Sanctum; Athanor accepts verified Evidence and appends the corresponding events to Chronicle; a Protocol is shaped and Sealed; an Artificer develops the implementation inside a Crucible; Runs are collected in full; Alembic computes the analysis; reviewers weigh the evidence and alternatives; the researcher commits a Decision; and Chronicle preserves the complete lineage.

```bash
bwork start "Study memory retrieval reliability for long-context Agents"
bwork investigate
bwork design
bwork seal protocol PT-001
bwork implement
bwork pilot
bwork run
bwork analyze
bwork review
bwork decide
bwork trace decision DE-001
```

# 14. The Promise of Benchwork

Good research tools should help researchers do three things: **see** evidence, hypotheses, limitations, failures, deviations, and open questions; **shape** vague intent into clear Claims, Protocols, Experiments, and Decision Rules; and **trace** any conclusion back to its materials, process, computation, interpretation, and authorization.

Arcana organizes those abilities as a craft. Athanor provides a stable core; Chronicle preserves research memory; Ward establishes action boundaries; Sigil maintains object identity; Alembic provides computational scale; Sanctum and Circle shape context; Crucible contains change; Grimoire preserves reusable knowledge; Rite describes method; Working advances research; Seal fixes commitment.

> Research is a long-term Working. Every Working deserves careful observation, precise shaping, complete recording, and handoff to the next researcher.

# Closing

The Arcana of Benchwork comes from a love of research craft. It names the bench, structures the process, relates the evidence, identifies the objects, bounds the automation, and gives research a memory.

Every Scry expands the view. Every Distill organizes understanding. Every Working advances research. Every Seal fixes a commitment. Every Chronicle entry carries today's work into the future.
