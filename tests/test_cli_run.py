from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from ti_framework.application.pipeline_runner import PipelineRunResult
from ti_framework.cli import main


class FakeRunner:
    def __init__(self, results: list[PipelineRunResult]) -> None:
        self._results = results

    def run_all(self, source_configs):  # noqa: ANN001
        return list(self._results)


def _write_valid_config(path: Path) -> None:
    path.write_text(
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


def test_run_command_prints_successful_result(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "sources.json"
    _write_valid_config(config_path)

    fake_results = [
        PipelineRunResult(
            source_name="SEC-1275 IOC",
            source_url="https://1275.ru/ioc/",
            snapshot_locator="/tmp/index.snapshot.json",
            snapshot_deleted=False,
            total_index_entries=3,
            new_index_entries=1,
            new_entries=(),
            fetched_entries=(),
            parsed_entries=(),
            stix_bundle_locator="/tmp/bundle.json",
            stix_object_count=7,
            succeeded=True,
            error_message=None,
        )
    ]

    monkeypatch.setattr(
        "ti_framework.cli.build_pipeline_runner",
        lambda **kwargs: FakeRunner(fake_results),
    )

    stdout = StringIO()
    with redirect_stdout(stdout):
        exit_code = main([
            "run",
            "--config",
            str(config_path),
            "--snapshots-dir",
            str(tmp_path / "snapshots"),
            "--bundles-dir",
            str(tmp_path / "bundles"),
            "--log-file",
            str(tmp_path / "pipeline.log"),
        ])

    output = stdout.getvalue()
    assert exit_code == 0
    assert "Source: SEC-1275 IOC" in output
    assert "succeeded: True" in output
    assert "Completed sources: 1" in output
    assert "Failed sources: 0" in output



def test_run_command_returns_nonzero_when_any_source_failed(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "sources.json"
    _write_valid_config(config_path)

    fake_results = [
        PipelineRunResult(
            source_name="Broken Source",
            source_url="https://example.com/",
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
            error_message="network error",
        )
    ]

    monkeypatch.setattr(
        "ti_framework.cli.build_pipeline_runner",
        lambda **kwargs: FakeRunner(fake_results),
    )

    stdout = StringIO()
    with redirect_stdout(stdout):
        exit_code = main([
            "run",
            "--config",
            str(config_path),
        ])

    output = stdout.getvalue()
    assert exit_code == 1
    assert "Source: Broken Source" in output
    assert "succeeded: False" in output
    assert "error: network error" in output
    assert "Failed sources: 1" in output



def test_run_command_aborts_on_invalid_config(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.json"
    config_path.write_text(
        json.dumps(
            [
                {
                    "name": "Broken Parser",
                    "index_url": "https://example.com/",
                    "parser_path": "ti_framework.infrastructure.parsers.missing.MissingParser",
                }
            ]
        ),
        encoding="utf-8",
    )

    stdout = StringIO()
    with redirect_stdout(stdout):
        exit_code = main(["run", "--config", str(config_path)])

    output = stdout.getvalue()
    assert exit_code == 1
    assert "Run aborted: configuration is invalid" in output
    assert "Invalid parser" in output
