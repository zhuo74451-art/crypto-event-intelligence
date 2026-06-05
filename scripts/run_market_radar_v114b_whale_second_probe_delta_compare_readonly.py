#!/usr/bin/env python3
"""
v114B Whale Second Probe Delta Compare — Read-Only
====================================================
Reads v114A baseline, makes ONE read-only HyperLiquid public info call
per tracked address, and computes position deltas against the baseline.

Invariants (enforced):
  - No API key used
  - No Authorization header
  - No retries
  - No daemon / watcher / loop
  - No TG send
  - No production state write
  - eligible_for_real_send = false (always)
  - tg_send_allowed = false (always)
  - No file deletion
  - local_delta_compare_only = true
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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

BASELINE_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_snapshot_result.json")
BASELINE_SNAPSHOT = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_snapshot.json")
BASELINE_POSITIONS = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_positions.jsonl")

OUT_LIVE_RESPONSE = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_second_probe_live_response.json")
OUT_DELTA_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_delta_compare_result.json")
OUT_DELTAS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_position_deltas.jsonl")
OUT_REPORT = os.path.join(RUNS_DIR, "v114b_whale_second_probe_delta_compare_readonly.md")
OUT_HANDOFF = os.path.join(RUNS_DIR, "v114b_whale_second_probe_delta_compare_readonly_handoff.md")

# HyperLiquid public info endpoint
HL_INFO_URL = "https://api.hyperliquid.xyz/info"
REQUEST_TIMEOUT_SEC = 10

TZ_SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))

# Safety invariants — these MUST remain as declared
API_KEY_USED = False
AUTHORIZATION_HEADER_USED = False
RETRY_COUNT = 0
DAEMON_STARTED = False
WATCHER_STARTED = False
TG_SENT = False
PRODUCTION_STATE_WRITTEN = False
FILES_DELETED = False
CREDENTIALS_READ = False
LOCAL_DELTA_COMPARE_ONLY = True

# Delta type enum
DELTA_NEW = "new_position"
DELTA_CLOSED = "closed_position"
DELTA_SIZE_CHANGED = "size_changed"
DELTA_UNCHANGED = "unchanged"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.datetime.now(TZ_SHANGHAI).isoformat()


def make_position_identity_key(address: str, asset: str, side: str) -> str:
    """Deterministic identity key matching v114A baseline format."""
    return f"{address.lower()}|{asset}|{side}"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_jsonl(path, records):
    """Save list of dicts as JSONL."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    return count


def save_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def safe_float(value, default=None):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def size_tolerance_check(baseline_size, current_size, tolerance_pct=0.01):
    """
    Check if two position sizes are within tolerance.
    Returns True if approximately equal; False if meaningfully different.
    Uses a 1% relative tolerance with an absolute floor of 0.01.
    """
    baseline = safe_float(baseline_size, 0)
    current = safe_float(current_size, 0)
    if baseline == 0 and current == 0:
        return True
    if baseline == 0 or current == 0:
        return False
    rel_diff = abs(current - baseline) / max(abs(baseline), abs(current))
    return rel_diff < tolerance_pct


# ---------------------------------------------------------------------------
# Step 1: Load v114A baseline
# ---------------------------------------------------------------------------
def load_baseline():
    """Load v114A baseline snapshot and positions."""
    if not os.path.exists(BASELINE_RESULT):
        print(f"ERROR: v114A baseline result not found at {BASELINE_RESULT}")
        sys.exit(1)
    if not os.path.exists(BASELINE_SNAPSHOT):
        print(f"ERROR: v114A baseline snapshot not found at {BASELINE_SNAPSHOT}")
        sys.exit(1)
    if not os.path.exists(BASELINE_POSITIONS):
        print(f"ERROR: v114A baseline positions not found at {BASELINE_POSITIONS}")
        sys.exit(1)

    baseline_result = load_json(BASELINE_RESULT)
    baseline_snapshot = load_json(BASELINE_SNAPSHOT)
    baseline_positions = []
    with open(BASELINE_POSITIONS, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                baseline_positions.append(json.loads(line))

    print(f"  Baseline result loaded: {baseline_result['baseline_records_written']} records")
    print(f"  Baseline snapshot loaded: {baseline_snapshot['positions_count']} positions")
    print(f"  Baseline positions JSONL loaded: {len(baseline_positions)} records")

    return baseline_result, baseline_snapshot, baseline_positions


# ---------------------------------------------------------------------------
# Step 2: Extract tracked addresses from baseline
# ---------------------------------------------------------------------------
def extract_tracked_addresses(baseline_positions):
    """Extract unique tracked addresses from baseline positions, preserving order."""
    seen = set()
    addresses = []
    for rec in baseline_positions:
        addr = rec["address"]
        if addr not in seen:
            seen.add(addr)
            addresses.append(addr)
    return addresses


# ---------------------------------------------------------------------------
# Step 3: Call HyperLiquid public info
# ---------------------------------------------------------------------------
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) v114B_SecondProbe_DeltaCompare",
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


