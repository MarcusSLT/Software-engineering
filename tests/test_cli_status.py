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


def test_run_command_writes_status_file_and_status_reads_it(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "sources.json"
    status_path = tmp_path / "status" / "last_run.json"
    _write_valid_config(config_path)

    fake_results = [
        PipelineRunResult(
            source_name="SEC-1275 IOC",
            source_url="https://1275.ru/ioc/",
            snapshot_locator=str(tmp_path / "index.snapshot.json"),
            snapshot_deleted=False,
            total_index_entries=4,
            new_index_entries=2,
            new_entries=(),
            fetched_entries=(),
            parsed_entries=(),
            stix_bundle_locator=str(tmp_path / "bundle.json"),
            stix_object_count=12,
            succeeded=True,
            error_message=None,
        )
    ]

    monkeypatch.setattr(
        "ti_framework.cli.build_pipeline_runner",
        lambda **kwargs: FakeRunner(fake_results),
    )

    run_stdout = StringIO()
    with redirect_stdout(run_stdout):
        run_exit_code = main([
            "run",
            "--config",
            str(config_path),
            "--status-file",
            str(status_path),
        ])

    assert run_exit_code == 0
    assert status_path.exists()

    status_stdout = StringIO()
    with redirect_stdout(status_stdout):
        status_exit_code = main([
            "status",
            "--status-file",
            str(status_path),
        ])

    output = status_stdout.getvalue()
    assert status_exit_code == 0
    assert "Status file:" in output
    assert "Total sources: 1" in output
    assert "Succeeded sources: 1" in output
    assert "Source: SEC-1275 IOC" in output
    assert "STIX object count: 12" in output


def test_status_command_returns_nonzero_for_missing_status_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "status" / "missing.json"

    stdout = StringIO()
    with redirect_stdout(stdout):
        exit_code = main([
            "status",
            "--status-file",
            str(missing_path),
        ])

    output = stdout.getvalue()
    assert exit_code == 1
    assert f"Status file not found: {missing_path}" in output
