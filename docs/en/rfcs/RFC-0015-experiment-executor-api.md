---
title: "RFC-0015: Experiment Executor API"
document_id: BW-RFC-0015
version: 0.1
status: draft
owner: unassigned
date: 2026-07-31
language: en
canonical: true
---

# RFC-0015: Experiment Executor API

## Status

This draft defines the typed Phase 3 control surface over the execution model
in RFC-0011, the Job protocol in RFC-0012, the storage model in RFC-0013, and
the Patch protocol in RFC-0014. It does not authorize a generic command runner,
automatic Provider invocation, automatic Patch promotion, or automatic
scientific promotion.

The API becomes implementable only when the four dependency RFCs and their
executable Schemas agree on identity, state, fencing, assurance, storage, and
result eligibility.

## Problem

RFC-0009 deliberately keeps shell, filesystem, Git, and web operations outside
the MCP scientific control plane. RFC-0011 narrowly amends that boundary so MCP
may delegate a closed, typed Job to an Executor without becoming the Executor.

Phase 3 therefore needs an API that can:

- submit an already resolved and authorized Execution Specification;
- return before a Worker finishes;
- observe durable Job and Attempt state with bounded stable pagination;
- request cancellation without pretending that cancellation is immediate;
- retrieve every terminal Job outcome, even when no Worker Result exists;
- submit exactly one eligible outcome to Athanor; and
- preserve all Phase 2 MCP names and meanings.

A single `execute` method accepting a command, working directory, environment,
or arbitrary payload would violate the accepted control-plane boundary even if
its implementation happened to use a sandbox.

## Decision

Benchwork adds a typed `ExecutionService` with five operations:

```text
start -> observe -> cancel
                  \
                   -> get outcome -> accept outcome -> Athanor Receipt
```

The Host-neutral operations are:

| Operation | MCP tool | Effect |
| --- | --- | --- |
| Start | `benchwork_start_job` | Durably submits one authorized Job; scheduling remains asynchronous |
| Observe | `benchwork_observe_job` | Reads one bounded, fixed-prefix page of Job operational state |
| Cancel | `benchwork_cancel_job` | Durably records an idempotent cancellation request or terminal no-op |
| Get outcome | `benchwork_get_job_result` | Derives the immutable terminal Job Outcome and its eligibility evidence |
| Accept outcome | `benchwork_accept_job_result` | Asks Athanor to accept the exact eligible Outcome as one Agent Result |

MCP validates a typed request, delegates it to `ExecutionService`, validates
the operation-specific success data, and returns a bounded
`mcp-tool-result/1.0` envelope. It does not interpret an executable, invoke a
shell, materialize a workspace, create a process, read arbitrary output paths,
or transform Worker messages into scientific facts.

The `0.4` reference implementation is local and asynchronous. Start returns
after `job.submitted` is durable. Worker execution never blocks the MCP
request, and MCP server lifetime is not the source of Job truth.

## Result layers

Three documents have deliberately different authority:

```text
optional Worker execution-result/1.0
              |
              v
terminal Attempt + cleanup + fence + assurance evidence
              |
              v
Executor execution-job-outcome/1.0
              |
              v
Athanor agent-result/2.0 -> agent-result.accepted -> Receipt
```

`execution-result/1.0` retains the RFC-0012 meaning: it is a bounded Worker
completion message with outcome `COMPLETED` or `FAILED`. A rejected,
cancelled, timed-out, lost, fenced, or preflight-rejected Attempt may have no
Worker Result.

`execution-job-outcome/1.0` is the Executor's deterministic immutable view of
one terminal Job. It exists for every terminal Job, binds the complete
post-terminal eligibility evidence, and carries an optional Worker Result
Sigil. It is operational evidence and not an Athanor Receipt.

`agent-result/2.0` is derived only from an eligible successful Job Outcome and
is a Proposal until Athanor accepts it. No layer may be substituted for
another or silently upgraded in authority.

Patch export and Patch Proposal acceptance are post-terminal derivations under
RFC-0014. They bind the accepted `agent-result/2.0` Receipt and never mutate or
backfill an immutable Job Outcome.

## Executable contract set

RFC-0012 owns these contracts used by the API:

- `execution-specification/1.0`;
- `execution-job/1.0`;
- `execution-attempt/1.0`;
- `attempt-authorization-subject/1.0`;
- `attempt-authorization-transition-request/1.0`;
- `execution-worker/1.0`;
- `execution-worker-session/1.0`;
- `execution-lease/1.0`;
- `execution-result/1.0`;
- `benchwork-source-tree/1.0`;
- `execution-storage-root-manifest/1.0`;
- `execution-root-hold-release-authorization/1.0`;
- `execution-output-storage-observation-set/1.0`;
- `execution-control-evidence/1.0`;
- `execution-control-evidence-set/1.0`;
- `execution-quarantine-binding-set/1.0`;
- `sanctum-assurance-profile/1.0`;
- `sanctum-assurance-claim/1.0`; and
- the execution journal and replay contracts.

This RFC owns these closed JSON Schema Draft 2020-12 documents:

| Contract identifier | Filename | Purpose |
| --- | --- | --- |
| `execution-start-request/1.0` | `execution-start-request-1.0.json` | Complete Execution Specification and Start idempotency binding |
| `execution-observe-request/1.0` | `execution-observe-request-1.0.json` | Job-bound fixed-prefix pagination request |
| `execution-observation/1.0` | `execution-observation-1.0.json` | Bounded public projection and event page |
| `execution-cancel-request/1.0` | `execution-cancel-request-1.0.json` | Revision-bound cancellation request and Host provenance |
| `execution-get-result-request/1.0` | `execution-get-result-request-1.0.json` | Read-only Job Outcome lookup |
| `execution-job-outcome/1.0` | `execution-job-outcome-1.0.json` | Deterministic terminal Job evidence and acceptance eligibility capsule |
| `execution-accept-result-request/1.0` | `execution-accept-result-request-1.0.json` | Exact Job Outcome acceptance binding |
| `agent-result-acceptance-policy/1.0` | `agent-result-acceptance-policy-1.0.json` | Closed, versioned predicate set for one Agent Result acceptance family |
| `agent-result-acceptance-authorization/1.0` | `agent-result-acceptance-authorization-1.0.json` | Complete Ward, approval, policy, actor, candidate, and storage authorization preimage |
| `agent-result-acceptance-transition-request/1.0` | `agent-result-acceptance-transition-request-1.0.json` | Complete internal Athanor candidate bound by the storage intent |
| `agent-result/2.0` | `agent-result-2.0.json` | Athanor-facing Agent Result derived from one eligible Job Outcome |
| `agent-result-record/2.0` | `agent-result-record-2.0.json` | Replayed accepted Task-result projection |
| `mcp-tool-registry/2.0` | `mcp-tool-registry-2.0.json` | Phase 2 inventory plus closed Phase 3 execution and Patch tools |

Their exact top-level field sets are:

| Contract | Exact top-level fields |
| --- | --- |
| `execution-start-request/1.0` | `schema_version`, `execution_specification`, `idempotency_key` |
| `execution-observe-request/1.0` | `schema_version`, `job_id`, `limit`, and optional `cursor`; no other field is optional |
| `execution-observation/1.0` | `schema_version`, `job_binding`, `task_binding`, `capability_binding`, `snapshot_binding`, `execution_specification_binding`, `job_state`, `job_revision`, `attempts`, `worker_sessions`, `lease_binding`, `public_fence_binding`, `assurance`, `cancellation`, `terminal`, `cleanup`, `quarantine`, `events`, `logs`, `through_journal_sequence`, `through_event_sigil`, `next_cursor`, `next_actions` |
| `execution-cancel-request/1.0` | `schema_version`, `cancellation_request_id`, `idempotency_key`, `job_id`, `job_binding_sigil`, `expected_job_revision`, `reason`, `actor`, `host_invocation`, `caller_observed_at` |
| `execution-get-result-request/1.0` | `schema_version`, `job_id` |
| `execution-job-outcome/1.0` | the exact field list in **Get Job Outcome** |
| `execution-accept-result-request/1.0` | `schema_version`, `job_id`, `execution_job_outcome_sigil`, `idempotency_key` |
| `agent-result-acceptance-policy/1.0` | `schema_version`, `policy_id`, `policy_version`, `canonical_event_type`, `transition_request_schema`, `authorization_schema`, `agent_result_schema`, `job_outcome_schema`, `reference_intent_schema`, `chronicle_event_schema`, `receipt_schema`, `ward_evaluator_profile`, `actor_authentication_profile`, `predicate_profile`, `predicates`, `policy_sigil` |
| `agent-result-acceptance-authorization/1.0` | `schema_version`, `transition_request_id`, `event_type`, `expected_chronicle_head`, `authority_subject`, `ward_pass`, `approval`, `acceptance_policy`, `acceptance_request_sigil`, `idempotency_key_sigil`, `reference_sets`, `managed_blob_sigils`, `acceptance_storage_binding`, `actor`, `host_invocation`, `chronicle_actor`, `requested_at`, `authorization_sigil` |
| `agent-result-acceptance-transition-request/1.0` | `schema_version`, `transition_request_id`, `event_type`, `expected_chronicle_head`, `agent_result`, `job_outcome_binding`, `acceptance_request_sigil`, `idempotency_key_sigil`, `reference_sets`, `managed_blob_sigils`, `acceptance_storage_binding`, `actor`, `host_invocation`, `chronicle_actor`, `acceptance_authorization`, `authorization_sigil`, `requested_at`, `transition_request_sigil` |
| `agent-result/2.0` | the exact field list in **Agent Result v2 and replay** |
| `agent-result-record/2.0` | the exact field list in **Agent Result v2 and replay** |
| `mcp-tool-registry/2.0` | `schema_version`, `api_version`, `stability`, `input_schema_source`, `response_schema`, `tools` |

`schema_version` is the named contract identifier in every row. Nullable
members in a required top-level field remain present as JSON null; only the
Observe request's `cursor` may be omitted. Nested objects and unions are
closed as assigned below. This table, not an illustrative example, is the
required-member source for the executable Schemas.

All use `$id` values under
`https://benchwork.dev/schemas/<contract-identifier>`. Every object is closed
with `additionalProperties: false`; arrays and strings have explicit bounds;
identifier-bearing maps constrain `propertyNames`; unknown versions, fields,
enums, and result layers fail closed.

Each new Phase 3 Registry entry names its request Schema and success-data
Schema. `tools/list.inputSchema` must be generated from or proven semantically
equal to the named request Schema. Before returning `ok: true`, MCP validates
`data` against the named success-data Schema and then wraps it in the unchanged
`mcp-tool-result/1.0` envelope. The original 38 entries retain their v1 field
set and existing inline-input behavior; migration does not require inventing
38 replacement request contracts.

### Closed API object definitions

`Sigil` is `sha256:` followed by 64 lowercase hexadecimal characters.
`Opaque` is printable UTF-8 of length `1..256` with no NUL or control
character. `U63` is an integer in `0..9223372036854775807` and
`PositiveU63` starts at one. `U64` is an integer in
`0..18446744073709551615`. `Timestamp` is UTC RFC 3339 ending in `Z`, with no
leap second and at most six fractional digits.
Job, Attempt, Lease, Worker, Worker Session, Executor, Execution Journal,
Journal Event, Log Stream, and Execution Specification IDs use the exact
RFC-0012 prefixes and bounds.
Outcome IDs use `OJ-[A-F0-9]{64}` and acceptance transition request IDs use
`ATR-[A-F0-9]{64}`. All other IDs use the owning contract's closed pattern
or `Opaque` where explicitly stated. Collections have at most 4096 members
unless a smaller bound is printed; set arrays are unique and sorted by the
stated key.

The API Schemas publish these exact closed `$defs`:

| Alias | Exact shape |
| --- | --- |
| `JobBinding` | `job_id: JB-ID`, `job_binding_sigil: Sigil` |
| `TaskBinding` | `task_id: Task-ID`, `task_capsule_sigil: Sigil` |
| `RegistryBinding` | Exact RFC-0011 `registry_id`, `registry_revision`, and `registry_sigil` |
| `CapabilityBinding` | `capability_id: Capability-ID`, `contract_version: constant "2.0"`, `capability_contract_sigil: Sigil` |
| `SnapshotBinding` | `snapshot_id: Snapshot-ID`, `snapshot_sigil: Sigil` |
| `SpecificationBinding` | `specification_id: ES-ID`, `specification_sigil: Sigil` |
| `CircleBinding` | `circle_id: RFC-0011 Circle-ID`, `circle_sigil: Sigil` |
| `ObservationCursor` | `job_id: JB-ID`, `last_returned_sequence: U63`, `through_journal_sequence: PositiveU63`, `through_event_sigil: Sigil`, `cursor_sigil: Sigil` |
| `WorkerSessionBinding` | RFC-0012 `NONE {kind: "NONE"}` or `BOUND {kind: "BOUND", worker_id: WK-ID, worker_binding_sigil: Sigil, worker_session_id: WS-ID, worker_session_binding_sigil: Sigil}` |
| `LeaseView` | `NONE {kind: "NONE"}` or `PRESENT {kind: "PRESENT", lease_id: LS-ID, state: "OFFERED"\|"ACTIVE"\|"RELEASED"\|"REVOKED"\|"EXPIRED"\|"FENCED", terminal_event_sigil: Sigil\|null}` |
| `PublicFenceView` | `NONE {kind: "NONE"}` or `PRESENT {kind: "PRESENT", tuple: RFC-0012 public_fence_tuple, final_fence_floor: U64, tombstone_present: boolean}` |
| `AssuranceView` | `requested_level: "SANCTUM-A0"\|"SANCTUM-A1"\|"SANCTUM-A2"`, `profile_version: Opaque`, `profile_sigil: Sigil`, `conformance_suite_id: Opaque`, `conformance_suite_sigil: Sigil`, `attempt_binding: NONE {kind: "NONE"} or RFC-0012 attempt_assurance_binding`, `job_binding: RFC-0012 job_assurance_binding` |
| `CancellationView` | `NONE {kind: "NONE"}`; `REQUESTED {kind: "REQUESTED", cancellation_request_id: Opaque, request_event_id: JE-ID, request_event_sigil: Sigil, reason: Opaque}`; or `OBSERVED_TERMINAL {kind: "OBSERVED_TERMINAL", cancellation_request_id: Opaque, observation_event_id: JE-ID, observation_event_sigil: Sigil, reason: Opaque}` |
| `TerminalView` | `NONTERMINAL {kind: "NONTERMINAL"}` or `TERMINAL {kind: "TERMINAL", state: "SUCCEEDED"\|"FAILED"\|"CANCELLED"\|"TIMED_OUT"\|"POLICY_VIOLATION", event_id: JE-ID, sequence: PositiveU63, event_sigil: Sigil, recorded_at: Timestamp}` |
| `AttemptTerminalView` | `NONTERMINAL {kind: "NONTERMINAL"}` or `TERMINAL {kind: "TERMINAL", state: "SUCCEEDED"\|"FAILED"\|"CANCELLED"\|"TIMED_OUT"\|"POLICY_VIOLATION"\|"LEASE_EXPIRED"\|"LOST"\|"FENCED"\|"REJECTED", event_id: JE-ID, sequence: PositiveU63, event_sigil: Sigil, recorded_at: Timestamp}` |
| `CleanupView` | `termination_status: "NOT_STARTED"\|"EXITED"\|"TERMINATED"\|"QUARANTINED"\|"UNVERIFIABLE"`, `handle_status: "NOT_APPLICABLE"\|"REVOKED"\|"FENCED"\|"QUARANTINED"\|"UNVERIFIABLE"`, `cleanup_status: "NOT_APPLICABLE"\|"VERIFIED"\|"PARTIAL"\|"FAILED"\|"QUARANTINED"`, `mutable_resource_isolation_status: "NOT_APPLICABLE"\|"VERIFIED_ISOLATED"\|"QUARANTINED"\|"UNVERIFIED"`, `output_publication_status: "NOT_APPLICABLE"\|"VERIFIED"\|"QUARANTINED"\|"FAILED"`, `quarantine_status: "NOT_REQUIRED"\|"COMPLETE"\|"PARTIAL"\|"FAILED"`, `termination_evidence_sigil: Sigil\|null`, `handle_disposition_evidence_sigil: Sigil\|null`, `cleanup_summary_sigil: Sigil\|null` |
| `QuarantineView` | `subject_kind: "ATTEMPT_OUTPUT"\|"LOG"\|"RESOURCE_EVIDENCE"\|"TERMINAL_SOURCE"`, `subject_id: Opaque`, `status: "NOT_REQUIRED"\|"COMPLETE"\|"PARTIAL"\|"FAILED"`, `evidence_sigil: Sigil\|null` |
| `ObservationAttempt` | `attempt_id: AT-ID`, `attempt_binding_sigil: Sigil`, `retry_ordinal: PositiveU63`, `state: RFC-0012 AttemptState`, `revision: U64`, `attempt_authorization_state: RFC-0012 AttemptAuthorizationState`, `worker_session_binding: WorkerSessionBinding`, `lease_binding: LeaseView`, `public_fence_binding: PublicFenceView`, `assurance: AssuranceView`, `terminal: AttemptTerminalView`, `cleanup: CleanupView`, `quarantine: [QuarantineView]` |
| `ObservationWorkerSession` | `worker_id: WK-ID`, `worker_binding_sigil: Sigil`, `worker_session_id: WS-ID`, `worker_session_binding_sigil: Sigil`, `state: RFC-0012 WorkerSessionState` |
| `ObservationEvent` | `sequence: PositiveU63`, `event_id: JE-ID`, `event_type: RFC-0012 EventType`, `recorded_at: Timestamp`, `related_entity_ids: [Opaque]`, `event_sigil: Sigil` |
| `ObservationLog` | `stream_kind: "STDOUT"\|"STDERR"\|"STRUCTURED"`, `stream_id: LG-ID`, `state: "OPEN"\|"CLOSED"`, `captured_bytes: U63`, `dropped_bytes: U63`, `truncated: boolean`, `blob_sigil: Sigil\|null`, `closure_event_sigil: Sigil\|null` |
| `NextAction` | `action: "WAIT"\|"OBSERVE"\|"CANCEL"\|"GET_OUTCOME"\|"ACCEPT_OUTCOME"\|"INSPECT_FAILURE"`, `reason_code: "JOB_NONTERMINAL"\|"CANCELLABLE"\|"TERMINAL_OUTCOME_READY"\|"OUTCOME_ELIGIBLE"\|"OUTCOME_INELIGIBLE"\|"FAILURE_RECORDED"`, `expected_job_revision: U64` |
| `ActorBinding` | `kind: "USER"\|"AGENT"\|"SYSTEM"`, `actor_id: Opaque`, `authentication_context_sigil: Sigil`, `actor_sigil: Sigil` |
| `HostInvocationBinding` | `host_identity_sigil: Sigil`, `invocation_id: Opaque`, `authentication_context_sigil: Sigil`, `invocation_sigil: Sigil` |
| `ChronicleActor` | Exact RFC-0001 `actor/1.0`: `actor_id`, `actor_type: "human"\|"policy"\|"tool"\|"agent"`, `host: "cli"\|"codex"\|"claude-code"`, and `authenticated_by` |
| `AcceptanceBlobValidation` | `blob_sigil: Sigil`, `size_bytes: RFC-0013 U63`, `replica_id: RFC-0013 SR-ID`, `backend_id: Opaque`, `backend_generation: Opaque`, `availability_event: RFC-0013 EventRef`, `integrity_evidence_sigil: Sigil`, `quarantine_status: "CLEAR"` |
| `AcceptanceStorageBinding` | `storage_event: RFC-0013 EventRef`, `storage_state_sigil: Sigil`, `validated_blob_sigils: [Sigil]`, `validation_evidence: [AcceptanceBlobValidation]`, `validation_evidence_set_sigil: Sigil` |
| `AcceptanceAuthoritySubject` | Complete closed authority and accepted-candidate binding defined below |
| `WardPassBinding` | Complete closed historical Ward re-evaluation defined below |
| `ApprovalEvidence` | Closed `NOT_REQUIRED` or canonical Event-and-Receipt-resolved `REQUIRED` branch defined below |
| `ExecutionStorageRootBinding` | Exact RFC-0012 `execution-journal-event/1.0#/$defs/storage_root_binding`, including its storage-root-manifest ID-and-Sigil pair |
| `TerminalizationStorageManifestBinding` | RFC-0015 `NOT_APPLICABLE {kind}` no-Attempt wrapper or the exact RFC-0012 terminal `FROZEN {kind, storage_root_manifest_id, storage_root_manifest_sigil}` branch |
| `OutputRootProtection` | RFC-0015 `NOT_APPLICABLE {kind}` no-Attempt wrapper or the exact RFC-0012 terminal `NO_HOLD` or `HELD` branch |

