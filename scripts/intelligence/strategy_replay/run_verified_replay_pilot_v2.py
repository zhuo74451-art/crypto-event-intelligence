#!/usr/bin/env python
"""Unified entry point for verified replay pilot V3 — full clean rebuild.
Supports --output-dir for test isolation.
"""
import subprocess, sys, pathlib, json, hashlib, shutil

DEFAULT_WORKTREE = pathlib.Path(r"C:\Users\zhuo7\Desktop\crypto-event-intelligence-worktrees\lane-c-macro-strategy-replay-v1")
DEFAULT_SD = DEFAULT_WORKTREE / "scripts" / "intelligence" / "strategy_replay"
DEFAULT_OUT = DEFAULT_WORKTREE / "data" / "intelligence" / "strategy_replay" / "pilot_v2"
DEFAULT_INDEX_DIR = DEFAULT_WORKTREE / "data" / "intelligence" / "strategy_replay" / "indexes"


def run(cmd, cwd=None):
    if cwd is None:
        cwd = DEFAULT_WORKTREE
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))
    if result.stdout:
        print(result.stdout[-400:] if len(result.stdout) > 400 else result.stdout)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr[-400:]}")
        raise RuntimeError(f"Command failed: {' '.join(cmd)} (exit {result.returncode})")
    return result


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def run_pipeline(clean=True, output_dir=None, worktree=None):
    if worktree is None:
        worktree = DEFAULT_WORKTREE
    if output_dir is None:
        out = DEFAULT_OUT
        index_dir = DEFAULT_INDEX_DIR
        sd = DEFAULT_SD
    else:
        out = pathlib.Path(output_dir)
        index_dir = out / ".." / "indexes"
        sd = worktree / "scripts" / "intelligence" / "strategy_replay"

    out.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    upstream_dir = out / "upstream"
    upstream_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("LANE C — VERIFIED REPLAY PILOT V3")
    print("=" * 60)

    if clean:
        print("\n--- Stage 0: Clean ---")
        for name in ["release_units_v1.jsonl", "decision_inputs_v1.jsonl",
                     "macro_abstention_records_v1.jsonl", "strategy_replay_results_v2.jsonl",
                     "strategy_hypotheses_v2.jsonl", "kernel_input_packages_v2.jsonl",
                     "abstention_records_v2.jsonl", "evaluation_outcomes_v1.jsonl",
                     "strategy_evaluations_v1.jsonl", "baseline_evaluations_v1.jsonl",
                     "decision_seal_v1.json",   # pilot_integrity_audit_v3.json is committed - not cleaned
                     "pilot_replay_report_v3.json", "pilot_replay_report_v3.md"]:
            p = out / name
            if p.exists(): p.unlink()
        db = index_dir / "strategy_replay_pilot_v2.sqlite"
        if db.exists(): db.unlink()
        print("  Clean complete.")

    print("\n--- Stage 1: Prepare inputs ---")
    run([sys.executable, "-X", "utf8", str(sd / "prepare_verified_pilot_inputs_v3.py"),
         "--output-dir", str(out)], cwd=worktree)

    print("\n--- Stage 2: Build decisions ---")
    run([sys.executable, "-X", "utf8", str(sd / "build_pilot_decisions_v2.py"),
         "--output-dir", str(out)], cwd=worktree)

    print("\n--- Stage 3: Seal decisions ---")
    seal = {
        "decision_inputs_sha256": sha256(out / "decision_inputs_v1.jsonl"),
        "hypotheses_sha256": sha256(out / "strategy_hypotheses_v2.jsonl"),
        "replay_results_sha256": sha256(out / "strategy_replay_results_v2.jsonl"),
        "producer_locks_sha256": sha256(out / "upstream" / "PRODUCER_LOCKS.yaml"),
        "sealed_before_evaluation": True,
    }
    (out / "decision_seal_v1.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    print(f"  Decision seal written.")

    print("\n--- Stage 4: Evaluate ---")
    run([sys.executable, "-X", "utf8", str(sd / "evaluate_pilot_decisions_v2.py"),
         "--output-dir", str(out)], cwd=worktree)

    print("\n--- Stage 5: Verify seal ---")
    current = {
        "decision_inputs_sha256": sha256(out / "decision_inputs_v1.jsonl"),
        "hypotheses_sha256": sha256(out / "strategy_hypotheses_v2.jsonl"),
        "replay_results_sha256": sha256(out / "strategy_replay_results_v2.jsonl"),
    }
    original = {k: v for k, v in seal.items() if k != "sealed_before_evaluation" and k != "producer_locks_sha256"}
    assert current == original, f"Seal violation! Decision outputs changed during evaluation."
    print("  Seal intact.")

    print("\n--- Stage 6: Build SQLite ---")
    run([sys.executable, "-X", "utf8", str(sd / "build_sqlite_index.py"),
         "--output-dir", str(out)], cwd=worktree)

    print("\n--- Stage 7: Run audits ---")
    run([sys.executable, "-X", "utf8", str(sd / "audit_replay_leakage.py"),
         "--results", str(out / "strategy_replay_results_v2.jsonl"),
         "--hypotheses", str(out / "strategy_hypotheses_v2.jsonl"),
         "--decision-inputs", str(out / "decision_inputs_v1.jsonl"),
         "--horizon-windows", str(out / "upstream" / "lane_b_horizon_windows_v3.jsonl"),
         "--decision-seal", str(out / "decision_seal_v1.json"),
         "--evaluation-outcomes", str(out / "evaluation_outcomes_v1.jsonl")])
    run([sys.executable, "-X", "utf8", str(sd / "audit_abstention_integrity.py"),
         "--abstentions", str(out / "macro_abstention_records_v1.jsonl")])
    run([sys.executable, "-X", "utf8", str(sd / "audit_kernel_packages.py"),
         "--packages", str(out / "kernel_input_packages_v2.jsonl")])
    print("  All audits passed.")

    print("\n--- Stage 8: Reports ---")
    report = {
        "status": "verified_small_sample_replay_pilot",
        "causal_inference_supported": False,
        "probability_supported": False,
        "calibration_supported": False,
        "walkforward_supported": False,
        "full_historical_coverage": False,
        "counts": {
            "canonical_macro_events": 12,
            "release_units": len([json.loads(l) for l in (out / "release_units_v1.jsonl").read_text("utf-8").strip().splitlines()]),
            "decision_units": len([json.loads(l) for l in (out / "decision_inputs_v1.jsonl").read_text("utf-8").strip().splitlines()]),
            "macro_abstentions": len([json.loads(l) for l in (out / "macro_abstention_records_v1.jsonl").read_text("utf-8").strip().splitlines()]),
            "macro_directional_hypotheses": 0,
            "replay_results": len([json.loads(l) for l in (out / "strategy_replay_results_v2.jsonl").read_text("utf-8").strip().splitlines()]),
            "hypotheses": len([json.loads(l) for l in (out / "strategy_hypotheses_v2.jsonl").read_text("utf-8").strip().splitlines()]),
            "kernel_packages": len([json.loads(l) for l in (out / "kernel_input_packages_v2.jsonl").read_text("utf-8").strip().splitlines()]),
            "evaluation_outcomes": len([json.loads(l) for l in (out / "evaluation_outcomes_v1.jsonl").read_text("utf-8").strip().splitlines()]),
            "strategy_evaluations": len([json.loads(l) for l in (out / "strategy_evaluations_v1.jsonl").read_text("utf-8").strip().splitlines()]),
            "baseline_evaluations": len([json.loads(l) for l in (out / "baseline_evaluations_v1.jsonl").read_text("utf-8").strip().splitlines()]),
        },
    }
    (out / "pilot_replay_report_v3.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    c = report["counts"]
    md = f"""# Pilot Replay Report V3

## Status
**verified_small_sample_replay_pilot**

## Boundaries
| Property | Value |
|----------|-------|
| Causal inference supported | False |
| Probability supported | False |
| Calibration supported | False |
| Walk-forward supported | False |
| Full historical coverage | False |

## Counts
| Metric | Count |
|--------|-------|
| Canonical macro events | 12 |
| Release units | {c["release_units"]} |
| Decision units | {c["decision_units"]} |
| Macro abstentions | {c["macro_abstentions"]} |
| Macro directional hypotheses | 0 |
| Replay results | {c["replay_results"]} |
| Hypotheses | {c["hypotheses"]} |
| Kernel packages | {c["kernel_packages"]} |
| Evaluation outcomes | {c["evaluation_outcomes"]} |
| Strategy evaluations | {c["strategy_evaluations"]} |
| Baseline evaluations | {c["baseline_evaluations"]} |
"""
    (out / "pilot_replay_report_v3.md").write_text(md, encoding="utf-8")

    print(f"\nPIPELINE COMPLETE. Counts: {json.dumps(c)}")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-clean", action="store_true")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: pilot_v2)")
    parser.add_argument("--worktree", default=None, help="Worktree root (default: lane-c worktree)")
    args = parser.parse_args()
    run_pipeline(clean=not args.no_clean, output_dir=args.output_dir, worktree=args.worktree)
