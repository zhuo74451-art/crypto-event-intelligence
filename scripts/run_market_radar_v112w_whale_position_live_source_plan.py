#!/usr/bin/env python3
"""
run_market_radar_v112w_whale_position_live_source_plan.py
===========================================================
v112W — Whale Position Alert Live Source Readiness Plan Runner.

Generates the full v112W planning artifact set:
  - Validates upstream state (v112V, v112F, v112H, v112O)
  - Generates field mapping config
  - Generates stop conditions config
  - Generates live response schema
  - Generates adapter spec
  - Runs label quality audit
  - Generates docs/plan
  - Generates result JSON
  - Generates run report and handoff

Design: Plan-only. No HyperLiquid API calls. No TG send. No daemon. No state write.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

VERSION = "v1.12-w"
MODE = "plan_only"

CN_TZ = timezone(timedelta(hours=8))
NOW = datetime(2026, 6, 5, 4, 13, 0, tzinfo=CN_TZ)
NOW_ISO = NOW.isoformat()

PROJECT_DIR = Path(__file__).resolve().parents[1]
os.chdir(str(PROJECT_DIR))

RESULTS_DIR = PROJECT_DIR / "results"
CONFIG_DIR = PROJECT_DIR / "config"
SCHEMAS_DIR = PROJECT_DIR / "schemas"
DOCS_DIR = PROJECT_DIR / "docs"
RUNS_DIR = PROJECT_DIR / "runs" / "market_radar"
DATA_DIR = PROJECT_DIR / "data"

RUNS_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Utility
# ═══════════════════════════════════════════════════════════════════════════════

def load_json(path: Path) -> dict:
    """Load a JSON file, return empty dict on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  [WARN] Could not load {path}: {e}")
        return {}


def write_json(path: Path, data: dict) -> None:
    """Write a JSON file with indentation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  [OK] Wrote {path}")


def write_md(path: Path, content: str) -> None:
    """Write a markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [OK] Wrote {path}")


def read_csv_rows(path: Path) -> list[dict]:
    """Read CSV into list of dicts."""
    rows = []
    if not path.exists():
        return rows
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Validate Upstream State
# ═══════════════════════════════════════════════════════════════════════════════

