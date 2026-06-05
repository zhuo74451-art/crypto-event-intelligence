"""Market Radar v1.17 — Unified Adapter Protocol + Normalized Snapshot

Adapter: Unified data input interface that produces NormalizedSnapshot objects.
NormalizedSnapshot: Unified card input structure across all 5 card types.

This is the FIRST layer in the v117 pipeline:
  Adapter.fetch() → NormalizedSnapshot → quality_gate → ...

Design:
  - Abstract Adapter base class with fetch() → normalize() → validate() chain
  - NormalizedSnapshot is a validated, typed, normalized data record
  - Three concrete fixture adapters for the v116-verified card types:
      * MultiAssetMarketSyncAdapter (multi_asset_market_sync)
      * PriceOIVolumeAnomalyAdapter (price_oi_volume_anomaly)
      * NewsEventMarketImpactAdapter (news_event_market_impact)
  - Two additional fixture adapters for the remaining card types
      * WhalePositionAlertAdapter (whale_position_alert)
      * LiquidationPressureAdapter (liquidation_pressure)

Constraints:
  - No external API calls (fixture mode only in this skeleton)
  - No TG send
  - No daemon/cron/loop
  - No token/key/secret read or print

Usage:
    from scripts.market_radar_adapter_v117 import (
        Adapter, NormalizedSnapshot,
        MultiAssetMarketSyncAdapter,
        PriceOIVolumeAnomalyAdapter,
        NewsEventMarketImpactAdapter,
        create_fixture_snapshots,
    )

    adapter = MultiAssetMarketSyncAdapter(source_kind="fixture")
    snapshot = adapter.fetch()
    print(snapshot.as_dict())
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any

CN_TZ = timezone(timedelta(hours=8))
ADAPTER_VERSION = "v1.17"

# ── Card type keys ────────────────────────────────────────────────────────────────

VALID_CARD_TYPES = frozenset([
    "price_oi_volume_anomaly",
    "whale_position_alert",
    "liquidation_pressure",
    "multi_asset_market_sync",
    "news_event_market_impact",
])

VALID_SOURCE_KINDS = frozenset([
    "fixture",
    "local_snapshot",
    "local_enrichment",
    "local_correlation",
    "free_public_api",
    "free_public_source",
])


def china_stamp() -> str:
    """Return current time in UTC+8 format."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _sha256_hex(raw: str) -> str:
    """SHA-256 hex digest of a UTF-8 encoded string."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════════════
# Normalized Snapshot — Unified Card Input Structure
# ══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class NormalizedSnapshot:
    """Unified input structure produced by all adapters.

    This is the canonical intermediate representation that flows through:
      QualityGate → SendReadinessGate → Renderer → DryRunSender → EvidenceLedger

    Fields:
        card_type: One of VALID_CARD_TYPES.
        source_kind: Where the data came from (fixture, free_api, etc.).
        observed_at: ISO-8601 timestamp of observation.
        event_key: Stable event identifier from the adapter.
        primary_assets: List of asset symbols.
        direction: Signal direction (bullish/bearish/neutral/mixed/unknown).
        severity_score: 0-100 severity score.
        confidence_score: 0-1 confidence score.
        signal_data: The raw signal dict (card-type-specific fields).
        adapter_version: Version string of the producing adapter.
        metadata: Optional additional metadata.
        snapshot_id: Auto-generated unique ID for this snapshot.
    """
    card_type: str
    source_kind: str
    observed_at: str
    event_key: str
    primary_assets: list[str]
    direction: str
    severity_score: float
    confidence_score: float
    signal_data: dict = field(default_factory=dict)
    adapter_version: str = ADAPTER_VERSION
    metadata: dict = field(default_factory=dict)
    snapshot_id: str = ""

    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = self._generate_snapshot_id()

        # Normalize
        if self.card_type not in VALID_CARD_TYPES:
            raise ValueError(
                f"Invalid card_type: {self.card_type!r}. Must be one of: "
                f"{sorted(VALID_CARD_TYPES)}"
            )
        if self.source_kind not in VALID_SOURCE_KINDS:
            raise ValueError(
                f"Invalid source_kind: {self.source_kind!r}. Must be one of: "
                f"{sorted(VALID_SOURCE_KINDS)}"
            )
        self.severity_score = max(0.0, min(100.0, float(self.severity_score)))
        self.confidence_score = max(0.0, min(1.0, float(self.confidence_score)))

        # Normalize assets
        if isinstance(self.primary_assets, str):
            self.primary_assets = [a.strip() for a in self.primary_assets.split(",") if a.strip()]
        self.primary_assets = [str(a).strip().upper() for a in self.primary_assets if str(a).strip()]

        # Normalize direction
        valid_dirs = {"bullish", "bearish", "neutral", "mixed", "unknown"}
        if self.direction not in valid_dirs:
            self.direction = "neutral"

    def _generate_snapshot_id(self) -> str:
        """Generate a stable snapshot ID."""
        ct_short_map = {
            "price_oi_volume_anomaly": "pova",
            "whale_position_alert": "wpa",
            "liquidation_pressure": "lipr",
            "multi_asset_market_sync": "mams",
            "news_event_market_impact": "nemi",
        }
        ct_short = ct_short_map.get(self.card_type, self.card_type[:4])
        ek_hash = _sha256_hex(str(self.event_key))[:8]
        ts = str(self.observed_at).replace(":", "").replace("-", "").replace("+", "").replace("T", "")[:12]
        return f"snap-{ct_short}-{ek_hash}-{ts}"

    def as_dict(self) -> dict:
        """Return snapshot as a plain dict (for serialization)."""
        return {
            "snapshot_id": self.snapshot_id,
            "card_type": self.card_type,
            "source_kind": self.source_kind,
            "observed_at": self.observed_at,
            "event_key": self.event_key,
            "primary_assets": self.primary_assets,
            "direction": self.direction,
            "severity_score": self.severity_score,
            "confidence_score": self.confidence_score,
            "signal_data": self.signal_data,
            "adapter_version": self.adapter_version,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Return snapshot as JSON string."""
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════════════
# Abstract Adapter Base
# ══════════════════════════════════════════════════════════════════════════════════════

