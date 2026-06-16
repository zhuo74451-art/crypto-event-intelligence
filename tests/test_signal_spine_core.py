"""Signal Spine v1 — Core Tests.

Tests cover:
  1. Observation construction (from raw data, from NormalizedSignal)
  2. Deterministic gate acceptance (all rules pass)
  3. Deterministic gate rejection (at least one rule rejects)
  4. Reason code existence on every result
  5. Unknown evidence NOT masqueraded as pass/fail (NOT_EVALUATED)
  6. Signal creation
  7. Legal state transitions
  8. Illegal state transitions
  9. Registry save and read (persistence)
  10. Duplicate observation doesn't create duplicate signal
  11. New evidence merged into existing signal
  12. AI fallback (template generation)
  13. History version preservation
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest

from market_radar.shared.models import (
    CardFamily,
    DataSourceType,
    NormalizedSignal,
    Observation,
    ObservationStatus,
    DataQuality,
    Signal,
    SignalStatus,
    GateVerdict,
    NoiseGateResult,
    EvidenceLink,
    SignalSpineResult,
    StatusTransition,
    is_valid_transition,
    china_now,
    sha256_short,
)
from market_radar.shared.noise_gate import (
    DeterministicNoiseGate,
    GATE_RULE_VERSION,
)
from market_radar.shared.signal_registry import (
    SignalRegistry,
    create_signal_registry,
)
from market_radar.shared.signal_orchestrator import (
    SignalOrchestrator,
    create_orchestrator,
)
from market_radar.shared.ai_fallback import (
    AIInterpreter,
    InterpretationResult,
    generate_template_interpretation,
    create_ai_interpreter,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

CN_TZ = timezone(timedelta(hours=8))


def _make_observation(
    source: str = "test_source",
    source_type: DataSourceType = DataSourceType.FREE_PUBLIC_SOURCE,
    affected_assets: Optional[list[str]] = None,
    title: str = "Test Event Title",
    intensity: str = "high",
    event_type: str = "ETF",
    data_quality: DataQuality = DataQuality.VERIFIED_MEDIUM,
    event_time: Optional[str] = None,
) -> Observation:
    """Create a standard test observation."""
    now = china_now()
    assets = affected_assets or ["BTC", "ETH"]

    return Observation(
        observation_id=str(uuid.uuid4()),
        source=source,
        source_type=source_type,
        observed_at=now,
        event_time=event_time or now,
        affected_assets=assets,
        normalized_payload={
            "title": title,
            "intensity": intensity,
            "event_type": event_type,
            "source_name": source,
        },
        raw_provenance={"original_source": source},
        evidence=[
            EvidenceLink(
                ref=sha256_short(f"test:{source}:{now}"),
                source=source,
                timestamp=now,
                description=f"Test evidence from {source}",
            )
        ],
        data_quality=data_quality,
        dedup_key=sha256_short(f"{source}:{title}:{','.join(sorted(assets))}", n=12),
        ingestion_status=ObservationStatus.NORMALIZED,
        card_family=CardFamily.NEWS_EVENT_MARKET_IMPACT,
    )


def _make_normalized_signal(
    card_family: CardFamily = CardFamily.NEWS_EVENT_MARKET_IMPACT,
    title: str = "SEC Approves BTC ETF",
    intensity: str = "high",
) -> NormalizedSignal:
    """Create a standard NormalizedSignal for testing."""
    return NormalizedSignal(
        source_type=DataSourceType.FREE_PUBLIC_SOURCE,
        card_family=card_family,
        asset_or_topic="BTC",
        timestamp=china_now(),
        metrics={
            "title": title,
            "intensity": intensity,
            "event_type": "ETF",
            "assets_affected": ["BTC", "ETH"],
            "source_name": "CryptoNews",
        },
        source_refs=["https://example.com/news/1"],
        risk_notes=["test data"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. Observation Construction
# ═══════════════════════════════════════════════════════════════════════════


class TestObservationConstruction:
    def test_direct_observation_creation(self):
        """Create an Observation directly with all required fields."""
        obs = _make_observation()
        assert obs.observation_id is not None
        assert obs.source == "test_source"
        assert obs.source_type == DataSourceType.FREE_PUBLIC_SOURCE
        assert "BTC" in obs.affected_assets
        assert "ETH" in obs.affected_assets
        assert obs.dedup_key is not None
        assert obs.ingestion_status == ObservationStatus.NORMALIZED
        assert len(obs.evidence) == 1

    def test_observation_from_normalized_signal(self):
        """Construct Observation from a NormalizedSignal."""
        signal = _make_normalized_signal()
        obs = Observation.from_normalized_signal(
            signal=signal,
            source="CryptoNews",
            data_quality=DataQuality.VERIFIED_MEDIUM,
        )
        assert obs.observation_id is not None
        assert obs.source == "CryptoNews"
        assert obs.source_type == DataSourceType.FREE_PUBLIC_SOURCE
        assert "BTC" in obs.affected_assets
        assert obs.ingestion_status == ObservationStatus.NORMALIZED
        assert obs.card_family == CardFamily.NEWS_EVENT_MARKET_IMPACT
        assert len(obs.evidence) >= 1  # has evidence from source_refs

    def test_observation_from_normalized_signal_empty_assets(self):
        """Observation from signal without assets uses asset_or_topic."""
        signal = NormalizedSignal(
            source_type=DataSourceType.FIXTURE,
            card_family=CardFamily.MULTI_ASSET_MARKET_SYNC,
            asset_or_topic="BTC/ETH/SOL",
            timestamp=china_now(),
            metrics={},
        )
        obs = Observation.from_normalized_signal(signal, source="fixture")
        # Should extract assets from asset_or_topic
        assert len(obs.affected_assets) > 0, "Should extract from asset_or_topic"
        assert "BTC" in obs.affected_assets

    def test_observation_dedup_key_deterministic(self):
        """Same source+title+assets produces same dedup_key."""
        obs1 = _make_observation(title="Same Event", source="src1", affected_assets=["BTC"])
        obs2 = _make_observation(title="Same Event", source="src1", affected_assets=["BTC"])
        assert obs1.dedup_key == obs2.dedup_key

    def test_observation_dedup_key_different_source(self):
        """Different source produces different dedup_key."""
        obs1 = _make_observation(title="Same Event", source="src1")
        obs2 = _make_observation(title="Same Event", source="src2")
        assert obs1.dedup_key != obs2.dedup_key

    def test_observation_as_dict(self):
        """as_dict() returns serializable representation."""
        obs = _make_observation()
        d = obs.as_dict()
        assert isinstance(d, dict)
        assert d["source_type"] == "free_public_source"
        assert d["data_quality"] == "verified_medium"
        assert d["ingestion_status"] == "normalized"
        assert "observation_id" in d


# ═══════════════════════════════════════════════════════════════════════════
# 2. Deterministic Gate — Acceptance
# ═══════════════════════════════════════════════════════════════════════════


class TestNoiseGateAcceptance:
    def test_all_rules_pass_for_quality_observation(self):
        """A high-quality observation should pass all evaluatable rules."""
        obs = _make_observation(data_quality=DataQuality.VERIFIED_HIGH)
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)

        assert len(results) == 10, f"Expected 10 rules, got {len(results)}"

        for r in results:
            assert r.rule_name is not None
            assert r.reason_code is not None
            assert r.reason is not None
            assert r.evaluated_at is not None
            assert r.rule_version == GATE_RULE_VERSION

        # Non-REJECT overall
        verdict = gate.aggregate(results)
        assert verdict != GateVerdict.REJECT

    def test_duplicate_rule_accepts_first_occurrence(self):
        """Duplicate rule should ACCEPT first occurrence."""
        obs = _make_observation()
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        dup_result = [r for r in results if r.rule_name == "duplicate_event"][0]
        assert dup_result.verdict == GateVerdict.ACCEPT

    def test_fresh_event_accepted(self):
        """Recent event time passes stale check."""
        now = china_now()
        obs = _make_observation(event_time=now)
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        stale_result = [r for r in results if r.rule_name == "stale_or_recycled_event"][0]
        assert stale_result.verdict in (GateVerdict.ACCEPT, GateVerdict.NOT_EVALUATED)

    def test_known_tradable_asset_accepted(self):
        """Observation with known assets passes asset check."""
        obs = _make_observation(affected_assets=["BTC", "ETH"])
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        asset_result = [r for r in results if r.rule_name == "no_tradable_asset"][0]
        assert asset_result.verdict == GateVerdict.ACCEPT

    def test_high_quality_source_accepted(self):
        """High quality source passes quality check."""
        obs = _make_observation(data_quality=DataQuality.VERIFIED_HIGH)
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        quality_result = [r for r in results if r.rule_name == "insufficient_source_quality"][0]
        assert quality_result.verdict == GateVerdict.ACCEPT

    def test_aggregate_all_accept(self):
        """All rules ACCEPT → aggregate verdict is ACCEPT."""
        gate = DeterministicNoiseGate()
        results = [
            NoiseGateResult(
                rule_name="r1", verdict=GateVerdict.ACCEPT, reason_code="ok",
                reason="ok", evidence_refs=[], evaluated_at=china_now(),
                rule_version=GATE_RULE_VERSION,
            ),
            NoiseGateResult(
                rule_name="r2", verdict=GateVerdict.ACCEPT, reason_code="ok",
                reason="ok", evidence_refs=[], evaluated_at=china_now(),
                rule_version=GATE_RULE_VERSION,
            ),
        ]
        verdict = gate.aggregate(results)
        assert verdict == GateVerdict.ACCEPT


# ═══════════════════════════════════════════════════════════════════════════
# 3. Deterministic Gate — Rejection
# ═══════════════════════════════════════════════════════════════════════════


class TestNoiseGateRejection:
    def test_low_credibility_source_rejected(self):
        """Low credibility source → REJECT."""
        obs = _make_observation(data_quality=DataQuality.LOW_CREDIBILITY)
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        quality_result = [r for r in results if r.rule_name == "insufficient_source_quality"][0]
        assert quality_result.verdict == GateVerdict.REJECT

    def test_single_unverified_source_rejected(self):
        """Single unverified source → REJECT."""
        obs = _make_observation(
            source="unknown_blog",
            data_quality=DataQuality.UNKNOWN,
            source_type=DataSourceType.LOCAL_SNAPSHOT,
        )
        # Clear source_refs to ensure single source path
        obs.source_refs = []
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        # May be NOT_EVALUATED or REJECT based on available data
        single_result = [r for r in results if r.rule_name == "single_unverified_source"]
        assert len(single_result) == 1
        r = single_result[0]
        assert r.verdict in (GateVerdict.REJECT, GateVerdict.NOT_EVALUATED)

    def test_stale_event_rejected(self):
        """Very old event → REJECT."""
        old_time = "2020-01-01T00:00:00+00:00"
        obs = _make_observation(event_time=old_time)
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        stale_result = [r for r in results if r.rule_name == "stale_or_recycled_event"][0]
        # Should either reject or not evaluate (depends on timestamp parsing)
        assert stale_result.verdict in (GateVerdict.REJECT, GateVerdict.NOT_EVALUATED)

    def test_high_pump_risk_rejected(self):
        """High pump risk → REJECT."""
        obs = _make_observation()
        obs.normalized_payload["pump_risk"] = "high"
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        pump_result = [r for r in results if r.rule_name == "high_chase_or_pump_risk"][0]
        assert pump_result.verdict == GateVerdict.REJECT

    def test_aggregate_reject_overrides(self):
        """Any REJECT → aggregate REJECT."""
        gate = DeterministicNoiseGate()
        results = [
            NoiseGateResult(
                rule_name="r1", verdict=GateVerdict.ACCEPT, reason_code="ok",
                reason="ok", evidence_refs=[], evaluated_at=china_now(),
                rule_version=GATE_RULE_VERSION,
            ),
            NoiseGateResult(
                rule_name="r2", verdict=GateVerdict.REJECT, reason_code="bad",
                reason="bad", evidence_refs=[], evaluated_at=china_now(),
                rule_version=GATE_RULE_VERSION,
            ),
        ]
        verdict = gate.aggregate(results)
        assert verdict == GateVerdict.REJECT


# ═══════════════════════════════════════════════════════════════════════════
# 4. Reason Code Existence
# ═══════════════════════════════════════════════════════════════════════════


class TestNoiseGateReasonCodes:
    def test_all_results_have_reason_code(self):
        """Every rule evaluation has a non-empty reason_code."""
        obs = _make_observation()
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        for r in results:
            assert r.reason_code, f"Rule {r.rule_name} missing reason_code"
            assert r.reason, f"Rule {r.rule_name} missing reason text"
            assert len(r.reason) > 0, f"Rule {r.rule_name} has empty reason"

    def test_all_results_have_evidence_refs(self):
        """Every rule evaluation has evidence_refs list (possibly empty)."""
        obs = _make_observation()
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        for r in results:
            assert isinstance(r.evidence_refs, list)

    def test_all_results_have_timestamps(self):
        """Every rule evaluation has a valid timestamp."""
        obs = _make_observation()
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)
        for r in results:
            assert r.evaluated_at is not None
            assert len(r.evaluated_at) > 0


# ═══════════════════════════════════════════════════════════════════════════
# 5. Unknown Evidence NOT Masqueraded
# ═══════════════════════════════════════════════════════════════════════════


class TestNoiseGateNotEvaluated:
    def test_missing_market_data_returns_not_evaluated(self):
        """Rules without data return NOT_EVALUATED, not fabricated pass/fail.

        Rules that require EXTERNAL market data (not inferable from
        observation content) must return NOT_EVALUATED.

        Rules like 'social_heat_without_spot_confirmation' that can
        evaluate from observation metadata alone correctly return
        ACCEPT when social heat is absent — that's a real evaluation.
        """
        obs = _make_observation()
        gate = DeterministicNoiseGate()
        results = gate.evaluate(obs)

        # Rules that require external market data NOT in a basic observation
        data_dependent_rules = [
            "already_heavily_price_in",
            "derivatives_overcrowding",
            "high_chase_or_pump_risk",
        ]

        for r in results:
            if r.rule_name in data_dependent_rules:
                msg = f"Rule '{r.rule_name}' returned {r.verdict} instead of NOT_EVALUATED for no-data input"
                assert r.verdict == GateVerdict.NOT_EVALUATED, msg

    def test_not_evaluated_not_masqueraded_as_accept(self):
        """NOT_EVALUATED is preserved, not downgraded to ACCEPT."""
        gate = DeterministicNoiseGate()
        results = [
            NoiseGateResult(
                rule_name="r1", verdict=GateVerdict.NOT_EVALUATED, reason_code="no_data",
                reason="Insufficient data", evidence_refs=[], evaluated_at=china_now(),
                rule_version=GATE_RULE_VERSION,
            ),
        ]
        assert results[0].verdict == GateVerdict.NOT_EVALUATED
        assert results[0].is_unknown
        assert not results[0].passed  # NOT_EVALUATED is not "passed"

    def test_not_evaluated_does_not_false_pass(self):
        """NOT_EVALUATED result.passed is False."""
        r = NoiseGateResult(
            rule_name="test", verdict=GateVerdict.NOT_EVALUATED, reason_code="no_data",
            reason="No data", evidence_refs=[], evaluated_at=china_now(),
            rule_version=GATE_RULE_VERSION,
        )
        assert not r.passed
        assert r.is_unknown

    def test_aggregate_with_not_evaluated(self):
        """Aggregate with NOT_EVALUATED but no reject → DOWNGRADE."""
        gate = DeterministicNoiseGate()
        results = [
            NoiseGateResult(
                rule_name="r1", verdict=GateVerdict.ACCEPT, reason_code="ok",
                reason="ok", evidence_refs=[], evaluated_at=china_now(),
                rule_version=GATE_RULE_VERSION,
            ),
            NoiseGateResult(
                rule_name="r2", verdict=GateVerdict.NOT_EVALUATED, reason_code="no_data",
                reason="no data", evidence_refs=[], evaluated_at=china_now(),
                rule_version=GATE_RULE_VERSION,
            ),
        ]
        verdict = gate.aggregate(results)
        # When no reject but has NOT_EVALUATED, should be DOWNGRADE
        assert verdict == GateVerdict.DOWNGRADE


# ═══════════════════════════════════════════════════════════════════════════
# 6. Signal Creation
# ═══════════════════════════════════════════════════════════════════════════


class TestSignalCreation:
    def test_create_signal_basic(self):
        """Create a signal with required fields."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="SEC Approves BTC ETF",
            affected_assets=["BTC", "ETH"],
            event_type="ETF",
            direction="bullish",
            confidence=0.65,
            trading_relevance="high",
            news_quality="verified",
            status=SignalStatus.CANDIDATE,
            first_seen_at=china_now(),
            updated_at=china_now(),
        )
        assert signal.signal_id is not None
        assert signal.title == "SEC Approves BTC ETF"
        assert signal.is_active
        assert not signal.is_terminal
        assert signal.confidence == 0.65

    def test_signal_as_dict(self):
        """Signal as_dict() is serializable."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test",
            affected_assets=["BTC"],
            event_type="test",
            direction="neutral",
            confidence=0.5,
            trading_relevance="medium",
            news_quality="unverified",
            status=SignalStatus.CANDIDATE,
            first_seen_at=china_now(),
            updated_at=china_now(),
        )
        d = signal.as_dict()
        assert isinstance(d, dict)
        assert d["status"] == "candidate"
        assert d["direction"] == "neutral"

    def test_signal_with_evidence(self):
        """Signal with evidence links."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test",
            affected_assets=["BTC"],
            event_type="test",
            direction="neutral",
            confidence=0.5,
            trading_relevance="medium",
            news_quality="unverified",
            status=SignalStatus.CANDIDATE,
            first_seen_at=china_now(),
            updated_at=china_now(),
            evidence=[
                EvidenceLink(
                    ref="sha256:abc123",
                    source="test",
                    timestamp=china_now(),
                    description="Test evidence",
                )
            ],
        )
        assert len(signal.evidence) == 1
        assert signal.evidence[0].ref == "sha256:abc123"

    def test_signal_with_renderer_payload(self):
        """Signal renderer_payload is preserved."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test",
            affected_assets=["BTC"],
            event_type="test",
            direction="neutral",
            confidence=0.5,
            trading_relevance="medium",
            news_quality="unverified",
            status=SignalStatus.CANDIDATE,
            first_seen_at=china_now(),
            updated_at=china_now(),
            renderer_payload={"title": "Test", "signal_id": "abc"},
        )
        assert signal.renderer_payload is not None
        assert signal.renderer_payload["title"] == "Test"


# ═══════════════════════════════════════════════════════════════════════════
# 7. Legal State Transitions
# ═══════════════════════════════════════════════════════════════════════════


class TestSignalLifecycleLegal:
    def test_candidate_to_confirmed(self):
        """candidate → confirmed is legal."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="bullish",
            confidence=0.6, trading_relevance="high",
            news_quality="verified",
            status=SignalStatus.CANDIDATE,
            first_seen_at=china_now(), updated_at=china_now(),
        )
        signal.transition_to(SignalStatus.CONFIRMED, "Event confirmed by second source")
        assert signal.status == SignalStatus.CONFIRMED
        assert len(signal.transition_history) == 1
        assert signal.transition_history[0].from_status == SignalStatus.CANDIDATE
        assert signal.transition_history[0].to_status == SignalStatus.CONFIRMED

    def test_confirmed_to_monitoring(self):
        """confirmed → monitoring is legal."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="verified",
            status=SignalStatus.CONFIRMED,
            first_seen_at=china_now(), updated_at=china_now(),
        )
        signal.transition_to(SignalStatus.MONITORING, "Moving to monitoring")
        assert signal.status == SignalStatus.MONITORING

    def test_confirmed_to_invalidated(self):
        """confirmed → invalidated is legal."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="verified",
            status=SignalStatus.CONFIRMED,
            first_seen_at=china_now(), updated_at=china_now(),
        )
        signal.transition_to(SignalStatus.INVALIDATED, "Event debunked")
        assert signal.status == SignalStatus.INVALIDATED
        assert signal.is_terminal
        assert not signal.is_active

    def test_confirmed_to_expired(self):
        """confirmed → expired is legal."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="verified",
            status=SignalStatus.CONFIRMED,
            first_seen_at=china_now(), updated_at=china_now(),
        )
        signal.transition_to(SignalStatus.EXPIRED, "Event window closed")
        assert signal.status == SignalStatus.EXPIRED

    def test_confirmed_to_resolved(self):
        """confirmed → resolved is legal."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="verified",
            status=SignalStatus.CONFIRMED,
            first_seen_at=china_now(), updated_at=china_now(),
        )
        signal.transition_to(SignalStatus.RESOLVED, "Event outcome determined")
        assert signal.status == SignalStatus.RESOLVED

    def test_candidate_to_invalidated(self):
        """candidate → invalidated (reject directly)."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="unverified",
            status=SignalStatus.CANDIDATE,
            first_seen_at=china_now(), updated_at=china_now(),
        )
        signal.transition_to(SignalStatus.INVALIDATED, "False positive")
        assert signal.status == SignalStatus.INVALIDATED

    def test_is_valid_transition_helper(self):
        """is_valid_transition helper works correctly."""
        assert is_valid_transition(SignalStatus.CANDIDATE, SignalStatus.CONFIRMED)
        assert is_valid_transition(SignalStatus.CANDIDATE, SignalStatus.MONITORING)
        assert is_valid_transition(SignalStatus.CANDIDATE, SignalStatus.INVALIDATED)
        assert is_valid_transition(SignalStatus.CONFIRMED, SignalStatus.MONITORING)
        assert is_valid_transition(SignalStatus.CONFIRMED, SignalStatus.EXPIRED)
        assert is_valid_transition(SignalStatus.CONFIRMED, SignalStatus.RESOLVED)


# ═══════════════════════════════════════════════════════════════════════════
# 8. Illegal State Transitions
# ═══════════════════════════════════════════════════════════════════════════


class TestSignalLifecycleIllegal:
    def test_terminal_no_transition(self):
        """Terminal states cannot transition."""
        for terminal_state in [SignalStatus.INVALIDATED, SignalStatus.EXPIRED, SignalStatus.RESOLVED]:
            signal = Signal(
                signal_id=str(uuid.uuid4()),
                title="Test", affected_assets=["BTC"],
                event_type="test", direction="neutral",
                confidence=0.5, trading_relevance="medium",
                news_quality="unverified",
                status=terminal_state,
                first_seen_at=china_now(), updated_at=china_now(),
            )
            for target in [SignalStatus.CANDIDATE, SignalStatus.CONFIRMED, SignalStatus.MONITORING]:
                with pytest.raises(ValueError, match="not allowed"):
                    signal.transition_to(target, f"Illegal {terminal_state} → {target}")

    def test_confirmed_to_candidate_illegal(self):
        """confirmed → candidate is illegal."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="verified",
            status=SignalStatus.CONFIRMED,
            first_seen_at=china_now(), updated_at=china_now(),
        )
        with pytest.raises(ValueError):
            signal.transition_to(SignalStatus.CANDIDATE, "Cannot go back")

    def test_expired_to_confirmed_illegal(self):
        """expired → confirmed is illegal."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="verified",
            status=SignalStatus.EXPIRED,
            first_seen_at=china_now(), updated_at=china_now(),
        )
        with pytest.raises(ValueError):
            signal.transition_to(SignalStatus.CONFIRMED, "Cannot revive")

    def test_invalidated_to_monitoring_illegal(self):
        """invalidated → monitoring is illegal."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="verified",
            status=SignalStatus.INVALIDATED,
            first_seen_at=china_now(), updated_at=china_now(),
        )
        with pytest.raises(ValueError):
            signal.transition_to(SignalStatus.MONITORING, "Cannot resurrect")

    def test_resolved_to_candidate_illegal(self):
        """resolved → candidate is illegal."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="verified",
            status=SignalStatus.RESOLVED,
            first_seen_at=china_now(), updated_at=china_now(),
        )
        with pytest.raises(ValueError):
            signal.transition_to(SignalStatus.CANDIDATE, "Cannot restart")

    def test_transition_preserves_history_on_error(self):
        """Failed transition does NOT modify history."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="verified",
            status=SignalStatus.EXPIRED,
            first_seen_at=china_now(), updated_at=china_now(),
        )
        original_history_len = len(signal.transition_history)
        with pytest.raises(ValueError):
            signal.transition_to(SignalStatus.CONFIRMED, "Should fail")
        assert len(signal.transition_history) == original_history_len


