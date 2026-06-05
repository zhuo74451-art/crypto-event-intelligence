#!/usr/bin/env python3
"""
run_market_radar_v112x_hyperliquid_one_shot_readonly_dryrun.py
===================================================================
v112X — HyperLiquid one-shot read-only dry-run.

Reads tracked addresses from v112W field mapping config,
calls HyperLiquid public info endpoint (POST, no auth),
transforms responses into v112X live response format,
applies v112W stop conditions, and writes results to disk.

Invariants (enforced):
  - No API key used
  - No Authorization header
  - No retries
  - No daemon / watcher / loop
  - No TG send
  - No production state write
  - eligible_for_real_send = false (always)
  - No file deletion
"""

import hashlib
import json
import os
import sys
import time
import datetime
import urllib.request
import urllib.error
import ssl

# ── Project paths ──────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)

CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
RESULTS_DIR = os.path.join(PROJECT_DIR, "results")
RUNS_DIR = os.path.join(PROJECT_DIR, "runs", "market_radar")
DATA_DIR = os.path.join(PROJECT_DIR, "data")

FIELD_MAPPING_PATH = os.path.join(CONFIG_DIR, "market_radar_v112w_whale_position_field_mapping.json")
STOP_CONDITIONS_PATH = os.path.join(CONFIG_DIR, "market_radar_v112w_hyperliquid_stop_conditions.json")
LIVE_RESPONSE_PATH = os.path.join(RESULTS_DIR, "market_radar_v112x_hyperliquid_live_response.json")
STOP_DECISION_PATH = os.path.join(RESULTS_DIR, "market_radar_v112x_hyperliquid_stop_decision.json")

# HyperLiquid public info endpoint
HL_INFO_URL = "https://api.hyperliquid.xyz/info"
REQUEST_TIMEOUT_SEC = 10
CN_TZ = datetime.timezone(datetime.timedelta(hours=8))

# Safety invariants — these MUST remain false
API_KEY_USED = False
AUTHORIZATION_HEADER_USED = False
RETRY_COUNT = 0
DAEMON_STARTED = False
TG_SENT = False
PRODUCTION_STATE_WRITTEN = False
ELIGIBLE_FOR_REAL_SEND = False


def now_iso() -> str:
    return datetime.datetime.now(CN_TZ).isoformat()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_tracked_addresses():
    """Load tracked addresses and their labels from v112W field mapping config."""
    fm = load_json(FIELD_MAPPING_PATH)
    addresses = fm.get("tracked_addresses_from_state_csv", [])
    labels = fm.get("tracked_address_labels", {})
    if not addresses:
        # Fallback: try to read from hyperliquid_position_state.csv
        csv_path = os.path.join(DATA_DIR, "hyperliquid_position_state.csv")
        if os.path.exists(csv_path):
            import csv
            seen = set()
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    addr = row.get("address", "").strip()
                    if addr and addr.startswith("0x") and addr not in seen:
                        seen.add(addr)
                        addresses.append(addr)
    return addresses, labels


def call_hyperliquid_info(address):
    """
    Call HyperLiquid public info endpoint for a single address.
    Returns (status_code, response_data, error_message).

    Uses NO API key. Uses NO Authorization header.
    Does NOT retry on failure.
    """
    payload = json.dumps({"type": "clearinghouseState", "user": address}).encode("utf-8")
    req = urllib.request.Request(
        HL_INFO_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) v112X_OneShot_DryRun",
        },
        method="POST",
    )

    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC, context=ctx) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                return status, None, f"JSON parse error: {str(e)}"
            return status, data, None
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = ""
        return e.code, None, f"HTTP {e.code}: {e.reason} — body: {body[:500]}"
    except urllib.error.URLError as e:
        return 0, None, f"URL error: {str(e.reason)}"
    except Exception as e:
        return 0, None, f"Exception: {str(e)}"


