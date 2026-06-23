"""Test macro abstentions are not counted as strategy errors."""
import json


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]

import json, pathlib

VD = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v2"


def test_macro_abstentions():
    rows = load_jsonl(VD / "datasets" / "macro_abstention_dataset_v2.jsonl")
    assert len(rows) == 12
    for r in rows:
        assert "consensus_missing" in r.get("reason_codes", [])


def test_macro_directional_zero():
    rows = load_jsonl(VD / "datasets" / "directional_validation_dataset_v2.jsonl")
    macro_rows = [r for r in rows if r.get("strategy_id", "").startswith("strat_us_")]
    assert len(macro_rows) == 0, "Macro strategies should not appear in directional dataset"
