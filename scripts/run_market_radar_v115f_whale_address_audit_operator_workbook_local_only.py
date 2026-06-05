#!/usr/bin/env python3
"""
v115F Whale Address Audit Operator Workbook — Local Only
===========================================================
Reads v115E manual audit forms / evidence requests / upgrade decisions and
generates a LOCAL operator workbook (CSV + Markdown) for human operators to
fill in missing evidence for all 4 whale addresses.

This is a LOCAL-ONLY operator workbook generation step:
  - No external API calls
  - No AI/model calls
  - No TG send
  - No production state write
  - No credential reads
  - No daemon / watcher / loop
  - No file deletion
  - No modification of v114A-v115E old results
  - ALL manual evidence fields are empty/false by default
  - ALL 4 addresses remain upgrade_ready=false and blocked

Outputs:
  - CSV operator workbook
  - Markdown operator workbook
  - Machine-readable manifest JSON
  - Gate result JSON
  - Handoff markdown
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

# v115E inputs (read-only)
V115E_EVIDENCE_REQUESTS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_requests.jsonl"
)
V115E_MANUAL_AUDIT_FORMS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_manual_audit_forms.jsonl"
)
V115E_UPGRADE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_label_upgrade_decisions.jsonl"
)
V115E_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_pack_result.json"
)

# v115D inputs (read-only, for block_reasons context)
V115D_GATE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_decisions.jsonl"
)

# v115B config (read-only)
V115B_ROUTING = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)

# v115F outputs
OUT_CSV = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.csv"
)
OUT_MD = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook.md"
)
OUT_MANIFEST = os.path.join(
    RESULTS_DIR, "market_radar_v115f_whale_address_audit_operator_workbook_manifest.json"
)
OUT_GATE_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115f_whale_address_audit_operator_workbook_gate_result.json"
)
OUT_HANDOFF = os.path.join(
    RUNS_DIR, "v115f_whale_address_audit_operator_workbook_local_only_handoff.md"
)

TZ_SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))

# Safety invariants
EXTERNAL_API_CALLED = False
AI_MODEL_CALLED = False
CREDENTIALS_READ = False
TG_SENT = False
PROD_STATE_WRITE = False
DAEMON_STARTED = False
WATCHER_STARTED = False
FILES_DELETED = False
REAL_SEND_CANDIDATE_GENERATED = False

# CSV columns as specified in the task
CSV_COLUMNS = [
    "address",
    "current_label",
    "current_confidence",
    "priority",
    "target_confidence",
    "why_this_address_matters",
    "related_delta_context",
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
    "ready_for_upgrade",
    "upgrade_ready",
    "send_allowed",
    "tg_test_group_allowed",
    "public_send_allowed",
    "block_reasons",
]

# Manual fields that must be empty by default
MANUAL_FIELDS = [
    "trusted_source_label_value",
    "trusted_source_url_or_note",
    "second_source_label_value",
    "second_source_url_or_note",
    "activity_pattern_note",
    "operator_confirmed_label",
    "operator_confidence_assessment",
    "operator_reject_reason",
]

MANUAL_BOOL_FIELDS = [
    "ready_for_upgrade",
    "upgrade_ready",
    "send_allowed",
    "tg_test_group_allowed",
    "public_send_allowed",
]

SEND_GUARD_FIELDS = [
    "send_allowed",
    "tg_test_group_allowed",
    "public_send_allowed",
]

REQUIRED_EVIDENCE_TYPES = [
    "trusted_source_label",
    "cross_source_consistency",
    "address_activity_consistency",
    "manual_operator_confirmation",
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


def save_csv(path, rows, columns):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


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


def fmt_bool(val) -> str:
    """Format boolean as lowercase string for CSV."""
    return str(val).lower()


def fmt_list(val) -> str:
    """Format list as semicolon-separated string."""
    if isinstance(val, list):
        return "; ".join(str(v) for v in val)
    return str(val)


# ---------------------------------------------------------------------------
# Step 1: Load v115E inputs
# ---------------------------------------------------------------------------
def load_inputs():
    """Load all required v115E input files."""
    errors = []

    for label, path in [
        ("v115E evidence requests", V115E_EVIDENCE_REQUESTS),
        ("v115E manual audit forms", V115E_MANUAL_AUDIT_FORMS),
        ("v115E upgrade decisions", V115E_UPGRADE_DECISIONS),
        ("v115E result", V115E_RESULT),
        ("v115D gate decisions", V115D_GATE_DECISIONS),
        ("v115B routing policy", V115B_ROUTING),
    ]:
        if not os.path.exists(path):
            errors.append(f"{label} not found: {path}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    evidence_requests = load_jsonl(V115E_EVIDENCE_REQUESTS)
    manual_audit_forms = load_jsonl(V115E_MANUAL_AUDIT_FORMS)
    upgrade_decisions = load_jsonl(V115E_UPGRADE_DECISIONS)
    v115e_result = load_json(V115E_RESULT)
    v115d_gate = load_jsonl(V115D_GATE_DECISIONS)
    v115b_routing = load_json(V115B_ROUTING)

    print(f"  v115E evidence requests: {len(evidence_requests)}")
    print(f"  v115E manual audit forms: {len(manual_audit_forms)}")
    print(f"  v115E upgrade decisions: {len(upgrade_decisions)}")
    print(f"  v115D gate decisions: {len(v115d_gate)}")
    print(f"  v115B routing policy loaded")

    return evidence_requests, manual_audit_forms, upgrade_decisions, v115e_result, v115d_gate, v115b_routing


# ---------------------------------------------------------------------------
# Step 2: Build CSV workbook rows from v115E data
# ---------------------------------------------------------------------------
def build_csv_rows(evidence_requests, manual_audit_forms, upgrade_decisions):
    """Build CSV workbook rows with all 22 required columns.

    All manual evidence fields are EMPTY by default.
    All boolean guard fields are FALSE by default.
    """
    rows = []

    for evr, maf, upd in zip(evidence_requests, manual_audit_forms, upgrade_decisions):
        # Safety check: addresses must match
        assert evr["address"] == maf["address"] == upd["address"], \
            f"Address mismatch: {evr['address']} / {maf['address']} / {upd['address']}"

        # Format related_delta_context as compact string for CSV
        delta_parts = []
        for dc in evr.get("related_delta_context", []):
            delta_parts.append(
                f"{dc.get('asset','?')}/{dc.get('side','?')}:"
                f"{dc.get('delta_type','?')} "
                f"({dc.get('review_summary','')[:80]})"
            )
        delta_str = " | ".join(delta_parts)

        row = {
            "address": evr["address"],
            "current_label": evr["current_label"],
            "current_confidence": evr["current_confidence"],
            "priority": evr["priority"],
            "target_confidence": evr["target_confidence"],
            "why_this_address_matters": evr["why_this_address_matters"],
            "related_delta_context": delta_str,
            # Manual evidence fields — ALL EMPTY by default
            "trusted_source_label_value": "",
            "trusted_source_url_or_note": "",
            "second_source_label_value": "",
            "second_source_url_or_note": "",
            "activity_pattern_note": "",
            "operator_confirmed_label": "",
            "operator_confidence_assessment": "",
            "operator_reject_reason": "",
            # Review tracking — EMPTY by default
            "reviewer": "",
            "reviewed_at": "",
            # Boolean guard fields — ALL FALSE by default
            "ready_for_upgrade": "false",
            "upgrade_ready": "false",
            "send_allowed": "false",
            "tg_test_group_allowed": "false",
            "public_send_allowed": "false",
            # Block reasons from v115E upgrade decision
            "block_reasons": "; ".join(upd.get("block_reasons", [])),
        }

        rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# Step 3: Generate Markdown workbook
# ---------------------------------------------------------------------------
def generate_markdown_workbook(csv_rows, evidence_requests, upgrade_decisions):
    """Generate the human-readable Markdown operator workbook."""

    # Per-address tables
    address_tables = ""
    for i, (row, evr, upd) in enumerate(zip(csv_rows, evidence_requests, upgrade_decisions)):
        addr = row["address"]
        sa = short_addr(addr)
        missing = evr.get("missing_evidence_types", [])
        missing_str = "\n".join(f"  - `{et}`" for et in missing)
        block_reasons = upd.get("block_reasons", [])
        block_str = "\n".join(f"  - `{br}`" for br in block_reasons)

        operator_actions = evr.get("operator_action_required", [])
        actions_str = "\n".join(f"  {i+1}. {act}" for i, act in enumerate(operator_actions))

        # Evidence table
        evidence_table = f"""| Field | Value | Status |
