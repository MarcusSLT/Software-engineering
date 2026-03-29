"""Differ abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ti_framework.domain.models import IndexEntry, SnapshotHandle
from ti_framework.ports.parser import Parser
from ti_framework.ports.preprocessor import Preprocessor


class Differ(ABC):
    """Compare parsed index entries against a previous snapshot."""

    @abstractmethod
    def diff(
        self,
        current_snapshot_handle: SnapshotHandle,
        current_entries: list[IndexEntry],
        parser: Parser,
        preprocessor: Preprocessor,
    ) -> list[IndexEntry]:
        raise NotImplementedError
