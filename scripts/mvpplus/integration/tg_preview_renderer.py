"""Telegram staging preview renderer — one-shot card builder.

Reads a run output directory, builds a Chinese preview card from real data.
UTF-8 safe: no hardcoded Chinese literals get corrupted at file-write time
because this file IS the source (git stores UTF-8).

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


# ── Garbled text gate ──────────────────────────────────────────────────

REQUIRED_CHINESE_MARKERS = [
    "鲸鱼警报",
    "大额杠杆多头",
    "开仓价",
    "当前标记价",
    "未实现盈亏",
    "清算价",
    "距清算价",
    "风险标记",
    "数据来源",
    "数据时间",
]


def check_garbled(text: str) -> list[str]:
    """Check text for garbled/truncated content. Returns violations list."""
    violations: list[str] = []
    if not text or not text.strip():
        violations.append("text is empty")
        return violations
    if re.search(r"\?{3,}", text):
        violations.append("text contains 3+ consecutive '?' — garbled encoding")
    if "�" in text:
        violations.append("text contains Unicode replacement character (U+FFFD)")
    for marker in REQUIRED_CHINESE_MARKERS:
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
    """Short-scale USD formatting."""
    if value is None:
        return "暂无数据"
    abs_val = abs(value)
    prefix = "-" if value < 0 else ""
    if abs_val >= 1_000_000_000:
        return f"{prefix}{abs_val / 1_000_000_000:.1f}B"
    elif abs_val >= 1_000_000:
        return f"{prefix}{abs_val / 1_000_000:.1f}M"
    elif abs_val >= 1_000:
        return f"{prefix}{abs_val / 1_000:.0f}K"
    else:
        return f"${value:,.0f}"


def shorten_address(address: str) -> str:
    """0x6c8512...84f6"""
    if len(address) <= 12:
        return address
    return address[:8] + "…" + address[-4:]


# ── Chinese label maps ─────────────────────────────────────────────────

CHINESE_LABELS = {
    "high_leverage": "高杠杆持仓",
    "concentrated_exposure": "集中持仓风险",
    "large_new_position": "新建大额仓位",
    "large_increase": "仓位大幅增加",
    "large_decrease": "仓位大幅减少",
    "direction_flip": "方向反转",
    "liquidation_critical": "清算接近临界",
}

SEVERITY_LABELS = {
    "critical": "严重",
    "high": "高",
    "medium": "中",
    "low": "低",
}


# ── Card builder ────────────────────────────────────────────────────────

def build_preview_card(
    whale_data: dict[str, Any],
    market_data: Optional[list[dict]] = None,
    run_data: Optional[dict] = None,
) -> str:
    """Build Telegram preview card from real run output data.

    All Chinese text is native UTF-8 (this file is UTF-8 in git).
    Caller must use ensure_ascii=False when serializing.
    """
    lines: list[str] = []
    lines.append("\U0001f40b Crypto Signal Intelligence OS — Staging \U0001f9ea")
    lines.append("")

    candidates = whale_data.get("alert_candidates", [])
    positions = whale_data.get("positions", [])

    if candidates:
        for c in candidates[:2]:
            atype = c.get("alert_type", "")
            severity = c.get("severity", "low")
            coin = c.get("coin", "")
            addr_short = c.get("address_short", "")
            observed = c.get("observed_value")
            sev_label = SEVERITY_LABELS.get(severity, severity)
            cn_type = CHINESE_LABELS.get(atype, atype)

            lines.append(f"\U0001f514 鲸鱼警报 — {cn_type} [{sev_label}]")
            lines.append(f"地址：{shorten_address(addr_short) if addr_short else c.get('label', '?')}")

            if atype == "high_leverage" and observed is not None:
                lines.append(f"资产：{coin}")
                lines.append(f"杠杆倍数：{observed}x")
            elif atype == "concentrated_exposure" and observed is not None:
                lines.append(f"资产：{coin}")
                lines.append(f"集中仓位价值：{format_amount_usd(observed)}")
            else:
                lines.append(f"资产：{coin}")
                lines.append(c.get("message", ""))
            lines.append("")

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

        dir_cn = "多头" if direction == "long" else "空头"
        lines.append(f"\U0001f4cb {coin} 大额杠杆{dir_cn}")
        lines.append(f"规模：{abs_size:,.0f} {coin}（约 {format_amount_usd(pos_value)}）")
        if leverage:
            lines.append(f"杠杆：{leverage}x")
        if entry_price:
            lines.append(f"开仓价：${entry_price:,.2f}")
        if mark_price:
            lines.append(f"当前标记价：${mark_price:,.2f}")
        if pnl is not None:
            lines.append(f"未实现盈亏：{format_amount_usd(pnl)}")
        if liq_price:
            lines.append(f"清算价：${liq_price:,.2f}")
        else:
            lines.append("清算价：暂无数据")
        lines.append(f"距清算价：{liq_dist}")
        lines.append("")

    # Risk flags from data
    risk_flags = []
    if positions:
        p = positions[0]
        if p.get("leverage", 0) >= 10:
            risk_flags.append("高杠杆")
        pv = abs(p.get("signed_size", 0)) * (p.get("mark_price", 0) or 0)
        if pv >= 5_000_000:
            risk_flags.append("资产集中")
        if p.get("position_value_usd", 0) >= 50_000_000:
            risk_flags.append("大额持仓")
        upnl = p.get("unrealized_pnl_usd", 0)
        if upnl is not None and upnl < -1_000_000:
            risk_flags.append("大幅未实现亏损")
    if risk_flags:
        lines.append("⚠️ 风险标记：" + " | ".join(risk_flags))
        lines.append("")

    # Market data
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

    # Source footnotes
    if run_data:
        sources = run_data.get("sources", [])
        src_lines = []
        for s in sources:
            sname = s.get("source", "")
            ok = s.get("ok", False)
            icon = "✅" if ok else "❌"
            src_lines.append(f"{icon} {sname}")
        if src_lines:
            lines.append("\U0001f4e1 数据来源")
            lines.extend(src_lines)
            lines.append("")

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append(f"数据时间：{now_str}")
    lines.append("")
    lines.append("\U0001f9ea Staging 修正版预览 • 当前未启用长期自动推送")

    return "\n".join(line for line in lines if line)


# ── Telegram one-shot send ─────────────────────────────────────────────

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


def telegram_call(
    token: str, method: str, payload: Optional[dict] = None, timeout: int = 20,
) -> dict:
    url = f"{TELEGRAM_API_BASE}{token}/{method}"
    if payload is None:
        req = urllib.request.Request(
            url, method="GET",
            headers={"User-Agent": "CSI-TG-Preview/1.0"},
        )
    else:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "CSI-TG-Preview/1.0",
            },
        )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
            desc = parsed.get("description", "HTTP error")
        except Exception:
            desc = raw[:500]
        return {"ok": False, "http_status": exc.code, "description": desc}
    except Exception as exc:
        return {"ok": False, "description": f"{type(exc).__name__}: {exc}"}


def send_preview_card(token: str, chat_id: int, preview_text: str) -> dict:
    """One-shot send with full gate. Max 1 sendMessage call."""
    violations = check_garbled(preview_text)
    if violations:
        return {"status": "blocked", "stage": "garbled_gate",
                "violations": violations, "send_attempts": 0}

    r = telegram_call(token, "getMe")
    if not r.get("ok"):
        return {"status": "failed", "stage": "getMe",
                "telegram": r, "send_attempts": 0}
    bot = r["result"]
    bot_id = bot["id"]

    r = telegram_call(token, "getChat", {"chat_id": chat_id})
    if not r.get("ok"):
        return {"status": "failed", "stage": "getChat",
                "channel_id": chat_id, "telegram": r, "send_attempts": 0}
    ch = r["result"]

    r = telegram_call(token, "getChatMember", {"chat_id": chat_id, "user_id": bot_id})
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
        "bot_username": bot.get("username"),
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
    violations = check_garbled(preview)

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


