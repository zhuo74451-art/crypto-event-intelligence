"""Local caching layer for HTTP responses."""

from __future__ import annotations
import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CachedResponse:
    """A cached HTTP response."""
    url: str
    etag: str
    last_modified: str
    body: bytes
    headers: dict
    cached_at: str  # ISO format timestamp
    content_hash: str


class AcquisitionCache(ABC):
    """Abstract cache for HTTP responses."""

    @abstractmethod
    def get(self, url: str, etag: str | None = None, last_modified: str | None = None) -> CachedResponse | None:
        ...

    @abstractmethod
    def set(self, url: str, response: CachedResponse, etag: str | None = None, last_modified: str | None = None) -> None:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...

    @abstractmethod
    def has(self, url: str) -> bool:
        ...

    def _make_key(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()


class LocalFileCache(AcquisitionCache):
    """File-system backed cache using JSON index + body files."""

    def __init__(self, cache_dir: str | Path) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._cache_dir / "_index.json"
        self._index: dict[str, dict] = {}
        self._load_index()

    def _load_index(self) -> None:
        if self._index_path.exists():
            try:
                with open(self._index_path, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception:
                self._index = {}

    def _save_index(self) -> None:
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False)

    def _body_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.bin"

    def get(self, url: str, etag: str | None = None, last_modified: str | None = None) -> CachedResponse | None:
        key = self._make_key(url)
        meta = self._index.get(key)
        if meta is None:
            return None
        body_file = self._body_path(key)
        if not body_file.exists():
            return None
        try:
            body = body_file.read_bytes()
        except Exception:
            return None
        return CachedResponse(
            url=meta["url"],
            etag=meta.get("etag", ""),
            last_modified=meta.get("last_modified", ""),
            body=body,
            headers=meta.get("headers", {}),
            cached_at=meta.get("cached_at", ""),
            content_hash=meta.get("content_hash", ""),
        )

    def set(self, url: str, response: CachedResponse, etag: str | None = None, last_modified: str | None = None) -> None:
        key = self._make_key(url)
        self._index[key] = {
            "url": response.url,
            "etag": response.etag,
            "last_modified": response.last_modified,
            "headers": response.headers,
            "cached_at": response.cached_at,
            "content_hash": response.content_hash,
        }
        self._body_path(key).write_bytes(response.body)
        self._save_index()

    def clear(self) -> None:
        for item in self._cache_dir.iterdir():
            if item.is_file() and item.name != "_index.json":
                try:
                    item.unlink()
                except Exception:
                    pass
        self._index = {}
        self._save_index()

    def has(self, url: str) -> bool:
        key = self._make_key(url)
        return key in self._index and self._body_path(key).exists()


class InMemoryCache(AcquisitionCache):
    """In-memory dict-backed cache — suitable for testing."""

    def __init__(self) -> None:
        self._store: dict[str, CachedResponse] = {}

    def get(self, url: str, etag: str | None = None, last_modified: str | None = None) -> CachedResponse | None:
        key = self._make_key(url)
        return self._store.get(key)

    def set(self, url: str, response: CachedResponse, etag: str | None = None, last_modified: str | None = None) -> None:
        key = self._make_key(url)
        self._store[key] = response

    def clear(self) -> None:
        self._store.clear()

    def has(self, url: str) -> bool:
        key = self._make_key(url)
        return key in self._store


class NoOpCache(AcquisitionCache):
    """Passthrough cache — never caches anything."""

    def get(self, url: str, etag: str | None = None, last_modified: str | None = None) -> CachedResponse | None:
        return None

    def set(self, url: str, response: CachedResponse, etag: str | None = None, last_modified: str | None = None) -> None:
        pass

    def clear(self) -> None:
        pass

    def has(self, url: str) -> bool:
        return False
