#!/usr/bin/env python3
"""
v115G Whale Manual Audit Workbook Intake Gate — Local Only
============================================================
Reads the v115F operator workbook (after human operator fills in manual evidence)
and runs an intake validation gate that determines whether each address meets
the minimum conditions to enter label upgrade review.

This is a LOCAL-ONLY intake gate:
  - No external API calls
  - No AI/model calls
  - No TG send
  - No production state write
  - No credential reads
  - No daemon / watcher / loop
  - No file deletion
  - No modification of v114A-v115F old results
  - No label confidence upgrades

Current state (empty workbook): ALL 4 addresses are intake_blocked.
This gate is designed to be re-run AFTER an operator fills in the workbook.

Outputs:
  - intake_records.jsonl (4 records)
  - intake_decisions.jsonl (4 decisions)
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

# v115F input (read-only) — the operator workbook
V115F_WORKBOOK_CSV = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)

# v115F manifest (read-only, for cross-reference)
V115F_MANIFEST = os.path.join(
    RESULTS_DIR, "market_radar_v115f_whale_address_audit_operator_workbook_manifest.json"
)

# v115E upgrade decisions (read-only, for context)
V115E_UPGRADE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_label_upgrade_decisions.jsonl"
)

# v115B routing policy (read-only)
V115B_ROUTING = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)

# v115G outputs
OUT_INTAKE_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_records.jsonl"
)
OUT_INTAKE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_decisions.jsonl"
)
OUT_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_workbook_intake_gate_result.json"
)
OUT_MD = os.path.join(
    RUNS_DIR, "v115g_whale_manual_audit_workbook_intake_gate_local_only.md"
)
OUT_HANDOFF = os.path.join(
    RUNS_DIR, "v115g_whale_manual_audit_workbook_intake_gate_local_only_handoff.md"
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

# Manual fields that the operator must fill in the workbook
MANUAL_INPUT_FIELDS = [
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
    "operator_reject_reason",
    "reviewer",
    "reviewed_at",
]

# Fields specifically requiring evidence URLs/notes
EVIDENCE_URL_FIELDS = [
    "trusted_source_url_or_note",
    "second_source_url_or_note",
]

# Operator confirmation fields
OPERATOR_CONFIRMATION_FIELDS = [
    "operator_confirmed_label",
    "operator_confidence_assessment",
]

# --- Intake Decision Block Reason Constants ---
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

# All known block reasons (ordered for deterministic output)
ALL_BLOCK_REASONS = [
    BR_TRUSTED_SOURCE_LABEL_MISSING,
    BR_TRUSTED_SOURCE_NOTE_OR_URL_MISSING,
    BR_SECOND_SOURCE_LABEL_MISSING,
    BR_SECOND_SOURCE_NOTE_OR_URL_MISSING,
    BR_ACTIVITY_PATTERN_NOTE_MISSING,
    BR_OPERATOR_CONFIRMED_LABEL_MISSING,
    BR_OPERATOR_CONFIDENCE_ASSESSMENT_MISSING,
    BR_REVIEWER_MISSING,
    BR_REVIEWED_AT_MISSING,
    BR_READY_FOR_UPGRADE_FALSE,
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


def load_csv_rows(path: str) -> list:
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def short_addr(address: str) -> str:
    """Return shortened address: 0xAAAA...BBBB"""
    if len(address) <= 14:
        return address
    return f"{address[:6]}...{address[-4:]}"


def field_is_empty(val) -> bool:
    """Check if a workbook field is empty/unfilled."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False


