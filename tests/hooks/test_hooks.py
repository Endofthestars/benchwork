import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HOOKS = Path(__file__).parents[2] / "plugins" / "benchwork" / "hooks"


def run_hook(
    name: str,
    event: dict,
    *,
    environment: dict[str, str] | None = None,
) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env=environment,
        timeout=5,
        check=False,
    )
    output = json.loads(completed.stdout) if completed.stdout.strip() else {}
    return completed.returncode, output


class HookTest(unittest.TestCase):
    def test_pre_tool_denies_direct_state_patch(self) -> None:
        code, output = run_hook(
            "pre_tool_use.py",
            {
                "tool_name": "apply_patch",
                "tool_input": {
                    "command": "*** Update File: .benchwork/chronicle.jsonl\n"
                },
            },
        )
        self.assertEqual(code, 0)
        decision = output["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")

    def test_pre_tool_denies_destructive_shell_but_allows_read(self) -> None:
        denied_commands = (
            "rm -rf .benchwork",
            "echo corrupted | sponge .benchwork/chronicle.jsonl",
            "git checkout -- .benchwork/chronicle.jsonl",
            "find .benchwork -type f -delete",
        )
        denied = []
        for command in denied_commands:
            _, output = run_hook(
                "pre_tool_use.py",
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": command},
                },
            )
            denied.append(output)
        _, allowed = run_hook(
            "pre_tool_use.py",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "cat .benchwork/chronicle.head"},
            },
        )
        self.assertTrue(
            all(
                output["hookSpecificOutput"]["permissionDecision"] == "deny"
                for output in denied
            )
        )
        self.assertEqual(allowed, {})

    def test_post_tool_reminds_about_tests_and_failed_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = {**os.environ, "PLUGIN_DATA": directory}
            _, edit = run_hook(
                "post_tool_use.py",
                {
                    "session_id": "session-1",
                    "tool_name": "apply_patch",
                    "tool_input": {"command": "*** Update File: src/benchwork/athanor.py"},
                    "tool_response": {"ok": True},
                },
                environment=environment,
            )
            _, failure = run_hook(
                "post_tool_use.py",
                {
                    "session_id": "session-1",
                    "tool_name": "Bash",
                    "tool_input": {"command": "python -m pytest tests/test_athanor.py"},
                    "tool_response": {"exit_code": 1},
                },
                environment=environment,
            )
        self.assertIn("smallest relevant tests", str(edit))
        self.assertIn("Preserve this failure", str(failure))
