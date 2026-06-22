from __future__ import annotations
from typing import List, Optional
from market_radar.strategies.macro_scheduled.contracts.pricing import CrowdingAssessment, CrowdingStatus


class CrowdingAssessor:
    @staticmethod
    def assess_crowding(funding: Optional[float] = None,
                         oi: Optional[float] = None,
                         basis: Optional[float] = None,
                         liquidations: Optional[float] = None,
                         spot_volume: Optional[float] = None,
                         pre_event_momentum: Optional[float] = None,
                         attention: Optional[str] = None) -> CrowdingAssessment:
        reasons: List[str] = []
        limitations: List[str] = [
            "V1 heuristic — single venue data cannot represent full market",
            "No perpetual swap breadth data",
        ]

        if funding is None and oi is None and basis is None:
            return CrowdingAssessment(status=CrowdingStatus.UNKNOWN, reasons=["Insufficient data"], limitations=limitations)

        data_points = 0
        long_signals = 0
        short_signals = 0

        if funding is not None:
            data_points += 1
            if funding > 0.1:
                long_signals += 1
                reasons.append(f"Elevated funding ({funding:+.4f})")
            elif funding < -0.05:
                short_signals += 1
                reasons.append(f"Negative funding ({funding:.4f})")

        if oi is not None:
            data_points += 1
            if oi > 1000000:
                long_signals += 1
                reasons.append(f"High OI ({oi:.0f})")

        if basis is not None and basis > 0.2:
            long_signals += 1
            reasons.append(f"Elevated basis ({basis:+.4f})")

        if liquidations is not None and abs(liquidations) > 50_000_000:
            reasons.append(f"Large liquidations ({abs(liquidations):.0f})")
            if liquidations > 0:
                short_signals += 1
            else:
                long_signals += 1

        if data_points == 0:
            return CrowdingAssessment(status=CrowdingStatus.UNKNOWN, limitations=limitations)

        if short_signals > long_signals and short_signals >= 2:
            return CrowdingAssessment(status=CrowdingStatus.CROWDED_SHORT, reasons=reasons, limitations=limitations)
        if long_signals >= 2:
            return CrowdingAssessment(status=CrowdingStatus.CROWDED_LONG, reasons=reasons, limitations=limitations)

        return CrowdingAssessment(status=CrowdingStatus.BALANCED, reasons=reasons, limitations=limitations)
