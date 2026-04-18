"""Simple entry snapshot fetcher for web publications."""

from __future__ import annotations

from typing import Iterable
import logging

from ti_framework.domain.models import FetchedEntry, IndexEntry, Source
from ti_framework.ports.entry_fetcher import EntryFetcher
from ti_framework.ports.scrapper import Scrapper

logger = logging.getLogger(__name__)


class WebEntryFetcher(EntryFetcher):
    """
    Fetch and persist entry-page snapshots for a list of IndexEntry objects.

    The fetcher reuses the existing Scrapper abstraction and marks all saved
    snapshots as snapshot_kind="entry" so they remain isolated from index snapshots.
    """

    def __init__(self, scrapper: Scrapper) -> None:
        self._scrapper = scrapper

    def fetch(self, index_entries: Iterable[IndexEntry]) -> list[FetchedEntry]:
        index_entries = list(index_entries)
        logger.info("Fetching %d entry pages", len(index_entries))
        results: list[FetchedEntry] = []

        for index_entry in index_entries:
            target = Source(
                name=index_entry.source_name,
                index_url=index_entry.publication_url,
                snapshot_kind="entry",
            )
            try:
                logger.debug("Fetching entry page %s", index_entry.publication_url)
                snapshot = self._scrapper.get_snapshot(target)
                handle = self._scrapper.save_snapshot(snapshot)
            except Exception:  # noqa: BLE001 - one broken entry must not stop the source
                logger.exception("Failed to fetch entry page %s", index_entry.publication_url)
                continue
            results.append(FetchedEntry(index_entry=index_entry, snapshot_handle=handle))
            logger.debug("Fetched entry page %s -> snapshot %s", index_entry.publication_url, handle.locator)

        logger.info("Successfully fetched %d/%d entry pages", len(results), len(index_entries))
        return results
