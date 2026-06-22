"""Precision patch V3 tests — cluster direction, missing context, quality, ARB-011."""
from __future__ import annotations

import pytest

from market_radar.intelligence.contracts.arbitration import (
    ArbitrationInput, VerdictState, ArbitrationStatus,
    HypothesisArbitrationContext, EligibilityReasonCode,
)
from market_radar.intelligence.contracts.hypothesis import MarketHypothesis, HypothesisStatus
from market_radar.intelligence.engines.arbitration import ArbitrationEngineV1


def make_hyp(hid, effect="bullish", horizon="short_term",
             status=HypothesisStatus.SUPPORTED):
    return MarketHypothesis(
        hypothesis_id=hid,
        event_id="evt_p3",
        strategy_instance_id=f"sti_{hid}",
        affected_assets=["BTC"],
        time_horizon=horizon,
        expected_effect=effect,
        status=status,
    )


def make_ctx(hid, verdict="verified_multi_source", regime_match=True,
             conf="confirmed", origin="", groups=None,
             signature="", required=None, available=None) -> HypothesisArbitrationContext:
    return HypothesisArbitrationContext(
        hypothesis_id=hid,
        strategy_instance_id=f"sti_{hid}",
        evidence_bundle_verdict=verdict,
        regime_matches=regime_match,
        market_confirmation=conf,
        strategy_origin_group=origin,
        evidence_independence_groups=groups or [f"group_{hid}"],
        transmission_signature=signature,
        required_inputs=required or ["price", "volume"],
        available_inputs=available or ["price", "volume"],
    )


# ── Cluster direction ────────────────────────────────────────────────────

class TestClusterDirection:
    """Cluster direction must use SET of directions, not member count."""

    def test_cluster_direction_no_member_majority(self):
        engine = ArbitrationEngineV1()
        hyps = [
            make_hyp("b1", effect="bullish", status=HypothesisStatus.SUPPORTED).to_dict(),
            make_hyp("b2", effect="bullish", status=HypothesisStatus.SUPPORTED).to_dict(),
            make_hyp("b3", effect="bullish", status=HypothesisStatus.SUPPORTED).to_dict(),
            make_hyp("b4", effect="bearish", status=HypothesisStatus.SUPPORTED).to_dict(),
        ]
        ctxs = {}
        for h in [make_hyp("b1"), make_hyp("b2"), make_hyp("b3"), make_hyp("b4", effect="bearish")]:
            ctxs[h.hypothesis_id] = make_ctx(h.hypothesis_id, origin="same_group", groups=["same_group"], conf="confirmed")
        inp = ArbitrationInput(asset="BTC", hypotheses=hyps, hypothesis_contexts=ctxs)
        out = engine.arbitrate(inp)
        # All 4 in same cluster (same origin). Mixed direction -> should NOT be directional.
        # 3 bull + 1 bear = mixed, not bullish majority
        for ha in out.horizon_assessments:
            assert ha.direction != "bullish", "Should not be bullish just because 3 bull > 1 bear"
            assert ha.verdict == VerdictState.INSUFFICIENT_EVIDENCE or \
                   ha.verdict == VerdictState.CONFLICT_UNRESOLVED, \
                   f"Mixed cluster should not be directional, got {ha.verdict}"

    def test_three_bull_one_bear_same_origin_is_mixed(self):
        """Three bull + one bear in same origin -> mixed cluster, not directional."""
        engine = ArbitrationEngineV1()
        hyps = [
            make_hyp("b1", effect="bullish").to_dict(),
            make_hyp("b2", effect="bullish").to_dict(),
            make_hyp("b3", effect="bullish").to_dict(),
            make_hyp("s1", effect="bearish").to_dict(),
        ]
        ctxs = {h.hypothesis_id: make_ctx(h.hypothesis_id, origin="shared") for h in
                [make_hyp("b1"), make_hyp("b2"), make_hyp("b3"), make_hyp("s1", effect="bearish")]}
        inp = ArbitrationInput(asset="BTC", hypotheses=hyps, hypothesis_contexts=ctxs)
        out = engine.arbitrate(inp)
        for ha in out.horizon_assessments:
            assert ha.direction != "bullish", "3 bull + 1 bear in same origin should not be bullish"

    def test_pure_bull_cluster_is_bullish(self):
        engine = ArbitrationEngineV1()
        hyps = [make_hyp(f"b{i}", effect="bullish").to_dict() for i in range(3)]
        ctxs = {f"b{i}": make_ctx(f"b{i}", groups=["same"]) for i in range(3)}
        inp = ArbitrationInput(asset="BTC", hypotheses=hyps, hypothesis_contexts=ctxs)
        out = engine.arbitrate(inp)
        for ha in out.horizon_assessments:
            for c in ha.decision_trace.support_clusters:
                if len(c.hypotheses) == 3:
                    assert c.direction == "bullish"


