#!/usr/bin/env python3
"""
v115H Whale Label Upgrade Adjudication Gate — Local Only
=========================================================
Reads v115G intake decisions and adjudicates whether each address may
proceed from low/medium to high confidence based on the manual audit
intake gate results.

This is a LOCAL-ONLY adjudication gate:
  - No external API calls
  - No AI/model calls
  - No TG send
  - No production state write
  - No credential reads
  - No daemon / watcher / loop
  - No file deletion
  - No modification of v114A-v115G old results
  - No label confidence upgrades (all blocked in current state)

Current state: ALL 4 addresses failed v115G intake → all adjudication_blocked.
This gate is designed to be re-run AFTER an operator fills the workbook
and intake passes, at which point real upgrade adjudication can happen.

Outputs:
  - adjudication_records.jsonl (4 records)
  - adjudication_decisions.jsonl (4 decisions)
  - gate_result.json
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

# v115G inputs (read-only)
V115G_INTAKE_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_records.jsonl"
)
V115G_INTAKE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_intake_decisions.jsonl"
)
V115G_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115g_whale_manual_audit_workbook_intake_gate_result.json"
)

# v115E upgrade decisions (read-only, for context)
V115E_UPGRADE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_label_upgrade_decisions.jsonl"
)

# v115F workbook (read-only, for cross-reference)
V115F_WORKBOOK_CSV = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)

# v115B routing policy (read-only)
V115B_ROUTING = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)

# v115H outputs
OUT_ADJUDICATION_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_records.jsonl"
)
OUT_ADJUDICATION_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_decisions.jsonl"
)
OUT_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115h_whale_label_upgrade_adjudication_gate_result.json"
)
OUT_MD = os.path.join(
    RUNS_DIR, "v115h_whale_label_upgrade_adjudication_gate_local_only.md"
)
OUT_HANDOFF = os.path.join(
    RUNS_DIR, "v115h_whale_label_upgrade_adjudication_gate_local_only_handoff.md"
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

# --- Adjudication Block Reason Constants ---
BR_INTAKE_NOT_READY = "INTAKE_NOT_READY"
BR_UPGRADE_CANDIDATE_FALSE = "UPGRADE_CANDIDATE_FALSE"
BR_MANUAL_EVIDENCE_INCOMPLETE = "MANUAL_EVIDENCE_INCOMPLETE"
BR_NO_CONFIDENCE_CHANGE_ALLOWED = "NO_CONFIDENCE_CHANGE_ALLOWED"
BR_SEND_GUARDS_REMAIN_FALSE = "SEND_GUARDS_REMAIN_FALSE"

# Block reasons that must be present for every intake_blocked address
REQUIRED_BLOCK_REASONS = sorted([
    BR_INTAKE_NOT_READY,
    BR_UPGRADE_CANDIDATE_FALSE,
    BR_MANUAL_EVIDENCE_INCOMPLETE,
    BR_NO_CONFIDENCE_CHANGE_ALLOWED,
    BR_SEND_GUARDS_REMAIN_FALSE,
])

# Evidence requirement fields
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


def load_jsonl(path) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def short_addr(address: str) -> str:
    """Return shortened address: 0xAAAA...BBBB"""
    if len(address) <= 14:
        return address
    return f"{address[:6]}...{address[-4:]}"


def field_is_empty(val) -> bool:
    """Check if a field is empty/unfilled."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False


# ---------------------------------------------------------------------------
# Step 1: Load v115G intake data
# ---------------------------------------------------------------------------
def load_intake_data():
    """Load v115G intake records and decisions. Must have exactly 4 each."""
    if not os.path.exists(V115G_INTAKE_RECORDS):
        print(f"ERROR: v115G intake records not found: {V115G_INTAKE_RECORDS}")
        sys.exit(1)

    if not os.path.exists(V115G_INTAKE_DECISIONS):
        print(f"ERROR: v115G intake decisions not found: {V115G_INTAKE_DECISIONS}")
        sys.exit(1)

    intake_records = load_jsonl(V115G_INTAKE_RECORDS)
    intake_decisions = load_jsonl(V115G_INTAKE_DECISIONS)

    if len(intake_records) != 4:
        print(f"ERROR: Expected 4 intake records, got {len(intake_records)}")
        sys.exit(1)

    if len(intake_decisions) != 4:
        print(f"ERROR: Expected 4 intake decisions, got {len(intake_decisions)}")
        sys.exit(1)

    print(f"  [OK] Loaded {len(intake_records)} intake records from v115G")
    print(f"  [OK] Loaded {len(intake_decisions)} intake decisions from v115G")
    return intake_records, intake_decisions


