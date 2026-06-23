"""Test folds are chronological with no violations."""
import json, pathlib

VD = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v2"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def test_no_temporal_overlap():
    folds = load_jsonl(VD / "folds" / "walkforward_fold_evaluations_v2.jsonl")
    for f in folds:
        assert f.get("temporal_overlap_violations", 99) == 0, f"Temporal overlap in {f['fold_id']}"
        assert f.get("purge_violations", 99) == 0, f"Purge violation in {f['fold_id']}"
        assert f.get("rule_fitting_performed") is False, f"Rule fitting in {f['fold_id']}"


def test_four_folds():
    folds = load_jsonl(VD / "folds" / "walkforward_fold_evaluations_v2.jsonl")
    assert len(folds) == 4, f"Expected 4 folds, got {len(folds)}"
