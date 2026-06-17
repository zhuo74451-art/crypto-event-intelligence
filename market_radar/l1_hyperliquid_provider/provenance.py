"""L1 — Data provenance tracking.

Every piece of whale data must carry provenance recording
whether it came from live API, cached state, or fixture.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_to_ts(iso_str: str) -> float:
    """Parse ISO-8601 string to Unix timestamp. Returns 0 on failure."""
    try:
        s = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(s).timestamp()
    except (ValueError, TypeError):
        return 0.0


class DataMode(str, Enum):
    """Origin of data — never conflate these."""
    LIVE = "live"          # Fresh from API this run
    CACHED = "cached"      # From local state (previous run)
    FIXTURE = "fixture"    # Synthetic/deterministic test data


@dataclass
class ProvenanceRecord:
    """Provenance metadata for a single data fetch or position.

    Every WhalePosition and change carries one of these.
    """
    data_mode: DataMode
    source: str
    fetched_at_utc: str
    response_age_seconds: Optional[float] = None
    raw_artifact_ref: Optional[str] = None      # Path to raw JSON if saved
    sdk_version: Optional[str] = None            # e.g. "hyperliquid-python-sdk 0.23.0"
    endpoint: Optional[str] = None               # API endpoint used
    cache_age_seconds: Optional[float] = None    # If cached, how old

    def as_dict(self) -> dict:
        d = asdict(self)
        d["data_mode"] = self.data_mode.value
        return d


@dataclass
class SourceHealth:
    """Health status for a data source."""
    status: str  # healthy | degraded | unavailable
    source: str
    occurred_at_utc: str
    error_type: Optional[str] = None
    retryable: Optional[bool] = None
    message_summary: Optional[str] = None


def make_source_health(
    source: str,
    status: str,
    occurred_at_utc: Optional[str] = None,
    error_type: Optional[str] = None,
    retryable: Optional[bool] = None,
    message_summary: Optional[str] = None,
) -> dict:
    if occurred_at_utc is None:
        occurred_at_utc = utc_now_str()
    entry: dict[str, Any] = {
        "status": status,
        "source": source,
        "occurred_at_utc": occurred_at_utc,
    }
    if error_type is not None:
        entry["error_type"] = error_type
    if retryable is not None:
        entry["retryable"] = retryable
    if message_summary is not None:
        entry["message_summary"] = message_summary
    return entry


def make_provenance(
    data_mode: DataMode,
    source: str = "hyperliquid_info_public",
    endpoint: Optional[str] = None,
    raw_artifact_ref: Optional[str] = None,
    sdk_version: Optional[str] = None,
    response_age_seconds: Optional[float] = None,
    cache_age_seconds: Optional[float] = None,
) -> ProvenanceRecord:
    return ProvenanceRecord(
        data_mode=data_mode,
        source=source,
        fetched_at_utc=utc_now_str(),
        endpoint=endpoint,
        raw_artifact_ref=raw_artifact_ref,
        sdk_version=sdk_version,
        response_age_seconds=response_age_seconds,
        cache_age_seconds=cache_age_seconds,
    )
