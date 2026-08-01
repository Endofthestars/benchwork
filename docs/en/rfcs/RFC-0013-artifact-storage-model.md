---
title: "RFC-0013: Artifact Storage Model"
document_id: BW-RFC-0013
version: 0.1
status: draft
owner: unassigned
date: 2026-07-31
language: en
canonical: true
---

# RFC-0013: Artifact Storage Model

## Status

This draft defines the Phase 3 storage boundary used by Sanctum execution. It
builds on RFC-0011 and consumes the Job, Attempt, Lease, and fencing identities
defined by RFC-0012. It does not authorize automatic Artifact registration,
reinterpret an accepted `artifact/1.0` record, or claim a production Artifact
Registry. It does add a versioned Alpha safety restriction for new
`artifact/1.0` registrations so that canonical v1 paths cannot alias managed
storage.

Phase 3 must publish closed executable Schemas, fixtures, a local reference
backend, and conformance evidence before this model can be accepted. Remote
backends and production retention automation remain Phase 4 work.

## Problem

Phase 2 records a canonical `artifact/1.0` only after Athanor verifies a local
root-contained file against its SHA-256 Sigil. Current validation resolves the
URI under the project root and also accepts an absolute URI whose resolved
target remains inside that root. That record gives the
scientific object a stable ID, a Program, a kind, a producing object, input
lineage, a registration time, and a Receipt. It does not define a storage
service, a physical object lifecycle, replication, transfer, quarantine,
retention, or garbage collection.

Phase 3 introduces execution outputs that may be partial, duplicated, late,
hostile, too large, corrupt in transit, or produced after a Lease is fenced.
It must also materialize immutable inputs into a Crucible without exposing
canonical or operational control-plane storage to the Worker. Treating every
path, object-store key, cache entry, or Worker claim as an Artifact would erase
the distinction between observed bytes, durable storage, and scientific
acceptance.

The storage model therefore needs to answer:

1. what identity belongs to the logical Artifact and what identity belongs to
   its bytes;
2. when transferred bytes become an eligible Blob and a usable Replica;
3. how imports, exports, materializations, retries, and crashes retain
   end-to-end integrity and provenance;
4. which storage state is operational and which state is canonical;
5. how retention and garbage collection avoid deleting live or scientifically
   referenced material; and
6. what a backend must prove before Benchwork relies on it.

## Decision

Benchwork separates a canonical logical **Artifact** from an immutable
content-identified **Blob** and from each physical **Replica** of that Blob.

```text
logical Artifact (Chronicle, Athanor authority)
                  |
                  | binds one byte Sigil
                  v
        Blob (immutable byte identity)
             /          |          \
            v           v           v
      Replica A    Replica B    unavailable
       local         remote      identity only
```

The relationships are:

- an `artifact/1.0` is a canonical research object;
- a Blob is one finite, opaque byte string identified by its byte-level Sigil;
- a Replica is one backend's physical realization of exactly one Blob;
- multiple logical Artifacts may bind the same Blob;
- one Blob may have zero, one, or many Replicas;
- a Blob or Replica may exist without any canonical Artifact; and
- storing, copying, exporting, deleting, or restoring bytes never creates,
  updates, or deletes a canonical Artifact.

A materialized file, extracted tree, download stream, staging object, log
capture, or Crucible output is not a Blob or Artifact merely because it exists.
It becomes an eligible Blob only through the verified commit protocol in this
RFC. It becomes a canonical Artifact only through an explicit Athanor
transition and Receipt.

Phase 3 adds independent storage contracts. The exact contract set owned and
required by this RFC is:

- `artifact-blob/1.0`;
- `artifact-replica/1.0`;
- `artifact-transfer/1.0`;
- `artifact-transfer-attempt/1.0`;
- `artifact-provenance/1.0`;
- `artifact-materialization/1.0`;
- `artifact-storage-backend/1.0`;
- `artifact-retention-policy/1.0`;
- `artifact-storage-reference-set/1.0`;
- `artifact-storage-reference-intent/1.0`;
- `artifact-storage-legacy-protection/1.0`;
- `artifact-gc-plan/1.0`;
- `artifact-storage-disposition/1.0`;
- `artifact-storage-journal-event/1.0`;
- `artifact-storage-journal-head/1.0`;
- `artifact-storage-state/1.0`;
- `artifact-storage-tail-evidence/1.0`;
- `artifact-storage-recovery-marker/1.0`; and
- `artifact-storage-doctor-report/1.0`.

Each conventional filename replaces `/` with `-` and appends `.json`; for
example, `artifact-storage-journal-event/1.0` is
`artifact-storage-journal-event-1.0.json`. Requiring another storage contract
or changing one of these meanings requires a new RFC or contract version; an
implementation cannot satisfy this version with an unnamed private record.

These are operational contracts. None is a replacement, extension, or new
interpretation of `artifact/1.0`. Their exact records are stored in a durable
Storage Journal and catalog, not in Chronicle. Accepted research state may
refer to a verified content identity through an explicitly versioned future
canonical contract, but storage records themselves have no scientific
authority.

The Phase 3 local reference runtime uses one built-in local backend whose
entire managed namespace is `.benchwork/storage/`. Its versioned internal
layout contains only coordinator-owned journal, state-cache, Blob, staging,
quarantine, lock, and recovery material. A path under that namespace is never
a v1 Artifact materialization, and a backend locator or backend URI is never
made acceptable by spelling it as a project-relative path.

After this RFC's implementation is enabled, Athanor rejects every new
`artifact/1.0` registration whose normalized project-root-relative lexical
location or resolved target is equal to or below `.benchwork/storage/`. It
still verifies ordinary root-contained v1 locations outside that namespace.
Before the managed store
is initialized in an upgraded project, migration preflight must find every
already accepted v1 Artifact whose recorded URI aliases the reserved
namespace, verify its existing bytes and Receipt, copy the bytes into a normal
managed Replica, and append a legacy-protection record. The recorded v1 path
remains in place as an immutable compatibility anchor, is excluded from
backend key allocation, and can never be selected by GC or an authorized
storage disposition. An unresolved, corrupt, or internal-layout-colliding
legacy reference blocks managed-store activation rather than being moved,
deleted, or guessed.

The local reference runtime retains committed and quarantined Attempt bytes by
default and exposes only explicit, auditable cleanup. A production local
Artifact Registry, automated policy retention, remote Replica adapters, and
dataset storage policy are Phase 4 capabilities.

## Terminology

| Term | Meaning |
| --- | --- |
| **Artifact** | A logical, canonical research object accepted by Athanor. In the existing contract it is an immutable `artifact/1.0` projection with an `AR-` ID and Chronicle Receipt. |
| **Blob** | One finite sequence of bytes whose primary identity is a byte-level Sigil. A Blob has no Program, scientific kind, producer, or acceptance status by itself. |
| **Replica** | One immutable physical realization of a Blob in one declared backend namespace, bound to backend object identity and generation evidence. |
| **Staging object** | Incomplete, uncommitted bytes in a transfer-scoped namespace. It is never an eligible Blob or Replica. |
| **Transfer** | One bounded operational attempt to ingest, copy, verify, export, or materialize bytes. Retrying creates a new transfer-attempt identity. |
| **Import** | A verified transfer from an external, local, or Attempt-scoped source into storage. Import is not Artifact registration. |
| **Export** | A verified transfer from a selected Blob to an authorized destination. Export is not scientific acceptance or Patch promotion. |
| **Materialization** | A bounded export of exact Blob bytes into a Sanctum, Crucible, or project-relative destination for a declared purpose. It is an operational view, not a new Replica unless explicitly committed as one. |
| **Storage Journal** | Durable operational history for transfers, Replica observations, provenance, retention, quarantine, and garbage collection. It has no canonical research authority. |
| **Quarantine** | An isolated operational namespace and state for partial, corrupt, mismatched, stale, unsafe, or unverifiable bytes. |
| **Backend profile** | A closed declaration of one storage adapter's identity, version, consistency, durability, verification, conditional-operation, and deletion capabilities. |
| **Locator** | Opaque backend-specific information used by the storage coordinator to reach a Replica. It is not a content identity and is not exposed as general Worker filesystem or object-store authority. |
| **Legacy v1 protection** | Operational hold binding an already accepted v1 Artifact, Receipt, recorded URI, verified bytes, and managed copy so reservation of `.benchwork/storage/` cannot invalidate or delete the historical path. |

An unavailable Blob is still a meaningful content identity recorded in
history, but Benchwork must not claim that its bytes are retrievable. A
canonical Artifact can likewise remain canonical while its recorded
`artifact/1.0` location is missing or corrupt; that is an integrity failure,
not permission to rewrite the Artifact.

## Content identity

### Byte identity

Phase 3 Blob identity uses the existing Sigil form:

```text
sha256:<64 lowercase hexadecimal characters>
```

The digest is SHA-256 over the exact logical byte sequence from offset zero
through the declared final byte. No path, file name, media type, timestamp,
POSIX mode, backend key, compression setting, encryption envelope, producer,
or provenance field participates in that identity. `size_bytes` is mandatory
verification metadata and must agree for every observation of a Sigil, but it
does not change the accepted `artifact/1.0` identity rule.

The Phase 3 profile accepts only `sha256`. Unknown algorithms and malformed or
non-canonical encodings fail closed. A future algorithm transition requires a
new versioned contract that records both identities and explicit migration
evidence; an implementation may not silently replace or reinterpret an
existing Sigil.

Content identity is calculated over logical bytes exposed to Benchwork.
Backend-transparent encryption, compression, or chunking may change the stored
representation, but the backend must reconstruct and stream the identical
logical bytes for verification. A Benchwork-visible compression, newline
normalization, archive rewrite, serialization change, or other transformation
creates a new Blob with a new Sigil and derived provenance.

All managed-store hashing is incremental and streaming. Import, export,
materialization, readback, recovery, and deep Doctor checks update SHA-256 and
an overflow-checked byte counter through a bounded buffer; they do not load an
unbounded payload into memory. A source hash and a destination readback hash
are independent passes. The Phase 3 resume profile recomputes SHA-256 over the
complete final logical byte stream before commit; serialized hash state,
per-chunk success, or a backend checksum cannot substitute for that final
pass. The same bounded streaming implementation is used when the upgraded
Athanor verifies a new v1 Artifact location, without changing what its Sigil
means.

### Files, trees, and structured content

A Blob is always bytes, never an implicitly walked directory. The storage
layer treats every structured payload, including a Patch Bundle, as opaque
bytes. It computes identity and enforces storage policy but does not interpret
patch operations, validate scientific meaning, or discover child references
by opening the Blob.

A directory or multi-file result may be represented by a higher-layer closed,
versioned bundle manifest whose canonical bytes are themselves a Blob. The
higher-layer validator, not the storage backend, validates each normalized
relative path, entry type, byte Sigil, and size and emits an explicit
`artifact-storage-reference-set/1.0` when member bytes require transitive
retention. That validator must reject:

- absolute, empty, dot, parent, duplicate, case-colliding, or
  normalization-colliding paths;
- symlinks, hard links, devices, sockets, FIFOs, and other special entries
  unless a later explicit bundle version defines safe semantics;
- undeclared entries and mutable external references; and
- unbounded file count, path length, per-entry size, or aggregate size.

An archive, manifest, or Patch Bundle remains opaque to the storage layer.
Storage verification does not make parsing or extraction safe. Parsing or
extraction requires a separate bounded validator and cannot change the source
Blob's identity. Missing, unknown, or invalid reference metadata fails GC
closed; the storage layer never guesses relationships from filenames, media
types, or digest-looking strings inside bytes.

### Equality, deduplication, and collision response

Equal verified Sigils identify the same Blob under the SHA-256 security
assumption. Deduplication may reuse an already verified Replica, but it must:

- compare the expected and observed byte count;
- preserve every distinct import and provenance observation;
- use conditional create rather than overwrite;
- verify the existing Replica before relying on it when its integrity is stale
  or uncertain; and
- never merge logical Artifact identity, Program membership, retention policy,
  or producer lineage merely because the bytes match.

Any evidence that one Sigil names different sizes or different byte sequences
is a suspected collision or integrity incident. Benchwork quarantines the new
input, marks all affected Replica claims ineligible, disables deduplication for
that identity, and requires explicit investigation. It never selects one
version by path, timestamp, or backend precedence.

## Operational and canonical boundary

Chronicle and the Storage Journal have different authorities.

| State | Classification | Transition authority |
| --- | --- | --- |
| `artifact/1.0`, its producer and input lineage, registration time, status, and Receipt | canonical research state | Athanor and Chronicle |
| Candidate Artifact descriptor, execution output, patch, captured log, or candidate Run attachment | Proposal | Worker or Executor until an explicit Athanor transition |
| Blob identity record, Replica state, backend locator, generation, availability, integrity observation, transfer, materialization, quarantine, retention, and GC state | durable operational storage state | Storage coordinator and verified backend operations |
| Staging bytes, temporary export files, transfer buffers, and Crucible paths | mutable or incomplete execution material | Enforcement backend and storage coordinator |

The Storage Journal is authoritative for what the storage subsystem attempted
and last verified. It is not authoritative for scientific meaning. Chronicle
is authoritative for which logical Artifacts were accepted, but it is not a
live Replica catalog.

A successful Job or Transfer may create a verified Blob and Replica. It does
not create an Artifact, Run, Assessment, Decision, or Seal. Conversely,
`artifact.registered` does not prove indefinite Replica availability,
replication count, backend durability, authenticity, absence of malware, or
scientific validity.

Storage state changes do not append Chronicle events merely because they
occurred. An explicit Athanor transition may later accept a bounded Proposal
that includes Blob, Transfer, Job, Attempt, and verification identities as
provenance. The corresponding Receipt records that scientific transition, not
ownership of the backend.

Failures are append-only history. A failed, cancelled, fenced, corrupt, or
quarantined transfer is never rewritten as successful. Replica deletion leaves
a tombstoned Replica record, Blob identity, transfer history, provenance, and
GC decision. Restoration creates a new Replica record or new verification
observation; it does not erase the outage or deletion.

## Managed namespace and Storage Journal

### Local layout

The built-in backend reserves this complete project-relative namespace:

```text
.benchwork/storage/
    format.json
    journal.frames
    journal-head.json
    state.json
    records/
    blobs/
    staging/
    quarantine/
    locks/
    recovery/
```

`format.json` pins the storage-format version, project identity, backend
profile and Sigil, and local conformance-suite Sigil. `journal.frames` is the
authority for operational history. `journal-head.json` and `state.json` are
replaceable verified caches. `records/` contains immutable, content-addressed
closed control records made durable before the Event that refers to them. The
remaining directories contain only material owned through journal records,
except for the one format-defined interrupted-tail marker and its immutable
evidence under `recovery/`; those have only the pre-journal authority defined
by the exact recovery protocol below. A name or digest-looking path in this
layout is not authoritative without a valid replayed record or that one
validated marker.

The only permitted pre-existing exceptions are historical v1 compatibility
anchors discovered and registered during migration preflight. They remain at
their recorded paths, are explicit permanent exclusions in State, and are
never treated as layout members or backend objects. An anchor that occupies or
aliases a required internal path blocks activation.

Only the storage coordinator writes this namespace. Workers, MCP callers,
Artifact producers, and native Host file operations receive neither raw paths
nor general read, write, list, or delete authority. A2 makes the complete
namespace unreachable. A1 does not claim hostile-code containment, but the
coordinator still withholds paths and handles and uses a constructed
environment.

The cross-journal canonical-reference gate is deliberately outside this
not-yet-initialized namespace at the fixed project-kernel path
`.benchwork/locks/canonical-reference.lock`. Athanor and storage open it
descriptor-relative with no-follow validation. Its external location lets the
same gate linearize v1 Artifact registration, migration preflight, store
activation, later canonical-reference commits, and GC before
`.benchwork/storage/` exists. It is not a Blob, Replica, control record, or
source of replay authority.

Initialization is a transaction. Read-only preflight first verifies Chronicle,
all v1 Artifact locations, namespace conflicts, free capacity, and the exact
legacy-protection plan. It then durably installs `format.json`, an empty
`journal.frames`, and the closed zero-count Head before any frame append. A
crash before all three exist leaves no initialized store and is restartable
only after repeating preflight; a mixed or conflicting set fails closed. The
first journal event creates an `INITIALIZING` store. Its `tail_recovery` is
null in the ordinary path; an interrupted first frame is repaired only by the
empty-prefix `storage.initialized` marker branch below, which repeats preflight
and records the non-null `TailRecovery`. Each accepted historical
v1 alias is copied through an internal Transfer whose closed purpose is
`LEGACY_V1_PROTECTION`. This is the only Transfer purpose legal while
`INITIALIZING` and it uses the ordinary reservation, staging, commit-intent,
readback, and recovery protocol. The alias then receives a
`legacy_v1.protection_registered` event after its compatibility anchor and
managed copy verify. `storage.activation_completed` changes the store to
`ACTIVE` only when every required protection exists. A crash or failure leaves
the store unable to import, materialize, delete, or run non-migration
Transfers until recovery completes; it never treats a partially initialized
layout as active.

Immediately after `storage.initialized`, initialization registers exactly two
immutable policies before any protection Transfer. The first is the
migration-protection policy. Its scope is the project, minimum Replica count
is one, retain-until is null, `automatic_gc_allowed` is false, and its system
authorization forbids both anchor disposition and managed-copy GC. Every
`LegacyExclusion.policy_id` cites it.

The second is the neutral execution-root hold carrier. Its exact
`artifact-retention-policy/1.0` fields are:

```text
policy_id = SP-EXECUTION-ROOT-HOLD-V1
scope = {kind: PROJECT, project_id: <this Storage State project_id>}
minimum_replica_count = 0
required_backends = []
required_failure_domains = []
maximum_integrity_age_seconds = null
deletion_grace_seconds = 0
retain_until = null
automatic_gc_allowed = true
authorization_sigil =
  Sigil(["execution-root-hold-policy-authorization/1.0",
         project_id,
         storage_format_version,
         backend_profile_sigil,
         conformance_suite_sigil])
```

`registered_at` is fixed by its one registration and `record_sigil` is its
ordinary self-Sigil. The policy itself imposes no minimum physical retention;
an `ACTIVE` execution hold supplies protection. These two exact registrations
are the only `retention.policy_registered` branches legal in
`INITIALIZING`. Activation requires both records to replay validly, and a
missing, changed, or project-mismatched execution policy blocks every
non-empty RFC-0012 ESM hold.

The upgraded `artifact.registered` transition acquires this outer gate before
validating its v1 location and retains it through its Chronicle commit.
Initialization acquires the gate before its first Chronicle replay and retains
it until `storage.activation_completed` is durable or activation aborts. It
replays Chronicle again under the gate immediately before installing
`format.json`; the discovered historical-alias set and Head must equal the
preflight plan. A concurrent new registration therefore commits entirely
before that snapshot and is protected, or waits until the
reserved-namespace rule is active. Upgrade requires exclusive use of a
gate-aware Athanor build; detecting an incompatible or ungated writer blocks
activation rather than racing it.

### Journal contracts and identities

The journal family consists of:

- `artifact-storage-journal-event/1.0`, a closed hash-chained event;
- `artifact-storage-journal-head/1.0`, a replaceable cache of journal ID,
  event count, last sequence, last event Sigil, and projected state Sigil;
  and
- `artifact-storage-state/1.0`, the deterministic replay projection.

All three are closed JSON Schemas with `additionalProperties: false`, bounded
strings and collections, canonical JSON encoding, and lowercase SHA-256
Sigils. They reject duplicate object keys, non-finite numbers, out-of-range
integers, unknown enum values, and unknown Schema versions.

Operational identifiers are opaque. The Phase 3 patterns are `SJ-` for a
Storage Journal, `SE-` for a journal event, `ST-` for a Transfer request,
`SA-` for a transfer attempt, `SR-` for a Replica, `SM-` for a
Materialization, `SQ-` for a Quarantine record, `SP-` for a retention policy,
`SH-` for a hold, `RS-` for a reference set, `RI-` for a canonical-reference
intent, `SG-` for a GC plan, and `SD-` for a disposition. They are never
derived from a path, PID, time, queue position, or scientific Run ID. Blob
identity remains its byte Sigil rather than gaining an arbitrary operational
ID. The imported RFC-0012 `ESM-ID` uses the same bounds and the `ESM-`
prefix; its deterministic derivation is owned by
`execution-storage-root-manifest/1.0`.

Every event has exactly this common envelope plus the selected closed payload
branch:

- `schema_version`, `journal_id`, `event_id`, one-based contiguous `sequence`, and
  closed `event_type`;
- `coordinator_id` and monotonically increasing local `epoch`;
- `recorded_at` and nullable bounded `observed_at`;
- sorted `entity_revisions`, each containing entity type and ID, exact
  preceding revision or null, and exact next revision;
- nullable `causation_event_id` and `idempotency_key_sigil`;
- sorted closed `quota_effects`, present and empty when the event has no quota
  consequence;
- one closed type-specific `payload`;
- `previous_event_sigil`, with null only at sequence one; and
- `event_sigil` over canonical JSON with that field omitted.

`recorded_at` is non-decreasing protocol time. On a detected rollback, the
clock-uncertain event retains the prior protocol time in its envelope and
places both observed clock values in its payload; it never backdates the
chain.

The Head contains exactly its Schema version, journal ID, storage-format
version, event count, last sequence, last event Sigil,
`committed_byte_length`, current epoch, state Sigil, and update time. For an
initialized journal, `event_count == last_sequence`; the only empty Head is the
pre-initialization value with zero count, zero sequence, zero committed byte
length, and null last-event and state Sigils. `committed_byte_length` is the
exclusive byte offset immediately after the last complete committed frame.
The `state_sigil` identifies the canonical bytes of the matching State. Where
this RFC names a Head Sigil, it means SHA-256 over the complete canonical Head
bytes; it is an observation identity, not an added Head field.
Head journal ID is `SJ-ID`, storage-format version is `Opaque`, counts,
sequence, committed length, and epoch are `U63`, event and State Sigils are
`Sigil|null` under the empty-Head rule, and update time is `Timestamp`.

The State contains exactly its Schema version, journal ID, storage-format version,
project identity, backend-profile identity and Sigil, conformance-profile
identity and suite Sigil, store status, active recovery identity and origin
status, clock status and anchor, current epoch, applied event count, last event
Sigil, and these sorted closed projection
collections:
`recoveries`, `blobs`, `replicas`, `transfer_requests`, `transfer_attempts`,
`materializations`, `quarantines`, `provenance`, `retention_policies`,
`holds`, `reference_sets`, `legacy_v1_protections`, `gc_plans`,
`canonical_reference_intents`, `dispositions`, `quota_reservations`,
`open_intents`, and `incidents`. It also contains derived availability and
quota counters and its own `state_sigil` computed with that field omitted.
Every projection carries its identity, revision, state, and the minimal typed
relationships required to validate it. Collections are sorted by identity;
replay cannot depend on filesystem enumeration order.
State journal ID is `SJ-ID`; storage format, project, backend-profile and
conformance-profile IDs are `Opaque`; their suite/profile identities are
`Sigil`; active recovery ID is `Opaque|null`; recovery origin is
`INITIALIZING|ACTIVE|null`; clock status is `TRUSTED|UNCERTAIN`; clock anchor
is `ClockRef`; epoch and applied count are `U63`; last-event Sigil is
`Sigil|null`; and `state_sigil` is `Sigil`.

Referenced immutable control records and byte payloads are durable before the
event that makes them visible. One event may atomically update related
projections, such as committing a Transfer while creating or selecting its
Blob and Replica. Replay accepts all those revisions or none.

### Closed Schema construction rules

The prose names below are normative JSON Schema aliases. `Sigil` is a string
matching `^sha256:[a-f0-9]{64}$`. `U63` is an integer in
`0..9223372036854775807`. `PositiveU63` starts at one. `U64` is an integer
in `0..18446744073709551615` and is used only where an imported RFC-0012 or
RFC-0014 counter requires that exact domain; parsers that cannot preserve it
exactly fail closed. `Timestamp` is a
UTC RFC 3339 string ending in `Z`, with no leap second and at most six
fractional digits. `Opaque` is printable UTF-8, length `1..256`, without NUL
or control characters. An operational ID is ASCII, length `3..128`, begins
with its assigned prefix, and otherwise matches
`[A-Za-z0-9][A-Za-z0-9._:-]*`. Collections have at most 4096 members unless
their owning policy declares a smaller bound. Every set is encoded as a
duplicate-free array in ascending Unicode-code-point order; tuple sets use
lexicographic field order stated here. Nullable fields are present with JSON
`null`; omission is not an alternative.

`VerificationMethod` is the closed string enum
`FULL_READBACK_SHA256` or `CONFORMANCE_END_TO_END`.
`ProvenanceRelation` is the closed string enum `CAPTURED`, `IMPORTED`,
`COPIED`, `DERIVED`, `EXPORTED`, `MATERIALIZED`, `VERIFIED`, or `DELETED`.

These reusable objects are exact and closed:

| Alias | Exact fields |
| --- | --- |
| `ControlRef` | `schema_version: Opaque`, `record_id: Opaque`, `record_sigil: Sigil` |
| `EventRef` | `journal_id: SJ-ID`, `event_id: SE-ID`, `sequence: PositiveU63`, `event_sigil: Sigil` |
| `EntityRevision` | `entity_type: EntityType`, `entity_id: Opaque`, `previous_revision: U63\|null`, `next_revision: PositiveU63` |
| `ChronicleHeadRef` | Phase 3-admissible `chronicle-head/1.1` value with the exact three-field closed shape `schema_version: "chronicle-head/1.1"`, `event_count: U63`, `terminal_receipt_sigil: Sigil\|null`; the existing Chronicle Schema has no upper bound on its integer, so `U63` is an additional RFC-0013 admission bound rather than a claim that the two integer domains are identical |
| `ChronicleCommitRef` | `event_id: Opaque`, `event_body_sigil: Sigil`, `receipt_id: Opaque`, `receipt_sigil: Sigil`, `head: ChronicleHeadRef` |
| `ExternalEventRef` | `protocol_id: Opaque`, `protocol_version: Opaque`, `journal_id: Opaque`, `event_id: Opaque`, `sequence: U64` in `1..18446744073709551615`, `event_type: Opaque`, `event_sigil: Sigil` |
| `CanonicalAbortAuthority` | `kind: "HEAD_SUPERSEDED_WITHOUT_BOUND_EVENT"`, `reference_intent_id: RI-ID`, `reference_intent_record_sigil: Sigil`, `transition_request_id: Opaque`, `transition_request_sigil: Sigil`, `expected_chronicle_head: ChronicleHeadRef`, `verified_chronicle_head: ChronicleHeadRef`, `absence_evidence_sigil: Sigil`, `authority_sigil: Sigil` |
| `Reason` | `code: ReasonCode`, `evidence_sigils: [Sigil]` |
| `QuotaClaim` | `quota_class: QuotaClass`, `byte_count: U63`, `object_count: U63`, `inode_count: U63`, `stream_count: U63`, `journal_bytes: U63`, `control_record_bytes: U63` |
| `OperationCapacityPlan` | `allowed_event_types: [StorageEventType]`, `max_event_frame_count: PositiveU63`, `max_control_record_count: U63`, `max_recovery_evidence_count: U63`, `max_event_frame_bytes: PositiveU63`, `max_control_record_bytes: PositiveU63`, `max_recovery_evidence_bytes: PositiveU63` |
| `ReservationRef` | `reservation_id: Opaque`, `claims: [QuotaClaim]`, `capacity_plan: OperationCapacityPlan`, `expires_at: Timestamp\|null`, `created_clock: ClockRef`, `remaining_micros_at_creation: U63\|null` |
| `BackendObjectRef` | `backend_id: Opaque`, `object_identity_sigil: Sigil`, `locator_sigil: Sigil`, `generation: Opaque`, `size_bytes: U63`, `blob_sigil: Sigil\|null` |
| `ExecutionFenceRef` | `execution_journal_id: Opaque`, `executor_epoch: U64`, `job_id: Opaque`, `attempt_id: Opaque`, `lease_id: Opaque`, `fencing_generation: U64`, `execution_event_sigil: Sigil`, `job_fence_floor: U64`, `tombstone_present: boolean` |
| `VerificationRef` | `method: VerificationMethod`, `evidence_sigil: Sigil`, `verified_at: Timestamp`, `next_due_at: Timestamp\|null` |
| `ClockRef` | `utc: Timestamp`, `monotonic_anchor_id: Opaque`, `monotonic_ticks: U63`, `monotonic_frequency_hz: PositiveU63`, `uncertainty_micros: U63`, `observation_sigil: Sigil` |
| `QuotaSnapshot` | `quota_class: QuotaClass`, `dimension: QuotaDimension`, `limit: U63`, `used: U63`, `reserved: U63`, `pressure_state: "CLEAR"\|"PRESSURED"` |
| `QuotaEffect` | `INITIALIZE {kind, snapshot: QuotaSnapshot}`; `RESERVE {kind, reservation: ReservationRef, owner_kind: QuotaOwnerKind, owner_id: Opaque, purpose: QuotaPurpose}`; `SETTLE {kind, reservation_id: Opaque, state_after: "RETAINED"\|"SETTLED", consumed_claims: [QuotaClaim], released_claims: [QuotaClaim], remaining_claims: [QuotaClaim], usage_additions: [QuotaClaim], retained_for_event_types: [StorageEventType]}`; `USAGE_REMOVED {kind, removal: QuotaClaim, owner_kind: QuotaOwnerKind, owner_id: Opaque}`; or `PRESSURE {kind, from_state: "CLEAR"\|"PRESSURED", to_state: "CLEAR"\|"PRESSURED", snapshot: QuotaSnapshot}` |
| `TailRecovery` | `prior_head_sigil: Sigil`, `old_committed_byte_length: U63`, `last_complete_byte_length: U63`, `discarded_suffix_size: PositiveU63`, `discarded_suffix_sigil: Sigil`, `evidence_record_sigil: Sigil` |

`HoldReleaseAuthority` is the exact closed union:

```text
EXECUTION_ROOT:
  kind = EXECUTION_ROOT
  authorization: ControlRef

PATCH_OPERATIONAL_ROOT:
  kind = PATCH_OPERATIONAL_ROOT
  protocol_id = benchwork.patch-promotion
  protocol_version = 1.0
  operational_journal_id: Opaque
  operational_root_id: Opaque
  operational_root_sigil: Sigil
  operational_root_plan: ControlRef
  reference_set: ReferenceSetRef
  hold_set_event: EventRef
  activation_event: ExternalEventRef
  inactivation_event: ExternalEventRef
  release_condition:
    NON_PARTIAL_OUTCOME_OBSERVED |
    RESOLVED_RECOVERY_OBSERVED |
    ABANDONED_WITH_DISPOSITION |
    JOURNAL_RECOVERY_COMPLETED
  terminal_authority: ControlRef
  release_evidence: ControlRef
  validator_id = benchwork.patch-operational-root-release
  validator_version = 1.1
  validator_sigil: Sigil
  authority_sigil: Sigil
```

The execution branch's `ControlRef` must name
`execution-root-hold-release-authorization/1.0`; its record ID and Sigil are
validated below. The patch branch's `authority_sigil` is the self-Sigil over
every other branch member. Its external Event refs all have
`protocol_id: benchwork.patch-promotion` and `protocol_version: 1.0`; RFC-0014
narrows their IDs, event types, and release-condition matrix.
`operational_root_plan` must name
`patch-operational-root-plan/1.0`; `release_evidence` must name
`patch-operational-root-release-evidence/1.0`. Both are complete immutable
records resolved by ID and Sigil, never arbitrary audit pointers. No third
branch or untyped authority map is admitted.

`QuotaClass` is exactly `JOURNAL`, `CONTROL_RECORD`, `STAGING`,
`QUARANTINE`, `COMMITTED`, `MATERIALIZATION`, `STREAM`, or `INODE`.
`QuotaDimension` is exactly `BYTE`, `OBJECT`, `INODE`, `STREAM`,
`JOURNAL_BYTE`, or `CONTROL_RECORD_BYTE`. The only legal
class/dimension pairs are `JOURNAL/JOURNAL_BYTE`,
`CONTROL_RECORD/CONTROL_RECORD_BYTE`, `STREAM/STREAM`, `INODE/INODE`, and
`BYTE` or `OBJECT` for each of `STAGING`, `QUARANTINE`, `COMMITTED`, and
`MATERIALIZATION`. A `QuotaClaim` has at least one non-zero component and has
non-zero values only in the dimensions legal for its class. Claim arrays are
unique, contain at most one member for each quota class, and are sorted by
quota class in ascending Unicode-code-point order. A quota-counter projection
identity is exactly `quota-counter:<QuotaClass>:<QuotaDimension>`. The
dimension is mandatory even for a class that has only one legal dimension; a
class-only quota entity ID is invalid.

`QuotaOwnerKind` is exactly `TRANSFER_ATTEMPT`, `MATERIALIZATION`,
`QUARANTINE`, `GC_TARGET`, `DISPOSITION`, `CANONICAL_REFERENCE`,
`LEGACY_PROTECTION`, or `RECOVERY`. `QuotaPurpose` is exactly
`PAYLOAD_LIFECYCLE`, `TERMINAL_OUTCOME`, `QUARANTINE_MOVE`,
`DELETION_OUTCOME`, `CANONICAL_PIN_LIFECYCLE`, or `RECOVERY_EVIDENCE`.
`StorageEventType` is the exact event enum below. `quota_effects` are sorted by
`(kind ordinal, reservation_id or snapshot class/dimension or removal
class/dimension)`, where the kind order is `INITIALIZE`, `RESERVE`, `SETTLE`,
`USAGE_REMOVED`, `PRESSURE` and strings compare by Unicode code point. No
event may address the same reservation or counter twice.

An `OperationCapacityPlan.allowed_event_types` array is non-empty, sorted in
Storage-event enum order, and contains only events in the owning operation's
closed capacity-source row below. Its three per-item maxima use the same
`56..8388664`, `1..8388664`, and `1..8388664` bounds as the corresponding
system maxima. Checked, overflow-free arithmetic defines:

```text
required_journal_bytes =
    max_event_frame_count * max_event_frame_bytes
required_control_bytes =
    max_control_record_count * max_control_record_bytes
  + max_recovery_evidence_count * max_recovery_evidence_bytes
```

The Reservation's total `JOURNAL/JOURNAL_BYTE` claim is at least
`required_journal_bytes`, and its total
`CONTROL_RECORD/CONTROL_RECORD_BYTE` claim is at least
`required_control_bytes`. Each maximum is immutable for the Reservation. An
event or record whose canonical durable length exceeds its per-item maximum, or
an operation that reaches any count maximum before a legal terminal outcome,
fails before another side effect and retains its existing Reservation for
Recovery. `remaining_micros_at_creation` is null exactly when `expires_at` is
null; otherwise it is the non-negative microsecond difference from
`created_clock.utc` to `expires_at`, rejected on `U63` overflow. It is creation
evidence, not a monotonic value reusable after restart.

A `RESERVE` adds every claim to the matching `reserved` counters and is legal
only when every resulting counter is within its limit. A `SETTLE` partitions
the prior remaining claims component-wise into `consumed_claims`,
`released_claims`, and `remaining_claims`; it cannot create or reclassify a
claim. `usage_additions` equals `consumed_claims` byte-for-byte and moves
those amounts from `reserved` to `used`. `released_claims` only subtract from
`reserved`. `RETAINED` requires non-empty remaining claims and a non-empty
exact future-event set; `SETTLED` requires both to be empty. A later
`SETTLE` on a retained reservation is legal only for an event in that set.
`USAGE_REMOVED` is legal only for exact amounts already charged as used and
physically removed by the same authorized disposition, materialization
cleanup, or GC event; it can never create, discover, or reclassify usage.
A `USAGE_REMOVED.removal` has exactly one non-zero component, so removal of a
byte-and-object allocation uses two effects ordered by class/dimension and
produces two distinct quota-counter revisions.
A `PRESSURE` snapshot is the complete counter after the transition, and its
`pressure_state` equals `to_state`.

The remaining shared `$defs` are also exact and closed:

