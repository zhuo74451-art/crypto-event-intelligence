"""Market Radar v1.13-B — Degraded Whale Preview Quality Gate (Local Only).

Reads v113A degraded whale preview cards and applies local quality gating
to classify each card as:
  - operator_preview_ready  : card is complete enough for operator review pack
  - review_only             : card needs wording fixes before operator review
  - blocked                 : card has safety or disclosure issues

Quality gates applied (all local, no external API):
  A. Safety routing gate    — routing guards must all be false
  B. Degraded disclosure gate — required warnings must be present
  C. Label confidence gate  — low/medium labels not disguised as confirmed
  D. Misleading wording gate — no forbidden terms in title/body
  E. Preview usability gate — required fields must be present

Outputs:
  - results/market_radar_v113b_degraded_whale_preview_quality_decisions.jsonl
  - results/market_radar_v113b_degraded_whale_preview_quality_gate_result.json
  - runs/market_radar/v113b_degraded_whale_preview_quality_gate_local_only.md
  - runs/market_radar/v113b_degraded_whale_preview_quality_gate_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v113b_degraded_whale_preview_quality_gate_local_only.py
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix Windows GBK encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat()

# ── Paths ──────────────────────────────────────────────────────────────────────
INPUT_CARDS_PATH = ROOT / "results" / "market_radar_v113a_degraded_whale_preview_cards.jsonl"
DECISIONS_PATH = ROOT / "results" / "market_radar_v113b_degraded_whale_preview_quality_decisions.jsonl"
RESULT_PATH = ROOT / "results" / "market_radar_v113b_degraded_whale_preview_quality_gate_result.json"
REPORT_PATH = ROOT / "runs" / "market_radar" / "v113b_degraded_whale_preview_quality_gate_local_only.md"
HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v113b_degraded_whale_preview_quality_gate_local_only_handoff.md"

# ── Forbidden misleading terms ─────────────────────────────────────────────────
FORBIDDEN_TERMS = [
    "确认",
    "实锤",
    "确定机构",
    "强信号",
    "立即发送",
    "可直接发布",
    "已触发报警",
    "正式信号",
]

# ── Required warning fragments for degraded disclosure ─────────────────────────
REQUIRED_WARNINGS = [
    "标签置信度不足",
    "单次快照，暂无法计算仓位变化",
    "使用本地观察时间，非 HyperLiquid 服务端时间",
]

# ── Required preview card fields for usability ─────────────────────────────────
REQUIRED_FIELDS = [
    "label",
    "asset",
    "side",
    "warnings",
]


def hash_card(card: dict) -> str:
    """Produce a stable hash of the card for traceability."""
    raw = json.dumps(card, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_preview_cards(path: Path) -> list[dict]:
    """Load v113A degraded whale preview cards from JSONL."""
    cards: list[dict] = []
    if not path.exists():
        print(f"[ERROR] Input cards file not found: {path}")
        return cards
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    cards.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    print(f"[WARN] Skipping unparseable line in {path}: {exc}")
    return cards


def validate_preconditions(cards: list[dict]) -> list[str]:
    """Validate that all cards satisfy v113A preconditions. Returns list of error messages."""
    errors: list[str] = []
    for i, card in enumerate(cards):
        cid = card.get("address_short", f"card_{i}")
        asset = card.get("asset", "?")
        if not card.get("local_preview_only"):
            errors.append(f"Card {i} [{cid}/{asset}]: local_preview_only is not true")
        if not card.get("degraded"):
            errors.append(f"Card {i} [{cid}/{asset}]: degraded is not true")
        if not card.get("mock_replay_only"):
            errors.append(f"Card {i} [{cid}/{asset}]: mock_replay_only is not true")
        if card.get("eligible_for_real_send"):
            errors.append(f"Card {i} [{cid}/{asset}]: eligible_for_real_send is true")
        if card.get("real_send_candidate"):
            errors.append(f"Card {i} [{cid}/{asset}]: real_send_candidate is true")
        if card.get("tg_send_allowed"):
            errors.append(f"Card {i} [{cid}/{asset}]: tg_send_allowed is true")
    return errors


# ══════════════════════════════════════════════════════════════════════════════════
# Gate functions — each returns (pass: bool, reasons: list[str])
# ══════════════════════════════════════════════════════════════════════════════════


def gate_safety_routing(card: dict) -> tuple[bool, list[str]]:
    """A. Safety routing gate — all routing guards must be false."""
    reasons: list[str] = []
    if not card.get("local_preview_only", False):
        reasons.append("safety_routing: local_preview_only is not true")
    if card.get("eligible_for_real_send", True):
        reasons.append("safety_routing: eligible_for_real_send is not false")
    if card.get("real_send_candidate", True):
        reasons.append("safety_routing: real_send_candidate is not false")
    if card.get("tg_send_allowed", True):
        reasons.append("safety_routing: tg_send_allowed is not false")
    if card.get("prod_state_write_allowed", True):
        reasons.append("safety_routing: prod_state_write_allowed is not false")
    return (len(reasons) == 0, reasons)


def gate_degraded_disclosure(card: dict) -> tuple[bool, list[str]]:
    """B. Degraded disclosure gate — required warnings must be present."""
    reasons: list[str] = []
    warnings = card.get("warnings", [])
    if not isinstance(warnings, list):
        reasons.append("degraded_disclosure: warnings is not a list")
        return (False, reasons)

    warnings_text = " | ".join(warnings)

    for req in REQUIRED_WARNINGS:
        if req not in warnings_text:
            reasons.append(f"degraded_disclosure: missing required warning '{req}'")

    # If liquidation_price is null, "清算价格不可用" must be present
    if card.get("liquidation_price") is None:
        if "清算价格不可用" not in warnings_text:
            reasons.append(
                "degraded_disclosure: liquidation_price is null "
                "but '清算价格不可用' warning is missing"
            )

    return (len(reasons) == 0, reasons)


def gate_label_confidence(card: dict) -> tuple[bool, list[str]]:
    """C. Label confidence gate — low/medium labels not disguised as confirmed."""
    reasons: list[str] = []
    label = str(card.get("label", ""))
    lc = str(card.get("label_confidence", ""))
    explanation = str(card.get("label_explanation", ""))

    # Must have label_confidence
    if not lc:
        reasons.append("label_confidence: label_confidence is missing or empty")
        return (False, reasons)

    # Must have label_explanation
    if not explanation:
        reasons.append("label_confidence: label_explanation is missing or empty")
        return (False, reasons)

    # Low/medium confidence labels must not be written as confirmed institutions
    if lc in ("low", "medium"):
        label_lower = label.lower()
        if "confirmed" in label_lower or "verified" in label_lower:
            reasons.append(
                f"label_confidence: {lc}-confidence label '{label}' "
                "contains 'confirmed'/'verified' claim"
            )

        # Explanation must not assert high-confidence (ignoring negation phrases)
        expl_lower = explanation.lower()
        # Remove negation contexts before checking for false high-confidence claims
        import re
        cleaned = re.sub(
            r"not\s+(a\s+)?high[\s-]?confidence",
            "",
            expl_lower,
        )
        if "high-confidence" in cleaned or "high confidence" in cleaned:
            reasons.append(
                "label_confidence: label_explanation incorrectly claims high-confidence"
            )

        # Low/medium labels must not use "确定" (confirmed) or similar
        if "确定" in label:
            reasons.append(
                f"label_confidence: {lc}-confidence label '{label}' uses '确定'"
            )

    # Low-confidence labels with "Unknown" must stay low
    if lc == "low" and "unknown" not in label.lower():
        reasons.append(
            f"label_confidence: low-confidence label '{label}' does not indicate 'Unknown'"
        )

    return (len(reasons) == 0, reasons)


def gate_misleading_wording(card: dict) -> tuple[bool, list[str]]:
    """D. Misleading wording gate — no forbidden terms in title/body."""
    reasons: list[str] = []
    title = str(card.get("title", ""))
    body = str(card.get("body", ""))
    combined = title + "\n" + body

    for term in FORBIDDEN_TERMS:
        if term in combined:
            reasons.append(f"misleading_wording: forbidden term '{term}' found")

    return (len(reasons) == 0, reasons)


def gate_preview_usability(card: dict) -> tuple[bool, list[str]]:
    """E. Preview usability gate — required fields must be present."""
    reasons: list[str] = []

    for field in REQUIRED_FIELDS:
        val = card.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            reasons.append(f"preview_usability: missing required field '{field}'")
        elif isinstance(val, list) and len(val) == 0:
            reasons.append(f"preview_usability: field '{field}' is an empty list")

    # Must have notional or position size indication
    if card.get("notional_usd") is None and card.get("position_size") is None:
        reasons.append("preview_usability: missing notional_usd or position_size")

    # Must have entry_price or alternative explanation
    if card.get("entry_price") is None:
        reasons.append("preview_usability: missing entry_price")

    # Must have source / degraded explanation
    if not card.get("degrade_reasons"):
        reasons.append("preview_usability: missing degrade_reasons")

    return (len(reasons) == 0, reasons)


# ══════════════════════════════════════════════════════════════════════════════════
# Decision logic
# ══════════════════════════════════════════════════════════════════════════════════


def decide_quality_gate(card: dict, card_index: int) -> dict:
    """Apply all quality gates and return a decision dict."""
    card_hash = hash_card(card)
    cid = card.get("address_short", f"card_{card_index}")
    asset = card.get("asset", "?")

    gates = {
        "safety_routing_gate": gate_safety_routing(card),
        "degraded_disclosure_gate": gate_degraded_disclosure(card),
        "label_confidence_gate": gate_label_confidence(card),
        "misleading_wording_gate": gate_misleading_wording(card),
        "preview_usability_gate": gate_preview_usability(card),
    }

    gate_results = {}
    all_blocking_reasons: list[str] = []
    all_review_notes: list[str] = []

    for gate_name, (passed, reasons) in gates.items():
        gate_results[gate_name] = "pass" if passed else "fail"
        if not passed:
            # Safety routing failure → always blocked
            # Degraded disclosure missing required warning → blocked
            # Label confidence misrepresentation → blocked
            if gate_name in ("safety_routing_gate", "degraded_disclosure_gate", "label_confidence_gate"):
                all_blocking_reasons.extend(reasons)
            elif gate_name == "misleading_wording_gate":
                # Misleading wording can be review_only or blocked
                all_blocking_reasons.extend(reasons)
            else:
                # Preview usability → missing fields → blocked
                all_blocking_reasons.extend(reasons)

    # Determine final decision
    safety_pass = gate_results["safety_routing_gate"] == "pass"
    disclosure_pass = gate_results["degraded_disclosure_gate"] == "pass"
    label_pass = gate_results["label_confidence_gate"] == "pass"
    wording_pass = gate_results["misleading_wording_gate"] == "pass"
    usability_pass = gate_results["preview_usability_gate"] == "pass"

    if not safety_pass or not disclosure_pass or not label_pass or not usability_pass:
        decision = "blocked"
    elif not wording_pass:
        # Misleading wording alone → review_only (can be fixed without data changes)
        decision = "review_only"
        all_review_notes.append(
            "misleading wording detected — must be corrected before operator review"
        )
    else:
        decision = "operator_preview_ready"

    return {
        "version": "v113B",
        "card_id": f"v113b_whale_{asset}_{cid}_{card_index}",
        "source_preview_card_hash": card_hash,
        "quality_gate_decision": decision,
        "eligible_for_real_send": False,
        "tg_send_allowed": False,
        "prod_state_write_allowed": False,
        "degraded": True,
        "mock_replay_only": True,
        "label_confidence": card.get("label_confidence", ""),
        "asset": asset,
        "label": card.get("label", ""),
        "gate_checks": gate_results,
        "blocking_reasons": all_blocking_reasons,
        "review_notes": all_review_notes,
    }


# ══════════════════════════════════════════════════════════════════════════════════
# Report generation
# ══════════════════════════════════════════════════════════════════════════════════


def generate_markdown_report(
    cards: list[dict],
    decisions: list[dict],
    result: dict,
) -> str:
    """Generate the quality gate report in markdown."""
    op_ready = result["operator_preview_ready_count"]
    review_only = result["review_only_count"]
    blocked = result["blocked_count"]
    total = len(decisions)

    # Blocking reasons distribution
    reason_counter: Counter = Counter()
    for d in decisions:
        for r in d["blocking_reasons"]:
            reason_counter[r] += 1

    # Label confidence distribution
    lc_counter: Counter = Counter()
    for d in decisions:
        lc_counter[d.get("label_confidence", "?")] += 1

    # Gate failure distribution
    gate_fail_counter: Counter = Counter()
    for d in decisions:
        for gate, status in d["gate_checks"].items():
            if status == "fail":
                gate_fail_counter[gate] += 1

    # Warning coverage
    warning_counter: Counter = Counter()
    for card in cards:
        for w in card.get("warnings", []):
            warning_counter[w] += 1

    # Missing warning cases
    missing_liq_warning = 0
    for card in cards:
        if card.get("liquidation_price") is None:
            warnings_text = " | ".join(card.get("warnings", []))
            if "清算价格不可用" not in warnings_text:
                missing_liq_warning += 1

    lines: list[str] = []
    lines.append("# Market Radar v1.13-B — Degraded Whale Preview Quality Gate Report")
    lines.append("")
    lines.append(f"**Generated at**: {NOW}")
    lines.append(f"**Version**: v113B")
    lines.append(f"**Status**: {result['status']}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Input preview cards loaded**: {result['input_preview_cards_loaded']}")
    lines.append(f"- **Quality decisions generated**: {result['quality_decisions_written']}")
    lines.append(f"- **operator_preview_ready**: {op_ready}")
    lines.append(f"- **review_only**: {review_only}")
    lines.append(f"- **blocked**: {blocked}")
    lines.append("")
    lines.append("## Safety Invariants")
    lines.append("")
    lines.append(f"- eligible_for_real_send_count: **{result['eligible_for_real_send_count']}**")
    lines.append(f"- real_send_candidate_count: **{result['real_send_candidate_count']}**")
    lines.append(f"- tg_send_allowed_count: **{result['tg_send_allowed_count']}**")
    lines.append(f"- prod_state_write: **{result['prod_state_write']}**")
    lines.append(f"- external_api_called: **{result['external_api_called']}**")
    lines.append(f"- credentials_read: **{result['credentials_read']}**")
    lines.append(f"- daemon_started: **{result['daemon_started']}**")
    lines.append(f"- watcher_started: **{result['watcher_started']}**")
    lines.append(f"- files_deleted: **{result['files_deleted']}**")
    lines.append("")
    lines.append("## Decision Distribution")
    lines.append("")
    lines.append(f"| Decision | Count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| operator_preview_ready | {op_ready} |")
    lines.append(f"| review_only | {review_only} |")
    lines.append(f"| blocked | {blocked} |")
    lines.append(f"| **Total** | **{total}** |")
    lines.append("")
    lines.append("## Label Confidence Distribution")
    lines.append("")
    lines.append(f"| Confidence | Count |")
    lines.append(f"|------------|-------|")
    for lc, count in sorted(lc_counter.items()):
        lines.append(f"| {lc} | {count} |")
    lines.append("")
    lines.append("## Gate Check Results")
    lines.append("")
    lines.append(f"| Gate | Pass | Fail |")
    lines.append(f"|------|------|------|")
    for gate_name in ["safety_routing_gate", "degraded_disclosure_gate", "label_confidence_gate", "misleading_wording_gate", "preview_usability_gate"]:
        failed = gate_fail_counter.get(gate_name, 0)
        passed = total - failed
        lines.append(f"| {gate_name} | {passed} | {failed} |")
    lines.append("")
    lines.append("## Warning Distribution")
    lines.append("")
    lines.append(f"| Warning | Count |")
    lines.append(f"|---------|-------|")
    for w, count in warning_counter.most_common():
        lines.append(f"| {w} | {count} |")
    lines.append("")
    lines.append("## Blocking Reasons Distribution")
    lines.append("")
    if reason_counter:
        lines.append(f"| Reason | Count |")
        lines.append(f"|--------|-------|")
        for reason, count in reason_counter.most_common():
            lines.append(f"| {reason} | {count} |")
    else:
        lines.append("No blocking reasons — all cards passed quality gates.")
    lines.append("")
    lines.append("## Per-Card Decision Details")
    lines.append("")
    for i, d in enumerate(decisions):
        lines.append(f"### Card {i}: {d['asset']} — {d['label']}")
        lines.append(f"- **Decision**: `{d['quality_gate_decision']}`")
        lines.append(f"- **Label confidence**: `{d['label_confidence']}`")
        lines.append(f"- **Gate checks**:")
        for gate, status in d["gate_checks"].items():
            icon = "✅" if status == "pass" else "❌"
            lines.append(f"  - {icon} {gate}: {status}")
        if d["blocking_reasons"]:
            lines.append(f"- **Blocking reasons**:")
            for r in d["blocking_reasons"]:
                lines.append(f"  - {r}")
        if d["review_notes"]:
            lines.append(f"- **Review notes**:")
            for r in d["review_notes"]:
                lines.append(f"  - {r}")
        lines.append("")
    lines.append("## Missing Warning Analysis")
    lines.append("")
    lines.append(f"- Cards with null liquidation_price: {sum(1 for c in cards if c.get('liquidation_price') is None)}")
    lines.append(f"- Of those, missing '清算价格不可用' warning: {missing_liq_warning}")
    lines.append(f"- Cards with delta unavailable: {sum(1 for c in cards if 'unavailable' in str(c.get('delta_status', '')))}")
    lines.append(f"- Cards with local timestamp: {sum(1 for c in cards if 'local' in str(c.get('timestamp_status', '')))}")
    lines.append("")
    lines.append("## Eligibility Check Summary")
    lines.append("")
    lines.append(f"- all_degraded_disclosures_checked: **{result['all_degraded_disclosures_checked']}**")
    lines.append(f"- label_confidence_checked: **{result['label_confidence_checked']}**")
    lines.append(f"- misleading_wording_checked: **{result['misleading_wording_checked']}**")
    lines.append("")
    lines.append("## Next Steps")
    lines.append("")
    lines.append(f"- **Recommended next step**: {result['next_step']}")
    if op_ready > 0:
        lines.append("- ✅ `operator_preview_ready_count > 0`: proceed to v113C degraded whale operator review pack (local-only)")
    if blocked > 0:
        lines.append("- ⚠️ `blocked_count > 0`: repair preview wording first, but never enter TG send path")
    if review_only > 0:
        lines.append("- 📝 `review_only_count > 0`: correct misleading wording before operator review")
    lines.append("")
    lines.append("---")
    lines.append(f"*Report generated at {NOW}*")
    return "\n".join(lines)


def generate_handoff_markdown(
    cards: list[dict],
    decisions: list[dict],
    result: dict,
) -> str:
    """Generate the handoff markdown for the next operator."""
    lines: list[str] = []
    lines.append("# Market Radar v1.13-B — Handoff")
    lines.append("")
    lines.append(f"**Generated at**: {NOW}")
    lines.append(f"**From**: v113B quality gate runner")
    lines.append(f"**To**: v113C operator review pack or wording repair")
    lines.append("")
    lines.append("## Handoff Summary")
    lines.append("")
    lines.append(f"- Input preview cards: {result['input_preview_cards_loaded']}")
    lines.append(f"- Quality decisions written: {result['quality_decisions_written']}")
    lines.append(f"- operator_preview_ready: {result['operator_preview_ready_count']}")
    lines.append(f"- review_only: {result['review_only_count']}")
    lines.append(f"- blocked: {result['blocked_count']}")
    lines.append("")
    lines.append("## Safety Status")
    lines.append("")
    lines.append("All cards confirmed:")
    lines.append("- ✅ `eligible_for_real_send=false`")
    lines.append("- ✅ `tg_send_allowed=false`")
    lines.append("- ✅ `prod_state_write=false`")
    lines.append("- ✅ No external API called")
    lines.append("- ✅ No credentials read")
    lines.append("- ✅ No TG send path entered")
    lines.append("- ✅ No prod state written")
    lines.append("")
    lines.append("## Handoff Actions Required")
    lines.append("")

    op_ready = result["operator_preview_ready_count"]
    blocked = result["blocked_count"]
    review_only = result["review_only_count"]

    if op_ready > 0:
        lines.append(f"### 1. Operator Review Pack (v113C)")
        lines.append(f"")
        lines.append(f"{op_ready} cards are `operator_preview_ready`.")
        lines.append(f"Proceed to v113C: assemble degraded whale operator review pack (local only).")
        lines.append(f"These cards can be bundled for manual operator review.")
        lines.append(f"DO NOT send to TG — they are still `eligible_for_real_send=false`.")
        lines.append("")

    if review_only > 0:
        lines.append(f"### 2. Wording Review ({review_only} cards)")
        lines.append(f"")
        lines.append(f"{review_only} cards have misleading wording that must be corrected.")
        lines.append(f"Fix wording before including in operator review pack.")
        lines.append("")

    if blocked > 0:
        lines.append(f"### 3. Blocked Cards ({blocked} cards)")
        lines.append(f"")
        lines.append(f"{blocked} cards are blocked. Reasons:")
        reason_counter: Counter = Counter()
        for d in decisions:
            if d["quality_gate_decision"] == "blocked":
                for r in d["blocking_reasons"]:
                    reason_counter[r] += 1
        for reason, count in reason_counter.most_common():
            lines.append(f"  - {reason}: {count} card(s)")
        lines.append(f"")
        lines.append(f"These must be repaired before they can enter operator review.")
        lines.append("")

    lines.append("## Files Generated")
    lines.append("")
    lines.append(f"- `{DECISIONS_PATH.relative_to(ROOT)}`")
    lines.append(f"- `{RESULT_PATH.relative_to(ROOT)}`")
    lines.append(f"- `{REPORT_PATH.relative_to(ROOT)}`")
    lines.append(f"- `{HANDOFF_PATH.relative_to(ROOT)}`")
    lines.append("")
    lines.append("## Constraints")
    lines.append("")
    lines.append("- Do NOT call external APIs.")
    lines.append("- Do NOT send to TG.")
    lines.append("- Do NOT write prod state.")
    lines.append("- Do NOT modify original v113A preview cards.")
    lines.append("- All decisions remain `eligible_for_real_send=false`.")
    lines.append("")
    lines.append("---")
    lines.append(f"*Handoff generated at {NOW}*")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════


def main() -> int:
    print("=" * 72)
    print("Market Radar v1.13-B — Degraded Whale Preview Quality Gate (Local Only)")
    print("=" * 72)
    print()

    # Step 1: Load preview cards
    print("[1/5] Loading v113A degraded whale preview cards...")
    cards = load_preview_cards(INPUT_CARDS_PATH)
    print(f"  Loaded {len(cards)} preview cards from {INPUT_CARDS_PATH.name}")
    print()

    if len(cards) == 0:
        print("[ERROR] No preview cards loaded. Aborting.")
        return 1

    # Step 2: Validate preconditions
    print("[2/5] Validating preconditions...")
    precondition_errors = validate_preconditions(cards)
    if precondition_errors:
        print(f"  ⚠️  {len(precondition_errors)} precondition errors found:")
        for e in precondition_errors:
            print(f"    - {e}")
    else:
        print(f"  ✅ All {len(cards)} cards satisfy v113A preconditions")
    print()

    # Step 3: Apply quality gates
    print("[3/5] Applying quality gates to each card...")
    decisions: list[dict] = []
    for i, card in enumerate(cards):
        decision = decide_quality_gate(card, i)
        decisions.append(decision)
        gate_status = decision["quality_gate_decision"]
        print(f"  Card {i}: {card['asset']} {card['side']} [{card.get('label', '?')}] → {gate_status}")

    op_ready = sum(1 for d in decisions if d["quality_gate_decision"] == "operator_preview_ready")
    review_only = sum(1 for d in decisions if d["quality_gate_decision"] == "review_only")
    blocked = sum(1 for d in decisions if d["quality_gate_decision"] == "blocked")
    print(f"  Summary: {op_ready} operator_preview_ready, {review_only} review_only, {blocked} blocked")
    print()

    # Step 4: Write decisions JSONL
    print("[4/5] Writing quality decisions...")
    DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISIONS_PATH, "w", encoding="utf-8") as f:
        for d in decisions:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"  Wrote {len(decisions)} decisions to {DECISIONS_PATH.name}")
    print()

    # Step 5: Generate result JSON
    print("[5/5] Generating result JSON, report, and handoff...")

    # Determine status
    all_passed = blocked == 0 and review_only == 0
    has_ready = op_ready > 0

    result = {
        "version": "v113B",
        "status": "passed" if all_passed else ("partial" if has_ready else "failed"),
        "input_preview_cards_loaded": len(cards),
        "quality_decisions_written": len(decisions),
        "operator_preview_ready_count": op_ready,
        "review_only_count": review_only,
        "blocked_count": blocked,
        "external_api_called": False,
        "local_quality_gate_only": True,
        "eligible_for_real_send_count": 0,
        "real_send_candidate_count": 0,
        "tg_send_allowed_count": 0,
        "prod_state_write": False,
        "daemon_started": False,
        "watcher_started": False,
        "credentials_read": False,
        "files_deleted": False,
        "all_degraded_disclosures_checked": True,
        "label_confidence_checked": True,
        "misleading_wording_checked": True,
        "precondition_errors": len(precondition_errors),
        "next_step": "v113c_degraded_whale_operator_review_pack_local_only",
        "generated_at": NOW,
    }

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  Wrote result to {RESULT_PATH.name}")

    # Generate report markdown
    report_md = generate_markdown_report(cards, decisions, result)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"  Wrote report to {REPORT_PATH.name}")

    # Generate handoff markdown
    handoff_md = generate_handoff_markdown(cards, decisions, result)
    with open(HANDOFF_PATH, "w", encoding="utf-8") as f:
        f.write(handoff_md)
    print(f"  Wrote handoff to {HANDOFF_PATH.name}")
    print()

    print("=" * 72)
    print(f"v113B Quality Gate complete.")
    print(f"  Status: {result['status']}")
    print(f"  operator_preview_ready: {op_ready}")
    print(f"  review_only: {review_only}")
    print(f"  blocked: {blocked}")
    print(f"  Next step: {result['next_step']}")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    sys.exit(main())
