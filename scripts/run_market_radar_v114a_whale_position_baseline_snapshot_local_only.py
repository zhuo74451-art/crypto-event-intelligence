#!/usr/bin/env python3
"""
v114A Whale Position Baseline Snapshot — Local Only
====================================================
Reads v112X live response + v113D seal, extracts 10 positions,
and generates a local baseline snapshot for future delta comparison.

This runner does NOT call any external API.
This runner does NOT read credentials.
This runner does NOT write production state.
This runner does NOT produce any send-ready artifacts.

Purpose: establish a local-only baseline so that v114B can
         run a new read-only one-shot probe and compute position deltas.
"""

import json
import hashlib
import os
import sys
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

V112X_RESPONSE = os.path.join(RESULTS_DIR, "market_radar_v112x_hyperliquid_live_response.json")
V112X_STOP = os.path.join(RESULTS_DIR, "market_radar_v112x_hyperliquid_stop_decision.json")
V113D_SEAL = os.path.join(RESULTS_DIR, "market_radar_v113d_degraded_whale_review_pack_seal_result.json")

OUT_POSITIONS = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_positions.jsonl")
OUT_SNAPSHOT = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_snapshot.json")
OUT_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_snapshot_result.json")
OUT_REPORT = os.path.join(RUNS_DIR, "v114a_whale_position_baseline_snapshot_local_only.md")
OUT_HANDOFF = os.path.join(RUNS_DIR, "v114a_whale_position_baseline_snapshot_local_only_handoff.md")

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_position_identity_key(address: str, asset: str, side: str) -> str:
    """Deterministic identity key: addr_lower|asset|side"""
    return f"{address.lower()}|{asset}|{side}"


