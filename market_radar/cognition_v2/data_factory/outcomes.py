"""Outcome observation acquisition and validation.

C04: Separate outcome records at 1h, 6h, 24h, 3d, 7d.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from market_radar.cognition_v2.data_factory.contracts import OutcomeObservation


class OutcomeBuilder:
    """Build outcome observations from price data at standard intervals."""

    CANONICAL_INTERVALS = {"1h": timedelta(hours=1),
                           "6h": timedelta(hours=6),
                           "24h": timedelta(hours=24),
                           "3d": timedelta(days=3),
                           "7d": timedelta(days=7)}

    def __init__(self, provider: str = "binance", instrument: str = "BTCUSDT"):
        self._provider = provider
        self._instrument = instrument

    def build(
        self, case_id: str, event_time: datetime,
        price_map: Dict[str, dict],
    ) -> List[OutcomeObservation]:
        """Build outcome observations from price data."""
        if event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")

        observations = []
        for interval, duration in self.CANONICAL_INTERVALS.items():
            close_time = event_time + duration
            prices = price_map.get(interval, {})

            obs = OutcomeObservation(
                outcome_id=f"{case_id}_{interval}",
                case_id=case_id,
                provider=self._provider,
                instrument=self._instrument,
                interval=interval,
                open_time=event_time,
                close_time=close_time,
                retrieval_time=datetime.now(timezone.utc),
                open_price=prices.get("open"),
                close_price=prices.get("close"),
                high_price=prices.get("high"),
                low_price=prices.get("low"),
                volume=prices.get("volume"),
                return_pct=prices.get("return_pct"),
                direction=prices.get("direction"),
                missing_data_reason=None
                if prices.get("close") is not None
                else "price_data_unavailable",
            )
            obs.content_hash = obs.compute_content_hash()
            observations.append(obs)

        return observations

    @staticmethod
    def validate_windows(
        windows: List[OutcomeObservation],
    ) -> List[str]:
        """Validate outcome windows. Returns list of error messages."""
        errors = []
        for w in windows:
            if w.close_time <= w.open_time:
                errors.append(
                    f"{w.outcome_id}: close_time {w.close_time} <= open_time {w.open_time}"
                )
            if w.high_price is not None and w.low_price is not None:
                if w.high_price < w.low_price:
                    errors.append(
                        f"{w.outcome_id}: high {w.high_price} < low {w.low_price}"
                    )
            if w.interval not in ("1h", "6h", "24h", "3d", "7d"):
                errors.append(f"{w.outcome_id}: invalid interval {w.interval}")
        return errors
