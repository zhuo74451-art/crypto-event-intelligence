import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one full v0.6 labeling cycle: AI pre-label, evaluate, prepare manual batch, refresh state/dashboard."
    )
    parser.add_argument("--sheet", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--batch-output", default=str(ROOT / "data" / "v06_manual_label_batch.csv"))
    parser.add_argument("--review-packet-output", default=str(ROOT / "data" / "v06_manual_label_batch_review.csv"))
    parser.add_argument("--auto-verify-provisional", action="store_true")
    parser.add_argument("--auto-verify-audit-size", type=int, default=20)
    parser.add_argument("--auto-close-low-risk", action="store_true")
    parser.add_argument("--auto-close-audit-size", type=int, default=20)
    parser.add_argument("--auto-fill-unlabeled", action="store_true")
    parser.add_argument("--auto-fill-unlabeled-audit-size", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--review-required-quota", type=int, default=10)
    parser.add_argument("--min-confidence", type=float, default=0.90)
    parser.add_argument("--apply-provisional", action="store_true")
    parser.add_argument("--provisional-min-confidence", type=float, default=0.75)
    parser.add_argument("--no-apply-high-confidence", action="store_true")
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    print("running: " + " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    args = parse_args()
    apply_flag = [] if args.no_apply_high_confidence else ["--apply-high-confidence"]
    provisional_flag = ["--apply-provisional", "--provisional-min-confidence", str(args.provisional_min_confidence)] if args.apply_provisional else []

    try:
        run(
            [
                sys.executable,
                "scripts/auto_label_v06_sheet.py",
                "--input",
                args.sheet,
                "--output",
                args.sheet,
                "--summary",
                str(ROOT / "results" / "v06_auto_label_summary.csv"),
                "--min-confidence",
                str(args.min_confidence),
                *apply_flag,
                *provisional_flag,
            ]
        )
        if args.auto_verify_provisional:
            run(
                [
                    sys.executable,
                    "scripts/auto_verify_v06_provisional_labels.py",
                    "--input",
                    args.sheet,
                    "--output",
                    args.sheet,
                    "--summary",
                    str(ROOT / "results" / "v06_auto_verify_summary.csv"),
                    "--audit-output",
                    str(ROOT / "data" / "v06_auto_verify_audit_sample.csv"),
                    "--audit-size",
                    str(args.auto_verify_audit_size),
                ]
            )
        if args.auto_close_low_risk:
            run(
                [
                    sys.executable,
                    "scripts/auto_close_low_risk_unlabeled.py",
                    "--input",
                    args.sheet,
                    "--output",
                    args.sheet,
                    "--summary",
                    str(ROOT / "results" / "v06_auto_close_summary.csv"),
                    "--audit-output",
                    str(ROOT / "data" / "v06_auto_close_audit_sample.csv"),
                    "--audit-size",
                    str(args.auto_close_audit_size),
                ]
            )
        if args.auto_fill_unlabeled:
            run(
                [
                    sys.executable,
                    "scripts/auto_fill_unlabeled_review_required.py",
                    "--input",
                    args.sheet,
                    "--output",
                    args.sheet,
                    "--summary",
                    str(ROOT / "results" / "v06_auto_fill_unlabeled_summary.csv"),
                    "--audit-output",
                    str(ROOT / "data" / "v06_auto_fill_unlabeled_audit_sample.csv"),
                    "--audit-size",
                    str(args.auto_fill_unlabeled_audit_size),
                ]
            )
        run(
            [
                sys.executable,
                "scripts/evaluate_manual_labels.py",
                "--input",
                args.sheet,
                "--summary",
                str(ROOT / "results" / "v06_manual_label_eval_summary.csv"),
                "--errors",
                str(ROOT / "results" / "v06_manual_label_eval_errors.csv"),
            ]
        )
        run(
            [
                sys.executable,
                "scripts/prepare_labeling_batch.py",
                "--input",
                args.sheet,
                "--output",
                args.batch_output,
                "--summary",
                str(ROOT / "results" / "v06_labeling_batch_summary.csv"),
                "--batch-size",
                str(args.batch_size),
                "--review-required-quota",
                str(args.review_required_quota),
            ]
        )
        run(
            [
                sys.executable,
                "scripts/export_v06_review_packet.py",
                "--input",
                args.batch_output,
                "--output",
                args.review_packet_output,
            ]
        )
        run([sys.executable, "scripts/refresh_project_state.py"])
        run([sys.executable, "scripts/render_project_dashboard.py"])
    except subprocess.CalledProcessError as exc:
        print(f"v0.6 labeling cycle failed with exit code {exc.returncode}")
        return exc.returncode

    print("v0.6 labeling cycle complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
