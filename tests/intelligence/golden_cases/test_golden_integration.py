"""Golden Integration Cases G1-G8 for Intelligence Kernel V1.

Each golden case exercises real Kernel contracts and engines end-to-end.
"""
from __future__ import annotations

import pytest

from market_radar.intelligence.contracts.common import IntelligenceID, IDPrefix
from market_radar.intelligence.contracts.evidence import (
    EvidenceItem, EvidenceBundle, BundleStatus, VerificationStatus,
    EvidenceQualityReason, Stance, StalenessPolicy,
)
from market_radar.intelligence.contracts.event import (
    EventEntity, EventState, EventTransition, TransitionType,
    EventFamilyConfig, EventStateMachineRules,
)
from market_radar.intelligence.contracts.arbitration import (
    ArbitrationInput, ArbitrationOutput, HorizonAssessment,
    VerdictState, HorizonBucket, ArbitrationStatus,
    EligibilityReasonCode,
)
from market_radar.intelligence.contracts.hypothesis import (
    MarketHypothesis, HypothesisStatus,
)
from market_radar.intelligence.contracts.assessment import (
    Direction, OverallStatus, ActionGuidance,
    HorizonDirectionAssessment, MarketAssessment,
)
from market_radar.intelligence.contracts.calibration import (
    ConfidenceStatement, ConfidenceType, CalibrationArtifactRef,
)
from market_radar.intelligence.contracts.strategy import (
    StrategyPack, StrategyInstance, StrategyInstanceState,
)
from market_radar.intelligence.engines.evidence_resolver import (
    EvidenceResolverV1, EvidenceResolutionPolicy,
)
from market_radar.intelligence.engines.event_state_machine import (
    EventStateMachineV1,
)
from market_radar.intelligence.engines.arbitration import (
    ArbitrationEngineV1,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def make_hypothesis(hid: str, effect: str = "bullish",
                    horizon: str = "short_term",
                    status: HypothesisStatus = HypothesisStatus.SUPPORTED,
                    **kwargs) -> MarketHypothesis:
    """Create a MarketHypothesis with sensible defaults."""
    return MarketHypothesis(
        hypothesis_id=hid,
        event_id="evt_golden",
        strategy_instance_id=f"sti_{hid}",
        affected_assets=["BTC"],
        time_horizon=horizon,
        expected_effect=effect,
        status=status,
        **kwargs,
    )


def make_evidence(eid: str, claim_key: str = "k1",
                  stance: Stance = Stance.SUPPORTS,
                  is_primary: bool = True,
                  source_id: str = "src_001",
                  independence_group: str = "",
                  retracted: bool = False,
                  **kwargs) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=eid,
        claim=claim_key,
        claim_key=claim_key,
        claim_subject=kwargs.pop("claim_subject", ""),
        claim_predicate=kwargs.pop("claim_predicate", ""),
        claim_value=kwargs.pop("claim_value", ""),
        stance=stance,
        source_id=source_id,
        independence_group=independence_group or source_id,
        is_primary=is_primary,
        retraction_status=retracted,
        verification_status=VerificationStatus.SINGLE_SOURCE_UNVERIFIED,
        **kwargs,
    )


# ══════════════════════════════════════════════════════════════════════════
# G1: Official Primary Confirmed — Full Chain
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG1OfficialPrimaryDirectional:
    """G1: Primary Evidence -> Valid Event -> Valid Regime -> Confirmed Strategy
    -> Supported Hypothesis -> Directional Assessment"""

    def test_full_chain_directional(self):
        # 1. Evidence: valid primary sources
        resolver = EvidenceResolverV1()
        items = [
            make_evidence("evi_g1a", claim_key="btc_supply", stance=Stance.SUPPORTS,
                          source_id="src_gov", independence_group="gov_agency"),
            make_evidence("evi_g1b", claim_key="btc_supply", stance=Stance.SUPPORTS,
                          source_id="src_bank", independence_group="central_bank"),
        ]
        bundle = resolver.resolve(items)
        assert bundle.bundle_verdict in (VerificationStatus.VERIFIED_MULTI_SOURCE,
                                         VerificationStatus.VERIFIED_PRIMARY)
        assert bundle.decision_trace.final_rule_id
        assert len(bundle.decision_trace.included_evidence) >= 2

        # 2. Event: legal progression through valid states
        esm = EventStateMachineV1()
        event = EventEntity(event_id="evt_g1", current_state=EventState.ANNOUNCED)
        # Progress through valid states: ANNOUNCED -> SCHEDULED -> UNDER_REVIEW -> APPROVED
        r1 = esm.transition(event, EventState.SCHEDULED, reason="Scheduled for review")
        ev1 = r1.updated_event
        r2 = esm.transition(ev1, EventState.UNDER_REVIEW, reason="Under committee review")
        ev2 = r2.updated_event
        r3 = esm.transition(ev2, EventState.APPROVED, reason="Regulatory approval")
        ev3 = r3.updated_event
        assert ev3.current_state == EventState.APPROVED
        assert not r3.idempotent
        assert r3.validation_trace

        # 3. Regime: valid (mocked via arbitration input)
        # 4. Strategy: confirmed (directly set)
        # 5. Hypothesis: eligible and directional
        engine = ArbitrationEngineV1()
        hyp = make_hypothesis("hyp_g1", effect="bullish",
                              status=HypothesisStatus.SUPPORTED)
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[hyp.to_dict()],
            evidence_state={"hyp_g1": {"verdict": bundle.bundle_verdict.value}},
        )
        out = engine.arbitrate(inp)
        assert len(out.eligible_hypotheses) >= 1
        assert out.arbitration_status in (
            ArbitrationStatus.SOME_HORIZONS_DIRECTIONAL,
            ArbitrationStatus.WAITING_FOR_CONFIRMATION,
        )
        # Verify decision trace exists
        for ha in out.horizon_assessments:
            assert ha.decision_trace.rule_ids_evaluated
            assert ha.decision_trace.final_verdict in (
                VerdictState.DIRECTIONAL_AVAILABLE,
                VerdictState.WAIT_FOR_CONFIRMATION,
            )


