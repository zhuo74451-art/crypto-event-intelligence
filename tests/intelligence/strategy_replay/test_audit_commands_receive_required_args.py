"""Test audit scripts exit with error when called without required args."""
import subprocess, sys, pathlib

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "strategy_replay"


def test_leakage_audit_requires_results():
    result = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_replay_leakage.py")],
                            capture_output=True, text=True)
    assert result.returncode != 0, "Leakage audit should fail without --results"


def test_abstention_audit_requires_abstentions():
    result = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_abstention_integrity.py")],
                            capture_output=True, text=True)
    assert result.returncode != 0, "Abstention audit should fail without --abstentions"


def test_kernel_package_audit_requires_packages():
    result = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_kernel_packages.py")],
                            capture_output=True, text=True)
    assert result.returncode != 0, "KP audit should fail without --packages"
