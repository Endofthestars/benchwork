# Phase 3 local threat-boundary review

## Status and scope

This is an independent local implementation review conducted against commit
`7ea893b`. It is retained Phase 3 evidence only. It is not an RFC acceptance
decision, an Athanor Receipt, or proof of any external Storage, Chronicle,
Ward, approval, or Worker authority.

The review examined the RFC-0011 and RFC-0013 trust boundaries in:

- `src/benchwork/execution.py`
- `src/benchwork/execution_contracts.py`
- `src/benchwork/artifact_storage_contracts.py`
- `src/benchwork/patch_promotion_contracts.py`
- MCP registration/runtime code, Phase 3 documents, and relevant tests

## Conclusion

No P1 or P2 finding was identified. The installed local slice does not treat
a self-Sigil, a caller-supplied fact, a Worker result, or a local comparator as
external authorization. Unresolved authority-bearing paths remain fail closed.

## Reviewed boundaries

| Boundary | Review conclusion |
| --- | --- |
| MCP tool surface | Only the fixed read, task, canon, and experiment modules are registered. The local `benchwork_start_job` helper is not published as an MCP tool. |
| Worker and local execution | `execution.py` is bounded operational code: it does not interpret arbitrary commands or append Chronicle records. Its trusted-local terminal hook does not make the resulting outcome acceptance-eligible. |
| Self-Sigil and supplied facts | Result v2 and supplied-facts helpers perform local deterministic closure only; they do not resolve Chronicle, Storage, Ward, approval, or acceptance authority. |
| Storage and Chronicle | Uninstalled Storage events fail closed. Canonical release requires an authoritative suffix-absence proof, while Storage replay/runtime authority functions reject in the contract-only slice. |
| Patch promotion | The contract validates wire and supplied facts only; its runtime-authority entry point rejects. |
| Status documents | The blocker register and acceptance packet consistently describe the local slice as non-authoritative and leave unresolved paths fail closed. |

## Reproduction evidence

The reviewer ran the following checks in `/Users/momo/benchwork-phase3-recovery`:

```bash
git status --short && git rev-parse --short HEAD
PYTHONPATH=src .venv/bin/python scripts/ci/check-phase3-contracts.py
```

The worktree was clean at `7ea893b`; the gate validated 214 published Schemas,
ran 182 tests, and reported Ruff clean for its checked source set.

## Residual assumptions

- `ExecutionService.record_terminal` is a trusted local-adapter hook. It is
  not MCP-exposed and cannot make an outcome acceptance-eligible, but its
  safety still depends on the host process boundary.
- A local contract gate cannot establish authoritative Chronicle suffixes,
  Storage backend state, or Ward/Registry/approval facts. Those prerequisites
  remain explicitly outside this review and must be supplied by their owning
  authoritative systems.

These residual items keep the RFC acceptance gate open; they are not evidence
that the bounded local implementation crosses those boundaries.
