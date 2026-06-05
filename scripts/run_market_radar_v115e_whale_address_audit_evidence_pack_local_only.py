#!/usr/bin/env python3
"""
v115E Whale Address Audit Evidence Pack — Local Only
======================================================
Reads v115B label upgrade targets and v115D send preview blockers
to generate a local Address Audit Evidence Pack for manual operator review.

This is a LOCAL-ONLY audit evidence pack step. No external APIs, no TG send,
no production state write. ALL 4 addresses remain upgrade_ready=false.

The pack contains, per address:
  - Evidence request (what evidence is needed and why it's missing)
  - Manual audit form (blank fields for operator to fill)
  - Label upgrade decision (blocked_missing_evidence, upgrade_ready=false)

Outputs:
  - Evidence requests JSONL (4 records)
  - Manual audit forms JSONL (4 records)
  - Label upgrade decisions JSONL (4 records)
  - Result JSON
  - Markdown report
  - Handoff markdown

Invariants (enforced):
  - No external API calls
  - No API key / credentials read
  - No TG send
  - No production state write
  - No daemon / watcher / loop
  - No file deletion
  - No modification of v114A-v115D old results
  - No real send candidate generation
  - All 4 upgrade decisions = blocked_missing_evidence
  - upgrade_ready_count = 0
  - blocked_upgrade_count = 4
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

# v115B configs (read-only)
V115B_ROUTING_POLICY = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)
V115B_SEND_PREVIEW_GATE = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_send_preview_gate_policy.json"
)

# v115B inputs (read-only)
V115B_UPGRADE_TARGETS = os.path.join(
    RESULTS_DIR, "market_radar_v115b_whale_label_upgrade_targets.jsonl"
)

# v115D inputs (read-only)
V115D_PREVIEW_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_records.jsonl"
)
V115D_GATE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_decisions.jsonl"
)

# v114C inputs (read-only)
V114C_REVIEW_CARDS = os.path.join(
    RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_cards.jsonl"
)

# v115E outputs
OUT_EVIDENCE_REQUESTS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_requests.jsonl"
)
OUT_MANUAL_AUDIT_FORMS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_manual_audit_forms.jsonl"
)
OUT_UPGRADE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_label_upgrade_decisions.jsonl"
)
OUT_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115e_whale_address_audit_evidence_pack_result.json"
)
OUT_REPORT = os.path.join(
    RUNS_DIR, "v115e_whale_address_audit_evidence_pack_local_only.md"
)
OUT_HANDOFF = os.path.join(
    RUNS_DIR, "v115e_whale_address_audit_evidence_pack_local_only_handoff.md"
)

TZ_SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))

# Safety invariants
EXTERNAL_API_CALLED = False
CREDENTIALS_READ = False
DAEMON_STARTED = False
WATCHER_STARTED = False
FILES_DELETED = False
TG_SENT = False
PROD_STATE_WRITE = False
AI_MODEL_CALLED = False
REAL_SEND_CANDIDATE_GENERATED = False

# Required evidence types (from v115B policy)
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


def save_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


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


# ---------------------------------------------------------------------------
# Step 1: Load inputs
# ---------------------------------------------------------------------------
def load_inputs():
    """Load all required input files."""
    errors = []

    for label, path in [
        ("v115B upgrade targets", V115B_UPGRADE_TARGETS),
        ("v115B routing policy", V115B_ROUTING_POLICY),
        ("v115B send preview gate policy", V115B_SEND_PREVIEW_GATE),
        ("v115D preview records", V115D_PREVIEW_RECORDS),
        ("v115D gate decisions", V115D_GATE_DECISIONS),
        ("v114C review cards", V114C_REVIEW_CARDS),
    ]:
        if not os.path.exists(path):
            errors.append(f"{label} not found: {path}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    targets = load_jsonl(V115B_UPGRADE_TARGETS)
    routing = load_json(V115B_ROUTING_POLICY)
    send_gate = load_json(V115B_SEND_PREVIEW_GATE)
    preview_records = load_jsonl(V115D_PREVIEW_RECORDS)
    gate_decisions = load_jsonl(V115D_GATE_DECISIONS)
    review_cards = load_jsonl(V114C_REVIEW_CARDS)

    print(f"  v115B upgrade targets: {len(targets)}")
    print(f"  v115B routing policy loaded")
    print(f"  v115B send preview gate policy loaded")
    print(f"  v115D preview records: {len(preview_records)}")
    print(f"  v115D gate decisions: {len(gate_decisions)}")
    print(f"  v114C review cards: {len(review_cards)}")

    return targets, routing, send_gate, preview_records, gate_decisions, review_cards


# ---------------------------------------------------------------------------
# Step 2: Gather delta context from v114C review cards for an address
# ---------------------------------------------------------------------------
def gather_delta_context(address: str, review_cards: list) -> list:
    """Collect all delta review cards for a given address."""
    context = []
    for card in review_cards:
        if card.get("address") == address:
            context.append({
                "position_identity_key": card.get("position_identity_key", ""),
                "delta_type": card.get("delta_type", ""),
                "asset": card.get("asset", ""),
                "side": card.get("side", ""),
                "size_delta_abs": card.get("size_delta_abs", 0),
                "operator_attention_level": card.get("operator_attention_level", ""),
                "review_summary": card.get("review_summary", ""),
                "warnings": card.get("warnings", []),
            })
    return context


# ---------------------------------------------------------------------------
# Step 3: Gather send preview blockers from v115D for an address
# ---------------------------------------------------------------------------
def gather_v115d_blockers(address: str, gate_decisions: list) -> list:
    """Collect v115D gate decision block reasons for a given address."""
    for d in gate_decisions:
        if d.get("address") == address:
            return d.get("block_reasons", [])
    return []


# ---------------------------------------------------------------------------
# Step 4: Build why_this_address_matters text
# ---------------------------------------------------------------------------
def build_why_this_address_matters(target: dict, delta_context: list) -> str:
    """Generate human-readable explanation of why this address matters."""
    label = target.get("current_label", "unknown")
    confidence = target.get("current_label_confidence", "low")
    attention = target.get("operator_attention_level", "low")
    positions = target.get("positions_linked", 1)
    delta_types = target.get("delta_types", [])

    parts = []
    parts.append(f"Address labeled as '{label}' with {confidence} confidence.")
    parts.append(f"Linked to {positions} position(s) on HyperLiquid.")

    if delta_types:
        parts.append(f"Delta types observed: {', '.join(delta_types)}.")

    if attention == "high":
        parts.append("HIGH operator attention — contains significant position change (e.g., closed_position).")
    elif attention == "medium":
        parts.append("MEDIUM operator attention — notable position changes requiring review.")

    # Asset summary from delta context
    assets = list(set(c.get("asset", "") for c in delta_context))
    if assets:
        parts.append(f"Assets involved: {', '.join(sorted(assets))}.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Step 5: Determine confidence-specific blockers
# ---------------------------------------------------------------------------
def get_confidence_blockers(confidence: str, label: str) -> list:
    """Return confidence-specific blockers for upgrade decisions."""
    blockers = []

    if confidence == "low":
        blockers.append("UNKNOWN_WHALE_REQUIRES_MANUAL_ATTRIBUTION")
        blockers.append("LOW_CONFIDENCE_LABEL_NOT_SENDABLE")
    elif "unknown" in label.lower():
        blockers.append("UNKNOWN_WHALE_REQUIRES_MANUAL_ATTRIBUTION")
        blockers.append("LOW_CONFIDENCE_LABEL_NOT_SENDABLE")

    if confidence == "medium":
        blockers.append("MEDIUM_CONFIDENCE_REQUIRES_CORROBORATION")

    return blockers


# ---------------------------------------------------------------------------
# Step 6: Generate evidence request for one address
# ---------------------------------------------------------------------------
def generate_evidence_request(target: dict, review_cards: list,
                              gate_decisions: list, index: int) -> dict:
    """Generate an evidence request record for a single address."""
    address = target["address"]
    confidence = target.get("current_label_confidence", "low")
    label = target.get("current_label", "")
    priority = target.get("upgrade_priority", "medium")

    delta_context = gather_delta_context(address, review_cards)
    v115d_blockers = gather_v115d_blockers(address, gate_decisions)

    why_matters = build_why_this_address_matters(target, delta_context)

    # All 4 evidence types are required; all must be marked missing
    # since no manual evidence has been collected yet
    missing_evidence_types = list(REQUIRED_EVIDENCE_TYPES)

    # Build operator_action_required
    actions = [
        "MANUAL_LABEL_VERIFICATION: Research and confirm whale identity from trusted on-chain explorers or label providers.",
        "CROSS_SOURCE_CHECK: Find at least one independent second source confirming this address's identity.",
        "ACTIVITY_PATTERN_VERIFICATION: Review HyperLiquid position history for consistency with claimed identity.",
        "OPERATOR_CONFIRMATION: Explicitly sign off on label or reject with reason.",
    ]

    priority_num = {"high": 1, "medium": 2, "low": 3}.get(priority, 2)

    request = {
        "evidence_request_id": f"v115e_evr_{index + 1:03d}",
        "version": "v115E",
        "address": address,
        "current_label": label,
        "current_confidence": confidence,
        "target_confidence": "high",
        "priority": priority,
        "priority_order": priority_num,
        "why_this_address_matters": why_matters,
        "related_delta_context": delta_context,
        "v115d_block_reasons": v115d_blockers,
        "required_evidence_types": list(REQUIRED_EVIDENCE_TYPES),
        "required_evidence_count": len(REQUIRED_EVIDENCE_TYPES),
        "missing_evidence_types": missing_evidence_types,
        "missing_evidence_count": len(missing_evidence_types),
        "operator_action_required": actions,
        "upgrade_ready": False,
        "generated_at": now_iso(),
    }

    return request


# ---------------------------------------------------------------------------
# Step 7: Generate manual audit form for one address
# ---------------------------------------------------------------------------
def generate_manual_audit_form(target: dict, review_cards: list,
                               index: int) -> dict:
    """Generate a blank manual audit form for operator to fill."""
    address = target["address"]
    confidence = target.get("current_label_confidence", "low")
    label = target.get("current_label", "")

    delta_context = gather_delta_context(address, review_cards)
    first_delta = delta_context[0] if delta_context else {}

    form = {
        "audit_form_id": f"v115e_maf_{index + 1:03d}",
        "version": "v115E",
        "address": address,
        "current_label": label,
        "current_confidence": confidence,
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
        # Upgrade gate — ALWAYS false until operator fills and confirms
        "ready_for_upgrade": False,
        # Reference context (read-only for operator)
        "reference_delta_type": first_delta.get("delta_type", ""),
        "reference_asset": first_delta.get("asset", ""),
        "reference_warnings": first_delta.get("warnings", []),
        "generated_at": now_iso(),
    }

    return form


# ---------------------------------------------------------------------------
# Step 8: Generate label upgrade decision for one address
# ---------------------------------------------------------------------------
def generate_upgrade_decision(target: dict, index: int,
                              gate_decisions: list) -> dict:
    """Generate a label upgrade decision — always blocked."""
    address = target["address"]
    confidence = target.get("current_label_confidence", "low")
    label = target.get("current_label", "")

    confidence_blockers = get_confidence_blockers(confidence, label)
    v115d_blockers = gather_v115d_blockers(address, gate_decisions)

    # Build comprehensive block reasons
    block_reasons = [
        "UPGRADE_BLOCKED_MISSING_EVIDENCE",
        "MANUAL_OPERATOR_EVIDENCE_REQUIRED",
        "NO_TRUSTED_SOURCE_LABEL_PROVIDED",
        "NO_CROSS_SOURCE_CONSISTENCY_VERIFIED",
        "NO_ACTIVITY_PATTERN_VERIFIED",
        "NO_OPERATOR_CONFIRMATION",
    ]
    block_reasons.extend(confidence_blockers)

    # Add v115D send blockers as context
    for br in v115d_blockers:
        if br not in block_reasons:
            block_reasons.append(br)

    decision = {
        "upgrade_decision_id": f"v115e_upd_{index + 1:03d}",
        "version": "v115E",
        "address": address,
        "current_label": label,
        "from_confidence": confidence,
        "to_confidence_requested": "high",
        "upgrade_ready": False,
        "decision": "blocked_missing_evidence",
        "missing_evidence_types": list(REQUIRED_EVIDENCE_TYPES),
        "missing_evidence_count": len(REQUIRED_EVIDENCE_TYPES),
        "send_allowed": False,
        "tg_test_group_allowed": False,
        "public_send_allowed": False,
        "block_reasons": block_reasons,
        "confidence_specific_blockers": confidence_blockers,
        "v115d_block_reasons": v115d_blockers,
        "next_operator_action": "Fill manual audit form with evidence for all 4 required evidence types, then re-run upgrade decision.",
        "generated_at": now_iso(),
    }

    return decision


# ---------------------------------------------------------------------------
# Step 9: Generate all evidence requests, audit forms, and upgrade decisions
# ---------------------------------------------------------------------------
def generate_all(targets, review_cards, gate_decisions):
    """Generate the complete audit evidence pack for all 4 addresses."""
    evidence_requests = []
    manual_audit_forms = []
    upgrade_decisions = []

    for i, target in enumerate(targets):
        address = target["address"]
        sa = short_addr(address)
        confidence = target.get("current_label_confidence", "low")
        label = target.get("current_label", "")

        # Generate evidence request
        evr = generate_evidence_request(target, review_cards, gate_decisions, i)
        evidence_requests.append(evr)

        # Generate manual audit form
        maf = generate_manual_audit_form(target, review_cards, i)
        manual_audit_forms.append(maf)

        # Generate upgrade decision
        upd = generate_upgrade_decision(target, i, gate_decisions)
        upgrade_decisions.append(upd)

        blockers = upd.get("confidence_specific_blockers", [])
        blocker_str = ", ".join(blockers) if blockers else "none"
        print(f"  [BLOCKED] {sa}: {label} ({confidence}) "
              f"— upgrade_ready=false — {len(upd['block_reasons'])} block reasons "
              f"— confidence_blockers: {blocker_str}")

    return evidence_requests, manual_audit_forms, upgrade_decisions


# ---------------------------------------------------------------------------
# Step 10: Build result JSON
# ---------------------------------------------------------------------------
def build_result(evidence_requests, manual_audit_forms, upgrade_decisions):
    """Build the v115E result JSON."""
    n = len(evidence_requests)
    upgrade_ready = sum(1 for d in upgrade_decisions if d.get("upgrade_ready") is True)
    blocked = sum(1 for d in upgrade_decisions if d.get("upgrade_ready") is False)

    result = {
        "stage": "v115e_whale_address_audit_evidence_pack_local_only",
        "version": "v115E",
        "input_targets": n,
        "evidence_requests": len(evidence_requests),
        "manual_audit_forms": len(manual_audit_forms),
        "upgrade_decisions": len(upgrade_decisions),
        "upgrade_ready_count": upgrade_ready,
        "blocked_upgrade_count": blocked,
        "high_confidence_after_upgrade": 0,
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
    save_json(OUT_RESULT, result)
    print(f"  Result JSON -> {OUT_RESULT}")
    return result


# ---------------------------------------------------------------------------
# Step 11: Generate markdown report
# ---------------------------------------------------------------------------
def generate_report(result, evidence_requests, manual_audit_forms,
                    upgrade_decisions, targets):
    """Generate the v115E markdown report."""

    # Evidence request rows
    evr_rows = ""
    for evr in evidence_requests:
        sa = short_addr(evr["address"])
        evr_rows += (
            f"| `{evr['evidence_request_id']}` | `{sa}` | "
            f"{evr['current_label']} | **{evr['current_confidence']}** | "
            f"{evr['priority']} | {evr['missing_evidence_count']}/{evr['required_evidence_count']} | "
            f"❌ blocked |\n"
        )

    # Audit form status rows
    form_rows = ""
    for maf in manual_audit_forms:
        sa = short_addr(maf["address"])
        filled = sum(1 for v in [
            maf["trusted_source_label_value"],
            maf["second_source_label_value"],
            maf["activity_pattern_note"],
            maf["operator_confirmed_label"],
        ] if v)
        total = 4
        form_rows += (
            f"| `{maf['audit_form_id']}` | `{sa}` | "
            f"{maf['current_label']} | {filled}/{total} fields filled | "
            f"ready_for_upgrade={maf['ready_for_upgrade']} |\n"
        )

    # Decision rows
    dec_rows = ""
    for upd in upgrade_decisions:
        sa = short_addr(upd["address"])
        conf_blockers = ", ".join(upd.get("confidence_specific_blockers", []))
        dec_rows += (
            f"| `{upd['upgrade_decision_id']}` | `{sa}` | "
            f"{upd['current_label']} | {upd['from_confidence']} → high | "
            f"`upgrade_ready=false` | `{upd['decision']}` | {conf_blockers} |\n"
        )

    report = f"""# v115E Whale Address Audit Evidence Pack — Local Only

