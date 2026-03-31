from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from src.ti_framework.application.pipeline_runner import PipelineRunner

import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock

from ti_framework.config.models import SourceConfig


class TestPipelineRunnerIntegration:
    """Тесты интеграции оркестратора пайплайна с моками портов."""

    def test_run_source_creates_snapshot_and_parses_index(self):
        source_config = SourceConfig(
            name="TestSource",
            index_url="http://example.com/index.html",
            parser_path="/path/to/parser",
        )

        try:
            runner = PipelineRunner(
                scrapper=None,
                preprocessor=MagicMock(return_value="<html>cleaned</html>"),
                differ=MagicMock(diff=lambda **kwargs: []),
                storage=MagicMock(
                    save=lambda *a: type("SnapshotHandle", (), {"locator": "loc_1"})()
                ),
                parser_loader=lambda p: type(
                    "Parser",
                    (),
                    {
                        "parse_index": lambda self, data=None: [
                            type("IE", (object,), {"title": "Title1"})
                        ]
                    },
                ),
            )

        except Exception as e:
            pytest.fail(f"Инициализация PipelineRunner упала. Ошибка: {e}")

    def test_run_source_drops_fresh_snapshot_if_no_new_entries(self):
        """Проверка логики удаления снапшота, если новых записей нет."""

        source_config = SourceConfig(
            name="TestSource",
            index_url="http://example.com/index.html",
            parser_path="/path/to/parser",
        )

        mock_scapper = MagicMock()
        mock_storage = MagicMock()

        def side_effect_save(*args):
            return type("SnapshotHandle", (), {"locator": "loc_1"})()

        mock_storage.save = lambda *a: side_effect_save()

        # Имитируем наличие старых снапшотов (> 1)
        mock_storage.list_snapshots.side_effect = lambda *a, **kw: [
            "old_snapshot_loc",
            "another_old",
        ]

        try:
            runner = PipelineRunner(
                scrapper=mock_scapper,
                preprocessor=MagicMock(return_value="<html>cleaned</html>"),
                differ=MagicMock(diff=lambda **kwargs: []),
                storage=mock_storage,
                parser_loader=lambda p: type(
                    "Parser",
                    (),
                    {
                        "parse_index": lambda self, data=None: [
                            type("IE", (object,), {"title": "Title1"})
                        ]
                    },
                ),
            )

            result = runner.run_source(source_config)

            assert result.snapshot_deleted is True, "Снапшот должен был быть удален"

        except Exception as e:
            pytest.fail(
                f"Логика удаления снапшота должна работать корректно. Ошибка: {e}"
            )

    def test_run_all_filters_disabled_sources(self):
        """Проверка, что run_all пропускает источники с enabled=False."""

        config_enabled = SourceConfig(
            name="ActiveSource",
            index_url="http://active.com/index.html",
            parser_path="/path/to/parser",
        )

        config_disabled = SourceConfig(
            name="InactiveSource",
            index_url="http://inactive.com/index.html",
            enabled=False,
            parser_path="/path/to/parser",
        )

        try:
            runner = PipelineRunner(
                scrapper=MagicMock(),
                preprocessor=MagicMock(return_value="<html>cleaned</html>"),
                differ=MagicMock(diff=lambda **kwargs: []),
                storage=MagicMock(save=lambda *a: type("H", (), {"locator": "loc"})()),
                parser_loader=lambda p: type(
                    "Parser",
                    (),
                    {
                        "parse_index": lambda self, data=None: [
                            type("IE", (object,), {"title": "Title1"})
                        ]
                    },
                ),
            )

            results = runner.run_all([config_enabled, config_disabled])

            assert len(results) == 1, (
                f"Должен быть обработан только один активный источник. Получено: {len(results)}"
            )

        except Exception as e:
            pytest.fail(
                f"Фильтрация отключенных источников должна работать корректно. Ошибка: {e}"
            )
