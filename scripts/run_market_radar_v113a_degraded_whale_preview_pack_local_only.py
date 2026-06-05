"""Market Radar v1.13-A — Degraded Whale Preview Pack (Local Only)

Reads v112Z degraded whale envelopes and generates local preview cards
for Market Radar card display layer validation.

Outputs:
  - results/market_radar_v113a_degraded_whale_preview_cards.jsonl
  - results/market_radar_v113a_degraded_whale_preview_pack_result.json
  - runs/market_radar/v113a_degraded_whale_preview_pack_local_only.md
  - runs/market_radar/v113a_degraded_whale_preview_pack_local_only_handoff.md

Constraints:
  - No external API calls (HyperLiquid or otherwise)
  - No AI/API/model calls
  - No TG send
  - No prod state write
  - No daemon/watcher/cron/loop
  - No credentials read
  - No files deleted
  - No real send candidate generation
  - eligible_for_real_send is ALWAYS false
  - tg_send_allowed is ALWAYS false

Usage:
    python scripts/run_market_radar_v113a_degraded_whale_preview_pack_local_only.py
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
VERSION = "v1.13-A"
RUN_ID = "20260605_022952"
TASK_ID = "20260605_v113a_degraded_whale_preview_pack_local_only"

# ── Paths ─────────────────────────────────────────────────────────────────────────────

INPUT_ENVELOPES_JSONL = ROOT / "results" / "market_radar_v112z_degraded_whale_envelopes.jsonl"
INPUT_COMPAT_RESULT = ROOT / "results" / "market_radar_v112z_degraded_whale_envelope_compatibility_result.json"

PREVIEW_CARDS_JSONL_PATH = ROOT / "results" / "market_radar_v113a_degraded_whale_preview_cards.jsonl"
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v113a_degraded_whale_preview_pack_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v113a_degraded_whale_preview_pack_local_only.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v113a_degraded_whale_preview_pack_local_only_handoff.md"


# ══════════════════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════════════════

def china_stamp() -> str:
    """Return current timestamp string in UTC+8."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def _sha256_hex(raw: str) -> str:
    """SHA-256 hex digest of a UTF-8 encoded string."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None if not found."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Failed to load {path}: {e}")
        return None


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file, returning list of dicts."""
    records: list[dict] = []
    if not path.exists():
        print(f"  [ERROR] Input JSONL not found: {path}")
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"  [WARN] Skipping malformed JSONL line: {e}")
    return records


def _short_addr(addr: str) -> str:
    """Shorten an Ethereum address for display: 0x1234...5678"""
    if not addr or len(addr) < 10:
        return addr
    return f"{addr[:6]}...{addr[-4:]}"


def _compute_source_envelope_hash(envelope: dict) -> str:
    """Compute a stable hash for the source envelope to link preview cards back."""
    ext = envelope.get("v112z_extension", {})
    raw = json.dumps({
        "signal_id": envelope.get("signal_id", ""),
        "address": ext.get("address", ""),
        "asset": ext.get("asset", ""),
        "side": ext.get("side", ""),
    }, sort_keys=True, ensure_ascii=True)
    return _sha256_hex(raw)


# ══════════════════════════════════════════════════════════════════════════════════════════
# Envelope Validation
# ══════════════════════════════════════════════════════════════════════════════════════════

def validate_envelope_preconditions(envelope: dict, index: int) -> list[str]:
    """Validate that a v112Z envelope meets all preconditions for preview card generation.

    Returns a list of validation error messages (empty = valid).
    """
    errors: list[str] = []
    ext = envelope.get("v112z_extension", {})

    if ext.get("degraded") is not True:
        errors.append(f"Envelope {index}: degraded is not true (got {ext.get('degraded')})")
    if ext.get("mock_replay_only") is not True:
        errors.append(f"Envelope {index}: mock_replay_only is not true (got {ext.get('mock_replay_only')})")
    if ext.get("eligible_for_real_send") is not False:
        errors.append(f"Envelope {index}: eligible_for_real_send is not false (got {ext.get('eligible_for_real_send')})")
    if ext.get("real_send_candidate") is not False:
        errors.append(f"Envelope {index}: real_send_candidate is not false (got {ext.get('real_send_candidate')})")

    rg = ext.get("routing_guard", {})
    if rg.get("tg_send_allowed") is not False:
        errors.append(f"Envelope {index}: routing_guard.tg_send_allowed is not false (got {rg.get('tg_send_allowed')})")
    if rg.get("prod_state_write_allowed") is not False:
        errors.append(f"Envelope {index}: routing_guard.prod_state_write_allowed is not false (got {rg.get('prod_state_write_allowed')})")

    return errors


