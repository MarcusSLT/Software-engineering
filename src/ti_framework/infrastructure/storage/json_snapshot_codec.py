"""JSON codec for snapshot persistence."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

from ti_framework.domain.models import Snapshot


class JsonSnapshotCodec:
    """Serialize and deserialize Snapshot objects to JSON-compatible dicts."""

    SCHEMA_VERSION = 2

    def encode(self, snapshot: Snapshot) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "collected_at": snapshot.collected_at.isoformat(),
            "source_url": snapshot.source_url,
            "source_name": snapshot.source_name,
            "snapshot_kind": snapshot.snapshot_kind,
            "sha256_hex": snapshot.sha256_hex,
            "data_base64": base64.b64encode(snapshot.data).decode("ascii"),
        }

    def decode(self, payload: dict[str, Any]) -> Snapshot:
        data_base64 = payload["data_base64"]
        data = base64.b64decode(data_base64.encode("ascii"))

        return Snapshot(
            collected_at=datetime.fromisoformat(payload["collected_at"]),
            source_url=payload["source_url"],
            source_name=payload["source_name"],
            snapshot_kind=payload.get("snapshot_kind", "index"),
            data=data,
        )