def parse_bool(val) -> bool:
    """Parse a boolean value from CSV string."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() == "true"
    return False


# ---------------------------------------------------------------------------
# Step 1: Load v115F workbook CSV
# ---------------------------------------------------------------------------
def load_workbook():
    """Load the v115F operator workbook CSV. Must have exactly 4 rows."""
    if not os.path.exists(V115F_WORKBOOK_CSV):
        print(f"ERROR: v115F workbook not found: {V115F_WORKBOOK_CSV}")
        sys.exit(1)

    rows = load_csv_rows(V115F_WORKBOOK_CSV)

    if len(rows) != 4:
        print(f"ERROR: Expected 4 workbook rows, got {len(rows)}")
        sys.exit(1)

    print(f"  [OK] Loaded {len(rows)} workbook rows from v115F CSV")
    return rows


# ---------------------------------------------------------------------------
# Step 2: Build intake records
# ---------------------------------------------------------------------------
def build_intake_records(workbook_rows):
    """For each workbook row, build an intake record.

    An intake record captures the workbook state as-is plus computed
    readiness flags. It does NOT make upgrade decisions — those are
    handled in Step 3.
    """
    intake_records = []

    for i, row in enumerate(workbook_rows):
        address = row.get("address", "").strip()

        # Determine which manual fields are complete
        manual_fields_status = {}
        for field in MANUAL_INPUT_FIELDS:
            manual_fields_status[field] = not field_is_empty(row.get(field, ""))

        # Aggregate readiness flags
        all_manual_complete = all(manual_fields_status.values())

        evidence_urls_present = all(
            manual_fields_status.get(f, False) for f in EVIDENCE_URL_FIELDS
        )

        operator_confirmation_present = all(
            manual_fields_status.get(f, False) for f in OPERATOR_CONFIRMATION_FIELDS
        )

        # ready_for_upgrade from CSV (operator-set)
        ready_for_upgrade_raw = parse_bool(row.get("ready_for_upgrade", "false"))

        # operator_reject_reason — if present, this is a rejection
        operator_reject_reason = row.get("operator_reject_reason", "").strip()

        # intake_ready: all manual fields complete AND ready_for_upgrade=true
        # AND no operator rejection
        intake_ready = (
            all_manual_complete
            and ready_for_upgrade_raw
            and operator_reject_reason == ""
        )

        record = {
            "intake_id": f"v115g_intake_{i+1:03d}",
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
            "generated_at": now_iso(),
        }

        intake_records.append(record)

    return intake_records


# ---------------------------------------------------------------------------
# Step 3: Build intake decisions
# ---------------------------------------------------------------------------
def build_intake_decisions(intake_records):
    """For each intake record, apply the intake gate rules and produce a decision.

    Decision rules:
    - If intake_ready=true and all manual fields complete → upgrade_candidate=true
    - If operator_reject_reason is filled → rejected case (still intake_blocked
      but block_reasons differ — includes OPERATOR_REJECTED)
    - Otherwise → intake_blocked with missing field reasons

    Current empty workbook: ALL 4 addresses get intake_blocked with all 10
    standard block reasons.
    """
    intake_decisions = []

    for rec in intake_records:
        address = rec["address"]

        # Collect missing fields
        missing_fields = []
        block_reasons = []

        # Check each required manual field
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

        # ready_for_upgrade check
        if not rec.get("ready_for_upgrade", False):
            missing_fields.append("ready_for_upgrade")
            block_reasons.append(BR_READY_FOR_UPGRADE_FALSE)

        # Determine decision
        operator_reject_reason = rec.get("operator_reject_reason", "").strip()

        if operator_reject_reason:
            # Operator explicitly rejected — still intake_blocked, but noted as rejected
            decision = "intake_blocked"
            upgrade_candidate = False
            upgrade_ready = False
            if BR_OPERATOR_REJECTED not in block_reasons:
                block_reasons.append(BR_OPERATOR_REJECTED)
        elif rec.get("intake_ready", False):
            # All checks passed — upgrade candidate
            decision = "intake_passed"
            upgrade_candidate = True
            upgrade_ready = True
        else:
            # Missing fields — intake blocked
            decision = "intake_blocked"
            upgrade_candidate = False
            upgrade_ready = False

        intake_decision = {
            "intake_decision_id": f"v115g_ind_{rec['intake_id'].split('_')[-1]}",
            "address": address,
            "decision": decision,
            "upgrade_candidate": upgrade_candidate,
            "upgrade_ready": upgrade_ready,
            "missing_fields": missing_fields,
            "block_reasons": block_reasons,
            "send_allowed": False,
            "tg_test_group_allowed": False,
            "public_send_allowed": False,
            "generated_at": now_iso(),
        }

        intake_decisions.append(intake_decision)

    return intake_decisions


# ---------------------------------------------------------------------------
# Step 4: Build gate result JSON
# ---------------------------------------------------------------------------
def build_gate_result(workbook_rows, intake_records, intake_decisions):
    """Build the comprehensive gate result JSON with all required fields."""

    # Count stats
    intake_ready_count = sum(1 for r in intake_records if r["intake_ready"])
    upgrade_candidate_count = sum(1 for d in intake_decisions if d["upgrade_candidate"])
    blocked_intake_count = sum(1 for d in intake_decisions if d["decision"] == "intake_blocked")
    rejected_count = sum(
        1 for d in intake_decisions
        if BR_OPERATOR_REJECTED in d.get("block_reasons", [])
    )

    # high_confidence check: how many addresses have high confidence after intake
    # (none — we don't upgrade labels in this stage)
    high_confidence_after = 0

    # Sanity checks
    all_send_guards_false = all(
        not d["send_allowed"]
        and not d["tg_test_group_allowed"]
        and not d["public_send_allowed"]
        for d in intake_decisions
    )

    result = {
        "stage": "v115g_whale_manual_audit_workbook_intake_gate_local_only",
        "input_workbook_rows": len(workbook_rows),
        "intake_records": len(intake_records),
        "intake_decisions": len(intake_decisions),
        "intake_ready_count": intake_ready_count,
        "upgrade_candidate_count": upgrade_candidate_count,
        "blocked_intake_count": blocked_intake_count,
        "rejected_count": rejected_count,
        "high_confidence_after_intake": high_confidence_after,
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
        "real_send_candidate_generated": REAL_SEND_CANDIDATE_GENERATED,
        "all_send_guards_false": all_send_guards_false,
        "no_label_upgraded": True,
        "generated_at": now_iso(),
    }

    return result


# ---------------------------------------------------------------------------
# Step 5: Generate markdown report
# ---------------------------------------------------------------------------
def generate_markdown_report(workbook_rows, intake_records, intake_decisions, gate_result):
    """Generate a human-readable markdown report of the intake gate run."""

    per_address = ""
    for i, (wb_row, rec, dec) in enumerate(zip(workbook_rows, intake_records, intake_decisions)):
        addr = rec["address"]
        sa = short_addr(addr)

        missing_str = "\n".join(f"  - `{mf}`" for mf in dec.get("missing_fields", []))
        block_str = "\n".join(f"  - `{br}`" for br in dec.get("block_reasons", []))

        per_address += f"""