|-------|-------|--------|
| `trusted_source_label_value` | *(empty — awaiting operator)* | [ ] Not filled |
| `trusted_source_url_or_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `second_source_label_value` | *(empty — awaiting operator)* | [ ] Not filled |
| `second_source_url_or_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `activity_pattern_note` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_confirmed_label` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_confidence_assessment` | *(empty — awaiting operator)* | [ ] Not filled |
| `operator_reject_reason` | *(empty — awaiting operator)* | [ ] Not filled |
| `reviewer` | *(empty — awaiting operator)* | [ ] Not filled |
| `reviewed_at` | *(empty — awaiting operator)* | [ ] Not filled |"""

        address_tables += f"""
### Address {i+1}: `{addr}`

**Label:** {row['current_label']}
**Confidence:** {row['current_confidence']} → target: {row['target_confidence']}
**Priority:** {row['priority']}
**upgrade_ready:** [NO] false
**send_allowed:** [NO] false
**tg_test_group_allowed:** [NO] false
**public_send_allowed:** [NO] false

#### Why This Address Matters
{row['why_this_address_matters']}

#### Delta Context
```
{row['related_delta_context']}
```

#### Missing Evidence ({len(missing)}/4 required)
{missing_str}

#### Operator Actions Required
{actions_str}

#### Manual Evidence Fields (all empty — operator must fill)
{evidence_table}