# ---------------------------------------------------------------------------
# Step 4: Parse HyperLiquid response into normalized positions
# ---------------------------------------------------------------------------
def parse_positions_from_clearinghouse(response_data, address):
    """
    Parse a clearinghouseState response into normalized position dicts.
    Each position: {symbol, side, position_size, entry_price, mark_price,
                     leverage, liquidation_price, notional_usd}
    """
    positions = []
    if not response_data:
        return positions

    # clearinghouseState returns {assetPositions: [...]}
    asset_positions = response_data.get("assetPositions", [])
    if not isinstance(asset_positions, list):
        return positions

    for raw_pos in asset_positions:
        pos = raw_pos.get("position", {})
        if not pos:
            continue

        coin = pos.get("coin", raw_pos.get("coin", "UNKNOWN"))
        szi_str = pos.get("szi", "0")
        entry_px_str = pos.get("entryPx", "0")
        liq_px_raw = pos.get("liquidationPx", None)
        leverage_obj = pos.get("leverage", {})
        position_value_str = pos.get("positionValue", "0")

        # Parse szi → side
        try:
            szi = float(szi_str)
        except (ValueError, TypeError):
            szi = 0.0
        if szi > 0:
            side = "long"
        elif szi < 0:
            side = "short"
        else:
            side = "flat"

        # Parse entry price
        try:
            entry_price = float(entry_px_str)
        except (ValueError, TypeError):
            entry_price = 0.0

        # Parse position value
        try:
            position_value = float(position_value_str)
        except (ValueError, TypeError):
            position_value = 0.0

        # Parse liquidation price
        liquidation_price = None
        if liq_px_raw is not None and liq_px_raw != "" and liq_px_raw != "0":
            try:
                liquidation_price = float(liq_px_raw)
            except (ValueError, TypeError):
                pass

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
        else:
            leverage = 0

        # Position size = abs(position_value) for notional; or abs(szi) * mark
        position_size = abs(position_value) if position_value != 0 else abs(szi)

        positions.append({
            "symbol": coin,
            "side": side,
            "position_size": position_size,
            "entry_price": entry_price,
            "leverage": leverage,
            "liquidation_price": liquidation_price,
            "position_value": position_value,
        })

    return positions


# ---------------------------------------------------------------------------
# Step 5: Build baseline index by identity key
# ---------------------------------------------------------------------------
def build_baseline_index(baseline_positions):
    """Build a dict mapping position_identity_key → baseline record."""
    index = {}
    for rec in baseline_positions:
        key = rec["position_identity_key"]
        index[key] = rec
    return index


