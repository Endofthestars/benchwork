#!/usr/bin/env python3
"""Inject a small, read-only canonical project summary at session start."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _root(start: Path) -> Path | None:
    for candidate in (start.resolve(), *start.resolve().parents):
        if (candidate / ".benchwork").is_dir() or (candidate / "benchwork.toml").is_file():
            return candidate
    return None


def _call(root: Path, *arguments: str) -> tuple[int, dict[str, Any]]:
    try:
        completed = subprocess.run(
            ["bwork", "--json", *arguments],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        value = json.loads(completed.stdout) if completed.stdout.strip() else {}
        return completed.returncode, value if isinstance(value, dict) else {}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return 1, {}


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    root = _root(Path(str(event.get("cwd") or ".")))
    if root is None:
        return 0
    status_code, status_envelope = _call(root, "status")
    doctor_code, doctor_envelope = _call(root, "doctor", "--deep")
    if status_code != 0:
        context = "Benchwork project detected, but read-only status failed closed."
    else:
        state = status_envelope.get("result", {})
        programs = state.get("programs", {}) if isinstance(state, dict) else {}
        active = None
        context_path = root / ".benchwork" / "context.json"
        try:
            active_value = json.loads(context_path.read_text(encoding="utf-8"))
            active = active_value.get("active_program_id")
        except (OSError, json.JSONDecodeError):
            pass
        program = programs.get(active, {}) if active else {}
        critical = sorted(
            issue_id
            for issue_id, issue in state.get("issues", {}).items()
            if issue.get("status") == "OPEN"
            and issue.get("severity") == "CRITICAL"
            and (active is None or issue.get("program_id") == active)
        )
        doctor_result = doctor_envelope.get("result", {})
        if doctor_code != 0:
            doctor_result = doctor_envelope.get("error", {}).get("details", {}).get("report", {})
        check_count = len(doctor_result.get("checks", {})) if isinstance(doctor_result, dict) else 0
        context = (
            "Benchwork canonical context: "
            f"active Program={active or 'none'}; "
            f"stage={program.get('status', 'none')}; "
            f"CRITICAL Issues={','.join(critical) if critical else 'none'}; "
            f"Deep Doctor={'PASS' if doctor_code == 0 else 'FAIL'} ({check_count} checks). "
            "Use Benchwork MCP tools for canonical changes; never edit .benchwork directly."
        )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context[:1800],
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
