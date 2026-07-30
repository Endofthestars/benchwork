---
name: benchwork-evaluate
description: Compute, interpret, assess, and decide from registered Benchwork experimental results. Use for Alembic analysis, Result Bundle interpretation, statistical review, Assessment recording, repair decisions, or requests to conclude what an experiment means.
---

# Benchwork Evaluate

Read [references/evaluation-checklist.md](references/evaluation-checklist.md) before interpreting results.

1. Read the sealed Protocol, all registered Runs, unresolved Issues, and existing Result Bundles.
2. Call `benchwork_compute_analysis`. Never replace Alembic output with hand-calculated statistics.
3. Interpret the Result Bundle against the registered estimand, comparisons, uncertainty policy, and falsifier.
4. When useful, ask a read-only independent reviewer to challenge statistical interpretation. Keep review local unless the exact external disclosure is explicitly approved. Preserve conflicts as Issues.
5. Record the Assessment with `benchwork_record_assessment`; open Issues for unresolved threats or contradictions.
6. Call `benchwork_preview_decision_seal` and show the exact outcome, rationale, required actions, content Sigil, and Gate result.
7. Stop for explicit user confirmation. Commit the Decision only with the fresh preview and exact confirmation token.

Separate numerical facts in the Result Bundle from interpretive judgment in the Assessment.
