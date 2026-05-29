import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://fapi.binance.com"
CN_TZ = timezone(timedelta(hours=8))


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


COLUMNS = [
    "observed_at_utc",
    "observed_at_china",
    "asset_symbol",
    "binance_futures_symbol",
    "last_price",
    "price_change_pct_1h",
    "price_change_pct_24h",
    "quote_volume_usd_1h",
    "quote_volume_change_pct_1h",
    "quote_volume_usd_24h",
    "open_interest",
    "open_interest_usd",
    "open_interest_change_pct_24h",
    "funding_rate",
    "next_funding_time_china",
    "top_position_long_short_ratio",
    "global_account_long_short_ratio",
    "taker_buy_sell_ratio",
    "crowding_bias",
    "market_state_label",
    "market_state_reason",
    "quality_status",
    "skip_reason",
    "raw_json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a public Binance USD-M market-state snapshot for TG digests.")
    parser.add_argument("--watchlist", default=str(ROOT / "data" / "funding_watchlist.csv"))
    parser.add_argument("--long-short-input", default=str(ROOT / "data" / "binance_long_short_snapshot.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_market_state_snapshot.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_market_state_snapshot_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_market_state_snapshot.md"))
    parser.add_argument("--oi-period", default="1h")
    parser.add_argument("--oi-limit", type=int, default=25)
    return parser.parse_args()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_to_china(value: str) -> str:
    raw = str(value or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw).astimezone(CN_TZ)
    except Exception:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC+8")


def ms_to_china(value: Any) -> str:
    try:
        dt = datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).astimezone(CN_TZ)
    except Exception:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC+8")


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


def enabled_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if str(row.get("enabled", "")).strip().lower() in {"1", "true", "yes", "y"}]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


def request_json(session: requests.Session, endpoint: str, params: dict, timeout: int = 15, retries: int = 3) -> Any:
    last_error = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            response = session.get(f"{BASE_URL}{endpoint}", params=params, timeout=timeout)
            if response.status_code < 500:
                response.raise_for_status()
                return response.json()
            last_error = RuntimeError(f"http={response.status_code}; body={response.text[:180]}")
        except Exception as exc:
            last_error = exc
        time.sleep(min(2 * attempt, 6))
    raise RuntimeError(f"request_failed:{last_error}")


def latest_long_short_by_symbol(path: Path) -> dict[str, dict]:
    output = {}
    for row in read_rows(path):
        symbol = str(row.get("binance_futures_symbol") or "").strip().upper()
        if symbol:
            output[symbol] = row
    return output


def oi_change_pct(records: Any) -> float:
    if not isinstance(records, list) or len(records) < 2:
        return 0.0
    first = safe_float(records[0].get("sumOpenInterest"))
    last = safe_float(records[-1].get("sumOpenInterest"))
    if first <= 0:
        return 0.0
    return (last / first - 1.0) * 100


def kline_1h_metrics(records: Any, current_price: float) -> tuple[float, float, float]:
    if not isinstance(records, list) or not records:
        return 0.0, 0.0, 0.0
    latest = records[-1]
    previous = records[-2] if len(records) >= 2 else []
    reference_price = safe_float(previous[4] if len(previous) > 4 else latest[1] if len(latest) > 1 else 0)
    if reference_price <= 0:
        reference_price = safe_float(latest[1] if len(latest) > 1 else 0)
    price_change_1h = (current_price / reference_price - 1.0) * 100 if reference_price > 0 and current_price > 0 else 0.0
    latest_quote_volume = safe_float(latest[7] if len(latest) > 7 else 0)
    previous_quote_volume = safe_float(previous[7] if len(previous) > 7 else 0)
    volume_change_1h = (latest_quote_volume / previous_quote_volume - 1.0) * 100 if previous_quote_volume > 0 else 0.0
    return price_change_1h, latest_quote_volume, volume_change_1h


def state_label(price_pct: float, oi_pct: float, funding: float, crowding_ratio: float, volume_usd: float) -> tuple[str, str]:
    reasons = []
    if price_pct >= 3 and oi_pct >= 3:
        reasons.append("价格与持仓同步上升")
    elif price_pct <= -3 and oi_pct >= 3:
        reasons.append("价格下跌但持仓上升")
    elif abs(price_pct) < 1 and oi_pct >= 5:
        reasons.append("价格横盘但持仓增加")
    elif abs(price_pct) >= 5:
        reasons.append("24小时价格波动较大")
    if abs(funding) >= 0.0008:
        reasons.append("资金费率偏离中性")
    if crowding_ratio >= 1.5:
        reasons.append("多头账户/仓位拥挤")
    elif 0 < crowding_ratio <= 0.67:
        reasons.append("空头账户/仓位拥挤")
    if volume_usd >= 1_000_000_000:
        reasons.append("24小时成交额较高")

    if not reasons:
        return "normal", "未见明显单项异常"
    if any("价格下跌但持仓上升" in item for item in reasons):
        return "stress_building", "；".join(reasons)
    if any("同步上升" in item for item in reasons):
        return "trend_with_oi", "；".join(reasons)
    if any("资金费率" in item for item in reasons) or any("拥挤" in item for item in reasons):
        return "crowding_or_funding", "；".join(reasons)
    return "active_market", "；".join(reasons)


