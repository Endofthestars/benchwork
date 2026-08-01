---
title: "RFC-0012: Job, Lease, and Worker Protocol"
document_id: BW-RFC-0012
version: 0.1
status: draft
owner: unassigned
date: 2026-07-31
language: en
canonical: true
---

# RFC-0012: Job, Lease, and Worker Protocol

## Status

This draft defines the Phase 3 operational protocol beneath RFC-0011. It
specifies the closed execution contracts, Job, Attempt, Lease, and Worker state
machines, fencing, liveness, retry, logs, result eligibility, assurance
evaluation, journal replay, and local crash recovery required by the `0.4`
reference runtime.

This RFC does not make operational state canonical research state, authorize a
generic MCP execution surface, define physical Artifact storage or Patch
promotion, or accept a Worker result scientifically. RFC-0013 through RFC-0015
remain required for those boundaries. No implementation may claim conformance
until this RFC is accepted and its executable Schemas and conformance fixtures
exist.

## Problem

RFC-0011 establishes that an Executor may coordinate a bounded Attempt without
gaining Athanor's canonical authority. That boundary is insufficient unless
all implementations agree on what happens when:

- two Workers believe they own the same work;
- a Lease expires while a process or external handle remains live;
- a heartbeat or renewal races with cancellation or timeout;
- a Worker sends a duplicate, conflicting, or late result;
- an Attempt fails and a retry begins;
- logs or outputs exceed their bounds;
- computation succeeds but required cleanup or assurance evidence does not;
- the Executor or Host restarts with ambiguous process ownership; or
- an operational journal is truncated, corrupt, or contains an illegal
  transition.

Ad hoc answers can produce split-brain side effects, reuse mutable state across
Attempts, turn a stale result into a Proposal, erase failed Attempts, infer
runtime provenance after a crash, or claim assurance from preflight intent
rather than terminal evidence.

## Decision

Phase 3 uses an append-only operational protocol:

```text
validated execution contracts
        |
        v
      Job
        |
        v
  Attempt allocation -- fresh fence generation
        |
        v
 preflight + Crucible materialization
        |
        v
 Lease offer -> Worker claim -> supervised execution
        |                    |
        |                    +-> bounded heartbeats, logs, result
        v
 revoke | expire | release | fence
        |
        v
 termination + cleanup
        |
        v
 terminal Attempt -> assurance evaluation
        |
        v
 retry or terminal Job
        |
        v
 eligible execution Proposal, never a canonical transition
```

The durable execution journal is the sole source of operational truth. Every
state transition is an append. Job, Attempt, Lease, and Worker projections are
reconstructed from that journal and may be discarded and rebuilt. A Worker,
backend, projection file, process table, Crucible path, queue, or API response
is never authoritative on its own.

One Job binds exactly one immutable Task Capsule and one immutable Execution
Specification. One Attempt is one try for that Job. Each Attempt receives one
strictly increasing Job-scoped fencing generation and may receive at most one
Lease; a preflight-rejected Attempt receives none. A failed claim, expired
offer, retry, reassignment, or recovery never reuses an Attempt or Lease
identity.

The `0.4` reference runtime is local and single-coordinator. The journal must
still make concurrent requests, duplicate delivery, Executor restart, and
surviving child processes deterministic. Remote Worker transport and
multi-coordinator consensus are non-goals, not permission to omit fencing.

## Executable contract set

The implementation must publish closed JSON Schema Draft 2020-12 documents
with the following exact identifiers and conventional filenames:

| Contract identifier | Filename | Purpose |
| --- | --- | --- |
| `execution-specification/1.0` | `execution-specification-1.0.json` | Immutable, Sigil-bound resolution of one v2 Task into enforceable runtime, lifecycle, logging, retry, output, and assurance requirements. |
| `execution-job/1.0` | `execution-job-1.0.json` | Immutable Job submission record bound to the Task Capsule and Execution Specification. |
| `execution-attempt/1.0` | `execution-attempt-1.0.json` | Immutable allocation of one retry ordinal, fencing generation, planned backend, and Crucible identity. |
| `attempt-authorization-subject/1.0` | `attempt-authorization-subject-1.0.json` | Deterministic, Attempt-specific approval subject required by `NEW_AUTHORIZATION_EACH_ATTEMPT`. |
| `attempt-authorization-transition-request/1.0` | `attempt-authorization-transition-request-1.0.json` | Closed Athanor request whose canonical Event and Receipt grant one exact Attempt authorization. |
| `execution-worker/1.0` | `execution-worker-1.0.json` | Stable Worker definition and its declared and Executor-verified capability manifest; it is not a live session. |
| `execution-worker-session/1.0` | `execution-worker-session-1.0.json` | One immutable, non-resumable Worker control session bound to one Executor epoch. |
| `execution-lease/1.0` | `execution-lease-1.0.json` | One time-bounded Lease offer bound to a Job, Attempt, Worker definition, Worker Session, Executor epoch, and fencing generation. |
| `execution-heartbeat/1.0` | `execution-heartbeat-1.0.json` | Bounded Worker- or Lease-scoped liveness and resource sample. |
| `execution-log-chunk/1.0` | `execution-log-chunk-1.0.json` | Content-identified, sequence-bound stdout, stderr, or structured-log chunk. |
| `execution-result/1.0` | `execution-result-1.0.json` | Bounded Worker completion message and staged-output manifest; it is not an Agent Result or Receipt. |
| `benchwork-source-tree/1.0` | `benchwork-source-tree-1.0.json` | Canonical retained terminal-source manifest and deterministic bundle identity for `BENCHWORK_SOURCE_TREE_V1`. |
| `execution-storage-root-manifest/1.0` | `execution-storage-root-manifest-1.0.json` | Single-assignment typed Blob/source closure and preallocated protection plan for one execution root. |
| `execution-root-hold-release-authorization/1.0` | `execution-root-hold-release-authorization-1.0.json` | Single-assignment authorization for the only three legal execution-root hold-release bases. |
| `execution-output-storage-observation-set/1.0` | `execution-output-storage-observation-set-1.0.json` | Immutable, resolvable fixed-prefix storage observations for one terminal Attempt's outputs, three Log streams, resource evidence, and terminal source. |
| `execution-control-evidence/1.0` | `execution-control-evidence-1.0.json` | Per-control preflight, runtime, termination, and cleanup evidence retained for one Attempt. |
| `execution-control-evidence-set/1.0` | `execution-control-evidence-set-1.0.json` | Immutable, resolvable closure of the exact ten per-control evidence records used to terminalize one Attempt. |
| `execution-quarantine-binding-set/1.0` | `execution-quarantine-binding-set-1.0.json` | Immutable, resolvable subject-to-Quarantine bindings used by one Attempt's terminal storage observation. |
| `sanctum-assurance-profile/1.0` | `sanctum-assurance-profile-1.0.json` | Versioned definitions of `SANCTUM-A0` through the claimable Phase 3 levels and their required controls. |
| `sanctum-assurance-claim/1.0` | `sanctum-assurance-claim-1.0.json` | Immutable post-terminal realized assurance evaluation for exactly one Attempt. |
| `execution-journal-event/1.0` | `execution-journal-event-1.0.json` | Hash-chained operational event with a closed event type and closed type-specific payload. |
| `execution-journal-head/1.0` | `execution-journal-head-1.0.json` | Replaceable journal-head cache binding the journal ID, last sequence, and last event Sigil. |
| `execution-recovery-action-set/1.0` | `execution-recovery-action-set-1.0.json` | Deterministically derived, immutable ordered recovery intents for one Recovery phase. |
| `execution-state/1.0` | `execution-state-1.0.json` | Replayed Executor epoch plus Job, Attempt, Lease, Worker-definition, Worker-Session, liveness, log, budget, deadline, and recovery projections. |

These contracts use `$id` values under
`https://benchwork.dev/schemas/<contract-identifier>`. Every object is closed
with `additionalProperties: false`; identifier-bearing maps also constrain
`propertyNames`. Unknown versions, fields, enum values, event types, assurance
profiles, conformance suites, or evidence kinds fail closed.

The Schema family depends on the RFC-0011 `capability-registry/2.0`,
`capability-contract/2.0`, and `task-capsule/2.0` contracts. The output
storage-observation and quarantine-binding-set contracts additionally import
the exact RFC-0013 `EventRef`, Blob, Replica, backend-object, verification,
Quarantine, owner-ID, and State-Sigil types; they cannot clone or widen them.
No v1 Capability or Task contract is valid input to
`execution-specification/1.0`.

### Common identity and encoding rules

The contracts use these identity classes:

| Object | Identifier pattern |
| --- | --- |
| Execution Specification | `ES-[A-Z0-9]+` |
| Job | `JB-[A-Z0-9]+` |
| Attempt | `AT-[A-Z0-9]+` |
| Attempt authorization subject | `AA-[A-F0-9]{64}` |
| Attempt authorization transition | `AAT-[A-F0-9]{64}` |
| Lease | `LS-[A-Z0-9]+` |
| Worker | `WK-[A-Z0-9]+` |
| Worker Session | `WS-[A-Z0-9]+` |
| Executor instance | `XI-[A-Z0-9]+` |
| Recovery transaction | `RY-[A-Z0-9]+` |
| Journal | `EJ-[A-Z0-9]+` |
| Journal event | `JE-[A-Z0-9]+` |
| Log stream | `LG-[A-Z0-9]+` |
| Log chunk | `LC-[A-Z0-9]+` |
| Output storage observation set | `OS-[A-F0-9]{64}` |
| Benchwork source tree | `BTS-[A-F0-9]{64}` |
| Execution storage-root manifest | `ESM-[A-F0-9]{64}` |
| Execution-root hold release authorization | `EHR-[A-F0-9]{64}` |
| Control evidence | `CE-[A-Z0-9]+` |
| Control evidence set | `CES-[A-F0-9]{64}` |
| Quarantine binding set | `QBS-[A-F0-9]{64}` |
| Assurance claim | `AC-[A-Z0-9]+` |

Every non-fixed operational identifier in this table is ASCII and has a total
length, including its prefix, of 3 through 128 bytes; its printed pattern
still requires at least one suffix character. The seven hash-derived `JB-`,
`AA-`, `OS-`, `BTS-`, `ESM-`, `CES-`, and `QBS-` domains are exactly 67
ASCII bytes, while `AAT-` and `EHR-` are exactly 68 ASCII bytes; none admits
a shortened or extended form. Every occurrence of one of these ID classes,
including inside an imported or projected binding, uses the same bound.

Identifiers are opaque and never derived from a PID, path, timestamp, queue
position, Worker name, or scientific Run identity. Attempt ordinals are
RFC-0011 `PositiveU63` values scoped to one Job and are diagnostic ordering,
not identity.

All Sigils use Benchwork canonical JSON and the existing `sha256:<64 lowercase
hex>` representation. A document's own Sigil field is omitted when computing
that Sigil. Byte payloads such as logs and staged outputs use byte-level Blob
Sigils rather than JSON canonicalization. Times are exactly RFC-0013
`Timestamp`: normalized RFC 3339 UTC values with a terminal `Z`, no leap
second, and at most six fractional digits. Durations and limits are
non-negative or positive integer units as stated by their field. All durable
deadlines use a `*_due_at` UTC field.
Worker-reported timestamps are observations only. Executor receive time, the
durable due time, and the monotonic-anchor rules below determine protocol
ordering.

Every execution-journal Event sequence, Event count, and field whose declared
meaning is an execution-journal sequence uses RFC-0013 `U63`; a one-based
Event sequence uses `PositiveU63`. This includes `sequence`,
`last_sequence`, `through_sequence`, `derived_through_sequence`,
`replay_through_sequence`, `target_sequence`, `effective_sequence`,
`disposition_sequence`, `evaluation_sequence`, and nullable
`last_heartbeat_sequence`. All addition is checked before allocation, and an
operation that would allocate `U63_MAX + 1` fails closed without a partial
frame or projection change. Executor epochs, fencing generations, and mutable
entity revisions remain `U64`; they are not journal sequences.

Every mutable projection carries a non-negative `revision`. A transition event
states the exact expected preceding revision and the next revision. Replay
rejects gaps, duplicate state-changing revision assignments with different
event Sigils, and transitions whose immutable bindings differ from the
object's creation record. An equal-revision entry that only validates a
non-owner relationship is not an assignment. The only events whose primary
state owner is required to use an equal revision are terminal-Job
`job.cancellation_observed` and
`storage_root.hold_release_observed`; any number of distinct, valid request
bindings or release bindings may observe the same unchanged Job revision.

### Execution Specification

The v1 top-level object has exactly these required members:

| Field | Exact v1 value or closed object |
| --- | --- |
| `schema_version` | Constant `execution-specification/1.0`. |
| `specification_id` | Execution Specification ID. |
| `created_at` | UTC creation time. |
| `task_binding` | Exactly `task_id` and `task_capsule_sigil`. |
| `capability_binding` | Exactly `capability_id`, `contract_version`, and `capability_contract_sigil`. |
| `snapshot_binding` | Exactly `snapshot_id` and `snapshot_sigil`. |
| `authorization` | Exactly `ward_decision_id`, `ward_decision_sigil`, `approval_requirement`, and the conditional approval fields below. |
| `policies` | Exactly `filesystem`, `executable`, `process`, `network`, `environment`, `credential`, `resource`, `input`, and `output`; each value is a closed resolved-policy object with `policy_id`, `policy_version`, `policy_sigil`, and its policy-specific bounded rules. |
| `output_contracts` | Bounded ordered array of closed entries containing `logical_name`, `schema_id`, `schema_sigil`, `maximum_bytes`, `maximum_count`, `path_rule`, and `side_effect_id`. |
| `result_requirement` | Exactly `worker_result_mode` and `successful_worker_outcome`; the mode is `REQUIRED`, `OPTIONAL`, or `FORBIDDEN`, and successful outcome is constant `COMPLETED`. |
| `runtime_constraints` | Exactly `runtime_identities`, `backend_identities`, `host_constraints`, and `identity_requirements`; all are bounded closed sets or closed objects. |
| `assurance_requirement` | Exactly `requested_level`, `profile_version`, `profile_sigil`, `conformance_suite_id`, and `conformance_suite_sigil`. |
| `deadline_policy` | Exact integer members `lease_duration_seconds`, `heartbeat_interval_seconds`, `heartbeat_timeout_seconds`, `lease_claim_timeout_seconds`, `attempt_wall_time_seconds`, `cancellation_grace_seconds`, `job_wall_time_seconds`, and `clock_uncertainty_tolerance_seconds`. |
| `attempt_budget` | Exact per-Attempt ceilings described below. |
| `job_budget` | Exact aggregate Job ceilings described below. |
| `retry_policy` | Exactly `max_attempts`, `retryable_terminal_reasons`, `backoff_kind`, `backoff_base_seconds`, `backoff_cap_seconds`, `resume_policy`, and `external_side_effects_retry_safe`. |
| `logging_policy` | Exactly `stdout_maximum_bytes`, `stderr_maximum_bytes`, `structured_maximum_bytes`, `aggregate_maximum_bytes`, `chunk_maximum_bytes`, and `overflow_behavior`. |
| `post_terminal_derivation` | Closed `NONE` or `CODE_MODIFICATION` branch described below. |
| `conformance_policy_version` | Closed conformance-policy version. |
| `specification_sigil` | Sigil over every other member. |

`attempt_budget` has exactly `cpu_time_seconds`, `peak_memory_bytes`,
`storage_bytes_written`, `output_bytes`, `log_bytes`, `process_starts`,
`network_egress_bytes`, and `network_requests`. `job_budget` has exactly
`attempts`, `cpu_time_seconds`, `storage_bytes_written`, `output_bytes`,
`log_bytes`, `process_starts`, `network_egress_bytes`, and
`network_requests`. Every value is a non-negative integer; `attempts` is
positive and equals `retry_policy.max_attempts`. A denied facility has a zero
limit rather than an omitted field. Job wall time is represented by
`job_wall_time_seconds` and the derived durable Job `deadline_due_at`, not by
a second ambiguous budget counter.

The only conditional members in v1 are:

| Container | Conditional fields | Rule |
| --- | --- | --- |
| `authorization` | `approval_receipt_id`, `approval_receipt_sigil` | Both are required exactly when `approval_requirement` is `REQUIRED`; both are absent when it is `NOT_REQUIRED`. |
| each resolved policy | Policy-specific branch selected by its closed mode enum | Exactly one Schema `oneOf` branch is present; no generic policy dictionary exists. |
| `post_terminal_derivation` | For `NONE`, exactly `mode`. For `CODE_MODIFICATION`, exactly `mode`, `crucible_base_identity`, `crucible_base_sigil`, `retention_policy_id`, `retention_policy_version`, `retention_policy_sigil`, `terminal_source_maximum_files`, `terminal_source_maximum_bytes`, `retention_duration_seconds`, and `source_identity_profile`. | A code-modification or other Patch-producing Task must use `CODE_MODIFICATION`; the immutable Base and complete bounded retention authority are fixed before Job creation. |

There are no other optional top-level members. Backoff fields remain present
and use the exact `backoff_kind` enum `NONE`, `FIXED`, or `EXPONENTIAL`.
`NONE` requires base and cap zero; `FIXED` requires a positive base and a cap
equal to it; `EXPONENTIAL` requires a positive base and a cap no smaller than
the base. `resume_policy` is exactly `FRESH_ONLY` or
`ALLOW_IMMUTABLE_RESUME`. Network limits remain present and zero when network
is denied. This exact shape is the source for the eventual closed JSON Schema
rather than an illustrative minimum.

In the `CODE_MODIFICATION` branch, both terminal-source maxima and
`retention_duration_seconds` are positive integers and
`source_identity_profile` is the constant
`BENCHWORK_SOURCE_TREE_V1`. The predeclared Base pair and retention-policy
tuple are non-null and must validate against the pinned Task, Snapshot, and
resolved output policy before the Specification Sigil is accepted.
`retention_policy_id` is exactly the RFC-0013 `SP-ID`,
`retention_policy_version` is the constant `1.0`, and
`retention_policy_sigil` resolves the exact
`artifact-retention-policy/1.0.record_sigil` for that ID. The duration is the
maximum lifetime of the execution-owned `ATTEMPT_OUTPUT` Reference-Set hold;
it does not replace, shorten, or reinterpret that physical retention policy.

`worker_result_mode` must be equal to or narrower than the v2 Task and
Capability. `REQUIRED` needs one accepted `COMPLETED` result for Attempt and
Job success; `OPTIONAL` permits an accepted `COMPLETED` result or explicit
`result_binding: NONE`; `FORBIDDEN` requires `NONE` and rejects every Worker
result message. A `FAILED` Worker outcome can never satisfy successful
completion, although it remains operational evidence.

Every authority in the Specification must be equal to or narrower than the
pinned v2 Task and Capability. Lifecycle settings may consume less time or
fewer resources but may not extend their bounds. Retry does not multiply an
otherwise single-use external side-effect permission unless the Task and
Capability explicitly make that side effect retry-safe and idempotent.

Every closed resolved policy rule that carries a Side-effect ID also carries
the exact closed `side_effect_authorization` object with
`side_effect_id`, `kind`, `authority_sigil`, `maximum_invocations`,
`retry_mode`, `idempotency_scope_sigil`, and `requires_approval`.
`retry_mode` is exactly `NO_RETRY`, `SAME_IDEMPOTENCY_KEY`, or
`NEW_AUTHORIZATION_EACH_ATTEMPT`; `kind` and the null matrix are the exact
RFC-0011 values. Repeated use of one Side-effect ID across policy rules must
repeat this object byte-for-byte, and the unique projection by Side-effect ID
must equal the pinned Task/Circle subset. No side-effect authority may survive
only as an unbound ID.

`AttemptAuthorizationEffect` is the closed object
`{side_effect_id, authority_sigil}`. The exact
`attempt_authorization_requirement` derived from that projection is
`NONE {kind, effects}` with an empty array or
`REQUIRED {kind, effects}` with one to 128 entries. The latter contains every
and only side effect whose retry mode is
`NEW_AUTHORIZATION_EACH_ATTEMPT`, strictly sorted by unique Side-effect ID,
with the exact authority Sigil. A non-`READ_ONLY` `NO_RETRY` effect requires
`max_attempts: 1`. A `SAME_IDEMPOTENCY_KEY` effect retains its exact non-null
scope Sigil in every carrying rule. A `NEW_AUTHORIZATION_EACH_ATTEMPT` effect
may coexist with `max_attempts > 1` only with
`external_side_effects_retry_safe: false` and the per-Attempt carrier below.

The Specification is immutable. Any change, including a narrower permission,
different retry count, different backend constraint, or different assurance
profile or suite, creates a new Specification Sigil and requires a new exact
approval where RFC-0011 requires approval.

`CODE_MODIFICATION` authorizes only bounded retention of terminal source for a
later RFC-0014 derivation. It does not authorize Patch preparation, acceptance,
or promotion. Its non-null `crucible_base_identity` and
`crucible_base_sigil` are copied from the pinned Task/Snapshot input
resolution and are therefore available even when no Attempt is ever
allocated. Every allocated Attempt must copy that exact pair.
`attempt.cleaning` and the Attempt terminal event bind the same immutable
Crucible Base identity and exact terminal-source binding. A verified branch
binds retained source identity, source Sigil, storage BlobRef,
retention-policy Sigil, byte/file counts,
storage status, and independent verifier-evidence Sigil; a quarantined branch
binds the same known fields, explicit null source identity/Sigil/BlobRef when nothing
content-identified was retained, zero counts, and closed reasons. The Job
terminal event repeats that exact binding for the selected Attempt, or
constructs the fixed no-Attempt quarantine branch from the Job-bound
Specification. A failure cannot be reconstructed or backfilled after the Job
Outcome is derived.

### Canonical retained source tree

`BENCHWORK_SOURCE_TREE_V1` means exactly the
`benchwork-source-tree/1.0` contract; it is not a tar, zip, directory path, or
implementation-selected serialization. The closed top-level record has
exactly `schema_version`, `source_tree_id`, `manifest`, `bundle_blob`,
`verified_at`, and `source_tree_sigil`. The Schema version is constant,
`bundle_blob` is the exact RFC-0013 `{blob_sigil, size_bytes: U63}`, and the
self-Sigil covers every other member.

`manifest` has exactly `format_version: BENCHWORK_SOURCE_TREE_V1`, `job_id`,
`attempt_id`, `attempt_binding_sigil`, `crucible_base_identity`,
`crucible_base_sigil`, `scope`, `path_semantics`, `entries`, `file_count`,
`byte_count`, and `manifest_sigil`. Its self-Sigil covers every other member.
`scope` is exactly `{root_kind: CRUCIBLE, included_paths, excluded_paths}`;
both path arrays are sorted unique sets of normalized project-relative paths,
are disjoint, and have at most 100,000 members. `path_semantics` is exactly
`{separator: SLASH, unicode_normalization: NFC, case_mode:
SENSITIVE|INSENSITIVE_REJECT_COLLISIONS, dot_segments: REJECT,
link_traversal: NOFOLLOW, reserved_name_policy: REJECT}`. `.benchwork/`,
`.git/`, absolute paths, empty or dot segments, NUL/control characters,
normalization or case collisions, and platform-reserved names are always
excluded and cannot be reintroduced by `included_paths`.

`entries` is a `0..100000` array sorted strictly by normalized path bytes,
unique by path, and contains exactly one of:

- `DIRECTORY {path, kind, entry_sigil}`;
- `FILE {path, kind, blob: RFC-0013 BlobRef, executable}`; or
- `SYMLINK {path, kind, target, target_sigil}`.

All objects are closed. A file Blob is the byte-level SHA-256 and U63 size of
its complete content. A symlink target is NFC UTF-8 of `0..4096` bytes and is
hashed as link data; it is never followed. `file_count` is the checked count
of `FILE` plus `SYMLINK` entries. `byte_count` is the checked sum of file
sizes plus symlink-target byte lengths. Both must fit the Specification
maxima. Unsupported types, hard-link ambiguity, sparse or partial traversal,
changed input, arithmetic overflow, or an incomplete scope fail verification.

The `bundle_blob` bytes are deterministic:

```text
ASCII "BWSOURCE1\n"
U64BE(length(canonical_json(manifest)))
canonical_json(manifest)
for each FILE entry in entries order:
    U64BE(entry.blob.size_bytes)
    exact file bytes
```

The decoder rejects a length, order, content Sigil, trailing-byte, manifest,
or count mismatch. `source_tree_id` is `BTS-` followed by uppercase SHA-256
hex over canonical JSON
`["benchwork-source-tree-id/1.0", job_id, attempt_id,
attempt_binding_sigil, manifest_sigil]`. Independent scan and bundle
readback must reproduce the complete manifest, bundle BlobRef, and record
self-Sigil.

For a verified terminal-source binding,
`terminal_source_identity == source_tree_id`,
`terminal_source_sigil == source_tree_sigil`, and
`storage_blob == bundle_blob`; its Base, counts, and identity profile equal
the manifest and Specification byte-for-byte. A quarantined branch preserves
the same three values when a complete claimed tree exists; all three are null
when none exists. RFC-0014 exports only after resolving this record and
verifying the deterministic bundle rather than reading a mutable Crucible.

### Job, Attempt, Worker, and Lease bindings

The following tables are the exact required top-level members of the v1
binding documents. No document has an optional top-level member except where
the conditional rules say so.

`execution-job/1.0`:

| Field | Meaning |
| --- | --- |
| `schema_version` | Constant `execution-job/1.0`. |
| `job_id` | Job identity. |
| `submitted_at` | Durable UTC submission time. |
| `submission_idempotency_key_sigil` | Sigil of the bounded Start idempotency key. |
| `start_request_sigil` | Complete RFC-0015 Start-request Sigil. |
| `task_id`, `task_capsule_sigil` | Exact Task binding. |
| `specification_id`, `specification_sigil` | Exact Specification binding. |
| `admission_chronicle_head` | Exact RFC-0013 Phase 3-admissible Chronicle Head observed under the outer gate before any Job side effect. |
| `admission_chronicle_head_evidence` | Closed admission evidence defined below. |
| `assurance_requirement` | Exact copy of the Specification tuple. |
| `deadline_due_at` | Durable UTC Job deadline derived once at submission. |
| `job_budget` | Exact copy of the aggregate ceilings. |
| `job_storage_roots` | Array of zero or one pre-held `JOB_INPUT` storage-root binding; its ESM covers every Job input and has this `job_id` and null `attempt_id`. |
| `job_binding_sigil` | Sigil over every other member. |

The admission evidence has exactly `profile`, `job_id`,
`start_request_sigil`, `observed_chronicle_head`, `observed_at`,
`validator_build_sigil`, and `evidence_sigil`; the profile is constant
`PHASE3_CHRONICLE_HEAD_ADMISSION_V1`, its observed Head equals the Job field,
its Job/request fields equal the enclosing Job, and the self-Sigil is the
common canonical-JSON self-Sigil over every other field. The Head
must have `event_count < U63_MAX`. Start acquires the outer canonical-
reference gate, replays Chronicle, validates this capacity bound, and freezes
this complete admission evidence in a Job-ID-keyed single-assignment pending
resolver before creating its Job-input ESM or any Storage side effect. The
complete `execution-job/1.0` document is assembled only after its root binding
exists, and embeds those already frozen evidence bytes; it is never claimed
to predate the hold whose EventRef it contains. An interrupted retry reuses
the exact frozen admission evidence but, under the gate, again requires the
then-current valid Chronicle Head to remain below `U63_MAX`; exhaustion,
ambiguity, or different evidence for the same Job ID fails before a new
Reference Set, hold, or execution event.

The Job contains no scientific Run ID and grants no canonical authority. The
replayed Job projection initializes `fencing_counter`, `fence_floor`, every
budget `consumed` counter, and every budget `reserved` counter to zero. Only
the atomic allocation, budget-settlement, and Lease-terminal events named
below may advance those values. Every non-empty `job_storage_roots` hold is
already durable under the outer gate before `job.submitted`; the submission
event activates exactly that immutable array.

For RFC-0015 Start, the key Sigil and Job ID are deterministic before any
Storage side effect:

```text
submission_idempotency_key_sigil =
  Sigil(["execution-start-idempotency-key/1.0", idempotency_key])

job_id =
  "JB-" + UPPER_HEX(SHA256(canonical_json(
    ["execution-job-id/1.0",
     task_id,
     submission_idempotency_key_sigil])))
```

The resulting Job ID is exactly 67 ASCII bytes and still belongs to `JB-ID`.
The `START_JOB` idempotency `scope_id` is the immutable Task ID, not the
allocated Job ID. Thus `(START_JOB, task_id,
submission_idempotency_key_sigil)` is caller-reconstructible and selects one
Job before holds. Reusing it with a different `start_request_sigil` is a
conflict.

`execution-attempt/1.0`:

| Field | Meaning |
| --- | --- |
| `schema_version` | Constant `execution-attempt/1.0`. |
| `attempt_id`, `job_id`, `job_binding_sigil` | Attempt and exact parent binding. |
| `retry_ordinal`, `fencing_generation` | RFC-0011 `PositiveU63` ordinal and unused strictly increasing unsigned 64-bit Job generation. |
| `assurance_requirement` | Exact requested tuple. |
| `backend_identity`, `backend_version`, `backend_configuration_sigil` | Planned enforcement backend. |
| `base_identity`, `base_sigil`, `input_identities` | Immutable Base identity/Sigil pair and bounded sorted input bindings. Under `CODE_MODIFICATION`, the pair is byte-for-byte equal to the Specification's predeclared `crucible_base_identity` and `crucible_base_sigil`. |
| `resume_mode` | `FRESH` or `IMMUTABLE_RESUME`. |
| `resume_source_identity` | Required exactly for `IMMUTABLE_RESUME` and absent for `FRESH`. |
| `crucible_id` | Newly allocated mutable materialization identity. |
| `output_namespace_id` | Newly allocated exclusive output namespace. |
| `log_stream_ids` | Exactly `STDOUT`, `STDERR`, and `STRUCTURED`, each bound to a fresh Log-stream ID. |
| `budget_reservation` | Exact Job-budget reservation described under Retry. |
| `attempt_authorization_requirement` | Exact immutable RFC-0011 `NONE` or `REQUIRED` branch derived from the Specification's carrying policies. |
| `created_at`, `deadline_due_at` | Creation time and durable Attempt deadline. |
| `attempt_binding_sigil` | Sigil over every other member. |

The only conditional Attempt member is `resume_source_identity`, required
exactly for `IMMUTABLE_RESUME` and absent for `FRESH`.
`attempt.preflight_passed` later binds the verified materialization content
identity. A retry always creates a new Attempt, Crucible, and output namespace.

### Per-Attempt authorization

`attempt-authorization-subject/1.0` is the executable RFC-0011
`AttemptAuthorizationSubject`. Its conventional filename is
`attempt-authorization-subject-1.0.json` and its exact `$id` is
`https://benchwork.dev/schemas/attempt-authorization-subject/1.0`.
The closed object has exactly `schema_version`,
`authorization_subject_id`, `job_id`, `job_binding_sigil`, `attempt_id`,
`attempt_binding_sigil`, `retry_ordinal`, `specification_id`,
`specification_sigil`, `effects`, and `authorization_subject_sigil`.
`schema_version` is constant `attempt-authorization-subject/1.0`; `effects`
is the non-empty one-to-128 RFC-0011 `AttemptAuthorizationEffect` set; the
self-Sigil covers every other field; and `retry_ordinal` is the exact
RFC-0011 `PositiveU63` value from the immutable Attempt.

The subject ID is `AA-` followed by the uppercase 64-hex SHA-256 digest of
canonical JSON:

```text
["attempt-authorization-subject-id/1.0",
 job_id,
 job_binding_sigil,
 attempt_id,
 attempt_binding_sigil,
 retry_ordinal,
 specification_id,
 specification_sigil,
 effects]
```

The subject is constructed only after the immutable Attempt document exists.
Its owner and Specification fields equal that Attempt and Job byte-for-byte,
and `effects` equals both its immutable
`attempt_authorization_requirement.effects` and the complete unique
projection of the Specification's
`NEW_AUTHORIZATION_EACH_ATTEMPT` carrying policies.

`attempt-authorization-transition-request/1.0` is the only v1 request that
can ask Athanor to grant this subject. Its closed object has exactly
`schema_version`, `transition_request_id`, `event_type`,
`expected_chronicle_head`, `authorization_subject`, `authority_evidence`,
`actor`, `host_invocation`, `chronicle_actor`, `idempotency_key_sigil`,
`requested_at`, and `transition_request_sigil`. `event_type` is the constant
`attempt.authorization.granted`; the Head is the exact Phase 3-admissible
RFC-0013 `ChronicleHeadRef`; `actor` and `host_invocation` are the exact
authenticated RFC-0015 bindings; `chronicle_actor` is the complete canonical
RFC-0001 `actor/1.0` `{actor_id, actor_type, host, authenticated_by}`; and the
self-Sigil covers every other field, including that Chronicle Actor.
`actor.authentication_context_sigil ==
host_invocation.authentication_context_sigil`; both binding self-Sigils
validate; and all three records are produced byte-for-byte by the same
authenticated invocation context rather than caller text.
`chronicle_actor.actor_id == actor.actor_id`; the closed kind mapping is
`USER -> human`, `AGENT -> agent`, and `SYSTEM -> policy|tool`. The Chronicle
`host` and `authenticated_by` values equal that context's canonical audit
Host and authentication mechanism and are not inferred from a Host-identity
Sigil, invocation ID, or caller text.
`authority_evidence` is the closed object
`{purpose: ATTEMPT_AUTHORIZATION, ward_decision_id, ward_decision_sigil,
authorization_policy_sigil, effects}`. Its `effects` equals the subject
byte-for-byte. Each effect is authorized at the expected Head by the pinned
Task, Capability, Circle, Snapshot, Specification, Ward decision, and
authenticated actor; the authority is re-evaluated rather than inferred from
the mere presence of their IDs. `authority_evidence_sigil` is the common
canonical-JSON Sigil of this complete object and is the value copied into the
canonical Event.

The transition ID is deterministic:

```text
transition_request_id =
  "AAT-" + UPPER_HEX(SHA256(canonical_json(
    ["attempt-authorization-transition-request-id/1.0",
     authorization_subject.authorization_subject_id,
     idempotency_key_sigil])))
```

The caller fixes the bounded idempotency key before the request. The immutable
request resolver is single-assignment by this ID: the first complete bytes,
including Actor, Host invocation, Chronicle Actor, Head, evidence, and
`requested_at`, win; an exact retry returns them and any different bytes
conflict. This resolver write precedes the Athanor call.

The successful canonical Event has type
`attempt.authorization.granted`. Its closed payload has exactly
`transition_request_id`, `transition_request_sigil`,
`authorization_subject_id`, `authorization_subject_sigil`,
`authority_evidence_sigil`, `actor`, and `occurred_at`. It resolves the exact
request and requires, byte-for-byte, the same subject, authority-evidence
Sigil, actor, and request time (`occurred_at == requested_at`). The Event is
admitted only at `expected_chronicle_head`; its outer `actor` is
byte-for-byte the request's `chronicle_actor`, while its payload `actor`
remains the RFC-0015 `ActorBinding`. It is not the operational
`attempt.authorization_bound` event.

`AttemptAuthorizationBinding` is the exact closed object
`{authorization_subject_id, authorization_subject_sigil,
authorization_transition_request_id, authorization_transition_request_sigil,
authorization_event_id, authorization_event_body_sigil,
authorization_receipt_id, authorization_receipt_sigil,
authorization_binding_sigil}`. Receipt ID uses `RC-[A-Z0-9]+`; its Sigil and
the binding self-Sigil use the common Sigil domain. The binding self-Sigil
covers every other field. The Receipt is the exact `receipt/1.1` for
`authorization_event_id` and `authorization_event_body_sigil`; the Event then
resolves the exact transition request, and that request resolves the complete
subject and purpose above. A Receipt itself does not contain a purpose or
subject, so no implementation may validate this binding by reading such
fictional Receipt fields. Every authority named in `effects` validates that
exact subject. An Attempt-specific subject, transition request, Event,
Receipt, or binding cannot equal or be reused by another Attempt or by the
Specification-level approval.

The replayed orthogonal `attempt_authorization_state` is exactly
`NONE {kind}`, `PENDING {kind}`, or
`BOUND {kind, authorization_subject, attempt_authorization_binding}`.
Allocation initializes it to `NONE` exactly for a `NONE` immutable
requirement and to `PENDING` exactly for `REQUIRED`.
`attempt.authorization_bound` is legal only while the Attempt lifecycle state
is `CREATED`, its authorization state is `PENDING`, and no stop is latched.
Its exact payload contains the complete `authorization_subject` and
`attempt_authorization_binding`; the nested subject ID and Sigil agree
byte-for-byte. The event advances only the Attempt revision and assigns
`BOUND` once. No event replaces or clears it.

The AA-ID and AAT-ID make a crash before either Event commitment retry the
exact same subject and immutable request. Athanor is idempotent by request ID
and Sigil: it returns the same Event and Receipt for the same complete request
and rejects ID reuse with different bytes. A crash after the Receipt exists
but before `attempt.authorization_bound` therefore resolves that exact
request/Event/Receipt chain and appends only the missing operational binding
event. Recovery is read-only toward Chronicle: it cannot construct a new
request, resample Head/time/actor, or mint a replacement authority. An
unknown or conflicting request, Event, or Receipt fails closed and the
Attempt may only stop or reject.

A `REQUIRED` Attempt cannot append `attempt.preflight_started`, receive or
claim a Lease, launch, issue credentials, or obtain any side-effecting handle
until `BOUND`. This guard applies to the first Attempt and every retry. A
predecessor's subject, Receipt, binding, idempotency scope, or side-effect
handle never authorizes its successor.