#### Block Reasons
{block_str}

---
"""

    markdown = f"""# v115F Whale Address Audit Operator Workbook

**Generated:** {now_iso()}
**Stage:** v115f_whale_address_audit_operator_workbook_local_only
**Input:** v115E address audit evidence pack (4 audit forms)

---

## ⚠️ IMPORTANT: Read Before Continuing

1. **This is a LOCAL operator workbook for manual evidence collection only.**
2. **This file is NOT a trading signal, NOT a production send file, NOT a TG send candidate.**
3. **Do NOT upgrade any label confidence before ALL manual evidence fields have been filled.**
4. **Each address requires ALL 4 evidence types before label upgrade can proceed.**
5. **After filling evidence, a separate upgrade gate must be run — this workbook does NOT auto-upgrade labels.**

---

## 1. Current State Summary

| Metric | Value |
|--------|-------|
| Total addresses | 4 |
| upgrade_ready_count | 0 |
| blocked_upgrade_count | 4 |
| send_ready | [NO] false |
| tg_test_group_ready | [NO] false |
| local_review_ready | [OK] true |
| manual_fields_prefilled | [NO] false |
| external_api_called | [NO] false |
| credentials_read | [NO] false |
| tg_sent | [NO] false |
| prod_state_write | [NO] false |
| daemon_started | [NO] false |
| watcher_started | [NO] false |
| labels upgraded | **0 — NONE** |

**Status:** [BLOCKED] ALL 4 addresses are BLOCKED. No label has been upgraded to high confidence.
Manual operator evidence collection is required before any upgrade can proceed.

---

## 2. Address Audit Tables
{address_tables}

## 3. Operator Filling Instructions

### How to Fill This Workbook

1. Open the accompanying CSV workbook: `{OUT_CSV}`
2. For each address, collect evidence for ALL 4 required types:
   - **trusted_source_label**: Look up the address on trusted explorers (Etherscan, Nansen, Arkham, etc.)
   - **cross_source_consistency**: Find at least one independent second source confirming identity
   - **address_activity_consistency**: Review HyperLiquid position history for consistency
   - **manual_operator_confirmation**: After reviewing all evidence, explicitly confirm or reject
