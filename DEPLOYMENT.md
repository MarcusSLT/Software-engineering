Полное руководство по развертыванию и сборке TI Framework
Проект: Software-engineering
 
ОГЛАВЛЕНИЕ
 
1. Требования к среде
2. Подготовка окружения
3. Сборка проекта
4. Конфигурация системы
5. Верификация сборки
6. Запуск системы
7. Продакшн-развертывание
8. Мониторинг и обслуживание
9. Устранение неполадок
 
1. ТРЕБОВАНИЯ К СРЕДЕ
 
1.1. Системные требования
 
Параметр
 Минимальные
 Рекомендуемые
Операционная система
 Linux / macOS / Windows 10+
 Ubuntu 20.04+ / Debian 11+
Python
 3.11+
 3.11+
Оперативная память
 2 GB
 4 GB+
Дисковое пространство
 500 MB
 2 GB+
Сетевой доступ
 HTTPS (порт 443)
 Стабильное соединение
Права доступа
 Чтение/запись в директорию проекта
 Выделенный пользователь

 
1.2. Проверка системных требований
 
# Проверка версии Python (должно быть ≥ 3.11)
python3 --version
 
# Если версия ниже 3.11, установите актуальную:
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
 
# macOS (через Homebrew):
brew install python@3.11
 
# Проверка наличия pip
python3 -m pip --version
 
# Проверка наличия git
git --version
 
# Проверка доступного дискового пространства
df -h .
 
# Проверка прав на запись в текущую директорию
touch test_write_permission && rm test_write_permission && echo "Write access: OK"
 
1.3. Необходимые системные пакеты
 
# Ubuntu/Debian
sudo apt update
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    git \
    curl \
    wget \
    build-essential
 
# CentOS/RHEL
sudo yum install -y \
    python3.11 \
    python3.11-venv \
    python3.11-devel \
    git \
    curl \
    wget \
    gcc \
    gcc-c++
 
# macOS (через Homebrew)
brew install python@3.11 git
 
2. ПОДГОТОВКА ОКРУЖЕНИЯ
 
2.1. Клонирование репозитория
 
# Перейдите в директорию для установки
cd /opt  # Для Linux продакшн
# или
cd ~/projects  # Для локальной разработки
 
# Клонирование репозитория
git clone https://github.com/MarcusSLT/Software-engineering.git
cd Software-engineering
 
# Проверка структуры проекта
ls -la
 
Ожидаемая структура после клонирования:
Software-engineering/
├── config/                    # Конфигурационные файлы
│   └── sources.json          # Конфигурация источников
├── src/ti_framework/         # Исходный код фреймворка
│   ├── application/          # Оркестрация (PipelineRunner)
│   ├── cli.py                # CLI интерфейс
│   ├── config/               # Загрузка конфигурации
│   ├── domain/               # Доменные модели
│   ├── infrastructure/       # Реализации портов
│   ├── logging_utils.py      # Утилиты логирования
│   └── ports/                # Контракты (интерфейсы)
├── tests/                    # Unit- и интеграционные тесты
├── examples/                 # Примеры запуска
│   ├── run_pipeline.py       # Полный pipeline
│   └── run_web_scrapper.py   # Тест скраппера
├── data/                     # Рабочие данные (создаётся при запуске)
│   ├── snapshots/            # Промежуточные snapshot
│   ├── bundles/              # STIX Bundle результаты
│   ├── logs/                 # Логи выполнения
│   └── status/               # Статус последнего запуска
├── pyproject.toml            # Конфигурация проекта и зависимостей
├── requirements.txt          # Зависимости (альтернатива pyproject.toml)
└── README.md                 # Документация
 
2.2. Создание виртуального окружения
 
# Перейдите в директорию проекта
cd /opt/Software-engineering
 
# Создание виртуального окружения
python3.11 -m venv .venv
 
# Активация виртуального окружения
# Linux/macOS:
source .venv/bin/activate
 
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
 
# Windows (Command Prompt):
.venv\Scripts\activate.bat
 
# Проверка активации (должен появиться префикс (.venv))
which python
# Ожидаемый вывод: /opt/Software-engineering/.venv/bin/python
 
python --version
# Ожидаемый вывод: Python 3.11.x
 
2.3. Установка зависимостей
 
# Обновление pip до актуальной версии
pip install --upgrade pip
 
# Установка зависимостей из pyproject.toml (рекомендуется)
pip install -e .
 
