"""STIX bundle builder abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from stix2.v21 import Bundle

from ti_framework.domain.models import Entry


class StixBundleBuilder(ABC):
    """Build a STIX 2.1 bundle from parsed publication entries."""

    @abstractmethod
    def build(self, entries: Iterable[Entry]) -> Bundle | None:
        """Return a STIX bundle or None when there is nothing semantically valid to emit."""
        raise NotImplementedError