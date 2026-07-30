# Benchwork for Codex

This plugin makes Codex the interactive conductor for auditable computational
research. Skills define workflows, the bundled STDIO MCP server changes
canonical state through Athanor, and trusted hooks guard against accidental
native writes to `.benchwork/`.

Install the `benchwork-arcana` Python package so `bwork` is on `PATH`, add this
repository marketplace to Codex, enable the plugin, review its hooks with
`/hooks`, and start a new conversation.

Use native Codex tools for repository inspection, patches, shell, Git, web
search, and review. Use `mcp__benchwork__*` tools for canonical research state.
Review locally by default. An external diff review requires a prepared Review
Request, explicit disclosure approval, a Ward-approved external Review Task,
and recorded Review provenance. General CLI or IDE authorization is not
disclosure authorization.

The plugin and its hooks are not the security boundary. Ward and Athanor still
validate every accepted transition.

Host acceptance is tiered. A missing graphical extension Host can be recorded
as `BLOCKED_BY_ENVIRONMENT` without blocking Kernel, MCP, or CLI acceptance.
See the repository
[Acceptance Exception Policy](../../docs/en/plugins/acceptance-exception-policy.md).

`benchwork-plugin-api.json` and each Skill's `skill.yaml` are versioned
Benchwork compatibility metadata. They do not replace Codex's
`.codex-plugin/plugin.json`, `SKILL.md`, or `agents/openai.yaml` discovery
contracts.
