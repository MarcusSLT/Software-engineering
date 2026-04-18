"""High-level pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable, Iterable

from ti_framework.config.models import SourceConfig
from ti_framework.domain.models import BundleHandle, Entry, FetchedEntry, IndexEntry, SnapshotHandle, Source
from ti_framework.logging_utils import configure_framework_logging
from ti_framework.ports.bundle_storage import BundleStorage
from ti_framework.ports.differ import Differ
from ti_framework.ports.entry_fetcher import EntryFetcher
from ti_framework.ports.ioc_filter import IOCFilter
from ti_framework.ports.parser import Parser
from ti_framework.ports.preprocessor import Preprocessor
from ti_framework.ports.scrapper import Scrapper
from ti_framework.ports.storage import SnapshotStorage
from ti_framework.ports.stix_bundle_builder import StixBundleBuilder

logger = logging.getLogger(__name__)


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
    succeeded: bool = True
    error_message: str | None = None


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
        ioc_filter: IOCFilter | None = None,
        stix_bundle_builder: StixBundleBuilder | None = None,
        bundle_storage: BundleStorage | None = None,
        log_level: int | str = "WARNING",
    ) -> None:
        configure_framework_logging(log_level)
        logger.debug("Initializing PipelineRunner with log_level=%r", log_level)
        self._scrapper = scrapper
        self._preprocessor = preprocessor
        self._differ = differ
        self._storage = storage
        self._parser_loader = parser_loader
        self._entry_fetcher = entry_fetcher
        self._ioc_filter = ioc_filter
        self._stix_bundle_builder = stix_bundle_builder
        self._bundle_storage = bundle_storage

    def run_source(self, source_config: SourceConfig) -> PipelineRunResult:
        source = source_config.to_source()
        logger.info("Starting pipeline for source '%s' (%s)", source.name, source.index_url)
        try:
            parser = self._parser_loader(source_config.parser_path)
            logger.debug("Loaded parser %s for source '%s'", source_config.parser_path, source.name)
            snapshot_handle = self._save_index_snapshot(source)
            logger.info("Saved index snapshot for source '%s': %s", source.name, snapshot_handle.locator)
            preprocessed_index = self._preprocessor.preprocess(snapshot_handle)
            index_entries = parser.parse_index(preprocessed_index)
            logger.info("Parsed %d index entries for source '%s'", len(index_entries), source.name)
            new_entries = self._differ.diff(
                current_snapshot_handle=snapshot_handle,
                current_entries=index_entries,
                parser=parser,
                preprocessor=self._preprocessor,
            )
            logger.info("Differ detected %d new entries for source '%s'", len(new_entries), source.name)

            if self._should_drop_fresh_snapshot(source.name, new_entries):
                logger.info(
                    "No new entries for source '%s'; deleting fresh index snapshot %s",
                    source.name,
                    snapshot_handle.locator,
                )
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
            logger.info(
                "Fetched %d entry snapshots and parsed %d entries for source '%s'",
                len(fetched_entries),
                len(parsed_entries),
                source.name,
            )
            bundle_handle, stix_object_count = self._build_and_save_bundle(source.name, parsed_entries)
            if bundle_handle is None:
                logger.info("No STIX bundle created for source '%s'", source.name)
            else:
                logger.info(
                    "Saved STIX bundle for source '%s': %s (%d objects)",
                    source.name,
                    bundle_handle.locator,
                    stix_object_count,
                )

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
        except Exception as exc:  # noqa: BLE001 - isolate source failures from one another
            logger.exception("Pipeline failed for source '%s'", source.name)
            return PipelineRunResult(
                source_name=source.name,
                source_url=source.index_url,
                snapshot_locator=None,
                snapshot_deleted=False,
                total_index_entries=0,
                new_index_entries=0,
                new_entries=(),
                fetched_entries=(),
                parsed_entries=(),
                stix_bundle_locator=None,
                stix_object_count=0,
                succeeded=False,
                error_message=str(exc),
            )

    def run_all(self, source_configs: Iterable[SourceConfig]) -> list[PipelineRunResult]:
        enabled_sources = [config for config in source_configs if config.enabled]
        logger.info("Starting pipeline for %d enabled sources", len(enabled_sources))
        results = [self.run_source(config) for config in enabled_sources]
        succeeded = sum(1 for result in results if result.succeeded)
        logger.info(
            "Completed pipeline for %d sources: %d succeeded, %d failed",
            len(results),
            succeeded,
            len(results) - succeeded,
        )
        return results

    def _save_index_snapshot(self, source: Source) -> SnapshotHandle:
        logger.debug("Fetching index snapshot for source '%s'", source.name)
        snapshot = self._scrapper.get_snapshot(source)
        return self._scrapper.save_snapshot(snapshot)

    def _should_drop_fresh_snapshot(self, source_name: str, new_entries: list[IndexEntry]) -> bool:
        if new_entries:
            return False
        return len(self._storage.list_snapshots(source_name, "index")) > 1

    def _fetch_and_parse_new_entries(self, parser: Parser, new_entries: list[IndexEntry]) -> tuple[list[FetchedEntry], list[Entry]]:
        if not new_entries or self._entry_fetcher is None:
            logger.debug("Skipping entry fetch stage because there are no new entries or no fetcher")
            return [], []

        logger.info("Fetching %d new publication pages", len(new_entries))
        fetched_entries = self._entry_fetcher.fetch(new_entries)
        parsed_entries: list[Entry] = []
        for item in fetched_entries:
            try:
                logger.debug("Parsing entry snapshot for %s", item.index_entry.publication_url)
                parsed_entry = parser.parse_entry(self._preprocessor.preprocess(item.snapshot_handle), item.index_entry)
                if self._ioc_filter is not None:
                    before_count = len(parsed_entry.iocs)
                    parsed_entry = self._ioc_filter.filter_entry(parsed_entry)
                    logger.debug(
                        "Filtered IOC set for %s: %d -> %d",
                        item.index_entry.publication_url,
                        before_count,
                        len(parsed_entry.iocs),
                    )
                parsed_entries.append(parsed_entry)
            except Exception:  # noqa: BLE001 - one broken entry must not stop the source
                logger.exception("Failed to parse entry page for %s", item.index_entry.publication_url)
                continue
        return fetched_entries, parsed_entries

    def _build_and_save_bundle(self, source_name: str, parsed_entries: list[Entry]) -> tuple[BundleHandle | None, int]:
        if not parsed_entries or self._stix_bundle_builder is None or self._bundle_storage is None:
            logger.debug("Skipping STIX build for source '%s' because prerequisites are missing", source_name)
            return None, 0

        logger.info("Building STIX bundle for source '%s' from %d parsed entries", source_name, len(parsed_entries))
        bundle = self._stix_bundle_builder.build(parsed_entries)
        if bundle is None:
            return None, 0

        handle = self._bundle_storage.save(bundle, source_name=source_name)
        return handle, len(bundle.objects)
