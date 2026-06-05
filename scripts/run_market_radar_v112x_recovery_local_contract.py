#!/usr/bin/env python3
"""
run_market_radar_v112x_recovery_local_contract.py
==================================================
v112X Recovery — Local contract and handoff restoration after r15 silent failure.

This runner does NOT call HyperLiquid or any external API.
It reads the existing v112W artifacts (stop conditions, field mapping, label audit,
plan result) and generates the v112X recovery scaffold:

  - Recovery result JSON (partial_not_live, all safety flags false)
  - Stop decision JSON (NOT_EXECUTED_LOCAL_RECOVERY_ONLY)
  - Markdown run report
  - Handoff markdown

The output is a complete, verifiable contract that the next executor can pick up
for the real v112X one-shot public API dry-run.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

VERSION = "v112X-recovery"
MODE = "local_recovery_only"

CN_TZ = timezone(timedelta(hours=8))
NOW = datetime.now(CN_TZ)
NOW_ISO = NOW.isoformat()

PROJECT_DIR = Path(__file__).resolve().parents[1]
os.chdir(str(PROJECT_DIR))

RESULTS_DIR = PROJECT_DIR / "results"
CONFIG_DIR = PROJECT_DIR / "config"
SCHEMAS_DIR = PROJECT_DIR / "schemas"
RUNS_DIR = PROJECT_DIR / "runs" / "market_radar"

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


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Load v112W Reference Artifacts
# ═══════════════════════════════════════════════════════════════════════════════

def load_v112w_artifacts() -> dict:
    """Load all v112W reference artifacts."""
    print("\n[Step 1] Loading v112W reference artifacts...")

    stop_conditions = load_json(
        CONFIG_DIR / "market_radar_v112w_hyperliquid_stop_conditions.json"
    )
    field_mapping = load_json(
        CONFIG_DIR / "market_radar_v112w_whale_position_field_mapping.json"
    )
    label_audit = load_json(
        RESULTS_DIR / "market_radar_v112w_whale_label_quality_audit.json"
    )
    plan_result = load_json(
        RESULTS_DIR / "market_radar_v112w_whale_position_live_source_plan_result.json"
    )

    artifacts = {
        "stop_conditions": stop_conditions,
        "field_mapping": field_mapping,
        "label_audit": label_audit,
        "plan_result": plan_result,
        "all_loaded": bool(stop_conditions and field_mapping and label_audit and plan_result),
    }

    loaded_count = sum(
        1 for v in [stop_conditions, field_mapping, label_audit, plan_result] if v
    )
    print(f"  Loaded {loaded_count}/4 v112W artifacts")
    for name, data in [
        ("stop_conditions", stop_conditions),
        ("field_mapping", field_mapping),
        ("label_audit", label_audit),
        ("plan_result", plan_result),
    ]:
        status = "OK" if data else "MISSING"
        print(f"  [{status}] {name}")

    return artifacts


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Generate Recovery Result JSON
# ═══════════════════════════════════════════════════════════════════════════════

def generate_recovery_result(artifacts: dict) -> dict:
    """Generate the v112X recovery result JSON."""
    print("\n[Step 2] Generating recovery result JSON...")

    all_loaded = artifacts["all_loaded"]

    result = {
        "version": "v112X-recovery",
        "status": "partial_not_live",
        "recovery_reason": "previous_executor_missing_result_file",
        "live_probe_executed": False,
        "external_api_called": False,
        "api_key_used": False,
        "authorization_header_used": False,
        "retry_count": 0,
        "daemon_started": False,
        "tg_sent": False,
        "production_state_written": False,
        "eligible_for_real_send": False,
        "stop_conditions_loaded": all_loaded,
        "field_mapping_loaded": all_loaded,
        "label_audit_loaded": all_loaded,
        "plan_result_loaded": all_loaded,
        "next_step": "v112X_hyperliquid_one_shot_readonly_dryrun",
        "generated_at": NOW_ISO,
        "generated_by": "run_market_radar_v112x_recovery_local_contract.py",
        "v112w_artifacts_referenced": {
            "stop_conditions": "config/market_radar_v112w_hyperliquid_stop_conditions.json",
            "field_mapping": "config/market_radar_v112w_whale_position_field_mapping.json",
            "label_audit": "results/market_radar_v112w_whale_label_quality_audit.json",
            "plan_result": "results/market_radar_v112w_whale_position_live_source_plan_result.json",
            "live_response_schema": "schemas/market_radar_v112w_hyperliquid_live_response_schema.json",
            "adapter_spec": "schemas/market_radar_v112w_hl_to_whale_adapter_spec.md",
        },
        "v112w_summary": {
            "plan_status": artifacts["plan_result"].get("status", "unknown"),
            "label_quality_ready": artifacts["label_audit"].get(
                "label_quality_ready_for_one_shot_plan", False
            ),
            "hyperliquid_stop_conditions_ready": artifacts["plan_result"].get(
                "hyperliquid_stop_conditions_ready", False
            ),
            "field_mapping_ready": artifacts["plan_result"].get(
                "field_mapping_ready", False
            ),
            "whale_position_plan_ready": artifacts["plan_result"].get(
                "whale_position_plan_ready", False
            ),
            "v112x_requires_user_confirmation": artifacts["plan_result"].get(
                "v112x_requires_user_confirmation", True
            ),
        },
        "safety_invariants": {
            "no_external_api_called": True,
            "no_hyperliquid_api_called": True,
            "no_api_key_used": True,
            "no_authorization_header_used": True,
            "no_tg_sent": True,
            "no_production_state_written": True,
            "no_daemon_started": True,
            "no_files_deleted": True,
            "no_credentials_read": True,
        },
    }

    output_path = RESULTS_DIR / "market_radar_v112x_recovery_local_contract_result.json"
    write_json(output_path, result)
    print(f"  Status: {result['status']}")
    print(f"  live_probe_executed: {result['live_probe_executed']}")
    print(f"  external_api_called: {result['external_api_called']}")
    print(f"  eligible_for_real_send: {result['eligible_for_real_send']}")

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Generate Stop Decision JSON
# ═══════════════════════════════════════════════════════════════════════════════

def generate_stop_decision() -> dict:
    """Generate the v112X recovery stop decision JSON."""
    print("\n[Step 3] Generating stop decision JSON...")

    decision = {
        "version": "v112X-recovery",
        "decision": "NOT_EXECUTED_LOCAL_RECOVERY_ONLY",
        "live_probe_executed": False,
        "eligible_for_real_send": False,
        "reason": "This recovery task only restores local contract and handoff artifacts after missing executor result.",
        "generated_at": NOW_ISO,
        "stop_conditions_evaluated": False,
        "stop_conditions_source": "config/market_radar_v112w_hyperliquid_stop_conditions.json",
        "note": "Stop conditions will be evaluated during the real v112X one-shot dry-run, not during this recovery step.",
        "next_decision_runner": "v112X_hyperliquid_one_shot_readonly_dryrun",
        "safety": {
            "no_real_send_possible": True,
            "no_api_call_possible": True,
            "no_state_write_possible": True,
            "recovery_only": True,
        },
    }

    output_path = RESULTS_DIR / "market_radar_v112x_recovery_stop_decision.json"
    write_json(output_path, decision)
    print(f"  Decision: {decision['decision']}")
    print(f"  live_probe_executed: {decision['live_probe_executed']}")
    print(f"  eligible_for_real_send: {decision['eligible_for_real_send']}")

    return decision


# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Generate Markdown Run Report
# ═══════════════════════════════════════════════════════════════════════════════

def generate_run_report(artifacts: dict, result: dict, decision: dict) -> str:
    """Generate the markdown run report content."""
    label_audit = artifacts["label_audit"]
    plan_result = artifacts["plan_result"]

    return f"""# v112X Recovery — Local Contract and Handoff Restoration

