"""Persistence port for STIX bundles."""

from __future__ import annotations

from abc import ABC, abstractmethod

from stix2.v21 import Bundle

from ti_framework.domain.models import BundleHandle


class BundleStorage(ABC):
    """Persist serialized STIX bundles."""

    @abstractmethod
    def save(self, bundle: Bundle, *, source_name: str) -> BundleHandle:
        raise NotImplementedError