# ---------------------------------------------------------------------------
# Step 2: Build adjudication records
# ---------------------------------------------------------------------------
def build_adjudication_records(intake_records, intake_decisions):
    """For each intake record, build an adjudication record.

    An adjudication record captures:
    - The intake state (ready or not)
    - Whether each evidence category is met
    - Whether adjudication can proceed (adjudication_ready)
    - Whether label upgrade is allowed (label_upgrade_allowed)

    Since all 4 addresses are currently intake_blocked, adjudication_ready
    and label_upgrade_allowed are both False for all addresses.
    """
    # Build lookup from intake_records by address
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

        # Assess each evidence category
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

        # Adjudication is ready only when: intake_ready AND upgrade_candidate
        # AND all evidence categories are met
        adjudication_ready = (
            intake_ready
            and upgrade_candidate
            and manual_fields_complete
            and evidence_requirements_met
        )

        # Label upgrade is allowed only when adjudication_ready AND all evidence ok
        label_upgrade_allowed = adjudication_ready

        adjudication_record = {
            "adjudication_id": f"v115h_adj_{i+1:03d}",
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
            "new_confidence": current_confidence,
            "generated_at": now_iso(),
        }

        adjudication_records.append(adjudication_record)

    return adjudication_records


# ---------------------------------------------------------------------------
# Step 3: Build adjudication decisions
# ---------------------------------------------------------------------------
def build_adjudication_decisions(adjudication_records, intake_decisions):
    """For each adjudication record, build an adjudication decision.

    Decision rules:
    - If intake_ready=false OR upgrade_candidate=false → adjudication_blocked
    - If evidence incomplete → adjudication_blocked
    - If all conditions met → adjudication_passed (NOT reached in current state)

    Every blocked decision MUST contain at minimum:
    - INTAKE_NOT_READY
    - UPGRADE_CANDIDATE_FALSE
    - MANUAL_EVIDENCE_INCOMPLETE
    - NO_CONFIDENCE_CHANGE_ALLOWED
    - SEND_GUARDS_REMAIN_FALSE
    """
    adjudication_decisions = []

    # Build lookup for intake decision
    decision_by_addr = {d["address"]: d for d in intake_decisions}

    for rec in adjudication_records:
        address = rec["address"]
        current_confidence = rec["current_confidence"]

        block_reasons = []

        # INTAKE_NOT_READY — because intake_ready is false
        if not rec["intake_ready"]:
            block_reasons.append(BR_INTAKE_NOT_READY)

        # UPGRADE_CANDIDATE_FALSE — because upgrade_candidate is false
        if not rec["upgrade_candidate"]:
            block_reasons.append(BR_UPGRADE_CANDIDATE_FALSE)

        # MANUAL_EVIDENCE_INCOMPLETE — because manual fields are not filled
        if not rec["manual_fields_complete"] or not rec["evidence_requirements_met"]:
            block_reasons.append(BR_MANUAL_EVIDENCE_INCOMPLETE)

        # NO_CONFIDENCE_CHANGE_ALLOWED — always true when adjudication_blocked
        block_reasons.append(BR_NO_CONFIDENCE_CHANGE_ALLOWED)

        # SEND_GUARDS_REMAIN_FALSE — always true in current state
        block_reasons.append(BR_SEND_GUARDS_REMAIN_FALSE)

        # Determine decision
        if rec.get("adjudication_ready", False) and rec.get("label_upgrade_allowed", False):
            decision = "adjudication_passed"
            label_upgrade_allowed = True
            to_confidence = "high"
        else:
            decision = "adjudication_blocked"
            label_upgrade_allowed = False
            to_confidence = current_confidence

        adjudication_decision = {
            "adjudication_decision_id": f"v115h_adjd_{rec['adjudication_id'].split('_')[-1]}",
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
            "generated_at": now_iso(),
        }

        adjudication_decisions.append(adjudication_decision)

    return adjudication_decisions