The acceptance-only definitions are exact, not illustrative:

```text
AcceptanceAuthoritySubject:
  registry_binding: RegistryBinding
  task_binding: TaskBinding
  program_id: Program-ID
  capability_binding: CapabilityBinding
  snapshot_binding: SnapshotBinding
  circle_binding: CircleBinding
  execution_specification_binding: SpecificationBinding
  job_binding: JobBinding
  job_outcome_binding:
    outcome_id: OJ-ID
    outcome_sigil: Sigil
  agent_result_sigil: Sigil

WardPassBinding:
  status = PASS
  ward_decision_id: RFC-0011 WardDecisionId
  ward_decision_sigil: Sigil
  resolved_permission_set_sigil: Sigil
  evaluated_chronicle_head: RFC-0013 ChronicleHeadRef
  evaluated_at: Timestamp

ApprovalEvidence is exactly one of:
  NOT_REQUIRED:
    kind = NOT_REQUIRED
    ward_decision_id: RFC-0011 WardDecisionId
    ward_decision_sigil: Sigil
  REQUIRED:
    kind = REQUIRED
    ward_decision_id: RFC-0011 WardDecisionId
    ward_decision_sigil: Sigil
    approval_policy_id: RFC-0011 UpperId(AP)
    approval_policy_version: RFC-0011 Version
    approval_policy_sigil: Sigil
    approval_subject_id: RFC-0011 UpperId(EA)
    approval_subject_sigil: Sigil
    approval_event_id: RFC-0001 Event-ID
    approval_event_body_sigil: Sigil
    approval_receipt_id: RFC-0001 Receipt-ID
    approval_receipt_sigil: Sigil
```

`agent-result-acceptance-policy/1.0` is one complete embedded policy record,
not a mutable policy name. Its scalar fields have these constant values:

```text
schema_version = agent-result-acceptance-policy/1.0
policy_id = agent-result-acceptance
policy_version = 1.0
canonical_event_type = agent-result.accepted
transition_request_schema = agent-result-acceptance-transition-request/1.0
authorization_schema = agent-result-acceptance-authorization/1.0
agent_result_schema = agent-result/2.0
job_outcome_schema = execution-job-outcome/1.0
reference_intent_schema = artifact-storage-reference-intent/1.0
chronicle_event_schema = chronicle-event/1.1
receipt_schema = receipt/1.1
ward_evaluator_profile = sanctum-authority-intersection/1.0
actor_authentication_profile = mcp-authenticated-invocation/1.0
predicate_profile = agent-result-acceptance-predicates/1.0
```

Its `predicates` array contains every value below exactly once and in this
order:

```text
EXPECTED_HEAD_ADMISSIBLE
AUTHENTICATED_INVOCATION_MATCH
TASK_AUTHORITY_CHAIN_VALID
CURRENT_WARD_PASS
APPROVAL_CHAIN_VALID
OUTCOME_REDERIVATION_MATCH
TERMINAL_SUCCESS_ELIGIBLE
EXECUTION_EVIDENCE_VALID
BUDGET_SETTLED
ASSURANCE_EVIDENCE_VALID
STORAGE_OBSERVATION_VALID
TERMINAL_SOURCE_VALID
EVIDENCE_SELECTION_FINAL
AGENT_RESULT_DERIVATION_MATCH
REFERENCE_SET_CLOSURE_VALID
ACCEPTANCE_STORAGE_PREFIX_VALID
```

`policy_sigil` covers canonical JSON of every other policy field. The policy
resolver accepts only the complete record above with a valid self-Sigil and
maps the ordered predicates to the correspondingly named checks in **Accept
Job Outcome**. It rejects an unknown ID, version, profile, field, predicate,
order, or Sigil; it has no `latest`, local-default, subset, or forward-
compatible fallback.

The mapping is exact: `EXPECTED_HEAD_ADMISSIBLE` is acceptance step 1;
`AUTHENTICATED_INVOCATION_MATCH` is the authenticated Actor, Host invocation,
and Chronicle Actor check before candidate construction;
`TASK_AUTHORITY_CHAIN_VALID` and
`APPROVAL_CHAIN_VALID` are the non-approval and approval parts of step 2;
`CURRENT_WARD_PASS` is step 3; and the predicates from
`OUTCOME_REDERIVATION_MATCH` through `ACCEPTANCE_STORAGE_PREFIX_VALID`, in
their printed order, are steps 4 through 14 respectively. Step 15 is the
Chronicle commit and durable permanent-pin mechanic, not an authorization
predicate. There is no post-commit protection-transfer step, and acceptance
never releases or changes the execution hold.
The pinned `mcp-authenticated-invocation/1.0` profile emits all three
bindings from one authenticated context and enforces the exact ID, kind,
Host, and authentication-mechanism rules above; a profile that supplies only
an Actor ID is not equivalent.

RFC-0012 aliases above are canonical URI `$ref`s, not local approximations.
`LeaseView.terminal_event_sigil` is null exactly for `OFFERED` or `ACTIVE`;
it is non-null for a terminal state. `ObservationAttempt.terminal` is
`TERMINAL` exactly when its Attempt state is terminal. An
`ObservationLog` in `OPEN` has null Blob and closure Sigils; `CLOSED` has both
non-null, including for an empty stream's content identity. Cursor Sigils
cover the other cursor fields. A cursor's Job equals the request Job,
`last_returned_sequence <= through_journal_sequence`, and `next_cursor` is
non-null exactly when another matching event remains in the fixed prefix.
`AssuranceView.attempt_binding` is `NONE` if and only if the projection has no
current or terminally selected Attempt; otherwise it is byte-for-byte the
selected Attempt's RFC-0012 assurance binding. Its Job binding always equals
the replayed Job binding, including `PENDING` before evaluation and
`NOT_APPLICABLE` after a terminal no-Attempt decision.
Inside an `ObservationAttempt`, an Attempt necessarily exists and the local
`NONE` branch is therefore forbidden.
`QuarantineView.evidence_sigil` is null exactly for `NOT_REQUIRED` and is
non-null for `COMPLETE`, `PARTIAL`, or `FAILED`.
`ActorBinding.actor_sigil` covers canonical JSON of its other three fields.
The two authentication-context Sigils in an actor/Host pair are equal, and
`HostInvocationBinding.invocation_sigil` covers canonical JSON of its other
three fields. Both records and the exact `ChronicleActor` must equal the
authenticated MCP invocation context; caller text cannot substitute for
authentication evidence. `ChronicleActor.actor_id == ActorBinding.actor_id`.
The authenticated context enforces the closed kind mapping `USER -> human`,
`AGENT -> agent`, and `SYSTEM -> policy|tool`; it also supplies and validates
the exact Chronicle `host` and `authenticated_by` values for the same
authentication context. Neither is inferred from
`host_identity_sigil`, an invocation ID, or caller text. `ChronicleActor`
has no independent self-Sigil; its complete bytes are covered by the
acceptance authorization and transition-request self-Sigils. An
RFC-0012 cancellation event's `host_provenance_sigil` is exactly this
`invocation_sigil`.
For a terminal Attempt, `CleanupView` is byte-for-byte the corresponding
RFC-0012 terminal status/evidence components. Before any such component is
recorded, its fixed value is the applicable `NOT_STARTED`,
`NOT_APPLICABLE`, or `NOT_REQUIRED` enum and its evidence Sigil is null;
later nonterminal pages copy only durably recorded progress.

`execution-observation/1.0` assigns its top-level fields as follows:
the five immutable bindings use the aliases above; `job_state` is the exact
RFC-0012 JobState and `job_revision` is `U64`; `attempts` and
`worker_sessions` are sorted arrays of their view aliases; `lease_binding`
and `public_fence_binding` use their view unions; `assurance`,
`cancellation`, `terminal`, and `cleanup` use their aliases; `quarantine`,
`events`, `logs`, and `next_actions` are sorted arrays of the named aliases;
the through sequence and Sigil are `PositiveU63` and `Sigil`;
`next_cursor` is `ObservationCursor|null`. Attempts are unique and ordered by
retry ordinal; Worker Sessions are unique and ordered by
`(worker_id, worker_session_id)`; related entity IDs within an event are
unique and sorted by Unicode code point; events are ordered by sequence;
Quarantine members are unique and ordered by `(subject_kind, subject_id)`;
logs are unique and ordered by the fixed stream-kind order
`STDOUT`, `STDERR`, `STRUCTURED` and then `stream_id`; and next actions use
the printed action order.
The top-level Attempt-derived views select the current unresolved Attempt, or
the Job terminal event's selected Attempt after Job terminalization. When no
Attempt exists they use `LeaseView.NONE`, `PublicFenceView.NONE`, an
`AssuranceView` containing the requested tuple, `attempt_binding: NONE`, and
the current Job assurance binding, the fixed pre-attempt cleanup defaults,
and empty Quarantine and log arrays. Otherwise the top-level logs are exactly
the selected Attempt's three RFC-0012 Log Streams; logs from another retry
are not merged into this unqualified array. All top-level Attempt-derived
views equal that Attempt's entry byte-for-byte and never select a different
retry.

`CancellationView` uses a closed selector. If any state-changing
`job.cancellation_requested` exists in the fixed prefix, it selects the
lowest-sequence such event and remains `REQUESTED`; later terminal
observations do not replace it. Otherwise, if one or more state-neutral
`job.cancellation_observed` events exist, it selects the lowest-sequence one
as `OBSERVED_TERMINAL`. It is `NONE` only when neither event exists. Thus
arbitrarily many idempotency-distinct terminal observations cannot make the
single view ambiguous.

Request field bindings are exact. Start embeds
`execution-specification/1.0` and an `Opaque` non-secret idempotency key.
Observe uses `JB-ID`, an integer limit in `1..256`, and optional
`ObservationCursor`. Cancel uses an `Opaque` cancellation ID and idempotency
key, `JB-ID`, `Sigil`, `U64` expected revision, `Opaque` reason,
`ActorBinding`, `HostInvocationBinding`, and `Timestamp`. Get-result uses
`JB-ID`. Accept-result uses `JB-ID`, `Sigil`, and an `Opaque` idempotency key.

## Start

`benchwork_start_job` accepts exactly one
`execution-start-request/1.0`:

```json
{
  "schema_version": "execution-start-request/1.0",
  "execution_specification": {},
  "idempotency_key": "client-generated-non-secret-value"
}
```

The nested document is the complete `execution-specification/1.0`; a path or
URI to an unvalidated document is not accepted. The request Schema does not
contain `command`, `shell`, `argv`, `cwd`, arbitrary environment variables,
credential values, raw input bytes, raw output paths, or untyped backend
configuration.

Executable and process authority comes only from the pinned
`capability-contract/2.0`, `task-capsule/2.0`, and Execution Specification.
Start resolves the exact registered Worker contract class and permitted
backend profile. It verifies that at least one installed profile can satisfy
the request, but it does not bind a mutable Worker session or instance to the
Job. RFC-0012 selects and revalidates a Worker independently for each Attempt,
including retries.

Before recording a Job, Start verifies:

1. Registry, Capability, Task, Snapshot, Circle, Execution Specification, and
   assurance-profile Schemas and Sigils;
2. that every execution permission is present in both the Capability and Task;
3. the final RFC-0011 approval requirement derived from the Capability,
   approval-bound side effects, Task policy, and Execution Specification; when
   that value is `REQUIRED`, the complete Receipt, Event, immutable transition
   request, content-derived subject, Ward decision, and preapproval
   Specification chain must validate, including recomputation with exactly
   `specification_sigil`, `approval_receipt_id`, and
   `approval_receipt_sigil` omitted;
4. Snapshot integrity and freshness;
5. the requested assurance level, exact profile and conformance-suite Sigils,
   permitted backend profiles, and control minima;
6. existence and integrity of every required input Blob;
7. output, log, time, process, resource, and storage bounds;
8. existence of an installed eligible Worker-contract class and backend
   profile, without claiming that a live Worker is already eligible; and
9. the idempotency key and complete start-request Sigil.

Before that lookup or any Storage write, Start derives:

```text
submission_idempotency_key_sigil =
  Sigil(["execution-start-idempotency-key/1.0", idempotency_key])

job_id =
  "JB-" + UPPER_HEX(SHA256(canonical_json(
    ["execution-job-id/1.0",
     execution_specification.task_binding.task_id,
     submission_idempotency_key_sigil])))
```

The RFC-0012 `START_JOB` idempotency scope is the Task ID, so the unique key
is `(START_JOB, task_id, submission_idempotency_key_sigil)`, not a newly
allocated Job ID. The complete `start_request_sigil` is its immutable value.
The caller can therefore reconstruct the same 67-byte `JB-ID` after a lost
response or restart, and changed request content under the same Task/key is a
conflict before a second Job or input plan exists.

Before a new Start persists any Job-input ESM or causes any Storage side
effect, it holds RFC-0013's outer canonical-reference gate, replays the
current Chronicle Head, validates the complete exact Phase 3
`ChronicleHeadRef`, and requires `event_count < U63_MAX`. It durably freezes
that value for the immutable RFC-0012 Job's `admission_chronicle_head` and
the accompanying `admission_chronicle_head_evidence` with exactly:

```text
profile = PHASE3_CHRONICLE_HEAD_ADMISSION_V1
job_id
start_request_sigil
observed_chronicle_head
observed_at
validator_build_sigil
evidence_sigil
```

`job_id` and `start_request_sigil` equal the enclosing Job,
`observed_chronicle_head` equals `admission_chronicle_head`,
`observed_at` is the trusted observation time, and `evidence_sigil` is the
canonical-JSON self-Sigil of the complete evidence object with only itself
omitted. A Job-ID-keyed single-assignment pending resolver durably freezes
only this seven-field admission evidence before ESM creation; an exact retry
reuses it, while different bytes at that Job ID are an integrity failure.
Once its root bindings are known, the immutable
`execution-job/1.0` and its `job_binding_sigil` cover both complete frozen
admission fields.

Only after those admission fields are frozen may Start persist the one
complete RFC-0012 `execution-storage-root-manifest/1.0` Job-input root plan
for that Job. Its
owner binding contains the exact start-request, Task, Specification, and
input-set bindings; its entries and `blob_refs` are the complete typed input
closure; and its preallocated protection plan fixes the later
Reference-Set-registration and hold Event IDs. The manifest is
single-assignment at its deterministic ESM-ID and durable before either
Storage event. An
orphan hold from an interrupted plan is either revalidated and reused by the
same derived Job before any release authorization exists, or released only
through the deterministic RFC-0012 `ORPHAN_ABORT` EHR. The latter permanently
vetoes activation of that ESM/root; the same Job cannot create a fresh hold or
later submit, and the hold can never select another Job identity.

