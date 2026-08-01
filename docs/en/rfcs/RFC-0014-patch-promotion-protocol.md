---
title: "RFC-0014: Patch Promotion Protocol"
document_id: BW-RFC-0014
version: 0.1
status: draft
owner: unassigned
date: 2026-07-31
language: en
canonical: true
---

# RFC-0014: Patch Promotion Protocol

## Status

This draft defines the Phase 3 protocol for exporting a bounded change from a
Crucible, validating it as an immutable Patch Proposal, and promoting that
exact proposal into a human-selected target through Host-native file and Git
tools.

This RFC depends on RFC-0011's control-plane and execution-plane separation,
RFC-0012's terminal Attempt and fencing rules, and RFC-0013's content-addressed
Blob and Artifact contracts, plus RFC-0015's immutable Job Outcome,
`agent-result/2.0`, and shared MCP Registry contracts. It does not authorize
automatic patch application, merge, commit, push, or publication. Executable
Schemas and the reference adapter are required before this protocol can advance
from draft.

## Problem

A Worker may modify files in a mutable Crucible, but neither Job completion nor
the existence of a textual diff proves that the change:

- was produced from the declared base;
- contains only files and entry types allowed by the Task;
- can be reproduced without fuzzy patch application;
- passed the declared validation policy;
- still applies to the researcher's current target;
- was explicitly selected by a human for that exact target; or
- was applied once, completely, and recoverably.

The existing Phase 2 `code-modification-result/1.0` contract records a patch
string, changed files, tests, a validation summary, and residual risks. Those
fields are sufficient for a bounded Agent Result Proposal, but they do not bind
an immutable Crucible base, machine-verifiable preimages and postimages,
validation evidence, a promotion target, or a recoverable application
operation. Reinterpreting that contract as application authority would change
its accepted meaning and make a Provider-authored string capable of driving a
repository mutation.

Patch handling also crosses two authority domains. Athanor and Chronicle own
accepted canonical research records. The interactive Host owns repository
reads, file edits, patch operations, shell, and Git through native tools. If
Athanor applied a patch, MCP exposed a Git proxy, or a Worker wrote directly to
the researcher's worktree, the Phase 2 Host boundary would be erased. If the
Host applied a patch without an identity-bound record, Benchwork could not
distinguish the intended change from a stale, duplicated, partial, or
conflicting mutation.

## Decision

Benchwork treats a patch as an immutable, content-identified Proposal and
treats promotion as a separately authorized, Host-native side effect.

```text
pinned Crucible Base Identity
              |
              v
 terminal eligible execution result
 + retained terminal Crucible identity
              |
              v
 Athanor accepts agent-result/2.0 -> Receipt
              |
              v
trusted derived export: stage -> verify -> commit Blobs
              |
              v
 Reference Set candidate + Patch Proposal candidate
 + expected Postimage Identity
              |
              v
 acquire RFC-0013 gate -> register Reference Set
 -> final request Sigil -> canonical-reference intent
              |
              v
 Athanor accepts patch.proposed -> Receipt
              |
              v
 isolated validation materialization + evidence
              |
              v
 immutable promotion preview
              |
              v
 explicit human authorization -> Chronicle Receipt
              |
              v
 Host-native exact apply + postimage verification
              |
              v
 Athanor accepts terminal promotion record
              |
              v
 Chronicle Receipt
```

Validation never promotes a patch. Human authorization never makes a patch
scientifically correct. A promotion authorization Receipt permits one exact,
idempotent application operation; it is not evidence that the operation
completed. A terminal promotion Receipt proves that Athanor accepted the
declared identities, evidence, and outcome under this protocol. It does not
prove that an external Git remote, branch, pull request, or deployment exists.

Patch derivation is post-terminal. An immutable Execution Job,
`execution-result/1.0`, accepted `agent-result/2.0`, or Job observation is
never reopened or backfilled with a Patch Proposal ID. The derived Proposal
points backward to exactly one accepted `agent-result/2.0` Receipt. A read
projection may later show that relationship without changing either source
record.

Phase 3 adds these exact closed, versioned contracts:

| Contract identifier | Purpose |
| --- | --- |
| `patch-base-identity-profile/1.0` | Complete-tree identity and path-semantics profile. |
| `patch-tree-manifest/1.0` | Canonical complete-tree manifest used by Base, Postimage, retained terminal-source, and Promotion Target identities. |
| `patch-base/1.0` | Immutable complete Base manifest identity and execution provenance. |
| `patch-bundle/1.0` | Primitive operations, explicit preimages and postimages, payload Blob references, and review renderings. |
| `patch-proposal/1.0` | Post-terminal derived Proposal bound to one accepted Agent Result Receipt. |
| `patch-validation-policy/1.0` | Required validation checks, evidence, assurance, and independence rules. |
| `patch-validation-evidence/1.0` | One immutable validation observation for the exact Proposal. |
| `patch-target-state-evidence/1.0` | Bounded verifier evidence for one Promotion Target identity. |
| `patch-promotion-adapter/1.0` | Closed Host-native application, deadline, guard, and recovery profile. |
| `patch-promotion-preview/1.0` | Immutable expiring human decision boundary for promotion or recovery. |
| `patch-promotion-authorization/1.0` | Canonical authorization bound to one exact Preview. |
| `patch-promotion-rejection/1.0` | Canonical explicit rejection bound to one exact Preview. |
| `patch-promotion-attempt/1.0` | One immutable allocation of a Host-native Promotion Attempt. |
| `patch-promotion-target-guard/1.0` | Target guard lifecycle, ownership, coordinator epoch, backend generation, fence floor, and expiry. |
| `patch-promotion-checkpoint/1.0` | Verified recoverable preimage checkpoint for one Attempt and affected-path set. |
| `patch-promotion-mutation-intent/1.0` | Write-ahead binding for all promotion side effects. |
| `patch-promotion-outcome/1.0` | One terminal Promotion Attempt outcome. |
| `patch-promotion-recovery-attempt/1.0` | One separately authorized attempt to recover a prior `PARTIAL` outcome. |
| `patch-promotion-recovery-intent/1.0` | Write-ahead binding for one exact recovery action. |
| `patch-promotion-recovery-record/1.0` | Terminal evidence for one Recovery Attempt. |
| `patch-promotion-journal-event/1.0` | Hash-chained operational event with closed type-specific payloads. |
| `patch-promotion-journal-head/1.0` | Replaceable cache for the verified Promotion Journal head. |
| `patch-promotion-state/1.0` | Deterministic replay projection for clock authority, Previews, decisions, guards, attempts, checkpoints, and recovery. |
| `patch-promotion-prepare-request/1.0` | Closed request for preparing a promotion or recovery Preview. |
| `patch-promotion-prepare-response/1.0` | Closed bounded response containing the exact Preview. |
| `patch-promotion-inspect-request/1.0` | Closed read request for one Proposal, Preview, decision, Promotion Attempt, or Recovery Attempt. |
| `patch-promotion-inspect-response/1.0` | Closed bounded and paginated inspection response. |
| `patch-promotion-authorize-request/1.0` | Closed `AUTHORIZE \| REJECT` human-decision request for one Preview. |
| `patch-promotion-authorize-response/1.0` | Closed response union containing the authorization or rejection Receipt and identity. |
| `patch-promotion-outcome-request/1.0` | Closed request for accepting one terminal Promotion or Recovery record. |
| `patch-promotion-outcome-response/1.0` | Closed response containing the accepted terminal Receipt. |
| `patch-operational-root-plan/1.0` | Immutable previsibility plan binding one future protection-bearing Promotion Event to its exact OperationalRoot identity. |
| `patch-operational-evidence-manifest/1.0` | Closed event-evidence or Journal-suffix source manifest with deterministic Storage extraction. |
| `patch-operational-root-release-evidence/1.0` | Replayable root, guard, canonical, retention, clock, and absence proof for one Storage hold release. |

Each identifier is published at the corresponding
`https://benchwork.dev/schemas/<name>/<version>` `$id` and conventional
`<name>-<version>.json` filename; for example,
`patch-promotion-journal-event/1.0` is
`patch-promotion-journal-event-1.0.json`. Aliases or differently versioned
filenames do not satisfy the contract.

### Exact contract shapes

The following notation is normative. `V<x>` is the exact version string `x`;
`ID<P>` is an ASCII string of 3 through 128 bytes matching
`P-[A-Za-z0-9][A-Za-z0-9._-]*`; `StorageID<P>` is an exact RFC-0013
operational ID: an ASCII string of 3 through 128 bytes matching
`P-[A-Za-z0-9][A-Za-z0-9._:-]*`; `StorageOpaque` is RFC-0013 `Opaque`:
printable UTF-8 of 1 through 256 bytes with no NUL or control character;
`OJID` is RFC-0015's exact 67-byte ASCII
`OJ-[A-F0-9]{64}` domain; `Sigil` is exactly the 71-byte ASCII form
`sha256:` followed by 64 lowercase hexadecimal SHA-256 characters; `Time` is
exactly RFC-0013 `Timestamp`: normalized UTC RFC 3339 ending in `Z`, with no
leap second and at most six fractional digits; `U64` is an integer in
`0..18446744073709551615`; `Text<N>` is
well-formed UTF-8 of `0..N` bytes with no NUL or disallowed control character;
`Enum<a|b>` is one listed ASCII value; and `Nullable<T>` is exactly JSON
`null` or `T`, never omission. `Token` is exactly 43 ASCII bytes matching
`[A-Za-z0-9_-]{43}`, the unpadded base64url encoding of 32 bytes; `True` is
exactly the JSON boolean `true`; `Bool` is exactly a JSON boolean; and `U63`
is an integer in `0..9223372036854775807`; `PositiveU63` is `U63` in
`1..9223372036854775807`. `Ref<T>` is the closed object
`{id: ID<T>, sigil: Sigil}`; `BlobRef` is the closed object
`{sigil: Sigil, size_bytes: U63, media_type: Text<128>}`. Its `sigil` value
equals RFC-0013 `BlobRef.blob_sigil` and its `size_bytes` value equals
RFC-0013 `BlobRef.size_bytes`; this is an exact value mapping, not an identical
object shape, because local `media_type` is additional bounded observation
metadata. `ReceiptRef` is the
closed object `{receipt_id: ID<RC>, receipt_sigil: Sigil,
event_id: ID<CE>, event_body_sigil: Sigil}`; and `Rev` is the closed object
`{entity_type: Text<64>, entity_id: Text<128>, prior_revision: U64,
next_revision: U64}` with `next_revision = prior_revision + 1`.
`StorageEventRef`, `StoragePrefixRef`, `ReferenceSetRef`, `HeadRef`,
`ChronicleHeadRef`, and `HoldBinding` are exact closed `$defs` below rather
than instances of generic `Ref<T>`. In particular, a replaceable Journal Head
has no synthetic object ID.

`List<T,lo..hi>` preserves order and may repeat. `Set<T,lo..hi,key>` is sorted
strictly by the named key using unsigned UTF-8 byte order and contains no
duplicate key; `value` means the primitive value itself and a parenthesized
tuple means lexicographic comparison of its members. `Obj<X>` and `Union<X>`
name the exact closed local `$defs` published in this RFC. `Obj<X>` is a
required object with exactly the named members. `Union<X>` is exactly one
discriminated branch; overlapping validation is forbidden. Those definitions
may use only the primitives above and state every member, branch discriminator,
and bound. The shared hard
caps are `MAX_PATHS = 100000`, `MAX_BLOBS = 4096`,
`MAX_EVIDENCE = 4096`, `MAX_LOG_REFS = 256`, `MAX_PAGE = 256`,
`MAX_STATE_ENTITIES = 1000000`, `MAX_DIAGNOSTIC_BYTES = 65536`, and
`MAX_RECORD_BYTES = 8388608`. `MAX_ACTIVE_GUARDS = 4096` is a project-global
admission cap, not a per-page limit. No Schema may raise a cap through
configuration. The complete canonical JSON of every top-level contract,
including State, is at most `MAX_RECORD_BYTES`; admission uses the lower limit
implied by that byte cap and every field/cardinality cap. A field maximum never
permits construction of an oversized record, and a Journal append that would
make the next projected State oversized is rejected before visibility.

`MAX_BLOBS` is also the aggregate cap on the sorted unique managed-Blob
closure of one Patch Bundle, derived Reference Set, operational hold, or
canonical transition request. Per-field maxima do not add: the retained
RFC-0012 source bundle, Base and Postimage manifests, the Patch Bundle Blob
itself, payloads, renderings, attachments, checkpoints, verifier evidence, and
other retained Blob members together must fit that one cap. Before any staging
reservation or write, Blob commit,
Reference Set registration, control-record creation, journal append,
canonical submission, or target side effect, Export, Prepare, and canonical
submission compute the complete candidate bytes and Sigils read-only, form
the exact distinct managed-Blob closure, and reject a 4,097th value. Later
steps must equal that preflight plan byte-for-byte and cannot discover or add
a Blob. This is the exact RFC-0013 Reference Set and reference-intent
collection bound; no sharding or implicit continuation is part of v1.
For a `patch-operational-evidence-manifest/1.0`, the distinct
`control_records` plus `blob_refs`, the extracted Reference Set `edges`, and
the computed `validation.evidence_sigils` are three separately bounded
collections and each has cardinality at most 4,096. The complete candidate
for all three is computed before Manifest finalization; exceeding any bound
fails before Manifest, Reference Set, plan, hold, or Promotion visibility.
The Event-specific `S(...)` union below is likewise a cross-field bound of at
most `MAX_EVIDENCE`: individual field maxima never authorize an aggregate
4,097th evidence Sigil.

Every row below is the complete top-level field set. Every field is required;
conditional values use `Nullable`. Objects and all nested objects have
`additionalProperties: false`; arrays have exact `minItems`, `maxItems`, sort,
and uniqueness constraints shown by their type. Except for the two raw-token
request/response exceptions stated below, the final named `*_sigil` is
the `sha256:` prefix followed by lowercase hex SHA-256 over canonical JSON
with only that field omitted. Canonical JSON
rejects duplicate keys, non-integer numbers, non-finite values, invalid UTF-8,
and non-canonical escapes.

| # | Contract | Exact required top-level fields and types | Self-Sigil |
| --- | --- | --- | --- |
| 1 | `patch-base-identity-profile/1.0` | `schema_version: V<1.0>`; `profile_id: ID<PBIP>`; `path_scope: Obj<PathScope>`; `path_semantics: Obj<PathSemantics>`; `entry_semantics: Obj<EntrySemantics>`; `limits: Obj<IdentityLimits>`; `protected_paths: Set<Text<4096>,1..256,value>`; `profile_sigil: Sigil` | `profile_sigil` |
| 2 | `patch-base/1.0` | `schema_version: V<1.0>`; `base_id: ID<PB>`; `identity_profile: Ref<PBIP>`; `source_root_id: Text<128>`; `source_root_sigil: Sigil`; `scope: Obj<PathScope>`; `tree: Obj<TreeIdentity>`; `manifest_blob: BlobRef`; `input_artifacts: Set<Ref<AR>,0..MAX_BLOBS,id>`; `execution: Obj<ExecutionBinding>`; `vcs: Nullable<Obj<VcsBinding>>`; `base_sigil: Sigil` | `base_sigil` |
| 3 | `patch-bundle/1.0` | `schema_version: V<1.0>`; `bundle_id: ID<PBU>`; `base: Ref<PB>`; `postimage: Obj<PostimageIdentity>`; `operations: Set<Obj<PatchOperation>,1..MAX_PATHS,path_bytes>`; `payloads: Set<BlobRef,0..MAX_BLOBS,sigil>`; `renderings: Set<BlobRef,0..MAX_LOG_REFS,sigil>`; `attachments: Set<BlobRef,0..MAX_LOG_REFS,sigil>`; `source: Obj<ExportSource>`; `agent_result_receipt: ReceiptRef`; `limits: Obj<BundleLimits>`; `bundle_sigil: Sigil` | `bundle_sigil` |
| 4 | `patch-proposal/1.0` | `schema_version: V<1.0>`; `proposal_id: ID<PP>`; `agent_result: Obj<AcceptedAgentResultBinding>`; `job_outcome: Obj<JobOutcomeBinding>`; `terminal_source: Obj<TerminalSourceBinding>`; `bundle: Ref<PBU>`; `base: Ref<PB>`; `postimage: Obj<PostimageIdentity>`; `reference_set: Obj<ReferenceSetRef>`; `control_bindings: Obj<ControlBindings>`; `execution_bindings: Obj<ExecutionBindings>`; `identity_profiles: Obj<IdentityProfiles>`; `scope: Obj<PathScope>`; `changed_paths: Set<Text<4096>,1..MAX_PATHS,value>`; `summary: Text<16384>`; `claimed_intent: Text<16384>`; `residual_risks: List<Text<4096>,0..256>`; `exporter: Obj<ExporterBinding>`; `created_at: Time`; `promotion_eligibility: Enum<ELIGIBLE\|INELIGIBLE>`; `proposal_sigil: Sigil` | `proposal_sigil` |
| 5 | `patch-validation-policy/1.0` | `schema_version: V<1.0>`; `policy_id: ID<PVP>`; `policy_version: Text<64>`; `required_checks: Set<Obj<ValidationRequirement>,1..MAX_EVIDENCE,check_id>`; `optional_checks: Set<Obj<ValidationRequirement>,0..MAX_EVIDENCE,check_id>`; `minimum_assurance: Obj<AssuranceRequirement>`; `independence: Obj<IndependenceRule>`; `environment_rules: List<Obj<EnvironmentRule>,0..256>`; `limits: Obj<ValidationLimits>`; `policy_sigil: Sigil` | `policy_sigil` |
| 6 | `patch-validation-evidence/1.0` | `schema_version: V<1.0>`; `evidence_id: ID<PVE>`; `proposal: Ref<PP>`; `bundle: Ref<PBU>`; `base: Ref<PB>`; `postimage: Obj<PostimageIdentity>`; `policy: Ref<PVP>`; `check: Obj<ValidationCheck>`; `validator: Obj<ValidatorBinding>`; `execution: Obj<ValidationExecution>`; `started_at: Time`; `terminal_at: Time`; `status: Enum<PASS\|FAIL\|ERROR\|CANCELLED\|INELIGIBLE>`; `exit_result: Obj<ExitResult>`; `observations: List<Text<4096>,0..256>`; `logs: Set<BlobRef,0..MAX_LOG_REFS,sigil>`; `result_artifacts: Set<Ref<AR>,0..MAX_EVIDENCE,id>`; `postimage_before: Obj<VerificationBinding>`; `postimage_after: Obj<VerificationBinding>`; `limitations: List<Text<4096>,0..256>`; `residual_risks: List<Text<4096>,0..256>`; `evidence_sigil: Sigil` | `evidence_sigil` |
| 7 | `patch-target-state-evidence/1.0` | `schema_version: V<1.0>`; `evidence_id: ID<PTSE>`; `target_id: ID<PT>`; `identity_profile: Ref<PBIP>`; `observed_identity: Obj<TreeIdentity>`; `target_content_generation: Text<256>`; `root_identity: Obj<RootIdentity>`; `observed_at: Time`; `verifier: Obj<VerifierBinding>`; `bounds: Obj<ScanBounds>`; `evidence_blobs: Set<BlobRef,1..MAX_EVIDENCE,sigil>`; `evidence_sigil: Sigil` | `evidence_sigil` |
| 8 | `patch-promotion-adapter/1.0` | `schema_version: V<1.0>`; `adapter_id: ID<PPA>`; `adapter_version: Text<64>`; `mode: Enum<FULL_TREE_ATOMIC_CAS\|PER_ENTRY_GENERATIONAL_CAS>`; `platform_profile: Obj<PlatformProfile>`; `deadline_policy: Obj<DeadlinePolicy>`; `guard_backend: Obj<GuardBackend>`; `mutation_semantics: Obj<MutationSemantics>`; `recovery_semantics: Obj<RecoverySemantics>`; `disabled_behaviors: Set<Text<128>,1..256,value>`; `limits: Obj<AdapterLimits>`; `configuration_sigil: Sigil`; `adapter_sigil: Sigil` | `adapter_sigil`; `configuration_sigil` covers exactly `{platform_profile, deadline_policy, guard_backend, mutation_semantics, recovery_semantics, disabled_behaviors, limits}` |
| 9 | `patch-promotion-preview/1.0` | `schema_version: V<1.0>`; `preview_id: ID<PRV>`; `kind: Enum<PROMOTE\|RECOVER_PARTIAL>`; `proposal: Ref<PP>`; `bundle: Ref<PBU>`; `base: Ref<PB>`; `postimage: Obj<PostimageIdentity>`; `validation_policy: Ref<PVP>`; `validation_evidence: Set<Ref<PVE>,1..MAX_EVIDENCE,id>`; `target: Obj<TargetBinding>`; `target_state_evidence: Ref<PTSE>`; `target_content_generation: Text<256>`; `adapter: Ref<PPA>`; `mode: Enum<FULL_TREE_ATOMIC_CAS\|PER_ENTRY_GENERATIONAL_CAS>`; `deadline_policy_sigil: Sigil`; `affected_paths: Set<Text<4096>,1..MAX_PATHS,value>`; `operation_sigil: Sigil`; `recovery: Nullable<Obj<RecoverySelection>>`; `abandoned_lineage: Nullable<Obj<AbandonedLineageBinding>>`; `residual_risks: List<Text<4096>,0..256>`; `prepared_at: Time`; `expires_at: Time`; `idempotency_key_sigil: Sigil`; `confirmation_token_sigil: Sigil`; `preview_sigil: Sigil` | `preview_sigil`; raw token is not a field |
| 10 | `patch-promotion-authorization/1.0` | `schema_version: V<1.0>`; `authorization_id: ID<PAU>`; `decision: Enum<AUTHORIZE>`; `preview: Ref<PRV>`; `proposal: Ref<PP>`; `target_state_evidence: Obj<patch-target-state-evidence/1.0>`; `target_content_generation: Text<256>`; `affected_paths: Set<Text<4096>,1..MAX_PATHS,value>`; `operation_sigil: Sigil`; `residual_risks: List<Text<4096>,0..256>`; `target: Obj<TargetBinding>`; `base: Ref<PB>`; `postimage: Obj<PostimageIdentity>`; `validation: Obj<ValidationSelection>`; `adapter: Ref<PPA>`; `mode: Enum<FULL_TREE_ATOMIC_CAS\|PER_ENTRY_GENERATIONAL_CAS>`; `recovery: Nullable<Obj<RecoverySelection>>`; `abandoned_lineage: Nullable<Obj<AbandonedLineageBinding>>`; `expires_at: Time`; `confirmation_token_sigil: Sigil`; `actor: Obj<ActorBinding>`; `host: Obj<HostBinding>`; `decision_at: Time`; `clock_policy_sigil: Sigil`; `clock_evidence_sigil: Sigil`; `request_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `authorization_sigil: Sigil` | `authorization_sigil`; the later canonical Event, not this candidate, binds the reference intent and set |
| 11 | `patch-promotion-rejection/1.0` | `schema_version: V<1.0>`; `rejection_id: ID<PREJ>`; `decision: Enum<REJECT>`; `preview: Ref<PRV>`; `proposal: Ref<PP>`; `actor: Obj<ActorBinding>`; `host: Obj<HostBinding>`; `reason: Text<4096>`; `decision_at: Time`; `clock_policy_sigil: Sigil`; `clock_evidence_sigil: Sigil`; `request_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `rejection_sigil: Sigil` | `rejection_sigil`; the later canonical Event, not this candidate, binds the reference intent and set |
| 12 | `patch-promotion-attempt/1.0` | `schema_version: V<1.0>`; `attempt_id: ID<PAT>`; `authorization: Ref<PAU>`; `operation_sigil: Sigil`; `target: Obj<TargetBinding>`; `target_content_generation: Text<256>`; `adapter: Ref<PPA>`; `mode: Enum<FULL_TREE_ATOMIC_CAS\|PER_ENTRY_GENERATIONAL_CAS>`; `created_at: Time`; `state: Enum<CREATED\|PREFLIGHTING\|READY\|MUTATING\|VERIFYING\|APPLIED\|RECOVERED_POSTIMAGE_OBSERVED\|ALREADY_APPLIED\|STALE\|CONFLICT\|FAILED\|PARTIAL\|CANCELLED>`; `revision: U64`; `attempt_sigil: Sigil` | `attempt_sigil` |
| 13 | `patch-promotion-target-guard/1.0` | `schema_version: V<1.0>`; `guard_id: ID<PG>`; `target_id: ID<PT>`; `owner_kind: Enum<PROMOTION\|RECOVERY>`; `owner_attempt_id: Text<128>`; `coordinator_id: ID<PC>`; `coordinator_epoch: U64`; `state: Enum<NONE\|ACQUIRING\|HELD\|RENEWING\|RELEASING\|FENCING\|RECOVERING\|RELEASED\|FENCED\|FAILED>`; `backend_generation: Nullable<Text<256>>`; `fencing_generation: U64`; `fence_floor: U64`; `target_content_generation: Text<256>`; `deadline_policy_sigil: Sigil`; `clock_anchor_evidence_sigil: Nullable<Sigil>`; `original_remaining_ns: Nullable<U64>`; `acquired_at: Nullable<Time>`; `expires_at: Nullable<Time>`; `recovery_of_guard_id: Nullable<ID<PG>>`; `revision: U64`; `guard_sigil: Sigil` | `guard_sigil`; the two anchor fields are both null before an anchor and otherwise both non-null |
| 14 | `patch-promotion-checkpoint/1.0` | `schema_version: V<1.0>`; `checkpoint_id: ID<PCK>`; `attempt_id: ID<PAT>`; `target_id: ID<PT>`; `base: Ref<PB>`; `affected_paths: Set<Text<4096>,1..MAX_PATHS,value>`; `entries: Set<Obj<CheckpointEntry>,1..MAX_PATHS,path_bytes>`; `checkpoint_blobs: Set<BlobRef,0..MAX_BLOBS,sigil>`; `created_at: Time`; `verified_at: Time`; `checkpoint_sigil: Sigil` | `checkpoint_sigil`; this record is finalized before its derived Reference Set and hold; an all-absent/directory preimage has an empty Blob set |
| 15 | `patch-promotion-mutation-intent/1.0` | `schema_version: V<1.0>`; `intent_id: ID<PMI>`; `attempt_id: ID<PAT>`; `authorization: Ref<PAU>`; `operation_sigil: Sigil`; `guard: Ref<PG>`; `fencing_generation: U64`; `fence_floor: U64`; `target_content_generation: Text<256>`; `checkpoint: Ref<PCK>`; `base: Ref<PB>`; `postimage: Obj<PostimageIdentity>`; `operations_sigil: Sigil`; `topology_plan: Obj<TopologyPlan>`; `root_identity: Obj<RootIdentity>`; `ancestor_identities: Set<Obj<AncestorIdentity>,1..MAX_PATHS,path_bytes>`; `adapter: Ref<PPA>`; `verification_method: Obj<VerificationMethod>`; `committed_at: Time`; `intent_sigil: Sigil` | `intent_sigil`; this record is finalized before its derived Reference Set and hold |
| 16 | `patch-promotion-outcome/1.0` | `schema_version: V<1.0>`; `outcome_id: ID<PO>`; `authorization_receipt: ReceiptRef`; `attempt_id: ID<PAT>`; `terminal_journal_event_id: ID<PJE>`; `terminal_journal_event_sigil: Sigil`; `operation_sigil: Sigil`; `adapter: Ref<PPA>`; `before_identity: Obj<TreeIdentity>`; `after_identity: Obj<TreeIdentity>`; `before_generation: Text<256>`; `after_generation: Text<256>`; `checkpoint: Nullable<Ref<PCK>>`; `mutation_intent: Nullable<Ref<PMI>>`; `guard: Nullable<Ref<PG>>`; `timestamps: Obj<OutcomeTimes>`; `status: Enum<APPLIED\|RECOVERED_POSTIMAGE_OBSERVED\|ALREADY_APPLIED\|STALE\|CONFLICT\|FAILED\|PARTIAL\|CANCELLED>`; `path_observations: Set<Obj<PathObservation>,1..MAX_PATHS,path_bytes>`; `adapter_write_evidence: Nullable<Obj<AdapterWriteEvidence>>`; `verifier_evidence: Set<BlobRef,1..MAX_EVIDENCE,sigil>`; `diagnostics: Text<MAX_DIAGNOSTIC_BYTES>`; `outcome_sigil: Sigil` | `outcome_sigil`; guard is null only when terminalized before allocation; terminal Journal event never contains this value, and the later canonical Event binds the reference intent and set |
| 17 | `patch-promotion-recovery-attempt/1.0` | `schema_version: V<1.0>`; `recovery_attempt_id: ID<PRA>`; `parent_attempt_id: ID<PAT>`; `parent_outcome_receipt: ReceiptRef`; `authorization: Ref<PAU>`; `action: Enum<RESTORE_BASE\|ACCEPT_POSTIMAGE\|ABANDON>`; `target: Obj<TargetBinding>`; `bound_before_identity: Obj<TreeIdentity>`; `bound_before_generation: Text<256>`; `checkpoint: Ref<PCK>`; `lineage: Obj<RecoveryLineageBinding>`; `created_at: Time`; `state: Enum<CREATED\|PREFLIGHTING\|READY\|RECOVERING\|VERIFYING\|BASE_RESTORED\|POSTIMAGE_ACCEPTED\|ABANDONED\|STALE\|FAILED\|PARTIAL\|CANCELLED>`; `revision: U64`; `recovery_attempt_sigil: Sigil` | `recovery_attempt_sigil` |
| 18 | `patch-promotion-recovery-intent/1.0` | `schema_version: V<1.0>`; `recovery_intent_id: ID<PRI>`; `recovery_attempt_id: ID<PRA>`; `parent_attempt_id: ID<PAT>`; `authorization: Ref<PAU>`; `action: Enum<RESTORE_BASE\|ACCEPT_POSTIMAGE\|ABANDON>`; `guard: Ref<PG>`; `fencing_generation: U64`; `fence_floor: U64`; `target_content_generation: Text<256>`; `checkpoint: Ref<PCK>`; `bound_before_identity: Obj<TreeIdentity>`; `base: Ref<PB>`; `postimage: Obj<PostimageIdentity>`; `topology_plan: Nullable<Obj<TopologyPlan>>`; `lineage: Obj<RecoveryLineageBinding>`; `committed_at: Time`; `recovery_intent_sigil: Sigil` | `recovery_intent_sigil`; this record is finalized before its derived Reference Set and hold |
| 19 | `patch-promotion-recovery-record/1.0` | `schema_version: V<1.0>`; `recovery_record_id: ID<PRR>`; `recovery_attempt_id: ID<PRA>`; `authorization_receipt: ReceiptRef`; `parent_attempt_id: ID<PAT>`; `parent_outcome_receipt: ReceiptRef`; `action: Enum<RESTORE_BASE\|ACCEPT_POSTIMAGE\|ABANDON>`; `guard: Nullable<Ref<PG>>`; `checkpoint: Ref<PCK>`; `recovery_intent: Nullable<Ref<PRI>>`; `lineage: Obj<RecoveryLineageBinding>`; `before_identity: Obj<TreeIdentity>`; `after_identity: Obj<TreeIdentity>`; `before_generation: Text<256>`; `after_generation: Text<256>`; `resulting_logical_fence_generation: U64`; `verifier_evidence: Set<BlobRef,1..MAX_EVIDENCE,sigil>`; `terminal_journal_event_id: ID<PJE>`; `terminal_journal_event_sigil: Sigil`; `status: Enum<BASE_RESTORED\|POSTIMAGE_ACCEPTED\|ABANDONED\|STALE\|FAILED\|PARTIAL\|CANCELLED>`; `abandonment_disposition: Nullable<Obj<AbandonmentDispositionAuthority>>`; `recovery_record_sigil: Sigil` | `recovery_record_sigil`; guard/intent are null only for the legal pre-allocation/pre-intent terminal branch; disposition is non-null exactly for `ABANDONED`; terminal Journal event never contains this value, and the later canonical Event binds the reference intent and set |
| 20 | `patch-promotion-journal-event/1.0` | `schema_version: V<1.0>`; `journal_id: ID<PJ>`; `event_id: ID<PJE>`; `sequence: U64` in `1..18446744073709551615`; `coordinator_id: ID<PC>`; `coordinator_epoch: U64`; `event_type: Enum<the exact 47 values below>`; `recorded_at: Time`; `entity_revisions: Set<Rev,1..MAX_STATE_ENTITIES,(entity_type,entity_id)>`; `causation_event_id: Nullable<ID<PJE>>`; `idempotency_key_sigil: Nullable<Sigil>`; `payload: Union<EventPayload>`; `previous_event_sigil: Nullable<Sigil>`; `event_sigil: Sigil` | `event_sigil`; `previous_event_sigil` is null only at sequence 1 |
| 21 | `patch-promotion-journal-head/1.0` | `schema_version: V<1.0>`; `journal_id: ID<PJ>`; `coordinator_epoch: U64`; `event_count: U64`; `last_sequence: U64`; `last_event_sigil: Nullable<Sigil>`; `committed_offset: U64`; `frames_file_sigil_prefix: Sigil`; `projected_state_sigil: Sigil`; `head_generation: U64`; `head_sigil: Sigil` | `head_sigil`; empty journal uses count/sequence/offset/generation `0` and null last Sigil |
| 22 | `patch-promotion-state/1.0` | `schema_version: V<1.0>`; `journal_id: ID<PJ>`; `through_sequence: U64`; `through_offset: U64`; `coordinator: Obj<CoordinatorProjection>`; `clock: Obj<ClockProjection>`; `previews: Set<Obj<PreviewProjection>,0..MAX_STATE_ENTITIES,preview_id>`; `decision_submissions: Set<Obj<DecisionProjection>,0..MAX_STATE_ENTITIES,preview_id>`; `guards: Set<Obj<GuardProjection>,0..MAX_STATE_ENTITIES,guard_id>`; `promotion_attempts: Set<Obj<PromotionProjection>,0..MAX_STATE_ENTITIES,attempt_id>`; `recovery_attempts: Set<Obj<RecoveryProjection>,0..MAX_STATE_ENTITIES,recovery_attempt_id>`; `idempotency_bindings: Set<Obj<IdempotencyBinding>,0..MAX_STATE_ENTITIES,(scope,key_sigil)>`; `canonical_links: Set<Obj<CanonicalLinkProjection>,0..MAX_STATE_ENTITIES,(kind,subject_id)>`; `logical_partial_fences: Set<Obj<LogicalPartialFenceProjection>,0..MAX_STATE_ENTITIES,target_id>`; `operational_roots: Set<Obj<OperationalRoot>,0..MAX_STATE_ENTITIES,root_id>`; `integrity_state: Enum<HEALTHY\|READ_ONLY_FAILED>`; `state_sigil: Sigil` | `state_sigil`; raw tokens are excluded |
| 23 | `patch-promotion-prepare-request/1.0` | `schema_version: V<1.0>`; `request_id: ID<PMR>`; `kind: Enum<PROMOTE\|RECOVER_PARTIAL>`; `proposal: Ref<PP>`; `validation_policy: Ref<PVP>`; `validation_evidence: Set<Ref<PVE>,1..MAX_EVIDENCE,id>`; `target_state_evidence: Ref<PTSE>`; `adapter: Ref<PPA>`; `mode: Enum<FULL_TREE_ATOMIC_CAS\|PER_ENTRY_GENERATIONAL_CAS>`; `recovery: Nullable<Obj<RecoverySelection>>`; `abandoned_lineage: Nullable<Obj<AbandonedLineageBinding>>`; `actor: Obj<ActorBinding>`; `host: Obj<HostBinding>`; `requested_at: Time`; `idempotency_key: Text<256>`; `request_sigil: Sigil` | `request_sigil` |
| 24 | `patch-promotion-prepare-response/1.0` | `schema_version: V<1.0>`; `preview: Obj<patch-promotion-preview/1.0>`; `confirmation_token: Token`; `journal_event_id: ID<PJE>`; `journal_event_sigil: Sigil`; `response_sigil: Sigil` | `response_sigil` hashes canonical JSON with raw `confirmation_token` replaced by `preview.confirmation_token_sigil`; computed only after `preview.prepared` commits, never referenced by that event, and raw token is returned only for initial Prepare or exact still-valid retry |
| 25 | `patch-promotion-inspect-request/1.0` | `schema_version: V<1.0>`; `selector: Union<InspectSelector>` with exactly one typed ID; `page_size: U64` in `1..MAX_PAGE`; `cursor: Nullable<Text<512>>`; `fixed_prefix: Nullable<Obj<JournalPrefix>>`; `request_sigil: Sigil` | `request_sigil` |
| 26 | `patch-promotion-inspect-response/1.0` | `schema_version: V<1.0>`; `selector: Union<InspectSelector>`; `fixed_prefix: Obj<JournalPrefix>`; `items: List<Union<InspectItem>,0..MAX_PAGE>`; `next_cursor: Nullable<Text<512>>`; `redactions: Set<Text<128>,0..64,value>`; `response_sigil: Sigil` | `response_sigil`; token, Host path, credential, checkpoint byte, and raw log fields are absent |
| 27 | `patch-promotion-authorize-request/1.0` | `schema_version: V<1.0>`; `request_id: ID<PAR>`; `decision: Enum<AUTHORIZE\|REJECT>`; `preview: Ref<PRV>`; `confirmation_token: Nullable<Token>`; `affirmative_confirmation: Nullable<True>`; `reason: Text<4096>`; `actor: Obj<ActorBinding>`; `host: Obj<HostBinding>`; `requested_at: Time`; `idempotency_key: Text<256>`; `confirmation_token_sigil: Nullable<Sigil>`; `request_sigil: Sigil` | `request_sigil` hashes canonical JSON with raw `confirmation_token` replaced by `confirmation_token_sigil`; `AUTHORIZE` requires token/digest/true, `REJECT` requires all three null |
| 28 | `patch-promotion-authorize-response/1.0` | `schema_version: V<1.0>`; `decision: Enum<AUTHORIZE\|REJECT>`; `record: Union<DecisionRecord>`; `receipt: ReceiptRef`; `response_sigil: Sigil` | `response_sigil`; branch discriminator equals `decision` and raw token is absent |
| 29 | `patch-promotion-outcome-request/1.0` | `schema_version: V<1.0>`; `request_id: ID<POR>`; `kind: Enum<PROMOTION_OUTCOME\|RECOVERY_RECORD>`; `record: Union<OutcomeRecordRef>`; `evidence_sigils: Set<Sigil,1..MAX_EVIDENCE,value>`; `actor: Obj<ActorBinding>`; `host: Obj<HostBinding>`; `requested_at: Time`; `idempotency_key: Text<256>`; `request_sigil: Sigil` | `request_sigil`; branch discriminator must equal top-level `kind` |
| 30 | `patch-promotion-outcome-response/1.0` | `schema_version: V<1.0>`; `kind: Enum<PROMOTION_OUTCOME\|RECOVERY_RECORD>`; `record_id: Text<128>`; `record_sigil: Sigil`; `receipt: ReceiptRef`; `response_sigil: Sigil` | `response_sigil` |
| 31 | `patch-tree-manifest/1.0` | `schema_version: V<1.0>`; `identity_profile: Ref<PBIP>`; `scope: Obj<PathScope>`; `path_semantics: Obj<PathSemantics>`; `entries: Set<Union<PatchTreeEntry>,0..MAX_PATHS,path>`; `entry_count: U64` in `0..MAX_PATHS`; `file_count: U64` in `0..MAX_PATHS`; `total_bytes: U63`; `root_entry_sigil: Sigil`; `manifest_sigil: Sigil`; `record_sigil: Sigil` | `record_sigil`; `manifest_sigil` is the cross-root content identity defined below |
| 32 | `patch-operational-root-plan/1.0` | `schema_version: V<1.0>`; `plan_id: ID<PORP>`; `operational_journal_id: ID<PJ>`; `activation_event_id: ID<PJE>`; `activation_event_type: RootActivationEventType`; `payload_field: ProtectionPayloadField`; `root_kind: OperationalRootKind`; `operational_root_id: ID<PROOT>`; `control_record: Obj<StorageControlRef>`; `reference_set: Obj<ReferenceSetRef>`; `reference_set_registration_event: Obj<StorageEventRef>`; `hold_id: StorageID<SH>`; `hold_set_event_id: StorageID<SE>`; `policy_id: StorageID<SP>`; `policy_sigil: Sigil`; `authorization_kind: Enum<PROMOTION_CONTROL\|JOURNAL_RECOVERY>`; `plan_sigil: Sigil` | `plan_sigil`; identity and causal formulas are defined below |
| 33 | `patch-operational-evidence-manifest/1.0` | `schema_version: V<1.0>`; `evidence_manifest_id: ID<PEM>`; `activation: Obj<EvidenceActivation>`; `body: Union<OperationalEvidenceBody>`; `control_records: Set<Obj<StorageControlRef>,0..MAX_EVIDENCE,(schema_version,record_id)>`; `blob_refs: Set<Obj<StorageBlobRef>,0..MAX_BLOBS,blob_sigil>`; `evidence_sigils: Set<Sigil,1..MAX_EVIDENCE,value>`; `manifest_sigil: Sigil` | `manifest_sigil`; the ID, event projection, extractor, validator, and aggregate bounds are defined below |
| 34 | `patch-operational-root-release-evidence/1.0` | `schema_version: V<1.0>`; `release_evidence_id: ID<PREL>`; `operational_journal_id: ID<PJ>`; `operational_root_id: ID<PROOT>`; `operational_root_sigil: Sigil`; `operational_root_plan: Obj<StorageControlRef>`; `hold_id: StorageID<SH>`; `reference_set: Obj<ReferenceSetRef>`; `hold_set_event: Obj<StorageEventRef>`; `activation_event: Obj<PromotionEventRef>`; `inactivation_event: Obj<PromotionEventRef>`; `release_condition: ReleaseCondition`; `terminal_authority: Obj<StorageControlRef>`; `canonical_completion: Union<CanonicalCompletion>`; `guard_completion: Union<GuardCompletion>`; `promotion_prefix: Obj<JournalPrefix>`; `storage_prefix: Obj<StoragePrefixRef>`; `policy: Obj<ReleasePolicyBinding>`; `trusted_clock: Obj<StorageClockRef>`; `retention_completion: Obj<RetentionCompletion>`; `intent_absence: Union<IntentAbsence>`; `record_sigil: Sigil` | `record_sigil`; deterministic ID and all branch formulas are defined below |

### Closed local `$defs`

The following tables are normative local `$defs`, not examples or deferred
Schema work. Every field shown is required, every object is closed, and every
union uses the shown `kind` or enclosing discriminator. A `$defs` row may
reference another row in this section or one of the 34 exact contract rows
above. `Obj<patch-promotion-preview/1.0>`,
`Obj<patch-promotion-attempt/1.0>`,
`Obj<patch-promotion-target-guard/1.0>`, and
`Obj<patch-promotion-recovery-attempt/1.0>` are exact embedded instances of
rows 9, 12, 13, and 17 respectively. They are not open extension points.

The imported and cross-journal `$defs` are:

| `$def` | Exact required fields or branches |
| --- | --- |
| `ReferenceSetRef` | `{reference_set_id: StorageID<RS>; reference_set_sigil: Sigil}`; it imports RFC-0013 `artifact-storage-reference-set/1.0` identity and verifies the complete registered record by Sigil |
| `StorageEventRef` | `{journal_id: StorageID<SJ>; event_id: StorageID<SE>; sequence: U63 in 1..9223372036854775807; event_sigil: Sigil}`; byte-for-byte RFC-0013 `EventRef` |
| `StoragePrefixRef` | `{journal_id: StorageID<SJ>; through_sequence: U63 in 1..9223372036854775807; terminal_event_sigil: Sigil; projected_state_sigil: Sigil}` |
| `StorageClockRef` | `{utc: Time; monotonic_anchor_id: StorageOpaque; monotonic_ticks: U63; monotonic_frequency_hz: PositiveU63; uncertainty_micros: U63; observation_sigil: Sigil}`; byte-for-byte RFC-0013 `ClockRef` |
| `StorageControlRef` | `{schema_version: StorageOpaque; record_id: StorageOpaque; record_sigil: Sigil}`; byte-for-byte RFC-0013 `ControlRef` |
| `ChronicleHeadRef` | `{schema_version: V<chronicle-head/1.1>; event_count: U63; terminal_receipt_sigil: Nullable<Sigil>}`; exact RFC-0013 Phase 3-admissible `ChronicleHeadRef`, including its additional admission bound, rather than a claim that the older Chronicle Schema's unbounded integer domain is identical |
| `HeadRef` | `{schema_version: V<1.0>; journal_id: ID<PJ>; coordinator_epoch: U64; event_count: U64; last_sequence: U64; last_event_sigil: Nullable<Sigil>; committed_offset: U64; frames_file_sigil_prefix: Sigil; projected_state_sigil: Sigil; head_generation: U64; head_sigil: Sigil}`; it is the complete parseable Head identity, not a synthetic ID |
| `StorageBlobRef` | `{blob_sigil: Sigil; size_bytes: U63}`; byte-for-byte RFC-0013 `BlobRef` and the RFC-0012 `benchwork-source-tree/1.0.bundle_blob` shape |
| `HoldAuthorization` | `{kind: Enum<PROMOTION_CONTROL\|JOURNAL_RECOVERY\|EXECUTION_ROOT_IMPORT>; subject_id: Text<128>; authorization_sigil: Sigil}` |
| `HoldBinding` | `{root_plan: Ref<PORP>; hold_id: StorageID<SH>; hold_set_event: Obj<StorageEventRef>; frozen_storage_prefix: Obj<StoragePrefixRef>; target_reference_set: Obj<ReferenceSetRef>; policy_id: StorageID<SP>; policy_sigil: Sigil; authorization: Obj<HoldAuthorization>}` |
| `PromotionEventRef` | `{protocol_id: constant "benchwork.patch-promotion"; protocol_version: constant "1.0"; journal_id: ID<PJ>; event_id: ID<PJE>; sequence: U64 in 1..18446744073709551615; event_type: one of the exact 47 Event types; event_sigil: Sigil}`; exact RFC-0013 `ExternalEventRef` narrowing |
| `PatchOperationalRootReleaseAuthority` | `{kind: constant "PATCH_OPERATIONAL_ROOT"; protocol_id: constant "benchwork.patch-promotion"; protocol_version: constant "1.0"; operational_journal_id: ID<PJ>; operational_root_id: ID<PROOT>; operational_root_sigil: Sigil; operational_root_plan: Obj<StorageControlRef>; reference_set: Obj<ReferenceSetRef>; hold_set_event: Obj<StorageEventRef>; activation_event: Obj<PromotionEventRef>; inactivation_event: Obj<PromotionEventRef>; release_condition: ReleaseCondition; terminal_authority: Obj<StorageControlRef>; release_evidence: Obj<StorageControlRef>; validator_id: constant "benchwork.patch-operational-root-release"; validator_version: constant "1.1"; validator_sigil: Sigil; authority_sigil: Sigil}`; byte-for-byte RFC-0013 `HoldReleaseAuthority.PATCH_OPERATIONAL_ROOT` |
| `JobOutcomeBinding` | `{outcome_schema: V<execution-job-outcome/1.0>; outcome_id: OJID; outcome_sigil: Sigil; job_id: Text<128>; job_terminal_event_id: Text<128>; job_terminal_event_sigil: Sigil; terminal_source_sigil: Sigil}`; this closed resolver binding identifies the complete RFC-0015 Outcome by `(outcome_id, outcome_sigil)`, copies `job_terminal.event_id`, `job_terminal.event_sigil`, and `terminal_source_binding.terminal_source_sigil`, and verifies the `OJ-` ID derivation exactly as RFC-0015 requires; it is not a partial Outcome representation |
| `ValidationJobOutcomeBinding` | `{outcome_schema: V<execution-job-outcome/1.0>; outcome_id: OJID; outcome_sigil: Sigil; job_id: Text<128>; job_binding_sigil: Sigil; job_terminal_event_id: Text<128>; job_terminal_event_sigil: Sigil}`; resolves and verifies the complete RFC-0015 Outcome for one validation execution, including its selected Attempt, authority, fence, assurance, storage, and terminal evidence |
| `AgentResultProvenance` | Canonical `$ref` to RFC-0015 `agent-result/2.0#/$defs/provenance`; the complete imported object is required byte-for-byte |
| `OutcomeAuthorityBinding` | Canonical `$ref` to RFC-0015 `execution-job-outcome/1.0#/$defs/authority_binding` |
| `OutcomeAssuranceContextBinding` | Canonical `$ref` to RFC-0015 `execution-job-outcome/1.0#/$defs/assurance_context_binding` |
| `OutcomeWorkerSessionBinding` | Canonical `$ref` to RFC-0015 `execution-job-outcome/1.0#/$defs/worker_session_binding` |
| `ReferenceIntentRef` | `{reference_intent_id: StorageID<RI>; record_sigil: Sigil}`; imports RFC-0013 `artifact-storage-reference-intent/1.0` |
| `CanonicalReferenceBinding` | `{reference_intent: Obj<ReferenceIntentRef>; transition_request_sigil: Sigil; reference_sets: Set<Obj<ReferenceSetRef>,1..MAX_EVIDENCE,reference_set_id>}` |

A `HoldBinding` validates only when all of these predicates hold at the same
outer-gate critical section. Let `resolved_root_plan` mean the complete
immutable plan resolved from `root_plan` by its `{id, sigil}` pair:

1. `root_plan` resolves the complete immutable
   `patch-operational-root-plan/1.0` record and its self-Sigil before the hold
   Event is appended;
2. `hold_set_event` resolves in the named Storage Journal and its exact payload
   is `{hold_id, target_kind: REFERENCE_SET, target_id, policy_id,
   authorization_sigil}`;
3. `target_id`, `policy_id`, and `authorization_sigil` equal the corresponding
   binding fields, `policy_sigil` resolves the exact immutable RFC-0013 policy
   record named by `policy_id`, and the resolved Reference Set Sigil equals
   `target_reference_set.reference_set_sigil`;
4. the resolved Reference Set has `source.kind:
   OPERATIONAL_CONTROL_RECORD`, and its source identity and Sigil equal the
   plan's exact `control_record`, while the Set, its registration Event,
   hold/Event IDs, policy tuple, authorization kind, planned activation tuple,
   and derived root ID equal the plan byte-for-byte;
5. `frozen_storage_prefix` is a verified replay prefix from the same Journal,
   includes `hold_set_event.sequence`, has that Event Sigil at that sequence,
   and projects the hold as `ACTIVE`; and
6. every Blob and typed edge reachable from the Reference Set verifies at the
   frozen prefix and again immediately before the Promotion event becomes
   visible.

For `PROMOTION_CONTROL` or `JOURNAL_RECOVERY`, the Reference Set registration
Event is resolved from the complete Set and Storage replay, and both
`authorization.authorization_sigil` and the hold-set payload value are
exactly:

```text
Sigil(["patch-operational-root-hold-set-authorization/1.0",
       {plan_id: root_plan.id,
        plan_sigil: root_plan.sigil},
       {reference_set_id: target_reference_set.reference_set_id,
        reference_set_sigil: target_reference_set.reference_set_sigil,
        registration_event: <exact StorageEventRef>},
       {hold_id, hold_set_event_id: hold_set_event.event_id},
       {policy_id, policy_sigil}])
```

`authorization.subject_id == root_plan.id`; the Set source identity and Sigil
instead equal `resolved_root_plan.control_record.record_id` and
`resolved_root_plan.control_record.record_sigil`. Every tuple in the formula
equals `resolved_root_plan`, including the complete registration Event.
`EXECUTION_ROOT_IMPORT`
instead validates the exact RFC-0012 execution-root formula and cannot
authorize a Promotion operational root. An arbitrary Sigil or changed plan,
Set, Event, policy, kind, or subject is invalid.

The root plan contains no future Promotion Event Sigil, hold Event Sigil,
OperationalRoot Sigil, or time observation. Its identities are:

```text
root_material = canonical_json({
  journal_id: operational_journal_id,
  event_id: activation_event_id,
  payload_field,
  hold_id,
  reference_set_id: reference_set.reference_set_id,
  control_record_id: control_record.record_id,
  control_record_sigil: control_record.record_sigil
})

operational_root_id =
  "PROOT-" + first_32_lower_hex(
    SHA-256("benchwork:promotion-operational-root:v1\0" || root_material))

plan_identity = {
  operational_journal_id, activation_event_id, activation_event_type,
  payload_field, root_kind, operational_root_id, control_record,
  reference_set, reference_set_registration_event, hold_id,
  hold_set_event_id, policy_id, policy_sigil, authorization_kind
}

plan_id =
  "PORP-" + UPPER_HEX(SHA256(canonical_json(
    ["patch-operational-root-plan-id/1.0", plan_identity])))

plan_sigil =
  Sigil(<complete patch-operational-root-plan/1.0 with only
         plan_sigil omitted>)
```

The `(operational_journal_id, activation_event_id)`, `plan_id`, `hold_id`, and
`hold_set_event_id` slots are single assignment. The Event slot's immutable
contents include `activation_event_type` and `payload_field`; the latter is
not part of the uniqueness key. Reuse requires identical complete plan bytes;
a collision, a changed field, or a different record is integrity failure. One
v1 Event can activate at most one operational root. At hold-set admission
Storage validates only this already-durable plan and the preallocated future
identities. It must not look up or pretend to validate a future Promotion
Event or live OperationalRoot.

At activation, the enclosing Promotion Event's Journal ID, Event ID, type, and
protection payload field equal the plan; the binding's plan, Set, hold, and
policy equal it; and recomputation yields the planned root ID. Only then does
replay create the `ACTIVE` root. `CHECKPOINT_PROTECTION` maps to
`CHECKPOINT`; Promotion and Recovery `INTENT_PROTECTION` map to
`MUTATION_INTENT` and `RECOVERY_INTENT` respectively;
`PRIOR_STEP_PROTECTION` and `EVIDENCE_PROTECTION` map to `EVIDENCE`; and
`SUFFIX_EVIDENCE_PROTECTION` maps to `JOURNAL_SUFFIX`.
`JOURNAL_RECOVERY` is legal exactly for
`coordinator.replay-started` plus `SUFFIX_EVIDENCE_PROTECTION`; all other
legal plans use `PROMOTION_CONTROL`.
The plan control Schema is also closed:
`CHECKPOINT` names `patch-promotion-checkpoint/1.0`;
`MUTATION_INTENT` names `patch-promotion-mutation-intent/1.0`;
`RECOVERY_INTENT` names `patch-promotion-recovery-intent/1.0`; and
`EVIDENCE` or `JOURNAL_SUFFIX` names
`patch-operational-evidence-manifest/1.0` whose activation tuple equals the
plan. The admitting Event's typed record reference must resolve the same
checkpoint/intent; an evidence Event resolves the Manifest only through the
plan-bearing binding and its exact Evidence Projection.

`ProtectionPayloadField` is exactly `CHECKPOINT_PROTECTION`,
`INTENT_PROTECTION`, `PRIOR_STEP_PROTECTION`, `EVIDENCE_PROTECTION`, or
`SUFFIX_EVIDENCE_PROTECTION`. `OperationalRootKind` is exactly `CHECKPOINT`,
`MUTATION_INTENT`, `RECOVERY_INTENT`, `EVIDENCE`, or `JOURNAL_SUFFIX`.
`RootActivationEventType` is the exact 23-value enum:

```text
coordinator.replay-started
target.guard-validated
promotion.checkpoint-committed
promotion.mutation-intent-committed
promotion.verification-started
promotion.applied
promotion.recovered-postimage-observed
promotion.already-applied
promotion.stale
promotion.conflicted
promotion.failed
promotion.partial
promotion.cancelled
recovery.checkpoint-verified
recovery.intent-committed
recovery.verification-started
recovery.base-restored
recovery.postimage-accepted
recovery.abandoned
recovery.stale
recovery.failed
recovery.partial
recovery.cancelled
```

Each value admits only the one protection field printed in the transition
table, except that the table distinguishes the two `INTENT_PROTECTION` root
kinds by event family. A planned type with no matching field, a second
protection field, or a different root-kind mapping is invalid.

The evidence-manifest local definitions are:

| `$def` | Exact required fields or branches |
| --- | --- |
| `EvidenceActivation` | `{operational_journal_id: ID<PJ>; activation_event_id: ID<PJE>; activation_event_type: RootActivationEventType; payload_field: Enum<PRIOR_STEP_PROTECTION\|EVIDENCE_PROTECTION\|SUFFIX_EVIDENCE_PROTECTION>}`; type and field must be one of the exact 19 Evidence Projection rows below |
| `PromotionEvidenceOwner` | `{kind: constant "PROMOTION"; attempt_id: ID<PAT>}` |
| `RecoveryEvidenceOwner` | `{kind: constant "RECOVERY"; recovery_attempt_id: ID<PRA>; parent_attempt_id: ID<PAT>}` |
| `JournalSuffixEvidenceOwner` | `{kind: constant "JOURNAL_SUFFIX"; journal_id: ID<PJ>; recovery_id: ID<PTRI>}` |
| `EventEvidenceOwner` | exactly one `PromotionEvidenceOwner` or `RecoveryEvidenceOwner` selected by `kind` |
| `OperationalEvidenceOwner` | exactly one `PromotionEvidenceOwner`, `RecoveryEvidenceOwner`, or `JournalSuffixEvidenceOwner` selected by `kind` |
| `EventEvidenceBody` | `{kind: constant "EVENT_EVIDENCE"; owner: Union<EventEvidenceOwner>; role: Enum<GUARD_VALIDATION\|VERIFICATION\|TERMINAL\|ABANDONMENT>; claims_sigil: Sigil; evidence_binding_sigil: Sigil}` |
| `JournalSuffixEvidenceBody` | `{kind: constant "JOURNAL_SUFFIX"; owner: Obj<JournalSuffixEvidenceOwner>; old_head: Obj<HeadRef>; observed_eof: U64; suffix_kind: Enum<COMPLETE\|TORN_EOF>; last_complete_offset: U64; target_head: Obj<HeadRef>; original_suffix_blob: Obj<StorageBlobRef>; classification_sigil: Sigil}` |
| `OperationalEvidenceBody` | exactly one `EventEvidenceBody` or `JournalSuffixEvidenceBody` branch selected by `kind` |

For `EVENT_EVIDENCE`, `evidence_binding_sigil` is exactly:

```text
Sigil(["patch-operational-event-evidence-binding/1.0",
       activation, body.owner, body.role, body.claims_sigil,
       control_records, blob_refs, evidence_sigils])
```

For `JOURNAL_SUFFIX`, activation is exactly
`coordinator.replay-started`/`SUFFIX_EVIDENCE_PROTECTION`; the owner Journal
equals the activation Journal; both Heads name that Journal;
`observed_eof > old_head.committed_offset`;
`original_suffix_blob.size_bytes ==
observed_eof - old_head.committed_offset`; and the Blob verifies that exact
byte range. `COMPLETE` requires
`last_complete_offset == observed_eof`; `TORN_EOF` requires
`old_head.committed_offset <= last_complete_offset < observed_eof`; in both
branches `target_head.committed_offset == last_complete_offset` and the
target prefix is deterministically reconstructed from the original suffix.
Its classification is:

```text
classification_sigil =
  Sigil(["patch-journal-suffix-classification/1.0",
         owner.journal_id, owner.recovery_id, old_head, observed_eof,
         suffix_kind, last_complete_offset, target_head,
         original_suffix_blob])
```

For every Event-evidence row below, `claims_sigil` is
`Sigil(["patch-operational-event-evidence-claims/1.0", activation,
<the exact row's closed payload after removing only its protection field and
the explicitly tabled evidence fields>])`. This is a field-by-field projection
from the table, not an `*_sigil` naming convention or an open reflection rule.

The suffix Blob occurs exactly once in `blob_refs`; no second suffix
generation or Sigil is legal. For every manifest, the aggregate
`control_records + blob_refs` cardinality is in `1..MAX_BLOBS`; the extracted
edge set is the same size and is also at most 4,096. A repeated
`(schema_version, record_id)` with a different record Sigil, or a repeated
`blob_sigil` with a different size, is invalid rather than a second set
member. All members exist and verify before the manifest, and no future Set,
plan, hold, Promotion Event, Head, or TailRecoveryIntent is a member.

Manifest identities are:

```text
manifest_identity = {
  activation, body, control_records, blob_refs, evidence_sigils
}

evidence_manifest_id =
  "PEM-" + UPPER_HEX(SHA256(canonical_json(
    ["patch-operational-evidence-manifest-id/1.0",
     manifest_identity])))

manifest_sigil =
  Sigil(<complete patch-operational-evidence-manifest/1.0 with only
         manifest_sigil omitted>)
```

The manifest ID and `(operational_journal_id, activation_event_id)` are
single-assignment. The Event slot fixes `activation_event_type` and
`payload_field` before Manifest finalization; neither is a second uniqueness
dimension. A manifest and its one RootPlan can activate only once; a second
Event, field, hold, or root reuse is integrity failure.

Its RFC-0013 Reference Set uses source
`{kind: OPERATIONAL_CONTROL_RECORD, identity: evidence_manifest_id,
schema_version: patch-operational-evidence-manifest/1.0,
sigil: manifest_sigil}` and these fixed profiles:

```text
extractor_id = benchwork.patch-operational-evidence
extractor_version = 1.0
extractor_sigil =
  Sigil(["patch-operational-evidence-extractor/1.0",
         "blob_refs -> HOLD_PROTECTS_BLOB",
         "control_records -> CONTROL_RETAINS_CONTROL"])

validator_id = benchwork.patch-operational-evidence
validator_version = 1.0
validator_sigil =
  Sigil(["patch-operational-evidence-validator/1.0",
         <closed owner/role/event matrix>,
         <closed Journal-suffix predicates>,
         extractor_sigil])
```

Each `blob_refs` member creates exactly one `HOLD_PROTECTS_BLOB` edge with
`target_identity == target_sigil == blob_sigil`; each `control_records`
member creates exactly one `CONTROL_RETAINS_CONTROL` edge with its exact
identity and Sigil. The sorted edge set has no other member.
Every `evidence_sigils` value resolves uniquely to exactly one member of those
two sets and equals that member's Blob or record Sigil. A bare, ambiguous,
missing, or multiply typed Sigil is invalid; identity, generation, timing, and
fence claims live in the closed body/`claims_sigil` rather than masquerading
as Storage edges.
`validation.evidence_sigils` is the sorted unique union of `manifest_sigil`,
all manifest `evidence_sigils`, every control-record Sigil, every Blob Sigil,
and, only for `JOURNAL_SUFFIX`, both Head Sigils and
`classification_sigil`. That computed union, not each input array in
isolation, has cardinality at most 4,096; the complete extracted edge set has
the same independent 4,096 cap. Either overflow rejects the candidate before
Manifest finalization and therefore before Reference Set registration. This
preflight computes the prospective deterministic `manifest_sigil` from the
complete candidate bytes without publishing them; final installation and
readback must reproduce it byte-for-byte. The exact source-validation value
is:

```text
Sigil(["patch-operational-evidence-source-validation/1.0",
       {evidence_manifest_id, manifest_sigil},
       {extractor_id, extractor_version, extractor_sigil},
       {validator_id, validator_version, validator_sigil},
       sorted_exact_edges,
       exact_validation_evidence_sigils])
```

All inputs precede Reference Set registration; no future Sigil participates.

`ReleaseCondition` is exactly `NON_PARTIAL_OUTCOME_OBSERVED`,
`RESOLVED_RECOVERY_OBSERVED`, `ABANDONED_WITH_DISPOSITION`, or
`JOURNAL_RECOVERY_COMPLETED`. The remaining release and abandonment
definitions are closed:

| `$def` | Exact required fields or branches |
| --- | --- |
| `AbandonedRootDisposition` | `{operational_root_id: ID<PROOT>; active_operational_root_sigil: Sigil; operational_root_plan: Obj<StorageControlRef>; hold_id: StorageID<SH>; reference_set: Obj<ReferenceSetRef>; policy_id: StorageID<SP>; policy_sigil: Sigil; disposition: constant "RELEASE_OPERATIONAL_HOLD_AFTER_CANONICAL_ABANDONMENT"}` |
| `TerminalGuardCompletion` | `{kind: constant "TERMINAL_GUARD"; guard: Ref<PG>; terminal_event: Obj<PromotionEventRef>; terminal_state: Enum<RELEASED\|FENCED\|FAILED>}` |
| `AbandonmentDispositionAuthority` | `{kind: constant "ABANDONED_OPERATIONAL_ROOT_DISPOSITION"; recovery_attempt_id: ID<PRA>; parent_attempt_id: ID<PAT>; authorization_receipt: ReceiptRef; actor: Obj<ActorBinding>; disposition_policy_id: constant "PDP-ABANDONED-ROOT-DISPOSITION-V1"; disposition_policy_sigil: Sigil; terminal_event: Obj<PromotionEventRef>; observed_partial_identity: Obj<TreeIdentity>; observed_generation: Text<256>; logical_fence_generation: U64; guard_completion: Obj<TerminalGuardCompletion>; root_dispositions: Set<Obj<AbandonedRootDisposition>,1..MAX_EVIDENCE,operational_root_id>; physical_byte_authority: constant "NONE"; logical_fence_disposition: constant "PRESERVE"; disposition_sigil: Sigil}` |
| `GuardCompletion` | exactly one `TerminalGuardCompletion`; `NO_GUARD_ALLOCATED {kind: constant "NO_GUARD_ALLOCATED"; owner_kind: Enum<PROMOTION\|RECOVERY>; owner_attempt_id: Text<128>; attempt_terminal_event: Obj<PromotionEventRef>; allocation_absence_proof_sigil: Sigil}`; or `NOT_APPLICABLE_JOURNAL_SUFFIX {kind: constant "NOT_APPLICABLE_JOURNAL_SUFFIX"; tail_recovery_id: ID<PTRI>; completion_event: Obj<PromotionEventRef>}` selected by `kind` |
| `CanonicalCompletion` | `COMMITTED_CANONICAL_RECORD {kind: constant "COMMITTED_CANONICAL_RECORD"; receipt: ReceiptRef; reference_intent: Obj<ReferenceIntentRef>; commit_event: Obj<StorageEventRef>}` or `NOT_APPLICABLE_JOURNAL_SUFFIX {kind: constant "NOT_APPLICABLE_JOURNAL_SUFFIX"}` |
| `ReleasePolicyBinding` | `{policy_id: StorageID<SP>; policy_sigil: Sigil; deletion_grace_seconds: U63; retain_until: Nullable<Time>}` |
| `RetentionCompletion` | `{inactivation_recorded_at: Time; grace_due_at: Time; release_not_before: Time; trusted_lower_bound: Time; proof_sigil: Sigil}` |
| `IntentAbsence` | `ATTEMPT_OPERATIONAL_INTENTS_ABSENT {kind: constant "ATTEMPT_OPERATIONAL_INTENTS_ABSENT"; owner_kind: Enum<PROMOTION\|RECOVERY>; owner_attempt_id: Text<128>; promotion_open_intent_ids: Set<Text<128>,0..0,value>; storage_open_reference_intent_ids: Set<StorageID<RI>,0..0,value>; absence_proof_sigil: Sigil}` or `TAIL_RECOVERY_INTENTS_ABSENT {kind: constant "TAIL_RECOVERY_INTENTS_ABSENT"; tail_recovery_id: ID<PTRI>; promotion_open_intent_ids: Set<Text<128>,0..0,value>; storage_open_reference_intent_ids: Set<StorageID<RI>,0..0,value>; absence_proof_sigil: Sigil}` |

`AbandonmentDispositionAuthority` is non-null exactly when the enclosing
Recovery Record has `status: ABANDONED` and `action: ABANDON`; it is null for
every other branch. Its authorization Receipt and Actor equal the exact
canonical Recovery authorization whose selected action is `ABANDON`.
`terminal_event` is `recovery.abandoned` and matches the enclosing Record;
the observed identity/generation and logical fence equal that Event and
Record. `recovery_attempt_id` equals the enclosing Record's
`recovery_attempt_id`, the terminal Event payload, the resolved Recovery
Intent owner, and the resolved Recovery Attempt; `parent_attempt_id` equals
the enclosing Record, Recovery Intent, and Recovery Attempt parent
byte-for-byte. The enclosing Record's non-null `guard`, the resolved
`recovery_intent.guard`, and this disposition's
`guard_completion.guard` are the same bound `Ref<PG>` byte-for-byte; the
replayed `recovery.abandoned.guard_id` equals that Ref's `id`. The Ref's Sigil
binds the immutable guard version carried by the Recovery Intent; the later
terminal Event and replay, rather than a silently substituted Ref, prove its
terminal descendant projection. The enclosing Record's
`terminal_journal_event_id` and
`terminal_journal_event_sigil` continue to identify `recovery.abandoned`,
never the later guard Event.

The abandonment branch has executable no-write equalities:

```text
record.before_identity
  == record.after_identity
  == recovery_attempt.bound_before_identity
  == abandonment_disposition.observed_partial_identity

tree_identity_sigil(record.before_identity)
  == terminal_event.before_identity_sigil
  == terminal_event.after_identity_sigil
  == verification_started.fresh_target_identity_sigil

record.before_generation
  == record.after_generation
  == recovery_attempt.bound_before_generation
  == abandonment_disposition.observed_generation
  == terminal_event.before_generation
  == terminal_event.after_generation
  == verification_started.fresh_target_content_generation

record.resulting_logical_fence_generation
  == record.lineage.logical_fence_generation
  == terminal_event.logical_fence_generation
  == abandonment_disposition.logical_fence_generation
```

`verification_started.scan_status` is `VERIFIED`; a null or alternate fresh
observation is invalid. The exact adapter invocation-trace Blob defined below
also proves that no target-content call occurs between that verification Event
and the reserved `recovery.abandoned` Event.

After `recovery.abandoned` is Head-committed, and before the Recovery Record
candidate or its self-Sigil is constructed, the Coordinator durably releases
or fences that exact guard through the ordinary intent, backend operation,
readback, and terminal-Event sequence. The
`guard_completion.terminal_event` is in the same Promotion Journal, has a
strictly greater sequence than `terminal_event`, maps its Event type to
`terminal_state` exactly, and replays to the same guard projection. A crash in
this interval resumes only that already-authorized guard terminalization; an
ambiguous result enters integrity failure and constructs or submits no
Recovery Record. Physical guard terminalization performs no target-content
write, grants no new mutation authority, and leaves every operational hold
and the logical partial fence active.

For `ABANDONED_WITH_DISPOSITION`, Release Evidence
`guard_completion` equals this embedded `guard_completion` byte-for-byte.
The later `canonical.receipt-observed` Event is strictly after both tabled
Promotion Events and deactivates exactly `root_dispositions`. Its disposition
policy is fixed:

```text
disposition_policy_sigil =
  Sigil(["patch-abandoned-operational-root-disposition-policy/1.0",
         "PDP-ABANDONED-ROOT-DISPOSITION-V1",
         "physical_byte_authority:NONE",
         "logical_fence_disposition:PRESERVE",
         "release-only-after-canonical-abandonment"])

disposition_sigil =
  Sigil(["patch-abandoned-operational-root-disposition/1.0",
         <complete AbandonmentDispositionAuthority with only
          disposition_sigil omitted>])
```

`root_dispositions` is exactly the active lineage-root set later named by
`canonical.receipt-observed.deactivated_operational_root_ids`; every root,
plan, active-root Sigil, hold, Set, and policy equals replayed Promotion and
Storage state. Before Record construction, the complete canonical request
must satisfy `1 + distinct_active_lineage_reference_set_count +
other_mandatory_reference_set_count <= MAX_EVIDENCE`; the leading one is the
new Recovery-Record source Set. The bounded `root_dispositions` field does not
waive that stricter aggregate request bound, and overflow rejects Record
construction rather than truncating either collection. The object grants no
target mutation, Blob deletion, logical
fence removal, generic Storage disposition, or release before the canonical
Receipt. Here "release before the canonical Receipt" means release of an
operational Storage hold or retained byte; it does not prohibit the exact
pre-Record physical guard terminalization above. An RFC-0013
`artifact-storage-disposition/1.0` can never substitute for this embedded
patch-specific authority.

`GuardCompletion.TERMINAL_GUARD` maps `RELEASED`, `FENCED`, and `FAILED`
only to `target.guard-released`, `target.guard-fenced`, and
`target.guard-failed`, respectively, with the exact guard projection and
Event. For every Attempt release condition, its `guard` Ref equals the
terminal authority record's non-null `guard` byte-for-byte and equals the
resolved mutation or Recovery Intent's guard when that intent exists; the
terminal guard Event payload names that Ref's `id`, and replay proves the
terminal descendant from the bound Ref's immutable Sigil. The abandonment
branch additionally satisfies the embedded equalities above.
`NO_GUARD_ALLOCATED` is valid only when complete replay through
`promotion_prefix` finds the empty set of matching guard-acquire intents,
Guard projections, and guard identities for the owner, and its Sigil is:

```text
Sigil(["patch-target-guard-allocation-absence/1.0",
       promotion_prefix.head.head_sigil,
       promotion_prefix.state_sigil,
       owner_kind, owner_attempt_id,
       attempt_terminal_event.event_sigil,
       {matching_guard_acquire_intent_event_ids: [],
        matching_guard_projection_ids: [],
        matching_guard_identity_ids: []}])
```

The absence branch is legal only for a non-`PARTIAL` Promotion Outcome whose
terminal record has a null guard and whose terminal source precedes guard
allocation. Its `attempt_terminal_event` is the exact terminal Event for the
same owner and strictly precedes `inactivation_event`. Resolved Recovery and
abandonment conditions require
`TERMINAL_GUARD`. Journal suffix recovery requires only
`NOT_APPLICABLE_JOURNAL_SUFFIX`. Thus a pre-allocation terminal Attempt is no
longer forced to invent a physical guard, while any existing guard makes the
absence branch invalid.

The release-evidence policy is the exact resolved RFC-0013 policy carried by
the hold. Its nullable `deletion_grace_seconds` must be non-null to enter the
release record; null or arithmetic failure retains the hold. The replayable
retention calculation first requires the exact equality
`retention_completion.inactivation_recorded_at ==
resolve(inactivation_event).recorded_at`; a caller-selected or earlier time is
invalid. It is then:

```text
grace_due_at =
  checked_utc_add(inactivation_recorded_at,
                  policy.deletion_grace_seconds)

release_not_before =
  max(grace_due_at,
      policy.retain_until if non-null else grace_due_at)

trusted_lower_bound =
  checked_utc_sub(trusted_clock.utc,
                  trusted_clock.uncertainty_micros)

trusted_lower_bound >= release_not_before

proof_sigil =
  Sigil(["patch-operational-root-retention-completion/1.0",
         operational_root_id,
         policy.policy_id, policy.policy_sigil,
         inactivation_event.event_sigil,
         inactivation_recorded_at,
         grace_due_at, release_not_before,
         trusted_clock.observation_sigil])
```

Storage replay at `storage_prefix` must show clock state `TRUSTED`, the exact
clock observation, active hold, Set, hold Event, and policy. Overflow,
underflow, an uncertain clock, or an unverifiable observation fails closed.

`promotion_open_intent_ids` is computed only from the fixed
`promotion_prefix` replay state, never from a mutable file or current pointer:

- for `{owner_kind: PROMOTION, owner_attempt_id}`, select every `ACTIVE`
  `OperationalRoot` whose `root_kind` is `MUTATION_INTENT`, resolve its exact
  `patch-promotion-mutation-intent/1.0` control record, require
  `attempt_id == owner_attempt_id`, and emit its `intent_id`;
- for `{owner_kind: RECOVERY, owner_attempt_id}`, select every `ACTIVE`
  `RECOVERY_INTENT` root, resolve its exact
  `patch-promotion-recovery-intent/1.0`, require
  `recovery_attempt_id == owner_attempt_id`, and emit
  `recovery_intent_id`; and
- for a tail owner, select every `ACTIVE` `JOURNAL_SUFFIX` root, resolve its
  exact non-null `coordinator.replay-started` activation Event, require the
  same `tail_recovery_id`, and emit that ID.

Each result is UTF-8 byte-sorted and deduplicated. A Promotion or Recovery
intent enters this projection only with the root activated by Event 25 or 39
and exits only when Event 6 makes that exact root inactive. A tail intent
enters only with the non-null Event 2 suffix root and exits only when Event 1
completes that exact TailRecoveryIntent and inactivates the root. IDs cannot
reopen. Events 6 and 1 apply their own root revisions first, then require the
derived owner result to be `[]`; Release Evidence recomputes the same result
at its fixed prefix. Lookup absence, a missing cache entry, or scanning a
mutable stage file is never an absence proof.

For an Attempt condition, `CanonicalCompletion.COMMITTED_CANONICAL_RECORD`
resolves the exact Outcome or Recovery Receipt and one RFC-0013
`canonical_reference.committed` Event whose immutable Reference Intent
contains this root's Set. Both absence arrays are the exact empty sets of
Promotion operational intents for that owner and Storage `OPEN` reference
intents whose closure contains this root or Set. For Journal recovery both
canonical and guard branches are `NOT_APPLICABLE_JOURNAL_SUFFIX`, the tail
absence branch is selected, the completed TailRecoveryIntent verifies, and
Promotion integrity is `HEALTHY`. `owner_kind` and `owner_attempt_id` equal
the root owner and terminal authority Attempt exactly; the tail
`tail_recovery_id` equals the suffix owner, completion branch, and completed
TailRecoveryIntent. The exact branch projection is:

```text
absence_owner =
  {kind: "ATTEMPT_OPERATIONAL_INTENTS_ABSENT",
   owner_kind, owner_attempt_id}
    for ATTEMPT_OPERATIONAL_INTENTS_ABSENT

absence_owner =
  {kind: "TAIL_RECOVERY_INTENTS_ABSENT", tail_recovery_id}
    for TAIL_RECOVERY_INTENTS_ABSENT
```

No other field, spelling, or generic owner map is admitted. The absence Sigil
for either branch is:

```text
Sigil(["patch-operational-intent-absence/1.0",
       promotion_prefix.head.head_sigil,
       promotion_prefix.state_sigil,
       storage_prefix,
       operational_root_id,
       absence_owner,
       {promotion_open_intent_ids: [],
        storage_open_reference_intent_ids: []}])
```

`promotion_prefix.head` names this Promotion Journal and ends exactly at
`inactivation_event`: its `last_sequence` equals
`inactivation_event.sequence`, its `last_event_sigil` equals
`inactivation_event.event_sigil`, and replay at that sequence resolves the
same Event ID/type and yields `promotion_prefix.state_sigil`. Activation
strictly precedes inactivation. For Attempt branches, the exact Attempt
terminal Event strictly precedes the terminal guard Event when one exists,
and that guard Event strictly precedes inactivation; the legal no-guard
terminal Event also strictly precedes inactivation. For
`ABANDONED_WITH_DISPOSITION`, these are specifically
`recovery.abandoned`, the embedded terminal guard Event, then
`canonical.receipt-observed`. For the suffix branch,
`GuardCompletion.NOT_APPLICABLE_JOURNAL_SUFFIX.completion_event` equals
`inactivation_event` byte-for-byte, is `coordinator.epoch-started`, names the
completed TailRecoveryIntent, and follows its activation.

```text
activation_event.sequence <= attempt_terminal_event.sequence
attempt_terminal_event.sequence
  < guard_completion.terminal_event.sequence
  < inactivation_event.sequence
    for TERMINAL_GUARD
attempt_terminal_event.sequence < inactivation_event.sequence
    for NO_GUARD_ALLOCATED
activation_event.sequence < inactivation_event.sequence
    for NOT_APPLICABLE_JOURNAL_SUFFIX
```

Every Event in one displayed inequality has
`journal_id == operational_journal_id`; its Event ID, type, and Sigil are
resolved at that exact sequence. No receive-time or cross-journal timestamp
substitutes for these Promotion sequence predicates. Equality in the first
predicate is legal exactly when that Attempt terminal Event's tabled
protection field is this root's activation Event; otherwise activation
strictly precedes the terminal Event.

`storage_prefix` names the hold's Storage Journal, includes
`hold_set_event` at its exact sequence and Sigil, and ends before the release
Event while replay still projects the hold `ACTIVE`. For an Attempt branch it
also includes `canonical_completion.commit_event` at that Event's exact
sequence and Sigil, resolves its type as `canonical_reference.committed`, and
shows that its immutable committed Reference Intent contains this
`reference_set`; `hold_set_event.sequence <
canonical_completion.commit_event.sequence <=
storage_prefix.through_sequence`. The committed canonical Event is durable
before the Promotion Journal appends the inactivation Event. The suffix
branch has no canonical commit and admits no substitute.

The release-evidence identity is:

```text
release_material = canonical_json({
  operational_journal_id, operational_root_id, operational_root_sigil,
  operational_root_plan, hold_id,
  inactivation_event_id: inactivation_event.event_id,
  release_condition
})

release_evidence_id =
  "PREL-" + first_32_lower_hex(
    SHA-256(
      "benchwork:patch-operational-root-release-evidence:v1\0"
      || release_material))

record_sigil =
  Sigil(<complete patch-operational-root-release-evidence/1.0 with only
         record_sigil omitted>)
```

The ID is single assignment. The complete record is finalized, fsynced, and
read back before `retention.hold_released`; retry resolves exactly the same
bytes. It binds the inactive root and its plan, hold, Set, both Events,
terminal authority, canonical/guard branch, Promotion and Storage replay
prefixes, policy, trusted clock, retention calculation, and absence branch.

The later authorized `retention.hold_released` transition never invalidates
this historical proof. It only changes the current root projection.

Identity, export, and patch `$defs` are:

| `$def` | Exact required fields or branches |
| --- | --- |
| `PathScope` | `{root_kind: Enum<CRUCIBLE\|PROMOTION_TARGET>; included_paths: Set<Text<4096>,0..MAX_PATHS,value>; excluded_paths: Set<Text<4096>,0..MAX_PATHS,value>}`; every path is normalized project-relative and the two sets are disjoint as exact values |
| `PathSemantics` | `{separator: Enum<SLASH>; unicode_normalization: Enum<NFC>; case_mode: Enum<SENSITIVE\|INSENSITIVE_REJECT_COLLISIONS>; dot_segments: Enum<REJECT>; link_traversal: Enum<NOFOLLOW>; reserved_name_policy: Enum<REJECT>}` |
| `EntrySemantics` | `{supported_types: Set<Enum<FILE\|DIRECTORY\|SYMLINK>,1..3,value>; content_digest: Enum<SHA256>; executable_bit: Enum<SIGNIFICANT\|IGNORED>; symlink_target: Enum<UTF8_NOFOLLOW>; metadata_policy: Enum<TYPE_CONTENT_MODE_ONLY>}` |
| `IdentityLimits` | `{max_paths: U64 in 1..MAX_PATHS; max_total_bytes: U63; max_file_bytes: U63; max_depth: U64 in 1..4096; max_symlink_bytes: U63 in 1..4096}` |
| `PatchTreeEntry` | `DIRECTORY {path: Text<4096>; kind: Enum<DIRECTORY>; entry_sigil: Sigil}`; `FILE {path: Text<4096>; kind: Enum<FILE>; blob: Obj<StorageBlobRef>; executable: Bool}`; or `SYMLINK {path: Text<4096>; kind: Enum<SYMLINK>; target: Text<4096>; target_sigil: Sigil}` |
| `TreeIdentity` | `{manifest_sigil: Sigil; root_entry_sigil: Sigil; entry_count: U64 in 0..MAX_PATHS; total_bytes: U63}` |
| `RootIdentity` | `{root_object_sigil: Sigil; root_generation: Text<256>; topology_sigil: Sigil}` |
| `PostimageIdentity` | `{identity_profile: Ref<PBIP>; tree: Obj<TreeIdentity>; manifest_blob: BlobRef}` |
| `EntryIdentity` | `ABSENT {kind: Enum<ABSENT>}`; `FILE {kind: Enum<FILE>; blob_sigil: Sigil; size_bytes: U63; executable: Bool}`; `DIRECTORY {kind: Enum<DIRECTORY>; entry_sigil: Sigil}`; or `SYMLINK {kind: Enum<SYMLINK>; target: Text<4096>; target_sigil: Sigil}` |
| `PatchOperation` | `{path_bytes: Text<4096>; operation: Enum<ADD\|MODIFY\|DELETE\|TYPE_CHANGE>; preimage: Union<EntryIdentity>; postimage: Union<EntryIdentity>; payload_sigil: Nullable<Sigil>}`; payload is non-null exactly for a `FILE` or `SYMLINK` postimage and the operation agrees with the two branch kinds |
| `ExecutionBinding` | `{job_id: Text<128>; job_binding_sigil: Sigil; attempt_id: Text<128>; attempt_binding_sigil: Sigil; terminal_event_id: Text<128>; terminal_event_sigil: Sigil}` |
| `VcsBinding` | `{kind: Enum<GIT>; repository_identity_sigil: Sigil; commit_sigil: Sigil; tree_sigil: Sigil; submodule_policy: Enum<REJECT\|PINNED>; dirty_state: Enum<CLEAN\|CAPTURED>}` |
| `ExportSource` | `{kind: Enum<RETAINED_TERMINAL_SOURCE>; terminal_source_sigil: Sigil; execution_event_sigil: Sigil; frozen_at: Time}` |
| `BundleLimits` | `{max_paths: U64 in 1..MAX_PATHS; max_blobs: U64 in 1..MAX_BLOBS; max_total_bytes: U63; max_payload_bytes: U63}` |
| `AcceptedAgentResultBinding` | `{schema_version: V<agent-result/2.0>; task_id: Text<128>; job_id: Text<128>; attempt_id: Text<128>; agent_result_sigil: Sigil; accepted_event_id: ID<CE>; accepted_event_body_sigil: Sigil; receipt: ReceiptRef; job_outcome_id: OJID; job_outcome_sigil: Sigil; terminal_source_sigil: Sigil}` |
| `TerminalSourceBinding` | `{kind: Enum<VERIFIED>; crucible_base_identity: Text<128>; crucible_base_sigil: Sigil; terminal_source_identity: Text<128>; terminal_source_sigil: Sigil; storage_blob: Obj<StorageBlobRef>; retention_policy_sigil: Sigil; file_count: U64 in 0..MAX_PATHS; byte_count: U63; storage_status: Enum<DURABLE_VERIFIED>; verifier_evidence_sigil: Sigil}`; byte-for-byte RFC-0015's accepted RFC-0012 `VERIFIED` branch |
| `ControlBindings` | `{task_capsule_sigil: Sigil; capability_contract_sigil: Sigil; snapshot_sigil: Sigil; execution_specification_sigil: Sigil}` |
| `ExecutionBindings` | `{job_binding: Obj<ExecutionJobBinding>; selected_attempt_id: Text<128>; attempt_binding_sigil: Sigil; assurance_claim_sigil: Sigil; provenance: Obj<AgentResultProvenance>}`; `job_binding`, selected Attempt, assurance claim, and provenance equal the accepted Agent Result and its resolved Outcome byte-for-byte |
| `ExecutionJobBinding` | `{job_id: Text<128>; job_binding_sigil: Sigil}`; byte-for-byte the RFC-0015 Agent Result `job_binding` |
| `IdentityProfiles` | `{base_profile: Ref<PBIP>; postimage_profile: Ref<PBIP>; patch_semantics_sigil: Sigil}` |
| `ExporterBinding` | `{exporter_id: Text<128>; exporter_version: Text<64>; configuration_sigil: Sigil; export_evidence_sigil: Sigil}` |

For a `PatchOperation`, `ADD` is exactly `ABSENT -> non-ABSENT`, `DELETE` is
exactly `non-ABSENT -> ABSENT`, `MODIFY` keeps the same non-`ABSENT` kind,
and `TYPE_CHANGE` changes between two non-`ABSENT` kinds. A `FILE` postimage
requires `payload_sigil == postimage.blob_sigil`; a `SYMLINK` postimage
requires `payload_sigil == postimage.target_sigil`; `DIRECTORY` and `ABSENT`
postimages require null. The Patch Bundle `payloads` set is exactly one
verified `BlobRef` for each distinct `FILE` postimage Blob Sigil with matching
size and for each distinct `SYMLINK` postimage target Sigil with size equal to
the canonical UTF-8 target-byte length. The symlink Blob bytes are exactly
`UTF8(postimage.target)` and recompute to `postimage.target_sigil`; both file
and symlink payload members use media type `application/octet-stream`.
Equivalently, `payloads` is the Sigil-deduplicated set of every non-null
operation payload and has no directory, absent, or unreferenced member.
`operations` count is at most `limits.max_paths`, the distinct payload count
is at most `limits.max_blobs`, each payload size is at most
`limits.max_payload_bytes`, and the checked byte sum of the distinct payload,
rendering, and attachment union is at most `limits.max_total_bytes`. The union
of Bundle payloads, renderings, attachments, manifests, and every other
managed Blob still satisfies the aggregate `MAX_BLOBS` rule.

A `patch-promotion-checkpoint/1.0` has exactly one `CheckpointEntry` for each
`affected_paths` value and no other entry. That path set equals the
authorization's and Patch Bundle's exact operation path set; each entry
preimage equals the corresponding operation preimage and a fresh verified
target observation. `checkpoint_blob` is non-null exactly for a `FILE` or
`SYMLINK` preimage. For `FILE`, its Sigil and size equal
`preimage.blob_sigil` and `preimage.size_bytes`; for `SYMLINK`, its Sigil is
`preimage.target_sigil` and its size is the canonical UTF-8 target-byte
length. Both branches use media type `application/octet-stream`; the Blob
bytes and recomputed identity must verify those equalities.
`checkpoint_blobs` is the sorted unique union of those non-null
`checkpoint_blob` values and no others. It is therefore empty exactly when
every preimage is `ABSENT` or `DIRECTORY`; no placeholder Blob is admitted.

`PathScope` uses component-boundary prefix semantics, never lexical string
prefixes, globs, regular expressions, or implementation ignore files. A
non-root path is directly scope-admissible exactly when:

1. it is a non-empty normalized project-relative path under the logical root;
2. `included_paths` is empty, or the path is equal to or a descendant by
   complete path components of at least one included path;
3. it is neither equal to nor a descendant of any excluded path; and
4. it is neither equal to nor a descendant of `.benchwork`, `.git`, or any
   `protected_paths` member from the resolved identity profile.

Exclusion and protection win over inclusion. Empty `included_paths` means the
complete logical tree subject only to the explicit exclusions and protected
paths; it never means an empty tree. An included descendant beneath an
excluded or protected ancestor remains excluded and cannot be reintroduced.
`a` is not an ancestor of `ab`; `a` is an ancestor of `a/b`. Manifest
membership is every existing directly admissible entry plus every proper
ancestor directory required to connect one to the logical root. Such a
structural-only ancestor may lie above an included prefix, but it does not
become directly admissible and cannot itself authorize a Patch operation.
The logical root itself is not an entry. An empty selected tree is therefore
represented by an empty `entries` array and a non-null deterministic root
Sigil. Non-membership can authorize `ADD` only for a directly admissible path
under this predicate whose complete ancestor chain was verified.

Normalization first decodes well-formed UTF-8, applies NFC, and then requires
`SLASH` separators. Absolute paths, empty components, leading or trailing
slashes, repeated separators, `.` or `..`, NUL or control characters,
platform-reserved components, and an over-depth or over-byte path are rejected
before scope selection. `INSENSITIVE_REJECT_COLLISIONS` compares the
profile-pinned case-folded component sequence but retains the original NFC
bytes only after proving uniqueness. A collision, undecodable name,
unsupported entry type, mount or link traversal, incomplete directory read,
or concurrent scan mutation invalidates the whole manifest rather than
omitting one entry.

`patch-tree-manifest/1.0` is the sole complete-tree byte format in this RFC.
Its `identity_profile` resolves one exact
`patch-base-identity-profile/1.0`; the manifest's included and excluded arrays,
path semantics, entry types, and limits equal that profile byte-for-byte,
except that `scope.root_kind` is contextual: `CRUCIBLE` for Base and
post-terminal Postimage scans and `PROMOTION_TARGET` for Host target scans.
All remaining scope members are identical across those contexts. One
Base/Postimage/target comparison uses the same `identity_profile` Ref
byte-for-byte in its manifests, `PostimageIdentity`, `TargetBinding`, and
target-state evidence; only the manifest's contextual `scope.root_kind`
changes. Minting a target-only profile or changing the profile Ref does not
normalize away and cannot produce an equal `TreeIdentity`.

The entries are the complete selected projection, sorted strictly by
normalized path UTF-8 bytes and unique by path. A `FILE.blob` is the RFC-0013
SHA-256 identity and exact U63 byte size of the complete file. If executable
mode is `SIGNIFICANT`, `executable` is the independently observed bit; if it
is `IGNORED`, the canonical value is `false`. A symlink target is NFC UTF-8,
is never followed, and has:

```text
byte_sigil(bytes) =
  "sha256:" + lower_hex(SHA256(bytes))

target_sigil = byte_sigil(UTF8(target))
```

Directory identities are bottom-up and independent of traversal order.
Define:

```text
json_sigil(value) =
  byte_sigil(canonical_json(value))

file_identity(entry) =
  json_sigil(["patch-tree-file-entry/1.0",
              entry.path, entry.blob, entry.executable])

symlink_identity(entry) =
  json_sigil(["patch-tree-symlink-entry/1.0",
              entry.path, entry.target, entry.target_sigil])

directory_identity(path, children) =
  json_sigil(["patch-tree-directory-entry/1.0",
              path,
              [[child_basename, child_kind, child_identity], ...]])
```

`children` contains every and only immediate child, sorted strictly by
normalized basename UTF-8 bytes. A file or symlink child uses the first or
second identity above; a directory child uses its recursively computed
`directory_identity`. Every `DIRECTORY.entry_sigil` equals that value.
`root_entry_sigil` is `directory_identity("", root_children)`. The empty tree
therefore has the fixed identity of the empty root-child array.

`entry_count == len(entries)`. `file_count` is the checked count of `FILE`
plus `SYMLINK` entries. `total_bytes` is the checked sum of every file size
plus every symlink-target UTF-8 byte length. Each component and aggregate
must satisfy the resolved `IdentityLimits`; overflow, a missing entry, or a
count mismatch rejects the manifest.

The cross-root content identity deliberately normalizes only the contextual
root kind:

```text
manifest_sigil =
  json_sigil([
    "patch-tree-manifest-identity/1.0",
    identity_profile,
    ["scope", scope.included_paths, scope.excluded_paths],
    path_semantics,
    entries,
    entry_count,
    file_count,
    total_bytes,
    root_entry_sigil
  ])
```

`record_sigil` is the ordinary self-Sigil over the complete closed
`patch-tree-manifest/1.0` with only `record_sigil` omitted. Thus a Crucible and
Promotion Target with identical governed content have the same
`manifest_sigil` and `TreeIdentity`, while their complete manifest records
and record Sigils retain the different contextual `root_kind`.

Every `TreeIdentity` is valid only with a resolved complete manifest whose
`manifest_sigil`, `root_entry_sigil`, `entry_count`, and `total_bytes` equal
it byte-for-byte. A Base or Postimage `manifest_blob` is exactly the canonical
JSON bytes of that complete manifest including `record_sigil`;
`manifest_blob.sigil == byte_sigil(bytes)`,
`manifest_blob.size_bytes == len(bytes)`, and `manifest_blob.media_type` is
the constant `application/vnd.benchwork.patch-tree-manifest+json`. A
`patch-target-state-evidence/1.0` record includes exactly one such matching
manifest Blob among `evidence_blobs`; any other evidence Blobs are distinct.
A `VerificationBinding.evidence_sigil` resolves verifier evidence that binds
that same manifest Blob and complete scan.

For the terminal Postimage, projection from RFC-0012 is exact. The exporter
resolves the accepted `TerminalSourceBinding` by
`(terminal_source_identity, terminal_source_sigil)` to one
`benchwork-source-tree/1.0` and requires:

```text
terminal_source_identity == source_tree.source_tree_id
terminal_source_sigil == source_tree.source_tree_sigil
terminal_source.storage_blob == source_tree.bundle_blob
source_tree.manifest.format_version == BENCHWORK_SOURCE_TREE_V1
source_tree.manifest.crucible_base_identity ==
  terminal_source.crucible_base_identity
source_tree.manifest.crucible_base_sigil ==
  terminal_source.crucible_base_sigil
source_tree.manifest.file_count == terminal_source.file_count
source_tree.manifest.byte_count == terminal_source.byte_count
```

The deterministic RFC-0012 bundle decoder must reproduce the source manifest
and every file byte, and its recomputed Blob Sigil and size must equal
`source_tree.bundle_blob`. The resolved Proposal postimage profile must have
the same included/excluded sets and `path_semantics` as the source manifest.
For this exact projection its `entry_semantics` must use `SHA256`,
`SIGNIFICANT`, `UTF8_NOFOLLOW`, and `TYPE_CONTENT_MODE_ONLY`, must list every
observed entry kind, and its limits must admit every observed path, file,
symlink, aggregate count, byte count, and depth. In particular,
`executable_bit: IGNORED` rejects this projection instead of rewriting a
source `executable` value.
The derived `patch-tree-manifest/1.0` has `root_kind: CRUCIBLE`; it copies
those sets, semantics, entry fields, file count, and byte count exactly,
renaming only `byte_count` to `total_bytes`. Every copied symlink and directory
Sigil is independently recomputed by the rules above and must already equal
the RFC-0012 value; the new root, manifest, and record Sigils are then
computed. The Postimage `TreeIdentity` and manifest Blob resolve that derived
record. A differing bundle Blob, source-manifest Sigil, path set, entry,
count, profile, derived manifest, or Postimage identity quarantines the
export. The source bundle and derived manifest Blob are distinct protected
Blobs; neither may substitute for the other.

Validation and target-observation `$defs` are:

| `$def` | Exact required fields or branches |
| --- | --- |
| `ValidationRequirement` | `{check_id: Text<128>; check_type: Enum<COMMAND\|STATIC_ANALYSIS\|TEST\|LOCAL_REVIEW\|EXTERNAL_REVIEW\|CUSTOM>; required_status: Enum<PASS>; assurance_level: Text<64>; validator_profile_sigil: Sigil; environment_profile_sigil: Sigil; timeout_seconds: U64 in 1..86400}` |
| `AssuranceRequirement` | `{minimum_level: Text<64>; assurance_profile_sigil: Sigil; control_evidence_profile_sigil: Sigil}` |
| `IndependenceRule` | `{mode: Enum<SAME_VALIDATOR_ALLOWED\|DISTINCT_VALIDATOR\|DISTINCT_CIRCLE\|EXTERNAL>; minimum_distinct_validators: U64 in 1..MAX_EVIDENCE}` |
| `EnvironmentRule` | `{rule_id: Text<128>; kind: Enum<REQUIRE\|FORBID\|MATCH>; value_sigil: Sigil; required: Bool}` |
| `ValidationLimits` | `{max_checks: U64 in 1..MAX_EVIDENCE; max_log_refs: U64 in 0..MAX_LOG_REFS; max_result_artifacts: U64 in 0..MAX_EVIDENCE; max_runtime_seconds: U64 in 1..86400}` |
| `ValidationCheck` | `{check_id: Text<128>; check_type: Enum<COMMAND\|STATIC_ANALYSIS\|TEST\|LOCAL_REVIEW\|EXTERNAL_REVIEW\|CUSTOM>; declared_scope_sigil: Sigil; expected_result_sigil: Sigil}` |
| `ValidatorBinding` | `{validator_id: Text<128>; validator_kind: Enum<AGENT\|HUMAN\|SERVICE>; circle_id: Nullable<Text<128>>; identity_sigil: Sigil; independence_evidence_sigil: Sigil}` |
| `ValidationExecution` | `{job_outcome: Obj<ValidationJobOutcomeBinding>; attempt_id: Text<128>; attempt_binding_sigil: Sigil; attempt_terminal_event_id: Text<128>; attempt_terminal_event_sigil: Sigil; execution_specification_sigil: Sigil; worker_session_binding: Union<OutcomeWorkerSessionBinding>; authority_binding: Union<OutcomeAuthorityBinding>; assurance_context_binding: Union<OutcomeAssuranceContextBinding>; assurance_claim_sigil: Sigil; dependency_set_sigil: Sigil; environment_sigil: Sigil; configuration_sigil: Sigil; input_set_sigil: Sigil}`; every execution, authority, fence, backend, requested-assurance, realized-claim, and terminal field is copied from and revalidated against the resolved Outcome |
| `ExitResult` | `{kind: Enum<EXITED\|SIGNALED\|NOT_RUN>; exit_code: Nullable<U64>; signal: Nullable<Text<64>>; evidence_sigil: Sigil}`; `EXITED` alone has an exit code, `SIGNALED` alone has a signal, and `NOT_RUN` has neither |
| `VerificationBinding` | `{verified: Bool; tree: Obj<TreeIdentity>; evidence_sigil: Sigil}` |
| `VerifierBinding` | `{verifier_id: Text<128>; verifier_version: Text<64>; configuration_sigil: Sigil; assurance_sigil: Sigil}` |
| `ScanBounds` | `{max_paths: U64 in 1..MAX_PATHS; max_total_bytes: U63; max_depth: U64 in 1..4096; observed_paths: U64 in 0..MAX_PATHS; observed_bytes: U63}`; observed values do not exceed their maxima |

Within one Validation Policy, `required_checks` and `optional_checks` are
disjoint by `check_id`; a repeated ID with identical or different bytes is
invalid. Their aggregate cardinality is at most
`limits.max_checks`, and `limits.max_checks <= MAX_EVIDENCE`. The selected
Evidence check-ID set equals every required check ID plus any chosen subset of
optional check IDs. Each selected ID has exactly one eligible `PASS` Evidence
record using the listed check type and installed profiles; required IDs cannot
be omitted, while unchosen optional IDs have no Evidence record.

Adapter, authorization, and target `$defs` are:

| `$def` | Exact required fields or branches |
| --- | --- |
| `PlatformProfile` | `{os_family: Enum<POSIX\|WINDOWS>; filesystem_sigil: Sigil; path_profile_sigil: Sigil; atomic_replace_scope: Enum<FULL_TREE\|PER_ENTRY>; conformance_suite_sigil: Sigil}` |
| `DeadlinePolicy` | `{preview_lifetime_seconds: U64 in 1..86400; guard_lifetime_seconds: U64 in 1..3600; guard_renewal_interval_seconds: U64 in 1..1800; clock_uncertainty_tolerance_seconds: U64 in 0..300; trusted_utc_source_profile_sigil: Sigil; monotonic_source_profile_sigil: Sigil; suspend_policy: Enum<FENCE_ON_UNPROVABLE\|COUNT_TRUSTED_SUSPEND>}` |
| `GuardBackend` | `{backend_id: Text<128>; profile_sigil: Sigil; cas_semantics: Enum<EXACT_GENERATION>; readback_semantics: Enum<LINEARIZABLE>; durable_tombstones: True; durable_fence_floor: True; generation_successor_profile_sigil: Sigil; max_active_guards: U64 in 1..MAX_ACTIVE_GUARDS}` |
| `MutationSemantics` | `{descriptor_relative_nofollow: True; preimage_compare_and_swap: True; topology_compare_and_swap: True; mode: Enum<FULL_TREE_ATOMIC_CAS\|PER_ENTRY_GENERATIONAL_CAS>; atomicity: Enum<FULL_TREE\|TARGET_WIDE_GENERATION>; per_step_receipts: Bool}`; full-tree mode requires `FULL_TREE` and false receipts, per-entry mode requires `TARGET_WIDE_GENERATION` and true receipts |
| `RecoverySemantics` | `{actions: Set<Enum<RESTORE_BASE\|ACCEPT_POSTIMAGE\|ABANDON>,3..3,value>; checkpoint_required: True; verifier_readback_required: True; partial_fence_required: True}` |
| `AdapterLimits` | `{max_paths: U64 in 1..MAX_PATHS; max_total_bytes: U63; max_operation_bytes: U63; max_backend_retries: U64 in 0..64; max_active_guards: U64 in 1..MAX_ACTIVE_GUARDS}` |
| `TargetBinding` | `{target_id: ID<PT>; target_class: Enum<WORKTREE\|DIRECTORY>; identity_profile: Ref<PBIP>; root_identity: Obj<RootIdentity>; selection_authorization_sigil: Sigil}` |
| `LogicalFencePromotionRecord` | `{kind: constant "PROMOTION_OUTCOME"; outcome_id: ID<PO>; outcome_sigil: Sigil; receipt: ReceiptRef}` |
| `LogicalFenceRecoveryRecord` | `{kind: constant "RECOVERY_RECORD"; recovery_record_id: ID<PRR>; recovery_record_sigil: Sigil; receipt: ReceiptRef}` |
| `LogicalFenceCanonicalRecord` | exactly one `LogicalFencePromotionRecord` or `LogicalFenceRecoveryRecord`, selected by `kind` |
| `RecoveryLineageBinding` | `{target_id: ID<PT>; logical_fence_generation: U64; logical_fence_revision: U64; logical_fence_sigil: Sigil; predecessor_head_sigil: Sigil; predecessor: Union<PROMOTION_PARTIAL {kind: constant "PROMOTION_PARTIAL"; parent_attempt_id: ID<PAT>; outcome_id: ID<PO>; outcome_sigil: Sigil; receipt: ReceiptRef}\|RECOVERY_TERMINAL {kind: constant "RECOVERY_TERMINAL"; parent_attempt_id: ID<PAT>; recovery_attempt_id: ID<PRA>; terminal_status: Enum<STALE\|FAILED\|PARTIAL\|CANCELLED>; recovery_record_id: ID<PRR>; recovery_record_sigil: Sigil; receipt: ReceiptRef}>}` |
| `AbandonedLineageBinding` | `{target_id: ID<PT>; reentry_proposal: Ref<PP>; logical_fence_generation: U64; logical_fence_revision: U64; logical_fence_sigil: Sigil; abandonment_head_sigil: Sigil; recovery_attempt_id: ID<PRA>; recovery_record_id: ID<PRR>; recovery_record_sigil: Sigil; recovery_record_receipt: ReceiptRef; abandonment_disposition_sigil: Sigil; observed_identity_sigil: Sigil; target_content_generation: Text<256>}` |
| `RecoverySelection` | `{parent_attempt_id: ID<PAT>; parent_outcome_receipt: ReceiptRef; checkpoint: Ref<PCK>; mutation_intent: Ref<PMI>; action: Enum<RESTORE_BASE\|ACCEPT_POSTIMAGE\|ABANDON>; lineage: Obj<RecoveryLineageBinding>}` |
| `ValidationSelection` | `{policy: Ref<PVP>; evidence: Set<Ref<PVE>,1..MAX_EVIDENCE,id>}` |
| `ActorBinding` | `{actor_id: Text<128>; actor_kind: Enum<HUMAN\|SERVICE>; authentication_context_sigil: Sigil}` |
| `ChronicleActor` | Exact RFC-0001 `actor/1.0` at `https://benchwork.dev/schemas/actor/1.0`: `{actor_id, actor_type, host, authenticated_by}` with no local widening or additional field |
| `HostBinding` | `{host_id: Text<128>; host_instance_sigil: Sigil; platform_sigil: Sigil; interactive_session_sigil: Sigil}` |

Mutation, outcome, and recovery `$defs` are:

| `$def` | Exact required fields or branches |
| --- | --- |
| `CheckpointEntry` | `{path_bytes: Text<4096>; preimage: Union<EntryIdentity>; checkpoint_blob: Nullable<BlobRef>; verification_sigil: Sigil}`; Blob is non-null exactly for a file or symlink preimage |
| `TopologyPlan` | `{mode: Enum<FULL_TREE_ATOMIC_CAS\|PER_ENTRY_GENERATIONAL_CAS>; target_wide_generation: Text<256>; root_identity: Obj<RootIdentity>; ancestor_set_sigil: Sigil; operation_order: List<Text<4096>,1..MAX_PATHS>; plan_sigil: Sigil}`; operation order is duplicate-free and contains the exact affected-path set |
| `AncestorIdentity` | `{path_bytes: Text<4096>; object_identity_sigil: Sigil; generation: Text<256>}` |
| `VerificationMethod` | `{kind: Enum<FULL_TREE_IDENTITY>; identity_profile: Ref<PBIP>; expected_tree: Obj<TreeIdentity>; verifier_profile_sigil: Sigil}` |
| `OutcomeTimes` | `{created_at: Time; mutation_started_at: Nullable<Time>; verification_started_at: Nullable<Time>; terminal_at: Time}`; non-null times are non-decreasing |
| `PathObservation` | `{path_bytes: Text<4096>; expected_preimage_sigil: Sigil; observed_preimage_sigil: Sigil; expected_postimage_sigil: Sigil; observed_postimage_sigil: Sigil; status: Enum<MATCH\|MISMATCH>}` |
| `AdapterReceiptEvidence` | exactly one of `FULL_TREE_ATOMIC_CAS {kind: constant "FULL_TREE_ATOMIC_CAS"; transaction_id_sigil: Sigil; adapter: Ref<PPA>; mutation_intent: Ref<PMI>; operation_sigil: Sigil; guard: Ref<PG>; fencing_generation: U64; fence_floor: U64; descriptor_root_identity: Obj<RootIdentity>; before_identity: Obj<TreeIdentity>; after_identity: Obj<TreeIdentity>; before_generation: Text<256>; after_generation: Text<256>; committed_at: Time; durability_evidence_sigil: Sigil; readback_evidence_sigil: Sigil}` or `PER_ENTRY_GENERATIONAL_CAS {kind: constant "PER_ENTRY_GENERATIONAL_CAS"; transaction_id_sigil: Sigil; adapter: Ref<PPA>; mutation_intent: Ref<PMI>; operation_sigil: Sigil; guard: Ref<PG>; fencing_generation: U64; fence_floor: U64; descriptor_root_identity: Obj<RootIdentity>; step_ordinal: U64 in 1..MAX_EVIDENCE; path_bytes: Text<4096>; preimage: Union<EntryIdentity>; postimage: Union<EntryIdentity>; before_generation: Text<256>; after_generation: Text<256>; committed_at: Time; durability_evidence_sigil: Sigil; readback_evidence_sigil: Sigil}` |
| `AdapterWriteEvidence` | `{mode: Enum<FULL_TREE_ATOMIC_CAS\|PER_ENTRY_GENERATIONAL_CAS>; transaction_id_sigil: Sigil; receipt_sigils: Set<Sigil,1..MAX_EVIDENCE,value>; before_generation: Text<256>; after_generation: Text<256>; causal_evidence_sigil: Sigil}` |

`AdapterLimits.max_paths` is at most `MAX_EVIDENCE` for
`PER_ENTRY_GENERATIONAL_CAS`; only `FULL_TREE_ATOMIC_CAS` may advertise a
value through `MAX_PATHS`. Prepare rejects a Preview whose affected-path count
exceeds the selected Adapter limit. Full-tree `AdapterWriteEvidence` has
exactly one transaction receipt. Per-entry evidence has exactly one receipt
per affected path, and its count therefore fits `1..MAX_EVIDENCE`; the Sigil
array remains value-sorted, while each resolved receipt binds one unique step
ordinal and path and the resolved set covers `TopologyPlan.operation_order`
exactly. Neither truncation, duplication, nor an omitted receipt is legal.

Every `receipt_sigils` member resolves through the protecting Evidence
Manifest to one committed Blob with media type
`application/vnd.benchwork.patch-adapter-write-receipt+json`. Its bytes are
the canonical JSON of exactly one `AdapterReceiptEvidence` branch, its Sigil
is the byte Sigil of those bytes, and its size is their exact length.
Full-tree mode admits one full-tree branch whose before/after identities equal
Base/Postimage. Per-entry branches have ordinals `1..N`, paths in exact
`TopologyPlan.operation_order`, and preimage/postimage values equal the
corresponding Patch Operation. Their generation chain is contiguous; its first
and last values equal the aggregate evidence's before/after generations.
Every branch copies the aggregate transaction ID, Adapter, Mutation Intent,
operation Sigil, Guard, fence values, and descriptor-root identity
byte-for-byte.

```text
causal_evidence_sigil =
  Sigil(["patch-adapter-write-causality/1.0",
         mode, transaction_id_sigil, receipt_sigils,
         before_generation, after_generation])
```

The complete `AdapterWriteEvidence` canonical JSON is itself one committed
Blob with media type
`application/vnd.benchwork.patch-adapter-write-evidence+json`; its Blob Sigil
is `adapter_write_evidence_sigil`. A terminal or verification Event carrying
that field must name this exact aggregate Blob. Its Evidence Manifest and the
later canonical Outcome Reference Set contain both the aggregate Blob and
every receipt Blob, without an omitted or extra receipt.

Replay and inspection `$defs` are:

| `$def` | Exact required fields or branches |
| --- | --- |
| `CoordinatorProjection` | `{coordinator_id: ID<PC>; state: Enum<NONE\|REPLAYING\|ACTIVE\|READ_ONLY_FAILED>; current_epoch: U64; revision: U64}`; initial replay state is `NONE`, epoch 0, revision 0 |
| `ClockProjection` | `{state: Enum<UNINITIALIZED\|TRUSTED\|UNCERTAIN>; last_trusted_utc: Nullable<Time>; anchor_evidence_sigil: Nullable<Sigil>; revision: U64}`; the two nullable fields are both null exactly in `UNINITIALIZED` |
| `PreviewProjection` | `{preview_id: ID<PRV>; preview_sigil: Sigil; state: Enum<PREPARED\|DECIDING\|AUTHORIZED\|REJECTED\|DECISION_FAILED\|EXPIRED>; expires_at: Time; token_state: Enum<AVAILABLE\|CONSUMED\|UNAVAILABLE>; idempotency_key_sigil: Sigil; revision: U64}` |
| `DecisionProjection` | `{preview_id: ID<PRV>; state: Enum<PENDING\|AUTHORIZED\|REJECTED\|FAILED>; redacted_request_sigil: Sigil; idempotency_key_sigil: Sigil; failure_id: Nullable<ID<PDF>>; receipt: Nullable<ReceiptRef>; revision: U64}`; exactly one terminal result field is non-null for its matching state |
| `GuardProjection` | `{guard: Obj<patch-promotion-target-guard/1.0>; last_intent_event_id: Nullable<ID<PJE>>; last_intent_event_sigil: Nullable<Sigil>; last_backend_request_sigil: Nullable<Sigil>; last_readback_evidence_sigil: Nullable<Sigil>}` |
| `PromotionProjection` | `{attempt: Obj<patch-promotion-attempt/1.0>; checkpoint: Nullable<Ref<PCK>>; mutation_intent: Nullable<Ref<PMI>>; terminal_event_id: Nullable<ID<PJE>>; terminal_event_sigil: Nullable<Sigil>}` |
| `RecoveryProjection` | `{attempt: Obj<patch-promotion-recovery-attempt/1.0>; recovery_intent: Nullable<Ref<PRI>>; terminal_event_id: Nullable<ID<PJE>>; terminal_event_sigil: Nullable<Sigil>}` |
| `IdempotencyBinding` | `{scope: Enum<PREPARE\|DECISION>; key_sigil: Sigil; request_sigil: Sigil; state: Enum<BOUND\|PENDING\|SUCCEEDED\|FAILED>; result_sigil: Nullable<Sigil>}`; `PREPARE` uses only `BOUND` with the non-null Preview Sigil result; `DECISION` uses `PENDING -> SUCCEEDED\|FAILED`, null only while pending and otherwise the Receipt or failure-detail Sigil; Outcome request idempotency lives in the immutable canonical-request slot rather than this Journal projection |
| `CanonicalLinkProjection` | `{kind: Enum<AUTHORIZATION\|REJECTION\|PROPOSAL\|VALIDATION\|PROMOTION_OUTCOME\|RECOVERY_RECORD>; subject_id: Text<128>; submission_event_id: Nullable<ID<PJE>>; canonical_event_id: ID<CE>; event_body_sigil: Sigil; receipt: ReceiptRef; request_sigil: Sigil; canonical_commit_event: Obj<StorageEventRef>; resulting_chronicle_head_sigil: Sigil; state: constant "OBSERVED"; revision: U64}` |
| `LogicalFenceHead` | exactly one of `PROMOTION_PARTIAL {kind: constant "PROMOTION_PARTIAL"; parent_attempt_id: ID<PAT>; terminal_event: Obj<PromotionEventRef>; observed_identity_sigil: Sigil; target_content_generation: Text<256>; logical_fence_generation: U64; canonical_record: Nullable<Obj<LogicalFencePromotionRecord>>; head_sigil: Sigil}`, `RECOVERY_TERMINAL {kind: constant "RECOVERY_TERMINAL"; parent_attempt_id: ID<PAT>; recovery_attempt_id: ID<PRA>; predecessor_head_sigil: Sigil; terminal_status: Enum<BASE_RESTORED\|POSTIMAGE_ACCEPTED\|ABANDONED\|STALE\|FAILED\|PARTIAL\|CANCELLED>; terminal_event: Obj<PromotionEventRef>; observed_identity_sigil: Sigil; target_content_generation: Text<256>; logical_fence_generation: U64; canonical_record: Nullable<Obj<LogicalFenceRecoveryRecord>>; head_sigil: Sigil}`, or `ABANDONED_REENTRY_RESOLVED {kind: constant "ABANDONED_REENTRY_RESOLVED"; attempt_id: ID<PAT>; terminal_status: Enum<APPLIED\|RECOVERED_POSTIMAGE_OBSERVED\|ALREADY_APPLIED>; terminal_event: Obj<PromotionEventRef>; abandoned_lineage: Obj<AbandonedLineageBinding>; observed_identity_sigil: Sigil; target_content_generation: Text<256>; logical_fence_generation: U64; canonical_record: Obj<LogicalFencePromotionRecord>; head_sigil: Sigil}`; every `head_sigil` covers the complete selected branch with only itself omitted |
| `LogicalPartialFenceProjection` | `{target_id: ID<PT>; state: Enum<ACTIVE\|ABANDONED\|CLEAR>; generation: U64; root_attempt_id: ID<PAT>; root_outcome_receipt: Nullable<ReceiptRef>; checkpoint: Ref<PCK>; mutation_intent: Ref<PMI>; head: Obj<LogicalFenceHead>; unresolved_recovery_attempt_id: Nullable<ID<PRA>>; revision: U64; logical_fence_sigil: Sigil}`; `logical_fence_sigil` covers every other field |
| `LogicalFenceReceiptTransition` | exactly one of `PROMOTION_PARTIAL_CANONICALIZED {kind: constant "PROMOTION_PARTIAL_CANONICALIZED"; target_id: ID<PT>; logical_fence_generation: U64; parent_attempt_id: ID<PAT>; terminal_event: Obj<PromotionEventRef>; canonical_record: Obj<LogicalFencePromotionRecord>}`, `RECOVERY_RECORD_CANONICALIZED {kind: constant "RECOVERY_RECORD_CANONICALIZED"; target_id: ID<PT>; logical_fence_generation: U64; parent_attempt_id: ID<PAT>; recovery_attempt_id: ID<PRA>; terminal_status: Enum<BASE_RESTORED\|POSTIMAGE_ACCEPTED\|ABANDONED\|STALE\|FAILED\|PARTIAL\|CANCELLED>; terminal_event: Obj<PromotionEventRef>; canonical_record: Obj<LogicalFenceRecoveryRecord>; next_state: Enum<ACTIVE\|ABANDONED\|CLEAR>}`, or `ABANDONED_REENTRY_RESOLVED {kind: constant "ABANDONED_REENTRY_RESOLVED"; target_id: ID<PT>; logical_fence_generation: U64; attempt_id: ID<PAT>; terminal_status: Enum<APPLIED\|RECOVERED_POSTIMAGE_OBSERVED\|ALREADY_APPLIED>; terminal_event: Obj<PromotionEventRef>; abandoned_lineage: Obj<AbandonedLineageBinding>; canonical_record: Obj<LogicalFencePromotionRecord>}` |
| `OperationalRoot` | `{root_id: ID<PROOT>; root_plan: Ref<PORP>; root_kind: Enum<CHECKPOINT\|MUTATION_INTENT\|RECOVERY_INTENT\|EVIDENCE\|JOURNAL_SUFFIX>; payload_field: Enum<CHECKPOINT_PROTECTION\|INTENT_PROTECTION\|PRIOR_STEP_PROTECTION\|EVIDENCE_PROTECTION\|SUFFIX_EVIDENCE_PROTECTION>; control_record_id: Text<128>; control_record_sigil: Sigil; reference_set: Obj<ReferenceSetRef>; protection: Obj<HoldBinding>; visible_event_id: ID<PJE>; visible_event_sigil: Sigil; last_transition_event_id: ID<PJE>; last_transition_event_sigil: Sigil; state: Enum<ACTIVE\|INACTIVE>; revision: U64; root_sigil: Sigil}`; `root_sigil` covers every other member; transition fields equal visibility at `ACTIVE` revision 1 creation and the exact receipt/epoch event at `INACTIVE` revision 2 |
| `JournalPrefix` | `{head: Obj<HeadRef>; state_sigil: Sigil}`; state Sigil equals deterministic replay through the referenced Head |
| `GuardRecoveryStart` | `{guard_id: ID<PG>; origin_state: Enum<ACQUIRING\|HELD\|RENEWING\|RELEASING\|FENCING\|RECOVERING>; guard_sigil: Sigil; last_physical_intent_event_id: Nullable<ID<PJE>>; last_physical_intent_event_sigil: Nullable<Sigil>; backend_request_sigil: Nullable<Sigil>; prior_backend_generation: Nullable<Text<256>>; intended_backend_generation: Nullable<Text<256>>; prior_fence_floor: U64; intended_fence_floor: U64; last_readback_evidence_sigil: Nullable<Sigil>}` |
| `PatchErrorDetails` | `{error_id: ID<PER>; retryable: Bool; entity_kind: Nullable<Enum<PROPOSAL\|PREVIEW\|DECISION\|GUARD\|PROMOTION_ATTEMPT\|RECOVERY_ATTEMPT\|REFERENCE_INTENT\|JOURNAL>>; entity_id: Nullable<Text<128>>; state: Nullable<Text<64>>; expected_sigil: Nullable<Sigil>; observed_sigil: Nullable<Sigil>; due_at: Nullable<Time>; idempotency_key_sigil: Nullable<Sigil>; failure_id: Nullable<ID<PDF>>; reason_code: PatchReasonCode; evidence_sigils: Set<Sigil,0..16,value>; detail_sigil: Sigil}` |
| `TailRecoveryIntent` | `{format_version: V<1.0>; recovery_id: ID<PTRI>; journal_id: ID<PJ>; old_head: Obj<HeadRef>; observed_eof: U64; suffix_kind: Enum<COMPLETE\|TORN_EOF>; last_complete_offset: U64; target_head: Obj<HeadRef>; suffix_evidence_blob: BlobRef; evidence_protection: Obj<HoldBinding>; stage: Enum<PROTECTED\|FRAMES_STABILIZED\|HEAD_INSTALLED\|REPLAY_EVENT_STAGED\|REPLAY_EVENT_COMMITTED\|COMPLETED>; replay_event_id: Nullable<ID<PJE>>; replay_event_sigil: Nullable<Sigil>; replay_event_head: Nullable<Obj<HeadRef>>; completion_mode: Nullable<Enum<NORMAL_REPLAY\|READ_ONLY_PREFIX>>; revision: U64; previous_record_sigil: Nullable<Sigil>; record_sigil: Sigil}` |

The empty Journal has one exact State, with the configured `journal_id`:

```text
schema_version = "1.0"
journal_id = configured Journal ID
through_sequence = 0
through_offset = 0
coordinator = {
  coordinator_id: "PC-UNINITIALIZED",
  state: "NONE",
  current_epoch: 0,
  revision: 0
}
clock = {
  state: "UNINITIALIZED",
  last_trusted_utc: null,
  anchor_evidence_sigil: null,
  revision: 0
}
previews = []
decision_submissions = []
guards = []
promotion_attempts = []
recovery_attempts = []
idempotency_bindings = []
canonical_links = []
logical_partial_fences = []
operational_roots = []
integrity_state = "HEALTHY"
```

Its `state_sigil` is the ordinary contract self-Sigil. The empty Head has
`schema_version: "1.0"`, the same configured `journal_id`,
`coordinator_epoch: 0`, zero count/sequence/offset and `head_generation: 0`,
null last Event Sigil, `frames_file_sigil_prefix` equal to the prefixed
SHA-256 of the empty byte string, and `projected_state_sigil` equal to that
exact State. Its `head_sigil` is the ordinary contract self-Sigil.

For every Event except rows 1 through 3, outer `coordinator_id` equals the
source projection's non-placeholder ID and outer `coordinator_epoch` equals
`source.current_epoch`; the destination preserves both. Row 2 has
`prior_epoch == source.current_epoch`, outer epoch
`== recovery_epoch == checked(prior_epoch + 1)`, and sets destination
Coordinator ID equal to the outer `coordinator_id`, epoch to
`recovery_epoch`, state to `REPLAYING`, and revision to prior + 1. Row 1 from
`NONE` has `prior_epoch: 0`, outer epoch `== new_epoch: 1`, requires a
non-placeholder outer `coordinator_id`, and copies that ID to the destination;
from `REPLAYING`, its outer ID equals the source ID and
`outer epoch == new_epoch == source.current_epoch ==
checked(prior_epoch + 1)`. It sets state `ACTIVE` and increments revision but
never increments the epoch a second time.

Row 3 from `NONE` uses outer epoch 1, requires a non-placeholder outer
`coordinator_id`, and copies that ID to the destination; from every other
source its outer ID/epoch equal the source. It sets state
`READ_ONLY_FAILED`, preserves the selected epoch, and increments Coordinator
revision. Top-level `integrity_state` is `READ_ONLY_FAILED` exactly when the
Coordinator state is so, and otherwise `HEALTHY`. Clock revision starts at 0
and increments exactly once only in rows 1, 4, and 5; their destination UTC
and anchor fields are the exact payload values tabled below.

After every committed Event, Head `coordinator_epoch` equals destination
`coordinator.current_epoch`; `projected_state_sigil` equals the complete
destination State; count, sequence, offset, last Event Sigil, and prefix Sigil
cover that same frame prefix. For a non-empty prefix,
`destination.through_sequence == event.sequence ==
covering_head.last_sequence == covering_head.event_count` and
`destination.through_offset == covering_head.committed_offset`; for the empty
prefix all four values are zero as defined above. The covering Head's
`head_generation` is `checked(prior_head.head_generation + 1)`. A
tail-recovery `target_head` is the single successor of its `old_head`, and the
replay Event's covering Head is the single successor of that `target_head`; a
different generation is invalid. An Event, State, or Head with a different
Coordinator ID/epoch, revision, clock revision, integrity value, through
sequence/offset, projected State Sigil, or Head generation is invalid.

The Preview token-state replay matrix is exhaustive. Row 7 creates
`PREPARED/AVAILABLE`. Row 8 with `decision: AUTHORIZE` changes
`AVAILABLE -> CONSUMED` when the single-use token is accepted into the durable
submission; row 8 with `decision: REJECT` changes
`AVAILABLE -> UNAVAILABLE` because that branch accepts no token and
terminalizes its availability. Row 9 preserves the branch-selected value:
`CONSUMED` for `AUTHORIZE`, `UNAVAILABLE` for `REJECT`. Row 6
`AUTHORIZATION` requires and preserves `CONSUMED`; row 6 `REJECTION` requires
and preserves `UNAVAILABLE`. Row 10 changes `AVAILABLE -> UNAVAILABLE`.
No other row changes a Preview token state. A still-valid Prepare retry that
may return the protected plaintext requires exactly `PREPARED/AVAILABLE`,
the same binding and idempotency key, a trusted clock, and a deadline not yet
due.

Every `canonical.receipt-observed` creates one immutable
`CanonicalLinkProjection` at revision 1. Its fields copy the closed payload
byte-for-byte, and:

```text
receipt.event_id == canonical_event_id
receipt.event_body_sigil == event_body_sigil
```

The kind matrix is exhaustive:

| Kind | Exact `subject_id` | Exact `submission_event_id` |
| --- | --- | --- |
| `PROPOSAL` | accepted `proposal.proposal_id` | null |
| `VALIDATION` | accepted `evidence.evidence_id` | null |
| `AUTHORIZATION` | accepted `preview.id` | exact `preview.decision-submission-started` Event |
| `REJECTION` | accepted `preview.id` | exact `preview.decision-submission-started` Event |
| `PROMOTION_OUTCOME` | accepted `outcome.outcome_id` | `outcome.terminal_journal_event_id` |
| `RECOVERY_RECORD` | accepted `recovery_record.recovery_record_id` | `recovery_record.terminal_journal_event_id` |

The observation Event's `causation_event_id` equals every non-null
`submission_event_id` and is null otherwise. `canonical_commit_event` resolves
exactly one RFC-0013 `canonical_reference.committed` Event. Its Reference
Intent and resolved final request have
`transition_request_sigil == request_sigil`; the Intent ID/Sigil equal the
Chronicle payload's `canonical_reference`; and its `chronicle_commit` copies
this exact Chronicle Event, Receipt, and resulting Head. Therefore:

```text
resulting_chronicle_head_sigil =
  Sigil(["patch-resulting-chronicle-head/1.0",
         canonical_commit_event.payload.chronicle_commit.head])
```

A duplicate `(kind, subject_id)`, a different request/commit/Event/Receipt, or
another Storage commit is an integrity conflict. For operational-root Release
Evidence, `canonical_completion.receipt`, `reference_intent`, and
`commit_event` equal this exact link's Receipt, resolved Intent reference, and
`canonical_commit_event` byte-for-byte. A later Storage Head lookup cannot
substitute for that causal link.

The Prepare idempotency projection is created only by `preview.prepared` with
`request_sigil == prepare_request_sigil`, state `BOUND`, and
`result_sigil == preview.preview_sigil`. A Decision projection is created only
by `preview.decision-submission-started` with the exact redacted request and a
null result. Event 6 changes it to `SUCCEEDED` with
`result_sigil == receipt.receipt_sigil`; Event 9 changes it to `FAILED` with
`result_sigil == error_details.detail_sigil`. No other Event changes either
scope, and an equal key with different request bytes is an integrity conflict.

`LogicalPartialFenceProjection` is the sole target-level partial-lineage
authority. A `PROMOTION_PARTIAL` or `RECOVERY_TERMINAL` head has a null
`canonical_record` until the exact Receipt observation fills it. Recovery
selection is legal only against the current `ACTIVE` projection with a
canonical head and null `unresolved_recovery_attempt_id`. Its complete
`RecoveryLineageBinding` must equal that projection's target, generation,
revision, Sigil, head Sigil, and latest canonical predecessor. The first
Recovery cites the canonical `PARTIAL` Outcome; every later Recovery cites the
latest canonical `STALE`, `FAILED`, `PARTIAL`, or `CANCELLED` Recovery Record.
Skipping or returning to an older head is invalid.

The replay assignment of every fence field is exact:

| Event | Exact `LogicalPartialFenceProjection` assignment |
| --- | --- |
| `promotion.partial` | For `NONE`, `CLEAR`, or `ABANDONED`, replace all historical root fields with `target_id = Attempt.target.target_id`, `root_attempt_id = payload.attempt_id`, `root_outcome_receipt = null`, and the exact PromotionProjection checkpoint and Mutation Intent Refs whose IDs equal the payload. Set state `ACTIVE`, head to this `PROMOTION_PARTIAL` Event with null canonical record, unresolved slot null, and generation 1 from `NONE` or checked prior + 1 otherwise. |
| `canonical.receipt-observed` for that `PARTIAL` Outcome | Preserve target, generation, root Attempt, checkpoint, Mutation Intent, and unresolved slot; set `root_outcome_receipt` to this Receipt and fill the same head's exact `LogicalFencePromotionRecord`. |
| `recovery.attempt-created` | Preserve all root fields and the head byte-for-byte; set only `unresolved_recovery_attempt_id` to this new Attempt and increment revision. |
| recovery Events 36 through 40 | No fence revision; the complete current projection remains byte-for-byte unchanged. |
| recovery terminal Events 41 through 47 | Preserve target and all four root fields; replace the head with the exact null-canonical `RECOVERY_TERMINAL`, retain the unresolved slot, and preserve generation except that `recovery.partial` uses checked prior + 1. |
| `canonical.receipt-observed` for that Recovery Record | Preserve target and all four root fields; fill the exact head canonical record, clear the unresolved slot, preserve generation, and apply the tabled `ACTIVE`, `CLEAR`, or `ABANDONED` state. |
| successful abandoned re-entry Outcome Receipt | Preserve target, generation, and all four historical root fields; replace the head with `ABANDONED_REENTRY_RESOLVED`, keep the unresolved slot null, and set state `CLEAR`. |

Every existing-row transition increments fence revision exactly once and
recomputes `logical_fence_sigil`; no other field changes. A
`RecoverySelection`'s `parent_attempt_id`, `parent_outcome_receipt`,
`checkpoint`, and `mutation_intent` equal the current projection's
`root_attempt_id`, non-null `root_outcome_receipt`, `checkpoint`, and
`mutation_intent` byte-for-byte. Thus later Recovery heads cannot replace or
silently redirect the original recoverable root.

`recovery.attempt-created` atomically sets the previously null unresolved slot.
Events 36 through 40 require that slot to equal their Recovery Attempt and
require the Attempt, Authorization selection, and any Recovery Intent lineage
to be byte-identical. A terminal Recovery Event advances the fence head but
does not clear the slot. Only `canonical.receipt-observed` for that exact
Recovery Record fills the head's canonical record and clears the slot. It maps
`STALE`, `FAILED`, `PARTIAL`, and `CANCELLED` to `ACTIVE`;
`BASE_RESTORED` and `POSTIMAGE_ACCEPTED` to `CLEAR`; and `ABANDONED` to
`ABANDONED`. The transition's `next_state`, generation, terminal Event, IDs,
Sigils, Receipt, and record branch must reproduce that mapping exactly.

Prepare has this exhaustive fence matrix:

| Request branch and current target fence | Required bindings and result |
| --- | --- |
| `RECOVER_PARTIAL` + `ACTIVE` | `recovery` non-null, `abandoned_lineage` null, exact current canonical lineage, unresolved slot null |
| `PROMOTE` + absent or `CLEAR` | both bindings null |
| `PROMOTE` + `ACTIVE` | reject `PATCH_RECOVERY_REQUIRED` before Preview |
| `PROMOTE` + `ABANDONED` | `recovery` null and exact current `abandoned_lineage` |

That matrix is not only a Prepare check. `promotion.attempt-created`, every
guard-acquire intent, Ready transition, mutation or Recovery intent commit,
every `target.guard-validated`, and immediately before every physical
target-content call replays and enforces it again. A Promotion whose
Authorization has null `abandoned_lineage` requires the current fence to be
absent or `CLEAR`; one with a non-null binding requires the current
`ABANDONED` projection to match it byte-for-byte. A Recovery requires the
current fence `ACTIVE`, its Authorization/Attempt lineage current, and the
unresolved slot equal to that Recovery Attempt. This blocks an older
Preview, Authorization, or Attempt even when a not-yet-canonicalized recovery
has already restored target bytes to Base. A pre-intent mismatch creates no
guard or content write and returns `PATCH_RECOVERY_REQUIRED` or takes the
legal `STALE` terminal path; a post-intent mismatch fences authority and enters
the deterministic replay classification without issuing the blocked call.

For abandoned re-entry, `reentry_proposal` equals the request/Preview Proposal,
is a new Proposal whose canonical observation follows the abandonment Receipt,
and fresh Target State Evidence equals the preserved observed identity and
generation. Preview and Authorization copy the entire binding. A new
`PARTIAL` advances the generation and returns the fence to `ACTIVE`. Otherwise
only a canonical `APPLIED`,
`RECOVERED_POSTIMAGE_OBSERVED`, or `ALREADY_APPLIED` re-entry Outcome may
create `ABANDONED_REENTRY_RESOLVED` and move it to `CLEAR`; failed, stale,
conflicted, or cancelled re-entry leaves `ABANDONED` unchanged.

`PatchErrorDetails.detail_sigil` covers the object with that field omitted.
`TailRecoveryIntent.record_sigil` covers its complete canonical JSON with that
field omitted. `PROTECTED` revision 1 has null `previous_record_sigil`; every
later stage is a new immutable record whose previous Sigil equals the prior
stage and whose revision is exactly one greater. An atomically replaced
current-stage pointer selects the newest record, but every historical stage
record remains content-addressable and is never rewritten. The three replay
fields are null through `HEAD_INSTALLED` and all non-null in
`REPLAY_EVENT_STAGED` and `REPLAY_EVENT_COMMITTED`.
`completion_mode` is null before `COMPLETED`. A completed
`NORMAL_REPLAY` record retains all three non-null replay fields; a completed
`READ_ONLY_PREFIX` record has all three null and is legal only for the
adopted `coordinator.integrity-failed` suffix branch below.
Whenever `coordinator.replay-started.tail_recovery_intent_sigil` is non-null,
it equals the retained `HEAD_INSTALLED` stage record Sigil, never the current
pointer, a staged record, or a record containing that event.
Every TailRecoveryIntent stage copies the Evidence Manifest's owner/recovery
identity, Heads, offsets, classification, and original suffix Blob
Sigil/size; `evidence_protection.root_plan` resolves that Manifest as its
control record. A different manifest, plan, binding, Blob generation, or
suffix classification is invalid.

Every non-null event payload field named `checkpoint_protection`,
`intent_protection`, `prior_step_protection`, `evidence_protection`, or
`suffix_evidence_protection` creates exactly one `OperationalRoot` at revision
1 in that same Journal transition. A null protection creates none.
`payload_field` is the corresponding uppercase enum.
`root_kind` is `CHECKPOINT` for `checkpoint_protection`,
`MUTATION_INTENT` or `RECOVERY_INTENT` for `intent_protection` according to
the event family, `JOURNAL_SUFFIX` for `suffix_evidence_protection`, and
`EVIDENCE` otherwise. The resolved plan must already be durable; its
`control_record` is the checkpoint, mutation intent, recovery intent, or
evidence manifest selected by that field/event matrix. The resolved
`target_reference_set` source must be `OPERATIONAL_CONTROL_RECORD`; its
identity and Sigil equal the plan control record and become
`control_record_id` and `control_record_sigil`, while
`authorization.subject_id` equals the plan ID. The root copies the plan
reference, binding, and Reference Set, copies the admitting Event ID and Sigil
into both transition pairs, equals `plan.operational_root_id`, and starts
`ACTIVE`.
Its `root_sigil` is the self-Sigil over every other complete projection
member and is recomputed for the `INACTIVE` revision without changing
identity. Its ID is deterministic:

```text
root_material = canonical_json({
  journal_id, event_id, payload_field, hold_id,
  reference_set_id, control_record_id, control_record_sigil
})
root_id = "PROOT-" + first_32_lower_hex(
  SHA-256("benchwork:promotion-operational-root:v1\0" || root_material))
```

This activation-time recomputation must equal the finalized plan. It is not
authority for Storage to validate a future Event or root at hold-set
admission.

The exact unions are:

| `$def` | Exact branches |
| --- | --- |
| `DecisionRecord` | `AUTHORIZE {kind: Enum<AUTHORIZE>; authorization: Obj<patch-promotion-authorization/1.0>}` or `REJECT {kind: Enum<REJECT>; rejection: Obj<patch-promotion-rejection/1.0>}` |
| `OutcomeRecordRef` | `PROMOTION_OUTCOME {kind: Enum<PROMOTION_OUTCOME>; outcome_id: ID<PO>; outcome_sigil: Sigil}` or `RECOVERY_RECORD {kind: Enum<RECOVERY_RECORD>; recovery_record_id: ID<PRR>; recovery_record_sigil: Sigil}` |
| `InspectSelector` | `PROPOSAL {kind: Enum<PROPOSAL>; proposal_id: ID<PP>}`; `PREVIEW {kind: Enum<PREVIEW>; preview_id: ID<PRV>}`; `DECISION {kind: Enum<DECISION>; preview_id: ID<PRV>}`; `PROMOTION_ATTEMPT {kind: Enum<PROMOTION_ATTEMPT>; attempt_id: ID<PAT>}`; `RECOVERY_ATTEMPT {kind: Enum<RECOVERY_ATTEMPT>; recovery_attempt_id: ID<PRA>}`; `PROMOTION_OUTCOME {kind: Enum<PROMOTION_OUTCOME>; outcome_id: ID<PO>}`; or `RECOVERY_RECORD {kind: Enum<RECOVERY_RECORD>; recovery_record_id: ID<PRR>}` |
| `InspectItem` | `PROPOSAL {kind: Enum<PROPOSAL>; record: Obj<patch-proposal/1.0>}`; `PREVIEW {kind: Enum<PREVIEW>; record: Obj<patch-promotion-preview/1.0>}`; `AUTHORIZATION {kind: Enum<AUTHORIZATION>; record: Obj<patch-promotion-authorization/1.0>}`; `REJECTION {kind: Enum<REJECTION>; record: Obj<patch-promotion-rejection/1.0>}`; `PROMOTION_ATTEMPT {kind: Enum<PROMOTION_ATTEMPT>; record: Obj<patch-promotion-attempt/1.0>}`; `RECOVERY_ATTEMPT {kind: Enum<RECOVERY_ATTEMPT>; record: Obj<patch-promotion-recovery-attempt/1.0>}`; `PROMOTION_OUTCOME {kind: Enum<PROMOTION_OUTCOME>; record: Obj<patch-promotion-outcome/1.0>}`; or `RECOVERY_RECORD {kind: Enum<RECOVERY_RECORD>; record: Obj<patch-promotion-recovery-record/1.0>}` |
| `EventPayload` | exactly one of 47 local branches selected by the parent event's exact `event_type`; branch `$defs` are named `EventPayload.<event_type>` and contain exactly the required payload fields, types, bounds, and conditional constraints in the complete transition table below |

The executable Journal Schema materializes all 47
`EventPayload.<event_type>` `$defs` from that table in this RFC. It may not use
an open map, an unevaluated payload, or a future Schema reference.

These top-level cross-field branches are also normative Schema constraints:

| Contract | Exact branch constraint |
| --- | --- |
| Prepare request, `patch-promotion-preview/1.0`, and `patch-promotion-authorization/1.0` | `RECOVER_PARTIAL` requires exact non-null `recovery` and null `abandoned_lineage`; `PROMOTE` requires null `recovery` and uses non-null `abandoned_lineage` exactly for the tabled `ABANDONED` re-entry branch |
| `patch-promotion-target-guard/1.0` | nullable backend and deadline fields equal the replay prefix: they are null only when no prior event established that value; once established, later states copy it until a named renew, fence, or release event replaces it; `recovery_of_guard_id` is non-null exactly for a replacement guard |
| `patch-promotion-outcome/1.0` | `checkpoint`, `mutation_intent`, and `guard` are each null exactly when the bound terminal Journal prefix contains no corresponding commit/acquire event for the Attempt; otherwise each is the exact established reference; the terminal event type must map to `status` |
| `patch-promotion-recovery-intent/1.0` | `RESTORE_BASE` requires non-null `topology_plan`; `ACCEPT_POSTIMAGE` and `ABANDON` require null |
| `patch-promotion-recovery-record/1.0` | lineage equals Attempt, Authorization selection, and any Intent; guard/intent are both non-null after `recovery.intent-committed`, guard alone is non-null after guard acquisition but before intent, and both are null before guard acquisition; terminal Event maps exactly to `status` and resulting fence generation; `abandonment_disposition` is non-null exactly for `action: ABANDON`, `status: ABANDONED` and satisfies the exact no-write, fence, and root-set rules above |
| inspect request and response | a non-null `cursor` requires non-null `fixed_prefix`; every item branch is legal for the selector at that fixed prefix; `next_cursor` is null exactly on the final page |
| authorize request and response | `AUTHORIZE` requires token, digest, and `true`; `REJECT` requires all three null; response decision and `DecisionRecord.kind` are equal |
| outcome request and response | request kind equals `OutcomeRecordRef.kind`; response `record_id` and `record_sigil` equal that accepted branch and response kind |

The Prepare request, Preview, and Authorization copy whichever non-null
lineage branch applies byte-for-byte. A Recovery Attempt, Recovery Intent, and
Recovery Record likewise copy the same `RecoveryLineageBinding`; resolving
only matching IDs while accepting different lineage bytes is invalid.

The executable Schemas must reproduce these 34 rows exactly. A new top-level
field, a wider bound, a differently sorted set, an omitted `Nullable` field, a
raw token in another contract, or a different Sigil projection requires a new
contract version.

Unknown fields, versions, identity profiles, patch semantics, validation
policies, application adapters, and outcome evidence fail closed. Patch bytes,
file payloads, full manifests, and validation logs are stored as
content-addressed Blobs under RFC-0013. Chronicle records their identities and
accepted relationships, not mutable workspaces or unbounded payloads.

## Terminology

| Term | Meaning |
| --- | --- |
| **Base Identity** | Immutable identity of the exact projected source tree materialized before an Attempt. It includes the identity profile and path semantics needed to recompute it. |
| **Patch Bundle** | Content-addressed change manifest, payload Blobs, and bounded human-readable representations exported from a Crucible. |
| **Patch Proposal** | Post-terminal immutable control record binding one Patch Bundle to exactly one accepted `agent-result/2.0` Receipt, its Base and expected Postimage identities, execution provenance, scope, and residual risks. |
| **Postimage Identity** | Identity of the projected tree that must exist after exact application of the Patch Proposal to its Base Identity. |
| **Validation Evidence** | Immutable result of running one declared validation check against a fresh materialization of the exact Base plus Patch Proposal. |
| **Validation Policy** | Versioned, Sigil-bound rule defining required checks, accepted outcomes, validator profiles, and minimum assurance. |
| **Promotion Preview** | Immutable, short-lived presentation of one proposal, exact evidence set, exact target, expected preimage and postimage, and application semantics. It is operational until confirmed. |
| **Promotion Authorization** | Canonical human authorization bound to the exact Preview Sigil and confirmation-token Sigil. It permits no broader patch, target, or Git action. |
| **Promotion Attempt** | One Host-native try to realize an authorized Postimage. It is distinct from an Executor Attempt and has a unique identity. |
| **Promotion Outcome** | Append-only terminal record of what one Promotion Attempt observed and changed. |
| **Recovery Attempt** | New, separately identified and authorized operation that may restore the Base, accept an already realized Postimage, or abandon Benchwork recovery after a prior `PARTIAL` Promotion Attempt. It never changes that prior terminal outcome. |
| **Promotion Journal** | Hash-chained append-only operational history for Promotion and Recovery Attempts, target guards, checkpoints, mutation intents, verification, and replay. It has no canonical authority. |
| **Promotion Coordinator** | Trusted Host-local component that owns the Promotion Journal, target-guard protocol, checkpoints, and adapter orchestration without becoming Athanor, MCP, or a generic Git service. |
| **Promotion Target** | Human-selected repository or worktree materialization identified by a stable target ID and an exact content identity. A path, branch name, tag, or `HEAD` string alone is not an identity. |

## Base and postimage identity

### Identity profile

A Base Identity is the Sigil of a closed `patch-base/1.0` document. It binds:

- the identity-profile ID, version, and Sigil;
- the logical source-root ID, its immutable source-root Sigil, and the
  project-relative scope;
- path normalization, Unicode, case-sensitivity, and executable-mode
  semantics;
- the complete sorted entry-manifest Blob Sigil for that scope;
- entry count and total byte count;
- the Blob or link-target Sigil, entry type, and normalized mode of every
  included path;
- selected input Artifact and materialization identities;
- the Executor Job, Attempt, Crucible, and base-materialization identities;
  and
- optional VCS provenance.

The identity scope excludes runtime scratch storage, RFC-0013 transport
metadata, and implementation-owned control directories, but those exclusions
are part of the identity profile rather than ambient convention. `.benchwork/`
and VCS administrative storage such as `.git/` are always protected control
paths and can never be Patch operations.

The manifest is an identity of entry content and semantics, not a tar archive
timestamp, inode, device number, checkout path, or filesystem traversal order.
Directories, regular files, executable modes, and symbolic links have distinct
entry types. A symbolic link is hashed as link data and is never followed while
constructing an identity. Hard links, submodules, sparse entries, large-file
pointers, and platform-specific entry types must be represented by an
explicitly supported profile or rejected.

The Base manifest is complete for its declared identity scope. Its sorted path
set therefore proves whether a normalized path was present before execution.
It does not predict which paths the Worker may add and contains no synthetic
future `ABSENT` entries. After terminal export discovers an added path, the
trusted exporter proves non-membership against the complete Base manifest and
then emits that operation's explicit `ABSENT` precondition inside the
`patch-bundle/1.0`. A partial, sparse, or exclusion-based manifest cannot
authorize `ADD` for a path whose prior non-membership it cannot prove.

For a Git source, the Base may additionally record the object format, resolved
commit object ID, tree object ID, submodule object IDs, and whether the
materialization was clean. Branches, tags, remote URLs, and `HEAD` are mutable
locators and never substitute for the entry-manifest identity. A commit ID is
sufficient only when a verified profile proves that the complete identity
scope is a clean materialization of that exact object and accounts for
submodules, filters, sparse checkout, and working-tree overlays.

The Postimage Identity uses the same identity profile and non-contextual scope
members. It is computed outside the Worker both from the Base manifest plus
the exported change manifest and from the exact RFC-0012 retained-source
bundle projection defined above. Those independently derived
`patch-tree-manifest/1.0` records and `TreeIdentity` values must agree. A
mismatch quarantines the export.

For this RFC's only eligible `VERIFIED` terminal-source branch,
`patch-base.source_root_id` equals
`terminal_source.crucible_base_identity` and
`patch-base.source_root_sigil` equals
`terminal_source.crucible_base_sigil`. In addition, the non-null
`terminal_source_identity`, `terminal_source_sigil`, and `storage_blob` resolve
and equal one exact RFC-0012 `benchwork-source-tree/1.0` ID, self-Sigil, and
`bundle_blob` triple. The trusted exporter recomputes the
Base manifest from that exact pinned source root under the Base's bound
identity profile and scope; the resulting manifest Blob, entry count, total
bytes, `TreeIdentity`, and Base Sigil must all agree. It independently decodes
the retained source bundle and derives the exact Postimage manifest as above.
A matching mutable source-root ID without the matching Sigil, or a source-tree
pair without the exact Storage Blob, is not lineage evidence.
`patch-base.base_sigil` is the self-Sigil of the later post-terminal wrapper,
including its execution provenance; it is neither equal to nor a replacement
for the pre-execution `source_root_sigil`.

### Patch footprint

Every primitive Patch operation is one of `ADD`, `MODIFY`, `DELETE`, or
`TYPE_CHANGE`. `ADD` requires an `ABSENT` preimage and non-`ABSENT`
postimage; `DELETE` requires the inverse; `MODIFY` requires two non-`ABSENT`
entries of the same kind; and `TYPE_CHANGE` requires two non-`ABSENT` entries
of different kinds. Because operations are unique by path, a type change
cannot be encoded as a same-path delete plus add. Renames and copies may be
displayed as review hints, but their authoritative meaning remains operations
on the distinct source and destination paths. Each operation binds:

- one normalized project-relative path;
- the exact expected preimage entry or `ABSENT`;
- the exact expected postimage entry or `ABSENT`; and
- the payload Blob Sigil when the postimage is a file or supported link.

Operations are sorted, unique by path, and covered by the Patch Bundle Sigil.
An apply adapter must compare every precondition and must produce every
postcondition. Context lines in a unified diff, rename similarity, file
timestamps, and patch-tool heuristics grant no authority.

The Patch Bundle may contain bounded unified diffs, binary summaries, or review
renderings, but those are derived views. Application authority comes from the
closed change manifest and payload identities. An adapter that cannot realize
an entry type or mode exactly rejects the proposal rather than approximating
it.

## Crucible export

The Worker never designates arbitrary Host paths for export and never supplies
the authoritative Base or Postimage identity. Before Worker code starts, the
Executor records the immutable Base Identity for the Crucible. During terminal
processing it freezes or snapshots the terminal Crucible under a retained
content identity before releasing mutable resources. When post-terminal
derivation was declared before launch, RFC-0012 and RFC-0015 bind this retained
terminal source during terminalization as a conditional immutable Job Outcome
field. It is operational evidence, not a Patch Proposal, and it can never be
added, replaced, or backfilled after the Outcome is derived.

Patch export may begin only after:

1. the Attempt and Job are terminal and eligible under RFC-0011 and RFC-0012;
2. RFC-0015 result acceptance has produced exactly one valid
   `agent-result/2.0` Receipt for the same Task, Job, Attempt, result, and
   retained terminal source; and
3. that Receipt and every source binding still verify.

The trusted exporter outside the Worker then:

1. resolves the pinned Crucible base by both source-root ID and
   source-root Sigil, recomputes the complete Base manifest under the bound
   identity profile and scope, and revalidates the retained terminal source;
2. resolves the retained source by the exact terminal-source ID, self-Sigil,
   and `storage_blob`, decodes the deterministic RFC-0012
   `benchwork-source-tree/1.0` bundle without following links, and reproduces
   its complete source manifest and file bytes;
3. applies the bound identity profile and exact `PathScope` predicate to
   derive `patch-tree-manifest/1.0`, then independently verifies every entry,
   count, directory/root Sigil, manifest Sigil, record Sigil, and manifest
   Blob;
4. computes the terminal Postimage Identity both from that manifest and from
   Base plus primitive operations and requires equality;
5. derives the primitive change manifest from Base to terminal state;
6. proves every `ADD` path absent from the complete Base path set and writes
   explicit `ABSENT` preconditions into the new Patch Bundle;
7. without allocating storage or appending any record, serializes and hashes
   the exact candidate Base and Postimage manifests, declared payloads, review
   renderings, attachments, and Patch Bundle bytes; builds one immutable
   in-memory export plan containing every exact Blob Sigil and size, including
   `terminal_source.storage_blob.blob_sigil`, both tree-manifest Blobs, and
   `patch_bundle_blob_sigil`, the byte-level RFC-0013 Blob Sigil of the
   complete canonical Patch Bundle document including its logical
   `bundle_sigil`; forms the sorted unique managed-Blob closure;
   and rejects a 4,097th distinct Blob or any other bound violation before the
   first side effect;
8. revalidates the already committed terminal-source Storage Blob and copies
   only the preflight-planned new manifests, declared payloads, review
   renderings, and attachments into fresh RFC-0013 staging objects;
9. verifies every staged Blob's complete bytes, size, Sigil, source binding,
   and Agent Result Receipt relationship;
10. commits each eligible Blob through RFC-0013's verified no-overwrite commit
   protocol;
11. constructs the closed Patch Bundle over only committed Blob identities in
    a fresh RFC-0013 staging object and requires its complete bytes, size,
    Sigil, source, Receipt relationship, and dependency closure to equal the
    preflight export plan byte-for-byte;
12. commits the verified Patch Bundle Blob through RFC-0013's no-overwrite
    commit protocol;
13. constructs and validates, but does not yet register, one immutable
    `artifact-storage-reference-set/1.0` candidate whose `source.kind` is
    `BLOB_MANIFEST`, whose source identity and source Sigil both equal
    `patch_bundle_blob_sigil`,
    and whose sorted typed edges include one explicit `BLOB` target for the
    same `patch_bundle_blob_sigil` using `BUNDLE_RETAINS_MEMBER`, plus every
    required Base manifest, terminal-source Storage Blob, payload, Postimage
    manifest, review rendering, and attachment Blob using
    `PATCH_RETAINS_BASE`, `PATCH_RETAINS_POSTIMAGE`, or
    `BUNDLE_RETAINS_MEMBER` as applicable; the complete distinct Blob closure
    equals the preflight plan and later request and reference-intent Blob
    arrays byte-for-byte;
    it also constructs the Proposal candidate and dependency plan, but not the
    final transition request;
14. acquires RFC-0013's canonical-reference gate before registering any new
    canonical binding;
15. while holding that gate, takes the Storage Journal lock, registers and
    reads back the exact Reference Set, and releases the Storage Journal lock;
16. still holding the gate, derives the deterministic Proposal-family CTR-ID,
    finalizes the exact `patch.proposed` transition request over the
    now-registered Reference Set, computes its request Sigil without any
    reference-intent, future Event, or Receipt field, and atomically creates or
    resolves the one single-assignment request slot;
17. takes the Storage Journal lock again, durably opens one
    `artifact-storage-reference-intent/1.0` binding that final request Sigil,
    Reference Set, and complete Blob closure, then releases the Storage Journal
    lock while retaining the canonical-reference gate;
18. asks Athanor to commit the exact transition; after verifying its Receipt,
    takes only the Storage Journal lock, appends
    `canonical_reference.committed`, verifies the resulting durable pin, and
    releases that lock while retaining the canonical-reference gate;
19. takes only the Promotion Journal lock, appends and Head-commits
    `canonical.receipt-observed` for the exact Proposal submission, releases
    that lock, and then releases the canonical-reference gate; and
20. for failed, partial, mismatched, stale, or unverifiable staging material,
    reserves the exact RFC-0013 Quarantine byte and object capacity before
    appending `quarantine.intent_recorded` or moving it, uses the exact source
    and destination generations, and calls it quarantined only after destination
    durability, readback, `quarantine.recorded`, and `transfer.quarantined`;
    when that reservation is unavailable, leaves it isolated as
    `HELD_FOR_DISPOSITION`, keeps the staging reservation charged, applies
    storage backpressure, and never calls it quarantined or exposes it as a
    Proposal input.

The `BLOB_MANIFEST` source describes the Reference Set's provenance only; it
does not itself create an RFC-0013 reachable Blob target. The explicit
Patch-Bundle `BLOB` edge in step 13 is therefore mandatory; its
`target_identity` and `target_sigil` both equal
`patch_bundle_blob_sigil`, even though that value also appears in both source
fields. Omitting that edge makes the set, managed closure, transition request,
and intent invalid.

Reference Set registration failure, missing or mismatched typed edges, inability
to open the canonical-reference intent, or an ambiguous intent makes the export
ineligible for `patch.proposed`. The intent remains a GC root while ambiguous.
While holding the canonical-reference gate, the exporter follows RFC-0013's
lock order: it may take and release the Storage or Promotion Journal lock, or
invoke Chronicle with no local journal lock, but never overlaps any two.

The exporter rejects absolute paths, traversal, NULs and control characters,
duplicate or case-colliding paths, protected control paths, unsupported entry
types, escaping links, changed immutable inputs, path-count or byte-count
overruns, and any operation not authorized by the Task and Execution
Specification.

A terminal failed, cancelled, expired, fenced, or policy-violating Attempt may
have its Crucible delta retained as quarantined operational evidence after the
required RFC-0013 reservation, or isolated as `HELD_FOR_DISPOSITION` when that
reservation is unavailable. It cannot produce a promotion-eligible Patch
Proposal. Retention never rewrites the Attempt as successful, and a retry
receives a new Attempt and export identity.

The exporter does not write the researcher's target worktree, index, branch,
or ref. Committed Blobs do not by themselves create a Patch Proposal. They
become eligible inputs to `patch.proposed` only through the post-terminal
Athanor transition below.

## Patch Proposal

A `patch-proposal/1.0` has exactly these closed top-level field groups; the
Schema makes every listed group required and closes every nested object:

- Schema version;
- a unique Proposal ID and its Proposal Sigil;
- exactly one accepted `agent-result/2.0` event ID, Receipt ID, Receipt Sigil,
  Agent Result Sigil, and Task-result binding;
- the directly copied Job Outcome ID and Sigil and non-null retained
  terminal-source ID, self-Sigil, and Storage Blob triple, exactly equal to
  the fields bound by that accepted Agent Result;
- Patch Bundle, Base, and Postimage identities;
- the registered RFC-0013 Reference Set ID and Sigil;
- Task Capsule, Capability Contract, Snapshot, and Execution Specification
  Sigils;
- the exact Agent Result Job binding, selected Attempt binding, realized
  assurance-claim Sigil, and complete RFC-0015 Agent Result provenance,
  including Executor epoch/build, Worker Session, backend, requested assurance,
  authorization, budget, storage, CES, and QBS bindings; Crucible Base and the
  retained-source ID/Sigil/Storage-Blob triple remain in the separate
  terminal-source binding;
- the exact identity and path-semantics profiles;
- the declared scope and sorted changed paths;
- a bounded summary, claimed intent, and residual risks;
- exporter identity, version, configuration Sigil, and export evidence; and
- creation time and promotion eligibility.

Conditionally absent values use the Schema's explicit `null` branch rather
than omission or an extension dictionary. Changing this field set requires a
new `patch-proposal` contract version.

The Worker may provide the summary and residual-risk Proposal, but the trusted
exporter computes changed paths, preimages, postimages, manifests, and Blob
Sigils. Worker-authored diff text cannot replace those values.

`JobOutcomeBinding` is not a generic two-field reference and does not define a
new Outcome namespace. It resolves an RFC-0015
`execution-job-outcome/1.0` whose ID is in the `OJ-` domain, verifies the
complete Outcome by `outcome_sigil`, and requires the copied Job terminal Event
and non-null terminal-source Sigils to match both that Outcome and
`AcceptedAgentResultBinding` byte for byte.

Before accepting `patch.proposed`, Athanor first resolves the bound Receipt to
one and only one accepted `agent-result/2.0` for the exact Task, Job, Attempt,
execution result, and terminal source. It then revalidates the Task,
Capability, Snapshot freshness, Execution Specification, expected output
contract, Job and Attempt terminal eligibility, realized assurance, exporter
evidence, direct Job Outcome and retained terminal-source equality, all
identity relationships, the registered Reference Set and typed dependency
closure, the open canonical-reference intent, and every committed RFC-0013
Blob.
Missing, ambiguous, rejected, or differently bound Agent Result acceptance
fails closed.

For the Base lineage, Athanor additionally requires
`proposal.base.source_root_id ==
proposal.terminal_source.crucible_base_identity` and
`proposal.base.source_root_sigil ==
proposal.terminal_source.crucible_base_sigil`, then independently verifies
that the Base manifest and identity were recomputed from that pinned source
root under the Proposal's exact identity profile and scope. Neither a
same-named mutable root nor a manifest supplied only by the Worker satisfies
this predicate. Athanor also resolves
`(terminal_source_identity, terminal_source_sigil)` to the exact RFC-0012
source-tree record, requires `terminal_source.storage_blob ==
source_tree.bundle_blob`, decodes the bundle, and rederives the Proposal's
Postimage manifest and `TreeIdentity`.

Phase 3 permits at most one accepted `patch.proposed` record for a given
Agent Result Receipt and terminal-source ID/Sigil/Storage-Blob triple. Exact
duplicate submission is idempotent; different Proposal content for that
binding is a conflict and requires a new accepted execution result rather than
mutation of the old one.
Acceptance occurs only through RFC-0013's canonical-reference gate. The
`patch.proposed` event directly binds the reference-intent ID and record Sigil,
transition-request Sigil, and every Reference Set ID and Sigil without
embedding its own Event Sigil or Receipt. The Proposal and candidate transition
request do not contain the reference-intent record Sigil, so the intent's
binding to the transition-request Sigil creates no hash cycle. After Athanor
returns the new Receipt, the storage coordinator appends
`canonical_reference.committed`; an ambiguous response leaves the intent
`OPEN` and pinned until Chronicle replay resolves it. A definitively aborted
request may append `canonical_reference.released` with
`ABORTED_BEFORE_CANONICAL_COMMIT` only through RFC-0013's exact
`HEAD_SUPERSEDED_WITHOUT_BOUND_EVENT` authority. Acceptance never updates the Execution Job,
`execution-result/1.0`, `agent-result/2.0`, their Receipts, or their immutable
projections. It does not apply the patch, register its payloads as scientific
results beyond their explicit Artifact records, or declare the implementation
valid.

Missing, late, duplicate with different content, under-assured, stale, fenced,
malformed, pre-Agent-Result, or policy-violating derived proposals remain
preserved in the export or storage journal and, subject to quota reservation,
Quarantine or `HELD_FOR_DISPOSITION`, but are ineligible for canonical proposal
acceptance. Patch derivation state never backfills the execution journal's
immutable Job or result outcome.

## Validation evidence

Validation is identity-bound and append-only. A validation check must run
against a fresh, exclusive materialization produced from the exact Base
Identity and Patch Proposal, not against an unverified residue of the mutation
Crucible. Before the check starts, the materializer verifies that applying the
proposal produces the expected Postimage. Validation execution follows its own
Task, Job, Attempt, Lease, Circle, and assurance requirements.

Each `patch-validation-evidence/1.0` record binds:

- the Patch Proposal, Patch Bundle, Base, and Postimage Sigils;
- the Validation Policy ID, version, and Sigil;
- a check ID, check type, declared scope, and expected result;
- validator identity plus dependency, environment, configuration, and input
  identities;
- the exact resolved validation Job Outcome, immutable Job and selected
  Attempt bindings, Attempt terminal Event, Execution Specification, Worker
  Session, Executor epoch/build and fence authority, backend identity and
  configuration, requested assurance tuple, and realized assurance claim;
- start and terminal timestamps, terminal status, and normalized exit result;
- bounded observations and the Sigils of complete logs and result Artifacts;
- whether the expected Postimage was verified before and after the check; and
- limitations and residual risks.

Allowed terminal statuses are `PASS`, `FAIL`, `ERROR`, `CANCELLED`, and
`INELIGIBLE`. The evidence verifier derives the status from retained runtime
evidence outside the validation Worker. A Worker-authored sentence such as
“tests passed” is not validation evidence.

The validation Outcome must be terminal and select the named Attempt.
`ValidationExecution.job_outcome` resolves the complete Outcome, while every
duplicated field is a byte-for-byte copy of its matching closed binding.
`worker_session_binding`, `authority_binding`, and
`assurance_context_binding` must be the eligible `BOUND`, `LEASED`, and
`ATTEMPT` branches respectively; the terminal Event and assurance claim must
resolve exactly. A backend summary Sigil, runtime label, or unbound Job and
Attempt ID cannot substitute for this lineage.

A validation set satisfies a policy only when every required check has one
eligible `PASS` record for the exact Proposal and the set meets the policy's
validator, environment, independence, assurance, and evidence requirements.
Optional checks and every failed, cancelled, errored, superseded, or
contradictory check remain visible. Later success does not delete or rewrite
earlier failure. A local review can be a required check, but an external review
still requires its own exact disclosure approval under the Review policy.

Validation establishes only that the declared checks produced the recorded
outcomes in the recorded environments. It is not scientific acceptance, a
Seal, permission to mutate a target, or a guarantee of correctness.

## Typed Patch MCP control plane

This RFC owns four typed Patch operations and their domain request and response
Schemas:

| MCP tool | Request Schema | Response `data` Schema | Semantics |
| --- | --- | --- | --- |
| `benchwork_prepare_patch_promotion` | `patch-promotion-prepare-request/1.0` | `patch-promotion-prepare-response/1.0` | Prepare an immutable Preview for `PROMOTE` or for a separately authorized `RECOVER_PARTIAL` action. |
| `benchwork_inspect_patch_promotion` | `patch-promotion-inspect-request/1.0` | `patch-promotion-inspect-response/1.0` | Read one Proposal, Preview, authorization or rejection, Promotion Attempt, Recovery Attempt, or accepted outcome with bounded pagination. |
| `benchwork_authorize_patch_promotion` | `patch-promotion-authorize-request/1.0` | `patch-promotion-authorize-response/1.0` | Commit one explicit human `AUTHORIZE` or `REJECT` decision for the exact unexpired Preview. |
| `benchwork_record_patch_promotion_outcome` | `patch-promotion-outcome-request/1.0` | `patch-promotion-outcome-response/1.0` | Ask Athanor to accept one already terminal Promotion Outcome or Recovery Record. |

Their exact `mcp-tool-registry/2.0` metadata is:

| Tool | Category | Permission | Risk | Approval | Canonical effect |
| --- | --- | --- | --- | --- | --- |
| `benchwork_prepare_patch_promotion` | `patch` | `propose` | high | `none` | `operational_event` |
| `benchwork_inspect_patch_promotion` | `patch` | `read` | low | `none` | `none` |
| `benchwork_authorize_patch_promotion` | `patch` | `commit` | high | `human_confirmation` | `canonical_event` |
| `benchwork_record_patch_promotion_outcome` | `patch` | `commit` | high | `patch_authorization` | `canonical_event` |

Every tool returns the existing bounded `mcp-tool-result/1.0` envelope. Its
`data` field must validate against the exact response Schema above. Requests
and responses are closed, length-bounded, JSON-safe, and Sigil-bound. Unknown
selectors, record kinds, fields, enum values, cursors, or versions fail
closed.

The prepare request is a discriminated union. `PROMOTE` binds the accepted
Proposal, validation policy and exact evidence set, target-state evidence,
adapter profile, mode, idempotency key, and, only for an abandoned-lineage
re-entry, the exact current `AbandonedLineageBinding`. `RECOVER_PARTIAL`
instead requires null `abandoned_lineage` and binds one terminal `PARTIAL`
Promotion Attempt and accepted original Outcome Receipt, checkpoint, mutation
intent, latest canonical logical-fence head, requested recovery action
`RESTORE_BASE`, `ACCEPT_POSTIMAGE`, or `ABANDON`, and fresh target-state
evidence. It cannot skip an intervening Recovery Record or silently reuse the
original promotion confirmation.

Inspect is read-only and accepts exactly one typed identity selector. It never
accepts a path, Blob locator, command, Git ref mutation, or backend credential,
and it never returns raw patch payloads, absolute Host paths, target-guard
tokens, checkpoint bytes, or unbounded logs.

Authorize is a closed union selected by `decision: AUTHORIZE | REJECT`. Both
branches require the Preview ID and Sigil, actor and Host provenance, bounded
decision reason, complete request time, and an idempotency key.
`AUTHORIZE` additionally requires the confirmation token and an affirmative
human confirmation; `REJECT` requires an explicit negative human decision,
sets the token field to the Schema's exact `null` branch, and grants no
mutation authority. The response is a closed union containing exactly the
authorization or rejection identity and its Receipt. The outcome request is a
closed discriminated union of `PROMOTION_OUTCOME` and `RECOVERY_RECORD`; either
branch accepts only the corresponding immutable record identity and evidence
Sigils. It does not accept replacement patch content or instructions to apply,
retry, restore, abandon, or mutate a target.

All four tools use only these stable `error.code` values:

```text
PATCH_SCHEMA_INVALID
PATCH_NOT_FOUND
PATCH_INELIGIBLE
PATCH_STALE
PATCH_CONFLICT
PATCH_IDEMPOTENCY_CONFLICT
PATCH_PREVIEW_EXPIRED
PATCH_DECISION_PENDING
PATCH_DECISION_FAILED
PATCH_TOKEN_INVALID
PATCH_CLOCK_UNCERTAIN
PATCH_GUARD_UNAVAILABLE
PATCH_INTEGRITY_FAILURE
PATCH_STORAGE_UNAVAILABLE
PATCH_CHRONICLE_UNAVAILABLE
PATCH_REFERENCE_PIN_FAILED
PATCH_RECOVERY_REQUIRED
PATCH_OUTCOME_INVALID
PATCH_UNSUPPORTED_TARGET
```

`PatchReasonCode` is the exact closed enum:

```text
SCHEMA_INVALID
NOT_FOUND
INELIGIBLE
STALE
CAS_CONFLICT
KEY_REUSED
PREVIEW_EXPIRED
DECISION_PENDING
DEFINITIVE_PRECOMMIT_ABORT
CHRONICLE_HEAD_CONFLICT
POLICY_INELIGIBLE
STALE_BINDING
DEADLINE_CROSSED
TOKEN_INVALID
CLOCK_UNCERTAIN
ACTIVE_GUARD_LIMIT
GUARD_BACKEND_UNAVAILABLE
INTEGRITY_FAILURE
STORAGE_UNAVAILABLE
CHRONICLE_UNAVAILABLE
REFERENCE_PIN_FAILED
RECOVERY_REQUIRED
OUTCOME_INVALID
UNSUPPORTED_TARGET
```

For a Patch tool failure, `mcp-tool-result/1.0.error.details` is exactly one
`Obj<PatchErrorDetails>` with these required fields:

```text
error_id: ID<PER>
retryable: Bool
entity_kind: Nullable<Enum<PROPOSAL|PREVIEW|DECISION|GUARD|
                            PROMOTION_ATTEMPT|RECOVERY_ATTEMPT|
                            REFERENCE_INTENT|JOURNAL>>
entity_id: Nullable<Text<128>>
state: Nullable<Text<64>>
expected_sigil: Nullable<Sigil>
observed_sigil: Nullable<Sigil>
due_at: Nullable<Time>
idempotency_key_sigil: Nullable<Sigil>
failure_id: Nullable<ID<PDF>>
reason_code: PatchReasonCode
evidence_sigils: Set<Sigil,0..16,value>
detail_sigil: Sigil
```

`detail_sigil` covers canonical JSON with that field omitted. The serialized
details object is at most 16384 bytes; `error.message` is at most 512 UTF-8
bytes; `warnings` and `next_actions` each contain at most 16 strings of at most
512 UTF-8 bytes. Unknown fields or codes fail Schema validation. Details never
contain a raw confirmation token, absolute Host path, credential, backend
handle, payload byte, stack trace, policy secret, or unbounded diagnostic.

The code mapping is deterministic: malformed input is
`PATCH_SCHEMA_INVALID`; unknown identities are `PATCH_NOT_FOUND`; changed
Sigils or revisions before mutation are `PATCH_STALE`; legal-state or
compare-and-swap conflicts are `PATCH_CONFLICT`; different content under an
existing key is `PATCH_IDEMPOTENCY_CONFLICT`; clock and integrity gates use
their named codes; unavailable Chronicle state uses
`PATCH_CHRONICLE_UNAVAILABLE`; this includes a Chronicle Head whose
`event_count` is at or above `U63_MAX`, with reason
`CHRONICLE_UNAVAILABLE`; missing or uncommittable RFC-0013 protection
uses `PATCH_REFERENCE_PIN_FAILED`; and a `PARTIAL` lineage presented as an
ordinary retry uses `PATCH_RECOVERY_REQUIRED`.

After `preview.decision-submission-started`, a definitive pre-commit abort is
not returned until `preview.decision-failed` and its updated Head are durable.
That event embeds the complete `PatchErrorDetails` object rather than only a
pointer to ephemeral error state. For this event, `retryable` is false,
`entity_kind` is `DECISION`, `failure_id` is non-null, `reason_code` equals the
event reason, and the request and idempotency-key Sigils are exact.

Both stable IDs are deterministic:

```text
failure_material = canonical_json({
  preview_id, decision, redacted_request_sigil,
  idempotency_key_sigil, reason
})
failure_id = "PDF-" + first_32_lower_hex(
  SHA-256("benchwork:patch-decision-failure:v1\0" || failure_material))
error_id = "PER-" + first_32_lower_hex(
  SHA-256("benchwork:patch-decision-error:v1\0" || failure_material))
```

The deterministic values are embedded and verified on replay; a mismatch is
integrity failure. Every exact retry returns
`PATCH_DECISION_FAILED` with the same `error_id`, `failure_id`, reason,
complete details object and Sigil, and `retryable: false`; a different decision
or request under the key returns `PATCH_IDEMPOTENCY_CONFLICT`, and a new
decision requires a new Preview. An ambiguous or unavailable commit remains
`DECIDING` and returns
`PATCH_DECISION_PENDING` or `PATCH_CHRONICLE_UNAVAILABLE` with
`retryable: true`; it never fabricates `DECISION_FAILED`. Expiry before any
submission returns the durable `PATCH_PREVIEW_EXPIRED` result, while a
definitive deadline rejection after submission is the stable
`PATCH_DECISION_FAILED` branch.

RFC-0015 owns the shared MCP transport and Registry versioning, but this RFC
owns these four operation semantics and request/response contracts.
`mcp-tool-registry/2.0` must include all four entries alongside RFC-0015's
Executor operations before either RFC can be accepted. No tool named
`benchwork_apply_patch`, `benchwork_git`, `benchwork_recover_anything`, or
other generic mutation surface is permitted.

## Promotion protocol

### 1. Prepare

The researcher or interactive Host selects one accepted Patch Proposal, a
Validation Policy, and one Promotion Target.
`benchwork_prepare_patch_promotion` asks Athanor to prepare a
`patch-promotion-preview/1.0`. Preparation is read-only with respect to
canonical state and never materializes or applies patch bytes.

Before returning it, the Promotion Coordinator appends
`preview.prepared` to the Promotion Journal under the prepare idempotency-key
Sigil. The event embeds the validated Preview and complete prepare-request
Sigil. It also binds `prepare_binding_sigil`, defined as the Sigil of the
closed response-independent object
`{prepare_request_sigil, preview_id, preview_sigil,
idempotency_key_sigil}`. Only after that event and Head are durable does the
Coordinator construct the response over the raw token and committed Journal
Event ID and Sigil, then compute `response_sigil`. Neither the Preview nor
`preview.prepared` contains that response Sigil. An exact still-valid retry
reconstructs the same response from the event, binding, and protected token;
conflicting key reuse fails. This operational append is not a Chronicle
transition and grants no mutation authority.

Preparation is legal only while the coordinator clock gate is `TRUSTED`.
Under the Journal writer lock it derives `expires_at` with checked UTC
arithmetic from the exact bound deadline policy, appends the Preview, replaces
the Head, and establishes its monotonic anchor before returning it. Arithmetic
failure, missing time evidence, or inability to establish the anchor rejects
Prepare rather than creating a longer-lived Preview.

The Preview binds:

- the Proposal, Base, Patch Bundle, and expected Postimage Sigils;
- the exact passing Validation Evidence Sigils and Validation Policy Sigil;
- the target ID, target identity profile, observed target preimage identity,
  and target-state evidence Sigil;
- the application-adapter ID, version, configuration Sigil, and exact
  application mode;
- the trusted UTC source profile and exact deadline-policy Sigils;
- the sorted affected paths, entry operations, scope, and residual risks;
- the exact current Recovery lineage or abandoned-lineage re-entry binding
  selected by the exhaustive fence matrix, with the other branch null;
- the Preview ID, idempotency scope, durable UTC `expires_at`, and Preview
  Sigil; and
- the Sigil of a single-use confirmation token, never its raw bytes.

The confirmation token is bounded operational authorization material generated
from at least 256 bits of entropy obtained directly from an operating-system
CSPRNG. Its canonical wire encoding is unpadded base64url of exactly 32 random
bytes. Its digest is
`SHA-256("benchwork:patch-confirmation-token:v1\0" || raw_token_bytes)`; this
domain-separated digest, represented as a Sigil, is the only token value
permitted in canonical or inspectable records. Validation decodes to a fixed
32-byte value and compares digests in constant time.

The raw token is emitted only by Prepare and an exact still-valid idempotent
Prepare retry. At rest it exists only as authenticated ciphertext inside the
protected `preview.prepared` payload under a versioned local token-storage
profile and may be presented only once on the protected local Authorize request
path; that request is redacted before diagnostics and its complete canonical
request Sigil is computed over the token digest rather than raw token bytes.
The raw value never appears in Authorize responses, Inspect, logs, diagnostics,
exported evidence, Chronicle, or an ordinary state projection. A consumed,
rejected, expired, mismatched, or unavailable token fails closed and cannot be
regenerated for the same Preview.

Target paths may be shown locally by the Host, but absolute Host paths and
credentials do not enter MCP results or Chronicle. A target ID is a logical
identifier, not proof of current content.

Athanor verifies the Proposal and evidence relationships. Ordinary `PROMOTE`
against an absent or `CLEAR` logical fence requires target-state identity equal
to the Proposal Base. `RECOVER_PARTIAL` instead requires the current
`ACTIVE` fence's exact observed identity/generation and latest canonical
lineage; abandoned re-entry requires the preserved `ABANDONED` identity,
generation, and binding. It also rechecks Task and Snapshot freshness,
Capability and Execution Specification Sigils, policy eligibility, Blob
availability, and that no terminal promotion already consumes the same
authorization. Any relevant change produces a new Preview; subset
authorization is not inferred.

### 2. Explicit human authorization

Promotion always requires an explicit human confirmation of the exact Preview.
The approval that authorized code modification inside a Crucible, general Host
or shell permission, a Ward `PASS`, a passing validation set, a previous patch
approval, or the original research request does not satisfy this confirmation.

`benchwork_authorize_patch_promotion` terminalizes the Preview with exactly one
human decision. The Promotion Coordinator first acquires RFC-0013's outer
canonical-reference gate and then the exclusive Promotion Journal writer lock,
retaining the gate for the entire normal decision path but holding the Journal
lock only for local replay and append phases. Under the Journal lock it replays
state, establishes a trusted clock anchor, processes all already-due Preview
expiries in the deterministic deadline order below, and requires the selected
Preview still to be `PREPARED` and strictly before `expires_at`. Every expiry
observer acquires this same outer gate before the Promotion Journal lock.

For `AUTHORIZE`, it verifies the fixed-length token in constant time and the
affirmative confirmation. For `REJECT`, it verifies the explicit negative
decision and absence of a token. Before contacting Athanor, it appends and
fsyncs `preview.decision-submission-started`, binding the Preview, decision,
trusted decision time and clock-anchor evidence Sigil, complete redacted request
Sigil, idempotency-key Sigil, actor and Host provenance, and expected Chronicle
Head, then releases the Promotion Journal lock while retaining the gate. The
payload fixes the complete selected Head through:

```text
expected_chronicle_head_sigil =
  json_sigil(["patch-expected-chronicle-head/1.0",
              expected_chronicle_head])
```

For both decision branches, final request construction and every recovery path
must recompute this formula over
`final_request.expected_chronicle_head` and obtain the event's exact
`expected_chronicle_head_sigil`; they may not resample a later Head. A mismatch
is `PATCH_IDEMPOTENCY_CONFLICT` and creates no request slot, Reference Intent,
or canonical Event. It follows the canonical pin sequence: finalize the
decision record, register its
derived Reference Set under only the Storage lock, finalize the Athanor
request, commit the reference intent under only the Storage lock, and contact
Chronicle with no local journal lock held. Athanor independently verifies the
bound clock policy and anchor
evidence, requires both the trusted decision time and the canonical Event
commit/`occurred_at` linearization time to precede `expires_at`, and appends
exactly `patch.promotion.authorized` or `patch.promotion.rejected`. A submitted
call that crosses the deadline commits neither decision and returns a
definitive pre-commit failure; the Coordinator then reacquires only the
Promotion Journal lock and appends
`preview.decision-failed` with reason `DEADLINE_CROSSED`, the stable failure ID,
the complete bounded `PatchErrorDetails` including its Sigil, and Chronicle
absence proof, commits its Head, and releases that lock. While still holding
the gate, it replays the verified Chronicle Head. The definitive Athanor
failure makes the local decision terminal but does not by itself authorize
release of the reference intent. Only when the verified Head has advanced
beyond the intent's expected Head and RFC-0013's complete
`HEAD_SUPERSEDED_WITHOUT_BOUND_EVENT` authority proves the exact candidate
absent may the Coordinator use only the Storage lock to append
`canonical_reference.released` through
`ABORTED_BEFORE_CANONICAL_COMMIT`. An unchanged, unavailable, invalid, or
ambiguous Head leaves the intent `OPEN`; a later gate holder retries the same
proof. `preview.expired` is reserved for a `PREPARED` Preview for which no
decision submission was durably started.

After receiving and verifying the Receipt, the Coordinator first appends and
verifies RFC-0013 `canonical_reference.committed` under only the Storage lock
and the still-held outer gate, then releases the Storage lock. It next acquires
only the Promotion Journal lock, appends and fsyncs
`canonical.receipt-observed`, verifies the new Head, releases that lock, and
finally releases the gate. The `AUTHORIZE` submission has already marked its
token consumed; the observation preserves that value. The `REJECT` submission
has already made the token unavailable, and the observation terminalizes the
Preview as rejected. No expiry observer or GC plan can interleave with that
sequence.

An ambiguous transport response leaves the Preview `DECIDING` and the
reference intent `OPEN`; the immediate linearizable lookup retains the outer
gate but holds no local journal lock. If the lookup remains unavailable, the
Coordinator releases the gate before returning a retryable result; the durable
`DECIDING` state forbids expiry or mutation and the open intent forbids GC.
After a crash, replay reacquires the gate before the Promotion Journal lock,
classifies every `DECIDING` Preview, releases that lock, and performs the
linearizable Athanor lookup using its exact request and idempotency Sigils
before processing any expiry. It reacquires only the lock needed for each
resulting Storage or Promotion event: an existing authorization or rejection
Receipt is observed and wins permanently; a definitively aborted pre-commit
transition becomes `DECISION_FAILED` with a durable stable failure and cannot
later become `EXPIRED`. That local terminal state may coexist with an `OPEN`
reference intent until the verified Head advances and the exact RFC-0013
absence authority validates. Unavailable or ambiguous Chronicle state leaves
the submission `DECIDING` and fail-closed. A canonical
decision that already committed can therefore never be overwritten by
`preview.expired` or repeated.

`patch-promotion-authorization/1.0` is self-contained for Chronicle replay. It
copies every non-secret Preview binding required to identify the Proposal,
Base, Postimage, target, target-state evidence, validation set, adapter, mode,
affected paths, expiry, and residual risks; it also binds the Preview Sigil,
confirmation-token Sigil, actor and Host provenance, confirmation time,
clock-policy and anchor-evidence Sigils, complete redacted authorize-request
Sigil, and idempotency-key Sigil. Replay never depends on the Promotion Journal
or raw token to reconstruct what was authorized. The Receipt authorizes only:

The embedded `target_state_evidence` is the complete closed
`patch-target-state-evidence/1.0`, not an operational Ref. Its identity and
Sigil equal the Preview's `target_state_evidence` Ref;
`target_content_generation`, `affected_paths`, `operation_sigil`, and
`residual_risks` equal the Preview fields byte-for-byte. The authorization's
Proposal, target, Base, Postimage, validation, Adapter, mode, recovery,
expiry, and confirmation-token Sigil also equal the referenced Preview and
its canonical Proposal. Any mismatch is a Schema/replay failure. Consequently
the canonical authorization still proves the exact generation and change set
after the Promotion Journal is unavailable, including a target that changed
away and later returned to equal bytes.

- this Patch Proposal and Postimage;
- this Promotion Target at this Base Identity;
- this application adapter and mode;
- this validation policy and exact evidence set; and
- one idempotent logical application operation.

Changing the patch, payload, Base, target, evidence set, policy, adapter,
application mode, affected paths, recovery action, or expected Postimage
requires a new Preview and new human confirmation. Authorization does not
include commit creation, branch or ref update, merge, rebase, push,
pull-request creation, deployment, or publication.

`patch-promotion-rejection/1.0` is likewise self-contained. It binds the
Preview and Proposal Sigils, decision `REJECT`, actor and Host provenance,
bounded reason, trusted decision time, complete redacted request Sigil,
clock-policy and anchor-evidence Sigils, idempotency-key Sigil, and the fact
that no confirmation token or mutation authority was accepted. An exact retry
returns its original Receipt; conflicting reuse fails. Rejection and expiry
never delete the Proposal or Validation Evidence.

### 3. Host-native exact application

After authorization, the interactive Host uses its native repository, file,
patch, shell, and Git capabilities through the trusted Promotion Coordinator
and bound adapter. MCP does not expose patch bytes as a command, proxy a
filesystem or Git operation, or select commands for the Host. Athanor does not
open the target worktree or invoke Git.

The `0.4` reference adapter implements only
`FULL_TREE_ATOMIC_CAS`. It constructs the complete Postimage in isolated
staging, verifies it independently, and publishes it through one atomic
identity-checked target transaction. `PER_ENTRY_GENERATIONAL_CAS` remains an
optional non-reference profile and is eligible only under the stricter
platform proof below.

The project-wide active-guard cardinality is always at most
`MAX_ACTIVE_GUARDS`. Active means exactly `ACQUIRING`, `HELD`, `RENEWING`,
`RELEASING`, `FENCING`, or `RECOVERING`; historical `RELEASED`, `FENCED`, and
`FAILED` guards do not count. Immediately before
`target.guard-acquire-intent-committed`, the Coordinator replays under the
exclusive Journal writer lock and requires:

```text
active_guard_count + 1 <=
min(MAX_ACTIVE_GUARDS,
    adapter.guard_backend.max_active_guards,
    adapter.limits.max_active_guards)
```

Failure appends no guard event, performs no backend operation, and returns
`PATCH_GUARD_UNAVAILABLE` with reason `ACTIVE_GUARD_LIMIT`; an already
allocated Attempt terminalizes without a guard. Recovery and clock fencing
must include every active guard in one bounded set. Replay projecting more
than 4096 active guards is `READ_ONLY_FAILED`, never a batch that silently
omits authority.

Before the first target content mutation, the Host-native adapter must:

1. load the exact authorization and verify its Receipt;
2. retrieve and verify every required immutable Blob;
3. allocate a unique `patch-promotion-attempt/1.0` and durably append
   `promotion.attempt-created`;
4. append `promotion.preflight-started`, allocate the next strictly increasing
   target fencing generation, and append and fsync
   `target.guard-acquire-intent-committed` before touching the physical guard;
5. acquire the exclusive target mutation guard for the exact coordinator epoch,
   target, Attempt, generation, and durable UTC expiry, verify its readback, and
   append and fsync `target.guard-acquired`;
6. open a stable descriptor for the exact target root without following a link,
   bind its root, device or mount, and ancestor identities, then recompute the
   complete target identity with the bound profile while holding and validating
   that guard and compare it with the Base and expected Postimage;
7. only if the target equals the exact Base, create a recoverable independent
   preimage checkpoint for every affected entry, verify its complete identity,
   finalize the checkpoint without future protection fields, register its
   derived operational Reference Set, append `retention.hold_set`, and append
   and fsync `promotion.checkpoint-committed` with the external `HoldBinding`;
8. append and fsync `promotion.ready` after every READY guard passes;
9. finalize the write-ahead mutation intent binding the authorization, Attempt,
   operation identity, guard and fence, checkpoint, Base, expected Postimage,
   complete operations Sigil, adapter configuration, root and ancestor
   identities, and expected verification method; register the finalized
   intent's derived operational Reference Set, append `retention.hold_set`, and
   append and fsync `promotion.mutation-intent-committed` with the external
   `HoldBinding`; and
10. immediately revalidate the guard, fencing floor, both deadline predicates,
    stable root, authorization and control/validation eligibility, complete
    target identity, and every affected-entry precondition before invoking the
    first native mutation.

If the target already equals the expected Postimage, the adapter performs no
write, creates neither a checkpoint nor mutation intent, and terminalizes the
Attempt as `ALREADY_APPLIED`. If it does not equal the Base, the Attempt
terminalizes as `STALE` without a checkpoint or target write. If it equals the
Base, the adapter follows the write-ahead sequence and applies the authoritative
entry operations without fuzzy context matching, implicit three-way merge,
rename inference, hook execution, network access, credential inheritance, or
unapproved filter execution. Any optional mechanism that can execute repository
code or change content semantics must be disabled or separately bound in the
Preview.

For `FULL_TREE_ATOMIC_CAS`, the adapter must:

1. materialize the entire declared scope in isolated staging from the exact
   Base plus committed Bundle payloads, without executing target-controlled
   hooks, filters, links, or code;
2. independently scan that staging tree and prove the complete expected
   Postimage identity and path topology;
3. append and Head-commit `target.guard-validated` for the single publish step,
   then execute one atomic publish CAS conditional on the exact Base identity,
   stable target root and publish-point ancestor identities, target-wide content
   generation, current guard ID and backend generation, coordinator epoch,
   fencing generation, fence floor, authorization, and both deadline
   predicates; and
4. require the backend to atomically advance the target-wide content
   generation and return a durable transaction receipt, then perform a
   linearizable generation and complete-tree readback before
   `promotion.verification-started`.

Before that verification event becomes visible, the adapter finalizes the
transaction-receipt/readback evidence record, derives its operational Reference
Set, appends `retention.hold_set`, and supplies `evidence_protection:
HoldBinding`.

The target-wide generation changes for every in-scope content or topology
mutation, including mutations by other writers; a platform cannot call a
per-adapter counter target-wide. The durable receipt binds the before and after
generation, root identities, Base, Postimage, guard tuple, transaction request
Sigil, commit point, and durability observation.
Generation strings are opaque bounded backend tokens, not lexically ordered
numbers; “advance” means the bound adapter verifies the backend's closed
successor proof and that an old token can never become current again.

An optional `PER_ENTRY_GENERATIONAL_CAS` adapter is eligible only if all of the
following are platform-enforced and bound in the Adapter, Preview, and mutation
intent:

- one monotonic target-wide content generation covers every in-scope mutation
  by every writer, and every entry CAS both compares and atomically advances
  it;
- the closed topology plan names every existing and newly created ancestor
  identity, pre-creates or stages parent objects without exposing them,
  orders additions parents before children and deletions children before
  parents, rejects file/directory and case collisions, and never traverses an
  unbound mount or link;
- each step is descriptor-relative and no-follow, compares the current global
  generation, exact entry precondition, root and ancestor identities, guard
  tuple, fence and deadline, writes through a fresh object rather than
  truncating an alias, and returns the exact next global generation plus a
  durable idempotent CAS receipt;
- before the next step, that receipt is finalized in immutable operational
  evidence, then that record becomes the source of a registered Reference Set
  and `retention.hold_set`; the next `target.guard-validated` frame binds its
  external `HoldBinding`; the final complete sorted receipt-set Sigil is bound
  by `promotion.verification-started`;
- crash recovery starts from the last proven global generation and receipt
  prefix, uses stable request Sigils to recover an ambiguous receipt, and
  never repeats a step whose non-commit cannot be proven; and
- any supported hard-link profile proves the complete in-scope alias set and
  the CAS semantics cover every alias consequence.

A platform whose global generation, topology identities, per-step receipt,
idempotent CAS, durable readback, or external-writer participation cannot be
verified is ineligible for per-entry mode. A prior full-tree scan, ordinary
rename, filesystem timestamp, or process-local lock is not an equivalent
control.

Guard expiry, renewal failure, fence change, authorization or control
ineligibility, root or ancestor change, or precondition failure during
application immediately stops further writes and classifies the observed
target as Base, Postimage, or `PARTIAL`/`CONFLICT` under the terminal rules.

The adapter applies through the chosen staging or transaction mechanism capable
of restoring the affected preimages. After the declared operations return, it
appends and fsyncs `promotion.verification-started`, validates the current guard
again, then scans the target with the same stable descriptor and identity
profile. Only exact equality with the expected Postimage is an applied result.
A command exit status, clean-looking diff, matching branch name, or existence
of some changed files is insufficient.

Eligible adapter-write evidence is an independently verifiable atomic
transaction receipt or complete sorted per-entry commit receipt set. It binds
the adapter, mutation intent, operation Sigil, guard tuple, fence floor,
descriptor-root identity, exact preimage and postimage, commit generation, and
durability observation, and it must survive coordinator restart. A process exit
status, mutable adapter log, target equality alone, or evidence first
reconstructed after a crash is not causal write evidence.

The target mutation guard is defense against concurrency, not identity.
Identity and preconditions are rechecked for every side effect while the guard
is held and live. A guard without exact comparison, or identity without the
current fencing generation, cannot authorize application.

### 4. Record the outcome

The Promotion Coordinator first commits the terminal Attempt event to the
Promotion Journal. The Host then submits the bounded
`patch-promotion-outcome/1.0` through
`benchwork_record_patch_promotion_outcome`. Before Athanor submission, the
Coordinator acquires the outer canonical-reference gate, finalizes the Outcome,
registers its new evidence Reference Set, includes the existing operational
sets, finalizes the request Sigil, and commits the reference intent. The Outcome
binds the authorization Receipt,
Promotion Attempt ID, terminal journal-event Sigil, operation identity, adapter
identity, before and after target identities, checkpoint and mutation-intent
identities when present, guard fencing generation, timestamps, terminal
status, affected-path observations, adapter-write evidence identity and
eligibility verdict when present, verifier evidence, and bounded diagnostics.
The guard field is explicitly null only for a legal terminal state reached
before guard allocation.

Athanor accepts only an outcome related to the exact authorization. It verifies
the outcome Schema, identities, evidence Sigils, transition legality,
Promotion Journal terminal-event binding, idempotency, and status-specific
requirements before appending the terminal record and issuing a Receipt. Raw
application logs, guard records, mutation intents, and checkpoints remain
outside Chronicle as bounded operational material or RFC-0013 Blobs.
The Coordinator commits the Receipt-backed canonical pin before releasing the
gate. With the Storage lock released and the gate still held, it then takes
the Promotion Journal lock and appends `canonical.receipt-observed`; for an
eligible non-`PARTIAL` Outcome with no other open intent and either its exact
terminal guard or a replay-proven `NO_GUARD_ALLOCATED` branch,
that Event names and transitions the exact owner roots to `INACTIVE`. It
verifies the new Head, releases the Promotion lock, and only
then releases the gate. Ambiguity leaves the pin and roots open and exact retry
resolves the original Outcome.

One Promotion Attempt has one of these terminal statuses:

| Status | Required meaning |
| --- | --- |
| `APPLIED` | The adapter changed a Base-identical target, eligible adapter-write evidence proves that causal write under the exact intent and guard, and an eligible verifier proved the exact expected Postimage. |
| `RECOVERED_POSTIMAGE_OBSERVED` | Replay found the exact expected Postimage after a durable mutation intent but lacks eligible evidence that this adapter caused it. No second write occurred and the status makes no causal claim. |
| `ALREADY_APPLIED` | The target already had the exact expected Postimage; the adapter made no content change. |
| `STALE` | Before mutation, the target, Task, Snapshot, policy, evidence, or authorization no longer matched the bound identity. No target write occurred. |
| `CONFLICT` | Exact application could not realize the Postimage because of an affected-path conflict or concurrent mutation. Evidence must state whether the target remained or returned to the Base; any other state is `PARTIAL`. |
| `FAILED` | An adapter or infrastructure failure occurred and evidence proves the target remained at, or was restored to, the Base. |
| `PARTIAL` | The target is provably neither the Base nor the expected Postimage after an interrupted or failed operation. Further promotion is fenced pending explicit recovery. |
| `CANCELLED` | Cancellation was accepted before any target content mutation. |

`APPLIED`, `RECOVERED_POSTIMAGE_OBSERVED`, and `ALREADY_APPLIED` are successful
materialization outcomes. Only `APPLIED` claims a verified adapter-caused
write. None automatically creates a Git commit, Artifact, Run, Assessment,
Decision, or Seal. `CONFLICT`, `FAILED`, `PARTIAL`, `CANCELLED`, `STALE`, and
every successful outcome remain append-only. No Promotion Attempt has an
outbound transition after any terminal status.

## Promotion Journal and state machines

The Promotion Journal is the sole operational authority for Promotion and
Recovery Attempt state. It is physically and logically separate from
Chronicle, the Executor journal, Git metadata, and the target worktree.
Chronicle remains canonical authority for accepted authorization and outcome
records; neither journal may import or rewrite the other's events.

Each `patch-promotion-journal-event/1.0` contains exactly:

- Schema version, journal ID, event ID, and one-based contiguous sequence;
- coordinator ID and monotonically increasing coordinator epoch;
- event type and non-decreasing recorded time from the coordinator clock
  authority; `coordinator.clock-uncertain` uses the last trusted anchor-derived
  time rather than an untrusted wall-clock reading;
- a sorted array of affected entity IDs with exact preceding and next
  revisions;
- optional causation-event ID and idempotency-key Sigil;
- one closed type-specific payload;
- previous-event Sigil, with `null` only at sequence one; and
- event Sigil over canonical JSON with that field omitted.

The exact closed `event_type` enum is:

```text
coordinator.epoch-started
coordinator.replay-started
coordinator.integrity-failed
coordinator.clock-uncertain
coordinator.clock-restored
canonical.receipt-observed

preview.prepared
preview.decision-submission-started
preview.decision-failed
preview.expired

target.guard-acquire-intent-committed
target.guard-acquired
target.guard-renew-intent-committed
target.guard-renewed
target.guard-validated
target.guard-release-intent-committed
target.guard-fence-intent-committed
target.guard-fenced
target.guard-released
target.guard-failed

promotion.attempt-created
promotion.preflight-started
promotion.checkpoint-committed
promotion.ready
promotion.mutation-intent-committed
promotion.verification-started
promotion.applied
promotion.recovered-postimage-observed
promotion.already-applied
promotion.stale
promotion.conflicted
promotion.failed
promotion.partial
promotion.cancelled

recovery.attempt-created
recovery.preflight-started
recovery.checkpoint-verified
recovery.ready
recovery.intent-committed
recovery.verification-started
recovery.base-restored
recovery.postimage-accepted
recovery.abandoned
recovery.stale
recovery.failed
recovery.partial
recovery.cancelled
```

The enum has exactly 47 values. The following table is the complete transition
table. `E:x->y` means entity `E` has exactly one matching `Rev` entry with its
current revision and next revision, and its state changes from `x` to `y`.
`E:x->x` still increments exactly once. A comma requires all named revisions
in the same event. In every row, each non-null protection payload field also
requires the one deterministic `operational_root:NONE->ACTIVE` revision
defined above; the root phrases printed in rows 23, 25, and 39 are that same
revision, not an additional one. No other entity revision is allowed. `Set`
fields use the bounds and byte-order rules above. Payloads are closed objects
containing exactly the named fields.

| # | `event_type` | Exact source and revisions | Exact payload fields and types | Exact destination |
| --- | --- | --- | --- | --- |
| 1 | `coordinator.epoch-started` | `coordinator:NONE\|REPLAYING->ACTIVE`, `clock:UNINITIALIZED\|TRUSTED->TRUSTED`; every named `operational_root:ACTIVE->INACTIVE` | `prior_epoch: U64`; `new_epoch: U64` exactly prior + 1; `replayed_head: Obj<HeadRef>`; `replayed_state_sigil: Sigil`; `clock_evidence_sigil: Sigil`; `completed_tail_recovery_id: Nullable<ID<PTRI>>`; `deactivated_operational_root_ids: Set<ID<PROOT>,0..MAX_STATE_ENTITIES,value>`; `started_at: Time` | Coordinator `ACTIVE`, clock `TRUSTED`; from `NONE`, current epoch becomes `new_epoch`; from `REPLAYING`, `new_epoch == source.current_epoch` (the replay-started Event already advanced it) and is not incremented again. Clock stores `last_trusted_utc == started_at` and this anchor Sigil. Named roots are exactly the completed healthy tail-recovery roots; after applying those revisions the matching open-tail-intent projection is empty |
| 2 | `coordinator.replay-started` | `coordinator:NONE\|ACTIVE\|REPLAYING->REPLAYING`; every listed `guard:ACQUIRING\|HELD\|RENEWING\|RELEASING\|RECOVERING->RECOVERING`; every listed `guard:FENCING->FENCING` | `prior_epoch: U64`; `recovery_epoch: U64` exactly prior + 1; `validated_head: Obj<HeadRef>`; `frames_file_size: U64`; `tail_recovery_id: Nullable<ID<PTRI>>`; `tail_recovery_intent_sigil: Nullable<Sigil>`; `suffix_evidence_sigil: Nullable<Sigil>`; `suffix_evidence_protection: Nullable<Obj<HoldBinding>>`; `unresolved_guards: Set<Obj<GuardRecoveryStart>,0..MAX_ACTIVE_GUARDS,guard_id>`; `started_at: Time` | `prior_epoch == source.current_epoch` and Coordinator becomes `REPLAYING` with `current_epoch == recovery_epoch`; `frames_file_size` equals `validated_head.committed_offset` before this event frame. All four tail fields are null when EOF already equaled the prior committed offset and non-null for staged suffix recovery; the non-null branch creates the exact active suffix root. A `REPLAYING` source is legal only for the tabled adopted-suffix re-entry; unresolved set equals every active guard |
| 3 | `coordinator.integrity-failed` | `coordinator:NONE\|ACTIVE\|REPLAYING\|READ_ONLY_FAILED->READ_ONLY_FAILED` | `reason: Enum<JOURNAL\|HEAD\|FRAME\|CLOCK\|GUARD\|TARGET\|STORAGE\|CHRONICLE\|SCHEMA>`; `evidence_sigils: Set<Sigil,1..MAX_EVIDENCE,value>`; `first_bad_offset: Nullable<U64>`; `first_bad_event_id: Nullable<ID<PJE>>`; `detected_at: Time` | Coordinator and project mutation gate `READ_ONLY_FAILED`; no skipped or inferred event |
| 4 | `coordinator.clock-uncertain` | `clock:TRUSTED->UNCERTAIN` | `last_trusted_utc: Time`; `observed_utc: Nullable<Time>`; `monotonic_status: Enum<OK\|RESET\|UNAVAILABLE>`; `divergence_seconds: Nullable<U64>`; `cause: Enum<ROLLBACK\|FORWARD_JUMP\|EXCESSIVE_SLEW\|MONOTONIC_RESET\|SUSPEND_UNKNOWN\|SOURCE_UNTRUSTED\|ARITHMETIC>`; `prior_anchor_evidence_sigil: Sigil`; `guards_to_fence: Set<ID<PG>,0..MAX_ACTIVE_GUARDS,value>`; `detected_at: Time` | Clock `UNCERTAIN`; projected `last_trusted_utc` and anchor Sigil equal these payload fields; set equals all active guards, and each must subsequently use events 17 then 18 before authority can resume |
| 5 | `coordinator.clock-restored` | `clock:UNCERTAIN->TRUSTED` | `trusted_source_sigil: Sigil`; `policy_sigil: Sigil`; `restored_utc: Time`; `new_anchor_evidence_sigil: Sigil`; `resolved_decision_ids: Set<ID<PRV>,0..MAX_EVIDENCE,value>`; `fenced_guard_ids: Set<ID<PG>,0..MAX_ACTIVE_GUARDS,value>` | Clock `TRUSTED` with projected UTC and anchor equal `restored_utc` and `new_anchor_evidence_sigil`; every old guard is terminal and all live deadlines have non-lengthening anchors. `resolved_decision_ids` lists only decision projections already terminalized by their own Events and changes no decision state |
| 6 | `canonical.receipt-observed` | `canonical_link:NONE->OBSERVED`; for `AUTHORIZATION\|REJECTION` also `preview:DECIDING->AUTHORIZED\|REJECTED`, `decision_submission:PENDING->AUTHORIZED\|REJECTED`, `decision_idempotency:PENDING->SUCCEEDED`; when `logical_fence_transition` is non-null, exactly one `logical_partial_fence:ACTIVE\|ABANDONED->ACTIVE\|ABANDONED\|CLEAR`; every named `operational_root:ACTIVE->INACTIVE` | `kind: Enum<AUTHORIZATION\|REJECTION\|PROPOSAL\|VALIDATION\|PROMOTION_OUTCOME\|RECOVERY_RECORD>`; `subject_id: Text<128>`; `submission_event_id: Nullable<ID<PJE>>`; `canonical_event_id: ID<CE>`; `event_body_sigil: Sigil`; `receipt: ReceiptRef`; `request_sigil: Sigil`; `canonical_commit_event: Obj<StorageEventRef>`; `resulting_chronicle_head_sigil: Sigil`; `logical_fence_transition: Nullable<Obj<LogicalFenceReceiptTransition>>`; `deactivated_operational_root_ids: Set<ID<PROOT>,0..MAX_STATE_ENTITIES,value>`; `observed_at: Time` | Immutable canonical link `OBSERVED` for every kind; decision branches additionally terminalize Preview, submission, and idempotency. `AUTHORIZATION` requires and preserves token `CONSUMED`; `REJECTION` requires and preserves token `UNAVAILABLE`. The optional fence transition is exact for a canonical `PARTIAL` Outcome, any Recovery Record, or a successful abandoned-lineage re-entry Outcome and null otherwise. The root set is empty except for a non-`PARTIAL` Outcome, a resolved or abandoned Recovery Record, and equals the applicable owner/lineage set; after applying those root revisions, the exact open-intent projection for each affected owner is empty. Guard completion is terminal except that a pre-allocation non-`PARTIAL` Outcome may prove no allocation; retention still delays Storage hold release |
| 7 | `preview.prepared` | `preview:NONE->PREPARED`, `prepare_idempotency:NONE->BOUND` | `preview: Obj<patch-promotion-preview/1.0>`; `prepare_request_sigil: Sigil`; `prepare_binding_sigil: Sigil`; `confirmation_token_ciphertext: Text<512>`; `token_storage_profile_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `monotonic_anchor_evidence_sigil: Sigil`; `original_remaining_ns: U64` | Preview `PREPARED` with token `AVAILABLE`; binding is the response-independent four-field projection defined in Prepare; no response or future Event Sigil is present |
| 8 | `preview.decision-submission-started` | `preview:PREPARED->DECIDING`, `decision_submission:NONE->PENDING`, `decision_idempotency:NONE->PENDING` | `preview_id: ID<PRV>`; `decision: Enum<AUTHORIZE\|REJECT>`; `decision_at: Time`; `clock_policy_sigil: Sigil`; `clock_evidence_sigil: Sigil`; `redacted_request_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `actor: Obj<ActorBinding>`; `host: Obj<HostBinding>`; `expected_chronicle_head_sigil: Sigil` | Preview `DECIDING`; token becomes `CONSUMED` for `AUTHORIZE` and `UNAVAILABLE` for `REJECT`; submission and idempotency are `PENDING`; expiry cannot overtake an unresolved canonical submission |
| 9 | `preview.decision-failed` | `preview:DECIDING->DECISION_FAILED`, `decision_submission:PENDING->FAILED`, `decision_idempotency:PENDING->FAILED` | `preview_id: ID<PRV>`; `decision: Enum<AUTHORIZE\|REJECT>`; `redacted_request_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `reason: Enum<DEFINITIVE_PRECOMMIT_ABORT\|CHRONICLE_HEAD_CONFLICT\|POLICY_INELIGIBLE\|STALE_BINDING\|DEADLINE_CROSSED>`; `error_details: Obj<PatchErrorDetails>`; `chronicle_absence_evidence_sigil: Sigil`; `deadline_evidence_sigil: Nullable<Sigil>`; `failed_at: Time` | Preview, submission, and idempotency `FAILED`; token remains `CONSUMED` for `AUTHORIZE` and `UNAVAILABLE` for `REJECT`; details have deterministic non-null failure/error IDs and `retryable: false`; deadline evidence is non-null exactly for `DEADLINE_CROSSED`; exact retry returns this durable object |
| 10 | `preview.expired` | `preview:PREPARED->EXPIRED` | `preview_id: ID<PRV>`; `expires_at: Time`; `trusted_utc: Time`; `deadline_basis: Enum<UTC\|MONOTONIC\|BOTH>`; `monotonic_elapsed_ns: U64`; `original_remaining_ns: U64`; `anchor_evidence_sigil: Sigil`; `decision_absence_evidence_sigil: Nullable<Sigil>`; `idempotency_key_sigil: Nullable<Sigil>` | Preview `EXPIRED` with token `UNAVAILABLE`; named predicate is due and no decision submission was durably started |
| 11 | `target.guard-acquire-intent-committed` | `guard:NONE->ACQUIRING` | `guard: Obj<patch-promotion-target-guard/1.0>`; `prior_backend_generation: Nullable<Text<256>>`; `intended_backend_generation: Text<256>`; `prior_fence_floor: U64`; `intended_fence_floor: U64`; `target_content_generation: Text<256>`; `deadline_policy_sigil: Sigil`; `clock_anchor_evidence_sigil: Sigil`; `original_remaining_ns: U64`; `backend_request_sigil: Sigil`; `committed_at: Time` | Guard `ACQUIRING`; resolved owner passes the current logical-fence admission matrix and no physical acquisition preceded this Event |
| 12 | `target.guard-acquired` | `guard:ACQUIRING->HELD` | `guard_id: ID<PG>`; `backend_request_sigil: Sigil`; `backend_receipt_sigil: Sigil`; `observed_backend_generation: Text<256>`; `observed_fence_floor: U64`; `fencing_generation: U64`; `expires_at: Time`; `clock_anchor_evidence_sigil: Sigil`; `original_remaining_ns: U64`; `readback_evidence_sigil: Sigil` | Guard `HELD`; observed values and deadline anchor equal the acquire intent |
| 13 | `target.guard-renew-intent-committed` | `guard:HELD->RENEWING` | `guard_id: ID<PG>`; `prior_backend_generation: Text<256>`; `intended_backend_generation: Text<256>`; `prior_expires_at: Time`; `intended_expires_at: Time`; `fencing_generation: U64`; `fence_floor: U64`; `intended_anchor_evidence_sigil: Sigil`; `intended_original_remaining_ns: U64`; `backend_request_sigil: Sigil`; `committed_at: Time` | Guard `RENEWING`; neither old due predicate holds, and the new deadline is strictly later but within renewal policy |
| 14 | `target.guard-renewed` | `guard:RENEWING->HELD` | `guard_id: ID<PG>`; `backend_request_sigil: Sigil`; `backend_receipt_sigil: Sigil`; `observed_backend_generation: Text<256>`; `prior_expires_at: Time`; `new_expires_at: Time`; `fencing_generation: U64`; `fence_floor: U64`; `new_anchor_evidence_sigil: Sigil`; `new_original_remaining_ns: U64`; `readback_evidence_sigil: Sigil` | Guard `HELD`; values and the newly authorized deadline equal the renewal intent |
| 15 | `target.guard-validated` | `guard:HELD->HELD` | `guard_id: ID<PG>`; `attempt_id: Text<128>`; `operation_step: U64`; `backend_generation: Text<256>`; `fencing_generation: U64`; `fence_floor: U64`; `target_content_generation: Text<256>`; `intended_target_content_generation: Text<256>`; `prior_step_receipt_sigil: Nullable<Sigil>`; `prior_step_protection: Obj<HoldBinding>`; `expires_at: Time`; `trusted_utc: Time`; `monotonic_elapsed_ns: U64`; `original_remaining_ns: U64`; `clock_anchor_evidence_sigil: Sigil`; `readback_evidence_sigil: Sigil` | Guard remains `HELD`; validation grants authority only when neither due predicate holds and the resolved owner still passes the exact logical-fence matrix; the receipt is null exactly at step zero and non-null thereafter, while protection is always non-null |
| 16 | `target.guard-release-intent-committed` | `guard:HELD->RELEASING` | `guard_id: ID<PG>`; `prior_backend_generation: Text<256>`; `intended_absence_generation: Text<256>`; `fencing_generation: U64`; `fence_floor: U64`; `cause: Enum<TERMINAL\|CANCELLED\|RECOVERY_COMPLETE\|SHUTDOWN>`; `backend_request_sigil: Sigil`; `committed_at: Time` | Guard `RELEASING`; no physical release preceded this event |
| 17 | `target.guard-fence-intent-committed` | `guard:ACQUIRING\|HELD\|RENEWING\|RELEASING\|RECOVERING->FENCING` | `guard_id: ID<PG>`; `origin_state: Enum<ACQUIRING\|HELD\|RENEWING\|RELEASING\|RECOVERING>`; `prior_backend_generation: Nullable<Text<256>>`; `intended_backend_generation: Text<256>`; `prior_fence_floor: U64`; `intended_fence_floor: U64` strictly greater; `prior_fencing_generation: U64`; `intended_fencing_generation: U64` strictly greater; `cause: Enum<EPOCH_CHANGE\|CLOCK_UNCERTAIN\|DEADLINE\|CRASH_RECOVERY\|PARTIAL\|INTEGRITY>`; `cause_evidence_sigil: Sigil`; `backend_request_sigil: Sigil`; `committed_at: Time` | Guard `FENCING`; no physical fence CAS for this request preceded the event |
| 18 | `target.guard-fenced` | `guard:FENCING->FENCED` | `guard_id: ID<PG>`; `fence_intent_event_id: ID<PJE>`; `backend_request_sigil: Sigil`; `backend_receipt_sigil: Sigil`; `observed_backend_generation: Text<256>`; `observed_fence_floor: U64`; `observed_fencing_generation: U64`; `readback_evidence_sigil: Sigil`; `fenced_at: Time` | Guard terminal `FENCED`; observations equal the fence intent |
| 19 | `target.guard-released` | `guard:RELEASING\|RECOVERING->RELEASED` | `guard_id: ID<PG>`; `release_intent_event_id: ID<PJE>`; `backend_request_sigil: Sigil`; `backend_receipt_sigil: Sigil`; `observed_absence_generation: Text<256>`; `observed_fencing_generation: U64`; `observed_fence_floor: U64`; `readback_evidence_sigil: Sigil`; `released_at: Time` | Guard terminal `RELEASED`; exact durable absence and preserved floor proved |
| 20 | `target.guard-failed` | `guard:ACQUIRING\|RENEWING\|RELEASING\|RECOVERING->FAILED` | `guard_id: ID<PG>`; `failed_phase: Enum<ACQUIRE\|RENEW\|RELEASE\|RECOVER>`; `backend_request_sigil: Nullable<Sigil>`; `observed_absence_generation: Text<256>`; `observed_fencing_generation: U64`; `observed_fence_floor: U64`; `failure_evidence_sigil: Sigil`; `reason: Enum<DEFINITIVE_REJECT\|LOST_BEFORE_USE\|UNSUPPORTED>`; `failed_at: Time` | Guard terminal `FAILED`; physical absence, durable floor, and no authority proved |
| 21 | `promotion.attempt-created` | `promotion_attempt:NONE->CREATED` | `attempt: Obj<patch-promotion-attempt/1.0>`; `authorization_receipt: ReceiptRef`; `created_at: Time` | Promotion Attempt `CREATED` only after the Authorization passes the current absent/`CLEAR` or exact `ABANDONED` logical-fence branch |
| 22 | `promotion.preflight-started` | `promotion_attempt:CREATED->PREFLIGHTING` | `attempt_id: ID<PAT>`; `authorization_sigil: Sigil`; `target_state_evidence_sigil: Sigil`; `target_content_generation: Text<256>`; `adapter_sigil: Sigil`; `started_at: Time` | Promotion Attempt `PREFLIGHTING` |
| 23 | `promotion.checkpoint-committed` | `promotion_attempt:PREFLIGHTING->PREFLIGHTING`, `checkpoint:NONE->COMMITTED`, `operational_root:NONE->ACTIVE` | `attempt_id: ID<PAT>`; `checkpoint: Ref<PCK>`; `checkpoint_protection: Obj<HoldBinding>`; `checkpoint_verification_sigil: Sigil`; `committed_at: Time` | Finalized checkpoint and external operational protection are durable before Journal visibility |
| 24 | `promotion.ready` | `promotion_attempt:PREFLIGHTING->READY` | `attempt_id: ID<PAT>`; `guard: Ref<PG>`; `checkpoint: Ref<PCK>`; `base_identity_sigil: Sigil`; `target_content_generation: Text<256>`; `control_revalidation_sigil: Sigil`; `ready_at: Time` | Promotion Attempt `READY`; current logical-fence branch and target evidence revalidate exactly |
| 25 | `promotion.mutation-intent-committed` | `promotion_attempt:READY->MUTATING`, `mutation_intent:NONE->COMMITTED`, `operational_root:NONE->ACTIVE` | `attempt_id: ID<PAT>`; `mutation_intent: Ref<PMI>`; `intent_protection: Obj<HoldBinding>`; `guard: Ref<PG>`; `target_content_generation: Text<256>`; `committed_at: Time` | Promotion Attempt `MUTATING`; current logical-fence branch revalidates, and the finalized intent and dependencies are already externally protected |
| 26 | `promotion.verification-started` | `promotion_attempt:MUTATING->VERIFYING` | `attempt_id: ID<PAT>`; `mutation_intent: Ref<PMI>`; `guard: Ref<PG>`; `fresh_target_identity_sigil: Sigil`; `fresh_target_content_generation: Text<256>`; `adapter_write_evidence_sigil: Nullable<Sigil>`; `evidence_protection: Obj<HoldBinding>`; `scan_evidence_sigil: Sigil`; `started_at: Time` | Promotion Attempt `VERIFYING`; all named evidence is protected before visibility; exact retry returns this event and does not increment revision |
| 27 | `promotion.applied` | `promotion_attempt:VERIFYING->APPLIED` | `attempt_id: ID<PAT>`; `terminal_status: Enum<APPLIED>`; `before_identity_sigil: Sigil`; `after_identity_sigil: Sigil`; `before_generation: Text<256>`; `after_generation: Text<256>`; `checkpoint_id: ID<PCK>`; `mutation_intent_id: ID<PMI>`; `guard_id: ID<PG>`; `adapter_write_evidence_sigil: Sigil`; `verifier_evidence_sigils: Set<Sigil,1..MAX_EVIDENCE,value>`; `path_observations_sigil: Sigil`; `diagnostics_sigil: Sigil`; `evidence_protection: Obj<HoldBinding>`; `terminal_at: Time` | Promotion Attempt terminal `APPLIED`; payload contains no Outcome ID or Outcome Sigil |
| 28 | `promotion.recovered-postimage-observed` | `promotion_attempt:VERIFYING->RECOVERED_POSTIMAGE_OBSERVED` | `attempt_id: ID<PAT>`; `terminal_status: Enum<RECOVERED_POSTIMAGE_OBSERVED>`; `before_identity_sigil: Sigil`; `after_identity_sigil: Sigil`; `before_generation: Text<256>`; `after_generation: Text<256>`; `checkpoint_id: ID<PCK>`; `mutation_intent_id: ID<PMI>`; `guard_id: ID<PG>`; `adapter_write_evidence_sigil: null`; `verifier_evidence_sigils: Set<Sigil,1..MAX_EVIDENCE,value>`; `path_observations_sigil: Sigil`; `diagnostics_sigil: Sigil`; `evidence_protection: Obj<HoldBinding>`; `terminal_at: Time` | Promotion Attempt terminal `RECOVERED_POSTIMAGE_OBSERVED`; no Outcome ID or Sigil |
| 29 | `promotion.already-applied` | `promotion_attempt:PREFLIGHTING\|READY->ALREADY_APPLIED` | `attempt_id: ID<PAT>`; `terminal_status: Enum<ALREADY_APPLIED>`; `observed_postimage_sigil: Sigil`; `target_content_generation: Text<256>`; `scan_evidence_sigil: Sigil`; `path_observations_sigil: Sigil`; `diagnostics_sigil: Sigil`; `evidence_protection: Obj<HoldBinding>`; `checkpoint_id: Nullable<ID<PCK>>`; `mutation_intent_id: null`; `terminal_at: Time` | Promotion Attempt terminal `ALREADY_APPLIED`; no Outcome ID or Sigil |
| 30 | `promotion.stale` | `promotion_attempt:PREFLIGHTING\|READY->STALE` | `attempt_id: ID<PAT>`; `terminal_status: Enum<STALE>`; `stale_kind: Enum<CONTROL\|VALIDATION\|TARGET\|AUTHORIZATION>`; `expected_sigil: Sigil`; `observed_sigil: Sigil`; `target_identity_sigil: Sigil`; `target_content_generation: Text<256>`; `evidence_sigil: Sigil`; `path_observations_sigil: Sigil`; `diagnostics_sigil: Sigil`; `evidence_protection: Obj<HoldBinding>`; `terminal_at: Time` | Promotion Attempt terminal `STALE`; no Outcome ID or Sigil |
| 31 | `promotion.conflicted` | `promotion_attempt:MUTATING->CONFLICT` | `attempt_id: ID<PAT>`; `terminal_status: Enum<CONFLICT>`; `conflict_kind: Enum<PATH\|ADD_OCCUPIED\|TYPE\|CASE\|GENERATION_CAS\|TOPOLOGY>`; `before_identity_sigil: Sigil`; `after_identity_sigil: Sigil`; `before_generation: Text<256>`; `after_generation: Text<256>`; `checkpoint_id: ID<PCK>`; `mutation_intent_id: ID<PMI>`; `evidence_sigil: Sigil`; `path_observations_sigil: Sigil`; `diagnostics_sigil: Sigil`; `evidence_protection: Obj<HoldBinding>`; `terminal_at: Time` | Promotion Attempt terminal `CONFLICT`; after identity is Base or event is invalid and must be `PARTIAL` |
| 32 | `promotion.failed` | `promotion_attempt:PREFLIGHTING\|READY\|MUTATING\|VERIFYING->FAILED` | `attempt_id: ID<PAT>`; `terminal_status: Enum<FAILED>`; `failed_phase: Enum<PREFLIGHT\|READY\|MUTATION\|VERIFICATION\|RECOVERY_REPLAY>`; `base_identity_sigil: Sigil`; `observed_identity_sigil: Sigil`; `target_content_generation: Text<256>`; `checkpoint_id: Nullable<ID<PCK>>`; `mutation_intent_id: Nullable<ID<PMI>>`; `evidence_sigil: Sigil`; `path_observations_sigil: Sigil`; `diagnostics_sigil: Sigil`; `evidence_protection: Obj<HoldBinding>`; `terminal_at: Time` | Promotion Attempt terminal `FAILED`; evidence proves exact Base |
| 33 | `promotion.partial` | `promotion_attempt:MUTATING\|VERIFYING->PARTIAL`, `logical_partial_fence:NONE\|CLEAR\|ABANDONED->ACTIVE` | `attempt_id: ID<PAT>`; `terminal_status: Enum<PARTIAL>`; `base_identity_sigil: Sigil`; `postimage_identity_sigil: Sigil`; `observed_identity_sigil: Sigil`; `target_content_generation: Text<256>`; `checkpoint_id: ID<PCK>`; `mutation_intent_id: ID<PMI>`; `logical_fence_generation: U64`; `evidence_sigil: Sigil`; `path_observations_sigil: Sigil`; `diagnostics_sigil: Sigil`; `evidence_protection: Obj<HoldBinding>`; `terminal_at: Time` | Promotion Attempt terminal `PARTIAL`; the target fence is `ACTIVE`, its new head is this Event, its unresolved-Recovery slot is null, and operational roots remain active. Generation is 1 from `NONE`, otherwise checked prior + 1; an `ABANDONED` source additionally requires the Attempt's exact abandoned-lineage authorization |
| 34 | `promotion.cancelled` | `promotion_attempt:CREATED\|PREFLIGHTING\|READY->CANCELLED` | `attempt_id: ID<PAT>`; `terminal_status: Enum<CANCELLED>`; `cancel_request_sigil: Nullable<Sigil>`; `no_intent_proof_sigil: Sigil`; `observed_identity_sigil: Sigil`; `target_content_generation: Text<256>`; `path_observations_sigil: Sigil`; `diagnostics_sigil: Sigil`; `evidence_protection: Obj<HoldBinding>`; `terminal_at: Time` | Promotion Attempt terminal `CANCELLED`; no target content mutation |
| 35 | `recovery.attempt-created` | `recovery_attempt:NONE->CREATED`, `logical_partial_fence:ACTIVE->ACTIVE` | `recovery_attempt: Obj<patch-promotion-recovery-attempt/1.0>`; `authorization_receipt: ReceiptRef`; `parent_outcome_receipt: ReceiptRef`; `logical_fence_generation: U64`; `created_at: Time` | Recovery Attempt `CREATED`; parent remains `PARTIAL`; current fence and authorized lineage match exactly, the prior unresolved-Recovery slot is null, and this Event atomically sets it to the new Recovery Attempt ID |
| 36 | `recovery.preflight-started` | `recovery_attempt:CREATED->PREFLIGHTING` | `recovery_attempt_id: ID<PRA>`; `action: Enum<RESTORE_BASE\|ACCEPT_POSTIMAGE\|ABANDON>`; `guard: Ref<PG>`; `target_state_evidence_sigil: Sigil`; `target_content_generation: Text<256>`; `started_at: Time` | Recovery Attempt `PREFLIGHTING` |
| 37 | `recovery.checkpoint-verified` | `recovery_attempt:PREFLIGHTING->PREFLIGHTING` | `recovery_attempt_id: ID<PRA>`; `checkpoint: Ref<PCK>`; `checkpoint_protection: Obj<HoldBinding>`; `checkpoint_verification_sigil: Sigil`; `verified_at: Time` | Recovery Attempt remains `PREFLIGHTING`; checkpoint and external protection verified |
| 38 | `recovery.ready` | `recovery_attempt:PREFLIGHTING->READY` | `recovery_attempt_id: ID<PRA>`; `action: Enum<RESTORE_BASE\|ACCEPT_POSTIMAGE\|ABANDON>`; `guard: Ref<PG>`; `checkpoint: Ref<PCK>`; `bound_before_identity_sigil: Sigil`; `target_content_generation: Text<256>`; `ready_at: Time` | Recovery Attempt `READY` |
| 39 | `recovery.intent-committed` | `recovery_attempt:READY->RECOVERING`, `recovery_intent:NONE->COMMITTED`, `operational_root:NONE->ACTIVE` | `recovery_attempt_id: ID<PRA>`; `recovery_intent: Ref<PRI>`; `intent_protection: Obj<HoldBinding>`; `guard: Ref<PG>`; `target_content_generation: Text<256>`; `committed_at: Time` | Recovery Attempt `RECOVERING`; finalized intent and dependencies are already externally protected |
| 40 | `recovery.verification-started` | `recovery_attempt:RECOVERING->VERIFYING` | `recovery_attempt_id: ID<PRA>`; `recovery_intent: Ref<PRI>`; `action: Enum<RESTORE_BASE\|ACCEPT_POSTIMAGE\|ABANDON>`; `scan_status: Enum<VERIFIED\|UNVERIFIABLE>`; `fresh_target_identity_sigil: Nullable<Sigil>`; `fresh_target_content_generation: Nullable<Text<256>>`; `evidence_protection: Obj<HoldBinding>`; `scan_evidence_sigil: Sigil`; `started_at: Time` | Recovery Attempt `VERIFYING`; verified values are non-null only for `VERIFIED`; all evidence is protected before visibility; replay repeats only the fresh scan, never the recovery write |
| 41 | `recovery.base-restored` | `recovery_attempt:VERIFYING->BASE_RESTORED`, `logical_partial_fence:ACTIVE->ACTIVE` | `recovery_attempt_id: ID<PRA>`; `terminal_status: Enum<BASE_RESTORED>`; `action: Enum<RESTORE_BASE>`; `before_identity_sigil: Sigil`; `after_identity_sigil: Sigil`; `before_generation: Text<256>`; `after_generation: Text<256>`; `checkpoint_id: ID<PCK>`; `recovery_intent_id: ID<PRI>`; `guard_id: ID<PG>`; `verifier_evidence_sigils: Set<Sigil,1..MAX_EVIDENCE,value>`; `evidence_protection: Obj<HoldBinding>`; `logical_fence_generation: U64`; `terminal_at: Time` | Recovery Attempt terminal `BASE_RESTORED`; fence head advances with null canonical record and the same generation; unresolved slot remains this Attempt until its Recovery Record Receipt |
| 42 | `recovery.postimage-accepted` | `recovery_attempt:VERIFYING->POSTIMAGE_ACCEPTED`, `logical_partial_fence:ACTIVE->ACTIVE` | `recovery_attempt_id: ID<PRA>`; `terminal_status: Enum<POSTIMAGE_ACCEPTED>`; `action: Enum<ACCEPT_POSTIMAGE>`; `before_identity_sigil: Sigil`; `after_identity_sigil: Sigil`; `before_generation: Text<256>`; `after_generation: Text<256>`; `checkpoint_id: ID<PCK>`; `recovery_intent_id: ID<PRI>`; `guard_id: ID<PG>`; `verifier_evidence_sigils: Set<Sigil,1..MAX_EVIDENCE,value>`; `evidence_protection: Obj<HoldBinding>`; `logical_fence_generation: U64`; `terminal_at: Time` | Recovery Attempt terminal `POSTIMAGE_ACCEPTED`; fence head advances with null canonical record and the same generation; unresolved slot remains this Attempt until its Recovery Record Receipt |
| 43 | `recovery.abandoned` | `recovery_attempt:VERIFYING->ABANDONED`, `logical_partial_fence:ACTIVE->ACTIVE` | `recovery_attempt_id: ID<PRA>`; `terminal_status: Enum<ABANDONED>`; `action: Enum<ABANDON>`; `before_identity_sigil: Sigil`; `after_identity_sigil: Sigil`; `before_generation: Text<256>`; `after_generation: Text<256>`; `checkpoint_id: ID<PCK>`; `recovery_intent_id: ID<PRI>`; `guard_id: ID<PG>`; `verifier_evidence_sigils: Set<Sigil,1..MAX_EVIDENCE,value>`; `evidence_protection: Obj<HoldBinding>`; `logical_fence_generation: U64`; `terminal_at: Time` | Recovery Attempt terminal `ABANDONED`; before and after identities and generations are equal to the bound-before and fresh verified observation, and the fence generation is unchanged. Fence head advances with null canonical record; unresolved slot remains this Attempt until its Receipt |
| 44 | `recovery.stale` | `recovery_attempt:PREFLIGHTING\|READY\|VERIFYING->STALE`, `logical_partial_fence:ACTIVE->ACTIVE` | `recovery_attempt_id: ID<PRA>`; `terminal_status: Enum<STALE>`; `action: Enum<RESTORE_BASE\|ACCEPT_POSTIMAGE\|ABANDON>`; `expected_identity_sigil: Sigil`; `observed_identity_sigil: Sigil`; `target_content_generation: Text<256>`; `recovery_intent_id: Nullable<ID<PRI>>`; `verification_event_id: Nullable<ID<PJE>>`; `evidence_sigil: Sigil`; `evidence_protection: Obj<HoldBinding>`; `logical_fence_generation: U64`; `terminal_at: Time` | Recovery Attempt terminal `STALE`; intent-present source must be `VERIFYING`; fence head advances at the same generation and unresolved slot remains this Attempt until its Receipt |
| 45 | `recovery.failed` | `recovery_attempt:PREFLIGHTING\|READY\|VERIFYING->FAILED`, `logical_partial_fence:ACTIVE->ACTIVE` | `recovery_attempt_id: ID<PRA>`; `terminal_status: Enum<FAILED>`; `action: Enum<RESTORE_BASE\|ACCEPT_POSTIMAGE\|ABANDON>`; `failed_phase: Enum<PREFLIGHT\|READY\|VERIFICATION\|CRASH_REPLAY>`; `observed_identity_sigil: Sigil`; `target_content_generation: Text<256>`; `recovery_intent_id: Nullable<ID<PRI>>`; `verification_event_id: Nullable<ID<PJE>>`; `evidence_sigil: Sigil`; `evidence_protection: Obj<HoldBinding>`; `logical_fence_generation: U64`; `terminal_at: Time` | Recovery Attempt terminal `FAILED`; intent-present source must be `VERIFYING`; fence head advances at the same generation and unresolved slot remains this Attempt until its Receipt |
| 46 | `recovery.partial` | `recovery_attempt:VERIFYING->PARTIAL`, `logical_partial_fence:ACTIVE->ACTIVE` | `recovery_attempt_id: ID<PRA>`; `terminal_status: Enum<PARTIAL>`; `action: Enum<RESTORE_BASE>`; `base_identity_sigil: Sigil`; `postimage_identity_sigil: Sigil`; `observed_identity_sigil: Sigil`; `target_content_generation: Text<256>`; `checkpoint_id: ID<PCK>`; `recovery_intent_id: ID<PRI>`; `verification_event_id: ID<PJE>`; `logical_fence_generation: U64`; `evidence_sigil: Sigil`; `evidence_protection: Obj<HoldBinding>`; `terminal_at: Time` | Recovery Attempt terminal `PARTIAL`; fence head advances and its generation is checked prior + 1; unresolved slot remains this Attempt until its Receipt |
| 47 | `recovery.cancelled` | `recovery_attempt:CREATED\|PREFLIGHTING\|READY->CANCELLED`, `logical_partial_fence:ACTIVE->ACTIVE` | `recovery_attempt_id: ID<PRA>`; `terminal_status: Enum<CANCELLED>`; `action: Enum<RESTORE_BASE\|ACCEPT_POSTIMAGE\|ABANDON>`; `no_intent_proof_sigil: Sigil`; `observed_identity_sigil: Sigil`; `target_content_generation: Text<256>`; `evidence_protection: Obj<HoldBinding>`; `logical_fence_generation: U64`; `terminal_at: Time` | Recovery Attempt terminal `CANCELLED`; no recovery content mutation; fence head advances at the same generation and unresolved slot remains this Attempt until its Receipt |

The following is the complete 19-row Evidence Projection. `S(...)` is the
exact sorted unique manifest `evidence_sigils` set. Each value must resolve as
exactly one tabled Blob or control-record member as defined above. `C(...)`
adds the named records to `control_records` independently of those typed
evidence values; `optional` means present exactly when the corresponding
payload ID is non-null. `blob_refs` and `control_records` equal the named
closure plus the unique resolutions of `S(...)`, with no extra member.
Every `C(...)` token has one exact `StorageControlRef` projection:
`checkpoint` is `{schema_version:
patch-promotion-checkpoint/1.0, record_id: checkpoint.id, record_sigil:
checkpoint.sigil}`; `mutation_intent` is `{schema_version:
patch-promotion-mutation-intent/1.0, record_id: mutation_intent.id,
record_sigil: mutation_intent.sigil}`; `recovery_intent` is `{schema_version:
patch-promotion-recovery-intent/1.0, record_id: recovery_intent.id,
record_sigil: recovery_intent.sigil}`; `guard` is `{schema_version:
patch-promotion-target-guard/1.0, record_id: guard.id, record_sigil:
guard.sigil}`; and
`verification Event` is `{schema_version:
patch-promotion-journal-event/1.0, record_id: verification_event.event_id,
record_sigil: verification_event.event_sigil}`. Each complete record resolves
and verifies; a Sigil-only lookup or alternate Schema is invalid.
`claims_sigil` covers every remaining closed payload field after removing only
the protection field and the fields explicitly named under `S(...)`. Every
row includes the cross-field predicate `cardinality(S(...)) <=
MAX_EVIDENCE`, even when one component field independently permits
`MAX_EVIDENCE` members. Thus `promotion.applied` admits at most 4,096 distinct
values across adapter-write, path-observation, diagnostics, and verifier
evidence, while `promotion.recovered-postimage-observed` admits at most 4,096
across path-observation, diagnostics, and verifier evidence. When
`adapter_write_evidence_sigil` is present, its exact aggregate Blob is in
`S(...)`; resolving its closed `receipt_sigils` additionally adds every typed
Adapter receipt Blob, and only those receipt Blobs, to `blob_refs`. The
complete `C(...)` plus resolved
`S(...)` member closure and both computed Reference Set collections must also
satisfy the aggregate bounds above before the Event or any protection record
is written.

| Activation Event and protection field | Exact owner / role | Exact `S(...)` | Exact additional `C(...)` and branch constraint |
| --- | --- | --- | --- |
| `coordinator.replay-started.suffix_evidence_protection` | `JOURNAL_SUFFIX` body | `S(original_suffix_blob.blob_sigil)` | the complete suffix branch above; the Event's `suffix_evidence_sigil == manifest_sigil`; the four nullable tail fields are all null with no manifest/root or all non-null with exactly one |
| `target.guard-validated.prior_step_protection` | replay-resolved `PROMOTION` or `RECOVERY`; `GUARD_VALIDATION` | `S(clock_anchor_evidence_sigil, readback_evidence_sigil, prior_step_receipt_sigil when non-null)` | `C(guard)`; the non-null prior-step receipt is resolved exactly once through `S(...)` and creates no duplicate control edge; receipt is null only at step zero, protection never is |
| `promotion.verification-started.evidence_protection` | `PROMOTION`; `VERIFICATION` | `S(scan_evidence_sigil, adapter_write_evidence_sigil when non-null)` | `C(mutation_intent, guard)`; the optional aggregate Adapter Blob is absent exactly when null; when present its exact receipt Blob closure is also included |
| `promotion.applied.evidence_protection` | `PROMOTION`; `TERMINAL` | `S(adapter_write_evidence_sigil, path_observations_sigil, diagnostics_sigil, every verifier_evidence_sigils member)` | `C(checkpoint, mutation_intent, guard)`; exact aggregate and receipt Adapter Blob closure included |
| `promotion.recovered-postimage-observed.evidence_protection` | `PROMOTION`; `TERMINAL` | `S(path_observations_sigil, diagnostics_sigil, every verifier_evidence_sigils member)` | `C(checkpoint, mutation_intent, guard)`; the null adapter-write field creates no member |
| `promotion.already-applied.evidence_protection` | `PROMOTION`; `TERMINAL` | `S(scan_evidence_sigil, path_observations_sigil, diagnostics_sigil)` | optional `C(checkpoint)`; mutation intent is null |
| `promotion.stale.evidence_protection` | `PROMOTION`; `TERMINAL` | `S(evidence_sigil, path_observations_sigil, diagnostics_sigil)` | no additional control; claims include stale kind and expected/observed identities |
| `promotion.conflicted.evidence_protection` | `PROMOTION`; `TERMINAL` | `S(evidence_sigil, path_observations_sigil, diagnostics_sigil)` | `C(checkpoint, mutation_intent)`; claims include both identities and generations |
| `promotion.failed.evidence_protection` | `PROMOTION`; `TERMINAL` | `S(evidence_sigil, path_observations_sigil, diagnostics_sigil)` | optional `C(checkpoint, mutation_intent)` exactly by the terminal source-state/null matrix |
| `promotion.partial.evidence_protection` | `PROMOTION`; `TERMINAL` | `S(evidence_sigil, path_observations_sigil, diagnostics_sigil)` | `C(checkpoint, mutation_intent)`; claims include the logical fence and all three identities |
| `promotion.cancelled.evidence_protection` | `PROMOTION`; `TERMINAL` | `S(no_intent_proof_sigil, path_observations_sigil, diagnostics_sigil)` | no additional control; nullable `cancel_request_sigil` is a closed audit claim in `claims_sigil`, not a Storage member; claims also include the observed identity |
| `recovery.verification-started.evidence_protection` | `RECOVERY`; `VERIFICATION` | `S(scan_evidence_sigil)` | `C(recovery_intent)`; fresh identity and generation are both non-null only for `VERIFIED` |
| `recovery.base-restored.evidence_protection` | `RECOVERY`; `TERMINAL` | `S(every verifier_evidence_sigils member)` | `C(checkpoint, recovery_intent, guard)` |
| `recovery.postimage-accepted.evidence_protection` | `RECOVERY`; `TERMINAL` | `S(every verifier_evidence_sigils member)` | `C(checkpoint, recovery_intent, guard)` |
| `recovery.abandoned.evidence_protection` | `RECOVERY`; `ABANDONMENT` | `S(every verifier_evidence_sigils member)` | `C(checkpoint, recovery_intent, guard)`; claims include the preserved logical-fence generation |
| `recovery.stale.evidence_protection` | `RECOVERY`; `TERMINAL` | `S(evidence_sigil)` | `C(recovery_intent, verification Event)` exactly for a `VERIFYING` source; both are absent otherwise |
| `recovery.failed.evidence_protection` | `RECOVERY`; `TERMINAL` | `S(evidence_sigil)` | `C(recovery_intent, verification Event)` exactly for a `VERIFYING` source; both are absent otherwise |
| `recovery.partial.evidence_protection` | `RECOVERY`; `TERMINAL` | `S(evidence_sigil)` | `C(checkpoint, recovery_intent, verification Event)` |
| `recovery.cancelled.evidence_protection` | `RECOVERY`; `TERMINAL` | `S(no_intent_proof_sigil)` | no additional control; claims include action and observed identity, and no recovery intent exists |

The admitting Event reprojects its exact payload and must reproduce the
manifest owner, role, `claims_sigil`, evidence set, typed member closure,
activation tuple, RootPlan, and HoldBinding byte-for-byte. No generic
“all fields ending in `_sigil`” rule is permitted.

### Exact terminal-record projection

Terminal records are a deterministic backward projection, not a second
description that may disagree with the Promotion Journal. For any complete
`TreeIdentity x`:

```text
tree_identity_sigil(x) =
  Sigil(["patch-tree-identity-object/1.0", x])

path_observations_sigil(outcome) =
  byte_sigil(canonical_json(outcome.path_observations))

diagnostics_sigil(outcome) =
  byte_sigil(UTF8(outcome.diagnostics))

adapter_write_evidence_sigil(evidence) =
  byte_sigil(canonical_json(evidence))
```

For `entry_identity_sigil(path, entry)`, use
`json_sigil(["patch-path-entry-identity/1.0", path, entry])`; a missing
manifest member is the exact `ABSENT` branch. `path_observations` contains
exactly one member for every Authorization affected path and no other path.
For that path, expected pre/post values are the corresponding Patch
Operation's EntryIdentity branches, while observed pre/post values are the
exact lookups in `before_identity` and `after_identity` manifests. All four
Sigils use the formula above. `status` is `MATCH` exactly when observed
postimage equals expected postimage byte-for-byte and is `MISMATCH` otherwise.
An incomplete or unverifiable lookup cannot construct an Outcome and enters
integrity failure rather than emitting a partial observation set.

The path-observation array and diagnostics bytes are committed Blobs with
fixed media types
`application/vnd.benchwork.patch-path-observations+json` and
`text/plain; charset=utf-8`. A non-null Adapter value resolves the exact
aggregate Blob and typed receipt closure defined above. Every member of
`verifier_evidence` has fixed media type
`application/vnd.benchwork.patch-verifier-evidence+json`; its Sigil and size
equal the resolved terminal Manifest Blob. A control record, another media
type, alternate bytes, or an extra verifier member is invalid.

IDs are single assignment:

```text
outcome_id =
  "PO-" + first_32_lower_hex(
    SHA-256("benchwork:patch-promotion-outcome:v1\0" ||
            canonical_json(
              [attempt_id,
               terminal_journal_event_id,
               terminal_journal_event_sigil])))

recovery_record_id =
  "PRR-" + first_32_lower_hex(
    SHA-256("benchwork:patch-promotion-recovery-record:v1\0" ||
            canonical_json(
              [recovery_attempt_id,
               terminal_journal_event_id,
               terminal_journal_event_sigil])))
```

For an Outcome, resolve its exact terminal Event `E`, replay through `E`, and
resolve Promotion Attempt `A`, Authorization `U`, and the authorization
Receipt. Then `E` ID/Sigil and payload Attempt ID equal the Outcome;
`authorization_receipt` is the Receipt copied by
`promotion.attempt-created`; `operation_sigil == A.operation_sigil ==
U.operation_sigil`; and `adapter == A.adapter == U.adapter`, also equaling a
non-null Mutation Intent's Adapter. Checkpoint, Mutation Intent, and Guard are
null exactly when no corresponding commit/allocation Event exists in that
prefix; otherwise they are the exact immutable Refs established there.

Outcome time fields are also projected:

```text
timestamps.created_at =
  A.created_at =
  promotion.attempt-created.payload.created_at

timestamps.mutation_started_at =
  null, or promotion.mutation-intent-committed.payload.committed_at

timestamps.verification_started_at =
  null, or promotion.verification-started.payload.started_at

timestamps.terminal_at = E.payload.terminal_at = E.recorded_at
```

The two nullable timestamps are null exactly when their named Event is absent.
The remaining Outcome projection is exhaustive:

| Status / exact Event | Before and after identity/generation | Exact refs and evidence |
| --- | --- | --- |
| `APPLIED` / `promotion.applied` | Tree Sigils and generations equal the payload pairs; objects equal Base and Postimage | checkpoint, intent, and guard non-null with matching IDs; Adapter evidence non-null, its mode/generations match; verifier Sigils equal payload |
| `RECOVERED_POSTIMAGE_OBSERVED` / matching Event | payload pairs; objects equal Base and Postimage | all three Refs non-null; Adapter evidence null; verifier Sigils equal payload |
| `ALREADY_APPLIED` / matching Event | before == after == Postimage; both generations equal `target_content_generation` | intent null; checkpoint/guard follow replay; verifier Sigils are exactly the singleton `scan_evidence_sigil` |
| `STALE` / `promotion.stale` | before == after; both Tree Sigils equal `target_identity_sigil`; both generations equal `target_content_generation` | intent null; checkpoint/guard follow replay; verifier Sigils are exactly the singleton `evidence_sigil` |
| `CONFLICT` / `promotion.conflicted` | Sigils/generations equal payload pairs; after identity equals Base | checkpoint, intent, guard non-null and IDs match; Adapter evidence null; verifier Sigils singleton `evidence_sigil` |
| `FAILED` / `promotion.failed` | before == after == Base; hashes equal payload base/observed Sigils; after generation equals payload; before generation equals the intent target generation when present and otherwise payload | nullable Refs follow replay; a non-null intent supplies the guard; Adapter evidence null; verifier Sigils singleton `evidence_sigil` |
| `PARTIAL` / `promotion.partial` | before equals Base; after hash equals observed and after is neither Base nor Postimage; before generation equals the intent target generation and after equals payload | checkpoint, intent, and guard non-null with matching IDs; Adapter evidence null; verifier Sigils singleton `evidence_sigil` |
| `CANCELLED` / `promotion.cancelled` | before == after with both hashes equal observed and both generations equal payload | intent null; checkpoint/guard follow replay; Adapter evidence null; verifier Sigils singleton `no_intent_proof_sigil` |

For every row, the Event's `path_observations_sigil` and
`diagnostics_sigil` equal the formulas above. The sorted unique
`path_observations` set and diagnostic text are therefore fixed by the
terminal Event; another set or text cannot be paired with the same Event.

For a Recovery Record, resolve terminal Event `E`, Recovery Attempt `R`, its
canonical Authorization/Receipt, original parent Outcome/Receipt, checkpoint,
and replay prefix. Event ID/Sigil and payload Recovery Attempt ID equal the
Record. Authorization and parent Receipts equal
`recovery.attempt-created`; `parent_attempt_id`, action, checkpoint, and
lineage equal `R`, the Authorization selection, and any Recovery Intent
byte-for-byte. Guard is null exactly before allocation; Recovery Intent is
null exactly before `recovery.intent-committed`. Event type maps one-to-one to
status, and `resulting_logical_fence_generation` equals the terminal payload:

| Status / exact Event | Before and after identity/generation | Refs, verifier, and disposition |
| --- | --- | --- |
| `BASE_RESTORED` / `recovery.base-restored` | hashes/generations equal payload; after equals Base | guard and intent non-null; payload IDs match; verifier Sigils equal payload; disposition null |
| `POSTIMAGE_ACCEPTED` / matching Event | before == after == Postimage; hashes/generations equal payload and generations are equal | guard and intent non-null; IDs match; verifier Sigils equal payload; disposition null |
| `ABANDONED` / `recovery.abandoned` | before == after == `R.bound_before_identity` == disposition observed identity; generations all equal `R.bound_before_generation` and disposition observed generation | guard and intent non-null; IDs and verifier Sigils match; exact non-null disposition; logical-fence generation equals lineage, payload, Record, and disposition |
| `STALE` / `recovery.stale` | before equals `R` bound identity/generation; after hash/generation equal payload observed/value | intent and verification Event are both present exactly from `VERIFYING`; guard follows replay; verifier Sigils singleton `evidence_sigil`; disposition null |
| `FAILED` / `recovery.failed` | before equals `R` bound identity/generation; after hash/generation equal payload observed/value | same source-state null matrix; verifier Sigils singleton `evidence_sigil`; disposition null |
| `PARTIAL` / `recovery.partial` | before equals `R` bound identity/generation; after hash/generation equal payload and after is neither Base nor Postimage | guard and intent non-null, IDs match; verifier Sigils singleton `evidence_sigil`; disposition null |
| `CANCELLED` / `recovery.cancelled` | before == after == `R.bound_before_identity`; generations equal the bound value and payload | no Recovery Intent; guard follows replay; verifier Sigils singleton `no_intent_proof_sigil`; disposition null |

For `ABANDON`, one verifier Blob is exactly the closed canonical JSON object
`{schema_version: "patch-adapter-invocation-trace/1.0",
recovery_intent: Ref<PRI>, verification_event: PromotionEventRef,
reserved_terminal_event_id: ID<PJE>, before_identity_sigil: Sigil,
after_identity_sigil: Sigil, before_generation: Text<256>,
after_generation: Text<256>, target_content_write_calls:
Set<Text<128>,0..0,value>}`. It binds the exact Recovery Intent and
verification Event, reserves this terminal Event ID, repeats the equal
identity/generation pairs, and proves an empty target-content invocation set.
It cannot contain the future terminal Event Sigil. Later physical guard
terminalization is a guard-backend operation and does not weaken this
target-content no-write proof.

Events 27 through 34 and 41 through 47 are terminal evidence only. They bind
only already-existing Attempt, intent, guard, storage-root, observation, and
verifier identities. They never embed a future
`patch-promotion-outcome/1.0`,
`patch-promotion-recovery-record/1.0`, their IDs, or their Sigils. Those later
canonical records bind backward to the exact terminal Journal event ID and
Sigil as specified in contracts 16 and 19. Exact transport retry returns the
existing event or Receipt and never appends a duplicate terminal event.

Each event type has one exact payload definition in
`patch-promotion-journal-event/1.0`. Adding, renaming, or accepting another
event type requires a new contract version. `canonical.receipt-observed`
records a verified Receipt relationship but grants no canonical authority.
`preview.prepared` binds the complete validated Preview, Prepare request Sigil,
response-independent four-field Prepare binding Sigil, idempotency-key Sigil,
and authenticated ciphertext for the raw confirmation token under the named
local token-storage profile. The response is computed afterward and points
one-way to this event; no Preview, Prepare binding, or Journal event points to
the response. Plaintext is returned only by Prepare or its exact still-valid
retry and is never present in the Journal frame or replay projection.
`preview.expired` records the first trusted
observation that an unused Preview passed its bound expiry, after decision
recovery proved no canonical decision exists.

`preview.decision-submission-started` is the write-ahead bridge to Chronicle.
Its payload is closed and binds the decision, trusted decision time, redacted
request and idempotency Sigils, clock-policy and anchor-evidence Sigils, actor
and Host, expected Chronicle Head, and Preview revision.
`canonical.receipt-observed` for that exact submission binds
the canonical Event ID, Event Body Sigil, Receipt ID and Sigil, decision, and
resulting Chronicle Head. Neither event embeds its own Event Sigil or a
not-yet-created Receipt. Its deactivation set is also the only Receipt-driven
`ACTIVE -> INACTIVE` operational-root transition; it never releases a Storage
hold and is empty for proposal, validation, authorization, rejection,
`PARTIAL`, or unresolved recovery.

Guard, checkpoint, mutation-intent, and recovery-intent events embed and bind
documents validated respectively as
`patch-promotion-target-guard/1.0`,
`patch-promotion-checkpoint/1.0`,
`patch-promotion-mutation-intent/1.0`, and
`patch-promotion-recovery-intent/1.0`. Their Sigils are repeated by every later
event that depends on them; a journal payload is not a substitute for
validating the referenced exact contract.
Those protected control records or exact Evidence Manifests are finalized
first and contain no future Set, RootPlan, hold, or Event Sigil. Their Set is
registered next; the RootPlan then binds that Set and the future identities;
only afterward can the hold and later Journal payload bind the plan-bearing
`HoldBinding`. Reversing any edge would create a forbidden self-hash cycle.
Admission capacity includes one RootPlan control record for every protected
root and, for evidence/suffix roots, one Evidence Manifest in addition to all
Blob/control members and TailRecoveryIntent stage records.

The guard events have closed payload branches and the physical side-effect
ordering is normative. Acquire, renew, and release intent events are durable
before the corresponding physical operation. `target.guard-acquired`, `renewed`,
`validated`, and `released` bind an independent backend readback identity and
the exact target, owner Attempt, epoch, fencing generation, fence floor, and
expiry. `target.guard-failed` binds the failed phase and proves
whether the physical guard is absent; ambiguity enters integrity-failure mode
rather than pretending release. `target.guard-fenced` advances the target fence
floor before an older holder can authorize another entry write.

The append-only `journal.frames` file has one crash-detectable binary frame per
event. All integers in this layout are unsigned 64-bit big-endian:

```text
offset  size  value
0       8     N, the canonical event-byte length
8       N     canonical JSON bytes of patch-promotion-journal-event/1.0
8+N     32    raw SHA-256 of those N bytes
40+N    8     N repeated
48+N    8     ASCII "BWPEV1\r\n"
```

`N` is in `1..8388608`, so a frame is exactly `N + 56` bytes. The canonical
event bytes include the validated `event_sigil`; the independent 32-byte frame
hash covers the complete encoded event. A frame is valid only when both
lengths match, the marker is exact, the frame hash matches, the JSON and event
Schema validate, and sequence, previous-event Sigil, epoch, revisions,
relationships, and transition all continue the committed prefix.

`patch-promotion-journal-head/1.0` is the atomically replaceable commit record.
`committed_offset` is exactly the first byte after the last committed frame;
`frames_file_sigil_prefix` is the prefixed Sigil of SHA-256 over the raw bytes in
`journal.frames[0:committed_offset]`; `event_count`, `last_sequence`, and
`last_event_sigil` identify that same prefix; and `projected_state_sigil`
identifies its deterministic replay. The empty journal uses offset, count, and
sequence zero, null last-event Sigil, and the SHA-256 of the empty byte string.
Only a newly initialized, provably empty journal may create an initial Head.
A missing, malformed, or cryptographically invalid Head for a non-empty
frames file is ambiguous and fails closed.
`HeadRef` copies all Head fields and resolves by self-Sigil, Journal ID,
generation, offset, raw-prefix Sigil, and replayed-state Sigil. No lookup by a
nonexistent Head object ID is permitted.

Under the exclusive journal-writer lock, append performs exactly:

1. validate the current Head self-Sigil, committed offset, complete prefix
   digest, last frame, event chain, and replayed state;
2. stat and read the frames file and require its physical EOF to equal
   `Head.committed_offset`; a shorter file fails integrity and a longer file
   enters the staged suffix-recovery protocol before any ordinary append;
3. validate the next event and every referenced immutable payload, then append
   its complete frame exactly at `committed_offset`;
4. `fsync` the frames file and verify its resulting size and appended bytes;
5. write the next Head to a fresh same-directory file, `fsync` it, atomically
   replace the Head, and `fsync` the parent directory; and
6. only after the new Head verifies, acknowledge the operational mutation or
   begin the exactly bound backend or target side effect.

A frame not covered by the prior `HeadRef` is not acknowledged, even if its
bytes reached storage. Ordinary append never writes through, truncates, or
silently adopts a suffix. A backend or target side effect before the
corresponding intent frame and Head commit is forbidden.

Recovery requires one cryptographically valid prior `HeadRef` whose entire
committed prefix exists, ends exactly on a valid frame boundary, matches
`frames_file_sigil_prefix`, and replays to `projected_state_sigil`. If EOF
equals `committed_offset`, there is no tail intent. If EOF is greater, the
entire suffix has exactly one legal classification:

- `COMPLETE`: one or more complete, valid, chain-contiguous frames end exactly
  at EOF; `last_complete_offset` is EOF and `target_head` covers all of them.
- `TORN_EOF`: zero or more such complete frames are followed by exactly one
  incomplete frame ending at EOF; `last_complete_offset` ends the complete
  prefix and `target_head` covers that prefix. The available header declares
  an in-range `N`, and every available complete hash, repeated length, or
  marker subfield already matches. An out-of-range length, a wrong available
  subfield, an impossible layout, or bytes after the incomplete frame is
  corruption, not a torn write.

A COMPLETE suffix may itself end with a previously ordinary
`coordinator.replay-started` frame whose four tail fields are null. After
adopting it, the one recovery-owned replay event uses the narrowly permitted
`REPLAYING -> REPLAYING` row to bind the new suffix evidence. A COMPLETE
suffix ending in `coordinator.integrity-failed` instead adopts the
`READ_ONLY_FAILED` State and uses the no-append terminal branch below. A
suffix replay event with non-null tail fields must have its matching durable
`REPLAY_EVENT_STAGED` intent chain already present and is resumed through that
chain; an absent or mismatched chain is corruption, not permission to create
another replay event.

Both classifications use the same exact `TailRecoveryIntent` `$def` and this
durable staged FSM:

1. While holding the shared outer gate, preserve
   `journal.frames[old_head.committed_offset:observed_eof]` as one immutable
   evidence Blob; under only the Promotion Journal lock durably reserve the
   exact replay Event slot with type `coordinator.replay-started` and field
   `SUFFIX_EVIDENCE_PROTECTION`, then release that lock; finalize the exact
   `JOURNAL_SUFFIX` Evidence Manifest with that reserved Event ID; register and
   read back its derived operational Reference Set; preallocate the hold and
   hold-set Event identities; finalize and read back its RootPlan; append and
   read back `retention.hold_set`; and freeze the resulting `HoldBinding`.
   Reverify the Blob, reserved Event tuple, manifest, set, plan, hold, frozen
   Storage prefix, prior Head, original suffix bytes, classification, and
   target Head. Atomically create the intent in `PROTECTED` with that exact
   protection before changing `journal.frames` or Head.
2. For `COMPLETE`, verify that the frames file still equals the original bytes
   and already ends at `last_complete_offset`. For `TORN_EOF`, require either
   the exact original bytes or the exact target prefix; in the former case
   truncate only to `last_complete_offset`, `fsync` the file, and verify the
   target prefix. Atomically advance the intent to `FRAMES_STABILIZED`.
3. Require the installed Head to be either `old_head` or exact `target_head`.
   In the former case install `target_head` by the normal fresh-file,
   file-sync, atomic-replace, and directory-sync protocol. Verify it and
   atomically advance the intent to `HEAD_INSTALLED`.
4. Revalidate the evidence protection under the still-held outer gate and
   retain the immutable `HEAD_INSTALLED` stage record and Sigil. If replay of
   `target_head` ends in `READ_ONLY_FAILED` because the adopted final frame is
   `coordinator.integrity-failed`, append no event to that failed state:
   advance directly to an immutable `COMPLETED` record with
   `completion_mode: READ_ONLY_PREFIX`, null replay fields, and
   `previous_record_sigil` equal to the `HEAD_INSTALLED` record. Preserve the
   suffix evidence hold permanently and release the locks in read-only mode.
   Otherwise construct the one exact `coordinator.replay-started` event and
   its covering Head. Its payload binds the recovery ID and the stable
   `HEAD_INSTALLED.record_sigil`, plus `target_head`, the Evidence Manifest
   Sigil as `suffix_evidence_sigil`, and the same `HoldBinding`; it never binds a record containing its own Event
   or Head. Then create the immutable `REPLAY_EVENT_STAGED` record with that
   Event ID, Event Sigil, and complete HeadRef, chained to the retained
   `HEAD_INSTALLED` record. Only after the staged record verifies may the
   Coordinator append the precomputed frame. The initial attempt uses the
   normal EOF-equal append and Head replacement. After the new Head and event
   verify, create the immutable `REPLAY_EVENT_COMMITTED` record.
5. For the normal branch, reverify the exact replay event, its covering Head,
   and its backward binding to the retained `HEAD_INSTALLED` record, then
   create `COMPLETED` with `completion_mode: NORMAL_REPLAY`. The later
   `coordinator.epoch-started` event names the completed recovery and
   transitions its operational root to `INACTIVE`; replay retains the outer
   gate until that event and Head verify. The forensic hold remains active
   until its independent release condition; completion never deletes suffix
   evidence. The read-only branch has no epoch event or Promotion-Journal
   operational root; its independently durable Storage hold is never
   released.

`TailRecoveryIntent` is implementation-owned repair metadata, not a Chronicle
event or a 35th public contract. Its exact local `$def`, stage, revision, and
Sigil are nevertheless normative. At most one non-`COMPLETED` tail intent may
exist per Journal. After any process crash, recovery reacquires the shared
outer gate before the Journal writer lock and resumes the durable stage; it
never assumes the crashed process still owns either lock.

Every second crash has one closed continuation:

| Durable intent stage and observed local state | Required continuation |
| --- | --- |
| `PROTECTED`; original suffix still present | repeat only the exact stabilize step; never recapture or reclassify evidence |
| `PROTECTED`; torn suffix already equals target prefix | verify it against the protected original evidence and advance to `FRAMES_STABILIZED`; do not truncate again |
| `FRAMES_STABILIZED`; prior Head installed | install only the precomputed target Head, then advance |
| `FRAMES_STABILIZED`; target Head already installed | verify it and advance to `HEAD_INSTALLED`; do not derive another Head |
| `HEAD_INSTALLED`; target State is not `READ_ONLY_FAILED` | construct the replay event once with the retained `HEAD_INSTALLED` record Sigil, persist its exact ID, Sigil, frame, and covering Head in a chained `REPLAY_EVENT_STAGED` record, then perform no write until that stage verifies |
| `HEAD_INSTALLED`; target State is `READ_ONLY_FAILED` from an adopted `coordinator.integrity-failed` frame | create only the chained `COMPLETED/READ_ONLY_PREFIX` record, retain the Storage hold forever, and perform no Promotion-Journal append |
| `REPLAY_EVENT_STAGED`; EOF equals target Head offset | append the exact precomputed frame, fsync, and install only its precomputed covering Head |
| `REPLAY_EVENT_STAGED`; EOF is a proper byte prefix of the precomputed frame after the target prefix | verify every available byte, append only the missing bytes, fsync, and install only the precomputed covering Head; a differing byte fails read-only |
| `REPLAY_EVENT_STAGED`; complete exact frame exists but target Head is still installed | verify the frame and install only the precomputed covering Head; do not invoke a second suffix classification |
| `REPLAY_EVENT_STAGED`; exact replay-event Head is installed | verify event, Head, its `HEAD_INSTALLED` backward binding, and the immutable stage chain, then create `REPLAY_EVENT_COMMITTED`; do not append a duplicate |
| `REPLAY_EVENT_COMMITTED`; exact event and Head verify | create `COMPLETED/NORMAL_REPLAY`; retain the hold |
| either `COMPLETED` mode | verify its complete immutable predecessor chain and perform no recovery write |
| any stage with a different suffix, Head, event, hold, Reference Set, frozen prefix, recovery ID, predecessor, or record Sigil | enter `READ_ONLY_FAILED`; do not overwrite either version |

A frames file shorter than `committed_offset`, a committed-prefix digest
mismatch, an offset in the middle of a frame, an invalid complete suffix frame,
a wrong event chain or revision, bytes after an incomplete frame, non-tail
corruption, two plausible cut points, a conflicting recovery intent, or the
absence of a valid prior `HeadRef` enters `READ_ONLY_FAILED`. Recovery never
skips a frame, repairs JSON, invents an event, treats a checksum mismatch as a
torn write, or truncates middle or ambiguous evidence.

`patch-promotion-state/1.0` is the byte-deterministic replay projection. It
contains every durable Preview and prepare-idempotency binding, Promotion and
Recovery Attempt, unresolved authorization, guard and fence floor, checkpoint
and mutation-intent identity, terminal outcome, exact canonical link when later
available, active or preserved target-level partial lineage, and every
operational root. Inspect redacts confirmation tokens from this projection.
It also contains the coordinator clock gate, last trusted UTC value and
evidence Sigil, every unresolved decision submission, every durable deadline,
and the exact guard lifecycle state. `canonical_links` is authoritative for
the projected Receipt set; no duplicate receipt-only cache is a contract
field. The checked aggregate count across every entity-bearing top-level set
is at most `MAX_STATE_ENTITIES`, not that limit independently multiplied by
the number of fields.

Replay validates every exact event Schema and binary frame, contiguous
sequence, Sigil, revision, relationship, idempotency binding, and state
transition, then recomputes `patch-promotion-state/1.0` and its state Sigil.
`coordinator.integrity-failed` may record a verified external or backend
integrity incident only while the journal prefix and next append remain
verifiable. A corrupt journal cannot truthfully append its own failure and is
diagnosed outside the chain.

### Clock and deadline authority

Every Preview expiry and target-guard expiry is one normalized durable UTC
`due_at`; neither a process-local timer nor an untrusted request timestamp is
authority. `patch-promotion-adapter/1.0` contains one closed deadline policy
with exact non-negative integer members `preview_lifetime_seconds`,
`guard_lifetime_seconds`, `guard_renewal_interval_seconds`, and
`clock_uncertainty_tolerance_seconds`, plus the trusted UTC source-profile
Sigil and closed suspend policy. The Preview and every guard bind that policy
Sigil. All deadline derivations use checked UTC arithmetic and reject overflow
instead of saturating.

For each new deadline the Coordinator samples the trusted UTC source and
monotonic clock in one bounded operation and establishes:

```text
trusted_utc_anchor
monotonic_anchor
due_at
original_remaining = max(0, due_at - trusted_utc_anchor)
```

The anchor evidence durably binds `due_at`, `trusted_utc_anchor`,
`original_remaining`, both clock-source profiles, sample uncertainty, and its
Sigil; only the process-local monotonic reading itself is omitted from durable
state. At every authority boundary a deadline is due if either predicate is
true:

```text
trusted_utc_now >= due_at
OR
monotonic_now - monotonic_anchor >= original_remaining
```

Both differences use checked non-negative integer nanoseconds. The UTC
predicate makes a trusted forward jump expire authority immediately. The
monotonic predicate makes a UTC rollback unable to extend authority. During a
UTC slew both clocks are sampled and either predicate wins; the implementation
may never select the more permissive clock.

Reanchoring the same `due_at` after trusted-clock restoration or restart may
only shorten the prior ceiling:

```text
wall_remaining = max(0, due_at - new_trusted_utc)
mono_remaining = max(0, old_original_remaining - proven_monotonic_elapsed)
new_original_remaining = min(wall_remaining, mono_remaining)
```

The new durable anchor evidence binds the prior anchor Sigil and both computed
remainders. When monotonic continuity across a restart is unavailable,
`proven_monotonic_elapsed` may be zero only as a conservative ceiling; the
trusted UTC predicate still applies, and any unprovable suspend duration or
rollback enters `UNCERTAIN` before authority resumes. No reanchor, tolerance,
restart, or clock restoration can increase the previous remaining ceiling.

A guard renewal is not a reanchor of the old deadline: while neither old due
predicate holds, its separately authorized renew intent creates one new
policy-bounded `due_at` and fresh original remaining duration. Replaying or
reanchoring that new deadline may only shorten it. Preview deadlines are never
renewed.

Before any decision, guard acquisition or renewal, entry mutation, or recovery
mutation, the Coordinator evaluates both predicates and processes already-due
work in this exact order:

```text
(due_at, fixed_priority, entity_id)
10 PREVIEW_EXPIRY
20 GUARD_EXPIRY
```

UTC values compare as normalized instants and `entity_id` by unsigned ASCII
bytes; timer callback, thread, request arrival, and directory order never break
a tie.

Before expiring a `PREPARED` Preview, the Coordinator proves that no decision
submission was durably started. Every `DECIDING` Preview is instead resolved
by the linearizable Chronicle lookup described above. An accepted
authorization or rejection Receipt always wins; definitive pre-commit absence
produces the durable `DECISION_FAILED` transition and stable error, while
ambiguity remains fail-closed in `DECIDING`.

On restart, replay compares current UTC with the last trusted Journal UTC and
applies the non-lengthening reanchor formula before authority resumes. UTC
rollback beyond the configured bounded tolerance, excessive UTC/monotonic
divergence or slew, monotonic reset during a live anchor, unprovable suspend
duration, arithmetic failure, or inability to establish UTC trust appends
`coordinator.clock-uncertain` with a non-decreasing time derived from the last
trusted anchor and moves the exact clock gate `TRUSTED -> UNCERTAIN`. A trusted
forward jump first expires every deadline made due by the UTC predicate; if
the jump also exceeds divergence policy, the remaining authority then enters
`UNCERTAIN`. The Coordinator:

1. forbids Prepare, authorization, guard acquisition or renewal, and every
   target or recovery mutation;
2. after the clock-uncertain frame and Head are durable, processes every held
   or indeterminate guard in sorted guard-ID order through
   `target.guard-fence-intent-committed`, the exact backend CAS and readback,
   then `target.guard-fenced`;
3. treats a deadline as due whenever it cannot prove that deadline remains in
   the future, subject to the canonical-decision lookup rule; and
4. retains unresolved state and evidence without inventing a timestamp.

The closed `coordinator.clock-uncertain` payload binds the last trusted UTC,
untrusted observed UTC through an explicit nullable branch, monotonic status,
checked divergence, cause enum, prior anchor-evidence Sigil, and sorted guard
IDs to fence. Intended generations and floors belong to each later durable
fence-intent event rather than being predicted by the clock event.
`coordinator.clock-restored` may move `UNCERTAIN -> TRUSTED` only after a named
trusted UTC source, fresh monotonic anchor evidence, all required decision
lookups, and fencing of every old guard verify. It never revives an expired
Preview, consumed token, old guard, epoch, or fencing generation. New guard
authority requires a new greater generation. Unlisted clock-gate transitions
fail closed. Its closed payload binds the trusted source and policy Sigils,
restored UTC, new anchor-evidence Sigil, resolved decision IDs, and sorted
fenced guard IDs.

The Preview projection follows
`none -> PREPARED -> DECIDING -> AUTHORIZED | REJECTED | DECISION_FAILED`,
with the additional direct `PREPARED -> EXPIRED` deadline transition.
`preview.prepared` creates it, a verified
`canonical.receipt-observed` for `patch.promotion.authorized` or
`patch.promotion.rejected` consumes it, `preview.decision-failed` preserves a
definitive pre-commit abort and stable retry result, and `preview.expired`
records expiry only before submission.
The trusted clock may make a still-recorded `PREPARED` Preview immediately
ineligible before the expiry event is appended; no mutation or authorization
may exploit that bookkeeping delay. All four terminal Preview states have no
outbound transition, and a new decision attempt requires a new Preview.

The target guard state machine is exhaustive:

```text
NONE       -> ACQUIRING
ACQUIRING  -> HELD | FENCING | RECOVERING | FAILED
HELD       -> HELD | RENEWING | RELEASING | FENCING | RECOVERING
RENEWING   -> HELD | FENCING | RECOVERING | FAILED
RELEASING  -> RELEASED | FENCING | RECOVERING | FAILED
RECOVERING -> FENCING | RELEASED | FAILED
FENCING    -> FENCED
```

`target.guard-acquire-intent-committed`,
`target.guard-renew-intent-committed`, and
`target.guard-release-intent-committed` respectively enter `ACQUIRING`,
`RENEWING`, and `RELEASING` before the external lock operation.
`target.guard-acquired`, `target.guard-renewed`, and
`target.guard-released` require exact physical readback and enter the
corresponding destination. `target.guard-validated` is a `HELD -> HELD`
self-loop that changes only its observation revision and never extends expiry.
Renewal is legal only before the current expiry, uses a strictly later bounded
expiry, retains the same owner, and durably records its intent before the
backend compare-and-swap.

The backend guard value is one closed tuple containing target ID, guard ID,
owner Attempt, coordinator epoch, backend generation, fencing generation,
fence floor, expiry, and target-wide content generation. Its CAS and
linearizable readback are durable. A backend that can delete that tuple must
retain a durable absence/tombstone generation and target fence floor; bare
absence that loses the last floor is not verifiable and is ineligible.
Backend-generation strings use the adapter's verified non-repeating successor
relation; fencing generation and fence floor are numeric and never decrease.

Every fence follows one write-ahead sequence:

1. derive the exact prior backend generation, prior fencing generation, and
   prior floor plus strictly greater intended values and a stable backend
   request Sigil;
2. append and Head-commit `target.guard-fence-intent-committed`, entering
   `FENCING`, before issuing a new backend operation;
3. execute one idempotent backend CAS for that request, conditional on the exact
   prior tuple or its exact durable absence generation, and write the intended
   generation and floor as a fenced tombstone;
4. obtain the durable backend receipt and linearizable readback; and
5. append and Head-commit `target.guard-fenced` only when readback equals every
   intended value.

Clock uncertainty, expiry, epoch change, crash recovery, partial mutation, and
integrity containment all use that same sequence. For clock uncertainty, the
clock event commits first and then each sorted guard receives its own fence
intent, CAS/readback, and fenced event. `coordinator.clock-restored` is illegal
until all named guards are terminal.

An ambiguous backend result in `FENCING` is resolved only by this exhaustive
observation table:

| Fresh backend observation for the durable fence intent | Required action |
| --- | --- |
| exact prior tuple or exact prior durable absence generation | retry the same idempotent CAS with the same request Sigil within the bounded backend policy, obtain its durable receipt, read back, and apply this table again; a definitive rejection while the exact precondition remains enters integrity failure |
| exact intended fenced tuple or tombstone | issue no second logical CAS; recover or verify the original receipt, bind the readback, and append `target.guard-fenced` |
| logical guard absent but a durable tombstone proves the exact intended backend generation, fencing generation, and floor | treat it as the preceding intended-tombstone row and append `target.guard-fenced` |
| any intermediate, higher, lower, foreign-owner, unknown, unavailable, or otherwise unverifiable value | enter coordinator integrity failure; do not append a terminal guard event and do not mutate the target |

`coordinator.replay-started` moves listed `ACQUIRING`, `HELD`, `RENEWING`,
`RELEASING`, and already `RECOVERING` old-epoch guards to `RECOVERING` while
preserving their origin state, last physical-intent event and Sigil, backend
request Sigil, prior/intended generations and floor, and last readback. A guard
with a durable fence intent remains `FENCING` and uses the FENCING table
directly. Recovery performs fresh observations before choosing exactly one row:

| Preserved origin and fresh observation in `RECOVERING` | Required action |
| --- | --- |
| `RELEASING`; exact prior held tuple | retry the same idempotent release CAS, which must preserve the durable target floor, then verify the exact intended released tombstone and append `target.guard-released` |
| `RELEASING`; exact intended released tombstone or exact absence carrying that tombstone generation and floor | issue no second release; bind the readback and append `target.guard-released` |
| `ACQUIRING`, `HELD`, `RENEWING`, or `RECOVERING`; exact prior tuple, exact intended tuple, or exact durable absence generation | append a crash-recovery fence-intent using a strictly greater floor/generation and then apply the `FENCING` table |
| any origin with no matching durable physical intent, or any different, intermediate, foreign, unknown, or unverifiable value | enter coordinator integrity failure; no release, fence, replacement guard, or target mutation is inferred |

A crash during recovery uses the same table again:

| Last durable recovery boundary | Next restart |
| --- | --- |
| replay-started committed, no recovery action event | repeat the fresh `RECOVERING` observation table |
| recovery fence-intent committed, CAS not known | keep the guard `FENCING`, perform fresh readback, and apply the same `FENCING` observation table |
| backend CAS or release may have committed, terminal guard event absent | perform readback first; never blindly repeat a non-idempotent operation |
| `target.guard-fenced`, `target.guard-released`, or `target.guard-failed` committed | preserve that terminal state and perform no physical guard operation |

`RELEASED`, `FENCED`, and `FAILED` are terminal for that guard identity.
Physical release always follows a durable release intent; a terminal Promotion
or Recovery Attempt must release or fence its physical guard, and a crash
cannot infer release from process death, wall time, or lock age. A still
unresolved Attempt may resume only after the old identity is terminal and a
new linked guard identity is acquired under a strictly greater coordinator
epoch, backend generation, fencing generation, and floor. The old guard is
never resurrected.

The Promotion Attempt state machine is exhaustive:

```text
CREATED -> PREFLIGHTING -> READY -> MUTATING -> VERIFYING -> APPLIED
   |          |            |          |            |
   |          |            |          |            +-> RECOVERED_POSTIMAGE_OBSERVED
   |          |            |          |            +-> FAILED | PARTIAL
   |          |            |          +-> CONFLICT | FAILED | PARTIAL
   |          |            +-> ALREADY_APPLIED | STALE | FAILED | CANCELLED
   |          +-> ALREADY_APPLIED | STALE | FAILED | CANCELLED
   +-> CANCELLED
```

`READY` requires a current `HELD` guard, exact Base, and a committed verified
checkpoint. `READY -> MUTATING` is legal only when the complete mutation intent
event and updated Head are durable before the first target side effect.
`MUTATING -> VERIFYING` requires all declared operations to have returned and
retains every bounded observation. `VERIFYING -> APPLIED` requires exact
Postimage evidence plus eligible adapter-write evidence bound to the exact
intent, guard, and per-entry or atomic transaction commits.
`VERIFYING -> RECOVERED_POSTIMAGE_OBSERVED` requires exact Postimage evidence
and explicit absence of such causal evidence. A target equal to neither Base
nor Postimage is always `PARTIAL`. All named outcome states are terminal and
have no outbound edge.

A `PARTIAL` Promotion Attempt is never changed to a recovery-derived or
successful status. Recovery allocates a new
`patch-promotion-recovery-attempt/1.0`, binds the original terminal Attempt,
checkpoint, and current canonical logical-fence head, and requires a new
`RECOVER_PARTIAL` Preview and human authorization. The target fence's
unresolved slot admits only one such Attempt until its exact Recovery Record
Receipt is observed. Its exhaustive state machine is:

```text
CREATED -> PREFLIGHTING -> READY -> RECOVERING -> VERIFYING
   |          |            |                         +-> BASE_RESTORED
   |          |            |                         +-> POSTIMAGE_ACCEPTED
   |          |            |                         +-> ABANDONED
   |          |            |                         +-> STALE | FAILED | PARTIAL
   |          |            +-> STALE | FAILED | CANCELLED
   |          +-> STALE | FAILED | CANCELLED
   +-> CANCELLED
```

The recovery action is fixed as `RESTORE_BASE`, `ACCEPT_POSTIMAGE`, or
`ABANDON` before authorization. A
`patch-promotion-recovery-record/1.0` binds its own Recovery Attempt,
authorization Receipt, parent `PARTIAL` Attempt and outcome Receipt, action,
guard and fence when allocated, checkpoint, recovery intent when present,
current lineage, before and after identities, resulting logical-fence
generation, verifier evidence, terminal journal-event Sigil, and terminal
status. The legal pre-allocation or pre-intent terminal branch
uses the exact null fields rather than inventing either identity.
`BASE_RESTORED`, `POSTIMAGE_ACCEPTED`, and `ABANDONED` describe only the
Recovery Attempt. The parent Promotion Attempt remains `PARTIAL` forever, and
inspection shows the append-only recovery edge rather than rewriting history.

Recovery `READY` always requires a current `HELD` guard, the authorized fresh
target identity, and a verified parent checkpoint binding. For
`RESTORE_BASE`, that fresh identity is the exact partial state from which the
restore is authorized. For `ACCEPT_POSTIMAGE`, it must already equal the exact
expected Postimage. For `ABANDON`, it may be any exact verifiable identity bound
by the Preview, but the Preview must state that no Base or Postimage claim is
being accepted.

`READY -> RECOVERING` is legal only after the Recovery Intent is finalized
without future protection fields, its derived operational Reference Set and
`retention.hold_set` Event verify, and `recovery.intent-committed` binds the
external `HoldBinding` in the updated Head. The Coordinator revalidates the
guard, fence, deadline, stable root, ancestors, and target before every
`RESTORE_BASE` entry write using the same descriptor-relative no-follow and
compare-and-swap rules as promotion. Once a recovery intent exists, every fresh post-intent
observation first appends and Head-commits
`recovery.verification-started`, moving `RECOVERING -> VERIFYING`, before any
terminal recovery event. This applies to success, stale, no-change failure,
partial result, and an unverifiable scan; the last remains `VERIFYING` under
the coordinator integrity gate rather than inventing a terminal identity.
`ACCEPT_POSTIMAGE` and `ABANDON` perform no content mutation. `ABANDONED`
preserves the exact observed partial state and logical partial fence. After
the `recovery.abandoned` Event is durable, the Coordinator terminalizes the
same physical guard before constructing the Recovery Record, using the exact
closed sequence and equality rules in `AbandonmentDispositionAuthority`.
This guard-only operation neither releases an operational Storage hold nor
changes target content. The canonical Receipt remains mandatory before root
inactivation or any Storage-hold release. Later Benchwork mutation requires a
new Proposal, fresh target-state evidence, and new Preview that explicitly
cites the abandoned lineage.

Only the canonical Recovery Record Receipt changes the logical-fence endpoint.
It clears the fence for verified `BASE_RESTORED` or
`POSTIMAGE_ACCEPTED`, preserves it as `ABANDONED` for the exact abandonment
authority, and otherwise returns it to `ACTIVE` after filling the latest head
and clearing the unresolved slot. Neither successful branch reuses the parent
Promotion authorization. Any later promotion requires a newly prepared
`PROMOTE` Preview and explicit human decision.

## Staleness and conflict

Staleness is an identity mismatch discovered before a target mutation.
Benchwork distinguishes:

- **control staleness**: the Task, Capability, Snapshot, Execution
  Specification, approval, assurance evidence, or accepted Proposal no longer
  passes its bound policy;
- **validation staleness**: the selected evidence does not bind the exact
  Proposal and current Validation Policy, or a policy-defined environmental
  constraint is no longer satisfied; and
- **target staleness**: the recomputed target identity does not equal the
  authorized Base, expected Postimage, or exact current Recovery/abandoned
  lineage identity and generation selected by the branch.

All three fail closed. A newer branch tip, a clean `git status`, a patch that
appears to apply, or changes outside displayed diff context do not waive an
identity mismatch. The identity profile may deliberately exclude unrelated
runtime paths, but it cannot be narrowed after authorization.

A conflict is discovered while attempting an exact, already authorized
transition from the Base to the Postimage. Examples include an affected path
changing after preflight, an add destination becoming occupied, a
file/directory or case collision, an unsupported mode at the target, a failed
compare-and-swap, or a target that becomes a mixed preimage/postimage.

Benchwork does not silently rebase, merge, fuzz, create reject files, choose a
side, or edit the change manifest. To continue on a different base, a Host must
materialize the old Proposal in a new Crucible, resolve the conflict as a new
change, export a new Base and Patch Proposal, repeat validation, and obtain a
new human authorization. The stale or conflicting Proposal and every failed
Promotion Attempt remain preserved.

## Idempotency and concurrency

Every prepare, authorize, and outcome request carries a caller-supplied
idempotency key within a defined project and operation scope. Repeating an
identical request returns the original Preview or authorization, rejection, or
outcome Receipt. Reusing the key with different canonical request content,
including changing `AUTHORIZE` to `REJECT`, fails with
`PATCH_IDEMPOTENCY_CONFLICT`. Transport
retry never creates a second human decision or silently starts another
Promotion Attempt.

Prepare bindings replay from `preview.prepared` in the Promotion Journal.
The event yields the response-independent binding and protected token; the
response is reconstructed afterward and points backward to that event. Replay
never expects a response Sigil inside the Preview or event.
Authorization, rejection, and accepted-outcome bindings replay from their
Chronicle events and Receipts, with `preview.decision-submission-started` as
write-ahead intent and `canonical.receipt-observed` as an operational cache and
cross-journal link rather than a second authority. A crash between either
authority append and response delivery therefore resolves the exact request
and returns the original object instead of expiring or repeating the
transition.
Each applicable Chronicle payload binds the operation-scoped idempotency-key
Sigil and complete canonical request Sigil; a lookup never relies only on the
operational observation event.

A definitive pre-commit decision abort replays from
`preview.decision-failed`, not from a transient transport error. The exact
request and key always return its stable `PATCH_DECISION_FAILED` details; a
different request or decision under the key is
`PATCH_IDEMPOTENCY_CONFLICT`. Only an unresolved Chronicle result remains
`DECIDING` and retryable.

A Promotion Attempt ID is unique and never reused. A retry after a proven
no-change failure creates a new Attempt ID but retains the same logical
operation identity and authorization. It may proceed only while the
authorization remains eligible and the target still equals the Base. A
`PARTIAL` outcome creates the target-level `ACTIVE` fence and blocks ordinary
promotion. Only the current canonical head with a null unresolved slot can
authorize one Recovery Attempt. A canonical Base/Postimage recovery clears
the fence; canonical abandonment changes it to `ABANDONED`, which admits only
a new Proposal, fresh target evidence, and a Preview/Authorization carrying
the exact abandoned-lineage binding. That re-entry clears the fence only when
its successful terminal Outcome Receipt is observed.

The Postimage Identity is the side-effect idempotency fence:

- target equals Base: an authorized apply may begin;
- target equals expected Postimage before any mutation intent: do not apply;
  record `ALREADY_APPLIED`;
- target equals expected Postimage while replaying an unresolved mutation
  intent: do not apply; record `APPLIED` only with eligible causal
  adapter-write evidence, otherwise record
  `RECOVERED_POSTIMAGE_OBSERVED`; and
- target equals neither: do not guess; record `STALE`, `CONFLICT`, or
  `PARTIAL` according to when the mismatch occurred.

Concurrent promotions to one target require serialization plus identity
comparison. Two authorizations against the same Base do not both remain
applicable after the first changes the target. The second becomes stale unless
its expected Postimage is byte-for-byte and semantics-for-semantics identical,
in which case it may only record an idempotent no-op under its own
authorization.

## Crash recovery

Crash recovery uses the Promotion Journal, accepted identities, and retained
checkpoints, never conversation history, process names, modification times,
`git status`, or a patch command's remembered exit code.

On coordinator restart, replay:

1. acquires the shared outer gate and exclusive recovery ownership, then the
   Promotion Journal writer lock; when Storage replay, Storage readback, or a
   Chronicle lookup is needed it releases the Promotion lock while retaining
   the gate and recovery ownership, takes only the Storage lock for Storage
   work or no local journal lock for Chronicle, and reacquires the Promotion
   lock only after that operation completes;
2. validates every event Schema, Sigil, previous-event link, sequence,
   revision, identity relationship, and legal state transition;
3. validates the prior `HeadRef` and either replays its exact committed prefix
   or performs only the permitted evidenced tail-suffix recovery, then
   validates `patch-promotion-state/1.0`;
4. establishes trusted UTC and fresh monotonic anchors or enters
   `coordinator.clock-uncertain`;
5. resolves every `DECIDING` Preview against Chronicle before processing
   expiry;
6. requires the active-guard projection at or below
   `MAX_ACTIVE_GUARDS`, appends a strictly greater coordinator epoch, and
   fences every guard from an older epoch before scheduling or mutation
   resumes;
7. reconciles each unresolved physical guard through the closed guard recovery
   table and reacquires authority only under a greater fencing generation; and
8. classifies the target only from the durable checkpoint, mutation or recovery
   intent, bound before-identity, Base, Postimage, exact action, and a fresh
   complete target identity.

Only after `coordinator.epoch-started`, all staged repairs, root readbacks, and
guard dispositions verify may replay release the Promotion lock, recovery
ownership, and outer gate in that order.

An interrupted Promotion Attempt without a durable mutation intent cannot have
an authorized target side effect. Replay appends `promotion.cancelled` with
the journal proof of no intent and fresh target observation; it does not mutate
the target. For an Attempt with a durable mutation intent:

- **Base found:** no mutation survived; replay appends `promotion.failed` with
  terminal status `FAILED` and verified no-change evidence, after which a new
  Promotion Attempt may retry while its authorization remains eligible.
- **Expected Postimage found:** replay performs no second write and appends
  `promotion.verification-started`. It may append `promotion.applied` with
  terminal status `APPLIED` only when eligible adapter-write evidence proves
  the exact causal write under this intent and guard; otherwise it appends
  `promotion.recovered-postimage-observed` with terminal status
  `RECOVERED_POSTIMAGE_OBSERVED` and explicitly disclaims causal attribution.
- **Neither found:** replay appends `promotion.partial` with terminal status
  `PARTIAL`, retains the checkpoint, intent, guard record, and diagnostics,
  advances the logical partial fence, and conditionally releases or fences the
  physical guard so ordinary retry cannot reuse it.
- **Identity or evidence cannot be verified:** the coordinator enters
  integrity-failure mode, preserves all material, and permits inspection but
  no mutation.

This deterministic replay terminalizes an interrupted original Attempt; it is
not the later human-selected recovery of an already terminal `PARTIAL`.

After `PARTIAL`, `benchwork_prepare_patch_promotion` must prepare a new
`RECOVER_PARTIAL` Preview. Explicit human authorization allocates a distinct
Recovery Attempt and commits a write-ahead recovery intent before any content
mutation or terminal recovery observation. Replay never resumes or repeats a
partially completed restore automatically. After guard recovery and a fresh
complete scan, it applies this exhaustive table:

| Authorized action | Durable recovery intent | Fresh observation | Required replay result |
| --- | --- | --- | --- |
| any | absent | target verifies equal to the bound pre-recovery identity | append `recovery.cancelled`; prove no Coordinator recovery write and perform none |
| any | absent | target has a different verified identity | append `recovery.stale`; prove no Coordinator recovery write and perform none |
| any | absent | target identity cannot be verified | integrity failure; do not infer an external change or mutate |
| `RESTORE_BASE` | present | exact Base | append `recovery.verification-started`, enter `VERIFYING`, then append `recovery.base-restored`; this is a recovered endpoint observation and claims adapter causality only when separately proven |
| `RESTORE_BASE` | present | exact bound pre-recovery partial identity | append `recovery.verification-started`, enter `VERIFYING`, then append `recovery.failed` with verified no-change evidence; a retry requires a new Recovery Preview |
| `RESTORE_BASE` | present | exact Postimage or any other verified identity | append `recovery.verification-started`, enter `VERIFYING`, then append `recovery.partial`, retain the parent checkpoint and both intents, and keep the logical partial fence |
| `ACCEPT_POSTIMAGE` | present | exact Postimage | append `recovery.verification-started`, enter `VERIFYING`, then append `recovery.postimage-accepted`; perform no content write |
| `ACCEPT_POSTIMAGE` | present | any other verified identity | append `recovery.verification-started`, enter `VERIFYING`, then append `recovery.stale`; perform no content write and keep the logical partial fence |
| `ABANDON` | present | exact Preview-bound target identity | append `recovery.verification-started`, enter `VERIFYING`, then append `recovery.abandoned`; perform no content write, preserve that identity, and keep the logical partial fence |
| `ABANDON` | present | any other verified identity | append `recovery.verification-started`, enter `VERIFYING`, then append `recovery.stale`; perform no content write and keep the logical partial fence |
| any | present | identity, checkpoint, intent, action, or evidence unverifiable | append `recovery.verification-started` with `scan_status: UNVERIFIABLE` and null observed identity/generation, enter `VERIFYING`, then enter coordinator integrity failure; retain everything and permit no mutation |

Every terminal table result first durably terminalizes the Recovery Attempt in
the Promotion Journal. For `ABANDONED`, it then terminalizes the exact guard
and embeds that already-durable completion as specified above; an unresolved
guard blocks Record construction. The complete
`patch-promotion-recovery-record/1.0` is only then constructed and submitted
idempotently through the outer-gate, Recovery Reference Set,
reference-intent, and committed-pin sequence. A crash after Chronicle append
returns the original Receipt and completes any missing pin.
Before releasing the gate, the Coordinator appends
`canonical.receipt-observed` under only the Promotion Journal lock. It
deactivates roots only for verified `BASE_RESTORED`,
`POSTIMAGE_ACCEPTED`, or `ABANDONED` with its exact embedded patch-specific
disposition. All three require the exact terminal-guard and intent-absence
branches; the abandonment branch additionally preserves the logical fence and
deactivates exactly its tabled roots. Every other Recovery status retains
them. For every status, that exact Receipt observation fills the latest fence
head's canonical record and clears the unresolved-Recovery slot; only then may
another Recovery Preview bind that head.
`BASE_RESTORED`, `POSTIMAGE_ACCEPTED`, and `ABANDONED`
belong only to the Recovery Attempt; the original Promotion Attempt and its
`PARTIAL` outcome are never relabeled. A `FAILED`, `STALE`, `PARTIAL`, or
`CANCELLED` Recovery requires its canonical Record Receipt and then a new
Preview and authorization for another action.

A crash after `recovery.verification-started` never returns to `RECOVERING` and
never repeats a restore. Replay verifies the same intent, guard, generation,
and scan-evidence prefix, performs a fresh read-only scan, and:

- if the guard tuple and target generation are unchanged, takes the same
  applicable `VERIFYING -> terminal` row;
- if an external generation change is proven, takes the applicable
  `recovery.stale` or `recovery.partial` row without mutation; or
- if the new observation is unavailable or ambiguous, leaves the Recovery
  Attempt `VERIFYING` under integrity failure.

Crash-point conformance covers at least: before authorization, after
authorization but before mutation, after checkpoint creation, between every
affected-entry write, after Postimage realization but before outcome
submission, during outcome submission, after Chronicle append but before the
Host receives the Receipt, before and after each journal fsync, during Head
replacement, during coordinator epoch change, and across every Recovery
Attempt boundary and every `RESTORE_BASE`, `ACCEPT_POSTIMAGE`, and `ABANDON`
observation row.

## Ownership and authority

| Component | Owns | Must not |
| --- | --- | --- |
| Researcher | Selection of Proposal, Validation Policy, target, residual-risk acceptance, explicit promotion authorization or rejection, explicit recovery action including abandonment, and any later Git publication decision | Treat Task approval or passing validation as promotion confirmation |
| Worker | Bounded edits inside its leased Crucible and a proposed summary of intent and risk | Read or write the Host target, choose a Promotion Target, forge Base or Postimage identity, or promote its output |
| Executor and exporter | Crucible Base capture, retained terminal-source ID/Sigil/Storage-Blob binding, post-Receipt bounded export, Patch Bundle construction, Blob commit, Reference Set and canonical-reference intent preparation, quota-safe quarantine or held disposition, and execution provenance | Backfill a Job or Agent Result, apply to the Host target, append Chronicle events, or make scientific or human decisions |
| Validation runtime | Execute declared checks in a fresh exact materialization and retain bounded evidence | Promote the patch or conceal failed and contradictory checks |
| Ward | Validate Capability, Task, execution, validation, and promotion-policy relationships | Execute a patch or infer human confirmation |
| Athanor | Validate and accept Proposal, evidence, authorization, recovery, and terminal outcome records; issue Receipts | Open or mutate a worktree, index, branch, ref, commit, or remote; invoke Git; or treat a Host claim as broader than its evidence |
| Chronicle | Preserve accepted Proposal, evidence, authorization, rejection, recovery, and outcome events and reconstruct their canonical relationships | Store mutable Crucibles, live apply locks, unbounded patch payloads, or act as a Git repository |
| Promotion Coordinator | Promotion Journal, coordinator epochs, trusted clock gate and anchors, target guards and fences, decision submissions, checkpoints, write-ahead intents, adapter orchestration, replay, and operational recovery | Append Chronicle, infer authorization, expose generic repository authority, or overwrite a terminal Attempt |
| MCP control surface | The four closed prepare, inspect, authorize, and outcome-recording operations owned by this RFC | Expose generic file, patch, shell, Git, web, command, recovery, or apply-anything authority |
| Interactive Host | Native target inspection and application, postimage verification, and user-facing approval UX through the bound coordinator and adapter | Write `.benchwork/` or the Promotion Journal directly, claim an Athanor Receipt before acceptance, or infer commit, push, merge, or publication authority |

Native Host tools may materialize and apply an authorized Bundle because the
human has selected that repository mutation. Canonical state still changes
only through Athanor. A native repository mutation performed without a valid
Promotion Authorization may exist on disk, but it is not a
Benchwork-recognized promotion and receives no fabricated lineage.

The promotion protocol does not turn MCP into the execution plane. Typed
requests carry identities, bounded evidence, and confirmations. Patch
materialization and Git behavior remain native Host operations, while Worker
execution remains subject to RFC-0011 through RFC-0013.

## Operational and canonical records

Chronicle records the exact accepted event types `patch.proposed`,
`patch.validation.recorded`, `patch.promotion.authorized`,
`patch.promotion.rejected`, `patch.promotion.outcome-recorded`, and
`patch.promotion.recovery-recorded`. `patch.proposed` binds exactly one prior
`agent-result/2.0` acceptance Receipt, its direct Job Outcome Sigil and retained
terminal-source ID/Sigil/Storage-Blob triple, and the exact RFC-0013 reference
intent and Reference Set. `patch.promotion.authorized` and
`patch.promotion.rejected` are the closed
terminal branches of the same typed human decision operation. Changing these
names or meanings requires a new RFC version and replay coverage.

Every one of those six transitions that creates, changes, or preserves managed
Blob reachability uses the same RFC-0013 sequence:

Before the first step, the coordinator replays Chronicle and requires
`expected_chronicle_head.event_count < U63_MAX`, so both the current Head and
the possible one-Event result fit RFC-0013's Phase 3 admission domain. At or
above the boundary it returns `PATCH_CHRONICLE_UNAVAILABLE` before Reference
Set registration, intent, reservation, Promotion-Journal mutation, or
Chronicle submission; it neither wraps nor clamps the count.
It also derives and validates the event-family request scope and deterministic
CTR-ID before the first side effect.

1. acquire the project canonical-reference gate before registering a newly
   derived Reference Set;
2. under the Storage Journal lock, register and read back that exact set, then
   release the Storage Journal lock while retaining the gate;
3. finalize the closed Athanor transition request and its Sigil only after the
   registered set IDs and Sigils are fixed, then atomically create or resolve
   the deterministic single-assignment request slot and read its complete
   bytes back;
4. under the Storage Journal lock, append
   `canonical_reference.intent_recorded` with the final request Sigil, expected
   Chronicle Head, complete sorted Reference Set and Blob closure, and reserved
   committed/release capacity; release that lock while retaining the gate;
5. ask Athanor to commit the exact request, whose event payload binds the
   reference-intent ID and record Sigil, request Sigil, and every Reference Set
   ID and Sigil; and
6. after verifying the Receipt, append and read back
   `canonical_reference.committed` under only the Storage lock, then release
   that lock while retaining the gate; and
7. under only the Promotion Journal lock, append and Head-commit
   `canonical.receipt-observed`, including any exact operational-root
   deactivations allowed by event row 6, release that lock, and then release the
   gate.

At no point do the Storage, Promotion, and Chronicle journal locks overlap. A
request slot is immutable operational control state but is not a root and
grants no canonical authority. A crash before it leaves at most an unrooted
deterministic Reference Set; a crash after it but before the intent leaves one
inert resolvable request. A crash or ambiguous response after the intent
leaves that intent `OPEN` and its complete closure pinned.
The next gate holder performs linearizable Chronicle recovery: an existing
exact Event and Receipt causes the missing committed event to be appended;
proven pre-commit absence plus definitive abort causes
`canonical_reference.released` with
`ABORTED_BEFORE_CANONICAL_COMMIT` only when the verified Head has advanced and
the exact RFC-0013 absence authority validates; unavailable, invalid,
unchanged, or ambiguous evidence leaves the intent open. Reference Set
registration alone is not a root.

A canonical candidate used as a newly derived Reference Set source contains
neither that future set nor the reference intent. The Proposal's own
`reference_set` is the earlier Bundle-sourced set, not a Proposal-sourced set.
In every case the later Chronicle Event carries the intent/set binding, which
keeps candidate, request, intent, Event, and Receipt hashes acyclic.

### Exact canonical transition wire shapes

The six final Athanor requests and six Chronicle event payloads are closed
local `$defs`. The table is their complete required field matrix; no common
base object contributes hidden fields.

| Canonical event | Exact final transition-request fields | Exact Chronicle event-payload fields |
| --- | --- | --- |
| `patch.proposed` | `schema_version: V<patch-proposed-transition-request/1.0>`; `transition_request_id: ID<CTR>`; `event_type: Enum<patch.proposed>`; `expected_chronicle_head: Obj<ChronicleHeadRef>`; `proposal: Obj<patch-proposal/1.0>`; `accepted_agent_result_receipt: ReceiptRef`; `reference_sets: Set<Obj<ReferenceSetRef>,1..1,reference_set_id>`; `managed_blob_sigils: Set<Sigil,1..MAX_BLOBS,value>`; `actor: Obj<ActorBinding>`; `chronicle_actor: Obj<ChronicleActor>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `requested_at: Time`; `transition_request_sigil: Sigil` | `proposal: Obj<patch-proposal/1.0>`; `accepted_agent_result_receipt: ReceiptRef`; `transition_request_id: ID<CTR>`; `canonical_reference: Obj<CanonicalReferenceBinding>`; `actor: Obj<ActorBinding>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `occurred_at: Time` |
| `patch.validation.recorded` | `schema_version: V<patch-validation-transition-request/1.0>`; `transition_request_id: ID<CTR>`; `event_type: Enum<patch.validation.recorded>`; `expected_chronicle_head: Obj<ChronicleHeadRef>`; `evidence: Obj<patch-validation-evidence/1.0>`; `proposal: Ref<PP>`; `reference_sets: Set<Obj<ReferenceSetRef>,1..1,reference_set_id>`; `managed_blob_sigils: Set<Sigil,1..MAX_BLOBS,value>`; `actor: Obj<ActorBinding>`; `chronicle_actor: Obj<ChronicleActor>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `requested_at: Time`; `transition_request_sigil: Sigil` | `evidence: Obj<patch-validation-evidence/1.0>`; `proposal: Ref<PP>`; `transition_request_id: ID<CTR>`; `canonical_reference: Obj<CanonicalReferenceBinding>`; `actor: Obj<ActorBinding>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `occurred_at: Time` |
| `patch.promotion.authorized` | `schema_version: V<patch-authorization-transition-request/1.0>`; `transition_request_id: ID<CTR>`; `event_type: Enum<patch.promotion.authorized>`; `expected_chronicle_head: Obj<ChronicleHeadRef>`; `authorization: Obj<patch-promotion-authorization/1.0>`; `preview: Ref<PRV>`; `client_request_sigil: Sigil`; `confirmation_token_sigil: Sigil`; `reference_sets: Set<Obj<ReferenceSetRef>,1..1,reference_set_id>`; `managed_blob_sigils: Set<Sigil,1..MAX_BLOBS,value>`; `actor: Obj<ActorBinding>`; `chronicle_actor: Obj<ChronicleActor>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `requested_at: Time`; `transition_request_sigil: Sigil` | `authorization: Obj<patch-promotion-authorization/1.0>`; `preview: Ref<PRV>`; `client_request_sigil: Sigil`; `confirmation_token_sigil: Sigil`; `transition_request_id: ID<CTR>`; `canonical_reference: Obj<CanonicalReferenceBinding>`; `actor: Obj<ActorBinding>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `occurred_at: Time` |
| `patch.promotion.rejected` | `schema_version: V<patch-rejection-transition-request/1.0>`; `transition_request_id: ID<CTR>`; `event_type: Enum<patch.promotion.rejected>`; `expected_chronicle_head: Obj<ChronicleHeadRef>`; `rejection: Obj<patch-promotion-rejection/1.0>`; `preview: Ref<PRV>`; `client_request_sigil: Sigil`; `reference_sets: Set<Obj<ReferenceSetRef>,1..1,reference_set_id>`; `managed_blob_sigils: Set<Sigil,1..MAX_BLOBS,value>`; `actor: Obj<ActorBinding>`; `chronicle_actor: Obj<ChronicleActor>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `requested_at: Time`; `transition_request_sigil: Sigil` | `rejection: Obj<patch-promotion-rejection/1.0>`; `preview: Ref<PRV>`; `client_request_sigil: Sigil`; `transition_request_id: ID<CTR>`; `canonical_reference: Obj<CanonicalReferenceBinding>`; `actor: Obj<ActorBinding>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `occurred_at: Time` |
| `patch.promotion.outcome-recorded` | `schema_version: V<patch-outcome-transition-request/1.0>`; `transition_request_id: ID<CTR>`; `event_type: Enum<patch.promotion.outcome-recorded>`; `expected_chronicle_head: Obj<ChronicleHeadRef>`; `outcome: Obj<patch-promotion-outcome/1.0>`; `authorization_receipt: ReceiptRef`; `terminal_journal_event_id: ID<PJE>`; `terminal_journal_event_sigil: Sigil`; `reference_sets: Set<Obj<ReferenceSetRef>,1..MAX_EVIDENCE,reference_set_id>`; `managed_blob_sigils: Set<Sigil,1..MAX_BLOBS,value>`; `actor: Obj<ActorBinding>`; `chronicle_actor: Obj<ChronicleActor>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `requested_at: Time`; `transition_request_sigil: Sigil` | `outcome: Obj<patch-promotion-outcome/1.0>`; `authorization_receipt: ReceiptRef`; `terminal_journal_event_id: ID<PJE>`; `terminal_journal_event_sigil: Sigil`; `transition_request_id: ID<CTR>`; `canonical_reference: Obj<CanonicalReferenceBinding>`; `actor: Obj<ActorBinding>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `occurred_at: Time` |
| `patch.promotion.recovery-recorded` | `schema_version: V<patch-recovery-record-transition-request/1.0>`; `transition_request_id: ID<CTR>`; `event_type: Enum<patch.promotion.recovery-recorded>`; `expected_chronicle_head: Obj<ChronicleHeadRef>`; `recovery_record: Obj<patch-promotion-recovery-record/1.0>`; `parent_outcome_receipt: ReceiptRef`; `terminal_journal_event_id: ID<PJE>`; `terminal_journal_event_sigil: Sigil`; `reference_sets: Set<Obj<ReferenceSetRef>,1..MAX_EVIDENCE,reference_set_id>`; `managed_blob_sigils: Set<Sigil,1..MAX_BLOBS,value>`; `actor: Obj<ActorBinding>`; `chronicle_actor: Obj<ChronicleActor>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `requested_at: Time`; `transition_request_sigil: Sigil` | `recovery_record: Obj<patch-promotion-recovery-record/1.0>`; `parent_outcome_receipt: ReceiptRef`; `terminal_journal_event_id: ID<PJE>`; `terminal_journal_event_sigil: Sigil`; `transition_request_id: ID<CTR>`; `canonical_reference: Obj<CanonicalReferenceBinding>`; `actor: Obj<ActorBinding>`; `authorization_sigil: Sigil`; `idempotency_key_sigil: Sigil`; `occurred_at: Time` |

In every branch, `actor.authentication_context_sigil` resolves the exact
authenticated invocation context that also produces `chronicle_actor`;
neither value may be supplied or rewritten by caller text.
`chronicle_actor.actor_id == actor.actor_id`. The closed kind relation is
`HUMAN -> human` and `SERVICE -> policy|tool|agent`, with the exact service
subtype, Chronicle `host`, and `authenticated_by` all taken from that same
context rather than inferred from an Actor ID, Host binding, or invocation
text. The complete `chronicle_actor` has no independent self-Sigil but is
covered by `transition_request_sigil`. Athanor copies it byte-for-byte into
the outer `chronicle-event/1.1.actor`; the payload `actor` remains the local
`ActorBinding`.

Every branch has one deterministic request namespace within the current
project store:

| Canonical event | `scope_kind` | `scope_id` source |
| --- | --- | --- |
| `patch.proposed` | `PROPOSAL` | `proposal.proposal_id` |
| `patch.validation.recorded` | `VALIDATION` | `evidence.evidence_id` |
| `patch.promotion.authorized` | `DECISION` | `preview.id` |
| `patch.promotion.rejected` | `DECISION` | `preview.id` |
| `patch.promotion.outcome-recorded` | `PROMOTION_OUTCOME` | `outcome.outcome_id` |
| `patch.promotion.recovery-recorded` | `RECOVERY_RECORD` | `recovery_record.recovery_record_id` |

The two decision branches deliberately share `DECISION`; changing
`AUTHORIZE` to `REJECT` under the same Preview and key reaches the same slot
and is a conflict, not a second request. Before any Reference Set or other
canonical side effect, the coordinator derives:

```text
transition_request_id =
  "CTR-" + UPPER_HEX(SHA256(canonical_json(
    ["patch-canonical-transition-request-id/1.0",
     scope_kind,
     scope_id,
     idempotency_key_sigil])))
```

The result is exactly 68 ASCII bytes and must match
`CTR-[A-F0-9]{64}`. A supplied or stored ID that does not equal this
derivation is invalid. The project-local unique identity is
`(scope_kind, scope_id, idempotency_key_sigil)`; the immutable-request resolver
index, Doctor, recovery, and conformance reject a second request or canonical
Event for that identity even if it uses another otherwise valid CTR-ID.

After the exact RFC-0013 Reference Sets are registered and read back, but
before a Reference Intent is created, the coordinator finalizes the complete
request and atomically creates or resolves one single-assignment request slot
at `transition_request_id`. First creation fixes every byte, including
schema branch, Event type, expected Head, candidate, Reference Sets, complete
Blob closure, Actor, Chronicle Actor, authorization, idempotency identity, trusted
`requested_at`, and `transition_request_sigil`. Exact retry returns those
stored bytes; it does not refresh the Head, time, Actor, Chronicle Actor,
authority, set, or closure. For an authorization or rejection decision this
finalization additionally resolves the unique
`preview.decision-submission-started` and requires:

```text
json_sigil(["patch-expected-chronicle-head/1.0",
            request.expected_chronicle_head])
  == submission_started.expected_chronicle_head_sigil
```

The selected Preview, decision branch, decision time, Actor, idempotency-key
Sigil, and redacted request Sigil must also equal that event. A missing event
or any mismatch is a closed conflict or integrity failure and cannot create,
replace, or submit a request. A registered-set/no-slot recovery reuses that
frozen Head rather than the current one. Any different complete bytes at the
same slot are
`PATCH_IDEMPOTENCY_CONFLICT`, including a different decision branch.

`LOCAL-PHASE3/1.0` realizes single assignment by writing the complete
canonical request to a coordinator-owned temporary file, fsyncing it,
installing it with no-replace semantics at the deterministic slot, and
fsyncing the parent directory. Only a complete Schema-valid final file whose
recomputed ID and Sigil match is addressable. A losing no-replace writer reads
and compares the winner. A temporary file is not a request and may be removed
after proving the final slot absent or valid; a malformed, truncated, or
conflicting final slot is an integrity failure and blocks canonical writes.
An ambiguous install acknowledgement is resolved by reading that same slot,
never by choosing another ID.

The request resolver accepts `(transition_request_id,
transition_request_sigil)`, returns the complete immutable request, and
recomputes every field and both hashes. RFC-0013 Reference Intent recovery,
Athanor submission, Chronicle replay, and Receipt recovery use that resolver;
none reconstructs a request from a Proposal, Preview, current clock, current
Actor, intent, or Event payload. The request has no future Intent, Event, or
Receipt field, so this durable write introduces no hash cycle.

Crash recovery is exhaustive:

| Durable boundary | Required recovery |
| --- | --- |
| No registered set and no request slot | Re-run read-only preflight and derive the same CTR-ID; no canonical side effect exists. |
| Registered set, no complete request slot | Reuse and verify RFC-0013's deterministic registered set. For a decision, resolve the exact `preview.decision-submission-started`, reconstruct the complete request with its frozen Head, and require the domain-separated Head-Sigil equality above before creating the one final request slot; never read the current Chronicle Head into that request. A missing event or mismatch fails closed and requires a new idempotency key. The unrooted set alone grants no authority. |
| Complete request slot, no Reference Intent | Resolve the exact bytes. Append an Intent only if the stored expected Head, authorization, Actor, Chronicle Actor, sets, Blobs, and all current predicates still verify; for a decision, recheck the write-ahead Head-Sigil equality; otherwise retain the inert request and return the closed precommit failure. A new attempt requires a new idempotency key. |
| Reference Intent `OPEN`, Chronicle result absent or ambiguous | Run RFC-0013 canonical-reference recovery using the exact resolved request; ambiguity leaves the Intent open and pinned. |
| Exact Chronicle Event and Receipt exist, committed Storage event missing | Verify Event, Receipt, request, Intent, sets, and closure, then append only the missing `canonical_reference.committed`. |
| Canonical commit and pin exist, Promotion observation missing | Append only the backward `canonical.receipt-observed` link under the Promotion Journal lock. |
| Conflicting request, duplicate identity, malformed slot, invalid Chronicle, or unverifiable resolver | Fail closed without a new request, Intent, Event, target mutation, or pin release. |

For every request, `transition_request_sigil` covers canonical JSON with only
that field omitted. `reference_sets` and `managed_blob_sigils` are the exact
sorted closure later copied into the RFC-0013 reference intent; no request
contains a future intent, Chronicle Event, or Receipt. The singular
authorization/rejection `authorization_sigil` is the decision-operation
authority proof and is distinct from the candidate record's self-Sigil.

For every one of the six request branches, the resolved RFC-0013
`artifact-storage-reference-intent/1.0` equals the final request under this
complete field map:

| Reference-intent field | Required final-request source |
| --- | --- |
| `transition_request_id` | `transition_request_id` byte-for-byte. |
| `transition_request_sigil` | `transition_request_sigil` byte-for-byte. |
| `canonical_event_type` | `event_type` byte-for-byte. |
| `expected_chronicle_head` | `expected_chronicle_head` byte-for-byte. |
| `reference_sets` | `reference_sets` byte-for-byte. |
| `blob_sigils` | `managed_blob_sigils` byte-for-byte. |
| `actor_id` | `actor.actor_id` and `chronicle_actor.actor_id` byte-for-byte. |
| `authorization_sigil` | `authorization_sigil` byte-for-byte. |
| `idempotency_key_sigil` | `idempotency_key_sigil` byte-for-byte. |
| `requested_at` | `requested_at` byte-for-byte. |

Its `reference_intent_id` uses the RFC-0013 RI-ID domain, `schema_version` is
constant, and `record_sigil` is recomputed over every other exact intent
field. There are no other copied, defaulted, or independently selectable
values. A structurally valid intent with any different request ID, event type,
actor, authority, idempotency identity, time, Head, set, Blob closure, or
request Sigil is unrelated and cannot authorize the Event or recovery.

For every event payload:

1. the embedded candidate and repeated fields are byte-for-byte equal to the
   accepted final request;
2. `transition_request_id`, payload `actor`, `authorization_sigil`, and
   `idempotency_key_sigil` equal the final request byte-for-byte, while the
   outer Chronicle Event type equals `request.event_type` and its complete
   `actor` equals `request.chronicle_actor` byte-for-byte;
3. `canonical_reference.transition_request_sigil` equals that request Sigil,
   its Reference Set array equals the request and RFC-0013 intent arrays, and
   its intent ID and record Sigil resolve to the exact still-open intent that
   satisfies every row of the complete map above;
4. `occurred_at` is the Chronicle linearization time and, for decisions,
   satisfies the bound deadline predicate;
5. the outer Chronicle Event supplies its own Event ID and body Sigil, and the
   paired Receipt remains outside this payload; and
6. unknown fields, missing closure members, different sorting, a mismatched
   repeated value, or an overlapping branch fail closed.

The executable Schemas publish these as
`CanonicalRequest.<event_type>` and `CanonicalPayload.<event_type>` local
`$defs`. Athanor cannot substitute an older generic proposal or decision
payload.

The canonical pin matrix is normative:

| Canonical event | Exact transition Reference Set source and managed closure | Gate/intent binding | Receipt recovery | Pin release |
| --- | --- | --- | --- | --- |
| `patch.proposed` | `BLOB_MANIFEST` source identity/Sigil both equal `patch_bundle_blob_sigil`; one explicit `BUNDLE_RETAINS_MEMBER` edge has `target_identity == target_sigil == patch_bundle_blob_sigil`, and the remaining edges cover the RFC-0012 source bundle named by `terminal_source.storage_blob`, Base and Postimage tree manifests, payloads, renderings, and attachments | final Proposal request, Bundle Reference Set, and every Blob Sigil including the terminal-source bundle and `patch_bundle_blob_sigil` | exact `patch.proposed` Event/Receipt commits the intent; ambiguity uses the generic lookup above | no committed-pin release exists in RFC-0014/1.0; RFC-0013 v1 rejects `CANONICAL_REFERENCE_REMOVED`, and a future removal requires a versioned Event/Receipt family |
| `patch.validation.recorded` | `CANONICAL_OBJECT` source equal to the Validation Evidence candidate; materialized Base/Postimage inputs, logs, result Artifacts or Blobs, and verifier evidence | final validation request and its newly registered Reference Set | exact validation Event/Receipt; failures and contradictory evidence retain separate pins | same permanent v1 pin: never because a check was superseded, failed, or aged; any future removal requires a versioned protocol |
| `patch.promotion.authorized` | `CANONICAL_OBJECT` source equal to the Authorization candidate; exact Proposal/Bundle closure, selected validation evidence, target-state evidence Blobs, and bounded displayed verifier material | final redacted authorize request, token Sigil only, and Authorization Reference Set | exact authorization Event/Receipt wins over operational expiry; ambiguity leaves Preview `DECIDING` and pin `OPEN` | same: Preview expiry, token consumption, or terminal promotion does not remove this canonical reference |
| `patch.promotion.rejected` | `CANONICAL_OBJECT` source equal to the Rejection candidate; exact Proposal/Bundle closure and evidence displayed for the rejected Preview | final redacted rejection request and Rejection Reference Set | exact rejection Event/Receipt; no mutation authority is created | same: rejection preserves rather than deletes the reviewed lineage |
| `patch.promotion.outcome-recorded` | `CANONICAL_OBJECT` source equal to the Outcome candidate; its new Reference Set covers terminal verifier, aggregate/receipt Adapter, path-observation, and diagnostics Blobs, while the intent also names every active lineage-root Reference Set, including checkpoint, mutation-intent, prior-step, verification, and terminal-evidence sets, plus Authorization/Proposal closure | final outcome request, all named Reference Sets, and backward terminal-Journal-event binding | exact outcome Event/Receipt; an observed Receipt completes an open intent without rewriting the terminal Journal event | same: operational holds may later release under the matrix below, but the committed canonical pin remains |
| `patch.promotion.recovery-recorded` | `CANONICAL_OBJECT` source equal to the Recovery Record candidate; its new set covers verifier/adapter/abandoned-state Blobs, while the intent also names every active Recovery lineage-root Reference Set, including parent checkpoint, recovery intent, verification and terminal evidence | final recovery request, all named Reference Sets, and backward terminal-Journal-event binding | exact recovery Event/Receipt; ambiguous replay never invents a resolved endpoint | same: no automatic release for Base restoration, Postimage acceptance, or abandonment |

Prepared Previews and their idempotency bindings are bounded append-only
Promotion Journal state; a cache may accelerate lookup but is not authority.
Decision submissions, clock anchors and gates, Promotion and Recovery Attempt
allocation, target guards, checkpoints, mutation intents, temporary staging
trees, partial writes, adapter logs, replay, and in-flight state are also
operational Promotion Journal state. They do not enter Chronicle merely because
they exist. They must be durable enough for the declared recovery profile,
unavailable to Workers, and cleaned only after all terminal and Recovery
Receipts and the retention policy permit it. The raw confirmation token remains
protected, is emitted only by Prepare and its exact retry, and is never copied
into Chronicle, Inspect, logs, diagnostics, or exported evidence.

Patch Bundles, payloads, manifests, validation logs, and verifier reports are
immutable committed Blobs or explicitly registered Artifacts under RFC-0013.
Failed export bytes are quarantined only after an exact Quarantine reservation;
otherwise they remain isolated `HELD_FOR_DISPOSITION`, retain their staging
charge, and are ineligible. Chronicle contains the eligible material's Sigils,
schemas, media types, bounds, and relationships.

Before any Promotion Journal event makes managed checkpoint, intent, adapter
receipt, verification, recovery, or Journal-tail evidence visible, the
Coordinator uses the same project-wide RFC-0013 outer canonical-reference gate
as RFC-0012 execution-root visibility. This is one gate, not a Promotion-local
lookalike. The exact acyclic sequence is:

1. commit and fully read back every referenced Blob, compute the complete
   bounded source-control candidate, and, for Evidence Manifest branches,
   compute every field except the not-yet-reserved activation Event ID;
2. acquire the outer gate before any Storage or Promotion visibility change;
3. under only the Promotion Journal lock, atomically reserve and fsync the
   single-assignment `(operational_journal_id, activation_event_id)` slot with
   its exact `activation_event_type` and one `payload_field`, then release that
   lock. The reservation is not an Event, has no sequence or Sigil, performs no
   revision, and creates no root; no Event other than the later exact planned
   Event may consume that ID;
4. while retaining the gate but no Journal lock, finalize, fsync, and read back
   the immutable checkpoint, mutation intent, recovery intent, or Evidence
   Manifest control record. An Evidence Manifest includes the already-reserved
   activation tuple; every record has its self-Sigil and contains no future
   Reference Set, plan, hold, Event Sigil, or Head;
5. under only the Storage Journal lock, register and read back an immutable
   Reference Set whose `source.kind` is `OPERATIONAL_CONTROL_RECORD` and whose
   source identity and Sigil equal the already-final record, capture its exact
   registration Event, then release the Storage lock;
6. while retaining the gate but no Journal lock, preallocate the hold ID and
   hold-set Event ID, derive the exact OperationalRoot ID, atomically
   create/fsync/read back the single-assignment
   `patch-operational-root-plan/1.0`, and verify that no conflicting slot is
   occupied;
7. under only the Storage Journal lock, validate that already-durable plan,
   append and verify
   `retention.hold_set`, capture its exact `StorageEventRef`, and verify the
   referenced Blob closure and active hold projection;
8. release the Storage lock while retaining the outer gate, then reacquire only
   the Storage lock for the final readback, freeze `StoragePrefixRef`, and
   verify Blob bytes, Reference Set, typed edges, root plan, hold Event,
   authorization source, and active projection again; release that lock;
9. for Journal-tail recovery only, construct and advance the immutable
   `TailRecoveryIntent` from the already-protected manifest/plan/hold without
   changing any planned identity;
10. under only the Promotion Journal lock, validate the complete `HoldBinding`
   and RootPlan against the frozen prefix and append and Head-commit exactly
   the planned event that first makes the control-record reference visible; and
11. verify that Event, its new Head, and the one planned `ACTIVE`
   OperationalRoot before releasing the Promotion lock and
   then the outer gate.

Every Storage operation that could release, supersede, or make a root
unavailable, including RFC-0012 execution-root removal and RFC-0013 GC root
freezing, acquires this same gate. Therefore no release can interleave between
the frozen Storage readback and Promotion-event visibility. The Storage and
Promotion Journal locks never overlap each other or Chronicle; each is
acquired only while the outer gate is already held.

The RootPlan, hold projection, and `retention.hold_set` Event are the complete
previsibility proof; no separately serialized hold object exists. A filename,
Promotion Journal reference, or pending upload is not an operational root. A
crash after only Event-slot reservation leaves no hold or root and that Event
ID can be resumed only with its exact tuple or abandoned forever. A crash
after the plan but before `retention.hold_set` leaves a plan-only orphan; a
crash after the hold but before the Promotion Event leaves a conservative
planned orphan hold. Recovery reacquires the outer gate and replays the
Storage and Promotion Journals one at a time. An exact retry may reuse only
the same reserved Event tuple, source record, plan, and hold; the manifest,
plan, Reference Set, hold, and Event each activate at most once.
Phase 3 has no release-authority branch for a hold whose planned Event never
created its `ACTIVE` root. If visibility is permanently abandoned, the plan
and hold remain conservative and Storage Doctor reports them. They are never
rebound to another Event/root or released from absence, age, generic
disposition, or a future-root lookup.

| Operational material and first visible event | Required pre-visibility protection | Exact release condition |
| --- | --- | --- |
| checkpoint Blobs at `promotion.checkpoint-committed` | reserve the one Event slot, then finalize checkpoint, Set, RootPlan, and hold in that order; the Event binds the exact plan-bearing `checkpoint_protection` and complete verification | only after a non-`PARTIAL` terminal Outcome Receipt, exact guard completion (including the legal no-allocation branch), policy retention, and closed intent absence; otherwise retain |
| mutation intent, topology plan, atomic or per-step receipts, and verifier material at `promotion.mutation-intent-committed`, guard validation, later validation, or terminal events | reserve the one Event slot, finalize the intent or exact Evidence Projection manifest, then Set, RootPlan, and hold; the Event binds the one planned protection | same non-`PARTIAL` Outcome conditions; `PARTIAL`, ambiguous causality, missing Outcome Receipt, or integrity failure retains the entire closure |
| parent checkpoint and new recovery intent/evidence at `recovery.checkpoint-verified` and `recovery.intent-committed` | reserve each Event slot, then finalize each recovery control record/manifest, Set, RootPlan, and hold; the binding covers the exact selected action and recovery evidence | only after a Recovery Record Receipt resolves exact Base or Postimage, a terminal physical guard, policy retention, and closed intent absence |
| `ABANDON` evidence at `recovery.abandoned` | reserve its Event slot, then finalize its exact abandonment manifest, Set, RootPlan, and hold with observed partial-state and logical-fence evidence | only after the `ABANDONED` Recovery Record Receipt embeds the exact patch-specific disposition, the physical guard is terminal, the fence remains, retention is met, and intent absence verifies; abandonment alone never releases |
| Journal suffix/torn-tail evidence at `coordinator.replay-started` | reserve the replay Event slot, then finalize the suffix Manifest, Set, RootPlan, and hold before the TailRecoveryIntent stages and bind their exact common protection | only after `coordinator.epoch-started` makes the completed tail root inactive, integrity is healthy, policy retention is met, and both Promotion/Storage recovery-intent absence branches verify |

For each satisfied row, the coordinator first finalizes and reads back the
exact `patch-operational-root-release-evidence/1.0`, then constructs
`PatchOperationalRootReleaseAuthority`. `operational_root_sigil` equals the
inactive root's self-Sigil; `operational_root_plan` names its exact plan;
`reference_set` and `hold_set_event` equal its `HoldBinding`;
`activation_event` is the exact `visible_event_id`/Sigil and sequence; and
`inactivation_event` is the exact `last_transition_event_id`/Sigil and
sequence. Both Event refs name this Promotion Journal and their types resolve
byte-for-byte. `release_evidence` names that exact release record.

The release-condition and terminal-authority mapping is closed:

| Release condition | Exact inactivation and terminal authority |
| --- | --- |
| `NON_PARTIAL_OUTCOME_OBSERVED` | `canonical.receipt-observed` for a complete non-`PARTIAL` `patch-promotion-outcome/1.0`; `terminal_authority` names that Outcome; canonical completion is committed; guard completion is terminal or exact no-allocation; Attempt-intent absence is selected. |
| `RESOLVED_RECOVERY_OBSERVED` | `canonical.receipt-observed` for a Recovery Record whose exact result is `BASE_RESTORED` or `POSTIMAGE_ACCEPTED`; `terminal_authority` names that Record; canonical completion, terminal guard, and Recovery-intent absence are required. |
| `ABANDONED_WITH_DISPOSITION` | `canonical.receipt-observed` for an `ABANDONED` Recovery Record containing the exact `AbandonmentDispositionAuthority`; `terminal_authority` names that Recovery Record, never an RFC-0013 disposition; canonical completion, terminal guard, preserved fence, exact deactivation set, and Recovery-intent absence are required. |
| `JOURNAL_RECOVERY_COMPLETED` | `coordinator.epoch-started` names the completed tail recovery and deactivates this root; `terminal_authority` names that exact Promotion Event; canonical and guard completion are not applicable, while healthy integrity and tail-intent absence are required. |

The `terminal_authority` `StorageControlRef` projection is exact:
`NON_PARTIAL_OUTCOME_OBSERVED` uses `{schema_version:
patch-promotion-outcome/1.0, record_id: outcome_id, record_sigil:
outcome_sigil}`; both Recovery conditions use `{schema_version:
patch-promotion-recovery-record/1.0, record_id: recovery_record_id,
record_sigil: recovery_record_sigil}`; and `JOURNAL_RECOVERY_COMPLETED` uses
`{schema_version: patch-promotion-journal-event/1.0, record_id:
inactivation_event.event_id, record_sigil: inactivation_event.event_sigil}`.
Each resolves the complete tabled record. No other Schema, ID projection, or
Sigil-only reference is legal.

The installed validator profile is deterministic:

```text
validator_sigil =
  Sigil(["patch-operational-root-release-validator-profile/1.1",
         "benchwork.patch-promotion", "1.0",
         ["NON_PARTIAL_OUTCOME_OBSERVED",
          "RESOLVED_RECOVERY_OBSERVED",
          "ABANDONED_WITH_DISPOSITION",
          "JOURNAL_RECOVERY_COMPLETED"],
         ["TERMINAL_GUARD",
          "NO_GUARD_ALLOCATED",
          "NOT_APPLICABLE_JOURNAL_SUFFIX"],
         "patch-operational-root-release-evidence/1.0"])

authority_sigil =
  Sigil(<complete PatchOperationalRootReleaseAuthority with only
         authority_sigil omitted>)
```

The validator resolves the exact release-evidence ID/Sigil, then requires
byte equality across its root, plan, hold, Set, Event, condition, and terminal
authority fields. It replays Promotion through `promotion_prefix` and the
inactivation Event, replays Storage through `storage_prefix`, verifies the
active pre-release hold and trusted clock, validates the exact
condition/canonical/guard branch, enforces every exact prefix inclusion and
Event-order predicate above, requires the replayed inactivation
`recorded_at`, recomputes retention and both absence sets, and, for
abandonment, validates every guard identity equality, the byte-identical
embedded completion, and exact deactivation set. `READ_ONLY_FAILED`,
`PARTIAL`, an open relevant intent, untrusted time, missing/extra evidence,
an earlier retention timestamp, or a branch mismatch retains the hold.
Bare Sigils may be indexed in the later Storage reason but never replace this
record or replay.

When a release condition is satisfied, the Storage Coordinator appends and
verifies RFC-0013 `retention.hold_released` with
`release_authority` equal to this complete object,
`authorization_sigil == authority_sigil`, and
`reason.code: OPERATIONAL_ROOT_TERMINATED`; the Event clock equals the
release-evidence clock observation. It proceeds through the reverse safe order. It
acquires the same outer gate, first
verifies that `canonical.receipt-observed` or
`coordinator.epoch-started` already made the exact operational root
`INACTIVE` in the Promotion projection and that the remaining tabled
conditions hold, then releases the Promotion lock, appends and reads back
`retention.hold_released` under only the Storage lock, and finally releases the
outer gate. RFC-0012 execution roots use the identical ordering. A crash leaves
an extra hold, never an unprotected visible root. Successful application,
process exit, wall-clock age, an absent local file, a failed scan, `PARTIAL`,
unresolved canonical submission, or `READ_ONLY_FAILED` never implies release.
Registered typed edges and all `OPEN`/`COMMITTED` canonical intents continue to
protect their closure independently.

## Invariants

- A Worker writes only its Crucible and never the researcher's Promotion
  Target.
- A Patch Proposal is a post-terminal derived object accepted only after and
  bound to exactly one accepted `agent-result/2.0` Receipt and directly copied
  RFC-0015 `OJ-` Job Outcome identity and Sigil and terminal-source
  ID/Sigil/Storage-Blob triple; it never backfills Job, execution-result, or
  Agent Result state.
- All 34 contracts, every nested object or union, all 47 Journal payloads, and
  all six final canonical request/event pairs resolve to exact closed local
  `$defs`; no implementation defers a shape to a future Schema.
- A complete Base manifest proves path membership. Explicit `ABSENT`
  preconditions are derived only after export proves an `ADD` path was absent.
- Eligible export bytes move through staging, complete verification, and
  committed Blob publication; canonical binding acquires the outer gate before
  Reference Set registration, final request Sigil, reference intent, Chronicle
  commit, and Receipt-backed pin; quarantine is reserved before use, and
  failed bytes remain `HELD_FOR_DISPOSITION` under backpressure when capacity
  is unavailable.
- Base, Patch Bundle, validation set, target preimage, and expected Postimage
  are immutable and Sigil-bound before human authorization.
- The trusted exporter, not the Worker, computes the authoritative change
  manifest and content identities.
- Validation is executed against a fresh exact Base-plus-Proposal
  materialization and never implies promotion.
- Every promotion requires explicit human confirmation for the exact Preview;
  the same typed decision operation can canonically preserve an explicit
  rejection without granting authority.
- A submitted decision ends only in an observed canonical Receipt, durable
  `DECISION_FAILED`, or unresolved `DECIDING`; expiry never overwrites any of
  those branches. The failed branch durably embeds its closed details and
  deterministic failure and error IDs.
- Preview and guard deadlines use trusted UTC plus live monotonic anchors;
  either due predicate wins, reanchoring only shortens, and clock uncertainty
  fences authority.
- Confirmation tokens contain at least 256 bits of CSPRNG entropy, use a
  domain-separated digest and constant-time comparison, and expose raw bytes
  only through Prepare, its exact retry, and the protected one-time request
  presentation.
- Prepare has a one-way hash graph: the Preview and `preview.prepared` bind only
  request/Preview/idempotency identity, while the later response alone binds
  the committed event.
- Code-modification Task approval and Promotion Authorization are distinct.
- A target mutation begins only from the exact authorized Base and succeeds
  only at the exact expected Postimage.
- Fuzzy application, implicit merge or rebase, and silent policy or assurance
  downgrade are prohibited.
- Duplicate delivery cannot apply a patch twice or create conflicting
  canonical records.
- A valid Journal Head commits one exact binary-frame prefix; only a complete
  valid suffix or one evidenced torn EOF frame is recoverable through the same
  staged intent, every ordinary append first proves EOF equals committed
  offset, and missing, middle-corrupt, or ambiguous authority fails read-only.
- A durable checkpoint, current target guard, and write-ahead mutation intent
  precede every target content side effect, and every managed operational Blob
  has a registered Reference Set and durable hold before Journal visibility.
  RFC-0012 execution roots and Promotion roots share one outer gate, and the
  Blob, set, Storage EventRef, frozen prefix, authorization, and hold remain
  verified until the visibility event commits.
- The reference adapter publishes one verified full-tree Postimage by atomic
  CAS over the Base, target-wide generation, guard/fence/deadline, root, and
  ancestors; optional per-entry mode additionally proves topology and pins
  every generation-advancing step receipt.
- Every physical fence CAS follows a Head-committed fence intent and exact
  readback; unknown or intermediate backend state never becomes `FENCED`.
- Project replay and admission preserve at most 4096 active target guards; a
  4097th guard produces no intent and no backend operation.
- Crash discovery of the Postimage without eligible adapter-write evidence is
  `RECOVERED_POSTIMAGE_OBSERVED`, never a causal `APPLIED` claim.
- Failed, stale, conflicting, cancelled, partial, rejected, recovered, and
  contradictory outcomes are preserved.
- A terminal Promotion Attempt never transitions again. Recovery from
  `PARTIAL` uses a new Recovery Attempt, authorization, and Record linked to
  but never rewriting the parent; `RESTORE_BASE`, `ACCEPT_POSTIMAGE`, and
  `ABANDON` have closed crash-replay outcomes.
- Athanor and MCP never inspect or mutate the Promotion Target, apply a patch,
  invoke shell or Git operations, or expose generic repository authority;
  Athanor may verify bounded control records and immutable Blobs.
- The native Host never writes `.benchwork/` directly.
- Promotion never automatically creates or seals scientific state and never
  grants commit, push, merge, review disclosure, deployment, or publication
  authority.
- Unknown or unverifiable identities, evidence, adapters, and recovery states
  fail closed.

## Compatibility and migration

This RFC preserves the accepted meanings of `capability-contract/1.0`,
`task-capsule/1.1`, `agent-result/1.1`, and
`code-modification-result/1.0`. In particular, the existing
`code-modification-result/1.0.data.patch` remains a Provider-neutral textual
Proposal. Its `tests_run` and `validation` fields remain a summary, not
identity-bound Validation Evidence.

A Phase 2 Code Modification Result is never directly eligible for this
promotion protocol. There is no inference of Base Identity from a Git branch,
current worktree, changed-file list, conversation, or patch context. There is
no inference of validation evidence from prose. There is no synthetic import
that manufactures the required Agent Result Receipt. A researcher may create a
new v2 Code Modification Task from the same intent, explicitly materialize the
declared Base, execute it, obtain a separately accepted `agent-result/2.0`
Receipt, and only then follow the post-terminal export, Proposal, validation,
and promotion path. The original v1 Result remains unchanged and is retained
only as provenance where an accepted contract permits that reference.

Existing Phase 2 native-tool workflows may continue to edit or apply patches
under direct human supervision. They are outside this Phase 3 promotion
protocol and receive no Patch Promotion Receipt or Sanctum assurance claim
unless repeated through the explicit v2 execution, result-acceptance,
post-terminal export, and promotion path.

No existing Chronicle event or Artifact field gains a new meaning. New
promotion events and Schemas require replay and migration coverage. RFC-0013
owns physical Blob and Replica semantics; this RFC owns their binding to Patch
Proposal and promotion lineage.

`agent-result/2.0` remains the immutable accepted execution result defined by
RFC-0015. It does not gain a Patch Proposal field after acceptance. RFC-0015
owns the shared MCP transport and `mcp-tool-registry/2.0`; that Registry must
add this RFC's four exact Patch operations and Schema identities without
changing their semantics. It may expose the derived Agent Result-to-Patch
relationship as a read projection but may not backfill either source object or
add a generic apply, recovery, file, shell, or Git escape hatch.

## Security and integrity

Patch Bundles, repository contents, validation logs, Git configuration, and
Worker summaries are untrusted inputs. Export, materialization, display, and
application are size-, path-, count-, and time-bounded. Parsers reject
ambiguous encodings, duplicate keys, unknown fields, absolute paths, traversal,
NULs, control characters, Unicode and case collisions, reserved names,
escaping links, special files, and identity mismatches.

`.benchwork/`, VCS administration directories, Host credential stores,
Agent-control sockets, and application checkpoints are outside patch scope.
They cannot be added, modified, deleted, traversed through a link, or smuggled
through an archive. At A2, the Worker cannot observe them. At A1, the runtime
must not claim malicious-code containment even though the exporter still
rejects out-of-scope output.

Git hooks, attributes, external diff drivers, clean/smudge filters, submodule
recursion, credential helpers, pagers, and repository-local executables can
execute code or change content interpretation. The reference adapter disables
them by default through a constructed environment and explicit configuration.
Any enabled behavior is a separately versioned adapter policy bound into the
Preview and human authorization. No promotion requires network access or
credentials.

Journal storage is adversarial crash evidence, not a stream that may be
best-effort parsed. Length duplication, frame hash, marker, event chain, Head
offset, and prefix Sigil jointly distinguish a permitted torn EOF from a
malformed complete frame, Head rollback, middle edit, appended garbage, or
ambiguous prefix. Ordinary append first proves physical EOF equality. A legal
complete or torn suffix becomes authority only through its protected staged
intent and exact replay event; a second crash cannot select another cut point.
The latter cases stop mutation and preserve bytes.

Target state is subject to time-of-check/time-of-use races. Root and ancestor
identity, target-wide content generation, guard backend generation, fencing
floor, and both deadline predicates therefore participate in the atomic
publish CAS. Descriptor-relative no-follow operations and explicit hard-link
profiles prevent an attacker from swapping an ancestor, mount, link, alias, or
add destination between scan and commit. A local lock or earlier scan alone
does not address this threat.

Wall clocks may jump, roll back, or slew, and monotonic clocks may reset across
suspend or restart. Evaluating UTC and monotonic due predicates independently,
using the earlier result, and allowing reanchors only to shorten authority
prevents clock behavior from extending a Preview or guard. Unverifiable time
fences all old guards before restoration.

Storage garbage collection is concurrent with proposal, validation, decision,
outcome, and recovery transitions. The outer canonical-reference gate plus
write-ahead reference intent closes that race for canonical bindings;
the same outer gate shared with RFC-0012, operational Reference Sets, exact
Storage EventRefs and frozen prefixes, and durable holds close it for
checkpoint, intent, receipt, verifier, recovery, and tail-repair material. An
ambiguous transition retains rather than releases.

MCP errors are an exfiltration surface. Patch failures expose only stable
codes, bounded closed details, redacted Sigils and logical IDs. Definitive
decision failures persist the complete details and verify deterministic IDs,
so retry cannot substitute mutable process memory. Tokens, paths, credentials,
stack traces, backend-private handles, and raw diagnostics are forbidden even
when an integrity or storage failure occurs.

Hash cycles are an integrity denial-of-service vector. Prepare binds only the
request-independent Preview identity before its event; the response binds that
already-committed event in one direction. Canonical candidates and requests
similarly exclude their future reference intent, Event, and Receipt.

Guard allocation is resource authority, not an unbounded queue. The global
4096 active-guard cap is checked under the replayed writer lock before any
backend request; exceeding it creates neither guard authority nor partial
admission.

Human-readable diffs are display data, not an authorization parser. The
confirmation UI must show at least Proposal identity, target identity, Base and
Postimage identities, affected paths, binary or link changes, validation
outcomes including failures, residual risks, application mode, and the absence
of commit or publication authority. Truncated displays state their bounds and
link to the exact immutable Bundle identity.

Sigils provide content integrity and relationship binding, not signatures or
protection from a malicious same-user Host process. A compromised Host,
kernel, Athanor, exporter, validation verifier, Promotion Coordinator,
Promotion Journal, application adapter, or filesystem can invalidate the
corresponding claim. The terminal Receipt states which verifier and evidence
profile were accepted; it never expands the threat model beyond those
components.

## Alternatives

- **Let the Worker edit the main worktree.** Rejected because it bypasses the
  Crucible boundary, human target selection, fencing, and recovery.
- **Automatically apply every successful Job output.** Rejected because Job
  success is neither validation nor human authorization.
- **Embed or later backfill a Patch Proposal in the Job or Agent Result.**
  Rejected because a Patch is derived only after terminal result acceptance,
  and immutable execution outcomes cannot acquire later fields.
- **Use the Phase 2 patch string as the promotion contract.** Rejected because
  it lacks Base, preimage, Postimage, payload, evidence, and target identity.
- **Use a branch name, tag, or `HEAD` as the Base.** Rejected because locators
  move and do not account for worktree overlays or content semantics.
- **Use unified-diff context and patch fuzz.** Rejected because heuristic
  application cannot prove the authorized Postimage.
- **Automatically three-way merge or rebase a stale patch.** Rejected because
  it creates a different change that requires a new Proposal, validation, and
  confirmation.
- **Have Athanor or MCP run Git.** Rejected because canonical transition
  authority must not become a repository execution surface.
- **Write patch payloads and logs into Chronicle.** Rejected because Chronicle
  stores canonical relationships, while RFC-0013 owns bounded Blob storage.
- **Treat passing tests as promotion approval.** Rejected because empirical
  evidence cannot replace researcher authority.
- **Assume a retry can safely rerun the patch command.** Rejected because a
  crash may occur after side effects but before acknowledgement; Base and
  Postimage identities are required to decide safely.

## Non-goals

- automatic conflict resolution, merge, rebase, cherry-pick, or patch fuzz;
- automatic Git commit creation, branch or ref updates, push, pull-request
  creation, release, deployment, or publication;
- multi-repository atomic promotion;
- semantic proof that a patch is correct, secure, or scientifically valid;
- replacement of code review, experiment registration, Run collection,
  Alembic analysis, or human Decision;
- direct promotion of Phase 2 Code Modification Results;
- remote target mutation or credential brokering in the `0.4` reference
  runtime;
- protection from a compromised Host administrator, kernel, control plane, or
  trusted adapter; and
- changing RFC-0011's assurance levels or RFC-0013's storage and retention
  contracts.

## Acceptance tests

Acceptance requires executable Schemas, bounded fixtures, replay coverage, a
local threat-model review, and a reference Host-native adapter. The combined
suite must demonstrate:

1. exactly the 34 contracts listed in this RFC are published under their exact
   identifiers and conventional filenames; each executable Schema reproduces
   its complete required top-level field set, nested closed branches, explicit
   nullability, integer and byte bounds, array cardinality, sort/uniqueness
   rule, and self-Sigil rule, and rejects every unknown field, version,
   identity profile, policy, adapter, event, state, and enum value; a mechanical
   resolver proves that every `Obj`, `Union`, all 47 Event payload branches,
   and all six canonical request/event pairs resolve to one local exact `$def`;
   `patch-tree-manifest/1.0` fixtures independently verify its content Sigil,
   contextual record Sigil, canonical manifest Blob, entry/root identities,
   and zero-entry tree;
   boundary fixtures reject seven-or-more fractional timestamp digits and
   reject `U63_MAX + 1` for every managed Blob size or directly copied byte
   count before Storage or canonical side effects, admit a Chronicle Head only
   while its next Event count remains within U63, and fail at or above
   `U63_MAX` before Reference Set, intent, reservation, Promotion-Journal, or
   Chronicle side effects;
2. `mcp-tool-registry/2.0` contains the four exact Patch tools, each advertises
   its exact closed request Schema, every successful `data` value validates
   against its exact response Schema, every failure uses one listed stable
   Patch code and the exact closed 16384-byte-bounded details branch without
   secrets or paths, and no generic apply, recovery, filesystem, shell, Git,
   web, or arbitrary-execution tool exists;
3. the same complete Base tree produces the same identity independent of
   traversal order, timestamps, inode numbers, and checkout path, while any
   included content, type, mode, link, submodule, path-set, or profile change
   changes the identity; the positive fixture copies
   `source_root_id`/`source_root_sigil` from the RFC-0015 terminal source and
   recomputes the manifest from that exact pinned root, while a same-ID,
   different-Sigil root and any manifest not derivable from the pinned root
   are rejected; scope fixtures prove empty-included means the complete tree,
   exclusion/protection wins, component prefixes do not use lexical prefix,
   ancestors are complete, case collisions reject, and CRUCIBLE versus
   PROMOTION_TARGET records retain different record Sigils but equal governed
   content produces the same `TreeIdentity`;
4. the Base contains no guessed future `ABSENT` entries; after export discovers
   an `ADD`, the exporter proves non-membership in the complete Base path set
   and proves the absent path is scope-admissible with a complete verified
   ancestor chain before writing the explicit `ABSENT` precondition into the
   Bundle;
5. mutable refs, branch names, tags, `HEAD`, paths, sparse or partial
   manifests, and clean-status claims cannot substitute for complete Base
   identity or prove add-path non-membership;
6. no Patch export or Proposal exists before terminal execution and one
   accepted `agent-result/2.0` Receipt; deriving a Patch never changes the Job,
   `execution-result/1.0`, Agent Result, or their Receipts;
7. normal export uses fresh RFC-0013 staging, complete byte, size, Sigil,
   source, and Receipt verification, verified no-overwrite Blob commit, and
   final Bundle commit; it then acquires the canonical-reference gate before
   Reference Set registration, registers and reads back the set inside the
   gate, derives the deterministic CTR-ID, atomically creates and reads back
   the complete single-assignment request, commits the exact reference intent,
   commits `patch.proposed`, commits the Receipt-backed pin, Head-commits the
   backward-only `canonical.receipt-observed`, and only then releases the gate;
   failed material enters Quarantine only after its exact reservation, while
   exhausted capacity produces isolated
   `HELD_FOR_DISPOSITION`, retained staging charges, and backpressure;
8. the exporter resolves the exact terminal-source
   ID/Sigil/`storage_blob` triple, verifies and decodes that one RFC-0012
   `benchwork-source-tree/1.0` bundle, derives changed paths, primitive
   operations, payload Sigils, `patch-tree-manifest/1.0`, and Postimage outside
   the Worker, and the Base-plus-operations derivation equals the retained
   bundle projection byte-for-byte at `TreeIdentity`; fixtures reject a
   different bundle Blob, source manifest, profile Ref, path set, entry,
   executable-mode interpretation, count, root, or derived manifest Blob;
9. export rejects traversal, absolute and control paths, duplicate and
   case-colliding names, escaping links, special files, changed immutable
   inputs, unsupported modes, and size or count exhaustion without exposing a
   partial, quarantined, or held Bundle as eligible;
10. failed, cancelled, expired, fenced, and policy-violating Executor Attempts
    preserve their Crucible evidence but cannot yield a promotion-eligible
    Proposal;
11. `patch.proposed` resolves exactly one matching accepted Agent Result event
    and Receipt, resolves the exact RFC-0015 `OJ-` Job Outcome rather than a
    generic `JO` reference, directly equals its Job Outcome Sigil and retained
    terminal-source ID/Sigil/Storage-Blob triple, validates its registered typed
    Reference Set and open canonical-reference intent, accepts at most one
    Proposal per Agent Result Receipt and exact terminal-source triple, treats
    an exact duplicate idempotently, and rejects a different Proposal without
    backfill; the transition-request,
    reference-intent, canonical Event, and Receipt fixture has no hash cycle,
    ambiguous intent remains `OPEN`, and only proven pre-commit abort releases
    it;
12. tampering with an Agent Result Receipt, Base, manifest, payload, committed
    Blob, Patch Bundle, Reference Set, canonical-reference intent, Proposal,
    validation log, or evidence Sigil prevents proposal or promotion
    acceptance;
13. Validation Evidence is accepted only for the exact Proposal, Base,
    Postimage, policy, runtime, environment, Job, Attempt, assurance, and
    retained outputs, and prose such as `validation: passed` is insufficient;
14. validation runs in a fresh Base-plus-Proposal materialization, every
    `FAIL`, `ERROR`, `CANCELLED`, `INELIGIBLE`, superseded, and contradictory
    result remains visible, and later `PASS` evidence does not overwrite it;
15. a promotion Preview fails when any required check is absent,
    under-assured, non-passing, stale, or bound to a different Proposal,
    Receipt, target, or policy;
16. Code Modification approval, Ward `PASS`, Job success, Agent Result
    acceptance, passing validation, general Host approval, and previous
    confirmation cannot replace `decision: AUTHORIZE` plus explicit affirmative
    confirmation of the exact Preview, while `decision: REJECT` produces its
    exact canonical rejection Receipt and no mutation authority through the
    same typed tool;
17. changing the Proposal, Base, Postimage, target, evidence set, policy,
    adapter, mode, affected paths, recovery action, or Preview Sigil
    invalidates confirmation and requires a new Preview; canonical
    Authorization embeds the complete target-state evidence and copies the
    target generation, affected paths, operation Sigil, and residual risks
    byte-for-byte, so Chronicle-only replay detects every mismatch and
    change-away-and-back;
18. exact duplicate prepare, authorize, and outcome requests return the same
   Preview including its still-valid token or the same authorization,
   rejection, or outcome Receipt, conflicting idempotency-key reuse fails,
    token generation uses at least 256 bits from an OS CSPRNG,
    domain-separated digest comparison is constant-time, raw confirmation
    tokens are emitted only in Prepare and its exact retry and are accepted
    only on the protected one-time request path, and Inspect is read-only,
    bounded, paginated, and free of paths, confirmation or guard tokens,
   checkpoints, payload bytes, and credentials; `preview.prepared` contains no
   response Sigil, its response-independent binding recomputes exactly, and the
   response points only backward to the committed event; a definitive abort
   after decision submission durably embeds the complete closed error details
   and deterministic failure/error IDs in `DECISION_FAILED`, exact retries
   return that same object, and an ambiguous submission remains retryable
   `DECIDING`; the definitive local failure leaves its reference intent
   `OPEN` at the unchanged expected Chronicle Head, and only a later
   Head-advanced complete RFC-0013 absence proof may release that intent;
19. Promotion Journal events validate their closed payloads, sequence,
    revision, coordinator epoch, Sigil, and previous-event link;
    `preview.prepared` makes Prepare and its idempotency binding restart-safe,
    the same outer gate brackets decision submission, Chronicle commit,
    Receipt observation, and expiry, while the Promotion Journal lock
    serializes only the local submission, observation, and expiry events; a
    crash after either canonical decision returns the original Receipt and
    that Receipt can never be overwritten by expiry; canonical decision
    payloads omit their own Event and Receipt and observation events refer only
    backward; frames validate exact leading and
    trailing lengths, canonical event bytes, frame hash, and marker; `HeadRef`
    resolves by Journal ID, generation, committed offset, prefix Sigil, and
    Head Sigil; ordinary append rejects EOF unequal to committed offset; both
    complete and torn suffixes use one protected staged tail intent; a crash at
    each protection, frame stabilization, Head installation, replay-event, and
    completion boundary follows the exact second-crash table; every immutable
    stage record chains to and preserves its predecessor, the replay event
    binds only the stable `HEAD_INSTALLED` record, an adopted ordinary
    replay-started frame uses the single `REPLAYING -> REPLAYING` branch, and
    an adopted integrity-failed frame completes without appending to the
    read-only State; a missing non-empty Head, middle corruption, invalid
    complete frame, bytes after a torn frame, or ambiguous cut point enters
    `READ_ONLY_FAILED`; and replay produces the same byte-level
    `patch-promotion-state/1.0`;
20. a deadline becomes due when trusted UTC reaches `due_at` or monotonic
    elapsed reaches the original remaining duration; rollback cannot extend
    it, a trusted forward jump expires it immediately, slew tests let either
    clock win, and every restart/restoration reanchor uses the minimum of wall
    and prior-monotonic remaining time; divergence, monotonic reset, and
    uncertain suspend enter `coordinator.clock-uncertain`, fence guards, resolve
    canonical decisions, and issue no new authority until a valid
    `coordinator.clock-restored`;
21. the exact 47 event types each accept only their one tabled source revision
    set, closed payload, and destination; every acquire, renewal, release, and
    fence follows its durable intent; crash injection before and after fence
    intent, backend CAS, readback, terminal event, replay-start, and a second
    recovery crash executes the `FENCING`/`RECOVERING` tables; intermediate or
    unverifiable generations fail closed; a fixture with both adapter limits
    set to 4096 admits exactly 4096 active guards project-wide and rejects the
    4097th before any guard event or backend operation, clock uncertainty lists
    the complete bounded active set, and replay above the cap fails read-only;
    unlisted and post-terminal transitions change neither journal nor target;
22. before every target content side effect, the current guard and fencing
    generation, both deadline predicates, root and ancestor identities,
    target-wide content generation, complete checkpoint, mutation or recovery
    intent, event frame, and updated Head are durable and immediately
    revalidated; checkpoint, intent, step-receipt, verifier, and recovery Blobs
    are invisible to the Journal until their exact source control record or
    19-row Evidence Manifest is finalized, its typed-member Set is registered,
    its single-assignment RootPlan is fsynced, and its planned
    `retention.hold_set` Event is durable; external `HoldBinding` verifies the
    plan, Storage EventRef, frozen prefix, Reference Set, policy tuple, and exact
    domain-separated authorization; step-zero guard validation protects its
    readback/clock evidence, suffix evidence has one manifest meaning, and
    fixtures reject a changed source, extractor, member, plan, activation
    Event/type/field, root ID, Set, policy, hold/Event ID, reused manifest/hold,
    future-root lookup, or 20th projection branch; RFC-0012 execution roots and
    Promotion roots contend on the same outer gate, Blob/set/plan/hold readback
    remains valid until the one activation; fixtures reserve the activation
    Event ID/type/field before Manifest finalization, reject a second field in
    the same `(journal_id, event_id)` slot, reject 4,097-member `S(...)`,
    typed-member, edge, or validation-evidence unions (including 4,096
    verifier Sigils plus required adapter/diagnostics), and admit exact 4,096
    boundaries where every aggregate fits; root release uses reverse order
    and the exact four-condition authority plus replayable Release Evidence,
    exercises terminal/no-guard/suffix guard completion, exact
    terminal/guard/inactivation sequence and prefix inclusion,
    canonical-commit inclusion, named absence projections, and
    retention/clock equality to the replayed inactivation `recorded_at`;
    abandonment fixtures terminalize the same Recovery Intent guard after
    `recovery.abandoned` but before Record construction, preserve the logical
    fence, embed the byte-identical completion, and reject an unrelated guard,
    reversed order, pre-Receipt Storage release, or generic disposition;
    crashes after slot reservation, plan, hold, or activation follow their
    distinct conservative outcomes and fixtures prove no self-hash cycle;
23. the `0.4` adapter builds and verifies the complete Postimage and performs
    one full-tree atomic CAS conditional on Base, global content generation,
    guard/fence/deadline, root, and ancestors, returning a durable receipt and
    readback; optional per-entry adapters are rejected unless every writer
    participates in one target-wide generation, the closed topology plan and
    old/new ancestor identities verify, every step atomically advances the
    generation and durably pins its receipt before the next step, and crash
    replay never repeats an unproven step; their `max_paths` cannot exceed
    `MAX_EVIDENCE`, and final evidence contains exactly one receipt per
    affected path while full-tree evidence contains exactly one transaction
    receipt; guard expiry or fence change stops
    further writes and two concurrent promotions cannot apply different
    Postimages from one Base;
24. delivery after the Postimage already exists and before mutation intent
    creates no intent, performs no second content mutation, and records
    `ALREADY_APPLIED`; replay after an intent records `APPLIED` only with
    eligible causal adapter-write evidence and otherwise records
    `RECOVERED_POSTIMAGE_OBSERVED`;
25. affected-path races, add collisions, file/directory collisions,
    ancestor link or mount replacement, hard-link aliasing, unsupported target
    semantics, and mixed preimage/postimage states produce retained `CONFLICT`
    or `PARTIAL` evidence rather than fuzzy application or an out-of-root
    write; fixtures enforce the exact `ADD`, `MODIFY`, `DELETE`, and
    `TYPE_CHANGE` preimage/postimage matrix and reject a same-path delete/add
    surrogate;
26. crash injection before and after frame length/body/hash/tail/marker writes,
    frames fsync, Head temp fsync/replace/directory fsync, the ordinary EOF
    equality check, suffix-evidence hold, each staged tail-recovery
    immutable intent record/truncation/Head/replay-event transition,
    predecessor-pointer replacement and a second crash, decision submission,
    Chronicle append,
    clock transition, guard acquire/fence/renew/validate/release, operational
    hold, checkpoint or intent commit, atomic publish or per-entry CAS receipt,
    Postimage verification, outcome submission, and coordinator epoch change
    deterministically classifies Base, Postimage, partial, stale, no-change,
    abandonment, or integrity failure and never applies an eligible patch
    twice;
27. restart replay fences older guards before mutation, terminalizes an
    interrupted Promotion intent as verified no-change `FAILED`, causally
    proven `APPLIED`, `RECOVERED_POSTIMAGE_OBSERVED`, or `PARTIAL`, and stops
    all mutation when journal or target evidence is unverifiable;
28. a terminal `PARTIAL` Promotion Attempt has no outbound transition;
    recovery requires a new `RECOVER_PARTIAL` Preview, explicit confirmation,
    Recovery Attempt, guard, checkpoint binding, write-ahead recovery intent,
    and Recovery Record, and crash replay executes the exact separate
    `RESTORE_BASE`, `ACCEPT_POSTIMAGE`, or `ABANDON` observation table without
    automatically resuming a partial restore; every intent-present observation
    first commits `recovery.verification-started`, every terminal then starts
    from `VERIFYING`, and a crash after verification-started repeats only the
    scan and never the recovery write;
29. `BASE_RESTORED`, `POSTIMAGE_ACCEPTED`, and `ABANDONED` belong only to the
    Recovery Attempt, the parent remains `PARTIAL`, `ABANDONED` retains the
    logical partial fence, embeds the exact Actor/approval/policy/root-set
    disposition with `physical_byte_authority: NONE`, rejects every generic
    RFC-0013 disposition substitute, and releases only through its canonical
    Receipt plus terminal guard and replayable release evidence; a failed,
    stale, or partial recovery cannot overwrite a newly authorized target
    state or conceal either history;
30. failed, stale, rejected, cancelled, conflicting, partial, recovered, and
    successful Promotion and Recovery outcomes survive Host restart, Promotion
    Journal replay, and Chronicle replay without rewriting earlier records;
31. Patch Bundles, component payloads, checkpoints, logs, and verifier material
    remain RFC-0013 Blobs or explicitly registered Artifacts; each of
    `patch.proposed`, `patch.validation.recorded`,
    `patch.promotion.authorized`, `patch.promotion.rejected`,
    `patch.promotion.outcome-recorded`, and
    `patch.promotion.recovery-recorded` validates every exact field in its
    tabled final request and Chronicle payload and exercises the canonical pin
    matrix from gate acquisition through Reference Set registration, final
    deterministic CTR-ID, single-assignment request slot and Sigil, intent,
    Receipt-backed commit or exact recovery; request,
    intent, and Event set/Blob closures compare byte for byte, the
    Bundle-sourced set has an explicit edge targeting the Patch Bundle Blob
    itself; every request's payload Actor, authenticated-context-derived
    Chronicle Actor, and outer Event Actor obey their exact equality and kind
    rules; and every intent request ID/type/Head/actor/authorization/
    idempotency/time field follows the complete mapping table; open and
    committed intents retain the validated closure, operational releases
    require their tabled Receipt/guard/retention/disposition conditions, and
    Chronicle contains only bounded identities and relationships; fixtures
    admit an aggregate closure of exactly 4,096 distinct managed Blobs
    including the RFC-0012 terminal-source bundle, both tree manifests, and the
    Patch Bundle Blob and reject the 4,097th during read-only preflight before
    any staging reservation/write, Blob commit, Reference Set, control record,
    journal append, canonical submission, or target side effect, even when
    each contributing field remains within its own bound;
    fixtures cover every scope-kind/source row, prove AUTHORIZE versus REJECT
    under one Preview/key conflicts in the same CTR slot, and inject crashes
    before and after Reference Set registration, request temporary-file fsync,
    no-replace install, directory fsync, request readback, intent append,
    Chronicle acknowledgement, committed-pin append, and Promotion
    observation; a decision fixture crashes after
    `preview.decision-submission-started` and Reference Set registration but
    before request-slot creation, advances Chronicle to a newer Head, and
    proves recovery either reuses the frozen complete Head whose
    domain-separated Sigil equals the submission event or fails closed, while
    a request containing the newer Head is rejected without a slot or
    canonical side effect; exact retry reuses the original request bytes and
    no branch selects a second CTR-ID;
32. a Worker, Executor, exporter, and validation runtime cannot mutate the
    Host target or append Chronicle events; the native Host cannot write
    `.benchwork/` or the Promotion Journal directly; and only the Promotion
    Coordinator may append legal operational events;
33. Athanor and MCP do not inspect or mutate the Promotion Target, apply a
    patch, or invoke shell or Git actions; bounded Blob and record verification
    remains allowed;
34. Git hooks, filters, external drivers, submodule recursion, credential
    helpers, repository executables, network access, and credentials are
    disabled by default and any exception is explicitly profile- and
    authorization-bound;
35. successful promotion creates no Git commit, branch or ref update, remote
    mutation, pull request, or new scientific Run, Artifact, Assessment,
    Decision, or Seal unless a separately authorized transition occurs; and
36. an existing `code-modification-result/1.0` fixture retains its Phase 2
    meaning, is rejected as a direct Phase 3 Patch Proposal, and can enter this
    protocol only through an explicit accepted v2 execution result,
    post-terminal export, new identity, validation, and confirmation path.

The `0.4` reference vertical slice must retain evidence for at least successful
post-Receipt derivation from the exact RFC-0012 source-tree
ID/Sigil/Storage-Blob triple, deterministic bundle decode, and executable
`patch-tree-manifest/1.0` projection under both `CRUCIBLE` and
`PROMOTION_TARGET` contexts; staging-to-committed export; Reference Set
registration inside the outer gate and canonical-reference intent/Receipt-pin
recovery for all six exact canonical request/event shapes; deterministic
CTR-ID derivation for every scope row, same-slot AUTHORIZE/REJECT conflict, and
single-assignment request-slot recovery at every temporary-file fsync,
no-replace install, directory-fsync, and readback boundary; shared
RFC-0012/Promotion
outer-gate contention; operational `StorageEventRef`/frozen-prefix hold
recovery and reverse-order release;
reserved failed-export Quarantine and quota-exhausted
`HELD_FOR_DISPOSITION`; full-tree atomic-CAS application and rejection of an
unverifiable per-entry platform;
already-applied duplicate delivery; recovered Postimage with and without causal
adapter-write evidence; explicit rejection; authorization-versus-expiry crash;
response-independent Prepare hashing; definitive post-submission
`DECISION_FAILED` durable-details retry with unchanged-Head open-intent and
Head-advanced exact-absence release fixtures; clock rollback, forward
jump, slew, non-lengthening reanchor, and restoration; guard acquire, renewal,
expiry, 4096/4097 active-guard admission, fence-intent CAS, release, crash
recovery, and crash during recovery; ordinary EOF mismatch refusal, complete
valid Journal suffix and torn EOF through every staged-intent second-crash
boundary, missing Head, middle corruption, and ambiguous-tail failure; stale
target; ancestor-link
replacement; conflict restored to Base; `PARTIAL` followed separately by
`recovery.verification-started` and `BASE_RESTORED`,
`POSTIMAGE_ACCEPTED`, and `ABANDONED` Recovery Attempts; idempotency-key
collision; Journal and Host restart at every write-ahead boundary; and all
protected-path attacks. Its documentation must state that Patch Promotion is
experimental and does not authorize or perform Git publication.
