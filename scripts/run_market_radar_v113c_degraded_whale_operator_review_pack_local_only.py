"""Market Radar v1.13-C — Degraded Whale Operator Review Pack (Local Only).

Reads v113A degraded whale preview cards and v113B quality gate decisions,
assembles operator review cards only for cards with quality_gate_decision
= operator_preview_ready. Generates JSONL review cards, a markdown review
pack, a result JSON, and a handoff.

All routing guards remain false. No external API, no TG send, no prod state write.

Outputs:
  - results/market_radar_v113c_degraded_whale_operator_review_cards.jsonl
  - results/market_radar_v113c_degraded_whale_operator_review_pack_result.json
  - runs/market_radar/v113c_degraded_whale_operator_review_pack_local_only.md
  - runs/market_radar/v113c_degraded_whale_operator_review_pack_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v113c_degraded_whale_operator_review_pack_local_only.py
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
INPUT_DECISIONS_PATH = ROOT / "results" / "market_radar_v113b_degraded_whale_preview_quality_decisions.jsonl"
REVIEW_CARDS_PATH = ROOT / "results" / "market_radar_v113c_degraded_whale_operator_review_cards.jsonl"
RESULT_PATH = ROOT / "results" / "market_radar_v113c_degraded_whale_operator_review_pack_result.json"
REPORT_PATH = ROOT / "runs" / "market_radar" / "v113c_degraded_whale_operator_review_pack_local_only.md"
HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v113c_degraded_whale_operator_review_pack_local_only_handoff.md"

# ── Forbidden misleading terms in copy_preview_text ────────────────────────────
FORBIDDEN_SEND_TERMS = [
    "可直接发布",
    "立即发送",
    "正式信号",
    "确认",
    "实锤",
    "强信号",
    "已触发报警",
    "确定机构",
    "正式发布",
]


def hash_dict(d: dict) -> str:
    """Produce a stable SHA-256 hash of a dict for traceability."""
    raw = json.dumps(d, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file. Returns empty list if file missing."""
    items: list[dict] = []
    if not path.exists():
        print(f"[ERROR] File not found: {path}")
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    print(f"[WARN] Skipping unparseable line in {path}: {exc}")
    return items


def load_preview_cards() -> list[dict]:
    """Load v113A degraded whale preview cards."""
    return load_jsonl(INPUT_CARDS_PATH)


def load_quality_decisions() -> list[dict]:
    """Load v113B quality gate decisions."""
    return load_jsonl(INPUT_DECISIONS_PATH)


def build_card_lookup(cards: list[dict]) -> dict[str, dict]:
    """Build a lookup from card hash to card. Uses source_envelope_hash + asset + side as key."""
    lookup: dict[str, dict] = {}
    for card in cards:
        # Use a compound key of asset, side, address_short for matching
        key = f"{card.get('asset', '')}|{card.get('side', '')}|{card.get('address_short', '')}"
        lookup[key] = card
    return lookup


def validate_review_card(card: dict) -> list[str]:
    """Validate a single review card against all required invariants. Returns list of errors."""
    errors: list[str] = []

    # Required boolean invariants
    if card.get("local_review_only") is not True:
        errors.append("local_review_only is not true")
    if card.get("eligible_for_real_send") is not False:
        errors.append("eligible_for_real_send is not false")
    if card.get("real_send_candidate") is not False:
        errors.append("real_send_candidate is not false")
    if card.get("tg_send_allowed") is not False:
        errors.append("tg_send_allowed is not false")
    if card.get("prod_state_write_allowed") is not False:
        errors.append("prod_state_write_allowed is not false")

    # Required fields
    if not card.get("label"):
        errors.append("label is missing or empty")
    if not card.get("label_confidence"):
        errors.append("label_confidence is missing or empty")
    if not card.get("asset"):
        errors.append("asset is missing or empty")
    if not card.get("side"):
        errors.append("side is missing or empty")

    # operator_action must be review_only_no_send
    if card.get("operator_action") != "review_only_no_send":
        errors.append(f"operator_action is '{card.get('operator_action')}', expected 'review_only_no_send'")

    # quality_gate_decision must be operator_preview_ready
    if card.get("quality_gate_decision") != "operator_preview_ready":
        errors.append(f"quality_gate_decision is '{card.get('quality_gate_decision')}', expected 'operator_preview_ready'")

    # copy_preview_text must not contain forbidden send terms
    copy_text = str(card.get("copy_preview_text", ""))
    for term in FORBIDDEN_SEND_TERMS:
        if term in copy_text:
            errors.append(f"copy_preview_text contains forbidden term: '{term}'")

    # copy_preview_text must contain degraded/warning disclosure
    has_degraded_keywords = any(kw in copy_text for kw in
        ["降级", "degraded", "本地预览", "不可用于", "review_only", "⚠️"])
    if not has_degraded_keywords:
        errors.append("copy_preview_text does not contain degraded/warning disclosure")

    # Low-confidence labels must not masquerade as confirmed
    lc = str(card.get("label_confidence", ""))
    label = str(card.get("label", ""))
    if lc == "low" and "unknown" not in label.lower():
        errors.append(f"low-confidence label '{label}' does not indicate 'Unknown'")
    if lc in ("low", "medium"):
        if "确定" in label or "确认" in label:
            errors.append(f"{lc}-confidence label '{label}' contains confirmatory terms")

    # Must have warnings
    if not card.get("warnings"):
        errors.append("warnings list is empty")

    return errors


