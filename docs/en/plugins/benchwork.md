# Benchwork Codex plugin

Benchwork 0.3.0a1 is designed for an interactive Codex session. Install the
Python package first, then install the repository marketplace and enable the
`benchwork` plugin.

```bash
python3 -m pip install -e .
codex plugin marketplace add .
codex plugin add benchwork@benchwork-local
```

Start a new Codex conversation after installation. Review and trust the bundled
hooks with `/hooks`; plugin hooks are skipped until trusted.

For direct development without the plugin, copy the relevant entries from
`.codex/config.toml.example` into trusted project configuration. The Codex CLI,
IDE extension, and desktop app share the same local MCP configuration.

## Workflow

Use `$benchwork-orchestrate` for broad work. It reads canonical status and
routes to investigation, design, implementation, pilot, evaluation, or resume.
Specialized skills can also be selected explicitly.

Codex uses native tools for source files, patches, shell, Git, web search, and
review. The `mcp__benchwork__*` tools read or change research state. Never edit
`.benchwork/` directly.

Scientific Seals use two calls: preview, then commit. Show the user the preview
and request confirmation. Commit only with the fresh preview Sigil, a new
idempotency key, and the exact token returned by the preview after the user
confirms.

## Trust and portability

`SessionStart` adds a bounded read-only project summary. `PreToolUse` blocks
obvious native state writes. `PostToolUse` reminds Codex about tests, Run
registration, artifacts, and failures. These hooks do not mutate canonical
state and cannot weaken Athanor if disabled.

The Skills and hooks are Codex-specific packaging. MCP tool semantics,
Capability contracts, Task outputs, and canonical state remain host-neutral.
