# Benchwork

[English](README.md) | [简体中文](README.zh-CN.md)

**An auditable workbench for agent-assisted computational research.**

Benchwork turns research activity into explicit, reviewable state. Agents and
tools may propose work, but only the deterministic Athanor kernel can accept a
canonical transition. Accepted events are written to a local, append-only
Chronicle with chained SHA-256 Sigils and receipts.

> Project status: `0.2.0a3` public Alpha. Milestones M0–M9 are implemented.

## Why Benchwork

Computational research rarely fails because it lacks one more chat interface.
It fails when intent, evidence, code, runs, analysis, and decisions drift apart.
Benchwork gives those elements stable identities and a recorded lifecycle:

```text
Idea → Evidence → Claim → Hypothesis → Protocol
     → Implementation → Experiment → Analysis → Review → Decision
```

The system separates two kinds of work:

- **proposals**, produced by researchers, Agents, Hosts, and tools; and
- **canonical state**, validated by Athanor and preserved in Chronicle.

Conversations remain useful interfaces, but they never become the source of
scientific state.

## What works today

- **Athanor** validates and serializes canonical state transitions.
- **Chronicle** stores an append-only JSONL event chain with an independently
  checked head.
- **Sigils and Receipts** bind accepted events to SHA-256 content digests.
- **Research Programs and Protocols** support a guarded
  `DRAFT → FROZEN` lifecycle.
- **Evidence, Claims, and Hypotheses** preserve sourced observations,
  verification checks, explicit relations, and falsifiable predictions.
- **Capabilities, Task Capsules, Circles, and Ward** bound tools, network
  access, time, and approval before delegation.
- **Codex and Claude Code Hosts** produce equivalent, provider-neutral task
  proposals.
- **Rites and Workings** pin workflow definitions and record protocol-bound
  stage transitions.
- **Experiments, Runs, and Alembic** preserve all outcomes and produce
  deterministic `result-bundle/1.0` analysis artifacts.
- **Assessments and Decisions** bind interpretation to Result Bundles and keep
  final scientific commitments human-sealed and replayable.
- **Artifacts, Issues, and Deviations** preserve content-addressed outputs,
  recoverable problems, and post-Seal changes without rewriting history.
- **Direct verbs and Agent handoff** create Ward-checked Task Proposals and
  accept Snapshot- and Contract-bound `agent-result/1.1` outputs through
  Athanor.
- **Open Grimoire** installs versioned, content-pinned, data-only Rite packs
  without executing extension code.
- **Versioned JSON Schemas** define the public contracts for research objects,
  events, tasks, runs, assessments, decisions, and result bundles.

Benchwork does not yet provide a canonical remote Agent backend or automatic
experiment execution. Alpha Grimoire installation is local and data-only;
publisher signatures and remote distribution remain future work.

## Integrity model

Benchwork fails closed when it detects an invalid schema, broken event chain,
tail truncation, altered Task Capsule, approval mismatch, unregistered Rite, or
invalid Working transition.

The current integrity model protects against accidents and detectable drift.
SHA-256 Sigils are content digests, not digital signatures. They do not defend
against a malicious writer who can replace the entire Chronicle, its head, and
all receipts.

For the complete boundary, see
[Integrity Repair](docs/en/architecture/INTEGRITY_REPAIR.md).

## Requirements

- Python 3.11 or newer
- `pip`

## Installation

For development, install the repository in editable mode:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

The package installs the `bwork` command and the versioned JSON Schemas used for
runtime validation.

## Quick start

Run these commands from a directory where Benchwork may create a local
`.benchwork/` state directory:

```bash
bwork init

bwork program create robust-agent-memory \
  --title "Reliable agent memory" \
  --problem "Measure retrieval reliability under long context."

bwork evidence record EV-001 \
  --program RP-001 \
  --source "paper.json|sha256:0000000000000000000000000000000000000000000000000000000000000000" \
  --observation "Prior work reports improved retrieval." \
  --source-resolved \
  --content-inspected

bwork claim create CL-001 \
  --program RP-001 \
  --type empirical \
  --statement "The treatment can improve retrieval." \
  --evidence "EV-001|SUPPORTS"

bwork claim verify-relation CL-001 --evidence EV-001

bwork hypothesis create HY-001 \
  --program RP-001 \
  --claim CL-001 \
  --statement "The treatment improves registered retrieval score." \
  --prediction "Mean score exceeds the baseline mean."

bwork rq seal --program RP-001 \
  --statement "Does the treatment improve registered retrieval score?"

bwork protocol draft PT-001 \
  --program RP-001 \
  --title "Memory retrieval study" \
  --analysis-plan "Compute effect sizes and uncertainty across seeds." \
  --study-mode confirmatory \
  --hypothesis HY-001

bwork protocol seal PT-001

bwork working start computational-study@0.2.0 \
  --program RP-001 \
  --protocol PT-001

bwork artifact register AR-001 \
  --program RP-001 \
  --kind implementation \
  --location "artifact.json|sha256:<digest-from-bwork-sigil-file>" \
  --producer WK-001 \
  --input PT-001

bwork experiment create EX-001 \
  --program RP-001 \
  --protocol PT-001 \
  --hypothesis HY-001 \
  --question "Does the treatment improve the registered score?"

bwork experiment transition EX-001 implemented
bwork experiment transition EX-001 pilot-started

bwork run record RUN-001 \
  --experiment EX-001 \
  --phase PILOT \
  --status COMPLETED \
  --include \
  --seed 1 \
  --metric score=0.82

bwork experiment transition EX-001 pilot-completed

bwork analyze --program RP-001 --protocol PT-001

bwork review RB-001 \
  --summary "The registered result supports the hypothesis." \
  --limitation "Only one run is available." \
  --claim-finding "CL-001|SUPPORTED|The observed direction matches the claim." \
  --hypothesis-finding "HY-001|SUPPORTED|The prediction was satisfied."

bwork decide \
  --program RP-001 \
  --outcome CONTINUE \
  --assessment AS-001 \
  --rationale "Collect more registered runs."

bwork status
bwork doctor
bwork trace CL-001
```

In a new project, the commands above create a complete trace from `EV-001` to
the Sealed `DE-001`. The matching canonical events move `WK-001` through its
pinned exit contracts to `COMPLETED`.

Operational integrity objects remain available alongside the scientific chain:

```bash
bwork issue open IS-001 \
  --program RP-001 \
  --subject AR-001 \
  --severity HIGH \
  --title "Environment metadata is incomplete" \
  --description "One dependency version was not captured."

bwork deviation record DV-001 \
  --protocol PT-001 \
  --kind UNPLANNED \
  --summary "Environment metadata repaired after Seal." \
  --rationale "Exact replay requires the missing version." \
  --impact MINOR \
  --affected AR-001 \
  --affected IS-001

bwork issue resolve IS-001 \
  --resolution "Registered the missing version without replacing the original Artifact."
```

The zero digest is only a syntactically valid documentation placeholder.
Production records should use the SHA-256 digest of the referenced artifact.

## Capability and approval flow

A Task Capsule declares its Capability, input Sigil, allowed tools, network
access, and time budget. Ward compares that Circle with the local Capability
contract:

```text
Task request
    ↓
Task Capsule + Circle
    ↓
Ward ── REJECTED
    ├── WAITING_FOR_APPROVAL → human approval Receipt → PASS
    └── PASS
```

The RFC direct verbs use the same boundary:

```bash
bwork start "Study recoverable agent memory"
bwork investigate --program RP-001
bwork design --program RP-001
bwork implement --program RP-001
bwork pilot --program RP-001
bwork run --program RP-001

bwork scry literature --program RP-001
bwork distill evidence --program RP-001
bwork invoke bench.hypothesis.challenge --program RP-001
```

`investigate` and `design` normally pass their read-only contracts.
`implement`, `pilot`, and bare `run` stop at `WAITING_FOR_APPROVAL`. These
commands prepare Task Capsules; they do not report Provider work as complete.
After a Provider returns an `agent-result/1.1` file:

```bash
bwork task accept agent-result.json
bwork trace task TK-001
bwork chronicle verify
bwork sigil verify artifact.json
```

Useful discovery commands:

```bash
bwork capability list
bwork host list
bwork rite list
bwork grimoire list
bwork --help
```

## Command map