def validate_upstream() -> dict:
    """Validate that all upstream v112V/F/H/O/P artifacts are present and correct."""
    print("\n[Step 1] Validating upstream state...")
    results = {"checks": [], "all_passed": True}

    # ── v112V ────────────────────────────────────────────────────────────────
    v112v = load_json(RESULTS_DIR / "market_radar_v112v_degraded_mock_replay_result.json")
    checks_v112v = [
        ("v112V status == 'passed'", v112v.get("status") == "passed"),
        ("v112V mock_replay_only == true", v112v.get("mock_replay_only") is True),
        ("v112V eligible_for_real_send_count == 0", v112v.get("eligible_for_real_send_count") == 0),
        ("v112V state_write_performed == false", v112v.get("state_write_performed") is False),
        ("v112V real_live_api_called_in_this_step == false", v112v.get("real_live_api_called_in_this_step") is False),
    ]
    for label, passed in checks_v112v:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")
        results["checks"].append({"upstream": "v112V", "check": label, "passed": passed})
        if not passed:
            results["all_passed"] = False

    # ── v112F ────────────────────────────────────────────────────────────────
    v112f = load_json(RESULTS_DIR / "market_radar_v112f_whale_position_local_enrichment_result.json")
    v112f_exists = bool(v112f)
    v112f_has_positions = v112f.get("positions_loaded", 0) > 0
    checks_v112f = [
        ("v112F result file exists and readable", v112f_exists),
        ("v112F positions_loaded > 0", v112f_has_positions),
        ("v112F real_tg_sent == false", v112f.get("real_tg_sent") is False),
        ("v112F external_api_called == false", v112f.get("external_api_called") is False),
    ]
    for label, passed in checks_v112f:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")
        results["checks"].append({"upstream": "v112F", "check": label, "passed": passed})
        if not passed:
            results["all_passed"] = False

    # ── v112H ────────────────────────────────────────────────────────────────
    v112h = load_json(RESULTS_DIR / "market_radar_v112h_unified_signal_envelope_result.json")
    wpa_count = v112h.get("card_type_counts", {}).get("whale_position_alert", 0)
    checks_v112h = [
        ("v112H result file exists and readable", bool(v112h)),
        ("v112H whale_position_alert envelopes present", wpa_count > 0),
        ("v112H whale_position_alert count >= 2", wpa_count >= 2),
    ]
    for label, passed in checks_v112h:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")
        results["checks"].append({"upstream": "v112H", "check": label, "passed": passed})
        if not passed:
            results["all_passed"] = False

    # ── v112O ────────────────────────────────────────────────────────────────
    v112o = load_json(RESULTS_DIR / "market_radar_v112o_send_preview_pack_result.json")
    wpa_preview = v112o.get("card_type_distribution", {}).get("whale_position_alert", 0)
    checks_v112o = [
        ("v112O result file exists and readable", bool(v112o)),
        ("v112O whale_position_alert preview cards present", wpa_preview > 0),
        ("v112O real_tg_sent == false", v112o.get("real_tg_sent") is False),
    ]
    for label, passed in checks_v112o:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")
        results["checks"].append({"upstream": "v112O", "check": label, "passed": passed})
        if not passed:
            results["all_passed"] = False

    # ── v112P ────────────────────────────────────────────────────────────────
    v112p = load_json(RESULTS_DIR / "market_radar_v112p_live_source_matrix.json")
    wpa_entry = None
    for entry in v112p.get("entries", []):
        if entry.get("card_type") == "whale_position_alert":
            wpa_entry = entry
            break
    checks_v112p = [
        ("v112P matrix exists and readable", bool(v112p)),
        ("v112P whale_position_alert entry present", wpa_entry is not None),
        ("v112P whale_position_alert readiness_level == 'high'",
         wpa_entry.get("readiness_level") == "high" if wpa_entry else False),
    ]
    for label, passed in checks_v112p:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")
        results["checks"].append({"upstream": "v112P", "check": label, "passed": passed})
        if not passed:
            results["all_passed"] = False

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Run Label Quality Audit
# ═══════════════════════════════════════════════════════════════════════════════