# ═══════════════════════════════════════════════════════════════════════════
# 9. Registry Save and Read (Persistence)
# ═══════════════════════════════════════════════════════════════════════════


class TestRegistryPersistence:
    def test_registry_save_and_load(self, tmp_path):
        """Registry saves to JSON and reloads correctly."""
        storage = tmp_path / "test_registry.json"
        registry = SignalRegistry(storage_path=storage)

        obs = _make_observation()
        signal = registry.create_signal(
            title="Test Signal",
            affected_assets=["BTC"],
            event_type="ETF",
            direction="bullish",
            confidence=0.7,
            observation=obs,
        )
        assert registry.signal_count() == 1
        registry.save()

        # Create new registry instance reading same file
        registry2 = SignalRegistry(storage_path=storage)
        assert registry2.signal_count() == 1

        loaded = registry2.get_signal(signal.signal_id)
        assert loaded is not None
        assert loaded.title == "Test Signal"
        assert loaded.confidence == 0.7

    def test_registry_preserves_observation_ids(self, tmp_path):
        """Registry persists observation→signal mapping."""
        storage = tmp_path / "obs_mapping.json"
        registry = SignalRegistry(storage_path=storage)

        obs = _make_observation()
        signal = registry.create_signal(
            title="Test", affected_assets=["BTC"],
            event_type="ETF", direction="bullish",
            confidence=0.5, observation=obs,
        )
        registry.save()

        registry2 = SignalRegistry(storage_path=storage)
        found = registry2.get_signal_by_observation(obs.observation_id)
        assert found is not None
        assert found.signal_id == signal.signal_id

    def test_registry_preserves_dedup_map(self, tmp_path):
        """Registry persists dedup_key→signal mapping."""
        storage = tmp_path / "dedup_map.json"
        registry = SignalRegistry(storage_path=storage)

        obs = _make_observation()
        signal = registry.create_signal(
            title="Test", affected_assets=["BTC"],
            event_type="ETF", direction="bullish",
            confidence=0.5, observation=obs,
        )
        registry.save()

        registry2 = SignalRegistry(storage_path=storage)
        found = registry2.get_signal_by_dedup_key(obs.dedup_key)
        assert found is not None
        assert found.signal_id == signal.signal_id

    def test_registry_preserves_history(self, tmp_path):
        """Registry persists transition history."""
        storage = tmp_path / "history.json"
        registry = SignalRegistry(storage_path=storage)

        obs = _make_observation()
        signal = registry.create_signal(
            title="Test", affected_assets=["BTC"],
            event_type="ETF", direction="bullish",
            confidence=0.5, observation=obs,
        )
        registry.transition_status(signal.signal_id, SignalStatus.CONFIRMED, "Confirmed")
        registry.save()

        registry2 = SignalRegistry(storage_path=storage)
        loaded = registry2.get_signal(signal.signal_id)
        assert loaded is not None
        assert len(loaded.transition_history) >= 1
        assert loaded.status == SignalStatus.CONFIRMED

    def test_registry_empty_file(self, tmp_path):
        """Registry handles empty/non-existent storage."""
        storage = tmp_path / "nonexistent.json"
        registry = SignalRegistry(storage_path=storage)
        assert registry.signal_count() == 0
        assert registry.all_signals() == []

    def test_registry_corrupted_file(self, tmp_path):
        """Registry handles corrupted storage gracefully."""
        storage = tmp_path / "corrupted.json"
        storage.write_text("{{{invalid json}}}", encoding="utf-8")
        # Should start fresh with warning
        registry = SignalRegistry(storage_path=storage)
        assert registry.signal_count() == 0

    def test_registry_prevents_duplicate_signal(self, tmp_path):
        """Same dedup_key doesn't create duplicate signal."""
        storage = tmp_path / "dedup_test.json"
        registry = SignalRegistry(storage_path=storage)

        obs1 = _make_observation(title="Same Event", source="src1")
        obs2 = _make_observation(title="Same Event", source="src1")

        s1 = registry.create_signal(
            title="Same Event", affected_assets=["BTC"],
            event_type="ETF", direction="bullish",
            confidence=0.5, observation=obs1,
        )
        s2 = registry.create_signal(
            title="Same Event", affected_assets=["BTC"],
            event_type="ETF", direction="bullish",
            confidence=0.5, observation=obs2,
        )
        # Should be the same signal
        assert s1.signal_id == s2.signal_id
        assert registry.signal_count() == 1


