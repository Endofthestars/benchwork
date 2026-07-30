# Dogfood Round 2 repair evidence

This directory records the local Round 2 repair of the failed Phase 2
dogfood trial. It contains exported, non-canonical evidence only. Canonical
Benchwork state was changed through the typed MCP boundary and no
`.benchwork/` state file is included here.

## Root cause

Round 1 attempted to complete `EX-001` with a run plan and metric that did not
match frozen Protocol `PT-001`. The Protocol required `RUN-000` and metric
`score`, while the trial recorded `RUN-001` through `RUN-005` using
`replay_success`. Athanor rejected pilot completion with
`VALIDATION_REJECTED`, and the failed trial was preserved.

## Repair

The repair preserved all Round 1 records. In particular, frozen `PT-001`,
active `WK-001`, `EX-001`, and their Chronicle histories remain unchanged.
The shared `RP-001`, `CL-002`, and `HY-002` aggregate objects advanced through
the registered evaluation while the repair added a new path:

```text
PT-002 -> WK-002 -> AR-002 -> EX-002
       -> RUN-101..RUN-105 -> RB-001 -> AS-001 -> DE-001
```

- `PT-002` freezes the included Pilot set as `RUN-101` through `RUN-104`.
- `RUN-105` remains a failed, excluded negative result with an explicit reason.
- `RB-001` analyzes only the four completed, included runs.
- `AS-001` records the synthetic-host limitations.
- `DE-001` seals the user-confirmed `REPAIR` outcome.
- `WK-002` finishes as `COMPLETED`; the original `WK-001` and `EX-001`
  remain in their failed-trial states.

The paired `replay_success` comparison produced a treatment mean of `1`, a
control mean of `0`, and a mean difference of `1` with a 95% Student-t
interval of `[1, 1]`. The standardized effect is unavailable because paired
differences have zero variance.

## Integrity checks

The final Deep Doctor report passes with 53 verified Chronicle events and 37
replayable objects. A fresh process restart exported the same status bytes
before and after restart:

```text
2d586f3dbb364808da96c1b212bb3371735a022cbdb0c9a226434f6c08aa64a2
```

Run the local evidence checks from the repository root:

```bash
sha256sum --check examples/phase2-final/dogfood-round2/SHA256SUMS
cmp \
  examples/phase2-final/dogfood-round2/round2-before-restart.json \
  examples/phase2-final/dogfood-round2/round2-after-restart.json
jq -e \
  '.ok and .chronicle_verified and .all_objects_replayable' \
  examples/phase2-final/dogfood-round2/restart-doctor.json
```

The Round 1 Protocol and Experiment traces are included so preservation can be
audited independently of the final aggregate snapshots. Full interactive
command logs are intentionally omitted because they are noisy and are not
required to verify the registered result.
