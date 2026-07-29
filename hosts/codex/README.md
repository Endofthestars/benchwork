# Benchwork Host Adapter: Codex

The Codex adapter uses the same `HostAdapter` contract as Claude Code. It may
create a Task Capsule and present Ward's decision, but it must not write
Chronicle events other than an explicit human approval action.

```bash
bwork host propose codex bench.code.inspect \
  --input-sigil sha256:<digest> --tool read --time-budget 300
```

When Ward returns `PASS`, Codex receives a bounded work request. Integrating a
real Codex execution surface belongs to a later executor milestone.
