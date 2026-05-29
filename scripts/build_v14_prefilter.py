import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
BENCHMARK_ASSETS = {"BTC", "ETH"}
SHORT_PRICE_ROWS: dict[str, dict] = {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build v14 hard prefilter results before Composer and Publisher.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_500_price_backfill.csv"))
    parser.add_argument("--price-in", default=str(ROOT / "results" / "v13_extended_price_in_report.csv"))
    parser.add_argument("--short-price-in", default=str(ROOT / "data" / "v14_short_price_in.csv"))
    parser.add_argument("--regime", default=str(ROOT / "results" / "v13_extended_regime_layer_report.csv"))
    parser.add_argument("--exploit-verified", default=str(ROOT / "data" / "active_exploit_verified.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v14_prefilter_results.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_prefilter_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_prefilter_report.md"))
    parser.add_argument("--max-pre-event-abnormal", type=float, default=0.02)
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


def safe_float(value) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return 0.0


def index_by(rows: list[dict], field: str) -> dict[str, dict]:
    return {str(row.get(field) or "").strip(): row for row in rows if str(row.get(field) or "").strip()}


def regime_index(rows: list[dict]) -> dict[str, list[dict]]:
    output: dict[str, list[dict]] = {}
    for row in rows:
        key = str(row.get("event_group") or "").strip()
        output.setdefault(key, []).append(row)
    return output


def exploit_index(rows: list[dict]) -> dict[str, dict]:
    return index_by(rows, "event_id")


def check_row(row: dict, price_rows: dict[str, dict], regimes: dict[str, list[dict]], exploit_rows: dict[str, dict], max_pre: float) -> dict:
    event_id = str(row.get("event_id") or "").strip()
    subtype = str(row.get("event_subtype") or row.get("event_type") or "").strip()
    asset = str(row.get("asset_symbol") or "").strip().upper()
    blocks: list[str] = []
    warnings: list[str] = []

    if not asset:
        blocks.append("missing_tradable_asset")
    if asset in BENCHMARK_ASSETS:
        blocks.append("benchmark_asset")
    if not (row.get("binance_spot_symbol") or row.get("binance_futures_symbol")):
        blocks.append("missing_binance_symbol")

    price_row = price_rows.get(event_id, {})
    pre_abnormal = safe_float(price_row.get("pre_event_abnormal_6h"))
    price_flag = str(price_row.get("price_in_flag") or "")
    if price_flag == "severe_price_in" or abs(pre_abnormal) > max_pre:
        blocks.append(f"pre_event_price_moved_{pre_abnormal:+.2%}_6h")
    elif not price_row:
        warnings.append("missing_pre_event_price_check")

    short_price_row = SHORT_PRICE_ROWS.get(event_id, {})
    if str(short_price_row.get("short_price_in_flag") or "") == "price_in_block":
        blocks.append(str(short_price_row.get("short_price_in_reason") or "short_price_in_block"))
    elif not short_price_row:
        warnings.append("missing_short_price_in_check")

    regime_rows = regimes.get(subtype, [])
    if not regime_rows:
        warnings.append("missing_regime_layer")
    elif all(str(item.get("btc_regime_trend_14d") or "") in {"btc_extreme_down", "btc_extreme_up", "liquidity_crisis"} for item in regime_rows):
        blocks.append("regime_filter_block")

    if subtype == "exploit_or_theft":
        exploit = exploit_rows.get(event_id, {})
        primary_asset = str(exploit.get("primary_tradable_asset") or exploit.get("affected_tradable_asset") or "").strip()
        confidence = safe_float(exploit.get("primary_asset_confidence") or {"high": 0.95, "medium": 0.75, "low": 0.3}.get(str(exploit.get("asset_attribution_confidence") or "low"), 0.0))
        impact_type = str(exploit.get("primary_impact_type") or "")
        if not primary_asset:
            blocks.append("missing_primary_tradable_asset")
        if confidence < 0.7:
            blocks.append("primary_asset_confidence_below_70pct")
        if impact_type == "chain_token" and confidence < 0.8:
            blocks.append("weak_chain_token_attribution")

    return {
        "event_id": event_id,
        "asset_symbol": asset,
        "event_subtype": subtype,
        "prefilter_passed": "true" if not blocks else "false",
        "prefilter_blocks": ",".join(blocks) if blocks else "pass",
        "prefilter_warnings": ",".join(warnings) if warnings else "none",
        "pre_event_abnormal_6h": f"{pre_abnormal:.6f}" if price_row else "",
        "price_in_5m": short_price_row.get("price_in_5m", ""),
        "price_in_15m": short_price_row.get("price_in_15m", ""),
        "price_in_1h": short_price_row.get("price_in_1h", ""),
        "short_price_in_flag": short_price_row.get("short_price_in_flag", ""),
        "price_in_flag": price_flag,
        "market_hours_block": "false",
        "title": row.get("title", ""),
    }


def render_report(rows: list[dict], summary: dict) -> str:
    block_counts = Counter(
        reason
        for row in rows
        for reason in str(row.get("prefilter_blocks") or "").split(",")
        if reason and reason != "pass"
    )
    lines = [
        "# v14 PreFilter Report",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- input_rows: {summary['input_rows']}",
        f"- passed_rows: {summary['passed_rows']}",
        f"- blocked_rows: {summary['blocked_rows']}",
        "",
        "## Block Reasons",
        "",
    ]
    for reason, count in block_counts.most_common(20):
        lines.append(f"- {reason}: {count}")
    lines.extend(["", "## Blocked Samples", "", "| event_id | asset | subtype | blocks | title |", "|---|---|---|---|---|"])
    for row in [item for item in rows if item["prefilter_passed"] != "true"][:40]:
        title = str(row.get("title") or "").replace("|", "\\|")[:120]
        lines.append(f"| {row['event_id']} | {row['asset_symbol']} | {row['event_subtype']} | {row['prefilter_blocks']} | {title} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    backfill = read_rows(normalize_path(args.backfill))
    price_rows = index_by(read_rows(normalize_path(args.price_in)), "event_id")
    global SHORT_PRICE_ROWS
    SHORT_PRICE_ROWS = index_by(read_rows(normalize_path(args.short_price_in)), "event_id")
    regimes = regime_index(read_rows(normalize_path(args.regime)))
    exploit_rows = exploit_index(read_rows(normalize_path(args.exploit_verified)))
    output = [check_row(row, price_rows, regimes, exploit_rows, args.max_pre_event_abnormal) for row in backfill]
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["event_id"])
    summary = {
        "generated_at_china": china_stamp(),
        "input_rows": len(output),
        "passed_rows": sum(1 for row in output if row["prefilter_passed"] == "true"),
        "blocked_rows": sum(1 for row in output if row["prefilter_passed"] != "true"),
        "warning_rows": sum(1 for row in output if row["prefilter_warnings"] != "none"),
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    normalize_path(args.markdown_output).write_text(render_report(output, summary), encoding="utf-8")
    print(f"input_rows={summary['input_rows']}")
    print(f"passed_rows={summary['passed_rows']}")
    print(f"blocked_rows={summary['blocked_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
