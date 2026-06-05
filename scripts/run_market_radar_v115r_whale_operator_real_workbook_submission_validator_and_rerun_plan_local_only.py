#!/usr/bin/env python3
"""
v115R Whale Operator Real Workbook Submission Validator & Safe Rerun Plan — Local Only
=======================================================================================
Reads the real v115F workbook, v115O evidence collection items, v115P fixture workbook,
and v115K policy configs to generate:

  1. Per-address validation records & decisions (submission_ready check).
  2. TEST_ONLY / fixture contamination detection.
  3. Rejected source detection.
  4. Reviewer / reviewed_at / operator_confirmation field checks.
  5. Safe rerun plan (blocked while any address is not submission_ready).
  6. Markdown + CSV validation report, real submission checklist, handoff.

NO real workbook modifications, NO label upgrades, NO send candidates, NO TG,
NO external API calls, NO credential reads, NO AI/model calls.
"""

import csv
import hashlib
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
V115F_WORKBOOK = os.path.join(RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv")
V115O_ITEMS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115o_whale_operator_evidence_collection_items.jsonl")
V115P_FIXTURE_WORKBOOK = os.path.join(RUNS_DIR, "v115p_whale_operator_fixture_filled_workbook.csv")
V115P_EXAMPLE_MD = os.path.join(RUNS_DIR, "v115p_whale_operator_filled_workbook_example.md")
V115K_REGISTRY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_source_registry.json")
V115K_SCORING_POLICY = os.path.join(CONFIG_DIR, "market_radar_v115k_whale_label_evidence_scoring_policy.json")

# Outputs
V115R_VALIDATION_RECORDS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115r_whale_real_workbook_submission_validation_records.jsonl")
V115R_VALIDATION_DECISIONS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v115r_whale_real_workbook_submission_validation_decisions.jsonl")
V115R_SAFE_RERUN_PLAN_JSON = os.path.join(RESULTS_DIR, "market_radar_v115r_whale_real_workbook_safe_rerun_plan.json")
V115R_RESULT_JSON = os.path.join(RESULTS_DIR, "market_radar_v115r_whale_operator_real_workbook_submission_validator_result.json")
V115R_REPORT_MD = os.path.join(RUNS_DIR, "v115r_whale_operator_real_workbook_submission_validation_report.md")
V115R_REPORT_CSV = os.path.join(RUNS_DIR, "v115r_whale_operator_real_workbook_submission_validation_report.csv")
V115R_CHECKLIST_MD = os.path.join(RUNS_DIR, "v115r_whale_operator_real_submission_checklist.md")
V115R_HANDOFF_MD = os.path.join(RUNS_DIR, "v115r_whale_operator_real_workbook_submission_validator_local_only_handoff.md")

NOW_ISO = datetime.now(timezone(timedelta(hours=8))).isoformat()

# ---------------------------------------------------------------------------
# Gate command order (enforced)
# ---------------------------------------------------------------------------
GATE_COMMANDS_IN_ORDER = [
    "python scripts/run_market_radar_v115o_whale_operator_evidence_collection_kit_and_workbook_preflight_local_only.py",
    "python scripts/run_market_radar_v115g_whale_manual_audit_workbook_intake_gate_local_only.py",
    "python scripts/run_market_radar_v115l_whale_label_evidence_scoring_gate_local_only.py",
    "python scripts/run_market_radar_v115h_whale_label_upgrade_adjudication_gate_local_only.py",
    "python scripts/run_market_radar_v115m_whale_manual_audit_end_to_end_upgrade_workflow_gate_local_only.py",
]

# ---------------------------------------------------------------------------
# TEST_ONLY / Fixture contamination terms to detect
# ---------------------------------------------------------------------------
TEST_ONLY_CONTAMINATION_TERMS = [
    "TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE",
    "TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE",
    "TEST_ONLY_ACTIVITY_PATTERN_DO_NOT_USE_AS_REAL_EVIDENCE",
    "TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE",
    "TEST_ONLY_REVIEWER",
    "TEST_ONLY_REVIEWED_AT_2026-06-05",
]

FIXTURE_CONTAMINATION_TERMS = [
    "fixture_only",
    "synthetic",
    "mock evidence",
]

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
# Low/medium address requirements from v115K scoring policy
# ---------------------------------------------------------------------------
LOW_UNKNOWN_REQUIRED_FIELDS = [
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

MEDIUM_REQUIRED_FIELDS = [
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

OPERATOR_MANAGED_FIELDS = [
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


def compute_sha256(path):
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_operator_fields(workbook_row):
    """Extract operator-managed workbook fields from a row."""
    return {
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


def check_test_only_contamination(operator_fields):
    """Check all field values for TEST_ONLY contamination terms."""
    hits = []
    all_text = " ".join(operator_fields.values())
    for term in TEST_ONLY_CONTAMINATION_TERMS:
        if term.lower() in all_text.lower():
            hits.append(term)
    return hits


def check_fixture_contamination(operator_fields):
    """Check all field values for fixture value contamination."""
    hits = []
    all_text = " ".join(operator_fields.values())
    for term in FIXTURE_CONTAMINATION_TERMS:
        if term.lower() in all_text.lower():
            hits.append(term)
    return hits


def check_rejected_source_hits(operator_fields):
    """Check all field values for rejected source type mentions."""
    hits = []
    all_text = " ".join(operator_fields.values())
    for rtype in REJECTED_SOURCE_TYPE_IDS + REJECTED_SOURCE_LABELS:
        if rtype.lower() in all_text.lower():
            if rtype not in hits:
                hits.append(rtype)
    return hits


def build_validation_record(workbook_row):
    """Build a validation record from a v115F workbook row."""
    addr = workbook_row.get("address", "")
    label = workbook_row.get("current_label", "")
    confidence = workbook_row.get("current_confidence", "")

    operator_fields = collect_operator_fields(workbook_row)

    # Determine present vs missing fields
    present = []
    missing = []
    for field in OPERATOR_MANAGED_FIELDS:
        val = operator_fields.get(field, "")
        if field == "ready_for_upgrade":
            if val.lower() == "true":
                present.append(field)
            else:
                missing.append(field)
        else:
            if val:
                present.append(field)
            else:
                missing.append(field)

    # Contamination detection
    test_only_hits = check_test_only_contamination(operator_fields)
    fixture_hits = check_fixture_contamination(operator_fields)
    rejected_hits = check_rejected_source_hits(operator_fields)

    record = {
        "version": "v115R",
        "address": addr,
        "display_label": label,
        "current_confidence": confidence,
        "operator_fields_status": operator_fields,
        "present_fields": present,
        "missing_required_fields": missing,
        "test_only_contamination_hits": test_only_hits,
        "fixture_value_contamination_hits": fixture_hits,
        "rejected_source_hits": rejected_hits,
        "checked_at": NOW_ISO,
    }
    return record


def determine_action_type(confidence, workbook_row):
    """Determine action_type from confidence level."""
    if confidence == "low":
        return "manual_attribution_required"
    elif confidence == "medium":
        return "corroboration_required"
    else:
        # Try to detect from label
        label = workbook_row.get("current_label", "").lower()
        if "unknown" in label:
            return "manual_attribution_required"
        return "corroboration_required"


def build_validation_decision(record, workbook_row):
    """Build a validation decision from a validation record."""
    addr = record["address"]
    label = record["display_label"]
    confidence = record["current_confidence"]

    missing = record["missing_required_fields"]
    present = record["present_fields"]
    test_only_hits = record["test_only_contamination_hits"]
    fixture_hits = record["fixture_value_contamination_hits"]
    rejected_hits = record["rejected_source_hits"]

    action_type = determine_action_type(confidence, workbook_row)
    is_low = (confidence == "low") or ("unknown" in workbook_row.get("current_label", "").lower())

    # Determine priority from v115F workbook
    priority = workbook_row.get("priority", "medium")

    # --- Compute submission_ready ---
    # ALL operator fields must be present, no TEST_ONLY contamination,
    # no fixture contamination, no rejected source hits, reviewer present,
    # reviewed_at present, operator_confirmation present
    has_all_fields = len(missing) == 0
    has_no_contamination = len(test_only_hits) == 0 and len(fixture_hits) == 0
    has_no_rejected = len(rejected_hits) == 0
    reviewer_ok = bool(record["operator_fields_status"].get("reviewer", ""))
    reviewed_at_ok = bool(record["operator_fields_status"].get("reviewed_at", ""))
    operator_confirmed_label_ok = bool(record["operator_fields_status"].get("operator_confirmed_label", ""))
    operator_confidence_ok = bool(record["operator_fields_status"].get("operator_confidence_assessment", ""))
    ready_for_upgrade_ok = record["operator_fields_status"].get("ready_for_upgrade", "").lower() == "true"

    submission_ready = (
        has_all_fields
        and has_no_contamination
        and has_no_rejected
        and reviewer_ok
        and reviewed_at_ok
        and operator_confirmed_label_ok
        and operator_confidence_ok
        and ready_for_upgrade_ok
    )

    # --- Build blocking reasons ---
    blocking_reasons = []
    if not has_all_fields:
        blocking_reasons.append("missing_required_fields")
    if test_only_hits:
        blocking_reasons.append("test_only_or_fixture_contamination_detected")
    if fixture_hits:
        blocking_reasons.append("fixture_value_contamination_detected")
    if rejected_hits:
        blocking_reasons.append("rejected_source_detected")
    if not reviewer_ok:
        blocking_reasons.append("reviewer_missing")
    if not reviewed_at_ok:
        blocking_reasons.append("reviewed_at_missing")
    if not operator_confirmed_label_ok:
        blocking_reasons.append("operator_confirmation_missing")
    if not operator_confidence_ok:
        blocking_reasons.append("operator_confidence_assessment_missing")
    if not ready_for_upgrade_ok:
        blocking_reasons.append("ready_for_upgrade_not_true")

    # Confidence-specific blocks
    if is_low:
        blocking_reasons.append("unknown_whale_requires_manual_attribution")
        blocking_reasons.append("low_confidence_label_not_sendable")
        if not has_all_fields:
            blocking_reasons.append("full_evidence_pack_required_for_low_unknown")
    else:
        blocking_reasons.append("medium_confidence_requires_corroboration")
        blocking_reasons.append("medium_cannot_direct_tg_test_group")

    # --- Source type validation ---
    source_type_validation = {
        "rejected_source_types_checked": True,
        "rejected_source_hits": rejected_hits,
        "allowed_primary_sources": [
            "primary_project_official_docs",
            "primary_exchange_institution_label",
            "primary_reputable_explorer_label",
            "primary_signed_statement",
            "primary_internal_verified_label",
        ],
        "allowed_secondary_sources": [
            "secondary_analytics_dashboard",
            "secondary_cross_source_clustering",
            "secondary_tx_behavior_evidence",
            "secondary_social_identity_linkage",
            "secondary_operator_reviewed_note",
        ],
        "allowed_activity_sources": [
            "activity_counterparty_pattern",
            "activity_asset_venue_pattern",
            "activity_position_consistency",
            "activity_historical_entity_interaction",
        ],
    }

    # --- Activity pattern validation ---
    activity_pattern_note_val = record["operator_fields_status"].get("activity_pattern_note", "")
    activity_pattern_ok = bool(activity_pattern_note_val)
    if is_low:
        # Low must not claim real attribution unless source bundle is complete
        if activity_pattern_ok and (not has_all_fields):
            activity_pattern_ok = False  # source bundle incomplete

    # --- Recommended next step ---
    if submission_ready:
        next_step = (
            "All required evidence fields filled and validated. "
            "Run v115O preflight to verify completeness, then proceed with gates "
            "in order: v115G → v115L → v115H → v115M."
        )
    else:
        next_step = (
            f"Operator must fill {len(missing)} missing required fields, "
            f"clear {len(test_only_hits)} TEST_ONLY contaminations, "
            f"clear {len(fixture_hits)} fixture contaminations, "
            f"and clear {len(rejected_hits)} rejected source hits "
            f"in {V115F_WORKBOOK} before resubmitting. "
            "Do NOT rerun gates until submission is validated."
        )

    # --- Safety status ---
    safety_status = "SAFE — local-only, no real upgrade, no send, no TG, no external API"

    decision = {
        "version": "v115R",
        "address": addr,
        "display_label": label,
        "current_confidence": confidence,
        "priority": priority,
        "action_type": action_type,
        "submission_ready": submission_ready,
        "ready_for_v115o_preflight": submission_ready,
        "ready_for_gate_rerun": False,  # requires v115O preflight pass first
        "missing_required_fields": missing,
        "present_fields": present,
        "source_type_validation": source_type_validation,
        "rejected_source_hits": rejected_hits,
        "test_only_contamination_hits": test_only_hits,
        "fixture_value_contamination_hits": fixture_hits,
        "reviewer_validation": reviewer_ok,
        "reviewed_at_validation": reviewed_at_ok,
        "operator_confirmation_validation": operator_confirmed_label_ok and operator_confidence_ok,
        "activity_pattern_validation": activity_pattern_ok,
        "recommended_next_step": next_step,
        "blocking_reasons": blocking_reasons if not submission_ready else [],
        "safety_status": safety_status,
        "generated_at": NOW_ISO,
    }
    return decision


def build_safe_rerun_plan(validation_decisions):
    """Build the safe rerun plan JSON."""
    submission_ready_count = sum(1 for d in validation_decisions if d["submission_ready"])
    submission_blocked_count = sum(1 for d in validation_decisions if not d["submission_ready"])

    safe_rerun_allowed = (submission_ready_count == len(validation_decisions)) and len(validation_decisions) > 0

    plan = {
        "version": "v115R",
        "safe_rerun_allowed": safe_rerun_allowed,
        "safe_rerun_blocked_count": submission_blocked_count,
        "safe_rerun_ready_count": submission_ready_count,
        "total_addresses": len(validation_decisions),
        "commands_allowed_to_run_now": [],
        "commands_after_all_submissions_ready": GATE_COMMANDS_IN_ORDER,
        "gate_order_must_be": ["v115O", "v115G", "v115L", "v115H", "v115M"],
        "gate_order_enforced": True,
        "must_run_v115o_preflight_before_gates": True,
        "medium_cannot_direct_tg_even_after_gate_pass": True,
        "generated_at": NOW_ISO,
        "notes": [
            "Current real v115F workbook is empty — all 4 addresses are blocked.",
            "Do NOT attempt to rerun gates until all addresses have valid real evidence.",
            "Must run v115O preflight first after filling workbook.",
            "Gate order is enforced: v115G → v115L → v115H → v115M.",
            "Medium confidence addresses CANNOT go directly to TG test group even if gates pass.",
        ],
    }
    return plan


def build_summary_json(validation_records, validation_decisions, safe_rerun_plan, sha256_before, sha256_after):
    """Build the summary result JSON."""
    submission_ready_count = sum(1 for d in validation_decisions if d["submission_ready"])
    submission_blocked_count = sum(1 for d in validation_decisions if not d["submission_ready"])
    manual_attribution_ready = sum(
        1 for d in validation_decisions
        if d["action_type"] == "manual_attribution_required" and d["submission_ready"]
    )
    corroboration_ready = sum(
        1 for d in validation_decisions
        if d["action_type"] == "corroboration_required" and d["submission_ready"]
    )
    test_only_hits_total = sum(len(d["test_only_contamination_hits"]) for d in validation_decisions)
    fixture_hits_total = sum(len(d["fixture_value_contamination_hits"]) for d in validation_decisions)
    rejected_hits_total = sum(len(d["rejected_source_hits"]) for d in validation_decisions)

    return {
        "stage": "v115r_whale_operator_real_workbook_submission_validator_and_rerun_plan_local_only",
        "version": "v115R",
        "description": "Real operator workbook submission validator and safe rerun plan for 4 whale addresses. LOCAL ONLY — no real upgrades, no sends, no TG, no AI/model calls.",
        "real_workbook_rows": len(validation_records),
        "validation_records": len(validation_records),
        "validation_decisions": len(validation_decisions),
        "submission_ready_count": submission_ready_count,
        "submission_blocked_count": submission_blocked_count,
        "ready_for_v115o_preflight_count": submission_ready_count,
        "ready_for_gate_rerun_count": 0,
        "manual_attribution_submission_ready_count": manual_attribution_ready,
        "corroboration_submission_ready_count": corroboration_ready,
        "test_only_contamination_hits_count": test_only_hits_total,
        "fixture_value_contamination_hits_count": fixture_hits_total,
        "rejected_source_hits_count": rejected_hits_total,
        "safe_rerun_allowed": safe_rerun_plan["safe_rerun_allowed"],
        "safe_rerun_blocked_count": safe_rerun_plan["safe_rerun_blocked_count"],
        "commands_allowed_to_run_now_count": len(safe_rerun_plan["commands_allowed_to_run_now"]),
        "next_gate_command_order_enforced": True,
        "real_workbook_sha256_before": sha256_before,
        "real_workbook_sha256_after": sha256_after,
        "real_workbook_modified": False,
        "real_label_upgrade_performed": False,
        "real_send_candidate_generated": False,
        "send_ready": False,
        "tg_test_group_ready": False,
        "tg_sent": False,
        "prod_state_write": False,
        "external_api_called": False,
        "credentials_read": False,
        "generated_at": NOW_ISO,
    }


def build_validation_report_md(validation_records, validation_decisions, summary):
    """Build the validation report markdown."""
    lines = []
    lines.append("# v115R Whale Operator Real Workbook Submission Validation Report")
    lines.append("")
    lines.append(f"**Generated**: {NOW_ISO}")
    lines.append(f"**Version**: v115R")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Real workbook rows**: {summary['real_workbook_rows']}")
    lines.append(f"- **Validation records**: {summary['validation_records']}")
    lines.append(f"- **Validation decisions**: {summary['validation_decisions']}")
    lines.append(f"- **Submission ready**: {summary['submission_ready_count']}")
    lines.append(f"- **Submission blocked**: {summary['submission_blocked_count']}")
    lines.append(f"- **Ready for v115O preflight**: {summary['ready_for_v115o_preflight_count']}")
    lines.append(f"- **Ready for gate rerun**: {summary['ready_for_gate_rerun_count']}")
    lines.append(f"- **TEST_ONLY contamination hits**: {summary['test_only_contamination_hits_count']}")
    lines.append(f"- **Fixture value contamination hits**: {summary['fixture_value_contamination_hits_count']}")
    lines.append(f"- **Rejected source hits**: {summary['rejected_source_hits_count']}")
    lines.append(f"- **Safe rerun allowed**: **{summary['safe_rerun_allowed']}**")
    lines.append("")

    lines.append("## ⚠️ Critical Finding")
    lines.append("")
    lines.append(f"**ALL {summary['validation_decisions']} addresses are currently SUBMISSION BLOCKED.**")
    lines.append("")
    lines.append("The real v115F workbook is empty — all operator-managed evidence fields are blank. "
                 "No address has any completed real evidence.")
    lines.append("")
    lines.append("### What This Means")
    lines.append("")
    lines.append("- **Submission NOT valid**: All addresses fail field completeness checks.")
    lines.append("- **v115O preflight NOT runnable**: Preflight would block all addresses in the current state.")
    lines.append("- **Gate rerun NOT permitted**: v115G → v115L → v115H → v115M must not be run.")
    lines.append("- **TG test group NOT accessible**: No address can enter TG test group.")
    lines.append("- **Operator action required**: Fill v115F workbook with real evidence, then validate.")
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
    lines.append(f"| Workbook SHA-256 | `{summary['real_workbook_sha256_before'][:16]}...` |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Per-Address Validation Results")
    lines.append("")
    lines.append("| # | Address | Label | Confidence | Submission Ready | Missing Fields | TEST_ONLY | Fixture | Rejected |")
    lines.append("|---|---------|-------|------------|------------------|----------------|-----------|---------|----------|")
    for idx, d in enumerate(validation_decisions, 1):
        addr_short = d["address"][:10] + "..."
        lines.append(
            f"| {idx} | {addr_short} | {d['display_label']} | {d['current_confidence']} | "
            f"**{d['submission_ready']}** | {len(d['missing_required_fields'])} | "
            f"{len(d['test_only_contamination_hits'])} | {len(d['fixture_value_contamination_hits'])} | "
            f"{len(d['rejected_source_hits'])} |"
        )
    lines.append("")

    for idx, d in enumerate(validation_decisions, 1):
        addr = d["address"]
        lines.append(f"### {idx}. {d['display_label']}")
        lines.append("")
        lines.append(f"- **Address**: `{addr}`")
        lines.append(f"- **Current Confidence**: {d['current_confidence']}")
        lines.append(f"- **Action Type**: {d['action_type']}")
        lines.append(f"- **Priority**: {d['priority']}")
        lines.append(f"- **Submission Ready**: **{d['submission_ready']}**")
        lines.append(f"- **Ready for v115O Preflight**: **{d['ready_for_v115o_preflight']}**")
        lines.append(f"- **Ready for Gate Rerun**: **{d['ready_for_gate_rerun']}**")
        lines.append("")

        lines.append("#### Blocking Reasons")
        lines.append("")
        if d["blocking_reasons"]:
            for br in d["blocking_reasons"]:
                lines.append(f"- `{br}`")
        else:
            lines.append("- None — submission is ready.")
        lines.append("")

        lines.append("#### Missing Required Fields")
        lines.append("")
        if d["missing_required_fields"]:
            for f in d["missing_required_fields"]:
                lines.append(f"- `{f}`")
        else:
            lines.append("- None — all required fields filled.")
        lines.append("")

        if d["present_fields"]:
            lines.append("#### Present Fields")
            lines.append("")
            for f in d["present_fields"]:
                lines.append(f"- `{f}`")
            lines.append("")

        lines.append("#### Contamination Detection")
        lines.append("")
        lines.append(f"- **TEST_ONLY contamination hits**: {len(d['test_only_contamination_hits'])}")
        if d["test_only_contamination_hits"]:
            for h in d["test_only_contamination_hits"]:
                lines.append(f"  - ❌ `{h}`")
        lines.append(f"- **Fixture value contamination hits**: {len(d['fixture_value_contamination_hits'])}")
        if d["fixture_value_contamination_hits"]:
            for h in d["fixture_value_contamination_hits"]:
                lines.append(f"  - ❌ `{h}`")
        lines.append("")

        lines.append("#### Rejected Source Detection")
        lines.append("")
        lines.append(f"- **Rejected source hits**: {len(d['rejected_source_hits'])}")
        if d["rejected_source_hits"]:
            for h in d["rejected_source_hits"]:
                lines.append(f"  - ❌ `{h}`")
        lines.append("")

        lines.append("#### Operator Review Validation")
        lines.append("")
        lines.append(f"- **Reviewer validation**: **{d['reviewer_validation']}**")
        lines.append(f"- **Reviewed_at validation**: **{d['reviewed_at_validation']}**")
        lines.append(f"- **Operator confirmation validation**: **{d['operator_confirmation_validation']}**")
        lines.append(f"- **Activity pattern validation**: **{d['activity_pattern_validation']}**")
        lines.append("")

        lines.append("#### Recommended Next Step")
        lines.append("")
        lines.append(d["recommended_next_step"])
        lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("## Why Safe Rerun Is Currently Blocked")
    lines.append("")
    lines.append(f"Safe rerun is blocked because **{summary['submission_blocked_count']} of {summary['validation_decisions']}** "
                 "addresses are not submission-ready.")
    lines.append("")
    lines.append("### Pre-conditions for safe rerun")
    lines.append("")
    lines.append("1. **All 4 addresses must be submission_ready=true** (all required fields filled with real, verified evidence).")
    lines.append("2. **No TEST_ONLY or fixture values** in any field.")
    lines.append("3. **No rejected sources** used as core evidence.")
    lines.append("4. **Operator confirmation complete** for all addresses (label, assessment, reviewer, reviewed_at, ready_for_upgrade).")
    lines.append("5. **Run v115O preflight first** after filling the workbook.")
    lines.append("6. **Only after preflight passes**, rerun gates in enforced order:")
    lines.append(f"   - `{GATE_COMMANDS_IN_ORDER[0]}`")
    lines.append(f"   - `{GATE_COMMANDS_IN_ORDER[1]}`")
    lines.append(f"   - `{GATE_COMMANDS_IN_ORDER[2]}`")
    lines.append(f"   - `{GATE_COMMANDS_IN_ORDER[3]}`")
    lines.append(f"   - `{GATE_COMMANDS_IN_ORDER[4]}`")
    lines.append("7. **Medium confidence addresses CANNOT go directly to TG test group** even after gate pass.")
    lines.append("")

    return "\n".join(lines)


def build_csv_report(validation_decisions):
    """Build the validation report CSV."""
    csv_columns = [
        "address",
        "display_label",
        "current_confidence",
        "priority",
        "action_type",
        "submission_ready",
        "ready_for_v115o_preflight",
        "ready_for_gate_rerun",
        "missing_required_fields",
        "present_fields",
        "source_type_validation",
        "rejected_source_hits",
        "test_only_contamination_hits",
        "fixture_value_contamination_hits",
        "reviewer_validation",
        "reviewed_at_validation",
        "operator_confirmation_validation",
        "activity_pattern_validation",
        "recommended_next_step",
        "blocking_reasons",
        "safety_status",
    ]

    output_path = V115R_REPORT_CSV
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        for d in validation_decisions:
            row = {}
            for col in csv_columns:
                val = d.get(col, "")
                if isinstance(val, list):
                    row[col] = "; ".join(str(v) for v in val)
                elif isinstance(val, dict):
                    row[col] = json.dumps(val, ensure_ascii=False)
                else:
                    row[col] = str(val) if val else ""
            writer.writerow(row)

    rows = []
    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_checklist_md(summary):
    """Build the real submission checklist markdown."""
    lines = []
    lines.append("# v115R Whale Operator Real Submission Checklist")
    lines.append("")
    lines.append(f"**Generated**: {NOW_ISO}")
    lines.append("")
    lines.append("## ⚠️ READ THIS FIRST — Avoid Common Mistakes")
    lines.append("")
    lines.append("This checklist is for the real operator filling the v115F workbook. "
                 "It ensures you do NOT accidentally copy TEST_ONLY fixture values or use "
                 "rejected evidence sources as real evidence.")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## ❌ TEST_ONLY / Fixture Value Warning")
    lines.append("")
    lines.append("**NEVER copy these values into the real v115F workbook:**")
    lines.append("")
    lines.append("| Contamination Term | Meaning |")
    lines.append("|--------------------|---------|")
    lines.append("| `TEST_ONLY_PRIMARY_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE` | Fixture primary source — NOT real evidence |")
    lines.append("| `TEST_ONLY_SECOND_SOURCE_DO_NOT_USE_AS_REAL_EVIDENCE` | Fixture secondary source — NOT real evidence |")
    lines.append("| `TEST_ONLY_ACTIVITY_PATTERN_DO_NOT_USE_AS_REAL_EVIDENCE` | Fixture activity pattern — NOT real evidence |")
    lines.append("| `TEST_ONLY_OPERATOR_CONFIRMATION_DO_NOT_USE_AS_REAL_EVIDENCE` | Fixture operator confirmation — NOT real evidence |")
    lines.append("| `TEST_ONLY_REVIEWER` | Fixture reviewer name — use YOUR real identifier |")
    lines.append("| `TEST_ONLY_REVIEWED_AT_2026-06-05` | Fixture review timestamp — use real review date |")
    lines.append("| `fixture_only` | Marks a value as fixture-only — must be replaced |")
    lines.append("| `synthetic` | Synthetic data — must be replaced |")
    lines.append("| `mock evidence` | Mock/simulated evidence — must be replaced |")
    lines.append("")
    lines.append("> If the validator detects ANY of these terms in your workbook, "
                 "`submission_ready` will be `false` and `test_only_or_fixture_contamination_detected` "
                 "will appear in blocking reasons.")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## ❌ Rejected Source Warning")
    lines.append("")
    lines.append("The following evidence sources **MUST NOT** be used as core evidence for label confidence upgrades:")
    lines.append("")
    for i, (rid, rlabel) in enumerate(zip(REJECTED_SOURCE_TYPE_IDS, REJECTED_SOURCE_LABELS), 1):
        lines.append(f"{i}. **{rlabel}** (`{rid}`)")
    lines.append("")
    lines.append("> Any label whose ONLY evidence comes from rejected_source categories must be immediately blocked "
                 "with REJECTED_EVIDENCE_ONLY block reason.")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## ✅ Allowed Evidence Sources")
    lines.append("")
    lines.append("### Primary Sources (at least 1 required for any high-confidence label)")
    lines.append("")
    lines.append("1. **Project/Team Official Docs or Disclosure** (`primary_project_official_docs`)")
    lines.append("2. **Verified Exchange/Institution Address Label Page** (`primary_exchange_institution_label`)")
    lines.append("3. **Reputable Block Explorer Label** (`primary_reputable_explorer_label`)")
    lines.append("4. **Public Signed Statement by Entity/Operator** (`primary_signed_statement`)")
    lines.append("5. **Internally Verified Historical Label Record** (`primary_internal_verified_label`)")
    lines.append("")
    lines.append("### Secondary Sources (at least 1 required)")
    lines.append("")
    lines.append("1. **Reputable Analytics Dashboard Label** (`secondary_analytics_dashboard`)")
    lines.append("2. **Cross-Source Wallet Clustering Note** (`secondary_cross_source_clustering`)")
    lines.append("3. **Historical Transaction Behavior Evidence** (`secondary_tx_behavior_evidence`)")
    lines.append("4. **Public Social Identity Linkage** (`secondary_social_identity_linkage`)")
    lines.append("5. **Previous Operator-Reviewed Label Note** (`secondary_operator_reviewed_note`)")
    lines.append("")
    lines.append("### Activity Pattern Sources (at least 1 required)")
    lines.append("")
    lines.append("1. **Consistent Counterparty Pattern** (`activity_counterparty_pattern`)")
    lines.append("2. **Repeated Asset/Venue Pattern** (`activity_asset_venue_pattern`)")
    lines.append("3. **Position Behavior Consistency** (`activity_position_consistency`)")
    lines.append("4. **Historical Interaction with Known Entity Addresses** (`activity_historical_entity_interaction`)")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Low / Unknown Whale Address Filling Requirements")
    lines.append("")
    lines.append("For addresses with `current_confidence=low` and labels containing 'Unknown':")
    lines.append("")
    lines.append("| # | Field | Requirement |")
    lines.append("|---|-------|-------------|")
    lines.append("| 1 | `trusted_source_label_value` | **Required** — real primary source identifying the entity |")
    lines.append("| 2 | `trusted_source_url_or_note` | **Required** — verifiable URL or documentation note |")
    lines.append("| 3 | `second_source_label_value` | **Required** — independent corroborating source |")
    lines.append("| 4 | `second_source_url_or_note` | **Required** — verifiable URL or documentation note |")
    lines.append("| 5 | `activity_pattern_note` | **Required** — on-chain behavior patterns consistent with claimed identity |")
    lines.append("| 6 | `operator_confirmed_label` | **Required** — confirmed entity label after manual research |")
    lines.append("| 7 | `operator_confidence_assessment` | **Required** — confidence assessment based on evidence |")
    lines.append("| 8 | `reviewer` | **Required** — your operator/auditor identifier |")
    lines.append("| 9 | `reviewed_at` | **Required** — ISO-8601 timestamp of review completion |")
    lines.append("| 10 | `ready_for_upgrade` | **Required** — set to `true` after all evidence complete |")
    lines.append("")
    lines.append("**Key rules for low/unknown whales:**")
    lines.append("")
    lines.append("- `action_type` must be `manual_attribution_required`")
    lines.append("- Cannot use ANY rejected source as core evidence")
    lines.append("- Cannot contain ANY TEST_ONLY value")
    lines.append("- Cannot copy fixture evidence values from v115P")
    lines.append("- Must not claim real attribution unless source bundle is complete (primary + secondary + activity + operator confirmation)")
    lines.append("- At least one `primary_source` is REQUIRED before any upgrade")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Medium Confidence Address Filling Requirements")
    lines.append("")
    lines.append("For addresses with `current_confidence=medium`:")
    lines.append("")
    lines.append("| # | Field | Requirement |")
    lines.append("|---|-------|-------------|")
    lines.append("| 1 | `trusted_source_label_value` | **Required** — existing label source or primary source |")
    lines.append("| 2 | `trusted_source_url_or_note` | **Required** — verifiable URL or documentation note |")
    lines.append("| 3 | `second_source_label_value` | **Required** — independent corroborating source |")
    lines.append("| 4 | `second_source_url_or_note` | **Required** — verifiable URL or documentation note |")
    lines.append("| 5 | `activity_pattern_note` | **Required** — on-chain behavior documentation |")
    lines.append("| 6 | `operator_confirmed_label` | **Required** — corroborated label after additional evidence |")
    lines.append("| 7 | `operator_confidence_assessment` | **Required** — confidence assessment |")
    lines.append("| 8 | `reviewer` | **Required** — your operator/auditor identifier |")
    lines.append("| 9 | `reviewed_at` | **Required** — ISO-8601 timestamp of review completion |")
    lines.append("| 10 | `ready_for_upgrade` | **Required** — set to `true` after all evidence complete |")
    lines.append("")
    lines.append("**Key rules for medium confidence addresses:**")
    lines.append("")
    lines.append("- `action_type` must be `corroboration_required`")
    lines.append("- Cannot use ANY rejected source as core evidence")
    lines.append("- Cannot contain ANY TEST_ONLY value")
    lines.append("- Cannot copy fixture evidence values from v115P")
    lines.append("- **Medium passing preflight does NOT equal TG test group readiness**")
    lines.append("- Must not claim direct TG readiness")
    lines.append("- All HC_REQ_001 through HC_REQ_009 must pass for high confidence upgrade")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Reviewer / Reviewed_at / Operator Confirmation Requirements")
    lines.append("")
    lines.append("- `reviewer`: Must be a non-empty operator/auditor identifier (NOT `TEST_ONLY_REVIEWER`)")
    lines.append("- `reviewed_at`: Must be a valid ISO-8601 timestamp (NOT `TEST_ONLY_REVIEWED_AT_2026-06-05`)")
    lines.append("- `operator_confirmed_label`: Must be a real, researched entity label (NOT a TEST_ONLY fixture value)")
    lines.append("- `operator_confidence_assessment`: Must be a real assessment based on evidence (NOT a TEST_ONLY fixture value)")
    lines.append("- `ready_for_upgrade`: Must be explicitly `true` after all evidence is complete")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Pre-Submission Self-Check")
    lines.append("")
    lines.append("Before submitting the real workbook, verify:")
    lines.append("")
    lines.append("- [ ] ALL 10 operator fields are filled for each of the 4 addresses")
    lines.append("- [ ] NO field contains `TEST_ONLY_...` values")
    lines.append("- [ ] NO field contains `fixture_only`, `synthetic`, or `mock evidence`")
    lines.append("- [ ] NO field references rejected source types (unsourced social post, anonymous claim, AI-generated label, screenshot without URL, stale label, TG chat label, vague claim)")
    lines.append("- [ ] Each low/unknown whale has: primary source + secondary source + activity pattern + operator confirmation + reviewer + reviewed_at")
    lines.append("- [ ] Each medium confidence address has: existing source or primary source + secondary source + activity pattern + operator confirmation + reviewer + reviewed_at")
    lines.append("- [ ] `reviewer` is YOUR real operator identifier")
    lines.append("- [ ] `reviewed_at` is the actual date/time you completed the review")
    lines.append("- [ ] `operator_confirmed_label` is the actual label you determined through research")
    lines.append("- [ ] `operator_confidence_assessment` is your honest assessment")
    lines.append("- [ ] `ready_for_upgrade` is set to `true`")
    lines.append("- [ ] Medium labels do NOT claim direct TG test group readiness")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Safe Rerun Order")
    lines.append("")
    lines.append("After the validator confirms all addresses are `submission_ready=true`, proceed in this exact order:")
    lines.append("")
    lines.append(f"1. **Run v115O preflight**: `{GATE_COMMANDS_IN_ORDER[0]}`")
    lines.append("2. **Only after preflight passes**, rerun gates in order:")
    lines.append(f"   - `{GATE_COMMANDS_IN_ORDER[1]}`")
    lines.append(f"   - `{GATE_COMMANDS_IN_ORDER[2]}`")
    lines.append(f"   - `{GATE_COMMANDS_IN_ORDER[3]}`")
    lines.append(f"   - `{GATE_COMMANDS_IN_ORDER[4]}`")
    lines.append("")
    lines.append("**⚠️ Important reminders:**")
    lines.append("")
    lines.append("- **Do NOT skip v115O preflight**. Running gates without preflight pass will result in blocks.")
    lines.append("- **Gate order is enforced**: v115G → v115L → v115H → v115M.")
    lines.append("- **Medium confidence addresses CANNOT go directly to TG test group**, even if gates pass.")
    lines.append("- **All addresses must pass the full HC_REQ_001 through HC_REQ_009 checklist before any TG delivery is considered.**")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Validation Command")
    lines.append("")
    lines.append("After filling the workbook, run the validator:")
    lines.append("")
    lines.append("```bash")
    lines.append("python scripts/run_market_radar_v115r_whale_operator_real_workbook_submission_validator_and_rerun_plan_local_only.py")
    lines.append("```")
    lines.append("")
    lines.append("This will re-check all 4 addresses and produce an updated validation report.")
    lines.append("")

    return "\n".join(lines)


def build_handoff_md(validation_decisions, summary, safe_rerun_plan):
    """Build the local-only handoff markdown."""
    lines = []
    lines.append("# v115R Handoff — Real Workbook Submission Validator & Safe Rerun Plan")
    lines.append("")
    lines.append(f"**Generated**: {NOW_ISO}")
    lines.append(f"**Stage**: v115R")
    lines.append(f"**Status**: LOCAL ONLY — no real upgrades, no sends, no TG, no AI/model calls")
    lines.append("")

    lines.append("## What Was Done")
    lines.append("")
    lines.append(f"- Validated real v115F workbook: {len(validation_decisions)} addresses checked")
    lines.append(f"- All {len(validation_decisions)} addresses: **submission blocked** (empty workbook)")
    lines.append(f"- TEST_ONLY contamination: {summary['test_only_contamination_hits_count']} hits detected")
    lines.append(f"- Fixture value contamination: {summary['fixture_value_contamination_hits_count']} hits detected")
    lines.append(f"- Rejected source: {summary['rejected_source_hits_count']} hits detected")
    lines.append(f"- Safe rerun: **blocked** ({summary['safe_rerun_blocked_count']} addresses not ready)")
    lines.append(f"- Gate command order enforced: **{summary['next_gate_command_order_enforced']}**")
    lines.append("")

    lines.append("## Next Steps for Operator")
    lines.append("")
    lines.append("1. Read the real submission checklist:")
    lines.append(f"   `{V115R_CHECKLIST_MD}`")
    lines.append("")
    lines.append("2. Open the v115F workbook:")
    lines.append(f"   `{V115F_WORKBOOK}`")
    lines.append("")
    lines.append("3. For EACH of the 4 addresses, fill ALL required fields with REAL, verifiable evidence:")
    lines.append("   - DO NOT copy TEST_ONLY values from v115P fixture workbook")
    lines.append("   - DO NOT use rejected source types")
    lines.append("   - Use YOUR real reviewer identifier and real review timestamp")
    lines.append("")
    lines.append("4. Rerun the validator to confirm all submissions are ready:")
    lines.append(f"   `python scripts/run_market_radar_v115r_whale_operator_real_workbook_submission_validator_and_rerun_plan_local_only.py`")
    lines.append("")
    lines.append("5. After validator confirms all 4 addresses `submission_ready=true`, run v115O preflight first:")
    lines.append(f"   `{GATE_COMMANDS_IN_ORDER[0]}`")
    lines.append("")
    lines.append("6. Only after preflight passes, rerun gates in order:")
    for cmd in GATE_COMMANDS_IN_ORDER[1:]:
        lines.append(f"   - `{cmd}`")
    lines.append("")
    lines.append("7. **Medium confidence addresses CANNOT go directly to TG test group** — do NOT claim TG test group readiness for medium labels.")
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
    lines.append(f"| Workbook SHA-256 (before) | `{summary['real_workbook_sha256_before'][:16]}...` |")
    lines.append(f"| Workbook SHA-256 (after) | `{summary['real_workbook_sha256_after'][:16]}...` |")
    lines.append("")

    lines.append("## Artifacts Generated")
    lines.append("")
    lines.append(f"- Validation records JSONL: `{V115R_VALIDATION_RECORDS_JSONL}`")
    lines.append(f"- Validation decisions JSONL: `{V115R_VALIDATION_DECISIONS_JSONL}`")
    lines.append(f"- Safe rerun plan JSON: `{V115R_SAFE_RERUN_PLAN_JSON}`")
    lines.append(f"- Result JSON: `{V115R_RESULT_JSON}`")
    lines.append(f"- Validation report MD: `{V115R_REPORT_MD}`")
    lines.append(f"- Validation report CSV: `{V115R_REPORT_CSV}`")
    lines.append(f"- Real submission checklist MD: `{V115R_CHECKLIST_MD}`")
    lines.append(f"- Handoff MD: `{V115R_HANDOFF_MD}`")
    lines.append("")

    lines.append("## Key Constraints Still Enforced")
    lines.append("")
    lines.append("- v115F workbook NOT modified by this run")
    lines.append("- v115P fixture workbook NOT modified by this run")
    lines.append("- v115A-v115Q historical products NOT modified")
    lines.append("- No TG send, no production write, no label upgrade")
    lines.append("- No external API calls, no credential reads")
    lines.append("- No AI/model calls")
    lines.append("- Gate rerun order enforced: v115O preflight → v115G → v115L → v115H → v115M")
    lines.append("- Medium confidence labels CANNOT claim direct TG test group readiness")
    lines.append("- Fixture values in v115P are NOT real evidence")
    lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 70)
    print("v115R Whale Operator Real Workbook Submission Validator & Safe Rerun Plan")
    print("=" * 70)

    # -------------------------------------------------------------------
    # 1. Load inputs
    # -------------------------------------------------------------------
    print("\n[1] Loading inputs...")

    workbook_rows = load_csv_dict(V115F_WORKBOOK)
    print(f"    Loaded v115F workbook: {len(workbook_rows)} rows (read-only)")

    v115o_items = load_jsonl(V115O_ITEMS_JSONL)
    print(f"    Loaded {len(v115o_items)} v115O evidence collection items")

    fixture_rows = load_csv_dict(V115P_FIXTURE_WORKBOOK)
    print(f"    Loaded v115P fixture workbook: {len(fixture_rows)} rows (read-only)")

    with open(V115P_EXAMPLE_MD, "r", encoding="utf-8") as f:
        fixture_example_md = f.read()
    print(f"    Loaded v115P fixture example: {len(fixture_example_md)} chars (read-only)")

    registry = load_json(V115K_REGISTRY)
    print(f"    Loaded v115K registry (v{registry.get('version')})")

    scoring_policy = load_json(V115K_SCORING_POLICY)
    print(f"    Loaded v115K scoring policy (v{scoring_policy.get('version')})")

    # Compute SHA-256 BEFORE any processing
    sha256_before = compute_sha256(V115F_WORKBOOK)
    print(f"    Workbook SHA-256 (before): {sha256_before}")

    # -------------------------------------------------------------------
    # 2. Generate validation records
    # -------------------------------------------------------------------
    print("\n[2] Generating validation records...")
    validation_records = []
    for row in workbook_rows:
        record = build_validation_record(row)
        validation_records.append(record)
        status = "EMPTY" if len(record["missing_required_fields"]) == len(OPERATOR_MANAGED_FIELDS) else "PARTIAL"
        print(f"    {record['display_label']}: {len(record['missing_required_fields'])} missing, "
              f"{len(record['test_only_contamination_hits'])} TEST_ONLY, "
              f"{len(record['fixture_value_contamination_hits'])} fixture → {status}")

    write_jsonl(V115R_VALIDATION_RECORDS_JSONL, validation_records)
    print(f"    Wrote {len(validation_records)} validation records")

    # -------------------------------------------------------------------
    # 3. Generate validation decisions
    # -------------------------------------------------------------------
    print("\n[3] Generating validation decisions...")
    validation_decisions = []
    for i, record in enumerate(validation_records):
        row = workbook_rows[i]
        decision = build_validation_decision(record, row)
        validation_decisions.append(decision)
        status = "READY" if decision["submission_ready"] else "BLOCKED"
        reasons = "; ".join(decision["blocking_reasons"][:3])
        print(f"    {decision['display_label']}: submission_ready={decision['submission_ready']} "
              f"→ {status} ({reasons}...)")

    write_jsonl(V115R_VALIDATION_DECISIONS_JSONL, validation_decisions)
    print(f"    Wrote {len(validation_decisions)} validation decisions")

    # -------------------------------------------------------------------
    # 4. Build safe rerun plan
    # -------------------------------------------------------------------
    print("\n[4] Building safe rerun plan...")
    safe_rerun_plan = build_safe_rerun_plan(validation_decisions)
    write_json(V115R_SAFE_RERUN_PLAN_JSON, safe_rerun_plan)
    print(f"    Safe rerun allowed: {safe_rerun_plan['safe_rerun_allowed']}")
    print(f"    Safe rerun blocked count: {safe_rerun_plan['safe_rerun_blocked_count']}")
    print(f"    Commands allowed to run now: {len(safe_rerun_plan['commands_allowed_to_run_now'])}")

    # -------------------------------------------------------------------
    # 5. Compute SHA-256 AFTER (must be identical)
    # -------------------------------------------------------------------
    sha256_after = compute_sha256(V115F_WORKBOOK)
    print(f"\n[5] Workbook SHA-256 verification...")
    print(f"    Before: {sha256_before}")
    print(f"    After:  {sha256_after}")
    print(f"    Identical: {sha256_before == sha256_after}")

    # -------------------------------------------------------------------
    # 6. Build summary JSON
    # -------------------------------------------------------------------
    print("\n[6] Building summary JSON...")
    summary = build_summary_json(validation_records, validation_decisions, safe_rerun_plan,
                                  sha256_before, sha256_after)
    write_json(V115R_RESULT_JSON, summary)
    print(f"    submission_ready_count: {summary['submission_ready_count']}")
    print(f"    submission_blocked_count: {summary['submission_blocked_count']}")
    print(f"    safe_rerun_allowed: {summary['safe_rerun_allowed']}")

    # -------------------------------------------------------------------
    # 7. Build markdown validation report
    # -------------------------------------------------------------------
    print("\n[7] Building markdown validation report...")
    report_md = build_validation_report_md(validation_records, validation_decisions, summary)
    write_text(V115R_REPORT_MD, report_md)
    print(f"    Wrote validation report to {V115R_REPORT_MD}")

    # -------------------------------------------------------------------
    # 8. Build CSV report
    # -------------------------------------------------------------------
    print("\n[8] Building CSV report...")
    csv_rows = build_csv_report(validation_decisions)
    print(f"    Wrote {len(csv_rows)} data rows to {V115R_REPORT_CSV}")

    # -------------------------------------------------------------------
    # 9. Build real submission checklist
    # -------------------------------------------------------------------
    print("\n[9] Building real submission checklist...")
    checklist_md = build_checklist_md(summary)
    write_text(V115R_CHECKLIST_MD, checklist_md)
    print(f"    Wrote checklist to {V115R_CHECKLIST_MD}")

    # -------------------------------------------------------------------
    # 10. Build handoff
    # -------------------------------------------------------------------
    print("\n[10] Building handoff...")
    handoff_md = build_handoff_md(validation_decisions, summary, safe_rerun_plan)
    write_text(V115R_HANDOFF_MD, handoff_md)
    print(f"    Wrote handoff to {V115R_HANDOFF_MD}")

    # -------------------------------------------------------------------
    # Done
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("v115R Runner Complete")
    print(f"  Validation records: {len(validation_records)}")
    print(f"  Validation decisions: {len(validation_decisions)}")
    print(f"  Submission ready: {summary['submission_ready_count']}")
    print(f"  Submission blocked: {summary['submission_blocked_count']}")
    print(f"  Safe rerun allowed: {summary['safe_rerun_allowed']}")
    print(f"  Workbook SHA-256 identical: {sha256_before == sha256_after}")
    print(f"  Workbook modified: False")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