| Alias | Exact shape |
| --- | --- |
| `BlobRef` | `blob_sigil: Sigil`, `size_bytes: U63` |
| `BackendRef` | `backend_id: Opaque`, `backend_profile_version: Opaque`, `backend_profile_sigil: Sigil` |
| `TransferBounds` | `max_bytes: U63`, `max_duration_millis: U63`, `max_file_count: U63\|null`, `max_chunk_count: U63`, `buffer_bytes: PositiveU63` |
| `ExecutionContext` | `NONE {kind: "NONE"}`; `ATTEMPT {kind: "ATTEMPT", execution_journal_id: Opaque, executor_epoch: U64, job_id: Opaque, attempt_id: Opaque}`; or `LEASED {kind: "LEASED", execution_journal_id: Opaque, executor_epoch: U64, job_id: Opaque, attempt_id: Opaque, lease_id: Opaque, worker_id: Opaque, worker_session_id: Opaque, fence: ExecutionFenceRef}` |
| `SourceDescriptor` | `LOCAL_FILE {kind: "LOCAL_FILE", authorization_scope_sigil: Sigil, lexical_identity_sigil: Sigil, resolved_file_identity_sigil: Sigil}`; `REPLICA {kind: "REPLICA", blob: BlobRef, replica_id: SR-ID, verification_sigil: Sigil}`; `ATTEMPT_OUTPUT {kind: "ATTEMPT_OUTPUT", execution: ExecutionContext, output_handle_id: Opaque}`; `EXTERNAL {kind: "EXTERNAL", source_class: Opaque, sanitized_identity_sigil: Sigil, authorization_sigil: Sigil}`; `STAGING {kind: "STAGING", transfer_attempt_id: SA-ID, object: BackendObjectRef}`; or `LEGACY_ARTIFACT {kind: "LEGACY_ARTIFACT", artifact_id: Opaque, receipt_sigil: Sigil, location_sigil: Sigil}` |
| `DestinationDescriptor` | `MANAGED_BACKEND {kind: "MANAGED_BACKEND", backend: BackendRef}`; `EXPORT {kind: "EXPORT", destination_class: Opaque, destination_identity_sigil: Sigil, authorization_sigil: Sigil}`; or `MATERIALIZATION {kind: "MATERIALIZATION", materialization_id: SM-ID, destination_class: Opaque, destination_identity_sigil: Sigil}` |
| `TransformationRef` | `NONE {kind: "NONE"}` or `DERIVED {kind: "DERIVED", contract_id: Opaque, contract_version: Opaque, implementation_sigil: Sigil, parameters_sigil: Sigil, input_blobs: [BlobRef]}` |
| `TimeSet` | `observed_at: Timestamp\|null`, `started_at: Timestamp`, `committed_at: Timestamp\|null`, `verified_at: Timestamp\|null`, `terminal_at: Timestamp` |
| `CleanupResult` | `state: NOT_REQUIRED\|PENDING\|CLEANED\|FAILED`, `evidence_sigil: Sigil\|null`, `reason: Reason\|null` |
| `TransferCommitIntent` | `intent_id: Opaque`, `provisional_replica_id: SR-ID`, `staging_object: BackendObjectRef`, `target_object: BackendObjectRef`, `computed_blob: BlobRef`, `execution_fence: ExecutionFenceRef\|null`, `reservation: ReservationRef`, `recorded_clock: ClockRef` |
| `ResidualStagingCleanup` | `state: NOT_REQUIRED\|PENDING\|CLEANED\|FAILED\|HELD_FOR_DISPOSITION`, `staging_object: BackendObjectRef\|null`, `evidence_sigil: Sigil\|null`, `reason: Reason\|null` |
| `MaterializationCommitIntent` | `intent_id: Opaque`, `staging_object: BackendObjectRef`, `destination_object: BackendObjectRef`, `expected_blob: BlobRef`, `destination_identity_sigil: Sigil`, `execution_fence: ExecutionFenceRef\|null`, `reservation: ReservationRef`, `recorded_clock: ClockRef` |
| `TransferRef` | `transfer_id: ST-ID`, `transfer_attempt_id: SA-ID`, `request_record_sigil: Sigil`, `attempt_record_sigil: Sigil`, `terminal_event: EventRef` |
| `ExpectedSizeOrBound` | `EXACT {kind, size_bytes: U63}` or `UPPER_BOUND {kind, max_size_bytes: U63}` |
| `PolicyScope` | `PROJECT {kind: "PROJECT", project_id: Opaque}`; `PROGRAM {kind: "PROGRAM", program_id: Opaque}`; `BLOB {kind: "BLOB", blob_sigil: Sigil}`; or `REFERENCE_SET {kind: "REFERENCE_SET", reference_set_id: RS-ID, reference_set_sigil: Sigil}` |
| `ReferenceSetRef` | `reference_set_id: RS-ID`, `reference_set_sigil: Sigil` |
| `ReferenceSource` | `kind: "CANONICAL_OBJECT"\|"OPERATIONAL_CONTROL_RECORD"\|"BLOB_MANIFEST"`, `identity: Opaque`, `schema_version: Opaque`, `sigil: Sigil` |
| `ReferenceExtractor` | `extractor_id: Opaque`, `extractor_version: Opaque`, `extractor_sigil: Sigil` |
| `ReferenceValidation` | `validator_id: Opaque`, `validator_version: Opaque`, `validator_sigil: Sigil`, `source_validation_sigil: Sigil`, `evidence_sigils: [Sigil]` |
| `ReferenceEdge` | `relationship: ReferenceRelationship`, `target_kind: ReferenceTargetKind`, `target_identity: Opaque`, `target_sigil: Sigil` |
| `LegacyExclusion` | `anchor_disposition: "PERMANENTLY_EXCLUDED"`, `managed_copy_gc: "PERMANENTLY_PROTECTED"`, `policy_id: SP-ID`, `authorization_sigil: Sigil` |
| `BackendIsolation` | `scope: "SINGLE_PROJECT"\|"SINGLE_TENANT_PROJECT"`, `namespace_enforcement: "DESCRIPTOR_RELATIVE_NOFOLLOW"\|"ADAPTER_SCOPED"`, `worker_access: "NONE"`, `worker_credentials_exposed: false` |
| `SystemReserveLimit` | `reserve_class: SystemReserveClass`, `max_event_frame_count: PositiveU63`, `max_control_record_count: U63`, `max_recovery_evidence_count: U63`, `max_event_frame_bytes: PositiveU63`, `max_control_record_bytes: PositiveU63`, `max_recovery_evidence_bytes: PositiveU63` |
| `BackendLimits` | `max_object_bytes: U63`, `transfer_bounds: TransferBounds`, `max_concurrent_streams: U63`, `max_inventory_entries: U63`, `max_tail_recovery_retries: PositiveU63`, `system_reserve_limits: [SystemReserveLimit]`, `system_journal_reserve_bytes: PositiveU63`, `system_control_record_reserve_bytes: PositiveU63`, `system_recovery_reserve_bytes: PositiveU63` |
| `BackendConsistency` | `read_after_write: "STRONG"\|"EVENTUAL"`, `list_consistency: "STRONG"\|"EVENTUAL"`, `atomic_visibility: boolean`, `immutable_generation: boolean`, `exact_generation_reads: boolean` |
| `BackendDurability` | `commit_semantics: "FSYNC_FILE_AND_PARENT"\|"REMOTE_DURABLE_ACK"`, `logical_readback: boolean`, `transparent_encryption: boolean`, `transparent_compression: boolean` |
| `BackendRangeResume` | `range_reads: boolean`, `resumable_stage_writes: boolean`, `resume_binding: "UNSUPPORTED"\|"GENERATION_OFFSET_PREFIX_SIGIL"` |
| `BackendConditionalOperations` | `conditional_create: boolean`, `no_overwrite_finalize: boolean`, `exact_generation_stat: boolean`, `exact_generation_delete: boolean` |
| `BackendDeletionCapabilities` | `exact_generation_delete: boolean`, `wildcard_delete: false`, `retention_lock: "NONE"\|"ENFORCED"`, `verification: "POST_DELETE_STAT"\|"RECEIPT_AND_RECONCILIATION"` |
| `BackendFencing` | `mode: "COORDINATOR_PRECOMMIT"\|"BACKEND_PUBLIC_FENCE"`, `attempt_staging_isolated: boolean`, `executor_epoch_checked: boolean`, `job_fence_floor_checked: boolean`, `tombstone_checked: boolean` |
| `BackendConformance` | `profile_id: "LOCAL-PHASE3/1.0"\|"PORTABLE-PHASE4/1.0"`, `suite_version: Opaque`, `suite_sigil: Sigil`, `host_platform_sigil: Sigil`, `evidence_sigil: Sigil` |
| `TraversalBounds` | `max_roots`, `max_nodes`, `max_edges`, `max_depth`, `max_control_record_bytes`, `max_wall_millis`, all `U63` |
| `ExecutionStorageRoot` | `root_kind: "JOB_INPUT"\|"ATTEMPT_INPUT"\|"ATTEMPT_OUTPUT"`, `job_id: Opaque`, `attempt_id: Opaque\|null`, `storage_root_manifest_id: ESM-ID`, `storage_root_manifest_sigil: Sigil`, `reference_set_id: RS-ID`, `reference_set_sigil: Sigil`, `hold_id: SH-ID`, `hold_set_event: EventRef` |
| `ExecutionRootSnapshot` | `execution_journal_id: Opaque`, `execution_event_count: U63`, `execution_last_event_sigil: Sigil\|null`, `roots: [ExecutionStorageRoot]`, `root_set_sigil: Sigil` |
| `GCRootSnapshot` | `chronicle_head: ChronicleHeadRef`, `storage_event: EventRef`, `execution_roots: ExecutionRootSnapshot`, `hold_set_sigil: Sigil`, `legacy_protection_set_sigil: Sigil`, `reference_intent_set_sigil: Sigil`, `reference_set_sigils: [Sigil]`, `policy_set_sigil: Sigil` |
| `ClosureProof` | `root_set_sigil: Sigil`, `extractor_suite_sigil: Sigil`, `bounds: TraversalBounds`, `visited_node_count: U63`, `visited_edge_count: U63`, `cycle_summary_sigil: Sigil`, `reachable_blob_sigils: [Sigil]`, `reachable_replica_ids: [SR-ID]`, `proof_sigil: Sigil` |
| `GCTarget` | `target_id: Opaque`, `replica_id: SR-ID`, `blob: BlobRef`, `backend_object: BackendObjectRef`, `reason_code: ReasonCode`, `expected_remaining_replica_ids: [SR-ID]` |
| `GCTargetState` | `target_id: Opaque`, `state: "PLANNED"\|"SKIPPED"\|"DELETING"\|"DELETED"\|"FAILED"`, `deletion_intent_id: Opaque\|null`, `root_revalidation_sigil: Sigil\|null`, `outcome_reservation: ReservationRef\|null`, `deletion_evidence_sigil: Sigil\|null`, `terminal_reason: Reason\|null`, `last_event_sigil: Sigil` |
| `OpenIntentProjection` | the six exact discriminated branches defined below, with no common untyped fallback |
| `DoctorSubjectKind` | `"JOURNAL"\|"STATE"\|"BACKEND_OBJECT"\|"REPLICA"\|"LEGACY_PROTECTION"\|"QUARANTINE"\|"QUOTA"\|"REFERENCE_SET"\|"HOLD"\|"OPEN_INTENT"\|"RECOVERY_EVIDENCE"` |
| `IncidentSubjectKind` | `"BLOB"\|"REPLICA"\|"TRANSFER_ATTEMPT"\|"MATERIALIZATION"\|"QUARANTINE"\|"BACKEND_OBJECT"\|"JOURNAL"\|"LEGACY_PROTECTION"` |
| `CheckResult` | `check_id: Opaque`, `status: "PASS"\|"WARN"\|"FAIL"\|"INCOMPLETE"`, `subject_kind: DoctorSubjectKind`, `subject_id: Opaque`, `evidence_sigils: [Sigil]`, `reason: Reason\|null` |
| `BackendInventoryEntry` | `backend_object: BackendObjectRef`, `owner_kind: "REPLICA"\|"TRANSFER_ATTEMPT"\|"MATERIALIZATION"\|"QUARANTINE"\|"UNJOURNALED"`, `owner_id: Opaque\|null`, `status: "OWNED"\|"UNJOURNALED"\|"CONFLICTING"\|"INACCESSIBLE"`, `evidence_sigils: [Sigil]` |
| `DoctorBounds` | `max_inventory_entries: U63`, `max_control_records: U63`, `max_rehash_bytes: U63`, `max_wall_millis: U63`, `inventory_truncated: boolean`, `rehash_truncated: boolean` |

Every union uses its explicitly named `kind`, `state`, `intent_kind`, or
enclosing event discriminator as a required constant discriminator. Fields shown
without an explicit type in a compact field-set table receive their type only
from an explicit binding paragraph in this RFC. A field with neither an
inline type nor one such binding is a Schema defect; it does not default to
`Opaque`. Only a field explicitly written `: Opaque` uses that alias. No
branch admits an untyped parameter map.

`EntityType` is exactly the entity-type enum in the revision section below.
`ReferenceTargetKind` is exactly `BLOB`, `REPLICA`, `REFERENCE_SET`,
`CANONICAL_OBJECT`, or `OPERATIONAL_CONTROL_RECORD`.
`ReferenceRelationship` is exactly:

```text
BUNDLE_RETAINS_MEMBER
CANONICAL_BINDS_BLOB
CANONICAL_RETAINS_OBJECT
CONTROL_RETAINS_BLOB
CONTROL_RETAINS_CONTROL
HOLD_PROTECTS_BLOB
JOB_REQUIRES_BLOB
PATCH_RETAINS_BASE
PATCH_RETAINS_POSTIMAGE
REFERENCE_SET_RETAINS_SET
TRANSFER_PINS_REPLICA
```

The relationship/source/target matrix is closed:

| Relationship | Exact `source.kind` | Exact legal `target_kind` |
| --- | --- | --- |
| `BUNDLE_RETAINS_MEMBER` | `BLOB_MANIFEST` | `BLOB` |
| `CANONICAL_BINDS_BLOB` | `CANONICAL_OBJECT` | `BLOB` |
| `CANONICAL_RETAINS_OBJECT` | `CANONICAL_OBJECT` | `CANONICAL_OBJECT`, `OPERATIONAL_CONTROL_RECORD`, or `REFERENCE_SET` |
| `CONTROL_RETAINS_BLOB` | `OPERATIONAL_CONTROL_RECORD` | `BLOB` |
| `CONTROL_RETAINS_CONTROL` | `OPERATIONAL_CONTROL_RECORD` | `OPERATIONAL_CONTROL_RECORD` |
| `HOLD_PROTECTS_BLOB` | `OPERATIONAL_CONTROL_RECORD` | `BLOB` |
| `JOB_REQUIRES_BLOB` | `OPERATIONAL_CONTROL_RECORD` | `BLOB` |
| `PATCH_RETAINS_BASE` | `BLOB_MANIFEST` | `BLOB` |
| `PATCH_RETAINS_POSTIMAGE` | `BLOB_MANIFEST` | `BLOB` |
| `REFERENCE_SET_RETAINS_SET` | `OPERATIONAL_CONTROL_RECORD` | `REFERENCE_SET` |
| `TRANSFER_PINS_REPLICA` | `OPERATIONAL_CONTROL_RECORD` | `REPLICA` |

For a `BLOB` target, `target_identity` is the Blob Sigil and equals
`target_sigil`. For `REPLICA`, `REFERENCE_SET`, `CANONICAL_OBJECT`, and
`OPERATIONAL_CONTROL_RECORD`, `target_identity` is respectively an `SR-ID`,
`RS-ID`, the canonical object's operational identity, or the control record's
operational identity; `target_sigil` is the verified immutable record or
Reference Set Sigil. A `BLOB_MANIFEST` source has `identity == sigil`, both
equal to the manifest Blob Sigil. A `REFERENCE_SET_RETAINS_SET` source has
`schema_version: "artifact-storage-reference-set/1.0"`. Every other source
identity and Schema version must resolve to the exact object whose verified
Sigil is `source.sigil`. Any relationship/source/target combination or
identity/Sigil mismatch outside this matrix is a Schema rejection, not an
unknown edge preserved for later interpretation.

`CleanupResult` and `ResidualStagingCleanup` use these exact field/null
matrices:

| Object and state | Object field | Evidence | Reason | Terminal legality |
| --- | --- | --- | --- | --- |
| `CleanupResult.NOT_REQUIRED` | n/a | null | null | yes |
| `CleanupResult.PENDING` | n/a | null | null | no |
| `CleanupResult.CLEANED` | n/a | non-null | null | yes |
| `CleanupResult.FAILED` | n/a | non-null | non-null | yes |
| `ResidualStagingCleanup.NOT_REQUIRED` | null | null | null | yes |
| `ResidualStagingCleanup.PENDING` | non-null | null | null | no |
| `ResidualStagingCleanup.CLEANED` | non-null | non-null | null | yes |
| `ResidualStagingCleanup.FAILED` | non-null | non-null | non-null | no; Recovery remains open |
| `ResidualStagingCleanup.HELD_FOR_DISPOSITION` | non-null | non-null | non-null | yes |

`SystemReserveClass` is exactly `INITIALIZATION`, `COORDINATOR_LIVENESS`,
`CLOCK_PRESSURE`, `CATALOG_ADMINISTRATION`, `VERIFICATION_INCIDENT`,
`RETENTION_REFERENCE`, `GC_ADMINISTRATION`, or `RECOVERY`. A backend's
`system_reserve_limits` contains exactly one member for every class, sorted in
that enum order. Counts are lifetime maxima for the installed backend-profile
version, not advisory telemetry. `max_event_frame_bytes` is in
`56..8388664`, the binary-frame overhead plus the Event-byte bound;
`max_control_record_bytes` and `max_recovery_evidence_bytes` are in
`1..8388664`. Each installed value must be at least the largest canonical item
assigned to that class by conformance fixtures.

`OpenIntentProjection` has exactly these branches. Every branch additionally
has `source_event: EventRef`, `intent_sigil: Sigil`, `revision: 1`, and
`last_event_sigil: Sigil`; both Sigils equal `source_event.event_sigil`.

| `intent_kind` | Exact remaining fields and bindings |
| --- | --- |
| `TRANSFER_COMMIT` | `intent_id: Opaque`, `owner_id: SA-ID`, `staging_object: BackendObjectRef`, `target_object: BackendObjectRef`, `authorization_expires_at: null` |
| `MATERIALIZATION_COMMIT` | `intent_id: Opaque`, `owner_id: SM-ID`, `staging_object: BackendObjectRef`, `target_object: BackendObjectRef`, `authorization_expires_at: null` |
| `QUARANTINE_MOVE` | `intent_id: SQ-ID`, `owner_id: SA-ID\|SM-ID`, `source_object: BackendObjectRef`, `target_object: BackendObjectRef`, `authorization_expires_at: null` |
| `GC_DELETE` | `intent_id: Opaque`, `owner_id: SG-ID`, `target_id: Opaque`, `target_object: BackendObjectRef`, `authorization_expires_at: Timestamp` |
| `DISPOSITION` | `intent_id: Opaque`, `owner_id: SD-ID`, `target_kind: "STAGING"\|"MATERIALIZATION_STAGING"\|"MATERIALIZATION_DESTINATION"\|"QUARANTINE"`, `target_object: BackendObjectRef`, `authorization_expires_at: Timestamp` |
| `CANONICAL_REFERENCE` | `intent_id: RI-ID`, `owner_id: RI-ID`, `expected_chronicle_head: ChronicleHeadRef`, `blob_sigils: [Sigil]`, `reference_set_sigils: [Sigil]`, `authorization_expires_at: null` |

Every field exposed by `TRANSFER_COMMIT` equals the corresponding field in the
owning Attempt's `TransferCommitIntent`; the Materialization and Quarantine
branches likewise equal the corresponding fields in their complete source
intent payloads. The GC and disposition fields equal their started-event
payload and referenced immutable authorization, and the canonical-reference
fields equal its immutable Reference Intent. Fields not duplicated in this
projection are recovered only by resolving the mandatory `source_event`; the
projection never invents a default or substitutes a later record. Open-intent
arrays are unique and sorted by `(intent_kind, intent_id)`. An `intent_id` is
globally unique among all open-intent kinds in one Storage Journal, so the
sorted `open_intent_ids` payload cannot alias two branches.

In a `LEASED` `ExecutionContext`, `execution_journal_id`, `executor_epoch`,
`job_id`, `attempt_id`, and `lease_id` equal the same-named fields inside
`fence` byte-for-byte. Any mismatch is `FENCE_REJECTED`.

`ReasonCode` is exactly:

```text
AUTHORIZATION_DENIED
BACKEND_AMBIGUOUS
BACKEND_CONFLICT
BACKEND_UNAVAILABLE
BOUNDS_EXCEEDED
CANCELLED
CHRONICLE_REFERENCE_CHANGED
CLOCK_UNCERTAIN
CONFLICT
CORRUPT
DESTINATION_CONFLICT
DISPOSITION_EXPIRED
DURABILITY_UNVERIFIED
EXECUTION_HOLD_LIFETIME_EXPIRED
EXECUTION_ROOT_ORPHAN_ABORTED
EXECUTION_ROOT_OWNER_TERMINATED
FENCE_REJECTED
GC_ROOT_CHANGED
GENERATION_MISMATCH
HASH_MISMATCH
INTEGRITY_FAILURE
INVALID_MESSAGE
LEASE_EXPIRED
LEGACY_PROTECTION_FAILED
MINIMUM_REPLICA_VIOLATION
OPERATIONAL_ROOT_TERMINATED
PAYLOAD_LOST
POLICY_REJECTED
QUARANTINE_RESERVATION_FAILED
QUOTA_EXHAUSTED
RECOVERY_INTERRUPTED_PRECOMMIT
RECOVERY_PAYLOAD_LOST
RETENTION_BLOCKED
SOURCE_CHANGED
TAIL_INCOMPLETE
TIMEOUT
UNKNOWN_SCHEMA
UNSAFE_PATH
VERIFICATION_FAILED
```

Every immutable control record in `records/` is canonical JSON, has a
top-level `schema_version`, and has exactly the remaining fields assigned by
its Schema. Its terminal self-Sigil field is `record_sigil`, except that the
Reference Set and Doctor report use the deliberately specific names
`reference_set_sigil` and `report_sigil`; each is computed with itself
omitted. It is stored under a path derived solely by the coordinator from that
self-Sigil. The path is not part of the record or its identity. The exact
top-level field sets are:

| Contract | Exact top-level fields |
| --- | --- |
| `artifact-blob/1.0` | `schema_version`, `blob_sigil`, `size_bytes`, `first_verified_at`, `availability`, `availability_as_of`, `availability_basis_sigil`, `effective_policy_set_sigil`, `next_verification_due_at`, `known_replica_ids`, `eligible_replica_ids`, `integrity_event_sigils`, `media_type_observations`, `filename_observations`, `revision`, `record_sigil` |
| `artifact-replica/1.0` | `schema_version`, `replica_id`, `blob_sigil`, `size_bytes`, `backend`, `object`, `state`, `created_by_transfer_attempt_id`, `verification`, `retention_policy_ids`, `revision`, `record_sigil` |
| `artifact-transfer/1.0` | `schema_version`, `transfer_id`, `direction`, `purpose`, `source`, `destination`, `expected_blob_sigil`, `bounds`, `backend`, `authorization_sigil`, `idempotency_key_sigil`, `execution`, `verification_method`, `provenance_policy_id`, `retention_policy_ids`, `created_at`, `record_sigil` |
| `artifact-transfer-attempt/1.0` | `schema_version`, `transfer_attempt_id`, `transfer_id`, `attempt_number`, `state`, `staging_state`, `reservation`, `staging_object`, `commit_intent`, `residual_staging_cleanup`, `computed_blob_sigil`, `computed_size_bytes`, `selected_replica_id`, `quarantine_id`, `terminal_reason`, `started_at`, `terminal_at`, `revision`, `record_sigil` |
| `artifact-provenance/1.0` | `schema_version`, `provenance_id`, `relation`, `blob`, `source`, `destination`, `actor_id`, `authorization_sigil`, `execution`, `backend`, `transfer`, `verification_sigils`, `transformation`, `times`, `terminal_reason`, `record_sigil` |
| `artifact-materialization/1.0` | `schema_version`, `materialization_id`, `source_blob_sigil`, `source_replica_id`, `source_verification_sigil`, `destination_class`, `destination_sigil`, `task_id`, `attempt_id`, `access_mode`, `bounds`, `reservation`, `destination_staging_object`, `commit_intent`, `residual_staging_cleanup`, `state`, `verification`, `cleanup`, `created_at`, `terminal_at`, `revision`, `record_sigil` |
| `artifact-storage-backend/1.0` | `schema_version`, `backend_id`, `adapter_id`, `adapter_version`, `protocol_version`, `adapter_sigil`, `configuration_sigil`, `namespace_sigil`, `isolation`, `limits`, `consistency`, `durability`, `verification_methods`, `range_resume`, `conditional_operations`, `deletion_capabilities`, `credential_class`, `fencing`, `conformance`, `record_sigil` |
| `artifact-retention-policy/1.0` | `schema_version`, `policy_id`, `scope`, `minimum_replica_count`, `required_backends`, `required_failure_domains`, `maximum_integrity_age_seconds`, `deletion_grace_seconds`, `retain_until`, `automatic_gc_allowed`, `authorization_sigil`, `registered_at`, `record_sigil` |
| `artifact-storage-reference-set/1.0` | `schema_version`, `reference_set_id`, `source`, `extractor`, `edges`, `validation`, `registration_event_id`, `created_at`, `reference_set_sigil` |
| `artifact-storage-reference-intent/1.0` | `schema_version`, `reference_intent_id`, `transition_request_id`, `transition_request_sigil`, `canonical_event_type`, `expected_chronicle_head`, `reference_sets`, `blob_sigils`, `actor_id`, `authorization_sigil`, `idempotency_key_sigil`, `requested_at`, `record_sigil` |
| `artifact-storage-legacy-protection/1.0` | `schema_version`, `protection_id`, `artifact_id`, `program_id`, `artifact_receipt_sigil`, `recorded_uri_sigil`, `lexical_identity_sigil`, `resolved_file_identity_sigil`, `anchor_observation_sigil`, `blob`, `protected_replica_id`, `transfer`, `verification`, `exclusion`, `registered_at`, `record_sigil` |
| `artifact-gc-plan/1.0` | `schema_version`, `gc_plan_id`, `policy_id`, `root_snapshot`, `extractor_suite_sigil`, `bounds`, `closure_proof`, `targets`, `created_at`, `grace_ends_at`, `record_sigil` |
| `artifact-storage-disposition/1.0` | `schema_version`, `disposition_id`, `target_kind`, `target_id`, `target_generation`, `expected_blob_sigil`, `expected_size_or_bound`, `reason_code`, `actor_id`, `policy_sigil`, `approval_evidence_sigil`, `authorization_sigil`, `authorized_at`, `expires_at`, `idempotency_key_sigil`, `record_sigil` |
| `artifact-storage-journal-event/1.0` | `schema_version`, `journal_id`, `event_id`, `sequence`, `event_type`, `coordinator_id`, `epoch`, `recorded_at`, `observed_at`, `entity_revisions`, `causation_event_id`, `idempotency_key_sigil`, `quota_effects`, `payload`, `previous_event_sigil`, `event_sigil` |
| `artifact-storage-journal-head/1.0` | `schema_version`, `journal_id`, `storage_format_version`, `event_count`, `last_sequence`, `last_event_sigil`, `committed_byte_length`, `current_epoch`, `state_sigil`, `updated_at` |
| `artifact-storage-state/1.0` | `schema_version`, `journal_id`, `storage_format_version`, `project_id`, `backend_profile_id`, `backend_profile_sigil`, `conformance_profile_id`, `conformance_suite_sigil`, `store_status`, `active_recovery_id`, `recovery_origin_status`, `clock_status`, `clock_anchor`, `current_epoch`, `applied_event_count`, `last_event_sigil`, `recoveries`, `blobs`, `replicas`, `transfer_requests`, `transfer_attempts`, `materializations`, `quarantines`, `provenance`, `retention_policies`, `holds`, `reference_sets`, `legacy_v1_protections`, `gc_plans`, `canonical_reference_intents`, `dispositions`, `quota_reservations`, `open_intents`, `incidents`, `availability_counters`, `quota_counters`, `state_sigil` |
| `artifact-storage-tail-evidence/1.0` | `schema_version`, `evidence_id`, `recovery_id`, `journal_id`, `kind`, `frame_start`, `observed_size`, `observed_bytes_sigil`, `previous_evidence_record_sigil`, `created_at`, `record_sigil` |
| `artifact-storage-recovery-marker/1.0` | `schema_version`, `recovery_id`, `journal_id`, `prior_head_sigil`, `old_committed_byte_length`, `last_complete_byte_length`, `discarded_suffix_size`, `discarded_suffix_sigil`, `evidence_record_sigil`, `phase`, `recovery_event_id`, `recovery_event_sigil`, `recovery_event_seed_record_sigil`, `recovery_frame_start`, `recovery_frame_size`, `recovery_frame_sigil`, `prepared_frame_evidence_record_sigil`, `retry_count`, `latest_retry_evidence_record_sigil`, `created_at`, `updated_at`, `record_sigil` |
| `artifact-storage-doctor-report/1.0` | `schema_version`, `report_id`, `mode`, `project_id`, `storage_journal_id`, `journal_head_sigil`, `chronicle_head_sigil`, `storage_format_version`, `backend_profile_id`, `backend_profile_sigil`, `conformance_profile_id`, `conformance_suite_sigil`, `coordinator_epoch`, `journal_verification`, `state_verification`, `backend_inventory`, `replica_checks`, `legacy_checks`, `quarantine_checks`, `quota_checks`, `reference_checks`, `open_intent_checks`, `bounds`, `incomplete_reasons`, `overall_status`, `started_at`, `completed_at`, `report_sigil` |

For every row, `schema_version` is the literal contract name in the first
column. A named self-Sigil is `Sigil` and is computed with itself omitted.
Unless a field is explicitly nullable below, it is required and non-null.
The following bindings complete the compact top-level field sets:

- Journal Event `schema_version` is the literal
  `artifact-storage-journal-event/1.0`; `journal_id` is `SJ-ID`; `event_id` is
  `SE-ID`; `sequence` is `PositiveU63`; `event_type` is `StorageEventType`;
  `coordinator_id` is `Opaque`; `epoch` is `PositiveU63`; `recorded_at` is
  `Timestamp`; `observed_at` is `Timestamp|null`; `entity_revisions` is
  `[EntityRevision]`; `causation_event_id` is `SE-ID|null`;
  `idempotency_key_sigil` is `Sigil|null`; `quota_effects` is
  `[QuotaEffect]`; `payload` is the exact event-type union below;
  `previous_event_sigil` is `Sigil|null`; and `event_sigil` is `Sigil`.
  `previous_event_sigil` is null exactly at sequence one and otherwise equals
  the immediately preceding event's Sigil. A non-null causation ID resolves to
  an earlier event in the same Journal. `observed_at` is null only when no
  authenticated external observation time exists; for a payload with `clock`
  it equals `clock.utc`, for `storage.clock_uncertain` it equals
  `detected_clock.utc`, and for `storage.clock_restored` it equals
  `new_clock.utc`. It never orders replay. `storage.initialized` has epoch one;
  a recovery or epoch-start envelope epoch equals its payload `next_epoch`;
  every other Event equals replayed State `current_epoch`.
  `coordinator_id` is stable within one epoch. When an owning immutable record
  contains an idempotency Sigil, a non-null envelope value equals it
  byte-for-byte; otherwise the envelope field is null.
  `event_sigil` is SHA-256 over the complete canonical Event with only that
  field omitted.
- Reference Set identity is `RS-ID`; `source`, `extractor`, `edges`, and
  `validation` are `ReferenceSource`, `ReferenceExtractor`, `[ReferenceEdge]`,
  and `ReferenceValidation`; `registration_event_id` is `SE-ID`; `created_at`
  is `Timestamp`; and `reference_set_sigil` is `Sigil`. Edges are sorted and
  unique by `(relationship, target_kind, target_identity, target_sigil)`.
  Validation evidence is non-empty, sorted, and unique. The registration event payload's
  Reference Set ID, Sigil, source identity, and source Sigil equal the record
  byte-for-byte, and its Event ID equals `registration_event_id`.
- Reference Intent identity is `RI-ID`; `transition_request_id` and `actor_id`
  are `Opaque`; `transition_request_sigil`, `authorization_sigil`,
  `idempotency_key_sigil`, and `record_sigil` are `Sigil`;
  `canonical_event_type` uses the closed enum below;
  `expected_chronicle_head` is `ChronicleHeadRef`; `reference_sets` is a
  non-empty `[ReferenceSetRef]` sorted and unique by `reference_set_id`;
  `blob_sigils` is a sorted unique `[Sigil]` of length `0..4096`; and
  `requested_at` is `Timestamp`. Every member resolves to the complete
  registered Reference Set with the same Sigil. `blob_sigils` equals,
  byte-for-byte, the exact sorted Blob set produced by the bounded typed
  transitive closure of all listed `reference_sets`, as defined under
  Schema-aware reference closure. The empty array is legal exactly when that
  closure reaches no Blob. The `canonical_reference.intent_recorded`
  payload's expected Head, Blob array, and Reference Set Sigil array equal the
  immutable record, its `ControlRef` names this Schema, ID, and
  `record_sigil`, and its lifecycle Reservation owner ID equals
  `reference_intent_id`. That Reservation has
  `expires_at == null` and `remaining_micros_at_creation == null`; a
  time-limited canonical pin is invalid.

Reference Set and Reference Intent identities are deterministic:

```text
reference_set_id =
  "RS-" + UPPER_HEX(SHA256(canonical_json(
    ["artifact-storage-reference-set-id/1.0",
     source, extractor, edges, validation])))

registration_event_id =
  if source.kind == "OPERATIONAL_CONTROL_RECORD"
     and source.schema_version == "execution-storage-root-manifest/1.0":
    "SE-" + UPPER_HEX(SHA256(canonical_json(
      ["artifact-storage-execution-root-reference-set-registration-event-id/1.0",
       source.identity])))
  else:
    "SE-" + UPPER_HEX(SHA256(canonical_json(
      ["artifact-storage-reference-set-registration-event-id/1.0",
       reference_set_id])))

reference_intent_id =
  "RI-" + UPPER_HEX(SHA256(canonical_json(
    ["artifact-storage-reference-intent-id/1.0",
     canonical_event_type,
     transition_request_id])))
```

Before allocating any registration Event or using a receive time in a
Reference Set, Storage atomically creates or resolves one pending candidate at
the deterministic `reference_set_id`. First creation fixes `created_at` and
the complete record bytes, including the deterministic
`registration_event_id`; retry reuses those bytes. A complete matching
registered set and Event are returned without another append. Different bytes
at the same identity are an integrity conflict. A torn candidate or ambiguous
Event acknowledgement is recovered by that same ID/Event-ID pair before any
higher-layer request is rebuilt.

For the execution-root branch, `source.identity` is the RFC-0012 `ESM-ID` and
the special Event ID equals the ESM's precomputed
`reference_set_registration_event_id`. Storage additionally maintains one
single-assignment candidate per `(ESM-ID, special registration Event ID)`.
It first resolves the complete ESM, then derives the fixed source, installed
extractor and validator, exact edges, and exact validation fields specified by
RFC-0012, and only then derives the RS-ID and Reference Set Sigil. A second
candidate, alternate RS-ID, generic RS-derived Event ID, changed
extractor/validator, or different registration Event for that ESM is an
integrity conflict. Execution-root `validation.evidence_sigils` is the exact
RFC-0012 projection and contains no future Reference Set Sigil, registration
Event Sigil, hold authorization, or hold-set Event Sigil. The dependency is
therefore acyclic:

```text
owner binding -> ESM-ID -> registration SE-ID -> ESM bytes/Sigil
  -> source/extractor/edges/validation -> RS-ID/Sigil
  -> registration Event body/Sigil
```

Likewise, `(canonical_event_type, transition_request_id)` has one global
Reference Intent identity and one projection entry. Atomic create-if-absent
fixes the complete record bytes; an exact retry reuses its existing
`intent_recorded` Event or finishes the one missing Event, while different
bytes are an idempotency conflict. State replay, Doctor, and recovery reject
two records or two creation Events for that identity even if their RI-IDs,
request keys, or otherwise valid fields differ. No scan or newly allocated
RI-ID is permitted.
- Blob identity and basis Sigils are `Sigil`; size and revision are `U63` and
  `PositiveU63`; times are `Timestamp` or the stated nullable time;
  availability is `AVAILABLE`, `DEGRADED`, `UNAVAILABLE`, or `INCIDENT`;
  `availability_as_of` is `EventRef`; Replica IDs are `[SR-ID]`; integrity
  identities are `[Sigil]`; and media-type and filename observations are
  `[Opaque]`.
