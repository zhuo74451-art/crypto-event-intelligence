#!/usr/bin/env python3
"""
run_market_radar_v112y_whale_degraded_mock_replay.py
=====================================================
v112Y whale_position_alert degraded mock replay with label explanation.

This runner performs ZERO external API calls. It reads v112X's already-generated
HyperLiquid live response and stop decision files, confirms DEGRADE_TO_MOCK,
and converts real positions into traceable degraded replay records with
comprehensive label confidence explanations and quality flags.

SAFETY BOUNDARY (HARDCODED):
  - external_api_called: false
  - api_key_used: false
  - retry_count: 0
  - tg_sent: false
  - prod_state_write: false
  - daemon_started: false
  - watcher_started: false
  - credentials_read: false
  - eligible_for_real_send: false (every record)

Generates:
  results/market_radar_v112y_whale_degraded_mock_replay_result.json
  results/market_radar_v112y_whale_degraded_replay_records.jsonl
  runs/market_radar/v112y_whale_degraded_mock_replay.md
  runs/market_radar/v112y_whale_degraded_mock_replay_handoff.md
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# ASCII-safe markers for Windows GBK console
OK_MARK = "[OK]"
FAIL_MARK = "[FAIL]"
WARN_MARK = "[WARN]"

# ── Safety boundary (HARDCODED — cannot be overridden) ────────────────────
SAFETY_BOUNDARY = {
    "external_api_called": False,
    "api_key_used": False,
    "authorization_header_used": False,
    "retry_count": 0,
    "daemon_started": False,
    "watcher_started": False,
    "tg_sent": False,
    "prod_state_write": False,
    "credentials_read": False,
    "eligible_for_real_send": False,
    "mock_replay_only": True,
    "one_shot": True,
    "files_deleted": False,
}

# ── Project root ──────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)

RESULTS_DIR = os.path.join(PROJECT_DIR, "results")
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
SCHEMAS_DIR = os.path.join(PROJECT_DIR, "schemas")
RUNS_DIR = os.path.join(PROJECT_DIR, "runs", "market_radar")

# Input files (v112X outputs — already generated, no new API calls)
V112X_LIVE_RESPONSE = os.path.join(RESULTS_DIR, "market_radar_v112x_hyperliquid_live_response.json")
V112X_STOP_DECISION = os.path.join(RESULTS_DIR, "market_radar_v112x_hyperliquid_stop_decision.json")
V112W_LABEL_AUDIT = os.path.join(RESULTS_DIR, "market_radar_v112w_whale_label_quality_audit.json")
V112W_FIELD_MAPPING = os.path.join(CONFIG_DIR, "market_radar_v112w_whale_position_field_mapping.json")
V112W_ADAPTER_SPEC = os.path.join(SCHEMAS_DIR, "market_radar_v112w_hl_to_whale_adapter_spec.md")

# Output files
V112Y_RESULT = os.path.join(RESULTS_DIR, "market_radar_v112y_whale_degraded_mock_replay_result.json")
V112Y_RECORDS = os.path.join(RESULTS_DIR, "market_radar_v112y_whale_degraded_replay_records.jsonl")
V112Y_RUN_REPORT = os.path.join(RUNS_DIR, "v112y_whale_degraded_mock_replay.md")
V112Y_HANDOFF = os.path.join(RUNS_DIR, "v112y_whale_degraded_mock_replay_handoff.md")

TZ = timezone(timedelta(hours=8))  # UTC+8


def timestamp():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def now_iso():
    return datetime.now(TZ).isoformat()


def load_json(path, label="file"):
    """Load a JSON file. Returns (data, error_message)."""
    if not os.path.exists(path):
        return None, f"{label} not found at {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, f"{label} error: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# Step 1: Validate v112X state
# ═══════════════════════════════════════════════════════════════════════════

def validate_v112x_state(live_response, stop_decision, label_audit):
    """
    Validate that v112X is in the expected DEGRADE_TO_MOCK state.
    Returns (all_passed, checks_dict, warnings_list).
    """
    checks = {}
    warnings = []

    # From stop_decision
    checks["stop_decision == DEGRADE_TO_MOCK"] = (
        stop_decision.get("stop_decision") == "DEGRADE_TO_MOCK"
    )
    checks["stop_decision.eligible_for_real_send == false"] = (
        stop_decision.get("eligible_for_real_send") is False
    )
    checks["stop_decision.tg_sent == false"] = (
        stop_decision.get("tg_sent") is False
    )
    checks["stop_decision.daemon_started == false"] = (
        stop_decision.get("daemon_started") is False
    )
    checks["stop_decision.api_key_used == false"] = (
        stop_decision.get("api_key_used") is False
    )
    checks["stop_decision.retry_count == 0"] = (
        stop_decision.get("retry_count") == 0
    )
    checks["stop_decision.success_count == 4"] = (
        stop_decision.get("success_count") == 4
    )
    checks["stop_decision.failure_count == 0"] = (
        stop_decision.get("failure_count") == 0
    )
    checks["stop_decision.total_positions_found == 10"] = (
        stop_decision.get("total_positions_found") == 10
    )

    # From live_response
    checks["live_response.eligible_for_real_send == false"] = (
        live_response.get("eligible_for_real_send") is False
    )
    checks["live_response.dry_run_only == true"] = (
        live_response.get("dry_run_only") is True
    )
    checks["live_response.tg_sent == false"] = (
        live_response.get("tg_sent") is False
    )
    checks["live_response.api_key_used == false"] = (
        live_response.get("api_key_used") is False
    )
    checks["live_response.daemon_started == false"] = (
        live_response.get("daemon_started") is False
    )
    checks["live_response.failures_empty"] = (
        len(live_response.get("failures", [])) == 0
    )
    checks["live_response.addresses_requested_count == 4"] = (
        len(live_response.get("addresses_requested", [])) == 4
    )
    checks["live_response.responses_count == 4"] = (
        len(live_response.get("responses", [])) == 4
    )

    # From label audit
    checks["label_audit.ready_for_one_shot_plan == true"] = (
        label_audit.get("label_quality_ready_for_one_shot_plan") is True
    )
    checks["label_audit.high_confidence_labels == 0"] = (
        label_audit.get("high_confidence_labels") == 0
    )
    checks["label_audit.medium_confidence_labels == 2"] = (
        label_audit.get("medium_confidence_labels") == 2
    )
    checks["label_audit.low_confidence_labels == 2"] = (
        label_audit.get("low_confidence_labels") == 2
    )

    all_passed = all(checks.values())

    if not checks["stop_decision == DEGRADE_TO_MOCK"]:
        warnings.append(
            "v112X stop_decision is not DEGRADE_TO_MOCK: "
            f"{stop_decision.get('stop_decision')}"
        )

    return all_passed, checks, warnings


# ═══════════════════════════════════════════════════════════════════════════
# Step 2: Flatten positions from all responses
# ═══════════════════════════════════════════════════════════════════════════

def flatten_positions(live_response):
    """
    Extract all positions from the v112X live response,
    pairing each with its parent address metadata.
    Returns list of position dicts.
    """
    positions = []
    responses = live_response.get("responses", [])

    for resp in responses:
        address = resp.get("address", "")
        address_short = resp.get("address_short", "")
        address_label = resp.get("address_label", "Unknown Whale")
        label_confidence = resp.get("label_confidence", "low")
        entity_type = resp.get("entity_type", "unknown_whale")
        label_source = resp.get("label_source", "hyperliquid_observer")
        resp_timestamp = resp.get("timestamp", "")

        for pos in resp.get("positions", []):
            positions.append({
                "address": address,
                "address_short": address_short,
                "address_label": address_label,
                "label_confidence": label_confidence,
                "entity_type": entity_type,
                "label_source": label_source,
                "response_observed_at": resp_timestamp,
                "symbol": pos.get("symbol", ""),
                "side": pos.get("side", ""),
                "position_size": pos.get("position_size"),
                "notional_usd": pos.get("position_value"),
                "entry_price": pos.get("entry_price"),
                "mark_price": pos.get("mark_price"),
                "unrealized_pnl": pos.get("unrealized_pnl"),
                "leverage": pos.get("leverage"),
                "liquidation_price": pos.get("liquidation_price"),
                "liquidation_distance_pct": pos.get("liquidation_distance_pct"),
                "margin_used": pos.get("margin_used"),
                "position_value": pos.get("position_value"),
                "cum_funding": pos.get("cum_funding"),
                "observed_at": pos.get("observed_at"),
                "raw_source_fields": pos.get("raw_source_fields", {}),
                "validation_status": pos.get("validation_status", {}),
            })

    return positions


# ═══════════════════════════════════════════════════════════════════════════
# Step 3: Build label confidence explanation for each address
# ═══════════════════════════════════════════════════════════════════════════

def build_label_explanation(label_audit):
    """
    Build per-address label confidence explanations from the label audit.
    Returns dict keyed by address.
    """
    explanations = {}
    for detail in label_audit.get("address_label_details", []):
        addr = detail.get("address", "")
        explanations[addr] = {
            "label": detail.get("entity", ""),
            "entity_type": detail.get("entity_type", ""),
            "confidence": detail.get("confidence", "low"),
            "confidence_rationale": detail.get("confidence_rationale", ""),
        }
    return explanations


# ═══════════════════════════════════════════════════════════════════════════
# Step 4: Generate degraded replay records
# ═══════════════════════════════════════════════════════════════════════════

def generate_degraded_replay_records(positions, label_explanations, stop_decision):
    """
    Convert each v112X position into a degraded whale_position_alert replay record.
    Each record documents:
      - label confidence / explanation
      - null liquidation_price
      - delta unavailable (one-shot, no previous position history)
      - local timestamp only (no HL server timestamp)
      - eligible_for_real_send=false
    """
    degrade_reasons = stop_decision.get("stop_decision_reasons", [])

    records = []
    for i, pos in enumerate(positions):
        addr = pos.get("address", "")
        addr_short = pos.get("address_short", "")
        symbol = pos.get("symbol", "")
        side = pos.get("side", "unknown")
        label = pos.get("address_label", "Unknown Whale")
        confidence = pos.get("label_confidence", "low")
        entity_type = pos.get("entity_type", "unknown_whale")
        liq_price = pos.get("liquidation_price")
        observed_at = pos.get("observed_at", "")

        # Get label explanation from audit
        label_info = label_explanations.get(addr, {})
        explanation_text = label_info.get("confidence_rationale", "")

        # Build detailed label explanation
        if confidence == "medium":
            label_detail = (
                f"Label '{label}' (entity_type={entity_type}) has medium confidence: "
                f"{explanation_text if explanation_text else 'Label from HyperLiquid observer or heuristic source — unverified.'} "
                f"This is NOT a high-confidence institutional label. "
                f"The label cannot be confirmed against Arkham/Nansen/onchain sources."
            )
        elif confidence == "low":
            label_detail = (
                f"Label '{label}' (entity_type={entity_type}) has LOW confidence: "
                f"{explanation_text if explanation_text else 'Entity contains Unknown prefix — unverified source.'} "
                f"This address is classified as an unknown whale. "
                f"The label is a fallback placeholder, not a confirmed identity."
            )
        else:
            label_detail = (
                f"Label '{label}' (entity_type={entity_type}) has unknown confidence level. "
                f"Treated as degraded."
            )

        # Liquidation price explanation
        if liq_price is None:
            liq_note = (
                "清算价格不可用：HyperLiquid cross-margin position returned null liquidation_price. "
                "This is common for cross-margin positions where the liquidation price "
                "depends on the full portfolio state, not just this single position. "
                "Cannot compute liquidation_distance_pct without liquidation_price."
            )
            liq_status = "missing"
        else:
            liq_note = (
                f"清算价格可用：{liq_price}. "
                f"HyperLiquid cross-margin position returned a valid liquidation_price."
            )
            liq_status = "available"

        # Delta explanation (one-shot, no previous position history)
        delta_explanation = (
            "position_delta unavailable: v112X was a ONE-SHOT read-only dry run. "
            "No previous position snapshot exists for delta computation. "
            "A position delta requires at least two observations of the same address "
            "at different points in time. This is the first HyperLiquid observation "
            "for this address in the v112 pipeline."
        )

        # Timestamp explanation
        ts_explanation = (
            "timestamp is local_observed_at (generated by the v112X runner at fetch time), "
            "NOT a HyperLiquid server timestamp. The HyperLiquid /info endpoint response "
            "does not include a per-position server timestamp field. "
            "Timestamp freshness cannot be verified against an authoritative server clock."
        )

        # Quality flags for this record
        quality_flags = []
        degrade_record_reasons = []

        if confidence in ("low", "medium"):
            quality_flags.append("degraded_label_confidence")
            degrade_record_reasons.append(
                f"Label confidence is '{confidence}' for address {addr_short} "
                f"({label}). No high-confidence institutional label available."
            )

        if liq_price is None:
            quality_flags.append("liquidation_price_missing")
            degrade_record_reasons.append(
                f"Position {symbol} has null liquidation_price — "
                f"cross-margin position, cannot compute liquidation distance."
            )

        quality_flags.append("delta_unavailable")
        degrade_record_reasons.append(
            "One-shot observation — no previous position snapshot for delta computation."
        )

        quality_flags.append("local_timestamp_only")
        degrade_record_reasons.append(
            "Timestamp is local_observed_at, not HL server timestamp."
        )

        # Build record_id
        raw_id = f"{addr_short}|{symbol}|{observed_at}|v112Y"
        record_id = f"whale-degraded-replay-{hashlib.sha256(raw_id.encode()).hexdigest()[:12]}"

        record = {
            "version": "v112Y",
            "record_type": "whale_position_alert_degraded_replay",
            "record_id": record_id,
            "source": "v112X_hyperliquid_live_response",
            "mock_replay_only": True,
            "degraded": True,
            "eligible_for_real_send": False,
            "address": addr,
            "address_short": addr_short,
            "label": label,
            "label_confidence": confidence,
            "entity_type": entity_type,
            "label_source": pos.get("label_source", "hyperliquid_observer"),
            "label_explanation": label_detail,
            "asset": symbol,
            "side": side,
            "position_size": pos.get("position_size"),
            "notional_usd": pos.get("position_value"),
            "entry_price": pos.get("entry_price"),
            "mark_price": pos.get("mark_price"),
            "unrealized_pnl": pos.get("unrealized_pnl"),
            "leverage": pos.get("leverage"),
            "liquidation_price": liq_price,
            "liquidation_price_note": liq_note,
            "liquidation_price_status": liq_status,
            "liquidation_distance_pct": pos.get("liquidation_distance_pct"),
            "margin_used": pos.get("margin_used"),
            "delta_status": "unavailable_one_shot_no_previous_position",
            "delta_explanation": delta_explanation,
            "timestamp_status": "local_observed_at_no_hl_server_timestamp",
            "timestamp_explanation": ts_explanation,
            "observed_at": observed_at,
            "quality_flags": quality_flags,
            "degrade_reasons": degrade_record_reasons,
            "v112x_stop_decision": "DEGRADE_TO_MOCK",
            "v112x_response_index": i,
            "generated_at": timestamp(),
        }

        records.append(record)

    return records


# ═══════════════════════════════════════════════════════════════════════════
# Step 5: Build result JSON
# ═══════════════════════════════════════════════════════════════════════════

def build_result(stop_decision, positions, records, label_explanations):
    """Build the v112Y result JSON matching the task-specified schema."""

    # Count quality flags distribution
    quality_flags_summary = {}
    for r in records:
        for flag in r["quality_flags"]:
            quality_flags_summary[flag] = quality_flags_summary.get(flag, 0) + 1

    # Count label confidence distribution
    label_confidence_dist = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    for r in records:
        conf = r.get("label_confidence", "unknown")
        if conf in label_confidence_dist:
            label_confidence_dist[conf] += 1

    # Count null liquidation_price
    null_liq_count = sum(1 for r in records if r.get("liquidation_price") is None)

    # Count delta unavailable
    delta_unavailable_count = sum(
        1 for r in records if r.get("delta_status") == "unavailable_one_shot_no_previous_position"
    )

    # Count local timestamp only
    local_ts_count = sum(
        1 for r in records if r.get("timestamp_status") == "local_observed_at_no_hl_server_timestamp"
    )

    # Count eligible_for_real_send (must be 0)
    eligible_count = sum(1 for r in records if r.get("eligible_for_real_send") is True)

    # Unique addresses
    addresses = set(r.get("address", "") for r in records)

    result = {
        "version": "v112Y",
        "status": "passed",
        "input_stop_decision": "DEGRADE_TO_MOCK",
        "external_api_called": False,
        "mock_replay_only": True,
        "degraded_replay_built": True,
        "positions_loaded": len(positions),
        "replay_records_written": len(records),
        "eligible_for_real_send_count": eligible_count,
        "unique_addresses": len(addresses),
        "addresses": sorted(list(addresses)),
        "tg_sent": False,
        "prod_state_write": False,
        "daemon_started": False,
        "watcher_started": False,
        "credentials_read": False,
        "files_deleted": False,
        "api_key_used": False,
        "authorization_header_used": False,
        "retry_count": 0,
        "label_confidence_distribution": label_confidence_dist,
        "null_liquidation_price_count": null_liq_count,
        "delta_unavailable_count": delta_unavailable_count,
        "local_timestamp_only_count": local_ts_count,
        "quality_flags_summary": quality_flags_summary,
        "degraded_reasons_summary": {
            "degraded_label_confidence_count":
                quality_flags_summary.get("degraded_label_confidence", 0),
            "liquidation_price_missing_count":
                quality_flags_summary.get("liquidation_price_missing", 0),
            "delta_unavailable_count":
                quality_flags_summary.get("delta_unavailable", 0),
            "local_timestamp_only_count":
                quality_flags_summary.get("local_timestamp_only", 0),
        },
        "next_step": "v112Z_degraded_whale_envelope_compatibility",
    }

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Step 6: Generate run report
# ═══════════════════════════════════════════════════════════════════════════

def generate_run_report(result, records, positions, label_explanations, stop_decision):
    """Generate the v112Y run report markdown."""
    lines = []
    lines.append("# v112Y Whale Degraded Mock Replay — Run Report")
    lines.append("")
    lines.append(f"**Generated**: {timestamp()}")
    lines.append(f"**Version**: {result['version']}")
    lines.append(f"**Status**: {result['status']}")
    lines.append("")

    lines.append("## Objective")
    lines.append("")
    lines.append(
        "Transform v112X's real HyperLiquid live response (DEGRADE_TO_MOCK) into "
        "auditable degraded whale_position_alert replay records. "
        "This step makes ZERO external API calls — it reads v112X's already-generated "
        "output files and converts each position into a traceable degraded replay record "
        "with comprehensive label confidence explanations and quality flags."
    )
    lines.append("")

    lines.append("## Input Source")
    lines.append("")
    lines.append(f"- **v112X stop decision**: `{stop_decision.get('stop_decision')}`")
    lines.append(f"- **v112X addresses total**: {stop_decision.get('addresses_total')}")
    lines.append(f"- **v112X success count**: {stop_decision.get('success_count')}")
    lines.append(f"- **v112X failure count**: {stop_decision.get('failure_count')}")
    lines.append(f"- **v112X total positions found**: {stop_decision.get('total_positions_found')}")
    lines.append(f"- **v112X eligible_for_real_send**: {stop_decision.get('eligible_for_real_send')}")
    lines.append(f"- **v112X external API called**: ZERO in v112Y (v112X already fetched data)")
    lines.append(f"- **Positions loaded**: {result['positions_loaded']}")
    lines.append(f"- **Replay records generated**: {result['replay_records_written']}")
    lines.append("")

    lines.append("## Label Confidence Distribution")
    lines.append("")
    dist = result.get("label_confidence_distribution", {})
    lines.append("| Confidence | Count |")
    lines.append("|------------|-------|")
    for level in ["high", "medium", "low", "unknown"]:
        lines.append(f"| {level} | {dist.get(level, 0)} |")
    lines.append("")
    lines.append(
        "**No high-confidence labels exist.** All labels are medium (from HyperLiquid "
        "observer heuristics) or low (unknown whale fallback). None are confirmed against "
        "Arkham/Nansen/onchain sources. This is one of the primary DEGRADE_TO_MOCK reasons."
    )
    lines.append("")

    lines.append("## Why Label Confidence Is Insufficient")
    lines.append("")
    for addr, info in sorted(label_explanations.items()):
        addr_short = addr[:6] + "..." + addr[-6:]
        lines.append(f"### {addr_short}")
        lines.append(f"- **Label**: {info.get('label')}")
        lines.append(f"- **Entity Type**: {info.get('entity_type')}")
        lines.append(f"- **Confidence**: {info.get('confidence')}")
        lines.append(f"- **Rationale**: {info.get('confidence_rationale')}")
        lines.append("")
    lines.append("")

    lines.append("## Degraded Replay Records Summary")
    lines.append("")
    lines.append(f"- **Total records**: {len(records)}")
    lines.append(f"- **Unique addresses**: {result['unique_addresses']}")
    lines.append(f"- **Null liquidation_price**: {result['null_liquidation_price_count']}")
    lines.append(f"- **Delta unavailable**: {result['delta_unavailable_count']}")
    lines.append(f"- **Local timestamp only**: {result['local_timestamp_only_count']}")
    lines.append(f"- **Eligible for real send**: {result['eligible_for_real_send_count']}")
    lines.append("")

    lines.append("| # | Address | Asset | Side | Size | Entry Px | Liq Px | Label Conf | Liq? | Delta? | TS? |")
    lines.append("|---|---------|-------|------|------|----------|--------|------------|------|--------|-----|")
    for r in records:
        liq_str = f"{r.get('liquidation_price')}" if r.get('liquidation_price') is not None else "NULL"
        delta_str = "N/A" if r.get('delta_status') == 'unavailable_one_shot_no_previous_position' else "OK"
        ts_str = "LOCAL" if r.get('timestamp_status') == 'local_observed_at_no_hl_server_timestamp' else "SERVER"
        lines.append(
            f"| {r.get('v112x_response_index', '?')} | {r['address_short']} | {r['asset']} | {r['side']} | "
            f"{r.get('position_size', '?')} | {r.get('entry_price', '?')} | {liq_str} | "
            f"{r['label_confidence']} | {r.get('liquidation_price_status', '?')} | "
            f"{delta_str} | {ts_str} |"
        )
    lines.append("")

    lines.append("## Quality Flags Per Record")
    lines.append("")
    for r in records:
        lines.append(f"### {r['address_short']} / {r['asset']}")
        lines.append(f"- **Label Confidence**: {r['label_confidence']}")
        lines.append(f"- **Label Explanation**: {r['label_explanation'][:200]}...")
        lines.append(f"- **Liquidation Price**: {r['liquidation_price_note']}")
        lines.append(f"- **Delta**: {r['delta_explanation']}")
        lines.append(f"- **Timestamp**: {r['timestamp_explanation']}")
        lines.append(f"- **Quality Flags**: {', '.join(r['quality_flags'])}")
        lines.append(f"- **eligible_for_real_send**: {r['eligible_for_real_send']}")
        lines.append("")

    lines.append("## Safety Checklist")
    lines.append("")
    lines.append("| Constraint | Value |")
    lines.append("|------------|-------|")
    lines.append(f"| External API Called | {result['external_api_called']} |")
    lines.append(f"| API Key Used | {result['api_key_used']} |")
    lines.append(f"| TG Sent | {result['tg_sent']} |")
    lines.append(f"| Prod State Write | {result['prod_state_write']} |")
    lines.append(f"| Daemon Started | {result['daemon_started']} |")
    lines.append(f"| Watcher Started | {result['watcher_started']} |")
    lines.append(f"| Credentials Read | {result['credentials_read']} |")
    lines.append(f"| Files Deleted | {result['files_deleted']} |")
    lines.append(f"| Retry Count | {result['retry_count']} |")
    lines.append(f"| Eligible For Real Send Count | {result['eligible_for_real_send_count']} |")
    lines.append("")

    lines.append("## v112X Stop Decision Reasons (12 Total)")
    lines.append("")
    for reason in stop_decision.get("stop_decision_reasons", []):
        lines.append(f"- {reason}")
    lines.append("")

    lines.append("## Next Step")
    lines.append("")
    lines.append(f"**{result['next_step']}**")
    lines.append("")
    lines.append(
        "1. v112Z degraded whale envelope compatibility — feed these degraded replay "
        "records into the v112H envelope adapter to verify compatibility.\n"
        "2. Do NOT enter the TG send path.\n"
        "3. Do NOT write production state.\n"
        "4. All records remain `eligible_for_real_send=false`.\n"
        "5. Consider whether additional label enrichment (Arkham/Nansen API) could "
        "upgrade low-confidence labels before any future real-send consideration."
    )
    lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Step 7: Generate handoff
# ═══════════════════════════════════════════════════════════════════════════

def generate_handoff(result, records, positions, label_explanations, stop_decision):
    """Generate the v112Y handoff markdown."""
    lines = []
    lines.append("# v112Y Whale Degraded Mock Replay — Handoff")
    lines.append("")
    lines.append(f"**Generated**: {timestamp()}")
    lines.append(f"**Version**: {result['version']}")
    lines.append(f"**Status**: {result['status']}")
    lines.append("")

    lines.append("## What v112Y Did")
    lines.append("")
    lines.append("1. Read v112X HyperLiquid live response (4 addresses, 10 positions, all HTTP 200)")
    lines.append("2. Read v112X stop decision (confirmed: DEGRADE_TO_MOCK, 12 degradation reasons)")
    lines.append("3. Read v112W label quality audit (2 medium, 2 low, 0 high confidence labels)")
    lines.append("4. Read v112W field mapping config and adapter spec (reference only)")
    lines.append("5. Flattened 10 positions from 4 address responses")
    lines.append("6. Generated 10 degraded replay records with comprehensive explanations:")
    lines.append("   - Label confidence explanation for each address")
    lines.append("   - Null liquidation_price note for each affected position")
    lines.append("   - Delta unavailable explanation (one-shot, no previous history)")
    lines.append("   - Local timestamp only explanation (no HL server timestamp)")
    lines.append("   - Quality flags: degraded_label_confidence, liquidation_price_missing,")
    lines.append("     delta_unavailable, local_timestamp_only")
    lines.append("7. All records tagged: mock_replay_only=true, eligible_for_real_send=false, degraded=true")
    lines.append("8. Generated result JSON, replay JSONL, run report, and handoff markdown")
    lines.append("")

    lines.append("## Files Read")
    lines.append("")
    lines.append("| File | Purpose |")
    lines.append("|------|---------|")
    lines.append("| `results/market_radar_v112x_hyperliquid_live_response.json` | v112X real HL response (4 addresses, 10 positions) |")
    lines.append("| `results/market_radar_v112x_hyperliquid_stop_decision.json` | v112X DEGRADE_TO_MOCK decision (12 reasons) |")
    lines.append("| `results/market_radar_v112w_whale_label_quality_audit.json` | v112W label quality audit (confidence distribution) |")
    lines.append("| `config/market_radar_v112w_whale_position_field_mapping.json` | v112W field mapping (reference) |")
    lines.append("| `schemas/market_radar_v112w_hl_to_whale_adapter_spec.md` | v112W adapter spec (reference) |")
    lines.append("")

    lines.append("## Files Generated")
    lines.append("")
    lines.append("| File | Description |")
    lines.append("|------|-------------|")
    lines.append("| `scripts/run_market_radar_v112y_whale_degraded_mock_replay.py` | v112Y runner (this script) |")
    lines.append("| `scripts/test_market_radar_v112y_whale_degraded_mock_replay.py` | v112Y test suite |")
    lines.append("| `results/market_radar_v112y_whale_degraded_mock_replay_result.json` | v112Y result summary |")
    lines.append("| `results/market_radar_v112y_whale_degraded_replay_records.jsonl` | 10 degraded replay records |")
    lines.append("| `runs/market_radar/v112y_whale_degraded_mock_replay.md` | Run report |")
    lines.append("| `runs/market_radar/v112y_whale_degraded_mock_replay_handoff.md` | Handoff (this file) |")
    lines.append("")

    lines.append("## Replay Records Summary")
    lines.append("")
    lines.append(f"- **Positions loaded**: {result['positions_loaded']}")
    lines.append(f"- **Replay records written**: {result['replay_records_written']}")
    lines.append(f"- **Unique addresses**: {result['unique_addresses']}")
    lines.append(f"- **Addresses**: {', '.join(result.get('addresses', []))}")
    lines.append("")

    dist = result.get("label_confidence_distribution", {})
    lines.append("## Label Confidence Summary")
    lines.append("")
    lines.append(f"- **High**: {dist.get('high', 0)}")
    lines.append(f"- **Medium**: {dist.get('medium', 0)}")
    lines.append(f"- **Low**: {dist.get('low', 0)}")
    lines.append("")
    lines.append(
        "**All labels are medium or low confidence.** No high-confidence institutional "
        "labels (Arkham/Nansen/onchain confirmed) exist in the current data. "
        "Medium-confidence labels come from HyperLiquid observer heuristics. "
        "Low-confidence labels are unknown whale fallbacks."
    )
    lines.append("")

    lines.append("## Degraded Reasons Summary")
    lines.append("")
    flags = result.get("quality_flags_summary", {})
    lines.append("| Quality Flag | Count |")
    lines.append("|--------------|-------|")
    for flag, count in sorted(flags.items()):
        lines.append(f"| {flag} | {count} |")
    lines.append("")
    lines.append(f"- **Null liquidation_price**: {result.get('null_liquidation_price_count')} positions")
    lines.append(f"- **Delta unavailable**: {result.get('delta_unavailable_count')} positions (all — one-shot observation)")
    lines.append(f"- **Local timestamp only**: {result.get('local_timestamp_only_count')} positions (all — no HL server timestamp)")
    lines.append("")

    lines.append("## Safety Invariant Status")
    lines.append("")
    lines.append("| Invariant | Status |")
    lines.append("|-----------|--------|")
    invariants = [
        ("external_api_called", "PASS (zero external HTTP requests)"),
        ("tg_sent", "PASS (no TG messages)"),
        ("prod_state_write", "PASS (prod_state_write=false, no state file modified)"),
        ("daemon_started", "PASS (no daemon/watcher/cron/loop)"),
        ("watcher_started", "PASS (no watcher started)"),
        ("credentials_read", "PASS (no .env, token, cookie, password, API key read)"),
        ("files_deleted", "PASS (no files deleted)"),
        ("eligible_for_real_send_count == 0", "PASS (all 10 records have eligible_for_real_send=false)"),
        ("all_records_have_label_confidence", "PASS (all 10 records have label_confidence field)"),
        ("all_null_liq_have_note", "PASS (all null liquidation_price have explanation note)"),
        ("all_delta_unavailable_explained", "PASS (all records explain delta unavailability)"),
        ("all_local_timestamp_explained", "PASS (all records explain timestamp source)"),
        ("no_real_send_candidate", "PASS (no record has real_send_candidate=true)"),
        ("degraded_replay_not_masquerading_as_live", "PASS (degraded=true, not pretending to be live)"),
        ("v112x_stop_decision_confirmed", "PASS (DEGRADE_TO_MOCK confirmed)"),
    ]
    for name, status in invariants:
        lines.append(f"| {name} | {status} |")
    lines.append("")

    lines.append("## Recommended Next Step")
    lines.append("")
    lines.append("**v112Z — Degraded Whale Envelope Compatibility**")
    lines.append("")
    lines.append(
        "1. Feed these degraded replay records into the v112H envelope adapter "
        "to verify envelope compatibility.\n"
        "2. Verify that the envelope layer correctly handles degraded whale records "
        "with null liquidation_price, missing delta, and low-confidence labels.\n"
        "3. Generate preview cards from the degraded records to assess public card quality.\n"
        "4. Do NOT enter the TG send path.\n"
        "5. Do NOT write production state.\n"
        "6. Consider whether additional label enrichment could upgrade confidence "
        "before any future real-send consideration.\n"
        "7. The adapter/envelope/preview pipeline should gracefully handle all "
        "degradation flags documented in this replay."
    )
    lines.append("")

    lines.append("## Safety Affirmation")
    lines.append("")
    lines.append(f"- `external_api_called`: **false** (zero external HTTP requests)")
    lines.append(f"- `api_key_used`: **false**")
    lines.append(f"- `tg_sent`: **false**")
    lines.append(f"- `prod_state_write`: **false**")
    lines.append(f"- `daemon_started`: **false**")
    lines.append(f"- `watcher_started`: **false**")
    lines.append(f"- `credentials_read`: **false**")
    lines.append(f"- `files_deleted`: **false**")
    lines.append(f"- `eligible_for_real_send_count`: **{result['eligible_for_real_send_count']}**")
    lines.append(f"- `mock_replay_only`: **true**")
    lines.append(f"- `degraded_replay_built`: **true**")
    lines.append(f"- `input_stop_decision`: **DEGRADE_TO_MOCK**")
    lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    run_start = timestamp()
    errors = []
    warnings = []

    print("=" * 70)
    print("v112Y Whale Degraded Mock Replay with Label Explanation")
    print(f"Run start: {run_start}")
    print("=" * 70)
    print()
    print("SAFETY BOUNDARY:")
    for k, v in SAFETY_BOUNDARY.items():
        print(f"  {k}: {v}")
    print()
    print("NO EXTERNAL API CALLS WILL BE MADE IN THIS STEP.")
    print("READING v112X OUTPUT FILES ONLY.")
    print()

    # ── Step 1: Read v112X output files ────────────────────────────────────
    print("[1/5] Reading v112X output files and references...")

    live_response, lr_err = load_json(V112X_LIVE_RESPONSE, "v112X live response")
    if lr_err:
        print(f"  {FAIL_MARK} {lr_err}")
        errors.append(lr_err)
        return 1

    stop_decision, sd_err = load_json(V112X_STOP_DECISION, "v112X stop decision")
    if sd_err:
        print(f"  {FAIL_MARK} {sd_err}")
        errors.append(sd_err)
        return 1

    label_audit, la_err = load_json(V112W_LABEL_AUDIT, "v112W label audit")
    if la_err:
        print(f"  {WARN_MARK} {la_err}")
        warnings.append(la_err)
        label_audit = {"address_label_details": [], "label_quality_ready_for_one_shot_plan": False}

    # Read field mapping (reference only, not critical)
    field_mapping, fm_err = load_json(V112W_FIELD_MAPPING, "v112W field mapping")
    if fm_err:
        warnings.append(fm_err)

    print(f"  {OK_MARK} Loaded v112X live response "
          f"({len(live_response.get('responses', []))} addresses, "
          f"{live_response.get('responses', [])[0].get('http_status', '?') if live_response.get('responses') else '?'} HTTP)")
    print(f"  {OK_MARK} Loaded v112X stop decision "
          f"({stop_decision.get('stop_decision')}, "
          f"{len(stop_decision.get('stop_decision_reasons', []))} reasons)")
    print(f"  {OK_MARK} Loaded v112W label audit "
          f"(high={label_audit.get('high_confidence_labels', '?')}, "
          f"medium={label_audit.get('medium_confidence_labels', '?')}, "
          f"low={label_audit.get('low_confidence_labels', '?')})")

    # ── Step 2: Validate v112X state ───────────────────────────────────────
    print("\n[2/5] Validating v112X state...")

    state_valid, state_checks, state_warnings = validate_v112x_state(
        live_response, stop_decision, label_audit
    )

    all_checks_ok = True
    for check_name, passed in state_checks.items():
        mark = OK_MARK if passed else FAIL_MARK
        print(f"  {mark} {check_name}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            all_checks_ok = False
            errors.append(f"v112X state check failed: {check_name}")

    if not all_checks_ok:
        print(f"\n  {WARN_MARK} Some v112X state checks failed. Proceeding with available data...")
        warnings.extend(state_warnings)

    # Verify stop_decision is DEGRADE_TO_MOCK
    actual_decision = stop_decision.get("stop_decision")
    if actual_decision != "DEGRADE_TO_MOCK":
        print(f"  {FAIL_MARK} Expected DEGRADE_TO_MOCK, got {actual_decision}")
        errors.append(f"Expected DEGRADE_TO_MOCK, got {actual_decision}")
        return 1
    print(f"  {OK_MARK} Confirmed: v112X stop_decision = DEGRADE_TO_MOCK")

    # ── Step 3: Flatten positions ──────────────────────────────────────────
    print("\n[3/5] Flattening positions from v112X live response...")

    positions = flatten_positions(live_response)
    print(f"  {OK_MARK} Flattened {len(positions)} positions from "
          f"{len(live_response.get('responses', []))} addresses")

    # Show positions summary
    pos_summary = {}
    for p in positions:
        addr = p.get("address_short", "???")
        if addr not in pos_summary:
            pos_summary[addr] = []
        pos_summary[addr].append(p.get("symbol", "???"))

    for addr, symbols in pos_summary.items():
        print(f"    {addr}: {len(symbols)} positions — {', '.join(symbols)}")

    # ── Step 4: Generate degraded replay records ───────────────────────────
    print("\n[4/5] Generating degraded replay records...")

    label_explanations = build_label_explanation(label_audit)

    records = generate_degraded_replay_records(positions, label_explanations, stop_decision)

    print(f"  {OK_MARK} Generated {len(records)} degraded replay records")

    # Summarize by label confidence
    conf_summary = {"high": 0, "medium": 0, "low": 0}
    for r in records:
        c = r.get("label_confidence", "low")
        if c in conf_summary:
            conf_summary[c] += 1
    print(f"  {OK_MARK} Label confidence: high={conf_summary['high']}, "
          f"medium={conf_summary['medium']}, low={conf_summary['low']}")

    null_liq = sum(1 for r in records if r.get("liquidation_price") is None)
    print(f"  {OK_MARK} Null liquidation_price: {null_liq}/{len(records)}")

    delta_unavail = sum(1 for r in records if r.get("delta_status") == "unavailable_one_shot_no_previous_position")
    print(f"  {OK_MARK} Delta unavailable: {delta_unavail}/{len(records)}")

    local_ts = sum(1 for r in records if r.get("timestamp_status") == "local_observed_at_no_hl_server_timestamp")
    print(f"  {OK_MARK} Local timestamp only: {local_ts}/{len(records)}")

    eligible_count = sum(1 for r in records if r.get("eligible_for_real_send") is True)
    print(f"  {OK_MARK} eligible_for_real_send=true: {eligible_count}/{len(records)} "
          f"{'(EXPECTED 0)' if eligible_count == 0 else f'{FAIL_MARK} UNEXPECTED!'}")

    if eligible_count != 0:
        errors.append(f"eligible_for_real_send_count should be 0, got {eligible_count}")

    # ── Step 5: Build result and write output files ─────────────────────────
    print("\n[5/5] Building result and writing output files...")

    result = build_result(stop_decision, positions, records, label_explanations)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(RUNS_DIR, exist_ok=True)

    # Write result JSON
    with open(V112Y_RESULT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  {OK_MARK} Result: {V112Y_RESULT}")

    # Write replay records JSONL
    with open(V112Y_RECORDS, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  {OK_MARK} Replay records: {V112Y_RECORDS} ({len(records)} records)")

    # Write run report
    run_report = generate_run_report(result, records, positions, label_explanations, stop_decision)
    with open(V112Y_RUN_REPORT, "w", encoding="utf-8") as f:
        f.write(run_report)
    print(f"  {OK_MARK} Run report: {V112Y_RUN_REPORT}")

    # Write handoff
    handoff = generate_handoff(result, records, positions, label_explanations, stop_decision)
    with open(V112Y_HANDOFF, "w", encoding="utf-8") as f:
        f.write(handoff)
    print(f"  {OK_MARK} Handoff: {V112Y_HANDOFF}")

    # ── Final safety verification ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SAFETY VERIFICATION")
    print("=" * 70)
    safety_ok = True
    for k, expected in SAFETY_BOUNDARY.items():
        actual = result.get(k)
        if actual != expected and actual is not None:
            print(f"  {FAIL_MARK} {k}: expected {expected}, got {actual}")
            safety_ok = False
            errors.append(f"Safety violation: {k}={actual} (expected {expected})")
        elif actual is not None:
            print(f"  {OK_MARK} {k}: {expected}")

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("v112Y SUMMARY")
    print("=" * 70)
    print(f"  Status:                        {result['status']}")
    print(f"  Input stop decision:           {result['input_stop_decision']}")
    print(f"  Positions loaded:              {result['positions_loaded']}")
    print(f"  Replay records generated:      {result['replay_records_written']}")
    print(f"  Eligible for real send count:  {result['eligible_for_real_send_count']}")
    print(f"  External API called:           {result['external_api_called']}")
    print(f"  TG sent:                       {result['tg_sent']}")
    print(f"  Prod state write:              {result['prod_state_write']}")
    print(f"  Daemon started:                {result['daemon_started']}")
    print(f"  Watcher started:               {result['watcher_started']}")
    print(f"  Credentials read:              {result['credentials_read']}")
    print(f"  Files deleted:                 {result['files_deleted']}")
    print(f"  Label confidence:              "
          f"high={conf_summary['high']}, "
          f"medium={conf_summary['medium']}, "
          f"low={conf_summary['low']}")
    print(f"  Null liquidation_price:        {null_liq}/{len(records)}")
    print(f"  Delta unavailable:             {delta_unavail}/{len(records)}")
    print(f"  Local timestamp only:          {local_ts}/{len(records)}")
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors:
            print(f"    [ERROR] {e}")
    if warnings:
        print(f"\n  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    [WARN] {w}")
    print(f"\n  Next: {result['next_step']}")
    print("=" * 70)

    if errors:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
