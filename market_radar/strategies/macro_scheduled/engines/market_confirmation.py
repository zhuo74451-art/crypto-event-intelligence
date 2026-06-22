from __future__ import annotations
from typing import Dict, List, Optional
from market_radar.strategies.macro_scheduled.contracts.confirmation import (
    MarketConfirmationSnapshot, ConfirmationChannel, ConfirmationStatus,
)


class MarketConfirmationEngine:
    @staticmethod
    def assess_channel(channel: str, value: Optional[float],
                        expected_direction: Optional[str]) -> ConfirmationChannel:
        if value is None:
            return ConfirmationChannel(channel=channel, status=ConfirmationStatus.MISSING)
        direction = "up" if value > 0 else ("down" if value < 0 else "flat")
        status = ConfirmationStatus.CONFIRMING
        if expected_direction and direction != expected_direction:
            status = ConfirmationStatus.CONTRADICTING
        return ConfirmationChannel(channel=channel, status=status, value=value, direction=direction)

    @staticmethod
    def build_confirmation_snapshot(data: Dict[str, Optional[float]],
                                     expected_direction: Optional[str]) -> MarketConfirmationSnapshot:
        channels: Dict[str, ConfirmationChannel] = {}
        contradictory: List[str] = []
        for ch, val in data.items():
            cc = MarketConfirmationEngine.assess_channel(ch, val, expected_direction)
            channels[ch] = cc
            if cc.status == ConfirmationStatus.CONTRADICTING:
                contradictory.append(ch)
        overall = ConfirmationStatus.CONFIRMING
        if contradictory:
            overall = ConfirmationStatus.CONTRADICTING if len(contradictory) > len(channels) / 2 else ConfirmationStatus.MIXED
        has_spot = any("spot" in k for k in channels if channels[k].status == ConfirmationStatus.CONFIRMING)
        deriv_only = all("spot" not in k for k in channels if channels.get(k) and channels[k].status == ConfirmationStatus.CONFIRMING)
        return MarketConfirmationSnapshot(
            channels=channels,
            overall_status=overall,
            has_spot_confirmation=has_spot,
            has_derivatives_only=deriv_only,
            contradictory_channels=contradictory,
        )

    @staticmethod
    def check_rapid_reversal(return_5m: Optional[float], return_15m: Optional[float],
                              return_1h: Optional[float]) -> bool:
        if return_5m is None or return_1h is None:
            return False
        if return_5m > 0 and return_15m is not None and return_15m < 0:
            return True
        if return_5m < 0 and return_15m is not None and return_15m > 0:
            return True
        return False

    @staticmethod
    def detect_derivatives_only(spot_volume: Optional[float], oi_change: Optional[float]) -> bool:
        if spot_volume is None and oi_change is not None:
            return True
        if spot_volume is not None and spot_volume < 100 and oi_change is not None and abs(oi_change) > 10:
            return True
        return False