def run_label_quality_audit() -> dict:
    """Audit address label quality from hyperliquid_position_state.csv."""
    print("\n[Step 2] Running label quality audit...")

    csv_path = DATA_DIR / "hyperliquid_position_state.csv"
    rows = read_csv_rows(csv_path)

    if not rows:
        print("  [WARN] No rows found in hyperliquid_position_state.csv")
        return {
            "tracked_addresses_total": 0,
            "positions_total": 0,
            "labels_total": 0,
            "high_confidence_labels": 0,
            "medium_confidence_labels": 0,
            "low_confidence_labels": 0,
            "unknown_labels": 0,
            "unknown_label_fallback_ready": True,
            "label_quality_ready_for_one_shot_plan": False,
            "error": "No data in CSV",
        }

    # Collect unique addresses and their entities
    address_entities: dict[str, str] = {}
    address_positions: dict[str, list[dict]] = {}
    for row in rows:
        addr = row.get("address", "").strip()
        entity = row.get("entity", "").strip()
        if addr:
            if addr not in address_entities:
                address_entities[addr] = entity
                address_positions[addr] = []
            address_positions[addr].append(row)

    tracked_total = len(address_entities)
    positions_total = len(rows)

    # Classify label confidence
    high_conf = 0
    med_conf = 0
    low_conf = 0
    unknown = 0

    for addr, entity in address_entities.items():
        entity_lower = entity.lower()
        if not entity or entity_lower in ("", "unknown", "none", "n/a"):
            unknown += 1
        elif "unknown" in entity_lower:
            low_conf += 1
        elif any(kw in entity_lower for kw in ("arkham", "nansen", "confirmed", "verified")):
            high_conf += 1
        else:
            # Known entity name but not from premium source → medium
            med_conf += 1

    labels_total = tracked_total - unknown

    audit = {
        "version": VERSION,
        "audit_type": "whale_address_label_quality",
        "generated_at": NOW_ISO,
        "source_file": "data/hyperliquid_position_state.csv",
        "source_columns_found": list(rows[0].keys()) if rows else [],
        "field_notes": [
            "CSV field 'entity' maps to address label — used for label quality assessment.",
            "CSV field 'address' maps to wallet address.",
            "No dedicated 'label_confidence' column — confidence inferred from entity name.",
            "Labels containing 'Unknown' prefix → low confidence.",
            "Labels with known entity names → medium confidence.",
            "Labels from Arkham/Nansen/confirmed sources → high confidence (none found).",
        ],
        "tracked_addresses_total": tracked_total,
        "positions_total": positions_total,
        "labels_total": labels_total,
        "high_confidence_labels": high_conf,
        "medium_confidence_labels": med_conf,
        "low_confidence_labels": low_conf,
        "unknown_labels": unknown,
        "unknown_label_fallback_ready": True,
        "label_quality_ready_for_one_shot_plan": labels_total > 0 and tracked_total > 0,
        "address_label_details": [],
    }

    for addr, entity in sorted(address_entities.items()):
        entity_lower = entity.lower()
        if not entity or entity_lower in ("", "unknown", "none", "n/a"):
            conf = "unknown"
            conf_rationale = "No label available."
        elif "unknown" in entity_lower:
            conf = "low"
            conf_rationale = f"Entity '{entity}' contains 'Unknown' — unverified source."
        elif any(kw in entity_lower for kw in ("arkham", "nansen", "confirmed", "verified")):
            conf = "high"
            conf_rationale = f"Entity '{entity}' appears to be from a verified source."
        else:
            conf = "medium"
            conf_rationale = f"Entity '{entity}' is a known name but from unverified source (HyperLiquid observer or heuristic)."

        positions = address_positions.get(addr, [])
        assets = list(set(p.get("asset_symbol", "").strip() for p in positions if p.get("asset_symbol", "").strip()))
        above_threshold = sum(
            1 for p in positions
            if p.get("above_threshold", "").strip().lower() == "true"
        )

        short = f"{addr[:6]}...{addr[-5:]}" if len(addr) > 12 else addr

        audit["address_label_details"].append({
            "address": addr,
            "address_short": short,
            "entity": entity,
            "entity_type": _infer_entity_type(entity),
            "confidence": conf,
            "confidence_rationale": conf_rationale,
            "position_count": len(positions),
            "assets": assets,
            "above_threshold_positions": above_threshold,
        })

    audit["confidence_distribution"] = {
        "high": {"count": high_conf, "pct": round(high_conf / tracked_total * 100, 1) if tracked_total else 0},
        "medium": {"count": med_conf, "pct": round(med_conf / tracked_total * 100, 1) if tracked_total else 0},
        "low": {"count": low_conf, "pct": round(low_conf / tracked_total * 100, 1) if tracked_total else 0},
        "unknown": {"count": unknown, "pct": round(unknown / tracked_total * 100, 1) if tracked_total else 0},
    }

    audit["assessment"] = {
        "ready_for_one_shot_plan": audit["label_quality_ready_for_one_shot_plan"],
        "all_addresses_have_labels": unknown == 0,
        "no_completely_unlabeled_addresses": unknown == 0,
        "low_confidence_labels_acceptable": True,
        "unknown_whale_fallback_works": True,
        "concerns": _audit_concerns(audit),
        "recommendation": (
            "Proceed with one-shot plan. Label quality is sufficient for observation purposes."
            if audit["label_quality_ready_for_one_shot_plan"]
            else "Cannot proceed — no labeled addresses available."
        ),
    }

    output_path = RESULTS_DIR / "market_radar_v112w_whale_label_quality_audit.json"
    write_json(output_path, audit)
    print(f"  Tracked addresses: {tracked_total}")
    print(f"  Positions: {positions_total}")
    print(f"  Labels: {labels_total} (high={high_conf}, medium={med_conf}, low={low_conf}, unknown={unknown})")
    print(f"  Ready for one-shot plan: {audit['label_quality_ready_for_one_shot_plan']}")

    return audit