Start first acquires RFC-0013's outer canonical-reference gate. While holding
it, the service briefly replays the Execution Journal and checks the
Task-scoped idempotency binding. An exact prior Start validates and reuses its
frozen admission Head and evidence, verifies its existing roots, and returns
that Job without registering new holds; conflicting reuse fails. Recovery
also replays the then-current Chronicle Head under the gate and again requires
its valid `event_count < U63_MAX`; it never refreshes the frozen Job evidence.
A new Start performs the admission replay and evidence freeze above, then
revalidates every input Blob and resolves the exact ESM. For a
non-empty ESM `blob_refs` set, Storage registers the Reference Set whose source
is exactly `{kind: OPERATIONAL_CONTROL_RECORD, identity: manifest_id,
schema_version: execution-storage-root-manifest/1.0,
sigil: manifest_sigil}`, uses the installed RFC-0012 manifest extractor and
validator, uses the ESM-ID-derived registration Event ID, emits exactly one
`JOB_REQUIRES_BLOB` edge per `blob_refs` member, resolves
`SP-EXECUTION-ROOT-HOLD-V1`, and appends the planned Reference-Set hold with
the exact post-registration authorization Sigil. The resulting RFC-0012
`storage_root_binding` carries `root_kind`, owner IDs, the manifest ID and
Sigil, Reference Set ID and Sigil, hold ID, and hold-set Event. An ESM with an
empty `blob_refs` set has `protection_plan: NONE` and produces no fabricated
Reference Set, hold, or root. Start releases the Storage Journal lock, takes
the execution-journal writer lock, replays current state, rechecks
idempotency and due global integrity conditions, re-resolves the hold as
`ACTIVE`, proves the deterministic EHR absent, and appends exactly
`job.submitted` with the matching sorted RFC-0012 `job_storage_roots`. That
event creates a `SUBMITTED` Job and binds the idempotency-key Sigil, complete
request Sigil, Job binding Sigil, root bindings, and revision. Only after the
event is durable does Start release the execution lock and outer gate. The
`job.submitted` payload copies `admission_chronicle_head` and
`admission_chronicle_head_evidence` byte-for-byte from the immutable Job; a
missing field, changed Head, or evidence self-Sigil mismatch invalidates
replay.

A crash after ESM durability reuses that exact single-assignment record; a
crash after a hold but before `job.submitted` leaves an orphan conservative
root. Gate-held recovery releases it only after verified execution-journal
replay proves that the Job event did not commit and it durably installs the
`ORPHAN_ABORT` EHR before the Storage release. A missing or released hold,
pre-existing EHR, changed ESM byte, incomplete manifest edge, changed Blob, or
mismatched Reference Set aborts Start before Job creation. Start returns only after the
event, ESM, Reference Set, hold, and referenced immutable inputs are durable.
An invalid, unavailable, ambiguous, or exhausted admission Head returns the
applicable closed `CHRONICLE_UNAVAILABLE` branch before ESM creation,
Reference Set registration, hold creation, or any execution-journal append.

The scheduler later appends the distinct `job.queued` event after admission
remains valid. Start may therefore return a `SUBMITTED` observation, or a later
state if the scheduler won a subsequent lock, but it never invents an atomic
"Job-created plus dispatch" event. A crash between `job.submitted` and
`job.queued` leaves one replayable `SUBMITTED` Job that recovery can queue or
stop; it cannot create a duplicate Job or Attempt.

The same Task, idempotency key, and start-request Sigil return the original
derived Job identity and a fresh observation. Reusing that Task/key with
different content fails with `IDEMPOTENCY_CONFLICT`; the same key under a
different Task has a different explicit scope.

Success data is `execution-observation/1.0`.

## Observe

`benchwork_observe_job` accepts a closed
`execution-observe-request/1.0` containing:

- `job_id`;
- `limit`, an integer in the implementation's advertised range and no greater
  than the contract maximum; and
- optional `cursor`.

On the first page the service verifies the current execution-journal prefix
and fixes:

- `through_journal_sequence`;
- `through_event_sigil`; and
- the Job revision observed at that prefix.

The cursor is a canonical, non-secret, content-bound object containing the Job
ID, the last returned sequence, and the same fixed-prefix sequence and event
Sigil. A later page validates that this prefix still exists with the same
Sigil and reads only Job-related events after the cursor and no later than the
fixed prefix. Events appended after the first page appear only in a new
first-page observation. A cursor for another Job, a non-ancestor prefix, an
event-Sigil mismatch, or a compacted prefix that cannot be verified fails with
`STALE_CURSOR`; it is never silently retargeted.

`execution-observation/1.0` contains:

- immutable Job, Task, Capability, Snapshot, and Execution Specification
  identities;
- current Job state and exact `job_revision` at the fixed prefix;
- ordered bounded Attempt summaries and their revisions;
- the stable Worker definition and immutable Worker Session ID and binding
  Sigil for each allocated Attempt;
- the current Lease state and public fence tuple when one exists;
- public executor epoch, fencing generation, fence floor, and terminal
  tombstone state needed to explain eligibility;
- requested assurance and finalized assurance evaluation when present;
- cancellation, terminal, cleanup, and quarantine summaries;
- one ordered bounded page of operational events;
- bounded log metadata or Blob references, never a live or unbounded stream;
- `through_journal_sequence`, `through_event_sigil`, and optional next cursor;
  and
- bounded next actions appropriate to the observed state.

Ordering is by journal sequence, not timestamp. Absolute Host paths, Lease
credentials, credential proofs, secrets, raw environment values, internal lock
data, and backend-private handles are never returned. Public fence evidence is
not a Lease credential and may be returned when required for provenance.

Observe is read-only. A missing, corrupt, or replay-inconsistent journal fails
closed rather than reporting inferred state from live processes, queues, or
Crucible paths.

## Cancel

`benchwork_cancel_job` accepts a closed
`execution-cancel-request/1.0` containing:

- cancellation request ID;
- bounded non-secret idempotency key;
- Job ID and immutable Job binding Sigil;
- `expected_job_revision`;
- bounded non-empty reason;
- actor type and actor ID;
- Host identity and invocation provenance; and
- caller-observed request time.

The trusted Executor receive time, not the caller timestamp, determines
ordering. Before taking the journal writer lock, the MCP adapter verifies the
Actor and Host Invocation Sigils against the authenticated call context. Under
the lock, the complete request Sigil covers both closed bindings, and the
RFC-0012 cancellation payload copies
`host_provenance_sigil = host_invocation.invocation_sigil`; any mismatch with
the authenticated context or any attempted rebinding fails before an event.
The service then:

1. replays the current verified Head;
2. evaluates trusted deadlines and commits any already-due timeout,
   heartbeat-loss, claim-expiry, or Lease-expiry events first;
3. compares `expected_job_revision` with the resulting current revision;
4. validates the Job binding, actor, Host provenance, and idempotency binding;
5. appends the RFC-0012 cancellation event durably;
6. latches stop, revokes or fences current authority, and prevents retry;
7. signals the backend to revoke handles and terminate the process tree; and
8. returns a fresh observation.

If a due deadline changes the state or revision before cancellation can
commit, the caller receives `EXECUTION_CONFLICT` and the new revision; the
deadline is not relabeled cancellation.

For a non-terminal Job, the cancellation event binds the complete request and
drives the RFC-0012 stop path. For an already terminal Job, the Executor
appends the RFC-0012 state-neutral `job.cancellation_observed` event. It binds
the request and idempotency-key Sigils but does not change the terminal state,
terminal cause, or Job revision. This durable no-op allows restart-safe replay
and conflicting-key detection without pretending that a terminal Job was
cancelled again.

The response distinguishes `cancellation_requested` from terminal
`CANCELLED`. Repeating the same request returns the original cancellation
record and a current observation. Reusing its key for different content fails
with `IDEMPOTENCY_CONFLICT`.

Cancellation preserves logs, outputs, failed Attempts, partial material, and
secondary facts. It cannot roll back already completed external side effects.
Success data is `execution-observation/1.0`.

## Get Job Outcome

`benchwork_get_job_result` accepts only
`execution-get-result-request/1.0`, which contains `job_id`.

The operation is read-only. A non-terminal Job returns
`EXECUTION_NOT_READY`. For a terminal Job, the service verifies the journal
prefix through the terminal Job event and deterministically derives one
`execution-job-outcome/1.0`. It does not rely on a projection cache, live
process, mutable path, or Worker assertion.

The closed Outcome has exactly these top-level fields:
`schema_version`, `outcome_id`, `job_id`, `job_binding_sigil`,
`job_terminal`, `task_binding`, `program_id`, `capability_binding`,
`snapshot_binding`, `circle_binding`, `approval_binding`,
`execution_specification_binding`, `attempt_summaries`,
`selected_attempt_binding`, `result_binding`, `completion_anchor_binding`,
`first_stop_or_fence_binding`, `lease_terminal_binding`,
`authority_binding`, `final_fence_binding`, `runtime_outcome`,
`terminal_source_binding`,
`terminal_source_observation`,
`assurance_context_binding`, `attempt_assurance_binding`,
`job_assurance_binding`,
`control_evidence_set_binding`, `quarantine_binding_set_binding`,
`terminalization_storage_manifest_binding`, `output_root_protection`,
`budget_binding`, `outputs`, `storage_observation_binding`, `logs`,
`resource_evidence`,
`acceptance_eligible`, `ineligibility_reasons`, `derivation_profile`,
`terminal_recorded_at`, and `outcome_sigil`. Every nested binding is closed;
nullable or union branches are only those stated below.

At top level, `schema_version` is constant, `outcome_id` is `OJ-ID`,
`job_id` is `JB-ID`, every named Sigil is `Sigil`, `program_id` uses the
canonical Program-ID domain, `acceptance_eligible` is `boolean`,
`ineligibility_reasons` is the closed set below, and
`terminal_recorded_at` is `Timestamp`. Binding, summary, output, log, and
resource fields use only the closed definitions below.

The executable Outcome Schema assigns the following exact closed shapes:

- `job_terminal` has exactly `job_revision`, `state`, `transition_cause`,
  `event_id`, `event_sequence`, and `event_sigil`. `state` is exactly
  `SUCCEEDED`, `FAILED`, `CANCELLED`, `TIMED_OUT`, or `POLICY_VIOLATION`;
  revision and sequence are `U64` and `PositiveU63`, event ID is `JE-ID`,
  event Sigil is `Sigil`, and `transition_cause` imports RFC-0012's exact
  closed object;
- `task_binding` has exactly `task_id` and `task_capsule_sigil`;
  `capability_binding` has exactly `capability_id`, `contract_version`, and
  `capability_contract_sigil`; `snapshot_binding` has exactly `snapshot_id`
  and `snapshot_sigil`; `circle_binding` has exactly `circle_id` and
  `circle_sigil`; and `execution_specification_binding` has exactly
  `specification_id` and `specification_sigil`;
- `approval_binding` is exactly
  `NOT_REQUIRED {kind, ward_decision_id, ward_decision_sigil}` or
  `REQUIRED {kind, ward_decision_id, ward_decision_sigil,
  approval_receipt_id, approval_receipt_sigil}`;
  IDs use their owning Ward/Receipt domains and Sigils are `Sigil`;
- `authority_binding` is exactly `NO_ATTEMPT {kind}`,
  `ASSIGNED_NO_LEASE {kind, allocation_executor_instance_id,
  allocation_executor_epoch, allocation_executor_build_sigil, job_id,
  attempt_id, fencing_generation}`, or
  `LEASED {kind, executor_instance_id, executor_epoch,
  executor_build_sigil, public_fence_tuple}`. `public_fence_tuple` is
  byte-for-byte RFC-0012's
  exact `{journal_id, executor_epoch, job_id, attempt_id, lease_id,
  fencing_generation}` object. The assigned branch carries only allocation
  event provenance, has no Lease-bound epoch or public tuple, uses the
  immutable Attempt generation, and is legal only when no Lease offer ever
  existed. Its build Sigil equals the allocation Event's epoch-bound
  `executor_build_sigil`. The leased branch's build Sigil equals the
  `lease.offered` Event's epoch-bound value. Executor IDs use `XI-ID`, epochs
  and generations are `U64`, every build Sigil is `Sigil`, and Job and
  Attempt IDs are `JB-ID` and `AT-ID`;
- `assurance_context_binding` is
  `NO_ATTEMPT {kind, requested_level, profile_version, profile_sigil,
  conformance_suite_id, conformance_suite_sigil}` or
  `ATTEMPT {kind, requested_level, profile_version, profile_sigil,
  conformance_suite_id, conformance_suite_sigil, backend_identity,
  backend_configuration_sigil, host_identity_sigil}`. The requested tuple is
  byte-for-byte equal to the Job and Specification; the Attempt branch is
  byte-for-byte equal to the selected Attempt and realized-claim environment.
  Requested level is `SANCTUM-A0|SANCTUM-A1|SANCTUM-A2`, versions and backend identity are `Opaque`,
  and every named Sigil is `Sigil`;
- `runtime_outcome` is exactly
  `NO_ATTEMPT {kind, computation_status, worker_status,
  process_termination_status, handle_revocation_status, cleanup_status,
  mutable_resource_isolation_status, output_publication_status,
  quarantine_status, termination_evidence_sigil,
  handle_disposition_evidence_sigil, cleanup_summary_sigil,
  quarantine_evidence_sigil, log_closure_sigil, output_closure_sigil,
  accounting_capture_event_id, accounting_capture_event_sigil}` or the same
  fields under `ATTEMPT`, plus no extras. In `NO_ATTEMPT`, all eight
  status values are respectively `NOT_STARTED`, `NOT_REPORTED`,
  `NOT_STARTED`, `NOT_APPLICABLE`, `NOT_APPLICABLE`, `NOT_APPLICABLE`,
  `NOT_APPLICABLE`, and `NOT_REQUIRED`, and all eight trailing evidence,
  closure, and accounting values
  are null. In `ATTEMPT`, every status, evidence, closure, and accounting
  binding is copied byte-for-byte from the selected Attempt's exact terminal
  evidence.
  `mutable_resource_isolation_status` is exactly `NOT_APPLICABLE`,
  `VERIFIED_ISOLATED`, `QUARANTINED`, or `UNVERIFIED`;
  `output_publication_status` is exactly `NOT_APPLICABLE`, `VERIFIED`,
  `QUARANTINED`, or `FAILED`. The remaining exact RFC-0012 enums are
  `computation_status:
  NOT_STARTED|COMPLETED|FAILED|UNKNOWN`,
  `worker_status:
  NOT_REPORTED|COMPLETED|FAILED|CANCELLED|TIMED_OUT|LOST`,
  `process_termination_status:
  NOT_STARTED|EXITED|TERMINATED|QUARANTINED|UNVERIFIABLE`,
  `handle_revocation_status:
  NOT_APPLICABLE|REVOKED|FENCED|QUARANTINED|UNVERIFIABLE`,
  `cleanup_status:
  NOT_APPLICABLE|VERIFIED|PARTIAL|FAILED|QUARANTINED`, and
  `quarantine_status: NOT_REQUIRED|COMPLETE|PARTIAL|FAILED`. The executable
  Schema references those RFC-0012 `$defs` rather than cloning them;
- `attempt_assurance_binding` is `NONE {kind}` only when no Attempt exists;
  otherwise it is byte-for-byte one of RFC-0012's terminal
  `CLAIMED`, `UNMET`, or `UNVERIFIABLE` State branches, including the exact
  evaluation event ID, Sigil, sequence, claim-or-reason fields, and evidence
  set. `job_assurance_binding` is byte-for-byte one of RFC-0012's terminal
  `CLAIMED`, `UNMET`, `UNVERIFIABLE`, or `NOT_APPLICABLE` branches; the last
  branch is legal only when no Attempt exists. Neither Outcome binding admits
  RFC-0012's nonterminal `PENDING` branch;
- `control_evidence_set_binding` and `quarantine_binding_set_binding` are
  each `NOT_APPLICABLE {kind}` exactly when no Attempt exists. Otherwise each
  is byte-for-byte the selected terminal Attempt's corresponding RFC-0012
  `FROZEN` ID-and-Sigil pair, the pair carried by `ACCOUNTING_CAPTURED`, and
  the pair copied into the observation document. Both complete set documents
  and every nested reference resolve and validate before derivation;
- `terminalization_storage_manifest_binding` is
  `NOT_APPLICABLE {kind}` exactly when no Attempt exists. Otherwise it is
  byte-for-byte the selected terminal Attempt's RFC-0012
  `FROZEN {kind, storage_root_manifest_id,
  storage_root_manifest_sigil}` branch carried by `ACCOUNTING_CAPTURED` and
  copied into the output-storage observation. The pair resolves exactly one
  `execution-storage-root-manifest/1.0` with `root_kind: ATTEMPT_OUTPUT`,
  the same Job and selected Attempt owner, complete typed entries and
  `blob_refs`, valid per-entry transfer/provenance or Quarantine origin, and
  the one immutable protection plan;
- `output_root_protection` is `NOT_APPLICABLE {kind}` exactly when no Attempt
  exists. Otherwise it is byte-for-byte the selected Attempt's RFC-0012
  terminal `NO_HOLD {kind, terminalization_storage_manifest_binding}` or
  `HELD {kind, terminalization_storage_manifest_binding,
  storage_root_binding}` branch, also carried by `ACCOUNTING_CAPTURED` and
  copied into the output-storage observation. Both copies of the manifest
  binding equal the top-level value. `NO_HOLD` requires the resolved
  manifest's `blob_refs` to be empty. `HELD` requires the exact RFC-0012
  `ATTEMPT_OUTPUT` root binding, including the same manifest ID and Sigil,
  Reference Set ID and Sigil, hold ID, and hold-set Event; that Reference
  Set's source is the exact manifest control record and its
  `CONTROL_RETAINS_BLOB` edges equal the complete manifest `blob_refs`
  projection. The selected Attempt terminal Event's `output_storage_roots`
  is empty exactly for `NO_HOLD` and otherwise contains exactly that one
  `HELD.storage_root_binding`. `HELD` records the exact protection installed
  at terminalization; it does not assert that the execution-owned hold is
  still `ACTIVE` at a later Outcome read. Its current RFC-0013 projection is
  either that exact `ACTIVE` hold or the same hold advanced once to
  `RELEASED` by the exact RFC-0012 `OUTPUT_DEADLINE` EHR and release Event.
  A selected acceptance-eligible Attempt always uses `HELD` because its three
  valid Log observations make the managed Blob closure non-empty;
- `budget_binding` has exactly `job_budget_ledger` and
  `selected_attempt_settlement`. `job_budget_ledger` is RFC-0012's exact
  closed ledger: each of the eight dimensions carries `limit`, `reserved`,
  `consumed`, and
  `exhaustion_status: AVAILABLE|EXHAUSTED|EXCEEDED`, plus the ledger Sigil.
  `EXCEEDED` is produced only by trusted settlement proving actual usage above
  the reserved limit and makes acceptance ineligible. The selected settlement
  is `NONE {kind}` iff no Attempt exists or is byte-for-byte RFC-0012's
  `SETTLED {kind, event_id, event_sigil, accounting_capture_event_id,
  accounting_capture_event_sigil, usage_status}` branch;
