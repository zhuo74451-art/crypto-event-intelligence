from __future__ import annotations
from typing import List, Optional
from market_radar.strategies.macro_scheduled.contracts.pricing import PricedInEstimate, PricedInStatus


class PricedInEstimator:
    @staticmethod
    def estimate_priced_in(pre_event_return: Optional[float] = None,
                             pre_event_positioning: Optional[str] = None,
                             consensus_dispersion: Optional[float] = None,
                             event_probability: Optional[float] = None,
                             narrative_attention: Optional[str] = None) -> PricedInEstimate:
        reasons: List[str] = []
        missing: List[str] = []
        limitations: List[str] = [
            "V1 heuristic only — not a calibrated pricing model",
            "No options implied move data in V1",
        ]

        if pre_event_return is None:
            missing.append("pre_event_return")
        if consensus_dispersion is None:
            missing.append("consensus_dispersion")
        if event_probability is None:
            missing.append("event_probability")

        priced_signals = 0
        total_signals = 0

        if pre_event_return is not None:
            total_signals += 1
            if abs(pre_event_return) > 3.0:
                priced_signals += 1
                reasons.append(f"Large pre-event move ({pre_event_return:+.2f}%)")

        if consensus_dispersion is not None:
            total_signals += 1
            if consensus_dispersion < 0.1:
                priced_signals += 1
                reasons.append(f"Tight consensus (dispersion={consensus_dispersion:.3f})")

        if event_probability is not None:
            total_signals += 1
            if event_probability > 0.8:
                priced_signals += 1
                reasons.append(f"High event probability ({event_probability:.0%})")

        if pre_event_positioning == "crowded":
            priced_signals += 1
            reasons.append("Pre-event positioning appears crowded")

        status = PricedInStatus.UNKNOWN
        if total_signals == 0:
            status = PricedInStatus.UNKNOWN
            reasons.append("No pricing signals available")
        else:
            ratio = priced_signals / total_signals if total_signals > 0 else 0
            if ratio >= 0.67:
                status = PricedInStatus.LARGELY_PRICED
            elif ratio >= 0.33:
                status = PricedInStatus.PARTIALLY_PRICED
            else:
                status = PricedInStatus.UNDERPRICED

        return PricedInEstimate(status=status, reasons=reasons, missing_inputs=missing, limitations=limitations)