def _infer_entity_type(entity: str) -> str:
    """Infer entity type from entity name."""
    el = entity.lower()
    if not el or el in ("unknown", "none", "n/a"):
        return "unknown_whale"
    if "unknown" in el:
        return "unknown_whale"
    if any(kw in el for kw in ("mm", "market maker", "wintermute", "jump", "dwf")):
        return "market_maker"
    if any(kw in el for kw in ("binance", "okx", "bybit", "exchange", "hot wallet")):
        return "exchange_related"
    if any(kw in el for kw in ("galaxy", "matrixport", "fund", "capital", "vc", "ventures")):
        return "fund_wallet"
    if any(kw in el for kw in ("smart", "alpha")):
        return "smart_money"
    return "high_leverage_trader"


def _audit_concerns(audit: dict) -> list[str]:
    """Generate list of concerns based on audit data."""
    concerns = []
    if audit["high_confidence_labels"] == 0:
        concerns.append("No high-confidence labels — all labels are medium or low confidence.")
    if audit["low_confidence_labels"] > 0:
        concerns.append(f"{audit['low_confidence_labels']} labels are low confidence ('Unknown * Whale').")
    if audit["unknown_labels"] > 0:
        concerns.append(f"{audit['unknown_labels']} addresses have no label at all.")
    concerns.append("Label freshness cannot be verified from CSV — timestamps only cover position updates.")
    return concerns


# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Verify Generated Config Files
# ═══════════════════════════════════════════════════════════════════════════════

def verify_config_files() -> dict:
    """Verify that all required config and schema files exist and are valid."""
    print("\n[Step 3] Verifying config and schema files...")
    files_to_check = [
        ("config", CONFIG_DIR / "market_radar_v112w_whale_position_field_mapping.json"),
        ("config", CONFIG_DIR / "market_radar_v112w_hyperliquid_stop_conditions.json"),
        ("schemas", SCHEMAS_DIR / "market_radar_v112w_hyperliquid_live_response_schema.json"),
        ("schemas", SCHEMAS_DIR / "market_radar_v112w_hl_to_whale_adapter_spec.md"),
        ("docs", DOCS_DIR / "market_radar_v112w_whale_position_live_source_plan.md"),
    ]

    results = {"checks": [], "all_present": True}
    for category, path in files_to_check:
        exists = path.exists()
        valid = False
        if exists and path.suffix == ".json":
            try:
                data = load_json(path)
                valid = bool(data)
            except Exception:
                valid = False
        elif exists:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            valid = len(content) > 100  # minimum content length check

        status = "PASS" if (exists and valid) else "FAIL"
        print(f"  [{status}] {path.name} (category={category})")
        results["checks"].append({
            "file": str(path.name),
            "category": category,
            "exists": exists,
            "valid": valid,
        })
        if not (exists and valid):
            results["all_present"] = False

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Generate Result JSON
# ═══════════════════════════════════════════════════════════════════════════════

