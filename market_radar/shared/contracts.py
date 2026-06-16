"""MVP+ — Sealed Shared Contracts (Lane 6 / Contract Seal V1).

All eight contracts required for the Crypto Signal Intelligence MVP+
internal workbench. Frozen by Lane 6 before any Lane 1-5 implementation.

Contract index:
  1. WhalePosition        — Current whale position on Hyperliquid
  2. WhalePositionChange  — Detected position change between snapshots
  3. MarketContext        — Market context for BTC/ETH/SOL/HYPE
  4. UnifiedFeedItem      — Single item from flash/news/TG feeds
  5. SourceClaim          — Provenance / attribution record
  6. EventCluster         — Grouped intelligence event cluster
  7. SourceHealth         — Health status per data source
  8. RunReport            — Full MVP+ run output

Design rules (per MVP+ Charter §5):
  - All timestamps are UTC ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)
  - All USD amounts are float, never 0 for missing — use null
  - All percentages are float (e.g. 15.5 for 15.5%), never 0 for missing
  - All enums are uppercase with underscore separation
  - null means unavailable/unknown — never 0, empty string, or sentinel
  - degraded data carries source/error_type/occurred_at/retryable/message_summary
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

# ── Contract version ──────────────────────────────────────────────────────────
CONTRACTS_VERSION = "mvp+v1.0"
CONTRACTS_SEALED_AT = "2026-06-16T00:00:00Z"


# ═══════════════════════════════════════════════════════════════════════════════
# Contract 1: WhalePosition
# ═══════════════════════════════════════════════════════════════════════════════

class PositionSide(str, Enum):
    """Direction of a position on Hyperliquid."""
    LONG = "LONG"
    SHORT = "SHORT"


class LabelConfidence(str, Enum):
    """Confidence level for an address label."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class EntityType(str, Enum):
    """Type classification for a wallet address."""
    FUND_WALLET = "FUND_WALLET"
    HIGH_LEVERAGE_TRADER = "HIGH_LEVERAGE_TRADER"
    EXCHANGE_RELATED = "EXCHANGE_RELATED"
    MARKET_MAKER = "MARKET_MAKER"
    SMART_MONEY = "SMART_MONEY"
    UNKNOWN_WHALE = "UNKNOWN_WHALE"
    UNCLASSIFIED = "UNCLASSIFIED"


@dataclass
class WhalePosition:
    """A single whale position on Hyperliquid.

    Represents one position (one asset, one side) for one tracked address.

    null semantics:
      - entry_price: null if position just opened and price not yet available
      - leverage: null if cross-margin with no isolated leverage set
      - mark_price: null if market price feed failed
      - unrealized_pnl_usd: null if PnL data unavailable
      - liquidation_price: null if not near liquidation or data unavailable
      - liquidation_distance_pct: null if liquidation_price is null
      - label / entity_type / label_confidence: null if address not identified
      - exposure_pct_of_portfolio: null if portfolio value unknown

    Time: observed_at is UTC ISO 8601.
    """
    # ── Core position data (all required) ──
    address: str                           # Full 0x wallet address, lowercase
    asset: str                             # Asset symbol e.g. "BTC", "ETH", "HYPE"
    side: PositionSide                     # LONG or SHORT
    position_size_usd: float               # Absolute position value in USD
    observed_at: str                       # UTC ISO 8601 timestamp

    # ── Position detail (required where available) ──
    entry_price: Optional[float] = None    # USD per unit
    mark_price: Optional[float] = None     # Current mark price USD
    leverage: Optional[float] = None       # Leverage multiplier (e.g. 5.0 = 5x)
    unrealized_pnl_usd: Optional[float] = None   # Unrealized PnL in USD
    margin_used_usd: Optional[float] = None      # Margin consumed in USD

    # ── Liquidation data (optional) ──
    liquidation_price: Optional[float] = None          # USD
    liquidation_distance_pct: Optional[float] = None   # % from mark price

    # ── Label / entity (optional — null if unknown) ──
    label: Optional[str] = None
    entity_type: Optional[EntityType] = None
    label_confidence: Optional[LabelConfidence] = None
    exposure_pct_of_portfolio: Optional[float] = None

    # ── Metadata ──
    data_origin: str = "live"              # "live" | "fixture" | "degraded"
    source: str = "hyperliquid_info_api"

    def as_dict(self) -> dict:
        d = asdict(self)
        d["side"] = self.side.value
        if self.entity_type:
            d["entity_type"] = self.entity_type.value
        if self.label_confidence:
            d["label_confidence"] = self.label_confidence.value
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# Contract 2: WhalePositionChange
# ═══════════════════════════════════════════════════════════════════════════════

