import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate whether Hyperliquid baseline is ready for official daily digest wording.")
    parser.add_argument("--input", default=str(ROOT / "results" / "v14_hyperliquid_snapshot_v2_summary.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_hyperliquid_baseline_readiness.csv"))
    parser.add_argument("--md-output", default=str(ROOT / "results" / "v14_hyperliquid_baseline_readiness.md"))
    parser.add_argument("--min-baseline-hours", type=float, default=24.0)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def safe_float(value) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return 0.0


def render(row: dict) -> str:
    lines = [
        "# Hyperliquid Baseline Readiness",
        "",
        f"生成时间：中国时间 {row['generated_at_china']}",
        "",
        f"- baseline_status: {row['baseline_status']}",
        f"- baseline_age_hours: {row['baseline_age_hours']}",
        f"- readiness_status: {row['readiness_status']}",
        f"- digest_label: {row['digest_label']}",
        f"- next_action: {row['next_action']}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.input))
    source = rows[-1] if rows else {}
    age = safe_float(source.get("baseline_age_hours"))
    baseline_status = str(source.get("baseline_status") or "missing")
    ready = baseline_status == "ok" and age >= args.min_baseline_hours
    partial = age > 0 and not ready
    output = {
        "generated_at_china": china_stamp(),
        "baseline_status": baseline_status,
        "baseline_age_hours": round(age, 2),
        "min_baseline_hours": args.min_baseline_hours,
        "readiness_status": "ready" if ready else "beta_partial" if partial else "missing",
        "digest_label": "正式版" if ready else "Beta：基线不足24小时" if partial else "Beta：暂无基线",
        "next_action": "可移除不足24小时提示" if ready else "继续积累快照，满24小时后重新验证",
        "status": "pass" if ready else "review",
    }
    write_rows(normalize_path(args.output), [output], list(output.keys()))
    normalize_path(args.md_output).write_text(render(output), encoding="utf-8")
    print(f"readiness_status={output['readiness_status']}")
    print(f"baseline_age_hours={output['baseline_age_hours']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
