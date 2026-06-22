from __future__ import annotations
from market_radar.domains.macro.contracts.common import SeasonalAdjustment


class SeasonalAdjustmentDetector:
    @staticmethod
    def detect_from_label(label: str) -> SeasonalAdjustment:
        lower = label.lower()
        if "sa" in lower or "seasonally adjusted" in lower:
            return SeasonalAdjustment.SEASONALLY_ADJUSTED
        elif "nsa" in lower or "not seasonally adjusted" in lower:
            return SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED
        return SeasonalAdjustment.UNKNOWN

    @staticmethod
    def is_comparable(adj_a: SeasonalAdjustment, adj_b: SeasonalAdjustment) -> bool:
        if adj_a == adj_b:
            return True
        if SeasonalAdjustment.UNKNOWN in (adj_a, adj_b):
            return False
        return False