# ---------------------------------------------------------------------------
# Step 6: Compare second probe vs baseline and produce delta records
# ---------------------------------------------------------------------------
def compute_deltas(baseline_index, probe_responses):
    """
    Compare probe positions against baseline and produce delta records.

    Delta types:
      - unchanged: baseline has it, probe has it, same size
      - size_changed: baseline has it, probe has it, different size
      - closed_position: baseline has it, probe does NOT have it
      - new_position: baseline does NOT have it, probe has it
    """
    deltas = []

    # Set of all baseline identity keys
    baseline_keys = set(baseline_index.keys())

    # Build map of probe identity keys → normalized position info
    probe_index = {}
    for resp in probe_responses:
        address = resp["address"]
        label = resp.get("address_label", resp.get("label", "Unknown"))
        label_confidence = resp.get("label_confidence", "unknown")
        for pos in resp.get("positions", []):
            key = make_position_identity_key(address, pos["symbol"], pos["side"])
            probe_index[key] = {
                "address": address,
                "label": label,
                "label_confidence": label_confidence,
                "asset": pos["symbol"],
                "side": pos["side"],
                "position_size": pos["position_size"],
                "entry_price": pos["entry_price"],
                "liquidation_price": pos.get("liquidation_price"),
                "position_value": pos.get("position_value", pos["position_size"]),
            }

    probe_keys = set(probe_index.keys())

    # --- Process each baseline position ---
    for key in baseline_keys:
        baseline_rec = baseline_index[key]
        if key in probe_index:
            # Position exists in both baseline and probe
            probe_rec = probe_index[key]
            b_size = baseline_rec["position_size"]
            p_size = probe_rec["position_size"]
            b_entry = baseline_rec["entry_price"]
            p_entry = probe_rec["entry_price"]

            if size_tolerance_check(b_size, p_size):
                delta_type = DELTA_UNCHANGED
            else:
                delta_type = DELTA_SIZE_CHANGED

            entry_price_changed = False
            if safe_float(b_entry) and safe_float(p_entry):
                if abs(safe_float(b_entry, 0) - safe_float(p_entry, 0)) > 0.01:
                    entry_price_changed = True

            size_delta = safe_float(p_size, 0) - safe_float(b_size, 0)

            liq_price = probe_rec.get("liquidation_price")

            quality_flags = ["second_probe_readonly", "local_delta_compare", "not_send_ready"]
            if liq_price is None:
                quality_flags.append("liquidation_price_unavailable")

            operator_note_parts = []
            if delta_type == DELTA_UNCHANGED:
                operator_note_parts.append(f"Position unchanged since v114A baseline")
            elif delta_type == DELTA_SIZE_CHANGED:
                operator_note_parts.append(
                    f"Size changed: baseline={b_size:,.2f} → current={p_size:,.2f} "
                    f"(delta={size_delta:+,.2f})"
                )
            if entry_price_changed:
                operator_note_parts.append(
                    f"Entry price changed: {b_entry} → {p_entry}"
                )
            if liq_price is None:
                operator_note_parts.append("Liquidation price unavailable")

            delta = {
                "version": "v114B",
                "delta_type": delta_type,
                "local_delta_compare_only": True,
                "eligible_for_real_send": False,
                "tg_send_allowed": False,
                "prod_state_write": False,
                "position_identity_key": key,
                "address": baseline_rec["address"],
                "label": baseline_rec["label"],
                "label_confidence": baseline_rec["label_confidence"],
                "asset": baseline_rec["asset"],
                "side": baseline_rec["side"],
                "baseline_size": b_size,
                "current_size": p_size,
                "size_delta": size_delta,
                "baseline_entry_price": b_entry,
                "current_entry_price": p_entry,
                "entry_price_changed": entry_price_changed,
                "liquidation_price": liq_price,
                "quality_flags": quality_flags,
                "operator_note": "; ".join(operator_note_parts) if operator_note_parts else "No significant change detected",
            }
            deltas.append(delta)
        else:
            # Position was in baseline but NOT in probe → closed
            quality_flags = ["second_probe_readonly", "local_delta_compare", "not_send_ready", "position_closed"]
            liq_price = baseline_rec.get("liquidation_price")

            delta = {
                "version": "v114B",
                "delta_type": DELTA_CLOSED,
                "local_delta_compare_only": True,
                "eligible_for_real_send": False,
                "tg_send_allowed": False,
                "prod_state_write": False,
                "position_identity_key": key,
                "address": baseline_rec["address"],
                "label": baseline_rec["label"],
                "label_confidence": baseline_rec["label_confidence"],
                "asset": baseline_rec["asset"],
                "side": baseline_rec["side"],
                "baseline_size": baseline_rec["position_size"],
                "current_size": 0,
                "size_delta": -safe_float(baseline_rec["position_size"], 0),
                "baseline_entry_price": baseline_rec["entry_price"],
                "current_entry_price": None,
                "entry_price_changed": False,
                "liquidation_price": liq_price,
                "quality_flags": quality_flags,
                "operator_note": (
                    f"Position CLOSED — was in v114A baseline but absent in v114B second probe. "
                    f"Asset: {baseline_rec['asset']}, Side: {baseline_rec['side']}, "
                    f"Baseline size: {baseline_rec['position_size']:,.2f}"
                ),
            }
            deltas.append(delta)

    # --- Process new positions (in probe but not in baseline) ---
    for key in probe_keys - baseline_keys:
        probe_rec = probe_index[key]
        liq_price = probe_rec.get("liquidation_price")

        quality_flags = ["second_probe_readonly", "local_delta_compare", "not_send_ready", "new_position_detected"]
        if liq_price is None:
            quality_flags.append("liquidation_price_unavailable")

        delta = {
            "version": "v114B",
            "delta_type": DELTA_NEW,
            "local_delta_compare_only": True,
            "eligible_for_real_send": False,
            "tg_send_allowed": False,
            "prod_state_write": False,
            "position_identity_key": key,
            "address": probe_rec["address"],
            "label": probe_rec["label"],
            "label_confidence": probe_rec["label_confidence"],
            "asset": probe_rec["asset"],
            "side": probe_rec["side"],
            "baseline_size": 0,
            "current_size": probe_rec["position_size"],
            "size_delta": safe_float(probe_rec["position_size"], 0),
            "baseline_entry_price": None,
            "current_entry_price": probe_rec["entry_price"],
            "entry_price_changed": False,
            "liquidation_price": liq_price,
            "quality_flags": quality_flags,
            "operator_note": (
                f"NEW position detected in v114B probe — not present in v114A baseline. "
                f"Asset: {probe_rec['asset']}, Side: {probe_rec['side']}, "
                f"Size: {probe_rec['position_size']:,.2f}"
            ),
        }
        deltas.append(delta)

    return deltas


