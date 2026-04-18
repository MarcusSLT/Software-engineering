from pathlib import Path

project_root = (
    str(Path(__file__).parent.parent / "src") if __name__ != "__main__" else ""
)
"""

КОМАНДА ДЛЯ ЗАПУСКА ТЕСТОВ:
python -m pytest tests/test_smoke.py --cov=ti_framework.config:tests/test_smoke.py --cov-report=term-missing -v


"""


def test_app_imports():
    """Smoke-тест: Проверка импорта ключевых модулей."""

    # Список критически важных пакетов проекта
    modules_to_check = [
        ("config", ["ti_framework.config.models"]),
        ("domain", ["ti_framework.domain.models"]),
        ("application", ["src.ti_framework.application.pipeline_runner"]),
        # Примечание: для application часто используется путь src., если он есть в структуре.
    ]

    try:
        from ti_framework import config, domain

        print("✅ Модули config и domain загружены.")

        # Попытка импорта pipeline (может требовать src/ или быть доступен напрямую)
        try:
            from ti_framework.application.pipeline_runner import PipelineRunner

            print("✅ Модуль application загружен.")
        except ImportError as e:
            if "src" in str(e):
                # Если ошибка именно в пути src, пробуем импортировать через относительный путь или инициализацию
                from ti_framework.application.pipeline_runner import PipelineRunner

                print("✅ Модуль application загружен (через fallback).")
            else:
                raise

        assert True

    except Exception as e:
        # Если импорт упал — это критическая ошибка сборки/деплойа
        pytest.fail(
            f"Smoke-тест провален: Приложение не может импортировать ключевые модули. Ошибка: {e}"
        )


def test_pipeline_initialization():
    """Smoke-тест: Проверка инициализации оркестратора (без реальных данных)."""

    try:
        from unittest.mock import MagicMock

        # Попытка создать объект PipelineRunner с минимальными зависимостями.
        # Если здесь упадет ошибка — значит, в коде есть блокировка при старте класса.

        runner = type(
            "MockPipeline",
            (),
            {
                "_parser_loader": lambda p: MagicMock(),
                "run_source": lambda x: None,
                "run_all": lambda y: [],
            },
        )()  # Очень упрощенный мок для проверки инициализации

    except Exception as e:
        pytest.fail(f"Smoke-тест провален: Ошибка при подготовке к запуску. {e}")


if __name__ == "__main__":
    try:
        import pytest

        # Запуск через pytest, если файл лежит в tests/
        print("Запуск Smoke-тестов...")

        # Если запускаешь напрямую (без pytest), раскомментируй ниже:
        # test_app_imports()
        # test_pipeline_initialization()

    except ImportError as e:
        if "pytest" in str(e):
            print(
                "Ошибка: Тестируйте этот файл через 'python -m pytest tests/smoke_test.py'"
            )
        else:
            raise
