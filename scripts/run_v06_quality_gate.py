import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the v0.6 intake quality gate and refresh local project state.")
    parser.add_argument("--holdout-size", type=int, default=201)
    parser.add_argument("--skip-synthetic", action="store_true")
    return parser.parse_args()


def run_step(name: str, command: list[str], allow_fail: bool = False) -> int:
    print(f"\n== {name} ==")
    print(" ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0 and not allow_fail:
        print(f"step failed: {name} exit_code={result.returncode}")
        return result.returncode
    if result.returncode != 0:
        print(f"step reported failure but continued: {name} exit_code={result.returncode}")
    return result.returncode


def main() -> int:
    args = parse_args()
    py = sys.executable
    steps: list[tuple[str, list[str], bool]] = []
    if not args.skip_synthetic:
        steps.append(("generate synthetic edge cases", [py, "scripts/generate_v06_synthetic_edge_cases.py"], False))
    steps.extend(
        [
            ("check local environment", [py, "scripts/check_local_environment.py"], False),
            ("build holdout audit sample", [py, "scripts/build_v06_holdout_audit_sample.py", "--size", str(args.holdout_size)], False),
            ("audit manual review required rows", [py, "scripts/audit_v06_manual_review_required.py"], False),
            ("audit v043 selection against v06 relevance", [py, "scripts/audit_v043_selection_against_v06.py"], False),
            ("check secret leaks", [py, "scripts/check_secret_leaks.py"], False),
        ("check strict TG draft pilot gate", [py, "scripts/check_v06_tg_pilot_gate.py"], True),
        ("build command registry", [py, "scripts/build_command_registry.py"], False),
    ]
    )

    gate_exit = 0
    for name, command, allow_fail in steps:
        rc = run_step(name, command, allow_fail=allow_fail)
        if rc != 0 and not allow_fail:
            return rc
        if name == "check strict TG draft pilot gate":
            gate_exit = rc

    # Project OS validation reads dashboard metrics, then the final dashboard
    # must be rendered again so it reflects the just-created validation result.
    for name, command in [
        ("index Claude responses", [py, "scripts/index_claude_responses.py"]),
        ("build Claude decision review queue", [py, "scripts/build_claude_decision_review_queue.py"]),
        ("build backtest readiness report", [py, "scripts/build_backtest_readiness_report.py"]),
        ("refresh project state for validation input", [py, "scripts/refresh_project_state.py"]),
        ("render project dashboard for validation input", [py, "scripts/render_project_dashboard.py"]),
        ("build project review actions", [py, "scripts/build_project_review_actions.py"]),
        ("build artifact manifest", [py, "scripts/build_artifact_manifest.py"]),
        ("render project dashboard after artifact manifest", [py, "scripts/render_project_dashboard.py"]),
        ("validate Project OS", [py, "scripts/validate_project_os.py"]),
        ("refresh project state after validation", [py, "scripts/refresh_project_state.py"]),
        ("render project dashboard after validation", [py, "scripts/render_project_dashboard.py"]),
    ]:
        rc = run_step(name, command)
        if rc != 0:
            return rc

    return gate_exit


if __name__ == "__main__":
    raise SystemExit(main())
