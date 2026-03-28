"""Preprocessor abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ti_framework.domain.models import PreprocessedData, SnapshotHandle


class Preprocessor(ABC):

    @abstractmethod
    def preprocess(self, snapshot_handle: SnapshotHandle) -> PreprocessedData:
        raise NotImplementedError