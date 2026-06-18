"""Portfolio risk thresholds — immutable configuration object.

All thresholds are frozen at construction time. No global mutable state.
Illegal values (NaN, negative, infinity) are rejected at construction.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PortfolioThresholds:
    """Immutable portfolio risk threshold configuration.

    Defaults match the W2 Portfolio Intelligence specification.
    All values must be positive finite numbers.
    """

    high_gross_exposure_usd: float = 10_000_000
    net_concentration_ratio: float = 0.8
    single_coin_concentration: float = 0.5
    single_address_concentration: float = 0.7
    high_weighted_leverage: float = 10.0
    liq_cluster_2pct: float = 2.0
    liq_cluster_5pct: float = 5.0
    coordination_window_hours: float = 6.0
    rapid_expansion_pct: float = 20.0
    stale_data_hours: float = 48.0

    def __post_init__(self) -> None:
        """Validate all thresholds are positive finite numbers."""
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"{field_name} must be numeric, got {type(value).__name__}"
                )
            if math.isnan(value) or math.isinf(value):
                raise ValueError(
                    f"{field_name} is NaN or Infinity — rejected"
                )
            if value <= 0:
                raise ValueError(
                    f"{field_name} must be positive, got {value}"
                )

    @property
    def config_hash(self) -> str:
        """Deterministic hash of all threshold values."""
        raw = "|".join(
            f"{f.name}={getattr(self, f.name)}"
            for f in sorted(self.__dataclass_fields__.values(), key=lambda x: x.name)
        )
        return "pcfg:" + hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, float]:
        return {
            f.name: getattr(self, f.name)
            for f in self.__dataclass_fields__.values()
        }


# Default singleton
DEFAULT_THRESHOLDS = PortfolioThresholds()