`execution-worker/1.0` is a stable definition, not a process:

| Field | Meaning |
| --- | --- |
| `schema_version` | Constant `execution-worker/1.0`. |
| `worker_id` | Stable Worker identity reused only across distinct Sessions of this definition. |
| `definition_revision` | Non-negative immutable definition revision. |
| `supersedes_worker_binding_sigil` | Required exactly when `definition_revision` is greater than zero and absent at revision zero. |
| `implementation_name`, `implementation_version` | Worker implementation binding. |
| `supported_runtimes`, `resource_ceilings` | Bounded declared capability sets. |
| `declared_backend_capabilities` | Bounded declarations with no evidentiary authority. |
| `verified_capability_tuples` | Bounded Executor-verified backend/profile/suite/configuration tuples. |
| `maximum_concurrency` | Positive verified definition ceiling. |
| `definition_created_at` | UTC time of this definition revision. |
| `worker_binding_sigil` | Sigil over every other member. |

`supersedes_worker_binding_sigil` is required exactly when
`definition_revision` is greater than zero and absent at revision zero.
Changing implementation, capabilities, verification, or concurrency creates
a new immutable definition revision; it never mutates a Worker Session.

`execution-worker-session/1.0` is one immutable live-session binding:

| Field | Meaning |
| --- | --- |
| `schema_version` | Constant `execution-worker-session/1.0`. |
| `worker_session_id`, `worker_id`, `worker_binding_sigil` | New Session identity and exact stable definition. |
| `executor_instance_id`, `executor_epoch` | Coordinator process and epoch to which this Session is exclusively attached. |
| `host_identity_sigil`, `backend_session_identity` | Exact Host and backend process/session evidence identities. |
| `control_channel_identity_sigil` | Protected bounded control-channel identity. |
| `verified_capability_tuple_sigil` | Selected subset of the Worker definition verified for this Session. |
| `maximum_concurrency` | Session ceiling no greater than the definition ceiling. |
| `opened_at` | UTC registration time. |
| `worker_session_binding_sigil` | Sigil over every other member. |

A fresh Worker process, control-channel re-establishment, Executor epoch, or
revalidation creates a new `worker_session_id` and a new immutable Session
document. A Session ID, backend session identity, or control-channel identity
is never reused. There is no Session generation counter and no
`OFFLINE -> REGISTERED` resurrection.

`execution-lease/1.0`:

| Field | Meaning |
| --- | --- |
| `schema_version` | Constant `execution-lease/1.0`. |
| `lease_id`, `job_id`, `attempt_id` | Exact Lease scope. |
| `worker_id`, `worker_binding_sigil` | Stable Worker definition binding. |
| `worker_session_id`, `worker_session_binding_sigil` | Exact immutable Session receiving authority. |
| `executor_instance_id`, `executor_epoch` | Issuing coordinator binding. |
| `fencing_generation` | Exact Attempt generation. |
| `offered_at`, `claim_due_at`, `initial_expiry_due_at`, `maximum_expiry_due_at` | Durable UTC authority bounds. |
| `heartbeat_policy` | Exact interval and timeout copied from the Specification. |
| `lease_credential_digest` | Digest only, never the credential. |
| `lease_binding_sigil` | Sigil over every other member. |

The unguessable Lease credential is delivered only through the protected
control handle. It is never placed in a log, projection, policy file,
environment dump, Worker-readable journal, or evidence export.

### Recovery action-set binding

`execution-recovery-action-set/1.0` has exactly
`schema_version`, `recovery_id`, `phase`, `derived_from_journal_id`,
`derived_through_sequence`, `derived_through_event_sigil`,
`supersedes_action_set_sigil`, `actions`, and `action_set_sigil`.
`supersedes_action_set_sigil` is null for an initial phase set and identifies
the current phase set replaced after a new clock/epoch interruption. `phase`
is `STARTED`, `FENCING`, `RECONCILING`, or `FINALIZING`. Each action has
exactly `ordinal`, `action_kind`, `entity_kind`, `entity_id`,
`expected_revision`, `target_event_id`, `target_sequence`,
`target_event_type`, `prerequisite_event_ids`, and `parameters`. Ordinals are
contiguous from zero; prerequisite IDs are sorted and refer only to events in
the derivation prefix or earlier actions' committed events. `entity_kind`,
`entity_id`, and `expected_revision` name the primary owner. For a
multi-entity target event, every secondary owner's exact preceding and next
revision is deterministically projected from the bound prefix plus earlier
ordinal events and must appear in the event envelope; it is not duplicated as
mutable action metadata.

The exact action kinds and parameter branches are:

| `action_kind` | Exact `parameters` members |
| --- | --- |
| `COMMIT_DUE_EVENT` | `deadline_kind`, `due_at`, `deadline_entity_id` |
| `RESTORE_CLOCK` | `clock_uncertain_event_id`, `trusted_time_source_sigil`, `clock_uncertainty_tolerance_seconds` |
| `FENCE_LEASE` | `lease_id`, `lease_binding_sigil`, `prior_fence_floor`, `tombstone_generation` |
| `REPUBLISH_TOMBSTONE` | `lease_id`, `tombstone_generation`, `original_terminal_event_sigil`, `sink_ids` |
| `OFFLINE_SESSION` | `worker_session_id`, `last_heartbeat_sequence`, `active_lease_ids` |
| `TERMINATE_PROCESS_TREE` | Closed union `TRACKED {kind, attempt_id, process_tree_identity, backend_configuration_sigil, termination_policy_sigil}` or `START_HANDLE {kind, attempt_id, backend_start_handle_sigil, backend_configuration_sigil, termination_policy_sigil}`. |
| `REVOKE_HANDLES` | `attempt_id`, `handle_set_sigil`, `sink_ids` |
| `CLOSE_SESSION` | `worker_session_id`, `backend_session_identity`, `control_channel_identity_sigil` |
| `CLOSE_LOG` | `attempt_id`, `stream`, `last_committed_sequence` |
| `VERIFY_OUTPUT_STORAGE` | `attempt_id`, `expected_output_set_sigil`, `storage_journal_id`, `storage_through_sequence`, `storage_through_event_sigil` |
| `VERIFY_TERMINAL_SOURCE` | `attempt_id`, `crucible_base_identity`, `crucible_base_sigil`, `retention_policy_sigil` |
| `BIND_DURABLE_ATTEMPT_AUTHORIZATION` | `attempt_id`, `authorization_subject_id`, `authorization_subject_sigil`, `authorization_transition_request_id`, `authorization_transition_request_sigil`, `authorization_event_id`, `authorization_event_body_sigil`, `authorization_receipt_id`, `authorization_receipt_sigil` |
| `RELEASE_INACTIVE_EXECUTION_INPUT_HOLD` | `root_kind`, `storage_root`, `owner_terminal_basis`, `release_authorization_id`, `release_authorization_sigil`; `root_kind` is `JOB_INPUT` or `ATTEMPT_INPUT`, `storage_root` is the complete matching binding, and `owner_terminal_basis` is the complete EHR `OWNER_TERMINAL` branch. |
| `RELEASE_DUE_EXECUTION_HOLD` | `job_id`, `release_schedule`, `release_authorization_id`, `release_authorization_sigil`; `release_schedule` is the complete matching `output_hold_release_schedules` entry, including its hold-set Event, duration, inactivation Event, due time, and deadline status. |
| `QUARANTINE_RESOURCE` | `attempt_id`, `resource_ids`, `reason_codes` |
| `ADVANCE_ATTEMPT` | `attempt_id`, `from_state`, `transition_cause` |
| `CLEAN_RESOURCE` | `attempt_id`, `resource_ids`, `cleanup_policy_sigil` |
| `COLLECT_ACCOUNTING` | `job_id`, `attempt_id`, `reservation`, `accounting_scope_sigil`, `backend_configuration_sigil`, `accounting_policy_sigil` |
| `SETTLE_BUDGET` | `job_id`, `attempt_id`, `reservation`, `accounting_capture_event_id`, `accounting_capture_event_sigil` |
| `EVALUATE_ATTEMPT_ASSURANCE` | `attempt_id`, `terminal_event_id`, `assurance_input_event_ids`; the input IDs are sorted and identify derivation-prefix or earlier-action evidence. |
| `EVALUATE_JOB_ASSURANCE` | Closed union `ATTEMPT {kind, job_id, attempt_id, attempt_assurance_event_id}` or `NOT_APPLICABLE {kind, job_id, reason}`; the latter reason is constant `NO_ATTEMPT_ALLOCATED`. |
| `ADVANCE_JOB` | `job_id`, `from_state`, `selected_attempt_id`, `transition_cause` |

Nullable values remain present: `last_heartbeat_sequence` is null when none,
`last_committed_sequence` is null for an empty stream, and
`selected_attempt_id` is null when no Attempt exists. No other action
parameter is nullable.

The action set is derived solely from the bound replay prefix. Sorting starts
with `(phase ordinal, action-kind ordinal)`, where action-kind ordinals follow
the printed order above. For `COMMIT_DUE_EVENT`, the remaining exact key is
`(due_at normalized instant, fixed deadline priority, deadline_entity_id
unsigned ASCII, target_event_type unsigned ASCII)`. For every other kind it
is `(entity-kind ordinal, entity_id unsigned ASCII, target_event_type unsigned
ASCII, canonical logical action unsigned bytes)`, with entity-kind order
`EXECUTOR`, `RECOVERY`, `WORKER`, `WORKER_SESSION`, `JOB`, `ATTEMPT`,
`LEASE`, `LOG_STREAM`. Duplicate logical actions are invalid. The canonical
logical action is the action object without
`ordinal`, `target_event_id`, or `target_sequence`; within a
`RECOVERY_DERIVATION` transition-cause template, it also replaces the
self-referential trigger event ID and effective sequence with the domain
constants `SELF_EVENT` and `SELF_SEQUENCE`. The reserved ID and sequence are
substituted only after sorting, avoiding a reservation cycle. External
observations may satisfy or fail an action but never change the frozen action
identity or ordering.

For a `STARTED` set, due-action derivation performs the ordinary deadline
sweep as a pure simulation over the bound prefix: it selects the least
applicable key, projects that primary event, virtually applies its complete
mandatory dependent stop/fence closure, then selects the next still-applicable
key. The set contains one `COMMIT_DUE_EVENT` only for each primary event that
survives that simulation, in selection order. The virtual dependent events
are not target events in `STARTED`; they become the exact `FENCING` actions
derived after the primary set completes. Thus a lower-priority key made
inapplicable by an earlier virtual closure is absent rather than committed
under a competing cause.

Each termination, revocation, close, cleanup, or verification action has a
fail-closed quarantine outcome within that same target event; it never derives
a new mid-phase action. `QUARANTINE_RESOURCE` is emitted separately only for
resources already known to require quarantine in the phase's derivation
prefix.

Allowed phase membership is exact:

- `STARTED` contains only `COMMIT_DUE_EVENT`;
- `FENCING` contains `FENCE_LEASE`, `REPUBLISH_TOMBSTONE`,
  `OFFLINE_SESSION`, `BIND_DURABLE_ATTEMPT_AUTHORIZATION`, and the
  `ADVANCE_ATTEMPT` or `ADVANCE_JOB` actions whose target transition is
  `STOPPING`;
- `RECONCILING` contains `TERMINATE_PROCESS_TREE`, `REVOKE_HANDLES`,
  `CLOSE_SESSION`, `CLOSE_LOG`, `VERIFY_OUTPUT_STORAGE`,
  `VERIFY_TERMINAL_SOURCE`, `QUARANTINE_RESOURCE`,
  `ADVANCE_ATTEMPT` actions that enter `CLEANING`,
  `CLEAN_RESOURCE`, and `COLLECT_ACCOUNTING`; and
- `FINALIZING` contains `RESTORE_CLOCK`, `ADVANCE_ATTEMPT` actions that enter
  a terminal Attempt state, `SETTLE_BUDGET`,
  `EVALUATE_ATTEMPT_ASSURANCE`, `EVALUATE_JOB_ASSURANCE`, and remaining
  `ADVANCE_JOB` actions, plus `RELEASE_INACTIVE_EXECUTION_INPUT_HOLD` and
  `RELEASE_DUE_EXECUTION_HOLD`.

An action kind in any other phase is invalid. The phase boundary is also the
dependency boundary: all verification and quarantine observations precede
terminal Attempt selection. Trusted accounting is captured in
`attempt.cleanup_progressed` after the Attempt enters `CLEANING` and after
every other metered Recovery action, so the later settlement and Job target
event are deterministic from the `FINALIZING` derivation prefix; action-kind
order then places terminal Attempt events before settlement, Attempt
assurance before Job assurance, and Job advancement last.
`RESTORE_CLOCK` is present exactly when the clock gate remains `UNCERTAIN`;
its target is the sole `executor.clock_restored` event, which carries the
exact Recovery action binding. If clock trust cannot be restored, that action
cannot complete and Recovery remains gated in `FINALIZING`.
The journal allocator deterministically reserves each pending action's unique
`target_event_id` from the domain-separated tuple `(journal_id, recovery_id,
phase, derived_through_event_sigil, ordinal, canonical logical action)` and
sets `target_sequence = derived_through_sequence + 2 + ordinal`: the
set-binding Recovery event occupies the intervening sequence. It does so
before the action-set Sigil is computed. Action-completion events commit
strictly by ordinal and use those exact envelope values. No ordinary external
mutation may interleave a current action set; a newly committed clock/epoch
interruption instead supersedes it through the rebase rule below. Reserved IDs
in a superseded set remain unusable history. These reservations also make an
enclosing `RECOVERY_DERIVATION` transition cause fully concrete before Sigil
computation.
An `executor.clock_uncertain` event or the first
`executor.epoch_started` event of a restarted process is the only event
allowed to consume a pending reserved sequence. It immediately invalidates
all uncommitted reservations in that set; only the required clock/epoch
control events and `recovery.action_set_rebased` may follow before the
replacement reservations become current.
Every action-completion event carries the common recovery-action binding
defined below, so replay can distinguish pending from completed actions
without inspecting a process table or mutable path.

When clock uncertainty or a new epoch interrupts an active Recovery, a
replacement set for the same phase is derived from the new verified prefix.
It preserves already completed action events, contains every still-required
old or new action in canonical order, binds the prior set in
`supersedes_action_set_sigil`, and becomes current only through
`recovery.action_set_rebased`. The superseded document remains immutable
history and cannot receive new completion bindings. Initial sets bound by
`recovery.started` or `recovery.phase_advanced` have a null
`supersedes_action_set_sigil`; a replacement set has that member equal to
`prior_action_set_sigil` in the rebasing event. `carried_completion_event_ids`
is unique, sorted by event sequence, and contains exactly those completion
events from the prior set or its transitive carry chain whose postconditions
remain valid in the new prefix. Their actions are omitted from the replacement
set. An action whose postcondition must be re-established is not carried and
appears as a fresh replacement-set action.
The rebasing event's `reason_event_id` identifies
`executor.clock_uncertain` when clock uncertainty consumed the reservation,
and otherwise the interrupting startup `executor.epoch_started`;
`new_epoch` equals the latest epoch in the replacement derivation prefix.

## Worker eligibility and identity

A Worker is an operational subject, not a principal with scientific authority.
Before it becomes schedulable, the Executor must:

1. validate the current Worker-definition revision and binding Sigil and
   require definition state `ENABLED`;
2. create and validate one fresh Worker Session bound to the current Executor
   instance and epoch;
3. verify the Session's backend identity, configuration Sigil, supported runtime, Host
   platform, resource ceiling, assurance profile, and conformance-suite tuple;
4. establish a bounded control channel that does not expose the journal or
   other Jobs' credentials;
5. record the independently verified capability tuple in the journal; and
6. place the Session in `READY` only if no reused Session, backend-session, or
   control-channel identity exists and every prior Session is unable to hold
   current authority.

The `0.4` runtime may implement the Worker in the same installation as the
Executor, but it must still allocate a fresh Worker Session identity and
enforce the protocol. A PID is recorded only as backend evidence and is
insufficient identity because PIDs are reusable.

One Worker Session may hold only the number of concurrent active Leases in its
verified `maximum_concurrency`. The `0.4` reference Worker defaults to one.
Capacity is scheduling information, not permission to share a Crucible,
credential, output namespace, or mutable sink between Attempts.

## Lifecycle overview

The journal serializes all transitions. The tables below are exhaustive:
transitions not listed are illegal. Terminal states have no outbound
transitions. A repeated request that carries the same idempotency key and exact
payload Sigil returns the originally committed event without appending a
transition. Reuse of that key with a different payload fails closed and is
recorded as a rejected protocol message.

Observation events such as a heartbeat, resource sample, log chunk, or
duplicate delivery do not change lifecycle state. They still require the exact
current object revision and bindings where their Schema calls for them.

A journal event may update several related projections atomically. In
particular, `job.attempt_allocated` changes the Job and creates its Attempt,
increments its fence generation, and reserves its exact Job-budget share,
while `lease.claimed` changes the Lease and Attempt and accounts for Worker
Session capacity. Lease release, revocation, expiry, and fencing also account
for Session capacity and advance the Job fence floor to an unassigned
tombstone in the same event. Replay applies all revisions and ledgers in such
an event or none of them; there is no valid prefix in which only part of the
relationship changed.

Attempt terminal state describes computation, termination, cleanup, and
quarantine only. It never asserts assurance or final Job-result eligibility.
`attempt.assurance_evaluated` is the only post-terminal Attempt observation
that may attach assurance evidence. It follows the one
`job.budget_settled` event for that Attempt and commits exactly once with
`CLAIMED`, `UNMET`, or `UNVERIFIABLE`; `CLAIMED` attaches one immutable claim
after validating the terminal-event and settlement Sigils, while the other
outcomes bind closed failure reasons and evidence Sigils. The event also
finalizes the parent Job's Attempt summary under the exact multi-owner
revision effects below. `NOT_APPLICABLE` is not valid for an allocated
Attempt because every Attempt has the pinned assurance profile.

Separately, `job.assurance_evaluated` commits exactly once before every Job
terminal event. Its closed `evaluation` enum is `CLAIMED`, `UNMET`,
`UNVERIFIABLE`, or `NOT_APPLICABLE`. For a Job with a selected or final
Attempt, it references that Attempt's completed evaluation and must agree with
it. `NOT_APPLICABLE` is permitted only when no Attempt was ever allocated,
binds the closed reason `NO_ATTEMPT_ALLOCATED`, and can never enable Job
success. Both evaluation events are state-neutral and cannot rewrite an
Attempt terminal fact.

### Job state machine

Job states are:

| State | Meaning |
| --- | --- |
| `SUBMITTED` | The closed Job and all immutable bindings were validated and durably appended. |
| `QUEUED` | The Job is eligible for Attempt allocation. |
| `ACTIVE` | An Attempt has been allocated and its retry or Job outcome has not yet been resolved. |
| `RETRY_WAIT` | The preceding Attempt is terminal and a permitted retry is waiting for its recorded eligibility time. |
| `STOPPING` | A terminal trigger is latched and no new Attempt may be allocated. |
| `SUCCEEDED` | One Attempt passed computation, result, termination, and cleanup checks and the separate Job assurance evaluation made its immutable Outcome acceptance-eligible. |
| `FAILED` | The Job ended without an eligible result for a non-policy, non-timeout, non-cancellation reason. |
| `CANCELLED` | An explicit cancellation won terminal ordering and shutdown completed or was safely quarantined. |
| `TIMED_OUT` | The Job deadline won terminal ordering. |
| `POLICY_VIOLATION` | A security or policy violation was established before terminalization. |

Legal Job transitions are:

The exact `job.stop_latched` cause-code enum is `CANCEL_REQUESTED`,
`JOB_DEADLINE`, `POLICY_VIOLATION`, `ADMISSION_INVALID`,
`FATAL_INFRASTRUCTURE`, `INTEGRITY_FAILURE`, `CLOCK_UNCERTAIN`,
`ATTEMPT_NONRETRYABLE`, `ATTEMPT_REJECTED`, `RETRY_EXHAUSTED`,
`RESULT_REQUIREMENT_FAILED`, `OUTPUT_VALIDATION_FAILED`,
`TERMINAL_SOURCE_RETENTION_FAILED`, `TERMINATION_FAILED`, `CLEANUP_FAILED`, `ASSURANCE_UNMET`,
`ASSURANCE_UNVERIFIABLE`, and `BUDGET_EXHAUSTED`.

| From | To | Required journal event and guard |
| --- | --- | --- |
| none | `SUBMITTED` | `job.submitted`; exact contracts, Ward decision, approval, freshness, idempotency, and deadline validate. |
| `SUBMITTED` | `QUEUED` | `job.queued`; admission remains valid. |
| `QUEUED` | `ACTIVE` | `job.attempt_allocated`; atomically creates one new Attempt in `CREATED`, allocates a new fencing generation and exact budget reservation, and confirms no other non-terminal Attempt. |
| `ACTIVE` | `RETRY_WAIT` | `job.retry_scheduled`; preceding Attempt is terminal, assurance evaluation and budget settlement are complete, its operational outcome is retryable, a next reservation can fit, and retry eligibility time is recorded. |
| `RETRY_WAIT` | `QUEUED` | `job.retry_ready`; eligibility time arrived, contracts remain valid, and Job deadline has not passed. |
| `SUBMITTED`, `QUEUED`, `RETRY_WAIT` | `STOPPING` | `job.stop_latched`; the cause is one of `CANCEL_REQUESTED`, `JOB_DEADLINE`, `POLICY_VIOLATION`, `ADMISSION_INVALID`, `FATAL_INFRASTRUCTURE`, `INTEGRITY_FAILURE`, or `CLOCK_UNCERTAIN`. |
| `ACTIVE` | `STOPPING` | `job.stop_latched`; any exact cause is legal when its bound evidence establishes the external trigger, a non-retryable/rejected Attempt, exhausted retry or budget, failed result/output/termination/cleanup, or completed `UNMET`/`UNVERIFIABLE` Job assurance evaluation. |
| `ACTIVE` | `SUCCEEDED` | `job.succeeded`; the selected Attempt is terminal `SUCCEEDED`, its result requirement and frozen storage observations pass, `CODE_MODIFICATION` terminal source is `VERIFIED`, budget settlement and `job.assurance_evaluated: CLAIMED` are complete, the claim satisfies the exact request, and no precedence conflict exists. |
| `STOPPING` | `FAILED` | `job.failed`; budget settlement where applicable and one `job.assurance_evaluated` are complete, and the cause resolves to infrastructure, validation, exhaustion, cleanup, or assurance failure. |
| `STOPPING` | `CANCELLED` | `job.cancelled`; explicit cancellation is the winning cause and one `job.assurance_evaluated` is complete. |
| `STOPPING` | `TIMED_OUT` | `job.timed_out`; Job deadline is the winning cause and one `job.assurance_evaluated` is complete. |
| `STOPPING` | `POLICY_VIOLATION` | `job.policy_violated`; a policy violation is established and one `job.assurance_evaluated` is complete. |

A non-retryable or exhausted Attempt first moves the Job from `ACTIVE` to
`STOPPING` with its precise cause, then to the applicable terminal state.
The v1 `queue_key` has exactly `ready_sequence` and `job_id`.
`ready_sequence` is the enclosing `job.queued` or `job.retry_ready` sequence,
assigned before Sigil computation. Among Jobs eligible for a particular
verified Worker Session, allocation order is ascending
`(ready_sequence, job_id unsigned ASCII)`. There is no hidden priority,
directory-order, clock-time, or process-local tie breaker.
Terminal Job events include all Attempt IDs and terminal states, the selected
result disposition and assurance-claim Sigils if any, cleanup or quarantine
status, selected Worker Session binding, first stop-or-fence binding, frozen
storage-observation ID-and-Sigil binding, the budget ledger Sigil, and the
`job.assurance_evaluated` event Sigil. No Job terminal event can precede that
evaluation. A cancellation against an already terminal Job appends the
state-neutral `job.cancellation_observed` event described below and never
changes this state machine.

### Attempt state machine

Attempt states are:

| State | Meaning |
| --- | --- |
| `CREATED` | Identity, retry ordinal, fence generation, and immutable bindings exist. |
| `PREFLIGHTING` | Policy, Snapshot, backend, assurance eligibility, inputs, and Crucible are being verified or materialized. |
| `READY` | Preflight passed and the exclusive Crucible is eligible for a Lease. |
| `LEASED` | A Lease was offered and claimed by the bound Worker. |
| `STARTING` | The backend is creating the process tree and control handles. |
| `RUNNING` | Worker execution is live under the current Lease. |
| `DRAINING` | The process reported completion or exited; logs, outputs, and runtime evidence are being closed and validated. |
| `STOPPING` | Authority is revoked or a terminal trigger requires process and handle shutdown. |
| `CLEANING` | Termination status, mutable-resource isolation, output quarantine/publication, and cleanup evidence are being finalized. |
| `SUCCEEDED` | Computation, the closed result requirement, termination, and required cleanup passed; realized assurance is evaluated afterward without changing this terminal state. |
| `FAILED` | Computation, result validation, output bounds, required terminal-source retention, infrastructure, termination, or cleanup failed. |
| `CANCELLED` | Explicit cancellation won terminal ordering. |
| `TIMED_OUT` | The Attempt or Job wall-time deadline won terminal ordering. |
| `POLICY_VIOLATION` | A policy or security boundary violation was established. |
| `LEASE_EXPIRED` | Lease expiry won terminal ordering before valid completion. |
| `LOST` | Worker/process ownership or termination could not be established; affected resources are quarantined. |
| `FENCED` | Recovery or authority replacement invalidated the Attempt before completion. |
| `REJECTED` | Preflight failed before Worker authority was granted. |

Legal Attempt transitions are:

| From | To | Required journal event and guard |
| --- | --- | --- |
| none | `CREATED` | `job.attempt_allocated`; the same event atomically changes the Job to `ACTIVE`, creates the Attempt, assigns an unused ordinal, and allocates a fencing generation greater than every prior generation for the Job. |
| `CREATED` | `PREFLIGHTING` | `attempt.preflight_started`; immutable bindings revalidate and per-Attempt authorization is `NONE` or `BOUND`. |
| `CREATED` | `STOPPING` | `attempt.stop_latched`; cancellation, deadline, recovery fence, fatal integrity, or budget invalidation was committed before preflight began. |
| `PREFLIGHTING` | `READY` | `attempt.preflight_passed`; all required checks and immutable materialization identities are durably recorded. |
| `PREFLIGHTING` | `STOPPING` | `attempt.stop_latched`; preflight rejection, cancellation, deadline, or policy failure. |
| `READY` | `LEASED` | `lease.claimed`; the same event atomically activates the one offered Lease and accounts for the selected Worker Session's capacity. |
| `READY` | `STOPPING` | `attempt.stop_latched`; cancellation, deadline, unclaimed Lease-offer/claim expiry, recovery fence, or loss of preflight validity. |
| `LEASED` | `STARTING` | `attempt.starting`; active Lease and backend start handle are recorded. |
| `LEASED` | `STOPPING` | `attempt.stop_latched`; active Lease expiry or authority loss, cancellation, timeout, policy revocation, or recovery fence. |
| `STARTING` | `RUNNING` | `attempt.running`; exact process-tree identity and active control handles are recorded before Worker code proceeds. |
| `STARTING` | `STOPPING` | `attempt.stop_latched`; start failure, cancellation, timeout, Lease loss, policy violation, or recovery fence. |
| `RUNNING` | `DRAINING` | `attempt.draining`; a preceding `attempt.result_accepted` or `attempt.result_rejected` disposition, or the explicit absence of a Worker result after observed process exit, is durably bound. |
| `RUNNING` | `STOPPING` | `attempt.stop_latched`; cancellation, deadline, Lease/heartbeat loss, policy violation, or recovery fence. |
| `DRAINING` | `CLEANING` | `attempt.cleaning`; result, logs, outputs, and runtime evidence are closed or explicitly quarantined. |
| `DRAINING` | `STOPPING` | `attempt.stop_latched`; a still-live process or handle requires revocation because validation exposed a violation. |
| `STOPPING` | `CLEANING` | `attempt.cleaning`; termination/revocation was verified or ambiguous resources were quarantined. |
| `CLEANING` | any terminal Attempt state | Matching `attempt.<terminal>` event; terminal precedence, result disposition, computation, termination, cleanup, quarantine, immutable assurance inputs, and the exact durable output-storage-observation-set reference are complete; realized assurance remains a later evaluation. |

Every terminal Attempt requires `storage_observation_binding: FROZEN`,
including a preflight rejection or an Attempt with no Result, no outputs,
three empty Log streams, or no Blob-bearing resource evidence; those cases use
the observation contract's explicit `NONE` and `EMPTY` branches.
`attempt.succeeded` additionally requires an eligible storage disposition for
every required output and, under `CODE_MODIFICATION`,
`terminal_source_binding: VERIFIED`. A quarantined or unavailable required
output or terminal source selects `attempt.failed` with the precise
validation, retention, or cleanup cause; it can never produce Job
`SUCCEEDED`.

For `CODE_MODIFICATION`, source retention verification or quarantine finishes
before `attempt.cleaning` commits. That event freezes the exact
`terminal_source_binding`; cleanup progress cannot replace it, and the
Attempt terminal event and selected Job terminal event repeat it byte for
byte. A crash after `attempt.cleaning` therefore resumes other missing cleanup
without recrawling a mutable Crucible or changing the source disposition.

`PREFLIGHTING`, `DRAINING`, `STOPPING`, and `CLEANING` may record their
bounded progress events without changing state. `attempt.cleanup_progressed`
is the shared finalization-progress event in `DRAINING`, `STOPPING`, or
`CLEANING`; its closed `step` determines which state's evidence is legal.
Progress may not skip required evidence. No transition goes directly from a
live state to terminal because termination and cleanup must be evaluated
first.
Before any terminal Attempt event, `CLEANING` also commits exactly one
`attempt.cleanup_progressed` with `step: ACCOUNTING_CAPTURED`, binding the
trusted supervisor's final per-dimension accounting evidence or explicit
unavailability. In that branch, `cleanup_evidence_sigil` is the complete
immutable accounting-evidence-set Sigil from which every later settlement
field is derived, and `finalization_bindings` is
`FROZEN {kind, control_evidence_set_binding,
quarantine_binding_set_binding, terminalization_storage_manifest_binding,
output_root_protection}`. The three record bindings are their exact
resolvable ID-and-Sigil pairs; all referenced closed documents and the
selected hold, when present, are durable before the event. Every earlier cleanup-progress step instead has
`finalization_bindings: NONE {kind}`. `ACCOUNTING_CAPTURED` is legal only in
`CLEANING`, after every metered backend, retention, output, evidence,
Quarantine, and cleanup action is finished. After it commits, only the bounded
immutable terminalization payloads reserved as Executor control overhead,
journal events, settlement, and assurance/Job evaluation may follow; any need
for further metered Blob, Replica, backend, retention, output, evidence,
Quarantine, or cleanup work prevents terminalization rather than silently
escaping the capture. The terminal event cannot precede that immutable
capture.

`attempt.result_accepted` is state-neutral and legal only in `RUNNING`.
`attempt.result_rejected` is state-neutral: the first result disposition may
occur in `RUNNING`, and a novel late or conflicting message may be recorded in
any later state. Exactly one first disposition is committed before
`attempt.draining` when a Worker result arrives. Acceptance validates the
current Lease and stores the immutable result Sigil; rejection stores the
result or message Sigil and closed reasons. An exact duplicate returns the
historical disposition without appending an event, changing revisions,
restoring liveness, or reactivating Lease authority. A conflicting second
result appends `attempt.result_rejected` only when it is a new bounded protocol
message; it never replaces the first disposition.

An Attempt terminal event preserves separately:

- the winning terminal trigger and its journal sequence;
- Worker-reported status and process exit information;
- exact Worker ID, Worker binding Sigil, Worker Session ID, and Session binding
  Sigil, or explicit absence before authority;
- Lease terminal state;
- the first stop-or-fence event ID, Sigil, type, and effective sequence, or
  explicit absence;
- process-tree termination status;
- cleanup or quarantine status;
- log and output closure status;
- frozen Storage Journal prefix and immutable, resolvable
  output-storage-observation-set ID and Sigil;
- accepted or rejected result disposition and rejection reasons;
- requested assurance and the pending assurance-evaluation status; and
- the exact frozen control-evidence-set, quarantine-binding-set, output ESM,
  and output-root-protection bindings bound by the final accounting event.

For `CODE_MODIFICATION`, it additionally preserves the immutable Crucible Base
identity and Sigil, retained terminal-source identity, Sigil, and storage
BlobRef, exact
retention-policy Sigil, file and byte counts, storage or quarantine status,
and verifier-evidence Sigil. Those conditional fields are absent for `NONE`.

This prevents a `CANCELLED`, `LOST`, or `LEASE_EXPIRED` label from hiding a
computation failure, cleanup failure, or policy observation.

### Lease state machine

Lease states are:

| State | Meaning |
| --- | --- |
| `OFFERED` | A time-bounded authority is addressed to exactly one immutable Worker Session but is not yet claimed. |
| `ACTIVE` | The bound Worker Session proved possession of the Lease credential before the claim deadline. |
| `RELEASED` | The Worker and Executor completed normal handoff and no further use is valid. |
| `REVOKED` | Cancellation, timeout, policy change, or fatal failure withdrew authority. |
| `EXPIRED` | The claim or active Lease deadline passed before a valid release. |
| `FENCED` | Executor recovery or authority replacement invalidated the Lease generation. |

Legal Lease transitions are:

| From | To | Required journal event and guard |
| --- | --- | --- |
| none | `OFFERED` | `lease.offered`; Attempt is `READY`, Worker is `READY` or `BUSY` below verified capacity, and the Lease bindings and credential digest are durable. |
| `OFFERED` | `ACTIVE` | `lease.claimed`; exact Worker Session, credential proof, Executor epoch, fence generation, and claim deadline validate. |
| `OFFERED` | `EXPIRED` | `lease.expired`; claim deadline passed before a valid claim. |
| `OFFERED` | `REVOKED` | `lease.revoked`; Job or Attempt stop trigger was committed. |
| `OFFERED` | `FENCED` | `lease.fenced`; Executor epoch changed or ownership became ambiguous. |
| `ACTIVE` | `ACTIVE` | `lease.renewed`; explicit renewal committed before expiry and within all maximum deadlines. |
| `ACTIVE` | `RELEASED` | `lease.released`; process tree and side-effect handles are closed and Worker completion handoff is durable. |
| `ACTIVE` | `REVOKED` | `lease.revoked`; cancellation, timeout, policy revocation, or fatal failure withdrew authority. |
| `ACTIVE` | `EXPIRED` | `lease.expired`; trusted Executor time reached expiry before release or renewal committed. |
| `ACTIVE` | `FENCED` | `lease.fenced`; Executor epoch changed or recovery invalidated ownership. |

Renewal changes only the active Lease projection's expiry, renewal counter, and
revision. It does not create a new Lease, rotate the fence generation, or
erase earlier expiry values. A terminal Lease can never be renewed, reclaimed,
or released a second time.

`lease.expired` commits before its causally linked
`attempt.stop_latched`. For an expired `OFFERED` Lease the Attempt is still
`READY`, and the next event uses the legal `READY -> STOPPING` path with cause
`LEASE_CLAIM_EXPIRED`. For an expired `ACTIVE` Lease it uses the Attempt's
current authority-bearing state with cause `LEASE_ACTIVE_EXPIRED`. A crash
between the two events leaves a replay-visible required action that Recovery
must complete; no Worker claim or message can enter that prefix.

### Worker-definition and Worker-Session state machines

A stable Worker definition and a live Worker Session have separate
projections. Worker-definition states are:

| State | Meaning |
| --- | --- |
| `REGISTERED` | One immutable definition revision is recorded but not enabled. |
| `ENABLED` | The current definition revision may create eligible Sessions. |
| `DRAINING` | No new Session or Lease may be admitted; existing Sessions are being closed. |
| `QUARANTINED` | Definition, verification, or policy failure prevents use. |
| `RETIRED` | The Worker identity is administratively terminal. |

Legal Worker-definition transitions are:

| From | To | Required event and guard |
| --- | --- | --- |
| none | `REGISTERED` | `worker.definition_registered`; definition revision zero and its exact Sigil validate. |
| `REGISTERED` | `ENABLED` | `worker.enabled`; independent capability verification is complete. |
| `REGISTERED` | `QUARANTINED`, `RETIRED` | `worker.quarantined` or `worker.retired`; validation fails or administration retires it. |
| `ENABLED` | `DRAINING`, `QUARANTINED` | `worker.draining` or `worker.quarantined`; all affected Sessions atomically stop accepting Leases. |
| `ENABLED` | `RETIRED` | `worker.retired`; no non-terminal Session or Lease remains. |
| `DRAINING` | `ENABLED` | `worker.enabled`; a new immutable definition revision is bound and revalidated before admission resumes. |
| `DRAINING` | `QUARANTINED`, `RETIRED` | `worker.quarantined` or `worker.retired`; retirement requires every Session and Lease terminal. |
| `QUARANTINED` | `ENABLED` | `worker.enabled`; an explicit new immutable definition revision and independent revalidation pass. |
| `QUARANTINED` | `RETIRED` | `worker.retired`; every Session and Lease is terminal. |

`RETIRED` has no outbound transition. Definition revisions never carry
liveness or Lease capacity.

Worker-Session states are:

| State | Meaning |
| --- | --- |
| `REGISTERED` | One immutable Session is bound to the current Executor epoch but not schedulable. |
| `READY` | Verification and liveness are current and no active Lease is held. |
| `BUSY` | One or more active Leases are held below or at the Session ceiling. |
| `DRAINING` | No new Lease is accepted while existing work is revoked or completed. |
| `OFFLINE` | Liveness is lost or the bound Executor epoch is obsolete. |
| `QUARANTINED` | Session identity, protocol, policy, or evidence failed. |
| `CLOSED` | The Session is terminal and can never receive or renew authority. |

