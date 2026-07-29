# Benchwork Host Adapter: Claude Code

The Claude Code adapter has the same contract and policy behavior as Codex. It
can prepare a bounded Task Capsule, display an approval requirement, and hand
the request to a future executor. It cannot mutate canonical research state.

```bash
bwork host propose claude-code bench.evidence.discover \
  --input-sigil sha256:<digest> --tool read --tool web --time-budget 300 --network
```

The future Claude Code integration must preserve the Capsule's Circle rather
than expanding its tools or authority.
