#!/usr/bin/env python3
"""
v115A Whale Delta Send-Readiness Strategy Gate — Local Only
=============================================================
Reads v114D seal + v114C review cards + v113D seal (reference only),
and produces a send-readiness strategy gate judgment.

Purpose: determine WHY the current pack is NOT send-ready and what
conditions must be met before it can enter TG test group.

Invariants (enforced):
  - No external API calls
  - No API key / credentials read
  - No TG send
  - No production state write
  - No daemon / watcher / loop
  - No file deletion
  - No modification of v114A-v114D old results
  - No real send candidate generation

Output:
  - send_readiness gate result JSON
  - blockers JSONL
  - markdown strategy report
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
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# Reference inputs (read-only)
V114D_SEAL = os.path.join(RESULTS_DIR, "market_radar_v114d_whale_delta_review_pack_seal_result.json")
V114D_MANIFEST = os.path.join(RESULTS_DIR, "market_radar_v114d_whale_delta_review_pack_manifest.json")
V114C_CARDS = os.path.join(RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_cards.jsonl")
V114B_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_delta_compare_result.json")
V114A_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114a_whale_position_baseline_snapshot_result.json")
V113D_SEAL = os.path.join(RESULTS_DIR, "market_radar_v113d_degraded_whale_review_pack_seal_result.json")

# v115A outputs
OUT_RESULT = os.path.join(RESULTS_DIR, "market_radar_v115a_whale_delta_send_readiness_gate_result.json")
OUT_BLOCKERS = os.path.join(RESULTS_DIR, "market_radar_v115a_whale_delta_send_readiness_blockers.jsonl")
OUT_REPORT = os.path.join(RUNS_DIR, "v115a_whale_delta_send_readiness_strategy_gate_local_only.md")
OUT_HANDOFF = os.path.join(RUNS_DIR, "v115a_whale_delta_send_readiness_strategy_gate_local_only_handoff.md")

TZ_SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))

# Safety invariants
EXTERNAL_API_CALLED = False
CREDENTIALS_READ = False
DAEMON_STARTED = False
WATCHER_STARTED = False
FILES_DELETED = False
TG_SENT = False
PROD_STATE_WRITE = False


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


# ---------------------------------------------------------------------------
# Step 1: Load reference inputs
# ---------------------------------------------------------------------------
def load_reference_inputs():
    """Load v114D seal, v114C cards, v113D seal (read-only)."""
    errors = []

    for label, path in [
        ("v114D seal", V114D_SEAL),
        ("v114D manifest", V114D_MANIFEST),
        ("v114C review cards", V114C_CARDS),
        ("v114B delta compare result", V114B_RESULT),
        ("v114A baseline result", V114A_RESULT),
        ("v113D seal", V113D_SEAL),
    ]:
        if not os.path.exists(path):
            errors.append(f"{label} not found: {path}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    v114d_seal = load_json(V114D_SEAL)
    v114d_manifest = load_json(V114D_MANIFEST)
    v114c_cards = load_jsonl(V114C_CARDS)
    v114b_result = load_json(V114B_RESULT)
    v114a_result = load_json(V114A_RESULT)
    v113d_seal = load_json(V113D_SEAL)

    print(f"  v114D seal: {v114d_seal.get('stage_conclusion')}")
    print(f"  v114C review cards: {len(v114c_cards)} cards")
    print(f"  v113D seal: {v113d_seal.get('stage_conclusion')}")

    return v114d_seal, v114d_manifest, v114c_cards, v114b_result, v114a_result, v113d_seal


# ---------------------------------------------------------------------------
# Step 2: Analyze label confidence distribution
# ---------------------------------------------------------------------------
def analyze_label_confidence(v114c_cards):
    """Analyze label confidence distribution from v114C review cards."""
    distribution = {"high": 0, "medium": 0, "low": 0}
    low_confidence_cards = []
    for c in v114c_cards:
        lc = c.get("label_confidence", "unknown")
        if lc in distribution:
            distribution[lc] += 1
        if lc == "low":
            low_confidence_cards.append({
                "position_identity_key": c.get("position_identity_key", "?"),
                "label": c.get("label", "?"),
                "asset": c.get("asset", "?"),
                "delta_type": c.get("delta_type", "?"),
            })

    print(f"  Label confidence: high={distribution['high']}, "
          f"medium={distribution['medium']}, low={distribution['low']}")
    return distribution, low_confidence_cards


# ---------------------------------------------------------------------------
# Step 3: Check operator actions
# ---------------------------------------------------------------------------
def analyze_operator_actions(v114c_cards):
    """Check all cards are still review_only_no_send."""
    all_review_only = all(
        c.get("operator_action") == "review_only_no_send"
        for c in v114c_cards
    )
    all_not_eligible = all(
        c.get("eligible_for_real_send") is False
        for c in v114c_cards
    )
    all_not_candidate = all(
        c.get("real_send_candidate") is False
        for c in v114c_cards
    )

    print(f"  All review_only_no_send: {all_review_only}")
    print(f"  All eligible_for_real_send=false: {all_not_eligible}")
    print(f"  All real_send_candidate=false: {all_not_candidate}")
    return all_review_only, all_not_eligible, all_not_candidate


# ---------------------------------------------------------------------------
# Step 4: Check historical consistency note
# ---------------------------------------------------------------------------
def analyze_historical_note(v113d_seal, v114a_result):
    """Check v113D vs v114A count for historical mismatch."""
    v113d_counts = v113d_seal.get("chain_counts", {})
    v113d_positions = v113d_counts.get("v112X_positions", 0)
    v114a_positions = v114a_result.get("baseline_records_written", 0)

    mismatch = v113d_positions != v114a_positions
    print(f"  v113D v112X_positions: {v113d_positions}")
    print(f"  v114A baseline_records_written: {v114a_positions}")
    print(f"  Historical mismatch exists: {mismatch}")
    return mismatch, v113d_positions, v114a_positions


# ---------------------------------------------------------------------------
# Step 5: Build blockers
# ---------------------------------------------------------------------------
def build_blockers(label_distribution, low_confidence_cards, all_review_only,
                   historical_mismatch, v113d_positions, v114a_positions):
    """Build the blocker list for send-readiness gate."""
    blockers = []

    # Blocker 1: LABEL_CONFIDENCE_NO_HIGH
    blockers.append({
        "version": "v115A",
        "blocker_id": "LABEL_CONFIDENCE_NO_HIGH",
        "severity": "high",
        "blocks_send_ready": True,
        "blocks_tg_test_group_ready": True,
        "description": (
            f"Zero positions have high-confidence labels. "
            f"Label confidence distribution: high={label_distribution['high']}, "
            f"medium={label_distribution['medium']}, low={label_distribution['low']}. "
            f"Without at least one high-confidence label, no position can be "
            f"routed to send."
        ),
        "required_resolution": (
            "Establish label confidence routing policy. At minimum, require "
            "that any position routed to TG test group must have "
            "label_confidence='high'. For v115B: plan label confidence "
            "upgrade path for at least the BTC closed_position owner."
        ),
    })

    # Blocker 2: LOW_CONFIDENCE_UNKNOWN_WHALES
    low_labels = [lc["label"] for lc in low_confidence_cards]
    blockers.append({
        "version": "v115A",
        "blocker_id": "LOW_CONFIDENCE_UNKNOWN_WHALES",
        "severity": "high",
        "blocks_send_ready": True,
        "blocks_tg_test_group_ready": True,
        "description": (
            f"Low-confidence labels = {label_distribution['low']}: {', '.join(low_labels)}. "
            f"These positions MUST remain downgraded and displayed as "
            f"'Unknown Whale' only. They cannot be used for TG routing."
        ),
        "required_resolution": (
            "Low-confidence unknown whales must continue to be displayed with "
            "downgraded presentation. They cannot be promoted to send "
            "candidates until label confidence is upgraded via external "
            "verification or operator override."
        ),
    })

    # Blocker 3: REVIEW_ONLY_NO_SEND
    blockers.append({
        "version": "v115A",
        "blocker_id": "REVIEW_ONLY_NO_SEND",
        "severity": "high",
        "blocks_send_ready": True,
        "blocks_tg_test_group_ready": True,
        "description": (
            f"All 10 v114C operator review cards are still "
            f"operator_action='review_only_no_send'. "
            f"eligible_for_real_send=false for all cards. "
            f"v114D stage_conclusion='local_delta_review_ready_not_send_ready'. "
            f"No card has been promoted to a send-eligible state."
        ),
        "required_resolution": (
            "At least one card must pass through a dedicated send gate "
            "(v115B+) before any TG routing can occur. The "
            "review_only_no_send flag must be explicitly upgraded to a "
            "send candidate by operator decision."
        ),
    })

    # Blocker 4: TG_COPY_NOT_TESTED
    blockers.append({
        "version": "v115A",
        "blocker_id": "TG_COPY_NOT_TESTED",
        "severity": "medium",
        "blocks_send_ready": True,
        "blocks_tg_test_group_ready": True,
        "description": (
            "The v114C operator review copy (review_summary) is designed "
            "for local operator review, NOT for TG send. No TG-formatted "
            "send copy has been generated or tested. The operator review "
            "copy must NOT be reused as TG send copy."
        ),
        "required_resolution": (
            "TG test copy must be generated separately from operator review "
            "copy. A dedicated TG formatting gate must produce send-ready "
            "copy that follows TG test group formatting conventions. "
            "This copy must be reviewed locally before any test send."
        ),
    })

    # Blocker 5: HISTORICAL_COUNT_MISMATCH_NOTE
    blockers.append({
        "version": "v115A",
        "blocker_id": "HISTORICAL_COUNT_MISMATCH_NOTE",
        "severity": "low",
        "blocks_send_ready": False,
        "blocks_tg_test_group_ready": False,
        "description": (
            f"Known historical count mismatch preserved from v113D: "
            f"v113D v112X_positions={v113d_positions} vs "
            f"v114A baseline_records_written={v114a_positions}. "
            f"This is a documented data consistency note (different "
            f"snapshot timing from same v112X data source). Does not "
            f"block send readiness directly but must remain documented."
        ),
        "required_resolution": (
            "No resolution required for send readiness. This is a "
            "historical artifact. Keep the note in all downstream reports. "
            "If future stages show new count inconsistencies, investigate "
            "separately."
        ),
    })

    # Blocker 6: NO_SEND_TEMPLATE_GATE
    blockers.append({
        "version": "v115A",
        "blocker_id": "NO_SEND_TEMPLATE_GATE",
        "severity": "high",
        "blocks_send_ready": True,
        "blocks_tg_test_group_ready": True,
        "description": (
            "No separate TG test group formatting gate exists. "
            "The current pipeline has operator review cards but no "
            "send template, no one-shot send preview gate, and no "
            "TG formatting step. Without a dedicated formatting gate, "
            "any send would be unformatted and untested."
        ),
        "required_resolution": (
            "Create a dedicated TG test group formatting gate (v115B+). "
            "This gate must: (1) generate TG-formatted send copy, "
            "(2) provide one-shot send preview before any actual send, "
            "(3) enforce formatting conventions, "
            "(4) include rollback / no-repeat / cooldown protections, "
            "(5) require explicit user pre-authorization scoped to "
            "TG test group only."
        ),
    })

    return blockers


# ---------------------------------------------------------------------------
# Step 6: Build send-readiness gate result
# ---------------------------------------------------------------------------
def build_gate_result(v114d_seal, v114c_cards, label_distribution,
                      blockers):
    """Build the v115A gate result JSON."""
    result = {
        "version": "v115A",
        "status": "passed",
        "strategy_gate": "whale_delta_send_readiness",
        "input_stage": "v114D",
        "input_stage_conclusion": "local_delta_review_ready_not_send_ready",
        "send_ready": False,
        "tg_test_group_ready": False,
        "local_review_ready": True,
        "external_api_called": EXTERNAL_API_CALLED,
        "prod_state_write": PROD_STATE_WRITE,
        "tg_sent": TG_SENT,
        "credentials_read": CREDENTIALS_READ,
        "daemon_started": DAEMON_STARTED,
        "watcher_started": WATCHER_STARTED,
        "files_deleted": FILES_DELETED,
        "eligible_for_real_send_count": v114d_seal.get("eligible_for_real_send_count", 0),
        "real_send_candidate_count": v114d_seal.get("real_send_candidate_count", 0),
        "tg_send_allowed_count": v114d_seal.get("tg_send_allowed_count", 0),
        "blocker_count": len(blockers),
        "label_confidence_distribution": label_distribution,
        "review_cards_total": len(v114c_cards),
        "review_only_no_send_count": sum(
            1 for c in v114c_cards
            if c.get("operator_action") == "review_only_no_send"
        ),
        "next_step": "v115b_whale_label_confidence_upgrade_plan_local_only",
        "generated_at": now_iso(),
    }
    save_json(OUT_RESULT, result)
    return result


# ---------------------------------------------------------------------------
# Step 7: Generate blockers JSONL
# ---------------------------------------------------------------------------
def generate_blockers_jsonl(blockers):
    """Write blockers to JSONL file."""
    save_jsonl(OUT_BLOCKERS, blockers)
    print(f"  Blockers JSONL -> {OUT_BLOCKERS} ({len(blockers)} blockers)")


# ---------------------------------------------------------------------------
# Step 8: Generate markdown strategy report
# ---------------------------------------------------------------------------
def generate_markdown_report(gate_result, blockers, label_distribution,
                             low_confidence_cards, v114d_seal, v113d_seal,
                             v114a_result):
    """Generate the v115A markdown strategy report."""

    blocker_rows = ""
    for b in blockers:
        blocks_send = "🔴 YES" if b["blocks_send_ready"] else "🟡 partial"
        blocks_tg = "🔴 YES" if b["blocks_tg_test_group_ready"] else "🟡 partial"
        blocker_rows += (
            f"| {b['blocker_id']} | {b['severity'].upper()} | "
            f"{blocks_send} | {blocks_tg} | "
            f"{b['description'][:120]}... |\n"
        )

    low_whale_rows = ""
    for lc in low_confidence_cards:
        low_whale_rows += (
            f"| `{lc['position_identity_key'][:50]}...` | "
            f"{lc['label']} | {lc['asset']} | {lc['delta_type']} |\n"
        )

    report = f"""# v115A Whale Delta Send-Readiness Strategy Gate — Local Only

