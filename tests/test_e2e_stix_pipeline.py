from __future__ import annotations

import base64
import json
import tempfile
import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

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


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
ENTRY_SNAPSHOT_PATH = FIXTURES_DIR / "sec1275_entry_snapshot.json"
ENTRY_SNAPSHOT_PAYLOAD = json.loads(ENTRY_SNAPSHOT_PATH.read_text(encoding="utf-8"))
ENTRY_HTML = base64.b64decode(ENTRY_SNAPSHOT_PAYLOAD["data_base64"]).decode("utf-8")
ENTRY_URL = ENTRY_SNAPSHOT_PAYLOAD["source_url"]
SOURCE_NAME = ENTRY_SNAPSHOT_PAYLOAD["source_name"]
INDEX_URL = "https://1275.ru/ioc/"
INDEX_HTML = f"""
<html>
  <body>
    <main>
      <article>
        <h2><a href="{ENTRY_URL}">Новая группа программ-вымогателей Tengu</a></h2>
      </article>
    </main>
  </body>
</html>
""".encode("utf-8")


class FakeHttpClient:
    def __init__(self) -> None:
        self._responses = {
            INDEX_URL: HttpResponse(
                url=INDEX_URL,
                status_code=200,
                content=INDEX_HTML,
                encoding="utf-8",
                content_type="text/html; charset=utf-8",
            ),
            ENTRY_URL: HttpResponse(
                url=ENTRY_URL,
                status_code=200,
                content=ENTRY_HTML.encode("utf-8"),
                encoding="utf-8",
                content_type="text/html; charset=utf-8",
            ),
        }

    def get(self, url: str) -> HttpResponse:
        try:
            return self._responses[url]
        except KeyError as exc:
            raise AssertionError(f"Unexpected URL requested during test: {url}") from exc


class StixPipelineE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        root = Path(self._tmpdir.name)

        snapshot_storage = FileSystemSnapshotStorage(root_dir=root / "snapshots")
        bundle_storage = FileSystemBundleStorage(root_dir=root / "bundles")
        scrapper = WebScrapper(http_client=FakeHttpClient(), storage=snapshot_storage)
        preprocessor = Utf8SnapshotPreprocessor(storage=snapshot_storage)
        differ = PreviousSnapshotDiffer(storage=snapshot_storage)
        entry_fetcher = WebEntryFetcher(scrapper=scrapper)
        stix_bundle_builder = Stix21BundleBuilder()

        self._runner = PipelineRunner(
            scrapper=scrapper,
            preprocessor=preprocessor,
            differ=differ,
            storage=snapshot_storage,
            parser_loader=load_parser,
            entry_fetcher=entry_fetcher,
            stix_bundle_builder=stix_bundle_builder,
            bundle_storage=bundle_storage,
        )
        self._storage = snapshot_storage
        self._source_config = SourceConfig(
            name=SOURCE_NAME,
            index_url=INDEX_URL,
            parser_path="ti_framework.infrastructure.parsers.sec1275_parser.Sec1275Parser",
            enabled=True,
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_pipeline_builds_stix_bundle_on_first_run_and_skips_second_run(self) -> None:
        first_result = self._runner.run_source(self._source_config)

        self.assertEqual(first_result.new_index_entries, 1)
        self.assertFalse(first_result.snapshot_deleted)
        self.assertEqual(len(first_result.fetched_entries), 1)
        self.assertEqual(len(first_result.parsed_entries), 1)
        self.assertIsNotNone(first_result.stix_bundle_locator)
        self.assertGreater(first_result.stix_object_count, 0)

        parsed_entry = first_result.parsed_entries[0]
        self.assertEqual(parsed_entry.source_url, ENTRY_URL)
        self.assertGreater(len(parsed_entry.iocs), 0)

        bundle_path = Path(first_result.stix_bundle_locator or "")
        bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        objects = bundle_payload["objects"]
        object_types = {obj["type"] for obj in objects}

        self.assertIn("report", object_types)
        self.assertIn("identity", object_types)
        self.assertIn("ipv4-addr", object_types)
        self.assertIn("domain-name", object_types)
        self.assertIn("x-ti-tox-id", object_types)

        reports = [obj for obj in objects if obj["type"] == "report"]
        self.assertEqual(len(reports), 1)
        self.assertTrue(reports[0]["object_refs"])

        second_result = self._runner.run_source(self._source_config)
        self.assertEqual(second_result.new_index_entries, 0)
        self.assertTrue(second_result.snapshot_deleted)
        self.assertIsNone(second_result.stix_bundle_locator)
        self.assertEqual(second_result.stix_object_count, 0)

        index_snapshots = self._storage.list_snapshots(SOURCE_NAME, "index")
        self.assertEqual(len(index_snapshots), 1)


if __name__ == "__main__":
    unittest.main()
