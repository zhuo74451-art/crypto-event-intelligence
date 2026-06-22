from __future__ import annotations
from market_radar.domains.macro.contracts.common import UnitType


class UnitConverter:
    @staticmethod
    def pct_to_basis_points(value: float) -> float:
        return value * 100.0

    @staticmethod
    def basis_points_to_pct(value: float) -> float:
        return value / 100.0

    @staticmethod
    def mo_to_yoy(mo_value: float, periods_per_year: int = 12) -> float:
        return ((1 + mo_value / 100) ** periods_per_year - 1) * 100

    @staticmethod
    def is_compatible(unit_a: UnitType, unit_b: UnitType) -> bool:
        compatible_pairs = {
            (UnitType.PERCENT, UnitType.BASIS_POINTS),
            (UnitType.BASIS_POINTS, UnitType.PERCENT),
            (UnitType.CHANGE_MOM, UnitType.CHANGE_YOY),
            (UnitType.CHANGE_YOY, UnitType.CHANGE_MOM),
        }
        if unit_a == unit_b:
            return True
        return (unit_a, unit_b) in compatible_pairs

    @staticmethod
    def normalize_value(value: float, from_unit: UnitType, to_unit: UnitType) -> float | None:
        if from_unit == to_unit:
            return value
        if from_unit == UnitType.PERCENT and to_unit == UnitType.BASIS_POINTS:
            return value * 100.0
        if from_unit == UnitType.BASIS_POINTS and to_unit == UnitType.PERCENT:
            return value / 100.0
        return None
