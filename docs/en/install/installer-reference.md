---
language: en
canonical: true
---

# Installer reference

## Platforms and prerequisites

The POSIX installer supports macOS x86_64/arm64, glibc Linux
x86_64/arm64, and WSL2. It requires a writable `HOME`, `curl` or `wget`, a
SHA-256 tool, and either `python3` or `jq >=1.6` for strict release JSON.

Native Windows, musl-only Linux, root/system-wide installation, and containers
without a writable `HOME` are unsupported.

## Options

```text
--version VERSION
--channel stable|rc|nightly
--backend auto|uv|pipx
--install-dir PATH
--bin-dir PATH
--with-codex
--with-claude
--without-hosts
--plugin-scope user|project|none
--project-root PATH
--modify-path
--no-modify-path
--dry-run
--print-plan
--yes
--quiet
--verbose
--json
--uninstall
--repair
--purge
--force
```

CLI values override environment values, which override defaults. Replace each
hyphenated option with an uppercase `BENCHWORK_` name, for example
`--plugin-scope` → `BENCHWORK_PLUGIN_SCOPE`. Additional variables are
`BENCHWORK_NO_BOOTSTRAP_UV`, `BENCHWORK_NO_TELEMETRY`, and
`BENCHWORK_INSTALLER_BASE_URL`.

`--install-dir` controls `UV_TOOL_DIR` or `PIPX_HOME`; `--bin-dir` controls
`UV_TOOL_BIN_DIR` or `PIPX_BIN_DIR`. Both must be absolute when supplied.

## Confirmation and idempotency

An interactive mutation asks for confirmation unless `--yes` is supplied.
Piped basic CLI installation may proceed without a prompt. Host and shell
profile changes still require explicit flags.

Reinstalling the same release validates existing state and repairs only
installer-owned assets. Repair does not upgrade without an explicit version or
channel. Downgrade requires an exact version and confirmation.

## Status and exit codes

| Code | Meaning |
|---:|---|
| 0 | success or healthy no-op |
| 2 | invalid arguments or preflight rejection |
| 3 | confirmation required or cancelled |
| 4 | integrity or verification failure |
| 5 | download or backend failure |
| 6 | requested Host configuration failure |
| 7 | rollback failure |

JSON mode writes one machine-readable document to stdout. Diagnostics and
actions go to stderr.