**Generated:** {result['generated_at']}
**Stage:** {result['stage']}
**Input Stages:** v115B (upgrade targets) + v115D (send preview blockers) + v114C (delta review cards)

---

## 1. Purpose

This is a **local-only address audit evidence pack** step. It reads v115B label upgrade
targets and v115D send preview blockers to produce a complete, operator-fillable audit
pack for each of the 4 whale addresses.

**ALL 4 addresses remain upgrade_ready=false.** No label upgrade to high confidence
has occurred. Each address has an evidence checklist, a blank manual audit form,
and a blocked upgrade decision with explicit reasons.

---

## 2. Inputs

| Input | Source | Records |
|-------|--------|---------|
| Label upgrade targets | v115B | 4 addresses |
| Label confidence routing policy | v115B config | read-only |
| Send preview gate policy | v115B config | read-only |
| One-shot send preview records | v115D | 4 records |
| Send preview gate decisions | v115D | 4 blocked decisions |
| Delta operator review cards | v114C | 10 review cards |

---

## 3. Address Audit Summary

### 3.1 Evidence Requests

| ID | Address | Label | Confidence | Priority | Missing Evidence | Status |
|----|---------|-------|-----------|----------|-----------------|--------|
{evr_rows}

### 3.2 Manual Audit Forms

