---
name: benchwork-pilot
description: Execute and register bounded pilot experiments under a sealed Benchwork Protocol. Use when running pilots, smoke experiments, registered arms or seeds, recording failed or negative Runs, or deciding whether an Experiment can leave the pilot stage.
---

# Benchwork Pilot

Read [references/pilot-checklist.md](references/pilot-checklist.md) before execution.

1. Read the sealed Protocol, Experiment, registered arms, and expected pilot Run IDs.
2. Open a `bench.experiment.execute` Task. Obtain explicit user approval for its execution boundary.
3. Use native shell for only the approved bounded commands.
4. Register every attempted Run with `benchwork_record_run`, including failed, cancelled, excluded, and negative outcomes.
5. Preserve command, seed, arm, metrics, artifacts, exclusion reason, and policy reference.
6. Complete or fail the Task based on the execution outcome.
7. Call `benchwork_transition_experiment` only after every Protocol-required pilot Run and arm is registered.

Never treat one successful Run as pilot completion and never discard a failed Run to make the pilot appear clean.
