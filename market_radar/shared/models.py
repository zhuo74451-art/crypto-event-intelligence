"""Market Radar v117 — Unified Models (Shared Pipeline).

Defines the minimum stable data models for the shared pipeline:
  CardFamily, DataSourceType, NormalizedSignal, GateDecision,
  SendReadinessDecision, RenderedCard, TGTestSendResult,
  EvidenceRecord, SharedPipelineResult

Signal Spine v1 extensions:
  Observation, Signal, SignalStatus, ObservationStatus,
  NoiseGateResult, GateVerdict, DataQuality

Covers all five card families:
  - multi_asset_market_sync
  - price_oi_volume_anomaly
  - news_event_market_impact
  - liquidation_pressure
  - whale_position_alert
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional

CN_TZ = timezone(timedelta(hours=8))
PIPELINE_VERSION = "v1.17"


def china_now() -> str:
    """Return current time in UTC+8 ISO format."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def sha256_short(text: str, n: int = 8) -> str:
    """Short SHA-256 hex digest for redacted proofs."""
    return "sha256:" + hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:n * 2]


# ── Enums ──────────────────────────────────────────────────────────────────


class CardFamily(str, Enum):
    """The five card families covered by the shared pipeline."""
    MULTI_ASSET_MARKET_SYNC = "multi_asset_market_sync"
    PRICE_OI_VOLUME_ANOMALY = "price_oi_volume_anomaly"
    NEWS_EVENT_MARKET_IMPACT = "news_event_market_impact"
    LIQUIDATION_PRESSURE = "liquidation_pressure"
    WHALE_POSITION_ALERT = "whale_position_alert"


class DataSourceType(str, Enum):
    """Types of data sources feeding into the pipeline."""
    FIXTURE = "fixture"
    FREE_PUBLIC_API = "free_public_api"
    FREE_PUBLIC_SOURCE = "free_public_source"
    LOCAL_SNAPSHOT = "local_snapshot"


class DataOrigin(str, Enum):
    """Provenance marker for data origin (not source credibility).

    Separated from DataQuality to avoid semantic confusion:
      DataOrigin = where the data came from (real / fixture / degraded)
      DataQuality = how trustworthy the source is (verified / unverified / etc.)
    """
    REAL = "real"
    FIXTURE = "fixture"
    DEGRADED = "degraded"


# ── Data Models ────────────────────────────────────────────────────────────


@dataclass
class NormalizedSignal:
    """Unified signal produced by an adapter, consumed by quality gate.

    Fields required by contract:
      source_type, card_family, asset_or_topic, timestamp,
      metrics, source_refs, risk_notes
    """
    source_type: DataSourceType
    card_family: CardFamily
    asset_or_topic: str
    timestamp: str
    metrics: dict[str, Any] = field(default_factory=dict)
    source_refs: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)

    # Optional metadata
    pipeline_version: str = PIPELINE_VERSION
    signal_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.source_type, str):
            self.source_type = DataSourceType(self.source_type)
        if isinstance(self.card_family, str):
            self.card_family = CardFamily(self.card_family)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["source_type"] = self.source_type.value
        d["card_family"] = self.card_family.value
        return d


@dataclass
class GateDecision:
    """Decision from the quality gate for a NormalizedSignal.

    allow / block + reason.
    """
    allow: bool
    reason: str
    card_family: CardFamily
    signal_id: Optional[str] = None
    gate_version: str = PIPELINE_VERSION
    reviewed_at: str = field(default_factory=china_now)
    metrics_snapshot: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.card_family, str):
            self.card_family = CardFamily(self.card_family)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["card_family"] = self.card_family.value
        return d


