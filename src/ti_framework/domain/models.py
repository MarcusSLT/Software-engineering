"""Core domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import Literal
from urllib.parse import urlparse

from .exceptions import SnapshotValidationError, SourceValidationError


SnapshotKind = Literal["index", "entry"]
_ALLOWED_SNAPSHOT_KINDS: frozenset[str] = frozenset({"index", "entry"})


def _validate_http_url(value: str, field_name: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be a valid HTTP/HTTPS URL")


def _validate_snapshot_kind(value: str) -> None:
    if value not in _ALLOWED_SNAPSHOT_KINDS:
        raise ValueError(
            f"snapshot_kind must be one of {sorted(_ALLOWED_SNAPSHOT_KINDS)}, got {value!r}"
        )


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Immutable snapshot of raw data fetched from a source."""

    collected_at: datetime
    source_url: str
    source_name: str
    data: bytes
    snapshot_kind: SnapshotKind = "index"
    sha256_hex: str = field(init=False)

    def __post_init__(self) -> None:
        if self.collected_at.tzinfo is None:
            raise SnapshotValidationError("collected_at must be timezone-aware")
        if not self.source_name.strip():
            raise SnapshotValidationError("source_name must not be empty")

        try:
            _validate_http_url(self.source_url, "source_url")
            _validate_snapshot_kind(self.snapshot_kind)
        except ValueError as exc:
            raise SnapshotValidationError(str(exc)) from exc

        if not isinstance(self.data, (bytes, bytearray, memoryview)):
            raise SnapshotValidationError("data must be bytes-like")

        payload = bytes(self.data)
        object.__setattr__(self, "data", payload)
        object.__setattr__(self, "sha256_hex", sha256(payload).hexdigest())


@dataclass(frozen=True, slots=True)
class Source:
    """Fetch target declaration for an index page or a concrete publication page."""

    name: str
    index_url: str
    snapshot_kind: SnapshotKind = "index"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise SourceValidationError("name must not be empty")

        try:
            _validate_http_url(self.index_url, "index_url")
            _validate_snapshot_kind(self.snapshot_kind)
        except ValueError as exc:
            raise SourceValidationError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class SnapshotHandle:
    """Reference to a persisted snapshot."""

    locator: str


@dataclass(frozen=True, slots=True)
class BundleHandle:
    """Reference to a persisted STIX bundle."""

    locator: str


@dataclass(frozen=True, slots=True)
class PreprocessedData:
    """Parser-ready representation restored from a persisted snapshot."""

    collected_at: datetime
    source_url: str
    source_name: str
    snapshot_kind: SnapshotKind
    text: str
    snapshot_locator: str


@dataclass(frozen=True, slots=True)
class IndexEntry:
    """Minimal result of parsing an index snapshot."""

    title: str
    publication_url: str
    source_name: str
    index_source_url: str
    indexed_at: datetime

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.source_name.strip():
            raise ValueError("source_name must not be empty")
        if self.indexed_at.tzinfo is None:
            raise ValueError("indexed_at must be timezone-aware")

        try:
            _validate_http_url(self.publication_url, "publication_url")
            _validate_http_url(self.index_source_url, "index_source_url")
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class IOC:
    """Single indicator of compromise extracted from a publication page."""

    kind: str
    value: str

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("kind must not be empty")
        if not self.value.strip():
            raise ValueError("value must not be empty")


@dataclass(frozen=True, slots=True)
class Entry:
    """Minimal result of parsing a concrete publication page."""

    title: str
    content: str
    source_url: str
    source_name: str
    collected_at: datetime
    iocs: tuple[IOC, ...] = ()

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.content.strip():
            raise ValueError("content must not be empty")
        if not self.source_name.strip():
            raise ValueError("source_name must not be empty")
        if self.collected_at.tzinfo is None:
            raise ValueError("collected_at must be timezone-aware")

        try:
            _validate_http_url(self.source_url, "source_url")
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class FetchedEntry:
    """Result of fetching and persisting a concrete publication page snapshot."""

    index_entry: IndexEntry
    snapshot_handle: SnapshotHandle