def build_row(session: requests.Session, item: dict, observed_utc: str, long_short: dict, oi_period: str, oi_limit: int) -> dict:
    asset = str(item.get("asset_symbol") or "").strip().upper()
    symbol = str(item.get("binance_futures_symbol") or "").strip().upper()
    row = {column: "" for column in COLUMNS}
    row.update(
        {
            "observed_at_utc": observed_utc,
            "observed_at_china": utc_to_china(observed_utc),
            "asset_symbol": asset,
            "binance_futures_symbol": symbol,
        }
    )
    if not symbol:
        row["quality_status"] = "skipped"
        row["skip_reason"] = "missing_futures_symbol"
        return row

    try:
        ticker = request_json(session, "/fapi/v1/ticker/24hr", {"symbol": symbol})
        oi = request_json(session, "/fapi/v1/openInterest", {"symbol": symbol})
        premium = request_json(session, "/fapi/v1/premiumIndex", {"symbol": symbol})
        oi_hist = request_json(session, "/futures/data/openInterestHist", {"symbol": symbol, "period": oi_period, "limit": oi_limit})
        kline_1h = request_json(session, "/fapi/v1/klines", {"symbol": symbol, "interval": "1h", "limit": 2})
    except Exception as exc:
        row["quality_status"] = "skipped"
        row["skip_reason"] = str(exc)[:180]
        return row

    last_price = safe_float(ticker.get("lastPrice") or premium.get("markPrice"))
    price_1h, volume_1h, volume_change_1h = kline_1h_metrics(kline_1h, last_price)
    price_pct = safe_float(ticker.get("priceChangePercent"))
    quote_volume = safe_float(ticker.get("quoteVolume"))
    oi_native = safe_float(oi.get("openInterest"))
    oi_usd = oi_native * last_price
    oi_pct = oi_change_pct(oi_hist)
    funding = safe_float(premium.get("lastFundingRate"))
    ls = long_short.get(symbol, {})
    crowding_ratio = safe_float(ls.get("top_position_long_short_ratio")) or safe_float(ls.get("global_account_long_short_ratio"))
    label, reason = state_label(price_pct, oi_pct, funding, crowding_ratio, quote_volume)

    row.update(
        {
            "last_price": f"{last_price:.8g}",
            "price_change_pct_1h": f"{price_1h:.4f}",
            "price_change_pct_24h": f"{price_pct:.4f}",
            "quote_volume_usd_1h": f"{volume_1h:.2f}",
            "quote_volume_change_pct_1h": f"{volume_change_1h:.4f}",
            "quote_volume_usd_24h": f"{quote_volume:.2f}",
            "open_interest": f"{oi_native:.8f}",
            "open_interest_usd": f"{oi_usd:.2f}",
            "open_interest_change_pct_24h": f"{oi_pct:.4f}",
            "funding_rate": f"{funding:.8f}",
            "next_funding_time_china": ms_to_china(premium.get("nextFundingTime")),
            "top_position_long_short_ratio": str(ls.get("top_position_long_short_ratio") or ""),
            "global_account_long_short_ratio": str(ls.get("global_account_long_short_ratio") or ""),
            "taker_buy_sell_ratio": str(ls.get("taker_buy_sell_ratio") or ""),
            "crowding_bias": str(ls.get("crowding_bias") or ""),
            "market_state_label": label,
            "market_state_reason": reason,
            "quality_status": "ok",
            "raw_json": json.dumps({"ticker": ticker, "open_interest": oi, "premium": premium, "kline_1h_tail": kline_1h, "oi_hist_tail": oi_hist[-3:] if isinstance(oi_hist, list) else oi_hist}, ensure_ascii=False, separators=(",", ":")),
        }
    )
    return row


def amount_yi(value: Any) -> str:
    number = safe_float(value)
    return f"{number / 100_000_000:.2f} 亿美元"


def pct(value: Any) -> str:
    number = safe_float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.2f}%"