- `outputs` imports RFC-0012's exact
  `attempt_outputs_none_member|attempt_output_member` union. With a selected
  Attempt it is byte-for-byte the complete first observation-member group,
  including the one explicit `ATTEMPT_OUTPUTS_NONE` sentinel or every sorted
  output member and its complete storage union; with no Attempt it is empty;
- `logs` imports RFC-0012's exact `log_stream_member`. With a selected
  Attempt it is byte-for-byte the complete three-member Log group in fixed
  `STDOUT`, `STDERR`, `STRUCTURED` order, including `EMPTY` content and the
  complete storage union; with no Attempt it is empty;
- `resource_evidence` imports RFC-0012's exact
  `resource_evidence_none_member|resource_evidence_member` union. With a
  selected Attempt it is byte-for-byte the complete resource group,
  including its explicit `RESOURCE_EVIDENCE_NONE` sentinel or every sorted
  Blob-bearing entry with parent control-evidence and phase-entry identities;
  with no Attempt it is empty;
- `terminal_source_observation` is `NO_ATTEMPT {kind}` exactly when no
  Attempt exists. Otherwise it imports and equals byte-for-byte exactly one
  RFC-0012 `terminal_source_not_applicable_member`,
  `terminal_source_none_member`, or `terminal_source_member`, including its
  complete storage union when present; and
- `derivation_profile` has exactly `profile_id`, `profile_version`,
  `algorithm_sigil`, `outcome_schema_sigil`, and
  `imported_schema_set_sigil`. `profile_id` and `profile_version` are the
  protocol constants `execution-job-outcome-v1` and `1.0`; the remaining
  fields are `Sigil`.

There is one derivation profile for `execution-job-outcome/1.0`, not a runtime
choice. `algorithm_sigil` is the Sigil of this exact canonical JSON array:

```json
[
  "execution-job-outcome-derivation-algorithm/1.0",
  "VALIDATE_SOURCE_PREFIX",
  "COPY_CLOSED_BINDINGS",
  "RECONSTRUCT_SELECTED_OBSERVATION",
  "EVALUATE_ALL_REASONS_IN_ENUM_ORDER",
  "SET_ELIGIBLE_IFF_EMPTY",
  "DERIVE_OJ_ID",
  "DERIVE_OUTCOME_SIGIL"
]
```

`outcome_schema_sigil` is the canonical installed Schema Sigil.
`imported_schema_set_sigil` is the Sigil of the canonical JSON array of every
transitive `$ref` reachable from `execution-job-outcome/1.0`, with each closed
entry exactly `{schema_id, schema_sigil}`, sorted strictly by `schema_id`
unsigned UTF-8 bytes and unique by that key. The implementation binary's
identity never enters this profile; its separate epoch-bound provenance is
`executor_build_sigil`. Any algorithm or reachable Schema-set change requires
a new Outcome Schema version. Re-derivation must retain the old profile and
schemas or fail closed; it cannot silently use an upgraded implementation.

The Outcome Schema publishes its exact closed `authority_binding`,
`assurance_context_binding`, and selected `worker_session_binding` at
`#/$defs/authority_binding`, `#/$defs/assurance_context_binding`, and
`#/$defs/worker_session_binding`. RFC-0014 validation records import these
canonical definitions and may not replace them with summary Sigils.

Every imported observation member above is a canonical URI `$ref` to
`https://benchwork.dev/schemas/execution-output-storage-observation-set/1.0#/$defs/<name>`.
The Outcome Schema does not clone, rename, flatten, omit, or add nullable
alternatives to those branches. For a selected Attempt, the ordered groups
are sliced from its one resolved observation document and
`outputs || logs || resource_evidence || [terminal_source_observation]`
reconstructs that document's exact `members` array byte-for-byte. For a
no-Attempt Outcome no observation-set resolver runs:
`storage_observation_binding` is `NOT_APPLICABLE`, the three arrays are empty,
and `terminal_source_observation` is `NO_ATTEMPT`; the reconstruction
assertion is inapplicable rather than an assertion about a nonexistent set.

`ineligibility_reasons` is a sorted unique array drawn exactly from:

```text
JOB_NOT_SUCCEEDED
ATTEMPT_ABSENT
ATTEMPT_NOT_SUCCEEDED
RESULT_REQUIREMENT_UNMET
COMPLETION_NOT_ESTABLISHED
AUTHORITY_LOST_BEFORE_COMPLETION
ATTEMPT_AUTHORIZATION_INVALID
WORKER_SESSION_EVIDENCE_MISSING
LEASE_TERMINAL_EVIDENCE_MISSING
FINAL_FENCE_EVIDENCE_MISSING
BUDGET_UNSETTLED
BUDGET_EXCEEDED
ACCOUNTING_UNVERIFIED
TERMINATION_UNVERIFIED
HANDLE_REVOCATION_UNVERIFIED
CLEANUP_UNVERIFIED
MUTABLE_RESOURCE_UNSAFE
OUTPUT_INVALID
OUTPUT_UNAVAILABLE
OUTPUT_QUARANTINED
TERMINAL_SOURCE_INVALID
TERMINAL_SOURCE_QUARANTINED
ASSURANCE_UNMET
ASSURANCE_UNVERIFIABLE
CONTROL_EVIDENCE_INVALID
STORAGE_OBSERVATION_INVALID
INTEGRITY_FAILURE
```

Derivation first requires every source record, imported branch, deterministic
ID, self-Sigil, owner relationship, and historical prefix to be structurally
and cryptographically valid. Failure at that layer aborts derivation; it does
not manufacture an Outcome containing a reason. A reason describes validly
encoded negative operational evidence. With that prerequisite, the following
table is exhaustive and each reason is present if and only if its predicate is
true:

| Reason | Exact predicate |
| --- | --- |
| `JOB_NOT_SUCCEEDED` | `job_terminal.state != SUCCEEDED`. |
| `ATTEMPT_ABSENT` | `selected_attempt_binding.kind == NONE`. |
| `ATTEMPT_NOT_SUCCEEDED` | A selected Attempt exists and its matching summary `terminal_state != SUCCEEDED`. |
| `RESULT_REQUIREMENT_UNMET` | The Specification mode is `REQUIRED` and the selected result is absent or not `ACCEPTED`; the mode is `OPTIONAL` and the selected result is `REJECTED`; or the mode is `FORBIDDEN` and the selected result is not `NONE`. |
| `COMPLETION_NOT_ESTABLISHED` | A selected Attempt exists and its completion anchor is not the one legal `RESULT_ACCEPTED` or `NO_RESULT` branch for the result mode and result binding, does not resolve its named Event, or occurs after the terminal decision. |
| `AUTHORITY_LOST_BEFORE_COMPLETION` | A selected Attempt's first stop-or-fence effective sequence is less than or equal to its completion-anchor sequence, or the fixed prefix records an earlier Lease expiry, revocation, fence, policy loss, or ownership loss. |
| `ATTEMPT_AUTHORIZATION_INVALID` | Any summary's immutable requirement and state violate RFC-0012's `NONE/NONE`, legal non-selected `REQUIRED/PENDING`, or exact `REQUIRED/BOUND` matrix; any bound subject, effects, Receipt, or Attempt owner mismatches or is reused; or the selected successful Attempt is not `NONE/NONE` or `REQUIRED/BOUND`. |
| `WORKER_SESSION_EVIDENCE_MISSING` | A selected successful Attempt lacks a complete `BOUND` Worker Session, or any selected Attempt for which a Lease was offered has a missing, unresolved, wrong-owner, or wrong-epoch Session binding. |
| `LEASE_TERMINAL_EVIDENCE_MISSING` | A selected successful Attempt has no offered Lease, or any selected Attempt with an offered Lease lacks the exact matching terminal Lease branch and terminal Event. |
| `FINAL_FENCE_EVIDENCE_MISSING` | The final-fence branch is not `NO_ATTEMPT` with floor zero for no Attempt, `ASSIGNED_NO_LEASE` with the exact Attempt generation and terminal Event for an Attempt that never had an offer, or `TOMBSTONE` with the exact Lease terminal Event and final floor for an offered Lease. |
| `BUDGET_UNSETTLED` | Any allocated Attempt lacks its unique settlement, or the selected settlement is absent or does not bind the exact accounting-capture Event. |
| `BUDGET_EXCEEDED` | Any final Job budget dimension has `exhaustion_status == EXCEEDED`. |
| `ACCOUNTING_UNVERIFIED` | A selected Attempt's accounting capture or settlement has `usage_status != MEASURED`, or their Event IDs and Sigils do not agree. |
| `TERMINATION_UNVERIFIED` | A selected Attempt's process status is neither `EXITED` nor `TERMINATED`, or its required termination evidence is absent. |
| `HANDLE_REVOCATION_UNVERIFIED` | A selected Attempt's handle status is not `NOT_APPLICABLE`, `REVOKED`, or `FENCED`, or a non-`NOT_APPLICABLE` branch lacks its required evidence. |
| `CLEANUP_UNVERIFIED` | A selected Attempt's cleanup status is not `VERIFIED` or its cleanup evidence is absent. |
| `MUTABLE_RESOURCE_UNSAFE` | A selected Attempt's isolation status is neither `NOT_APPLICABLE` nor `VERIFIED_ISOLATED`. |
| `OUTPUT_INVALID` | The result/output group violates the Specification's mode, logical-name, Schema, count, or byte rules; output publication is `FAILED`; an output uses storage `NONE`; or its member Blob identity or size disagrees with its storage branch. |
| `OUTPUT_UNAVAILABLE` | An output has `QUARANTINE_TERMINAL_NEGATIVE`, or a non-quarantined output has a `BLOB` branch whose terminal status or current frozen availability is not `AVAILABLE`, whose Replica is not `SELECTED` and `AVAILABLE`, or whose selected verification is not valid at the frozen prefix. An `INCIDENT` output also satisfies this predicate. |
| `OUTPUT_QUARANTINED` | An output storage branch is retained `QUARANTINED`, or output publication status is `QUARANTINED` with the exact QBS `RETAINED` disposition. A terminal-negative quarantine does not satisfy this reason. |
| `TERMINAL_SOURCE_INVALID` | The Specification requires `CODE_MODIFICATION` and the direct and observation source bindings disagree, the policy or Base differs from the Specification, the `terminal_source_identity`/`terminal_source_sigil`/`storage_blob` null matrix is invalid, or a `VERIFIED` source violates source-tree identity, bundle BlobRef, count, byte, storage, or verification rules. |
| `TERMINAL_SOURCE_QUARANTINED` | The direct or observation terminal-source branch is `QUARANTINED`. |
| `ASSURANCE_UNMET` | Attempt or Job assurance is `UNMET`, or a claim does not meet the exact requested level, profile, suite, backend, and evidence requirements. |
| `ASSURANCE_UNVERIFIABLE` | Attempt or Job assurance is `UNVERIFIABLE`. |
| `CONTROL_EVIDENCE_INVALID` | The complete valid CES contains a realized control state below its required state, a still-applicable deficiency, or a QBS/control relationship that fails its semantic predicate. |
| `STORAGE_OBSERVATION_INVALID` | A Log or resource-evidence member has `NONE`, `QUARANTINED`, `QUARANTINE_TERMINAL_NEGATIVE`, non-`AVAILABLE`, non-`SELECTED`, mismatched, or unverifiable storage evidence; the terminalization storage manifest, its complete entry/Blob closure, protection plan, Reference Set, hold, or copied output-root-protection branch is missing or inconsistent; or a selected successful Attempt with a non-empty valid managed closure lacks the exact frozen `HELD` branch and its current exact `ACTIVE` or valid output-deadline `RELEASED` projection. Output and terminal-source member content errors use their dedicated reasons above. |
| `INTEGRITY_FAILURE` | The fixed prefix contains a durably recorded integrity gate or incident, or any referenced Blob has `INCIDENT` availability or a recorded verification failure. |

The implementation evaluates every row, never short-circuits at the first
failure, and constructs the set in exactly the printed enum order:

```text
reasons = []
for reason in printed_enum_order:
    if exact_predicate(reason):
        reasons.append(reason)
acceptance_eligible = (reasons == [])
```

Thus every applicable reason is retained and the same verified prefix yields
the same byte array across implementations. `acceptance_eligible` is true if
and only if this array is empty. `terminal_recorded_at` is copied from the
terminal Job event, and `outcome_sigil` covers every other field. Outcome IDs
are `OJ-` followed by the uppercase 64-hex SHA-256 digest of canonical JSON
`["execution-job-outcome-id/1.0", job_id,
job_terminal.event_sigil]`. This is the complete cross-implementation
derivation and matches `OJ-[A-F0-9]{64}`.

Every Job Outcome binds:

- Outcome ID and Outcome Sigil;
- Job ID, immutable Job binding Sigil, terminal Job revision, terminal status,
  stable cause, terminal event sequence, and terminal event Sigil;
- Task, Program, Capability, Snapshot, Circle, approval, and Execution
  Specification identities and Sigils;
- every Attempt's immutable authorization requirement and exact terminal
  authorization state; a `REQUIRED` successful Attempt resolves one
  purpose-bound subject/Receipt pair unique to that Attempt, while a `NONE`
  requirement has state `NONE`; `PENDING` or a reused/mismatched pair adds
  `ATTEMPT_AUTHORIZATION_INVALID`;
- RFC-0012's exact sorted `attempt_summaries`, whose entries contain only
  `attempt_id`, `attempt_binding_sigil`, `retry_ordinal`, `terminal_state`,
  `terminal_event_id`, `terminal_event_sigil`, `worker_session_binding`,
  `attempt_authorization_requirement`,
  `attempt_authorization_state`,
  `budget_settlement_event_sigil`, and
  `assurance_evaluation_event_sigil`;
- the exact `selected_attempt_binding` union:
  `NONE {kind}` or
  `SELECTED {kind, attempt_id, attempt_binding_sigil,
  attempt_terminal_event_id, attempt_terminal_event_sigil,
  attempt_authorization_state, worker_session_binding, result_binding,
  completion_anchor_binding,
  first_stop_or_fence_binding, storage_observation_binding}`;
- a direct copy of the selected `result_binding`, exactly
  `NONE {kind}`,
  `ACCEPTED {kind, result_sigil, disposition_event_id,
  disposition_event_sigil, disposition_sequence}`, or
  `REJECTED {kind, message_sigil, disposition_event_id,
  disposition_event_sigil, disposition_sequence, reason_codes}`;
- a direct `completion_anchor_binding`, exactly
  `NOT_ESTABLISHED {kind}`,
  `RESULT_ACCEPTED {kind, event_id, event_sigil, sequence, result_sigil}`, or
  `NO_RESULT {kind, event_id, event_sigil, sequence,
  process_exit_observation_sigil}`. `RESULT_ACCEPTED` names
  `attempt.result_accepted`; `NO_RESULT` names `attempt.draining`, so a legal
  terminal Outcome can prove completion even when its result policy permits or
  requires no Worker Result;
- a direct `first_stop_or_fence_binding`, exactly `NONE {kind}` or
  `PRESENT {kind, event_id, event_type, event_sigil, effective_sequence}`.
  Ordering always compares `effective_sequence` against
  `completion_anchor_binding.sequence`; event sequence without the effective
  sequence is not equivalent evidence;
- the direct `authority_binding`, selected Attempt's Executor epoch and public
  fence tuple where a Lease existed, and exact
  `lease_terminal_binding`, which is `NONE {kind}` or
  `TERMINAL {kind, lease_id, lease_state, terminal_event_id,
  terminal_event_sigil, final_fence_floor, tombstone_event_sigil}`;
- a direct `final_fence_binding`, exactly
  `NO_ATTEMPT {kind, final_fence_floor}`,
  `ASSIGNED_NO_LEASE {kind, final_fence_floor, attempt_id,
  attempt_terminal_event_sigil}`, or
  `TOMBSTONE {kind, final_fence_floor, lease_id,
  lease_terminal_event_sigil, tombstone_event_sigil}`. `NO_ATTEMPT` requires
  floor zero, `ASSIGNED_NO_LEASE` proves the allocated Attempt never received
  a Lease, and `TOMBSTONE` proves the terminal Lease generation equals the
  final floor;
- process termination, handle revocation, cleanup, mutable-resource isolation,
  output publication, and quarantine status;
- a direct `terminal_source_binding`, exactly
  `NOT_APPLICABLE {kind}`,
  `VERIFIED {kind, crucible_base_identity, crucible_base_sigil,
  terminal_source_identity, terminal_source_sigil, storage_blob,
  retention_policy_sigil, file_count, byte_count, storage_status,
  verifier_evidence_sigil}`, or
  `QUARANTINED {kind, crucible_base_identity, crucible_base_sigil,
  terminal_source_identity, terminal_source_sigil, storage_blob,
  retention_policy_sigil, file_count, byte_count, storage_status,
  verifier_evidence_sigil, reason_codes}`. A non-null `storage_blob` is the
  exact RFC-0013 `BlobRef {blob_sigil, size_bytes}` copied from the resolved
  RFC-0012 `benchwork-source-tree/1.0.bundle_blob`; it is not reconstructed
  from `terminal_source_sigil` or `byte_count`;
- requested assurance tuple, separate `attempt.assurance_evaluated` and
  `job.assurance_evaluated` event IDs, sequences, Sigils, and closed evaluation
  enums, plus the optional realized assurance-claim Sigil;
- the complete control-evidence-set and quarantine-binding-set ID-and-Sigil
  pairs, terminalization storage-manifest pair, and exact output-root
  protection branch frozen before accounting capture;
- final Job aggregate-budget ledger Sigil, selected Attempt budget-settlement
  event ID and Sigil, and closed exhaustion status for every aggregate
  dimension;
- the exact bounded output, three-Log, resource-evidence, and terminal-source
  observation-member groups, including every explicit negative/content/storage
  union branch, together with the exact
  `storage_observation_binding` union:
  `NOT_APPLICABLE {kind}` or
  `FROZEN {kind, storage_journal_id, through_sequence,
  through_event_sigil, output_storage_observation_set_id,
  output_storage_observation_set_sigil}`;
- `acceptance_eligible` and a closed sorted set of stable ineligibility reasons;
  and
- deterministic derivation profile, terminal recorded time, and Outcome Sigil.