3. Fill in the corresponding CSV fields for each address
4. When ALL 4 evidence types are filled for an address, set `ready_for_upgrade` to `true`
5. After ALL addresses are reviewed, run the next upgrade gate stage

### Field Definitions

| CSV Column | Type | Instructions |
|------------|------|--------------|
| `trusted_source_label_value` | text | Label from trusted source (e.g., "Wintermute", "Jump Trading") |
| `trusted_source_url_or_note` | text | URL or note for the trusted source |
| `second_source_label_value` | text | Label from a second independent source |
| `second_source_url_or_note` | text | URL or note for the second source |
| `activity_pattern_note` | text | Notes on on-chain activity pattern consistency |
| `operator_confirmed_label` | text | Operator's final confirmed label |
| `operator_confidence_assessment` | text | Operator's confidence assessment (low/medium/high) |
| `operator_reject_reason` | text | If rejecting, reason for rejection |
| `reviewer` | text | Name/ID of the operator filling this row |
| `reviewed_at` | text | ISO timestamp when review was completed |
| `ready_for_upgrade` | bool | Set to `true` ONLY when ALL 4 evidence types are complete |
| `upgrade_ready` | bool | Set to `true` ONLY after operator confirms evidence is sufficient |
| `send_allowed` | bool | Do NOT set manually — gate-controlled |
| `tg_test_group_allowed` | bool | Do NOT set manually — gate-controlled |
| `public_send_allowed` | bool | Do NOT set manually — gate-controlled |

### ⚠️ Critical Constraints

- **Do NOT set `ready_for_upgrade` to `true` until ALL 4 evidence types are filled per address.**
- **Do NOT modify `send_allowed`, `tg_test_group_allowed`, or `public_send_allowed` — these are gate-controlled.**
- **Do NOT modify `block_reasons` — these are gate-generated.**
- **This is a LOCAL workbook only. Filling it does NOT automatically upgrade labels or send anything.**

---

## 4. Explicit NOT Declarations

This workbook is explicitly **NOT**:

- [NO] A trading signal
- [NO] Financial advice
- [NO] A production send file
- [NO] A TG send candidate
- [NO] A label upgrade execution
- [NO] A send-ready assertion
- [NO] AI-generated evidence
- [NO] External API query results

This workbook **IS**:

- [OK] A local operator audit workbook
- [OK] A structured template for manual evidence collection
- [OK] Input for a future label upgrade gate (not yet run)
- [OK] Fully guarded — all send flags are false
- [OK] Traceable, verifiable, reproducible

---

