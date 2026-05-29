import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build TG source usefulness report from sent alerts and follow-up data.")
    parser.add_argument("--sent-state", default=str(ROOT / "data" / "tg_live_sent_state.csv"))
    parser.add_argument("--followup", default=str(ROOT / "results" / "v08_tg_alert_followup_backfill.csv"))
    parser.add_argument("--quality", default=str(ROOT / "results" / "v08_tg_alert_followup_quality_report.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v08_tg_source_usefulness_report.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_tg_source_usefulness_summary.csv"))
    parser.add_argument("--by-source", default=str(ROOT / "results" / "v08_tg_source_usefulness_by_source.csv"))
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--min-move-4h", type=float, default=0.02)
    parser.add_argument("--min-move-24h", type=float, default=0.03)
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
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"]:
        try:
            return datetime.strptime(raw[:19], fmt).replace(tzinfo=timezone(timedelta(hours=8)))
        except ValueError:
            continue
    return None


def safe_float(value) -> float | None:
    try:
        raw = str(value or "").strip()
        if raw == "":
            return None
        return float(raw)
    except Exception:
        return None


def pct(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value * 100:.2f}%"


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def source_key(row: dict) -> str:
    event_type = str(row.get("event_type", "") or "").strip()
    if event_type:
        return event_type
    draft_id = str(row.get("draft_id", "") or "").strip().lower()
    candidate_id = str(row.get("candidate_id", "") or "").strip().lower()
    if "funding" in draft_id or "funding" in candidate_id:
        return "funding_rate"
    if "watcher" in draft_id or "watcher" in candidate_id:
        return "unknown_watcher"
    return "unknown"


def latest_by_key(rows: list[dict], key_field: str) -> dict[str, dict]:
    output = {}
    for row in rows:
        key = str(row.get(key_field, "") or "").strip()
        if key:
            output[key] = row
    return output


def usefulness_status(row: dict) -> str:
    sent = int(row["sent_count"])
    if sent == 0:
        return "no_data"
    if int(row["followup_24h_rows"]) >= 3 and float(row["move_24h_hit_rate"]) < 0.2:
        return "review_noise"
    if float(row["move_4h_hit_rate"]) >= 0.4 or float(row["move_24h_hit_rate"]) >= 0.4:
        return "promising"
    if sent >= 5 and int(row["followup_4h_rows"]) == 0:
        return "needs_instrumentation"
    return "insufficient_data"