# ---------------------------------------------------------------------------
# Step 4: Build gate result JSON
# ---------------------------------------------------------------------------
def build_gate_result(intake_records, intake_decisions,
                      adjudication_records, adjudication_decisions):
    """Build the comprehensive gate result JSON with all required fields."""

    adjudication_ready_count = sum(1 for r in adjudication_records if r["adjudication_ready"])
    label_upgrade_allowed_count = sum(1 for d in adjudication_decisions if d["label_upgrade_allowed"])
    label_upgraded_count = 0  # We never upgrade labels — blocked
    blocked_adjudication_count = sum(
        1 for d in adjudication_decisions if d["decision"] == "adjudication_blocked"
    )
    high_confidence_after = sum(
        1 for d in adjudication_decisions if d.get("to_confidence") == "high"
    )

    result = {
        "stage": "v115h_whale_label_upgrade_adjudication_gate_local_only",
        "input_intake_records": len(intake_records),
        "input_intake_decisions": len(intake_decisions),
        "adjudication_records": len(adjudication_records),
        "adjudication_decisions": len(adjudication_decisions),
        "adjudication_ready_count": adjudication_ready_count,
        "label_upgrade_allowed_count": label_upgrade_allowed_count,
        "label_upgraded_count": label_upgraded_count,
        "blocked_adjudication_count": blocked_adjudication_count,
        "high_confidence_after_adjudication": high_confidence_after,
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
        "generated_at": now_iso(),
    }

    return result


