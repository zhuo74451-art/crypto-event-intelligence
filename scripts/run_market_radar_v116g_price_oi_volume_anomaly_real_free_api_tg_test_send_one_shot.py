"""Market Radar v1.16-G — Price/OI/Volume Anomaly Real Free API TG Test Send (One-Shot)

Fetches real market data from Binance PUBLIC endpoints (NO API key required),
computes price_oi_volume_anomaly signals per asset, applies conservative admission
rules, generates cards, runs quality gate and send-readiness gate, then attempts
ONE-SHOT TG test-group send if credentials are available.

THIS IS REAL EXTERNAL API + REAL TG TEST SEND (one-shot only).
Not fixture. Not production. Not daemon/loop.

Free API sources (all Binance public, no key needed):
  - GET /api/v3/ticker/24hr          → 24hr price change, volume
  - GET /fapi/v1/ticker/24hr          → futures 24hr ticker
  - GET /fapi/v1/openInterest         → current open interest
  - GET /fapi/v1/openInterestHist     → historical OI (for OI change %)

Assets: BTCUSDT, ETHUSDT, SOLUSDT (minimum 3 assets)

Anomaly admission (conservative):
  - price move >= 4% AND volume/OI has at least one confirmation factor → admission_passed
  - price move >= 5% even if OI history missing → weak-confirmation card (oi_history_missing: true)
  - If no asset reaches threshold → blocked_gate_not_passed, no TG send

Outputs:
  results/market_radar_v116g_price_oi_volume_anomaly_raw_snapshots.json
  results/market_radar_v116g_price_oi_volume_anomaly_signal_records.jsonl
  results/market_radar_v116g_price_oi_volume_anomaly_card_records.jsonl
  results/market_radar_v116g_price_oi_volume_anomaly_quality_gate_records.jsonl
  results/market_radar_v116g_price_oi_volume_anomaly_send_readiness_records.jsonl
  results/market_radar_v116g_price_oi_volume_anomaly_tg_send_attempts.jsonl
  results/market_radar_v116g_price_oi_volume_anomaly_tg_test_send_result.json
  runs/market_radar/v116g_price_oi_volume_anomaly_card_preview.md
  runs/market_radar/v116g_price_oi_volume_anomaly_tg_test_send_report.md
  runs/market_radar/v116g_price_oi_volume_anomaly_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v116g_price_oi_volume_anomaly_real_free_api_tg_test_send_one_shot.py
"""

from __future__ import annotations

import hashlib
import json
import os
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
CARD_FAMILY = "price_oi_volume_anomaly"
VERSION = "v1.16-G"
STAGE = "v116g_price_oi_volume_anomaly_real_free_api_tg_test_send_one_shot"
TASK_ID = "20260605_v116g_price_oi_volume_anomaly_real_free_api_tg_test_send_one_shot"
RUN_ID = "20260605_121906"
CN_TZ = timezone(timedelta(hours=8))

# Assets to fetch
TARGET_ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
ASSET_LABELS = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL"}

# ── Free public API endpoints (NO API key needed) ────────────────────────
BINANCE_SPOT_TICKER_24HR = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_FUTURES_TICKER_24HR = "https://fapi.binance.com/fapi/v1/ticker/24hr"
BINANCE_FUTURES_OPEN_INTEREST = "https://fapi.binance.com/fapi/v1/openInterest"
BINANCE_FUTURES_OI_HIST = "https://fapi.binance.com/fapi/v1/openInterestHist"

# ── Anomaly admission thresholds ─────────────────────────────────────────
ADMISSION_PRICE_THRESHOLD_PCT = 4.0       # >= 4% + confirmation factor
ADMISSION_WEAK_PRICE_THRESHOLD_PCT = 5.0  # >= 5% even without OI history
VOLUME_CONFIRMATION_THRESHOLD_USD = 500_000_000  # $500M quote volume as confirmation

