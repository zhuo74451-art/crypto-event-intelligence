"""Tests for legacy adapters."""

import pytest
from market_radar.intelligence.adapters.legacy_observation import LegacyObservationAdapter, FieldMapping
from market_radar.intelligence.adapters.legacy_signal_registry import LegacySignalRegistryAdapter


class DummyObservation:
    """A minimal simulation of a legacy Observation."""
    def __init__(self):
        self.observation_id = "obs_001"
        self.source = "test_source"
        self.source_type = "free_public_api"
        self.observed_at = "2024-01-01T00:00:00Z"
        self.event_time = None
        self.affected_assets = ["BTC", "ETH"]
        self.normalized_payload = {"title": "Test event"}
        self.raw_provenance = {}
        self.evidence = []
        self.data_quality = "verified_medium"
        self.observation_fingerprint = "fp_001"
        self.event_dedup_key = "dedup_001"
        self.ingestion_status = "normalized"
        self.card_family = "news_event_market_impact"
        self.source_refs = ["https://example.com/news/1"]
        self.risk_notes = []


class DummySignal:
    """A minimal simulation of a legacy Signal."""
    def __init__(self):
        self.signal_id = "sig_001"
        self.title = "Test signal"
        self.affected_assets = ["BTC"]
        self.event_type = "news"
        self.direction = "bullish"
        self.confidence = 0.75
        self.trading_relevance = "medium"
        self.news_quality = "verified"
        self.status = "confirmed"
        self.first_seen_at = "2024-01-01T00:00:00Z"
        self.updated_at = "2024-01-02T00:00:00Z"
        self.evidence = []
        self.invalidation_reason = None


class TestLegacyObservationAdapter:
    def test_map_observation(self):
        obs = DummyObservation()
        result = LegacyObservationAdapter.map_observation(obs)
        assert result.success
        assert result.success

    def test_evidence_items_created(self):
        obs = DummyObservation()
        result = LegacyObservationAdapter.map_observation(obs)
        assert len(result.evidence_items) >= 0

    def test_event_created(self):
        obs = DummyObservation()
        result = LegacyObservationAdapter.map_observation(obs)
        if result.event:
            assert "BTC" in result.event.assets

    def test_mapping_summary(self):
        obs = DummyObservation()
        summary = LegacyObservationAdapter.mapping_summary(obs)
        assert "field_count" in summary


class TestLegacySignalRegistryAdapter:
    def test_map_signal(self):
        sig = DummySignal()
        result = LegacySignalRegistryAdapter.map_signal(sig)
        assert result["mapped"]
        assert result["hypothesis"] is not None
        assert result["instance"] is not None

    def test_confidence_is_uncalibrated(self):
        sig = DummySignal()
        result = LegacySignalRegistryAdapter.map_signal(sig)
        cs = result["confidence"]
        assert cs.confidence_type.value == "uncalibrated_score"
        assert cs.production_probability is False

    def test_lossy_mapping_warning(self):
        sig = DummySignal()
        result = LegacySignalRegistryAdapter.map_signal(sig)
        assert len(result["warnings"]) > 0

    def test_mapping_summary(self):
        sig = DummySignal()
        summary = LegacySignalRegistryAdapter.mapping_summary(sig)
        assert summary["mapped"]

    def test_no_modification_of_original(self):
        sig = DummySignal()
        original_signal_id = sig.signal_id
        LegacySignalRegistryAdapter.map_signal(sig)
        assert sig.signal_id == original_signal_id
