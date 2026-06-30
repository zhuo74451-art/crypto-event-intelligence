
"""Focused tests for strategy evaluators, arbitration, adapters, baselines."""

from __future__ import annotations
import json, tempfile
from pathlib import Path
from market_radar.cognition.strategy_evaluators import (evaluate_all, get_evaluator_ids, StrategyEvaluation)
from market_radar.cognition.arbitration_engine import (arbitrate_with_evaluations, register_strategies, update_registry_status)
from market_radar.cognition.strategy_components import StrategyRegistry, StrategySpec, StrategyStatus
from market_radar.cognition.strategy_library import get_all_strategy_specs, evaluate_strategy_eligibility
from market_radar.cognition.world_model import MarketWorldState
from market_radar.cognition.shadow_runner import evaluate_coverage, evaluate_baselines, evaluate_confidence_calibration, evaluate_leakage, build_evaluation_report
from market_radar.cognition.contracts import EventState, Assessment, Abstention
from market_radar.cognition.intake_adapters import QuickFlashJSONLLoader, DirectEvidenceAdapter, MarketStateAdapter
from market_radar.cognition.intake_contracts import MarketStateInput
from market_radar.cognition.world_builder import classify_priced_in, classify_risk_regime, classify_liquidity, classify_trend, classify_leverage, classify_narrative


# ---------- Strategy evaluator tests ----------

def test_all_eight_strategies_execute():
    """All 8 strategy evaluators execute as code."""
    vars_ = {"signed_surprise": 3.0, "price_return": -2.0, "volume_24h": 1e9,
             "funding_rate": 0.002, "open_interest": 1e8,
             "btc_return_24h": 5.0, "eth_return_24h": 2.0,
             "exchange_netflow": 100, "stablecoin_liquidity": 1e7,
             "unlock_amount": 1e6, "circulating_supply": 1e8,
             "incident_severity": "critical", "affected_tvl": 5e7}
    evals = evaluate_all(vars_)
    assert len(evals) == 8, f"Expected 8, got {len(evals)}"
    ids = [e.strategy_id for e in evals]
    assert "event_surprise_momentum_v1" in ids
    assert "post_event_underreaction_v1" in ids
    assert "overreaction_reversal_v1" in ids
    assert "cross_asset_relative_strength_v1" in ids


def test_strategy_trigger_rejection():
    """Strategy with no trigger remains rejected."""
    vars_ = {"signed_surprise": 0.5, "price_return": 0.1}
    evals = evaluate_all(vars_)
    surprise = [e for e in evals if e.strategy_id == "event_surprise_momentum_v1"][0]
    assert surprise.status == "rejected", f"Expected rejected, got {surprise.status}"
    assert "trigger_not_met" in surprise.reason_codes


def test_strategy_abstention_missing_inputs():
    """Strategy with missing inputs abstains."""
    evals = evaluate_all({})
    for e in evals:
        if e.missing_variables:
            assert e.status == "abstained", f"{e.strategy_id} should be abstained"


def test_strategy_eligible():
    """Strategy with trigger met becomes eligible."""
    vars_ = {"signed_surprise": 5.0, "price_return": -3.0, "volume_24h": 1e9}
    evals = evaluate_all(vars_)
    surprise = [e for e in evals if e.strategy_id == "event_surprise_momentum_v1"][0]
    assert surprise.status == "eligible", f"Expected eligible, got {surprise.status}"
    assert surprise.trigger_result is True


# ---------- Arbitration tests ----------

def test_arbitration_consumes_evaluations():
    """Arbitration uses evaluation records correctly."""
    ws = MarketWorldState(as_of="2026-07-01T00:00:00Z")
    evals = evaluate_all({"signed_surprise": 5.0, "price_return": -3.0, "volume_24h": 1e9,
                          "funding_rate": 0.002})
    result = arbitrate_with_evaluations(evals, ws, "evt1")
    assert len(result.eligible_strategies) >= 1
    assert result.outcome in ("actionable_watch", "monitor", "abstain", "insufficient_evidence")


