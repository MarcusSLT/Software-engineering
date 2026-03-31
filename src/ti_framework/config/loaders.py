"""Load source definitions from JSON config files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from .models import SourceConfig


def load_source_configs(path: str | Path) -> List[SourceConfig]:
    """Загружает конфигурацию источников. Обработаны ошибки чтения файла и JSON."""

    # Проверка пути до файла (опционально, но полезно для раннего отказа)
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Конфигурация не найдена по пути: {path}")

    try:
        with path_obj.open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)

        rows = _extract_source_rows(payload)
        return [
            SourceConfig(  # Используем имя из импорта выше, проверь соответствие в твоем коде
                name=row["name"],
                index_url=row["index_url"],
                parser_path=row.get(
                    "parser_path", ""
                ),  # Добавлена защита от ключа "parser_path" (если он не обязателен)
                enabled=row.get("enabled", True),
            )
            for row in rows
        ]

    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        # Преобразуем ошибку JSON в понятное сообщение или кастомное исключение
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