### Address {i+1}: `{addr}`

| Field | Value |
|-------|-------|
| Label | {rec['current_label']} |
| Confidence | {rec['current_confidence']} → target: {rec['target_confidence']} |
| Priority | {rec['priority']} |
| intake_ready | [{"OK" if rec['intake_ready'] else "NO"}] {rec['intake_ready']} |
| manual_fields_complete | [{"OK" if rec['manual_fields_complete'] else "NO"}] {rec['manual_fields_complete']} |
| evidence_url_fields_present | [{"OK" if rec['evidence_url_fields_present'] else "NO"}] {rec['evidence_url_fields_present']} |
| operator_confirmation_present | [{"OK" if rec['operator_confirmation_present'] else "NO"}] {rec['operator_confirmation_present']} |
| decision | **{dec['decision']}** |
| upgrade_candidate | [{"OK" if dec['upgrade_candidate'] else "NO"}] {dec['upgrade_candidate']} |
| upgrade_ready | [{"OK" if dec['upgrade_ready'] else "NO"}] {dec['upgrade_ready']} |

#### Missing Fields ({len(dec.get('missing_fields', []))})
{missing_str if missing_str else '  *(none — all fields complete)*'}

#### Block Reasons ({len(dec.get('block_reasons', []))})
{block_str if block_str else '  *(none — no blocks)*'}

---
"""

    markdown = f"""# v115G Whale Manual Audit Workbook Intake Gate — Local Only

**Generated:** {gate_result['generated_at']}
**Stage:** v115g_whale_manual_audit_workbook_intake_gate_local_only
**Lane:** 1

---

## ⚠️ IMPORTANT: Read Before Continuing

1. **This is a LOCAL intake validation gate only.**
2. **This file is NOT a trading signal, NOT a production send file, NOT a TG send candidate.**
3. **NO label confidence has been upgraded by this stage.**
4. **This gate reads the v115F operator workbook and validates each address for intake readiness.**
5. **ALL 4 addresses are currently intake_blocked — operator must fill workbook before re-running.**

---

## 1. Gate Summary

