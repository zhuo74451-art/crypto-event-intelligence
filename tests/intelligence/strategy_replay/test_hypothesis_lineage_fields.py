"""Test hypotheses have complete lineage fields."""
import json, pathlib

D = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "strategy_replay" / "pilot_v2"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def test_all_hypotheses_have_lineage():
    hyps = load_jsonl(D / "strategy_hypotheses_v2.jsonl")
    for h in hyps:
        assert h.get("release_unit_id"), f"Missing release_unit_id: {h.get('hypothesis_id','')[:20]}"
        assert h.get("constituent_event_ids"), f"Missing constituent_event_ids: {h.get('hypothesis_id','')[:20]}"
        assert h.get("event_families"), f"Missing event_families: {h.get('hypothesis_id','')[:20]}"
        assert h.get("decision_unit_id"), f"Missing decision_unit_id: {h.get('hypothesis_id','')[:20]}"
        assert h.get("decision_cutoff_utc"), f"Missing decision_cutoff_utc: {h.get('hypothesis_id','')[:20]}"
        assert h.get("signal_window_id"), f"Missing signal_window_id: {h.get('hypothesis_id','')[:20]}"
        assert h.get("signal_direction"), f"Missing signal_direction: {h.get('hypothesis_id','')[:20]}"
        assert h.get("precision_class"), f"Missing precision_class: {h.get('hypothesis_id','')[:20]}"
