# Phase 3 exit audit

This document records the release-exit evidence required by the Phase 3
roadmap. It is an audit aid, not an RFC acceptance record and not a claim of
runtime or scientific authority.

| Exit requirement | Current evidence | Status |
| --- | --- | --- |
| Five accepted RFCs | RFC-0011 through RFC-0015 remain `draft`. | Blocked by explicit RFC acceptance. |
| Executable Schemas and examples | `scripts/ci/check-schemas.py` validates 214 published Schemas; Phase 3 fixtures are checked by the contract suite. | Present. |
| Threat-model review | RFC-0011 and RFC-0013 contain threat models, but there is no recorded independent review decision. | Missing retained review evidence. |
| Conformance suite | `scripts/ci/check-phase3-contracts.py` validates the contract-only local slice. It deliberately does not establish full conformance. | Partial. |
| Local reference vertical slice | Local `benchwork-local-*/0.1` storage and execution primitives retain bounded operational evidence. RFC-0012 replay preserves multi-Attempt history, fresh retry-allocation identities, lease-fence monotonicity, Result acceptance local closure, and supplied-facts assurance-Claim closure. Retry scheduling/readiness and complete Storage replay remain unavailable; all authority-bearing paths fail closed. | Partial. |

## Verified baseline

The current repeatable baseline is:

```bash
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/ci/check-phase3-contracts.py
```

It is evidence for contract integrity and the bounded local slice only. It
does not change the ownership rules in the RFCs: Athanor remains the only
canonical authority, and the Executor cannot promote a Worker result into a
scientific fact.

## Remaining implementation order

1. Install RFC-0012 retry scheduling and readiness with the missing supplied
   Specification, terminal-event, deadline, and freshness facts; then
   demonstrate a terminal Attempt through scheduling, readiness, new
   allocation, and restart replay.
2. Install the required RFC-0013 Storage reducers and prove retained output,
   quarantine, and recovery projections from a complete Storage prefix.
3. Extend the existing supplied-facts Result and assurance-Claim comparators
   only to consume their remaining externally verified resolver results. A
   `CLAIMED` outcome already cannot be established by an opaque Sigil alone in
   the installed replay path.
4. Resolve the authority and State-evolution prerequisites in the
   [Phase 3 blocker register](PHASE3_BLOCKER_REGISTER.md), then run the
   expanded conformance suite and retain independent threat-model review
   evidence.
5. Request explicit acceptance for each RFC. This repository forbids sealing
   an RFC without that confirmation.
