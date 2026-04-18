"""Drop IPv4 indicators that belong to IANA special-purpose ranges."""

from __future__ import annotations

from ipaddress import IPv4Address, IPv4Network, ip_address

from ti_framework.domain.models import IOC

# IANA IPv4 Special-Purpose Address Space entries that are not globally reachable.
# More-specific globally reachable carve-outs (for example 192.0.0.9/32, 192.0.0.10/32,
# 192.31.196.0/24, 192.52.193.0/24, 192.175.48.0/24) are intentionally excluded.
_BLOCKED_NETWORKS: tuple[IPv4Network, ...] = tuple(
    IPv4Network(cidr)
    for cidr in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.88.99.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "240.0.0.0/4",
        "255.255.255.255/32",
    )
)

_ALLOWED_SINGLE_ADDRESSES: frozenset[IPv4Address] = frozenset(
    IPv4Address(value)
    for value in (
        "192.0.0.9",
        "192.0.0.10",
    )
)


def parse_ipv4_value(value: str) -> IPv4Address | None:
    """Parse a plain IPv4 string and return None for non-IPv4 values."""
    try:
        parsed = ip_address(value.strip())
    except ValueError:
        return None
    return parsed if isinstance(parsed, IPv4Address) else None


def is_special_purpose_ipv4(address: IPv4Address) -> bool:
    """Return True when an IPv4 address belongs to a blocked special-purpose range."""
    if address in _ALLOWED_SINGLE_ADDRESSES:
        return False
    return any(address in network for network in _BLOCKED_NETWORKS)


class DropSpecialPurposeIPv4Rule:
    """Reject IPv4 and ipv4_port IOC values from special-purpose ranges."""

    def should_keep(self, ioc: IOC) -> bool:
        if ioc.kind not in {"ipv4", "ipv4_port"}:
            return True

        address = self._extract_ipv4(ioc)
        if address is None:
            return True
        return not is_special_purpose_ipv4(address)

    @staticmethod
    def _extract_ipv4(ioc: IOC) -> IPv4Address | None:
        value = ioc.value.strip()
        if ioc.kind == "ipv4_port":
            if ":" not in value:
                return None
            value = value.split(":", 1)[0]
        return parse_ipv4_value(value)