class ChangeType(str, Enum):
    """Type of position change detected between snapshots."""
    POSITION_OPENED = "POSITION_OPENED"        # New position appeared
    POSITION_INCREASED = "POSITION_INCREASED"  # Size increased
    POSITION_REDUCED = "POSITION_REDUCED"      # Size decreased
    POSITION_CLOSED = "POSITION_CLOSED"        # Position fully closed
    DIRECTION_FLIPPED = "DIRECTION_FLIPPED"    # Long→Short or Short→Long
    NO_CHANGE = "NO_CHANGE"                    # No meaningful change
    UNKNOWN = "UNKNOWN"                        # Cannot determine


class RiskLevel(str, Enum):
    """Risk assessment for a position change."""
    CRITICAL = "CRITICAL"       # Liquidation near or massive position shift
    ELEVATED = "ELEVATED"       # Large change, notable concentration
    NORMAL = "NORMAL"           # Routine change within expected bounds
    LOW = "LOW"                 # Minimal change, no concern
    UNKNOWN = "UNKNOWN"         # Insufficient data to assess


@dataclass
class WhalePositionChange:
    """A detected change in a whale position between two observation snapshots.

    Two observation timestamps:
      - previous_observed_at: snapshot before the change
      - current_observed_at: snapshot after the change (same as position.observed_at)

    null semantics:
      - previous_position_size_usd: null if position was not present before (new open)
      - position_delta_usd: null if previous size unknown
      - change_pct: null if previous size was 0 or unknown
      - risk_factors: empty list if no risk factors identified

    Time: all timestamps UTC ISO 8601.
    """
    address: str
    asset: str
    side: PositionSide
    change_type: ChangeType

    # ── Current state (after change) ──
    current_position_size_usd: float
    current_observed_at: str
    current_entry_price: Optional[float] = None
    current_mark_price: Optional[float] = None
    current_unrealized_pnl_usd: Optional[float] = None
    current_liquidation_price: Optional[float] = None
    current_liquidation_distance_pct: Optional[float] = None
    current_leverage: Optional[float] = None

    # ── Previous state (before change) ──
    previous_position_size_usd: Optional[float] = None
    previous_observed_at: Optional[str] = None

    # ── Delta ──
    position_delta_usd: Optional[float] = None   # Signed: positive = increase, negative = decrease
    change_pct: Optional[float] = None            # Signed percentage change

    # ── Classification ──
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    risk_factors: list[str] = field(default_factory=list)

    # ── Context (copied from WhalePosition) ──
    label: Optional[str] = None
    entity_type: Optional[EntityType] = None
    label_confidence: Optional[LabelConfidence] = None

    # ── Metadata ──
    data_origin: str = "live"
    source: str = "hyperliquid_position_engine"

    def as_dict(self) -> dict:
        d = asdict(self)
        d["side"] = self.side.value
        d["change_type"] = self.change_type.value
        d["risk_level"] = self.risk_level.value
        if self.entity_type:
            d["entity_type"] = self.entity_type.value
        if self.label_confidence:
            d["label_confidence"] = self.label_confidence.value
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# Contract 3: MarketContext
# ═══════════════════════════════════════════════════════════════════════════════

class MarketDataSource(str, Enum):
    """Source market data was fetched from."""
    BINANCE_SPOT = "BINANCE_SPOT"
    BINANCE_FUTURES = "BINANCE_FUTURES"
    HYPERLIQUID_SPOT = "HYPERLIQUID_SPOT"
    HYPERLIQUID_PERP = "HYPERLIQUID_PERP"
    CCXT_AGGREGATE = "CCXT_AGGREGATE"
    FIXTURE = "FIXTURE"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


