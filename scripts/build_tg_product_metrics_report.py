import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build product-level TG metrics from sent alerts and follow-up data.")
    parser.add_argument("--sent-state", default=str(ROOT / "data" / "tg_live_sent_state.csv"))
    parser.add_argument("--followup", default=str(ROOT / "results" / "v08_tg_alert_followup_backfill.csv"))
    parser.add_argument("--quality-loop", default=str(ROOT / "results" / "v08_tg_quality_loop_summary.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v08_tg_product_metrics.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_tg_product_metrics_summary.csv"))
    parser.add_argument("--lookback-days", type=int, default=7)
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


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def china_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0)


def parse_china_time(value: str) -> datetime | None:
    raw = str(value or "").strip().replace(" UTC+8", "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(raw[:19], fmt).replace(tzinfo=timezone(timedelta(hours=8)))
        except ValueError:
            continue
    return None


def safe_float(value) -> float | None:
    try:
        if str(value or "").strip() == "":
            return None
        return float(str(value).strip())
    except Exception:
        return None


def avg_abs(values: list[float | None]) -> float:
    clean = [abs(v) for v in values if v is not None]
    return round(sum(clean) / len(clean), 6) if clean else 0.0


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def markdown_count_table(title: str, counter: Counter) -> list[str]:
    lines = [f"## {title}", "", "| value | count |", "|---|---:|"]
    if not counter:
        lines.append("| none | 0 |")
    else:
        for key, count in counter.most_common():
            lines.append(f"| {key or 'blank'} | {count} |")
    lines.append("")
    return lines


def main() -> int:
    args = parse_args()
    cutoff = china_now() - timedelta(days=args.lookback_days)
    sent_rows_all = [
        row for row in read_rows(normalize_path(args.sent_state)) if str(row.get("status", "")).strip().lower() == "sent"
    ]
    sent_rows = []
    for row in sent_rows_all:
        dt = parse_china_time(row.get("sent_at_china", ""))
        if dt and dt >= cutoff:
            sent_rows.append(row)

    followup_rows = read_rows(normalize_path(args.followup))
    followup_by_id = {str(row.get("event_id", "") or "").strip(): row for row in followup_rows}
    source_counts = Counter(str(row.get("event_type", "") or "unknown") for row in sent_rows)
    asset_counts = Counter(str(row.get("asset_symbol", "") or "unknown") for row in sent_rows)
    severity_counts = Counter(str(row.get("severity_tier", "") or "unknown") for row in sent_rows)
    first_hand_count = sum(1 for row in sent_rows if str(row.get("candidate_id", "")).startswith("watcher_"))
    mature_4h = []
    mature_24h = []
    for row in sent_rows:
        candidate_id = str(row.get("candidate_id", "") or "").strip()
        follow = followup_by_id.get(candidate_id, {})
        mature_4h.append(safe_float(follow.get("abnormal_vs_btc_4h")))
        mature_24h.append(safe_float(follow.get("abnormal_vs_btc_24h")))

    sent_count = len(sent_rows)
    source_count = len(source_counts)
    first_hand_share = round(first_hand_count / sent_count, 4) if sent_count else 0.0
    avg_abs_4h = avg_abs(mature_4h)
    avg_abs_24h = avg_abs(mature_24h)
    summary = {
        "generated_at_china": china_now().strftime("%Y-%m-%d %H:%M:%S UTC+8"),
        "lookback_days": args.lookback_days,
        "sent_count": sent_count,
        "source_count": source_count,
        "first_hand_count": first_hand_count,
        "first_hand_share": first_hand_share,
        "followup_4h_rows": sum(1 for value in mature_4h if value is not None),
        "followup_24h_rows": sum(1 for value in mature_24h if value is not None),
        "avg_abs_abnormal_vs_btc_4h": avg_abs_4h,
        "avg_abs_abnormal_vs_btc_24h": avg_abs_24h,
        "top_source": source_counts.most_common(1)[0][0] if source_counts else "",
        "top_source_share": round(source_counts.most_common(1)[0][1] / sent_count, 4) if sent_count and source_counts else 0.0,
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    lines = [
        "# v0.8 TG Product Metrics",
        "",
        "This report is for product operations. It does not provide trading advice.",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- lookback_days: {args.lookback_days}",
        f"- sent_count: {sent_count}",
        f"- first_hand_share: {pct(first_hand_share)}",
        f"- avg_abs_abnormal_vs_btc_4h: {pct(avg_abs_4h)}",
        f"- avg_abs_abnormal_vs_btc_24h: {pct(avg_abs_24h)}",
        f"- top_source_share: {pct(summary['top_source_share'])}",
        "",
        *markdown_count_table("By Event Type", source_counts),
        *markdown_count_table("By Asset", asset_counts),
        *markdown_count_table("By Severity", severity_counts),
        "## Read",
        "",
        "- Target first-hand share for the next 30 days: >50%.",
        "- Target realtime alert volume: 10-20 useful alerts/day after sources are expanded.",
        "- Target follow-up: enough 4h rows to judge source quality; 24h will lag naturally.",
        "- Do not interpret this as performance or trading advice.",
        "",
    ]
    output_path = normalize_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"sent_count={sent_count}")
    print(f"first_hand_share={first_hand_share}")
    print(f"wrote_report={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
