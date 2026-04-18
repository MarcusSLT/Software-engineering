"""Shared logging configuration for the ti_framework package."""

from __future__ import annotations

import logging
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


def _select_format(level: int) -> str:
    """Choose a readable INFO format or a verbose DEBUG format."""
    return _DEBUG_FORMAT if level <= logging.DEBUG else _INFO_FORMAT


def configure_framework_logging(level: int | str = "WARNING") -> logging.Logger:
    """Configure the package logger once and return it.

    Child loggers such as ``ti_framework.application.pipeline_runner`` propagate to
    this logger, so configuring it once is enough for the whole project.
    """
    logger = logging.getLogger("ti_framework")
    normalized_level = normalize_log_level(level)
    logger.setLevel(normalized_level)

    formatter = logging.Formatter(_select_format(normalized_level))
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        for handler in logger.handlers:
            handler.setFormatter(formatter)

    logger.propagate = False
    return logger
