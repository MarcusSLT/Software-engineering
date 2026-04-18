"""Drop local-only or obviously malformed URL indicators."""

from __future__ import annotations

from urllib.parse import urlparse

from ti_framework.domain.models import IOC
from ti_framework.infrastructure.filters.invalid_domain_rule import DropInvalidDomainRule
from ti_framework.infrastructure.filters.special_purpose_ipv4_rule import is_special_purpose_ipv4, parse_ipv4_value

_INTERNAL_HOST_SUFFIXES = (
    ".local",
    ".localdomain",
    ".localhost",
    ".internal",
    ".intranet",
    ".lan",
    ".home",
    ".corp",
)
_INTERNAL_HOST_EXACT = {
    "localhost",
    "localdomain",
}


class DropInternalUrlRule:
    """Reject URLs pointing to private/special-purpose or local-only destinations."""

    def __init__(self) -> None:
        self._domain_rule = DropInvalidDomainRule()

    def should_keep(self, ioc: IOC) -> bool:
        if ioc.kind != "url":
            return True

        value = ioc.value.strip()
        if not value:
            return False

        parsed = urlparse(value)
        hostname = parsed.hostname
        if not parsed.scheme or not hostname:
            return False

        host = hostname.strip().rstrip(".").lower()
        if host in _INTERNAL_HOST_EXACT or host.endswith(_INTERNAL_HOST_SUFFIXES):
            return False
        if "." not in host:
            return False

        ipv4 = parse_ipv4_value(host)
        if ipv4 is not None:
            return not is_special_purpose_ipv4(ipv4)

        return self._domain_rule.should_keep(IOC(kind="domain", value=host))
