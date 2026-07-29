---
language: en
canonical: true
---

# Integrity Repair

This milestone closes the first adversarial review of the Athanor foundation.

- Every canonical transition now reads, validates, allocates, and appends under
  one cross-platform lock.
- `chronicle.head` anchors the event count and terminal Sigil, making tail
  truncation and incomplete commits fail closed.
- Approval events bind the complete Task Capsule Sigil, Capability, input, and
  Circle. Mutable or repurposed Capsules are rejected.
- Working creation embeds a pinned Rite definition and Sigil. Each stage exit
  requires the artifact kind declared by that pinned definition.
- Runtime Program, Protocol, Working, Chronicle Event, and Task Capsule objects
  are checked against the published Draft 2020-12 Schemas.

The head and hashes protect integrity against accidents and detectable drift.
They are not signatures and do not defend against a malicious writer who can
rewrite the ledger, head, and all receipts together.