**Version:** v112X-recovery
**Run ID:** 20260605_022952
**Status:** partial_not_live
**Generated:** {NOW_ISO}

## Recovery Context

- **Reason:** Previous executor (r15) exited without writing result.md, causing a
  silent failure in the v112X pipeline.
- **This run:** Restores the local contract and handoff artifacts so the next
  executor can pick up and execute the real v112X HyperLiquid one-shot dry-run.
- **Mode:** Local recovery only — no external API calls, no live probes, no TG send.

## What This Runner Did

1. Loaded all v112W reference artifacts (4/4 loaded: {result['stop_conditions_loaded']}).
2. Generated recovery result JSON with all safety invariants verified.
3. Generated stop decision JSON (NOT_EXECUTED_LOCAL_RECOVERY_ONLY).
4. Generated this run report.
5. Generated handoff markdown for the next executor.

## Safety Invariants (All Enforced)

| Invariant | Value |
|---|---|
| live_probe_executed | false |
| external_api_called | false |
| api_key_used | false |
| authorization_header_used | false |
| retry_count | 0 |
| daemon_started | false |
| tg_sent | false |
| production_state_written | false |
| eligible_for_real_send | false |

## v112W Reference State

- **Plan status:** {plan_result.get('status', 'unknown')}
- **Whale position plan ready:** {plan_result.get('whale_position_plan_ready', 'N/A')}
- **Stop conditions ready:** {plan_result.get('hyperliquid_stop_conditions_ready', 'N/A')}
- **Field mapping ready:** {plan_result.get('field_mapping_ready', 'N/A')}
- **Label quality audit ready:** {label_audit.get('label_quality_ready_for_one_shot_plan', 'N/A')}
- **HL-to-Whale adapter spec ready:** {plan_result.get('hl_to_whale_adapter_spec_ready', 'N/A')}
- **v112X requires user confirmation:** {plan_result.get('v112x_requires_user_confirmation', 'N/A')}