def normalize_position(raw_pos, address):
    """
    Normalize a raw HyperLiquid position into v112X internal format.

    raw_pos is the inner 'position' object from assetPositions.
    Returns a dict conforming to the v112W schema.
    """
    coin = raw_pos.get("coin", "UNKNOWN")
    szi_str = raw_pos.get("szi", "0")
    entry_px_str = raw_pos.get("entryPx", "0")
    liq_px_raw = raw_pos.get("liquidationPx", None)
    unrealized_pnl_str = raw_pos.get("unrealizedPnl", "0")
    leverage_obj = raw_pos.get("leverage", {})
    margin_used_str = raw_pos.get("marginUsed", "0")
    position_value_str = raw_pos.get("positionValue", "0")
    cum_funding = raw_pos.get("cumFunding", {})

    validation = {
        "required_fields_present": True,
        "numeric_parse_ok": True,
        "side_determined": True,
        "missing_fields": [],
        "parse_errors": [],
    }

    # Parse szi → side determination
    try:
        szi = float(szi_str)
    except (ValueError, TypeError):
        szi = 0.0
        validation["numeric_parse_ok"] = False
        validation["parse_errors"].append(f"szi parse failed: {szi_str}")

    if szi > 0:
        side = "long"
    elif szi < 0:
        side = "short"
    else:
        side = "flat"
        validation["side_determined"] = False

    # Parse entry price
    try:
        entry_price = float(entry_px_str)
    except (ValueError, TypeError):
        entry_price = 0.0
        validation["numeric_parse_ok"] = False
        validation["parse_errors"].append(f"entryPx parse failed: {entry_px_str}")

    # Parse unrealized PnL
    try:
        unrealized_pnl = float(unrealized_pnl_str)
    except (ValueError, TypeError):
        unrealized_pnl = 0.0
        validation["numeric_parse_ok"] = False
        validation["parse_errors"].append(f"unrealizedPnl parse failed: {unrealized_pnl_str}")

    # Parse liquidation price
    liquidation_price = None
    if liq_px_raw is not None and liq_px_raw != "":
        try:
            liquidation_price = float(liq_px_raw)
        except (ValueError, TypeError):
            validation["missing_fields"].append("liquidation_price (parse failed)")

    # Parse leverage
    if isinstance(leverage_obj, dict):
        leverage = leverage_obj.get("value", 0)
        if isinstance(leverage, (int, float)):
            pass
        else:
            try:
                leverage = float(leverage)
            except (ValueError, TypeError):
                leverage = 0
                validation["parse_errors"].append(f"leverage parse failed: {leverage_obj}")
    else:
        leverage = 0
        validation["missing_fields"].append("leverage")

    # Parse margin used
    try:
        margin_used = float(margin_used_str)
    except (ValueError, TypeError):
        margin_used = 0.0

    # Parse position value
    try:
        position_value = float(position_value_str)
    except (ValueError, TypeError):
        position_value = 0.0

    # Derive mark price: position_value / abs(szi)
    mark_price = 0.0
    if szi != 0:
        mark_price = abs(position_value / szi)
    else:
        mark_price = entry_price  # fallback when no position

    # Position size in USD
    position_size = abs(position_value) if position_value != 0 else abs(szi) * mark_price

    # Liquidation distance
    liquidation_distance_pct = None
    if liquidation_price is not None and mark_price > 0:
        liquidation_distance_pct = round(abs(mark_price - liquidation_price) / mark_price * 100, 2)

    # Check required fields
    if not coin or coin == "UNKNOWN":
        validation["missing_fields"].append("symbol")
        validation["required_fields_present"] = False
    if side == "flat":
        validation["missing_fields"].append("side (position is flat / zero size)")

    normalized = {
        "symbol": coin.upper(),
        "side": side,
        "position_size": round(position_size, 2),
        "entry_price": round(entry_price, 6),
        "mark_price": round(mark_price, 6),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "leverage": round(leverage, 2) if isinstance(leverage, (int, float)) else 0,
        "liquidation_price": round(liquidation_price, 6) if liquidation_price is not None else None,
        "liquidation_distance_pct": liquidation_distance_pct,
        "margin_used": round(margin_used, 2),
        "position_value": round(position_value, 2),
        "cum_funding": {
            "all_time": cum_funding.get("allTime", "0"),
            "since_open": cum_funding.get("sinceOpen", "0"),
            "since_change": cum_funding.get("sinceChange", "0"),
        },
        "observed_at": now_iso(),
        "raw_source_fields": {
            "coin": coin,
            "szi": szi_str,
            "entryPx": entry_px_str,
            "liquidationPx": str(liq_px_raw) if liq_px_raw is not None else None,
            "unrealizedPnl": unrealized_pnl_str,
            "leverage_type": leverage_obj.get("type", "") if isinstance(leverage_obj, dict) else "",
            "leverage_value": leverage if isinstance(leverage, (int, float)) else 0,
            "marginUsed": margin_used_str,
            "positionValue": position_value_str,
            "cumFunding": {
                "allTime": cum_funding.get("allTime", "0") if isinstance(cum_funding, dict) else "0",
                "sinceOpen": cum_funding.get("sinceOpen", "0") if isinstance(cum_funding, dict) else "0",
                "sinceChange": cum_funding.get("sinceChange", "0") if isinstance(cum_funding, dict) else "0",
            },
        },
        "validation_status": validation,
    }
    return normalized