@dataclass
class MarketContext:
    """Market data snapshot for a single asset.

    Primary assets: BTC, ETH, SOL, HYPE.
    Other tracked assets may also appear.

    null semantics:
      - open_interest: null if not available for this asset/source
      - funding_rate: null if not available (spot only)
      - long_short_ratio: null if not available
      - market_cap / dominance_pct: null if not available
      - volume_24h: null if data unavailable (not 0 - distinguish from actual 0 volume)

    Time: observed_at UTC ISO 8601.
    """
    symbol: str                              # e.g. "BTC", "ETH", "SOL", "HYPE"
    price: float                             # USD
    price_change_24h_pct: Optional[float] = None   # %
    volume_24h: Optional[float] = None             # USD
    high_24h: Optional[float] = None         # USD
    low_24h: Optional[float] = None          # USD

    # ── Futures data (optional) ──
    open_interest: Optional[float] = None          # USD
    funding_rate: Optional[float] = None           # e.g. 0.0001 = 0.01%
    long_short_ratio: Optional[float] = None       # e.g. 1.5 = longs 50% more

    # ── Market cap (optional) ──
    market_cap: Optional[float] = None
    dominance_pct: Optional[float] = None

    # ── Metadata ──
    source: MarketDataSource = MarketDataSource.BINANCE_SPOT
    observed_at: str = ""                    # UTC ISO 8601
    data_origin: str = "live"

    def as_dict(self) -> dict:
        d = asdict(self)
        d["source"] = self.source.value
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# Contract 4: UnifiedFeedItem
# ═══════════════════════════════════════════════════════════════════════════════

class FeedType(str, Enum):
    """Classification of the originating feed."""
    FLASH = "FLASH"                    # Rapid / urgent alert
    NEWS = "NEWS"                      # News article
    TELEGRAM = "TELEGRAM"              # Telegram message
    ONCHAIN = "ONCHAIN"                # On-chain data event
    SOCIAL = "SOCIAL"                  # Social media (X, Discord)
    UNKNOWN = "UNKNOWN"


class FeedSourceName(str, Enum):
    """Known feed source names."""
    COINDESK = "COINDESK"
    COINTELEGRAPH = "COINTELEGRAPH"
    DECRYPT = "DECRYPT"
    THE_BLOCK = "THE_BLOCK"
    BINANCE_ANNOUNCEMENTS = "BINANCE_ANNOUNCEMENTS"
    HYPERLIQUID_FEED = "HYPERLIQUID_FEED"
    TELEGRAM_ALPHA = "TELEGRAM_ALPHA"
    TELEGRAM_SIGNAL = "TELEGRAM_SIGNAL"
    TELEGRAM_NEWS = "TELEGRAM_NEWS"
    X_FEED = "X_FEED"
    UNKNOWN = "UNKNOWN"


class ExtractionMethod(str, Enum):
    """How the feed item was extracted/parsed."""
    RULE_BASED_RSS = "RULE_BASED_RSS"
    RULE_BASED_JSON_API = "RULE_BASED_JSON_API"
    RULE_BASED_KEYWORD = "RULE_BASED_KEYWORD"
    TG_FORWARD = "TG_FORWARD"
    DIRECT_API = "DIRECT_API"
    UNKNOWN = "UNKNOWN"


@dataclass
class UnifiedFeedItem:
    """A single normalized item from any existing feed (flash/news/TG).

    null semantics:
      - url: null if no direct URL available
      - body: null if only title exists
      - intensity: null if not classified
      - event_type: null if not classified
      - dedup_key: null if not yet deduplicated
      - original_id: null if source does not provide message IDs

    Time: published_at / ingested_at UTC ISO 8601.
    """
    feed_id: str                         # Unique ID across all feeds
    feed_type: FeedType
    source_name: FeedSourceName

    title: str
    body: Optional[str] = None
    url: Optional[str] = None

    # ── Classification (optional) ──
    event_type: Optional[str] = None     # ETF / regulatory / hack / listing / etc.
    intensity: Optional[str] = None      # high / medium / low
    assets_affected: list[str] = field(default_factory=list)

    # ── Dedup ──
    dedup_key: Optional[str] = None
    original_id: Optional[str] = None    # Source's own message/event ID

    # ── Timestamps ──
    published_at: str = ""               # UTC ISO 8601 (source time)
    ingested_at: str = ""                # UTC ISO 8601 (when we got it)

    # ── Metadata ──
    extraction_method: ExtractionMethod = ExtractionMethod.UNKNOWN
    data_origin: str = "live"

    def as_dict(self) -> dict:
        d = asdict(self)
        d["feed_type"] = self.feed_type.value
        d["source_name"] = self.source_name.value
        d["extraction_method"] = self.extraction_method.value
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# Contract 5: SourceClaim
# ═══════════════════════════════════════════════════════════════════════════════

