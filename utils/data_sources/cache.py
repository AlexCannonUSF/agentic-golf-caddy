"""Disk-backed JSON cache for external data sources."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from utils.config import cache_dir


class DiskCache:
    """Persist JSON-serializable payloads by source + logical key."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base_dir = Path(base_dir) if base_dir is not None else cache_dir("shared").parents[0]
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _source_dir(self, source: str) -> Path:
        path = self._base_dir / source
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _hash_key(key: dict[str, Any]) -> str:
        payload = json.dumps(key, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def path_for(self, source: str, key: dict[str, Any]) -> Path:
        """Return the on-disk path for the given source/key pair."""

        return self._source_dir(source) / f"{self._hash_key(key)}.json"

    def get(self, source: str, key: dict[str, Any]) -> Any | None:
        """Load a cached payload if present."""

        path = self.path_for(source, key)
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        return record.get("payload")

    def set(self, source: str, key: dict[str, Any], payload: Any) -> Path:
        """Store a payload and return the written path."""

        path = self.path_for(source, key)
        record = {"key": key, "payload": payload}
        path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
        return path