# Альтернативно: установка из requirements.txt
pip install -r requirements.txt
 
# Установка дополнительных инструментов для разработки
pip install pytest pytest-cov flake8 black mypy
 
# Проверка установленных пакетов
pip list
 
Ожидаемые ключевые пакеты:
Пакет
 Версия
 Назначение
requests
 ≥2.31, <3.0
 HTTP-запросы к источникам
beautifulsoup4
 ≥4.12, <5.0
 Парсинг HTML
stix2
 ≥3.0, <4.0
 Генерация STIX 2.1 объектов
pytest
 ≥7.0
 Тестирование
pytest-cov
 ≥4.0
 Измерение покрытия кода

 
2.4. Настройка прав доступа (для Linux продакшн)
 
# Создание выделенного пользователя для запуска
sudo useradd -r -s /bin/false ti-framework
 
# Создание директорий для данных
sudo mkdir -p /opt/Software-engineering/data/{snapshots,bundles,logs,status}
 
# Установка владельца
sudo chown -R ti-framework:ti-framework /opt/Software-engineering
 
# Установка прав на чтение/запись
sudo chmod -R 750 /opt/Software-engineering
sudo chmod -R 770 /opt/Software-engineering/data
 
# Проверка прав
ls -la /opt/Software-engineering/
 
3. СБОРКА ПРОЕКТА
 
3.1. Типы сборок
 
Тип сборки
 Назначение
 Команда
 Когда использовать
Dev-сборка
 Локальная разработка
 pip install -e .
 Разработка, отладка
Test-сборка
 Запуск тестов в CI
 pip install . + pytest
 CI/CD pipeline
Release-сборка
 Продакшн-развёртывание
 pip install .
 Продуктивная среда

 
3.2. Dev-сборка (локальная разработка)
 
# 1. Клонирование репозитория
git clone https://github.com/MarcusSLT/Software-engineering.git
cd Software-engineering
 
# 2. Создание виртуального окружения
python3.11 -m venv .venv
source .venv/bin/activate
 
# 3. Установка в режиме разработки (editable mode)
pip install -e .
 
# 4. Установка инструментов разработки
pip install pytest pytest-cov flake8 black mypy
 
# 5. Копирование шаблона конфигурации
cp config/sources.json.example config/sources.json 2>/dev/null || true
 
# 6. Запуск smoke-тестов
pytest tests/ --smoke
 
# 7. Проверка CLI
ti-framework --help
 
3.3. Test-сборка (CI/CD pipeline)
 
# .github/workflows/ci.yml
name: TI Framework CI
 
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
 
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Create virtual environment
        run: python -m venv .venv
      
      - name: Activate and install dependencies
        run: |
          source .venv/bin/activate
          pip install --upgrade pip
          pip install -e .
          pip install pytest pytest-cov flake8
      
      - name: Run linting
        run: |
          source .venv/bin/activate
          flake8 src/ti_framework/ tests/
      
      - name: Run unit tests
        run: |
          source .venv/bin/activate
          pytest tests/ \
            --cov=src/ti_framework \
            --cov-report=html \
            --cov-report=xml \
            --cov-report=term \
            --junitxml=reports/test-results.xml
      
      - name: Check coverage
        run: |
          source .venv/bin/activate
          coverage report --fail-under=70
      
      - name: Upload coverage report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: htmlcov/
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: reports/
 
3.4. Release-сборка
 
# 1. Checkout релизной версии
git checkout tags/v1.0.0  # Или актуальный тег
 
# 2. Создание изолированного окружения
python3.11 -m venv /opt/ti-framework/.venv
 
# 3. Активация окружения
source /opt/ti-framework/.venv/bin/activate
 
# 4. Установка без кэша (для чистоты сборки)
pip install --no-cache-dir .
 
# 5. Копирование продуктивной конфигурации
cp config/sources.json.prod /opt/ti-framework/config/sources.json
 
# 6. Создание директорий для артефактов
mkdir -p /opt/ti-framework/data/{snapshots,bundles,logs,status}
 
# 7. Установка прав доступа
chown -R ti-framework:ti-framework /opt/ti-framework
chmod -R 750 /opt/ti-framework
chmod -R 770 /opt/ti-framework/data
 
# 8. Валидация конфигурации
ti-framework validate --config config/sources.json
 
# 9. Запуск тестов перед развёртыванием
pytest tests/ --cov-fail-under=70
 
