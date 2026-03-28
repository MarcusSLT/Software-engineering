"""HTTP-related ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Minimal HTTP response abstraction for scraper implementations."""

    url: str
    status_code: int
    content: bytes
    encoding: str | None = None
    content_type: str | None = None

    def as_utf8_bytes(self) -> bytes:
        """
        Normalize text payload into UTF-8 bytes.

        For the current stage of the project, snapshots are assumed to carry
        text-oriented source material.
        """
        source_encoding = self.encoding or "utf-8"
        text = self.content.decode(source_encoding, errors="replace")
        return text.encode("utf-8")


class HttpClient(Protocol):
    """Port for HTTP clients used by scrapers."""

    def get(self, url: str) -> HttpResponse:
        ...