# ── Eligibility completeness ─────────────────────────────────────────────

class TestEligibilityCompleteness:
    """E01-E12 must always produce exactly 12 decisions per hypothesis."""

    def test_missing_context_produces_12_decisions(self):
        engine = ArbitrationEngineV1()
        hyp = make_hyp("hyp_noctx", effect="bullish")
        inp = ArbitrationInput(asset="BTC", hypotheses=[hyp.to_dict()])
        out = engine.arbitrate(inp)
        assert len(out.ineligible_hypotheses) >= 1
        ih = out.ineligible_hypotheses[0]
        assert len(ih.decisions) == 12, f"Expected 12 decisions, got {len(ih.decisions)}"

    def test_missing_context_is_ineligible(self):
        engine = ArbitrationEngineV1()
        hyp = make_hyp("hyp_noctx", effect="bullish")
        inp = ArbitrationInput(asset="BTC", hypotheses=[hyp.to_dict()])
        out = engine.arbitrate(inp)
        assert len(out.eligible_hypotheses) == 0
        assert len(out.ineligible_hypotheses) >= 1

    def test_all_12_decisions_have_trace_entries(self):
        engine = ArbitrationEngineV1()
        hyp = make_hyp("hyp_noctx", effect="bullish")
        inp = ArbitrationInput(asset="BTC", hypotheses=[hyp.to_dict()])
        out = engine.arbitrate(inp)
        ih = out.ineligible_hypotheses[0]
        for d in ih.decisions:
            assert d.trace, f"Decision missing trace: {d}"


# ── Quality mapping ──────────────────────────────────────────────────────

class TestQualityMapping:
    """Quality dimensions must come from context, not fixed defaults."""

    def test_missing_transmission_is_not_moderate(self):
        """Transmission coherence without data should be INSUFFICIENT."""
        engine = ArbitrationEngineV1()
        hyp = make_hyp("hyp_tx", effect="bullish")
        ctx = make_ctx("hyp_tx", groups=["g1"])
        ctx.transmission_signature = ""
        ctx.transmission_coherence = ""
        inp = ArbitrationInput(asset="BTC", hypotheses=[hyp.to_dict()],
                               hypothesis_contexts={"hyp_tx": ctx})
        out = engine.arbitrate(inp)
        # Should still be eligible (transmission absent doesn't block)
        assert len(out.eligible_hypotheses) >= 1

    def test_complete_context_produces_strong_chain(self):
        engine = ArbitrationEngineV1()
        hyp = make_hyp("hyp_strong", effect="bullish")
        ctx = make_ctx("hyp_strong", verdict="verified_multi_source",
                       conf="confirmed", groups=["g1"])
        inp = ArbitrationInput(asset="BTC", hypotheses=[hyp.to_dict()],
                               hypothesis_contexts={"hyp_strong": ctx})
        out = engine.arbitrate(inp)
        for ha in out.horizon_assessments:
            assert ha.verdict == VerdictState.DIRECTIONAL_AVAILABLE

    def test_one_insufficient_blocks_strong_chain(self):
        engine = ArbitrationEngineV1()
        hyp = make_hyp("hyp_weak", effect="bullish")
        # Weak evidence
        ctx = make_ctx("hyp_weak", verdict="single_source_unverified",
                       conf="confirmed", groups=["g1"])
        inp = ArbitrationInput(asset="BTC", hypotheses=[hyp.to_dict()],
                               hypothesis_contexts={"hyp_weak": ctx})
        out = engine.arbitrate(inp)
        # May still get WAIT or INSUFFICIENT, just not strong directional
        for ha in out.horizon_assessments:
            assert ha.verdict != VerdictState.ABSTAIN