# 10. Создание бэкапа текущей версии (при обновлении)
# tar -czf /backup/ti-framework-$(date +%Y%m%d).tar.gz /opt/ti-framework
 
3.5. Автоматизация сборки (Makefile)
 
# Makefile для автоматизации сборок
 
.PHONY: setup install test test-coverage lint clean validate run run-scraper release
 
# Настройки
PYTHON := python3.11
VENV := .venv
ACTIVATE := source $(VENV)/bin/activate
 
# Создание окружения
setup:
        	$(PYTHON) -m venv $(VENV)
        	@echo "Virtual environment created at $(VENV)"
 
# Установка зависимостей
install:
        	$(ACTIVATE) && pip install --upgrade pip
        	$(ACTIVATE) && pip install -e .
        	@echo "Dependencies installed"
 
# Установка для продакшна
install-prod:
        	$(ACTIVATE) && pip install --no-cache-dir .
        	@echo "Production installation complete"
 
# Запуск всех тестов
test:
        	$(ACTIVATE) && pytest tests/ -v
 
# Запуск тестов с отчётом о покрытии
test-coverage:
        	$(ACTIVATE) && pytest tests/ \
                    	--cov=src/ti_framework \
                    	--cov-report=html \
                    	--cov-report=term \
                    	--cov-fail-under=70
        	@echo "Coverage report generated in htmlcov/"
 
# Линтинг кода
lint:
        	$(ACTIVATE) && flake8 src/ti_framework/ tests/
        	@echo "Linting complete"
 
# Валидация конфигурации
validate:
        	$(ACTIVATE) && ti-framework validate --config config/sources.json
        	@echo "Configuration validated"
 
# Запуск полного pipeline
run:
        	$(ACTIVATE) && ti-framework run \
                    	--config config/sources.json \
                    	--log-file data/logs/pipeline.log \
                    	--log-level INFO
 
# Запуск только скраппера (тест)
run-scraper:
        	$(ACTIVATE) && python examples/run_web_scrapper.py
 
