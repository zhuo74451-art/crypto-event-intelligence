"""HTTP response handling — safe header redaction and structured response."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

SAFE_HEADERS: frozenset[str] = frozenset({
    "content-type",
    "content-length",
    "etag",
    "last-modified",
    "date",
    "cache-control",
    "location",
})


def redact_headers(raw_headers: dict) -> dict:
    """Return a new dict with only SAFE_HEADERS, keys lowercased."""
    return {
        k.lower(): v
        for k, v in raw_headers.items()
        if k.lower() in SAFE_HEADERS
    }


@dataclass
class HttpResponse:
    """A safe, redacted HTTP response."""
    status: int
    headers: dict
    body: bytes
    encoding: str = "utf-8"
    elapsed_ms: float = 0.0
    from_cache: bool = False
    etag: str = ""
    last_modified: str = ""


_SECRET_PATTERNS = frozenset({
    "secret", "token", "key", "password", "authorization", "cookie",
})


def _matches_secret(key: str) -> bool:
    lowered = key.lower().replace("-", "").replace("_", "")
    return any(p in lowered for p in _SECRET_PATTERNS)


def redact_sensitive_fields(d: dict) -> dict:
    """Remove any fields whose key contains secret, token, key, password, authorization, or cookie (case-insensitive)."""
    return {k: v for k, v in d.items() if not _matches_secret(k)}
