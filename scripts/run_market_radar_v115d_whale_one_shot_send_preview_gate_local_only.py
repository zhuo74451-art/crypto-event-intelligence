#!/usr/bin/env python3
"""
v115D Whale One-Shot Send Preview Gate — Local Only
=====================================================
Reads v115C TG test copy templates and v115B send preview gate policy
to generate one-shot send preview records and gate decisions.

This is a LOCAL-ONLY preview gate step. No external APIs, no TG send,
no production state write. ALL previews are blocked — no real send
candidate generated.

Key: high confidence labels = 0, so ALL previews must be blocked.

Outputs:
  - One-shot send preview records JSONL (4 records)
  - Gate decisions JSONL (4 blocked decisions)
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
  - No modification of v114A-v115C old results
  - No real send candidate generation
  - All previews blocked, sendable_previews = 0
"""

import json
import os
import sys
import datetime
import hashlib

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
V115B_COOLDOWN_POLICY = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_rollback_cooldown_policy.json"
)

# v115C inputs (read-only)
V115C_TEMPLATES = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_templates.jsonl"
)

# v115D outputs
OUT_PREVIEW_RECORDS = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_records.jsonl"
)
OUT_GATE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_decisions.jsonl"
)
OUT_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115d_whale_one_shot_send_preview_gate_result.json"
)
OUT_REPORT = os.path.join(
    RUNS_DIR, "v115d_whale_one_shot_send_preview_gate_local_only.md"
)
OUT_HANDOFF = os.path.join(
    RUNS_DIR, "v115d_whale_one_shot_send_preview_gate_local_only_handoff.md"
)

TZ_SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))
TODAY_DATE = datetime.datetime.now(TZ_SHANGHAI).strftime("%Y%m%d")

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


def compute_payload_hash(copy_text: str, address: str, asset: str,
                         delta_type: str, scope: str) -> str:
    """Compute SHA-256 hash of copy_text + address + asset + delta_type + scope."""
    payload_input = copy_text + address + asset + delta_type + scope
    return hashlib.sha256(payload_input.encode("utf-8")).hexdigest()


def compute_no_repeat_key(address: str, asset: str, side: str,
                          delta_type: str, date_str: str) -> str:
    """Build no-repeat key: {address}_{asset}_{side}_{delta_type}_{date}"""
    return f"{address}_{asset}_{side}_{delta_type}_{date_str}"


def compute_cooldown_key(address: str, asset: str, date_str: str) -> str:
    """Build cooldown key: {address}_{asset}_{date}"""
    return f"{address}_{asset}_{date_str}"


