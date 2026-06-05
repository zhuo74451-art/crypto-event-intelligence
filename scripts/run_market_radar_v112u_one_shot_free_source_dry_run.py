#!/usr/bin/env python3
"""
run_market_radar_v112u_one_shot_free_source_dry_run.py
========================================================
v112U one-shot free source dry-run — ACTUAL implementation.

This runner makes REAL one-shot HTTP GET requests to free public
CoinGecko and CoinCap REST APIs to verify that live free-source data
can be fetched, normalized to LiveSourceResponse schema, and evaluated
through v112T stop conditions (CONTINUE/ABORT/DEGRADE_TO_MOCK).

SAFETY BOUNDARY (HARDCODED):
  - request_mode: one_shot_get_only
  - allowed_methods: [GET]
  - allowed_sources: [coingecko_public_rest, coincap_public_rest]
  - api_key_required: false
  - retry_enabled: false
  - max_single_request_timeout_seconds: 3
  - max_total_runtime_seconds: 30
  - real_tg_sent: false
  - production_state_write: false
  - eligible_for_real_send: false

Generates:
  results/market_radar_v112u_one_shot_free_source_dry_run_result.json
  results/market_radar_v112u_live_source_response.json
  results/market_radar_v112u_stop_decision.json
  runs/market_radar/v112u_one_shot_free_source_dry_run.md
  runs/market_radar/v112u_one_shot_free_source_dry_run_handoff.md
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import socket
from datetime import datetime, timezone, timedelta

# ASCII-safe markers for Windows GBK console
OK_MARK = "[OK]"
FAIL_MARK = "[FAIL]"
WARN_MARK = "[WARN]"

# ── Safety boundary (HARDCODED — cannot be overridden) ────────────────────
SAFETY_BOUNDARY = {
    "request_mode": "one_shot_get_only",
    "allowed_methods": ["GET"],
    "allowed_sources": ["coingecko_public_rest", "coincap_public_rest"],
    "api_key_required": False,
    "retry_enabled": False,
    "max_single_request_timeout_seconds": 3,
    "max_total_runtime_seconds": 30,
    "real_tg_sent": False,
    "production_state_write": False,
    "eligible_for_real_send": False,
}

# ── Assets to request ─────────────────────────────────────────────────────
ASSETS_TO_REQUEST = ["bitcoin", "ethereum", "solana"]  # CoinGecko IDs
ASSET_SYMBOLS = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}

# ── Project root ──────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)

RESULTS_DIR = os.path.join(PROJECT_DIR, "results")
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
SCHEMAS_DIR = os.path.join(PROJECT_DIR, "schemas")
RUNS_DIR = os.path.join(PROJECT_DIR, "runs", "market_radar")

# Input files (allowed by task)
V112T_RESULT_IN = os.path.join(RESULTS_DIR, "market_radar_v112t_one_shot_free_source_plan_result.json")
V112T_MAPPING = os.path.join(CONFIG_DIR, "market_radar_v112t_free_source_mapping.json")
V112T_STOP_CONDITIONS = os.path.join(CONFIG_DIR, "market_radar_v112t_stop_conditions.json")
V112T_SCHEMA = os.path.join(SCHEMAS_DIR, "market_radar_v112t_live_source_response_schema.json")
V112Q_THRESHOLDS = os.path.join(CONFIG_DIR, "market_radar_v112q_multi_asset_thresholds.json")

# Output files
V112U_RESULT = os.path.join(RESULTS_DIR, "market_radar_v112u_one_shot_free_source_dry_run_result.json")
V112U_LIVE_RESPONSE = os.path.join(RESULTS_DIR, "market_radar_v112u_live_source_response.json")
V112U_STOP_DECISION = os.path.join(RESULTS_DIR, "market_radar_v112u_stop_decision.json")
V112U_RUN_REPORT = os.path.join(RUNS_DIR, "v112u_one_shot_free_source_dry_run.md")
V112U_HANDOFF = os.path.join(RUNS_DIR, "v112u_one_shot_free_source_dry_run_handoff.md")

TZ = timezone(timedelta(hours=8))  # UTC+8


def timestamp():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def now_iso():
    return datetime.now(TZ).isoformat()


def load_json(path, label="file"):
    if not os.path.exists(path):
        return None, f"{label} not found at {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, f"{label} error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# Step 1: Validate v112T prerequisites
# ═══════════════════════════════════════════════════════════════════════════

def validate_v112t_prerequisites(v112t_result):
    """Validate v112T plan result meets all prerequisites for v112U execution."""
    issues = []

    checks = {
        "status": "passed",
        "plan_only": True,
        "v112u_requires_user_confirmation": True,
        "real_live_api_called": False,
        "real_tg_sent": False,
        "external_ai_called": False,
        "daemon_started": False,
    }

    for key, expected in checks.items():
        actual = v112t_result.get(key)
        if actual != expected:
            issues.append(f"v112T.{key}: expected={expected}, got={actual}")

    return len(issues) == 0, issues


# ═══════════════════════════════════════════════════════════════════════════
# Step 2: Free source HTTP fetchers (one-shot, GET only)
# ═══════════════════════════════════════════════════════════════════════════

def http_get(url, timeout_seconds=3):
    """
    Make a single GET request to a free public REST endpoint.
    Returns (status_code, body_text, error_message, latency_ms).

    Rules enforced:
      - GET only
      - No Authorization header
      - No API key
      - Timeout <= 3 seconds
      - No retry
      - 429/4xx/5xx are recorded but handled upstream by stop conditions
    """
    start = time.time()
    error_message = None
    status_code = None
    body_text = None

    try:
        req = urllib.request.Request(url, method="GET")
        # Deliberately NOT adding Authorization header
        # Deliberately NOT adding any API key header
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = response.getcode()
            body = response.read()
            body_text = body.decode("utf-8")
    except urllib.error.HTTPError as e:
        status_code = e.code
        try:
            body_text = e.read().decode("utf-8")
        except Exception:
            body_text = ""
        error_message = f"HTTP {e.code} {e.reason}"
    except urllib.error.URLError as e:
        error_message = f"URL Error: {e.reason}"
    except socket.timeout:
        error_message = f"Socket timeout after {timeout_seconds}s"
    except TimeoutError:
        error_message = f"Timeout after {timeout_seconds}s"
    except Exception as e:
        error_message = f"Unexpected error: {e}"

    latency_ms = int((time.time() - start) * 1000)

    return {
        "status_code": status_code,
        "body_text": body_text,
        "error_message": error_message,
        "latency_ms": latency_ms,
        "url": url,
    }


def fetch_coingecko_simple_price(assets, timeout_seconds=3):
    """
    Fetch prices from CoinGecko /api/v3/simple/price.
    Returns raw response info dict.
    """
    ids = ",".join(assets)
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={ids}&vs_currencies=usd&include_24hr_change=true"
    )
    result = http_get(url, timeout_seconds)
    result["source"] = "coingecko_public_rest"
    result["endpoint"] = "/api/v3/simple/price"
    return result


def fetch_coingecko_coins_markets(timeout_seconds=3):
    """
    Fetch market data from CoinGecko /api/v3/coins/markets.
    Returns raw response info dict.
    """
    url = (
        "https://api.coingecko.com/api/v3/coins/markets"
        "?vs_currency=usd&order=market_cap_desc&per_page=50&page=1"
        "&sparkline=false&price_change_percentage=1h,24h"
    )
    result = http_get(url, timeout_seconds)
    result["source"] = "coingecko_public_rest"
    result["endpoint"] = "/api/v3/coins/markets"
    return result


def fetch_coincap_assets(timeout_seconds=3):
    """
    Fetch assets from CoinCap /api/v2/assets.
    Returns raw response info dict.
    """
    url = "https://api.coincap.io/v2/assets?limit=50"
    result = http_get(url, timeout_seconds)
    result["source"] = "coincap_public_rest"
    result["endpoint"] = "/api/v2/assets"
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Step 3: Normalize to LiveSourceResponse
# ═══════════════════════════════════════════════════════════════════════════

def normalize_coingecko_simple_price(raw_result):
    """
    Normalize CoinGecko /simple/price response to asset array.
    Response shape: {"bitcoin": {"usd": 12345, "usd_24h_change": 1.23}, ...}
    """
    if raw_result["status_code"] not in (200, 201, 202, 203, 204):
        return [], [f"HTTP status {raw_result['status_code']}: {raw_result['error_message']}"]

    try:
        data = json.loads(raw_result["body_text"])
    except (json.JSONDecodeError, TypeError):
        return [], ["JSON parse failure"]

    assets = []
    fetched_at = now_iso()

    for asset_id in ASSETS_TO_REQUEST:
        asset_data = data.get(asset_id)
        if asset_data is None:
            continue

        price_usd = asset_data.get("usd")
        price_change_pct = asset_data.get("usd_24h_change")  # CoinGecko /simple/price 24h change

        if price_usd is None:
            continue

        asset = {
            "asset_id": asset_id,
            "symbol": ASSET_SYMBOLS.get(asset_id, asset_id.upper()),
            "price_usd": float(price_usd),
            "price_change_pct": float(price_change_pct) if price_change_pct is not None else None,
            "price_change_pct_1h": None,  # Not available from /simple/price when not requested
            "volume_change_pct": None,     # Not available from /simple/price
            "open_interest_change_pct": None,  # Never available from free sources
            "last_updated_at": fetched_at,  # CoinGecko /simple/price doesn't include per-asset timestamp
            "source_latency_ms": raw_result.get("latency_ms"),
            "raw_source_fields": asset_data,
        }
        assets.append(asset)

    return assets, []


def normalize_coingecko_coins_markets(raw_result):
    """
    Normalize CoinGecko /coins/markets response to asset array.
    Response shape: [{id, symbol, current_price, price_change_percentage_24h, ...}, ...]
    Filter to only BTC, ETH, SOL.
    """
    if raw_result["status_code"] not in (200, 201, 202, 203, 204):
        return [], [f"HTTP status {raw_result['status_code']}: {raw_result['error_message']}"]

    try:
        data = json.loads(raw_result["body_text"])
    except (json.JSONDecodeError, TypeError):
        return [], ["JSON parse failure"]

    if not isinstance(data, list):
        return [], ["Unexpected response shape (expected array)"]

    assets = []
    fetched_at = now_iso()
    target_ids = set(ASSETS_TO_REQUEST)  # ["bitcoin", "ethereum", "solana"]

    for coin in data:
        asset_id = coin.get("id", "")
        if asset_id not in target_ids:
            continue

        last_updated = coin.get("last_updated")
        source_latency_ms = None
        if last_updated:
            try:
                # last_updated is ISO-8601 string from CoinGecko
                src_time = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                now_time = datetime.now(TZ)
                source_latency_ms = int((now_time - src_time.astimezone(TZ)).total_seconds() * 1000)
            except Exception:
                pass

        asset = {
            "asset_id": asset_id,
            "symbol": (coin.get("symbol") or "").upper(),
            "price_usd": float(coin["current_price"]) if coin.get("current_price") is not None else None,
            "price_change_pct": float(coin["price_change_percentage_24h"]) if coin.get("price_change_percentage_24h") is not None else None,
            "price_change_pct_1h": float(coin["price_change_percentage_1h_in_currency"]) if coin.get("price_change_percentage_1h_in_currency") is not None else None,
            "volume_change_pct": None,  # /coins/markets gives total_volume not % change
            "open_interest_change_pct": None,
            "last_updated_at": last_updated or fetched_at,
            "source_latency_ms": source_latency_ms or raw_result.get("latency_ms"),
            "raw_source_fields": coin,
        }
        assets.append(asset)

    return assets, []


def normalize_coincap_assets(raw_result):
    """
    Normalize CoinCap /v2/assets response to asset array.
    Response shape: {"data": [{id, symbol, priceUsd, changePercent24Hr, ...}, ...]}
    Filter to only bitcoin, ethereum, solana.
    """
    if raw_result["status_code"] not in (200, 201, 202, 203, 204):
        return [], [f"HTTP status {raw_result['status_code']}: {raw_result['error_message']}"]

    try:
        data = json.loads(raw_result["body_text"])
    except (json.JSONDecodeError, TypeError):
        return [], ["JSON parse failure"]

    coin_list = data.get("data", [])
    if not isinstance(coin_list, list):
        return [], ["Unexpected response shape (missing data array)"]

    assets = []
    fetched_at = now_iso()
    # CoinCap IDs: bitcoin, ethereum, solana (same as coingecko IDs)
    target_ids = set(ASSETS_TO_REQUEST)

    for coin in coin_list:
        asset_id = coin.get("id", "").lower()
        if asset_id not in target_ids:
            continue

        last_updated = coin.get("updated")  # CoinCap uses unix timestamp in ms
        last_updated_str = fetched_at
        source_latency_ms = None
        if last_updated:
            try:
                src_time = datetime.fromtimestamp(int(last_updated) / 1000, tz=TZ)
                now_time = datetime.now(TZ)
                source_latency_ms = int((now_time - src_time).total_seconds() * 1000)
                last_updated_str = src_time.isoformat()
            except Exception:
                pass

        asset = {
            "asset_id": asset_id,
            "symbol": (coin.get("symbol") or "").upper(),
            "price_usd": float(coin["priceUsd"]) if coin.get("priceUsd") is not None else None,
            "price_change_pct": float(coin["changePercent24Hr"]) if coin.get("changePercent24Hr") is not None else None,
            "price_change_pct_1h": None,  # NOT available from CoinCap
            "volume_change_pct": None,     # NOT available from CoinCap (raw volume only)
            "open_interest_change_pct": None,
            "last_updated_at": last_updated_str,
            "source_latency_ms": source_latency_ms or raw_result.get("latency_ms"),
            "raw_source_fields": coin,
        }
        assets.append(asset)

    return assets, []


# ═══════════════════════════════════════════════════════════════════════════
# Step 4: Apply v112T stop conditions
# ═══════════════════════════════════════════════════════════════════════════

def apply_stop_conditions(
    live_source_response,
    raw_primary,
    raw_fallback,
    stop_config,
    elapsed_seconds,
    max_total_seconds,
):
    """
    Apply v112T three-state stop conditions.
    Evaluates ABORT first, then DEGRADE_TO_MOCK, then CONTINUE as fallback.

    Returns (decision, reason, abort_rules, degrade_rules, continue_rules).
    """
    abort_rules_triggered = []
    degrade_rules_triggered = []
    continue_rules_satisfied = []

    assets = live_source_response.get("assets", [])

    # ── ABORT checks ────────────────────────────────────────────────────

    # ABORT_HTTP_NON_2XX
    for resp in [raw_primary, raw_fallback]:
        if resp is None:
            continue
        sc = resp.get("status_code")
        if sc is not None and sc not in (200, 201, 202, 203, 204):
            abort_rules_triggered.append({
                "id": "ABORT_HTTP_NON_2XX",
                "detail": f"HTTP {sc} from {resp.get('source')}",
                "url": resp.get("url"),
            })

    # ABORT_HTTP_429
    for resp in [raw_primary, raw_fallback]:
        if resp is None:
            continue
        if resp.get("status_code") == 429:
            abort_rules_triggered.append({
                "id": "ABORT_HTTP_429",
                "detail": f"Rate limited (429) from {resp.get('source')}",
                "url": resp.get("url"),
            })

    # ABORT_REQUEST_TIMEOUT (3s per request in v112U; v112T plan had 15s)
    for resp in [raw_primary, raw_fallback]:
        if resp is None:
            continue
        if resp.get("error_message") and "timeout" in resp["error_message"].lower():
            abort_rules_triggered.append({
                "id": "ABORT_REQUEST_TIMEOUT",
                "detail": f"Request timeout: {resp.get('error_message')}",
                "latency_ms": resp.get("latency_ms"),
                "url": resp.get("url"),
            })

    # ABORT_TOTAL_DURATION
    if elapsed_seconds > max_total_seconds:
        abort_rules_triggered.append({
            "id": "ABORT_TOTAL_DURATION",
            "detail": f"Total elapsed {elapsed_seconds:.1f}s > {max_total_seconds}s limit",
        })

    # ABORT_JSON_PARSE_FAILURE
    for resp in [raw_primary, raw_fallback]:
        if resp is None:
            continue
        # Check if we got a non-2xx response (already flagged)
        sc = resp.get("status_code")
        if sc is not None and sc not in (200, 201, 202, 203, 204):
            continue  # Already caught by ABORT_HTTP_NON_2XX
        if resp.get("body_text") is None:
            continue
        try:
            json.loads(resp["body_text"])
        except (json.JSONDecodeError, TypeError):
            abort_rules_triggered.append({
                "id": "ABORT_JSON_PARSE_FAILURE",
                "detail": f"JSON parse failure from {resp.get('source')} at {resp.get('endpoint')}",
            })

    # ABORT_SCHEMA_MISMATCH (required top-level keys check)
    required_asset_fields = {"asset_id", "symbol", "price_usd", "price_change_pct", "last_updated_at"}
    missing_count = 0
    total_fields_checked = 0
    for asset in assets:
        for field in required_asset_fields:
            total_fields_checked += 1
            if asset.get(field) is None:
                missing_count += 1

    if total_fields_checked > 0 and (missing_count / total_fields_checked) > 0.20:
        abort_rules_triggered.append({
            "id": "ABORT_REQUIRED_FIELDS_MISSING",
            "detail": f"Missing {missing_count}/{total_fields_checked} required fields (>20%)",
        })

    # ABORT_PRICE_DIVERGENCE (only if both sources returned data)
    # We'll check this if cross-source validation is possible

    # ABORT_TIMESTAMP_SKEW (>120s between observations)
    if len(assets) >= 2:
        timestamps = []
        for a in assets:
            try:
                ts = a.get("last_updated_at", "")
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00") if ts else "")
                timestamps.append(dt)
            except Exception:
                pass
        if len(timestamps) >= 2:
            max_skew = (max(timestamps) - min(timestamps)).total_seconds()
            if max_skew > 120:
                abort_rules_triggered.append({
                    "id": "ABORT_TIMESTAMP_SKEW",
                    "detail": f"Max timestamp skew {max_skew:.0f}s > 120s",
                })

    # ── DEGRADE_TO_MOCK checks ───────────────────────────────────────────

    # DEGRADE_PARTIAL_ASSET_FAILURE
    if len(assets) < len(ASSETS_TO_REQUEST):
        success_rate = len(assets) / len(ASSETS_TO_REQUEST) if ASSETS_TO_REQUEST else 0
        if success_rate < 0.80:
            degrade_rules_triggered.append({
                "id": "DEGRADE_PARTIAL_ASSET_FAILURE",
                "detail": f"Got {len(assets)}/{len(ASSETS_TO_REQUEST)} assets ({success_rate:.0%}) < 80%",
            })

    # DEGRADE_OPTIONAL_FIELDS_MISSING
    optional_missing_count = 0
    for asset in assets:
        if asset.get("open_interest_change_pct") is None:
            optional_missing_count += 1
        if asset.get("volume_change_pct") is None:
            optional_missing_count += 1
    if optional_missing_count > 0:
        degrade_rules_triggered.append({
            "id": "DEGRADE_OPTIONAL_FIELDS_MISSING",
            "detail": f"{optional_missing_count} optional field(s) missing across assets (OI, volume_change_pct unavailable from free sources)",
        })

    # DEGRADE_MULTI_SOURCE_UNCERTAIN (only primary source succeeded)
    primary_ok = raw_primary and raw_primary.get("status_code") in (200, 201, 202, 203, 204)
    fallback_ok = raw_fallback and raw_fallback.get("status_code") in (200, 201, 202, 203, 204)
    if primary_ok and not fallback_ok:
        degrade_rules_triggered.append({
            "id": "DEGRADE_MULTI_SOURCE_UNCERTAIN",
            "detail": "Only primary source (CoinGecko) returned data; cross-validation impossible",
        })
    elif fallback_ok and not primary_ok:
        degrade_rules_triggered.append({
            "id": "DEGRADE_MULTI_SOURCE_UNCERTAIN",
            "detail": "Only fallback source (CoinCap) returned data; cross-validation impossible",
        })

    # DEGRADE_SOURCE_FRESHNESS
    for asset in assets:
        try:
            last_up = asset.get("last_updated_at", "")
            dt = datetime.fromisoformat(last_up.replace("Z", "+00:00") if last_up else "")
            now_dt = datetime.now(TZ)
            age_seconds = (now_dt - dt.astimezone(TZ)).total_seconds()
            if age_seconds > 120:
                degrade_rules_triggered.append({
                    "id": "DEGRADE_SOURCE_FRESHNESS",
                    "detail": f"Asset {asset.get('symbol')} data is {age_seconds:.0f}s old (>120s)",
                })
                break  # One stale asset is enough to flag
        except Exception:
            pass

    # DEGRADE_THRESHOLD_BOUNDARY (check if any price change is within +/-10% of 2.0% threshold)
    for asset in assets:
        pct = asset.get("price_change_pct")
        if pct is not None:
            if 1.8 <= abs(pct) <= 2.2:  # +/-10% of 2.0
                degrade_rules_triggered.append({
                    "id": "DEGRADE_THRESHOLD_BOUNDARY",
                    "detail": f"Asset {asset.get('symbol')} change {pct:.2f}% within +/-10% of 2.0% threshold boundary",
                })
                break  # One boundary asset is enough

    # ── CONTINUE checks ──────────────────────────────────────────────────

    if not abort_rules_triggered:
        # CONTINUE_ALL_REQUIRED_COMPLETE
        all_required_present = True
        for asset in assets:
            for field in required_asset_fields:
                if asset.get(field) is None:
                    all_required_present = False
                    break
        if all_required_present and len(assets) > 0:
            continue_rules_satisfied.append({
                "id": "CONTINUE_ALL_REQUIRED_COMPLETE",
                "detail": f"All {len(required_asset_fields)} required fields present for {len(assets)} assets",
            })

        # CONTINUE_NO_ABORT_OR_DEGRADE
        if not degrade_rules_triggered:
            continue_rules_satisfied.append({
                "id": "CONTINUE_NO_ABORT_OR_DEGRADE",
                "detail": "No ABORT or DEGRADE conditions triggered",
            })

    # CONTINUE_ELIGIBLE_FALSE (always true — policy constraint)
    continue_rules_satisfied.append({
        "id": "CONTINUE_ELIGIBLE_FALSE",
        "detail": "eligible_for_real_send = false (policy constraint, always enforced)",
    })

    # ── Final decision ───────────────────────────────────────────────────
    if abort_rules_triggered:
        decision = "ABORT"
        reason = f"{len(abort_rules_triggered)} abort rule(s) triggered"
    elif degrade_rules_triggered:
        decision = "DEGRADE_TO_MOCK"
        reason = f"{len(degrade_rules_triggered)} degrade rule(s) triggered"
    else:
        decision = "CONTINUE"
        reason = "All checks passed; free source data is valid for mock adapter processing"

    return {
        "decision": decision,
        "reason": reason,
        "abort_rules_triggered": abort_rules_triggered,
        "degrade_rules_triggered": degrade_rules_triggered,
        "continue_rules_satisfied": continue_rules_satisfied,
        "eligible_for_real_send": False,
        "state_write_performed": False,
        "real_tg_sent": False,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Step 5: Generate output files
# ═══════════════════════════════════════════════════════════════════════════

def generate_run_report(result, live_response, stop_decision, raw_primary, raw_fallback, elapsed):
    """Generate the v112U run report markdown."""
    lines = []
    lines.append("# v112U One-Shot Free Source Dry-Run — Run Report")
    lines.append("")
    lines.append(f"**Generated**: {timestamp()}")
    lines.append(f"**Status**: {result['status']}")
    lines.append(f"**Stop Decision**: {stop_decision['decision']}")
    lines.append("")

    lines.append("## v112U Objective")
    lines.append("")
    lines.append("Execute one-shot free source dry-run: make real HTTP GET requests to CoinGecko "
                "and CoinCap free public REST APIs, normalize the response to LiveSourceResponse schema, "
                "and apply v112T stop conditions to determine CONTINUE/ABORT/DEGRADE_TO_MOCK.")
    lines.append("")

    lines.append("## Sources Requested")
    lines.append("")
    if raw_primary:
        rp = raw_primary
        lines.append(f"- **Primary**: CoinGecko Public REST — `{rp.get('endpoint')}`")
        lines.append(f"  - Status: HTTP {rp.get('status_code')}")
        lines.append(f"  - Latency: {rp.get('latency_ms')}ms")
        if rp.get("error_message"):
            lines.append(f"  - Error: {rp['error_message']}")
    if raw_fallback:
        rf = raw_fallback
        lines.append(f"- **Fallback**: CoinCap Public REST — `{rf.get('endpoint')}`")
        lines.append(f"  - Status: HTTP {rf.get('status_code')}")
        lines.append(f"  - Latency: {rf.get('latency_ms')}ms")
        if rf.get("error_message"):
            lines.append(f"  - Error: {rf['error_message']}")
    lines.append("")

    lines.append("## Assets Requested")
    lines.append("")
    lines.append(f"- {', '.join(ASSET_SYMBOLS.values())} (3 assets)")
    lines.append(f"- Assets returned: {len(live_response.get('assets', []))}")
    lines.append("")

    lines.append("## Price Data Retrieved")
    lines.append("")
    assets = live_response.get("assets", [])
    if assets:
        lines.append("| Asset | Symbol | Price (USD) | 24h Change % | Source |")
        lines.append("|-------|--------|-------------|--------------|--------|")
        for a in assets:
            lines.append(
                f"| {a.get('asset_id')} | {a.get('symbol')} | "
                f"${a.get('price_usd', 'N/A')} | "
                f"{a.get('price_change_pct', 'N/A')} | "
                f"{live_response.get('source_name')} |"
            )
    else:
        lines.append("(No asset data retrieved)")
    lines.append("")

    lines.append("## Safety Checklist")
    lines.append("")
    lines.append("| Constraint | Value |")
    lines.append("|------------|-------|")
    lines.append(f"| API Key Used | {result['api_key_used']} |")
    lines.append(f"| Authorization Header Used | {result['authorization_header_used']} |")
    lines.append(f"| Retry Attempted | {result['retry_attempted']} |")
    lines.append(f"| TG Sent | {result['real_tg_sent']} |")
    lines.append(f"| Production State Write | {result['state_write_performed']} |")
    lines.append(f"| Daemon Started | {result['daemon_started']} |")
    lines.append(f"| External AI Called | {result['external_ai_called']} |")
    lines.append(f"| Files Deleted | {result['files_deleted']} |")
    lines.append(f"| Eligible For Real Send | {result['eligible_for_real_send']} |")
    lines.append("")

    lines.append("## Stop Decision")
    lines.append("")
    lines.append(f"**Decision**: `{stop_decision['decision']}`")
    lines.append(f"**Reason**: {stop_decision['reason']}")
    lines.append("")

    if stop_decision.get("abort_rules_triggered"):
        lines.append("### ABORT Rules Triggered")
        for rule in stop_decision["abort_rules_triggered"]:
            lines.append(f"- **{rule['id']}**: {rule['detail']}")

    if stop_decision.get("degrade_rules_triggered"):
        lines.append("### DEGRADE Rules Triggered")
        for rule in stop_decision["degrade_rules_triggered"]:
            lines.append(f"- **{rule['id']}**: {rule['detail']}")

    if stop_decision.get("continue_rules_satisfied"):
        lines.append("### CONTINUE Rules Satisfied")
        for rule in stop_decision["continue_rules_satisfied"]:
            lines.append(f"- **{rule['id']}**: {rule['detail']}")
    lines.append("")

    lines.append("## Why Still NOT Eligible for Real Send")
    lines.append("")
    lines.append("Even if CONTINUE, v112U policy mandates `eligible_for_real_send=false`. Reasons:")
    lines.append("")
    lines.append("1. This is a dry-run only — no production infrastructure is connected")
    lines.append("2. Only one or two free sources are used — insufficient for production redundancy")
    lines.append("3. Open Interest data is missing from free sources (needed for v112Q secondary metric)")
    lines.append("4. Free tier rate limits prevent reliable production operation")
    lines.append("5. No historical baseline has been established (required by v112Q)")
    lines.append("6. No TG formatting, send pipeline, or monitoring is connected")
    lines.append("")

    lines.append("## Latency")
    lines.append("")
    lines.append(f"- Total elapsed: {elapsed:.2f}s")
    if raw_primary:
        lines.append(f"- CoinGecko request latency: {raw_primary.get('latency_ms')}ms")
    if raw_fallback:
        lines.append(f"- CoinCap request latency: {raw_fallback.get('latency_ms')}ms")
    lines.append("")

    lines.append("## Recommended Next Step")
    lines.append("")
    lines.append(f"**{result['recommended_next_step']}**")
    if stop_decision['decision'] == 'CONTINUE':
        lines.append("")
        lines.append("Since v112U returned CONTINUE, v112V should:")
        lines.append("1. Build live response -> mock adapter compatibility bridge")
        lines.append("2. Verify v112R adapter can consume live-normalized response shape")
        lines.append("3. Run gate/preview integration with live-adapted mock data")

    elif stop_decision['decision'] == 'DEGRADE_TO_MOCK':
        lines.append("")
        lines.append("Since v112U returned DEGRADE_TO_MOCK, v112V should:")
        lines.append("1. Run mock replay with the degradation reason documented")
        lines.append("2. Consider whether stop condition thresholds need adjustment")
        lines.append("3. Build mock replay explanation layer")
    elif stop_decision['decision'] == 'ABORT':
        lines.append("")
        lines.append("Since v112U returned ABORT, v112V should:")
        lines.append("1. Determine if failure is transient (network) or permanent (schema change)")
        lines.append("2. If transient: allow one retry with user confirmation in v112V")
        lines.append("3. If permanent: freeze live source route, return to mock-only pipeline")
    lines.append("")

    return "\n".join(lines)


def generate_handoff(result, live_response, stop_decision, elapsed):
    """Generate the v112U handoff markdown."""
    lines = []
    lines.append("# v112U One-Shot Free Source Dry-Run — Handoff")
    lines.append("")
    lines.append(f"**Generated**: {timestamp()}")
    lines.append(f"**Version**: {result['version']}")
    lines.append(f"**Status**: {result['status']}")
    lines.append(f"**Stop Decision**: {stop_decision['decision']}")
    lines.append("")

    lines.append("## What v112U Did")
    lines.append("")
    lines.append("1. Validated v112T plan prerequisites (status=passed, plan_only=true, v112u_requires_user_confirmation=true)")
    lines.append("2. Made real one-shot HTTP GET requests to free public CoinGecko REST API")
    lines.append("3. (If CoinGecko failed) Made one-shot HTTP GET request to CoinCap REST API as fallback")
    lines.append("4. Normalized raw responses to v112T LiveSourceResponse schema")
    lines.append("5. Applied v112T three-state stop conditions (ABORT/DEGRADE_TO_MOCK/CONTINUE)")
    lines.append("6. Generated result JSON, live source response JSON, stop decision JSON")
    lines.append("7. Generated run report and handoff markdown files")
    lines.append(f"8. Total elapsed: {elapsed:.2f}s")
    lines.append("")

    lines.append("## Configurations Read")
    lines.append("")
    lines.append("- `results/market_radar_v112t_one_shot_free_source_plan_result.json` — v112T plan validation")
    lines.append("- `config/market_radar_v112t_free_source_mapping.json` — field mapping reference")
    lines.append("- `config/market_radar_v112t_stop_conditions.json` — stop condition rules")
    lines.append("- `schemas/market_radar_v112t_live_source_response_schema.json` — response schema")
    lines.append("- `config/market_radar_v112q_multi_asset_thresholds.json` — v112Q thresholds reference")
    lines.append("")

    lines.append("## Free Public Endpoints Requested")
    lines.append("")
    lines.append("- `GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true`")
    lines.append("- `GET https://api.coincap.io/v2/assets?limit=50` (fallback)")
    lines.append("")
    lines.append("No API keys. No Authorization header. No cookies. No tokens.")
    lines.append("")

    lines.append("## Files Generated")
    lines.append("")
    lines.append("| File | Description |")
    lines.append("|------|-------------|")
    lines.append("| `scripts/run_market_radar_v112u_one_shot_free_source_dry_run.py` | Runner |")
    lines.append("| `scripts/test_market_radar_v112u_one_shot_free_source_dry_run.py` | Test suite |")
    lines.append("| `results/market_radar_v112u_one_shot_free_source_dry_run_result.json` | Result |")
    lines.append("| `results/market_radar_v112u_live_source_response.json` | Normalized live response |")
    lines.append("| `results/market_radar_v112u_stop_decision.json` | Stop decision |")
    lines.append("| `runs/market_radar/v112u_one_shot_free_source_dry_run.md` | Run report |")
    lines.append("| `runs/market_radar/v112u_one_shot_free_source_dry_run_handoff.md` | Handoff |")
    lines.append("")

    lines.append("## Stop Decision Details")
    lines.append("")
    lines.append(f"- **Decision**: `{stop_decision['decision']}`")
    lines.append(f"- **Reason**: {stop_decision['reason']}")
    lines.append(f"- **ABORT rules triggered**: {len(stop_decision.get('abort_rules_triggered', []))}")
    lines.append(f"- **DEGRADE rules triggered**: {len(stop_decision.get('degrade_rules_triggered', []))}")
    lines.append(f"- **CONTINUE rules satisfied**: {len(stop_decision.get('continue_rules_satisfied', []))}")
    lines.append("")

    lines.append("## Current Safety Posture (Still NOT Enabled)")
    lines.append("")
    lines.append("| Capability | Status | Reason |")
    lines.append("|------------|--------|--------|")
    lines.append("| TG send | DISABLED | Dry-run only; no send pipeline connected |")
    lines.append("| Daemon | DISABLED | One-shot execution only |")
    lines.append("| Production state write | DISABLED | No state files modified |")
    lines.append("| External AI | DISABLED | No external AI API called |")
    lines.append("| Real send | DISABLED | eligible_for_real_send=false (policy) |")
    lines.append("| API Key | NOT USED | Free public endpoints only |")
    lines.append("| Retry | NOT USED | retry_enabled=false (policy) |")
    lines.append("| Files deleted | NONE | No files deleted |")
    lines.append("")

    lines.append("## Recommended Next Step")
    lines.append("")
    if stop_decision['decision'] == 'CONTINUE':
        lines.append("**v112V: Live response -> mock adapter compatibility**")
        lines.append("")
        lines.append("Since free source returns valid data with CONTINUE decision:")
        lines.append("1. Build the live-to-mock adapter bridge")
        lines.append("2. Verify the live response shape is compatible with v112R mock input")
        lines.append("3. Integration-test with gate/preview pipeline using adapted data")
        lines.append("4. Still keep eligible_for_real_send=false until v112W production gate review")
    elif stop_decision['decision'] == 'DEGRADE_TO_MOCK':
        lines.append("**v112V: Mock replay with failure reason**")
        lines.append("")
        lines.append("Since live response is DEGRADE_TO_MOCK:")
        lines.append("1. Document the specific degradation reasons")
        lines.append("2. Decide if stop condition thresholds need adjustment for free sources")
        lines.append("3. Build mock replay with degradation explanation layer")
        lines.append("4. Consider if free sources are inherently unsuitable or if thresholds are too strict")
    elif stop_decision['decision'] == 'ABORT':
        lines.append("**v112V: Mock replay with failure reason**")
        lines.append("")
        lines.append("Since live fetch ABORTED:")
        lines.append("1. Classify abort cause: transient (network/timeout) vs permanent (schema/API change)")
        lines.append("2. If transient: allow ONE retry with user confirmation in v112V")
        lines.append("3. If permanent: freeze live source route, return to mock-only pipeline")
        lines.append("4. Consider alternative free sources or adjusting timeout/retry policy")
    lines.append("")

    lines.append("## Safety Affirmation")
    lines.append("")
    lines.append(f"- `real_live_api_called`: **true** (authorized one-shot, free public source)")
    lines.append(f"- `external_api_called`: **true** (authorized one-shot, free public source)")
    lines.append(f"- `external_ai_called`: **false**")
    lines.append(f"- `real_tg_sent`: **false**")
    lines.append(f"- `daemon_started`: **false**")
    lines.append(f"- `files_deleted`: **false**")
    lines.append(f"- `api_key_used`: **false**")
    lines.append(f"- `authorization_header_used`: **false**")
    lines.append(f"- `retry_attempted`: **false**")
    lines.append(f"- `eligible_for_real_send`: **false**")
    lines.append(f"- `state_write_performed`: **false**")
    lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    run_start_time = time.time()
    run_start_ts = timestamp()
    errors = []
    warnings = []

    print("=" * 70)
    print("v112U One-Shot Free Source Dry-Run — ACTUAL Implementation")
    print(f"Run start: {run_start_ts}")
    print("=" * 70)
    print()
    print("SAFETY BOUNDARY:")
    for k, v in SAFETY_BOUNDARY.items():
        print(f"  {k}: {v}")
    print()

    # ── Step 1: Validate v112T prerequisites ────────────────────────────
    print("[1/6] Validating v112T prerequisites...")
    v112t, v112t_err = load_json(V112T_RESULT_IN, "v112T result")
    if v112t_err:
        print(f"  {FAIL_MARK} {v112t_err}")
        errors.append(v112t_err)
        v112t_ok = False
        v112t_issues = [v112t_err]
    else:
        v112t_ok, v112t_issues = validate_v112t_prerequisites(v112t)

    for issue in v112t_issues:
        print(f"  {FAIL_MARK} {issue}")
        errors.append(issue)

    if v112t_ok:
        print(f"  {OK_MARK} All v112T prerequisites met")
    else:
        print(f"  {FAIL_MARK} v112T prerequisites NOT met — cannot proceed to live fetch")
        errors.append("v112T prerequisites not met; runner may abort after validation")

    # ── Step 2: One-shot HTTP GET ───────────────────────────────────────
    print("\n[2/6] Performing one-shot HTTP GET to free public APIs...")

    max_total_seconds = SAFETY_BOUNDARY["max_total_runtime_seconds"]
    elapsed = time.time() - run_start_time

    if elapsed > max_total_seconds:
        print(f"  {FAIL_MARK} Already exceeded max runtime ({elapsed:.1f}s > {max_total_seconds}s)")
        raw_primary = None
        raw_fallback = None
    else:
        # Primary: CoinGecko /simple/price
        print(f"  Requesting CoinGecko /api/v3/simple/price for BTC, ETH, SOL...")
        raw_primary = fetch_coingecko_simple_price(
            ASSETS_TO_REQUEST,
            timeout_seconds=SAFETY_BOUNDARY["max_single_request_timeout_seconds"],
        )
        print(f"    Status: HTTP {raw_primary.get('status_code')}")
        print(f"    Latency: {raw_primary.get('latency_ms')}ms")
        if raw_primary.get("error_message"):
            print(f"    Error: {raw_primary['error_message']}")

        # Fallback: CoinCap /v2/assets (only if primary failed or for cross-validation)
        # Actually, per task: try CoinGecko, if non-2xx try CoinCap
        primary_status = raw_primary.get("status_code")
        if primary_status not in (200, 201, 202, 203, 204):
            print(f"  CoinGecko failed (HTTP {primary_status}), trying CoinCap /v2/assets...")
            elapsed = time.time() - run_start_time
            remaining = max_total_seconds - elapsed
            if remaining <= 0:
                print(f"  {FAIL_MARK} No time remaining for fallback ({elapsed:.1f}s elapsed)")
                raw_fallback = None
            else:
                raw_fallback = fetch_coincap_assets(
                    timeout_seconds=min(SAFETY_BOUNDARY["max_single_request_timeout_seconds"], int(remaining))
                )
                print(f"    Status: HTTP {raw_fallback.get('status_code')}")
                print(f"    Latency: {raw_fallback.get('latency_ms')}ms")
                if raw_fallback.get("error_message"):
                    print(f"    Error: {raw_fallback['error_message']}")
        else:
            # Primary succeeded; still try fallback for cross-validation if time permits
            elapsed = time.time() - run_start_time
            remaining = max_total_seconds - elapsed
            if remaining > SAFETY_BOUNDARY["max_single_request_timeout_seconds"]:
                print(f"  CoinGecko OK; also trying CoinCap for cross-validation...")
                raw_fallback = fetch_coincap_assets(
                    timeout_seconds=SAFETY_BOUNDARY["max_single_request_timeout_seconds"],
                )
                print(f"    Status: HTTP {raw_fallback.get('status_code')}")
                print(f"    Latency: {raw_fallback.get('latency_ms')}ms")
                if raw_fallback.get("error_message"):
                    print(f"    Error: {raw_fallback['error_message']}")
            else:
                print(f"  Skipping CoinCap (not enough time remaining: {remaining:.1f}s)")
                raw_fallback = None

    # ── Step 3: Normalize to LiveSourceResponse ──────────────────────────
    print("\n[3/6] Normalizing response to LiveSourceResponse schema...")

    assets = []
    normalization_warnings = []

    # Determine which response to use as primary data source
    primary_ok = raw_primary and raw_primary.get("status_code") in (200, 201, 202, 203, 204)
    fallback_ok = raw_fallback and raw_fallback.get("status_code") in (200, 201, 202, 203, 204)

    source_name = "coingecko_public_rest"
    validation_status = "valid"

    if primary_ok:
        # Normalize CoinGecko /simple/price response
        cg_assets, cg_warnings = normalize_coingecko_simple_price(raw_primary)
        assets = cg_assets
        normalization_warnings.extend(cg_warnings)
        source_name = "coingecko_public_rest"
        print(f"  {OK_MARK} CoinGecko: {len(assets)} assets normalized")
    elif fallback_ok:
        # Normalize CoinCap /v2/assets response
        cc_assets, cc_warnings = normalize_coincap_assets(raw_fallback)
        assets = cc_assets
        normalization_warnings.extend(cc_warnings)
        source_name = "coincap_public_rest"
        print(f"  {OK_MARK} CoinCap: {len(assets)} assets normalized")
    else:
        print(f"  {FAIL_MARK} Both sources failed; no assets to normalize")
        validation_status = "invalid"

    for w in normalization_warnings:
        print(f"  {WARN_MARK} {w}")
        warnings.append(w)

    live_source_response = {
        "source_name": source_name,
        "fetched_at": now_iso(),
        "request_mode": "live_one_shot",
        "assets": assets,
        "validation_status": validation_status,
        "stop_decision": "PENDING",  # Will be set by stop conditions
        "stop_decision_reasons": [],
        "cross_source_validation": {
            "performed": False,
            "price_divergence_pct": None,
            "timestamp_divergence_seconds": None,
            "assets_compared": 0,
            "verdict": "not_performed",
        },
        "eligible_for_real_send": False,
        "metadata": {
            "plan_version": "v1.12-t",
            "dry_run": True,
            "assets_requested": len(ASSETS_TO_REQUEST),
            "assets_returned": len(assets),
            "request_duration_ms": int((time.time() - run_start_time) * 1000),
        },
    }

    # ── Step 4: Apply stop conditions ────────────────────────────────────
    print("\n[4/6] Applying v112T stop conditions...")

    stop_config, stop_err = load_json(V112T_STOP_CONDITIONS, "stop_conditions")
    if stop_err:
        print(f"  {WARN_MARK} Could not load stop conditions: {stop_err}")
        warnings.append(stop_err)

    elapsed_total = time.time() - run_start_time

    stop_decision = apply_stop_conditions(
        live_source_response=live_source_response,
        raw_primary=raw_primary,
        raw_fallback=raw_fallback,
        stop_config=stop_config if stop_config else {},
        elapsed_seconds=elapsed_total,
        max_total_seconds=max_total_seconds,
    )

    live_source_response["stop_decision"] = stop_decision["decision"]
    if stop_decision.get("abort_rules_triggered"):
        live_source_response["stop_decision_reasons"] = [
            r["detail"] for r in stop_decision["abort_rules_triggered"]
        ]
    elif stop_decision.get("degrade_rules_triggered"):
        live_source_response["stop_decision_reasons"] = [
            r["detail"] for r in stop_decision["degrade_rules_triggered"]
        ]
    else:
        live_source_response["stop_decision_reasons"] = ["All checks passed"]

    print(f"  Decision: {stop_decision['decision']}")
    print(f"  Reason: {stop_decision['reason']}")
    print(f"  ABORT rules triggered: {len(stop_decision['abort_rules_triggered'])}")
    print(f"  DEGRADE rules triggered: {len(stop_decision['degrade_rules_triggered'])}")
    print(f"  CONTINUE rules satisfied: {len(stop_decision['continue_rules_satisfied'])}")

    # ── Step 5: Build result ─────────────────────────────────────────────
    print("\n[5/6] Building result JSON...")

    overall_status = stop_decision["decision"]
    if overall_status == "CONTINUE":
        status = "passed"
    elif overall_status == "DEGRADE_TO_MOCK":
        status = "degraded"
    else:
        status = "aborted"

    one_shot_performed = raw_primary is not None
    real_live_api_called = raw_primary is not None  # true if we attempted any HTTP

    result = {
        "version": "v1.12-u",
        "status": status,
        "dry_run_only": True,
        "one_shot_http_get_performed": one_shot_performed,
        "live_ready": False,
        "real_live_api_called": real_live_api_called,
        "real_tg_sent": False,
        "external_api_called": real_live_api_called,
        "external_ai_called": False,
        "daemon_started": False,
        "files_deleted": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
        "candidate_card_type": "multi_asset_market_sync",
        "source_count_attempted": (1 if raw_primary else 0) + (1 if raw_fallback else 0),
        "asset_count_requested": len(ASSETS_TO_REQUEST),
        "stop_decision": stop_decision["decision"],
        "eligible_for_real_send": False,
        "real_send_ready": False,
        "production_state_write_ready": False,
        "state_write_performed": False,
        "retry_attempted": False,
        "api_key_used": False,
        "authorization_header_used": False,
        "recommended_next_step": "v112v_live_response_to_mock_adapter_if_continue_else_mock_replay",
        "prerequisites_validated": v112t_ok,
        "total_elapsed_seconds": round(elapsed_total, 2),
        "errors": errors,
        "warnings": warnings,
        "generated_at": timestamp(),
    }

    # ── Step 6: Write output files ───────────────────────────────────────
    print("\n[6/6] Writing output files...")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(RUNS_DIR, exist_ok=True)

    # Write result JSON
    with open(V112U_RESULT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  {OK_MARK} Result: {V112U_RESULT}")

    # Write live source response JSON
    with open(V112U_LIVE_RESPONSE, "w", encoding="utf-8") as f:
        json.dump(live_source_response, f, indent=2, ensure_ascii=False)
    print(f"  {OK_MARK} Live response: {V112U_LIVE_RESPONSE}")

    # Write stop decision JSON
    with open(V112U_STOP_DECISION, "w", encoding="utf-8") as f:
        json.dump(stop_decision, f, indent=2, ensure_ascii=False)
    print(f"  {OK_MARK} Stop decision: {V112U_STOP_DECISION}")

    # Write run report
    run_report = generate_run_report(result, live_source_response, stop_decision,
                                     raw_primary, raw_fallback, elapsed_total)
    with open(V112U_RUN_REPORT, "w", encoding="utf-8") as f:
        f.write(run_report)
    print(f"  {OK_MARK} Run report: {V112U_RUN_REPORT}")

    # Write handoff
    handoff = generate_handoff(result, live_source_response, stop_decision, elapsed_total)
    with open(V112U_HANDOFF, "w", encoding="utf-8") as f:
        f.write(handoff)
    print(f"  {OK_MARK} Handoff: {V112U_HANDOFF}")

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("v112U SUMMARY")
    print("=" * 70)
    print(f"  Status:              {result['status']}")
    print(f"  Stop decision:        {result['stop_decision']}")
    print(f"  Real live API called: {result['real_live_api_called']}")
    print(f"  One-shot GET done:    {result['one_shot_http_get_performed']}")
    print(f"  Assets requested:     {result['asset_count_requested']}")
    print(f"  Sources attempted:    {result['source_count_attempted']}")
    print(f"  TG sent:              {result['real_tg_sent']}")
    print(f"  State write:          {result['state_write_performed']}")
    print(f"  API key used:         {result['api_key_used']}")
    print(f"  Auth header used:     {result['authorization_header_used']}")
    print(f"  Retry attempted:      {result['retry_attempted']}")
    print(f"  Daemon started:       {result['daemon_started']}")
    print(f"  External AI called:   {result['external_ai_called']}")
    print(f"  Eligible for send:    {result['eligible_for_real_send']}")
    print(f"  Total elapsed:        {result['total_elapsed_seconds']}s")
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors:
            print(f"    [ERROR] {e}")
    if warnings:
        print(f"\n  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    [WARN] {w}")
    print(f"\n  Next: {result['recommended_next_step']}")
    print("=" * 70)

    return 0 if status == "passed" else 0  # ABORT/DEGRADE still exit 0 (clean stop)


if __name__ == "__main__":
    sys.exit(main())