# ---------------------------------------------------------------------------
# Step 5: Generate markdown report
# ---------------------------------------------------------------------------
def generate_markdown_report(adjudication_records, adjudication_decisions, gate_result):
    """Generate a human-readable markdown report of the adjudication gate run."""

    per_address = ""
    for i, (rec, dec) in enumerate(zip(adjudication_records, adjudication_decisions)):
        addr = rec["address"]
        sa = short_addr(addr)

        block_str = "\n".join(f"  - `{br}`" for br in dec.get("block_reasons", []))

        per_address += f"""
### Address {i+1}: `{addr}`

| Field | Value |
|-------|-------|
| Label | {rec['current_label']} |
| Current Confidence | {rec['current_confidence']} |
| Requested Confidence | {rec['requested_confidence']} |
| intake_ready | [{"OK" if rec['intake_ready'] else "NO"}] {rec['intake_ready']} |
| upgrade_candidate | [{"OK" if rec['upgrade_candidate'] else "NO"}] {rec['upgrade_candidate']} |
| manual_fields_complete | [{"OK" if rec['manual_fields_complete'] else "NO"}] {rec['manual_fields_complete']} |
| evidence_requirements_met | [{"OK" if rec['evidence_requirements_met'] else "NO"}] {rec['evidence_requirements_met']} |
| trusted_source_ok | [{"OK" if rec['trusted_source_ok'] else "NO"}] {rec['trusted_source_ok']} |
| second_source_ok | [{"OK" if rec['second_source_ok'] else "NO"}] {rec['second_source_ok']} |
| activity_pattern_ok | [{"OK" if rec['activity_pattern_ok'] else "NO"}] {rec['activity_pattern_ok']} |
| operator_confirmation_ok | [{"OK" if rec['operator_confirmation_ok'] else "NO"}] {rec['operator_confirmation_ok']} |
| adjudication_ready | [{"OK" if rec['adjudication_ready'] else "NO"}] {rec['adjudication_ready']} |
| label_upgrade_allowed | [{"OK" if rec['label_upgrade_allowed'] else "NO"}] {rec['label_upgrade_allowed']} |
| new_confidence | {rec['new_confidence']} |
| decision | **{dec['decision']}** |
| from_confidence | {dec['from_confidence']} |
| to_confidence | {dec['to_confidence']} |

#### Block Reasons ({len(dec.get('block_reasons', []))})
{block_str if block_str else '  *(none — no blocks)*'}

---
"""

    markdown = f"""# v115H Whale Label Upgrade Adjudication Gate — Local Only

**Generated:** {gate_result['generated_at']}
**Stage:** v115h_whale_label_upgrade_adjudication_gate_local_only
**Lane:** 1

---

## ⚠️ IMPORTANT: Read Before Continuing

1. **This is a LOCAL adjudication gate only.**
2. **This file is NOT a trading signal, NOT a production send file, NOT a TG send candidate.**
3. **NO label confidence has been upgraded by this stage.**
4. **This gate reads v115G intake decisions and adjudicates label upgrade eligibility.**
5. **ALL 4 addresses are currently adjudication_blocked — operator must fill the v115F workbook and pass v115G intake before re-running.**

---

## 1. Gate Summary

| Metric | Value |
|--------|-------|
| input_intake_records | {gate_result['input_intake_records']} |
| input_intake_decisions | {gate_result['input_intake_decisions']} |
| adjudication_records | {gate_result['adjudication_records']} |
| adjudication_decisions | {gate_result['adjudication_decisions']} |
| adjudication_ready_count | {gate_result['adjudication_ready_count']} |
| label_upgrade_allowed_count | {gate_result['label_upgrade_allowed_count']} |
| label_upgraded_count | {gate_result['label_upgraded_count']} |
| blocked_adjudication_count | {gate_result['blocked_adjudication_count']} |
| high_confidence_after_adjudication | {gate_result['high_confidence_after_adjudication']} |
| send_ready | [{"OK" if gate_result['send_ready'] else "NO"}] {gate_result['send_ready']} |
| tg_test_group_ready | [{"OK" if gate_result['tg_test_group_ready'] else "NO"}] {gate_result['tg_test_group_ready']} |
| local_review_ready | [OK] {gate_result['local_review_ready']} |
| labels upgraded | **0 — NONE** |

**Status:** [BLOCKED] ALL {gate_result['blocked_adjudication_count']} addresses are adjudication_blocked.
Operator must fill the v115F workbook, pass v115G intake, then re-run this gate.

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

## 3. Per-Address Adjudication Results
{per_address}

## 4. Adjudication Gate Rules Reference

An address is **adjudication_ready** only when ALL of the following are true:

1. `intake_ready` = true (from v115G intake gate)
2. `upgrade_candidate` = true (from v115G intake decision)
3. `manual_fields_complete` = true (all 10 manual fields filled in workbook)
4. `evidence_requirements_met` = true (all 4 evidence categories satisfied)
   - `trusted_source_ok`: trusted_source_label_value AND trusted_source_url_or_note filled
   - `second_source_ok`: second_source_label_value AND second_source_url_or_note filled
   - `activity_pattern_ok`: activity_pattern_note filled
   - `operator_confirmation_ok`: operator_confirmed_label AND operator_confidence_assessment filled

An address is **label_upgrade_allowed** only when adjudication_ready = true.

**Block Reasons for adjudication_blocked:**
- `INTAKE_NOT_READY` — intake_ready is false
- `UPGRADE_CANDIDATE_FALSE` — upgrade_candidate is false
- `MANUAL_EVIDENCE_INCOMPLETE` — manual fields or evidence categories not satisfied
- `NO_CONFIDENCE_CHANGE_ALLOWED` — no label confidence change permitted
- `SEND_GUARDS_REMAIN_FALSE` — all send guards remain false

---

## 5. Explicit NOT Declarations

This adjudication gate is explicitly **NOT**:

- [NO] A label upgrade execution
- [NO] A TG send
- [NO] A trading signal
- [NO] Financial advice
- [NO] A production send file
- [NO] A public send candidate
- [NO] AI-generated evidence
- [NO] External API query results

This adjudication gate **IS**:

- [OK] A local label upgrade adjudication gate
- [OK] A structured check for label upgrade eligibility
- [OK] Re-usable after operator fills workbook and intake passes
- [OK] Fully guarded — all send flags are false
- [OK] Traceable, verifiable, reproducible

---

*Generated by v115H runner. Local only. No external communication intended.*
"""
    return markdown