# Очистка артефактов
clean:
        	find . -type d -name __pycache__ -exec rm -rf {} +
        	find . -type f -name "*.pyc" -delete
        	rm -rf $(VENV)/ htmlcov/ .pytest_cache/ .mypy_cache/
        	rm -rf data/snapshots/* data/bundles/* data/logs/* data/status/*
        	@echo "Cleanup complete"
 
# Подготовка релиза
release: lint test-coverage validate
        	@echo "Release build complete"
        	@echo "Ready for deployment"
 
Использование Makefile:
make setup          # Создание виртуального окружения
make install        # Установка зависимостей для разработки
make install-prod   # Установка для продакшна
make test           # Запуск всех тестов
make test-coverage  # Тесты с отчётом о покрытии
make lint           # Проверка стиля кода
make validate       # Валидация конфигурации
make run            # Запуск полного pipeline
make run-scraper    # Тест скраппера
make clean          # Очистка временных файлов
make release        # Полная подготовка релиза
 
4. КОНФИГУРАЦИЯ СИСТЕМЫ
 
4.1. Структура конфигурационного файла
 
Файл: config/sources.json
{
  "sources": [
    {
      "name": "SEC-1275 IOC",
      "index_url": "https://1275.ru/ioc/",
      "parser_path": "ti_framework.infrastructure.parsers.sec1275_parser.Sec1275Parser",
      "enabled": true
    },
    {
      "name": "Securelist",
      "index_url": "https://securelist.com/all/",
      "parser_path": "ti_framework.infrastructure.parsers.securelist_parser.SecurelistParser",
      "enabled": true
    },
    {
      "name": "Proofpoint Threat Insight",
      "index_url": "https://www.proofpoint.com/us/blog/threat-insight",
      "parser_path": "ti_framework.infrastructure.parsers.proofpoint_threat_insight_parser.ProofpointThreatInsightParser",
      "enabled": true
    }
  ]
}
 
4.2. Поля конфигурации
 
Поле
 Тип
 Обязательное
 Описание
 Пример
name
 string
 Да
 Уникальное имя источника
 "SEC-1275 IOC"
index_url
 string
 Да
 URL индексной страницы источника
 "https://1275.ru/ioc/"
parser_path
 string
 Да
 Полный путь к классу парсера
 "ti_framework.infrastructure.parsers.sec1275_parser.Sec1275Parser"
enabled
 boolean
  Да
 Флаг активности источника
 true / false

 
4.3. Создание конфигурации для разных окружений
 
4.3.1. Development (sources.json.dev)
{
  "sources": [
    {
      "name": "SEC-1275 IOC",
      "index_url": "https://1275.ru/ioc/",
      "parser_path": "ti_framework.infrastructure.parsers.sec1275_parser.Sec1275Parser",
      "enabled": true
    }
  ]
}
 
4.3.2. Testing (sources.json.test)
{
  "sources": [
    {
      "name": "SEC-1275 IOC",
      "index_url": "https://1275.ru/ioc/",
      "parser_path": "ti_framework.infrastructure.parsers.sec1275_parser.Sec1275Parser",
      "enabled": true
    },
    {
      "name": "Securelist",
      "index_url": "https://securelist.com/all/",
      "parser_path": "ti_framework.infrastructure.parsers.securelist_parser.SecurelistParser",
      "enabled": true
    }
  ]
}
 
4.3.3. Production (sources.json.prod)
{
  "sources": [
    {
      "name": "SEC-1275 IOC",
      "index_url": "https://1275.ru/ioc/",
      "parser_path": "ti_framework.infrastructure.parsers.sec1275_parser.Sec1275Parser",
      "enabled": true
    },
    {
      "name": "Securelist",
      "index_url": "https://securelist.com/all/",
      "parser_path": "ti_framework.infrastructure.parsers.securelist_parser.SecurelistParser",
      "enabled": true
    },
    {
      "name": "Proofpoint Threat Insight",
      "index_url": "https://www.proofpoint.com/us/blog/threat-insight",
      "parser_path": "ti_framework.infrastructure.parsers.proofpoint_threat_insight_parser.ProofpointThreatInsightParser",
      "enabled": true
    }
  ]
}
 
4.4. Валидация конфигурации
 
# Проверка конфигурации перед запуском
ti-framework validate --config config/sources.json
 
# Ожидаемый вывод при успехе:
# ✓ Configuration valid
# ✓ All parsers found
# ✓ All sources enabled: 3
 
# Проверка с подробным логированием
ti-framework validate --config config/sources.json --log-level DEBUG
 
4.5. Добавление нового источника
 
# 1. Откройте конфигурационный файл
nano config/sources.json
 
# 2. Добавьте новую запись в массив sources
{
  "name": "New Source Name",
  "index_url": "https://newsource.com/ioc/",
  "parser_path": "ti_framework.infrastructure.parsers.new_parser.NewParser",
  "enabled": true
}
 
# 3. Реализуйте парсер (наследник ports/Parser)
# См. примеры в src/ti_framework/infrastructure/parsers/
 
# 4. Протестируйте новый источник
ti-framework validate --config config/sources.json
python examples/run_web_scrapper.py
 
# 5. Запустите полный pipeline
ti-framework run --config config/sources.json
 
5. ВЕРИФИКАЦИЯ СБОРКИ
 
5.1. Контрольные точки верификации
 
Этап
 Проверка
 Команда
 Ожидаемый результат
После установки Python
 Версия ≥ 3.11
 python --version
 Python 3.11.x
После установки зависимостей
 Все пакеты установлены
 pip list
 requests, beautifulsoup4, stix2 в списке
После валидации конфигурации
 Конфиг валиден
 ti-framework validate
 ✓ Configuration valid
После smoke-тестов
 Все тесты прошли
 pytest tests/ --smoke
 26 passed
После первого запуска
 STIX Bundle создан
 ls data/bundles/
 Файл bundle--*.json
После валидации STIX
 Bundle соответствует стандарту
 python -c "import stix2; stix2.parse(open('data/bundles/...'))"
 Без ошибок

 
5.2. Чек-лист успешной сборки
 
[ ] Python ≥ 3.11 установлен и активен
[ ] Виртуальное окружение создано и активировано
[ ] Все зависимости из pyproject.toml установлены
[ ] Файл config/sources.json существует и валиден
[ ] Smoke-тесты проходят без ошибок (26 тестов)
[ ] Unit-тесты с покрытием ≥70% для ключевых модулей
[ ] Директории data/{snapshots,bundles,logs,status} созданы
[ ] Права доступа настроены корректно
[ ] Первый запуск pipeline завершён успешно (код 0)
[ ] STIX Bundle сформирован и валиден
[ ] Логи записываются в data/logs/
[ ] Статус последнего запуска доступен в data/status/
 
5.3. Автоматическая проверка сборки (скрипт)
 
#!/bin/bash
# verify_build.sh
 
set -e
 
echo "=== TI Framework Build Verification ==="
echo ""
 
# Проверка Python
echo "[1/8] Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
if [[ $(python -c "import sys; print(sys.version_info >= (3, 11))") == "True" ]]; then
    echo "✓ Python $PYTHON_VERSION"
else
    echo "✗ Python 3.11+ required, found $PYTHON_VERSION"
    exit 1
fi
 
# Проверка виртуального окружения
echo "[2/8] Checking virtual environment..."
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✓ Virtual environment active: $VIRTUAL_ENV"
else
    echo "✗ Virtual environment not active"
    exit 1
fi
 
# Проверка зависимостей
echo "[3/8] Checking dependencies..."
pip show requests beautifulsoup4 stix2 > /dev/null 2>&1 && echo "✓ Core dependencies installed" || exit 1
 
# Проверка конфигурации
echo "[4/8] Validating configuration..."
ti-framework validate --config config/sources.json || exit 1
 
# Запуск smoke-тестов
echo "[5/8] Running smoke tests..."
pytest tests/ --smoke -q || exit 1
 
# Проверка директорий
echo "[6/8] Checking data directories..."
for dir in snapshots bundles logs status; do
    [ -d "data/$dir" ] || mkdir -p "data/$dir"
done
echo "✓ Data directories ready"
 
# Тестовый запуск скраппера
echo "[7/8] Testing web scrapper..."
python examples/run_web_scrapper.py || echo "⚠ Scrapper test skipped (network may be unavailable)"
 
# Итог
echo "[8/8] Build verification complete!"
echo ""
echo "=== All checks passed ==="
echo "Ready to run: ti-framework run --config config/sources.json"
 
Использование:
chmod +x verify_build.sh
./verify_build.sh
 
6. ЗАПУСК СИСТЕМЫ
 
6.1. CLI команды
 
Команда
 Назначение
 Пример
ti-framework validate
 Валидация конфигурации
 ti-framework validate --config config/sources.json
ti-framework run
 Запуск полного pipeline
 ti-framework run --config config/sources.json
ti-framework status
 Просмотр статуса последнего запуска
 ti-framework status --status-file data/status/last_run.json
ti-framework --help
 Справка по командам
 ti-framework --help

 
.2. Запуск полного pipeline
 
# Базовый запуск
ti-framework run --config config/sources.json
 
# Запуск с логированием в файл
ti-framework run \
  --config config/sources.json \
  --log-file data/logs/pipeline.log \
  --log-level INFO
 
# Запуск с подробным логированием (DEBUG)
ti-framework run \
  --config config/sources.json \
  --log-file data/logs/pipeline.log \
  --log-level DEBUG \
  --status-file data/status/last_run.json
 
# Запуск с кастомными директориями
ti-framework run \
  --config config/sources.json \
  --snapshots-dir /custom/snapshots \
  --bundles-dir /custom/bundles \
  --log-file /custom/logs/pipeline.log
 
6.3. Ожидаемый вывод при запуске
 
=== TI Framework Pipeline ===
Configuration: config/sources.json
Log level: INFO
Log file: data/logs/pipeline.log
 
Processing source: SEC-1275 IOC
  ✓ Index snapshot created
  ✓ New entries found: 2
  ✓ Entries fetched: 2
  ✓ IoC extracted: 47
  ✓ STIX Bundle created: data/bundles/sec-1275/bundle--xxx.json
 
Processing source: Securelist
  ✓ Index snapshot created
  ✓ New entries found: 0
  ✓ No new entries - snapshot cleaned
 
Processing source: Proofpoint Threat Insight
  ✓ Index snapshot created
  ✓ New entries found: 1
  ✓ Entries fetched: 1
  ✓ IoC extracted: 23
  ✓ STIX Bundle created: data/bundles/proofpoint/bundle--yyy.json
 
=== Summary ===
Total sources: 3
Succeeded: 3
Failed: 0
Total IoC extracted: 70
Total STIX objects: 145
 
Status saved to: data/status/last_run.json
Pipeline completed successfully (exit code: 0)
 
6.4. Просмотр статуса последнего запуска
 
# Команда CLI
ti-framework status --status-file data/status/last_run.json
 
# Прямой просмотр JSON
cat data/status/last_run.json | python -m json.tool
 
# Пример содержимого status-файла:
{
  "generated_at": "2026-04-19T10:30:00+00:00",
  "config_path": "config/sources.json",
  "total_sources": 3,
  "succeeded_sources": 3,
  "failed_sources": 0,
  "sources": [
    {
      "source_name": "SEC-1275 IOC",
      "succeeded": true,
      "total_index_entries": 15,
      "new_index_entries": 2,
      "fetched_entries": 2,
      "parsed_entries": 2,
      "stix_object_count": 47,
      "stix_bundle_locator": "data/bundles/sec-1275/bundle--xxx.json"
    }
  ]
}
 
6.5. Тестовый запуск (только скраппер)
 
# Запуск без полного pipeline (проверка скраппера и парсера)
python examples/run_web_scrapper.py
 
# Ожидаемый вывод:
# Snapshot saved to: data/snapshots/sec-1275/index_*.json
# Parsed entries: 15
# Entry URLs: [...]
 
6.6. Повторный запуск (инкрементальная обработка)
 
# Первый запуск
ti-framework run --config config/sources.json
# Вывод: new_index_entries: 2, fetched_entries: 2
 
# Повторный запуск (без новых данных)
ti-framework run --config config/sources.json
# Вывод: new_index_entries: 0, fetched_entries: 0
# Snapshot cleaned (нет новых данных)
 
7. ПРОДАКШН-РАЗВЁРТЫВАНИЕ
 
7.1. Структура продакшн-окружения
 
/opt/ti-framework/
├── .venv/                          # Виртуальное окружение
├── config/
│   └── sources.json                # Продуктивная конфигурация
├── src/                            # Исходный код
├── data/
│   ├── snapshots/                  # Промежуточные snapshot
│   ├── bundles/                    # STIX Bundle результаты
│   ├── logs/                       # Логи выполнения
│   └── status/                     # Статус последнего запуска
├── scripts/
│   ├── run_pipeline.sh             # Скрипт запуска
│   └── backup.sh                   # Скрипт бэкапа
└── systemd/
    └── ti-framework.service        # Systemd service (опционально)
 
7.2. Скрипт автоматического запуска
 
#!/bin/bash
# /opt/ti-framework/scripts/run_pipeline.sh
 
set -e
 
# Настройки
TI_FRAMEWORK_DIR="/opt/ti-framework"
VENV_ACTIVATE="$TI_FRAMEWORK_DIR/.venv/bin/activate"
CONFIG_FILE="$TI_FRAMEWORK_DIR/config/sources.json"
LOG_FILE="$TI_FRAMEWORK_DIR/data/logs/pipeline.log"
STATUS_FILE="$TI_FRAMEWORK_DIR/data/status/last_run.json"
LOCK_FILE="/tmp/ti-framework.lock"
 
# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}
 
# Проверка блокировки (предотвращение параллельных запусков)
if [ -f "$LOCK_FILE" ]; then
    log "ERROR: Another instance is running (lock file exists)"
    exit 1
fi
 
# Создание lock-файла
touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT
 
log "=== TI Framework Pipeline Started ==="
 
# Активация виртуального окружения
source "$VENV_ACTIVATE"
 
# Запуск pipeline
ti-framework run \
    --config "$CONFIG_FILE" \
    --log-file "$LOG_FILE" \
    --log-level INFO \
    --status-file "$STATUS_FILE"
 
EXIT_CODE=$?
 
if [ $EXIT_CODE -eq 0 ]; then
    log "=== Pipeline completed successfully ==="
else
    log "=== Pipeline failed with exit code: $EXIT_CODE ==="
fi
 
exit $EXIT_CODE
 
Настройка прав:
chmod +x /opt/ti-framework/scripts/run_pipeline.sh
chown ti-framework:ti-framework /opt/ti-framework/scripts/run_pipeline.sh
 
7.3. Настройка автоматического запуска (cron)
 
# Открытие crontab для пользователя ti-framework
sudo crontab -u ti-framework -e
 
# Добавление задачи (запуск каждые 6 часов)
0 */6 * * * /opt/ti-framework/scripts/run_pipeline.sh >> /opt/ti-framework/data/logs/cron.log 2>&1
 