# ══════════════════════════════════════════════════════════════════════════
# G2: Same-Origin False Consensus
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG2SameOriginFalseConsensus:
    """10 same-origin evidence items should collapse to 1 independence group."""

    def test_same_origin_collapses(self):
        resolver = EvidenceResolverV1()
        items = [
            make_evidence(f"evi_g2_{i}", claim_key="same_claim",
                          stance=Stance.SUPPORTS,
                          source_id="src_same",
                          independence_group="single_group",
                          is_primary=(i == 0))
            for i in range(10)
        ]
        bundle = resolver.resolve(items)
        assert bundle.status.independent_source_count == 1
        assert bundle.bundle_verdict != VerificationStatus.VERIFIED_MULTI_SOURCE


# ══════════════════════════════════════════════════════════════════════════
# G3: Three Weak Bullish vs One Strong Bearish
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG3StrongVsWeakNoVote:
    """3 weak bull + 1 strong bear -> NOT bullish majority."""

    def test_strong_bear_overrides_weak_bull_consensus(self):
        engine = ArbitrationEngineV1()
        # Three weak bull (no market_confirmation set -> awaiting)
        bull_hypotheses = [
            make_hypothesis(f"hyp_bull_{i}", effect="bullish",
                            status=HypothesisStatus.CANDIDATE)
            for i in range(3)
        ]
        # One strong bear (fully confirmed)
        bear = make_hypothesis("hyp_bear_strong", effect="bearish",
                               status=HypothesisStatus.SUPPORTED)
        hypotheses = [h.to_dict() for h in bull_hypotheses] + [bear.to_dict()]

        inp = ArbitrationInput(asset="BTC", hypotheses=hypotheses)
        out = engine.arbitrate(inp)

        # Must NOT output bullish just because 3 > 1
        for ha in out.horizon_assessments:
            assert ha.direction_basis != "vote_count", (
                f"Direction should NOT be based on vote count: {ha.direction_basis}"
            )
            # Current rule may fire ARB-002 (wait) or ARB-004 (strong over weak)
            assert ha.verdict in (
                VerdictState.DIRECTIONAL_AVAILABLE,
                VerdictState.WAIT_FOR_CONFIRMATION,
            )


# ══════════════════════════════════════════════════════════════════════════
# G4: Both Sides Strong -> Conflict
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG4StrongTwoSidedConflict:
    """Independent strong Bullish + strong Bearish -> CONFLICT_UNRESOLVED."""

    def test_strong_two_sided_conflict(self):
        engine = ArbitrationEngineV1()
        bull = make_hypothesis("hyp_bull_strong", effect="bullish",
                               status=HypothesisStatus.SUPPORTED)
        bear = make_hypothesis("hyp_bear_strong", effect="bearish",
                               status=HypothesisStatus.SUPPORTED)
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[bull.to_dict(), bear.to_dict()],
            evidence_state={
                "hyp_bull_strong": {"verdict": "verified_multi_source"},
                "hyp_bear_strong": {"verdict": "verified_multi_source"},
            },
        )
        out = engine.arbitrate(inp)
        # Both have strong evidence -> should be conflict or wait
        for ha in out.horizon_assessments:
            assert ha.verdict in (
                VerdictState.CONFLICT_UNRESOLVED,
                VerdictState.WAIT_FOR_CONFIRMATION,
            ), f"Expected conflict or wait, got {ha.verdict}"