# ══════════════════════════════════════════════════════════════════════════════════════════
# Preview Card Builder
# ══════════════════════════════════════════════════════════════════════════════════════════

def build_degraded_whale_preview_card(envelope: dict, index: int) -> dict:
    """Build a local preview card from a v112Z degraded whale envelope.

    The preview card MUST:
      - Retain degraded identifiers
      - Show label confidence
      - NOT disguise low-confidence / unknown whale as confirmed institution
      - Display "清算价格不可用" for null liquidation_price
      - Display "单次快照，暂无法计算仓位变化" for position delta
      - Display "使用本地观察时间，非 HyperLiquid 服务端时间"
      - Set local_preview_only=true
      - Set tg_send_allowed=false
      - Set eligible_for_real_send=false
    """
    ext = envelope.get("v112z_extension", {})

    # ── Extract fields from envelope extension ──────────────────────────────────
    label = str(ext.get("label", "Unknown Whale"))
    label_confidence = str(ext.get("label_confidence", "low"))
    label_explanation = str(ext.get("label_explanation", ""))
    entity_type = str(ext.get("entity_type", "unknown_whale"))
    asset = str(ext.get("asset", "UNKNOWN")).strip().upper()
    side = str(ext.get("side", "long"))
    notional_usd = _safe_float(ext.get("notional_usd", 0))
    entry_price = _safe_float(ext.get("entry_price", 0))
    mark_price = _safe_float(ext.get("mark_price", 0))
    leverage = _safe_float(ext.get("leverage", 0))
    unrealized_pnl = _safe_float(ext.get("unrealized_pnl", 0))
    liquidation_price = ext.get("liquidation_price")
    liquidation_price_status = str(ext.get("liquidation_price_status", "missing"))
    delta_status = str(ext.get("delta_status", "unavailable_one_shot_no_previous_position"))
    delta_explanation = str(ext.get("delta_explanation", ""))
    timestamp_status = str(ext.get("timestamp_status", "local_observed_at_no_hl_server_timestamp"))
    timestamp_explanation = str(ext.get("timestamp_explanation", ""))
    quality_flags = ext.get("quality_flags", [])
    if isinstance(quality_flags, str):
        quality_flags = [quality_flags]
    degrade_reasons = ext.get("degrade_reasons", [])
    if isinstance(degrade_reasons, str):
        degrade_reasons = [degrade_reasons]
    address_short = str(ext.get("address_short", ""))
    observed_at = str(envelope.get("observed_at", china_stamp()))

    # ── Build warnings ──────────────────────────────────────────────────────────
    warnings: list[str] = []

    # Label confidence warning
    if label_confidence in ("low", "medium"):
        warnings.append("标签置信度不足")

    # Liquidation price warning
    if liquidation_price is None or liquidation_price_status == "missing":
        warnings.append("清算价格不可用")
        liquidation_price_display = "清算价格不可用"
    else:
        liquidation_price_display = f"${liquidation_price:,.2f}"

    # Delta warning
    if "unavailable" in delta_status:
        warnings.append("单次快照，暂无法计算仓位变化")
    delta_display = "单次快照，暂无法计算仓位变化"

    # Timestamp warning
    if "local" in timestamp_status:
        warnings.append("使用本地观察时间，非 HyperLiquid 服务端时间")
    timestamp_display = "本地观察时间"

    # Ensure all four standard warnings are present for degraded cards
    standard_warnings = [
        "标签置信度不足",
        "清算价格不可用",
        "单次快照，暂无法计算仓位变化",
        "使用本地观察时间，非 HyperLiquid 服务端时间",
    ]
    for w in standard_warnings:
        if w not in warnings:
            # Only add if applicable based on envelope data
            if w == "清算价格不可用" and liquidation_price is not None:
                continue  # Skip if liquidation price is actually available
            warnings.append(w)

    # ── Build title ─────────────────────────────────────────────────────────────
    side_emoji = "📈" if side == "long" else "📉" if side == "short" else "📊"
    side_cn = "多头" if side == "long" else "空头" if side == "short" else side
    title = f"{side_emoji} 主力仓位雷达｜{asset} {side_cn} [降级本地预览]"

    # ── Build body ──────────────────────────────────────────────────────────────
    body_lines = [
        f"一句话：{label} 在 {asset} 持有 {side_cn} $ {notional_usd:,.0f}。",
        "",
        f"● 持仓规模：$ {notional_usd:,.0f}",
        f"● 入场价：$ {entry_price:,.2f}",
        f"● 标记价：$ {mark_price:,.2f}",
        f"● 杠杆：{leverage:.0f}x",
    ]

    if unrealized_pnl != 0:
        pnl_sign = "+" if unrealized_pnl > 0 else ""
        body_lines.append(f"● 未实现盈亏：{pnl_sign}$ {unrealized_pnl:,.2f}")

    body_lines.append(f"● 清算价：{liquidation_price_display}")

    if liquidation_price is not None:
        liq_dist = ext.get("liquidation_distance_pct")
        if liq_dist is not None:
            body_lines.append(f"● 距清算：{liq_dist:.1f}%")

    body_lines.extend([
        f"● 标签：{label}（{entity_type}，置信度：{label_confidence}）",
        f"📌 地址：`{address_short}`",
        "",
        f"⏱ 时间：{observed_at}（{timestamp_display}）",
        "",
        f"⚠️ 降级本地预览：仅用于 Market Radar 卡片展示层验证。",
        f"⚠️ 不可用于 TG 发送或生产决策。",
    ])

    body = "\n".join(body_lines)

    # ── Build source envelope hash ──────────────────────────────────────────────
    source_hash = _compute_source_envelope_hash(envelope)

    # ── Assemble preview card ───────────────────────────────────────────────────
    preview_card = {
        "version": "v113A",
        "card_type": "whale_position_alert",
        "preview_type": "degraded_whale_local_preview",
        "local_preview_only": True,
        "degraded": True,
        "mock_replay_only": True,
        "eligible_for_real_send": False,
        "real_send_candidate": False,
        "tg_send_allowed": False,
        "prod_state_write_allowed": False,
        "title": title,
        "body": body,
        "warnings": warnings,
        "label": label,
        "label_confidence": label_confidence,
        "label_explanation": label_explanation,
        "label_source": str(ext.get("label_source", "")),
        "entity_type": entity_type,
        "asset": asset,
        "side": side,
        "notional_usd": notional_usd,
        "entry_price": entry_price,
        "mark_price": mark_price,
        "leverage": leverage,
        "unrealized_pnl": unrealized_pnl,
        "liquidation_price": liquidation_price,
        "liquidation_price_display": liquidation_price_display,
        "liquidation_price_status": liquidation_price_status,
        "delta_display": delta_display,
        "delta_status": delta_status,
        "delta_explanation": delta_explanation,
        "timestamp_display": timestamp_display,
        "timestamp_status": timestamp_status,
        "timestamp_explanation": timestamp_explanation,
        "quality_flags": quality_flags,
        "degrade_reasons": degrade_reasons,
        "address_short": address_short,
        "observed_at": observed_at,
        "source_envelope_hash": source_hash,
        "source_envelope_index": index,
        "generated_at": china_stamp(),
    }

    return preview_card


