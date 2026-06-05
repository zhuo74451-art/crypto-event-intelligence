"""
Send local_news_flow_preview.md as a single TG summary message.

Usage:
    python scripts/send_local_news_flow_preview_to_tg.py              # dry-run
    python scripts/send_local_news_flow_preview_to_tg.py --send        # real send
    python scripts/send_local_news_flow_preview_to_tg.py --send --chat-id -100xxx

Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from os.environ.
NEVER prints or logs token value or full chat_id.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

DISCLAIMER = "⚠️ 仅作市场结构与链上情报观察，不构成任何交易建议。"
BANNED = ["买入", "卖出", "做多", "做空", "开仓", "止盈", "止损", "追涨", "杀跌"]


def china_now() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def load_env_from_ps1() -> dict[str, str]:
    """Try to source config/local_secrets.ps1 via subprocess powershell."""
    cfg: dict[str, str] = {}
    ps1 = ROOT / "config" / "local_secrets.ps1"
    if not ps1.exists():
        return cfg
    import subprocess
    script = f'. "{ps1}"; Write-Host "TOKEN=$env:TELEGRAM_BOT_TOKEN"; Write-Host "CHAT=$env:TELEGRAM_CHAT_ID"; Write-Host "CHATS=$env:TELEGRAM_PUBLISH_CHAT_IDS"'
    r = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                       capture_output=True, text=True, timeout=15)
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("TOKEN=") and len(line) > 6:
            cfg["TELEGRAM_BOT_TOKEN"] = line[6:]
        elif line.startswith("CHAT=") and len(line) > 5:
            cfg["TELEGRAM_CHAT_ID"] = line[5:]
        elif line.startswith("CHATS=") and len(line) > 6:
            cfg["TELEGRAM_PUBLISH_CHAT_IDS"] = line[6:]
    return cfg


def get_config() -> dict[str, str]:
    cfg = {}
    # Try powershell secrets first (Windows), then os.environ (already loaded)
    try:
        cfg.update(load_env_from_ps1())
    except Exception:
        pass
    # os.environ overrides
    for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_PUBLISH_CHAT_IDS"):
        if k in os.environ and os.environ[k]:
            cfg[k] = os.environ[k]
    return cfg


def pick_chat_id(cfg: dict[str, str]) -> str:
    for k in ("TELEGRAM_CHAT_ID", "TELEGRAM_PUBLISH_CHAT_IDS"):
        v = cfg.get(k, "")
        if v:
            # If comma-separated, take first
            return v.split(",")[0].strip()
    return ""


def build_message(preview_path: Path) -> str:
    """Extract preview content and build a single TG HTML summary."""
    if not preview_path.exists():
        return "<b>本地快讯流预览</b>\n\n暂无预览数据。"

    text = preview_path.read_text(encoding="utf-8")
    # Extract key sections
    raw_count = ""
    cand_count = ""
    items = []

    for line in text.splitlines():
        s = line.strip()
        if "本轮同步快讯" in s:
            raw_count = s
        elif "候选事件" in s:
            cand_count = s
        elif s.startswith("### ") and len(items) < 5:
            title = s.lstrip("# ").strip()
            items.append(title)

    lines = ["<b>[Live News Flow] 本地快讯流预览</b>", ""]
    lines.append(f"生成时间：{china_now()}")
    if raw_count:
        lines.append(raw_count)
    if cand_count:
        lines.append(cand_count)
    lines.append("")

    if items:
        lines.append("<b>最新快讯（前 5 条）：</b>")
        for i, t in enumerate(items, 1):
            safe_title = html.escape(t[:80])
            lines.append(f"{i}. {safe_title}")
    else:
        lines.append("（暂无快讯预览）")

    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def filter_banned(text: str) -> tuple[bool, list[str]]:
    hits = [kw for kw in BANNED if kw in text]
    return len(hits) == 0, hits


def init_sent_state(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent (
            content_hash TEXT PRIMARY KEY,
            sent_at      TEXT NOT NULL,
            chat_id      TEXT NOT NULL DEFAULT '',
            msg_id       TEXT NOT NULL DEFAULT '',
            status       TEXT NOT NULL DEFAULT 'sent',
            error        TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.commit()
    return conn


def already_sent(conn: sqlite3.Connection, h: str, chat_id: str) -> bool:
    r = conn.execute("SELECT 1 FROM sent WHERE content_hash = ? AND chat_id = ? AND status = 'sent'",
                     (h, chat_id)).fetchone()
    return r is not None


def record_sent(conn: sqlite3.Connection, h: str, chat_id: str, msg_id: str, status: str, error: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sent (content_hash, sent_at, chat_id, msg_id, status, error) VALUES (?, ?, ?, ?, ?, ?)",
        (h, china_now(), chat_id, msg_id, status, error),
    )
    conn.commit()


def send_telegram(token: str, chat_id: str, text: str) -> tuple[str, str]:
    clean, hits = filter_banned(text)
    if not clean:
        return "", f"blocked: {hits}"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    data = urllib.parse.urlencode(payload).encode("utf-8")
    url = TELEGRAM_API.format(token=token)
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return "", f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}"
    except Exception as e:
        return "", str(e)[:200]
    r = json.loads(body)
    if r.get("ok"):
        return str(r["result"]["message_id"]), ""
    return "", f"API: {body[:200]}"


def main() -> int:
    p = argparse.ArgumentParser(description="Send local_news_flow_preview.md summary to TG.")
    p.add_argument("--send", action="store_true", help="Actually send to Telegram")
    p.add_argument("--chat-id", type=str, default=None, help="Override chat_id")
    p.add_argument("--preview", default=str(ROOT / "results" / "local_news_flow_preview.md"))
    p.add_argument("--state", default=str(ROOT / "data" / "local_news_flow_tg_sent_state.sqlite"))
    args = p.parse_args()

    cfg = get_config()
    token = cfg.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = args.chat_id or pick_chat_id(cfg)

    preview_path = Path(args.preview)
    msg = build_message(preview_path)
    content_hash = hashlib.sha256(msg.encode("utf-8")).hexdigest()

    print(f"token_configured: {bool(token)}")
    print(f"chat_id_configured: {bool(chat_id)}")
    print(f"Content hash: {content_hash[:16]}")
    print(f"Message length: {len(msg)} chars")
    print(f"Message lines: {msg.count(chr(10)) + 1}")
    print()

    state_path = Path(args.state)
    conn = init_sent_state(state_path)

    if args.send:
        if not token:
            print("ERROR: TELEGRAM_BOT_TOKEN not set.")
            print("  Run: . .\\config\\local_secrets.ps1")
            conn.close()
            return 1
        if not chat_id:
            print("ERROR: No chat_id found. Set TELEGRAM_CHAT_ID or TELEGRAM_PUBLISH_CHAT_IDS.")
            conn.close()
            return 1
        if already_sent(conn, content_hash, chat_id):
            print("SKIPPED: Content hash already sent to this chat.")
            conn.close()
            return 0
        msg_id, error = send_telegram(token, chat_id, msg)
        if error:
            print(f"FAILED: {error}")
            record_sent(conn, content_hash, chat_id, "", "failed", error)
            conn.close()
            return 1
        print(f"SENT: message_id={msg_id}")
        record_sent(conn, content_hash, chat_id, msg_id, "sent", "")
    else:
        print("[DRY-RUN] Not sent. Use --send to send.")
        print("--- Message preview ---")
        # Safe print for Windows GBK terminals
        safe = msg[:500].encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        try:
            print(safe)
        except UnicodeEncodeError:
            print(safe.encode('ascii', errors='replace').decode('ascii'))
        if len(msg) > 500:
            print(f"... ({len(msg) - 500} more chars)")
        print("--- End preview ---")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