Legal Worker-Session transitions are:

| From | To | Required event and guard |
| --- | --- | --- |
| none | `REGISTERED` | `worker_session.registered`; fresh Session, backend-session, and control-channel identities, current epoch, enabled definition, and exact bindings validate. |
| `REGISTERED` | `READY`, `OFFLINE`, `QUARANTINED`, `CLOSED` | `worker_session.ready`, `worker_session.offline`, `worker_session.quarantined`, or `worker_session.closed`. |
| `READY` | `BUSY` | `lease.claimed`; capacity accounting is atomic with Lease and Attempt transitions. |
| `READY` | `DRAINING`, `OFFLINE`, `QUARANTINED`, `CLOSED` | Matching `worker_session.<state>` event; direct close requires no active Lease. |
| `BUSY` | `BUSY` | `lease.claimed` below capacity, or one of several Leases terminalizes while another remains active. |
| `BUSY` | `READY` | A Lease-terminal event releases the final capacity slot while definition and Session remain eligible. |
| `BUSY` | `DRAINING`, `OFFLINE`, `QUARANTINED` | Matching Session event atomically prevents admission and latches revocation or fencing for every active Lease. |
| `DRAINING` | `OFFLINE`, `QUARANTINED`, `CLOSED` | Matching Session event; close requires every Lease terminal. Revalidation creates a new Session rather than returning this one to `READY`. |
| `OFFLINE`, `QUARANTINED` | `CLOSED` | `worker_session.closed`; all Leases and backend handles are terminal, revoked, fenced, or quarantined. |

`CLOSED` has no outbound transition. `OFFLINE` and `QUARANTINED` Sessions
cannot receive or renew a Lease and can only close. A returning process or
re-established channel creates a new Session ID; it never reactivates an old
Session or Lease.

## Fencing and exclusive side effects

Each Job owns a monotonically increasing unsigned 64-bit `fencing_counter` and
a durable `fence_floor`. Allocation of every Attempt atomically increments the
counter, assigns that value as the Attempt's `fencing_generation`, and moves
the floor to it. Release, revocation, expiry, or fencing of a Lease atomically
increments the counter again and publishes the new value as an unassigned
fence tombstone. This makes the preceding credential stale even when no
replacement Attempt exists. A later Attempt receives a value strictly greater
than the tombstone. Counter exhaustion fails the Job closed; it never wraps.

Executor recovery also advances a global unsigned 64-bit `executor_epoch`.
The effective public fence tuple for an active Attempt is:

```text
(journal_id, executor_epoch, job_id, attempt_id, lease_id,
 fencing_generation)
```

The unguessable Lease credential proves possession but is not the fencing
order. Every Worker message repeats the public fence tuple and proves the
credential through the protected control channel. A valid credential with a
stale tuple is rejected; a current tuple without credential proof is rejected.

The Executor and each side-effecting sink maintain the highest accepted
Executor epoch and the Job's current fence floor. They reject generations
below the floor and reject a different Attempt or Lease at an assigned current
generation. A tombstone has no valid Attempt or Lease. A new assigned
generation is published durably before its credential is delivered, and every
tombstone is published before revocation is acknowledged. No Worker controls
or increments either counter.

Result fencing is mandatory at every assurance level: only the current,
unexpired, active Lease may contribute Worker-originated result, log, output,
or runtime observations. Late material is retained or quarantined with a
rejection reason but cannot become eligible through retry or manual
relabeling. After Lease termination, only the trusted Executor, backend, or
evidence verifier may append termination, revocation, cleanup, and assurance
evidence, bound to both the Attempt generation and the terminal fence
tombstone.

Result acceptance is evaluated at the journal sequence of
`attempt.result_accepted`. If the Lease was current, active, unexpired, and
unrevoked at that sequence, the accepted result remains historically
well-fenced evidence after a later normal `lease.released` and the mandatory
higher fence-floor tombstone. The later tombstone does not retroactively turn
that historical acceptance into a stale message, and replay must preserve the
original disposition.

Historical acceptance is necessary but not sufficient for Outcome selection.
An accepted result can be selected only when:

1. no `job.stop_latched`, `attempt.stop_latched`, `lease.revoked`,
   `lease.expired`, `lease.fenced`, `executor.clock_uncertain`, or
   policy/integrity trigger has an effective trigger sequence no later than
   the result-acceptance sequence;
2. no later evidence proves that authority had already been lost when the
   result was accepted;
3. no conflicting second result or output identity exists;
4. the normal termination, release, cleanup, budget settlement, and assurance
   evaluation complete; and
5. the Attempt and Job terminal guards select that exact acceptance-event and
   result Sigil.

Normal release or a tombstone committed after accepted completion satisfies
fence closure rather than violating item 1. A duplicate result delivered
after release, revocation, expiry, fencing, restart, or terminalization returns
the original historical disposition only; it cannot restore authority, append
a second acceptance, or make the result newly selectable.

At `SANCTUM-A2`, result fencing alone is not sufficient. On cancellation,
timeout, policy revocation, heartbeat loss, Lease expiry, or recovery, the
backend must:

1. prevent new process creation;
2. terminate the complete process tree;
3. revoke filesystem, network, credential, IPC, output, and external-sink
   handles;
4. publish the revocation generation to every sink that supports fencing;
5. verify termination and revocation independently of Worker testimony; and
6. quarantine any resource whose exclusivity cannot be proved.

A sink that cannot revoke an issued handle must validate the current fence
tuple against Executor state on every side-effecting operation. A sink that
can do neither is ineligible for A2 and cannot be shared with a replacement
Attempt.

At A1, the supervisor must still enforce wall-time and cancellation for the
tracked cooperative process group and must not reuse an ambiguously owned
Crucible or output namespace. A1 makes no hostile-containment claim. At A0,
stale result rejection and operational identity remain mandatory even though
process containment is not claimed.

## Heartbeat and renewal protocol

Worker and Lease liveness are separate:

- a Worker heartbeat proves only that the registered Worker control session
  responded;
- a Lease heartbeat reports bounded progress and resource observations for one
  Attempt under the current fence tuple;
- neither heartbeat extends a Lease; and
- a Worker heartbeat never proves that its process tree, policy controls, or
  side-effect handles are healthy.

The `execution-heartbeat/1.0` common object has exactly these required
members: `schema_version`, `scope`, `worker_id`, `worker_session_id`,
`worker_session_binding_sigil`, `executor_epoch`, `sequence`,
`prior_accepted_sequence`, `status`, `resource_sample`, `observed_at`, and
`message_sigil`. `scope` is `WORKER` or `LEASE`; `prior_accepted_sequence` is
the preceding unsigned sequence or `null` only for sequence zero. The
resource sample is a closed bounded object with exact CPU, memory, storage,
process, and network entries. Every entry has exactly `status` and `value`;
`status` is `OBSERVED` with a non-negative integer value or `UNAVAILABLE` with
`value: null`. A denied and observed facility reports zero rather than
`UNAVAILABLE`.

For `LEASE`, the fields `job_id`, `attempt_id`, `lease_id`,
`lease_binding_sigil`, `fence_tuple`, and `credential_proof` are all required.
For `WORKER`, all six are absent. `challenge_response` is required exactly
when the active Session policy names an outstanding Executor challenge and is
otherwise absent. No Worker-instance or session-generation field exists.

The Executor records its receive time. For each scope:

- a new sequence with valid bindings is appended before it updates liveness;
- an exact duplicate sequence and message Sigil is idempotent;
- a duplicate sequence with different content is a protocol violation;
- a lower sequence is stale and rejected;
- a skipped sequence is recorded as a gap but may be accepted only when the
  profile declares loss-tolerant heartbeats; and
- heartbeats arriving after a committed stop, Lease expiry, session change, or
  Executor epoch change are late and cannot restore liveness.

The Execution Specification sets `heartbeat_interval_seconds` and
`heartbeat_timeout_seconds` within the assurance profile's limits. Heartbeat
timeout must be shorter than the active Lease duration. When the trusted
receive-time deadline passes, the Executor first appends the due liveness-loss
event, then revokes or fences the Lease. It does not accept a concurrently
arriving heartbeat first merely because deadline processing was delayed.

A Worker may request renewal, but only the Executor grants it. Renewal is
valid only when:

1. the Lease is `ACTIVE` and the request arrives and commits before its current
   expiry;
2. Worker Session, credential proof, Executor epoch, fence tuple, heartbeat
   sequence, and Lease revision match;
3. Job and Attempt are not stopping or terminal;
4. Snapshot, policy, backend eligibility, and any revocation state remain
   valid;
5. the latest required heartbeat is within its deadline;
6. the proposed expiry is later than the current expiry but no later than the
   Attempt deadline, Job deadline, Lease maximum expiry, or policy ceiling; and
7. the durable `lease.renewed` event commits before the Executor acknowledges
   renewal.

A renewal request after expiry is rejected even if the Worker believes it was
sent earlier. Clock skew cannot resurrect authority. The Worker clock is not
used to decide expiry.

## Cancellation, timeouts, and terminal ordering

Cancellation is an idempotent Job-scoped request containing a cancellation
request ID, idempotency-key Sigil, actor and Host provenance, bounded reason,
request time, Job ID and binding Sigil, and expected Job revision. RFC-0015
defines its transport. This RFC defines its effect.

Every Job or Attempt deadline, Lease claim or expiry, heartbeat timeout, retry
eligibility time, and cancellation grace has one durable UTC `due_at`. On
process start, and after each newly committed or renewed due time, the
Executor creates an in-process anchor:

```text
(trusted_utc_at_anchor, monotonic_at_anchor, due_at)
remaining = due_at - trusted_utc_at_anchor
```

If `remaining <= 0`, the deadline is already due. Otherwise the live timer
expires when monotonic elapsed time reaches `remaining`; a later wall-clock
adjustment cannot extend it. Monotonic values are process-local observations
and are never persisted or compared across restart. After restart, replay
reads each durable `due_at`, verifies the current UTC clock against the last
trusted journal time, and establishes fresh monotonic anchors before any
authority can be issued.

Before committing any heartbeat, renewal, result, cancellation, or scheduling
transition, the Executor collects every already-due deadline and commits them
in ascending exact key order:

```text
(due_at, fixed_priority, entity_id)
```

UTC text is compared as its normalized instant and `entity_id` by unsigned
ASCII bytes. The closed priorities, lowest first, are:

| Priority | Deadline kind | Entity ID |
| --- | --- | --- |
| 10 | `JOB_DEADLINE` | Job ID |
| 20 | `ATTEMPT_DEADLINE` | Attempt ID |
| 30 | `HEARTBEAT_TIMEOUT` | Worker Session ID or Lease ID |
| 40 | `LEASE_EXPIRY` | Lease ID |
| 50 | `LEASE_CLAIM_DEADLINE` | Lease ID |
| 60 | `CANCELLATION_GRACE` | Attempt ID |
| 70 | `RETRY_ELIGIBILITY` | Job ID |

Only a deadline applicable to the replayed state participates:
`JOB_DEADLINE` applies to `SUBMITTED`, `QUEUED`, `ACTIVE`, or `RETRY_WAIT`;
`ATTEMPT_DEADLINE` applies to `CREATED`, `PREFLIGHTING`, `READY`, `LEASED`,
`STARTING`, `RUNNING`, or `DRAINING`; Worker-Session heartbeat timeout applies
to `READY`, `BUSY`, or `DRAINING`; Lease heartbeat timeout and
`LEASE_EXPIRY` apply only to `ACTIVE`; `LEASE_CLAIM_DEADLINE` applies only to
`OFFERED`; and cancellation grace applies to `STOPPING` only until
`FORCE_TERMINATION_DUE` is committed. `RETRY_ELIGIBILITY` applies only to
`RETRY_WAIT`. A state transition in an earlier key removes any
now-inapplicable later key before the next due item is selected.

Processing one key also commits its mandatory dependent stop/fence events
under the same writer lock before selecting the next key. Those dependent
events use the primary event as their `PRIOR_EVENT` trigger and copy its
effective sequence. A crash between the primary and dependent events leaves a
deterministic Recovery action for that exact propagation. Consequently, for
example, a simultaneous Job and Attempt deadline latches `JOB_DEADLINE` on
both Job and Attempt, while a heartbeat timeout ordered before Lease expiry
latches the heartbeat-loss chain rather than relabeling it as expiry.

The sole append-order exception is Recovery `STARTED`: authority is already
globally gated, so its `COMMIT_DUE_EVENT` actions commit the causally surviving
primary due events in the exact order produced by the virtual-closure sweep
above. The subsequently derived `FENCING` action set materializes each
previously simulated dependent Lease, Attempt, Session, and Job transition
before any authority can resume. No request or ordinary event may interleave.
Each dependent transition identifies its earliest applicable primary event as
the `PRIOR_EVENT` trigger and copies that event's effective sequence. This
two-phase representation has exactly the same winning causes and surviving
due keys as immediate propagation, while preserving the invariant that one
Recovery action owns one reserved target event.

Before a pending Cancel request is compared, each due chain that affects its
Job advances that Job revision exactly once: directly through
`job.stop_latched`, through a Lease-terminal fence-floor update, or, when no
Lease event exists, through the parent ordering projection in
`attempt.stop_latched`. Thus an already-due Attempt deadline cannot leave the
same expected Job revision and be relabeled by a concurrent cancellation.

This key, not timer callback order, directory order, thread order, or receive
timestamp, decides simultaneous due work. After all due events commit,
journal sequence decides genuinely non-due concurrent triggers. The first
committed terminal trigger is latched and cannot be replaced merely to obtain
a more convenient status.

There are four independent authority bounds plus one stop-escalation bound:

| Bound | Effect |
| --- | --- |
| Job `deadline_due_at` | Stops the Job and prevents all retries. |
| Attempt `deadline_due_at` | Stops only the current Attempt; retry depends on policy and remaining Job time. |
| Lease `claim_due_at` | Expires an unclaimed offer and terminates that Attempt. |
| Lease expiry or heartbeat `due_at` | Removes Worker authority and terminates or quarantines the Attempt. |
| Attempt `grace_due_at` | Ends cooperative cancellation grace and invokes mandatory termination without changing the already latched cause. |

The exact durable calculations use checked UTC arithmetic:

```text
job.deadline_due_at =
  job.submitted_at + job_wall_time_seconds
attempt.deadline_due_at =
  min(attempt.created_at + attempt_wall_time_seconds,
      job.deadline_due_at)
lease.claim_due_at =
  min(lease.offered_at + lease_claim_timeout_seconds,
      attempt.deadline_due_at, job.deadline_due_at)
lease.initial_expiry_due_at =
  min(lease.offered_at + lease_duration_seconds,
      lease.maximum_expiry_due_at,
      attempt.deadline_due_at, job.deadline_due_at)
worker_session_heartbeat.initial_due_at =
  worker_session.ready.recorded_at + heartbeat_timeout_seconds
worker_session_heartbeat.next_due_at =
  last_accepted_receive_time + heartbeat_timeout_seconds
lease_heartbeat.next_due_at =
  min(last_accepted_receive_time + heartbeat_timeout_seconds,
      lease.current_expiry_due_at,
      attempt.deadline_due_at, job.deadline_due_at)
attempt.grace_due_at =
  attempt.stop_latched.recorded_at + cancellation_grace_seconds
```

`lease.maximum_expiry_due_at` is the immutable minimum of the Attempt, Job,
and resolved policy ceilings. A renewal's `new_expiry_due_at` is the minimum
of its validated proposal and those same ceilings and must be strictly later
than current expiry. Checked-arithmetic failure rejects creation or renewal;
it never saturates to a later time. `worker_session.ready` durably binds the
initial heartbeat due time before the Session is schedulable. The
Worker-Session heartbeat branch has no Lease, Attempt, or Job ceiling. When
cancellation grace becomes due, the Executor appends
`attempt.stop_progressed` with `step: FORCE_TERMINATION_DUE` before invoking
the mandatory backend path.

If UTC moves backward beyond `clock_uncertainty_tolerance_seconds`, wall and
monotonic elapsed time diverge beyond that tolerance, the monotonic source
resets, suspend/resume behavior is unknowable, or UTC trust otherwise cannot
be established, the Executor must commit `executor.clock_uncertain` using a
non-decreasing time derived from its last trusted anchor. Outside the initial
startup clock check, including during an active Recovery, it does so under the
writer lock, immediately gates authority, and appends a strictly greater
`executor.epoch_started`. At startup, step 3 below has already created a fresh
gated epoch; uncertainty found by step 4 appends
`executor.clock_uncertain` in that epoch and does not allocate a redundant
second epoch for the same observation. It then follows exactly one branch:

- with no active Recovery, it derives and durably stores a new `STARTED`
  action set and appends `recovery.started` with a fresh `recovery_id` and the
  most recent completed Recovery as `prior_recovery_id`; or
- with an incomplete Recovery, it retains that `recovery_id` and phase,
  derives a replacement current-phase action set from the new prefix, and
  appends `recovery.action_set_rebased` before any further action completion.

That new or rebased runtime Recovery:

1. disables scheduling, Session readiness, Lease offer, claim, renewal, result
   acceptance, and new side-effect authority;
2. fences every `OFFERED` or `ACTIVE` Lease and publishes its tombstone;
3. moves every affected non-terminal Attempt through `STOPPING`;
4. treats a durable deadline as due whenever it cannot prove that the deadline
   remains in the future; and
5. terminates or quarantines live processes and handles.

Clock uncertainty never lengthens authority. `executor.clock_restored` may
commit only after a trusted UTC source and fresh monotonic anchor are
validated within that Recovery. It does not restore any old Session, Lease, or
Attempt authority; the new Recovery must reach `COMPLETED`, and normal new
Session/Attempt identities are still required. A crash anywhere in this
ordering replays the clock gate and either continues the incomplete Recovery
or creates only the missing action-set start/rebase event; it never creates a
second active Recovery or resumes the pre-uncertainty epoch.

An explicit cancellation committed before a due deadline wins over a later
timeout. A due deadline committed first cannot be relabeled cancellation.
Policy violations discovered before terminal commitment are an escalation:
they are always retained, make the result ineligible, and terminalize the
Attempt and Job as `POLICY_VIOLATION` even if another stop trigger was already
latched. Ambiguous process ownership terminalizes the Attempt as `LOST` and
forces quarantine; it is never reported as clean cancellation or timeout.

For a non-terminal Job, the first valid Cancel request is bound by
`job.stop_latched`, including `cancellation_request_id`,
`idempotency_key_sigil`, complete `cancel_request_sigil`, actor/Host
provenance, reason, and expected revision. An exact replay returns that
original cancellation record and a current observation without another event.
Conflicting reuse of either identity or key fails closed.

For a Job already terminal when the request is evaluated, and only when
`expected_job_revision` equals that terminal revision, the Executor appends
exactly one `job.cancellation_observed` for that request binding. The event
carries the same exact fields plus the existing terminal event ID and Sigil.
It is state-neutral: the Job state, cause, terminal event, and revision do not
change. Exact replay returns the original observation event; a conflicting key
is rejected.

If mandatory due-deadline processing changes state or revision before the
Cancel comparison, the request returns RFC-0015 `EXECUTION_CONFLICT` with the
new revision and appends no cancellation event. A later retry using the new
matching terminal revision may append `job.cancellation_observed`. Thus a
deadline is never relabeled cancellation and restart never turns a terminal
no-op into a cancellation transition.

After a stop trigger, no new Lease, renewal, retry, log stream, or result can
become eligible. The Executor requests graceful cooperative stop only for the
bounded cancellation grace. It then invokes the backend's mandatory
termination path. A2 termination and handle revocation must be independently
verified.

Terminal classification does not erase secondary facts. For example, a
cancelled Attempt can retain `cleanup_status: FAILED`, and a timed-out Attempt
can retain an observed non-zero exit. A computation that otherwise succeeded
but fails result validation, output bounds, or required cleanup terminalizes as
`FAILED`, with the computation outcome retained separately. Requested
assurance is evaluated only after terminalization; an unmet request makes the
result ineligible and the Job `FAILED` without rewriting the Attempt.

## Retry and resume

The Execution Specification is the only source of retry authority. Its retry
policy declares:

- `max_attempts`, including the first Attempt;
- the exact retryable Attempt terminal states and reason codes;
- deterministic fixed or bounded exponential backoff without random hidden
  state;
- whether an explicit immutable resume identity is permitted; and
- whether every declared external side effect is idempotent and fence-aware.

`backoff_ordinal` equals the preceding Attempt's positive retry ordinal. With
`t` equal to that Attempt terminal event's durable `recorded_at`, retry timing
is exactly:

```text
NONE:        eligible_due_at = t
FIXED:       eligible_due_at = t + backoff_base_seconds
EXPONENTIAL: eligible_due_at =
               t + min(backoff_cap_seconds,
                       backoff_base_seconds * 2^(backoff_ordinal - 1))
```

Arithmetic is checked before `job.retry_scheduled`; overflow or an
unrepresentable UTC result prevents retry and latches `RETRY_EXHAUSTED`.
There is no random jitter, process-local seed, or restart-relative delay.

`CANCELLED`, `POLICY_VIOLATION`, `REJECTED` due to an invalid contract or
approval, forged identity or Sigil, stale Snapshot, and any unknown failure are
never retryable. `FAILED`, `TIMED_OUT`, `LEASE_EXPIRED`, `LOST`, or `FENCED`
are retryable only when both the exact reason code and policy allow them.
Cleanup ambiguity can retry only into completely new mutable resources; it
never authorizes reuse.

Retry requires all of the following:

1. the preceding Attempt is terminal and preserved;
2. no cancellation, Job timeout, policy violation, or fatal integrity event is
   active;
3. the preceding Attempt's budget settlement and assurance evaluation are
   durable, and a complete next-Attempt reservation fits;
4. Task, Capability, Execution Specification, approval, Snapshot freshness,
   backend eligibility, and requested assurance preflight revalidate;
5. a new Attempt ID, next ordinal, higher fencing generation, and new mutable
   resource identities are allocated; when its immutable authorization
   requirement is `REQUIRED`, a fresh deterministic Attempt subject and
   distinct valid Receipt bind exactly once before preflight; this binding
   cannot reuse the predecessor or Specification approval; a new Lease ID and
   Worker authority follow only if preflight passes; and
6. `job.retry_scheduled`, `job.retry_ready`, and the atomic
   `job.attempt_allocated` event commit in order before materialization or
   Worker launch.

The default is a fresh Crucible from the pinned immutable base and inputs.
Resume is permitted at A1 or higher only when the Specification explicitly
allows it and a content-identified immutable resume source validates. The
Executor must prove the predecessor's process tree and handles are fenced,
validate every resumed byte against the resume identity, allocate a new
mutable materialization and output namespace, and record lineage to the prior
Attempt. A mutable directory, path, container name, or surviving process is
never a resume identity.

Retry does not merge logs, outputs, metrics, or results. The Job projection
lists every Attempt. Only one terminal Attempt can supply the selected result
candidate for the later Job assurance and Outcome decision, while every
preceding failure remains inspectable.

### Job aggregate budget ledger

The Job budget is enforced by a replayed
`{limit, reserved, consumed}` ledger for every aggregate dimension. Worker
reports and heartbeats are never trusted accounting. The enforcement backend
or Executor supervisor measures counters outside the Worker and binds each
measurement to the Attempt, process-tree identity, backend-configuration
Sigil, interval, and evidence Sigil.

`budget_reservation` has exactly `attempts`, `cpu_time_seconds`,
`storage_bytes_written`, `output_bytes`, `log_bytes`, `process_starts`,
`network_egress_bytes`, and `network_requests`. For v1,
`job.attempt_allocated` reserves `attempts: 1` and the full corresponding
Execution Specification `attempt_budget` ceiling for every other dimension.
Allocation is illegal unless, for every dimension:

```text
consumed + reserved + requested_reservation <= limit
```

All ledger arithmetic is checked unsigned arithmetic. Overflow fails closed
before mutation and is never treated as remaining capacity.

The event atomically adds the reservation, creates the Attempt, and stores the
same reservation and exact derived `attempt_authorization_requirement` in its
immutable binding. Replay initializes the orthogonal authorization state to
`NONE` or `PENDING` in that same event. No authorization subject,
materialization, process start, or later retry scheduling may precede that
commit. `peak_memory_bytes` remains a per-Attempt instantaneous ceiling
enforced by the supervisor and is not summed in the Job ledger.

While the Attempt is `CLEANING`, after all measured activity has stopped, the
Executor commits the one `ACCOUNTING_CAPTURED` progress event described
above. After the terminal Attempt event, `job.budget_settled` commits exactly
once before retry scheduling or Job terminalization. Its closed payload
contains the Attempt ID, reservation, accounting-capture event ID and Sigil,
`usage_status`, exact per-dimension `measured`, exact per-dimension `charged`,
accounting interval, supervisor identity, complete accounting-evidence-set
Sigil, and resulting ledger Sigil.
`usage_status` is `MEASURED`, `PARTIAL`, or `UNAVAILABLE`. A verified measured
dimension is charged its measured value and releases the unused reservation.
Each missing, discontinuous, corrupt, or Worker-only dimension is charged its
full reservation. `UNAVAILABLE` therefore charges every reserved dimension in
full. Attempt-count charge is always one.

Exceeding an enforced reservation is a policy violation and cannot be hidden
by settlement. A crash between Attempt terminalization and settlement resumes
that exact settlement; if trusted counters cannot be reconstructed, it
charges the full preserved reservation. A reservation is never silently
released, transferred to another Attempt, or recomputed under a changed
Specification. Retry eligibility is decided only from the post-settlement
ledger and requires another full reservation. This makes retry count and
aggregate resource use deterministic under replay.

## Logs and bounded result transport

The Executor creates separate ordered streams for `STDOUT`, `STDERR`, and
`STRUCTURED`. The Worker cannot select an arbitrary Host path as a log sink.
`execution-log-chunk/1.0` has exactly these required members:

| Field group | Exact fields |
| --- | --- |
| Contract and identity | `schema_version`, `chunk_id`, `log_stream_id`, `job_id`, `attempt_id`, `lease_id`, `worker_id`, `worker_session_id`, `executor_epoch`. |
| Immutable bindings | `attempt_binding_sigil`, `lease_binding_sigil`, `worker_session_binding_sigil`, `fence_tuple`. |
| Stream position | `stream`, `sequence`; `stream` is `STDOUT`, `STDERR`, or `STRUCTURED`, and sequence is zero-based and local to that stream. |
| Content | `byte_length`, `media_type`, `encoding`, `blob_sigil`, `staging_reference`. |
| Timing and boundaries | `observed_at`, `received_at`, `split_utf8_boundary`, `split_line`. |
| Integrity | `chunk_record_sigil`. |

There are no conditional members. Boundary flags remain present for binary
encodings and are `false`; the staging reference is a closed
Executor-generated opaque value, never a Host path.

The staging reference is operational and confers no read or write authority.
RFC-0013 defines durable Blob and Replica storage. Until then, the `0.4`
runtime may use a local content-addressed execution spool outside the Worker,
with atomic write-before-event publication and the complete `.benchwork/`
tree unreachable from an A2 Worker.

Chunk sequence and content identity are validated before journal commitment.
An exact repeated sequence and Blob Sigil is idempotent. Conflicting content at
the same sequence, a stale fence, a chunk after stream closure, an unexpected
stream, or an oversized chunk is rejected and recorded. Partial writes remain
quarantined and absent from the committed stream.

Per-stream and aggregate byte limits are enforced outside the Worker. On
limit:

- the Executor appends `log.truncated` exactly once with captured and dropped
  byte counts;
- further bytes are drained or discarded without unbounded buffering;
- overflow behavior follows the closed Specification enum `TRUNCATE` or
  `TERMINATE`;
- truncation remains visible in result and assurance evidence; and
- redaction is never treated as secret non-inheritance or containment.

Log timestamps and text are untrusted observations. Logs cannot change
lifecycle state, issue commands, prove policy enforcement, or become canonical
Artifacts without explicit Athanor acceptance under RFC-0013 and RFC-0015.

`execution-result/1.0` has exactly these required members:

| Field group | Exact fields |
| --- | --- |
| Contract and identity | `schema_version`, `job_id`, `attempt_id`, `lease_id`, `worker_id`, `worker_session_id`, `executor_epoch`. |
| Immutable bindings | `job_binding_sigil`, `attempt_binding_sigil`, `lease_binding_sigil`, `worker_session_binding_sigil`, `fence_tuple`. |
| Worker outcome | `worker_outcome`, whose enum is exactly `COMPLETED` or `FAILED`. |
| Process observation | `termination_observation`, a closed union described below. |
| Runtime observation | `runtime_observation`, exactly `started_at`, `ended_at`, `cpu_time_seconds`, `peak_memory_bytes`, `process_count`, and `observation_evidence_sigil`. |
| Logs | `log_stream_summaries`, exactly one closed entry for each configured stream sorted by stream enum, and `log_set_sigil`. |
| Outputs | `outputs`, an array of at most 4,096 unique entries sorted by `(logical_name unsigned ASCII, blob_sigil)`; every entry has exactly `logical_name`, `schema_id`, `schema_sigil`, `staging_reference`, `byte_size`, and `blob_sigil`. |
| Diagnostics | Bounded closed arrays `diagnostics` and `limitations`. |
| Integrity | `result_sigil`. |

Each output `staging_reference` is the closed
`ATTEMPT_OUTPUT {kind, storage_subject_id, output_handle_id, transfer_id,
transfer_attempt_id}` branch. The Executor preallocates the RFC-0013
`ST-ID`/`SA-ID` pair and unguessable handle before exposing it to the current
Lease. The stable subject ID is fixed at the same time as
`Sigil(["execution-attempt-output-storage-subject-id/1.0", job_id,
attempt_id, output_handle_id])`; it does not depend on bytes that do not yet
exist. The later ESM entry and RFC-0013 TransferRef must use the same subject,
handle, and transfer IDs. No path, URL, backend locator, Replica ID, or prior
Attempt handle is a legal branch.

`termination_observation.kind` is `EXITED`, `SIGNALED`, or `UNKNOWN`.
`EXITED` requires `exit_code` and forbids `signal`; `SIGNALED` requires
`signal` and forbids `exit_code`; `UNKNOWN` forbids both. Every branch also
requires `observed_at` and `observation_source`. There are no other
conditional result members.

The Worker never writes a realized assurance claim. While authority is
current, the Executor accepts at most one result Sigil for an Attempt, commits
its accepted or rejected disposition before `attempt.draining`, and preserves
the disposition sequence.
An exact duplicate returns that disposition without an event. A conflicting
second result is a protocol violation. A missing, late, stale, malformed,
over-limit, wrong-Schema, wrong-path, wrong-Sigil, or wrong-fence result is
retained as rejected operational evidence and cannot be selected by the Job.

Outputs are staged atomically with respect to their recorded byte identity.
Existence, process exit zero, Worker `COMPLETED`, Attempt `SUCCEEDED`, or Job
`SUCCEEDED` does not register an Artifact, create a scientific Run, or append a
Chronicle event. The result remains an execution Proposal until RFC-0015's
typed acceptance path invokes Athanor and Athanor independently validates it.

### Execution storage-root manifest

`execution-storage-root-manifest/1.0` is the only source document from which
an RFC-0012 execution Reference Set may be extracted. It freezes the complete
typed subject-to-storage closure before a root can become visible. Its closed
top-level object has exactly:

| Field | Exact v1 value |
| --- | --- |
| `schema_version` | Constant `execution-storage-root-manifest/1.0`. |
| `manifest_id` | Deterministic `ESM-ID` below. |
| `root_kind` | `JOB_INPUT`, `ATTEMPT_INPUT`, or `ATTEMPT_OUTPUT`. |
| `job_id`, `attempt_id` | Exact owner IDs; Attempt ID is null only for `JOB_INPUT`. |
| `owner_binding` | The one closed owner branch below. |
| `entries` | Complete sorted array of zero to 4,096 `StorageRootEntry` values. |
| `blob_refs` | Sorted unique projection of every committed managed Blob in `entries`, zero to 4,096 RFC-0013 `BlobRef` values. |
| `protection_plan` | Closed `NONE` or `PLANNED` branch below. |
| `created_at` | Time fixed by first single-assignment creation. |
| `manifest_sigil` | Sigil over every other top-level field. |

The owner branches are exact:

| `root_kind` | Exact `owner_binding` fields |
| --- | --- |
| `JOB_INPUT` | `kind`, `start_request_sigil`, `task_id`, `task_capsule_sigil`, `specification_id`, `specification_sigil`, `input_set_sigil`. |
| `ATTEMPT_INPUT` | `kind`, `job_binding_sigil`, `attempt_binding_sigil`, `preflight_plan_sigil`, `materialization_id`, `materialization_record_sigil`, `input_set_sigil`. |
| `ATTEMPT_OUTPUT` | `kind`, `job_binding_sigil`, `attempt_binding_sigil`, `result_binding`, `log_set_sigil`, `output_set_sigil`, `control_evidence_set_binding`, `terminal_source_binding`, `quarantine_plan_sigil`. |

Every owner field resolves the exact immutable record or execution-journal
binding named by the owner. An `ATTEMPT_OUTPUT` manifest is created only after
the ten-record control-evidence closure and terminal-source disposition are
durable, and before `ACCOUNTING_CAPTURED`; it never refers to the later QBS,
OS, Attempt-terminal event, or Outcome.

Each `StorageRootEntry` has exactly `storage_subject_id`, `subject`,
`claimed_blob`, `storage_origin`, and `entry_sigil`. The self-Sigil covers the
other four fields. For every branch except `ATTEMPT_OUTPUT`,
`storage_subject_id` is the lowercase Sigil of
`["execution-storage-subject-id/1.0", root_kind, job_id, attempt_id,
subject]`. For `ATTEMPT_OUTPUT`, it is the preallocated Result
staging-reference value derived from the opaque output handle by the formula
above, and `staging_reference_sigil` resolves that complete branch. It is a
stable identity, not a path or backend locator. `subject` is exactly one of:

| Entry subject | Exact fields |
| --- | --- |
| `JOB_INPUT` | `kind`, `input_ordinal`, `input_identity`, `input_sigil`. |
| `ATTEMPT_INPUT` | `kind`, `input_ordinal`, `input_identity`, `input_sigil`, `materialization_id`. |
| `ATTEMPT_OUTPUT` | `kind`, `logical_name`, `schema_id`, `schema_sigil`, `staging_reference_sigil`, `byte_size`, `blob_sigil`. |
| `LOG_STREAM` | `kind`, `stream`, `log_stream_id`, `stream_set_sigil`, `byte_size`, `blob_sigil`. |
| `RESOURCE_EVIDENCE` | `kind`, `control_evidence_id`, `control_evidence_sigil`, `control_dimension`, `phase`, `phase_evidence_entry_sigil`, `byte_size`, `blob_sigil`. |
| `TERMINAL_SOURCE` | `kind`, `disposition`, `terminal_source_identity`, `terminal_source_sigil`, `storage_blob`, `retention_policy_sigil`, `file_count`, `byte_count`. |

The arrays are grouped in this table order and then sorted by the natural
immutable key already defined for that subject family; input ordinals are
contiguous from zero. Subjects and `storage_subject_id` values are unique.
The manifest contains every Job input or Attempt input in its bound input set.
For `ATTEMPT_OUTPUT` it contains every accepted output, all three closed Log
streams, every Blob-bearing entry reachable through the frozen CES, and the
non-null terminal source. Nothing may be omitted to meet the bound.

`claimed_blob` is an RFC-0013 `BlobRef` or null. It is non-null and equals the
subject's Blob identity and byte size for `COMMITTED_BLOB` or `QUARANTINE`;
it is null exactly for `NOT_STORED`. The `storage_origin` union is:

| Origin | Exact fields and rule |
| --- | --- |
| `COMMITTED_BLOB` | `kind`, `transfer`, `provenance_id`, `provenance_sigil`, `blob_record_sigil`, `terminal_event`; `transfer` is the exact RFC-0013 `TransferRef`, the provenance record is `CAPTURED` or `IMPORTED` as appropriate and names that same transfer and Blob, and `terminal_event` equals `transfer.terminal_event`. |
| `QUARANTINE` | `kind`, `transfer`, `provenance_id`, `provenance_sigil`, `quarantine_id`, `quarantine_origin_event`; the transfer attempt and Quarantine owner are identical and the provenance preserves that same attempted ingest. |
| `NOT_STORED` | `kind`, `transfer`, `terminal_reason`, `evidence_sigil`; `transfer` is the exact failed `TransferRef` or null only when no transfer was started, and the reason proves why no managed Blob or retained Quarantine exists. |

For an `ATTEMPT_OUTPUT` subject, every non-null transfer is the current
Attempt's transfer, not merely the creator of a deduplicated Replica. Its
request has `direction: INGEST`, `purpose: ATTEMPT_OUTPUT`,
`source.kind: ATTEMPT_OUTPUT`, `destination.kind: MANAGED_BACKEND`, and
`execution.kind: LEASED`. The source and top-level execution objects equal
each other and the exact execution-journal ID, Executor epoch, Job, Attempt,
Lease, Worker, Worker Session, and public fence tuple that authorized the
output. `source.output_handle_id` equals the Result staging-reference
`output_handle_id`; that branch also carries this `storage_subject_id` and
the same Transfer ID/Attempt ID, and its Sigil equals
`subject.staging_reference_sigil`. Expected Blob,
exact byte bound, selected backend, committed Blob, transfer terminal Event,
and provenance Blob all equal `claimed_blob`. A pre-existing Blob or Replica
may satisfy the bytes, but the current TransferRef and current provenance
remain mandatory; an older Replica's creator cannot impersonate this
Attempt.

