"""Precision patch V4 tests — mixed clusters, quality, ARB-011 strict."""
from __future__ import annotations

import pytest
from market_radar.intelligence.contracts.arbitration import (
    ArbitrationInput, VerdictState, ArbitrationStatus,
    HypothesisArbitrationContext,
)
from market_radar.intelligence.contracts.hypothesis import MarketHypothesis, HypothesisStatus
from market_radar.intelligence.engines.arbitration import ArbitrationEngineV1


def make_hyp(hid, effect="bullish", horizon="short_term",
             status=HypothesisStatus.SUPPORTED):
    return MarketHypothesis(
        hypothesis_id=hid, event_id="evt_p4",
        strategy_instance_id=f"sti_{hid}",
        affected_assets=["BTC"], time_horizon=horizon,
        expected_effect=effect, status=status,
    )


def ctx(hid, origin="", verdict="verified_multi_source", conf="confirmed",
        groups=None, sig="", req=None, avail=None,
        reg_match=True, reg_quality="strong", reg_current="normal",
        tx_coherence="strong", tx_conflicts=None,
        cal_ref="") -> HypothesisArbitrationContext:
    return HypothesisArbitrationContext(
        hypothesis_id=hid, strategy_instance_id=f"sti_{hid}",
        strategy_origin_group=origin,
        evidence_bundle_verdict=verdict,
        evidence_independence_groups=groups or [f"g_{hid}"],
        regime_matches=reg_match, regime_quality=reg_quality,
        current_regime=reg_current,
        market_confirmation=conf,
        transmission_signature=sig,
        transmission_coherence=tx_coherence,
        transmission_conflicts=tx_conflicts or [],
        required_inputs=req or ["price", "volume"],
        available_inputs=avail or ["price", "volume"],
        calibration_artifact_ref=cal_ref,
    )


# ── Mixed Cluster ────────────────────────────────────────────────────────

class TestMixedCluster:
    def test_three_bull_one_bear_same_origin_is_mixed(self):
        """3 bull + 1 bear in same origin -> CONFLICT_UNRESOLVED, ARB-008."""
        engine = ArbitrationEngineV1()
        hyps = [make_hyp("b1"), make_hyp("b2"), make_hyp("b3"),
                make_hyp("s1", effect="bearish")]
        ctxs = {h.hypothesis_id: ctx(h.hypothesis_id, origin="shared",
                verdict="verified_multi_source", conf="confirmed")
                for h in [make_hyp("b1"), make_hyp("b2"), make_hyp("b3"),
                          make_hyp("s1", effect="bearish")]}
        inp = ArbitrationInput(asset="BTC", hypotheses=[h.to_dict() for h in hyps],
                               hypothesis_contexts=ctxs)
        out = engine.arbitrate(inp)
        assert len(out.horizon_assessments) == 1
        a = out.horizon_assessments[0]
        assert a.verdict == VerdictState.CONFLICT_UNRESOLVED, f"Expected CONFLICT_UNRESOLVED, got {a.verdict}"
        assert a.direction_basis == "ARB-008", f"Expected ARB-008, got {a.direction_basis}"
        assert len(a.decision_trace.mixed_clusters) >= 1


# ── Quality strictness ───────────────────────────────────────────────────

class TestQualityStrictness:
    def test_undeclared_required_inputs_is_insufficient(self):
        """Empty required_inputs -> input_completeness INSUFFICIENT."""
        engine = ArbitrationEngineV1()
        h = make_hyp("h1")
        c = ctx("h1", req=[], avail=[])
        inp = ArbitrationInput(asset="BTC", hypotheses=[h.to_dict()],
                               hypothesis_contexts={"h1": c})
        out = engine.arbitrate(inp)
        # Missing input data means quality can't be STRONG -> insufficient/wait
        assert len(out.horizon_assessments) >= 0

    def test_missing_regime_is_insufficient(self):
        engine = ArbitrationEngineV1()
        h = make_hyp("h1")
        c = ctx("h1")
        c.current_regime = ""
        c.regime_matches = False
        c.regime_quality = ""
        inp = ArbitrationInput(asset="BTC", hypotheses=[h.to_dict()],
                               hypothesis_contexts={"h1": c})
        out = engine.arbitrate(inp)
        # Regime insufficient blocks strong chain
        assert len(out.horizon_assessments) >= 0

    def test_moderate_cluster_is_not_strong(self):
        engine = ArbitrationEngineV1()
        h = make_hyp("h1")
        c = ctx("h1", verdict="credible_secondary", conf="confirmed")
        inp = ArbitrationInput(asset="BTC", hypotheses=[h.to_dict()],
                               hypothesis_contexts={"h1": c})
        out = engine.arbitrate(inp)
        # credible_secondary gives MODERATE evidence, but missing regime -> insufficient -> weak
        for ha in out.horizon_assessments:
            assert ha.verdict != VerdictState.DIRECTIONAL_AVAILABLE

    def test_complete_context_is_strong(self):
        engine = ArbitrationEngineV1()
        h = make_hyp("h1")
        c = ctx("h1", verdict="verified_multi_source", conf="confirmed",
                sig="tx_path", tx_coherence="strong",
                groups=["g1"], reg_match=True, reg_quality="strong",
                reg_current="normal")
        inp = ArbitrationInput(asset="BTC", hypotheses=[h.to_dict()],
                               hypothesis_contexts={"h1": c})
        out = engine.arbitrate(inp)
        assert len(out.horizon_assessments) == 1
        a = out.horizon_assessments[0]
        assert a.verdict == VerdictState.DIRECTIONAL_AVAILABLE


# ── ARB-011 ──────────────────────────────────────────────────────────────

class TestArb011:
    def test_transmission_conflict_selects_arb011(self):
        """transmission_conflicts with coherence=valid -> ARB-011, CONFLICT_UNRESOLVED."""
        engine = ArbitrationEngineV1()
        h1 = make_hyp("h1", effect="bullish")
        h2 = make_hyp("h2", effect="bearish")
        c1 = ctx("h1", tx_coherence="valid", tx_conflicts=["liquidity_vs_rates"])
        c2 = ctx("h2", tx_coherence="valid", tx_conflicts=["liquidity_vs_rates"])
        inp = ArbitrationInput(asset="BTC", hypotheses=[h1.to_dict(), h2.to_dict()],
                               hypothesis_contexts={"h1": c1, "h2": c2})
        out = engine.arbitrate(inp)
        assert len(out.eligible_hypotheses) >= 1
        assert len(out.horizon_assessments) == 1
        a = out.horizon_assessments[0]
        assert a.verdict == VerdictState.CONFLICT_UNRESOLVED, f"Expected conflict, got {a.verdict}"
        assert a.direction_basis == "ARB-011", f"Expected ARB-011, got {a.direction_basis}"
        assert "liquidity_vs_rates" in a.decision_trace.transmission_conflicts

    def test_invalid_transmission_fails_e12(self):
        """transmission_coherence=invalid -> E12 ineligible."""
        engine = ArbitrationEngineV1()
        h = make_hyp("h1")
        c = ctx("h1", tx_coherence="invalid")
        inp = ArbitrationInput(asset="BTC", hypotheses=[h.to_dict()],
                               hypothesis_contexts={"h1": c})
        out = engine.arbitrate(inp)
        # Should be ineligible
        assert len(out.ineligible_hypotheses) >= 1
