"""Signal Spine IO v1 — Event Intelligence Decision Semantics.

Defines the semantic decision categories for Event Intelligence output.

Categories (mutually exclusive):
  - 观察 (OBSERVE):    Worth watching, monitor for developments
  - 风险提示 (RISK):   Notable risk flag — be cautious
  - 禁止 (BLOCK):      Do NOT act on this signal under any circumstances
  - 丢弃 (DISCARD):    Low quality / irrelevant / duplicate / incomplete

Core rules:
  - NEVER produce buy/sell/long/short/guaranteed-profit language
  - ALL outputs are observation + risk assessment only
  - Data quality must be explicitly marked (real / fixture / degraded)

Integration note: When the core Pipeline/Registry is ready, this module should
be called by the decision stage after quality gate passes. The final decision
is a combination of: QualityGate → EventIntelligence → Renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class IntelligenceDecision(str, Enum):
    """Event Intelligence semantic decision.

    These are the ONLY allowed final decisions.
    No buy/sell/long/short/guaranteed-profit equivalents permitted.
    """
    OBSERVE = "观察"
    RISK_TIP = "风险提示"
    BLOCK = "禁止"
    DISCARD = "丢弃"


class DataOrigin(str, Enum):
    """Provenance marker for data origin (not to be confused with DataQuality
    from models.py, which tracks source credibility)."""
    REAL = "real"
    FIXTURE = "fixture"
    DEGRADED = "degraded"


@dataclass
class EventIntelligenceResult:
    """Structured result of event intelligence evaluation.

    All fields are observation/risk-only — no trading instructions.
    """
    # Core
    event_description: str
    assets: list[str]

    # Quality assessment
    news_quality: str  # "high" | "medium" | "low" | "very_low"
    trade_relevance: str  # "high" | "medium" | "low" | "none"
    data_origin: DataOrigin

    # Decision (one of the four categories)
    decision: IntelligenceDecision

    # Risk assessment
    risk_tags: list[str]
    observation_window: str

    # Evidence
    evidence_summary: str
    source_refs: list[str]

    # Dedup (optional)
    dedup_key: str = ""

    # Disclaimer
    disclaimer: str = (
        "⚠ 事件情报观察，不构成投资建议。"
        "本信号仅提供事件影响分析，不包含买卖建议。"
        "所有决策仅供参考，风险自负。"
        "Event intelligence observation only — not financial advice. "
        "No buy/sell/long/short recommendations."
    )

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["decision"] = self.decision.value
        d["data_origin"] = self.data_origin.value if isinstance(self.data_origin, DataOrigin) else self.data_origin
        return d

    def validate_safety(self) -> list[str]:
        """Validate that this result contains NO trading language.

        Checks event_description and evidence_summary only.
        The disclaimer field is EXCLUDED because it explicitly states
        what is NOT included (e.g., '不包含买卖建议、做多做空指示或确定收益承诺').

        Returns list of violations (empty = clean).
        """
        violations: list[str] = []
        forbidden_terms = [
            "buy", "sell", "long", "short", "买入", "卖出", "做多", "做空",
            "guaranteed", "guarantee", "certain", "确定收益", "保赚",
            "profit", "profit-taking", "take profit",
        ]
        # Only check event_description and evidence_summary, NOT disclaimer
        # Disclaimer is excluded because it naturally mentions these terms
        # in the context of stating they are NOT included
        combined = f"{self.event_description} {self.evidence_summary}"
        text_lower = combined.lower()

        for term in forbidden_terms:
            if term.lower() in text_lower:
                violations.append(f"Forbidden term detected: '{term}'")

        # Decision must be one of the four semantic categories
        if self.decision not in (
            IntelligenceDecision.OBSERVE,
            IntelligenceDecision.RISK_TIP,
            IntelligenceDecision.BLOCK,
            IntelligenceDecision.DISCARD,
        ):
            violations.append(f"Invalid decision category: {self.decision}")

        return violations


def evaluate_event_semantics(
    signal_data: dict[str, Any],
    is_duplicate: bool = False,
) -> EventIntelligenceResult:
    """Evaluate a signal payload and produce an EventIntelligenceResult.

    This is a rule-based evaluator (NO AI/model). It applies event
    intelligence semantics to determine the appropriate decision category.

    Args:
        signal_data: Dictionary with fixture/signal fields
        is_duplicate: If True, the signal was already seen (dedup)

    Returns:
        EventIntelligenceResult with decision and evidence
    """
    metrics = signal_data.get("metrics", {})
    card_family = signal_data.get("card_family", "unknown")
    asset_or_topic = signal_data.get("asset_or_topic", "")
    source_refs = signal_data.get("source_refs", [])
    risk_notes = signal_data.get("risk_notes", [])
    dedup_key = signal_data.get("dedup_key", "")

    event_title = metrics.get("title", "")
    source_name = metrics.get("source_name", "")
    event_type = metrics.get("event_type", "")
    intensity = metrics.get("intensity", "low")
    attribution_risk = metrics.get("attribution_risk", "unsafe")
    assets_affected = metrics.get("assets_affected", [])
    news_quality = metrics.get("news_quality", "medium")
    trade_relevance = metrics.get("trade_relevance", "low")

    # ── 1. Check for dedup ──
    if is_duplicate:
        return EventIntelligenceResult(
            event_description=f"[DUPLICATE] {event_title}" if event_title else "Duplicate event (no title)",
            assets=assets_affected if assets_affected else [asset_or_topic] if asset_or_topic else [],
            news_quality=news_quality,
            trade_relevance=trade_relevance,
            data_origin=DataOrigin.FIXTURE,
            decision=IntelligenceDecision.DISCARD,
            risk_tags=["dedup", "duplicate_content"],
            observation_window="N/A — discarded",
            evidence_summary=f"Duplicate event — same dedup_key as previously seen event. Source: {source_name}",
            source_refs=source_refs + ["dedup:matched"],
            dedup_key=dedup_key,
        )

    # ── 2. Check for missing critical fields ──
    missing = []
    if not event_title:
        missing.append("title")
    if not assets_affected and not asset_or_topic:
        missing.append("asset")
    if not event_type:
        missing.append("event_type")

    if len(missing) >= 2:
        return EventIntelligenceResult(
            event_description=f"Incomplete event — missing fields: {', '.join(missing)}",
            assets=assets_affected if assets_affected else [asset_or_topic] if asset_or_topic else ["unknown"],
            news_quality="low",
            trade_relevance="none",
            data_origin=DataOrigin.DEGRADED,
            decision=IntelligenceDecision.DISCARD,
            risk_tags=["missing_fields", "incomplete_data", "unusable"],
            observation_window="N/A — discarded",
            evidence_summary=f"Event discarded due to missing critical fields: {', '.join(missing)}",
            source_refs=source_refs,
        )

    # ── 3. Check for insufficient source ──
    # Check BEFORE pump — insufficient source is DISCARD, not BLOCK
    corroborating = metrics.get("corroborating_sources", -1)
    if corroborating == 0 or (source_name and ("unverified" in source_name.lower() or "telegram" in source_name.lower())):
        return EventIntelligenceResult(
            event_description=event_title or "Event with insufficient source",
            assets=assets_affected if assets_affected else [asset_or_topic],
            news_quality=news_quality,
            trade_relevance=trade_relevance,
            data_origin=DataOrigin.DEGRADED,
            decision=IntelligenceDecision.DISCARD,
            risk_tags=["unverified_source", "insufficient_evidence"],
            observation_window="N/A — discarded",
            evidence_summary=f"Insufficient source evidence: single unverifiable source ({source_name}). No corroboration available.",
            source_refs=source_refs + ["verification:failed"],
            dedup_key=dedup_key,
        )

    # ── 4. Check for pump/FOMO indicators ──
    pump_indicators = metrics.get("pump_indicators", [])
    is_very_low_quality = news_quality == "very_low"
    has_coordinated_pump = any("pump" in str(ind).lower() for ind in pump_indicators)
    if pump_indicators or (is_very_low_quality and has_coordinated_pump):
        risk_tags = ["pump_and_dump", "high_risk"]
        if pump_indicators:
            risk_tags.extend(pump_indicators[:4])
        return EventIntelligenceResult(
            event_description=event_title or "High pump/FOMO risk event",
            assets=assets_affected if assets_affected else [asset_or_topic],
            news_quality=news_quality,
            trade_relevance=trade_relevance,
            data_origin=DataOrigin.FIXTURE if source_refs and "fixture" in str(source_refs) else DataOrigin.REAL,
            decision=IntelligenceDecision.BLOCK,
            risk_tags=risk_tags,
            observation_window="N/A — blocked",
            evidence_summary=f"Event blocked: pump/FOMO risk detected. Source: {source_name}. Indicators: {len(pump_indicators)} pump signals.",
            source_refs=source_refs,
            dedup_key=dedup_key,
        )

    # very_low quality that's NOT pump → still discard
    if is_very_low_quality:
        return EventIntelligenceResult(
            event_description=event_title or "Very low quality event",
            assets=assets_affected if assets_affected else [asset_or_topic],
            news_quality=news_quality,
            trade_relevance=trade_relevance,
            data_origin=DataOrigin.DEGRADED,
            decision=IntelligenceDecision.DISCARD,
            risk_tags=["very_low_quality", "insufficient_evidence"],
            observation_window="N/A — discarded",
            evidence_summary=f"Event discarded: very low news quality ({news_quality}). Source: {source_name}.",
            source_refs=source_refs,
            dedup_key=dedup_key,
        )

    # ── 5. Check for old news / rehash ──
    rehash_indicators = metrics.get("rehash_indicators", [])
    if rehash_indicators:
        original_date = metrics.get("original_publish_date", "unknown")
        days_since = metrics.get("days_since_original", 0)
        return EventIntelligenceResult(
            event_description=f"[OLD NEWS] {event_title}" if event_title else "Old news rehash",
            assets=assets_affected if assets_affected else [asset_or_topic],
            news_quality=news_quality,
            trade_relevance=trade_relevance,
            data_origin=DataOrigin.DEGRADED,
            decision=IntelligenceDecision.RISK_TIP,
            risk_tags=["old_news", "rehash", "stale_information"],
            observation_window="N/A — stale information",
            evidence_summary=f"Old news rehash: original published {original_date} ({days_since} days ago). No new information.",
            source_refs=source_refs + ["rehash_detected"],
            dedup_key=dedup_key,
        )

    # ── 6. Check for no-clear-asset event ──
    if not assets_affected:
        return EventIntelligenceResult(
            event_description=event_title or "Macro event (no specific asset)",
            assets=[asset_or_topic] if asset_or_topic else ["broad_market"],
            news_quality=news_quality,
            trade_relevance=trade_relevance,
            data_origin=DataOrigin.REAL if "fixture" not in str(source_refs) else DataOrigin.FIXTURE,
            decision=IntelligenceDecision.OBSERVE,
            risk_tags=["macro_event", "indirect_impact", "no_asset_attribution"],
            observation_window="48h",
            evidence_summary=f"Macroeconomic event — no specific crypto asset attribution. Monitor broad market impact. Source: {source_name}",
            source_refs=source_refs + ["no_asset_attribution"],
            dedup_key=dedup_key,
        )

    # ── 7. Default: high-quality event → OBSERVE ──
    risk_tags = []
    if intensity == "high":
        risk_tags.append("high_volatility")
    if event_type:
        risk_tags.append(event_type)
    if attribution_risk == "direct":
        risk_tags.append("direct_attribution")
    elif attribution_risk == "indirect":
        risk_tags.append("indirect_impact")

    return EventIntelligenceResult(
        event_description=event_title or "Market event",
        assets=assets_affected if assets_affected else [asset_or_topic],
        news_quality=news_quality,
        trade_relevance=trade_relevance,
        data_origin=DataOrigin.REAL if "fixture" not in str(source_refs) else DataOrigin.FIXTURE,
        decision=IntelligenceDecision.OBSERVE,
        risk_tags=risk_tags,
        observation_window="24h" if intensity == "high" else "48h",
        evidence_summary=f"Event accepted: {event_type} event from {source_name}. Attribution: {attribution_risk}. Intensity: {intensity}.",
        source_refs=source_refs,
        dedup_key=dedup_key,
    )
