#!/usr/bin/env python3
"""
v115N Whale Manual Audit Operator Action Queue — Local Only
=============================================================
Based on v115M real workflow blocked results, generates an operator action queue
for 4 whale addresses, translating blocked reasons into actionable manual evidence
completion tasks.

This stage produces ONLY an operator action queue:
  - NO real label upgrade
  - NO real send candidate
  - NO TG test group delivery
  - NO external API calls
  - NO credentials read
  - NO production state write

Inputs:
  - results/market_radar_v115m_whale_real_workflow_records.jsonl
  - results/market_radar_v115m_whale_real_workflow_decisions.jsonl
  - results/market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_result.json
  - results/market_radar_v115e_whale_address_audit_evidence_requests.jsonl
  - results/market_radar_v115g_whale_manual_audit_intake_decisions.jsonl
  - results/market_radar_v115l_whale_real_workbook_evidence_scoring_decisions.jsonl
  - config/market_radar_v115k_whale_label_evidence_source_registry.json
  - config/market_radar_v115k_whale_label_evidence_scoring_policy.json
  - runs/market_radar/v115f_whale_address_audit_operator_workbook.csv

Outputs:
  - results/market_radar_v115n_whale_manual_audit_operator_actions.jsonl
  - results/market_radar_v115n_whale_manual_audit_operator_action_queue_result.json
  - runs/market_radar/v115n_whale_manual_audit_operator_action_queue.csv
  - runs/market_radar/v115n_whale_manual_audit_operator_action_queue.md
  - runs/market_radar/v115n_whale_manual_audit_operator_action_queue_local_only_handoff.md
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# ---------------------------------------------------------------------------
# Input paths
# ---------------------------------------------------------------------------
V115M_RECORDS = os.path.join(RESULTS_DIR, "market_radar_v115m_whale_real_workflow_records.jsonl")
V115M_DECISIONS = os.path.join(RESULTS_DIR, "market_radar_v115m_whale_real_workflow_decisions.jsonl")
V115M_GATE_RESULT = os.path.join(RESULTS_DIR, "market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_result.json")
V115E_EVIDENCE_REQUESTS = os.path.join(RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_requests.jsonl")
V115G_INTAKE_DECISIONS = os.path.join(RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_decisions.jsonl")
V115L_SCORING_DECISIONS = os.path.join(RESULTS_DIR, "market_radar_v115l_whale_real_workbook_evidence_scoring_decisions.jsonl")
V115K_REGISTRY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_source_registry.json")
V115K_SCORING_POLICY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy.json")
V115F_WORKBOOK = os.path.join(RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv")

# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------
OUT_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115n_whale_manual_audit_operator_actions.jsonl")
OUT_JSON = os.path.join(RESULTS_DIR, "market_radar_v115n_whale_manual_audit_operator_action_queue_result.json")
OUT_CSV = os.path.join(RUNS_DIR, "v115n_whale_manual_audit_operator_action_queue.csv")
OUT_MD = os.path.join(RUNS_DIR, "v115n_whale_manual_audit_operator_action_queue.md")
OUT_HANDOFF = os.path.join(RUNS_DIR, "v115n_whale_manual_audit_operator_action_queue_local_only_handoff.md")

# ---------------------------------------------------------------------------
# Next gate command order (fixed)
# ---------------------------------------------------------------------------
NEXT_GATE_COMMANDS = [
    "python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py",
    "python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py",
    "python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py",
    "python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py",
]

# ---------------------------------------------------------------------------
# All fields the v115F workbook expects to be filled
# ---------------------------------------------------------------------------
WORKBOOK_OPERATOR_FIELDS = [
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
    "reviewer",
    "reviewed_at",
    "ready_for_upgrade",
]

PRIMARY_SOURCE_TYPE_IDS = [
    "primary_project_official_docs",
    "primary_exchange_institution_label",
    "primary_reputable_explorer_label",
    "primary_signed_statement",
    "primary_internal_verified_label",
]

SECONDARY_SOURCE_TYPE_IDS = [
    "secondary_analytics_dashboard",
    "secondary_cross_source_clustering",
    "secondary_tx_behavior_evidence",
    "secondary_social_identity_linkage",
    "secondary_operator_reviewed_note",
]

ACTIVITY_SOURCE_TYPE_IDS = [
    "activity_counterparty_pattern",
    "activity_asset_venue_pattern",
    "activity_position_consistency",
    "activity_historical_entity_interaction",
]

REJECTED_SOURCE_TYPE_IDS = [
    "rejected_unsourced_social_post",
    "rejected_single_anonymous_claim",
    "rejected_ai_attribution",
    "rejected_screenshot_without_url",
    "rejected_stale_label_no_date",
    "rejected_tg_chat_label",
    "rejected_vague_whale_claim",
]


def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv_dict(path):
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def format_source_types(source_type_ids, registry):
    """Format source type IDs into human-readable labels."""
    labels = []
    categories = registry.get("categories", {})
    for cat_name, cat_data in categories.items():
        for stype in cat_data.get("types", []):
            if stype["type_id"] in source_type_ids:
                labels.append(f"{stype['label']} ({stype['type_id']})")
    return labels


def format_rejected_warning(registry):
    """Generate rejected source warning text."""
    rejected = registry.get("categories", {}).get("rejected_source", {})
    note = rejected.get("automatic_rejection_note", "")
    types = rejected.get("types", [])
    type_labels = [f"  - {t['label']}: {t['rejection_reason']}" for t in types]
    warning = f"{note}\n\nRejected source types to avoid:\n" + "\n".join(type_labels)
    return warning


def build_operator_action(
    address_data,
    v115m_record,
    v115m_decision,
    v115e_request,
    v115g_intake,
    v115l_scoring,
    registry,
    scoring_policy,
    workbook_row_idx,
):
    """Build a single operator action record."""
    address = address_data["address"]
    current_label = address_data["current_label"]
    current_confidence = address_data["current_confidence"]
    target_confidence = address_data.get("target_confidence", "high")

    # Determine action type and priority
    if current_confidence == "low":
        action_type = "manual_attribution_required"
        priority = "high"
    else:
        action_type = "corroboration_required"
        priority = "medium"

    # Blocked stage and reasons
    blocked_stage = v115m_record.get("workflow_stage_blocked", "intake_gate")
    blocked_reasons = v115m_record.get("workflow_block_reasons", [])
    if isinstance(blocked_reasons, list):
        blocked_reasons = "; ".join(blocked_reasons)
    else:
        blocked_reasons = str(blocked_reasons)

    # Missing workbook fields from v115G intake
    missing_fields = v115g_intake.get("missing_fields", [])
    g_block_reasons = v115g_intake.get("block_reasons", [])
    if isinstance(g_block_reasons, list):
        g_block_reasons = "; ".join(g_block_reasons)
    else:
        g_block_reasons = str(g_block_reasons)

    # Recommended source types
    missing_evidence = v115e_request.get("missing_evidence_types", [])
    recommended_primary = PRIMARY_SOURCE_TYPE_IDS
    recommended_secondary = SECONDARY_SOURCE_TYPE_IDS
    recommended_activity = ACTIVITY_SOURCE_TYPE_IDS

    if current_confidence == "low":
        recommended_source_types = {
            "primary": format_source_types(recommended_primary, registry),
            "secondary": format_source_types(recommended_secondary, registry),
            "activity": format_source_types(recommended_activity, registry),
            "note": "For unknown whale: MUST provide trusted primary source + second source/cross-source + activity pattern + operator confirmation. At least one primary_source is required before any upgrade.",
        }
    else:
        recommended_source_types = {
            "primary": format_source_types(recommended_primary, registry),
            "secondary": format_source_types(recommended_secondary, registry),
            "activity": format_source_types(recommended_activity, registry),
            "note": "For medium confidence: need full HC_REQ checklist completion. Primary + secondary + activity + operator confirmation all required before upgrade to high.",
        }

    # Rejected source warning
    rejected_warning = format_rejected_warning(registry)

    # Operator instruction
    if action_type == "manual_attribution_required":
        operator_instruction_lines = [
            f"ACTION: MANUAL ATTRIBUTION REQUIRED for {address}",
            f"",
            f"This address is labeled as '{current_label}' with {current_confidence} confidence.",
            f"The entity identity has NOT been established — manual research is required.",
            f"",
            f"STEP 1 — Trusted Primary Source (REQUIRED):",
            f"  Find at least ONE verifiable primary source that identifies this address.",
            f"  Acceptable: project official docs, exchange/institution label page,",
            f"  reputable block explorer label, signed statement, or internal verified record.",
            f"  Record findings in: trusted_source_label_value + trusted_source_url_or_note",
            f"",
            f"STEP 2 — Second Source / Cross-Source (REQUIRED):",
            f"  Find at least ONE independent secondary or cross-source confirmation.",
            f"  Acceptable: analytics dashboard label, cross-source clustering,",
            f"  transaction behavior evidence, social identity linkage.",
            f"  Record findings in: second_source_label_value + second_source_url_or_note",
            f"",
            f"STEP 3 — Activity Pattern (REQUIRED):",
            f"  Document on-chain behavior patterns consistent with the claimed identity.",
            f"  Review HyperLiquid position history for consistency.",
            f"  Record findings in: activity_pattern_note",
            f"",
            f"STEP 4 — Operator Confirmation (REQUIRED):",
            f"  Sign off on the identified label with operator_confirmed_label,",
            f"  operator_confidence_assessment, reviewer name, and reviewed_at timestamp.",
            f"  Set ready_for_upgrade = true ONLY when ALL evidence is complete.",
            f"",
            f"CRITICAL: This is an UNKNOWN whale. You MUST establish entity identity",
            f"before any confidence upgrade can proceed. DO NOT use rejected sources",
            f"(unsourced social posts, anonymous claims, AI attributions, screenshots",
            f"without URLs, stale labels, TG/chat labels, or vague whale claims).",
            f"",
            f"After completing workbook fields, rerun gates in order (see next_gate_commands).",
        ]
    else:
        operator_instruction_lines = [
            f"ACTION: CORROBORATION REQUIRED for {address}",
            f"",
            f"This address is labeled as '{current_label}' with {current_confidence} confidence.",
            f"The label is at medium confidence — additional corroborating evidence is needed",
            f"to reach high confidence before any TG test group delivery.",
            f"",
            f"STEP 1 — Verify Existing Primary Source (REQUIRED):",
            f"  Confirm the existing label source is valid and verifiable.",
            f"  If no primary source exists yet, find at least ONE verifiable primary source.",
            f"  Record findings in: trusted_source_label_value + trusted_source_url_or_note",
            f"",
            f"STEP 2 — Add Corroborating Secondary Source (REQUIRED):",
            f"  Find at least ONE independent secondary source confirming the label.",
            f"  Cross-reference: analytics dashboards, cross-source clustering,",
            f"  transaction behavior, social identity linkage.",
            f"  Record findings in: second_source_label_value + second_source_url_or_note",
            f"",
            f"STEP 3 — Document Activity Pattern (REQUIRED):",
            f"  Review and document HyperLiquid position history for consistency.",
            f"  Note any behavioral patterns matching the claimed entity.",
            f"  Record findings in: activity_pattern_note",
            f"",
            f"STEP 4 — Operator Confirmation (REQUIRED):",
            f"  Explicitly confirm the label with operator_confirmed_label,",
            f"  operator_confidence_assessment, reviewer name, and reviewed_at timestamp.",
            f"  Set ready_for_upgrade = true ONLY when ALL HC_REQ_001 through HC_REQ_009 pass.",
            f"",
            f"IMPORTANT: Medium confidence labels CANNOT go directly to TG test group.",
            f"You MUST complete the full evidence checklist and rerun all gates.",
            f"DO NOT use rejected sources as core evidence.",
            f"",
            f"After completing workbook fields, rerun gates in order (see next_gate_commands).",
        ]

    operator_instruction = "\n".join(operator_instruction_lines)

    # Workbook row hint
    workbook_row_hint = f"Row {workbook_row_idx + 2} in v115F workbook (CSV row {workbook_row_idx + 2}, 1-based data row {workbook_row_idx + 1})"

    action = {
        "address": address,
        "display_label": current_label,
        "current_confidence": current_confidence,
        "target_confidence": target_confidence,
        "priority": priority,
        "action_type": action_type,
        "blocked_stage": blocked_stage,
        "blocked_reasons": blocked_reasons,
        "intake_block_reasons": g_block_reasons,
        "missing_workbook_fields": missing_fields,
        "missing_evidence_types": missing_evidence,
        "recommended_source_types": recommended_source_types,
        "rejected_source_warning": rejected_warning,
        "operator_instruction": operator_instruction,
        "workbook_file": "runs/market_radar/v115f_whale_address_audit_operator_workbook.csv",
        "workbook_row_hint": workbook_row_hint,
        "next_gate_commands": list(NEXT_GATE_COMMANDS),
        "next_gate_command_order_enforced": True,
        "safety_status": {
            "real_workbook_modified": False,
            "real_label_upgrade_performed": False,
            "real_send_candidate_generated": False,
            "send_ready": False,
            "tg_test_group_ready": False,
            "tg_sent": False,
            "prod_state_write": False,
            "external_api_called": False,
            "credentials_read": False,
            "daemon_started": False,
            "watcher_started": False,
            "files_deleted": False,
        },
    }
    return action


def build_csv_row(action):
    """Convert action to CSV-safe row values."""
    recommended_str = ""
    if isinstance(action.get("recommended_source_types"), dict):
        rst = action["recommended_source_types"]
        parts = []
        parts.append("=== PRIMARY ===\n" + "\n".join(f"  * {s}" for s in rst.get("primary", [])))
        parts.append("=== SECONDARY ===\n" + "\n".join(f"  * {s}" for s in rst.get("secondary", [])))
        parts.append("=== ACTIVITY ===\n" + "\n".join(f"  * {s}" for s in rst.get("activity", [])))
        parts.append("NOTE: " + rst.get("note", ""))
        recommended_str = "\n\n".join(parts)

    # Use pipe separator within the blocked_reasons column for readability
    gate_commands_str = " ; ".join(action.get("next_gate_commands", []))

    return {
        "address": action["address"],
        "display_label": action["display_label"],
        "current_confidence": action["current_confidence"],
        "priority": action["priority"],
        "action_type": action["action_type"],
        "blocked_stage": action["blocked_stage"],
        "blocked_reasons": action.get("blocked_reasons", ""),
        "missing_workbook_fields": "; ".join(action.get("missing_workbook_fields", [])),
        "recommended_source_types": recommended_str,
        "operator_instruction": action.get("operator_instruction", ""),
        "next_gate_commands": gate_commands_str,
    }


def main():
    tz_shanghai = timezone(timedelta(hours=8))
    generated_at = datetime.now(tz_shanghai).isoformat()

    print("=" * 70)
    print("v115N Operator Action Queue — Local Only")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # Load all inputs
    # -----------------------------------------------------------------------
    print("\n[1] Loading inputs...")
    v115m_records = load_jsonl(V115M_RECORDS)
    print(f"  Loaded {len(v115m_records)} v115M real workflow records")

    v115m_decisions = load_jsonl(V115M_DECISIONS)
    print(f"  Loaded {len(v115m_decisions)} v115M real workflow decisions")

    v115m_gate = load_json(V115M_GATE_RESULT)
    print(f"  Loaded v115M gate result: {v115m_gate.get('stage')}")

    v115e_requests = load_jsonl(V115E_EVIDENCE_REQUESTS)
    print(f"  Loaded {len(v115e_requests)} v115E evidence requests")

    v115g_intakes = load_jsonl(V115G_INTAKE_DECISIONS)
    print(f"  Loaded {len(v115g_intakes)} v115G intake decisions")

    v115l_scorings = load_jsonl(V115L_SCORING_DECISIONS)
    print(f"  Loaded {len(v115l_scorings)} v115L scoring decisions")

    registry = load_json(V115K_REGISTRY)
    print(f"  Loaded v115K registry: {registry.get('version')}")

    scoring_policy = load_json(V115K_SCORING_POLICY)
    print(f"  Loaded v115K scoring policy: {scoring_policy.get('version')}")

    workbook_rows = load_csv_dict(V115F_WORKBOOK)
    print(f"  Loaded v115F workbook: {len(workbook_rows)} rows")

    # -----------------------------------------------------------------------
    # Build address index
    # -----------------------------------------------------------------------
    print("\n[2] Building address index...")
    # Index evidence requests by address
    evidence_by_addr = {}
    for req in v115e_requests:
        evidence_by_addr[req["address"]] = req

    # Index intake decisions by address
    intake_by_addr = {}
    for dec in v115g_intakes:
        intake_by_addr[dec["address"]] = dec

    # Index scoring decisions by address
    scoring_by_addr = {}
    for dec in v115l_scorings:
        scoring_by_addr[dec["address"]] = dec

    # Build address list from v115M records (the canonical order)
    addresses_data = []
    for i, rec in enumerate(v115m_records):
        addr = rec["address"]
        addresses_data.append({
            "address": addr,
            "current_label": rec["current_label"],
            "current_confidence": rec["current_confidence"],
            "target_confidence": rec.get("target_confidence", "high"),
            "v115m_record": rec,
            "v115m_decision": v115m_decisions[i] if i < len(v115m_decisions) else None,
            "v115e_request": evidence_by_addr.get(addr, {}),
            "v115g_intake": intake_by_addr.get(addr, {}),
            "v115l_scoring": scoring_by_addr.get(addr, {}),
            "workbook_row_idx": i,
        })

    # -----------------------------------------------------------------------
    # Generate operator actions
    # -----------------------------------------------------------------------
    print("\n[3] Generating operator actions...")
    operator_actions = []
    for ad in addresses_data:
        action = build_operator_action(
            ad,
            ad["v115m_record"],
            ad["v115m_decision"],
            ad["v115e_request"],
            ad["v115g_intake"],
            ad["v115l_scoring"],
            registry,
            scoring_policy,
            ad["workbook_row_idx"],
        )
        operator_actions.append(action)
        print(f"  Generated: {ad['address'][:10]}... ({action['action_type']}, {action['priority']})")

    # -----------------------------------------------------------------------
    # Classify actions
    # -----------------------------------------------------------------------
    high_priority = [a for a in operator_actions if a["priority"] == "high"]
    medium_priority = [a for a in operator_actions if a["priority"] == "medium"]
    manual_attribution = [a for a in operator_actions if a["action_type"] == "manual_attribution_required"]
    corroboration = [a for a in operator_actions if a["action_type"] == "corroboration_required"]

    csv_rows = [build_csv_row(a) for a in operator_actions]

    # -----------------------------------------------------------------------
    # Write JSONL
    # -----------------------------------------------------------------------
    print("\n[4] Writing outputs...")
    with open(OUT_JSONL, "w", encoding="utf-8", newline="\n") as f:
        for action in operator_actions:
            f.write(json.dumps(action, ensure_ascii=False) + "\n")
    print(f"  Wrote {len(operator_actions)} actions to {os.path.basename(OUT_JSONL)}")

    # -----------------------------------------------------------------------
    # Write JSON summary
    # -----------------------------------------------------------------------
    result = {
        "stage": "v115n_whale_manual_audit_operator_action_queue_local_only",
        "version": "v115N",
        "description": "Operator action queue generated from v115M blocked workflow results. NO real upgrade, NO send, NO TG. Actions only.",
        "operator_actions": len(operator_actions),
        "high_priority_actions": len(high_priority),
        "medium_priority_actions": len(medium_priority),
        "manual_attribution_required_count": len(manual_attribution),
        "corroboration_required_count": len(corroboration),
        "queue_csv_rows": len(csv_rows),
        "next_gate_command_order_enforced": True,
        "next_gate_commands": list(NEXT_GATE_COMMANDS),
        "real_workbook_modified": False,
        "real_label_upgrade_performed": False,
        "real_send_candidate_generated": False,
        "send_ready": False,
        "tg_test_group_ready": False,
        "tg_sent": False,
        "prod_state_write": False,
        "external_api_called": False,
        "ai_model_called": False,
        "credentials_read": False,
        "daemon_started": False,
        "watcher_started": False,
        "files_deleted": False,
        "local_review_ready": True,
        "generated_at": generated_at,
        "action_type_rules": {
            "manual_attribution_required": {
                "applies_to": "low confidence / unknown whale",
                "priority": "high",
                "requirements": [
                    "Trusted primary source (mandatory)",
                    "Second source / cross-source (mandatory)",
                    "Activity pattern (mandatory)",
                    "Operator confirmation (mandatory)",
                ],
                "note": "Unknown whale must establish entity identity before any confidence upgrade.",
            },
            "corroboration_required": {
                "applies_to": "medium confidence",
                "priority": "medium",
                "requirements": [
                    "Verify existing label source",
                    "Add corroborating secondary source",
                    "Document activity pattern",
                    "Complete operator confirmation",
                    "Pass all HC_REQ_001 through HC_REQ_009",
                ],
                "note": "Medium labels cannot go directly to TG test group. Must complete full checklist first.",
            },
        },
        "address_summary": [
            {
                "address": a["address"],
                "display_label": a["display_label"],
                "current_confidence": a["current_confidence"],
                "action_type": a["action_type"],
                "priority": a["priority"],
            }
            for a in operator_actions
        ],
    }
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  Wrote gate result to {os.path.basename(OUT_JSON)}")

    # -----------------------------------------------------------------------
    # Write CSV
    # -----------------------------------------------------------------------
    csv_fields = [
        "address",
        "display_label",
        "current_confidence",
        "priority",
        "action_type",
        "blocked_stage",
        "blocked_reasons",
        "missing_workbook_fields",
        "recommended_source_types",
        "operator_instruction",
        "next_gate_commands",
    ]
    with open(OUT_CSV, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)
    print(f"  Wrote {len(csv_rows)} rows to {os.path.basename(OUT_CSV)}")

    # -----------------------------------------------------------------------
    # Write Markdown
    # -----------------------------------------------------------------------
    md_lines = []
    md_lines.append("# v115N Whale Operator Action Queue")
    md_lines.append("")
    md_lines.append(f"**Generated**: {generated_at}")
    md_lines.append("")
    md_lines.append("## Overview")
    md_lines.append("")
    md_lines.append(f"- **Total addresses**: {len(operator_actions)}")
    md_lines.append(f"- **High priority (manual attribution)**: {len(high_priority)}")
    md_lines.append(f"- **Medium priority (corroboration)**: {len(medium_priority)}")
    md_lines.append(f"- **Manual attribution required**: {len(manual_attribution)}")
    md_lines.append(f"- **Corroboration required**: {len(corroboration)}")
    md_lines.append("")
    md_lines.append("## Safety Status")
    md_lines.append("")
    md_lines.append("| Item | Status |")
    md_lines.append("|------|--------|")
    md_lines.append("| Real workbook modified | **false** |")
    md_lines.append("| Real label upgrade performed | **false** |")
    md_lines.append("| Real send candidate generated | **false** |")
    md_lines.append("| Send ready | **false** |")
    md_lines.append("| TG test group ready | **false** |")
    md_lines.append("| TG sent | **false** |")
    md_lines.append("| Prod state write | **false** |")
    md_lines.append("| External API called | **false** |")
    md_lines.append("| Credentials read | **false** |")
    md_lines.append("")
    md_lines.append("## Next Gate Command Order (Enforced)")
    md_lines.append("")
    for i, cmd in enumerate(NEXT_GATE_COMMANDS, 1):
        md_lines.append(f"{i}. `{cmd}`")
    md_lines.append("")

    # High priority section
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## High Priority Actions (Manual Attribution Required)")
    md_lines.append("")
    md_lines.append(f"**Count**: {len(high_priority)}")
    md_lines.append("")
    md_lines.append("These addresses are **unknown whales** with low confidence. The operator MUST manually")
    md_lines.append("research and establish entity identity before any confidence upgrade can proceed.")
    md_lines.append("")

    for i, action in enumerate(high_priority, 1):
        rst = action.get("recommended_source_types", {})
        md_lines.append(f"### {i}. {action['display_label']}")
        md_lines.append("")
        md_lines.append(f"- **Address**: `{action['address']}`")
        md_lines.append(f"- **Current Confidence**: {action['current_confidence']}")
        md_lines.append(f"- **Action Type**: {action['action_type']}")
        md_lines.append(f"- **Priority**: {action['priority']}")
        md_lines.append(f"- **Blocked Stage**: {action['blocked_stage']}")
        md_lines.append(f"- **Workbook Row Hint**: {action.get('workbook_row_hint', '')}")
        md_lines.append("")
        md_lines.append("#### Blocked Reasons")
        md_lines.append("")
        for reason in action.get("blocked_reasons", "").split("; "):
            if reason.strip():
                md_lines.append(f"- {reason.strip()}")
        md_lines.append("")
        md_lines.append("#### Missing Workbook Fields")
        md_lines.append("")
        for field in action.get("missing_workbook_fields", []):
            md_lines.append(f"- `{field}`")
        md_lines.append("")
        md_lines.append("#### Recommended Source Types")
        md_lines.append("")
        md_lines.append("**Primary Sources (at least 1 required):**")
        for s in rst.get("primary", []):
            md_lines.append(f"- {s}")
        md_lines.append("")
        md_lines.append("**Secondary Sources (at least 1 required):**")
        for s in rst.get("secondary", []):
            md_lines.append(f"- {s}")
        md_lines.append("")
        md_lines.append("**Activity Sources (at least 1 required):**")
        for s in rst.get("activity", []):
            md_lines.append(f"- {s}")
        md_lines.append("")
        md_lines.append(f"> {rst.get('note', '')}")
        md_lines.append("")
        md_lines.append("#### Operator Instruction")
        md_lines.append("")
        md_lines.append("```")
        md_lines.append(action.get("operator_instruction", ""))
        md_lines.append("```")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    # Medium priority section
    md_lines.append("## Medium Priority Actions (Corroboration Required)")
    md_lines.append("")
    md_lines.append(f"**Count**: {len(medium_priority)}")
    md_lines.append("")
    md_lines.append("These addresses have medium confidence labels. Additional corroborating evidence is needed")
    md_lines.append("to reach high confidence. They CANNOT go directly to TG test group.")
    md_lines.append("")

    for i, action in enumerate(medium_priority, 1):
        rst = action.get("recommended_source_types", {})
        md_lines.append(f"### {i}. {action['display_label']}")
        md_lines.append("")
        md_lines.append(f"- **Address**: `{action['address']}`")
        md_lines.append(f"- **Current Confidence**: {action['current_confidence']}")
        md_lines.append(f"- **Action Type**: {action['action_type']}")
        md_lines.append(f"- **Priority**: {action['priority']}")
        md_lines.append(f"- **Blocked Stage**: {action['blocked_stage']}")
        md_lines.append(f"- **Workbook Row Hint**: {action.get('workbook_row_hint', '')}")
        md_lines.append("")
        md_lines.append("#### Blocked Reasons")
        md_lines.append("")
        for reason in action.get("blocked_reasons", "").split("; "):
            if reason.strip():
                md_lines.append(f"- {reason.strip()}")
        md_lines.append("")
        md_lines.append("#### Missing Workbook Fields")
        md_lines.append("")
        for field in action.get("missing_workbook_fields", []):
            md_lines.append(f"- `{field}`")
        md_lines.append("")
        md_lines.append("#### Recommended Source Types")
        md_lines.append("")
        md_lines.append("**Primary Sources (at least 1 required):**")
        for s in rst.get("primary", []):
            md_lines.append(f"- {s}")
        md_lines.append("")
        md_lines.append("**Secondary Sources (at least 1 required):**")
        for s in rst.get("secondary", []):
            md_lines.append(f"- {s}")
        md_lines.append("")
        md_lines.append("**Activity Sources (at least 1 required):**")
        for s in rst.get("activity", []):
            md_lines.append(f"- {s}")
        md_lines.append("")
        md_lines.append(f"> {rst.get('note', '')}")
        md_lines.append("")
        md_lines.append("#### Operator Instruction")
        md_lines.append("")
        md_lines.append("```")
        md_lines.append(action.get("operator_instruction", ""))
        md_lines.append("```")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    md_lines.append("")
    md_lines.append("## Rejected Source Warning")
    md_lines.append("")
    md_lines.append("The following evidence sources MUST NOT be used to support label confidence upgrades:")
    md_lines.append("")
    rejected_types = registry.get("categories", {}).get("rejected_source", {}).get("types", [])
    for rt in rejected_types:
        md_lines.append(f"- **{rt['label']}** (`{rt['type_id']}`): {rt['rejection_reason']}")
    md_lines.append("")
    md_lines.append("> Any label whose ONLY evidence comes from rejected_source categories must be immediately blocked.")
    md_lines.append("")

    with open(OUT_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md_lines))
    print(f"  Wrote markdown to {os.path.basename(OUT_MD)}")

    # -----------------------------------------------------------------------
    # Write Handoff
    # -----------------------------------------------------------------------
    handoff_lines = []
    handoff_lines.append("# v115N Whale Operator Action Queue — Local Only Handoff")
    handoff_lines.append("")
    handoff_lines.append(f"**Generated**: {generated_at}")
    handoff_lines.append("")
    handoff_lines.append("## What This Stage Did")
    handoff_lines.append("")
    handoff_lines.append(f"- Read {len(v115m_records)} v115M real workflow records (all blocked)")
    handoff_lines.append(f"- Read {len(v115e_requests)} v115E evidence requests")
    handoff_lines.append(f"- Read {len(v115g_intakes)} v115G intake decisions")
    handoff_lines.append(f"- Read {len(v115l_scorings)} v115L scoring decisions")
    handoff_lines.append(f"- Read v115K source registry & scoring policy")
    handoff_lines.append(f"- Read v115F operator workbook ({len(workbook_rows)} rows)")
    handoff_lines.append(f"- Generated {len(operator_actions)} operator actions for the 4 real addresses")
    handoff_lines.append("")

    handoff_lines.append("## Current Status of 4 Addresses")
    handoff_lines.append("")
    handoff_lines.append("All 4 addresses remain BLOCKED:")
    handoff_lines.append("")
    for a in operator_actions:
        handoff_lines.append(f"  - `{a['address'][:10]}...`: {a['action_type']} (priority={a['priority']})")
    handoff_lines.append("")

    handoff_lines.append("## Explicit Safety Assertions")
    handoff_lines.append("")
    handoff_lines.append("The following are ALL **false** — this stage produced NO real changes:")
    handoff_lines.append("")
    handoff_lines.append("| Assertion | Value |")
    handoff_lines.append("|-----------|-------|")
    handoff_lines.append("| real_workbook_modified | false |")
    handoff_lines.append("| real_label_upgrade_performed | false |")
    handoff_lines.append("| real_send_candidate_generated | false |")
    handoff_lines.append("| send_ready | false |")
    handoff_lines.append("| tg_test_group_ready | false |")
    handoff_lines.append("| tg_sent | false |")
    handoff_lines.append("| prod_state_write | false |")
    handoff_lines.append("| external_api_called | false |")
    handoff_lines.append("| ai_model_called | false |")
    handoff_lines.append("| credentials_read | false |")
    handoff_lines.append("| daemon_started | false |")
    handoff_lines.append("| watcher_started | false |")
    handoff_lines.append("| files_deleted | false |")
    handoff_lines.append("")

    handoff_lines.append("## TG Test Group Status")
    handoff_lines.append("")
    handoff_lines.append("**ALL 4 addresses are NOT allowed in TG test group.**")
    handoff_lines.append("")
    handoff_lines.append("This stage is operator action queue only. It does NOT grant TG permission.")
    handoff_lines.append("")

    handoff_lines.append("## What This Stage IS")
    handoff_lines.append("")
    handoff_lines.append("- A structured operator action queue based on v115M blocked results")
    handoff_lines.append("- Translation of blocked reasons into actionable manual evidence tasks")
    handoff_lines.append("- Guidance on which source types to use and which to reject")
    handoff_lines.append("- The exact gate command order to rerun after evidence completion")
    handoff_lines.append("")

    handoff_lines.append("## What This Stage IS NOT")
    handoff_lines.append("")
    handoff_lines.append("- NOT a real label upgrade")
    handoff_lines.append("- NOT a real send candidate generation")
    handoff_lines.append("- NOT a TG test group delivery")
    handoff_lines.append("- NOT a production state write")
    handoff_lines.append("- NOT an external API call")
    handoff_lines.append("- NOT a credential read")
    handoff_lines.append("")

    handoff_lines.append("## Next Steps")
    handoff_lines.append("")
    handoff_lines.append("1. **Operator manually researches** each address using the recommended source types")
    handoff_lines.append("2. **Operator fills in workbook fields** in the v115F workbook CSV")
    handoff_lines.append("3. **Or: Run Gemini audit** of this action queue to assess operator feasibility")
    handoff_lines.append("4. **After evidence complete**: Rerun gates in fixed order:")
    handoff_lines.append("   - v115G (intake gate)")
    handoff_lines.append("   - v115L (evidence scoring gate)")
    handoff_lines.append("   - v115H (adjudication gate)")
    handoff_lines.append("   - v115M (end-to-end workflow gate)")
    handoff_lines.append("5. **If all gates pass**: Then evaluate TG test group routing via v115D preview gate")
    handoff_lines.append("")

    handoff_lines.append("## Files Generated")
    handoff_lines.append("")
    handoff_lines.append(f"- `{os.path.basename(OUT_JSONL)}` — 4 operator actions (JSONL)")
    handoff_lines.append(f"- `{os.path.basename(OUT_JSON)}` — Summary gate result")
    handoff_lines.append(f"- `{os.path.basename(OUT_CSV)}` — 4-row CSV for manual editing")
    handoff_lines.append(f"- `{os.path.basename(OUT_MD)}` — Human-readable action queue report")
    handoff_lines.append(f"- `{os.path.basename(OUT_HANDOFF)}` — This handoff document")
    handoff_lines.append("")

    handoff_lines.append("## Files NOT Modified")
    handoff_lines.append("")
    handoff_lines.append("- v115F workbook (NOT modified)")
    handoff_lines.append("- Any v115A-v115M historical products (NOT modified)")
    handoff_lines.append("- Any production/state/send/TG files (NOT modified)")
    handoff_lines.append("")

    with open(OUT_HANDOFF, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(handoff_lines))
    print(f"  Wrote handoff to {os.path.basename(OUT_HANDOFF)}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("v115N Operator Action Queue — Complete")
    print("=" * 70)
    print(f"  operator_actions: {len(operator_actions)}")
    print(f"  high_priority_actions: {len(high_priority)}")
    print(f"  medium_priority_actions: {len(medium_priority)}")
    print(f"  manual_attribution_required_count: {len(manual_attribution)}")
    print(f"  corroboration_required_count: {len(corroboration)}")
    print(f"  next_gate_command_order_enforced: True")
    print(f"  real_workbook_modified: False")
    print(f"  real_label_upgrade_performed: False")
    print(f"  real_send_candidate_generated: False")
    print(f"  send_ready: False")
    print(f"  tg_test_group_ready: False")
    print(f"  tg_sent: False")
    print(f"  prod_state_write: False")
    print(f"  external_api_called: False")
    print(f"  credentials_read: False")
    return 0


if __name__ == "__main__":
    sys.exit(main())