| Command | Purpose |
|---|---|
| `bwork init` | Initialize Chronicle, Capability contracts, Rites, and Grimoires |
| `bwork status` | Rebuild and print canonical state |
| `bwork doctor` | Verify Chronicle events, Sigils, head, and receipt chain |
| `bwork program` | Create Research Programs |
| `bwork start` | Start a Research Program from an objective |
| `bwork investigate`, `design`, `implement`, `pilot`, `run` | Prepare bounded phase Tasks |
| `bwork scry`, `distill`, `invoke` | Prepare Arcana or explicit Capability Tasks |
| `bwork seal` | Seal a Protocol through the direct RFC form |
| `bwork evidence` | Record, verify, and inspect sourced Evidence |
| `bwork claim` | Create Claims and explicitly verify Evidence relations |
| `bwork hypothesis` | Create and inspect falsifiable Hypotheses |
| `bwork rq` | Explicitly Seal a Research Question |
| `bwork protocol` | Draft and Seal Protocols |
| `bwork reproduction` | Bind reproduction status to canonical research objects |
| `bwork capability` | Inspect installed Capability contracts |
| `bwork task` | Create/inspect Task Capsules and accept Agent Results |
| `bwork ward` | Evaluate a Task Capsule against policy |
| `bwork approval` | Record explicit human approval |
| `bwork host` | Create Codex or Claude Code Host proposals |
| `bwork rite` | Inspect pinned workflow definitions |
| `bwork grimoire` | Compute Rite Sigils and install pinned local Grimoires |
| `bwork working` | Start, inspect, and advance Rite executions |
| `bwork experiment` | Create Protocol-bound Experiments |
| `bwork run record` | Record immutable Runs and analysis inclusion |
| `bwork analyze` | Produce a deterministic Alembic Result Bundle |
| `bwork review` | Record a Result Bundle Assessment |
| `bwork assessment` | Inspect completed Assessments |
| `bwork decide` | Human-Seal a scientific Decision |
| `bwork decision` | Inspect sealed Decisions |
| `bwork artifact` | Register and inspect content-addressed Artifacts |
| `bwork issue` | Open, resolve, and inspect research Issues |
| `bwork deviation` | Record and inspect post-Seal Protocol Deviations |
| `bwork chronicle` | Show or verify the Chronicle |
| `bwork sigil` | Show object/Receipt Sigils or verify a file |
| `bwork trace` | Show Chronicle events for an object |

Use `bwork <command> --help` for command-specific arguments.

## Local state

`bwork init` creates project-local state:

```text
.benchwork/
├── chronicle.jsonl
├── chronicle.head
├── chronicle.lock
├── capabilities.json
├── capabilities.lock
├── rites.json
├── grimoires.json
├── grimoires.lock
└── capsules/
```

Chronicle is canonical. Task Capsules are immutable, inspectable proposals
stored outside the canonical ledger until an accepted transition refers to
them.

## Documentation

| Topic | English | 简体中文 |
|---|---|---|
| Documentation index | [English](docs/en/README.md) | [简体中文](docs/zh-CN/README.md) |
| Arcana language and design | [RFC-0000](docs/en/rfcs/RFC-0000-arcana.md) | [RFC-0000](docs/zh-CN/rfcs/RFC-0000-arcana.md) |
| Athanor invariants | [Architecture note](docs/en/architecture/ATHANOR.md) | — |
| Circle and Ward | [Architecture note](docs/en/architecture/CIRCLE.md) | — |
| Host symmetry | [Twin Gate](docs/en/architecture/TWIN_GATE.md) | — |
| Working lifecycle | [First Rite](docs/en/architecture/FIRST_RITE.md) | — |
| Analysis boundary | [Alembic](docs/en/architecture/ALEMBIC.md) | — |
| Scientific canon | [Scientific Canon](docs/en/architecture/SCIENTIFIC_CANON.md) | — |
| Integrity and recovery | [Integrity and Recovery](docs/en/architecture/INTEGRITY_RECOVERY.md) | — |
| Commands and Agent handoff | [Command Surface](docs/en/architecture/COMMAND_SURFACE.md) | — |
| Extension boundary | [Open Grimoire](docs/en/architecture/OPEN_GRIMOIRE.md) | — |
| Localization | [Policy](docs/LOCALIZATION.md) | — |

English is the canonical documentation source. Missing translations fall back
to English; untranslated English pages are not copied into locale directories.

## Repository layout

```text
src/benchwork/     Athanor kernel, CLI, Ward, Hosts, Rites, and Grimoire
schemas/           Public versioned JSON Schema contracts
tests/             Deterministic unit and integrity tests
docs/en/           Canonical English documentation
docs/zh-CN/        Simplified Chinese translations
hosts/             Host-specific integration guidance
examples/          Minimal research artifacts
```

## Development

Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

Changes to canonical transitions should include tests for replay, schema
validation, integrity failure, and concurrency where applicable. Documentation
changes should preserve locale paths and follow
[the localization policy](docs/LOCALIZATION.md).

## License

Benchwork is available under the [MIT License](LICENSE).
