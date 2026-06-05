"""Market Radar v117 — Gate Contracts (Shared Pipeline).

QualityGate: decides whether a NormalizedSignal is sufficient to generate a card.
  Output: allow/block + reason.

SendReadinessGate: decides whether a rendered card can be sent to TG test group.
  - TG test group one-shot → conditional allow
  - production readiness → always False
  - formal channel/group → always block
  - X/Twitter → always block
  - daemon/cron/loop → always block

Must explicitly preserve:
  - Liquidation gate NOT lowered
  - Whale manual evidence NOT bypassed
  - Production ready defaults to False
"""

from __future__ import annotations

from typing import Any

from market_radar.shared.models import (
    CardFamily,
    GateDecision,
    NormalizedSignal,
    RenderedCard,
    SendReadinessDecision,
    PIPELINE_VERSION,
)


# ═══════════════════════════════════════════════════════════════════════════
# Quality Gate
# ═══════════════════════════════════════════════════════════════════════════


class QualityGate:
    """Evaluates a NormalizedSignal against quality thresholds.

    Rules per card family:
      - multi_asset_market_sync → allow if at least 2 assets with data
      - price_oi_volume_anomaly → allow if admission_passed in metrics
      - news_event_market_impact → allow if event has title + intensity >= medium
      - liquidation_pressure → allow if composite_score >= admission_threshold
                               (gate NOT lowered — calm market correctly blocks)
      - whale_position_alert → allow if manual_evidence_provided == True
                               (gate NOT bypassed — requires human input)
    """

    def __init__(self):
        self._gate_version = PIPELINE_VERSION

    def evaluate(self, signal: NormalizedSignal) -> GateDecision:
        """Evaluate a NormalizedSignal and return a GateDecision."""
        card = signal.card_family
        metrics = signal.metrics

        if card == CardFamily.MULTI_ASSET_MARKET_SYNC:
            return self._evaluate_multi_asset(signal)
        elif card == CardFamily.PRICE_OI_VOLUME_ANOMALY:
            return self._evaluate_price_oi(signal)
        elif card == CardFamily.NEWS_EVENT_MARKET_IMPACT:
            return self._evaluate_news_event(signal)
        elif card == CardFamily.LIQUIDATION_PRESSURE:
            return self._evaluate_liquidation(signal)
        elif card == CardFamily.WHALE_POSITION_ALERT:
            return self._evaluate_whale(signal)
        else:
            return GateDecision(
                allow=False,
                reason=f"Unknown card family: {card}",
                card_family=card,
                gate_version=self._gate_version,
            )

    def _evaluate_multi_asset(self, signal: NormalizedSignal) -> GateDecision:
        assets = signal.metrics.get("assets", [])
        if len(assets) >= 2:
            return GateDecision(
                allow=True,
                reason=f"Multi-asset data available for {len(assets)} assets",
                card_family=CardFamily.MULTI_ASSET_MARKET_SYNC,
                gate_version=self._gate_version,
                metrics_snapshot={"asset_count": len(assets)},
            )
        return GateDecision(
            allow=False,
            reason=f"Insufficient asset data: {len(assets)} assets (need >= 2)",
            card_family=CardFamily.MULTI_ASSET_MARKET_SYNC,
            gate_version=self._gate_version,
        )

    def _evaluate_price_oi(self, signal: NormalizedSignal) -> GateDecision:
        # Check for aggregated signals
        signals = signal.metrics.get("signals", [])
        if signals:
            # Check if the primary signal passes admission
            for s in signals:
                if s.get("admission_passed", False):
                    return GateDecision(
                        allow=True,
                        reason=f"Anomaly detected: {s.get('anomaly_type')} on {s.get('symbol')}",
                        card_family=CardFamily.PRICE_OI_VOLUME_ANOMALY,
                        gate_version=self._gate_version,
                        metrics_snapshot={"anomaly_type": s.get("anomaly_type")},
                    )
            return GateDecision(
                allow=False,
                reason="No asset passed admission threshold — insufficient anomaly signal strength",
                card_family=CardFamily.PRICE_OI_VOLUME_ANOMALY,
                gate_version=self._gate_version,
            )

        # Legacy path: single asset signal
        admission = signal.metrics.get("admission_passed", False)
        if admission:
            return GateDecision(
                allow=True,
                reason=f"Admission passed for {signal.asset_or_topic}",
                card_family=CardFamily.PRICE_OI_VOLUME_ANOMALY,
                gate_version=self._gate_version,
            )
        return GateDecision(
            allow=False,
            reason=f"Admission not passed for {signal.asset_or_topic} — signal below threshold",
            card_family=CardFamily.PRICE_OI_VOLUME_ANOMALY,
            gate_version=self._gate_version,
        )

    def _evaluate_news_event(self, signal: NormalizedSignal) -> GateDecision:
        title = signal.metrics.get("title", "")
        intensity = signal.metrics.get("intensity", "low")

        if not title:
            return GateDecision(
                allow=False,
                reason="News event missing title — cannot generate meaningful card",
                card_family=CardFamily.NEWS_EVENT_MARKET_IMPACT,
                gate_version=self._gate_version,
            )

        if intensity in ("high", "medium"):
            return GateDecision(
                allow=True,
                reason=f"News event with {intensity} intensity accepted",
                card_family=CardFamily.NEWS_EVENT_MARKET_IMPACT,
                gate_version=self._gate_version,
                metrics_snapshot={"intensity": intensity},
            )
        return GateDecision(
            allow=False,
            reason=f"News event intensity '{intensity}' below gate threshold",
            card_family=CardFamily.NEWS_EVENT_MARKET_IMPACT,
            gate_version=self._gate_version,
        )

    def _evaluate_liquidation(self, signal: NormalizedSignal) -> GateDecision:
        """Liquidation gate — NOT lowered. Only passes in volatile conditions."""
        composite_score = signal.metrics.get("composite_score", 0)
        threshold = signal.metrics.get("admission_threshold", 0.60)
        calm_market = signal.metrics.get("calm_market", True)

        if calm_market:
            return GateDecision(
                allow=False,
                reason=(
                    f"Liquidation gate: blocked — calm market conditions "
                    f"(composite_score={composite_score:.2f}, threshold={threshold:.2f}). "
                    f"Gate NOT lowered. This is a design-justified block, not a failure. "
                    f"Retry during high-volatility window."
                ),
                card_family=CardFamily.LIQUIDATION_PRESSURE,
                gate_version=self._gate_version,
                metrics_snapshot={
                    "composite_score": composite_score,
                    "threshold": threshold,
                    "calm_market": calm_market,
                },
            )

        if composite_score >= threshold:
            return GateDecision(
                allow=True,
                reason=f"Liquidation pressure detected (score={composite_score:.2f} >= threshold={threshold:.2f})",
                card_family=CardFamily.LIQUIDATION_PRESSURE,
                gate_version=self._gate_version,
                metrics_snapshot={"composite_score": composite_score},
            )

        return GateDecision(
            allow=False,
            reason=(
                f"Liquidation gate: blocked — composite_score={composite_score:.2f} "
                f"below threshold={threshold:.2f}. Gate NOT lowered."
            ),
            card_family=CardFamily.LIQUIDATION_PRESSURE,
            gate_version=self._gate_version,
            metrics_snapshot={"composite_score": composite_score, "threshold": threshold},
        )

    def _evaluate_whale(self, signal: NormalizedSignal) -> GateDecision:
        """Whale gate — requires manual evidence. NEVER auto-approves."""
        manual_evidence = signal.metrics.get("manual_evidence_provided", False)

        if not manual_evidence:
            return GateDecision(
                allow=False,
                reason=(
                    f"Whale gate: blocked — manual evidence NOT provided. "
                    f"Address attribution requires human on-chain verification. "
                    f"Do NOT bypass manual evidence requirement. "
                    f"Gate correctly blocking automated-only signals."
                ),
                card_family=CardFamily.WHALE_POSITION_ALERT,
                gate_version=self._gate_version,
                metrics_snapshot={"manual_evidence_provided": False},
            )

        return GateDecision(
            allow=True,
            reason="Whale position alert accepted — manual evidence provided",
            card_family=CardFamily.WHALE_POSITION_ALERT,
            gate_version=self._gate_version,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Send-Readiness Gate
# ═══════════════════════════════════════════════════════════════════════════


class SendReadinessGate:
    """Gate that evaluates whether a rendered card can be sent.

    Hard rules:
      - production_send_ready = ALWAYS False
      - formal_channel_send = ALWAYS blocked
      - X/Twitter send = ALWAYS blocked
      - daemon/cron/loop = ALWAYS blocked
      - TG test group one-shot = conditionally allowed
    """

    def __init__(self):
        self._gate_version = PIPELINE_VERSION

    def evaluate(
        self,
        card: RenderedCard,
        gate_decision: GateDecision,
        target: str = "test_group",
    ) -> SendReadinessDecision:
        """Evaluate send readiness for a rendered card."""
        reasons: list[str] = []

        # Always block production
        reasons.append("production_send_ready=false (by design)")

        # Always block formal channels
        if target not in ("test_group",):
            reasons.append(f"blocked: target={target} is not test_group")
        reasons.append("blocked: formal_channel")

        # Always block X/Twitter
        reasons.append("blocked: x_twitter")

        # Always block daemon/cron/loop
        reasons.append("blocked: daemon_cron_loop")

        # Test group check
        allow_test_group = gate_decision.allow and target == "test_group"
        if allow_test_group:
            reasons.append("test_group_one_shot: allowed")
        else:
            if not gate_decision.allow:
                reasons.append("test_group: blocked — quality gate not passed")
            if target != "test_group":
                reasons.append(f"test_group: blocked — target '{target}' is not test_group")

        return SendReadinessDecision(
            allow_test_group=allow_test_group,
            reason="; ".join(reasons),
            production_send_ready=False,
            block_formal_channel=True,
            block_x_twitter=True,
            block_daemon_cron_loop=True,
            gate_version=self._gate_version,
        )
