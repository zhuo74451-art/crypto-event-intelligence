"""Test Lane C producer lock is valid."""
import json, pathlib, hashlib

VD = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v2"
UP = VD / "upstream"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def test_all_artifacts_present():
    expected = ["release_units_v1.jsonl", "decision_inputs_v1.jsonl",
                "macro_abstention_records_v1.jsonl", "strategy_hypotheses_v2.jsonl",
                "evaluation_outcomes_v1.jsonl", "strategy_evaluations_v1.jsonl",
                "baseline_evaluations_v1.jsonl"]
    for f in expected:
        assert (UP / f).exists(), f"Missing upstream artifact: {f}"


def test_correct_counts():
    assert len(load_jsonl(UP / "release_units_v1.jsonl")) == 8
    assert len(load_jsonl(UP / "decision_inputs_v1.jsonl")) == 16
    assert len(load_jsonl(UP / "macro_abstention_records_v1.jsonl")) == 12
    assert len(load_jsonl(UP / "strategy_hypotheses_v2.jsonl")) == 32
    assert len(load_jsonl(UP / "evaluation_outcomes_v1.jsonl")) == 32
    assert len(load_jsonl(UP / "strategy_evaluations_v1.jsonl")) == 32
    assert len(load_jsonl(UP / "baseline_evaluations_v1.jsonl")) == 128


def test_producer_lock_file_exists():
    assert (UP / "LANE_C_PRODUCER_LOCK.yaml").exists()
