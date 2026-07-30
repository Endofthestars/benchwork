---
name: benchwork-design
description: Turn Benchwork Evidence, Claims, and Hypotheses into a falsifiable study design and Protocol draft. Use for research-question framing, estimands, competing explanations, validity threats, analysis plans, Protocol review, or requests to preregister a study.
---

# Benchwork Design

Read [references/design-checklist.md](references/design-checklist.md) before drafting.

1. Read the active Program plus current Evidence, Claims, Hypotheses, and open Issues.
2. Open a `bench.study.design` Task.
3. When an independent lane is available, ask a read-only reviewer to challenge rival explanations and validity threats. Keep disagreements as Issues.
4. Specify the estimand, intervention or comparison, measurements, competing explanations, falsifier, exclusions, and validity threats.
5. Complete the Task with the expected structured proposal.
6. Draft the Protocol through `benchwork_draft_protocol`.
7. Call `benchwork_preview_protocol_seal` and present its changed fields, content Sigil, and Gate result.
8. Stop and request explicit user confirmation. Call `benchwork_commit_protocol_seal` only after the user provides that confirmation in the current interaction.

Never infer confirmation from prior chat, silence, or approval of a different action.
