"""Shared adapter models for Window 4 external adapters."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class AdapterHealth:
    """Health status of a single adapter data source."""
    source: str
    available: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    checked_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdapterProvenance:
    """Provenance information for an adapter result."""
    source: str  # "sdk" | "raw_http_fallback" | "fixture" | "unavailable"
    method: str
    endpoint: Optional[str] = None
    latency_ms: Optional[float] = None
    healthy: bool = True
    detail: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class AdapterError:
    """Structured adapter-level error."""
    code: str
    message: str
    detail: Optional[str] = None
    source: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class AdapterResult:
    """Generic adapter result envelope."""
    ok: bool
    data: Any = None
    provenance: Optional[AdapterProvenance] = None
    error: Optional[AdapterError] = None

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"ok": self.ok}
        if self.data is not None:
            d["data"] = self.data
        if self.provenance is not None:
            d["provenance"] = self.provenance.as_dict()
        if self.error is not None:
            d["error"] = self.error.as_dict()
        return d
