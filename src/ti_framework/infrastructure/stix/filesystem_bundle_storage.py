"""Filesystem-backed storage for STIX bundles."""

from __future__ import annotations

from pathlib import Path

from stix2.v21 import Bundle

from ti_framework.domain.exceptions import BundleStorageError
from ti_framework.domain.models import BundleHandle
from ti_framework.ports.bundle_storage import BundleStorage


class FileSystemBundleStorage(BundleStorage):
    """Persist STIX bundles as formatted JSON files."""

    def __init__(self, root_dir: str | Path) -> None:
        self._root_dir = Path(root_dir)

    def save(self, bundle: Bundle, *, source_name: str) -> BundleHandle:
        safe_source_name = source_name.strip().replace(" ", "_")
        target_dir = self._root_dir / safe_source_name
        target_dir.mkdir(parents=True, exist_ok=True)

        path = target_dir / f"{bundle.id}.bundle.json"
        try:
            path.write_text(bundle.serialize(pretty=True), encoding="utf-8")
        except OSError as exc:
            raise BundleStorageError(f"Failed to save STIX bundle to {path}: {exc}") from exc

        return BundleHandle(locator=str(path))