`blob_refs` equals every and only `claimed_blob` whose origin is
`COMMITTED_BLOB`, sorted by `(blob_sigil, size_bytes)` and de-duplicated by
the complete pair. A Quarantine entry is protected by its exact isolated
Quarantine lifecycle rather than by pretending it is a registered Blob; a
negative entry creates no Blob edge.

`protection_plan` is `NONE {kind}` exactly when `blob_refs` is empty.
Otherwise it is
`PLANNED {kind, reference_set_registration_event_id, hold_id,
hold_set_event_id, policy_id, policy_sigil, hold_lifetime}`.
The registration Event ID is the deterministic RFC-0013 `SE-ID` below; the
hold and hold-set Event IDs are freshly preallocated RFC-0013 `SH-ID` and
`SE-ID` values. All three become the exact later registration or hold
identities:

```text
reference_set_registration_event_id =
  "SE-" + UPPER_HEX(SHA256(canonical_json(
    ["artifact-storage-execution-root-reference-set-registration-event-id/1.0",
     manifest_id])))
```

`policy_id` is constant `SP-EXECUTION-ROOT-HOLD-V1`, and `policy_sigil`
resolves the one installed project-scoped RFC-0013 neutral operational policy
with that ID. This tuple is mandatory for every non-empty root, including a
`NONE`-mode output root. It is independent of, and cannot substitute for, the
user-selected `CODE_MODIFICATION` terminal-source retention policy.
`hold_lifetime` is:

- `OWNER_TERMINAL {kind}` for `JOB_INPUT` or `ATTEMPT_INPUT`; or
- `OUTPUT_RETENTION {kind, maximum_duration_seconds}` for
  `ATTEMPT_OUTPUT`, where the duration equals the bound Specification's
  `retention_duration_seconds` for `CODE_MODIFICATION` and is zero for
  `NONE`.

The plan intentionally contains no future Reference Set ID/Sigil, Storage
Event Sigil, or hold-set Event Sigil. After the complete ESM is durable,
RFC-0013 deterministically derives the Reference Set from the ESM source; a
future Sigil inside this self-Sigiled record would create a hash cycle.

The manifest ID is:

```text
manifest_id =
  "ESM-" + UPPER_HEX(SHA256(canonical_json(
    ["execution-storage-root-manifest-id/1.0",
     root_kind, job_id, attempt_id, owner_binding])))
```

There is at most one ESM per owner and root kind. The resolver is
single-assignment by ESM-ID: first creation fixes all entries, the protection
plan, `created_at`, and self-Sigil; an exact retry reuses it, while any second
byte sequence for that ID is an integrity failure. The ESM is durable before
Reference Set registration, so a crash can resolve the exact source without
enumerating files, transfers, Replicas, or current State.

Its RFC-0013 Reference Set source is exactly
`{kind: OPERATIONAL_CONTROL_RECORD, identity: manifest_id,
schema_version: execution-storage-root-manifest/1.0,
sigil: manifest_sigil}`. The extractor is the installed constant
`{extractor_id: benchwork.execution-storage-root-manifest,
extractor_version: 1.0, extractor_sigil}` and the validator is the installed
constant `{validator_id: benchwork.execution-storage-root-manifest,
validator_version: 1.0, validator_sigil, source_validation_sigil,
evidence_sigils}`. Their Sigils are computed from their complete closed
profiles by these fixed formulas:

```text
extractor_sigil =
  Sigil(["execution-storage-root-extractor-profile/1.0",
         "benchwork.execution-storage-root-manifest", "1.0"])

validator_sigil =
  Sigil(["execution-storage-root-validator-profile/1.0",
         "benchwork.execution-storage-root-manifest", "1.0"])
```

`evidence_sigils` is computed first. It is the sorted unique union of
`manifest_sigil`; every Sigil-typed leaf in `owner_binding`; every
`entry_sigil` and Sigil-typed leaf in each entry's `subject`; the planned
`policy_sigil`; and, for each entry, the Sigils present in its closed
storage-origin branch: the Transfer request and Attempt record Sigils plus
terminal Event Sigil for every non-null `TransferRef`; the provenance Sigil
and Blob-record Sigil for `COMMITTED_BLOB`; the provenance Sigil and
quarantine-origin Event Sigil for `QUARANTINE`; or the negative
`evidence_sigil` for `NOT_STORED`. It contains no Reference Set Sigil,
registration Event Sigil, hold authorization, hold-set Event Sigil, EHR, or
release Event Sigil. A missing, extra, duplicated, or differently ordered
evidence value is invalid.

The source-validation value is then exactly:

```text
source_validation_sigil =
  Sigil(["execution-storage-root-source-validation/1.0",
         manifest_id,
         manifest_sigil,
         extractor_sigil,
         validator_sigil,
         [[entry.storage_subject_id, entry.entry_sigil], ...],
         blob_refs,
         evidence_sigils])
```

The entry pairs preserve ESM order. `evidence_sigils` is the sorted unique
projection just defined. The extractor emits exactly one Blob edge for each
`blob_refs` member: `JOB_INPUT` uses
`JOB_REQUIRES_BLOB`, while both Attempt kinds use
`CONTROL_RETAINS_BLOB`. No other edge is legal.

When `protection_plan` is `PLANNED`, Storage registers that exact set at
`reference_set_registration_event_id`, then appends
`retention.hold_set` at `hold_set_event_id`. The hold uses the planned
`hold_id`, policy tuple, `target_kind: REFERENCE_SET`, and
`target_id` equal to the newly derived Reference Set ID. Its
`authorization_sigil` is exactly:

```text
Sigil(["execution-root-hold-set-authorization/1.0",
       {manifest_id, manifest_sigil},
       {reference_set_id, reference_set_sigil,
        registration_event: <exact RFC-0013 EventRef>},
       {hold_id, hold_set_event_id},
       {policy_id, policy_sigil}])
```

Every member equals the ESM, registered Reference Set, registration Event, and
plan byte-for-byte. The formula is evaluated only after registration and is
therefore intentionally outside the ESM. The closed
`storage_root_binding` then adds `storage_root_manifest_id` and
`storage_root_manifest_sigil` to the exact RFC-0013 root fields and must
resolve this ESM, set, active hold, its exact set-authorization Sigil, and both
planned Event IDs. When the plan is `NONE`, no Reference Set, hold, or visible
execution root is fabricated.

`terminalization_storage_manifest_binding` is
`PENDING {kind}` before the output ESM exists or
`FROZEN {kind, storage_root_manifest_id, storage_root_manifest_sigil}`
afterward. `output_root_protection` is `PENDING {kind}` before capture, then
exactly
`NO_HOLD {kind, terminalization_storage_manifest_binding}` when the frozen
ESM has no Blob refs, or
`HELD {kind, terminalization_storage_manifest_binding,
storage_root_binding}` when its active Reference-Set hold is durable. These
two bindings are frozen before `ACCOUNTING_CAPTURED`.

### Execution-root hold-release authorization

`execution-root-hold-release-authorization/1.0` is the only authority that
may release a hold created from an execution ESM. Its closed top-level object
has exactly `schema_version`, `release_authorization_id`,
`execution_journal_id`, `storage_root`, `policy`,
`hold_set_authorization_sigil`, `basis`, and
`release_authorization_sigil`. `storage_root` is the complete closed
`storage_root_binding` above. `policy` has exactly `policy_id` and
`policy_sigil`, byte-for-byte equal to the ESM plan and resolved hold.
`hold_set_authorization_sigil` is the exact set-authorization value above.

The `basis` union is exactly:

```text
OWNER_TERMINAL:
  kind = OWNER_TERMINAL
  activation_event_id: JE-ID
  activation_event_sequence: PositiveU63
  activation_event_sigil: Sigil
  terminal_event_id: JE-ID
  terminal_event_sequence: PositiveU63
  terminal_event_sigil: Sigil
  terminal_event_type: closed execution Event type
  verification_head: complete execution-journal-head/1.0
  verification_state_sigil: Sigil

ORPHAN_ABORT:
  kind = ORPHAN_ABORT
  intended_activation_event_type: closed execution Event type
  absence_head: complete execution-journal-head/1.0
  absence_state_sigil: Sigil

OUTPUT_DEADLINE:
  kind = OUTPUT_DEADLINE
  activation_event_id: JE-ID
  activation_event_sequence: PositiveU63
  activation_event_sigil: Sigil
  release_schedule: complete output_hold_release_schedules entry
  terminal_event_sequence: PositiveU63
  terminal_event_sigil: Sigil
  verification_head: complete execution-journal-head/1.0
  verification_state_sigil: Sigil
```

Its deterministic identity and self-Sigil are:

```text
release_authorization_id =
  "EHR-" + UPPER_HEX(SHA256(canonical_json(
    ["execution-root-hold-release-authorization-id/1.0",
     storage_root.hold_id])))

release_authorization_sigil =
  Sigil(<complete authorization with only
         release_authorization_sigil omitted>)
```

The resolver is immutable and single-assignment by `EHR-ID`; the first legal
basis for a hold wins and changed bytes are an integrity conflict.
Construction, Storage release, and any execution-journal observation occur
under the outer gate. The authorization is durable before
`retention.hold_released`. A crash resolves the same EHR record and existing
Storage Event or appends only the missing release.

`OWNER_TERMINAL` is legal only for `JOB_INPUT` with its exact parent Job
terminal Event, or `ATTEMPT_INPUT` with its exact owner Attempt terminal
Event. The Event ID, Sigil, type, owner IDs, and activated
`storage_root_binding` all come from replay through `verification_head`; the
activation fields identify the sole activation Event and the terminal fields
identify its sole inactivation Event in that same prefix, the Head ends at or
after the terminal sequence, and `verification_state_sigil` equals the State
projected through that exact Head.
`OUTPUT_DEADLINE` is legal only for `ATTEMPT_OUTPUT`; its schedule is
byte-for-byte one entry from the exact parent Job terminal Event, its
`terminal_event_sigil` names that Event, the activation fields identify the
owner Attempt terminal Event, both occur in order in the complete replay
through `verification_head`, `verification_state_sigil` equals that prefix's
State, and trusted time is at or after the schedule's immutable due predicate
under the rules below.

`ORPHAN_ABORT` is legal only when its complete, self-Sigiled
`absence_head` is the gate-held current verified Execution Journal Head and
`absence_state_sigil` equals the State projected through it; replay through
that Head proves that the sole activating Event for the exact ESM/root did not
commit. The intended activation type is `job.submitted` for
`JOB_INPUT`, `attempt.preflight_passed` for `ATTEMPT_INPUT`, or the exact
planned Attempt terminal type for `ATTEMPT_OUTPUT`. Once an `ORPHAN_ABORT`
EHR exists, that ESM/root is permanently activation-ineligible; retry may
finish its release but may not install a fresh hold or later activate it.
New work requires a new Job or Attempt identity.

Before any sole activating Event commits, replay must resolve the planned hold
as `ACTIVE` and prove that no EHR exists for its deterministic
`release_authorization_id`. Missing or ambiguous proof blocks activation.
This rule closes the race between orphan proof and a late activation. None of
the three bases authorizes byte deletion, another hold, or a canonical,
policy, legal, or preservation reference.

### Closed terminalization input sets

`execution-control-evidence-set/1.0` is the only v1 closure of the individual
`execution-control-evidence/1.0` records used to terminalize one Attempt. Its
conventional Schema filename is
`execution-control-evidence-set-1.0.json` and its exact `$id` is
`https://benchwork.dev/schemas/execution-control-evidence-set/1.0`.
The closed top-level object has exactly:

| Field | Exact v1 value |
| --- | --- |
| `schema_version` | Constant `execution-control-evidence-set/1.0`. |
| `control_evidence_set_id` | The deterministic `CES-ID` below. |
| `job_id`, `attempt_id`, `attempt_binding_sigil` | Exact immutable owner bindings. |
| `control_evidence_refs` | Exactly ten closed references, one per control dimension. |
| `control_evidence_set_sigil` | Sigil over every other top-level member. |

Each `control_evidence_refs` member has exactly `control_dimension`,
`control_evidence_id`, and `control_evidence_sigil`. The array has exactly ten
members in the control-dimension matrix order printed below. Its dimensions
and IDs are both unique. Each pair resolves one complete
`execution-control-evidence/1.0` document whose Job, Attempt, dimension, ID,
and self-Sigil equal the reference byte-for-byte. The ten resolved documents
are the complete evidence family for the Attempt: a document outside this
closure cannot satisfy assurance, create a resource-evidence observation, or
replace a missing dimension.

Within every resolved document, each of the four `phase_evidence` arrays is
unique by canonical JSON and sorted by
`(evidence_kind enum order, producer_identity unsigned ASCII,
verifier_identity unsigned ASCII, collected_at, blob_sigil null first,
staging_reference canonical JSON)`. The derived
`phase_evidence_entry_sigil` is the Sigil of that exact closed entry; it is
not a new field in `execution-control-evidence/1.0`. This gives every
Blob-bearing entry a stable, independently recomputable identity.

`control_evidence_set_id` is `CES-` followed by the uppercase 64-hex SHA-256
digest of canonical JSON:

```text
["execution-control-evidence-set-id/1.0",
 job_id,
 attempt_id,
 attempt_binding_sigil]
```

`control_evidence_set_binding` is exactly
`PENDING {kind}` or
`FROZEN {kind, control_evidence_set_id, control_evidence_set_sigil}`.
The ten evidence documents and set document are durable before the final
`ACCOUNTING_CAPTURED` progress event; that event carries only the `FROZEN`
branch. One deterministic, single-assignment pending resolver slot exists per
Attempt. It is addressable by the `CES-ID` only while replay has the Attempt
in `CLEANING`, no `ACCOUNTING_CAPTURED` event exists, and the owner binding
matches. Once written, it returns the one self-Sigil and complete canonical
set document. The event and every later consumer use the exact ID-and-Sigil
pair; ID-only lookup, Sigil-only lookup, enumeration, and substitution of a
newer evidence family are invalid. A crash after record durability but before
the event reuses the same record; a different self-Sigil for that ID is an
integrity failure. There are at most `MAX_ATTEMPTS` 4,096 such records.

`execution-quarantine-binding-set/1.0` is the only v1 complete mapping from
an execution subject to an RFC-0013 Quarantine item, including retained and
terminal-negative outcomes. Its conventional Schema
filename is `execution-quarantine-binding-set-1.0.json` and its exact `$id`
is
`https://benchwork.dev/schemas/execution-quarantine-binding-set/1.0`.
The closed top-level object has exactly:

| Field | Exact v1 value |
| --- | --- |
| `schema_version` | Constant `execution-quarantine-binding-set/1.0`. |
| `quarantine_binding_set_id` | The deterministic `QBS-ID` below. |
| `job_id`, `attempt_id`, `attempt_binding_sigil` | Exact immutable owner bindings. |
| `quarantine_plan_sigil` | Exact plan frozen by `attempt.cleaning`. |
| `terminalization_storage_manifest_binding` | Exact frozen output ESM ID and Sigil prepared before accounting capture. |
| `storage_event` | Exact RFC-0013 `EventRef` at the final pre-accounting Storage prefix. |
| `storage_state_sigil` | Sigil of the complete RFC-0013 State replayed through `storage_event`. |
| `bindings` | Complete sorted subject-to-Quarantine bindings; empty when no subject is quarantined. |
| `quarantine_binding_set_sigil` | Sigil over every other top-level member. |

Every `bindings` member has exactly `storage_subject_id`,
`manifest_entry_sigil`, `subject`, `storage_origin`, `quarantine_ref`,
`disposition`, and `quarantine_binding_sigil`, whose self-Sigil covers every
other field. The first two fields select exactly one entry in the frozen ESM;
`subject` and `storage_origin` equal that entry byte-for-byte.
`quarantine_ref` has exactly `quarantine_id`, `owner_kind`, `owner_id`,
`quarantine_record_sigil`, `origin_event`, `observation_event`, `state`,
`source_object`, `destination_object`, `source_cleanup`, and `reason`. It
imports the RFC-0013 `SQ-ID`, owner domains, State fields, and complete
`EventRef` without restatement. `subject` is exactly one of these closed
branches:

| Subject branch | Exact fields |
| --- | --- |
| `ATTEMPT_OUTPUT` | `kind`, `logical_name`, `schema_id`, `schema_sigil`, `staging_reference_sigil`, `byte_size`, `blob_sigil`. |
| `LOG_STREAM` | `kind`, `stream`, `log_stream_id`, `stream_set_sigil`, `byte_size`, `blob_sigil`. |
| `RESOURCE_EVIDENCE` | `kind`, `control_evidence_id`, `control_evidence_sigil`, `control_dimension`, `phase`, `phase_evidence_entry_sigil`, `byte_size`, `blob_sigil`. |
| `TERMINAL_SOURCE` | `kind`, `disposition`, `terminal_source_identity`, `terminal_source_sigil`, `storage_blob`, `retention_policy_sigil`, `file_count`, `byte_count`. |

The branch order above is the primary sort key. Remaining sort keys are,
respectively, the output member key, Log stream enum order, the resource
member key plus phase-entry Sigil, and terminal-source Sigil, all compared by
unsigned ASCII where not already an enum or integer. Subjects and Quarantine
IDs are unique. The array has at most 4,096 members.

The set is derived after all cleanup and storage work is complete from exactly
the accepted Result outputs, three closed Log streams, every Blob-bearing
entry reached through the frozen control-evidence set, and the frozen
terminal-source binding. While holding the RFC-0013 outer gate, the Executor
replays one complete Storage prefix and binds its exact EventRef and State
Sigil before constructing the set. It contains one binding if and only if
that ESM entry has `storage_origin: QUARANTINE`, including both retained and
terminal-negative outcomes. `storage_origin.transfer.transfer_attempt_id`
equals `quarantine_ref.owner_id`, whose owner kind is
`TRANSFER_ATTEMPT`; this is always the current execution transfer fixed by
the ESM. The subject copies the source fields byte-for-byte.

`origin_event` is exactly `quarantine.recorded` or `quarantine.failed`.
For both origins, the owning RFC-0013 Transfer Attempt terminal Event is
exactly `transfer.quarantined`, names this Q-ID, carries
`quarantine_event == origin_event`, and equals
`storage_origin.transfer.terminal_event`. A `transfer.failed` terminal Event
is legal only for `NOT_STORED`, never for an ESM `QUARANTINE` origin.
`observation_event` is the exact last Event that produced the frozen State and
is equal to or later than `origin_event`. `INTENT_RECORDED`, `INSPECTING`, or
`DISPOSING` is not terminal and blocks `ACCOUNTING_CAPTURED`.

The origin-and-state matrix is closed:

| Origin Event | Frozen State | Exact disposition |
| --- | --- | --- |
| `quarantine.recorded` | `HELD` | `RETAINED` |
| `quarantine.recorded` | `DISPOSAL_FAILED` | `RETAINED` |
| `quarantine.recorded` | `DISPOSED` | `TERMINAL_NEGATIVE` |
| `quarantine.failed` | `FAILED` | `TERMINAL_NEGATIVE` |
| `quarantine.failed` | `DISPOSAL_FAILED` | `TERMINAL_NEGATIVE` |
| `quarantine.failed` | `DISPOSED` | `TERMINAL_NEGATIVE` |

Every other pair is invalid. `RETAINED` additionally requires the exact
`quarantine.recorded.verification` to authenticate the non-null destination
generation and the claimed Blob Sigil and size. For `DISPOSAL_FAILED`, the
exact observation Event and its failure evidence must also authenticate that
same destination generation as still present, isolated, and byte-identical at
the frozen prefix; missing or ambiguous presence blocks
`ACCOUNTING_CAPTURED`. Failed-origin
`DISPOSAL_FAILED` never acquires that verification and cannot become retained
content. `RETAINED` maps to the observation contract's `QUARANTINED` branch.
`TERMINAL_NEGATIVE` maps only to `QUARANTINE_TERMINAL_NEGATIVE`: it proves
unavailable, ineligible bytes and can never be relabeled retained Quarantine
or Blob. `source_object`, `destination_object`, cleanup, reason, record Sigil,
and both Events equal the exact frozen RFC-0013 projection. There is no
matching by Blob alone, size alone, pathname, filename, timestamp, or current
State enumeration.

`quarantine_binding_set_id` is `QBS-` followed by the uppercase 64-hex
SHA-256 digest of canonical JSON:

```text
["execution-quarantine-binding-set-id/1.0",
 job_id,
 attempt_id,
 attempt_binding_sigil,
 quarantine_plan_sigil,
 terminalization_storage_manifest_binding]
```

`quarantine_binding_set_binding` is exactly
`PENDING {kind}` or
`FROZEN {kind, quarantine_binding_set_id, quarantine_binding_set_sigil}`.
The set document is durable before the final `ACCOUNTING_CAPTURED` event,
which carries only the `FROZEN` branch. Its deterministic per-Attempt
single-assignment resolver has the same pre-event-only access, record-before-
event, exact-pair lookup, conflict, orphan-reuse, and 4,096-record rules as
the control-evidence-set resolver. An empty set is still a resolvable closed
record and is the only proof that the complete subject traversal found no
Quarantine binding. Recovery of a pending set replays its historical
`storage_event` and validates `storage_state_sigil`; it never refreshes the
set from a later Storage Head.

### Frozen output storage-observation set

`execution-output-storage-observation-set/1.0` is the only v1 document that
freezes terminal storage facts for an allocated Attempt. Its conventional
Schema filename is
`execution-output-storage-observation-set-1.0.json` and its exact `$id` is
`https://benchwork.dev/schemas/execution-output-storage-observation-set/1.0`.
The Schema is JSON Schema Draft 2020-12, every object and union branch is
closed, and every field below is required unless its branch explicitly
requires `null`.

The top-level object has exactly:

| Field | Exact v1 value |
| --- | --- |
| `schema_version` | Constant `execution-output-storage-observation-set/1.0`. |
| `observation_set_id` | The deterministic `OS-ID` below. |
| `job_id`, `attempt_id`, `attempt_binding_sigil` | Exact immutable owner bindings. |
| `result_binding` | The exact `execution-journal-event/1.0#/$defs/result_binding` branch frozen for the Attempt. |
| `log_closure_sigil`, `output_closure_sigil` | Exact non-null terminalization inputs. |
| `control_evidence_set_binding` | Exact frozen `CES-ID` and self-Sigil bound by `ACCOUNTING_CAPTURED`. |
| `quarantine_binding_set_binding` | Exact frozen `QBS-ID` and self-Sigil bound by `ACCOUNTING_CAPTURED`. |
| `terminalization_storage_manifest_binding` | Exact frozen output ESM ID and Sigil bound by `ACCOUNTING_CAPTURED`. |
| `output_root_protection` | Exact pre-terminal `NO_HOLD` or `HELD` protection branch bound by `ACCOUNTING_CAPTURED`. |
| `terminal_source_binding` | The exact `execution-journal-event/1.0#/$defs/terminal_source_binding` frozen by `attempt.cleaning`. |
| `storage_event` | Exact RFC-0013 `EventRef` at the observed Storage Journal prefix. |
| `storage_state_sigil` | Sigil of the complete RFC-0013 State replayed through `storage_event`. |
| `members` | The bounded, sorted, unique closed member union below. |
| `blob_sigils` | Sorted unique aggregate of every non-null Blob identity in `members`. |
| `observation_set_sigil` | Sigil over every other top-level member. |

`observation_set_id` is `OS-` followed by the uppercase 64-hex SHA-256 digest
of canonical JSON:

```text
["execution-output-storage-observation-set-id/1.0",
 job_id,
 attempt_id,
 attempt_binding_sigil,
 result_binding,
 log_closure_sigil,
 output_closure_sigil,
 control_evidence_set_binding,
 quarantine_binding_set_binding,
 terminalization_storage_manifest_binding,
 output_root_protection,
 terminal_source_binding]
```

This is one of the three terminalization-record deterministic-ID exceptions
for otherwise opaque execution IDs. It lets an interrupted pre-terminal
construction resolve the
same immutable record rather than enumerate files or guess a content hash.
Construction may use the deterministic ID to read the one single-assignment
pending resolver slot for that Attempt only when Execution Journal replay has
that Attempt in `CLEANING`, its `ACCOUNTING_CAPTURED` event is durable, and no
terminal event exists. The slot is created only after every ID input above is
immutable. Once present, it returns exactly one
`observation_set_sigil` and complete canonical document. A terminal event and
all later consumers resolve only the exact
`(observation_set_id, observation_set_sigil)` pair carried by the event. The
resolver rejects an unknown pair, a second Sigil for the same ID, or bytes
that do not validate both identities. The document is durable before the
Attempt terminal event that first references it. A record whose durable write
completed but whose event did not is a pending terminalization payload, not
an active root or terminal fact; Recovery reuses its frozen Storage prefix
even if the current Storage Head later advances.

`storage_event` imports RFC-0013 `EventRef` byte-for-byte and therefore has
exactly `journal_id`, `event_id`, `sequence`, and `event_sigil`.
`storage_state_sigil` equals the self-Sigil of the closed RFC-0013 State
obtained by replaying that same Journal through that Event. A document is
invalid if its Event is not at that sequence, the State has a different
Journal ID, applied count, last Event Sigil, or State Sigil, or a member is
resolved from a later State. A current State cache, backend listing, path,
filename, or retrieval time is never an observation input.
Both fields equal the resolved quarantine-binding-set document's
`storage_event` and `storage_state_sigil` byte-for-byte. That pre-accounting
prefix is the single storage fact boundary for the QBS and OS documents; OS
construction after `ACCOUNTING_CAPTURED` does not sample a second prefix.

Both terminalization-set bindings resolve their exact canonical documents
before any observation member is derived. Their Job, Attempt, and Attempt
binding equal this document byte-for-byte. The control-evidence set has
exactly ten valid resolvable evidence references; the quarantine-binding set
has the same `quarantine_plan_sigil` frozen for this Attempt and is complete
for the source traversal. Both the QBS and OS resolve the same exact output
ESM. `output_root_protection` proves either that this ESM has an empty
`blob_refs` set or that its exact Reference Set and active hold were durable
before accounting capture. A missing record, an ID/Sigil mismatch, a second
record for one deterministic ID, an unresolved member reference, or a
different owner invalidates the observation document.

`members` has `minItems: 6` and
`maxItems: MAX_OUTPUT_STORAGE_OBSERVATION_MEMBERS`, whose fixed value is
4,096. It uses exactly these closed branches:

| Member branch | Exact fields |
| --- | --- |
| `ATTEMPT_OUTPUTS_NONE` | `kind`, `reason`; reason is `NO_RESULT`, `RESULT_REJECTED`, or `OUTPUT_ARRAY_EMPTY`. |
| `ATTEMPT_OUTPUT` | `kind`, `storage_subject_id`, `manifest_entry_sigil`, `logical_name`, `schema_id`, `schema_sigil`, `staging_reference_sigil`, `byte_size`, `blob_sigil`, `storage_origin`, `storage`. |
| `LOG_STREAM` | `kind`, `storage_subject_id`, `manifest_entry_sigil`, `stream`, `log_stream_id`, `final_sequence`, `captured_bytes`, `dropped_bytes`, `truncated`, `stream_set_sigil`, `closure_event_id`, `closure_event_sigil`, `storage_origin`, `content`. |
| `RESOURCE_EVIDENCE_NONE` | `kind`. |
| `RESOURCE_EVIDENCE` | `kind`, `storage_subject_id`, `manifest_entry_sigil`, `control_evidence_id`, `control_evidence_sigil`, `control_dimension`, `phase`, `phase_evidence_entry_sigil`, `evidence_kind`, `producer_identity`, `verifier_identity`, `collected_at`, `byte_size`, `blob_sigil`, `storage_origin`, `storage`. |
| `TERMINAL_SOURCE_NOT_APPLICABLE` | `kind`. |
| `TERMINAL_SOURCE_NONE` | `kind`, `reason_codes`. |
| `TERMINAL_SOURCE` | `kind`, `storage_subject_id`, `manifest_entry_sigil`, `disposition`, `terminal_source_identity`, `terminal_source_sigil`, `storage_blob`, `retention_policy_sigil`, `file_count`, `byte_count`, `storage_origin`, `storage`. |

The executable Schema publishes these branches as the canonical named
`$defs` `attempt_outputs_none_member`, `attempt_output_member`,
`log_stream_member`, `resource_evidence_none_member`,
`resource_evidence_member`, `terminal_source_not_applicable_member`,
`terminal_source_none_member`, and `terminal_source_member`. It also
publishes `storage_observation`, `control_evidence_set_binding`, and
`quarantine_binding_set_binding`,
`terminalization_storage_manifest_binding`, and
`output_root_protection`. A consumer imports the exact
`https://benchwork.dev/schemas/execution-output-storage-observation-set/1.0#/$defs/<name>`
URI; a cloned or widened local branch is not equivalent.

Every named Sigil uses the common lowercase representation. Byte counts,
member counts, file counts, and non-null Log sequences use RFC-0013 `U63`;
`final_sequence` is `U63|null`, `truncated` is boolean, and
`collected_at` is the exact common UTC Timestamp. Job, Attempt, Log-stream,
control-evidence, and execution-Event IDs use their RFC-0012 domains.
All remaining identities use RFC-0013 bounded `Opaque`; no string exceeds 256
UTF-8 bytes or contains NUL or control characters. `staging_reference_sigil`
is the Sigil of the complete canonical staging-reference value and is not a
locator. `phase`, `control_dimension`, `evidence_kind`, `disposition`, and
terminal-source reason codes use only their already printed closed RFC-0012
enums. These are imported Schema definitions, not unconstrained local strings.

The kind value is the branch name. Member cardinality and order are closed:

1. the first group is either one `ATTEMPT_OUTPUTS_NONE` member or between one
   and 4,096 `ATTEMPT_OUTPUT` members, never both;
2. the next group is exactly three `LOG_STREAM` members in fixed
   `STDOUT`, `STDERR`, `STRUCTURED` order, with exactly the three immutable
   Log-stream IDs allocated to the Attempt;
3. the next group is either one `RESOURCE_EVIDENCE_NONE` member or between
   one and 4,096 `RESOURCE_EVIDENCE` members, never both; and
4. the final group is exactly one of the three terminal-source branches.

The 4,096-member maximum applies to the combined union, not independently to
each group. `blob_sigils` is the duplicate-free unsigned-ASCII-sorted union
of every non-null Blob Sigil named by an output, Log content, resource
evidence, terminal source, `BLOB` storage branch, or
`QUARANTINED.claimed_blob_sigil` or
`QUARANTINE_TERMINAL_NEGATIVE.claimed_blob_sigil`; it has
`maxItems: MAX_OUTPUT_STORAGE_OBSERVATION_BLOBS`, also 4,096. Construction
rejects a 4,097th member or distinct Blob before making the document durable;
it cannot omit a Log stream, evidence member, output, or terminal source to
fit. Result acceptance likewise rejects an output manifest whose complete
projected observation set would exceed either aggregate bound.

Every non-placeholder member resolves exactly one entry in the frozen output
ESM by `storage_subject_id` and `manifest_entry_sigil`; its subject fields,
claimed Blob, and `storage_origin` are copied byte-for-byte. Therefore an
output observation always retains the current Attempt's exact TransferRef and
provenance even when the selected Blob projection points at a deduplicated
Replica created by an older transfer. The OS cannot synthesize provenance
from `replica.creator`, a shared Blob, or current backend state.

Output members are unique and sorted by
`(logical_name unsigned ASCII, blob_sigil)` and equal the accepted Result's
complete output array after replacing the opaque staging reference with its
canonical-JSON Sigil. `ATTEMPT_OUTPUTS_NONE` uses `NO_RESULT` only with
`result_binding: NONE`, `RESULT_REJECTED` only with `REJECTED`, and
`OUTPUT_ARRAY_EMPTY` only with an accepted Result whose output array is
empty. Resource members are unique and sorted by
`(control_evidence_id unsigned ASCII, phase order, evidence-kind enum order,
phase_evidence_entry_sigil)`, where phase order is `PREFLIGHT`, `RUNTIME`,
`TERMINATION`, `CLEANUP`. Resolve the exact control-evidence-set ID-and-Sigil
pair, then every one of its ten ID-and-Sigil member references. Resource
members equal every Blob-bearing phase entry in that closed traversal:
`control_evidence_sigil` equals the resolved parent record, and
`phase_evidence_entry_sigil` equals the independently recomputed Sigil of the
exact entry whose remaining fields are copied byte-for-byte. The `NONE`
branch is legal only when that complete traversal is empty. A control
evidence Sigil without its set ID and closed member references cannot supply
this collection.

Each `LOG_STREAM.content` is exactly
`EMPTY {kind, blob_sigil, storage}` or
`CAPTURED {kind, blob_sigil, storage}`. `EMPTY` requires null
`final_sequence`, zero captured bytes, the SHA-256 Blob identity of the empty
byte string, and a storage observation for those zero bytes. `CAPTURED`
requires non-null final sequence, positive captured bytes, and a Blob whose
logical bytes are the sequence-ordered concatenation of all committed chunks
through that final sequence. In both branches, the content Blob Sigil,
captured byte count, closure Event, and complete chunk sequence recompute the
exact `stream_set_sigil`; dropped bytes are not silently appended to the
content. Thus even an empty or truncated stream has one explicit stable
branch, and Outcome derivation never guesses a Blob from a log-set hash.

`TERMINAL_SOURCE_NOT_APPLICABLE` is legal only with the
`terminal_source_binding: NOT_APPLICABLE` branch.
`TERMINAL_SOURCE_NONE` is legal only with `QUARANTINED` whose source identity
and Sigil and `storage_blob` are all null and whose counts are both zero; its
non-empty sorted `reason_codes` equal that binding. `TERMINAL_SOURCE` copies
the non-null identity, Sigil, storage BlobRef, retention-policy Sigil, file
count, and byte count from
`VERIFIED` or
`QUARANTINED`, and `disposition` names that exact branch. A `VERIFIED`
terminal source requires `storage: BLOB`; a quarantined terminal source
uses `storage: QUARANTINED` only for a QBS `RETAINED` disposition and
`storage: QUARANTINE_TERMINAL_NEGATIVE` for `TERMINAL_NEGATIVE`.

Every member's `storage` or log `content.storage` is exactly one of these
closed branches:

| Storage branch | Exact fields |
| --- | --- |
| `NONE` | `kind`, `terminal_storage_status`; status is constant `UNAVAILABLE`. |
| `BLOB` | `kind`, `terminal_storage_status`, `blob_sigil`, `size_bytes`, `blob_record_sigil`, `availability`, `availability_as_of`, `availability_basis_sigil`, `integrity_event_sigils`, `quarantine`, `replica`. |
| `QUARANTINED` | `kind`, `terminal_storage_status`, `claimed_blob_sigil`, `claimed_size_bytes`, `quarantine_binding_sigil`, `quarantine_id`, `owner_kind`, `owner_id`, `state`, `source_object`, `destination_object`, `quarantine_record_sigil`, `quarantine_event`, `reason`. |
| `QUARANTINE_TERMINAL_NEGATIVE` | `kind`, `terminal_storage_status`, `claimed_blob_sigil`, `claimed_size_bytes`, `quarantine_binding_sigil`, `quarantine_id`, `owner_kind`, `owner_id`, `state`, `source_object`, `destination_object`, `quarantine_record_sigil`, `origin_event`, `observation_event`, `reason`; status is constant `UNAVAILABLE` and state is `FAILED`, `DISPOSAL_FAILED`, or `DISPOSED`. |

`NONE` is legal only when the source bytes never became an RFC-0013 Blob or
Quarantine record. It is explicit negative evidence and cannot make a Job
succeed. In `BLOB`, `terminal_storage_status` and `availability` are the same
RFC-0013 value, exactly `AVAILABLE`, `DEGRADED`, `UNAVAILABLE`, or
`INCIDENT`. `blob_sigil`, `size_bytes`, `blob_record_sigil`,
`availability_as_of`, `availability_basis_sigil`, and the sorted unique
`integrity_event_sigils` equal the complete frozen RFC-0013 Blob projection.
The member's independently declared Blob identity and size must equal this
branch. `availability_as_of` is an exact RFC-0013 `EventRef` no later than
`storage_event`, not a Timestamp.

`BLOB.quarantine` is exactly `NONE {kind}`. A directly quarantined member
uses the `QUARANTINED` storage branch instead, whose
`terminal_storage_status` is constant `QUARANTINED`.
`claimed_blob_sigil` and `claimed_size_bytes` are non-null and equal the
member's claimed identity and size. The member deterministically constructs
its closed subject branch and resolves the observation document's exact
quarantine-binding-set ID-and-Sigil pair. Exactly one binding has that subject
byte-for-byte; `quarantine_binding_sigil`, Quarantine ID, owner, record Sigil,
and complete `quarantine_event` equal that binding's `observation_event`. The remaining fields
copy that one exact RFC-0013 Quarantine State item, including its nullable
source object, non-null destination `BackendObjectRef`, and closed `Reason`.

Only a QBS `RETAINED` binding is legal in `QUARANTINED`: its origin is
`quarantine.recorded` and its State is `HELD` or `DISPOSAL_FAILED`. In both
cases the
referenced destination generation remains durably isolated and its
`blob_sigil` and `size_bytes` equal the claimed pair. `INTENT_RECORDED`,
`INSPECTING`, and `DISPOSING` block accounting. A QBS
`TERMINAL_NEGATIVE` binding uses `FAILED`, `DISPOSAL_FAILED`, or `DISPOSED`
only with the exact origin/state matrix above and is legal only in
`QUARANTINE_TERMINAL_NEGATIVE`, using the QBS binding's exact origin and
observation Events; that branch is unavailable and never success-eligible.
A failed move, failed-origin disposition failure, or completed disposition
cannot be reported as retained Quarantine. If `source_object` is non-null, its size
equals the claimed size and its Blob Sigil is either null exactly as preserved
by RFC-0013's unauthenticated-intent branch or equals the claimed Sigil; no
other identity is legal. Source and destination objects retain their complete
backend/object/locator identity Sigils and immutable generations. The
Quarantine State record's last EventRef is no later than `storage_event`.
The complete quarantine-binding set contains every and only quarantined
observation subject, so a Quarantine item cannot be selected by shared Blob,
size, filename, directory enumeration, most-recent time, or an unrelated
owner.

