"""Market Radar v117 — Renderer Contract (Shared Pipeline).

Input: NormalizedSignal, GateDecision
Output: RenderedCard

Required card fields:
  title, body, card_family, risk_disclaimer, evidence_summary, production_status

For news_event_market_impact:
  observation_only = True
  not_causal_proof = True
"""

from __future__ import annotations

from market_radar.shared.models import (
    CardFamily,
    GateDecision,
    NormalizedSignal,
    RenderedCard,
    PIPELINE_VERSION,
)


class CardRenderer:
    """Renders a NormalizedSignal + GateDecision into a RenderedCard."""

    def __init__(self):
        self._version = PIPELINE_VERSION

    def render(self, signal: NormalizedSignal, gate: GateDecision) -> RenderedCard:
        """Render a card based on card family."""
        card_family = signal.card_family

        if card_family == CardFamily.MULTI_ASSET_MARKET_SYNC:
            return self._render_multi_asset(signal, gate)
        elif card_family == CardFamily.PRICE_OI_VOLUME_ANOMALY:
            return self._render_price_oi(signal, gate)
        elif card_family == CardFamily.NEWS_EVENT_MARKET_IMPACT:
            return self._render_news_event(signal, gate)
        elif card_family == CardFamily.LIQUIDATION_PRESSURE:
            return self._render_liquidation(signal, gate)
        elif card_family == CardFamily.WHALE_POSITION_ALERT:
            return self._render_whale(signal, gate)
        else:
            return RenderedCard(
                title=f"[BLOCKED] Unknown Card: {card_family.value}",
                body=f"Card family '{card_family.value}' has no renderer.",
                card_family=card_family,
                risk_disclaimer="⚠ 内部数据，不作投资建议。Production Send = False。",
                evidence_summary="No evidence — unknown card family.",
            )

    # ── Multi-Asset Market Sync ─────────────────────────────────────────

    def _render_multi_asset(self, signal: NormalizedSignal, gate: GateDecision) -> RenderedCard:
        assets = signal.metrics.get("assets", [])
        sync_obs = signal.metrics.get("sync_observation", "")

        asset_lines = []
        for a in assets[:5]:
            change_pct = a.get("price_change_pct", 0)
            direction = "📈" if change_pct > 0 else "📉" if change_pct < 0 else "➡"
            asset_lines.append(
                f"  {direction} {a.get('symbol', '?')}: "
                f"${a.get('price', 0):,.2f} "
                f"({change_pct:+.2f}%) "
                f"Vol: ${a.get('volume_24h', 0)/1e9:.1f}B"
            )

        body = "\n".join([
            "**Multi-Asset Market Sync**",
            "",
            *asset_lines,
            "",
            f"Correlation: {signal.metrics.get('correlation_score', 0):.2f}",
            f"Observation: {sync_obs}" if sync_obs else "",
            "",
            "Source: Binance Public API (no key required)",
        ])

        return RenderedCard(
            title=f"📊 Market Sync: {signal.asset_or_topic}",
            body=body,
            card_family=CardFamily.MULTI_ASSET_MARKET_SYNC,
            risk_disclaimer="⚠ 市场数据观察，不构成投资建议。数据源于 Binance 免费公开 API。Production Send = False。",
            evidence_summary=f"Binance 24hr tickers for {len(assets)} assets",
            production_status="test_group_only",
        )

    # ── Price/OI/Volume Anomaly ─────────────────────────────────────────

    def _render_price_oi(self, signal: NormalizedSignal, gate: GateDecision) -> RenderedCard:
        signals = signal.metrics.get("signals", [])
        primary = signal.metrics.get("primary_asset", signal.asset_or_topic)

        signal_lines = []
        for s in signals[:3]:
            change = s.get("price_change_24h_pct", 0)
            direction = "📈" if change > 0 else "📉" if change < 0 else "➡"
            symbol = s.get("symbol", "?")
            anomaly = s.get("anomaly_type", "normal")
            admission = "✅" if s.get("admission_passed") else "❌"
            oi = s.get("open_interest_current")
            oi_str = f"OI: ${oi/1e9:.1f}B" if oi else "OI: N/A"
            conf = ", ".join(s.get("confirmation_factors", [])) or "none"
            signal_lines.append(
                f"  {direction} {symbol}: {change:+.2f}% | {oi_str} | "
                f"anomaly={anomaly} | admit={admission} | factors=[{conf}]"
            )

        body = "\n".join([
            "**Price / OI / Volume Anomaly Scan**",
            "",
            *signal_lines,
            "",
            "Anomaly criteria: |price_chg| > 5% + ≥1 confirmation factor",
            "Confirmation factors: price_move_significant, volume_spike, oi_elevated",
            "",
            "Data: Binance Public API (spot 24hr tickers + futures OI)",
        ])

        return RenderedCard(
            title=f"🔍 Anomaly Scan: {primary}",
            body=body,
            card_family=CardFamily.PRICE_OI_VOLUME_ANOMALY,
            risk_disclaimer="⚠ 异常检测信号，不构成投资建议。OI 历史数据可能缺失。Production Send = False。",
            evidence_summary=f"Price/OI anomaly scan across {len(signals)} assets via Binance public API",
            production_status="test_group_only",
        )

    # ── News Event Market Impact ────────────────────────────────────────

    def _render_news_event(self, signal: NormalizedSignal, gate: GateDecision) -> RenderedCard:
        title = signal.metrics.get("title", "Untitled Event")
        source_name = signal.metrics.get("source_name", "Unknown")
        event_type = signal.metrics.get("event_type", "other")
        intensity = signal.metrics.get("intensity", "low")
        url = signal.metrics.get("url", "")
        attr_risk = signal.metrics.get("attribution_risk", "indirect")
        assets = signal.metrics.get("assets_affected", [])

        intensity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(intensity, "⚪")

        body = "\n".join([
            f"**{title}**",
            "",
            f"Source: {source_name}",
            f"Type: {event_type} | Intensity: {intensity_icon} {intensity}",
            f"Attribution: {attr_risk}",
            f"Assets: {', '.join(assets) if assets else 'N/A'}",
            f"URL: {url}" if url else "",
            "",
            "⚠ **Observation Only — Not Causal Proof**",
            "本卡片仅记录事件影响观察，不构成因果证明。",
            "The observed event may or may not cause the market move.",
            "Multiple confounding factors always present.",
        ])

        return RenderedCard(
            title=f"📰 Event: {title[:80]}",
            body=body,
            card_family=CardFamily.NEWS_EVENT_MARKET_IMPACT,
            risk_disclaimer="⚠ 事件影响观察，不构成因果证明，不构成投资建议。数据源于免费公开来源。Production Send = False。",
            evidence_summary=f"News event from {source_name} ({event_type}, {intensity} intensity)",
            production_status="test_group_only",
            observation_only=True,
            not_causal_proof=True,
        )

    # ── Liquidation Pressure ────────────────────────────────────────────

    def _render_liquidation(self, signal: NormalizedSignal, gate: GateDecision) -> RenderedCard:
        assets = signal.metrics.get("assets", [])
        composite = signal.metrics.get("composite_score", 0)
        threshold = signal.metrics.get("admission_threshold", 0.60)

        asset_lines = []
        for a in assets[:3]:
            symbol = a.get("symbol", "?")
            lsr = a.get("long_short_ratio", 0)
            long_liq = a.get("long_liquidation_24h", 0)
            short_liq = a.get("short_liquidation_24h", 0)
            funding = a.get("funding_rate", 0)
            asset_lines.append(
                f"  {symbol}: L/S={lsr:.2f} | LongLiq=${long_liq/1e6:.1f}M | "
                f"ShortLiq=${short_liq/1e6:.1f}M | Funding={funding:.4f}%"
            )

        if not gate.allow:
            body = "\n".join([
                "**[BLOCKED] Liquidation Pressure**",
                "",
                f"Composite Score: {composite:.2f} / Threshold: {threshold:.2f}",
                f"Gate Status: ⛔ BLOCKED — calm market conditions",
                "",
                "This is a DESIGN-JUSTIFIED block, NOT a failure:",
                "- Liquidation pressure is an event-triggered card type",
                "- Gate correctly prevents card generation during quiet markets",
                "- Do NOT lower the threshold to force card generation",
                "- Retry during high-volatility window",
            ])
            evidence = f"Gate blocked: composite={composite:.2f} < threshold={threshold:.2f} (calm market)"
        else:
            body = "\n".join([
                "**🔥 Liquidation Pressure Alert**",
                "",
                *asset_lines,
                "",
                f"Composite Score: {composite:.2f} (threshold: {threshold:.2f})",
                "⚠ High liquidation risk — monitor positions carefully",
            ])
            evidence = f"Liquidation pressure detected: composite={composite:.2f}"

        return RenderedCard(
            title=f"💥 Liquidation: {signal.asset_or_topic}",
            body=body,
            card_family=CardFamily.LIQUIDATION_PRESSURE,
            risk_disclaimer="⚠ Liquidation gate NOT lowered. Event-triggered card. Production Send = False。",
            evidence_summary=evidence,
            production_status="test_group_only",
        )

    # ── Whale Position Alert ────────────────────────────────────────────

    def _render_whale(self, signal: NormalizedSignal, gate: GateDecision) -> RenderedCard:
        addresses = signal.metrics.get("addresses_tracked", [])
        total_exp = signal.metrics.get("total_exposure_usd", 0)

        addr_lines = []
        for a in addresses[:4]:
            addr_lines.append(
                f"  {a.get('address', '?')}: "
                f"{'LONG' if a.get('direction') == 'long' else 'SHORT'} "
                f"${a.get('position_size_usd', 0)/1e6:.1f}M"
            )

        if not gate.allow:
            body = "\n".join([
                "**[BLOCKED] Whale Position Alert**",
                "",
                f"Tracked Addresses: {len(addresses)}",
                f"Total Exposure: ${total_exp/1e6:.1f}M",
                "",
                "⛔ Gate Status: BLOCKED — manual evidence NOT provided",
                "",
                "This is a DESIGN-JUSTIFIED block, NOT a failure:",
                "- Whale position alert requires human on-chain address attribution",
                "- No free public API can provide address ownership verification",
                "- Fake/fabricated evidence is worse than no evidence",
                "- Do NOT bypass manual evidence requirement",
                "",
                "Next step: Complete operator workbook with address verification",
                "Then rerun with manual_evidence_provided=true",
            ])
        else:
            body = "\n".join([
                "**🐋 Whale Position Alert**",
                "",
                *addr_lines,
                "",
                f"Total Exposure: ${total_exp/1e6:.1f}M",
                "Manual evidence: ✅ verified",
            ])

        return RenderedCard(
            title=f"🐋 Whale Alert: {signal.asset_or_topic}",
            body=body,
            card_family=CardFamily.WHALE_POSITION_ALERT,
            risk_disclaimer="⚠ Whale tracking requires manual evidence. Do NOT bypass. Production Send = False。",
            evidence_summary=(
                "Manual evidence required — blocked" if not gate.allow
                else f"Whale positions verified — {len(addresses)} addresses"
            ),
            production_status="test_group_only",
        )


def create_renderer() -> CardRenderer:
    """Factory: create the default card renderer."""
    return CardRenderer()
