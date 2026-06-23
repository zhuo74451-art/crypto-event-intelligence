"""Test that release_unit_id is the independence unit."""
import json, pathlib

VD = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v2"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def test_independence_units_are_release_units():
    rows = load_jsonl(VD / "datasets" / "directional_validation_dataset_v2.jsonl")
    ru_ids = set(r["release_unit_id"] for r in rows)
    assert len(ru_ids) == 8, f"Expected 8 independent release units, got {len(ru_ids)}"
    for r in rows:
        assert r["dependency_cluster_id"] == r["release_unit_id"], \
            f"dependency_cluster_id should equal release_unit_id: {r['validation_row_id']}"


def test_not_32_independent_events():
    rows = load_jsonl(VD / "datasets" / "directional_validation_dataset_v2.jsonl")
    assert len(rows) == 32, "32 directional rows"
    ru_ids = set(r["release_unit_id"] for r in rows)
    assert len(ru_ids) == 8, f"Only {len(ru_ids)} independent units"
    assert len(ru_ids) != len(rows), "Should not have 32 independent units"
