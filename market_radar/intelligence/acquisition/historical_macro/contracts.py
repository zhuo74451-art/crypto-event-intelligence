"""Canonical Python contracts for historical macro-economic evidence.

Mirrors the JSON Schema definitions in schemas/intelligence/historical_macro/
and provides deterministic ID generation, as-of queries, and validation.
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


# --- ID Generation ---


def generate_event_id(country: str, event_family: str,
                      reference_period: str,
                      actual_release_at_utc: str) -> str:
    """Deterministic SHA256-based event ID.

    Same inputs yield same ID regardless of order or runtime.
    """
    payload = "|".join([
        country.strip().upper(),
        event_family.strip().lower(),
        reference_period.strip(),
        validate_utc(actual_release_at_utc),
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


# --- Main Contract: MacroReleaseEventV1 ---


@dataclass
class MacroReleaseEventV1:
    """A single macro-economic release event with values and consensus."""
    event_id: str = ""
    event_family: str = ""
    series_id: str = ""
    country: str = "US"
    currency: str = "USD"

    reference_period: str = ""
    scheduled_release_at_utc: str = ""
    actual_release_at_utc: str = ""
    first_seen_at_utc: str = ""
    retrieved_at_utc: str = ""

    actual_initial: Optional[float] = None
    actual_initial_unit: str = ""
    prior_as_known_then: Optional[float] = None
    prior_revised_latest: Optional[float] = None
    revision_status: str = "initial"

    official_source_name: str = ""
    official_source_url: str = ""
    official_release_id: str = ""
    official_document_hash: str = ""

    consensus_value: Optional[float] = None
    consensus_unit: str = ""
    consensus_observed_at_utc: Optional[str] = None
    consensus_source_count: int = 0
    point_in_time_quality: str = "missing"

    surprise_raw: Optional[float] = None
    surprise_standardized: Optional[float] = None
    surprise_method: str = ""
    surprise_window: str = ""
    surprise_sample_count: int = 0

    as_known_then_cutoff_utc: str = ""
    current_best_generated_at_utc: str = ""

    data_quality_flags: list[str] = field(default_factory=list)
    provenance_refs: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.event_id and self.event_family and self.reference_period and self.actual_release_at_utc:
            self.event_id = generate_event_id(
                self.country, self.event_family,
                self.reference_period, self.actual_release_at_utc,
            )
        if not self.first_seen_at_utc:
            self.first_seen_at_utc = utc_now()
        if not self.retrieved_at_utc:
            self.retrieved_at_utc = utc_now()
        if not self.as_known_then_cutoff_utc:
            self.as_known_then_cutoff_utc = self.actual_release_at_utc
        if not self.current_best_generated_at_utc:
            self.current_best_generated_at_utc = utc_now()
        if self.surprise_raw is None:
            self.surprise_raw = compute_surprise_raw(
                self.event_family, self.actual_initial, self.consensus_value,
            )

    def to_dict(self) -> dict[str, Any]:
        result = {}
        for f in dataclasses.fields(self):
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
        for f in dataclasses.fields(self):
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
        for f in dataclasses.fields(self):
            val = getattr(self, f.name)
            if isinstance(val, Enum):
                result[f.name] = val.value
            else:
                result[f.name] = val
        return result


# --- Source Snapshot ---


@dataclass
class MacroSourceSnapshotV1:
    """Metadata about a raw data fetch."""
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
        for f in dataclasses.fields(self):
            val = getattr(self, f.name)
            if isinstance(val, Enum):
                result[f.name] = val.value
            else:
                result[f.name] = val
        return result



# --- As-Of Query Engine ---


class MacroAsOfEngine:
    """Provides point-in-time as-of queries for macro events.

    Supports historical replay by filtering revisions and consensus
    to those visible at a given UTC time.
    """

    @staticmethod
    def get_release_as_of(
        event: MacroReleaseEventV1,
        revisions: list[MacroRevisionRecordV1],
        as_of_utc: str,
    ) -> MacroReleaseEventV1:
        """Return the event state as known at as_of_utc.

        Uses actual_initial if as_of matches the release time,
        otherwise applies revisions published before as_of_utc.
        """
        as_of_dt = utc_parse(as_of_utc)
        release_dt = utc_parse(event.actual_release_at_utc)

        if as_of_dt < release_dt:
            result = MacroReleaseEventV1(
                event_id=event.event_id,
                event_family=event.event_family,
                series_id=event.series_id,
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
            event_family=event.event_family,
            series_id=event.series_id,
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
        """Return consensus observations published before as_of_utc."""
        as_of_dt = utc_parse(as_of_utc)
        return [
            obs for obs in observations
            if utc_parse(obs.published_at_utc) <= as_of_dt
        ]

    @staticmethod
    def get_revision_chain(
        event_id: str,
        revisions: list[MacroRevisionRecordV1],
    ) -> list[MacroRevisionRecordV1]:
        """Return sorted revision chain for an event."""
        return sorted(
            [r for r in revisions if r.event_id == event_id],
            key=lambda r: (r.revision_published_at_utc, r.revision_sequence),
        )

    @staticmethod
    def get_current_best(
        event: MacroReleaseEventV1,
        revisions: list[MacroRevisionRecordV1],
    ) -> Optional[float]:
        """Return the latest known value (initial or last revision)."""
        if not revisions:
            return event.actual_initial
        sorted_revs = sorted(
            revisions,
            key=lambda r: (r.revision_published_at_utc, r.revision_sequence),
        )
        return sorted_revs[-1].revised_value
