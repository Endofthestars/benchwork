---
title: "RFC-0011: Sanctum Execution Model"
document_id: BW-RFC-0011
version: 0.1
status: draft
owner: unassigned
date: 2026-07-31
language: en
canonical: true
---

# RFC-0011: Sanctum Execution Model

## Status

This draft defines the Phase 3 trust and ownership model for controlled
execution. It refines RFC-0007 and explicitly amends RFC-0009 only to permit
typed delegation to an Executor. It does not weaken the accepted Phase 2
control-plane boundary or make MCP an execution runtime.

This RFC does not authorize an implementation by itself. Job, Lease, and
Worker state machines, Artifact storage, Patch promotion, and the typed
Executor API require RFC-0012 through RFC-0015 and their executable Schemas.

## Problem

Phase 2 can create an immutable Task Capsule, evaluate its declarative Circle
through Ward, obtain a bound human approval, and accept a structured Agent
Result through Athanor. The interactive Host still performs repository,
shell, Git, and web actions with native tools. A `PASS` Ward decision therefore
means that a request is permitted by the declared Capability contract; it is
not evidence that filesystem, network, process, resource, or time boundaries
were enforced.

Phase 3 needs to execute an approved Task in a real environment while
preserving four separations:

1. permission is not enforcement;
2. execution success is not scientific acceptance;
3. mutable execution state is not immutable scientific Run state; and
4. a workspace or container name is not an isolation guarantee.

Without an explicit model, an Executor could silently reinterpret the frozen
Phase 2 Circle, write operational events into Chronicle, grant a Worker broad
Host access, treat a successful process as a scientific Run, or claim
isolation from the mere use of a subprocess or container.

## Decision

Benchwork separates the scientific control plane from a bounded execution
plane.

```text
Task Capsule + pinned Snapshot + Capability Contract
                    |
                    v
       Ward authorization and policy resolution
                    |
                    v
       versioned Execution Specification
                    |
                    v
    Executor -> Job -> Lease -> Attempt -> Worker
                    |
                    v
        Sanctum context + Crucible workspace
                    |
                    v
       bounded result, logs, and output Sigils
                    |
                    v
                 Proposal
                    |
                    v
       Athanor validation -> Chronicle Receipt
```

The control plane owns identity, authorization, policy validation, scientific
validation, and canonical transitions. The execution plane owns scheduling,
leases, process and sandbox control, mutable workspaces, runtime observation,
and result transport. The execution plane cannot append Chronicle events or
mutate canonical projections.

Phase 3 execution requires new closed `capability-registry/2.0`,
`capability-contract/2.0`, and `task-capsule/2.0` contracts plus a closed,
versioned Execution Specification. The v2 Registry stores execution-capable
contracts and their Sigils without changing `capability-registry/1.1`. The v2
contracts must explicitly authorize filesystem scopes, executable and process
capabilities, network policy, environment and credential policy, resource
ceilings, visible inputs, bounded outputs, and the minimum evidence state
required for each control dimension. The Execution Specification pins those
contracts, the Research Snapshot, resolved Circle, requested assurance, inputs,
output limits, runtime requirements, assurance-profile ID, version, and Sigil,
and permitted conformance-suite identity and Sigil. Its exact Schema and
relationship to Job creation are defined by RFC-0012 and RFC-0015.

`capability-contract/1.0` and `task-capsule/1.1` remain valid Phase 2
control-plane contracts for unassured native-Host workflows. They are not
eligible for Executor launch, do not receive a Sanctum assurance claim, and are
not silently reinterpreted as executable sandbox contracts.

A Phase 3 Execution Specification may narrow a v2 Task Capsule, but it may not
add a tool, filesystem scope, executable, process capability, network
permission, credential, budget, input, or output that the pinned Capability
and Task did not authorize. Any broader permission requires a new Task and,
when applicable, a new approval bound to the complete execution policy.

Whenever the resolved approval branch is `REQUIRED`, whether required by the
Capability or upgraded by the Task, the Phase 3 approval binds the exact
Capability Contract Sigil, Task Capsule Sigil, pre-approval Specification
subject, assurance-profile ID, version, and Sigil, permitted
conformance-suite identity and Sigil, and resolved permission set. The
pre-approval subject deterministically covers every final Execution
Specification member except the final self-Sigil and the approval Receipt
binding that is not yet available. The final Specification then binds the
Receipt ID and Sigil and receives its own self-Sigil. Exact match is required.
A narrower or otherwise changed Execution Specification changes the
pre-approval subject and requires a new approval; Benchwork does not infer
subset authorization. A Phase 2 approval Receipt never authorizes a v2 Task.

Absence is not permission. When a pinned contract has no field for an
execution dimension, the Executor treats that dimension as denied. It may not
infer filesystem or command authority from a tool name, objective, Host
conversation, repository layout, or ambient process environment.

Every execution produces operational evidence and, at most, a Proposal.
Athanor remains the only authority that can turn a validated Proposal into
canonical research state and issue a Receipt.

## Owned executable v2 contracts

This RFC owns the following five JSON Schema Draft 2020-12 contracts. Their
filenames and identifiers are normative; an implementation must not publish a
different Schema under one of these identifiers.

| Instance contract | Repository filename | Exact `$id` |
| --- | --- | --- |
| `capability-registry/2.0` | `schemas/capability-registry-2.0.json` | `https://benchwork.dev/schemas/capability-registry/2.0` |
| `capability-contract/2.0` | `schemas/capability-contract-2.0.json` | `https://benchwork.dev/schemas/capability-contract/2.0` |
| `task-capsule/2.0` | `schemas/task-capsule-2.0.json` | `https://benchwork.dev/schemas/task-capsule/2.0` |
| `execution-approval-subject/1.0` | `schemas/execution-approval-subject-1.0.json` | `https://benchwork.dev/schemas/execution-approval-subject/1.0` |
| `execution-approval-transition-request/1.0` | `schemas/execution-approval-transition-request-1.0.json` | `https://benchwork.dev/schemas/execution-approval-transition-request/1.0` |

Each Schema has `$schema` equal to
`https://json-schema.org/draft/2020-12/schema`. The definitions below are the
complete source contract for those Schemas, not illustrative examples. Every
record, whether named, inline, top-level, or nested, is a JSON object for which
every listed member is required and `additionalProperties` is false. Every
union is a Draft 2020-12 `oneOf`; composed branches also set
`unevaluatedProperties` to false. A decoder rejects duplicate object keys
before Schema evaluation. There are no implicit defaults.

Some content rules cannot be expressed portably by JSON Schema alone. A
conforming validator therefore consists of Draft 2020-12 Schema validation
followed by the semantic checks in this section. Schema-valid but
semantically invalid input is invalid for Ward, Executor launch, Sigil
calculation, and persistence.

### Common scalar and collection rules

The five Schemas use these exact aliases:

| Alias | Exact rule |
| --- | --- |
| `Sigil` | ASCII string matching `^sha256:[0-9a-f]{64}$`; 71 bytes. |
| `U63` | JSON integer from 0 through 9,223,372,036,854,775,807. |
| `PositiveU63` | JSON integer from 1 through 9,223,372,036,854,775,807. |
| `Timestamp` | RFC 3339 date-time normalized to UTC with a terminal `Z`, whole seconds only, exactly 20 ASCII bytes. |
| `Version` | ASCII string matching `^[0-9]+[.][0-9]+(?:[.][0-9]+)?$`, 3 through 32 bytes. |
| `CapabilityId` | ASCII string matching `^bench[.][a-z0-9]+(?:[.][a-z0-9]+)+$`, 9 through 128 bytes. |
| `UpperId(P)` | ASCII string matching `^P-[A-Z0-9]+(?:[._-][A-Z0-9]+)*$`, including prefix, 4 through 128 bytes. |
| `WardDecisionId` | ASCII string matching `^WD-[A-Z0-9]+(?:[._-][A-Z0-9]+)*$`, including prefix, 4 through 128 bytes. |
| `StoragePolicyId` | Exact RFC-0013 `SP-ID`: ASCII string matching `^SP-[A-Za-z0-9][A-Za-z0-9._:-]*$`, including prefix, 3 through 128 bytes. |
| `Token` | ASCII string matching `^[A-Za-z0-9][A-Za-z0-9._:-]*$`, 1 through 128 bytes. |
| `LogicalName` | ASCII string matching `^[a-z][a-z0-9_-]*$`, 1 through 64 bytes. |
| `SchemaId` | ASCII string matching `^[a-z][a-z0-9-]*/[0-9]+[.][0-9]+$`, 5 through 128 bytes. |
| `MediaType` | Lowercase ASCII type and subtype matching `^[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+$`, 3 through 128 bytes. |
| `RelativePath` | UTF-8 string of 1 through 1,024 bytes using `/`; it is relative, NFC-normalized, contains no NUL, empty segment, `.` segment, or `..` segment, and has no trailing `/`. |
| `HostName` | Lowercase ASCII DNS name of 1 through 253 bytes; no wildcard, IP literal, trailing dot, user information, or embedded port. |
| `EnvironmentName` | ASCII string matching `^[A-Z_][A-Z0-9_]*$`, 1 through 128 bytes. |
| `HumanText(N)` | NFC-normalized UTF-8 string containing no NUL, from 1 through `N` bytes. |

The concrete `UpperId` prefixes used here are `CR` for a Registry, `TK` for a
Task, `RP` for a Program, `SS` for a Snapshot, `CI` for a Circle, `POL` for a
policy, `TL` for a tool, `EX` for an executable, `RT` for a runtime, `BE` for
a backend, `FS` for a filesystem grant, `ND` for a network destination, `CH`
for a credential handle, `SE` for a side effect, `AP` for an approval policy,
`EA` for an execution-approval subject, `EAT` for an
execution-approval transition request, `AA` for an
Attempt-authorization subject, `RC` for a Receipt, and `CS` for a conformance
suite. A field named with one of those nouns uses that prefix. A research
object ID uses the prefix required by its object Schema and is 3 through 128
ASCII bytes.

A `WardDecisionId` resolves through Ward's immutable decision store to one
complete Ward decision record and its Sigil. Resolution is single-assignment:
the same ID can never resolve to different bytes or a different Sigil.

`Set<T, min, max, key>` means an array with those inclusive item bounds,
`uniqueItems: true`, no null item, and a semantic key that occurs exactly once.
Items are in strictly increasing order by the unsigned UTF-8 bytes of `key`;
equal adjacent keys are invalid even when the complete JSON objects differ.
Scalar sets use the complete scalar. Tuple keys are compared component by
component. A definition that says `enum order` instead uses its explicitly
printed enum order and still rejects a repeated enum value. A map is serialized
with keys in strictly increasing unsigned UTF-8 order. The semantic validator
enforces UTF-8 byte limits, NFC, strict ordering, Set-key and map-key
uniqueness, timestamp normalization, and cross-field conditions; JSON Schema
enforces the corresponding code-point, pattern, type, and item bounds. Every
subset comparison is by this unique semantic key; one parent item can
authorize at most one child item.

`segment_depth(p)` is the positive number of `/`-delimited segments in a
`RelativePath`. A path `q` is within `(path_prefix = p, maximum_depth = d)`
exactly when `q` equals `p`, or `q` is a descendant of `p` and
`segment_depth(q) - segment_depth(p) <= d`. To narrow a parent prefix
`(p_parent, d_parent)` to `(p_child, d_child)`, let
`delta = segment_depth(p_child) - segment_depth(p_parent)`. The child prefix
must equal or descend from the parent and checked arithmetic must prove
`delta + d_child <= d_parent`; overflow is invalid. Equality consumes zero
depth. These rules use the parent prefix as the absolute comparison basis and
apply identically to filesystem and output prefixes.

All Sigils use the canonical JSON encoding defined by RFC-0001: recursively
sorted keys, ASCII escapes, compact separators, and no non-finite number.
`contract_sigil` is SHA-256 over the complete Capability Contract with only
`contract_sigil` omitted. `registry_sigil` is SHA-256 over the complete
Registry with only `registry_sigil` omitted; embedded Capability
`contract_sigil` values remain present. `circle_sigil` is SHA-256 over the
complete Circle with only `circle_sigil` omitted. `capsule_sigil` is SHA-256
over the complete Task Capsule with only `capsule_sigil` omitted; the Circle's
valid `circle_sigil` remains present. Each value is encoded as lowercase
`sha256:` plus the 64 hexadecimal digest digits. A placeholder, all-zero
digest, digest computed with its own member present, or digest of a different
canonical byte stream is invalid.