Every RFC-0012 branch named above imports its canonical `$def` byte-for-byte:
all objects are closed, every field is required, and a union branch cannot be
represented as null or as an abbreviated object. The two explicit no-Attempt
`NOT_APPLICABLE` terminalization-set branches are closed RFC-0015 wrapper
branches; each selected-Attempt alternative is the unmodified RFC-0012
`FROZEN` branch, never a clone or widening. The direct result,
completion-anchor, first-stop-or-fence, and storage-observation bindings must
equal the corresponding values inside `selected_attempt_binding` and the
terminal Job event wherever applicable. The
terminalization-storage-manifest and output-root-protection bindings equal
the selected terminal Attempt State, its `ACCOUNTING_CAPTURED` finalization
bindings, terminal Attempt Event evidence, and the resolved output-storage
observation byte-for-byte. The direct terminal-source binding equals the
selected Attempt's terminal evidence and the terminal Job event.
`worker_session_binding` is exactly `NONE {kind}` or
`BOUND {kind, worker_id, worker_binding_sigil, worker_session_id,
worker_session_binding_sigil}`.

The top-level `first_stop_or_fence_binding` is present even when no Attempt is
selected. With a selected Attempt it is byte-for-byte equal to the selected
copy; otherwise it is deterministically derived from the first effective Job
stop or fence trigger. When `attempt_summaries` is empty, the Outcome requires
`selected_attempt_binding: NONE`, `result_binding: NONE`,
`completion_anchor_binding: NOT_ESTABLISHED`,
`storage_observation_binding: NOT_APPLICABLE`, and
both terminalization-set bindings `NOT_APPLICABLE`, all three observation
arrays empty, and `terminal_source_observation: NO_ATTEMPT`, plus
`terminalization_storage_manifest_binding: NOT_APPLICABLE`,
`output_root_protection: NOT_APPLICABLE`,
`authority_binding: NO_ATTEMPT`, `assurance_context_binding: NO_ATTEMPT`,
and `final_fence_binding: NO_ATTEMPT` with floor zero.
`selected_attempt_binding: NONE` is legal if and only if
`attempt_summaries` is empty; otherwise `SELECTED` names the terminal
highest-retry-ordinal Attempt available at the Job decision.

`worker_session_binding: NONE` and `lease_terminal_binding: NONE` are legal
only when the Attempt never created a Lease offer. Once any Lease reaches
`OFFERED`, the Outcome must bind the immutable Worker Session and a terminal
Lease; a lost, expired, revoked, or fenced offer cannot be represented as
`NONE`.

For `terminal_source_binding`, `NOT_APPLICABLE` is legal only for Execution
Specification branch `NONE`. `CODE_MODIFICATION` requires `VERIFIED` or
`QUARANTINED`; only `VERIFIED` can be acceptance-eligible or Job
`SUCCEEDED`. `VERIFIED` requires non-null identities and Sigils,
`storage_status: DURABLE_VERIFIED`, and bounded counts. `QUARANTINED` requires
non-null Base, retention-policy, and verifier bindings,
`storage_status: QUARANTINED`, and a non-empty sorted `reason_codes` set from
RFC-0012's closed enum. Its `terminal_source_identity`,
`terminal_source_sigil`, and `storage_blob` are either all non-null or all
null; null is legal only when no content-identified source was retained and
then both counts are zero. When non-null, all three resolve one exact
`benchwork-source-tree/1.0` and its deterministic bundle. A quarantined branch is always
`acceptance_eligible: false`. For a no-Attempt `CODE_MODIFICATION` Job, that
branch uses the predeclared Base and retention policy, null source identity
and Sigil, null `storage_blob`, zero counts, `storage_status: QUARANTINED`,
`reason_codes: [SOURCE_ABSENT]`, and non-null verifier evidence.

The Outcome Sigil covers every field except itself. Outcome ID is
deterministically derived from the Job ID and terminal event Sigil. The
terminal event's recorded time is used; retrieval time is not embedded.
Repeated derivation from the same valid execution-journal prefix, the exact
referenced immutable storage/control observations, and the installed Schema
set is byte-for-byte equal. Later Replica availability or storage policy
changes never rewrite the terminal observation embedded in the Outcome.

Failed, cancelled, timed-out, policy-violating, lost, fenced, rejected, or
preflight-rejected work therefore remains retrievable even when no Worker
Result or assurance claim exists. Such an Outcome is normally ineligible, but
its absence of evidence is explicit rather than fabricated.

The Outcome does not contain a later Agent Result Receipt, Patch Proposal,
Patch promotion state, Run, or Artifact registration. Those are independent
canonical or derived objects and cannot mutate an execution Outcome.

The method never reads arbitrary Crucible paths and never returns unbounded
output bytes. Bytes are accessed only through RFC-0013's bounded Blob
operations.

## Accept Job Outcome

`benchwork_accept_job_result` accepts exactly:

```json
{
  "schema_version": "execution-accept-result-request/1.0",
  "job_id": "JB-...",
  "execution_job_outcome_sigil": "sha256:...",
  "idempotency_key": "client-generated-non-secret-value"
}
```

The request cannot provide replacement output, Worker Result, assurance
evidence, Patch content, Artifact URI, or canonical payload fields. The Job
Outcome Sigil is the immutable acceptance capsule binding the complete
post-terminal evidence set.

The MCP request is not the Athanor candidate. After authenticating the
invocation and completing the checks below, the coordinator constructs one
closed `agent-result-acceptance-transition-request/1.0`. Its fields have these
exact meanings and types:

- `schema_version` and `event_type` are constants
  `agent-result-acceptance-transition-request/1.0` and
  `agent-result.accepted`;
- `transition_request_id` is `ATR-` followed by the uppercase 64-hex SHA-256
  digest of canonical JSON
  `["agent-result-acceptance-transition-id/1.0", task_id,
  idempotency_key_sigil]`;
- `expected_chronicle_head` is RFC-0013's exact Phase 3-admissible
  `ChronicleHeadRef`; the older Chronicle Schema's unbounded integer domain is
  not widened into this request;
- `agent_result` is the complete Schema-valid `agent-result/2.0`, and
  `job_outcome_binding` has exactly `outcome_id: OJ-ID` and
  `outcome_sigil: Sigil`;
- `acceptance_request_sigil` covers the complete external
  `execution-accept-result-request/1.0`, and `idempotency_key_sigil` is the
  domain-separated Sigil of its key;
- `reference_sets` is a one-member array containing the exact RFC-0013
  `ReferenceSetRef`, and `managed_blob_sigils` is the complete sorted unique
  `1..4096` Blob-Sigil set produced by that Reference Set's typed closure.
  The closure includes every output, three Log contents, Blob-bearing resource
  evidence, and the terminal source's non-null `storage_blob.blob_sigil`,
  including every additional Blob reached through its resolved
  `benchwork-source-tree/1.0` manifest;
- `acceptance_storage_binding` is the exact alias above;
- `actor` and `host_invocation` are the closed bindings verified from the
  authenticated MCP context, not fields invented from caller text;
- `chronicle_actor` is the complete canonical `actor/1.0` value produced by
  that same authenticated context and is the exact future outer Chronicle
  Event actor;
- `acceptance_authorization` is the complete closed
  `agent-result-acceptance-authorization/1.0` document defined below;
  top-level `authorization_sigil` equals its self-Sigil byte-for-byte;
  `requested_at` is the trusted coordinator receive time; and
- `transition_request_sigil` covers canonical JSON of every preceding field
  with only itself omitted.

No field is nullable. Conditional approval fields are absent in the
`NOT_REQUIRED` branch rather than null. The candidate contains no
reference-intent identity, Storage intent event, Agent Result acceptance
Event ID or Sigil, resulting Head, or Agent Result acceptance Receipt. A
prior Execution-approval Event and Receipt may occur only inside the
`REQUIRED` authorization branch and necessarily predate the final Execution
Specification. The registered Reference Set can therefore be hashed into the
candidate, the candidate into the RFC-0013 intent, and the later intent
binding into the Chronicle event without a cycle.

### Acceptance authorization closure

`acceptance_authorization` repeats no independently selectable value. Its
exact equality rules are:

| Authorization field | Required transition/source value |
| --- | --- |
| `transition_request_id` | Transition request `transition_request_id`. |
| `event_type` | Transition request `event_type`, constant `agent-result.accepted`. |
| `expected_chronicle_head` | Transition request `expected_chronicle_head`. |
| `authority_subject.registry_binding` | Complete binding inside the resolved `task-capsule/2.0`. |
| `authority_subject.task_binding` | Agent Result Task ID and Capsule Sigil, also equal to the Outcome. |
| `authority_subject.program_id` | Agent Result and Outcome `program_id`. |
| `authority_subject.capability_binding` | Complete Agent Result and Outcome binding byte-for-byte. |
| `authority_subject.snapshot_binding` | Complete Agent Result and Outcome binding byte-for-byte. |
| `authority_subject.circle_binding` | Complete Outcome binding and resolved Task Circle identity. |
| `authority_subject.execution_specification_binding` | Complete Agent Result and Outcome binding byte-for-byte. |
| `authority_subject.job_binding` | Complete Agent Result Job binding and Outcome Job ID/Sigil. |
| `authority_subject.job_outcome_binding` | Transition request and Agent Result Job-Outcome binding. |
| `authority_subject.agent_result_sigil` | `agent_result.result_sigil`. |
| `acceptance_policy` | The complete Schema-valid policy record printed above. |
| `acceptance_request_sigil`, `idempotency_key_sigil` | Same-named transition-request fields. |
| `reference_sets`, `managed_blob_sigils` | Same-named transition-request arrays byte-for-byte. |
| `acceptance_storage_binding` | Same-named transition-request binding byte-for-byte. |
| `actor`, `host_invocation`, `chronicle_actor`, `requested_at` | Same-named transition-request values byte-for-byte. |

The authorization's `ward_pass.status` is constant `PASS`.
`ward_decision_id` and `ward_decision_sigil` equal the resolved Execution
Specification authorization, Outcome approval binding, and
`approval` branch. `resolved_permission_set_sigil` is recomputed from the
exact closed RFC-0011 permission-set preimage, not copied without
verification. `evaluated_chronicle_head` equals
`expected_chronicle_head`, and `evaluated_at` equals `requested_at`.
For a new acceptance, that Head is the current verified Head and Ward
re-evaluates the bound Registry, Capability, Task, Snapshot, Circle,
Specification, approval, and policy at the trusted time. Historical replay
later replays that bound Head and time; it does not substitute a later
Registry, policy, Snapshot state, or wall clock.

`approval` is `NOT_REQUIRED` if and only if the Task approval binding,
Specification authorization, and Outcome approval binding all select
`NOT_REQUIRED`; no approval subject, Event, or Receipt is inferred.
`REQUIRED` copies the Task's exact approval-policy tuple, the Specification
and Outcome Receipt pair, and resolves this exact acyclic chain:

```text
execution-approval-subject/1.0
  -> execution-approval-transition-request/1.0
  -> chronicle-event/1.1 type execution.approval.granted
  -> receipt/1.1
  -> final execution-specification/1.0
```

The approval Event object ID equals `approval_subject_id`. Its exact RFC-0011
payload has `transition_request_id`, `transition_request_sigil`,
`purpose: EXECUTION_APPROVAL`, `approval_subject_id`,
`approval_subject_sigil`, `actor`, and `occurred_at`; it does not embed or
invent a subject inside the Receipt. The payload request pair resolves the
complete `execution-approval-transition-request/1.0`, whose event type,
purpose, complete approval subject, expected Head, Actor, Host invocation,
Chronicle Actor, key Sigil, requested time, and self-Sigil validate. The
outer approval Event actor equals that request's `chronicle_actor`
byte-for-byte. The payload subject pair
equals both that request's complete subject and this authorization branch;
the payload Actor equals the request Actor, and payload and outer Event
`occurred_at` equal the request `requested_at`.
Validation rederives the RFC-0011 content-addressed `EA-ID` from every
semantic subject member and the `EAT-ID` from
`(approval_subject.task_id, idempotency_key_sigil)`, and enforces both
single-assignment resolvers. A caller-chosen alternate subject ID or changed
subject under the same Task/key scope is invalid.

```text
approval_event.type
  == approval_request.event_type
  == "execution.approval.granted"
approval_event.object_id
  == approval_request.approval_subject.approval_subject_id
approval_event.sequence
  == approval_request.expected_chronicle_head.event_count + 1
approval_event.previous_receipt_sigil
  == approval_request.expected_chronicle_head.terminal_receipt_sigil

approval_event.payload.transition_request_id
  == approval_request.transition_request_id
approval_event.payload.transition_request_sigil
  == approval_request.transition_request_sigil
approval_event.payload.purpose
  == approval_request.purpose
  == "EXECUTION_APPROVAL"
approval_event.payload.approval_subject_id
  == approval_request.approval_subject.approval_subject_id
approval_event.payload.approval_subject_sigil
  == approval_request.approval_subject.approval_subject_sigil
approval_event.payload.actor
  == approval_request.actor
approval_event.actor
  == approval_request.chronicle_actor
approval_event.payload.occurred_at
  == approval_request.requested_at
  == approval_event.occurred_at
```

The Event ID and computed body Sigil equal `approval_event_id` and
`approval_event_body_sigil`; its paired Receipt ID and computed Sigil equal
`approval_receipt_id` and `approval_receipt_sigil`. The Receipt's `event_id`,
`event_body_sigil`, `previous_receipt_sigil`, and `accepted_at` equal the
Event according to RFC-0001. The subject's Ward, Registry, Task, Capability,
Snapshot, Circle, approval-policy, assurance, resolved-permission, and
preapproval-Specification bindings validate exactly under RFC-0011. After the
Receipt, the final Specification inserts only that Receipt pair and passes
RFC-0011's three-field omission recomputation.
A Phase 2 `approval.granted` Event, a Receipt without its Event, an
unresolved or mismatched approval transition request, an
Attempt-authorization Receipt, a different subject, or any Receipt field
treated as an invented `purpose`, subject, or transition request is invalid.

`authorization_sigil` is the Sigil of canonical JSON for the complete
`agent-result-acceptance-authorization/1.0` document with only
`authorization_sigil` omitted. The transition request embeds that complete
document, repeats the same Sigil at top level, and covers both through
`transition_request_sigil`. Its Actor and Host authentication-context Sigils
are equal, both self-Sigils validate, and those bindings plus
`chronicle_actor` equal the same authenticated MCP invocation. The exact
kind mapping, Host class, and authentication mechanism validate as printed
above. On a first admission the policy resolver validates all
sixteen predicates in printed order; false or indeterminate is rejection.
On precommit recovery the immutable authorization is reused only if the same
Head, Actor/Host/Chronicle-Actor authority, policy, storage prefix, Reference
Set closure, and Blob predicates still validate. Recovery never regenerates
it with a new time, caller, policy, or prefix.

Any related RFC-0013 Reference Intent must satisfy all of these equalities:

```text
intent.transition_request_id == request.transition_request_id
intent.transition_request_sigil == request.transition_request_sigil
intent.canonical_event_type == request.event_type
intent.canonical_event_type ==
  request.acceptance_authorization.acceptance_policy.canonical_event_type
intent.expected_chronicle_head == request.expected_chronicle_head
intent.reference_sets == request.reference_sets
intent.blob_sigils == request.managed_blob_sigils
intent.actor_id == request.actor.actor_id
intent.actor_id == request.chronicle_actor.actor_id
intent.authorization_sigil == request.authorization_sigil
intent.authorization_sigil ==
  request.acceptance_authorization.authorization_sigil
intent.idempotency_key_sigil == request.idempotency_key_sigil
intent.requested_at == request.requested_at
```

Intent validation resolves the immutable transition request by its exact ID
and Sigil, validates the embedded policy and approval chain, and recomputes
the authorization Sigil. A bare, syntactically valid Sigil is not authority.
The same resolver is available to Chronicle replay; a missing, ambiguous, or
unverifiable transition request fails closed.

The hash dependency is strictly:

```text
bound authority/evidence + embedded policy + actor/Host/Chronicle actor
  + frozen Storage prefix
  -> acceptance authorization
  -> transition request
  -> RFC-0013 Reference Intent
  -> Chronicle Event body
  -> receipt/1.1
```

The transition request ID is also the pre-intent idempotency identity for the
exact `(Task-ID, idempotency_key_sigil)` namespace. The coordinator derives
that ID before any control-record write and performs one atomic
create-if-absent at that identity. Actor, Host Invocation, Chronicle Actor,
authorization, and trusted `requested_at` are fixed on its first durable
creation. A retry first
looks up that same ID: a complete record with the same
`acceptance_request_sigil` is reused byte-for-byte rather than rebuilt with a
new invocation time; any different request is `IDEMPOTENCY_CONFLICT`. Because
the ID does not depend on the acceptance-request Sigil, changing request
content while reusing a Task's key cannot select a second record. Reuse also
reauthorizes the current caller against the stored Actor, Host invocation,
Chronicle Actor, and policy; the non-secret key alone grants no read or commit
authority and never rewrites the stored provenance. A torn record is never
addressable as complete and is
recovered at that same ID by the immutable-control-record protocol before
another write. A
complete request with no intent is inert and creates no root; while holding
the outer gate, recovery may append its exact intent only if the expected
Chronicle Head, authorization, storage prefix, Reference Set, and every Blob
predicate still verify. Otherwise it preserves the inert request, returns the
applicable closed precommit error, and never calls Athanor.

The acceptance-storage binding is also executable, not a timestamp claim.
Its `storage_state_sigil` is the Sigil of RFC-0013 State replayed exactly
through `storage_event`; `validated_blob_sigils` equals
`managed_blob_sigils` byte-for-byte. `validation_evidence` is embedded in the
binding, is sorted and unique by `blob_sigil`, has exactly one member per
validated Blob, and its Blob-Sigil projection equals
`validated_blob_sigils` byte-for-byte. For each Blob, replay enumerates every
eligible `AVAILABLE` Replica at that exact State, discards a quarantined,
expired, stale, corrupt, mismatched-size, or unverifiable generation, sorts
the remainder by `replica_id` using unsigned ASCII byte order, and selects
the first. Thus backend inventory order and process-local choice cannot change
the binding. The member's size, backend, generation, availability EventRef,
and integrity evidence resolve byte-for-byte to that selected Replica and
prove the exact Blob generation: `availability_event.event_sigil` equals the
selected Replica projection's `last_event_sigil`, and
`integrity_evidence_sigil` equals its current non-expired
`verification.evidence_sigil`. `quarantine_status` is constant `CLEAR`.
`validation_evidence_set_sigil` is the Sigil of canonical JSON for the
complete embedded array. Both `validated_blob_sigils` and
`validation_evidence` have `1..4096` members and their Blob projections are
identical. An eligible selected Attempt always contributes the three closed
Log-stream content observations; even three empty streams reach the
content-addressed empty-byte Blob, so this acceptance family has no empty
managed-Blob branch.

