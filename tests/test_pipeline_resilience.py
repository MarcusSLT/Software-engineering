from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ti_framework.application.pipeline_runner import PipelineRunner
from ti_framework.config.models import SourceConfig
from ti_framework.infrastructure.differs.previous_snapshot_differ import PreviousSnapshotDiffer
from ti_framework.infrastructure.fetchers.web_entry_fetcher import WebEntryFetcher
from ti_framework.infrastructure.parsers.parser_loader import load_parser
from ti_framework.infrastructure.preprocessors.utf8_snapshot_preprocessor import Utf8SnapshotPreprocessor
from ti_framework.infrastructure.scrappers.web_scrapper import WebScrapper
from ti_framework.infrastructure.storage.filesystem_snapshot_storage import FileSystemSnapshotStorage
from ti_framework.infrastructure.stix.filesystem_bundle_storage import FileSystemBundleStorage
from ti_framework.infrastructure.stix.stix21_bundle_builder import Stix21BundleBuilder
from ti_framework.ports.http import HttpResponse


class FakeHttpClient:
    def get(self, url: str) -> HttpResponse:
        if "broken.example" in url:
            return HttpResponse(url=url, status_code=200, content=b"", encoding="utf-8", content_type="text/html")
        return HttpResponse(
            url=url,
            status_code=200,
            content=b"<html><body><main><article><h2><a href='https://1275.ru/ioc/test/'>Test IOC</a></h2></article></main></body></html>",
            encoding="utf-8",
            content_type="text/html",
        )


class PipelineResilienceTest(unittest.TestCase):
    def test_failed_source_does_not_stop_other_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot_storage = FileSystemSnapshotStorage(root_dir=root / "snapshots")
            bundle_storage = FileSystemBundleStorage(root_dir=root / "bundles")
            scrapper = WebScrapper(http_client=FakeHttpClient(), storage=snapshot_storage)
            preprocessor = Utf8SnapshotPreprocessor(storage=snapshot_storage)
            differ = PreviousSnapshotDiffer(storage=snapshot_storage)
            entry_fetcher = WebEntryFetcher(scrapper=scrapper)
            runner = PipelineRunner(
                scrapper=scrapper,
                preprocessor=preprocessor,
                differ=differ,
                storage=snapshot_storage,
                parser_loader=load_parser,
                entry_fetcher=entry_fetcher,
                stix_bundle_builder=Stix21BundleBuilder(),
                bundle_storage=bundle_storage,
            )
            results = runner.run_all([
                SourceConfig(
                    name="Broken",
                    index_url="https://broken.example/all/",
                    parser_path="ti_framework.infrastructure.parsers.securelist_parser.SecurelistParser",
                ),
                SourceConfig(
                    name="SEC-1275 IOC",
                    index_url="https://1275.ru/ioc/",
                    parser_path="ti_framework.infrastructure.parsers.sec1275_parser.Sec1275Parser",
                ),
            ])
            self.assertEqual(len(results), 2)
            self.assertFalse(results[0].succeeded)
            self.assertTrue(results[1].succeeded)


if __name__ == "__main__":
    unittest.main()
