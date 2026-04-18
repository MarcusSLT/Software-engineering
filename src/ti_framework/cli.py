"""Command-line interface for the TI framework."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ti_framework.application.pipeline_runner import PipelineRunner, PipelineRunResult
from ti_framework.config.loaders import load_source_configs
from ti_framework.infrastructure.differs.previous_snapshot_differ import PreviousSnapshotDiffer
from ti_framework.infrastructure.fetchers.web_entry_fetcher import WebEntryFetcher
from ti_framework.infrastructure.filters.invalid_domain_rule import DropInvalidDomainRule
from ti_framework.infrastructure.filters.internal_url_rule import DropInternalUrlRule
from ti_framework.infrastructure.filters.rule_based_ioc_filter import RuleBasedIOCFilter
from ti_framework.infrastructure.filters.special_purpose_ipv4_rule import DropSpecialPurposeIPv4Rule
from ti_framework.infrastructure.http.requests_http_client import RequestsHttpClient
from ti_framework.infrastructure.parsers.parser_loader import load_parser
from ti_framework.infrastructure.preprocessors.utf8_snapshot_preprocessor import Utf8SnapshotPreprocessor
from ti_framework.infrastructure.scrappers.web_scrapper import WebScrapper
from ti_framework.infrastructure.storage.filesystem_snapshot_storage import FileSystemSnapshotStorage
from ti_framework.infrastructure.stix.filesystem_bundle_storage import FileSystemBundleStorage
from ti_framework.infrastructure.stix.stix21_bundle_builder import Stix21BundleBuilder
from ti_framework.logging_utils import configure_framework_logging


@dataclass(frozen=True, slots=True)
class ValidateConfigResult:
    """Result of validating a source configuration file."""

    config_path: Path
    total_sources: int
    enabled_sources: int
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.issues


def validate_config(config_path: str | Path) -> ValidateConfigResult:
    """Validate source configuration structure and parser availability."""

    path = Path(config_path)
    issues: list[str] = []

    try:
        source_configs = load_source_configs(path)
    except Exception as exc:  # noqa: BLE001 - CLI should report any validation failure cleanly
        return ValidateConfigResult(
            config_path=path,
            total_sources=0,
            enabled_sources=0,
            issues=(f"Failed to load config: {exc}",),
        )

    for index, source_config in enumerate(source_configs, start=1):
        source_label = f"source #{index} ({source_config.name})"

        try:
            source_config.to_source()
        except Exception as exc:  # noqa: BLE001 - report invalid source declaration
            issues.append(f"Invalid {source_label}: {exc}")

        try:
            load_parser(source_config.parser_path)
        except Exception as exc:  # noqa: BLE001 - report parser import/typing problems
            issues.append(
                f"Invalid parser for {source_label}: {source_config.parser_path!r} ({exc})"
            )

    return ValidateConfigResult(
        config_path=path,
        total_sources=len(source_configs),
        enabled_sources=sum(1 for config in source_configs if config.enabled),
        issues=tuple(issues),
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="ti-framework",
        description="Threat intelligence collection and processing framework",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate source configuration without running the pipeline",
    )
    validate_parser.add_argument(
        "--config",
        default="config/sources.json",
        help="Path to source configuration JSON file",
    )
    validate_parser.add_argument(
        "--log-level",
        default="WARNING",
        help="Logging level for the CLI command",
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Run the TI pipeline for enabled sources from a configuration file",
    )
    run_parser.add_argument(
        "--config",
        default="config/sources.json",
        help="Path to source configuration JSON file",
    )
    run_parser.add_argument(
        "--snapshots-dir",
        default="data/snapshots",
        help="Directory for stored snapshots",
    )
    run_parser.add_argument(
        "--bundles-dir",
        default="data/bundles",
        help="Directory for generated STIX bundles",
    )
    run_parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level for the pipeline run",
    )
    run_parser.add_argument(
        "--log-file",
        default="data/logs/pipeline.log",
        help="Optional path to a log file",
    )

    return parser


def _run_validate_command(config_path: str | Path, log_level: str | int) -> int:
    configure_framework_logging(log_level)
    result = validate_config(config_path)

    print(f"Configuration: {result.config_path}")
    print(f"Total sources: {result.total_sources}")
    print(f"Enabled sources: {result.enabled_sources}")

    if result.is_valid:
        print("Validation result: OK")
        return 0

    print("Validation result: FAILED")
    for issue in result.issues:
        print(f" - {issue}")
    return 1


def build_pipeline_runner(
    *,
    snapshots_dir: str | Path,
    bundles_dir: str | Path,
    log_level: str | int,
    log_file: str | Path | None,
) -> PipelineRunner:
    storage = FileSystemSnapshotStorage(root_dir=snapshots_dir)
    bundle_storage = FileSystemBundleStorage(root_dir=bundles_dir)
    http_client = RequestsHttpClient()
    scrapper = WebScrapper(http_client=http_client, storage=storage)
    preprocessor = Utf8SnapshotPreprocessor(storage=storage)
    differ = PreviousSnapshotDiffer(storage=storage)
    entry_fetcher = WebEntryFetcher(scrapper=scrapper)
    stix_bundle_builder = Stix21BundleBuilder()
    ioc_filter = RuleBasedIOCFilter([
        DropSpecialPurposeIPv4Rule(),
        DropInvalidDomainRule(),
        DropInternalUrlRule(),
    ])

    return PipelineRunner(
        scrapper=scrapper,
        preprocessor=preprocessor,
        differ=differ,
        storage=storage,
        parser_loader=load_parser,
        entry_fetcher=entry_fetcher,
        ioc_filter=ioc_filter,
        stix_bundle_builder=stix_bundle_builder,
        bundle_storage=bundle_storage,
        log_level=log_level,
        log_file=None if log_file is None else str(log_file),
    )


def _print_run_result(result: PipelineRunResult) -> None:
    print(f"Source: {result.source_name}")
    print(f"  succeeded: {result.succeeded}")
    if not result.succeeded:
        print(f"  error: {result.error_message}")
        return

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


def _run_run_command(
    *,
    config_path: str | Path,
    snapshots_dir: str | Path,
    bundles_dir: str | Path,
    log_level: str | int,
    log_file: str | Path | None,
) -> int:
    validate_result = validate_config(config_path)
    if not validate_result.is_valid:
        print(f"Configuration: {validate_result.config_path}")
        print("Run aborted: configuration is invalid")
        for issue in validate_result.issues:
            print(f" - {issue}")
        return 1

    runner = build_pipeline_runner(
        snapshots_dir=snapshots_dir,
        bundles_dir=bundles_dir,
        log_level=log_level,
        log_file=log_file,
    )
    source_configs = load_source_configs(config_path)
    results = runner.run_all(source_configs)

    for result in results:
        _print_run_result(result)

    failed_runs = sum(1 for result in results if not result.succeeded)
    print(f"Completed sources: {len(results)}")
    print(f"Failed sources: {failed_runs}")
    return 0 if failed_runs == 0 else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _run_validate_command(args.config, args.log_level)

    if args.command == "run":
        return _run_run_command(
            config_path=args.config,
            snapshots_dir=args.snapshots_dir,
            bundles_dir=args.bundles_dir,
            log_level=args.log_level,
            log_file=args.log_file,
        )

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
