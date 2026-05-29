import argparse
import csv
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
HORIZONS = ["1h", "4h", "24h", "72h"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build event type performance matrix from TG outcomes.")
    parser.add_argument("--outcomes", default=str(ROOT / "data" / "tg_alert_outcomes.csv"))
    parser.add_argument("--historical-backfill", default=str(ROOT / "results" / "v08_historical_replay_broad_200_price_backfill.csv"))
    parser.add_argument("--historical-quality", default=str(ROOT / "results" / "v08_historical_replay_broad_200_quality_report.csv"))
    parser.add_argument("--include-historical", default="true")
    parser.add_argument("--output", default=str(ROOT / "results" / "event_type_performance_matrix.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "event_type_performance_matrix_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "event_type_performance_matrix.md"))
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
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def asset_tier(asset: str) -> str:
    asset = str(asset or "").upper()
    if asset in {"BTC", "ETH"}:
        return "benchmark_asset"
    if asset in {"BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "LINK"}:
        return "large_cap_alt"
    if asset:
        return "other_alt"
    return "unknown"


def row_key(row: dict) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("event_type") or "unknown").strip() or "unknown",
        str(row.get("event_subtype") or "unknown").strip() or "unknown",
        str(row.get("source_type") or "unknown").strip() or "unknown",
        asset_tier(row.get("asset_symbol", "")),
        str(row.get("btc_regime_trend_14d") or "unknown").strip() or "unknown",
    )


def abnormal_value(row: dict, horizon: str) -> float | None:
    for field in (f"abnormal_primary_{horizon}", f"abnormal_vs_btc_{horizon}"):
        value = safe_float(row.get(field))
        if value is not None:
            return value
    return None


def quality_fail_ids(rows: list[dict]) -> set[str]:
    output = set()
    for row in rows:
        event_id = str(row.get("event_id") or row.get("alert_id") or "").strip()
        if event_id and str(row.get("quality_status") or "").strip().lower() == "fail":
            output.add(event_id)
    return output


def normalized_live_rows(rows: list[dict]) -> list[dict]:
    output = []
    for row in rows:
        if str(row.get("quality_status") or "").lower() == "fail":
            continue
        item = dict(row)
        item["event_subtype"] = item.get("event_subtype") or item.get("event_type") or "unknown"
        item["source_type"] = item.get("source_type") or "live_unknown"
        item["sample_origin"] = "live_tg"
        output.append(item)
    return output


def normalized_historical_rows(backfill_rows: list[dict], failed_ids: set[str]) -> list[dict]:
    output = []
    for row in backfill_rows:
        event_id = str(row.get("event_id") or "").strip()
        if event_id in failed_ids:
            continue
        if str(row.get("status") or "").strip().lower() not in {"ok", "partial"}:
            continue
        item = dict(row)
        item["event_subtype"] = item.get("event_subtype") or item.get("event_type") or "unknown"
        item["source_type"] = item.get("source_type") or item.get("source") or "historical_unknown"
        item["btc_regime_trend_14d"] = item.get("btc_regime_trend_14d") or "historical_unknown"
        item["sample_origin"] = "historical_replay"
        output.append(item)
    return output


def status_for(row: dict) -> str:
    max_count = max(int(row.get(f"computed_{h}_count", 0) or 0) for h in HORIZONS)
    valid_24h = int(row.get("computed_24h_count", 0) or 0)
    if max_count < 10:
        return "insufficient_sample"
    if valid_24h < 10:
        return "short_horizon_only"
    avg_24h = abs(safe_float(row.get("avg_abnormal_primary_24h")) or 0.0)
    if avg_24h >= 0.01:
        return "promising_needs_validation"
    return "weak_or_context_only"


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    outcomes = normalized_live_rows(read_rows(normalize_path(args.outcomes)))
    historical_rows = []
    if truthy(args.include_historical):
        historical_rows = normalized_historical_rows(
            read_rows(normalize_path(args.historical_backfill)),
            quality_fail_ids(read_rows(normalize_path(args.historical_quality))),
        )
    all_rows = [*outcomes, *historical_rows]
    grouped = defaultdict(list)
    for row in all_rows:
        grouped[row_key(row)].append(row)

    output = []
    for key, rows in grouped.items():
        event_type, event_subtype, source_type, tier, btc_regime = key
        out = {
            "event_type": event_type,
            "event_subtype": event_subtype,
            "source_type": source_type,
            "asset_tier": tier,
            "btc_regime_trend_14d": btc_regime,
            "sample_count": len(rows),
        }
        for horizon in HORIZONS:
            values = [abnormal_value(row, horizon) for row in rows]
            values = [value for value in values if value is not None]
            out[f"computed_{horizon}_count"] = len(values)
            out[f"avg_abnormal_primary_{horizon}"] = round(avg(values), 6)
            out[f"median_abnormal_primary_{horizon}"] = round(median(values), 6)
            out[f"win_rate_primary_{horizon}"] = round(sum(1 for value in values if value > 0) / len(values), 4) if values else 0.0
        out["matrix_status"] = status_for(out)
        output.append(out)

    output.sort(key=lambda row: (-int(row.get("sample_count", 0)), row["event_type"], row["source_type"]))
    fields = list(output[0].keys()) if output else [
        "event_type",
        "event_subtype",
        "source_type",
        "asset_tier",
        "btc_regime_trend_14d",
        "sample_count",
        "matrix_status",
    ]
    write_rows(normalize_path(args.output), output, fields)
    summary = {
        "status": "pass",
        "generated_at_china": china_stamp(),
        "live_input_rows": len(outcomes),
        "historical_input_rows": len(historical_rows),
        "input_rows": len(all_rows),
        "matrix_rows": len(output),
        "insufficient_sample_count": sum(1 for row in output if row["matrix_status"] == "insufficient_sample"),
        "short_horizon_only_count": sum(1 for row in output if row["matrix_status"] == "short_horizon_only"),
        "promising_needs_validation_count": sum(1 for row in output if row["matrix_status"] == "promising_needs_validation"),
        "output": str(normalize_path(args.output)),
        "markdown_output": str(normalize_path(args.markdown_output)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    lines = [
        "# Event Type Performance Matrix",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- input_rows: {summary['input_rows']}",
        f"- matrix_rows: {summary['matrix_rows']}",
        "",
        "## Matrix Preview",
        "",
        *markdown_table(
            output[:30],
            [
                "event_type",
                "event_subtype",
                "source_type",
                "asset_tier",
                "btc_regime_trend_14d",
                "sample_count",
                "computed_1h_count",
                "avg_abnormal_primary_1h",
                "computed_24h_count",
                "avg_abnormal_primary_24h",
                "matrix_status",
            ],
        ),
        "",
        "This matrix is for research QA and source routing. It does not provide trading advice.",
        "",
    ]
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"matrix_rows={len(output)}")
    print(f"wrote_output={normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
