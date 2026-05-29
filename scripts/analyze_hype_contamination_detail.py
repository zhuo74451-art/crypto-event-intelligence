import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze HYPE concentration inside whale_position historical samples.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_200_price_backfill.csv"))
    parser.add_argument("--candidates", default=str(ROOT / "data" / "event_candidates_real_2000_older_review.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v13_hype_contamination_detail.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v13_hype_contamination_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v13_hype_contamination_report.md"))
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


def parse_dt(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def safe_float(value) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def main() -> int:
    args = parse_args()
    backfill = read_rows(normalize_path(args.backfill))
    candidates = {str(row.get("candidate_id") or "").strip(): row for row in read_rows(normalize_path(args.candidates))}
    hype_rows = []
    for row in backfill:
        if str(row.get("asset_symbol") or "").upper() != "HYPE":
            continue
        if str(row.get("event_subtype") or row.get("event_type") or "") not in {"whale_wallet_position", "whale_position"}:
            continue
        candidate = candidates.get(str(row.get("event_id") or "").strip(), {})
        dt = parse_dt(row.get("event_time_utc") or row.get("event_time"))
        ret24 = safe_float(row.get("abnormal_vs_btc_24h"))
        hype_rows.append(
            {
                "event_id": row.get("event_id", ""),
                "event_time_utc": row.get("event_time_utc", ""),
                "event_date_utc": dt.date().isoformat() if dt else "",
                "source": row.get("source", ""),
                "candidate_source": candidate.get("source", ""),
                "author": candidate.get("author", ""),
                "source_id": f"{candidate.get('source', row.get('source', ''))}:{candidate.get('author', '')}".strip(":").lower(),
                "abnormal_vs_btc_24h": "" if ret24 is None else round(ret24, 6),
                "title": row.get("title", ""),
            }
        )
    write_rows(normalize_path(args.output), hype_rows, ["event_id", "event_time_utc", "event_date_utc", "source", "candidate_source", "author", "source_id", "abnormal_vs_btc_24h", "title"])

    dates = [row["event_date_utc"] for row in hype_rows if row["event_date_utc"]]
    daily_counts = Counter(dates)
    source_counts = Counter(row["source_id"] for row in hype_rows)
    returns = [safe_float(row.get("abnormal_vs_btc_24h")) for row in hype_rows]
    returns = [value for value in returns if value is not None]
    total = len(hype_rows)
    max_daily = max(daily_counts.values()) if daily_counts else 0
    unique_days = len(daily_counts)
    top_source_count = source_counts.most_common(1)[0][1] if source_counts else 0
    top3_source_count = sum(count for _, count in source_counts.most_common(3))
    if total and max_daily / total > 0.5:
        time_pattern = "burst"
    elif unique_days < 7:
        time_pattern = "short_window"
    else:
        time_pattern = "distributed"
    if total and top_source_count / total > 0.6:
        source_pattern = "single_source_dominated"
    elif total and top3_source_count / total > 0.8:
        source_pattern = "few_sources_dominated"
    else:
        source_pattern = "diverse_sources"
    mean_return = sum(returns) / len(returns) if returns else 0.0
    median_return = median(returns)
    if returns and abs(mean_return) > abs(median_return) * 1.5 and abs(mean_return) > 0.02:
        return_pattern = "outlier_driven"
    else:
        return_pattern = "consistent"
    action = "archive_or_digest_only" if time_pattern in {"burst", "short_window"} or source_pattern != "diverse_sources" else "continue_collect"
    summary = {
        "status": "warning" if action == "archive_or_digest_only" else "pass",
        "generated_at_china": china_stamp(),
        "hype_whale_rows": total,
        "unique_days": unique_days,
        "max_daily_count": max_daily,
        "max_daily_ratio": round(max_daily / total, 4) if total else 0.0,
        "top_source_count": top_source_count,
        "top_source_ratio": round(top_source_count / total, 4) if total else 0.0,
        "top3_source_ratio": round(top3_source_count / total, 4) if total else 0.0,
        "mean_abnormal_vs_btc_24h": round(mean_return, 6),
        "median_abnormal_vs_btc_24h": round(median_return, 6),
        "time_pattern": time_pattern,
        "source_pattern": source_pattern,
        "return_pattern": return_pattern,
        "recommended_action": action,
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    lines = [
        "# v13 HYPE Contamination Detail",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- hype_whale_rows: {total}",
        f"- unique_days: {unique_days}",
        f"- time_pattern: {time_pattern}",
        f"- source_pattern: {source_pattern}",
        f"- return_pattern: {return_pattern}",
        f"- recommended_action: {action}",
        "",
        "## Daily Counts",
        "",
        "| date | count |",
        "|---|---:|",
    ]
    for date, count in daily_counts.most_common(20):
        lines.append(f"| {date} | {count} |")
    lines.extend(["", "## Top Sources", "", "| source_id | count |", "|---|---:|"])
    for source, count in source_counts.most_common(10):
        lines.append(f"| {source} | {count} |")
    normalize_path(args.markdown_output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"hype_whale_rows={total}")
    print(f"time_pattern={time_pattern}")
    print(f"recommended_action={action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