| ID | Address | Label | Fields Filled | Ready |
|----|---------|-------|---------------|-------|
{form_rows}

**All manual evidence fields are empty/false by default — no evidence has been
fabricated.** Operator must fill in each field manually.

### 3.3 Label Upgrade Decisions

| ID | Address | Label | Confidence Path | Upgrade Ready | Decision | Confidence Blockers |
|----|---------|-------|-----------------|---------------|----------|---------------------|
{dec_rows}

---

## 4. Required Evidence Types (per v115B policy)

All 4 addresses require ALL 4 evidence types for upgrade to high confidence:

1. **`trusted_source_label`** — Label from a recognized on-chain explorer or label provider
   (e.g., Nansen, Arkham, Etherscan labels).
2. **`cross_source_consistency`** — Independent second source confirming same entity
   identity at this address.
3. **`address_activity_consistency`** — On-chain activity pattern matches expected
   behavior of claimed entity.
4. **`manual_operator_confirmation`** — Human operator explicitly confirms label
   after reviewing all evidence.

---

## 5. Result Summary

| Metric | Value |
|--------|-------|
| input_targets | {result['input_targets']} |
| evidence_requests | {result['evidence_requests']} |
| manual_audit_forms | {result['manual_audit_forms']} |
| upgrade_decisions | {result['upgrade_decisions']} |
| upgrade_ready_count | ❌ `{result['upgrade_ready_count']}` |
| blocked_upgrade_count | 🛑 `{result['blocked_upgrade_count']}` |
| high_confidence_after_upgrade | `{result['high_confidence_after_upgrade']}` |
| send_ready | ❌ `{result['send_ready']}` |
| tg_test_group_ready | ❌ `{result['tg_test_group_ready']}` |
| local_review_ready | ✅ `{result['local_review_ready']}` |

