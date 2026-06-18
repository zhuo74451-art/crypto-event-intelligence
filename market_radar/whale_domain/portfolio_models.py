"""Whale Domain — portfolio intelligence data models.

Deterministic models for multi-address whale portfolio analysis.
No network, no I/O, no random. All IDs derived via hashlib.sha256.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# ── Constants ─────────────────────────────────────────────────────────────

LIQ_CLUSTER_2PCT = 2.0
LIQ_CLUSTER_5PCT = 5.0
HIGH_GROSS_EXPOSURE_USD = 10_000_000
NET_CONCENTRATION_RATIO = 0.8
SINGLE_COIN_CONCENTRATION = 0.5
SINGLE_ADDRESS_CONCENTRATION = 0.7
HIGH_WEIGHTED_LEVERAGE = 10.0


# ── Portfolio Data Models ────────────────────────────────────────────────


@dataclass
class AddressExposureSummary:
    """Exposure summary for a single whale address."""

    address: str
    label: Optional[str]
    gross_exposure_usd: float
    net_exposure_usd: float
    long_exposure_usd: float
    short_exposure_usd: float
    coin_count: int
    largest_position: dict
    weighted_leverage: Optional[float] = None
    closest_liquidation_distance_pct: Optional[float] = None
    risk_flags: list[str] = field(default_factory=list)
    unrealized_pnl_usd: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def compute_id(address: str, snapshot_time_utc: str) -> str:
        """Deterministic ID for an address exposure summary."""
        raw = f"addr_exp:{address}:{snapshot_time_utc}"
        return "w2:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class CoinExposureSummary:
    """Exposure summary for a single coin across all tracked addresses."""

    coin: str
    total_long_usd: float
    total_short_usd: float
    net_exposure_usd: float
    address_count: int
    long_address_count: int
    short_address_count: int
    concentration_ratio: Optional[float] = None
    leverage_weighted: Optional[float] = None
    liquidation_cluster: dict = field(default_factory=lambda: {
        "within_2pct_count": 0,
        "within_5pct_count": 0,
    })

    def to_dict(self) -> dict:
        return asdict(self)

    def as_dict(self) -> dict:
        """Public alias for serialisation, matching the spec."""
        return self.to_dict()


@dataclass
class EntityExposureSummary:
    """Exposure summary for a known entity (multi-address grouping)."""

    entity_id: str
    entity_label: str
    confidence: str
    source: str
    addresses: list[str] = field(default_factory=list)
    gross_exposure_usd: float = 0.0
    net_exposure_usd: float = 0.0
    long_exposure_usd: float = 0.0
    short_exposure_usd: float = 0.0
    coin_count: int = 0
    weighted_leverage: Optional[float] = None
    risk_flags: list[str] = field(default_factory=list)
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CoordinatedAction:
    """A detected coordinated action across multiple addresses/entities."""

    action_id: str
    action_type: str
    coin: str
    direction: str
    address_count: int
    entity_count: int
    total_delta_usd: float
    time_window_start: str
    time_window_end: str
    confidence: str
    reason_codes: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def compute_id(
        action_type: str,
        coin: str,
        direction: str,
        time_window_start: str,
        time_window_end: str,
    ) -> str:
        """Deterministic ID — no random UUID."""
        raw = (
            f"coord:{action_type}:{coin}:{direction}:"
            f"{time_window_start}:{time_window_end}"
        )
        return "w2:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class PortfolioChange:
    """A single change detected in the portfolio between snapshots."""

    change_id: str
    change_type: str
    description: str
    previous_value: Optional[float] = None
    current_value: Optional[float] = None
    delta: Optional[float] = None
    affected_addresses: list[str] = field(default_factory=list)
    affected_coins: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def compute_id(
        change_type: str,
        previous_value: Optional[float],
        current_value: Optional[float],
        snapshot_time_utc: str,
    ) -> str:
        """Deterministic ID for a portfolio change."""
        prev = str(previous_value) if previous_value is not None else "none"
        curr = str(current_value) if current_value is not None else "none"
        raw = f"pfchg:{change_type}:{prev}:{curr}:{snapshot_time_utc}"
        return "w2:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class PortfolioRiskFinding:
    """A single risk finding from portfolio analysis."""

    finding_id: str
    rule_id: str
    severity: str  # critical / high / medium / low / info
    evidence: dict = field(default_factory=dict)
    threshold: str = ""
    observed_value: Optional[float] = None
    affected_addresses: list[str] = field(default_factory=list)
    affected_coins: list[str] = field(default_factory=list)
    data_quality: str = "complete"
    explanation: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def compute_id(
        rule_id: str,
        observed_value: Optional[float],
        snapshot_time_utc: str,
    ) -> str:
        """Deterministic ID for a risk finding."""
        obs = str(observed_value) if observed_value is not None else "none"
        raw = f"risk:{rule_id}:{obs}:{snapshot_time_utc}"
        return "w2:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class WhalePortfolioSnapshot:
    """Complete multi-address portfolio snapshot for a whale intelligence run."""

    snapshot_id: str
    captured_at: str
    addresses: list[str] = field(default_factory=list)
    positions_count: int = 0
    gross_exposure_usd: float = 0.0
    net_exposure_usd: float = 0.0
    long_exposure_usd: float = 0.0
    short_exposure_usd: float = 0.0
    unrealized_pnl_usd: Optional[float] = None
    weighted_leverage: Optional[float] = None
    liquidation_exposure_usd: dict = field(default_factory=lambda: {
        "within_2pct_count": 0,
        "within_2pct_value_usd": 0.0,
        "within_5pct_count": 0,
        "within_5pct_value_usd": 0.0,
    })
    address_summaries: list[AddressExposureSummary] = field(default_factory=list)
    coin_summaries: list[CoinExposureSummary] = field(default_factory=list)
    entity_summaries: list[EntityExposureSummary] = field(default_factory=list)
    risk_findings: list[PortfolioRiskFinding] = field(default_factory=list)
    coordinated_actions: list[CoordinatedAction] = field(default_factory=list)
    changes_since_previous: list[PortfolioChange] = field(default_factory=list)
    data_quality: str = "complete"  # complete / partial / stale / incomplete

    def to_dict(self) -> dict:
        return asdict(self)

    def as_dict(self) -> dict:
        """Public alias for serialisation, matching the spec."""
        return self.to_dict()

    @staticmethod
    def compute_id(captured_at: str, addresses: list[str]) -> str:
        """Deterministic ID — no random UUID."""
        addr_key = ":".join(sorted(a.lower() for a in addresses)) if addresses else "empty"
        raw = f"pf_snap:{captured_at}:{addr_key}"
        return "w2:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class PortfolioIntelligenceSummary:
    """Summarised intelligence output derived from a portfolio snapshot."""

    portfolio_posture: str
    dominant_exposure: str
    top_risks: list[str] = field(default_factory=list)
    coordinated_observations: list[str] = field(default_factory=list)
    data_quality: str = "complete"
    changes_summary: list[str] = field(default_factory=list)
    invalidation_conditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
