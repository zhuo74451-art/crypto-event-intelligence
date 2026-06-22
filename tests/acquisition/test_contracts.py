"""Contract and time tests — 25+ tests."""

import pytest, json, copy
from datetime import datetime, timezone
from market_radar.acquisition.contracts import *
from market_radar.acquisition.contracts.timestamps import (
    utc_now, FiveTimestamps, TimestampEvidence, TimestampQuality, TimestampAnomaly,
)
from market_radar.acquisition.contracts.source import (
    SourceContract, AuthorityTier, SourceRole, AcquisitionMethod,
)
from market_radar.acquisition.contracts.observation import (
    ObservationStatus, NormalizedObservation,
)
from market_radar.acquisition.contracts.revision import (
    RevisionType, RevisionRecord, RevisionLineage,
)
from market_radar.acquisition.contracts.health import (
    HealthStatus, DriftSeverity, HealthIndicator, SourceHealthReport, ParserDriftReport,
)
from market_radar.acquisition.contracts.replay import (
    ReplayMode, ReplayQuery, ReplayResult,
)
from market_radar.acquisition.contracts.raw_document import RawDocument


# ── FiveTimestamps tests ─────────────────────────────────────────────

def test_five_timestamps_all_present():
    now = utc_now()
    ts = FiveTimestamps(
        published_at=TimestampEvidence(now, TimestampQuality.EXPLICIT_SOURCE),
        effective_at=TimestampEvidence(now, TimestampQuality.INFERRED_FROM_CONTENT),
        updated_at=TimestampEvidence(now, TimestampQuality.HTTP_HEADER),
        first_seen_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
        retrieved_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
    )
    assert ts.published_at.is_present()
    assert ts.effective_at.is_present()
    assert ts.updated_at.is_present()
    assert ts.first_seen_at.is_present()
    assert ts.retrieved_at.is_present()
    d = ts.to_dict()
    assert "published_at" in d and "retrieved_at" in d


def test_five_timestamps_first_seen_not_after_retrieved():
    now = utc_now()
    ts = FiveTimestamps(
        first_seen_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
        retrieved_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
    )
    warnings = ts.validate()
    assert len(warnings) == 0

    # If first_seen > retrieved, validate should warn
    earlier = datetime(2024, 1, 1, tzinfo=timezone.utc)
    later = datetime(2024, 1, 2, tzinfo=timezone.utc)
    ts_bad = FiveTimestamps(
        first_seen_at=TimestampEvidence(later, TimestampQuality.RETRIEVAL_ONLY),
        retrieved_at=TimestampEvidence(earlier, TimestampQuality.RETRIEVAL_ONLY),
    )
    warnings_bad = ts_bad.validate()
    assert len(warnings_bad) == 1
    assert "first_seen_at" in warnings_bad[0]


def test_five_timestamps_missing_with_reason():
    ts = FiveTimestamps(
        published_at=TimestampEvidence(
            value=None, quality=TimestampQuality.UNKNOWN,
            missing_reason="Not provided by source",
        ),
    )
    assert not ts.published_at.is_present()
    assert ts.published_at.missing_reason == "Not provided by source"


def test_timestamp_quality_enum_values():
    assert TimestampQuality.EXPLICIT_SOURCE.value == "explicit_source"
    assert TimestampQuality.STRUCTURED_METADATA.value == "structured_metadata"
    assert TimestampQuality.HTTP_HEADER.value == "http_header"
    assert TimestampQuality.INFERRED_FROM_CONTENT.value == "inferred_from_content"
    assert TimestampQuality.RETRIEVAL_ONLY.value == "retrieval_only"
    assert TimestampQuality.CONFLICTING.value == "conflicting"
    assert TimestampQuality.UNKNOWN.value == "unknown"
    assert len(TimestampQuality) == 7


def test_timestamp_anomaly_enum_values():
    assert TimestampAnomaly.NONE.value == "none"
    assert TimestampAnomaly.BEFORE_1970.value == "before_1970"
    assert TimestampAnomaly.FAR_FUTURE.value == "far_future"
    assert TimestampAnomaly.BEFORE_PUBLISHED.value == "before_published"
    assert TimestampAnomaly.AFTER_RETRIEVED.value == "after_retrieved"
    assert TimestampAnomaly.CONFLICTS_WITH_OTHER.value == "conflicts_with_other"
    assert TimestampAnomaly.MISSING_REASON.value == "missing_reason"
    assert TimestampAnomaly.SUSPICIOUS_ACCURACY.value == "suspicious_accuracy"
    assert len(TimestampAnomaly) == 8