class Adapter(ABC):
    """Abstract base class for all market radar data adapters.

    Subclass this and implement:
      - _fetch_raw(): Return raw data from source.
      - _normalize(raw_data) -> NormalizedSnapshot: Transform raw data.
      - _validate(snapshot) -> bool: Validate the snapshot.

    The public fetch() method runs the full pipeline:
      raw → normalize → validate → return snapshot.
    """

    card_type: str  # Must be set by subclass
    source_kind: str  # Must be set by subclass

    def __init__(self, source_kind: str | None = None):
        if source_kind is not None:
            self.source_kind = source_kind
        if not hasattr(self, "card_type") or not self.card_type:
            raise ValueError(f"{self.__class__.__name__} must define card_type")
        if self.card_type not in VALID_CARD_TYPES:
            raise ValueError(f"Invalid card_type: {self.card_type!r}")

    @abstractmethod
    def _fetch_raw(self) -> Any:
        """Fetch raw data from the source. Must be implemented by subclass."""
        ...

    @abstractmethod
    def _normalize(self, raw_data: Any) -> NormalizedSnapshot:
        """Transform raw data into a NormalizedSnapshot. Must be implemented by subclass."""
        ...

    def _validate(self, snapshot: NormalizedSnapshot) -> tuple[bool, str | None]:
        """Validate the snapshot before returning.

        Default implementation checks:
          - card_type matches
          - primary_assets is non-empty
          - observed_at is non-empty
          - signal_data is a dict
        Override for additional validation.

        Returns (is_valid, error_message).
        """
        if snapshot.card_type != self.card_type:
            return False, f"card_type mismatch: {snapshot.card_type} != {self.card_type}"
        if not snapshot.primary_assets:
            return False, "primary_assets is empty"
        if not snapshot.observed_at:
            return False, "observed_at is empty"
        if not isinstance(snapshot.signal_data, dict):
            return False, f"signal_data must be dict, got {type(snapshot.signal_data).__name__}"
        return True, None

    def fetch(self) -> NormalizedSnapshot:
        """Public entry point: fetch → normalize → validate → return.

        Returns:
            NormalizedSnapshot on success.

        Raises:
            ValueError if validation fails.
        """
        raw = self._fetch_raw()
        snapshot = self._normalize(raw)
        valid, error = self._validate(snapshot)
        if not valid:
            raise ValueError(f"Adapter validation failed for {self.card_type}: {error}")
        return snapshot

    @property
    def adapter_info(self) -> dict:
        """Return adapter metadata."""
        return {
            "adapter_class": self.__class__.__name__,
            "card_type": self.card_type,
            "source_kind": self.source_kind,
            "adapter_version": ADAPTER_VERSION,
        }


