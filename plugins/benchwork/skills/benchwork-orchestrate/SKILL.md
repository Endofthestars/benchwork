---
name: benchwork-orchestrate
description: Coordinate broad Benchwork research requests spanning multiple stages. Use when a researcher asks to start a research project, continue a study, asks “what should we do next?”, or gives a goal that must be routed across investigation, design, implementation, pilot, evaluation, or recovery.
---

# Benchwork Orchestrate

Read [references/checklist.md](references/checklist.md) before acting.

1. Call `benchwork_status`, then `benchwork_next_actions`.
2. State the active Research Program explicitly. If none is active, ask the user to select one or create one through `benchwork_create_program`.
3. Build a short adaptive plan from canonical state and unresolved Issues.
4. Switch to the specialized Benchwork skill once one stage dominates:
   - evidence work: `$benchwork-investigate`
   - study design: `$benchwork-design`
   - code changes: `$benchwork-implement`
   - bounded execution: `$benchwork-pilot`
   - analysis and decision: `$benchwork-evaluate`
   - uncertain or interrupted state: `$benchwork-resume`
5. Preserve unresolved Issues across handoffs and report the latest Receipt for accepted changes.

Use native Codex tools for files, patches, shell, Git, web research, and review. Use Benchwork MCP tools for canonical state. Never edit `.benchwork/` directly.

Pause for explicit user confirmation before any RQ, Protocol, or Decision commit and before expensive execution. Do not perform deep stage-specific analysis here when a specialized skill applies.
