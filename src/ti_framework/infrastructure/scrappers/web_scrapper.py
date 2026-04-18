"""Web-based scrapper implementation."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from ti_framework.domain.exceptions import FetchError
from ti_framework.domain.models import Snapshot, Source
from ti_framework.ports.http import HttpClient
from ti_framework.ports.scrapper import Scrapper
from ti_framework.ports.storage import SnapshotStorage

logger = logging.getLogger(__name__)


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
        logger.info("Fetching %s snapshot for source '%s' from %s", source.snapshot_kind, source.name, source.index_url)
        try:
            response = self._http_client.get(source.index_url)
            payload = response.as_utf8_bytes()
        except Exception as exc:  # noqa: BLE001 - infrastructure boundary
            raise FetchError(
                f"Failed to fetch source '{source.name}' from {source.index_url}: {exc}"
            ) from exc

        logger.debug(
            "Fetched %s snapshot for '%s': status=%s bytes=%d content_type=%r final_url=%s",
            source.snapshot_kind,
            source.name,
            response.status_code,
            len(payload),
            response.content_type,
            response.url,
        )

        if not payload.strip():
            raise FetchError(
                f"Failed to fetch source '{source.name}' from {source.index_url}: empty response body"
            )

        snapshot = Snapshot(
            collected_at=datetime.now(timezone.utc),
            source_url=response.url,
            source_name=source.name,
            snapshot_kind=source.snapshot_kind,
            data=payload,
        )
        logger.debug(
            "Created %s snapshot for '%s' with sha256=%s",
            snapshot.snapshot_kind,
            snapshot.source_name,
            snapshot.sha256_hex,
        )
        return snapshot
