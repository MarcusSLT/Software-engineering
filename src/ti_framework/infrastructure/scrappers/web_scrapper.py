"""Web-based scrapper implementation."""

from __future__ import annotations

from datetime import datetime, timezone

from ti_framework.domain.exceptions import FetchError
from ti_framework.domain.models import Snapshot, Source
from ti_framework.ports.http import HttpClient
from ti_framework.ports.scrapper import Scrapper
from ti_framework.ports.storage import SnapshotStorage


class WebScrapper(Scrapper):
    """
    Scrapper for web sources.

    Responsibility:
    - load the target page;
    - normalize it into UTF-8 bytes;
    - return a Snapshot.

    It does not own persistence logic. Saving remains available through the
    inherited save_snapshot/saveSnapshot methods.
    """

    def __init__(self, http_client: HttpClient, storage: SnapshotStorage) -> None:
        super().__init__(storage=storage)
        self._http_client = http_client

    def get_snapshot(self, source: Source) -> Snapshot:
        try:
            response = self._http_client.get(source.index_url)
            payload = response.as_utf8_bytes()
        except Exception as exc:  # noqa: BLE001 - infrastructure boundary
            raise FetchError(
                f"Failed to fetch source '{source.name}' from {source.index_url}: {exc}"
            ) from exc

        if not payload.strip():
            raise FetchError(
                f"Failed to fetch source '{source.name}' from {source.index_url}: empty response body"
            )

        return Snapshot(
            collected_at=datetime.now(timezone.utc),
            source_url=response.url,
            source_name=source.name,
            snapshot_kind=source.snapshot_kind,
            data=payload,
        )
