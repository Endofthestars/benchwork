---
title: "RFC-0010: The Invitation Installer Contract"
document_id: BW-RFC-0010
version: 1.0
status: accepted
owner: Endofthestars
date: 2026-07-30
language: en
canonical: true
---

# RFC-0010: The Invitation Installer Contract

## Problem

Benchwork can be installed from PyPI, but the release has no auditable,
host-aware installation path for a researcher who has not cloned this
repository. Ad hoc package installation also cannot verify the Codex plugin,
configure a Host without duplicating configuration, or provide bounded repair
and uninstall behavior.

## Decision

Benchwork publishes a POSIX `install.sh` bootstrap for macOS, Linux, and WSL2.
The bootstrap owns environment detection, immutable release resolution, exact
`uv tool` or `pipx` installation, and delegation to the installed
`bwork install` command. Python owns JSON validation, plugin extraction,
installer state, Host configuration, repair, rollback, and uninstall.

The first installer release is package version `0.3.0rc2`, tag `v0.3.0rc2`,
and plugin version `0.3.0-rc.2`. Exact release assets are immutable. The
unqualified installer resolves the stable channel and fails while no stable
release exists; prereleases require `--channel rc` or an exact `--version`.
Exact versions resolve through the immutable GitHub Release asset set; channel
descriptors resolve through `benchwork.dev`.

The installer state root is
`${XDG_DATA_HOME:-$HOME/.local/share}/benchwork`. Backend tool environments and
executable directories remain backend-owned. `--install-dir` maps to
`UV_TOOL_DIR` or `PIPX_HOME`; `--bin-dir` maps to `UV_TOOL_BIN_DIR` or
`PIPX_BIN_DIR`.

Release JSON is parsed only by `python3` or `jq >= 1.6`. A Host without either
parser fails preflight with an actionable error before any mutation.

## Public command contract

`install.sh` accepts:

```text
--help
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

Every option other than `--help` has a `BENCHWORK_*` environment equivalent.
CLI values override environment values, which override defaults. Unknown
options and invalid boolean values fail. Version and channel are mutually
exclusive, as are repair, uninstall, and normal installation. Quiet and
verbose are mutually exclusive. Host flags conflict with `--without-hosts`.

`bwork` exposes the project-independent installation commands documented in
`docs/en/architecture/COMMAND_SURFACE.md`. They must not discover, initialize,
migrate, recover, or seal research state.

## Invariants

- No operation requires `sudo` or mutates system Python.
- Installer execution never creates or changes `.benchwork/`.
- Host CLIs are detected but never installed.
- Host configuration and shell-profile mutation are opt-in.
- The Codex plugin's bundled MCP server is preferred. A standalone Codex MCP
  entry is a fallback, not a duplicate registration.
- Claude integration is MCP-only and experimental for this release.
- External Review disclosure is never authorized or changed.
- An existing newer Benchwork is never replaced without an exact requested
  version and confirmation.
- Repair retains the installed version unless a version or channel is given.
- Uninstall removes only installer-owned assets and preserves research data.

## Compatibility and migration

PEP 440 package versions, Git tags, and SemVer plugin versions are distinct
fields in the release manifest and must satisfy the compatibility mapping.
Installer state is forward-versioned. Unknown schema versions and unknown
fields fail closed.

The existing `bwork doctor` remains project-scoped. Installation diagnostics
live under `bwork install doctor`.

## Security and integrity

Downloads require HTTPS, bounded redirects, timeouts, retries, and response
sizes. Exact artifacts are verified before execution or extraction. Archives
reject absolute paths, traversal, duplicate names, links, devices, control
characters, and size/count violations.

Checksums protect against accidental corruption and origin drift. They do not
protect against compromise of both the release origin and its checksum
publication. A later RFC will require release signatures.

The installer never evaluates network or user input, sources downloaded
content, logs secrets, or copies Host configuration into diagnostics.

## Alternatives

- A large shell-only installer was rejected because structured configuration
  and archive handling are safer and more testable in Python.
- `pip install --user` and privileged installation were rejected because they
  mutate shared Python environments.
- Requiring Bash was rejected because `/bin/sh` portability is part of the
  public interface.

## Non-goals

Native Windows, system-wide installation, background updates, telemetry,
automatic Host installation, project initialization, external Review
authorization, remote MCP, and stable-channel publication are not part of the
first installer release.

## Acceptance tests

The release must pass static POSIX checks, the declared Linux and macOS matrix,
a WSL2 Golden Trial, malicious-manifest and archive fixtures, idempotent
reinstallation, upgrade/rollback, repair, uninstall, byte-identical
publication checks, and before/after assertions that research state was not
touched.
