"""Tests for strategy lifecycle engine."""

import pytest
from market_radar.intelligence.contracts.strategy import (
    StrategyInstance, StrategyInstanceState,
)
from market_radar.intelligence.engines.strategy_lifecycle import StrategyLifecycleEngineV1
from market_radar.intelligence.errors.codes import IntelligenceError


def make_inst(sid="sti_001", state=StrategyInstanceState.INACTIVE):
    return StrategyInstance(instance_id=sid, strategy_id="str_001",
                            asset="BTC", time_horizon="short_term", state=state)


class TestLifecycleTransitions:
    def test_inactive_to_watching(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst()
        tx = engine.evaluate(inst, context_met=True)
        assert inst.state == StrategyInstanceState.WATCHING
        assert tx.to_state == StrategyInstanceState.WATCHING

    def test_watching_to_triggered(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst(state=StrategyInstanceState.WATCHING)
        tx = engine.evaluate(inst, trigger_met=True)
        assert inst.state == StrategyInstanceState.TRIGGERED

    def test_triggered_to_awaiting(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst(state=StrategyInstanceState.TRIGGERED)
        tx = engine.evaluate(inst)
        assert inst.state == StrategyInstanceState.AWAITING_CONFIRMATION

    def test_triggered_to_confirmed(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst(state=StrategyInstanceState.TRIGGERED)
        tx = engine.evaluate(inst, confirmation_met=True)
        assert inst.state == StrategyInstanceState.CONFIRMED

    def test_awaiting_confirmation_to_confirmed(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst(state=StrategyInstanceState.AWAITING_CONFIRMATION)
        tx = engine.evaluate(inst, confirmation_met=True)
        assert inst.state == StrategyInstanceState.CONFIRMED

    def test_awaiting_confirmation_to_weakened(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst(state=StrategyInstanceState.AWAITING_CONFIRMATION)
        tx = engine.evaluate(inst, weakening_evidence=True)
        assert inst.state == StrategyInstanceState.WEAKENED

    def test_confirmed_to_weakened(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst(state=StrategyInstanceState.CONFIRMED)
        tx = engine.evaluate(inst, weakening_evidence=True)
        assert inst.state == StrategyInstanceState.WEAKENED

    def test_any_to_invalidated(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst(state=StrategyInstanceState.WATCHING)
        tx = engine.evaluate(inst, invalidation_triggered=True)
        assert inst.state == StrategyInstanceState.INVALIDATED

    def test_any_to_expired(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst(state=StrategyInstanceState.WATCHING)
        tx = engine.evaluate(inst, expired=True)
        assert inst.state == StrategyInstanceState.EXPIRED

    def test_invalidation_priority_over_expiry(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst(state=StrategyInstanceState.WATCHING)
        tx = engine.evaluate(inst, invalidation_triggered=True, expired=True)
        assert inst.state == StrategyInstanceState.INVALIDATED

    def test_invalidated_terminal_no_further(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst(state=StrategyInstanceState.INVALIDATED)
        tx = engine.evaluate(inst, context_met=True)
        assert tx is None

    def test_expired_terminal_no_further(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst(state=StrategyInstanceState.EXPIRED)
        tx = engine.evaluate(inst, context_met=True)
        assert tx is None

    def test_illegal_transition_raises(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst()
        with pytest.raises(IntelligenceError):
            engine.transition(inst, StrategyInstanceState.CONFIRMED)

    def test_transition_reason_recorded(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst()
        engine.evaluate(inst, context_met=True)
        assert len(inst.transitions) == 1
        assert "Context conditions" in inst.transitions[0].reason

    def test_allowed_method_check(self):
        engine = StrategyLifecycleEngineV1()
        inst = make_inst()
        assert engine.is_allowed(inst, StrategyInstanceState.WATCHING)
        assert not engine.is_allowed(inst, StrategyInstanceState.CONFIRMED)
