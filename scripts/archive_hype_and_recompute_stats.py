import argparse
import csv
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
HORIZONS = ["1h", "4h", "24h", "72h"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive HYPE whale burst contamination and recompute event-group stats.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_200_price_backfill.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "backtest_v08_alt_history_clean.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v13_post_hype_removal_summary.csv"))
    parser.add_argument("--group-stats", default=str(ROOT / "results" / "v13_post_hype_removal_group_stats.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v13_post_hype_removal_report.md"))
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


def safe_float(value) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def event_group(row: dict) -> str:
    return str(row.get("event_subtype") or row.get("event_type") or "unknown").strip() or "unknown"


def archive_reason(row: dict) -> str:
    asset = str(row.get("asset_symbol") or "").upper()
    subtype = str(row.get("event_subtype") or row.get("event_type") or "")
    if asset == "HYPE" and subtype == "whale_wallet_position":
        return "single_asset_burst_contamination"
    return ""


def route_status(stats: dict) -> str:
    valid_24h = int(stats.get("computed_24h_count", 0) or 0)
    avg_24h = float(stats.get("avg_abnormal_vs_btc_24h", 0) or 0)
    win_24h = float(stats.get("win_rate_vs_btc_24h", 0) or 0)
    group = str(stats.get("event_group") or "")
    if valid_24h >= 30 and avg_24h >= 0.01 and win_24h >= 0.55:
        return "collect_more_after_cleaning"
    if group in {"exploit_or_theft", "etf_or_fund_flow"} and valid_24h >= 20:
        return "digest_only"
    if valid_24h < 10:
        return "insufficient_sample"
    return "collect_more"


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.backfill))
    output = []
    for row in rows:
        item = dict(row)
        reason = archive_reason(item)
        item["is_archived"] = "true" if reason else "false"
        item["archive_reason"] = reason
        output.append(item)
    fields = list(output[0].keys()) if output else ["event_id", "is_archived", "archive_reason"]
    write_rows(normalize_path(args.output), output, fields)

    clean = [row for row in output if row.get("is_archived") != "true"]
    groups = defaultdict(list)
    for row in clean:
        groups[event_group(row)].append(row)
    group_rows = []
    for group, items in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        stats = {"generated_at_china": china_stamp(), "event_group": group, "sample_count": len(items)}
        for horizon in HORIZONS:
            values = [safe_float(row.get(f"abnormal_vs_btc_{horizon}")) for row in items]
            values = [value for value in values if value is not None]
            stats[f"computed_{horizon}_count"] = len(values)
            stats[f"avg_abnormal_vs_btc_{horizon}"] = round(avg(values), 6)
            stats[f"win_rate_vs_btc_{horizon}"] = round(sum(1 for value in values if value > 0) / len(values), 4) if values else 0.0
        stats["post_archive_route_status"] = route_status(stats)
        group_rows.append(stats)
    write_rows(normalize_path(args.group_stats), group_rows, list(group_rows[0].keys()) if group_rows else ["event_group"])

    status_counts = defaultdict(int)
    for row in group_rows:
        status_counts[row["post_archive_route_status"]] += 1
    archived_count = sum(1 for row in output if row.get("is_archived") == "true")
    summary = {
        "generated_at_china": china_stamp(),
        "status": "pass",
        "input_rows": len(rows),
        "archived_rows": archived_count,
        "clean_rows": len(clean),
        "whale_wallet_position_remaining": sum(1 for row in clean if event_group(row) == "whale_wallet_position"),
        "boost_count": 0,
        "digest_only_count": status_counts.get("digest_only", 0),
        "collect_more_count": status_counts.get("collect_more", 0) + status_counts.get("collect_more_after_cleaning", 0),
        "insufficient_sample_count": status_counts.get("insufficient_sample", 0),
        "output": str(normalize_path(args.output)),
        "group_stats": str(normalize_path(args.group_stats)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    lines = [
        "# v13 Post-HYPE Removal Report",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- input_rows: {summary['input_rows']}",
        f"- archived_rows: {summary['archived_rows']}",
        f"- clean_rows: {summary['clean_rows']}",
        f"- whale_wallet_position_remaining: {summary['whale_wallet_position_remaining']}",
        f"- boost_count: {summary['boost_count']}",
        "",
        "| event_group | samples | avg_24h | win_rate_24h | route_status |",
        "|---|---:|---:|---:|---|",
    ]
    for row in group_rows:
        lines.append(
            f"| {row['event_group']} | {row['sample_count']} | {row['avg_abnormal_vs_btc_24h']} | "
            f"{row['win_rate_vs_btc_24h']} | {row['post_archive_route_status']} |"
        )
    lines.append("")
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"input_rows={len(rows)}")
    print(f"archived_rows={archived_count}")
    print(f"clean_rows={len(clean)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
