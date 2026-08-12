# Phase 3 contract gate

Run the repeatable Phase 3 evidence gate from the repository root:

```bash
.venv/bin/python scripts/ci/check-phase3-contracts.py
```

It verifies the published Schema family, RFC-0012 execution and storage
contract validators, RFC-0015 Job Outcome validator, local durable
start/observe/cancel/restart flow, and the MCP boundary that rejects generic
execution authority.

The gate is intentionally contract-only.  A passing run is evidence for the
local reference slice; it does not claim a complete RFC-0012 Journal replayer,
RFC-0013 Storage backend, RFC-0015 Result acceptance, remote Worker support,
or scientific authority.  Those remain the Phase 3 release-exit work named in
the [roadmap](ROADMAP.md#phase-3--sanctum-04).
