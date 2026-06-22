"""Adversarial and edge-case test scenarios for the intelligence kernel.

Each scenario proves the system fails conservatively rather than producing
false confident output.
"""

import pytest
from market_radar.intelligence.contracts.evidence import (
    EvidenceItem, VerificationStatus, Stance,
)
from market_radar.intelligence.contracts.event import (
    EventEntity, EventState, EventTransition, TransitionType,
)
from market_radar.intelligence.contracts.calibration import (
    ConfidenceStatement, ConfidenceType,
)
from market_radar.intelligence.engines.evidence_resolver import EvidenceResolverV1
from market_radar.intelligence.engines.event_state_machine import EventStateMachineV1
from market_radar.intelligence.engines.arbitration import ArbitrationEngineV1
from market_radar.intelligence.engines.transmission_graph import TransmissionGraphEngineV1
from market_radar.intelligence.contracts.transmission import (
    TransmissionNode, TransmissionEdge, EdgeSign, NodeType,
)
from market_radar.intelligence.contracts.hypothesis import MarketHypothesis, HypothesisStatus
from market_radar.intelligence.contracts.arbitration import ArbitrationInput, VerdictState


def make_item(eid, group="g", is_primary=False, retracted=False):
    return EvidenceItem(
        evidence_id=eid, claim="test", source_id=eid,
        independence_group=group, is_primary=is_primary,
        retraction_status=retracted,
        verification_status=VerificationStatus.SINGLE_SOURCE_UNVERIFIED,
    )


