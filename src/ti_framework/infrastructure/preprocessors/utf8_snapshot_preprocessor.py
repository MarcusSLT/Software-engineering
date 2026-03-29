"""Preprocessor implementation for UTF-8 text snapshots."""

from __future__ import annotations

from ti_framework.domain.exceptions import PreprocessingError
from ti_framework.domain.models import PreprocessedData, SnapshotHandle
from ti_framework.ports.preprocessor import Preprocessor
from ti_framework.ports.storage import SnapshotStorage


class Utf8SnapshotPreprocessor(Preprocessor):
    """Load a persisted UTF-8 snapshot and expose parser-ready text."""

    def __init__(self, storage: SnapshotStorage) -> None:
        self._storage = storage

    def preprocess(self, snapshot_handle: SnapshotHandle) -> PreprocessedData:
        try:
            snapshot = self._storage.load(snapshot_handle)
            text = snapshot.data.decode("utf-8")
        except Exception as exc:  # noqa: BLE001 - storage and encoding boundary
            raise PreprocessingError(
                f"Failed to preprocess snapshot '{snapshot_handle.locator}': {exc}"
            ) from exc

        return PreprocessedData(
            collected_at=snapshot.collected_at,
            source_url=snapshot.source_url,
            source_name=snapshot.source_name,
            snapshot_kind=snapshot.snapshot_kind,
            text=text,
            snapshot_locator=snapshot_handle.locator,
        )