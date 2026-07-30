---
language: en
canonical: true
---

# Installer security

The installer is a user-scoped bootstrap and configuration tool. It is not a
privileged package manager.

It uses HTTPS with certificate validation, bounded redirects, timeouts,
retries, and download sizes. Release assets are exact-versioned and verified
with SHA-256 before execution or extraction. Plugin extraction rejects links,
devices, absolute paths, traversal, duplicate/case-colliding names, control
characters, and oversized members.

Installer state, plugins, backups, and uninstall support live outside research
projects under `${XDG_DATA_HOME:-$HOME/.local/share}/benchwork`. Writes use
private permissions and atomic replacement.

The installer never:

- invokes `bwork init`, migration, recovery, or Seal commands;
- creates or changes `.benchwork/`;
- installs or launches a model Host;
- invokes a paid model session;
- enables external Review disclosure;
- logs Host configuration contents or secrets;
- uses `eval`, sources downloads, disables TLS, or invokes `sudo`.

Checksums detect corruption and origin drift. A checksum served from the same
compromised origin is not a complete authenticity system. The RC records this
trust boundary; signed Sigstore or equivalent verification is deferred.

Report installer vulnerabilities through the repository's private GitHub
security advisory form.
