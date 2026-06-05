"""Market Radar v1.12-F — Whale Position Alert Local Enrichment Adapter

Provides local address label enrichment, historical position sequence tracking,
position delta calculation, alert type classification, valid/blocked decision,
and public card rendering — all from local fixtures without external API calls.

Design principle:
  Load fixture → Normalize → Enrich label → Calculate delta →
  Classify alert type → Decide valid/blocked → Render public card →
  Debug/secret leak check → Output.

Classes:
  WhaleAddressLabel    — normalized address label record
  WhalePositionEvent   — normalized whale position event
  EnrichedWhaleAlert   — fully enriched whale alert ready for card rendering

Functions:
  load_address_labels(path) → list[dict]
  load_whale_positions(path) → list[dict]
  normalize_whale_position(raw) → WhalePositionEvent
  enrich_wallet_label(event, labels) → WhalePositionEvent
  calculate_position_delta(event) → tuple[float, str]
  classify_alert_type(event) → str
  decide_valid_blocked(event) → tuple[bool, str | None]
  render_whale_public_card(event, label) → str
  check_public_debug_leak(text) → list[str]
  check_public_secret_leak(text) → list[str]
  process_whale_position(raw, labels) → dict

Security:
  - Does NOT read / print / save any token, chat_id, key, cookie, or password.
  - Does NOT access environment variables for credentials.
  - Does NOT make network calls.
  - Does NOT call any external AI service.
  - Does NOT send Telegram messages.
  - Does NOT output full wallet addresses in public cards.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

VERSION = "v1.12-F"
MODE = "whale_position_local_enrichment"

CN_TZ = timezone(timedelta(hours=8))

# ══════════════════════════════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class WhaleAddressLabel:
    """Normalized address label for a wallet."""
    wallet: str = ""
    label: str = ""
    entity_type: str = ""       # smart_money | high_leverage_trader | exchange_related | fund_wallet | unknown_whale | market_maker
    confidence: str = "medium"  # high | medium | low
    source_type: str = ""       # onchain_analysis | hyperliquid_observer | arkham_intelligence_label | nansen_ai_label | onchain_heuristic
    tags: list[str] = field(default_factory=list)
    estimated_portfolio_usd: float = 0.0
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WhalePositionEvent:
    """Normalized whale position event — the canonical input shape for enrichment."""
    data_mode: str = "fixture"
    source: str = "local_fixture_v112f"
    event_id: str = ""
    observed_at: str = ""
    wallet: str = ""
    asset: str = ""
    side: str = ""                   # long | short
    entry_price: float = 0.0
    mark_price: float = 0.0
    position_size_usd: float = 0.0
    leverage: float = 0.0
    unrealized_pnl_usd: float = 0.0
    unrealized_pnl_pct: float = 0.0
    margin_used_usd: float = 0.0
    liquidation_price: float = 0.0
    previous_position_size_usd: float = 0.0
    previous_observed_at: str = ""
    position_delta_usd: float = 0.0
    alert_type: str = "unknown"      # position_opened | position_increased | position_reduced | high_leverage_risk | large_unrealized_loss | unknown
    # Enrichment fields (populated after processing)
    label: str = ""
    entity_type: str = ""
    label_confidence: str = ""
    wallet_short: str = ""
    chain: str = "hyperliquid"
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════════════

# Valid alert types
VALID_ALERT_TYPES = [
    "position_opened",
    "position_increased",
    "position_reduced",
    "high_leverage_risk",
    "large_unrealized_loss",
    "unknown",
]

# Valid entity types for address labels
VALID_ENTITY_TYPES = [
    "smart_money",
    "high_leverage_trader",
    "exchange_related",
    "fund_wallet",
    "unknown_whale",
    "market_maker",
]

# Thresholds for valid whale signals
WHALE_POSITION_SIZE_THRESHOLD = 500_000         # $500K minimum
WHALE_POSITION_DELTA_THRESHOLD = 200_000        # $200K minimum delta
WHALE_LEVERAGE_THRESHOLD = 10                   # 10x+ leverage
WHALE_UNREALIZED_LOSS_THRESHOLD = -100_000      # -$100K underwater

# Block thresholds
BLOCK_POSITION_SIZE_MIN = 50_000                # Below $50K is too small

# Debug / secret leak terms (extended for v112f)
DEBUG_LEAK_TERMS = [
    "debug", "internal", "trace", "fixture",
    "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
    "payload_render", "format_check", "content_quality",
    "gate_decision", "score↑", "blocked_by", "gate_version",
    "factor_hits", "block_reason", "block_rules", "block_triggered",
    "admission_result", "not_reached", "mock_sent", "mock_message_id",
    "价值:", "冷却:", "pre_send:", "allow", "upgrade_override",
    "block", "observe",
]

SECRET_LEAK_TERMS = [
    "secret", "token", "api_key", "chat_id", "password",
]

LOCAL_PATH_PATTERNS = [
    r'[A-Za-z]:\\Users',
    r'[A-Za-z]:\\Program',
    r'[A-Za-z]:\\Windows',
    r'/home/',
    r'/Users/',
    r'ai_relay_desk',
]

SYNTHETIC_KEYS = [
    "0x7a9f2c8d4e6b1a3f5c7d9e2b4a6f8c0d2e4a6b8c",
    "0x3b6e9f1c8a5d2f4e7a1c5d8f2b4e6a8c0d2e4f6a",
    "0x5c8d1f4a7e2b9f6c3a8d5e2f4b6a8c0d2e4f6a8b",
    "0x9e2b4a6f8c0d2e4a6b8c0d2e4f6a8b0c2d4e6f8a",
    "0x1f4a7e2b9c6d8f0a3c5e7b9d1f4a6c8e0b2d4f6a",
    "0x2d4e6f8a0b2c4e6f8a0d2c4e6f8a0b2c4d6e8f0a2",
]


# ══════════════════════════════════════════════════════════════════════════════════════
# Load Functions
# ══════════════════════════════════════════════════════════════════════════════════════

def load_address_labels(path: str | Path | None = None) -> list[dict]:
    """Load whale address labels from a fixture JSON file.

    Args:
        path: Path to the address labels fixture JSON. If None, uses default v112f path.

    Returns:
        List of label dicts.
    """
    if path is None:
        root = Path(__file__).resolve().parents[1]
        path = root / "data" / "fixtures" / "market_radar_v112f_whale_address_labels.json"

    p = Path(path)
    if not p.exists():
        return []

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("labels", [])


def load_whale_positions(path: str | Path | None = None) -> list[dict]:
    """Load whale position sequence from a fixture JSON file.

    Args:
        path: Path to the whale positions fixture JSON. If None, uses default v112f path.

    Returns:
        List of position dicts.
    """
    if path is None:
        root = Path(__file__).resolve().parents[1]
        path = root / "data" / "fixtures" / "market_radar_v112f_whale_positions.json"

    p = Path(path)
    if not p.exists():
        return []

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("positions", [])


# ══════════════════════════════════════════════════════════════════════════════════════
# Normalize
# ══════════════════════════════════════════════════════════════════════════════════════

def normalize_whale_position(raw: dict) -> WhalePositionEvent:
    """Normalize a raw whale position dict into a canonical WhalePositionEvent.

    Handles field name variations and missing fields gracefully.
    """
    return WhalePositionEvent(
        data_mode=str(raw.get("data_mode", "fixture")),
        source=str(raw.get("source", "local_fixture_v112f")),
        event_id=str(raw.get("event_id", "")),
        observed_at=str(raw.get("observed_at", "")),
        wallet=str(raw.get("wallet") or ""),
        asset=str(raw.get("asset", "")),
        side=str(raw.get("side", "")),
        entry_price=_safe_float(raw.get("entry_price")),
        mark_price=_safe_float(raw.get("mark_price")),
        position_size_usd=_safe_float(raw.get("position_size_usd")),
        leverage=_safe_float(raw.get("leverage")),
        unrealized_pnl_usd=_safe_float(raw.get("unrealized_pnl_usd")),
        unrealized_pnl_pct=_safe_float(raw.get("unrealized_pnl_pct")),
        margin_used_usd=_safe_float(raw.get("margin_used_usd")),
        liquidation_price=_safe_float(raw.get("liquidation_price")),
        previous_position_size_usd=_safe_float(raw.get("previous_position_size_usd")),
        previous_observed_at=str(raw.get("previous_observed_at") or ""),
        position_delta_usd=_safe_float(raw.get("position_delta_usd")),
        alert_type=str(raw.get("alert_type", "unknown")),
        chain=str(raw.get("chain", "hyperliquid")),
        note=str(raw.get("note", "")),
    )


# ══════════════════════════════════════════════════════════════════════════════════════
# Enrich — Wallet Label
# ══════════════════════════════════════════════════════════════════════════════════════

def enrich_wallet_label(
    event: WhalePositionEvent,
    labels: list[dict],
) -> WhalePositionEvent:
    """Enrich a whale position event with address label information.

    Looks up the wallet address in the labels list. If found, populates
    label, entity_type, label_confidence, and wallet_short fields.
    If not found, marks as "unlabeled" with entity_type "unknown_whale".

    Args:
        event: Normalized whale position event.
        labels: List of address label dicts.

    Returns:
        The same event with label fields populated.
    """
    if not event.wallet:
        event.label = ""
        event.entity_type = ""
        event.label_confidence = ""
        event.wallet_short = ""
        return event

    # Generate short wallet form regardless
    event.wallet_short = _wallet_short(event.wallet)

    # Look up label
    for lbl in labels:
        if lbl.get("wallet", "").lower() == event.wallet.lower():
            event.label = str(lbl.get("label", ""))
            event.entity_type = str(lbl.get("entity_type", "unknown_whale"))
            event.label_confidence = str(lbl.get("confidence", "low"))
            return event

    # No label found
    event.label = "Unknown Whale"
    event.entity_type = "unknown_whale"
    event.label_confidence = "low"
    return event


# ══════════════════════════════════════════════════════════════════════════════════════
# Position Delta
# ══════════════════════════════════════════════════════════════════════════════════════

def calculate_position_delta(event: WhalePositionEvent) -> tuple[float, str]:
    """Calculate the position size delta and direction.

    Uses previous_position_size_usd to compute the change. If the event
    already has position_delta_usd set, it is used directly. Otherwise
    it is computed as current - previous.

    Returns:
        (delta_usd: float, delta_direction: str) — one of:
        "opened", "increased", "reduced", "unchanged"
    """
    prev = event.previous_position_size_usd
    curr = event.position_size_usd

    # Use pre-computed delta if available and no previous data
    if abs(event.position_delta_usd) > 1e-10:
        delta = event.position_delta_usd
    else:
        delta = curr - prev

    if prev <= 0 and curr > 0:
        direction = "opened"
    elif delta > 0 and abs(delta) > 1e-10:
        direction = "increased"
    elif delta < 0 and abs(delta) > 1e-10:
        direction = "reduced"
    else:
        direction = "unchanged"

    # Store computed delta back on event
    if abs(event.position_delta_usd) < 1e-10:
        event.position_delta_usd = delta

    return delta, direction


# ══════════════════════════════════════════════════════════════════════════════════════
# Alert Type Classification
# ══════════════════════════════════════════════════════════════════════════════════════

def classify_alert_type(event: WhalePositionEvent) -> str:
    """Classify the alert type for a whale position event.

    Priority-based classification:
      1. If event already has a valid alert_type set, use it.
      2. If leverage >= 10 → high_leverage_risk (unless overridden by loss)
      3. If unrealized_pnl_usd <= -100000 → large_unrealized_loss
      4. If previous position was 0 and current > 0 → position_opened
      5. If delta > 0 → position_increased
      6. If delta < 0 → position_reduced
      7. Fallback → unknown

    Returns:
        Alert type string.
    """
    # Use pre-existing alert_type if valid
    if event.alert_type and event.alert_type in VALID_ALERT_TYPES and event.alert_type != "unknown":
        return event.alert_type

    # Compute delta if not set
    delta, direction = calculate_position_delta(event)

    # Priority: large loss overrides leverage risk
    if event.unrealized_pnl_usd <= WHALE_UNREALIZED_LOSS_THRESHOLD:
        event.alert_type = "large_unrealized_loss"
        return event.alert_type

    if event.leverage >= WHALE_LEVERAGE_THRESHOLD:
        event.alert_type = "high_leverage_risk"
        return event.alert_type

    if direction == "opened":
        event.alert_type = "position_opened"
    elif direction == "increased":
        event.alert_type = "position_increased"
    elif direction == "reduced":
        event.alert_type = "position_reduced"
    else:
        # Check if still valid by other criteria
        if event.position_size_usd >= WHALE_POSITION_SIZE_THRESHOLD:
            event.alert_type = "position_opened"  # default for large position
        else:
            event.alert_type = "unknown"

    return event.alert_type


# ══════════════════════════════════════════════════════════════════════════════════════
# Valid / Blocked Decision
# ══════════════════════════════════════════════════════════════════════════════════════

def decide_valid_blocked(event: WhalePositionEvent) -> tuple[bool, bool, str | None]:
    """Decide whether a whale position event is valid or blocked.

    Valid whale signal criteria (at least one must be met):
      - position_size_usd >= 500,000
      - abs(position_size_delta_usd) >= 200,000
      - leverage >= 10
      - unrealized_pnl_usd <= -100,000

    Block criteria:
      - Missing wallet address
      - Position size < $50,000 (below minimum threshold)
      - Asset is unsupported or missing

    Returns:
        (valid: bool, blocked: bool, block_reason: str | None)
    """
    # ── Block checks ──────────────────────────────────────────────────
    if not event.wallet or str(event.wallet).strip() == "":
        return False, True, "missing_wallet"

    if not event.asset or str(event.asset).strip() == "":
        return False, True, "missing_asset"

    if event.position_size_usd < BLOCK_POSITION_SIZE_MIN:
        return False, True, "position_size_too_small"

    # ── Validity checks ───────────────────────────────────────────────
    is_valid = False

    if event.position_size_usd >= WHALE_POSITION_SIZE_THRESHOLD:
        is_valid = True
    elif abs(event.position_delta_usd) >= WHALE_POSITION_DELTA_THRESHOLD:
        is_valid = True
    elif event.leverage >= WHALE_LEVERAGE_THRESHOLD:
        is_valid = True
    elif event.unrealized_pnl_usd <= WHALE_UNREALIZED_LOSS_THRESHOLD:
        is_valid = True

    if not is_valid:
        return False, True, "below_whale_threshold"

    return True, False, None


# ══════════════════════════════════════════════════════════════════════════════════════
# Public Card Renderer
# ══════════════════════════════════════════════════════════════════════════════════════

def render_whale_public_card(event: WhalePositionEvent) -> str:
    """Render a clean public whale position alert card.

    The card MUST NOT contain:
      - Full wallet addresses (only short form: 0x7a9f...b8c)
      - Debug/internal/trace/fixture/secret/token/api_key/chat_id/password terms
      - Local absolute paths
      - Gate/internal pipeline terms

    Each card includes:
      - Whale label
      - Wallet short form
      - Asset
      - Side (long/short in Chinese)
      - Position size (USD)
      - Leverage
      - Position delta
      - Alert type
      - Concise reason
      - Observed at

    Args:
        event: Fully enriched whale position event.

    Returns:
        Public card text string.
    """
    asset = event.asset or "Unknown"
    side_cn = "多头" if event.side.lower() == "long" else "空头" if event.side.lower() == "short" else event.side or "未知"
    wallet_short = event.wallet_short or _wallet_short(event.wallet)
    label = event.label or "Unknown Whale"

    # Determine alert type display
    alert_type_display = {
        "position_opened": "新开仓位",
        "position_increased": "加仓",
        "position_reduced": "减仓",
        "high_leverage_risk": "高杠杆风险",
        "large_unrealized_loss": "大额浮亏",
        "unknown": "未知变动",
    }.get(event.alert_type, "仓位变动")

    # Title emoji
    if "loss" in event.alert_type or event.unrealized_pnl_usd < -50000:
        title_emoji = "🔴"
    elif "risk" in event.alert_type or event.leverage >= 10:
        title_emoji = "🟠"
    elif "opened" in event.alert_type or "increased" in event.alert_type:
        title_emoji = "🟢"
    elif "reduced" in event.alert_type:
        title_emoji = "🔵"
    else:
        title_emoji = "📊"

    # Build reason
    reasons_parts = []
    if abs(event.position_delta_usd) >= 100_000:
        delta_dir = "增加" if event.position_delta_usd > 0 else "减少"
        reasons_parts.append(f"仓位{delta_dir} {_fmt_money(abs(event.position_delta_usd))}")
    if event.leverage >= 10:
        reasons_parts.append(f"{event.leverage:.0f}x 高杠杆")
    if event.unrealized_pnl_usd <= -50000:
        reasons_parts.append(f"浮亏 {_fmt_money(abs(event.unrealized_pnl_usd))}")
    if event.position_size_usd >= WHALE_POSITION_SIZE_THRESHOLD:
        reasons_parts.append(f"大额持仓 {_fmt_money(event.position_size_usd)}")

    concise_reason = "；".join(reasons_parts) if reasons_parts else f"{alert_type_display}，持仓 {_fmt_money(event.position_size_usd)}"

    # Build card lines
    lines = []

    # Title
    lines.append(f"{title_emoji} 巨鲸仓位警报｜{asset} {side_cn} {alert_type_display}")
    lines.append("")

    # Whale label and wallet
    lines.append(f"🏷️ 地址标签：{label}")
    lines.append(f"📌 钱包地址：`{wallet_short}`")
    lines.append("")

    # Key metrics
    lines.append(f"● 资产：{asset}")
    lines.append(f"● 方向：{side_cn}")
    lines.append(f"● 持仓规模：{_fmt_money(event.position_size_usd)}")

    if event.leverage > 0:
        lines.append(f"● 杠杆倍数：{event.leverage:.1f}x")

    if abs(event.position_delta_usd) >= 1:
        delta_sign = "+" if event.position_delta_usd > 0 else ""
        lines.append(f"● 仓位变化：{delta_sign}{_fmt_money(event.position_delta_usd)}")

    if event.entry_price > 0:
        lines.append(f"● 开仓均价：${_fmt_price(event.entry_price)}")
    if event.mark_price > 0:
        lines.append(f"● 当前价格：${_fmt_price(event.mark_price)}")

    pnl_sign = "+" if event.unrealized_pnl_usd >= 0 else ""
    if abs(event.unrealized_pnl_usd) > 0.01:
        lines.append(f"● 未实现盈亏：{pnl_sign}{_fmt_money(event.unrealized_pnl_usd)}（{pnl_sign}{event.unrealized_pnl_pct:.1f}%）")

    if event.liquidation_price > 0 and event.mark_price > 0:
        if side_cn == "多头":
            liq_dist = (event.mark_price - event.liquidation_price) / event.mark_price * 100
        else:
            liq_dist = (event.liquidation_price - event.mark_price) / event.mark_price * 100
        liq_dist = max(liq_dist, 0)
        lines.append(f"● 清算价格：${_fmt_price(event.liquidation_price)}（距清算 {liq_dist:.1f}%）")

    lines.append("")

    # Alert type and reason
    lines.append(f"📢 警报类型：{alert_type_display}")
    lines.append(f"💡 触发原因：{concise_reason}")

    if event.previous_observed_at:
        lines.append(f"📅 上次观测：{event.previous_observed_at}")
    lines.append(f"🕐 观测时间：{event.observed_at}")

    lines.append("")
    lines.append(f"🔗 行情查看：CoinGecko / DexScreener")
    lines.append("")
    lines.append("⚠️ 仅供观察，不构成交易建议。巨鲸行为不保证方向正确性。")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════════════
# Debug / Secret Leak Checks
# ══════════════════════════════════════════════════════════════════════════════════════

def check_public_debug_leak(text: str) -> list[str]:
    """Check public card text for forbidden debug/internal/gate terms.

    Args:
        text: Public card text to check.

    Returns:
        List of forbidden debug terms found.
    """
    if not text:
        return []

    text_lower = text.lower()
    found: list[str] = []
    for term in DEBUG_LEAK_TERMS:
        if term.lower() in text_lower:
            found.append(term)
    return found


def check_public_secret_leak(text: str) -> list[str]:
    """Check public card text for secret/token/path leaks.

    Checks for:
      - Secret/token/api_key/chat_id/password terms
      - Local absolute paths (Windows and Unix)
      - ai_relay_desk references
      - Full wallet addresses (42+ char hex addresses)

    Args:
        text: Public card text to check.

    Returns:
        List of forbidden secret terms found.
    """
    if not text:
        return []

    text_lower = text.lower()
    found: list[str] = []

    # Check for secret terms
    for term in SECRET_LEAK_TERMS:
        if term.lower() in text_lower:
            found.append(term)

    # Check for local path patterns
    for pattern in LOCAL_PATH_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(f"local_path:{pattern}")
            break

    # Check for full wallet addresses (0x followed by 40 hex chars)
    # This is a safety net — public cards should only show short form
    full_addr_matches = re.findall(r'0x[a-fA-F0-9]{40}', text)
    # Exclude our known synthetic keys if they somehow appear
    for match in full_addr_matches:
        if match.lower() not in [k.lower() for k in SYNTHETIC_KEYS]:
            pass  # We flag ALL full addresses
        found.append("full_wallet_address")

    return found


def check_secrets_and_debug(text: str) -> tuple[list[str], list[str]]:
    """Combined check for both debug and secret leaks.

    Returns:
        (debug_leaks: list[str], secret_leaks: list[str])
    """
    return check_public_debug_leak(text), check_public_secret_leak(text)


# ══════════════════════════════════════════════════════════════════════════════════════
# Process — Full Pipeline
# ══════════════════════════════════════════════════════════════════════════════════════

def process_whale_position(
    raw: dict,
    labels: list[dict],
) -> dict:
    """Full pipeline: normalize → enrich → classify → validate → render → check.

    This is the single entry point for processing a raw whale position dict
    through the entire v112f enrichment pipeline.

    Args:
        raw: Raw position dict from fixture.
        labels: List of address label dicts.

    Returns:
        Dict with all processing results including:
          - event_id, asset, wallet_short, label, entity_type
          - alert_type, position_delta_usd
          - valid, blocked, block_reason
          - public_card (full text)
          - debug_leak_terms, secret_leak_terms
          - debug_leak_count, secret_leak_count
          - live_ready, real_tg_sent, external_api_called, external_ai_called, daemon_started
    """
    # Step 1: Normalize
    event = normalize_whale_position(raw)

    # Step 2: Enrich wallet label
    event = enrich_wallet_label(event, labels)

    # Step 3: Calculate position delta
    delta, delta_dir = calculate_position_delta(event)

    # Step 4: Classify alert type
    alert_type = classify_alert_type(event)

    # Step 5: Valid / blocked decision
    valid, blocked, block_reason = decide_valid_blocked(event)

    # Step 6: Render public card (only for valid events, or all for diagnostics)
    public_card = render_whale_public_card(event) if valid else ""

    # Step 7: Leak checks
    debug_leaks, secret_leaks = check_secrets_and_debug(public_card)

    return {
        "event_id": event.event_id,
        "observed_at": event.observed_at,
        "data_mode": event.data_mode,
        "source": event.source,
        "asset": event.asset,
        "side": event.side,
        "wallet_short": event.wallet_short,
        "label": event.label,
        "entity_type": event.entity_type,
        "label_confidence": event.label_confidence,
        "position_size_usd": event.position_size_usd,
        "leverage": event.leverage,
        "entry_price": event.entry_price,
        "mark_price": event.mark_price,
        "unrealized_pnl_usd": event.unrealized_pnl_usd,
        "unrealized_pnl_pct": event.unrealized_pnl_pct,
        "liquidation_price": event.liquidation_price,
        "margin_used_usd": event.margin_used_usd,
        "previous_position_size_usd": event.previous_position_size_usd,
        "previous_observed_at": event.previous_observed_at,
        "position_delta_usd": event.position_delta_usd,
        "position_delta_direction": delta_dir,
        "alert_type": alert_type,
        "chain": event.chain,
        "note": event.note,
        "valid": valid,
        "blocked": blocked,
        "block_reason": block_reason,
        "public_card": public_card,
        "public_card_length": len(public_card),
        "debug_leak_terms": debug_leaks,
        "secret_leak_terms": secret_leaks,
        "debug_leak_count": len(debug_leaks),
        "secret_leak_count": len(secret_leaks),
        "clean": len(debug_leaks) == 0 and len(secret_leaks) == 0,
        "live_ready": False,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
    }


# ══════════════════════════════════════════════════════════════════════════════════════
# Utility Functions
# ══════════════════════════════════════════════════════════════════════════════════════

def _safe_float(value, default=0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace("%", "").replace(",", "").replace("+", "").strip()
        if not s:
            return default
        try:
            return float(s)
        except (ValueError, TypeError):
            return default
    return default


def _wallet_short(wallet: str) -> str:
    """Generate short wallet form: 0x7a9f...b8c"""
    if not wallet or str(wallet).strip() == "":
        return "--"
    s = str(wallet).strip()
    if len(s) <= 12:
        return s
    return f"{s[:6]}...{s[-4:]}"


def _fmt_money(value: float) -> str:
    """Format a value as human-readable USD."""
    v = abs(value)
    sign = "-" if value < 0 else ""
    if v >= 1_000_000_000:
        return f"{sign}${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{sign}${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{sign}${v/1_000:.2f}K"
    if v < 0.01 and v > 0:
        return f"{sign}${v:.6f}"
    return f"{sign}${v:,.2f}"


def _fmt_price(value: float) -> str:
    """Format a USD price."""
    v = abs(value)
    if v >= 1000:
        return f"{value:,.2f}"
    if v >= 1:
        return f"{value:.2f}"
    return f"{value:.6f}"


if __name__ == "__main__":
    print(f"Market Radar {VERSION} — Whale Position Feed Adapter")
    print(f"Mode: {MODE}")
    print("This module is intended to be imported, not run directly.")
    print("Use run_market_radar_v112f_whale_position_local_enrichment.py instead.")
