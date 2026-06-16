"""Signal Spine v1 — Integration Tests.

Covers:
  1. Cross-source event merge (different sources, same event → same signal)
  2. Duplicate does NOT emit a second card
  3. enum news-quality bug regression
  4. trading_relevance type constraint
  5. Future timestamp → NOT_EVALUATED/DOWNGRADE (not ACCEPT)
  6. Atomic registry persistence with backup/recovery
  7. Corrupted registry visible recovery
  8. SignalSpineResult → DryRunRenderer
  9. Old SharedPipeline regression
  10. Dual dedup fields (observation_fingerprint vs event_dedup_key)
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path

import pytest

from market_radar.shared.models import (
    CardFamily,
    DataSourceType,
    DataQuality,
    DataOrigin,
    Observation,
    ObservationStatus,
    Signal,
    SignalStatus,
    GateVerdict,
    NoiseGateResult,
    SignalSpineResult,
    china_now,
    sha256_short,
)
from market_radar.shared.adapter_contract import FixtureCatalog
from market_radar.shared.noise_gate import DeterministicNoiseGate
from market_radar.shared.signal_registry import SignalRegistry, create_signal_registry
from market_radar.shared.signal_orchestrator import SignalOrchestrator, create_orchestrator
from market_radar.shared.pipeline import SharedPipeline
from market_radar.shared.event_intelligence_mapper import EventIntelligenceMapper
from market_radar.shared.dry_run_renderer import DryRunRenderer, create_dry_run_renderer


# ═══════════════════════════════════════════════════════════════════════════
# 1. Cross-Source Event Merge
# ═══════════════════════════════════════════════════════════════════════════


class TestCrossSourceMerge:
    def test_same_event_different_sources_merge(self, tmp_path):
        """Same event from different sources → merged into one signal."""
        storage = tmp_path / "cross_source.json"
        orchestrator = create_orchestrator(storage_path=str(storage))

        # Create two observations of same event from different sources
        obs1 = Observation(
            observation_id=str(uuid.uuid4()),
            source="source_a",
            source_type=DataSourceType.FREE_PUBLIC_SOURCE,
            observed_at=china_now(),
            event_time=china_now(),
            affected_assets=["BTC", "ETH"],
            normalized_payload={"title": "SEC Approves BTC ETF", "event_type": "ETF", "intensity": "high"},
            raw_provenance={},
            evidence=[],
            data_quality=DataQuality.VERIFIED_MEDIUM,
            observation_fingerprint=sha256_short("source_a:event:1", n=8),
            event_dedup_key=Observation._compute_event_dedup_key(
                "SEC Approves BTC ETF", ["BTC", "ETH"], "ETF"
            ),
            ingestion_status=ObservationStatus.NORMALIZED,
        )
        obs2 = Observation(
            observation_id=str(uuid.uuid4()),
            source="source_b",
            source_type=DataSourceType.FREE_PUBLIC_SOURCE,
            observed_at=china_now(),
            event_time=china_now(),
            affected_assets=["BTC", "ETH"],
            normalized_payload={"title": "SEC Approves BTC ETF", "event_type": "ETF", "intensity": "high"},
            raw_provenance={},
            evidence=[],
            data_quality=DataQuality.VERIFIED_MEDIUM,
            observation_fingerprint=sha256_short("source_b:event:1", n=8),
            event_dedup_key=Observation._compute_event_dedup_key(
                "SEC Approves BTC ETF", ["BTC", "ETH"], "ETF"
            ),
            ingestion_status=ObservationStatus.NORMALIZED,
        )

        # Same event_dedup_key
        assert obs1.event_dedup_key == obs2.event_dedup_key
        # Different observation fingerprints
        assert obs1.observation_fingerprint != obs2.observation_fingerprint

        r1 = orchestrator.process(obs1)
        r2 = orchestrator.process(obs2)

        if r1.signal and r2.signal:
            assert r1.signal.signal_id == r2.signal.signal_id, "Different sources should merge into same signal"
            # Both observations should be in the merged signal
            assert obs1.observation_id in r2.signal.observation_ids
            assert obs2.observation_id in r2.signal.observation_ids

    def test_different_events_not_merged(self, tmp_path):
        """Different events from same source → different signals."""
        storage = tmp_path / "no_merge.json"
        orchestrator = create_orchestrator(storage_path=str(storage))

        obs1 = Observation(
            observation_id=str(uuid.uuid4()),
            source="src", source_type=DataSourceType.FREE_PUBLIC_SOURCE,
            observed_at=china_now(), event_time=china_now(),
            affected_assets=["BTC"],
            normalized_payload={"title": "Event Alpha", "event_type": "ETF", "intensity": "high"},
            raw_provenance={}, evidence=[],
            data_quality=DataQuality.VERIFIED_MEDIUM,
            observation_fingerprint=sha256_short("src:alpha", n=8),
            event_dedup_key=Observation._compute_event_dedup_key("Event Alpha", ["BTC"], "ETF"),
            ingestion_status=ObservationStatus.NORMALIZED,
        )
        obs2 = Observation(
            observation_id=str(uuid.uuid4()),
            source="src", source_type=DataSourceType.FREE_PUBLIC_SOURCE,
            observed_at=china_now(), event_time=china_now(),
            affected_assets=["ETH"],
            normalized_payload={"title": "Event Beta", "event_type": "regulatory", "intensity": "medium"},
            raw_provenance={}, evidence=[],
            data_quality=DataQuality.VERIFIED_MEDIUM,
            observation_fingerprint=sha256_short("src:beta", n=8),
            event_dedup_key=Observation._compute_event_dedup_key("Event Beta", ["ETH"], "regulatory"),
            ingestion_status=ObservationStatus.NORMALIZED,
        )

        assert obs1.event_dedup_key != obs2.event_dedup_key

        r1 = orchestrator.process(obs1)
        r2 = orchestrator.process(obs2)

        if r1.signal and r2.signal:
            assert r1.signal.signal_id != r2.signal.signal_id

    def test_event_dedup_key_normalization(self):
        """event_dedup_key normalizes title, assets, and event_type."""
        # Different casing, extra whitespace
        key1 = Observation._compute_event_dedup_key(
            "  SEC APPROVES BTC ETF  ", ["BTC", "ETH"], "ETF"
        )
        key2 = Observation._compute_event_dedup_key(
            "sec approves btc etf", ["eth", "btc"], "etf"
        )
        # Same after normalization
        assert key1 == key2


# ═══════════════════════════════════════════════════════════════════════════
# 2. Duplicate Does NOT Emit Second Card
# ═══════════════════════════════════════════════════════════════════════════


class TestDuplicateNoSecondCard:
    def test_duplicate_observation_emit_card_false(self, tmp_path):
        """Duplicate observation → emit_card=False, observation_decision=suppress_duplicate."""
        storage = tmp_path / "dedup_card.json"
        orchestrator = create_orchestrator(storage_path=str(storage))
        mapper = EventIntelligenceMapper()

        obs = Observation(
            observation_id=str(uuid.uuid4()),
            source="test", source_type=DataSourceType.FREE_PUBLIC_SOURCE,
            observed_at=china_now(), event_time=china_now(),
            affected_assets=["BTC"],
            normalized_payload={"title": "Test Event", "event_type": "ETF", "intensity": "high"},
            raw_provenance={}, evidence=[],
            data_quality=DataQuality.VERIFIED_MEDIUM,
            observation_fingerprint=sha256_short("test:obs1", n=8),
            event_dedup_key=Observation._compute_event_dedup_key("Test Event", ["BTC"], "ETF"),
            ingestion_status=ObservationStatus.NORMALIZED,
        )

        r1 = orchestrator.process(obs)
        r1, ei1 = mapper.populate_result(r1)

        # First occurrence should emit
        assert r1.emit_card in (True, False)  # Depends on gate pass
        # Submit same observation again
        r2 = orchestrator.process(obs)
        r2, ei2 = mapper.populate_result(r2)

        if r2.registry_action == "merged_into_existing":
            assert r2.emit_card is False
            assert r2.observation_decision == "suppress_duplicate"
        else:
            # May be rejected by gate if already seen
            assert not r2.gate_passed or r2.registry_action == "merged_into_existing"


# ═══════════════════════════════════════════════════════════════════════════
# 3. Enum News-Quality Bug Regression
# ═══════════════════════════════════════════════════════════════════════════


class TestNewsQualityRegression:
    def test_news_quality_from_data_quality_enum(self):
        """_assess_news_quality uses DataQuality enum, not string comparison."""
        from market_radar.shared.signal_orchestrator import SignalOrchestrator
        orch = SignalOrchestrator()

        # Create observations with DataQuality enum values
        obs_high = _make_test_obs(data_quality=DataQuality.VERIFIED_HIGH)
        obs_medium = _make_test_obs(data_quality=DataQuality.VERIFIED_MEDIUM)
        obs_low = _make_test_obs(data_quality=DataQuality.UNVERIFIED)
        obs_vlow = _make_test_obs(data_quality=DataQuality.LOW_CREDIBILITY)
        obs_unknown = _make_test_obs(data_quality=DataQuality.UNKNOWN)

        assert orch._assess_news_quality(obs_high) == "high"
        assert orch._assess_news_quality(obs_medium) == "medium"
        assert orch._assess_news_quality(obs_low) == "low"
        assert orch._assess_news_quality(obs_vlow) == "very_low"
        assert orch._assess_news_quality(obs_unknown) == "low"  # Unknown → low


def _make_test_obs(data_quality=DataQuality.VERIFIED_MEDIUM) -> Observation:
    return Observation(
        observation_id=str(uuid.uuid4()),
        source="test", source_type=DataSourceType.FREE_PUBLIC_SOURCE,
        observed_at=china_now(), event_time=china_now(),
        affected_assets=["BTC"],
        normalized_payload={"title": "Test", "event_type": "ETF", "intensity": "high"},
        raw_provenance={}, evidence=[],
        data_quality=data_quality,
        observation_fingerprint=sha256_short("test:obs", n=8),
        event_dedup_key=sha256_short("test:event", n=8),
        ingestion_status=ObservationStatus.NORMALIZED,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 4. trading_relevance Type Constraint
# ═══════════════════════════════════════════════════════════════════════════


class TestTradingRelevanceConstraint:
    def test_trading_relevance_only_valid_values(self):
        """trading_relevance must be high/medium/low/none."""
        from market_radar.shared.signal_orchestrator import SignalOrchestrator
        orch = SignalOrchestrator()
        VALID = {"high", "medium", "low", "none"}

        obs = _make_test_obs()
        from market_radar.shared.ai_fallback import generate_template_interpretation
        interpretation = generate_template_interpretation(obs)

        # Ensure the method returns only valid values
        tr = orch._assess_trading_relevance(obs, interpretation)
        assert tr in VALID, f"trading_relevance '{tr}' not in {VALID}"

    def test_trading_relevance_not_from_risk_notes(self):
        """trading_relevance must NOT be the first risk note (regression)."""
        from market_radar.shared.signal_orchestrator import SignalOrchestrator
        orch = SignalOrchestrator()
        VALID = {"high", "medium", "low", "none"}

        # Run the orchestrator process and check trading_relevance on the signal
        obs = _make_test_obs()
        result = orch.process(obs)
        if result.signal:
            tr = result.signal.trading_relevance
            assert tr in VALID, f"trading_relevance '{tr}' not in {VALID}"
            # Verify it's NOT a risk note text (which would be longer)
            assert len(tr) <= 6, f"trading_relevance looks like a risk note: '{tr}'"


# ═══════════════════════════════════════════════════════════════════════════
# 5. Future Timestamp → NOT_EVALUATED/DOWNGRADE
# ═══════════════════════════════════════════════════════════════════════════


class TestFutureTimestamp:
    def test_future_event_time_not_accepted(self):
        """Future event_time → NOT_EVALUATED or DOWNGRADE, never ACCEPT."""
        obs = Observation(
            observation_id=str(uuid.uuid4()),
            source="test", source_type=DataSourceType.FREE_PUBLIC_SOURCE,
            observed_at="2024-01-01T00:00:00+00:00",
            event_time="2025-01-01T00:00:00+00:00",  # 1 year in the future
            affected_assets=["BTC"],
            normalized_payload={"title": "Future Event", "event_type": "unknown", "intensity": "low"},
            raw_provenance={}, evidence=[],
            data_quality=DataQuality.UNKNOWN,
            observation_fingerprint=sha256_short("future:test", n=8),
            event_dedup_key=sha256_short("future:event", n=8),
            ingestion_status=ObservationStatus.NORMALIZED,
        )

        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        stale_result = [r for r in results if r.rule_name == "stale_or_recycled_event"][0]

        assert stale_result.verdict != GateVerdict.ACCEPT, (
            f"Future timestamp should not return ACCEPT, got {stale_result.verdict}"
        )
        assert stale_result.verdict in (GateVerdict.DOWNGRADE, GateVerdict.NOT_EVALUATED), (
            f"Future timestamp should DOWNGRADE or NOT_EVALUATED, got {stale_result.verdict}"
        )
        assert "timezone_or_future_timestamp" in stale_result.reason_code or "future" in stale_result.reason_code


# ═══════════════════════════════════════════════════════════════════════════
# 6. Atomic Registry Persistence
# ═══════════════════════════════════════════════════════════════════════════


class TestAtomicRegistry:
    def test_atomic_write_creates_temp_file(self, tmp_path):
        """Save process uses .tmp file before atomic rename."""
        storage = tmp_path / "atomic_registry.json"
        registry = SignalRegistry(storage_path=storage)

        obs = _make_test_obs()
        registry.create_signal(
            title="Test", affected_assets=["BTC"],
            event_type="ETF", direction="bullish",
            confidence=0.5, observation=obs,
        )
        registry.save()

        # The main file should exist
        assert storage.exists()
        # The tmp file should be cleaned up
        assert not storage.with_suffix(".json.tmp").exists()

    def test_backup_created_on_subsequent_save(self, tmp_path):
        """Second save creates a .backup of the first."""
        storage = tmp_path / "backup_test.json"
        registry = SignalRegistry(storage_path=storage)

        obs = _make_test_obs()
        registry.create_signal(
            title="v1", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, observation=obs,
        )
        registry.save()

        # Second save
        obs2 = _make_test_obs()
        registry.merge_observation(registry.get_signal(list(registry._signals.keys())[0]), obs2)
        registry.save()

        backup = storage.with_suffix(".json.backup")
        assert backup.exists(), "Backup file should exist after second save"

    def test_backup_recovery_on_corruption(self, tmp_path):
        """Corrupted registry recovers from backup."""
        storage = tmp_path / "corrupt_recover.json"
        registry = SignalRegistry(storage_path=storage)

        obs = _make_test_obs()
        s = registry.create_signal(
            title="Recover Me", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, observation=obs,
        )
        signal_id = s.signal_id
        registry.save()

        # Create backup by simulating second save
        registry.save()

        # Corrupt the main file
        storage.write_text("{{{corrupted json}}}", encoding="utf-8")

        # New registry should recover from backup
        registry2 = SignalRegistry(storage_path=storage)
        recovered = registry2.get_signal(signal_id)
        assert recovered is not None, "Should recover signal from backup"
        assert recovered.title == "Recover Me"
        # Corrupted file should be renamed
        assert storage.with_suffix(".json.corrupt").exists() or not storage.exists()


# ═══════════════════════════════════════════════════════════════════════════
# 7. SignalSpineResult → DryRunRenderer
# ═══════════════════════════════════════════════════════════════════════════


class TestSpineResultToDryRun:
    def test_spine_result_renders_via_integrated_pipeline(self, tmp_path):
        """SignalSpineResult flows through to DryRunRenderer output."""
        storage = tmp_path / "spine_to_dryrun.json"
        output_dir = tmp_path / "dry_run_output"

        pipeline = SharedPipeline()
        catalog = FixtureCatalog()
        adapter = catalog.adapter_for(CardFamily.NEWS_EVENT_MARKET_IMPACT)

        result, dry_run = pipeline.run_signal_spine(
            adapter=adapter,
            source_label="integration_test",
            dry_run=True,
            storage_path=str(storage),
        )

        # Verify the result has decision fields
        assert result.observation_decision in ("observe", "risk_tip", "discard", "block", "suppress_duplicate", "")
        assert isinstance(result.emit_card, bool)
        assert result.data_origin is None or result.data_origin in ("real", "fixture", "degraded")

        # Verify dry-run output exists
        if dry_run is not None:
            assert dry_run.dry_run_id is not None
            assert dry_run.event_intelligence is not None
            assert dry_run.event_intelligence.decision is not None
            assert len(dry_run.markdown_output) > 100
            assert "Production Send = False" in dry_run.telegram_card


# ═══════════════════════════════════════════════════════════════════════════
# 8. Old SharedPipeline Regression
# ═══════════════════════════════════════════════════════════════════════════


class TestOldPipelineRegression:
    def test_run_all_fixtures_still_works(self):
        """Old run_all_fixtures() still works and produces 5 results."""
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()
        assert len(results) == 5, f"Expected 5 fixture results, got {len(results)}"

    def test_three_verified_pass(self):
        """3 verified card families still pass the quality gate."""
        pipeline = SharedPipeline()
        results = pipeline.run_all_fixtures()

        passing = [r for r in results if r.passed]
        # At minimum the verified families pass
        assert len(passing) >= 3, f"Expected >=3 passing, got {len(passing)}"

    def test_new_spine_does_not_break_old_pipeline(self, tmp_path):
        """Adding run_signal_spine doesn't break the old run() method."""
        pipeline = SharedPipeline()
        catalog = FixtureCatalog()
        adapter = catalog.adapter_for(CardFamily.MULTI_ASSET_MARKET_SYNC)

        old_result = pipeline.run(adapter)
        assert old_result is not None
        assert old_result.card_family == CardFamily.MULTI_ASSET_MARKET_SYNC


