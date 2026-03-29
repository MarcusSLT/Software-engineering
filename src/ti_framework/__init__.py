"""TI data collection framework."""

from ti_framework.config.loaders import load_source_configs
from ti_framework.config.models import SourceConfig
from ti_framework.domain.models import (
    Entry,
    IndexEntry,
    PreprocessedData,
    Snapshot,
    SnapshotHandle,
    Source,
)
from ti_framework.infrastructure.parsers.parser_loader import load_parser
from ti_framework.infrastructure.parsers.sec1275_parser import Sec1275Parser
from ti_framework.infrastructure.preprocessors.utf8_snapshot_preprocessor import (
    Utf8SnapshotPreprocessor,
)
from ti_framework.infrastructure.scrappers.web_scrapper import WebScrapper
from ti_framework.infrastructure.storage.filesystem_snapshot_storage import (
    FileSystemSnapshotStorage,
)
from ti_framework.ports.parser import Parser
from ti_framework.ports.preprocessor import Preprocessor
from ti_framework.ports.scrapper import Scrapper

__all__ = [
    "Entry",
    "IndexEntry",
    "PreprocessedData",
    "Snapshot",
    "SnapshotHandle",
    "Source",
    "SourceConfig",
    "Parser",
    "Preprocessor",
    "Scrapper",
    "WebScrapper",
    "Utf8SnapshotPreprocessor",
    "Sec1275Parser",
    "FileSystemSnapshotStorage",
    "load_parser",
    "load_source_configs",
]
