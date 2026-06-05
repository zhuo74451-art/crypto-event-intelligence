"""Market Radar v1.16-I — Liquidation Pressure Proxy Real Free API TG Test Send (One-Shot)

Fetches real market data from Binance PUBLIC endpoints (NO API key required),
computes liquidation_pressure proxy signals per asset using conservative proxy
indicators (funding rate, OI change, long/short ratio, taker buy/sell ratio),
generates cards, runs quality gate and send-readiness gate, then attempts
ONE-SHOT TG test-group send if credentials are available.

THIS IS REAL EXTERNAL API + REAL TG TEST SEND (one-shot only).
Not fixture. Not production. Not daemon/loop.

IMPORTANT: Binance REST does NOT provide direct liquidation order data.
This runner uses CONSERVATIVE PROXY indicators. Cards MUST explicitly state
"清算压力代理信号" — they are NOT real liquidation tape data.

Free API sources (all Binance public, no key needed):
  - GET /api/v3/ticker/24hr                              → 24hr spot price change, volume
  - GET /fapi/v1/ticker/24hr                              → futures 24hr ticker
  - GET /fapi/v1/openInterest                             → current open interest
  - GET /fapi/v1/openInterestHist                         → historical OI (for OI change %)
  - GET /fapi/v1/fundingRate                              → latest funding rate
  - GET /futures/data/globalLongShortAccountRatio         → long/short ratio (if available)
  - GET /futures/data/takerlongshortRatio                 → taker buy/sell ratio (if available)

Assets: BTCUSDT, ETHUSDT, SOLUSDT (minimum 3 assets)

Liquidation pressure proxy admission (conservative):
  - price move >= 4% AND at least 2 confirmation factors → admission_passed
  - price move >= 5% AND at least 1 confirmation factor → admission_passed
  - If key proxy indicators insufficient → blocked_gate_not_passed
  - If no asset reaches threshold → no TG send

Outputs:
  results/market_radar_v116i_liquidation_pressure_raw_snapshots.json
  results/market_radar_v116i_liquidation_pressure_signal_records.jsonl
  results/market_radar_v116i_liquidation_pressure_card_records.jsonl
  results/market_radar_v116i_liquidation_pressure_quality_gate_records.jsonl
  results/market_radar_v116i_liquidation_pressure_send_readiness_records.jsonl
  results/market_radar_v116i_liquidation_pressure_tg_send_attempts.jsonl
  results/market_radar_v116i_liquidation_pressure_tg_test_send_result.json
  runs/market_radar/v116i_liquidation_pressure_card_preview.md
  runs/market_radar/v116i_liquidation_pressure_tg_test_send_report.md
  runs/market_radar/v116i_liquidation_pressure_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v116i_liquidation_pressure_real_free_api_tg_test_send_one_shot.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

import requests

# ── Project root ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── Constants ────────────────────────────────────────────────────────────
CARD_FAMILY = "liquidation_pressure"
VERSION = "v1.16-I"
STAGE = "v116i_liquidation_pressure_real_free_api_tg_test_send_one_shot"
TASK_ID = "20260605_v116i_liquidation_pressure_real_free_api_tg_test_send_one_shot"
RUN_ID = "20260605_124925"
CN_TZ = timezone(timedelta(hours=8))

# Assets to fetch
TARGET_ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
ASSET_LABELS = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL"}

# ── Free public API endpoints (NO API key needed) ────────────────────────
BINANCE_SPOT_TICKER_24HR = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_FUTURES_TICKER_24HR = "https://fapi.binance.com/fapi/v1/ticker/24hr"
BINANCE_FUTURES_OPEN_INTEREST = "https://fapi.binance.com/fapi/v1/openInterest"
BINANCE_FUTURES_OI_HIST = "https://fapi.binance.com/fapi/v1/openInterestHist"
BINANCE_FUTURES_FUNDING_RATE = "https://fapi.binance.com/fapi/v1/fundingRate"
BINANCE_FUTURES_LS_RATIO = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
BINANCE_FUTURES_TAKER_RATIO = "https://fapi.binance.com/futures/data/takerlongshortRatio"

# ── Liquidation pressure proxy admission thresholds ─────────────────────
ADMISSION_PRICE_THRESHOLD_PCT = 4.0       # >= 4% + 2 confirmation factors
ADMISSION_WEAK_PRICE_THRESHOLD_PCT = 5.0  # >= 5% + 1 confirmation factor
VOLUME_CONFIRMATION_THRESHOLD_USD = 500_000_000  # $500M quote volume as confirmation

# Funding rate extreme thresholds (absolute value, as decimal)
FUNDING_EXTREME_BTC_ETH = 0.0005   # 0.05% — extreme for BTC/ETH
FUNDING_EXTREME_SOL = 0.0010       # 0.10% — extreme for SOL

# OI change threshold for confirmation
OI_CHANGE_CONFIRM_THRESHOLD_PCT = 2.0  # >= 2% OI change

# Long/short ratio extreme thresholds
LS_RATIO_BULLISH = 1.2   # > 1.2 = bullish (long dominant)
LS_RATIO_BEARISH = 0.8   # < 0.8 = bearish (short dominant)

# Taker buy/sell ratio thresholds
TAKER_RATIO_BUY = 1.2    # > 1.2 = buying pressure
TAKER_RATIO_SELL = 0.8   # < 0.8 = selling pressure

# ── Output paths ─────────────────────────────────────────────────────────
OUTPUT_DIR = ROOT / "results"
RUNS_DIR = ROOT / "runs" / "market_radar"

RAW_SNAPSHOTS_JSON = OUTPUT_DIR / "market_radar_v116i_liquidation_pressure_raw_snapshots.json"
SIGNAL_RECORDS_JSONL = OUTPUT_DIR / "market_radar_v116i_liquidation_pressure_signal_records.jsonl"
CARD_RECORDS_JSONL = OUTPUT_DIR / "market_radar_v116i_liquidation_pressure_card_records.jsonl"
QUALITY_GATE_JSONL = OUTPUT_DIR / "market_radar_v116i_liquidation_pressure_quality_gate_records.jsonl"
SEND_READINESS_JSONL = OUTPUT_DIR / "market_radar_v116i_liquidation_pressure_send_readiness_records.jsonl"
TG_SEND_ATTEMPTS_JSONL = OUTPUT_DIR / "market_radar_v116i_liquidation_pressure_tg_send_attempts.jsonl"
SEND_RESULT_JSON = OUTPUT_DIR / "market_radar_v116i_liquidation_pressure_tg_test_send_result.json"
CARD_PREVIEW_MD = RUNS_DIR / "v116i_liquidation_pressure_card_preview.md"
SEND_REPORT_MD = RUNS_DIR / "v116i_liquidation_pressure_tg_test_send_report.md"
HANDOFF_MD = RUNS_DIR / "v116i_liquidation_pressure_local_only_handoff.md"

# ── Safety flags (will be populated during execution) ─────────────────────
SAFETY = {
    "real_external_api_called": False,
    "fixture_only": False,
    "production_send_ready": False,
    "prod_state_write": False,
    "ai_model_called": False,
    "credentials_printed": False,
    "credentials_read_plaintext": False,
    "daemon_or_loop_started": False,
    "files_deleted": False,
    "tg_test_sent": False,
    "tg_message_id_redacted": None,
    "api_key_required": False,
    "api_source": "Binance public REST endpoints (no API key)",
    "secret_preflight_run": False,
    "telegram_bot_token_present": False,
    "telegram_chat_id_present": False,
    "secret_preflight_passed": False,
}


def generate_timestamp() -> str:
    return datetime.now(CN_TZ).isoformat()


def hash_value(value: str) -> str:
    """Hash a value with sha256 for redacted logging. Never returns raw value."""
    if not value:
        return "sha256:empty"
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════
# Step 0: SAFE SECRET PREFLIGHT
# ══════════════════════════════════════════════════════════════════════════

def safe_secret_preflight() -> dict:
    """Check boolean presence of TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.

    CRITICAL SAFETY RULES (enforced by this function):
      1. NEVER print, echo, write, or log the values of the tokens/IDs.
      2. ONLY output boolean presence: true/false.
      3. NEVER store the raw values in any file or variable beyond this check.
      4. If present, values stay in os.environ only (set by load_local_secrets.ps1).

    Returns:
        dict with boolean flags only.
    """
    print("=" * 70)
    print("[0] SAFE SECRET PREFLIGHT")
    print("=" * 70)
    print("  Checking TG credential presence (BOOLEAN ONLY — no values printed)...")

    bot_token_present = bool(os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    chat_id_present = bool(os.environ.get("TELEGRAM_CHAT_ID", ""))

    print(f"  telegram_bot_token_present: {bot_token_present}")
    print(f"  telegram_chat_id_present: {chat_id_present}")

    preflight_passed = bot_token_present and chat_id_present

    if preflight_passed:
        print("  [PREFLIGHT PASS] Both TG credentials present. TG test send will be attempted.")
    else:
        missing = []
        if not bot_token_present:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not chat_id_present:
            missing.append("TELEGRAM_CHAT_ID")
        print(f"  [PREFLIGHT BLOCKED] Missing: {', '.join(missing)}")
        print("  Will generate card + gates but TG send will be blocked.")

    SAFETY["secret_preflight_run"] = True
    SAFETY["telegram_bot_token_present"] = bot_token_present
    SAFETY["telegram_chat_id_present"] = chat_id_present
    SAFETY["secret_preflight_passed"] = preflight_passed

    if preflight_passed:
        SAFETY["credentials_read_plaintext"] = True

    print()
    return {
        "telegram_bot_token_present": bot_token_present,
        "telegram_chat_id_present": chat_id_present,
        "preflight_passed": preflight_passed,
        "preflight_timestamp": generate_timestamp(),
        "note": "Only boolean presence checked. Raw values never printed/logged/stored.",
    }


# ══════════════════════════════════════════════════════════════════════════
# Step 1: Fetch real market data from Binance public API
# ══════════════════════════════════════════════════════════════════════════

def fetch_binance_spot_24hr_tickers() -> dict[str, dict]:
    """Fetch 24hr ticker stats from Binance spot (public, no API key)."""
    print("[1a] Fetching Binance SPOT 24hr tickers...")
    try:
        resp = requests.get(BINANCE_SPOT_TICKER_24HR, timeout=15)
        resp.raise_for_status()
        all_tickers = resp.json()
        target_map = {t["symbol"]: t for t in all_tickers if t["symbol"] in TARGET_ASSETS}
        for sym in TARGET_ASSETS:
            if sym in target_map:
                t = target_map[sym]
                print(f"  {sym}: price={t['lastPrice']}, 24h_change={t['priceChangePercent']}%, "
                      f"vol={t['quoteVolume']}")
            else:
                print(f"  {sym}: NOT FOUND in spot tickers")
        return target_map
    except Exception as e:
        print(f"  ERROR fetching spot tickers: {e}")
        return {}


def fetch_binance_futures_24hr_tickers() -> dict[str, dict]:
    """Fetch 24hr ticker stats from Binance futures (public, no API key)."""
    print("[1b] Fetching Binance FUTURES 24hr tickers...")
    try:
        resp = requests.get(BINANCE_FUTURES_TICKER_24HR, timeout=15)
        resp.raise_for_status()
        all_tickers = resp.json()
        target_map = {t["symbol"]: t for t in all_tickers if t["symbol"] in TARGET_ASSETS}
        for sym in TARGET_ASSETS:
            if sym in target_map:
                t = target_map[sym]
                print(f"  {sym}: price={t['lastPrice']}, 24h_change={t['priceChangePercent']}%, "
                      f"vol={t['quoteVolume']}")
            else:
                print(f"  {sym}: NOT FOUND in futures tickers")
        return target_map
    except Exception as e:
        print(f"  ERROR fetching futures tickers: {e}")
        return {}


def fetch_binance_open_interest() -> dict[str, dict]:
    """Fetch current open interest from Binance futures (public, no API key)."""
    print("[1c] Fetching Binance futures open interest...")
    results = {}
    for sym in TARGET_ASSETS:
        try:
            resp = requests.get(
                BINANCE_FUTURES_OPEN_INTEREST,
                params={"symbol": sym},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            results[sym] = data
            print(f"  {sym}: openInterest={data.get('openInterest', '?')}, "
                  f"time={data.get('time', '?')}")
        except Exception as e:
            print(f"  {sym}: ERROR fetching open interest: {e}")
    return results


def fetch_binance_oi_history() -> dict[str, dict]:
    """Fetch recent OI history to compute OI change % (public, no API key).

    Returns a dict with per-symbol entries:
        {
            "symbol": {
                "data": [...],
                "oi_change_pct": float | None,
                "oi_history_available": bool,
                "fallback_reason": str | None,
            }
        }
    """
    print("[1d] Fetching Binance futures OI history (for OI change %)...")
    results = {}
    for sym in TARGET_ASSETS:
        entry = {
            "data": [],
            "oi_change_pct": None,
            "oi_history_available": False,
            "fallback_reason": None,
        }
        try:
            resp = requests.get(
                BINANCE_FUTURES_OI_HIST,
                params={"symbol": sym, "period": "5m", "limit": 3},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            entry["data"] = data

            if len(data) >= 2:
                oi_curr = float(data[-1]["sumOpenInterest"])
                oi_prev = float(data[-2]["sumOpenInterest"])
                if oi_prev > 0:
                    oi_change_pct = ((oi_curr - oi_prev) / oi_prev) * 100
                    entry["oi_change_pct"] = round(oi_change_pct, 4)
                    entry["oi_history_available"] = True
                    print(f"  {sym}: OI {oi_curr:.0f}, prev {oi_prev:.0f}, "
                          f"change={oi_change_pct:+.4f}%")
                else:
                    entry["fallback_reason"] = "oi_prev_zero"
                    print(f"  {sym}: OI prev is zero, cannot compute change %")
            elif len(data) == 1:
                entry["fallback_reason"] = "only_one_datapoint"
                print(f"  {sym}: OI={data[0].get('sumOpenInterest', '?')} (only 1 data point)")
            else:
                entry["fallback_reason"] = "oi_history_endpoint_returned_empty"
                print(f"  {sym}: no OI history data returned from endpoint")
        except Exception as e:
            entry["fallback_reason"] = f"oi_history_fetch_error: {str(e)[:100]}"
            print(f"  {sym}: ERROR fetching OI history: {e}")

        results[sym] = entry
    return results


def fetch_binance_funding_rates() -> dict[str, dict]:
    """Fetch latest funding rate from Binance futures (public, no API key)."""
    print("[1e] Fetching Binance futures funding rates...")
    results = {}
    for sym in TARGET_ASSETS:
        entry = {
            "funding_rate": None,
            "funding_rate_pct": None,
            "funding_available": False,
            "fallback_reason": None,
        }
        try:
            resp = requests.get(
                BINANCE_FUTURES_FUNDING_RATE,
                params={"symbol": sym, "limit": 1},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                rate = float(data[0]["fundingRate"])
                entry["funding_rate"] = rate
                entry["funding_rate_pct"] = round(rate * 100, 4)
                entry["funding_available"] = True
                print(f"  {sym}: funding_rate={rate:.6f} ({rate*100:+.4f}%)")
            else:
                entry["fallback_reason"] = "funding_endpoint_returned_empty"
                print(f"  {sym}: no funding rate data returned")
        except Exception as e:
            entry["fallback_reason"] = f"funding_fetch_error: {str(e)[:100]}"
            print(f"  {sym}: ERROR fetching funding rate: {e}")

        results[sym] = entry
    return results


def fetch_binance_long_short_ratio() -> dict[str, dict]:
    """Fetch global long/short account ratio from Binance futures (public, no API key).

    This endpoint may not be available on all Binance API versions.
    Falls back gracefully if unavailable.
    """
    print("[1f] Fetching Binance futures long/short account ratio...")
    results = {}
    for sym in TARGET_ASSETS:
        entry = {
            "long_short_ratio": None,
            "long_account_pct": None,
            "short_account_pct": None,
            "ls_ratio_available": False,
            "fallback_reason": None,
        }
        try:
            resp = requests.get(
                BINANCE_FUTURES_LS_RATIO,
                params={"symbol": sym, "period": "5m", "limit": 1},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                ratio = float(data[0]["longShortRatio"])
                long_pct = float(data[0]["longAccount"]) * 100
                short_pct = float(data[0]["shortAccount"]) * 100
                entry["long_short_ratio"] = round(ratio, 4)
                entry["long_account_pct"] = round(long_pct, 2)
                entry["short_account_pct"] = round(short_pct, 2)
                entry["ls_ratio_available"] = True
                print(f"  {sym}: L/S ratio={ratio:.4f}, long={long_pct:.1f}%, short={short_pct:.1f}%")
            else:
                entry["fallback_reason"] = "ls_ratio_endpoint_returned_empty"
                print(f"  {sym}: no L/S ratio data returned")
        except Exception as e:
            entry["fallback_reason"] = f"ls_ratio_fetch_error_or_endpoint_unavailable: {str(e)[:100]}"
            print(f"  {sym}: L/S ratio endpoint unavailable or error: {type(e).__name__}")

        results[sym] = entry
    return results


def fetch_binance_taker_buy_sell_ratio() -> dict[str, dict]:
    """Fetch taker buy/sell volume ratio from Binance futures (public, no API key).

    This endpoint may not be available on all Binance API versions.
    Falls back gracefully if unavailable.
    """
    print("[1g] Fetching Binance futures taker buy/sell ratio...")
    results = {}
    for sym in TARGET_ASSETS:
        entry = {
            "taker_buy_sell_ratio": None,
            "taker_buy_vol_pct": None,
            "taker_sell_vol_pct": None,
            "taker_ratio_available": False,
            "fallback_reason": None,
        }
        try:
            resp = requests.get(
                BINANCE_FUTURES_TAKER_RATIO,
                params={"symbol": sym, "period": "5m", "limit": 1},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                ratio = float(data[0]["buySellRatio"])
                entry["taker_buy_sell_ratio"] = round(ratio, 4)
                # buyVol + sellVol from the same entry
                buy_vol = float(data[0].get("buyVol", 0))
                sell_vol = float(data[0].get("sellVol", 0))
                total = buy_vol + sell_vol
                if total > 0:
                    entry["taker_buy_vol_pct"] = round(buy_vol / total * 100, 2)
                    entry["taker_sell_vol_pct"] = round(sell_vol / total * 100, 2)
                entry["taker_ratio_available"] = True
                print(f"  {sym}: taker B/S ratio={ratio:.4f}, "
                      f"buy={entry.get('taker_buy_vol_pct', '?')}%, "
                      f"sell={entry.get('taker_sell_vol_pct', '?')}%")
            else:
                entry["fallback_reason"] = "taker_ratio_endpoint_returned_empty"
                print(f"  {sym}: no taker ratio data returned")
        except Exception as e:
            entry["fallback_reason"] = f"taker_ratio_fetch_error_or_endpoint_unavailable: {str(e)[:100]}"
            print(f"  {sym}: taker ratio endpoint unavailable or error: {type(e).__name__}")

        results[sym] = entry
    return results


# ══════════════════════════════════════════════════════════════════════════
# Step 2: Build raw snapshots from real API data
# ══════════════════════════════════════════════════════════════════════════

def build_raw_snapshot(
    spot_tickers: dict,
    futures_tickers: dict,
    open_interests: dict,
    oi_histories: dict,
    funding_rates: dict,
    ls_ratios: dict,
    taker_ratios: dict,
) -> dict:
    """Build raw snapshot with all fetched data per asset."""
    print("\n[2] Building raw snapshot from real API data...")

    observed_at = generate_timestamp()
    assets = []

    for sym in TARGET_ASSETS:
        label = ASSET_LABELS.get(sym, sym)
        spot = spot_tickers.get(sym, {})
        fut = futures_tickers.get(sym, {})
        oi_data = open_interests.get(sym, {})
        oi_hist_entry = oi_histories.get(sym, {})
        funding_entry = funding_rates.get(sym, {})
        ls_entry = ls_ratios.get(sym, {})
        taker_entry = taker_ratios.get(sym, {})

        # Price data
        price_change_pct_str = spot.get("priceChangePercent",
                                        fut.get("priceChangePercent", "0"))
        try:
            price_change_pct = float(price_change_pct_str)
        except (ValueError, TypeError):
            price_change_pct = 0.0

        try:
            futures_price_change_pct_str = fut.get("priceChangePercent", "0")
            futures_price_change_pct = float(futures_price_change_pct_str)
        except (ValueError, TypeError):
            futures_price_change_pct = 0.0

        try:
            last_price = float(spot.get("lastPrice", fut.get("lastPrice", 0)))
        except (ValueError, TypeError):
            last_price = 0.0

        try:
            high_24h = float(spot.get("highPrice", fut.get("highPrice", 0)))
        except (ValueError, TypeError):
            high_24h = 0.0

        try:
            low_24h = float(spot.get("lowPrice", fut.get("lowPrice", 0)))
        except (ValueError, TypeError):
            low_24h = 0.0

        try:
            volume_24h = float(spot.get("volume", fut.get("volume", 0)))
        except (ValueError, TypeError):
            volume_24h = 0.0

        try:
            quote_volume_24h = float(spot.get("quoteVolume", fut.get("quoteVolume", 0)))
        except (ValueError, TypeError):
            quote_volume_24h = 0.0

        try:
            open_interest_current = float(oi_data.get("openInterest", 0))
        except (ValueError, TypeError):
            open_interest_current = 0.0

        # OI change
        oi_change_pct = oi_hist_entry.get("oi_change_pct")
        oi_history_available = oi_hist_entry.get("oi_history_available", False)
        oi_fallback_reason = oi_hist_entry.get("fallback_reason")

        # Funding rate
        funding_rate = funding_entry.get("funding_rate")
        funding_rate_pct = funding_entry.get("funding_rate_pct")
        funding_available = funding_entry.get("funding_available", False)
        funding_fallback = funding_entry.get("fallback_reason")

        # Long/short ratio
        long_short_ratio = ls_entry.get("long_short_ratio")
        ls_ratio_available = ls_entry.get("ls_ratio_available", False)
        ls_fallback = ls_entry.get("fallback_reason")

        # Taker ratio
        taker_buy_sell_ratio = taker_entry.get("taker_buy_sell_ratio")
        taker_ratio_available = taker_entry.get("taker_ratio_available", False)
        taker_fallback = taker_entry.get("fallback_reason")

        # Collect data limitations
        data_limitations = []
        if not oi_history_available and oi_fallback_reason:
            data_limitations.append(f"oi_history: {oi_fallback_reason}")
        if not funding_available and funding_fallback:
            data_limitations.append(f"funding_rate: {funding_fallback}")
        if not ls_ratio_available and ls_fallback:
            data_limitations.append(f"long_short_ratio: {ls_fallback}")
        if not taker_ratio_available and taker_fallback:
            data_limitations.append(f"taker_buy_sell_ratio: {taker_fallback}")

        asset_entry = {
            "asset": label,
            "symbol": sym,
            "price": round(last_price, 4),
            "price_change_24h_pct": round(price_change_pct, 4),
            "futures_price_change_24h_pct": round(futures_price_change_pct, 4),
            "volume_24h": round(volume_24h, 2),
            "quote_volume_24h": round(quote_volume_24h, 2),
            "high_24h": round(high_24h, 4),
            "low_24h": round(low_24h, 4),
            "open_interest_current": round(open_interest_current, 2),
            "open_interest_change_pct": oi_change_pct,
            "oi_history_available": oi_history_available,
            "oi_fallback_reason": oi_fallback_reason,
            "funding_rate": funding_rate,
            "funding_rate_pct": funding_rate_pct,
            "funding_available": funding_available,
            "funding_fallback_reason": funding_fallback,
            "long_short_ratio": long_short_ratio,
            "ls_ratio_available": ls_ratio_available,
            "ls_ratio_fallback_reason": ls_fallback,
            "taker_buy_sell_ratio": taker_buy_sell_ratio,
            "taker_ratio_available": taker_ratio_available,
            "taker_ratio_fallback_reason": taker_fallback,
            "data_limitations": data_limitations,
            "is_fixture": False,
            "data_source": "binance_public_api",
            "proxy_note": "清算压力代理指标 — 非真实逐笔清算数据。基于价格变动/OI/资金费率/LS比率/taker比率的复合代理估算。",
        }
        assets.append(asset_entry)

        oi_str = f"{oi_change_pct:+.4f}%" if oi_change_pct is not None else "N/A"
        fr_str = f"{funding_rate_pct:+.4f}%" if funding_rate_pct is not None else "N/A"
        ls_str = f"{long_short_ratio:.4f}" if long_short_ratio is not None else "N/A"
        tk_str = f"{taker_buy_sell_ratio:.4f}" if taker_buy_sell_ratio is not None else "N/A"
        print(f"  {label}: price={last_price}, price_chg={price_change_pct:+.2f}%, "
              f"quote_vol=${quote_volume_24h:,.0f}, OI={open_interest_current:,.0f}, "
              f"OI_chg={oi_str}, funding={fr_str}, L/S={ls_str}, taker={tk_str}, "
              f"limitations={len(data_limitations)}")

    snapshot = {
        "event_id": f"real_liq_{datetime.now(CN_TZ).strftime('%Y%m%d_%H%M%S')}",
        "observed_at": observed_at,
        "assets": assets,
        "asset_count": len(assets),
        "api_source": "Binance public REST endpoints (no API key)",
        "api_key_required": False,
        "is_fixture": False,
        "data_mode": "real_external_api",
        "real_external_api_called": True,
        "data_note": "清算压力代理信号 (liquidation pressure proxy) — Binance REST 不提供直接清算流数据。本快照使用公开衍生指标（价格变动/OI/资金费率/LS比率/taker比率）作为保守代理。",
        "fetch_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    print(f"  Built snapshot with {len(assets)} assets from real Binance API")
    return snapshot


# ══════════════════════════════════════════════════════════════════════════
# Step 3: Compute liquidation pressure proxy signals per asset
# ══════════════════════════════════════════════════════════════════════════

def compute_liquidation_pressure_signals(snapshot: dict) -> list[dict]:
    """Compute liquidation_pressure proxy signals for each asset.

    Conservative admission rules:
      - price move >= 4% AND at least 2 confirmation factors → admission_passed
      - price move >= 5% AND at least 1 confirmation factor → admission_passed
      - Otherwise → blocked_gate_not_passed

    Confirmation factors (proxy indicators):
      1. Funding rate extreme (abs > threshold)
      2. OI change significant (> 2%)
      3. Long/short ratio extreme (< 0.8 or > 1.2)
      4. Taker buy/sell ratio extreme (< 0.8 or > 1.2)

    Proxy pressure score: composite 0-10 based on available indicators.
    """
    print("\n[3] Computing liquidation pressure proxy signals per asset...")

    assets = snapshot["assets"]
    signals = []

    for asset in assets:
        label = asset["asset"]
        sym = asset["symbol"]
        price_chg = asset["price_change_24h_pct"]
        abs_price_chg = abs(price_chg)
        direction = "up" if price_chg >= 0 else "down"

        funding_rate = asset.get("funding_rate")
        funding_rate_pct = asset.get("funding_rate_pct")
        funding_available = asset.get("funding_available", False)

        oi_change_pct = asset.get("open_interest_change_pct")
        oi_history_available = asset.get("oi_history_available", False)

        ls_ratio = asset.get("long_short_ratio")
        ls_ratio_available = asset.get("ls_ratio_available", False)

        taker_ratio = asset.get("taker_buy_sell_ratio")
        taker_ratio_available = asset.get("taker_ratio_available", False)

        quote_vol = asset["quote_volume_24h"]
        oi_current = asset["open_interest_current"]

        # ── Determine confirmation factors ──────────────────────────────
        confirmation_factors = []

        # Factor 1: Funding rate extreme
        funding_extreme = False
        if funding_available and funding_rate is not None:
            if sym in ("BTCUSDT", "ETHUSDT"):
                funding_extreme = abs(funding_rate) >= FUNDING_EXTREME_BTC_ETH
            else:
                funding_extreme = abs(funding_rate) >= FUNDING_EXTREME_SOL
            if funding_extreme:
                funding_dir = "positive" if funding_rate > 0 else "negative"
                confirmation_factors.append(
                    f"funding_extreme: rate={funding_rate_pct:+.4f}% ({funding_dir}), "
                    f"threshold={FUNDING_EXTREME_BTC_ETH*100 if sym in ('BTCUSDT','ETHUSDT') else FUNDING_EXTREME_SOL*100:.1f}%"
                )

        # Factor 2: OI change significant
        oi_significant = False
        if oi_history_available and oi_change_pct is not None:
            if abs(oi_change_pct) >= OI_CHANGE_CONFIRM_THRESHOLD_PCT:
                oi_significant = True
                oi_dir = "increasing" if oi_change_pct > 0 else "decreasing"
                confirmation_factors.append(
                    f"oi_significant: OI_chg={oi_change_pct:+.4f}% ({oi_dir}), "
                    f"threshold={OI_CHANGE_CONFIRM_THRESHOLD_PCT}%"
                )

        # Factor 3: Long/short ratio extreme
        ls_extreme = False
        if ls_ratio_available and ls_ratio is not None:
            if ls_ratio > LS_RATIO_BULLISH:
                ls_extreme = True
                confirmation_factors.append(
                    f"ls_ratio_bullish: L/S={ls_ratio:.4f} > {LS_RATIO_BULLISH} "
                    f"(long dominant — potential long squeeze risk)"
                )
            elif ls_ratio < LS_RATIO_BEARISH:
                ls_extreme = True
                confirmation_factors.append(
                    f"ls_ratio_bearish: L/S={ls_ratio:.4f} < {LS_RATIO_BEARISH} "
                    f"(short dominant — potential short squeeze risk)"
                )

        # Factor 4: Taker buy/sell ratio extreme
        taker_extreme = False
        if taker_ratio_available and taker_ratio is not None:
            if taker_ratio > TAKER_RATIO_BUY:
                taker_extreme = True
                confirmation_factors.append(
                    f"taker_buy_pressure: taker B/S={taker_ratio:.4f} > {TAKER_RATIO_BUY} "
                    f"(aggressive buying — possible short liquidation cascade)"
                )
            elif taker_ratio < TAKER_RATIO_SELL:
                taker_extreme = True
                confirmation_factors.append(
                    f"taker_sell_pressure: taker B/S={taker_ratio:.4f} < {TAKER_RATIO_SELL} "
                    f"(aggressive selling — possible long liquidation cascade)"
                )

        # Volume confirmation (supplementary)
        vol_confirm = quote_vol >= VOLUME_CONFIRMATION_THRESHOLD_USD
        if vol_confirm:
            confirmation_factors.append(
                f"volume_confirm: quote_vol=${quote_vol:,.0f} >= ${VOLUME_CONFIRMATION_THRESHOLD_USD:,.0f}"
            )

        has_confirm_factor = len(confirmation_factors) > 0
        confirm_count = len(confirmation_factors)

        # ── Compute proxy pressure score (0-10) ─────────────────────────
        proxy_score = 0.0
        # Base from price move: 0-5 points (1 point per 1% move, max 5)
        proxy_score += min(abs_price_chg, 5.0)

        # Funding contribution: 0-2 points
        if funding_extreme:
            proxy_score += 2.0
        elif funding_available:
            proxy_score += 1.0

        # OI contribution: 0-1.5 points
        if oi_significant:
            proxy_score += 1.5

        # L/S ratio contribution: 0-1 point
        if ls_extreme:
            proxy_score += 1.0

        # Taker ratio contribution: 0-1 point
        if taker_extreme:
            proxy_score += 1.0

        proxy_score = round(min(proxy_score, 10.0), 2)

        # ── Determine admission ─────────────────────────────────────────
        admission_passed = False
        pressure_type = None

        if abs_price_chg >= ADMISSION_PRICE_THRESHOLD_PCT and confirm_count >= 2:
            admission_passed = True
            pressure_type = f"{direction}_liquidation_pressure_confirmed"
            print(f"  {label}: [ADMIT] price_chg={price_chg:+.2f}%, "
                  f"confirm_factors={confirm_count} (>=2), score={proxy_score}")
        elif abs_price_chg >= ADMISSION_WEAK_PRICE_THRESHOLD_PCT and confirm_count >= 1:
            admission_passed = True
            pressure_type = f"{direction}_liquidation_pressure_weak"
            print(f"  {label}: [ADMIT-WEAK] price_chg={price_chg:+.2f}%, "
                  f"confirm_factors={confirm_count} (>=1), score={proxy_score}")
        elif abs_price_chg >= ADMISSION_PRICE_THRESHOLD_PCT and confirm_count == 1:
            # Borderline: >=4% but only 1 factor — not enough for admission
            pressure_type = f"{direction}_liquidation_pressure_insufficient"
            print(f"  {label}: [BLOCKED] price_chg={price_chg:+.2f}% >= {ADMISSION_PRICE_THRESHOLD_PCT}% "
                  f"but only {confirm_count} confirm factor (need >=2)")
        elif abs_price_chg >= ADMISSION_PRICE_THRESHOLD_PCT and confirm_count == 0:
            pressure_type = f"{direction}_liquidation_pressure_no_confirm"
            print(f"  {label}: [BLOCKED] price_chg={price_chg:+.2f}% >= {ADMISSION_PRICE_THRESHOLD_PCT}% "
                  f"but 0 confirm factors")
        else:
            print(f"  {label}: [BELOW_THRESHOLD] price_chg={price_chg:+.2f}% < "
                  f"{ADMISSION_PRICE_THRESHOLD_PCT}%")

        # ── Determine pressure direction (long/short liquidation risk) ──
        # If price is going down fast, longs are being liquidated
        # If price is going up fast, shorts are being liquidated
        if direction == "down":
            proxy_pressure_direction = "long_liquidation_risk"
        else:
            proxy_pressure_direction = "short_liquidation_risk"

        signal = {
            "card_family": CARD_FAMILY,
            "event_id": f"{snapshot['event_id']}_{label.lower()}",
            "observed_at": snapshot["observed_at"],
            "asset": label,
            "symbol": sym,
            "price": asset["price"],
            "price_change_24h_pct": price_chg,
            "futures_price_change_24h_pct": asset["futures_price_change_24h_pct"],
            "futures_volume_24h": asset["volume_24h"],
            "futures_quote_volume_24h": quote_vol,
            "open_interest_current": oi_current,
            "funding_rate": funding_rate,
            "long_short_ratio": ls_ratio,
            "taker_buy_sell_ratio": taker_ratio,
            "open_interest_change_pct": oi_change_pct,
            "proxy_pressure_score": proxy_score,
            "proxy_pressure_direction": proxy_pressure_direction,
            "direction": direction,
            "pressure_type": pressure_type,
            "confirmation_factors": confirmation_factors,
            "confirm_factor_count": confirm_count,
            "has_confirm_factor": has_confirm_factor,
            "admission_passed": admission_passed,
            "data_limitations": asset["data_limitations"],
            "funding_available": funding_available,
            "ls_ratio_available": ls_ratio_available,
            "taker_ratio_available": taker_ratio_available,
            "oi_history_available": oi_history_available,
            "oi_history_missing": not oi_history_available,
            "api_source": "Binance public REST endpoints (no API key)",
            "api_key_required": False,
            "real_external_api_called": True,
            "is_fixture": False,
            "data_mode": "real_external_api",
            "proxy_disclaimer": "清算压力代理信号 — 基于价格变动/OI/资金费率/LS比率/taker比率的复合代理估算，非真实逐笔清算数据。",
        }
        signals.append(signal)

    admitted = sum(1 for s in signals if s["admission_passed"])
    total = len(signals)
    print(f"  Summary: {admitted}/{total} assets admitted for liquidation pressure cards")

    if admitted == 0:
        print("  [BLOCKED] No assets reached admission threshold. "
              "Gate will be blocked_gate_not_passed.")

    return signals


# ══════════════════════════════════════════════════════════════════════════
# Step 4: Render liquidation pressure cards (NO AI/model called)
# ══════════════════════════════════════════════════════════════════════════

def render_liquidation_pressure_card(signal: dict) -> str:
    """Render a liquidation_pressure card in Chinese.

    This is a self-contained renderer that does NOT call any AI/model.

    CRITICAL: Cards explicitly state "清算压力代理信号" — they do NOT
    masquerade as real liquidation tape data.
    """
    label = signal["asset"]
    sym = signal["symbol"]
    direction = signal["direction"]
    price_chg = signal["price_change_24h_pct"]
    abs_price_chg = abs(price_chg)
    quote_vol = signal["futures_quote_volume_24h"]
    oi_current = signal["open_interest_current"]
    oi_change_pct = signal["open_interest_change_pct"]
    funding_rate_pct = signal.get("funding_rate")
    funding_rate_pct_display = round(funding_rate_pct * 100, 4) if funding_rate_pct is not None else None
    ls_ratio = signal.get("long_short_ratio")
    taker_ratio = signal.get("taker_buy_sell_ratio")
    proxy_score = signal["proxy_pressure_score"]
    proxy_direction = signal["proxy_pressure_direction"]
    pressure_type = signal.get("pressure_type", "N/A")
    confirm_factors = signal["confirmation_factors"]
    confirm_count = signal["confirm_factor_count"]
    data_limitations = signal.get("data_limitations", [])
    oi_history_missing = signal.get("oi_history_missing", False)
    funding_available = signal.get("funding_available", False)
    ls_ratio_available = signal.get("ls_ratio_available", False)
    taker_ratio_available = signal.get("taker_ratio_available", False)
    price = signal["price"]
    high_24h = signal.get("high_24h", signal.get("high_24h", 0))
    low_24h = signal.get("low_24h", signal.get("low_24h", 0))
    futures_price_chg = signal.get("futures_price_change_24h_pct", 0)

    if direction == "up":
        dir_icon = "\U0001f4c8"  # 📈
        dir_text = "上涨"
    else:
        dir_icon = "\U0001f4c9"  # 📉
        dir_text = "下跌"

    if proxy_direction == "long_liquidation_risk":
        risk_icon = "\U0001f534"  # 🔴
        risk_text = "多头清算风险"
        risk_detail = "价格快速下跌可能触发多头仓位连环清算"
    else:
        risk_icon = "\U0001f7e0"  # 🟠
        risk_text = "空头清算风险"
        risk_detail = "价格快速上涨可能触发空头仓位连环清算"

    # Pressure severity
    if proxy_score >= 7:
        severity = "高"
        severity_icon = "\U0001f534"
    elif proxy_score >= 4:
        severity = "中"
        severity_icon = "\U0001f7e0"
    else:
        severity = "低"
        severity_icon = "\U0001f7e1"

    # Build reason
    reason_parts = [f"{label} 24小时{dir_text} {abs_price_chg:.2f}%"]
    if futures_price_chg != 0:
        reason_parts.append(f"合约同步{futures_price_chg:+.2f}%")
    reason = f"清算压力代理信号：检测到{', '.join(reason_parts)}，可能伴随{risk_text}。"

    # Confirmation details
    confirm_lines = []
    if confirm_factors:
        for cf in confirm_factors:
            confirm_lines.append(f"● {cf}")
    else:
        confirm_lines.append("● 无确认因子（信号不足）")

    # Data availability indicators
    data_lines = []
    data_lines.append(f"● 资金费率：{'可用' if funding_available else '不可用（fallback）'}")
    data_lines.append(f"● 多空账户比：{'可用' if ls_ratio_available else '不可用（fallback）'}")
    data_lines.append(f"● Taker买卖比：{'可用' if taker_ratio_available else '不可用（fallback）'}")

    # Metric lines
    metric_lines = [
        f"● 资产：{label} ({sym})",
        f"● 当前价格：${price:,.2f}",
        f"● 24h涨跌幅：{price_chg:+.2f}%",
        f"● 合约24h涨跌幅：{futures_price_chg:+.2f}%",
        f"● 24h最高：${high_24h:,.2f}",
        f"● 24h最低：${low_24h:,.2f}",
        f"● 24h成交量（Quote）：${quote_vol:,.0f}",
        f"● 当前OI：{oi_current:,.0f}",
    ]

    if oi_change_pct is not None:
        metric_lines.append(f"● OI变化：{oi_change_pct:+.4f}%")
    else:
        metric_lines.append("● OI变化：N/A（历史数据不可用）")

    if funding_rate_pct_display is not None:
        metric_lines.append(f"● 资金费率：{funding_rate_pct_display:+.4f}%")
    else:
        metric_lines.append("● 资金费率：N/A")

    if ls_ratio is not None:
        metric_lines.append(f"● 多空账户比(L/S)：{ls_ratio:.4f}")
    else:
        metric_lines.append("● 多空账户比(L/S)：N/A")

    if taker_ratio is not None:
        metric_lines.append(f"● Taker买卖比(B/S)：{taker_ratio:.4f}")
    else:
        metric_lines.append("● Taker买卖比(B/S)：N/A")

    # Data limitations section
    limitation_lines = []
    if data_limitations:
        limitation_lines = ["", "⚠️ 数据限制（Fallback）："]
        for dl in data_limitations:
            limitation_lines.append(f"  ● {dl}")

    card_lines = [
        f"{dir_icon} {risk_icon} 清算压力代理信号｜{label} {dir_text}｜{risk_text}",
        "",
        f"一句话：{reason}",
        "",
        "\U0001f4ca 指标数据：",
    ] + metric_lines + [
        "",
        "✅ 确认因子：",
    ] + confirm_lines + [
        "",
        "\U0001f4e1 数据可用性：",
    ] + data_lines + [
        "",
        f"\U0001f4ca 代理压力评分：{proxy_score}/10（{severity}）",
        f"\U0001f4ca 压力方向：{risk_text}",
        f"\U0001f4ca 信号类型：{pressure_type}",
    ] + limitation_lines + [
        "",
        "⚠️ 重要声明：本信号为清算压力代理信号（liquidation pressure proxy），",
        "基于价格变动、OI变化、资金费率、多空比、taker买卖比等公开衍生指标的",
        "复合估算生成。Binance REST API 不提供直接清算流数据。",
        "本信号不代表真实逐笔清算数据，不构成交易建议。",
        "",
        "ℹ️ 说明：清算压力代理信号反映市场极端波动可能伴随的",
        "杠杆仓位被强制清算风险。高杠杆市场中，",
        "价格快速变动可能导致连环清算（cascade liquidation）。",
        "代理指标仅提供参考，实际清算情况请以交易所清算数据为准。",
        "",
        f"\U0001f550 观测时间：{signal['observed_at']}",
        "",
        "\U0001f4ca 数据源：Binance 公开行情 API（免费，无需 API Key）",
        "⚠️ 代理指标，非真实逐笔清算数据",
        "",
        "\U0001f510 v116I 安全预检通过 | 真实API（免费） | 测试群 one-shot 发送",
    ]

    card_text = "\n".join(line for line in card_lines if line)
    return card_text


# ══════════════════════════════════════════════════════════════════════════
# Step 5: Quality Gate
# ══════════════════════════════════════════════════════════════════════════

def run_quality_gate(signal: dict, card_text: str) -> dict:
    """Run quality gate checks on the liquidation pressure signal and card."""
    print(f"\n[5] Running quality gate for {signal['asset']}...")

    required_fields = [
        "card_family", "event_id", "asset", "symbol",
        "price_change_24h_pct", "futures_quote_volume_24h",
        "open_interest_current", "funding_rate",
        "long_short_ratio", "taker_buy_sell_ratio",
        "proxy_pressure_score", "proxy_pressure_direction",
        "pressure_type",
    ]
    required_present = all(signal.get(f) is not None for f in required_fields)

    card_present = bool(card_text and len(card_text) > 100)
    family_correct = signal.get("card_family") == CARD_FAMILY
    asset_present = bool(signal.get("asset") and signal.get("symbol"))

    # No investment advice
    no_trading_advice = True
    bad_phrases = ["买入", "卖出", "做多", "做空", "all in", "满仓", "清仓",
                   "必涨", "必跌", "稳赚", "抄底", "梭哈",
                   "必爆仓", "必跌", "必涨", "开空", "开多"]
    for phrase in bad_phrases:
        if phrase in card_text:
            no_trading_advice = False
            break

    # Must contain proxy disclaimer
    has_proxy_disclaimer = any(keyword in card_text for keyword in [
        "代理信号", "proxy", "代理指标", "非真实逐笔清算",
    ])

    # Must NOT masquerade as real liquidation tape
    no_fake_tape = True
    fake_tape_phrases = ["实时清算", "真实清算数据", "liquidation tape",
                         "清算流水", "逐笔清算", "清算订单流"]
    for phrase in fake_tape_phrases:
        if phrase in card_text:
            # Check context — if it says "NOT real", it's OK
            if "非" not in card_text[max(0, card_text.find(phrase)-10):card_text.find(phrase)+len(phrase)+10]:
                no_fake_tape = False
                break

    # No forbidden terms
    no_forbidden_terms = True
    forbidden_terms = ["token", "api_key", "chat_id", "password", "secret",
                       "debug", "internal", "fixture"]
    for term in forbidden_terms:
        if term.lower() in card_text.lower():
            no_forbidden_terms = False
            break

    api_source_ok = signal.get("api_key_required") is False
    real_api_ok = signal.get("real_external_api_called") is True
    not_fixture = not signal.get("is_fixture", True)
    admission_ok = signal.get("admission_passed", False)

    blocked_reasons = []
    if not required_present:
        blocked_reasons.append("missing_required_fields")
    if not card_present:
        blocked_reasons.append("card_text_too_short_or_missing")
    if not family_correct:
        blocked_reasons.append(f"wrong_card_family: expected {CARD_FAMILY}")
    if not asset_present:
        blocked_reasons.append("asset_or_symbol_missing")
    if not no_trading_advice:
        blocked_reasons.append("trading_advice_detected")
    if not no_forbidden_terms:
        blocked_reasons.append("forbidden_terms_in_card")
    if not api_source_ok:
        blocked_reasons.append("api_key_required_detected")
    if not real_api_ok:
        blocked_reasons.append("not_real_external_api")
    if not not_fixture:
        blocked_reasons.append("is_fixture_data")
    if not admission_ok:
        blocked_reasons.append("admission_not_passed")
    if not has_proxy_disclaimer:
        blocked_reasons.append("missing_proxy_disclaimer")
    if not no_fake_tape:
        blocked_reasons.append("masquerading_as_real_liquidation_tape")

    quality_gate_passed = len(blocked_reasons) == 0 and admission_ok

    qr = {
        "card_family": CARD_FAMILY,
        "event_id": signal["event_id"],
        "asset": signal["asset"],
        "quality_gate_passed": quality_gate_passed,
        "required_fields_present": required_present,
        "card_text_present": card_present,
        "family_correct": family_correct,
        "asset_present": asset_present,
        "no_forbidden_terms": no_forbidden_terms,
        "no_trading_advice": no_trading_advice,
        "has_proxy_disclaimer": has_proxy_disclaimer,
        "no_fake_liquidation_tape": no_fake_tape,
        "api_source_ok": api_source_ok,
        "real_api_ok": real_api_ok,
        "not_fixture": not_fixture,
        "admission_passed": admission_ok,
        "blocked_reasons": blocked_reasons,
        "fixture_only": False,
        "checked_at": generate_timestamp(),
    }

    status = "PASS" if quality_gate_passed else "BLOCKED"
    print(f"  Quality gate: {status}")
    if blocked_reasons:
        print(f"  Blocked reasons: {blocked_reasons}")

    return qr


# ══════════════════════════════════════════════════════════════════════════
# Step 6: Send-Readiness Gate
# ══════════════════════════════════════════════════════════════════════════

def run_send_readiness_gate(signal: dict, quality_gate: dict, preflight: dict) -> dict:
    """Run send-readiness gate checks, incorporating safe secret preflight results."""
    print(f"\n[6] Running send-readiness gate for {signal['asset']}...")

    qg_passed = quality_gate.get("quality_gate_passed", False)
    admission_ok = signal.get("admission_passed", False)
    not_fixture = not signal.get("is_fixture", True)
    preflight_passed = preflight.get("preflight_passed", False)
    bot_token_exists = preflight.get("telegram_bot_token_present", False)
    chat_id_exists = preflight.get("telegram_chat_id_present", False)

    tg_sender_available = bot_token_exists and chat_id_exists
    production_send_ready = False  # NEVER for this task
    tg_test_group_ready = tg_sender_available and qg_passed and admission_ok

    blocked_reasons = []
    if not qg_passed:
        blocked_reasons.append("quality_gate_not_passed")
    if not admission_ok:
        blocked_reasons.append("admission_not_passed")
    if not not_fixture:
        blocked_reasons.append("is_fixture_data")
    if not tg_sender_available:
        if not bot_token_exists:
            blocked_reasons.append("tg_bot_token_not_configured")
        if not chat_id_exists:
            blocked_reasons.append("tg_chat_id_not_configured")

    send_readiness_passed = tg_test_group_ready

    sr = {
        "card_family": CARD_FAMILY,
        "event_id": signal["event_id"],
        "asset": signal["asset"],
        "send_readiness_passed": send_readiness_passed,
        "tg_test_group_ready": tg_test_group_ready,
        "production_send_ready": production_send_ready,
        "tg_sender_available": tg_sender_available,
        "bot_token_configured": bot_token_exists,
        "chat_id_configured": chat_id_exists,
        "secret_preflight_passed": preflight_passed,
        "admission_passed": admission_ok,
        "quality_gate_passed": qg_passed,
        "not_fixture": not_fixture,
        "blocked_reasons": blocked_reasons,
        "fixture_only": False,
        "checked_at": generate_timestamp(),
    }

    status = "PASS" if send_readiness_passed else "BLOCKED"
    print(f"  Send-readiness: {status}")
    print(f"  Preflight passed: {preflight_passed}")
    print(f"  TG sender available: {tg_sender_available}")
    print(f"  TG test group ready: {tg_test_group_ready}")
    if blocked_reasons:
        print(f"  Blocked reasons: {blocked_reasons}")

    return sr


# ══════════════════════════════════════════════════════════════════════════
# Step 7: TG Test Send (one-shot) with redacted proof
# ══════════════════════════════════════════════════════════════════════════

def attempt_tg_test_send(
    signal: dict,
    card_text: str,
    send_readiness: dict,
    preflight: dict,
) -> dict:
    """Attempt one-shot TG test group send with full redacted proof.

    CRITICAL SAFETY:
      - Never prints token/chat_id values
      - Records only redacted (sha256 hashed) message_id
      - Does NOT store raw chat_id or token in any output file
    """
    print(f"\n[7] Attempting TG test group send for {signal['asset']} (one-shot)...")

    if not send_readiness.get("send_readiness_passed", False):
        print("  [BLOCKED] Send-readiness not passed, skipping TG send")
        return {
            "attempted": False,
            "success": False,
            "blocked_reason": "send_readiness_not_passed",
            "blocked_details": send_readiness.get("blocked_reasons", []),
            "target_type": "test_group",
            "one_shot": True,
        }

    if not send_readiness.get("tg_sender_available", False):
        print("  [BLOCKED] TG sender not configured (missing env vars)")
        return {
            "attempted": False,
            "success": False,
            "blocked_reason": "tg_blocked_missing_sender_or_config",
            "blocked_details": send_readiness.get("blocked_reasons", []),
            "target_type": "test_group",
            "one_shot": True,
        }

    if not preflight.get("preflight_passed", False):
        print("  [BLOCKED] Safe secret preflight not passed")
        return {
            "attempted": False,
            "success": False,
            "blocked_reason": "tg_blocked_preflight_not_passed",
            "target_type": "test_group",
            "one_shot": True,
        }

    # Read credentials from environment (set by load_local_secrets.ps1)
    # NEVER print or log these values
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    proxy_url = os.environ.get("TELEGRAM_PROXY_URL", None)

    if not bot_token or not chat_id:
        print("  [BLOCKED] Empty token or chat_id after env check")
        return {
            "attempted": False,
            "success": False,
            "blocked_reason": "tg_blocked_missing_sender_or_config",
            "target_type": "test_group",
            "one_shot": True,
        }

    # SAFETY: Only compute redacted hashes, never log raw values
    token_redacted = hash_value(bot_token)
    chat_id_redacted = hash_value(chat_id)
    print("  TG credentials found in environment (values NOT printed)")
    print(f"  token fingerprint: {token_redacted}")
    print(f"  chat_id fingerprint: {chat_id_redacted}")
    print(f"  Proxy: {'configured' if proxy_url else 'not configured'}")

    # Import sender components (lazy import to allow script to run even if modules missing)
    try:
        from scripts.market_radar_sender import (
            TGTransport,
            RealHttpClient,
        )
    except ImportError as e:
        print(f"  [BLOCKED] Cannot import market_radar_sender: {e}")
        return {
            "attempted": False,
            "success": False,
            "blocked_reason": f"tg_blocked_import_error: {e}",
            "target_type": "test_group",
            "one_shot": True,
        }

    # Build transport
    try:
        if proxy_url:
            http_client = RealHttpClient(timeout=10, proxy_url=proxy_url)
        else:
            http_client = RealHttpClient(timeout=10)

        transport = TGTransport(
            bot_token=bot_token,
            default_chat_id=chat_id,
            http_client=http_client,
            timeout_seconds=10,
        )
        print("  TGTransport created (credentials redacted from all output)")

        # Build send payload
        send_payload = {
            "text": card_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        print(f"  Sending card ({len(card_text)} chars) to TG test group...")
        result = transport.send(send_payload, target="test_group", parse_mode="HTML")

        SAFETY["tg_test_sent"] = result.success

        # Redact message_id
        message_id = result.message_id
        safe_msg_id = None
        if message_id and not message_id.startswith("dry-run") and not message_id.startswith("tg-stub"):
            safe_msg_id = hash_value(message_id)
            SAFETY["tg_message_id_redacted"] = safe_msg_id
            md_redacted_display = "sha256:" + hashlib.sha256(message_id.encode()).hexdigest()[:12]
            print(f"  TG send result: success={result.success}, "
                  f"message_id_present: true, "
                  f"message_id_redacted: {md_redacted_display}")
        elif message_id:
            print(f"  TG send result: success={result.success}, message_id={message_id} (stub/dry-run)")
        else:
            print(f"  TG send result: success={result.success}, message_id=None")

        print(f"  status_code={result.status_code}, error_type={result.error_type}")

        if result.error_message:
            error_safe = result.error_message
            if bot_token and bot_token in error_safe:
                error_safe = error_safe.replace(bot_token, "[REDACTED_TOKEN]")
            if chat_id and chat_id in error_safe:
                error_safe = error_safe.replace(chat_id, "[REDACTED_CHAT_ID]")
            print(f"  error_message: {error_safe[:200]}")

        return {
            "attempted": True,
            "success": result.success,
            "status": "done" if result.success else "failed",
            "message_id_present": bool(message_id),
            "message_id_redacted": safe_msg_id,
            "status_code": result.status_code,
            "error_type": result.error_type,
            "error_message": error_safe[:200] if result.error_message else None,
            "provider": result.provider,
            "tg_api_called": result.tg_api_called,
            "provider_metadata_redacted": True,
            "target_type": "test_group",
            "one_shot": True,
            "production_send": False,
            "sent_at": generate_timestamp(),
        }

    except Exception as e:
        error_str = str(e)
        # Redact secrets from error string (token, chat_id, proxy credentials)
        if bot_token and bot_token in error_str:
            error_str = error_str.replace(bot_token, "[REDACTED_TOKEN]")
        if chat_id and chat_id in error_str:
            error_str = error_str.replace(chat_id, "[REDACTED_CHAT_ID]")
        if proxy_url and proxy_url in error_str:
            error_str = error_str.replace(proxy_url,
                                          re.sub(r'://[^@]*@', '://[REDACTED_CREDENTIALS]@', proxy_url))
        print(f"  [BLOCKED] TG send exception: {type(e).__name__}: {error_str[:200]}")
        return {
            "attempted": True,
            "success": False,
            "status": "failed",
            "error_type": "EXCEPTION",
            "error_message": error_str[:200],
            "tg_api_called": False,
            "target_type": "test_group",
            "one_shot": True,
        }


# ══════════════════════════════════════════════════════════════════════════
# Write outputs
# ══════════════════════════════════════════════════════════════════════════

def write_outputs(
    preflight: dict,
    snapshot: dict,
    signals: list[dict],
    cards: list[dict],
    quality_gates: list[dict],
    send_readiness_list: list[dict],
    tg_attempts: list[dict],
) -> dict:
    """Write all output files and return the final result summary."""
    print("\n[8] Writing output files...")

    # 1. Raw snapshots
    ensure_dir(RAW_SNAPSHOTS_JSON)
    with open(RAW_SNAPSHOTS_JSON, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RAW_SNAPSHOTS_JSON}")

    # 2. Signal records
    ensure_dir(SIGNAL_RECORDS_JSONL)
    with open(SIGNAL_RECORDS_JSONL, "w", encoding="utf-8") as f:
        for sig in signals:
            f.write(json.dumps(sig, ensure_ascii=False) + "\n")
    print(f"  [OK] {SIGNAL_RECORDS_JSONL} ({len(signals)} records)")

    # 3. Card records
    ensure_dir(CARD_RECORDS_JSONL)
    with open(CARD_RECORDS_JSONL, "w", encoding="utf-8") as f:
        for card in cards:
            card_record = {
                "card_family": CARD_FAMILY,
                "event_id": card["event_id"],
                "asset": card["asset"],
                "card_text": card["card_text"],
                "card_char_count": len(card["card_text"]),
                "proxy_disclaimer": "清算压力代理信号 — 非真实逐笔清算数据",
                "generated_at": generate_timestamp(),
                "real_external_api_called": True,
                "fixture_only": False,
            }
            f.write(json.dumps(card_record, ensure_ascii=False) + "\n")
    print(f"  [OK] {CARD_RECORDS_JSONL} ({len(cards)} records)")

    # 4. Quality gate records
    ensure_dir(QUALITY_GATE_JSONL)
    with open(QUALITY_GATE_JSONL, "w", encoding="utf-8") as f:
        for qg in quality_gates:
            f.write(json.dumps(qg, ensure_ascii=False) + "\n")
    print(f"  [OK] {QUALITY_GATE_JSONL} ({len(quality_gates)} records)")

    # 5. Send-readiness records
    ensure_dir(SEND_READINESS_JSONL)
    with open(SEND_READINESS_JSONL, "w", encoding="utf-8") as f:
        for sr in send_readiness_list:
            f.write(json.dumps(sr, ensure_ascii=False) + "\n")
    print(f"  [OK] {SEND_READINESS_JSONL} ({len(send_readiness_list)} records)")

    # 6. TG send attempts
    ensure_dir(TG_SEND_ATTEMPTS_JSONL)
    with open(TG_SEND_ATTEMPTS_JSONL, "w", encoding="utf-8") as f:
        for ta in tg_attempts:
            f.write(json.dumps(ta, ensure_ascii=False) + "\n")
    print(f"  [OK] {TG_SEND_ATTEMPTS_JSONL} ({len(tg_attempts)} records)")

    # Determine which signals passed admission
    admitted_signals = [s for s in signals if s.get("admission_passed", False)]
    any_admitted = len(admitted_signals) > 0

    # Find TG attempts for admitted signals
    admitted_tg_attempts = [
        ta for i, ta in enumerate(tg_attempts)
        if i < len(signals) and signals[i].get("admission_passed", False)
    ]
    any_tg_sent = any(ta.get("success", False) for ta in admitted_tg_attempts)
    any_tg_attempted = any(ta.get("attempted", False) for ta in admitted_tg_attempts)

    # Find first blocked reason from any TG attempt
    first_blocked = None
    for ta in admitted_tg_attempts:
        if ta.get("blocked_reason") and not ta.get("success", False):
            first_blocked = ta["blocked_reason"]
            break

    preflight_passed = preflight.get("preflight_passed", False)
    tg_available = preflight_passed

    # Determine audit_result
    api_unavailable = not SAFETY.get("real_external_api_called", False)

    if api_unavailable:
        audit_result = "blocked_free_api_unavailable"
    elif not any_admitted:
        audit_result = "blocked_gate_not_passed"
    elif any_tg_sent:
        audit_result = "real_free_api_tg_test_sent"
    elif any_tg_attempted and not any_tg_sent:
        audit_result = "real_free_api_card_ready_tg_blocked_missing_sender"
    elif tg_available and any_admitted:
        audit_result = "real_free_api_card_ready_tg_blocked_missing_sender"
    else:
        audit_result = "blocked_gate_not_passed"

    # 7. Send result JSON
    result = {
        "card_family": CARD_FAMILY,
        "version": VERSION,
        "stage": STAGE,
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "generated_at": generate_timestamp(),
        "real_external_api_called": SAFETY["real_external_api_called"],
        "fixture_only": False,
        "production_send_ready": False,
        "prod_state_write": False,
        "ai_model_called": False,
        "credentials_printed": False,
        "credentials_read_plaintext": SAFETY["credentials_read_plaintext"],
        "daemon_or_loop_started": False,
        "files_deleted": False,
        "api_key_required": False,
        "api_source": "Binance public REST endpoints (no API key)",
        "data_note": "liquidation_pressure_proxy — 基于衍生代理指标的清算压力估算，非真实逐笔清算数据",
        "secret_preflight_run": SAFETY["secret_preflight_run"],
        "telegram_bot_token_present": preflight.get("telegram_bot_token_present", False),
        "telegram_chat_id_present": preflight.get("telegram_chat_id_present", False),
        "secret_preflight_passed": preflight_passed,
        "assets_fetched": TARGET_ASSETS,
        "asset_count": snapshot.get("asset_count", 0),
        "signals_generated": len(signals),
        "signals_admitted": len(admitted_signals),
        "cards_generated": len(cards),
        "any_admitted": any_admitted,
        "quality_gate_any_passed": any(qg.get("quality_gate_passed", False) for qg in quality_gates),
        "send_readiness_any_passed": any(sr.get("send_readiness_passed", False) for sr in send_readiness_list),
        "tg_sender_available": tg_available,
        "tg_test_sent": any_tg_sent,
        "tg_attempted": any_tg_attempted,
        "tg_message_id_redacted": SAFETY.get("tg_message_id_redacted"),
        "tg_message_id_present": any(ta.get("message_id_present", False) for ta in tg_attempts),
        "audit_result": audit_result,
        "blocked_reason": first_blocked if not any_tg_sent else None,
        "target_type": "test_group",
        "one_shot": True,
        "production_send": False,
    }
    ensure_dir(SEND_RESULT_JSON)
    with open(SEND_RESULT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {SEND_RESULT_JSON}")
    print(f"  audit_result: {audit_result}")

    # 8. Card preview markdown
    preview_lines = [
        f"# Market Radar {VERSION} — Liquidation Pressure Proxy Card Preview",
        "",
        f"**Generated**: {generate_timestamp()}",
        f"**Card Family**: `{CARD_FAMILY}`",
        f"**API Source**: Binance public REST endpoints (free, no API key)",
        f"**Assets**: {', '.join(TARGET_ASSETS)}",
        f"**Preflight**: {'PASS' if preflight_passed else 'BLOCKED'}",
        f"**Admitted**: {len(admitted_signals)}/{len(signals)}",
        "",
        "⚠️ **重要声明**: 本报告所有信号均为清算压力代理信号（liquidation pressure proxy），",
        "基于价格变动、OI变化、资金费率、多空比、taker买卖比等公开衍生指标的复合估算。",
        "Binance REST API 不提供直接清算流数据，本信号不代表真实逐笔清算数据。",
        "",
        "---",
        "",
        "## Admission Summary",
        "",
        f"| Asset | Price Chg | QVol | OI Chg | Funding | L/S Ratio | Taker B/S | Score | Admitted | Type |",
        f"|-------|-----------|------|--------|---------|-----------|-----------|-------|----------|------|",
    ]
    for sig in signals:
        oi_str = f"{sig['open_interest_change_pct']:+.2f}%" if sig['open_interest_change_pct'] is not None else "N/A"
        fr_str = f"{sig.get('funding_rate', 0)*100:+.4f}%" if sig.get('funding_rate') is not None else "N/A"
        ls_str = f"{sig.get('long_short_ratio', 0):.4f}" if sig.get('long_short_ratio') is not None else "N/A"
        tk_str = f"{sig.get('taker_buy_sell_ratio', 0):.4f}" if sig.get('taker_buy_sell_ratio') is not None else "N/A"
        preview_lines.append(
            f"| {sig['asset']} | {sig['price_change_24h_pct']:+.2f}% | "
            f"${sig['futures_quote_volume_24h']:,.0f} | {oi_str} | {fr_str} | {ls_str} | {tk_str} | "
            f"{sig.get('proxy_pressure_score', '?')} | "
            f"{sig['admission_passed']} | "
            f"{sig.get('pressure_type', 'N/A')} |"
        )

    preview_lines += [
        "",
        "---",
        "",
        "## Cards Generated",
        "",
    ]

    for card in cards:
        preview_lines += [
            f"### {card['asset']}",
            "",
            "```",
            card["card_text"],
            "```",
            "",
            "---",
            "",
        ]

    preview_lines += [
        "",
        "## Confirmation Factors Detail",
        "",
        f"| Asset | Price Chg | Confirm Count | Confirm Factors | Admitted |",
        f"|-------|-----------|---------------|-----------------|----------|",
    ]
    for sig in signals:
        factors_short = [cf[:60] + "..." if len(cf) > 60 else cf for cf in sig.get("confirmation_factors", [])]
        preview_lines.append(
            f"| {sig['asset']} | {sig['price_change_24h_pct']:+.2f}% | "
            f"{sig.get('confirm_factor_count', 0)} | "
            f"{'; '.join(factors_short) if factors_short else 'N/A'} | "
            f"{sig['admission_passed']} |"
        )

    preview_lines += [
        "",
        "## Data Availability Matrix",
        "",
        f"| Asset | Funding | L/S Ratio | Taker B/S | OI History |",
        f"|-------|---------|-----------|-----------|------------|",
    ]
    for sig in signals:
        preview_lines.append(
            f"| {sig['asset']} | {sig.get('funding_available', False)} | "
            f"{sig.get('ls_ratio_available', False)} | "
            f"{sig.get('taker_ratio_available', False)} | "
            f"{sig.get('oi_history_available', False)} |"
        )

    preview_lines += [
        "",
        "---",
        "",
        "## v116I Safety Flags",
        "",
        f"| Flag | Value |",
        f"|------|-------|",
        f"| secret_preflight_run | True |",
        f"| telegram_bot_token_present | {preflight.get('telegram_bot_token_present', False)} |",
        f"| telegram_chat_id_present | {preflight.get('telegram_chat_id_present', False)} |",
        f"| secret_preflight_passed | {preflight_passed} |",
        f"| real_external_api_called | {SAFETY['real_external_api_called']} |",
        f"| fixture_only | False |",
        f"| production_send_ready | False |",
        f"| ai_model_called | False |",
        f"| files_deleted | False |",
        f"| one_shot | True |",
    ]
    ensure_dir(CARD_PREVIEW_MD)
    with open(CARD_PREVIEW_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(preview_lines) + "\n")
    print(f"  [OK] {CARD_PREVIEW_MD}")

    # 9. Send report markdown
    report_lines = [
        f"# Market Radar {VERSION} — Liquidation Pressure Proxy TG Test Send Report",
        "",
        f"**Generated**: {generate_timestamp()}",
        f"**Task ID**: {TASK_ID}",
        f"**Run ID**: {RUN_ID}",
        "",
        "⚠️ **声明**: 本报告所有信号为清算压力代理信号（proxy），非真实逐笔清算数据。",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| card_family | `{CARD_FAMILY}` |",
        f"| audit_result | **{audit_result}** |",
        f"| real_external_api_called | **{SAFETY['real_external_api_called']}** |",
        f"| signals_admitted | **{len(admitted_signals)}/{len(signals)}** |",
        f"| TG test sent | **{any_tg_sent}** |",
        f"| secret_preflight_passed | **{preflight_passed}** |",
        f"| quality_gate_any_passed | {any(qg.get('quality_gate_passed', False) for qg in quality_gates)} |",
        f"| send_readiness_any_passed | {any(sr.get('send_readiness_passed', False) for sr in send_readiness_list)} |",
        f"| TG sender available | {tg_available} |",
        "",
        "---",
        "",
        "## Safe Secret Preflight",
        "",
        f"| Check | Result |",
        f"|-------|--------|",
        f"| preflight_run | True |",
        f"| telegram_bot_token_present | {preflight.get('telegram_bot_token_present', False)} |",
        f"| telegram_chat_id_present | {preflight.get('telegram_chat_id_present', False)} |",
        f"| preflight_passed | {preflight_passed} |",
        f"| values_printed | False |",
        f"| values_logged | False |",
        f"| values_in_output | False |",
        "",
        "---",
        "",
        "## API Source",
        "",
        "- **Source**: Binance public REST endpoints",
        "- **Endpoints used**:",
        "  - `/api/v3/ticker/24hr` (spot)",
        "  - `/fapi/v1/ticker/24hr` (futures)",
        "  - `/fapi/v1/openInterest`",
        "  - `/fapi/v1/openInterestHist`",
        "  - `/fapi/v1/fundingRate`",
        "  - `/futures/data/globalLongShortAccountRatio`",
        "  - `/futures/data/takerlongshortRatio`",
        "- **API key required**: No",
        "- **Paid**: No (free public API)",
        "- **Data type**: Liquidation pressure PROXY (保守代理指标，非真实逐笔清算数据)",
        "",
        "---",
        "",
        "## Assets Fetched",
        "",
    ]
    for sym in TARGET_ASSETS:
        label = ASSET_LABELS[sym]
        asset_data = next((a for a in snapshot.get("assets", []) if a["asset"] == label), None)
        if asset_data:
            oi_str = f"{asset_data['open_interest_change_pct']:+.4f}%" if asset_data['open_interest_change_pct'] is not None else "N/A"
            fr_str = f"{asset_data.get('funding_rate_pct', 0):+.4f}%" if asset_data.get('funding_rate_pct') is not None else "N/A"
            report_lines.append(
                f"- **{label}** ({sym}): price_chg={asset_data['price_change_24h_pct']:+.2f}%, "
                f"OI_chg={oi_str}, funding={fr_str}, "
                f"L/S={'可用' if asset_data.get('ls_ratio_available') else 'fallback'}, "
                f"taker={'可用' if asset_data.get('taker_ratio_available') else 'fallback'}"
            )

    report_lines += [
        "",
        "---",
        "",
        "## Liquidation Pressure Proxy Admission Results",
        "",
        f"| Asset | Price Chg | Score | Admitted | Type | Confirm Count | Direction |",
        f"|-------|-----------|-------|----------|------|---------------|-----------|",
    ]
    for sig in signals:
        report_lines.append(
            f"| {sig['asset']} | {sig['price_change_24h_pct']:+.2f}% | "
            f"{sig.get('proxy_pressure_score', '?')} | "
            f"{sig['admission_passed']} | "
            f"{sig.get('pressure_type', 'N/A')} | "
            f"{sig.get('confirm_factor_count', 0)} | "
            f"{sig.get('proxy_pressure_direction', 'N/A')} |"
        )

    report_lines += [
        "",
        "---",
        "",
        "## Gate Results",
        "",
        "### Quality Gate",
        "",
        f"| Asset | QG Passed | Blocked Reasons |",
        f"|-------|-----------|-----------------|",
    ]
    for sig, qg in zip(signals, quality_gates):
        report_lines.append(
            f"| {sig['asset']} | {qg.get('quality_gate_passed', False)} | "
            f"{qg.get('blocked_reasons', [])} |"
        )

    report_lines += [
        "",
        "### Send-Readiness Gate",
        "",
        f"| Asset | SR Passed | TG Ready | Blocked Reasons |",
        f"|-------|-----------|----------|-----------------|",
    ]
    for sig, sr in zip(signals, send_readiness_list):
        report_lines.append(
            f"| {sig['asset']} | {sr.get('send_readiness_passed', False)} | "
            f"{sr.get('tg_test_group_ready', False)} | "
            f"{sr.get('blocked_reasons', [])} |"
        )

    report_lines += [
        "",
        "---",
        "",
        "## TG Send Attempts (v116I Redacted Proof)",
        "",
        f"| Asset | Attempted | Success | Msg ID Redacted | Blocked Reason |",
        f"|-------|-----------|---------|-----------------|----------------|",
    ]
    for sig, ta in zip(signals, tg_attempts):
        if sig.get("admission_passed", False):
            report_lines.append(
                f"| {sig['asset']} | {ta.get('attempted', False)} | "
                f"{ta.get('success', False)} | "
                f"{ta.get('message_id_redacted', 'N/A')} | "
                f"{ta.get('blocked_reason', 'N/A')} |"
            )
        else:
            report_lines.append(
                f"| {sig['asset']} | N/A (not admitted) | N/A | N/A | admission_not_passed |"
            )

    report_lines += [
        "",
        "---",
        "",
        "## Safety Confirmation",
        "",
        f"| Constraint | Status |",
        f"|------------|--------|",
        f"| secret_preflight_run | True |",
        f"| real_external_api_called | {SAFETY['real_external_api_called']} |",
        f"| fixture_only | False |",
        f"| production_send_ready | False |",
        f"| prod_state_write | False |",
        f"| ai_model_called | False |",
        f"| credentials_printed | False |",
        f"| daemon_or_loop_started | False |",
        f"| files_deleted | False |",
        f"| TG target is test group | True |",
        f"| TG target is channel | False |",
        f"| api_key_required | False |",
        f"| one_shot (not loop) | True |",
        f"| token in outputs | False (redacted proof only) |",
        f"| chat_id in outputs | False (redacted proof only) |",
        f"| proxy disclaimer present | True |",
        f"| not masquerading as real tape | True |",
        "",
        "---",
        "",
        "## Conclusion",
        "",
        f"**Audit result**: `{audit_result}`",
        "",
    ]

    if any_tg_sent:
        report_lines.append("TG test group send **SUCCEEDED**. Liquidation pressure proxy card(s) delivered to test group (one-shot).")
        report_lines.append(f"Redacted message proof: {SAFETY.get('tg_message_id_redacted', 'N/A')}")
    elif not any_admitted:
        report_lines.append(
            "No assets reached liquidation pressure proxy admission thresholds. "
            "Gate blocked_gate_not_passed. No cards generated, no TG send attempted."
        )
    elif audit_result == "real_free_api_card_ready_tg_blocked_missing_sender":
        report_lines.append(
            f"Liquidation pressure proxy cards were generated and passed gates, but TG send was **blocked** "
            f"because: {first_blocked}. Cards are ready for manual review."
        )
    else:
        report_lines.append(f"Blocked: {audit_result}")

    report_lines += [
        "",
        "⚠️ **代理数据声明**: 本报告所有指标均为清算压力代理信号。",
        "Binance REST API 不提供直接清算流数据。压力评分基于价格变动、OI变化、",
        "资金费率、多空比和taker买卖比的复合代理估算。实际清算情况以交易所清算数据为准。",
    ]

    ensure_dir(SEND_REPORT_MD)
    with open(SEND_REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")
    print(f"  [OK] {SEND_REPORT_MD}")

    # 10. Handoff markdown
    handoff_lines = [
        f"# Market Radar {VERSION} — Handoff: Liquidation Pressure Proxy Real Free API TG Test Send",
        "",
        f"**Generated**: {generate_timestamp()}",
        f"**Task ID**: {TASK_ID}",
        f"**Run ID**: {RUN_ID}",
        f"**Status**: {'done' if any_tg_sent else 'partial'}",
        f"**result_source**: claude_code_executor",
        f"**executor_lane**: 1",
        f"**project_label**: market_radar",
        "",
        "---",
        "",
        "## Result Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| card_family | `{CARD_FAMILY}` |",
        f"| audit_result | `{audit_result}` |",
        f"| real_external_api_called | **{SAFETY['real_external_api_called']}** |",
        f"| real_free_api_tg_test_sent | **{any_tg_sent}** |",
        f"| secret_preflight_passed | **{preflight_passed}** |",
        f"| signals_generated | {len(signals)} |",
        f"| signals_admitted | {len(admitted_signals)} |",
        f"| api_key_required | False |",
        f"| fixture_only | False |",
        f"| production_send_ready | False |",
        f"| prod_state_write | False |",
        f"| ai_model_called | False |",
        f"| daemon_or_loop_started | False |",
        f"| files_deleted | False |",
        f"| proxy_disclaimer | True (清算压力代理信号) |",
        "",
        "---",
        "",
        "## v116I Safe Secret Preflight",
        "",
        f"| Check | Value |",
        f"|-------|-------|",
        f"| preflight_run | True |",
        f"| telegram_bot_token_present | {preflight.get('telegram_bot_token_present', False)} |",
        f"| telegram_chat_id_present | {preflight.get('telegram_chat_id_present', False)} |",
        f"| preflight_passed | {preflight_passed} |",
        f"| raw values printed | False |",
        f"| raw values in any output | False |",
        "",
        "---",
        "",
        "## Admission Details",
        "",
        f"| Asset | Price Chg | Score | Admitted | Type | Confirm Count |",
        f"|-------|-----------|-------|----------|------|---------------|",
    ]
    for sig in signals:
        handoff_lines.append(
            f"| {sig['asset']} | {sig['price_change_24h_pct']:+.2f}% | "
            f"{sig.get('proxy_pressure_score', '?')} | "
            f"{sig['admission_passed']} | "
            f"{sig.get('pressure_type', 'N/A')} | "
            f"{sig.get('confirm_factor_count', 0)} |"
        )

    handoff_lines += [
        "",
        "---",
        "",
        "## Data Availability",
        "",
        f"| Asset | Funding | L/S Ratio | Taker B/S | OI History | Limitations |",
        f"|-------|---------|-----------|-----------|------------|-------------|",
    ]
    for sig in signals:
        limitations_count = len(sig.get("data_limitations", []))
        handoff_lines.append(
            f"| {sig['asset']} | {sig.get('funding_available', False)} | "
            f"{sig.get('ls_ratio_available', False)} | "
            f"{sig.get('taker_ratio_available', False)} | "
            f"{sig.get('oi_history_available', False)} | "
            f"{limitations_count} |"
        )

    handoff_lines += [
        "",
        "---",
        "",
        "## Files Produced",
        "",
    ]
    for fp in [
        RAW_SNAPSHOTS_JSON, SIGNAL_RECORDS_JSONL, CARD_RECORDS_JSONL,
        QUALITY_GATE_JSONL, SEND_READINESS_JSONL, TG_SEND_ATTEMPTS_JSONL,
        SEND_RESULT_JSON, CARD_PREVIEW_MD, SEND_REPORT_MD, HANDOFF_MD,
    ]:
        handoff_lines.append(f"- `{fp}`")

    handoff_lines += [
        "",
        "---",
        "",
        "## Blocked Reason (if any)",
        "",
        f"{first_blocked if not any_tg_sent else 'N/A — TG test send succeeded'}",
        "",
        "---",
        "",
        "## TG Send Proof (redacted — v116I standard)",
        "",
        f"message_id_present: {any(ta.get('message_id_present', False) for ta in tg_attempts)}",
        f"message_id_redacted: {SAFETY.get('tg_message_id_redacted', 'N/A')}",
        f"token_in_output: False",
        f"chat_id_in_output: False",
        "",
        "---",
        "",
        "## Safety Confirmation",
        "",
        "- [PASS] Secret preflight executed — boolean only, no raw values",
        "- [PASS] No production channel send",
        "- [PASS] No production state written",
        "- [PASS] No AI/model called",
        "- [PASS] No paid API called",
        "- [PASS] No credentials printed to output",
        "- [PASS] No files deleted",
        "- [PASS] No daemon/loop started",
        "- [PASS] One-shot execution only",
        "- [PASS] TG target is test group, not channel",
        "- [PASS] Only redacted message proof recorded",
        "- [PASS] Conservative liquidation pressure proxy admission rules applied",
        "- [PASS] Cards explicitly state liquidation pressure proxy (清算压力代理信号)",
        "- [PASS] No masquerading as real liquidation tape data",
        "",
        "---",
        "",
        "## Unfinished Items / Risks",
        "",
        "1. This is a ONE-SHOT test. No continuous monitoring or automated resend.",
        "2. Liquidation pressure is a PROXY — Binance REST does not provide direct liquidation order data.",
        "3. Long/short ratio endpoint and taker buy/sell ratio endpoint may be unavailable on some Binance API versions; handled via fallback.",
        "4. OI change % relies on 5-minute historical comparison from Binance OI history endpoint; may be noisy.",
        "5. Funding rate extreme thresholds are conservative; may miss moderate funding stress.",
        "6. Proxy pressure score is a composite of up to 4 indicators; missing indicators reduce score but still allow admission with sufficient price move.",
        "7. TG test group send depends on environment variables set by load_local_secrets.ps1.",
        "8. During calm market periods, liquidation pressure proxy signals may not meet admission thresholds.",
        "9. Cross-exchange liquidation data (e.g., Hyperliquid API) not integrated in this version.",
        "10. Cards correctly identify as proxy signals — downstream consumers must not misinterpret as real liquidation tape.",
    ]

    ensure_dir(HANDOFF_MD)
    with open(HANDOFF_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(handoff_lines) + "\n")
    print(f"  [OK] {HANDOFF_MD}")

    return result


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

def main() -> int:
    print("=" * 70)
    print(f"Market Radar {VERSION} — Liquidation Pressure Proxy Real Free API")
    print("TG Test Send (One-Shot)")
    print("ONE-SHOT execution. Not daemon. Not production.")
    print("")
    print("[PROXY] LIQUIDATION PRESSURE PROXY -- not real liquidation tape data")
    print("=" * 70)
    print()

    overall_status = "done"
    final_result = {}

    try:
        # ── Step 0: Safe Secret Preflight ──
        preflight = safe_secret_preflight()

        # ── Step 1: Fetch real data from Binance ──
        spot_tickers = fetch_binance_spot_24hr_tickers()
        futures_tickers = fetch_binance_futures_24hr_tickers()
        open_interests = fetch_binance_open_interest()
        oi_histories = fetch_binance_oi_history()
        funding_rates = fetch_binance_funding_rates()
        ls_ratios = fetch_binance_long_short_ratio()
        taker_ratios = fetch_binance_taker_buy_sell_ratio()

        if not spot_tickers and not futures_tickers:
            print("\n[FATAL] No data from any Binance API. API may be unavailable.")
            SAFETY["real_external_api_called"] = False
            snapshot = {
                "event_id": "blocked_free_api_unavailable",
                "observed_at": generate_timestamp(),
                "assets": [],
                "asset_count": 0,
                "api_source": "Binance (blocked — no response)",
                "api_key_required": False,
                "real_external_api_called": False,
                "blocked": True,
                "block_reason": "free_api_unavailable: no response from Binance public endpoints",
            }
            signals = []
            overall_status = "partial"
        else:
            SAFETY["real_external_api_called"] = True

            # ── Step 2: Build raw snapshot ──
            snapshot = build_raw_snapshot(
                spot_tickers, futures_tickers, open_interests, oi_histories,
                funding_rates, ls_ratios, taker_ratios,
            )

            # ── Step 3: Compute liquidation pressure signals ──
            signals = compute_liquidation_pressure_signals(snapshot)

        # ── Step 4: Generate cards for admitted signals ──
        cards = []
        quality_gates = []
        send_readiness_list = []
        tg_attempts = []

        for sig in signals:
            card_text = ""
            if sig["admission_passed"]:
                print(f"\n[4] Rendering liquidation pressure card for {sig['asset']}...")
                card_text = render_liquidation_pressure_card(sig)
                print(f"  Card rendered: {len(card_text)} chars, {card_text.count(chr(10)) + 1} lines")
            else:
                print(f"\n[4] Skipping card for {sig['asset']} (admission not passed)")
                card_text = f"[BLOCKED] {sig['asset']}: liquidation pressure proxy admission not passed. "
                card_text += f"price_chg={sig['price_change_24h_pct']:+.2f}%, "
                card_text += f"proxy_score={sig.get('proxy_pressure_score', '?')}/10, "
                card_text += f"confirm_factors={sig.get('confirm_factor_count', 0)}. "
                card_text += f"Threshold: {ADMISSION_PRICE_THRESHOLD_PCT}%+2 factors or {ADMISSION_WEAK_PRICE_THRESHOLD_PCT}%+1 factor."

            cards.append({
                "event_id": sig["event_id"],
                "asset": sig["asset"],
                "card_text": card_text,
            })

            # ── Step 5: Quality gate ──
            qg = run_quality_gate(sig, card_text)
            quality_gates.append(qg)

            # ── Step 6: Send-readiness gate ──
            sr = run_send_readiness_gate(sig, qg, preflight)
            send_readiness_list.append(sr)

            # ── Step 7: TG test send ──
            if sig["admission_passed"] and qg.get("quality_gate_passed"):
                ta = attempt_tg_test_send(sig, card_text, sr, preflight)
            else:
                print(f"\n[7] Skipping TG send for {sig['asset']} (gate not passed)")
                ta = {
                    "attempted": False,
                    "success": False,
                    "blocked_reason": "gate_not_passed",
                    "target_type": "test_group",
                    "one_shot": True,
                }
            tg_attempts.append(ta)

        # ── Step 8: Write outputs ──
        final_result = write_outputs(
            preflight, snapshot, signals, cards,
            quality_gates, send_readiness_list, tg_attempts,
        )

        audit_result = final_result.get("audit_result", "blocked_gate_not_passed")
        if not any(ta.get("success", False) for ta in tg_attempts):
            overall_status = "partial"

    except Exception as e:
        print(f"\n[FATAL] Unhandled exception: {e}")
        traceback.print_exc()
        overall_status = "failed"
        audit_result = "blocked_free_api_unavailable"
        final_result = {
            "card_family": CARD_FAMILY,
            "version": VERSION,
            "stage": STAGE,
            "generated_at": generate_timestamp(),
            "real_external_api_called": SAFETY["real_external_api_called"],
            "fixture_only": False,
            "production_send_ready": False,
            "prod_state_write": False,
            "ai_model_called": False,
            "credentials_printed": False,
            "credentials_read_plaintext": False,
            "daemon_or_loop_started": False,
            "files_deleted": False,
            "secret_preflight_run": SAFETY.get("secret_preflight_run", False),
            "audit_result": "blocked_free_api_unavailable",
            "error": str(e)[:300],
        }
        ensure_dir(SEND_RESULT_JSON)
        with open(SEND_RESULT_JSON, "w", encoding="utf-8") as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)

    # ── Final summary ──
    print("\n" + "=" * 70)
    print("EXECUTION COMPLETE")
    print("=" * 70)
    print(f"  Status:              {overall_status}")
    print(f"  card_family:         {CARD_FAMILY}")
    print(f"  real_api_called:     {SAFETY['real_external_api_called']}")
    print(f"  preflight_passed:    {SAFETY['secret_preflight_passed']}")
    print(f"  tg_test_sent:        {SAFETY['tg_test_sent']}")
    print(f"  tg_msg_id_redacted:  {SAFETY.get('tg_message_id_redacted', 'N/A')}")
    print(f"  audit_result:        {final_result.get('audit_result', 'unknown')}")
    print(f"  api_key_required:    False")
    print(f"  fixture_only:        False")
    print(f"  proxy_disclaimer:    清算压力代理信号（非真实逐笔清算数据）")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
