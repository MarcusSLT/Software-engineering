"""Interfaces for IOC filtering."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from ti_framework.domain.models import Entry, IOC


class IOCFilterRule(Protocol):
    """Single rule used by IOC filters."""

    def should_keep(self, ioc: IOC) -> bool:
        """Return True when the IOC should stay in the feed."""


class IOCFilter(ABC):
    """Filter IOC collections before downstream serialization."""

    @abstractmethod
    def filter_iocs(self, iocs: tuple[IOC, ...] | list[IOC]) -> tuple[IOC, ...]:
        raise NotImplementedError

    def filter_entry(self, entry: Entry) -> Entry:
        filtered_iocs = self.filter_iocs(entry.iocs)
        if filtered_iocs == entry.iocs:
            return entry
        return Entry(
            title=entry.title,
            content=entry.content,
            source_url=entry.source_url,
            source_name=entry.source_name,
            collected_at=entry.collected_at,
            iocs=filtered_iocs,
        )
