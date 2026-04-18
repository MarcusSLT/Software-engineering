"""Parser implementation for Securelist (Kaspersky Securelist)."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

from ti_framework.domain.exceptions import ParsingError
from ti_framework.domain.models import Entry, IOC, IndexEntry, PreprocessedData
from ti_framework.ports.parser import Parser


class SecurelistParser(Parser):
    """Source-specific parser for https://securelist.com/all/."""

    _INDEX_LINK_SELECTORS: tuple[str, ...] = (
        "main h3 a[href]",
        "h3 a[href]",
        "article h2 a[href]",
        "article h3 a[href]",
    )
    _ENTRY_CONTAINER_SELECTORS: tuple[str, ...] = (
        "article .post-content",
        "article .entry-content",
        "article .single-content",
        "article .article-content",
        "article [class*='content']",
        "main article",
        "article",
        "main",
        "body",
    )
    _SKIP_PATHS: frozenset[str] = frozenset({"/", "/all/", "/all", "/tags/", "/authors/"})
    _ARTICLE_PATH_RE = re.compile(r"^/[^/]+/\d+/?$")
    _IOC_SECTION_RE = re.compile(r"(?:appendix\s*[ivx]+\s*[–-]\s*)?indicators?\s+of\s+compromise", re.I)
    _URL_RE = re.compile(r"\bhttps?://[^\s<>'\")\]]+")
    _IP_PORT_RE = re.compile(
        r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}:(?:6553[0-5]|655[0-2]\d|65[0-4]\d{2}|6[0-4]\d{3}|[1-5]?\d{1,4})\b"
    )
    _IP_RE = re.compile(r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b")
    _SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
    _SHA1_RE = re.compile(r"\b[a-fA-F0-9]{40}\b")
    _MD5_RE = re.compile(r"\b[a-fA-F0-9]{32}\b")
    _DOMAIN_RE = re.compile(
        r"\b[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+\b"
    )
    _KIND_HINTS: tuple[tuple[str, str], ...] = (
        ("sha-256", "sha256"),
        ("sha256", "sha256"),
        ("sha-1", "sha1"),
        ("sha1", "sha1"),
        ("md5", "md5"),
        ("urls", "url"),
        ("url", "url"),
        ("domains and ips", "mixed_network"),
        ("domains & ips", "mixed_network"),
        ("domains and ip", "mixed_network"),
        ("ip addresses", "ipv4"),
        ("ips", "ipv4"),
        ("ip", "ipv4"),
        ("domains", "domain"),
        ("domain", "domain"),
        ("file hashes", "mixed_hash"),
        ("hashes", "mixed_hash"),
    )

    def parse_index(self, data: PreprocessedData) -> list[IndexEntry]:
        try:
            soup = BeautifulSoup(data.text, "html.parser")
            entries = self._extract_index_entries(soup=soup, data=data)
        except ParsingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ParsingError(f"Failed to parse index snapshot for {data.source_name}: {exc}") from exc

        if not entries:
            raise ParsingError(f"No index entries were extracted from snapshot of source '{data.source_name}'")
        return entries

    def parse_entry(self, data: PreprocessedData, index_entry: IndexEntry) -> Entry:
        if data.snapshot_kind != "entry":
            raise ParsingError(f"parse_entry() expects an entry snapshot, got snapshot_kind={data.snapshot_kind!r}")

        try:
            soup = BeautifulSoup(data.text, "html.parser")
            container = self._locate_entry_container(soup)
            title = self._extract_entry_title(container, index_entry)
            content = self._extract_content_text(container)
            iocs = tuple(self._extract_iocs(container))
        except ParsingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ParsingError(f"Failed to parse entry snapshot for {data.source_url}: {exc}") from exc

        return Entry(
            title=title,
            content=content,
            source_url=data.source_url,
            source_name=data.source_name,
            collected_at=data.collected_at,
            iocs=iocs,
        )

    def _extract_index_entries(self, *, soup: BeautifulSoup, data: PreprocessedData) -> list[IndexEntry]:
        seen_urls: set[str] = set()
        results: list[IndexEntry] = []

        for selector in self._INDEX_LINK_SELECTORS:
            for anchor in soup.select(selector):
                if not isinstance(anchor, Tag):
                    continue
                href = (anchor.get("href") or "").strip()
                title = self._normalize_text(anchor.get_text(" ", strip=True))
                if not href or not title:
                    continue

                publication_url = urljoin(data.source_url, href)
                if publication_url in seen_urls:
                    continue
                if not self._looks_like_publication_url(publication_url, data.source_url):
                    continue

                seen_urls.add(publication_url)
                results.append(
                    IndexEntry(
                        title=title,
                        publication_url=publication_url,
                        source_name=data.source_name,
                        index_source_url=data.source_url,
                        indexed_at=data.collected_at,
                    )
                )

        return results

    def _looks_like_publication_url(self, url: str, base_url: str) -> bool:
        parsed = urlparse(url)
        base = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc != base.netloc:
            return False
        if parsed.path in self._SKIP_PATHS:
            return False
        return bool(self._ARTICLE_PATH_RE.match(parsed.path or "/"))

    def _locate_entry_container(self, soup: BeautifulSoup) -> Tag:
        for selector in self._ENTRY_CONTAINER_SELECTORS:
            candidate = soup.select_one(selector)
            if isinstance(candidate, Tag):
                text = self._normalize_text(candidate.get_text(" ", strip=True))
                if text:
                    return candidate
        raise ParsingError("Failed to locate content element on entry page")

    def _extract_entry_title(self, container: Tag, index_entry: IndexEntry) -> str:
        title_node = container.select_one("h1")
        if isinstance(title_node, Tag):
            title = self._normalize_text(title_node.get_text(" ", strip=True))
            if title:
                return title
        return index_entry.title

    def _extract_content_text(self, container: Tag) -> str:
        text = container.get_text("\n", strip=True)
        lines = [self._normalize_text(line) for line in text.splitlines()]
        content = "\n".join(line for line in lines if line)
        if not content:
            raise ParsingError("Entry content container is empty")
        return content

    def _extract_iocs(self, container: Tag) -> list[IOC]:
        heading = self._find_ioc_heading(container)
        if heading is None:
            return []

        blocks = self._collect_section_blocks(heading)
        if not blocks:
            return []

        results: list[IOC] = []
        seen: set[tuple[str, str]] = set()
        current_hint: str | None = None

        for block in blocks:
            if self._is_heading(block):
                current_hint = self._kind_from_heading(block.get_text(" ", strip=True))
                continue

            if block.name == "table":
                self._extract_iocs_from_table(block, results, seen)
                continue

            if block.name in {"ul", "ol"}:
                for li in block.find_all("li"):
                    self._extract_iocs_from_text(li.get_text(" ", strip=True), current_hint, results, seen)
                continue

            if block.name in {"pre", "code"}:
                self._extract_iocs_from_text(block.get_text("\n", strip=True), current_hint, results, seen)
                continue

            if block.name in {"p", "div", "section", "figure", "blockquote"}:
                hint_from_block = self._kind_from_heading(block.get_text(" ", strip=True))
                effective_hint = hint_from_block or current_hint
                self._extract_iocs_from_text(block.get_text("\n", strip=True), effective_hint, results, seen)

        return results

    def _find_ioc_heading(self, container: Tag) -> Tag | None:
        for heading in container.find_all(["h2", "h3", "h4"]):
            text = self._normalize_heading(heading.get_text(" ", strip=True))
            if self._IOC_SECTION_RE.search(text):
                return heading
        return None

    def _collect_section_blocks(self, heading: Tag) -> list[Tag]:
        blocks: list[Tag] = []
        for sibling in heading.next_siblings:
            if isinstance(sibling, NavigableString):
                continue
            if not isinstance(sibling, Tag):
                continue
            if sibling.name in {"h1", "h2"}:
                break
            blocks.append(sibling)
        return blocks

    def _is_heading(self, node: Tag) -> bool:
        return node.name in {"h2", "h3", "h4", "h5"}

    def _kind_from_heading(self, text: str) -> str | None:
        normalized = self._normalize_heading(text)
        for needle, kind in self._KIND_HINTS:
            if needle in normalized:
                return kind
        return None

    def _extract_iocs_from_table(self, table: Tag, results: list[IOC], seen: set[tuple[str, str]]) -> None:
        rows = table.find_all("tr")
        if not rows:
            return

        header_cells = rows[0].find_all(["th", "td"])
        kinds_by_col = [self._kind_from_heading(cell.get_text(" ", strip=True)) for cell in header_cells]
        if not any(kinds_by_col):
            for row in rows:
                for cell in row.find_all(["th", "td"]):
                    self._extract_iocs_from_text(cell.get_text(" ", strip=True), None, results, seen)
            return

        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            for idx, cell in enumerate(cells):
                hint = kinds_by_col[idx] if idx < len(kinds_by_col) else None
                self._extract_iocs_from_text(cell.get_text(" ", strip=True), hint, results, seen)

    def _extract_iocs_from_text(
        self,
        text: str,
        hint: str | None,
        results: list[IOC],
        seen: set[tuple[str, str]],
    ) -> None:
        normalized = self._normalize_ioc_text(text)
        if not normalized:
            return

        if hint in {"md5", "sha1", "sha256", "ipv4", "url", "domain"}:
            kind_map = {hint: self._patterns_for_kind(hint)}
        elif hint == "mixed_hash":
            kind_map = {"sha256": [self._SHA256_RE], "sha1": [self._SHA1_RE], "md5": [self._MD5_RE]}
        elif hint == "mixed_network":
            kind_map = {"url": [self._URL_RE], "ipv4": [self._IP_RE], "domain": [self._DOMAIN_RE]}
        else:
            kind_map = {
                "url": [self._URL_RE],
                "sha256": [self._SHA256_RE],
                "sha1": [self._SHA1_RE],
                "md5": [self._MD5_RE],
                "ipv4": [self._IP_RE],
                "domain": [self._DOMAIN_RE],
            }

        residual = normalized
        extracted_urls = [m.group(0) for m in self._URL_RE.finditer(normalized)]
        for url in extracted_urls:
            residual = residual.replace(url, " ")
        residual = self._IP_PORT_RE.sub(" ", residual)
        residual = self._IP_RE.sub(" ", residual)

        for kind, patterns in kind_map.items():
            target_text = residual if kind == "domain" else normalized
            for pattern in patterns:
                for match in pattern.finditer(target_text):
                    value = match.group(0).strip(".,;:()[]{}<>'\"")
                    if not value:
                        continue
                    if kind == "domain" and self._looks_like_hash(value):
                        continue
                    self._append_ioc(kind, value, results, seen)

    def _patterns_for_kind(self, kind: str) -> list[re.Pattern[str]]:
        mapping = {
            "md5": [self._MD5_RE],
            "sha1": [self._SHA1_RE],
            "sha256": [self._SHA256_RE],
            "ipv4": [self._IP_RE],
            "url": [self._URL_RE],
            "domain": [self._DOMAIN_RE],
        }
        return mapping[kind]

    def _append_ioc(self, kind: str, value: str, results: list[IOC], seen: set[tuple[str, str]]) -> None:
        pair = (kind, value)
        if pair in seen:
            return
        seen.add(pair)
        results.append(IOC(kind=kind, value=value))

    def _looks_like_hash(self, value: str) -> bool:
        return bool(self._MD5_RE.fullmatch(value) or self._SHA1_RE.fullmatch(value) or self._SHA256_RE.fullmatch(value))

    def _normalize_heading(self, text: str) -> str:
        text = self._normalize_text(text).lower()
        return text.replace("—", "-").replace("–", "-")

    def _normalize_ioc_text(self, text: str) -> str:
        normalized = self._normalize_text(text)
        normalized = normalized.replace("hxxps://", "https://").replace("hxxp://", "http://")
        normalized = normalized.replace("[:]//", "://")
        normalized = normalized.replace("[.]", ".").replace("(.)", ".")
        normalized = normalized.replace("［.］", ".")
        return normalized

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