The acceptance coordinator acquires RFC-0013's outermost
canonical-reference gate before validation and retains it through both the
Chronicle commit and durable storage-pin outcome. Athanor and the storage
coordinator then independently perform their assigned checks:

1. replays Chronicle, fixes `expected_chronicle_head`, requires its
   `event_count < U63_MAX` so the possible one-Event result remains
   representable, and rejects any conflicting accepted result for the Task;
2. validates `task-capsule/2.0`, `capability-contract/2.0`, Registry, Snapshot,
   Circle, and exact Sigils; validates the `NOT_REQUIRED` branch or resolves
   the exact v2 Execution-approval subject, transition request,
   `execution.approval.granted` Event, and paired Receipt chain without
   treating Receipt fields as an implicit subject or request;
3. validates the complete embedded acceptance policy and authenticated
   Actor/Host/Chronicle-Actor triple, including exact Actor ID, kind mapping,
   Host class, and authentication mechanism, then verifies current Ward
   `PASS`, the recomputed permission-set Sigil, and Snapshot freshness at the
   authorization's bound Head and trusted time;
4. asks `ExecutionService` to rederive the exact Outcome from the verified
   execution journal and compares its Sigil;
5. requires terminal Job `SUCCEEDED` and `acceptance_eligible: true`;
6. validates the terminal Job and Attempt events and every exact RFC-0012
   binding copied into the Outcome: selected Worker Result or permitted
   `NO_RESULT` anchor, completion-anchor sequence, first stop/fence effective
   sequence, immutable per-Attempt authorization requirement and exact
   `NONE` or purpose-bound `BOUND` state, immutable Worker Session, Lease
   terminal binding, public fence tuple, final-fence branch and tombstone,
   process termination, cleanup, terminal-source branch, and quarantine
   status;
7. validates the selected Attempt budget settlement, final aggregate Job
   ledger, and absence of `EXCEEDED` or unaccounted dimensions; an exactly
   `EXHAUSTED` declared limit is settled and valid but admits no further work;
8. validates the exact requested assurance tuple, separate Attempt and Job
   assurance-evaluation events, realized claim, profile,
   conformance suite, backend, configuration, the exact frozen
   control-evidence-set ID-and-Sigil pair, all ten referenced evidence
   records, and the exact frozen quarantine-binding-set pair and every subject
   mapping;
9. resolves the exact observation-set pair, frozen
   `terminalization_storage_manifest_binding`, and
   `output_root_protection` carried by `ACCOUNTING_CAPTURED`; requires all
   copies in the terminal Attempt Event, observation set, and Outcome to be
   byte-for-byte equal; requires `output_storage_roots` to be empty for
   `NO_HOLD` or the exact one held root for `HELD`; and
   validates the manifest's selected-Attempt owner, complete entries,
   `blob_refs`, protection plan, Reference Set, hold, extractor, validator,
   and edge closure. The current hold may be the exact original `ACTIVE`
   projection or its one valid `RELEASED` successor under the RFC-0012
   output-deadline EHR; a released execution hold is not fabricated as active
   and does not by itself make otherwise still-available bytes ineligible. It
   validates that the Outcome's output, three-Log,
   resource-evidence, and terminal-source groups concatenate to the
   observation set's complete ordered member array byte-for-byte, then
   validates every expected output Schema, Blob identity, byte bound, frozen
   terminal storage union, non-quarantine state, and exact current RFC-0013
   Transfer and Transfer-Attempt provenance for each `ATTEMPT_OUTPUT`.
   An output `QUARANTINED` branch adds the `OUTPUT_QUARANTINED`
   ineligibility reason; an output `QUARANTINE_TERMINAL_NEGATIVE` branch adds
   `OUTPUT_UNAVAILABLE`; and either branch on a Log or resource-evidence
   member adds `STORAGE_OBSERVATION_INVALID`.
   Historical
   `created_by_transfer_attempt_id` alone, a shared Blob, or the selected
   Replica is not output-origin proof. Every actual `ATTEMPT_OUTPUT`, all
   three `LOG_STREAM` observations, every Blob-bearing resource-evidence
   entry, and a non-null terminal source map to exactly one matching typed
   storage-root-manifest entry; the output, resource, and terminal-source
   negative sentinels map to no entry; and the manifest contains no extra
   subject;
10. when `CODE_MODIFICATION` was declared, requires the exact `VERIFIED`
   terminal-source branch and validates its immutable Base, retained source,
   retention-policy, bounds, storage status, and verifier-evidence bindings;
   `terminal_source_identity`, `terminal_source_sigil`, and `storage_blob`
   are all non-null, resolve one exact `benchwork-source-tree/1.0`, and
   respectively equal its `source_tree_id`, `source_tree_sigil`, and
   `bundle_blob`;
11. confirms that no late, conflicting, stale, fenced, or rejected message can
   replace the selected evidence;
12. deterministically derives and Schema-validates `agent-result/2.0` using
    only the printed field mapping from exact `ATTEMPT_OUTPUT` members and the
    exact empty mapping for `ATTEMPT_OUTPUTS_NONE`;
13. while retaining the outer gate, acquires the Storage Journal lock, replays
   its current State, and performs the final current-availability, integrity,
   non-quarantine, exact-generation, and transfer-evidence validation for
   every managed Blob. Through the trusted versioned extractor it registers
   one immutable `artifact-storage-reference-set/1.0` whose source is exactly
   `{kind: OPERATIONAL_CONTROL_RECORD, identity: outcome_id, schema_version:
   execution-job-outcome/1.0, sigil: outcome_sigil}` and whose
   `CONTROL_RETAINS_BLOB` edges are the complete sorted output, log,
   resource-evidence, terminal-source bundle and manifest-reached, and other
   managed Blob set. Its installed extractor rejects any Blob that is absent
   from the complete Outcome/source-tree closure and any missing member. The
   edge projection equals `managed_blob_sigils` byte-for-byte and contains
   every Blob protected by the selected Attempt's frozen output ESM; the
   acceptance Reference Set is an additional canonicalization root, not a
   mutation or substitute for that ESM or its historical Reference Set. This
   does not
   describe the operational Outcome as canonical; the later reference intent
   and Chronicle Receipt establish the canonical pin. The edge set is
   non-empty;
14. still under that same Storage lock, replays the post-registration State,
   performs the same final Blob predicates once more, fixes
   `acceptance_storage_binding` to that exact last Storage event and State
   Sigil, constructs and validates the complete embedded policy,
   approval-resolved `acceptance_authorization`, and immutable transition
   request above at its content-derived ID, and appends one
   `artifact-storage-reference-intent/1.0` through
   `canonical_reference.intent_recorded`. The intent event is the immediate
   next Storage event: its `previous_event_sigil` equals
   `acceptance_storage_binding.storage_event.event_sigil`; its intent record
   has `canonical_event_type == transition_request.event_type ==
   agent-result.accepted` and equals the transition request ID and Sigil,
   expected Chronicle Head,
   Reference Set, exact Blob set, actor ID, authorization Sigil,
   idempotency-key Sigil, and requested time byte-for-byte. It then releases
   the Storage lock but retains the outer gate; and
15. asks Athanor to append the exact candidate conditional on that Head,
    records the returned Event and Receipt through
    `canonical_reference.committed`, verifies that permanent v1 pin, and
    releases the gate. This step never releases or changes an execution hold.

Only after steps 1 through 14 may Athanor append the new-version
`agent-result.accepted` Chronicle event. Step 15 durably marks the paired
storage pin committed. An `ACTIVE` execution hold remains additive until its
independent RFC-0012 `OUTPUT_DEADLINE` schedule; a hold already validly
released before acceptance remains historical evidence and is not released
again. Acceptance supplies no EHR basis and cannot shorten that lifecycle.
Failure or a crash recovers the canonical intent/Event/Receipt chain without
changing the hold. The service may return its `receipt/1.1` after the permanent
v1 pin is committed.
Failure to register or validate the Reference Set or intent is
`RESULT_INELIGIBLE`; it never creates a Chronicle Event. A crash after the
Chronicle append is recovered by the exact RFC-0013 intent and Receipt lookup,
not by creating a second Event or releasing the pin.

A valid Phase 3 Head at `U63_MAX` returns
`CHRONICLE_UNAVAILABLE/HEAD_COUNT_EXHAUSTED`; a greater count admitted only by
an older unbounded contract is not a Phase 3 `ChronicleHeadRef` and returns
`CHRONICLE_UNAVAILABLE/HEAD_INVALID`. Both fail before Reference Set
registration, transition-request persistence, Reference Intent, Reservation,
or Chronicle submission. Existing Outcome and storage
evidence remain intact; the coordinator never wraps or clamps the count.

The acceptance-storage linearization point is the verified prefix immediately
before `canonical_reference.intent_recorded`, not an unrecorded read before
the Storage lock. A missing Replica, integrity incident, or Quarantine event
committed before that point fails acceptance. A newly observed incident after
that point is later evidence and cannot retroactively change the accepted
proposal, just as corruption observed after any Receipt does not rewrite that
Receipt. GC and authorized deletion cannot cross the interval because they
must acquire the retained outer gate. The intent-bound transition request and
`AcceptanceStorageBinding`, rather than timing assumptions, prove which
storage state was accepted.

Acceptance does not automatically:

- register a logical Artifact;
- create or update a scientific Run;
- apply or promote a Patch;
- transition an Experiment;
- create an Assessment; or
- Seal a Research Question, Protocol, or Decision.

Those actions remain separate typed Athanor transitions. Every stale, fenced,
under-assured, malformed, quarantined, corrupt, incomplete, or otherwise
ineligible Outcome remains preserved and receives no fabricated Receipt.

## Agent Result v2 and replay

### `agent-result/2.0`

The deterministic Proposal has exactly these top-level fields:

```text
schema_version
task_id
program_id
task_capsule_sigil
host_identity_sigil
capability_binding
snapshot_binding
job_binding
execution_specification_binding
job_outcome_binding
terminal_event_sigil
selected_attempt_id
assurance_claim_sigil
terminal_source_binding
status
outputs
provenance
result_sigil
```

`schema_version` is constant `agent-result/2.0`; `status` is constant
`COMPLETED`. The nested objects are closed and exact:

- `capability_binding` has `capability_id`, `contract_version`, and
  `capability_contract_sigil`;
- `snapshot_binding` has `snapshot_id` and `snapshot_sigil`;
- `job_binding` has `job_id` and `job_binding_sigil`;
- `execution_specification_binding` has `specification_id` and
  `specification_sigil`;
- `job_outcome_binding` has `outcome_id` and `outcome_sigil`;
- `terminal_source_binding` is byte-for-byte equal to the Outcome branch and
  is either `NOT_APPLICABLE {kind}` or the exact RFC-0012
  `VERIFIED` branch; `QUARANTINED` cannot occur in an accepted Agent Result;
- every `outputs` member has exactly `task_output_id`, `declared_schema_id`,
  `declared_schema_sigil`, `blob_sigil`, `size_bytes`,
  `source_observation_member_sigil`, and
  `storage_integrity_evidence_sigil`, and members are unique and sorted by
  `(task_output_id, blob_sigil)`; and
- `provenance` has exactly `executor_instance_id`, `executor_epoch`,
  `executor_build_sigil`, `worker_id`, `worker_binding_sigil`,
  `worker_session_id`, `worker_session_binding_sigil`, `backend_identity`,
  `backend_configuration_sigil`, `requested_assurance_level`,
  `assurance_profile_sigil`, `conformance_suite_sigil`,
  `attempt_authorization_state`,
  `budget_settlement_event_sigil`, `job_budget_ledger_sigil`,
  `storage_observation_binding`, `control_evidence_set_binding`,
  `quarantine_binding_set_binding`,
  `terminalization_storage_manifest_binding`, and
  `output_root_protection`.

Task and Program IDs use their canonical domains; Job, Attempt, Worker,
Worker Session, Executor, and Execution Specification IDs use RFC-0012
domains; every named Sigil is `Sigil`; executor epoch is `U64`; and requested
assurance level is `SANCTUM-A0|SANCTUM-A1|SANCTUM-A2`. Output IDs and Schema
IDs are `Opaque`, output size is RFC-0013 `U63`, and every output Sigil is
`Sigil`.
`storage_observation_binding` is the exact RFC-0012 `$def`, not an
abbreviated local object.
`terminalization_storage_manifest_binding` and `output_root_protection` are
the exact RFC-0012 terminal branches, including the complete held
`ATTEMPT_OUTPUT` root when present; an RFC-0015 no-Attempt wrapper can never
enter an accepted Agent Result.
`attempt_authorization_state` is byte-for-byte the selected Attempt's exact
RFC-0012 terminal state and is therefore `NONE` for no requirement or
`BOUND` with its complete subject and binding for a required eligible
Attempt; `PENDING` cannot enter an Agent Result.
`terminal_event_sigil` is the Outcome's Job-terminal Event Sigil;
`selected_attempt_id` is the Outcome's selected `AT-ID`; and
`assurance_claim_sigil` is the selected terminal RFC-0012 claim. All three
equal their Outcome bindings byte-for-byte.

The Proposal is created only for an acceptance-eligible successful Outcome, so
`selected_attempt_id`, `assurance_claim_sigil`, every Worker and Session
binding, and every required output-integrity binding are non-null. Optional
Task outputs are represented by their deterministic presence or absence in
the sorted array, not by null members. Such an Outcome necessarily has a
`LEASED` authority branch. The complete non-output mapping is:

| `agent-result/2.0` field | Exact Outcome source |
| --- | --- |
| `task_id` | `task_binding.task_id` |
| `program_id` | `program_id` |
| `task_capsule_sigil` | `task_binding.task_capsule_sigil` |
| `host_identity_sigil` | `assurance_context_binding.host_identity_sigil` |
| `capability_binding` | Complete `capability_binding` byte-for-byte |
| `snapshot_binding` | Complete `snapshot_binding` byte-for-byte |
| `job_binding` | `{job_id: outcome.job_id, job_binding_sigil: outcome.job_binding_sigil}` |
| `execution_specification_binding` | Complete `execution_specification_binding` byte-for-byte |
| `job_outcome_binding` | `{outcome_id: outcome.outcome_id, outcome_sigil: outcome.outcome_sigil}` |
| `terminal_event_sigil` | `job_terminal.event_sigil` |
| `selected_attempt_id` | `selected_attempt_binding.attempt_id` |
| `assurance_claim_sigil` | `attempt_assurance_binding.assurance_claim_sigil` |
| `terminal_source_binding` | Complete `terminal_source_binding` byte-for-byte |
| `status` | Constant `COMPLETED` |

The `provenance` mapping is independently exhaustive:

| Provenance field | Exact Outcome source |
| --- | --- |
| `executor_instance_id` | `authority_binding.executor_instance_id` |
| `executor_epoch` | `authority_binding.executor_epoch` |
| `executor_build_sigil` | `authority_binding.executor_build_sigil` |
| `worker_id`, `worker_binding_sigil`, `worker_session_id`, `worker_session_binding_sigil` | Same-named fields of `selected_attempt_binding.worker_session_binding` |
| `backend_identity` | `assurance_context_binding.backend_identity` |
| `backend_configuration_sigil` | `assurance_context_binding.backend_configuration_sigil` |
| `requested_assurance_level` | `assurance_context_binding.requested_level` |
| `assurance_profile_sigil` | `assurance_context_binding.profile_sigil` |
| `conformance_suite_sigil` | `assurance_context_binding.conformance_suite_sigil` |
| `attempt_authorization_state` | Complete `selected_attempt_binding.attempt_authorization_state` byte-for-byte |
| `budget_settlement_event_sigil` | `budget_binding.selected_attempt_settlement.event_sigil` |
| `job_budget_ledger_sigil` | `budget_binding.job_budget_ledger.budget_ledger_sigil` |
| `storage_observation_binding` | Complete top-level `storage_observation_binding` byte-for-byte |
| `control_evidence_set_binding` | Complete top-level `control_evidence_set_binding` byte-for-byte |
| `quarantine_binding_set_binding` | Complete top-level `quarantine_binding_set_binding` byte-for-byte |
| `terminalization_storage_manifest_binding` | Complete top-level `terminalization_storage_manifest_binding` byte-for-byte |
| `output_root_protection` | Complete top-level `output_root_protection` byte-for-byte |

The `agent-result/2.0` Schema publishes this exact object at
`#/$defs/provenance`; consumers import that canonical URI rather than cloning
or abbreviating it. A field absent from these two tables has no inference
rule.

The exact
`ATTEMPT_OUTPUTS_NONE` observation sentinel maps to an empty Agent Result
array. Every `ATTEMPT_OUTPUT` maps only as follows:
`logical_name -> task_output_id`, `schema_id -> declared_schema_id`,
`schema_sigil -> declared_schema_sigil`, `blob_sigil -> blob_sigil`, and
`byte_size -> size_bytes`; no other renamed or inferred value is permitted.
`source_observation_member_sigil` is the independently recomputed Sigil of the
complete exact observation member. Eligibility requires that member's
`storage` to be `BLOB` with terminal status `AVAILABLE` and
`replica: SELECTED`; `storage_integrity_evidence_sigil` is exactly that
selected Replica's `verification.evidence_sigil`. A missing, `NONE`,
degraded, unavailable, incident, quarantined, or unselected storage branch
cannot enter an Agent Result. `storage_observation_binding` reuses the exact
RFC-0012 union; both terminalization-set provenance bindings reuse the
Outcome's exact frozen ID-and-Sigil pairs; and the storage-manifest and
output-protection provenance fields reuse the Outcome's exact frozen
manifest pair and held-root branch.

