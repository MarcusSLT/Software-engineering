from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import stix2

# При необходимости можно поменять шаблоны правил
IP_RULE_TEMPLATE = (
    'alert ip any any <> {indicator} any '
    '(msg:"TI IOC IPv4: {indicator}"; '
    'threshold:type limit, track ip_pair, count 1, seconds 120; '
    'reference:url,{reference_url}; '
    'classtype:trojan-activity; '
    'sid:{sid}; rev:1;)'
)

DOMAIN_RULE_TEMPLATE = (
    'alert dns $HOME_NET any -> any any '
    '(msg:"TI IOC domain: {indicator}"; '
    'threshold:type limit, track by_src, count 1, seconds 120; '
    'dns.query; dotprefix; content:".{indicator}"; endswith; '
    'reference:url,{reference_url}; '
    'classtype:trojan-activity; '
    'sid:{sid}; rev:1;)'
)

START_SID = 7000000


def _load_bundle(path: Path) -> dict[str, Any]:
    bundle = stix2.parse(path.read_text(encoding="utf-8"), allow_custom=True)
    if getattr(bundle, "type", None) != "bundle":
        raise ValueError(f"{path} is not a STIX bundle")
    return json.loads(bundle.serialize())


def _collect_reports_by_object_ref(bundle: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    reports_by_ref: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for obj in bundle.get("objects", []):
        if obj.get("type") != "report":
            continue

        refs = obj.get("object_refs", [])
        if not isinstance(refs, list):
            continue

        for ref in refs:
            reports_by_ref[ref].append(obj)

    return reports_by_ref


def _extract_reference_urls(report: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for ref in report.get("external_references", []):
        url = ref.get("url")
        if isinstance(url, str) and url.strip():
            urls.append(url.strip())
    return urls


def _collect_iocs(bundle: dict[str, Any]) -> list[tuple[str, str, str]]:
    """
    Возвращает список кортежей:
    (ioc_type, indicator_value, reference_url)
    где ioc_type in {"ipv4", "domain"}
    """
    reports_by_ref = _collect_reports_by_object_ref(bundle)
    rows: list[tuple[str, str, str]] = []

    for obj in bundle.get("objects", []):
        obj_type = obj.get("type")
        obj_id = obj.get("id")

        if obj_type not in {"ipv4-addr", "domain-name"}:
            continue
        if not isinstance(obj_id, str):
            continue

        value = obj.get("value")
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip()

        report_urls: list[str] = []
        for report in reports_by_ref.get(obj_id, []):
            report_urls.extend(_extract_reference_urls(report))

        report_urls = sorted(set(report_urls))
        if not report_urls:
            report_urls = ["https://example.invalid/no-reference"]

        ioc_type = "ipv4" if obj_type == "ipv4-addr" else "domain"
        for url in report_urls:
            rows.append((ioc_type, value, url))

    return sorted(set(rows))


def _render_rule(ioc_type: str, indicator: str, reference_url: str, sid: int) -> str:
    if ioc_type == "ipv4":
        return IP_RULE_TEMPLATE.format(
            indicator=indicator,
            reference_url=reference_url,
            sid=sid,
        )

    if ioc_type == "domain":
        return DOMAIN_RULE_TEMPLATE.format(
            indicator=indicator,
            reference_url=reference_url,
            sid=sid,
        )

    raise ValueError(f"Unsupported IOC type: {ioc_type}")


def generate_rules(bundle_path: Path, output_path: Path) -> None:
    bundle = _load_bundle(bundle_path)
    iocs = _collect_iocs(bundle)

    rules: list[str] = []
    sid = START_SID

    for ioc_type, indicator, reference_url in iocs:
        rules.append(_render_rule(ioc_type, indicator, reference_url, sid))
        sid += 1

    output_path.write_text("\n".join(rules) + ("\n" if rules else ""), encoding="utf-8")

    print(f"Read bundle: {bundle_path}")
    print(f"IOC rows: {len(iocs)}")
    print(f"Rules written: {len(rules)}")
    print(f"Output: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate simple Suricata rules from a STIX bundle."
    )
    parser.add_argument("input_stix", type=Path, help="Path to input STIX bundle JSON")
    parser.add_argument("output_rules", type=Path, help="Path to output .rules file")
    args = parser.parse_args()

    generate_rules(args.input_stix, args.output_rules)


if __name__ == "__main__":
    main()