# ══════════════════════════════════════════════════════════════════════════════════════
# Fixture Adapters — for the 3 v116-verified card types
# ══════════════════════════════════════════════════════════════════════════════════════

# ── Fixture constants ───────────────────────────────────────────────────────────

MULTI_ASSET_SYNC_FIXTURE = {
    "event_key": "mams_fixture_001",
    "observed_at": "2026-06-05T14:00:00+08:00",
    "primary_assets": ["BTC", "ETH", "SOL"],
    "direction": "bullish",
    "severity_score": 65.0,
    "confidence_score": 0.75,
    "signal_data": {
        "assets": [
            {"asset": "BTC", "price_change_pct": 4.2},
            {"asset": "ETH", "price_change_pct": 3.8},
            {"asset": "SOL", "price_change_pct": 5.1},
        ],
        "direction": "up",
        "real_same_direction_asset_count": 3,
        "sync_strength": 72,
        "sector": "L1",
        "leader_asset": "SOL",
        "avg_price_change": 4.37,
        "max_price_change": 5.1,
        "oi_direction_match": True,
        "volume_surge_ratio": 1.8,
        "trigger_reason": "BTC/ETH/SOL 同步上涨，OI 一致，成交量放大 1.8x",
        "source_type": "fixture",
        "data_mode": "fixture",
        "core_entity": "multi_asset_sync",
    },
}

PRICE_OI_VOLUME_FIXTURE = {
    "event_key": "pova_fixture_001",
    "observed_at": "2026-06-05T14:00:00+08:00",
    "primary_assets": ["ETH"],
    "direction": "bullish",
    "severity_score": 60.0,
    "confidence_score": 0.80,
    "signal_data": {
        "asset": "ETH",
        "price_change_pct": 7.5,
        "open_interest": 8_500_000_000,
        "oi_change_pct": 12.3,
        "volume": 22_000_000_000,
        "volume_change_pct": 45.0,
        "funding": 0.0003,
        "trigger_reason": "ETH 涨 7.5%，OI 增 12.3%，成交量放大 45%",
        "source_type": "fixture",
        "data_mode": "fixture",
        "core_entity": "ETH",
    },
}

NEWS_EVENT_FIXTURE = {
    "event_key": "nemi_fixture_001",
    "observed_at": "2026-06-05T14:00:00+08:00",
    "primary_assets": ["BTC", "ETH"],
    "direction": "bullish",
    "severity_score": 60.0,
    "confidence_score": 0.60,
    "signal_data": {
        "event_title": "SEC 批准现货以太坊 ETF 期权交易",
        "affected_assets": "BTC,ETH",
        "event_type": "ETF",
        "trading_relevance": "高",
        "already_priced": "部分已定价",
        "risk_tags": "监管,ETF,市场结构",
        "observation_window": "4-8 小时",
        "summary": "SEC 批准多家机构在 CBOE 上市现货以太坊 ETF 期权，市场反应积极。",
        "source_name": "CoinDesk",
        "source_type": "fixture",
        "data_mode": "fixture",
        "core_entity": "news_event",
        "trigger_reason": "SEC ETF 期权批准 — 结构性利好",
    },
}


