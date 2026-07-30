---
language: en
canonical: true
---

# Installer RC acceptance

This report must be completed from the exact `v0.3.0rc2` tag. `PASS` is
forbidden while any required trial is `NOT_RUN`, `FAIL`, or lacks retained
evidence.

## Installer

- version: `0.3.0rc2`
- platforms: Linux/macOS/WSL2
- backends: uv, pipx
- public URLs: pending tagged publication

## Release assets

- install.sh: pending
- release manifest: pending
- plugin archive: pending
- SHA256SUMS: pending
- SBOM: pending
- provenance: pending

## Host setup

- Codex MCP: NOT_RUN
- Codex Plugin: NOT_RUN
- Claude MCP: NOT_RUN — experimental
- known limitations: local marketplace refresh may require a new Host process

## Safety

- no-root verification: NOT_RUN
- no project-state mutation: automated PASS required
- archive security: automated PASS required
- checksum failures: automated PASS required
- config backups: automated PASS required
- disclosure boundary: automated/document review PASS required

## Tests

- static shell checks: NOT_RUN
- Linux matrix: NOT_RUN
- macOS matrix: NOT_RUN
- WSL2: NOT_RUN
- idempotency: NOT_RUN
- upgrade/rollback: NOT_RUN
- uninstall: NOT_RUN

## Golden commands

```bash
sh install.sh --help
sh install.sh --dry-run --version 0.3.0rc2
sh install.sh --version 0.3.0rc2 --with-codex
bwork install doctor
bwork mcp check
bwork plugin check
bwork install uninstall --dry-run
```

## Final decision

`REPAIR` until every required row above has accepted evidence.
