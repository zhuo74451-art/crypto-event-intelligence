"""
Return-based label computation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..contracts.label import ReturnLabel, LabelMeta, DirectionLabel, Direction
from ..contracts.common import LabelStatus


class ReturnLabelBuilder:
    """Builds return-based labels for validation events."""

    HORIZONS = ["15m", "1h", "4h", "24h", "3d", "7d", "30d"]
    HORIZON_SECONDS = {
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "24h": 86400,
        "3d": 259200,
        "7d": 604800,
        "30d": 2592000,
    }

    def build_return_label(
        self,
        event_id: str,
        horizon: str,
        entry_price: float,
        exit_price: float,
        benchmark_return: Optional[float] = None,
        computed_at: Optional[datetime] = None,
        matures_at: Optional[datetime] = None,
    ) -> ReturnLabel:
        """Build a return label from entry and exit prices."""
        raw_return = (exit_price - entry_price) / entry_price if entry_price else 0.0
        log_return = __import__("math").log(exit_price / entry_price) if entry_price and exit_price > 0 else 0.0
        abnormal_return = (raw_return - benchmark_return) if benchmark_return is not None else None

        return ReturnLabel(
            event_id=event_id,
            horizon=horizon,
            raw_return=raw_return,
            log_return=log_return,
            abnormal_return=abnormal_return,
            benchmark="custom" if benchmark_return is not None else None,
            meta=LabelMeta(
                label_status=LabelStatus.MATURE if matures_at and computed_at and computed_at >= matures_at else LabelStatus.IMMATURE,
                matures_at=matures_at,
                computed_at=computed_at,
                label_source="price_data",
            ),
        )

    def build_direction_from_return(
        self,
        return_label: ReturnLabel,
        flat_threshold: float = 0.005,
    ) -> DirectionLabel:
        """Build a direction label from a return label."""
        if return_label.raw_return is None:
            direction = Direction.UNKNOWN
        elif abs(return_label.raw_return) <= flat_threshold:
            direction = Direction.FLAT
        elif return_label.raw_return > flat_threshold:
            direction = Direction.UP
        else:
            direction = Direction.DOWN

        return DirectionLabel(
            event_id=return_label.event_id,
            horizon=return_label.horizon,
            direction=direction,
            flat_threshold=flat_threshold,
            meta=return_label.meta,
        )
