# Benchwork Host Adapter: Claude Code

The Claude Code adapter has the same contract and policy behavior as Codex. It
can prepare a bounded Task Capsule, display an approval requirement, and hand
the request to a future executor. It cannot mutate canonical research state.

```bash
bwork host propose claude-code bench.evidence.discover \
  --input-sigil sha256:<digest> --tool read --tool web --time-budget 300 --network
```

A Claude Code integration must preserve the Capsule's Circle rather than
expanding its tools or authority.

Claude Code CLI holds a Tier 1 PASS from its 2026-07-31 trial, recorded in
[`examples/phase2-final/host-claude-code`](../../examples/phase2-final/host-claude-code/README.md).
A Host that opens its own Task Capsule declares itself with `host_session` so
Chronicle records the acting Host; Athanor refuses an Agent Result whose
provenance Host does not match its Capsule.
