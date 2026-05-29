import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize live TG alert performance and feedback.")
    parser.add_argument("--sent-state", default=str(ROOT / "data" / "tg_live_sent_state.csv"))
    parser.add_argument("--feedback", default=str(ROOT / "data" / "tg_alert_feedback.csv"))
    parser.add_argument("--quality-summary", default=str(ROOT / "results" / "v07_tg_live_quality_gate_summary.csv"))
    parser.add_argument("--rate-summary", default=str(ROOT / "results" / "v08_tg_rate_limit_summary.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v08_tg_live_performance_report.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_tg_live_performance_summary.csv"))
    parser.add_argument("--date", default="", help="China date YYYY-MM-DD. Default: today.")
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def today_china() -> str:
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")


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


def rows_on_date(rows: list[dict], field: str, date_text: str) -> list[dict]:
    return [row for row in rows if str(row.get(field, "") or "").startswith(date_text)]


def sent_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if str(row.get("status", "")).strip().lower() == "sent"]


def counter_table(counter: Counter) -> list[str]:
    if not counter:
        return ["| item | count |", "|---|---:|", "| none | 0 |"]
    lines = ["| item | count |", "|---|---:|"]
    for key, count in counter.most_common():
        lines.append(f"| {key or 'unknown'} | {count} |")
    return lines


def latest_summary(rows: list[dict]) -> dict:
    return rows[-1] if rows else {}


def main() -> int:
    args = parse_args()
    date_text = args.date.strip() or today_china()
    sent = rows_on_date(sent_rows(read_rows(normalize_path(args.sent_state))), "sent_at_china", date_text)
    feedback = rows_on_date(read_rows(normalize_path(args.feedback)), "collected_at_china", date_text)
    quality = latest_summary(read_rows(normalize_path(args.quality_summary)))
    rate = latest_summary(read_rows(normalize_path(args.rate_summary)))

    event_counts = Counter(str(row.get("event_type", "") or "unknown") for row in sent)
    asset_counts = Counter(str(row.get("asset_symbol", "") or "unknown") for row in sent)
    severity_counts = Counter(str(row.get("severity_tier", "") or "unknown") for row in sent)
    feedback_counts = Counter(str(row.get("feedback_value", "") or "unknown") for row in feedback)

    summary = {
        "date_china": date_text,
        "sent_count": len(sent),
        "feedback_count": len(feedback),
        "positive_feedback_count": feedback_counts.get("positive", 0),
        "negative_feedback_count": feedback_counts.get("negative", 0),
        "comment_feedback_count": feedback_counts.get("comment", 0),
        "top_event_type": event_counts.most_common(1)[0][0] if event_counts else "",
        "top_event_type_count": event_counts.most_common(1)[0][1] if event_counts else 0,
        "top_asset": asset_counts.most_common(1)[0][0] if asset_counts else "",
        "top_asset_count": asset_counts.most_common(1)[0][1] if asset_counts else 0,
        "quality_pass_count": quality.get("quality_pass_count", ""),
        "quality_warning_count": quality.get("quality_warning_count", ""),
        "quality_fail_count": quality.get("quality_fail_count", ""),
        "rate_pass_count": rate.get("rate_pass_count", ""),
        "rate_blocked_count": rate.get("rate_blocked_count", ""),
        "daily_send_limit": rate.get("daily_send_limit", ""),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    lines = [
        "# v0.8 TG Live Performance Report",
        "",
        f"- date_china: {date_text}",
        f"- sent_count: {len(sent)}",
        f"- feedback_count: {len(feedback)}",
        f"- positive_feedback_count: {feedback_counts.get('positive', 0)}",
        f"- negative_feedback_count: {feedback_counts.get('negative', 0)}",
        "",
        "## Sent By Event Type",
        "",
        *counter_table(event_counts),
        "",
        "## Sent By Asset",
        "",
        *counter_table(asset_counts),
        "",
        "## Sent By Severity",
        "",
        *counter_table(severity_counts),
        "",
        "## Feedback",
        "",
        *counter_table(feedback_counts),
        "",
        "## Latest Gates",
        "",
        "| gate | pass | warning/block | fail |",
        "|---|---:|---:|---:|",
        f"| quality | {quality.get('quality_pass_count', '')} | {quality.get('quality_warning_count', '')} | {quality.get('quality_fail_count', '')} |",
        f"| rate_limit | {rate.get('rate_pass_count', '')} | {rate.get('rate_blocked_count', '')} |  |",
        "",
        "## Notes",
        "",
        "- Feedback is based on Telegram replies/reactions captured by the bot.",
        "- Price follow-up tracking is not included yet; that is the next reporting layer.",
        "- This report is for alert-quality operations only and is not trading advice.",
        "",
    ]
    output_path = normalize_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"sent_count={len(sent)}")
    print(f"feedback_count={len(feedback)}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