The only nullable members in these contracts are
`supersedes_registry_sigil`, `expires_at`, the null fields in the
`NOT_REQUIRED` approval branches, and `idempotency_scope_sigil` under the
condition stated below. Conditional union members are absent rather than
null. No other member accepts null.

### Capability policy types

The following closed aliases are shared by the Capability Contract and the
Task Circle. A Task value is a proposed narrowing of the corresponding
Capability value; the comparison is defined later in this section.

`ToolAuthority` is exactly one of:

```text
DENY:
  mode = DENY
  grants = Set<ToolGrant, 0, 0, tool_id>

ALLOWLIST:
  mode = ALLOWLIST
  grants = Set<ToolGrant, 1, 256, tool_id>

ToolGrant:
  tool_id: UpperId(TL)
  tool_version: Version
  tool_sigil: Sigil
  maximum_invocations: PositiveU63
  side_effect_id: UpperId(SE)
```

An observational tool uses a declared `READ_ONLY` Side Effect rather than
omitting `side_effect_id`.

`FilesystemAuthority` is exactly one of:

```text
DENY:
  mode = DENY
  grants = Set<FilesystemGrant, 0, 0, grant_id>

ALLOWLIST:
  mode = ALLOWLIST
  grants = Set<FilesystemGrant, 1, 256, grant_id>

FilesystemGrant:
  grant_id: UpperId(FS)
  root_kind: SNAPSHOT_INPUT, CRUCIBLE, DECLARED_OUTPUT, or EPHEMERAL
  path_prefix: RelativePath
  operations: Set<FilesystemOperation, 1, 8, enum order>
  maximum_read_bytes: U63
  maximum_write_bytes: U63
  maximum_entries: U63
  maximum_depth: U63
  symlink_policy = NOFOLLOW
  mount_policy = NO_NEW_MOUNTS

FilesystemOperation enum order:
  STAT, READ, LIST, CREATE, WRITE, RENAME, DELETE, EXECUTE
```

A zero read or write ceiling denies that byte-producing operation even when
the operation token is present. `SNAPSHOT_INPUT` grants may not contain a
write operation; `DECLARED_OUTPUT` grants may not contain `EXECUTE`.

`ExecutableAuthority` is exactly one of:

```text
DENY:
  mode = DENY
  grants = Set<ExecutableGrant, 0, 0, executable_id>

ALLOWLIST:
  mode = ALLOWLIST
  grants = Set<ExecutableGrant, 1, 128, executable_id>

ExecutableGrant:
  executable_id: UpperId(EX)
  executable_version: Version
  executable_sigil: Sigil
  runtime_id: UpperId(RT)
  runtime_version: Version
  runtime_sigil: Sigil
  entrypoint: RelativePath
  argument_schema_id: SchemaId
  argument_schema_sigil: Sigil
  maximum_starts: PositiveU63
  side_effect_id: UpperId(SE)
```

`ProcessAuthority` is exactly one of:

```text
DENY:
  mode = DENY
  maximum_processes = 0
  maximum_tree_depth = 0
  child_executable_ids = Set<UpperId(EX), 0, 0, value>
  process_group_signals = false
  dynamic_loading = false

ALLOWLIST:
  mode = ALLOWLIST
  maximum_processes: PositiveU63
  maximum_tree_depth: PositiveU63
  child_executable_ids: Set<UpperId(EX), 0, 128, value>
  process_group_signals: boolean
  dynamic_loading: boolean
```

The initial executable is authorized by `ExecutableAuthority`; every child
executable must also occur in `child_executable_ids`. `dynamic_loading` never
authorizes a library whose Blob Sigil is not part of the selected runtime
identity.

`NetworkAuthority` is exactly one of:

```text
DENY:
  mode = DENY
  dns_mode = DENY
  destinations = Set<NetworkDestination, 0, 0, destination_id>
  maximum_connections = 0
  maximum_requests = 0
  maximum_egress_bytes = 0

ALLOWLIST:
  mode = ALLOWLIST
  dns_mode = PINNED_ANSWER
  destinations = Set<NetworkDestination, 1, 256, destination_id>
  maximum_connections: PositiveU63
  maximum_requests: PositiveU63
  maximum_egress_bytes: PositiveU63

NetworkDestination:
  destination_id: UpperId(ND)
  protocol: TCP, UDP, HTTP, or HTTPS
  host: HostName
  ports: Set<integer 1..65535, 1, 32, value>
  address_policy_sigil: Sigil
  redirect_policy: DENY or SAME_DESTINATION
  side_effect_id: UpperId(SE)
```

`PINNED_ANSWER` requires the selected address-policy Sigil to bind every
resolved address before launch. Redirects never add a host, port, protocol,
or address.

`EnvironmentAuthority` is exactly one of:

```text
DENY:
  mode = DENY
  inheritance = NONE
  variables = Set<EnvironmentVariable, 0, 0, name>

ALLOWLIST:
  mode = ALLOWLIST
  inheritance = NONE
  variables = Set<EnvironmentVariable, 1, 256, name>

EnvironmentVariable:
  name: EnvironmentName
  source_kind: CONSTANT, SNAPSHOT_METADATA, RUNTIME_METADATA,
               or CREDENTIAL_HANDLE
  source_binding_id: Token
  source_sigil: Sigil
  required: boolean
```

An environment rule authorizes only the exact content or opaque source bound
by `source_sigil`; the contract never carries a secret value. Ambient
inheritance, path-derived variables, and unlisted variables are denied.

`CredentialAuthority` is exactly one of:

```text
DENY:
  mode = DENY
  ambient_credentials = false
  value_exposure = NEVER
  handles = Set<CredentialHandle, 0, 0, handle_id>

OPAQUE_HANDLES:
  mode = OPAQUE_HANDLES
  ambient_credentials = false
  value_exposure = NEVER
  handles = Set<CredentialHandle, 1, 64, handle_id>

CredentialHandle:
  handle_id: UpperId(CH)
  credential_class: Token
  scope_sigil: Sigil
  maximum_uses: PositiveU63
  side_effect_id: UpperId(SE)
```

Credentials are opaque handles supplied by a separately trusted broker.
Neither branch permits a raw credential, inherited token, credential path, or
Worker-readable secret value.

The resource and lifecycle aliases are closed records:

```text
AttemptBudget:
  cpu_time_seconds: U63
  peak_memory_bytes: U63
  storage_bytes_written: U63
  output_bytes: U63
  log_bytes: U63
  process_starts: U63
  network_egress_bytes: U63
  network_requests: U63

JobBudget:
  attempts: PositiveU63
  cpu_time_seconds: U63
  storage_bytes_written: U63
  output_bytes: U63
  log_bytes: U63
  process_starts: U63
  network_egress_bytes: U63
  network_requests: U63

ResourceAuthority:
  attempt_budget: AttemptBudget
  job_budget: JobBudget
  maximum_open_files: U63
  maximum_file_count: U63
  maximum_concurrent_threads: U63

DeadlineAuthority:
  lease_duration_seconds: PositiveU63
  heartbeat_interval_seconds: PositiveU63
  heartbeat_timeout_seconds: PositiveU63
  lease_claim_timeout_seconds: PositiveU63
  attempt_wall_time_seconds: PositiveU63
  cancellation_grace_seconds: U63
  job_wall_time_seconds: PositiveU63
  clock_uncertainty_tolerance_seconds: U63

RetryAuthority:
  maximum_attempts: PositiveU63
  allowed_retryable_terminal_reasons:
    Set<RetryableTerminalReason, 0, 25, enum order>
  allowed_backoff_kinds:
    Set<BackoffKind, 1, 3, enum order>
  maximum_backoff_base_seconds: U63
  maximum_backoff_cap_seconds: U63
  allowed_resume_policies:
    Set<ResumePolicy, 1, 2, enum order>

BackoffKind enum order:
  NONE, FIXED, EXPONENTIAL

ResumePolicy enum order:
  FRESH_ONLY, ALLOW_IMMUTABLE_RESUME

RetryableTerminalReason enum order:
  ATTEMPT_DEADLINE, HEARTBEAT_TIMEOUT, LEASE_CLAIM_EXPIRED,
  LEASE_ACTIVE_EXPIRED, LEASE_REVOKED, RECOVERY_FENCE, CLOCK_UNCERTAIN,
  EXECUTOR_EPOCH_CHANGED, SESSION_CHANNEL_LOST, PREFLIGHT_REJECTED,
  START_FAILED, COMPUTATION_FAILED, VALIDATION_FAILED, RESULT_CONFLICT,
  RESULT_REQUIREMENT_FAILED, OUTPUT_VALIDATION_FAILED,
  TERMINAL_SOURCE_RETENTION_FAILED, TERMINATION_FAILED, CLEANUP_FAILED,
  LOST_OWNERSHIP, ASSURANCE_UNMET, ASSURANCE_UNVERIFIABLE,
  BUDGET_EXHAUSTED, ATTEMPT_REJECTED, FATAL_INFRASTRUCTURE

LoggingAuthority:
  stdout_maximum_bytes: U63
  stderr_maximum_bytes: U63
  structured_maximum_bytes: U63
  aggregate_maximum_bytes: U63
  chunk_maximum_bytes: U63
  allowed_overflow_behaviors:
    Set<OverflowBehavior, 1, 2, enum order>

OverflowBehavior enum order:
  TRUNCATE, TERMINATE

ResultAuthority:
  allowed_worker_result_modes:
    Set<WorkerResultMode, 1, 2, enum order>

WorkerResultMode enum order:
  REQUIRED, OPTIONAL, FORBIDDEN

PostTerminalAuthority:
  allowed_modes:
    Set<PostTerminalMode, 1, 2, enum order>
  retention_policies:
    Set<RetentionPolicyBinding, 0, 32,
        (retention_policy_id, retention_policy_version)>
  terminal_source_maximum_files: U63
  terminal_source_maximum_bytes: U63
  retention_duration_seconds: U63
  source_identity_profiles:
    Set<SourceIdentityProfile, 0, 1, enum order>

PostTerminalMode enum order:
  NONE, CODE_MODIFICATION

SourceIdentityProfile enum order:
  BENCHWORK_SOURCE_TREE_V1

RetentionPolicyBinding:
  retention_policy_id: StoragePolicyId
  retention_policy_version: Version, constant "1.0"
  retention_policy_sigil: Sigil

LifecycleAuthority:
  deadlines: DeadlineAuthority
  retry: RetryAuthority
  logging: LoggingAuthority
  result: ResultAuthority
  post_terminal: PostTerminalAuthority
```

`allowed_worker_result_modes` has exactly one of the four canonical values
`[REQUIRED]`, `[OPTIONAL]`, `[FORBIDDEN]`, or
`[REQUIRED, FORBIDDEN]`. `OPTIONAL` semantically admits all three resolved
modes; `REQUIRED` admits only `REQUIRED`; `FORBIDDEN` admits only `FORBIDDEN`;
and `[REQUIRED, FORBIDDEN]` admits either strict branch but not `OPTIONAL`.
Any array that combines `OPTIONAL` with another token is non-canonical and
invalid. A Task result set narrows a Capability result set exactly when its
admitted resolved-mode set is a subset. A Specification selects one member of
the intersection of the Capability and Task admitted sets, not necessarily a
token printed literally in both arrays.

A `RetentionPolicyBinding` is an exact import of one RFC-0013
`artifact-retention-policy/1.0` record. Its `retention_policy_id` equals that
record's `policy_id`, `retention_policy_sigil` equals its `record_sigil`, and
`retention_policy_version` is the importing contract-version constant `1.0`;
it is not an independent version field on the RFC-0013 record. Resolution of a
missing record, a non-`SP-` ID, a version other than `1.0`, or a mismatched
record Sigil fails closed.