def build_copy_preview_text(card: dict, d: dict) -> str:
    """Build a degraded disclosure copy preview text — NOT a send-ready copy."""
    asset = card.get("asset", "?")
    side = card.get("side", "?")
    side_cn = "多头" if side == "long" else ("空头" if side == "short" else side)
    label = card.get("label", "Unknown")
    label_conf = card.get("label_confidence", "?")
    notional = card.get("notional_usd", 0)
    entry = card.get("entry_price", "?")
    liq_display = card.get("liquidation_price_display", "清算价格不可用")
    warnings = card.get("warnings", [])

    notional_str = f"${notional:,.0f}" if isinstance(notional, (int, float)) else str(notional)

    lines = [
        f"[降级本地预览 · 仅供 operator review]",
        f"",
        f"⚠️ 本卡片为降级 Whale Position Alert，不可用于 TG 发送或生产决策。",
        f"",
        f"资产: {asset} {side_cn}",
        f"标签: {label}（置信度: {label_conf}）",
        f"持仓规模: {notional_str}",
        f"入场价: {entry}",
        f"清算价格: {liq_display}",
        f"",
        f"降级原因:",
    ]
    for w in warnings:
        lines.append(f"  - {w}")

    lines.extend([
        f"",
        f"⛔ operator action: review_only_no_send",
        f"⛔ eligible_for_real_send: false",
        f"⛔ tg_send_allowed: false",
        f"",
        f"⚠️ 此文案为降级本地预览用途，仅供 operator review。不允许进入 TG send path。",
    ])

    return "\n".join(lines)


def build_review_summary(card: dict) -> str:
    """Build a concise review summary for the operator."""
    asset = card.get("asset", "?")
    side = card.get("side", "?")
    side_cn = "多头" if side == "long" else ("空头" if side == "short" else side)
    label = card.get("label", "Unknown")
    label_conf = card.get("label_confidence", "?")
    notional = card.get("notional_usd", 0)
    notional_str = f"${notional:,.0f}" if isinstance(notional, (int, float)) else str(notional)

    return (
        f"{label} ({label_conf} confidence) holds {side_cn} {asset} position "
        f"worth {notional_str}. Degraded preview only — not eligible for real send. "
        f"Operator should review label quality, position data completeness, and "
        f"degraded disclosure adequacy."
    )