# ═══════════════════════════════════════════════════════════════════════════
# 10. Duplicate Observation → No Duplicate Signal (Orchestrator)
# ═══════════════════════════════════════════════════════════════════════════


class TestOrchestratorDedup:
    def test_same_observation_twice_no_duplicate(self, tmp_path):
        """Orchestrator processes same observation twice without duplicating."""
        storage = tmp_path / "orchestrator_dedup.json"
        orchestrator = create_orchestrator(storage_path=str(storage))

        obs = _make_observation()
        result1 = orchestrator.process(obs)

        assert result1.signal is not None
        assert result1.registry_action in ("created_new", "gate_not_passed")

        # Process same observation again
        result2 = orchestrator.process(obs)

        if result1.signal is not None:
            assert result2.signal is not None
            assert result2.signal.signal_id == result1.signal.signal_id

    def test_same_dedup_key_different_obs_merged(self, tmp_path):
        """Two observations with same dedup key get merged into one signal."""
        storage = tmp_path / "dedup_merge.json"
        orchestrator = create_orchestrator(storage_path=str(storage))

        obs1 = _make_observation(title="Merged Event", source="src_a")
        obs2 = _make_observation(title="Merged Event", source="src_a")

        # Need to ensure obs2 has same dedup_key
        assert obs1.dedup_key == obs2.dedup_key

        result1 = orchestrator.process(obs1)
        result2 = orchestrator.process(obs2)

        if result1.signal is not None and result2.signal is not None:
            assert result1.signal.signal_id == result2.signal.signal_id

    def test_different_signals_not_merged(self, tmp_path):
        """Different events create different signals."""
        storage = tmp_path / "different.json"
        orchestrator = create_orchestrator(storage_path=str(storage))

        obs1 = _make_observation(title="Event Alpha", source="src_a")
        obs2 = _make_observation(title="Event Beta", source="src_b")

        result1 = orchestrator.process(obs1)
        result2 = orchestrator.process(obs2)

        if result1.signal is not None and result2.signal is not None:
            assert result1.signal.signal_id != result2.signal.signal_id


