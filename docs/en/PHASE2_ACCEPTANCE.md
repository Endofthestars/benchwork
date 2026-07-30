# Phase 2 acceptance matrix

| Milestone | Acceptance | Evidence |
| --- | --- | --- |
| M11 — The Grimoire | Plugin-first boundary, seven Skills, AGENTS.md, repo marketplace | RFC-0008; plugin validator; skill validators |
| M12 — The Instrument | STDIO server, instructions, read tools, envelopes, pagination | MCP in-memory and subprocess tests |
| M13 — The Familiar | Open/get/complete/fail Task loop and Host Session provenance | `tests/mcp/test_runtime.py` |
| M14 — The Wards | Startup, pre-tool, and post-tool hooks; direct state-write denial | `tests/hooks/test_hooks.py` |
| M15 — The Working | Canonical writes, preview/commit Seals, Runs, Alembic, seven workflows | runtime tests and existing lifecycle/Alembic suites |
| M16 — Trial of the Familiar | Marketplace package, validation, fresh client discovery | plugin validation, `tests/interactive/test_codex_contract.py`, install/upgrade/rollback trials, STDIO subprocess trial, and the CLI trial below |

The deterministic suite is the release gate:

```bash
.phase2-work-venv/bin/python -m coverage run -m unittest discover -s tests -t .
.phase2-work-venv/bin/python -m coverage report
pytest -q
ruff check .
mypy src/benchwork
python3 scripts/ci/check-schemas.py
python3 scripts/ci/check-doc-links.py
python3 scripts/ci/check-release-policy.py
```

## 2026-07-30 local trial

- Codex CLI `0.145.0` loaded Benchwork `0.3.0-alpha.1` from
  `benchwork-local` in fresh, read-only conversations.
- Explicit `$benchwork-orchestrate` selection discovered `mcp__benchwork` and
  called `benchwork_status`, then `benchwork_next_actions`; both returned
  successful `mcp-tool-result/1.0` envelopes.
- The broad request “What should we do next for this study?” implicitly
  selected `benchwork:benchwork-orchestrate` and followed the same read order.
- A cache-busted upgrade and rollback to `0.3.0-alpha.1` both installed
  successfully. The post-rollback MCP status call returned `ok: true`.
- Install, upgrade, and rollback did not create `.benchwork/` in the source
  repository. MCP discovery was exercised in a separate initialized trial
  project, which was removed after the trial.
- The official OpenAI Codex VS Code extension `26.721.41059` was installed
  against VS Code `1.122.0`. The extension and CLI share `config.toml`, and the
  Benchwork server is visible there as enabled. This headless host had no
  display or running extension host, so a real IDE chat selection/call trial
  remains pending.
- An external `codex exec review --uncommitted` attempt was denied by the
  execution approval layer because CLI/IDE acceptance authorization did not
  separately authorize disclosure of the uncommitted diff for model review.

The local deterministic gate completed with 128 tests, 167 subtests, and 81%
coverage. Manual IDE and desktop trials should run the same representative
prompt set in a new conversation after each plugin reinstall.
