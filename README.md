# TI Framework

Модульный фреймворк для сбора и обработки Threat Intelligence (TI) данных из внешних источников публикаций по ИБ.

## О проекте

Проект решает задачу автоматизации сбора публикаций из внешних источников, извлечения индикаторов компрометации (IoC) и формирования результата в стандартизированном формате **STIX 2.1 Bundle**.

Система ориентирована на обработку неоднородных и слабоструктурированных источников: HTML-страниц, бюллетеней безопасности, блогов и технических публикаций.
Ключевая идея архитектуры — **модульный pipeline**, где каждый источник проходит последовательные этапы получения, препроцессинга, парсинга, сравнения состояний, извлечения новых публикаций и сборки итогового STIX bundle.

## Цели проекта

- сократить ручной труд при мониторинге внешних источников;
- автоматизировать извлечение IoC из публикаций;
- повысить качество данных за счёт базовой нормализации и типизации;
- упростить подключение новых источников без переписывания ядра;
- выдавать результат в стандартизированном формате для дальнейшей интеграции в системы ИБ.

## Архитектурный подход

В проекте используется **модульная конвейерная архитектура**.

Основные архитектурные компоненты:

- **PipelineRunner** — координация этапов обработки и управление жизненным циклом pipeline;
- **внутренний pipeline обработки** — преобразование сырых данных источника в структурированный набор IoC;
- **слой представления результата** — формирование STIX v2.1 Bundle.

### Основной pipeline

Для одного источника обработка проходит по шагам:

1. `WebScrapper` загружает индекс источника и сохраняет `index`-snapshot.
2. `Preprocessor` восстанавливает snapshot в `PreprocessedData`.
3. `Parser.parse_index()` возвращает `IndexEntry`.
4. `Differ` сравнивает текущий индекс с предыдущим snapshot.
5. Если новых записей нет, свежий `index`-snapshot удаляется и bundle не создаётся.
6. Если новые записи есть, `EntryFetcher` скачивает каждую публикацию как `entry`-snapshot.
7. `Parser.parse_entry()` извлекает `Entry` и IoC.
8. `Stix21BundleBuilder` собирает STIX 2.1 Bundle.
9. `FileSystemBundleStorage` сохраняет bundle в JSON.

## Интерфейсы и реализации

### Порты (`src/ti_framework/ports`)
В проекте выделены контракты для ключевых модулей pipeline:

- `Scrapper`
- `Preprocessor`
- `Parser`
- `Differ`
- `EntryFetcher`
- `StixBundleBuilder`
- `Storage`
- `BundleStorage`
- `HttpClient`
- `IOCFilter`

### Реализации (`src/ti_framework/infrastructure`)
Для MVP добавлены реализации:

- `WebScrapper`
- `Utf8SnapshotPreprocessor`
- `PreviousSnapshotDiffer`
- `WebEntryFetcher`
- `Stix21BundleBuilder`
- `FileSystemBundleStorage`
- `RequestsHttpClient`
- `RuleBasedIOCFilter`

Также в проекте присутствуют source-specific парсеры:

- `Sec1275Parser`
- `SecurelistParser`
- `ProofpointThreatInsightParser`

## STIX-слой

На текущем этапе каждая новая публикация превращается в `report` SDO, а каждый извлечённый IoC — в SCO подходящего типа:

- `ipv4` → `ipv4-addr`
- `ipv4_port` → `network-traffic` + вспомогательный `ipv4-addr`
- `domain`, `host names`, `onion domains` → `domain-name`
- `url` → `url`
- `md5`, `sha1`, `sha256` → `file` с `hashes`
- `tox id` → пользовательский SCO `x-ti-tox-id`
- неизвестные типы → пользовательский SCO `x-ti-observable`

`report.object_refs` содержит ссылки на связанные SCO из публикации.

## Нефункциональные свойства MVP

Архитектура проекта ориентирована на:

- **модульность** — каждый этап обработки выделен в отдельный компонент;
- **расширяемость** — новый источник подключается через новую реализацию и конфиг;
- **надёжность** — сбой одного источника не должен ломать остальной pipeline;
- **прослеживаемость** — сохраняются `source_name`, `source_url`, `collected_at`, а результат связан с публикацией;
- **совместимость** — результат формируется в формате **STIX v2.1 Bundle**;
- **наблюдаемость** — технические логи и отчёт по результатам обработки.

## Ограничения MVP

В текущую версию **не входят**:

