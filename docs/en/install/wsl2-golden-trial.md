---
language: en
canonical: true
---

# WSL2 Golden Trial

Use a clean, supported WSL2 distribution and record its Windows build, WSL
version, distribution release, kernel, shell, architecture, Python/parser
availability, backend version, and exact installer checksum.

1. Confirm no `bwork`, installer state, or Benchwork Host entries exist.
2. Inspect the exact versioned installer.
3. Run the dry-run and retain its plan.
4. Install `0.3.0rc2` without Hosts and run all installation checks.
5. Install again and compare state, Host configuration, plugin entries, and
   PATH blocks byte-for-byte.
6. Configure Codex if available, start a fresh process, and verify plugin/MCP
   discovery without invoking a model.
7. Exercise repair, upgrade/rollback fixtures, and uninstall.
8. Confirm a prepared research fixture and its `.benchwork/` tree are
   byte-identical before and after.

Attach command output and checksums to the installer acceptance report. Do not
record secrets or full Host configuration.