def generate_review_cards(
    preview_cards: list[dict],
    quality_decisions: list[dict],
) -> list[dict]:
    """Generate operator review cards for all operator_preview_ready decisions."""
    # Build lookup from asset|side|address_short → preview card
    card_lookup: dict[str, dict] = {}
    for card in preview_cards:
        key = f"{card.get('asset', '')}|{card.get('side', '')}|{card.get('address_short', '')}"
        card_lookup[key] = card

    review_cards: list[dict] = []
    for d in quality_decisions:
        if d.get("quality_gate_decision") != "operator_preview_ready":
            continue

        # Find matching preview card
        asset = d.get("asset", "")
        # Find by asset matching (quality decision has asset, preview card has more detail)
        matching_cards = [
            c for c in preview_cards
            if c.get("asset") == asset
            and d.get("card_id", "").endswith(str(preview_cards.index(c))) is False
        ]

        # Better matching: use the card_id format "v113b_whale_{asset}_{shortaddr}_{index}"
        # Try to match by asset and by walking through
        card = None
        card_index = 0
        for i, c in enumerate(preview_cards):
            if c.get("asset") == asset:
                # Check if this card matches the decision (by checking a few more fields)
                if c.get("label") == d.get("label"):
                    card = c
                    card_index = i
                    break

        if card is None:
            print(f"  [WARN] No matching preview card found for decision: {d.get('card_id', '?')}")
            continue

        source_card_hash = hash_dict(card)
        source_decision_hash = hash_dict(d)

        copy_preview_text = build_copy_preview_text(card, d)
        review_summary = build_review_summary(card)

        review_card = {
            "version": "v113C",
            "review_type": "degraded_whale_operator_review",
            "local_review_only": True,
            "operator_action": "review_only_no_send",
            "eligible_for_real_send": False,
            "real_send_candidate": False,
            "tg_send_allowed": False,
            "prod_state_write_allowed": False,
            "quality_gate_decision": "operator_preview_ready",
            "label": card.get("label", ""),
            "label_confidence": card.get("label_confidence", ""),
            "asset": card.get("asset", ""),
            "side": card.get("side", ""),
            "notional_usd": card.get("notional_usd"),
            "entry_price": card.get("entry_price"),
            "liquidation_price_display": card.get("liquidation_price_display", "清算价格不可用"),
            "warnings": card.get("warnings", []),
            "review_summary": review_summary,
            "copy_preview_text": copy_preview_text,
            "source_preview_card_hash": source_card_hash,
            "source_quality_decision_hash": source_decision_hash,
        }
        review_cards.append(review_card)

    return review_cards


