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
    parser = argparse.ArgumentParser(description="Build signal decay curve from TG alert outcomes.")
    parser.add_argument("--outcomes", default=str(ROOT / "data" / "tg_alert_outcomes.csv"))
    parser.add_argument("--historical-backfill", default=str(ROOT / "results" / "v08_historical_replay_broad_200_price_backfill.csv"))
    parser.add_argument("--historical-quality", default=str(ROOT / "results" / "v08_historical_replay_broad_200_quality_report.csv"))
    parser.add_argument("--include-historical", default="true")
    parser.add_argument("--group-by", default="event_type,event_subtype,source_type")
    parser.add_argument("--output", default=str(ROOT / "results" / "signal_decay_curve.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "signal_decay_curve_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "signal_decay_curve.md"))
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
        item["sample_origin"] = "historical_replay"
        output.append(item)
    return output


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def group_key(row: dict, fields: list[str]) -> tuple[str, ...]:
    return tuple(str(row.get(field) or "unknown").strip() or "unknown" for field in fields)


def decay_status(row: dict) -> str:
    c1 = int(row.get("computed_1h_count", 0) or 0)
    c24 = int(row.get("computed_24h_count", 0) or 0)
    c72 = int(row.get("computed_72h_count", 0) or 0)
    if max(c1, c24, c72) < 10:
        return "insufficient_sample"
    if c24 == 0 and c72 == 0:
        return "only_short_horizon"
    a1 = abs(safe_float(row.get("avg_abnormal_primary_1h")) or 0.0)
    a24 = abs(safe_float(row.get("avg_abnormal_primary_24h")) or 0.0)
    if a1 > 0 and a24 > a1 * 1.5:
        return "slow_burn_or_lagged"
    if a1 > 0 and a24 < a1 * 0.5:
        return "fast_decay"
    return "monitor"


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    fields = [field.strip() for field in args.group_by.split(",") if field.strip()]
    live_rows = normalized_live_rows(read_rows(normalize_path(args.outcomes)))
    historical_rows = []
    if truthy(args.include_historical):
        historical_rows = normalized_historical_rows(
            read_rows(normalize_path(args.historical_backfill)),
            quality_fail_ids(read_rows(normalize_path(args.historical_quality))),
        )
    rows = [*live_rows, *historical_rows]
    grouped = defaultdict(list)
    for row in rows:
        grouped[group_key(row, fields)].append(row)

    output = []
    for key, items in grouped.items():
        out = {field: value for field, value in zip(fields, key)}
        out["sample_count"] = len(items)
        previous_avg = None
        for horizon in HORIZONS:
            values = [abnormal_value(item, horizon) for item in items]
            values = [value for value in values if value is not None]
            avg_value = avg(values)
            out[f"computed_{horizon}_count"] = len(values)
            out[f"avg_abnormal_primary_{horizon}"] = round(avg_value, 6)
            out[f"median_abnormal_primary_{horizon}"] = round(median(values), 6)
            out[f"abs_avg_abnormal_primary_{horizon}"] = round(abs(avg_value), 6)
            if previous_avg is None:
                out[f"decay_ratio_from_previous_to_{horizon}"] = ""
            else:
                out[f"decay_ratio_from_previous_to_{horizon}"] = round(abs(avg_value) / abs(previous_avg), 4) if previous_avg else ""
            if values:
                previous_avg = avg_value
        out["decay_status"] = decay_status(out)
        output.append(out)

    output.sort(key=lambda row: (-int(row.get("sample_count", 0)), row.get("event_type", ""), row.get("source_type", "")))
    output_fields = list(output[0].keys()) if output else [*fields, "sample_count", "decay_status"]
    write_rows(normalize_path(args.output), output, output_fields)

    summary = {
        "status": "pass",
        "generated_at_china": china_stamp(),
        "live_input_rows": len(live_rows),
        "historical_input_rows": len(historical_rows),
        "input_rows": len(rows),
        "curve_rows": len(output),
        "insufficient_sample_count": sum(1 for row in output if row["decay_status"] == "insufficient_sample"),
        "only_short_horizon_count": sum(1 for row in output if row["decay_status"] == "only_short_horizon"),
        "fast_decay_count": sum(1 for row in output if row["decay_status"] == "fast_decay"),
        "slow_burn_or_lagged_count": sum(1 for row in output if row["decay_status"] == "slow_burn_or_lagged"),
        "output": str(normalize_path(args.output)),
        "markdown_output": str(normalize_path(args.markdown_output)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    preview_cols = [
        *fields,
        "sample_count",
        "computed_1h_count",
        "avg_abnormal_primary_1h",
        "computed_4h_count",
        "avg_abnormal_primary_4h",
        "computed_24h_count",
        "avg_abnormal_primary_24h",
        "computed_72h_count",
        "avg_abnormal_primary_72h",
        "decay_status",
    ]
    lines = [
        "# Signal Decay Curve",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- input_rows: {summary['input_rows']}",
        f"- curve_rows: {summary['curve_rows']}",
        "",
        "## Curve Preview",
        "",
        *markdown_table(output[:30], preview_cols),
        "",
        "This curve is for research QA and source routing. It does not provide trading advice.",
        "",
    ]
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"curve_rows={len(output)}")
    print(f"wrote_output={normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
