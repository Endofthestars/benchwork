# Changelog

All notable changes are recorded here. Benchwork remains a prerelease and uses
versioned schemas plus explicit migration notes for compatibility.

## 0.3.0rc2 — The Invitation

- Added the auditable POSIX installer and exact release/channel manifests.
- Added uv-first isolated installation, pipx fallback, plugin staging,
  installer state, Host diagnostics, repair, rollback, and uninstall.
- Added checksummed release assets, SBOM/provenance generation, installer CI,
  GitHub Pages publication, and installation documentation.

See [release notes](docs/en/releases/0.3.0rc2.md).

## 0.3.0rc1 — The Instrumentarium Seal

- Froze the Phase 2 host-native Plugin and MCP architecture.
- Packaged seven Codex Skills, trusted guardrail hooks, and the STDIO MCP
  connection.
- Published and registered 38 typed scientific-control-plane tools.
- Added immutable preview/commit scientific Seals and Host Session provenance.
- Added Review Request and Review Artifact provenance with an explicit
  external disclosure gate.
- Formalized Kernel, CLI, and IDE Host acceptance tiers and accepted
  environment/authorization exception states.
- Added the deterministic Phase 2 golden `REPAIR` scenario.

See [release notes](docs/en/releases/0.3.0rc1.md) and
[migration guide](docs/en/migrations/0.3.0rc1.md).

## 0.2.0rc1 — The Seal

- Completed the Phase 1 deterministic Kernel, Chronicle, Ward, Athanor,
  Capability, replay, integrity, and release acceptance baseline.
