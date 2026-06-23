"""Market confirmation — evaluates cross-asset confirmation for macro events."""
from __future__ import annotations
from typing import Any, Optional


def evaluate_spot_confirmation(
    btc_pre_price: Optional[float] = None,
    btc_post_price: Optional[float] = None,
    expected_direction: str = "neutral",
    threshold_pct: float = 0.005,
) -> dict[str, Any]:
    """Evaluate BTC spot market confirmation."""
    if btc_pre_price is None or btc_post_price is None:
        return {"confirmed": False, "direction": "unknown", "magnitude_pct": 0.0, "quality": "missing"}
    change_pct = (btc_post_price - btc_pre_price) / btc_pre_price
    if abs(change_pct) < threshold_pct:
        return {"confirmed": False, "direction": "neutral", "magnitude_pct": change_pct, "quality": "low"}
    direction = "bullish" if change_pct > 0 else "bearish"
    aligned = (expected_direction == direction) if expected_direction != "neutral" else True
    return {
        "confirmed": aligned, "direction": direction, "magnitude_pct": change_pct,
        "quality": "high" if abs(change_pct) > 0.02 else "medium",
    }


def evaluate_cross_asset_confirmation(
    yield_2y_change: Optional[float] = None,
    dxy_change: Optional[float] = None,
    sp500_change: Optional[float] = None,
    nasdaq_change: Optional[float] = None,
    gold_change: Optional[float] = None,
    expected_risk_direction: str = "risk_off",
    threshold_pct: float = 0.001,
) -> dict[str, Any]:
    """Evaluate cross-asset confirmation for the expected macro transmission."""
    signals = {}
    if yield_2y_change is not None and abs(yield_2y_change) >= threshold_pct:
        signals["yield_2y"] = {"change": yield_2y_change, "direction": "rising" if yield_2y_change > 0 else "falling"}
    if dxy_change is not None and abs(dxy_change) >= threshold_pct:
        signals["dxy"] = {"change": dxy_change, "direction": "rising" if dxy_change > 0 else "falling"}
    if sp500_change is not None and abs(sp500_change) >= threshold_pct:
        signals["sp500"] = {"change": sp500_change, "direction": "rising" if sp500_change > 0 else "falling"}
    if nasdaq_change is not None and abs(nasdaq_change) >= threshold_pct:
        signals["nasdaq"] = {"change": nasdaq_change, "direction": "rising" if nasdaq_change > 0 else "falling"}
    if gold_change is not None and abs(gold_change) >= threshold_pct:
        signals["gold"] = {"change": gold_change, "direction": "rising" if gold_change > 0 else "falling"}

    if not signals:
        return {"confirmation_level": "missing", "signals": {}, "coherence": "missing", "aligned_count": 0, "total_signals": 0}

    aligned = 0
    if expected_risk_direction == "risk_off":
        if signals.get("yield_2y", {}).get("direction") == "rising": aligned += 1
        if signals.get("dxy", {}).get("direction") == "rising": aligned += 1
        if signals.get("sp500", {}).get("direction") == "falling": aligned += 1
        if signals.get("nasdaq", {}).get("direction") == "falling": aligned += 1
        if signals.get("gold", {}).get("direction") == "rising": aligned += 1
    else:
        if signals.get("yield_2y", {}).get("direction") == "falling": aligned += 1
        if signals.get("dxy", {}).get("direction") == "falling": aligned += 1
        if signals.get("sp500", {}).get("direction") == "rising": aligned += 1
        if signals.get("nasdaq", {}).get("direction") == "rising": aligned += 1
        if signals.get("gold", {}).get("direction") == "falling": aligned += 1

    total = len(signals)
    ratio = aligned / total if total > 0 else 0
    if ratio >= 0.8:
        level = "spot_cross_asset_confirmed"
    elif ratio >= 0.6:
        level = "cross_asset_confirmed"
    elif ratio >= 0.3:
        level = "partial"
    else:
        level = "contradicting"

    return {"confirmation_level": level, "signals": signals, "coherence": "coherent" if ratio >= 0.5 else "conflicting",
            "aligned_count": aligned, "total_signals": total}


def evaluate_derivatives_confirmation(
    funding_rate_change: Optional[float] = None,
    oi_change_pct: Optional[float] = None,
    basis_change: Optional[float] = None,
) -> dict[str, Any]:
    """Evaluate BTC derivatives confirmation."""
    signals = {}
    if funding_rate_change is not None:
        signals["funding"] = {"value": funding_rate_change, "interpretation": "increasing" if funding_rate_change > 0 else "decreasing"}
    if oi_change_pct is not None:
        signals["oi"] = {"value": oi_change_pct, "interpretation": "rising" if oi_change_pct > 0 else "falling"}
    if basis_change is not None:
        signals["basis"] = {"value": basis_change, "interpretation": "expanding" if basis_change > 0 else "contracting"}
    if not signals:
        return {"confirmation_level": "missing", "signals": {}, "derivatives_only": False}
    return {"confirmation_level": "partial" if len(signals) > 0 else "missing", "signals": signals, "derivatives_only": True}
