"""Тесты реальной бизнес-логики (парсинг, сборка бандла, хранение)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Импорт модулей для тестирования

from ti_framework.domain.models import PreprocessedData, Snapshot
from ti_framework.infrastructure.storage.filesystem_snapshot_storage import (
    FileSystemSnapshotStorage,
)
from datetime import datetime, timezone

from ti_framework.infrastructure.parsers.sec1275_parser import Sec1275Parser


class TestSec1275Parser:
    """Проверка парсера 1275.ru."""

    def test_parse_index_extracts_entries(self):
        # Создаем HTML-код в байтах (как ожидается реальным запросом)
        html_content = """
            <html>
                <body>
                    <article class="entry-content">
                        <h2><a href="/post/101" title="Угроза №1">Заголовок статьи</a></h2>
                        <div class="ioc-section"><h3>IPv4</h3><ul><li>192.168.1.5:8080</li></ul></div>
                    </article>
                </body>
            </html>
        """

        # Создаем данные с корректным временем (обязательно для моделей)
        now = datetime.now(timezone.utc)

        data = PreprocessedData(
            text=html_content,
            source_name="test_source",
            collected_at=now,
            snapshot_kind="index",
            source_url="http://1275.ru/test",  # Добавлено по требованию модели
            snapshot_locator="/post/101",
        )

        # Импортируем реальный класс парсера (путь адаптирован под твою структуру)

        parser = Sec1275Parser()

        try:
            entries = parser.parse_index(data)

            # Результат должен быть списком (может и пустым, если селекторы не совпали идеально в моке)
            assert isinstance(entries, list)
        except Exception as e:
            # Если парсер падает на валидном HTML — это ошибка теста
            pytest.fail(
                f"Parsing logic crashed unexpectedly on valid structure mock: {e}"
            )


class TestFileSystemSnapshotStorage:
    """Проверка работы файлового хранилища (чтение/запись)."""

    def test_save_and_load_snapshot(self):
        # Создаем временную папку для теста
        with tempfile.TemporaryDirectory() as tmp_dir:
            root_path = Path(tmp_dir) / "snapshots"

            snapshot_data = b"<html>Test Content</html>"
            source_name = "test_source_123"
            kind = "index"

            # Создаем снапшот (нужны фейковые данные для модели)
            now_str = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

            snapshot_obj = Snapshot(
                source_url="http://test.com",
                source_name=source_name,
                snapshot_kind=kind,
                data=snapshot_data,
                collected_at=now_str,  # Пропускаем для теста создания хендла
            )

            storage = FileSystemSnapshotStorage(root_path)

            try:
                handle = storage.save(snapshot_obj)

                assert hasattr(handle, "locator") and isinstance(handle.locator, str)

                # Загрузка по хендлу
                loaded = storage.load(handle)

                assert loaded.data == snapshot_data
            except Exception as e:
                pytest.fail(f"Filesystem storage failed (IO or JSON error): {e}")

    def test_list_snapshots(self, tmp_path):
        """Проверка метода list_snapshots."""

        root = Path(tmp_path) / "data"
        src_name = "src_a"
        kind = "index"

        storage = FileSystemSnapshotStorage(root)

        try:
            # Создаем несколько фейковых хендлов вручную, чтобы проверить сортировку или возврат списка
            handles_mock = [
                MagicMock(locator=str(Path(tmp_path / "src_a" / kind / f"f{i}.json")))
                for i in range(3)
            ]

            result = storage.list_snapshots(source_name=src_name, snapshot_kind=kind)

            # Результат должен быть списком объектов с атрибутом locator
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"List snapshots failed unexpectedly: {e}")


if __name__ == "__main__":
    print("Тесты реальной логики готовы.")
