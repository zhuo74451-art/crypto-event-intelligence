import argparse
from pathlib import Path

try:
    from utils.watcher_utils import (
        ALERT_COLUMNS,
        compact_number,
        load_symbol_map,
        make_dedupe_key,
        normalize_path,
        read_csv_rows,
        safe_float,
        write_csv_rows,
        write_summary,
    )
except ModuleNotFoundError:
    from scripts.utils.watcher_utils import (
        ALERT_COLUMNS,
        compact_number,
        load_symbol_map,
        make_dedupe_key,
        normalize_path,
        read_csv_rows,
        safe_float,
        write_csv_rows,
        write_summary,
    )


ROOT = Path(__file__).resolve().parents[1]

EVENT_COLUMNS = [
    "event_id",
    "event_time",
    "title",
    "content",
    "source",
    "asset_symbol",
    "binance_spot_symbol",
    "binance_futures_symbol",
    "event_type",
    "direction_hint",
    "importance",
    "raw_signal_type",
    "watcher_source",
    "entity_label",
    "address",
    "tx_hash",
    "amount_native",
    "amount_usd",
    "confidence",
    "signal_asset_symbol",
    "alert_id",
    "event_time_china",
    "event_type_l2",
    "risk_category",
    "publish_route",
    "needs_model_review",
    "model_review_reason",
    "threshold_rule",
    "metric_value",
    "raw_json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize first-hand watcher alerts into event rows.")
    parser.add_argument(
        "--inputs",
        nargs="+",
        default=[
            str(ROOT / "data" / "watcher_alerts_address_transfers.csv"),
            str(ROOT / "data" / "watcher_alerts_stablecoin_mint_burn.csv"),
            str(ROOT / "data" / "watcher_alerts_hyperliquid_positions.csv"),
            str(ROOT / "data" / "watcher_alerts_cex_listings.csv"),
            str(ROOT / "data" / "watcher_alerts_token_unlocks.csv"),
        ],
    )
    parser.add_argument("--alerts-output", default=str(ROOT / "data" / "watcher_alerts_raw.csv"))
    parser.add_argument("--events-output", default=str(ROOT / "data" / "watcher_events_raw.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v07_watcher_normalization_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v07_watcher_daily_report.md"))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


def symbol_info(symbol: str, symbol_map: dict[str, dict]) -> tuple[str, str]:
    item = symbol_map.get(str(symbol or "").strip().upper(), {})
    return str(item.get("binance_spot_symbol", "")).strip(), str(item.get("binance_futures_symbol", "")).strip()


def event_asset(alert: dict) -> str:
    event_type = str(alert.get("event_type_l1", "")).strip()
    symbol = str(alert.get("asset_symbol", "")).strip().upper()
    if event_type == "stablecoin_flow":
        return "BTC"
    return symbol


def direction_hint(alert: dict) -> str:
    metric_type = str(alert.get("metric_type", "")).strip()
    if metric_type in {"treasury_transfer_out", "stablecoin_burn"}:
        return "risk"
    if metric_type == "lending_liquidation":
        return "risk"
    if metric_type == "token_unlock_upcoming":
        return "risk"
    if metric_type.startswith("hyperliquid_position_"):
        return "observe"
    return "observe"


def importance(alert: dict) -> int:
    amount = safe_float(alert.get("amount_usd"))
    if amount >= 100_000_000:
        return 5
    if amount >= 10_000_000:
        return 4
    if amount >= 1_000_000:
        return 3
    return 2


def title_for(alert: dict) -> str:
    entity = str(alert.get("primary_entity", "") or "Unknown entity").strip()
    metric_type = str(alert.get("metric_type", "")).strip()
    symbol = str(alert.get("asset_symbol", "")).strip().upper()
    amount = compact_number(safe_float(alert.get("amount_usd")))
    if metric_type == "hyperliquid_position_long":
        return f"{entity} holds large Hyperliquid long position: {amount} {symbol}"
    if metric_type == "hyperliquid_position_short":
        return f"{entity} holds large Hyperliquid short position: {amount} {symbol}"
    if metric_type == "cex_netflow_in":
        return f"{entity} aggregated exchange wallet net inflow: {amount} {symbol}"
    if metric_type == "cex_netflow_out":
        return f"{entity} aggregated exchange wallet net outflow: {amount} {symbol}"
    if metric_type == "funding_rate_high_positive":
        return f"{symbol} funding rate is unusually positive: {alert.get('metric_value', '')}"
    if metric_type == "funding_rate_high_negative":
        return f"{symbol} funding rate is unusually negative: {alert.get('metric_value', '')}"
    if metric_type == "lending_liquidation":
        return f"{entity} observed large Aave V3 liquidation: {amount} debt covered, collateral {symbol}"
    if metric_type == "cex_listing_announcement":
        return f"{entity} published listing announcement for {symbol}"
    if metric_type == "token_unlock_upcoming":
        return f"{symbol} scheduled token unlock is approaching: {amount}"
    if metric_type == "stablecoin_mint":
        return f"{entity} observed {amount} {symbol} mint on Ethereum"
    if metric_type == "stablecoin_burn":
        return f"{entity} observed {amount} {symbol} burn on Ethereum"
    if metric_type == "stablecoin_treasury_in":
        return f"{entity} treasury received {amount} {symbol}"
    if metric_type == "stablecoin_treasury_out":
        return f"{entity} treasury sent {amount} {symbol}"
    if metric_type == "treasury_transfer_out":
        return f"{entity} treasury transferred out {amount} {symbol}"
    if metric_type.startswith("cex_transfer"):
        return f"{entity} wallet {metric_type.replace('_', ' ')} {amount} {symbol}"
    return f"{entity} watched address moved {amount} {symbol}"