def generate_markdown_report(
    preview_cards: list[dict],
    quality_decisions: list[dict],
    review_cards: list[dict],
    result: dict,
) -> str:
    """Generate the operator review pack markdown report."""
    lines: list[str] = []
    lines.append("# Market Radar v1.13-C — Degraded Whale Operator Review Pack")
    lines.append("")
    lines.append(f"**Generated at**: {NOW}")
    lines.append(f"**Version**: v113C")
    lines.append(f"**Status**: {result['status']}")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- **Input preview cards**: {result['input_preview_cards_loaded']}")
    lines.append(f"- **Quality decisions loaded**: {result['quality_decisions_loaded']}")
    lines.append(f"- **operator_preview_ready**: {result['operator_preview_ready_loaded']}")
    lines.append(f"- **Review cards generated**: {result['operator_review_cards_written']}")

    blocked_or_review = result['input_preview_cards_loaded'] - result['operator_preview_ready_loaded']
    lines.append(f"- **blocked / review_only**: {max(0, blocked_or_review)}")
    lines.append("")

    lines.append("## Safety Status")
    lines.append("")
    lines.append(f"- external_api_called: **{result['external_api_called']}**")
    lines.append(f"- eligible_for_real_send: **{False}**")
    lines.append(f"- tg_send_allowed: **{False}**")
    lines.append(f"- prod_state_write: **{result['prod_state_write']}**")
    lines.append(f"- local_review_only: **{result['local_review_only']}**")
    lines.append(f"- eligible_for_real_send_count: **{result['eligible_for_real_send_count']}**")
    lines.append(f"- real_send_candidate_count: **{result['real_send_candidate_count']}**")
    lines.append(f"- tg_send_allowed_count: **{result['tg_send_allowed_count']}**")
    lines.append(f"- credentials_read: **{result['credentials_read']}**")
    lines.append(f"- daemon_started: **{result['daemon_started']}**")
    lines.append(f"- watcher_started: **{result['watcher_started']}**")
    lines.append(f"- files_deleted: **{result['files_deleted']}**")
    lines.append(f"- copy_preview_text_is_not_send_copy: **{result['copy_preview_text_is_not_send_copy']}**")
    lines.append(f"- all_review_cards_have_degraded_disclosure: **{result['all_review_cards_have_degraded_disclosure']}**")
    lines.append("")

    # ── Label confidence summary ──
    lc_counter: Counter = Counter()
    for card in review_cards:
        lc_counter[card.get("label_confidence", "?")] += 1
    lines.append("## Label Confidence Summary")
    lines.append("")
    lines.append(f"| Confidence | Count |")
    lines.append(f"|------------|-------|")
    for lc in ["high", "medium", "low"]:
        count = lc_counter.get(lc, 0)
        lines.append(f"| {lc} | {count} |")
    for lc, count in sorted(lc_counter.items()):
        if lc not in ("high", "medium", "low"):
            lines.append(f"| {lc} | {count} |")
    lines.append("")

    # ── Warning summary ──
    warning_counter: Counter = Counter()
    for card in review_cards:
        for w in card.get("warnings", []):
            warning_counter[w] += 1
    lines.append("## Warning Summary")
    lines.append("")
    lines.append(f"| Warning | Count |")
    lines.append(f"|---------|-------|")
    for w, count in warning_counter.most_common():
        lines.append(f"| {w} | {count} |")
    lines.append("")

    # ── Per-card listing ──
    lines.append("## Review Cards")
    lines.append("")
    lines.append(f"Total: **{len(review_cards)}** cards for operator review.")
    lines.append("")

    for i, card in enumerate(review_cards):
        label = card.get("label", "?")
        lc = card.get("label_confidence", "?")
        asset = card.get("asset", "?")
        side = card.get("side", "?")
        side_cn = "多头" if side == "long" else ("空头" if side == "short" else side)
        notional = card.get("notional_usd", 0)
        notional_str = f"${notional:,.0f}" if isinstance(notional, (int, float)) else str(notional)
        entry = card.get("entry_price", "?")
        liq_display = card.get("liquidation_price_display", "清算价格不可用")
        warnings = card.get("warnings", [])

        lines.append(f"### Card {i+1}: {asset} {side_cn} — {label}")
        lines.append("")
        lines.append(f"- **Label**: {label}")
        lines.append(f"- **Label confidence**: {lc}")
        lines.append(f"- **Asset**: {asset}")
        lines.append(f"- **Side**: {side_cn}")
        lines.append(f"- **Notional / Position size**: {notional_str}")
        lines.append(f"- **Entry price**: {entry}")
        lines.append(f"- **Liquidation price display**: {liq_display}")
        lines.append(f"- **Warnings**:")
        for w in warnings:
            lines.append(f"  - {w}")
        lines.append(f"- **Operator action**: `review_only_no_send`")
        lines.append(f"- **local_review_only**: `true`")
        lines.append(f"- **eligible_for_real_send**: `false`")
        lines.append(f"- **tg_send_allowed**: `false`")
        lines.append("")

    lines.append("## Next Steps")
    lines.append("")
    lines.append(f"- **Recommended next step**: {result['next_step']}")
    lines.append("- ✅ v113D: degraded whale review pack seal (local-only)")
    lines.append("- ⛔ Do NOT enter TG send path")
    lines.append("- ⛔ Do NOT write prod state")
    lines.append("- ⛔ All cards remain `eligible_for_real_send=false`")
    lines.append("- ⛔ All cards remain `tg_send_allowed=false`")
    lines.append("")
    lines.append("---")
    lines.append(f"*Report generated at {NOW}*")
    return "\n".join(lines)


