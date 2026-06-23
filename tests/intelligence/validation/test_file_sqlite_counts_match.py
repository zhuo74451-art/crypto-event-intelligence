"""Test file record counts match SQLite."""
import sqlite3, json, pathlib

VD = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v2"
DB = VD / "indexes" / "validation_pilot_v2.sqlite"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def test_counts_match():
    conn = sqlite3.connect(str(DB))
    checks = [
        ("directional_validation", "datasets/directional_validation_dataset_v2.jsonl"),
        ("macro_abstentions", "datasets/macro_abstention_dataset_v2.jsonl"),
        ("fold_evaluations", "folds/walkforward_fold_evaluations_v2.jsonl"),
        ("baseline_comparisons", "baselines/paired_baseline_comparison_v2.jsonl"),
        ("leave_one_unit_out", "evaluations/leave_one_release_unit_out_v2.jsonl"),
        ("failed_experiments", "failed_experiments/failed_experiments_v2.jsonl"),
    ]
    for table, fpath in checks:
        fc = len(load_jsonl(VD / fpath))
        dc = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        assert fc == dc, f"Mismatch {table}: file={fc} db={dc}"
    conn.close()
