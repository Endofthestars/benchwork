# Phase 2 acceptance matrix

Phase 2 uses the
[Acceptance Exception Policy](plugins/acceptance-exception-policy.md). An
unavailable optional Host and a correctly denied disclosure are explicit
states, not product failures.

## M17 seal verdict

```yaml
version: 0.3.0rc1
phase2:
  implementation: COMPLETE
  acceptance: PASS_WITH_ACCEPTED_EXCEPTIONS
  contracts: FROZEN_ALPHA
phase3_rfc_gate: OPEN
```

This verdict does not convert optional or unauthorized Host work into PASS.
It records required gates separately from accepted environment and disclosure
states.

## Release acceptance

| Boundary | Status | Release effect | Evidence |
| --- | --- | --- | --- |
| Tier 0 — Kernel | PASS | Required | Chronicle, Schema, Ward, Capability, replay, and deterministic suites |
| MCP | PASS | Required | in-memory and spawned-STDIO discovery, envelopes, pagination, Task and canonical tool tests |
| Tier 1 — Codex CLI Host | PASS | Required before Phase release | fresh Codex CLI explicit/implicit Skill trials and MCP calls |
| Tier 1 — Claude Code CLI | PASS | Second CLI Host gate satisfied | fresh Claude Code CLI MCP discovery, read-only calls, and a bounded Task loop with an Athanor Receipt |
| Tier 2 — IDE Host | BLOCKED_BY_ENVIRONMENT (accepted) | Does not block Core/MCP/CLI | `HOST-IDE-001`; extension installed, no graphical extension Host available |
| External Review | WAITING_FOR_DISCLOSURE_AUTHORIZATION | Does not block local review or Core/MCP/CLI | Disclosure Gate denied an unapproved diff review |

The IDE exception has no impact on Core, MCP, or CLI acceptance. It must be
closed before a public IDE integration release.

`HOST-IDE-001` is owned by the Benchwork release owner. Its reproducible
closure procedure is maintained in the
[Host Support Matrix](HOST_SUPPORT_MATRIX.md).

External Review remains pending until a researcher approves the exact source,
files, disclosure flags, and destination. No diff was uploaded during this
acceptance run.

The M17 deterministic gate completed with 144 unittest cases, 144 pytest
cases, 174 subtests, and 81% branch-aware coverage on Python 3.13. Ruff and
mypy completed without findings, and the SciPy numerical oracle passed.

## Milestone evidence

| Milestone | Acceptance | Evidence |
| --- | --- | --- |
| M11 — The Grimoire | Plugin-first boundary, seven Skills, AGENTS.md, repo marketplace | RFC-0008; plugin validator; Skill validators |
| M12 — The Instrument | STDIO server, instructions, read tools, envelopes, pagination | MCP in-memory and subprocess tests |
| M12.5 — Host Boundary Verification | Kernel/CLI/IDE tiers and environment exception | `host-capability-matrix.yaml`; policy tests |
| M13 — The Familiar | Open/get/complete/fail Task loop and Host Session provenance | `tests/mcp/test_runtime.py` |
| M13.5 — Review Provenance | local/external capabilities, disclosure approval, Review Receipts | `tests/test_review_provenance.py` |
| M14 — The Wards | startup, pre-tool, and post-tool hooks; direct state-write denial | `tests/hooks/test_hooks.py` |
| M15 — The Working | canonical writes, preview/commit Seals, Runs, Alembic, seven workflows | runtime tests and lifecycle/Alembic suites |
| M16 — Trial of the Familiar | marketplace package, fresh CLI discovery, accepted Host exception | plugin validation, interactive contract tests, install/upgrade/rollback trials |
| M17 — The Instrumentarium Seal | frozen Alpha contracts, Tool Registry, release metadata, golden REPAIR, rc1 package | registry parity tests, golden scenario, package smoke, this matrix |

The deterministic suite remains the release gate:

```bash
python -m coverage run -m unittest discover -s tests -t .
python -m coverage report
pytest -q
ruff check .
mypy src/benchwork
python3 scripts/ci/check-schemas.py
python3 scripts/ci/check-doc-links.py
python3 scripts/ci/check-release-policy.py
```

The M17 golden path is published under
[`examples/phase2-final`](../../examples/phase2-final/README.md). It exercises
an accepted `bench.study.audit` proposal, replacement Protocol preview/commit,
registered implementation and Runs, Alembic analysis, Assessment, and a
human-sealed `REPAIR` Decision through Chronicle replay.

