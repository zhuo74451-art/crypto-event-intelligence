"""
Test script: send exactly ONE test message to verify token/chat_id.

Usage:
    python scripts/test_local_tg_send.py              # dry-run (default)
    python scripts/test_local_tg_send.py --send        # real send (requires token)

Reads config from config/local_tg_publisher.env or environment variables.
NEVER prints or logs the token value.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def load_env() -> dict[str, str]:
    """Load config from env file + os.environ."""
    cfg: dict[str, str] = {}
    env_path = ROOT / "config" / "local_tg_publisher.env"
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    for k in cfg:
        if k in os.environ:
            cfg[k] = os.environ[k]
    return cfg


def main() -> int:
    parser = argparse.ArgumentParser(description="Send one test TG message to verify config.")
    parser.add_argument("--send", action="store_true",
                        help="Actually send to Telegram (default: dry-run only)")
    parser.add_argument("--chat-id", type=str, default=None,
                        help="Override TELEGRAM_CHAT_ID")
    args = parser.parse_args()

    cfg = load_env()
    token = cfg.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = args.chat_id or cfg.get("TELEGRAM_CHAT_ID", "")

    # Safety: never print the actual token
    masked_token = token[:8] + "..." + token[-4:] if len(token) > 12 else "(empty)"
    print(f"Token: {masked_token}")
    print(f"Chat ID: {chat_id}")
    print(f"Mode: {'REAL SEND' if args.send else 'DRY RUN'}")
    print()

    if args.send:
        if not token:
            print("ERROR: TELEGRAM_BOT_TOKEN not set.")
            print("Set it in config/local_tg_publisher.env or as environment variable.")
            return 1
        if not chat_id:
            print("ERROR: TELEGRAM_CHAT_ID not set.")
            print("Set it in config/local_tg_publisher.env or as environment variable.")
            return 1

    now_china = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    test_message = (
        f"<b>🧪 v16 Local Publisher — 测试消息</b>\n\n"
        f"时间：{now_china}\n"
        f"来源：scripts/test_local_tg_send.py\n\n"
        f"如果你看到这条消息，说明 Token 和 Chat ID 配置正确。\n\n"
        f"⚠️ 仅作市场结构与链上情报观察，不构成任何交易建议。"
    )

    print("── Test message preview ──")
    print(test_message)
    print("── End preview ──")
    print()

    if not args.send:
        print("DRY RUN complete. Use --send to send real message.")
        return 0

    payload = {
        "chat_id": chat_id,
        "text": test_message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    url = TELEGRAM_API.format(token=token)

    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {e.code} — {err_body[:300]}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    try:
        result = json.loads(body)
        if result.get("ok"):
            msg_id = result["result"].get("message_id", "")
            print(f"SUCCESS: Message sent! message_id={msg_id}")
            return 0
        print(f"ERROR: Telegram API returned: {body[:300]}")
        return 1
    except Exception as e:
        print(f"ERROR parsing response: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