@dataclass
class SendReadinessDecision:
    """Decision on whether a rendered card is ready for TG test group send.

    production_send_ready is always False.
    Formal channel/group sends are always blocked.
    X/Twitter sends are always blocked.
    Daemon/cron/loop is always blocked.
    """
    allow_test_group: bool
    reason: str
    production_send_ready: bool = False
    block_formal_channel: bool = True
    block_x_twitter: bool = True
    block_daemon_cron_loop: bool = True
    gate_version: str = PIPELINE_VERSION
    reviewed_at: str = field(default_factory=china_now)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class RenderedCard:
    """Rendered card output from the renderer.

    Required fields: title, body, card_family, risk_disclaimer,
    evidence_summary, production_status.
    """
    title: str
    body: str
    card_family: CardFamily
    risk_disclaimer: str
    evidence_summary: str
    production_status: str = "test_group_only"

    # For news_event_market_impact cards
    observation_only: bool = False
    not_causal_proof: bool = False

    renderer_version: str = PIPELINE_VERSION
    rendered_at: str = field(default_factory=china_now)

    def __post_init__(self):
        if isinstance(self.card_family, str):
            self.card_family = CardFamily(self.card_family)

    @property
    def full_text(self) -> str:
        """Return the complete card text."""
        parts = [self.title, "", self.body]
        if self.risk_disclaimer:
            parts.extend(["", self.risk_disclaimer])
        return "\n".join(parts)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["card_family"] = self.card_family.value
        return d


@dataclass
class TGTestSendResult:
    """Result of a TG test group one-shot send attempt.

    All sensitive fields (token, chat_id, message_id) are redacted.
    production_send is always False.
    """
    attempted: bool
    success: bool
    status: str  # "sent" | "skipped" | "blocked" | "failed"
    reason: str
    target_type: str = "test_group"
    one_shot: bool = True
    production_send: bool = False

    # Redacted proofs (sha256 hashes, never raw values)
    message_id_proof: Optional[str] = None
    token_proof: Optional[str] = None
    chat_id_proof: Optional[str] = None
    credentials_printed: bool = False

    sent_at: str = field(default_factory=china_now)
    sender_version: str = PIPELINE_VERSION

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvidenceRecord:
    """Redacted evidence record for the evidence ledger.

    proof is sha256-like; no raw token/chat_id/message_id.
    production_send is always False.
    """
    card_family: CardFamily
    pipeline_version: str
    timestamp: str
    production_send: bool = False
    proof: Optional[str] = None
    event_id: Optional[str] = None
    asset_or_topic: Optional[str] = None
    quality_gate_allow: Optional[bool] = None
    send_readiness_allow: Optional[bool] = None
    tg_test_sent: Optional[bool] = None
    tg_status: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.card_family, str):
            self.card_family = CardFamily(self.card_family)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["card_family"] = self.card_family.value
        return d


@dataclass
class SharedPipelineResult:
    """Aggregate result of running the complete shared pipeline for one signal."""
    card_family: CardFamily
    asset_or_topic: str
    signal: Optional[NormalizedSignal] = None
    gate_decision: Optional[GateDecision] = None
    rendered_card: Optional[RenderedCard] = None
    send_readiness: Optional[SendReadinessDecision] = None
    tg_result: Optional[TGTestSendResult] = None
    evidence: Optional[EvidenceRecord] = None
    pipeline_version: str = PIPELINE_VERSION
    completed_at: str = field(default_factory=china_now)
    error: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.card_family, str):
            self.card_family = CardFamily(self.card_family)

    @property
    def passed(self) -> bool:
        """Pipeline completed successfully (all gates passed, TG sent or legitimately skipped)."""
        if self.error:
            return False
        if self.gate_decision and not self.gate_decision.allow:
            return False
        if self.send_readiness and not self.send_readiness.allow_test_group:
            return False
        return True

    def as_dict(self) -> dict:
        d: dict[str, Any] = {}
        d["card_family"] = self.card_family.value
        d["asset_or_topic"] = self.asset_or_topic
        d["signal"] = self.signal.as_dict() if self.signal else None
        d["gate_decision"] = self.gate_decision.as_dict() if self.gate_decision else None
        d["rendered_card"] = self.rendered_card.as_dict() if self.rendered_card else None
        d["send_readiness"] = self.send_readiness.as_dict() if self.send_readiness else None
        d["tg_result"] = self.tg_result.as_dict() if self.tg_result else None
        d["evidence"] = self.evidence.as_dict() if self.evidence else None
        d["pipeline_version"] = self.pipeline_version
        d["completed_at"] = self.completed_at
        d["error"] = self.error
        d["passed"] = self.passed
        return d


