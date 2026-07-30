# Phase 2 acceptance matrix

Phase 2 uses the
[Acceptance Exception Policy](plugins/acceptance-exception-policy.md). An
unavailable optional Host and a correctly denied disclosure are explicit
states, not product failures.

## Release acceptance

| Boundary | Status | Release effect | Evidence |
| --- | --- | --- | --- |
| Tier 0 — Kernel | PASS | Required | Chronicle, Schema, Ward, Capability, replay, and deterministic suites |
| MCP | PASS | Required | in-memory and spawned-STDIO discovery, envelopes, pagination, Task and canonical tool tests |
| Tier 1 — CLI Host | PASS | Required before Phase release | fresh Codex CLI explicit/implicit Skill trials and MCP calls |
| Tier 2 — IDE Host | BLOCKED_BY_ENVIRONMENT (accepted) | Does not block Core/MCP/CLI | `HOST-IDE-001`; extension installed, no graphical extension Host available |
| External Review | WAITING_FOR_DISCLOSURE_AUTHORIZATION | Does not block local review or Core/MCP/CLI | Disclosure Gate denied an unapproved diff review |

The IDE exception has no impact on Core, MCP, or CLI acceptance. It must be
closed before a public IDE integration release.

External Review remains pending until a researcher approves the exact source,
files, disclosure flags, and destination. No diff was uploaded during this
acceptance run.

The hardened deterministic gate completed with 135 unittest cases (one
environment-dependent subprocess skip), 134 pytest cases, 167 subtests, and
81% branch-aware coverage. Ruff and mypy completed without findings.

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
