"""Regime classifier — deterministic rule-based macro regime classification.
Uses only point-in-time available data. No future information or LLM.
"""
from __future__ import annotations
from typing import Optional
from .contracts import RegimeClassificationResult, RegimeLabel


def classify_regime(
    cpi_trend_3m: Optional[float] = None,
    core_pce_trend_3m: Optional[float] = None,
    nfp_trend_3m: Optional[float] = None,
    unemployment_trend_3m: Optional[float] = None,
    yield_2y_trend_1w: Optional[float] = None,
    yield_10y_trend_1w: Optional[float] = None,
    dxy_trend_1w: Optional[float] = None,
    sp500_trend_1w: Optional[float] = None,
    btc_volatility_1w: Optional[float] = None,
    funding_rate_avg: Optional[float] = None,
    information_cutoff_utc: str = "",
) -> RegimeClassificationResult:
    """Classify current macro regime using deterministic rules. Rules evaluated in order."""
    inputs_used = []
    inputs_missing = []

    def _check(name: str, val) -> bool:
        if val is not None:
            inputs_used.append(name)
            return True
        inputs_missing.append(name)
        return False

    _check("cpi_trend_3m", cpi_trend_3m)
    _check("core_pce_trend_3m", core_pce_trend_3m)
    _check("nfp_trend_3m", nfp_trend_3m)
    _check("unemployment_trend_3m", unemployment_trend_3m)
    _check("yield_2y_trend_1w", yield_2y_trend_1w)
    _check("yield_10y_trend_1w", yield_10y_trend_1w)
    _check("dxy_trend_1w", dxy_trend_1w)
    _check("sp500_trend_1w", sp500_trend_1w)
    _check("btc_volatility_1w", btc_volatility_1w)
    _check("funding_rate_avg", funding_rate_avg)

    # Rule 1: Risk-off stress
    if sp500_trend_1w is not None and sp500_trend_1w < -0.03:
        if btc_volatility_1w is not None and btc_volatility_1w > 0.05:
            return RegimeClassificationResult(
                regime="risk_off_stress", rule_id="rule_risk_off_01",
                inputs_used=inputs_used, inputs_missing=inputs_missing,
                information_cutoff_utc=information_cutoff_utc,
                quality="high" if cpi_trend_3m is not None else "medium",
                alternative_regimes=[{"regime": "mixed_uncertain", "rule_id": "fallback"}])

    # Rule 2: Risk-on expansion
    if sp500_trend_1w is not None and sp500_trend_1w > 0.02:
        if btc_volatility_1w is not None and btc_volatility_1w < 0.03:
            return RegimeClassificationResult(
                regime="risk_on_expansion", rule_id="rule_risk_on_01",
                inputs_used=inputs_used, inputs_missing=inputs_missing,
                information_cutoff_utc=information_cutoff_utc,
                quality="high" if nfp_trend_3m is not None else "medium",
                alternative_regimes=[{"regime": "mixed_uncertain", "rule_id": "fallback"}])

    # Rule 3: Inflation dominant
    if cpi_trend_3m is not None and cpi_trend_3m > 0.03:
        if yield_2y_trend_1w is not None and yield_2y_trend_1w > 0:
            return RegimeClassificationResult(
                regime="inflation_dominant", rule_id="rule_inflation_01",
                inputs_used=inputs_used, inputs_missing=inputs_missing,
                information_cutoff_utc=information_cutoff_utc,
                quality="high" if core_pce_trend_3m is not None else "medium",
                alternative_regimes=[{"regime": "mixed_uncertain", "rule_id": "fallback"}])

    # Rule 4: Growth dominant
    if nfp_trend_3m is not None and nfp_trend_3m > 150000:
        if unemployment_trend_3m is not None and unemployment_trend_3m < 0:
            return RegimeClassificationResult(
                regime="growth_dominant", rule_id="rule_growth_01",
                inputs_used=inputs_used, inputs_missing=inputs_missing,
                information_cutoff_utc=information_cutoff_utc,
                quality="high" if yield_2y_trend_1w is not None else "medium",
                alternative_regimes=[{"regime": "mixed_uncertain", "rule_id": "fallback"}])

    # Rule 5: Liquidity dominant
    if yield_2y_trend_1w is not None and yield_2y_trend_1w < 0:
        if dxy_trend_1w is not None and dxy_trend_1w < 0:
            return RegimeClassificationResult(
                regime="liquidity_dominant", rule_id="rule_liquidity_01",
                inputs_used=inputs_used, inputs_missing=inputs_missing,
                information_cutoff_utc=information_cutoff_utc,
                quality="medium",
                alternative_regimes=[{"regime": "mixed_uncertain", "rule_id": "fallback"}])

    return RegimeClassificationResult(
        regime="mixed_uncertain", rule_id="rule_fallback_01",
        inputs_used=inputs_used, inputs_missing=inputs_missing,
        information_cutoff_utc=information_cutoff_utc, quality="low",
        alternative_regimes=[])