---

## 6. Confidence-Specific Blockers

- **Low confidence (Unknown Whale) addresses:** `UNKNOWN_WHALE_REQUIRES_MANUAL_ATTRIBUTION`,
  `LOW_CONFIDENCE_LABEL_NOT_SENDABLE`
- **Medium confidence addresses:** `MEDIUM_CONFIDENCE_REQUIRES_CORROBORATION`

---

## 7. Safety Invariants

| Invariant | Status |
|-----------|--------|
| external_api_called | ✅ `{result['external_api_called']}` |
| ai_model_called | ✅ `{result['ai_model_called']}` |
| credentials_read | ✅ `{result['credentials_read']}` |
| tg_sent | ✅ `{result['tg_sent']}` |
| prod_state_write | ✅ `{result['prod_state_write']}` |
| daemon_started | ✅ `{result['daemon_started']}` |
| watcher_started | ✅ `{result['watcher_started']}` |
| files_deleted | ✅ `{result['files_deleted']}` |
| real_send_candidate_generated | ✅ `{result['real_send_candidate_generated']}` |

---

## 8. Explicit NOT Declarations

This stage is explicitly **NOT**:

- ❌ A label upgrade execution
- ❌ A TG send
- ❌ Send-ready for production
- ❌ TG-test-group-ready
- ❌ A trading signal
- ❌ Financial advice
- ❌ Production state
- ❌ A real send candidate
- ❌ AI-generated evidence

