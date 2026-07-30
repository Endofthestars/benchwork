---
language: en
canonical: true
---

# Quick install

Benchwork's installer is an RC interface. Select the RC channel explicitly:

```bash
curl -LsSf https://benchwork.dev/install.sh | sh -s -- --channel rc
```

Safer inspect-first flow:

```bash
curl -LsSf https://benchwork.dev/install.sh -o install-benchwork.sh
less install-benchwork.sh
sh install-benchwork.sh --channel rc
rm install-benchwork.sh
```

For a reproducible exact install:

```bash
curl -LsSf https://benchwork.dev/releases/0.3.0rc2/install.sh \
  -o install-benchwork.sh
sh install-benchwork.sh --version 0.3.0rc2
```

The immutable GitHub Release fallback is:

```bash
curl -LsSf \
  https://github.com/Endofthestars/benchwork/releases/download/v0.3.0rc2/install.sh |
  sh -s -- --version 0.3.0rc2
```

Exact-version installs resolve the manifest and all release assets from that
same immutable GitHub Release, so this fallback does not depend on the
unversioned installer endpoint after the script has started.

The unqualified stable channel intentionally fails until Benchwork publishes a
stable package.

Host integration is opt-in:

```bash
sh install-benchwork.sh --version 0.3.0rc2 --with-codex
sh install-benchwork.sh --version 0.3.0rc2 --with-claude
```

Claude support is an experimental MCP-only preview. The installer does not
install Codex, Claude Code, or a Claude plugin.

Verify:

```bash
bwork install doctor
bwork mcp check
bwork plugin check
bwork host check codex
```

The result must report `Project state: NOT_TOUCHED`.