def test_arbitration_priced_in_blocks():
    """Priced-in state affects arbitration outcome."""
    ws = MarketWorldState(as_of="2026-07-01T00:00:00Z")
    evals = evaluate_all({"signed_surprise": 5.0, "price_return": -3.0, "volume_24h": 1e9})
    result = arbitrate_with_evaluations(evals, ws, "evt1", priced_in_label="mostly_priced")
    assert result.outcome == "monitor", f"Expected monitor for priced-in, got {result.outcome}"


def test_arbitration_conflict_blocks():
    """Source conflicts block actionable outcome."""
    ws = MarketWorldState(as_of="2026-07-01T00:00:00Z")
    evals = evaluate_all({"signed_surprise": 5.0, "price_return": -3.0, "volume_24h": 1e9})
    result = arbitrate_with_evaluations(evals, ws, "evt1", has_source_conflicts=True)
    assert result.outcome == "monitor", f"Expected monitor for conflicts, got {result.outcome}"


# ---------- Intake adapter tests ----------

def test_quickflash_jsonl_adapter():
    """QuickFlash JSONL adapter loads and validates."""
    import tempfile
    td = tempfile.mkdtemp()
    f = Path(td) / "test.jsonl"
    f.write_text('{"upstream_item_id":"evt1","cleaned_title":"Test","source_identity":"x_sensor","authority_class":"social_sensor","fact_permission":"single_source"}\n', encoding="utf-8")
    qf = QuickFlashJSONLLoader()
    envs, errs = qf.load(f)
    assert len(envs) == 1, f"Expected 1 envelope, got {len(envs)}"
    assert envs[0].source_identity == "x_sensor"


def test_direct_evidence_upgrade():
    """Direct evidence adapter creates bundles with correct authority."""
    dea = DirectEvidenceAdapter()
    bundle = dea.to_bundle("cisa", title="Test CISA event")
    assert bundle.authority_class == "primary_official", f"Expected primary_official, got {bundle.authority_class}"
    assert bundle.fact_permission == "confirmed"


def test_market_state_adapter_missing_metrics():
    """MarketStateAdapter tracks missing metrics."""
    msa = MarketStateAdapter()
    msi = msa.to_input("BTC", {"price": 50000})
    assert "volume_24h" in msi.missing_metrics
    assert "open_interest" in msi.missing_metrics


# ---------- Classifier tests ----------

def test_classifiers_return_valid_labels():
    """All classifiers return valid labels."""
    risk, _ = classify_risk_regime(5.0, 0.0002)
    assert risk in ("risk_on", "risk_off", "mixed", "unclear"), f"Unexpected: {risk}"
    liq, _ = classify_liquidity(0.0002, 1e9)
    assert liq in ("expanding", "contracting", "unclear"), f"Unexpected: {liq}"
    trend, _ = classify_trend(50000, 48000)
    assert trend in ("trend", "range", "dislocation", "unclear"), f"Unexpected: {trend}"
    lev, _ = classify_leverage(0.0002)
    assert lev in ("low", "normal", "crowded", "stressed"), f"Unexpected: {lev}"
    nav, _ = classify_narrative(30)
    assert nav in ("emerging", "broadening", "crowded", "decaying", "absent"), f"Unexpected: {nav}"
    pi, _ = classify_priced_in(2.5, 3.0)
    assert pi in ("unpriced", "partially_priced", "mostly_priced", "indeterminate"), f"Unexpected: {pi}"


# ---------- Baseline tests ----------

def test_baselines_calculated():
    """Historical baselines produce real values."""
    events = [EventState(event_id="e1", title="Test")]
    assessments = [Assessment(assessment_id="a1", event_id="e1", market_confirmation="supports", overall_confidence=0.6)]
    abstentions = [Abstention(event_id="e2", code="expectation_unavailable")]
    coverage = evaluate_coverage(events, assessments, abstentions)
    assert coverage["coverage_pct"] > 0
    assert coverage["assessment_rate"] >= 0
    cal = evaluate_confidence_calibration(assessments)
    assert cal["mean_confidence"] > 0
    rep = build_evaluation_report(events, assessments, abstentions)
    assert "baselines" in rep
    assert rep["baselines"]["always_neutral_baseline"] is not None