`BLOB.replica` is exactly `NONE {kind}` or
`SELECTED {kind, replica_id, replica_record_sigil, state, backend, object,
verification}`. The selected branch imports RFC-0013 `BackendRef`,
`BackendObjectRef`, and `VerificationRef` without restatement; `state` is
constant `AVAILABLE`, so the observation retains the backend identity,
backend profile version and Sigil, object identity and locator Sigils,
immutable backend generation, verification method and evidence, verification
time, and next due time. For every `BLOB` branch, the selector is total:
replay the frozen Blob's exact sorted `eligible_replica_ids`; use `NONE` iff
that array is empty, otherwise select the unsigned-ASCII smallest Replica ID
and copy that complete frozen Replica projection. The selected Replica's
Blob, size, backend object Blob, state, generation, and verification must
match the member and frozen Blob. No caller preference, backend priority,
filesystem order, current availability, or retry may select a different
Replica.

Before the mandatory final `ACCOUNTING_CAPTURED` progress event, when logs,
outputs, terminal-source disposition, the complete output ESM and its
Blob/Reference-Set hold, and every
metered storage, evidence, Quarantine, and cleanup action are closed, the
Executor acquires the RFC-0013 outer gate and then the Storage Journal lock.
It verifies the one complete Storage prefix and State, durably creates or
reuses the exact CES and QBS resolver records, and fixes the QBS historical
prefix. It releases the Storage Journal lock while retaining the outer gate,
then appends `ACCOUNTING_CAPTURED` with the CES and QBS `FROZEN` pairs, the
frozen output ESM pair, and its exact `NO_HOLD` or `HELD` protection branch.

Immediately afterward, still under that gate, it constructs this observation
document from the QBS-bound historical prefix only when the deterministic OS
pending slot is absent. If that slot already exists, it instead replays and
validates the record's same bound historical prefix and reuses the exact pair.
It appends the Attempt terminal event with that `FROZEN` reference and only
afterward releases the outer gate. All three terminalization documents and
resolvers are pre-reserved Executor control overhead; their writes cannot
create or change a Blob, Replica, Quarantine, hold, or backend object after
accounting capture. Every `BLOB` member that must survive
terminalization is covered by one of the terminal event's pre-held
`ATTEMPT_OUTPUT` Reference Sets; one Reference Set may cover many members. A
crash can therefore leave at most one pending immutable record and
conservative holds for an Attempt, but never an accounting capture that
omitted later metered work or a terminal event whose referenced record or Blob
protection was not already durable.

Idempotency is byte-exact. Before terminal commitment, retry under the same
owner and terminal inputs derives the same OS-ID. If its pending resolver slot
exists, the retry must reuse that record's Storage EventRef, State Sigil,
members, and self-Sigil; it cannot refresh the observation from a later
Storage Head. After terminal commitment, replay or a repeated internal
finalization request returns the already committed terminal event and its
exact resolver pair without rebuilding the document. Reuse of an OS-ID with
a changed member, prefix, owner, or self-Sigil is an integrity failure, not a
second observation and not permission to search for another hash. Because an
Attempt's ID inputs freeze before construction, at most one such record exists
per Attempt and the global record count is bounded by `MAX_ATTEMPTS` 4,096.

### Storage-root linearization

RFC-0013 owns Blob, Reference Set, hold, and GC semantics. This RFC owns when
an execution root becomes visible or inactive. The two journals use the
RFC-0013 outer canonical-reference gate to make that boundary conservative
under every crash.

V1 has exactly three root kinds and activation events:

| Root kind | Owner equality | Sole activating execution event | Sole inactivating execution event |
| --- | --- | --- | --- |
| `JOB_INPUT` | Entry `job_id` equals the submitted Job; `attempt_id` is null. | `job.submitted` in its required `job_storage_roots`. | That Job's terminal event. |
| `ATTEMPT_INPUT` | Entry `job_id` and `attempt_id` equal the preflight Attempt and its immutable parent. | `attempt.preflight_passed` in its required `input_storage_roots`. | That Attempt's terminal event. |
| `ATTEMPT_OUTPUT` | Entry `job_id` and `attempt_id` equal the terminal Attempt and its immutable parent. | That Attempt's terminal event in its required `output_storage_roots`. | The parent Job's terminal event. |

Every array is present and contains zero or one entry. One ESM and one
Reference Set cover the complete Blob closure for that owner and root kind;
splitting a closure across multiple roots is invalid. No other event can
carry, activate, rename, or inactivate an execution root. `ACTIVE_CONTROL` is
forbidden in RFC-0012 v1:
the event and State Schemas reject it, and an implementation that needs such a
root requires a new RFC and Schema version with a complete event lifecycle.

Before `job.submitted`, the Executor holds the gate, registers the exact
Reference Sets for the immutable Job inputs, and appends every Storage hold.
It releases the Storage Journal lock, appends `job.submitted` with the exact
pre-held `job_storage_roots`, and then releases the outer gate. Immediately
before that append it re-resolves each hold as `ACTIVE` and proves that no
deterministic EHR record exists. A hold without the submission event is an
orphan conservative hold, never a live Job root. The Job roots remain active
through every retry and become inactive only when the Job terminal event
commits.

Before `attempt.preflight_passed` may expose a managed Attempt input, the
Executor performs the same hold-first order and appends that event with only
`ATTEMPT_INPUT` entries. Output transfer follows the same order: verified
Blob, Reference Set, and hold are durable before the Attempt terminal event
binds only `ATTEMPT_OUTPUT` entries. Pending input or output whose hold exists
but whose activating event does not is an orphan conservative Storage hold
and is not an active execution root or eligible output. Each activating Event
performs the same final `ACTIVE`-hold and no-EHR check under the gate.

Root removal uses the reverse safe order while holding the same gate. The
Execution Journal first appends the transition that makes the root inactive;
only then may the Executor durably create the matching `OWNER_TERMINAL` or
`OUTPUT_DEADLINE` EHR and Storage append `retention.hold_released`. An
unactivated orphan instead requires the exact `ORPHAN_ABORT` EHR above. A
crash therefore leaves an extra hold, never an unprotected live execution
reference. `JOB_INPUT` is released only by its Job-terminal
`OWNER_TERMINAL` basis and `ATTEMPT_INPUT` only by its Attempt-terminal
`OWNER_TERMINAL` basis. State retains each historical binding after
inactivation, but
`ExecutionRootSnapshot` includes it only from the activating event through the
prefix immediately before its inactivating event. Output holds may remain
after Job terminal only through their immutable execution-owned retention
schedule below; lingering hold duration does not reactivate the execution
root. A canonical RFC-0015 reference, legal hold, or RFC-0013 retention policy
uses its own independent protection and is never represented by prolonging an
execution hold.

Every Job terminal payload contains sorted
`output_hold_release_schedules`, one for each child `ATTEMPT_OUTPUT` root and
none for an output manifest whose protection branch is `NO_HOLD`. Each closed
entry has exactly `attempt_id`, `storage_root_manifest_id`,
`storage_root_manifest_sigil`, `reference_set_id`, `reference_set_sigil`,
`hold_id`, `hold_set_event`, `retention_duration_seconds`,
`root_inactivation_event_id`, `release_due_at`, and `deadline_status`.
`root_inactivation_event_id` equals the enclosing Job terminal Event ID.
The duration is the bound Specification value for `CODE_MODIFICATION` and
zero for `NONE`; it is the maximum lifetime of this execution-owned hold, not
the minimum physical lifetime of any RFC-0013 policy. With checked Timestamp
arithmetic, `release_due_at = terminal recorded_at + duration` and
`deadline_status: EXACT`. If addition is unrepresentable, the entry instead
uses the terminal `recorded_at` and `OVERFLOW_FAIL_CLOSED`; that Job cannot
be `SUCCEEDED` under `CODE_MODIFICATION`.

Release uses the same outer gate. The Executor first proves by complete
Execution replay that the named Job terminal Event inactivated the root and
that trusted time is at or after `release_due_at`, then creates or resolves the
exact `OUTPUT_DEADLINE` EHR. Storage appends the one
`retention.hold_released` for exactly this `SH-ID` with
`authorization_sigil == release_authorization_sigil`; afterward Execution
appends `storage_root.hold_release_observed` with the complete schedule, EHR
ID and Sigil, and exact Storage release `EventRef`. A zero-duration schedule
follows this order immediately after the Job terminal Event under the same
gate. A crash at any point leaves either an extra hold or a durable EHR or
Storage release that Recovery can reuse; it never releases before
inactivation. Clock uncertainty, unavailable replay, or an ambiguous Storage
prefix preserves the hold.

The observation payload's `release_binding` is a closed union:

- `OWNER_TERMINAL {kind, storage_root, release_authorization_id,
  release_authorization_sigil}` for an activated `JOB_INPUT` or
  `ATTEMPT_INPUT`; or
- `OUTPUT_DEADLINE {kind, release_schedule, release_authorization_id,
  release_authorization_sigil}` for `ATTEMPT_OUTPUT`.

The owner branch's root and EHR equal the complete release authorization; the
output branch's schedule is byte-for-byte one entry from its terminal Job.
`storage_release_event` resolves the exact RFC-0013
`retention.hold_released` Event. Its hold ID, reason branch, and authorization
Sigil equal the resolved EHR. One observation is legal per hold; exact replay
returns it and conflicting binding, EHR, or Storage Event substitution fails.
`ORPHAN_ABORT` has no observation branch: by definition no activating
execution Event made a Job or Attempt owner visible, so the durable EHR and
the exact Storage release Event are its complete operational evidence.

The release removes only the execution-owned hold. It neither deletes bytes
nor alters a policy hold, legal hold, canonical reference intent, accepted
Agent Result pin, or another root. RFC-0013 independently decides physical GC
eligibility after all remaining protections are applied.

Recovery acquires the gate, replays both journals one at a time in the order
defined by RFC-0013, and reconciles only toward more protection when either
side is unavailable or ambiguous. An orphan has no execution-journal owner
and therefore is not an action in
`execution-recovery-action-set/1.0`. Only after no Execution Recovery is
active, a Storage-side orphan reconciler may hold the gate, replay through the
complete current Execution Head, prove absence of the sole activation, create
or resolve the deterministic `ORPHAN_ABORT` EHR, and reuse or append only that
hold's Storage release. The same rule applies inside exact Start recovery
before a new activation is considered. For an inactive input root, Execution
Recovery creates or resolves `OWNER_TERMINAL`; for an output root it executes
`RELEASE_DUE_EXECUTION_HOLD` only for an `EXACT` due schedule or the immediate
`OVERFLOW_FAIL_CLOSED` schedule and resolves `OUTPUT_DEADLINE`. In every
branch it reuses an existing EHR and Storage release before any missing
observation. An ambiguous Head, prefix, clock, EHR, or release retains the
hold. This protocol lets RFC-0013 GC derive its closed
`ExecutionRootSnapshot`; a filename, result message, current process, or
unlocked Head comparison is never an execution root decision.

## Requested and realized assurance

Requested assurance is immutable input; realized assurance is terminal
evidence.

The Execution Specification and Job bind:

```text
(requested level,
 assurance-profile version and Sigil,
 permitted conformance-suite identity and Sigil)
```

Each Attempt repeats that tuple and records a planned backend identity,
backend-configuration Sigil, and preflight eligibility decision. Worker
capability, backend selection, conformance history, and `PREFLIGHTING -> READY`
show only that the Attempt may try to meet the request. None is a realized
claim.

`sanctum-assurance-profile/1.0` has exactly `schema_version`,
`profile_version`, `levels`, `conformance_suites`, and `profile_sigil`.
`schema_version` is the constant `sanctum-assurance-profile/1.0`; every other
member is covered by `profile_sigil`. `levels` contains exactly three entries,
in increasing `rank`, and each closed entry has exactly `level`, `rank`,
`name`, `threat_model_sigil`, `control_requirements`, and `level_sigil`. The
three fixed `(level, rank, name)` tuples are
`(SANCTUM-A0, 0, DECLARED_ATTEMPT)`,
`(SANCTUM-A1, 1, SUPERVISED)`, and
`(SANCTUM-A2, 2, ISOLATED)`. A3 is reserved by RFC-0011 and is not a v1 enum
value. Each `control_requirements` array has exactly one entry for each of the
ten control dimensions in the printed matrix order. An entry has exactly
`control_dimension`, `required_state`, `required_evidence_kinds`, and
`requirement_evidence_profile_sigil`. `required_evidence_kinds` is a unique
non-empty array in the evidence-kind enum order defined below; the evidence
profile Sigil binds the closed verifier predicates applied to those kinds.

The A0 and A1 `required_state` values are exactly the matrix below. The A2
vector, in that same control-dimension order, is exactly
`VERIFIED`, `ENFORCED`, `ENFORCED`, `ENFORCED`, `ENFORCED`, `ENFORCED`,
`ENFORCED`, `VERIFIED`, `ENFORCED`, `VERIFIED`. Its evidence-profile Sigils
bind the externally enforced isolation, adversarial fixture, and Host threat
model required by RFC-0011; an A1 evidence profile cannot be reused as an A2
entry.

`conformance_suites` is a non-empty bounded array sorted by
`(level rank, conformance_suite_id unsigned ASCII, suite_version unsigned
ASCII)`. Every closed entry has exactly `conformance_suite_id`,
`suite_version`, `level`, `backend_constraints_sigil`,
`host_constraints_sigil`, `fixture_set_sigil`,
`evidence_oracle_sigil`, and `conformance_suite_sigil`. IDs are unique within
a profile version. Each suite's `level` names one of the three profile
entries, and its fixture and oracle Sigils must test every requirement through
that level. An Execution Specification's `profile_version` and
`profile_sigil` identify this complete document, while its
`conformance_suite_id` and `conformance_suite_sigil` identify exactly one
entry whose level rank is at least the requested rank. No member is optional
or nullable, and unknown levels, states, dimensions, suites, or duplicate
entries fail closed.

The `execution-control-evidence/1.0` top-level object has exactly:

| Field | Exact v1 meaning |
| --- | --- |
| `schema_version` | Constant `execution-control-evidence/1.0`. |
| `control_evidence_id`, `job_id`, `attempt_id` | Evidence and execution scope. |
| `control_dimension` | One of the exact dimensions in the matrix below. |
| `required_state` | Exactly `ENFORCED`, `VERIFIED`, `OBSERVED`, or `ANY_RECORDED`. |
| `realized_state` | Exactly `ENFORCED`, `VERIFIED`, `OBSERVED`, or `UNAVAILABLE`. |
| `phase_evidence` | Exactly `preflight`, `runtime`, `termination`, and `cleanup`; each is a `0..4096` array, present even when empty. |
| `bindings` | Exactly `backend_sigil`, `host_sigil`, `runtime_sigil`, `policy_set_sigil`, `input_set_sigil`, and `output_set_sigil`. |
| `deficiencies` | Zero to 4,096 sorted closed reason entries; present even when empty. |
| `control_evidence_sigil` | Sigil over every other member. |

Every `phase_evidence` entry has exactly `evidence_kind`,
`producer_identity`, `verifier_identity`, `collected_at`, `byte_size`,
`blob_sigil`, and `staging_reference`. `byte_size` and `blob_sigil` are either
both null or respectively RFC-0013 `U63` and `Sigil`.
`staging_reference` is exactly
`NONE {kind}` when that pair is null or
`TRANSFER {kind, storage_subject_id, transfer: RFC-0013 TransferRef,
provenance_id, provenance_sigil}` when it is non-null. The transfer and
provenance resolve the same Blob and exact current Attempt owner. Across all
four arrays of one document there are at most 4,096 entries, and across the
ten documents selected by one CES there are at most 4,096 Blob-bearing
entries; overflow fails before the CES or output ESM is durable.
The exact `control_dimension` enum is
`IDENTITY_AUTHORIZATION`, `FILESYSTEM`, `NETWORK`,
`PROCESS_EXECUTABLE`, `RESOURCE`, `ENVIRONMENT_CREDENTIAL`,
`LOG_OUTPUT_CAPTURE`, `RUNTIME_INPUT_OUTPUT_IDENTITY`,
`CANCELLATION_FENCING`, and `TERMINATION_CLEANUP`. There is no generic
dimension or evidence dictionary.

The exact `evidence_kind` enum is `TASK_BINDING`, `CAPABILITY_BINDING`,
`SNAPSHOT_BINDING`, `WARD_DECISION`, `APPROVAL_RECEIPT`,
`BACKEND_CONFIGURATION`, `HOST_IDENTITY`, `POLICY_RESOLUTION`,
`BASE_IDENTITY`, `INPUT_IDENTITY`, `MATERIALIZATION_IDENTITY`,
`ENVIRONMENT_CONSTRUCTION`, `FILESYSTEM_POLICY`, `NETWORK_POLICY`,
`EXECUTABLE_SELECTION`, `PROCESS_TREE`, `WALL_TIME_ENFORCEMENT`,
`RESOURCE_ACCOUNTING`, `CREDENTIAL_NONINHERITANCE`, `LOG_CAPTURE`,
`OUTPUT_VALIDATION`, `STORAGE_OBSERVATION`, `FENCE_TOMBSTONE`,
`TERMINATION`, `HANDLE_REVOCATION`, `CLEANUP`, `QUARANTINE`,
`TERMINAL_SOURCE_VERIFICATION`, or `CONFORMANCE_FIXTURE`. Each
`deficiencies` entry has exactly `reason_code`, `phase`, `evidence_kind`, and
`detail_sigil`; `phase` is `PREFLIGHT`, `RUNTIME`, `TERMINATION`, or
`CLEANUP`, and its reason uses the closed protocol reason enum below.

Requirement satisfaction is an explicit relation, not an inferred ordering:
`ANY_RECORDED` accepts any realized state; `OBSERVED` accepts
`OBSERVED`, `VERIFIED`, or `ENFORCED`; `VERIFIED` accepts only `VERIFIED`;
and `ENFORCED` accepts only `ENFORCED`. An `ENFORCED` document may carry
independent verifier evidence, but enforcement is not silently relabeled
verification and vice versa.

Only the trusted evidence verifier, after the Attempt is terminal and its
termination and cleanup evidence is immutable, may emit
`sanctum-assurance-claim/1.0`. Its exact required top-level members are
`schema_version`, `assurance_claim_id`, `job_id`, `attempt_id`,
`attempt_terminal_event_id`, `attempt_terminal_event_sigil`,
`requested_assurance`, `realized_level`, `satisfies_request`,
`profile_sigil`, `conformance_suite_sigil`, `backend_identity`,
`backend_configuration_sigil`, `host_identity_sigil`, `policy_set_sigil`,
`result_binding`, `control_evidence_set_binding`, `termination_status`,
`cleanup_status`, `issued_at`, and `assurance_claim_sigil`.
`result_binding` is a closed union: `NONE` has exactly `kind`; `ACCEPTED` has
exactly `kind`, `result_sigil`, and `result_acceptance_event_sigil`. There are
no other optional top-level fields.

A claim may describe a failed, cancelled, timed-out, or policy-violating
Attempt when its boundary evidence is complete; assurance describes execution
controls, not computational or scientific success. A lower realized level may
be recorded as explicit diagnostic evidence with
`satisfies_request: false`, but it never downgrades the request, makes a result
eligible, or lets a Job succeed. Missing or unverifiable evidence produces no
claim at that level.

A terminal `SUCCEEDED` Attempt is only a candidate for Job success. It requires:

1. its accepted result when required, explicit no-result disposition when
   permitted, and all selected outputs validate;
2. its Lease was current through accepted completion;
3. its process tree and required handles are terminated or released;
4. cleanup and output publication postconditions pass; and
5. no policy violation, stop trigger, stale binding, or conflicting result
   precedes terminal commitment.

After that terminal event and its budget settlement,
`attempt.assurance_evaluated` records one closed evaluation outcome without
changing the Attempt state. `CLAIMED` includes the valid claim Sigil; `UNMET`
or `UNVERIFIABLE` includes no claim and binds its evidence and reasons. The
Job can become `SUCCEEDED` only when a claim has `satisfies_request: true` and
its realized level is at least the requested level under the exact pinned
profile.

If computation completed but assurance is missing or insufficient, the
Attempt remains terminal `SUCCEEDED` as an operational computation outcome,
while its result remains ineligible and the Job becomes `FAILED` with reason
`ASSURANCE_UNMET`. The Executor never changes the requested level, substitutes
a different profile or suite, or reports preflight eligibility as realized
assurance.

### Exact A0 and A1 control/evidence matrix

For this RFC, `ANY_RECORDED` requires a control-evidence document that
truthfully uses one of the four realized evidence states; it does not imply
enforcement. These are the exact v1 minima:

| Control dimension | `SANCTUM-A0` minimum | `SANCTUM-A1` minimum and required evidence |
| --- | --- | --- |
| `IDENTITY_AUTHORIZATION` | `VERIFIED`: v2 Task, Capability, Snapshot, Ward, approval when required, Specification, Job, and Attempt identities and Sigils. | Same `VERIFIED` set, plus selected backend/profile/suite/configuration bindings. |
| `FILESYSTEM` | `ANY_RECORDED`; no containment claim. | `VERIFIED`: exclusive Crucible materialized from the pinned immutable Base or validated immutable resume identity, new mutable identity, and no reuse of ambiguous predecessor state. |
| `NETWORK` | `ANY_RECORDED`; no containment claim. | `OBSERVED`: closed network policy and supervisor observation are retained; this remains a cooperative-workload statement, not network isolation. |
| `PROCESS_EXECUTABLE` | `ANY_RECORDED`; no process-control claim. | `ENFORCED`: allowlisted initial executable, exact runtime identity, tracked cooperative process group, and supervisor start/exit evidence. |
| `RESOURCE` | `ANY_RECORDED`; Worker samples alone are diagnostic. | `ENFORCED`: durable wall-time/cancellation timers, per-Attempt ceilings, trusted Job-budget accounting, and terminal resource evidence. |
| `ENVIRONMENT_CREDENTIAL` | `ANY_RECORDED`; no hostile secret-exclusion claim. | `ENFORCED`: constructed allowlisted environment and absence of ambient credentials and unrelated inherited variables, with supervisor construction evidence. |
| `LOG_OUTPUT_CAPTURE` | `ANY_RECORDED`; bounds and stale-message rejection still apply operationally. | `ENFORCED`: bounded external capture, deterministic truncation/termination behavior, exact output contracts, and verified stream/output closure. |
| `RUNTIME_INPUT_OUTPUT_IDENTITY` | `VERIFIED` for pinned Job/Attempt input bindings; runtime/output absence is explicit. | `VERIFIED`: exact runtime, immutable inputs, produced outputs, Blob Sigils, byte counts, and storage disposition. |
| `CANCELLATION_FENCING` | `VERIFIED`: current fence tuple decides message disposition; this claims no process containment. | `ENFORCED`: supervisor wall-time and cooperative cancellation, Lease tombstone publication, no authority resurrection, and no ambiguous mutable-resource reuse. |
| `TERMINATION_CLEANUP` | `ANY_RECORDED`; missing evidence may be `UNAVAILABLE`. | `VERIFIED`: durable terminal event, tracked process-group termination or safe quarantine, handle disposition, cleanup, and retained evidence. |

Every A1 cell is mandatory. A policy whose own minimum evidence state is
stronger remains stronger; the matrix never weakens a v2 Capability or Task.
A1 does not claim hostile filesystem, network, process, resource, credential,
or `.benchwork/` isolation; those are A2 properties.

Required negative fixtures include:

- Phase 2 native-Host activity, or a Job with no Attempt, cannot claim A0;
- a missing Ward/approval/Sigil binding cannot claim A0 even if a process ran;
- Worker self-report, PID existence, or preflight eligibility cannot replace
  an A0 fence decision or an A1 verifier;
- a reused mutable Crucible, mutable resume path, inherited ambient
  credentials, untracked child, process-local-only wall timer, unbounded or
  unclosed capture, Worker-only accounting, or missing terminal/cleanup
  evidence prevents A1;
- A1 evidence cannot be relabeled A2 merely because a container, worktree, or
  namespace mechanism was present; and
- an incomplete control is recorded at its actual lower state and yields
  `UNMET` or `UNVERIFIABLE`, never an inferred claim.

## Operational journal

The execution journal is append-only operational state and is physically and
logically separate from Chronicle. It must not allocate Chronicle event types
or Receipt IDs, write Chronicle Heads/Seals/projections, or use canonical
object stores as its journal. It may carry an exact immutable external
Chronicle Event/Receipt reference where this RFC explicitly requires one,
such as Attempt authorization; that reference grants no execution-journal
writer authority. No Job or heartbeat event is appended to Chronicle.

### Journal Head and replayed State contracts

The closed limit profile is the constant
`EXECUTION_JOURNAL_V1_FIXED_LIMITS`. Its Schema constants are:

| Constant | Exact inclusive maximum |
| --- | ---: |
| `MAX_RECOVERIES` | 4,096 |
| `MAX_WORKERS` | 4,096 |
| `MAX_WORKER_SESSIONS` | 4,096 |
| `MAX_JOBS` | 4,096 |
| `MAX_ATTEMPTS` | 4,096 |
| `MAX_EXECUTION_STORAGE_ROOT_MANIFESTS` | 12,288 |
| `MAX_EXECUTION_STORAGE_ROOT_MANIFEST_ENTRIES` | 4,096 per manifest |
| `MAX_OUTPUT_STORAGE_OBSERVATION_RECORDS` | 4,096 |
| `MAX_OUTPUT_STORAGE_OBSERVATION_MEMBERS` | 4,096 |
| `MAX_OUTPUT_STORAGE_OBSERVATION_BLOBS` | 4,096 |
| `MAX_LEASES` | 4,096 |
| `MAX_LOG_STREAMS` | 12,288 |
| `MAX_DEADLINES` | 32,768 |
| `MAX_IDEMPOTENCY_RECORDS` | 65,536 |
| `MAX_ENTITY_PROJECTIONS` | 36,865, including the singleton Executor |
| `MAX_STATE_ROWS` | 135,169, including entity, deadline, and idempotency rows |
| `MAX_ENTITY_REVISIONS_PER_EVENT` | 5 |

One Job-input ESM plus at most one input and one output ESM per Attempt
explains the 12,288 manifest limit; the actual total is additionally bounded
by the created Job and Attempt counts. The three Log streams created per
Attempt explain the 12,288 Log-stream limit. The
single-assignment OS-ID rule makes the observation-record limit equal to
`MAX_ATTEMPTS`; pending and terminal records count identically. Counts include
terminal and failed history and never decrease. A `CREATE` or adjunct record
that would exceed its collection, entity-total, or State-total limit is
rejected before event-ID/sequence reservation and cannot be made legal by
dropping history. Existing entities may still advance so cleanup and
terminalization remain possible.

`execution-journal-head/1.0` has exactly `schema_version`, `limit_profile`,
`journal_id`, `last_sequence`, `last_event_id`, `last_event_sigil`,
`updated_at`, and `head_sigil`. `schema_version` is constant
`execution-journal-head/1.0`; `last_sequence` is `PositiveU63` because a valid
journal begins with `executor.epoch_started`; the event ID and Sigil
must identify that exact sequence; and `head_sigil` covers every other
member. `limit_profile` is the constant above. Head validation replays or
checks the bound prefix's collection counts against every constant before the
cache can be installed. `updated_at` is diagnostic cache metadata and never
participates in event ordering. No field is optional or nullable.

`execution-state/1.0` is a closed replaceable replay cache, not an authority
source. Its exact top-level members are `schema_version`, `limit_profile`,
`journal_binding`, `executor`, `recoveries`, `workers`, `worker_sessions`,
`jobs`, `attempts`, `leases`, `log_streams`, `deadlines`,
`idempotency_records`, and `state_sigil`. `schema_version` is constant
`execution-state/1.0`; `limit_profile` is the constant above.
`journal_binding` has exactly `journal_id`, `through_sequence`,
`through_event_id`, and `through_event_sigil`; it must equal the verified
journal prefix used to derive every other field, and `through_sequence` is
`PositiveU63`. `state_sigil` covers every
other member. All arrays are present even when empty, contain no duplicate
identity, include every entity created in the bound journal prefix, and are
bounded respectively by the matching fixed `MAX_*` constants. Their entity
sum and complete row sum must also fit the two total constants. A limit cannot
be used to omit terminal or failed history.

The State Schema publishes these closed reusable projection aliases:

- `public_fence_tuple` has exactly `journal_id`, `executor_epoch`, `job_id`,
  `attempt_id`, `lease_id`, and `fencing_generation`;
- `executor_build_binding` has exactly `implementation_id`,
  `implementation_version`, `source_revision_sigil`,
  `executable_artifact_sigil`, `dependency_set_sigil`,
  `build_configuration_sigil`, and `executor_build_sigil`. The first two are
  non-empty bounded `Opaque` values, every remaining value is `Sigil`, and
  `executor_build_sigil` is the self-Sigil over the other six fields;
- `terminal_event_binding` is exactly `NONE {kind}` or
  `PRESENT {kind, terminal_state, terminal_event_id, terminal_event_sigil,
  terminal_sequence, terminal_recorded_at}`. Context restricts
  `terminal_state` to the printed terminal enum for the owning entity;
- `attempt_authorization_requirement` is the exact immutable RFC-0011
  `NONE {kind, effects}` or `REQUIRED {kind, effects}` branch above;
- `attempt_authorization_binding` is the exact nine-field closed binding
  above, and its subject ID/Sigil always resolves the complete canonical
  `attempt-authorization-subject/1.0`; its request, Event, and Receipt fields
  resolve the complete authorization chain above;
- `attempt_authorization_state` is exactly `NONE {kind}`, `PENDING {kind}`,
  or `BOUND {kind, authorization_subject,
  attempt_authorization_binding}`; the embedded subject uses the canonical
  contract `$ref` and the binding uses the alias immediately above;
- `attempt_assurance_binding` is exactly `PENDING {kind}`,
  `CLAIMED {kind, evaluation_event_id, evaluation_event_sigil,
  evaluation_sequence, assurance_claim_sigil, evidence_set_sigil}`,
  `UNMET {kind, evaluation_event_id, evaluation_event_sigil,
  evaluation_sequence, reason_codes, evidence_set_sigil}`, or
  `UNVERIFIABLE {kind, evaluation_event_id, evaluation_event_sigil,
  evaluation_sequence, reason_codes, evidence_set_sigil}`;
- `job_assurance_binding` is exactly `PENDING {kind}`,
  `CLAIMED {kind, evaluation_event_id, evaluation_event_sigil,
  evaluation_sequence, attempt_id, attempt_assurance_event_sigil,
  assurance_claim_sigil, evidence_set_sigil}`,
  `UNMET {kind, evaluation_event_id, evaluation_event_sigil,
  evaluation_sequence, attempt_id, attempt_assurance_event_sigil,
  reason_codes, evidence_set_sigil}`,
  `UNVERIFIABLE {kind, evaluation_event_id, evaluation_event_sigil,
  evaluation_sequence, attempt_id, attempt_assurance_event_sigil,
  reason_codes, evidence_set_sigil}`, or
  `NOT_APPLICABLE {kind, evaluation_event_id, evaluation_event_sigil,
  evaluation_sequence, reason, evidence_set_sigil}`; the last branch has
  constant reason `NO_ATTEMPT_ALLOCATED`;
- `budget_dimension` has exactly `limit`, `reserved`, `consumed`, and
  `exhaustion_status`. The counters are non-negative checked integers.
  `exhaustion_status` is exactly `AVAILABLE` when
  `consumed + reserved < limit`, `EXHAUSTED` when it equals the limit, or
  `EXCEEDED` when trusted settlement proves use beyond the limit; only
  settlement may create `EXCEEDED`, and no further reservation is legal; and
- `budget_ledger` has exactly `attempts`, `cpu_time_seconds`,
  `storage_bytes_written`, `output_bytes`, `log_bytes`, `process_starts`,
  `network_egress_bytes`, `network_requests`, and `budget_ledger_sigil`;
  each dimension is the closed object above and the Sigil covers all eight;
- `budget_settlement_binding` is exactly `PENDING {kind}` or
  `SETTLED {kind, event_id, event_sigil, accounting_capture_event_id,
  accounting_capture_event_sigil, usage_status}`; `usage_status` is
  `MEASURED`, `PARTIAL`, or `UNAVAILABLE`; and
- `storage_root_binding` is byte-for-byte the journal-event `$def` of the same
  name described below. State Schema `$ref` uses its canonical RFC-0012 URI
  rather than redefining it;
- `terminalization_storage_manifest_binding` is the exact `PENDING` or
  `FROZEN` ESM pair above; and
- `output_root_protection` is `PENDING {kind}` before capture and the exact
  `NO_HOLD` or `HELD` branch above afterward. Both are published as named
  journal-event `$defs` and imported rather than cloned.

The executable Schemas also publish these named definitions at their canonical
URIs without changing the enums printed elsewhere:

- `https://benchwork.dev/schemas/execution-state/1.0#/$defs/executor_build_binding`
  is the exact closed build object above;
- `https://benchwork.dev/schemas/execution-state/1.0#/$defs/job_state` is the
  scalar enum `SUBMITTED`, `QUEUED`, `ACTIVE`, `RETRY_WAIT`, `STOPPING`,
  `SUCCEEDED`, `FAILED`, `CANCELLED`, `TIMED_OUT`, or `POLICY_VIOLATION`;
- `https://benchwork.dev/schemas/execution-state/1.0#/$defs/attempt_state` is
  the scalar enum `CREATED`, `PREFLIGHTING`, `READY`, `LEASED`, `STARTING`,
  `RUNNING`, `DRAINING`, `STOPPING`, `CLEANING`, `SUCCEEDED`, `FAILED`,
  `CANCELLED`, `TIMED_OUT`, `POLICY_VIOLATION`, `LEASE_EXPIRED`, `LOST`,
  `FENCED`, or `REJECTED`;
- `https://benchwork.dev/schemas/execution-state/1.0#/$defs/worker_session_state`
  is the scalar enum `REGISTERED`, `READY`, `BUSY`, `DRAINING`, `OFFLINE`,
  `QUARANTINED`, or `CLOSED`;
- `https://benchwork.dev/schemas/execution-journal-event/1.0#/$defs/event_type`
  is the exact 73-value enum block below; and
- `https://benchwork.dev/schemas/execution-journal-event/1.0#/$defs/storage_root_binding`
  is the exact closed object below.

Every State or event field carrying one of these values uses the named `$ref`;
RFC-0015 observation Schemas import the same URI rather than cloning a local
enum.

The exact `executor` object has `executor_instance_id`, `executor_epoch`,
`executor_build_binding`, `revision`, `clock_state`, `last_trusted_utc`,
`clock_uncertain_event_id`, `active_recovery_id`, `authority_gates`,
`last_event_id`, and `last_event_sigil`. `clock_state` is `TRUSTED` or
`UNCERTAIN`; `clock_uncertain_event_id` is non-null exactly in `UNCERTAIN`.
`active_recovery_id` is non-null exactly while one Recovery is active.
`authority_gates` is a unique array in the fixed order
`INTEGRITY_FAILURE`, `CLOCK_UNCERTAIN`, `RECOVERY_ACTIVE`; it is empty only
when none applies.

Every `recoveries` entry has exactly `recovery_id`, `revision`, `state`,
`prior_recovery_id`, `started_event_sigil`, `current_action_set_sigil`,
`last_event_id`, and `last_event_sigil`. `state` is `STARTED`, `FENCING`,
`RECONCILING`, `FINALIZING`, or `COMPLETED`; `prior_recovery_id` is null only
for the first Recovery. Entries are sorted by their `recovery.started`
sequence.

Every `workers` entry has exactly `worker_id`, `revision`, `state`,
`worker_binding_sigil`, `definition_revision`, `worker_session_ids`,
`last_event_id`, and `last_event_sigil`. Every `worker_sessions` entry has
exactly `worker_session_id`, `revision`, `state`, `worker_id`,
`worker_binding_sigil`, `worker_session_binding_sigil`, `executor_epoch`,
`capacity`, `capacity_in_use`, `last_heartbeat_sequence`,
`last_heartbeat_message_sigil`, `next_heartbeat_due_at`, `lease_ids`,
`last_event_id`, and `last_event_sigil`. Capacity is null only before
`worker_session.ready`; `capacity_in_use` is zero while capacity is null and
otherwise a non-negative integer no greater than capacity. Both
last-heartbeat fields are null before the first accepted heartbeat and
thereafter identify the same message; next due time is null in `REGISTERED`,
`OFFLINE`, `QUARANTINED`, or `CLOSED`. Identity arrays are unsigned-ASCII
sorted. Workers and Sessions use their exact state enums above.

