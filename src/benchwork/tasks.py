"""Task Capsule assembly across Capability and Snapshot boundaries."""

from __future__ import annotations

from typing import Any

from .athanor import Athanor
from .circle import CapsuleStore, CapabilityRegistry
from .snapshots import SnapshotStore


class TaskService:
    """Creates a Task only after pinning its contract and Program state."""

    def __init__(
        self,
        athanor: Athanor,
        registry: CapabilityRegistry,
        capsules: CapsuleStore,
    ) -> None:
        self.athanor = athanor
        self.registry = registry
        self.capsules = capsules
        self.snapshots = SnapshotStore(athanor.root)

    def create(
        self,
        capability: str,
        program_id: str,
        objective: str,
        circle: dict[str, Any],
        *,
        host: str = "cli",
    ) -> dict[str, Any]:
        contract = self.registry.get(capability)
        contract_sigil = self.registry.contract_sigil(capability)
        events = self.athanor.chronicle.events()
        state = self.athanor._project(events)
        snapshot, snapshot_sigil = self.snapshots.create(
            program_id,
            state,
            events,
        )
        return self.capsules.create(
            capability,
            program_id,
            objective,
            contract,
            contract_sigil,
            snapshot,
            snapshot_sigil,
            circle,
            host=host,
        )