- Replica ID is `SR-ID`; its Blob identity and size are `Sigil` and `U63`;
  backend and object are `BackendRef` and `BackendObjectRef`; state is
  `COMMITTING`, `AVAILABLE`, `VERIFYING`, `STALE`, `CORRUPT`, `ABANDONED`,
  `DELETING`, `DELETED`, or `DELETE_FAILED`; creator is `SA-ID`;
  verification is `VerificationRef|null`; policy IDs are `[SP-ID]`; and
  revision is `PositiveU63`. Verification is null exactly in `COMMITTING` or
  `ABANDONED`; it is non-null in `AVAILABLE`, `VERIFYING`, `STALE`,
  `DELETING`, `DELETED`, and `DELETE_FAILED`. `CORRUPT` retains a non-null last
  successful verification when one exists and is null only when corruption
  was proven before any successful committed-generation verification.
- Transfer ID is `ST-ID`; source, destination, bounds, backend, and execution
  use their named aliases; all authorization, idempotency, and policy-set
  identities are `Sigil`; retention policy IDs are `[SP-ID]`; and creation is
  `Timestamp`.
- Transfer Attempt IDs are `SA-ID` and `ST-ID`; attempt number and revision
  are `PositiveU63`; state uses the transfer-attempt state enum;
  `staging_state` is `NOT_CREATED`, `PRESENT`, `MISSING`, or
  `HELD_FOR_DISPOSITION`; reservation is `ReservationRef`; staging object,
  commit intent, computed Blob Sigil and size, selected Replica,
  Quarantine ID, terminal reason, and terminal time are nullable with types
  `BackendObjectRef`, `TransferCommitIntent`, `Sigil`, `U63`, `SR-ID`,
  `SQ-ID`, `Reason`, and `Timestamp`; residual cleanup is
  `ResidualStagingCleanup`; and start time is `Timestamp`.
- Provenance identity and actor are `Opaque`; relation is
  `ProvenanceRelation`; Blob, source, destination, execution, backend, transfer,
  transformation, and times use their named aliases; authorization and
  verification identities are `Sigil` and `[Sigil]`; terminal reason is
  `Reason|null`.
- Materialization ID is `SM-ID`; source Blob and verification identities and
  destination identity are `Sigil`; source Replica is `SR-ID`;
  destination class is `SANCTUM_INPUT`, `CRUCIBLE_WORKSPACE`, or
  `PROJECT_EXPORT`; Task and Attempt IDs are `Opaque|null`; access mode is
  `READ_ONLY`, `COPY_ON_WRITE`, or `WRITABLE_COPY`; bounds, reservation,
  staging object, commit intent, residual staging cleanup, verification, and
  cleanup use the bindings below; state uses the materialization state enum;
  creation is `Timestamp`, terminal time is `Timestamp|null`, and revision is
  `PositiveU63`.
- Legacy-protection IDs, Artifact IDs, and Program IDs are `Opaque`; all
  Receipt, URI, path-identity, anchor, and record identities are `Sigil`;
  Blob, transfer, verification, and exclusion use their named aliases;
  protected Replica is `SR-ID`; and registration is `Timestamp`.
- GC plan ID and policy ID are `SG-ID` and `SP-ID`; root snapshot, bounds,
  closure proof, and targets use their named aliases; extractor identity is
  `Sigil`; creation and grace end are `Timestamp`.
- Disposition ID is `SD-ID`; target kind is `STAGING`,
  `MATERIALIZATION_STAGING`, `MATERIALIZATION_DESTINATION`, or `QUARANTINE`;
  target ID and generation and actor ID are `Opaque`; expected Blob is
  `Sigil|null`; size/bound uses `ExpectedSizeOrBound`; reason is
  `ReasonCode`; all policy, approval, authorization, and idempotency
  identities are `Sigil`; and both times are `Timestamp`.
  `target_id` is an `SA-ID`, `SM-ID`, `SM-ID`, or `SQ-ID` respectively for
  those four target kinds, and `target_generation` equals the selected
  `BackendObjectRef.generation`.

Tail-evidence records are closed immutable recovery records. `kind` is exactly
`ORIGINAL_INTERRUPTED_APPEND`, `RECOVERY_EVENT_SEED`,
`RECOVERY_FRAME_TEMPLATE`, or `RECOVERY_FRAME_RETRY_SUFFIX`. `frame_start` and
`observed_size` are `U63`;
`evidence_id` and `recovery_id` are `Opaque`, `journal_id` is `SJ-ID`, all
named Sigils are `Sigil`, and `created_at` is `Timestamp`.
all four kinds require a positive observed size. A seed's raw bytes are the
complete canonical recovery Event bytes; a template's are the complete binary
frame. The exact raw bytes are stored next to the record under a
content-derived name and must hash to `observed_bytes_sigil`; a record without
those bytes is invalid. `previous_evidence_record_sigil` is null only for the
original suffix. The seed points to the original, the template points to the
seed, and each retry suffix points to the immediately preceding template or
retry record, forming a bounded verified chain without an array that can be
silently truncated.

The Recovery Marker's phase is exactly `EVIDENCE_DURABLE`,
`TAIL_TRUNCATED`, `RECOVERY_EVENT_ID_DURABLE`, `RECOVERY_EVENT_PREPARED`,
`RECOVERY_EVENT_RETRY_EVIDENCE_DURABLE`, or
`RECOVERY_EVENT_COMMITTED`. In the first two phases the event ID, event Sigil,
seed Sigil, all `recovery_frame_*` fields, and prepared-template field are
null. In `RECOVERY_EVENT_ID_DURABLE`, the event ID, event Sigil, and seed
record Sigil are non-null and immutable while all frame and prepared-template
fields remain null. From `RECOVERY_EVENT_PREPARED` onward, those three fields,
frame start, positive frame size, frame Sigil, and template evidence-record
Sigil are non-null and immutable. `retry_count` is zero before the retry phase;
`latest_retry_evidence_record_sigil` is null exactly when `retry_count` is
zero and otherwise identifies the last chained retry suffix. `retry_count`
cannot exceed the installed backend's `limits.max_tail_recovery_retries`.
Every phase replacement preserves the same recovery identity and original
tail fields and advances `updated_at`; changing any prepared-event field is an
integrity failure.
Marker recovery ID is `Opaque`, journal ID is `SJ-ID`, byte offsets, lengths,
and retry count are `U63` with the stated positive constraints, all named
Sigils are `Sigil|null` where the phase matrix permits null, recovery event ID
is `SE-ID|null`, and both times are `Timestamp`.

Every nested object named by those contracts is also closed and is assigned
once in the executable Schema `$defs`; it cannot be a free-form map. `source`,
`destination`, `backend`, `object`, `bounds`, `execution`, `transfer`,
`transformation`, `times`, `cleanup`, `root_snapshot`, `closure_proof`,
`authorization`, and `outcome` are discriminated unions with an explicit
`kind` or `state`. Unknown discriminators are invalid. The executable Schema
suite must contain one positive fixture for every branch and one
additional-property rejection fixture for every object definition before this
RFC can advance from draft.

Specifically, Replica `backend` and `object` use `BackendRef` and
`BackendObjectRef`. Transfer `source`, `destination`, `bounds`, `backend`, and
`execution` use `SourceDescriptor`, `DestinationDescriptor`,
`TransferBounds`, `BackendRef`, and `ExecutionContext`.
Transfer Attempt `reservation`, `staging_object`, `commit_intent`, and
`residual_staging_cleanup` use `ReservationRef`, nullable
`BackendObjectRef`, nullable `TransferCommitIntent`, and
`ResidualStagingCleanup`.
Provenance `blob`, `source`, `destination`, `execution`, `backend`,
`transfer`, `transformation`, and `times` use `BlobRef`, the two descriptors,
`ExecutionContext`, `BackendRef`, `TransferRef`, `TransformationRef`, and
`TimeSet`.
Materialization `bounds`, `reservation`, `verification`, `cleanup`, and
`residual_staging_cleanup` use `TransferBounds`, `ReservationRef`, nullable
`VerificationRef`, `CleanupResult`, and `ResidualStagingCleanup`; its
`destination_staging_object` is `BackendObjectRef|null`, and `commit_intent`
is `MaterializationCommitIntent|null`. Before commit intent, residual cleanup
is `NOT_REQUIRED`; at commit intent it becomes `PENDING`; every terminal
Materialization uses only `NOT_REQUIRED`, `CLEANED`, or
`HELD_FOR_DISPOSITION`. Retention `scope` uses `PolicyScope`.
Legacy protection `blob`, `transfer`, `verification`, and `exclusion` use
`BlobRef`, `TransferRef`, `VerificationRef`, and `LegacyExclusion`. GC `root_snapshot`,
`bounds`, `closure_proof`, and every target use `GCRootSnapshot`,
`TraversalBounds`, `ClosureProof`, and `GCTarget`. Disposition
`expected_size_or_bound` uses `ExpectedSizeOrBound`.

Backend `isolation`, `limits`, `consistency`, `durability`, `range_resume`,
`conditional_operations`, `deletion_capabilities`, `fencing`, and
`conformance` use the same-named `Backend*` aliases above.
`verification_methods` is a non-empty sorted unique array whose members are
exactly `FULL_READBACK_SHA256` or `CONFORMANCE_END_TO_END`.
`credential_class` is exactly `COORDINATOR_HOST_LOCAL` or
`COORDINATOR_SCOPED_REMOTE`; the local profile requires the former. Backend
IDs and version fields are `Opaque`; `adapter_sigil`, `configuration_sigil`,
`namespace_sigil`, and `record_sigil` are `Sigil`.

Retention `policy_id` is `SP-ID`, `scope` is `PolicyScope`,
`minimum_replica_count` is `U63`, `required_backends` and
`required_failure_domains` are sorted unique `[Opaque]`,
`maximum_integrity_age_seconds` and `deletion_grace_seconds` are
`U63|null`, `retain_until` is `Timestamp|null`, `automatic_gc_allowed` is
`boolean`, `authorization_sigil` is `Sigil`, and `registered_at` is
`Timestamp`.

Doctor `journal_verification` and `state_verification` are `CheckResult`;
`backend_inventory` is `[BackendInventoryEntry]`; `replica_checks`,
`legacy_checks`, `quarantine_checks`, `quota_checks`, `reference_checks`, and
`open_intent_checks` are `[CheckResult]`; `bounds` is `DoctorBounds`;
`incomplete_reasons` is `[Reason]`; and both times are `Timestamp`.
`mode` and `overall_status` use the enums in the Storage Doctor section.
`project_id` and `report_id` are `Opaque`, `report_sigil` is `Sigil`, and
`storage_journal_id` is `SJ-ID|null`. The report's observed
`journal_head_sigil`, `chronicle_head_sigil`, `backend_profile_sigil`, and
`conformance_suite_sigil` are `Sigil|null`; its storage-format,
backend-profile, and conformance-profile IDs are `Opaque|null`; and
`coordinator_epoch` is `U63|null`.

Transfer `direction` is exactly `INGEST`, `COPY`, `EXPORT`, or
`MATERIALIZE`; `purpose` is exactly `ARTIFACT_IMPORT`, `ATTEMPT_OUTPUT`,
`LEGACY_V1_PROTECTION`, `REPLICA_COPY`, `REPLICA_REPAIR`,
`SANCTUM_INPUT`, `PATCH_BUNDLE`, `USER_EXPORT`, or
`QUARANTINE_REINSPECTION`. `expected_blob_sigil` is `Sigil|null`.
`verification_method` is `VerificationMethod`.

`entity_revisions` members contain exactly `entity_type`, `entity_id`,
`previous_revision`, and `next_revision`. `previous_revision` is `U63|null`;
`next_revision` is `PositiveU63`, equals one when the prior value is null, and
otherwise equals the prior value plus one. Members are unique and sorted by
`(entity_type, entity_id)`. `entity_type` is exactly `STORE`, `BLOB`,
`REPLICA`, `TRANSFER_REQUEST`, `TRANSFER_ATTEMPT`, `MATERIALIZATION`,
`QUARANTINE`, `PROVENANCE`, `RETENTION_POLICY`, `HOLD`, `REFERENCE_SET`,
`REFERENCE_INTENT`, `LEGACY_PROTECTION`, `GC_PLAN`, `DISPOSITION`, `QUOTA`,
or `INCIDENT`.

`entity_revisions` contains only directly owned mutable projections. A
policy-, hold-, reference-, or trusted-clock event that changes a derived
Blob availability view lists its owning entity revisions exactly as shown in
the event table and does not enumerate fan-out `BLOB` revisions. Replay must
still recompute the affected closed Blob views and availability counters from
the new global basis. Omitting a directly changed Blob or Replica is invalid;
adding a synthetic fan-out revision is also invalid.

State collections are not generic maps. Their item shapes are exactly:

| State collection | Exact item fields |
| --- | --- |
| `recoveries` | `recovery_id: Opaque`, `origin_status: INITIALIZING\|ACTIVE`, `state: ACTIVE\|COMPLETED`, `started_event_sigil: Sigil`, `epoch_ids: [U63]`, `tail_recovery_evidence_record_sigils: [Sigil]`, `completed_event_sigil: Sigil\|null`, `resume_status: INITIALIZING\|ACTIVE\|null` |
| `blobs` | `record: artifact-blob/1.0`, `last_event_sigil: Sigil` |
| `replicas` | `record: artifact-replica/1.0`, `last_event_sigil: Sigil` |
| `transfer_requests` | `transfer_id: ST-ID`, `request_record_sigil: Sigil`, `state: ACTIVE\|SATISFIED`, `attempt_ids: [SA-ID]`, `selected_attempt_id: SA-ID\|null`, `revision: PositiveU63`, `last_event_sigil: Sigil` |
| `transfer_attempts` | `record: artifact-transfer-attempt/1.0`, `last_event_sigil: Sigil` |
| `materializations` | `record: artifact-materialization/1.0`, `last_event_sigil: Sigil` |
| `quarantines` | `quarantine_id: SQ-ID`, `owner_kind: TRANSFER_ATTEMPT\|MATERIALIZATION`, `owner_id: Opaque`, `state: INTENT_RECORDED\|HELD\|INSPECTING\|DISPOSING\|DISPOSED\|DISPOSAL_FAILED\|FAILED`, `source_object: BackendObjectRef\|null`, `destination_object: BackendObjectRef\|null`, `source_cleanup: ResidualStagingCleanup`, `reservation: ReservationRef`, `reason: Reason`, `revision: PositiveU63`, `last_event_sigil: Sigil`, `record_sigil: Sigil`; `owner_id` is `SA-ID` or `SM-ID` exactly as selected by `owner_kind` |
| `provenance` | `provenance_id: Opaque`, `record_sigil: Sigil`, `revision: 1`, `last_event_sigil: Sigil` |
| `retention_policies` | `policy_id: SP-ID`, `record_sigil: Sigil`, `revision: 1`, `last_event_sigil: Sigil` |
| `holds` | `hold_id: SH-ID`, `target_kind: BLOB\|REPLICA\|REFERENCE_SET`, `target_id: Opaque`, `policy_id: SP-ID`, `state: ACTIVE\|RELEASED`, `set_authorization_sigil: Sigil`, `release_authorization_sigil: Sigil\|null`, `revision: PositiveU63`, `last_event_sigil: Sigil` |
| `reference_sets` | `reference_set_id: RS-ID`, `reference_set_sigil: Sigil`, `source_identity: Opaque`, `revision: 1`, `last_event_sigil: Sigil` |
| `legacy_v1_protections` | `PROTECTED {protection_id: Opaque, artifact_id: Opaque, state: "PROTECTED", record: artifact-storage-legacy-protection/1.0, receipt_sigil: Sigil, reason: null, revision: PositiveU63, last_event_sigil: Sigil}` or `FAILED {protection_id: Opaque, artifact_id: Opaque, state: "FAILED", record: null, receipt_sigil: Sigil\|null, reason: Reason, revision: PositiveU63, last_event_sigil: Sigil}` |
| `gc_plans` | `gc_plan_id: SG-ID`, `record_sigil: Sigil`, `state: DRAFT\|AUTHORIZED\|EXECUTING\|COMPLETED\|PARTIAL\|ABORTED`, `authorization_sigil: Sigil\|null`, `authorized_at: Timestamp\|null`, `authorization_expires_at: Timestamp\|null`, `target_states: [GCTargetState]`, `revision: PositiveU63`, `last_event_sigil: Sigil` |
| `canonical_reference_intents` | `reference_intent_id: RI-ID`, `record_sigil: Sigil`, `state: OPEN\|COMMITTED\|RELEASED`, `chronicle_commit: ChronicleCommitRef\|null`, `release_kind: "ABORTED_BEFORE_CANONICAL_COMMIT"\|null`, `release_authority_sigil: Sigil\|null`, `release_reason: Reason\|null`, `revision: PositiveU63`, `last_event_sigil: Sigil`; the four terminal fields are all null in `OPEN`, only `chronicle_commit` is non-null in `COMMITTED`, and only the three release fields are non-null in `RELEASED` |
| `dispositions` | `disposition_id: SD-ID`, `record_sigil: Sigil`, `state: AUTHORIZED\|EXECUTING\|COMPLETED\|FAILED`, `execution_intent_id: Opaque\|null`, `outcome_sigil: Sigil\|null`, `revision: PositiveU63`, `last_event_sigil: Sigil` |
| `quota_reservations` | `reservation: ReservationRef`, `owner_kind: QuotaOwnerKind`, `owner_id: Opaque`, `purpose: QuotaPurpose`, `state: ACTIVE\|RETAINED\|SETTLED`, `consumed_claims: [QuotaClaim]`, `released_claims: [QuotaClaim]`, `remaining_claims: [QuotaClaim]`, `retained_for_event_types: [StorageEventType]`, `revision: PositiveU63`, `last_event_sigil: Sigil` |
| `open_intents` | `OpenIntentProjection` |
| `incidents` | `incident_id: Opaque`, `subject_kind: IncidentSubjectKind`, `subject_id: Opaque`, `reason: Reason`, `state: "OPEN"`, `revision: 1`, `last_event_sigil: Sigil` |

For a GC target, `deletion_intent_id` and `outcome_reservation` are null in
`PLANNED` or `SKIPPED` and non-null in `DELETING`, `DELETED`, or `FAILED`;
`root_revalidation_sigil` is non-null after skip or deletion start;
`deletion_evidence_sigil` is non-null only in `DELETED`; and
`terminal_reason` is non-null exactly in `SKIPPED` or `FAILED`. A Disposition's
`execution_intent_id` is null in `AUTHORIZED` and in the pre-start
`AUTHORIZED -> FAILED` expiry branch. It is non-null in `EXECUTING`,
`COMPLETED`, and the post-start `EXECUTING -> FAILED` branch.
`outcome_sigil` is null in `AUTHORIZED` or `EXECUTING`; in `COMPLETED` or
either `FAILED` branch it equals the terminal Event Sigil.

`availability_counters` contains exactly `available_blobs`,
`degraded_blobs`, `unavailable_blobs`, and `incident_blobs`, all `U63`.
`quota_counters` is a sorted array with exactly one `QuotaSnapshot` for every
legal class/dimension pair, ordered by that pair. All other State arrays
are sorted by their first identity field, or by the identity field inside
`record` for the four record-wrapper collections; `open_intents` alone uses
the `(intent_kind, intent_id)` order defined above. Every wrapper is closed;
duplicate keys are invalid.
Each Quarantine projection's `record_sigil` covers that complete closed item
with `record_sigil` omitted; it changes with the revision and is not an
immutable control-record identity.

GC target-state fields obey this exact matrix. `PLANNED` has all four
nullable evidence fields null. `SKIPPED` has non-null root-revalidation Sigil
and terminal reason, with null reservation and deletion evidence. `DELETING`
has non-null root-revalidation Sigil and outcome reservation, with null
deletion evidence and reason. `DELETED` preserves those two non-null fields,
adds non-null deletion evidence, and has null reason. `FAILED` preserves the
non-null revalidation Sigil and reservation, has null deletion evidence, and
has a non-null reason. Target states are sorted by `target_id`.

`store_status` is exactly `INITIALIZING`, `ACTIVE`, or `RECOVERING`.
`active_recovery_id` and `recovery_origin_status` are both null outside
`RECOVERING` and both non-null inside it; the origin is exactly
`INITIALIZING` or `ACTIVE`. A completed recovery's `resume_status` equals its
origin and its completion Sigil is non-null. An active recovery has null
completion and resume fields. Recovery entries are sorted by their
`storage.recovery_started` sequence; `epoch_ids` is non-empty, strictly
increasing, and appends the current epoch after every recovery re-crash.

A quota reservation follows `NONE -> ACTIVE -> RETAINED`,
`RETAINED -> RETAINED`, and `ACTIVE|RETAINED -> SETTLED`.
Every transition is driven by one matching `QuotaEffect`; there is no
directory-derived or implicit release. A retained reservation can be settled
only by one of its exact `retained_for_event_types`. State replay applies all
effects in array order, stores cumulative consumed and released claims,
verifies each resulting `QuotaSnapshot`, and then recomputes
`quota_counters`; arithmetic overflow, a negative balance, an unknown
reservation, an illegal class/dimension pair, or a snapshot mismatch is
`INTEGRITY_FAILURE`.

### Closed event set

The `artifact-storage-journal-event/1.0` event-type enum is exactly:

```text
storage.initialized
storage.activation_completed
storage.epoch_started
storage.clock_uncertain
storage.clock_restored
storage.recovery_started
storage.recovery_completed
storage.message_rejected
legacy_v1.protection_registered
legacy_v1.protection_failed
quota.pressure_entered
quota.pressure_cleared
transfer.prepared
transfer.streaming_started
transfer.verification_started
transfer.commit_intent_recorded
transfer.committed
transfer.failed
transfer.cancelled
transfer.quarantined
replica.verification_started
replica.verified
replica.verification_expired
replica.corrupt
blob.incident_recorded
materialization.prepared
materialization.streaming_started
materialization.verification_started
materialization.commit_intent_recorded
materialization.committed
materialization.cleanup_started
materialization.cleaned
materialization.cleanup_failed
materialization.failed
materialization.quarantined
quarantine.intent_recorded
quarantine.recorded
quarantine.failed
quarantine.reinspection_started
quarantine.reinspection_completed
provenance.recorded
retention.policy_registered
retention.hold_set
retention.hold_released
reference_set.registered
canonical_reference.intent_recorded
canonical_reference.committed
canonical_reference.released
gc.plan_created
gc.plan_authorized
gc.execution_started
gc.target_skipped
gc.target_deletion_started
gc.target_deleted
gc.target_failed
gc.completed
gc.aborted
disposition.authorized
disposition.started
disposition.completed
disposition.failed
```

The following tables are the complete event-to-payload construction. Every
listed payload field is required; `|null` is the only nullable notation.
`[T]` is a sorted unique bounded array, `Object` means `BackendObjectRef`,
`Fence` means `ExecutionFenceRef`, `Verify` means `VerificationRef`, `Ref`
means `ControlRef`, and `Clock` means `ClockRef`. The revision column is the
exact directly owned `entity_type` set. Each non-`QUOTA` entity appears once.
`QUOTA` means the exact one-or-more quota projection revisions selected
one-to-one by that event's non-empty `quota_effects`; their entity IDs are the
reservation IDs or
`quota-counter:<QuotaClass>:<QuotaDimension>` keys, then the resulting
members are independently placed by the mandatory entity-revision sort. Every
`INITIALIZE` or `PRESSURE` effect uses the class and dimension in its snapshot;
every `USAGE_REMOVED` counter revision uses the class and sole non-zero legal
dimension in its removal claim. The twelve initialization effects therefore
produce twelve distinct `QUOTA` revisions, in the same class/dimension order
as `quota_counters`.
An event whose row omits `QUOTA` requires empty `quota_effects`; `none`
requires an empty revision array. Where a row names alternatives separated by
`or`, the Event Schema uses `oneOf` selected by the stated discriminator and
admits no other combination.

Every `Ref` is further narrowed by its payload field: `backend`,
`protection`, `transfer`, `transfer_attempt`, `replica`,
`provisional_replica`, `materialization`, `provenance`, `policy`,
`reference_intent`, `gc_plan`, and `disposition` require the matching owned
contract's literal `schema_version`, operational record ID, and self-Sigil. A
Ref to a different Schema or ID class is invalid even when its Sigil resolves.

| Event type | Exact payload fields | Exact revisions |
| --- | --- | --- |
| `storage.initialized` | `project_id: Opaque`, `storage_format_version: Opaque`, `backend: Ref`, `conformance_profile_id: Opaque`, `conformance_suite_sigil: Sigil`, `quota_snapshots: [QuotaSnapshot]`, `tail_recovery: TailRecovery\|null`, `clock: Clock` | `STORE`, `QUOTA` |
| `storage.activation_completed` | `legacy_protection_ids: [Opaque]`, `activation_evidence_sigil: Sigil`, `clock: Clock` | `STORE` |
| `storage.epoch_started` | `previous_epoch: U63`, `next_epoch: PositiveU63`, `active_recovery_id: Opaque\|null`, `tail_recovery: TailRecovery\|null`, `reason: Reason`, `clock: Clock` | `STORE` |
| `storage.clock_uncertain` | `previous_clock: Clock`, `detected_clock: Clock`, `divergence_micros: U63`, `affected_reservation_ids: [Opaque]`, `reason: Reason` | `STORE` |
| `storage.clock_restored` | `previous_observation_sigil: Sigil`, `new_clock: Clock`, `expired_entity_ids: [Opaque]`, `evidence_sigils: [Sigil]` | `STORE` |
| `storage.recovery_started` | `recovery_id: Opaque`, `origin_status: "INITIALIZING"\|"ACTIVE"`, `previous_epoch: U63`, `next_epoch: PositiveU63`, `tail_recovery: TailRecovery\|null`, `open_intent_ids: [Opaque]`, `clock: Clock` | `STORE` |
| `storage.recovery_completed` | `recovery_id: Opaque`, `epoch: PositiveU63`, `resume_status: "INITIALIZING"\|"ACTIVE"`, `resolved_intent_ids: [Opaque]`, `evidence_sigils: [Sigil]`, `clock: Clock` | `STORE` |
| `storage.message_rejected` | `message_class: Opaque`, `message_sigil: Sigil\|null`, `reason: Reason` | `none` |
| `legacy_v1.protection_registered` | `protection: Ref`, `artifact_id: Opaque`, `receipt_sigil: Sigil`, `anchor_observation_sigil: Sigil`, `blob_sigil: Sigil`, `size_bytes: U63`, `replica_id: SR-ID` | `LEGACY_PROTECTION`, `BLOB`, `REPLICA` |
| `legacy_v1.protection_failed` | `protection_id: Opaque`, `artifact_id: Opaque`, `receipt_sigil: Sigil\|null`, `reason: Reason` | `LEGACY_PROTECTION` |
| `quota.pressure_entered` | `snapshot: QuotaSnapshot`, `reason: Reason`, `clock: Clock` | `QUOTA` |
| `quota.pressure_cleared` | `snapshot: QuotaSnapshot`, `evidence_sigils: [Sigil]`, `clock: Clock` | `QUOTA` |

| Event type | Exact payload fields | Exact revisions |
| --- | --- | --- |
| `transfer.prepared` | `transfer: Ref`, `transfer_attempt: Ref`, `reservation: ReservationRef`, `execution_fence: Fence\|null` | `TRANSFER_REQUEST`, `TRANSFER_ATTEMPT`, `QUOTA` |
| `transfer.streaming_started` | `transfer_id: ST-ID`, `transfer_attempt_id: SA-ID`, `staging_object: Object`, `execution_fence: Fence\|null`, `clock: Clock` | `TRANSFER_ATTEMPT` |
| `transfer.verification_started` | `transfer_id: ST-ID`, `transfer_attempt_id: SA-ID`, `staging_object: Object`, `computed_blob_sigil: Sigil`, `computed_size_bytes: U63`, `verification_method: VerificationMethod`, `execution_fence: Fence\|null` | `TRANSFER_ATTEMPT` |
| `transfer.commit_intent_recorded` | `transfer_id: ST-ID`, `transfer_attempt_id: SA-ID`, `commit_intent: TransferCommitIntent`, `provisional_replica: Ref` | `TRANSFER_ATTEMPT`, `BLOB`, `REPLICA` |
| `transfer.committed` | `transfer_id: ST-ID`, `transfer_attempt_id: SA-ID`, `outcome: "NEW_REPLICA"\|"DEDUPLICATED_REPLICA"`, `provisional_replica_id: SR-ID`, `provisional_target_absence_evidence_sigil: Sigil\|null`, `blob_sigil: Sigil`, `size_bytes: U63`, `replica: Ref`, `backend_object: Object`, `verification: Verify`, `residual_staging_cleanup: ResidualStagingCleanup`, `execution_fence: Fence\|null` | `TRANSFER_REQUEST`, `TRANSFER_ATTEMPT`, `BLOB`, provisional `REPLICA`, `QUOTA`; the selected existing Replica in the dedup branch is verified but not revised |
| `transfer.failed` | `transfer_id: ST-ID`, `transfer_attempt_id: SA-ID`, `reason: Reason`, `staging_object: Object\|null`, `staging_state: "NOT_CREATED"\|"MISSING"\|"HELD_FOR_DISPOSITION"`, `residual_staging_cleanup: ResidualStagingCleanup`, `provisional_replica_id: SR-ID\|null`, `provisional_target_absence_evidence_sigil: Sigil\|null`, `blob_sigil: Sigil\|null`, `execution_fence: Fence\|null` | pre-intent: `TRANSFER_REQUEST`, `TRANSFER_ATTEMPT`, `QUOTA`; post-intent: those plus `BLOB`, `REPLICA`, selected by the provisional ID and Blob fields both being null or non-null |
| `transfer.cancelled` | `transfer_id: ST-ID`, `transfer_attempt_id: SA-ID`, `reason: Reason`, `staging_object: Object\|null`, `staging_state: "NOT_CREATED"\|"MISSING"\|"HELD_FOR_DISPOSITION"`, `residual_staging_cleanup: ResidualStagingCleanup`, `provisional_replica_id: SR-ID\|null`, `provisional_target_absence_evidence_sigil: Sigil\|null`, `blob_sigil: Sigil\|null`, `execution_fence: Fence\|null` | pre-intent: `TRANSFER_REQUEST`, `TRANSFER_ATTEMPT`, `QUOTA`; post-intent: those plus `BLOB`, `REPLICA`, selected by the provisional ID and Blob fields both being null or non-null |
| `transfer.quarantined` | `transfer_id: ST-ID`, `transfer_attempt_id: SA-ID`, `quarantine_id: SQ-ID`, `quarantine_event: EventRef`, `residual_staging_cleanup: ResidualStagingCleanup`, `reason: Reason`, `provisional_replica_id: SR-ID\|null`, `provisional_target_absence_evidence_sigil: Sigil\|null`, `blob_sigil: Sigil\|null`, `execution_fence: Fence\|null` | pre-intent: `TRANSFER_REQUEST`, `TRANSFER_ATTEMPT`, `QUARANTINE`, `QUOTA`; post-intent: those plus `BLOB`, `REPLICA`, selected by the provisional ID and Blob fields both being null or non-null |
| `replica.verification_started` | `replica_id: SR-ID`, `backend_object: Object`, `method: VerificationMethod`, `clock: Clock` | `REPLICA`, `BLOB` |
| `replica.verified` | `replica_id: SR-ID`, `backend_object: Object`, `verification: Verify`, `clock: Clock` | `REPLICA`, `BLOB` |
| `replica.verification_expired` | `replica_id: SR-ID`, `due_at: Timestamp`, `clock: Clock` | `REPLICA`, `BLOB` |
| `replica.corrupt` | `replica_id: SR-ID`, `backend_object: Object`, `reason: Reason`, `verification: Verify\|null` | `REPLICA`, `BLOB` |
| `blob.incident_recorded` | `blob_sigil: Sigil`, `incident_id: Opaque`, `reason: Reason`, `conflicting_record_sigils: [Sigil]` | `BLOB`, `INCIDENT` |

| Event type | Exact payload fields | Exact revisions |
| --- | --- | --- |
| `materialization.prepared` | `materialization: Ref`, `source_replica_id: SR-ID`, `source_verification_sigil: Sigil`, `reservation: ReservationRef`, `execution_fence: Fence\|null` | `MATERIALIZATION`, `QUOTA` |
| `materialization.streaming_started` | `materialization_id: SM-ID`, `destination_staging_object: Object`, `clock: Clock` | `MATERIALIZATION` |
| `materialization.verification_started` | `materialization_id: SM-ID`, `destination_staging_object: Object`, `expected_blob_sigil: Sigil`, `expected_size_bytes: U63` | `MATERIALIZATION` |
| `materialization.commit_intent_recorded` | `materialization_id: SM-ID`, `commit_intent: MaterializationCommitIntent` | `MATERIALIZATION` |
| `materialization.committed` | `materialization_id: SM-ID`, `commit_intent_id: Opaque`, `destination_object: Object`, `destination_identity_sigil: Sigil`, `verification: Verify`, `residual_staging_cleanup: ResidualStagingCleanup`, `execution_fence: Fence\|null` | `MATERIALIZATION`, `QUOTA` |
| `materialization.cleanup_started` | `materialization_id: SM-ID`, `destination_identity_sigil: Sigil`, `authorization_sigil: Sigil`, `clock: Clock` | `MATERIALIZATION`, `QUOTA` |
| `materialization.cleaned` | `materialization_id: SM-ID`, `destination_identity_sigil: Sigil`, `cleanup_evidence_sigil: Sigil`, `clock: Clock` | `MATERIALIZATION`, `QUOTA` |
| `materialization.cleanup_failed` | `materialization_id: SM-ID`, `destination_identity_sigil: Sigil`, `cleanup_evidence_sigil: Sigil`, `reason: Reason`, `clock: Clock` | `MATERIALIZATION`, `QUOTA` |
| `materialization.failed` | `materialization_id: SM-ID`, `reason: Reason`, `destination_staging_object: Object\|null`, `staging_state: "NOT_CREATED"\|"MISSING"\|"HELD_FOR_DISPOSITION"`, `residual_staging_cleanup: ResidualStagingCleanup`, `destination_object: Object\|null`, `destination_state: "NOT_CREATED"\|"MISSING"\|"HELD_FOR_DISPOSITION"`, `destination_cleanup: CleanupResult` | `MATERIALIZATION`, `QUOTA` |
| `materialization.quarantined` | `materialization_id: SM-ID`, `quarantine_id: SQ-ID`, `quarantine_event: EventRef`, `residual_staging_cleanup: ResidualStagingCleanup`, `reason: Reason` | `MATERIALIZATION`, `QUARANTINE`, `QUOTA` |
| `quarantine.intent_recorded` | `quarantine_id: SQ-ID`, `owner_kind: "TRANSFER_ATTEMPT"\|"MATERIALIZATION"`, `owner_id: Opaque`, `source_object: Object`, `destination_object: Object`, `reservation: ReservationRef`, `expected_blob_sigil: Sigil\|null`, `expected_size_bytes: U63\|null`, `reason: Reason` | `QUARANTINE`, `QUOTA`, and exactly one of `TRANSFER_ATTEMPT` or `MATERIALIZATION` selected by `owner_kind` |
| `quarantine.recorded` | `quarantine_id: SQ-ID`, `owner_kind: "TRANSFER_ATTEMPT"\|"MATERIALIZATION"`, `owner_id: Opaque`, `destination_object: Object`, `verification: Verify`, `source_cleanup: ResidualStagingCleanup` | `QUARANTINE`, `QUOTA`, and exactly one of `TRANSFER_ATTEMPT` or `MATERIALIZATION` selected by `owner_kind` |
| `quarantine.failed` | `quarantine_id: SQ-ID`, `owner_kind: "TRANSFER_ATTEMPT"\|"MATERIALIZATION"`, `owner_id: Opaque`, `source_object: Object\|null`, `source_cleanup: ResidualStagingCleanup`, `destination_object: Object\|null`, `destination_state: "NOT_CREATED"\|"MISSING"\|"HELD_FOR_DISPOSITION"`, `reason: Reason` | `QUARANTINE`, `QUOTA`, and exactly one of `TRANSFER_ATTEMPT` or `MATERIALIZATION` selected by `owner_kind` |
| `quarantine.reinspection_started` | `quarantine_id: SQ-ID`, `reinspection_id: Opaque`, `authorization_sigil: Sigil`, `reservation: ReservationRef`, `clock: Clock` | `QUARANTINE`, `QUOTA` |
| `quarantine.reinspection_completed` | `quarantine_id: SQ-ID`, `reinspection_id: Opaque`, `outcome: "REMAINS_HELD"\|"NEW_TRANSFER_PREPARED"`, `evidence_sigils: [Sigil]`, `new_transfer_id: ST-ID\|null` | `QUARANTINE`, `QUOTA` |