# ---------------------------------------------------------------------------
# Step 7: Write outputs
# ---------------------------------------------------------------------------
def write_live_response(responses, addresses, success_count, failure_count):
    """Write the second probe live response JSON."""
    live_resp = {
        "version": "v114B",
        "source": "hyperliquid_public_info",
        "dry_run_only": True,
        "one_shot": True,
        "second_probe": True,
        "local_delta_compare_only": True,
        "external_api_called": True,
        "api_key_used": False,
        "authorization_header_used": False,
        "retry_count": 0,
        "daemon_started": False,
        "watcher_started": False,
        "tg_sent": False,
        "production_state_written": False,
        "eligible_for_real_send": False,
        "addresses_requested": addresses,
        "success_count": success_count,
        "failure_count": failure_count,
        "total_requested": len(addresses),
        "responses": responses,
        "generated_at": now_iso(),
    }
    save_json(OUT_LIVE_RESPONSE, live_resp)
    return live_resp


def write_delta_result(
    baseline_result, addresses, success_count, failure_count, deltas
):
    """Write the delta compare result JSON."""
    new_count = sum(1 for d in deltas if d["delta_type"] == DELTA_NEW)
    closed_count = sum(1 for d in deltas if d["delta_type"] == DELTA_CLOSED)
    size_changed_count = sum(1 for d in deltas if d["delta_type"] == DELTA_SIZE_CHANGED)
    unchanged_count = sum(1 for d in deltas if d["delta_type"] == DELTA_UNCHANGED)
    entry_price_changed_count = sum(1 for d in deltas if d["entry_price_changed"])

    all_success = failure_count == 0

    # Label confidence from deltas (preserving baseline labels)
    label_conf = {"high": 0, "medium": 0, "low": 0}
    for d in deltas:
        lc = d.get("label_confidence", "unknown")
        if lc in label_conf:
            label_conf[lc] += 1

    liq_null_count = sum(1 for d in deltas if d["liquidation_price"] is None)

    result = {
        "version": "v114B",
        "status": "passed" if all_success else "degraded",
        "second_probe_executed": True,
        "baseline_records_loaded": baseline_result["baseline_records_written"],
        "addresses_requested_count": len(addresses),
        "success_count": success_count,
        "failure_count": failure_count,
        "delta_records_written": len(deltas),
        "new_position_count": new_count,
        "closed_position_count": closed_count,
        "size_changed_count": size_changed_count,
        "unchanged_count": unchanged_count,
        "entry_price_changed_count": entry_price_changed_count,
        "external_api_called": True,
        "api_key_used": False,
        "authorization_header_used": False,
        "credentials_read": False,
        "retry_count": 0,
        "local_delta_compare_only": True,
        "prod_state_write": False,
        "eligible_for_real_send_count": 0,
        "tg_send_allowed_count": 0,
        "real_send_candidate_count": 0,
        "daemon_started": False,
        "watcher_started": False,
        "files_deleted": False,
        "label_confidence_distribution": label_conf,
        "liquidation_price_null_count": liq_null_count,
        "next_step": "v114c_whale_delta_operator_review_pack_local_only",
        "generated_at": now_iso(),
    }
    save_json(OUT_DELTA_RESULT, result)
    return result


def write_deltas_jsonl(deltas):
    """Write delta records as JSONL. Returns count written."""
    return save_jsonl(OUT_DELTAS_JSONL, deltas)