def render_markdown(rows: list[dict], summary: dict) -> str:
    ok_rows = [row for row in rows if row.get("quality_status") == "ok"]
    top_abs_price = sorted(ok_rows, key=lambda row: abs(safe_float(row.get("price_change_pct_24h"))), reverse=True)[:5]
    top_oi = sorted(ok_rows, key=lambda row: safe_float(row.get("open_interest_change_pct_24h")), reverse=True)[:5]
    top_funding = sorted(ok_rows, key=lambda row: abs(safe_float(row.get("funding_rate"))), reverse=True)[:5]
    lines = [
        "# v14 市场状态快照",
        "",
        f"- 观测时间：{summary.get('observed_at_china','-')}",
        f"- 覆盖市场：{summary.get('ok_rows','0')}/{summary.get('watchlist_rows','0')} 个",
        f"- 合约持仓合计：{amount_yi(summary.get('total_open_interest_usd'))}",
        f"- 24h成交额合计：{amount_yi(summary.get('total_quote_volume_usd_24h'))}",
        f"- BTC 24h：{pct(summary.get('btc_price_change_pct_24h'))}；ETH 24h：{pct(summary.get('eth_price_change_pct_24h'))}",
        "",
        "## 波动较大",
    ]
    lines.extend(
        f"- {row.get('asset_symbol')}: 价格 {pct(row.get('price_change_pct_24h'))}，持仓 {pct(row.get('open_interest_change_pct_24h'))}，{row.get('market_state_reason')}"
        for row in top_abs_price
    )
    lines.append("")
    lines.append("## 持仓变化")
    lines.extend(
        f"- {row.get('asset_symbol')}: 持仓 {pct(row.get('open_interest_change_pct_24h'))}，持仓规模 {amount_yi(row.get('open_interest_usd'))}"
        for row in top_oi
    )
    lines.append("")
    lines.append("## 资金费率偏离")
    lines.extend(
        f"- {row.get('asset_symbol')}: 资金费率 {safe_float(row.get('funding_rate')) * 100:.4f}%；{row.get('crowding_bias') or '拥挤度暂无'}"
        for row in top_funding
    )
    lines.append("")
    lines.append("说明：这是市场结构观察，不构成任何交易建议。")
    return "\n".join(lines) + "\n"


def build_summary(rows: list[dict], observed_utc: str) -> dict:
    ok_rows = [row for row in rows if row.get("quality_status") == "ok"]
    by_asset = {row.get("asset_symbol"): row for row in ok_rows}
    funding_extreme = [row for row in ok_rows if abs(safe_float(row.get("funding_rate"))) >= 0.0008]
    crowding = [
        row
        for row in ok_rows
        if safe_float(row.get("top_position_long_short_ratio")) >= 1.5
        or (0 < safe_float(row.get("top_position_long_short_ratio")) <= 0.67)
    ]
    top_price = max(ok_rows, key=lambda row: abs(safe_float(row.get("price_change_pct_24h"))), default={})
    top_oi = max(ok_rows, key=lambda row: safe_float(row.get("open_interest_change_pct_24h")), default={})
    return {
        "observed_at_utc": observed_utc,
        "observed_at_china": utc_to_china(observed_utc),
        "watchlist_rows": len(rows),
        "ok_rows": len(ok_rows),
        "skipped_rows": sum(1 for row in rows if row.get("quality_status") == "skipped"),
        "total_open_interest_usd": f"{sum(safe_float(row.get('open_interest_usd')) for row in ok_rows):.2f}",
        "total_quote_volume_usd_24h": f"{sum(safe_float(row.get('quote_volume_usd_24h')) for row in ok_rows):.2f}",
        "btc_price_change_pct_24h": by_asset.get("BTC", {}).get("price_change_pct_24h", ""),
        "eth_price_change_pct_24h": by_asset.get("ETH", {}).get("price_change_pct_24h", ""),
        "top_price_move_asset": top_price.get("asset_symbol", ""),
        "top_price_move_pct_24h": top_price.get("price_change_pct_24h", ""),
        "top_oi_change_asset": top_oi.get("asset_symbol", ""),
        "top_oi_change_pct_24h": top_oi.get("open_interest_change_pct_24h", ""),
        "funding_extreme_count": len(funding_extreme),
        "funding_extreme_assets": ";".join(row.get("asset_symbol", "") for row in funding_extreme[:8]),
        "crowding_extreme_count": len(crowding),
        "crowding_extreme_assets": ";".join(row.get("asset_symbol", "") for row in crowding[:8]),
        "status": "pass" if ok_rows else "warning",
    }


def main() -> int:
    args = parse_args()
    observed_utc = now_utc_iso()
    watch_rows = enabled_rows(read_rows(normalize_path(args.watchlist)))
    long_short = latest_long_short_by_symbol(normalize_path(args.long_short_input))
    session = requests.Session()
    session.trust_env = False

    rows = []
    for index, item in enumerate(watch_rows, start=1):
        symbol = str(item.get("binance_futures_symbol") or "").strip().upper()
        print(f"[{index}/{len(watch_rows)}] market_state symbol={symbol}")
        rows.append(build_row(session, item, observed_utc, long_short, args.oi_period, args.oi_limit))

    summary = build_summary(rows, observed_utc)
    write_rows(normalize_path(args.output), rows, COLUMNS)
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    normalize_path(args.markdown_output).write_text(render_markdown(rows, summary), encoding="utf-8")
    print(f"market_state_rows={len(rows)} ok={summary['ok_rows']} skipped={summary['skipped_rows']}")
    print(f"status={summary['status']}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