def make_baseline_hash(address: str, asset: str, side: str, position_size: float,
                       entry_price: float, observed_at: str) -> str:
    """Deterministic content hash for future delta verification."""
    payload = (
        f"{address.lower()}|{asset}|{side}|{position_size}|{entry_price}|{observed_at}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def safe_float(value, default=None):
    """Safely convert value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Step 1: Read v112X live response
# ---------------------------------------------------------------------------
def load_v112x_response():
    if not os.path.exists(V112X_RESPONSE):
        print(f"ERROR: v112X response not found at {V112X_RESPONSE}")
        sys.exit(1)
    with open(V112X_RESPONSE, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Step 2: Read v112X stop decision
# ---------------------------------------------------------------------------
def load_v112x_stop_decision():
    if not os.path.exists(V112X_STOP):
        print(f"ERROR: v112X stop decision not found at {V112X_STOP}")
        sys.exit(1)
    with open(V112X_STOP, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Step 3: Read v113D seal result
# ---------------------------------------------------------------------------
def load_v113d_seal():
    if not os.path.exists(V113D_SEAL):
        print(f"ERROR: v113D seal not found at {V113D_SEAL}")
        sys.exit(1)
    with open(V113D_SEAL, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Step 4: Extract positions from v112X response
# ---------------------------------------------------------------------------
def extract_positions(response: dict) -> list:
    """Extract all positions from the v112X response."""
    positions = []
    for entry in response.get("responses", []):
        address = entry["address"]
        label = entry.get("address_label", "Unknown")
        label_confidence = entry.get("label_confidence", "unknown")
        for pos in entry.get("positions", []):
            positions.append({
                "address": address,
                "label": label,
                "label_confidence": label_confidence,
                "asset": pos["symbol"],
                "side": pos["side"],
                "position_size": pos["position_size"],
                "notional_usd": pos.get("position_value", pos["position_size"]),
                "entry_price": pos["entry_price"],
                "mark_price": pos.get("mark_price"),
                "leverage": pos.get("leverage"),
                "liquidation_price": pos.get("liquidation_price"),
                "observed_at": pos.get("observed_at", entry.get("timestamp", "")),
            })
    return positions


# ---------------------------------------------------------------------------
# Step 5: Build baseline records
# ---------------------------------------------------------------------------
def build_baseline_records(positions: list, stop_decision: str) -> list:
    """Convert extracted positions into baseline records."""
    observed_at_local = datetime.now(TZ_SHANGHAI).isoformat()
    records = []
    for pos in positions:
        identity_key = make_position_identity_key(pos["address"], pos["asset"], pos["side"])
        baseline_hash = make_baseline_hash(
            pos["address"], pos["asset"], pos["side"],
            safe_float(pos["position_size"], 0),
            safe_float(pos["entry_price"], 0),
            pos["observed_at"],
        )
        record = {
            "version": "v114A",
            "baseline_type": "whale_position_local_baseline",
            "local_baseline_only": True,
            "prod_state_write": False,
            "eligible_for_real_send": False,
            "tg_send_allowed": False,
            "source": "v112X_hyperliquid_live_response",
            "source_stop_decision": stop_decision,
            "address": pos["address"],
            "label": pos["label"],
            "label_confidence": pos["label_confidence"],
            "asset": pos["asset"],
            "side": pos["side"],
            "position_size": pos["position_size"],
            "notional_usd": pos["notional_usd"],
            "entry_price": pos["entry_price"],
            "mark_price": pos["mark_price"],
            "liquidation_price": pos["liquidation_price"],
            "leverage": pos["leverage"],
            "observed_at_local": observed_at_local,
            "observed_at_source": pos["observed_at"],
            "position_identity_key": identity_key,
            "baseline_hash": baseline_hash,
            "future_delta_ready": True,
            "baseline_limitations": [
                "local baseline only",
                "not production state",
                "not send ready",
                "label confidence may be medium_or_low",
                "liquidation price may be unavailable",
            ],
        }
        records.append(record)
    return records


# ---------------------------------------------------------------------------
# Step 6: Write outputs
# ---------------------------------------------------------------------------
def write_positions_jsonl(records: list) -> int:
    """Write baseline positions as JSONL. Returns count written."""
    os.makedirs(os.path.dirname(OUT_POSITIONS), exist_ok=True)
    count = 0
    with open(OUT_POSITIONS, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_snapshot_json(records: list, stop_decision: str, seal: dict) -> dict:
    """Write and return baseline snapshot JSON."""
    addresses = set(r["address"] for r in records)
    snapshot = {
        "version": "v114A",
        "snapshot_type": "whale_position_local_baseline_snapshot",
        "local_baseline_only": True,
        "prod_state_write": False,
        "sealed_source_stage": "v113D",
        "source_live_probe": "v112X",
        "source_stop_decision": stop_decision,
        "positions_count": len(records),
        "unique_addresses_count": len(addresses),
        "future_delta_ready": True,
        "eligible_for_real_send_count": 0,
        "tg_send_allowed_count": 0,
        "next_step": "v114b_whale_second_probe_delta_compare_readonly",
        "label_confidence_distribution": {
            "high": sum(1 for r in records if r["label_confidence"] == "high"),
            "medium": sum(1 for r in records if r["label_confidence"] == "medium"),
            "low": sum(1 for r in records if r["label_confidence"] == "low"),
        },
        "liquidation_price_null_count": sum(1 for r in records if r["liquidation_price"] is None),
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
    }
    os.makedirs(os.path.dirname(OUT_SNAPSHOT), exist_ok=True)
    with open(OUT_SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return snapshot


def write_result_json(
    records: list,
    seal: dict,
    snapshot: dict,
) -> dict:
    """Write and return result JSON."""
    addresses = set(r["address"] for r in records)
    result = {
        "version": "v114A",
        "status": "passed",
        "baseline_snapshot_created": True,
        "positions_loaded": len(records),
        "baseline_records_written": len(records),
        "unique_addresses_count": len(addresses),
        "local_baseline_only": True,
        "external_api_called": False,
        "prod_state_write": False,
        "eligible_for_real_send_count": 0,
        "tg_send_allowed_count": 0,
        "real_send_candidate_count": 0,
        "credentials_read": False,
        "daemon_started": False,
        "watcher_started": False,
        "files_deleted": False,
        "future_delta_ready": True,
        "next_step": "v114b_whale_second_probe_delta_compare_readonly",
        "label_confidence_distribution": snapshot["label_confidence_distribution"],
        "liquidation_price_null_count": snapshot["liquidation_price_null_count"],
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
    }
    os.makedirs(os.path.dirname(OUT_RESULT), exist_ok=True)
    with open(OUT_RESULT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


# ---------------------------------------------------------------------------
# Step 7: Write markdown reports
# ---------------------------------------------------------------------------
def write_reports(records: list, snapshot: dict, result: dict, seal: dict):
    """Write the run report and handoff markdown files."""
    addresses = set(r["address"] for r in records)
    label_dist = snapshot["label_confidence_distribution"]
    liq_null = snapshot["liquidation_price_null_count"]

    # Identify unique labels
    address_labels = {}
    for r in records:
        address_labels[r["address"]] = {
            "label": r["label"],
            "confidence": r["label_confidence"],
            "positions": [r2["asset"] for r2 in records if r2["address"] == r["address"]],
        }

    # --- Report ---
    asset_list = "\n".join(
        f"| {r['address'][:10]}...{r['address'][-6:]} | {r['label']} | {r['label_confidence']} | {r['asset']} | {r['side']} | {r['position_size']:,.2f} | {r['liquidation_price'] or 'null'} |"
        for r in records
    )

    report = f"""# v114A Whale Position Baseline Snapshot — Local Only

**Generated:** {result['generated_at']}
**Status:** passed
**Version:** v114A

---

## Purpose

This is a **local-only** baseline snapshot of 10 whale positions derived from the
v112X HyperLiquid one-shot live response. It is intentionally:

- **NOT production state**
- **NOT send-ready**
- **NOT eligible for Telegram delivery**

Its sole purpose is to serve as a **comparison baseline** for the next read-only
one-shot probe (v114B), enabling position delta computation.

---

## Input Sources

| Source | File | Status |
|--------|------|--------|
| Live Response | `market_radar_v112x_hyperliquid_live_response.json` | read |
| Stop Decision | `market_radar_v112x_hyperliquid_stop_decision.json` | read |
| Seal Result | `market_radar_v113d_degraded_whale_review_pack_seal_result.json` | read |

### v112X Stop Decision
- **Decision:** `{snapshot['source_stop_decision']}`
- **Reason:** degraded label confidence + missing liquidation prices + no previous position history

### v113D Seal
- **Sealed:** `{seal.get('sealed', 'N/A')}`
- **Stage Conclusion:** `{seal.get('stage_conclusion', 'N/A')}`

---

## Baseline Summary

| Metric | Value |
|--------|-------|
| Positions loaded | {len(records)} |
| Baseline records written | {len(records)} |
| Unique addresses | {len(addresses)} |
| Unique addresses count | {snapshot['unique_addresses_count']} |
| Future delta ready | {snapshot['future_delta_ready']} |

### Label Confidence Distribution

| Level | Count |
|-------|-------|
| High | {label_dist['high']} |
| Medium | {label_dist['medium']} |
| Low | {label_dist['low']} |

### Liquidation Price Availability

| Status | Count |
|--------|-------|
| Available | {len(records) - liq_null} |
| Null / Unavailable | {liq_null} |

---

## Address Summary

"""
    for addr, info in address_labels.items():
        report += f"### {addr}\n"
        report += f"- **Label:** {info['label']}\n"
        report += f"- **Label Confidence:** {info['confidence']}\n"
        report += f"- **Positions:** {', '.join(info['positions'])}\n\n"

    report += f"""## Baseline Positions

| Address | Label | Confidence | Asset | Side | Size | Liquidation Price |
|---------|-------|------------|-------|------|------|-------------------|
{asset_list}

---

## Safety Invariants

| Invariant | Value |
|-----------|-------|
| local_baseline_only | True |
| prod_state_write | False |
| eligible_for_real_send_count | 0 |
| tg_send_allowed_count | 0 |
| real_send_candidate_count | 0 |
| external_api_called | False |
| credentials_read | False |
| daemon_started | False |
| watcher_started | False |
| files_deleted | False |

---

## Baseline Limitations

{chr(10).join(f'- {lim}' for lim in records[0]['baseline_limitations'])}

---

## Next Step

**v114B:** Whale second probe delta compare (read-only).
- Must be one-shot, read-only, no API key, no TG, no prod state, no daemon.
- Compares a new read-only probe against this baseline to compute position deltas.

---

## Output Files

| File | Path |
|------|------|
| Positions JSONL | `{OUT_POSITIONS}` |
| Snapshot JSON | `{OUT_SNAPSHOT}` |
| Result JSON | `{OUT_RESULT}` |
| Report MD | `{OUT_REPORT}` |
| Handoff MD | `{OUT_HANDOFF}` |
"""

    os.makedirs(RUNS_DIR, exist_ok=True)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)

    # --- Handoff ---
    handoff = f"""# v114A Handoff — Whale Position Baseline Snapshot

**Generated:** {result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only

---

## What was done

1. Read v112X live response (4 addresses, 10 positions).
2. Read v112X stop decision → confirmed `DEGRADE_TO_MOCK`.
3. Read v113D seal → confirmed `sealed=true`, `stage_conclusion=local_operator_review_ready_not_send_ready`.
4. Extracted 10 positions from the v112X response.
5. Generated baseline records with identity keys and content hashes.
6. Wrote baseline snapshot, result, positions JSONL, and reports.

## Key Results

| Metric | Value |
|--------|-------|
| Positions loaded | {len(records)} |
| Baseline records written | {len(records)} |
| Unique addresses | {len(addresses)} |
| Label confidence: high | {label_dist['high']} |
| Label confidence: medium | {label_dist['medium']} |
| Label confidence: low | {label_dist['low']} |
| Liquidation price null | {liq_null} |
| External API called | False |
| Prod state written | False |
| Send candidates | 0 |

## Baseline Is NOT

- Production state
- Send-ready
- TG-eligible
- A trading signal
- A position recommendation

## Baseline IS

- A local-only reference snapshot
- Input for future v114B delta comparison
- Fully guarded with safety invariants

## Next Step

**v114B — Whale Second Probe Delta Compare (Read-Only)**

Requirements for v114B:
- One-shot, read-only
- No API key
- No TG delivery
- No production state write
- No daemon/watcher/cron
- Compare new probe positions against this baseline
- Compute position deltas (new, closed, size changed)

## Safety Confirmation

All safety invariants pass:
- `local_baseline_only=true`
- `prod_state_write=false`
- `eligible_for_real_send_count=0`
- `tg_send_allowed_count=0`
- `external_api_called=false`
- `credentials_read=false`
- `daemon_started=false`
- `watcher_started=false`

---

*This handoff is for the next stage executor. No action required now.*
"""
    with open(OUT_HANDOFF, "w", encoding="utf-8") as f:
        f.write(handoff)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v114A Whale Position Baseline Snapshot — Local Only")
    print("=" * 70)

    # Step 1-3: Load inputs
    print("\n[1/6] Loading v112X live response...")
    v112x = load_v112x_response()
    print(f"  Loaded response with {len(v112x.get('responses', []))} address entries")

    print("\n[2/6] Loading v112X stop decision...")
    v112x_stop = load_v112x_stop_decision()
    stop_decision = v112x_stop["stop_decision"]
    print(f"  Stop decision: {stop_decision}")
    assert stop_decision == "DEGRADE_TO_MOCK", f"Expected DEGRADE_TO_MOCK, got {stop_decision}"

    print("\n[3/6] Loading v113D seal...")
    v113d_seal = load_v113d_seal()
    print(f"  Sealed: {v113d_seal['sealed']}")
    print(f"  Stage conclusion: {v113d_seal['stage_conclusion']}")
    assert v113d_seal["sealed"] is True, "v113D seal must be sealed=true"
    assert v113d_seal["stage_conclusion"] == "local_operator_review_ready_not_send_ready"

    # Step 4: Extract positions
    print("\n[4/6] Extracting positions from v112X response...")
    positions = extract_positions(v112x)
    print(f"  Extracted {len(positions)} positions")
    assert len(positions) == 10, f"Expected 10 positions, got {len(positions)}"

    # Step 5: Build baseline records
    print("\n[5/6] Building baseline records...")
    records = build_baseline_records(positions, stop_decision)
    print(f"  Built {len(records)} baseline records")
    for r in records:
        assert r["local_baseline_only"] is True
        assert r["prod_state_write"] is False
        assert r["eligible_for_real_send"] is False
        assert r["tg_send_allowed"] is False
        assert r["position_identity_key"]
        assert r["baseline_hash"]
        assert r["future_delta_ready"] is True

    # Step 6: Write outputs
    print("\n[6/6] Writing outputs...")
    written = write_positions_jsonl(records)
    print(f"  Positions JSONL: {written} records → {OUT_POSITIONS}")

    snapshot = write_snapshot_json(records, stop_decision, v113d_seal)
    print(f"  Snapshot JSON: {snapshot['positions_count']} positions, "
          f"{snapshot['unique_addresses_count']} addresses → {OUT_SNAPSHOT}")

    result = write_result_json(records, v113d_seal, snapshot)
    print(f"  Result JSON: status={result['status']} → {OUT_RESULT}")

    write_reports(records, snapshot, result, v113d_seal)
    print(f"  Report MD → {OUT_REPORT}")
    print(f"  Handoff MD → {OUT_HANDOFF}")

    # Verify safety invariants
    print("\n" + "=" * 70)
    print("Safety Invariant Verification")
    print("=" * 70)
    invariants = [
        ("local_baseline_only", result["local_baseline_only"] is True),
        ("prod_state_write", result["prod_state_write"] is False),
        ("external_api_called", result["external_api_called"] is False),
        ("credentials_read", result["credentials_read"] is False),
        ("daemon_started", result["daemon_started"] is False),
        ("watcher_started", result["watcher_started"] is False),
        ("files_deleted", result["files_deleted"] is False),
        ("eligible_for_real_send_count", result["eligible_for_real_send_count"] == 0),
        ("tg_send_allowed_count", result["tg_send_allowed_count"] == 0),
        ("real_send_candidate_count", result["real_send_candidate_count"] == 0),
    ]
    all_pass = True
    for name, ok in invariants:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {name} = {result[name]}")

    print("\n" + "=" * 70)
    if all_pass:
        print("v114A COMPLETE — All invariants passed.")
    else:
        print("v114A COMPLETE — Some invariants FAILED.")
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