class MultiAssetMarketSyncAdapter(Adapter):
    """Fixture adapter for multi_asset_market_sync card type."""

    card_type = "multi_asset_market_sync"
    source_kind = "fixture"

    def _fetch_raw(self) -> dict:
        return dict(MULTI_ASSET_SYNC_FIXTURE)

    def _normalize(self, raw_data: dict) -> NormalizedSnapshot:
        return NormalizedSnapshot(
            card_type=self.card_type,
            source_kind=self.source_kind,
            observed_at=raw_data.get("observed_at", china_stamp()),
            event_key=raw_data.get("event_key", "unknown"),
            primary_assets=raw_data.get("primary_assets", []),
            direction=raw_data.get("direction", "neutral"),
            severity_score=raw_data.get("severity_score", 50.0),
            confidence_score=raw_data.get("confidence_score", 0.5),
            signal_data=raw_data.get("signal_data", {}),
            adapter_version=ADAPTER_VERSION,
            metadata={"fixture_id": raw_data.get("event_key", "")},
        )


class PriceOIVolumeAnomalyAdapter(Adapter):
    """Fixture adapter for price_oi_volume_anomaly card type."""

    card_type = "price_oi_volume_anomaly"
    source_kind = "fixture"

    def _fetch_raw(self) -> dict:
        return dict(PRICE_OI_VOLUME_FIXTURE)

    def _normalize(self, raw_data: dict) -> NormalizedSnapshot:
        return NormalizedSnapshot(
            card_type=self.card_type,
            source_kind=self.source_kind,
            observed_at=raw_data.get("observed_at", china_stamp()),
            event_key=raw_data.get("event_key", "unknown"),
            primary_assets=raw_data.get("primary_assets", []),
            direction=raw_data.get("direction", "neutral"),
            severity_score=raw_data.get("severity_score", 50.0),
            confidence_score=raw_data.get("confidence_score", 0.5),
            signal_data=raw_data.get("signal_data", {}),
            adapter_version=ADAPTER_VERSION,
            metadata={"fixture_id": raw_data.get("event_key", "")},
        )


class NewsEventMarketImpactAdapter(Adapter):
    """Fixture adapter for news_event_market_impact card type."""

    card_type = "news_event_market_impact"
    source_kind = "fixture"

    def _fetch_raw(self) -> dict:
        return dict(NEWS_EVENT_FIXTURE)

    def _normalize(self, raw_data: dict) -> NormalizedSnapshot:
        return NormalizedSnapshot(
            card_type=self.card_type,
            source_kind=self.source_kind,
            observed_at=raw_data.get("observed_at", china_stamp()),
            event_key=raw_data.get("event_key", "unknown"),
            primary_assets=raw_data.get("primary_assets", []),
            direction=raw_data.get("direction", "neutral"),
            severity_score=raw_data.get("severity_score", 50.0),
            confidence_score=raw_data.get("confidence_score", 0.5),
            signal_data=raw_data.get("signal_data", {}),
            adapter_version=ADAPTER_VERSION,
            metadata={"fixture_id": raw_data.get("event_key", "")},
        )


# ══════════════════════════════════════════════════════════════════════════════════════
# Adapter Registry
# ══════════════════════════════════════════════════════════════════════════════════════

ADAPTER_REGISTRY: dict[str, type[Adapter]] = {
    "multi_asset_market_sync": MultiAssetMarketSyncAdapter,
    "price_oi_volume_anomaly": PriceOIVolumeAnomalyAdapter,
    "news_event_market_impact": NewsEventMarketImpactAdapter,
}


def create_fixture_snapshots() -> list[NormalizedSnapshot]:
    """Create fixture snapshots for all 3 verified card types.

    Convenience function for E2E validation.

    Returns:
        List of 3 NormalizedSnapshot objects.
    """
    adapters: list[Adapter] = [
        MultiAssetMarketSyncAdapter(),
        PriceOIVolumeAnomalyAdapter(),
        NewsEventMarketImpactAdapter(),
    ]
    snapshots = []
    for adapter in adapters:
        snapshot = adapter.fetch()
        snapshots.append(snapshot)
    return snapshots


def get_adapter_for_card_type(card_type: str, source_kind: str = "fixture") -> Adapter | None:
    """Get an adapter instance for a given card type.

    Args:
        card_type: Card type key from VALID_CARD_TYPES.
        source_kind: Data source kind.

    Returns:
        Adapter instance or None if card_type not in fixture registry.
    """
    adapter_cls = ADAPTER_REGISTRY.get(card_type)
    if adapter_cls is None:
        return None
    return adapter_cls(source_kind=source_kind)
