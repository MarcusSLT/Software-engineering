"""Parser implementation for the 1275.ru IOC source."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

from ti_framework.domain.exceptions import ParsingError
from ti_framework.domain.models import Entry, IOC, IndexEntry, PreprocessedData
from ti_framework.ports.parser import Parser

logger = logging.getLogger(__name__)


class Sec1275Parser(Parser):
    """
    Source-specific parser for https://1275.ru/ioc/.

    Index pages are parsed with BeautifulSoup. Entry pages are also parsed with
    BeautifulSoup and rely on article/content selectors plus heading navigation,
    which is less brittle than a single absolute XPath.
    """

    _TITLE_LINK_SELECTORS: tuple[str, ...] = (
        "main article h2 a[href]",
        "article h2 a[href]",
        ".entry-title a[href]",
        ".post-title a[href]",
        "h2 a[href]",
    )
    _ENTRY_CONTAINER_SELECTORS: tuple[str, ...] = (
        "main article .entry-content",
        "main article .post-content",
        "main article .td-post-content",
        "main article .single-content",
        "main article .article-content",
        "main article .wp-block-post-content",
        "main article [class*='content']",
        "article .entry-content",
        "article .post-content",
        "article .td-post-content",
        "article .single-content",
        "article .article-content",
        "article .wp-block-post-content",
        "article [class*='content']",
        "main article",
        "article",
        "main",
    )
    _IGNORED_EXACT_TITLES: frozenset[str] = frozenset(
        {
            "Популярное",
            "Подписки",
            "Топы",
            "Закладки",
        }
    )
    _SKIP_PATH_PREFIXES: tuple[str, ...] = (
        "/page/",
        "/category/",
        "/tag/",
        "/author/",
        "/feed/",
        "/wp-content/",
        "/wp-json/",
    )
    _IOC_SECTION_TITLE: str = "индикаторы компрометации"
    _PROTECTED_TEXT_MARKERS: tuple[str, ...] = (
        "доступно только авторизованным пользователям",
        "присоединиться",
    )
    _STOP_SECTION_MARKERS: tuple[str, ...] = (
        "комментарии",
        "похожие записи",
        "поделиться",
    )
    _IOC_KIND_ALIASES: tuple[tuple[str, str], ...] = (
        ("ipv4 port combinations", "ipv4_port"),
        ("ipv4", "ipv4"),
        ("urls", "url"),
        ("url", "url"),
        ("sha256", "sha256"),
        ("sha1", "sha1"),
        ("md5", "md5"),
        ("domains", "domain"),
        ("domain", "domain"),
        ("hosts", "domain"),
    )
    _IOC_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
        (
            re.compile(
                r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}:(?:6553[0-5]|655[0-2]\d|65[0-4]\d{2}|6[0-4]\d{3}|[1-5]?\d{1,4})\b"
            ),
            "ipv4_port",
        ),
        (
            re.compile(r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b"),
            "ipv4",
        ),
        (re.compile(r"\b[a-fA-F0-9]{64}\b"), "sha256"),
        (re.compile(r"\b[a-fA-F0-9]{40}\b"), "sha1"),
        (re.compile(r"\b[a-fA-F0-9]{32}\b"), "md5"),
        (re.compile(r"\bhttps?://[^\s<>'\"]+"), "url"),
        (
            re.compile(
                r"\b[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+\b"
            ),
            "domain",
        ),
    )

    def parse_index(self, data: PreprocessedData) -> list[IndexEntry]:
        logger.info("%s: parsing index snapshot for %s", self.__class__.__name__, data.source_url)
        try:
            soup = BeautifulSoup(data.text, "html.parser")
            entries = self._extract_index_entries(soup=soup, data=data)
        except ParsingError:
            raise
        except Exception as exc:  # noqa: BLE001 - parser boundary
            raise ParsingError(f"Failed to parse index snapshot for {data.source_name}: {exc}") from exc

        if not entries:
            raise ParsingError(
                f"No index entries were extracted from snapshot of source '{data.source_name}'"
            )

        logger.info("%s: extracted %d index entries from %s", self.__class__.__name__, len(entries), data.source_url)
        return entries

    def parse_entry(self, data: PreprocessedData, index_entry: IndexEntry) -> Entry:
        logger.info("%s: parsing entry page %s", self.__class__.__name__, data.source_url)
        if data.snapshot_kind != "entry":
            raise ParsingError(
                f"parse_entry() expects an entry snapshot, got snapshot_kind={data.snapshot_kind!r}"
            )

        try:
            soup = BeautifulSoup(data.text, "html.parser")
            article = self._locate_entry_article(soup)
            content_container = self._locate_content_container(article)
            title = self._extract_entry_title(article=article, index_entry=index_entry)
            content = self._extract_content_text(content_container)
            iocs = tuple(self._extract_iocs(content_container))
        except ParsingError:
            raise
        except Exception as exc:  # noqa: BLE001 - parser boundary
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

        for anchor in self._collect_candidate_links(soup):
            href = anchor.get("href")
            title = anchor.get_text(" ", strip=True)
            if not href or not title:
                continue
            if title in self._IGNORED_EXACT_TITLES:
                continue

            publication_url = urljoin(data.source_url, href)
            if not self._looks_like_publication_url(publication_url, data.source_url):
                continue
            if publication_url in seen_urls:
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

    def _collect_candidate_links(self, soup: BeautifulSoup) -> list[Tag]:
        seen_nodes: set[int] = set()
        anchors: list[Tag] = []

        for selector in self._TITLE_LINK_SELECTORS:
            for node in soup.select(selector):
                if not isinstance(node, Tag):
                    continue
                node_id = id(node)
                if node_id in seen_nodes:
                    continue
                seen_nodes.add(node_id)
                anchors.append(node)

        return anchors

    def _looks_like_publication_url(self, url: str, base_url: str) -> bool:
        parsed = urlparse(url)
        base = urlparse(base_url)

        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc != base.netloc:
            return False

        path = parsed.path or "/"
        if path == "/":
            return False
        if any(path.startswith(prefix) for prefix in self._SKIP_PATH_PREFIXES):
            return False

        return True

    def _locate_entry_article(self, soup: BeautifulSoup) -> Tag:
        article = soup.select_one("main article") or soup.select_one("article")
        if article is None or not isinstance(article, Tag):
            raise ParsingError("Failed to locate article element on entry page")
        return article

    def _locate_content_container(self, article: Tag) -> Tag:
        for selector in self._ENTRY_CONTAINER_SELECTORS:
            candidate = article.select_one(selector)
            if candidate is None or not isinstance(candidate, Tag):
                continue
            if self._contains_ioc_heading(candidate):
                return candidate

        for selector in self._ENTRY_CONTAINER_SELECTORS:
            candidate = article.select_one(selector)
            if candidate is None or not isinstance(candidate, Tag):
                continue
            if self._normalize_text(candidate.get_text(" ", strip=True)):
                return candidate

        return article

    def _contains_ioc_heading(self, container: Tag) -> bool:
        return self._find_ioc_heading(container) is not None

    def _extract_entry_title(self, *, article: Tag, index_entry: IndexEntry) -> str:
        title_node = article.select_one("h1")
        if title_node is not None:
            title = self._normalize_text(title_node.get_text(" ", strip=True))
            if title:
                return title
        return index_entry.title

    def _extract_content_text(self, container: Tag) -> str:
        text = container.get_text("\n", strip=True)
        lines = [self._normalize_text(line) for line in text.splitlines()]
        filtered = [line for line in lines if line]
        content = "\n".join(filtered)
        if not content:
            raise ParsingError("Entry content container is empty")
        return content

    def _extract_iocs(self, container: Tag) -> list[IOC]:
        ioc_heading = self._find_ioc_heading(container)
        if ioc_heading is None:
            return []

        current_kind: str | None = None
        seen_pairs: set[tuple[str, str]] = set()
        results: list[IOC] = []
        start_level = self._heading_level(ioc_heading)

        for block in self._iter_ioc_section_blocks(ioc_heading=ioc_heading):
            if block.name in {"h2", "h3", "h4", "h5", "h6"}:
                heading_text = self._normalize_text(block.get_text(" ", strip=True))
                heading_level = self._heading_level(block)
                lowered = heading_text.casefold()

                if heading_level <= start_level and lowered != self._IOC_SECTION_TITLE:
                    if any(marker in lowered for marker in self._STOP_SECTION_MARKERS):
                        break
                    break

                if heading_level > start_level:
                    current_kind = self._canonical_ioc_kind(heading_text)
                continue

            if current_kind is None:
                continue

            for value in self._extract_values_from_block(current_kind=current_kind, block=block):
                key = (current_kind, value)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                results.append(IOC(kind=current_kind, value=value))

        return results

    def _iter_ioc_section_blocks(self, *, ioc_heading: Tag) -> Iterable[Tag]:
        """
        1275.ru places IOC data inside a wrapper like:
            <h2>Индикаторы компрометации</h2>
            <div class="tabcontent"> ... <h3>IPv4</h3><ul>...</ul> ... </div>

        So walking only ioc_heading.next_siblings misses nested h3/ul pairs.
        If the immediate sibling is a tabcontent wrapper, iterate over its
        direct children; otherwise fall back to plain sibling traversal.
        """
        wrapper = self._next_meaningful_sibling(ioc_heading)
        if wrapper is not None and wrapper.name == "div" and self._is_tab_content(wrapper):
            for child in wrapper.children:
                if isinstance(child, Tag):
                    yield child
            return

        for sibling in ioc_heading.next_siblings:
            if isinstance(sibling, Tag):
                yield sibling

    def _next_meaningful_sibling(self, node: Tag) -> Tag | None:
        for sibling in node.next_siblings:
            if isinstance(sibling, Tag):
                return sibling
            if isinstance(sibling, NavigableString) and self._normalize_text(str(sibling)):
                break
        return None

    def _is_tab_content(self, node: Tag) -> bool:
        classes = {cls.casefold() for cls in node.get("class", [])}
        return "tabcontent" in classes


    def _find_ioc_heading(self, container: Tag) -> Tag | None:
        for heading in container.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            text = self._normalize_text(heading.get_text(" ", strip=True)).casefold()
            if text == self._IOC_SECTION_TITLE:
                return heading
        return None

    def _extract_values_from_block(self, *, current_kind: str, block: Tag) -> list[str]:
        if self._contains_protected_marker(block.get_text(" ", strip=True)):
            return []

        texts: list[str] = []
        if block.name in {"ul", "ol"}:
            texts.extend(
                self._normalize_text(li.get_text(" ", strip=True))
                for li in block.find_all("li", recursive=False)
            )
        elif block.name in {"pre", "code"}:
            texts.extend(self._split_multiline_values(block.get_text("\n", strip=True)))
        else:
            for selector in ("li", "code", "pre", "p"):
                elements = block.select(selector)
                if elements:
                    texts.extend(
                        self._normalize_text(element.get_text(" ", strip=True))
                        for element in elements
                    )
                    break
            if not texts:
                text = self._normalize_text(block.get_text("\n", strip=True))
                texts.extend(self._split_multiline_values(text))

        values: list[str] = []
        for text in texts:
            if not text or self._contains_protected_marker(text):
                continue
            extracted = self._extract_values_from_text(current_kind=current_kind, text=text)
            if extracted:
                values.extend(extracted)
            elif block.name in {"ul", "ol", "pre", "code"}:
                values.append(text)

        return values

    def _extract_values_from_text(self, *, current_kind: str, text: str) -> list[str]:
        for pattern, marker in self._IOC_PATTERNS:
            if marker != current_kind:
                continue
            return [self._normalize_text(match) for match in pattern.findall(text)]

        candidates = self._split_multiline_values(text)
        return [candidate for candidate in candidates if candidate and not self._contains_protected_marker(candidate)]

    def _split_multiline_values(self, text: str) -> list[str]:
        return [
            self._normalize_text(part)
            for part in re.split(r"[\r\n]+", text)
            if self._normalize_text(part)
        ]

    def _contains_protected_marker(self, text: str) -> bool:
        lowered = self._normalize_text(text).casefold()
        return any(marker in lowered for marker in self._PROTECTED_TEXT_MARKERS)

    def _canonical_ioc_kind(self, heading_text: str) -> str:
        lowered = self._normalize_text(heading_text).casefold()
        for alias, canonical in self._IOC_KIND_ALIASES:
            if alias in lowered:
                return canonical
        return lowered

    def _heading_level(self, heading: Tag) -> int:
        if heading.name and heading.name.startswith("h") and heading.name[1:].isdigit():
            return int(heading.name[1:])
        return 99

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()
