"""Requests-based HTTP client implementation."""

from __future__ import annotations

from dataclasses import dataclass

import requests

from ti_framework.ports.http import HttpClient, HttpResponse


@dataclass(slots=True)
class RequestsHttpClient(HttpClient):
    timeout_seconds: float = 20.0
    user_agent: str = "ti-framework/0.1"

    def get(self, url: str) -> HttpResponse:
        response = requests.get(
            url,
            timeout=self.timeout_seconds,
            headers={"User-Agent": self.user_agent},
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