| Event type | Exact payload fields | Exact revisions |
| --- | --- | --- |
| `provenance.recorded` | `provenance: Ref`, `blob_sigil: Sigil`, `relation: ProvenanceRelation` | `PROVENANCE` |
| `retention.policy_registered` | `policy: Ref` | `RETENTION_POLICY` |
| `retention.hold_set` | `hold_id: SH-ID`, `target_kind: "BLOB"\|"REPLICA"\|"REFERENCE_SET"`, `target_id: Opaque`, `policy_id: SP-ID`, `authorization_sigil: Sigil` | `HOLD` |
| `retention.hold_released` | `hold_id: SH-ID`, `release_authority: HoldReleaseAuthority`, `authorization_sigil: Sigil`, `reason: Reason`, `clock: Clock` | `HOLD` |
| `reference_set.registered` | `reference_set_id: RS-ID`, `reference_set_sigil: Sigil`, `source_identity: Opaque`, `source_sigil: Sigil` | `REFERENCE_SET` |
| `canonical_reference.intent_recorded` | `reference_intent: Ref`, `expected_chronicle_head: ChronicleHeadRef`, `blob_sigils: [Sigil]`, `reference_set_sigils: [Sigil]`, `lifecycle_reservation: ReservationRef` | `REFERENCE_INTENT`, `QUOTA` |
| `canonical_reference.committed` | `reference_intent_id: RI-ID`, `chronicle_commit: ChronicleCommitRef` | `REFERENCE_INTENT`, `QUOTA` |
| `canonical_reference.released` | `reference_intent_id: RI-ID`, `release_kind: constant "ABORTED_BEFORE_CANONICAL_COMMIT"`, `chronicle_commit: constant null`, `abort_authority: CanonicalAbortAuthority`, `reason: Reason` | `REFERENCE_INTENT`, `QUOTA` |
| `gc.plan_created` | `gc_plan: Ref`, `root_snapshot_sigil: Sigil`, `closure_proof_sigil: Sigil`, `target_ids: [Opaque]` | `GC_PLAN` |
| `gc.plan_authorized` | `gc_plan_id: SG-ID`, `authorization_sigil: Sigil`, `authorized_target_ids: [Opaque]`, `expires_at: Timestamp`, `clock: Clock` | `GC_PLAN` |
| `gc.execution_started` | `gc_plan_id: SG-ID`, `root_revalidation_sigil: Sigil`, `clock: Clock` | `GC_PLAN` |
| `gc.target_skipped` | `gc_plan_id: SG-ID`, `target_id: Opaque`, `replica_id: SR-ID`, `backend_object: Object`, `reason: Reason`, `root_revalidation_sigil: Sigil` | `GC_PLAN` |
| `gc.target_deletion_started` | `gc_plan_id: SG-ID`, `target_id: Opaque`, `deletion_intent_id: Opaque`, `replica_id: SR-ID`, `backend_object: Object`, `root_revalidation_sigil: Sigil`, `authorization_sigil: Sigil`, `outcome_reservation: ReservationRef` | `GC_PLAN`, `REPLICA`, `BLOB`, `QUOTA` |
| `gc.target_deleted` | `gc_plan_id: SG-ID`, `target_id: Opaque`, `deletion_intent_id: Opaque`, `replica_id: SR-ID`, `backend_object: Object`, `deletion_evidence_sigil: Sigil`, `clock: Clock` | `GC_PLAN`, `REPLICA`, `BLOB`, `QUOTA` |
| `gc.target_failed` | `gc_plan_id: SG-ID`, `target_id: Opaque`, `deletion_intent_id: Opaque`, `replica_id: SR-ID`, `backend_object: Object`, `reason: Reason`, `clock: Clock` | `GC_PLAN`, `REPLICA`, `BLOB`, `QUOTA` |
| `gc.completed` | `gc_plan_id: SG-ID`, `deleted_target_ids: [Opaque]`, `skipped_target_ids: [Opaque]`, `failed_target_ids: [Opaque]`, `outcome_sigil: Sigil`, `clock: Clock` | `GC_PLAN` |
| `gc.aborted` | `gc_plan_id: SG-ID`, `reason: Reason`, `clock: Clock` | `GC_PLAN` |
| `disposition.authorized` | `disposition: Ref`, `target_kind: "STAGING"\|"MATERIALIZATION_STAGING"\|"MATERIALIZATION_DESTINATION"\|"QUARANTINE"`, `target_id: Opaque`, `target_object: Object`, `outcome_reservation: ReservationRef`, `clock: Clock` | `DISPOSITION`, `QUOTA` |
| `disposition.started` | `disposition_id: SD-ID`, `execution_intent_id: Opaque`, `target_kind: "STAGING"\|"MATERIALIZATION_STAGING"\|"MATERIALIZATION_DESTINATION"\|"QUARANTINE"`, `target_id: Opaque`, `target_object: Object`, `authorization_sigil: Sigil`, `clock: Clock` | `DISPOSITION`, plus `QUARANTINE` only for `QUARANTINE`; Transfer and Materialization lifecycle state remains terminal while the open intent records execution |
| `disposition.completed` | `disposition_id: SD-ID`, `execution_intent_id: Opaque`, `target_kind: "STAGING"\|"MATERIALIZATION_STAGING"\|"MATERIALIZATION_DESTINATION"\|"QUARANTINE"`, `target_id: Opaque`, `target_object: Object`, `deletion_evidence_sigil: Sigil`, `clock: Clock` | `DISPOSITION`, `QUOTA`, plus `TRANSFER_ATTEMPT` for `STAGING`, `MATERIALIZATION` for either materialization target, or `QUARANTINE` for `QUARANTINE` |
| `disposition.failed` | `disposition_id: SD-ID`, `execution_intent_id: Opaque\|null`, `target_kind: "STAGING"\|"MATERIALIZATION_STAGING"\|"MATERIALIZATION_DESTINATION"\|"QUARANTINE"`, `target_id: Opaque`, `target_object: Object`, `reason: Reason`, `clock: Clock` | pre-start expiry: `DISPOSITION`, `QUOTA`, with every target owner unchanged; post-start: those plus `QUARANTINE` only for `QUARANTINE`, while other target owners remain byte-for-byte unchanged |

The following cross-field rules are part of those Event Schema branches:

- A normal `storage.initialized` has null `tail_recovery`. A non-null value is
  legal only for the empty-prefix interrupted-initialization recovery branch
  below; each of its six fields equals the corresponding fixed Recovery Marker
  field byte-for-byte.
- In `transfer.prepared`, `transfer.record_id` equals the immutable Transfer
  request's `transfer_id`, `transfer_attempt.record_id` equals the immutable
  Attempt's `transfer_attempt_id`, and
  `transfer_attempt.transfer_id == transfer.record_id`. The payload
  Ref Sigils equal the two resolved records' self-Sigils, and the Reservation
  equals the Attempt's Reservation byte-for-byte. The payload fence equals
  `transfer.execution.fence` when that request has a `LEASED` execution
  context and is null otherwise.
- In `transfer.verification_started`, both IDs resolve the exact request and
  Attempt selected by `transfer.prepared`; the post-event Attempt's
  `transfer_id`, current `staging_object`, computed Blob Sigil, computed size,
  and execution fence equal the payload byte-for-byte.
  `verification_method` equals the immutable Transfer request's
  `verification_method` and is supported by its bound backend profile. In
  `replica.verification_started`, `replica_id` resolves the exact Replica,
  `backend_object` equals that Replica's `object` byte-for-byte, and `method`
  is supported by the Replica's bound backend profile.
- In `transfer.commit_intent_recorded`, the `commit_intent.reservation` equals
  the Attempt Reservation, its fence equals the request's current public fence,
  and its computed Blob equals the immediately preceding verified size and
  Sigil. `provisional_replica` names
  `artifact-replica/1.0`, has
  `replica_id == commit_intent.provisional_replica_id`, state `COMMITTING`,
  null verification, the same Blob, target object, backend, creator Attempt,
  and revision one. The Blob revision uses
  `commit_intent.computed_blob.blob_sigil`; the Replica revision uses the
  provisional ID. The Attempt's post-event `commit_intent` equals the complete
  payload object byte-for-byte and the new `TRANSFER_COMMIT` open intent is
  derived from this Event.
- Every post-intent Transfer terminal payload has
  `provisional_replica_id == attempt.commit_intent.provisional_replica_id`
  and `blob_sigil == attempt.commit_intent.computed_blob.blob_sigil`;
  `transfer.committed.size_bytes` also equals the intent's computed size.
  For `NEW_REPLICA`, `replica.record_id == provisional_replica_id`,
  `backend_object == commit_intent.target_object`, the supplied verification
  covers that exact generation and Blob, and the provisional Replica moves
  `COMMITTING -> AVAILABLE`;
  `provisional_target_absence_evidence_sigil` is null. For
  `DEDUPLICATED_REPLICA`, that evidence Sigil is non-null and authenticates
  exact-generation absence, and
  `replica.record_id != provisional_replica_id`; the selected record must
  already replay `AVAILABLE`, match the Blob and size, and have the same
  non-expired verification as the payload. More exactly,
  `payload.backend_object == selected_replica.object` and
  `payload.verification == selected_replica.verification` byte-for-byte; that
  verification's evidence authenticates the exact tuple
  `(backend_object.generation, blob_sigil, size_bytes)` carried by the Event
  and selected Replica. It receives no revision, while the provisional Replica
  alone moves `COMMITTING -> ABANDONED` with null verification. Failure,
  cancellation, and quarantine after intent likewise abandon that Replica. In
  each of those three Events the provisional ID,
  absence-evidence Sigil, and Blob Sigil are all null exactly when the Attempt
  has no commit intent; otherwise the ID and Blob have the equalities above
  and the evidence Sigil is non-null. All five post-intent terminal Schema
  branches remove the exact `TRANSFER_COMMIT` open intent. `ABANDONED` also
  means that the intent's exact provisional target generation is proved
  absent: DEDUP never created it, and a failure, cancellation, or quarantine
  either proves it was never created or conditionally removes only that exact
  unpublished generation under the durable commit intent. If absence cannot
  be authenticated, the Attempt remains `COMMITTING` in Recovery and the open
  intent and Reservation remain live.
- For `transfer.failed` and `transfer.cancelled`, `staging_state:
  NOT_CREATED` requires null `staging_object` and cleanup `NOT_REQUIRED`;
  `MISSING` requires the exact non-null last staged object and cleanup
  `CLEANED` for that object with absence evidence; and
  `HELD_FOR_DISPOSITION` requires the exact non-null last staged object and
  the identically named cleanup state and object. The Attempt record stores
  the payload cleanup byte-for-byte.
- `transfer.quarantined.residual_staging_cleanup` equals the referenced
  `quarantine_event` payload's `source_cleanup` byte-for-byte, and the
  terminal Attempt stores that same object. The EventRef must identify the
  exact preceding `quarantine.recorded` or `quarantine.failed` Event for the
  payload's `quarantine_id` and Transfer Attempt owner, whose source object is
  the exact last Transfer staging generation and never the provisional target
  object.
- In `materialization.committed`, `commit_intent_id` equals the replayed
  Materialization's `commit_intent.intent_id`;
  `destination_object == commit_intent.destination_object`,
  `destination_identity_sigil` equals both
  `commit_intent.destination_identity_sigil` and
  `materialization.destination_sigil`, and
  `execution_fence == commit_intent.execution_fence`, all byte-for-byte. The
  intent's `expected_blob.blob_sigil` equals
  `materialization.source_blob_sigil`, its size equals the exact selected
  source Replica size, and the payload destination has that non-null Blob
  Sigil and size. The payload `verification` equals
  `materialization.verification` byte-for-byte and authenticates the exact
  destination generation, Blob Sigil, and size in that destination object.
  No different destination generation or merely byte-equal object can satisfy
  this branch.
- `materialization.committed.residual_staging_cleanup` is terminal and names
  exactly the intent's staging object unless `NOT_REQUIRED`. The
  Materialization record stores it byte-for-byte. A failed Materialization
  uses the state matrix in the next rule.
  `materialization.quarantined.residual_staging_cleanup` equals the referenced
  `quarantine_event` payload's `source_cleanup` byte-for-byte, and the
  terminal Materialization stores that same object; the EventRef identifies
  the exact preceding `quarantine.recorded` or `quarantine.failed` Event for
  the payload's `quarantine_id` and Materialization owner, whose source object
  is the exact last materialization staging generation and never its final
  destination. Every
  Materialization terminal branch removes `MATERIALIZATION_COMMIT` when that
  open intent exists.
- In `materialization.failed`, each `NOT_CREATED` state requires its matching
  object null. Staging `MISSING` or `HELD_FOR_DISPOSITION` requires the exact
  non-null last staged generation and, after commit intent, that object equals
  the intent's staging object. A final-destination `MISSING` or
  `HELD_FOR_DISPOSITION` branch requires a commit intent and the exact
  non-null destination object from it; before intent, destination state is
  `NOT_CREATED`. Staging `NOT_CREATED` requires cleanup `NOT_REQUIRED`;
  staging `MISSING` requires `CLEANED` with absence evidence; and staging
  `HELD_FOR_DISPOSITION` requires the identically named cleanup state and
  object. The destination matrix is likewise exact: `NOT_CREATED` requires
  `destination_cleanup: NOT_REQUIRED`; `MISSING` requires `CLEANED` with
  absence evidence; and `HELD_FOR_DISPOSITION` requires `FAILED` with
  non-null evidence and a reason equal to the Event's reason. The
  Materialization record stores
  `destination_cleanup` byte-for-byte as its `cleanup`.
- In `quarantine.intent_recorded`, `expected_blob_sigil` and
  `expected_size_bytes` are either both null or both non-null. They are
  non-null exactly when replay of the owner supplies a complete authenticated
  expected Blob-and-size pair, and then equal that pair byte-for-byte; neither
  field may be synthesized from an unauthenticated partial observation. The
  null pair is legal only when no complete authenticated pair exists. When
  non-null, `expected_blob_sigil` equals both `source_object.blob_sigil` and
  `destination_object.blob_sigil`, while `expected_size_bytes` equals both
  `source_object.size_bytes` and `destination_object.size_bytes`; with a null
  pair the intent destination's Blob Sigil is null.
  `TRANSFER_ATTEMPT` selects an `SA-ID` owner and a `source_object` equal to
  that Attempt's exact current staging object. `MATERIALIZATION` selects an
  `SM-ID` owner and a source equal to that Materialization's exact current
  destination-staging object. In both branches `destination_object` is the
  fresh, distinct, coordinator-owned Quarantine identity and generation
  covered by the Reservation; it cannot name the source, a pre-existing
  object, or a pathname-derived substitute.
- `quarantine.recorded` and `quarantine.failed` repeat the intent's
  `quarantine_id`, owner kind, and owner ID exactly and store `source_cleanup`
  byte-for-byte in the Quarantine projection. `NOT_REQUIRED` proves the
  intent-bound source generation is absent as a consequence of the atomic
  move; `CLEANED` proves its exact conditional removal; and
  `HELD_FOR_DISPOSITION` proves it remains present and inaccessible.
  `PENDING` or `FAILED` cannot appear in either terminal Event. The referenced
  owner terminal Event repeats the same cleanup object. Both Quarantine
  terminal branches remove `QUARANTINE_MOVE`.
- `quarantine.recorded.destination_object` has the same backend ID, object
  identity, locator, and generation as the intent destination byte-for-byte,
  and its exact size also equals the intent destination size. Its Blob Sigil
  is non-null, and its verification evidence authenticates that exact
  destination identity and generation, Blob Sigil, and size. When the
  expected pair is non-null, the terminal Blob Sigil and size equal it; when
  the pair is null, this terminal verification is the first authenticated
  complete pair and does not retroactively alter the intent's null Blob
  field. The Event is invalid if verification covers another generation,
  only a prefix, or bytes with a different size or Blob Sigil.
- In `quarantine.failed`, null `source_object` is legal only with
  `source_cleanup: NOT_REQUIRED`; otherwise the source object equals
  both the intent source and `source_cleanup.staging_object` byte-for-byte.
  `destination_state: NOT_CREATED` alone has null `destination_object`;
  `MISSING` and `HELD_FOR_DISPOSITION` carry the exact non-null intent
  destination identity, generation, Blob Sigil, and size, with the latter
  consuming its charged Quarantine usage. A failed branch carries no success
  verification and therefore cannot adopt its destination as verified
  Quarantine content.
- In `provenance.recorded`, `provenance` resolves the exact immutable
  `artifact-provenance/1.0` record; its Ref ID and Sigil equal that record's
  `provenance_id` and `record_sigil`. The payload's `blob_sigil` equals the
  resolved record's `blob.blob_sigil`, and its `relation` equals the resolved
  record's `relation`, all byte-for-byte.
- Every `retention.hold_set` is one of two closed Phase 3 branches and targets
  a registered `REFERENCE_SET`. For an RFC-0012 execution ESM, its payload,
  registered Set, registration Event, ESM plan, neutral policy, and Event ID
  validate byte-for-byte, and `authorization_sigil` is exactly:

  ```text
  Sigil(["execution-root-hold-set-authorization/1.0",
         {manifest_id, manifest_sigil},
         {reference_set_id, reference_set_sigil,
          registration_event: <exact EventRef>},
         {hold_id, hold_set_event_id},
         {policy_id, policy_sigil}])
  ```

  For an RFC-0014 operational root, no root or activation Event exists yet.
  The payload instead resolves and validates the already-durable
  `patch-operational-root-plan/1.0`: its source control record, registered Set,
  registration Event, preallocated Promotion Event/root/hold/Event IDs,
  policy tuple, authorization kind, content-derived plan/root identities, and
  self-Sigil all match. `authorization_sigil` uses RFC-0014's closed formula
  over the plan pair, exact Set/registration Event, hold/Event IDs, and policy
  pair; its subject is the plan ID. Admission must not look up or infer a
  future Promotion Event or live OperationalRoot. An alternate plan, target
  kind, arbitrary authorization Sigil, reused activation/hold slot, or third
  Phase 3 hold-set branch is invalid.
- Every `retention.hold_released` resolves one exact `ACTIVE` hold and advances
  only that projection to `RELEASED`. Its `release_authority` is the complete
  closed union above; no reason text or bare Sigil is authority.

  In `EXECUTION_ROOT`, the `ControlRef` names
  `execution-root-hold-release-authorization/1.0`, its `record_id` is exactly:

  ```text
  "EHR-" + UPPER_HEX(SHA256(canonical_json(
    ["execution-root-hold-release-authorization-id/1.0", hold_id])))
  ```

  and it resolves the immutable RFC-0012 EHR whose
  `release_authorization_sigil == authorization.record_sigil ==
  payload.authorization_sigil`. The EHR's complete Storage root, neutral
  policy, and hold-set authorization equal this hold and its creation chain.
  RFC-0012 replay through the exact Head in its basis validates the sole
  activation/inactivation or activation absence:

  - `OWNER_TERMINAL` is legal only for `JOB_INPUT` or `ATTEMPT_INPUT`; reason
    code is `EXECUTION_ROOT_OWNER_TERMINATED`, and trusted `clock.utc` is at
    or after the named owner-terminal Event's `recorded_at`;
  - `ORPHAN_ABORT` is legal only when the gate-held verified Head proves the
    sole activation absent and the EHR permanently vetoes later activation;
    reason code is `EXECUTION_ROOT_ORPHAN_ABORTED`; clock is trusted but
    grants no release authority; and
  - `OUTPUT_DEADLINE` is legal only for an `ATTEMPT_OUTPUT` schedule with
    `EXACT` or `OVERFLOW_FAIL_CLOSED`; reason code is
    `EXECUTION_HOLD_LIFETIME_EXPIRED`, the schedule's Job terminal Event and
    activation Event match the EHR, and trusted `clock.utc` is at or after
    the immutable `release_due_at`.

  For all three execution branches, `reason.evidence_sigils` is the sorted
  unique union of the EHR Sigil, ESM Sigil, Reference Set Sigil, hold-set
  Event Sigil, and every basis activation, terminal, and verified-Head Sigil
  present in that branch. A missing, extra, or alternate evidence Sigil is
  invalid. For `OUTPUT_DEADLINE`, RFC-0012's matching
  `storage_root.hold_release_observed` additionally carries the complete
  schedule, EHR ID/Sigil, and exact four-field Storage `EventRef`.

  In `PATCH_OPERATIONAL_ROOT`, `payload.authorization_sigil` equals the
  branch's `authority_sigil`, reason code is
  `OPERATIONAL_ROOT_TERMINATED`, and the installed
  `benchwork.patch-operational-root-release/1.1` validator first resolves the
  exact RootPlan and
  `patch-operational-root-release-evidence/1.0` record, then replays the exact
  RFC-0014 Promotion Journal through `inactivation_event` and this Storage
  Journal through the evidence's pre-release prefix. The plan equals the
  original hold-set plan and activation root; the release record equals the
  authority's root, Set, hold/Event, activation/inactivation Events,
  condition, terminal authority, policy, and prefixes byte-for-byte. The
  validator enforces the closed canonical-completion,
  `TERMINAL_GUARD | NO_GUARD_ALLOCATED |
  NOT_APPLICABLE_JOURNAL_SUFFIX` mapping, the embedded patch-specific
  abandonment disposition, trusted clock and checked retention formula,
  healthy suffix integrity, and both exact empty relevant-intent sets.
  In particular, `retention_completion.inactivation_recorded_at` equals the
  replayed inactivation Event's `recorded_at` byte-for-byte; the Promotion
  prefix ends exactly at that Event ID/sequence/Sigil; and an Attempt terminal
  Event, its exact terminal guard Event when present, and the inactivation
  Event occur in that order. The Storage prefix contains the exact hold-set
  Event and, for a canonical branch, the exact
  `canonical_reference.committed` Event while the hold still projects
  `ACTIVE`. That committed Event resolves the same immutable Reference Intent
  and Reference Set; its complete EventRef equals both
  `release_evidence.canonical_completion.commit_event` and the replayed
  `canonical.receipt-observed.canonical_commit_event` byte-for-byte. This
  payload-carried backward link, not cross-journal timestamps or a later Head
  lookup, proves that the canonical commit was durable before Promotion
  inactivation.
  For abandonment, the embedded and release-evidence guard completions are
  byte-identical; their bound guard Ref equals the enclosing Record and
  Recovery Intent guard Refs byte-for-byte, and its ID equals
  `recovery.abandoned.guard_id`; the guard Event follows
  `recovery.abandoned` and precedes Record construction. A
  generic RFC-0013 disposition, bare Sigil, future-root lookup, uncertain
  clock, open intent, branch substitution, or incomplete replay retains the
  hold.

  `reason.evidence_sigils` is only an audit index and is exactly the sorted
  unique set of the authority Sigil, release-evidence record Sigil,
  operational-root Sigil, RootPlan Sigil, Reference Set Sigil, policy Sigil,
  hold-set/activation/inactivation Event Sigils, terminal-authority record
  Sigil, and validator Sigil. A missing or extra value is invalid, but even an
  exact index never substitutes for resolving and replaying the release
  record. The Event's `clock` equals the evidence's exact trusted
  `ClockRef`.

  Retry resolves the same unique release Event rather than appending another.
  No branch releases a different hold or authorizes deletion.
- A `gc.target_deletion_started.deletion_intent_id` is fresh and is repeated
  byte-for-byte by its one terminal target Event. It creates `GC_DELETE`; that
  intent is removed only by `gc.target_deleted` or `gc.target_failed`.
- A pre-start `disposition.failed` is legal only from `AUTHORIZED`, with
  `execution_intent_id: null`, `reason.code: DISPOSITION_EXPIRED`, and an
  authenticated clock proving the immutable authorization due. It changes
  only `DISPOSITION` and `QUOTA`, settles the active outcome Reservation,
  creates or removes no `OpenIntentProjection`, performs no backend or target
  side effect, and leaves every target owner byte-for-byte unchanged.
  Otherwise `disposition.started.execution_intent_id` is fresh, is repeated
  non-null by its terminal Event, creates `DISPOSITION`, and is removed only
  by `disposition.completed` or post-start `disposition.failed`. In both
  failed branches, the disposition record, authorization Event, target kind,
  target ID, target generation, and target object are identical; the
  post-start branch additionally matches the started Event and open intent
  byte-for-byte.

The following is the complete quota-effect program for every event whose
revision row contains `QUOTA`. “Settle” always means exactly one `SETTLE`
effect for the named prior reservation. Its claims must cover the canonical
encoded event frame and every control record made durable for that event;
claims not consumed by the stated durable outcome are released. No other
event may create, settle, retain, or remove quota usage.

| Event or branch | Exact quota effects |
| --- | --- |
| `storage.initialized` | One `INITIALIZE` for each of the twelve legal class/dimension pairs. The effect snapshots equal `payload.quota_snapshots` byte-for-byte, are ordered by class/dimension, and start with `used: 0`, `reserved: 0`, and `pressure_state: CLEAR`; each produces the distinct matching `quota-counter:<class>:<dimension>` revision. Format and fixed system-reserve bytes are outside project quota. |
| `quota.pressure_entered` | One `PRESSURE` with `CLEAR -> PRESSURED`; its complete snapshot equals the payload snapshot and the replayed post-event counter. |
| `quota.pressure_cleared` | One `PRESSURE` with `PRESSURED -> CLEAR`; its complete snapshot equals the payload snapshot and the replayed post-event counter. |
| `transfer.prepared` | One `RESERVE` whose reservation equals the payload and attempt record, owner is `(TRANSFER_ATTEMPT, transfer_attempt_id)`, and purpose is `PAYLOAD_LIFECYCLE`. |
| `transfer.committed` | Settle the attempt reservation to `SETTLED`. A `NEW_REPLICA` consumes the exact `COMMITTED` byte/object claims for the selected durable Replica; `DEDUPLICATED_REPLICA` consumes none. Either branch additionally consumes exact `STAGING` claims only for a residual object in `HELD_FOR_DISPOSITION`, plus its used Journal/control-record claims. |
| `transfer.failed` or `transfer.cancelled` | Settle the attempt reservation to `SETTLED`. It consumes exact `STAGING` byte/object claims iff `staging_state` is `HELD_FOR_DISPOSITION`, consumes its used Journal/control-record claims, and releases every other claim. |
| `transfer.quarantined` | Settle the attempt reservation to `SETTLED`, consuming its used Journal/control-record claims. It additionally consumes the exact `STAGING` byte/object claims iff the referenced Quarantine Event's `source_cleanup` is `HELD_FOR_DISPOSITION`; otherwise it releases all payload claims. The independent Quarantine reservation owns only the verified destination bytes. |
| `materialization.prepared` | One `RESERVE` whose reservation equals the payload and materialization record, owner is `(MATERIALIZATION, materialization_id)`, and purpose is `PAYLOAD_LIFECYCLE`. |
| `materialization.committed` | Settle the materialization reservation to `RETAINED`, consuming the exact durable destination as `MATERIALIZATION` byte/object usage plus the event's Journal/control-record claims. It also consumes exact `STAGING` byte/object usage iff `residual_staging_cleanup` is `HELD_FOR_DISPOSITION`; otherwise the staging claims are released. Remaining claims are non-empty and `retained_for_event_types` is exactly `[materialization.cleanup_started]`; a later residual disposition obtains its own outcome Reservation and does not borrow this cleanup share. |
| `materialization.cleanup_started` | Settle the retained reservation to `RETAINED`, consuming the event's Journal/control-record claims. Remaining claims are non-empty and `retained_for_event_types` is exactly `[materialization.cleaned, materialization.cleanup_failed]` in enum order. |
| `materialization.cleaned` | Settle the retained reservation to `SETTLED`, consuming its final Journal/control-record claims, and add one `USAGE_REMOVED` per non-zero `MATERIALIZATION` destination dimension physically removed by this event. A separately retained staging residual remains owned by its exact disposition path and is not removed here. |
| `materialization.cleanup_failed` | Settle the retained reservation to `SETTLED`, consuming its final Journal/control-record claims and removing no destination usage. The failed exact destination remains charged as `MATERIALIZATION`; Phase 3 has no implicit cleanup retry or release. |
| `materialization.failed` | Settle the active reservation to `SETTLED`. It consumes exact `STAGING` and/or `MATERIALIZATION` byte/object claims for each object whose matching state is `HELD_FOR_DISPOSITION`, consumes its used Journal/control-record claims, and releases all other claims. |
| `materialization.quarantined` | Settle the active reservation to `SETTLED`, consuming its used Journal/control-record claims and exact `STAGING` source byte/object claims iff the referenced Quarantine Event's `source_cleanup` is `HELD_FOR_DISPOSITION`; otherwise it releases those source claims. The independent Quarantine reservation owns only the verified destination bytes. A final Materialization destination is never the source of this branch. |
| `quarantine.intent_recorded` | One `RESERVE` equal to the payload reservation, owner `(QUARANTINE, quarantine_id)`, purpose `QUARANTINE_MOVE`. |
| `quarantine.recorded` | Settle that reservation to `SETTLED`, consuming the exact durable destination as `QUARANTINE` byte/object usage and its used Journal/control-record claims. |
| `quarantine.failed` | Settle that reservation to `SETTLED`. It consumes exact `QUARANTINE` byte/object usage iff `destination_state` is `HELD_FOR_DISPOSITION`, consumes its used Journal/control-record claims, and releases every other claim. |
| `quarantine.reinspection_started` | One `RESERVE` equal to the payload reservation, owner `(QUARANTINE, reinspection_id)`, purpose `TERMINAL_OUTCOME`. |
| `quarantine.reinspection_completed` | Settle the matching reinspection reservation to `SETTLED`, consuming only its used Journal/control-record claims. A new Transfer has its own reservation. |
| `canonical_reference.intent_recorded` | One `RESERVE` equal to `lifecycle_reservation`, owner `(CANONICAL_REFERENCE, reference_intent_id)`, purpose `CANONICAL_PIN_LIFECYCLE`. |
| `canonical_reference.committed` | Settle the active intent reservation to `SETTLED`, consuming the commit Event's Journal/control-record claims and releasing every unused claim. A committed v1 pin has no outbound release Event and therefore retains no future-event Reservation. |
| `canonical_reference.released` | Settle only the active uncommitted-intent reservation to `SETTLED`, consuming its abort-release Journal/control-record claims and releasing all unused claims. |
| `gc.target_deletion_started` | One `RESERVE` equal to `outcome_reservation`, owner `(GC_TARGET, target_id)`, purpose `DELETION_OUTCOME`. |
| `gc.target_deleted` | Settle the target reservation to `SETTLED`, consuming its used Journal/control-record claims, and add one `USAGE_REMOVED` per non-zero `COMMITTED` dimension of the conditionally deleted Replica generation. |
| `gc.target_failed` | Settle the target reservation to `SETTLED`, consuming its used Journal/control-record claims, releasing unused claims, and removing no committed usage. |
| `disposition.authorized` | One `RESERVE` equal to `outcome_reservation`, owner `(DISPOSITION, disposition_id)`, purpose `DELETION_OUTCOME`. |
| `disposition.completed` | Settle the disposition reservation to `SETTLED`, consuming its used Journal/control-record claims, and add one `USAGE_REMOVED` per non-zero dimension of the exact usage selected by `target_kind`: `STAGING` and `MATERIALIZATION_STAGING` remove `STAGING`, `MATERIALIZATION_DESTINATION` removes `MATERIALIZATION`, and `QUARANTINE` removes `QUARANTINE`. |
| `disposition.failed` | In both the pre-start null-intent expiry branch and every post-start non-null-intent branch, settle the disposition reservation to `SETTLED`, consume its used Journal/control-record claims, release unused claims, and remove no target usage. |

The capacity source for every Event is closed by the following 61-row table.
`SYSTEM(C)` means that the Event frame and every newly durable control record
referred to by that Event consume class `C` from `system_reserve_limits`.
`NEW(owner)` means the Reservation created by that same Event is validated and
physically withheld before the frame or any referred control record is
written. `ACTIVE(owner)` and `RETAINED(owner)` require the named replayed
Reservation and consume only its still-unconsumed `capacity_plan` counts and
claims. An existing immutable record merely resolved by an Event consumes no
new capacity. No Event frame, new control record, or evidence record may be
split across sources or fall back to another source.

| Event type | Exact capacity source |
| --- | --- |
| `storage.initialized` | `SYSTEM(INITIALIZATION)` when `tail_recovery` is null; `SYSTEM(RECOVERY)` otherwise |
| `storage.activation_completed` | `SYSTEM(INITIALIZATION)` |
| `storage.epoch_started` | `SYSTEM(COORDINATOR_LIVENESS)` outside Recovery; `SYSTEM(RECOVERY)` inside Recovery |
| `storage.clock_uncertain` | `SYSTEM(CLOCK_PRESSURE)` |
| `storage.clock_restored` | `SYSTEM(CLOCK_PRESSURE)` |
| `storage.recovery_started` | frame and generic recovery records: `SYSTEM(RECOVERY)`; each operation-specific observation record: that open intent's `ACTIVE` or `RETAINED` owner |
| `storage.recovery_completed` | `SYSTEM(RECOVERY)` |
| `storage.message_rejected` | `SYSTEM(CLOCK_PRESSURE)` |
| `legacy_v1.protection_registered` | `SYSTEM(INITIALIZATION)` |
| `legacy_v1.protection_failed` | `SYSTEM(INITIALIZATION)` |
| `quota.pressure_entered` | `SYSTEM(CLOCK_PRESSURE)` |
| `quota.pressure_cleared` | `SYSTEM(CLOCK_PRESSURE)` |
| `transfer.prepared` | `NEW(TRANSFER_ATTEMPT)` |
| `transfer.streaming_started` | `ACTIVE(TRANSFER_ATTEMPT)` |
| `transfer.verification_started` | `ACTIVE(TRANSFER_ATTEMPT)` |
| `transfer.commit_intent_recorded` | `ACTIVE(TRANSFER_ATTEMPT)` |
| `transfer.committed` | `ACTIVE(TRANSFER_ATTEMPT)`, settled by this Event |
| `transfer.failed` | `ACTIVE(TRANSFER_ATTEMPT)`, settled by this Event |
| `transfer.cancelled` | `ACTIVE(TRANSFER_ATTEMPT)`, settled by this Event |
| `transfer.quarantined` | `ACTIVE(TRANSFER_ATTEMPT)`, settled by this Event |
| `replica.verification_started` | `SYSTEM(VERIFICATION_INCIDENT)` |
| `replica.verified` | `SYSTEM(VERIFICATION_INCIDENT)` |
| `replica.verification_expired` | `SYSTEM(VERIFICATION_INCIDENT)` |
| `replica.corrupt` | `SYSTEM(VERIFICATION_INCIDENT)` |
| `blob.incident_recorded` | `SYSTEM(VERIFICATION_INCIDENT)` |
| `materialization.prepared` | `NEW(MATERIALIZATION)` |
| `materialization.streaming_started` | `ACTIVE(MATERIALIZATION)` |
| `materialization.verification_started` | `ACTIVE(MATERIALIZATION)` |
| `materialization.commit_intent_recorded` | `ACTIVE(MATERIALIZATION)` |
| `materialization.committed` | `ACTIVE(MATERIALIZATION)`, retained by this Event |
| `materialization.cleanup_started` | `RETAINED(MATERIALIZATION)` |
| `materialization.cleaned` | `RETAINED(MATERIALIZATION)`, settled by this Event |
| `materialization.cleanup_failed` | `RETAINED(MATERIALIZATION)`, settled by this Event |
| `materialization.failed` | `ACTIVE(MATERIALIZATION)`, settled by this Event |
| `materialization.quarantined` | `ACTIVE(MATERIALIZATION)`, settled by this Event |
| `quarantine.intent_recorded` | `NEW(QUARANTINE)` |
| `quarantine.recorded` | `ACTIVE(QUARANTINE)`, settled by this Event |
| `quarantine.failed` | `ACTIVE(QUARANTINE)`, settled by this Event |
| `quarantine.reinspection_started` | `NEW(QUARANTINE)` for the reinspection identity |
| `quarantine.reinspection_completed` | `ACTIVE(QUARANTINE)` for the reinspection identity, settled by this Event |
| `provenance.recorded` | `SYSTEM(CATALOG_ADMINISTRATION)` |
| `retention.policy_registered` | `SYSTEM(RETENTION_REFERENCE)` |
| `retention.hold_set` | `SYSTEM(RETENTION_REFERENCE)` |
| `retention.hold_released` | `SYSTEM(RETENTION_REFERENCE)` |
| `reference_set.registered` | `SYSTEM(RETENTION_REFERENCE)` |
| `canonical_reference.intent_recorded` | `NEW(CANONICAL_REFERENCE)` |
| `canonical_reference.committed` | `ACTIVE(CANONICAL_REFERENCE)`, settled by this Event |
| `canonical_reference.released` | `ACTIVE(CANONICAL_REFERENCE)`, settled by this Event |
| `gc.plan_created` | `SYSTEM(GC_ADMINISTRATION)` |
| `gc.plan_authorized` | `SYSTEM(GC_ADMINISTRATION)` |
| `gc.execution_started` | `SYSTEM(GC_ADMINISTRATION)` |
| `gc.target_skipped` | `SYSTEM(GC_ADMINISTRATION)` |
| `gc.target_deletion_started` | `NEW(GC_TARGET)` |
| `gc.target_deleted` | `ACTIVE(GC_TARGET)`, settled by this Event |
| `gc.target_failed` | `ACTIVE(GC_TARGET)`, settled by this Event |
| `gc.completed` | `SYSTEM(GC_ADMINISTRATION)` |
| `gc.aborted` | `SYSTEM(GC_ADMINISTRATION)` |
| `disposition.authorized` | `NEW(DISPOSITION)` |
| `disposition.started` | `ACTIVE(DISPOSITION)` |
| `disposition.completed` | `ACTIVE(DISPOSITION)`, settled by this Event |
| `disposition.failed` | `ACTIVE(DISPOSITION)`, settled by this Event in either the pre-start or post-start branch |

