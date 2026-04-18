from __future__ import annotations

import tempfile
from pathlib import Path

from stix2 import parse as stix_parse
from stix2.v21 import Bundle

from ti_framework.application.pipeline_runner import PipelineRunner
from ti_framework.config.models import SourceConfig
from ti_framework.domain.models import Entry, IOC, IndexEntry
from ti_framework.infrastructure.differs.previous_snapshot_differ import PreviousSnapshotDiffer
from ti_framework.infrastructure.fetchers.web_entry_fetcher import WebEntryFetcher
from ti_framework.infrastructure.filters.invalid_domain_rule import DropInvalidDomainRule
from ti_framework.infrastructure.filters.internal_url_rule import DropInternalUrlRule
from ti_framework.infrastructure.filters.rule_based_ioc_filter import RuleBasedIOCFilter
from ti_framework.infrastructure.filters.special_purpose_ipv4_rule import DropSpecialPurposeIPv4Rule
from ti_framework.infrastructure.preprocessors.utf8_snapshot_preprocessor import Utf8SnapshotPreprocessor
from ti_framework.infrastructure.scrappers.web_scrapper import WebScrapper
from ti_framework.infrastructure.storage.filesystem_snapshot_storage import FileSystemSnapshotStorage
from ti_framework.infrastructure.stix.filesystem_bundle_storage import FileSystemBundleStorage
from ti_framework.infrastructure.stix.stix21_bundle_builder import Stix21BundleBuilder
from ti_framework.ports.http import HttpResponse


INDEX_URL = "https://example.org/index"
ENTRY_URL = "https://example.org/post-1"


class FakeHttpClient:
    def __init__(self) -> None:
        self._responses = {
            INDEX_URL: HttpResponse(
                url=INDEX_URL,
                status_code=200,
                content=f'<html><body><a href="{ENTRY_URL}">post</a></body></html>'.encode(),
                encoding="utf-8",
                content_type="text/html; charset=utf-8",
            ),
            ENTRY_URL: HttpResponse(
                url=ENTRY_URL,
                status_code=200,
                content=b"<html><body>entry</body></html>",
                encoding="utf-8",
                content_type="text/html; charset=utf-8",
            ),
        }

    def get(self, url: str) -> HttpResponse:
        return self._responses[url]


class FakeParser:
    def parse_index(self, data):
        return [
            IndexEntry(
                title="Post 1",
                publication_url=ENTRY_URL,
                source_name=data.source_name,
                index_source_url=data.source_url,
                indexed_at=data.collected_at,
            )
        ]

    def parse_entry(self, data, index_entry):
        return Entry(
            title=index_entry.title,
            content="entry body",
            source_url=index_entry.publication_url,
            source_name=index_entry.source_name,
            collected_at=data.collected_at,
            iocs=(
                IOC("ipv4", "127.0.0.1"),
                IOC("ipv4", "8.8.8.8"),
                IOC("ipv4_port", "192.168.1.10:443"),
                IOC("domain", "evil.example"),
                IOC("domain", "corp.local"),
                IOC("url", "https://evil.example/dropper"),
                IOC("url", "http://localhost/admin"),
            ),
        )



def test_pipeline_applies_all_ioc_quality_filters_before_stix_bundle_build() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        storage = FileSystemSnapshotStorage(root / "snapshots")
        bundle_storage = FileSystemBundleStorage(root / "bundles")
        scrapper = WebScrapper(http_client=FakeHttpClient(), storage=storage)
        preprocessor = Utf8SnapshotPreprocessor(storage=storage)
        differ = PreviousSnapshotDiffer(storage=storage)
        entry_fetcher = WebEntryFetcher(scrapper=scrapper)
        runner = PipelineRunner(
            scrapper=scrapper,
            preprocessor=preprocessor,
            differ=differ,
            storage=storage,
            parser_loader=lambda _: FakeParser(),
            entry_fetcher=entry_fetcher,
            ioc_filter=RuleBasedIOCFilter([
                DropSpecialPurposeIPv4Rule(),
                DropInvalidDomainRule(),
                DropInternalUrlRule(),
            ]),
            stix_bundle_builder=Stix21BundleBuilder(),
            bundle_storage=bundle_storage,
        )

        result = runner.run_source(
            SourceConfig(
                name="Filter Test Source",
                index_url=INDEX_URL,
                parser_path="ignored.for.test",
                enabled=True,
            )
        )

        assert result.succeeded is True
        assert len(result.parsed_entries) == 1
        assert result.parsed_entries[0].iocs == (
            IOC("ipv4", "8.8.8.8"),
            IOC("domain", "evil.example"),
            IOC("url", "https://evil.example/dropper"),
        )
        assert result.stix_bundle_locator is not None

        bundle_path = Path(result.stix_bundle_locator)
        bundle = stix_parse(bundle_path.read_text(encoding="utf-8"), allow_custom=True)
        assert isinstance(bundle, Bundle)

        observable_values = []
        for obj in bundle.objects:
            if obj.type == "ipv4-addr":
                observable_values.append(obj.value)
            if obj.type == "domain-name":
                observable_values.append(obj.value)
            if obj.type == "url":
                observable_values.append(obj.value)

        assert "8.8.8.8" in observable_values
        assert "evil.example" in observable_values
        assert "https://evil.example/dropper" in observable_values
        assert "127.0.0.1" not in observable_values
        assert "192.168.1.10" not in observable_values
        assert "corp.local" not in observable_values
        assert "http://localhost/admin" not in observable_values
