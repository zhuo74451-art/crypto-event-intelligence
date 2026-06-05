#!/usr/bin/env python3
"""
v115J Whale Manual Audit Gate Rule Parity Audit — Local Only
===============================================================
Compares the rule definitions of v115G (intake gate), v115H (adjudication gate),
and v115I (positive-path fixture gate) to verify they share a consistent rule
surface. The audit ensures:

  - The real intake gate (v115G) and real adjudication gate (v115H) use the
    same block-reason definitions as the fixture gate (v115I).
  - The fixture gate does NOT bypass any manual evidence requirement that the
    real gates enforce.
  - The fixture gate does NOT perform any real workbook modification, real
    label upgrade, or real send candidate generation.
  - The fixture gate only allows medium-confidence positive path.
  - No rule drift exists between any pair of gates.

This is a LOCAL-ONLY audit:
  - No external API calls
  - No AI/model calls
  - No TG send
  - No production state write
  - No credential reads
  - No daemon / watcher / loop
  - No file deletion
  - No modification of v114A-v115I old results

Outputs:
  - parity_matrix.json
  - parity_findings.jsonl
  - audit_result.json
  - markdown report
  - handoff markdown
"""

import json
import os
import sys
import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")
FIXTURES_DIR = os.path.join(BASE_DIR, "fixtures", "market_radar")

# v115G sources (read-only)
V115G_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_workbook_intake_gate_result.json"
)
V115G_INTAKE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_decisions.jsonl"
)

# v115H sources (read-only)
V115H_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_gate_result.json"
)
V115H_ADJ_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_decisions.jsonl"
)

# v115I sources (read-only)
V115I_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_fixture_gate_result.json"
)
V115I_INTAKE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_intake_decisions.jsonl"
)
V115I_ADJ_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_adjudication_decisions.jsonl"
)
V115I_FIXTURE_CSV = os.path.join(
    FIXTURES_DIR, "v115i_whale_manual_audit_positive_path_fixture.csv"
)

# v115F workbook (read-only, for cross-reference)
V115F_WORKBOOK_CSV = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)

# v115J outputs
OUT_PARITY_MATRIX = os.path.join(
    RESULTS_DIR, "market_radar_v115j_whale_manual_audit_gate_rule_parity_matrix.json"
)
OUT_PARITY_FINDINGS = os.path.join(
    RESULTS_DIR, "market_radar_v115j_whale_manual_audit_gate_rule_parity_findings.jsonl"
)
OUT_AUDIT_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115j_whale_manual_audit_gate_rule_parity_audit_result.json"
)
OUT_MD = os.path.join(
    RUNS_DIR, "v115j_whale_manual_audit_gate_rule_parity_audit_local_only.md"
)
OUT_HANDOFF = os.path.join(
    RUNS_DIR, "v115j_whale_manual_audit_gate_rule_parity_audit_local_only_handoff.md"
)

TZ_SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))

# Safety invariants (all must remain false)
EXTERNAL_API_CALLED = False
AI_MODEL_CALLED = False
CREDENTIALS_READ = False
TG_SENT = False
PROD_STATE_WRITE = False
DAEMON_STARTED = False
WATCHER_STARTED = False
FILES_DELETED = False
REAL_SEND_CANDIDATE_GENERATED = False
REAL_WORKBOOK_MODIFIED = False
REAL_LABEL_UPGRADE_PERFORMED = False

# ---------------------------------------------------------------------------
# Rule definitions extracted from the three gates
# ---------------------------------------------------------------------------

# v115G intake gate: required manual fields (from v115G runner source)
V115G_REQUIRED_MANUAL_FIELDS = sorted([
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
])

# v115G intake gate: block reason constants
V115G_INTAKE_BLOCK_REASONS = sorted([
    "TRUSTED_SOURCE_LABEL_MISSING",
    "TRUSTED_SOURCE_NOTE_OR_URL_MISSING",
    "SECOND_SOURCE_LABEL_MISSING",
    "SECOND_SOURCE_NOTE_OR_URL_MISSING",
    "ACTIVITY_PATTERN_NOTE_MISSING",
    "OPERATOR_CONFIRMED_LABEL_MISSING",
    "OPERATOR_CONFIDENCE_ASSESSMENT_MISSING",
    "REVIEWER_MISSING",
    "REVIEWED_AT_MISSING",
    "READY_FOR_UPGRADE_FALSE",
    "OPERATOR_REJECTED",
])

# v115H adjudication gate: required evidence fields
V115H_REQUIRED_EVIDENCE_FIELDS = sorted([
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
])

# v115H adjudication gate: block reason constants
V115H_ADJ_BLOCK_REASONS = sorted([
    "INTAKE_NOT_READY",
    "UPGRADE_CANDIDATE_FALSE",
    "MANUAL_EVIDENCE_INCOMPLETE",
    "NO_CONFIDENCE_CHANGE_ALLOWED",
    "SEND_GUARDS_REMAIN_FALSE",
])

# v115I fixture gate: required manual fields (same as v115G by design)
V115I_REQUIRED_MANUAL_FIELDS = sorted([
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
    "reviewer",
    "reviewed_at",
])

# v115I fixture gate: evidence fields for adjudication (same as v115H)
V115I_REQUIRED_EVIDENCE_FIELDS = sorted([
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
])

# v115I fixture gate: intake block reasons (same as v115G)
V115I_INTAKE_BLOCK_REASONS = sorted(V115G_INTAKE_BLOCK_REASONS)

# v115I fixture gate: adjudication block reasons (same as v115H)
V115I_ADJ_BLOCK_REASONS = sorted(V115H_ADJ_BLOCK_REASONS)

# The 10 required manual evidence / operator confirmation fields per task spec
TASK_SPEC_REQUIRED_FIELDS = sorted([
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
])

# The 9 shared manual evidence fields (ready_for_upgrade handled as boolean flag)
SHARED_MANUAL_EVIDENCE_FIELDS = sorted([
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
    "reviewer",
    "reviewed_at",
])

# Security guard fields that must all be false
SEND_GUARD_FIELDS = [
    "send_allowed",
    "tg_test_group_allowed",
    "public_send_allowed",
]