The exact `allowed_event_types` for an operation Reservation is the subset
named for its owner by this table, further narrowed at Reservation creation to
the paths reachable from the immutable request and policy; it never changes
after creation. In particular, the only owner-reserved
non-`QUOTA` intermediate Events are
`transfer.streaming_started`, `transfer.verification_started`,
`transfer.commit_intent_recorded`, `materialization.streaming_started`,
`materialization.verification_started`,
`materialization.commit_intent_recorded`, and `disposition.started`.
Every other non-`QUOTA` Event is assigned to the explicit `SYSTEM` class above
or consumes an already active/retained owner Reservation as a terminal
transition. A conformance check derives the enum set from this table and
requires exact equality with both the Event enum and Event payload table.

For each `SystemReserveLimit c`, checked arithmetic defines:

```text
class_journal_bytes(c) =
    c.max_event_frame_count * c.max_event_frame_bytes
class_control_bytes(c) =
    c.max_control_record_count * c.max_control_record_bytes
class_recovery_bytes(c) =
    c.max_recovery_evidence_count * c.max_recovery_evidence_bytes

required_system_journal_bytes = sum_c class_journal_bytes(c)
required_system_control_record_bytes = sum_c class_control_bytes(c)
required_system_recovery_bytes = sum_c class_recovery_bytes(c)
```

Count minima are also executable rather than operator guesses. For every
reachable State `s` under the profile's collection and concurrency bounds,
conformance enumerates each open system-funded workflow and takes the
worst-case remaining legal branch of its closed state machine:

```text
terminal_event_min(c) =
  max_s sum_{workflow w in s, class(w)=c} remaining_event_frames(w)
terminal_control_min(c) =
  max_s sum_{workflow w in s, class(w)=c} remaining_control_records(w)
terminal_recovery_min(c) =
  max_s sum_{workflow w in s, class(w)=c} remaining_evidence_records(w)
```

For `INITIALIZATION`, each minimum additionally includes the greater bootstrap
demand for `storage.initialized`, `storage.activation_completed`, and exactly
one legacy-protection outcome per bounded preflight entry. For `RECOVERY`, it
includes the complete tail-marker, original-suffix, Event-seed,
prepared-template, `max_tail_recovery_retries` retry-evidence, epoch, and
completion path.
Each installed count is at least its matching minimum. A profile whose counts
are positive but cannot escrow these maxima is rejected before its first
Event; it cannot defer that failure until a terminal frame is needed.

Every class has positive frame count and frame size. `RECOVERY` additionally
has positive control-record and recovery-evidence counts; every class assigned
an Event that can create a control record has positive control-record count.
The three installed backend limits are strictly positive and respectively at
least the three computed totals. Any multiplication or sum overflow, zero
in a count required positive by the preceding rules, event-count exhaustion,
per-item bound violation, or installed limit below its computed requirement
rejects the backend profile before
initialization. System usage is a monotone replay fold by `(reserve_class,
kind, sequence-or-record-sigil)`; Doctor recomputes all three counts and byte
totals. Reaching a declared lifetime maximum closes caller mutation admission
before the next write and requires a new versioned backend profile with added
physical capacity; it never borrows project quota or another system class.

For a system-funded Event that opens a nonterminal workflow—initialization,
Replica verification, a hold-release path, GC planning or execution, clock
Recovery, or Storage Recovery—admission also escrows that class's exact
worst-case remaining Event, control-record, and evidence counts from the closed
state machine and profile bounds. The replay fold tracks
`consumed + escrowed` per class even though this administrative ledger is
derived rather than a project quota counter. An unrelated system Event cannot
consume escrow. A matching terminal Event converts its actual lengths to
consumed and releases only unused escrow; Recovery preserves it. Thus the
positive system reserve guarantees all already opened administrative
workflows can reach a legal terminal or recoverable state, rather than merely
admitting their first frame.

Tail marker, original suffix, recovery-event seed, prepared-frame template,
retry suffix, and generic recovery completion evidence always consume
`SYSTEM(RECOVERY)`. Evidence that classifies or terminalizes one particular
Transfer, Materialization, Quarantine, GC target, disposition, or canonical
intent consumes that owner's `max_recovery_evidence_count` and control-record
claim. The system Recovery frame may refer to those already durable
owner-charged records, but cannot pay for them.

All object and byte amounts above come from the exact verified
`BackendObjectRef`, not a later listing. Journal and control-record amounts
come from their canonical durable byte lengths. The sum of `used + reserved`
for each legal counter must equal the deterministic fold of initialization
and all later effects; backend inventory is only a reconciliation claim. An
expired active operation is terminalized by its owning failure, cancellation,
or recovery event, which performs the mapped settlement. There is no generic
reservation-expiry event that could release capacity while its owner or bytes
remain live. A committed canonical pin has no expiry.

Every type has one closed payload branch. A rejected message can be recorded
only after its envelope is safe and bounded enough to append; otherwise the
coordinator rejects it without copying untrusted content into the journal.
Adding, renaming, or changing the meaning of an event requires a new Schema
and replay version.

### Exhaustive state machines

Store transitions are:

```text
NONE -> INITIALIZING -> ACTIVE
          |              |
          v              v
       RECOVERING <------
          |       |
          v       v
   INITIALIZING  ACTIVE
```

`storage.initialized` enters `INITIALIZING`;
`storage.activation_completed` alone enters `ACTIVE`.
`storage.recovery_started` enters `RECOVERING` from either nonterminal store
status and freezes that exact origin. `storage.recovery_completed` returns
only to the frozen origin, so recovery during migration cannot accidentally
activate an incompletely protected store. While already `RECOVERING`, a
process re-crash appends `storage.epoch_started` for the same
`active_recovery_id`, preserves the origin and unresolved intents, and resumes
that recovery; it never appends a second `storage.recovery_started`.
`storage.epoch_started` outside recovery has null active-recovery identity and
must have null `tail_recovery`; inside recovery its active identity is
non-null and `tail_recovery` is non-null exactly when that restart repaired an
interrupted final frame. It does not change `INITIALIZING` or `ACTIVE`.
`INTEGRITY_FAILURE` is a
fail-closed verifier result rather than an event appended to a chain that
cannot be trusted.

The independent clock gate is `TRUSTED -> UNCERTAIN -> TRUSTED`, driven by
`storage.clock_uncertain` and `storage.clock_restored`. Clock events do not
change store status. While `UNCERTAIN`, the coordinator issues no new write
handle, finalizes no Transfer, expires no hold or authorization, releases no
reservation based on time, and performs no disposition or GC. It may retain
bytes, revoke access, run bounded verification, and record non-time-based
failure evidence.

Transfer-attempt transitions are:

```text
none -> PREPARED -> STREAMING -> VERIFYING -> COMMITTING -> COMMITTED
              \          \            \             \
               +----------+------------+-------------+
                              |
                              v
                  FAILED | CANCELLED | QUARANTINED
```

The corresponding events are the `transfer.*` events above.
`transfer.commit_intent_recorded` also creates a provisional Replica in
`COMMITTING`, with the intent's explicit provisional ID and null verification,
and creates the exact `TRANSFER_COMMIT` open-intent projection.
`transfer.committed` atomically makes the Transfer terminal. `NEW_REPLICA`
makes that provisional Replica `AVAILABLE` with the terminal verification and
selects the same ID. `DEDUPLICATED_REPLICA` verifies and selects a distinct
pre-existing `AVAILABLE` Replica without revising it, and makes only the
provisional Replica `ABANDONED`. Failure, cancellation, or quarantine after
intent also makes the provisional Replica `ABANDONED`; it is never selectable.
Every post-intent terminal branch removes the exact open intent.

Replica transitions are:

```text
none -> COMMITTING -> AVAILABLE -> STALE
          |              |          |
          v              v          v
      ABANDONED      VERIFYING <- STALE
                         |
                         +-> AVAILABLE | CORRUPT

AVAILABLE | STALE | CORRUPT | DELETE_FAILED
                  \                   /
                   -> DELETING -> DELETED | DELETE_FAILED
```

Only a verified Transfer can first enter `AVAILABLE`. Verification events
drive the `VERIFYING` branch. `replica.verification_expired` deterministically
moves an `AVAILABLE` Replica to `STALE` at its recorded due time; revalidation
uses `STALE -> VERIFYING -> AVAILABLE | CORRUPT`. Only an authorized GC target
can enter `DELETING`, and the `gc.target_*` event atomically updates both
target and Replica. A failed delete is ineligible until a later explicit
reconcile and new GC plan.

Materialization transitions are:

```text
none -> PREPARED -> STREAMING -> VERIFYING -> COMMITTING -> AVAILABLE
          |           |            |             |             |
          +-----------+------------+-------------+             v
                      |                                   CLEANING
                      v                                     |
             FAILED | QUARANTINED                  CLEANED | CLEANUP_FAILED
```

A materialization that fails verification never becomes visible at its final
destination. `materialization.commit_intent_recorded` is the sole transition
into `COMMITTING` and is durable before any final-destination create or rename.
It also creates `MATERIALIZATION_COMMIT`. Cleanup failure remains distinct from
successful use. Before a terminal Event, every intent-owned residual staging
generation is proven absent, conditionally cleaned, or retained exactly as
`HELD_FOR_DISPOSITION`; terminalization removes the open intent.

Quarantine bytes follow
`INTENT_RECORDED -> HELD -> INSPECTING -> HELD`, with
`INTENT_RECORDED -> FAILED` when exact recovery proves that isolation cannot
complete. Successful reinspection starts a new Transfer and does not change
the failed original Transfer.
`quarantine.intent_recorded` creates `INTENT_RECORDED` before any backend move
and binds the source staging generation, destination Quarantine identity and
generation, exact reserved bytes and objects, expected Sigil and size when
known, and recovery preconditions. `quarantine.recorded` enters `HELD` only
after the moved bytes and destination generation are durable and verified.
Authorized disposal follows
`HELD | FAILED | DISPOSAL_FAILED -> DISPOSING -> DISPOSED |
DISPOSAL_FAILED`. A new
disposition has its own
`AUTHORIZED -> FAILED` pre-start expiry branch or
`AUTHORIZED -> EXECUTING -> COMPLETED | FAILED` execution branch.
The original `quarantine.recorded` or `quarantine.failed` Event remains
resolvable through every later state. A `DISPOSAL_FAILED` state descended
from `quarantine.recorded` may be treated as retained isolation only when the
exact failed-disposition observation proves that same verified destination
generation still present and isolated. A `DISPOSAL_FAILED` state descended
from `quarantine.failed` remains terminal negative evidence and never gains a
success verification or eligible Blob/Replica status.

A failed Transfer whose bytes cannot obtain a Quarantine reservation does not
create a Quarantine record and does not claim that bytes vanished. Its staging
projection enters `HELD_FOR_DISPOSITION`, keeps its exact staging generation
and quota charge, and blocks new admission until an exact authorized
disposition removes it or capacity becomes available for a new write-ahead
Quarantine intent.

A GC plan follows
`DRAFT -> AUTHORIZED -> EXECUTING -> COMPLETED | PARTIAL | ABORTED`. Each
target independently follows
`PLANNED -> SKIPPED | DELETING -> DELETED | FAILED`. Target failure cannot be
rewritten as deletion, and a retry requires a new plan or an explicitly
versioned continuation bound to the unchanged plan and current target.

Retention policies and Reference Sets are registered once and immutable. Holds
follow `NONE -> ACTIVE -> RELEASED`. Provenance is a one-shot immutable
record. Legacy protection follows `NONE -> PROTECTED | FAILED`; retry after
failure uses a new migration-attempt identity. Quota pressure follows
`CLEAR -> PRESSURED -> CLEAR`. `storage.message_rejected` records no entity
transition, while `blob.incident_recorded` changes only the derived Blob
availability to `INCIDENT`.

Canonical-reference intents follow
`NONE -> OPEN -> COMMITTED` or `NONE -> OPEN -> RELEASED`.
`OPEN` and `COMMITTED` both pin their exact Blob set. `COMMITTED` has no
outbound transition in v1. `RELEASED` is legal only when the exact
`HEAD_SUPERSEDED_WITHOUT_BOUND_EVENT` authority proves that the conditional
candidate never committed and can no longer commit. An ambiguous intent
remains `OPEN` and is a GC root. `CANONICAL_REFERENCE_REMOVED` is not a v1
enum or lifecycle branch; a future removal protocol requires a new version
with its own canonical Event family and Receipt rules.

These transition sets and the events that drive them are exhaustive. Terminal
Transfer attempts, Materializations, GC targets, dispositions, released
holds, disposed Quarantine records, abandoned or deleted
Replicas, policies, Reference Sets, provenance records, and legacy-protection
attempts have no outbound lifecycle-state transition. Exact disposition
Events may revise only the retained residual-object subprojection of a terminal
Transfer Attempt or Materialization while leaving its terminal lifecycle state
unchanged. Restore, retry, repair, reinspection result, or repeated deletion
otherwise uses the new identity required by the relevant state machine and
cites the preceding record. A `DELETE_FAILED` Replica may enter `DELETING`
only through a new independently authorized GC target.

Open intents are a deterministic projection, never a directory scan:

| Creating Event | Exact branch and identity | Removing Event set |
| --- | --- | --- |
| `transfer.commit_intent_recorded` | `TRANSFER_COMMIT`, `intent_id == commit_intent.intent_id`, owner Attempt | `transfer.committed`, `transfer.failed`, `transfer.cancelled`, or `transfer.quarantined` |
| `materialization.commit_intent_recorded` | `MATERIALIZATION_COMMIT`, `intent_id == commit_intent.intent_id`, owner Materialization | `materialization.committed`, `materialization.failed`, or `materialization.quarantined` |
| `quarantine.intent_recorded` | `QUARANTINE_MOVE`, `intent_id == quarantine_id`, owner selected by `owner_kind` | `quarantine.recorded` or `quarantine.failed` |
| `gc.target_deletion_started` | `GC_DELETE`, `intent_id == deletion_intent_id`, owner GC plan | matching `gc.target_deleted` or `gc.target_failed` |
| `disposition.started` | `DISPOSITION`, `intent_id == execution_intent_id`, owner disposition | matching `disposition.completed` or `disposition.failed` |
| `canonical_reference.intent_recorded` | `CANONICAL_REFERENCE`, both IDs equal `reference_intent_id` | `canonical_reference.committed` or `canonical_reference.released` |

Creation sets revision one and both event Sigils as required by
`OpenIntentProjection`. Removal requires an exact ID, owner, source Event, and
object/authorization match; an unknown or mismatched terminal ID is
`INTEGRITY_FAILURE`. `storage.recovery_started.open_intent_ids` is the complete
sorted set of these replayed IDs, and `storage.recovery_completed` can list an
ID as resolved only after its removing Event is durable.
A pre-start `disposition.failed` has a null execution-intent ID and therefore
does not match this table: it neither creates nor removes an open intent.

### Append, replay, and recovery

`journal.frames` is a concatenation of binary frames; it is not JSONL. Each
frame has exactly this byte layout:

```text
offset  size       value
0       8          unsigned big-endian event-byte length N
8       N          canonical UTF-8 JSON event bytes, with no BOM or newline
8+N     32         raw SHA-256 digest of those N event bytes
40+N    8          the same unsigned big-endian N
48+N    8          ASCII bytes "BWSEV1\r\n"
```

`N` is in `1..8388608`. The opening length, closing length, raw digest, fixed
marker, canonical JSON bytes, closed Event Schema, event Sigil, chain link,
sequence, and entity revisions must all validate. A frame boundary is
therefore mechanical; a newline, a valid JSON prefix, a filename, or a Head
claim cannot create a frame.

Before acknowledging a mutation, the coordinator holds the exclusive journal
lock, verifies the complete committed chain and relevant revisions, evaluates
due fences and quotas, validates the event, and makes referenced immutable
material durable. It then writes the complete frame, fsyncs
`journal.frames`, atomically replaces and fsyncs the Head with the new
`committed_byte_length`, fsyncs the storage directory as required by the Host
profile, and only then exposes success or a handle. A backend commit, move, or
delete that can occur before its journal intent is forbidden.

Replay starts at `storage.initialized`, requires contiguous sequence and event
Sigils, validates every exact Schema and relationship, applies only the state
machines above, recomputes quota counters and Blob availability, and validates
the result against `artifact-storage-state/1.0`. The state projection contains
the current epoch, journal last-event Sigil, all entity revisions and states,
legacy protections, policies, holds, typed reference sets, quota reservations,
GC and disposition state, and derived availability. The catalog is only a
projection of that state.

The Head is a cache, not authority. A missing or stale Head may be rebuilt from
a chain consisting entirely of complete valid frames. A valid frame after a
stale Head is replayed; it is not discarded merely because Head replacement
did not occur. A conflicting Head, invalid middle frame, complete frame with a
bad digest or marker, unknown event, broken Sigil, illegal transition, revision
gap, impossible relationship, or missing referenced immutable payload puts
storage into `INTEGRITY_FAILURE`. It may run read-only Doctor and evidence
export but may not import, materialize, finalize, authorize disposition, or
delete.

There is one narrowly defined interrupted-append case. EOF may occur after
one through seven bytes of a final prospective opening length, or after a
complete valid bounded opening length but before all event bytes, digest,
repeated length, and marker have arrived. Recovery may treat that suffix as
uncommitted only when a previously durable, fully valid Head points to a valid
frame boundary at or before the last complete frame, every complete
intervening frame validates, and no byte after the incomplete suffix can form
another frame. A complete opening length of zero or more than the bound is
corruption, not an interrupted append.

While holding the journal lock, recovery first stores the exact suffix bytes
and its `ORIGINAL_INTERRUPTED_APPEND` evidence record under `recovery/`, then
atomically installs
`recovery/tail-recovery.json` as a valid
`artifact-storage-recovery-marker/1.0` with `phase: EVIDENCE_DURABLE`. The
marker binds that record and the exact `TailRecovery` fields. Only then may it
truncate the suffix to the recorded last-complete boundary, fsync the journal
and directory, and atomically replace the marker with
`phase: TAIL_TRUNCATED`.

After replaying the complete prefix, recovery constructs exactly one
recovery-entry Event:

- for an empty prefix with the valid installed `format.json`, empty Journal,
  and zero Head, it reacquires the canonical-reference gate, repeats
  initialization preflight, requires the project, backend, conformance,
  quota-limit, and legacy plan to equal the installed format and current
  Chronicle snapshot, and constructs `storage.initialized` with the exact
  `TailRecovery` in its otherwise-null `tail_recovery` field;
- for `INITIALIZING` or `ACTIVE`, it constructs
  `storage.recovery_started`; and
- for `RECOVERING`, it constructs `storage.epoch_started` bound to the
  existing `active_recovery_id`.

No other replayed prefix is legal. The empty-prefix branch enters
`INITIALIZING` directly and has no synthetic prior Recovery projection;
subsequent migration resumes under the ordinary initialization state machine.
The other two Events carry the exact `TailRecovery` as already defined.

Recovery then generates one candidate `SE-` ID in memory and constructs the
canonical Event bytes containing that ID. ID allocation has no separately
durable allocator side effect: the ID becomes allocated only when the marker
replacement below commits it. Recovery stores and fsyncs those exact canonical
bytes plus a `RECOVERY_EVENT_SEED` evidence record, then atomically replaces
and fsyncs the marker as
`phase: RECOVERY_EVENT_ID_DURABLE`, binding the event ID, Event Sigil, and seed
record. It writes no frame-template byte before that marker is durable.

From the marker-bound seed, Recovery constructs the one binary frame, stores
and fsyncs it with a `RECOVERY_FRAME_TEMPLATE` evidence record, and atomically
replaces the marker with `phase: RECOVERY_EVENT_PREPARED`, adding the frame
start, size, frame Sigil, and template record. It may then append only those
exact bytes. After the frame and matching Head are durable, it replaces the
marker with `phase: RECOVERY_EVENT_COMMITTED`, removes the marker, and fsyncs
`recovery/`. All evidence records and raw evidence bytes remain retained.

Startup checks that one fixed marker path before ordinary replay. A crash in
`EVIDENCE_DURABLE` either completes the same exact truncation or, if the suffix
is already absent and the valid journal ends at the bound, advances to
`TAIL_TRUNCATED`. In `TAIL_TRUNCATED`, no Event identity or template is durable;
Recovery may construct one candidate only through the seed-and-marker
transaction above. An orphan seed left before marker replacement has no
authority and is retained as unreferenced Recovery evidence. A crash in
`RECOVERY_EVENT_ID_DURABLE` resolves the marker-bound seed, verifies its exact
Event ID and Sigil, and creates the same frame template before append; it never
allocates another ID or searches for an orphan seed.

In `RECOVERY_EVENT_PREPARED`, the journal suffix at the bound must be exactly
empty, the complete prepared frame, or a strict byte prefix of that frame. An
empty suffix retries the exact frame. A complete valid frame rebuilds or
confirms the Head and advances to `RECOVERY_EVENT_COMMITTED`. For a strict
prefix, recovery first stores those exact bytes and a chained
`RECOVERY_FRAME_RETRY_SUFFIX` record, then advances the marker to
`RECOVERY_EVENT_RETRY_EVIDENCE_DURABLE`, atomically incrementing `retry_count`
and binding that record as the evidence-chain head; only that phase authorizes
truncation back to the prepared frame start. After journal and directory fsync
it returns the marker to `RECOVERY_EVENT_PREPARED`, preserving the counter and
chain head, and retries the same frame. A crash before or during that retry
truncation deterministically completes the same operation. A crash in
`RECOVERY_EVENT_COMMITTED` verifies the exact event and Head, then only removes
the marker.

Any marker, evidence chain, prepared frame, Head, or journal mismatch enters
`INTEGRITY_FAILURE`; recovery never restarts the decision from directory
contents. A missing or conflicting old Head, an invalid length, digest,
repeated length, marker, non-prefix retry suffix, or complete conflicting
frame is not an interrupted append. Doctor never performs this repair.
Best-effort skipping, truncation of a complete unknown frame, truncation
without retained evidence, changing the prepared event on retry, and
reconstruction from directory names are forbidden.

For a non-empty prefix, Recovery starts a higher coordinator epoch and, after
any proven interrupted append is resolved, appends the applicable
`storage.recovery_started` or `storage.epoch_started` Event defined above. It
resolves every open intent and side effect against exact backend generations,
then appends `storage.recovery_completed` before ordinary mutations resume. An
empty-prefix `storage.initialized` completes only tail repair and enters
`INITIALIZING`; it does not append `storage.recovery_completed`. No branch
infers ownership or completion from a path alone, and an unavailable or
ambiguous backend leaves an initialized store in `RECOVERING` without a new
mutable side effect.
A restart that replays an active Recovery first advances the epoch through the
one bound `storage.epoch_started`, fences any prior coordinator authority, and
continues the same open-intent set plus any newly discovered intent; it cannot
drop a prior intent or change the frozen resume status.

### Trusted clock and expiry

Every durable deadline is one authenticated UTC value: Reservation
`expires_at`, Verification `next_due_at`, retention-policy `retain_until`,
Blob `next_verification_due_at`, GC-plan `grace_ends_at`, GC authorization
`authorization_expires_at`, or disposition `expires_at`. Null is legal only
where that field's Schema explicitly permits it. Persisted monotonic ticks are
clock observations, not deadline authority and are never compared across a
process restart or monotonic-domain change.

On process start, after each new due time, and after clock restoration, the
coordinator first verifies current UTC against the last trusted Journal time
and creates only an in-process anchor:

```text
(trusted_utc_at_anchor, monotonic_at_anchor, durable_due_at)
remaining = durable_due_at - trusted_utc_at_anchor
```

`remaining <= 0` is already due. Otherwise the live timer becomes due at the
earlier of trusted UTC reaching `durable_due_at` or monotonic elapsed reaching
`remaining`. A later wall-clock adjustment cannot extend it. No process-local
anchor is serialized. `ReservationRef.created_clock` and
`remaining_micros_at_creation` preserve the creation observation only and
cannot re-establish future authority after restart.

If UTC rollback, monotonic-domain loss, arithmetic overflow, excessive
divergence, or unauthenticated time prevents proof that a durable deadline
remains in the future, that deadline is conservatively due. The coordinator
first appends `storage.clock_uncertain`, closes the clock gate, enters or
continues Recovery, and applies due items in ascending
`(due_at, owner kind, owner ID)` order. “Due” revokes or rejects time-limited
authority: it terminalizes an operation through its owning Event, marks
verification stale, ends a GC or disposition authorization, and merely
triggers retention re-evaluation rather than authorizing deletion.
If a Disposition authorization becomes due while its state is still
`AUTHORIZED`, the owning terminal Event is the pre-start
`disposition.failed` branch with null execution-intent ID; it performs no
backend side effect and leaves the target projection unchanged.

Restoration requires bounded evidence and a fresh process-local anchor,
appends `storage.clock_restored`, and durably resolves every item that cannot
be proven future before another caller mutation. It never restores an old GC,
disposition, Lease, or transfer authority. No caller timestamp, backend
timestamp, filesystem mtime, or object-store date can restore trust or order
an Event.

## Storage records and lifecycle

### Blob record

`artifact-blob/1.0` is a closed replay projection with exactly these top-level
fields: `schema_version`, `blob_sigil`, `size_bytes`, nullable
`first_verified_at`, `availability`, `availability_as_of`,
`availability_basis_sigil`, `effective_policy_set_sigil`, nullable
`next_verification_due_at`, sorted
`known_replica_ids`, sorted `eligible_replica_ids`, sorted
`integrity_event_sigils`, bounded sorted
`media_type_observations`, bounded sorted sanitized
`filename_observations`, `revision`, and `record_sigil`. The record Sigil is
canonical JSON over every field except itself; Blob identity remains
`blob_sigil`, not the changing record Sigil. `first_verified_at` is null only
for an identity that has never had an eligible verified Replica. Descriptive
media-type or filename observations never participate in Blob identity.
Availability is a total function evaluated in this exact priority order:

1. `INCIDENT` when any unresolved collision, catalog contradiction, or
   integrity incident affects the Blob;
2. otherwise `UNAVAILABLE` when the eligible Replica count is zero;
3. otherwise `DEGRADED` when one or more eligible Replicas exist but their
   count, backend distribution, integrity freshness, or another merged active
   retention requirement is unmet; and
4. otherwise `AVAILABLE`.

No Blob can satisfy more than one branch. A Replica is eligible only while it
is `AVAILABLE`, its generation and byte identity verify, and its explicit
verification deadline has not expired. State replay evaluates availability as
of the latest applicable direct or fan-out event at the verified State Head,
records that complete `EventRef` in `availability_as_of`, and resolves its
`recorded_at` only by verified Journal replay; it never stores a Timestamp in
that field or consults retrieval time. `availability_basis_sigil` covers the
exact sorted applicable
Replica revisions, integrity events, active policy records, holds, reference
roots, verification deadlines, and trusted clock event used by that
calculation.

Blob `revision` advances only for an event that directly owns that Blob or one
of its Replica relationships. Project-, Program-, or Reference-Set-scoped
policy and hold events may change many derived Blob views; replay recomputes
those records and their `record_sigil`, `availability_basis_sigil`, and wrapper
`last_event_sigil` without fabricating thousands of `BLOB` revision
assignments. Such fan-out is deterministic from the policy/hold entity
revision and Storage Head and grants no entity-level compare-and-swap
authority. A caller that needs concurrency control compares the Storage Head
and basis Sigil, not the intrinsic Blob revision alone.

Before any operation selects a Replica or changes storage state, the
coordinator evaluates due verification deadlines under the Journal lock and
appends `replica.verification_expired` before the requested operation. A
strictly read-only view may additionally report `currently_eligible: false`
when trusted current time is past a recorded deadline, but that view is not
the State projection or State Sigil and grants no authority.

These states make no canonical or scientific claim.

### Transfer lifecycle

Every transfer has an immutable request identity and one or more unique attempt
identities. `artifact-transfer/1.0` is the immutable `ST-` request;
`artifact-transfer-attempt/1.0` is one `SA-` execution of that request. An
event, projection, API result, or test must use `transfer_id` only for the
request and `transfer_attempt_id` only for an attempt; neither identifier may
stand for both. The attempt's append-only projection follows:

```text
PREPARED -> STREAMING -> VERIFYING -> COMMITTING -> COMMITTED
     |          |             |             |
     +----------+-------------+-------------+
                    v
         FAILED | CANCELLED | QUARANTINED
```

`COMMITTED` is valid only when the complete logical bytes, size, expected
identity policy, backend commit, and required post-write verification all
pass. `FAILED`, `CANCELLED`, and `QUARANTINED` are terminal for that transfer
attempt. Retry creates a new attempt and retains the prior terminal record.

The Attempt's `commit_intent` is null before
`transfer.commit_intent_recorded` and is the exact `TransferCommitIntent`
thereafter. `residual_staging_cleanup` is `PENDING` while an intent-owned
residual generation may still require classification; every terminal record
uses `NOT_REQUIRED`, `CLEANED`, or `HELD_FOR_DISPOSITION` with the field/null
matrix defined by `ResidualStagingCleanup`. `FAILED` is a nonterminal Recovery
observation and cannot appear in a terminal Attempt. No terminal record can
leave cleanup `PENDING`.

The Attempt staging projection is also exact. `PREPARED` has
`staging_state: NOT_CREATED` and null `staging_object`; `STREAMING`,
`VERIFYING`, and `COMMITTING` have `PRESENT` and the exact non-null generation.
A terminal Event with cleanup `NOT_REQUIRED` or `CLEANED` has `MISSING` and
retains the exact historical `staging_object` unless its explicit pre-intent
failure branch is `NOT_CREATED`; cleanup `HELD_FOR_DISPOSITION` has the
identically named staging state and object. Only `COMMITTED` has a non-null
`selected_replica_id`, and only `QUARANTINED` has a non-null `quarantine_id`.
The former has null terminal reason; `FAILED`, `CANCELLED`, and `QUARANTINED`
have the exact non-null payload Reason.

The request binds:

- direction and operation purpose;
- source and destination classes;
- expected Sigil when one is pinned;
- maximum byte count, duration, and optional file-count limits;
- backend profile ID, version, and Sigil;
- authorization and idempotency identity;
- Job, Attempt, Lease, and public RFC-0012 fence tuple when execution is the
  source or sink; secret Lease credentials and proofs are never journaled;
- required verification method; and
- provenance and retention policy references.

Reuse of an idempotency key with any changed bound field is rejected. Replaying
an exactly matching committed request returns the existing outcome without
performing a second mutable write.

The stored public fence tuple is exactly `(execution_journal_id,
executor_epoch, job_id, attempt_id, lease_id, fencing_generation)`. Every
side-effecting storage event also binds the execution-journal event Sigil at
which the coordinator verified that tuple, the then-current Job fence floor,
and whether a later tombstone already existed. A generation alone, or a tuple
without current journal evidence, is never sufficient.

### Replica lifecycle

A Replica becomes `AVAILABLE` only after a committed transfer identifies its
Blob and records backend object identity, immutable generation or version,
size, and verification evidence. Later checks append observations. A Replica
may become `VERIFYING`, `CORRUPT`, `DELETING`, `DELETED`, or `DELETE_FAILED`;
it never changes from one Blob identity to another. `QUARANTINED` is not a
Replica state: quarantined bytes have a separate Quarantine identity and can
become a Replica only through a new verified Transfer.

A replacement or repaired copy is a new Replica with a fresh backend
generation whose transition is explicit and conditionally verified. Backend
overwrite of an `AVAILABLE` Replica is forbidden even when the claimed Sigil
is unchanged.

### Materialization lifecycle

A materialization record binds the source Blob and Replica verification,
destination class, normalized destination, Task and Attempt where applicable,
requested access mode, created time, and cleanup result. Materialization is
atomic from the consumer's perspective: the destination is absent until its
complete bytes have been verified and finalized.

The record independently tracks consumer-destination cleanup in `cleanup` and
commit-time staging cleanup in `residual_staging_cleanup`; one cannot stand in
for the other. A committed destination may become visible with a residual
staging generation only when that residual is durably
`HELD_FOR_DISPOSITION`, inaccessible, and charged. Failed Materialization
staging and failed final destinations use the two exact materialization
disposition target kinds and remain charged until their completed Event.

Before a final destination exists, and in `QUARANTINED`, `cleanup` is
`NOT_REQUIRED`. `materialization.committed` and
`materialization.cleanup_started` store `PENDING`;
`materialization.cleaned` stores `CLEANED` with the payload's cleanup-evidence
Sigil; and `materialization.cleanup_failed` stores `FAILED` with the payload's
cleanup-evidence Sigil and Reason. A `materialization.failed` projection uses
the exact `destination_cleanup` object and state/object matrix in its Event
branch. Thus `FAILED` or `CLEANUP_FAILED` plus `cleanup: FAILED` and the
intent-bound destination object is the durable held-destination condition that
`MATERIALIZATION_DESTINATION` may authorize; it is never inferred from a path.

Sanctum inputs are read-only at the policy boundary. A writable Crucible copy
is a derived mutable workspace, not the source Replica. Hard-linking an
untrusted or writable destination to a content-addressed backend object is
forbidden because mutation through either name would corrupt the Blob.
Copy-on-write or reflink materialization is allowed only when conformance tests
prove that destination mutation cannot change stored bytes.

## Trusted import

"Trusted import" means that Benchwork establishes and retains the declared
identity, source binding, policy decision, and transfer evidence. It does not
mean that imported content is safe, authentic, licensed, scientifically valid,
or worthy of canonical acceptance.

An import follows this sequence:

1. Ward or another authorized control-plane caller submits a closed import
   request with source class, bounds, expected identity policy, destination
   backend, provenance, and idempotency identity.
2. The storage coordinator allocates a fresh transfer-scoped staging namespace.
   The source cannot choose a final backend key.
3. The coordinator opens the source without following an unvalidated path,
   streams bytes while enforcing byte and time limits, and computes SHA-256 and
   byte count over the received logical bytes.
4. The coordinator closes the source, verifies completeness, compares any
   expected Sigil and size, and records the computed result before commit.
5. It appends a recoverable commit intent, conditionally creates or reuses the
   content-addressed backend object, and verifies the committed logical bytes.
6. Only then does it append `COMMITTED`, create or confirm the Replica, and
   make the Blob eligible for later materialization or proposal submission.

If the caller supplies an expected Sigil, exact match is mandatory. If no
prior Sigil exists, Benchwork may capture the bytes under the newly computed
identity only when the import policy permits `CAPTURE_NEW_IDENTITY`. Provenance
must say that the identity was first observed at ingest. Such a capture cannot
satisfy a Task input or other contract that pinned an identity before
execution.

Local path import rejects paths outside the authorized scope, path traversal,
symlink or hard-link ambiguity, special files, source replacement during read,
and size changes. It must either hold a stable file handle and verify source
metadata before and after the read or copy from an isolation mechanism that
provides equivalent stability. A directory is rejected unless a declared
bundle builder handles it under the closed manifest rules.

