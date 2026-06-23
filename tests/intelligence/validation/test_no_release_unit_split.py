"""Test no release unit is split across train/test."""
import json, pathlib

VD = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v2"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def test_no_split():
    folds = load_jsonl(VD / "folds" / "walkforward_fold_evaluations_v2.jsonl")
    for f in folds:
        train_ids = set(f.get("train_release_unit_ids", []))
        test_ids = set(f.get("test_release_unit_ids", []))
        assert len(train_ids & test_ids) == 0, f"Release unit split in {f['fold_id']}"