`retention_duration_seconds` is a maximum lifetime for the execution-owned
Storage hold that protects retained terminal source. It is not a minimum
physical-retention duration, does not rewrite the imported RFC-0013 policy's
absolute `retain_until`, and cannot extend any policy selected by that record.
RFC-0012 derives one absolute `release_due_at` by checked UTC addition of the
trusted parent Job terminal Event's `recorded_at` and the resolved duration.
Worker time, backend time, filesystem metadata, and retrieval time are never
inputs. An unrepresentable addition fails closed and cannot saturate, wrap, or
be interpreted as an indefinite hold.

Once that execution root is inactive, `release_due_at` is its immutable
scheduled release point; restart and Recovery may complete the same release
but may not choose or persist a later deadline. A coordinator reconciles the
hold at the first trusted opportunity at which RFC-0012 and RFC-0013 can prove
the complete ownership prefix and due predicate. The hold may remain active
after the scheduled point only while trusted time, replay, or ownership proof
is unavailable or ambiguous; that fail-closed overdue state is not a deadline
extension and no policy may deliberately schedule release later. This releases
neither an RFC-0013 canonical-reference pin nor a legal, preservation, or other
policy hold and does not itself authorize deletion. Those protections are
additive and may retain the bytes after the execution hold expires.

`JobBudget.attempts` equals `RetryAuthority.maximum_attempts`. Every aggregate
Job ceiling is at least the corresponding Attempt ceiling. The heartbeat
interval is less than the heartbeat timeout, the timeout does not exceed the
lease duration, claim timeout does not exceed lease duration, and lease and
Attempt wall time do not exceed Job wall time. Logging aggregate bytes do not
exceed the sum of the three stream ceilings, and chunk bytes do not exceed the
aggregate ceiling. When maximum attempts is greater than one, the retryable
reason set is non-empty. If only `NONE` backoff is allowed, both backoff maxima
are zero; otherwise the base maximum is positive and the cap maximum is no
smaller. If `CODE_MODIFICATION` is absent, the retention-policy and
source-profile sets are empty and all three post-terminal numeric ceilings
are zero. If it is present, those sets and ceilings are non-empty or positive
as their element types require.

Those user-selectable post-terminal retention policies are distinct from the
mandatory execution-root operational hold policy. Every non-empty RFC-0012
`execution-storage-root-manifest/1.0`, including `JOB_INPUT`,
`ATTEMPT_INPUT`, and a `NONE`-mode `ATTEMPT_OUTPUT`, uses the exact installed
RFC-0013 policy whose ID is `SP-EXECUTION-ROOT-HOLD-V1`. That policy is not a
member of either authority's selectable retention-policy set and grants no
new execution or post-terminal derivation authority. RFC-0012 fixes its
resolved policy Sigil in the preallocated protection plan, and RFC-0013 fixes
the complete installed record and hold authorization. Missing, changed, or
project-mismatched resolution blocks root planning.

The resolved RFC-0012 retry branch keeps all fields present. `NONE` selects
zero base and cap; `FIXED` selects a positive base and an equal cap; and
`EXPONENTIAL` selects a positive base and a cap no smaller than the base. The
selected values remain within both authorities' maxima. The resolved resume
policy is exactly `FRESH_ONLY` or `ALLOW_IMMUTABLE_RESUME` and occurs in both
allowed sets.

Input and output authority use these aliases:

```text
InputAuthority is exactly one of:
  DENY:
    mode = DENY
    maximum_inputs = 0
    maximum_aggregate_bytes = 0
    allowed_object_types =
      Set<SnapshotObjectType, 0, 0, enum order>
    allowed_media_types = Set<MediaType, 0, 0, value>
    require_immutable_identity = true
    require_content_sigil = true
  ALLOWLIST:
    mode = ALLOWLIST
    maximum_inputs: PositiveU63
    maximum_aggregate_bytes: PositiveU63
    allowed_object_types:
      Set<SnapshotObjectType, 1, 17, enum order>
    allowed_media_types:
      Set<MediaType, 1, 64, value>
    require_immutable_identity = true
    require_content_sigil = true

SnapshotObjectType enum order:
  research-program, evidence, claim, hypothesis, protocol, working,
  experiment, run, result-bundle, assessment, decision, artifact, issue,
  deviation, reproduction-record, review-request, review-artifact

SnapshotObjectId prefix by object type:
  research-program = RP, evidence = EV, claim = CL, hypothesis = HY,
  protocol = PT, working = WK, experiment = EX, run = RUN,
  result-bundle = RB, assessment = AS, decision = DE, artifact = AR,
  issue = IS, deviation = DV, reproduction-record = RR,
  review-request = RV, review-artifact = RV
  Each branch is UpperId(the printed prefix), selected by object_type.

PathRule is exactly one of:
  FIXED:
    kind = FIXED
    relative_path: RelativePath
  PREFIX:
    kind = PREFIX
    relative_prefix: RelativePath
    maximum_depth: U63

OutputGrant:
  logical_name: LogicalName
  schema_id: SchemaId
  schema_sigil: Sigil
  maximum_bytes: PositiveU63
  maximum_count: PositiveU63
  path_rule: PathRule
  side_effect_id: UpperId(SE)

OutputAuthority is exactly one of:
  DENY:
    mode = DENY
    maximum_outputs = 0
    maximum_aggregate_bytes = 0
    grants = Set<OutputGrant, 0, 0, logical_name>
  ALLOWLIST:
    mode = ALLOWLIST
    maximum_outputs: PositiveU63
    maximum_aggregate_bytes: PositiveU63
    grants = Set<OutputGrant, 1, 256, logical_name>
```

In the `ALLOWLIST` branch, `maximum_outputs` is no greater than the sum of
grant `maximum_count` values, and `maximum_aggregate_bytes` is no greater than
the resource output ceilings. Each output path must also be covered by a
writable `DECLARED_OUTPUT` filesystem grant. A fixed path narrows an equal
fixed path or a parent prefix exactly when its segment delta is within the
parent maximum depth. A child prefix narrows a parent prefix only under the
checked `delta + d_child <= d_parent` rule above. A prefix never narrows a
fixed path.

Runtime, side-effect, approval, and assurance aliases are:

```text
IdentityBinding:
  identity_id: Token
  identity_version: Version
  identity_sigil: Sigil

ConstraintBinding:
  constraint_id: Token
  constraint_sigil: Sigil

IdentityRequirements:
  require_host_identity: boolean
  require_backend_configuration_identity: boolean
  require_runtime_content_identity: boolean

RuntimeAuthority:
  runtime_identities:
    Set<IdentityBinding, 1, 64,
        (identity_id, identity_version, identity_sigil)>
  backend_identities:
    Set<IdentityBinding, 1, 64,
        (identity_id, identity_version, identity_sigil)>
  host_constraints:
    Set<ConstraintBinding, 0, 64, constraint_id>
  identity_requirements: IdentityRequirements

SideEffectGrant:
  side_effect_id: UpperId(SE)
  kind: READ_ONLY, IDEMPOTENT_WRITE, or SINGLE_USE_EXTERNAL
  authority_sigil: Sigil
  maximum_invocations: PositiveU63
  retry_mode: NO_RETRY, SAME_IDEMPOTENCY_KEY,
              or NEW_AUTHORIZATION_EACH_ATTEMPT
  idempotency_scope_sigil: Sigil or null
  requires_approval: boolean

SideEffectAuthority:
  grants: Set<SideEffectGrant, 0, 128, side_effect_id>

ApprovalAuthority is exactly one of:
  NOT_REQUIRED:
    requirement = NOT_REQUIRED
    policy_id = null
    policy_version = null
    policy_sigil = null
    binding_scope = NONE
  REQUIRED:
    requirement = REQUIRED
    policy_id: UpperId(AP)
    policy_version: Version
    policy_sigil: Sigil
    binding_scope = EXACT_EXECUTION_POLICY

ControlRequirement:
  control_dimension: ControlDimension
  required_state: ANY_RECORDED, OBSERVED, VERIFIED, or ENFORCED
  required_evidence_kinds:
    Set<EvidenceKind, 1, 29, enum order>
  requirement_evidence_profile_sigil: Sigil

AssuranceGrant:
  requested_level: SANCTUM-A0, SANCTUM-A1, or SANCTUM-A2
  profile_version: Version
  profile_sigil: Sigil
  conformance_suite_id: UpperId(CS)
  conformance_suite_sigil: Sigil
  control_requirements:
    Set<ControlRequirement, 10, 10, control-dimension order>

AssuranceAuthority:
  grants:
    Set<AssuranceGrant, 1, 64,
        (requested_level, profile_version, profile_sigil,
         conformance_suite_id, conformance_suite_sigil)>
```

`idempotency_scope_sigil` is non-null exactly for
`SAME_IDEMPOTENCY_KEY` and null for the other retry modes.
`SINGLE_USE_EXTERNAL` requires `maximum_invocations` equal to one and may use
only `NO_RETRY` or `NEW_AUTHORIZATION_EACH_ATTEMPT`. In a Capability Contract,
a grant with `requires_approval: true` is valid only when the Capability
approval branch is `REQUIRED`. A Task or resolved Specification may narrow
`false` to `true` only when its own approval branch is `REQUIRED`, the exact
side-effect ID is covered by that approval, and the policy tuple satisfies the
rules below. Every `side_effect_id` referenced by a tool, executable,
destination, credential handle, or output grant exists exactly once in
`SideEffectAuthority`.

The exact `ControlDimension` order is:

```text
IDENTITY_AUTHORIZATION
FILESYSTEM
NETWORK
PROCESS_EXECUTABLE
RESOURCE
ENVIRONMENT_CREDENTIAL
LOG_OUTPUT_CAPTURE
RUNTIME_INPUT_OUTPUT_IDENTITY
CANCELLATION_FENCING
TERMINATION_CLEANUP
```

The exact `EvidenceKind` order is:

```text
TASK_BINDING
CAPABILITY_BINDING
SNAPSHOT_BINDING
WARD_DECISION
APPROVAL_RECEIPT
BACKEND_CONFIGURATION
HOST_IDENTITY
POLICY_RESOLUTION
BASE_IDENTITY
INPUT_IDENTITY
MATERIALIZATION_IDENTITY
ENVIRONMENT_CONSTRUCTION
FILESYSTEM_POLICY
NETWORK_POLICY
EXECUTABLE_SELECTION
PROCESS_TREE
WALL_TIME_ENFORCEMENT
RESOURCE_ACCOUNTING
CREDENTIAL_NONINHERITANCE
LOG_CAPTURE
OUTPUT_VALIDATION
STORAGE_OBSERVATION
FENCE_TOMBSTONE
TERMINATION
HANDLE_REVOCATION
CLEANUP
QUARANTINE
TERMINAL_SOURCE_VERIFICATION
CONFORMANCE_FIXTURE
```

The ten control requirements occur exactly once and in the printed order.
Their requested state and evidence profile may be stronger than the selected
assurance profile's minimum but never weaker. Requirement satisfaction is not
a total ordering: `ANY_RECORDED` accepts `UNAVAILABLE`, `OBSERVED`,
`VERIFIED`, or `ENFORCED`; `OBSERVED` accepts `OBSERVED`, `VERIFIED`, or
`ENFORCED`; `VERIFIED` accepts only `VERIFIED`; and `ENFORCED` accepts only
`ENFORCED`.

### `capability-contract/2.0`

The top-level Capability Contract has exactly these required members:

| Field | Exact type or value |
| --- | --- |
| `schema_version` | Constant `capability-contract/2.0`. |
| `capability_id` | `CapabilityId`. |
| `contract_version` | Constant `2.0`. |
| `display_name` | `HumanText(128)`. |
| `purpose` | `HumanText(4096)`. |
| `tools` | `ToolAuthority`. |
| `filesystem` | `FilesystemAuthority`. |
| `executable` | `ExecutableAuthority`. |
| `process` | `ProcessAuthority`. |
| `network` | `NetworkAuthority`. |
| `environment` | `EnvironmentAuthority`. |
| `credential` | `CredentialAuthority`. |
| `resource` | `ResourceAuthority`. |
| `input` | `InputAuthority`. |
| `output` | `OutputAuthority`. |
| `runtime` | `RuntimeAuthority`. |
| `lifecycle` | `LifecycleAuthority`. |
| `side_effects` | `SideEffectAuthority`. |
| `assurance` | `AssuranceAuthority`. |
| `approval` | `ApprovalAuthority`. |
| `issued_at` | `Timestamp`. |
| `expires_at` | `Timestamp` or null. |
| `contract_sigil` | Self-Sigil defined above. |

