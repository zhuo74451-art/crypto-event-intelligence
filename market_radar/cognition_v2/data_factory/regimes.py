"""Deterministic market regime labeling.

C04: Versioned regime assignment using stored market observations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


REQUIRED_REGIMES = {"bull", "bear", "ranging", "high_volatility", "crisis", "recovery"}


class MarketRegimeLabeler:
    """Assign market regime labels to cases using versioned rules."""

    def __init__(self, rule_version: str = "1.0"):
        self._rule_version = rule_version

    def label_from_price_data(
        self,
        case_time: datetime,
        prices_30d_before: List[float],
        prices_30d_after: List[float],
    ) -> Tuple[str, str]:
        """Assign a regime label based on price action around event time.

        Returns (label, rule_description).
        """
        if not prices_30d_before or not prices_30d_after:
            return ("unknown", "insufficient_price_data")

        before_return = (prices_30d_before[-1] / prices_30d_before[0] - 1) if prices_30d_before[0] else 0
        after_return = (prices_30d_after[-1] / prices_30d_after[0] - 1) if prices_30d_after[0] else 0

        # Volatility estimate
        import statistics
        if len(prices_30d_before) > 1:
            daily_returns = [
                (prices_30d_before[i] / prices_30d_before[i-1] - 1)
                for i in range(1, len(prices_30d_before))
                if prices_30d_before[i-1]
            ]
            vol = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
        else:
            vol = 0

        if vol > 0.05 and before_return < -0.10:
            return ("crisis", f"high_volatility({vol:.3f})+sharp_decline({before_return:.3f})")
        if before_return > 0.20:
            return ("bull", f"strong_upward({before_return:.3f})")
        if before_return < -0.15:
            return ("bear", f"strong_decline({before_return:.3f})")
        if vol > 0.04:
            return ("high_volatility", f"elevated_volatility({vol:.3f})")
        if abs(before_return) < 0.05:
            return ("ranging", f"low_movement({before_return:.3f})")
        if after_return > 0.05 and before_return < -0.05:
            return ("recovery", f"recovery_from_decline({before_return:.3f}_to_{after_return:.3f})")
        return ("ranging", f"default_classification({before_return:.3f})")
