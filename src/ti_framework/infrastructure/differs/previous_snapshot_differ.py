"""Differ implementation based on the previous persisted snapshot."""

from __future__ import annotations

from pathlib import Path

from ti_framework.domain.exceptions import SnapshotNotFoundError
from ti_framework.domain.models import IndexEntry, SnapshotHandle
from ti_framework.ports.differ import Differ
from ti_framework.ports.parser import Parser
from ti_framework.ports.preprocessor import Preprocessor
from ti_framework.ports.storage import SnapshotStorage


class PreviousSnapshotDiffer(Differ):
    """Return only entries which were absent in the immediately previous snapshot."""

    def __init__(self, storage: SnapshotStorage) -> None:
        self._storage = storage

    def diff(
        self,
        current_snapshot_handle: SnapshotHandle,
        current_entries: list[IndexEntry],
        parser: Parser,
        preprocessor: Preprocessor,
    ) -> list[IndexEntry]:
        current_snapshot = self._storage.load(current_snapshot_handle)
        snapshots = self._storage.list_snapshots(
            current_snapshot.source_name,
            current_snapshot.snapshot_kind,
        )
        if len(snapshots) <= 1:
            return list(current_entries)

        previous_snapshot_handle = snapshots[self._find_current_index(current_snapshot_handle, snapshots) - 1]
        previous_entries = parser.parse_index(preprocessor.preprocess(previous_snapshot_handle))
        previous_urls = {entry.publication_url for entry in previous_entries}
        return [entry for entry in current_entries if entry.publication_url not in previous_urls]

    def _find_current_index(
        self,
        current_snapshot_handle: SnapshotHandle,
        snapshot_handles: list[SnapshotHandle],
    ) -> int:
        current_locator = str(Path(current_snapshot_handle.locator).resolve())
        for index, handle in enumerate(snapshot_handles):
            if str(Path(handle.locator).resolve()) == current_locator:
                return index
        raise SnapshotNotFoundError(
            "Current snapshot handle is not present in storage listing: "
            f"{current_snapshot_handle.locator}"
        )