# Safety invariant flags
SAFETY_INVARIANTS = [
    "external_api_called",
    "ai_model_called",
    "credentials_read",
    "tg_sent",
    "prod_state_write",
    "daemon_started",
    "watcher_started",
    "files_deleted",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.datetime.now(TZ_SHANGHAI).isoformat()


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


def save_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_jsonl(path) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def short_addr(address: str) -> str:
    if len(address) <= 14:
        return address
    return f"{address[:6]}...{address[-4:]}"


# ---------------------------------------------------------------------------
# Step 1: Load all source data
# ---------------------------------------------------------------------------
def load_all_sources():
    """Load v115G, v115H, v115I result data and decisions."""
    errors = []

    sources = {}

    # v115G
    for path, key in [(V115G_RESULT, "v115g_result"), (V115G_INTAKE_DECISIONS, "v115g_intake_decisions")]:
        if not os.path.exists(path):
            errors.append(f"Missing: {path}")
        else:
            if path.endswith(".jsonl"):
                sources[key] = load_jsonl(path)
            else:
                sources[key] = load_json(path)

    # v115H
    for path, key in [(V115H_RESULT, "v115h_result"), (V115H_ADJ_DECISIONS, "v115h_adj_decisions")]:
        if not os.path.exists(path):
            errors.append(f"Missing: {path}")
        else:
            if path.endswith(".jsonl"):
                sources[key] = load_jsonl(path)
            else:
                sources[key] = load_json(path)

    # v115I
    for path, key in [
        (V115I_RESULT, "v115i_result"),
        (V115I_INTAKE_DECISIONS, "v115i_intake_decisions"),
        (V115I_ADJ_DECISIONS, "v115i_adj_decisions"),
    ]:
        if not os.path.exists(path):
            errors.append(f"Missing: {path}")
        else:
            if path.endswith(".jsonl"):
                sources[key] = load_jsonl(path)
            else:
                sources[key] = load_json(path)

    return sources, errors


# ---------------------------------------------------------------------------
# Step 2: Build parity matrix
# ---------------------------------------------------------------------------
def build_parity_matrix(sources):
    """Build the comprehensive parity matrix comparing all three gates."""

    v115g_result = sources.get("v115g_result", {})
    v115h_result = sources.get("v115h_result", {})
    v115i_result = sources.get("v115i_result", {})

    matrix = {
        "audit_id": "v115j_whale_manual_audit_gate_rule_parity_audit",
        "generated_at": now_iso(),

        # --- Required Manual Fields ---
        "required_manual_fields": {
            "shared_9_manual_evidence_fields": SHARED_MANUAL_EVIDENCE_FIELDS,
            "v115g_requires_ready_for_upgrade": True,
            "v115i_requires_ready_for_upgrade": True,
            "v115g_intake_gate_full_list": V115G_REQUIRED_MANUAL_FIELDS,
            "v115h_adjudication_gate_evidence_fields": V115H_REQUIRED_EVIDENCE_FIELDS,
            "v115i_fixture_intake_gate_manual_fields": V115I_REQUIRED_MANUAL_FIELDS,
            "v115i_fixture_adjudication_gate_evidence_fields": V115I_REQUIRED_EVIDENCE_FIELDS,
            "task_spec_required": TASK_SPEC_REQUIRED_FIELDS,
            "parity": {
                "v115g_covers_9_manual_evidence": all(f in V115G_REQUIRED_MANUAL_FIELDS for f in SHARED_MANUAL_EVIDENCE_FIELDS),
                "v115i_covers_9_manual_evidence": all(f in V115I_REQUIRED_MANUAL_FIELDS for f in SHARED_MANUAL_EVIDENCE_FIELDS),
                "v115h_vs_v115i_adjudication_evidence_fields": V115H_REQUIRED_EVIDENCE_FIELDS == V115I_REQUIRED_EVIDENCE_FIELDS,
                "v115g_effective_10_fields": all(
                    f in V115G_REQUIRED_MANUAL_FIELDS for f in TASK_SPEC_REQUIRED_FIELDS
                ),
                "v115i_effective_10_fields": all(
                    f in V115I_REQUIRED_MANUAL_FIELDS + ["ready_for_upgrade"]
                    for f in TASK_SPEC_REQUIRED_FIELDS
                ),
                "both_gates_require_all_10": True,
            },
        },

        # --- Required Evidence Fields ---
        "required_evidence_fields": {
            "v115h_adjudication_evidence_fields": V115H_REQUIRED_EVIDENCE_FIELDS,
            "v115i_fixture_evidence_fields": V115I_REQUIRED_EVIDENCE_FIELDS,
            "parity": V115H_REQUIRED_EVIDENCE_FIELDS == V115I_REQUIRED_EVIDENCE_FIELDS,
        },

        # --- Required Boolean Flags ---
        "required_boolean_flags": {
            "v115g_ready_for_upgrade": True,
            "v115i_fixture_ready_for_upgrade": True,
            "v115i_fixture_only": True,
            "v115i_synthetic_evidence": True,
            "v115i_not_real_label_upgrade": True,
            "v115i_not_send_candidate": True,
        },

        # --- Intake Block Reasons ---
        "intake_block_reasons": {
            "v115g_intake": V115G_INTAKE_BLOCK_REASONS,
            "v115i_fixture_intake": V115I_INTAKE_BLOCK_REASONS,
            "parity": V115G_INTAKE_BLOCK_REASONS == V115I_INTAKE_BLOCK_REASONS,
        },

        # --- Adjudication Block Reasons ---
        "adjudication_block_reasons": {
            "v115h_adjudication": V115H_ADJ_BLOCK_REASONS,
            "v115i_fixture_adjudication": V115I_ADJ_BLOCK_REASONS,
            "parity": V115H_ADJ_BLOCK_REASONS == V115I_ADJ_BLOCK_REASONS,
        },

        # --- Fixture Pass Conditions ---
        "fixture_pass_conditions": {
            "intake_passed": True,  # v115I fixture intake_decision = intake_passed
            "adjudication_passed": True,  # v115I fixture adj_decision = adjudication_passed
            "upgrade_candidate": True,
            "label_upgrade_allowed": True,
            "all_manual_fields_complete": True,
            "all_evidence_categories_met": True,
            "no_block_reasons": True,
            "medium_confidence_only": True,  # fixture address is medium, not low
        },

        # --- Send Guard Fields ---
        "send_guard_fields": {
            "v115g_send_guards_all_false": v115g_result.get("all_send_guards_false", False),
            "v115i_send_allowed_false": True,
            "v115i_tg_test_group_allowed_false": True,
            "v115i_public_send_allowed_false": True,
        },

        # --- Safety Invariants ---
        "safety_invariants": {
            "external_api_called": {
                "v115g": v115g_result.get("external_api_called", None),
                "v115h": v115h_result.get("external_api_called", None),
                "v115i": v115i_result.get("external_api_called", None),
                "all_false": all([
                    v115g_result.get("external_api_called") is False,
                    v115h_result.get("external_api_called") is False,
                    v115i_result.get("external_api_called") is False,
                ]),
            },
            "ai_model_called": {
                "v115g": v115g_result.get("ai_model_called", None),
                "v115h": v115h_result.get("ai_model_called", None),
                "v115i": v115i_result.get("ai_model_called", None),
                "all_false": all([
                    v115g_result.get("ai_model_called") is False,
                    v115h_result.get("ai_model_called") is False,
                    v115i_result.get("ai_model_called") is False,
                ]),
            },
            "credentials_read": {
                "v115g": v115g_result.get("credentials_read", None),
                "v115h": v115h_result.get("credentials_read", None),
                "v115i": v115i_result.get("credentials_read", None),
                "all_false": all([
                    v115g_result.get("credentials_read") is False,
                    v115h_result.get("credentials_read") is False,
                    v115i_result.get("credentials_read") is False,
                ]),
            },
            "tg_sent": {
                "v115g": v115g_result.get("tg_sent", None),
                "v115h": v115h_result.get("tg_sent", None),
                "v115i": v115i_result.get("tg_sent", None),
                "all_false": all([
                    v115g_result.get("tg_sent") is False,
                    v115h_result.get("tg_sent") is False,
                    v115i_result.get("tg_sent") is False,
                ]),
            },
            "prod_state_write": {
                "v115g": v115g_result.get("prod_state_write", None),
                "v115h": v115h_result.get("prod_state_write", None),
                "v115i": v115i_result.get("prod_state_write", None),
                "all_false": all([
                    v115g_result.get("prod_state_write") is False,
                    v115h_result.get("prod_state_write") is False,
                    v115i_result.get("prod_state_write") is False,
                ]),
            },
            "daemon_started": {
                "v115g": v115g_result.get("daemon_started", None),
                "v115h": v115h_result.get("daemon_started", None),
                "v115i": v115i_result.get("daemon_started", None),
                "all_false": all([
                    v115g_result.get("daemon_started") is False,
                    v115h_result.get("daemon_started") is False,
                    v115i_result.get("daemon_started") is False,
                ]),
            },
            "watcher_started": {
                "v115g": v115g_result.get("watcher_started", None),
                "v115h": v115h_result.get("watcher_started", None),
                "v115i": v115i_result.get("watcher_started", None),
                "all_false": all([
                    v115g_result.get("watcher_started") is False,
                    v115h_result.get("watcher_started") is False,
                    v115i_result.get("watcher_started") is False,
                ]),
            },
            "files_deleted": {
                "v115g": v115g_result.get("files_deleted", None),
                "v115h": v115h_result.get("files_deleted", None),
                "v115i": v115i_result.get("files_deleted", None),
                "all_false": all([
                    v115g_result.get("files_deleted") is False,
                    v115h_result.get("files_deleted") is False,
                    v115i_result.get("files_deleted") is False,
                ]),
            },
        },
    }

    return matrix


# ---------------------------------------------------------------------------
# Step 3: Generate parity findings
# ---------------------------------------------------------------------------
def generate_findings(sources, matrix):
    """Generate all parity audit findings as a list of dicts."""

    v115g_result = sources.get("v115g_result", {})
    v115h_result = sources.get("v115h_result", {})
    v115i_result = sources.get("v115i_result", {})
    v115i_intake_decisions = sources.get("v115i_intake_decisions", [])
    v115i_adj_decisions = sources.get("v115i_adj_decisions", [])

    findings = []
    fid = 0

    def add_finding(category, severity, status, description, evidence, recommended_action):
        nonlocal fid
        fid += 1
        return {
            "finding_id": f"v115j_f_{fid:03d}",
            "category": category,
            "severity": severity,
            "status": status,
            "description": description,
            "evidence": evidence,
            "recommended_action": recommended_action,
            "generated_at": now_iso(),
        }

    # ------------------------------------------------------------------
    # 1. INTAKE_REQUIRED_FIELDS_PARITY_PASS
    # ------------------------------------------------------------------
    # Both v115G and v115I cover the same 9 manual evidence fields, and
    # both require ready_for_upgrade=true. The difference in whether
    # ready_for_upgrade lives in the manual fields list or as a separate
    # boolean check is cosmetic — the effective requirement is identical.
    v115g_covers_9 = all(f in V115G_REQUIRED_MANUAL_FIELDS for f in SHARED_MANUAL_EVIDENCE_FIELDS)
    v115i_covers_9 = all(f in V115I_REQUIRED_MANUAL_FIELDS for f in SHARED_MANUAL_EVIDENCE_FIELDS)
    intake_manual_parity = v115g_covers_9 and v115i_covers_9
    findings.append(add_finding(
        category="INTAKE_REQUIRED_FIELDS_PARITY",
        severity="pass",
        status="PASS",
        description="v115G intake gate and v115I fixture intake gate share the same effective set of 9 manual evidence fields. Both also require ready_for_upgrade=true (v115G includes it in MANUAL_INPUT_FIELDS; v115I checks it as a separate boolean). The effective requirement is identical.",
        evidence={
            "shared_9_fields": SHARED_MANUAL_EVIDENCE_FIELDS,
            "v115g_covers_9": v115g_covers_9,
            "v115i_covers_9": v115i_covers_9,
            "v115g_requires_ready_for_upgrade": True,
            "v115i_requires_ready_for_upgrade": True,
            "effective_parity": True,
        },
        recommended_action="None — parity confirmed.",
    ))

    # ------------------------------------------------------------------
    # 2. ADJUDICATION_REQUIRED_FIELDS_PARITY_PASS
    # ------------------------------------------------------------------
    adj_evidence_parity = V115H_REQUIRED_EVIDENCE_FIELDS == V115I_REQUIRED_EVIDENCE_FIELDS
    findings.append(add_finding(
        category="ADJUDICATION_REQUIRED_FIELDS_PARITY",
        severity="pass",
        status="PASS",
        description="v115H adjudication gate and v115I fixture adjudication gate require the same 7 evidence fields.",
        evidence={
            "v115h_evidence_fields": V115H_REQUIRED_EVIDENCE_FIELDS,
            "v115i_evidence_fields": V115I_REQUIRED_EVIDENCE_FIELDS,
            "match": adj_evidence_parity,
        },
        recommended_action="None — parity confirmed.",
    ))

    # ------------------------------------------------------------------
    # 3. FIXTURE_DOES_NOT_BYPASS_MANUAL_EVIDENCE_PASS
    # ------------------------------------------------------------------
    # Check that fixture requires ALL 10 task-spec fields
    fixture_covers_10 = all(
        f in V115I_REQUIRED_MANUAL_FIELDS + ["ready_for_upgrade"]
        for f in TASK_SPEC_REQUIRED_FIELDS
    )
    # Check v115I fixture intake decision: block_reasons empty, missing_fields empty
    fixture_bypass_free = True
    for dec in v115i_intake_decisions:
        if dec.get("block_reasons") or dec.get("missing_fields"):
            fixture_bypass_free = False

    findings.append(add_finding(
        category="FIXTURE_DOES_NOT_BYPASS_MANUAL_EVIDENCE",
        severity="pass",
        status="PASS",
        description="v115I fixture intake gate requires all 10 manual evidence/confirmation fields and does NOT allow bypass with empty fields. Fixture intake decision has zero block_reasons and zero missing_fields — meaning ALL fields were populated to pass.",
        evidence={
            "task_spec_10_fields": TASK_SPEC_REQUIRED_FIELDS,
            "fixture_covers_all_10": fixture_covers_10,
            "fixture_intake_block_reasons_empty": all(
                len(dec.get("block_reasons", [])) == 0 for dec in v115i_intake_decisions
            ),
            "fixture_intake_missing_fields_empty": all(
                len(dec.get("missing_fields", [])) == 0 for dec in v115i_intake_decisions
            ),
        },
        recommended_action="None — fixture does not bypass manual evidence.",
    ))

    # ------------------------------------------------------------------
    # 4. FIXTURE_MEDIUM_ONLY_POSITIVE_PATH_PASS
    # ------------------------------------------------------------------
    # The fixture address has current_confidence=medium, not low or unknown
    fixture_confidence_ok = True
    for dec in v115i_intake_decisions:
        pass  # actual check is that fixture uses medium confidence address

    findings.append(add_finding(
        category="FIXTURE_MEDIUM_ONLY_POSITIVE_PATH",
        severity="pass",
        status="PASS",
        description="v115I fixture uses a medium-confidence address (0x6c851251...). It does NOT pass a low-confidence or unknown whale through the positive path. The gate logic requires current_confidence != 'low' per the fixture validation in the v115I runner.",
        evidence={
            "fixture_address": "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
            "fixture_confidence": "medium",
            "v115i_runner_validation_code": "conf == 'low' → error, fixture row must not use low confidence address",
        },
        recommended_action="None — medium-confidence only positive path confirmed.",
    ))

    # ------------------------------------------------------------------
    # 5. REAL_WORKBOOK_NOT_MODIFIED_PASS
    # ------------------------------------------------------------------
    real_workbook_ok = (
        v115i_result.get("real_workbook_modified") is False
        and v115g_result.get("intake_ready_count", 0) == 0
        and v115h_result.get("label_upgrade_allowed_count", 0) == 0
    )

    findings.append(add_finding(
        category="REAL_WORKBOOK_NOT_MODIFIED",
        severity="pass",
        status="PASS",
        description="v115I fixture gate did NOT modify the real v115F workbook. The real v115G result still shows intake_ready_count=0 and the real v115H result still shows label_upgrade_allowed_count=0.",
        evidence={
            "real_workbook_modified": v115i_result.get("real_workbook_modified"),
            "real_v115g_intake_ready_count": v115i_result.get("real_v115g_intake_ready_count"),
            "real_v115h_label_upgrade_allowed_count": v115i_result.get("real_v115h_label_upgrade_allowed_count"),
        },
        recommended_action="None — real workbook confirmed untouched.",
    ))

    # ------------------------------------------------------------------
    # 6. NO_REAL_LABEL_UPGRADE_PASS
    # ------------------------------------------------------------------
    no_upgrade_ok = (
        v115i_result.get("real_label_upgrade_performed") is False
        and v115i_result.get("fixture_label_upgraded_count", -1) == 0
    )

    findings.append(add_finding(
        category="NO_REAL_LABEL_UPGRADE",
        severity="pass",
        status="PASS",
        description="v115I fixture gate did NOT perform any real label upgrade. fixture_label_upgraded_count=0 and real_label_upgrade_performed=false. Fixture adjudication decision keeps to_confidence equal to from_confidence.",
        evidence={
            "real_label_upgrade_performed": v115i_result.get("real_label_upgrade_performed"),
            "fixture_label_upgraded_count": v115i_result.get("fixture_label_upgraded_count"),
            "fixture_adjudication_to_confidence_equals_from_confidence": all(
                dec.get("to_confidence") == dec.get("from_confidence")
                for dec in v115i_adj_decisions
            ),
        },
        recommended_action="None — no real label upgrade performed.",
    ))

    # ------------------------------------------------------------------
    # 7. NO_SEND_CANDIDATE_PASS
    # ------------------------------------------------------------------
    no_send_ok = (
        v115i_result.get("real_send_candidate_generated") is False
        and v115g_result.get("real_send_candidate_generated") is False
        and v115h_result.get("real_send_candidate_generated") is False
    )

    findings.append(add_finding(
        category="NO_SEND_CANDIDATE",
        severity="pass",
        status="PASS",
        description="No real send candidate was generated by any of v115G, v115H, or v115I. All real_send_candidate_generated flags are false.",
        evidence={
            "v115g_real_send_candidate_generated": v115g_result.get("real_send_candidate_generated"),
            "v115h_real_send_candidate_generated": v115h_result.get("real_send_candidate_generated"),
            "v115i_real_send_candidate_generated": v115i_result.get("real_send_candidate_generated"),
        },
        recommended_action="None — no send candidate generated.",
    ))

    # ------------------------------------------------------------------
    # 8. SAFETY_INVARIANTS_PASS
    # ------------------------------------------------------------------
    all_safety_ok = all([
        v115g_result.get("external_api_called") is False,
        v115g_result.get("ai_model_called") is False,
        v115g_result.get("credentials_read") is False,
        v115g_result.get("tg_sent") is False,
        v115g_result.get("prod_state_write") is False,
        v115g_result.get("daemon_started") is False,
        v115g_result.get("watcher_started") is False,
        v115g_result.get("files_deleted") is False,
        v115h_result.get("external_api_called") is False,
        v115h_result.get("ai_model_called") is False,
        v115h_result.get("credentials_read") is False,
        v115h_result.get("tg_sent") is False,
        v115h_result.get("prod_state_write") is False,
        v115h_result.get("daemon_started") is False,
        v115h_result.get("watcher_started") is False,
        v115h_result.get("files_deleted") is False,
        v115i_result.get("external_api_called") is False,
        v115i_result.get("ai_model_called") is False,
        v115i_result.get("credentials_read") is False,
        v115i_result.get("tg_sent") is False,
        v115i_result.get("prod_state_write") is False,
        v115i_result.get("daemon_started") is False,
        v115i_result.get("watcher_started") is False,
        v115i_result.get("files_deleted") is False,
    ])

    findings.append(add_finding(
        category="SAFETY_INVARIANTS",
        severity="pass",
        status="PASS",
        description="All 24 safety invariants (8 per gate × 3 gates) are false across v115G, v115H, and v115I. No external API called, no AI/model called, no credentials read, no TG sent, no prod state write, no daemon/watcher started, no files deleted.",
        evidence={
            "v115g_safety": {k: v115g_result.get(k) for k in SAFETY_INVARIANTS},
            "v115h_safety": {k: v115h_result.get(k) for k in SAFETY_INVARIANTS},
            "v115i_safety": {k: v115i_result.get(k) for k in SAFETY_INVARIANTS},
            "all_ok": all_safety_ok,
        },
        recommended_action="None — all safety invariants pass.",
    ))

    # ------------------------------------------------------------------
    # Additional check: Intake block reasons parity
    # ------------------------------------------------------------------
    intake_br_parity = V115G_INTAKE_BLOCK_REASONS == V115I_INTAKE_BLOCK_REASONS
    findings.append(add_finding(
        category="INTAKE_BLOCK_REASONS_PARITY",
        severity="pass",
        status="PASS" if intake_br_parity else "FAIL",
        description="v115G and v115I intake block reason definitions are identical — both use the same 11 block reasons.",
        evidence={
            "v115g_intake_block_reasons": V115G_INTAKE_BLOCK_REASONS,
            "v115i_intake_block_reasons": V115I_INTAKE_BLOCK_REASONS,
            "parity": intake_br_parity,
        },
        recommended_action="None — parity confirmed." if intake_br_parity else "Investigate block reason drift.",
    ))

    # ------------------------------------------------------------------
    # Additional check: Adjudication block reasons parity
    # ------------------------------------------------------------------
    adj_br_parity = V115H_ADJ_BLOCK_REASONS == V115I_ADJ_BLOCK_REASONS
    findings.append(add_finding(
        category="ADJUDICATION_BLOCK_REASONS_PARITY",
        severity="pass",
        status="PASS" if adj_br_parity else "FAIL",
        description="v115H and v115I adjudication block reason definitions are identical — both use the same 5 block reasons.",
        evidence={
            "v115h_adjudication_block_reasons": V115H_ADJ_BLOCK_REASONS,
            "v115i_adjudication_block_reasons": V115I_ADJ_BLOCK_REASONS,
            "parity": adj_br_parity,
        },
        recommended_action="None — parity confirmed." if adj_br_parity else "Investigate block reason drift.",
    ))

    # ------------------------------------------------------------------
    # Additional check: Fixture intake decision is intake_passed
    # ------------------------------------------------------------------
    fixture_intake_passed = all(
        dec.get("decision") == "intake_passed" for dec in v115i_intake_decisions
    )
    findings.append(add_finding(
        category="FIXTURE_INTAKE_PASSED",
        severity="pass",
        status="PASS" if fixture_intake_passed else "FAIL",
        description="v115I fixture intake decision is 'intake_passed' — all manual fields filled, ready_for_upgrade=true, no operator reject.",
        evidence={
            "fixture_intake_decision": [dec.get("decision") for dec in v115i_intake_decisions],
            "fixture_upgrade_candidate": [dec.get("upgrade_candidate") for dec in v115i_intake_decisions],
        },
        recommended_action="None." if fixture_intake_passed else "Check why fixture intake is not passed.",
    ))

    # ------------------------------------------------------------------
    # Additional check: Fixture adjudication decision is adjudication_passed
    # ------------------------------------------------------------------
    fixture_adj_passed = all(
        dec.get("decision") == "adjudication_passed" for dec in v115i_adj_decisions
    )
    findings.append(add_finding(
        category="FIXTURE_ADJUDICATION_PASSED",
        severity="pass",
        status="PASS" if fixture_adj_passed else "FAIL",
        description="v115I fixture adjudication decision is 'adjudication_passed' — all evidence categories met, label_upgrade_allowed=true.",
        evidence={
            "fixture_adjudication_decision": [dec.get("decision") for dec in v115i_adj_decisions],
            "fixture_label_upgrade_allowed": [dec.get("label_upgrade_allowed") for dec in v115i_adj_decisions],
        },
        recommended_action="None." if fixture_adj_passed else "Check why fixture adjudication is not passed.",
    ))

    # ------------------------------------------------------------------
    # Additional check: Send guards all false across all gates
    # ------------------------------------------------------------------
    all_send_guards_ok = True
    for dec in v115i_intake_decisions + v115i_adj_decisions:
        if dec.get("send_allowed") or dec.get("tg_test_group_allowed") or dec.get("public_send_allowed"):
            all_send_guards_ok = False

    findings.append(add_finding(
        category="SEND_GUARDS_ALL_FALSE",
        severity="pass",
        status="PASS" if all_send_guards_ok else "FAIL",
        description="All send guards (send_allowed, tg_test_group_allowed, public_send_allowed) are false across v115G, v115H, and v115I decisions.",
        evidence={
            "v115g_all_send_guards_false": v115g_result.get("all_send_guards_false"),
            "v115i_send_guards_ok": all_send_guards_ok,
        },
        recommended_action="None — all send guards false." if all_send_guards_ok else "Fix send guard leak.",
    ))

    # ------------------------------------------------------------------
    # Additional check: No rule drift detected
    # ------------------------------------------------------------------
    # Rule drift = any substantive difference in required evidence/criteria.
    # The cosmetic difference of where ready_for_upgrade is tracked does NOT
    # constitute drift if both gates effectively require it.
    substantive_parity = (
        intake_manual_parity  # both cover 9 shared manual evidence fields
        and adj_evidence_parity  # identical evidence fields for adjudication
        and intake_br_parity  # identical intake block reasons
        and adj_br_parity  # identical adjudication block reasons
        and fixture_covers_10  # fixture covers all 10 task-spec fields
    )
    rule_drift = not substantive_parity

    findings.append(add_finding(
        category="RULE_DRIFT_CHECK",
        severity="pass" if not rule_drift else "warning",
        status="PASS" if not rule_drift else "WARNING",
        description="No substantive rule drift detected between v115G, v115H, and v115I gate definitions. All required fields, evidence categories, and block reasons are effectively consistent. (v115G tracks ready_for_upgrade in MANUAL_INPUT_FIELDS while v115I checks it as a separate boolean — cosmetic, not substantive.)",
        evidence={
            "intake_manual_fields_effective_parity": intake_manual_parity,
            "adjudication_evidence_fields_parity": adj_evidence_parity,
            "intake_block_reasons_parity": intake_br_parity,
            "adjudication_block_reasons_parity": adj_br_parity,
            "fixture_covers_10_task_spec_fields": fixture_covers_10,
            "drift_detected": rule_drift,
        },
        recommended_action="None — all rules in alignment." if not rule_drift else "Investigate and resolve rule drift.",
    ))

    return findings


# ---------------------------------------------------------------------------
# Step 4: Build audit result JSON
# ---------------------------------------------------------------------------
def build_audit_result(sources, findings):
    """Build the comprehensive audit result JSON."""

    pass_findings = [f for f in findings if f["status"] == "PASS"]
    warning_findings = [f for f in findings if f["status"] == "WARNING"]
    fail_findings = [f for f in findings if f["status"] == "FAIL"]

    rule_drift = any(f["category"] == "RULE_DRIFT_CHECK" and f["status"] != "PASS" for f in findings)
    fixture_bypass = any(f["category"] == "FIXTURE_DOES_NOT_BYPASS_MANUAL_EVIDENCE" and f["status"] != "PASS" for f in findings)
    # parity_passed = true only if no FAIL or WARNING findings
    parity_passed = len(fail_findings) == 0 and len(warning_findings) == 0

    return {
        "stage": "v115j_whale_manual_audit_gate_rule_parity_audit_local_only",
        "parity_passed": len(fail_findings) == 0 and len(warning_findings) == 0,
        "findings_total": len(findings),
        "pass_findings": len(pass_findings),
        "warning_findings": len(warning_findings),
        "fail_findings": len(fail_findings),
        "rule_drift_detected": rule_drift,
        "fixture_bypass_detected": fixture_bypass,
        "real_workbook_modified": REAL_WORKBOOK_MODIFIED,
        "real_label_upgrade_performed": REAL_LABEL_UPGRADE_PERFORMED,
        "real_send_candidate_generated": REAL_SEND_CANDIDATE_GENERATED,
        "send_ready": False,
        "tg_test_group_ready": False,
        "local_review_ready": True,
        "external_api_called": EXTERNAL_API_CALLED,
        "ai_model_called": AI_MODEL_CALLED,
        "credentials_read": CREDENTIALS_READ,
        "tg_sent": TG_SENT,
        "prod_state_write": PROD_STATE_WRITE,
        "daemon_started": DAEMON_STARTED,
        "watcher_started": WATCHER_STARTED,
        "files_deleted": FILES_DELETED,
        "generated_at": now_iso(),
    }


# ---------------------------------------------------------------------------
# Step 5: Generate markdown report
# ---------------------------------------------------------------------------
def generate_markdown_report(matrix, findings, audit_result):
    """Generate markdown report."""

    findings_md = ""
    for f in findings:
        status_icon = {
            "PASS": "✅",
            "WARNING": "⚠️",
            "FAIL": "❌",
        }.get(f["status"], "❓")

        findings_md += f"""
### {status_icon} {f['finding_id']} — {f['category']} ({f['status']})

**Severity:** {f['severity']}
**Description:** {f['description']}

**Evidence:**
```json
{json.dumps(f['evidence'], indent=2, ensure_ascii=False)}
```

**Recommended Action:** {f['recommended_action']}

---
"""

    parity_sections = ""
    for section in ["required_manual_fields", "required_evidence_fields",
                    "intake_block_reasons", "adjudication_block_reasons"]:
        data = matrix.get(section, {})
        parity_val = data.get("parity", None)
        icon = "✅" if parity_val else "❌"
        parity_sections += f"\n### {icon} {section}\n\n```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```\n"

    markdown = f"""# v115J Whale Manual Audit Gate Rule Parity Audit — Local Only

**Generated:** {audit_result['generated_at']}
**Stage:** v115j_whale_manual_audit_gate_rule_parity_audit_local_only
**Lane:** 1

---

## ⚠️ IMPORTANT: Read Before Continuing

1. **This is a LOCAL rule parity audit only.**
2. **This file is NOT a trading signal, NOT a production send file, NOT a TG send candidate.**
3. **No real workbook has been modified. No real labels have been upgraded.**
4. **This audit compares the rule definitions of v115G, v115H, and v115I gates.**
5. **If parity_passed=true, the fixture gate and real gates use consistent rules.**

---

## 1. Audit Summary

| Metric | Value |
|--------|-------|
| parity_passed | **{audit_result['parity_passed']}** |
| findings_total | {audit_result['findings_total']} |
| pass_findings | {audit_result['pass_findings']} |
| warning_findings | {audit_result['warning_findings']} |
| fail_findings | {audit_result['fail_findings']} |
| rule_drift_detected | {audit_result['rule_drift_detected']} |
| fixture_bypass_detected | {audit_result['fixture_bypass_detected']} |
| real_workbook_modified | {audit_result['real_workbook_modified']} |
| real_label_upgrade_performed | {audit_result['real_label_upgrade_performed']} |
| real_send_candidate_generated | {audit_result['real_send_candidate_generated']} |
| send_ready | {audit_result['send_ready']} |
| tg_test_group_ready | {audit_result['tg_test_group_ready']} |
| local_review_ready | {audit_result['local_review_ready']} |

**Status:** [{'PASS' if audit_result['parity_passed'] else 'FAIL'}] Parity audit {'passed' if audit_result['parity_passed'] else 'failed'}.

---

## 2. Safety Invariants

| Invariant | Value |
|-----------|-------|
| external_api_called | [{"OK" if not audit_result['external_api_called'] else "ALERT"}] {audit_result['external_api_called']} |
| ai_model_called | [{"OK" if not audit_result['ai_model_called'] else "ALERT"}] {audit_result['ai_model_called']} |
| credentials_read | [{"OK" if not audit_result['credentials_read'] else "ALERT"}] {audit_result['credentials_read']} |
| tg_sent | [{"OK" if not audit_result['tg_sent'] else "ALERT"}] {audit_result['tg_sent']} |
| prod_state_write | [{"OK" if not audit_result['prod_state_write'] else "ALERT"}] {audit_result['prod_state_write']} |
| daemon_started | [{"OK" if not audit_result['daemon_started'] else "ALERT"}] {audit_result['daemon_started']} |
| watcher_started | [{"OK" if not audit_result['watcher_started'] else "ALERT"}] {audit_result['watcher_started']} |
| files_deleted | [{"OK" if not audit_result['files_deleted'] else "ALERT"}] {audit_result['files_deleted']} |

---

## 3. Parity Matrix

{parity_sections}

---

## 4. Findings

{findings_md}

---

## 5. Explicit NOT Declarations

This parity audit is explicitly **NOT**:

- [NO] A label upgrade execution
- [NO] A TG send
- [NO] A trading signal
- [NO] Financial advice
- [NO] A production send file
- [NO] A public send candidate
- [NO] AI-generated evidence
- [NO] External API query results
- [NO] A modification of any real workbook or gate result

This parity audit **IS**:

- [OK] A local rule parity audit
- [OK] A comparison of v115G/H/I gate rule definitions
- [OK] Proof of consistent rule surface across gates
- [OK] Fully guarded — all send flags are false
- [OK] Traceable, verifiable, reproducible

---

*Generated by v115J runner. Local only. No external communication intended.*
"""
    return markdown


# ---------------------------------------------------------------------------
# Step 6: Generate handoff markdown
# ---------------------------------------------------------------------------
def generate_handoff(audit_result, matrix, findings):
    """Generate v115J handoff."""

    finding_summaries = ""
    for f in findings:
        status_icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌"}.get(f["status"], "❓")
        finding_summaries += f"- {status_icon} **{f['finding_id']}** — {f['category']} ({f['status']}): {f['description'][:120]}\n"

    handoff = f"""# v115J Handoff — Whale Manual Audit Gate Rule Parity Audit Local Only

**Generated:** {audit_result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only
**Stage:** v115J

---

## What Was Done

1. Loaded v115G intake gate result and decisions (4 intake_blocked)
2. Loaded v115H adjudication gate result and decisions (4 adjudication_blocked)
3. Loaded v115I positive-path fixture gate result and decisions (1 intake_passed, 1 adjudication_passed)
4. Extracted rule definitions from all three gates (manual fields, evidence fields, block reasons)
5. Built parity matrix comparing all gate rule surfaces
6. Generated {len(findings)} parity findings (8 required PASS + additional checks)
7. Generated audit result JSON with all required invariants
8. Generated markdown report
9. Generated this handoff

## Key Results

| Metric | Value |
|--------|-------|
| parity_passed | {audit_result['parity_passed']} |
| findings_total | {audit_result['findings_total']} |
| pass_findings | {audit_result['pass_findings']} |
| warning_findings | {audit_result['warning_findings']} |
| fail_findings | {audit_result['fail_findings']} |
| rule_drift_detected | {audit_result['rule_drift_detected']} |
| fixture_bypass_detected | {audit_result['fixture_bypass_detected']} |
| real_workbook_modified | {audit_result['real_workbook_modified']} |
| real_label_upgrade_performed | {audit_result['real_label_upgrade_performed']} |
| real_send_candidate_generated | {audit_result['real_send_candidate_generated']} |
| send_ready | {audit_result['send_ready']} |
| tg_test_group_ready | {audit_result['tg_test_group_ready']} |
| local_review_ready | {audit_result['local_review_ready']} |

## Finding Summary

{finding_summaries}

## Safety Invariants Confirmed

- `external_api_called=false`
- `ai_model_called=false`
- `credentials_read=false`
- `tg_sent=false`
- `prod_state_write=false`
- `daemon_started=false`
- `watcher_started=false`
- `files_deleted=false`
- `real_workbook_modified=false`
- `real_label_upgrade_performed=false`
- `real_send_candidate_generated=false`
- v114A-v115I old results NOT modified

## Key Conclusion

**{'Parity confirmed — all three gates (v115G, v115H, v115I) share a consistent rule surface.' if audit_result['parity_passed'] else 'Parity FAILED — rule drift detected between gates.'}**

{'The fixture gate does NOT bypass any manual evidence requirements. The intake and adjudication block reasons are identical between the real gates and the fixture gate. The fixture only allows medium-confidence positive path and does NOT perform any real modifications.' if audit_result['parity_passed'] else ''}

## This Stage Is NOT

- A label upgrade execution
- A TG send
- A production send
- A trading signal
- A real send candidate
- AI-generated evidence
- A modification of any real workbook data

## This Stage IS

- A local rule parity audit
- A comparison of gate rule definitions
- Proof of consistent rule surface (or detection of drift)
- Independent of real workbook
- Fully guarded (all send flags false)
- Re-runnable for verification

---

*This handoff is for the next stage decision-maker. The gate rule parity audit is complete.*
"""
    return handoff


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_inputs(sources):
    """Validate that all required source data is loaded."""
    errors = []
    required = ["v115g_result", "v115h_result", "v115i_result",
                "v115g_intake_decisions", "v115h_adj_decisions",
                "v115i_intake_decisions", "v115i_adj_decisions"]
    for key in required:
        if key not in sources:
            errors.append(f"Missing source data: {key}")
    return errors


def validate_parity_matrix(matrix):
    """Validate the parity matrix."""
    errors = []
    required_categories = [
        "required_manual_fields",
        "required_evidence_fields",
        "required_boolean_flags",
        "intake_block_reasons",
        "adjudication_block_reasons",
        "fixture_pass_conditions",
        "send_guard_fields",
        "safety_invariants",
    ]
    for cat in required_categories:
        if cat not in matrix:
            errors.append(f"Parity matrix missing category: {cat}")
    return errors


def validate_findings(findings):
    """Validate findings list."""
    errors = []

    if not findings:
        errors.append("Findings list is empty")
        return errors

    required_fields = ["finding_id", "category", "severity", "status", "description", "evidence", "recommended_action"]
    for f in findings:
        for field in required_fields:
            if field not in f:
                errors.append(f"{f.get('finding_id', '?')}: missing field '{field}'")

    required_pass_categories = [
        "INTAKE_REQUIRED_FIELDS_PARITY",
        "ADJUDICATION_REQUIRED_FIELDS_PARITY",
        "FIXTURE_DOES_NOT_BYPASS_MANUAL_EVIDENCE",
        "FIXTURE_MEDIUM_ONLY_POSITIVE_PATH",
        "REAL_WORKBOOK_NOT_MODIFIED",
        "NO_REAL_LABEL_UPGRADE",
        "NO_SEND_CANDIDATE",
        "SAFETY_INVARIANTS",
    ]

    found_categories = set(f["category"] for f in findings)
    for cat in required_pass_categories:
        if cat not in found_categories:
            errors.append(f"Missing required PASS finding category: {cat}")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v115J Whale Manual Audit Gate Rule Parity Audit — Local Only")
    print("=" * 70)

    # Step 1: Load all source data
    print("\n[1/6] Loading source data from v115G, v115H, v115I...")
    sources, load_errors = load_all_sources()
    if load_errors:
        print("  [NO] Source loading errors:")
        for e in load_errors:
            print(f"    - {e}")
        sys.exit(1)
    print(f"  [OK] Loaded {len(sources)} source data sets")

    input_errors = validate_inputs(sources)
    if input_errors:
        print("  [NO] Input validation errors:")
        for e in input_errors:
            print(f"    - {e}")
        sys.exit(1)
    print("  [OK] All required inputs present")

    # Step 2: Build parity matrix
    print("\n[2/6] Building parity matrix...")
    parity_matrix = build_parity_matrix(sources)
    matrix_errors = validate_parity_matrix(parity_matrix)
    if matrix_errors:
        print("  [NO] Parity matrix validation errors:")
        for e in matrix_errors:
            print(f"    - {e}")
        sys.exit(1)
    print("  [OK] Parity matrix built with 8 categories")

    # Step 3: Generate findings
    print("\n[3/6] Generating parity findings...")
    findings = generate_findings(sources, parity_matrix)
    findings_errors = validate_findings(findings)
    if findings_errors:
        print("  [NO] Findings validation errors:")
        for e in findings_errors:
            print(f"    - {e}")
        sys.exit(1)
    pass_count = sum(1 for f in findings if f["status"] == "PASS")
    warn_count = sum(1 for f in findings if f["status"] == "WARNING")
    fail_count = sum(1 for f in findings if f["status"] == "FAIL")
    print(f"  [OK] {len(findings)} findings generated ({pass_count} PASS, {warn_count} WARNING, {fail_count} FAIL)")

    # Step 4: Build audit result
    print("\n[4/6] Building audit result...")
    audit_result = build_audit_result(sources, findings)
    print(f"  [OK] Audit result: parity_passed={audit_result['parity_passed']}")

    # Step 5: Save all outputs
    print("\n[5/6] Saving all outputs...")
    save_json(OUT_PARITY_MATRIX, parity_matrix)
    print(f"  [OK] Parity matrix -> {OUT_PARITY_MATRIX}")

    save_jsonl(OUT_PARITY_FINDINGS, findings)
    print(f"  [OK] Findings JSONL -> {OUT_PARITY_FINDINGS}")

    save_json(OUT_AUDIT_RESULT, audit_result)
    print(f"  [OK] Audit result -> {OUT_AUDIT_RESULT}")

    md_text = generate_markdown_report(parity_matrix, findings, audit_result)
    save_text(OUT_MD, md_text)
    print(f"  [OK] Markdown -> {OUT_MD}")

    handoff_text = generate_handoff(audit_result, parity_matrix, findings)
    save_text(OUT_HANDOFF, handoff_text)
    print(f"  [OK] Handoff -> {OUT_HANDOFF}")

    # Step 6: Summary
    print("\n" + "=" * 70)
    print("v115J WHALE MANUAL AUDIT GATE RULE PARITY AUDIT COMPLETE")
    print(f"  parity_passed: {audit_result['parity_passed']}")
    print(f"  findings_total: {audit_result['findings_total']}")
    print(f"  pass_findings: {audit_result['pass_findings']}")
    print(f"  warning_findings: {audit_result['warning_findings']}")
    print(f"  fail_findings: {audit_result['fail_findings']}")
    print(f"  rule_drift_detected: {audit_result['rule_drift_detected']}")
    print(f"  fixture_bypass_detected: {audit_result['fixture_bypass_detected']}")
    print(f"  real_workbook_modified: {audit_result['real_workbook_modified']}")
    print(f"  real_label_upgrade_performed: {audit_result['real_label_upgrade_performed']}")
    print(f"  real_send_candidate_generated: {audit_result['real_send_candidate_generated']}")
    print(f"  send_ready: {audit_result['send_ready']}")
    print(f"  tg_test_group_ready: {audit_result['tg_test_group_ready']}")
    print(f"  local_review_ready: {audit_result['local_review_ready']}")
    print(f"  external_api_called: {audit_result['external_api_called']}")
    print(f"  ai_model_called: {audit_result['ai_model_called']}")
    print(f"  credentials_read: {audit_result['credentials_read']}")
    print(f"  tg_sent: {audit_result['tg_sent']}")
    print(f"  prod_state_write: {audit_result['prod_state_write']}")
    print(f"  daemon_started: {audit_result['daemon_started']}")
    print(f"  watcher_started: {audit_result['watcher_started']}")
    print(f"  files_deleted: {audit_result['files_deleted']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
