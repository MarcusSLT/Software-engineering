"""Composable IOC filter built from small filtering rules."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from ti_framework.domain.models import IOC
from ti_framework.ports.ioc_filter import IOCFilter, IOCFilterRule

logger = logging.getLogger(__name__)


class RuleBasedIOCFilter(IOCFilter):
    """Apply IOC filter rules sequentially, keeping only accepted indicators."""

    def __init__(self, rules: Iterable[IOCFilterRule] | None = None) -> None:
        self._rules = tuple(rules or ())

    def filter_iocs(self, iocs: tuple[IOC, ...] | list[IOC]) -> tuple[IOC, ...]:
        filtered: list[IOC] = []
        for ioc in iocs:
            if self._should_keep(ioc):
                filtered.append(ioc)
        logger.debug(
            "IOC filter kept %d of %d indicators using %d rules",
            len(filtered),
            len(iocs),
            len(self._rules),
        )
        return tuple(filtered)

    def _should_keep(self, ioc: IOC) -> bool:
        for rule in self._rules:
            if not rule.should_keep(ioc):
                logger.debug("IOC dropped by %s: %s=%s", rule.__class__.__name__, ioc.kind, ioc.value)
                return False
        return True
