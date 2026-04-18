from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from contextlib import redirect_stdout

from ti_framework.cli import main, validate_config


def test_validate_config_accepts_valid_config(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.json"
    config_path.write_text(
        json.dumps(
            [
                {
                    "name": "SEC-1275 IOC",
                    "index_url": "https://1275.ru/ioc/",
                    "parser_path": "ti_framework.infrastructure.parsers.sec1275_parser.Sec1275Parser",
                    "enabled": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    result = validate_config(config_path)

    assert result.is_valid is True
    assert result.total_sources == 1
    assert result.enabled_sources == 1
    assert result.issues == ()


def test_validate_command_reports_invalid_parser(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.json"
    config_path.write_text(
        json.dumps(
            [
                {
                    "name": "Broken Parser",
                    "index_url": "https://example.com/index",
                    "parser_path": "ti_framework.infrastructure.parsers.missing.MissingParser",
                }
            ]
        ),
        encoding="utf-8",
    )

    stdout = StringIO()
    with redirect_stdout(stdout):
        exit_code = main(["validate", "--config", str(config_path)])

    output = stdout.getvalue()
    assert exit_code == 1
    assert "Validation result: FAILED" in output
    assert "Invalid parser" in output


def test_validate_command_reports_invalid_source_url(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.json"
    config_path.write_text(
        json.dumps(
            [
                {
                    "name": "Bad URL",
                    "index_url": "not-a-url",
                    "parser_path": "ti_framework.infrastructure.parsers.sec1275_parser.Sec1275Parser",
                }
            ]
        ),
        encoding="utf-8",
    )

    stdout = StringIO()
    with redirect_stdout(stdout):
        exit_code = main(["validate", "--config", str(config_path)])

    output = stdout.getvalue()
    assert exit_code == 1
    assert "Validation result: FAILED" in output
    assert "Invalid source" in output


def test_validate_command_returns_zero_for_valid_config(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.json"
    config_path.write_text(
        json.dumps(
            [
                {
                    "name": "Proofpoint Threat Insight",
                    "index_url": "https://www.proofpoint.com/us/blog/threat-insight",
                    "parser_path": "ti_framework.infrastructure.parsers.proofpoint_threat_insight_parser.ProofpointThreatInsightParser",
                    "enabled": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    stdout = StringIO()
    with redirect_stdout(stdout):
        exit_code = main(["validate", "--config", str(config_path)])

    output = stdout.getvalue()
    assert exit_code == 0
    assert "Validation result: OK" in output
    assert "Total sources: 1" in output
    assert "Enabled sources: 1" in output
