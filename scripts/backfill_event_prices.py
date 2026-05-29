import argparse
import csv
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import pandas as pd
import requests

try:
    from utils.time_utils import (
        parse_any_time_to_utc_iso,
        utc_iso_to_china_iso,
        utc_ms_to_china_iso,
        utc_ms_to_utc_iso,
    )
except ModuleNotFoundError:
    from scripts.utils.time_utils import (
        parse_any_time_to_utc_iso,
        utc_iso_to_china_iso,
        utc_ms_to_china_iso,
        utc_ms_to_utc_iso,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_PATH = ROOT / "data" / "price_cache.sqlite"

TIME_OFFSETS_MS = {
    "t0": 0,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "24h": 24 * 60 * 60 * 1000,
    "72h": 72 * 60 * 60 * 1000,
}

RETURN_WINDOWS = ["1h", "4h", "24h", "72h"]

OUTPUT_COLUMNS = [
    "event_id",
    "event_time",
    "event_time_utc",
    "event_time_china",
    "title",
    "content",
    "source",
    "asset_symbol",
    "binance_spot_symbol",
    "binance_futures_symbol",
    "event_type",
    "event_subtype",
    "source_type",
    "direction_hint",
    "importance",
    "data_provider",
    "market_type",
    "symbol_used",
    "raw_backtest_mode",
    "price_target_t0_utc",
    "price_target_t0_china",
    "price_target_1h_utc",
    "price_target_1h_china",
    "price_target_4h_utc",
    "price_target_4h_china",
    "price_target_24h_utc",
    "price_target_24h_china",
    "price_target_72h_utc",
    "price_target_72h_china",
    "asset_price_t0_kline_time_utc",
    "asset_price_t0_kline_time_china",
    "asset_price_1h_kline_time_utc",
    "asset_price_1h_kline_time_china",
    "asset_price_4h_kline_time_utc",
    "asset_price_4h_kline_time_china",
    "asset_price_24h_kline_time_utc",
    "asset_price_24h_kline_time_china",
    "asset_price_72h_kline_time_utc",
    "asset_price_72h_kline_time_china",
    "btc_price_t0_kline_time_utc",
    "btc_price_t0_kline_time_china",
    "btc_price_1h_kline_time_utc",
    "btc_price_1h_kline_time_china",
    "btc_price_4h_kline_time_utc",
    "btc_price_4h_kline_time_china",
    "btc_price_24h_kline_time_utc",
    "btc_price_24h_kline_time_china",
    "btc_price_72h_kline_time_utc",
    "btc_price_72h_kline_time_china",
    "eth_price_t0_kline_time_utc",
    "eth_price_t0_kline_time_china",
    "eth_price_1h_kline_time_utc",
    "eth_price_1h_kline_time_china",
    "eth_price_4h_kline_time_utc",
    "eth_price_4h_kline_time_china",
    "eth_price_24h_kline_time_utc",
    "eth_price_24h_kline_time_china",
    "eth_price_72h_kline_time_utc",
    "eth_price_72h_kline_time_china",
    "asset_price_t0",
    "asset_price_1h",
    "asset_price_4h",
    "asset_price_24h",
    "asset_price_72h",
    "btc_price_t0",
    "btc_price_1h",
    "btc_price_4h",
    "btc_price_24h",
    "btc_price_72h",
    "eth_price_t0",
    "eth_price_1h",
    "eth_price_4h",
    "eth_price_24h",
    "eth_price_72h",
    "asset_return_1h",
    "asset_return_4h",
    "asset_return_24h",
    "asset_return_72h",
    "btc_return_1h",
    "btc_return_4h",
    "btc_return_24h",
    "btc_return_72h",
    "eth_return_1h",
    "eth_return_4h",
    "eth_return_24h",
    "eth_return_72h",
    "abnormal_vs_btc_1h",
    "abnormal_vs_btc_4h",
    "abnormal_vs_btc_24h",
    "abnormal_vs_btc_72h",
    "abnormal_vs_eth_1h",
    "abnormal_vs_eth_4h",
    "abnormal_vs_eth_24h",
    "abnormal_vs_eth_72h",
    "status",
    "skip_reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill post-event crypto prices from public Binance kline APIs."
    )
    parser.add_argument("--input", default=str(ROOT / "data" / "events_raw.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "event_price_backfill.csv"))
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cache", default=str(DEFAULT_CACHE_PATH))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--force-refresh", default="false")
    parser.add_argument(
        "--quality-output",
        default=str(ROOT / "results" / "event_quality_report.csv"),
        help="Optional path for writing a quality report after backfill.",
    )
    return parser.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def str_to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_event_time_to_ms(value: str) -> int:
    raw = parse_any_time_to_utc_iso(value)
    if not raw:
        raise ValueError(f"event_time is invalid: {value}")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return int(dt.timestamp() * 1000)


class PriceCache:
    def __init__(self, db_path: Path):
        ensure_parent(db_path)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_cache (
                provider TEXT NOT NULL,
                market_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                target_timestamp_ms INTEGER NOT NULL,
                kline_open_time_ms INTEGER NOT NULL,
                close_price REAL NOT NULL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (
                    provider,
                    market_type,
                    symbol,
                    interval,
                    target_timestamp_ms
                )
            )
            """
        )
        self.conn.commit()

    def get(
        self,
        provider: str,
        market_type: str,
        symbol: str,
        interval: str,
        target_timestamp_ms: int,
    ) -> Optional[Tuple[int, float, str]]:
        row = self.conn.execute(
            """
            SELECT kline_open_time_ms, close_price, raw_json
            FROM price_cache
            WHERE provider = ?
              AND market_type = ?
              AND symbol = ?
              AND interval = ?
              AND target_timestamp_ms = ?
            """,
            (provider, market_type, symbol, interval, target_timestamp_ms),
        ).fetchone()
        if not row:
            return None
        return int(row[0]), float(row[1]), str(row[2])

    def set(
        self,
        provider: str,
        market_type: str,
        symbol: str,
        interval: str,
        target_timestamp_ms: int,
        kline_open_time_ms: int,
        close_price: float,
        raw_json: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO price_cache (
                provider,
                market_type,
                symbol,
                interval,
                target_timestamp_ms,
                kline_open_time_ms,
                close_price,
                raw_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider,
                market_type,
                symbol,
                interval,
                target_timestamp_ms,
                kline_open_time_ms,
                close_price,
                raw_json,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


class BinanceKlineProvider:
    provider = "binance"
    interval_candidates = ["1m", "5m"]

    def __init__(
        self,
        cache: PriceCache,
        timeout: int = 10,
        max_retries: int = 3,
        force_refresh: bool = False,
    ):
        self.cache = cache
        self.timeout = timeout
        self.max_retries = max_retries
        self.force_refresh = force_refresh
        self.session = requests.Session()

    def get_close_after(
        self,
        market_type: str,
        symbol: str,
        target_timestamp_ms: int,
    ) -> Optional[Dict[str, object]]:
        symbol = str(symbol).strip().upper()
        if not symbol:
            return None

        for interval in self.interval_candidates:
            cached = None
            if not self.force_refresh:
                cached = self.cache.get(
                    self.provider, market_type, symbol, interval, target_timestamp_ms
                )
            if cached:
                kline_open_time_ms, close_price, raw_json = cached
                logging.debug(
                    "cache hit %s %s %s %s %s",
                    self.provider,
                    market_type,
                    symbol,
                    interval,
                    target_timestamp_ms,
                )
                return {
                    "provider": self.provider,
                    "market_type": market_type,
                    "symbol": symbol,
                    "interval": interval,
                    "target_timestamp_ms": target_timestamp_ms,
                    "kline_open_time_ms": kline_open_time_ms,
                    "close_price": close_price,
                    "raw_json": raw_json,
                    "from_cache": True,
                }

            kline = self._fetch_one_kline(market_type, symbol, interval, target_timestamp_ms)
            if not kline:
                continue

            kline_open_time_ms = int(kline[0])
            close_price = float(kline[4])
            raw_json = json.dumps(kline, ensure_ascii=False)
            self.cache.set(
                self.provider,
                market_type,
                symbol,
                interval,
                target_timestamp_ms,
                kline_open_time_ms,
                close_price,
                raw_json,
            )
            return {
                "provider": self.provider,
                "market_type": market_type,
                "symbol": symbol,
                "interval": interval,
                "target_timestamp_ms": target_timestamp_ms,
                "kline_open_time_ms": kline_open_time_ms,
                "close_price": close_price,
                "raw_json": raw_json,
                "from_cache": False,
            }

        return None

    def _fetch_one_kline(
        self,
        market_type: str,
        symbol: str,
        interval: str,
        target_timestamp_ms: int,
    ) -> Optional[list]:
        if market_type == "spot":
            url = "https://api.binance.com/api/v3/klines"
        elif market_type == "futures":
            url = "https://fapi.binance.com/fapi/v1/klines"
        else:
            raise ValueError(f"Unsupported market_type: {market_type}")

        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": target_timestamp_ms,
            "limit": 1,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                if response.status_code in {400, 404}:
                    logging.warning(
                        "%s %s %s returned %s: %s",
                        market_type,
                        symbol,
                        interval,
                        response.status_code,
                        response.text[:200],
                    )
                    return None
                response.raise_for_status()
                payload = response.json()
                if not payload:
                    return None
                return payload[0]
            except requests.RequestException as exc:
                logging.warning(
                    "request failed attempt=%s/%s market=%s symbol=%s interval=%s error=%s",
                    attempt,
                    self.max_retries,
                    market_type,
                    symbol,
                    interval,
                    exc,
                )
                if attempt < self.max_retries:
                    time.sleep(0.5 * attempt)
        return None


class CoinGeckoProviderPlaceholder:
    provider = "coingecko"

    def get_close_after(self, *_args, **_kwargs) -> Optional[Dict[str, object]]:
        return None


def load_symbol_map(symbol_map_path: Path) -> Dict[str, Dict[str, str]]:
    if not symbol_map_path.exists():
        logging.warning("symbol map not found: %s", symbol_map_path)
        return {}

    symbol_map = pd.read_csv(symbol_map_path, dtype=str).fillna("")
    mapped: Dict[str, Dict[str, str]] = {}
    for _, row in symbol_map.iterrows():
        asset_symbol = str(row.get("asset_symbol", "")).strip().upper()
        if not asset_symbol:
            continue
        mapped[asset_symbol] = {
            "binance_spot_symbol": str(row.get("binance_spot_symbol", "")).strip().upper(),
            "binance_futures_symbol": str(row.get("binance_futures_symbol", "")).strip().upper(),
            "coingecko_id": str(row.get("coingecko_id", "")).strip(),
            "notes": str(row.get("notes", "")).strip(),
        }
    return mapped


def apply_symbol_mapping(
    row: pd.Series,
    symbol_map: Dict[str, Dict[str, str]],
) -> Tuple[pd.Series, Optional[str]]:
    enriched = row.copy()
    asset_symbol = str(enriched.get("asset_symbol", "") or "").strip().upper()
    spot_symbol = str(enriched.get("binance_spot_symbol", "") or "").strip().upper()
    futures_symbol = str(enriched.get("binance_futures_symbol", "") or "").strip().upper()

    enriched["asset_symbol"] = asset_symbol
    enriched["binance_spot_symbol"] = spot_symbol
    enriched["binance_futures_symbol"] = futures_symbol

    if spot_symbol or futures_symbol:
        return enriched, None
    if not asset_symbol:
        return enriched, "missing_asset_symbol"

    mapped = symbol_map.get(asset_symbol)
    if mapped is None:
        return enriched, "missing_symbol_mapping"

    enriched["binance_spot_symbol"] = mapped.get("binance_spot_symbol", "")
    enriched["binance_futures_symbol"] = mapped.get("binance_futures_symbol", "")
    if not enriched["binance_spot_symbol"] and not enriched["binance_futures_symbol"]:
        return enriched, "unsupported_symbol"

    return enriched, None


def choose_symbol(row: pd.Series) -> Iterable[Tuple[str, str]]:
    spot_symbol = str(row.get("binance_spot_symbol", "") or "").strip().upper()
    futures_symbol = str(row.get("binance_futures_symbol", "") or "").strip().upper()
    if spot_symbol:
        yield "spot", spot_symbol
    if futures_symbol:
        yield "futures", futures_symbol


def reference_symbol(symbol: str) -> Iterable[Tuple[str, str]]:
    yield "spot", symbol
    yield "futures", symbol


def fetch_price_series(
    provider: BinanceKlineProvider,
    candidates: Iterable[Tuple[str, str]],
    event_timestamp_ms: int,
) -> Tuple[Dict[str, Optional[float]], Dict[str, str], Dict[str, Optional[int]], Optional[str]]:
    prices: Dict[str, Optional[float]] = {label: None for label in TIME_OFFSETS_MS}
    kline_open_times: Dict[str, Optional[int]] = {label: None for label in TIME_OFFSETS_MS}
    meta: Dict[str, str] = {"provider": "", "market_type": "", "symbol": ""}
    tried = []

    for market_type, symbol in candidates:
        tried.append(f"{market_type}:{symbol}")
        local_prices: Dict[str, Optional[float]] = {}
        first_result = None
        for label, offset_ms in TIME_OFFSETS_MS.items():
            result = provider.get_close_after(market_type, symbol, event_timestamp_ms + offset_ms)
            local_prices[label] = None if result is None else float(result["close_price"])
            if result is not None:
                kline_open_times[label] = int(result["kline_open_time_ms"])
            if result and first_result is None:
                first_result = result

        if any(value is not None for value in local_prices.values()):
            prices.update(local_prices)
            meta = {
                "provider": provider.provider,
                "market_type": market_type,
                "symbol": symbol,
            }
            return prices, meta, kline_open_times, None

    return prices, meta, kline_open_times, "no price data for candidates: " + ", ".join(tried or ["none"])


def calc_return(price_now: Optional[float], price_t0: Optional[float]) -> Optional[float]:
    if price_now is None or price_t0 in (None, 0):
        return None
    return price_now / price_t0 - 1


def maybe_subtract(left: Optional[float], right: Optional[float]) -> Optional[float]:
    if left is None or right is None:
        return None
    return left - right


def to_csv_value(value):
    if value is None:
        return ""
    return value


def process_event(
    row: pd.Series,
    provider: BinanceKlineProvider,
    symbol_map: Dict[str, Dict[str, str]],
) -> Dict[str, object]:
    row, mapping_reason = apply_symbol_mapping(row, symbol_map)
    out = {column: "" for column in OUTPUT_COLUMNS}
    for column in [
        "event_id",
        "event_time",
        "event_time_utc",
        "event_time_china",
        "title",
        "content",
        "source",
        "asset_symbol",
        "binance_spot_symbol",
        "binance_futures_symbol",
        "event_type",
        "event_subtype",
        "source_type",
        "direction_hint",
        "importance",
        "raw_backtest_mode",
    ]:
        out[column] = row.get(column, "")
    if not out["raw_backtest_mode"]:
        out["raw_backtest_mode"] = "published_after_event"

    reasons = []
    if mapping_reason:
        out["status"] = "skipped"
        out["skip_reason"] = mapping_reason
        return out

    event_time_utc = parse_any_time_to_utc_iso(
        str(row.get("event_time_utc", "") or row.get("event_time", ""))
    )
    event_time_china = utc_iso_to_china_iso(event_time_utc)
    out["event_time_utc"] = event_time_utc
    out["event_time_china"] = event_time_china
    if event_time_china:
        out["event_time"] = event_time_china

    try:
        event_timestamp_ms = parse_event_time_to_ms(event_time_utc or str(row.get("event_time", "")))
    except Exception as exc:
        out["status"] = "skipped"
        out["skip_reason"] = f"invalid event_time: {exc}"
        return out

    for label, offset_ms in TIME_OFFSETS_MS.items():
        target_ms = event_timestamp_ms + offset_ms
        out[f"price_target_{label}_utc"] = utc_ms_to_utc_iso(target_ms)
        out[f"price_target_{label}_china"] = utc_ms_to_china_iso(target_ms)

    asset_prices, asset_meta, asset_kline_times, asset_reason = fetch_price_series(
        provider, choose_symbol(row), event_timestamp_ms
    )
    btc_prices, _btc_meta, btc_kline_times, btc_reason = fetch_price_series(
        provider, reference_symbol("BTCUSDT"), event_timestamp_ms
    )
    eth_prices, _eth_meta, eth_kline_times, eth_reason = fetch_price_series(
        provider, reference_symbol("ETHUSDT"), event_timestamp_ms
    )

    if asset_reason:
        reasons.append("unsupported_symbol")
        reasons.append(f"asset: {asset_reason}")
    if btc_reason:
        reasons.append(f"btc: {btc_reason}")
    if eth_reason:
        reasons.append(f"eth: {eth_reason}")

    out["data_provider"] = asset_meta["provider"]
    out["market_type"] = asset_meta["market_type"]
    out["symbol_used"] = asset_meta["symbol"]

    for label in TIME_OFFSETS_MS:
        out[f"asset_price_{label}"] = to_csv_value(asset_prices[label])
        out[f"btc_price_{label}"] = to_csv_value(btc_prices[label])
        out[f"eth_price_{label}"] = to_csv_value(eth_prices[label])
        for prefix, times in [
            ("asset", asset_kline_times),
            ("btc", btc_kline_times),
            ("eth", eth_kline_times),
        ]:
            kline_ms = times.get(label)
            out[f"{prefix}_price_{label}_kline_time_utc"] = utc_ms_to_utc_iso(kline_ms) if kline_ms else ""
            out[f"{prefix}_price_{label}_kline_time_china"] = utc_ms_to_china_iso(kline_ms) if kline_ms else ""

    asset_returns = {
        window: calc_return(asset_prices[window], asset_prices["t0"])
        for window in RETURN_WINDOWS
    }
    btc_returns = {
        window: calc_return(btc_prices[window], btc_prices["t0"])
        for window in RETURN_WINDOWS
    }
    eth_returns = {
        window: calc_return(eth_prices[window], eth_prices["t0"])
        for window in RETURN_WINDOWS
    }

    for window in RETURN_WINDOWS:
        out[f"asset_return_{window}"] = to_csv_value(asset_returns[window])
        out[f"btc_return_{window}"] = to_csv_value(btc_returns[window])
        out[f"eth_return_{window}"] = to_csv_value(eth_returns[window])
        out[f"abnormal_vs_btc_{window}"] = to_csv_value(
            maybe_subtract(asset_returns[window], btc_returns[window])
        )
        out[f"abnormal_vs_eth_{window}"] = to_csv_value(
            maybe_subtract(asset_returns[window], eth_returns[window])
        )

    expected_price_columns = [
        f"{prefix}_price_{label}"
        for prefix in ["asset", "btc", "eth"]
        for label in TIME_OFFSETS_MS
    ]
    has_any_asset_return = any(out[f"asset_return_{window}"] != "" for window in RETURN_WINDOWS)
    missing_prices = [column for column in expected_price_columns if out[column] == ""]

    if not has_any_asset_return:
        out["status"] = "skipped"
        if not reasons:
            reasons.append("asset has no computable return")
    elif missing_prices:
        out["status"] = "partial"
        reasons.append("missing prices: " + ", ".join(missing_prices))
    else:
        out["status"] = "ok"

    out["skip_reason"] = "; ".join(reasons)
    return out


def write_rows(output_path: Path, rows: Iterable[Dict[str, object]]) -> None:
    ensure_parent(output_path)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    cache_path = normalize_path(args.cache)
    symbol_map_path = normalize_path(args.symbol_map)
    quality_output_path = normalize_path(args.quality_output) if args.quality_output else None
    force_refresh = str_to_bool(args.force_refresh)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1
    logging.info("input file: %s", input_path.name)

    if args.dry_run:
        logging.info("dry run: would read %s and write %s", input_path, output_path)
        logging.info("dry run: would use cache %s", cache_path)
        logging.info("dry run: would use symbol map %s", symbol_map_path)
        logging.info("dry run: force_refresh=%s", force_refresh)
        return 0

    events = pd.read_csv(input_path, dtype=str).fillna("")
    if args.limit and args.limit > 0:
        events = events.head(args.limit)

    cache = PriceCache(cache_path)
    provider = BinanceKlineProvider(cache, force_refresh=force_refresh)
    symbol_map = load_symbol_map(symbol_map_path)
    rows = []

    try:
        total = len(events)
        for idx, row in events.iterrows():
            event_id = row.get("event_id", f"row_{idx}")
            try:
                result = process_event(row, provider, symbol_map)
                rows.append(result)
                message = (
                    f"[{len(rows)}/{total}] event_id={result.get('event_id', '')} "
                    f"asset={result.get('asset_symbol', '')} status={result.get('status', '')}"
                )
                if result.get("status") != "ok" and result.get("skip_reason"):
                    message += f" reason={result.get('skip_reason')}"
                logging.info(message)
            except Exception as exc:
                logging.exception("event failed event_id=%s", event_id)
                failed = {column: "" for column in OUTPUT_COLUMNS}
                for column in [
                    "event_id",
                    "event_time",
                    "title",
                    "content",
                    "source",
                    "asset_symbol",
                    "binance_spot_symbol",
                    "binance_futures_symbol",
                    "event_type",
                    "event_subtype",
                    "source_type",
                    "direction_hint",
                    "importance",
                    "raw_backtest_mode",
                ]:
                    failed[column] = row.get(column, "")
                if not failed["raw_backtest_mode"]:
                    failed["raw_backtest_mode"] = "published_after_event"
                failed["status"] = "skipped"
                failed["skip_reason"] = f"unhandled error: {exc}"
                rows.append(failed)
    finally:
        cache.close()

    write_rows(output_path, rows)
    logging.info("wrote %s rows to %s", len(rows), output_path)
    if quality_output_path:
        try:
            from validate_backfill_results import build_quality_report

            report = build_quality_report(pd.DataFrame(rows))
            ensure_parent(quality_output_path)
            report.to_csv(quality_output_path, index=False)
            logging.info("wrote quality report to %s", quality_output_path)
        except Exception as exc:
            logging.warning("could not write quality report: %s", exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
