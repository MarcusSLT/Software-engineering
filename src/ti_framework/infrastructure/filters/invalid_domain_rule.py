"""Drop invalid or clearly internal domain indicators."""

from __future__ import annotations

import re

from ti_framework.domain.models import IOC
from ti_framework.infrastructure.filters.special_purpose_ipv4_rule import parse_ipv4_value

_DOMAIN_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)
_INTERNAL_SUFFIXES = (
    ".local",
    ".localdomain",
    ".localhost",
    ".internal",
    ".intranet",
    ".lan",
    ".home",
    ".corp",
)
_INTERNAL_EXACT = {
    "localhost",
    "localdomain",
}


class DropInvalidDomainRule:
    """Reject malformed domains and obviously local-only hostnames."""

    def should_keep(self, ioc: IOC) -> bool:
        if ioc.kind != "domain":
            return True

        value = ioc.value.strip().rstrip(".").lower()
        if not value:
            return False
        if any(ch.isspace() for ch in value):
            return False
        if "/" in value or ":" in value or "@" in value:
            return False
        if value in _INTERNAL_EXACT or value.endswith(_INTERNAL_SUFFIXES):
            return False
        if parse_ipv4_value(value) is not None:
            return False
        if "." not in value:
            return False
        if len(value) > 253:
            return False

        labels = value.split(".")
        return all(_DOMAIN_LABEL_RE.fullmatch(label) for label in labels)
