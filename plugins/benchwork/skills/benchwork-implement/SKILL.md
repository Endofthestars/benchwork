---
name: benchwork-implement
description: Inspect and modify repository code for a registered Benchwork study. Use when implementing a Protocol, changing model or analysis code, reviewing research code, fixing a study implementation, or registering an implementation artifact.
---

# Benchwork Implement

Read [references/implementation-checklist.md](references/implementation-checklist.md)
and [references/review-policy.md](references/review-policy.md) before editing.

1. Read the sealed Protocol and relevant Working.
2. Open `bench.code.inspect` for diagnosis or `bench.code.modify` for changes. Do not pass an approval reason unless the user explicitly approved the mutation boundary.
3. Use native repository search and file reading to locate the smallest safe change.
4. Modify source with native edit or patch tools. Never write `.benchwork/` directly.
5. Run the smallest relevant tests with native shell.
6. Use a local `/review` or equivalent read-only review before completing a core change.
   For any external reviewer, prepare the Review Request and stop for explicit
   disclosure authorization before opening `bench.review.external`.
7. Complete the Task with changed files, patch summary, test commands and results, and residual risks.
8. Create a project-relative implementation manifest or artifact, calculate its Sigil, and call `benchwork_register_artifact`.

Keep canonical scientific state in MCP tools. Code edits and test output remain native Codex work until explicitly registered.