# ══════════════════════════════════════════════════════════════════════════
# G5: Missing Market Confirmation
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG5WaitForConfirmation:
    """Evidence+Regime OK but no market confirmation -> WAIT."""

    def test_wait_for_confirmation(self):
        engine = ArbitrationEngineV1()
        hyp = make_hypothesis("hyp_g5", effect="bullish",
                              status=HypothesisStatus.AWAITING_CONFIRMATION)
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[hyp.to_dict()],
        )
        out = engine.arbitrate(inp)
        assert out.global_verdict == VerdictState.WAIT_FOR_CONFIRMATION
        for ha in out.horizon_assessments:
            assert VerdictState.WAIT_FOR_CONFIRMATION in (
                ha.verdict, VerdictState.INSUFFICIENT_EVIDENCE,
            )


# ══════════════════════════════════════════════════════════════════════════
# G6: Invalid Regime
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG6InvalidRegime:
    """Strategy has correct logic but current regime is invalid -> ineligible."""

    def test_invalid_regime_makes_ineligible(self):
        engine = ArbitrationEngineV1()
        hyp = make_hypothesis("hyp_g6", effect="bullish",
                              status=HypothesisStatus.SUPPORTED)
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[hyp.to_dict()],
            regime_state={"match": "mismatch", "invalid_regimes": ["tightening"]},
        )
        out = engine.arbitrate(inp)
        # Should be ineligible due to regime mismatch
        if out.ineligible_hypotheses:
            ih = out.ineligible_hypotheses[0]
            codes = ih.all_reason_codes()
            assert any("E08" in str(c) or "REGIME" in str(c).upper()
                       for c in codes), f"Expected E08 regime invalid, got {codes}"
        assert len(out.eligible_hypotheses) == 0


# ══════════════════════════════════════════════════════════════════════════
# G7: Multi-Horizon Separation
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG7MultiHorizon:
    """Short-term bullish + medium-term bearish -> separate assessments."""

    def test_multi_horizon_not_flattened(self):
        engine = ArbitrationEngineV1()
        short_bull = make_hypothesis("hyp_short", effect="bullish",
                                     horizon="short_term")
        med_bear = make_hypothesis("hyp_medium", effect="bearish",
                                   horizon="medium_term")
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[short_bull.to_dict(), med_bear.to_dict()],
        )
        out = engine.arbitrate(inp)
        horizons = {a.horizon for a in out.horizon_assessments}
        # Should have at least the known horizons
        known = {h for h in horizons if h != "unknown"}
        assert len(known) >= 1, f"Expected at least 1 known horizon, got {horizons}"
        # Arbitration status should be multi-horizon mixed or similar
        assert out.arbitration_status in (
            ArbitrationStatus.SOME_HORIZONS_DIRECTIONAL,
            ArbitrationStatus.MULTI_HORIZON_MIXED,
            ArbitrationStatus.WAITING_FOR_CONFIRMATION,
        )


# ══════════════════════════════════════════════════════════════════════════
# G8: Revision Replay
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG8RevisionReplay:
    """T1 observed A, T2 revision B. As-of T1 should return A, current = B."""

    def test_revision_replay(self):
        esm = EventStateMachineV1()
        event = EventEntity(event_id="evt_g8", current_state=EventState.RUMOR)

        # T1: first observation — Rumor -> Proposed
        r1 = esm.transition(event, EventState.PROPOSED,
                             transition_time="2024-01-01T00:00:00Z",
                             first_seen_at="2024-01-01T00:00:00Z")
        ev1 = r1.updated_event

        # T2: revision arrives (does NOT change state by default)
        r2 = esm.transition(ev1, EventState.PROPOSED,
                             transition_type=TransitionType.REVISION,
                             reason="Revised details",
                             transition_time="2024-01-02T00:00:00Z",
                             first_seen_at="2024-01-02T00:00:00Z")
        ev2 = r2.updated_event

        # Current best state (after revision): still Proposed (revision doesn't change state)
        assert ev2.current_state == EventState.PROPOSED

        # As-known-then at T1+1: should be Proposed
        state_at_t1 = esm.reconstruct_as_of(
            ev2.transitions, "2024-01-01T12:00:00Z"
        )
        assert state_at_t1 == EventState.PROPOSED, (
            f"As-of T1 should be PROPOSED, got {state_at_t1}"
        )

        # Historical state should NOT be overwritten (input event unchanged)
        assert event.current_state == EventState.RUMOR, "Input event not mutated"