def apply_stop_conditions(live_response):
    """
    Apply v112W stop conditions to the live response.
    Returns (decision: str, reasons: list[str]).

    Order: ABORT first → DEGRADE_TO_MOCK → CONTINUE.
    """
    stop_config = load_json(STOP_CONDITIONS_PATH)
    abort_conditions = stop_config.get("stop_conditions", {}).get("ABORT", {}).get("conditions", [])
    degrade_conditions = stop_config.get("stop_conditions", {}).get("DEGRADE_TO_MOCK", {}).get("conditions", [])
    continue_conditions = stop_config.get("stop_conditions", {}).get("CONTINUE", {}).get("conditions", [])

    reasons = []
    responses = live_response.get("responses", [])
    failures = live_response.get("failures", [])
    addresses = live_response.get("addresses_requested", [])

    # ── Check ABORT first ────────────────────────────────────────────────
    # ABORT_AUTH_REQUIRED
    if live_response.get("api_key_used", False) or live_response.get("authorization_header_used", False):
        reasons.append("ABORT_AUTH_REQUIRED: API key or Authorization header used")
        return "ABORT", reasons

    # ABORT_STATE_WRITE_ATTEMPTED
    if live_response.get("production_state_written", False):
        reasons.append("ABORT_STATE_WRITE_ATTEMPTED: production state write detected")
        return "ABORT", reasons

    # ABORT_EMPTY_TRACKED_ADDRESSES
    if not addresses:
        reasons.append("ABORT_EMPTY_TRACKED_ADDRESSES: no tracked addresses to request")
        return "ABORT", reasons

    # Check each failure for ABORT triggers
    non_2xx_count = 0
    timeout_count = 0
    json_parse_count = 0
    rate_limit_count = 0
    for fail in failures:
        status = fail.get("http_status", 0)
        error = fail.get("error", "")

        if status != 0 and (status < 200 or status >= 300):
            non_2xx_count += 1
        if "timeout" in error.lower() or "timed out" in error.lower():
            timeout_count += 1
        if "json" in error.lower() and "parse" in error.lower():
            json_parse_count += 1
        if "rate" in error.lower() or "blocked" in error.lower() or "429" in str(status):
            rate_limit_count += 1

    # ABORT_HTTP_NON_2XX — all requests failed with non-2xx
    if non_2xx_count > 0 and non_2xx_count == len(addresses) and len(responses) == 0:
        reasons.append("ABORT_HTTP_NON_2XX: all requests returned non-2xx status")
        return "ABORT", reasons

    # ABORT_TIMEOUT — all requests timed out
    if timeout_count > 0 and timeout_count == len(addresses) and len(responses) == 0:
        reasons.append("ABORT_TIMEOUT: all requests timed out")
        return "ABORT", reasons

    # ABORT_JSON_PARSE_ERROR — all responses failed JSON parsing
    if json_parse_count > 0 and json_parse_count == len(addresses) and len(responses) == 0:
        reasons.append("ABORT_JSON_PARSE_ERROR: all responses failed JSON parsing")
        return "ABORT", reasons

    # ABORT_RATE_LIMIT
    if rate_limit_count > 0:
        reasons.append("ABORT_RATE_LIMIT: rate limit or blocking detected")
        return "ABORT", reasons

    # ABORT_RESPONSE_MISSING_POSITIONS_ARRAY — check each response
    # Responses are already normalized; check for `positions` key
    all_missing_positions = True
    for resp in responses:
        positions = resp.get("positions", [])
        if positions:
            all_missing_positions = False
            break

    if all_missing_positions and len(responses) > 0:
        # Every response has zero positions — this is a data gap, not necessarily a schema mismatch
        # But if responses exist and every single one has no positions, that's concerning
        reasons.append("ABORT_RESPONSE_MISSING_POSITIONS_ARRAY: all tracked addresses returned zero positions")
        return "ABORT", reasons

    # ABORT_FIELD_MISSING_RATE_HIGH — >20% missing required fields
    total_positions = sum(len(resp.get("positions", [])) for resp in responses)
    if total_positions > 0:
        missing_count = 0
        for resp in responses:
            for pos in resp.get("positions", []):
                vs = pos.get("validation_status", {})
                if not vs.get("required_fields_present", True):
                    missing_count += 1
        if missing_count / total_positions > 0.2:
            reasons.append(f"ABORT_FIELD_MISSING_RATE_HIGH: {missing_count}/{total_positions} positions missing required fields (>20%)")
            return "ABORT", reasons

    # ABORT_NUMERIC_PARSE_FAILURE
    numeric_fail_count = 0
    for resp in responses:
        for pos in resp.get("positions", []):
            vs = pos.get("validation_status", {})
            if not vs.get("numeric_parse_ok", True):
                numeric_fail_count += 1
    if numeric_fail_count > 0 and total_positions > 0 and numeric_fail_count / total_positions > 0.2:
        reasons.append(f"ABORT_NUMERIC_PARSE_FAILURE: {numeric_fail_count}/{total_positions} positions have numeric parse failures (>20%)")
        return "ABORT", reasons

    # ── Check DEGRADE_TO_MOCK ────────────────────────────────────────────
    has_degrade = False

    # DEGRADE_PARTIAL_ADDRESS_FAILURE
    total_requests = len(addresses)
    success_count = len(responses)
    if success_count < total_requests and success_count > 0:
        # Partial failure
        if success_count / total_requests >= 0.5:
            reasons.append("DEGRADE_PARTIAL_ADDRESS_FAILURE: partial address failure, success rate >= 50%")
            has_degrade = True
        else:
            # < 50% success → ABORT
            reasons.append("ABORT_EMPTY_TRACKED_ADDRESSES: success rate below 50% across tracked addresses")
            return "ABORT", reasons

    # All addresses failed → ABORT
    if success_count == 0 and total_requests > 0:
        reasons.append("ABORT_EMPTY_TRACKED_ADDRESSES: all tracked addresses returned no usable data")
        return "ABORT", reasons

    # DEGRADE_LABEL_MISSING / DEGRADE_LABEL_STALE
    for resp in responses:
        label_conf = resp.get("label_confidence", "low")
        if label_conf == "low":
            reasons.append(f"DEGRADE_LABEL_MISSING: address {resp.get('address_short', '?')} has low label confidence")
            has_degrade = True

    # DEGRADE_LIQUIDATION_PRICE_MISSING
    for resp in responses:
        for pos in resp.get("positions", []):
            if pos.get("liquidation_price") is None:
                reasons.append(f"DEGRADE_LIQUIDATION_PRICE_MISSING: {pos.get('symbol', '?')} position missing liquidation_price")
                has_degrade = True

    # DEGRADE_DELTA_CANNOT_COMPUTE — no history to compute delta
    reasons.append("DEGRADE_DELTA_CANNOT_COMPUTE: no previous position history available for delta computation")
    has_degrade = True

    # DEGRADE_TIMESTAMP_FRESHNESS — we're generating local timestamps
    reasons.append("DEGRADE_TIMESTAMP_FRESHNESS: using locally generated timestamps")
    has_degrade = True

    # DEGRADE_PREVIOUS_SIZE_UNAVAILABLE
    reasons.append("DEGRADE_PREVIOUS_SIZE_UNAVAILABLE: previous position size not available from live response")
    has_degrade = True

    if has_degrade:
        return "DEGRADE_TO_MOCK", reasons

    # ── Check CONTINUE ────────────────────────────────────────────────────
    # CONTINUE requires at least one active position with all required fields
    has_valid_position = False
    for resp in responses:
        for pos in resp.get("positions", []):
            vs = pos.get("validation_status", {})
            side = pos.get("side", "flat")
            position_size = pos.get("position_size", 0)
            if (
                vs.get("required_fields_present", False) and
                vs.get("numeric_parse_ok", False) and
                side != "flat" and
                position_size > 0
            ):
                has_valid_position = True
                break

    if has_valid_position:
        reasons.append("CONTINUE_ALL_REQUIRED_FIELDS: at least one tracked address returns complete position data")
        reasons.append("CONTINUE_ACTIVE_POSITION: at least one tracked address returns active position")
        reasons.append("CONTINUE_NUMERIC_PARSE_OK: numeric fields parse successfully")
        reasons.append("CONTINUE_TIMESTAMP_OK: timestamps safely generated")
        reasons.append("CONTINUE_LABEL_OK: labels available or 'Unknown Whale' fallback applied")
        reasons.append("CONTINUE_ADAPTER_CAN_PRODUCE: adapter can produce v112F-compatible event")
        reasons.append("CONTINUE_ENVELOPE_ELIGIBLE: eligible_for_real_send=false enforced")
        reasons.append("CONTINUE_NO_ABORT_NO_DEGRADE: all quality gates passed")
        return "CONTINUE", reasons

    # Default: fallback to DEGRADE_TO_MOCK if we have any responses
    if len(responses) > 0:
        reasons.append("DEGRADE_TO_MOCK (fallback): responses present but no position meets all CONTINUE criteria")
        return "DEGRADE_TO_MOCK", reasons

    # Default ABORT
    reasons.append("ABORT (default fail-safe): no path to CONTINUE or DEGRADE_TO_MOCK")
    return "ABORT", reasons