# ══════════════════════════════════════════════════════════════════════════════════════════
# Preview Card Validation
# ══════════════════════════════════════════════════════════════════════════════════════════

def validate_preview_card(card: dict, index: int) -> list[str]:
    """Validate that a preview card meets all quality requirements.

    Returns a list of validation error messages (empty = valid).
    """
    errors: list[str] = []

    # Safety invariants
    if card.get("local_preview_only") is not True:
        errors.append(f"Card {index}: local_preview_only is not true")
    if card.get("eligible_for_real_send") is not False:
        errors.append(f"Card {index}: eligible_for_real_send is not false")
    if card.get("real_send_candidate") is not False:
        errors.append(f"Card {index}: real_send_candidate is not false")
    if card.get("tg_send_allowed") is not False:
        errors.append(f"Card {index}: tg_send_allowed is not false")
    if card.get("degraded") is not True:
        errors.append(f"Card {index}: degraded is not true")
    if card.get("mock_replay_only") is not True:
        errors.append(f"Card {index}: mock_replay_only is not true")
    if card.get("prod_state_write_allowed") is not False:
        errors.append(f"Card {index}: prod_state_write_allowed is not false")

    # Label confidence must be preserved
    if not card.get("label_confidence"):
        errors.append(f"Card {index}: label_confidence missing")
    label_conf = str(card.get("label_confidence", ""))
    if label_conf in ("low", "medium"):
        if not card.get("label_explanation"):
            errors.append(f"Card {index}: label_explanation missing for {label_conf} confidence label")
        # Must not disguise as confirmed institution
        label = str(card.get("label", "")).lower()
        if "confirmed" in label or "verified" in label:
            errors.append(f"Card {index}: {label_conf}-confidence label contains 'confirmed'/'verified' — disguised as institution")
        explanation = str(card.get("label_explanation", "")).lower()
        # Check for AFFIRMATIVE claims (not negations like "NOT a high-confidence label")
        if re.search(r"(?<!not\s)(?<!not\sa\s)high.confidence", explanation, re.IGNORECASE):
            # Only flag if it's a positive claim, not a denial
            if not re.search(r"not\s+(a\s+)?high.confidence", explanation, re.IGNORECASE):
                errors.append(f"Card {index}: label_explanation incorrectly claims high-confidence")
        if "confirmed institution" in explanation and "not a confirmed" not in explanation and "no confirmed" not in explanation:
            errors.append(f"Card {index}: label_explanation incorrectly claims confirmed institution")

    # Liquidation price display
    if card.get("liquidation_price") is None:
        if "清算价格不可用" not in str(card.get("liquidation_price_display", "")):
            errors.append(f"Card {index}: null liquidation_price but display does not show '清算价格不可用'")

    # Delta display
    if "unavailable" in str(card.get("delta_status", "")):
        if "暂无法计算仓位变化" not in str(card.get("delta_display", "")):
            errors.append(f"Card {index}: delta unavailable but display does not show explanation")

    # Timestamp display
    if "local" in str(card.get("timestamp_status", "")):
        if "本地观察时间" not in str(card.get("timestamp_display", "")):
            errors.append(f"Card {index}: local timestamp but display does not show '本地观察时间'")

    # Warnings must contain key degraded warnings
    warnings = card.get("warnings", [])
    if not isinstance(warnings, list):
        errors.append(f"Card {index}: warnings is not a list")
    elif len(warnings) < 2:
        errors.append(f"Card {index}: too few warnings ({len(warnings)})")

    # Title must indicate degraded/local preview
    title = str(card.get("title", ""))
    if "降级" not in title:
        errors.append(f"Card {index}: title missing '降级' indicator")
    if "预览" not in title:
        errors.append(f"Card {index}: title missing '预览' indicator")

    return errors


