"""Run the end-to-end TI pipeline for configured sources."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ti_framework.application.pipeline_runner import PipelineRunner
from ti_framework.config.loaders import load_source_configs
from ti_framework.infrastructure.differs.previous_snapshot_differ import PreviousSnapshotDiffer
from ti_framework.infrastructure.fetchers.web_entry_fetcher import WebEntryFetcher
from ti_framework.infrastructure.http.requests_http_client import RequestsHttpClient
from ti_framework.infrastructure.parsers.parser_loader import load_parser
from ti_framework.infrastructure.preprocessors.utf8_snapshot_preprocessor import Utf8SnapshotPreprocessor
from ti_framework.infrastructure.scrappers.web_scrapper import WebScrapper
from ti_framework.infrastructure.storage.filesystem_snapshot_storage import FileSystemSnapshotStorage
from ti_framework.infrastructure.stix.filesystem_bundle_storage import FileSystemBundleStorage
from ti_framework.infrastructure.stix.stix21_bundle_builder import Stix21BundleBuilder


def main() -> None:
    sources_path = PROJECT_ROOT / "config" / "sources.json"
    snapshots_dir = PROJECT_ROOT / "data" / "snapshots"
    bundles_dir = PROJECT_ROOT / "data" / "bundles"

    storage = FileSystemSnapshotStorage(root_dir=snapshots_dir)
    bundle_storage = FileSystemBundleStorage(root_dir=bundles_dir)
    http_client = RequestsHttpClient()
    scrapper = WebScrapper(http_client=http_client, storage=storage)
    preprocessor = Utf8SnapshotPreprocessor(storage=storage)
    differ = PreviousSnapshotDiffer(storage=storage)
    entry_fetcher = WebEntryFetcher(scrapper=scrapper)
    stix_bundle_builder = Stix21BundleBuilder()

    runner = PipelineRunner(
        scrapper=scrapper,
        preprocessor=preprocessor,
        differ=differ,
        storage=storage,
        parser_loader=load_parser,
        entry_fetcher=entry_fetcher,
        stix_bundle_builder=stix_bundle_builder,
        bundle_storage=bundle_storage,
    )

    source_configs = load_source_configs(sources_path)
    results = runner.run_all(source_configs)

    for result in results:
        print(f"Source: {result.source_name}")
        print(f"  succeeded: {result.succeeded}")
        if not result.succeeded:
            print(f"  error: {result.error_message}")
            continue

        print(f"  index snapshot kept: {not result.snapshot_deleted}")
        print(f"  total index entries: {result.total_index_entries}")
        print(f"  new index entries: {result.new_index_entries}")
        print(f"  fetched entries: {len(result.fetched_entries)}")
        print(f"  parsed entries: {len(result.parsed_entries)}")
        if result.snapshot_locator:
            print(f"  index snapshot: {result.snapshot_locator}")
        if result.stix_bundle_locator:
            print(f"  STIX bundle: {result.stix_bundle_locator}")
            print(f"  STIX object count: {result.stix_object_count}")

        for entry in result.parsed_entries:
            print(f"    - {entry.title}")
            print(f"      IOC count: {len(entry.iocs)}")
            for ioc in entry.iocs[:10]:
                print(f"        * {ioc.kind}: {ioc.value}")
            if len(entry.iocs) > 10:
                print(f"        ... and {len(entry.iocs) - 10} more")


if __name__ == "__main__":
    main()
