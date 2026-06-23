"""Historical market data contracts.

Provides typed contracts for:
- MarketBarV1 (OHLCV bars)
- DerivativeSnapshotV1 (funding, OI, basis, liquidations)
- InstrumentRegistryV1 (instrument metadata)
- EventMarketWindowV1 (windows around macro events)
- MarketReactionLabelV1 (multi-horizon reaction labels)
- SourceSnapshotV1 (provenance records)

All IDs are deterministic SHA-256 prefixes — no UUID4, no randomness.
All timestamps are UTC ISO-8601 with Z suffix.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AssetClass(str, Enum):
    CRYPTO = "crypto"
    RATES = "rates"
    EQUITIES = "equities"
    COMMODITIES = "commodities"
    FX = "fx"
    MACRO = "macro"


class InstrumentType(str, Enum):
    SPOT = "spot"
    PERP_FUTURE = "perp_future"
    FUTURE = "future"
    OPTION = "option"
    ETF = "etf"
    INDEX = "index"
    YIELD = "yield"
    CASH = "cash"
    COMMODITY_FUTURE = "commodity_future"


class Interval(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class DataQuality(str, Enum):
    EXACT_ARCHIVED = "exact_archived_market_data"
    EXACT_PUBLIC_API = "exact_public_api_retrieval"
    VERIFIED_PUBLIC_DATASET = "verified_public_dataset"
    EXPLICIT_PROXY = "explicit_liquid_proxy"
    LOWER_FREQ_FALLBACK = "lower_frequency_fallback"
    RECONSTRUCTED = "reconstructed_with_limits"
    MISSING = "missing"


class LabelDirection(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class LabelAvailability(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    MINIMAL = "minimal"
    MISSING = "missing"


class ExactOrProxy(str, Enum):
    EXACT = "exact"
    PROXY = "proxy"


# ---------------------------------------------------------------------------
# Deterministic ID Generation
# ---------------------------------------------------------------------------

def _make_id(*parts: str, length: int = 24) -> str:
    """Generate a deterministic ID from ordered parts."""
    raw = "".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def make_bar_id(
    instrument_id: str,
    interval: str,
    open_time_utc: str,
    source_provider: str,
) -> str:
    return _make_id(instrument_id, interval, open_time_utc, source_provider)


def make_snapshot_id(
    instrument_id: str,
    observed_at_utc: str,
    source_provider: str,
) -> str:
    return _make_id(instrument_id, observed_at_utc, source_provider)


def make_window_id(
    event_id: str,
    instrument_id: str,
    event_time_utc: str,
    bar_interval: str,
    window_version: str = "1.0.0",
) -> str:
    return _make_id(event_id, instrument_id, event_time_utc, bar_interval, window_version)


def make_label_id(
    event_id: str,
    instrument_id: str,
    event_time_utc: str,
    calculation_version: str = "1.0.0",
) -> str:
    return _make_id(event_id, instrument_id, event_time_utc, calculation_version)


def make_source_snapshot_id(
    source_provider: str,
    url: str,
    retrieved_at_utc: str,
) -> str:
    return _make_id(source_provider, url, retrieved_at_utc)


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------

@dataclass
class MarketBarV1:
    """A single OHLCV market bar."""
    contract_name: str = "MarketBarV1"
    schema_version: str = "1.0.0"

    bar_id: str = ""
    instrument_id: str = ""
    symbol: str = ""
    venue: str = ""
    asset_class: str = AssetClass.CRYPTO.value
    instrument_type: str = InstrumentType.SPOT.value
    quote_currency: str = "USDT"

    interval: str = Interval.H1.value
    open_time_utc: str = ""
    close_time_utc: str = ""

    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    quote_volume: float = 0.0
    trade_count: int = 0

    is_adjusted: bool = False
    adjustment_method: str = ""
    is_proxy: bool = False
    proxy_for: str = ""

    source_provider: str = ""
    source_snapshot_id: str = ""
    retrieved_at_utc: str = ""
    first_seen_at_utc: str = ""

    data_quality: str = DataQuality.MISSING.value
    quality_flags: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "MarketBarV1":
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in fields(cls)}})


@dataclass
class DerivativeSnapshotV1:
    """A snapshot of crypto derivative market data."""
    contract_name: str = "DerivativeSnapshotV1"
    schema_version: str = "1.0.0"

    snapshot_id: str = ""
    instrument_id: str = ""
    symbol: str = ""
    venue: str = ""
    observed_at_utc: str = ""
    interval: str = Interval.H1.value

    mark_price: Optional[float] = None
    index_price: Optional[float] = None
    funding_rate: Optional[float] = None
    next_funding_at_utc: Optional[str] = None
    open_interest: Optional[float] = None
    open_interest_value: Optional[float] = None
    basis: Optional[float] = None
    premium_index: Optional[float] = None

    liquidation_long_volume: Optional[float] = None
    liquidation_short_volume: Optional[float] = None
    liquidation_is_proxy: bool = False
    liquidation_proxy_method: str = ""

    source_provider: str = ""
    source_snapshot_id: str = ""
    retrieved_at_utc: str = ""

    data_quality: str = DataQuality.MISSING.value
    quality_flags: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "DerivativeSnapshotV1":
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in fields(cls)}})


@dataclass
class InstrumentRegistryV1:
    """Registry entry for a market instrument."""
    contract_name: str = "InstrumentRegistryV1"
    schema_version: str = "1.0.0"

    instrument_id: str = ""
    canonical_name: str = ""
    symbol: str = ""
    venue: str = ""
    asset_class: str = AssetClass.CRYPTO.value
    instrument_type: str = InstrumentType.SPOT.value
    currency: str = "USDT"
    timezone: str = "UTC"
    trading_hours: str = "24/7"
    calendar: str = "continuous"
    exact_or_proxy: str = ExactOrProxy.EXACT.value
    proxy_for: str = ""
    valid_from: str = ""
    valid_to: str = ""
    provider_symbols: dict[str, str] = field(default_factory=dict)
    notes: str = ""

    def to_json(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "InstrumentRegistryV1":
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in fields(cls)}})


@dataclass
class EventMarketWindowV1:
    """Market data window around a macro event."""
    contract_name: str = "EventMarketWindowV1"
    schema_version: str = "1.0.0"

    window_id: str = ""
    event_id: str = ""
    event_family: str = ""
    event_time_utc: str = ""
    instrument_id: str = ""

    pre_window_start_utc: str = ""
    post_window_end_utc: str = ""
    bar_interval: str = Interval.M5.value

    bars_expected: int = 0
    bars_present: int = 0
    coverage_ratio: float = 0.0
    stale_bar_count: int = 0
    missing_bar_count: int = 0

    pre_event_reference_price: Optional[float] = None
    event_bar_open: Optional[float] = None
    event_bar_close: Optional[float] = None
    post_event_reference_prices: dict[str, float] = field(default_factory=dict)

    source_refs: list[str] = field(default_factory=list)
    data_quality: str = DataQuality.MISSING.value
    quality_flags: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "EventMarketWindowV1":
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in fields(cls)}})


@dataclass
class MarketReactionLabelV1:
    """Multi-horizon market reaction label for an event."""
    contract_name: str = "MarketReactionLabelV1"
    schema_version: str = "1.0.0"

    label_id: str = ""
    event_id: str = ""
    instrument_id: str = ""
    event_time_utc: str = ""

    return_1m: Optional[float] = None
    return_5m: Optional[float] = None
    return_15m: Optional[float] = None
    return_30m: Optional[float] = None
    return_1h: Optional[float] = None
    return_4h: Optional[float] = None
    return_1d: Optional[float] = None

    realized_vol_pre_1h: Optional[float] = None
    realized_vol_post_1h: Optional[float] = None
    volume_zscore: Optional[float] = None
    max_favorable_excursion_1h: Optional[float] = None
    max_adverse_excursion_1h: Optional[float] = None

    funding_change_1h: Optional[float] = None
    open_interest_change_1h: Optional[float] = None
    basis_change_1h: Optional[float] = None

    direction_5m: str = LabelDirection.NEUTRAL.value
    direction_1h: str = LabelDirection.NEUTRAL.value
    direction_1d: str = LabelDirection.NEUTRAL.value

    label_availability: str = LabelAvailability.MISSING.value
    data_quality: str = DataQuality.MISSING.value
    quality_flags: list[str] = field(default_factory=list)
    calculation_version: str = "1.0.0"

    def to_json(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "MarketReactionLabelV1":
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in fields(cls)}})


@dataclass
class SourceSnapshotV1:
    """Provenance record for a data retrieval operation."""
    contract_name: str = "SourceSnapshotV1"
    schema_version: str = "1.0.0"

    source_snapshot_id: str = ""
    source_provider: str = ""
    url: str = ""
    retrieved_at_utc: str = ""
    source_data_type: str = ""
    success: bool = False
    error_message: str = ""
    byte_size: int = 0
    content_hash: str = ""
    record_count: int = 0
    headers_sent: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "SourceSnapshotV1":
        return cls(**{k: v for k, v in data.items() if k in {f.name for f in fields(cls)}})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utc_now() -> str:
    """Return current UTC time as ISO-8601 with Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_ohlc(bar: MarketBarV1) -> list[str]:
    """Validate OHLC relationships. Returns list of violation descriptions."""
    flags: list[str] = []
    if bar.open < 0:
        flags.append("negative_open")
    if bar.high < 0:
        flags.append("negative_high")
    if bar.low < 0:
        flags.append("negative_low")
    if bar.close < 0:
        flags.append("negative_close")
    if bar.volume < 0:
        flags.append("negative_volume")
    if bar.high < bar.low:
        flags.append("high_below_low")
    if bar.high < bar.open:
        flags.append("high_below_open")
    if bar.high < bar.close:
        flags.append("high_below_close")
    if bar.low > bar.open:
        flags.append("low_above_open")
    if bar.low > bar.close:
        flags.append("low_above_close")
    if bar.open == 0 or bar.high == 0 or bar.low == 0 or bar.close == 0:
        flags.append("zero_price")
    return flags