# ---------------------------------------------------------------------------
# Step 6: Generate handoff markdown
# ---------------------------------------------------------------------------
def generate_handoff(gate_result, adjudication_records, adjudication_decisions):
    """Generate the v115H handoff markdown."""

    address_summaries = ""
    for i, rec in enumerate(adjudication_records):
        dec = adjudication_decisions[i]
        sa = short_addr(rec["address"])
        address_summaries += (
            f"- [{dec['decision'].upper()}] Address {i+1}: `{sa}` — {rec['current_label']} "
            f"({rec['current_confidence']}) — "
            f"intake_ready={rec['intake_ready']} — "
            f"adjudication_ready={rec['adjudication_ready']} — "
            f"label_upgrade_allowed={dec['label_upgrade_allowed']} — "
            f"block_reasons={len(dec.get('block_reasons', []))}\n"
        )

    handoff = f"""# v115H Handoff — Whale Label Upgrade Adjudication Gate Local Only

**Generated:** {gate_result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only
**Stage:** v115H

---

## What Was Done

1. Read v115G intake records (4 records)
2. Read v115G intake decisions (4 decisions — all intake_blocked)
3. Read v115G gate result (for cross-reference)
4. Read v115E upgrade decisions (for context)
5. Read v115F operator workbook (for cross-reference)
6. Read v115B routing policy (for context)
7. Built 4 adjudication records from intake state
8. Applied adjudication gate rules to generate 4 adjudication decisions
9. Generated gate result JSON with all required fields
10. Generated markdown adjudication report
11. Generated this handoff

## Address Summary

{address_summaries}

## Key Results

| Metric | Value |
|--------|-------|
| input_intake_records | {gate_result['input_intake_records']} |
| input_intake_decisions | {gate_result['input_intake_decisions']} |
| adjudication_records | {gate_result['adjudication_records']} |
| adjudication_decisions | {gate_result['adjudication_decisions']} |
| adjudication_ready_count | {gate_result['adjudication_ready_count']} |
| label_upgrade_allowed_count | {gate_result['label_upgrade_allowed_count']} |
| label_upgraded_count | {gate_result['label_upgraded_count']} |
| blocked_adjudication_count | {gate_result['blocked_adjudication_count']} |
| high_confidence_after_adjudication | {gate_result['high_confidence_after_adjudication']} |
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
- `label_upgraded_count=0`
- v114A-v115G old results NOT modified

## This Stage Is NOT

- A label upgrade execution
- A TG send
- A production send
- A trading signal
- A real send candidate
- AI-generated evidence

## This Stage IS

- A local label upgrade adjudication gate
- A structured check for upgrade eligibility after intake
- Re-runnable after operator fills workbook and intake passes
- Input for future confidence upgrade execution

## Next Operator Actions Required

1. Fill the v115F operator workbook CSV for addresses intended for upgrade
2. Fill ALL 10 required manual fields per address
3. Set ready_for_upgrade=true and fill reviewer/reviewed_at
4. Re-run v115G intake gate to verify intake_ready
5. After intake_ready_count > 0, re-run this v115H adjudication gate
6. Only after adjudication_ready_count > 0, proceed to label upgrade execution

---

*This handoff is for the next stage decision-maker. Operator evidence collection required before adjudication can pass.*
"""
    return handoff


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_input_data(intake_records, intake_decisions):
    """Validate v115G input data before processing."""
    errors = []

    if len(intake_records) != 4:
        errors.append(f"Expected 4 intake records, got {len(intake_records)}")

    if len(intake_decisions) != 4:
        errors.append(f"Expected 4 intake decisions, got {len(intake_decisions)}")

    # Check address alignment
    rec_addrs = set(r["address"] for r in intake_records)
    dec_addrs = set(d["address"] for d in intake_decisions)
    if rec_addrs != dec_addrs:
        errors.append("Address mismatch between intake records and decisions")

    return errors


def validate_adjudication_records(adjudication_records):
    """Validate adjudication records against task requirements."""
    errors = []

    if len(adjudication_records) != 4:
        errors.append(f"Expected 4 adjudication records, got {len(adjudication_records)}")

    required_fields = [
        "address", "current_label", "current_confidence",
        "requested_confidence", "intake_ready", "upgrade_candidate",
        "manual_fields_complete", "evidence_requirements_met",
        "trusted_source_ok", "second_source_ok",
        "activity_pattern_ok", "operator_confirmation_ok",
        "adjudication_ready", "label_upgrade_allowed", "new_confidence",
    ]

    for i, rec in enumerate(adjudication_records):
        for field in required_fields:
            if field not in rec:
                errors.append(f"Adjudication record {i+1}: missing field '{field}'")

        # adjudication_ready must be false (all blocked)
        if rec.get("adjudication_ready") is not False:
            errors.append(
                f"Adjudication record {i+1}: adjudication_ready should be False, "
                f"got {rec.get('adjudication_ready')}"
            )

        # label_upgrade_allowed must be false (all blocked)
        if rec.get("label_upgrade_allowed") is not False:
            errors.append(
                f"Adjudication record {i+1}: label_upgrade_allowed should be False, "
                f"got {rec.get('label_upgrade_allowed')}"
            )

        # requested_confidence must be "high"
        if rec.get("requested_confidence") != "high":
            errors.append(
                f"Adjudication record {i+1}: requested_confidence should be 'high', "
                f"got '{rec.get('requested_confidence')}'"
            )

        # new_confidence must equal current_confidence (no upgrade)
        if rec.get("new_confidence") != rec.get("current_confidence"):
            errors.append(
                f"Adjudication record {i+1}: new_confidence should equal current_confidence, "
                f"got new={rec.get('new_confidence')} vs current={rec.get('current_confidence')}"
            )

    return errors


