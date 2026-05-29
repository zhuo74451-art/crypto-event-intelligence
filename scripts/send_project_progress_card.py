import argparse
import os
import re
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a concise Chinese project progress card to Telegram.")
    parser.add_argument("--title", default="系统进展")
    parser.add_argument("--body", default="")
    parser.add_argument("--token-env", default="TELEGRAM_BOT_TOKEN")
    parser.add_argument("--chat-id-env", default="TELEGRAM_CHAT_ID")
    parser.add_argument("--load-local-secrets", default="true")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--send", action="store_true")
    return parser.parse_args()


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def load_local_secrets(env: dict, enabled: str) -> dict:
    if not truthy(enabled):
        return env
    path = ROOT / "config" / "local_secrets.ps1"
    if not path.exists():
        return env
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for name in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_PUBLISH_CHAT_IDS"]:
        match = re.search(r"\$env:" + re.escape(name) + r"\s*=\s*['\"]([^'\"]+)['\"]", text)
        if match:
            env[name] = match.group(1).strip()
    return env


def send_message(token: str, chat_id: str, text: str, retries: int = 3) -> dict:
    last_error = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            response = requests.post(
                TELEGRAM_API.format(token=token),
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=20,
            )
            payload = response.json()
            if response.status_code < 300 and payload.get("ok"):
                result = payload.get("result", {})
                return result if isinstance(result, dict) else {}
            last_error = RuntimeError(f"telegram send failed: http={response.status_code}; body={str(payload)[:300]}")
        except Exception as exc:
            last_error = exc
        time.sleep(min(attempt, 3))
    raise RuntimeError(str(last_error))


def main() -> int:
    args = parse_args()
    body = args.body.strip() or "项目有新进展。"
    text = "\n".join(
        [
            f"<b>⚙️ {args.title}</b>",
            "",
            body,
            "",
            "说明：这是项目测试进展卡，不是市场交易建议。",
        ]
    )
    if not args.send:
        print(text)
        return 0

    env = load_local_secrets(os.environ.copy(), args.load_local_secrets)
    token = env.get(args.token_env, "").strip()
    chat_id = env.get(args.chat_id_env, "").strip()
    if not chat_id and args.chat_id_env == "TELEGRAM_CHAT_ID":
        chat_id = env.get("TELEGRAM_PUBLISH_CHAT_IDS", "").split(",")[0].strip()
    if not token or not chat_id:
        print("missing Telegram token or chat id")
        return 2
    result = send_message(token, chat_id, text, args.retries)
    print(f"sent progress card message_id={result.get('message_id', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