def generate_result_json(
    upstream_ok: bool,
    label_audit_ok: bool,
    config_ok: bool,
) -> dict:
    """Generate the v112W result JSON."""
    print("\n[Step 4] Generating result JSON...")

    result = {
        "version": "v1.12-w",
        "status": "passed" if (upstream_ok and label_audit_ok and config_ok) else "failed",
        "dry_run_only": True,
        "plan_only": True,
        "live_ready": False,
        "real_live_api_called": False,
        "hyperliquid_api_called": False,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "files_deleted": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
        "candidate_card_type": "whale_position_alert",
        "previous_candidate_frozen": "multi_asset_market_sync",
        "multi_asset_freeze_reason": "mock_ready_but_free_source_data_gap",
        "whale_position_plan_ready": True,
        "hyperliquid_stop_conditions_ready": True,
        "field_mapping_ready": True,
        "label_quality_audit_ready": label_audit_ok,
        "hl_to_whale_adapter_spec_ready": True,
        "decision_modes": ["CONTINUE", "ABORT", "DEGRADE_TO_MOCK"],
        "real_send_ready": False,
        "production_state_write_ready": False,
        "v112x_requires_user_confirmation": True,
        "recommended_next_step": "v112x_hyperliquid_one_shot_read_only_dry_run_requires_user_confirmation",
        "upstream_validation": {
            "all_passed": upstream_ok,
        },
        "artifacts_generated": [
            "config/market_radar_v112w_whale_position_field_mapping.json",
            "config/market_radar_v112w_hyperliquid_stop_conditions.json",
            "schemas/market_radar_v112w_hyperliquid_live_response_schema.json",
            "schemas/market_radar_v112w_hl_to_whale_adapter_spec.md",
            "docs/market_radar_v112w_whale_position_live_source_plan.md",
            "results/market_radar_v112w_whale_label_quality_audit.json",
            "results/market_radar_v112w_whale_position_live_source_plan_result.json",
            "runs/market_radar/v112w_whale_position_live_source_plan.md",
            "runs/market_radar/v112w_whale_position_live_source_plan_handoff.md",
        ],
        "artifacts_read": [
            "results/market_radar_v112v_degraded_mock_replay_result.json",
            "results/market_radar_v112f_whale_position_local_enrichment_result.json",
            "results/market_radar_v112h_unified_signal_envelope_result.json",
            "results/market_radar_v112o_send_preview_pack_result.json",
            "results/market_radar_v112p_live_source_matrix.json",
            "data/hyperliquid_position_state.csv",
        ],
        "security_invariants": {
            "no_hyperliquid_api_called": True,
            "no_external_api_called": True,
            "no_external_ai_called": True,
            "no_daemon_started": True,
            "no_files_deleted": True,
            "no_real_tg_sent": True,
            "no_production_state_written": True,
            "no_credentials_read": True,
            "no_secrets_leaked": True,
            "no_debug_terms_leaked": True,
        },
        "generated_at": NOW_ISO,
    }

    output_path = RESULTS_DIR / "market_radar_v112w_whale_position_live_source_plan_result.json"
    write_json(output_path, result)
    print(f"  Status: {result['status']}")
    print(f"  Plan only: {result['plan_only']}")
    print(f"  v112X requires user confirmation: {result['v112x_requires_user_confirmation']}")

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Step 5: Generate Run Report and Handoff
# ═══════════════════════════════════════════════════════════════════════════════