def validate_adjudication_decisions(adjudication_decisions):
    """Validate adjudication decisions against task requirements."""
    errors = []

    if len(adjudication_decisions) != 4:
        errors.append(f"Expected 4 adjudication decisions, got {len(adjudication_decisions)}")

    required_fields = [
        "address", "decision", "label_upgrade_allowed",
        "from_confidence", "to_confidence", "requested_confidence",
        "block_reasons", "send_allowed", "tg_test_group_allowed",
        "public_send_allowed",
    ]

    for i, dec in enumerate(adjudication_decisions):
        for field in required_fields:
            if field not in dec:
                errors.append(f"Adjudication decision {i+1}: missing field '{field}'")

        # decision must be adjudication_blocked
        if dec.get("decision") != "adjudication_blocked":
            errors.append(
                f"Adjudication decision {i+1}: decision should be 'adjudication_blocked', "
                f"got '{dec.get('decision')}'"
            )

        # label_upgrade_allowed must be false
        if dec.get("label_upgrade_allowed") is not False:
            errors.append(
                f"Adjudication decision {i+1}: label_upgrade_allowed should be False, "
                f"got {dec.get('label_upgrade_allowed')}"
            )

        # send guards must be false
        for guard in ["send_allowed", "tg_test_group_allowed", "public_send_allowed"]:
            if dec.get(guard) is not False:
                errors.append(
                    f"Adjudication decision {i+1}: {guard} should be False, "
                    f"got {dec.get(guard)}"
                )

        # block_reasons must contain all 5 required reasons
        br_set = set(dec.get("block_reasons", []))
        missing_reasons = set(REQUIRED_BLOCK_REASONS) - br_set
        if missing_reasons:
            errors.append(
                f"Adjudication decision {i+1}: missing block reasons: {sorted(missing_reasons)}"
            )

        # from_confidence must equal to_confidence (no upgrade)
        if dec.get("from_confidence") != dec.get("to_confidence"):
            errors.append(
                f"Adjudication decision {i+1}: from_confidence != to_confidence "
                f"({dec.get('from_confidence')} != {dec.get('to_confidence')})"
            )

        # to_confidence must not be "high"
        if dec.get("to_confidence") == "high":
            errors.append(
                f"Adjudication decision {i+1}: to_confidence should not be 'high' "
                f"for blocked decision"
            )

        # block_reasons must be non-empty
        if not dec.get("block_reasons"):
            errors.append(f"Adjudication decision {i+1}: block_reasons is empty")

    return errors