def followup_metric(row: dict, horizon: str) -> float | None:
    event_type = str(row.get("event_type", "") or "").strip()
    asset = str(row.get("asset_symbol", "") or "").strip().upper()
    if event_type in {"stablecoin_flow", "cex_netflow"} and asset == "BTC":
        return safe_float(row.get(f"asset_return_{horizon}"))
    return safe_float(row.get(f"abnormal_vs_btc_{horizon}"))


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    if not rows:
        return ["| item | count |", "|---|---:|", "| none | 0 |"]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    cutoff = china_now() - timedelta(days=args.lookback_days)

    sent_rows_all = [
        row
        for row in read_rows(normalize_path(args.sent_state))
        if str(row.get("status", "") or "").strip().lower() == "sent"
    ]
    sent_rows = []
    for row in sent_rows_all:
        sent_at = parse_china_time(str(row.get("sent_at_china", "") or ""))
        if sent_at and sent_at >= cutoff:
            sent_rows.append(row)

    followup_rows = latest_by_key(read_rows(normalize_path(args.followup)), "event_id")
    quality_rows = latest_by_key(read_rows(normalize_path(args.quality)), "event_id")

    grouped: dict[str, dict] = {}
    for row in sent_rows:
        key = source_key(row)
        item = grouped.setdefault(
            key,
            {
                "source": key,
                "sent_count": 0,
                "dry_run_excluded": 0,
                "followup_4h_rows": 0,
                "followup_24h_rows": 0,
                "move_4h_hit_count": 0,
                "move_24h_hit_count": 0,
                "quality_pass_count": 0,
                "quality_warning_count": 0,
                "quality_fail_count": 0,
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "unknown_asset_count": 0,
            },
        )
        item["sent_count"] += 1
        tier = str(row.get("severity_tier", "") or "unknown").strip().lower()
        if tier == "critical":
            item["critical_count"] += 1
        elif tier == "high":
            item["high_count"] += 1
        elif tier == "medium":
            item["medium_count"] += 1
        if not str(row.get("asset_symbol", "") or "").strip():
            item["unknown_asset_count"] += 1

        candidate_id = str(row.get("candidate_id", "") or "").strip()
        followup = followup_rows.get(candidate_id, {})
        abnormal_4h = followup_metric(followup, "4h")
        abnormal_24h = followup_metric(followup, "24h")
        if abnormal_4h is not None:
            item["followup_4h_rows"] += 1
            if abs(abnormal_4h) >= args.min_move_4h:
                item["move_4h_hit_count"] += 1
        if abnormal_24h is not None:
            item["followup_24h_rows"] += 1
            if abs(abnormal_24h) >= args.min_move_24h:
                item["move_24h_hit_count"] += 1

        quality = quality_rows.get(candidate_id, {})
        quality_status = str(quality.get("quality_status", "") or "").strip().lower()
        if quality_status == "pass":
            item["quality_pass_count"] += 1
        elif quality_status == "warning":
            item["quality_warning_count"] += 1
        elif quality_status == "fail":
            item["quality_fail_count"] += 1

    source_rows = []
    for item in grouped.values():
        item["move_4h_hit_rate"] = rate(int(item["move_4h_hit_count"]), int(item["followup_4h_rows"]))
        item["move_24h_hit_rate"] = rate(int(item["move_24h_hit_count"]), int(item["followup_24h_rows"]))
        item["usefulness_status"] = usefulness_status(item)
        source_rows.append(item)
    source_rows.sort(key=lambda row: (row["usefulness_status"] != "promising", -int(row["sent_count"]), row["source"]))

    status_counts = Counter(row["usefulness_status"] for row in source_rows)
    total_sent = sum(int(row["sent_count"]) for row in source_rows)
    total_4h = sum(int(row["followup_4h_rows"]) for row in source_rows)
    total_24h = sum(int(row["followup_24h_rows"]) for row in source_rows)
    summary = {
        "generated_at_china": china_now().strftime("%Y-%m-%d %H:%M:%S UTC+8"),
        "lookback_days": args.lookback_days,
        "sent_count": total_sent,
        "source_count": len(source_rows),
        "followup_4h_rows": total_4h,
        "followup_24h_rows": total_24h,
        "promising_source_count": status_counts.get("promising", 0),
        "review_noise_source_count": status_counts.get("review_noise", 0),
        "needs_instrumentation_source_count": status_counts.get("needs_instrumentation", 0),
        "insufficient_data_source_count": status_counts.get("insufficient_data", 0),
        "top_source": source_rows[0]["source"] if source_rows else "",
        "top_source_sent_count": source_rows[0]["sent_count"] if source_rows else 0,
        "status": "pass",
    }

    fieldnames = [
        "source",
        "sent_count",
        "followup_4h_rows",
        "move_4h_hit_count",
        "move_4h_hit_rate",
        "followup_24h_rows",
        "move_24h_hit_count",
        "move_24h_hit_rate",
        "quality_pass_count",
        "quality_warning_count",
        "quality_fail_count",
        "critical_count",
        "high_count",
        "medium_count",
        "unknown_asset_count",
        "usefulness_status",
    ]
    write_rows(normalize_path(args.by_source), source_rows, fieldnames)
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    report_rows = []
    for row in source_rows:
        report_rows.append(
            {
                "source": row["source"],
                "sent": row["sent_count"],
                "4h_hit": f'{row["move_4h_hit_count"]}/{row["followup_4h_rows"]}',
                "24h_hit": f'{row["move_24h_hit_count"]}/{row["followup_24h_rows"]}',
                "status": row["usefulness_status"],
            }
        )

    lines = [
        "# v0.8 TG Source Usefulness Report",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- lookback_days: {args.lookback_days}",
        f"- sent_count: {total_sent}",
        f"- followup_4h_rows: {total_4h}",
        f"- followup_24h_rows: {total_24h}",
        "",
        "## By Source",
        "",
        *markdown_table(report_rows, ["source", "sent", "4h_hit", "24h_hit", "status"]),
        "",
        "## Interpretation",
        "",
        "- `promising`: post-alert movement is starting to support keeping this source.",
        "- `review_noise`: enough negative/no-move evidence to consider lowering priority, raising thresholds, or moving to digest-only.",
        "- `needs_instrumentation`: messages were sent but follow-up coverage is missing.",
        "- `insufficient_data`: not enough observations yet.",
        "- For stablecoin/CEX stablecoin-flow proxy events, movement hit-rate uses BTC's own post-alert return instead of abnormal-vs-BTC.",
        "",
        "## Product Rule",
        "",
        "This report is for alert-quality operations only. It does not provide trading advice or execution signals.",
        "",
    ]
    output_path = normalize_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"sent_count={total_sent}")
    print(f"source_count={len(source_rows)}")
    print(f"wrote_report={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
