from __future__ import annotations

import logging

from ti_framework.logging_utils import configure_framework_logging, normalize_log_level


def test_normalize_log_level_accepts_case_insensitive_names() -> None:
    assert normalize_log_level("debug") == logging.DEBUG
    assert normalize_log_level("Info") == logging.INFO


def test_configure_framework_logging_attaches_handler() -> None:
    logger = configure_framework_logging("INFO")
    assert logger.name == "ti_framework"
    assert logger.handlers
    assert logger.level == logging.INFO


def test_configure_framework_logging_uses_compact_format_for_info() -> None:
    logger = configure_framework_logging("INFO")
    formatter = logger.handlers[0].formatter
    assert formatter is not None
    assert formatter._fmt == "%(levelname)s | %(message)s"


def test_configure_framework_logging_uses_verbose_format_for_debug() -> None:
    logger = configure_framework_logging("DEBUG")
    formatter = logger.handlers[0].formatter
    assert formatter is not None
    assert "%(asctime)s" in formatter._fmt
    assert "%(filename)s:%(lineno)d" in formatter._fmt


def test_configure_framework_logging_reconfigures_existing_handler() -> None:
    logger = configure_framework_logging("INFO")
    assert logger.handlers[0].formatter is not None
    assert logger.handlers[0].formatter._fmt == "%(levelname)s | %(message)s"

    logger = configure_framework_logging("DEBUG")
    assert logger.handlers[0].formatter is not None
    assert "%(asctime)s" in logger.handlers[0].formatter._fmt