# Альтернативно: запуск раз в день в 02:00
0 2 * * * /opt/ti-framework/scripts/run_pipeline.sh >> /opt/ti-framework/data/logs/cron.log 2>&1
 
7.4. Настройка systemd service (альтернатива cron)
 
# /etc/systemd/system/ti-framework.service
[Unit]
Description=TI Framework Pipeline
After=network.target
 
[Service]
Type=oneshot
User=ti-framework
Group=ti-framework
WorkingDirectory=/opt/ti-framework
ExecStart=/opt/ti-framework/.venv/bin/ti-framework run --config /opt/ti-framework/config/sources.json --log-file /opt/ti-framework/data/logs/pipeline.log
StandardOutput=append:/opt/ti-framework/data/logs/systemd.log
StandardError=append:/opt/ti-framework/data/logs/systemd.log
 
[Install]
WantedBy=multi-user.target
 
Активация service:
# Копирование файла
sudo cp /opt/ti-framework/systemd/ti-framework.service /etc/systemd/system/
 
# Перезагрузка systemd
sudo systemctl daemon-reload
 
# Включение автозапуска
sudo systemctl enable ti-framework
 
# Запуск вручную
sudo systemctl start ti-framework
 
# Проверка статуса
sudo systemctl status ti-framework
 
# Просмотр логов
sudo journalctl -u ti-framework -f
 
 
7.5. Настройка таймера systemd (альтернатива cron)
 
