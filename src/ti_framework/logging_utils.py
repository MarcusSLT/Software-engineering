"""Shared logging configuration for the ti_framework package."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

_INFO_FORMAT: Final[str] = "%(levelname)s | %(message)s"
_DEBUG_FORMAT: Final[str] = (
    "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)


def normalize_log_level(level: int | str) -> int:
    """Convert a user-provided logging level into a stdlib logging level integer."""
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        normalized = level.strip().upper()
        if normalized.isdigit():
            return int(normalized)
        value = getattr(logging, normalized, None)
        if isinstance(value, int):
            return value
    raise ValueError(f"Unsupported log level: {level!r}")


def _select_console_format(level: int) -> str:
    """Choose a readable INFO format or a verbose DEBUG format for console logs."""
    return _DEBUG_FORMAT if level <= logging.DEBUG else _INFO_FORMAT


def _build_stream_handler(level: int) -> logging.Handler:
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_select_console_format(level)))
    return handler


def _build_file_handler(level: int, log_file: str | Path) -> logging.Handler:
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_DEBUG_FORMAT))
    return handler


def configure_framework_logging(
    level: int | str = "WARNING",
    *,
    log_file: str | Path | None = None,
) -> logging.Logger:
    """Configure the package logger and return it.

    Child loggers such as ``ti_framework.application.pipeline_runner`` propagate to
    this logger, so configuring it once is enough for the whole project.
    When ``log_file`` is provided, logs are emitted both to stderr and to the file.
    """
    logger = logging.getLogger("ti_framework")
    normalized_level = normalize_log_level(level)
    logger.setLevel(normalized_level)

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    logger.addHandler(_build_stream_handler(normalized_level))
    if log_file is not None:
        logger.addHandler(_build_file_handler(normalized_level, log_file))

    logger.propagate = False
    return logger