- обогащение данных;
- MongoDB-хранилище;
- Consumer API;
- сложная маршрутизация;
- динамические источники с headless-рендерингом и anti-bot-защитой.

MVP ориентирован на **статичные HTML-источники**.

## Конфигурация источников

Список источников задаётся в `config/sources.json`.

Для источника указываются:

- `name`
- `index_url`
- `parser_path`
- `enabled`

Если новый источник использует уже существующий parser, достаточно изменить конфиг.
Если нужен новый parser, достаточно добавить новый класс и прописать его dotted path в конфиге.
## Тестирование
Проект использует **Pytest** для модульного тестирования, применяя многоуровневую стратегию: от изолированных юнит-тестов до сквозных E2E-сценариев. Мы активно используем мокирование (`unittest.mock`) для изоляции логики от внешних зависимостей (сеть, файловая система).
Тесты сгруппированы по функциональному назначению:

*   **Core Domain:** Проверка базовых моделей данных и валидации сущностей (`Snapshot`, `Entry`). *(Файлы: test_domain.py)*
*   **Configuration & CLI:** Тестирование загрузчиков конфигураций, а также проверка командной строки (валидация аргументов, статусы). *(Файлы: test_cli_*.*py, test_config.py)*
*   **Infrastructure Components:** Изолированное тестирование низкоуровневых компонентов — парсеров (`ProofpointThreatInsightParser`, `SecurelistParser`), хранилищ и базовой логики обработки данных. *(Файлы: test_infrastructure.py, test_*parser.py)*
*   **Ports & Abstractions:** Проверка контрактов между слоями через мокирование внешних интерфейсов (HTTP, etc.). *(Файл: test_ports.py)*
*   **Pipeline Logic (Integration):** Тестирование логического потока данных — как компоненты взаимодействуют друг с другом и обрабатывают данные в рамках одного сценария. *(Файлы: test_ioc_filter.*.*py, test_pipeline_resilience.py)*
*   **System Orchestration:** Проверка работы главного оркестратора (`PipelineRunner`) при разных входных условиях (успех/сбой). *(Файл: test_application.py)*
*   **End-to-End Scenarios (E2E):** Полный сквозной тест, имитирующий рабочий цикл от начала до конца с минимальным количеством моков. *(Файлы: test_e2e_stix_pipeline.py)*
*   **Smoke Tests:** Быстрая проверка работоспособности ядра системы при старте проекта (проверка импортов и инициализации). *(Файл: test_smoke.py)*

### Запуск всех тестов вместе
- `python run_all_tests.py`               Все тесты (всего 52)
### Запуск отдельного теста
- `python -m pytest tests/test_названиетеста.py --cov=ti_framework --cov-report=term-missing -v `
### Результаты тестирования
- [Результаты тестов](./tests/results/tests.pdf)
## Стек технологий

- **Python 3.11+**
- `requests`
- `beautifulsoup4`
- `stix2`
- `pytest` / `pytest-cov`
- `unittest.mock`
- JSON-конфиги
- GitHub
- VS Code


## Подготовка окружения

Перед запуском проекта необходимо создать виртуальное окружение и установить зависимости из `requirements.txt`.

```text
Linux / macOS
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

Windows PowerShell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

Windows cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
pip install -e .
```

## Запуск

После установки проекта как пакета (`pip install -e .`) доступны команды:

```bash
ti-framework validate --config config/sources.json
ti-framework run --config config/sources.json
ti-framework status
```

Если команда `ti-framework` недоступна, можно использовать запуск через Python:

```text
Linux / macOS
PYTHONPATH=./src python -m ti_framework.cli validate --config config/sources.json
PYTHONPATH=./src python -m ti_framework.cli run --config config/sources.json
PYTHONPATH=./src python -m ti_framework.cli status

Windows PowerShell
$env:PYTHONPATH="./src"
python -m ti_framework.cli validate --config config/sources.json
python -m ti_framework.cli run --config config/sources.json
python -m ti_framework.cli status

Windows cmd
set PYTHONPATH=./src
python -m ti_framework.cli validate --config config/sources.json
python -m ti_framework.cli run --config config/sources.json
python -m ti_framework.cli status
```

Во время работы framework формирует:

- snapshot-данные в `data/snapshots`
- STIX bundles в `data/bundles`
- статус последнего запуска в `data/status/last_run.json`
- лог выполнения pipeline в `data/logs/pipeline.log`
