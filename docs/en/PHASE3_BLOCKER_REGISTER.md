# Phase 3 blocker register

This register records implementation boundaries found by local independent
review. It is not an authority grant, RFC acceptance record, or a substitute
for a complete Chronicle/Storage replay.

## Active blockers

| Area | Why the installed local comparator must fail closed | Required before a local reducer/comparator may be installed |
| --- | --- | --- |
| RFC-0012 retry scheduling and readiness | The published Event payload has opaque terminal-reason, backoff, queue, deadline, and freshness values. The repository has neither an immutable Specification resolver nor a non-forgeable resolver Receipt/authorization result. A self-Sigiled “resolution” record would let a caller authorize `ACTIVE -> RETRY_WAIT -> QUEUED`. | A resolver-owned, verified eligibility and readiness result; exact Specification and terminal/settlement/assurance bindings; persistent eligibility binding for the State; and a continuous prefix test through the next Attempt allocation. |
| RFC-0013 quota-pressure transitions | Quota counters are independent projected entities, but the current closed Storage State does not retain their per-counter revisions. Reusing the Journal sequence would produce invalid entity-revision algebra. | An approved State/Schema evolution that persists independent quota-counter revisions, plus exact `observed_at`/clock semantics and pressure transition tests. |
| RFC-0013 canonical-reference release | Local facts can close self-Sigils and a Head advance, but cannot prove that a Chronicle suffix contains no binding Event. | An authoritative full Chronicle replay/adaptor or an externally verified absence authority. The public reducer remains fail closed. |
| Full RFC-0013 Storage replay | The prefix dispatcher still deliberately rejects transfer, replica, materialization, quarantine, retention, GC, and disposition Events without their authoritative immutable-record and backend facts. | Reducers and supplied-facts comparators for each Event family, followed by retained-output, quarantine, and recovery prefix fixtures. |

## Local review record

The following local reviews were performed in the active project session. They
are advisory implementation review evidence only; no source was disclosed to
an external reviewer.

| Scope | Disposition | Evidence |
| --- | --- | --- |
| Result acceptance, Outcome and assurance-Claim local closures | Findings were fixed before the corresponding commits; the installed paths retain fail-closed authority boundaries. | `ab5ed53`, `c64b377`; focused suite and full test baseline in the exit audit. |
| Lease fencing and retained multi-Attempt selection | A stale-lease/fence-regression finding was fixed before merge. | `d4fa717`; final-floor guards and replay tests. |
| Canonical-reference commit/release local facts | Closure, quota-settlement, and release-absence findings were resolved by retaining fail-closed release behavior where authority is missing. | `9f1b605`, `f74cc66`; Storage contract tests. |
| Proposed retry and quota-pressure reducers | Rejected, not merged: their initial forms would have treated caller-controlled inputs as authority or violated independent entity revisions. | No implementation commit; blockers above describe the required design inputs. |

## Verification baseline

Run from the repository root:

```bash
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/ci/check-phase3-contracts.py
```

These commands establish only the contract-only local slice. They do not
accept any RFC, establish backend truth, or grant Athanor/Chronicle authority.
