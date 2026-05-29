import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze whale_position asset concentration and burst contamination.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_200_price_backfill.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v13_whale_asset_contamination_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v13_whale_asset_contamination_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v13_whale_asset_contamination_report.md"))
    parser.add_argument("--asset-share-threshold", type=float, default=0.60)
    parser.add_argument("--short-window-days", type=float, default=7.0)
    parser.add_argument("--burst-window-days", type=int, default=3)
    parser.add_argument("--burst-share-threshold", type=float, default=0.80)
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


def parse_utc(value: str) -> datetime | None:
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


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def max_window_share(times: list[datetime], window_days: int) -> float:
    if not times:
        return 0.0
    ordered = sorted(times)
    best = 0
    right = 0
    delta = timedelta(days=window_days)
    for left, start in enumerate(ordered):
        while right < len(ordered) and ordered[right] - start <= delta:
            right += 1
        best = max(best, right - left)
    return best / len(ordered)


def main() -> int:
    args = parse_args()
    rows = [
        row
        for row in read_rows(normalize_path(args.backfill))
        if (row.get("event_type") == "whale_position" or row.get("event_subtype") == "whale_wallet_position")
        and str(row.get("status") or "").lower() in {"ok", "partial"}
    ]
    total = len(rows)
    grouped = defaultdict(list)
    for row in rows:
        asset = str(row.get("asset_symbol") or "UNKNOWN").upper()
        grouped[asset].append(row)

    output = []
    for asset, items in grouped.items():
        times = [parse_utc(row.get("event_time_utc") or row.get("event_time")) for row in items]
        times = [item for item in times if item is not None]
        returns_24h = [safe_float(row.get("abnormal_vs_btc_24h")) for row in items]
        returns_24h = [item for item in returns_24h if item is not None]
        sources = Counter(str(row.get("source") or row.get("source_type") or "unknown") for row in items)
        timespan_days = 0.0
        if len(times) >= 2:
            timespan_days = (max(times) - min(times)).total_seconds() / 86400
        asset_share = len(items) / total if total else 0.0
        burst_share = max_window_share(times, args.burst_window_days)
        win_rate = sum(1 for value in returns_24h if value > 0) / len(returns_24h) if returns_24h else 0.0
        flags = []
        if asset_share > args.asset_share_threshold:
            flags.append("single_asset_concentration")
        if timespan_days and timespan_days < args.short_window_days:
            flags.append("short_time_span")
        if burst_share >= args.burst_share_threshold:
            flags.append("burst_window_concentration")
        if sources and sources.most_common(1)[0][1] / len(items) > 0.6:
            flags.append("single_source_dominated")
        if "single_asset_concentration" in flags and ("short_time_span" in flags or "burst_window_concentration" in flags):
            recommendation = "downgrade_asset_whale_to_digest"
        elif flags:
            recommendation = "collect_more_with_contamination_flag"
        else:
            recommendation = "eligible_for_future_validation"
        output.append(
            {
                "generated_at_china": china_stamp(),
                "asset_symbol": asset,
                "event_count": len(items),
                "asset_share": round(asset_share, 4),
                "unique_sources": len(sources),
                "top_source": sources.most_common(1)[0][0] if sources else "",
                "top_source_share": round(sources.most_common(1)[0][1] / len(items), 4) if sources else 0.0,
                "timespan_days": round(timespan_days, 4),
                "burst_window_days": args.burst_window_days,
                "burst_window_share": round(burst_share, 4),
                "avg_abnormal_vs_btc_24h": round(avg(returns_24h), 6),
                "win_rate_vs_btc_24h": round(win_rate, 4),
                "contamination_flags": ",".join(flags),
                "recommendation": recommendation,
            }
        )
    output.sort(key=lambda row: (-row["event_count"], row["asset_symbol"]))
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["asset_symbol"])

    summary = {
        "generated_at_china": china_stamp(),
        "status": "fail" if any(row["recommendation"] == "downgrade_asset_whale_to_digest" for row in output) else "pass",
        "whale_rows": total,
        "asset_groups": len(output),
        "downgrade_asset_count": sum(1 for row in output if row["recommendation"] == "downgrade_asset_whale_to_digest"),
        "flagged_asset_count": sum(1 for row in output if row["contamination_flags"]),
        "top_asset": output[0]["asset_symbol"] if output else "",
        "top_asset_share": output[0]["asset_share"] if output else 0.0,
        "output": str(normalize_path(args.output)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    lines = [
        "# v13 Whale Asset Contamination Report",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- whale_rows: {summary['whale_rows']}",
        f"- asset_groups: {summary['asset_groups']}",
        f"- status: {summary['status']}",
        "",
        "| asset | count | share | days | burst_3d_share | top_source_share | avg_24h | win_rate_24h | flags | recommendation |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in output:
        lines.append(
            f"| {row['asset_symbol']} | {row['event_count']} | {row['asset_share']} | {row['timespan_days']} | "
            f"{row['burst_window_share']} | {row['top_source_share']} | {row['avg_abnormal_vs_btc_24h']} | "
            f"{row['win_rate_vs_btc_24h']} | {row['contamination_flags']} | {row['recommendation']} |"
        )
    lines.append("")
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"whale_rows={total}")
    print(f"asset_groups={len(output)}")
    print(f"status={summary['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
