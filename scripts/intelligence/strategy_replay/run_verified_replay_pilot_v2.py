"""Unified entry point for verified replay pilot v2.
Orchestrates: lock → release units → decisions → evaluation → audit → report.
"""
import json, pathlib, sys, subprocess

WORKTREE = pathlib.Path(r"C:\Users\zhuo7\Desktop\crypto-event-intelligence-worktrees\lane-c-macro-strategy-replay-v1")
sys.path.insert(0, str(WORKTREE))

SCRIPTS = WORKTREE / "scripts" / "intelligence" / "strategy_replay"
OUT = WORKTREE / "data" / "intelligence" / "strategy_replay" / "pilot_v2"


def run_script(name):
    """Run a stage script and report."""
    path = SCRIPTS / name
    print(f"\\n{'='*60}")
    print(f"Running: {name}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(path)],
        capture_output=True, text=True, cwd=str(WORKTREE)
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
        raise RuntimeError(f"{name} failed with code {result.returncode}")
    return result.stdout


def run_pipeline():
    # Stage 1: Build decisions (no future data)
    run_script("build_pilot_decisions_v2.py")

    # Stage 2: Evaluate (reads sealed hypotheses first)
    run_script("evaluate_pilot_decisions_v2.py")

    # Stage 3: Audit
    audit_scripts = ["audit_replay_leakage.py", "audit_abstention_integrity.py", "audit_kernel_packages.py"]
    for script in audit_scripts:
        script_path = SCRIPTS / script
        if script_path.exists():
            print(f"\\n--- {script} ---")
            result = subprocess.run(
                [sys.executable, "-X", "utf8", str(script_path)],
                capture_output=True, text=True, cwd=str(WORKTREE)
            )
            print(result.stdout[:500] if result.stdout else "no output")

    print(f"\\n{'='*60}")
    print("Pipeline complete.")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_pipeline()