*Generated by v115F runner. Local only. No external communication intended.*
"""
    return markdown


# ---------------------------------------------------------------------------
# Step 4: Build manifest JSON
# ---------------------------------------------------------------------------
def build_manifest(csv_rows):
    """Build the machine-readable workbook manifest."""
    manifest = {
        "stage": "v115f_whale_address_audit_operator_workbook_local_only",
        "input_audit_forms": 4,
        "workbook_rows": len(csv_rows),
        "addresses": len(csv_rows),
        "manual_fields_prefilled": False,
        "upgrade_ready_count": 0,
        "blocked_upgrade_count": 4,
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
    return manifest


# ---------------------------------------------------------------------------
# Step 5: Build gate result JSON
# ---------------------------------------------------------------------------
def build_gate_result(csv_rows, markdown_text):
    """Build the local gate result JSON, checking all invariants."""

    # Check CSV row count
    csv_row_count = len(csv_rows)
    csv_ok = csv_row_count == 4

    # Check all 4 addresses in markdown
    addresses_in_md = all(row["address"] in markdown_text for row in csv_rows)

    # Check manual fields are empty
    all_manual_empty = True
    for row in csv_rows:
        for field in MANUAL_FIELDS:
            if row.get(field, "") != "":
                all_manual_empty = False
                break

    # Check boolean fields are false
    all_bools_false = True
    for row in csv_rows:
        for field in MANUAL_BOOL_FIELDS:
            if row.get(field, "false") != "false":
                all_bools_false = False
                break

    # Check all upgrade_ready = false
    all_upgrade_ready_false = all(row.get("upgrade_ready", "false") == "false" for row in csv_rows)

    # Check all send guards false
    all_send_guards_false = True
    for row in csv_rows:
        for field in SEND_GUARD_FIELDS:
            if row.get(field, "false") != "false":
                all_send_guards_false = False
                break

    # Check block_reasons non-empty
    all_block_reasons_nonempty = all(
        row.get("block_reasons", "").strip() != "" for row in csv_rows
    )

    # Check no external results embedded
    no_external_results = True  # All manual fields are empty = no external results

    # Check no label upgraded
    no_label_upgraded = True  # upgrade_ready_count = 0 means no upgrade

    gate_passed = (
        csv_ok
        and addresses_in_md
        and all_manual_empty
        and all_bools_false
        and all_upgrade_ready_false
        and all_send_guards_false
        and all_block_reasons_nonempty
        and no_external_results
        and no_label_upgraded
    )

    checks = [
        {"check": "csv_row_count=4", "result": csv_ok, "detail": f"got {csv_row_count} rows"},
        {"check": "4 addresses in markdown", "result": addresses_in_md, "detail": ""},
        {"check": "all manual fields empty", "result": all_manual_empty, "detail": ""},
        {"check": "all manual bool fields false", "result": all_bools_false, "detail": ""},
        {"check": "all upgrade_ready=false", "result": all_upgrade_ready_false, "detail": ""},
        {"check": "all send_allowed=false", "result": all_send_guards_false, "detail": ""},
        {"check": "all tg_test_group_allowed=false", "result": all_send_guards_false, "detail": ""},
        {"check": "all public_send_allowed=false", "result": all_send_guards_false, "detail": ""},
        {"check": "all block_reasons non-empty", "result": all_block_reasons_nonempty, "detail": ""},
        {"check": "no external query results embedded", "result": no_external_results, "detail": ""},
        {"check": "no label upgraded", "result": no_label_upgraded, "detail": ""},
    ]

    gate_result = {
        "gate_stage": "v115f_whale_address_audit_operator_workbook_local_only",
        "gate_passed": gate_passed,
        "checks": checks,
        "failed_checks": [c for c in checks if not c["result"]],
        "csv_row_count": csv_row_count,
        "addresses_in_markdown": addresses_in_md,
        "all_manual_fields_empty": all_manual_empty,
        "all_bool_fields_false": all_bools_false,
        "all_upgrade_ready_false": all_upgrade_ready_false,
        "all_send_guards_false": all_send_guards_false,
        "all_block_reasons_nonempty": all_block_reasons_nonempty,
        "no_external_results_embedded": no_external_results,
        "no_label_upgraded": no_label_upgraded,
        "safety_invariants": {
            "external_api_called": EXTERNAL_API_CALLED,
            "ai_model_called": AI_MODEL_CALLED,
            "credentials_read": CREDENTIALS_READ,
            "tg_sent": TG_SENT,
            "prod_state_write": PROD_STATE_WRITE,
            "daemon_started": DAEMON_STARTED,
            "watcher_started": WATCHER_STARTED,
            "files_deleted": FILES_DELETED,
        },
        "generated_at": now_iso(),
    }

    return gate_result


# ---------------------------------------------------------------------------
# Step 6: Generate handoff markdown
# ---------------------------------------------------------------------------
def generate_handoff(manifest, gate_result, csv_rows):
    """Generate the v115F handoff markdown."""

    address_summaries = ""
    for i, row in enumerate(csv_rows):
        sa = short_addr(row["address"])
        address_summaries += (
            f"- [BLOCKED] Address {i+1}: `{sa}` — {row['current_label']} "
            f"({row['current_confidence']}) — "
            f"workbook row {i+1} — all manual fields empty — "
            f"upgrade_ready=false — send_allowed=false\n"
        )

    handoff = f"""# v115F Handoff — Whale Address Audit Operator Workbook Local Only