`expires_at`, when non-null, is later than `issued_at`. IDs used by a grant
are unique across that grant type. Every executable names an allowed runtime;
all process child IDs name allowed executable grants. Every credential-backed
environment source names an allowed credential handle. Denied facilities
have their exact `DENY` branch and zero bounds; a missing facility is invalid,
not denied.

Cross-dimension bounds are checked in both a Capability and a Task Circle.
Executable starts do not exceed the process-start budgets; network requests
and egress do not exceed their Attempt and Job counters; output and log
aggregates do not exceed their matching counters; and bounded filesystem
writes fit the storage-written counters. For each Side Effect, the sum of
maximum invocations through its referencing grants does not exceed the Side
Effect maximum. A zero resource counter therefore denies the corresponding
facility even if a separate allowlist accidentally contains a grant.

### `capability-registry/2.0`

The top-level Capability Registry has exactly these required members:

| Field | Exact type or value |
| --- | --- |
| `schema_version` | Constant `capability-registry/2.0`. |
| `registry_id` | `UpperId(CR)`. |
| `registry_revision` | `U63`. |
| `created_at` | `Timestamp`. |
| `supersedes_registry_sigil` | `Sigil` or null. |
| `capabilities` | Map of 1 through 4,096 `CapabilityId` keys to complete `capability-contract/2.0` values. |
| `registry_sigil` | Self-Sigil defined above. |

At revision zero, `supersedes_registry_sigil` is null. At every later
revision it is non-null and equals the Registry Sigil at revision minus one;
the creation time does not move backward. Revisions are contiguous. Map keys
are sorted and unique by `CapabilityId`; a duplicate JSON key fails before
Schema validation. Each value is the complete v2 Contract, including its
valid `contract_sigil`, and the map key is byte-for-byte equal to that value's
`capability_id`. A v1 contract, abbreviated binding, `$ref` object, null
value, alias, or key/value mismatch is invalid. A Capability ID occurs once
per revision and denotes the same capability lineage across revisions;
changing its Contract keeps the ID but changes the complete value and Sigils
in a new revision.

### `task-capsule/2.0`

Task-specific aliases are:

```text
RegistryBinding:
  registry_id: UpperId(CR)
  registry_revision: U63
  registry_sigil: Sigil

CapabilityBinding:
  capability_id: CapabilityId
  contract_version = 2.0
  contract_sigil: Sigil

SnapshotBinding:
  snapshot_id: UpperId(SS)
  snapshot_sigil: Sigil

VisibleInput:
  logical_name: LogicalName
  object_id: SnapshotObjectId matched to object_type
  object_type: SnapshotObjectType
  object_sigil: Sigil
  media_type: MediaType
  maximum_bytes: PositiveU63
  mount_path: RelativePath

ExpectedOutput:
  logical_name: LogicalName
  schema_id: SchemaId
  schema_sigil: Sigil
  maximum_bytes: PositiveU63
  maximum_count: PositiveU63
  path_rule: PathRule
  side_effect_id: UpperId(SE)

Circle:
  circle_id: UpperId(CI)
  tools: ToolAuthority
  filesystem: FilesystemAuthority
  executable: ExecutableAuthority
  process: ProcessAuthority
  network: NetworkAuthority
  environment: EnvironmentAuthority
  credential: CredentialAuthority
  resource: ResourceAuthority
  input: InputAuthority
  output: OutputAuthority
  runtime: RuntimeAuthority
  lifecycle: LifecycleAuthority
  side_effects: SideEffectAuthority
  circle_sigil: Sigil

RequestedAssurance:
  requested_level: SANCTUM-A0, SANCTUM-A1, or SANCTUM-A2
  profile_version: Version
  profile_sigil: Sigil
  conformance_suite_id: UpperId(CS)
  conformance_suite_sigil: Sigil
  control_requirements:
    Set<ControlRequirement, 10, 10, control-dimension order>

ApprovalBinding is exactly one of:
  NOT_REQUIRED:
    requirement = NOT_REQUIRED
    policy_id = null
    policy_version = null
    policy_sigil = null
    binding_scope = NONE
    bound_side_effect_ids = Set<UpperId(SE), 0, 0, value>
  REQUIRED:
    requirement = REQUIRED
    policy_id: UpperId(AP)
    policy_version: Version
    policy_sigil: Sigil
    binding_scope = EXACT_EXECUTION_POLICY
    bound_side_effect_ids:
      Set<UpperId(SE), 0, 128, value>
```

The top-level Task Capsule has exactly these required members:

| Field | Exact type or value |
| --- | --- |
| `schema_version` | Constant `task-capsule/2.0`. |
| `task_id` | `UpperId(TK)`. |
| `host` | Exactly `cli`, `codex`, or `claude-code`. |
| `program_id` | `UpperId(RP)`. |
| `objective` | `HumanText(16384)`. |
| `registry_binding` | `RegistryBinding`. |
| `capability_binding` | `CapabilityBinding`. |
| `snapshot_binding` | `SnapshotBinding`. |
| `visible_inputs` | `Set<VisibleInput, 0, 4096, logical_name>`. |
| `expected_outputs` | `Set<ExpectedOutput, 0, 256, logical_name>`. |
| `circle` | `Circle`. |
| `requested_assurance` | `RequestedAssurance`. |
| `approval_binding` | `ApprovalBinding`. |
| `created_at` | `Timestamp`. |
| `expires_at` | `Timestamp` or null. |
| `capsule_sigil` | Self-Sigil defined above. |

The Registry binding resolves one immutable v2 Registry. The Capability
binding resolves exactly the complete value at its matching map key and
repeats that value's version and Sigil. The Snapshot resolves one immutable
`research-snapshot/1.0` whose `program_id` equals the Task `program_id`.
Every visible input occurs in that Snapshot with byte-for-byte equal object
ID, type, and Sigil; logical names and mount paths are separately unique.
Visible-input counts, aggregate byte maxima, types, and media types satisfy
both Capability and Circle input authorities. No repository file,
conversation turn, ambient directory, or unpinned research object is an
input.

`created_at` is no earlier than the bound Registry creation time, Capability
issue time, or Snapshot creation time. The Capability and Task are unexpired
at Ward authorization; expiration after launch is handled only by the closed
RFC-0012 deadline and cancellation rules and never extends authority.

Every expected output is byte-for-byte equal to its unique-key Circle output
grant. The matching Capability grant has the same logical name, Schema ID,
Schema Sigil, and side-effect ID; its path rule is equal to or broader than
the Task path rule under the fixed/prefix and checked-depth rules, and its
count and byte maxima are equal or higher. Logical names and fixed paths are
unique. Their aggregate maxima fit both output and resource ceilings. The
Circle output grant array and `expected_outputs` are byte-for-byte equal; the
duplicated location makes the declared output set directly inspectable but
cannot create a second authority. The Execution Specification resolves
`output_contracts` from this exact ordered array and may retain an explicit
subset, narrow a path rule, or lower its bounds; no undeclared output becomes
a Proposal.

At Specification resolution, `REQUIRED` requires a non-empty resolved
`output_contracts` array, `FORBIDDEN` requires an empty array and a resolved
output `DENY` branch, and `OPTIONAL` permits either. The Task may advertise
more than one allowed result mode, but the Specification selects exactly one
and applies this relation without inventing an output.

The Circle contains every execution dimension even when it denies that
dimension. Ward validates its `circle_sigil` before comparing authority; the
Capsule self-Sigil covers that already validated Circle including its
`circle_sigil`. It is invalid if any member is broader than the pinned
Capability. Its side-effect set contains exactly the grants referenced by its
selected tools, executables, destinations, credential handles, and outputs.
The requested assurance tuple and all ten control requirements equal one
Capability assurance grant. `approval_binding.bound_side_effect_ids` is
exactly the sorted Circle side-effect IDs whose grants require approval. If
that set is non-empty or the Capability requires approval, the Task branch is
`REQUIRED` and its approval-policy tuple is byte-for-byte equal to the
Capability tuple. A Task may upgrade a `NOT_REQUIRED` Capability to a
`REQUIRED` Task only with a closed approval-policy tuple recognized by Ward's
versioned policy set; an unknown tuple fails closed. It cannot downgrade or
substitute a Capability-required policy.

An approval Receipt is deliberately not embedded in the Capsule. The Task's
`approval_binding` is the immutable requirement; RFC-0012 `authorization`
carries the resulting Receipt ID and Sigil. `expires_at`, when non-null, is
later than `created_at`; an expired Task is well-formed but ineligible for a
new Ward authorization or launch.

For a `REQUIRED` branch, Ward first constructs the complete final
`execution-specification/1.0` candidate with two deliberate omissions:
`specification_sigil` is absent, and `authorization.approval_receipt_id` plus
`authorization.approval_receipt_sigil` are absent. The authorization object
still contains its exact Ward-decision fields and
`approval_requirement: REQUIRED`; every other final member and value is
already fixed. `preapproval_specification_sigil` is SHA-256 over that
canonical candidate. This digest preimage is not a Schema instance and is
never persisted or launched. Omitting any additional field, using a
placeholder, or changing a field after this digest is invalid.

The closed approval aliases are:

```text
ApprovalAssuranceBinding:
  requested_level: SANCTUM-A0, SANCTUM-A1, or SANCTUM-A2
  profile_version: Version
  profile_sigil: Sigil
  conformance_suite_id: UpperId(CS)
  conformance_suite_sigil: Sigil

ExecutionApprovalSubject:
  schema_version = execution-approval-subject/1.0
  approval_subject_id: UpperId(EA)
  specification_id: RFC-0012 Specification ID
  preapproval_specification_sigil: Sigil
  registry_binding: RegistryBinding
  task_id: UpperId(TK)
  task_capsule_sigil: Sigil
  capability_binding: CapabilityBinding
  snapshot_binding: SnapshotBinding
  circle_id: UpperId(CI)
  circle_sigil: Sigil
  ward_decision_id: WardDecisionId
  ward_decision_sigil: Sigil
  approval_policy_id: UpperId(AP)
  approval_policy_version: Version
  approval_policy_sigil: Sigil
  assurance_requirement: ApprovalAssuranceBinding
  resolved_permission_set_sigil: Sigil
  approval_subject_sigil: Sigil

ExecutionApprovalTransitionRequest:
  schema_version = execution-approval-transition-request/1.0
  transition_request_id: EAT-ID
  event_type = execution.approval.granted
  purpose = EXECUTION_APPROVAL
  expected_chronicle_head: RFC-0013 ChronicleHeadRef
  approval_subject: ExecutionApprovalSubject
  actor: RFC-0015 ActorBinding
  host_invocation: RFC-0015 HostInvocationBinding
  chronicle_actor: exact RFC-0001 actor/1.0
  idempotency_key_sigil: Sigil
  requested_at: Timestamp
  transition_request_sigil: Sigil

ExecutionApprovalGrantedPayload:
  transition_request_id: EAT-ID
  transition_request_sigil: Sigil
  purpose = EXECUTION_APPROVAL
  approval_subject_id: UpperId(EA)
  approval_subject_sigil: Sigil
  actor: RFC-0015 ActorBinding
  occurred_at: Timestamp
```

`resolved_permission_set_sigil` is SHA-256 over one closed canonical object
containing the candidate's exact `policies`, `output_contracts`,
`result_requirement`, `runtime_constraints`, `assurance_requirement`,
`deadline_policy`, `attempt_budget`, `job_budget`, `retry_policy`,
`logging_policy`, `post_terminal_derivation`, and
`conformance_policy_version` members. `approval_subject_sigil` is the
self-Sigil over the complete subject with only that member omitted.

`approval_subject_id` is content-derived and exactly 67 ASCII bytes:

```text
approval_subject_id =
  "EA-" + UPPER_HEX(SHA256(canonical_json(
    ["execution-approval-subject-id/1.0",
     specification_id,
     preapproval_specification_sigil,
     registry_binding,
     task_id,
     task_capsule_sigil,
     capability_binding,
     snapshot_binding,
     circle_id,
     circle_sigil,
     ward_decision_id,
     ward_decision_sigil,
     approval_policy_id,
     approval_policy_version,
     approval_policy_sigil,
     assurance_requirement,
     resolved_permission_set_sigil])))
```