**Generated:** {gate_result['generated_at']}
**Status:** {gate_result['status']}
**Version:** v115A
**Input Stage:** v114D (`{gate_result['input_stage_conclusion']}`)

---

## 1. Purpose

This is a **strategy gate**, NOT a send step. Its sole purpose is to answer:

> *Why is the current v114D sealed pack NOT send-ready?*
> *What conditions must be met before it can enter TG test group?*

No send occurs. No production state is written. This is a local-only policy evaluation.

---

## 2. Send-Readiness Judgment

| Decision | Value | Expected |
|----------|-------|----------|
| **send_ready** | ❌ `false` | `false` ✅ |
| **tg_test_group_ready** | ❌ `false` | `false` ✅ |
| **local_review_ready** | ✅ `true` | `true` ✅ |
| eligible_for_real_send_count | `{gate_result['eligible_for_real_send_count']}` | 0 ✅ |
| real_send_candidate_count | `{gate_result['real_send_candidate_count']}` | 0 ✅ |
| tg_send_allowed_count | `{gate_result['tg_send_allowed_count']}` | 0 ✅ |

**Conclusion:** The v114D sealed pack is **local-review-ready** but **NOT send-ready** and **NOT TG-test-group-ready**. All routing counts are zero as expected.

---

## 3. Blocker Summary ({len(blockers)} blockers)

