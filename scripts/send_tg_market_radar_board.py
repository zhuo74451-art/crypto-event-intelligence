import argparse
import csv
import hashlib
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


SENT_COLUMNS = [
    "sent_at_china",
    "board_id",
    "board_label",
    "telegram_chat_id",
    "telegram_message_id",
    "text_hash",
    "status",
    "error",
]


SUMMARY_COLUMNS = [
    "status",
    "mode",
    "board_id",
    "board_label",
    "telegram_chat_id",
    "telegram_message_id",
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send the latest v0.9 TG market-radar board.")
    parser.add_argument("--input", default=str(ROOT / "data" / "tg_market_radar_boards.csv"))
    parser.add_argument("--sent-state", default=str(ROOT / "data" / "tg_board_sent_state.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v09_tg_market_radar_send_summary.csv"))
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--token-env", default="TELEGRAM_BOT_TOKEN")
    parser.add_argument("--chat-id-env", default="TELEGRAM_CHAT_ID")
    parser.add_argument("--load-local-secrets", default="true")
    parser.add_argument("--record-ledger", default="true")
    parser.add_argument("--ledger", default=str(ROOT / "data" / "tg_alert_ledger.csv"))
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0)


def china_stamp() -> str:
    return china_now().strftime("%Y-%m-%d %H:%M:%S UTC+8")


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


def append_row(path: Path, row: dict, fieldnames: list[str]) -> None:
    rows = read_rows(path)
    rows.append(row)
    write_rows(path, rows, fieldnames)


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def load_local_secrets(env: dict, enabled: str) -> dict:
    if not truthy(enabled):
        return env
    path = ROOT / "config" / "local_secrets.ps1"
    if not path.exists():
        return env
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for name in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
        match = re.search(r"\$env:" + re.escape(name) + r"\s*=\s*['\"]([^'\"]+)['\"]", text)
        if match:
            env[name] = match.group(1).strip()
    return env


def text_hash(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8", errors="replace")).hexdigest()[:16]


def dedupe_key(row: dict) -> str:
    label = str(row.get("board_label", "") or "").strip()
    hour = china_now().strftime("%Y-%m-%d %H")
    return f"{label}|{hour}"


def already_sent_this_hour(sent_rows: list[dict], board_row: dict) -> bool:
    key = dedupe_key(board_row)
    for row in sent_rows:
        if str(row.get("status", "") or "").strip().lower() != "sent":
            continue
        sent_at = str(row.get("sent_at_china", "") or "")
        if not sent_at.startswith(china_now().strftime("%Y-%m-%d %H")):
            continue
        if str(row.get("board_label", "") or "").strip() and key == f"{row.get('board_label')}|{sent_at[:13]}":
            return True
    return False


def send_message(token: str, chat_id: str, text: str) -> dict:
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
    if response.status_code >= 300 or not payload.get("ok"):
        raise RuntimeError(f"telegram send failed: http={response.status_code}; body={str(payload)[:300]}")
    result = payload.get("result", {})
    return result if isinstance(result, dict) else {}


def record_ledger(args: argparse.Namespace, board: dict, status: str, chat_id: str, message_id: str) -> None:
    if not truthy(args.record_ledger):
        return
    if str(board.get("section_count", "") or "0").strip() in {"", "0"}:
        return
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "record_tg_alert_ledger.py"),
        "--board-id",
        str(board.get("board_id", "") or ""),
        "--board-label",
        str(board.get("board_label", "") or ""),
        "--telegram-chat-id",
        chat_id,
        "--telegram-message-id",
        message_id,
        "--send-status",
        status,
        "--published-at-china",
        china_stamp(),
        "--ledger",
        str(normalize_path(args.ledger)),
    ]
    result = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
    if result.returncode != 0:
        print(((result.stdout or "") + "\n" + (result.stderr or "")).strip()[-800:])


def main() -> int:
    args = parse_args()
    board_rows = read_rows(normalize_path(args.input))
    if not board_rows:
        summary = {"status": "no_board", "mode": "send" if args.send else "dry_run", "board_id": "", "board_label": "", "telegram_chat_id": "", "telegram_message_id": "", "error": ""}
        write_rows(normalize_path(args.summary), [summary], SUMMARY_COLUMNS)
        print("no board rows found")
        return 1

    board = board_rows[-1]
    text = str(board.get("board_text", "") or "").strip()
    if not text:
        summary = {"status": "empty_board_text", "mode": "send" if args.send else "dry_run", "board_id": board.get("board_id", ""), "board_label": board.get("board_label", ""), "telegram_chat_id": "", "telegram_message_id": "", "error": ""}
        write_rows(normalize_path(args.summary), [summary], SUMMARY_COLUMNS)
        return 1
    if str(board.get("section_count", "") or "0").strip() in {"", "0"}:
        summary = {"status": "skipped_no_new_items", "mode": "send" if args.send else "dry_run", "board_id": board.get("board_id", ""), "board_label": board.get("board_label", ""), "telegram_chat_id": "", "telegram_message_id": "", "error": ""}
        write_rows(normalize_path(args.summary), [summary], SUMMARY_COLUMNS)
        print("skipped board with no new items")
        return 0

    sent_state = normalize_path(args.sent_state)
    sent_rows = read_rows(sent_state)
    mode = "send" if args.send else "dry_run"
    if not args.force and already_sent_this_hour(sent_rows, board):
        summary = {"status": "skipped_duplicate_hour", "mode": mode, "board_id": board.get("board_id", ""), "board_label": board.get("board_label", ""), "telegram_chat_id": "", "telegram_message_id": "", "error": ""}
        write_rows(normalize_path(args.summary), [summary], SUMMARY_COLUMNS)
        print("skipped duplicate board for this hour")
        return 0

    import os

    env = load_local_secrets(os.environ.copy(), args.load_local_secrets)
    token = env.get(args.token_env, "").strip()
    chat_id = env.get(args.chat_id_env, "").strip()
    status = "dry_run"
    error = ""
    telegram_message_id = ""
    telegram_chat_id = ""
    try:
        if args.send:
            if not token or not chat_id:
                raise RuntimeError("missing Telegram token or chat id")
            result = send_message(token, chat_id, text)
            telegram_message_id = str(result.get("message_id", "") or "")
            result_chat = result.get("chat", {}) if isinstance(result.get("chat", {}), dict) else {}
            telegram_chat_id = str(result_chat.get("id", "") or chat_id)
            status = "sent"
        else:
            print(text)
    except Exception as exc:
        status = "failed"
        error = str(exc)[:300]

    if args.send:
        append_row(
            sent_state,
            {
                "sent_at_china": china_stamp(),
                "board_id": board.get("board_id", ""),
                "board_label": board.get("board_label", ""),
                "telegram_chat_id": telegram_chat_id,
                "telegram_message_id": telegram_message_id,
                "text_hash": text_hash(text),
                "status": status,
                "error": error,
            },
            SENT_COLUMNS,
        )
        record_ledger(args, board, status, telegram_chat_id or chat_id, telegram_message_id)
    summary = {
        "status": status,
        "mode": mode,
        "board_id": board.get("board_id", ""),
        "board_label": board.get("board_label", ""),
        "telegram_chat_id": telegram_chat_id,
        "telegram_message_id": telegram_message_id,
        "error": error,
    }
    write_rows(normalize_path(args.summary), [summary], SUMMARY_COLUMNS)
    print(f"board send status={status}")
    return 0 if status in {"sent", "dry_run"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
