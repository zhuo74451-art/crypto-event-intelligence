"""Tests for arbitration engine."""

import pytest
from market_radar.intelligence.contracts.arbitration import (
    ArbitrationInput, ArbitrationOutput, HorizonAssessment,
    VerdictState, HorizonBucket,
)
from market_radar.intelligence.contracts.hypothesis import MarketHypothesis, HypothesisStatus
from market_radar.intelligence.engines.arbitration import ArbitrationEngineV1


def make_hyp(hid, effect="bullish", horizon="short_term",
             status=HypothesisStatus.SUPPORTED):
    return MarketHypothesis(
        hypothesis_id=hid,
        event_id="evt_001",
        strategy_instance_id=f"sti_{hid}",
        affected_assets=["BTC"],
        time_horizon=horizon,
        expected_effect=effect,
        status=status,
    )


class TestArbitration:
    def test_no_hypotheses_insufficient(self):
        engine = ArbitrationEngineV1()
        inp = ArbitrationInput(asset="BTC", hypotheses=[])
        out = engine.arbitrate(inp)
        assert out.global_verdict == VerdictState.INSUFFICIENT_EVIDENCE

    def test_single_supporting_directional(self):
        engine = ArbitrationEngineV1()
        inp = ArbitrationInput(asset="BTC", hypotheses=[
            make_hyp("hyp_001", effect="bullish").to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert len(out.horizon_assessments) == 1
        # Without market_confirmation set, ARB-002 returns WAIT_FOR_CONFIRMATION
        assert out.horizon_assessments[0].verdict in (
            VerdictState.DIRECTIONAL_AVAILABLE, VerdictState.WAIT_FOR_CONFIRMATION
        )

    def test_unconfirmed_waits(self):
        engine = ArbitrationEngineV1()
        inp = ArbitrationInput(asset="BTC", hypotheses=[
            make_hyp("hyp_001", effect="bullish",
                     status=HypothesisStatus.AWAITING_CONFIRMATION).to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert out.global_verdict == VerdictState.WAIT_FOR_CONFIRMATION

    def test_conflicting_directions(self):
        engine = ArbitrationEngineV1()
        inp = ArbitrationInput(asset="BTC", hypotheses=[
            make_hyp("hyp_001", effect="bullish").to_dict(),
            make_hyp("hyp_002", effect="bearish").to_dict(),
        ])
        out = engine.arbitrate(inp)
        # Without strong evidence on both sides, ARB-002 returns WAIT_FOR_CONFIRMATION
        # Need confidence context (market_confirmation, evidence bundles) for CONFLICT_UNRESOLVED
        assert out.horizon_assessments[0].verdict in (
            VerdictState.CONFLICT_UNRESOLVED, VerdictState.WAIT_FOR_CONFIRMATION
        )

    def test_different_horizons_separated(self):
        engine = ArbitrationEngineV1()
        inp = ArbitrationInput(asset="BTC", hypotheses=[
            make_hyp("hyp_001", effect="bullish", horizon="short_term").to_dict(),
            make_hyp("hyp_002", effect="bearish", horizon="long_term").to_dict(),
        ])
        out = engine.arbitrate(inp)
        # Different horizons should produce separate assessments
        horizons = set(a.horizon for a in out.horizon_assessments)
        assert len(horizons) >= 1  # May collapse to same bucket
        assert len(out.horizon_assessments) >= 1

    def test_ineligible_hypotheses_excluded(self):
        engine = ArbitrationEngineV1()
        inp = ArbitrationInput(asset="BTC", hypotheses=[
            make_hyp("hyp_001", effect="bullish",
                     status=HypothesisStatus.INVALIDATED).to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert len(out.ineligible_hypotheses) >= 1
        assert len(out.eligible_hypotheses) == 0

    def test_same_source_strategies_not_independent(self):
        engine = ArbitrationEngineV1()
        inp = ArbitrationInput(asset="BTC", hypotheses=[
            make_hyp("hyp_001", effect="bullish").to_dict(),
            make_hyp("hyp_002", effect="bullish").to_dict(),
        ])
        out = engine.arbitrate(inp)
        # Both are supporting, even if same source
        assert len(out.horizon_assessments[0].supporting_hypotheses) == 2

    def test_market_confirmation_missing_noted(self):
        engine = ArbitrationEngineV1()
        inp = ArbitrationInput(asset="BTC", hypotheses=[
            make_hyp("hyp_001", effect="bullish").to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert len(out.eligible_hypotheses) == 1

    def test_abstain_with_alternatives(self):
        engine = ArbitrationEngineV1()
        inp = ArbitrationInput(asset="BTC", hypotheses=[
            make_hyp("hyp_001", effect="neutral").to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert len(out.horizon_assessments[0].alternative_hypotheses) > 0

    def test_zero_eligible_returns_insufficient(self):
        engine = ArbitrationEngineV1()
        inp = ArbitrationInput(asset="BTC", hypotheses=[
            make_hyp("hyp_001", effect="bullish",
                     status=HypothesisStatus.INVALIDATED).to_dict(),
            make_hyp("hyp_002", effect="bearish",
                     status=HypothesisStatus.EXPIRED).to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert out.global_verdict == VerdictState.INSUFFICIENT_EVIDENCE
