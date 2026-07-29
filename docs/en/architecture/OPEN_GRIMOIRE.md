---
language: en
canonical: true
---

# Open Grimoire

Open Grimoire is Benchwork's versioned extension boundary. The Alpha accepts a
local directory containing `grimoire.json` and one or more data-only
`rite/1.0` JSON definitions. It never imports or executes extension code.

## Pinning

The manifest declares an exact Grimoire SemVer, the compatible Benchwork API,
and a canonical SHA-256 Sigil for every Rite. Installation validates those
contracts and copies the manifest and definitions into
`.benchwork/grimoires.json`. A later change to the source directory therefore
cannot alter the installed Rite.

The same Grimoire version cannot be replaced with different content. A Rite ID
cannot override a built-in Rite or collide with another installed Grimoire.
When a Working starts, Athanor embeds the complete Rite definition and its
Sigil in Chronicle, so replay no longer depends on the registry.

## Filesystem boundary

Rite paths must remain under the Grimoire directory. Absolute paths, parent
traversal, symlink escapes, duplicate JSON keys, oversized JSON files, invalid
Schemas, and duplicate stage names fail closed. The Alpha supports at most 128
Rites per manifest and 64 stages per Rite.

## Trust boundary

Sigils detect content drift; they are not publisher signatures. Alpha
installation is deliberately local and data-only. Remote fetching, executable
adapters, Capability or Policy Packs, publisher identity, and signature trust
are outside this version.

Authors can calculate the canonical digest used by a manifest and then install
the directory:

```bash
bwork grimoire sigil rites/ablation-study.json
bwork grimoire install .
```
