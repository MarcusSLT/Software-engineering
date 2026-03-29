"""Entry fetcher abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from ti_framework.domain.models import FetchedEntry, IndexEntry


class EntryFetcher(ABC):
    """Fetch and persist snapshots for concrete publication pages."""

    @abstractmethod
    def fetch(self, index_entries: Iterable[IndexEntry]) -> list[FetchedEntry]:
        raise NotImplementedError
