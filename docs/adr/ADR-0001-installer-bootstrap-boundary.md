# ADR-0001: Keep the shell bootstrap small and move configuration to Python

- Status: accepted
- Date: 2026-07-30
- Owners: Endofthestars
- Related RFCs: RFC-0010

## Context

The public installer must run through `/bin/sh` on several operating systems,
but it also needs strict JSON, safe archive handling, atomic state, and
idempotent Host configuration.

## Decision

`install.sh` performs only preflight, release resolution, backend bootstrap,
exact package installation, and invocation of `bwork install`. The installed
Python package performs every structured or persistent operation.

Repository shell helpers may support testing and release assembly, but the
published `install.sh` is a self-contained immutable asset and never sources
downloaded modules.

## Consequences

Dry-run planning is available before package installation, while detailed
configuration diagnostics become available after the exact package is
installed. Repair can reinstall the recorded exact package before delegating
to Python if the executable link is missing.

## Compatibility

The boundary is an installer implementation detail. The command, environment,
manifest, state, and status contracts are public Alpha interfaces governed by
RFC-0010.

## Validation

Shell tests prove that dry-run and plan modes create no persistent state.
Python tests cover strict JSON, state, plugin extraction, Host configuration,
rollback, and uninstall.
