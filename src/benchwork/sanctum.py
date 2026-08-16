"""Experimental, local-only execution-plane state for Phase 3.

This module deliberately does not launch processes, access a network, mutate a
project, or append Chronicle events.  It models the operational Job and Lease
boundary so a future Executor can be tested without confusing its outcome with
scientific state.  Worker results remain untrusted proposals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import re
from typing import Any

from .athanor import SIGIL


class SanctumError(ValueError):
    """Raised when an operational Job or Lease transition is invalid."""


class JobState(StrEnum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class LeaseState(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


_TERMINAL_JOB_STATES = {
    JobState.COMPLETED,
    JobState.FAILED,
    JobState.CANCELLED,
    JobState.EXPIRED,
}
_OPERATIONAL_IDENTIFIER = re.compile(r"^[A-Z]+-[A-Za-z0-9][A-Za-z0-9_-]*$")


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _require_sigil(name: str, value: str) -> None:
    if not isinstance(value, str) or not SIGIL.fullmatch(value):
        raise SanctumError(f"{name} must be a SHA-256 Sigil")


def _require_identifier(prefix: str, name: str, value: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith(prefix)
        or not _OPERATIONAL_IDENTIFIER.fullmatch(value)
    ):
        raise SanctumError(f"{name} must start with {prefix}")


@dataclass
class _Lease:
    lease_id: str
    job_id: str
    worker_id: str
    fencing_token: int
    expires_at: datetime
    status: LeaseState = LeaseState.ACTIVE

    def record(self) -> dict[str, Any]:
        return {
            "schema_version": "sanctum-local-lease/0.1",
            "lease_id": self.lease_id,
            "job_id": self.job_id,
            "worker_id": self.worker_id,
            "fencing_token": self.fencing_token,
            "status": self.status,
            "expires_at": _timestamp(self.expires_at),
        }


@dataclass
class _Job:
    job_id: str
    task_capsule_sigil: str
    circle_sigil: str
    created_at: datetime
    status: JobState = JobState.PENDING
    attempt: int = 0
    worker_id: str | None = None
    lease_id: str | None = None
    result: dict[str, Any] | None = None

    def record(self) -> dict[str, Any]:
        return {
            "schema_version": "sanctum-local-job/0.1",
            "job_id": self.job_id,
            "task_capsule_sigil": self.task_capsule_sigil,
            "circle_sigil": self.circle_sigil,
            "status": self.status,
            "attempt": self.attempt,
            "created_at": _timestamp(self.created_at),
            "worker_id": self.worker_id,
            "lease_id": self.lease_id,
        }


class LocalSanctumRuntime:
    """An in-memory Phase 3 reference state machine, not an Executor.

    The caller supplies timestamps to make expiry and recovery scenarios fully
    deterministic.  All returned mappings conform to the published execution
    schemas; no mapping is a canonical research object.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, _Job] = {}
        self._leases: dict[str, _Lease] = {}
        self._next_fencing_token = 1

    def submit(
        self,
        job_id: str,
        task_capsule_sigil: str,
        circle_sigil: str,
        *,
        now: datetime,
    ) -> dict[str, Any]:
        _require_identifier("JB-", "job_id", job_id)
        _require_sigil("task_capsule_sigil", task_capsule_sigil)
        _require_sigil("circle_sigil", circle_sigil)
        if job_id in self._jobs:
            raise SanctumError(f"Job already exists: {job_id}")
        job = _Job(job_id, task_capsule_sigil, circle_sigil, now)
        self._jobs[job_id] = job
        return job.record()

    def claim(
        self,
        job_id: str,
        lease_id: str,
        worker_id: str,
        duration_seconds: int,
        *,
        now: datetime,
    ) -> dict[str, Any]:
        job = self._job(job_id)
        _require_identifier("LS-", "lease_id", lease_id)
        _require_identifier("WK-", "worker_id", worker_id)
        if duration_seconds <= 0:
            raise SanctumError("duration_seconds must be positive")
        if lease_id in self._leases:
            raise SanctumError(f"Lease already exists: {lease_id}")
        if job.status is not JobState.PENDING:
            raise SanctumError(f"Job cannot be claimed from {job.status}")
        lease = _Lease(
            lease_id=lease_id,
            job_id=job_id,
            worker_id=worker_id,
            fencing_token=self._next_fencing_token,
            expires_at=now + timedelta(seconds=duration_seconds),
        )
        self._next_fencing_token += 1
        self._leases[lease_id] = lease
        job.status = JobState.CLAIMED
        job.attempt += 1
        job.worker_id = worker_id
        job.lease_id = lease_id
        return lease.record()

    def start(self, job_id: str, lease_id: str, *, now: datetime) -> dict[str, Any]:
        job, _ = self._active_lease(job_id, lease_id, now)
        if job.status is not JobState.CLAIMED:
            raise SanctumError(f"Job cannot start from {job.status}")
        job.status = JobState.RUNNING
        return job.record()

    def heartbeat(
        self,
        job_id: str,
        lease_id: str,
        duration_seconds: int,
        *,
        now: datetime,
    ) -> dict[str, Any]:
        job, lease = self._active_lease(job_id, lease_id, now)
        if job.status is not JobState.RUNNING:
            raise SanctumError(f"Job cannot heartbeat from {job.status}")
        if duration_seconds <= 0:
            raise SanctumError("duration_seconds must be positive")
        lease.expires_at = now + timedelta(seconds=duration_seconds)
        return lease.record()

    def finish(
        self,
        job_id: str,
        lease_id: str,
        status: JobState,
        summary: str,
        outputs: list[dict[str, str]],
        *,
        now: datetime,
    ) -> dict[str, Any]:
        job, lease = self._active_lease(job_id, lease_id, now)
        if job.status is not JobState.RUNNING:
            raise SanctumError(f"Job cannot finish from {job.status}")
        if status not in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
            raise SanctumError("finish status must be COMPLETED, FAILED, or CANCELLED")
        if not isinstance(summary, str) or not summary:
            raise SanctumError("summary is required")
        if status is JobState.COMPLETED and not outputs:
            raise SanctumError("a completed Worker Result requires at least one output")
        for output in outputs:
            if set(output) != {"schema", "uri", "blob_sigil"}:
                raise SanctumError("each output has only schema, uri, and blob_sigil")
            _require_sigil("output.blob_sigil", output.get("blob_sigil", ""))
            if (
                not isinstance(output.get("uri"), str)
                or not output["uri"]
                or not isinstance(output.get("schema"), str)
                or not output["schema"]
            ):
                raise SanctumError("each output requires uri, schema, and blob_sigil")
        job.status = status
        lease.status = LeaseState.RELEASED
        job.result = {
            "schema_version": "sanctum-local-worker-result/0.1",
            "job_id": job_id,
            "attempt": job.attempt,
            "worker_id": lease.worker_id,
            "lease_id": lease_id,
            "status": status,
            "summary": summary,
            "outputs": outputs,
            "produced_at": _timestamp(now),
        }
        return job.result.copy()

    def cancel(self, job_id: str, reason: str) -> dict[str, Any]:
        job = self._job(job_id)
        if job.status in _TERMINAL_JOB_STATES:
            raise SanctumError(f"Job is already terminal: {job.status}")
        if not reason:
            raise SanctumError("reason is required")
        job.status = JobState.CANCELLED
        if job.lease_id is not None:
            self._leases[job.lease_id].status = LeaseState.RELEASED
        return job.record()

    def expire_leases(self, *, now: datetime) -> list[dict[str, Any]]:
        """Expire active leases and fail closed their non-terminal Jobs."""
        expired: list[dict[str, Any]] = []
        for lease in self._leases.values():
            if lease.status is LeaseState.ACTIVE and now >= lease.expires_at:
                lease.status = LeaseState.EXPIRED
                job = self._jobs[lease.job_id]
                if job.status not in _TERMINAL_JOB_STATES:
                    job.status = JobState.EXPIRED
                expired.append(job.record())
        return expired

    def job(self, job_id: str) -> dict[str, Any]:
        return self._job(job_id).record()

    def _job(self, job_id: str) -> _Job:
        try:
            return self._jobs[job_id]
        except KeyError as error:
            raise SanctumError(f"Unknown Job: {job_id}") from error

    def _active_lease(self, job_id: str, lease_id: str, now: datetime) -> tuple[_Job, _Lease]:
        job = self._job(job_id)
        if job.lease_id != lease_id:
            raise SanctumError("Lease is not bound to Job")
        lease = self._leases[lease_id]
        if lease.status is not LeaseState.ACTIVE or now >= lease.expires_at:
            if lease.status is LeaseState.ACTIVE:
                lease.status = LeaseState.EXPIRED
                job.status = JobState.EXPIRED
            raise SanctumError("Lease is no longer active")
        return job, lease