Worker output import uses an Attempt-scoped write handle. The Worker receives
neither backend credentials nor a final Blob key. Finalization requires the
current unexpired Lease and authenticated Worker-protocol authority. At A2,
the backend validates the complete public tuple, its highest accepted Executor
epoch, the matching Job fence floor, and absence of a higher tombstone on
every direct side-effecting operation. A backend that cannot do so may only
permit writes to Attempt-isolated staging that the trusted coordinator alone
can commit. Immediately before final commit, the coordinator replays the
execution journal and requires the same journal, epoch, Job, Attempt, Lease,
generation, active Lease state, fence floor, and tombstone status to remain
eligible. Lease credentials and proofs are ephemeral secrets and never enter a
Transfer, provenance record, or log. Late, fenced, over-limit, partial, or
policy-violating output is ineligible for the Job result. The coordinator
preserves its bytes in quarantine only after reserving the applicable bounded
quarantine capacity. If capacity is unavailable, it
retains the failed Transfer with
`staging_state: HELD_FOR_DISPOSITION`, does not expose the bytes, keeps the
exact staging reservation charged, and applies storage backpressure until a
separately authorized disposition or later Quarantine reservation resolves
the staging object.

### Closed `ATTEMPT_OUTPUT` ingest binding

An `artifact-transfer/1.0` request uses `purpose: ATTEMPT_OUTPUT` if and only
if the Executor preallocated it for one current RFC-0012 Lease-scoped output
handle. It becomes eligible for an execution output root only when one
accepted Result output selects that exact pair and the later
`execution-storage-root-manifest/1.0` entry resolves it. The following matrix
is closed; no other direction, descriptor, execution branch, fence, handle,
Blob, backend, or historical-transfer substitution is legal:

| Surface | Exact value | Required equalities |
| --- | --- | --- |
| Direction and purpose | `direction: INGEST`, `purpose: ATTEMPT_OUTPUT` | Either value selects this entire matrix; it cannot be combined with any other row of the source/destination space. |
| Source | `ATTEMPT_OUTPUT {kind, execution, output_handle_id}` | `source.execution` equals the request's top-level `execution` byte-for-byte. |
| Destination and backend | `MANAGED_BACKEND {kind, backend}` | `destination.backend == transfer.backend` byte-for-byte. The Attempt staging object, commit-intent target object, terminal Event backend object, and selected Replica all use that `backend_id`; the selected Replica's complete `backend` equals the request backend. |
| Execution and public fence | `LEASED {kind, execution_journal_id, executor_epoch, job_id, attempt_id, lease_id, worker_id, worker_session_id, fence}` | The imported RFC-0012 execution identifiers equal the accepted Result's owner and current Lease. `fence.execution_journal_id`, epoch, Job, Attempt, Lease, and generation equal the Result `fence_tuple`'s `journal_id` and same-named fields; its additional execution-Event Sigil, Job fence floor, and tombstone status authenticate that exact current tuple. Finalization revalidates all of them. `ATTEMPT`, `NONE`, a prior Lease, or a merely equal fence Sigil is invalid. |
| Result staging reference | `ATTEMPT_OUTPUT {kind, storage_subject_id, output_handle_id, transfer_id, transfer_attempt_id}` | This is the exact closed branch in the accepted `execution-result/1.0` output. `source.output_handle_id` equals its opaque `output_handle_id`; `storage_subject_id` equals `Sigil(["execution-attempt-output-storage-subject-id/1.0", job_id, attempt_id, output_handle_id])` and the ESM entry's `storage_subject_id`. Its `transfer_id` and `transfer_attempt_id` equal the current `ST-ID` and `SA-ID`, and its canonical-JSON Sigil equals the ESM subject's `staging_reference_sigil`. A path, URL, backend locator, Replica ID, another Attempt's handle, or equality between the handle and derived subject is invalid. |
| Blob and bound | Non-null `expected_blob_sigil`; exact request byte bound | `expected_blob_sigil` equals the Result output and ESM subject `blob_sigil`; `bounds.max_bytes` equals that output's `byte_size`. The Transfer Attempt's computed Sigil and size, commit-intent `computed_blob`, terminal Event Blob and size, selected Replica, provenance Blob, ESM `claimed_blob`, and committed Blob record all equal that pair. |
| Current `TransferRef` | `transfer_id`, `transfer_attempt_id`, `request_record_sigil`, `attempt_record_sigil`, `terminal_event` | The IDs are the Result branch's current pair. The two record Sigils resolve this immutable request and its terminal Attempt record. `terminal_event` is the exact Storage Event that terminalized that Attempt and carries the same IDs; no field is reconstructed from a Replica or Blob. |
| Current provenance | One `artifact-provenance/1.0` record with `relation: CAPTURED` | Its Blob, source, destination, authorization, execution, backend, and `transfer` equal this request, committed Blob pair, and current `TransferRef`; `transformation` is `NONE`. For a committed output, `terminal_reason` is null and `verification_sigils` is the one-member array containing the terminal exact-generation verification evidence Sigil. Its ID and record Sigil are the pair carried by the ESM entry. |

For a committed output, the physical outcome matrix is also exact:

| `transfer.committed.outcome` | Selected Replica | Current Transfer and provenance |
| --- | --- | --- |
| `NEW_REPLICA` | `replica_id == provisional_replica_id`; its `created_by_transfer_attempt_id` equals the current `SA-ID`. | The ESM `TransferRef` and `CAPTURED` provenance use the current Result-bound `ST-ID`/`SA-ID` and this terminal Event. |
| `DEDUPLICATED_REPLICA` | `replica_id != provisional_replica_id`; the selected `AVAILABLE` Replica and its historical `created_by_transfer_attempt_id` remain unchanged, while only the provisional Replica becomes `ABANDONED`. | The ESM still carries a new current `TransferRef` and current `CAPTURED` provenance for the Result-bound `ST-ID`/`SA-ID`. The historical Replica creator, its request or Attempt Sigil, its terminal Event, and any older provenance record cannot populate or stand in for any current field. |

An ESM `QUARANTINE` origin likewise carries the current Result-bound
`TransferRef` and current `CAPTURED` provenance for the attempted Blob; its
terminal reason and Quarantine owner resolve that same `SA-ID`. A
`NOT_STORED` origin carries the current failed or cancelled `TransferRef` when
one was started and carries null only when no Transfer was started; it cannot
borrow older provenance or a byte-equal Replica to claim storage success.

Staging is the normal, incomplete state of every import and is not quarantine.
It has a Transfer owner, reservation, deadline, generation, and recoverable
state. Failed staging bytes may move into a fresh Quarantine generation only
after the coordinator reserves the exact byte and object bound and durably
appends `quarantine.intent_recorded`. The backend move then uses the exact
source and destination generations in that intent. After destination
durability and readback verify, `quarantine.recorded` changes the Quarantine
to `HELD`; only then may `transfer.quarantined` terminalize the attempt and
settle the staging reservation. It releases source claims only when
`source_cleanup` proves the source absent or cleaned; an exact residual remains
charged as `HELD_FOR_DISPOSITION`. Recovery resolves a crash after the intent
from those exact generations and never from a pathname guess. Staging paths
cannot be relabelled as quarantine merely to bypass quotas, and neither
staging nor quarantine can be selected as a Replica.

At `quarantine.intent_recorded`, the projection's `source_cleanup` is
`PENDING` for the exact source object. `quarantine.recorded` or
`quarantine.failed` replaces it with the payload's legal terminal cleanup
object byte-for-byte. Reinspection and destination disposition preserve that
source-cleanup evidence. A later owner-staging disposition updates only the
owner's repeated residual subprojection; the Quarantine retains the terminal
move evidence that was true when it completed.
The Quarantine `source_object` is null exactly when terminal source cleanup is
`NOT_REQUIRED`; `PENDING`, `CLEANED`, and `HELD_FOR_DISPOSITION` retain the
intent's exact source reference. Its `destination_object` is null exactly for
a terminal `quarantine.failed` `NOT_CREATED` destination. An intent or failed
projection otherwise retains the intent destination reference exactly; a
recorded projection retains the terminal verified reference with the same
intent-bound backend identity, locator, generation, and size and its exact
verified Blob Sigil, including after disposal as tombstone identity.

An existing `artifact/1.0` may be copied into managed storage only after the
coordinator verifies the Chronicle record, registration Receipt, root-contained
resolved location under the existing v1 rule, and exact location Sigil. This
creates operational
Blob, Replica, and provenance records. It does not migrate, replace, or update
the Artifact or permit removal of its recorded local file.

## Trusted export and materialization

An export selects source bytes by Blob Sigil and size, never by an unverified
mutable path or a human filename. The coordinator:

1. authorizes the exact destination class and normalized destination;
2. selects an eligible Replica under the required backend and freshness
   policy;
3. streams the complete logical bytes while recomputing SHA-256 and size;
4. writes into a fresh destination staging name with explicit bounds;
5. atomically finalizes with no-clobber or exact generation preconditions;
6. verifies the destination by readback or a conformance-approved end-to-end
   checksum over the same logical bytes; and
7. records a closed export manifest and cleanup outcome.

The export manifest binds the Blob Sigil and size, source Replica and
verification evidence, destination descriptor without credentials, transfer
request and attempt IDs, backend profiles, authorization, timestamps,
idempotency key, bytes observed, verification method, and result.

A sink acknowledgement, TLS success, HTTP status, object-store ETag, file
existence, process exit code, or matching filename is insufficient by itself.
An ETag may count as content verification only when the exact backend profile
defines it as a cryptographic digest over the same logical bytes and the
conformance suite proves that behavior for the selected operation.

Export never overwrites an unrelated destination. An existing destination may
be treated as an idempotent success only after its exact bytes and request
binding are verified. Otherwise the operation fails without changing the
destination and retains the conflict record.

Materializing a Blob as a stable project-relative file can prepare a later
`artifact/1.0` registration. The materialization must use a durable independent
copy, preserve the exact Sigil, and pass destination readback before Athanor is
called. Artifact registration remains a separate explicit transition with an
`AR-` ID, Program, kind, producer, inputs, and Receipt. The storage coordinator
cannot call that transition merely because export succeeded.

## Transfer integrity, atomicity, and recovery

Every transfer computes an end-to-end digest and byte count at the Benchwork
trust boundary. Transport encryption and backend checksums are additive
controls, not substitutes for content identity.

Chunked and resumable transfer is allowed only when the transfer contract
binds:

- the immutable source Blob identity or a transfer-scoped source snapshot;
- exact offset and total size;
- verified prefix or chunk identities;
- backend upload or generation identity;
- the same request, authorization, Lease, and fencing context; and
- a resume proof that no accepted byte range changed.

Out-of-order, overlapping, missing, duplicated with different bytes, or
unverifiable chunks fail the attempt. Final identity is always recomputed or
cryptographically combined under a separately specified algorithm over the
complete logical byte sequence; a list of individually valid chunks is not
automatically the Blob identity.

Publication uses a recoverable intent:

1. append a commit intent containing staging identity, computed Sigil and size,
   backend profile, target key derivation, and preconditions;
2. conditionally finalize the backend object without overwriting an existing
   generation;
3. verify the finalized logical bytes and durability evidence; and
4. append the committed Replica and Transfer records.

That commit intent is also the sole rollback authority for conditional removal
of its exact never-published provisional target generation after the execution
fence becomes ineligible or verification fails. It never authorizes deletion
of a pre-existing generation or the selected DEDUP Replica. Absence or exact
rollback evidence is retained by the terminal Event; an ambiguous or failed
rollback leaves the intent open in Recovery.

After a crash, recovery replays the Storage Journal. It does not infer success
from a filename or object key. For each unresolved intent it verifies the
staging and final objects, generation, Sigil, size, fencing eligibility, and
backend response. It may complete the exact pending commit, record an
idempotent pre-existing Replica, or quarantine the bytes. Ambiguity fails
closed.

The recovery decision for every nonterminal Transfer attempt is exact:

| Durable attempt state | Verified backend observation | Required recovery action |
| --- | --- | --- |
| `PREPARED`, `STREAMING`, or `VERIFYING` | no `transfer.commit_intent_recorded` exists | No final object could legally have been created. Append `transfer.failed` with `RECOVERY_INTERRUPTED_PRECOMMIT`; release an unused reservation, but retain any exact staging generation as `HELD_FOR_DISPOSITION` or move it only through a new durable Quarantine intent. |
| `COMMITTING` | intended final generation exists, independently verifies against the intent, and the execution fence remains eligible | Append `transfer.committed`, creating the intended Replica or selecting the exact already named verified Replica. |
| `COMMITTING` | final object is absent, the exact intended staging generation exists, and the execution fence remains eligible | Revalidate every intent precondition, perform the one conditional finalize, read back, and append `transfer.committed`. |
| `COMMITTING` | exact final generation and exact residual staging generation both exist, and the execution fence remains eligible | Conditionally clean only the intent-bound residual staging generation, verify that cleanup or retain its exact failure/held disposition, then append `transfer.committed` from the verified final generation with the closed `residual_staging_cleanup` outcome. |
| `COMMITTING` | the execution fence is now stale, tombstoned, or otherwise ineligible | Never append `transfer.committed` for this Attempt. Leave an already journaled pre-existing Replica unchanged. Prove the provisional target was never created or conditionally remove only its exact unpublished generation under the commit intent; if that cannot be authenticated, remain `RECOVERING`. Then isolate the exact staging generation through a new Quarantine intent or retain it `HELD_FOR_DISPOSITION`, and terminalize the Transfer as fenced and ineligible. |
| `COMMITTING` | neither exact final nor exact staging generation exists | Append `transfer.failed` with `RECOVERY_PAYLOAD_LOST`, retain the missing-generation evidence, and make no Replica available. |
| `COMMITTING` | an object exists with a different generation, size, Sigil, namespace identity, or ownership | Append the applicable incident and `transfer.failed`; quarantine only a separately identified exact generation through the Quarantine protocol. Never overwrite or adopt the conflicting object. |
| any nonterminal state | the backend observation, execution fence, or durability result is unavailable or ambiguous | Remain `RECOVERING`, retain the unresolved intent and reservation as roots, and perform no finalize, move, cleanup, or terminal transition. |

Every `COMMITTING` row therefore replays the execution journal before
classification. A generation observed at the intended final key is not proof
that its side effect preceded a later fence, and recovery never backdates it.

Materialization recovery is independently exhaustive:

| Durable materialization state | Verified destination observation | Required recovery action |
| --- | --- | --- |
| `PREPARED`, `STREAMING`, or `VERIFYING` | no `materialization.commit_intent_recorded` exists | No final destination could legally have been created. Append `materialization.failed` with `RECOVERY_INTERRUPTED_PRECOMMIT`; retain an exact staging generation as `HELD_FOR_DISPOSITION` or move it only through a new Quarantine intent. |
| `COMMITTING` | the exact intended final generation exists, readback matches the source Blob, and the execution fence remains eligible | Append `materialization.committed` for that exact intent and generation; do not write again. |
| `COMMITTING` | final is absent, the exact staging generation exists, and the execution fence remains eligible | Revalidate the intent and destination no-clobber precondition, perform the one conditional finalize, read back, and append `materialization.committed`. |
| `COMMITTING` | exact final and exact residual staging generations both exist and the fence remains eligible | Conditionally clean only the exact residual staging generation first. Append `materialization.committed` only after recording `CLEANED`, or after proving the generation remains exact and inaccessible and recording `HELD_FOR_DISPOSITION`; store that complete result in the Event and Materialization. |
| `COMMITTING` | the fence is stale, tombstoned, or otherwise ineligible | Never append `materialization.committed`. Isolate the exact staging generation through a new Quarantine intent or retain it `HELD_FOR_DISPOSITION`; retain every exact final destination as `HELD_FOR_DISPOSITION` in the distinct destination field, then append the fenced `materialization.failed` branch. |
| `COMMITTING` | neither exact final nor exact staging generation exists | Append `materialization.failed` with `RECOVERY_PAYLOAD_LOST`, retain missing-generation evidence, and expose no destination handle. |
| `COMMITTING` | an object exists with a different generation, identity, size, Sigil, namespace, or ownership | Record the applicable incident and append `materialization.failed`; never overwrite, adopt, or expose the conflicting object. |
| any nonterminal state | destination, staging, fence, or durability observation is unavailable or ambiguous | Remain `RECOVERING`, retain the open intent and reservation, expose no destination handle, and perform no finalize, cleanup, or terminal transition. |

The destination namespace stays inaccessible to its intended consumer until
`materialization.committed` and the matching Head are durable. Recovery checks
the current execution fence in every `COMMITTING` row. A filesystem name,
successful rename response, or matching bytes without the exact intent and
generation is not a materialization commit.

Recovery of `quarantine.intent_recorded` uses the same closed observation
discipline. Exact destination present and verified permits
`quarantine.recorded`; exact source present with destination absent permits the
one intent-bound conditional move followed by readback. When both are present,
Recovery conditionally cleans only the exact residual source generation before
the terminal Event. It appends `quarantine.recorded` only with `CLEANED`, or
with `HELD_FOR_DISPOSITION` after proving the source remains exact,
inaccessible, and quota-owned; an unavailable cleanup result remains
`RECOVERING`. Neither object present produces
`quarantine.failed` with retained loss evidence. A generation, identity, or
byte mismatch records an incident and `quarantine.failed`; any still-present
exact generation remains inaccessible and quota-charged until a separately
authorized disposition. An unavailable or ambiguous observation remains
`RECOVERING`. No branch relabels a pathname, guesses ownership, or releases a
reservation without a durable event.

Recovery of an open `GC_DELETE` is exhaustive:

| Verified observation after `gc.target_deletion_started` | Required action |
| --- | --- |
| exact approved generation is present, authorization is provably future, and current root/policy revalidation still permits deletion | Retry only the same conditional exact-generation delete, prove the post-delete absence, and append `gc.target_deleted` with the same deletion-intent ID. |
| exact generation is present but authorization is due or current root/policy revalidation blocks deletion | Perform no delete; append `gc.target_failed` with `DISPOSITION_EXPIRED` or `GC_ROOT_CHANGED`, move the Replica to `DELETE_FAILED`, and retain the bytes. |
| exact generation is absent and exact-generation stat plus the durable started Event proves the approved target is the generation now absent | Append `gc.target_deleted` with bounded absence evidence. This records the authorized target's physical absence without asserting an unobserved backend acknowledgement. |
| a different generation, identity, size, Blob Sigil, namespace ancestor, or owner is present | Do not delete it; append the applicable incident and `gc.target_failed` with `GENERATION_MISMATCH` or `BACKEND_CONFLICT`. |
| exact-generation presence, absence, durability, root state, or authorization cannot be authenticated | Remain `RECOVERING`; retain `GC_DELETE` and its Reservation; append no target terminal Event. |

Recovery of an open `DISPOSITION` is independently exhaustive:

| Verified observation after `disposition.started` | Required action |
| --- | --- |
| exact authorized generation is present and authorization is provably future | Retry only the same conditional exact-generation delete, prove absence, and append `disposition.completed` with the same execution-intent ID. |
| exact authorized generation is present but authorization is due | Perform no delete; append `disposition.failed` with `DISPOSITION_EXPIRED`; retain the target and its usage charge. |
| exact authorized generation is absent and exact-generation stat plus the durable started Event proves that exact target is now absent | Append `disposition.completed` with bounded absence evidence and remove only the matching charged usage. |
| a different generation, identity, size, Sigil, namespace ancestor, or owner is present | Do not delete it; append the applicable incident and `disposition.failed` with `GENERATION_MISMATCH` or `BACKEND_CONFLICT`. |
| exact-generation presence, absence, durability, or authorization cannot be authenticated | Remain `RECOVERING`; retain `DISPOSITION` and its Reservation; append no terminal Event. |

Both matrices use the Event-bound backend object, not listing or path
inference. The absent branches are legal because the started Event proves the
exact generation was revalidated immediately before deletion authority; they
still require fresh exact-generation absence evidence. A terminal Event
atomically removes the matching `OpenIntentProjection`, settles only its
Reservation, updates the owner projection, and records the deletion or failure
outcome. Recovery never substitutes a new intent ID, generation, target, or
authorization.
An `AUTHORIZED` Disposition whose authorization is due before
`disposition.started` is outside the open-intent matrix: Recovery appends only
the null-intent `disposition.failed` branch, settles its Reservation, and
performs no target observation, mutation, or open-intent operation.

The backend must make a committed object visible atomically or keep the object
outside the readable Replica namespace until the coordinator records it.
Readers never observe staging objects as available Blobs. A backend whose
consistency model cannot satisfy that rule is ineligible for committed
Replica use under this profile.

Cancellation and Lease loss stop new transfer activity. At A2, they revoke the
Worker's output handle and prevent finalization. An immutable identical Blob
that was already committed may remain as unreferenced operational storage, but
the fenced Attempt's provenance and result remain ineligible. A late attempt
cannot borrow a Replica committed by another attempt to fabricate eligible
completion.

## Provenance

Content identity answers "which bytes"; provenance answers "how Benchwork
observed, moved, or derived them." Provenance is append-only and is not folded
into Blob identity.

`artifact-provenance/1.0` records, as applicable:

- provenance event ID and relation type such as `CAPTURED`, `IMPORTED`,
  `COPIED`, `DERIVED`, `EXPORTED`, `MATERIALIZED`, `VERIFIED`, or `DELETED`;
- Blob Sigil and size plus source and destination classes;
- source Artifact ID and registration Receipt, source Blob or Replica, or
  sanitized external source descriptor;
- actor and control-plane authorization;
- Job, Attempt, Lease, public fence tuple and tombstone evidence, Worker,
  Executor, and realized assurance claim when execution is involved;
- backend profile, transfer request and attempt, and verification evidence
  Sigils;
- transformation contract, implementation version and Sigil, parameters,
  input Blob identities, and runtime identity for derived bytes;
- observed, started, committed, verified, and terminal times; and
- policy violations, missing evidence, and quarantine or deletion reason.

Credentials, signed query strings, bearer tokens, secret environment values,
and unredacted sensitive headers never enter provenance. A sanitized descriptor
must remain sufficient to distinguish the source class and stable object
identity without enabling access.

Deduplication retains each provenance event even when no new physical bytes
are written. A transformation always produces a derived provenance edge and a
new output identity unless its exact output bytes happen to equal an existing
Blob; in that case the new derivation edge is still retained.

Operational provenance cannot replace the canonical `artifact/1.0`
`producer_id` or `input_ids`. Matching a Job, Attempt, path, filename, or Blob
Sigil does not infer Program lineage. Athanor separately validates canonical
producer and input objects in the same Program.

The following evidence levels remain distinct:

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| `IDENTITY_COMPUTED` | Benchwork computed a Sigil and size for captured bytes | A prior party committed to that identity |
| `IDENTITY_MATCHED` | Captured bytes match a previously pinned Sigil and size | Source authenticity or scientific validity |
| `SOURCE_BOUND` | The transfer record binds the sanitized source and authorization | That the source statement is true |
| `TRANSFER_VERIFIED` | Source and destination logical bytes match end to end | Long-term availability or canonical acceptance |
| `CANONICALLY_REFERENCED` | Athanor accepted a transition that refers to the bytes under a defined contract | Safety, correctness, or indefinite retention |

No Provider, Worker, Executor, storage adapter, or checksum service can issue
a scientific acceptance Receipt.

## Storage backend contract

An Artifact storage backend is a privileged operational adapter behind the
storage coordinator. It is not a Worker tool, canonical authority, general
filesystem API, or general object-store proxy.

`artifact-storage-backend/1.0` declares a closed profile containing:

- backend ID, implementation and protocol version, build or package Sigil, and
  configuration Sigil with secrets excluded;
- namespace and tenant or project isolation semantics;
- maximum object size and supported transfer bounds;
- conditional-create, no-overwrite, immutable-generation, and atomic-visibility
  behavior;
- read-after-write and list consistency;
- logical-byte readback and checksum capabilities;
- range and resume behavior;
- durability and fsync or remote-commit semantics;
- deletion preconditions and retention-lock behavior;
- supported encryption or compression transparency;
- fencing support for side-effecting sinks;
- reconciliation and corruption-reporting capabilities; and
- conformance-suite identity, version, Sigil, Host platform, and evidence
  Sigil.

Unknown profile fields or capability values fail closed. A mechanism name,
cloud brand, filesystem, container, encryption claim, or advertised checksum
does not establish conformance.

The coordinator-facing interface is content-scoped and must support the
equivalent of:

| Operation | Required boundary |
| --- | --- |
| `begin_stage` | Allocate a fresh bounded staging object under a transfer identity and optional fence. |
| `write_stage` | Write bounded bytes without selecting or overwriting a final key. |
| `finalize_if_absent` | Atomically bind verified staged bytes to a digest-derived key or return the exact existing generation. |
| `open_read` | Stream logical bytes from one exact Replica and generation. |
| `stat` | Return size, generation, state, and backend metadata without treating metadata as verified content. |
| `verify` | Provide readback required for the coordinator to validate the complete logical bytes. |
| `delete_if_generation` | Delete one exact generation only under its matching GC-delete Event, authorized disposition, or unpublished provisional-target rollback intent. Prefix, wildcard, and unresolved-path deletion are forbidden. |
| `reconcile` | Enumerate or prove managed objects for recovery without making them available before verification. |

Backend keys are derived by trusted code from the verified Sigil and backend
namespace. Callers and Workers cannot provide arbitrary keys. Locators remain
opaque operational metadata and are never interpreted as proof of content.

The adapter must return typed bounded results. Backend claims are untrusted
until the coordinator validates their Schema, request binding, generation,
size, and required readback. An adapter cannot append Chronicle, grant a Ward
approval, manufacture missing provenance, register an Artifact, or elevate a
Sanctum assurance claim.

At A2, the Worker cannot access backend credentials, the Storage Journal,
catalog, quarantine, or committed namespace. The storage coordinator and
backend join the operational trusted computing base for any realized claim
that depends on their enforcement. A backend without per-write fencing may
accept only Attempt-isolated staging to which the Worker loses access; the
trusted coordinator validates the current fence before final commit.

The `0.4` profile permits only the built-in local backend. Arbitrary executable
Storage adapters remain outside the public SDK until signature, supply-chain,
permission, isolation, and conformance policy are accepted. Phase 4 may add
pluggable remote adapters behind this interface; no particular remote provider
is required.

## Conformance profiles and release boundary

Conformance is profile-specific. Evidence for one profile cannot be relabelled
as evidence for another, and an implementation may advertise only the exact
profile and suite Sigil recorded in `format.json`, the Storage State, and its
backend profile.

`LOCAL-PHASE3/1.0` is the required `0.4` profile. It covers only the built-in
single-project local backend under `.benchwork/storage/` and requires:

- one fenced storage coordinator at a time and exclusive Journal locking;
- no-follow, project-confined path operations and conditional creation;
- same-filesystem atomic visibility, directory and file durability through
  explicit fsync barriers, and crash recovery for every commit boundary;
- immutable Blob generations, exact-generation reads and deletes, and no
  overwrite of an available Replica;
- bounded streaming SHA-256 and size verification on source and readback;
- quota reservation, pressure, staging, quarantine, manual-disposition,
  61-row capacity-source equality, and positive system-reserve formulas
  defined by this RFC;
- Storage Journal replay, local reconciliation, Storage Doctor, GC dry-run,
  and exact manually authorized GC execution for eligible committed Replicas;
  and
- adversarial tests for crashes, path substitution, disk and inode
  exhaustion, partial operations, stale locks, and generation races on the
  exact Host filesystem and implementation build.

It does not claim remote transport, multi-coordinator consensus, automatic
replication, remote durability, automatic GC, verified remote deletion, or
production disaster recovery.

`PORTABLE-PHASE4/1.0` is a reserved later profile, not an optional checkbox on
the local suite. Enabling it requires a new accepted conformance package for
remote consistency, transport and credential isolation, immutable generation
and fencing semantics, reconciliation under partial network failure,
replication and repair, retention enforcement, automated GC, restore, and
backend-specific deletion evidence. Passing `LOCAL-PHASE3/1.0` cannot satisfy
any of those requirements. Unsupported interface methods fail closed; profile
negotiation cannot silently downgrade a requested guarantee.

## Storage Doctor

`bwork storage doctor` performs a read-only storage inspection and emits a
closed `artifact-storage-doctor-report/1.0`. The report binds the project,
Journal ID and last-event Sigil, Chronicle Head Sigil, storage format, backend
profile and Sigil, conformance profile and suite Sigil, coordinator epoch,
inspected backend generations, check results, applied limits and truncation,
overall status, and `report_sigil`. A report never grants authority or
changes availability by itself.

`mode` is exactly `NORMAL` or `DEEP`; `overall_status` is exactly `HEALTHY`,
`DEGRADED`, `RECOVERY_REQUIRED`, `INTEGRITY_FAILURE`, or `INCOMPLETE`.
When the format and Journal chain verify, all nullable identity fields named
above are non-null and `journal_verification.status` is `PASS`. If format or
Journal authority cannot be established, `storage_journal_id`, Head Sigil,
storage-format identity, backend and conformance identities, and coordinator
epoch are each null unless independently verified; neither cached Head nor
State may populate them. `journal_verification` records the failure,
`state_verification.status` is `INCOMPLETE`, every replay-dependent check is
`INCOMPLETE`, `incomplete_reasons` is non-empty, and `overall_status` is
`INTEGRITY_FAILURE` or `INCOMPLETE`, never `HEALTHY`. A verified Chronicle
Head may remain non-null independently of Storage Journal failure.

The normal mode validates the namespace and permissions, format, Journal
chain, Head and State caches, replay equivalence, closed Schemas and state
machines, quota-counter identities and Reservations, the exact 61-row
capacity-source classification, all system-reserve consumed and escrowed
counts/bytes against the installed formulas, legacy v1 protections, Reference
Sets and their relationship matrix, RFC-0014 Evidence Manifest/RootPlan/
hold/activation chains, holds, open intents, GC root/proof
equalities, and exact backend generations named by records. A valid plan plus
active hold with its exact activation absent is reported as a conservative
previsibility orphan, never auto-released or treated as a live root. It checks
that no staged, quarantined, deleted, abandoned, or unjournaled generation is
selectable as an available Replica. It also validates any fixed recovery
marker and evidence; a pending valid marker reports `RECOVERY_REQUIRED`, while
a mismatch reports `INTEGRITY_FAILURE`.

`bwork storage doctor --deep` additionally streams and rehashes every managed
available Replica, every legacy v1 compatibility anchor and protected managed
copy, and quarantined evidence when inspection policy permits. It reconciles
the bounded backend inventory against Journal ownership without trusting
directory names. The existing `bwork doctor --deep` invokes this storage check
when an active managed store exists while retaining all pre-existing
`artifact/1.0` path and Sigil checks.

Doctor never truncates the Journal, rewrites a cache, repairs a Replica,
releases a hold, moves a legacy anchor, disposes of bytes, or executes GC. If
the Journal cannot be trusted, Doctor may still emit a bounded diagnostic
report over independently read evidence, explicitly marks replay-derived
fields unavailable, and leaves storage in read-only `INTEGRITY_FAILURE`.
Unknown Schemas, incomplete inventory caused by a declared bound, or an
unresolved contradiction cannot produce a healthy result.

## Capacity, backpressure, and authorized disposition

The Execution Specification, backend profile, and active retention policy
bind immutable limits for each Transfer and materialization, aggregate staging
bytes and objects, quarantine bytes and objects, committed bytes and objects,
open file descriptors, and concurrent streams, plus separate reserves for
Journal growth, immutable control-record bytes, and recovery evidence. A limit
change is a new versioned policy or execution decision, never an in-place
relaxation.

Before issuing an output handle or beginning an import, export, or
materialization, the coordinator reserves the exact declared upper bound
against the relevant byte and object budgets. Insufficient capacity returns
typed `STORAGE_BACKPRESSURE`; no Job is launched and no write handle is
issued. `quota.pressure_entered` and `quota.pressure_cleared` journal the
bounded condition without repeatedly copying attacker-controlled requests.
An admitted operation may consume only its reservation. Growth past it fails
the attempt and cannot borrow quarantine capacity without a separate
reservation.

An RFC-0014 protected-root operation similarly reserves, before its first
write, one RootPlan control record for every root; an Evidence Manifest for
every event/suffix root; every manifest Blob/control member and Reference Set;
the hold and activation Event frames; the release-evidence record and release
Event; and, for tail recovery, all bounded TailRecoveryIntent stage records.
No later phase may discover an unreserved member or use a partial manifest to
fit capacity.

Every admitted Transfer, Materialization, Quarantine move, GC deletion,
disposition, and canonical-reference intent also reserves the profile-bounded
Journal and control-record bytes needed to reach one legal terminal or
recoverable state. A payload reservation that omits those lifecycle bytes is
invalid; backend side effects never begin on the hope that later record space
will become available.

The backend profile additionally withholds fixed
`system_journal_reserve_bytes`, `system_control_record_reserve_bytes`, and
`system_recovery_reserve_bytes` from every project quota limit. They are
available only through the eight `SystemReserveClass` limits and exact 61-row
capacity-source table above. That table includes initialization and migration
policy, coordinator liveness, clock and pressure, legacy protection,
verification and incidents, provenance, policy, holds, Reference Sets, GC
planning and skips, and tail/Recovery records; there is no implicit
“administrative” fallback. They never appear as free or reserved project
quota, cannot be lent to payload operations, and have the strict positive
capacity formulas, count bounds, and monotone physical-byte fold defined
above. Exhausting any class closes mutation admission and requires a new
versioned profile plus operator capacity; it never authorizes truncation or
deletion.

Journal and recovery reserve cannot be consumed by payload bytes. If the
coordinator cannot durably record a terminal outcome, it stops admitting
mutations and fails closed; it does not delete older records or bytes to make
space. Record retention and byte retention are distinct: Blob identities,
entity projections, Journal events, provenance, policies, failure evidence,
GC plans, dispositions, and tombstones remain even when an authorized policy
later removes their physical payload bytes. A retained record must expose
whether its bytes are `AVAILABLE`, `QUARANTINED`, `DISPOSED`, or
`HELD_FOR_DISPOSITION`. `NOT_CAPTURED` is permitted only when the coordinator
proved that no payload byte ever entered staging; it is never used for bytes
that may still exist.

Phase 3 never garbage-collects an immutable object in `records/` or retained
recovery evidence. Before the referring Event, their admission is charged to
the exact owner or system capacity source assigned by the 61-row table; an
unassigned record is invalid. A future compaction format would require an
accepted migration RFC that preserves every content identity and replay proof.

`artifact-storage-disposition/1.0` is the only Phase 3 operation that can
destroy uncommitted Transfer staging, Materialization staging, a failed or
expired Materialization destination, or quarantined bytes outside GC. Its
target kind selects exactly one owner projection: `STAGING` selects an
`SA-ID`, either materialization kind selects an `SM-ID`, and `QUARANTINE`
selects an `SQ-ID`. It is a closed, immutable authorization binding that exact
owner, backend generation, expected Sigil when known, exact size or upper
bound, reason, actor, policy and approval evidence, authorization time, expiry,
and idempotency identity. For either staging kind, the target object equals
the owner's replayed `HELD_FOR_DISPOSITION` residual object. For a
Materialization destination, it equals the intent destination selected by the
terminal `destination_state: HELD_FOR_DISPOSITION` or
`materialization.cleanup_failed` Event and current `cleanup: FAILED`. For
Quarantine it equals the retained destination in `HELD` or
`DISPOSAL_FAILED`, or in `FAILED` only when its terminal Event recorded
`destination_state: HELD_FOR_DISPOSITION`. Prefixes, wildcards, unresolved
paths, and post-approval target substitution are forbidden. The Journal records
authorization, start, completion or failure, and preserves the target record
and disposition tombstone.

Disposition projection effects are exact:

| Target kind | Started projection | Completed owner projection | Failed owner projection |
| --- | --- | --- | --- |
| `STAGING` | only Disposition becomes `EXECUTING`; the terminal Attempt remains unchanged | Attempt remains terminal, `staging_state` becomes `MISSING`, and matching `residual_staging_cleanup` becomes `CLEANED` with the deletion evidence | Attempt remains byte-for-byte unchanged |
| `MATERIALIZATION_STAGING` | only Disposition becomes `EXECUTING`; Materialization remains terminal | Materialization remains terminal and its matching `residual_staging_cleanup` becomes `CLEANED` with the deletion evidence | Materialization remains byte-for-byte unchanged |
| `MATERIALIZATION_DESTINATION` | only Disposition becomes `EXECUTING`; Materialization remains `FAILED` or `CLEANUP_FAILED` | lifecycle state remains terminal and `cleanup` becomes `CLEANED` with the deletion evidence | Materialization remains byte-for-byte unchanged |
| `QUARANTINE` | Quarantine enters `DISPOSING` | Quarantine enters `DISPOSED` | Quarantine enters `DISPOSAL_FAILED` |

The completed Event retains the exact removed `BackendObjectRef` even where an
owner projection's nullable live-object field becomes null. A completed
materialization-target disposition never turns a failed Materialization into
success or exposes its destination.

