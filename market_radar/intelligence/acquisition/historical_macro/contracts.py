"""Canonical Python contracts for historical macro-economic evidence — V2.

V2 changes:
- Release time provenance fields (release_time_quality, release_time_verified)
- Measure semantics (primary_measure, secondary_measures, actual_value_status)
- DST-aware ET->UTC conversion
- Logical event key for cross-provider dedup
- Provider observation contract (MacroReleaseObservationV1)
- Eligibility fields for downstream lanes
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from ...contracts.common import utc_now, utc_parse, validate_utc


# --- Enums ---


class EventFamily(str, Enum):
    US_CPI = "us_cpi"
    US_CORE_CPI = "us_core_cpi"
    US_NONFARM_PAYROLLS = "us_nonfarm_payrolls"
    US_UNEMPLOYMENT_RATE = "us_unemployment_rate"
    US_CORE_PCE = "us_core_pce"
    US_FOMC_RATE_DECISION = "us_fomc_rate_decision"
    US_RETAIL_SALES = "us_retail_sales"
    US_PPI = "us_ppi"
    US_GDP = "us_gdp"
    US_ISM_MANUFACTURING = "us_ism_manufacturing"
    US_INITIAL_JOBLESS_CLAIMS = "us_initial_jobless_claims"
    FOMC_MINUTES = "fomc_minutes"


class RevisionStatus(str, Enum):
    INITIAL = "initial"
    REVISED = "revised"
    MULTIPLE_REVISIONS = "multiple_revisions"
    UNAVAILABLE = "unavailable"


class PointInTimeQuality(str, Enum):
    STRICT_ARCHIVED_PRE_EVENT = "strict_archived_pre_event"
    VERIFIED_PRE_EVENT_MEDIA = "verified_pre_event_media"
    RECONSTRUCTED_MULTI_SOURCE = "reconstructed_multi_source"
    SINGLE_SOURCE_RECONSTRUCTED = "single_source_reconstructed"
    MISSING = "missing"


class ReleaseTimeQuality(str, Enum):
    VERIFIED_OFFICIAL_RELEASE_PAGE = "verified_official_release_page"
    VERIFIED_OFFICIAL_CALENDAR = "verified_official_calendar"
    VERIFIED_OFFICIAL_ARCHIVE = "verified_official_archive"
    RECONSTRUCTED_OFFICIAL_DATE_ONLY = "reconstructed_official_date_only"
    ESTIMATED_UNUSABLE = "estimated_unusable"
    MISSING = "missing"


class ActualValueStatus(str, Enum):
    VERIFIED_INITIAL_FROM_RELEASE = "verified_initial_from_release"
    DERIVED_FROM_VERIFIED_RELEASE_TABLE = "derived_from_verified_release_table"
    CURRENT_LATEST_ONLY = "current_latest_only"
    RECONSTRUCTED_WITH_LIMITS = "reconstructed_with_limits"
    MISSING = "missing"


class MeasurementType(str, Enum):
    SEASONALLY_ADJUSTED_MOM_PERCENT = "seasonally_adjusted_mom_percent"
    UNADJUSTED_YOY_PERCENT = "unadjusted_yoy_percent"
    INDEX_LEVEL = "index_level"
    PAYROLL_CHANGE_THOUSANDS = "payroll_change_thousands"
    UNEMPLOYMENT_RATE_PERCENT = "unemployment_rate_percent"
    PERCENT_RANGE_MIDPOINT = "percent_range_midpoint"
    CHANGE_BASIS_POINTS = "change_basis_points"


class EstimateType(str, Enum):
    CONSENSUS_MEDIAN = "consensus_median"
    CONSENSUS_MEAN = "consensus_mean"
    SINGLE_ANALYST = "single_analyst"
    RANGE_MIDPOINT = "range_midpoint"
    SURVEY = "survey"
    MARKET_IMPLIED = "market_implied"
    OFFICIAL_FORECAST = "official_forecast"


class Provider(str, Enum):
    BLS = "bls"
    BEA = "bea"
    FEDERAL_RESERVE = "federal_reserve"
    FRED_ALFRED = "fred_alfred"
    PUBLIC_CONSENSUS = "public_consensus"


class ParseStatus(str, Enum):
    PARSED = "parsed"
    PARTIAL = "partial"
    FAILED = "failed"
    PENDING = "pending"


class ObservationQuality(str, Enum):
    VERIFIED_INITIAL = "verified_initial"
    DERIVED = "derived"
    CURRENT_LATEST = "current_latest"
    RECONSTRUCTED = "reconstructed"
    MISSING = "missing"


# --- DST-Aware ET to UTC Conversion ---


# Known US Eastern release times by event family
ET_RELEASE_TIMES: dict[str, str] = {
    "us_cpi": "08:30",
    "us_core_cpi": "08:30",
    "us_nonfarm_payrolls": "08:30",
    "us_unemployment_rate": "08:30",
    "us_core_pce": "08:30",
    "us_fomc_rate_decision": "14:00",
}


def us_eastern_date_to_utc(release_date: str, et_time_str: str = "08:30") -> str:
    """Convert a US Eastern date+time to UTC, properly handling EST/EDT.

    release_date: YYYY-MM-DD format date
    et_time_str: HH:MM in 24-hour Eastern Time

    Rules:
    - Second Sunday March (2AM) -> EDT (UTC-4)
    - First Sunday November (2AM) -> EST (UTC-5)
    """
    from datetime import timedelta

    dt = datetime.strptime(f"{release_date} {et_time_str}", "%Y-%m-%d %H:%M")
    year = dt.year

    # Compute second Sunday of March for this year
    mar_1 = datetime(year, 3, 1)
    days_to_first_sun_mar = (6 - mar_1.weekday()) % 7
    second_sun_mar = mar_1 + timedelta(days=days_to_first_sun_mar + 7)

    # Compute first Sunday of November
    nov_1 = datetime(year, 11, 1)
    days_to_first_sun_nov = (6 - nov_1.weekday()) % 7
    first_sun_nov = nov_1 + timedelta(days=days_to_first_sun_nov)

    # EDT: UTC-4, EST: UTC-5
    if second_sun_mar <= dt < first_sun_nov:
        # EDT (UTC-4)
        utc_dt = dt + timedelta(hours=4)
    else:
        # EST (UTC-5)
        utc_dt = dt + timedelta(hours=5)

    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def us_eastern_to_utc(release_date_et: str, et_time: str = "08:30") -> str:
    """Convert US Eastern date/time to UTC ISO string.

    Handles EST/EDT based on date.
    """
    return us_eastern_date_to_utc(release_date_et, et_time)


# --- Logical Event Key ---


def generate_logical_event_key(country: str, event_family: str,
                                reference_period: str) -> str:
    """Generate a provider-independent logical event key.

    Two events with the same key represent the same economic release
    regardless of which provider reported them.
    """
    parts = [
        country.strip().upper(),
        event_family.strip().lower(),
        reference_period.strip(),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


# --- ID Generation ---


def generate_event_id(logical_event_key: str,
                       actual_release_at_utc: str) -> str:
    """Deterministic SHA256-based event ID.

    Uses logical_event_key (provider-independent) + verified release time.
    """
    payload = "|".join([
        logical_event_key,
        validate_utc(actual_release_at_utc),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def generate_observation_id(event_id: str, provider: str,
                             series_id: str, reference_period: str,
                             measure_type: str) -> str:
    """Deterministic provider observation ID."""
    payload = "|".join([
        event_id,
        provider.strip().lower(),
        series_id.strip(),
        reference_period.strip(),
        measure_type.strip().lower(),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def generate_consensus_observation_id(event_id: str, source_name: str,
                                       published_at_utc: str,
                                       consensus_value: float) -> str:
    """Deterministic consensus observation ID."""
    payload = "|".join([
        event_id,
        source_name.strip().lower(),
        validate_utc(published_at_utc),
        str(consensus_value),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def generate_revision_id(event_id: str, revision_published_at_utc: str,
                          previous_value: float, revised_value: float) -> str:
    """Deterministic revision record ID."""
    payload = "|".join([
        event_id,
        validate_utc(revision_published_at_utc),
        str(previous_value),
        str(revised_value),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def generate_snapshot_id(provider: str, source_url: str,
                          retrieved_at_utc: str) -> str:
    """Deterministic source snapshot ID."""
    payload = "|".join([
        provider.strip().lower(),
        source_url.strip(),
        validate_utc(retrieved_at_utc),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]



# --- Surprise Calculation ---


SUPRISE_DIRECTION_SEMANTICS: dict[str, str] = {
    "us_cpi": "actual_initial - consensus_value",
    "us_core_cpi": "actual_initial - consensus_value",
    "us_nonfarm_payrolls": "actual_initial - consensus_value",
    "us_unemployment_rate": "actual_initial - consensus_value",
    "us_core_pce": "actual_initial - consensus_value",
    "us_fomc_rate_decision": "actual_rate - expected_rate",
}


def compute_surprise_raw(event_family: str,
                          actual_initial: Optional[float],
                          consensus_value: Optional[float]) -> Optional[float]:
    """Compute raw surprise when both values exist."""
    if actual_initial is None or consensus_value is None:
        return None
    return actual_initial - consensus_value


# --- Canonical Event Measures by Family ---

FAMILY_MEASURES: dict[str, dict[str, Any]] = {
    "us_cpi": {
        "primary_measure": "seasonally_adjusted_mom_percent",
        "secondary_measures": ["unadjusted_yoy_percent", "index_level"],
        "default_unit": "pct_change_mom",
    },
    "us_core_cpi": {
        "primary_measure": "seasonally_adjusted_mom_percent",
        "secondary_measures": ["unadjusted_yoy_percent", "index_level"],
        "default_unit": "pct_change_mom",
    },
    "us_nonfarm_payrolls": {
        "primary_measure": "payroll_change_thousands",
        "secondary_measures": [],
        "default_unit": "thousands",
    },
    "us_unemployment_rate": {
        "primary_measure": "unemployment_rate_percent",
        "secondary_measures": [],
        "default_unit": "percent",
    },
    "us_core_pce": {
        "primary_measure": "seasonally_adjusted_mom_percent",
        "secondary_measures": ["unadjusted_yoy_percent", "index_level"],
        "default_unit": "pct_change_mom",
    },
    "us_fomc_rate_decision": {
        "primary_measure": "percent_range_midpoint",
        "secondary_measures": ["change_basis_points"],
        "default_unit": "percent_range_midpoint",
    },
}


# --- Main Contract: MacroReleaseEventV1 ---


@dataclass
class MacroReleaseEventV1:
    """A single canonical macro-economic release event.

    V2 fields:
    - release_time_quality, release_time_verified, release_time_source_url
    - actual_value_status, measure_type, primary_measure, secondary_measures
    - event_alignment_eligible, strategy_replay_eligible
    - logical_event_key, provider_observation_refs
    """
    # Identity
    event_id: str = ""
    logical_event_key: str = ""
    event_family: str = ""
    country: str = "US"
    currency: str = "USD"

    # Reference period
    reference_period: str = ""

    # Release time (verified)
    scheduled_release_at_utc: str = ""
    actual_release_at_utc: str = ""
    release_time_timezone: str = "America/New_York"
    release_time_quality: str = "missing"
    release_time_verified: bool = False
    release_time_source_url: str = ""
    release_time_source_snapshot_id: str = ""
    event_alignment_eligible: bool = False

    # Values
    actual_initial: Optional[float] = None
    actual_initial_unit: str = ""
    actual_value_status: str = "missing"
    measure_type: str = ""
    primary_measure: str = ""
    secondary_measures: list[str] = field(default_factory=list)
    strategy_replay_eligible: bool = False

    # Prior / revision
    prior_as_known_then: Optional[float] = None
    prior_revised_latest: Optional[float] = None
    revision_status: str = "initial"

    # Official source
    official_source_name: str = ""
    official_source_url: str = ""
    official_release_id: str = ""
    official_document_hash: str = ""

    # Consensus
    consensus_value: Optional[float] = None
    consensus_unit: str = ""
    consensus_observed_at_utc: Optional[str] = None
    consensus_source_count: int = 0
    point_in_time_quality: str = "missing"
    consensus_aggregation_method: str = ""
    consensus_independence_groups: list[str] = field(default_factory=list)

    # Surprise
    surprise_raw: Optional[float] = None
    surprise_standardized: Optional[float] = None
    surprise_method: str = ""
    surprise_window: str = ""
    surprise_sample_count: int = 0

    # Provenance
    as_known_then_cutoff_utc: str = ""
    current_best_generated_at_utc: str = ""
    first_seen_at_utc: str = ""
    retrieved_at_utc: str = ""
    provider_observation_refs: list[str] = field(default_factory=list)
    data_quality_flags: list[str] = field(default_factory=list)
    provenance_refs: list[str] = field(default_factory=list)

    def __post_init__(self):
        now = utc_now()
        if not self.logical_event_key and self.event_family and self.reference_period:
            self.logical_event_key = generate_logical_event_key(
                self.country, self.event_family, self.reference_period,
            )
        if not self.event_id and self.logical_event_key and self.actual_release_at_utc:
            self.event_id = generate_event_id(self.logical_event_key, self.actual_release_at_utc)

        if not self.first_seen_at_utc:
            self.first_seen_at_utc = now
        if not self.retrieved_at_utc:
            self.retrieved_at_utc = now
        if not self.as_known_then_cutoff_utc:
            self.as_known_then_cutoff_utc = self.actual_release_at_utc
        if not self.current_best_generated_at_utc:
            self.current_best_generated_at_utc = now
        if not self.primary_measure and self.event_family in FAMILY_MEASURES:
            self.primary_measure = FAMILY_MEASURES[self.event_family]["primary_measure"]
            self.secondary_measures = list(FAMILY_MEASURES[self.event_family]["secondary_measures"])
        if not self.measure_type:
            self.measure_type = self.primary_measure
        if self.surprise_raw is None and self.actual_initial is not None and self.consensus_value is not None:
            self.surprise_raw = compute_surprise_raw(
                self.event_family, self.actual_initial, self.consensus_value,
            )
        if self.event_alignment_eligible and not self.release_time_verified:
            self.event_alignment_eligible = False
        if self.strategy_replay_eligible and self.actual_value_status not in (
            "verified_initial_from_release", "derived_from_verified_release_table",
        ):
            self.strategy_replay_eligible = False

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for f in __import__("dataclasses").fields(self):
            val = getattr(self, f.name)
            if isinstance(val, Enum):
                result[f.name] = val.value
            else:
                result[f.name] = val
        return result


# --- Provider Observation ---


@dataclass
class MacroReleaseObservationV1:
    """A single provider observation of a macro release.

    Multiple observations may correspond to one canonical event.
    """
    observation_id: str = ""
    event_id: str = ""
    logical_event_key: str = ""
    provider: str = ""
    series_id: str = ""
    source_record_id: str = ""
    observed_value: Optional[float] = None
    measure_type: str = ""
    source_snapshot_id: str = ""
    observation_quality: str = "missing"
    retrieved_at_utc: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.retrieved_at_utc:
            self.retrieved_at_utc = utc_now()

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for f in __import__("dataclasses").fields(self):
            val = getattr(self, f.name)
            if isinstance(val, Enum):
                result[f.name] = val.value
            else:
                result[f.name] = val
        return result


# --- Consensus Observation ---


@dataclass
class MacroConsensusObservationV1:
    """A single consensus observation from one source."""
    consensus_observation_id: str = ""
    event_id: str = ""
    source_name: str = ""
    source_url: str = ""
    published_at_utc: str = ""
    observed_at_utc: str = ""
    consensus_value: float = 0.0
    consensus_unit: str = ""
    estimate_type: str = "consensus_median"
    point_in_time_quality: str = "reconstructed_multi_source"
    archive_method: str = ""
    content_hash: str = ""
    independence_group: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.consensus_observation_id and self.event_id:
            self.consensus_observation_id = generate_consensus_observation_id(
                self.event_id, self.source_name,
                self.published_at_utc, self.consensus_value,
            )
        if not self.observed_at_utc:
            self.observed_at_utc = utc_now()

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for f in __import__("dataclasses").fields(self):
            val = getattr(self, f.name)
            if isinstance(val, Enum):
                result[f.name] = val.value
            else:
                result[f.name] = val
        return result


# --- Revision Record ---


@dataclass
class MacroRevisionRecordV1:
    """A single revision to a released value."""
    revision_id: str = ""
    event_id: str = ""
    series_id: str = ""
    reference_period: str = ""
    revision_published_at_utc: str = ""
    previous_value: float = 0.0
    revised_value: float = 0.0
    revision_sequence: int = 1
    source_url: str = ""
    source_snapshot_id: str = ""
    content_hash: str = ""
    first_seen_at_utc: str = ""

    def __post_init__(self):
        if not self.revision_id and self.event_id:
            self.revision_id = generate_revision_id(
                self.event_id, self.revision_published_at_utc,
                self.previous_value, self.revised_value,
            )
        if not self.first_seen_at_utc:
            self.first_seen_at_utc = utc_now()

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for f in __import__("dataclasses").fields(self):
            val = getattr(self, f.name)
            if isinstance(val, Enum):
                result[f.name] = val.value
            else:
                result[f.name] = val
        return result


# --- Source Snapshot ---


@dataclass
class MacroSourceSnapshotV1:
    """Metadata about a real raw data fetch."""
    snapshot_id: str = ""
    provider: str = ""
    source_url: str = ""
    retrieved_at_utc: str = ""
    published_at_utc: str = ""
    content_type: str = ""
    sha256: str = ""
    local_path: str = ""
    http_status: int = 0
    license_note: str = ""
    parse_status: str = "pending"
    parse_error: str = ""

    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = generate_snapshot_id(
                self.provider, self.source_url, self.retrieved_at_utc,
            )

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for f in __import__("dataclasses").fields(self):
            val = getattr(self, f.name)
            if isinstance(val, Enum):
                result[f.name] = val.value
            else:
                result[f.name] = val
        return result


# --- As-Of Query Engine ---


class MacroAsOfEngine:
    """Provides point-in-time as-of queries for macro events."""

    @staticmethod
    def get_release_as_of(
        event: MacroReleaseEventV1,
        revisions: list[MacroRevisionRecordV1],
        as_of_utc: str,
    ) -> MacroReleaseEventV1:
        as_of_dt = utc_parse(as_of_utc)
        release_dt = utc_parse(event.actual_release_at_utc)

        if as_of_dt < release_dt:
            result = MacroReleaseEventV1(
                event_id=event.event_id,
                logical_event_key=event.logical_event_key,
                event_family=event.event_family,
                country=event.country,
                currency=event.currency,
                reference_period=event.reference_period,
                actual_release_at_utc=event.actual_release_at_utc,
                actual_initial=None,
                prior_as_known_then=event.prior_as_known_then,
                as_known_then_cutoff_utc=as_of_utc,
            )
            return result

        best_value = event.actual_initial
        best_seq = 0
        sorted_revisions = sorted(
            revisions,
            key=lambda r: (r.revision_published_at_utc, r.revision_sequence),
        )
        for rev in sorted_revisions:
            rev_dt = utc_parse(rev.revision_published_at_utc)
            if rev_dt <= as_of_dt and rev.revision_sequence > best_seq:
                best_value = rev.revised_value
                best_seq = rev.revision_sequence

        result = MacroReleaseEventV1(
            event_id=event.event_id,
            logical_event_key=event.logical_event_key,
            event_family=event.event_family,
            country=event.country,
            currency=event.currency,
            reference_period=event.reference_period,
            actual_release_at_utc=event.actual_release_at_utc,
            actual_initial=event.actual_initial,
            prior_as_known_then=event.prior_as_known_then,
            actual_initial_unit=event.actual_initial_unit,
            as_known_then_cutoff_utc=as_of_utc,
        )
        if best_seq > 0:
            result.prior_revised_latest = best_value
        else:
            result.prior_revised_latest = event.actual_initial
        return result

    @staticmethod
    def get_consensus_as_of(
        observations: list[MacroConsensusObservationV1],
        as_of_utc: str,
    ) -> list[MacroConsensusObservationV1]:
        as_of_dt = utc_parse(as_of_utc)
        return [obs for obs in observations if utc_parse(obs.published_at_utc) <= as_of_dt]

    @staticmethod
    def get_revision_chain(
        event_id: str, revisions: list[MacroRevisionRecordV1],
    ) -> list[MacroRevisionRecordV1]:
        return sorted(
            [r for r in revisions if r.event_id == event_id],
            key=lambda r: (r.revision_published_at_utc, r.revision_sequence),
        )

    @staticmethod
    def get_current_best(
        event: MacroReleaseEventV1, revisions: list[MacroRevisionRecordV1],
    ) -> Optional[float]:
        if not revisions:
            return event.actual_initial
        sorted_revs = sorted(
            revisions,
            key=lambda r: (r.revision_published_at_utc, r.revision_sequence),
        )
        return sorted_revs[-1].revised_value