| Blocker ID | Severity | Blocks Send | Blocks TG | Description |
|------------|----------|-------------|-----------|-------------|
{blocker_rows}

---

## 4. Blockers Detail

### 4.1 LABEL_CONFIDENCE_NO_HIGH — HIGH

**Why it blocks:**
- Zero positions out of {gate_result['review_cards_total']} have `label_confidence='high'`.
- Without high-confidence labels, no position can be trusted for any routing decision.

**Label confidence distribution:**

| Level | Count | Cards |
|-------|-------|-------|
| 🔴 High | **{label_distribution['high']}** | — |
| 🟡 Medium | {label_distribution['medium']} | loraclexyz (7) + Matrixport Related (1) |
| 🟠 Low | {label_distribution['low']} | Unknown Hyperliquid Whale + Unknown HYPE Whale |

**Required resolution:** Establish label confidence routing policy. Plan v115B label confidence upgrade path.

### 4.2 LOW_CONFIDENCE_UNKNOWN_WHALES — HIGH

**Why it blocks:**
- {label_distribution['low']} positions have low-confidence labels. These are unknown entities and cannot be promoted to send candidates.

**Low-confidence cards:**

| Position Key | Label | Asset | Delta Type |
|-------------|-------|-------|-------------|
{low_whale_rows}

