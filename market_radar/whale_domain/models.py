"""Whale Domain — data models and core utility functions.

All models are plain dataclasses. No network, no I/O, no random IDs.
Deterministic: same input -> same normalized output.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# ── Constants ─────────────────────────────────────────────────────────────

SIZE_CHANGE_THRESHOLD = 0.001  # coins — float jitter filter
LIQ_DISTANCE_CRITICAL = 5.0     # percent — within 5% of liquidation
HIGH_LEVERAGE_THRESHOLD = 10.0
LARGE_POSITION_USD = 1_000_000
MASSIVE_POSITION_USD = 5_000_000


# ── Change Types ──────────────────────────────────────────────────────────

class ChangeType(str, Enum):
    """All 14 supported position change types."""
    BASELINE_OPEN_POSITION = "baseline_open_position"
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    INCREASE_LONG = "increase_long"
    INCREASE_SHORT = "increase_short"
    REDUCE_LONG = "reduce_long"
    REDUCE_SHORT = "reduce_short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    FLIP_LONG_TO_SHORT = "flip_long_to_short"
    FLIP_SHORT_TO_LONG = "flip_short_to_long"
    LIQUIDATION_DISTANCE_NARROWED = "liquidation_distance_narrowed"
    NO_CHANGE = "no_change"
    STALE_SNAPSHOT_REJECTED = "stale_snapshot_rejected"


# ── Core Domain Models ────────────────────────────────────────────────────


@dataclass
class WhalePositionInput:
    """Input position data from external source (injected, never fetched).

    This is the input to the domain. All fields are plain types.
    The domain never fetches this data — it's injected by the adapter layer.
    """
    address: str
    label: Optional[str]
    coin: str
    signed_size: float        # Positive = long, negative = short
    entry_price: float
    mark_price: float
    position_value_usd: float
    leverage: float
    unrealized_pnl_usd: Optional[float] = None
    liquidation_price: Optional[float] = None
    snapshot_time_utc: str = ""
    entity_type: Optional[str] = None
    label_confidence: Optional[str] = None
    margin_mode: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.signed_size, (int, float)):
            self.signed_size = float(self.signed_size)


@dataclass
class WhaleSnapshot:
    """A snapshot of a single position at a point in time.

    This is the normalized internal representation, derived from
    WhalePositionInput. Includes computed liquidation distance.
    """
    address: str
    label: Optional[str]
    coin: str
    direction: str          # "long" | "short"
    signed_size: float
    absolute_size: float
    position_value_usd: float
    entry_price: float
    mark_price: float
    leverage: float
    unrealized_pnl_usd: Optional[float] = None
    liquidation_price: Optional[float] = None
    liquidation_distance_pct: Optional[float] = None
    snapshot_time_utc: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def compute_id(address: str, coin: str, snapshot_time_utc: str) -> str:
        """Deterministic ID — no random UUID."""
        raw = f"snap:{address}:{coin}:{snapshot_time_utc}"
        return "w2:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class WhalePositionChange:
    """Detected change between two position snapshots."""
    change_id: str
    address: str
    label: Optional[str]
    coin: str
    change_type: str  # ChangeType value
    direction: str
    previous: Optional[dict] = None  # WhaleSnapshot as dict or None
    current: Optional[dict] = None   # WhaleSnapshot as dict or None
    delta: Optional[dict] = None     # Computed delta
    risk_flags: list[str] = field(default_factory=list)
    detected_at_utc: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def compute_id(address: str, coin: str, change_type: str,
                   current_time: str) -> str:
        raw = f"chg:{address}:{coin}:{change_type}:{current_time}"
        return "w2:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class WhaleExposure:
    """Aggregate exposure metrics for a set of positions."""
    total_positions: int = 0
    total_long_value_usd: float = 0.0
    total_short_value_usd: float = 0.0
    net_exposure_usd: float = 0.0
    total_unrealized_pnl_usd: float = 0.0
    unique_addresses: int = 0
    unique_coins: int = 0
    per_coin_exposure: list[dict] = field(default_factory=list)
    biggest_positions: list[dict] = field(default_factory=list)
    nearest_liquidation: list[dict] = field(default_factory=list)
    high_leverage_positions: list[dict] = field(default_factory=list)
    liquidation_distance_bands: Optional[dict] = None
    generated_at_utc: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WhaleEntityProfile:
    """An entity that may control multiple whale addresses."""
    entity_id: str
    entity_label: str
    entity_type: str
    confidence: str
    label_source: str
    addresses: list[str] = field(default_factory=list)
    notes: Optional[str] = None
    total_value_usd: float = 0.0
    total_pnl_usd: float = 0.0
    position_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WhaleWatchlistEntry:
    """A watchlist entry with filter criteria."""
    address: Optional[str] = None
    label: Optional[str] = None
    coin: Optional[str] = None
    min_position_value_usd: float = LARGE_POSITION_USD
    max_liquidation_distance_pct: float = LIQ_DISTANCE_CRITICAL
    priority: int = 5


@dataclass
class WhaleAlertCandidate:
    """An alert generated from position analysis.

    Generated only — never sent. No send mechanism in domain.
    """
    alert_id: str
    alert_type: str
    severity: str
    coin: str
    label: Optional[str]
    address_short: str
    message: str
    observed_value: Optional[float] = None
    generated_at_utc: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def compute_id(alert_type: str, address: str, coin: str,
                   generated_at: str) -> str:
        raw = f"alr:{alert_type}:{address}:{coin}:{generated_at}"
        return "w2:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class WhaleDomainResult:
    """Complete result of whale domain processing."""
    snapshot_time_utc: str
    changes: list[WhalePositionChange] = field(default_factory=list)
    exposure: Optional[WhaleExposure] = None
    entity_profiles: list[WhaleEntityProfile] = field(default_factory=list)
    watchlist: Optional[dict] = None
    alert_candidates: list[WhaleAlertCandidate] = field(default_factory=list)
    is_baseline: bool = False
    version: str = "v2"

    def to_dict(self) -> dict:
        return {
            "snapshot_time_utc": self.snapshot_time_utc,
            "changes": [c.to_dict() for c in self.changes],
            "exposure": self.exposure.to_dict() if self.exposure else None,
            "entity_profiles": [e.to_dict() for e in self.entity_profiles],
            "watchlist": self.watchlist,
            "alert_candidates": [a.to_dict() for a in self.alert_candidates],
            "is_baseline": self.is_baseline,
            "version": self.version,
        }


# ── Core Utility Functions ────────────────────────────────────────────────


def compute_liquidation_distance(
    direction: str,
    mark_price: Optional[float],
    liquidation_price: Optional[float],
) -> Optional[float]:
    """Compute liquidation distance percentage.

    Long:  (mark_price - liquidation_price) / mark_price * 100
           Positive when liquidation is below mark (normal for longs).
           Larger value = further from liquidation (safer).

    Short: (liquidation_price - mark_price) / mark_price * 100
           Positive when liquidation is above mark (normal for shorts).
           Larger value = further from liquidation (safer).

    Both formulas return the same sign convention: positive = away from liq.
    Returns None if either price is missing or mark_price <= 0.
    Negative values are preserved (not abs'd) — they represent the
    anomalous case where liquidation is on the wrong side of mark.
    """
    if mark_price is None or liquidation_price is None:
        return None
    if mark_price <= 0:
        return None

    if direction == "long":
        return (mark_price - liquidation_price) / mark_price * 100
    elif direction == "short":
        return (liquidation_price - mark_price) / mark_price * 100
    return None


def make_position_key(address: str, coin: str) -> str:
    """Deterministic key for position lookup in state dict."""
    return f"{address.lower()}:{coin.upper()}"


def extract_snapshot(input_data: WhalePositionInput) -> WhaleSnapshot:
    """Convert a WhalePositionInput to a WhaleSnapshot with computed fields."""
    direction = "long" if input_data.signed_size > 0 else "short"
    abs_size = abs(input_data.signed_size)

    liq_distance = compute_liquidation_distance(
        direction, input_data.mark_price, input_data.liquidation_price,
    )

    return WhaleSnapshot(
        address=input_data.address,
        label=input_data.label,
        coin=input_data.coin,
        direction=direction,
        signed_size=input_data.signed_size,
        absolute_size=abs_size,
        position_value_usd=input_data.position_value_usd,
        entry_price=input_data.entry_price,
        mark_price=input_data.mark_price,
        leverage=input_data.leverage,
        unrealized_pnl_usd=input_data.unrealized_pnl_usd,
        liquidation_price=input_data.liquidation_price,
        liquidation_distance_pct=liq_distance,
        snapshot_time_utc=input_data.snapshot_time_utc,
    )


def snapshot_to_dict(snap: WhaleSnapshot) -> dict:
    return snap.to_dict()


def dict_to_snapshot(d: dict) -> WhaleSnapshot:
    return WhaleSnapshot(**d)


def _iso_to_ts(iso_str: Optional[str]) -> float:
    """Parse ISO timestamp to Unix timestamp. Returns 0 on failure."""
    if not iso_str:
        return 0
    try:
        s = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(s).timestamp()
    except (ValueError, TypeError):
        return 0
