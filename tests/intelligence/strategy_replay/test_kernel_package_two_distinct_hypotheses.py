"""Test kernel packages have 2 distinct hypotheses each."""
import json, pathlib

D = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "strategy_replay" / "pilot_v2"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def test_all_kernel_packages_have_two_distinct_hypotheses():
    kps = load_jsonl(D / "kernel_input_packages_v2.jsonl")
    for kp in kps:
        hids = [h.get("hypothesis_id", "") for h in kp.get("hypotheses", [])]
        assert len(hids) == 2, f"KP {kp.get('kernel_package_id','')[:20]}: expected 2 hypotheses, got {len(hids)}"
        assert len(set(hids)) == 2, f"KP {kp.get('kernel_package_id','')[:20]}: duplicate hypothesis IDs: {hids}"
        horizons = [h.get("time_horizon", "") for h in kp.get("hypotheses", [])]
        assert "continuation_to_4h" in horizons, f"KP: missing continuation_to_4h: {horizons}"
        assert "continuation_to_24h" in horizons, f"KP: missing continuation_to_24h: {horizons}"
