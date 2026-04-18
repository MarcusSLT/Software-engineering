#!/usr/bin/env python3
"""
Удобный скрипт для запуска всех тестов проекта ti_framework
с генерацией отчётов о покрытии кодом (Coverage).
Запуск: pytest tests/ || python run_tests.py
"""

import subprocess
import sys
from pathlib import Path


def get_coverage_flags():
    """Формирует флаги для coverage, чтобы разделить отчеты по модулям."""
    # Запрашиваем покрытие отдельно для config, domain и infrastructure
    return [
        "--cov=ti_framework.config",
        "--cov-report=term-missing:skip-covered",
        "--cov-config=.coveragerc"
        if Path(".coveragerc").exists()
        else "",  # Если есть конфиг проекта
        "-v",  # Подробный вывод тестов
    ]


def main():
    """Запускает pytest с аргументами для отчётов."""

    print("=" * 60)
    print("TI Framework - Test Runner")
    print(f"Python: {sys.version}")
    print("=" * 60)

    # Команда запускается из корня проекта (где лежит pyproject.toml и src/)
    cmd = [sys.executable, "-m", "pytest"] + get_coverage_flags() + ["tests/"]

    try:
        result = subprocess.run(cmd, check=False)

        print("\n" + "=" * 60)
        if result.returncode == 0:
            print("✅ Все тесты пройдены успешно.")
        else:
            print(f"❌ Найдено {result.returncode} ошибок/проваленных тестов.")

    except FileNotFoundError as e:
        # Если pytest не найден в PATH (редко, но бывает)
        print("Ошибка: Не удалось найти python или модуль pytest. Проверьте окружение.")
        sys.exit(1)


if __name__ == "__main__":
    main()