# ── Output paths ─────────────────────────────────────────────────────────
OUTPUT_DIR = ROOT / "results"
RUNS_DIR = ROOT / "runs" / "market_radar"

RAW_SNAPSHOTS_JSON = OUTPUT_DIR / "market_radar_v116g_price_oi_volume_anomaly_raw_snapshots.json"
SIGNAL_RECORDS_JSONL = OUTPUT_DIR / "market_radar_v116g_price_oi_volume_anomaly_signal_records.jsonl"
CARD_RECORDS_JSONL = OUTPUT_DIR / "market_radar_v116g_price_oi_volume_anomaly_card_records.jsonl"
QUALITY_GATE_JSONL = OUTPUT_DIR / "market_radar_v116g_price_oi_volume_anomaly_quality_gate_records.jsonl"
SEND_READINESS_JSONL = OUTPUT_DIR / "market_radar_v116g_price_oi_volume_anomaly_send_readiness_records.jsonl"
TG_SEND_ATTEMPTS_JSONL = OUTPUT_DIR / "market_radar_v116g_price_oi_volume_anomaly_tg_send_attempts.jsonl"
SEND_RESULT_JSON = OUTPUT_DIR / "market_radar_v116g_price_oi_volume_anomaly_tg_test_send_result.json"
CARD_PREVIEW_MD = RUNS_DIR / "v116g_price_oi_volume_anomaly_card_preview.md"
SEND_REPORT_MD = RUNS_DIR / "v116g_price_oi_volume_anomaly_tg_test_send_report.md"
HANDOFF_MD = RUNS_DIR / "v116g_price_oi_volume_anomaly_local_only_handoff.md"

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
                      f"vol={t['quoteVolume']}, high={t.get('highPrice')}, low={t.get('lowPrice')}")
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
                "data": [...],       # raw OI history data points
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
                print(f"  {sym}: OI={data[0].get('sumOpenInterest', '?')} (only 1 data point, "
                      f"cannot compute OI change %)")
            else:
                entry["fallback_reason"] = "oi_history_endpoint_returned_empty"
                print(f"  {sym}: no OI history data returned from endpoint")
        except Exception as e:
            entry["fallback_reason"] = f"oi_history_fetch_error: {str(e)[:100]}"
            print(f"  {sym}: ERROR fetching OI history: {e}")

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

        oi_change_pct = oi_hist_entry.get("oi_change_pct")
        oi_history_available = oi_hist_entry.get("oi_history_available", False)
        oi_fallback_reason = oi_hist_entry.get("fallback_reason")

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
            "is_fixture": False,
            "data_source": "binance_public_api",
        }
        assets.append(asset_entry)

        oi_str = f"{oi_change_pct:+.4f}%" if oi_change_pct is not None else "N/A"
        print(f"  {label}: price={last_price}, price_chg={price_change_pct:+.2f}%, "
              f"quote_vol=${quote_volume_24h:,.0f}, OI={open_interest_current:,.0f}, "
              f"OI_chg={oi_str}, OI_hist_avail={oi_history_available}")

    snapshot = {
        "event_id": f"real_pova_{datetime.now(CN_TZ).strftime('%Y%m%d_%H%M%S')}",
        "observed_at": observed_at,
        "assets": assets,
        "asset_count": len(assets),
        "api_source": "Binance public REST endpoints (no API key)",
        "api_key_required": False,
        "is_fixture": False,
        "data_mode": "real_external_api",
        "real_external_api_called": True,
        "fetch_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    print(f"  Built snapshot with {len(assets)} assets from real Binance API")
    return snapshot


# ══════════════════════════════════════════════════════════════════════════
# Step 3: Compute anomaly signals per asset (conservative admission)
# ══════════════════════════════════════════════════════════════════════════

def compute_anomaly_signals(snapshot: dict) -> list[dict]:
    """Compute price_oi_volume_anomaly signals for each asset.

    Conservative admission rules:
      - price move >= 4% AND (volume/USD confirmation OR OI confirmation) → admission_passed
      - price move >= 5% even without OI history → weak-confirmation (oi_history_missing: true)
      - Otherwise → blocked_gate_not_passed
    """
    print("\n[3] Computing anomaly signals per asset...")

    assets = snapshot["assets"]
    signals = []

    for asset in assets:
        label = asset["asset"]
        sym = asset["symbol"]
        price_chg = asset["price_change_24h_pct"]
        futures_price_chg = asset["futures_price_change_24h_pct"]
        quote_vol = asset["quote_volume_24h"]
        oi_current = asset["open_interest_current"]
        oi_change_pct = asset["open_interest_change_pct"]
        oi_history_available = asset["oi_history_available"]
        oi_fallback_reason = asset["oi_fallback_reason"]

        abs_price_chg = abs(price_chg)
        direction = "up" if price_chg >= 0 else "down"

        # Determine confirmation factors
        confirmation_factors = []

        # Volume confirmation: quote volume > threshold
        vol_confirm = quote_vol >= VOLUME_CONFIRMATION_THRESHOLD_USD
        if vol_confirm:
            confirmation_factors.append(f"volume_confirm: quote_vol=${quote_vol:,.0f} >= ${VOLUME_CONFIRMATION_THRESHOLD_USD:,.0f}")

        # OI confirmation: OI change aligns with price direction
        oi_confirm = False
        if oi_history_available and oi_change_pct is not None:
            if (price_chg > 0 and oi_change_pct > 0) or (price_chg < 0 and oi_change_pct < 0):
                oi_confirm = True
                confirmation_factors.append(f"oi_confirm: OI_chg={oi_change_pct:+.4f}% aligned with price {direction}")
            elif abs(oi_change_pct) > 2.0:
                # OI changed significantly but direction may diverge
                confirmation_factors.append(f"oi_significant: OI_chg={oi_change_pct:+.4f}% (magnitude >2%)")

        # Futures-spot convergence
        if abs(price_chg) > 0 and abs(futures_price_chg) > 0:
            spot_fut_diff = abs(price_chg - futures_price_chg)
            if spot_fut_diff < 1.0:
                confirmation_factors.append(f"spot_futures_convergent: spot_chg={price_chg:+.2f}%, fut_chg={futures_price_chg:+.2f}%")

        has_confirm_factor = len(confirmation_factors) > 0

        # Determine anomaly type
        anomaly_type = None
        admission_passed = False

        if abs_price_chg >= ADMISSION_PRICE_THRESHOLD_PCT and has_confirm_factor:
            # Standard admission: >= 4% + confirmation factor
            anomaly_type = f"{direction}_anomaly_confirmed"
            admission_passed = True
            print(f"  {label}: [ADMIT] price_chg={price_chg:+.2f}%, confirm_factors={len(confirmation_factors)}")
        elif abs_price_chg >= ADMISSION_WEAK_PRICE_THRESHOLD_PCT and not oi_history_available:
            # Weak admission: >= 5% but OI history missing
            anomaly_type = f"{direction}_anomaly_weak_confirm"
            admission_passed = True
            print(f"  {label}: [ADMIT-WEAK] price_chg={price_chg:+.2f}%, OI_history_missing, "
                  f"reason={oi_fallback_reason}")
        elif abs_price_chg >= ADMISSION_WEAK_PRICE_THRESHOLD_PCT and has_confirm_factor:
            # >= 5% with confirmation factor (strong signal)
            anomaly_type = f"{direction}_anomaly_strong"
            admission_passed = True
            print(f"  {label}: [ADMIT-STRONG] price_chg={price_chg:+.2f}%, confirm_factors={len(confirmation_factors)}")
        elif abs_price_chg >= ADMISSION_PRICE_THRESHOLD_PCT and not has_confirm_factor:
            # >= 4% but no confirmation factor — borderline, report as anomaly but not admitted
            anomaly_type = f"{direction}_anomaly_unconfirmed"
            admission_passed = False
            print(f"  {label}: [BLOCKED] price_chg={price_chg:+.2f}% >= {ADMISSION_PRICE_THRESHOLD_PCT}% "
                  f"but no confirmation factors")
        else:
            print(f"  {label}: [BELOW_THRESHOLD] price_chg={price_chg:+.2f}% < "
                  f"{ADMISSION_PRICE_THRESHOLD_PCT}%")

        signal = {
            "card_family": CARD_FAMILY,
            "event_id": f"{snapshot['event_id']}_{label.lower()}",
            "observed_at": snapshot["observed_at"],
            "asset": label,
            "symbol": sym,
            "price": asset["price"],
            "price_change_24h_pct": price_chg,
            "futures_price_change_24h_pct": futures_price_chg,
            "volume_24h": asset["volume_24h"],
            "quote_volume_24h": quote_vol,
            "high_24h": asset["high_24h"],
            "low_24h": asset["low_24h"],
            "open_interest_current": oi_current,
            "open_interest_change_pct": oi_change_pct,
            "oi_history_available": oi_history_available,
            "oi_fallback_reason": oi_fallback_reason,
            "oi_history_missing": not oi_history_available,
            "direction": direction,
            "anomaly_type": anomaly_type,
            "confirmation_factors": confirmation_factors,
            "has_confirm_factor": has_confirm_factor,
            "admission_passed": admission_passed,
            "api_source": "Binance public REST endpoints (no API key)",
            "api_key_required": False,
            "real_external_api_called": True,
            "is_fixture": False,
            "data_mode": "real_external_api",
        }
        signals.append(signal)

    admitted = sum(1 for s in signals if s["admission_passed"])
    total = len(signals)
    print(f"  Summary: {admitted}/{total} assets admitted for anomaly cards")

    if admitted == 0:
        print("  [BLOCKED] No assets reached admission threshold. "
              "Gate will be blocked_gate_not_passed.")

    return signals


# ══════════════════════════════════════════════════════════════════════════
# Step 4: Render anomaly cards (NO AI/model called)
# ══════════════════════════════════════════════════════════════════════════

def render_anomaly_card(signal: dict) -> str:
    """Render a price_oi_volume_anomaly card in Chinese.

    This is a self-contained renderer that does NOT call any AI/model.
    """
    label = signal["asset"]
    sym = signal["symbol"]
    direction = signal["direction"]
    price_chg = signal["price_change_24h_pct"]
    futures_price_chg = signal["futures_price_change_24h_pct"]
    quote_vol = signal["quote_volume_24h"]
    oi_current = signal["open_interest_current"]
    oi_change_pct = signal["open_interest_change_pct"]
    oi_history_missing = signal["oi_history_missing"]
    anomaly_type = signal["anomaly_type"]
    confirm_factors = signal["confirmation_factors"]
    price = signal["price"]
    high_24h = signal.get("high_24h", 0)
    low_24h = signal.get("low_24h", 0)

    if direction == "up":
        dir_icon = "\U0001f4c8"  # 📈
        dir_text = "上涨"
    else:
        dir_icon = "\U0001f4c9"  # 📉
        dir_text = "下跌"

    # Determine anomaly severity label
    if "strong" in (anomaly_type or ""):
        severity = "强烈异常"
        severity_icon = "\U0001f534"  # 🔴
    elif "confirmed" in (anomaly_type or ""):
        severity = "确认异常"
        severity_icon = "\U0001f7e0"  # 🟠
    elif "weak" in (anomaly_type or ""):
        severity = "弱确认异常"
        severity_icon = "\U0001f7e1"  # 🟡
    else:
        severity = "未确认异动"
        severity_icon = "⚪"

    # Build reason text
    reason_parts = [f"{label} 24小时{direction}幅度 {abs(price_chg):.2f}%"]

    if futures_price_chg != 0:
        reason_parts.append(f"合约同步变化 {futures_price_chg:+.2f}%")

    if not oi_history_missing and oi_change_pct is not None:
        reason_parts.append(f"OI变化 {oi_change_pct:+.2f}%")
    elif oi_history_missing:
        reason_parts.append("OI历史数据不可用")

    reason = f"检测到{', '.join(reason_parts)}。"

    # Confirmation details
    confirm_lines = []
    if confirm_factors:
        for cf in confirm_factors:
            confirm_lines.append(f"● {cf}")
    else:
        confirm_lines.append("● 无确认因子（弱信号）")

    oi_line = f"● OI变化：{oi_change_pct:+.4f}%" if oi_change_pct is not None else "● OI变化：N/A（历史数据不可用）"
    oi_warning = "\n⚠️ OI历史数据缺失，本信号为弱确认异常。" if oi_history_missing else ""

    card_lines = [
        f"{dir_icon} {severity_icon} 价格/OI/成交量异常｜{label} {dir_text}",
        "",
        f"一句话：{reason}",
        "",
        f"● 资产：{label} ({sym})",
        f"● 当前价格：${price:,.2f}",
        f"● 24h涨跌幅：{price_chg:+.2f}%",
        f"● 合约24h涨跌幅：{futures_price_chg:+.2f}%",
        f"● 24h最高：${high_24h:,.2f}",
        f"● 24h最低：${low_24h:,.2f}",
        f"● 24h成交量（Quote）：${quote_vol:,.0f}",
        f"● 当前OI：{oi_current:,.0f}",
        oi_line,
        f"● 异常类型：{anomaly_type or 'N/A'}",
        f"● 异常等级：{severity}",
        "",
        "确认因子：",
    ] + confirm_lines + [
        "",
        f"\U0001f550 观测时间：{signal['observed_at']}",
        "",
        "\U0001f4a1 说明：价格/OI/成交量异常可能反映市场短期情绪或",
        "资金流动，不代表趋势延续。不构成交易建议。",
        oi_warning,
        "",
        "\U0001f4ca 数据源：Binance 公开行情 API（免费，无需 API Key）",
        "",
        "\U0001f510 v116G 安全预检通过 | 真实API | 测试群 one-shot 发送",
    ]

    card_text = "\n".join(line for line in card_lines if line)
    return card_text


# ══════════════════════════════════════════════════════════════════════════
# Step 5: Quality Gate
# ══════════════════════════════════════════════════════════════════════════

def run_quality_gate(signal: dict, card_text: str) -> dict:
    """Run quality gate checks on the anomaly signal and card."""
    print(f"\n[5] Running quality gate for {signal['asset']}...")

    required_fields = [
        "card_family", "event_id", "asset", "symbol",
        "price_change_24h_pct", "quote_volume_24h",
        "open_interest_current", "anomaly_type",
    ]
    required_present = all(signal.get(f) is not None for f in required_fields)

    card_present = bool(card_text and len(card_text) > 100)
    family_correct = signal.get("card_family") == CARD_FAMILY
    asset_present = bool(signal.get("asset") and signal.get("symbol"))

    # No investment advice
    no_trading_advice = True
    bad_phrases = ["买入", "卖出", "做多", "做空", "all in", "满仓", "清仓",
                   "必涨", "必跌", "稳赚", "抄底", "梭哈"]
    for phrase in bad_phrases:
        if phrase in card_text:
            no_trading_advice = False
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
        "api_source_ok": api_source_ok,
        "real_api_ok": real_api_ok,
        "not_fixture": not_fixture,
        "admission_passed": admission_ok,
        "oi_history_missing": signal.get("oi_history_missing", False),
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
        if bot_token and bot_token in error_str:
            error_str = error_str.replace(bot_token, "[REDACTED_TOKEN]")
        if chat_id and chat_id in error_str:
            error_str = error_str.replace(chat_id, "[REDACTED_CHAT_ID]")
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
        # Card is ready but TG was not attempted (shouldn't normally happen)
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
        # v116G preflight fields
        "secret_preflight_run": preflight.get("preflight_passed", False) or True,
        "telegram_bot_token_present": preflight.get("telegram_bot_token_present", False),
        "telegram_chat_id_present": preflight.get("telegram_chat_id_present", False),
        "secret_preflight_passed": preflight_passed,
        # Standard fields
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
        f"# Market Radar {VERSION} — Price/OI/Volume Anomaly Card Preview",
        "",
        f"**Generated**: {generate_timestamp()}",
        f"**Card Family**: `{CARD_FAMILY}`",
        f"**API Source**: Binance public REST endpoints (free, no API key)",
        f"**Assets**: {', '.join(TARGET_ASSETS)}",
        f"**Preflight**: {'PASS' if preflight_passed else 'BLOCKED'}",
        f"**Admitted**: {len(admitted_signals)}/{len(signals)}",
        "",
        "---",
        "",
        "## Admission Summary",
        "",
        f"| Asset | Price Chg | QVol | OI Chg | OI Hist | Admitted | Type |",
        f"|-------|-----------|------|--------|---------|----------|------|",
    ]
    for sig in signals:
        oi_str = f"{sig['open_interest_change_pct']:+.2f}%" if sig['open_interest_change_pct'] is not None else "N/A"
        preview_lines.append(
            f"| {sig['asset']} | {sig['price_change_24h_pct']:+.2f}% | "
            f"${sig['quote_volume_24h']:,.0f} | {oi_str} | "
            f"{sig['oi_history_available']} | {sig['admission_passed']} | "
            f"{sig.get('anomaly_type', 'N/A')} |"
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
        "## Signal Metrics",
        "",
        f"| Asset | Anomaly Type | Confirm Factors | Admitted |",
        f"|-------|-------------|-----------------|----------|",
    ]
    for sig in signals:
        preview_lines.append(
            f"| {sig['asset']} | {sig.get('anomaly_type', 'N/A')} | "
            f"{len(sig.get('confirmation_factors', []))} | "
            f"{sig['admission_passed']} |"
        )

    preview_lines += [
        "",
        "---",
        "",
        "## v116G Safety Flags",
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
        f"# Market Radar {VERSION} — Price/OI/Volume Anomaly TG Test Send Report",
        "",
        f"**Generated**: {generate_timestamp()}",
        f"**Task ID**: {TASK_ID}",
        f"**Run ID**: {RUN_ID}",
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
        "- **Endpoints used**: `/api/v3/ticker/24hr`, `/fapi/v1/ticker/24hr`, `/fapi/v1/openInterest`, `/fapi/v1/openInterestHist`",
        "- **API key required**: No",
        "- **Paid**: No (free public API)",
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
            report_lines.append(
                f"- **{label}** ({sym}): price_chg={asset_data['price_change_24h_pct']:+.2f}%, "
                f"OI_chg={oi_str}, "
                f"OI_hist_avail={asset_data['oi_history_available']}"
            )

    report_lines += [
        "",
        "---",
        "",
        "## Anomaly Admission Results",
        "",
        f"| Asset | Price Chg | Admitted | Anomaly Type | Confirm Factors | OI Missing |",
        f"|-------|-----------|----------|-------------|-----------------|------------|",
    ]
    for sig in signals:
        report_lines.append(
            f"| {sig['asset']} | {sig['price_change_24h_pct']:+.2f}% | "
            f"{sig['admission_passed']} | "
            f"{sig.get('anomaly_type', 'N/A')} | "
            f"{len(sig.get('confirmation_factors', []))} | "
            f"{sig.get('oi_history_missing', False)} |"
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
        "## TG Send Attempts (v116G Redacted Proof)",
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
        "",
        "---",
        "",
        "## Conclusion",
        "",
        f"**Audit result**: `{audit_result}`",
        "",
    ]

    if any_tg_sent:
        report_lines.append("TG test group send **SUCCEEDED**. Anomaly card(s) delivered to test group (one-shot).")
        report_lines.append(f"Redacted message proof: {SAFETY.get('tg_message_id_redacted', 'N/A')}")
    elif not any_admitted:
        report_lines.append(
            "No assets reached anomaly admission thresholds. Gate blocked_gate_not_passed. "
            "No cards generated, no TG send attempted."
        )
    elif audit_result == "real_free_api_card_ready_tg_blocked_missing_sender":
        report_lines.append(
            f"Anomaly cards were generated and passed gates, but TG send was **blocked** "
            f"because: {first_blocked}. Cards are ready for manual review."
        )
    else:
        report_lines.append(f"Blocked: {audit_result}")

    ensure_dir(SEND_REPORT_MD)
    with open(SEND_REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")
    print(f"  [OK] {SEND_REPORT_MD}")

    # 10. Handoff markdown
    handoff_lines = [
        f"# Market Radar {VERSION} — Handoff: Price/OI/Volume Anomaly Real Free API TG Test Send",
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
        "",
        "---",
        "",
        "## v116G Safe Secret Preflight",
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
        f"| Asset | Price Chg | Admitted | Anomaly Type | OI Missing |",
        f"|-------|-----------|----------|-------------|------------|",
    ]
    for sig in signals:
        handoff_lines.append(
            f"| {sig['asset']} | {sig['price_change_24h_pct']:+.2f}% | "
            f"{sig['admission_passed']} | "
            f"{sig.get('anomaly_type', 'N/A')} | "
            f"{sig.get('oi_history_missing', False)} |"
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
        "## TG Send Proof (redacted — v116G standard)",
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
        "- [PASS] Conservative anomaly admission rules applied",
        "",
        "---",
        "",
        "## Unfinished Items / Risks",
        "",
        "1. This is a ONE-SHOT test. No continuous monitoring or automated resend.",
        "2. OI change % relies on 5-minute historical comparison from Binance OI history endpoint; may be noisy.",
        "3. OI history endpoint may return insufficient data points for some assets; handled via fallback.",
        "4. Volume confirmation uses spot quote volume threshold; may not capture futures-specific volume anomalies.",
        "5. TG test group send depends on environment variables set by load_local_secrets.ps1.",
        "6. Conservative admission thresholds (4%/5%) may miss moderate but meaningful anomalies.",
        "7. No multi-timeframe analysis; only 24h window currently evaluated.",
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
    print(f"Market Radar {VERSION} — Price/OI/Volume Anomaly Real Free API")
    print("TG Test Send (One-Shot)")
    print("ONE-SHOT execution. Not daemon. Not production.")
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
            )

            # ── Step 3: Compute anomaly signals ──
            signals = compute_anomaly_signals(snapshot)

        # ── Step 4: Generate cards for admitted signals ──
        cards = []
        quality_gates = []
        send_readiness_list = []
        tg_attempts = []

        for sig in signals:
            card_text = ""
            if sig["admission_passed"]:
                print(f"\n[4] Rendering anomaly card for {sig['asset']}...")
                card_text = render_anomaly_card(sig)
                print(f"  Card rendered: {len(card_text)} chars, {card_text.count(chr(10)) + 1} lines")
            else:
                print(f"\n[4] Skipping card for {sig['asset']} (admission not passed)")
                card_text = f"[BLOCKED] {sig['asset']}: admission not passed. "
                card_text += f"price_chg={sig['price_change_24h_pct']:+.2f}%. "
                card_text += f"Threshold: {ADMISSION_PRICE_THRESHOLD_PCT}%+confirm or {ADMISSION_WEAK_PRICE_THRESHOLD_PCT}% weak."

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
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
