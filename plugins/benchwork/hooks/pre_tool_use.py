#!/usr/bin/env python3
"""Block native-tool writes that bypass the Benchwork control plane."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

MUTATING_SHELL = re.compile(
    r"(?i)(?:^|[\s;&|])(?:rm|mv|cp|install|truncate|tee|sponge|touch|mkdir|"
    r"rmdir|unlink|ln|chmod|chown|dd|patch|rsync|tar|zip|unzip|"
    r"ed|ex|vim|nvim|emacs|perl|python(?:3)?|ruby|node)\b|"
    r"\bgit\s+(?:checkout|restore|clean|reset|rm|mv|apply)\b|"
    r"\bfind\b[^;&|]*(?:-delete|-exec|-execdir)\b|"
    r"\bsed\s+(?:-[A-Za-z]*i[A-Za-z]*|--in-place)\b|"
    r"(?:^|[^<])(?:>>|>)\s*[\"']?[^;&|]*\.benchwork(?:/|\b)"
)
PATCH_TARGET = re.compile(
    r"(?m)^\*\*\* (?:Add|Update|Delete|Move to) File: .*?(?:^|/)\.benchwork(?:/|$)"
)


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("command", "cmd", "patch", "input"):
            if isinstance(value.get(key), str):
                return value[key]
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    tool = str(event.get("tool_name") or "")
    content = _text(event.get("tool_input"))
    if tool in {"apply_patch", "Edit", "Write"} and (
        PATCH_TARGET.search(content) or ".benchwork/" in content
    ):
        _deny("Direct edits to .benchwork are forbidden; use Benchwork MCP tools.")
        return 0
    if tool == "Bash" and ".benchwork" in content and MUTATING_SHELL.search(content):
        _deny("Destructive or mutating shell access to .benchwork is forbidden.")
        return 0
    if tool.startswith("mcp__benchwork__") and re.search(
        r"(?:commit_.*_seal|seal)", tool
    ):
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "additionalContext": (
                            "A scientific Seal requires a fresh preview and explicit "
                            "human confirmation. Athanor remains the enforcement boundary."
                        ),
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
