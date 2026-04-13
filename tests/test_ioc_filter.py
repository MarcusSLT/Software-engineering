from __future__ import annotations

from datetime import datetime, timezone

from ti_framework.domain.models import Entry, IOC
from ti_framework.infrastructure.filters.invalid_domain_rule import DropInvalidDomainRule
from ti_framework.infrastructure.filters.internal_url_rule import DropInternalUrlRule
from ti_framework.infrastructure.filters.rule_based_ioc_filter import RuleBasedIOCFilter
from ti_framework.infrastructure.filters.special_purpose_ipv4_rule import DropSpecialPurposeIPv4Rule


def test_drop_special_purpose_ipv4_rule_blocks_ioc_values_from_reserved_ranges() -> None:
    rule = DropSpecialPurposeIPv4Rule()

    dropped = [
        IOC("ipv4", "127.0.0.1"),
        IOC("ipv4", "10.25.10.2"),
        IOC("ipv4", "100.64.1.10"),
        IOC("ipv4", "169.254.12.4"),
        IOC("ipv4", "172.16.4.8"),
        IOC("ipv4", "192.168.1.44"),
        IOC("ipv4", "198.51.100.7"),
        IOC("ipv4", "203.0.113.20"),
        IOC("ipv4", "255.255.255.255"),
        IOC("ipv4_port", "127.0.0.1:443"),
    ]

    assert all(not rule.should_keep(ioc) for ioc in dropped)


def test_drop_special_purpose_ipv4_rule_keeps_public_ipv4_and_explicit_iana_exceptions() -> None:
    rule = DropSpecialPurposeIPv4Rule()

    kept = [
        IOC("ipv4", "8.8.8.8"),
        IOC("ipv4", "1.1.1.1"),
        IOC("ipv4_port", "8.8.4.4:53"),
        IOC("ipv4", "192.0.0.9"),
        IOC("ipv4", "192.0.0.10"),
        IOC("domain", "example.org"),
    ]

    assert all(rule.should_keep(ioc) for ioc in kept)


def test_drop_invalid_domain_rule_blocks_malformed_and_internal_domains() -> None:
    rule = DropInvalidDomainRule()

    dropped = [
        IOC("domain", "localhost"),
        IOC("domain", "internal"),
        IOC("domain", "corp.local"),
        IOC("domain", "bad domain.example"),
        IOC("domain", "example.com/path"),
        IOC("domain", "alice@example.org"),
        IOC("domain", "192.168.1.10"),
        IOC("domain", "-bad.example"),
    ]
    kept = [
        IOC("domain", "evil.example"),
        IOC("domain", "sub-domain.badguy.net"),
        IOC("url", "https://example.org/malware"),
    ]

    assert all(not rule.should_keep(ioc) for ioc in dropped)
    assert all(rule.should_keep(ioc) for ioc in kept)


def test_drop_internal_url_rule_blocks_local_invalid_and_private_url_hosts() -> None:
    rule = DropInternalUrlRule()

    dropped = [
        IOC("url", "http://localhost:8080/admin"),
        IOC("url", "https://corp.local/login"),
        IOC("url", "http://10.0.0.5/beacon"),
        IOC("url", "http://192.168.1.44/panel"),
        IOC("url", "http://internal-host/path"),
        IOC("url", "not-a-url"),
    ]
    kept = [
        IOC("url", "https://evil.example/payload"),
        IOC("url", "http://8.8.8.8/a"),
    ]

    assert all(not rule.should_keep(ioc) for ioc in dropped)
    assert all(rule.should_keep(ioc) for ioc in kept)


def test_rule_based_ioc_filter_filters_entry_without_touching_other_fields() -> None:
    entry = Entry(
        title="Example",
        content="content",
        source_url="https://example.org/post",
        source_name="Example Source",
        collected_at=datetime.now(timezone.utc),
        iocs=(
            IOC("ipv4", "10.10.10.10"),
            IOC("ipv4", "8.8.8.8"),
            IOC("domain", "evil.example"),
            IOC("domain", "corp.local"),
            IOC("url", "https://evil.example/dropper"),
            IOC("url", "http://localhost/internal"),
            IOC("ipv4_port", "192.168.0.10:8080"),
        ),
    )

    ioc_filter = RuleBasedIOCFilter([
        DropSpecialPurposeIPv4Rule(),
        DropInvalidDomainRule(),
        DropInternalUrlRule(),
    ])
    filtered = ioc_filter.filter_entry(entry)

    assert filtered.title == entry.title
    assert filtered.source_url == entry.source_url
    assert filtered.iocs == (
        IOC("ipv4", "8.8.8.8"),
        IOC("domain", "evil.example"),
        IOC("url", "https://evil.example/dropper"),
    )