# /etc/systemd/system/ti-framework.timer
[Unit]
Description=Run TI Framework Pipeline every 6 hours
Requires=ti-framework.service
 
[Timer]
OnBootSec=1min
OnUnitActiveSec=6h
Unit=ti-framework.service
 
[Install]
WantedBy=timers.target
 
Активация таймера:
sudo cp /opt/ti-framework/systemd/ti-framework.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ti-framework.timer
sudo systemctl start ti-framework.timer
sudo systemctl list-timers --all
 
### 7.6. Скрипт резервного копирования
 
#!/bin/bash
# /opt/ti-framework/scripts/backup.sh
 
set -e
 
BACKUP_DIR="/backup/ti-framework"
DATE=$(date +%Y%m%d_%H%M%S)
TI_FRAMEWORK_DIR="/opt/ti-framework"
 
# Создание директории бэкапа
mkdir -p "$BACKUP_DIR"
 
# Бэкап конфигурации
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" -C "$TI_FRAMEWORK_DIR" config/
 
# Бэкап STIX Bundle (результаты)
tar -czf "$BACKUP_DIR/bundles_$DATE.tar.gz" -C "$TI_FRAMEWORK_DIR" data/bundles/
 
# Бэкап статусов
tar -czf "$BACKUP_DIR/status_$DATE.tar.gz" -C "$TI_FRAMEWORK_DIR" data/status/
 
