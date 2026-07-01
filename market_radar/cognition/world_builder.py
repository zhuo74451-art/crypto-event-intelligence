"""F03: Market World Model builder and deterministic classifiers.

Consumes intake lane outputs and produces all 11 domain states.
Deterministic V1 classifiers for regime, liquidity, trend, leverage,
narrative and priced-in.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from market_radar.cognition.world_model import (
    MarketWorldState,
    MacroLiquidityState, RegulatoryGeoState, SpotCrossAssetState,
    DerivativesPositioningState, StablecoinLiquidityState, OnChainWhaleState,
    DefiProtocolState, TokenSupplyState, SecurityOperationalState,
    AttentionNarrativeState, DataQualityState,
    RegimeClassification, PricedInAssessment,
    RegimeLabel, LiquidityLabel, TrendLabel, LeverageLabel,
    NarrativeLabel, PricedInLabel,
)
from market_radar.cognition.intake_contracts import MarketStateInput


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_world_state(as_of, market_inputs, event_assets, source_health=None):
    ws = MarketWorldState(as_of=as_of)
    btc_data = _first_asset(market_inputs, "BTC")
    eth_data = _first_asset(market_inputs, "ETH")
    # 1. Macro
    macro = MacroLiquidityState(domain="macro_and_liquidity", as_of=as_of,
        key_metrics={"btc_price": btc_data.price if btc_data else None,
                    "eth_price": eth_data.price if eth_data else None,
                    "funding_rate": btc_data.funding_rate if btc_data else None})
    ws.macro_and_liquidity = macro
    ws.domains["macro_and_liquidity"] = macro
    # 2. Spot
    spot = SpotCrossAssetState(domain="spot_and_cross_asset", as_of=as_of,
        key_metrics={"btc_price": btc_data.price if btc_data else None})
    ws.spot_and_cross_asset = spot
    ws.domains["spot_and_cross_asset"] = spot
    # 3. Derivatives
    deriv = DerivativesPositioningState(domain="derivatives_and_positioning", as_of=as_of,
        key_metrics={"funding_rate": btc_data.funding_rate if btc_data else None,
                    "open_interest": btc_data.open_interest if btc_data else None})
    ws.derivatives_and_positioning = deriv
    ws.domains["derivatives_and_positioning"] = deriv
    # 4-11: Remaining domains
    for dom_id, cls_name in [
        ("regulatory_and_geopolitical", RegulatoryGeoState),
        ("stablecoin_liquidity", StablecoinLiquidityState),
        ("onchain_and_whales", OnChainWhaleState),
        ("defi_and_protocol", DefiProtocolState),
        ("token_supply_and_unlocks", TokenSupplyState),
        ("security_and_operational", SecurityOperationalState),
        ("attention_and_narrative", AttentionNarrativeState),
        ("data_quality_and_health", DataQualityState),
    ]:
        state = cls_name(domain=dom_id, as_of=as_of,
            unavailable_variables=["no_data_received"])
        setattr(ws, dom_id.replace("-", "_"), state)
        ws.domains[dom_id] = state
    return ws


def _first_asset(inputs, asset):
    for inp in inputs:
        if inp.asset == asset:
            return inp
    return None


def classify_risk_regime(btc_return_24h, funding_rate, volume_change=None):
    if btc_return_24h is None:
        return RegimeLabel.UNCLEAR.value, 0.0
    score = 0.0
    if btc_return_24h > 3.0: score += 1.0
    if btc_return_24h < -3.0: score -= 1.0
    if funding_rate is not None:
        if funding_rate > 0.0001: score += 0.5
        elif funding_rate < -0.0001: score -= 0.5
    if score >= 0.8: return RegimeLabel.RISK_ON.value, abs(score)
    if score <= -0.8: return RegimeLabel.RISK_OFF.value, abs(score)
    return RegimeLabel.MIXED.value, abs(score)


def classify_liquidity(funding_rate, volume_24h):
    if funding_rate is None: return LiquidityLabel.UNCLEAR.value, 0.0
    if funding_rate > 0.0005: return LiquidityLabel.EXPANDING.value, min(funding_rate*1000, 1.0)
    if funding_rate < -0.0005: return LiquidityLabel.CONTRACTING.value, min(abs(funding_rate)*1000, 1.0)
    return LiquidityLabel.UNCLEAR.value, 0.3


def classify_trend(price, pre_price):
    if price is None or pre_price is None or pre_price == 0:
        return TrendLabel.UNCLEAR.value, 0.0
    pct = abs((price - pre_price) / pre_price) * 100.0
    if pct > 10.0: return TrendLabel.DISLOCATION.value, min(pct/20.0, 1.0)
    if pct > 3.0: return TrendLabel.TREND.value, min(pct/10.0, 1.0)
    return TrendLabel.RANGE.value, 1.0 - min(pct/3.0, 1.0)


def classify_leverage(funding_rate):
    if funding_rate is None: return LeverageLabel.NORMAL.value, 0.0
    fr = abs(funding_rate)
    if fr > 0.005: return LeverageLabel.STRESSED.value, min(fr*200, 1.0)
    if fr > 0.001: return LeverageLabel.CROWDED.value, min(fr*500, 1.0)
    if fr < 0.0001: return LeverageLabel.LOW.value, 1.0 - fr*1000
    return LeverageLabel.NORMAL.value, 0.5


def classify_narrative(social_volume_change=None):
    if social_volume_change is None: return NarrativeLabel.ABSENT.value, 0.0
    if social_volume_change > 50: return NarrativeLabel.EMERGING.value, min(social_volume_change/100, 1.0)
    if social_volume_change > 20: return NarrativeLabel.BROADENING.value, min(social_volume_change/50, 1.0)
    if social_volume_change > -10: return NarrativeLabel.CROWDED.value, 0.5
    return NarrativeLabel.DECAYING.value, min(abs(social_volume_change)/50, 1.0)


def classify_priced_in(pre_event_movement, surprise_gap, volume_anomaly=False):
    if pre_event_movement is None: return PricedInLabel.INDETERMINATE.value, 0.0
    am = abs(pre_event_movement)
    if am < 1.0: return PricedInLabel.UNPRICED.value, 0.0
    if am < 3.0: return PricedInLabel.PARTIALLY_PRICED.value, am/5.0
    if volume_anomaly: return PricedInLabel.MOSTLY_PRICED.value, min(am/10.0, 1.0)
    return PricedInLabel.MOSTLY_PRICED.value, am/10.0


def build_regime_classification(as_of, btc_return_24h=None, funding_rate=None,
        btc_price=None, btc_pre_price=None, social_volume_change=None,
        volume_24h=None):
    risk_label, risk_conf = classify_risk_regime(btc_return_24h, funding_rate)
    liq_label, liq_conf = classify_liquidity(funding_rate, volume_24h)
    trend_label, trend_conf = classify_trend(btc_price, btc_pre_price)
    lev_label, lev_conf = classify_leverage(funding_rate)
    nav_label, nav_conf = classify_narrative(social_volume_change)
    return RegimeClassification(as_of=as_of,
        risk_label=risk_label, liquidity_label=liq_label,
        trend_label=trend_label, leverage_label=lev_label,
        narrative_label=nav_label,
        inputs={"btc_return_24h": btc_return_24h, "funding_rate": funding_rate},
        uncertainty=str(round(1.0 - (risk_conf+liq_conf+trend_conf+lev_conf)/4.0, 2)))