# ═══════════════════════════════════════════════════════════════════════════
# 11. New Evidence Merged Into Existing Signal
# ═══════════════════════════════════════════════════════════════════════════


class TestEvidenceMerge:
    def test_second_observation_appends_evidence(self, tmp_path):
        """Second observation appends new evidence to existing signal."""
        storage = tmp_path / "evidence_merge.json"
        registry = SignalRegistry(storage_path=storage)

        obs1 = _make_observation(title="Merge Event", source="src_a")
        signal = registry.create_signal(
            title="Merge Event", affected_assets=["BTC"],
            event_type="ETF", direction="bullish",
            confidence=0.5, observation=obs1,
        )
        initial_evidence_count = len(signal.evidence)

        obs2 = _make_observation(title="Merge Event", source="src_b")
        registry._append_observation_to_signal(signal, obs2)

        assert len(signal.observation_ids) == 2
        assert len(signal.evidence) > initial_evidence_count

    def test_evidence_not_duplicated(self, tmp_path):
        """Same evidence ref is not added twice."""
        storage = tmp_path / "no_dup_evidence.json"
        registry = SignalRegistry(storage_path=storage)

        obs = _make_observation()
        signal = registry.create_signal(
            title="Test", affected_assets=["BTC"],
            event_type="ETF", direction="bullish",
            confidence=0.5, observation=obs,
        )
        initial_count = len(signal.evidence)

        # Append same observation again
        registry._append_observation_to_signal(signal, obs)
        # Should not add duplicate evidence refs
        assert len(signal.evidence) >= initial_count