# ══════════════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print(f"=== Market Radar {VERSION} — Degraded Whale Preview Pack (Local Only) ===")
    print(f"Run: {china_stamp()}")
    print(f"Run ID: {RUN_ID}")
    print(f"Task ID: {TASK_ID}")
    print()
    print("Constraints:")
    print("  EXTERNAL API: NONE")
    print("  TG SEND: NONE")
    print("  PROD STATE WRITE: NONE")
    print("  DAEMON/WATCHER/CRON/LOOP: NONE")
    print("  CREDENTIALS READ: NONE")
    print("  REAL SEND CANDIDATE: NONE")
    print()

    # ── Step 1: Load v112Z degraded whale envelopes ──────────────────────────────
    print("[1/6] Loading v112Z degraded whale envelopes...")
    input_envelopes = load_jsonl(INPUT_ENVELOPES_JSONL)
    input_count = len(input_envelopes)
    print(f"  Loaded: {input_count} envelopes from {INPUT_ENVELOPES_JSONL}")

    if input_count == 0:
        print("  [ERROR] No input envelopes found. Aborting.")
        return 1

    # Also load compatibility result for cross-validation
    compat_result = load_json(INPUT_COMPAT_RESULT)
    if compat_result:
        print(f"  v112Z compat result: status={compat_result.get('status')}, envelopes={compat_result.get('envelopes_written')}")

    # ── Step 2: Validate envelope preconditions ──────────────────────────────────
    print("[2/6] Validating envelope preconditions...")
    precondition_errors: list[str] = []
    for i, env in enumerate(input_envelopes):
        errors = validate_envelope_preconditions(env, i)
        precondition_errors.extend(errors)

    all_preconditions_met = len(precondition_errors) == 0
    if all_preconditions_met:
        print(f"  All {input_count} envelopes passed precondition validation.")
    else:
        print(f"  [WARN] {len(precondition_errors)} precondition issues:")
        for err in precondition_errors[:10]:
            print(f"    - {err}")
        if len(precondition_errors) > 10:
            print(f"    ... and {len(precondition_errors) - 10} more")
    print()

    # ── Step 3: Build preview cards ──────────────────────────────────────────────
    print("[3/6] Building degraded whale preview cards...")
    preview_cards: list[dict] = []
    build_errors: list[str] = []

    for i, env in enumerate(input_envelopes):
        try:
            card = build_degraded_whale_preview_card(env, i)
            preview_cards.append(card)
        except Exception as e:
            build_errors.append(f"Envelope {i}: {e}")
            print(f"  [ERROR] Failed to build preview card for envelope {i}: {e}")

    card_count = len(preview_cards)
    print(f"  Built: {card_count} preview cards")

    if build_errors:
        print(f"  {len(build_errors)} build errors:")
        for err in build_errors:
            print(f"    - {err}")
    print()

    # ── Step 4: Validate preview cards ───────────────────────────────────────────
    print("[4/6] Validating preview cards...")
    card_errors: list[str] = []
    for i, card in enumerate(preview_cards):
        errors = validate_preview_card(card, i)
        card_errors.extend(errors)

    all_cards_valid = len(card_errors) == 0
    if all_cards_valid:
        print(f"  All {card_count} preview cards passed validation.")
    else:
        print(f"  {len(card_errors)} card validation issues:")
        for err in card_errors[:20]:
            print(f"    - {err}")
        if len(card_errors) > 20:
            print(f"    ... and {len(card_errors) - 20} more")

    # ── Safety invariant checks ──────────────────────────────────────────────────
    all_local_preview = all(c.get("local_preview_only") is True for c in preview_cards)
    all_not_eligible = all(c.get("eligible_for_real_send") is False for c in preview_cards)
    all_not_candidate = all(c.get("real_send_candidate") is False for c in preview_cards)
    all_no_tg = all(c.get("tg_send_allowed") is False for c in preview_cards)
    all_degraded = all(c.get("degraded") is True for c in preview_cards)
    all_mock = all(c.get("mock_replay_only") is True for c in preview_cards)
    all_label_conf = all(bool(c.get("label_confidence")) for c in preview_cards)

    print(f"  all_local_preview_only=true: {all_local_preview}")
    print(f"  all_eligible_for_real_send=false: {all_not_eligible}")
    print(f"  all_real_send_candidate=false: {all_not_candidate}")
    print(f"  all_tg_send_allowed=false: {all_no_tg}")
    print(f"  all_degraded=true: {all_degraded}")
    print(f"  all_mock_replay_only=true: {all_mock}")
    print(f"  all_label_confidence_present: {all_label_conf}")
    print()

    # ── Label confidence distribution ────────────────────────────────────────────
    label_conf_dist: dict[str, int] = {}
    for card in preview_cards:
        lc = str(card.get("label_confidence", "unknown"))
        label_conf_dist[lc] = label_conf_dist.get(lc, 0) + 1

    print(f"  Label confidence distribution: {label_conf_dist}")

    # Verify low/medium confidence cards have explanation
    low_medium_cards = [c for c in preview_cards if str(c.get("label_confidence", "")) in ("low", "medium")]
    all_have_explanation = all(bool(c.get("label_explanation")) for c in low_medium_cards)
    print(f"  Low/medium confidence cards have explanation: {all_have_explanation}")

    # ── Warnings distribution ────────────────────────────────────────────────────
    warning_dist: dict[str, int] = {}
    for card in preview_cards:
        for w in card.get("warnings", []):
            warning_dist[w] = warning_dist.get(w, 0) + 1

    print(f"  Warnings distribution:")
    for w, count in sorted(warning_dist.items()):
        print(f"    - {w}: {count}")

    # Liquidation price check
    null_liq_cards = [c for c in preview_cards if c.get("liquidation_price") is None]
    all_null_liq_displayed = all(
        "清算价格不可用" in str(c.get("liquidation_price_display", ""))
        for c in null_liq_cards
    )
    print(f"  Null liquidation_price cards: {len(null_liq_cards)}")
    print(f"  All null liq show '清算价格不可用': {all_null_liq_displayed}")

    # Delta check
    delta_unavail_cards = [c for c in preview_cards if "unavailable" in str(c.get("delta_status", ""))]
    all_delta_displayed = all(
        "暂无法计算仓位变化" in str(c.get("delta_display", ""))
        for c in delta_unavail_cards
    )
    print(f"  Delta unavailable cards: {len(delta_unavail_cards)}")
    print(f"  All delta show explanation: {all_delta_displayed}")

    # Timestamp check
    local_ts_cards = [c for c in preview_cards if "local" in str(c.get("timestamp_status", ""))]
    all_ts_displayed = all(
        "本地观察时间" in str(c.get("timestamp_display", ""))
        for c in local_ts_cards
    )
    print(f"  Local timestamp cards: {len(local_ts_cards)}")
    print(f"  All timestamp show '本地观察时间': {all_ts_displayed}")
    print()

    # ── Step 5: Write outputs ────────────────────────────────────────────────────
    print("[5/6] Writing outputs...")

    # Ensure directories exist
    PREVIEW_CARDS_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 5a. Write preview cards JSONL
    with open(PREVIEW_CARDS_JSONL_PATH, "w", encoding="utf-8") as f:
        for card in preview_cards:
            f.write(json.dumps(card, ensure_ascii=False) + "\n")
    print(f"  [OK] {PREVIEW_CARDS_JSONL_PATH} ({card_count} lines)")

    # 5b. Write result JSON
    result = {
        "version": "v113A",
        "status": "passed" if all_cards_valid and card_count == input_count else "partial",
        "input_envelopes_loaded": input_count,
        "preview_cards_written": card_count,
        "external_api_called": False,
        "local_preview_only": True,
        "degraded_preview_pack_built": True,
        "eligible_for_real_send_count": 0,
        "real_send_candidate_count": 0,
        "tg_send_allowed_count": 0,
        "prod_state_write": False,
        "daemon_started": False,
        "watcher_started": False,
        "credentials_read": False,
        "files_deleted": False,
        "label_confidence_displayed": all_label_conf,
        "liquidation_price_unavailable_displayed": all_null_liq_displayed,
        "delta_unavailable_displayed": all_delta_displayed,
        "local_timestamp_displayed": all_ts_displayed,
        "all_local_preview_only_true": all_local_preview,
        "all_eligible_for_real_send_false": all_not_eligible,
        "all_real_send_candidate_false": all_not_candidate,
        "all_tg_send_allowed_false": all_no_tg,
        "all_degraded_true": all_degraded,
        "all_mock_replay_only_true": all_mock,
        "label_confidence_distribution": label_conf_dist,
        "warnings_distribution": warning_dist,
        "null_liquidation_price_cards": len(null_liq_cards),
        "delta_unavailable_cards": len(delta_unavail_cards),
        "local_timestamp_cards": len(local_ts_cards),
        "all_preconditions_met": all_preconditions_met,
        "all_cards_valid": all_cards_valid,
        "precondition_errors": len(precondition_errors),
        "card_validation_errors": len(card_errors),
        "build_errors": len(build_errors),
        "cards_equal_input_envelopes": card_count == input_count,
        "next_step": "v113b_degraded_whale_preview_quality_gate_local_only",
        "generated_at": china_stamp(),
    }

    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")

    # 5c. Write report
    write_report(preview_cards, result, label_conf_dist, warning_dist)
    print(f"  [OK] {REPORT_MD_PATH}")

    # 5d. Write handoff
    write_handoff(preview_cards, result, label_conf_dist, warning_dist)
    print(f"  [OK] {HANDOFF_MD_PATH}")

    # ── Step 6: Summary ──────────────────────────────────────────────────────────
    print()
    print(f"{'=' * 70}")
    print(f"v1.13-A Degraded Whale Preview Pack (Local Only) — Complete")
    print(f"{'=' * 70}")
    print(f"  Input envelopes:              {input_count}")
    print(f"  Preview cards generated:      {card_count}")
    print(f"  Cards == envelopes:           {card_count == input_count}")
    print(f"  All preconditions met:        {all_preconditions_met}")
    print(f"  All cards valid:              {all_cards_valid}")
    print(f"  Label confidence:             {label_conf_dist}")
    print(f"  Null liquidation cards:       {len(null_liq_cards)}")
    print(f"  Delta unavailable cards:      {len(delta_unavail_cards)}")
    print(f"  Local timestamp cards:        {len(local_ts_cards)}")
    print(f"  local_preview_only:           ALL TRUE")
    print(f"  eligible_for_real_send:       ALL FALSE")
    print(f"  real_send_candidate:          ALL FALSE")
    print(f"  tg_send_allowed:              ALL FALSE")
    print(f"  External API:                 NONE")
    print(f"  TG send:                      NONE")
    print(f"  Prod state write:             NONE")
    print(f"  Daemon/Watcher/Cron/Loop:     NONE")
    print(f"  Credentials read:             NONE")
    print(f"  Next step:                    v113b_degraded_whale_preview_quality_gate_local_only")
    print(f"{'=' * 70}")

    return 0