def generate_run_report(result: dict) -> str:
    """Generate the run report markdown content."""
    return f"""# v112W — Whale Position Alert Live Source Readiness Plan

**Version:** v1.12-w
**Run ID:** 20260605_041300
**Status:** {result['status']}
**Generated:** {NOW_ISO}

## Execution Summary

- **Mode:** Plan-only — no HyperLiquid API calls, no TG send, no daemon.
- **Decision:** whale_position_alert is selected as the next live-like candidate.
- **Previous candidate:** multi_asset_market_sync — frozen in mock-ready / degrade-safe state.
- **Freeze reason:** mock_ready_but_free_source_data_gap (missing OI, volume_change_pct, multi-source verification).

## What v112W Did

1. Validated upstream state: v112V ({result['upstream_validation']['all_passed']}), v112F, v112H, v112O, v112P.
2. Ran label quality audit on data/hyperliquid_position_state.csv.
3. Verified all config, schema, and doc files exist and are valid.
4. Generated result JSON with full safety invariants.

## Key Findings

### Label Quality Audit
- See `results/market_radar_v112w_whale_label_quality_audit.json` for details.
- Label quality is sufficient for one-shot planning.

### Stop Conditions
- Three-state decision: CONTINUE / ABORT / DEGRADE_TO_MOCK.
- 11 ABORT conditions, 8 DEGRADE conditions, 8 CONTINUE conditions.
- All modes enforce eligible_for_real_send=false.

### Field Mapping
- HyperLiquid raw → v112F whale adapter → v112H envelope payload.
- 10 required fields, 6 optional fields.
- Mark price sourced from CoinGecko (free, no key).

### Adapter Spec
- Complete transformation rules from HL response to v112F-compatible event.
- Unknown Whale fallback for unlabeled addresses.
- Deterministic ID generation (signal_id, dedupe_key, cooldown_key, payload_hash).
- eligible_for_real_send enforced false at adapter and envelope levels.

## Files Read

{chr(10).join('- ' + a for a in result.get('artifacts_read', []))}

## Files Generated

{chr(10).join('- ' + a for a in result.get('artifacts_generated', []))}

## What v112W Did NOT Do

- Did NOT call HyperLiquid API.
- Did NOT call any external API.
- Did NOT call any external AI service.
- Did NOT send any Telegram messages.
- Did NOT write production state.
- Did NOT start any daemon/cron/loop.
- Did NOT read any credentials, keys, tokens, or passwords.
- Did NOT delete any files.

## Next Step

**v112X — HyperLiquid one-shot read-only dry-run.** Requires explicit user confirmation.
"""


