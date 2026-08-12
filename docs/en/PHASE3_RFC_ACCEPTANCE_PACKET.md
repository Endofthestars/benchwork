# Phase 3 RFC acceptance packet

This packet prepares a human acceptance review; it does not accept, seal, or
change the status of any RFC. Each RFC remains `draft` until the project owner
explicitly accepts it.

## Shared review boundary

The current baseline is 214 published Schemas, the contract-only Phase 3 gate,
and the bounded `benchwork-local-*/0.1` runtime. The reproducible commands
are in the [exit audit](PHASE3_EXIT_AUDIT.md#verified-baseline). Those checks
do not prove a complete RFC-0012 Journal replayer, a complete RFC-0013 Storage
backend, canonical Result acceptance, or scientific authority. The exact gaps
are maintained in the [blocker register](PHASE3_BLOCKER_REGISTER.md).

## Per-RFC acceptance checklist

| RFC | Evidence ready for review | Acceptance blocker |
| --- | --- | --- |
| RFC-0011 — Sanctum Execution Model | Published Schema family, bounded local runtime lifecycle tests, fail-closed MCP/runtime boundaries, and a [retained independent local trust-boundary review](PHASE3_THREAT_MODEL_REVIEW.md). | Formal RFC acceptance and the external authority evidence remain pending. |
| RFC-0012 — Job, Lease, and Worker Protocol | Execution State/Journal schemas; Job Outcome contracts; multi-Attempt, lease-fence, terminalization, assurance-Claim, cancellation, expiry, duplicate-delivery, and restart tests. | Retry scheduling/readiness still lacks externally verified Specification, deadline, freshness, and resolver facts; complete Storage/Result authority replay is also unavailable. |
| RFC-0013 — Artifact Storage Model | Storage schemas; initialization, activation, recovery, message rejection, failed legacy-protection, Reference Set, canonical-reference, provenance-policy registration, and active-Store retention-policy registration for locally closed PROJECT/Reference Set scopes. | Transfer lifecycle, quota revisions, retention initialization/BLOB/PROGRAM scopes, full backend replay, and authoritative Chronicle absence are incomplete. |
| RFC-0014 — Patch Promotion Protocol | Published Patch schemas and contract tests for journal, bundle, checkpoint, mutation intent, target guard, attempt, outcome, recovery record, and the retained [local trust-boundary review](PHASE3_THREAT_MODEL_REVIEW.md). | Requires final cross-RFC replay/Storage evidence and reference Host-native adapter evidence before the Phase 3 release gate can be asserted. |
| RFC-0015 — Experiment Executor API | Typed request/Outcome schemas; strict Result v2 local closure; supplied-facts acceptance comparator; Result/Observation contract tests. | Comparator intentionally does not grant canonical acceptance; it still requires externally verified Chronicle/Storage/Outcome facts. |

## Required human decision

For each RFC, the reviewer must make one explicit choice:

1. accept the exact draft and its documented boundaries;
2. request named changes; or
3. defer acceptance pending named evidence.

No blanket Phase 3 approval changes five `draft` RFCs into accepted documents.
Any acceptance record must identify the exact RFC, version, reviewed commit,
reviewer, time, and rationale.