A disposition can never target an `AVAILABLE` Replica, canonical project
file, legacy v1 compatibility anchor, protected managed copy, Journal payload,
or active recovery material. Replica deletion remains the GC protocol.
Disposition is manual and explicit in Phase 3; quota pressure alone never
authorizes it. When a Quarantine reservation cannot be obtained, the failure
record says `HELD_FOR_DISPOSITION` and continues charging the exact staging
generation rather than pretending that an unrecorded deletion occurred. The
same rule retains and charges a Materialization staging or destination
generation until the matching materialization disposition branch removes it.

## Retention and garbage collection

Byte-retention policy applies to physical Replica, staging, and quarantine
payloads. It does not erase canonical events, logical Artifact records, Blob
identities, Storage Journal events, entity projections, transfer history,
provenance, policies, authorizations, failures, disposition records, GC
evidence, or deletion tombstones. Those identities and records remain
inspectable after bytes are removed. Conversely, retaining a Blob record does
not claim that its bytes remain available.

`artifact-retention-policy/1.0` is immutable and content-identified. It binds
scope, its contract version, minimum Replica requirements, integrity-check
freshness, retain-until and grace rules, automatic-GC permission, authorization,
and registration time. Holds are separate journaled projections that cite the
policy. Quarantine remains governed by its explicit state and disposition
protocol. Changing policy creates a new record and does not rewrite prior
decisions.

Every Blob projection binds the sorted set and Sigil of all active policies
whose closed scope matches it. The effective policy is their component-wise
strictest merge:

- minimum Replica count is the maximum;
- required backend or failure-domain sets are the union;
- maximum integrity age and deletion grace are the minimum non-null duration;
- retain-until time is the maximum;
- every hold and canonical pin is additive; and
- deletion, disclosure, or quarantine release is permitted only when every
  applicable policy permits it.

An unknown scope, incomparable rule, overflow, or contradictory requirement
fails closed, protects the bytes, and makes availability `DEGRADED` unless an
integrity incident independently selects `INCIDENT`. Replay orders policies by
policy ID and Sigil, applies this fixed merge, and records the resulting
`effective_policy_set_sigil`; current directory or map order is never an
input.

Protected roots include:

- every managed Blob explicitly bound to a verified canonical Artifact or
  other accepted canonical object under a defined retention rule;
- pinned research inputs, Result Bundles, reproduction material, and explicit
  legal or preservation holds;
- active or recoverable Jobs, Attempts, Leases, transfers, exports,
  materializations, and commit intents;
- every `OPEN` or `COMMITTED` canonical-reference intent;
- active or recoverable Patch Promotion and Recovery material represented by
  a registered operational Reference Set and durable hold;
- material required by an unexpired retention policy;
- Replica repair or reconciliation work in progress;
- quarantined material until its separate quarantine policy and exact
  disposition permit disposal; and
- every legacy v1 compatibility anchor, its protected managed copy, and the
  protection evidence created during upgrade.

A Promotion Journal, path, or checkpoint filename is not itself a storage
root. RFC-0014 must register the exact operational Reference Set and hold in
the Storage Journal before making checkpoint, intent, or recovery Blob
material visible; release requires its terminal/recovery Receipt and every
applicable retention policy.

The RFC-0014 boundary is specifically the single-assignment Promotion
activation Event slot first, control record or Evidence Manifest second,
Reference Set/registration Event third, immutable RootPlan fourth,
`retention.hold_set` fifth, and the one exact planned Promotion activation
Event/root last. Slot reservation fixes Event ID/type/payload field but is not
an Event and creates no state or root. The RootPlan is a durable control
record, not a Storage root; the active hold is the protection before and after
activation. Storage admits the hold by validating the plan and its
preallocated identities, never by reading a future Event/root. A crash after
only slot reservation leaves no hold; a crash after a plan or hold but before
activation leaves the corresponding plan-only or conservative hold orphan.
RFC-0014 v1 provides no
absence-, age-, or disposition-based release for it: only the exact planned
activation may resume, otherwise Doctor reports the plan/active hold/absent
activation and the hold remains. The plan, manifest, Set, hold, and activation
are each single assignment and cannot be rebound or reused for a second root.

The existing `artifact/1.0.location.uri` is not a managed Replica locator.
The storage subsystem must never move, replace, hard-link, or garbage-collect
that root-contained file. Importing it copies bytes and creates an explicit
operational binding; matching only its Sigil is not authority to change the
recorded path. This rule applies to ordinary v1 locations and to protected
historical locations under the now-reserved namespace.

### Schema-aware reference closure

GC reachability is a bounded, typed graph computation, not a scan for
digest-looking strings. Roots come only from a verified Chronicle snapshot,
the replayed Storage and execution journals, active retention policies and
holds, and legacy v1 protections. Each accepted Schema version has one closed,
versioned extractor that maps its typed fields to typed edges such as
`CANONICAL_BINDS_BLOB`, `JOB_REQUIRES_BLOB`, `TRANSFER_PINS_REPLICA`,
`BUNDLE_RETAINS_MEMBER`, or `HOLD_PROTECTS_BLOB`. Extractor code identity,
version, and Sigil form part of the conformance suite.

Higher-layer validators register an immutable
`artifact-storage-reference-set/1.0`. Its top-level fields are exactly
`schema_version`, `reference_set_id`, `source`, `extractor`, `edges`,
`validation`, `registration_event_id`, `created_at`, and
`reference_set_sigil`, with the exact `ReferenceSource`,
`ReferenceExtractor`, `ReferenceValidation`, and field types defined above.
`registration_event_id` is allocated before the record is made durable and is
the `reference_set.registered` Event ID; the record does not contain that
Event's Sigil and therefore creates no hash cycle.

Registration uses the deterministic identity and pending-candidate protocol
above. The first atomic candidate creation fixes `created_at`, the complete
canonical bytes, and deterministic Event ID before the Event append. A crash
between candidate creation, Event append, Head installation, set readback, and
higher-layer transition-request finalization always resolves and reuses that
same candidate and Event. It never allocates a second timestamp, ID, or
semantically duplicate set.

Each `edges` member contains exactly `relationship`, `target_kind`,
`target_identity`, and `target_sigil`. Members are unique and sorted by that
four-field tuple. Its field types and the only legal
relationship/source/target combinations are exactly the closed matrix above.

Every nested object is closed. `reference_set_sigil` is SHA-256 over canonical
JSON with that field omitted. Storage verifies the source record and its Sigil
through the named validator and never derives an edge merely by opening a
Blob. In particular, a Patch Bundle is an opaque Blob to storage; RFC-0014 or
its validator must register an explicit verified Reference Set for any base,
payload, rendering, or attachment whose bytes require transitive retention.

For source Schema `patch-operational-evidence-manifest/1.0`, the only
installed profiles are `extractor_id` and `validator_id`
`benchwork.patch-operational-evidence`, both version `1.0`, with the exact
profile Sigils defined by RFC-0014. The manifest is finalized before
registration and binds one preallocated Promotion Journal/Event/type/payload
field plus one closed Event-evidence or Journal-suffix branch. Extraction
produces exactly one `HOLD_PROTECTS_BLOB` edge per sorted `blob_refs` member
and one `CONTROL_RETAINS_CONTROL` edge per sorted `control_records` member;
the edge identity/Sigil pairs equal those members and no extra edge exists.
The distinct `control_records` plus `blob_refs`, the resulting `edges`, and
the complete computed `validation.evidence_sigils` are separately capped at
4,096 members. The first two collections have equal cardinality. The
RFC-0014 source preflight rejects any overflow before Manifest finalization;
Storage independently recomputes and rejects it before registration. A
duplicate control `(schema_version, record_id)` with a different Sigil or a
duplicate Blob Sigil with a different size is an integrity conflict.
Every manifest `evidence_sigils` value resolves uniquely to exactly one such
Blob or control member. The validation evidence is the exact sorted unique
union of the manifest Sigil, its typed evidence/member Sigils, and, only for
the suffix branch, the two Head and classification Sigils; its
`source_validation_sigil` is RFC-0014's exact domain-separated formula over
the source pair, both profile tuples, sorted edges, and that evidence set.
A bare or multiply typed Sigil, unknown owner/role/Event combination, changed
member, null-branch manifest, or any future Set/Event/RootPlan/hold/Head/
TailRecoveryIntent Sigil is invalid. Registration never reads a future
Promotion Event or OperationalRoot.

The executable fixture set contains one positive case for every row and every
listed alternative target of the matrix, plus a rejection for every
relationship paired with each unlisted source or target kind, wrong identity
type, wrong target Sigil, wrong source Sigil, extra property, duplicate edge,
or non-canonical order.

A missing extractor for a reachable Schema, an unknown Schema or relationship,
an absent required Reference Set, a mismatch between a source and its
Reference Set, or invalid extraction evidence aborts planning and protects the
affected material. The planner never guesses an edge from a filename, media
type, backend key, untyped JSON member, or Sigil-looking text.

Closure follows typed edges transitively and detects cycles. The retention
policy binds maximum roots, nodes, edges, depth, aggregate control-record
bytes, and wall time. Reaching any bound, arithmetic overflow, unstable source,
or cycle-processing error aborts the plan with retained evidence; it cannot
use a partial traversal to conclude that a Blob is unreachable. A completed
GC plan binds the ordered root set, all Reference Set Sigils, extractor suite
Sigil, traversal bounds, visited-node and edge counts, cycle summary, and the
resulting reachable Blob and Replica sets.

Reference Intent admission uses the same deterministic typed traversal with
the listed `reference_sets` as its exact roots. It resolves each root and every
reachable `REFERENCE_SET` target by both ID and Sigil, follows each verified
edge once in canonical tuple order, collects every reachable `BLOB` target,
and also collects the Blob identity of every reachable `REPLICA`. Cycles are
collapsed by the exact `(target_kind, target_identity, target_sigil)` node
key. The universal `4096` collection bound applies independently to root
sets, visited nodes, visited edges, traversal depth, and the resulting Blob
set; reaching a bound before proving completion, or encountering an unknown,
missing, mismatched, unstable, or invalid node or edge, rejects admission
before `canonical_reference.intent_recorded`.
The Reference Intent's `blob_sigils` must equal the resulting sorted unique
Blob set byte-for-byte and has length `0..4096`. An empty array is valid
exactly when the completed closure contains no Blob; it does not authorize a
placeholder Blob, an unrelated pin, or a partial traversal. Replay recomputes
this equality from the immutable Reference Sets rather than trusting the
stored array.

The GC hash graph is exact. `H(x)` below is SHA-256 over canonical JSON bytes;
each tuple array is unique and lexicographically sorted by the fields shown:

```text
hold_set_sigil =
  H([[hold_id, target_kind, target_id, policy_id,
      set_authorization_sigil, last_event_sigil], ...])

legacy_protection_set_sigil =
  H([[protection_id, artifact_id, blob_sigil, protected_replica_id,
      record_sigil, last_event_sigil], ...])

reference_intent_set_sigil =
  H([[reference_intent_id, state, record_sigil, last_event_sigil], ...])

policy_set_sigil =
  H([[policy_id, record_sigil, last_event_sigil], ...])

execution_root_set_sigil =
  H(complete ExecutionRootSnapshot with root_set_sigil omitted)

root_snapshot_sigil = H(complete GCRootSnapshot)
proof_sigil = H(complete ClosureProof with proof_sigil omitted)
```

The hold array contains active holds; the legacy array contains every
protected legacy entry; the reference-intent array contains every `OPEN` or
`COMMITTED` intent; and the policy array contains every policy applicable to
any root or target. `GCRootSnapshot.reference_set_sigils` is the sorted unique
array of every complete Reference Set traversable from those roots. Its
`execution_roots.root_set_sigil` is computed by the separate formula below.
Its `storage_event` is the verified Storage prefix immediately before
`gc.plan_created`, so it cannot refer to the plan Event itself.

For an `artifact-gc-plan/1.0`, let `root_snapshot` and `closure_proof` denote
those exact nested fields and let `event` denote the exact
`gc.plan_created.payload` that refers to the plan. All of these equalities are
mandatory:

```text
root_snapshot.hold_set_sigil == hold_set_sigil
root_snapshot.legacy_protection_set_sigil == legacy_protection_set_sigil
root_snapshot.reference_intent_set_sigil == reference_intent_set_sigil
root_snapshot.policy_set_sigil == policy_set_sigil
root_snapshot.execution_roots.root_set_sigil == execution_root_set_sigil
closure_proof.root_set_sigil == root_snapshot_sigil
closure_proof.extractor_suite_sigil == gc_plan.extractor_suite_sigil
closure_proof.bounds == gc_plan.bounds
closure_proof.proof_sigil == proof_sigil
event.root_snapshot_sigil == root_snapshot_sigil
event.closure_proof_sigil == proof_sigil
event.target_ids == [target.target_id for target in gc_plan.targets]
```

Targets are sorted and unique by `target_id`; their Blob, Replica, backend
generation, reason, and expected remaining Replica arrays are covered by the
GC plan's `record_sigil`. The Event's `gc_plan` Ref resolves that exact record.
A mismatched component-set Sigil, proof/root binding, bound, extractor, target
order, target identity, or self-Sigil is a Schema or replay failure and cannot
be authorized or revalidated.

### Canonical-reference gate

A Chronicle transition that would make a managed Blob reachable has a
cross-journal write-ahead protocol. `artifact-storage-reference-intent/1.0`
contains exactly `schema_version`, `reference_intent_id`,
`transition_request_id`, `transition_request_sigil`, `canonical_event_type`,
`expected_chronicle_head`, `reference_sets`, `blob_sigils`, `actor_id`,
`authorization_sigil`, `idempotency_key_sigil`, `requested_at`, and
`record_sigil`. `expected_chronicle_head` contains exactly
`schema_version: chronicle-head/1.1`, `event_count`, and
`terminal_receipt_sigil`. Each sorted unique `reference_sets` member contains
exactly `reference_set_id` and `reference_set_sigil`; `blob_sigils` is sorted
and unique, has length `0..4096`, and equals the exact Reference Set closure
defined above. The empty array is legal only for a completed closure with no
reachable Blob. `transition_request_sigil` identifies the complete closed
Athanor request independently of any not-yet-created Event or Receipt. Every
nested object is closed, and `record_sigil` covers canonical JSON with that
field omitted.

Although the existing `chronicle-head/1.1` Schema permits an unbounded
non-negative integer, this protocol admits a canonical-reference operation
only when the replayed `event_count` is strictly less than `U63_MAX`. The
current Head therefore fits `ChronicleHeadRef`, and the one Event that the
candidate may commit has a representable resulting count. At
`event_count == U63_MAX`, or for any greater Chronicle Head accepted by the
older Schema, the coordinator fails closed before Reference Set registration,
Reference Intent creation, Reservation, or Chronicle submission. It preserves
existing state and requires a future versioned migration; it never wraps,
clamps, or serializes a wider count into this contract.

`canonical_event_type` is exactly one of
`agent-result.accepted`, `patch.proposed`, `patch.validation.recorded`,
`patch.promotion.authorized`, `patch.promotion.rejected`,
`patch.promotion.outcome-recorded`, or
`patch.promotion.recovery-recorded`. A later canonical event family that
creates, changes, or removes managed Blob reachability must version this
contract rather than pass an unrecognized string.

`canonical_reference.committed` is legal exactly once from `OPEN`. It resolves
the immutable Reference Intent and complete transition request by the
intent's ID/Sigil pair, then resolves one exact `chronicle-event/1.1` and
paired `receipt/1.1`. Validation requires:

```text
event.type == intent.canonical_event_type
event.sequence == intent.expected_chronicle_head.event_count + 1
event.previous_receipt_sigil
  == intent.expected_chronicle_head.terminal_receipt_sigil

chronicle_commit.event_id == event.event_id
chronicle_commit.event_body_sigil == event.event_body_sigil
chronicle_commit.receipt_id == event.receipt.receipt_id
chronicle_commit.receipt_sigil == event.receipt.receipt_sigil
chronicle_commit.head == {
  schema_version: "chronicle-head/1.1",
  event_count: intent.expected_chronicle_head.event_count + 1,
  terminal_receipt_sigil: chronicle_commit.receipt_sigil
}
```

The Event Body Sigil and Receipt Sigil are recomputed. The ordinary RFC-0001
Receipt equalities for Event ID, Event Body Sigil, previous Receipt Sigil, and
accepted/occurred time all hold. The event-family resolver validates the
complete request-to-candidate mapping, including transition-request ID and
Sigil, Reference Intent ID and record Sigil, Reference Set pairs, actor,
authorization, idempotency identity, and every family-specific payload field.
A different Event, Receipt, resulting Head, request, candidate payload, or
set projection is an integrity conflict.

`canonical_reference.released` is legal exactly once from `OPEN`, with
`release_kind: ABORTED_BEFORE_CANONICAL_COMMIT`,
`chronicle_commit: null`, and the complete `CanonicalAbortAuthority`. Its
members equal the Reference Intent and request byte-for-byte, and:

```text
absence_evidence_sigil =
  Sigil(["artifact-storage-canonical-precommit-absence/1.0",
         reference_intent_id,
         reference_intent_record_sigil,
         transition_request_id,
         transition_request_sigil,
         expected_chronicle_head,
         verified_chronicle_head])

authority_sigil =
  Sigil(<complete CanonicalAbortAuthority with only authority_sigil omitted>)
```

While holding the canonical-reference gate, complete Chronicle replay must
validate both Heads, prove
`verified_chronicle_head.event_count >
expected_chronicle_head.event_count`, and prove that the complete suffix after
the expected Head contains no Event that the event-family resolver binds to
this request or intent. The old conditional candidate can then no longer
commit. The release `reason.code` is `CHRONICLE_REFERENCE_CHANGED` and its
`evidence_sigils` is exactly the sorted unique set of the authority Sigil,
absence-evidence Sigil, Reference Intent record Sigil, and transition-request
Sigil. If the current Head is unchanged, any replay is unavailable or
ambiguous, or a bound Event exists, the intent remains `OPEN`.
`CANONICAL_REFERENCE_REMOVED` is forbidden in v1.

The project has one outermost **canonical-reference gate**. Every Phase 3
Athanor transition that creates, changes, or removes a managed Blob binding
must:

1. acquire the gate, register any newly derived Reference Set, and verify
   Chronicle, Storage Journal, candidate request, every Reference Set,
   extractor, validation evidence, and Blob;
2. append `canonical_reference.intent_recorded` before the Chronicle
   transaction, pinning the exact intent record, request, Reference Sets, and
   exact closure-derived Blob set, including a legal empty set;
3. release the Storage Journal lock while retaining the gate, then ask Athanor
   to commit the exact candidate conditional on `expected_chronicle_head`;
4. require the canonical event payload to bind `reference_intent_id`,
   `record_sigil`, `transition_request_sigil`, and every Reference Set ID and
   Sigil; and
5. after Athanor returns a verified Receipt, append
   `canonical_reference.committed` with the canonical Event ID, Event Body
   Sigil, Receipt ID and Sigil, and resulting Chronicle Head, then release the
   gate.

Reference Set registration alone is not a root and grants no canonical
authority. A caller deriving a set for this transaction retains the gate from
registration through intent append; if it cannot append the intent, it creates
no Chronicle Event and leaves the verified bytes as ordinary unreferenced
operational storage subject to their existing policy.

Intent admission reserves Journal and control-record capacity for exactly one
terminal path—`canonical_reference.committed` or the aborted
`canonical_reference.released` branch—plus bounded recovery evidence. Either
terminal Event settles the Reservation; a committed v1 pin has no later
release reserve. Without the complete terminal-path reserve, the coordinator
does not append the intent or call Athanor.
The lifecycle Reservation is canonical-lifecycle capacity, not a lease:
`expires_at` and `remaining_micros_at_creation` are both null in the
`canonical_reference.intent_recorded` payload. The open intent's
`source_event` resolves that exact active Reservation and preserves it
byte-for-byte until one terminal path settles it. The committed pin itself is
the durable `COMMITTED` reference-intent projection and does not depend on a
retained quota Reservation.

The raw Receipt is the ordinary outer Event Receipt and is not embedded in the
canonical event payload. A failed Athanor transaction does not erase the
intent. While holding the gate, recovery verifies the complete Chronicle. If
the exact bound event and Receipt exist, it appends the missing committed
Event. If the candidate is absent and the verified Head has advanced past the
expected Head, it may append `canonical_reference.released` only with the
exact `HEAD_SUPERSEDED_WITHOUT_BOUND_EVENT` proof above. If Chronicle is
unavailable, invalid, unchanged, or ambiguous, the intent remains `OPEN`,
pins all named Blobs, and blocks both GC and another transition using that
idempotency identity.

A committed pin is permanent in Phase 3. Storage expiry, policy change, Job
termination, an absent file, or an unversioned removal claim never implies
release. A future canonical-removal Event family and Receipt protocol must
version this contract before a committed pin can have an outbound transition.

The same outer gate linearizes execution roots. Before an RFC-0012 execution
event can first expose a managed Blob as a Job input, Attempt input, or Attempt
output, the Executor holds the gate, registers the exact
`OPERATIONAL_CONTROL_RECORD` Reference Set, and appends its durable Storage
hold. It then releases the Storage Journal lock, appends the execution event
that binds the Reference Set and hold, and only then releases the gate. The
final activation check re-resolves the hold as `ACTIVE` and proves that the
deterministic EHR for its hold ID does not exist. A crash before the execution
event leaves a conservative orphan hold. Because no execution Event activated
an owner, this is not an execution-recovery action and cannot fabricate an
execution release observation. Only when no Execution Recovery is active may
the Storage-side orphan reconciler, or the exact Start retry before a new
activation is considered, release it by durably creating the exact RFC-0012
`ORPHAN_ABORT` EHR under the gate after verified Execution replay proves the
sole activation absent. That EHR is a permanent activation veto; a late Event
cannot expose the root.

Removal uses the reverse safe order under the same gate: first append the
execution event that makes the root inactive, then durably create the exact
`OWNER_TERMINAL` or `OUTPUT_DEADLINE` EHR, then append
`retention.hold_released`. A crash leaves an extra hold, never a missing live
root. `JOB_INPUT` and `ATTEMPT_INPUT` use only their exact owner-terminal EHR;
`ATTEMPT_OUTPUT` uses only its immutable deadline EHR. A canonical Agent
Result transition establishes an independent additive pin and never releases
or shortens the execution hold. An output hold may remain overdue only while
trusted clock, execution replay, EHR, or Storage-prefix proof is unavailable
or ambiguous; this fail-closed retention does not move its scheduled
deadline.

`ExecutionStorageRoot` has exactly the nine fields in its `$defs` row and is
byte-for-byte compatible with RFC-0012's
`execution-journal-event/1.0#/$defs/storage_root_binding`. Entries are sorted
by `(root_kind, job_id, attempt_id, storage_root_manifest_id,
reference_set_id, hold_id)`. `storage_root_manifest_id` is the exact
`ESM-` identity of one RFC-0012
`execution-storage-root-manifest/1.0`, and
`storage_root_manifest_sigil` is that complete document's self-Sigil. The
nullable Attempt ID is null only for `JOB_INPUT`; it is non-null and equals
the owning Attempt for `ATTEMPT_INPUT` or `ATTEMPT_OUTPUT`.
`ExecutionRootSnapshot.root_set_sigil` is SHA-256 over the complete closed
snapshot with that field omitted. Its event count and nullable last-event
Sigil are the verified Execution Journal Head at the same replay point; zero
count requires null last-event Sigil. Every root's ESM, Reference Set, active
hold, and `hold_set_event` must replay exactly. In particular:

1. the manifest pair resolves one complete
   `execution-storage-root-manifest/1.0` whose `manifest_id`,
   `manifest_sigil`, `root_kind`, `job_id`, and `attempt_id` equal the root
   byte-for-byte; its single-assignment resolver rejects a second byte
   sequence for the same ID;
2. the ESM has `protection_plan.kind: PLANNED`; its preallocated
   `reference_set_registration_event_id`, `hold_id`, and
   `hold_set_event_id` equal the registered Reference Set Event ID, this
   root's `hold_id`, and `hold_set_event.event_id`, respectively, and its
   policy ID and Sigil equal `SP-EXECUTION-ROOT-HOLD-V1` and its exact
   initialized project policy cited by the hold;
3. the Reference Set resolves with exactly `reference_set_id` and
   `reference_set_sigil`, and its special ESM-ID-derived
   `registration_event_id` equals the ESM's precomputed registration Event ID;
4. the hold is `ACTIVE`, has `target_kind: REFERENCE_SET`, and has
   `target_id == reference_set_id`;
5. `hold_set_event` is the exact `retention.hold_set` Event that created that
   hold, and its `hold_id`, target kind, target ID, policy ID, and
   authorization Sigil equal the replayed hold byte-for-byte and the exact
   RFC-0012 post-registration formula; and
6. the set's source is exactly
   `{kind: OPERATIONAL_CONTROL_RECORD, identity:
   storage_root_manifest_id, schema_version:
   execution-storage-root-manifest/1.0, sigil:
   storage_root_manifest_sigil}`. Its installed extractor and validator equal
   the profiles pinned by RFC-0012, and its sorted edges are the complete ESM
   `blob_refs` closure: `JOB_INPUT` uses `JOB_REQUIRES_BLOB`, while
   `ATTEMPT_INPUT` and `ATTEMPT_OUTPUT` use `CONTROL_RETAINS_BLOB`. Its
   source-validation and evidence Sigils equal the exact RFC-0012 formulas
   and exclude every future Set/Event/hold/release Sigil.

Every edge has `target_kind: BLOB` and
`target_identity == target_sigil == manifest BlobRef.blob_sigil`; the edge
projection equals the manifest's sorted unique BlobRef projection exactly.
An active hold on a Blob, Replica, or different Reference Set cannot protect
this root. An incomplete edge set, mismatched source/owner, wrong
relationship, or valid but unrelated hold invalidates the snapshot and
protects conservatively.

### Execution-owned output-hold deadline

For an `ATTEMPT_OUTPUT` ESM, `protection_plan.hold_lifetime` is exactly
`OUTPUT_RETENTION {kind, maximum_duration_seconds}`. That duration is the
maximum lifetime of this one execution-owned `SH-ID` after the root's parent
Job becomes terminal. It is not an
`artifact-retention-policy/1.0.retain_until` minimum, does not rewrite that
policy, and does not bound any canonical pin, legal hold, preservation hold,
different execution hold, Quarantine protection, or open reference intent.

While holding the canonical-reference gate, the Executor and Storage derive:

```text
release_due_at =
  checked_utc_add(
    parent_job_terminal_event.recorded_at,
    protection_plan.hold_lifetime.maximum_duration_seconds)
```

The Job terminal Event is the sole RFC-0012 inactivation event for this
`ATTEMPT_OUTPUT` root. Its exact Event identity, Event Sigil, and
`recorded_at`, plus the ESM ID/Sigil and hold ID, are the release
authorization evidence. Its closed RFC-0012
`output_hold_release_schedules` entry repeats the Attempt, ESM, Reference Set,
hold, and hold-set Event, sets `root_inactivation_event_id` to that enclosing
Event ID, and repeats the bound duration. Checked addition that produces a
representable RFC 3339 UTC timestamp records that value with
`deadline_status: EXACT`. Overflow never wraps, saturates, or becomes an
indefinite duration: the schedule instead repeats the terminal
`recorded_at` and uses `OVERFLOW_FAIL_CLOSED`. The inactivated root is
therefore immediately due for this execution-hold release, while a
`CODE_MODIFICATION` Job with that schedule cannot be `SUCCEEDED`.

Canonical acceptance, a replacement pin, and every other earlier narrowing
are invalid release bases in v1. Storage appends exactly one
`retention.hold_released` for this `hold_id` only when an `EXACT`
`release_due_at` becomes due, or immediately after inactivation for an
`OVERFLOW_FAIL_CLOSED` schedule whose due time is the terminal
`recorded_at`. Before that append the Executor creates or resolves the
deterministic `OUTPUT_DEADLINE` EHR. The Storage Event uses
`reason.code: EXECUTION_HOLD_LIFETIME_EXPIRED` and the schedule-bound
authorization and evidence defined in the Event rules above. RFC-0012 then
appends `storage_root.hold_release_observed` with that complete schedule, EHR
ID/Sigil, and exact Storage release `EventRef`. A zero duration takes this
reverse-order branch immediately after the Job terminal Event. Process restart
or Recovery never recomputes or moves an exact deadline: under the gate it
reuses an already committed EHR and Storage release or, once trusted time
proves the immutable deadline due, appends the missing release and
observation. Clock uncertainty, unavailable journal replay, or an ambiguous
prefix or EHR preserves the hold and blocks new time-authorized finalization,
disposition, and GC until the release preconditions can be proved.

That Event advances only the named hold projection from `ACTIVE` to
`RELEASED`; its revision set remains exactly `HOLD`. It does not release,
shorten, supersede, or mutate the referenced retention policy, Reference Set,
canonical-reference intent, canonical Artifact pin, legal/preservation root,
Quarantine record, another `SH-ID`, or any Blob or Replica record. The
effective root set is then recomputed additively. Any surviving policy,
canonical root, legal/preservation hold, Quarantine protection, recovery
root, or different hold continues to block GC. Releasing this hold is never
byte-deletion authority and never proves that any Replica is eligible for
deletion.

Lock order is always canonical-reference gate first. While holding it, a
coordinator may take and release the Storage Journal lock, Execution Journal
lock, or Chronicle lock, but never holds two journal locks simultaneously and
never tries to acquire the gate while holding any one. This ordering is part
of the local conformance suite.

`LOCAL-PHASE3/1.0` realizes the gate as an exclusive Host-kernel lock on the
fixed coordinator-owned
`.benchwork/locks/canonical-reference.lock`, opened descriptor-relative with
no-follow validation. It never steals authority from a PID, timestamp,
hostname, or stale-looking file; kernel release on process death is followed
by intent recovery before a new holder proceeds. Failure to prove exclusive
ownership is `STORAGE_BACKPRESSURE` or
`INTEGRITY_FAILURE`, never an unlocked fallback. A multi-Host or remote gate
requires the later portable conformance profile.

### Plan and execution

Garbage collection is mark-and-sweep over an immutable root snapshot and
Storage Journal generation. Reference count alone is insufficient because
crashes, delayed canonical transitions, retention changes, and concurrent
imports can make it stale. GC follows:

1. validate the retention policy and authorization;
2. capture and Sigil-bind the Chronicle Head, Storage Journal event,
   `ExecutionRootSnapshot`, holds, legacy protections, Reference Sets, and
   extractor-suite Sigil;
3. compute the complete bounded transitive closure described above;
4. create a deterministic dry-run plan with exact Replica IDs, Blob
   identities, backend generations, reasons, closure proof, and expected
   remaining availability;
5. retain that immutable plan for the policy grace period and obtain explicit
   authorization for exactly its targets;
6. immediately before each deletion, acquire the canonical-reference gate,
   replay current Chronicle and release its lock, replay the Execution Journal
   and release its lock, verify every execution root's active Storage hold,
   then acquire the exclusive Storage Journal lock, replay storage state,
   resolve every reference intent, and recompute that target's reachability
   from every current root through all of its current ancestor edges;
7. while retaining the gate, revalidate holds, legacy protections, active
   transfers, policy, integrity freshness, Replica generation, minimum Replica
   count, the exact backend object, and every namespace ancestor, and reserve
   Journal capacity for the target's durable deletion or failure outcome;
8. append `gc.target_deletion_started` while retaining both locks,
   conditionally delete only the approved generation, verify the bounded
   backend outcome, append the target tombstone or failure, and only then
   release the Storage Journal lock and gate; and
9. retain the plan, authorization, closure evidence, skips, and all failures.

Target-specific revalidation is mandatory even when the Chronicle or Journal
Head has not changed; matching Heads are not proof that paths or backend
generations are unchanged. If either Head has changed, the coordinator
recomputes current typed reachability for the target and its ancestors rather
than trusting the old closure. A new root or edge, a removed or changed
Reference Set, an unknown ancestor, a traversal bound, changed hold, policy,
active transfer, integrity status, minimum count, or legacy protection skips
that target. It does not authorize a different target, and GC never broadens
the approved set.

The gate remains held from the final current-root computation through the
durable deletion outcome, so no new canonical or execution reference can
commit between the reachability decision and physical deletion. Every `OPEN`
or `COMMITTED` canonical-reference intent and every active execution hold is a
root. Recovery ambiguity therefore protects bytes rather than permitting
deletion. This protocol, rather than Head equality or a second unlocked
lookup, closes both canonical-reference and execution-root GC
time-of-check/time-of-use races.

For `LOCAL-PHASE3/1.0`, the exclusive Storage Journal lock also remains held
from final replay through the durable target outcome. Consequently no hold,
policy, transfer, materialization, disposition, Replica observation, or other
operational root can interleave after revalidation. Backend deletion has a
profile-bound timeout; timeout records `gc.target_failed` before either lock
is released. A later portable profile may replace the long-held local lock
only with a conformance-proven transactional fence that gives the same
linearization.

For the local backend, deletion is anchored at an already opened trusted
directory descriptor for `.benchwork/storage/` and uses no-follow,
descriptor-relative operations or an equivalent proven primitive. Immediately
before deletion, it validates each ancestor component's expected type,
identity, device, inode or platform file identity, permissions, and generation,
then validates that the target is the expected regular immutable file with the
approved Replica ID, Blob Sigil, size, and generation. A symlink, mount,
rename, replacement, hard-link ambiguity, ownership change, or failed
ancestor check skips the target and records evidence. A remote backend must
provide equivalent namespace confinement and delete only with an exact
immutable-generation precondition.

Normal GC must not remove the last eligible managed Replica of a
canonically-retained Blob. A destructive policy that intentionally permits
loss of the final copy requires a later accepted production contract; the
Phase 3 staging/quarantine disposition cannot authorize it. GC also never
classifies a failed or negative scientific Run as disposable merely because
its outcome is undesirable.

The Phase 3 reference runtime performs no automatic GC. Its three physical
cleanup authorities are closed: a Transfer commit intent may roll back only
its exact unpublished provisional generation; an exact authorized disposition
may delete only one of its four uncommitted or quarantined target kinds; and an
exact manually authorized GC plan may delete only the eligible committed
Replica generations enumerated by that plan. Disposition and GC require
recovery to prove that each target is neither live nor protected, and Phase 3
GC may never remove the last eligible Replica of a canonically retained Blob.
Committed Attempt outputs remain retained by default; failed and late output
records always remain, while their bytes follow the separately recorded
quarantine-retention outcome. Phase 4 must supply the
`PORTABLE-PHASE4/1.0` policy, authorization, race, crash, last-Replica,
replication, deletion, and restore conformance before automated GC is enabled.

## Quarantine and corruption

Quarantine is separate from staging and from the committed Replica namespace.
Staging is expected transient work owned by a live or recoverable Transfer;
quarantine is a terminal isolation decision with its own identity, evidence,
reservation, retention state, and authorization boundary. A pathname move
alone cannot change either state.

Bytes enter quarantine when Benchwork observes at least:

- partial, truncated, over-limit, or timeout-terminated transfer;
- expected-versus-computed Sigil or size mismatch;
- unknown digest algorithm or ambiguous encoding;
- path escape, symlink or hard-link ambiguity, special file, or unsafe bundle;
- stale or fenced Lease, duplicate completion conflict, or late output;
- backend generation, visibility, durability, or readback contradiction;
- corrupt known Replica, suspected collision, or catalog contradiction;
- malformed or missing required provenance; or
- policy, authorization, secret-handling, or cleanup violation.

A quarantine record binds the original request, claimed and computed
identities where available, byte count, source, Job and Attempt context,
reason code, evidence Sigil, isolation location, access policy, and retention
decision. It also records whether bytes were retained and their exact backend
generation. It must not copy secrets into metadata.

Quarantined bytes:

- are never selected for materialization, export, deduplication, Replica repair,
  result eligibility, or Artifact registration;
- are unreachable to Workers and ordinary storage readers;
- do not count toward Replica availability or retention minimums;
- remain bounded by quarantine storage quotas; and
- may be inspected or disposed of only through an explicit audited operation.

Successful reinspection does not silently flip the original transfer to
success. It creates a new verified import or Replica record that cites the
quarantine evidence, while the original failure remains. Disposal removes only
the quarantined bytes and preserves the record and evidence identity. Quota
pressure does not authorize eviction: if a reservation cannot be obtained,
the coordinator leaves the exact staging generation
`HELD_FOR_DISPOSITION`, retains the failed-transfer and quota evidence, and
does not claim that Quarantine bytes exist.

