import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate whether whale-position historical performance is contaminated.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_200_price_backfill.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v12_whale_position_contamination_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v12_whale_position_contamination_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v12_whale_position_contamination_report.md"))
    parser.add_argument("--max-hype-ratio", type=float, default=0.15)
    parser.add_argument("--max-single-asset-ratio", type=float, default=0.30)
    parser.add_argument("--min-unique-assets", type=int, default=10)
    parser.add_argument("--min-timespan-days", type=float, default=60.0)
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


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.backfill))
    whale_rows = [
        row for row in rows
        if str(row.get("event_type") or "").strip() == "whale_position"
        or str(row.get("event_subtype") or "").strip() in {"whale_wallet_position", "whale_position_static_large", "whale_position_size_change"}
    ]
    assets = [str(row.get("asset_symbol") or "").strip().upper() or "UNKNOWN" for row in whale_rows]
    counts = Counter(assets)
    total = len(whale_rows)
    unique_assets = len([asset for asset in counts if asset != "UNKNOWN"])
    hype_count = counts.get("HYPE", 0)
    max_asset, max_count = ("", 0)
    if counts:
        max_asset, max_count = counts.most_common(1)[0]
    hype_ratio = hype_count / total if total else 0.0
    max_single_asset_ratio = max_count / total if total else 0.0
    dts = [parse_dt(row.get("event_time_utc") or row.get("event_time")) for row in whale_rows]
    dts = [dt for dt in dts if dt]
    timespan_days = round((max(dts) - min(dts)).total_seconds() / 86400, 2) if len(dts) >= 2 else 0.0
    flags = []
    if hype_ratio > args.max_hype_ratio:
        flags.append("hype_contamination")
    if max_single_asset_ratio > args.max_single_asset_ratio:
        flags.append("single_asset_concentration")
    if unique_assets < args.min_unique_assets:
        flags.append("low_asset_diversity")
    if timespan_days < args.min_timespan_days:
        flags.append("short_time_span")
    status = "fail" if flags else "pass"

    asset_rows = [
        {
            "asset_symbol": asset,
            "sample_count": count,
            "sample_ratio": round(count / total, 4) if total else 0.0,
        }
        for asset, count in counts.most_common()
    ]
    write_rows(normalize_path(args.output), asset_rows, ["asset_symbol", "sample_count", "sample_ratio"])
    summary = {
        "status": status,
        "generated_at_china": china_stamp(),
        "backfill_rows": len(rows),
        "whale_rows": total,
        "unique_assets": unique_assets,
        "hype_count": hype_count,
        "hype_ratio": round(hype_ratio, 4),
        "max_asset": max_asset,
        "max_single_asset_count": max_count,
        "max_single_asset_ratio": round(max_single_asset_ratio, 4),
        "timespan_days": timespan_days,
        "quality_flags": ",".join(flags),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    lines = [
        "# v12 Whale Position Contamination Report",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- status: {status}",
        f"- whale_rows: {total}",
        f"- unique_assets: {unique_assets}",
        f"- hype_ratio: {summary['hype_ratio']}",
        f"- max_single_asset: {max_asset} / {summary['max_single_asset_ratio']}",
        f"- timespan_days: {timespan_days}",
        f"- quality_flags: {summary['quality_flags']}",
        "",
        "If this report fails, whale-position boost must be disabled or downgraded until contamination is resolved.",
        "",
    ]
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"status={status}")
    print(f"whale_rows={total}")
    print(f"quality_flags={summary['quality_flags']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