Every `jobs` entry has exactly `job_id`, `revision`, `state`,
`job_binding_sigil`, `job_storage_roots`, `attempt_ids`,
`current_attempt_id`,
`fencing_counter`, `fence_floor`, `budget_ledger`, `deadline_due_at`,
`retry_eligible_due_at`, `queue_key`, `attempt_summaries`,
`selected_attempt_binding`, `completion_anchor_binding`,
`first_stop_or_fence_binding`, `final_fence_binding`,
`storage_observation_binding`, `terminal_source_binding`,
`output_hold_release_schedules`, `job_assurance_binding`,
`terminal_event_binding`, `last_event_id`, and
`last_event_sigil`. `current_attempt_id` is set by
`job.attempt_allocated` and remains that Attempt ID through Attempt
terminalization and `job.budget_settled`; it becomes null only in the
subsequent `attempt.assurance_evaluated` multi-owner event. It is otherwise
null, including before the first allocation and between a finalized Attempt
and retry allocation. Retry due time is non-null exactly in `RETRY_WAIT`;
queue key is non-null exactly in `QUEUED`.
`fencing_counter` and `fence_floor` are unsigned 64-bit integers with
`fence_floor <= fencing_counter`; both start at zero and only the atomic
events named below advance them.
`attempt_summaries` contains one exact `FINAL` summary only for an Attempt
whose terminal event, Job-budget settlement, and Attempt assurance evaluation
have all committed. A terminal-but-unsettled or settled-but-unevaluated
Attempt remains represented by `current_attempt_id` and its Attempt
projection, with no partial summary. `attempt.assurance_evaluated` atomically
adds the one final summary and clears `current_attempt_id`. At Job
terminalization the array covers every allocated Attempt and is
byte-for-byte equal to the terminal payload's sorted array.
`job_storage_roots` is byte-for-byte equal to the immutable Job document and
`job.submitted` payload. It contains only `JOB_INPUT`, remains historical
after terminalization, and is active for Storage-root derivation only from
submission through the prefix immediately before the Job terminal event.
`selected_attempt_binding`, `completion_anchor_binding`,
`final_fence_binding`, `storage_observation_binding`, and
`terminal_source_binding` are null before Job terminalization and, when
terminal, are byte-for-byte equal to the terminal event. The first-stop
binding and assurance binding are always their closed union rather than null.
`output_hold_release_schedules` is empty before terminalization and then
equals the terminal payload's complete immutable sorted schedule; later
release-observation events do not rewrite it or the terminal binding.
A terminal Job with no Attempt uses `storage_observation_binding:
NOT_APPLICABLE`; every terminal Job with an allocated selected Attempt copies
that Attempt's exact `FROZEN` branch.

Every `attempts` entry has exactly `attempt_id`, `revision`, `state`,
`attempt_binding_sigil`, `job_id`, `retry_ordinal`,
`fencing_generation`, `lease_executor_epoch`, `public_fence_tuple`,
`worker_session_binding`, `lease_id`, `result_binding`,
`attempt_authorization_requirement`, `attempt_authorization_state`,
`completion_anchor_binding`, `lease_terminal_binding`,
`first_stop_or_fence_binding`, `storage_observation_binding`,
`terminal_source_binding`, `accounting_capture_binding`,
`budget_settlement_binding`, `attempt_assurance_binding`,
`input_storage_roots`, `output_storage_roots`,
`control_evidence_set_binding`, `quarantine_binding_set_binding`,
`terminalization_storage_manifest_binding`, `output_root_protection`,
`deadline_due_at`, `grace_due_at`,
`terminal_event_binding`, `last_event_id`, and `last_event_sigil`.
Lease epoch, fence tuple, and Lease ID are null until an offer exists and are
thereafter immutable. The authorization requirement equals the immutable
Attempt document; its state is `NONE` or `PENDING` at allocation as selected
by that branch and may advance once from `PENDING` to `BOUND` only through
`attempt.authorization_bound`. `accounting_capture_binding` is exactly
`PENDING {kind}` or
`CAPTURED {kind, event_id, event_sigil, usage_status,
accounting_evidence_set_sigil}`. `budget_settlement_binding` is exactly
`PENDING {kind}` or
`SETTLED {kind, event_id, event_sigil, accounting_capture_event_id,
accounting_capture_event_sigil, usage_status}`. Grace due time is non-null
only in `STOPPING`. Both terminalization-set bindings and
`terminalization_storage_manifest_binding` are `PENDING` before
`ACCOUNTING_CAPTURED` and their exact `FROZEN` pairs afterward;
`output_root_protection` is `PENDING {kind}` before capture and its exact
`NO_HOLD` or `HELD` branch afterward. None is null.
`lease_terminal_binding` is `NONE` before an offer,
null from offer until the Lease terminal event, and `TERMINAL` thereafter.
`storage_observation_binding` is null before Attempt terminalization and is
the terminal event's exact `FROZEN` branch thereafter; an allocated Attempt
never uses `NOT_APPLICABLE`. Under a `CODE_MODIFICATION` Specification,
`terminal_source_binding` is null until `attempt.cleaning` and then
`VERIFIED` or `QUARANTINED`; under `NONE` it is always `NOT_APPLICABLE`.
`input_storage_roots` is empty until
`attempt.preflight_passed` and then byte-for-byte equals that event's sorted
array of only `ATTEMPT_INPUT`; those roots are active until the prefix
immediately before Attempt terminalization. `output_storage_roots` is empty
until Attempt terminalization and then equals its terminal event's sorted
array of only `ATTEMPT_OUTPUT`; those roots are active until the prefix
immediately before parent Job terminalization. Both historical arrays remain
present after inactivation, contain at most one `storage_root_binding`,
enforce exact owner equality, and use the RFC-0013 root tuple. All other
binding fields use the exact reusable unions in this RFC and
never null.

The finalization prefix is therefore always constructible. Immediately after
an Attempt terminal event, its `terminal_event_binding` is `PRESENT` while
`budget_settlement_binding` and `attempt_assurance_binding` remain `PENDING`;
the parent Job still names it as `current_attempt_id` and has no summary for
it. `job.budget_settled` then advances both the Job and Attempt, updates the
Job ledger and the Attempt's settlement binding atomically, but leaves
`current_attempt_id` and the absent summary unchanged.
`attempt.assurance_evaluated` is legal only after that settlement; it advances
both projections, freezes the Attempt assurance branch, appends the complete
Job `attempt_summary`, and clears `current_attempt_id` atomically. A crash
after any of these three events replays to exactly one of those states. Retry
scheduling, Job assurance evaluation, and Job terminalization require
`current_attempt_id: null` and therefore cannot observe or serialize a
partial summary.

Every `leases` entry has exactly `lease_id`, `revision`, `state`,
`lease_binding_sigil`, `job_id`, `attempt_id`, `worker_id`,
`worker_session_id`, `executor_epoch`, `fencing_generation`,
`claim_due_at`, `expiry_due_at`, `maximum_expiry_due_at`,
`last_heartbeat_sequence`, `last_heartbeat_message_sigil`,
`last_resource_sample_sigil`, `next_heartbeat_due_at`, `renewal_counter`,
`terminal_event_binding`, `tombstone_generation`,
`tombstone_event_sigil`, `last_event_id`, and `last_event_sigil`.
All three last-heartbeat fields are null before the first accepted Lease
heartbeat and thereafter identify the same message;
`next_heartbeat_due_at` is null in `OFFERED` and every terminal state but
non-null in `ACTIVE`;
tombstone fields are both non-null exactly in a terminal Lease state.

Every `log_streams` entry has exactly `log_stream_id`, `revision`, `state`,
`attempt_id`, `stream`, `next_sequence`, `captured_bytes`, `dropped_bytes`,
`truncated`, `final_sequence`, `stream_set_sigil`, `last_event_id`, and
`last_event_sigil`. `state` is `OPEN` or `CLOSED`; final sequence and stream
set Sigil are null in `OPEN`, while final sequence alone may remain null for
an empty closed stream. `stream` is `STDOUT`, `STDERR`, or `STRUCTURED`.

Each `deadlines` entry has exactly `deadline_kind`, `due_at`,
`fixed_priority`, `entity_id`, `source_event_id`, and
`source_event_sigil`. It represents one currently applicable deadline and is
sorted by the exact deadline key below. Each `idempotency_records` entry has
exactly `operation_kind`, `scope_id`, `idempotency_key_sigil`,
`request_sigil`, `disposition_event_id`, and `disposition_event_sigil`;
`operation_kind` is exactly `START_JOB`, `CANCEL_JOB`,
`REGISTER_WORKER_SESSION`, `CLAIM_LEASE`, `RENEW_LEASE`, `RELEASE_LEASE`,
`SUBMIT_RESULT`, or `APPEND_LOG_CHUNK`. Records are sorted by
`(operation_kind, scope_id unsigned ASCII, idempotency_key_sigil)` and bind
the first durable disposition forever. Scope is respectively the immutable
Task ID for Start, allocated Job ID for Cancel, Worker Session ID for
registration, Lease ID for the three Lease operations, Attempt ID for result
submission, and Log-stream ID for chunk append.

The entity arrays are sorted by creation-event sequence and then identity.
Every `last_event_id`/`last_event_sigil` pair identifies the event that
produced that entry's current revision. Any null outside the conditions above,
any extra projection member, or any cache value that differs from full replay
invalidates the cache; replay discards and rebuilds it without changing the
journal.

### Event envelope

Every `execution-journal-event/1.0` has exactly these required top-level
members:

| Field | Exact v1 rule |
| --- | --- |
| `schema_version` | Constant `execution-journal-event/1.0`. |
| `journal_id`, `event_id`, `sequence` | Exact journal, unique event, and one-based contiguous sequence. |
| `event_type` | One value from the exact enum below. |
| `executor_instance_id`, `executor_epoch`, `executor_build_sigil` | Appending coordinator identity, durable epoch, and immutable build Sigil fixed by that epoch's `executor.epoch_started`. |
| `recorded_at` | Non-decreasing trusted UTC protocol time. |
| `observed_at` | UTC observation time or `null`; it never orders the protocol. |
| `entity_revisions` | Non-empty bounded array sorted by `(entity_kind, entity_id)`. |
| `causation_event_id` | Direct cause event ID or `null`. |
| `idempotency_key_sigil` | Bound mutation-key Sigil or `null`. |
| `recovery_action_binding` | Closed Recovery action binding or `null` for a non-Recovery action. |
| `payload` | Exactly one closed branch selected by `event_type`. |
| `previous_event_sigil` | `null` only at sequence one; otherwise the preceding event Sigil. |
| `event_sigil` | Sigil over every other member. |

The `executor.epoch_started` payload carries the complete
`executor_build_binding` whose self-Sigil equals the envelope
`executor_build_sigil`. Replay stores that binding in the Executor projection.
Every later Event with the same `(executor_instance_id, executor_epoch)` must
copy the epoch-start build Sigil byte-for-byte. An epoch transition may select
a different valid build binding, but it never relabels an Event, Lease,
Attempt, or authority binding from an older epoch.

Each `entity_revisions` entry has exactly `entity_kind`, `entity_id`,
`preceding_revision`, and `next_revision`. Creation uses
`preceding_revision: null` and `next_revision: 0`. Every owner projection
changed by an event, including state-neutral evidence, advances exactly by
one; an entity listed only to validate an unchanged relationship uses equal
non-null revisions. The exact table below, including its two closed
conditional augmentations, is the sole authority for which changed or
unchanged projections appear. A multi-entity event lists every effect in that
table and no other entity.

A journal revision entry's exact `entity_kind` enum and ID class are:

| `entity_kind` | Required `entity_id` class |
| --- | --- |
| `EXECUTOR` | Executor instance ID |
| `RECOVERY` | Recovery transaction ID |
| `WORKER` | Worker ID |
| `WORKER_SESSION` | Worker Session ID |
| `JOB` | Job ID |
| `ATTEMPT` | Attempt ID |
| `LEASE` | Lease ID |
| `LOG_STREAM` | Log-stream ID |

This printed order is the canonical `entity_revisions` sort order. Budget,
deadline, result, assurance, and retention projections are owned by their Job
or Attempt; they do not invent anonymous entity kinds.

The revision-effect algebra is closed:

- `CREATE(K, id)` requires no prior projection for `(K, id)`, encodes
  `(preceding_revision: null, next_revision: 0)`, and initializes exactly the
  state named by the event;
- `ADVANCE(K, id)` requires the current non-negative revision `r`, encodes
  `(r, r + 1)` with checked arithmetic, and makes this event the projection's
  `last_event_id`/`last_event_sigil`;
- `EQUAL(K, id)` requires the current revision `r`, encodes `(r, r)`, and
  validates the named unchanged relationship without changing state,
  revision, or last-event binding.

For the table below, `X` is the envelope `executor_instance_id`; `R` is the
payload or recovery-action `recovery_id`; and `W`, `S`, `J`, `A`, `L`, and
`G` are the Worker, Worker Session, Job, Attempt, Lease, and Log-stream IDs
resolved from the event's immutable binding or its uniquely typed revision
entry. `J`, `A`, `L`, and `S` must equal the parent/child IDs in every
referenced immutable document. `G0`, `G1`, and `G2` are respectively the
fresh `STDOUT`, `STDERR`, and `STRUCTURED` Log-stream IDs in the newly created
Attempt binding.

Each row is the exact base set of revision entries for that one event:

| Event type | Exact base revision effects |
| --- | --- |
| `executor.epoch_started` | `CREATE(EXECUTOR, X)` exactly at sequence one; otherwise `ADVANCE(EXECUTOR, X)` for the existing Executor ID. |
| `executor.clock_uncertain` | `ADVANCE(EXECUTOR, X)` |
| `executor.clock_restored` | `ADVANCE(EXECUTOR, X)` |
| `recovery.started` | `ADVANCE(EXECUTOR, X)`, `CREATE(RECOVERY, R)` |
| `recovery.action_set_rebased` | `ADVANCE(RECOVERY, R)` |
| `recovery.phase_advanced` | `ADVANCE(RECOVERY, R)` |
| `recovery.completed` | `ADVANCE(EXECUTOR, X)`, `ADVANCE(RECOVERY, R)` |
| `worker.definition_registered` | `CREATE(WORKER, W)` |
| `worker.enabled` | `ADVANCE(WORKER, W)` |
| `worker.draining` | `ADVANCE(WORKER, W)` |
| `worker.quarantined` | `ADVANCE(WORKER, W)` |
| `worker.retired` | `ADVANCE(WORKER, W)` |
| `worker_session.registered` | `CREATE(WORKER_SESSION, S)` |
| `worker_session.ready` | `ADVANCE(WORKER_SESSION, S)` |
| `worker_session.draining` | `ADVANCE(WORKER_SESSION, S)` |
| `worker_session.offline` | `ADVANCE(WORKER_SESSION, S)` |
| `worker_session.quarantined` | `ADVANCE(WORKER_SESSION, S)` |
| `worker_session.closed` | `ADVANCE(WORKER_SESSION, S)` |
| `worker_session.heartbeat_accepted` | `ADVANCE(WORKER_SESSION, S)` |
| `worker_session.message_rejected` | `ADVANCE(WORKER_SESSION, S)` |
| `job.submitted` | `CREATE(JOB, J)` |
| `job.queued` | `ADVANCE(JOB, J)` |
| `job.attempt_allocated` | `ADVANCE(JOB, J)`, `CREATE(ATTEMPT, A)`, `CREATE(LOG_STREAM, G0)`, `CREATE(LOG_STREAM, G1)`, `CREATE(LOG_STREAM, G2)`; the three streams initialize `OPEN` atomically. |
| `job.budget_settled` | `ADVANCE(JOB, J)`, `ADVANCE(ATTEMPT, A)` |
| `job.retry_scheduled` | `ADVANCE(JOB, J)` |
| `job.retry_ready` | `ADVANCE(JOB, J)` |
| `job.stop_latched` | `ADVANCE(JOB, J)` |
| `job.cancellation_observed` | `EQUAL(JOB, J)` |
| `job.assurance_evaluated` | `ADVANCE(JOB, J)` |
| `job.succeeded` | `ADVANCE(JOB, J)` |
| `job.failed` | `ADVANCE(JOB, J)` |
| `job.cancelled` | `ADVANCE(JOB, J)` |
| `job.timed_out` | `ADVANCE(JOB, J)` |
| `job.policy_violated` | `ADVANCE(JOB, J)` |
| `storage_root.hold_release_observed` | `EQUAL(JOB, J)` |
| `job.message_rejected` | `ADVANCE(JOB, J)` |
| `attempt.authorization_bound` | `ADVANCE(ATTEMPT, A)` |
| `attempt.preflight_started` | `ADVANCE(ATTEMPT, A)` |
| `attempt.preflight_progressed` | `ADVANCE(ATTEMPT, A)` |
| `attempt.preflight_passed` | `ADVANCE(ATTEMPT, A)` |
| `attempt.starting` | `ADVANCE(ATTEMPT, A)` |
| `attempt.running` | `ADVANCE(ATTEMPT, A)` |
| `attempt.result_accepted` | `ADVANCE(ATTEMPT, A)` |
| `attempt.result_rejected` | `ADVANCE(ATTEMPT, A)` |
| `attempt.draining` | `ADVANCE(ATTEMPT, A)` |
| `attempt.stop_latched` | `ADVANCE(ATTEMPT, A)` plus `ADVANCE(JOB, J)` when no earlier event in the same effective-sequence due chain advanced `J`; otherwise `EQUAL(JOB, J)`. |
| `attempt.stop_progressed` | `ADVANCE(ATTEMPT, A)` |
| `attempt.cleaning` | `ADVANCE(ATTEMPT, A)` |
| `attempt.cleanup_progressed` | `ADVANCE(ATTEMPT, A)` |
| `attempt.succeeded` | `ADVANCE(ATTEMPT, A)` |
| `attempt.failed` | `ADVANCE(ATTEMPT, A)` |
| `attempt.cancelled` | `ADVANCE(ATTEMPT, A)` |
| `attempt.timed_out` | `ADVANCE(ATTEMPT, A)` |
| `attempt.policy_violated` | `ADVANCE(ATTEMPT, A)` |
| `attempt.lease_expired` | `ADVANCE(ATTEMPT, A)` |
| `attempt.lost` | `ADVANCE(ATTEMPT, A)` |
| `attempt.fenced` | `ADVANCE(ATTEMPT, A)` |
| `attempt.rejected` | `ADVANCE(ATTEMPT, A)` |
| `attempt.assurance_evaluated` | `ADVANCE(ATTEMPT, A)`, `ADVANCE(JOB, J)` |
| `lease.offered` | `CREATE(LEASE, L)`, `ADVANCE(WORKER_SESSION, S)`, `ADVANCE(ATTEMPT, A)` |
| `lease.claimed` | `ADVANCE(WORKER_SESSION, S)`, `ADVANCE(ATTEMPT, A)`, `ADVANCE(LEASE, L)` |
| `lease.heartbeat_accepted` | `ADVANCE(LEASE, L)` |
| `lease.renewed` | `ADVANCE(LEASE, L)` |
| `lease.released` | `ADVANCE(WORKER_SESSION, S)`, `ADVANCE(JOB, J)`, `ADVANCE(ATTEMPT, A)`, `ADVANCE(LEASE, L)` |
| `lease.revoked` | `ADVANCE(WORKER_SESSION, S)`, `ADVANCE(JOB, J)`, `ADVANCE(ATTEMPT, A)`, `ADVANCE(LEASE, L)` |
| `lease.expired` | `ADVANCE(WORKER_SESSION, S)`, `ADVANCE(JOB, J)`, `ADVANCE(ATTEMPT, A)`, `ADVANCE(LEASE, L)` |
| `lease.fenced` | `ADVANCE(WORKER_SESSION, S)`, `ADVANCE(JOB, J)`, `ADVANCE(ATTEMPT, A)`, `ADVANCE(LEASE, L)` |
| `lease.tombstone_republished` | `ADVANCE(LEASE, L)` |
| `lease.message_rejected` | `ADVANCE(LEASE, L)` |
| `log.chunk_committed` | `ADVANCE(LOG_STREAM, G)` |
| `log.chunk_rejected` | `ADVANCE(LOG_STREAM, G)` |
| `log.truncated` | `ADVANCE(LOG_STREAM, G)` |
| `log.closed` | `ADVANCE(LOG_STREAM, G)` |

There are exactly 73 base rows. A non-null `recovery_action_binding` adds
exactly one `EQUAL(RECOVERY, R)` entry unless the base row already names `R`;
phase-transition and Recovery control events have a null binding and receive
no augmentation. For `attempt.stop_latched`, “already advanced” is true
exactly when replay finds an earlier event with the same
`transition_cause.effective_sequence` whose exact row contains
`ADVANCE(JOB, J)`; no process-local flag participates. The event Schema
rejects every missing, duplicate, or extra revision entry, a wrong ID or mode,
an unsorted entry array, and any array longer than the fixed v1 maximum of
five. Immutable references not named by a row are validated through their
Sigils and relationships but do not create optional `EQUAL` entries.

A non-null `recovery_action_binding` has exactly `recovery_id`, `phase`,
`action_set_sigil`, and `action_ordinal`. It must identify the unique frozen
action whose target event ID, sequence, type, entity, expected revision, and
prerequisites match this event. A phase-transition event itself uses `null`.

The exact v1 `event_type` enum is:

```text
executor.epoch_started
executor.clock_uncertain
executor.clock_restored
recovery.started
recovery.action_set_rebased
recovery.phase_advanced
recovery.completed
worker.definition_registered
worker.enabled
worker.draining
worker.quarantined
worker.retired
worker_session.registered
worker_session.ready
worker_session.draining
worker_session.offline
worker_session.quarantined
worker_session.closed
worker_session.heartbeat_accepted
worker_session.message_rejected
job.submitted
job.queued
job.attempt_allocated
job.budget_settled
job.retry_scheduled
job.retry_ready
job.stop_latched
job.cancellation_observed
job.assurance_evaluated
job.succeeded
job.failed
job.cancelled
job.timed_out
job.policy_violated
storage_root.hold_release_observed
job.message_rejected
attempt.authorization_bound
attempt.preflight_started
attempt.preflight_progressed
attempt.preflight_passed
attempt.starting
attempt.running
attempt.result_accepted
attempt.result_rejected
attempt.draining
attempt.stop_latched
attempt.stop_progressed
attempt.cleaning
attempt.cleanup_progressed
attempt.succeeded
attempt.failed
attempt.cancelled
attempt.timed_out
attempt.policy_violated
attempt.lease_expired
attempt.lost
attempt.fenced
attempt.rejected
attempt.assurance_evaluated
lease.offered
lease.claimed
lease.heartbeat_accepted
lease.renewed
lease.released
lease.revoked
lease.expired
lease.fenced
lease.tombstone_republished
lease.message_rejected
log.chunk_committed
log.chunk_rejected
log.truncated
log.closed
```

The payload branches use these closed reusable objects, each published under
its printed name in `execution-journal-event/1.0#/$defs`:

- `transition_cause` has exactly `code`, `trigger_kind`,
  `trigger_event_id`, `effective_sequence`, and `evidence_sigil`.
  `trigger_kind` is `PRIOR_EVENT`, `CURRENT_REQUEST`, `DUE_DEADLINE`, or
  `RECOVERY_DERIVATION`; the event ID and sequence identify the prior event
  for `PRIOR_EVENT` and the enclosing event itself for the other three.
  `trigger_event_id` is never null: the enclosing event ID and sequence are
  assigned before Sigil computation, so a request, deadline, or recovery
  trigger binds its own event ID and sequence without a circular Sigil;
  a `RECOVERY_DERIVATION` cause uses its action set's
  `derived_through_event_sigil` as `evidence_sigil`, never the still-circular
  action-set or set-binding-event Sigil;
- `transition_cause.code` is exactly one of `COMPLETION_ESTABLISHED`,
  `CANCEL_REQUESTED`,
  `JOB_DEADLINE`, `ATTEMPT_DEADLINE`, `HEARTBEAT_TIMEOUT`,
  `LEASE_CLAIM_EXPIRED`, `LEASE_ACTIVE_EXPIRED`, `LEASE_REVOKED`,
  `RECOVERY_FENCE`, `CLOCK_UNCERTAIN`, `EXECUTOR_EPOCH_CHANGED`,
  `SESSION_CHANNEL_LOST`, `POLICY_VIOLATION`, `ADMISSION_INVALID`,
  `PREFLIGHT_REJECTED`, `START_FAILED`, `COMPUTATION_FAILED`,
  `VALIDATION_FAILED`,
  `RESULT_CONFLICT`, `RESULT_REQUIREMENT_FAILED`,
  `OUTPUT_VALIDATION_FAILED`, `TERMINAL_SOURCE_RETENTION_FAILED`,
  `TERMINATION_FAILED`, `CLEANUP_FAILED`,
  `LOST_OWNERSHIP`, `ASSURANCE_UNMET`, `ASSURANCE_UNVERIFIABLE`,
  `BUDGET_EXHAUSTED`, `RETRY_EXHAUSTED`, `ATTEMPT_NONRETRYABLE`,
  `ATTEMPT_REJECTED`, `FATAL_INFRASTRUCTURE`, or `INTEGRITY_FAILURE`;
  `COMPLETION_ESTABLISHED` is valid only for `attempt.succeeded` or
  `job.succeeded`, uses `PRIOR_EVENT`, and identifies the exact
  `RESULT_ACCEPTED` or `NO_RESULT` completion-anchor event and sequence;
- `budget_vector` has exactly `attempts`, `cpu_time_seconds`,
  `storage_bytes_written`, `output_bytes`, `log_bytes`, `process_starts`,
  `network_egress_bytes`, and `network_requests`;
- `storage_root_binding` has exactly `root_kind`, `job_id`, `attempt_id`,
  `storage_root_manifest_id`, `storage_root_manifest_sigil`,
  `reference_set_id`, `reference_set_sigil`, `hold_id`, and
  `hold_set_event`. `root_kind` is `JOB_INPUT`, `ATTEMPT_INPUT`,
  or `ATTEMPT_OUTPUT`; `ACTIVE_CONTROL` is not a v1 value. IDs are bounded
  operational strings and `reference_set_sigil` is a Sigil. `JOB_INPUT`
  requires null `attempt_id`; both Attempt kinds require a non-null Attempt
  ID. In every event or State container, `job_id` must equal the owning Job
  and a non-null `attempt_id` must equal the owning Attempt whose immutable
  parent is that Job. `hold_set_event` has exactly `journal_id`, `event_id`,
  `sequence`, and `event_sigil`, using the RFC-0013 `EventRef` types. The
  manifest pair resolves the exact ESM whose owner and planned Event IDs equal
  this root. The member shape is byte-for-byte compatible with RFC-0013
  `ExecutionStorageRoot`, while this v1 enum is its closed admissible subset;
- `result_binding` is exactly one of `NONE {kind}`,
  `ACCEPTED {kind, result_sigil, disposition_event_id,
  disposition_event_sigil, disposition_sequence}`, or
  `REJECTED {kind, message_sigil, disposition_event_id,
  disposition_event_sigil, disposition_sequence, reason_codes}`;
- `completion_anchor_binding` is exactly
  `NOT_ESTABLISHED {kind}`,
  `RESULT_ACCEPTED {kind, event_id, event_sigil, sequence, result_sigil}`, or
  `NO_RESULT {kind, event_id, event_sigil, sequence,
  process_exit_observation_sigil}`. `RESULT_ACCEPTED` identifies
  `attempt.result_accepted`; `NO_RESULT` identifies `attempt.draining` and
  its process-exit observation Sigil is non-null;
- `worker_session_binding` is exactly `NONE {kind}` or
  `BOUND {kind, worker_id, worker_binding_sigil, worker_session_id,
  worker_session_binding_sigil}`. `NONE` is legal only when the Attempt never
  received a Lease offer; an `OFFERED` or later Lease requires `BOUND` even
  when it was never claimed;
- `first_stop_or_fence_binding` is exactly `NONE {kind}` or
  `PRESENT {kind, event_id, event_type, event_sigil, effective_sequence}`. It
  is the earliest applicable authority-ineligibility trigger known through
  the selected Attempt terminal event. A later Job-only stop is preserved by
  the Job terminal `transition_cause` and never rewrites this frozen binding.
  For a no-Attempt Outcome, the direct binding is instead derived from the
  Job's first stop trigger;
- `storage_observation_binding` is exactly `NOT_APPLICABLE {kind}` or
  `FROZEN {kind, storage_journal_id, through_sequence,
  through_event_sigil, output_storage_observation_set_id,
  output_storage_observation_set_sigil}`. `NOT_APPLICABLE` is legal only for
  a terminal Job with no allocated Attempt. `FROZEN` is mandatory for every
  terminal Attempt; its ID and Sigil resolve exactly one
  `execution-output-storage-observation-set/1.0`, and its three prefix fields
  equal that document's `storage_event.journal_id`, `sequence`, and
  `event_sigil` byte-for-byte;
- `selected_attempt_binding` is exactly `NONE {kind}` or
  `SELECTED {kind, attempt_id, attempt_binding_sigil,
  attempt_terminal_event_id, attempt_terminal_event_sigil,
  attempt_authorization_state, worker_session_binding, result_binding,
  completion_anchor_binding,
  first_stop_or_fence_binding, storage_observation_binding}`. `NONE` is legal
  iff no Attempt was allocated; otherwise `SELECTED` names the terminal
  highest-retry-ordinal Attempt available when the final Job decision is
  committed;
- `attempt_summary`, used by each `attempt_summaries` entry, has exactly
  `attempt_id`,
  `attempt_binding_sigil`, `retry_ordinal`, `terminal_state`,
  `terminal_event_id`, `terminal_event_sigil`, `worker_session_binding`,
  `attempt_authorization_requirement`,
  `attempt_authorization_state`,
  `budget_settlement_event_sigil`, and
  `assurance_evaluation_event_sigil`, sorted by retry ordinal. It is a
  `FINAL` record even though it has no redundant `kind`: both trailing Sigils
  are non-null, the terminal event precedes budget settlement, and settlement
  precedes assurance evaluation. No pending or partially populated
  `attempt_summary` branch exists;

Each summary's `attempt_authorization_requirement` is copied byte-for-byte
from its immutable Attempt. A `NONE` requirement permits only state `NONE`.
A `REQUIRED` requirement permits a non-selected failed Attempt to retain
`PENDING`; any `BOUND` state must resolve its complete subject and binding,
must have `authorization_subject.effects` equal to the requirement's effects,
and must be unique to that Attempt. The selected successful Attempt must be
exactly `NONE/NONE` or `REQUIRED/BOUND`. A Receipt or subject reused across
Attempts, substituted from Specification approval, or bound to different
effects invalidates the terminal Job event. The selected binding's
`attempt_authorization_state` equals the matching summary's state
byte-for-byte; its requirement is obtained only from that matching summary,
never inferred from the state.

- `lease_terminal_binding` is exactly `NONE {kind}` or
  `TERMINAL {kind, lease_id, lease_state, terminal_event_id,
  terminal_event_sigil, final_fence_floor, tombstone_event_sigil}`. `NONE` is
  legal iff no Lease was ever offered to the Attempt; otherwise the Lease must
  already be terminal;
- `final_fence_binding` is exactly
  `NO_ATTEMPT {kind, final_fence_floor}`,
  `ASSIGNED_NO_LEASE {kind, final_fence_floor, attempt_id,
  attempt_terminal_event_sigil}`, or
  `TOMBSTONE {kind, final_fence_floor, lease_id,
  lease_terminal_event_sigil, tombstone_event_sigil}`. `NO_ATTEMPT` requires
  floor zero; `ASSIGNED_NO_LEASE` requires the last allocated generation and
  proves that Attempt never received a Lease; `TOMBSTONE` requires the
  terminal Lease event's tombstone generation to equal the final floor;
- `terminal_source_binding` is exactly `NOT_APPLICABLE {kind}`,
  `VERIFIED {kind, crucible_base_identity, crucible_base_sigil,
  terminal_source_identity, terminal_source_sigil, storage_blob,
  retention_policy_sigil, file_count, byte_count, storage_status,
  verifier_evidence_sigil}`, or
  `QUARANTINED {kind, crucible_base_identity, crucible_base_sigil,
  terminal_source_identity, terminal_source_sigil, storage_blob,
  retention_policy_sigil, file_count, byte_count, storage_status,
  verifier_evidence_sigil,
  reason_codes}`. In `VERIFIED`, every identity/Sigil is non-null,
  `storage_status` is constant `DURABLE_VERIFIED`, and counts are within the
  predeclared bounds. In `QUARANTINED`, Base, policy, and verifier bindings
  remain non-null, `storage_status` is constant `QUARANTINED`, and
  `reason_codes` is a non-empty sorted set drawn exactly from
  `BASE_BINDING_INVALID`, `SOURCE_ABSENT`, `SOURCE_PARTIAL`,
  `SOURCE_MUTABLE`, `SOURCE_IDENTITY_MISMATCH`, `FILE_LIMIT_EXCEEDED`,
  `BYTE_LIMIT_EXCEEDED`, `STORAGE_UNVERIFIED`,
  `RETENTION_POLICY_MISMATCH`, and `VERIFIER_UNAVAILABLE`.
  `terminal_source_identity`, `terminal_source_sigil`, and `storage_blob` are
  either all non-null or all null; null is allowed only when no
  content-identified source was retained and then both counts are zero. When
  non-null they resolve one exact `benchwork-source-tree/1.0` and its
  deterministic bundle as defined above; and
- `attempt_terminal_evidence` has exactly `transition_cause`,
  `computation_status`, `worker_status`, `process_termination_status`,
  `handle_revocation_status`, `cleanup_status`,
  `mutable_resource_isolation_status`, `output_publication_status`,
  `quarantine_status`, `termination_evidence_sigil`,
  `handle_disposition_evidence_sigil`, `cleanup_summary_sigil`,
  `quarantine_evidence_sigil`,
  `log_closure_sigil`, `output_closure_sigil`, `result_binding`,
  `attempt_authorization_state`,
  `completion_anchor_binding`,
  `worker_session_binding`, `lease_terminal_binding`,
  `first_stop_or_fence_binding`, `storage_observation_binding`,
  `accounting_capture_event_id`, `accounting_capture_event_sigil`,
  `control_evidence_set_binding`, `quarantine_binding_set_binding`,
  `terminalization_storage_manifest_binding`, `output_root_protection`,
  `assurance_input_set_sigil`, and `terminal_source_binding`. The four
  evidence/summary Sigils, both closure Sigils, both accounting bindings, both
  terminalization-set bindings, ESM/protection bindings, and the assurance
  input-set Sigil are
  non-null for every allocated Attempt, including a preflight rejection;
  evidence that a facility never became active is still explicit evidence
  rather than null. Both set bindings are `FROZEN`. Its
  `storage_observation_binding` is always `FROZEN`; the referenced observation
  document's owner, `result_binding`, both closure Sigils, both
  terminalization-set bindings, the ESM/protection bindings, and
  `terminal_source_binding` are byte-for-byte equal to this terminal evidence
  and its owning Attempt. Any mismatch invalidates the terminal event rather
  than being repaired from the observation-set Sigil.

The terminal payload's `output_storage_roots` is empty exactly when
`output_root_protection.kind == NO_HOLD`; otherwise it contains exactly the
one `HELD.storage_root_binding`. Thus `ACCOUNTING_CAPTURED` proves protection
before the terminal Event activates the same root, and the terminal Event
cannot substitute another ESM, Reference Set, hold, or Storage prefix.

The terminal authorization state is the exact replayed value. `PENDING` is
legal only for an Attempt that never passed preflight and terminalized through
a closed rejection or stop path; it is never acceptance-eligible.
Every `SUCCEEDED` Attempt whose immutable requirement is `REQUIRED` carries
the one valid `BOUND` subject and Receipt, while a `NONE` requirement carries
state `NONE`. The terminal event cannot omit or abbreviate either complete
`BOUND` object.

The eight terminal-status fields are closed enums:

| Field | Exact values |
| --- | --- |
| `computation_status` | `NOT_STARTED`, `COMPLETED`, `FAILED`, `UNKNOWN` |
| `worker_status` | `NOT_REPORTED`, `COMPLETED`, `FAILED`, `CANCELLED`, `TIMED_OUT`, `LOST` |
| `process_termination_status` | `NOT_STARTED`, `EXITED`, `TERMINATED`, `QUARANTINED`, `UNVERIFIABLE` |
| `handle_revocation_status` | `NOT_APPLICABLE`, `REVOKED`, `FENCED`, `QUARANTINED`, `UNVERIFIABLE` |
| `cleanup_status` | `NOT_APPLICABLE`, `VERIFIED`, `PARTIAL`, `FAILED`, `QUARANTINED` |
| `mutable_resource_isolation_status` | `NOT_APPLICABLE`, `VERIFIED_ISOLATED`, `QUARANTINED`, `UNVERIFIED` |
| `output_publication_status` | `NOT_APPLICABLE`, `VERIFIED`, `QUARANTINED`, `FAILED` |
| `quarantine_status` | `NOT_REQUIRED`, `COMPLETE`, `PARTIAL`, `FAILED` |

The assurance claim's `termination_status` uses the
`process_termination_status` enum and its `cleanup_status` uses the same
cleanup enum. These facts remain independent of the Attempt terminal-state
enum. Any `UNVERIFIABLE`, `PARTIAL`, or `FAILED` termination, handle,
cleanup, or mutable-resource fact that leaves authority or exclusivity
ambiguous requires the corresponding resource to be represented by
`quarantine_status: COMPLETE`; otherwise terminalization is illegal.
Each status row is also published as the same-named scalar `$def` in
`execution-journal-event/1.0`; consumers import those component definitions
without importing the enclosing terminal-evidence object.

`NOT_APPLICABLE` terminal source is required when the Specification branch is
`NONE`; `VERIFIED` or `QUARANTINED` is required for `CODE_MODIFICATION`.
If a `CODE_MODIFICATION` Job terminalizes without any Attempt, its Job
terminal event uses `QUARANTINED` with the predeclared Base and retention
policy, null terminal-source identity and Sigil, zero counts,
null storage BlobRef,
`SOURCE_ABSENT`, and non-null verifier evidence; `NOT_APPLICABLE` remains
forbidden. For an allocated Attempt, the Job copy is byte-for-byte equal to
that Attempt's frozen branch.
Every `SUCCEEDED` Attempt has an established completion anchor:
`RESULT_ACCEPTED` for `REQUIRED` or an accepted `OPTIONAL` result, and
`NO_RESULT` for a permitted absent result. `FORBIDDEN` can use only
`NO_RESULT`. The `result_binding`, completion anchor, selected Attempt, and
Job-terminal copies must agree exactly. First stop-or-fence ordering is always
compared to `completion_anchor_binding.sequence`, so no-result completion has
the same deterministic race semantics as accepted-result completion.

