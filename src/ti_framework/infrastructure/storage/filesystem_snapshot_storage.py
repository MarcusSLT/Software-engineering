"""Filesystem-based snapshot storage."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ti_framework.domain.exceptions import SnapshotNotFoundError, SnapshotStorageError
from ti_framework.domain.models import Snapshot, SnapshotHandle, SnapshotKind
from ti_framework.ports.storage import SnapshotStorage

_SCHEMA_VERSION = 2


class FileSystemSnapshotStorage(SnapshotStorage):
    """Persist snapshots as JSON files in a local directory tree."""

    def __init__(self, root_dir: str | Path) -> None:
        self._root_dir = Path(root_dir)

    def save(self, snapshot: Snapshot) -> SnapshotHandle:
        target_dir = self._snapshot_dir(snapshot.source_name, snapshot.snapshot_kind)
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = (
            f"{snapshot.collected_at:%Y%m%dT%H%M%S%f%z}_"
            f"{snapshot.sha256_hex}.snapshot.json"
        )
        path = target_dir / filename

        try:
            path.write_text(
                json.dumps(
                    self._encode_snapshot(snapshot),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            raise SnapshotStorageError(f"Failed to save snapshot to {path}: {exc}") from exc

        return SnapshotHandle(locator=str(path))

    def load(self, handle: SnapshotHandle) -> Snapshot:
        path = Path(handle.locator)
        if not path.exists():
            raise SnapshotNotFoundError(f"Snapshot not found: {path}")

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise SnapshotStorageError(f"Failed to read snapshot from {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise SnapshotStorageError(f"Snapshot file is not valid JSON: {path}") from exc

        try:
            return self._decode_snapshot(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise SnapshotStorageError(f"Snapshot JSON has invalid structure: {path}") from exc

    def delete(self, handle: SnapshotHandle) -> None:
        path = Path(handle.locator)
        if not path.exists():
            raise SnapshotNotFoundError(f"Snapshot not found: {path}")

        try:
            path.unlink()
            self._cleanup_empty_dirs(path.parent)
        except OSError as exc:
            raise SnapshotStorageError(f"Failed to delete snapshot {path}: {exc}") from exc

    def list_snapshots(
        self,
        source_name: str,
        snapshot_kind: SnapshotKind = "index",
    ) -> list[SnapshotHandle]:
        directory = self._snapshot_dir(source_name, snapshot_kind)
        if not directory.exists():
            return []

        files = sorted(path for path in directory.glob("*.snapshot.json") if path.is_file())
        return [SnapshotHandle(locator=str(path)) for path in files]

    def _snapshot_dir(self, source_name: str, snapshot_kind: SnapshotKind) -> Path:
        return self._root_dir / source_name.strip().replace(" ", "_") / snapshot_kind

    def _cleanup_empty_dirs(self, directory: Path) -> None:
        current = directory
        while current != self._root_dir and current.exists() and current.is_dir():
            if any(current.iterdir()):
                break
            current.rmdir()
            current = current.parent

    def _encode_snapshot(self, snapshot: Snapshot) -> dict[str, Any]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "collected_at": snapshot.collected_at.isoformat(),
            "source_url": snapshot.source_url,
            "source_name": snapshot.source_name,
            "snapshot_kind": snapshot.snapshot_kind,
            "sha256_hex": snapshot.sha256_hex,
            "data_base64": base64.b64encode(snapshot.data).decode("ascii"),
        }

    def _decode_snapshot(self, payload: dict[str, Any]) -> Snapshot:
        return Snapshot(
            collected_at=datetime.fromisoformat(payload["collected_at"]),
            source_url=payload["source_url"],
            source_name=payload["source_name"],
            snapshot_kind=payload.get("snapshot_kind", "index"),
            data=base64.b64decode(payload["data_base64"].encode("ascii")),
        )