# ═══════════════════════════════════════════════════════════════════════════
# Signal Spine v1 — Observation & Signal Models
# ═══════════════════════════════════════════════════════════════════════════

SIGNAL_SPINE_VERSION = "v1.0"


class ObservationStatus(str, Enum):
    """Status of an observation in the ingestion pipeline."""
    RAW = "raw"
    NORMALIZED = "normalized"
    DEDUPLICATED = "deduplicated"
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class DataQuality(str, Enum):
    """Quality assessment for an observation's source data."""
    VERIFIED_HIGH = "verified_high"
    VERIFIED_MEDIUM = "verified_medium"
    UNVERIFIED = "unverified"
    LOW_CREDIBILITY = "low_credibility"
    UNKNOWN = "unknown"


class SignalStatus(str, Enum):
    """Lifecycle status for a Signal object.

    Legal transitions:
      candidate         → confirmed, monitoring, invalidated
      confirmed         → monitoring, invalidated, expired, resolved
      monitoring        → confirmed, invalidated, expired, resolved
      invalidated       → (terminal)
      expired           → (terminal)
      resolved          → (terminal)
    """
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    MONITORING = "monitoring"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"
    RESOLVED = "resolved"


# Legal lifecycle transitions
VALID_SIGNAL_TRANSITIONS: dict[SignalStatus, set[SignalStatus]] = {
    SignalStatus.CANDIDATE: {SignalStatus.CONFIRMED, SignalStatus.MONITORING, SignalStatus.INVALIDATED},
    SignalStatus.CONFIRMED: {SignalStatus.MONITORING, SignalStatus.INVALIDATED, SignalStatus.EXPIRED, SignalStatus.RESOLVED},
    SignalStatus.MONITORING: {SignalStatus.CONFIRMED, SignalStatus.INVALIDATED, SignalStatus.EXPIRED, SignalStatus.RESOLVED},
    SignalStatus.INVALIDATED: set(),
    SignalStatus.EXPIRED: set(),
    SignalStatus.RESOLVED: set(),
}


def is_valid_transition(from_status: SignalStatus, to_status: SignalStatus) -> bool:
    """Check if a lifecycle transition is legal."""
    allowed = VALID_SIGNAL_TRANSITIONS.get(from_status, set())
    return to_status in allowed


class GateVerdict(str, Enum):
    """Outcome of a deterministic noise gate rule evaluation.

    Accept: signal passes this gate rule.
    Reject: signal fails this gate rule (discard or block).
    Downgrade: signal passes but with reduced confidence / observe-only.
    NotEvaluated: rule had insufficient data to judge.
    """
    ACCEPT = "accept"
    REJECT = "reject"
    DOWNGRADE = "downgrade"
    NOT_EVALUATED = "not_evaluated"


class IngestionStatus(str, Enum):
    """Tracking status for observation ingestion."""
    NEW = "new"
    SEEN = "seen"
    MERGED = "merged"


@dataclass
class EvidenceLink:
    """A reference to evidence supporting an observation or signal.

    The 'ref' is a sha256-like redacted fingerprint or absolute ref.
    """
    ref: str
    source: str
    timestamp: str
    description: str
    ref_type: str = "observation"  # observation | signal | external