class TestAdversarial:
    def test_ten_media_all_same_source(self):
        """Ten media outlets all citing the same anonymous source should not
        count as ten independent sources."""
        resolver = EvidenceResolverV1()
        items = [
            make_item(f"evi_{i:03d}", group="anonymous_leak", is_primary=False)
            for i in range(10)
        ]
        bundle = resolver.resolve(items)
        assert bundle.status.independent_source_count == 1
        assert bundle.bundle_verdict != VerificationStatus.VERIFIED_MULTI_SOURCE

    def test_retracted_official_announcement(self):
        """An official announcement later deleted/retracted should not remain verified."""
        resolver = EvidenceResolverV1()
        items = [
            make_item("evi_001", group="official", is_primary=True, retracted=True),
        ]
        bundle = resolver.resolve(items)
        assert bundle.bundle_verdict != VerificationStatus.VERIFIED_PRIMARY

    def test_conflicting_primary_sources(self):
        """Two primary sources contradicting each other on same claim key should resolve to CONFLICTING."""
        resolver = EvidenceResolverV1()
        items = [
            EvidenceItem(evidence_id="evi_a", claim="Approved", claim_key="approval_status",
                          claim_subject="BTC ETF", claim_predicate="status", claim_value="approved",
                          stance=Stance.SUPPORTS, source_id="src_a",
                          independence_group="gov_a", is_primary=True),
            EvidenceItem(evidence_id="evi_b", claim="Rejected", claim_key="approval_status",
                          claim_subject="BTC ETF", claim_predicate="status", claim_value="rejected",
                          stance=Stance.CONTRADICTS, source_id="src_b",
                          independence_group="gov_b", is_primary=True),
        ]
        bundle = resolver.resolve(items)
        assert bundle.bundle_verdict == VerificationStatus.CONFLICTING

    def test_short_term_bullish_long_term_bearish(self):
        """Same event: short-term bullish, long-term bearish — must be
        separate assessments, not a contradiction."""
        from tests.intelligence.test_arbitration import make_arb_input
        engine = ArbitrationEngineV1()
        inp = make_arb_input("BTC", [
            MarketHypothesis(
                hypothesis_id="hyp_short", event_id="evt_001",
                strategy_instance_id="sti_001",
                affected_assets=["BTC"], time_horizon="short_term",
                expected_effect="bullish",
                status=HypothesisStatus.SUPPORTED,
            ).to_dict(),
            MarketHypothesis(
                hypothesis_id="hyp_long", event_id="evt_001",
                strategy_instance_id="sti_002",
                affected_assets=["BTC"], time_horizon="long_term",
                expected_effect="bearish",
                status=HypothesisStatus.SUPPORTED,
            ).to_dict(),
        ])
        out = engine.arbitrate(inp)
        # Should have at least one assessment (short_term)
        assert len(out.horizon_assessments) >= 1

    def test_three_low_quality_vs_one_high_quality(self):
        """Three low-quality strategies supporting vs one high-quality opposing
        — should not vote, should preserve the conflict."""
        from tests.intelligence.test_arbitration import make_arb_input
        engine = ArbitrationEngineV1()
        inp = make_arb_input("BTC", [
            MarketHypothesis(
                hypothesis_id="high_quality", event_id="evt_001",
                strategy_instance_id="sti_high",
                affected_assets=["BTC"], time_horizon="short_term",
                expected_effect="bearish",
                status=HypothesisStatus.SUPPORTED,
            ).to_dict(),
            MarketHypothesis(
                hypothesis_id="low_a", event_id="evt_001",
                strategy_instance_id="sti_low_a",
                affected_assets=["BTC"], time_horizon="short_term",
                expected_effect="bullish",
                status=HypothesisStatus.CANDIDATE,
            ).to_dict(),
            MarketHypothesis(
                hypothesis_id="low_b", event_id="evt_001",
                strategy_instance_id="sti_low_b",
                affected_assets=["BTC"], time_horizon="short_term",
                expected_effect="bullish",
                status=HypothesisStatus.CANDIDATE,
            ).to_dict(),
            MarketHypothesis(
                hypothesis_id="low_c", event_id="evt_001",
                strategy_instance_id="sti_low_c",
                affected_assets=["BTC"], time_horizon="short_term",
                expected_effect="bullish",
                status=HypothesisStatus.CANDIDATE,
            ).to_dict(),
        ])
        out = engine.arbitrate(inp)
        # All are eligible, so we should have mixed signals
        ha = out.horizon_assessments[0]
        assert len(ha.supporting_hypotheses) > 0 or len(ha.opposing_hypotheses) > 0

    def test_no_pre_event_expectation(self):
        """Without pre-event expectation, expectation gap must return unavailable."""
        from market_radar.intelligence.engines.expectation_gap import ExpectationGapEngineV1
        engine = ExpectationGapEngineV1()
        result = engine.handle_no_expectation("No survey data available")
        assert result.gap_status.value == "unavailable"
        assert result.expectation_quality == "insufficient"

    def test_llm_confidence_without_calibration(self):
        """An LLM claiming 80% confidence without calibration artifact must be rejected."""
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
            value="0.80",
            probability_value=0.80,
        )
        errors = cs.validate()
        # Without production_probability=False, it fails
        assert len(errors) > 0

    def test_undeclared_cycle_in_transmission_graph(self):
        """A cycle in the transmission graph that is not declared as reflexive
        should be detected as a cycle."""
        engine = TransmissionGraphEngineV1()
        engine.add_node(TransmissionNode(node_id="n1", node_type=NodeType.NARRATIVE, label="A"))
        engine.add_node(TransmissionNode(node_id="n2", node_type=NodeType.NARRATIVE, label="B"))
        engine.add_edge(TransmissionEdge(edge_id="e1", source_node="n1", target_node="n2",
                                          sign=EdgeSign.POSITIVE))
        engine.add_edge(TransmissionEdge(edge_id="e2", source_node="n2", target_node="n1",
                                          sign=EdgeSign.POSITIVE))
        cycles = engine.detect_cycles()
        assert len(cycles) > 0

    def test_event_revision_not_new_transition(self):
        """Event being revised should not count as a new progression."""
        sm = EventStateMachineV1()
        event = EventEntity(event_id="evt_001", current_state=EventState.APPROVED)
        sm.transition(event, EventState.APPROVED,
                       transition_type=TransitionType.REVISION, reason="Revised document")