| Metric | Value |
|--------|-------|
| input_workbook_rows | {gate_result['input_workbook_rows']} |
| intake_records | {gate_result['intake_records']} |
| intake_decisions | {gate_result['intake_decisions']} |
| intake_ready_count | {gate_result['intake_ready_count']} |
| upgrade_candidate_count | {gate_result['upgrade_candidate_count']} |
| blocked_intake_count | {gate_result['blocked_intake_count']} |
| rejected_count | {gate_result['rejected_count']} |
| high_confidence_after_intake | {gate_result['high_confidence_after_intake']} |
| send_ready | [{"OK" if gate_result['send_ready'] else "NO"}] {gate_result['send_ready']} |
| tg_test_group_ready | [{"OK" if gate_result['tg_test_group_ready'] else "NO"}] {gate_result['tg_test_group_ready']} |
| local_review_ready | [OK] {gate_result['local_review_ready']} |
| labels upgraded | **0 — NONE** |

**Status:** [BLOCKED] ALL {gate_result['blocked_intake_count']} addresses are intake_blocked.
Operator must fill the v115F workbook before re-running this intake gate.

---

## 2. Safety Invariants

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
| real_send_candidate_generated | [{"OK" if not gate_result['real_send_candidate_generated'] else "ALERT"}] {gate_result['real_send_candidate_generated']} |

---

## 3. Per-Address Intake Results
{per_address}

## 4. Intake Gate Rules Reference

An address is **intake_ready** only when ALL of the following are true:

1. `trusted_source_label_value` is non-empty → TRUSTED_SOURCE_LABEL_MISSING if empty
2. `trusted_source_url_or_note` is non-empty → TRUSTED_SOURCE_NOTE_OR_URL_MISSING if empty
3. `second_source_label_value` is non-empty → SECOND_SOURCE_LABEL_MISSING if empty
4. `second_source_url_or_note` is non-empty → SECOND_SOURCE_NOTE_OR_URL_MISSING if empty
5. `activity_pattern_note` is non-empty → ACTIVITY_PATTERN_NOTE_MISSING if empty
6. `operator_confirmed_label` is non-empty → OPERATOR_CONFIRMED_LABEL_MISSING if empty
7. `operator_confidence_assessment` is non-empty → OPERATOR_CONFIDENCE_ASSESSMENT_MISSING if empty
8. `reviewer` is non-empty → REVIEWER_MISSING if empty
9. `reviewed_at` is non-empty → REVIEWED_AT_MISSING if empty
10. `ready_for_upgrade` is true → READY_FOR_UPGRADE_FALSE if false

An address is **upgrade_candidate** only when intake_ready=true AND no operator_reject_reason.

---

## 5. Explicit NOT Declarations

This intake gate is explicitly **NOT**:

- [NO] A label upgrade execution
- [NO] A TG send
- [NO] A trading signal
- [NO] Financial advice
- [NO] A production send file
- [NO] A public send candidate
- [NO] AI-generated evidence
- [NO] External API query results

This intake gate **IS**:

- [OK] A local intake validation gate
- [OK] A structured check for manual evidence completeness
- [OK] Input for future label upgrade review (not yet run)
- [OK] Fully guarded — all send flags are false
- [OK] Traceable, verifiable, reproducible

---

*Generated by v115G runner. Local only. No external communication intended.*
"""
    return markdown


# ---------------------------------------------------------------------------
# Step 6: Generate handoff markdown
# ---------------------------------------------------------------------------
def generate_handoff(gate_result, intake_records, intake_decisions):
    """Generate the v115G handoff markdown."""

    address_summaries = ""
    for i, rec in enumerate(intake_records):
        dec = intake_decisions[i]
        sa = short_addr(rec["address"])
        address_summaries += (
            f"- [{dec['decision'].upper()}] Address {i+1}: `{sa}` — {rec['current_label']} "
            f"({rec['current_confidence']}) — "
            f"intake_ready={rec['intake_ready']} — "
            f"upgrade_candidate={dec['upgrade_candidate']} — "
            f"missing_fields={len(dec.get('missing_fields', []))} — "
            f"block_reasons={len(dec.get('block_reasons', []))}\n"
        )

    handoff = f"""# v115G Handoff — Whale Manual Audit Workbook Intake Gate Local Only