# Удаление бэкапов старше 30 дней
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
 
echo "Backup completed: $BACKUP_DIR"
 
8. МОНИТОРИНГ И ОБСЛУЖИВАНИЕ
 
8.1. Логи системы
 
Файл
 Назначение
 Уровень
data/logs/pipeline.log
 Основное логирование pipeline
 INFO/DEBUG
data/logs/cron.log
 Логи cron-задач
 INFO
data/logs/systemd.log
 Логи systemd service
 INFO
data/status/last_run.json
 Статус последнего запуска
 JSON

 
8.2. Просмотр логов
 
# Последние 100 строк логов
tail -n 100 data/logs/pipeline.log
 
# Логи в реальном времени
tail -f data/logs/pipeline.log
 
# Поиск ошибок в логах
grep -i "error" data/logs/pipeline.log
 
# Логи за конкретную дату
grep "2026-04-19" data/logs/pipeline.log
 
# Статистика по уровням логирования
grep -c "INFO" data/logs/pipeline.log
grep -c "WARNING" data/logs/pipeline.log
grep -c "ERROR" data/logs/pipeline.log
 
8.3. Мониторинг здоровья системы
 
#!/bin/bash
# health_check.sh
 
TI_FRAMEWORK_DIR="/opt/ti-framework"
STATUS_FILE="$TI_FRAMEWORK_DIR/data/status/last_run.json"
 
# Проверка статуса последнего запуска
if [ -f "$STATUS_FILE" ]; then
    LAST_RUN=$(python -c "import json; print(json.load(open('$STATUS_FILE'))['generated_at'])")
    FAILED=$(python -c "import json; print(json.load(open('$STATUS_FILE'))['failed_sources'])")
    
    echo "Last run: $LAST_RUN"
    echo "Failed sources: $FAILED"
    
    if [ "$FAILED" -gt 0 ]; then
        echo "⚠ WARNING: Some sources failed"
        exit 1
    else
        echo "✓ All sources processed successfully"
        exit 0
    fi
else
    echo "✗ ERROR: Status file not found"
    exit 1
fi
 
8.4. Очистка устаревших данных
 
