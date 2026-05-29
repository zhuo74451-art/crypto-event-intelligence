import argparse
import csv
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from utils.time_utils import parse_any_time_to_utc_iso, utc_iso_to_china_iso
except ModuleNotFoundError:
    from scripts.utils.time_utils import parse_any_time_to_utc_iso, utc_iso_to_china_iso


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
]

FOLLOWUP_COLUMNS = [
    "event_id",
    "event_time",
    "event_time_china",
    "title",
    "source",
    "asset_symbol",
    "event_type",
    "data_provider",
    "market_type",
    "symbol_used",
    "asset_price_t0",
    "asset_price_4h",
    "asset_price_24h",
    "btc_price_t0",
    "btc_price_4h",
    "btc_price_24h",
    "eth_price_t0",
    "eth_price_4h",
    "eth_price_24h",
    "asset_return_4h",
    "asset_return_24h",
    "btc_return_4h",
    "btc_return_24h",
    "eth_return_4h",
    "eth_return_24h",
    "abnormal_vs_btc_4h",
    "abnormal_vs_btc_24h",
    "abnormal_vs_eth_4h",
    "abnormal_vs_eth_24h",
    "status",
    "skip_reason",
]

BINANCE_SPOT_KLINES = "https://api.binance.com/api/v3/klines"
BINANCE_FUTURES_KLINES = "https://fapi.binance.com/fapi/v1/klines"
WINDOWS_MS = {"t0": 0, "4h": 4 * 3600 * 1000, "24h": 24 * 3600 * 1000}
STABLE_SYMBOLS = {"USDT", "USDC", "DAI", "BUSD", "FDUSD", "TUSD", "USDP"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 4h/24h follow-up report for sent TG alerts.")
    parser.add_argument("--sent-state", default=str(ROOT / "data" / "tg_live_sent_state.csv"))
    parser.add_argument("--events-output", default=str(ROOT / "data" / "tg_alert_followup_events.csv"))
    parser.add_argument("--backfill-output", default=str(ROOT / "results" / "v08_tg_alert_followup_backfill.csv"))
    parser.add_argument("--quality-output", default=str(ROOT / "results" / "v08_tg_alert_followup_quality_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_tg_alert_followup_summary.csv"))
    parser.add_argument("--report", default=str(ROOT / "results" / "v08_tg_alert_followup_report.md"))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--min-age-hours", type=float, default=4)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--run-backfill", default="true")
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


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


def load_symbol_map(path: Path) -> dict[str, dict]:
    output = {}
    for row in read_rows(path):
        symbol = str(row.get("asset_symbol", "") or "").strip().upper()
        if symbol:
            output[symbol] = row
    return output


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def utc_iso_to_dt(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def safe_float(value) -> float | None:
    try:
        if str(value).strip() == "":
            return None
        return float(str(value).strip())
    except Exception:
        return None


def event_time_ms(event_time_utc: str) -> int | None:
    dt = utc_iso_to_dt(event_time_utc)
    if not dt:
        return None
    return int(dt.timestamp() * 1000)


def pct(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value * 100:.2f}%"


def compact(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}"


def request_klines(url: str, symbol: str, start_ms: int, interval: str) -> list | None:
    params = {"symbol": symbol, "interval": interval, "startTime": start_ms, "limit": 1}
    last_error = None
    for attempt in range(1, 4):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code in {400, 404}:
                return None
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list) and payload:
                return payload[0]
            return None
        except Exception as exc:
            last_error = exc
            time.sleep(min(2 * attempt, 6))
    return None


def close_after(market_type: str, symbol: str, target_ms: int) -> float | None:
    url = BINANCE_SPOT_KLINES if market_type == "spot" else BINANCE_FUTURES_KLINES
    for interval in ["1m", "5m"]:
        kline = request_klines(url, symbol, target_ms, interval)
        if kline:
            return safe_float(kline[4])
    return None


def symbol_candidates(asset: str, symbol_map: dict[str, dict]) -> list[tuple[str, str]]:
    asset = str(asset or "").strip().upper()
    row = symbol_map.get(asset, {})
    output = []
    spot = str(row.get("binance_spot_symbol", "") or "").strip().upper()
    futures = str(row.get("binance_futures_symbol", "") or "").strip().upper()
    if spot:
        output.append(("spot", spot))
    if futures and futures != spot:
        output.append(("futures", futures))
    return output