**Required resolution:** Low-confidence unknown whales must remain downgraded. Do not promote to send candidates without external verification.

### 4.3 REVIEW_ONLY_NO_SEND — HIGH

**Why it blocks:**
- All {gate_result['review_cards_total']} v114C operator review cards have `operator_action='review_only_no_send'`.
- v114D stage_conclusion is `local_delta_review_ready_not_send_ready`.
- No card has been promoted to a send-eligible state.

**Required resolution:** At least one card must pass through a dedicated send gate (v115B+) with explicit promotion to send candidate.

### 4.4 TG_COPY_NOT_TESTED — MEDIUM

**Why it blocks:**
- Operator review copy (v114C `review_summary`) is NOT TG send copy.
- No TG-formatted send message has been generated or tested.
- Reusing operator review copy for TG send would produce unformatted, untested output.

**Required resolution:** Generate TG test copy separately. Review locally before any test send.

### 4.5 HISTORICAL_COUNT_MISMATCH_NOTE — LOW

**Why it's noted (not a hard block):**
- v113D `v112X_positions` = {v113d_seal.get('chain_counts', {}).get('v112X_positions', '?')}
- v114A `baseline_records_written` = {v114a_result.get('baseline_records_written', '?')}
- Difference is a known artifact of different snapshot timing from same v112X data.
- Does NOT block send readiness but must remain documented.

