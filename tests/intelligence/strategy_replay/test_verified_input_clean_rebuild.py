"""Test prepare script produces correct outputs from git objects."""
import subprocess, sys, pathlib

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "strategy_replay"


def test_prepare_produces_correct_counts():
    result = subprocess.run([sys.executable, "-X", "utf8", str(SD / "prepare_verified_pilot_inputs_v3.py")],
                             capture_output=True, text=True)
    assert result.returncode == 0, f"Prepare failed: {result.stderr[:200]}"
    import json
    for line in result.stdout.strip().splitlines():
        try:
            data = json.loads(line)
            if "release_units" in data:
                assert data["release_units"] == 8, f"Expected 8 RUs, got {data['release_units']}"
            if "decision_inputs" in data:
                assert data["decision_inputs"] == 16, f"Expected 16 DUs, got {data['decision_inputs']}"
        except json.JSONDecodeError:
            pass
