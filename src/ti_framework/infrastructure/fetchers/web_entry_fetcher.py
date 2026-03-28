"""Simple entry snapshot fetcher for web publications."""

from __future__ import annotations

from typing import Iterable

from ti_framework.domain.models import FetchedEntry, IndexEntry, Source
from ti_framework.ports.entry_fetcher import EntryFetcher
from ti_framework.ports.scrapper import Scrapper


class WebEntryFetcher(EntryFetcher):
    """
    Fetch and persist entry-page snapshots for a list of IndexEntry objects.

    The fetcher reuses the existing Scrapper abstraction and marks all saved
    snapshots as snapshot_kind="entry" so they remain isolated from index snapshots.
    """

    def __init__(self, scrapper: Scrapper) -> None:
        self._scrapper = scrapper

    def fetch(self, index_entries: Iterable[IndexEntry]) -> list[FetchedEntry]:
        results: list[FetchedEntry] = []

        for index_entry in index_entries:
            target = Source(
                name=index_entry.source_name,
                index_url=index_entry.publication_url,
                snapshot_kind="entry",
            )
            snapshot = self._scrapper.get_snapshot(target)
            handle = self._scrapper.save_snapshot(snapshot)
            results.append(FetchedEntry(index_entry=index_entry, snapshot_handle=handle))

        return results