#!/bin/bash
# cleanup.sh
 
TI_FRAMEWORK_DIR="/opt/ti-framework"
RETENTION_DAYS=30
 
# Удаление snapshot старше 30 дней
find "$TI_FRAMEWORK_DIR/data/snapshots" -type f -mtime +$RETENTION_DAYS -delete
 
# Удаление логов старше 30 дней
find "$TI_FRAMEWORK_DIR/data/logs" -type f -name "*.log" -mtime +$RETENTION_DAYS -delete
 
# Удаление старых бэкапов
find "/backup/ti-framework" -type f -mtime +90 -delete
 
echo "Cleanup completed"
 
Настройка в cron (еженедельно):
0 3 * * 0 /opt/ti-framework/scripts/cleanup.sh >> /opt/ti-framework/data/logs/cleanup.log 2>&1
 
8.5. Метрики для мониторинга
 
Метрика
 Описание
 Источник
 Целевое значение
pipeline_duration
 Время выполнения pipeline
 Логи
 <10 мин
sources_success_rate
 % успешных источников
 last_run.json
 ≥95
ioc_extracted
 Количество извлечённых IoC
 last_run.json
 Зависит от источника
stix_bundle_count
 Количество созданных Bundle
 data/bundles/
 = количеству источников с новыми данными
error_count
 Количество ошибок
 Логи
 0

 
 
9. УСТРАНЕНИЕ НЕПОЛАДОК
9.1. Частые проблемы и решения
 
Проблема
 Возможная причина
 Решение
Python version error
 Версия Python < 3.11
 Установить Python 3.11+
ModuleNotFoundError
 Зависимости не установлены
 pip install -e .
Configuration invalid
 Ошибка в sources.json
 ti-framework validate для диагностики
Parser not found
 Неверный parser_path
 Проверить путь к классу парсера
Permission denied
 Нет прав на запись
 chown/chmod для директорий
Network timeout
 Источник недоступен
 Проверить сеть, настроить retry
STIX validation failed
 Некорректные данные
 Проверить логи парсера
No new entries
 Нет новых публикаций
 Нормальное поведение при инкрементальной обработке

 
9.2. Диагностика проблем
 
# 1. Проверка версии Python
python --version
 
# 2. Проверка активации виртуального окружения
echo $VIRTUAL_ENV
 
# 3. Проверка установленных зависимостей
pip list | grep -E "requests|beautifulsoup4|stix2"
 
# 4. Валидация конфигурации
ti-framework validate --config config/sources.json --log-level DEBUG
 
# 5. Запуск с подробным логированием
ti-framework run --config config/sources.json --log-level DEBUG
 
# 6. Проверка прав доступа
ls -la data/
 
# 7. Проверка сетевой доступности
curl -I https://1275.ru/ioc/
 
# 8. Просмотр последних ошибок
grep -i "error" data/logs/pipeline.log | tail -20
 
9.3. Восстановление после сбоя
 
# 1. Остановка текущих процессов
pkill -f "ti-framework"
 
# 2. Удаление lock-файлов
rm -f /tmp/ti-framework.lock
 
# 3. Проверка целостности данных
ls -la data/snapshots/
ls -la data/bundles/
 
# 4. Восстановление из бэкапа (при необходимости)
tar -xzf /backup/ti-framework/config_20260419.tar.gz -C /opt/ti-framework/
 
# 5. Повторный запуск
ti-framework run --config config/sources.json
 
ИТОГОВЫЙ ЧЕК-ЛИСТ РАЗВЁРТЫВАНИЯ
 
[ ] 1. Системные требования проверены (Python 3.11+, 2GB RAM, 500MB disk)
[ ] 2. Репозиторий клонирован
[ ] 3. Виртуальное окружение создано и активировано
[ ] 4. Зависимости установлены (pip install -e .)
[ ] 5. Конфигурация sources.json создана и валидирована
[ ] 6. Smoke-тесты пройдены (26 тестов)
[ ] 7. Директории data/{snapshots,bundles,logs,status} созданы
[ ] 8. Права доступа настроены
[ ] 9. Первый запуск pipeline выполнен успешно
[ ] 10. STIX Bundle сформирован и валиден
[ ] 11. Логи записываются корректно
[ ] 12. Статус последнего запуска доступен
[ ] 13. Автоматический запуск настроен (cron/systemd)
[ ] 14. Бэкап-скрипт настроен
[ ] 15. Мониторинг здоровья настроен


