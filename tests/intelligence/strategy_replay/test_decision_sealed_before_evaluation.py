"""Test decision seal exists and is valid."""
import json, pathlib, hashlib

D = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "strategy_replay" / "pilot_v2"


def test_decision_seal_exists():
    seal_path = D / "decision_seal_v1.json"
    assert seal_path.exists(), "decision_seal_v1.json not found"
    seal = json.loads(seal_path.read_text("utf-8"))
    assert seal.get("sealed_before_evaluation") is True, "Seal not marked sealed_before_evaluation"
    assert seal.get("hypotheses_sha256"), "Missing hypotheses_sha256 in seal"
    current = hashlib.sha256((D / "strategy_hypotheses_v2.jsonl").read_bytes()).hexdigest()
    assert current == seal["hypotheses_sha256"], "Hypotheses hash changed since seal!"
