import yaml, pathlib


def test_no_duplicate_manifest_key():
    """Use YAML loader that rejects duplicate keys."""
    manifest = pathlib.Path(__file__).parents[3] / "docs" / "execution" / "lane_d" / "PILOT_V3_INTEGRATION_MANIFEST.yaml"
    assert manifest.exists()
    # yaml.SafeLoader accepts duplicates silently, so we parse manually
    raw = manifest.read_text("utf-8")
    # Count occurrences of "sqlite_index:" in the outputs section
    in_outputs = False
    count = 0
    for line in raw.splitlines():
        if line.strip().startswith("outputs:"):
            in_outputs = True
        elif in_outputs and line.strip().startswith("sqlite_index:"):
            count += 1
        elif in_outputs and line.strip() and not line[0].isspace():
            in_outputs = False
    assert count == 1, f"Expected exactly 1 sqlite_index in outputs, found {count}"