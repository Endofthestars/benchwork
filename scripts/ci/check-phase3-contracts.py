#!/usr/bin/env python3
"""Run the bounded, executable Phase 3 contract gate.

This gate deliberately verifies only the published contract-only surface and
the non-executing local vertical slice.  A pass does not grant Journal replay,
Storage, Result-acceptance, or scientific authority.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TESTS = (
    "tests/test_execution.py",
    "tests/test_execution_state_journal_event_v1_contract.py",
    "tests/test_execution_job_outcome_v1_contract.py",
    "tests/test_artifact_storage_journal_v1_contract.py",
    "tests/test_patch_promotion_journal_v1_contract.py",
    "tests/test_patch_promotion_bundle_v1_contract.py",
    "tests/test_patch_promotion_checkpoint_v1_contract.py",
    "tests/test_patch_promotion_mutation_intent_v1_contract.py",
    "tests/test_patch_promotion_target_guard_v1_contract.py",
    "tests/test_patch_promotion_attempt_v1_contract.py",
    "tests/test_patch_promotion_outcome_v1_contract.py",
    "tests/test_patch_promotion_recovery_record_v1_contract.py",
    "tests/mcp/test_runtime.py",
    "tests/mcp/test_tool_registry.py",
)


def _run(*command: str) -> None:
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def main() -> int:
    python = sys.executable
    _run(python, "scripts/ci/check-schemas.py")
    _run(python, "-m", "pytest", "-q", *TESTS)
    _run(python, "-m", "ruff", "check", "src/benchwork", "tests")
    _run(python, "-m", "mypy", "src")
    print("Phase 3 contract gate passed (contract-only/local vertical slice).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
