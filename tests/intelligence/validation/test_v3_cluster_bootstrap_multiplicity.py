"""Test V3 cluster bootstrap preserves duplicate multiplicity."""
import json, pathlib

VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_bootstrap_min_max_rows():
    p = VD3 / "bootstrap" / "cluster_bootstrap_summary_v3.json"
    assert p.exists(), "Bootstrap summary not found"
    boot = json.loads(p.read_text("utf-8"))
    assert boot.get("minimum_sampled_row_count", 0) >= 32, "min_rows should be 32"
    assert boot.get("maximum_sampled_row_count", 0) >= 32, "max_rows should be 32"
    assert boot.get("duplicate_cluster_draws_observed") is True, "Multiplicity not preserved"
    assert boot.get("algorithm_version") == "3.0.0", "Wrong algorithm version"
    assert boot.get("inferential_use") is False, "inferential_use should be False"
    assert boot.get("cluster_count_insufficient") is True, "cluster_count_insufficient should be True"