The subject resolver is immutable and single-assignment by that derived
`approval_subject_id`. It rederives the ID before storage or use; the same ID
cannot resolve to different bytes or a different `approval_subject_sigil`.
Changing any semantic member therefore requires a different subject ID, while
presenting changed bytes under an existing ID is an integrity conflict.

The raw approval idempotency key accepted at the authenticated request boundary
is an NFC-normalized UTF-8 string of 1 through 256 bytes containing no NUL or
Unicode control character. It is never persisted in the transition request.
Its exact durable projection is:

```text
idempotency_key_sigil =
  Sigil(["execution-approval-idempotency-key/1.0",
         raw_approval_idempotency_key])
```

`EAT-ID` is exactly `EAT-` followed by the uppercase 64-hex SHA-256 digest of
canonical JSON:

```text
["execution-approval-transition-request-id/1.0",
 approval_subject.task_id,
 idempotency_key_sigil]
```

The request's self-Sigil covers every other request member. Its
`approval_subject` is the complete subject above, and the expected Head is the
exact Phase 3-admissible RFC-0013 `ChronicleHeadRef`. The authenticated caller
fixes the bounded idempotency key, actor, Host invocation, Chronicle actor,
request time, and expected Head before the request becomes durable. The
`chronicle_actor` is the complete canonical RFC-0001 `actor/1.0`
`{actor_id, actor_type, host, authenticated_by}`. It has no independent
self-Sigil but is covered by `transition_request_sigil`.
`actor.authentication_context_sigil ==
host_invocation.authentication_context_sigil`; both binding self-Sigils
validate; and all three records are produced byte-for-byte from the same
authenticated invocation context rather than caller text.
`chronicle_actor.actor_id == actor.actor_id`; the closed kind mapping is
`USER -> human`, `AGENT -> agent`, and `SYSTEM -> policy|tool`. The Chronicle
`host` and `authenticated_by` values equal that context's canonical audit
Host and authentication mechanism and are not inferred from a Host-identity
Sigil, invocation ID, or caller text. The immutable resolver is
single-assignment by `transition_request_id`, and the unique operation scope is
`(EXECUTION_APPROVAL, approval_subject.task_id, idempotency_key_sigil)`: an
exact retry reuses the same bytes and any changed subject, actor, invocation,
Chronicle actor, Head, time, purpose, or key is an idempotency conflict rather
than a new interpretation of the old request. In particular, a caller cannot
escape that conflict by presenting a different derived `EA-ID`.

The successful canonical Event is an exact `chronicle-event/1.1` whose `type`
is `execution.approval.granted`, whose `object_id` equals
`approval_subject_id`, and whose payload is exactly
`ExecutionApprovalGrantedPayload`. Its payload resolves the exact transition
request by ID and Sigil and requires the same purpose, subject ID and Sigil,
actor, and request time byte-for-byte; `occurred_at == requested_at` and the
outer Event's `occurred_at` is the same value. The outer Event's complete
`actor` is byte-for-byte the request's `chronicle_actor`; its payload
`actor` remains the RFC-0015 `ActorBinding`. The transition commits only
against `expected_chronicle_head`. A changed or missing request, an Event-body
Sigil mismatch, a different subject, purpose, payload Actor, outer Chronicle
Actor, or an Event at another Head fails closed.

The paired `receipt/1.1` is resolved by exact Receipt ID and Sigil. It binds the
canonical Event only through `event_id` and `event_body_sigil`, and the ordinary
RFC-0001 equalities for `previous_receipt_sigil` and `accepted_at` must also
hold. The Receipt Schema contains no purpose, subject ID, subject Sigil,
transition-request ID, or final Specification Sigil. Purpose and subject are
proved only by the verified chain:

```text
receipt/1.1
  -> chronicle-event/1.1 execution.approval.granted
  -> execution-approval-transition-request/1.0
  -> execution-approval-subject/1.0
```

After that complete chain validates, Ward inserts only the exact Receipt ID and
Sigil, recomputes the pre-approval digest from the now-final object using the
three-field omission rule, requires equality with the resolved request
subject's `preapproval_specification_sigil`, and then computes
`specification_sigil` over every other final member. Thus the final
Specification binds the Receipt, the Receipt binds the Event, and the Event
resolves the request and pre-approval subject without a digest cycle. A
different candidate, subject, request, Event, Receipt, or final binding
requires a fresh subject, request, and canonical approval.

### Capability, Task, and Execution Specification comparison

Ward performs this algorithm before it signs an RFC-0012 Execution
Specification. It is deterministic and fail-closed:

1. Validate the Registry, every embedded Contract, their self-Sigils,
   ordering, revision linkage, and timestamp relations. Resolve the Task's
   exact Registry binding; no newer Registry may be substituted.
2. Validate the Circle and Task Capsule self-Sigils. Resolve the Capability
   map key and require exact Capability ID, version, and Contract Sigil.
   Resolve the Snapshot and every visible object by exact ID, type, and Sigil.
3. Compare every authority-bearing Circle member to the matching Capability
   member. `circle_id` and `circle_sigil` are immutable identity, not authority
   values and have no Capability counterpart. A broader Task is invalid; Ward
   does not silently trim it. After this check, the Capability intersection
   with the Task is exactly the Task authority.
4. Resolve every RFC-0012 field from that intersection. The Specification may
   make a further explicit narrowing, but every changed value participates in
   a new pre-approval subject when approval is required and in the final
   `specification_sigil`.
5. Reject an absent, unknown, duplicate, unordered, null, unresolved, or
   unmappable authority. There is no default, ambient fallback, or
   best-effort policy.

The comparison primitives are exact. An allowed set may only become a subset
under its stated semantic relation. A numeric permission or budget may only
decrease. There is no global boolean ordering: a boolean not named below must
remain exact. `process_group_signals` and `dynamic_loading` may change only
from `true` to `false`; environment `required`, each
`IdentityRequirements` member, and side-effect `requires_approval` may change
only from `false` to `true`; the two Input identity requirements remain
constant `true`; and derived `external_side_effects_retry_safe` is recomputed
rather than compared as an authority bit. `DENY` dominates every allow branch,
and a Task or Specification may not replace a Capability denial with a
non-empty set or non-zero ceiling. An identity, version, Schema ID, and Sigil
must match byte-for-byte; a semantically similar object or newer version is
not a substitute. Null never grants authority.

The field-by-field resolution into `execution-specification/1.0` is:

| Capability and Task source | RFC-0012 destination and exact narrowing rule |
| --- | --- |
| Resolver-owned envelope | `schema_version` is constant `execution-specification/1.0`; `specification_id` is a new Execution Specification ID; `created_at` is a normalized creation time; `conformance_policy_version` is constant `sanctum-authority-intersection/1.0`; and `specification_sigil` covers every other RFC-0012 member. None conveys execution authority. |
| Task identity and self-Sigil | `task_binding`; exact Task ID and Capsule Sigil. |
| Capability identity, version, and self-Sigil | `capability_binding`; exact tuple from the bound Registry value. |
| Snapshot identity and Sigil | `snapshot_binding`; exact tuple. |
| Ward and Task approval requirement | `authorization`; exact Ward decision binding, exact requirement, and Receipt fields present only for `REQUIRED`. The Ward decision binds the Registry tuple, complete resolved permission set, assurance tuple, and approval-policy tuple. A required Receipt resolves its exact `execution.approval.granted` Event, transition request, and `ExecutionApprovalSubject`; that subject's recomputed pre-approval digest matches the final Specification after omitting exactly `specification_sigil`, `approval_receipt_id`, and `approval_receipt_sigil`. |
| Filesystem Circle | `policies.filesystem`; grants are matched by unique grant ID, root kind is exact, operation sets are subsets, byte and entry ceilings do not increase, and a descendant prefix is valid only when checked arithmetic proves `delta + child.maximum_depth <= parent.maximum_depth`. |
| Tool and executable Circle | `policies.executable`; each resolved rule carries the exact tool or executable IDs, versions, Sigils, runtime tuple, argument-Schema tuple, entrypoint, and side-effect ID. Sets and invocation or start ceilings only decrease. No tool authority remains only in an objective string. |
| Process Circle | `policies.process`; `DENY` dominates, child executable IDs are a subset, numeric ceilings decrease, and either boolean can change only from true to false. |
| Network Circle | `policies.network`; `DENY` dominates; destination ID, protocol, host, address-policy Sigil, redirect policy, and side-effect ID remain exact; the destination set is a subset and each selected destination's port set is an explicit subset of its matching parent port set; all three ceilings decrease. |
| Environment Circle | `policies.environment`; inheritance remains `NONE`; variable names are a subset and source kind, binding ID, and source Sigil are exact. `required` may change only from false to true. |
| Credential Circle | `policies.credential`; ambient credentials remain false and exposure remains `NEVER`; handle IDs are a subset, class, scope Sigil, and side-effect ID are exact, and use ceilings decrease. |
| Resource Circle | `policies.resource`, `attempt_budget`, and `job_budget`; every counter is no greater than both parents, a denied facility has zero, and `job_budget.attempts` exactly equals resolved retry `max_attempts`. Open-file, file-count, and thread rules remain in the closed resource policy. |
| Visible inputs and input Circle | `policies.input`; each input has the exact Snapshot object identity and Sigil, mount path, media type, and equal-or-lower byte ceiling. Count and aggregate ceilings decrease. Immutable identity and content-Sigil requirements remain true. |
| Expected outputs and output Circle | `policies.output` and `output_contracts`; the ordered output array is exact or an explicit subset, identities and side-effect IDs are exact, count and byte ceilings decrease, and each path rule is equal or narrower. |
| Runtime Circle | `runtime_constraints`; runtime and backend identities and Host constraints are subsets with exact versions and Sigils. A true identity requirement cannot become false. |
| Lifecycle deadlines | `deadline_policy`; each of the eight integer values is no greater than both Capability and Task maxima and retains all deadline cross-field relations. |
| Lifecycle result rule | `result_requirement`; `successful_worker_outcome` is constant `COMPLETED`. The selected mode must occur in the intersection of the two admitted-mode expansions defined above; `REQUIRED` and `FORBIDDEN` are each narrower than `OPTIONAL` but are incomparable with one another. |
| Lifecycle retry rule | `retry_policy`; attempts and backoff values do not increase, terminal-reason and enum choices are subsets, and the selected backoff and resume values obey their closed RFC-0012 branches. |
| Lifecycle logging rule | `logging_policy`; all five byte ceilings decrease, aggregate is no greater than their sum, and overflow behavior is selected from both allowed sets. |
| Lifecycle post-terminal rule | `post_terminal_derivation`; `NONE` grants nothing. `CODE_MODIFICATION` is valid only when allowed by both parents, uses an exact immutable Base identity and Sigil from a visible Snapshot input, selects an exact permitted retention-policy tuple and source profile, and decreases all file, byte, and execution-owned-hold lifetime ceilings. The selected duration is never an RFC-0013 minimum physical-retention duration. |
| Requested assurance | `assurance_requirement`; the five-member profile and suite tuple is copied exactly. The selected profile entry must reproduce the Task's ten ordered control requirements and the installed suite must cover them; no level, profile, suite, Sigil, state, or evidence-profile substitution is allowed. |
| Side-effect Circle | The relevant resolved tool, executable, network, credential, and output rules retain exact side-effect IDs, kinds, authority Sigils, retry modes, approval bits, and conditional idempotency-scope Sigils. Grants form a unique-key subset and invocation ceilings decrease. `NO_RETRY` is narrower than either retrying mode; `SAME_IDEMPOTENCY_KEY` and `NEW_AUTHORIZATION_EACH_ATTEMPT` may only remain exact and are incomparable; `requires_approval` may change only from false to true. The latter retry mode derives the exact immutable `AttemptAuthorizationRequirement` carried by every RFC-0012 Attempt. No side-effect authority may be left without an RFC-0012 policy or Attempt carrier. |

