import argparse
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local TG alert-quality loop.")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--followup-min-age-hours", type=float, default=4)
    parser.add_argument("--followup-limit", type=int, default=200)
    parser.add_argument("--strict", default="false", help="If true, stop on first failed step.")
    return parser.parse_args()


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def china_now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def run_step(name: str, command: list[str], strict: bool) -> dict:
    started = china_now()
    print(f"[{name}] start {started}")
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    status = "pass" if result.returncode == 0 else "fail"
    print(f"[{name}] {status}")
    if strict and result.returncode != 0:
        raise SystemExit(result.returncode)
    return {
        "step": name,
        "status": status,
        "returncode": result.returncode,
        "started_at_china": started,
        "finished_at_china": china_now(),
        "stdout_tail": result.stdout[-500:].replace("\n", " "),
        "stderr_tail": result.stderr[-500:].replace("\n", " "),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["step", "status"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    strict = truthy(args.strict)
    rows: list[dict] = []

    rows.append(run_step("enrich_sent_state", [sys.executable, "scripts/enrich_tg_sent_state_metadata.py"], strict))
    rows.append(
        run_step(
            "build_followup_report",
            [
                sys.executable,
                "scripts/build_tg_alert_followup_report.py",
                "--min-age-hours",
                str(args.followup_min_age_hours),
                "--limit",
                str(args.followup_limit),
            ],
            strict,
        )
    )
    rows.append(
        run_step(
            "build_source_usefulness",
            [
                sys.executable,
                "scripts/build_tg_source_usefulness_report.py",
                "--lookback-days",
                str(args.lookback_days),
            ],
            strict,
        )
    )

    summary_path = ROOT / "results" / "v08_tg_quality_loop_summary.csv"
    write_csv(summary_path, rows)
    failed = sum(1 for row in rows if row["status"] != "pass")
    print(f"failed_steps={failed}")
    print(f"wrote_summary={summary_path}")
    return 1 if failed and strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
