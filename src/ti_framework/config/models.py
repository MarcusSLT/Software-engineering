"""Configuration models."""

from __future__ import annotations

from dataclasses import dataclass

from ti_framework.domain.models import Source


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """Runtime configuration for a source pipeline."""

    name: str
    index_url: str
    parser_path: str
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if not self.parser_path.strip():
            raise ValueError("parser_path must not be empty")

    def to_source(self) -> Source:
        return Source(name=self.name, index_url=self.index_url)