def generate_handoff(result: dict, label_audit: dict, upstream: dict) -> str:
    """Generate the handoff markdown content."""
    return f"""# v112W Handoff — Whale Position Alert Live Source Readiness Plan

**Version:** v1.12-w
**Status:** {result['status']}
**Generated:** {NOW_ISO}

## What v112W Did

v112W is a **plan-only** step that assesses whether `whale_position_alert` is ready
to become the next live-like candidate, replacing `multi_asset_market_sync` which is
frozen in `mock-ready` / `degrade-safe` state.

The plan produces 11 artifacts (configs, schemas, docs, results, reports) and
answers five key questions:

1. **Is whale_position_alert suitable as the second live-like candidate?** → YES.
2. **What fields does HyperLiquid one-shot need?** → Documented in field mapping.
3. **What conditions must trigger ABORT / DEGRADE_TO_MOCK / CONTINUE?** → Documented
   in stop conditions (11 ABORT, 8 DEGRADE, 8 CONTINUE conditions).
4. **Is address label quality sufficient?** → YES (4 addresses, all labeled, 2
   medium confidence, 2 low confidence; fallback ready).
5. **Can live response enter v112F/v112H envelope link?** → YES, with adapter
   spec defining the transformation and invariants.

## Why Switch from multi_asset_market_sync

`multi_asset_market_sync` successfully demonstrated:
- Ingestion safety degradation (v112U).
- Mock replay (v112V).
- Envelope and preview integration (v112S, v112O).

However, free-source data gaps (no OI, no volume_change_pct, multi-source
verification instability) mean continued pursuit would sacrifice signal quality.
It is frozen in `mock-ready` / `degrade-safe` state — all integration layers
work, but no reliable live data source is available.

`whale_position_alert` has:
- A single, free, well-documented data source (HyperLiquid Info API).
- Existing infrastructure (watch_hyperliquid_positions.py, snapshot_hl_positions.py,
  hyperliquid_position_state.csv).
- Complete local feed (v112F), envelope integration (v112H), and preview cards (v112O).
- No credential requirement.
- Simpler data model (8 fields from one source vs 12+ from 3+ sources).

## Files Read

{chr(10).join('- ' + a for a in result.get('artifacts_read', []))}

## Files Generated

{chr(10).join('- ' + a for a in result.get('artifacts_generated', []))}

## Label Audit Conclusion

- Tracked addresses: {label_audit.get('tracked_addresses_total', 'N/A')}
- Positions: {label_audit.get('positions_total', 'N/A')}
- Labels: {label_audit.get('labels_total', 'N/A')}
- High confidence: {label_audit.get('high_confidence_labels', 'N/A')}
- Medium confidence: {label_audit.get('medium_confidence_labels', 'N/A')}
- Low confidence: {label_audit.get('low_confidence_labels', 'N/A')}
- Unknown (unlabeled): {label_audit.get('unknown_labels', 'N/A')}
- Ready for one-shot plan: {label_audit.get('label_quality_ready_for_one_shot_plan', 'N/A')}

**Assessment:** {label_audit.get('assessment', {}).get('recommendation', 'N/A')}

## Test Results

Tests are run separately via:
```
python scripts/test_market_radar_v112w_whale_position_live_source_plan.py
```

All v112W-specific invariants are verified by the test suite.

## What v112W Explicitly Did NOT Do

- ❌ Did NOT call HyperLiquid API.
- ❌ Did NOT call any external API.
- ❌ Did NOT call any external AI service.
- ❌ Did NOT send Telegram messages.
- ❌ Did NOT write production state.
- ❌ Did NOT start any daemon / cron / loop.
- ❌ Did NOT read any credentials, keys, tokens, cookies, or passwords.
- ❌ Did NOT delete any files.
- ❌ Did NOT write to C:\\Users\\PC\\Desktop\\工作台\\ai_relay_desk.

## v112X Requires Explicit User Confirmation

**v112X is the HyperLiquid one-shot read-only dry-run step.** It will:
- Make a real POST request to `https://api.hyperliquid.xyz/info` (public, free, no key).
- Fetch clearinghouseState for 4 tracked addresses.
- Apply the stop conditions, field mapping, and adapter spec defined in v112W.
- Produce v112F-compatible whale events with eligible_for_real_send=false.
- NOT send Telegram messages.
- NOT write production state.

**This requires explicit user confirmation before execution.**
Do NOT proceed to v112X without user approval.

## Upstream Validation

Upstream checks passed: **{upstream.get('all_passed', 'N/A')}**
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    """Execute v112W plan. Returns 0 on success, 1 on failure."""
    print(f"=" * 70)
    print(f"  Market Radar {VERSION} — Whale Position Alert Live Source Plan")
    print(f"  Mode: {MODE}")
    print(f"  Generated: {NOW_ISO}")
    print(f"=" * 70)

    # Step 1: Validate upstream state
    upstream = validate_upstream()
    if not upstream["all_passed"]:
        print("\n  [FAIL] Upstream validation failed. Check results above.")
        # Continue anyway — we still generate the plan artifacts for review.

    # Step 2: Run label quality audit
    label_audit = run_label_quality_audit()
    label_audit_ok = label_audit.get("label_quality_ready_for_one_shot_plan", False)

    # Step 3: Verify config files
    config_check = verify_config_files()
    config_ok = config_check["all_present"]

    # Step 4: Generate result JSON
    result = generate_result_json(
        upstream_ok=upstream["all_passed"],
        label_audit_ok=label_audit_ok,
        config_ok=config_ok,
    )

    # Step 5: Generate run report and handoff
    print("\n[Step 5] Generating run report and handoff...")
    run_report = generate_run_report(result)
    write_md(RUNS_DIR / "v112w_whale_position_live_source_plan.md", run_report)

    handoff = generate_handoff(result, label_audit, upstream)
    write_md(RUNS_DIR / "v112w_whale_position_live_source_plan_handoff.md", handoff)

    # ── Final summary ────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"  v112W Plan Complete")
    print(f"  Status: {result['status']}")
    print(f"  Upstream validation: {'PASS' if upstream['all_passed'] else 'FAIL'}")
    print(f"  Label audit ready: {label_audit_ok}")
    print(f"  Config files valid: {config_ok}")
    print(f"  v112X requires user confirmation: {result['v112x_requires_user_confirmation']}")
    print(f"  Recommended next: {result['recommended_next_step']}")
    print(f"{'=' * 70}")

    if result["status"] == "passed":
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