@dataclass
class Observation:
    """A normalized observation from a data source.

    This is the primary input to the Signal Spine pipeline. It represents
    a single observed event or data point from a source, normalized for
    deterministic processing.

    Dual dedup fields:
      - observation_fingerprint: source-specific (includes source name).
        Identifies the exact observation from a specific source.
      - event_dedup_key: source-agnostic (excludes source name).
        Identifies the underlying event across sources.
        Normalized via title trim, lowercase, whitespace collapse,
        asset sort+uppercase, event_type casefold.

    Can be constructed from a NormalizedSignal or directly from raw data.
    """
    observation_id: str
    source: str
    source_type: DataSourceType
    observed_at: str
    event_time: Optional[str]
    affected_assets: list[str]
    normalized_payload: dict[str, Any]
    raw_provenance: dict[str, Any]
    evidence: list[EvidenceLink]
    data_quality: DataQuality
    observation_fingerprint: str
    event_dedup_key: str
    ingestion_status: ObservationStatus
    card_family: Optional[CardFamily] = None
    source_refs: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.source_type, str):
            self.source_type = DataSourceType(self.source_type)
        if isinstance(self.data_quality, str):
            self.data_quality = DataQuality(self.data_quality)
        if isinstance(self.ingestion_status, str):
            self.ingestion_status = ObservationStatus(self.ingestion_status)
        if isinstance(self.card_family, str):
            self.card_family = CardFamily(self.card_family)

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize title for event-level dedup.

        1. Strip whitespace
        2. Lowercase/casefold
        3. Collapse consecutive whitespace
        """
        import re
        return re.sub(r'\s+', ' ', title.strip().casefold())

    @staticmethod
    def _normalize_assets(assets: list[str]) -> str:
        """Normalize asset list for event-level dedup.

        Sort, uppercase, join.
        """
        return ','.join(sorted(set(a.upper().strip() for a in assets if a.strip())))

    @staticmethod
    def _compute_time_bucket(event_time: Optional[str], bucket_hours: int = 24) -> str:
        """Compute a deterministic time bucket from an event timestamp.

        Prevents different-dates-same-title from being permanently merged.

        Args:
            event_time: ISO 8601 timestamp or None.
            bucket_hours: Bucket size in hours (24 for news, smaller for HF data).

        Returns:
            Bucket string like "2026-06-16T00" for 24h or "2026-06-16T04" for 4h.
            Returns "no_time" if event_time cannot be parsed.
        """
        if not event_time:
            return "no_time"
        try:
            ts = event_time.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts)
            bucket_index = (dt.hour // bucket_hours) * bucket_hours
            return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}T{bucket_index:02d}"
        except (ValueError, TypeError):
            return "no_time"

    @classmethod
    def _compute_event_dedup_key(
        cls,
        title: str,
        assets: list[str],
        event_type: str,
        event_time: Optional[str] = None,
        bucket_hours: int = 24,
    ) -> str:
        """Compute source-agnostic event dedup key.

        Does NOT include source — different sources reporting
        the same event produce the same event_dedup_key.

        Includes a deterministic time bucket to prevent
        different-dates-same-title from being merged forever.

        Args:
            title: Event title.
            assets: Affected asset list.
            event_type: Event type classification.
            event_time: ISO timestamp for time bucketing (optional).
            bucket_hours: Time bucket size in hours.
        """
        norm_title = cls._normalize_title(title)
        norm_assets = cls._normalize_assets(assets)
        norm_type = event_type.strip().casefold()
        bucket = cls._compute_time_bucket(event_time, bucket_hours)
        raw = f"{norm_title}:{norm_assets}:{norm_type}:tb:{bucket}"
        return sha256_short(raw, n=12)

    @classmethod
    def from_normalized_signal(
        cls,
        signal: NormalizedSignal,
        source: str,
        event_time: Optional[str] = None,
        data_quality: DataQuality = DataQuality.UNKNOWN,
    ) -> Observation:
        """Construct an Observation from a NormalizedSignal.

        This is the primary bridge between the existing adapter pipeline
        and the Signal Spine.
        """
        obs_id = str(uuid.uuid4())
        now = china_now()

        # Build affected_assets from signal metrics
        assets = list(signal.metrics.get("assets_affected", []))
        if not assets and signal.asset_or_topic and signal.asset_or_topic != "N/A":
            # Try to extract from asset_or_topic string (e.g. "BTC/ETH/SOL")
            assets = [a.strip() for a in signal.asset_or_topic.split("/") if a.strip()]

        # Build evidence links from existing source refs
        evidence = [
            EvidenceLink(
                ref=sha256_short(ref),
                source=source,
                timestamp=now,
                description=f"Source ref: {ref[:100]}" if len(ref) > 100 else f"Source ref: {ref}",
                ref_type="observation",
            )
            for ref in signal.source_refs
        ]

        # Compute observation_fingerprint (source-specific)
        title = signal.metrics.get("title", "") or signal.asset_or_topic
        fp_raw = f"{source}:{title}:{','.join(sorted(assets))}"
        observation_fingerprint = sha256_short(fp_raw, n=12)

        # Compute event_dedup_key (source-agnostic, with time bucket)
        event_type = signal.metrics.get("event_type", "")
        effective_time = event_time or signal.timestamp
        event_dedup_key = cls._compute_event_dedup_key(title, assets, event_type, effective_time)

        return cls(
            observation_id=obs_id,
            source=source,
            source_type=signal.source_type,
            observed_at=now,
            event_time=event_time or signal.timestamp,
            affected_assets=assets,
            normalized_payload=signal.metrics,
            raw_provenance={
                "signal_id": signal.signal_id,
                "source_refs": signal.source_refs,
                "card_family": signal.card_family.value if signal.card_family else None,
                "risk_notes": signal.risk_notes,
            },
            evidence=evidence,
            data_quality=data_quality,
            observation_fingerprint=observation_fingerprint,
            event_dedup_key=event_dedup_key,
            ingestion_status=ObservationStatus.NORMALIZED,
            card_family=signal.card_family,
            source_refs=list(signal.source_refs),
            risk_notes=list(signal.risk_notes),
        )

    def as_dict(self) -> dict:
        d = asdict(self)
        d["source_type"] = self.source_type.value if isinstance(self.source_type, Enum) else self.source_type
        d["data_quality"] = self.data_quality.value if isinstance(self.data_quality, Enum) else self.data_quality
        d["ingestion_status"] = self.ingestion_status.value if isinstance(self.ingestion_status, Enum) else self.ingestion_status
        if self.card_family:
            d["card_family"] = self.card_family.value if isinstance(self.card_family, Enum) else self.card_family
        return d


@dataclass
class NoiseGateResult:
    """Result of evaluating a single deterministic noise gate rule.

    Each rule in the gate produces one of these. The overall gate decision
    is the aggregation of all rule results.
    """
    rule_name: str
    verdict: GateVerdict
    reason_code: str
    reason: str
    evidence_refs: list[str]
    evaluated_at: str
    rule_version: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.verdict, str):
            self.verdict = GateVerdict(self.verdict)

    @property
    def passed(self) -> bool:
        """Rule passed if verdict is ACCEPT or DOWNGRADE (not REJECT)."""
        return self.verdict in (GateVerdict.ACCEPT, GateVerdict.DOWNGRADE)

    @property
    def is_unknown(self) -> bool:
        return self.verdict == GateVerdict.NOT_EVALUATED

    def as_dict(self) -> dict:
        d = asdict(self)
        d["verdict"] = self.verdict.value if isinstance(self.verdict, Enum) else self.verdict
        return d


@dataclass
class StatusTransition:
    """Record of a single lifecycle status change."""
    from_status: SignalStatus
    to_status: SignalStatus
    reason: str
    timestamp: str
    actor: str = "noise_gate"  # noise_gate | orchestrator | manual

    def __post_init__(self):
        if isinstance(self.from_status, str):
            self.from_status = SignalStatus(self.from_status)
        if isinstance(self.to_status, str):
            self.to_status = SignalStatus(self.to_status)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["from_status"] = self.from_status.value
        d["to_status"] = self.to_status.value
        return d


@dataclass
class Signal:
    """A signal object — the core updatable artifact of the Signal Spine.

    A Signal represents a market-relevant event that has passed the noise gate.
    It is NOT a trading signal — only an intelligence observation that may be
    relevant for monitoring.

    Status lifecycle:
      candidate → confirmed / monitoring → invalidated / expired / resolved
    """
    signal_id: str
    title: str
    affected_assets: list[str]
    event_type: str
    direction: str  # bullish | bearish | neutral
    confidence: float  # 0.0-1.0
    trading_relevance: str  # high | medium | low | none
    news_quality: str  # verified | sourced | unverified
    status: SignalStatus
    first_seen_at: str
    updated_at: str

    # Optional detailed state
    event_id: Optional[str] = None
    price_in_state: Optional[dict[str, Any]] = None
    confirmation_states: list[str] = field(default_factory=list)
    pump_risk: Optional[str] = None  # high | medium | low | unknown
    evidence: list[EvidenceLink] = field(default_factory=list)
    observation_ids: list[str] = field(default_factory=list)
    invalidation_reason: Optional[str] = None
    watch_windows: list[str] = field(default_factory=list)
    renderer_payload: Optional[dict[str, Any]] = None
    transition_history: list[StatusTransition] = field(default_factory=list)

    # Source tracking
    card_family: Optional[CardFamily] = None
    source_type: Optional[DataSourceType] = None

    # Spine metadata
    pipeline_version: str = SIGNAL_SPINE_VERSION

    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = SignalStatus(self.status)
        if isinstance(self.card_family, str):
            self.card_family = CardFamily(self.card_family)
        if isinstance(self.source_type, str):
            self.source_type = DataSourceType(self.source_type)

    def transition_to(self, new_status: SignalStatus, reason: str, actor: str = "orchestrator") -> None:
        """Transition this signal to a new status with validation.

        Raises ValueError if the transition is illegal.
        """
        if isinstance(new_status, str):
            new_status = SignalStatus(new_status)

        if not is_valid_transition(self.status, new_status):
            raise ValueError(
                f"SignalStatus transition {self.status.value} → {new_status.value} is not allowed. "
                f"Allowed from '{self.status.value}': "
                f"{[s.value for s in VALID_SIGNAL_TRANSITIONS.get(self.status, set())]}"
            )

        transition = StatusTransition(
            from_status=self.status,
            to_status=new_status,
            reason=reason,
            timestamp=china_now(),
            actor=actor,
        )
        self.transition_history.append(transition)
        self.status = new_status
        self.updated_at = china_now()

    @property
    def is_terminal(self) -> bool:
        return self.status in (SignalStatus.INVALIDATED, SignalStatus.EXPIRED, SignalStatus.RESOLVED)

    @property
    def is_active(self) -> bool:
        return self.status in (SignalStatus.CANDIDATE, SignalStatus.CONFIRMED, SignalStatus.MONITORING)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        if self.card_family:
            d["card_family"] = self.card_family.value
        if self.source_type:
            d["source_type"] = self.source_type.value
        return d


@dataclass
class SignalSpineResult:
    """Result of processing a single observation through the Signal Spine.

    This is the primary output record for the core orchestrator.
    """
    observation: Observation
    gate_results: list[NoiseGateResult]
    gate_passed: bool
    signal: Optional[Signal] = None
    registry_action: Optional[str] = None  # created_new | merged_into_existing | rejected_by_gate | gate_not_passed
    error: Optional[str] = None
    processed_at: str = field(default_factory=china_now)
    pipeline_version: str = SIGNAL_SPINE_VERSION

    # Unified decision output (populated by event intelligence mapper)
    emit_card: bool = True  # Whether a card should be emitted for this observation
    observation_decision: str = ""  # Final decision: "emit" | "suppress_duplicate" | "discard" | "block" | "risk_tip" | "observe"
    data_origin: Optional[str] = None

    @property
    def gate_verdicts(self) -> dict[str, str]:
        return {r.rule_name: r.verdict.value for r in self.gate_results}

    def as_dict(self) -> dict:
        d = asdict(self)
        d["gate_verdicts"] = self.gate_verdicts
        return d


# ── Fixture Helpers ────────────────────────────────────────────────────────

FIVE_CARD_FAMILIES = [
    CardFamily.MULTI_ASSET_MARKET_SYNC,
    CardFamily.PRICE_OI_VOLUME_ANOMALY,
    CardFamily.NEWS_EVENT_MARKET_IMPACT,
    CardFamily.LIQUIDATION_PRESSURE,
    CardFamily.WHALE_POSITION_ALERT,
]

THREE_VERIFIED_CARD_FAMILIES = [
    CardFamily.MULTI_ASSET_MARKET_SYNC,
    CardFamily.PRICE_OI_VOLUME_ANOMALY,
    CardFamily.NEWS_EVENT_MARKET_IMPACT,
]