Each `ATTEMPT_OUTPUT` creates exactly one output member. The complete mapped
array is sorted strictly by `(task_output_id unsigned UTF-8 bytes,
blob_sigil ASCII)` and unique by that tuple. The selected Replica evidence is
the member's frozen terminal observation, even when acceptance-time validation
selects a different current Replica for `AcceptanceStorageBinding`.

The result Sigil is canonical JSON over every field except `result_sigil`.
There is no mutable URI, Crucible path, backend URI, raw command, or credential.
An output's logical Artifact registration, if desired, is a later RFC-0013
transition.

### Chronicle event

The v2 `agent-result.accepted` payload has exactly:

```text
agent_result
program_id
host_identity_sigil
capability_contract_sigil
snapshot_sigil
task_capsule_sigil
job_outcome_sigil
result_sigil
acceptance_request_sigil
idempotency_key_sigil
transition_request_id
transition_request_sigil
acceptance_storage_binding
actor
host_invocation
authorization_sigil
reference_intent_id
reference_intent_record_sigil
reference_set_id
reference_set_sigil
occurred_at
```

`agent_result` is the complete `agent-result/2.0`. Every repeated identity or
Sigil is byte-for-byte equal to the corresponding nested result or
transition request and canonical-reference-intent binding.
`transition_request_id` is `ATR-ID`;
`acceptance_storage_binding`, `actor`, and `host_invocation` are the exact
closed candidate values; every named Sigil is `Sigil`; and `occurred_at` is
the Athanor trusted `Timestamp`. The outer Event's complete `actor` is the
request's exact `chronicle_actor`, while its Actor ID, authorization,
idempotency key, transition request, Reference Set, and storage intent values
equal the RFC-0013 intent byte-for-byte. No payload field is optional or
nullable. The outer Chronicle Event type, transition request `event_type`, and
Reference Intent `canonical_event_type` are all exactly
`agent-result.accepted`; any cross-family value is rejected before Chronicle.

Replay enforces these exact equalities before it projects any accepted result:

```text
event.type
  == request.event_type
  == intent.canonical_event_type
  == "agent-result.accepted"

payload.transition_request_id
  == request.transition_request_id
  == intent.transition_request_id
payload.transition_request_sigil
  == request.transition_request_sigil
  == intent.transition_request_sigil

payload.authorization_sigil
  == request.authorization_sigil
  == request.acceptance_authorization.authorization_sigil
  == intent.authorization_sigil
payload.actor
  == request.actor
  == request.acceptance_authorization.actor
payload.host_invocation
  == request.host_invocation
  == request.acceptance_authorization.host_invocation
event.actor
  == request.chronicle_actor
  == request.acceptance_authorization.chronicle_actor
event.actor.actor_id
  == payload.actor.actor_id
  == intent.actor_id

payload.acceptance_request_sigil
  == request.acceptance_request_sigil
  == request.acceptance_authorization.acceptance_request_sigil
payload.idempotency_key_sigil
  == request.idempotency_key_sigil
  == request.acceptance_authorization.idempotency_key_sigil
payload.acceptance_storage_binding
  == request.acceptance_storage_binding
  == request.acceptance_authorization.acceptance_storage_binding

payload.reference_set_id
  == request.reference_sets[0].reference_set_id
  == intent.reference_sets[0].reference_set_id
payload.reference_set_sigil
  == request.reference_sets[0].reference_set_sigil
  == intent.reference_sets[0].reference_set_sigil

payload.reference_intent_id
  == intent.reference_intent_id
payload.reference_intent_record_sigil
  == intent.record_sigil

payload.agent_result
  == request.agent_result
payload.program_id
  == request.agent_result.program_id
payload.host_identity_sigil
  == request.agent_result.host_identity_sigil
payload.capability_contract_sigil
  == request.agent_result.capability_binding.capability_contract_sigil
payload.snapshot_sigil
  == request.agent_result.snapshot_binding.snapshot_sigil
payload.task_capsule_sigil
  == request.agent_result.task_capsule_sigil
payload.job_outcome_sigil
  == request.job_outcome_binding.outcome_sigil
  == request.agent_result.job_outcome_binding.outcome_sigil
payload.result_sigil
  == request.agent_result.result_sigil

event.object_id
  == request.agent_result.task_id
event.sequence
  == request.expected_chronicle_head.event_count + 1
event.previous_receipt_sigil
  == request.expected_chronicle_head.terminal_receipt_sigil
event.occurred_at
  == payload.occurred_at
  == event.receipt.accepted_at
event.receipt.event_id
  == event.event_id
event.receipt.event_body_sigil
  == event.event_body_sigil
event.receipt.previous_receipt_sigil
  == event.previous_receipt_sigil
```

Replay resolves the immutable request and complete authorization preimage,
recomputes the embedded policy self-Sigil, validates the historical Ward
decision at the bound Head and trusted time, and, for `REQUIRED`, resolves
the exact approval subject, approval transition request,
`execution.approval.granted` Event body, and paired Receipt chain. It
evaluates only the policy version and authorization
inputs bound before the intent; it cannot substitute a later Head, Ward
decision, policy, approval, Actor, Host invocation, Chronicle Actor, or time.
A missing request or intent, a bare authorization Sigil without its preimage,
an unresolved
approval Event or Receipt, or any inequality above invalidates replay.

The complete transition request is durable as an immutable control record at
`transition_request_id` before the Storage intent event is appended. The
request-to-event mapping is exact: `agent_result`, Job Outcome binding,
acceptance-request and key Sigils, acceptance-storage binding, Actor, Host
Invocation, the complete Chronicle Actor, the authorization Sigil whose
complete preimage remains resolvable through the request, transition request
identity, and Reference Set are copied byte-for-byte—the first two into the
payload and the Chronicle Actor into the outer Event. The intent supplies its
later intent identity and record Sigil, and Athanor supplies only
`occurred_at`. The event omits
`expected_chronicle_head` and the explicit managed-Blob array because the
bound intent preserves both without widening them.

The paired `receipt/1.1` is generated after the Event body Sigil and remains
outside the payload exactly as RFC-0001 requires. The full persisted Chronicle
Event carries that paired Receipt in its standard outer `receipt` field.
Neither the payload nor `agent-result/2.0` embeds the Receipt that proves its
own acceptance.

The event object ID is exactly the Task ID. The event is valid only if no
`agent-result.accepted` event of any supported Agent Result version already
exists for that Task. Receipt binding, event Sigil computation, lock ordering,
and durability retain RFC-0001 meanings, with RFC-0013's
canonical-reference gate outside both journal locks. Neither the Reference Set
nor the transition request or intent embeds the later Event Sigil or Receipt,
so the protocol has no hash cycle.

An exact retry whose key and request Sigils match first recovers and verifies
the immutable transition request, bound RFC-0013 reference intent, frozen
acceptance-storage prefix, Reference Set, and committed pin, then returns the
original Receipt. If the Task is already bound to the exact Outcome but the
caller uses a new unused key, the service performs the same checks, returns
the original Receipt with an `already_accepted` warning, and does not create
or bind a second key. An absent or ambiguous request, prefix, or pin is
recovered or fails closed; the service never treats the Receipt alone as
permission to release the gate. Reusing a bound key for any different request
returns `IDEMPOTENCY_CONFLICT`. A different Outcome for the same Task returns
`RESULT_ALREADY_ACCEPTED`.

### `agent-result-record/2.0`

Replay validates the v2 event and projects exactly:

```text
schema_version
task_id
program_id
task_capsule_sigil
host_identity_sigil
capability_binding
snapshot_binding
job_binding
execution_specification_binding
job_outcome_binding
terminal_event_sigil
selected_attempt_id
assurance_claim_sigil
canonical_reference_binding
terminal_source_binding
outputs
provenance
status
agent_result_sigil
accepted_at
acceptance_receipt
```

`schema_version` is constant `agent-result-record/2.0`; `status` is constant
`COMPLETED`. Apart from `schema_version`,
`canonical_reference_binding`, `agent_result_sigil`, `accepted_at`, and
`acceptance_receipt`, every record field from `task_id` through `status` is a
same-named byte-for-byte copy of the accepted Agent Result. This exhaustive
rule includes `task_id`, `program_id`, `task_capsule_sigil`,
`host_identity_sigil`, all five immutable binding objects,
`terminal_event_sigil`, `selected_attempt_id`, `assurance_claim_sigil`,
`terminal_source_binding`, `outputs`, `provenance`, and `status`;
there is no second projection or inference rule.
`canonical_reference_binding` has
exactly `reference_intent_id`, `reference_intent_record_sigil`,
`transition_request_id`, `transition_request_sigil`,
`acceptance_storage_binding`, `reference_set_id`, and
`reference_set_sigil`, copied from the event and verified request/intent.
`agent_result_sigil` equals the accepted result's `result_sigil`.
`accepted_at` is exactly the Chronicle event `occurred_at`, and
`acceptance_receipt` is exactly the event Receipt ID. `accepted_at` is
`Timestamp`; every named Sigil is `Sigil`; IDs use the same domains as the
accepted Agent Result, RFC-0013 reference intent/set, and Receipt contracts.
No field is nullable.

Replay supports `agent-result/1.0`, `agent-result/1.1`, and
`agent-result/2.0` through separate Schema and projection branches. It rejects
unknown versions, cross-version field inference, duplicate Task acceptance,
Outcome mismatch, non-deterministic output order, invalid Sigils, or Receipt
mismatch. The v1 and v1.1 projections remain byte-for-byte or semantically
unchanged as their contracts require.

## Patch handoff

For a code-modification Task, RFC-0014's exporter may derive a Patch Bundle
only under its own post-terminal contract. Such a Task and Execution
Specification must have declared bounded terminal-source retention before
launch; the resulting Job Outcome and Agent Result bind that immutable source
without containing a Patch. `patch.proposed` must bind the exact accepted
`agent-result/2.0` Receipt, Job Outcome Sigil, retained terminal-source
identity and Sigil, its exact non-null `storage_blob` equal to the resolved
source tree's `bundle_blob`, Patch Base, payload Blobs, and exporter evidence.
A Patch Proposal cannot be canonically accepted directly from a Worker Result
or an unaccepted Job Outcome.

Patch preparation, inspection, explicit authorization, and outcome recording
use the separate closed MCP tools and Schemas owned by RFC-0014. They are
listed in the same `mcp-tool-registry/2.0`; none is an implicit side effect of
the five execution tools. Their exact names are:

- `benchwork_prepare_patch_promotion`;
- `benchwork_inspect_patch_promotion`;
- `benchwork_authorize_patch_promotion`; and
- `benchwork_record_patch_promotion_outcome`.

## MCP Registry amendment

`mcp-tool-registry/2.0` preserves the original 38 Phase 2 entries in their
original order and meaning, then adds the five execution tools in the order
listed in this RFC, followed by RFC-0014's closed Patch tools in RFC-0014's
normative order. The complete v2 Registry therefore has exactly 47 entries;
another name requires a new Registry contract version.

The Registry document has `api_version: 0.4`, `stability: alpha`,
`input_schema_source: tools/list.inputSchema`, and
`response_schema: mcp-tool-result/1.0`. Its tool item is a closed union: the
unchanged Phase 2 branch has the exact v1 fields, while the new Phase 3 branch
also requires `request_schema` and `success_data_schema`.
The v1 branch has exactly `name`, `category`, `permission`, `risk`,
`approval`, and `canonical_effect`. The Phase 3 branch has exactly those six
plus `request_schema` and `success_data_schema`; both are literal contract
identifiers from this RFC or RFC-0014. The Registry top-level version fields
are the constants printed above, and `tools` is an ordered array of exactly
47 closed items with unique names.

The v2 Registry extends the closed enums as required for:

- `category: execution` and `category: patch`;
- `approval: execution_policy`, `approval: execution_control`, and
  `approval: patch_authorization`; and
- `canonical_effect: operational_event`.

Existing enum values such as `none`, `ward`, `human_confirmation`,
`task_event`, and `canonical_event` retain their v1 meanings. RFC-0014 fixes
the exact metadata of the four Patch entries.

For the five execution tools:

| Tool | Permission | Risk | Approval | Canonical effect | Success data |
| --- | --- | --- | --- | --- | --- |
| `benchwork_start_job` | `execute` | high | `execution_policy` | `operational_event` | `execution-observation/1.0` |
| `benchwork_observe_job` | `read` | low | `none` | `none` | `execution-observation/1.0` |
| `benchwork_cancel_job` | `execute` | high | `execution_control` | `operational_event` | `execution-observation/1.0` |
| `benchwork_get_job_result` | `read` | low | `none` | `none` | `execution-job-outcome/1.0` |
| `benchwork_accept_job_result` | `commit` | high | `ward` | `task_event` | `agent-result-record/2.0` |

All new tools remain `alpha`. The existing `mcp-tool-registry/1.0`,
`mcp-tool-result/1.0`, tool meanings, and 38-tool surface remain available
unchanged. A v1 client never receives a v2 tool merely because the server
supports it.

## Error contract

Execution operations use the existing MCP error envelope and add stable codes:

| Code | Meaning |
| --- | --- |
| `EXECUTION_NOT_FOUND` | The Job does not exist |
| `EXECUTION_NOT_READY` | The requested terminal Outcome or transition is not available |
| `EXECUTION_CONFLICT` | Current revision or state does not permit the operation |
| `IDEMPOTENCY_CONFLICT` | A key is already bound to different request content |
| `EXECUTION_POLICY_REJECTED` | Ward or resolved execution policy rejected the request |
| `ASSURANCE_UNAVAILABLE` | No installed eligible profile can meet requested assurance |
| `STALE_EXECUTION` | Snapshot, Capability, Task, approval, or base identity is stale |
| `STALE_CURSOR` | The requested observation prefix cannot be verified exactly |
| `LEASE_FENCED` | The Attempt no longer owns eligible authority |
| `RESULT_INELIGIBLE` | The terminal Job Outcome cannot be accepted by Athanor |
| `RESULT_ALREADY_ACCEPTED` | The Task already has a different accepted Agent Result |
| `CHRONICLE_UNAVAILABLE` | Chronicle cannot admit Start or the exact acceptance transition |

Error details are closed and bounded per operation. They contain stable IDs,
revisions, and reason enums, not stack traces, absolute paths, secrets, raw
policy tokens, Worker diagnostics, or backend-private handles.
The error envelope's `details` branch is exactly:

| Code | Exact detail fields |
| --- | --- |
| `EXECUTION_NOT_FOUND` | `job_id: JB-ID` |
| `EXECUTION_NOT_READY` | `job_id: JB-ID`, `job_state: RFC-0012 JobState`, `job_revision: U64` |
| `EXECUTION_CONFLICT` | `job_id: JB-ID`, `expected_job_revision: U64`, `current_job_revision: U64`, `through_event_sigil: Sigil` |
| `IDEMPOTENCY_CONFLICT` | `idempotency_key_sigil: Sigil`, `bound_request_sigil: Sigil`, `presented_request_sigil: Sigil` |
| `EXECUTION_POLICY_REJECTED` | `request_sigil: Sigil`, `ward_decision_sigil: Sigil\|null`, `reason_codes: ["WARD_FAILED"\|"CAPABILITY_DENIED"\|"TASK_DENIED"\|"APPROVAL_MISSING"\|"POLICY_MISMATCH"]` |
| `ASSURANCE_UNAVAILABLE` | `requested_level: "SANCTUM-A0"\|"SANCTUM-A1"\|"SANCTUM-A2"`, `profile_sigil: Sigil`, `reason_codes: ["PROFILE_NOT_INSTALLED"\|"BACKEND_INELIGIBLE"\|"HOST_INELIGIBLE"\|"CONTROL_UNAVAILABLE"\|"SUITE_MISMATCH"]` |
| `STALE_EXECUTION` | `subject_kind: "SNAPSHOT"\|"CAPABILITY"\|"TASK"\|"APPROVAL"\|"BASE"`, `subject_id: Opaque`, `expected_sigil: Sigil`, `observed_sigil: Sigil\|null` |
| `STALE_CURSOR` | `job_id: JB-ID`, `cursor_sigil: Sigil`, `reason: "WRONG_JOB"\|"NON_ANCESTOR"\|"SIGIL_MISMATCH"\|"PREFIX_UNAVAILABLE"\|"MALFORMED"` |
| `LEASE_FENCED` | `job_id: JB-ID`, `attempt_id: AT-ID`, `lease_id: LS-ID`, `fencing_generation: U64`, `final_fence_floor: U64`, `tombstone_event_sigil: Sigil` |
| `RESULT_INELIGIBLE` | `job_id: JB-ID`, `outcome_sigil: Sigil`, `ineligibility_reasons: [OutcomeIneligibilityReason]` |
| `RESULT_ALREADY_ACCEPTED` | `task_id: Task-ID`, `presented_outcome_sigil: Sigil`, `accepted_result_version: "agent-result/1.0"\|"agent-result/1.1"\|"agent-result/2.0"`, `accepted_result_sigil: Sigil`, `accepted_outcome_sigil: Sigil\|null`, `acceptance_receipt_id: Receipt-ID` |
| `CHRONICLE_UNAVAILABLE` | `job_id: JB-ID`, `operation: "START_JOB"\|"ACCEPT_JOB_OUTCOME"`, `observed_head_event_count: U63\|null`, `reason: "HEAD_COUNT_EXHAUSTED"\|"HEAD_UNAVAILABLE"\|"HEAD_INVALID"` |

`OutcomeIneligibilityReason` is the exact enum printed under Get Job Outcome.
Arrays are non-empty, unique, sorted, and bounded to 256. No error branch
admits a field from another branch. In `RESULT_ALREADY_ACCEPTED`,
`accepted_outcome_sigil` is non-null exactly for `agent-result/2.0`; it is
null for v1.0 or v1.1, which predate Job Outcomes. The accepted result Sigil
and Receipt remain mandatory in every branch.
For `CHRONICLE_UNAVAILABLE`, `observed_head_event_count` is `U63_MAX` exactly
for `HEAD_COUNT_EXHAUSTED` and null for `HEAD_UNAVAILABLE` or `HEAD_INVALID`;
untrusted or non-representable Head content is never coerced into the detail
object.
`benchwork_accept_job_result` returns `RESULT_INELIGIBLE` for every failed
Outcome-eligibility predicate and includes the complete ordered
`ineligibility_reasons`; it never promotes an individual reason such as
`OUTPUT_QUARANTINED`, `OUTPUT_UNAVAILABLE`, or
`STORAGE_OBSERVATION_INVALID` into a competing top-level error code.

