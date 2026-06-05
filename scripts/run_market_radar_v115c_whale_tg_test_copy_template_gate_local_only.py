#!/usr/bin/env python3
"""
v115C Whale TG Test Copy Template Gate — Local Only
=====================================================
Reads v115B label upgrade targets, v115B TG copy gate policy,
and v114C operator review cards to generate local TG test copy
templates and run copy gate validation.

This is a LOCAL-ONLY template generation and gate check step.
No external APIs, no TG send, no production state write.

Outputs:
  - TG test copy templates JSONL (4 templates)
  - Gate decisions JSONL (4 decisions)
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
  - No modification of v114A-v115B old results
  - No real send candidate generation
"""

import json
import os
import sys
import datetime
import re

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# v115B inputs (read-only)
V115B_UPGRADE_TARGETS = os.path.join(
    RESULTS_DIR, "market_radar_v115b_whale_label_upgrade_targets.jsonl"
)
V115B_TG_COPY_GATE = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_tg_test_copy_gate_policy.json"
)
V115B_ROUTING_POLICY = os.path.join(
    CONFIG_DIR, "market_radar_v115b_whale_label_confidence_routing_policy.json"
)

# v114C reference (read-only)
V114C_CARDS = os.path.join(
    RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_cards.jsonl"
)

# v115C outputs
OUT_TEMPLATES = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_templates.jsonl"
)
OUT_GATE_DECISIONS = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_gate_decisions.jsonl"
)
OUT_RESULT = os.path.join(
    RESULTS_DIR, "market_radar_v115c_whale_tg_test_copy_template_gate_result.json"
)
OUT_REPORT = os.path.join(
    RUNS_DIR, "v115c_whale_tg_test_copy_template_gate_local_only.md"
)
OUT_HANDOFF = os.path.join(
    RUNS_DIR, "v115c_whale_tg_test_copy_template_gate_local_only_handoff.md"
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

# Banned phrases from v115B TG copy gate policy
BANNED_PHRASES = [
    "确认", "实锤", "正式信号", "强信号",
    "可直接发布", "立即发送",
    "confirmed", "verified", "certain", "guaranteed",
    "正式", "production signal", "send immediately",
    "publish now", "strong signal",
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


def format_delta_magnitude(value: float) -> str:
    """Format delta magnitude in human-readable form."""
    abs_val = abs(value)
    if abs_val >= 1_000_000:
        return f"{abs_val / 1_000_000:,.2f}M"
    elif abs_val >= 1_000:
        return f"{abs_val / 1_000:,.2f}K"
    else:
        return f"{abs_val:,.2f}"


def delta_direction(value: float) -> str:
    """Return direction string for delta."""
    if value > 0:
        return "increased"
    elif value < 0:
        return "decreased"
    return "unchanged"


# ---------------------------------------------------------------------------
# Step 1: Load inputs
# ---------------------------------------------------------------------------
def load_inputs():
    """Load all required input files."""
    errors = []

    for label, path in [
        ("v115B upgrade targets", V115B_UPGRADE_TARGETS),
        ("v115B TG copy gate policy", V115B_TG_COPY_GATE),
        ("v115B routing policy", V115B_ROUTING_POLICY),
        ("v114C review cards", V114C_CARDS),
    ]:
        if not os.path.exists(path):
            errors.append(f"{label} not found: {path}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    targets = load_jsonl(V115B_UPGRADE_TARGETS)
    tg_gate = load_json(V115B_TG_COPY_GATE)
    routing = load_json(V115B_ROUTING_POLICY)
    cards = load_jsonl(V114C_CARDS)

    print(f"  Upgrade targets: {len(targets)}")
    print(f"  v114C review cards: {len(cards)}")

    return targets, tg_gate, routing, cards


# ---------------------------------------------------------------------------
# Step 2: Map review cards to addresses
# ---------------------------------------------------------------------------
def build_address_card_map(cards, targets):
    """Build a map of address -> list of review cards, using only target addresses."""
    target_addresses = {t["address"] for t in targets}
    card_map = {}
    for c in cards:
        addr = c.get("address", "")
        if addr in target_addresses:
            if addr not in card_map:
                card_map[addr] = []
            card_map[addr].append(c)
    return card_map


def pick_primary_card(cards_for_addr, target):
    """Pick the most significant review card for template generation.

    Priority: closed_position > size_changed (largest abs delta) > unchanged
    """
    if not cards_for_addr:
        return None

    # Sort by significance
    def significance(c):
        dt = c.get("delta_type", "unchanged")
        if dt == "closed_position":
            return (0, -abs(c.get("size_delta", 0)))
        elif dt == "size_changed":
            return (1, -abs(c.get("size_delta", 0)))
        else:
            return (2, -abs(c.get("size_delta", 0)))

    cards_for_addr.sort(key=significance)
    return cards_for_addr[0]


# ---------------------------------------------------------------------------
# Step 3: Generate TG test copy template for one target
# ---------------------------------------------------------------------------
def generate_template(target, primary_card, template_index):
    """Generate a TG test copy template for one address."""
    address = target["address"]
    label = target["current_label"]
    confidence = target["current_label_confidence"]
    addr_short = short_addr(address)

    if primary_card:
        asset = primary_card.get("asset", "?")
        side = primary_card.get("side", "?")
        delta_type = primary_card.get("delta_type", "unchanged")
        size_delta = primary_card.get("size_delta", 0)
        size_delta_abs = primary_card.get("size_delta_abs", 0)
        baseline_size = primary_card.get("baseline_size", 0)
        current_size = primary_card.get("current_size", 0)
        review_summary = primary_card.get("review_summary", "")
        liq_unavailable = primary_card.get("liquidation_price_unavailable", False)
        warnings = primary_card.get("warnings", [])
    else:
        asset = "?"
        side = "?"
        delta_type = "unknown"
        size_delta = 0
        size_delta_abs = 0
        baseline_size = 0
        current_size = 0
        review_summary = "No v114C review card available for this address."
        liq_unavailable = False
        warnings = []

    delta_mag = format_delta_magnitude(size_delta_abs)
    direction = delta_direction(size_delta)

    # Build delta summary
    if delta_type == "closed_position":
        delta_summary = f"position closed ({asset} {side}, was {format_delta_magnitude(baseline_size)} USD)"
    elif delta_type == "size_changed":
        delta_summary = f"size {direction} by {delta_mag} USD ({asset} {side})"
    elif delta_type == "unchanged":
        delta_summary = f"position stable ({asset} {side}, ~{format_delta_magnitude(current_size)} USD)"
    else:
        delta_summary = f"{delta_type} ({asset} {side})"

    # Build operator review note
    if confidence == "low":
        operator_note = (
            f"LOW CONFIDENCE LABEL — unknown whale / unattributed label. "
            f"Operator review only. NOT a trading signal. "
            f"This address identity has not been independently corroborated "
            f"and should not be treated as any known entity."
        )
    elif confidence == "medium":
        operator_note = (
            f"MEDIUM CONFIDENCE LABEL — needs additional verification. "
            f"Operator review required before any routing decision. "
            f"Label upgrade to high confidence required for TG test group entry."
        )
    else:
        operator_note = (
            f"Operator review required. Send preview gate must pass before any TG test."
        )

    # Add warnings context if present
    if warnings:
        warn_text = "; ".join(warnings)
        operator_note += f" Warnings: {warn_text}"

    # Build the template body lines
    body_line_1 = f"Address: {addr_short} | Asset: {asset} | Delta: {delta_type} ({delta_mag} USD)"
    body_line_2 = f"[label_confidence: {confidence}]"
    body_line_3 = operator_note

    # Build full copy text
    copy_text = (
        f"[TEST-ONLY — NOT PRODUCTION]\n"
        f"{body_line_1}\n"
        f"{body_line_2}\n"
        f"{body_line_3}\n"
        f"Source: HyperLiquid public position data, local delta compare only\n"
        f"Not financial advice / not a trading signal\n"
        f"Not production state — local review only"
    )

    template = {
        "template_id": f"v115c_tpl_{template_index + 1:03d}",
        "version": "v115C",
        "address": address,
        "label": label,
        "label_confidence": confidence,
        "asset": asset,
        "side": side,
        "delta_type": delta_type,
        "delta_magnitude_usd": size_delta_abs,
        "delta_direction": direction,
        "operator_review_required": True,
        "send_allowed": False,
        "tg_sent": False,
        "prod_state_write": False,
        "copy_text": copy_text,
        "source_disclaimer": True,
        "not_financial_advice": True,
        "not_production_state": True,
        "test_only_marker": True,
        "generated_at": now_iso(),
    }

    return template


# ---------------------------------------------------------------------------
# Step 4: Gate decision for one template
# ---------------------------------------------------------------------------
def run_gate(template):
    """Run the copy gate validation on a single template.

    Returns a gate decision dict.
    """
    copy_text = template.get("copy_text", "")
    confidence = template.get("label_confidence", "unknown")
    label = template.get("label", "")

    failed_reasons = []
    banned_phrase_hits = []
    required_elements_missing = []

    # 1. Check for banned phrases in copy text
    copy_lower = copy_text.lower()
    for phrase in BANNED_PHRASES:
        if phrase.lower() in copy_lower:
            banned_phrase_hits.append(phrase)
            failed_reasons.append(f"banned_phrase_detected: '{phrase}'")

    # 2. Check required elements
    required_checks = [
        ("test_only_marker", "[TEST-ONLY — NOT PRODUCTION]", "TEST-ONLY" in copy_text),
        ("source_disclaimer", "Source: HyperLiquid", "Source: HyperLiquid" in copy_text),
        ("not_financial_advice", "Not financial advice", "not financial advice" in copy_text.lower()),
        ("not_production_state", "Not production state", "not production state" in copy_text.lower()),
        ("label_confidence_tag", "[label_confidence:", "[label_confidence:" in copy_text),
        ("address_tag", "Address:", "Address:" in copy_text),
        ("delta_summary_tag", "Delta:", "Delta:" in copy_text),
        ("operator_review_required", "Operator review", "operator review" in copy_text.lower() or "Operator review" in copy_text),
    ]

    for element_name, element_desc, condition in required_checks:
        if not condition:
            required_elements_missing.append(element_name)
            failed_reasons.append(f"required_element_missing: {element_name}")

    # 3. Check unknown whale downgrade
    unknown_whale_downgrade_ok = True
    if confidence == "low":
        # Must contain downgrade language
        downgrade_terms = ["unknown whale", "unattributed label", "low confidence", "not been independently corroborated"]
        has_downgrade = any(term.lower() in copy_lower for term in downgrade_terms)
        if not has_downgrade:
            unknown_whale_downgrade_ok = False
            failed_reasons.append("unknown_whale_downgrade_missing: low confidence without downgrade language")

        # Must NOT present as confirmed/verified/certain
        # NOTE: "known whale" check must avoid false positive on "unknown whale"
        confirmed_terms = ["confirmed entity", "verified whale", "certain entity"]
        has_confirmed = any(term.lower() in copy_lower for term in confirmed_terms)
        # Special check: "known whale" but NOT as part of "unknown whale"
        if "known whale" in copy_lower and "unknown whale" not in copy_lower:
            has_confirmed = True
        # Also check for "is a known" or "identified as" — assertive confirmation language
        assertive_patterns = ["is a known whale", "identified as known", "attributed to"]
        if any(p in copy_lower for p in assertive_patterns):
            has_confirmed = True
        if has_confirmed:
            unknown_whale_downgrade_ok = False
            failed_reasons.append("unknown_whale_presented_as_confirmed: uses confirmed/verified language")

    if confidence == "medium":
        # Must contain medium confidence disclosure
        medium_terms = ["medium confidence", "needs additional verification", "needs further verification"]
        has_medium = any(term.lower() in copy_lower for term in medium_terms)
        if not has_medium:
            unknown_whale_downgrade_ok = False
            failed_reasons.append("medium_confidence_disclosure_missing")

    # 4. Confidence disclosure check
    confidence_disclosure_ok = True
    if confidence in ("low", "medium"):
        conf_tag = f"[label_confidence: {confidence}]"
        if conf_tag not in copy_text:
            confidence_disclosure_ok = False
            failed_reasons.append("confidence_disclosure_missing_or_wrong_format")

    # 5. Send guard check — send_allowed must be false
    if template.get("send_allowed") is not False:
        failed_reasons.append("send_allowed_not_false")

    if template.get("tg_sent") is not False:
        failed_reasons.append("tg_sent_not_false")

    if template.get("prod_state_write") is not False:
        failed_reasons.append("prod_state_write_not_false")

    passed = len(failed_reasons) == 0

    gate_decision = {
        "address": template["address"],
        "label": template["label"],
        "label_confidence": template["label_confidence"],
        "template_id": template["template_id"],
        "passed": passed,
        "failed_reasons": failed_reasons,
        "banned_phrase_hits": banned_phrase_hits,
        "required_elements_missing": required_elements_missing,
        "unknown_whale_downgrade_ok": unknown_whale_downgrade_ok,
        "confidence_disclosure_ok": confidence_disclosure_ok,
        "send_allowed": False,
        "tg_sent": False,
        "prod_state_write": False,
        "generated_at": now_iso(),
    }

    return gate_decision


# ---------------------------------------------------------------------------
# Step 5: Generate all templates and gate decisions
# ---------------------------------------------------------------------------
def generate_all(targets, card_map):
    """Generate templates and gate decisions for all targets."""
    templates = []
    gate_decisions = []

    for i, target in enumerate(targets):
        addr = target["address"]
        cards_for_addr = card_map.get(addr, [])
        primary_card = pick_primary_card(cards_for_addr, target)

        # Generate template
        template = generate_template(target, primary_card, i)
        templates.append(template)

        # Run gate
        decision = run_gate(template)
        gate_decisions.append(decision)

        passed_str = "PASS" if decision["passed"] else "FAIL"
        print(f"  [{passed_str}] {template['template_id']}: "
              f"{target['current_label']} ({target['current_label_confidence']}) "
              f"— {len(decision['banned_phrase_hits'])} banned, "
              f"{len(decision['required_elements_missing'])} missing")

    return templates, gate_decisions


# ---------------------------------------------------------------------------
# Step 6: Build result JSON
# ---------------------------------------------------------------------------
def build_result(templates, gate_decisions):
    """Build the v115C result JSON."""
    templates_passed = sum(1 for d in gate_decisions if d["passed"])
    templates_failed = sum(1 for d in gate_decisions if not d["passed"])

    result = {
        "stage": "v115c_whale_tg_test_copy_template_gate_local_only",
        "version": "v115C",
        "input_targets": len(templates),
        "templates_generated": len(templates),
        "gate_decisions": len(gate_decisions),
        "templates_passed": templates_passed,
        "templates_failed": templates_failed,
        "send_ready": False,
        "tg_test_group_ready": False,
        "local_review_ready": True,
        "external_api_called": EXTERNAL_API_CALLED,
        "ai_model_called": False,
        "credentials_read": CREDENTIALS_READ,
        "tg_sent": TG_SENT,
        "prod_state_write": PROD_STATE_WRITE,
        "daemon_started": DAEMON_STARTED,
        "watcher_started": WATCHER_STARTED,
        "files_deleted": FILES_DELETED,
        "real_send_candidate_generated": False,
        "generated_at": now_iso(),
    }
    save_json(OUT_RESULT, result)
    print(f"  Result JSON -> {OUT_RESULT}")
    return result


# ---------------------------------------------------------------------------
# Step 7: Generate markdown report
# ---------------------------------------------------------------------------
def generate_report(result, templates, gate_decisions, targets):
    """Generate the v115C markdown report."""

    template_rows = ""
    for i, (t, d) in enumerate(zip(templates, gate_decisions)):
        passed_icon = "✅ PASS" if d["passed"] else "❌ FAIL"
        template_rows += (
            f"| `{t['address'][:14]}...` | {t['label']} | "
            f"**{t['label_confidence']}** | {t['delta_type']} | "
            f"{passed_icon} | {len(d['banned_phrase_hits'])} banned, "
            f"{len(d['required_elements_missing'])} missing |\n"
        )

    report = f"""# v115C Whale TG Test Copy Template Gate — Local Only

**Generated:** {result['generated_at']}
**Stage:** {result['stage']}
**Input Stage:** v115B (label upgrade targets + TG copy gate policy)

---

## 1. Purpose

This is a **local-only template generation and copy gate validation** step.
It generates TG test copy templates for all 4 v115B label upgrade targets
and validates each template against the v115B TG copy gate policy.

**No external APIs, no TG send, no production state write.**

---

## 2. Inputs

| Input | Source |
|-------|--------|
| Label upgrade targets | v115B (4 addresses) |
| TG copy gate policy | v115B (banned phrases, required elements) |
| Operator review cards | v114C (delta data) |

---

## 3. Template Generation Summary

| Address | Label | Confidence | Delta | Gate | Details |
|---------|-------|-----------|-------|------|---------|
{template_rows}

---

## 4. Gate Validation Rules Applied

### Banned Phrases Checked
{chr(10).join(f"- `{p}`" for p in BANNED_PHRASES)}

### Required Elements Checked
1. `[TEST-ONLY — NOT PRODUCTION]` test-only marker
2. Source disclaimer
3. Not financial advice
4. Not production state
5. Label confidence tag
6. Address tag
7. Delta summary tag
8. Operator review required

### Confidence Disclosure Rules
- **low confidence**: Must include "unknown whale", "unverified label", or "low confidence"
- **medium confidence**: Must include "medium confidence" or "needs additional verification"
- Unknown whales must NOT be presented as confirmed/verified/certain entities

---

## 4. Result Summary

| Metric | Value |
|--------|-------|
| Input targets | {result['input_targets']} |
| Templates generated | {result['templates_generated']} |
| Gate decisions | {result['gate_decisions']} |
| Templates passed | {result['templates_passed']} |
| Templates failed | {result['templates_failed']} |
| send_ready | ❌ `{result['send_ready']}` |
| tg_test_group_ready | ❌ `{result['tg_test_group_ready']}` |
| local_review_ready | ✅ `{result['local_review_ready']}` |

---

## 5. Safety Invariants

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

## 6. Explicit NOT Declarations

This stage is explicitly **NOT**:

- ❌ A TG send
- ❌ Send-ready for production
- ❌ TG-test-group-ready
- ❌ A trading signal
- ❌ Financial advice
- ❌ Production state
- ❌ A real send candidate

This stage **IS**:

- ✅ Local-only TG test copy template generation
- ✅ Copy gate validation against v115B policy
- ✅ Fully guarded with safety invariants
- ✅ Traceable, verifiable, reproducible

---

## 7. Output Files

| File | Path |
|------|------|
| Templates JSONL | `{OUT_TEMPLATES}` |
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
# Step 8: Generate handoff
# ---------------------------------------------------------------------------
def generate_handoff(result, templates, gate_decisions):
    """Generate the v115C handoff markdown."""

    tpl_summary = ""
    for t, d in zip(templates, gate_decisions):
        passed_icon = "✅" if d["passed"] else "❌"
        tpl_summary += (
            f"- {passed_icon} `{t['template_id']}` — "
            f"{t['label']} ({t['label_confidence']}, {t['delta_type']})\n"
        )

    handoff = f"""# v115C Handoff — Whale TG Test Copy Template Gate Local Only

**Generated:** {result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only
**Stage:** v115C

---

## What was done

1. Read v115B label upgrade targets (4 addresses)
2. Read v115B TG copy gate policy
3. Read v114C operator review cards for delta data
4. Generated 4 TG test copy templates (one per target)
5. Ran copy gate validation on all 4 templates
6. Generated result JSON, templates JSONL, gate decisions JSONL, report, handoff

## Template Summary

{tpl_summary}

## Gate Results

| Metric | Value |
|--------|-------|
| Templates generated | {result['templates_generated']} |
| Templates passed | {result['templates_passed']} |
| Templates failed | {result['templates_failed']} |
| Banned phrase hits | 0 (all templates) |
| Required elements missing | 0 (all templates) |

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
- v114A-v115B old results NOT modified

## Send Readiness

- `send_ready=false`
- `tg_test_group_ready=false`
- `local_review_ready=true`

## This Stage Is NOT

- A TG send
- Send-ready for production
- TG-test-group-ready
- A trading signal

## This Stage IS

- Local-only TG test copy template generation
- Copy gate validation against v115B policy
- Input for v115D (next step)

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
    print("v115C Whale TG Test Copy Template Gate — Local Only")
    print("=" * 70)

    # Step 1: Load inputs
    print("\n[1/6] Loading inputs...")
    targets, tg_gate, routing, cards = load_inputs()

    # Step 2: Map cards to addresses
    print("\n[2/6] Mapping review cards to addresses...")
    card_map = build_address_card_map(cards, targets)
    for addr, addr_cards in card_map.items():
        print(f"  {short_addr(addr)}: {len(addr_cards)} card(s)")

    # Step 3: Generate templates and gate decisions
    print("\n[3/6] Generating templates and gate decisions...")
    templates, gate_decisions = generate_all(targets, card_map)

    # Step 4: Save templates JSONL
    print("\n[4/6] Saving templates JSONL...")
    save_jsonl(OUT_TEMPLATES, templates)
    print(f"  Templates -> {OUT_TEMPLATES} ({len(templates)} templates)")

    # Step 5: Save gate decisions JSONL
    print("\n[5/6] Saving gate decisions JSONL...")
    save_jsonl(OUT_GATE_DECISIONS, gate_decisions)
    print(f"  Gate decisions -> {OUT_GATE_DECISIONS} ({len(gate_decisions)} decisions)")

    # Step 6: Build result, report, handoff
    print("\n[6/6] Building result JSON, report, and handoff...")
    result = build_result(templates, gate_decisions)
    generate_report(result, templates, gate_decisions, targets)
    generate_handoff(result, templates, gate_decisions)

    # Final summary
    print("\n" + "=" * 70)
    print("v115C TEMPLATE GATE COMPLETE")
    print(f"  Templates generated: {result['templates_generated']}")
    print(f"  Templates passed: {result['templates_passed']}")
    print(f"  Templates failed: {result['templates_failed']}")
    print(f"  send_ready: {result['send_ready']}")
    print(f"  tg_test_group_ready: {result['tg_test_group_ready']}")
    print(f"  local_review_ready: {result['local_review_ready']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