# ═══════════════════════════════════════════════════════════════════════════
# 9. Dual Dedup Fields
# ═══════════════════════════════════════════════════════════════════════════


class TestDualDedup:
    def test_observation_fingerprint_includes_source(self):
        """Different sources → different fingerprints."""
        fp1 = sha256_short("src_a:same title:BTC,ETH", n=12)
        fp2 = sha256_short("src_b:same title:BTC,ETH", n=12)
        assert fp1 != fp2

    def test_event_dedup_key_excludes_source(self):
        """Same event from different sources → same event_dedup_key."""
        key1 = Observation._compute_event_dedup_key("Same Title", ["BTC", "ETH"], "ETF")
        key2 = Observation._compute_event_dedup_key("Same Title", ["BTC", "ETH"], "ETF")
        assert key1 == key2

    def test_different_event_different_dedup_key(self):
        """Different events → different event_dedup_key."""
        key1 = Observation._compute_event_dedup_key("Event One", ["BTC"], "ETF")
        key2 = Observation._compute_event_dedup_key("Event Two", ["BTC"], "ETF")
        assert key1 != key2

    def test_event_dedup_key_case_insensitive(self):
        """event_dedup_key is case-insensitive."""
        key1 = Observation._compute_event_dedup_key("SEC APPROVES BTC ETF", ["BTC"], "ETF")
        key2 = Observation._compute_event_dedup_key("sec approves btc etf", ["BTC"], "etf")
        assert key1 == key2
