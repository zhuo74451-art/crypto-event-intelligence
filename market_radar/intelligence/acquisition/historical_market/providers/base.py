"""Base class and common utilities for historical market data providers."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..contracts import (
    DataQuality,
    MarketBarV1,
    DerivativeSnapshotV1,
    SourceSnapshotV1,
    utc_now,
    make_source_snapshot_id,
)


@dataclass
class ProviderResult:
    """Result of a provider fetch operation."""
    success: bool = False
    record_count: int = 0
    error_message: str = ""
    source_snapshot: Optional[SourceSnapshotV1] = None
    bars: list[MarketBarV1] = field(default_factory=list)
    derivatives: list[DerivativeSnapshotV1] = field(default_factory=list)


class BaseProvider(ABC):
    """Abstract base for all historical market data providers."""

    def __init__(
        self,
        cache_dir: str | Path,
        output_dir: str | Path,
        provider_name: str,
    ):
        self.provider_name = provider_name
        self.cache_dir = Path(cache_dir) / provider_name
        self.output_dir = Path(output_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @abstractmethod
    def list_instruments(self) -> list[dict[str, Any]]:
        """Return list of instrument metadata dicts."""
        ...

    @abstractmethod
    def fetch_bars(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        force: bool = False,
    ) -> ProviderResult:
        """Fetch OHLCV bars for a symbol."""
        ...

    def fetch_derivative_snapshots(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        force: bool = False,
    ) -> ProviderResult:
        """Fetch derivative snapshots (default: not available)."""
        return ProviderResult(success=True, record_count=0)

    def fetch_metadata(self) -> dict[str, Any]:
        """Return provider metadata."""
        return {
            "provider_name": self.provider_name,
            "version": "1.0.0",
        }

    # ------------------------------------------------------------------
    # Cache & retry helpers
    # ------------------------------------------------------------------

    def _cache_path(self, symbol: str, interval: str, suffix: str = ".json") -> Path:
        return self.cache_dir / f"{symbol}_{interval}{suffix}"

    def _load_cache(self, path: Path) -> Optional[list[dict[str, Any]]]:
        if not path.exists():
            return None
        try:
            if path.suffix == ".gz":
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    return [json.loads(line) for line in f if line.strip()]
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix == ".jsonl":
                    return [json.loads(line) for line in f if line.strip()]
                return json.load(f)
        except Exception:
            return None

    def _save_cache(self, path: Path, data: list[dict] | list[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".gz":
            with gzip.open(path, "wt", encoding="utf-8") as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
        elif path.suffix == ".jsonl":
            with open(path, "w", encoding="utf-8") as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)

    def _make_snapshot(
        self,
        url: str,
        data_type: str,
        success: bool,
        record_count: int = 0,
        error: str = "",
        content: str | None = None,
    ) -> SourceSnapshotV1:
        now = utc_now()
        content_hash = hashlib.sha256((content or "").encode()).hexdigest() if content else ""
        return SourceSnapshotV1(
            source_snapshot_id=make_source_snapshot_id(self.provider_name, url, now),
            source_provider=self.provider_name,
            url=url,
            retrieved_at_utc=now,
            source_data_type=data_type,
            success=success,
            error_message=error,
            record_count=record_count,
            content_hash=content_hash,
        )

    def _rate_limit(self, seconds: float = 0.5) -> None:
        time.sleep(seconds)

    def _utc_now_str(self) -> str:
        return utc_now()

    def _to_data_quality(self, tag: str) -> str:
        """Map internal quality tag to canonical DataQuality."""
        mapping = {
            "archive": DataQuality.EXACT_ARCHIVED.value,
            "api": DataQuality.EXACT_PUBLIC_API.value,
            "dataset": DataQuality.VERIFIED_PUBLIC_DATASET.value,
            "proxy": DataQuality.EXPLICIT_PROXY.value,
            "fallback": DataQuality.LOWER_FREQ_FALLBACK.value,
            "reconstructed": DataQuality.RECONSTRUCTED.value,
        }
        return mapping.get(tag, DataQuality.MISSING.value)