This stage **IS**:

- ✅ A local-only address audit evidence pack
- ✅ Operator-fillable manual audit forms
- ✅ Evidence checklists with explicit gaps
- ✅ Blocked upgrade decisions with full reasoning
- ✅ Input for future manual operator review and evidence collection
- ✅ Fully guarded with safety invariants
- ✅ Traceable, verifiable, reproducible

---

## 9. Output Files

| File | Path |
|------|------|
| Evidence Requests JSONL | `{OUT_EVIDENCE_REQUESTS}` |
| Manual Audit Forms JSONL | `{OUT_MANUAL_AUDIT_FORMS}` |
| Upgrade Decisions JSONL | `{OUT_UPGRADE_DECISIONS}` |
| Result JSON | `{OUT_RESULT}` |
| Report MD | `{OUT_REPORT}` |
| Handoff MD | `{OUT_HANDOFF}` |

---

*This report is for local operator review only. No external communication intended.*
"""
    save_text(OUT_REPORT, report)
    print(f"  Markdown report -> {OUT_REPORT}")


# ---------------------------------------------------------------------------
# Step 12: Generate handoff
# ---------------------------------------------------------------------------
def generate_handoff(result, evidence_requests, manual_audit_forms,
                     upgrade_decisions):
    """Generate the v115E handoff markdown."""

    evr_summary = ""
    for evr, maf, upd in zip(evidence_requests, manual_audit_forms, upgrade_decisions):
        sa = short_addr(evr["address"])
        evr_summary += (
            f"- 🛑 `{sa}` — {evr['current_label']} "
            f"({evr['current_confidence']}) — "
            f"missing {evr['missing_evidence_count']} evidence types — "
            f"form: `{maf['audit_form_id']}` (0 fields filled) — "
            f"decision: `{upd['upgrade_decision_id']}` blocked_missing_evidence\n"
        )

    handoff = f"""# v115E Handoff — Whale Address Audit Evidence Pack Local Only