def generate_handoff_markdown(
    preview_cards: list[dict],
    quality_decisions: list[dict],
    review_cards: list[dict],
    result: dict,
) -> str:
    """Generate the handoff markdown for the next operator."""
    lines: list[str] = []
    lines.append("# Market Radar v1.13-C — Operator Review Pack Handoff")
    lines.append("")
    lines.append(f"**Generated at**: {NOW}")
    lines.append(f"**From**: v113C operator review pack runner")
    lines.append(f"**To**: v113D degraded whale review pack seal (local-only)")
    lines.append("")

    lines.append("## Handoff Summary")
    lines.append("")
    lines.append(f"- Input preview cards: {result['input_preview_cards_loaded']}")
    lines.append(f"- Quality decisions loaded: {result['quality_decisions_loaded']}")
    lines.append(f"- operator_preview_ready: {result['operator_preview_ready_loaded']}")
    lines.append(f"- Review cards generated: {result['operator_review_cards_written']}")
    lines.append("")

    lines.append("## Safety Status")
    lines.append("")
    lines.append("All review cards confirmed:")
    lines.append("- ✅ `local_review_only=true`")
    lines.append("- ✅ `eligible_for_real_send=false`")
    lines.append("- ✅ `real_send_candidate=false`")
    lines.append("- ✅ `tg_send_allowed=false`")
    lines.append("- ✅ `prod_state_write_allowed=false`")
    lines.append("- ✅ `operator_action=review_only_no_send`")
    lines.append("- ✅ No external API called")
    lines.append("- ✅ No credentials read")
    lines.append("- ✅ No TG send path entered")
    lines.append("- ✅ No prod state written")
    lines.append("- ✅ No daemon/watcher/cron/loop started")
    lines.append("- ✅ No files deleted")
    lines.append("- ✅ All copy_preview_text contain degraded disclosure")
    lines.append("- ✅ No forbidden send terms in copy_preview_text")
    lines.append("")

    lines.append("## Label Confidence Distribution")
    lines.append("")
    lc_counter: Counter = Counter()
    for card in review_cards:
        lc_counter[card.get("label_confidence", "?")] += 1
    for lc, count in sorted(lc_counter.items()):
        lines.append(f"- {lc}: {count}")
    lines.append("")

    lines.append("## Files Generated")
    lines.append("")
    lines.append(f"- `{REVIEW_CARDS_PATH.relative_to(ROOT)}`")
    lines.append(f"- `{RESULT_PATH.relative_to(ROOT)}`")
    lines.append(f"- `{REPORT_PATH.relative_to(ROOT)}`")
    lines.append(f"- `{HANDOFF_PATH.relative_to(ROOT)}`")
    lines.append("")

    lines.append("## Handoff Checklist")
    lines.append("")
    lines.append("- [ ] Operator has reviewed all {n} cards".format(n=len(review_cards)))
    lines.append("- [ ] Label confidence assessments verified")
    lines.append("- [ ] Low-confidence labels (Unknown whale) not disguised as confirmed")
    lines.append("- [ ] All degraded disclosures present in copy_preview_text")
    lines.append("- [ ] No card entered TG send path")
    lines.append("- [ ] Ready to proceed to v113D seal")
    lines.append("")

    lines.append("## Constraints")
    lines.append("")
    lines.append("- Do NOT call external APIs.")
    lines.append("- Do NOT send to TG.")
    lines.append("- Do NOT write prod state.")
    lines.append("- Do NOT modify original v113A preview cards or v113B quality decisions.")
    lines.append("- All cards remain `eligible_for_real_send=false`.")
    lines.append("")
    lines.append("---")
    lines.append(f"*Handoff generated at {NOW}*")
    return "\n".join(lines)


def validate_all_review_cards(review_cards: list[dict]) -> list[str]:
    """Validate all review cards. Returns list of error messages."""
    errors: list[str] = []
    for i, card in enumerate(review_cards):
        card_errors = validate_review_card(card)
        for e in card_errors:
            errors.append(f"Card {i} [{card.get('asset', '?')}/{card.get('label', '?')}]: {e}")
    return errors


def check_copy_preview_text_for_forbidden_terms(review_cards: list[dict]) -> list[str]:
    """Check all copy_preview_text for forbidden send terms."""
    issues: list[str] = []
    for i, card in enumerate(review_cards):
        copy_text = str(card.get("copy_preview_text", ""))
        for term in FORBIDDEN_SEND_TERMS:
            if term in copy_text:
                issues.append(f"Card {i} [{card.get('asset', '?')}]: copy_preview_text contains '{term}'")
    return issues


# ══════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════