Every RFC-0012 resolved policy has exactly `policy_id`, `policy_version`,
`policy_sigil`, and the policy-specific closed rules above. Its Sigil covers
that complete resolved object except the Sigil member, using the same
canonical encoding and self-Sigil algorithm as these contracts. Policy IDs are
`UpperId(POL)` and policy versions are `Version`; together they identify the
deterministic resolver and rule format but never replace the field
comparison. A policy with an unknown rule, omitted denial, unbound side-effect
reference, or rule not representable by RFC-0012 is rejected rather than
approximated.

For retry, `external_side_effects_retry_safe` is true exactly when at least
one selected non-`READ_ONLY` effect exists, every such effect uses
`SAME_IDEMPOTENCY_KEY`, the Specification binds the exact non-null
idempotency-scope Sigil into each carrying policy, and its invocation and Job
ceilings permit the selected attempt count. It is false when there is no
external write or when any selected effect uses `NO_RETRY` or
`NEW_AUTHORIZATION_EACH_ATTEMPT`. A selected non-`READ_ONLY` `NO_RETRY`
effect requires resolved `max_attempts` equal to one. A selected
`NEW_AUTHORIZATION_EACH_ATTEMPT` effect permits a greater value only through
the per-Attempt binding below. `SINGLE_USE_EXTERNAL` is never made retry-safe
by a boolean.

### Per-Attempt authorization carrier requirement

`NEW_AUTHORIZATION_EACH_ATTEMPT` requires a new, immutable authorization after
each Attempt binding exists and before that Attempt can preflight, acquire a
Lease, launch, or receive any side-effect handle. This requirement applies to
the first Attempt as well as every retry. It is distinct from the
Specification-level approval Receipt and never changes the immutable
Specification.

The RFC-0011-side source contract for the RFC-0012 carrier is:

```text
AttemptAuthorizationEffect:
  side_effect_id: UpperId(SE)
  authority_sigil: Sigil

AttemptAuthorizationRequirement is exactly one of:
  NONE:
    kind = NONE
    effects = Set<AttemptAuthorizationEffect, 0, 0, side_effect_id>
  REQUIRED:
    kind = REQUIRED
    effects =
      Set<AttemptAuthorizationEffect, 1, 128, side_effect_id>

AttemptAuthorizationSubject:
  schema_version = attempt-authorization-subject/1.0
  authorization_subject_id: UpperId(AA)
  job_id: RFC-0012 Job ID
  job_binding_sigil: Sigil
  attempt_id: RFC-0012 Attempt ID
  attempt_binding_sigil: Sigil
  retry_ordinal: PositiveU63
  specification_id: RFC-0012 Specification ID
  specification_sigil: Sigil
  effects:
    Set<AttemptAuthorizationEffect, 1, 128, side_effect_id>
  authorization_subject_sigil: Sigil

AttemptAuthorizationBinding:
  authorization_subject_id: UpperId(AA)
  authorization_subject_sigil: Sigil
  authorization_transition_request_id: RFC-0012 AAT-ID
  authorization_transition_request_sigil: Sigil
  authorization_event_id: Chronicle Event ID
  authorization_event_body_sigil: Sigil
  authorization_receipt_id: UpperId(RC)
  authorization_receipt_sigil: Sigil
  authorization_binding_sigil: Sigil

AttemptAuthorizationState is exactly one of:
  NONE:
    kind = NONE
  PENDING:
    kind = PENDING
  BOUND:
    kind = BOUND
    authorization_subject: AttemptAuthorizationSubject
    attempt_authorization_binding: AttemptAuthorizationBinding
```

The subject and binding are closed objects. Their respective self-Sigils omit
only `authorization_subject_sigil` and `authorization_binding_sigil`.
`AttemptAuthorizationRequirement.effects` is derived exactly from the
resolved carrying policies: it contains every and only selected side effect
whose retry mode is `NEW_AUTHORIZATION_EACH_ATTEMPT`, with the exact
`authority_sigil`. A non-empty derived set selects `REQUIRED`; an empty set
selects `NONE`.

RFC-0012 must carry the requirement as an immutable required member of
`execution-attempt/1.0`, covered by `attempt_binding_sigil`.
`job.attempt_allocated` initializes the replayed authorization state to
`PENDING` for `REQUIRED` and `NONE` otherwise. A new
`attempt.authorization_bound` event is lifecycle-state-neutral, advances the
owning Attempt revision, changes only the orthogonal authorization projection
`PENDING -> BOUND`, and has exact payload members `authorization_subject` and
`attempt_authorization_binding`; the event and projection retain both complete
closed objects. The binding's subject ID and Sigil equal the embedded subject
byte-for-byte. No other event may assign or replace that binding.

The authorization Receipt resolves by exact ID and Sigil and binds only its
`authorization_event_id` and `authorization_event_body_sigil` through the
standard `receipt/1.1` fields. That canonical Event must have type
`attempt.authorization.granted` and must resolve the exact RFC-0012
`attempt-authorization-transition-request/1.0` by the two request fields in
the binding. The request carries purpose `ATTEMPT_AUTHORIZATION` and resolves
the complete embedded subject. A Receipt itself contains neither that purpose
nor any subject field. The subject's Job, Attempt, retry ordinal, and
Specification ID/Sigil must be byte-for-byte equal to the allocated Attempt
and its immutable parents. Its effect set must equal both the immutable
Attempt requirement and the selected carrying-policy projection. Each
authority named by `authority_sigil` must validate the same request and subject
chain before the operational `attempt.authorization_bound` event can commit.

An authorization-subject ID or Sigil, transition-request ID or Sigil,
canonical Event ID or body Sigil, Receipt ID or Sigil, or
authorization-binding Sigil used by one Attempt is ineligible for every other
Attempt, including another Attempt of the same Job. An Attempt authorization
Receipt is also distinct from and may not reuse the Specification-level
approval Receipt. A subject, request, Event, or Receipt may commit at most
once, and `BOUND` is single-assignment. Retry therefore requires fresh subject,
request, Event, and Receipt identities after the new Attempt binding exists;
copying, rebinding, widening, or replaying a predecessor's authorization fails
closed.
A missing or invalid binding permits only the closed rejection or stop path
and never preflight, Lease authority, launch, or handle issuance. An RFC-0012
implementation that lacks any field, state, or event above must reject
`NEW_AUTHORIZATION_EACH_ATTEMPT` rather than treating the
Specification-level approval as its substitute.

If approval is `REQUIRED`, RFC-0012 `authorization` contains both Receipt
fields, and Ward resolves the exact Receipt -> `execution.approval.granted`
Event -> transition request -> `ExecutionApprovalSubject` chain. The subject
binds the Registry, Capability, Task, Snapshot, Circle, Ward decision,
assurance profile and suite tuple, approval-policy tuple, complete resolved
permission set, and `preapproval_specification_sigil`; it deliberately does
not bind the final `specification_sigil`. If approval is `NOT_REQUIRED`, both
Receipt fields are absent and no approval subject, request, or Event is
inferred. A narrower Specification changes the pre-approval digest and never
reuses the old subject, request, Event, or Receipt.

## Terminology

| Term | Meaning in Phase 3 |
| --- | --- |
| **Task Capsule** | Immutable control-plane statement of one objective, pinned Capability, Research Snapshot, expected outputs, and declared Circle. Executor launch requires the Phase 3 v2 contract. |
| **Execution Specification** | Immutable, versioned, identity-bound resolution of one Task into enforceable runtime requirements. It can narrow but never broaden the authorized Task. |
| **Sanctum** | Logical per-Attempt Agent context containing only the objective, visible inputs, tools, budget, policy, and output contract granted to that Attempt. |
| **Circle** | Per-Task permission and context boundary. Its declaration is policy input; its realized controls and evidence determine the actual assurance claim. |
| **Ward** | Control-plane policy authority that validates the Task and Execution Specification before launch and rechecks applicable postconditions before result acceptance. |
| **Executor** | Coordinator that persists operational state, selects an eligible backend and Worker, issues Leases, supervises Attempts, and transports bounded results. |
| **Job** | Operational execution request bound to exactly one Task Capsule and Execution Specification. A Job is not a scientific Run. |
| **Attempt** | One execution try for a Job. Retry creates a new Attempt identity and never rewrites the preceding Attempt. |
| **Lease** | Time-bounded, fenced authority for one Worker to act on one Attempt. Detailed semantics belong to RFC-0012. |
| **Worker** | Untrusted or partially trusted runtime subject that performs one Attempt. It has no canonical authority. |
| **Crucible** | Mutable workspace materialized for an Attempt. It is an execution resource, not a canonical Artifact and not the Sanctum itself. |
| **Proposal** | Bounded output that may be submitted to Athanor. Process exit code, Job completion, or output existence does not imply acceptance. |
| **Scientific Run** | Immutable terminal research observation accepted under the Run contract. It is distinct from Job and Attempt lifecycle state. |

A retry receives a fresh Sanctum instance. A Crucible is materialized fresh by
default. A1 or higher may resume only from an immutable base plus an explicit
resume content identity after recovery validation proves that the preceding
process tree and handles are fenced, the materialization is intact, and the
new Attempt has exclusive access. An implementation may not infer continuity
or exclusivity from a path.

## Ownership and authority

| Component | Owns | Must not |
| --- | --- | --- |
| Researcher or interactive Host | Task intent, requested operation, required human confirmations | Infer that approval or execution success is a scientific Seal |
| MCP control surface | Typed requests that submit an already resolved Job to the Executor, observe or cancel it, and submit bounded results | Interpret or run Worker commands, or expose a universal shell, filesystem, Git, web, or arbitrary-execution escape hatch |
| Ward | Contract comparison, approval binding, policy resolution, launch decision, applicable postcondition checks | Execute Worker code or grant authority beyond the pinned contracts |
| Executor | Job, Attempt, Lease, Worker, backend, cancellation, timeout, logs, and recovery state | Append Chronicle events, edit canonical projections, or manufacture missing provenance |
| Enforcement backend | Realize and report the controls supported by its declared assurance profile | Self-upgrade an assurance claim because it uses a named technology such as a container |
| Worker | Perform the bounded Attempt and return declared outputs | Change its policy, Lease, audit record, assurance claim, or canonical state |
| Athanor | Validate Proposals, enforce scientific Gates, append accepted events, issue Receipts | Treat Executor success as sufficient scientific evidence |
| Chronicle | Preserve accepted research events and reconstruct canonical research state | Act as the queue or heartbeat store for live execution |

The trusted computing base for canonical integrity contains Athanor, Chronicle
verification, Schema validation, and Ward. The operational trusted computing
base for A2 assurance additionally contains the Executor coordinator,
execution journal implementation, enforcement backend, Host kernel, and
assurance-evidence verifier. Compromise of any of those components can
invalidate the operational claim. Worker code, Task inputs, repository content,
Provider output, generated patches, and mutable Crucibles are untrusted.

This is an authority boundary, not a new cryptographic defense for local
storage. The current unsigned Chronicle does not protect against a malicious
same-user process that can rewrite the ledger, Head, and Receipts together.
At A2, the Worker cannot reach that storage; protecting it from a compromised
Executor, control plane, or Host administrator remains outside this RFC.

Human approval authorizes a particular bound operation. It does not make its
code, data, Worker, Provider, or outputs trustworthy.

## Operational and canonical state

Phase 3 uses two distinct authorities:

- Chronicle is the source of canonical research state.
- A durable execution journal is the source of operational Job state.

The execution journal is authoritative for scheduling and recovery but has no
scientific authority. Its format, locking, and replay rules are defined by
RFC-0012.

| State | Classification | Transition authority |
| --- | --- | --- |
| Research Program, Evidence, Claim, Protocol, Experiment, scientific Run, Assessment, Decision, registered Artifact | canonical research state | Athanor and Chronicle |
| Human approval Receipt | canonical authorization evidence | Athanor and Chronicle |
| Task Capsule, Snapshot, and Execution Specification | immutable pinned control records | Their versioned control-plane stores and validators |
| Job, Attempt, Lease, Worker, queue position, heartbeat, cancellation request, exit status, resource sample | durable operational state | Executor |
| Crucible files, temporary outputs, stdout, and stderr | mutable or captured execution material | Enforcement backend and Executor |
| Agent Result, execution result, patch, candidate Run, candidate Artifact | Proposal | Worker or Executor until Athanor accepts a defined transition |

