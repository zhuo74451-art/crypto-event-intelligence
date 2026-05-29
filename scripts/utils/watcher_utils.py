import csv
import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

try:
    from utils.time_utils import utc_iso_to_china_iso
except ModuleNotFoundError:
    from scripts.utils.time_utils import utc_iso_to_china_iso


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ETHERSCAN_V2_URL = "https://api.etherscan.io/v2/api"
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"

STABLE_SYMBOLS = {"USDT", "USDC", "DAI", "BUSD", "TUSD", "USDP", "FDUSD"}
SYMBOL_ALIASES = {
    "WETH": "ETH",
    "WBTC": "BTC",
}

ALERT_COLUMNS = [
    "alert_id",
    "observed_at_utc",
    "observed_at_china",
    "source_type",
    "watcher_source",
    "blockchain",
    "block_number",
    "tx_hash",
    "log_index",
    "primary_entity",
    "primary_address",
    "counterparty_entity",
    "counterparty_address",
    "asset_symbol",
    "token_address",
    "amount_native",
    "amount_usd",
    "metric_type",
    "metric_value",
    "metric_change_pct",
    "event_type_l1",
    "event_type_l2",
    "risk_category",
    "confidence",
    "relevance_score",
    "threshold_rule",
    "dedupe_key",
    "needs_model_review",
    "model_review_reason",
    "publish_route",
    "status",
    "skip_reason",
    "raw_json",
]


def redact_secret(text: Any) -> str:
    redacted = str(text or "")
    redacted = re.sub(r"apikey=[A-Za-z0-9_-]+", "apikey=<redacted>", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"api_key=[A-Za-z0-9_-]+", "api_key=<redacted>", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"sk-or-v1-[A-Za-z0-9_-]+", "sk-or-v1-<redacted>", redacted)
    return redacted


def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root_dir() / path
    return path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def dt_to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def epoch_to_utc_iso(value: Any) -> str:
    try:
        return dt_to_utc_iso(datetime.fromtimestamp(int(value), tz=timezone.utc))
    except Exception:
        return ""


def utc_iso_to_epoch(value: str) -> int:
    raw = str(value or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return int(datetime.fromisoformat(raw).timestamp())


def utc_iso_to_china(value: str) -> str:
    return utc_iso_to_china_iso(value)


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_csv_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    ensure_parent(path)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def address_key(value: str) -> str:
    return str(value or "").strip().lower()


def is_enabled(row: dict) -> bool:
    return str(row.get("enabled", "")).strip().lower() in {"1", "true", "yes", "y"}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def token_amount(raw_value: Any, decimals: Any) -> float:
    try:
        return int(str(raw_value)) / (10 ** int(str(decimals)))
    except Exception:
        return 0.0


def compact_number(value: float) -> str:
    value = float(value or 0)
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:.2f}K"
    return f"${value:.2f}"


def make_alert_id(*parts: Any) -> str:
    raw = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"fh_{digest}"


def make_dedupe_key(*parts: Any) -> str:
    raw = "|".join(str(part or "") for part in parts)
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]


def request_json(url: str, params: dict | None = None, timeout: int = 15, retries: int = 3) -> dict | list:
    last_error = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code < 500:
                response.raise_for_status()
                return response.json()
            last_error = RuntimeError(f"http {response.status_code}: {response.text[:200]}")
        except Exception as exc:
            last_error = exc
        time.sleep(min(2 * attempt, 8))
    raise RuntimeError(f"request failed: {last_error}")


def etherscan_token_transfers(
    address: str,
    api_key: str,
    chain_id: str = "1",
    start_block: int = 0,
    end_block: int = 99999999,
    page: int = 1,
    offset: int = 100,
    sort: str = "desc",
) -> list[dict]:
    params = {
        "chainid": chain_id,
        "module": "account",
        "action": "tokentx",
        "address": address,
        "startblock": start_block,
        "endblock": end_block,
        "page": page,
        "offset": offset,
        "sort": sort,
        "apikey": api_key,
    }
    payload = request_json(ETHERSCAN_V2_URL, params=params)
    if not isinstance(payload, dict):
        raise RuntimeError("unexpected Etherscan response")
    status = str(payload.get("status", ""))
    message = str(payload.get("message", ""))
    result = payload.get("result", [])
    if status == "0" and isinstance(result, str):
        if "No transactions found" in result:
            return []
        raise RuntimeError(f"Etherscan error: {message}; {result}")
    if not isinstance(result, list):
        raise RuntimeError(f"unexpected Etherscan result: {result}")
    return result


def load_symbol_map(path: Path) -> dict[str, dict]:
    rows = read_csv_rows(path)
    output = {}
    for row in rows:
        symbol = str(row.get("asset_symbol", "")).strip().upper()
        if symbol:
            output[symbol] = row
    return output


def fetch_binance_price(symbol: str, symbol_map: dict[str, dict]) -> float:
    normalized = SYMBOL_ALIASES.get(str(symbol or "").strip().upper(), str(symbol or "").strip().upper())
    if normalized in STABLE_SYMBOLS:
        return 1.0
    item = symbol_map.get(normalized, {})
    pair = str(item.get("binance_spot_symbol", "") or item.get("binance_futures_symbol", "")).strip().upper()
    if not pair:
        return 0.0
    try:
        payload = request_json(BINANCE_TICKER_URL, params={"symbol": pair}, timeout=10, retries=2)
        if isinstance(payload, dict):
            return safe_float(payload.get("price"))
    except Exception:
        return 0.0
    return 0.0


