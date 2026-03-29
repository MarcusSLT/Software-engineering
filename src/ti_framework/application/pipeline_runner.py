"""High-level pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from ti_framework.config.models import SourceConfig
from ti_framework.domain.models import BundleHandle, Entry, FetchedEntry, IndexEntry, SnapshotHandle, Source
from ti_framework.ports.bundle_storage import BundleStorage
from ti_framework.ports.differ import Differ
from ti_framework.ports.entry_fetcher import EntryFetcher
from ti_framework.ports.parser import Parser
from ti_framework.ports.preprocessor import Preprocessor
from ti_framework.ports.scrapper import Scrapper
from ti_framework.ports.storage import SnapshotStorage
from ti_framework.ports.stix_bundle_builder import StixBundleBuilder


@dataclass(frozen=True, slots=True)
class PipelineRunResult:
    """Outcome of processing one source index snapshot."""

    source_name: str
    source_url: str
    snapshot_locator: str | None
    snapshot_deleted: bool
    total_index_entries: int
    new_index_entries: int
    new_entries: tuple[IndexEntry, ...]
    fetched_entries: tuple[FetchedEntry, ...]
    parsed_entries: tuple[Entry, ...]
    stix_bundle_locator: str | None
    stix_object_count: int


class PipelineRunner:
    """Run the index -> entry -> STIX pipeline for one or many sources."""

    def __init__(
        self,
        *,
        scrapper: Scrapper,
        preprocessor: Preprocessor,
        differ: Differ,
        storage: SnapshotStorage,
        parser_loader: Callable[[str], Parser],
        entry_fetcher: EntryFetcher | None = None,
        stix_bundle_builder: StixBundleBuilder | None = None,
        bundle_storage: BundleStorage | None = None,
    ) -> None:
        self._scrapper = scrapper
        self._preprocessor = preprocessor
        self._differ = differ
        self._storage = storage
        self._parser_loader = parser_loader
        self._entry_fetcher = entry_fetcher
        self._stix_bundle_builder = stix_bundle_builder
        self._bundle_storage = bundle_storage

    def run_source(self, source_config: SourceConfig) -> PipelineRunResult:
        parser = self._parser_loader(source_config.parser_path)
        source = source_config.to_source()

        snapshot_handle = self._save_index_snapshot(source)
        index_entries = parser.parse_index(self._preprocessor.preprocess(snapshot_handle))
        new_entries = self._differ.diff(
            current_snapshot_handle=snapshot_handle,
            current_entries=index_entries,
            parser=parser,
            preprocessor=self._preprocessor,
        )

        if self._should_drop_fresh_snapshot(source.name, new_entries):
            self._storage.delete(snapshot_handle)
            return PipelineRunResult(
                source_name=source.name,
                source_url=source.index_url,
                snapshot_locator=None,
                snapshot_deleted=True,
                total_index_entries=len(index_entries),
                new_index_entries=0,
                new_entries=(),
                fetched_entries=(),
                parsed_entries=(),
                stix_bundle_locator=None,
                stix_object_count=0,
            )

        fetched_entries, parsed_entries = self._fetch_and_parse_new_entries(parser, new_entries)
        bundle_handle, stix_object_count = self._build_and_save_bundle(source.name, parsed_entries)

        return PipelineRunResult(
            source_name=source.name,
            source_url=source.index_url,
            snapshot_locator=snapshot_handle.locator,
            snapshot_deleted=False,
            total_index_entries=len(index_entries),
            new_index_entries=len(new_entries),
            new_entries=tuple(new_entries),
            fetched_entries=tuple(fetched_entries),
            parsed_entries=tuple(parsed_entries),
            stix_bundle_locator=None if bundle_handle is None else bundle_handle.locator,
            stix_object_count=stix_object_count,
        )

    def run_all(self, source_configs: Iterable[SourceConfig]) -> list[PipelineRunResult]:
        return [self.run_source(config) for config in source_configs if config.enabled]

    def _save_index_snapshot(self, source: Source) -> SnapshotHandle:
        snapshot = self._scrapper.get_snapshot(source)
        return self._scrapper.save_snapshot(snapshot)

    def _should_drop_fresh_snapshot(self, source_name: str, new_entries: list[IndexEntry]) -> bool:
        if new_entries:
            return False
        return len(self._storage.list_snapshots(source_name, "index")) > 1

    def _fetch_and_parse_new_entries(self, parser: Parser, new_entries: list[IndexEntry]) -> tuple[list[FetchedEntry], list[Entry]]:
        if not new_entries or self._entry_fetcher is None:
            return [], []

        fetched_entries = self._entry_fetcher.fetch(new_entries)
        parsed_entries = [
            parser.parse_entry(self._preprocessor.preprocess(item.snapshot_handle), item.index_entry)
            for item in fetched_entries
        ]
        return fetched_entries, parsed_entries

    def _build_and_save_bundle(self, source_name: str, parsed_entries: list[Entry]) -> tuple[BundleHandle | None, int]:
        if not parsed_entries or self._stix_bundle_builder is None or self._bundle_storage is None:
            return None, 0

        bundle = self._stix_bundle_builder.build(parsed_entries)
        if bundle is None:
            return None, 0

        handle = self._bundle_storage.save(bundle, source_name=source_name)
        return handle, len(bundle.objects)
