"""Test V3 baseline coverage contract is correct."""
import json, pathlib

VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def test_baseline_coverage_contract():
    comps = load_jsonl(VD3 / "baselines" / "paired_baseline_comparison_v3.jsonl")
    for c in comps:
        assert c["paired_rows"] == 32, f"{c['baseline_id']}: expected 32 paired, got {c['paired_rows']}"
        assert c["strategy_coverage"]["numerator"] == 32
        assert c["strategy_coverage"]["rate"] == 1.0
        if c["baseline_id"] == "always_abstain":
            assert c["baseline_coverage"]["numerator"] == 0, "always_abstain should have 0 baseline coverage"
            assert c["directional_comparison_applicable"] is False
            assert c["strategy_correct"] is None
        else:
            assert c["baseline_coverage"]["numerator"] == 32, f"{c['baseline_id']}: expected 32 baseline coverage"
            assert c["baseline_coverage"]["rate"] == 1.0, f"{c['baseline_id']}: baseline coverage rate should be 1.0"
            assert c["strategy_correct"] is not None
