from __future__ import annotations
from typing import Dict, List, Tuple


class ConsensusParser:
    @staticmethod
    def parse_numeric_point(value_str: str | float | None) -> float | None:
        if value_str is None:
            return None
        if isinstance(value_str, (int, float)):
            return float(value_str)
        try:
            return float(value_str.strip().replace(",", "").replace("+", "").replace("%", ""))
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def parse_range(range_str: str | None) -> Tuple[float | None, float | None]:
        if range_str is None:
            return None, None
        try:
            parts = range_str.replace("[", "").replace("]", "").replace("(", "").replace(")", "").split(",")
            if len(parts) == 2:
                return float(parts[0].strip()), float(parts[1].strip())
        except (ValueError, AttributeError):
            pass
        return None, None

    @staticmethod
    def parse_distribution(values: List[str]) -> Dict[str, float]:
        result = {}
        for v in values:
            try:
                parts = v.split(":")
                if len(parts) == 2:
                    result[parts[0].strip()] = float(parts[1].strip())
            except (ValueError, AttributeError):
                continue
        return result

    @staticmethod
    def parse_binary_probability(text: str) -> float | None:
        if text is None:
            return None
        try:
            cleaned = text.strip().replace("%", "").replace("probability", "").strip()
            return float(cleaned) / 100.0
        except (ValueError, AttributeError):
            return None