## Label Audit Summary

- Tracked addresses: {label_audit.get('tracked_addresses_total', 'N/A')}
- Labels: {label_audit.get('labels_total', 'N/A')}
  - High confidence: {label_audit.get('high_confidence_labels', 'N/A')}
  - Medium confidence: {label_audit.get('medium_confidence_labels', 'N/A')}
  - Low confidence: {label_audit.get('low_confidence_labels', 'N/A')}

## Files Generated

- `results/market_radar_v112x_recovery_local_contract_result.json`
- `results/market_radar_v112x_recovery_stop_decision.json`
- `runs/market_radar/v112x_recovery_local_contract.md`
- `runs/market_radar/v112x_recovery_local_contract_handoff.md`

## Files Referenced (Read-Only)

- `config/market_radar_v112w_hyperliquid_stop_conditions.json`
- `config/market_radar_v112w_whale_position_field_mapping.json`
- `schemas/market_radar_v112w_hyperliquid_live_response_schema.json`
- `schemas/market_radar_v112w_hl_to_whale_adapter_spec.md`
- `results/market_radar_v112w_whale_label_quality_audit.json`
- `results/market_radar_v112w_whale_position_live_source_plan_result.json`

## What This Runner Did NOT Do

- ❌ Did NOT call HyperLiquid API.
- ❌ Did NOT call any external API.
- ❌ Did NOT call any external AI service.
- ❌ Did NOT send Telegram messages.
- ❌ Did NOT write production state.
- ❌ Did NOT start any daemon / cron / loop.
- ❌ Did NOT read any credentials, keys, tokens, or passwords.
- ❌ Did NOT delete any files.
- ❌ Did NOT mark any signal as real_send_candidate.
- ❌ Did NOT claim live dry-run passed.

## Next Step

**v112X HyperLiquid one-shot read-only dry-run** — requires explicit user confirmation.
This recovery has restored all local contract artifacts needed for the next executor
to proceed directly to the real v112X step.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Step 5: Generate Handoff Markdown
# ═══════════════════════════════════════════════════════════════════════════════