## Idempotency and concurrency

- Start keys bind the complete `execution-start-request/1.0` Sigil and frozen
  admission Chronicle-Head evidence in both the immutable Job and
  `job.submitted`; retry reuses those bytes while separately rechecking
  current Head capacity.
- Cancel keys bind the complete `execution-cancel-request/1.0` Sigil in the
  cancellation event, including a state-neutral terminal no-op.
- Accept keys bind the complete `execution-accept-result-request/1.0` Sigil in
  both the immutable internal transition request and accepted Chronicle event;
  the per-Task key Sigil deterministically selects the transition request
  identity, and the event also binds that transition request's identity and
  Sigil.
- Read operations require no idempotency key.
- Execution mutations compare exact entity `revision` values under the
  execution-journal lock; this RFC does not invent a generic "state version."
- Observation pages bind exact `through_journal_sequence` and
  `through_event_sigil`; this RFC does not invent a second journal version.
- Due deadlines are committed before caller-requested mutations.
- A losing concurrent mutation returns `EXECUTION_CONFLICT` with the current
  Job revision and no fabricated success.
- Execution idempotency survives MCP, Executor, Worker, and Host restart
  because it replays from the execution journal.
- Canonical acceptance idempotency survives restart because it replays both
  Chronicle, the immutable transition request, and the exact RFC-0013
  canonical-reference intent and pin.
- Idempotency never overrides freshness, fencing, assurance, Blob integrity,
  Ward, or terminal ordering.

## Invariants

- MCP delegates typed Job control; it never runs or interprets Worker commands.
- Start cannot broaden the pinned Capability, Task, Circle, approval, or
  assurance profile.
- Start freezes an admissible Chronicle Head and its complete self-Sigiled
  evidence before any Job-input ESM or Storage side effect.
- Start acknowledges exactly one durable `job.submitted`; queueing is a later
  RFC-0012 transition.
- Every Start input is held in RFC-0013 before `job.submitted` exposes its
  execution root; a crash can leave only extra protection.
- Observe never infers state from a process table, queue, or Crucible path.
- Cancel is a request until termination evidence is durable.
- Public fence evidence is distinct from the secret Lease credential.
- A Worker Result is optional operational input, not a terminal Job Outcome.
- Every terminal Job has one deterministic Job Outcome.
- Job Outcome retrieval is not scientific acceptance.
- Athanor remains the only canonical transition authority.
- Agent Result acceptance freezes final storage validation and the complete
  internal transition request under the Storage lock, writes the exact
  storage reference intent before Chronicle, and returns no Receipt until the
  corresponding pin is durably committed.
- A canonical Agent Result pin is additive to the exact execution hold named
  by its `HELD` output-root-protection branch. Acceptance never releases or
  changes that hold; only its independent RFC-0012 EHR lifecycle may do so,
  and a crash preserves extra protection.
- Job success does not create a Run, Artifact, Assessment, Decision, Patch, or
  Seal.
- Patch derivation never mutates an immutable Job Outcome.
- Every failed, cancelled, timed-out, policy-violating, lost, fenced, stale,
  duplicate, rejected, and ineligible message or Outcome remains recorded.
- No request or response exposes an ambient command, absolute Host path,
  credential, secret, Lease credential, or unbounded collection.

## Compatibility and migration

The new tools are additive to the Phase 2 MCP surface. Existing tools, request
fields, response fields, error codes, Chronicle events, and published Schemas
keep their meanings.

`benchwork_open_task`, `benchwork_complete_task`, and
`benchwork_fail_task` remain Phase 2 Task v1 operations. They do not create,
control, or accept a Phase 3 Job. Clients migrate by explicitly creating Task
v2 and calling the new operations; conversation or native-tool history is not
converted into execution evidence.

The accepted `agent-result/1.1` path remains replayable. New execution outcomes
use `agent-result/2.0` and an explicit version-aware acceptance and replay
branch. There is no lossy automatic conversion between them.

The v2 MCP registry does not mutate the v1 Registry file or make v2 tools
visible to a v1-only client.

## Security and integrity

MCP has no direct handle to the Worker process, Crucible filesystem, Artifact
backend internals, Lease credentials, or target repository.
`ExecutionService` is the only adapter between MCP and the Executor journal.

All mutating requests are closed, size-bounded, Schema-validated, and
content-addressed before side effects. Execution Specifications, Worker
Results, Job Outcomes, and Agent Results remain untrusted until their complete
identity chains validate at the authority appropriate to each layer.

Start fails before Job creation when approval, policy, assurance profile,
input, or backend-profile eligibility is missing. After `job.submitted`, every
partial failure is recorded in the operational journal and recovered or
terminalized under RFC-0012.

Lease credentials and credential proofs are accepted only on the authenticated
Worker protocol, never through MCP. Observation may expose the public executor
epoch, fencing generation, fence floor, and tombstone necessary to explain
eligibility, but these values grant no authority.

## Alternatives

- **One `benchwork_execute` tool.** Rejected because an untyped command surface
  is the universal escape hatch prohibited by RFC-0009.
- **Put `command` and `argv` on Start.** Rejected because the caller could
  bypass the pinned Capability and Worker contract.
- **Bind Start to one Worker instance.** Rejected because preflight and retry
  must independently select and revalidate Worker eligibility.
- **Make Job creation and queueing one invented event.** Rejected because it
  conflicts with RFC-0012's replayable `SUBMITTED -> QUEUED` transition.
- **Use Worker Result for all terminal states.** Rejected because several
  terminal paths have no Worker message and Workers cannot issue assurance
  claims.
- **Put acceptance status or Patch ID into Job Outcome.** Rejected because
  later canonical and derived records must not mutate terminal operational
  evidence.
- **Block Start until completion.** Rejected because cancellation,
  observation, crash recovery, and bounded MCP latency require asynchronous
  execution.
- **Return live logs through MCP.** Rejected because streams are unbounded and
  not restart-stable; logs use stable pages or Blob references.
- **Automatically register Runs, Artifacts, or Patches.** Rejected because
  operational success cannot substitute for Athanor validation or separate
  authorization.
- **Reuse Task v1 tools.** Rejected because it would silently reinterpret the
  frozen Phase 2 contracts.

## Non-goals

- generic shell, filesystem, Git, web, or arbitrary executable access;
- automatic Provider or model invocation;
- remote MCP, remote Workers, cluster scheduling, or GPU orchestration;
- secret brokering;
- direct Blob download or upload through MCP;
- automatic Patch export, acceptance, or promotion;
- automatic scientific Run or Artifact registration; and
- changing RQ, Protocol, or Decision confirmation requirements.

## Acceptance tests

The API is acceptable only when tests demonstrate:

1. the original 38 MCP tools retain exact names, order, request meanings, and
   response envelopes;
2. every new v2 tool has a closed request Schema, a success-data Schema, and a
   matching `tools/list.inputSchema`; every nested alias, union branch,
   cursor, observation view, Actor, Host invocation, Chronicle Actor, Outcome,
   Agent Result, internal acceptance transition request, replay record, and
   Registry item rejects extra or mistyped fields;
3. no execution request accepts `command`, `shell`, `argv`, `cwd`, arbitrary
   environment values, credentials, raw bytes, or raw output paths;
4. Start rejects missing or forged approval for Capability-required,
   side-effect-required, and Task-upgraded `REQUIRED` branches, stale Snapshot,
   broadened policy, invalid Sigils, missing inputs, and unavailable assurance
   profile without creating a Job; the Task-upgrade fixture recomputes the
   exact three-field-omission preapproval chain and rejects a Receipt, Event,
   request, subject, or Ward substitution;
5. Start durably appends `job.submitted`, later scheduling appends
   `job.queued`; before any ESM or Storage side effect it admits only an exact
   Phase 3 Chronicle Head with `event_count < U63_MAX`, freezes the complete
   Head and self-Sigiled admission evidence for later byte-equal inclusion in
   both Job and submission event, and rejects an unavailable, ambiguous,
   mismatched, or exhausted Head without ESM, Storage, or execution-journal
   side effects through the closed `operation: START_JOB` error branch. It
   creates or reuses the exact single-assignment
   `execution-storage-root-manifest/1.0`, establishes its typed Job-input
   Reference Set with the ESM-ID-derived registration Event, exact validation
   evidence, neutral policy, and domain-separated planned hold under the outer
   gate before the Job event, rejects an incomplete edge closure,
   source/extractor/validator/authorization mismatch, or pre-existing EHR, and
   crashes before or after either journal append recover one Job or a
   conservative orphan hold with no duplicate Attempt; an `ORPHAN_ABORT` EHR
   permanently vetoes later activation, while crash retry preserves the
   original admission evidence and separately requires the then-current Head
   below `U63_MAX`;
6. repeated identical Start returns one Job while conflicting key reuse
   returns `IDEMPOTENCY_CONFLICT`;
7. Observe pages bind a fixed verified journal prefix, remain stable while
   later events append, survive restart, preserve the exact closed public
   projection on every page, and reject cross-Job, malformed, or stale
   cursors; no-Attempt assurance, Worker Session and log ordering, related
   entity ordering, selected-retry log scope, and first-effective
   cancellation selection are deterministic;
8. Observe contains no absolute paths, Lease credentials, secrets, backend
   handles, or unbounded logs while retaining public fence provenance;
9. Cancel commits already-due deadlines first, compares the exact Job revision,
   distinguishes requested from terminal state, fences authority, revokes
   side-effecting handles, verifies Actor and Host Sigils against the
   authenticated context, maps the invocation Sigil to RFC-0012 Host
   provenance, and is idempotent;
10. cancellation of a terminal Job appends one replayable state-neutral
    `job.cancellation_observed` binding and never changes terminal cause;
11. success with a Worker Result and cancellation, timeout, loss, fencing, or
    rejection without a Worker Result all produce deterministic retrievable
    `execution-job-outcome/1.0` documents whose exact attempt summaries,
    selected Attempt, Worker Session, `RESULT_ACCEPTED|NO_RESULT` completion
    anchor, effective-sequence stop/fence precedence,
    exact per-Attempt authorization `NONE|BOUND` state and distinct
    purpose-bound Receipt,
    `NO_ATTEMPT|ASSIGNED_NO_LEASE|TOMBSTONE` final fence, budget settlement,
    Attempt and Job assurance evaluations,
    `NOT_APPLICABLE|VERIFIED|QUARANTINED` terminal source, and frozen storage
    observation reproduce the RFC-0012 decision without a null or abbreviated
    substitute, including the fixed no-Attempt branch and the requirement that
    every offered Lease bind a Session and terminal Lease, no-Attempt logs are
    empty, and a selected Attempt contributes the exact output and resource
    groups including their sentinels, exactly its three Log Streams, the exact
    terminal-source observation member, and both frozen terminalization-set
    bindings, frozen terminalization storage-manifest pair, and exact
    `NO_HOLD|HELD` output-root-protection branch;
    the OJ-ID algorithm is identical across implementations; exact-limit
    `EXHAUSTED` settlement remains valid, while `EXCEEDED` is ineligible;
12. repeated Outcome derivation from the same execution-journal prefix and
    the exact ID-and-Sigil-resolved control-evidence, Quarantine-binding, and
    output-storage-observation sets and output ESM is byte-for-byte equal; the
    Outcome, `ACCOUNTING_CAPTURED`, and observation-set copies of the manifest
    and protection bindings agree byte-for-byte; the four Outcome
    observation groups concatenate to the exact source member array without
    renaming, flattening, omission, or a null substitute; every storage set
    uses its frozen RFC-0013 prefix and deterministic lowest eligible Replica
    selector, later evidence or Replica changes never rewrite it,
    unavailability present at the final intent-bound storage prefix blocks
    acceptance, and Get Outcome changes neither journal nor Chronicle;
13. Job Outcomes exclude later acceptance, Patch, Artifact, Run, and
    Experiment state;
14. Accept rejects stale, late, fenced, duplicate, under-assured, malformed,
    corrupt, quarantined, incomplete, or Sigil-mismatched Outcomes, including
    every `CODE_MODIFICATION` Outcome whose terminal source is not
    `VERIFIED`; retained `QUARANTINED` output maps to
    `OUTPUT_QUARANTINED`, terminal-negative output maps to
    `OUTPUT_UNAVAILABLE`, and either quarantine branch in Log/resource
    evidence maps to `STORAGE_OBSERVATION_INVALID`; every such eligibility
    failure returns the one top-level `RESULT_INELIGIBLE` branch with the
    complete ordered reason set;
15. accepted output produces exactly one deterministic `agent-result/2.0`,
    whose output mapping has only the printed source fields, exact source
    member Sigil, and selected-Replica verification Sigil and maps the explicit
    no-output sentinel to an empty array,
    whose provenance carries the exact ESM and output-protection bindings, one
    complete immutable
    `agent-result-acceptance-authorization/1.0` and embedded
    `agent-result-acceptance-policy/1.0`, one complete immutable
    `agent-result-acceptance-transition-request/1.0`, one
    `agent-result.accepted` Event body, and one paired Receipt outside its
    payload; request-to-intent-to-event mappings verify byte-for-byte without a
    hash cycle, but no automatic Run, Artifact, Experiment, Assessment,
    Decision, Patch, or Seal;
16. exact acceptance retries return the original Receipt; every request using
    the same `(Task-ID, idempotency_key_sigil)` selects the same ATR-ID, and
    different request content fails with `IDEMPOTENCY_CONFLICT` even after a
    crash leaves a complete no-intent request; a different Outcome cannot
    replace a Task's accepted result; a pre-existing v1/v1.1 result returns
    the versioned closed `RESULT_ALREADY_ACCEPTED` branch without fabricating
    an Outcome Sigil;
17. Chronicle replay projects `agent-result-record/2.0` deterministically while
    preserving its transition request, acceptance-storage, Reference Set, and
    canonical-reference intent bindings, resolving and recomputing the complete
    authorization policy, Ward proof, and approval Event/Receipt chain, and
    preserving v1 and v1.1 replay behavior;
18. Patch tools in `mcp-tool-registry/2.0` match RFC-0014 and cannot bypass the
    accepted Agent Result Receipt;
19. Executor, MCP, and Host restart preserve idempotency, fixed-prefix
    observations, terminal outcomes, and canonical acceptance;
20. Phase 2 Chronicle replay and existing MCP contract fixtures remain
    byte-for-byte or semantically equal as their contracts require; and
21. disabled or unavailable execution support leaves the Phase 2 control plane
    fully functional;
22. acceptance registers and validates the exact RFC-0013 Reference Set,
    uses the exact operational Job Outcome with `CONTROL_RETAINS_BLOB` rather
    than falsely classifying it as canonical, performs final Blob validation,
    embeds the complete deterministically selected per-Blob Replica evidence,
    fixes a closed Storage prefix, makes the complete transition request
    durable, and writes the immediately following canonical-reference intent
    under one Storage lock before Chronicle; the minimal eligible no-output
    fixture still retains one distinct empty-byte Blob reached by its three
    `EMPTY` Log observations, and an empty managed set is rejected;
    it commits the permanent v1 pin without releasing or changing the exact
    hold named by the selected `HELD` output-root-protection branch and
    recovers every crash boundary without a duplicate Event, false release,
    missing pin, or hash cycle; the execution hold remains additive until its
    independent RFC-0012 deadline;
    and
23. concurrent GC cannot delete an output between acceptance validation and
    canonical commit because both paths obey the outermost
    canonical-reference gate, execution-root hold protocol, and declared lock
    order; concurrent missing-Replica, integrity-incident, and Quarantine
    fixtures committed before the frozen pre-intent prefix fail acceptance,
    while evidence first committed afterward is a later incident and cannot
    rewrite the bound prefix or Receipt; and
24. acceptance admits a `chronicle-head/1.1` value only while its next Event
    count remains within U63; a valid Head at `U63_MAX` returns the closed
    `CHRONICLE_UNAVAILABLE/HEAD_COUNT_EXHAUSTED` branch, while a greater
    older-contract count returns `CHRONICLE_UNAVAILABLE/HEAD_INVALID`.
    Both fail before Reference Set, transition-request, intent, reservation,
    or Chronicle side effects, use
    `operation: ACCEPT_JOB_OUTCOME`, and never wrap or clamp the count;
25. positive `NOT_REQUIRED` and `REQUIRED` fixtures validate the complete
    authorization preimage and embedded policy self-Sigils. A table-driven
    negative fixture mutates each authority-subject, Ward, approval, policy,
    request, key, Reference-Set, Blob-set, storage-prefix, Actor, Host,
    Chronicle Actor, time, or repeated transition value independently and is
    rejected before Chronicle. The authentication matrix rejects every
    Actor-ID, kind-to-type, Host-class, authentication-mechanism, or outer
    Event-actor mismatch. The approval matrix also rejects a missing subject,
    missing approval transition request, missing approval Event, Receipt-only
    evidence, request/payload/Actor/time inequality, Event/body/Receipt
    inequality, wrong `purpose`, Phase 2 `approval.granted`,
    Attempt-authorization Receipt, and a final Specification that does not
    insert only the exact execution-approval Receipt pair; and
26. transition-request-to-Intent-to-Event replay checks every printed
    equality, including byte-for-byte outer `actor/1.0`, and fails on a
    missing preimage or bare authorization Sigil without a hash cycle.
    Terminal-source fixtures independently exercise the
    `terminal_source_identity`/`terminal_source_sigil`/`storage_blob`
    all-null or all-non-null matrix and exact source-tree `bundle_blob`
    equality. Output-root fixtures reject a wrong ESM owner, entry,
    `blob_refs`, protection plan, manifest source, extractor, validator, edge,
    copied manifest pair, terminal Event `output_storage_roots`, Reference
    Set, hold, or hold-set Event; `NO_HOLD` is valid only for an empty ESM and
    empty terminal root array, an eligible Outcome requires the exact
    one-root `HELD` branch, accepts either its exact still-`ACTIVE` hold or its
    valid already-`RELEASED` output-deadline-EHR successor, never appends a
    release during acceptance, and cannot change any execution root.
