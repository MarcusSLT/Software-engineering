"""STIX 2.1 bundle builder."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC
from typing import Any

from stix2 import properties
from stix2.v21 import (
    Bundle,
    CustomObservable,
    DomainName,
    ExternalReference,
    File,
    Identity,
    IPv4Address,
    NetworkTraffic,
    Report,
    URL,
)

from ti_framework.domain.exceptions import StixBundleError
from ti_framework.domain.models import Entry, IOC
from ti_framework.ports.stix_bundle_builder import StixBundleBuilder


@CustomObservable(
    "x-ti-tox-id",
    [("value", properties.StringProperty(required=True))],
    id_contrib_props=["value"],
)
class ToxIdObservable:  # pragma: no cover - exercised through builder tests/e2e
    """Custom SCO for Tox identifiers, which do not have a native STIX 2.1 SCO."""


@CustomObservable(
    "x-ti-observable",
    [
        ("observable_type", properties.StringProperty(required=True)),
        ("value", properties.StringProperty(required=True)),
    ],
    id_contrib_props=["observable_type", "value"],
)
class GenericTextObservable:  # pragma: no cover - exercised through builder tests/e2e
    """Fallback custom SCO for source-specific observable types without a standard SCO."""


class Stix21BundleBuilder(StixBundleBuilder):
    """Convert parsed entries and IOC values into a STIX 2.1 bundle."""

    _IPV4_PORT_RE = re.compile(
        r"^(?P<ip>(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}):"
        r"(?P<port>6553[0-5]|655[0-2]\d|65[0-4]\d{2}|6[0-4]\d{3}|[1-5]?\d{1,4})$"
    )
    _DOMAIN_KINDS: frozenset[str] = frozenset({
        "domain",
        "domains",
        "host names",
        "hostname",
        "hostnames",
        "onion domains",
    })
    _URL_KINDS: frozenset[str] = frozenset({"url", "urls"})
    _TOX_KINDS: frozenset[str] = frozenset({"tox id", "tox", "tox ids"})

    def __init__(self, report_type: str = "threat-report") -> None:
        self._report_type = report_type

    def build(self, entries: Iterable[Entry]) -> Bundle | None:
        entries = list(entries)
        if not entries:
            return None

        try:
            registry: dict[str, Any] = {}
            reports: list[Report] = []

            source_identity = self._build_source_identity(entries[0])
            registry[source_identity.id] = source_identity

            for entry in entries:
                object_refs = self._build_observables(entry.iocs, registry)
                if not object_refs:
                    continue

                report = self._build_report(
                    entry=entry,
                    object_refs=object_refs,
                    created_by_ref=source_identity.id,
                )
                registry[report.id] = report
                reports.append(report)

            if not reports:
                return None

            report_ids = {report.id for report in reports}
            ordered_objects = [source_identity]
            ordered_objects.extend(
                obj for object_id, obj in registry.items()
                if object_id not in report_ids and object_id != source_identity.id
            )
            ordered_objects.extend(reports)
            return Bundle(objects=ordered_objects, allow_custom=True)
        except StixBundleError:
            raise
        except Exception as exc:  # noqa: BLE001 - STIX boundary
            raise StixBundleError(f"Failed to build STIX bundle: {exc}") from exc

    def _build_observables(self, iocs: Iterable[IOC], registry: dict[str, Any]) -> list[str]:
        object_refs: list[str] = []
        for ioc in iocs:
            for stix_object in self._build_sco_objects(ioc):
                registry.setdefault(stix_object.id, stix_object)
                object_refs.append(stix_object.id)
        return list(dict.fromkeys(object_refs))

    def _build_source_identity(self, entry: Entry) -> Identity:
        timestamp = entry.collected_at.astimezone(UTC)
        return Identity(
            name=entry.source_name,
            identity_class="organization",
            created=timestamp,
            modified=timestamp,
        )

    def _build_report(self, *, entry: Entry, object_refs: list[str], created_by_ref: str) -> Report:
        timestamp = entry.collected_at.astimezone(UTC)
        content = entry.content if len(entry.content) <= 20_000 else f"{entry.content[:19_997]}..."
        return Report(
            name=entry.title,
            description=content,
            report_types=[self._report_type],
            published=timestamp,
            created=timestamp,
            modified=timestamp,
            created_by_ref=created_by_ref,
            object_refs=object_refs,
            external_references=[
                ExternalReference(
                    source_name=entry.source_name,
                    url=entry.source_url,
                    description="Original publication URL",
                )
            ],
            allow_custom=True,
        )

    def _build_sco_objects(self, ioc: IOC) -> tuple[Any, ...]:
        kind = ioc.kind.casefold().strip()
        value = ioc.value.strip()

        if kind == "ipv4":
            return (IPv4Address(value=value),)
        if kind == "ipv4_port":
            return self._build_ipv4_port_objects(value)
        if kind in self._DOMAIN_KINDS:
            return (DomainName(value=value),)
        if kind in self._URL_KINDS:
            return (URL(value=value),)
        if kind == "md5":
            return (File(hashes={"MD5": value}),)
        if kind == "sha1":
            return (File(hashes={"SHA-1": value}),)
        if kind == "sha256":
            return (File(hashes={"SHA-256": value}),)
        if kind in self._TOX_KINDS:
            return (ToxIdObservable(value=value),)
        return (GenericTextObservable(observable_type=kind, value=value),)

    def _build_ipv4_port_objects(self, value: str) -> tuple[Any, ...]:
        match = self._IPV4_PORT_RE.match(value)
        if not match:
            raise StixBundleError(f"Invalid ipv4_port IOC value: {value!r}")

        address = IPv4Address(value=match.group("ip"))
        traffic = NetworkTraffic(
            protocols=["ipv4"],
            dst_ref=address.id,
            dst_port=int(match.group("port")),
        )
        return address, traffic