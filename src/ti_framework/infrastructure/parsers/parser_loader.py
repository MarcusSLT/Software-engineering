"""Dynamic parser loader."""

from __future__ import annotations

from importlib import import_module
import logging

from ti_framework.ports.parser import Parser

logger = logging.getLogger(__name__)


def load_parser(parser_path: str) -> Parser:
    logger.debug("Loading parser %s", parser_path)
    module_path, separator, class_name = parser_path.rpartition(".")
    if not separator:
        raise ValueError(
            "parser_path must be a dotted path like 'package.module.ParserClass'"
        )

    module = import_module(module_path)
    parser_class = getattr(module, class_name)

    if not isinstance(parser_class, type) or not issubclass(parser_class, Parser):
        raise TypeError(f"Loaded object '{parser_path}' is not a Parser subclass")

    instance = parser_class()
    logger.debug("Loaded parser instance %s", parser_class.__name__)
    return instance
