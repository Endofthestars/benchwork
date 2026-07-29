---
language: en
canonical: true
---

# M10 Acceptance Matrix

M10 closes Phase 1 only when the checks below pass on the complete stacked
branch. Automatic Provider or Executor implementation remains prohibited.

| Area | Acceptance evidence |
|---|---|
| Receipt identity and chain | `test_chronicle_v11.py`, `test_chronicle_v11_contract.py` |
| Recovery and migration | Chronicle recovery, migration, and injected commit-failure tests |
| Snapshot and Capability binding | `test_agent_results.py`, `test_snapshot_task_v11_contract.py` |
| Scientific Gates and Actor records | `test_scientific_canon.py` |
| Working, Experiment, and Run lifecycle | `test_lifecycle_v11.py` |
| Registered descriptive analysis | `test_alembic.py` |
| Project root, active Program, JSON errors | `test_cli_surface.py` |
| Full research-chain replay | `test_m10_repair_study.py` and `examples/m10-repair-study/` |
| Published schema structure | `scripts/ci/check-schemas.py` |
| Documentation links | `scripts/ci/check-doc-links.py` |
| Stable-release block | `scripts/ci/check-release-policy.py` |
| Lint and types | Ruff and mypy CI steps |
| Core coverage | Coverage branch report, minimum 80%, excluding the CLI adapter |
| Installability | Wheel build, metadata check, fresh install smoke test |

## Expected golden state

The repair-study fixture must finish with:

```yaml
program_status: EVALUATED
working_status: COMPLETED
decision: REPAIR
chronicle_verified: true
all_objects_replayable: true
```

It must also retain one failed Run, one completed excluded Run with a reason,
an open CRITICAL Issue, and the rejected `CONTINUE` attempt without an appended
event.

## Release gate

The first non-development release remains blocked while the distribution, CLI,
import, or schema URL name is provisional. Passing M10 permits Phase 2 design
and implementation work; it does not imply stable package publication.
