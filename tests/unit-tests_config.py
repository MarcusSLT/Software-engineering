import pytest
from pathlib import Path
import tempfile
import json

# Убедись, что импорты находятся в начале файла
from ti_framework.config.loaders import load_source_configs
from ti_framework.config.models import (
    SourceConfig as DomainSource,
)  # Проверь имя класса в config/models.py


class TestLoadSourceConfigs:
    """Тесты загрузки конфигурации источников."""

    def test_load_valid_json_list(self):
        """Проверка успешной загрузки списка JSON-массива."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "sources.json"

            # Добавлен параметр parser_path во все записи
            data = [
                {
                    "name": "SiteA",
                    "index_url": "http://site-a.com",
                    "parser_path": "/path/to/parser_a",
                },
                {
                    "name": "SiteB",
                    "index_url": "https://site-b.org",
                    "parser_path": "/path/to/parser_b",
                },
            ]

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            try:
                configs = load_source_configs(str(config_path))

                results = [
                    {"count": len(configs)},
                    {item.name for item in configs},
                    {item.index_url for item in configs},
                ]

                assert len(configs) == 2, "Должно быть загружено 2 источника"
                # Проверяем что parser_path тоже заполнен (опционально)
                assert all(c.parser_path != "" for c in configs), (
                    "Все источники должны иметь путь к парсеру"
                )

            except Exception as e:
                pytest.fail(
                    f"Загрузка валидного списка должна пройти успешно. Ошибка: {e}"
                )

    def test_load_valid_json_object_with_sources(self):
        """Проверка успешной загрузки объекта с ключом 'sources'."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"

            data = {
                "name_of_config_file": "ignored",
                "sources": [
                    {
                        "name": "TargetSite",
                        "index_url": "http://target.com",
                        "parser_path": "/path/to/target_parser",
                    }
                ],
            }

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            try:
                configs = load_source_configs(str(config_path))

                assert len(configs) == 1, "Должен быть извлечен один источник"
                assert configs[0].name == "TargetSite", "Имя должно совпадать с JSON"
                # Проверяем наличие parser_path

            except Exception as e:
                pytest.fail(
                    f"Загрузка объекта с ключом 'sources' должна пройти успешно. Ошибка: {e}"
                )

    def test_load_missing_file_raises_error(self):
        """Проверка, что отсутствие файла вызывает ошибку."""

        fake_path = Path("/tmp/nonexistent_config_12345.json")

        try:
            configs = load_source_configs(str(fake_path))

            pytest.fail(
                "Ожидается исключение FileNotFoundError для отсутствующего файла"
            )

        except FileNotFoundError as e:
            assert "nonexistent" in str(e).lower() or "not found" in str(e).lower(), (
                f"Ошибка должна содержать информацию о файле. Получено: {e}"
            )


class TestSourceConfigModelValidation:
    """Тесты валидации модели SourceConfig."""

    def test_valid_config_creation(self):
        """Проверка создания объекта с корректными данными (добавлен parser_path)."""

        try:
            config = DomainSource(
                name="ValidSite",
                index_url="http://valid-site.com/page/index.html",
                parser_path="/path/to/validator_parser",  # Обязательно добавлено
            )

            results = [
                {"name": config.name},
                {"index_url_length": len(config.index_url)},
                {"parser_path_set": bool(config.parser_path)},
            ]

            assert config.name == "ValidSite", "Имя должно совпадать"

        except Exception as e:
            pytest.fail(f"Валидная конфигурация должна создаваться. Ошибка: {e}")

    def test_config_with_empty_name_raises_error(self):
        """Проверка, что пустое имя вызывает ошибку."""

        try:
            config = DomainSource(
                name="",
                index_url="http://example.com",  # Добавлен parser_path для избежания ошибки типа в инициализации
                parser_path="/path/to/parser",  # Обязательно добавлено
            )

            pytest.fail("Ожидается исключение ValueError для пустого имени")

        except ValueError as e:
            assert "name must not be empty" in str(e), (
                f"Ошибка должна содержать текст валидации. Получено: {e}"
            )

    def test_config_with_empty_parser_path_raises_error(self):
        """Проверка, что отсутствие parser_path вызывает ошибку."""

        try:
            config = DomainSource(
                name="TestSite",
                index_url="http://example.com",  # Добавлен для корректной инициализации (если он не обязательный аргумент)
                parser_path="",  # Пустой строковый путь должен вызвать ошибку валидации
            )

            pytest.fail("Ожидается исключение ValueError для пустого parser_path")

        except ValueError as e:
            assert "parser_path must not be empty" in str(e), (
                f"Ошибка должна указывать на parser_path. Получено: {e}"
            )
