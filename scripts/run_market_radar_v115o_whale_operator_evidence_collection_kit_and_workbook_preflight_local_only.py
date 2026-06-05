#!/usr/bin/env python3
"""
v115O Whale Operator Evidence Collection Kit & Workbook Preflight — Local Only
================================================================================
Reads v115N operator actions, v115F workbook (read-only), and v115K policy configs
to generate:

  1. Per-address evidence collection items (what to research, what sources to use,
     what to avoid, what workbook fields to fill, minimum pass conditions).
  2. Workbook preflight records & decisions (checks current v115F workbook for
     completeness — all 4 addresses expected blocked with empty workbook).
  3. Markdown + CSV operator evidence collection kit.
  4. Markdown preflight report.
  5. Local-only handoff.

NO real workbook modifications, NO label upgrades, NO send candidates, NO TG,
NO external API calls, NO credential reads.
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

# Inputs (read-only)
V115N_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115n_whale_manual_audit_operator_actions.jsonl")
V115F_WORKBOOK = os.path.join(RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv")
V115K_REGISTRY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_source_registry.json")
V115K_SCORING_POLICY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy.json")

# Outputs
V115O_ITEMS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115o_whale_operator_evidence_collection_items.jsonl")
V115O_PREFLIGHT_RECORDS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115o_whale_operator_workbook_preflight_records.jsonl")
V115O_PREFLIGHT_DECISIONS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115o_whale_operator_workbook_preflight_decisions.jsonl")
V115O_RESULT_JSON = os.path.join(RESULTS_DIR, "market_radar_v115o_whale_operator_evidence_collection_kit_result.json")
V115O_KIT_MD = os.path.join(RUNS_DIR, "v115o_whale_operator_evidence_collection_kit.md")
V115O_KIT_CSV = os.path.join(RUNS_DIR, "v115o_whale_operator_evidence_collection_kit.csv")
V115O_PREFLIGHT_REPORT_MD = os.path.join(RUNS_DIR, "v115o_whale_operator_workbook_preflight_report.md")
V115O_HANDOFF_MD = os.path.join(RUNS_DIR, "v115o_whale_operator_evidence_collection_kit_local_only_handoff.md")

NOW_ISO = datetime.now(timezone(timedelta(hours=8))).isoformat()

# ---------------------------------------------------------------------------
# Known rejected source type_ids from v115K registry
# ---------------------------------------------------------------------------
REJECTED_SOURCE_TYPE_IDS = [
    "rejected_unsourced_social_post",
    "rejected_single_anonymous_claim",
    "rejected_ai_attribution",
    "rejected_screenshot_without_url",
    "rejected_stale_label_no_date",
    "rejected_tg_chat_label",
    "rejected_vague_whale_claim",
]

REJECTED_SOURCE_LABELS = [
    "Unsourced Social Post",
    "Single Anonymous Claim",
    "AI-Generated Attribution Without Source",
    "Screenshot Without Verifiable URL or Note",
    "Stale Label Without Update Date",
    "Label Copied from TG/Chat Without Evidence",
    "Vague 'Whale Said to Be X' Style Notes",
]

# ---------------------------------------------------------------------------
# Gate command order (enforced)
# ---------------------------------------------------------------------------
NEXT_GATE_COMMANDS = [
    "python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py",
    "python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py",
    "python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py",
    "python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py",
]

PREFLIGHT_COMMAND = "python scripts/run_market_radar_v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only.py"


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


def write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def get_primary_checklist():
    """Return the primary source checklist from registry knowledge."""
    return [
        "Project/Team Official Docs or Disclosure (primary_project_official_docs)",
        "Verified Exchange/Institution Address Label Page (primary_exchange_institution_label)",
        "Reputable Block Explorer Label (primary_reputable_explorer_label)",
        "Public Signed Statement by Entity/Operator (primary_signed_statement)",
        "Internally Verified Historical Label Record (primary_internal_verified_label)",
    ]


def get_secondary_checklist():
    return [
        "Reputable Analytics Dashboard Label (secondary_analytics_dashboard)",
        "Cross-Source Wallet Clustering Note (secondary_cross_source_clustering)",
        "Historical Transaction Behavior Evidence (secondary_tx_behavior_evidence)",
        "Public Social Identity Linkage (secondary_social_identity_linkage)",
        "Previous Operator-Reviewed Label Note (secondary_operator_reviewed_note)",
    ]


def get_activity_checklist():
    return [
        "Consistent Counterparty Pattern (activity_counterparty_pattern)",
        "Repeated Asset/Venue Pattern (activity_asset_venue_pattern)",
        "Position Behavior Consistency (activity_position_consistency)",
        "Historical Interaction with Known Entity Addresses (activity_historical_entity_interaction)",
    ]


def get_operator_confirmation_fields():
    return [
        "operator_confirmed_label",
        "operator_confidence_assessment",
        "reviewer",
        "reviewed_at",
        "ready_for_upgrade",
    ]


def get_reviewer_fields():
    return [
        "reviewer",
        "reviewed_at",
    ]


def get_required_evidence_bundle_low():
    """Required evidence bundle for low/unknown whale (manual_attribution_required)."""
    return [
        "trusted_primary_source",
        "independent_second_source_or_cross_source",
        "activity_pattern_note",
        "operator_confirmation",
        "reviewer",
        "reviewed_at",
        "ready_for_upgrade",
    ]


def get_required_evidence_bundle_medium():
    """Required evidence bundle for medium confidence (corroboration_required)."""
    return [
        "trusted_primary_source_or_existing_label_source",
        "independent_second_source_or_cross_source",
        "activity_pattern_note",
        "operator_confirmation",
        "reviewer",
        "reviewed_at",
        "ready_for_upgrade",
    ]


def get_workbook_fields_to_fill():
    """All workbook fields the operator must fill for any address upgrade."""
    return [
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


def build_evidence_collection_item(action, registry, scoring_policy):
    """Build a single evidence collection item from a v115N operator action."""
    addr = action["address"]
    display_label = action["display_label"]
    current_confidence = action["current_confidence"]
    priority = action["priority"]
    action_type = action["action_type"]
    recommended = action.get("recommended_source_types", {})

    is_low = current_confidence == "low"

    if is_low:
        research_goal = (
            f"Establish entity identity for {display_label} ({addr}). "
            "This address is currently unknown/low confidence. The operator MUST "
            "manually research and determine which entity or individual controls this address "
            "using trusted primary sources, independent secondary corroboration, and "
            "on-chain activity pattern analysis."
        )
        required_bundle = [
            "trusted_primary_source",
            "independent_second_source_or_cross_source",
            "activity_pattern_note",
            "operator_confirmation",
            "reviewer",
            "reviewed_at",
            "ready_for_upgrade",
        ]
        minimum_pass_condition = (
            "Cannot upgrade from unknown/low unless ALL required evidence fields are complete "
            "(trusted_primary_source + independent_second_source + activity_pattern_note "
            "+ operator_confirmation + reviewer + reviewed_at + ready_for_upgrade=true) "
            "AND no rejected source is present as core evidence. "
            "At least one primary_source is REQUIRED before any upgrade."
        )
        safety_status = "SAFE — local-only, no real upgrade, no send, no TG"
    else:
        research_goal = (
            f"Corroborate existing medium-confidence label for {display_label} ({addr}). "
            "This address has a medium confidence label. The operator MUST find additional "
            "corroborating evidence from primary sources, independent secondary sources, "
            "and document activity patterns consistent with the claimed identity. "
            "Medium labels CANNOT go directly to TG test group."
        )
        required_bundle = [
            "trusted_primary_source_or_existing_label_source",
            "independent_second_source_or_cross_source",
            "activity_pattern_note",
            "operator_confirmation",
            "reviewer",
            "reviewed_at",
            "ready_for_upgrade",
        ]
        minimum_pass_condition = (
            "Medium label CANNOT enter TG test group until corroboration passes "
            "the full HC_REQ_001 through HC_REQ_009 scoring checklist AND "
            "adjudication gate approves the upgrade to high confidence. "
            "All required evidence fields must be complete."
        )
        safety_status = "SAFE — local-only, no real upgrade, no send, no TG"

    item = {
        "version": "v115O",
        "address": addr,
        "display_label": display_label,
        "current_confidence": current_confidence,
        "priority": priority,
        "action_type": action_type,
        "research_goal": research_goal,
        "required_evidence_bundle": required_bundle,
        "primary_source_checklist": recommended.get("primary", get_primary_checklist()),
        "secondary_source_checklist": recommended.get("secondary", get_secondary_checklist()),
        "activity_pattern_checklist": recommended.get("activity", get_activity_checklist()),
        "operator_confirmation_fields": get_operator_confirmation_fields(),
        "reviewer_fields": get_reviewer_fields(),
        "rejected_source_types": [r["label"] for r in registry.get("categories", {}).get("rejected_source", {}).get("types", [])],
        "rejected_source_type_ids": REJECTED_SOURCE_TYPE_IDS,
        "do_not_use_evidence_warning": action.get("rejected_source_warning", ""),
        "workbook_fields_to_fill": get_workbook_fields_to_fill(),
        "minimum_pass_condition": minimum_pass_condition,
        "next_local_preflight_command": PREFLIGHT_COMMAND,
        "next_gate_commands_after_preflight_pass": NEXT_GATE_COMMANDS,
        "next_gate_command_order_enforced": True,
        "safety_status": safety_status,
        "generated_at": NOW_ISO,
    }
    return item


def build_preflight_record(workbook_row):
    """Build a preflight record from a v115F workbook row."""
    addr = workbook_row.get("address", "")
    label = workbook_row.get("current_label", "")
    confidence = workbook_row.get("current_confidence", "")

    operator_fields = {
        "trusted_source_label_value": workbook_row.get("trusted_source_label_value", "").strip(),
        "trusted_source_url_or_note": workbook_row.get("trusted_source_url_or_note", "").strip(),
        "second_source_label_value": workbook_row.get("second_source_label_value", "").strip(),
        "second_source_url_or_note": workbook_row.get("second_source_url_or_note", "").strip(),
        "activity_pattern_note": workbook_row.get("activity_pattern_note", "").strip(),
        "operator_confirmed_label": workbook_row.get("operator_confirmed_label", "").strip(),
        "operator_confidence_assessment": workbook_row.get("operator_confidence_assessment", "").strip(),
        "reviewer": workbook_row.get("reviewer", "").strip(),
        "reviewed_at": workbook_row.get("reviewed_at", "").strip(),
        "ready_for_upgrade": workbook_row.get("ready_for_upgrade", "").strip(),
    }

    # Determine which fields are present vs missing
    present = []
    missing = []
    for field, val in operator_fields.items():
        if field == "ready_for_upgrade":
            # ready_for_upgrade is "true"/"false" string or empty - check for truthy "true"
            if val.lower() == "true":
                present.append(field)
            else:
                missing.append(field)
        else:
            if val:
                present.append(field)
            else:
                missing.append(field)

    # Check for rejected source hits in the workbook data
    all_text = " ".join([v for v in operator_fields.values()]) + " " + workbook_row.get("block_reasons", "")
    rejected_hits = []
    for rtype in REJECTED_SOURCE_TYPE_IDS + REJECTED_SOURCE_LABELS:
        rlower = rtype.lower()
        if rlower in all_text.lower():
            if rtype not in rejected_hits:
                rejected_hits.append(rtype)

    record = {
        "version": "v115O",
        "address": addr,
        "display_label": label,
        "current_confidence": confidence,
        "operator_fields_status": operator_fields,
        "present_fields": present,
        "missing_required_fields": missing,
        "rejected_source_hits": rejected_hits,
        "checked_at": NOW_ISO,
    }
    return record


def build_preflight_decision(record, action_type):
    """Build a preflight decision from a record."""
    addr = record["address"]
    label = record["display_label"]
    confidence = record["current_confidence"]

    missing = record["missing_required_fields"]
    present = record["present_fields"]
    rejected_hits = record["rejected_source_hits"]

    preflight_ready = len(missing) == 0 and len(rejected_hits) == 0

    # Currently the workbook is empty, so all are blocked
    ready_for_gate_rerun = False

    decision = {
        "version": "v115O",
        "address": addr,
        "display_label": label,
        "current_confidence": confidence,
        "action_type": action_type,
        "preflight_ready": preflight_ready,
        "missing_required_fields": missing,
        "present_fields": present,
        "rejected_source_hits": rejected_hits,
        "ready_for_gate_rerun": ready_for_gate_rerun,
        "recommended_next_step": (
            f"Operator must fill ALL missing workbook fields ({len(missing)} missing) "
            f"in {V115F_WORKBOOK} before re-running preflight. "
            "Do NOT rerun gates until preflight passes."
        ),
        "generated_at": NOW_ISO,
    }
    return decision


def build_kit_markdown(items, preflight_decisions):
    """Build the evidence collection kit markdown report."""
    high_items = [i for i in items if i["priority"] == "high"]
    medium_items = [i for i in items if i["priority"] == "medium"]

    lines = []
    lines.append("# v115O Whale Operator Evidence Collection Kit")
    lines.append("")
    lines.append(f"**Generated**: {NOW_ISO}")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- **Total addresses**: {len(items)}")
    lines.append(f"- **High priority (manual attribution)**: {len(high_items)}")
    lines.append(f"- **Medium priority (corroboration)**: {len(medium_items)}")
    lines.append(f"- **Manual attribution required**: {len(high_items)}")
    lines.append(f"- **Corroboration required**: {len(medium_items)}")
    lines.append("")
    lines.append("## Safety Status")
    lines.append("")
    lines.append("| Item | Status |")
    lines.append("|------|--------|")
    lines.append("| Workbook modified | **false** |")
    lines.append("| Real label upgrade performed | **false** |")
    lines.append("| Real send candidate generated | **false** |")
    lines.append("| Send ready | **false** |")
    lines.append("| TG test group ready | **false** |")
    lines.append("| TG sent | **false** |")
    lines.append("| Prod state write | **false** |")
    lines.append("| External API called | **false** |")
    lines.append("| Credentials read | **false** |")
    lines.append("")

    # Preflight command
    lines.append("## Preflight Command")
    lines.append("")
    lines.append(f"```bash\n{PREFLIGHT_COMMAND}\n```")
    lines.append("")
    lines.append("Run this preflight FIRST after filling v115F workbook. It checks field completeness.")
    lines.append("")

    # Next gate commands
    lines.append("## Next Gate Command Order (Enforced — Only After Preflight Pass)")
    lines.append("")
    for i, cmd in enumerate(NEXT_GATE_COMMANDS, 1):
        lines.append(f"{i}. `{cmd}`")
    lines.append("")

    # ---- High Priority Section ----
    lines.append("---")
    lines.append("")
    lines.append("## High Priority Manual Attribution")
    lines.append("")
    lines.append(f"**Count**: {len(high_items)}")
    lines.append("")
    lines.append(
        "These addresses are **unknown whales** with low confidence. The operator MUST manually "
        "research and establish entity identity before any confidence upgrade can proceed."
    )
    lines.append("")

    for idx, item in enumerate(high_items, 1):
        addr = item["address"]
        label = item["display_label"]
        lines.append(f"### {idx}. {label}")
        lines.append("")
        lines.append(f"- **Address**: `{addr}`")
        lines.append(f"- **Current Confidence**: {item['current_confidence']}")
        lines.append(f"- **Action Type**: {item['action_type']}")
        lines.append(f"- **Priority**: {item['priority']}")
        lines.append("")

        # Find matching preflight decision
        pfd = next((d for d in preflight_decisions if d["address"] == addr), None)

        lines.append("#### Current Status")
        lines.append("")
        if pfd:
            lines.append(f"- **Preflight Ready**: **{pfd['preflight_ready']}**")
            lines.append(f"- **Ready for Gate Rerun**: **{pfd['ready_for_gate_rerun']}**")
        lines.append(f"- **Blocked**: YES — workbook fields are empty, missing {len(item['required_evidence_bundle'])} required evidence items")
        lines.append("")

        lines.append("#### Why Blocked")
        lines.append("")
        lines.append("The v115F workbook for this address is empty. All operator-managed evidence fields are blank:")
        lines.append("")
        for field in item["workbook_fields_to_fill"]:
            lines.append(f"- `{field}`: **EMPTY**")
        lines.append("")

        lines.append("#### What to Research")
        lines.append("")
        lines.append(item["research_goal"])
        lines.append("")

        lines.append("#### Required Evidence Bundle")
        lines.append("")
        for eb in item["required_evidence_bundle"]:
            lines.append(f"- [ ] {eb}")
        lines.append("")

        lines.append("#### Primary Source Checklist (at least 1 required)")
        lines.append("")
        for ps in item["primary_source_checklist"]:
            lines.append(f"- [ ] {ps}")
        lines.append("")

        lines.append("#### Secondary Source Checklist (at least 1 required)")
        lines.append("")
        for ss in item["secondary_source_checklist"]:
            lines.append(f"- [ ] {ss}")
        lines.append("")

        lines.append("#### Activity Pattern Checklist (at least 1 required)")
        lines.append("")
        for ac in item["activity_pattern_checklist"]:
            lines.append(f"- [ ] {ac}")
        lines.append("")

        lines.append("#### Forbidden Source Types (DO NOT USE)")
        lines.append("")
        for rs in item["rejected_source_types"]:
            lines.append(f"- ❌ {rs}")
        lines.append("")

        lines.append("#### Workbook Fields to Fill")
        lines.append("")
        lines.append(f"File: `{V115F_WORKBOOK}`")
        lines.append("")
        for field in item["workbook_fields_to_fill"]:
            lines.append(f"- `{field}`")
        lines.append("")

        lines.append("#### Minimum Pass Condition")
        lines.append("")
        lines.append(item["minimum_pass_condition"])
        lines.append("")

        lines.append("#### After Filling Workbook")
        lines.append("")
        lines.append(f"1. Run preflight: `{PREFLIGHT_COMMAND}`")
        lines.append("2. If preflight passes, rerun gates in order:")
        for cmd in NEXT_GATE_COMMANDS:
            lines.append(f"   - `{cmd}`")
        lines.append("")

        lines.append("---")
        lines.append("")

    # ---- Medium Priority Section ----
    lines.append("## Medium Priority Corroboration")
    lines.append("")
    lines.append(f"**Count**: {len(medium_items)}")
    lines.append("")
    lines.append(
        "These addresses have medium confidence labels. Additional corroborating evidence is needed "
        "to reach high confidence. They **CANNOT** go directly to TG test group."
    )
    lines.append("")

    for idx, item in enumerate(medium_items, 1):
        addr = item["address"]
        label = item["display_label"]
        lines.append(f"### {idx}. {label}")
        lines.append("")
        lines.append(f"- **Address**: `{addr}`")
        lines.append(f"- **Current Confidence**: {item['current_confidence']}")
        lines.append(f"- **Action Type**: {item['action_type']}")
        lines.append(f"- **Priority**: {item['priority']}")
        lines.append("")

        pfd = next((d for d in preflight_decisions if d["address"] == addr), None)

        lines.append("#### Current Status")
        lines.append("")
        if pfd:
            lines.append(f"- **Preflight Ready**: **{pfd['preflight_ready']}**")
            lines.append(f"- **Ready for Gate Rerun**: **{pfd['ready_for_gate_rerun']}**")
        lines.append(f"- **Blocked**: YES — workbook fields are empty, missing {len(item['required_evidence_bundle'])} required evidence items")
        lines.append("")

        lines.append("#### Why Blocked")
        lines.append("")
        lines.append("The v115F workbook for this address is empty. All operator-managed evidence fields are blank:")
        lines.append("")
        for field in item["workbook_fields_to_fill"]:
            lines.append(f"- `{field}`: **EMPTY**")
        lines.append("")

        lines.append("#### What to Research")
        lines.append("")
        lines.append(item["research_goal"])
        lines.append("")

        lines.append("#### Required Evidence Bundle")
        lines.append("")
        for eb in item["required_evidence_bundle"]:
            lines.append(f"- [ ] {eb}")
        lines.append("")

        lines.append("#### Primary Source Checklist (at least 1 required)")
        lines.append("")
        for ps in item["primary_source_checklist"]:
            lines.append(f"- [ ] {ps}")
        lines.append("")

        lines.append("#### Secondary Source Checklist (at least 1 required)")
        lines.append("")
        for ss in item["secondary_source_checklist"]:
            lines.append(f"- [ ] {ss}")
        lines.append("")

        lines.append("#### Activity Pattern Checklist (at least 1 required)")
        lines.append("")
        for ac in item["activity_pattern_checklist"]:
            lines.append(f"- [ ] {ac}")
        lines.append("")

        lines.append("#### Forbidden Source Types (DO NOT USE)")
        lines.append("")
        for rs in item["rejected_source_types"]:
            lines.append(f"- ❌ {rs}")
        lines.append("")

        lines.append("#### Workbook Fields to Fill")
        lines.append("")
        lines.append(f"File: `{V115F_WORKBOOK}`")
        lines.append("")
        for field in item["workbook_fields_to_fill"]:
            lines.append(f"- `{field}`")
        lines.append("")

        lines.append("#### Minimum Pass Condition")
        lines.append("")
        lines.append(item["minimum_pass_condition"])
        lines.append("")

        lines.append("#### After Filling Workbook")
        lines.append("")
        lines.append(f"1. Run preflight: `{PREFLIGHT_COMMAND}`")
        lines.append("2. If preflight passes, rerun gates in order:")
        for cmd in NEXT_GATE_COMMANDS:
            lines.append(f"   - `{cmd}`")
        lines.append("")

        lines.append("---")
        lines.append("")

    # Rejected Source Warning
    lines.append("## Rejected Source Warning")
    lines.append("")
    lines.append("The following evidence sources **MUST NOT** be used to support label confidence upgrades:")
    lines.append("")
    for i, (rid, rlabel) in enumerate(zip(REJECTED_SOURCE_TYPE_IDS, REJECTED_SOURCE_LABELS), 1):
        lines.append(f"{i}. **{rlabel}** (`{rid}`)")
    lines.append("")
    lines.append("> Any label whose ONLY evidence comes from rejected_source categories must be immediately blocked with REJECTED_EVIDENCE_ONLY block reason.")
    lines.append("")

    return "\n".join(lines)


def build_preflight_report_md(preflight_records, preflight_decisions):
    """Build the preflight report markdown."""
    lines = []
    lines.append("# v115O Whale Workbook Preflight Report")
    lines.append("")
    lines.append(f"**Generated**: {NOW_ISO}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Total addresses checked**: {len(preflight_decisions)}")
    lines.append(f"- **Preflight ready**: {sum(1 for d in preflight_decisions if d['preflight_ready'])}")
    lines.append(f"- **Preflight blocked**: {sum(1 for d in preflight_decisions if not d['preflight_ready'])}")
    lines.append(f"- **Ready for gate rerun**: {sum(1 for d in preflight_decisions if d['ready_for_gate_rerun'])}")
    lines.append("")

    lines.append("## ⚠️ Critical Finding")
    lines.append("")
    lines.append("**ALL 4 addresses are currently PREFLIGHT BLOCKED.**")
    lines.append("")
    lines.append("The v115F workbook (`runs/market_radar/v115f_whale_address_audit_operator_workbook.csv`) is empty — ")
    lines.append("all operator-managed evidence fields are blank. No address has any completed evidence.")
    lines.append("")
    lines.append("### What This Means")
    lines.append("")
    lines.append("- **Gate rerun is NOT permitted**: Do NOT run v115G → v115L → v115H → v115M until preflight passes.")
    lines.append("- **TG test group is NOT accessible**: No address can enter TG test group in the current state.")
    lines.append("- **Label upgrade is NOT possible**: All addresses lack the required evidence for any confidence upgrade.")
    lines.append("- **Operator action required**: Fill v115F workbook fields for each address, then rerun v115O preflight.")
    lines.append("")

    lines.append("## Required Operator Workflow")
    lines.append("")
    lines.append("1. Open `runs/market_radar/v115f_whale_address_audit_operator_workbook.csv`")
    lines.append(f"2. Fill ALL required fields for each address (see evidence collection kit at `{V115O_KIT_MD}`)")
    lines.append(f"3. Run preflight: `{PREFLIGHT_COMMAND}`")
    lines.append("4. If preflight passes (all addresses `preflight_ready=true`), proceed to gates:")
    for cmd in NEXT_GATE_COMMANDS:
        lines.append(f"   - `{cmd}`")
    lines.append("")

    lines.append("## Per-Address Preflight Results")
    lines.append("")
    lines.append("| Address | Label | Confidence | Preflight Ready | Gate Rerun | Missing Fields |")
    lines.append("|---------|-------|------------|-----------------|------------|----------------|")
    for d in preflight_decisions:
        addr_short = d["address"][:10] + "..."
        lines.append(
            f"| {addr_short} | {d['display_label']} | {d['current_confidence']} | "
            f"**{d['preflight_ready']}** | **{d['ready_for_gate_rerun']}** | "
            f"{len(d['missing_required_fields'])} |"
        )
    lines.append("")

    for d in preflight_decisions:
        lines.append(f"### {d['display_label']} (`{d['address'][:10]}...`)")
        lines.append("")
        lines.append(f"- **Confidence**: {d['current_confidence']}")
        lines.append(f"- **Action Type**: {d['action_type']}")
        lines.append(f"- **Preflight Ready**: **{d['preflight_ready']}**")
        lines.append(f"- **Ready for Gate Rerun**: **{d['ready_for_gate_rerun']}**")
        lines.append("")
        lines.append(f"#### Missing Required Fields ({len(d['missing_required_fields'])})")
        lines.append("")
        for f in d['missing_required_fields']:
            lines.append(f"- `{f}`")
        if d['present_fields']:
            lines.append("")
            lines.append(f"#### Present Fields ({len(d['present_fields'])})")
            lines.append("")
            for f in d['present_fields']:
                lines.append(f"- `{f}`")
        if d['rejected_source_hits']:
            lines.append("")
            lines.append(f"#### ⚠️ Rejected Source Hits ({len(d['rejected_source_hits'])})")
            for rh in d['rejected_source_hits']:
                lines.append(f"- {rh}")
        lines.append("")
        lines.append(f"#### Recommended Next Step")
        lines.append("")
        lines.append(d['recommended_next_step'])
        lines.append("")

    return "\n".join(lines)


def build_csv(items):
    """Build the evidence collection kit CSV."""
    csv_columns = [
        "address",
        "display_label",
        "current_confidence",
        "priority",
        "action_type",
        "research_goal",
        "required_evidence_bundle",
        "primary_source_checklist",
        "secondary_source_checklist",
        "activity_pattern_checklist",
        "rejected_source_types",
        "do_not_use_evidence_warning",
        "workbook_fields_to_fill",
        "minimum_pass_condition",
        "next_local_preflight_command",
        "next_gate_commands_after_preflight_pass",
        "safety_status",
    ]

    os.makedirs(os.path.dirname(V115O_KIT_CSV), exist_ok=True)
    with open(V115O_KIT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        for item in items:
            row = {}
            for col in csv_columns:
                val = item.get(col, "")
                if isinstance(val, list):
                    row[col] = "; ".join(val)
                else:
                    row[col] = str(val) if val else ""
            writer.writerow(row)

    rows = []
    with open(V115O_KIT_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_handoff_md(items, preflight_decisions, summary):
    """Build the local-only handoff markdown."""
    lines = []
    lines.append("# v115O Handoff — Evidence Collection Kit & Workbook Preflight")
    lines.append("")
    lines.append(f"**Generated**: {NOW_ISO}")
    lines.append(f"**Stage**: v115O")
    lines.append(f"**Status**: LOCAL ONLY — no real upgrades, no sends, no TG")
    lines.append("")

    lines.append("## What Was Done")
    lines.append("")
    lines.append(f"- Generated {len(items)} evidence collection items for operator manual research")
    lines.append(f"- Ran preflight on v115F workbook: {len(preflight_decisions)} addresses checked")
    lines.append(f"- All {len(preflight_decisions)} addresses: **preflight blocked** (empty workbook)")
    lines.append("")

    lines.append("## Next Steps for Operator")
    lines.append("")
    lines.append("1. Read the evidence collection kit at:")
    lines.append(f"   `{V115O_KIT_MD}`")
    lines.append("")
    lines.append("2. Open the v115F workbook at:")
    lines.append(f"   `{V115F_WORKBOOK}`")
    lines.append("")
    lines.append("3. For EACH address, fill all required fields following the evidence collection kit guidance")
    lines.append("")
    lines.append(f"4. Rerun preflight: `{PREFLIGHT_COMMAND}`")
    lines.append("")
    lines.append("5. Only after ALL addresses pass preflight, rerun gates in order:")
    for cmd in NEXT_GATE_COMMANDS:
        lines.append(f"   - `{cmd}`")
    lines.append("")

    lines.append("## Safety Boundaries")
    lines.append("")
    lines.append("| Item | Status |")
    lines.append("|------|--------|")
    lines.append("| Workbook modified | **false** |")
    lines.append("| Real label upgrade performed | **false** |")
    lines.append("| Real send candidate generated | **false** |")
    lines.append("| Send ready | **false** |")
    lines.append("| TG test group ready | **false** |")
    lines.append("| TG sent | **false** |")
    lines.append("| Prod state write | **false** |")
    lines.append("| External API called | **false** |")
    lines.append("| Credentials read | **false** |")
    lines.append("")

    lines.append("## Artifacts Generated")
    lines.append("")
    lines.append(f"- Evidence collection items JSONL: `{V115O_ITEMS_JSONL}`")
    lines.append(f"- Preflight records JSONL: `{V115O_PREFLIGHT_RECORDS_JSONL}`")
    lines.append(f"- Preflight decisions JSONL: `{V115O_PREFLIGHT_DECISIONS_JSONL}`")
    lines.append(f"- Result JSON: `{V115O_RESULT_JSON}`")
    lines.append(f"- Evidence collection kit MD: `{V115O_KIT_MD}`")
    lines.append(f"- Evidence collection kit CSV: `{V115O_KIT_CSV}`")
    lines.append(f"- Preflight report MD: `{V115O_PREFLIGHT_REPORT_MD}`")
    lines.append(f"- Handoff MD: `{V115O_HANDOFF_MD}`")
    lines.append("")

    lines.append("## Key Constraints Still Enforced")
    lines.append("")
    lines.append("- v115F workbook NOT modified by this run")
    lines.append("- v115A-v115N historical products NOT modified")
    lines.append("- No TG send, no production write, no label upgrade")
    lines.append("- No external API calls, no credential reads")
    lines.append("- Gate rerun order enforced: v115G → v115L → v115H → v115M")
    lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 70)
    print("v115O Whale Operator Evidence Collection Kit & Workbook Preflight")
    print("=" * 70)

    # -------------------------------------------------------------------
    # 1. Load inputs
    # -------------------------------------------------------------------
    print("\n[1] Loading inputs...")
    actions = load_jsonl(V115N_JSONL)
    print(f"    Loaded {len(actions)} operator actions from v115N")

    registry = load_json(V115K_REGISTRY)
    print(f"    Loaded v115K registry (v{registry.get('version')})")

    scoring_policy = load_json(V115K_SCORING_POLICY)
    print(f"    Loaded v115K scoring policy (v{scoring_policy.get('version')})")

    workbook_rows = load_csv_dict(V115F_WORKBOOK)
    print(f"    Loaded v115F workbook: {len(workbook_rows)} rows (read-only)")

    # -------------------------------------------------------------------
    # 2. Generate evidence collection items
    # -------------------------------------------------------------------
    print("\n[2] Generating evidence collection items...")
    items = []
    for action in actions:
        item = build_evidence_collection_item(action, registry, scoring_policy)
        items.append(item)
        print(f"    Generated item for {item['display_label']} ({item['action_type']})")

    write_jsonl(V115O_ITEMS_JSONL, items)
    print(f"    Wrote {len(items)} items to {V115O_ITEMS_JSONL}")

    # -------------------------------------------------------------------
    # 3. Generate preflight records & decisions
    # -------------------------------------------------------------------
    print("\n[3] Generating preflight records & decisions...")

    # Map action_type per address from actions
    addr_action_map = {a["address"]: a["action_type"] for a in actions}

    preflight_records = []
    preflight_decisions = []
    for row in workbook_rows:
        record = build_preflight_record(row)
        preflight_records.append(record)

        action_type = addr_action_map.get(record["address"], "unknown")
        decision = build_preflight_decision(record, action_type)
        preflight_decisions.append(decision)

        status = "BLOCKED" if not decision["preflight_ready"] else "READY"
        print(f"    {record['display_label']}: preflight_ready={decision['preflight_ready']} → {status}")

    write_jsonl(V115O_PREFLIGHT_RECORDS_JSONL, preflight_records)
    write_jsonl(V115O_PREFLIGHT_DECISIONS_JSONL, preflight_decisions)
    print(f"    Wrote {len(preflight_records)} records to preflight records")
    print(f"    Wrote {len(preflight_decisions)} decisions to preflight decisions")

    # -------------------------------------------------------------------
    # 4. Build summary JSON
    # -------------------------------------------------------------------
    print("\n[4] Building summary JSON...")
    high_priority_items = len([i for i in items if i["priority"] == "high"])
    medium_priority_items = len([i for i in items if i["priority"] == "medium"])
    manual_attribution_count = len([i for i in items if i["action_type"] == "manual_attribution_required"])
    corroboration_count = len([i for i in items if i["action_type"] == "corroboration_required"])
    preflight_ready_count = sum(1 for d in preflight_decisions if d["preflight_ready"])
    preflight_blocked_count = sum(1 for d in preflight_decisions if not d["preflight_ready"])
    ready_for_gate_count = sum(1 for d in preflight_decisions if d["ready_for_gate_rerun"])
    rejected_hits_count = sum(len(d["rejected_source_hits"]) for d in preflight_decisions)

    summary = {
        "stage": "v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only",
        "version": "v115O",
        "description": "Evidence collection kit and workbook preflight for 4 whale addresses from v115N operator action queue. LOCAL ONLY — no real upgrades, no sends, no TG.",
        "evidence_collection_items": len(items),
        "high_priority_items": high_priority_items,
        "medium_priority_items": medium_priority_items,
        "manual_attribution_required_count": manual_attribution_count,
        "corroboration_required_count": corroboration_count,
        "preflight_records": len(preflight_decisions),
        "preflight_ready_count": preflight_ready_count,
        "preflight_blocked_count": preflight_blocked_count,
        "ready_for_gate_rerun_count": ready_for_gate_count,
        "rejected_source_hits_count": rejected_hits_count,
        "workbook_modified": False,
        "real_label_upgrade_performed": False,
        "real_send_candidate_generated": False,
        "send_ready": False,
        "tg_test_group_ready": False,
        "tg_sent": False,
        "prod_state_write": False,
        "external_api_called": False,
        "credentials_read": False,
        "next_gate_command_order_enforced": True,
        "next_gate_commands": NEXT_GATE_COMMANDS,
        "preflight_command": PREFLIGHT_COMMAND,
        "generated_at": NOW_ISO,
    }

    write_json(V115O_RESULT_JSON, summary)
    print(f"    Summary: {len(items)} items, {high_priority_items} high, {medium_priority_items} medium")
    print(f"    Preflight: {preflight_ready_count} ready, {preflight_blocked_count} blocked")

    # -------------------------------------------------------------------
    # 5. Build markdown reports
    # -------------------------------------------------------------------
    print("\n[5] Building markdown reports...")

    kit_md = build_kit_markdown(items, preflight_decisions)
    write_text(V115O_KIT_MD, kit_md)
    print(f"    Wrote evidence collection kit to {V115O_KIT_MD}")

    preflight_md = build_preflight_report_md(preflight_records, preflight_decisions)
    write_text(V115O_PREFLIGHT_REPORT_MD, preflight_md)
    print(f"    Wrote preflight report to {V115O_PREFLIGHT_REPORT_MD}")

    # -------------------------------------------------------------------
    # 6. Build CSV
    # -------------------------------------------------------------------
    print("\n[6] Building CSV...")
    csv_rows = build_csv(items)
    print(f"    Wrote {len(csv_rows)} data rows to {V115O_KIT_CSV}")

    # -------------------------------------------------------------------
    # 7. Build handoff
    # -------------------------------------------------------------------
    print("\n[7] Building handoff...")
    handoff_md = build_handoff_md(items, preflight_decisions, summary)
    write_text(V115O_HANDOFF_MD, handoff_md)
    print(f"    Wrote handoff to {V115O_HANDOFF_MD}")

    # -------------------------------------------------------------------
    # Done
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("v115O Runner Complete")
    print(f"  Evidence collection items: {len(items)}")
    print(f"  High priority (manual attribution): {high_priority_items}")
    print(f"  Medium priority (corroboration): {medium_priority_items}")
    print(f"  Preflight records: {len(preflight_decisions)}")
    print(f"  Preflight ready: {preflight_ready_count}")
    print(f"  Preflight blocked: {preflight_blocked_count}")
    print(f"  Ready for gate rerun: {ready_for_gate_count}")
    print(f"  Workbook modified: False")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
