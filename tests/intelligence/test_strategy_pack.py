"""Tests for strategy pack contracts."""

import pytest
from market_radar.intelligence.contracts.strategy import (
    StrategyPack, StrategyOrigin, StrategyInstance,
    StrategyInstanceState, InstanceTransition,
)


class TestStrategyPack:
    def test_valid_pack(self):
        pack = StrategyPack(
            strategy_id="str_001",
            name="Test Strategy",
            abstention_logic="Wait for clearer signal",
            invalidation_conditions=["Regime shift detected"],
        )
        errors = pack.validate()
        assert len(errors) == 0

    def test_missing_abstention_logic(self):
        pack = StrategyPack(strategy_id="str_002", name="Bad Strategy")
        errors = pack.validate()
        assert any("abstention_logic" in e for e in errors)

    def test_missing_invalidation_conditions(self):
        pack = StrategyPack(
            strategy_id="str_003",
            name="Bad Strategy",
            abstention_logic="Wait",
        )
        errors = pack.validate()
        assert any("invalidation_condition" in e.lower() for e in errors)

    def test_missing_strategy_id(self):
        pack = StrategyPack(
            strategy_id="",
            name="Missing ID",
            abstention_logic="Wait",
            invalidation_conditions=["test"],
        )
        errors = pack.validate()
        assert any("strategy_id" in e for e in errors)

    def test_missing_name(self):
        pack = StrategyPack(
            strategy_id="str_004",
            name="",
            abstention_logic="Wait",
            invalidation_conditions=["test"],
        )
        errors = pack.validate()
        assert any("name" in e for e in errors)

    def test_unverified_source_seed(self):
        pack = StrategyPack(
            strategy_id="str_005",
            name="Trader algo",
            origin=StrategyOrigin(origin_type="trader"),
            abstention_logic="No clear edge",
            invalidation_conditions=["Stop loss triggered"],
        )
        assert pack.historical_validation_status == "unverified"


class TestStrategyInstance:
    def test_initial_state_inactive(self):
        inst = StrategyInstance(
            instance_id="sti_001",
            strategy_id="str_001",
            asset="BTC",
            time_horizon="short_term",
        )
        assert inst.state == StrategyInstanceState.INACTIVE

    def test_custom_initial_state(self):
        inst = StrategyInstance(
            instance_id="sti_002",
            strategy_id="str_001",
            asset="ETH",
            time_horizon="medium_term",
            state=StrategyInstanceState.WATCHING,
        )
        assert inst.state == StrategyInstanceState.WATCHING

    def test_transition_history(self):
        inst = StrategyInstance(
            instance_id="sti_003",
            strategy_id="str_001",
            asset="BTC",
            time_horizon="swing",
        )
        assert len(inst.transitions) == 0
