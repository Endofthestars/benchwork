# Claude Code CLI Tier 1 Host trial

This directory records the 2026-07-31 Tier 1 Host validation for Claude Code
CLI, which closed the `PENDING_HOST_VALIDATION` state left open by the Phase 2
acceptance. It contains exported, non-canonical evidence only. No `.benchwork/`
state file and no conversation reasoning is included here.

## Method

Each trial was a fresh, ephemeral Claude Code CLI `2.1.220` conversation
started with `--strict-mcp-config`, so the Benchwork MCP server was the only
one loaded. Every trial ran against a temporary project outside this
repository; the source repository never acquired a `.benchwork/` directory.

Transcripts were captured as `stream-json` and distilled into
[`trial-log.json`](trial-log.json). The Host session identifier was pinned with
`--session-id`, so the `invocation_id` recorded in Chronicle can be checked
against the transcript that produced it.

## What the trial found

Read-only discovery passed immediately. The MCP server reported `connected`
and the Host discovered all 38 registry tools. `benchwork_status` and
`benchwork_next_actions` each returned `ok: true` with an
`mcp-tool-result/1.0` envelope, both when the tools were named explicitly and
when the Host was given only the broad request "What should we do next for this
study?" with 26 non-MCP tools still available.

The bounded Task loop did not pass. `benchwork_open_task` minted every Task
Capsule with a hardcoded `codex` Host and exposed no parameter for the acting
Host, so a truthful `claude-code` provenance was refused:

```text
VALIDATION_REJECTED: Agent Result provenance Host does not match its Task Capsule
```

Athanor was right to refuse. The defect was that the MCP boundary gave a
non-Codex Host no way to describe itself, in a module whose own docstring
claims to be host-neutral. The Host reported the rejection rather than
resubmitting a false `codex` provenance to force a green run.

This is what the evidence policy means when it says contract inspection is
insufficient. `hosts.py` already exported a `ClaudeCodeHostAdapter`, the Task
Capsule schema already enumerated `claude-code`, and Ward already admitted it.
Only a live Host trial reached the one line that did not.

## The repair

`benchwork_open_task` now accepts the same optional `host_session` argument
that `benchwork_complete_task` and `benchwork_fail_task` already took, and
mints the Capsule for that Host. The default remains `codex`, so existing
Codex flows are unchanged, and an unregistered Host is refused rather than
minted and later rejected by Ward.

## Result

The repaired loop completed end to end. Chronicle recorded the Capsule and the
accepted Agent Result under the acting Host:

| Item | Value |
| --- | --- |
| Program | `RP-001`, Receipt `RC-3913CD0AC6A6` |
| Task | `TK-B280B5160682`, capability `bench.code.inspect` |
| Capsule Host | `claude-code` |
| Circle | `read` only, no network, 900 s |
| Ward | `PASS` |
| Completion | `ok: true`, Receipt `RC-47D74468807A` |
| Output | `code-inspection-result/1.0` |

The Host used only `Read` alongside the Benchwork tools, matching the Capsule
Circle. Deep Doctor reported 2 verified Chronicle events with an intact Receipt
chain. The canonical provenance excerpt is in
[`agent-result-provenance.json`](agent-result-provenance.json).

## Verify

```bash
sha256sum --check examples/phase2-final/host-claude-code/SHA256SUMS

jq -e '.verdict.tier_1_claude_code_cli == "PASS"' \
  examples/phase2-final/host-claude-code/trial-log.json

jq -e '.agent_result.provenance.host == "claude-code"' \
  examples/phase2-final/host-claude-code/agent-result-provenance.json

python3 -m unittest \
  tests.mcp.test_runtime.MCPRuntimeTest.test_declared_host_owns_its_capsule_and_completes_the_task \
  tests.mcp.test_runtime.MCPRuntimeTest.test_capsule_defaults_to_codex_and_rejects_a_foreign_host_result \
  tests.mcp.test_runtime.MCPRuntimeTest.test_unknown_task_host_is_refused
```

## Scope

This trial closes Tier 1 for Claude Code CLI only. `HOST-IDE-001` remains
`BLOCKED_BY_ENVIRONMENT` and External Review remains
`WAITING_FOR_DISCLOSURE_AUTHORIZATION`; neither was exercised here. The
inspection output also recorded a residual risk worth carrying forward: the
Circle preservation requirement in the Host adapter README is documentation
prose, not an enforced mechanism.