Job scheduling, heartbeat, retry, cancellation, timeout, and terminal events do
not enter Chronicle merely because they occurred. An accepted Proposal may
carry Job and Attempt identities and Sigils as provenance. Logs or outputs
become canonical Artifacts only through an explicit Artifact registration and
Receipt.

Operational records are never overwritten to hide failure. Failed, cancelled,
expired, fenced, policy-violating, and lost Attempts remain in the execution
journal. Retrying appends a new Attempt. A retention or archival operation must
be explicit, auditable, and preserve terminal summaries and content identities;
the Phase 3 reference runtime retains all terminal records by default.

A terminal Job does not create or update a scientific Run. If execution
produces a candidate Run, Athanor separately validates its Program, Protocol,
Experiment, phase, terminal status, metrics, Artifacts, and analysis
disposition. This preserves failed and negative scientific Runs without
conflating them with infrastructure failure.

## Authorization and execution boundary

Before every Attempt, the control and execution planes must:

1. load and verify the exact Task Capsule, Capsule Sigil, Snapshot, Capability
   Contract, and Execution Specification;
2. require Ward to return `PASS` for the complete bound policy and require any
   approval Receipt to match that policy;
3. verify Snapshot integrity and freshness at launch;
4. select a backend whose verified profile meets the requested minimum
   assurance and every required control;
5. materialize only declared inputs into a fresh or explicitly resumed
   Crucible;
6. record the backend identity, policy Sigil, input identities, requested
   assurance, planned control profile, and preflight eligibility before Worker
   code starts; and
7. acquire a valid fenced Lease for the Attempt.

An unsupported control, unknown policy field, failed preflight, missing
approval, stale Snapshot, or unmet assurance requirement rejects launch.
Benchwork does not silently relax policy, downgrade assurance, or ask the
Worker to enforce its own boundary.

During execution:

- policy enforcement and audit state remain outside the Worker;
- the Execution Specification never grants direct `.benchwork/` access;
- credentials and unrelated Host environment variables are absent by default;
- the Executor bounds runtime, captured output, and result transport;
- cancellation and Lease expiry fence later Worker output and begin resource
  revocation; and
- every detected control violation is recorded.

At A0 and A1, these rules limit what Benchwork grants but do not claim
containment against a hostile Worker that discovers ambient Host paths. At A2
or higher, the backend must make the entire `.benchwork/` tree unreachable.
Required research inputs are exported as explicitly selected, immutable,
Sigil-bound materializations rather than mounting canonical or operational
control-plane storage. Other undeclared Host paths and credentials are also
unreachable.

At A2 or higher, result fencing alone is insufficient. Cancellation, Lease
loss, or policy revocation must terminate the complete process tree and revoke
the Attempt's filesystem, network, credential, and output handles. A mutable
sink that cannot revoke a handle must validate the current fencing token on
every side-effecting operation. A replacement Attempt cannot receive the same
mutable Crucible, output namespace, or external sink until the preceding
Attempt is confirmed terminated or the resource is quarantined.

At A2 or higher, a violation of an isolation, resource, credential, or
side-effect boundary terminates the complete process tree, revokes its handles,
and makes the result ineligible. A non-security output-format or result-Schema
failure may invalidate the result without an additional kill after Worker
execution has already ended.

On completion, the Executor records terminal evidence before offering a
bounded Proposal. Only after terminal state, process-tree termination, cleanup,
and required postconditions are verified may the evidence verifier issue an
immutable realized assurance claim. Athanor then revalidates the Capsule and
Capability Sigils, Execution Specification Sigil, Snapshot freshness, expected
output Schemas, Blob Sigils, Ward decision, Job and Attempt identity, terminal
Lease eligibility, realized-claim Sigil, assurance profile and conformance
suite, realized level against the requested minimum, and runtime provenance. A
stale, duplicate, late, fenced, malformed, under-assured, or policy-violating
result is preserved as operational evidence but rejected for scientific
acceptance.

## Assurance model

`sanctum-assurance-profile/1.0` defines the Phase 3 assurance vocabulary.
Before launch, an Attempt records `requested_assurance` and a preflight
eligibility decision. Neither is an assurance claim. A realized assurance claim
may be issued only after terminal and cleanup evidence exists. It is
per-Attempt, not a product-wide label, and binds the profile version and Sigil,
level, backend identity and version, Host platform, policy and
backend-configuration Sigils, conformance-suite identity and Sigil, and
retained evidence Sigil. An incomplete, crashed, or unverifiable Attempt has no
realized claim at the requested level; Benchwork records the missing evidence
and does not silently downgrade it. Unknown profiles, versions, or suite
identities fail closed. The levels are cumulative minimums:

| Level | Name | Minimum meaning |
| --- | --- | --- |
| `SANCTUM-A0` | Declared Attempt | A Phase 3 Job and Attempt exist and Ward validated their pinned policy, but the Attempt has no execution-plane enforcement claim. Phase 2 native-Host activity is outside this assurance model, not A0, because it has no Attempt evidence. |
| `SANCTUM-A1` | Supervised | An exclusive Crucible materialized from a pinned fresh or validated resume identity, constructed allowlisted environment, tracked process group, supervisor-enforced wall-time and cancellation, bounded log and output capture, exact runtime/input/output identities, and durable terminal and cleanup evidence are all present. The workload is assumed cooperative. This level is not a security sandbox. |
| `SANCTUM-A2` | Isolated | A1 plus enforcement outside the Worker for deny-by-default filesystem scope, network policy, process containment, resource ceilings, secret non-inheritance, and controlled output paths. It is intended to contain untrusted non-privileged user-space code under a stated Host threat model. |
| `SANCTUM-A3` | Reserved: Attested | Reserved for a later remote-trust RFC. Phase 3 defines no claimable A3 profile or conformance path. |

Every A1 requirement in the table is mandatory. A Host that cannot enforce
wall time and cancellation for the tracked cooperative process group, construct
the required environment, bound capture, or retain the required identities and
terminal evidence may claim only A0. Implementations cannot interpret
"supervised" as "whatever this Host happens to support."

Each Attempt also records a control matrix for at least:

- filesystem reads and writes;
- network ingress and egress;
- process creation and executable selection;
- CPU, memory, storage, and wall time;
- environment variables, credentials, and secret material;
- log and output capture;
- runtime and input identity; and
- cancellation, fencing, and cleanup.

Each dimension reports `ENFORCED`, `VERIFIED`, `OBSERVED`, or `UNAVAILABLE`,
with backend-specific evidence. For A1 or higher, a level may be claimed only
when its required policy controls are `ENFORCED` and its identity or evidence
requirements are `VERIFIED`. A0 has no enforcement minimum; it requires
verified Task, policy, Job, Attempt, and Ward identities and reports execution
controls at their actual `ENFORCED`, `VERIFIED`, `OBSERVED`, or `UNAVAILABLE`
state. Partial enforcement remains visible but cannot aggregate into A1 unless
every A1 requirement is satisfied. `OBSERVED` is diagnostic evidence, not
policy enforcement. Missing or unknown evidence fails the requested claim
closed.

Subprocesses, virtual environments, containers, worktrees, namespaces, virtual
machines, and remote sandboxes are mechanisms, not assurance levels. No
mechanism earns a level by name. The backend must pass the conformance suite in
the exact supported configuration.

The `0.4` local reference runtime must provide at least `SANCTUM-A1` and label
it experimental. It may claim `SANCTUM-A2` only on a declared backend and Host
combination that passes the A2 adversarial conformance profile. An A1-only
runtime must be described as supervised execution, not isolated or sandboxed
execution. It may not claim A3. Production-grade isolation remains a Phase 4
gate.

## Threat model

### Assets

The model protects:

- Chronicle, Receipts, Seals, projections, and other `.benchwork/` state;
- the exact Task, policy, inputs, runtime identity, outputs, and provenance;
- Host files, credentials, processes, and network access outside the Circle;
- completeness of terminal Job and Attempt history, including failures; and
- the distinction between operational evidence, Proposals, and accepted
  scientific state.

### Adversaries and failures

The design treats repository content, input data, generated code, Provider
output, Plugin content, and Worker code as potentially malformed or malicious.
A0 and A1 do not claim to contain a malicious Worker; A2 is the first level
whose threat model includes hostile non-privileged user-space code. A1
conformance therefore tests a cooperative workload, while A2 conformance uses
adversarial workloads. The model also covers non-malicious crashes, duplicate
delivery, out-of-order messages, stale snapshots, lost heartbeats, expired
Leases, partial writes, disk exhaustion, process trees that outlive a parent,
and Host restart.

Required adversarial cases include:

- path traversal, absolute paths, symlink or hard-link escape, and special
  files;
- writes to `.benchwork/`, undeclared paths, or immutable inputs;
- undeclared network egress, loopback access, and inherited proxy settings;
- credential or Host-environment inheritance;
- fork, subprocess, daemon, and orphan-process escape;
- CPU, memory, storage, time, log, file-count, and output-size exhaustion;
- forged backend identity, policy evidence, logs, exit status, or output
  Sigils;
- Lease replay, split-brain Workers, late results, and duplicate completion;
- stale Capsule, Capability, Snapshot, Crucible base, or patch identity; and
- attempts to turn Job success directly into a Run, Artifact, Assessment,
  Decision, or Seal.

### Trust limits

`SANCTUM-A2` does not claim protection from a compromised kernel, hypervisor,
Benchwork control plane, Executor coordinator, execution journal,
assurance-evidence verifier, enforcement backend, malicious same-user local
writer, or Host administrator. A3 does not define confidential computing or
protection from a malicious remote operator; those claims require a separate
RFC and evidence model.

Availability against an administrator, physical attacker, or infrastructure
operator is outside Phase 3. Scientific validity is also outside the sandbox
claim: isolation can preserve execution boundaries and provenance, but it
cannot establish that a method, measurement, or interpretation is correct.

## Failure and recovery principles

- Every Job and Attempt has a unique identity. Retry never reuses an Attempt
  identity.
- Only the current unexpired fenced Lease may produce an eligible result.
- At A2 or higher, Lease loss, cancellation, and policy revocation also revoke
  side-effecting handles and terminate the complete process tree. Fencing only
  the returned result is insufficient.
- A replacement Attempt cannot share a mutable resource with an unfenced
  predecessor. The predecessor must be confirmed terminated, or the resource
  must be quarantined and rematerialized under a new identity.
- Cancellation, timeout, policy violation, and Worker loss are distinct
  terminal evidence and are not rewritten as generic failure.
- Executor restart reconstructs Job state from the durable execution journal,
  not from conversation, process names, or Crucible directory names.
- Ambiguous ownership after restart fences the old Worker before another
  Attempt can become eligible.
- Output publication is atomic with respect to its recorded content identity.
  Partial outputs remain quarantined and ineligible.
- Cleanup failure is retained as a policy or infrastructure failure even when
  Worker computation succeeded.
- Loss or corruption of required provenance prevents assurance and result
  acceptance; Benchwork never reconstructs it from best guesses.

RFC-0012 defines the exact states, fencing tokens, heartbeat and renewal
rules, terminal precedence, and crash-recovery algorithm.

## Invariants

- Athanor remains the only authority for canonical transitions.
- Chronicle remains the source of canonical research state.
- An Executor, Worker, backend, Job, Attempt, or successful process has no
  scientific authority.
- Job, Attempt, and Lease state remains separate from immutable scientific Run
  state.
- A Ward `PASS` is authorization, not proof of enforcement.
- A realized assurance claim is issued only after terminal and cleanup
  verification and binds one Attempt, a versioned profile and
  conformance-suite Sigil, and retained enforcement evidence.
- A Phase 3 execution policy may narrow but never broaden its pinned Task and
  Capability contracts.
- Existing versioned Phase 2 identifiers keep their accepted meanings.
- Human confirmation remains mandatory for Research Question, Protocol, and
  Decision Seals.
- Failed and negative operational and scientific outcomes are preserved in
  their respective records.
- MCP remains typed and bounded and gains no general execution escape hatch.
- The Worker cannot access `.benchwork/`, or write its policy, Lease, or audit
  record, at A2 or higher.
