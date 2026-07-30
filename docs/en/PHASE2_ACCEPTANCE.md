# Phase 2 acceptance matrix

| Milestone | Acceptance | Evidence |
| --- | --- | --- |
| M11 — The Grimoire | Plugin-first boundary, seven Skills, AGENTS.md, repo marketplace | RFC-0008; plugin validator; skill validators |
| M12 — The Instrument | STDIO server, instructions, read tools, envelopes, pagination | MCP in-memory and subprocess tests |
| M13 — The Familiar | Open/get/complete/fail Task loop and Host Session provenance | `tests/mcp/test_runtime.py` |
| M14 — The Wards | Startup, pre-tool, and post-tool hooks; direct state-write denial | `tests/hooks/test_hooks.py` |
| M15 — The Working | Canonical writes, preview/commit Seals, Runs, Alembic, seven workflows | runtime tests and existing lifecycle/Alembic suites |
| M16 — Trial of the Familiar | Marketplace package, validation, fresh client discovery | plugin validation, `tests/interactive/test_codex_contract.py`, install/uninstall smoke test, and STDIO subprocess trial |

The deterministic suite is the release gate:

```bash
pytest -q
ruff check src tests plugins/benchwork/hooks
mypy src/benchwork
python3 scripts/ci/check-schemas.py
python3 scripts/ci/check-doc-links.py
python3 scripts/ci/check-release-policy.py
```

Manual CLI, IDE, and desktop trials should run the same representative prompt
set in a new conversation after each plugin reinstall. Surface-specific UI
behavior is recorded separately from canonical acceptance.
