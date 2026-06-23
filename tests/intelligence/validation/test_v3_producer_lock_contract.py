"""Test V3 producer lock has correct YAML types."""
import pathlib, yaml

VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_lock_yaml_types():
    lock_path = VD3 / "upstream" / "LANE_C_PRODUCER_LOCK.yaml"
    assert lock_path.exists()
    lock = yaml.safe_load(lock_path.read_text("utf-8"))
    assert isinstance(lock["producer_audit_violations_ok"], bool), "audit_violations_ok should be bool"
    for name, art in lock.get("artifacts", {}).items():
        assert isinstance(art["source_and_copy_equal"], bool), f"{name}: source_and_copy_equal should be bool"
        assert isinstance(art["record_count"], int), f"{name}: record_count should be int"