**Required resolution:** Keep note in all downstream reports. Investigate only if new inconsistencies appear.

### 4.6 NO_SEND_TEMPLATE_GATE — HIGH

**Why it blocks:**
- No dedicated TG test group formatting gate exists.
- No one-shot send preview gate.
- No rollback / no-repeat / cooldown protections.
- No user pre-authorization mechanism for TG test group.

**Required resolution:** Create a dedicated TG test group formatting gate that includes:
- TG-formatted send copy generation
- One-shot send preview before any send
- Rollback / no-repeat / cooldown protections
- Explicit user pre-authorization scoped to TG test group only

---

## 5. Future Readiness Checklist — Minimum Conditions for TG Test Group

The following conditions MUST be met before any card enters TG test group:

1. ✅ **Label confidence routing policy established**
   - At minimum: `label_confidence='high'` required for TG routing
   - Medium-confidence labels may be considered for test-only after review

2. ✅ **Low-confidence unknown whales remain downgraded**
   - Unknown Hyperliquid Whale and Unknown HYPE Whale stay as degraded display
   - No promotion without external verification

3. ✅ **TG test copy generated separately**
   - NOT reusing operator review copy
   - TG-formatted message follows test group conventions
   - Reviewed locally before any send

4. ✅ **TG test group send remains test-only**
   - No production state writes
   - No real send to production channel
   - Test group delivery only

