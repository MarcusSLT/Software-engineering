"""Load source definitions from JSON config files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List

from .models import SourceConfig

logger = logging.getLogger(__name__)


def load_source_configs(path: str | Path) -> List[SourceConfig]:
    """Загружает конфигурацию источников. Обработаны ошибки чтения файла и JSON."""

    path_obj = Path(path)
    logger.debug("Loading source config from %s", path_obj)
    if not path_obj.exists():
        raise FileNotFoundError(f"Конфигурация не найдена по пути: {path}")

    try:
        with path_obj.open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)

        rows = _extract_source_rows(payload)
        configs = [
            SourceConfig(
                name=row["name"],
                index_url=row["index_url"],
                parser_path=row.get("parser_path", ""),
                enabled=row.get("enabled", True),
            )
            for row in rows
        ]
        logger.info("Loaded %d source configurations from %s", len(configs), path_obj)
        return configs

    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка формата JSON конфигурации ({e})") from e
    except UnicodeDecodeError:
        raise IOError("Файл конфигурации поврежден (не UTF-8)")


def _extract_source_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("sources"), list):
        return payload["sources"]
    raise ValueError(
        "Source config must be a JSON list or an object with a 'sources' list"
    )