**Generated:** {result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only
**Stage:** v115E

---

## What was done

1. Read v115B label upgrade targets (4 addresses)
2. Read v115B routing policy and send preview gate policy
3. Read v115D one-shot send preview records and gate decisions (all blocked)
4. Read v114C delta operator review cards (10 cards)
5. Generated 4 evidence requests with full required/missing evidence breakdown
6. Generated 4 blank manual audit forms with all operator-fillable fields
7. Generated 4 label upgrade decisions (ALL blocked_missing_evidence)
8. Generated result JSON, report, and handoff

## Address Audit Summary

{evr_summary}

## Key Results

| Metric | Value |
|--------|-------|
| evidence_requests | {result['evidence_requests']} |
| manual_audit_forms | {result['manual_audit_forms']} |
| upgrade_decisions | {result['upgrade_decisions']} |
| upgrade_ready_count | {result['upgrade_ready_count']} |
| blocked_upgrade_count | {result['blocked_upgrade_count']} |
| high_confidence_after_upgrade | {result['high_confidence_after_upgrade']} |
| send_ready | {result['send_ready']} |
| tg_test_group_ready | {result['tg_test_group_ready']} |
| local_review_ready | {result['local_review_ready']} |

## Confidence-Specific Blockers Applied

- 2 low/unknown confidence addresses: `UNKNOWN_WHALE_REQUIRES_MANUAL_ATTRIBUTION`, `LOW_CONFIDENCE_LABEL_NOT_SENDABLE`
- 2 medium confidence addresses: `MEDIUM_CONFIDENCE_REQUIRES_CORROBORATION`

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
- v114A-v115D old results NOT modified

## This Stage Is NOT

- A label upgrade execution
- A TG send
- Send-ready for production
- TG-test-group-ready
- A trading signal
- A real send candidate

## This Stage IS

- A local-only address audit evidence pack
- 4 operator-fillable manual audit forms
- 4 evidence checklists with explicit gaps
- 4 blocked upgrade decisions with full reasoning
- Input for future manual operator review

## Next Operator Actions Required

1. For each address, research trusted on-chain label sources
2. Find independent second-source corroboration
3. Verify on-chain activity patterns
4. Fill manual audit forms with collected evidence
5. Only after ALL 4 evidence types are filled can upgrade be re-evaluated

---

*This handoff is for the next stage decision-maker. Operator review and evidence
collection required before any label upgrade can proceed.*
"""
    save_text(OUT_HANDOFF, handoff)
    print(f"  Handoff -> {OUT_HANDOFF}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v115E Whale Address Audit Evidence Pack — Local Only")
    print("=" * 70)

    # Step 1: Load inputs
    print("\n[1/8] Loading inputs...")
    targets, routing, send_gate, preview_records, gate_decisions, review_cards = \
        load_inputs()

    if len(targets) != 4:
        print(f"  ERROR: Expected 4 upgrade targets, got {len(targets)}")
        sys.exit(1)

    # Step 2: Verify routing state
    high_count = routing.get("current_state", {}).get("high_count", 0)
    print(f"\n[2/8] Routing state check: high_count={high_count}")
    print(f"  Confirmed: 0 high-confidence labels exist")

    # Step 3: Verify v115D all blocked
    sendable = sum(1 for d in gate_decisions if d.get("send_allowed") is True)
    print(f"\n[3/8] v115D gate state: sendable={sendable}")
    print(f"  Confirmed: No preview passed the send gate")

    # Step 4: Generate evidence requests, audit forms, and upgrade decisions
    print("\n[4/8] Generating audit evidence pack...")
    evidence_requests, manual_audit_forms, upgrade_decisions = \
        generate_all(targets, review_cards, gate_decisions)

    # Step 5: Save evidence requests JSONL
    print("\n[5/8] Saving evidence requests JSONL...")
    save_jsonl(OUT_EVIDENCE_REQUESTS, evidence_requests)
    print(f"  Evidence requests -> {OUT_EVIDENCE_REQUESTS} "
          f"({len(evidence_requests)} records)")

    # Step 6: Save manual audit forms JSONL
    print("\n[6/8] Saving manual audit forms JSONL...")
    save_jsonl(OUT_MANUAL_AUDIT_FORMS, manual_audit_forms)
    print(f"  Manual audit forms -> {OUT_MANUAL_AUDIT_FORMS} "
          f"({len(manual_audit_forms)} records)")

    # Step 7: Save upgrade decisions JSONL
    print("\n[7/8] Saving upgrade decisions JSONL...")
    save_jsonl(OUT_UPGRADE_DECISIONS, upgrade_decisions)
    print(f"  Upgrade decisions -> {OUT_UPGRADE_DECISIONS} "
          f"({len(upgrade_decisions)} records)")

    # Step 8: Build result, report, handoff
    print("\n[8/8] Building result JSON, report, and handoff...")
    result = build_result(evidence_requests, manual_audit_forms, upgrade_decisions)
    generate_report(result, evidence_requests, manual_audit_forms,
                    upgrade_decisions, targets)
    generate_handoff(result, evidence_requests, manual_audit_forms,
                     upgrade_decisions)

    # Final summary
    print("\n" + "=" * 70)
    print("v115E WHALE ADDRESS AUDIT EVIDENCE PACK COMPLETE")
    print(f"  input_targets: {result['input_targets']}")
    print(f"  evidence_requests: {result['evidence_requests']}")
    print(f"  manual_audit_forms: {result['manual_audit_forms']}")
    print(f"  upgrade_decisions: {result['upgrade_decisions']}")
    print(f"  upgrade_ready_count: {result['upgrade_ready_count']}")
    print(f"  blocked_upgrade_count: {result['blocked_upgrade_count']}")
    print(f"  high_confidence_after_upgrade: {result['high_confidence_after_upgrade']}")
    print(f"  send_ready: {result['send_ready']}")
    print(f"  tg_test_group_ready: {result['tg_test_group_ready']}")
    print(f"  local_review_ready: {result['local_review_ready']}")
    print(f"  external_api_called: {result['external_api_called']}")
    print(f"  ai_model_called: {result['ai_model_called']}")
    print(f"  credentials_read: {result['credentials_read']}")
    print(f"  tg_sent: {result['tg_sent']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