The remaining event payload scalar domains are exact:

- `startup_reason` is `INITIAL_START`, `PROCESS_RESTART`,
  `RECOVERY_RESTART`, or `ADMINISTRATIVE_RESTART`;
- `monotonic_status` is `RESET`, `UTC_DIVERGED`, `UNAVAILABLE`, or
  `SUSPEND_UNPROVABLE`;
- `message_kind` is `WORKER_SESSION_REGISTRATION`,
  `WORKER_SESSION_HEARTBEAT`, `LEASE_CLAIM`, `LEASE_HEARTBEAT`,
  `LEASE_RENEWAL`, `LEASE_RELEASE`, or `CANCEL_REQUEST`;
- `attempt.preflight_progressed.step` is `TASK_BINDINGS_VERIFIED`,
  `POLICIES_VERIFIED`, `BASE_INPUTS_VERIFIED`, `BACKEND_VERIFIED`,
  `MATERIALIZATION_CREATED`, or `OUTPUT_NAMESPACE_CREATED`;
- `attempt.stop_progressed.step` is `COOPERATIVE_STOP_REQUESTED`,
  `FORCE_TERMINATION_DUE`, `PROCESS_TREE_TERMINATED`, or
  `HANDLES_REVOKED`; and
- `attempt.cleanup_progressed.step` is `LOGS_CLOSED`, `OUTPUTS_CLOSED`,
  `TERMINATION_VERIFIED`, `RESOURCES_CLEANED`, `QUARANTINE_VERIFIED`, or
  `ACCOUNTING_CAPTURED`. The first two are legal in `DRAINING`; the first
  five are legal as applicable in `STOPPING` or `CLEANING`;
  `ACCOUNTING_CAPTURED` is legal only in `CLEANING` and only as the final
  metered progress step. Its `remaining_resource_ids` is empty and its
  `finalization_bindings` carries the already durable frozen CES, QBS, output
  ESM, and output-root protection bindings. Every earlier branch uses
  `finalization_bindings: NONE`. A step is
  recorded at most once per Attempt.

`worker_session.message_rejected` restricts `message_kind` to the two
Worker-Session values, `job.message_rejected` requires `CANCEL_REQUEST`, and
`lease.message_rejected` restricts it to the four Lease values. Result and
log rejection events have fixed kinds by event type and therefore do not
repeat a `message_kind` member.

Unless a field has a smaller enum in this RFC, every machine
`reason_code`, `reason_codes`, or `terminal_reason` value is drawn from the
exact `transition_cause.code` enum plus
`ADMIN_DRAIN`, `ADMIN_RETIRE`, `DEFINITION_SUPERSEDED`,
`CAPABILITY_REVOKED`, `VERIFICATION_FAILED`, `CONTROL_CHANNEL_LOST`,
`WORKER_SHUTDOWN`, `BACKEND_CLOSE_FAILED`, `MALFORMED_MESSAGE`,
`UNKNOWN_SCHEMA`, `INVALID_SIGIL`, `WRONG_ENTITY`, `WRONG_SESSION`,
`WRONG_EPOCH`, `STALE_REVISION`, `CONFLICTING_DUPLICATE`, `SEQUENCE_GAP`,
`STATE_INELIGIBLE`, `CREDENTIAL_INVALID`, `LEASE_NOT_CURRENT`,
`FENCE_STALE`, `DEADLINE_ALREADY_DUE`, `MESSAGE_TOO_LARGE`,
`LIMIT_EXCEEDED`, `RESULT_SCHEMA_INVALID`, `OUTPUT_SCHEMA_INVALID`,
`EVIDENCE_MISSING`, `EVIDENCE_INVALID`, `PROFILE_MISMATCH`,
`CONFORMANCE_SUITE_MISMATCH`, `CLAIM_INVALID`, `ACCOUNTING_PARTIAL`,
`ACCOUNTING_UNAVAILABLE`, `RESOURCE_AMBIGUOUS`, and
`NO_ATTEMPT_ALLOCATED`. Reason arrays are unique,
unsigned-ASCII sorted, and non-empty except that a `CLAIMED` assurance
evaluation has an empty array. The no-Attempt Job evaluation has exactly
`[NO_ATTEMPT_ALLOCATED]`. The terminal-source reason array remains restricted
to its smaller enum above. Actor-supplied cancellation `reason` is instead a
required, normalized, bounded 1--1024-byte UTF-8 string and has no authority
outside its request Sigil.

Attempt assurance `evaluation` is exactly `CLAIMED`, `UNMET`, or
`UNVERIFIABLE`; Job assurance adds `NOT_APPLICABLE`. `CLAIMED` requires a
claim Sigil and empty reasons. `UNMET` and `UNVERIFIABLE` require a null claim
Sigil and non-empty reasons. `NOT_APPLICABLE` is legal only for a Job with no
allocated Attempt, uses the fixed reason above, and requires all Attempt and
claim fields null. Budget `usage_status` is exactly `MEASURED`, `PARTIAL`, or
`UNAVAILABLE`; budget exhaustion is exactly `AVAILABLE`, `EXHAUSTED`, or
`EXCEEDED` under the arithmetic rule in `budget_dimension`. Attempt terminal
states are exactly `SUCCEEDED`, `FAILED`, `CANCELLED`, `TIMED_OUT`,
`POLICY_VIOLATION`, `LEASE_EXPIRED`, `LOST`, `FENCED`, and `REJECTED`; Job
terminal states are exactly `SUCCEEDED`, `FAILED`, `CANCELLED`, `TIMED_OUT`,
and `POLICY_VIOLATION`; Lease terminal states are exactly `RELEASED`,
`REVOKED`, `EXPIRED`, and `FENCED`.

Arrays named below are bounded, contain closed entries, and use the canonical
sort key named by their field. The exact event ownership and payload fields
are:

| Event type | State owner and transition | Exact payload members |
| --- | --- | --- |
| `executor.epoch_started` | Executor epoch creation/increment | `prior_epoch`, `new_epoch`, `startup_reason`, `host_identity_sigil`, `executor_build_binding` |
| `executor.clock_uncertain` | Executor clock gate `TRUSTED -> UNCERTAIN` | `last_trusted_utc`, `detected_utc`, `monotonic_status`, `divergence_seconds`, `affected_lease_ids` |
| `executor.clock_restored` | Executor clock gate `UNCERTAIN -> TRUSTED` | `trusted_time_source_sigil`, `restored_utc`, `fenced_lease_ids`, `new_anchor_evidence_sigil` |
| `recovery.started` | Recovery transaction creation in `STARTED`; Executor sets `active_recovery_id` and closes `RECOVERY_ACTIVE` gate | `recovery_id`, `prior_recovery_id`, `replay_through_sequence`, `replay_through_event_sigil`, `old_epoch`, `new_epoch`, `nonterminal_job_ids`, `nonterminal_attempt_ids`, `nonterminal_lease_ids`, `nonterminal_worker_session_ids`, `initial_action_set_sigil` |
| `recovery.action_set_rebased` | Active Recovery remains in its current phase | `recovery_id`, `phase`, `prior_action_set_sigil`, `replacement_action_set_sigil`, `reason_event_id`, `new_epoch`, `carried_completion_event_ids` |
| `recovery.phase_advanced` | Recovery phase named in payload | `recovery_id`, `from_phase`, `to_phase`, `completed_action_set_sigil`, `next_action_set_sigil`, `completed_entity_ids`, `quarantined_entity_ids` |
| `recovery.completed` | Recovery `FINALIZING -> COMPLETED`; Executor clears `active_recovery_id` and reopens `RECOVERY_ACTIVE` gate | `recovery_id`, `completed_action_set_sigil`, `recovered_state_sigil`, `fence_tombstone_event_ids`, `quarantined_entity_ids`, `resumable_job_ids` |
| `worker.definition_registered` | Worker definition none `-> REGISTERED` | `worker_binding_sigil`, `definition_revision`, `supersedes_worker_binding_sigil` |
| `worker.enabled` | Worker definition `REGISTERED`, `DRAINING`, or `QUARANTINED -> ENABLED` | `worker_binding_sigil`, `verification_evidence_set_sigil` |
| `worker.draining` | Worker definition `ENABLED -> DRAINING` | `reason_code`, `affected_worker_session_ids` |
| `worker.quarantined` | Worker definition `REGISTERED`, `ENABLED`, or `DRAINING -> QUARANTINED` | `reason_codes`, `evidence_set_sigil`, `affected_worker_session_ids` |
| `worker.retired` | Worker definition `REGISTERED`, `ENABLED`, `DRAINING`, or `QUARANTINED -> RETIRED` | `reason_code`, `closed_worker_session_ids` |
| `worker_session.registered` | Worker Session none `-> REGISTERED` | `worker_session_binding_sigil`, `worker_binding_sigil`, `backend_session_identity`, `control_channel_identity_sigil` |
| `worker_session.ready` | Session `REGISTERED -> READY` | `verification_evidence_set_sigil`, `capacity`, `initial_heartbeat_due_at` |
| `worker_session.draining` | Session `READY` or `BUSY -> DRAINING` | `reason_code`, `active_lease_ids` |
| `worker_session.offline` | Session `REGISTERED`, `READY`, `BUSY`, or `DRAINING -> OFFLINE` | `transition_cause`, `last_heartbeat_sequence`, `active_lease_ids` |
| `worker_session.quarantined` | Session `REGISTERED`, `READY`, `BUSY`, or `DRAINING -> QUARANTINED` | `reason_codes`, `evidence_set_sigil`, `active_lease_ids` |
| `worker_session.closed` | Session `REGISTERED`, `READY`, `DRAINING`, `OFFLINE`, or `QUARANTINED -> CLOSED`, with no authoritative Lease | `reason_code`, `terminal_lease_ids`, `backend_close_evidence_sigil` |
| `worker_session.heartbeat_accepted` | Session `READY`, `BUSY`, or `DRAINING`, state-neutral | `heartbeat_message_sigil`, `sequence`, `prior_accepted_sequence`, `received_at`, `next_heartbeat_due_at` |
| `worker_session.message_rejected` | Session state-neutral | `message_kind`, `message_sigil`, `reason_codes`, `historical_disposition_event_id` |
| `job.submitted` | Job none `-> SUBMITTED`; activates its pre-held `JOB_INPUT` roots | `job_binding_sigil`, `start_request_sigil`, `submission_idempotency_key_sigil`, `admission_chronicle_head`, `admission_chronicle_head_evidence`, `deadline_due_at`, `job_budget`, `job_storage_roots` |
| `job.queued` | Job `SUBMITTED -> QUEUED` | `admission_evidence_sigil`, `queue_key` |
| `job.attempt_allocated` | Job `QUEUED -> ACTIVE`; Attempt creation; fence and budget ledgers | `attempt_binding_sigil`, `retry_ordinal`, `fencing_generation`, `prior_fencing_counter`, `resulting_fence_floor`, `budget_reservation`, `resulting_budget_ledger_sigil` |
| `job.budget_settled` | Job `ACTIVE` or `STOPPING` and terminal Attempt, both state-neutral; Job ledger and Attempt settlement binding advance atomically | `attempt_id`, `reservation`, `accounting_capture_event_id`, `accounting_capture_event_sigil`, `usage_status`, `measured`, `charged`, `accounting_started_at`, `accounting_ended_at`, `supervisor_identity`, `accounting_evidence_set_sigil`, `resulting_budget_ledger_sigil` |
| `job.retry_scheduled` | Job `ACTIVE -> RETRY_WAIT` | `preceding_attempt_id`, `terminal_reason`, `eligible_due_at`, `backoff_ordinal`, `post_settlement_budget_ledger_sigil` |
| `job.retry_ready` | Job `RETRY_WAIT -> QUEUED` | `eligible_due_at`, `deadline_check_sigil`, `freshness_evidence_sigil`, `queue_key` |
| `job.stop_latched` | Job `SUBMITTED`, `QUEUED`, `ACTIVE`, or `RETRY_WAIT -> STOPPING` | `transition_cause`, `request_binding`; `request_binding` is `NONE {kind}` or `CANCELLATION {kind, cancellation_request_id, idempotency_key_sigil, cancel_request_sigil, actor_sigil, host_provenance_sigil, reason, expected_job_revision}` |
| `job.cancellation_observed` | Terminal Job state-neutral | `cancellation_request_id`, `idempotency_key_sigil`, `cancel_request_sigil`, `actor_sigil`, `host_provenance_sigil`, `reason`, `expected_job_revision`, `terminal_event_id`, `terminal_event_sigil` |
| `job.assurance_evaluated` | Job `ACTIVE` or `STOPPING`, state-neutral | `evaluation`, `attempt_id`, `attempt_assurance_event_sigil`, `assurance_claim_sigil`, `reason_codes`, `evidence_set_sigil`; Attempt fields are null only for `NOT_APPLICABLE`, and claim Sigil is non-null only for `CLAIMED` |
| `job.succeeded`, `job.failed`, `job.cancelled`, `job.timed_out`, `job.policy_violated` | Job matching source in the Job table `->` matching terminal state; inactivates its `JOB_INPUT` and every child `ATTEMPT_OUTPUT` root | `transition_cause`, `attempt_summaries`, `selected_attempt_binding`, `completion_anchor_binding`, `first_stop_or_fence_binding`, `job_assurance_event_sigil`, `budget_ledger_sigil`, `final_fence_binding`, `cleanup_summary_sigil`, `storage_observation_binding`, `terminal_source_binding`, `output_hold_release_schedules` |
| `storage_root.hold_release_observed` | Job state-neutral; proves one owner-terminal or scheduled output execution-hold release | `job_id`, `release_binding`, `storage_release_event` |
| `job.message_rejected` | Job state-neutral | `message_kind`, `message_sigil`, `reason_codes`, `historical_disposition_event_id` |
| `attempt.authorization_bound` | Attempt lifecycle `CREATED`, authorization `PENDING -> BOUND`, lifecycle-state-neutral | `authorization_subject`, `attempt_authorization_binding` |
| `attempt.preflight_started` | Attempt `CREATED -> PREFLIGHTING` | `preflight_plan_sigil`, `freshness_evidence_sigil` |
| `attempt.preflight_progressed` | Attempt `PREFLIGHTING`, state-neutral | `step`, `progress_evidence_sigil` |
| `attempt.preflight_passed` | Attempt `PREFLIGHTING -> READY`; activates only its pre-held `ATTEMPT_INPUT` roots | `materialization_identity`, `materialization_sigil`, `preflight_evidence_set_sigil`, `input_storage_roots` |
| `attempt.starting` | Attempt `LEASED -> STARTING` | `backend_start_handle_sigil`, `start_request_sigil` |
| `attempt.running` | Attempt `STARTING -> RUNNING` | `process_tree_identity`, `process_tree_evidence_sigil`, `side_effect_handle_set_sigil` |
| `attempt.result_accepted` | Attempt `RUNNING`, state-neutral | `result_sigil`, `lease_revision`, `fence_tuple`, `received_at`, `validation_evidence_sigil` |
| `attempt.result_rejected` | Attempt state-neutral; a first disposition only in `RUNNING`, or a novel late/conflicting message in `DRAINING`, `STOPPING`, `CLEANING`, or any terminal Attempt state | `message_sigil`, `claimed_result_sigil`, `received_at`, `reason_codes`, `historical_disposition_event_id` |
| `attempt.draining` | Attempt `RUNNING -> DRAINING` | `result_binding`, `process_exit_observation_sigil` |
| `attempt.stop_latched` | Attempt `CREATED`, `PREFLIGHTING`, `READY`, `LEASED`, `STARTING`, `RUNNING`, or `DRAINING -> STOPPING`; parent Job ordering projection advances when no event in the same due chain already advanced it | `transition_cause`, `grace_due_at` |
| `attempt.stop_progressed` | Attempt `STOPPING`, state-neutral | `step`, `termination_evidence_sigil`, `remaining_handle_ids` |
| `attempt.cleaning` | Attempt `DRAINING` or `STOPPING -> CLEANING` | `log_closure_sigil`, `output_closure_sigil`, `termination_evidence_sigil`, `quarantine_plan_sigil`, `terminal_source_binding` |
| `attempt.cleanup_progressed` | Attempt `DRAINING`, `STOPPING`, or `CLEANING`, state-neutral finalization progress | `step`, `cleanup_evidence_sigil`, `remaining_resource_ids`, `finalization_bindings`; `NONE {kind}` except `ACCOUNTING_CAPTURED`, which requires `FROZEN {kind, control_evidence_set_binding, quarantine_binding_set_binding, terminalization_storage_manifest_binding, output_root_protection}` |
| `attempt.succeeded`, `attempt.failed`, `attempt.cancelled`, `attempt.timed_out`, `attempt.policy_violated`, `attempt.lease_expired`, `attempt.lost`, `attempt.fenced`, `attempt.rejected` | Attempt `CLEANING ->` matching terminal state; inactivates its `ATTEMPT_INPUT` roots and activates only its pre-held `ATTEMPT_OUTPUT` roots | `attempt_terminal_evidence`, `fencing_generation`, `final_fence_floor`, `output_storage_roots` |
| `attempt.assurance_evaluated` | Settled terminal Attempt state-neutral; Attempt assurance and parent Job final summary/current-attempt fields advance atomically | `evaluation`, `assurance_claim_sigil`, `reason_codes`, `evidence_set_sigil`; claim Sigil is non-null only for `CLAIMED` |
| `lease.offered` | Lease none `-> OFFERED` | `lease_binding_sigil`, `credential_digest`, `claim_due_at`, `initial_expiry_due_at`, `maximum_expiry_due_at` |
| `lease.claimed` | Lease `OFFERED -> ACTIVE`; Attempt `READY -> LEASED`; Session capacity updated | `credential_proof_sigil`, `claimed_at`, `next_heartbeat_due_at`, `session_capacity_after` |
| `lease.heartbeat_accepted` | Active Lease state-neutral | `heartbeat_message_sigil`, `sequence`, `prior_accepted_sequence`, `received_at`, `next_heartbeat_due_at`, `resource_sample_sigil` |
| `lease.renewed` | Lease `ACTIVE -> ACTIVE` | `renewal_request_sigil`, `prior_expiry_due_at`, `new_expiry_due_at`, `renewal_counter` |
| `lease.released` | Lease `ACTIVE -> RELEASED`; Session capacity and Job fence floor updated | `release_evidence_sigil`, `prior_fence_floor`, `tombstone_generation`, `tombstone_publication_sigil`, `session_capacity_after` |
| `lease.revoked` | Lease `OFFERED` or `ACTIVE -> REVOKED`; Session capacity and Job fence floor updated | `transition_cause`, `prior_fence_floor`, `tombstone_generation`, `tombstone_publication_sigil`, `session_capacity_after` |
| `lease.expired` | Lease `OFFERED` or `ACTIVE -> EXPIRED`; Session capacity and Job fence floor updated | `deadline_kind`, `due_at`, `prior_fence_floor`, `tombstone_generation`, `tombstone_publication_sigil`, `session_capacity_after` |
| `lease.fenced` | Lease `OFFERED` or `ACTIVE -> FENCED`; Session capacity and Job fence floor updated | `transition_cause`, `prior_fence_floor`, `tombstone_generation`, `tombstone_publication_sigil`, `session_capacity_after` |
| `lease.tombstone_republished` | Terminal Lease state-neutral | `tombstone_generation`, `original_terminal_event_sigil`, `sink_ids`, `publication_evidence_sigil` |
| `lease.message_rejected` | Lease state-neutral | `message_kind`, `message_sigil`, `reason_codes`, `historical_disposition_event_id` |
| `log.chunk_committed` | Open log stream state-neutral append | `log_stream_id`, `chunk_record_sigil`, `stream`, `sequence`, `blob_sigil`, `captured_bytes_after` |
| `log.chunk_rejected` | Log stream state-neutral | `log_stream_id`, `stream`, `sequence`, `message_sigil`, `reason_codes`, `historical_disposition_event_id` |
| `log.truncated` | Open log stream state-neutral latch | `log_stream_id`, `stream`, `limit_bytes`, `captured_bytes`, `dropped_bytes`, `overflow_behavior` |
| `log.closed` | Log stream open `-> CLOSED` | `log_stream_id`, `stream`, `final_sequence`, `captured_bytes`, `dropped_bytes`, `stream_set_sigil` |

Every field shown in the payload column is required. Fields explicitly
described as nullable remain present with `null`; no other null or conditional
member is allowed. In addition, `prior_epoch` is null only for the first
epoch; `recovery.started.old_epoch` is zero, not null, only when no prior
epoch exists. `prior_recovery_id` is null only when no earlier Recovery exists,
`supersedes_worker_binding_sigil` only at Worker definition revision zero,
heartbeat prior sequence only at sequence zero,
`claimed_result_sigil` only when a malformed message has no valid claimed
Sigil, `process_exit_observation_sigil` only when no exit was observed, and
`historical_disposition_event_id` only when no prior disposition exists.
`final_sequence` is null only for an empty log stream. In a quarantined
terminal-source branch, source identity, Sigil, and storage BlobRef are null only when no
content-identified source could be retained; counts remain zero and the
reason is explicit. A Job terminal event's `storage_observation_binding`,
`terminal_source_binding`, `completion_anchor_binding`,
`first_stop_or_fence_binding`, and any selected Attempt's copies must be
exactly equal. A terminal Attempt's storage branch is always `FROZEN`, its
resolver pair must validate before replay applies the event, and the
observation record's owner, terminal inputs, full RFC-0013 EventRef, and State
Sigil must satisfy the equalities above. With no Attempt, selection is
`NONE`, completion is `NOT_ESTABLISHED`, storage is `NOT_APPLICABLE`, final
fence is `NO_ATTEMPT`, and first stop is derived from the Job stop trigger.
`worker_session.message_rejected`,
`job.message_rejected`, `attempt.result_rejected`,
`lease.message_rejected`, and `log.chunk_rejected` preserve a new rejected
message. Exact duplicate replay returns the referenced historical disposition
and appends no event.

Adding an event type, payload member, enum value, owner, or transition meaning
requires a new Schema version and an explicit replay compatibility rule.

### Append and durability

Before acknowledging a state-changing operation, the Executor must:

1. hold the journal's exclusive writer lock;
2. replay or validate the current Head and relevant entity revisions;
3. evaluate due deadlines before the requested operation;
4. validate the complete event and transition;
5. make every referenced immutable payload and its exact resolver entry
   durable;
6. append the event bytes atomically or through a framed record whose checksum
   detects a partial tail;
7. make the appended event durable;
8. atomically replace the journal-head cache; and
9. only then release authority, a Lease credential, renewal response, result
   disposition, or API success to the caller.

The Head is a cache, not authority. A missing or stale Head is rebuilt from the
journal. A Head that points beyond or conflicts with the verified chain is an
integrity failure. Filesystem rename or write completion without required
durability is not sufficient evidence after a Host crash.

The `0.4` reference runtime uses one writer lock and one Executor epoch at a
time. A second coordinator that cannot acquire the lock must not schedule,
renew, cancel, recover, or terminalize work. This RFC does not define
distributed consensus.

### Replay

Replay starts from the first event and:

1. validates every event against its exact installed Schema and resolves each
   immutable payload by every ID-and-Sigil field carried by that event;
2. requires the expected journal ID, contiguous sequence, and hash chain;
3. recomputes every event Sigil;
4. requires a valid initial `executor.epoch_started`;
5. validates entity identity, immutable binding, revision, relationship, and
   idempotency constraints;
6. applies only the legal state-machine transitions in this RFC;
7. validates that at most one non-terminal Attempt exists per Job, at most one
   Lease exists per Attempt, every `LEASED` or later Attempt has exactly one,
   fencing generations increase, Worker Session capacity is not exceeded, and
   terminal objects never transition;
8. reconstructs durable due times, in-process-anchor prerequisites, Worker
   definitions and Sessions, budget reservations and settlements, log
   sequence and limits, historical result dispositions, cleanup, terminal
   source retention, output-storage-observation references, assurance, retry,
   and recovery state; and
9. validates the resulting projection against `execution-state/1.0`.

The replayed projection must be byte-for-byte deterministic under canonical
JSON for the same journal and installed Schema set. Queue ordering and
deterministic retry eligibility are derived from committed events, not current
directory order or wall-clock iteration.

Unknown versions or event types, an invalid Sigil, missing middle event,
partial non-tail record, illegal transition, revision mismatch, fence
regression, duplicate identity, impossible relationship, or broken referenced
payload stops replay at the last verified prefix and places the Executor in
integrity-failure mode. It may inspect and export evidence but may not schedule,
renew, accept results, or silently skip, reorder, repair, or infer an event.
For a `FROZEN` storage observation, replay resolves the exact observation-set
ID and Sigil, replays RFC-0013 through its complete EventRef, recomputes the
State Sigil and every member/Replica selector, and compares all terminal
bindings byte-for-byte. It never searches for a record by Sigil alone or
substitutes a later Replica.

A single clearly partial final frame may be quarantined only by an explicit
repair procedure defined in a later integrity RFC. Automatic truncation is
forbidden. The `0.4` reference runtime retains the complete journal and all
terminal Attempt events. Checkpoints or compacted projections may accelerate
observation only after verifying their prefix Event Sigil; they never replace
the journal or authorize deletion of failed history.

## Restart and recovery

Executor startup and runtime clock uncertainty use the same journaled Recovery
transaction. At most one Recovery transaction is active; a completed
transaction remains terminal history but does not prevent a later fresh
`recovery_id`. Its states and only legal transitions are:

| From | To | Event and committed postcondition |
| --- | --- | --- |
| no active Recovery | `STARTED` | `recovery.started`; replay prefix, prior completed Recovery if any, old/new epoch, all non-terminal entity sets, and the durable `STARTED` action-set Sigil are bound, and every authority-creating operation is gated off. |
| `STARTED`, `FENCING`, `RECONCILING`, or `FINALIZING` | same phase | `recovery.action_set_rebased`; the same `recovery_id` remains active, the replacement current-phase action set binds the immediately prior set and the new verified prefix, valid completion events are carried exactly once, and no further action completion may bind the superseded set. |
| `STARTED` | `FENCING` | `recovery.phase_advanced`; the `STARTED` action set is complete and the exact durable `FENCING` action set is bound. |
| `FENCING` | `RECONCILING` | `recovery.phase_advanced`; the `FENCING` action set is complete, all old `OFFERED`/`ACTIVE` Leases have durable tombstones, and the exact `RECONCILING` action set is bound. |
| `RECONCILING` | `FINALIZING` | `recovery.phase_advanced`; reconciliation actions verified, terminated, settled, or quarantined resources and the exact `FINALIZING` action set is bound. |
| `FINALIZING` | `COMPLETED` | `recovery.completed`; the `FINALIZING` action set, Attempt, assurance, retry, and Job consequences are durable and the replayed state Sigil validates. |

`COMPLETED` is terminal. Each action-set document is made durable before the
event that binds its Sigil. A phase event is appended only after every action
in `completed_action_set_sigil` has one matching event with the exact common
Recovery binding; carried completion events are retained by the transitive
rebase chain but do not satisfy a replacement-set action. The action events
are the normal exact v1 events above, so phase work is idempotent: replay
enumerates the frozen current set, skips actions with a matching committed
event, re-publishes a tombstone without changing its generation, and never
derives or emits a substitute action.

Startup performs these ordered steps:

1. acquire the exclusive writer lock and validate the complete journal;
2. if replay fails, stop before epoch allocation in integrity-failure mode;
3. append one strictly greater `executor.epoch_started`;
4. verify UTC and establish fresh monotonic anchors, or enter
   `executor.clock_uncertain`;
5. create `recovery.started` only when no incomplete Recovery transaction
   exists; otherwise retain that exact `recovery_id` and replayed phase,
   derive a replacement action set from the new-epoch prefix, and append
   `recovery.action_set_rebased` before any further action completion;
6. re-execute the current phase's fixed action set until its postcondition is
   durable, then advance one phase; in `FENCING`, every
   `BIND_DURABLE_ATTEMPT_AUTHORIZATION` for an already existing exact
   request/Event/Receipt precedes the same Attempt's stop action, performs
   read-only resolution only, and is omitted when no such complete chain
   exists; and
7. issue no scheduling, Session readiness, Lease claim, renewal, result
   acceptance, or side-effect authority until `recovery.completed`.

A crash before an action event leaves no action to infer. A crash after the
action event but before phase advancement replays that action and appends only
the missing phase event. A crash after phase advancement resumes the next
phase. Thus repeated crashes never duplicate an Attempt, Lease, budget charge,
result disposition, assurance evaluation, terminal-source binding, or fence
tombstone.

### Job recovery table

| Replayed Job state | Mandatory recovery behavior |
| --- | --- |
| `SUBMITTED` | Commit any due Job deadline first. Otherwise revalidate the bound admission evidence and append the one missing `job.queued`, or latch a precise stop cause. Never create a second Job for the Start key. |
| `QUEUED` | Commit due deadline/freshness failures or preserve `QUEUED`. No Attempt is allocated until Recovery is `COMPLETED`; later allocation uses the normal atomic reservation event. |
| `ACTIVE` | Reconcile its one non-terminal or recently terminal Attempt by the Attempt table, settle its reservation, complete assurance evaluation, then deterministically retry, stop, or succeed. The Job state alone never implies process outcome. |
| `RETRY_WAIT` | Preserve the recorded `eligible_due_at`; commit a due Job deadline first. If eligibility is due, append one `job.retry_ready`; otherwise retain the exact wait. Allocation still waits for Recovery completion. |
| `STOPPING` | Create no Attempt or retry. Finish the current Attempt if any, settle budget, append the required Job assurance evaluation, and commit the terminal state selected by the latched cause and higher-precedence evidence. |
| any terminal Job | Preserve state, cause, revision, terminal event, the selected Attempt's exact CES, QBS, and storage-observation resolver pairs, and immutable Outcome inputs. Resolve and revalidate all referenced records; missing or mismatched bytes are an integrity failure, never a reconstruction request. Resume only an idempotent pending terminal Cancel no-op lookup and the closed execution-root hold-release reconciliation defined below. That reconciliation may resolve or create only the exact EHR, append the matching RFC-0013 Storage release, and append one state-neutral `storage_root.hold_release_observed`; it never rebuilds terminalization or Outcome-input evidence and never changes the terminal Job or Outcome. |

### Attempt recovery table

| Replayed Attempt state | Mandatory recovery behavior |
| --- | --- |
| `CREATED` | No preflight is inferred. If operational binding was interrupted after the exact canonical Receipt became durable, derive the same AA-ID and AAT-ID, resolve only the exact immutable request, `attempt.authorization.granted` Event, and Receipt, and execute `BIND_DURABLE_ATTEMPT_AUTHORIZATION` before any stop only when that complete chain validates. Never submit or rebuild a request. Then use the legal `CREATED -> STOPPING` transition with `RECOVERY_FENCE`, clean or quarantine allocated namespaces, and terminalize `FENCED` unless a higher-precedence cause applies. |
| `PREFLIGHTING` | Latch recovery stop, quarantine any incompletely materialized Crucible/input/output state, enter `CLEANING`, and terminalize `FENCED`, `REJECTED`, or `LOST` according to durable evidence. |
| `READY` | No Worker authority exists, but the old Attempt generation is not reused. Latch stop, clean the materialization, and terminalize `FENCED`; a retry receives new identities. |
| `LEASED` | Fence the active Lease and Session capacity first, latch stop, verify no process began or terminate it, clean/quarantine, then terminalize `FENCED` or `LOST`. |
| `STARTING` | Fence the Lease, locate the process tree only by bound backend identity, prevent further creation, terminate/revoke, clean/quarantine, and terminalize `FENCED`, `LOST`, or a higher-precedence state. |
| `RUNNING` | Fence the Lease and sinks before trusting new messages, terminate the complete tracked tree and handles, then `STOPPING -> CLEANING -> FENCED/LOST` unless an earlier cancellation, timeout, or policy cause wins. A result accepted before the crash remains historical evidence but no missing `attempt.draining` event is inferred. |
| `DRAINING` | The result disposition or permitted no-result completion anchor is already durable. Fence any still-active Lease, close logs/outputs, verify termination and cleanup, and continue to `CLEANING`. An accepted-result or no-result anchor before the later recovery tombstone remains selectable only if no earlier authority-loss trigger exists and every terminal postcondition passes. |
| `STOPPING` | Re-run the idempotent termination and handle-revocation plan, quarantine ambiguity, append the one missing `attempt.cleaning`, and terminalize under the already latched cause or higher-precedence evidence. |
| `CLEANING` | Preserve the terminal-source disposition and Quarantine plan frozen by `attempt.cleaning`; re-run only cleanup steps absent from the journal and verify or quarantine logs, outputs, evidence, and mutable resources. If `ACCOUNTING_CAPTURED` is absent, deterministically derive or resolve the CES, output ESM, its exact Reference Set/hold when non-empty, and QBS; validate every reference and subject mapping; then append the final capture with all four frozen bindings. If it is present, resolve only those exact bindings. Then derive or resolve the OS-ID, reusing its historical RFC-0013 EventRef/State Sigil when already pending, and append the one matching terminal event. Later evidence or storage state never refreshes any terminalization record. |
| terminal, assurance pending | Never change terminal state. Resolve and validate the exact `FROZEN` CES, QBS, and observation records, settle the preserved budget reservation, then produce only trusted post-terminal evidence and append exactly one `attempt.assurance_evaluated`. Missing evidence yields `UNVERIFIABLE`; a missing or contradictory referenced record is an integrity failure, not reconstruction. |
| terminal, assurance complete | Preserve the event, all three terminalization resolver pairs, and claim/evaluation Sigils byte-for-byte; continue only pending Job settlement/evaluation. |

### Lease and Worker recovery table

| Entity and replayed state | Mandatory recovery behavior |
| --- | --- |
| Lease `OFFERED` | Append `lease.fenced`, advance and publish the Job tombstone, and reject all later claim proofs. |
| Lease `ACTIVE` | Append `lease.fenced`, advance and publish the Job tombstone, revoke the protected credential and all bound handles, and release Session capacity atomically. |
| Lease `RELEASED`, `REVOKED`, `EXPIRED`, or `FENCED` | Preserve its terminal event and generation. Verify or idempotently republish the existing tombstone; never allocate another tombstone for the same terminal transition. |
| Worker definition `REGISTERED` | Preserve the stable definition; it remains unschedulable until independently enabled after Recovery. |
| Worker definition `ENABLED` | Preserve the definition state; all old-epoch Sessions are handled separately and no new Session becomes ready before Recovery completes. |
| Worker definition `DRAINING` | Preserve the drain latch and close its Sessions; do not enable implicitly. |
| Worker definition `QUARANTINED` | Preserve quarantine and evidence; recovery cannot revalidate it implicitly. |
| Worker Session `REGISTERED` | Append `worker_session.offline`, fence any unexpected Lease, then close after backend/channel disposition is durable. |
| Worker Session `READY` | Append `worker_session.offline`; it held no active authority and closes without reuse. |
| Worker Session `BUSY` | Append `worker_session.offline`, fence every active Lease, terminate/revoke its handles, then close. |
| Worker Session `DRAINING` | Append `worker_session.offline`, finish fencing/termination for all Leases, then close. |
| Worker Session `OFFLINE` | Preserve offline cause and close after every Lease and backend handle is terminal. |
| Worker Session `QUARANTINED` | Preserve quarantine evidence and close after every Lease and handle is terminal or quarantined. |
| Worker Session `CLOSED` | Preserve terminal state. A returning process must create a new Session ID. |

### Adjunct recovery table

