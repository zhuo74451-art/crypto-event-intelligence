"""
v1.8H Single Card TG Group Send
- Verify target is a TG group (not channel)
- Send exactly 1 card from candidate markdown
- Max sent_count = 1, then stop
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

TG_BASE = "https://api.telegram.org/bot{token}"


def load_token_and_chat_id() -> tuple[str, str]:
    """Load token + chat_id from env or local_secrets.ps1. Never print values."""
    env: dict[str, str] = dict(os.environ)

    # Try local_tg_publisher.env
    env_path = ROOT / "config" / "local_tg_publisher.env"
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

    # Fallback: parse local_secrets.ps1
    secrets_path = ROOT / "config" / "local_secrets.ps1"
    if secrets_path.exists():
        import re
        text = secrets_path.read_text(encoding="utf-8-sig", errors="replace")
        for name in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
            if name not in env or not env[name]:
                match = re.search(
                    r"\$env:" + re.escape(name) + r"\s*=\s*['\"]([^'\"]+)['\"]", text
                )
                if match:
                    env[name] = match.group(1).strip()

    token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = env.get("TELEGRAM_CHAT_ID", "").strip()

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not found in env or config")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID not found in env or config")

    return token, chat_id


def api_call(token: str, method: str, params: dict | None = None) -> dict:
    """Call Telegram Bot API. Returns parsed JSON."""
    url = TG_BASE.format(token=token) + "/" + method
    if params:
        data = urllib.parse.urlencode(params).encode("utf-8")
    else:
        data = None

    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_body[:300]}")
    except Exception as e:
        raise RuntimeError(f"API call failed: {e}")

    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON response: {body[:200]}")

    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result.get('description', body[:200])}")

    return result.get("result", result)


def verify_group(token: str, chat_id: str) -> dict:
    """Call getChat and verify it's a group/supergroup, NOT a channel."""
    result = api_call(token, "getChat", {"chat_id": chat_id})

    chat_type = result.get("type", "unknown")
    chat_title = result.get("title", "(no title)")

    # Mask: only print type and first 2 chars of title
    masked_title = chat_title[:2] + "***" if len(chat_title) > 2 else chat_title

    print(f"Chat type: {chat_type}")
    print(f"Chat title: {masked_title}")

    if chat_type in ("group", "supergroup"):
        print("VERIFIED: Target is a Telegram group.")
        return result
    elif chat_type == "channel":
        raise RuntimeError(
            f"BLOCKED: Target is a Telegram CHANNEL (type={chat_type}). "
            f"Task only allows group sends."
        )
    else:
        raise RuntimeError(
            f"BLOCKED: Unknown chat type '{chat_type}'. "
            f"Cannot confirm it's a group. Stopping."
        )


def load_candidate_text() -> str:
    """Read the candidate card markdown file."""
    candidate_path = ROOT / "results" / "static_position_v18g_send_candidate.md"
    if not candidate_path.exists():
        raise RuntimeError(f"Candidate file not found: {candidate_path}")
    text = candidate_path.read_text(encoding="utf-8-sig", errors="replace").strip()
    if not text:
        raise RuntimeError("Candidate file is empty")
    return text


def send_one_message(token: str, chat_id: str, text: str) -> dict:
    """Send exactly ONE message via Telegram sendMessage."""
    print("Sending 1 message to TG group...")
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    result = api_call(token, "sendMessage", params)
    msg_id = result.get("message_id", "")
    result_chat = result.get("chat", {})
    actual_chat_id = str(result_chat.get("id", ""))

    # Safety: verify result chat type matches
    result_chat_type = result_chat.get("type", "")
    if result_chat_type == "channel":
        raise RuntimeError(
            f"CRITICAL: Message was sent to a CHANNEL (type={result_chat_type}). "
            f"This violates task constraints."
        )

    print(f"Message sent successfully. message_id={msg_id}")
    return {"message_id": str(msg_id), "chat_id_masked": actual_chat_id[:4] + "***" if len(actual_chat_id) > 4 else "***"}


def main() -> int:
    now_china = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    print(f"=== v1.8H Single Card TG Group Send ===")
    print(f"Time: {now_china}")
    print()

    SENT_COUNT = 0
    MAX_SEND = 1

    try:
        # Step 1: Load credentials (never printed)
        token, chat_id = load_token_and_chat_id()
        print("Credentials loaded: OK (token + chat_id present)")

        # Step 2: Verify target is a group
        chat_info = verify_group(token, chat_id)

        # Step 3: Load candidate text
        candidate_text = load_candidate_text()
        print(f"Candidate loaded: {len(candidate_text)} chars")

        # Step 4: Send exactly 1 message
        if SENT_COUNT >= MAX_SEND:
            print("Send limit reached. Stopping.")
            return 0

        send_result = send_one_message(token, chat_id, candidate_text)
        SENT_COUNT += 1

        # Step 5: Output result JSON for the result.md
        result = {
            "status": "done",
            "sent_count": SENT_COUNT,
            "message_id": send_result.get("message_id", ""),
            "target_type": "TG群",
            "tg_api_called": True,
            "sent_exceed_1": False,
            "sent_channel": False,
            "loop_started": False,
            "sensitive_printed": False,
            "remote_db_written": False,
        }
        print()
        print("=== RESULT_JSON ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        result = {
            "status": "failed",
            "sent_count": SENT_COUNT,
            "message_id": "",
            "target_type": "TG群",
            "tg_api_called": SENT_COUNT > 0,
            "sent_exceed_1": False,
            "sent_channel": False,
            "loop_started": False,
            "sensitive_printed": False,
            "remote_db_written": False,
            "error": str(e)[:500],
        }
        print()
        print("=== RESULT_JSON ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
