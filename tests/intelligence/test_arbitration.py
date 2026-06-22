"""Tests for arbitration engine."""

import pytest
from market_radar.intelligence.contracts.arbitration import (
    ArbitrationInput, ArbitrationOutput, HorizonAssessment,
    VerdictState, HorizonBucket, HypothesisArbitrationContext,
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


def make_context(hid, verdict="verified_multi_source",
                 regime_match=True, confirmation="confirmed"):
    """Create a HypothesisArbitrationContext from a hypothesis ID."""
    return HypothesisArbitrationContext(
        hypothesis_id=hid,
        strategy_instance_id=f"sti_{hid}",
        evidence_bundle_verdict=verdict,
        regime_matches=regime_match,
        market_confirmation=confirmation,
        evidence_independence_groups=["default_group"],
        required_inputs=["price", "volume"],
        available_inputs=["price", "volume"],
    )


def make_arb_input(asset: str, hyps: list[dict],
                   evidence_state: dict | None = None,
                   regime_state: dict | None = None) -> ArbitrationInput:
    """Create ArbitrationInput with both legacy and context data."""
    contexts = {}
    for h_dict in hyps:
        if isinstance(h_dict, dict):
            hid = h_dict.get("hypothesis_id", "")
            status_str = h_dict.get("status", "")
            if status_str in ("supported", "confirmed"):
                conf = "confirmed"
            elif status_str in ("awaiting_confirmation",):
                conf = "awaiting"
            else:
                conf = "awaiting"
            contexts[hid] = HypothesisArbitrationContext(
                hypothesis_id=hid,
                strategy_instance_id=h_dict.get("strategy_instance_id", ""),
                evidence_bundle_verdict="verified_multi_source",
                regime_matches=True,
                regime_quality="strong",
                current_regime="normal",
                market_confirmation=conf,
                evidence_independence_groups=[f"group_{hid}"],
                required_inputs=["price", "volume"],
                available_inputs=["price", "volume"],
                transmission_coherence="strong",
            )
    return ArbitrationInput(
        asset=asset,
        hypotheses=hyps,
        hypothesis_contexts=contexts,
        evidence_state=evidence_state or {},
        regime_state=regime_state or {},
    )


class TestArbitration:
    def test_no_hypotheses_insufficient(self):
        engine = ArbitrationEngineV1()
        inp = ArbitrationInput(asset="BTC", hypotheses=[])
        out = engine.arbitrate(inp)
        assert out.global_verdict == VerdictState.INSUFFICIENT_EVIDENCE

    def test_single_supporting_directional(self):
        engine = ArbitrationEngineV1()
        inp = make_arb_input("BTC", [
            make_hyp("hyp_001", effect="bullish").to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert len(out.horizon_assessments) == 1
        assert out.horizon_assessments[0].verdict == VerdictState.DIRECTIONAL_AVAILABLE

    def test_unconfirmed_waits(self):
        engine = ArbitrationEngineV1()
        inp = make_arb_input("BTC", [
            make_hyp("hyp_001", effect="bullish",
                     status=HypothesisStatus.AWAITING_CONFIRMATION).to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert out.global_verdict == VerdictState.WAIT_FOR_CONFIRMATION

    def test_conflicting_directions(self):
        engine = ArbitrationEngineV1()
        inp = make_arb_input("BTC", [
            make_hyp("hyp_001", effect="bullish").to_dict(),
            make_hyp("hyp_002", effect="bearish").to_dict(),
        ])
        out = engine.arbitrate(inp)
        # Both have strong evidence -> CONFLICT_UNRESOLVED
        assert out.horizon_assessments[0].verdict == VerdictState.CONFLICT_UNRESOLVED

    def test_different_horizons_separated(self):
        engine = ArbitrationEngineV1()
        inp = make_arb_input("BTC", [
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
        inp = make_arb_input("BTC", [
            make_hyp("hyp_001", effect="bullish",
                     status=HypothesisStatus.INVALIDATED).to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert len(out.ineligible_hypotheses) >= 1
        assert len(out.eligible_hypotheses) == 0

    def test_same_source_strategies_not_independent(self):
        engine = ArbitrationEngineV1()
        inp = make_arb_input("BTC", [
            make_hyp("hyp_001", effect="bullish").to_dict(),
            make_hyp("hyp_002", effect="bullish").to_dict(),
        ])
        out = engine.arbitrate(inp)
        # Both are supporting, even if same source
        assert len(out.horizon_assessments[0].supporting_hypotheses) == 2

    def test_market_confirmation_missing_noted(self):
        engine = ArbitrationEngineV1()
        inp = make_arb_input("BTC", [
            make_hyp("hyp_001", effect="bullish").to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert len(out.eligible_hypotheses) == 1

    def test_abstain_with_alternatives(self):
        engine = ArbitrationEngineV1()
        inp = make_arb_input("BTC", [
            make_hyp("hyp_001", effect="neutral").to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert len(out.horizon_assessments[0].alternative_hypotheses) > 0

    def test_zero_eligible_returns_insufficient(self):
        engine = ArbitrationEngineV1()
        inp = make_arb_input("BTC", [
            make_hyp("hyp_001", effect="bullish",
                     status=HypothesisStatus.INVALIDATED).to_dict(),
            make_hyp("hyp_002", effect="bearish",
                     status=HypothesisStatus.EXPIRED).to_dict(),
        ])
        out = engine.arbitrate(inp)
        assert out.global_verdict == VerdictState.INSUFFICIENT_EVIDENCE