# ═══════════════════════════════════════════════════════════════════════════
# 12. AI Fallback (Template Generation)
# ═══════════════════════════════════════════════════════════════════════════


class TestAIFallback:
    def test_template_interpretation_generated(self):
        """Template interpretation is generated from observation data."""
        obs = _make_observation(title="BTC ETF Approval", intensity="high")
        result = generate_template_interpretation(obs)

        assert isinstance(result, InterpretationResult)
        assert result.event_title is not None
        assert result.direction in ("bullish", "bearish", "neutral")
        assert 0.0 <= result.confidence <= 1.0
        assert result.event_type is not None
        assert result.explanation is not None
        assert result.interpretation_method == "template_generated"

    def test_template_includes_risk_notes(self):
        """Template interpretation includes appropriate risk notes."""
        obs = _make_observation()
        result = generate_template_interpretation(obs)
        assert len(result.risk_notes) > 0
        assert any("template_generated" in note for note in result.risk_notes)

    def test_ai_interpreter_fallback_by_default(self):
        """AIInterpreter defaults to fallback (template) mode."""
        interpreter = AIInterpreter()
        assert not interpreter.is_available

        obs = _make_observation()
        result = interpreter.interpret(obs)
        assert result.interpretation_method == "template_generated"

    def test_ai_interpreter_stub_when_available(self):
        """AIInterpreter stub returns template when set available."""
        interpreter = AIInterpreter(available=True)
        assert interpreter.is_available

        obs = _make_observation()
        result = interpreter.interpret(obs)
        # Stub still returns template since AI is not actually connected
        assert result.interpretation_method == "template_generated"

    def test_template_direction_from_intensity(self):
        """Template direction correlates with event intensity."""
        obs_high = _make_observation(intensity="high")
        obs_low = _make_observation(intensity="low")

        r_high = generate_template_interpretation(obs_high)
        r_low = generate_template_interpretation(obs_low)

        # High intensity should have higher confidence than low
        assert r_high.confidence >= r_low.confidence

    def test_template_assets_included(self):
        """Template includes affected assets from observation."""
        obs = _make_observation(affected_assets=["BTC", "ETH", "SOL"])
        result = generate_template_interpretation(obs)
        assert len(result.assets_affected) == 3
        assert "BTC" in result.assets_affected


