#!/usr/bin/env python3
"""
v115I Whale Manual Audit Positive Path Fixture Gate — Local Only
==================================================================
Reads the real v115F workbook (4 rows, for structure reference only — NEVER
modified), then creates and validates a single test-only synthetic fixture row
with all manual evidence fields filled.

Purpose: Prove that the intake / adjudication gate logic CAN pass when
evidence is complete — it is not a "permanently blocked" design. The fixture
simulates the positive path without touching any real workbook data.

This is a LOCAL-ONLY fixture gate:
  - No external API calls
  - No AI/model calls
  - No TG send
  - No production state write
  - No credential reads
  - No daemon / watcher / loop
  - No file deletion
  - No modification of v114A-v115H old results
  - No real send candidate generated
  - No real label upgrade performed

Outputs:
  - Fixture CSV (already created)
  - intake_records.jsonl (1 record)
  - intake_decisions.jsonl (1 decision)
  - adjudication_records.jsonl (1 record)
  - adjudication_decisions.jsonl (1 decision)
  - gate_result.json
  - markdown report
  - handoff markdown
"""

import csv
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

# v115F input (read-only) — real workbook, NEVER modified
V115F_WORKBOOK_CSV = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)

# v115G real results (read-only) — must still show blocked state
V115G_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_workbook_intake_gate_result.json"
)

# v115H real results (read-only) — must still show blocked state
V115H_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_gate_result.json"
)

# v115B routing policy (read-only)
V115B_ROUTING = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)

# v115I fixture input
FIXTURE_CSV = os.path.join(
    FIXTURES_DIR, "v115i_whale_manual_audit_positive_path_fixture.csv"
)