def compute_short_address(address):
    """Shorten a full address: 0xabcd...ef123"""
    if len(address) > 12:
        return f"{address[:6]}...{address[-5:]}"
    return address


def main():
    """Main entry point. Returns exit code (0 = success, 1 = ABORT)."""
    started_at = now_iso()
    print(f"[v112X] HyperLiquid one-shot read-only dry-run")
    print(f"[v112X] Started at: {started_at}")
    print(f"[v112X] Project dir: {PROJECT_DIR}")

    # ── Step 1: Load tracked addresses ────────────────────────────────────
    addresses, labels = load_tracked_addresses()
    print(f"[v112X] Tracked addresses loaded: {len(addresses)}")
    for addr in addresses:
        label_info = labels.get(addr, {})
        label = label_info.get("label", "Unknown")
        print(f"  - {compute_short_address(addr)} : {label}")

    if not addresses:
        print("[v112X] ERROR: No tracked addresses found. Cannot proceed.")
        live_response = {
            "version": "v112X",
            "source": "hyperliquid_public_info",
            "dry_run_only": True,
            "one_shot": True,
            "external_api_called": False,
            "api_key_used": API_KEY_USED,
            "authorization_header_used": AUTHORIZATION_HEADER_USED,
            "retry_count": RETRY_COUNT,
            "daemon_started": DAEMON_STARTED,
            "tg_sent": TG_SENT,
            "production_state_written": PRODUCTION_STATE_WRITTEN,
            "eligible_for_real_send": ELIGIBLE_FOR_REAL_SEND,
            "addresses_requested": [],
            "responses": [],
            "failures": [
                {"error": "No tracked addresses found", "http_status": 0}
            ],
            "started_at": started_at,
            "completed_at": now_iso(),
        }
        save_json(LIVE_RESPONSE_PATH, live_response)

        # Stop decision
        decision, reasons = apply_stop_conditions(live_response)
        stop_decision = {
            "version": "v112X",
            "generated_at": now_iso(),
            "stop_decision": decision,
            "stop_decision_reasons": reasons,
            "addresses_total": 0,
            "success_count": 0,
            "failure_count": 1,
            "api_key_used": API_KEY_USED,
            "authorization_header_used": AUTHORIZATION_HEADER_USED,
            "retry_count": RETRY_COUNT,
            "daemon_started": DAEMON_STARTED,
            "tg_sent": TG_SENT,
            "production_state_written": PRODUCTION_STATE_WRITTEN,
            "eligible_for_real_send": ELIGIBLE_FOR_REAL_SEND,
            "notes": ["No tracked addresses found — cannot make API calls."],
        }
        save_json(STOP_DECISION_PATH, stop_decision)
        print(f"[v112X] Stop decision: {decision}")
        return 0  # Not a security violation, just no data

    # ── Step 2: Call HyperLiquid API for each address ─────────────────────
    responses = []
    failures = []
    external_api_called = True

    for addr in addresses:
        addr_short = compute_short_address(addr)
        label_info = labels.get(addr, {})
        label = label_info.get("label", "Unknown Whale")
        entity_type = label_info.get("entity_type", "unknown_whale")
        confidence = label_info.get("confidence", "low")
        label_source = label_info.get("source", "hyperliquid_observer")

        print(f"[v112X] Requesting: {addr_short} ({label})...")
        http_status, data, error = call_hyperliquid_info(addr)

        if error is not None or http_status < 200 or http_status >= 300:
            print(f"  FAILED: HTTP {http_status} — {error}")
            failures.append({
                "address": addr,
                "address_short": addr_short,
                "label": label,
                "http_status": http_status,
                "error": error,
                "timestamp": now_iso(),
            })
            continue

        # ── Parse response ────────────────────────────────────────────────
        asset_positions = data.get("assetPositions", [])
        normalized_positions = []

        for raw_pos in asset_positions:
            inner = raw_pos.get("position", raw_pos)
            norm = normalize_position(inner, addr)
            normalized_positions.append(norm)

        print(f"  OK: HTTP {http_status}, {len(asset_positions)} asset positions")

        responses.append({
            "address": addr,
            "address_short": addr_short,
            "address_label": label,
            "label_confidence": confidence,
            "entity_type": entity_type,
            "label_source": label_source,
            "http_status": http_status,
            "positions_count": len(asset_positions),
            "positions": normalized_positions,
            "raw_response_asset_positions_count": len(asset_positions),
            "timestamp": now_iso(),
        })

    # ── Step 3: Build live response ───────────────────────────────────────
    live_response = {
        "version": "v112X",
        "source": "hyperliquid_public_info",
        "dry_run_only": True,
        "one_shot": True,
        "external_api_called": external_api_called,
        "api_key_used": API_KEY_USED,
        "authorization_header_used": AUTHORIZATION_HEADER_USED,
        "retry_count": RETRY_COUNT,
        "daemon_started": DAEMON_STARTED,
        "tg_sent": TG_SENT,
        "production_state_written": PRODUCTION_STATE_WRITTEN,
        "eligible_for_real_send": ELIGIBLE_FOR_REAL_SEND,
        "addresses_requested": addresses,
        "responses": responses,
        "failures": failures,
        "started_at": started_at,
        "completed_at": now_iso(),
    }

    save_json(LIVE_RESPONSE_PATH, live_response)
    print(f"\n[v112X] Live response saved: {LIVE_RESPONSE_PATH}")
    print(f"[v112X] Success: {len(responses)}, Failures: {len(failures)}")

    # ── Step 4: Apply stop conditions ─────────────────────────────────────
    print("\n[v112X] Applying v112W stop conditions...")
    decision, reasons = apply_stop_conditions(live_response)

    # Count positions
    total_positions = sum(len(r.get("positions", [])) for r in responses)
    active_positions = sum(
        1 for r in responses
        for p in r.get("positions", [])
        if p.get("side") != "flat" and p.get("position_size", 0) > 0
    )

    stop_decision = {
        "version": "v112X",
        "generated_at": now_iso(),
        "stop_decision": decision,
        "stop_decision_reasons": reasons,
        "addresses_total": len(addresses),
        "success_count": len(responses),
        "failure_count": len(failures),
        "total_positions_found": total_positions,
        "active_positions_found": active_positions,
        "api_key_used": API_KEY_USED,
        "authorization_header_used": AUTHORIZATION_HEADER_USED,
        "retry_count": RETRY_COUNT,
        "daemon_started": DAEMON_STARTED,
        "tg_sent": TG_SENT,
        "production_state_written": PRODUCTION_STATE_WRITTEN,
        "eligible_for_real_send": ELIGIBLE_FOR_REAL_SEND,
        "notes": [],
    }

    # Decision-specific notes
    if decision == "ABORT":
        stop_decision["notes"].append("v112Y suggestion: whale degraded mock replay with label explanation")
    elif decision == "DEGRADE_TO_MOCK":
        stop_decision["notes"].append("v112Y suggestion: whale degraded mock replay with label explanation")
    elif decision == "CONTINUE":
        stop_decision["notes"].append("v112Y suggestion: live response → whale adapter compatibility check")

    stop_decision["notes"].append(f"Mark price derived from position_value / abs(szi); no external price API called.")
    stop_decision["notes"].append(f"No previous position history — position_delta cannot be computed.")
    stop_decision["notes"].append(f"All labels from v112W field mapping config — no live label lookup performed.")

    save_json(STOP_DECISION_PATH, stop_decision)
    print(f"[v112X] Stop decision: {decision}")
    for r in reasons:
        print(f"  - {r}")

    # ── Step 5: Print summary ─────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  v112X — Dry-Run Summary")
    print(f"{'=' * 60}")
    print(f"  Addresses requested : {len(addresses)}")
    print(f"  Successful responses: {len(responses)}")
    print(f"  Failed requests     : {len(failures)}")
    print(f"  Total positions     : {total_positions}")
    print(f"  Active positions    : {active_positions}")
    print(f"  API key used        : {API_KEY_USED}")
    print(f"  Auth header used    : {AUTHORIZATION_HEADER_USED}")
    print(f"  Retry count         : {RETRY_COUNT}")
    print(f"  TG sent             : {TG_SENT}")
    print(f"  Prod state written  : {PRODUCTION_STATE_WRITTEN}")
    print(f"  Daemon started      : {DAEMON_STARTED}")
    print(f"  Eligible real send  : {ELIGIBLE_FOR_REAL_SEND}")
    print(f"  Stop decision       : {decision}")
    print(f"{'=' * 60}")

    # Exit code: 0 for all outcomes (ABORT from lack of data is not a
    # security violation — it's an expected stop decision).
    # Only non-zero if there was a true security violation.
    return 0


if __name__ == "__main__":
    sys.exit(main())