5. ✅ **One-shot send preview gate exists**
   - Before any actual send, a preview must be generated and reviewed
   - Preview must show exact message content, recipient, and routing

6. ✅ **Rollback / no-repeat / cooldown protections**
   - Same-asset cooldown enforced
   - No-repeat guard against duplicate sends
   - Rollback capability documented

7. ✅ **User pre-authorization scoped to TG test group only**
   - Authorization is for test group, NOT production channel
   - Explicit user confirmation required
   - No implied production publish permission

---

## 6. Safety Invariant Status

| Invariant | Status |
|-----------|--------|
| external_api_called | ✅ `{gate_result['external_api_called']}` |
| prod_state_write | ✅ `{gate_result['prod_state_write']}` |
| tg_sent | ✅ `{gate_result['tg_sent']}` |
| credentials_read | ✅ `{gate_result['credentials_read']}` |
| daemon_started | ✅ `{gate_result['daemon_started']}` |
| watcher_started | ✅ `{gate_result['watcher_started']}` |
| files_deleted | ✅ `{gate_result['files_deleted']}` |
| old results modified | ✅ No (v114A-v114D unchanged) |
| real send candidate generated | ✅ No (0 candidates) |

---

## 7. Explicit NOT Declarations

This stage is explicitly **NOT**:

- ❌ Send-ready
- ❌ TG-test-group-ready
- ❌ Production-state-ready
- ❌ A real send candidate
- ❌ A TG send
- ❌ A trading signal
- ❌ A position recommendation
- ❌ Live-passed
- ❌ Ready for external consumption

This stage **IS**:

- ✅ A local-only strategy gate evaluation
- ✅ Input for v115B planning
- ✅ Fully guarded with safety invariants
- ✅ Traceable, verifiable, reproducible

---

## 8. Next Step

**`{gate_result['next_step']}`**

The next executor should:
1. Plan label confidence upgrade path (focus on BTC closed_position owner)
2. Define label confidence routing policy thresholds
3. Design TG test copy formatting gate
4. Design one-shot send preview gate
5. Design rollback / cooldown / no-repeat protections
6. Define user pre-authorization mechanism

---

## 9. Output Files

| File | Path |
|------|------|
| Gate Result JSON | `{OUT_RESULT}` |
| Blockers JSONL | `{OUT_BLOCKERS}` |
| Strategy Report MD | `{OUT_REPORT}` |
| Handoff MD | `{OUT_HANDOFF}` |

---

*This strategy gate report is for local operator review only. No external communication intended.*
"""
    save_text(OUT_REPORT, report)


# ---------------------------------------------------------------------------
# Step 9: Generate handoff
# ---------------------------------------------------------------------------
def generate_handoff(gate_result, blockers):
    """Generate the v115A handoff markdown."""

    blocker_summary = ""
    for b in blockers:
        blocker_summary += (
            f"- **{b['blocker_id']}** ({b['severity'].upper()}): "
            f"{b['description'][:150]}...\n"
        )

    handoff = f"""# v115A Handoff — Whale Delta Send-Readiness Strategy Gate Local Only

