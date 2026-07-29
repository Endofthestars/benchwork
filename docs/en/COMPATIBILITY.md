---
language: en
canonical: true
---

# Compatibility Policy

Benchwork `0.2` is a public Alpha and follows Semantic Versioning for the Python
distribution. Persisted schemas use independent explicit versions. A package
minor version may add a new schema version but must not silently reinterpret an
existing schema identifier.

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

## Compatibility rules

- Chronicle versions never mix inside one ledger.
- Published schemas remain available for validation and explicit migration.
- Unknown persisted fields fail closed.
- Public CLI aliases remain available for the documented migration window.
- Exit codes and JSON error codes are machine-interface contracts.
- Alpha APIs may change only with migration notes and replay tests.
