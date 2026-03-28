"""Scrapper abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ti_framework.domain.models import Snapshot, SnapshotHandle, Source
from ti_framework.ports.storage import SnapshotStorage


class Scrapper(ABC):

    def __init__(self, storage: SnapshotStorage) -> None:
        self._storage = storage

    @abstractmethod
    def get_snapshot(self, source: Source) -> Snapshot:
        raise NotImplementedError

    def save_snapshot(self, snapshot: Snapshot) -> SnapshotHandle:
        return self._storage.save(snapshot)

    # Compatibility aliases matching the coursework naming style.
    def getSnapshot(self, source: Source) -> Snapshot:
        return self.get_snapshot(source)

    def saveSnapshot(self, snapshot: Snapshot) -> SnapshotHandle:
        return self.save_snapshot(snapshot)