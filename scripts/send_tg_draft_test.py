import argparse
import csv
import os
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
    parser = argparse.ArgumentParser(description="Manually send a small TG draft test batch. Default is dry-run.")
    parser.add_argument("--input", default=str(ROOT / "data" / "tg_drafts_v07_watcher_private_pilot.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_draft_test_send_summary.csv"))
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--send", action="store_true", help="Actually call Telegram sendMessage. Omit for dry-run.")
    parser.add_argument("--token-env", default="TELEGRAM_BOT_TOKEN")
    parser.add_argument("--chat-id-env", default="TELEGRAM_CHAT_ID")
    parser.add_argument("--only-approved", action="store_true", help="Only send reviewer_decision=approve or approved_text rows.")
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_summary(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)


def approved(row: dict) -> bool:
    decision = str(row.get("reviewer_decision", "") or "").strip().lower()
    approved_text = str(row.get("approved_text", "") or "").strip()
    return bool(approved_text or decision in {"approve", "approved", "include"})


def message_text(row: dict) -> str:
    return str(row.get("approved_text", "") or row.get("draft_text", "") or "").strip()


def send_message(token: str, chat_id: str, text: str, timeout: int = 20) -> dict:
    url = TELEGRAM_API.format(token=token)
    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=timeout,
    )
    try:
        payload = response.json()
    except Exception:
        payload = {"ok": False, "description": response.text[:300]}
    if response.status_code >= 300 or not payload.get("ok"):
        raise RuntimeError(f"telegram send failed: http={response.status_code}; body={str(payload)[:300]}")
    return payload


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    summary_path = normalize_path(args.summary)
    rows = read_rows(input_path)
    candidates = []
    for row in rows:
        if str(row.get("auto_send_enabled", "")).strip().lower() == "true":
            print(f"refusing row with auto_send_enabled=true: {row.get('draft_id')}")
            continue
        if args.only_approved and not approved(row):
            continue
        text = message_text(row)
        if text:
            candidates.append((row, text))
        if args.limit and len(candidates) >= args.limit:
            break

    token = os.environ.get(args.token_env, "").strip()
    chat_id = os.environ.get(args.chat_id_env, "").strip()
    sent = 0
    failed = 0
    mode = "send" if args.send else "dry_run"

    if args.send and (not token or not chat_id):
        write_summary(
            summary_path,
            {
                "mode": mode,
                "input_rows": len(rows),
                "candidate_rows": len(candidates),
                "sent_rows": 0,
                "failed_rows": 0,
                "status": "missing_telegram_env",
                "message": f"Set {args.token_env} and {args.chat_id_env} in current terminal.",
            },
        )
        print(f"missing Telegram env: {args.token_env}, {args.chat_id_env}")
        return 1

    for row, text in candidates:
        print(f"[{mode}] {row.get('draft_id')} {row.get('candidate_id')}")
        if not args.send:
            print(text[:500])
            print("")
            continue
        try:
            send_message(token, chat_id, text)
            sent += 1
            time.sleep(max(0.0, args.sleep_seconds))
        except Exception as exc:
            failed += 1
            print(f"send failed for {row.get('draft_id')}: {exc}")

    status = "pass" if failed == 0 else "fail"
    write_summary(
        summary_path,
        {
            "mode": mode,
            "input_rows": len(rows),
            "candidate_rows": len(candidates),
            "sent_rows": sent,
            "failed_rows": failed,
            "status": status,
            "message": "ok",
        },
    )
    print(f"mode={mode}")
    print(f"candidate_rows={len(candidates)}")
    print(f"sent_rows={sent}")
    print(f"failed_rows={failed}")
    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