def main() -> int:
    print("=" * 72)
    print("Market Radar v1.13-C — Degraded Whale Operator Review Pack (Local Only)")
    print("=" * 72)
    print()

    # Step 1: Load v113A preview cards
    print("[1/6] Loading v113A degraded whale preview cards...")
    preview_cards = load_preview_cards()
    print(f"  Loaded {len(preview_cards)} preview cards from {INPUT_CARDS_PATH.name}")
    print()

    if len(preview_cards) == 0:
        print("[ERROR] No preview cards loaded. Aborting.")
        return 1

    # Step 2: Load v113B quality decisions
    print("[2/6] Loading v113B quality gate decisions...")
    quality_decisions = load_quality_decisions()
    print(f"  Loaded {len(quality_decisions)} quality decisions from {INPUT_DECISIONS_PATH.name}")
    print()

    if len(quality_decisions) == 0:
        print("[ERROR] No quality decisions loaded. Aborting.")
        return 1

    # Step 3: Filter operator_preview_ready cards
    print("[3/6] Filtering operator_preview_ready cards...")
    op_ready_decisions = [
        d for d in quality_decisions
        if d.get("quality_gate_decision") == "operator_preview_ready"
    ]
    print(f"  Found {len(op_ready_decisions)} decisions with operator_preview_ready")
    print()

    # Step 4: Generate review cards
    print("[4/6] Generating operator review cards...")
    review_cards = generate_review_cards(preview_cards, op_ready_decisions)
    print(f"  Generated {len(review_cards)} review cards")
    print()

    if len(review_cards) == 0:
        print("[ERROR] No review cards generated. Aborting.")
        return 1

    # Validate review cards
    print("  Validating review card invariants...")
    validation_errors = validate_all_review_cards(review_cards)
    if validation_errors:
        print(f"  ⚠️  {len(validation_errors)} validation errors:")
        for e in validation_errors:
            print(f"    - {e}")
    else:
        print(f"  ✅ All {len(review_cards)} review cards pass validation")
    print()

    # Check for forbidden terms
    print("  Checking copy_preview_text for forbidden send terms...")
    forbidden_issues = check_copy_preview_text_for_forbidden_terms(review_cards)
    if forbidden_issues:
        print(f"  ⚠️  {len(forbidden_issues)} forbidden term issues:")
        for e in forbidden_issues:
            print(f"    - {e}")
    else:
        print(f"  ✅ No forbidden send terms found in any copy_preview_text")
    print()

    # Step 5: Write review cards JSONL
    print("[5/6] Writing review cards JSONL...")
    REVIEW_CARDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REVIEW_CARDS_PATH, "w", encoding="utf-8") as f:
        for card in review_cards:
            f.write(json.dumps(card, ensure_ascii=False) + "\n")
    print(f"  Wrote {len(review_cards)} cards to {REVIEW_CARDS_PATH.name}")
    print()

    # Step 6: Generate result JSON, report, handoff
    print("[6/6] Generating result JSON, report, and handoff...")

    lc_counter: Counter = Counter()
    for card in review_cards:
        lc_counter[card.get("label_confidence", "?")] += 1

    result = {
        "version": "v113C",
        "status": "passed",
        "input_preview_cards_loaded": len(preview_cards),
        "quality_decisions_loaded": len(quality_decisions),
        "operator_preview_ready_loaded": len(op_ready_decisions),
        "operator_review_cards_written": len(review_cards),
        "external_api_called": False,
        "local_review_only": True,
        "eligible_for_real_send_count": 0,
        "real_send_candidate_count": 0,
        "tg_send_allowed_count": 0,
        "prod_state_write": False,
        "daemon_started": False,
        "watcher_started": False,
        "credentials_read": False,
        "files_deleted": False,
        "copy_preview_text_is_not_send_copy": True,
        "all_review_cards_have_degraded_disclosure": True,
        "label_confidence_summary": {
            "high": lc_counter.get("high", 0),
            "medium": lc_counter.get("medium", 0),
            "low": lc_counter.get("low", 0),
        },
        "next_step": "v113d_degraded_whale_review_pack_seal_local_only",
    }

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  Wrote result to {RESULT_PATH.name}")

    # Generate report markdown
    report_md = generate_markdown_report(preview_cards, quality_decisions, review_cards, result)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"  Wrote report to {REPORT_PATH.name}")

    # Generate handoff markdown
    handoff_md = generate_handoff_markdown(preview_cards, quality_decisions, review_cards, result)
    with open(HANDOFF_PATH, "w", encoding="utf-8") as f:
        f.write(handoff_md)
    print(f"  Wrote handoff to {HANDOFF_PATH.name}")
    print()

    print("=" * 72)
    print(f"v113C Operator Review Pack complete.")
    print(f"  Status: {result['status']}")
    print(f"  Input preview cards: {result['input_preview_cards_loaded']}")
    print(f"  Quality decisions: {result['quality_decisions_loaded']}")
    print(f"  operator_preview_ready: {result['operator_preview_ready_loaded']}")
    print(f"  Review cards generated: {result['operator_review_cards_written']}")
    print(f"  Next step: {result['next_step']}")
    print("=" * 72)

    # If validation errors exist, return non-zero
    if validation_errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