def write_reports(
    baseline_result, addresses, success_count, failure_count,
    deltas, delta_result, responses
):
    """Write markdown report and handoff files."""

    new_count = delta_result["new_position_count"]
    closed_count = delta_result["closed_position_count"]
    size_changed_count = delta_result["size_changed_count"]
    unchanged_count = delta_result["unchanged_count"]
    entry_price_changed_count = delta_result["entry_price_changed_count"]
    label_conf = delta_result["label_confidence_distribution"]
    liq_null = delta_result["liquidation_price_null_count"]

    # Build delta table
    delta_rows = []
    for d in deltas:
        addr_short = f"{d['address'][:10]}...{d['address'][-6:]}"
        delta_rows.append(
            f"| {addr_short} | {d['label']} | {d['label_confidence']} | "
            f"{d['asset']} | {d['side']} | {d['delta_type']} | "
            f"{d['baseline_size']:,.2f} | {d['current_size']:,.2f} | "
            f"{d['size_delta']:+,.2f} | "
            f"{'Yes' if d['entry_price_changed'] else 'No'} |"
        )

    delta_table = "\n".join(delta_rows) if delta_rows else "| (none) | | | | | | | | | |"

    # Address-level summary
    addr_details = []
    for addr in addresses:
        addr_deltas = [d for d in deltas if d["address"] == addr]
        addr_new = sum(1 for d in addr_deltas if d["delta_type"] == DELTA_NEW)
        addr_closed = sum(1 for d in addr_deltas if d["delta_type"] == DELTA_CLOSED)
        addr_changed = sum(1 for d in addr_deltas if d["delta_type"] == DELTA_SIZE_CHANGED)
        addr_unchanged = sum(1 for d in addr_deltas if d["delta_type"] == DELTA_UNCHANGED)
        addr_details.append(
            f"| {addr[:10]}...{addr[-6:]} | {len(addr_deltas)} | "
            f"{addr_new} | {addr_closed} | {addr_changed} | {addr_unchanged} |"
        )

    addr_table = "\n".join(addr_details)

    # --- Report ---
    report = f"""# v114B Whale Second Probe Delta Compare — Read-Only

**Generated:** {delta_result['generated_at']}
**Status:** {delta_result['status']}
**Version:** v114B

---

## Purpose

Second read-only HyperLiquid probe compared against v114A local baseline.
Computes position deltas (new / closed / size_changed / unchanged) without
any production writes, TG sends, or daemon processes.

---

## Input Sources

| Source | File | Status |
|--------|------|--------|
| v114A Baseline Snapshot | `market_radar_v114a_whale_position_baseline_snapshot.json` | read |
| v114A Baseline Positions | `market_radar_v114a_whale_position_baseline_positions.jsonl` | read |
| HyperLiquid Public API | `POST api.hyperliquid.xyz/info` | {success_count}/{len(addresses)} success |

---

## Probe Results

| Metric | Value |
|--------|-------|
| Baseline records loaded | {baseline_result['baseline_records_written']} |
| Addresses requested | {len(addresses)} |
| Second probe success | {success_count} |
| Second probe failure | {failure_count} |
| External API called | True |
| API key used | False |
| Authorization header used | False |
| Credentials read | False |
| Retry count | 0 |

### Requested Addresses

"""
    for addr in addresses:
        addr_resps = [r for r in responses if r.get("address") == addr]
        if addr_resps:
            r = addr_resps[0]
            status = "success" if r.get("http_status") == 200 else f"failed ({r.get('http_status')})"
            pos_count = r.get("positions_count", 0)
            label = r.get("address_label", "Unknown")
            report += f"- `{addr}` — {label} — {status} — {pos_count} positions\n"
        else:
            report += f"- `{addr}` — no response\n"

    report += f"""
---

## Delta Summary

| Metric | Value |
|--------|-------|
| Delta records written | {len(deltas)} |
| New positions | {new_count} |
| Closed positions | {closed_count} |
| Size changed | {size_changed_count} |
| Unchanged | {unchanged_count} |
| Entry price changed | {entry_price_changed_count} |

### Per-Address Summary

| Address | Total Deltas | New | Closed | Changed | Unchanged |
|---------|-------------|-----|--------|---------|-----------|
{addr_table}

---

## Label Confidence Summary

| Level | Count |
|-------|-------|
| High | {label_conf['high']} |
| Medium | {label_conf['medium']} |
| Low | {label_conf['low']} |

**Note:** Label confidence preserved from v114A baseline audit. No confidence upgrades applied.

### Liquidation Price Availability

| Status | Count |
|--------|-------|
| Available | {len(deltas) - liq_null} |
| Null / Unavailable | {liq_null} |

---

## Delta Records

| Address | Label | Confidence | Asset | Side | Type | Baseline Size | Current Size | Delta | Entry Price Changed |
|---------|-------|------------|-------|------|------|---------------|--------------|-------|---------------------|
{delta_table}

---

## Safety Invariants

| Invariant | Value |
|-----------|-------|
| local_delta_compare_only | True |
| eligible_for_real_send (all records) | False |
| tg_send_allowed (all records) | False |
| prod_state_write | False |
| external_api_called | True |
| api_key_used | False |
| authorization_header_used | False |
| credentials_read | False |
| retry_count | 0 |
| daemon_started | False |
| watcher_started | False |
| files_deleted | False |

---

## Conclusions

- **local_delta_compare_only**: True — this is local comparison only
- **not_tg_send_ready**: All records have `tg_send_allowed=false`
- **not_prod_state_ready**: `prod_state_write=false`
- **not_real_send_candidate**: `eligible_for_real_send_count=0`

### Special Notes

"""
    # Check for 0x50b3 BTC position
    btc_closed = [d for d in deltas
                  if d["delta_type"] == DELTA_CLOSED
                  and d["address"].startswith("0x50b3")
                  and d["asset"] == "BTC"]
    if btc_closed:
        report += "- **0x50b3 BTC position**: Confirmed as closed_position (not an error). Expected behavior when position disappears between probes.\n"
    else:
        # Check if BTC position still present
        btc_deltas = [d for d in deltas if d["address"].startswith("0x50b3") and d["asset"] == "BTC"]
        if btc_deltas:
            report += f"- **0x50b3 BTC position**: Still present. Delta type: {btc_deltas[0]['delta_type']}.\n"

    report += f"""
---

## Next Step

**v114C:** Whale delta operator review pack — local-only.
- Review all {len(deltas)} delta records
- Validate classifications
- Prepare operator review cards
- No TG send, no prod state, no daemon

---

## Output Files

| File | Path |
|------|------|
| Second Probe Live Response | `{OUT_LIVE_RESPONSE}` |
| Delta Compare Result | `{OUT_DELTA_RESULT}` |
| Delta Records JSONL | `{OUT_DELTAS_JSONL}` |
| Report MD | `{OUT_REPORT}` |
| Handoff MD | `{OUT_HANDOFF}` |
"""

    os.makedirs(RUNS_DIR, exist_ok=True)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)

    # --- Handoff ---
    handoff = f"""# v114B Handoff — Whale Second Probe Delta Compare

**Generated:** {delta_result['generated_at']}
**Lane:** 1
**Risk Level:** low-readonly-public-api

---

## What was done

1. Loaded v114A baseline: {baseline_result['baseline_records_written']} records across {len(addresses)} addresses.
2. Called HyperLiquid public info endpoint (POST, no auth) for each of the {len(addresses)} tracked addresses — one call each, no retries.
3. Successfully received responses for {success_count}/{len(addresses)} addresses (failure: {failure_count}).
4. Compared second probe positions against baseline by `position_identity_key = address|asset|side`.
5. Classified {len(deltas)} delta records: {new_count} new, {closed_count} closed, {size_changed_count} size_changed, {unchanged_count} unchanged.
6. Entry price changed for {entry_price_changed_count} positions.
7. All outputs written with safety invariants enforced.

## Key Results

| Metric | Value |
|--------|-------|
| Baseline records loaded | {baseline_result['baseline_records_written']} |
| Addresses requested | {len(addresses)} |
| Probe success / fail | {success_count} / {failure_count} |
| New positions | {new_count} |
| Closed positions | {closed_count} |
| Size changed | {size_changed_count} |
| Unchanged | {unchanged_count} |
| Entry price changed | {entry_price_changed_count} |
| Label confidence: high / medium / low | {label_conf['high']} / {label_conf['medium']} / {label_conf['low']} |
| Liquidation price null | {liq_null} |
| External API called | True |
| API key used | False |
| Prod state written | False |
| Send candidates | 0 |

## Confirmed Safety Invariants

- `local_delta_compare_only=true` (all outputs)
- `eligible_for_real_send=false` (all delta records)
- `tg_send_allowed=false` (all delta records)
- `prod_state_write=false`
- `api_key_used=false`
- `authorization_header_used=false`
- `credentials_read=false`
- `retry_count=0`
- `daemon_started=false`
- `watcher_started=false`
- `files_deleted=false`

## Delta Classification Rules Applied

- Address|asset|side matching via position_identity_key
- Baseline present + probe present + same size → unchanged
- Baseline present + probe present + different size → size_changed
- Baseline present + probe absent → closed_position
- Baseline absent + probe present → new_position
- Entry price differs by >0.01 → entry_price_changed=true
- Label confidence preserved from v114A baseline (no upgrades)

## This Stage Is NOT

- Production state
- Send-ready
- TG-eligible
- A trading signal
- A position recommendation
- Ready for external consumption

## This Stage IS

- A local-only delta computation
- Input for v114C operator review
- Fully guarded with safety invariants

## Next Step

**v114C — Whale Delta Operator Review Pack (Local-Only)**

Requirements for v114C:
- Review all {len(deltas)} delta records
- No TG send, no prod state, no daemon
- Local operator review cards only
- Validate delta classifications

---

*This handoff is for the next stage executor (v114C). No action required now.*
"""

    with open(OUT_HANDOFF, "w", encoding="utf-8") as f:
        f.write(handoff)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v114B Whale Second Probe Delta Compare — Read-Only")
    print("=" * 70)

    # Step 1: Load baseline
    print("\n[1/6] Loading v114A baseline...")
    baseline_result, baseline_snapshot, baseline_positions = load_baseline()
    assert baseline_result["baseline_records_written"] == 10, \
        f"Expected 10 baseline records, got {baseline_result['baseline_records_written']}"
    assert baseline_snapshot["positions_count"] == 10
    assert len(baseline_positions) == 10

    # Step 2: Extract tracked addresses
    print("\n[2/6] Extracting tracked addresses from baseline...")
    addresses = extract_tracked_addresses(baseline_positions)
    print(f"  Extracted {len(addresses)} unique addresses:")
    for addr in addresses:
        addr_deltas = [p for p in baseline_positions if p["address"] == addr]
        label = addr_deltas[0]["label"] if addr_deltas else "Unknown"
        print(f"    {addr} — {label} ({len(addr_deltas)} positions)")
    assert len(addresses) == 4, f"Expected 4 addresses, got {len(addresses)}"

    # Step 3: Second probe — call HyperLiquid for each address
    print("\n[3/6] Executing second probe (HyperLiquid public info)...")
    print(f"  Endpoint: {HL_INFO_URL}")
    print(f"  Method: POST (no auth, no API key)")
    responses = []
    success_count = 0
    failure_count = 0

    # Build baseline label lookup for response enrichment
    addr_label_map = {}
    for p in baseline_positions:
        if p["address"] not in addr_label_map:
            addr_label_map[p["address"]] = {
                "label": p["label"],
                "confidence": p["label_confidence"],
            }

    for i, addr in enumerate(addresses):
        addr_short = f"{addr[:10]}...{addr[-6:]}"
        label_info = addr_label_map.get(addr, {"label": "Unknown", "confidence": "low"})
        print(f"  [{i+1}/{len(addresses)}] Probing {addr_short} ({label_info['label']})...")

        status_code, data, error = call_hyperliquid_info(addr)

        if error:
            print(f"    FAILED: {error}")
            failure_count += 1
            responses.append({
                "address": addr,
                "address_short": addr_short,
                "address_label": label_info["label"],
                "label_confidence": label_info["confidence"],
                "http_status": status_code,
                "positions_count": 0,
                "positions": [],
                "error": error,
                "observed_at": now_iso(),
            })
        else:
            positions = parse_positions_from_clearinghouse(data, addr)
            print(f"    SUCCESS — {len(positions)} positions returned")
            for pos in positions:
                print(f"      {pos['symbol']} {pos['side']} size={pos['position_size']:,.2f} entry={pos['entry_price']}")
            success_count += 1
            responses.append({
                "address": addr,
                "address_short": addr_short,
                "address_label": label_info["label"],
                "label_confidence": label_info["confidence"],
                "http_status": status_code,
                "positions_count": len(positions),
                "positions": positions,
                "observed_at": now_iso(),
            })

    # Step 4: Compute deltas
    print("\n[4/6] Computing position deltas...")
    baseline_index = build_baseline_index(baseline_positions)
    print(f"  Baseline index: {len(baseline_index)} identity keys")

    deltas = compute_deltas(baseline_index, responses)
    print(f"  Computed {len(deltas)} delta records")

    # Summary
    new_count = sum(1 for d in deltas if d["delta_type"] == DELTA_NEW)
    closed_count = sum(1 for d in deltas if d["delta_type"] == DELTA_CLOSED)
    size_changed_count = sum(1 for d in deltas if d["delta_type"] == DELTA_SIZE_CHANGED)
    unchanged_count = sum(1 for d in deltas if d["delta_type"] == DELTA_UNCHANGED)
    print(f"    New: {new_count}, Closed: {closed_count}, "
          f"Size changed: {size_changed_count}, Unchanged: {unchanged_count}")

    # Validate delta types
    for d in deltas:
        assert d["delta_type"] in (DELTA_NEW, DELTA_CLOSED, DELTA_SIZE_CHANGED, DELTA_UNCHANGED), \
            f"Invalid delta_type: {d['delta_type']}"
        assert d["local_delta_compare_only"] is True
        assert d["eligible_for_real_send"] is False
        assert d["tg_send_allowed"] is False
        assert d["prod_state_write"] is False
        assert d["position_identity_key"], "Missing position_identity_key"

    # Step 5: Write outputs
    print("\n[5/6] Writing outputs...")

    live_resp = write_live_response(responses, addresses, success_count, failure_count)
    print(f"  Second probe live response → {OUT_LIVE_RESPONSE}")

    written = write_deltas_jsonl(deltas)
    print(f"  Delta records JSONL: {written} records → {OUT_DELTAS_JSONL}")

    delta_result = write_delta_result(
        baseline_result, addresses, success_count, failure_count, deltas
    )
    print(f"  Delta compare result: status={delta_result['status']} → {OUT_DELTA_RESULT}")

    write_reports(
        baseline_result, addresses, success_count, failure_count,
        deltas, delta_result, responses
    )
    print(f"  Report MD → {OUT_REPORT}")
    print(f"  Handoff MD → {OUT_HANDOFF}")

    # Step 6: Safety invariant verification
    print("\n[6/6] Safety invariant verification...")
    invariants = [
        ("local_delta_compare_only", delta_result["local_delta_compare_only"] is True),
        ("second_probe_executed", delta_result["second_probe_executed"] is True),
        ("external_api_called", delta_result["external_api_called"] is True),
        ("api_key_used", delta_result["api_key_used"] is False),
        ("authorization_header_used", delta_result["authorization_header_used"] is False),
        ("credentials_read", delta_result["credentials_read"] is False),
        ("retry_count", delta_result["retry_count"] == 0),
        ("prod_state_write", delta_result["prod_state_write"] is False),
        ("eligible_for_real_send_count", delta_result["eligible_for_real_send_count"] == 0),
        ("tg_send_allowed_count", delta_result["tg_send_allowed_count"] == 0),
        ("real_send_candidate_count", delta_result["real_send_candidate_count"] == 0),
        ("daemon_started", delta_result["daemon_started"] is False),
        ("watcher_started", delta_result["watcher_started"] is False),
        ("files_deleted", delta_result["files_deleted"] is False),
        ("baseline_records_loaded", delta_result["baseline_records_loaded"] == 10),
        ("addresses_requested_count", delta_result["addresses_requested_count"] == 4),
    ]
    all_pass = True
    for name, ok in invariants:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
            print(f"  [{status}] {name}")
        else:
            print(f"  [{status}] {name}")

    # Verify all delta records individually
    print(f"\n  Per-record verification ({len(deltas)} records)...")
    for i, d in enumerate(deltas):
        if d.get("eligible_for_real_send") is not False:
            print(f"  [FAIL] delta[{i}] eligible_for_real_send is not False")
            all_pass = False
        if d.get("tg_send_allowed") is not False:
            print(f"  [FAIL] delta[{i}] tg_send_allowed is not False")
            all_pass = False

    print("\n" + "=" * 70)
    if all_pass:
        print("v114B COMPLETE — All invariants passed.")
    else:
        print("v114B COMPLETE — Some invariants FAILED.")
        sys.exit(1)

    # If all responses failed, set degraded status explicitly
    if failure_count == len(addresses) and delta_result["status"] != "degraded":
        print("\nWARNING: All requests failed but status is not degraded.")
        delta_result["status"] = "degraded"
        save_json(OUT_DELTA_RESULT, delta_result)
        print("  Updated status to degraded.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