def content_for(alert: dict) -> str:
    parts = [
        f"First-hand watcher alert.",
        f"Entity: {alert.get('primary_entity', '')}.",
        f"Metric: {alert.get('metric_type', '')}.",
        f"Asset: {alert.get('asset_symbol', '')}.",
        f"USD value: {compact_number(safe_float(alert.get('amount_usd')))}.",
        f"Native size: {alert.get('amount_native', '')}.",
        f"Observed China time: {alert.get('observed_at_china', '')}.",
        f"Tx: {alert.get('tx_hash', '')}.",
        f"Threshold: {alert.get('threshold_rule', '')}.",
        "This is an observation for research and monitoring, not trading advice.",
    ]
    return " ".join(part for part in parts if part.strip())


def normalize_event(alert: dict, symbol_map: dict[str, dict]) -> dict:
    asset = event_asset(alert)
    spot, futures = symbol_info(asset, symbol_map)
    event_id = f"watcher_{alert.get('alert_id', '')}"
    return {
        "event_id": event_id,
        "event_time": alert.get("observed_at_utc", ""),
        "title": title_for(alert),
        "content": content_for(alert),
        "source": f"first_hand:{alert.get('watcher_source', '')}",
        "asset_symbol": asset,
        "binance_spot_symbol": spot,
        "binance_futures_symbol": futures,
        "event_type": alert.get("event_type_l1", ""),
        "direction_hint": direction_hint(alert),
        "importance": importance(alert),
        "raw_signal_type": alert.get("metric_type", ""),
        "watcher_source": alert.get("watcher_source", ""),
        "entity_label": alert.get("primary_entity", ""),
        "address": alert.get("primary_address", ""),
        "tx_hash": alert.get("tx_hash", ""),
        "amount_native": alert.get("amount_native", ""),
        "amount_usd": alert.get("amount_usd", ""),
        "confidence": alert.get("confidence", ""),
        "signal_asset_symbol": alert.get("asset_symbol", ""),
        "alert_id": alert.get("alert_id", ""),
        "event_time_china": alert.get("observed_at_china", ""),
        "event_type_l2": alert.get("event_type_l2", ""),
        "risk_category": alert.get("risk_category", ""),
        "publish_route": alert.get("publish_route", ""),
        "needs_model_review": alert.get("needs_model_review", ""),
        "model_review_reason": alert.get("model_review_reason", ""),
        "threshold_rule": alert.get("threshold_rule", ""),
        "metric_value": alert.get("metric_value", ""),
        "raw_json": alert.get("raw_json", ""),
    }


def render_markdown(alerts: list[dict], events: list[dict], summary: dict) -> str:
    lines = [
        "# v0.7 First-Hand Watcher Daily Report",
        "",
        "This report is local-only. It does not send Telegram messages and does not provide trading advice.",
        "",
        "## Summary",
        "",
        "| field | value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Alerts", "", "| time_china | entity | type | asset | amount_usd | route |", "|---|---|---|---|---:|---|"])
    for alert in alerts[:30]:
        lines.append(
            f"| {alert.get('observed_at_china', '')} | {alert.get('primary_entity', '')} | {alert.get('metric_type', '')} | {alert.get('asset_symbol', '')} | {alert.get('amount_usd', '')} | {alert.get('publish_route', '')} |"
        )
    lines.extend(["", "## Normalized Events", "", "| event_id | event_time_china | asset | event_type | title |", "|---|---|---|---|---|"])
    for event in events[:30]:
        title = str(event.get("title", "")).replace("|", "\\|")
        lines.append(
            f"| `{event.get('event_id', '')}` | {event.get('event_time_china', '')} | {event.get('asset_symbol', '')} | {event.get('event_type', '')} | {title} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    symbol_map = load_symbol_map(normalize_path(args.symbol_map))
    all_alerts = []
    input_rows = 0
    for value in args.inputs:
        rows = read_csv_rows(normalize_path(value))
        input_rows += len(rows)
        all_alerts.extend(rows)

    deduped = []
    seen = set()
    for alert in all_alerts:
        if str(alert.get("status", "")).strip().lower() not in {"ok", "sample"}:
            continue
        key = str(alert.get("dedupe_key", "")).strip() or make_dedupe_key(
            alert.get("tx_hash"), alert.get("primary_address"), alert.get("asset_symbol"), alert.get("metric_type")
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(alert)
        if len(deduped) >= args.limit:
            break

    events = [normalize_event(alert, symbol_map) for alert in deduped]
    write_csv_rows(normalize_path(args.alerts_output), deduped, ALERT_COLUMNS)
    write_csv_rows(normalize_path(args.events_output), events, EVENT_COLUMNS)
    summary = {
        "input_alert_rows": input_rows,
        "deduped_alert_rows": len(deduped),
        "event_rows": len(events),
        "needs_model_review_rows": sum(1 for row in deduped if str(row.get("needs_model_review", "")).lower() == "true"),
        "stablecoin_flow_rows": sum(1 for row in deduped if row.get("event_type_l1") == "stablecoin_flow"),
        "onchain_transfer_rows": sum(1 for row in deduped if row.get("event_type_l1") == "onchain_transfer"),
        "cex_netflow_rows": sum(1 for row in deduped if row.get("event_type_l1") == "cex_netflow"),
        "funding_rate_rows": sum(1 for row in deduped if row.get("event_type_l1") == "funding_rate"),
        "liquidation_rows": sum(1 for row in deduped if row.get("event_type_l1") == "liquidation"),
        "status": "pass",
    }
    write_summary(normalize_path(args.summary), summary)
    normalize_path(args.markdown_output).write_text(render_markdown(deduped, events, summary), encoding="utf-8")
    print(f"input_alert_rows={input_rows}")
    print(f"event_rows={len(events)}")
    print(f"wrote_events={args.events_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