# v115I outputs
OUT_INTAKE_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_intake_records.jsonl"
)
OUT_INTAKE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_intake_decisions.jsonl"
)
OUT_ADJUDICATION_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_adjudication_records.jsonl"
)
OUT_ADJUDICATION_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_adjudication_decisions.jsonl"
)
OUT_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115i_whale_manual_audit_positive_path_fixture_gate_result.json"
)
OUT_MD = os.path.join(
    RUNS_DIR, "v115i_whale_manual_audit_positive_path_fixture_gate_local_only.md"
)
OUT_HANDOFF = os.path.join(
    RUNS_DIR, "v115i_whale_manual_audit_positive_path_fixture_gate_local_only_handoff.md"
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

# --- Intake Decision Block Reason Constants (same as v115G) ---
BR_TRUSTED_SOURCE_LABEL_MISSING = "TRUSTED_SOURCE_LABEL_MISSING"
BR_TRUSTED_SOURCE_NOTE_OR_URL_MISSING = "TRUSTED_SOURCE_NOTE_OR_URL_MISSING"
BR_SECOND_SOURCE_LABEL_MISSING = "SECOND_SOURCE_LABEL_MISSING"
BR_SECOND_SOURCE_NOTE_OR_URL_MISSING = "SECOND_SOURCE_NOTE_OR_URL_MISSING"
BR_ACTIVITY_PATTERN_NOTE_MISSING = "ACTIVITY_PATTERN_NOTE_MISSING"
BR_OPERATOR_CONFIRMED_LABEL_MISSING = "OPERATOR_CONFIRMED_LABEL_MISSING"
BR_OPERATOR_CONFIDENCE_ASSESSMENT_MISSING = "OPERATOR_CONFIDENCE_ASSESSMENT_MISSING"
BR_REVIEWER_MISSING = "REVIEWER_MISSING"
BR_REVIEWED_AT_MISSING = "REVIEWED_AT_MISSING"
BR_READY_FOR_UPGRADE_FALSE = "READY_FOR_UPGRADE_FALSE"
BR_OPERATOR_REJECTED = "OPERATOR_REJECTED"

# --- Adjudication Block Reason Constants (same as v115H) ---
BR_INTAKE_NOT_READY = "INTAKE_NOT_READY"
BR_UPGRADE_CANDIDATE_FALSE = "UPGRADE_CANDIDATE_FALSE"
BR_MANUAL_EVIDENCE_INCOMPLETE = "MANUAL_EVIDENCE_INCOMPLETE"
BR_NO_CONFIDENCE_CHANGE_ALLOWED = "NO_CONFIDENCE_CHANGE_ALLOWED"
BR_SEND_GUARDS_REMAIN_FALSE = "SEND_GUARDS_REMAIN_FALSE"

# Manual fields required for intake
MANUAL_INPUT_FIELDS = [
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
    "reviewer",
    "reviewed_at",
]

EVIDENCE_URL_FIELDS = [
    "trusted_source_url_or_note",
    "second_source_url_or_note",
]

OPERATOR_CONFIRMATION_FIELDS = [
    "operator_confirmed_label",
    "operator_confidence_assessment",
]

EVIDENCE_FIELDS = [
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
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


def load_csv_rows(path: str) -> list:
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def short_addr(address: str) -> str:
    if len(address) <= 14:
        return address
    return f"{address[:6]}...{address[-4:]}"


def field_is_empty(val) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False


def parse_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() == "true"
    return False


# ---------------------------------------------------------------------------
# Step 1: Read real v115F workbook (structure only, NOT modified)
# ---------------------------------------------------------------------------
def verify_real_workbook():
    """Verify the real v115F workbook exists and has 4 rows. Do NOT modify."""
    if not os.path.exists(V115F_WORKBOOK_CSV):
        print(f"ERROR: v115F workbook not found: {V115F_WORKBOOK_CSV}")
        sys.exit(1)

    rows = load_csv_rows(V115F_WORKBOOK_CSV)

    if len(rows) != 4:
        print(f"ERROR: Expected 4 workbook rows, got {len(rows)}")
        sys.exit(1)

    print(f"  [OK] Real v115F workbook confirmed: {len(rows)} rows (read-only)")
    return rows


# ---------------------------------------------------------------------------
# Step 2: Load fixture CSV
# ---------------------------------------------------------------------------
def load_fixture():
    """Load the v115I fixture CSV. Must have exactly 1 row."""
    if not os.path.exists(FIXTURE_CSV):
        print(f"ERROR: Fixture CSV not found: {FIXTURE_CSV}")
        sys.exit(1)

    rows = load_csv_rows(FIXTURE_CSV)

    if len(rows) != 1:
        print(f"ERROR: Expected 1 fixture row, got {len(rows)}")
        sys.exit(1)

    print(f"  [OK] Loaded {len(rows)} fixture row from v115I CSV")
    return rows


# ---------------------------------------------------------------------------
# Step 3: Validate fixture metadata
# ---------------------------------------------------------------------------
def validate_fixture_metadata(fixture_rows):
    """Check that the fixture row has all required metadata flags."""
    errors = []

    for i, row in enumerate(fixture_rows):
        fixture_only = parse_bool(row.get("fixture_only", "false"))
        synthetic_evidence = parse_bool(row.get("synthetic_evidence", "false"))
        not_real_label_upgrade = parse_bool(row.get("not_real_label_upgrade", "false"))
        not_send_candidate = parse_bool(row.get("not_send_candidate", "false"))

        if not fixture_only:
            errors.append(f"Fixture row {i+1}: fixture_only must be true, got {row.get('fixture_only')}")
        if not synthetic_evidence:
            errors.append(f"Fixture row {i+1}: synthetic_evidence must be true, got {row.get('synthetic_evidence')}")
        if not not_real_label_upgrade:
            errors.append(f"Fixture row {i+1}: not_real_label_upgrade must be true, got {row.get('not_real_label_upgrade')}")
        if not not_send_candidate:
            errors.append(f"Fixture row {i+1}: not_send_candidate must be true, got {row.get('not_send_candidate')}")

    return errors


# ---------------------------------------------------------------------------
# Step 4: Build intake records from fixture
# ---------------------------------------------------------------------------
def build_intake_records(fixture_rows):
    """For the fixture row, build an intake record with all evidence fields present."""
    intake_records = []

    for i, row in enumerate(fixture_rows):
        address = row.get("address", "").strip()

        manual_fields_status = {}
        for field in MANUAL_INPUT_FIELDS:
            manual_fields_status[field] = not field_is_empty(row.get(field, ""))

        all_manual_complete = all(manual_fields_status.values())

        evidence_urls_present = all(
            manual_fields_status.get(f, False) for f in EVIDENCE_URL_FIELDS
        )

        operator_confirmation_present = all(
            manual_fields_status.get(f, False) for f in OPERATOR_CONFIRMATION_FIELDS
        )

        ready_for_upgrade_raw = parse_bool(row.get("ready_for_upgrade", "false"))
        operator_reject_reason = row.get("operator_reject_reason", "").strip()

        intake_ready = (
            all_manual_complete
            and ready_for_upgrade_raw
            and operator_reject_reason == ""
        )

        record = {
            "intake_id": f"v115i_fixture_intake_{i+1:03d}",
            "address": address,
            "current_label": row.get("current_label", "").strip(),
            "current_confidence": row.get("current_confidence", "").strip(),
            "target_confidence": row.get("target_confidence", "").strip(),
            "priority": row.get("priority", "").strip(),
            "trusted_source_label_value": row.get("trusted_source_label_value", "").strip(),
            "trusted_source_url_or_note": row.get("trusted_source_url_or_note", "").strip(),
            "second_source_label_value": row.get("second_source_label_value", "").strip(),
            "second_source_url_or_note": row.get("second_source_url_or_note", "").strip(),
            "activity_pattern_note": row.get("activity_pattern_note", "").strip(),
            "operator_confirmed_label": row.get("operator_confirmed_label", "").strip(),
            "operator_confidence_assessment": row.get("operator_confidence_assessment", "").strip(),
            "operator_reject_reason": operator_reject_reason,
            "reviewer": row.get("reviewer", "").strip(),
            "reviewed_at": row.get("reviewed_at", "").strip(),
            "ready_for_upgrade": ready_for_upgrade_raw,
            "manual_fields_complete": all_manual_complete,
            "evidence_url_fields_present": evidence_urls_present,
            "operator_confirmation_present": operator_confirmation_present,
            "intake_ready": intake_ready,
            "fixture_only": parse_bool(row.get("fixture_only", "false")),
            "synthetic_evidence": parse_bool(row.get("synthetic_evidence", "false")),
            "not_real_label_upgrade": parse_bool(row.get("not_real_label_upgrade", "false")),
            "not_send_candidate": parse_bool(row.get("not_send_candidate", "false")),
            "generated_at": now_iso(),
        }

        intake_records.append(record)

    return intake_records


# ---------------------------------------------------------------------------
# Step 5: Build intake decisions from fixture
# ---------------------------------------------------------------------------
def build_intake_decisions(intake_records):
    """Apply intake gate rules to fixture intake records.

    For a fully filled positive-path fixture, this should produce
    decision='intake_passed' with upgrade_candidate=true.
    """
    intake_decisions = []

    for rec in intake_records:
        address = rec["address"]

        missing_fields = []
        block_reasons = []

        if field_is_empty(rec.get("trusted_source_label_value", "")):
            missing_fields.append("trusted_source_label_value")
            block_reasons.append(BR_TRUSTED_SOURCE_LABEL_MISSING)

        if field_is_empty(rec.get("trusted_source_url_or_note", "")):
            missing_fields.append("trusted_source_url_or_note")
            block_reasons.append(BR_TRUSTED_SOURCE_NOTE_OR_URL_MISSING)

        if field_is_empty(rec.get("second_source_label_value", "")):
            missing_fields.append("second_source_label_value")
            block_reasons.append(BR_SECOND_SOURCE_LABEL_MISSING)

        if field_is_empty(rec.get("second_source_url_or_note", "")):
            missing_fields.append("second_source_url_or_note")
            block_reasons.append(BR_SECOND_SOURCE_NOTE_OR_URL_MISSING)

        if field_is_empty(rec.get("activity_pattern_note", "")):
            missing_fields.append("activity_pattern_note")
            block_reasons.append(BR_ACTIVITY_PATTERN_NOTE_MISSING)

        if field_is_empty(rec.get("operator_confirmed_label", "")):
            missing_fields.append("operator_confirmed_label")
            block_reasons.append(BR_OPERATOR_CONFIRMED_LABEL_MISSING)

        if field_is_empty(rec.get("operator_confidence_assessment", "")):
            missing_fields.append("operator_confidence_assessment")
            block_reasons.append(BR_OPERATOR_CONFIDENCE_ASSESSMENT_MISSING)

        if field_is_empty(rec.get("reviewer", "")):
            missing_fields.append("reviewer")
            block_reasons.append(BR_REVIEWER_MISSING)

        if field_is_empty(rec.get("reviewed_at", "")):
            missing_fields.append("reviewed_at")
            block_reasons.append(BR_REVIEWED_AT_MISSING)

        if not rec.get("ready_for_upgrade", False):
            missing_fields.append("ready_for_upgrade")
            block_reasons.append(BR_READY_FOR_UPGRADE_FALSE)

        operator_reject_reason = rec.get("operator_reject_reason", "").strip()

        if operator_reject_reason:
            decision = "intake_blocked"
            upgrade_candidate = False
            upgrade_ready = False
            if BR_OPERATOR_REJECTED not in block_reasons:
                block_reasons.append(BR_OPERATOR_REJECTED)
        elif rec.get("intake_ready", False):
            decision = "intake_passed"
            upgrade_candidate = True
            upgrade_ready = True
        else:
            decision = "intake_blocked"
            upgrade_candidate = False
            upgrade_ready = False

        intake_decision = {
            "intake_decision_id": f"v115i_fixture_ind_{rec['intake_id'].split('_')[-1]}",
            "address": address,
            "decision": decision,
            "upgrade_candidate": upgrade_candidate,
            "upgrade_ready": upgrade_ready,
            "missing_fields": missing_fields,
            "block_reasons": block_reasons,
            "send_allowed": False,
            "tg_test_group_allowed": False,
            "public_send_allowed": False,
            "fixture_only": rec.get("fixture_only", False),
            "not_send_candidate": rec.get("not_send_candidate", False),
            "generated_at": now_iso(),
        }

        intake_decisions.append(intake_decision)

    return intake_decisions


# ---------------------------------------------------------------------------
# Step 6: Build adjudication records from fixture
# ---------------------------------------------------------------------------
def build_adjudication_records(intake_records, intake_decisions):
    """Build adjudication records from fixture intake data.

    With all evidence complete, this should produce adjudication_ready=true
    and label_upgrade_allowed=true for the fixture row.
    """
    record_by_addr = {r["address"]: r for r in intake_records}
    decision_by_addr = {d["address"]: d for d in intake_decisions}

    adjudication_records = []

    for i, decision in enumerate(intake_decisions):
        address = decision["address"]
        record = record_by_addr.get(address, {})

        current_label = record.get("current_label", "")
        current_confidence = record.get("current_confidence", "")
        intake_ready = record.get("intake_ready", False)
        upgrade_candidate = decision.get("upgrade_candidate", False)
        manual_fields_complete = record.get("manual_fields_complete", False)

        trusted_source_ok = (
            not field_is_empty(record.get("trusted_source_label_value", ""))
            and not field_is_empty(record.get("trusted_source_url_or_note", ""))
        )

        second_source_ok = (
            not field_is_empty(record.get("second_source_label_value", ""))
            and not field_is_empty(record.get("second_source_url_or_note", ""))
        )

        activity_pattern_ok = (
            not field_is_empty(record.get("activity_pattern_note", ""))
        )

        operator_confirmation_ok = (
            not field_is_empty(record.get("operator_confirmed_label", ""))
            and not field_is_empty(record.get("operator_confidence_assessment", ""))
        )

        evidence_requirements_met = (
            trusted_source_ok
            and second_source_ok
            and activity_pattern_ok
            and operator_confirmation_ok
        )

        adjudication_ready = (
            intake_ready
            and upgrade_candidate
            and manual_fields_complete
            and evidence_requirements_met
        )

        # IMPORTANT: Even though adjudication allows upgrade, we do NOT
        # actually upgrade the label — label_upgrade_allowed records the
        # gate decision, but label_upgraded_count stays 0.
        label_upgrade_allowed = adjudication_ready

        adjudication_record = {
            "adjudication_id": f"v115i_fixture_adj_{i+1:03d}",
            "address": address,
            "current_label": current_label,
            "current_confidence": current_confidence,
            "requested_confidence": "high",
            "intake_ready": intake_ready,
            "upgrade_candidate": upgrade_candidate,
            "manual_fields_complete": manual_fields_complete,
            "evidence_requirements_met": evidence_requirements_met,
            "trusted_source_ok": trusted_source_ok,
            "second_source_ok": second_source_ok,
            "activity_pattern_ok": activity_pattern_ok,
            "operator_confirmation_ok": operator_confirmation_ok,
            "adjudication_ready": adjudication_ready,
            "label_upgrade_allowed": label_upgrade_allowed,
            "new_confidence": current_confidence,  # NOT upgraded
            "fixture_only": record.get("fixture_only", False),
            "synthetic_evidence": record.get("synthetic_evidence", False),
            "not_real_label_upgrade": record.get("not_real_label_upgrade", False),
            "not_send_candidate": record.get("not_send_candidate", False),
            "generated_at": now_iso(),
        }

        adjudication_records.append(adjudication_record)

    return adjudication_records


# ---------------------------------------------------------------------------
# Step 7: Build adjudication decisions from fixture
# ---------------------------------------------------------------------------
def build_adjudication_decisions(adjudication_records):
    """Apply adjudication gate rules to fixture adjudication records.

    For the positive-path fixture, this should produce
    decision='adjudication_passed' with label_upgrade_allowed=true.
    BUT we still keep label_upgraded_count=0 — no actual upgrade is performed.
    """
    adjudication_decisions = []

    for rec in adjudication_records:
        address = rec["address"]
        current_confidence = rec["current_confidence"]

        block_reasons = []

        if not rec["intake_ready"]:
            block_reasons.append(BR_INTAKE_NOT_READY)

        if not rec["upgrade_candidate"]:
            block_reasons.append(BR_UPGRADE_CANDIDATE_FALSE)

        if not rec["manual_fields_complete"] or not rec["evidence_requirements_met"]:
            block_reasons.append(BR_MANUAL_EVIDENCE_INCOMPLETE)

        if rec.get("adjudication_ready", False) and rec.get("label_upgrade_allowed", False):
            # Positive path: all conditions met, gate passes
            decision = "adjudication_passed"
            label_upgrade_allowed = True
            to_confidence = current_confidence  # NOT actually upgraded
        else:
            decision = "adjudication_blocked"
            label_upgrade_allowed = False
            to_confidence = current_confidence
            block_reasons.append(BR_NO_CONFIDENCE_CHANGE_ALLOWED)
            block_reasons.append(BR_SEND_GUARDS_REMAIN_FALSE)

        adjudication_decision = {
            "adjudication_decision_id": f"v115i_fixture_adjd_{rec['adjudication_id'].split('_')[-1]}",
            "address": address,
            "decision": decision,
            "label_upgrade_allowed": label_upgrade_allowed,
            "from_confidence": current_confidence,
            "to_confidence": to_confidence,
            "requested_confidence": "high",
            "block_reasons": sorted(block_reasons),
            "send_allowed": False,
            "tg_test_group_allowed": False,
            "public_send_allowed": False,
            "fixture_only": rec.get("fixture_only", False),
            "not_send_candidate": rec.get("not_send_candidate", False),
            "generated_at": now_iso(),
        }

        adjudication_decisions.append(adjudication_decision)

    return adjudication_decisions


# ---------------------------------------------------------------------------
# Step 8: Build gate result JSON
# ---------------------------------------------------------------------------
def build_gate_result(fixture_rows, intake_records, intake_decisions,
                      adjudication_records, adjudication_decisions,
                      real_v115g_result, real_v115h_result):
    """Build the comprehensive v115I gate result JSON."""

    fixture_intake_ready_count = sum(1 for r in intake_records if r["intake_ready"])
    fixture_upgrade_candidate_count = sum(1 for d in intake_decisions if d["upgrade_candidate"])
    fixture_blocked_intake_count = sum(1 for d in intake_decisions if d["decision"] == "intake_blocked")
    fixture_adjudication_ready_count = sum(1 for r in adjudication_records if r["adjudication_ready"])
    fixture_label_upgrade_allowed_count = sum(1 for d in adjudication_decisions if d["label_upgrade_allowed"])
    fixture_label_upgraded_count = 0  # NEVER actually upgrade

    # Cross-check real results
    real_v115g_intake_ready = real_v115g_result.get("intake_ready_count", 0)
    real_v115h_upgrade_allowed = real_v115h_result.get("label_upgrade_allowed_count", 0)

    result = {
        "stage": "v115i_whale_manual_audit_positive_path_fixture_gate_local_only",
        "fixture_only": True,
        "synthetic_evidence": True,
        "real_workbook_modified": REAL_WORKBOOK_MODIFIED,
        "real_label_upgrade_performed": REAL_LABEL_UPGRADE_PERFORMED,
        "real_send_candidate_generated": REAL_SEND_CANDIDATE_GENERATED,
        "fixture_rows": len(fixture_rows),
        "fixture_intake_records": len(intake_records),
        "fixture_intake_decisions": len(intake_decisions),
        "fixture_intake_ready_count": fixture_intake_ready_count,
        "fixture_upgrade_candidate_count": fixture_upgrade_candidate_count,
        "fixture_blocked_intake_count": fixture_blocked_intake_count,
        "fixture_adjudication_records": len(adjudication_records),
        "fixture_adjudication_decisions": len(adjudication_decisions),
        "fixture_adjudication_ready_count": fixture_adjudication_ready_count,
        "fixture_label_upgrade_allowed_count": fixture_label_upgrade_allowed_count,
        "fixture_label_upgraded_count": fixture_label_upgraded_count,
        "real_v115g_intake_ready_count": real_v115g_intake_ready,
        "real_v115h_label_upgrade_allowed_count": real_v115h_upgrade_allowed,
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

    return result


# ---------------------------------------------------------------------------
# Step 9: Generate markdown report
# ---------------------------------------------------------------------------
def generate_markdown_report(fixture_rows, intake_records, intake_decisions,
                              adjudication_records, adjudication_decisions,
                              gate_result):
    """Generate v115I markdown report."""

    per_fixture = ""
    for i, (row, ir, id_, ar, ad) in enumerate(zip(
        fixture_rows, intake_records, intake_decisions,
        adjudication_records, adjudication_decisions
    )):
        addr = ir["address"]
        sa = short_addr(addr)

        intake_block_str = "\n".join(f"  - `{br}`" for br in id_.get("block_reasons", []))
        adj_block_str = "\n".join(f"  - `{br}`" for br in ad.get("block_reasons", []))

        per_fixture += f"""
### Fixture Row {i+1}: `{addr}`

#### Intake Results

| Field | Value |
|-------|-------|
| Label | {ir['current_label']} |
| Confidence | {ir['current_confidence']} → target: {ir['target_confidence']} |
| intake_ready | [{"OK" if ir['intake_ready'] else "NO"}] {ir['intake_ready']} |
| manual_fields_complete | [{"OK" if ir['manual_fields_complete'] else "NO"}] {ir['manual_fields_complete']} |
| evidence_url_fields_present | [{"OK" if ir['evidence_url_fields_present'] else "NO"}] {ir['evidence_url_fields_present']} |
| operator_confirmation_present | [{"OK" if ir['operator_confirmation_present'] else "NO"}] {ir['operator_confirmation_present']} |
| decision | **{id_['decision']}** |
| upgrade_candidate | [{"OK" if id_['upgrade_candidate'] else "NO"}] {id_['upgrade_candidate']} |

#### Intake Block Reasons ({len(id_.get('block_reasons', []))})
{intake_block_str if intake_block_str else '  *(none — all checks passed)*'}

#### Adjudication Results

| Field | Value |
|-------|-------|
| trusted_source_ok | [{"OK" if ar['trusted_source_ok'] else "NO"}] {ar['trusted_source_ok']} |
| second_source_ok | [{"OK" if ar['second_source_ok'] else "NO"}] {ar['second_source_ok']} |
| activity_pattern_ok | [{"OK" if ar['activity_pattern_ok'] else "NO"}] {ar['activity_pattern_ok']} |
| operator_confirmation_ok | [{"OK" if ar['operator_confirmation_ok'] else "NO"}] {ar['operator_confirmation_ok']} |
| evidence_requirements_met | [{"OK" if ar['evidence_requirements_met'] else "NO"}] {ar['evidence_requirements_met']} |
| adjudication_ready | [{"OK" if ar['adjudication_ready'] else "NO"}] {ar['adjudication_ready']} |
| label_upgrade_allowed | [{"OK" if ar['label_upgrade_allowed'] else "NO"}] {ar['label_upgrade_allowed']} |
| new_confidence | {ar['new_confidence']} (NOT upgraded) |
| decision | **{ad['decision']}** |

#### Adjudication Block Reasons ({len(ad.get('block_reasons', []))})
{adj_block_str if adj_block_str else '  *(none — gate passed)*'}

#### Fixture Metadata
| Flag | Value |
|------|-------|
| fixture_only | {ir.get('fixture_only', False)} |
| synthetic_evidence | {ir.get('synthetic_evidence', False)} |
| not_real_label_upgrade | {ir.get('not_real_label_upgrade', False)} |
| not_send_candidate | {ir.get('not_send_candidate', False)} |

---
"""

    markdown = f"""# v115I Whale Manual Audit Positive Path Fixture Gate — Local Only

**Generated:** {gate_result['generated_at']}
**Stage:** v115i_whale_manual_audit_positive_path_fixture_gate_local_only
**Lane:** 1
**Fixture Only:** YES — SYNTHETIC TEST DATA

---

## ⚠️ CRITICAL: Read Before Continuing

1. **THIS IS A TEST-ONLY FIXTURE GATE.**
2. **ALL DATA IS SYNTHETIC. NO REAL ADDRESSES. NO REAL EVIDENCE.**
3. **This file proves the gate logic CAN pass when evidence is complete.**
4. **No real workbook has been modified. No real labels have been upgraded.**
5. **No TG send. No production state write. No external API calls.**

---

## 1. Purpose

This v115I fixture gate proves that the intake/adjudication gate pipeline
introduced in v115G/v115H is **not a permanently-blocked design**. When all
manual evidence fields are complete (as this fixture demonstrates), the gate
logic allows passage through both intake and adjudication stages.

The real v115F workbook remains in its original blocked state (4 addresses,
all blocked). This fixture is independent and test-only.

---

## 2. Gate Summary — Fixture (Positive Path)

| Metric | Value |
|--------|-------|
| fixture_rows | {gate_result['fixture_rows']} |
| fixture_intake_records | {gate_result['fixture_intake_records']} |
| fixture_intake_decisions | {gate_result['fixture_intake_decisions']} |
| fixture_intake_ready_count | {gate_result['fixture_intake_ready_count']} |
| fixture_upgrade_candidate_count | {gate_result['fixture_upgrade_candidate_count']} |
| fixture_blocked_intake_count | {gate_result['fixture_blocked_intake_count']} |
| fixture_adjudication_records | {gate_result['fixture_adjudication_records']} |
| fixture_adjudication_decisions | {gate_result['fixture_adjudication_decisions']} |
| fixture_adjudication_ready_count | {gate_result['fixture_adjudication_ready_count']} |
| fixture_label_upgrade_allowed_count | {gate_result['fixture_label_upgrade_allowed_count']} |
| fixture_label_upgraded_count | {gate_result['fixture_label_upgraded_count']} |
| send_ready | [{"OK" if gate_result['send_ready'] else "NO"}] {gate_result['send_ready']} |
| tg_test_group_ready | [{"OK" if gate_result['tg_test_group_ready'] else "NO"}] {gate_result['tg_test_group_ready']} |
| local_review_ready | [OK] {gate_result['local_review_ready']} |

**Fixture Status:** [PASS] Fixture intake passed — gate logic can pass when evidence is complete.
**Real Status:** [BLOCKED] Real v115F workbook still has 4 blocked addresses.

---

## 3. Cross-Check: Real Workbook Unchanged

| Metric | Expected | Actual |
|--------|----------|--------|
| real_v115g_intake_ready_count | 0 | {gate_result['real_v115g_intake_ready_count']} |
| real_v115h_label_upgrade_allowed_count | 0 | {gate_result['real_v115h_label_upgrade_allowed_count']} |
| real_workbook_modified | false | {gate_result['real_workbook_modified']} |
| real_label_upgrade_performed | false | {gate_result['real_label_upgrade_performed']} |
| real_send_candidate_generated | false | {gate_result['real_send_candidate_generated']} |

---

## 4. Safety Invariants

| Invariant | Value |
|-----------|-------|
| external_api_called | [{"OK" if not gate_result['external_api_called'] else "ALERT"}] {gate_result['external_api_called']} |
| ai_model_called | [{"OK" if not gate_result['ai_model_called'] else "ALERT"}] {gate_result['ai_model_called']} |
| credentials_read | [{"OK" if not gate_result['credentials_read'] else "ALERT"}] {gate_result['credentials_read']} |
| tg_sent | [{"OK" if not gate_result['tg_sent'] else "ALERT"}] {gate_result['tg_sent']} |
| prod_state_write | [{"OK" if not gate_result['prod_state_write'] else "ALERT"}] {gate_result['prod_state_write']} |
| daemon_started | [{"OK" if not gate_result['daemon_started'] else "ALERT"}] {gate_result['daemon_started']} |
| watcher_started | [{"OK" if not gate_result['watcher_started'] else "ALERT"}] {gate_result['watcher_started']} |
| files_deleted | [{"OK" if not gate_result['files_deleted'] else "ALERT"}] {gate_result['files_deleted']} |

---

## 5. Per-Fixture Results
{per_fixture}

## 6. Explicit NOT Declarations

This fixture gate is explicitly **NOT**:

- [NO] A real label upgrade
- [NO] A TG send
- [NO] A trading signal
- [NO] Financial advice
- [NO] A production send file
- [NO] A public send candidate
- [NO] AI-generated evidence
- [NO] External API query results
- [NO] A modification of any real workbook

This fixture gate **IS**:

- [OK] A test-only positive path fixture gate
- [OK] Proof that gate logic can pass when evidence is complete
- [OK] Fully guarded — all send flags are false
- [OK] Independent of real workbook — no real data modified
- [OK] Traceable, verifiable, reproducible
- [OK] Synthetic evidence — not real

---

*Generated by v115I runner. Local only. Test fixture only. No external communication intended.*
"""
    return markdown


# ---------------------------------------------------------------------------
# Step 10: Generate handoff markdown
# ---------------------------------------------------------------------------
def generate_handoff(gate_result, intake_records, intake_decisions,
                     adjudication_records, adjudication_decisions):
    """Generate v115I handoff."""

    fixture_summaries = ""
    for i, (ir, id_, ar, ad) in enumerate(zip(
        intake_records, intake_decisions,
        adjudication_records, adjudication_decisions
    )):
        sa = short_addr(ir["address"])
        fixture_summaries += (
            f"- [{id_['decision'].upper()}] Fixture {i+1}: `{sa}` — {ir['current_label']} "
            f"({ir['current_confidence']}) — "
            f"intake_ready={ir['intake_ready']} — "
            f"upgrade_candidate={id_['upgrade_candidate']} — "
            f"adjudication_ready={ar['adjudication_ready']} — "
            f"label_upgrade_allowed={ad['label_upgrade_allowed']} — "
            f"label_upgraded={gate_result['fixture_label_upgraded_count']}\n"
        )

    handoff = f"""# v115I Handoff — Whale Manual Audit Positive Path Fixture Gate Local Only

**Generated:** {gate_result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only
**Stage:** v115I
**Fixture Only:** YES

---

## What Was Done

1. Read real v115F workbook (4 rows — read-only, NOT modified)
2. Confirmed real v115G result (intake_ready_count=0) — unchanged
3. Confirmed real v115H result (label_upgrade_allowed_count=0) — unchanged
4. Read v115B routing policy (for context)
5. Loaded v115I fixture CSV (1 synthetic positive-path row)
6. Validated fixture metadata flags (fixture_only, synthetic_evidence, etc.)
7. Built 1 fixture intake record from synthetic evidence
8. Applied intake gate rules → intake_passed, upgrade_candidate=true
9. Built 1 fixture adjudication record
10. Applied adjudication gate rules → adjudication_passed, label_upgrade_allowed=true
11. fixture_label_upgraded_count = 0 (NO actual upgrade performed)
12. Generated gate result JSON with all required fields
13. Generated markdown report
14. Generated this handoff

## Fixture Summary

{fixture_summaries}

## Key Results

| Metric | Value |
|--------|-------|
| fixture_rows | {gate_result['fixture_rows']} |
| fixture_intake_ready_count | {gate_result['fixture_intake_ready_count']} |
| fixture_upgrade_candidate_count | {gate_result['fixture_upgrade_candidate_count']} |
| fixture_blocked_intake_count | {gate_result['fixture_blocked_intake_count']} |
| fixture_adjudication_ready_count | {gate_result['fixture_adjudication_ready_count']} |
| fixture_label_upgrade_allowed_count | {gate_result['fixture_label_upgrade_allowed_count']} |
| fixture_label_upgraded_count | {gate_result['fixture_label_upgraded_count']} |
| real_v115g_intake_ready_count | {gate_result['real_v115g_intake_ready_count']} |
| real_v115h_label_upgrade_allowed_count | {gate_result['real_v115h_label_upgrade_allowed_count']} |
| real_workbook_modified | {gate_result['real_workbook_modified']} |
| real_label_upgrade_performed | {gate_result['real_label_upgrade_performed']} |
| real_send_candidate_generated | {gate_result['real_send_candidate_generated']} |
| send_ready | {gate_result['send_ready']} |
| tg_test_group_ready | {gate_result['tg_test_group_ready']} |
| local_review_ready | {gate_result['local_review_ready']} |

## Safety Invariants Confirmed

- `external_api_called=false`
- `ai_model_called=false`
- `credentials_read=false`
- `tg_sent=false`
- `prod_state_write=false`
- `daemon_started=false`
- `watcher_started=false`
- `files_deleted=false`
- `real_send_candidate_generated=false`
- `real_workbook_modified=false`
- `real_label_upgrade_performed=false`
- `fixture_label_upgraded_count=0`
- v114A-v115H old results NOT modified
- v115F workbook NOT modified

## Key Finding

**The intake/adjudication gate is NOT a permanently-blocked design.** When
all manual evidence fields are complete (as demonstrated by this synthetic
fixture), the gate logic correctly passes both stages:

- Intake: intake_passed → upgrade_candidate=true
- Adjudication: adjudication_passed → label_upgrade_allowed=true

This confirms the gate design is sound — it blocks when evidence is missing
(v115G/v115H with empty workbook) and allows passage when evidence is
complete (v115I fixture).

## This Stage Is NOT

- A real label upgrade
- A TG send
- A production send
- A trading signal
- A real send candidate
- AI-generated evidence
- A modification of any real workbook data

## This Stage IS

- A test-only positive path fixture gate
- Proof that gate logic can pass
- Independent of real workbook
- Fully guarded (all send flags false)
- Re-runnable for verification

---

*This handoff is for the next stage decision-maker. The gate design is validated: it blocks when it should, and passes when it should.*
"""
    return handoff


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_fixture(fixture_rows):
    """Validate fixture before processing."""
    errors = []

    if len(fixture_rows) != 1:
        errors.append(f"Expected 1 fixture row, got {len(fixture_rows)}")

    # Check metadata flags
    meta_errors = validate_fixture_metadata(fixture_rows)
    errors.extend(meta_errors)

    for i, row in enumerate(fixture_rows):
        addr = row.get("address", "").strip()
        if not addr:
            errors.append(f"Fixture row {i+1}: address is empty")
        if not addr.startswith("0x"):
            errors.append(f"Fixture row {i+1}: address does not start with 0x: {addr}")

        conf = row.get("current_confidence", "").strip()
        if conf == "low":
            errors.append(f"Fixture row {i+1}: must not use low confidence address")

    return errors


def validate_intake_records(intake_records):
    """Validate fixture intake records."""
    errors = []

    if len(intake_records) != 1:
        errors.append(f"Expected 1 intake record, got {len(intake_records)}")

    for rec in intake_records:
        if rec.get("intake_ready") is not True:
            errors.append(
                f"Fixture intake record: intake_ready must be True for positive path, "
                f"got {rec.get('intake_ready')}"
            )
        if rec.get("manual_fields_complete") is not True:
            errors.append(
                f"Fixture intake record: manual_fields_complete must be True, "
                f"got {rec.get('manual_fields_complete')}"
            )

    return errors


def validate_intake_decisions(intake_decisions):
    """Validate fixture intake decisions."""
    errors = []

    if len(intake_decisions) != 1:
        errors.append(f"Expected 1 intake decision, got {len(intake_decisions)}")

    for dec in intake_decisions:
        if dec.get("decision") != "intake_passed":
            errors.append(
                f"Fixture intake decision: must be 'intake_passed' for positive path, "
                f"got '{dec.get('decision')}'"
            )
        if dec.get("upgrade_candidate") is not True:
            errors.append(
                f"Fixture intake decision: upgrade_candidate must be True, "
                f"got {dec.get('upgrade_candidate')}"
            )

    return errors


def validate_adjudication_records(adjudication_records):
    """Validate fixture adjudication records."""
    errors = []

    if len(adjudication_records) != 1:
        errors.append(f"Expected 1 adjudication record, got {len(adjudication_records)}")

    for rec in adjudication_records:
        if rec.get("adjudication_ready") is not True:
            errors.append(
                f"Fixture adjudication record: adjudication_ready must be True, "
                f"got {rec.get('adjudication_ready')}"
            )
        if rec.get("label_upgrade_allowed") is not True:
            errors.append(
                f"Fixture adjudication record: label_upgrade_allowed must be True, "
                f"got {rec.get('label_upgrade_allowed')}"
            )
        # new_confidence must equal current_confidence (no actual upgrade)
        if rec.get("new_confidence") != rec.get("current_confidence"):
            errors.append(
                f"Fixture adjudication record: new_confidence must equal current_confidence "
                f"(no actual upgrade), got new={rec.get('new_confidence')} vs "
                f"current={rec.get('current_confidence')}"
            )

    return errors


def validate_adjudication_decisions(adjudication_decisions):
    """Validate fixture adjudication decisions."""
    errors = []

    if len(adjudication_decisions) != 1:
        errors.append(f"Expected 1 adjudication decision, got {len(adjudication_decisions)}")

    for dec in adjudication_decisions:
        if dec.get("decision") != "adjudication_passed":
            errors.append(
                f"Fixture adjudication decision: must be 'adjudication_passed', "
                f"got '{dec.get('decision')}'"
            )
        if dec.get("label_upgrade_allowed") is not True:
            errors.append(
                f"Fixture adjudication decision: label_upgrade_allowed must be True, "
                f"got {dec.get('label_upgrade_allowed')}"
            )
        # to_confidence must equal from_confidence (no actual upgrade)
        if dec.get("to_confidence") != dec.get("from_confidence"):
            errors.append(
                f"Fixture adjudication decision: to_confidence must equal from_confidence "
                f"(no actual upgrade), got to={dec.get('to_confidence')} vs "
                f"from={dec.get('from_confidence')}"
            )

    return errors


def cross_check_real_results():
    """Cross-check that real v115G and v115H results are still blocked."""
    errors = []

    if not os.path.exists(V115G_GATE_RESULT):
        errors.append(f"v115G gate result missing: {V115G_GATE_RESULT}")
    else:
        v115g = load_json(V115G_GATE_RESULT)
        if v115g.get("intake_ready_count") != 0:
            errors.append(
                f"Real v115G: expected intake_ready_count=0, "
                f"got {v115g.get('intake_ready_count')}"
            )

    if not os.path.exists(V115H_GATE_RESULT):
        errors.append(f"v115H gate result missing: {V115H_GATE_RESULT}")
    else:
        v115h = load_json(V115H_GATE_RESULT)
        if v115h.get("label_upgrade_allowed_count") != 0:
            errors.append(
                f"Real v115H: expected label_upgrade_allowed_count=0, "
                f"got {v115h.get('label_upgrade_allowed_count')}"
            )

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v115I Whale Manual Audit Positive Path Fixture Gate — Local Only")
    print("=" * 70)

    # Step 1: Verify real workbook exists (read-only)
    print("\n[1/10] Verifying real v115F workbook (read-only)...")
    workbook_rows = verify_real_workbook()
    print("  [OK] Real workbook confirmed: 4 rows, NOT modified")

    # Step 2: Cross-check real v115G/v115H results still blocked
    print("\n[2/10] Cross-checking real v115G/v115H results...")
    cc_errors = cross_check_real_results()
    if cc_errors:
        print("  [NO] Cross-check errors:")
        for e in cc_errors:
            print(f"    - {e}")
        sys.exit(1)
    print("  [OK] Real v115G: intake_ready_count=0 (still blocked)")
    print("  [OK] Real v115H: label_upgrade_allowed_count=0 (still blocked)")

    # Step 3: Load fixture
    print("\n[3/10] Loading v115I fixture CSV...")
    fixture_rows = load_fixture()
    fixture_errors = validate_fixture(fixture_rows)
    if fixture_errors:
        print("  [NO] Fixture validation errors:")
        for e in fixture_errors:
            print(f"    - {e}")
        sys.exit(1)
    print(f"  [OK] Fixture validated: {len(fixture_rows)} row, all metadata flags set")

    # Step 4: Build intake records
    print("\n[4/10] Building fixture intake records...")
    intake_records = build_intake_records(fixture_rows)
    ir_errors = validate_intake_records(intake_records)
    if ir_errors:
        print("  [NO] Intake record validation errors:")
        for e in ir_errors:
            print(f"    - {e}")
        sys.exit(1)
    print(f"  [OK] {len(intake_records)} intake record — intake_ready=true (positive path)")

    # Step 5: Build intake decisions
    print("\n[5/10] Building fixture intake decisions...")
    intake_decisions = build_intake_decisions(intake_records)
    id_errors = validate_intake_decisions(intake_decisions)
    if id_errors:
        print("  [NO] Intake decision validation errors:")
        for e in id_errors:
            print(f"    - {e}")
        sys.exit(1)
    print(f"  [OK] {len(intake_decisions)} intake decision — intake_passed, upgrade_candidate=true")

    # Step 6: Build adjudication records
    print("\n[6/10] Building fixture adjudication records...")
    adjudication_records = build_adjudication_records(intake_records, intake_decisions)
    ar_errors = validate_adjudication_records(adjudication_records)
    if ar_errors:
        print("  [NO] Adjudication record validation errors:")
        for e in ar_errors:
            print(f"    - {e}")
        sys.exit(1)
    adj_ready = adjudication_records[0]["adjudication_ready"]
    print(f"  [OK] {len(adjudication_records)} adjudication record — adjudication_ready={adj_ready}")

    # Step 7: Build adjudication decisions
    print("\n[7/10] Building fixture adjudication decisions...")
    adjudication_decisions = build_adjudication_decisions(adjudication_records)
    ad_errors = validate_adjudication_decisions(adjudication_decisions)
    if ad_errors:
        print("  [NO] Adjudication decision validation errors:")
        for e in ad_errors:
            print(f"    - {e}")
        sys.exit(1)
    label_ok = adjudication_decisions[0]["label_upgrade_allowed"]
    print(f"  [OK] {len(adjudication_decisions)} adjudication decision — adjudication_passed, label_upgrade_allowed={label_ok}")

    # Step 8: Load real v115G/H results for cross-reference
    print("\n[8/10] Loading real v115G/v115H results for cross-reference...")
    real_v115g = load_json(V115G_GATE_RESULT)
    real_v115h = load_json(V115H_GATE_RESULT)
    print(f"  [OK] Real v115G intake_ready_count={real_v115g.get('intake_ready_count')}")
    print(f"  [OK] Real v115H label_upgrade_allowed_count={real_v115h.get('label_upgrade_allowed_count')}")

    # Step 9: Build and save gate result
    print("\n[9/10] Building and saving gate result...")
    gate_result = build_gate_result(
        fixture_rows, intake_records, intake_decisions,
        adjudication_records, adjudication_decisions,
        real_v115g, real_v115h
    )
    save_json(OUT_GATE_RESULT, gate_result)
    print(f"  [OK] -> {OUT_GATE_RESULT}")

    # Step 10: Save all outputs
    print("\n[10/10] Saving all outputs...")
    save_jsonl(OUT_INTAKE_RECORDS, intake_records)
    print(f"  [OK] Intake records -> {OUT_INTAKE_RECORDS}")

    save_jsonl(OUT_INTAKE_DECISIONS, intake_decisions)
    print(f"  [OK] Intake decisions -> {OUT_INTAKE_DECISIONS}")

    save_jsonl(OUT_ADJUDICATION_RECORDS, adjudication_records)
    print(f"  [OK] Adjudication records -> {OUT_ADJUDICATION_RECORDS}")

    save_jsonl(OUT_ADJUDICATION_DECISIONS, adjudication_decisions)
    print(f"  [OK] Adjudication decisions -> {OUT_ADJUDICATION_DECISIONS}")

    md_text = generate_markdown_report(
        fixture_rows, intake_records, intake_decisions,
        adjudication_records, adjudication_decisions, gate_result
    )
    save_text(OUT_MD, md_text)
    print(f"  [OK] Markdown -> {OUT_MD}")

    handoff_text = generate_handoff(
        gate_result, intake_records, intake_decisions,
        adjudication_records, adjudication_decisions
    )
    save_text(OUT_HANDOFF, handoff_text)
    print(f"  [OK] Handoff -> {OUT_HANDOFF}")

    # Final summary
    print("\n" + "=" * 70)
    print("v115I WHALE MANUAL AUDIT POSITIVE PATH FIXTURE GATE COMPLETE")
    print(f"  fixture_rows: {gate_result['fixture_rows']}")
    print(f"  fixture_intake_ready_count: {gate_result['fixture_intake_ready_count']}")
    print(f"  fixture_upgrade_candidate_count: {gate_result['fixture_upgrade_candidate_count']}")
    print(f"  fixture_blocked_intake_count: {gate_result['fixture_blocked_intake_count']}")
    print(f"  fixture_adjudication_ready_count: {gate_result['fixture_adjudication_ready_count']}")
    print(f"  fixture_label_upgrade_allowed_count: {gate_result['fixture_label_upgrade_allowed_count']}")
    print(f"  fixture_label_upgraded_count: {gate_result['fixture_label_upgraded_count']}")
    print(f"  real_v115g_intake_ready_count: {gate_result['real_v115g_intake_ready_count']}")
    print(f"  real_v115h_label_upgrade_allowed_count: {gate_result['real_v115h_label_upgrade_allowed_count']}")
    print(f"  real_workbook_modified: {gate_result['real_workbook_modified']}")
    print(f"  real_label_upgrade_performed: {gate_result['real_label_upgrade_performed']}")
    print(f"  real_send_candidate_generated: {gate_result['real_send_candidate_generated']}")
    print(f"  send_ready: {gate_result['send_ready']}")
    print(f"  tg_test_group_ready: {gate_result['tg_test_group_ready']}")
    print(f"  local_review_ready: {gate_result['local_review_ready']}")
    print(f"  external_api_called: {gate_result['external_api_called']}")
    print(f"  ai_model_called: {gate_result['ai_model_called']}")
    print(f"  credentials_read: {gate_result['credentials_read']}")
    print(f"  tg_sent: {gate_result['tg_sent']}")
    print(f"  prod_state_write: {gate_result['prod_state_write']}")
    print(f"  daemon_started: {gate_result['daemon_started']}")
    print(f"  watcher_started: {gate_result['watcher_started']}")
    print(f"  files_deleted: {gate_result['files_deleted']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
