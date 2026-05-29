import argparse
import csv
import os
import re
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a deduplicated Chinese TG alert quality summary card.")
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_alert_quality_daily_summary.csv"))
    parser.add_argument("--report", default=str(ROOT / "results" / "tg_alert_quality_daily.md"))
    parser.add_argument("--state", default=str(ROOT / "data" / "tg_quality_summary_send_state.csv"))
    parser.add_argument("--token-env", default="TELEGRAM_BOT_TOKEN")
    parser.add_argument("--chat-id-env", default="TELEGRAM_CHAT_ID")
    parser.add_argument("--load-local-secrets", default="true")
    parser.add_argument("--min-computed", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--send", action="store_true")
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_stamp() -> str:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def read_first_row(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[0] if rows else {}


def write_state(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerow(row)


def safe_int(value) -> int:
    try:
        return int(float(str(value or "0").strip()))
    except Exception:
        return 0


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


def html_escape(text: str) -> str:
    return str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_text(summary: dict) -> str:
    computed_1h = safe_int(summary.get("computed_1h"))
    computed_4h = safe_int(summary.get("computed_4h"))
    computed_24h = safe_int(summary.get("computed_24h"))
    computed_72h = safe_int(summary.get("computed_72h"))
    best_24h = summary.get("best_event_type_24h") or "暂无"
    worst_24h = summary.get("worst_event_type_24h") or "暂无"
    lines = [
        "<b>🧪 TG 情报效果追踪</b>",
        "",
        f"时间：{china_stamp()}",
        f"已评价：{html_escape(summary.get('outcome_rows', '0'))} 条",
        f"部分成熟：{html_escape(summary.get('partial_rows', '0'))} 条｜完整成熟：{html_escape(summary.get('ok_rows', '0'))} 条",
        f"可计算：1h {computed_1h}｜4h {computed_4h}｜24h {computed_24h}｜72h {computed_72h}",
        "",
        f"24h 暂优类型：{html_escape(best_24h)}",
        f"24h 暂弱类型：{html_escape(worst_24h)}",
        "",
        "用途：只判断情报质量和事件类型有效性，不构成任何交易建议。",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    summary_path = normalize_path(args.summary)
    state_path = normalize_path(args.state)
    summary = read_first_row(summary_path)
    if not summary:
        print("missing quality summary")
        return 2

    computed_total = sum(safe_int(summary.get(f"computed_{horizon}")) for horizon in ["1h", "4h", "24h", "72h"])
    signature = "|".join(str(summary.get(f"computed_{horizon}", "")) for horizon in ["1h", "4h", "24h", "72h"])
    previous = read_first_row(state_path)
    if not args.force:
        if computed_total < args.min_computed:
            print(f"skip: computed_total={computed_total} < min_computed={args.min_computed}")
            return 0
        if previous.get("signature") == signature:
            print(f"skip: duplicate signature={signature}")
            return 0

    text = build_text(summary)
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
    result = send_message(token, chat_id, text)
    write_state(
        state_path,
        {
            "sent_at_china": china_stamp(),
            "signature": signature,
            "telegram_chat_id": chat_id,
            "telegram_message_id": str(result.get("message_id", "")),
        },
    )
    print(f"sent quality summary card message_id={result.get('message_id', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
