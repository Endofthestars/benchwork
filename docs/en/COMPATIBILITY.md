---
language: en
canonical: true
---

# Compatibility Policy

Benchwork `0.3` is an Alpha research-control-plane release. The Python
distribution follows PEP 440; the Codex plugin follows Semantic Versioning.
Persisted schemas, MCP envelopes, plugin workflow metadata, and Host
provenance use independent explicit versions. A package release may add a new
contract version but must never silently reinterpret an existing identifier.

The Phase 2 contract freeze begins with `0.3.0rc1`. “Frozen” means the existing
name and versioned meaning are reviewable compatibility commitments; it does
not promote Alpha interfaces to Stable.

## Stability levels

| Level | Compatibility promise |
| --- | --- |
| `experimental` | Breaking changes are allowed and must be identified in release notes. |
| `alpha` | Breaking changes require an accepted RFC, migration guidance, and replay or contract tests. |
| `stable` | No breaking change within the supported major version. |

All Phase 2 MCP tools, plugin workflows, and their versioned companion
metadata are `alpha` unless a more specific document says otherwise.

## Frozen Phase 2 surfaces

| Surface | Contract | Stability |
| --- | --- | --- |
| MCP tool names and envelopes | [MCP API Policy](MCP_API_POLICY.md) | `alpha` |
| Codex plugin, Skills, and Host rules | [Plugin API Policy](PLUGIN_API_POLICY.md) | `alpha` |
| Host acceptance tiers and exceptions | [Host Support Matrix](HOST_SUPPORT_MATRIX.md) | `alpha` |
| Persisted scientific state | Published JSON Schemas and accepted RFCs | Per schema/RFC |

## Provisional names

The following names are intentionally not frozen for a stable release:

| Surface | Current provisional value |
|---|---|
| Python distribution | `benchwork-arcana` |
| CLI | `bwork` |
| Python import | `benchwork` |
| Schema URL domain | `https://benchwork.dev/schemas/` |

The first non-development release is blocked until an accepted RFC freezes all
four values and this table marks them `frozen`.

## Supported platform

The M10 reference kernel is supported and tested on Linux with Python
3.11-3.14. Other POSIX systems may work but are not release-gated. Windows is
not an M10-supported platform; this explicit POSIX-only declaration remains
until Windows locking, atomic replacement, and package smoke tests enter CI.

The `0.3.0rc2` POSIX installer has a separate support boundary: macOS
x86_64/arm64, glibc Linux x86_64/arm64, and Windows through WSL2. Native
Windows and musl-only Linux remain unsupported by `install.sh`.

## Compatibility rules

- Chronicle versions never mix inside one ledger.
- Published schemas remain available for validation and explicit migration.
- Unknown persisted fields fail closed.
- Public CLI aliases remain available for the documented migration window.
- Exit codes and JSON error codes are machine-interface contracts.
- Alpha APIs may change only with migration notes and replay tests.
- MCP tool removals, renames, permission changes, and request or result
  reinterpretations are breaking changes.
- Plugin installation, upgrade, rollback, and removal never mutate canonical
  `.benchwork/` state.
- Host-specific packaging may change without changing the host-neutral
  scientific contract.