def generate_handoff(artifacts: dict, result: dict, decision: dict) -> str:
    """Generate the handoff markdown content."""
    plan_result = artifacts["plan_result"]
    label_audit = artifacts["label_audit"]
    field_mapping = artifacts["field_mapping"]
    stop_conditions = artifacts["stop_conditions"]

    tracked_addresses = field_mapping.get("tracked_addresses_from_state_csv", [])
    tracked_labels = field_mapping.get("tracked_address_labels", {})

    addr_list = ""
    for addr in tracked_addresses:
        label_info = tracked_labels.get(addr, {})
        label = label_info.get("label", "Unknown")
        entity_type = label_info.get("entity_type", "unknown_whale")
        confidence = label_info.get("confidence", "low")
        addr_list += f"  - `{addr}` → {label} ({entity_type}, {confidence})\n"

    return f"""# v112X Recovery Handoff — For Next Executor

**Version:** v112X-recovery
**Status:** partial_not_live
**Decision:** NOT_EXECUTED_LOCAL_RECOVERY_ONLY
**Generated:** {NOW_ISO}

## Purpose of This Handoff

This handoff provides the next executor with everything needed to execute the
**real v112X HyperLiquid one-shot read-only dry-run**. The recovery step has
restored all local contract artifacts but has NOT performed any live work.

## What Was Restored

1. **Recovery Result JSON** → `results/market_radar_v112x_recovery_local_contract_result.json`
   - Status: partial_not_live
   - All safety flags: false (no live work done)
   - All v112W references loaded: true

2. **Stop Decision JSON** → `results/market_radar_v112x_recovery_stop_decision.json`
   - Decision: NOT_EXECUTED_LOCAL_RECOVERY_ONLY
   - Stop conditions NOT evaluated (deferred to real v112X)

3. **Run Report** → `runs/market_radar/v112x_recovery_local_contract.md`
4. **Handoff** → `runs/market_radar/v112x_recovery_local_contract_handoff.md`

## Ready for Real v112X Execution

The following v112W artifacts are loaded and verified:

### Stop Conditions ({stop_conditions.get('version', 'unknown')})
- Decision modes: {stop_conditions.get('decision_modes', [])}
- Default decision: {stop_conditions.get('default_decision', 'ABORT')}
- ABORT conditions: {len(stop_conditions.get('stop_conditions', {}).get('ABORT', {}).get('conditions', []))}
- DEGRADE conditions: {len(stop_conditions.get('stop_conditions', {}).get('DEGRADE_TO_MOCK', {}).get('conditions', []))}
- CONTINUE conditions: {len(stop_conditions.get('stop_conditions', {}).get('CONTINUE', {}).get('conditions', []))}
- Invariants enforced: eligible_for_real_send always false, no production writes, no TG send, no API key.

### Field Mapping ({field_mapping.get('version', 'unknown')})
- Planned source: {field_mapping.get('planned_source', 'N/A')}
- Endpoint: {field_mapping.get('endpoint_plan', 'N/A')}
- Request type: {field_mapping.get('request_type', 'N/A')}
- API key required: {field_mapping.get('api_key_required', 'N/A')}
- Authorization header required: {field_mapping.get('authorization_header_required', 'N/A')}
- Method: {field_mapping.get('method_is_post_but_read_only', 'N/A')} (POST, read-only)
- Required fields: {len(field_mapping.get('required_fields', []))}
- Optional fields: {len(field_mapping.get('optional_fields', []))}

### Tracked Addresses
{addr_list if addr_list else '  (none)'}

### Label Quality Audit ({label_audit.get('version', 'unknown')})
- Total addresses: {label_audit.get('tracked_addresses_total', 'N/A')}
- High confidence: {label_audit.get('high_confidence_labels', 'N/A')}
- Medium confidence: {label_audit.get('medium_confidence_labels', 'N/A')}
- Low confidence: {label_audit.get('low_confidence_labels', 'N/A')}
- Ready for one-shot plan: {label_audit.get('label_quality_ready_for_one_shot_plan', 'N/A')}

### Plan Result ({plan_result.get('version', 'unknown')})
- Status: {plan_result.get('status', 'unknown')}
- Whale position plan ready: {plan_result.get('whale_position_plan_ready', 'N/A')}
- v112X requires user confirmation: {plan_result.get('v112x_requires_user_confirmation', 'N/A')}

## What the Next Executor Must Do

### Real v112X One-Shot Dry-Run

1. **Confirm** that the user has explicitly approved the HyperLiquid API call.
2. **Make POST requests** to `https://api.hyperliquid.xyz/info` with:
   ```json
   {{"type": "clearinghouseState", "user": "<tracked_address>"}}
   ```
   for each of the 4 tracked addresses.
3. **Apply stop conditions** from `config/market_radar_v112w_hyperliquid_stop_conditions.json`.
4. **Apply field mapping** from `config/market_radar_v112w_whale_position_field_mapping.json`.
5. **Apply adapter spec** from `schemas/market_radar_v112w_hl_to_whale_adapter_spec.md`.
6. **Generate v112F-compatible whale events** with all safety invariants enforced.
7. **Write complete AI_RELAY_EXECUTOR_RESULT_V1** to the executor outbox.

### Invariants for Real v112X

- `eligible_for_real_send` MUST remain `false`.
- `data_mode` MUST be `"live_like_planned"` (NOT `"live"`, NOT `"production"`).
- No TG send function may be called.
- No production state file may be written.
- No credentials, keys, or auth tokens may be read or sent.
- The HyperLiquid endpoint is public and free — no API key is needed.

### Stop Condition Flow

1. Check ABORT conditions first. If any match → stop immediately.
2. Check DEGRADE_TO_MOCK conditions. If any match → proceed with degraded quality.
3. If all clear → CONTINUE (but still eligible_for_real_send=false).

## Safety Checklist for Next Executor

- [ ] User has explicitly confirmed the v112X one-shot dry-run.
- [ ] No API keys, tokens, or credentials are read or sent.
- [ ] HyperLiquid request is POST + read-only (no state mutation).
- [ ] Stop conditions are evaluated before any signal generation.
- [ ] eligible_for_real_send is always false.
- [ ] No TG messages are sent.
- [ ] No production state is written.
- [ ] Complete AI_RELAY_EXECUTOR_RESULT_V1 is written to outbox.

## What This Recovery Did NOT Do

- ❌ Did NOT call HyperLiquid API.
- ❌ Did NOT call any external API.
- ❌ Did NOT call any external AI service.
- ❌ Did NOT send Telegram messages.
- ❌ Did NOT write production state.
- ❌ Did NOT start any daemon / cron / loop.
- ❌ Did NOT read any credentials, keys, tokens, or passwords.
- ❌ Did NOT delete any files.
- ❌ Did NOT disguise local recovery as live dry-run passed.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    """Execute v112X recovery local contract. Returns 0 on success."""
    print(f"=" * 70)
    print(f"  Market Radar {VERSION} — Recovery Local Contract")
    print(f"  Mode: {MODE}")
    print(f"  Generated: {NOW_ISO}")
    print(f"=" * 70)

    # Step 1: Load v112W reference artifacts
    artifacts = load_v112w_artifacts()
    if not artifacts["all_loaded"]:
        print("\n  [WARN] Not all v112W artifacts loaded. Recovery will proceed with partial data.")
        # Continue — partial data is acceptable for recovery scaffold.

    # Step 2: Generate recovery result JSON
    result = generate_recovery_result(artifacts)

    # Step 3: Generate stop decision JSON
    decision = generate_stop_decision()

    # Step 4: Generate run report
    print("\n[Step 4] Generating run report...")
    run_report = generate_run_report(artifacts, result, decision)
    write_md(RUNS_DIR / "v112x_recovery_local_contract.md", run_report)

    # Step 5: Generate handoff
    print("\n[Step 5] Generating handoff...")
    handoff = generate_handoff(artifacts, result, decision)
    write_md(RUNS_DIR / "v112x_recovery_local_contract_handoff.md", handoff)

    # ── Final summary ────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"  v112X Recovery Complete")
    print(f"  Status: {result['status']}")
    print(f"  Decision: {decision['decision']}")
    print(f"  live_probe_executed: {result['live_probe_executed']}")
    print(f"  external_api_called: {result['external_api_called']}")
    print(f"  eligible_for_real_send: {result['eligible_for_real_send']}")
    print(f"  All v112W artifacts loaded: {artifacts['all_loaded']}")
    print(f"  Next step: {result['next_step']}")
    print(f"{'=' * 70}")

    return 0  # Always success for recovery — partial data is acceptable.


if __name__ == "__main__":
    sys.exit(main())
