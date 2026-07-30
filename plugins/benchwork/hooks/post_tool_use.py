#!/usr/bin/env python3
"""Emit concise validation and registration reminders after native tools."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

TEST_COMMAND = re.compile(r"(?i)\b(pytest|unittest|tox|nox|cargo test|go test|npm test|npm run test)\b")
EXPERIMENT_COMMAND = re.compile(r"(?i)\b(pilot|experiment|train|benchmark|evaluate|inference)\b")
CORE_PATH = re.compile(r"(?m)(?:src/benchwork/|schemas/|pyproject\.toml)")


def _state_path(session_id: str) -> Path | None:
    data = os.environ.get("PLUGIN_DATA")
    if not data:
        return None
    digest = hashlib.sha256(session_id.encode()).hexdigest()[:24]
    return Path(data) / "hook-state" / f"{digest}.json"


def _load(path: Path | None) -> dict[str, bool]:
    if path is None:
        return {"core_changed": False, "tests_run": False}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return {
            "core_changed": bool(value.get("core_changed")),
            "tests_run": bool(value.get("tests_run")),
        }
    except (OSError, json.JSONDecodeError):
        return {"core_changed": False, "tests_run": False}


def _save(path: Path | None, value: dict[str, bool]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)


def _failed(response: Any) -> bool:
    if isinstance(response, dict):
        exit_code = response.get("exit_code")
        if isinstance(exit_code, int) and exit_code != 0:
            return True
        if response.get("is_error") is True or response.get("ok") is False:
            return True
    text = _flatten(response)
    return bool(re.search(r"(?i)\b(exit code|exited with code|return code)\s*[=:]?\s*[1-9]", text))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    tool = str(event.get("tool_name") or "")
    tool_input = _flatten(event.get("tool_input"))
    response = event.get("tool_response")
    path = _state_path(str(event.get("session_id") or "unknown"))
    state = _load(path)
    messages: list[str] = []

    if tool in {"apply_patch", "Edit", "Write"} and CORE_PATH.search(tool_input):
        state["core_changed"] = True
        state["tests_run"] = False
        messages.append("Core code changed; run the smallest relevant tests before completion.")
    if tool == "Bash" and TEST_COMMAND.search(tool_input):
        state["tests_run"] = not _failed(response)
    if state["core_changed"] and not state["tests_run"] and tool == "Bash":
        if not TEST_COMMAND.search(tool_input):
            messages.append("Core changes remain unvalidated by a successful relevant test.")
    if tool == "Bash" and EXPERIMENT_COMMAND.search(tool_input) and not _failed(response):
        messages.append("Register every experimental outcome, including negative Runs, through Benchwork MCP.")
    if tool.endswith("benchwork_record_run"):
        messages = [message for message in messages if "experimental outcome" not in message]
    if _failed(response):
        messages.append("Preserve this failure in the Task or Run record; do not silently discard it.")
    _save(path, state)

    if messages:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": " ".join(dict.fromkeys(messages))[:1600],
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