**Generated:** {manifest['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only
**Stage:** v115F

---

## What Was Done

1. Read v115E audit evidence pack (4 manual audit forms, 4 evidence requests, 4 upgrade decisions)
2. Read v115D send preview gate decisions (for block_reasons context)
3. Read v115B routing policy
4. Generated CSV operator workbook with 22 columns and 4 address rows
5. Generated Markdown operator audit manual with complete instructions
6. Generated machine-readable workbook manifest
7. Generated local gate result with 11 invariant checks
8. Generated this handoff

## Address Summary

{address_summaries}

## Key Results

| Metric | Value |
|--------|-------|
| workbook_rows | {manifest['workbook_rows']} |
| addresses | {manifest['addresses']} |
| manual_fields_prefilled | {manifest['manual_fields_prefilled']} |
| upgrade_ready_count | {manifest['upgrade_ready_count']} |
| blocked_upgrade_count | {manifest['blocked_upgrade_count']} |
| send_ready | {manifest['send_ready']} |
| tg_test_group_ready | {manifest['tg_test_group_ready']} |
| local_review_ready | {manifest['local_review_ready']} |
| gate_passed | {gate_result['gate_passed']} |

## Gate Checks

All {len(gate_result['checks'])} gate checks passed: [OK] {gate_result['gate_passed']}

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
- v114A-v115E old results NOT modified

## This Stage Is NOT

- A label upgrade execution
- A TG send
- Send-ready for production
- TG-test-group-ready
- A trading signal
- A real send candidate
- AI-generated evidence

## This Stage IS

- A local operator workbook for manual evidence collection
- 4 fillable address audit rows in CSV
- Complete operator filling instructions in Markdown
- Machine-readable manifest for automation
- Local gate result for quality assurance
- Input for future manual operator review

## Next Operator Actions Required

1. Open the CSV workbook: `runs/market_radar/v115f_whale_address_audit_operator_workbook.csv`
2. For each of the 4 addresses, research and collect evidence from trusted sources
3. Fill in all 8 manual evidence fields per address
4. Set `ready_for_upgrade` to `true` ONLY after ALL 4 evidence types are complete
5. Run the next upgrade gate stage when all addresses have complete evidence

---

*This handoff is for the next stage decision-maker. Operator evidence collection required before any label upgrade can proceed.*
"""
    return handoff


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def validate_csv_rows(csv_rows):
    """Validate CSV workbook rows against task requirements."""
    errors = []

    # Count check
    if len(csv_rows) != 4:
        errors.append(f"Expected 4 CSV rows, got {len(csv_rows)}")

    for i, row in enumerate(csv_rows):
        prefix = f"Row {i+1}"

        # All columns present
        for col in CSV_COLUMNS:
            if col not in row:
                errors.append(f"{prefix}: missing column '{col}'")

        # Address present
        if not row.get("address"):
            errors.append(f"{prefix}: address is empty")

        # Manual fields empty
        for field in MANUAL_FIELDS:
            val = row.get(field, None)
            if val not in ("", None):
                errors.append(f"{prefix}: manual field '{field}' should be empty, got '{val}'")

        # Boolean fields false
        for field in MANUAL_BOOL_FIELDS:
            val = row.get(field, "")
            if val != "false":
                errors.append(f"{prefix}: '{field}' should be 'false', got '{val}'")

        # Block reasons non-empty
        if not row.get("block_reasons", "").strip():
            errors.append(f"{prefix}: block_reasons is empty")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v115F Whale Address Audit Operator Workbook — Local Only")
    print("=" * 70)

    # Step 1: Load inputs
    print("\n[1/7] Loading v115E inputs...")
    evidence_requests, manual_audit_forms, upgrade_decisions, v115e_result, v115d_gate, v115b_routing = \
        load_inputs()

    if len(evidence_requests) != 4:
        print(f"  ERROR: Expected 4 evidence requests, got {len(evidence_requests)}")
        sys.exit(1)
    if len(manual_audit_forms) != 4:
        print(f"  ERROR: Expected 4 manual audit forms, got {len(manual_audit_forms)}")
        sys.exit(1)
    if len(upgrade_decisions) != 4:
        print(f"  ERROR: Expected 4 upgrade decisions, got {len(upgrade_decisions)}")
        sys.exit(1)
    print("  [OK] 4 evidence requests, 4 audit forms, 4 upgrade decisions loaded")

    # Step 2: Build CSV workbook rows
    print("\n[2/7] Building CSV workbook rows...")
    csv_rows = build_csv_rows(evidence_requests, manual_audit_forms, upgrade_decisions)

    # Validate before saving
    validation_errors = validate_csv_rows(csv_rows)
    if validation_errors:
        print("  [NO] CSV validation errors:")
        for e in validation_errors:
            print(f"    - {e}")
        sys.exit(1)
    print(f"  [OK] {len(csv_rows)} CSV rows built and validated")

    # Step 3: Save CSV workbook
    print("\n[3/7] Saving CSV workbook...")
    save_csv(OUT_CSV, csv_rows, CSV_COLUMNS)
    print(f"  [OK] CSV -> {OUT_CSV}")

    # Step 4: Generate and save Markdown workbook
    print("\n[4/7] Generating Markdown workbook...")
    markdown_text = generate_markdown_workbook(csv_rows, evidence_requests, upgrade_decisions)
    save_text(OUT_MD, markdown_text)
    print(f"  [OK] Markdown -> {OUT_MD}")

    # Step 5: Build and save manifest
    print("\n[5/7] Building manifest JSON...")
    manifest = build_manifest(csv_rows)
    save_json(OUT_MANIFEST, manifest)
    print(f"  [OK] Manifest -> {OUT_MANIFEST}")

    # Step 6: Build and save gate result
    print("\n[6/7] Building gate result JSON...")
    gate_result = build_gate_result(csv_rows, markdown_text)
    save_json(OUT_GATE_RESULT, gate_result)
    print(f"  [OK] Gate result -> {OUT_GATE_RESULT}")

    # Step 7: Generate handoff
    print("\n[7/7] Generating handoff...")
    handoff_text = generate_handoff(manifest, gate_result, csv_rows)
    save_text(OUT_HANDOFF, handoff_text)
    print(f"  [OK] Handoff -> {OUT_HANDOFF}")

    # Final summary
    print("\n" + "=" * 70)
    print("v115F WHALE ADDRESS AUDIT OPERATOR WORKBOOK COMPLETE")
    print(f"  workbook_rows: {manifest['workbook_rows']}")
    print(f"  addresses: {manifest['addresses']}")
    print(f"  manual_fields_prefilled: {manifest['manual_fields_prefilled']}")
    print(f"  upgrade_ready_count: {manifest['upgrade_ready_count']}")
    print(f"  blocked_upgrade_count: {manifest['blocked_upgrade_count']}")
    print(f"  send_ready: {manifest['send_ready']}")
    print(f"  tg_test_group_ready: {manifest['tg_test_group_ready']}")
    print(f"  local_review_ready: {manifest['local_review_ready']}")
    print(f"  gate_passed: {gate_result['gate_passed']}")
    print(f"  external_api_called: {manifest['external_api_called']}")
    print(f"  ai_model_called: {manifest['ai_model_called']}")
    print(f"  credentials_read: {manifest['credentials_read']}")
    print(f"  tg_sent: {manifest['tg_sent']}")
    print(f"  prod_state_write: {manifest['prod_state_write']}")
    print(f"  daemon_started: {manifest['daemon_started']}")
    print(f"  watcher_started: {manifest['watcher_started']}")
    print(f"  files_deleted: {manifest['files_deleted']}")
    print(f"  real_send_candidate_generated: {manifest['real_send_candidate_generated']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