def estimate_usd(symbol: str, amount_native: float, symbol_map: dict[str, dict]) -> tuple[float, float]:
    price = fetch_binance_price(symbol, symbol_map)
    if not price:
        return 0.0, 0.0
    return amount_native * price, price


def write_summary(path: Path, summary: dict) -> None:
    write_csv_rows(path, [summary], list(summary.keys()))


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def sample_transfer_alerts() -> list[dict]:
    # Use mature sample timestamps so local no-key validation can exercise
    # 1h/4h/24h/72h price backfill. Live watcher rows use actual chain time.
    observed = dt_to_utc_iso(now_utc() - timedelta(hours=96))
    china = utc_iso_to_china(observed)
    rows = [
        {
            "source_type": "first_hand",
            "watcher_source": "sample_eth_address_transfers",
            "blockchain": "ethereum",
            "block_number": "sample",
            "tx_hash": "sample_tx_large_eth_transfer",
            "log_index": "0",
            "primary_entity": "Binance",
            "primary_address": "0x28C6c06298d514Db089934071355E5743bf21d60",
            "counterparty_entity": "unknown",
            "counterparty_address": "0x000000000000000000000000000000000000dEaD",
            "asset_symbol": "ETH",
            "token_address": "native_or_weth",
            "amount_native": "2500",
            "amount_usd": "9500000",
            "metric_type": "transfer_out",
            "metric_value": "9500000",
            "metric_change_pct": "",
            "event_type_l1": "onchain_transfer",
            "event_type_l2": "watched_address_transfer",
            "risk_category": "cex_flow",
            "confidence": "sample",
            "relevance_score": "0.82",
            "threshold_rule": "sample_amount_usd>=5000000",
            "needs_model_review": "false",
            "model_review_reason": "",
            "publish_route": "review",
            "status": "ok",
            "skip_reason": "",
        },
        {
            "source_type": "first_hand",
            "watcher_source": "sample_eth_address_transfers",
            "blockchain": "ethereum",
            "block_number": "sample",
            "tx_hash": "sample_tx_protocol_treasury",
            "log_index": "0",
            "primary_entity": "Aave",
            "primary_address": "0x25F2226B597E8F9514B3F68F00f494cF4f286491",
            "counterparty_entity": "unknown",
            "counterparty_address": "0x000000000000000000000000000000000000bEEF",
            "asset_symbol": "AAVE",
            "token_address": "sample_aave_token",
            "amount_native": "12000",
            "amount_usd": "2400000",
            "metric_type": "treasury_transfer_out",
            "metric_value": "2400000",
            "metric_change_pct": "",
            "event_type_l1": "onchain_transfer",
            "event_type_l2": "protocol_treasury_outflow",
            "risk_category": "protocol_treasury",
            "confidence": "sample",
            "relevance_score": "0.74",
            "threshold_rule": "sample_amount_usd>=2000000",
            "needs_model_review": "true",
            "model_review_reason": "protocol_treasury_outflow",
            "publish_route": "review",
            "status": "ok",
            "skip_reason": "",
        },
    ]
    output = []
    for row in rows:
        item = {column: "" for column in ALERT_COLUMNS}
        item.update(row)
        item["observed_at_utc"] = observed
        item["observed_at_china"] = china
        item["dedupe_key"] = make_dedupe_key(item["primary_address"], item["tx_hash"], item["asset_symbol"])
        item["alert_id"] = make_alert_id(item["watcher_source"], item["tx_hash"], item["primary_address"], item["asset_symbol"])
        item["raw_json"] = json_dumps({"sample": True})
        output.append(item)
    return output


def sample_stablecoin_alerts() -> list[dict]:
    # Use mature sample timestamps so local no-key validation can exercise
    # 1h/4h/24h/72h price backfill. Live watcher rows use actual chain time.
    observed = dt_to_utc_iso(now_utc() - timedelta(hours=96))
    china = utc_iso_to_china(observed)
    rows = [
        {
            "source_type": "first_hand",
            "watcher_source": "sample_stablecoin_mint_burn",
            "blockchain": "ethereum",
            "block_number": "sample",
            "tx_hash": "sample_tx_usdt_mint",
            "log_index": "0",
            "primary_entity": "Tether",
            "primary_address": "0x5754284f345afc66a98fbb0a0afe71e0f007b949",
            "counterparty_entity": "zero_address",
            "counterparty_address": ZERO_ADDRESS,
            "asset_symbol": "USDT",
            "token_address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "amount_native": "100000000",
            "amount_usd": "100000000",
            "metric_type": "stablecoin_mint",
            "metric_value": "100000000",
            "metric_change_pct": "",
            "event_type_l1": "stablecoin_flow",
            "event_type_l2": "stablecoin_mint",
            "risk_category": "supply_change",
            "confidence": "sample",
            "relevance_score": "0.9",
            "threshold_rule": "sample_mint_usd>=50000000",
            "needs_model_review": "false",
            "model_review_reason": "",
            "publish_route": "review",
            "status": "ok",
            "skip_reason": "",
        }
    ]
    output = []
    for row in rows:
        item = {column: "" for column in ALERT_COLUMNS}
        item.update(row)
        item["observed_at_utc"] = observed
        item["observed_at_china"] = china
        item["dedupe_key"] = make_dedupe_key(item["token_address"], item["tx_hash"], item["metric_type"])
        item["alert_id"] = make_alert_id(item["watcher_source"], item["tx_hash"], item["token_address"], item["metric_type"])
        item["raw_json"] = json_dumps({"sample": True})
        output.append(item)
    return output