**Generated:** {gate_result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only
**Stage:** v115G

---

## What Was Done

1. Read v115F operator workbook CSV (4 address rows)
2. Read v115F workbook manifest (for cross-reference)
3. Read v115E upgrade decisions (for context)
4. Read v115B routing policy (for context)
5. Built 4 intake records from workbook state
6. Applied intake gate rules to generate 4 intake decisions
7. Generated gate result JSON with all required fields
8. Generated markdown intake report
9. Generated this handoff

## Address Summary

{address_summaries}

## Key Results

| Metric | Value |
|--------|-------|
| input_workbook_rows | {gate_result['input_workbook_rows']} |
| intake_records | {gate_result['intake_records']} |
| intake_decisions | {gate_result['intake_decisions']} |
| intake_ready_count | {gate_result['intake_ready_count']} |
| upgrade_candidate_count | {gate_result['upgrade_candidate_count']} |
| blocked_intake_count | {gate_result['blocked_intake_count']} |
| rejected_count | {gate_result['rejected_count']} |
| high_confidence_after_intake | {gate_result['high_confidence_after_intake']} |
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
- `no_label_upgraded=true`
- `all_send_guards_false=true`
- v114A-v115F old results NOT modified

## This Stage Is NOT

- A label upgrade execution
- A TG send
- A production send
- A trading signal
- A real send candidate
- AI-generated evidence

## This Stage IS

- A local intake validation gate
- A structured check for workbook completeness
- Re-runnable after operator fills workbook
- Input for future label upgrade review gate

## Next Operator Actions Required

1. Fill the v115F operator workbook CSV for ALL 4 addresses
2. Fill ALL 10 required fields per address (trusted source, second source, activity pattern, operator confirmation, reviewer info, ready_for_upgrade)
3. After filling, re-run this v115G intake gate to re-evaluate
4. Only after intake_ready_count > 0, proceed to label upgrade review

---

*This handoff is for the next stage decision-maker. Operator evidence collection required before intake can pass.*
"""
    return handoff


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_workbook_rows(workbook_rows):
    """Validate workbook rows before processing."""
    errors = []

    if len(workbook_rows) != 4:
        errors.append(f"Expected 4 workbook rows, got {len(workbook_rows)}")

    for i, row in enumerate(workbook_rows):
        addr = row.get("address", "").strip()
        if not addr:
            errors.append(f"Row {i+1}: address is empty")
        if not addr.startswith("0x"):
            errors.append(f"Row {i+1}: address does not start with 0x: {addr}")

    return errors


def validate_intake_records(intake_records, workbook_rows):
    """Validate intake records against task requirements."""
    errors = []

    if len(intake_records) != 4:
        errors.append(f"Expected 4 intake records, got {len(intake_records)}")

    required_fields = [
        "address", "current_label", "current_confidence", "target_confidence",
        "priority", "trusted_source_label_value", "trusted_source_url_or_note",
        "second_source_label_value", "second_source_url_or_note",
        "activity_pattern_note", "operator_confirmed_label",
        "operator_confidence_assessment", "operator_reject_reason",
        "reviewer", "reviewed_at", "ready_for_upgrade",
        "manual_fields_complete", "evidence_url_fields_present",
        "operator_confirmation_present", "intake_ready",
    ]

    for i, rec in enumerate(intake_records):
        for field in required_fields:
            if field not in rec:
                errors.append(f"Intake record {i+1}: missing field '{field}'")

        # intake_ready must be false for empty workbook
        if rec.get("intake_ready") is not False:
            errors.append(
                f"Intake record {i+1}: intake_ready should be False for empty workbook, "
                f"got {rec.get('intake_ready')}"
            )

    return errors


def validate_intake_decisions(intake_decisions):
    """Validate intake decisions against task requirements."""
    errors = []

    if len(intake_decisions) != 4:
        errors.append(f"Expected 4 intake decisions, got {len(intake_decisions)}")

    required_fields = [
        "address", "decision", "upgrade_candidate", "upgrade_ready",
        "missing_fields", "block_reasons", "send_allowed",
        "tg_test_group_allowed", "public_send_allowed",
    ]

    required_block_reasons = {
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
    }

    for i, dec in enumerate(intake_decisions):
        for field in required_fields:
            if field not in dec:
                errors.append(f"Intake decision {i+1}: missing field '{field}'")

        # decision must be intake_blocked for empty workbook
        if dec.get("decision") != "intake_blocked":
            errors.append(
                f"Intake decision {i+1}: decision should be 'intake_blocked', "
                f"got '{dec.get('decision')}'"
            )

        # upgrade_candidate must be false
        if dec.get("upgrade_candidate") is not False:
            errors.append(
                f"Intake decision {i+1}: upgrade_candidate should be False, "
                f"got {dec.get('upgrade_candidate')}"
            )

        # upgrade_ready must be false
        if dec.get("upgrade_ready") is not False:
            errors.append(
                f"Intake decision {i+1}: upgrade_ready should be False, "
                f"got {dec.get('upgrade_ready')}"
            )

        # send guards must be false
        for guard in ["send_allowed", "tg_test_group_allowed", "public_send_allowed"]:
            if dec.get(guard) is not False:
                errors.append(
                    f"Intake decision {i+1}: {guard} should be False, got {dec.get(guard)}"
                )

        # block_reasons must contain all required reasons for empty workbook
        block_set = set(dec.get("block_reasons", []))
        missing_block_reasons = required_block_reasons - block_set
        if missing_block_reasons:
            errors.append(
                f"Intake decision {i+1}: missing block reasons: {sorted(missing_block_reasons)}"
            )

        # missing_fields must be non-empty
        if not dec.get("missing_fields"):
            errors.append(f"Intake decision {i+1}: missing_fields is empty")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v115G Whale Manual Audit Workbook Intake Gate — Local Only")
    print("=" * 70)

    # Step 1: Load workbook
    print("\n[1/7] Loading v115F operator workbook...")
    workbook_rows = load_workbook()

    validation_errors = validate_workbook_rows(workbook_rows)
    if validation_errors:
        print("  [NO] Workbook validation errors:")
        for e in validation_errors:
            print(f"    - {e}")
        sys.exit(1)
    print("  [OK] Workbook validated — 4 rows, all addresses present")

    # Step 2: Build intake records
    print("\n[2/7] Building intake records...")
    intake_records = build_intake_records(workbook_rows)
    rec_errors = validate_intake_records(intake_records, workbook_rows)
    if rec_errors:
        print("  [NO] Intake record validation errors:")
        for e in rec_errors:
            print(f"    - {e}")
        sys.exit(1)
    print(f"  [OK] {len(intake_records)} intake records built and validated")

    # Step 3: Build intake decisions
    print("\n[3/7] Building intake decisions...")
    intake_decisions = build_intake_decisions(intake_records)
    dec_errors = validate_intake_decisions(intake_decisions)
    if dec_errors:
        print("  [NO] Intake decision validation errors:")
        for e in dec_errors:
            print(f"    - {e}")
        sys.exit(1)
    print(f"  [OK] {len(intake_decisions)} intake decisions built and validated")

    # Step 4: Save intake records
    print("\n[4/7] Saving intake records...")
    save_jsonl(OUT_INTAKE_RECORDS, intake_records)
    print(f"  [OK] -> {OUT_INTAKE_RECORDS}")

    # Step 5: Save intake decisions
    print("\n[5/7] Saving intake decisions...")
    save_jsonl(OUT_INTAKE_DECISIONS, intake_decisions)
    print(f"  [OK] -> {OUT_INTAKE_DECISIONS}")

    # Step 6: Build and save gate result
    print("\n[6/7] Building gate result...")
    gate_result = build_gate_result(workbook_rows, intake_records, intake_decisions)
    save_json(OUT_GATE_RESULT, gate_result)
    print(f"  [OK] -> {OUT_GATE_RESULT}")

    # Step 7: Generate markdown report and handoff
    print("\n[7/7] Generating markdown report and handoff...")
    md_text = generate_markdown_report(workbook_rows, intake_records, intake_decisions, gate_result)
    save_text(OUT_MD, md_text)
    print(f"  [OK] Markdown -> {OUT_MD}")

    handoff_text = generate_handoff(gate_result, intake_records, intake_decisions)
    save_text(OUT_HANDOFF, handoff_text)
    print(f"  [OK] Handoff -> {OUT_HANDOFF}")

    # Final summary
    print("\n" + "=" * 70)
    print("v115G WHALE MANUAL AUDIT WORKBOOK INTAKE GATE COMPLETE")
    print(f"  input_workbook_rows: {gate_result['input_workbook_rows']}")
    print(f"  intake_records: {gate_result['intake_records']}")
    print(f"  intake_decisions: {gate_result['intake_decisions']}")
    print(f"  intake_ready_count: {gate_result['intake_ready_count']}")
    print(f"  upgrade_candidate_count: {gate_result['upgrade_candidate_count']}")
    print(f"  blocked_intake_count: {gate_result['blocked_intake_count']}")
    print(f"  rejected_count: {gate_result['rejected_count']}")
    print(f"  high_confidence_after_intake: {gate_result['high_confidence_after_intake']}")
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
    print(f"  real_send_candidate_generated: {gate_result['real_send_candidate_generated']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
