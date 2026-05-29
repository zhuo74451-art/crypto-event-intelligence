import argparse
import csv
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
HORIZONS = ["1h", "4h", "24h", "72h"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build live/historical source effectiveness report.")
    parser.add_argument("--registry", default=str(ROOT / "data" / "source_registry.csv"))
    parser.add_argument("--ledger", default=str(ROOT / "data" / "tg_alert_ledger.csv"))
    parser.add_argument("--outcomes", default=str(ROOT / "data" / "tg_alert_outcomes.csv"))
    parser.add_argument("--decision-log", default=str(ROOT / "data" / "tg_radar_decision_log.csv"))
    parser.add_argument("--historical-by-source", default=str(ROOT / "results" / "v10_historical_signal_quality_by_source.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "source_effectiveness_report.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "source_effectiveness_report.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "source_effectiveness_summary.csv"))
    parser.add_argument("--false-positive-threshold", type=float, default=0.003)
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


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def registry_by_type(rows: list[dict]) -> dict[str, dict]:
    output = {}
    for row in rows:
        stype = str(row.get("source_type") or "").strip()
        if stype and stype not in output:
            output[stype] = row
    return output


def historical_by_source(rows: list[dict]) -> dict[str, dict]:
    output = {}
    for row in rows:
        source = str(row.get("source") or row.get("source_type") or "").strip()
        if source:
            output[source] = row
            if source.startswith("tg:"):
                output[source[3:].lower()] = row
    return output


def event_type_from_source(source_type: str) -> str:
    mapping = {
        "hyperliquid": "whale_position",
        "token_unlock": "token_unlock",
        "long_short": "market_structure",
        "cex_netflow": "cex_netflow",
        "stablecoin_flow": "stablecoin_flow",
        "address_transfer": "whale_position",
        "funding_rate": "funding_rate",
        "exchange_listing": "exchange_listing",
        "lending_liquidation": "lending_liquidation",
    }
    return mapping.get(source_type, source_type)


def false_positive_like(row: dict, threshold: float) -> bool:
    values = []
    for horizon in HORIZONS:
        value = safe_float(row.get(f"abnormal_primary_{horizon}"))
        if value is not None:
            values.append(abs(value))
    return bool(values) and max(values) < threshold


def live_status(row: dict) -> str:
    outcome_rows = int(row.get("outcome_rows", 0) or 0)
    computed_1h = int(row.get("computed_1h_count", 0) or 0)
    computed_4h = int(row.get("computed_4h_count", 0) or 0)
    sent_rows = int(row.get("sent_count", 0) or 0)
    false_rate = safe_float(row.get("false_positive_like_rate")) or 0.0
    avg_1h = safe_float(row.get("avg_abnormal_primary_1h")) or 0.0
    if outcome_rows == 0 and sent_rows == 0:
        return "shadow_or_no_live_data"
    if computed_4h < 10 and computed_1h < 10:
        return "insufficient_live_outcomes"
    if false_rate >= 0.65:
        return "likely_noise_or_digest_only"
    if computed_4h >= 10 and abs(avg_1h) >= 0.005:
        return "promising_needs_more_samples"
    return "monitor"


def route_recommendation(row: dict) -> str:
    status = row.get("live_effectiveness_status", "")
    default_route = row.get("tg_default_route", "")
    if status == "likely_noise_or_digest_only":
        return "digest_or_archive"
    if status == "shadow_or_no_live_data":
        return "shadow"
    if status == "insufficient_live_outcomes":
        return default_route or "monitor"
    if status == "promising_needs_more_samples":
        return "board_or_interrupt_when_extreme"
    return default_route or "monitor"


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    registry_rows = read_rows(normalize_path(args.registry))
    ledger_rows = read_rows(normalize_path(args.ledger))
    outcome_rows = read_rows(normalize_path(args.outcomes))
    decision_rows = read_rows(normalize_path(args.decision_log))
    hist_rows = read_rows(normalize_path(args.historical_by_source))
    registry = registry_by_type(registry_rows)
    historical = historical_by_source(hist_rows)

    all_source_types = sorted(
        set(registry)
        | {str(row.get("source_type") or "").strip() for row in ledger_rows if row.get("source_type")}
        | {str(row.get("source_type") or "").strip() for row in outcome_rows if row.get("source_type")}
        | {str(row.get("source_type") or "").strip() for row in decision_rows if row.get("source_type")}
    )

    ledger_by_source = defaultdict(list)
    outcome_by_source = defaultdict(list)
    decision_by_source = defaultdict(list)
    for row in ledger_rows:
        ledger_by_source[str(row.get("source_type") or "unknown").strip() or "unknown"].append(row)
    for row in outcome_rows:
        outcome_by_source[str(row.get("source_type") or "unknown").strip() or "unknown"].append(row)
    for row in decision_rows:
        decision_by_source[str(row.get("source_type") or "unknown").strip() or "unknown"].append(row)

    output = []
    for source_type in all_source_types:
        reg = registry.get(source_type, {})
        ledger = ledger_by_source.get(source_type, [])
        outcomes = outcome_by_source.get(source_type, [])
        decisions = decision_by_source.get(source_type, [])
        decision_counts = Counter(str(row.get("decision") or "unknown").strip() or "unknown" for row in decisions)
        sent_count = sum(1 for row in ledger if str(row.get("send_status") or "").strip() == "sent")
        skipped_or_failed_count = sum(1 for row in ledger if str(row.get("send_status") or "").strip() not in {"sent", ""})
        row = {
            "source_type": source_type,
            "source_id": reg.get("source_id", source_type),
            "source_family": reg.get("source_family", ""),
            "enabled": reg.get("enabled", ""),
            "shadow_mode": reg.get("shadow_mode", ""),
            "tg_default_route": reg.get("tg_default_route", ""),
            "confidence_level": reg.get("confidence_level", ""),
            "decision_rows": len(decisions),
            "selected_count": decision_counts.get("selected", 0),
            "filtered_digest_only_count": decision_counts.get("filtered_digest_only", 0),
            "suppressed_cooldown_count": decision_counts.get("suppressed_cooldown", 0),
            "not_selected_capacity_count": decision_counts.get("not_selected_capacity", 0),
            "sent_count": sent_count,
            "skipped_or_failed_count": skipped_or_failed_count,
            "outcome_rows": len(outcomes),
            "false_positive_like_count": sum(1 for item in outcomes if false_positive_like(item, args.false_positive_threshold)),
        }
        row["false_positive_like_rate"] = round(row["false_positive_like_count"] / len(outcomes), 4) if outcomes else 0.0
        for horizon in HORIZONS:
            values = [safe_float(item.get(f"abnormal_primary_{horizon}")) for item in outcomes]
            values = [value for value in values if value is not None]
            row[f"computed_{horizon}_count"] = len(values)
            row[f"avg_abnormal_primary_{horizon}"] = round(avg(values), 6)
            row[f"median_abnormal_primary_{horizon}"] = round(median(values), 6)
            row[f"win_rate_primary_{horizon}"] = round(sum(1 for value in values if value > 0) / len(values), 4) if values else 0.0
        hist = historical.get(source_type) or historical.get(str(reg.get("source_id") or "").lower()) or {}
        row["historical_sample_count"] = hist.get("sample_count", "")
        row["historical_valid_24h_count"] = hist.get("valid_24h_count", "")
        row["historical_avg_abnormal_vs_btc_24h"] = hist.get("avg_abnormal_vs_btc_24h", "")
        row["historical_status"] = hist.get("historical_usefulness_status", reg.get("evaluation_status", ""))
        row["mapped_event_type"] = event_type_from_source(source_type)
        row["live_effectiveness_status"] = live_status(row)
        row["recommended_route"] = route_recommendation(row)
        output.append(row)

    output.sort(key=lambda row: (row["live_effectiveness_status"], row["source_type"]))
    fields = list(output[0].keys()) if output else ["source_type", "live_effectiveness_status"]
    write_rows(normalize_path(args.output), output, fields)

    summary = {
        "status": "pass",
        "generated_at_china": china_stamp(),
        "source_rows": len(output),
        "ledger_rows": len(ledger_rows),
        "outcome_rows": len(outcome_rows),
        "decision_rows": len(decision_rows),
        "shadow_or_no_live_data_count": sum(1 for row in output if row["live_effectiveness_status"] == "shadow_or_no_live_data"),
        "insufficient_live_outcomes_count": sum(1 for row in output if row["live_effectiveness_status"] == "insufficient_live_outcomes"),
        "likely_noise_or_digest_only_count": sum(1 for row in output if row["live_effectiveness_status"] == "likely_noise_or_digest_only"),
        "promising_needs_more_samples_count": sum(1 for row in output if row["live_effectiveness_status"] == "promising_needs_more_samples"),
        "output": str(normalize_path(args.output)),
        "markdown_output": str(normalize_path(args.markdown_output)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    preview_cols = [
        "source_type",
        "enabled",
        "shadow_mode",
        "sent_count",
        "outcome_rows",
        "computed_1h_count",
        "computed_4h_count",
        "avg_abnormal_primary_1h",
        "false_positive_like_rate",
        "historical_status",
        "live_effectiveness_status",
        "recommended_route",
    ]
    lines = [
        "# Source Effectiveness Report",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- source_rows: {summary['source_rows']}",
        f"- ledger_rows: {summary['ledger_rows']}",
        f"- outcome_rows: {summary['outcome_rows']}",
        f"- decision_rows: {summary['decision_rows']}",
        "",
        "## Source Matrix",
        "",
        *markdown_table(output, preview_cols),
        "",
        "## Interpretation",
        "",
        "- `shadow_or_no_live_data`: source is registered but has no live outcome evidence yet; keep in shadow or archive.",
        "- `insufficient_live_outcomes`: source has live rows but too few matured horizons for product conclusions.",
        "- `likely_noise_or_digest_only`: available outcomes show low movement; lower priority or move to digest.",
        "- `promising_needs_more_samples`: early signal worth more samples, but not statistically conclusive.",
        "",
        "This report is for source governance and research QA. It does not provide trading advice.",
        "",
    ]
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"source_rows={len(output)}")
    print(f"wrote_output={normalize_path(args.output)}")
    print(f"wrote_report={normalize_path(args.markdown_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
