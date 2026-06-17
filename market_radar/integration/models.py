"""Integration layer data models — no-send one-shot pipeline.

These are Integration-owned types that aggregate results from W2/W3/W4/W5
without duplicating Lane business models.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_run_id() -> str:
    return f"os-{uuid.uuid4().hex[:12]}"


@dataclass
class SourceRunStatus:
    """Health/provenance of a single data source within a run."""
    source: str
    status: str  # "ok" | "degraded" | "unavailable"
    ok: bool
    latency_ms: Optional[float] = None
    provenance: Optional[str] = None
    error: Optional[str] = None
    detail: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class WhaleSnapshotResult:
    """Normalized whale position snapshot from HL adapter."""
    address: str
    ok: bool
    position_count: int
    positions: list[dict] = field(default_factory=list)
    changes: list[dict] = field(default_factory=list)
    alert_candidates: list[dict] = field(default_factory=list)
    is_baseline: bool = True
    error: Optional[str] = None


@dataclass
class MarketSnapshotResult:
    """Normalized market ticker snapshot."""
    symbol: str
    source: str
    ok: bool
    last_price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    provenance: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class FeedResult:
    """Feed aggregation result."""
    data_mode: str  # "fixture" | "live-public"
    live_count: int
    fixture_count: int
    research_count: int
    items: list[dict] = field(default_factory=list)
    status: str = "ok"
    error: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class IntegrationConfig:
    """Configuration for a single one-shot run."""
    mode: str = "fixture"  # "fixture" | "live-public"
    state_dir: str = "data/integration/state"
    output_dir: str = "data/integration/output"
    whale_address: str = ""
    exchange: str = "binance"
    timeout: float = 30.0
    no_send: bool = True
    # Feed provider config
    feed_enabled: bool = True
    feed_limit: int = 100
    feed_max_items: int = 500
    feed_timeout_seconds: float = 10.0
    feed_cursor_name: str = "published_at_backend"
    feed_cursor_state_file: str = "feed_cursor.json"
    feed_initial_since: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.no_send:
            raise ValueError("no_send must be True — sending is prohibited")
        if not 1 <= self.feed_limit <= 500:
            raise ValueError(f"feed_limit must be 1-500, got {self.feed_limit}")
        if not 1 <= self.feed_max_items <= 5000:
            raise ValueError(f"feed_max_items must be 1-5000, got {self.feed_max_items}")
        if self.feed_timeout_seconds <= 0:
            raise ValueError(f"feed_timeout_seconds must be > 0, got {self.feed_timeout_seconds}")
        if not self.feed_cursor_name:
            raise ValueError("feed_cursor_name must be non-empty")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IntegrationRunResult:
    """Complete result of one one-shot integration run."""
    run_id: str = field(default_factory=_new_run_id)
    started_at: str = field(default_factory=_utc_now)
    finished_at: Optional[str] = None
    status: str = "running"  # "completed" | "degraded" | "failed"
    data_mode: str = "fixture"
    no_send: bool = True
    scheduler_started: bool = False
    credentials_used: bool = False
    config: Optional[IntegrationConfig] = None
    sources: list[SourceRunStatus] = field(default_factory=list)
    whale: Optional[WhaleSnapshotResult] = None
    markets: list[MarketSnapshotResult] = field(default_factory=list)
    feed: Optional[FeedResult] = None
    alert_candidate_count: int = 0
    output_paths: list[str] = field(default_factory=list)
    state_db_paths: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    ccxt_preflight: Optional[dict] = None
    feed_summary: Optional[dict] = None

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "data_mode": self.data_mode,
            "no_send": self.no_send,
            "scheduler_started": self.scheduler_started,
            "credentials_used": self.credentials_used,
            "sources": [s.as_dict() for s in self.sources],
            "markets": [m.as_dict() for m in self.markets],
            "alert_candidate_count": self.alert_candidate_count,
            "output_paths": self.output_paths,
            "state_db_paths": self.state_db_paths,
            "errors": self.errors,
        }
        if self.config:
            d["config"] = self.config.as_dict()
        if self.whale:
            d["whale"] = {
                "address": self.whale.address,
                "ok": self.whale.ok,
                "position_count": self.whale.position_count,
                "change_count": len(self.whale.changes),
                "alert_candidate_count": len(self.whale.alert_candidates),
                "is_baseline": self.whale.is_baseline,
            }
            if self.whale.error:
                d["whale"]["error"] = self.whale.error
        if self.feed:
            d["feed"] = self.feed.as_dict()
        if self.feed_summary:
            d["feed_summary"] = self.feed_summary
        return d


@dataclass
class OneShotArtifactPaths:
    """Paths for artifacts produced by a single one-shot run."""
    report_json: str = ""
    workbench_html: str = ""
    source_health_db: str = ""
    run_history_db: str = ""
    whale_snapshot_json: str = ""
    market_snapshot_json: str = ""
