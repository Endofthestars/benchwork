---
language: en
canonical: true
---

# First Rite: Computational Study

`computational-study@0.2.1` is the M10 canonical-event-driven Benchwork Rite. It
creates a Working only when its referenced Protocol is `FROZEN` and belongs to
the stated Research Program.

```text
IMPLEMENTATION -> PILOT -> ANALYSIS -> REVIEW -> DECISION -> COMPLETED
```

Each non-terminal stage declares an exit contract over a canonical Chronicle
event. Athanor advances the Working during replay and records the satisfying
Event and Object IDs. Manual `working.advanced` transitions are not accepted.
The pinned `computational-study@0.1.0` and `@0.2.0` definitions remain
readable for legacy ledgers.

See [RFC-0004](../rfcs/RFC-0004-rite-working-transition-model.md) for the
complete transition contract.
