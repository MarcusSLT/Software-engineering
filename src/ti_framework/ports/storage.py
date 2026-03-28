"""Persistence ports."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ti_framework.domain.models import Snapshot, SnapshotHandle, SnapshotKind


class SnapshotStorage(ABC):
    """Abstract storage for persisted snapshots."""

    @abstractmethod
    def save(self, snapshot: Snapshot) -> SnapshotHandle:
        raise NotImplementedError

    @abstractmethod
    def load(self, handle: SnapshotHandle) -> Snapshot:
        raise NotImplementedError

    @abstractmethod
    def delete(self, handle: SnapshotHandle) -> None:
        """Delete a persisted snapshot by handle."""
        raise NotImplementedError

    @abstractmethod
    def list_snapshots(
        self,
        source_name: str,
        snapshot_kind: SnapshotKind = "index",
    ) -> list[SnapshotHandle]:
        """Return persisted snapshots for a source and kind ordered from oldest to newest."""
        raise NotImplementedError