class ClaimType(str, Enum):
    """Type of claim made by a source."""
    POSITION_EXISTS = "POSITION_EXISTS"
    POSITION_CHANGED = "POSITION_CHANGED"
    MARKET_MOVEMENT = "MARKET_MOVEMENT"
    NEWS_EVENT = "NEWS_EVENT"
    RUMOR = "RUMOR"
    CONFIRMATION = "CONFIRMATION"
    ANALYSIS = "ANALYSIS"
    UNKNOWN = "UNKNOWN"


class ClaimStatus(str, Enum):
    """Verification status of a claim."""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    DISPUTED = "DISPUTED"
    REFUTED = "REFUTED"
    UNVERIFIABLE = "UNVERIFIABLE"


@dataclass
class SourceClaim:
    """A provenance/attribution record for a data claim.

    Links a specific claim to its source with confidence assessment.

    null semantics:
      - claim_detail: null if only the type is known
      - refuted_by: null if not refuted
      - verified_at: null if not yet verified

    Time: UTC ISO 8601.
    """
    claim_id: str
    source_name: str
    claim_type: ClaimType
    ref_type: str                            # "whale_position" | "market_data" | "feed_item" | "cluster"
    ref_id: str                              # ID of the referenced object
    claim_detail: Optional[str] = None       # Free-text description

    # ── Confidence ──
    confidence: float = 0.0                  # 0.0-1.0
    status: ClaimStatus = ClaimStatus.PENDING

    # ── Cross-reference ──
    supporting_refs: list[str] = field(default_factory=list)
    refuted_by: Optional[str] = None

    # ── Timestamps ──
    claimed_at: str = ""                     # UTC ISO 8601
    verified_at: Optional[str] = None        # UTC ISO 8601

    # ── Metadata ──
    data_origin: str = "live"

    def as_dict(self) -> dict:
        d = asdict(self)
        d["claim_type"] = self.claim_type.value
        d["status"] = self.status.value
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# Contract 6: EventCluster
# ═══════════════════════════════════════════════════════════════════════════════

class ClusterRisk(str, Enum):
    """Aggregate risk level for a cluster."""
    CRITICAL = "CRITICAL"
    ELEVATED = "ELEVATED"
    MODERATE = "MODERATE"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class EventCluster:
    """A grouped intelligence event — multiple signals converging on one topic.

    Combines feed items, position changes, and market context into
    a single clustered event for the workbench display.

    null semantics:
      - aggregate_confidence: null if data insufficient
      - resolved_at: null if still ongoing
      - cluster_assets: empty list if assets span too broadly

    Time: UTC ISO 8601.
    """
    cluster_id: str
    title: str
    cluster_assets: list[str] = field(default_factory=list)

    # ── Constituent parts ──
    feed_item_ids: list[str] = field(default_factory=list)
    position_change_ids: list[str] = field(default_factory=list)
    signal_ids: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)

    # ── Assessment ──
    risk: ClusterRisk = ClusterRisk.UNKNOWN
    aggregate_confidence: Optional[float] = None
    risk_tags: list[str] = field(default_factory=list)

    # ── Directions ──
    direction: str = "neutral"             # bullish / bearish / neutral / mixed

    # ── Lifecycle ──
    first_seen_at: str = ""                # UTC ISO 8601
    updated_at: str = ""                   # UTC ISO 8601
    resolved_at: Optional[str] = None      # UTC ISO 8601

    # ── Summary ──
    evidence_summary: str = ""
    source_count: int = 0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["risk"] = self.risk.value
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# Contract 7: SourceHealth
# ═══════════════════════════════════════════════════════════════════════════════

