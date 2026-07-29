# Benchwork

An auditable workbench for agent-assisted computational research.

`Benchwork` is the product, `Arcana` is its design language, and `Athanor` is
the deterministic kernel. Agent services may propose work; canonical research
state is stored locally as an append-only Chronicle and validated by Athanor.

```text
Idea -> Evidence -> Protocol -> Implementation -> Experiment
     -> Deterministic Analysis -> Scientific Review -> Decision
```

## First milestone

This repository initializes the Athanor foundation:

- an append-only Chronicle at `.benchwork/chronicle.jsonl`;
- SHA-256 Sigil receipts for accepted events;
- Research Program projections derived from Chronicle events;
- a guarded `DRAFT -> FROZEN` Protocol lifecycle with an analysis plan; and
- Circle Task Capsules and Ward checks before any provider may act; and
- a small dependency-free `bwork` CLI.

No Agent or provider adapter is canonical in this milestone. Conversations are
interfaces, never the source of scientific state.

## Quick start

```bash
python -m pip install -e .
bwork init
bwork program create robust-agent-memory --title "Reliable agent memory"
bwork protocol draft PT-001 --program RP-001 --title "Memory study" --analysis-plan "Compute effect sizes by seed."
bwork protocol seal PT-001
bwork task create bench.code.modify --input-sigil sha256:0000000000000000000000000000000000000000000000000000000000000000 --tool read --tool write --time-budget 300
bwork ward check TK-... # waits for explicit approval
bwork approval grant TK-... --reason "Reviewed the requested code boundary."
bwork host propose codex bench.code.inspect --input-sigil sha256:... --tool read --time-budget 300
bwork working start computational-study@0.1.0 --program RP-001 --protocol PT-001
bwork working advance WK-001 --reason "Implementation reviewed."
bwork status
bwork trace PT-001
```

## Layout

- `docs/rfcs/RFC-0000-arcana.md`: the accepted language and design bible.
- `src/benchwork`: Athanor kernel and CLI.
- `schemas`: public, versioned JSON Schemas.
- `hosts`: symmetric Codex and Claude Code Host adapter guidance.
- `docs/architecture/FIRST_RITE.md`: the first protocol-bound Working lifecycle.
- `examples`: a minimal research-program artifact.

See [the architecture note](docs/architecture/ATHANOR.md) for invariants and
[RFC-0000](docs/rfcs/RFC-0000-arcana.md) for terminology.