When a committed Replica fails verification, the coordinator marks that
Replica `CORRUPT`, stops serving it, and verifies another Replica before
failover. It may separately copy bounded forensic bytes into a new Quarantine
record, but the Replica itself never changes identity or becomes quarantined.
It never repairs in place by overwriting the corrupt generation. If no
eligible Replica remains, the Blob becomes `UNAVAILABLE` or `INCIDENT`, and
dependent work fails closed.

Quarantine is an operational safety state, not a scientific conclusion.
Benchwork may propose an Issue or Deviation from its evidence, but only Athanor
can accept that separate transition.

## Authorization and isolation

Storage permissions are deny-by-default and appear explicitly in the Phase 3
Capability, Task Capsule, Execution Specification, and Ward decision. A
filesystem read permission does not imply Blob import, backend read, export,
retention change, quarantine inspection, or deletion authority.

The minimum distinct permissions are:

- select a declared Blob as an immutable input;
- materialize that input into a named Task scope;
- write bounded Attempt output into isolated staging;
- finalize eligible output after Lease and policy validation;
- export a Blob to one declared destination class;
- inspect storage metadata or quarantine;
- set a retention hold;
- authorize one exact staging or quarantine disposition;
- execute one already authorized exact disposition; and
- execute a specific GC plan.

MCP and Worker surfaces remain typed and content-scoped. They expose no
general backend key, arbitrary path, bucket, prefix, filesystem, or deletion
operation. The Worker cannot choose a storage namespace, override a Sigil,
disable verification, release quarantine, authorize disposition, change
retention, or invoke GC.

At A1, the local runtime supervises cooperative output capture and removes
ambient credentials but does not claim containment of malicious code. At A2,
the complete committed store, Storage Journal, quarantine, backend credentials,
and `.benchwork/` tree are unreachable to the Worker. Only declared immutable
inputs and an Attempt-scoped bounded output handle cross the Circle.

Storage authorization does not authorize external disclosure. An export to a
remote or external party requires the exact destination and disclosure policy
to be approved under the applicable Review or future transport contract.

## Compatibility and migration

This RFC does not reinterpret or rewrite an already accepted
`artifact/1.0`, its Schema identifier, event payload, projection, Receipt, or
Chronicle replay. It does make one deliberately versioned Alpha-era safety
tightening to admission: after the storage-format upgrade, new registrations
cannot use the reserved `.benchwork/storage/` namespace. The CLI, MCP, and
Doctor surfaces must report this as the new validator rule, not as a new
meaning for historical events.

Outside that namespace, the accepted Athanor semantics remain:

- `artifact_id` uses an `AR-` identifier and is unique;
- `program_id` identifies an existing Research Program;
- `kind` is non-empty;
- `location` contains exactly `uri` and `sigil`;
- `location.uri` resolves within the project and is readable at registration;
- `location.sigil` is SHA-256 over the exact file bytes;
- `producer_id` and every `input_id` identify existing objects in the same
  Program;
- registration is immutable, sets `status: REGISTERED`, advances applicable
  Working state, and carries the Chronicle time and Receipt; and
- later integrity inspection expects the recorded local bytes to remain
  available and to match their Sigil.

For every new registration, Athanor adds only two reserved-namespace checks to
the existing v1 resolution behavior:

1. if the lexical URI can be expressed beneath the project root, normalize
   that comparison path without following links and reject it when it equals
   `.benchwork/storage` or has that directory as an ancestor; and
2. resolve the candidate exactly as the current v1 implementation does,
   including its existing symlink-following and root-containment behavior, and
   reject it when the resolved target is inside or aliases the reserved
   namespace.

An absolute URI or symlink alias that the existing implementation resolves
inside the project and outside the reserved namespace remains admissible.
This RFC does not introduce a general lexical-root-containment or no-follow
rule for ordinary v1 Artifact files. Only managed-store internals use the new
no-follow primitives. Reserved-path comparison follows the Host filesystem's
case and Unicode semantics and fails closed only when that reserved-boundary
decision is ambiguous. These checks happen before streaming content hashing or
Chronicle append.

In particular, `artifact/1.0.location` is never reinterpreted as:

- a Blob record, Replica ID, backend key, Replica set, cache pointer, mutable
  URL, retention promise, or availability claim;
- the digest of a directory walk, metadata document, ciphertext, or storage
  manifest instead of the referenced file bytes; or
- permission for a backend to move, rewrite, replace, or delete the recorded
  project file.

The existing Schema's reference shape does not override Athanor's exact-field
and project-path checks. A backend URI that current Athanor cannot resolve and
read as a project-local file cannot be placed into `artifact/1.0.location` to
simulate migration. A backend locator, URI, or object key is opaque operational
metadata even if it can be made to resemble a relative file path. To register
managed bytes under v1, a caller must explicitly materialize and verify a
durable independent file outside `.benchwork/storage/`, then invoke the v1
registration with its ordinary producer and input lineage.

Upgrade preflight is mandatory before `storage.activation_completed`:

1. replay Chronicle and enumerate every already accepted v1 location;
2. normalize and resolve each location under the historical Host rules and
   identify every lexical or physical alias of `.benchwork/storage/`;
3. verify the immutable Artifact record, Receipt, current exact bytes, and
   recorded Sigil using bounded streaming;
4. after `storage.initialized`, reserve capacity and run the exact
   `LEGACY_V1_PROTECTION` Transfer through staging, durable commit intent,
   conditional finalize, and readback, without moving, linking, renaming, or
   overwriting the recorded path;
5. make one closed `artifact-storage-legacy-protection/1.0` record durable,
   binding the Artifact and Program, Receipt, a Sigil of the recorded URI,
   lexical and resolved file identities, anchor observation, Blob, verified
   managed Replica and Transfer, and `LegacyExclusion`, then append one
   `legacy_v1.protection_registered` event whose `protection` Ref identifies
   that exact record; and
6. activate storage only after replay proves that every discovered alias has
   exactly one valid protection.

The historical v1 path is a compatibility anchor, not a backend Replica. It
remains subject to the existing Deep Doctor byte check and is excluded from
backend key allocation, staging, reconciliation ownership, disposition, and
GC. Its protected managed copy is also a permanent GC root while v1 depends on
that anchor. Missing or changed bytes, an unreadable Receipt, path ambiguity,
insufficient migration capacity, or collision with required internal files
such as `format.json` or `journal.frames` emits or retains migration failure
evidence and blocks activation. The upgrader never rewrites the Chronicle
event, repairs the anchor from the copy, hides the conflict, or treats a
backend URI as the old file.

Existing v1 locations outside the reserved namespace keep their prior
behavior. They may be explicitly imported into managed storage, but import
only copies and binds verified bytes operationally; it does not update their
recorded location. Deleting or losing every ordinary managed Replica never
deletes or rewrites an `artifact/1.0` record. A future canonical Artifact
contract that natively binds a Blob independent of a project path must use a
new Schema and event version with an accepted RFC, migration guidance,
fixtures, and replay coverage.

Existing inline Artifact references in Runs, Workings, Evidence, and other
Phase 2 contracts retain their meanings. New storage fields are not smuggled
into their existing `uri`, `sigil`, or provenance fields.

## Threat model

### Assets

The model protects:

- the mapping from Blob Sigil to exact logical bytes;
- canonical Artifact records, Chronicle, Receipts, and `.benchwork/` state from
  storage or Worker mutation;
- committed Replicas from partial publication, overwrite, corruption, and
  mutable aliases;
- Host files, backend namespaces, credentials, quarantine, and unrelated
  project material;
- complete transfer, failure, deletion, and provenance history;
- protected research material from premature or racing garbage collection; and
- the distinction between stored bytes, eligible Proposals, and accepted
  scientific state.

### Adversaries and failures

Sources, imported bytes, repository files, archive content, Worker output,
Provider output, paths, filenames, media types, checksums supplied by callers,
and destination acknowledgements are untrusted. Backend responses are claims
until verified. The model covers malicious non-privileged Worker behavior only
at A2, consistent with RFC-0011.

Required threat cases include:

- forged Sigils, size lies, truncation, reordering, duplicated or missing
  chunks, and corruption in transit or at rest;
- path traversal, absolute paths, symlink and hard-link substitution, special
  files, case or Unicode collisions, and time-of-check/time-of-use replacement;
- archive traversal, decompression bombs, excessive files, and unsafe entry
  types;
- staging publication, partial rename, stale generation, overwrite, eventual
  consistency, and false durability acknowledgement;
- ETag or transport-security claims incorrectly treated as content identity;
- transfer retry, idempotency-key conflict, stale Lease, split-brain Worker,
  late finalization, and duplicate completion;
- forged source, backend, Job, Attempt, assurance, provenance, deletion, or
  verification evidence;
- backend credential theft, cross-project or cross-tenant reads, content-name
  enumeration, and secrets copied into logs or provenance;
- disk, inode, memory, bandwidth, log, staging, or quarantine exhaustion;
- bit rot, missing Replica, wrong restore, and silent backend mutation;
- Journal truncation, forged Head, State cache, interrupted-tail marker or
  recovery evidence, illegal event transition, open-intent ambiguity, and
  storage activation with an unprotected legacy v1 alias;
- quota pressure used to trigger implicit eviction, record erasure, or
  unauthorized quarantine disposal;
- GC reference-count races, incomplete or unbounded transitive closure,
  unknown relationship Schema, stale root snapshots, changed ancestor edge,
  active-transfer deletion, last-Replica deletion, symlink or ancestor
  substitution, wildcard or prefix deletion, and partial delete;
- suspected digest collision or contradictory catalog records; and
- attempts to turn storage success directly into an Artifact, Run, Assessment,
  Decision, Patch promotion, or Seal.

### Trust limits

SHA-256 content identity relies on collision and second-preimage resistance.
It detects accidental or malicious byte changes when Benchwork recomputes the
digest; it does not authenticate the source, prove scientific correctness,
scan for malware, establish license rights, or provide confidentiality.

The built-in local backend, storage coordinator, Storage Journal verifier, Host
kernel, filesystem, and enforcement backend are part of the operational
trusted computing base for Phase 3 storage claims. This RFC does not protect
against their coordinated compromise, a Host administrator, a malicious
same-user process with direct access to their files, or physical storage
attack. A2 prevents the Worker from reaching those components but does not
protect against a compromised control plane.

Remote transport confidentiality, malicious remote operators, verified
deletion, geographic durability, erasure coding, and key-management guarantees
are not claimed in Phase 3. Encryption at rest or in transit does not replace
end-to-end Blob verification. A remote backend may still withhold data or lie
about deletion; stronger attestation requires a later RFC.

Content-addressed storage leaks equality to an observer of keys or access
patterns. Backend locators and access logs therefore require authorization and
must not be exposed to Workers or unauthorised clients.

## Invariants

- Athanor remains the only canonical transition authority.
- `artifact/1.0` retains its accepted logical meaning and local byte-verification
  semantics; new Alpha registrations reject the reserved managed namespace.
- Every historical v1 alias under `.benchwork/storage/` has a verified
  permanent protection before storage activation and is never a GC or
  disposition target.
- A Blob is immutable exact bytes identified by a byte-level Sigil; a Replica
  realizes exactly one Blob.
- Blob, Replica, Transfer, and backend existence has no scientific authority.
- Every committed transfer has end-to-end Sigil and size verification.
- Managed hashing and readback are bounded streaming operations over the
  complete logical byte sequence.
- Staging and quarantine are never readable as eligible Replicas.
- Staging is live incomplete work; quarantine is a separately reserved,
  terminal isolation record. Neither state is inferred from a path.
- Partial, mismatched, late, fenced, corrupt, or unverifiable bytes fail closed
  and remain recorded.
- A Worker never receives committed-store, quarantine, journal, catalog, or
  backend credential authority.
- No available Replica is overwritten in place.
- Retry and recovery are idempotent and preserve every transfer attempt.
- The hash-chained Storage Journal is authority; Head, State, directory names,
  and backend listings are verified projections or claims.
- A complete Journal frame is never truncated or skipped; only a proven
  EOF-interrupted final suffix is evidence-preserved and removed under the
  exact recovery rule.
- An interrupted first Event recovers through the explicit empty-prefix
  initialization branch; every later recovery-frame template has a
  marker-bound Event ID, Sigil, and seed before template bytes exist.
- A Transfer commit intent names exactly one provisional Replica with null
  verification. NEW makes it available; DEDUP or any post-intent failure
  abandons it only with exact provisional-target absence evidence while
  preserving the distinct selected Replica.
- Deduplication preserves all provenance and never merges logical lineage or
  policy.
- Transformations create explicit derived provenance and are identified by
  their output bytes.
- Storage operations never append Chronicle or automatically create canonical
  objects.
- Retention and GC remove only exact physical Replicas under a current
  authorized plan; they never erase canonical or operational history.
- Record identity and history outlive authorized byte disposal; quota pressure
  never grants deletion authority.
- Every project quota counter is a deterministic fold of the closed
  `QuotaEffect` program; reservations, retained future-event shares,
  settlement, pressure, and physical usage removal are never inferred.
- All twelve quota counters have class-and-dimension entity identities. Every
  one of the 61 Event types has exactly one owner or named system capacity
  source, and every installed system class satisfies its positive count and
  byte formulas.
- Transfer, Materialization, and Quarantine terminal Events classify every residual
  generation as absent, cleaned, or exactly held and charged; every held
  Transfer, Materialization, or Quarantine object has one legal disposition
  target kind.
- GC uses closed Schema-aware Reference Sets and a complete bounded transitive
  closure; unknown or exhausted traversal fails closed.
- Reference relationships obey the closed source/target matrix, and every GC
  component-set, root snapshot, closure proof, target array, and Event binding
  verifies its defined canonical preimage and equality.
- Every Phase 3 canonical Blob binding has a durable reference intent before
  Chronicle commit; every open or committed intent is a GC root.
- Every Phase 3 execution Blob binding has its Storage Reference Set and hold
  before its execution event becomes visible; removal commits the execution
  transition before releasing the hold, under the same outer gate.
- GC revalidates every target's current ancestors and exact namespace path or
  backend generation while holding the canonical-reference gate through its
  durable deletion outcome.
- Every side-effect intent is one exact `OpenIntentProjection`; GC and
  disposition Recovery use their complete exact-generation observation
  matrices and never infer success from a path or unbound absence.
- Normal GC never removes the last eligible Replica of canonically retained
  material.
- Storage treats Patch Bundles and every other structured payload as opaque
  bytes; higher layers supply typed Reference Sets.
- Blob `availability_as_of` is always an `EventRef`, and every durable
  deadline follows the conservative RFC-0012 restart rule: inability to prove
  that it remains future makes it due and never extends authority.
- `LOCAL-PHASE3/1.0` evidence cannot be used to claim
  `PORTABLE-PHASE4/1.0` conformance.
- Unknown algorithms, Schemas, backend profiles, controls, and evidence fail
  closed.

## Relationship to adjacent RFCs

- RFC-0011 owns authority, assurance, Sanctum, Circle, Ward, Crucible, and the
  operational-versus-canonical boundary.
- RFC-0012 owns Job, Attempt, Lease, the public fence tuple, secret Lease
  credential, cancellation, terminal eligibility, and crash-recovery
  identities consumed by storage transfers. Its execution events own root
  visibility; this RFC owns the preceding Reference Set/hold and shared-gate
  ordering that makes those roots safe for GC.
- RFC-0014 may encode a Patch Proposal and its validation evidence as Blobs,
  but storage treats its Patch Bundle as an opaque Blob. RFC-0014 owns its
  trusted extractor and supplies this RFC's typed Reference Set, while also
  owning base identity, conflict handling, human promotion, and repository
  mutation.
- RFC-0015 exposes typed Executor start, observe, cancel, and result operations.
  It may return bounded Blob descriptors and transfer status, but never raw
  backend credentials or general storage access. Its Agent Result acceptance
  registers an exact Reference Set and uses this RFC's canonical-reference
  gate.

Those RFCs may refine record fields but may not weaken this RFC's identity,
atomic publication, quarantine, compatibility, provenance, or authority
boundaries without explicitly superseding it.

## Alternatives

- **Make every stored Blob a canonical Artifact.** Rejected because caches,
  duplicate bytes, failed outputs, imports, and quarantined material do not
  have scientific meaning or accepted Program lineage.
- **Treat `artifact/1.0.location.uri` as a backend locator.** Rejected because
  current Athanor resolves and hashes a project-local file, and existing Deep
  Doctor and replay behavior must remain unchanged.
- **Store Replica lists in Chronicle.** Rejected because health checks,
  transfers, repair, replication, and deletion are operational churn rather
  than canonical research transitions.
- **Trust Worker-provided hashes or backend ETags.** Rejected because both are
  untrusted claims and may cover different bytes or encodings.
- **Write directly to the final content-addressed path.** Rejected because
  readers could observe partial bytes and crashes could make a key look
  committed.
- **Use mutable paths as content identity.** Rejected because paths and object
  keys can be reused, redirected, or changed independently of bytes.
- **Use reference counts alone for GC.** Rejected because crash recovery,
  concurrent roots, delayed canonical acceptance, and retention changes create
  deletion races.
- **Hard-link materializations to stored Blobs.** Rejected because a writable
  alias can corrupt the supposedly immutable backend object.
- **Automatically register successful Job outputs.** Rejected because
  execution and storage success cannot replace Athanor validation or
  researcher authority.

## Non-goals

- rewriting, automatically relocating, or replacing an accepted
  `artifact/1.0`; the reserved-namespace admission check is the explicit
  versioned Alpha safety tightening defined here;
- production-grade remote storage, replication, geo-durability, erasure
  coding, or disaster recovery;
- selecting a cloud provider or requiring Slurm, Kubernetes, or cluster
  storage;
- remote Worker transport or automatic Provider invocation;
- malware detection, content moderation, scientific validation, license
  adjudication, or source authenticity;
- general secret brokering, encryption-key management, or confidential
  computing;
- Patch application, merge, or promotion;
- automatic creation of Artifacts, Runs, Assessments, Decisions, or Seals;
- defining a canonical Dataset version contract; and
- allowing third-party executable Storage adapters in the `0.4` reference
  runtime.

## Acceptance tests

Acceptance requires executable closed Schemas, positive and adversarial
fixtures, threat-model review, crash tests, and retained conformance evidence.
The combined suite must demonstrate:

1. every already accepted `artifact/1.0` fixture and Chronicle replays
   unchanged, and ordinary new locations outside the reserved namespace retain
   their CLI, MCP, Working-transition, and Deep Doctor behavior;
2. `artifact/1.0.location` still contains exactly `uri` and `sigil`, resolves
   to a project-local readable file at registration, is never accepted as a
   Replica set or backend locator, and rejects lexical, resolved, symlink,
   case, and normalization aliases of `.benchwork/storage/`;
3. upgrade preflight detects every historical v1 reserved-namespace alias,
   verifies its Receipt and bytes by streaming, creates a managed copy and
   closed legacy-protection record through the migration-only
   `LEGACY_V1_PROTECTION` Transfer with a durable commit intent, without
   rewriting the event or path, holds the fixed outer gate across the final
   Chronicle replay and activation, and blocks on concurrent ungated writers,
   missing bytes, collision, ambiguity, or insufficient capacity;
4. exact byte identity distinguishes newline, serialization, compression, and
   other byte changes, while equal verified bytes deduplicate without merging
   Artifacts, Programs, policies, or provenance;
5. file names, paths, media types, timestamps, backend keys, encryption
   envelopes, and metadata do not affect Blob identity;
6. directory and bundle handling rejects traversal, absolute and duplicate
   paths, case or normalization collisions, special files, excessive counts,
   and aggregate-size violations;
7. import streams through bounded memory into isolated staging, enforces
    overflow-safe bounds, computes SHA-256 and size, records commit intent,
    creates the explicit null-verification provisional Replica, conditionally
    finalizes, independently streams readback, and only then exposes an
    `AVAILABLE` Replica; NEW selects that provisional ID, while DEDUP abandons
    it with exact target-generation absence evidence and selects a distinct
    already verified Replica without revising it, with Event backend object
    and verification byte-for-byte equal to that selected Replica and bound to
    its exact generation, Blob Sigil, and size;
8. capture without a prior Sigil is labelled `IDENTITY_COMPUTED` and cannot
   satisfy a pre-pinned input, while an expected mismatch is quarantined;
9. local import detects source replacement, symlink and hard-link ambiguity,
   special files, truncation, growth, and project-scope escape;
10. partial writes, disk exhaustion, crash before or after backend finalize,
    and lost commit acknowledgement recover deterministically from the complete
    commit intent and `OpenIntentProjection` without exposing staging,
    fabricating success, or losing the provisional Replica transition;
11. retry preserves each transfer-attempt record, exact idempotent replay
    returns the prior result, and conflicting idempotency-key reuse fails;
12. chunk corruption, loss, overlap, reordering, inconsistent resume state,
    and total-size mismatch prevent commit even when transport security or
    per-chunk checks pass;
13. export selects by verified Blob identity, uses no-clobber staging and
    atomic finalize, verifies the destination logical bytes, records a closed
    manifest, and rejects an unrelated existing destination;
14. TLS, process exit, file existence, backend metadata, and ordinary
    object-store ETags cannot substitute for end-to-end verification;
15. materialization is exact and atomic, declared immutable inputs are
    read-only, destination mutation cannot alter a stored Replica, and
    hard-link aliasing is rejected; crashes before intent, after intent,
    after conditional finalize, after readback, and after the terminal frame
    follow the exhaustive materialization-recovery matrix without exposing an
    unjournaled destination, and both-present recovery records `CLEANED` or
    exact charged `HELD_FOR_DISPOSITION` before the terminal frame; the commit
    Event's intent ID, destination object and identity, fence, expected Blob
    and size, and verification satisfy every terminal-record equality above;
16. Worker output is bounded and Attempt-scoped; stale Lease, invalid fence,
    cancellation, duplicate completion, policy violation, and late output
    prevent finalization and result eligibility;
17. an A2 Worker cannot reach the committed namespace, quarantine, Storage
    Journal, catalog, backend credentials, `.benchwork/`, or another Attempt's
    staging;
18. backend profile mismatch, unsupported conditional operation, unknown
    capability, false atomicity, stale generation, and inconsistent readback
    fail closed;
19. the backend never overwrites an available Replica, and suspected
    same-Sigil size or byte contradiction places the identity into incident
    state;
20. corruption of one Replica removes it from selection, verifies another
    Replica before failover, and reports the Blob unavailable when no eligible
    Replica remains;
21. deduplicated import, copy, transformation, export, verification, deletion,
    and restore each retain distinct provenance and never manufacture canonical
    producer or input lineage;
22. provenance rejects credentials and secrets while retaining source class,
    authorization, Job, Attempt, Lease, fence, backend, transfer, verification,
    and transformation identities;
23. Blob commit, Replica repair, export, quarantine, and GC leave Chronicle,
    Runs, Artifacts, Assessments, Decisions, and Seals unchanged until an
    explicit Athanor transition succeeds;
24. GC computes a deterministic dry-run from Sigil-bound canonical and
    operational roots and typed Reference Sets, observes a grace period,
    acquires the canonical-reference gate, replays Chronicle and Execution
    journals one at a time, verifies every execution Reference Set and hold,
    and then acquires the exclusive Storage Journal lock for final
    revalidation through deletion outcome; it revalidates every target,
    ancestor edge, namespace ancestor, and generation, and cannot delete
    active, held, newly referenced, legacy-protected, quarantined, or
    minimum-Replica material; component-set preimages, root snapshot,
    closure-proof self-Sigil, plan Ref, and exact ordered target IDs pass every
    equality above and each single-field mismatch is rejected;
25. stale-root, concurrent-import, retention-change, backend-generation,
    partial-delete, and restart races preserve evidence and never broaden a GC
    plan;
26. deletion targets one exact Replica, leaves Blob identity, provenance,
    transfer history, GC decision, and tombstone intact, and wildcard or prefix
    deletion is unavailable;
27. the Phase 3 runtime has no normal path to delete the last eligible managed
    Replica of canonically retained material and performs no automatic GC;
28. staging and quarantine have distinct identities and state machines;
    quarantine is isolated and quota-bounded, cannot serve as a Replica or
    deduplication source, and requires a new verified import for release or an
    exact audited disposition; Quarantine terminal Events carry the closed
    source-cleanup object, a retained source stays owner-charged, the expected
    Blob and size are jointly null or non-null, and successful isolation
    verifies the exact intent-bound destination generation, Blob Sigil, and
    size;
29. restart recovery reconstructs storage state from the durable Storage
    Journal's complete binary frames and verified backend generations rather
    than paths, filenames, conversation, or Worker claims, derives exactly the
    six open-intent branches and their create/remove mappings, and exercises
    every row of the Transfer, Materialization, Quarantine, GC-delete, and
    disposition recovery matrices, including the no-open-intent pre-start
    Disposition expiry branch;
30. unknown storage Schemas, journal events, state transitions, Sigil
    algorithms, provenance versions, reference relationships, retention
    policies, backend profiles, or required evidence are rejected; and
31. the `0.4` local vertical slice retains all terminal Attempt output and
    quarantine records by default, identifies its exact Host and backend
    configuration, and makes no production Registry or remote durability
    claim;
32. all Journal Event, Head, and State Schemas reject extra or malformed
    fields; Event envelope, Reference Set, Reference Intent, cleanup, deadline,
    and open-intent fields have the exact types, null matrices, and equality
    constraints assigned by this RFC; every Event branch has exactly its
    payload and entity revisions; legal Events replay to the identical State
    Sigil, while a broken chain, revision gap, unknown Event, or illegal
    transition enters read-only `INTEGRITY_FAILURE`;
33. crashes at every payload, intent, event, fsync, Head replacement, backend
    commit, delete, disposition, and recovery boundary preserve a valid prefix
    and resolve without path inference, hidden success, or truncation of a
    complete frame; only a proven EOF-interrupted final suffix with a valid old
    Head is evidence-preserved and removed, and crashes before or after each
    recovery-marker phase—including an interrupted first
    `storage.initialized`, `RECOVERY_EVENT_ID_DURABLE`, and every partial retry
    of the prepared recovery-entry frame—resume the same durably allocated
    Event ID, Sigil, seed, template, and decision;
34. storage treats a Patch Bundle and other structured Blobs as opaque bytes,
    and only an explicit higher-layer Reference Set can retain their typed
    children;
35. reference closure follows multiple levels, handles cycles
    deterministically, and aborts without deletion on an unknown extractor,
    missing or mismatched Reference Set, node, edge, depth, byte, or time
    bound, integer overflow, or changing source;
36. a new reference on any ancestor, a changed target relationship, a symlink,
    mount, rename, inode or generation substitution, hard-link ambiguity, or
    failed no-follow check skips the exact GC target after authorization while
    leaving other targets independently revalidated;
37. normal and deep Storage Doctor produce closed Sigil-bound reports; deep
    mode streams all required Replica, legacy-anchor, protected-copy, and
    permitted quarantine bytes, and neither mode repairs, deletes, releases,
    truncates, or hides an incomplete check;
38. byte, object, inode, stream, staging, quarantine, committed, and Journal
    counters initialize all twelve legal class/dimension pairs; every mapped
    `RESERVE`, partial retained `SETTLE`, terminal `SETTLE`, `PRESSURE`, and
    `USAGE_REMOVED` effect replays to identical counters before a Job or write
    handle is issued, the twelve initialization revisions use twelve distinct
    `quota-counter:<class>:<dimension>` identities, and an admitted operation
    cannot exceed, reclassify, or borrow beyond its claims; the 61-row
    capacity-source table is mechanically equal to both Event sets, every
    owner plan covers its maximum Event/control/recovery counts, and every
    system class satisfies the strict positive capacity formulas;
39. quota exhaustion never silently deletes payloads or history:
    failed staging remains exactly `HELD_FOR_DISPOSITION` with its reservation
    charged until an authorized transition, while Blob identity, Transfer,
    provenance, failure, disposition, GC, and tombstone records survive
    authorized byte removal; materialization cleanup and canonical-pin
    reservations retain exactly their future-event claims, Materialization and
    Quarantine residuals remain charged to their exact classes and owners, and
    expiry is resolved only by the owning terminal Event;
40. disposition requires an unexpired exact authorization and conditional
    generation match, exercises all four target-kind owner projections and the
    complete present/absent/mismatch/expired/ambiguous Recovery matrix, cannot
    use prefixes or wildcards, and cannot target an available Replica,
    canonical file, legacy anchor or copy, Journal, or recovery material; an
    authorization that expires in `AUTHORIZED` takes the null-intent
    `AUTHORIZED -> FAILED` branch with no open intent, backend side effect, or
    target-owner revision, while every post-start failure repeats the non-null
    execution-intent ID;
41. `LOCAL-PHASE3/1.0` passes its exact Host crash, fsync, path, quota,
    reconciliation, Doctor, GC dry-run, and manually authorized GC execution
    suite but cannot advertise `PORTABLE-PHASE4/1.0`, remote durability,
    automated GC, or replication evidence;
42. backend URIs, keys, and digest-shaped paths remain opaque operational
    locators and cannot be disguised as new v1 Artifact locations; an explicit
    verified materialization outside `.benchwork/storage/` can use the
    unchanged v1 path; and
43. provisional-target rollback, GC, and disposition can remove only their
    exact authorized physical bytes, never operational identity or history,
    and availability projections clearly distinguish retained records from
    available bytes;
44. `ST-` request and `SA-` attempt identities are never interchanged; retry
    keeps the immutable request, creates a new attempt, and preserves every
    prior attempt;
45. every owned contract and nested `$defs` object has positive, negative,
    additional-property, discriminator, bound, sorting, and canonical-Sigil
    fixtures generated from the exact field sets in this RFC, including every
    closed verification-method and provenance-relation value,
    Replica-verification, cleanup, Recovery-Marker, deadline, and open-intent
    state/null branch;
46. Reference Set registration verifies the exact source and extractor,
    exercises every legal relationship/source/target row, rejects every
    unlisted combination, identity/Sigil mismatch, unknown relationship or
    target kind, and retains Patch Bundle members only through explicit typed
    edges; its semantic content deterministically selects one RS-ID and the
    generic RS-derived SE-ID, while an execution ESM uses only its
    ESM-ID-derived special SE-ID and one fixed candidate; first creation
    freezes `created_at` and complete bytes, and crashes before or after
    candidate durability, Event append, Head installation, readback, or
    higher-layer request finalization reuse that exact set/Event rather than
    allocating a new time or identity; RFC-0014 Evidence Manifest fixtures
    exercise all 19 owner/role/Event projections and the suffix branch, exact
    fixed extractor/validator Sigils, typed Blob/control edges and validation
    evidence, and reject a bare/multiply typed Sigil, missing/extra member,
    null-branch manifest, changed activation tuple, future Sigil, or second
    activation; exact 4,096 member/edge/validation-evidence boundaries pass,
    while a 4,097th aggregate member, edge, validation Sigil, same control
    identity with another Sigil, or same Blob Sigil with another size fails
    before registration;
47. crashes before intent, after `canonical_reference.intent_recorded`, after
    the Chronicle Event, after its Receipt, and before
    `canonical_reference.committed` deterministically recover without a false
    release or lost pin; the intent accepts `0..4096` exact closure-derived
    Blob Sigils, including the legal empty closure, rejects every partial or
    mismatched set, and its lifecycle Reservation is non-expiring while
    `OPEN` and settles on either terminal path; committed fixtures verify the
    exact Event sequence/type/body, Receipt ID/Sigil, prior Receipt, request,
    set projection, and resulting Head; abort fixtures require an advanced
    verified Head and complete bound-Event absence proof; deterministic RI-ID
    and global
    `(canonical_event_type, transition_request_id)` uniqueness make an exact
    retry reuse one immutable record and one creation Event, while different
    bytes, duplicate IDs, or duplicate creation Events fail closed;
48. GC and a concurrent Athanor transition are linearized by the
    canonical-reference gate under every lock-order and crash schedule, with an
    ambiguous `OPEN` intent always protecting its Blob set; execution input
    and output visibility uses the same gate with Storage hold first and
    execution event second, while removal reverses that order; every execution
    root resolves the exact ESM-sourced Reference Set and complete typed Blob
    edge closure, and its `ACTIVE` hold targets that same Reference Set and is
    created by the exact bound and authorized `retention.hold_set` Event—an
    unrelated active Blob, Replica, Reference-Set hold, or changed
    authorization is rejected; activation rejects a pre-existing EHR; every
    RFC-0014 hold-set admission resolves the already-durable single-assignment
    RootPlan and never a future Event/root, exact activation reproduces its
    Event/type/field/root identity, a second field in one Event slot or a
    changed/reused plan/Set/hold/policy is rejected, and crashes after slot
    reservation, plan, or hold distinguish no-hold, plan-only, and unreleased
    conservative previsibility orphans; all three execution EHR bases and all
    four RFC-0014
    release conditions resolve the exact RootPlan and replayable release
    record, exercise canonical, terminal/no-guard/suffix, trusted-clock/
    retention, exact prefix/Event order, intent-absence, and embedded
    patch-abandonment branches, reject an earlier inactivation time, missing
    canonical commit, unrelated guard, reversed abandonment guard order,
    generic disposition, or bare evidence index, and retain on ambiguous proof;
    and
49. a committed canonical pin has no v1 outbound transition, while a
    provably uncommitted request uses only
    `ABORTED_BEFORE_CANONICAL_COMMIT` with
    `HEAD_SUPERSEDED_WITHOUT_BOUND_EVENT`; an unchanged Head, existing bound
    Event, wrong Receipt/Head, or any `CANONICAL_REFERENCE_REMOVED` branch is
    rejected; and
50. UTC forward steps, rollback, slew, monotonic-domain loss, and restart
    expire on the earlier trusted UTC or live process-local monotonic
    condition, treat every deadline whose future cannot be proved as due,
    never compare monotonic ticks across restart or extend authority, and close
    the clock gate before any time-authorized finalization, release,
    disposition, or GC when trust is uncertain;
51. a canonical-reference operation accepts a `chronicle-head/1.1`
    `event_count` only below `U63_MAX`, permits the next Event while its
    resulting count remains representable, and at or above that boundary
    fails before Reference Set registration, intent, reservation, or Chronicle
    side effects without wrapping, clamping, or losing existing state;
52. every `ExecutionStorageRoot` has exactly the nine printed fields, sorts
    with its ESM identity, and resolves the same RFC-0012 ESM ID/Sigil, owner,
    `PLANNED` protection plan, ESM-ID-derived registration ID, preallocated
    hold Event ID, exact neutral policy tuple, Reference Set, active hold,
    domain-separated hold-set authorization, fixed extractor/validator,
    deterministic validation evidence, and complete typed Blob edge closure;
    a missing manifest pair, second byte sequence or Set for one ESM-ID, generic
    SE-ID substitution, owner mismatch, swapped planned Event, future-Sigil
    evidence, valid but unrelated set or hold, or incomplete edge projection
    is rejected;
53. `ATTEMPT_OUTPUT` fixtures exercise the exact `INGEST` request matrix,
    accepted Result staging-reference branch, opaque handle and exact derived
    subject mapping, current `LEASED` execution and public fence, exact
    Blob/byte bound, backend, current `TransferRef`, and current `CAPTURED`
    provenance for `NEW_REPLICA`, `DEDUPLICATED_REPLICA`, Quarantine, and
    terminal-negative outcomes; every cross-field mismatch fails, and the
    DEDUP fixture proves that a historical selected Replica's creator Attempt,
    record Sigils, terminal Event, or provenance cannot replace the current
    Result-bound `ST-ID`/`SA-ID` chain; and
54. execution-owned output-hold tests derive the checked `release_due_at`
    from the exact parent Job terminal Event for zero and positive durations,
    produce only the exact RFC-0012 schedule, map overflow to the terminal
    time with `OVERFLOW_FAIL_CLOSED`, fail the `CODE_MODIFICATION` success
    guard, and release that inactivated execution hold immediately; a
    clock-uncertain schedule remains protected without recomputing its
    deadline, canonical replacement and every earlier narrowing are rejected,
    and at an exact or overflow-mapped expiry Storage resolves the one
    `OUTPUT_DEADLINE` EHR and appends one
    `EXECUTION_HOLD_LIFETIME_EXPIRED` release for the exact `SH-ID` with the
    EHR-bound authorization, exact evidence, and one `HOLD` revision; retry
    reuses its EHR and exact Storage `EventRef` in
    `storage_root.hold_release_observed`; input owner-terminal and orphan-abort
    fixtures exercise their distinct reason/evidence/activation rules, with no
    execution observation fabricated for the never-activated orphan; policy
    `retain_until`, canonical and legal/preservation roots, Quarantine,
    different holds, Blob/Replica records, and surviving GC protection remain
    unchanged, and the release alone never authorizes byte deletion.

The acceptance report must map every test to the exact backend profile,
conformance-suite Sigil, Host platform, source revision, and retained evidence.
