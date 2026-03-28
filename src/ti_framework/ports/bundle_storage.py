"""Bundle storage abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from stix2.v21 import Bundle


class BundleStorage(ABC):
    """Persist generated STIX bundles."""

    @abstractmethod
    def save(self, bundle: Bundle) -> Path:
        raise NotImplementedError