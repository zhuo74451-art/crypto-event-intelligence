"""Test full strategy_replay test suite runs in one pass, order-independent."""
import subprocess, sys, pathlib


def test_full_suite_order_independence():
    """Run the entire strategy_replay test directory and confirm 0 failures."""
    test_dir = pathlib.Path(__file__).parents[3] / "tests" / "intelligence" / "strategy_replay"
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", str(test_dir), "-q", "--tb=short"],
        capture_output=True, text=True
    )
    # Print output for debugging
    output = result.stdout + result.stderr
    print(output[-500:] if len(output) > 500 else output)

    assert result.returncode == 0, (
        f"Full suite failed (exit {result.returncode}). "
        f"Output:\n{output[-1000:]}"
    )
