"""Market Radar v1.12-G — Multi-Asset Market Sync Local Correlation Adapter

Provides local multi-asset snapshot loading, synchronized move score calculation,
direction agreement, sector/basket detection, sync type classification,
valid/blocked decision, and public card rendering — all from local fixtures
without external API calls.

Design principle:
  Load fixture → Normalize snapshot → Calculate sync score → Detect direction →
  Classify sync type → Decide valid/blocked → Render public card →
  Debug/secret leak check → Output.

Sync types supported:
  - market_wide_risk_on
  - market_wide_risk_off
  - l2_beta_sync
  - exchange_token_sync
  - stablecoin_liquidity_stress
  - unknown

Valid signal requirements (all must be met):
  - At least 2 assets moving in same direction
  - Average absolute price change >= 3%, OR average volume_change_pct >= 80%, OR average oi_change_pct >= 15%
  - Direction agreement >= 0.66

Functions:
  load_snapshots(path) → list[dict]
  normalize_snapshot(raw) → dict
  calculate_synchronized_move_score(assets) → float
  calculate_direction_agreement(assets) → float
  detect_sector_basket_type(assets) → str
  classify_sync_type(event) → str
  decide_valid_blocked(event) → tuple[bool, str | None]
  render_public_card(event) → str
  check_debug_leak(text) → list[str]
  check_secret_leak(text) → list[str]
  process_snapshot(raw) → dict

Security:
  - Does NOT read / print / save any token, chat_id, key, cookie, or password.
  - Does NOT access environment variables for credentials.
  - Does NOT make network calls.
  - Does NOT call any external AI service.
  - Does NOT send Telegram messages.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

VERSION = "v1.12-G"
MODE = "multi_asset_market_sync_local_correlation"

CN_TZ = timezone(timedelta(hours=8))

# ── Known Sync Types ────────────────────────────────────────────────────────────────

SYNC_TYPES = [
    "market_wide_risk_on",
    "market_wide_risk_off",
    "l2_beta_sync",
    "exchange_token_sync",
    "stablecoin_liquidity_stress",
    "unknown",
]

# ── Sector / Basket Mapping ─────────────────────────────────────────────────────────

L1_ASSETS = {"BTC", "ETH", "SOL", "BNB", "AVAX", "ADA", "DOT", "NEAR", "APT", "SUI", "ATOM", "FTM", "INJ", "SEI", "TIA"}

L2_ASSETS = {"OP", "ARB", "MATIC", "POL", "IMX", "MANTA", "STRK", "ZK", "SCROLL", "BLAST", "MODE", "METIS", "BOBA"}

EXCHANGE_TOKENS = {"BNB", "OKB", "BGB", "CRO", "KCS", "GT", "HTX", "WBT", "MX", "BIT", "LEO"}

STABLECOINS = {"USDT", "USDC", "DAI", "FRAX", "TUSD", "BUSD", "USDD", "USDE", "PYUSD", "FDUSD", "CRVUSD", "GHO"}

HIGH_BETA = {"SOL", "AVAX", "NEAR", "INJ", "RUNE", "PENDLE", "WIF", "BONK", "PEPE", "DOGE", "LDO", "ENS"}

L2_LEADER = {"ETH"}

EXCHANGE_LEADER = {"BNB"}

STABLECOIN_LEADER = {"USDT", "USDC"}

RISK_ON_LEADER = {"BTC", "ETH"}

RISK_OFF_LEADER = {"BTC", "ETH"}


# ══════════════════════════════════════════════════════════════════════════════════════
# Core Functions
# ══════════════════════════════════════════════════════════════════════════════════════

def load_snapshots(path: str | Path) -> list[dict]:
    """Load multi-asset snapshots from a fixture JSON file.

    Args:
        path: Path to the fixture JSON file.

    Returns:
        List of raw snapshot dicts.
    """
    p = Path(path)
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("snapshots", [])


def normalize_snapshot(raw: dict) -> dict:
    """Normalize a raw snapshot into a canonical event dict.

    Args:
        raw: Raw snapshot dict from fixture.

    Returns:
        Normalized event dict with computed fields.
    """
    assets_raw = raw.get("assets", [])

    # Normalize each asset entry
    assets: list[dict] = []
    for a in assets_raw:
        assets.append({
            "asset": str(a.get("asset", "")).upper(),
            "price_change_pct": _safe_float(a.get("price_change_pct")),
            "volume_change_pct": _safe_float(a.get("volume_change_pct")),
            "oi_change_pct": _safe_float(a.get("oi_change_pct")),
            "funding_rate": _safe_float(a.get("funding_rate")),
            "liquidation_usd": _safe_float(a.get("liquidation_usd")),
            "is_fixture": a.get("is_fixture", raw.get("is_fixture", True)),
        })

    return {
        "event_id": str(raw.get("event_id", "")),
        "observed_at": str(raw.get("observed_at", "")),
        "window_minutes": int(raw.get("window_minutes", 30)),
        "assets": assets,
        "asset_count": len(assets),
        "expected_sync_type": str(raw.get("expected_sync_type", "unknown")),
        "expected_direction": str(raw.get("expected_direction", "neutral")),
        "expected_primary_assets": raw.get("expected_primary_assets", []),
        "block_reason": str(raw.get("block_reason", "")),
        "note": str(raw.get("note", "")),
        "is_fixture": raw.get("is_fixture", True),
        "data_mode": str(raw.get("data_mode", "fixture")),
    }


def calculate_synchronized_move_score(assets: list[dict]) -> float:
    """Calculate synchronized move score (0-100) for a set of assets.

    The score combines:
      - Magnitude consistency (how similar the moves are in size)
      - Direction agreement (how many move in same direction)
      - Factor confirmation (OI + volume alignment)

    Args:
        assets: List of normalized asset dicts with price_change_pct,
                volume_change_pct, oi_change_pct.

    Returns:
        Synchronized move score from 0 to 100.
    """
    if not assets or len(assets) < 2:
        return 0.0

    n = len(assets)

    # ── 1. Magnitude consistency (Pearson-style similarity) ──────────────────
    price_changes = [a["price_change_pct"] for a in assets]
    abs_changes = [abs(pc) for pc in price_changes]

    mean_abs = sum(abs_changes) / n if n > 0 else 0
    if mean_abs < 1e-10:
        magnitude_score = 0.0
    else:
        # Coefficient of variation: lower = more consistent
        variance = sum((ac - mean_abs) ** 2 for ac in abs_changes) / n
        std_dev = math.sqrt(variance)
        cv = std_dev / mean_abs if mean_abs > 0 else 1.0
        magnitude_score = max(0.0, min(1.0, 1.0 - cv))

    # ── 2. Direction agreement ───────────────────────────────────────────────
    dir_score = calculate_direction_agreement(assets)

    # ── 3. Factor confirmation ───────────────────────────────────────────────
    # Check OI alignment with price direction
    oi_same_direction = 0
    for a in assets:
        pc = a["price_change_pct"]
        oi = a["oi_change_pct"]
        if (pc > 0 and oi > 0) or (pc < 0 and oi < 0):
            oi_same_direction += 1
    oi_ratio = oi_same_direction / n if n > 0 else 0

    # Check volume surge
    vol_avg = sum(a["volume_change_pct"] for a in assets) / n if n > 0 else 0
    vol_surge = min(1.0, vol_avg / 150.0)  # Cap at 150% avg = 1.0

    factor_score = (oi_ratio * 0.5 + vol_surge * 0.5)

    # ── 4. Composite score ───────────────────────────────────────────────────
    composite = magnitude_score * 0.30 + dir_score * 0.40 + factor_score * 0.30
    score = composite * 100.0

    return round(min(100.0, max(0.0, score)), 1)


def calculate_direction_agreement(assets: list[dict]) -> float:
    """Calculate direction agreement ratio (0-1) for a set of assets.

    Measures what fraction of assets agree on the dominant direction.
    Returns 1.0 for perfect agreement, 0.0 for equal split.

    Args:
        assets: List of normalized asset dicts with price_change_pct.

    Returns:
        Direction agreement ratio from 0.0 to 1.0.
    """
    if not assets:
        return 0.0

    up_count = sum(1 for a in assets if a["price_change_pct"] > 0)
    down_count = sum(1 for a in assets if a["price_change_pct"] < 0)
    total = up_count + down_count

    if total == 0:
        return 0.0

    dominant = max(up_count, down_count)
    return round(dominant / total, 3)


def detect_sector_basket_type(assets: list[dict]) -> str:
    """Detect the sector/basket type from a list of normalized assets.

    Returns one of: L1, L2, L1+L2, exchange_token, stablecoin,
    high_beta, defi, meme, mixed, unknown.

    Uses asset symbol heuristics.

    Args:
        assets: List of normalized asset dicts.

    Returns:
        Sector/basket type string.
    """
    if not assets:
        return "unknown"

    names = {a["asset"].upper() for a in assets}
    n = len(names)

    l1_count = len(names & L1_ASSETS)
    l2_count = len(names & L2_ASSETS)
    exchange_count = len(names & EXCHANGE_TOKENS)
    stable_count = len(names & STABLECOINS)
    high_beta_count = len(names & HIGH_BETA)

    # Stablecoin dominated
    if stable_count >= n * 0.5:
        return "stablecoin"

    # Exchange token dominated
    if exchange_count >= n * 0.5:
        return "exchange_token"

    # Mixed L1+L2 (check before pure L2/L1)
    if l1_count > 0 and l2_count > 0:
        return "L1+L2"

    # L2 dominated (>50% are L2 assets)
    if l2_count >= n * 0.5:
        return "L2"

    # L1 dominated
    if l1_count >= n * 0.5:
        return "L1"

    # High beta concentration
    if high_beta_count >= n * 0.5:
        return "high_beta"

    return "mixed"


def classify_sync_type(event: dict) -> str:
    """Classify the sync type of a multi-asset event.

    Uses asset composition, direction, and magnitude to determine
    the most likely sync type.

    Args:
        event: Normalized event dict with assets, direction, sector info.

    Returns:
        Sync type string (one of SYNC_TYPES).
    """
    assets = event.get("assets", [])
    if not assets:
        return "unknown"

    direction = event.get("direction", "neutral")
    sector = event.get("sector", detect_sector_basket_type(assets))
    names = {a["asset"].upper() for a in assets}
    n = len(names)

    # ── Stablecoin liquidity stress ──────────────────────────────────────────
    stable_count = len(names & STABLECOINS)
    if stable_count >= n * 0.5:
        avg_vol = sum(a["volume_change_pct"] for a in assets) / len(assets) if assets else 0
        if avg_vol >= 100:
            return "stablecoin_liquidity_stress"

    # ── Exchange token sync ─────────────────────────────────────────────────
    exchange_count = len(names & EXCHANGE_TOKENS)
    if exchange_count >= n * 0.5:
        return "exchange_token_sync"

    # ── L2 beta sync ─────────────────────────────────────────────────────────
    l2_count = len(names & L2_ASSETS)
    has_eth = "ETH" in names
    if l2_count >= 2 or (has_eth and l2_count >= 1):
        return "l2_beta_sync"

    # ── Market-wide risk-on / risk-off ───────────────────────────────────────
    l1_count = len(names & L1_ASSETS)
    if l1_count >= 2 and direction == "up":
        return "market_wide_risk_on"
    if l1_count >= 2 and direction == "down":
        return "market_wide_risk_off"

    # ── Fallback: direction-based ────────────────────────────────────────────
    if direction == "up" and n >= 2:
        return "market_wide_risk_on"
    if direction == "down" and n >= 2:
        return "market_wide_risk_off"

    return "unknown"


def decide_valid_blocked(event: dict) -> tuple[bool, str | None]:
    """Decide whether a multi-asset event is valid or should be blocked.

    Valid criteria (all must be met):
      - At least 2 assets in same direction
      - Average absolute price change >= 3%, OR average volume_change_pct >= 80%,
        OR average oi_change_pct >= 15%
      - Direction agreement >= 0.66

    Args:
        event: Normalized event dict with computed fields.

    Returns:
        (is_valid: bool, block_reason: str | None)
    """
    assets = event.get("assets", [])

    # ── Asset count check ────────────────────────────────────────────────────
    if len(assets) < 2:
        return False, "insufficient_assets: need at least 2 assets, got {}".format(len(assets))

    # ── Direction agreement check ────────────────────────────────────────────
    dir_agreement = event.get("direction_agreement", calculate_direction_agreement(assets))
    if dir_agreement < 0.66:
        return False, "direction_conflict: direction_agreement={:.2f} < 0.66".format(dir_agreement)

    # ── Movement amplitude check ─────────────────────────────────────────────
    abs_price_changes = [abs(a["price_change_pct"]) for a in assets]
    avg_abs_price = sum(abs_price_changes) / len(abs_price_changes) if abs_price_changes else 0

    avg_volume = sum(a["volume_change_pct"] for a in assets) / len(assets) if assets else 0
    avg_oi = sum(abs(a["oi_change_pct"]) for a in assets) / len(assets) if assets else 0

    price_ok = avg_abs_price >= 3.0
    volume_ok = avg_volume >= 80.0
    oi_ok = avg_oi >= 15.0

    if not (price_ok or volume_ok or oi_ok):
        return False, (
            "small_amplitude: avg_abs_price={:.1f}% (<3%), "
            "avg_volume={:.1f}% (<80%), avg_oi={:.1f}% (<15%)"
        ).format(avg_abs_price, avg_volume, avg_oi)

    return True, None


def render_public_card(event: dict) -> str:
    """Render a clean public card for a multi-asset sync event.

    Public card requirements:
      - sync type
      - direction
      - primary assets
      - window_minutes
      - average price move
      - average volume move
      - average OI move
      - concise reason
      - observed_at

    Forbidden:
      - debug, internal, trace, fixture, secret, token, api_key, chat_id, password
      - absolute local paths

    Args:
        event: Normalized event dict with computed fields.

    Returns:
        Public card text string.
    """
    sync_type = event.get("sync_type", "unknown")
    direction = event.get("direction", "neutral")
    assets = event.get("assets", [])
    window_minutes = event.get("window_minutes", 30)
    observed_at = event.get("observed_at", "")
    sector = event.get("sector", "")
    primary_assets = event.get("primary_assets", [])

    # ── Compute averages ─────────────────────────────────────────────────────
    n = len(assets) if assets else 0
    avg_price = sum(a["price_change_pct"] for a in assets) / n if n > 0 else 0
    avg_volume = sum(a["volume_change_pct"] for a in assets) / n if n > 0 else 0
    avg_oi = sum(a["oi_change_pct"] for a in assets) / n if n > 0 else 0
    total_liq = sum(a["liquidation_usd"] for a in assets) if assets else 0
    sync_score = event.get("sync_score", 0)

    # ── Direction display ────────────────────────────────────────────────────
    if direction == "up":
        dir_icon = "📈"
        dir_text = "同步上涨"
    elif direction == "down":
        dir_icon = "📉"
        dir_text = "同步下跌"
    else:
        dir_icon = "➡️"
        dir_text = "方向不一致"

    # ── Sync type display ───────────────────────────────────────────────────
    type_labels = {
        "market_wide_risk_on": "市场普涨共振",
        "market_wide_risk_off": "市场普跌共振",
        "l2_beta_sync": "L2 高Beta同步",
        "exchange_token_sync": "平台币联动",
        "stablecoin_liquidity_stress": "稳定币流动性压力",
        "unknown": "多资产同步异动",
    }
    type_label = type_labels.get(sync_type, sync_type.replace("_", " ").title())

    # ── Primary assets display ───────────────────────────────────────────────
    if primary_assets:
        primary_str = "、".join(primary_assets[:5])
    else:
        asset_names = [a["asset"] for a in assets[:5]]
        primary_str = "、".join(asset_names)

    # ── Sector info ──────────────────────────────────────────────────────────
    sector_labels = {
        "L1": "Layer 1",
        "L2": "Layer 2",
        "L1+L2": "L1 + L2",
        "exchange_token": "平台币",
        "stablecoin": "稳定币",
        "high_beta": "高Beta",
        "mixed": "混合板块",
    }
    sector_display = sector_labels.get(sector, sector) if sector else ""

    # ── Reason ───────────────────────────────────────────────────────────────
    if sync_score >= 75:
        strength = "强烈"
    elif sync_score >= 50:
        strength = "明显"
    else:
        strength = "初步"

    if sector_display:
        reason = (
            "检测到{sector}板块{n}个资产{dir_text}，"
            "平均涨跌幅{avg_price:+.1f}%，"
            "同步异动得分{sync_score:.0f}分（{strength}），"
            "成交量放大{avg_vol:.0f}%，OI变化{avg_oi:+.1f}%。"
        ).format(
            sector=sector_display, n=n, dir_text=dir_text,
            avg_price=avg_price, sync_score=sync_score,
            strength=strength, avg_vol=avg_volume, avg_oi=avg_oi,
        )
    else:
        reason = (
            "检测到{n}个资产{dir_text}，"
            "平均涨跌幅{avg_price:+.1f}%，"
            "同步异动得分{sync_score:.0f}分（{strength}），"
            "成交量放大{avg_vol:.0f}%，OI变化{avg_oi:+.1f}%。"
        ).format(
            n=n, dir_text=dir_text, avg_price=avg_price,
            sync_score=sync_score, strength=strength,
            avg_vol=avg_volume, avg_oi=avg_oi,
        )

    # ── Build card ───────────────────────────────────────────────────────────
    lines = [
        "{dir_icon} 多资产共振｜{type_label} {n}个资产".format(
            dir_icon=dir_icon, type_label=type_label, n=n,
        ),
        "",
        "一句话：{reason}".format(reason=reason),
        "",
        "● 共振类型：{type_label}".format(type_label=type_label),
        "● 方向：{dir_text}".format(dir_text=dir_text),
        "● 主要资产：{primary}".format(primary=primary_str),
        "● 观测窗口：{w}分钟".format(w=window_minutes),
        "● 平均涨跌幅：{avg_price:+.2f}%".format(avg_price=avg_price),
        "● 平均成交量变化：{avg_vol:+.1f}%".format(avg_vol=avg_volume),
        "● 平均OI变化：{avg_oi:+.2f}%".format(avg_oi=avg_oi),
        "● 同步异动得分：{score:.0f}/100".format(score=sync_score),
    ]

    if total_liq > 0:
        lines.append(
            "● 总清算金额：{liq}".format(liq=_fmt_money(total_liq))
        )

    if sector_display:
        lines.append("● 板块：{s}".format(s=sector_display))

    lines.extend([
        "",
        "🕐 观测时间：{ts}".format(ts=observed_at),
        "",
    ])

    # ── Links ────────────────────────────────────────────────────────────────
    if assets:
        first_asset = assets[0]["asset"]
        lines.append(
            "🔗 行情查看：CoinGecko / DexScreener（{a}）".format(a=first_asset)
        )
    lines.append("")

    lines.append("💡 触发原因：{reason}".format(reason=reason))
    lines.append("")
    lines.append("⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。")

    return "\n".join(lines)


def check_debug_leak(text: str) -> list[str]:
    """Check text for debug/internal/trace/fixture terms.

    Args:
        text: Text to check.

    Returns:
        List of forbidden debug terms found.
    """
    if not text:
        return []

    forbidden = [
        "debug", "internal", "trace", "fixture",
        "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
        "payload_render", "format_check", "content_quality",
        "价值:", "冷却:", "pre_send:", "allow", "upgrade_override",
        "not_reached", "mock_sent", "mock_message_id",
        "gate_decision", "score↑", "blocked_by", "gate_version",
        "factor_hits", "block_reason", "block:", "observe",
    ]

    found: list[str] = []
    text_lower = text.lower()
    for term in forbidden:
        if term.lower() in text_lower:
            found.append(term)
    return found


def check_secret_leak(text: str) -> list[str]:
    """Check text for secret/token/key/password/chat_id terms.

    Args:
        text: Text to check.

    Returns:
        List of forbidden secret terms found.
    """
    if not text:
        return []

    forbidden = [
        "secret", "token", "api_key", "chat_id", "password",
    ]

    found: list[str] = []
    text_lower = text.lower()
    for term in forbidden:
        if term.lower() in text_lower:
            found.append(term)

    # Check for absolute paths
    if re.search(r'[A-Za-z]:\\(?:Users|Program|Windows)', text):
        found.append("local_absolute_path")

    return found


def process_snapshot(raw: dict) -> dict:
    """Process a raw snapshot through the full v112g pipeline.

    Pipeline:
      1. Normalize snapshot
      2. Calculate direction agreement
      3. Calculate synchronized move score
      4. Detect sector/basket
      5. Determine direction
      6. Classify sync type
      7. Decide valid/blocked
      8. Render public card (if valid)
      9. Check debug/secret leaks

    Args:
        raw: Raw snapshot dict from fixture.

    Returns:
        Dict with all processing results.
    """
    # ── 1. Normalize ─────────────────────────────────────────────────────────
    event = normalize_snapshot(raw)
    assets = event["assets"]

    # ── 2. Direction agreement ───────────────────────────────────────────────
    dir_agreement = calculate_direction_agreement(assets)
    event["direction_agreement"] = dir_agreement

    # ── 3. Synchronized move score ───────────────────────────────────────────
    sync_score = calculate_synchronized_move_score(assets)
    event["sync_score"] = sync_score

    # ── 4. Sector / Basket detection ─────────────────────────────────────────
    sector = detect_sector_basket_type(assets)
    event["sector"] = sector

    # ── 5. Determine direction ───────────────────────────────────────────────
    up_count = sum(1 for a in assets if a["price_change_pct"] > 0)
    down_count = sum(1 for a in assets if a["price_change_pct"] < 0)
    if up_count > down_count:
        direction = "up"
    elif down_count > up_count:
        direction = "down"
    else:
        direction = "neutral"
    event["direction"] = direction

    # ── 6. Primary assets ────────────────────────────────────────────────────
    # Sort by absolute price change, take top
    sorted_assets = sorted(assets, key=lambda a: abs(a["price_change_pct"]), reverse=True)
    primary = [a["asset"] for a in sorted_assets[:3]]
    event["primary_assets"] = primary

    # ── 7. Classify sync type ────────────────────────────────────────────────
    sync_type = classify_sync_type(event)
    event["sync_type"] = sync_type

    # ── Compute asset-level averages ─────────────────────────────────────────
    n = len(assets) if assets else 0
    event["avg_price_change"] = round(sum(a["price_change_pct"] for a in assets) / n, 2) if n > 0 else 0.0
    event["avg_volume_change"] = round(sum(a["volume_change_pct"] for a in assets) / n, 2) if n > 0 else 0.0
    event["avg_oi_change"] = round(sum(a["oi_change_pct"] for a in assets) / n, 2) if n > 0 else 0.0
    event["max_price_change"] = round(max((a["price_change_pct"] for a in assets), default=0), 2)
    event["min_price_change"] = round(min((a["price_change_pct"] for a in assets), default=0), 2)

    # ── 8. Decide valid/blocked ──────────────────────────────────────────────
    is_valid, block_reason = decide_valid_blocked(event)
    event["valid"] = is_valid
    event["blocked"] = not is_valid
    event["block_reason"] = block_reason

    # ── 9. Render public card ────────────────────────────────────────────────
    public_card = ""
    if is_valid:
        public_card = render_public_card(event)
    event["public_card"] = public_card

    # ── 10. Debug / Secret leak check ────────────────────────────────────────
    debug_terms = check_debug_leak(public_card)
    secret_terms = check_secret_leak(public_card)
    event["debug_leak_terms"] = debug_terms
    event["secret_leak_terms"] = secret_terms
    event["debug_leak_count"] = len(debug_terms)
    event["secret_leak_count"] = len(secret_terms)
    event["clean"] = len(debug_terms) == 0 and len(secret_terms) == 0

    # ── 11. Safety flags ─────────────────────────────────────────────────────
    event["real_tg_sent"] = False
    event["external_api_called"] = False
    event["external_ai_called"] = False
    event["daemon_started"] = False
    event["live_ready"] = False

    return event


# ══════════════════════════════════════════════════════════════════════════════════════
# Private Helpers
# ══════════════════════════════════════════════════════════════════════════════════════

def _safe_float(value, default: float = 0.0) -> float:
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


def _fmt_money(value: float) -> str:
    """Format USD amount in human-readable form."""
    v = abs(value)
    sign = "-" if value < 0 else ""
    if v >= 1_000_000_000:
        return f"{sign}${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{sign}${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{sign}${v/1_000:.2f}K"
    if 0 < v < 0.01:
        return f"{sign}${v:.6f}"
    return f"{sign}${v:,.2f}"
