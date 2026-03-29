"""Minimal example that scrapes one configured source and parses its index."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ti_framework.config.loaders import load_source_configs
from ti_framework.infrastructure.http.requests_http_client import RequestsHttpClient
from ti_framework.infrastructure.parsers.parser_loader import load_parser
from ti_framework.infrastructure.preprocessors.utf8_snapshot_preprocessor import Utf8SnapshotPreprocessor
from ti_framework.infrastructure.scrappers.web_scrapper import WebScrapper
from ti_framework.infrastructure.storage.filesystem_snapshot_storage import FileSystemSnapshotStorage


def main() -> None:
    sources_path = PROJECT_ROOT / "config" / "sources.json"
    snapshots_dir = PROJECT_ROOT / "data" / "snapshots"

    source_config = load_source_configs(sources_path)[0]
    storage = FileSystemSnapshotStorage(root_dir=snapshots_dir)
    scrapper = WebScrapper(
        http_client=RequestsHttpClient(),
        storage=storage,
    )
    preprocessor = Utf8SnapshotPreprocessor(storage=storage)
    parser = load_parser(source_config.parser_path)

    snapshot = scrapper.get_snapshot(source_config.to_source())
    handle = scrapper.save_snapshot(snapshot)
    prepared = preprocessor.preprocess(handle)
    entries = parser.parse_index(prepared)

    print(f"snapshot saved to: {handle.locator}")
    print(f"snapshot kind: {prepared.snapshot_kind}")
    print(f"parsed index entries: {len(entries)}")
    for entry in entries[:5]:
        print(f"- {entry.title} -> {entry.publication_url}")


if __name__ == "__main__":
    main()