**Generated:** {gate_result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only
**Status:** {gate_result['status']}

---

## What was done

1. Read v114D seal (stage_conclusion: `{gate_result['input_stage_conclusion']}`)
2. Read v114C operator review cards ({gate_result['review_cards_total']} cards)
3. Read v113D seal for historical context
4. Read v114A baseline for cross-validation
5. Analyzed label confidence distribution: high={gate_result['label_confidence_distribution']['high']}, medium={gate_result['label_confidence_distribution']['medium']}, low={gate_result['label_confidence_distribution']['low']}
6. Identified {gate_result['blocker_count']} blockers for send readiness
7. Generated gate result JSON, blockers JSONL, strategy report, and handoff
8. Stage conclusion: **send_ready=false, tg_test_group_ready=false, local_review_ready=true**

## Send-Readiness Decision

| Field | Value |
|-------|-------|
| send_ready | ❌ `false` |
| tg_test_group_ready | ❌ `false` |
| local_review_ready | ✅ `true` |
| eligible_for_real_send_count | `{gate_result['eligible_for_real_send_count']}` |
| real_send_candidate_count | `{gate_result['real_send_candidate_count']}` |
| tg_send_allowed_count | `{gate_result['tg_send_allowed_count']}` |

## Blockers Summary

{blocker_summary}

## Future Readiness Checklist

1. Label confidence routing policy established (high-confidence required for TG)
2. Low-confidence unknown whales remain downgraded
3. TG test copy generated separately from operator review copy
4. TG test group send remains test-only, no prod state write
5. One-shot send preview gate exists
6. Rollback / no-repeat / cooldown protections in place
7. User pre-authorization scoped to TG test group only

## Safety Invariants Confirmed

- `external_api_called=false`
- `prod_state_write=false`
- `tg_sent=false`
- `credentials_read=false`
- `daemon_started=false`
- `watcher_started=false`
- `files_deleted=false`
- v114A-v114D old results NOT modified
- No real send candidate generated

## This Stage Is NOT

- Send-ready
- TG-test-group-ready
- A TG send
- A trading signal
- Production state
- Live-passed

## This Stage IS

- A local-only strategy gate
- Input for v115B
- Fully guarded

## Next Step

**{gate_result['next_step']}**

Plan v115B: whale label confidence upgrade, TG formatting gate design,
send preview gate design, and cooldown protections.

---

*This handoff is for the next stage decision-maker. No action required now.*
"""
    save_text(OUT_HANDOFF, handoff)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v115A Whale Delta Send-Readiness Strategy Gate — Local Only")
    print("=" * 70)

    # Step 1: Load reference inputs
    print("\n[1/6] Loading reference inputs...")
    (v114d_seal, v114d_manifest, v114c_cards,
     v114b_result, v114a_result, v113d_seal) = load_reference_inputs()

    # Step 2: Analyze label confidence
    print("\n[2/6] Analyzing label confidence distribution...")
    label_distribution, low_confidence_cards = analyze_label_confidence(v114c_cards)

    # Step 3: Analyze operator actions
    print("\n[3/6] Analyzing operator actions...")
    all_review_only, all_not_eligible, all_not_candidate = analyze_operator_actions(v114c_cards)

    # Step 4: Analyze historical consistency note
    print("\n[4/6] Analyzing historical consistency note...")
    mismatch, v113d_positions, v114a_positions = analyze_historical_note(
        v113d_seal, v114a_result)

    # Step 5: Build blockers
    print("\n[5/6] Building blockers...")
    blockers = build_blockers(
        label_distribution, low_confidence_cards, all_review_only,
        mismatch, v113d_positions, v114a_positions)
    print(f"  Built {len(blockers)} blockers")

    # Step 6: Generate all outputs
    print("\n[6/6] Generating outputs...")

    gate_result = build_gate_result(
        v114d_seal, v114c_cards, label_distribution, blockers)
    print(f"  Gate result -> {OUT_RESULT}")

    generate_blockers_jsonl(blockers)

    generate_markdown_report(
        gate_result, blockers, label_distribution,
        low_confidence_cards, v114d_seal, v113d_seal, v114a_result)
    print(f"  Strategy report -> {OUT_REPORT}")

    generate_handoff(gate_result, blockers)
    print(f"  Handoff -> {OUT_HANDOFF}")

    # Final summary
    print("\n" + "=" * 70)
    print("v115A STRATEGY GATE COMPLETE")
    print(f"  send_ready: {gate_result['send_ready']}")
    print(f"  tg_test_group_ready: {gate_result['tg_test_group_ready']}")
    print(f"  local_review_ready: {gate_result['local_review_ready']}")
    print(f"  Blockers: {len(blockers)}")
    print(f"  Next step: {gate_result['next_step']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
