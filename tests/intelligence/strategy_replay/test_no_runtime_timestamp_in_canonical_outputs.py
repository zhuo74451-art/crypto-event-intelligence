"""Test canonical outputs have no fabricated timestamps."""
import json, pathlib

D = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "strategy_replay" / "pilot_v2"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def test_no_generated_at_utc_in_results():
    results = load_jsonl(D / "strategy_replay_results_v2.jsonl")
    for r in results:
        val = r.get("generated_at_utc")
        assert val is None or val == "", f"Non-null generated_at_utc found: {r.get('replay_result_id','')[:20]} = {val}"


def test_no_generated_at_utc_in_hypotheses():
    hyps = load_jsonl(D / "strategy_hypotheses_v2.jsonl")
    for h in hyps:
        val = h.get("generated_at_utc")
        assert val is None or val == "", f"Non-null generated_at_utc in hypothesis: {h.get('hypothesis_id','')[:20]} = {val}"
