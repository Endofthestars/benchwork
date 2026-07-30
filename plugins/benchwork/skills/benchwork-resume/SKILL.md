---
name: benchwork-resume
description: Recover and continue a Benchwork study from canonical state after interruption or in a new session. Use when asked to resume, continue an earlier study, recover uncertain integrity, reconstruct progress, or decide what remains without relying on old chat history.
---

# Benchwork Resume

Read [references/recovery-checklist.md](references/recovery-checklist.md) before continuing.

1. Run `benchwork_doctor` with `deep=true` when the session is new or integrity is uncertain.
2. Stop on any failed integrity check; do not initialize, migrate, repair, or infer around the failure.
3. Call `benchwork_status`, `benchwork_get_program`, and `benchwork_next_actions`.
4. Read the active Working, unresolved Issues, latest Assessments and Decisions, and relevant trace events.
5. Reconstruct the next bounded action exclusively from canonical state.
6. Select the specialized Benchwork skill for that action.

Do not infer project state from old conversation content. Treat chat only as a source of user intent that must be reconciled with Chronicle.