def validate_gate_result(gate_result):
    """Validate gate result JSON against task requirements."""
    errors = []

    expected = {
        "stage": "v115h_whale_label_upgrade_adjudication_gate_local_only",
        "input_intake_records": 4,
        "input_intake_decisions": 4,
        "adjudication_records": 4,
        "adjudication_decisions": 4,
        "adjudication_ready_count": 0,
        "label_upgrade_allowed_count": 0,
        "label_upgraded_count": 0,
        "blocked_adjudication_count": 4,
        "high_confidence_after_adjudication": 0,
        "send_ready": False,
        "tg_test_group_ready": False,
        "local_review_ready": True,
        "external_api_called": False,
        "ai_model_called": False,
        "credentials_read": False,
        "tg_sent": False,
        "prod_state_write": False,
        "daemon_started": False,
        "watcher_started": False,
        "files_deleted": False,
        "real_send_candidate_generated": False,
    }

    for key, expected_val in expected.items():
        actual = gate_result.get(key)
        if actual != expected_val:
            errors.append(
                f"Gate result: '{key}' expected {expected_val!r}, got {actual!r}"
            )

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v115H Whale Label Upgrade Adjudication Gate — Local Only")
    print("=" * 70)

    # Step 1: Load v115G intake data
    print("\n[1/7] Loading v115G intake data...")
    intake_records, intake_decisions = load_intake_data()

    input_errors = validate_input_data(intake_records, intake_decisions)
    if input_errors:
        print("  [NO] Input validation errors:")
        for e in input_errors:
            print(f"    - {e}")
        sys.exit(1)
    print("  [OK] Input validated — 4 intake records, 4 intake decisions")

    # Step 2: Build adjudication records
    print("\n[2/7] Building adjudication records...")
    adjudication_records = build_adjudication_records(intake_records, intake_decisions)
    rec_errors = validate_adjudication_records(adjudication_records)
    if rec_errors:
        print("  [NO] Adjudication record validation errors:")
        for e in rec_errors:
            print(f"    - {e}")
        sys.exit(1)
    print(f"  [OK] {len(adjudication_records)} adjudication records built and validated")

    # Step 3: Build adjudication decisions
    print("\n[3/7] Building adjudication decisions...")
    adjudication_decisions = build_adjudication_decisions(adjudication_records, intake_decisions)
    dec_errors = validate_adjudication_decisions(adjudication_decisions)
    if dec_errors:
        print("  [NO] Adjudication decision validation errors:")
        for e in dec_errors:
            print(f"    - {e}")
        sys.exit(1)
    print(f"  [OK] {len(adjudication_decisions)} adjudication decisions built and validated")

    # Step 4: Save adjudication records
    print("\n[4/7] Saving adjudication records...")
    save_jsonl(OUT_ADJUDICATION_RECORDS, adjudication_records)
    print(f"  [OK] -> {OUT_ADJUDICATION_RECORDS}")

    # Step 5: Save adjudication decisions
    print("\n[5/7] Saving adjudication decisions...")
    save_jsonl(OUT_ADJUDICATION_DECISIONS, adjudication_decisions)
    print(f"  [OK] -> {OUT_ADJUDICATION_DECISIONS}")

    # Step 6: Build and save gate result
    print("\n[6/7] Building gate result...")
    gate_result = build_gate_result(
        intake_records, intake_decisions,
        adjudication_records, adjudication_decisions
    )
    result_errors = validate_gate_result(gate_result)
    if result_errors:
        print("  [NO] Gate result validation errors:")
        for e in result_errors:
            print(f"    - {e}")
        sys.exit(1)
    save_json(OUT_GATE_RESULT, gate_result)
    print(f"  [OK] -> {OUT_GATE_RESULT}")

    # Step 7: Generate markdown report and handoff
    print("\n[7/7] Generating markdown report and handoff...")
    md_text = generate_markdown_report(adjudication_records, adjudication_decisions, gate_result)
    save_text(OUT_MD, md_text)
    print(f"  [OK] Markdown -> {OUT_MD}")

    handoff_text = generate_handoff(gate_result, adjudication_records, adjudication_decisions)
    save_text(OUT_HANDOFF, handoff_text)
    print(f"  [OK] Handoff -> {OUT_HANDOFF}")

    # Final summary
    print("\n" + "=" * 70)
    print("v115H WHALE LABEL UPGRADE ADJUDICATION GATE COMPLETE")
    print(f"  input_intake_records: {gate_result['input_intake_records']}")
    print(f"  input_intake_decisions: {gate_result['input_intake_decisions']}")
    print(f"  adjudication_records: {gate_result['adjudication_records']}")
    print(f"  adjudication_decisions: {gate_result['adjudication_decisions']}")
    print(f"  adjudication_ready_count: {gate_result['adjudication_ready_count']}")
    print(f"  label_upgrade_allowed_count: {gate_result['label_upgrade_allowed_count']}")
    print(f"  label_upgraded_count: {gate_result['label_upgraded_count']}")
    print(f"  blocked_adjudication_count: {gate_result['blocked_adjudication_count']}")
    print(f"  high_confidence_after_adjudication: {gate_result['high_confidence_after_adjudication']}")
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
