import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local private-pilot daily workflow.")
    parser.add_argument("--draft-input", default="data/event_candidates_v06_clean_low_risk_preview.csv")
    parser.add_argument("--prefilter-output", default="data/event_candidates_v06_tg_prefilter_pass.csv")
    parser.add_argument("--prefilter-rejects", default="data/event_candidates_v06_tg_prefilter_rejects.csv")
    parser.add_argument("--draft-output", default="data/tg_drafts_v06_private_pilot.csv")
    parser.add_argument("--draft-markdown", default="results/tg_drafts_v06_private_pilot.md")
    parser.add_argument("--draft-limit", type=int, default=20)
    parser.add_argument("--ai-review", action="store_true", help="Run OpenRouter/Claude review using OPENROUTER_API_KEY from the current environment.")
    parser.add_argument("--skip-project-refresh", action="store_true")
    return parser.parse_args()


def run_step(name: str, args: list[str]) -> None:
    print(f"\n== {name} ==")
    print(" ".join([sys.executable, *args]))
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main() -> int:
    args = parse_args()
    try:
        run_step(
            "prefilter TG draft candidates",
            [
                "scripts/prefilter_tg_draft_candidates.py",
                "--input",
                args.draft_input,
                "--output",
                args.prefilter_output,
                "--rejects-output",
                args.prefilter_rejects,
                "--summary",
                "results/tg_draft_prefilter_summary.csv",
            ],
        )
        run_step(
            "generate local TG drafts",
            [
                "scripts/generate_tg_drafts.py",
                "--input",
                args.prefilter_output,
                "--output",
                args.draft_output,
                "--markdown-output",
                args.draft_markdown,
                "--limit",
                str(args.draft_limit),
            ],
        )
        if args.ai_review:
            run_step(
                "AI-review local TG drafts",
                [
                    "scripts/ai_review_tg_drafts.py",
                    "--input",
                    args.draft_output,
                    "--output",
                    "data/tg_drafts_v06_private_pilot_ai_reviewed.csv",
                    "--summary",
                    "results/tg_draft_ai_review_summary.csv",
                    "--limit",
                    str(args.draft_limit),
                    "--apply",
                ],
            )
        run_step(
            "validate local TG drafts",
            [
                "scripts/validate_tg_drafts.py",
                "--input",
                args.draft_output,
                "--output",
                "results/tg_draft_validation_report.csv",
                "--summary",
                "results/tg_draft_validation_summary.csv",
                "--markdown-output",
                "results/tg_draft_validation_report.md",
            ],
        )
        run_step(
            "summarize TG draft feedback",
            [
                "scripts/summarize_tg_draft_feedback.py",
                "--input",
                args.draft_output,
                "--summary",
                "results/tg_draft_feedback_summary.csv",
                "--markdown-output",
                "results/tg_draft_feedback_summary.md",
            ],
        )
        run_step(
            "prepare TG draft review packet",
            [
                "scripts/prepare_tg_draft_review_packet.py",
                "--input",
                args.draft_output,
                "--output",
                "data/tg_draft_review_packet.csv",
                "--markdown-output",
                "results/tg_draft_review_packet.md",
                "--limit",
                str(args.draft_limit),
                "--only-pending",
            ],
        )
        run_step(
            "classify other_review reasons",
            [
                "scripts/classify_other_review_reasons.py",
                "--input",
                "data/event_candidates_v06_other_review_queue.csv",
                "--output",
                "data/event_candidates_v06_other_review_classified.csv",
                "--summary",
                "results/v06_other_review_reason_summary.csv",
                "--markdown-output",
                "results/v06_other_review_reason_summary.md",
            ],
        )
        run_step(
            "build TG draft rule-improvement report",
            [
                "scripts/build_tg_draft_rule_improvement_report.py",
                "--input",
                args.draft_output,
                "--output",
                "results/tg_draft_rule_improvement_report.csv",
                "--summary",
                "results/tg_draft_rule_improvement_summary.csv",
                "--markdown-output",
                "results/tg_draft_rule_improvement_report.md",
            ],
        )
        run_step(
            "build approved TG draft pool",
            [
                "scripts/build_approved_tg_draft_pool.py",
                "--input",
                args.draft_output,
                "--output",
                "data/tg_drafts_v06_approved_pool.csv",
                "--summary",
                "results/tg_draft_approved_pool_summary.csv",
                "--markdown-output",
                "results/tg_draft_approved_pool.md",
            ],
        )
        run_step(
            "build daily private-pilot report",
            [
                "scripts/build_daily_private_pilot_report.py",
                "--drafts",
                args.draft_output,
                "--validation",
                "results/tg_draft_validation_summary.csv",
                "--feedback",
                "results/tg_draft_feedback_summary.csv",
                "--other-review",
                "results/v06_other_review_reason_summary.csv",
                "--summary",
                "results/daily_private_pilot_summary.csv",
                "--markdown-output",
                "results/daily_private_pilot_report.md",
            ],
        )
        if not args.skip_project_refresh:
            run_step("build command registry", ["scripts/build_command_registry.py"])
            run_step("build artifact manifest", ["scripts/build_artifact_manifest.py"])
            run_step("refresh project state", ["scripts/refresh_project_state.py"])
            run_step("render project dashboard", ["scripts/render_project_dashboard.py"])
            run_step("validate Project OS", ["scripts/validate_project_os.py"])
            run_step("refresh project state after validation", ["scripts/refresh_project_state.py"])
            run_step("render project dashboard after validation", ["scripts/render_project_dashboard.py"])
    except subprocess.CalledProcessError as exc:
        print(f"step failed: {exc.cmd} exit_code={exc.returncode}")
        return exc.returncode

    print("\nDaily private-pilot workflow completed.")
    print(f"draft_csv={args.draft_output}")
    print(f"draft_markdown={args.draft_markdown}")
    print(f"prefilter_pass={args.prefilter_output}")
    print(f"prefilter_rejects={args.prefilter_rejects}")
    print("validation_summary=results/tg_draft_validation_summary.csv")
    print("feedback_summary=results/tg_draft_feedback_summary.csv")
    print("review_packet=data/tg_draft_review_packet.csv")
    print("approved_pool=data/tg_drafts_v06_approved_pool.csv")
    print("daily_report=results/daily_private_pilot_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
