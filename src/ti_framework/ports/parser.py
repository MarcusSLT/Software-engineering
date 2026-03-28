"""Parser abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ti_framework.domain.models import Entry, IndexEntry, PreprocessedData


class Parser(ABC):
    """
    Common parsing contract for source-specific parser implementations.

    - parse_index() works with a preprocessed snapshot of a source index page
      and returns discovered publication references.
    - parse_entry() is reserved for future work with individual publication pages.
    """

    @abstractmethod
    def parse_index(self, data: PreprocessedData) -> list[IndexEntry]:
        raise NotImplementedError

    @abstractmethod
    def parse_entry(self, data: PreprocessedData, index_entry: IndexEntry) -> Entry:
        raise NotImplementedError