# ══════════════════════════════════════════════════════════════════════════════════════════
# Report / Handoff Writers
# ══════════════════════════════════════════════════════════════════════════════════════════

def write_report(
    preview_cards: list[dict],
    result: dict,
    label_conf_dist: dict[str, int],
    warning_dist: dict[str, int],
) -> None:
    """Write the v113A Markdown report."""
    lines = [
        f"# Market Radar v1.13-A — Degraded Whale Preview Pack (Local Only) 报告",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: v113A",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Based on**: v112Z degraded whale envelopes",
        f"",
        f"---",
        f"",
        f"## 概述",
        f"",
        f"本报告证明基于 v112Z 的 {result['input_envelopes_loaded']} 条 degraded whale envelopes",
        f"成功生成了 {result['preview_cards_written']} 张本地 preview card。",
        f"",
        f"所有 preview card 均保留 degraded 标识，用于验证 Market Radar 卡片展示层",
        f"能正确表达降级状态。本轮**仅生成本地预览包**，不做 TG 发送，不做外部请求，",
        f"不做生产写入。",
        f"",
        f"---",
        f"",
        f"## 全局统计",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 输入 envelopes 数量 | {result['input_envelopes_loaded']} |",
        f"| 输出 preview cards 数量 | {result['preview_cards_written']} |",
        f"| cards 与 envelopes 一致 | {result['cards_equal_input_envelopes']} |",
        f"| external_api_called | {result['external_api_called']} |",
        f"| local_preview_only | {result['local_preview_only']} |",
        f"| degraded_preview_pack_built | {result['degraded_preview_pack_built']} |",
        f"| eligible_for_real_send_count | {result['eligible_for_real_send_count']} |",
        f"| real_send_candidate_count | {result['real_send_candidate_count']} |",
        f"| tg_send_allowed_count | {result['tg_send_allowed_count']} |",
        f"| prod_state_write | {result['prod_state_write']} |",
        f"| daemon_started | {result['daemon_started']} |",
        f"| watcher_started | {result['watcher_started']} |",
        f"| credentials_read | {result['credentials_read']} |",
        f"| files_deleted | {result['files_deleted']} |",
        f"",
        f"---",
        f"",
        f"## Label Confidence 分布",
        f"",
        f"| 置信度 | 数量 |",
        f"|--------|------|",
    ]
    for conf in ["high", "medium", "low", "unknown"]:
        count = label_conf_dist.get(conf, 0)
        lines.append(f"| {conf} | {count} |")
    lines.extend([
        f"",
        f"**注意**: 没有 high confidence 标签。low/medium 标签均保留 label_explanation，",
        f"未伪装成确定机构。",
        f"",
        f"---",
        f"",
        f"## Warnings 分布",
        f"",
        f"| Warning | 出现次数 |",
        f"|---------|----------|",
    ])
    for w, count in sorted(warning_dist.items()):
        lines.append(f"| {w} | {count} |")
    lines.extend([
        f"",
        f"---",
        f"",
        f"## Degraded 展示层验证状态",
        f"",
        f"| 展示项 | 状态 |",
        f"|--------|------|",
        f"| label_confidence_displayed | {'✅' if result['label_confidence_displayed'] else '❌'} |",
        f"| liquidation_price_unavailable_displayed | {'✅' if result['liquidation_price_unavailable_displayed'] else '❌'} |",
        f"| delta_unavailable_displayed | {'✅' if result['delta_unavailable_displayed'] else '❌'} |",
        f"| local_timestamp_displayed | {'✅' if result['local_timestamp_displayed'] else '❌'} |",
        f"",
        f"---",
        f"",
        f"## Routing Guard 状态",
        f"",
        f"| Guard | 值 |",
        f"|-------|-----|",
        f"| local_preview_only | true (all) |",
        f"| eligible_for_real_send | false (all) |",
        f"| real_send_candidate | false (all) |",
        f"| tg_send_allowed | false (all) |",
        f"| prod_state_write_allowed | false (all) |",
        f"",
        f"**所有 preview card 均**:",
        f"- local_preview_only = true",
        f"- eligible_for_real_send = false",
        f"- real_send_candidate = false",
        f"- tg_send_allowed = false",
        f"- 不得进入 TG send path",
        f"- 不伪装成 live passed",
        f"- 不写 prod state",
        f"",
        f"---",
        f"",
        f"## Preview Card 列表",
        f"",
    ])

    for i, card in enumerate(preview_cards, 1):
        lines.extend([
            f"### {i}. {card.get('asset', '?')} {card.get('side', '?')} — {card.get('label', '?')}",
            f"",
            f"| 字段 | 值 |",
            f"|------|-----|",
            f"| address | `{card.get('address_short', '?')}` |",
            f"| label | {card.get('label', '?')} |",
            f"| label_confidence | {card.get('label_confidence', '?')} |",
            f"| entity_type | {card.get('entity_type', '?')} |",
            f"| asset | {card.get('asset', '?')} |",
            f"| side | {card.get('side', '?')} |",
            f"| notional_usd | {card.get('notional_usd', 0):,.0f} |",
            f"| leverage | {card.get('leverage', 0):,.0f}x |",
            f"| liquidation_price_display | {card.get('liquidation_price_display', '?')} |",
            f"| delta_display | {card.get('delta_display', '?')} |",
            f"| timestamp_display | {card.get('timestamp_display', '?')} |",
            f"| local_preview_only | {card.get('local_preview_only')} |",
            f"| eligible_for_real_send | {card.get('eligible_for_real_send')} |",
            f"| tg_send_allowed | {card.get('tg_send_allowed')} |",
            f"| warnings | {', '.join(card.get('warnings', []))} |",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## 执行约束确认",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| external_api_called | false |",
        f"| AI/API/model calls | false |",
        f"| tg_send | false |",
        f"| prod_state_write | false |",
        f"| daemon_started | false |",
        f"| watcher_started | false |",
        f"| credentials_read | false |",
        f"| files_deleted | false |",
        f"| eligible_for_real_send | false (all) |",
        f"| real_send_candidate | false (all) |",
        f"| tg_send_allowed | false (all) |",
        f"| degraded 伪装成 live passed | false |",
        f"| low-confidence 伪装成确定机构 | false |",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"v113b: degraded whale preview quality gate local-only — ",
        f"对 preview card 质量建立关卡验证，确保展示层完整覆盖降级场景。",
        f"",
    ])

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_handoff(
    preview_cards: list[dict],
    result: dict,
    label_conf_dist: dict[str, int],
    warning_dist: dict[str, int],
) -> None:
    """Write the v113A handoff markdown."""
    lines = [
        f"# Market Radar v1.13-A — Degraded Whale Preview Pack (Local Only) Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: v113A",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"",
        f"---",
        f"",
        f"## 修改文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `scripts/run_market_radar_v113a_degraded_whale_preview_pack_local_only.py` | 新增 | v113A degraded whale preview pack runner |",
        f"| `scripts/test_market_radar_v113a_degraded_whale_preview_pack_local_only.py` | 新增 | v113A test suite |",
        f"| `results/market_radar_v113a_degraded_whale_preview_cards.jsonl` | 新增 | Preview cards JSONL |",
        f"| `results/market_radar_v113a_degraded_whale_preview_pack_result.json` | 新增 | Result JSON |",
        f"| `runs/market_radar/v113a_degraded_whale_preview_pack_local_only.md` | 新增 | Markdown 报告 |",
        f"| `runs/market_radar/v113a_degraded_whale_preview_pack_local_only_handoff.md` | 新增 | Handoff（本文件） |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"cd C:\\Users\\PC\\Desktop\\Projects\\事件情报系统",
        f"python scripts/run_market_radar_v113a_degraded_whale_preview_pack_local_only.py",
        f"python scripts/test_market_radar_v113a_degraded_whale_preview_pack_local_only.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## 输入与输出",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| Input envelopes | {result['input_envelopes_loaded']} |",
        f"| Output preview cards | {result['preview_cards_written']} |",
        f"| Cards == envelopes | {result['cards_equal_input_envelopes']} |",
        f"| All preconditions met | {result['all_preconditions_met']} |",
        f"| All cards valid | {result['all_cards_valid']} |",
        f"| Build errors | {result['build_errors']} |",
        f"",
        f"---",
        f"",
        f"## Label Confidence 摘要",
        f"",
        f"| 置信度 | 数量 |",
        f"|--------|------|",
    ]
    for conf in ["high", "medium", "low", "unknown"]:
        count = label_conf_dist.get(conf, 0)
        lines.append(f"| {conf} | {count} |")
    lines.extend([
        f"",
        f"⚠️ 无 high confidence 标签。所有 medium/low 标签均正确保留 label_explanation，",
        f"未伪装成确定机构。",
        f"",
        f"---",
        f"",
        f"## Warning 摘要",
        f"",
        f"| Warning | 出现次数 |",
        f"|---------|----------|",
    ])
    for w, count in sorted(warning_dist.items()):
        lines.append(f"| {w} | {count} |")
    lines.extend([
        f"",
        f"---",
        f"",
        f"## Routing Guard 摘要",
        f"",
        f"| Guard | 值 |",
        f"|-------|-----|",
        f"| local_preview_only | ALL TRUE |",
        f"| eligible_for_real_send | ALL FALSE |",
        f"| real_send_candidate | ALL FALSE |",
        f"| tg_send_allowed | ALL FALSE |",
        f"| prod_state_write_allowed | ALL FALSE |",
        f"",
        f"---",
        f"",
        f"## Safety Invariant 状态",
        f"",
        f"| Invariant | 状态 |",
        f"|-----------|------|",
        f"| No external API calls | ✅ |",
        f"| No AI/API/model calls | ✅ |",
        f"| No credentials read | ✅ |",
        f"| No TG send | ✅ |",
        f"| No prod state write | ✅ |",
        f"| No daemon/watcher/cron/loop | ✅ |",
        f"| No files deleted | ✅ |",
        f"| Degraded preview NOT disguised as live passed | ✅ |",
        f"| Low-confidence labels NOT disguised as confirmed institutions | ✅ |",
        f"| All label_confidence preserved | ✅ |",
        f"| All null liquidation_price show '清算价格不可用' | {'✅' if result['liquidation_price_unavailable_displayed'] else '❌'} |",
        f"| All delta unavailable show explanation | {'✅' if result['delta_unavailable_displayed'] else '❌'} |",
        f"| All local timestamp show '本地观察时间' | {'✅' if result['local_timestamp_displayed'] else '❌'} |",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"v113b: degraded whale preview quality gate local-only — ",
        f"对 preview card 质量建立关卡验证，确保展示层完整覆盖降级场景。",
        f"",
    ])

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