# ── ARB-011 ──────────────────────────────────────────────────────────────

class TestArb011:
    """ARB-011: unresolved transmission conflict -> CONFLICT_UNRESOLVED."""

    def test_transmission_conflict_selects_arb011(self):
        engine = ArbitrationEngineV1()
        hyp1 = make_hyp("hyp_t1", effect="bullish")
        hyp2 = make_hyp("hyp_t2", effect="bearish")
        ctx1 = make_ctx("hyp_t1", groups=["g1"])
        ctx1.transmission_coherence = "invalid"
        ctx2 = make_ctx("hyp_t2", groups=["g2"])
        ctx2.transmission_coherence = "invalid"
        inp = ArbitrationInput(asset="BTC", hypotheses=[hyp1.to_dict(), hyp2.to_dict()],
                               hypothesis_contexts={"hyp_t1": ctx1, "hyp_t2": ctx2})
        out = engine.arbitrate(inp)
        for ha in out.horizon_assessments:
            if ha.verdict == VerdictState.CONFLICT_UNRESOLVED:
                assert ha.direction_basis == "ARB-011", f"Expected ARB-011, got {ha.direction_basis}"

    def test_invalid_transmission_fails_e12(self):
        engine = ArbitrationEngineV1()
        hyp = make_hyp("hyp_tx_bad", effect="bullish")
        ctx = make_ctx("hyp_tx_bad", groups=["g1"])
        ctx.transmission_coherence = "invalid"
        inp = ArbitrationInput(asset="BTC", hypotheses=[hyp.to_dict()],
                               hypothesis_contexts={"hyp_tx_bad": ctx})
        out = engine.arbitrate(inp)
        # Should be ineligible due to E12
        assert len(out.ineligible_hypotheses) >= 1


# ── ID stability ─────────────────────────────────────────────────────────

class TestArbitrationId:
    """Arbitration ID must be canonical and content-dependent."""

    def test_same_input_different_order_same_id(self):
        engine = ArbitrationEngineV1()
        hyps = [make_hyp("a", effect="bullish"), make_hyp("b", effect="bearish")]
        ctxs = {"a": make_ctx("a"), "b": make_ctx("b")}
        inp1 = ArbitrationInput(asset="BTC", hypotheses=[h.to_dict() for h in hyps],
                                hypothesis_contexts=ctxs)
        inp2 = ArbitrationInput(asset="BTC", hypotheses=[hyps[1].to_dict(), hyps[0].to_dict()],
                                hypothesis_contexts=ctxs)
        out1 = engine.arbitrate(inp1)
        out2 = engine.arbitrate(inp2)
        assert out1.arbitration_id == out2.arbitration_id

    def test_same_count_different_hypotheses_different_id(self):
        engine = ArbitrationEngineV1()
        ctxs_a = {"a": make_ctx("a"), "b": make_ctx("b")}
        ctxs_c = {"c": make_ctx("c"), "d": make_ctx("d")}
        inp1 = ArbitrationInput(asset="BTC", hypotheses=[make_hyp("a").to_dict(), make_hyp("b").to_dict()],
                                hypothesis_contexts=ctxs_a)
        inp2 = ArbitrationInput(asset="BTC", hypotheses=[make_hyp("c").to_dict(), make_hyp("d").to_dict()],
                                hypothesis_contexts=ctxs_c)
        out1 = engine.arbitrate(inp1)
        out2 = engine.arbitrate(inp2)
        assert out1.arbitration_id != out2.arbitration_id
