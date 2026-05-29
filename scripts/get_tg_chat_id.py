import argparse
import csv
import os
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read Telegram bot updates and list chat IDs. Token is read from env only.")
    parser.add_argument("--token-env", default="TELEGRAM_BOT_TOKEN")
    parser.add_argument("--output", default=str(ROOT / "results" / "tg_chat_id_candidates.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_chat_id_candidates_summary.csv"))
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--proxy", default="", help="Optional proxy, for example http://127.0.0.1:7897")
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def chat_from_update(update: dict) -> dict | None:
    for key in ("message", "channel_post", "edited_message", "edited_channel_post", "my_chat_member"):
        item = update.get(key)
        if not isinstance(item, dict):
            continue
        chat = item.get("chat") if key != "my_chat_member" else item.get("chat")
        if isinstance(chat, dict):
            return {
                "update_id": update.get("update_id", ""),
                "source_field": key,
                "chat_id": chat.get("id", ""),
                "chat_type": chat.get("type", ""),
                "title": chat.get("title", ""),
                "username": chat.get("username", ""),
                "first_name": chat.get("first_name", ""),
                "last_name": chat.get("last_name", ""),
                "date": item.get("date", ""),
            }
    return None


def main() -> int:
    args = parse_args()
    token = os.environ.get(args.token_env, "").strip()
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    if not token:
        write_rows(
            summary_path,
            [
                {
                    "status": "missing_token",
                    "candidate_count": 0,
                    "message": f"Set {args.token_env} in current PowerShell process.",
                }
            ],
            ["status", "candidate_count", "message"],
        )
        print(f"missing {args.token_env}")
        return 1

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None
        response = requests.get(url, params={"allowed_updates": "[]"}, timeout=args.timeout, proxies=proxies)
    except requests.RequestException as exc:
        write_rows(
            summary_path,
            [
                {
                    "status": "request_failed",
                    "candidate_count": 0,
                    "message": str(exc).replace(token, "<redacted>")[:200],
                }
            ],
            ["status", "candidate_count", "message"],
        )
        print(f"request_failed={str(exc).replace(token, '<redacted>')[:200]}")
        return 2
    try:
        payload = response.json()
    except Exception:
        payload = {"ok": False, "description": response.text[:300]}
    if response.status_code >= 300 or not payload.get("ok"):
        write_rows(
            summary_path,
            [
                {
                    "status": "telegram_error",
                    "candidate_count": 0,
                    "message": str(payload.get("description", ""))[:200],
                }
            ],
            ["status", "candidate_count", "message"],
        )
        print(f"telegram_error={str(payload.get('description', ''))[:200]}")
        return 2

    rows = []
    seen = set()
    for update in payload.get("result", []):
        row = chat_from_update(update)
        if not row:
            continue
        key = str(row.get("chat_id", ""))
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)

    write_rows(
        output_path,
        rows,
        ["update_id", "source_field", "chat_id", "chat_type", "title", "username", "first_name", "last_name", "date"],
    )
    status = "pass" if rows else "no_updates"
    message = "ok" if rows else "Add the bot to the group, send a message in the group, then run again."
    write_rows(
        summary_path,
        [{"status": status, "candidate_count": len(rows), "message": message}],
        ["status", "candidate_count", "message"],
    )
    print(f"status={status}")
    print(f"candidate_count={len(rows)}")
    for row in rows:
        print(f"chat_id={row['chat_id']} type={row['chat_type']} title={row['title'] or row['username']}")
    return 0 if rows else 3


if __name__ == "__main__":
    raise SystemExit(main())
