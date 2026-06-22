"""
Validation workbench — common types and utilities.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# ─── Enums ───────────────────────────────────────────────────────────────────


class PointInTimeMode(str, enum.Enum):
    STRICT_AS_KNOWN_THEN = "strict_as_known_then"
    RECONSTRUCTED_WITH_LIMITS = "reconstructed_with_limits"
    FIXTURE_ONLY = "fixture_only"


class LabelStatus(str, enum.Enum):
    IMMATURE = "immature"
    MATURE = "mature"
    DISPUTED = "disputed"
    UNAVAILABLE = "unavailable"


class Direction(str, enum.Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"
    UNKNOWN = "unknown"


class VolatilityState(str, enum.Enum):
    VOLATILITY_UP = "volatility_up"
    VOLATILITY_DOWN = "volatility_down"
    NORMAL = "normal"
    UNKNOWN = "unknown"


class EventOutcome(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DELAYED = "delayed"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    REVERSED = "reversed"
    UNKNOWN = "unknown"


class BenchmarkType(str, enum.Enum):
    BTC = "btc"
    ETH = "eth"
    MARKET_CAP_WEIGHTED_CRYPTO = "market_cap_weighted_crypto"
    SECTOR_INDEX = "sector_index"
    NASDAQ = "nasdaq"
    SP500 = "sp500"
    CUSTOM = "custom"
    NONE = "none"


class SplitMethod(str, enum.Enum):
    CHRONOLOGICAL_HOLDOUT = "chronological_holdout"
    ROLLING_WINDOW = "rolling_window"
    EXPANDING_WINDOW = "expanding_window"
    PURGED = "purged"
    GROUP_AWARE = "group_aware"


class ExperimentStatus(str, enum.Enum):
    DRAFT = "draft"
    FROZEN = "frozen"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INVALIDATED = "invalidated"
    SUPERSEDED = "superseded"


class CalibrationMethod(str, enum.Enum):
    NONE = "none"
    HISTOGRAM_BINNING = "histogram_binning"
    PLATT_SCALING = "platt_scaling"
    ISOTONIC_REGRESSION = "isotonic_regression"
    TEMPERATURE_SCALING = "temperature_scaling"


class DataAvailabilityLevel(str, enum.Enum):
    INSUFFICIENT = "insufficient"
    LIMITED = "limited"
    ADEQUATE = "adequate"


class PredictionIncrement(str, enum.Enum):
    NONE = "none"
    UNCERTAIN = "uncertain"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class CalibrationQuality(str, enum.Enum):
    NOT_AVAILABLE = "not_available"
    POOR = "poor"
    MIXED = "mixed"
    ACCEPTABLE = "acceptable"


class RegimeStability(str, enum.Enum):
    UNKNOWN = "unknown"
    REGIME_SPECIFIC = "regime_specific"
    UNSTABLE = "unstable"
    BROADLY_STABLE = "broadly_stable"


class PromotionRecommendation(str, enum.Enum):
    REJECT = "reject"
    REVISE_SPECIFICATION = "revise_specification"
    COLLECT_MORE_DATA = "collect_more_data"
    CONTINUE_SHADOW_TEST = "continue_shadow_test"
    ELIGIBLE_FOR_EXTERNAL_REVIEW = "eligible_for_external_review"


class MultipleTestingMethod(str, enum.Enum):
    BONFERRONI = "bonferroni"
    HOLM = "holm"
    BENJAMINI_HOCHBERG = "benjamini_hochberg"


class BootstrapMethod(str, enum.Enum):
    IID = "iid"
    BLOCK = "block"
    EVENT_CLUSTER = "event_cluster"


class ConfidenceType(str, enum.Enum):
    UNCALIBRATED_SCORE = "uncalibrated_score"
    CALIBRATED_PROBABILITY = "calibrated_probability"


# ─── Core dataclasses ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ValidationEventIdentity:
    """Unique identity for a real-world event in the validation system."""

    event_cluster_id: str
    source_dependence_group: str
    primary_source_id: str
    campaign_id: Optional[str] = None


@dataclass(frozen=True)
class TimeInterval:
    start: datetime
    end: datetime

    def contains(self, dt: datetime) -> bool:
        return self.start <= dt <= self.end

    def overlaps(self, other: TimeInterval) -> bool:
        return self.start <= other.end and other.start <= self.end

    def duration_seconds(self) -> float:
        return (self.end - self.start).total_seconds()


@dataclass(frozen=True)
class PredictionWindow:
    """Window for evaluating a prediction."""

    window_start: datetime  # when prediction is made
    window_end: datetime  # when label becomes observable
    horizon: str  # e.g. "1h", "24h"


@dataclass(frozen=True)
class RevisionRef:
    """Reference to a specific revision of a value."""

    revision_id: str
    original_release: datetime
    revision_time: datetime
    value_ref: str


# ─── Fingerprint helpers ─────────────────────────────────────────────────────


def stable_fingerprint(data: dict) -> str:
    """Generate a stable fingerprint from a dictionary, excluding time/absolute paths."""
    import hashlib
    import json

    sanitized = _sanitize_for_fingerprint(data)
    raw = json.dumps(sanitized, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _sanitize_for_fingerprint(data):
    """Remove time-sensitive and path-sensitive fields from fingerprint input."""
    if isinstance(data, dict):
        skip_keys = {
            "created_at", "started_at", "finished_at",
            "computed_at", "matures_at",
            "absolute_path", "machine_name", "hostname",
        }
        return {
            k: _sanitize_for_fingerprint(v)
            for k, v in data.items()
            if k not in skip_keys
        }
    if isinstance(data, (list, tuple)):
        return [_sanitize_for_fingerprint(item) for item in data]
    if isinstance(data, datetime):
        return data.isoformat()
    return data
