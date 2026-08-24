"""Small, explicit local experiment runner for the first usable product loop.

This module intentionally provides a trusted-local execution profile, not a
sandbox.  It runs an argv vector without a shell, captures logs, preserves a
durable operational record, and asks Athanor to record the resulting scientific
Run.  Remote workers, scheduling, retries, and isolation remain separate work.
"""

from __future__ import annotations

import json
import math
import os
import re
import signal
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .athanor import Athanor, AthanorError, content_sigil
from .file_integrity import file_sigil


RUN_ID = re.compile(r"^RUN-[A-Z0-9][A-Z0-9_-]*$")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:  # pragma: no cover - exercised by Windows acceptance
            process.terminate()
        process.wait(timeout=2)
        return
    except (ProcessLookupError, subprocess.TimeoutExpired):
        pass
    if process.poll() is None:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:  # pragma: no cover - exercised by Windows acceptance
            process.kill()
    process.wait()


def _metrics(path: Path | None, inline: dict[str, float]) -> dict[str, float]:
    metrics = dict(inline)
    if path is not None:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AthanorError(f"cannot read metrics JSON: {path}") from error
        if not isinstance(document, dict):
            raise AthanorError("metrics JSON must be an object")
        for name, value in document.items():
            if name in metrics:
                raise AthanorError(f"duplicate metric: {name}")
            metrics[name] = value
    for name, value in metrics.items():
        if (
            not isinstance(name, str)
            or not name.strip()
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise AthanorError("metrics JSON requires finite numeric values")
        metrics[name] = float(value)
    return metrics


class LocalExperimentRunner:
    """Execute one trusted-local command and preserve it as a canonical Run."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve_project_path(self, value: Path, label: str) -> Path:
        path = value if value.is_absolute() else self.root / value
        resolved = path.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as error:
            raise AthanorError(f"{label} must stay inside the project") from error
        return resolved

    def _consume_project_file(self, path: Path, label: str) -> Path:
        if path.is_symlink():
            raise AthanorError(f"{label} must be a regular project file")
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(self.root)
        except (OSError, ValueError) as error:
            raise AthanorError(f"{label} must stay inside the project") from error
        if not resolved.is_file():
            raise AthanorError(f"{label} must be a regular project file")
        return resolved

    def execute(
        self,
        *,
        run_id: str,
        experiment_id: str,
        command: list[str],
        working_directory: Path = Path("."),
        timeout_seconds: int = 1800,
        phase: str = "FORMAL",
        arm: str | None = None,
        seed: int | None = None,
        inline_metrics: dict[str, float] | None = None,
        metrics_file: Path | None = None,
        output_files: list[Path] | None = None,
        exclude: bool = False,
        exclusion_reason: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
            raise AthanorError("Run ID must use the form RUN-<identifier>")
        if not command or any(not isinstance(item, str) or not item or "\x00" in item for item in command):
            raise AthanorError("local execution requires a non-empty argv command")
        if (
            not isinstance(timeout_seconds, int)
            or isinstance(timeout_seconds, bool)
            or not 1 <= timeout_seconds <= 14400
        ):
            raise AthanorError("local execution timeout must be in 1..14400 seconds")
        if phase not in {"PILOT", "FORMAL"}:
            raise AthanorError("Run phase must be PILOT or FORMAL")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise AthanorError("Run seed must be an integer or null")
        if arm is not None and (not isinstance(arm, str) or not arm.strip()):
            raise AthanorError("Run arm must be a non-empty string")
        if exclusion_reason is not None and (
            not isinstance(exclusion_reason, str) or not exclusion_reason.strip()
        ):
            raise AthanorError("Run exclusion reason must be a non-empty string")
        if exclusion_reason is not None and not exclude:
            raise AthanorError("Run exclusion reason requires --exclude")
        _metrics(None, inline_metrics or {})

        working_path = self._resolve_project_path(working_directory, "working directory")
        if not working_path.is_dir():
            raise AthanorError(f"working directory does not exist: {working_directory}")
        athanor = Athanor(self.root)
        experiment = athanor.experiments().get(experiment_id)
        if experiment is None:
            raise AthanorError(f"unknown Experiment: {experiment_id}")
        if run_id in athanor.runs():
            raise AthanorError(f"Run already exists: {run_id}")
        required_status = "PILOT_RUNNING" if phase == "PILOT" else "FORMAL_RUNNING"
        if experiment["status"] != required_status:
            raise AthanorError(
                f"local {phase} Run requires Experiment status {required_status}: "
                f"{experiment['status']}"
            )
        protocol = athanor.protocols()[experiment["protocol_id"]]
        if protocol.get("analysis_spec") is not None and arm is None:
            raise AthanorError("Run arm is required by the Protocol analysis_spec")
        resolved_metrics = (
            self._resolve_project_path(metrics_file, "metrics file")
            if metrics_file is not None
            else None
        )
        resolved_outputs = [
            self._resolve_project_path(path, "output file") for path in (output_files or [])
        ]

        run_directory = self.root / ".benchwork" / "local-runs" / run_id
        if run_directory.exists():
            raise AthanorError(f"local Run execution already exists: {run_id}")
        run_directory.mkdir(parents=True)
        stdout_path = run_directory / "stdout.log"
        stderr_path = run_directory / "stderr.log"
        record_path = run_directory / "execution.json"
        started_at = _utc_now()
        timed_out = False
        cancelled = False
        return_code: int | None = None
        launch_error: str | None = None

        try:
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                try:
                    process = subprocess.Popen(
                        command,
                        cwd=working_path,
                        stdin=subprocess.DEVNULL,
                        stdout=stdout,
                        stderr=stderr,
                        shell=False,
                        start_new_session=os.name == "posix",
                    )
                    try:
                        return_code = process.wait(timeout=timeout_seconds)
                    except subprocess.TimeoutExpired:
                        timed_out = True
                        _stop_process(process)
                    except KeyboardInterrupt:
                        cancelled = True
                        _stop_process(process)
                except subprocess.TimeoutExpired:
                    timed_out = True
                except OSError as error:
                    launch_error = f"{type(error).__name__}: {error}"
        finally:
            stdout_path.touch(exist_ok=True)
            stderr_path.touch(exist_ok=True)

        completed_at = _utc_now()
        status = (
            "CANCELLED"
            if cancelled
            else ("COMPLETED" if return_code == 0 and not timed_out else "FAILED")
        )
        observed_metrics: dict[str, float] = {}
        metrics_error: str | None = None
        if status == "COMPLETED":
            try:
                consumed_metrics = (
                    self._consume_project_file(resolved_metrics, "metrics file")
                    if resolved_metrics is not None
                    else None
                )
                observed_metrics = _metrics(consumed_metrics, inline_metrics or {})
            except AthanorError as error:
                status = "FAILED"
                metrics_error = str(error)

        artifacts = [
            {
                "uri": str(path.relative_to(self.root)),
                "sigil": file_sigil(path),
            }
            for path in (stdout_path, stderr_path)
        ]
        missing_outputs: list[str] = []
        for path in resolved_outputs:
            try:
                consumed_output = self._consume_project_file(path, "output file")
            except AthanorError:
                missing_outputs.append(str(path.relative_to(self.root)))
                status = "FAILED"
                continue
            artifacts.append(
                {
                    "uri": str(consumed_output.relative_to(self.root)),
                    "sigil": file_sigil(consumed_output),
                }
            )

        included = status == "COMPLETED" and bool(observed_metrics) and not exclude
        reason = exclusion_reason
        if status == "COMPLETED" and not included and not reason:
            reason = "No metrics were provided" if not observed_metrics else "Excluded by local runner"

        operational_record: dict[str, Any] = {
            "schema_version": "benchwork-local-run-execution/0.1",
            "run_id": run_id,
            "experiment_id": experiment_id,
            "command": command,
            "working_directory": str(working_path.relative_to(self.root)) or ".",
            "timeout_seconds": timeout_seconds,
            "started_at": started_at,
            "completed_at": completed_at,
            "return_code": return_code,
            "timed_out": timed_out,
            "cancelled": cancelled,
            "launch_error": launch_error,
            "metrics_error": metrics_error,
            "missing_outputs": missing_outputs,
            "status": status,
            "metrics": observed_metrics,
            "artifacts": artifacts,
        }
        operational_record["record_sigil"] = content_sigil(operational_record)
        _atomic_json(record_path, operational_record)

        canonical_artifacts = [
            *artifacts,
            {
                "uri": str(record_path.relative_to(self.root)),
                "sigil": file_sigil(record_path),
            },
        ]

        receipt = athanor.record_run(
            run_id,
            experiment_id,
            status,
            included,
            observed_metrics,
            seed,
            canonical_artifacts,
            phase,
            reason,
            None,
            arm,
        )
        run = athanor.runs()[run_id]
        return {
            "run": run,
            "run_sigil": content_sigil(run),
            "receipt_id": receipt.receipt_id,
            "receipt_sigil": receipt.sigil,
            "execution_record": str(record_path.relative_to(self.root)),
            "stdout": str(stdout_path.relative_to(self.root)),
            "stderr": str(stderr_path.relative_to(self.root)),
        }
