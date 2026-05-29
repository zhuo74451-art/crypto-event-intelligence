import argparse
import csv
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
GET_UPDATES_URL = "https://api.telegram.org/bot{token}/getUpdates"

FEEDBACK_COLUMNS = [
    "collected_at_china",
    "update_id",
    "feedback_type",
    "feedback_value",
    "telegram_chat_id",
    "telegram_message_id",
    "feedback_user_id",
    "feedback_username",
    "feedback_text",
    "draft_id",
    "candidate_id",
    "event_type",
    "asset_symbol",
    "amount_usd",
    "status",
    "raw_json",
]

STATE_COLUMNS = ["key", "value"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Telegram alert feedback into local CSV.")
    parser.add_argument("--sent-state", default=str(ROOT / "data" / "tg_live_sent_state.csv"))
    parser.add_argument("--feedback-output", default=str(ROOT / "data" / "tg_alert_feedback.csv"))
    parser.add_argument("--state", default=str(ROOT / "data" / "tg_feedback_collect_state.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_alert_feedback_summary.csv"))
    parser.add_argument("--token-env", default="TELEGRAM_BOT_TOKEN")
    parser.add_argument("--load-local-secrets", default="true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--timeout", type=int, default=20)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def load_local_secrets(env: dict, enabled: str) -> dict:
    if str(enabled).strip().lower() not in {"1", "true", "yes", "y"}:
        return env
    path = ROOT / "config" / "local_secrets.ps1"
    if not path.exists():
        return env
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for name in ["TELEGRAM_BOT_TOKEN"]:
        match = re.search(r"\$env:" + re.escape(name) + r"\s*=\s*['\"]([^'\"]+)['\"]", text)
        if match:
            env[name] = match.group(1).strip()
    return env


def state_value(path: Path, key: str, default: str = "") -> str:
    for row in read_rows(path):
        if str(row.get("key", "")).strip() == key:
            return str(row.get("value", "")).strip()
    return default


def write_state_value(path: Path, key: str, value: str) -> None:
    rows = [row for row in read_rows(path) if str(row.get("key", "")).strip() != key]
    rows.append({"key": key, "value": value})
    write_rows(path, rows, STATE_COLUMNS)


def sent_index(rows: list[dict]) -> dict[tuple[str, str], dict]:
    output = {}
    for row in rows:
        chat_id = str(row.get("telegram_chat_id", "") or "").strip()
        message_id = str(row.get("telegram_message_id", "") or "").strip()
        if chat_id and message_id:
            output[(chat_id, message_id)] = row
    return output


def user_fields(user: dict) -> tuple[str, str]:
    if not isinstance(user, dict):
        return "", ""
    username = str(user.get("username", "") or "")
    if not username:
        name = " ".join(part for part in [str(user.get("first_name", "") or ""), str(user.get("last_name", "") or "")] if part)
        username = name
    return str(user.get("id", "") or ""), username


def classify_text_feedback(text: str) -> tuple[str, str]:
    raw = str(text or "").strip()
    positive = {"👍", "❤️", "🔥", "+1", "有用", "不错", "准", "好", "valuable", "useful"}
    negative = {"👎", "-1", "没用", "垃圾", "不准", "噪音", "noise", "bad"}
    lowered = raw.lower()
    if any(item in raw or item in lowered for item in positive):
        return "reply", "positive"
    if any(item in raw or item in lowered for item in negative):
        return "reply", "negative"
    return "reply", "comment"


def parse_update(update: dict, sent: dict[tuple[str, str], dict]) -> dict | None:
    update_id = str(update.get("update_id", "") or "")
    if "message_reaction" in update:
        reaction = update.get("message_reaction", {})
        chat = reaction.get("chat", {}) if isinstance(reaction, dict) else {}
        chat_id = str(chat.get("id", "") or "")
        message_id = str(reaction.get("message_id", "") or "")
        user_id, username = user_fields(reaction.get("user", {}))
        new_reaction = reaction.get("new_reaction", [])
        reaction_text = ",".join(str(item.get("emoji", "") or item.get("type", "")) for item in new_reaction if isinstance(item, dict))
        feedback_value = "positive" if any(mark in reaction_text for mark in ["👍", "❤️", "🔥"]) else "negative" if "👎" in reaction_text else "reaction"
        linked = sent.get((chat_id, message_id), {})
        return build_row(update_id, "reaction", feedback_value, chat_id, message_id, user_id, username, reaction_text, linked, update)

    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return None
    reply = message.get("reply_to_message", {})
    if not isinstance(reply, dict):
        return None
    chat = message.get("chat", {}) if isinstance(message.get("chat", {}), dict) else {}
    chat_id = str(chat.get("id", "") or "")
    message_id = str(reply.get("message_id", "") or "")
    linked = sent.get((chat_id, message_id), {})
    if not linked:
        return None
    text = str(message.get("text", "") or message.get("caption", "") or "").strip()
    feedback_type, feedback_value = classify_text_feedback(text)
    user_id, username = user_fields(message.get("from", {}))
    return build_row(update_id, feedback_type, feedback_value, chat_id, message_id, user_id, username, text, linked, update)


def build_row(
    update_id: str,
    feedback_type: str,
    feedback_value: str,
    chat_id: str,
    message_id: str,
    user_id: str,
    username: str,
    text: str,
    linked: dict,
    raw: dict,
) -> dict:
    return {
        "collected_at_china": china_now(),
        "update_id": update_id,
        "feedback_type": feedback_type,
        "feedback_value": feedback_value,
        "telegram_chat_id": chat_id,
        "telegram_message_id": message_id,
        "feedback_user_id": user_id,
        "feedback_username": username,
        "feedback_text": text,
        "draft_id": linked.get("draft_id", ""),
        "candidate_id": linked.get("candidate_id", ""),
        "event_type": linked.get("event_type", ""),
        "asset_symbol": linked.get("asset_symbol", ""),
        "amount_usd": linked.get("amount_usd", ""),
        "status": "matched" if linked else "unmatched",
        "raw_json": str(raw)[:2000],
    }


def main() -> int:
    args = parse_args()
    env = load_local_secrets(os.environ.copy(), args.load_local_secrets)
    token = env.get(args.token_env, "").strip()
    output_path = normalize_path(args.feedback_output)
    state_path = normalize_path(args.state)
    summary_path = normalize_path(args.summary)
    sent = sent_index(read_rows(normalize_path(args.sent_state)))

    if not token:
        write_rows(summary_path, [{"status": "missing_telegram_token", "feedback_rows": 0}], ["status", "feedback_rows"])
        print("TELEGRAM_BOT_TOKEN missing; no feedback request sent")
        return 1

    offset = state_value(state_path, "next_update_offset", "")
    params = {
        "limit": args.limit,
        "timeout": args.timeout,
        "allowed_updates": ["message", "message_reaction"],
    }
    if offset:
        params["offset"] = offset
    response = requests.get(GET_UPDATES_URL.format(token=token), params=params, timeout=args.timeout + 10)
    payload = response.json()
    if response.status_code >= 300 or not payload.get("ok"):
        raise RuntimeError(f"telegram getUpdates failed: http={response.status_code}; body={str(payload)[:300]}")

    updates = payload.get("result", [])
    rows = []
    max_update_id = None
    for update in updates if isinstance(updates, list) else []:
        try:
            max_update_id = max(max_update_id or int(update.get("update_id", 0)), int(update.get("update_id", 0)))
        except Exception:
            pass
        row = parse_update(update, sent)
        if row:
            rows.append(row)
    append_rows(output_path, rows, FEEDBACK_COLUMNS)
    if max_update_id is not None:
        write_state_value(state_path, "next_update_offset", str(max_update_id + 1))

    summary = {
        "status": "pass",
        "updates_read": len(updates) if isinstance(updates, list) else 0,
        "feedback_rows": len(rows),
        "matched_rows": sum(1 for row in rows if row.get("status") == "matched"),
        "positive_rows": sum(1 for row in rows if row.get("feedback_value") == "positive"),
        "negative_rows": sum(1 for row in rows if row.get("feedback_value") == "negative"),
        "comment_rows": sum(1 for row in rows if row.get("feedback_value") == "comment"),
        "output": str(output_path),
    }
    write_rows(summary_path, [summary], list(summary.keys()))
    print(f"feedback_rows={len(rows)}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
