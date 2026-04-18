"""Command-line interface for the TI framework."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ti_framework.config.loaders import load_source_configs
from ti_framework.infrastructure.parsers.parser_loader import load_parser
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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _run_validate_command(args.config, args.log_level)

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