def test_utc_now_is_timezone_aware():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc


# ── SourceContract tests ─────────────────────────────────────────────

def test_source_contract_required_fields():
    sc = SourceContract(
        source_id="src-1",
        source_name="Source One",
    )
    assert sc.source_id == "src-1"
    assert sc.source_name == "Source One"
    assert sc.enabled is True


def test_source_contract_authority_tier_enum():
    sc = SourceContract(
        source_id="a", source_name="A",
        authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
    )
    assert sc.authority_tier == AuthorityTier.PRIMARY_OFFICIAL
    assert sc.authority_tier.value == "primary_official"


def test_source_contract_role_enum():
    roles = (
        SourceRole.AUTHORITATIVE_EVIDENCE,
        SourceRole.RESEARCH,
    )
    sc = SourceContract(source_id="b", source_name="B", roles=roles)
    assert SourceRole.AUTHORITATIVE_EVIDENCE in sc.roles
    assert SourceRole.RESEARCH in sc.roles


def test_source_contract_round_trip():
    sc = SourceContract(
        source_id="rt", source_name="RoundTrip",
        authority_tier=AuthorityTier.SPECIALIZED_INDEPENDENT,
        roles=(SourceRole.DISCOVERY, SourceRole.EXPECTATION),
        primary_method=AcquisitionMethod.RSS,
        independence_group="crypto",
        enabled=True,
    )
    d = sc.to_dict()
    sc2 = SourceContract.from_dict(d)
    assert sc2.source_id == sc.source_id
    assert sc2.source_name == sc.source_name
    assert sc2.authority_tier == sc.authority_tier
    assert sc2.roles == sc.roles
    assert sc2.primary_method == sc.primary_method
    assert sc2.independence_group == sc.independence_group


def test_source_contract_no_market_direction():
    """SourceContract must NOT contain bullish/bearish or signal fields."""
    sc = SourceContract(source_id="safe", source_name="Safe")
    d = sc.to_dict()
    assert "bullish" not in d
    assert "bearish" not in d
    assert "signal" not in d
    assert "market_direction" not in d


# ── RawDocument tests ────────────────────────────────────────────────

def test_raw_document_fields():
    doc = RawDocument(
        raw_document_id="doc-1",
        source_id="src-1",
        http_status=200,
        payload_size=1024,
    )
    assert doc.raw_document_id == "doc-1"
    assert doc.http_status == 200
    d = doc.to_dict()
    assert d["http_status"] == 200
    assert d["payload_size"] == 1024


# ── NormalizedObservation tests ──────────────────────────────────────

def test_observation_no_bullish_bearish():
    obs = NormalizedObservation(
        observation_id="obs-1",
        source_id="src-1",
        title="Test",
    )
    d = obs.to_dict()
    assert "bullish" not in d
    assert "bearish" not in d
    assert "signal_score" not in d


def test_observation_status_enum():
    assert ObservationStatus.VALID.value == "valid"
    assert ObservationStatus.PARTIAL.value == "partial"
    assert ObservationStatus.CONFLICTING.value == "conflicting"
    assert ObservationStatus.STALE.value == "stale"
    assert ObservationStatus.RETRACTED.value == "retracted"
    assert ObservationStatus.PARSE_FAILED.value == "parse_failed"
    assert ObservationStatus.UNSUPPORTED.value == "unsupported"
    assert len(ObservationStatus) == 7


# ── Revision tests ───────────────────────────────────────────────────

def test_revision_type_enum_all_values():
    assert RevisionType.FIRST_SEEN.value == "first_seen"
    assert RevisionType.NO_CHANGE.value == "no_change"
    assert RevisionType.CONTENT_CHANGED.value == "content_changed"
    assert RevisionType.METADATA_CHANGED.value == "metadata_changed"
    assert RevisionType.CORRECTED.value == "corrected"
    assert RevisionType.RETRACTED.value == "retracted"
    assert RevisionType.DELETED.value == "deleted"
    assert RevisionType.RESTORED.value == "restored"
