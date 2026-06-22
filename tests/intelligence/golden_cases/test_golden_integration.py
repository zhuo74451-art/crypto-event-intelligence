"""Golden Integration Cases G1-G8 for Intelligence Kernel V1.

Each golden case exercises real Kernel contracts and engines end-to-end
with STRICT assertions (no lenient pass/fail alternatives).
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
    EligibilityReasonCode, HypothesisArbitrationContext,
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
from market_radar.intelligence.engines.evidence_resolver import (
    EvidenceResolverV1, EvidenceResolutionPolicy,
)
from market_radar.intelligence.engines.event_state_machine import (
    EventStateMachineV1,
)
from market_radar.intelligence.engines.arbitration import (
    ArbitrationEngineV1,
)


def make_hypothesis(hid: str, effect: str = "bullish",
                    horizon: str = "short_term",
                    status: HypothesisStatus = HypothesisStatus.SUPPORTED,
                    **kwargs) -> MarketHypothesis:
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


def make_context(hid: str, verdict: str = "verified_multi_source",
                 regime_match: bool = True,
                 confirmation: str = "confirmed",
                 origin: str = "",
                 evidence_groups: list[str] | None = None,
                 transmission: str = "",
                 **kwargs) -> HypothesisArbitrationContext:
    return HypothesisArbitrationContext(
        hypothesis_id=hid,
        strategy_instance_id=f"sti_{hid}",
        evidence_bundle_verdict=verdict,
        regime_matches=regime_match,
        regime_quality="strong",
        current_regime="normal",
        market_confirmation=confirmation,
        strategy_origin_group=origin,
        evidence_independence_groups=evidence_groups or ["group_default"],
        transmission_signature=transmission,
        transmission_coherence="strong",
        required_inputs=["price", "volume"],
        available_inputs=["price", "volume"],
        **kwargs,
    )


# ══════════════════════════════════════════════════════════════════════════
# G1: Official Primary Confirmed — Full Chain -> DIRECTIONAL_AVAILABLE
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG1OfficialPrimaryDirectional:
    """G1: Full chain -> directional_available, bullish, ARB-003"""

    def test_full_chain_directional(self):
        engine = ArbitrationEngineV1()
        hyp = make_hypothesis("hyp_g1", effect="bullish", status=HypothesisStatus.SUPPORTED)
        ctx = make_context("hyp_g1", verdict="verified_multi_source", regime_match=True,
                           confirmation="confirmed")
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[hyp.to_dict()],
            hypothesis_contexts={"hyp_g1": ctx},
        )
        out = engine.arbitrate(inp)
        assert len(out.eligible_hypotheses) >= 1
        for ha in out.horizon_assessments:
            assert ha.verdict == VerdictState.DIRECTIONAL_AVAILABLE, f"Expected DIRECTIONAL_AVAILABLE, got {ha.verdict}"
            assert ha.direction == "bullish", f"Expected bullish, got {ha.direction}"
            assert ha.direction_basis == "ARB-003", f"Expected ARB-003, got {ha.direction_basis}"
            assert ha.decision_trace.rule_ids_evaluated


# ══════════════════════════════════════════════════════════════════════════
# G2: Same-Origin False Consensus -> 1 cluster
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG2SameOriginFalseConsensus:
    """10 same-origin hypotheses -> 1 cluster in arbitration."""

    def test_same_origin_collapses_in_arbitration(self):
        engine = ArbitrationEngineV1()
        hyps = [
            make_hypothesis(f"hyp_g2_{i}", effect="bullish",
                            status=HypothesisStatus.SUPPORTED)
            for i in range(10)
        ]
        ctxs = {}
        for h in hyps:
            ctxs[h.hypothesis_id] = make_context(
                h.hypothesis_id, verdict="single_source_unverified",
                origin="same_group", confirmation="confirmed",
            )
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[h.to_dict() for h in hyps],
            hypothesis_contexts=ctxs,
        )
        out = engine.arbitrate(inp)
        for ha in out.horizon_assessments:
            total_clusters = len(ha.decision_trace.support_clusters)
            assert total_clusters == 1, f"Expected 1 cluster, got {total_clusters}"
            cl = ha.decision_trace.support_clusters[0]
            assert len(cl.hypotheses) == 10, f"Expected 10 hypotheses in cluster"


# ══════════════════════════════════════════════════════════════════════════
# G3: Three Weak Bullish vs One Strong Bearish -> Bearish, ARB-004
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG3StrongVsWeakNoVote:
    """3 weak bull + 1 strong bear -> bearish, ARB-004 (not bullish majority)"""

    def test_strong_bear_overrides_weak_bull_consensus(self):
        engine = ArbitrationEngineV1()
        bull_hyps = [
            make_hypothesis(f"hyp_bull_{i}", effect="bullish",
                            status=HypothesisStatus.CANDIDATE)
            for i in range(3)
        ]
        bear_hyp = make_hypothesis("hyp_bear_strong", effect="bearish",
                                   status=HypothesisStatus.SUPPORTED)
        ctxs = {}
        for h in bull_hyps:
            ctxs[h.hypothesis_id] = make_context(
                h.hypothesis_id, verdict="single_source_unverified",
                origin="bull_group", confirmation="awaiting",
                evidence_groups=["bull_evidence"],
            )
        ctxs[bear_hyp.hypothesis_id] = make_context(
            bear_hyp.hypothesis_id, verdict="verified_multi_source",
            origin="bear_independent", confirmation="confirmed",
            regime_match=True,
            evidence_groups=["bear_evidence"],
        )
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[h.to_dict() for h in bull_hyps] + [bear_hyp.to_dict()],
            hypothesis_contexts=ctxs,
        )
        out = engine.arbitrate(inp)
        for ha in out.horizon_assessments:
            assert ha.verdict == VerdictState.DIRECTIONAL_AVAILABLE, f"Expected DIRECTIONAL_AVAILABLE, got {ha.verdict}"
            assert ha.direction == "bearish", f"Expected bearish, got {ha.direction}"
            assert ha.direction_basis == "ARB-004", f"Expected ARB-004, got {ha.direction_basis}"


# ══════════════════════════════════════════════════════════════════════════
# G4: Both Sides Strong -> CONFLICT_UNRESOLVED
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG4StrongTwoSidedConflict:
    """Independent strong Bullish + strong Bearish -> CONFLICT_UNRESOLVED, ARB-005"""

    def test_strong_two_sided_conflict(self):
        engine = ArbitrationEngineV1()
        bull = make_hypothesis("hyp_bull", effect="bullish", status=HypothesisStatus.SUPPORTED)
        bear = make_hypothesis("hyp_bear", effect="bearish", status=HypothesisStatus.SUPPORTED)
        ctxs = {
            "hyp_bull": make_context("hyp_bull", verdict="verified_multi_source",
                                      origin="bull_origin", confirmation="confirmed",
                                      evidence_groups=["bull_ev_group"]),
            "hyp_bear": make_context("hyp_bear", verdict="verified_multi_source",
                                      origin="bear_origin", confirmation="confirmed",
                                      evidence_groups=["bear_ev_group"]),
        }
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[bull.to_dict(), bear.to_dict()],
            hypothesis_contexts=ctxs,
        )
        out = engine.arbitrate(inp)
        for ha in out.horizon_assessments:
            assert ha.verdict == VerdictState.CONFLICT_UNRESOLVED, f"Expected CONFLICT_UNRESOLVED, got {ha.verdict}"
            assert ha.direction_basis == "ARB-005", f"Expected ARB-005, got {ha.direction_basis}"


# ══════════════════════════════════════════════════════════════════════════
# G5: Missing Market Confirmation -> WAIT_FOR_CONFIRMATION
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG5WaitForConfirmation:
    """Evidence+Regime OK but no market confirmation -> WAIT, ARB-002"""

    def test_wait_for_confirmation(self):
        engine = ArbitrationEngineV1()
        hyp = make_hypothesis("hyp_g5", effect="bullish",
                              status=HypothesisStatus.AWAITING_CONFIRMATION)
        ctx = make_context("hyp_g5", verdict="verified_multi_source",
                           regime_match=True, confirmation="awaiting")
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[hyp.to_dict()],
            hypothesis_contexts={"hyp_g5": ctx},
        )
        out = engine.arbitrate(inp)
        assert out.global_verdict == VerdictState.WAIT_FOR_CONFIRMATION
        for ha in out.horizon_assessments:
            assert ha.verdict == VerdictState.WAIT_FOR_CONFIRMATION, f"Expected WAIT, got {ha.verdict}"
            assert ha.direction_basis == "ARB-002", f"Expected ARB-002, got {ha.direction_basis}"


# ══════════════════════════════════════════════════════════════════════════
# G6: Invalid Regime -> Ineligible (E08)
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG6InvalidRegime:
    """Strategy valid but current regime is invalid -> ineligible, E08"""

    def test_invalid_regime_makes_ineligible(self):
        engine = ArbitrationEngineV1()
        hyp = make_hypothesis("hyp_g6", effect="bullish", status=HypothesisStatus.SUPPORTED)
        ctx = make_context("hyp_g6", verdict="verified_multi_source",
                           regime_match=False, confirmation="confirmed")
        ctx.invalid_regimes = ["tightening"]
        ctx.current_regime = "tightening"
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[hyp.to_dict()],
            hypothesis_contexts={"hyp_g6": ctx},
        )
        out = engine.arbitrate(inp)
        assert len(out.eligible_hypotheses) == 0, f"Expected 0 eligible, got {len(out.eligible_hypotheses)}"
        assert len(out.ineligible_hypotheses) >= 1
        ih = out.ineligible_hypotheses[0]
        codes = ih.all_reason_codes()
        assert any("E08" in str(c) for c in codes), f"Expected E08 in codes, got {codes}"


# ══════════════════════════════════════════════════════════════════════════
# G7: Multi-Horizon Separation
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG7MultiHorizon:
    """Short-term bullish + medium-term bearish -> separate assessments, mixed status"""

    def test_multi_horizon_not_flattened(self):
        engine = ArbitrationEngineV1()
        short_bull = make_hypothesis("hyp_short", effect="bullish", horizon="short_term",
                                     status=HypothesisStatus.SUPPORTED)
        med_bear = make_hypothesis("hyp_medium", effect="bearish", horizon="medium_term",
                                    status=HypothesisStatus.SUPPORTED)
        ctxs = {
            "hyp_short": make_context("hyp_short", verdict="verified_multi_source",
                                       regime_match=True, confirmation="confirmed",
                                       origin="bull_orig"),
            "hyp_medium": make_context("hyp_medium", verdict="verified_multi_source",
                                        regime_match=True, confirmation="confirmed",
                                        origin="bear_orig"),
        }
        inp = ArbitrationInput(
            asset="BTC",
            hypotheses=[short_bull.to_dict(), med_bear.to_dict()],
            hypothesis_contexts=ctxs,
        )
        out = engine.arbitrate(inp)
        horizons = {a.horizon for a in out.horizon_assessments}
        assert "short_term" in horizons, f"Expected short_term in {horizons}"
        assert "medium_term" in horizons, f"Expected medium_term in {horizons}"
        for ha in out.horizon_assessments:
            if ha.horizon == "short_term":
                assert ha.direction == "bullish"
            elif ha.horizon == "medium_term":
                assert ha.direction == "bearish"
        assert out.arbitration_status == ArbitrationStatus.MULTI_HORIZON_MIXED, (
            f"Expected MULTI_HORIZON_MIXED, got {out.arbitration_status}"
        )


# ══════════════════════════════════════════════════════════════════════════
# G8: State Correction Replay
# ══════════════════════════════════════════════════════════════════════════

class TestGoldenG8RevisionReplay:
    """T1 state A, T2 state correction to B. As-of T1 returns A, current = B."""

    def test_revision_replay(self):
        esm = EventStateMachineV1()
        event = EventEntity(event_id="evt_g8", current_state=EventState.RUMOR)

        # T1: Rumor -> Proposed (progression)
        r1 = esm.transition(event, EventState.PROPOSED,
                             transition_time="2024-01-01T00:00:00Z",
                             first_seen_at="2024-01-01T00:00:00Z")
        ev1 = r1.updated_event
        assert ev1.current_state == EventState.PROPOSED  # State A

        # T2: State correction: Proposed -> Announced (legitimate state change)
        r2 = esm.transition(ev1, EventState.ANNOUNCED,
                             transition_type=TransitionType.PROGRESSION,
                             reason="New information confirms announcement",
                             transition_time="2024-01-02T00:00:00Z",
                             first_seen_at="2024-01-02T00:00:00Z")
        ev2 = r2.updated_event
        assert ev2.current_state == EventState.ANNOUNCED  # State B

        # As-known-then before T2: should be PROPOSED (State A)
        state_before_t2 = esm.reconstruct_as_of(
            ev2.transitions, "2024-01-01T12:00:00Z"
        )
        assert state_before_t2 == EventState.PROPOSED, (
            f"As-of before T2 should be PROPOSED, got {state_before_t2}"
        )

        # Current best after T2: should be ANNOUNCED (State B)
        assert ev2.current_state == EventState.ANNOUNCED

        # Original input event NOT mutated
        assert event.current_state == EventState.RUMOR, "Input event not mutated"