# ---------------------------------------------------------------------------
# Step 1: Load inputs
# ---------------------------------------------------------------------------
def load_inputs():
    """Load all required input files."""
    errors = []

    for label, path in [
        ("v115C templates", V115C_TEMPLATES),
        ("v115B routing policy", V115B_ROUTING_POLICY),
        ("v115B send preview gate policy", V115B_SEND_PREVIEW_GATE),
        ("v115B cooldown policy", V115B_COOLDOWN_POLICY),
    ]:
        if not os.path.exists(path):
            errors.append(f"{label} not found: {path}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    templates = load_jsonl(V115C_TEMPLATES)
    routing = load_json(V115B_ROUTING_POLICY)
    send_gate = load_json(V115B_SEND_PREVIEW_GATE)
    cooldown = load_json(V115B_COOLDOWN_POLICY)

    print(f"  v115C templates: {len(templates)}")
    print(f"  v115B routing policy loaded")
    print(f"  v115B send preview gate policy loaded")
    print(f"  v115B cooldown policy loaded")

    return templates, routing, send_gate, cooldown


# ---------------------------------------------------------------------------
# Step 2: Generate one-shot send preview record for one template
# ---------------------------------------------------------------------------
def generate_preview_record(template, record_index):
    """Generate a one-shot send preview record from a v115C template."""
    address = template["address"]
    asset = template["asset"]
    side = template.get("side", "?")
    delta_type = template["delta_type"]
    label = template["label"]
    label_confidence = template["label_confidence"]
    copy_text = template.get("copy_text", "")

    scope = "tg_test_group_only"

    # Compute keys
    payload_hash = compute_payload_hash(copy_text, address, asset, delta_type, scope)
    no_repeat_key = compute_no_repeat_key(address, asset, side, delta_type, TODAY_DATE)
    cooldown_key = compute_cooldown_key(address, asset, TODAY_DATE)

    # All previews must be blocked
    block_reasons = [
        "LABEL_CONFIDENCE_BELOW_HIGH",
        "OPERATOR_APPROVAL_MISSING",
        "TG_SEND_DISABLED_BY_DEFAULT",
        "NOT_SEND_READY",
    ]

    # Low confidence / unknown whale gets extra blockers
    if label_confidence == "low" or "unknown" in label.lower():
        block_reasons.append("UNKNOWN_WHALE_NOT_SENDABLE")
        block_reasons.append("LABEL_UPGRADE_REQUIRED")

    preview_record = {
        "preview_id": f"v115d_pvw_{record_index + 1:03d}",
        "template_id": template["template_id"],
        "address": address,
        "asset": asset,
        "side": side,
        "delta_type": delta_type,
        "label": label,
        "label_confidence": label_confidence,
        "copy_text": copy_text,
        "payload_hash": payload_hash,
        "no_repeat_key": no_repeat_key,
        "cooldown_key": cooldown_key,
        "scope": scope,
        "operator_approval": False,
        "user_preauthorization_scope": scope,
        "send_allowed": False,
        "blocked": True,
        "block_reasons": block_reasons,
        "generated_at": now_iso(),
    }

    return preview_record


# ---------------------------------------------------------------------------
# Step 3: Generate gate decision for one preview record
# ---------------------------------------------------------------------------
def generate_gate_decision(preview_record, routing, send_gate, cooldown):
    """Generate a gate decision for a preview record.

    ALL decisions must be blocked. No send is allowed.
    """
    label_confidence = preview_record["label_confidence"]
    label = preview_record["label"]
    address = preview_record["address"]

    block_reasons = [
        "LABEL_CONFIDENCE_BELOW_HIGH",
        "OPERATOR_APPROVAL_MISSING",
        "TG_SEND_DISABLED_BY_DEFAULT",
        "NOT_SEND_READY",
    ]

    # Low confidence / unknown whale extra blockers
    if label_confidence == "low" or "unknown" in label.lower():
        block_reasons.append("UNKNOWN_WHALE_NOT_SENDABLE")
        block_reasons.append("LABEL_UPGRADE_REQUIRED")

    # Additional policy-derived reasons
    # Check routing policy — no high confidence labels exist
    high_count = routing.get("current_state", {}).get("high_count", 0)
    if high_count == 0:
        block_reasons.append("NO_HIGH_CONFIDENCE_LABELS_EXIST")

    gate_decision = {
        "preview_id": preview_record["preview_id"],
        "template_id": preview_record["template_id"],
        "address": address,
        "label": label,
        "label_confidence": label_confidence,
        "asset": preview_record["asset"],
        "delta_type": preview_record["delta_type"],
        "payload_hash": preview_record["payload_hash"],
        "no_repeat_key": preview_record["no_repeat_key"],
        "cooldown_key": preview_record["cooldown_key"],
        "scope": preview_record["scope"],
        "operator_approval": False,
        "send_allowed": False,
        "blocked": True,
        "block_reasons": block_reasons,
        "send_ready": False,
        "tg_test_group_ready": False,
        "local_review_ready": True,
        "tg_sent": False,
        "prod_state_write": False,
        "real_send_candidate_generated": False,
        "gate_passed": False,
        "generated_at": now_iso(),
    }

    return gate_decision


# ---------------------------------------------------------------------------
# Step 4: Generate all preview records and gate decisions
# ---------------------------------------------------------------------------
def generate_all(templates, routing, send_gate, cooldown):
    """Generate preview records and gate decisions for all templates."""
    preview_records = []
    gate_decisions = []

    for i, template in enumerate(templates):
        # Generate preview record
        preview = generate_preview_record(template, i)
        preview_records.append(preview)

        # Generate gate decision
        decision = generate_gate_decision(preview, routing, send_gate, cooldown)
        gate_decisions.append(decision)

        conf = preview["label_confidence"]
        reasons_count = len(decision["block_reasons"])
        print(f"  [BLOCKED] {preview['preview_id']}: "
              f"{preview['label']} ({conf}) "
              f"— {reasons_count} block reasons")

    return preview_records, gate_decisions


# ---------------------------------------------------------------------------
# Step 5: Build result JSON
# ---------------------------------------------------------------------------
def build_result(preview_records, gate_decisions):
    """Build the v115D result JSON."""
    sendable = sum(1 for p in preview_records if p.get("send_allowed") is True)
    blocked = sum(1 for p in preview_records if p.get("blocked") is True)
    payload_hashes = [p["payload_hash"] for p in preview_records]
    unique_hashes = len(set(payload_hashes))

    result = {
        "stage": "v115d_whale_one_shot_send_preview_gate_local_only",
        "version": "v115D",
        "input_templates": len(preview_records),
        "preview_records": len(preview_records),
        "gate_decisions": len(gate_decisions),
        "sendable_previews": sendable,
        "blocked_previews": blocked,
        "unique_payload_hashes": unique_hashes,
        "duplicate_payload_hashes": len(payload_hashes) - unique_hashes,
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
# Step 6: Generate markdown report
# ---------------------------------------------------------------------------
def generate_report(result, preview_records, gate_decisions, templates):
    """Generate the v115D markdown report."""

    preview_rows = ""
    for p, d in zip(preview_records, gate_decisions):
        reasons = ", ".join(d["block_reasons"][:3])
        if len(d["block_reasons"]) > 3:
            reasons += f", ... ({len(d['block_reasons'])} total)"
        preview_rows += (
            f"| `{p['preview_id']}` | `{p['address'][:14]}...` | "
            f"{p['label']} | **{p['label_confidence']}** | "
            f"{p['delta_type']} | ❌ BLOCKED | {reasons} |\n"
        )

    hash_rows = ""
    for p in preview_records:
        hash_rows += (
            f"| `{p['preview_id']}` | "
            f"`{p['payload_hash'][:16]}...` | "
            f"`{p['no_repeat_key'][:60]}...` | "
            f"`{p['cooldown_key'][:50]}...` |\n"
        )

    report = f"""# v115D Whale One-Shot Send Preview Gate — Local Only

**Generated:** {result['generated_at']}
**Stage:** {result['stage']}
**Input Stage:** v115C (TG test copy templates) + v115B (send preview gate policy)

---

## 1. Purpose

This is a **local-only one-shot send preview gate** step. It reads v115C TG test
copy templates and generates one-shot send preview records with full payload hash,
no-repeat key, cooldown key, and gate decisions.

**ALL previews are BLOCKED** because high confidence labels = 0. No real send
candidate is generated. No TG send occurs.

---

## 2. Inputs

| Input | Source |
|-------|--------|
| TG test copy templates | v115C (4 templates) |
| Send preview gate policy | v115B |
| Label confidence routing policy | v115B |
| Rollback/cooldown policy | v115B |

---

## 3. Preview Records Summary

| Preview ID | Address | Label | Confidence | Delta | Gate | Block Reasons |
|------------|---------|-------|-----------|-------|------|---------------|
{preview_rows}

---

## 4. Payload Hash & Keys

| Preview ID | Payload Hash | No-Repeat Key | Cooldown Key |
|------------|-------------|---------------|--------------|
{hash_rows}

**All payload hashes are SHA-256 of:** `copy_text + address + asset + delta_type + scope`

**No-repeat key format:** `{{address}}_{{asset}}_{{side}}_{{delta_type}}_{{date}}`

**Cooldown key format:** `{{address}}_{{asset}}_{{date}}`

---

## 5. Gate Decision Block Reasons (per preview)

All 4 previews are blocked with at least:
- `LABEL_CONFIDENCE_BELOW_HIGH`
- `OPERATOR_APPROVAL_MISSING`
- `TG_SEND_DISABLED_BY_DEFAULT`
- `NOT_SEND_READY`

Low confidence / unknown whale previews additionally include:
- `UNKNOWN_WHALE_NOT_SENDABLE`
- `LABEL_UPGRADE_REQUIRED`

---

## 6. Result Summary

| Metric | Value |
|--------|-------|
| Input templates | {result['input_templates']} |
| Preview records | {result['preview_records']} |
| Gate decisions | {result['gate_decisions']} |
| sendable_previews | ❌ `{result['sendable_previews']}` |
| blocked_previews | 🛑 `{result['blocked_previews']}` |
| unique_payload_hashes | `{result['unique_payload_hashes']}` |
| duplicate_payload_hashes | `{result['duplicate_payload_hashes']}` |
| send_ready | ❌ `{result['send_ready']}` |
| tg_test_group_ready | ❌ `{result['tg_test_group_ready']}` |
| local_review_ready | ✅ `{result['local_review_ready']}` |

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

- ❌ A TG send
- ❌ Send-ready for production
- ❌ TG-test-group-ready
- ❌ A trading signal
- ❌ Financial advice
- ❌ Production state
- ❌ A real send candidate

This stage **IS**:

- ✅ One-shot send preview gate generation (local only)
- ✅ Full payload hash, no-repeat key, cooldown key computation
- ✅ Gate decision with explicit block reasons
- ✅ Fully guarded with safety invariants
- ✅ Traceable, verifiable, reproducible

---

## 9. Output Files

| File | Path |
|------|------|
| Preview Records JSONL | `{OUT_PREVIEW_RECORDS}` |
| Gate Decisions JSONL | `{OUT_GATE_DECISIONS}` |
| Result JSON | `{OUT_RESULT}` |
| Report MD | `{OUT_REPORT}` |
| Handoff MD | `{OUT_HANDOFF}` |

---

*This report is for local operator review only. No external communication intended.*
"""
    save_text(OUT_REPORT, report)
    print(f"  Markdown report -> {OUT_REPORT}")


# ---------------------------------------------------------------------------
# Step 7: Generate handoff
# ---------------------------------------------------------------------------
def generate_handoff(result, preview_records, gate_decisions):
    """Generate the v115D handoff markdown."""

    pvw_summary = ""
    for p in preview_records:
        reasons_count = len(p["block_reasons"])
        pvw_summary += (
            f"- 🛑 `{p['preview_id']}` — "
            f"{p['label']} ({p['label_confidence']}, {p['delta_type']}) "
            f"— {reasons_count} block reasons\n"
        )

    handoff = f"""# v115D Handoff — Whale One-Shot Send Preview Gate Local Only

**Generated:** {result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only
**Stage:** v115D

---

## What was done

1. Read v115C TG test copy templates (4 templates)
2. Read v115B send preview gate policy
3. Read v115B routing policy
4. Read v115B rollback/cooldown policy
5. Generated 4 one-shot send preview records with full metadata
6. Generated 4 gate decisions (ALL BLOCKED)
7. Computed SHA-256 payload hashes, no-repeat keys, cooldown keys
8. Generated result JSON, preview records JSONL, gate decisions JSONL, report, handoff

## Preview Summary

{pvw_summary}

## Gate Results

| Metric | Value |
|--------|-------|
| Preview records | {result['preview_records']} |
| Gate decisions | {result['gate_decisions']} |
| sendable_previews | {result['sendable_previews']} |
| blocked_previews | {result['blocked_previews']} |
| unique_payload_hashes | {result['unique_payload_hashes']} |
| duplicate_payload_hashes | {result['duplicate_payload_hashes']} |

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
- v114A-v115C old results NOT modified

## Send Readiness

- `send_ready=false`
- `tg_test_group_ready=false`
- `local_review_ready=true`
- `sendable_previews=0`

## This Stage Is NOT

- A TG send
- Send-ready for production
- TG-test-group-ready
- A trading signal
- A real send candidate

## This Stage IS

- One-shot send preview gate generation (local only)
- Full metadata for future send review if labels reach high confidence
- Input for future stages when high confidence labels exist

---

*This handoff is for the next stage decision-maker. No action required now.*
"""
    save_text(OUT_HANDOFF, handoff)
    print(f"  Handoff -> {OUT_HANDOFF}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v115D Whale One-Shot Send Preview Gate — Local Only")
    print("=" * 70)

    # Step 1: Load inputs
    print("\n[1/6] Loading inputs...")
    templates, routing, send_gate, cooldown = load_inputs()

    # Step 2: Verify high confidence labels = 0
    high_count = routing.get("current_state", {}).get("high_count", 0)
    print(f"\n[2/6] Routing state check: high_count={high_count}")
    if high_count > 0:
        print(f"  WARNING: high_count={high_count} — but gate policy still blocks all sends")

    # Step 3: Generate preview records and gate decisions
    print("\n[3/6] Generating preview records and gate decisions...")
    preview_records, gate_decisions = generate_all(templates, routing, send_gate, cooldown)

    # Step 4: Save preview records JSONL
    print("\n[4/6] Saving preview records JSONL...")
    save_jsonl(OUT_PREVIEW_RECORDS, preview_records)
    print(f"  Preview records -> {OUT_PREVIEW_RECORDS} ({len(preview_records)} records)")

    # Step 5: Save gate decisions JSONL
    print("\n[5/6] Saving gate decisions JSONL...")
    save_jsonl(OUT_GATE_DECISIONS, gate_decisions)
    print(f"  Gate decisions -> {OUT_GATE_DECISIONS} ({len(gate_decisions)} decisions)")

    # Step 6: Build result, report, handoff
    print("\n[6/6] Building result JSON, report, and handoff...")
    result = build_result(preview_records, gate_decisions)
    generate_report(result, preview_records, gate_decisions, templates)
    generate_handoff(result, preview_records, gate_decisions)

    # Final summary
    print("\n" + "=" * 70)
    print("v115D ONE-SHOT SEND PREVIEW GATE COMPLETE")
    print(f"  Preview records: {result['preview_records']}")
    print(f"  Gate decisions: {result['gate_decisions']}")
    print(f"  sendable_previews: {result['sendable_previews']}")
    print(f"  blocked_previews: {result['blocked_previews']}")
    print(f"  unique_payload_hashes: {result['unique_payload_hashes']}")
    print(f"  duplicate_payload_hashes: {result['duplicate_payload_hashes']}")
    print(f"  send_ready: {result['send_ready']}")
    print(f"  tg_test_group_ready: {result['tg_test_group_ready']}")
    print(f"  local_review_ready: {result['local_review_ready']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
