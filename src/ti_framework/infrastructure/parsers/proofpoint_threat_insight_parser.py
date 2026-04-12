"""Parser implementation for Proofpoint Threat Insight blog."""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

from ti_framework.domain.exceptions import ParsingError
from ti_framework.domain.models import Entry, IOC, IndexEntry, PreprocessedData
from ti_framework.ports.parser import Parser

logger = logging.getLogger(__name__)


class ProofpointThreatInsightParser(Parser):
    """Source-specific parser for https://www.proofpoint.com/us/blog/threat-insight."""

    _ENTRY_CONTAINER_SELECTORS: tuple[str, ...] = (
        "main article",
        "article",
        "main [class*='blog']",
        "main [class*='post']",
        "main [class*='content']",
        "main",
        "body",
    )
    _IOC_SECTION_RE = re.compile(r"(?:example\s+)?indicators?\s+of\s+compromise", re.I)
    _URL_RE = re.compile(r"\bhttps?://[^\s<>'\")\]]+")
    _IP_RE = re.compile(r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b")
    _SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
    _SHA1_RE = re.compile(r"\b[a-fA-F0-9]{40}\b")
    _MD5_RE = re.compile(r"\b[a-fA-F0-9]{32}\b")
    _DOMAIN_RE = re.compile(
        r"\b[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+\b"
    )
    _FILENAME_RE = re.compile(r"\b[\w() -]+\.(?:exe|dll|lnk|zip|rar|docm|xlsx|xlsm|pdf|js|vbs|hta)\b", re.I)
    _EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
    _SKIP_URL_PATTERNS: tuple[str, ...] = (
        "/us/blog/threat-insight$",
        "/us/blog/threat-insight/preview",
        "/us/blog/threat-insight?page=",
        "/us/blog/threat-insight?",
    )
    _ARTICLE_PATH_RE = re.compile(r"^/us/blog/threat-insight/[a-z0-9][a-z0-9-]*/*$", re.I)
    _KIND_HINTS: tuple[tuple[str, str], ...] = (
        ("sha256", "sha256"),
        ("sha-256", "sha256"),
        ("sha1", "sha1"),
        ("sha-1", "sha1"),
        ("md5", "md5"),
        ("hash", "hash"),
        ("domain", "domain"),
        ("ip", "ipv4"),
        ("url", "url"),
        ("file", "filename"),
    )

    def parse_index(self, data: PreprocessedData) -> list[IndexEntry]:
        logger.info("%s: parsing index snapshot for %s", self.__class__.__name__, data.source_url)
        try:
            soup = BeautifulSoup(data.text, "html.parser")
            entries = self._extract_index_entries(soup=soup, data=data)
        except ParsingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ParsingError(f"Failed to parse index snapshot for {data.source_name}: {exc}") from exc

        if not entries:
            raise ParsingError(f"No index entries were extracted from snapshot of source '{data.source_name}'")
        logger.info("%s: extracted %d index entries from %s", self.__class__.__name__, len(entries), data.source_url)
        return entries

    def parse_entry(self, data: PreprocessedData, index_entry: IndexEntry) -> Entry:
        logger.info("%s: parsing entry page %s", self.__class__.__name__, data.source_url)
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

        entry = Entry(
            title=title,
            content=content,
            source_url=data.source_url,
            source_name=data.source_name,
            collected_at=data.collected_at,
            iocs=iocs,
        )
        logger.info("%s: parsed entry '%s' with %d IOC(s)", self.__class__.__name__, entry.title, len(entry.iocs))
        return entry

    def _extract_index_entries(self, *, soup: BeautifulSoup, data: PreprocessedData) -> list[IndexEntry]:
        seen_urls: set[str] = set()
        results: list[IndexEntry] = []
        for anchor in soup.select("a[href]"):
            if not isinstance(anchor, Tag):
                continue
            href = (anchor.get("href") or "").strip()
            if not href:
                continue
            publication_url = urljoin(data.source_url, href)
            if publication_url in seen_urls or not self._looks_like_publication_url(publication_url):
                continue
            title = self._normalize_text(anchor.get_text(" ", strip=True))
            if not title:
                title = self._title_from_nearby(anchor)
            if not title:
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

    def _looks_like_publication_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc != "www.proofpoint.com":
            return False
        path = parsed.path.rstrip("/")
        if not self._ARTICLE_PATH_RE.match(path):
            return False
        return not any(path.endswith(pattern.rstrip("$")) for pattern in self._SKIP_URL_PATTERNS)

    def _title_from_nearby(self, anchor: Tag) -> str:
        for candidate in [anchor.parent, anchor.find_parent(["article", "div", "section"])]:
            if not isinstance(candidate, Tag):
                continue
            for selector in ("h1", "h2", "h3", "h4"):
                node = candidate.select_one(selector)
                if isinstance(node, Tag):
                    title = self._normalize_text(node.get_text(" ", strip=True))
                    if title and title.lower() not in {"read more", "threat insight"}:
                        return title
            text = self._normalize_text(candidate.get_text(" ", strip=True))
            if text and len(text) < 180 and text.lower() not in {"read more", "threat insight"}:
                return text
        return ""

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
        blocks: list[Tag]
        if heading is not None:
            blocks = self._collect_section_blocks(heading)
        else:
            blocks = self._collect_fallback_ioc_blocks(container)
        if not blocks:
            return []

        results: list[IOC] = []
        seen: set[tuple[str, str]] = set()
        current_hint: str | None = None

        for block in blocks:
            if self._is_heading(block):
                current_hint = self._kind_from_text(block.get_text(" ", strip=True))
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
                hint = current_hint or self._kind_from_text(block.get_text(" ", strip=True))
                self._extract_iocs_from_text(block.get_text("\n", strip=True), hint, results, seen)

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

    def _collect_fallback_ioc_blocks(self, container: Tag) -> list[Tag]:
        blocks: list[Tag] = []
        for table in container.find_all("table"):
            if self._looks_like_ioc_table(table):
                blocks.append(table)
        return blocks

    def _looks_like_ioc_table(self, table: Tag) -> bool:
        header_texts = [
            self._normalize_heading(cell.get_text(" ", strip=True))
            for cell in table.find_all(["th", "td"], limit=8)
        ]
        header_blob = " | ".join(text for text in header_texts if text)
        if not header_blob:
            return False
        has_indicator_col = "indicator" in header_blob
        has_context_col = any(token in header_blob for token in ("description", "type", "context", "first seen"))
        return has_indicator_col and has_context_col

    def _is_heading(self, node: Tag) -> bool:
        return node.name in {"h2", "h3", "h4", "h5"}

    def _kind_from_text(self, text: str) -> str | None:
        normalized = self._normalize_heading(text)
        for needle, kind in self._KIND_HINTS:
            if needle in normalized:
                return kind
        return None

    def _extract_iocs_from_table(self, table: Tag, results: list[IOC], seen: set[tuple[str, str]]) -> None:
        rows = table.find_all("tr")
        if not rows:
            return
        for row in rows:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            row_texts = [self._normalize_text(cell.get_text(" ", strip=True)) for cell in cells]
            row_hint = next((self._kind_from_text(text) for text in row_texts if self._kind_from_text(text)), None)
            if len(cells) >= 2 and row_hint:
                self._extract_iocs_from_text(cells[0].get_text(" ", strip=True), row_hint, results, seen)
                continue
            for cell in cells:
                self._extract_iocs_from_text(cell.get_text(" ", strip=True), row_hint, results, seen)

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

        if hint == "sha256":
            kind_map = {"sha256": [self._SHA256_RE]}
        elif hint == "sha1":
            kind_map = {"sha1": [self._SHA1_RE]}
        elif hint == "md5":
            kind_map = {"md5": [self._MD5_RE]}
        elif hint == "ipv4":
            kind_map = {"ipv4": [self._IP_RE]}
        elif hint == "domain":
            kind_map = {"domain": [self._DOMAIN_RE]}
        elif hint == "url":
            kind_map = {"url": [self._URL_RE]}
        elif hint == "filename":
            kind_map = {"filename": [self._FILENAME_RE]}
        else:
            kind_map = {
                "url": [self._URL_RE],
                "sha256": [self._SHA256_RE],
                "sha1": [self._SHA1_RE],
                "md5": [self._MD5_RE],
                "ipv4": [self._IP_RE],
                "domain": [self._DOMAIN_RE],
                "filename": [self._FILENAME_RE],
            }

        residual = normalized
        for url in [m.group(0) for m in self._URL_RE.finditer(normalized)]:
            residual = residual.replace(url, " ")
        for email in [m.group(0) for m in self._EMAIL_RE.finditer(normalized)]:
            residual = residual.replace(email, " ")
        residual = self._IP_RE.sub(" ", residual)

        for kind, patterns in kind_map.items():
            target = residual if kind == "domain" else normalized
            for pattern in patterns:
                for match in pattern.finditer(target):
                    value = match.group(0).strip(".,;:()[]{}<>'\"")
                    if not value:
                        continue
                    if kind == "domain" and (self._looks_like_hash(value) or self._looks_like_filename(value)):
                        continue
                    self._append_ioc(kind, value, results, seen)

    def _append_ioc(self, kind: str, value: str, results: list[IOC], seen: set[tuple[str, str]]) -> None:
        pair = (kind, value)
        if pair in seen:
            return
        seen.add(pair)
        results.append(IOC(kind=kind, value=value))

    def _looks_like_hash(self, value: str) -> bool:
        return bool(self._MD5_RE.fullmatch(value) or self._SHA1_RE.fullmatch(value) or self._SHA256_RE.fullmatch(value))

    def _looks_like_filename(self, value: str) -> bool:
        return bool(self._FILENAME_RE.fullmatch(value))

    def _normalize_heading(self, text: str) -> str:
        return self._normalize_text(text).lower().replace("—", "-").replace("–", "-")

    def _normalize_ioc_text(self, text: str) -> str:
        normalized = self._normalize_text(text)
        normalized = normalized.replace("hxxps://", "https://").replace("hxxp://", "http://")
        normalized = normalized.replace("[:]//", "://")
        normalized = normalized.replace("[.]", ".").replace("(.)", ".")
        normalized = normalized.replace("［.］", ".")
        return normalized

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