def reference_candidates(symbol: str) -> list[tuple[str, str]]:
    return [("spot", symbol), ("futures", symbol)]


def fetch_series(candidates: list[tuple[str, str]], base_ms: int) -> tuple[dict[str, float | None], dict, str]:
    tried = []
    for market_type, symbol in candidates:
        tried.append(f"{market_type}:{symbol}")
        prices = {label: close_after(market_type, symbol, base_ms + offset) for label, offset in WINDOWS_MS.items()}
        if any(value is not None for value in prices.values()):
            return prices, {"market_type": market_type, "symbol": symbol}, ""
    return {label: None for label in WINDOWS_MS}, {"market_type": "", "symbol": ""}, "no_price_data:" + ",".join(tried)


def calc_return(now_value: float | None, start_value: float | None) -> float | None:
    if now_value is None or start_value in (None, 0):
        return None
    return now_value / start_value - 1


def subtract(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def build_followup_events(sent_rows: list[dict], min_age_hours: float, limit: int) -> tuple[list[dict], dict]:
    events = []
    stats = Counter()
    seen = set()
    current = now_utc()
    for row in sent_rows:
        stats["total_rows"] += 1
        if str(row.get("status", "")).strip().lower() != "sent":
            stats["non_sent_rows"] += 1
            continue
        asset = str(row.get("asset_symbol", "") or "").strip().upper()
        if not asset:
            stats["missing_asset_rows"] += 1
            continue
        raw_time = str(row.get("sent_at_china", "") or "").strip()
        sent_utc = parse_any_time_to_utc_iso(raw_time)
        sent_dt = utc_iso_to_dt(sent_utc)
        if not sent_dt:
            stats["bad_time_rows"] += 1
            continue
        age_hours = (current - sent_dt).total_seconds() / 3600
        if age_hours < min_age_hours:
            stats["too_young_rows"] += 1
            continue
        candidate_id = str(row.get("candidate_id", "") or "").strip()
        event_id = candidate_id or f"tg_sent_{len(events) + 1:04d}"
        if event_id in seen:
            stats["duplicate_event_rows"] += 1
            continue
        seen.add(event_id)
        event_type = str(row.get("event_type", "") or "tg_alert").strip() or "tg_alert"
        price_asset = "BTC" if event_type in {"cex_netflow", "stablecoin_flow"} and asset in STABLE_SYMBOLS else asset
        amount = str(row.get("amount_usd", "") or "").strip()
        severity = str(row.get("severity_tier", "") or "").strip()
        title = f"TG sent alert: {event_type} {asset}"
        if amount:
            title += f" amount_usd={amount}"
        if severity:
            title += f" severity={severity}"
        if price_asset != asset:
            title += f" followup_proxy={price_asset}"
        events.append(
            {
                "event_id": event_id,
                "event_time": sent_utc,
                "title": title,
                "content": f"Telegram alert follow-up measurement. Original alert asset={asset}; price follow-up asset={price_asset}. Research and alert-quality evaluation only.",
                "source": "tg_live_sent_state",
                "asset_symbol": price_asset,
                "binance_spot_symbol": "",
                "binance_futures_symbol": "",
                "event_type": event_type,
                "direction_hint": "observe",
                "importance": "3",
            }
        )
        stats["eligible_rows"] += 1
        if limit and len(events) >= limit:
            break
    return events, dict(stats)


def build_lightweight_backfill(events: list[dict], symbol_map_path: Path) -> list[dict]:
    symbol_map = load_symbol_map(symbol_map_path)
    rows = []
    for event in events:
        row = {column: "" for column in FOLLOWUP_COLUMNS}
        row.update(
            {
                "event_id": event.get("event_id", ""),
                "event_time": event.get("event_time", ""),
                "event_time_china": utc_iso_to_china_iso(event.get("event_time", "")),
                "title": event.get("title", ""),
                "source": event.get("source", ""),
                "asset_symbol": event.get("asset_symbol", ""),
                "event_type": event.get("event_type", ""),
                "data_provider": "binance",
            }
        )
        base_ms = event_time_ms(str(event.get("event_time", "")))
        if base_ms is None:
            row["status"] = "skipped"
            row["skip_reason"] = "bad_event_time"
            rows.append(row)
            continue
        asset = str(event.get("asset_symbol", "") or "").strip().upper()
        candidates = symbol_candidates(asset, symbol_map)
        if not candidates:
            row["status"] = "skipped"
            row["skip_reason"] = "missing_or_unsupported_symbol"
            rows.append(row)
            continue

        asset_prices, asset_meta, asset_reason = fetch_series(candidates, base_ms)
        btc_prices, _, btc_reason = fetch_series(reference_candidates("BTCUSDT"), base_ms)
        eth_prices, _, eth_reason = fetch_series(reference_candidates("ETHUSDT"), base_ms)
        row["market_type"] = asset_meta.get("market_type", "")
        row["symbol_used"] = asset_meta.get("symbol", "")

        for label in ["t0", "4h", "24h"]:
            row[f"asset_price_{label}"] = "" if asset_prices[label] is None else asset_prices[label]
            row[f"btc_price_{label}"] = "" if btc_prices[label] is None else btc_prices[label]
            row[f"eth_price_{label}"] = "" if eth_prices[label] is None else eth_prices[label]

        asset_4h = calc_return(asset_prices["4h"], asset_prices["t0"])
        asset_24h = calc_return(asset_prices["24h"], asset_prices["t0"])
        btc_4h = calc_return(btc_prices["4h"], btc_prices["t0"])
        btc_24h = calc_return(btc_prices["24h"], btc_prices["t0"])
        eth_4h = calc_return(eth_prices["4h"], eth_prices["t0"])
        eth_24h = calc_return(eth_prices["24h"], eth_prices["t0"])
        row["asset_return_4h"] = "" if asset_4h is None else asset_4h
        row["asset_return_24h"] = "" if asset_24h is None else asset_24h
        row["btc_return_4h"] = "" if btc_4h is None else btc_4h
        row["btc_return_24h"] = "" if btc_24h is None else btc_24h
        row["eth_return_4h"] = "" if eth_4h is None else eth_4h
        row["eth_return_24h"] = "" if eth_24h is None else eth_24h
        row["abnormal_vs_btc_4h"] = "" if subtract(asset_4h, btc_4h) is None else subtract(asset_4h, btc_4h)
        row["abnormal_vs_btc_24h"] = "" if subtract(asset_24h, btc_24h) is None else subtract(asset_24h, btc_24h)
        row["abnormal_vs_eth_4h"] = "" if subtract(asset_4h, eth_4h) is None else subtract(asset_4h, eth_4h)
        row["abnormal_vs_eth_24h"] = "" if subtract(asset_24h, eth_24h) is None else subtract(asset_24h, eth_24h)

        reasons = [reason for reason in [asset_reason, btc_reason, eth_reason] if reason]
        computable = bool(str(row["abnormal_vs_btc_4h"]).strip() or str(row["abnormal_vs_btc_24h"]).strip())
        if computable and not reasons:
            row["status"] = "ok"
        elif computable:
            row["status"] = "partial"
            row["skip_reason"] = ";".join(reasons)
        else:
            row["status"] = "skipped"
            row["skip_reason"] = ";".join(reasons or ["no_computable_followup"])
        rows.append(row)
    return rows


def avg(values: list[float]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def render_report(backfill_rows: list[dict], summary: dict) -> str:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for row in backfill_rows:
        by_type[str(row.get("event_type", "") or "unknown")].append(row)

    lines = [
        "# v0.8 TG Alert Follow-up Report",
        "",
        "This report measures what happened after Telegram alerts were sent. It is for alert-quality review only and is not trading advice.",
        "",
        "## Summary",
        "",
        "| field | value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## By Event Type",
            "",
            "| event_type | rows | 4h computable | 24h computable | avg abnormal_vs_btc_4h | avg abnormal_vs_btc_24h |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for event_type, rows in sorted(by_type.items(), key=lambda item: len(item[1]), reverse=True):
        v4 = [safe_float(row.get("abnormal_vs_btc_4h")) for row in rows]
        v24 = [safe_float(row.get("abnormal_vs_btc_24h")) for row in rows]
        lines.append(
            f"| {event_type} | {len(rows)} | {sum(value is not None for value in v4)} | {sum(value is not None for value in v24)} | {pct(avg(v4))} | {pct(avg(v24))} |"
        )

    scored_4h = [(safe_float(row.get("abnormal_vs_btc_4h")), row) for row in backfill_rows]
    scored_4h = [(score, row) for score, row in scored_4h if score is not None]
    scored_24h = [(safe_float(row.get("abnormal_vs_btc_24h")), row) for row in backfill_rows]
    scored_24h = [(score, row) for score, row in scored_24h if score is not None]

    def section(title: str, items: list[tuple[float, dict]]) -> None:
        lines.extend(["", f"## {title}", "", "| abnormal_vs_btc | asset | event_type | title |", "|---:|---|---|---|"])
        if not items:
            lines.append("| n/a |  |  | no computable rows yet |")
            return
        for score, row in items[:10]:
            title_text = str(row.get("title", "") or "").replace("|", "\\|")
            lines.append(f"| {pct(score)} | {row.get('asset_symbol', '')} | {row.get('event_type', '')} | {title_text} |")

    section("Best 4h Follow-ups", sorted(scored_4h, key=lambda item: item[0], reverse=True))
    section("Worst 4h Follow-ups", sorted(scored_4h, key=lambda item: item[0]))
    section("Best 24h Follow-ups", sorted(scored_24h, key=lambda item: item[0], reverse=True))
    section("Worst 24h Follow-ups", sorted(scored_24h, key=lambda item: item[0]))

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- 4h rows become meaningful only after alerts are at least 4 hours old.",
            "- 24h rows become meaningful only after alerts are at least 24 hours old.",
            "- Missing rows usually mean the alert is too new, the asset has no Binance symbol, or the old sent-state row lacked asset metadata.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    sent_path = normalize_path(args.sent_state)
    events_path = normalize_path(args.events_output)
    backfill_path = normalize_path(args.backfill_output)
    quality_path = normalize_path(args.quality_output)
    summary_path = normalize_path(args.summary)
    report_path = normalize_path(args.report)
    symbol_map_path = normalize_path(args.symbol_map)

    sent_rows = read_rows(sent_path)
    events, stats = build_followup_events(sent_rows, args.min_age_hours, args.limit)
    write_rows(events_path, events, EVENT_COLUMNS)

    if events and truthy(args.run_backfill):
        followup_rows = build_lightweight_backfill(events, symbol_map_path)
        write_rows(backfill_path, followup_rows, FOLLOWUP_COLUMNS)
        write_rows(quality_path, [], ["status", "note"])
    elif not events:
        write_rows(backfill_path, [], [])
        write_rows(quality_path, [], [])

    backfill_rows = read_rows(backfill_path)
    summary = {
        "sent_state_rows": len(sent_rows),
        "eligible_event_rows": len(events),
        "backfill_rows": len(backfill_rows),
        "ok_rows": sum(1 for row in backfill_rows if str(row.get("status", "")).lower() == "ok"),
        "partial_rows": sum(1 for row in backfill_rows if str(row.get("status", "")).lower() == "partial"),
        "skipped_rows": sum(1 for row in backfill_rows if str(row.get("status", "")).lower() == "skipped"),
        "computable_4h_rows": sum(1 for row in backfill_rows if str(row.get("abnormal_vs_btc_4h", "")).strip()),
        "computable_24h_rows": sum(1 for row in backfill_rows if str(row.get("abnormal_vs_btc_24h", "")).strip()),
        "min_age_hours": args.min_age_hours,
        **stats,
    }
    write_rows(summary_path, [summary], list(summary.keys()))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(backfill_rows, summary), encoding="utf-8")
    print(f"eligible_event_rows={len(events)}")
    print(f"backfill_rows={len(backfill_rows)}")
    print(f"computable_4h_rows={summary['computable_4h_rows']}")
    print(f"computable_24h_rows={summary['computable_24h_rows']}")
    print(f"wrote_report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
