"""Test outcomes have dual window lineage (signal + target)."""
import json, pathlib

D = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "strategy_replay" / "pilot_v2"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def test_all_outcomes_have_dual_window_lineage():
    outs = load_jsonl(D / "evaluation_outcomes_v1.jsonl")
    for o in outs:
        assert o.get("signal_window_id"), f"Missing signal_window_id: {o.get('outcome_id','')[:20]}"
        assert o.get("target_window_id"), f"Missing target_window_id: {o.get('outcome_id','')[:20]}"
        refs = o.get("source_window_ids", [])
        assert len(refs) == 2, f"Expected 2 source_window_ids, got {len(refs)}: {o.get('outcome_id','')[:20]}"
        sp = o.get("outcome_start_price_source", {})
        assert sp.get("field") == "signal_endpoint_price", f"Bad start source field: {sp.get('field')}"
        assert sp.get("window_id"), f"Missing start window_id"
        ep = o.get("outcome_end_price_source", {})
        assert ep.get("field") == "post_bar_close", f"Bad end source field: {ep.get('field')}"
        assert ep.get("window_id"), f"Missing end window_id"