## 2026-07-31 Claude Code CLI Tier 1 trial

- Fresh ephemeral Claude Code CLI `2.1.220` conversations loaded the Benchwork
  MCP server with `--strict-mcp-config` against a temporary project outside the
  source repository. The server reported `connected` and all 38 registry tools
  were discovered.
- `benchwork_status` and `benchwork_next_actions` both returned `ok=true` with
  `mcp-tool-result/1.0`, from an explicit request and from the broad request
  "What should we do next for this study?" while 26 non-MCP tools remained
  available.
- The first bounded Task loop was blocked. `benchwork_open_task` minted the
  Capsule with a hardcoded `codex` Host, so truthful `claude-code` provenance
  was refused with `VALIDATION_REJECTED`. The Host reported the rejection
  rather than resubmitting a false provenance.
- `benchwork_open_task` now accepts the optional `host_session` argument that
  the completion tools already took, defaulting to `codex` and refusing an
  unregistered Host. The repaired loop completed `bench.code.inspect` as
  `TK-B280B5160682` with Capsule host `claude-code`, Ward `PASS`, and Receipt
  `RC-47D74468807A`.
- The Host used only `Read` alongside the Benchwork tools, matching the Capsule
  Circle. Deep Doctor reported 2 verified Chronicle events with an intact
  Receipt chain, and the source repository had no `.benchwork/` directory.
- Evidence is published under
  [`examples/phase2-final/host-claude-code`](../../examples/phase2-final/host-claude-code/README.md).
- IDE execution and External Review were not exercised; `HOST-IDE-001` and
  `WAITING_FOR_DISCLOSURE_AUTHORIZATION` are unchanged.

## 2026-07-30 M17 rc1 trial

- The Python wheel and source distribution built as `0.3.0rc1`; Twine accepted
  both. A force-installed wheel initialized a fresh project, passed Deep
  Doctor, loaded all packaged schemas, and discovered 38 registry tools.
- The local marketplace installed
  `0.3.0-rc.1+codex.20260730080053`. The source manifest was restored to the
  release version `0.3.0-rc.1` after cache-busted installation.
- A fresh ephemeral Codex CLI `0.145.0` read-only conversation explicitly
  selected `$benchwork-orchestrate`. `benchwork_status` and
  `benchwork_next_actions` both returned `ok=true` with
  `mcp-tool-result/1.0`.
- A second fresh conversation implicitly selected
  `benchwork:benchwork-orchestrate` for “What should we do next for this
  study?” and made the same two read-only MCP calls.
- Neither CLI trial used shell or file-edit tools. The temporary project's
  Chronicle remained at zero events after plugin installation and both calls,
  and the source repository had no `.benchwork/` directory.
- VS Code `1.122.0` and the `openai.chatgpt` extension were installed, but no
  display variable or graphical extension Host was available. IDE execution
  therefore remains `HOST-IDE-001: BLOCKED_BY_ENVIRONMENT`.
- No external diff review was attempted or disclosed. External Review remains
  `WAITING_FOR_DISCLOSURE_AUTHORIZATION`.

## 2026-07-30 Host trial

- Codex CLI `0.145.0` loaded Benchwork `0.3.0-alpha.1` from
  `benchwork-local` in fresh, read-only conversations.
- Explicit `$benchwork-orchestrate` selection discovered `mcp__benchwork` and
  called `benchwork_status`, then `benchwork_next_actions`; both returned
  successful `mcp-tool-result/1.0` envelopes.
- The broad request “What should we do next for this study?” implicitly
  selected `benchwork:benchwork-orchestrate` and followed the same read order.
- Cache-busted upgrade and rollback both installed successfully and did not
  create `.benchwork/` in the source repository.
- The official Codex VS Code extension was installed and shared the CLI MCP
  configuration, but the headless machine had no display or running extension
  Host. This is `HOST-IDE-001: BLOCKED_BY_ENVIRONMENT`.
- An external `codex exec review --uncommitted` attempt was denied because the
  CLI/IDE acceptance authorization did not separately approve disclosure of the
  uncommitted diff. This is
  `WAITING_FOR_DISCLOSURE_AUTHORIZATION`, confirming the intended boundary.
