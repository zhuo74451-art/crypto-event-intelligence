"""Test validation dataset has complete lineage."""
import json, pathlib

VD = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v2"


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def test_directional_rows_have_lineage():
    rows = load_jsonl(VD / "datasets" / "directional_validation_dataset_v2.jsonl")
    for r in rows:
        assert r.get("release_unit_id"), f"Missing release_unit_id: {r['validation_row_id']}"
        assert r.get("decision_unit_id"), f"Missing decision_unit_id: {r['validation_row_id']}"
        assert r.get("hypothesis_id"), f"Missing hypothesis_id: {r['validation_row_id']}"
        assert r.get("dependency_cluster_id"), f"Missing dependency_cluster_id: {r['validation_row_id']}"


def test_macro_abstention_rows():
    rows = load_jsonl(VD / "datasets" / "macro_abstention_dataset_v2.jsonl")
    assert len(rows) == 12
    for r in rows:
        assert r.get("reason_codes"), f"Missing reason_codes: {r['validation_row_id']}"
