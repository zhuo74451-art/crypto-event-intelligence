from __future__ import annotations
from datetime import datetime
from typing import Tuple


class ReleaseParser:
    @staticmethod
    def parse_release_time(raw_time: str, timezone: str = "America/New_York") -> datetime | None:
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%B %d, %Y %H:%M",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(raw_time, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def parse_component_value(raw_value: str | float | int | None, unit: str | None = None) -> float | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, (int, float)):
            return float(raw_value)
        try:
            cleaned = raw_value.strip().replace(",", "").replace("+", "").replace("%", "").replace("$", "")
            return float(cleaned)
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def parse_prior_revision(raw_values: Tuple[str | None, str | None]) -> Tuple[float | None, float | None]:
        prior = ReleaseParser.parse_component_value(raw_values[0])
        revision = ReleaseParser.parse_component_value(raw_values[1])
        return prior, revision
