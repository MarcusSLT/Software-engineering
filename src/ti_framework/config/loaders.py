"""Load source definitions from JSON config files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ti_framework.config.models import SourceConfig


def load_source_configs(path: str | Path) -> list[SourceConfig]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)

    rows = _extract_source_rows(payload)
    return [
        SourceConfig(
            name=row["name"],
            index_url=row["index_url"],
            parser_path=row["parser_path"],
            enabled=row.get("enabled", True),
        )
        for row in rows
    ]


def _extract_source_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("sources"), list):
        return payload["sources"]
    raise ValueError("Source config must be a JSON list or an object with a 'sources' list")