| Replayed intermediate evidence | Mandatory recovery behavior |
| --- | --- |
| Open log stream | Resume from its last committed sequence, drain only a still-bound live backend during reconciliation, then append one `log.closed` or preserve a prior truncation. Partial uncommitted bytes remain quarantined. |
| Accepted/rejected result disposition | Return the historical disposition for duplicates. Never append another acceptance or revive authority; use its committed sequence in terminal conflict checks. |
| Attempt authorization Receipt with ambiguous operational acknowledgement | Recompute the subject, AA-ID, and AAT-ID from the immutable Attempt and stored idempotency identity. If replay already has the exact `BOUND` event, return it. If absent, resolve by the exact request ID/Sigil and verify its `attempt.authorization.granted` Event and `receipt/1.1` Event pair before appending the one missing operational event while the Attempt is still `CREATED`; a missing or conflicting request, Event, or Receipt forces the closed stop path. Never mint or bind a replacement. |
| Reserved but unsettled budget | Settle once from trusted supervisor evidence. Any unrecoverable dimension is charged at its full reservation. |
| Attempt terminal with no assurance evaluation | Append one `CLAIMED`, `UNMET`, or `UNVERIFIABLE` evaluation from immutable evidence; never infer Worker controls. |
| Job stopping with no Job assurance evaluation | Append one roll-up evaluation, using `NOT_APPLICABLE` only when no Attempt ever existed, before any Job terminal event. |
| `CODE_MODIFICATION` terminal-source staging before `attempt.cleaning` | Validate the predeclared Base, source content, file/byte bounds, retention-policy Sigil, durable storage, and verifier evidence, then freeze the exact verified or quarantined binding in `attempt.cleaning`. Any partial, mutable, absent, or unverifiable source is quarantined; recovery never replaces that frozen branch. |
| Durable CES or QBS record with no `ACCOUNTING_CAPTURED` event | Recompute its deterministic ID from the immutable owner and, for QBS, Quarantine-plan input; resolve the single pending pair by that ID and reuse it only when every canonical byte, evidence reference, subject mapping, and owner validates. The pending record alone does not close accounting or permit terminalization. |
| `ACCOUNTING_CAPTURED` with frozen CES, QBS, ESM, and output-root protection | Resolve only the exact bindings carried by the event and validate their complete documents, ESM edge closure, and active hold when `HELD`. Missing or changed bytes are an integrity failure; recovery cannot rebuild any binding from later evidence, current files, current RFC-0013 State, or a Sigil-only search. |
| Durable output-storage-observation record with no Attempt terminal event | Derive its OS-ID again from the immutable terminal inputs, resolve the single pending pair by that ID, and reuse it only if every canonical byte and its historical Storage prefix validate. A later Storage Head never refreshes or replaces it. The pending record activates no root and cannot imply terminalization by itself. |
| Attempt terminal event with a `FROZEN` observation reference | Resolve its exact CES, QBS, and OS ID-and-Sigil pairs, replay RFC-0013 through the bound EventRef, compare the State Sigil, every evidence reference and Quarantine subject mapping, all observation members, the minimum-eligible-Replica selections, and every terminal input byte-for-byte, and then preserve the records. Missing, changed, or unresolvable evidence closes the integrity gate; recovery never scans by hash or substitutes current evidence or storage. |
| Inactive Job- or Attempt-input root with an active hold | Under the outer gate, replay through the exact owner-terminal prefix and State, derive or resolve the deterministic `OWNER_TERMINAL` EHR, append or reuse only that hold's RFC-0013 release, and append the one missing `storage_root.hold_release_observed` owner branch. An absent activation, owner mismatch, ambiguous prefix/EHR, or clock uncertainty retains the hold; an unactivated orphan uses only the separate `ORPHAN_ABORT` protocol. |
| Due output-hold release schedule | Under the outer gate, prove the exact parent Job terminal Event inactivated the root, require trusted time at or after the immutable due time, resolve the deterministic `OUTPUT_DEADLINE` EHR, and resolve or append only that hold's RFC-0013 `retention.hold_released`; then append the missing `storage_root.hold_release_observed` with that EHR ID/Sigil. If either journal, time, or authorization is unavailable, retain the hold. Never release a policy, canonical, legal, or unrelated hold and never delete bytes directly. |
| Terminal Job or derived Outcome | Resolve the selected Attempt's exact observation record and direct-copy it under the derivation rules below. Never crawl a mutable Crucible, add a missing retained-source binding, replace a quarantine disposition, or backfill the immutable Outcome. Later RFC-0014 derivation consumes only the terminal evidence already bound. |

An old Worker Session cannot reattach to its Lease after the epoch changes,
even if it still has the credential and believes the Lease time remains. Its
messages are late evidence. A replacement Attempt never shares mutable
resources unless the predecessor is verified terminated and an explicit
immutable resume identity passes the resume protocol.

The `0.4` runtime always fences live Leases across restart. A future backend
may preserve live authority only under a new RFC defining durable coordinator
continuity, reattachment proof, clock behavior, and equivalent assurance
evidence. Process existence alone is not continuity. If a process cannot be
found or killed, the affected Attempt becomes `LOST`, resources remain
quarantined, and no assurance requiring verified termination is claimed.
Unrelated Jobs resume only when the backend proves resource and authority
separation; otherwise the Executor remains fail-closed.

## Result eligibility and scientific acceptance

The operational projection exposes result dispositions and eligibility
evidence, not a Receipt. Worker `execution-result/1.0`, terminal Attempt,
terminal Job, RFC-0015 `execution-job-outcome/1.0`, and Athanor
`agent-result/2.0` are distinct layers.

### Deterministic `execution-job-outcome/1.0` prerequisites

RFC-0015 owns the Outcome Schema and API. This RFC supplies the operational
prerequisites. Its Schema must import, without restatement or widening, the
RFC-0012 `$defs` for `public_fence_tuple`,
`attempt_assurance_binding`, `job_assurance_binding`, `budget_dimension`,
`budget_ledger`, `budget_settlement_binding`,
`attempt_authorization_requirement`, and `attempt_authorization_state` from
`execution-state/1.0`, and `transition_cause`,
`result_binding`, `completion_anchor_binding`, `worker_session_binding`,
`first_stop_or_fence_binding`, `selected_attempt_binding`,
`lease_terminal_binding`, `final_fence_binding`,
`storage_observation_binding`, `terminal_source_binding`,
`attempt_summary`, `computation_status`, `worker_status`,
`process_termination_status`, `handle_revocation_status`, `cleanup_status`,
`mutable_resource_isolation_status`, `output_publication_status`, and
`quarantine_status` from
`execution-journal-event/1.0`. A `$ref` targets the installed exact
`https://benchwork.dev/schemas/<contract-identifier>#/$defs/<name>` URI.
RFC-0015 also validates
`execution-output-storage-observation-set/1.0` at its exact `$id` and derives
each storage-backed Outcome collection from that complete document; the
observation-set Sigil is not a substitute for resolving it.
Its Outcome `outputs`, `logs`, `resource_evidence`, and
`terminal_source_observation` import the named member `$defs` above and
together preserve the exact ordered member union. RFC-0015 may wrap those
values only in a closed object that names where the value came from; it may
not rename a member, add a null alternative, collapse an explicit union
branch, or substitute a projection cache. Every direct Outcome copy is
byte-for-byte equal under canonical JSON to the referenced terminal-prefix
value. RFC-0015's later `agent-result/2.0` output projection is distinct: it
may use only the explicit field mapping printed by that RFC after eligibility
has validated the complete source member and selected Replica.

RFC-0015 `runtime_outcome` is intentionally its own closed derived object, not
an import of the complete `attempt_terminal_evidence` object. In its Attempt
branch, every same-named status, evidence/summary Sigil, closure Sigil, and
accounting binding is copied byte-for-byte from the selected Attempt terminal
evidence. Its no-Attempt branch uses RFC-0015's fixed explicit status and null
values. It may add only the closed derivation fields RFC-0015 specifies and
must not weaken any imported component enum.

For every terminal Job, Outcome derivation must:

1. validate the journal and installed exact Schema set through the terminal
   Job event;
2. use only that fixed execution prefix, the terminal event's `recorded_at`,
   the pinned derivation-profile identity, and the one immutable
   output-storage observation document resolved by the terminal
   `storage_observation_binding` ID-and-Sigil pair; verify its OS-ID, self
   Sigil, RFC-0013 EventRef, replayed State Sigil, owner and terminal-input
   equalities, then resolve and validate its exact CES-ID/Sigil and QBS-ID/
   Sigil pairs, all ten control references, and every Quarantine subject
   mapping before reading a member. Retrieval time, later execution, evidence,
   or Storage events and mutable current projections are not inputs;
3. verify the immutable Job, Task Capsule, Capability Contract, Snapshot,
   Ward, Specification approval, Execution Specification, Program, Circle,
   and input bindings; for every Attempt, also verify its immutable
   authorization requirement and exact terminal authorization state, and
   resolve each required `BOUND` subject and distinct Receipt;
4. include the exact sorted `attempt_summaries`, verify every Attempt binding
   and terminal event, and verify exactly one budget settlement and one
   Attempt assurance evaluation per allocated Attempt;
5. verify the pre-terminal `job.assurance_evaluated` event and its exact link
   from the terminal Job event;
6. verify the exact `selected_attempt_binding`; for `SELECTED`, copy its
   `result_binding` directly into the Outcome, while `NONE` requires direct
   `result_binding: NONE`. Verify the direct `completion_anchor_binding`; all
   applicable direct copies equal the selected and Job terminal values. A
   selected result anchor binds its
   `attempt.result_accepted` event ID, Sigil, and sequence strictly before
   `attempt.draining`, while a permitted no-result anchor binds that
   `attempt.draining` event ID, Sigil, sequence, and process-exit observation;
   either anchor precedes Attempt and Job terminalization;
7. apply the exact authority-history branch: a selected Attempt that ever
   received an offer has `worker_session_binding: BOUND`, a non-null Executor
   epoch and `public_fence_tuple`, and terminal Lease/tombstone evidence; a
   selected Attempt never offered a Lease has `worker_session_binding: NONE`,
   no Lease-bound Executor epoch or public tuple,
   `lease_terminal_binding: NONE`, and
   `final_fence_binding: ASSIGNED_NO_LEASE`; its allocation event's Executor
   instance/epoch may be copied as provenance but confers no authority. A Job
   with no allocated Attempt has all Attempt authority identities absent,
   `lease_terminal_binding: NONE`, and
   `final_fence_binding: NO_ATTEMPT`. Also verify the exact
   first stop-or-fence event and effective sequence or explicit absence;
8. verify process termination, handle revocation, cleanup, mutable-resource
   isolation, log/output closure, publication or quarantine, the complete
   resolvable control-evidence and Quarantine-binding sets carried by
   `ACCOUNTING_CAPTURED`, and the accounting ledger;
9. bind the requested assurance tuple, evaluation event, optional realized
   claim, backend, Host, profile, suite, and configuration Sigils;
10. derive outputs, exactly three selected-Attempt Log streams,
    resource-evidence references, and terminal-source storage only by
    byte-for-byte projection of the observation set's ordered closed member
    union. Bind its exact ID and Sigil, Storage Journal EventRef and State
    Sigil, Blob records, availability and integrity evidence, Quarantine
    branches, and the unsigned-ASCII-minimum eligible Replica's backend object
    and generation. Preserve explicit `NONE`/`EMPTY` branches and the combined
    4,096-member and 4,096-distinct-Blob bounds; and
11. for `CODE_MODIFICATION`, bind the exact terminal-source branch already
    present in the Attempt and Job terminal events: a `VERIFIED` branch carries
    immutable Crucible Base, retained source, retention policy, bounds, storage
    status, and verifier evidence, while `QUARANTINED` carries explicit absence
    or quarantined identity and closed reasons.

Outcome ID is deterministically derived from Job ID and terminal-event Sigil.
Outcome Sigil covers every field except itself. The Outcome includes
`acceptance_eligible` and RFC-0015's closed sorted ineligibility reasons.
`acceptance_eligible` is true only when all of these predicates hold:

- Job and selected Attempt are both `SUCCEEDED`;
- the selected Attempt's authorization state is `NONE` exactly for a `NONE`
  requirement or one valid `BOUND` subject/Receipt exactly for `REQUIRED`;
- the selected result is `ACCEPTED` when the Specification mode is
  `REQUIRED`, is accepted or explicitly absent under `OPTIONAL`, and is absent
  under `FORBIDDEN`; any acceptance disposition precedes draining and
  terminalization;
- the exact first stop-or-fence binding is absent or its effective sequence is
  strictly later than the completion-anchor sequence, and no revocation,
  expiry, clock, policy, integrity, or conflicting result in the fixed prefix
  proves earlier authority loss;
- the later Lease terminal event and higher fence-floor tombstone are present;
- budget settlement, termination, handle disposition, cleanup, logs, outputs,
  storage, and any required terminal-source retention pass without
  quarantine;
- `job.assurance_evaluated` is `CLAIMED`, its Attempt claim satisfies the exact
  requested profile and suite, and the complete control evidence validates;
  and
- no closed ineligibility reason remains.

A normal Lease release, recovery closure, or higher tombstone after accepted
completion does not retroactively stale the selected result. Its acceptance
event is historical evidence. It is selectable only when the ordering and
postconditions above pass. A permitted `NO_RESULT` draining anchor is likewise
historical completion evidence and uses the same ordering test. A rejected
late or duplicate message after the Job terminal event is preserved outside
the fixed Outcome prefix and cannot replace selected evidence or mutate the
immutable Outcome.

Failed, cancelled, timed-out, policy-violating, lost, fenced, rejected, and
preflight-rejected Jobs still derive one deterministic Outcome, normally with
`acceptance_eligible: false`, even when no Worker result, Lease, or assurance
claim exists. `NOT_APPLICABLE` makes that absence explicit only for a Job with
no Attempt and never makes it eligible.

Repeated derivation from the same verified terminal prefix and installed
Schema set and the same referenced immutable storage observations must be
byte-for-byte equal. Terminal storage status is the frozen observation, not a
query of current availability. A missing observation record, changed
ID/Sigil pair, State-Sigil mismatch, 4,097th member or distinct Blob, or
non-minimum selected Replica makes derivation fail closed; it is never repaired
by scanning immutable records or the current backend. The Outcome never
contains or later backfills
an Agent Result Receipt, Patch Proposal, Patch state, Run, Artifact, or
Experiment state. In particular, RFC-0014 may derive a Patch only from the
predeclared retained terminal source after an accepted `agent-result/2.0`
Receipt; it cannot crawl a mutable Crucible or modify the Outcome.

Eligibility does not imply scientific acceptance. RFC-0015 asks Athanor to
rederive the exact Outcome Sigil and revalidate current canonical
preconditions, including current RFC-0013 Blob/Replica availability and
integrity rather than treating the frozen terminal observation as current.
Only Athanor may append a Chronicle event and issue a Receipt. If Athanor
rejects the Proposal as stale, malformed, duplicate,
scientifically invalid, or otherwise ineligible, the operational Job, Attempt,
Outcome, and negative evidence remain unchanged.

## Invariants

- Chronicle is the source of canonical research state; the execution journal
  is the source of operational execution state.
- Athanor remains the only canonical transition authority.
- Exactly one immutable Task Capsule and Execution Specification bind a Job.
- At most one non-terminal Attempt exists for a Job.
- An Attempt has at most one Lease, every `LEASED` or later Attempt has exactly
  one, and reassignment creates a new Attempt.
- Attempt IDs, Lease IDs, Worker Session IDs, backend-session identities,
  control-channel identities, Executor epochs, and fence generations are never
  reused.
- Only the current active, unexpired Lease can contribute newly accepted
  Worker material; a later tombstone preserves, but does not create,
  historical acceptance.
- Heartbeats do not renew Leases, Worker clocks do not decide deadlines, and
  renewal never resurrects expired authority.
- Durable UTC due times plus in-process monotonic anchors decide deadlines;
  clock uncertainty fences authority and cannot extend it.
- Terminal state never transitions, and retry never rewrites an Attempt.
- Failed, cancelled, timed-out, rejected, expired, lost, fenced, and
  policy-violating Attempts remain replayable.
- A replacement Attempt never shares mutable resources with an unfenced or
  ambiguously owned predecessor.
- Preflight eligibility, Worker capability, and mechanism names are not
  realized assurance.
- Attempt terminal state describes computation, termination, and cleanup, not
  assurance; every terminal Job references one prior closed Job assurance
  evaluation.
- Realized assurance is per-Attempt, post-terminal, evidence-bound, and cannot
  silently downgrade requested assurance.
- Every Attempt allocation reserves aggregate Job budget atomically, and every
  terminal Attempt settles it once from trusted accounting or a full
  fail-closed charge.
- Every terminal Attempt names one resolvable `FROZEN` output-storage
  observation set whose owner, terminal inputs, RFC-0013 EventRef, State
  Sigil, at most 4,096 members, and at most 4,096 distinct Blob identities
  validate byte-for-byte; only a no-Attempt terminal Job uses
  `NOT_APPLICABLE`.
- Each Attempt's frozen terminal inputs derive one OS-ID and permit at most one
  pending-or-terminal observation record, so the complete execution record
  family contains at most `MAX_ATTEMPTS` 4,096 such records.
- A frozen Blob observation selects no Replica exactly when its eligible set
  is empty and otherwise selects the unsigned-ASCII-smallest eligible Replica;
  no later backend or availability state changes that fact.
- A Worker definition is stable across fresh immutable Sessions; an offline,
  quarantined, closed, or old-epoch Session never re-registers.
- A terminal Job Outcome is a deterministic fixed-prefix derivation and is
  never backfilled with later acceptance, Patch, Run, Artifact, or retained
  source state.
- Job success is not a Run, Artifact, Assessment, Decision, Seal, or Receipt.
- Logs and outputs are bounded, content-identified, untrusted operational
  material until explicitly accepted.
- Unknown contracts, controls, events, identities, evidence, or transitions
  fail closed.
- An A2 Worker cannot access or mutate the execution journal, Lease authority
  store, policy source, Chronicle, canonical projections, or any part of
  `.benchwork/`.

## Compatibility

This RFC refines RFC-0007's reserved Executor contract and is subordinate to
RFC-0011's trust and assurance model. It does not change any accepted Phase 2
Schema or identifier.

In particular:

- `task-capsule/1.1` remains declarative and is never wrapped or reinterpreted
  as an executable Job;
- `agent-result/1.1` remains a Phase 2 Proposal and is distinct from
  `execution-result/1.0`;
- scientific `run/1.1` and `run/1.2` terminal states do not gain queued,
  leased, running, retrying, lost, or fenced meanings;
- Chronicle Heads and Receipts are not reused as execution journal Heads or
  events;
- current interactive Codex and Claude Code native-tool Tasks remain outside
  this protocol; and
- a Phase 2 approval never authorizes an Execution Specification or Job.

An Alpha implementation changing any state, transition, terminal precedence,
event payload, fence behavior, or replay meaning must publish a new accepted
RFC version, new executable Schema version where required, migration guidance,
and replay fixtures. Historical execution journals are never replayed under
new semantics by guesswork.

## Security and integrity

Worker messages, Worker clocks, process exit data, resource samples, logs,
outputs, and backend evidence are untrusted until their identities, bounds,
Sigils, fence tuple, and relationships validate. Control and journal channels
must reject ambiguous encoding, path traversal, special-file substitution,
oversized frames, decompression bombs, and identifier confusion.

Lease credentials are capabilities. They must be unguessable, scoped to one
Lease, stored outside Worker-readable state, compared without leaking useful
partial information, rotated by new Lease rather than renewal, and destroyed
or revoked at terminalization. Logs, exception text, process listings, and
diagnostic exports must not disclose them.

The Executor journal and evidence verifier are part of the operational trusted
computing base. The Worker cannot write its own state, fence generation,
heartbeat acceptance, committed log-set summary, result eligibility, cleanup
status, or assurance claim. At A2 the enforcement backend, rather than Worker
cooperation, controls process, filesystem, network, resources, credentials,
and output handles.

An output-storage observation exposes only RFC-0013 object-identity and
locator Sigils, immutable generations, and closed verification evidence. It
never exposes a backend locator, credential, Host path, or Worker-usable
handle. The resolver accepts only the exact OS-ID and self-Sigil from a
verified terminal event; pre-terminal construction's only exception is the
single-assignment pending lookup by the deterministic OS-ID. Enumeration,
prefix matching, and Sigil-only lookup are forbidden.

The local hash chain detects accidental damage and inconsistent replay; it
does not protect against a malicious same-user process able to rewrite the
entire journal, Head, Schemas, and evidence store. RFC-0011's trust limits
remain.

## Alternatives

- **Reuse scientific Run states for scheduling.** Rejected because operational
  retry and liveness churn would change immutable scientific meaning.
- **Allow a Worker to pull any queued Job.** Rejected because selection,
  verified capability, Lease identity, and permission would become an
  unbounded ambient queue capability.
- **Use only an unguessable token, without a fence generation.** Rejected
  because a leaked or delayed old token cannot order split-brain side effects.
- **Fence only returned results.** Rejected because an expired Worker could
  still mutate a Crucible, output namespace, or external sink.
- **Treat heartbeat as renewal.** Rejected because liveness data would silently
  extend authority without policy and deadline validation.
- **Reassign the same Attempt after Worker loss.** Rejected because provenance,
  logs, mutable state, and side effects from the two Workers would be
  ambiguous.
- **Trust a surviving process after Executor restart.** Rejected for `0.4`
  because process identity does not prove coordinator continuity, current
  authority, handle fencing, or evidence completeness.
- **Store runtime events in Chronicle.** Rejected because the Executor has no
  canonical authority and operational replay has different failure semantics.
- **Drop old logs and Attempts after success.** Rejected because failures,
  retries, truncation, and recovery are required operational evidence.

## Non-goals

- remote Workers or multi-coordinator scheduling;
- consensus, leader election, or network partitions between Executors;
- Slurm, Kubernetes, cloud queues, or broad GPU scheduling;
- production-grade A2 isolation on every Host;
- `SANCTUM-A3`, remote attestation, or confidential computing;
- physical Artifact replication, retention, or garbage collection;
- Patch validation, application, merge, or promotion;
- secret brokering or granting network credentials to Workers;
- automatic Provider invocation;
- automatic scientific Run or Artifact creation; and
- a generic command, shell, filesystem, Git, web, or arbitrary-execution MCP
  operation.

## Acceptance tests

Acceptance requires executable Schemas, positive and adversarial fixtures,
deterministic replay tests, crash-injection tests, and retained evidence for
the exact `0.4` Host/backend configuration. The suite must prove:

1. every listed Schema has the exact identifier, top-level fields,
   conditional branches, bounds, and enums in this RFC, rejects every unknown
   field/value, validates complete golden fixtures, publishes the fixed
   `EXECUTION_JOURNAL_V1_FIXED_LIMITS` constants, and resolves the canonical
   named `$defs` `job_state`, `attempt_state`, `worker_session_state`,
   `event_type`, and `storage_root_binding` at their printed URIs; the
   24-contract set includes the Attempt-authorization subject and transition
   request, retained source-tree, execution-storage-root-manifest,
   execution-root hold-release authorization, control-evidence-set,
   quarantine-binding-set, and observation-set filenames and `$id` values,
   exact JB-ID, AA-ID, AAT-ID, BTS-ID, ESM-ID, EHR-ID, CES-ID, QBS-ID, and
   OS-ID algorithms,
   top-level fields, all reference/member/storage branches, and
   additional-property rejection at every nesting level;
2. the journal Schema accepts exactly the v1 event set and payload table,
   rejects an omitted required payload field or extra event type, and enforces
   the exact 73-row base revision-effect closure, including each exact owner
   kind, owner ID, `CREATE`/`ADVANCE`/`EQUAL` mode, conditional
   `attempt.stop_latched` Job mode, Recovery augmentation, five-entry maximum,
   and rejection of every missing, duplicate, extra, or wrongly ordered
   revision, as well as every closed reason, message, progress, status,
   assurance, and budget enum;
3. v1 Capability and Task contracts are ineligible, while the Execution
   Specification cannot broaden its v2 Task, Capability, Snapshot, approval,
   runtime, retry, output, retention, budget, or assurance authority;
4. all listed Job, Attempt, Lease, Worker-definition, and Worker-Session
   transitions succeed only from their stated source states, including
   `CREATED -> STOPPING`, and every unlisted lifecycle transition fails;
5. Attempt terminal events depend only on computation, result disposition,
   termination, cleanup, and quarantine; assurance failure never rewrites an
   Attempt terminal state;
6. every Job terminal path, including no-Attempt cancellation, timeout,
   validation failure, and policy failure, has exactly one preceding
   `job.assurance_evaluated` with the legal
   `CLAIMED`/`UNMET`/`UNVERIFIABLE`/`NOT_APPLICABLE` branch;
7. one Job cannot have two non-terminal Attempts, one Attempt cannot have two
   Leases, Session capacity cannot be exceeded, and identities or fence
   generations cannot be reused;
8. a stable Worker definition creates multiple fresh immutable Sessions, while
   process restart, channel re-establishment, epoch change, offline,
   quarantine, or close always requires a new Session ID and never reactivates
   an old Lease;
9. Lease claim requires the exact Worker definition, Worker Session,
   credential proof, Executor epoch, fence tuple, and unexpired durable claim
   due time;
10. heartbeat alone never changes Lease expiry; accepted ordering, exact
    duplicates, conflicting duplicates, gaps, stale messages, and late
    messages follow the closed disposition rules;
11. renewal commits durably before acknowledgement, respects every durable
    maximum due time, and cannot revive expired, revoked, released, fenced,
    stopping, offline, quarantined, closed, or old-epoch authority;
12. UTC `due_at` plus a live monotonic anchor does not extend a deadline after
    wall-clock adjustment, and restart reconstructs anchors only after clock
    validation;
13. simultaneous due work commits in exact
    `(due_at, fixed_priority, entity_id)` order across randomized timer,
    thread, and receive ordering, and each higher-priority primary event
    finishes its dependent stop/fence propagation before a lower-priority
    still-applicable key can latch a cause; Recovery `STARTED` derives the
    identical surviving primary set by virtual dependent closure and its
    `FENCING` phase then materializes exactly those deferred dependencies;
14. clock rollback, monotonic reset, excessive divergence, and unprovable
    suspend duration append `executor.clock_uncertain`, forbid new authority,
    fence active/offered Leases, stop Attempts, and never restore old
    authority after `executor.clock_restored`; an interruption during an
    active Recovery retains its ID and phase, invalidates pending target
    reservations, binds one replacement set, and never creates a second active
    Recovery;
15. repeated exact non-terminal cancellation returns one `job.stop_latched`,
    conflicting key reuse fails, and cancellation prevents later authority or
    retry;
16. cancellation of a terminal Job appends one state-neutral
    `job.cancellation_observed` per exact matching-revision request, preserves
    state/cause/revision, replays the same no-op after restart, and appends
    nothing when due processing first causes a revision conflict;
17. Attempt allocation atomically reserves the full exact budget vector,
    creates the Attempt and exactly three `OPEN` `STDOUT`, `STDERR`, and
    `STRUCTURED` Log-stream projections in the same event with exactly five
    revision effects, rejects any vector that does not fit, and performs no
    materialization before reservation durability;
18. trusted measured settlement releases unused reservation, partial or
    unavailable accounting charges each unknown dimension in full, every
    terminal Attempt has one prior immutable `ACCOUNTING_CAPTURED` event,
    whose `FROZEN` finalization bindings resolve the exact ten-member
    control-evidence set and complete subject-to-Quarantine set; settlement
    binds that exact event and occurs exactly once after crash, and retry
    requires a new full reservation; replay and crash injection after
    Attempt terminalization, `job.budget_settled`, and
    `attempt.assurance_evaluated` prove the exact terminal-without-summary,
    settled-without-summary, and final-summary prefixes, both cross-owner
    revision advances, and the exact `current_attempt_id` lifetime; measured
    overage is retained, produces `EXCEEDED`, and forces policy-ineligible
    termination rather than being capped or erased;
19. every retry preserves the prior Attempt, allocates new Attempt, Lease,
    Crucible, output-namespace, Session authority, and higher fence identities,
    and never retries a forbidden cause;
20. fresh retry and immutable resume follow their distinct branches; mutable
    paths, surviving processes, ambiguous cleanup, or predecessor authority
    cannot become resume identity;
21. log chunk order, duplicate disposition, conflicting duplicates, atomic
    publication, stream closure, truncation, terminate-on-overflow, and late
    rejection are deterministic and bounded; every terminal Attempt's
    observation set carries exactly three ordered Log members, including
    explicit empty-stream content; resource members resolve the exact CES
    parent and phase-entry Sigils; Quarantine fixtures require the exact QBS
    subject mapping, reject a same-Blob/size unrelated Quarantine, reject
    every non-retained state and object/generation mismatch; and exact-limit
    fixtures accept 4,096 combined members and distinct Blob identities while
    rejecting either 4,097th value before record durability;
22. the first Worker result commits `attempt.result_accepted` or
    `attempt.result_rejected` before `attempt.draining`; duplicates return the
    historical disposition without an event or authority change;
23. malformed, conflicting, stale-fence, late, wrong-Schema, wrong-Sigil,
    over-limit, and partial results remain rejected evidence and cannot replace
    an accepted result;
24. a valid accepted result followed by normal Lease release and a higher
    fence-floor tombstone remains historically well-fenced, while any
    authority-loss trigger effective no later than its completion anchor makes
    it unselectable; an `OPTIONAL`/`FORBIDDEN` no-result anchor uses the same
    test against its draining sequence;
25. requested assurance is immutable; preflight creates no claim; a claim
    appears only after Attempt terminalization and immutable termination/
    cleanup evidence and binds every exact profile, suite, backend, Host,
    policy, input, output, and control-evidence identity through the frozen
    CES-ID-and-Sigil pair and all ten resolvable member references;
26. A0 positive and negative fixtures enforce the exact matrix, including
    verified Phase 3 Job/Attempt/Ward identities and truthful lower-state
    controls without an execution-enforcement claim;
27. A1 positive and negative fixtures cover exclusive materialization,
    constructed environment, tracked process group, wall-time/cancellation,
    trusted accounting, bounded capture, exact identities, and terminal
    evidence, and never claim A2 hostile isolation;
28. lower realized assurance remains visible with
    `satisfies_request: false`; a computationally successful Attempt remains
    `SUCCEEDED`, while the separate assurance roll-up makes the Job
    `FAILED/ASSURANCE_UNMET`;
29. A2 cancellation and Lease loss kill the complete adversarial process tree,
    revoke or fence every side-effecting handle, make `.benchwork/`
    unreachable, and prevent ambiguous mutable-resource sharing;
30. journal replay validates Schema, sequence, chain, Sigils, revisions,
    relationships, exact event ownership, idempotency, fences, deadlines,
    budgets, retention, every fixed collection/entity/row/revisions-per-event
    limit, and the complete closed `execution-state/1.0`, including its exact
    `limit_profile`, every projection alias, and every conditional null rule;
    every terminal Attempt is `FROZEN`, only a no-Attempt terminal Job is
    `NOT_APPLICABLE`, and ID-only, Sigil-only, missing, mismatched-owner,
    mismatched-prefix, or mismatched-State references fail closed;
31. replay from the same journal is byte-for-byte deterministic, stale or
    missing `execution-journal-head/1.0` or State caches rebuild safely,
    both caches carry the exact fixed `limit_profile`, conflicting Heads fail
    closed, checkpointed observation equals full replay, and a create that
    would exceed any fixed limit fails before ID/sequence reservation without
    deleting terminal or failed history;
32. corrupt middle events, invalid Sigils, sequence gaps, illegal transitions,
    partial records, unknown events, and conflicting Heads fail closed without
    automatic truncation, repair, or scheduling;
33. crash injection in every Recovery phase and before/after payload
    durability, event append, Head replacement, Lease delivery, renewal
    acknowledgement, result disposition, budget settlement, assurance
    evaluation, terminal-source retention, output-storage-observation record
    and resolver durability, control-evidence-set and quarantine-binding-set
    record/resolver durability, Storage hold creation, each sole
    root-activating event, each sole root-inactivating event, hold release, and
    terminal commitment yields the exact idempotent state; pre-event retry
    resolves each single pending CES-ID/Sigil and QBS-ID/Sigil and
    pre-terminal retry resolves the single pending OS-ID/Sigil; later evidence
    or Storage prefixes cannot overwrite them, pending records activate no
    root, no ID-only lookup is legal outside its stated pre-event recovery
    window, each complete family never exceeds 4,096 records, and phase
    membership, canonical action order,
    reserved event IDs/sequences, action bindings, rebase carry set,
    superseded-set rejection, and conservative orphan holds all validate;
34. each non-terminal Job, Attempt, Lease, Worker-definition, and
    Worker-Session state follows its recovery-table row, including repeated
    crashes with no duplicate transition or tombstone; observation recovery
    resolves the exact three terminalization-record pairs, replays the frozen
    RFC-0013 State, reproduces every control reference, quarantine subject
    mapping, observation member, and minimum-eligible-Replica selection
    byte-for-byte, and never scans by hash or substitutes current evidence or
    storage;
35. old Sessions and Leases cannot reattach after restart; every surviving
    process, handle, Crucible, output namespace, and sink is terminated,
    verified, or quarantined before `recovery.completed`; root fixtures accept
    only `JOB_INPUT`, `ATTEMPT_INPUT`, and `ATTEMPT_OUTPUT`, reject
    `ACTIVE_CONTROL`, enforce exact Job/Attempt owner IDs and sorted bounds,
    and expose each root only over its specified activation interval;
36. `CODE_MODIFICATION` requires predeclared bounded retention and terminal
    events bind immutable Base/source/policy/verifier evidence; the
    Specification's non-null Base identity/Sigil copy into every Attempt and
    deterministically supply the no-Attempt branch; missing or partial
    retention quarantines, a null source is permitted only as the paired
    null/zero-count `QUARANTINED` branch, and no terminal Outcome is later
    backfilled;
37. every terminal Job derives one byte-stable
    `execution-job-outcome/1.0`, including no-result negative paths, from its
    fixed verified terminal prefix and referenced immutable frozen storage
    observation resolved by exact OS-ID and Sigil, with exact Session,
    Attempt-summary, accepted-result event, first stop/fence, final-fence union
    (including a final pre-Lease Attempt), Storage EventRef and State Sigil,
    exact CES and QBS pairs, all ten control references, every Quarantine
    subject mapping, direct output, three-Log, resource-evidence, and
    terminal-source observation groups, Blob, availability, integrity, and
    selected Replica/backend-generation bindings;
    its Schema resolves every mandatory RFC-0012 component and the complete
    observation contract through the printed canonical `$ref`, including
    `budget_settlement_binding` and every named observation-member `$def`,
    preserves explicit `NONE`/`EMPTY` without rename or flattening, enforces
    both aggregate 4,096 limits, and rejects any cloned, widened, missing, or
    4,097-member import;
38. later duplicate, rejected, or terminal-cancellation observation events do
    not mutate an Outcome, current storage availability does not change its
    frozen terminal observation, a later lexically smaller Replica does not
    replace the frozen minimum eligible Replica, and Outcome derivation
    changes neither execution journal nor Chronicle;
39. terminal Jobs and all failed, cancelled, timed-out, expired, rejected,
    lost, fenced, policy-violating, under-assured, quarantined, and partial
    evidence remain present after replay; and
40. Job success and Outcome retrieval leave Chronicle, Runs, Artifacts,
    Assessments, Decisions, Patches, Seals, and Receipts unchanged, while
    RFC-0015 exposes only closed typed operations and no execution escape
    hatch; and
41. an empty `NEW_AUTHORIZATION_EACH_ATTEMPT` projection initializes
    authorization `NONE`, while every non-empty first or retried Attempt
    initializes `PENDING`, derives the exact AA-ID only after immutable
    allocation, resolves one distinct Receipt through the purpose-bound
    request/Event chain, commits one
    `attempt.authorization_bound` before preflight/Lease/handle authority, and
    reaches `BOUND` exactly once; crash before or after Receipt/event
    durability reuses the same subject and Receipt, while predecessor,
    cross-Attempt, Specification-Receipt, changed-effect, missing, and
    conflicting reuse all fail closed without launch;
42. Attempt authorization fixtures derive the exact AAT-ID, persist the
    immutable transition request before Athanor, resolve
    `attempt.authorization.granted` and its `receipt/1.1` by exact Event
    ID/body Sigil, and reject any validation that invents purpose/subject
    fields on the Receipt; the payload Actor, outer canonical
    `actor/1.0`, and authenticated-context mapping all match byte-for-byte;
    Recovery binds only an already durable complete
    chain and never resamples Head, actor, Chronicle actor, time, or authority;
43. retained-source fixtures deterministically reproduce the complete
    `benchwork-source-tree/1.0` manifest and `BWSOURCE1` bundle, enforce the
    identity/Sigil/storage-Blob all-null-or-all-non-null matrix, reject
    traversal, scope, ordering, byte, count, and bundle mismatches, and allow
    RFC-0014 export only from exact verified bundle readback;
44. each execution root resolves one single-assignment ESM and, when
    non-empty, the exact installed extractor/validator, complete typed Blob
    edges, ESM-ID-derived registration Event ID, deterministic Reference Set,
    neutral installed operational policy, exact post-registration set
    authorization, and active hold targeting that Set; crash injection at ESM,
    registration, hold, accounting capture, and root activation boundaries
    proves the graph has no future-Sigil cycle and leaves conservative
    protection;
45. output ESM and QBS fixtures bind every output, Log, Blob-bearing resource
    entry, terminal source, current TransferRef, provenance, byte size, and
    Quarantine owner; both origins terminate through the exact
    `transfer.quarantined` Event; only
    `quarantine.recorded + (HELD|DISPOSAL_FAILED)` maps to retained
    `QUARANTINED`, while recorded-origin `DISPOSED` and failed-origin
    `FAILED|DISPOSAL_FAILED|DISPOSED` map only to
    `QUARANTINE_TERMINAL_NEGATIVE`; in-progress or unlisted pairs and every
    4,097th phase, deficiency, member, or Blob value fail before capture;
46. every output hold receives the immutable checked release schedule,
    duration zero releases only after the Job terminal event, positive
    duration waits for trusted due time, overflow fails closed, and crash or
    clock uncertainty leaves an extra hold; input-owner terminal, orphan-abort,
    and output-deadline fixtures each derive the one EHR from the hold ID,
    activation rejects any pre-existing EHR, owner/deadline release and
    observation are idempotent, and orphan release is idempotent with no
    fabricated execution observation; none removes policy, legal, canonical,
    or other-root protection or deletes bytes;
47. Start validates a current Phase 3 Chronicle Head with
    `event_count < U63_MAX` under the outer gate before Job document, ESM,
    Reference Set, hold, or execution Event durability, freezes the exact
    admission evidence, and rejects exhausted, unavailable, invalid, or
    conflicting retries without side effects; and
48. an `ATTEMPT_OUTPUT` storage entry accepts only the current leased
    Attempt's exact INGEST request, staging handle, fence, backend,
    TransferRef, terminal Event, Blob, and provenance; deduplication may reuse
    verified bytes but never an old Replica creator, transfer, or provenance
    as current-attempt evidence.

The reference vertical slice must publish its highest realized assurance only
for the exact tested backend, Host, profile, conformance suite, and
configuration Sigils. The `0.4` release must demonstrate expiration,
cancellation, duplicate delivery, stale-result rejection, retry, bounded logs,
assurance failure, journal replay, and restart recovery end to end.
