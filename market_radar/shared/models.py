"""Market Radar v117 — Unified Models (Shared Pipeline).

Defines the minimum stable data models for the shared pipeline:
  CardFamily, DataSourceType, NormalizedSignal, GateDecision,
  SendReadinessDecision, RenderedCard, TGTestSendResult,
  EvidenceRecord, SharedPipelineResult

Covers all five card families:
  - multi_asset_market_sync
  - price_oi_volume_anomaly
  - news_event_market_impact
  - liquidation_pressure
  - whale_position_alert
"""

from __future__ import annotations

import hashlib
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
