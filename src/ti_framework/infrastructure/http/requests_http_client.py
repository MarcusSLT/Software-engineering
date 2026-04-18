"""Requests-based HTTP client implementation."""

from __future__ import annotations

from dataclasses import dataclass

import requests

from ti_framework.ports.http import HttpClient, HttpResponse


@dataclass(slots=True)
class RequestsHttpClient(HttpClient):
    timeout_seconds: float = 20.0
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )

    def get(self, url: str) -> HttpResponse:
        response = requests.get(
            url,
            timeout=self.timeout_seconds,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        response.raise_for_status()

        content_type = response.headers.get("Content-Type")
        encoding = response.encoding or response.apparent_encoding

        return HttpResponse(
            url=response.url,
            status_code=response.status_code,
            content=response.content,
            encoding=encoding,
            content_type=content_type,
        )