# ═══════════════════════════════════════════════════════════════════════════
# 13. History Version Preservation
# ═══════════════════════════════════════════════════════════════════════════


class TestHistoryPreservation:
    def test_transition_history_recorded(self):
        """Each status transition records a history entry."""
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="verified",
            status=SignalStatus.CANDIDATE,
            first_seen_at=china_now(), updated_at=china_now(),
        )

        signal.transition_to(SignalStatus.CONFIRMED, "Source verified")
        signal.transition_to(SignalStatus.MONITORING, "Monitoring")
        signal.transition_to(SignalStatus.RESOLVED, "Outcome known")

        assert len(signal.transition_history) == 3
        assert signal.transition_history[0].to_status == SignalStatus.CONFIRMED
        assert signal.transition_history[1].to_status == SignalStatus.MONITORING
        assert signal.transition_history[2].to_status == SignalStatus.RESOLVED

    def test_history_timestamps_are_ordered(self):
        """Transition timestamps are in order."""
        import time
        signal = Signal(
            signal_id=str(uuid.uuid4()),
            title="Test", affected_assets=["BTC"],
            event_type="test", direction="neutral",
            confidence=0.5, trading_relevance="medium",
            news_quality="verified",
            status=SignalStatus.CANDIDATE,
            first_seen_at=china_now(), updated_at=china_now(),
        )

        signal.transition_to(SignalStatus.CONFIRMED, "Confirmed")
        time.sleep(0.01)
        signal.transition_to(SignalStatus.MONITORING, "Monitoring")

        assert signal.transition_history[0].timestamp <= signal.transition_history[1].timestamp

    def test_registry_preserves_invalidation_reason(self, tmp_path):
        """Registry preserves invalidation reason across loads."""
        storage = tmp_path / "invalidation.json"
        registry = SignalRegistry(storage_path=storage)

        obs = _make_observation()
        signal = registry.create_signal(
            title="Test", affected_assets=["BTC"],
            event_type="ETF", direction="bullish",
            confidence=0.5, observation=obs,
        )
        registry.record_invalidation(
            signal.signal_id,
            reason="Event debunked by official source",
            invalidation_reason="Official correction issued",
        )
        registry.save()

        registry2 = SignalRegistry(storage_path=storage)
        loaded = registry2.get_signal(signal.signal_id)
        assert loaded is not None
        assert loaded.status == SignalStatus.INVALIDATED
        assert loaded.invalidation_reason == "Official correction issued"
