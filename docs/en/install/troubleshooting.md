---
language: en
canonical: true
---

# Installer troubleshooting

Every failure prints a recovery action. Start with:

```bash
bwork install status --json
bwork install doctor --json
bwork mcp check --json
```

## Channel unavailable

The selected channel has no published descriptor. During the RC period use:

```bash
sh install.sh --channel rc
```

## Missing JSON parser

Install `python3` or `jq >=1.6`, then rerun. This check happens before uv
bootstrap by contract.

## `bwork` is not on PATH

Use the exact export printed by the installer, or rerun with `--modify-path`.
The installer edits only the profile matching the detected shell.

## Host configuration is blocked

Run `codex --version` or `claude --version`, then inspect the corresponding
Host check. Managed workplace policy can forbid local marketplaces or MCP
configuration; the installer reports this rather than editing undocumented
configuration fields.

## Repair

```bash
curl -LsSf https://benchwork.dev/install.sh | sh -s -- --repair
```

Repair uses the recorded exact version and does not upgrade unless a version
or channel is supplied.
