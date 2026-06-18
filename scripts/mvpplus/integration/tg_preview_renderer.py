"""Telegram staging preview renderer — hardened one-shot card builder.

Fixes applied:
  1. telegram_call() error desensitization — no token leak, safe UTF-8
  2. Merge same-position alerts into one main card with risk tags
  3. Remove per-source health detail from public card
  4. Dynamic garbled gate — REQUIRED_CHINESE_MARKERS adapts to card type
  5. No risk recalculation — consume domain output only
  6. Address handling for both full and already-short addresses
  7. Uniform USD formatting

Usage (server):
    python scripts/mvpplus/integration/tg_preview_renderer.py \
        --run-dir /path/to/output \
        --channel-id -1003993870683

Outputs:
    stdout:      JSON with preview_text and gate verdict
    --send:      Actually sends via Telegram (requires TELEGRAM_BOT_TOKEN env)
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ── Garbled text gate (dynamic) ──────────────────────────────────────────

# Core universal markers — every card must have these
UNIVERSAL_REQUIRED = [
    "数据来源",
    "数据时间",
]

# Position-specific markers — only required when positions exist
POSITION_REQUIRED = [
    "开仓价",
    "当前标记价",
    "清算价",
    "距清算价",
    "未实现",
]

# Alert/risk markers — only required when alert candidates exist
RISK_REQUIRED = [
    "风险标记",
]

WHALE_HEADER_MARKERS = [
    "鲸鱼报警",
    "大额杠杆",
]


def get_required_markers(
    has_positions: bool = False,
    has_alerts: bool = False,
    has_whale_data: bool = False,
) -> list[str]:
    """Build REQUIRED_CHINESE_MARKERS dynamically based on card content."""
    markers = list(UNIVERSAL_REQUIRED)
    if has_whale_data:
        markers.append("大额杠杆")
    if has_positions:
        markers.extend(POSITION_REQUIRED)
    if has_alerts:
        markers.append("风险标记")
    return markers


def check_garbled(text: str, markers: Optional[list[str]] = None) -> list[str]:
    """Check text for garbled/truncated content. Returns violations list."""
    violations: list[str] = []
    if not text or not text.strip():
        violations.append("text is empty")
        return violations
    if re.search(r"\?{3,}", text):
        violations.append("text contains 3+ consecutive '?' — garbled encoding")
    if "�" in text:
        violations.append("text contains Unicode replacement character (U+FFFD)")
    for marker in (markers or UNIVERSAL_REQUIRED):
        if marker not in text:
            violations.append(f"required Chinese text missing: {marker}")
    return violations


# ── Liquidation distance display ────────────────────────────────────────

MAX_SANE_PCT = 1000.0


def format_liquidation_distance(
    direction: str,
    mark_price: Optional[float],
    liquidation_price: Optional[float],
) -> str:
    """User-facing liquidation distance: always positive buffer percent."""
    if mark_price is None or liquidation_price is None:
        return "暂无数据"
    if mark_price <= 0:
        return "暂无数据"

    if direction == "long":
        raw = (mark_price - liquidation_price) / mark_price * 100
    elif direction == "short":
        raw = (liquidation_price - mark_price) / mark_price * 100
    else:
        return "暂无数据"

    if raw <= 0:
        return "已达到或越过理论清算价 — 请关注"
    if raw > MAX_SANE_PCT:
        return f"{raw:.1f}%"
    return f"{raw:.1f}%"


def format_amount_usd(value: Optional[float]) -> str:
    """Short-scale USD formatting — uniform sign handling."""
    if value is None:
        return "暂无数据"
    abs_val = abs(value)
    prefix = "-" if value < 0 else ""
    if abs_val >= 1_000_000_000:
        return f"{prefix}${abs_val / 1_000_000_000:.1f}B"
    elif abs_val >= 1_000_000:
        return f"{prefix}${abs_val / 1_000_000:.1f}M"
    elif abs_val >= 1_000:
        return f"{prefix}${abs_val / 1_000:.0f}K"
    else:
        return f"{prefix}${value:,.0f}"


def shorten_address(address: str) -> str:
    """Safely shorten an EVM address or pass through already-short form.

    Full 42-char EVM address: 0x6c8512...84f6
    Already shortened: pass through unchanged.
    """
    if not address:
        return ""
    if len(address) <= 12:
        return address
    # If already contains ellipsis, assume already shortened
    if "…" in address or "..." in address:
        return address
    return address[:8] + "…" + address[-4:]


# ── Chinese label maps (consuming domain output, not recalculating) ─────

RISK_LABELS: dict[str, str] = {
    "high_leverage": "高杠杆持仓",
    "concentrated_exposure": "集中持仓风险",
    "large_new_position": "新建大额仓位",
    "large_increase": "仓位大幅增加",
    "large_decrease": "仓位大幅减少",
    "direction_flip": "方向反转",
    "liquidation_critical": "清算接近临界",
}

SEVERITY_LABELS: dict[str, str] = {
    "critical": "严重",
    "high": "高",
    "medium": "中",
    "low": "低",
}


# ── Card builder ────────────────────────────────────────────────────────

def _collect_risk_tags(candidates: list[dict]) -> tuple[list[str], list[str]]:
    """Extract risk tags and severity labels from alert_candidates.

    This is a pure mapping — it does NOT recalculate or invent risks.
    Unknown alert_types are silently skipped; no synthetic risk is created.
    """
    tags: list[str] = []
    severities: list[str] = []
    seen_types: set[str] = set()
    for c in candidates:
        atype = c.get("alert_type", "")
        if atype and atype not in seen_types:
            seen_types.add(atype)
            cn = RISK_LABELS.get(atype)
            if cn:
                tags.append(cn)
            sev = c.get("severity", "")
            if sev and sev not in severities:
                severities.append(sev)
    return tags, severities


def build_preview_card(
    whale_data: dict[str, Any],
    market_data: Optional[list[dict]] = None,
    run_data: Optional[dict] = None,
) -> str:
    """Build Telegram preview card from real run output data.

    All Chinese text is native UTF-8 (this file is UTF-8 in git).
    Caller must use ensure_ascii=False when serializing.

    Principles:
      - Same-position alerts merge into one main card
      - Source health detail is NOT shown in public card
      - Risk labels come from domain alert_candidates, not recalculation
    """
    lines: list[str] = []
    lines.append("\U0001f40b Crypto Signal Intelligence OS — Staging \U0001f9ea")
    lines.append("")

    # Prefer delivery_candidates (alert-state filtered), fallback to raw
    candidates = whale_data.get("delivery_candidates",
                                whale_data.get("alert_candidates", []))
    positions = whale_data.get("positions", [])

    # ── Position section (one main card, not per-alert) ─────────────────
    if positions:
        pos = positions[0]
        coin = pos.get("coin", "")
        direction = pos.get("direction", "long")
        signed_size = pos.get("signed_size", 0) or 0
        abs_size = abs(signed_size)
        entry_price = pos.get("entry_price")
        mark_price = pos.get("mark_price")
        leverage = pos.get("leverage")
        pnl = pos.get("unrealized_pnl_usd")
        liq_price = pos.get("liquidation_price")
        liq_dist = format_liquidation_distance(direction, mark_price, liq_price)
        pos_value = pos.get("position_value_usd")
        address = pos.get("address") or pos.get("address_short", "")
        label = pos.get("label", "")
        addr_display = shorten_address(address)

        dir_cn = "多头" if direction == "long" else "空头"
        lines.append(f"\U0001f40b {coin} 大额杠杆{dir_cn}")

        if label:
            lines.append(f"地址：{label}（{addr_display}）")
        else:
            lines.append(f"地址：{addr_display}")
        lines.append(f"规模：{abs_size:,.0f} {coin}（约 {format_amount_usd(pos_value)}）")
        if leverage:
            lines.append(f"杠杆：{leverage}x")
        if entry_price:
            lines.append(f"开仓价：${entry_price:,.2f}")
        if mark_price:
            lines.append(f"当前标记价：${mark_price:,.2f}")

        # PnL: use domain terminology based on sign
        if pnl is not None:
            if pnl < 0:
                lines.append(f"未实现亏损：{format_amount_usd(pnl)}")
            else:
                lines.append(f"未实现盈利：{format_amount_usd(pnl)}")
        if liq_price:
            lines.append(f"清算价：${liq_price:,.2f}")
        else:
            lines.append("清算价：暂无数据")
        lines.append(f"距清算价：{liq_dist}")
        lines.append("")

    # ── Risk tags from domain output (not recalculated) ─────────────────
    if candidates:
        risk_tags, severities = _collect_risk_tags(candidates)
        if risk_tags:
            lines.append("⚠️ 风险标记：" + " | ".join(risk_tags))
            lines.append("")

    # ── Market data ─────────────────────────────────────────────────────
    if market_data:
        prices = []
        for m in market_data:
            sym = m.get("symbol", "")
            price = m.get("last_price")
            src = m.get("source", "")
            if price:
                prices.append(f"{sym}: ${price:,.2f} ({src})")
        if prices:
            lines.append("\U0001f4e1 市场快照")
            lines.extend(prices)
            lines.append("")

    # ── Source footnote (summary only — no per-source health) ────────────
    sources_seen: set[str] = set()
    if run_data:
        src_list = run_data.get("sources", [])
        for s in src_list:
            sname = s.get("source", "")
            if sname:
                sources_seen.add(sname)
    if positions:
        sources_seen.add("Hyperliquid")
    if market_data:
        for m in market_data:
            src = m.get("source", "")
            if src:
                sources_seen.add(src)
    if sources_seen:
        lines.append(f"\U0001f4e1 数据来源：{'、'.join(sorted(sources_seen))}")
    else:
        lines.append("\U0001f4e1 数据来源：Hyperliquid、Binance")

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append(f"数据时间：{now_str}")
    lines.append("")
    lines.append("\U0001f9ea Staging 修正版预览 • 当前未启用长期自动推送")

    return "\n".join(line for line in lines if line)


# ── Telegram one-shot send (error-desensitized) ─────────────────────────

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


def _sanitize_error(error_text: str, token: str) -> str:
    """Remove bot token from any error text."""
    if token and token in error_text:
        return error_text.replace(token, "[REDACTED_TOKEN]")
    return error_text


def telegram_call(
    token: str, method: str, payload: Optional[dict] = None, timeout: int = 20,
) -> dict:
    """Make a Telegram API call. Never leaks token in errors or logs.

    Security guarantees:
      - Exception messages are sanitized to remove token
      - HTTP response bodies are read with strict UTF-8 (no errors='replace')
      - Token never appears in returned dict values
      - Full URL never appears in returned dict values
    """
    if payload is None:
        req = urllib.request.Request(
            f"{TELEGRAM_API_BASE}{token}/{method}", method="GET",
            headers={"User-Agent": "CSI-TG-Preview/1.0"},
        )
    else:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{TELEGRAM_API_BASE}{token}/{method}", data=body, method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "CSI-TG-Preview/1.0",
            },
        )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Read response body with strict UTF-8; if invalid, use safe fallback
        raw_body = exc.read()
        try:
            body_text = raw_body.decode("utf-8")
        except UnicodeDecodeError:
            body_text = "[non-UTF-8 response body]"
        try:
            parsed = json.loads(body_text)
            desc = parsed.get("description", f"HTTP {exc.code}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            desc = f"HTTP {exc.code}: {body_text[:200]}"
        desc = _sanitize_error(desc, token)
        return {"ok": False, "http_status": exc.code, "description": desc}
    except urllib.error.URLError as exc:
        safe_reason = _sanitize_error(str(exc.reason), token) if hasattr(exc, 'reason') else "network error"
        return {"ok": False, "description": f"URLError: {_safe_type(exc)}"}
    except OSError as exc:
        return {"ok": False, "description": f"OSError: {_safe_type(exc)}"}
    except Exception as exc:
        return {"ok": False, "description": f"Exception: {type(exc).__name__}"}


def _safe_type(exc: BaseException) -> str:
    """Return a safe description from an exception — no str(exc) with URLs/tokens."""
    name = type(exc).__name__
    return name


def send_preview_card(token: str, chat_id: int, preview_text: str) -> dict:
    """One-shot send with full gate. Max 1 sendMessage call."""
    markers = get_required_markers(
        has_positions=True,
        has_alerts=True,
        has_whale_data=True,
    )
    violations = check_garbled(preview_text, markers=markers)
    if violations:
        return {"status": "blocked", "stage": "garbled_gate",
                "violations": violations, "send_attempts": 0}

    r = telegram_call(token, "getMe")
    if not r.get("ok"):
        return {"status": "failed", "stage": "getMe",
                "telegram": r, "send_attempts": 0}

    r = telegram_call(token, "getChat", {"chat_id": chat_id})
    if not r.get("ok"):
        return {"status": "failed", "stage": "getChat",
                "channel_id": chat_id, "telegram": r, "send_attempts": 0}
    ch = r["result"]

    r = telegram_call(token, "getChatMember", {"chat_id": chat_id, "user_id": ch.get("id", 0)})
    if not r.get("ok"):
        return {"status": "failed", "stage": "getChatMember",
                "channel_title": ch.get("title"), "telegram": r, "send_attempts": 0}
    m = r["result"]
    ms = m.get("status")
    cp = m.get("can_post_messages")

    if ms not in ("administrator", "creator"):
        return {"status": "failed", "stage": "permission",
                "member_status": ms, "send_attempts": 0}
    if ms == "administrator" and cp is not True:
        return {"status": "failed", "stage": "permission",
                "can_post_messages": cp, "send_attempts": 0}

    r = telegram_call(token, "sendMessage", {
        "chat_id": chat_id, "text": preview_text, "disable_notification": True,
    })
    if not r.get("ok"):
        return {"status": "failed", "stage": "sendMessage",
                "channel_id": chat_id, "telegram": r, "send_attempts": 1}

    sent = r["result"]
    return {
        "status": "success",
        "channel_id": chat_id,
        "channel_title": ch.get("title"),
        "channel_username": ch.get("username"),
        "member_status": ms,
        "can_post_messages": cp,
        "sent_message_id": sent.get("message_id"),
        "send_attempts": 1,
    }


# ── CLI entry point ────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Telegram preview renderer")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--channel-id", type=int, default=-1003993870683)
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--token-env", default="TELEGRAM_BOT_TOKEN")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    run_files = list(run_dir.glob("run_*.json"))
    if not run_files:
        print(json.dumps({"error": "no run_*.json found"}, ensure_ascii=False))
        sys.exit(1)
    with open(run_files[0], "r", encoding="utf-8") as f:
        run_data = json.load(f)

    whale_files = list(run_dir.glob("whale_*.json"))
    whale_data: dict = {"ok": False}
    if whale_files:
        with open(whale_files[0], "r", encoding="utf-8") as f:
            whale_data = json.load(f)

    market_files = list(run_dir.glob("market_*.json"))
    market_data: list[dict] = []
    if market_files:
        with open(market_files[0], "r", encoding="utf-8") as f:
            market_data = json.load(f).get("symbols", [])

    preview = build_preview_card(whale_data, market_data, run_data)

    has_pos = bool(whale_data.get("positions"))
    has_alerts = bool(whale_data.get("alert_candidates"))
    markers = get_required_markers(
        has_positions=has_pos,
        has_alerts=has_alerts,
        has_whale_data=has_pos or has_alerts,
    )
    violations = check_garbled(preview, markers=markers)

    result = {
        "preview_text": preview,
        "preview_length": len(preview),
        "garbled_violations": violations,
        "garbled_gate_pass": len(violations) == 0,
        "send_status": "dry_run",
    }

    if args.send:
        token = os.environ.get(args.token_env, "").strip()
        if not token:
            result["send_status"] = "skipped_no_token"
        else:
            send_result = send_preview_card(token, args.channel_id, preview)
            result.update(send_result)
            result["send_status"] = send_result.get("status")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
