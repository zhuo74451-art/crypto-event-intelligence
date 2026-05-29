import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HORIZONS = ["1h", "4h", "24h", "72h"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize source/event usefulness from historical backtest rows.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_broad_200_price_backfill.csv"))
    parser.add_argument("--quality", default=str(ROOT / "results" / "v08_historical_replay_broad_200_quality_report.csv"))
    parser.add_argument("--by-event-type", default=str(ROOT / "results" / "v08_historical_source_usefulness_by_event_type.csv"))
    parser.add_argument("--by-source", default=str(ROOT / "results" / "v08_historical_source_usefulness_by_source.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_historical_source_usefulness_summary.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v08_historical_source_usefulness_report.md"))
    parser.add_argument("--min-move-24h", type=float, default=0.03)
    parser.add_argument("--min-move-72h", type=float, default=0.05)
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


def safe_float(value) -> float | None:
    try:
        raw = str(value or "").strip()
        if not raw:
            return None
        return float(raw)
    except Exception:
        return None


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def pct(value: float) -> str:
    return f"{value:.4f}"


def quality_by_event_id(rows: list[dict]) -> dict[str, dict]:
    output = {}
    for row in rows:
        event_id = str(row.get("event_id", "") or "").strip()
        if event_id:
            output[event_id] = row
    return output


def group_key(row: dict, dimension: str) -> str:
    if dimension == "source":
        return str(row.get("source", "") or "unknown").strip() or "unknown"
    return str(row.get("event_type", "") or "unknown").strip() or "unknown"


def source_status(row: dict) -> str:
    valid_24h = int(row.get("valid_24h_count", 0) or 0)
    valid_72h = int(row.get("valid_72h_count", 0) or 0)
    btc_eth_share = float(row.get("benchmark_asset_share", 0) or 0)
    hit_24h = float(row.get("abs_move_24h_hit_rate", 0) or 0)
    hit_72h = float(row.get("abs_move_72h_hit_rate", 0) or 0)
    if btc_eth_share >= 0.65 and int(row.get("sample_count", 0) or 0) >= 10:
        return "benchmark_polluted"
    if valid_24h < 10 and valid_72h < 10:
        return "insufficient_data"
    if hit_24h >= 0.35 or hit_72h >= 0.35:
        return "promising_for_expansion"
    if valid_24h >= 20 and hit_24h < 0.15:
        return "review_noise_or_digest_only"
    return "needs_more_replay"


def summarize(rows: list[dict], quality_rows: dict[str, dict], dimension: str, min_move_24h: float, min_move_72h: float) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        status = str(row.get("status", "") or "").strip().lower()
        if status not in {"ok", "partial"}:
            continue
        event_id = str(row.get("event_id", "") or "").strip()
        quality = quality_rows.get(event_id, {})
        if str(quality.get("quality_status", "") or "").strip().lower() == "fail":
            continue
        grouped[group_key(row, dimension)].append(row)

    output = []
    for key, items in grouped.items():
        result = {
            dimension: key,
            "sample_count": len(items),
            "btc_event_count": sum(1 for r in items if str(r.get("asset_symbol", "")).upper() == "BTC"),
            "eth_event_count": sum(1 for r in items if str(r.get("asset_symbol", "")).upper() == "ETH"),
            "benchmark_asset_share": 0.0,
        }
        result["benchmark_asset_share"] = round((result["btc_event_count"] + result["eth_event_count"]) / len(items), 4) if items else 0.0
        for horizon in HORIZONS:
            values = [safe_float(r.get(f"abnormal_vs_btc_{horizon}")) for r in items]
            values = [v for v in values if v is not None]
            asset_values = [safe_float(r.get(f"asset_return_{horizon}")) for r in items]
            asset_values = [v for v in asset_values if v is not None]
            result[f"valid_{horizon}_count"] = len(values)
            result[f"avg_abnormal_vs_btc_{horizon}"] = round(avg(values), 6)
            result[f"median_abnormal_vs_btc_{horizon}"] = round(median(values), 6)
            result[f"win_rate_vs_btc_{horizon}"] = round(sum(1 for v in values if v > 0) / len(values), 4) if values else 0.0
            threshold = min_move_72h if horizon == "72h" else min_move_24h
            result[f"abs_move_{horizon}_hit_rate"] = round(sum(1 for v in values if abs(v) >= threshold) / len(values), 4) if values else 0.0
            result[f"avg_asset_return_{horizon}"] = round(avg(asset_values), 6)
        result["historical_usefulness_status"] = source_status(result)
        output.append(result)
    output.sort(key=lambda r: (r["historical_usefulness_status"] != "promising_for_expansion", -int(r["sample_count"]), str(r.get(dimension, ""))))
    return output


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    if not rows:
        return ["| item | count |", "|---|---:|", "| none | 0 |"]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    backfill_rows = read_rows(normalize_path(args.backfill))
    qrows = quality_by_event_id(read_rows(normalize_path(args.quality)))
    by_event = summarize(backfill_rows, qrows, "event_type", args.min_move_24h, args.min_move_72h)
    by_source = summarize(backfill_rows, qrows, "source", args.min_move_24h, args.min_move_72h)

    event_fields = list(by_event[0].keys()) if by_event else ["event_type", "sample_count", "historical_usefulness_status"]
    source_fields = list(by_source[0].keys()) if by_source else ["source", "sample_count", "historical_usefulness_status"]
    write_rows(normalize_path(args.by_event_type), by_event, event_fields)
    write_rows(normalize_path(args.by_source), by_source, source_fields)

    summary = {
        "backfill": str(normalize_path(args.backfill)),
        "input_rows": len(backfill_rows),
        "event_type_rows": len(by_event),
        "source_rows": len(by_source),
        "promising_event_type_count": sum(1 for r in by_event if r.get("historical_usefulness_status") == "promising_for_expansion"),
        "promising_source_count": sum(1 for r in by_source if r.get("historical_usefulness_status") == "promising_for_expansion"),
        "benchmark_polluted_event_type_count": sum(1 for r in by_event if r.get("historical_usefulness_status") == "benchmark_polluted"),
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    event_preview = [
        {
            "event_type": row.get("event_type", ""),
            "samples": row.get("sample_count", 0),
            "24h_valid": row.get("valid_24h_count", 0),
            "24h_avg": row.get("avg_abnormal_vs_btc_24h", 0),
            "24h_hit": row.get("abs_move_24h_hit_rate", 0),
            "status": row.get("historical_usefulness_status", ""),
        }
        for row in by_event[:20]
    ]
    source_preview = [
        {
            "source": row.get("source", ""),
            "samples": row.get("sample_count", 0),
            "24h_valid": row.get("valid_24h_count", 0),
            "24h_avg": row.get("avg_abnormal_vs_btc_24h", 0),
            "24h_hit": row.get("abs_move_24h_hit_rate", 0),
            "status": row.get("historical_usefulness_status", ""),
        }
        for row in by_source[:20]
    ]
    lines = [
        "# v0.8 Historical Source Usefulness From Backtest",
        "",
        f"- backfill: `{summary['backfill']}`",
        f"- input_rows: {summary['input_rows']}",
        f"- event_type_rows: {summary['event_type_rows']}",
        f"- source_rows: {summary['source_rows']}",
        "",
        "## By Event Type",
        "",
        *markdown_table(event_preview, ["event_type", "samples", "24h_valid", "24h_avg", "24h_hit", "status"]),
        "",
        "## By Source",
        "",
        *markdown_table(source_preview, ["source", "samples", "24h_valid", "24h_avg", "24h_hit", "status"]),
        "",
        "## Interpretation Rules",
        "",
        "- `promising_for_expansion`: historical rows show enough follow-up movement to justify more samples/source work.",
        "- `benchmark_polluted`: BTC/ETH benchmark assets dominate; do not use this bucket for abnormal-vs-BTC conclusions without a different benchmark.",
        "- `review_noise_or_digest_only`: enough samples but weak post-event movement; lower priority or move to digest.",
        "- `insufficient_data`: do not make product conclusions yet.",
        "",
        "This report is research QA only and does not provide trading instructions.",
        "",
    ]
    normalize_path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(f"event_type_rows={len(by_event)}")
    print(f"source_rows={len(by_source)}")
    print(f"wrote_report={normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
