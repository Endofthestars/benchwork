---
language: en
canonical: true
---

# Offline installation

The first installer RC does not implement a `file://` or unsigned offline
bundle mode. `BENCHWORK_INSTALLER_BASE_URL` must use HTTPS.

For an isolated machine, transfer the exact wheel, plugin archive, release
manifest, `SHA256SUMS`, SBOM, and provenance from a trusted online machine.
Verify `SHA256SUMS` independently before installing the wheel with an existing
offline-capable uv or pipx environment.

Host configuration can then be performed with the local `bwork install`
commands. This is an expert/manual path and is not part of the RC Golden Trial.