class SourceStatus(str, Enum):
    """Operational status of a data source."""
    OK = "OK"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass
class DegradedInfo:
    """Structured information about a degraded/failed source."""
    error_type: str                        # Class of error (e.g. "HTTP_TIMEOUT", "RATE_LIMITED")
    occurred_at: str                       # UTC ISO 8601
    retryable: bool = True
    message_summary: str = ""              # Human-readable, no secrets
    retry_attempts: int = 0
    next_retry_at: Optional[str] = None    # UTC ISO 8601


@dataclass
class SourceHealth:
    """Operational health for a single data source.

    null semantics:
      - degraded_info: null if source is OK
      - last_error_at: null if no errors recorded
      - latency_ms: null if no request yet
      - last_success_at: null if never succeeded

    Time: UTC ISO 8601.
    """
    source_name: str
    source_group: str                      # "hyperliquid" | "market" | "news" | "telegram" | "onchain"
    status: SourceStatus

    # ── Timing ──
    last_success_at: Optional[str] = None  # UTC ISO 8601
    last_error_at: Optional[str] = None    # UTC ISO 8601
    latency_ms: Optional[float] = None     # Latest request latency

    # ── Counts ──
    success_count: int = 0
    error_count: int = 0
    consecutive_failures: int = 0

    # ── Degradation ──
    degraded_info: Optional[DegradedInfo] = None

    def as_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# Contract 8: RunReport
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LaneResult:
    """Result from a single lane."""
    lane_id: str                           # "L1" | "L2" | "L3" | "L4" | "L5"
    status: str                            # "OK" | "DEGRADED" | "FAILED" | "SKIPPED"
    item_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunReport:
    """Complete output from a single MVP+ workbench run.

    This is the top-level contract — everything a workbench UI needs
    to render a complete internal dashboard.

    null semantics:
      - error: null if run completed without fatal error
      - workbench_html_path: null until UI lane populates it

    Time: UTC ISO 8601.
    """
    run_id: str                            # UUID
    started_at: str                        # UTC ISO 8601
    completed_at: str                      # UTC ISO 8601

    # ── Lane outputs ──
    whale_positions: list[WhalePosition] = field(default_factory=list)
    whale_changes: list[WhalePositionChange] = field(default_factory=list)
    market_contexts: list[MarketContext] = field(default_factory=list)
    feed_items: list[UnifiedFeedItem] = field(default_factory=list)
    event_clusters: list[EventCluster] = field(default_factory=list)
    source_claims: list[SourceClaim] = field(default_factory=list)

    # ── Source health ──
    source_health: list[SourceHealth] = field(default_factory=list)

    # ── Lane results ──
    lane_results: dict[str, LaneResult] = field(default_factory=dict)

    # ── UI —───────────────────────────
    workbench_html_path: Optional[str] = None   # Populated by Lane 5
    workbench_html_name: Optional[str] = None   # HTML filename only

    # ── Run metadata ──
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    known_limitations: list[str] = field(default_factory=list)
    degraded_paths: list[str] = field(default_factory=list)
    contracts_version: str = CONTRACTS_VERSION
    contracts_sealed_at: str = CONTRACTS_SEALED_AT

    def as_dict(self) -> dict:
        d = asdict(self)
        d["whale_positions"] = [p.as_dict() for p in self.whale_positions]
        d["whale_changes"] = [c.as_dict() for c in self.whale_changes]
        d["market_contexts"] = [c.as_dict() for c in self.market_contexts]
        d["feed_items"] = [i.as_dict() for i in self.feed_items]
        d["event_clusters"] = [c.as_dict() for c in self.event_clusters]
        d["source_claims"] = [c.as_dict() for c in self.source_claims]
        d["source_health"] = [h.as_dict() for h in self.source_health]
        d["lane_results"] = {k: v.as_dict() for k, v in self.lane_results.items()}
        return d