- Unknown fields, controls, backends, evidence formats, and assurance versions
  fail closed.

## Compatibility and migration

This RFC extends RFC-0007's reserved Executor boundary and preserves RFC-0002,
RFC-0005, and RFC-0008. It amends RFC-0009 only by allowing MCP to submit,
observe, and cancel a typed Job through the future RFC-0015 API. MCP still does
not interpret or run a command, edit a repository, perform Git or web actions,
or invoke a Provider.

No Phase 2 Schema is changed in place. In particular:

- `task-capsule/1.1.circle.tools`, `network`, and
  `time_budget_seconds` retain their declarative meanings;
- `agent-result/1.1` remains a proposal contract and receives no inferred
  execution authority;
- `run/1.1` and `run/1.2` retain terminal scientific statuses only;
- `artifact/1.0` remains a logical canonical record rather than a physical
  Blob or Replica contract; and
- current Codex and Claude Code native-tool workflows remain valid but are
  outside the Sanctum assurance model unless a Phase 3 Job and Attempt wrap the
  activity.

Phase 3 adds independent versioned execution Schemas, including
`capability-registry/2.0`, `capability-contract/2.0`, and
`task-capsule/2.0`. Registry v1.1 never stores a v2 Contract. Importing a
Capability into Registry v2 is an explicit validation and registration
operation that creates a new Contract Sigil; it does not mutate the v1
Registry or carry approvals forward.

Existing v1 Task Capsules are never launched by the Executor. A researcher may
explicitly create a new v2 Task from the same objective and Snapshot, but
permissions absent from v1 must be selected and approved explicitly. There is
no automatic or lossy Task migration, and no migration from Host conversation
history or native tool activity into Job or Attempt records.

An accepted Phase 3 result may require a new Agent Result or provenance
version. It must not encode Job semantics into an existing field with a new
meaning. Any breaking Alpha change requires an accepted RFC, migration
guidance, and replay or contract coverage.

## Relationship to later RFCs

- RFC-0012 defines Job, Attempt, Lease, Worker, logs, terminal states, retry,
  fencing, and recovery.
- RFC-0013 defines logical Artifact, Blob, Replica, transfer integrity,
  retention, and storage backend boundaries.
- RFC-0014 defines Crucible base identity, Patch Proposal, validation,
  conflict handling, and explicit human promotion.
- RFC-0015 defines typed start, observe, cancel, and result operations over the
  accepted execution contracts.

Those RFCs may refine implementation details but may not weaken this RFC's
ownership, authority, state-separation, or assurance invariants without
explicitly superseding it.

## Security and integrity

Execution metadata, policies, inputs, outputs, logs, and backend evidence are
untrusted until their Schemas, identities, bounds, and relationships validate.
Policy and result transport must be length-bounded and reject ambiguous
encoding, unknown fields, path escapes, and identity mismatches.

The control plane passes capabilities, not ambient Host authority. Worker
processes receive a constructed environment and explicit handles rather than
the launching Host's complete environment. A1 removes ambient credentials and
unrelated environment variables from the launched process but does not claim
hostile-code containment. At A2 or higher, the backend enforces that the Host
home directory, credential stores, ambient Host IPC or control sockets,
inherited Agent sockets, and the complete `.benchwork/` tree are absent.
Network sockets created by the backend may exist only as allowed by the bound
network policy. Selected research state is copied into the Sanctum only through
a bounded export that records its Schema and Sigil.

At A2 or higher, enforcement occurs outside the Worker and remains effective
for its complete process tree. Preflight success alone is insufficient:
postconditions must verify termination, output boundaries, and cleanup. Any
detected escape or unverifiable cleanup prevents a realized claim at the
requested level and invalidates result eligibility.

Secrets are denied by default. Phase 3 does not define a secret broker.
Redacting a secret after capture is not equivalent to preventing disclosure.

## Alternatives

- **Put execution inside Athanor.** Rejected because mutable, fallible runtime
  coordination would enlarge the canonical transition authority and couple
  Chronicle integrity to process control.
- **Treat Job as an in-progress Run.** Rejected because queue and retry state
  are operational, while a Run is an immutable terminal scientific
  observation.
- **Add a generic MCP shell or filesystem tool.** Rejected because it erases
  typed permission boundaries and creates a universal escape hatch.
- **Execute `task-capsule/1.1` directly.** Rejected because its accepted Circle
  is declarative and cannot express the enforcement, identity, resource, and
  evidence requirements of Phase 3. Phase 3 uses explicit v2 Capability and
  Task contracts instead.
- **Equate a container or worktree with isolation.** Rejected because a
  mechanism name says nothing about mounts, network, credentials, resources,
  process containment, or the tested threat model.
- **Write every heartbeat and retry into Chronicle.** Rejected because
  operational churn is not canonical scientific state and would make replay
  depend on runtime scheduling.
- **Automatically register successful outputs.** Rejected because execution
  completion cannot replace Athanor validation or human scientific authority.

## Non-goals

- automatic Provider invocation or model routing;
- remote Workers, cluster scheduling, Slurm, Kubernetes, or broad GPU support;
- production-grade isolation or a claim against kernel or administrator
  compromise;
- physical Artifact storage, replication, or garbage collection;
- Patch application, merge, or promotion;
- a secret-management or credential-brokering system;
- automatic creation of Runs, Artifacts, Assessments, Decisions, or Seals;
- changing Phase 2 Host symmetry or native-tool workflows; and
- defining the detailed protocols reserved for RFC-0012 through RFC-0015.

## Acceptance tests

Acceptance of the Phase 3 execution model requires the five executable
Schemas owned by this RFC plus the dependent Schemas, examples, threat-model
review, and conformance tests supplied by RFC-0012 through RFC-0015. The
combined suite must demonstrate:

1. existing Phase 2 fixtures retain their accepted meanings and no v1 Schema
   is reinterpreted;
2. Registry v1.1 rejects v2 Contracts, v1 Task Capsules are ineligible for
   Executor launch, Registry v2 rejects abbreviated or v1 values, duplicate or
   unordered Capability IDs, key/ID mismatches, invalid embedded or self
   Sigils, and every fixture proves field-by-field that an Execution
   Specification cannot broaden its v2 Task, Capability, approval, Snapshot,
   expected outputs, or any Circle dimension;
3. Phase 2 approvals never authorize v2 Tasks, and any change to an approved
   Execution Specification, assurance-profile ID, version or Sigil, or
   permitted conformance-suite identity or Sigil requires a new exact-match
   approval;
4. launch records requested assurance and preflight eligibility but no realized
   claim; a realized claim appears only after terminal and cleanup evidence is
   immutable;
5. unknown controls, assurance profiles, profile or conformance-suite Sigils,
   unmet assurance, missing evidence, and implicit downgrades fail before
   launch or prevent the requested realized claim;
6. A0 is claimed only for a recorded Phase 3 Attempt, every A1 mandatory
   control passes cooperative conformance, and A1 cannot claim A2;
7. fresh and resumed A1 Crucibles are exclusive, content-identified, and
   recovery-validated before launch;
8. each A2 backend makes `.benchwork/` unreachable and denies path escape,
   undeclared network access, Host credential inheritance, process escape, and
   declared resource overruns;
9. at A2, cancellation, Lease loss, policy revocation, and any isolation,
   resource, credential, or side-effect violation terminate the process tree,
   revoke or fence every side-effecting sink, and prevent a replacement Attempt
   from sharing mutable resources with an unfenced predecessor;
10. cancellation, timeout, Lease expiry, duplicate delivery, late results,
   stale results, and restart recovery are deterministic and preserve every
   Attempt;
11. the Executor may append valid operational transitions but cannot rewrite
    or delete prior records; an A2 Worker receives a read-only projected policy
    but cannot modify its bound policy or Lease or access their authority
    stores, the execution journal, Chronicle, or canonical projections;
12. Job completion leaves Chronicle, Runs, Artifacts, Assessments, Decisions,
   and Seals unchanged until an explicit Athanor transition succeeds;
13. accepted Proposals retain Capsule, policy, Job, Attempt, backend, input,
    output, assurance-profile, conformance-suite, and evidence provenance;
14. Athanor rejects a missing, mismatched, late, terminally ineligible, or
    under-assured realized claim;
15. partial outputs, forged Sigils, corrupt logs, and missing provenance are
    quarantined and ineligible for acceptance;
16. A2 cleanup and process-tree termination are verified, while A1 records
    cooperative cleanup without claiming hostile containment, and every
    cleanup failure is retained;
17. an MCP start request only submits a closed typed Job to the Executor, and
    no Phase 3 MCP tool exposes generic command, filesystem, Git, web, or
    arbitrary-execution authority;
18. a `REQUIRED` approval fixture constructs the pre-approval candidate,
    subject, transition request, canonical `execution.approval.granted` Event,
    paired Receipt, and final Specification in that order; the exact
    Receipt-to-Event-to-request-to-subject chain and three-field omission
    recomputation succeed without a digest cycle, while a changed post-subject
    field, wrong Event type or body Sigil, mismatched request, changed subject
    bytes under one EA-ID, a changed subject under the same
    `(Task-ID, idempotency_key_sigil)` operation scope, reused request ID,
    reused Receipt, or any claimed final-Specification binding fails;
19. every boolean-direction fixture follows its field-specific rule: Process
    permits only true-to-false, environment `required`, runtime identity
    requirements, and side-effect approval permit only false-to-true, Input
    identity booleans remain true, and an unlisted boolean must remain exact;
20. every `Set` fixture rejects equal semantic keys even when the full objects
    differ, including duplicate tool IDs, environment names, output logical
    names, Host constraint IDs, retention tuples, and assurance tuples in a
    Task Circle;
21. filesystem and output prefix fixtures accept parent `a` depth one narrowed
    to child `a/x` depth zero, reject child `a/x` depth one, reject checked
    addition overflow, and apply the same boundary to a fixed output path;
22. `IdentityRequirements` rejects a missing member, an extra member, null,
    and an unknown nested property;
23. result-mode fixtures accept Capability `[OPTIONAL]` narrowed to Task
    `[REQUIRED]`, `[FORBIDDEN]`, or `[REQUIRED, FORBIDDEN]`, reject Task
    `[OPTIONAL]` under Capability `[REQUIRED]`, and reject every array that
    combines `OPTIONAL` with another token;
24. a Task fixture validates `circle_sigil` from the Circle preimage with only
    that field omitted and then validates `capsule_sigil` with the valid Circle
    Sigil retained; omission, placeholder, wrong omission, or a Circle mutation
    fails both eligibility and launch; and
25. each Attempt selecting `NEW_AUTHORIZATION_EACH_ATTEMPT` starts with the
    exact immutable requirement, cannot preflight while `PENDING`, reaches
    `BOUND` through one exact event, and rejects a missing field, wrong Job,
    Attempt, ordinal, Specification, effect set, authority Sigil, subject Sigil,
    Receipt binding, reused predecessor subject or Receipt, second assignment,
    or RFC-0012 implementation lacking the complete carrier; and
26. every post-terminal retention binding resolves one exact RFC-0013
    `artifact-retention-policy/1.0` record by `SP-` ID and `record_sigil`, uses
    the importing version constant `1.0`, and rejects the former `POL-`
    namespace, any other version, an unresolved policy, or a mismatched Sigil
    before Execution Specification or Job creation;
27. both Specification approval and per-Attempt authorization reject a
    `receipt/1.1` with any invented purpose or subject member, resolve purpose
    and subject only through the exact canonical Event and immutable transition
    request, and reject a wrong request ID/Sigil, Event ID/body Sigil, purpose,
    subject, payload Actor, outer Chronicle Actor, authentication-context
    mapping, or cross-Specification/cross-Attempt reuse; and
28. retention fixtures prove that narrowing
    `retention_duration_seconds` can only move the execution-owned hold's
    checked absolute `release_due_at` earlier, overflow fails closed, expiry and
    crash Recovery release that exact hold without extending its deadline, and
    an additive canonical pin or legal, preservation, or stricter RFC-0013
    policy may retain the bytes afterward without keeping the execution hold
    active or treating its duration as a physical-retention minimum.

The `0.4` reference vertical slice must retain evidence for its exact Host and
backend configuration and must state the highest assurance level that the
evidence actually supports.
