import yaml, json, pathlib, hashlib

DOC = pathlib.Path(__file__).parents[3] / "docs" / "execution" / "lane_d"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_all_declared_hashes_match():
    manifest = DOC / "PILOT_V3_INTEGRATION_MANIFEST.yaml"
    assert manifest.exists()
    data = yaml.safe_load(manifest.read_text("utf-8"))
    outputs = data.get("outputs", {})
    mismatches = []
    for key, info in outputs.items():
        if not isinstance(info, dict):
            continue
        path = info.get("path", "")
        expected = info.get("sha256")
        if not path or not expected:
            continue
        full_path = pathlib.Path(__file__).parents[3] / path
        if not full_path.exists():
            mismatches.append(f"{key}: file not found: {path}")
            continue
        actual = hashlib.sha256(full_path.read_bytes()).hexdigest()
        if actual != expected:
            mismatches.append(f"{key}: expected {expected[:16]}..., got {actual[:16]}...")
    assert len(mismatches) == 0, f"Hash mismatches:\n" + "\n".join(mismatches)


def test_integrity_audit_hash_matches():
    """Specifically check the integrity_audit report that was just regenerated."""
    manifest = DOC / "PILOT_V3_INTEGRATION_MANIFEST.yaml"
    data = yaml.safe_load(manifest.read_text("utf-8"))
    audit_info = data.get("outputs", {}).get("integrity_audit", {})
    if not audit_info:
        # The integrity_audit isn't in REQUIRED, so it may or may not be listed
        return  # Not all manifests include it — skip if missing
    expected = audit_info.get("sha256", "")
    assert expected, "integrity_audit declared but missing sha256"
    actual = hashlib.sha256((pathlib.Path(__file__).parents[3] / audit_info["path"]).read_bytes()).hexdigest()
    assert actual == expected, f"integrity_audit hash mismatch: {actual[:16]} != {expected[:16]}"


def test_required_unavailable_status_artifacts_present():
    """calibration, multiple_testing, drift status files must exist even if status=unavailable."""
    for name in ["calibration", "multiple_testing", "drift"]:
        p = VD3 / name / f"{name}_status_v3.json"
        assert p.exists(), f"Missing required artifact: {p}"
        data = json.loads(p.read_text("utf-8"))
        assert data.get("status") == "unavailable", f"{name} status should be unavailable, got {data.get('status')}"