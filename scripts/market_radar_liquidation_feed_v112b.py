"""Market Radar v1.12-B — Liquidation Pressure Local Feed Adapter 清算数据适配层

Provides a vendor-neutral liquidation data normalization layer, pressure detection,
public card rendering, and validation — all working from local fixtures without
any external API calls.

Design principle:
  Ingestion shape does not matter (Coinglass, exchange feed, local snapshot).
  Normalize → Detect → Render → Validate.
  All samples are explicitly tagged with data_mode.

Classes:
  LiquidationSnapshot       — normalized input record
  LiquidationCluster        — price zone with liquidation density
  LiquidationPressureSignal — detected pressure output

Functions:
  normalize_liquidation_snapshot(raw) → LiquidationSnapshot
  detect_liquidation_pressure(snapshot) → LiquidationPressureSignal | None
  render_liquidation_pressure_card(signal) → str
  validate_liquidation_signal(signal) → dict

Security:
  - Does NOT read / print / save any token, chat_id, key, cookie, or password.
  - Does NOT access environment variables for credentials.
  - Does NOT make network calls.
  - Does NOT call Coinglass or any paid API.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any

VERSION = "v1.12-B"
MODE = "liquidation_pressure_local_feed"

CN_TZ = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class LiquidationCluster:
    """A price zone where liquidations are concentrated."""
    price_low: float = 0.0
    price_high: float = 0.0
    liquidation_usd: float = 0.0
    direction: str = ""  # "long" | "short" | "both"


@dataclass
class LiquidationSnapshot:
    """Normalized liquidation snapshot for a single asset at a point in time.

    This is the canonical input shape — regardless of whether the raw data
    came from Coinglass, an exchange websocket, or a local CSV.
    """
    data_mode: str = "fixture"       # fixture | local_snapshot | live
    source: str = "local_fixture"    # local_fixture | coinglass_placeholder | exchange_placeholder
    asset: str = ""                  # BTC, ETH, SOL, ...
    timestamp_utc: str = ""          # ISO-8601 UTC
    price: float = 0.0               # Current market price in USD
    long_liquidation_usd_1h: float = 0.0
    short_liquidation_usd_1h: float = 0.0
    long_liquidation_usd_24h: float = 0.0
    short_liquidation_usd_24h: float = 0.0
    liquidation_cluster_above: list[LiquidationCluster] = field(default_factory=list)
    liquidation_cluster_below: list[LiquidationCluster] = field(default_factory=list)
    open_interest_usd: float = 0.0
    volume_24h_usd: float = 0.0

    def to_dict(self) -> dict:
        return {
            "data_mode": self.data_mode,
            "source": self.source,
            "asset": self.asset,
            "timestamp_utc": self.timestamp_utc,
            "price": self.price,
            "long_liquidation_usd_1h": self.long_liquidation_usd_1h,
            "short_liquidation_usd_1h": self.short_liquidation_usd_1h,
            "long_liquidation_usd_24h": self.long_liquidation_usd_24h,
            "short_liquidation_usd_24h": self.short_liquidation_usd_24h,
            "liquidation_cluster_above": [asdict(c) for c in self.liquidation_cluster_above],
            "liquidation_cluster_below": [asdict(c) for c in self.liquidation_cluster_below],
            "open_interest_usd": self.open_interest_usd,
            "volume_24h_usd": self.volume_24h_usd,
        }


@dataclass
class LiquidationPressureSignal:
    """Detected liquidation pressure signal, ready for card rendering.

    pressure_type:
      - "long_liquidation_pressure"  — below price, long liq dominant
      - "short_liquidation_pressure" — above price, short liq dominant
      - "two_sided_liquidation_pressure" — clusters both sides
    """
    data_mode: str = "fixture"
    source: str = "local_fixture"
    asset: str = ""
    timestamp_utc: str = ""
    price: float = 0.0
    pressure_type: str = ""              # see docstring
    long_liquidation_usd_1h: float = 0.0
    short_liquidation_usd_1h: float = 0.0
    long_liquidation_usd_24h: float = 0.0
    short_liquidation_usd_24h: float = 0.0
    total_liquidation_usd_1h: float = 0.0
    cluster_above_total_usd: float = 0.0
    cluster_below_total_usd: float = 0.0
    open_interest_usd: float = 0.0
    volume_24h_usd: float = 0.0
    live_ready: bool = False
    blocked: bool = False
    block_reason: str = ""
    trigger_description: str = ""

    def to_dict(self) -> dict:
        return {
            "data_mode": self.data_mode,
            "source": self.source,
            "asset": self.asset,
            "timestamp_utc": self.timestamp_utc,
            "price": self.price,
            "pressure_type": self.pressure_type,
            "long_liquidation_usd_1h": self.long_liquidation_usd_1h,
            "short_liquidation_usd_1h": self.short_liquidation_usd_1h,
            "long_liquidation_usd_24h": self.long_liquidation_usd_24h,
            "short_liquidation_usd_24h": self.short_liquidation_usd_24h,
            "total_liquidation_usd_1h": self.total_liquidation_usd_1h,
            "cluster_above_total_usd": self.cluster_above_total_usd,
            "cluster_below_total_usd": self.cluster_below_total_usd,
            "open_interest_usd": self.open_interest_usd,
            "volume_24h_usd": self.volume_24h_usd,
            "live_ready": self.live_ready,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "trigger_description": self.trigger_description,
        }


# ══════════════════════════════════════════════════════════════════════════════════════
# Normalize
# ══════════════════════════════════════════════════════════════════════════════════════

def normalize_liquidation_snapshot(raw: dict) -> LiquidationSnapshot:
    """Normalize a raw liquidation data dict into a LiquidationSnapshot.

    Handles multiple possible field names from different sources.
    Always produces the canonical shape regardless of input format.
    """
    def _f(key, default=0.0):
        """Safe float extractor."""
        val = raw.get(key)
        if val is None:
            return default
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return float(val)
        if isinstance(val, str):
            s = val.strip().replace("$", "").replace(",", "").replace("%", "").strip()
            try:
                return float(s)
            except (ValueError, TypeError):
                return default
        return default

    def _s(key, default=""):
        """Safe string extractor."""
        val = raw.get(key, default)
        if val is None:
            return default
        return str(val).strip()

    # Cluster extraction
    clusters_above_raw = raw.get("liquidation_cluster_above", [])
    if not isinstance(clusters_above_raw, list):
        clusters_above_raw = []
    clusters_below_raw = raw.get("liquidation_cluster_below", [])
    if not isinstance(clusters_below_raw, list):
        clusters_below_raw = []

    def _parse_clusters(raw_list: list) -> list[LiquidationCluster]:
        result = []
        for item in raw_list:
            if isinstance(item, dict):
                result.append(LiquidationCluster(
                    price_low=_f("price_low", 0.0) if "price_low" in item else _f("low", 0.0),
                    price_high=_f("price_high", 0.0) if "price_high" in item else _f("high", 0.0),
                    liquidation_usd=_f("liquidation_usd", 0.0) if "liquidation_usd" in item else _f("liq_usd", 0.0),
                    direction=_s("direction", ""),
                ))
        return result

    return LiquidationSnapshot(
        data_mode=_s("data_mode", "fixture"),
        source=_s("source", "local_fixture"),
        asset=_s("asset", "").upper(),
        timestamp_utc=_s("timestamp_utc", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        price=_f("price", 0.0),
        long_liquidation_usd_1h=_f("long_liquidation_usd_1h", 0.0),
        short_liquidation_usd_1h=_f("short_liquidation_usd_1h", 0.0),
        long_liquidation_usd_24h=_f("long_liquidation_usd_24h", 0.0),
        short_liquidation_usd_24h=_f("short_liquidation_usd_24h", 0.0),
        liquidation_cluster_above=_parse_clusters(clusters_above_raw),
        liquidation_cluster_below=_parse_clusters(clusters_below_raw),
        open_interest_usd=_f("open_interest_usd", 0.0),
        volume_24h_usd=_f("volume_24h_usd", 0.0),
    )


# ══════════════════════════════════════════════════════════════════════════════════════
# Detect Liquidation Pressure
# ══════════════════════════════════════════════════════════════════════════════════════

# Thresholds (tunable)
LONG_LIQ_1H_HIGH = 5_000_000    # $5M+ in 1h → significant long liquidation
SHORT_LIQ_1H_HIGH = 5_000_000   # $5M+ in 1h → significant short liquidation
CLUSTER_MIN_USD = 1_000_000     # $1M+ in a cluster → notable
LIQ_1H_LOW_THRESHOLD = 500_000  # Below $500k total 1h → low signal
TWO_SIDED_RATIO = 0.3           # If both sides > 30% of the larger side → two-sided


def detect_liquidation_pressure(snapshot: LiquidationSnapshot) -> LiquidationPressureSignal | None:
    """Detect liquidation pressure from a normalized snapshot.

    Returns a LiquidationPressureSignal if pressure is detected, or None if
    the snapshot should be blocked (no meaningful signal).

    Block conditions (returns None):
      - asset is empty
      - price <= 0
      - all liquidation amounts == 0
      - clusters are empty AND 1h liquidation is low
    """
    # ── Block checks ──────────────────────────────────────────────────────
    if not snapshot.asset or len(snapshot.asset.strip()) == 0:
        return None  # caller should wrap with blocked=True

    if snapshot.price <= 0:
        return None

    total_liq_1h = snapshot.long_liquidation_usd_1h + snapshot.short_liquidation_usd_1h
    total_liq_24h = snapshot.long_liquidation_usd_24h + snapshot.short_liquidation_usd_24h
    has_clusters = len(snapshot.liquidation_cluster_above) > 0 or len(snapshot.liquidation_cluster_below) > 0

    if total_liq_1h == 0 and total_liq_24h == 0 and not has_clusters:
        return None

    if not has_clusters and total_liq_1h < LIQ_1H_LOW_THRESHOLD:
        return None

    # ── Cluster totals ────────────────────────────────────────────────────
    cluster_above_total = sum(c.liquidation_usd for c in snapshot.liquidation_cluster_above)
    cluster_below_total = sum(c.liquidation_usd for c in snapshot.liquidation_cluster_below)

    # ── Pressure type detection ───────────────────────────────────────────
    long_dominant = snapshot.long_liquidation_usd_1h >= LONG_LIQ_1H_HIGH or cluster_below_total >= CLUSTER_MIN_USD
    short_dominant = snapshot.short_liquidation_usd_1h >= SHORT_LIQ_1H_HIGH or cluster_above_total >= CLUSTER_MIN_USD

    # Two-sided: both sides have significant clusters
    if long_dominant and short_dominant:
        pressure_type = "two_sided_liquidation_pressure"
        trigger = (
            f"{snapshot.asset} 上下方均存在清算密集区，"
            f"下方多头清算 {_fmt_money(cluster_below_total)}，"
            f"上方空头清算 {_fmt_money(cluster_above_total)}，"
            f"双向波动风险升高。"
        )
    elif long_dominant:
        pressure_type = "long_liquidation_pressure"
        trigger = (
            f"{snapshot.asset} 下方多头清算压力升高，"
            f"近1h 多头清算 {_fmt_money(snapshot.long_liquidation_usd_1h)}，"
            f"下方清算密集区 {_fmt_money(cluster_below_total)}，"
            f"若价格继续回落可能放大短线波动。"
        )
    elif short_dominant:
        pressure_type = "short_liquidation_pressure"
        trigger = (
            f"{snapshot.asset} 上方空头清算压力升高，"
            f"近1h 空头清算 {_fmt_money(snapshot.short_liquidation_usd_1h)}，"
            f"上方清算密集区 {_fmt_money(cluster_above_total)}，"
            f"若价格上行可能引发空头踩踏。"
        )
    else:
        # Has some liquidation but not enough to classify — weak signal
        pressure_type = "long_liquidation_pressure" if snapshot.long_liquidation_usd_1h > snapshot.short_liquidation_usd_1h else "short_liquidation_pressure"
        dominant_side = "多头" if pressure_type == "long_liquidation_pressure" else "空头"
        trigger = f"{snapshot.asset} {dominant_side}清算略有升高，但尚未达到显著压力阈值，保持观察。"

    # ── live_ready flag ───────────────────────────────────────────────────
    live_ready = snapshot.data_mode != "fixture"

    return LiquidationPressureSignal(
        data_mode=snapshot.data_mode,
        source=snapshot.source,
        asset=snapshot.asset,
        timestamp_utc=snapshot.timestamp_utc,
        price=snapshot.price,
        pressure_type=pressure_type,
        long_liquidation_usd_1h=snapshot.long_liquidation_usd_1h,
        short_liquidation_usd_1h=snapshot.short_liquidation_usd_1h,
        long_liquidation_usd_24h=snapshot.long_liquidation_usd_24h,
        short_liquidation_usd_24h=snapshot.short_liquidation_usd_24h,
        total_liquidation_usd_1h=total_liq_1h,
        cluster_above_total_usd=cluster_above_total,
        cluster_below_total_usd=cluster_below_total,
        open_interest_usd=snapshot.open_interest_usd,
        volume_24h_usd=snapshot.volume_24h_usd,
        live_ready=live_ready,
        blocked=False,
        block_reason="",
        trigger_description=trigger,
    )


# ══════════════════════════════════════════════════════════════════════════════════════
# Validate
# ══════════════════════════════════════════════════════════════════════════════════════

def validate_liquidation_signal(signal: LiquidationPressureSignal) -> dict:
    """Validate a liquidation pressure signal against block rules.

    Returns a dict with:
      - valid: bool
      - blocked: bool
      - block_reason: str
      - warnings: list[str]
      - live_ready: bool
      - data_mode_ok: bool
    """
    warnings: list[str] = []

    # Block rule 1: missing asset
    if not signal.asset or len(signal.asset.strip()) == 0:
        return {
            "valid": False, "blocked": True,
            "block_reason": "缺少 asset 字段",
            "warnings": warnings, "live_ready": False, "data_mode_ok": True,
        }

    # Block rule 2: price <= 0
    if signal.price <= 0:
        return {
            "valid": False, "blocked": True,
            "block_reason": "price <= 0，无法判断清算压力",
            "warnings": warnings, "live_ready": False, "data_mode_ok": True,
        }

    # Block rule 3: all liquidation amounts == 0
    total_liq = (
        signal.long_liquidation_usd_1h + signal.short_liquidation_usd_1h +
        signal.long_liquidation_usd_24h + signal.short_liquidation_usd_24h +
        signal.cluster_above_total_usd + signal.cluster_below_total_usd
    )
    if total_liq == 0:
        return {
            "valid": False, "blocked": True,
            "block_reason": "清算金额全部为 0，无有效数据",
            "warnings": warnings, "live_ready": False, "data_mode_ok": True,
        }

    # Block rule 4: cluster empty AND 1h liq low
    has_clusters = signal.cluster_above_total_usd > 0 or signal.cluster_below_total_usd > 0
    if not has_clusters and signal.total_liquidation_usd_1h < LIQ_1H_LOW_THRESHOLD:
        return {
            "valid": False, "blocked": True,
            "block_reason": f"清算集群为空且 1h 清算金额 ${signal.total_liquidation_usd_1h:,.0f} 低于阈值 ${LIQ_1H_LOW_THRESHOLD:,.0f}",
            "warnings": warnings, "live_ready": False, "data_mode_ok": True,
        }

    # Block rule 5: fixture must not be live_ready
    data_mode_ok = True
    if signal.data_mode == "fixture" and signal.live_ready:
        warnings.append("fixture 样本被标记为 live_ready，已自动修正")
        signal.live_ready = False
        data_mode_ok = False

    return {
        "valid": True,
        "blocked": False,
        "block_reason": "",
        "warnings": warnings,
        "live_ready": signal.live_ready,
        "data_mode_ok": data_mode_ok,
    }


# ══════════════════════════════════════════════════════════════════════════════════════
# Render Public Card
# ══════════════════════════════════════════════════════════════════════════════════════

# Forbidden terms in public output
PUBLIC_FORBIDDEN_TERMS = [
    "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
    "payload_render", "format_check", "content_quality",
    "admission", "block_rules", "data_mode", "fixture",
    "mock", "debug", "live_ready",
]


def render_liquidation_pressure_card(signal: LiquidationPressureSignal) -> str:
    """Render a human-readable public card for a liquidation pressure signal.

    The output MUST NOT contain any internal field names, gate terms, or
    debug identifiers. It should read like a public market observer note.
    """
    asset = signal.asset or "Unknown"
    price = signal.price

    # ── Pressure type → human description ────────────────────────────────
    type_map = {
        "long_liquidation_pressure": "多头清算压力",
        "short_liquidation_pressure": "空头清算压力",
        "two_sided_liquidation_pressure": "双向清算密集",
    }
    pressure_label = type_map.get(signal.pressure_type, "清算压力")

    lines = [f"⚠️ 清算压力｜{asset}", ""]

    # 一句话
    lines.append(f"一句话：{signal.trigger_description}")
    lines.append("")

    # 关键数据
    if price > 0:
        lines.append(f"● 当前价格：{_fmt_price(price)}")
    if signal.long_liquidation_usd_1h > 0:
        lines.append(f"● 近 1h 多头清算：{_fmt_money(signal.long_liquidation_usd_1h)}")
    if signal.short_liquidation_usd_1h > 0:
        lines.append(f"● 近 1h 空头清算：{_fmt_money(signal.short_liquidation_usd_1h)}")
    if signal.long_liquidation_usd_24h > 0:
        lines.append(f"● 近 24h 多头清算：{_fmt_money(signal.long_liquidation_usd_24h)}")
    if signal.short_liquidation_usd_24h > 0:
        lines.append(f"● 近 24h 空头清算：{_fmt_money(signal.short_liquidation_usd_24h)}")

    # Cluster zones
    if signal.cluster_below_total_usd > 0:
        lines.append(f"● 下方清算密集区：{_fmt_money(signal.cluster_below_total_usd)}")
    if signal.cluster_above_total_usd > 0:
        lines.append(f"● 上方清算密集区：{_fmt_money(signal.cluster_above_total_usd)}")

    if signal.open_interest_usd > 0:
        lines.append(f"● 未平仓合约：{_fmt_money(signal.open_interest_usd)}")
    if signal.volume_24h_usd > 0:
        lines.append(f"● 24h 成交量：{_fmt_money(signal.volume_24h_usd)}")

    # Observation window
    obs_window = "1-4 小时" if signal.pressure_type != "two_sided_liquidation_pressure" else "2-6 小时"
    lines.append(f"● 观察窗口：{obs_window}")
    lines.append("")

    # Trigger reason
    lines.append(f"💡 触发原因：{signal.trigger_description}")
    lines.append("")

    # Disclaimer
    lines.append("⚠️ 仅供观察，不构成交易建议。")

    return "\n".join(lines)


def check_public_debug_leak(text: str) -> list[str]:
    """Check rendered public text for forbidden internal/debug terms.

    Returns a list of any forbidden terms found.
    """
    found: list[str] = []
    text_lower = text.lower()
    for term in PUBLIC_FORBIDDEN_TERMS:
        if term.lower() in text_lower:
            found.append(term)
    return found


# ══════════════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════════════

def _fmt_money(value: float) -> str:
    """Format USD value in human-readable form."""
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
        return f"${value:,.2f}"
    if v >= 1:
        return f"${value:.2f}"
    return f"${value:.6f}"


# ══════════════════════════════════════════════════════════════════════════════════════
# Convenience: process a raw dict end-to-end
# ══════════════════════════════════════════════════════════════════════════════════════

def process_raw_snapshot(raw: dict) -> dict:
    """End-to-end: normalize → detect → validate → render.

    Returns a dict suitable for the runner's result aggregation.
    """
    snapshot = normalize_liquidation_snapshot(raw)

    # Pre-checks for block reasons before detection
    if not snapshot.asset or len(snapshot.asset.strip()) == 0:
        return {
            "sample_id": raw.get("sample_id", "unknown"),
            "data_mode": snapshot.data_mode,
            "asset": "",
            "snapshot": snapshot.to_dict(),
            "signal": None,
            "blocked": True,
            "block_reason": "缺少 asset 字段",
            "public_card": "",
            "debug_leak_terms": [],
            "debug_leak_free": True,
        }

    if snapshot.price <= 0:
        return {
            "sample_id": raw.get("sample_id", "unknown"),
            "data_mode": snapshot.data_mode,
            "asset": snapshot.asset,
            "snapshot": snapshot.to_dict(),
            "signal": None,
            "blocked": True,
            "block_reason": "price <= 0，无法判断清算压力",
            "public_card": "",
            "debug_leak_terms": [],
            "debug_leak_free": True,
        }

    total_liq = (
        snapshot.long_liquidation_usd_1h + snapshot.short_liquidation_usd_1h +
        snapshot.long_liquidation_usd_24h + snapshot.short_liquidation_usd_24h
    )
    has_clusters = len(snapshot.liquidation_cluster_above) > 0 or len(snapshot.liquidation_cluster_below) > 0

    if total_liq == 0 and not has_clusters:
        return {
            "sample_id": raw.get("sample_id", "unknown"),
            "data_mode": snapshot.data_mode,
            "asset": snapshot.asset,
            "snapshot": snapshot.to_dict(),
            "signal": None,
            "blocked": True,
            "block_reason": "清算金额全部为 0，无有效数据",
            "public_card": "",
            "debug_leak_terms": [],
            "debug_leak_free": True,
        }

    # Detect
    signal = detect_liquidation_pressure(snapshot)

    if signal is None:
        return {
            "sample_id": raw.get("sample_id", "unknown"),
            "data_mode": snapshot.data_mode,
            "asset": snapshot.asset,
            "snapshot": snapshot.to_dict(),
            "signal": None,
            "blocked": True,
            "block_reason": "检测后未产生有效信号（清算数据不足或未达阈值）",
            "public_card": "",
            "debug_leak_terms": [],
            "debug_leak_free": True,
        }

    # Validate
    validation = validate_liquidation_signal(signal)

    # Render
    public_card = ""
    debug_leak_terms: list[str] = []
    if not validation["blocked"]:
        public_card = render_liquidation_pressure_card(signal)
        debug_leak_terms = check_public_debug_leak(public_card)

    return {
        "sample_id": raw.get("sample_id", "unknown"),
        "data_mode": signal.data_mode,
        "asset": signal.asset,
        "snapshot": snapshot.to_dict(),
        "signal": signal.to_dict(),
        "blocked": validation["blocked"],
        "block_reason": validation["block_reason"],
        "public_card": public_card,
        "debug_leak_terms": debug_leak_terms,
        "debug_leak_free": len(debug_leak_terms) == 0,
        "live_ready": validation["live_ready"],
        "data_mode_ok": validation["data_mode_ok"],
    }
