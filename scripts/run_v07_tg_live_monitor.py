import argparse
import csv
import hashlib
import os
import re
import subprocess
import sys
import time
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
    "draft_id",
    "candidate_id",
    "event_type",
    "asset_symbol",
    "amount_usd",
    "severity_tier",
    "telegram_chat_id",
    "telegram_message_id",
    "text_hash",
    "status",
    "error",
]

QUALITY_REPORT_COLUMNS = [
    "checked_at_china",
    "draft_id",
    "candidate_id",
    "event_type",
    "asset_symbol",
    "amount_usd",
    "confidence_label",
    "strength_stars",
    "quality_status",
    "quality_score",
    "quality_flags",
]

RATE_LIMIT_REPORT_COLUMNS = [
    "checked_at_china",
    "draft_id",
    "candidate_id",
    "event_type",
    "asset_symbol",
    "amount_usd",
    "severity_tier",
    "time_window",
    "time_window_priority",
    "rate_limit_status",
    "rate_limit_flags",
]

SOURCE_DAILY_CAPS = {
    "whale_position": 8,
    "cex_netflow": 4,
    "stablecoin_flow": 4,
    "funding_rate": 3,
    "liquidation": 3,
    "onchain_transfer": 3,
    "exchange_listing": 6,
    "token_unlock": 4,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Continuously run v0.7 watchers and send validated TG drafts.")
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--max-cycles", type=int, default=0, help="0 means run forever.")
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--limit-alerts", type=int, default=100)
    parser.add_argument("--draft-input", default=str(ROOT / "data" / "tg_drafts_v07_watcher_private_pilot.csv"))
    parser.add_argument("--sent-state", default=str(ROOT / "data" / "tg_live_sent_state.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v07_tg_live_monitor_summary.csv"))
    parser.add_argument("--log", default=str(ROOT / "results" / "v07_tg_live_monitor.log"))
    parser.add_argument("--send", action="store_true", help="Actually send to Telegram. Omit for dry-run.")
    parser.add_argument("--max-send-per-cycle", type=int, default=3)
    parser.add_argument("--token-env", default="TELEGRAM_BOT_TOKEN")
    parser.add_argument("--chat-id-env", default="TELEGRAM_CHAT_ID")
    parser.add_argument("--api-key-env", default="ETHERSCAN_API_KEY")
    parser.add_argument("--load-local-secrets", default="true")
    parser.add_argument("--quality-gate", default="true")
    parser.add_argument("--quality-report", default=str(ROOT / "results" / "v07_tg_live_quality_gate_report.csv"))
    parser.add_argument("--quality-summary", default=str(ROOT / "results" / "v07_tg_live_quality_gate_summary.csv"))
    parser.add_argument("--daily-send-limit", type=int, default=15)
    parser.add_argument("--token-cooldown-minutes", type=int, default=60)
    parser.add_argument("--source-daily-caps", default="true")
    parser.add_argument("--time-policy", default="true")
    parser.add_argument("--time-policy-file", default=str(ROOT / "config" / "tg_send_time_policy.csv"))
    parser.add_argument("--rate-limit-report", default=str(ROOT / "results" / "v08_tg_rate_limit_report.csv"))
    parser.add_argument("--rate-limit-summary", default=str(ROOT / "results" / "v08_tg_rate_limit_summary.csv"))
    parser.add_argument("--performance-report", default=str(ROOT / "results" / "v08_tg_live_performance_report.md"))
    parser.add_argument("--performance-summary", default=str(ROOT / "results" / "v08_tg_live_performance_summary.csv"))
    parser.add_argument("--followup-report", default=str(ROOT / "results" / "v08_tg_alert_followup_report.md"))
    parser.add_argument("--followup-summary", default=str(ROOT / "results" / "v08_tg_alert_followup_summary.csv"))
    parser.add_argument("--followup-events", default=str(ROOT / "data" / "tg_alert_followup_events.csv"))
    parser.add_argument("--followup-backfill", default=str(ROOT / "results" / "v08_tg_alert_followup_backfill.csv"))
    parser.add_argument("--followup-quality", default=str(ROOT / "results" / "v08_tg_alert_followup_quality_report.csv"))
    parser.add_argument("--followup-min-age-hours", type=float, default=4)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def log_line(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{china_now()}] {text}"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line)


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
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    if exists:
        existing_rows = read_rows(path)
        existing_fields = list(existing_rows[0].keys()) if existing_rows else []
        if existing_fields and existing_fields != fieldnames:
            merged_fields = []
            for name in [*existing_fields, *fieldnames]:
                if name not in merged_fields:
                    merged_fields.append(name)
            write_rows(path, existing_rows, merged_fields)
            fieldnames = merged_fields
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def load_local_secrets(env: dict, enabled: str) -> dict:
    if str(enabled).strip().lower() not in {"1", "true", "yes", "y"}:
        return env
    path = ROOT / "config" / "local_secrets.ps1"
    if not path.exists():
        return env
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for name in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "ETHERSCAN_API_KEY"]:
        match = re.search(r"\$env:" + re.escape(name) + r"\s*=\s*['\"]([^'\"]+)['\"]", text)
        if match:
            env[name] = match.group(1).strip()
    return env


def text_hash(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8", errors="replace")).hexdigest()[:16]


def as_bool(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def safe_float(value: str) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return 0.0


def parse_china_time(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def today_china_date() -> str:
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")


def china_now_dt() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


def load_time_policy(path: Path) -> list[dict]:
    rows = read_rows(path)
    policy = []
    for row in rows:
        try:
            start_hour = int(str(row.get("start_hour", "")).strip())
            end_hour = int(str(row.get("end_hour", "")).strip())
        except Exception:
            continue
        if not (0 <= start_hour <= 23 and 1 <= end_hour <= 24):
            continue
        if start_hour >= end_hour:
            continue
        policy.append(
            {
                "window_label": str(row.get("window_label", "") or "default").strip() or "default",
                "start_hour": start_hour,
                "end_hour": end_hour,
                "window_priority": str(row.get("window_priority", "") or "normal").strip().lower(),
                "max_send_per_cycle": str(row.get("max_send_per_cycle", "") or "").strip(),
                "min_severity": str(row.get("min_severity", "") or "watch").strip().lower(),
            }
        )
    return policy


def current_time_window(policy: list[dict]) -> dict:
    hour = china_now_dt().hour
    for row in policy:
        if row["start_hour"] <= hour < row["end_hour"]:
            return row
    return {
        "window_label": "unconfigured",
        "start_hour": 0,
        "end_hour": 24,
        "window_priority": "normal",
        "max_send_per_cycle": "",
        "min_severity": "watch",
    }


def severity_rank(value: str) -> int:
    raw = str(value or "").strip().lower()
    return {"fyi": 0, "watch": 1, "high": 2, "critical": 3}.get(raw, 1)


def time_window_max_send(default_max: int, window: dict, enabled: bool) -> int:
    if not enabled:
        return default_max
    raw = str(window.get("max_send_per_cycle", "") or "").strip()
    if not raw:
        return default_max
    try:
        return max(0, int(raw))
    except Exception:
        return default_max


def star_count(value: str) -> int:
    text = str(value or "")
    count = text.count("★")
    if count:
        return count
    return text.count("鈽")


def confidence_score(label: str) -> int:
    raw = str(label or "").strip().lower()
    if raw in {"高", "high"}:
        return 25
    if raw in {"中", "medium"}:
        return 15
    if raw in {"低", "low"}:
        return -25
    if raw in {"样例", "sample"}:
        return -100
    return 5


def severity_tier(row: dict) -> str:
    explicit = str(row.get("severity_tier", "") or "").strip().lower()
    if explicit in {"critical", "high", "watch", "fyi"}:
        return explicit
    event_type = str(row.get("event_type", "") or "").strip()
    raw_signal = str(row.get("raw_signal_type", "") or "").strip()
    asset = str(row.get("asset_symbol", "") or "").strip().upper()
    amount = safe_float(row.get("amount_usd", ""))
    rate = safe_float(row.get("amount_native", ""))

    if event_type == "whale_position":
        if amount >= 100_000_000 or (asset == "HYPE" and amount >= 75_000_000):
            return "critical"
        if amount >= 50_000_000:
            return "high"
        return "watch"
    if event_type == "cex_netflow":
        if amount >= 500_000_000:
            return "critical"
        if amount >= 100_000_000:
            return "high"
        return "watch"
    if event_type == "stablecoin_flow":
        if amount >= 250_000_000:
            return "critical"
        if amount >= 100_000_000:
            return "high"
        return "watch"
    if event_type == "liquidation":
        if amount >= 10_000_000:
            return "critical"
        if amount >= 5_000_000:
            return "high"
        return "watch"
    if event_type == "funding_rate":
        if abs(rate) >= 0.002:
            return "critical"
        if abs(rate) >= 0.001:
            return "high"
        return "watch" if raw_signal else "fyi"
    if event_type == "exchange_listing":
        return "critical"
    if event_type == "token_unlock":
        if amount >= 50_000_000:
            return "high"
        return "watch"
    return "watch"


def quality_gate(row: dict) -> dict:
    flags: list[str] = []
    score = 0
    event_type = str(row.get("event_type", "") or "").strip()
    raw_signal = str(row.get("raw_signal_type", "") or "").strip()
    risk_category = str(row.get("risk_category", "") or "").strip()
    asset = str(row.get("asset_symbol", "") or "").strip().upper()
    amount = safe_float(row.get("amount_usd", ""))
    confidence = str(row.get("confidence_label", "") or "").strip()
    stars = star_count(str(row.get("strength_stars", "") or ""))
    text = str(row.get("approved_text", "") or row.get("draft_text", "") or "")

    if not row.get("candidate_id"):
        flags.append("missing_candidate_id")
    if not text:
        flags.append("missing_text")
    if not asset:
        flags.append("missing_asset")
    if amount <= 0 and event_type != "exchange_listing":
        flags.append("missing_amount_usd")

    score += confidence_score(confidence)
    score += min(25, max(0, int(amount / 5_000_000)))
    score += max(0, min(20, stars * 4))
    if event_type in {
        "stablecoin_flow",
        "whale_position",
        "onchain_transfer",
        "cex_netflow",
        "funding_rate",
        "liquidation",
        "exchange_listing",
        "token_unlock",
    }:
        score += 15
    else:
        flags.append("unknown_event_type")
        score -= 20

    if event_type == "stablecoin_flow":
        min_amount = 50_000_000
        if raw_signal == "stablecoin_burn":
            min_amount = 100_000_000
        if amount < min_amount:
            flags.append("below_stablecoin_threshold")
            score -= 35
    elif event_type == "whale_position":
        if amount < 20_000_000:
            flags.append("below_hyperliquid_position_threshold")
            score -= 35
        if amount >= 30_000_000:
            score += 8
        if asset == "HYPE" and amount >= 50_000_000:
            score += 8
    elif event_type == "onchain_transfer":
        min_amount = 5_000_000
        if risk_category == "protocol_treasury":
            min_amount = 2_000_000
        if amount < min_amount:
            flags.append("below_onchain_transfer_threshold")
            score -= 35
    elif event_type == "cex_netflow":
        if amount < 20_000_000:
            flags.append("below_cex_netflow_threshold")
            score -= 35
        if amount >= 50_000_000:
            score += 8
    elif event_type == "funding_rate":
        rate = safe_float(row.get("amount_native", ""))
        if abs(rate) < 0.0005:
            flags.append("below_funding_rate_threshold")
            score -= 35
        if abs(rate) >= 0.001:
            score += 8
    elif event_type == "liquidation":
        if amount < 1_000_000:
            flags.append("below_lending_liquidation_threshold")
            score -= 35
        if amount >= 5_000_000:
            score += 8
    elif event_type == "exchange_listing":
        if raw_signal != "cex_listing_announcement":
            flags.append("unexpected_listing_signal")
            score -= 20
        else:
            score += 20
    elif event_type == "token_unlock":
        if amount < 10_000_000:
            flags.append("below_token_unlock_threshold")
            score -= 35
        else:
            score += 10
        if amount >= 50_000_000:
            score += 8

    if confidence in {"低", "low", "样例", "sample"}:
        flags.append("low_or_sample_confidence")

    forbidden = ("买入", "卖出", "做多", "做空", "开多", "开空", "止盈", "止损")
    if any(word in text for word in forbidden):
        flags.append("contains_trading_advice_word")
        score -= 100

    if score < 55 and "low_quality_score" not in flags:
        flags.append("low_quality_score")

    if flags:
        fatal = {
            "missing_candidate_id",
            "missing_text",
            "missing_asset",
            "missing_amount_usd",
            "low_or_sample_confidence",
            "contains_trading_advice_word",
        }
        status = "fail" if any(flag in fatal for flag in flags) or score < 55 else "warning"
    else:
        status = "pass" if score >= 70 else "warning"
    if status == "warning" and score < 55:
        status = "fail"

    return {
        "checked_at_china": china_now(),
        "draft_id": str(row.get("draft_id", "") or "").strip(),
        "candidate_id": str(row.get("candidate_id", "") or "").strip(),
        "event_type": event_type,
        "asset_symbol": asset,
        "amount_usd": str(row.get("amount_usd", "") or "").strip(),
        "confidence_label": confidence,
        "strength_stars": str(row.get("strength_stars", "") or "").strip(),
        "quality_status": status,
        "quality_score": str(score),
        "quality_flags": ",".join(flags),
    }


def sent_candidate_ids(rows: list[dict]) -> set[str]:
    keys = set()
    for row in rows:
        if str(row.get("status", "")).strip().lower() == "sent":
            candidate_id = str(row.get("candidate_id", "")).strip()
            if candidate_id:
                keys.add(candidate_id)
    return keys


def sent_today_rows(rows: list[dict]) -> list[dict]:
    today = today_china_date()
    output = []
    for row in rows:
        if str(row.get("status", "")).strip().lower() != "sent":
            continue
        if str(row.get("sent_at_china", "")).startswith(today):
            output.append(row)
    return output


def rate_limit_gate(
    row: dict,
    sent_rows: list[dict],
    daily_send_limit: int,
    cooldown_minutes: int,
    source_caps_enabled: bool,
    time_policy_enabled: bool,
    time_window: dict,
) -> dict:
    flags = []
    event_type = str(row.get("event_type", "") or "").strip()
    asset = str(row.get("asset_symbol", "") or "").strip().upper()
    amount = str(row.get("amount_usd", "") or "").strip()
    tier = severity_tier(row)
    today_rows = sent_today_rows(sent_rows)

    if time_policy_enabled:
        min_severity = str(time_window.get("min_severity", "watch") or "watch").strip().lower()
        if severity_rank(tier) < severity_rank(min_severity):
            flags.append("time_window_min_severity_not_met")

    if daily_send_limit and len(today_rows) >= daily_send_limit:
        flags.append("daily_send_limit_reached")

    if source_caps_enabled:
        cap = SOURCE_DAILY_CAPS.get(event_type)
        if cap is not None:
            source_count = sum(1 for item in today_rows if str(item.get("event_type", "")).strip() == event_type)
            if source_count >= cap:
                flags.append("source_daily_cap_reached")

    now_local = datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)
    cooldown_key = (event_type, asset)
    if cooldown_minutes:
        for item in reversed(sent_rows):
            if str(item.get("status", "")).strip().lower() != "sent":
                continue
            item_key = (str(item.get("event_type", "")).strip(), str(item.get("asset_symbol", "")).strip().upper())
            if item_key != cooldown_key:
                continue
            sent_at = parse_china_time(str(item.get("sent_at_china", "")))
            if sent_at and (now_local - sent_at).total_seconds() < cooldown_minutes * 60:
                flags.append("token_cooldown_active")
                break

    return {
        "checked_at_china": china_now(),
        "draft_id": str(row.get("draft_id", "") or "").strip(),
        "candidate_id": str(row.get("candidate_id", "") or "").strip(),
        "event_type": event_type,
        "asset_symbol": asset,
        "amount_usd": amount,
        "severity_tier": tier,
        "time_window": str(time_window.get("window_label", "") or ""),
        "time_window_priority": str(time_window.get("window_priority", "") or ""),
        "rate_limit_status": "blocked" if flags else "pass",
        "rate_limit_flags": ",".join(flags),
    }


def run_pipeline(env: dict, hours: float, limit_alerts: int, log_path: Path) -> bool:
    cmd = [
        sys.executable,
        "scripts/run_v07_first_hand_watchers.py",
        "--hours",
        str(hours),
        "--limit-alerts",
        str(limit_alerts),
        "--sample-if-no-key",
        "false",
    ]
    result = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    if result.stdout:
        log_line(log_path, result.stdout.strip()[-1200:])
    if result.returncode != 0:
        log_line(log_path, f"pipeline_failed exit={result.returncode}; stderr={result.stderr[-800:]}")
        return False
    return True


def validate_drafts(input_path: Path, log_path: Path) -> bool:
    cmd = [
        sys.executable,
        "scripts/validate_tg_drafts.py",
        "--input",
        str(input_path),
        "--output",
        "results/tg_drafts_v07_watcher_validation_report.csv",
        "--summary",
        "results/tg_drafts_v07_watcher_validation_summary.csv",
        "--markdown-output",
        "results/tg_drafts_v07_watcher_validation_report.md",
    ]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if result.stdout:
        log_line(log_path, result.stdout.strip())
    if result.returncode != 0:
        log_line(log_path, f"draft_validation_failed exit={result.returncode}; stderr={result.stderr[-800:]}")
        return False
    rows = read_rows(ROOT / "results" / "tg_drafts_v07_watcher_validation_summary.csv")
    if not rows:
        return False
    summary = rows[0]
    return str(summary.get("status", "")).strip().lower() == "pass"


def summarize_followups(args: argparse.Namespace, log_path: Path) -> None:
    cmd = [
        sys.executable,
        "scripts/build_tg_alert_followup_report.py",
        "--sent-state",
        str(normalize_path(args.sent_state)),
        "--events-output",
        str(normalize_path(args.followup_events)),
        "--backfill-output",
        str(normalize_path(args.followup_backfill)),
        "--quality-output",
        str(normalize_path(args.followup_quality)),
        "--summary",
        str(normalize_path(args.followup_summary)),
        "--report",
        str(normalize_path(args.followup_report)),
        "--symbol-map",
        str(ROOT / "data" / "symbol_map.csv"),
        "--min-age-hours",
        str(args.followup_min_age_hours),
        "--limit",
        str(args.limit_alerts),
    ]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if result.stdout:
        log_line(log_path, result.stdout.strip())
    if result.returncode != 0:
        log_line(log_path, f"followup_summary_failed exit={result.returncode}; stderr={result.stderr[-800:]}")


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
    try:
        payload = response.json()
    except Exception:
        payload = {"ok": False, "description": response.text[:300]}
    if response.status_code >= 300 or not payload.get("ok"):
        raise RuntimeError(f"telegram send failed: http={response.status_code}; body={str(payload)[:300]}")
    result = payload.get("result", {})
    return result if isinstance(result, dict) else {}


def eligible_drafts(
    path: Path,
    state_path: Path,
    max_count: int,
    quality_gate_enabled: bool,
    quality_report_path: Path,
    quality_summary_path: Path,
    daily_send_limit: int,
    token_cooldown_minutes: int,
    source_caps_enabled: bool,
    time_policy_enabled: bool,
    time_window: dict,
    rate_limit_report_path: Path,
    rate_limit_summary_path: Path,
) -> list[tuple[dict, str, str]]:
    rows = read_rows(path)
    sent_rows = read_rows(state_path)
    already_sent = sent_candidate_ids(sent_rows)
    output = []
    quality_rows = []
    rate_rows = []
    for row in rows:
        text = str(row.get("approved_text", "") or row.get("draft_text", "") or "").strip()
        candidate_id = str(row.get("candidate_id", "") or "").strip()
        if not text or not candidate_id:
            continue
        if candidate_id in already_sent:
            continue
        quality = quality_gate(row)
        quality_rows.append(quality)
        if quality_gate_enabled and quality["quality_status"] == "fail":
            continue
        rate = rate_limit_gate(
            row,
            sent_rows,
            daily_send_limit,
            token_cooldown_minutes,
            source_caps_enabled,
            time_policy_enabled,
            time_window,
        )
        rate_rows.append(rate)
        if rate["rate_limit_status"] == "blocked":
            continue
        output.append((row, text, text_hash(text)))
        pending_sent = dict(row)
        pending_sent["status"] = "sent"
        pending_sent["sent_at_china"] = china_now()
        sent_rows.append(pending_sent)
        if max_count and len(output) >= max_count:
            break
    write_rows(quality_report_path, quality_rows, QUALITY_REPORT_COLUMNS)
    write_rows(rate_limit_report_path, rate_rows, RATE_LIMIT_REPORT_COLUMNS)
    summary = {
        "status": "pass",
        "checked_at_china": china_now(),
        "draft_rows_checked": len(quality_rows),
        "quality_pass_count": sum(1 for row in quality_rows if row["quality_status"] == "pass"),
        "quality_warning_count": sum(1 for row in quality_rows if row["quality_status"] == "warning"),
        "quality_fail_count": sum(1 for row in quality_rows if row["quality_status"] == "fail"),
        "eligible_after_quality_gate": len(output),
    }
    rate_summary = {
        "status": "pass",
        "checked_at_china": china_now(),
        "rate_rows_checked": len(rate_rows),
        "rate_pass_count": sum(1 for row in rate_rows if row["rate_limit_status"] == "pass"),
        "rate_blocked_count": sum(1 for row in rate_rows if row["rate_limit_status"] == "blocked"),
        "daily_send_limit": daily_send_limit,
        "token_cooldown_minutes": token_cooldown_minutes,
        "source_daily_caps_enabled": str(source_caps_enabled).lower(),
        "time_policy_enabled": str(time_policy_enabled).lower(),
        "time_window": str(time_window.get("window_label", "") or ""),
        "time_window_priority": str(time_window.get("window_priority", "") or ""),
        "time_window_min_severity": str(time_window.get("min_severity", "") or ""),
        "effective_max_send_per_cycle": max_count,
        "selected_after_rate_limit": len(output),
    }
    write_rows(quality_summary_path, [summary], list(summary.keys()))
    write_rows(rate_limit_summary_path, [rate_summary], list(rate_summary.keys()))
    return output


def main() -> int:
    args = parse_args()
    log_path = normalize_path(args.log)
    draft_path = normalize_path(args.draft_input)
    state_path = normalize_path(args.sent_state)
    summary_path = normalize_path(args.summary)
    quality_report_path = normalize_path(args.quality_report)
    quality_summary_path = normalize_path(args.quality_summary)
    rate_limit_report_path = normalize_path(args.rate_limit_report)
    rate_limit_summary_path = normalize_path(args.rate_limit_summary)
    time_policy_enabled = as_bool(args.time_policy)
    time_policy = load_time_policy(normalize_path(args.time_policy_file)) if time_policy_enabled else []
    env = load_local_secrets(os.environ.copy(), args.load_local_secrets)
    mode = "send" if args.send else "dry_run"
    quality_gate_enabled = as_bool(args.quality_gate)

    token = env.get(args.token_env, "").strip()
    chat_id = env.get(args.chat_id_env, "").strip()
    if args.send and (not token or not chat_id):
        log_line(log_path, "missing Telegram env; live send not started")
        write_rows(summary_path, [{"status": "missing_telegram_env", "mode": mode}], ["status", "mode"])
        return 1

    cycles = 0
    total_sent = 0
    total_failed = 0
    log_line(log_path, f"monitor_start mode={mode} interval_seconds={args.interval_seconds} time_policy={str(time_policy_enabled).lower()}")

    while True:
        cycles += 1
        cycle_sent = 0
        cycle_failed = 0
        ok = run_pipeline(env, args.hours, args.limit_alerts, log_path)
        if ok:
            ok = validate_drafts(draft_path, log_path)
        if ok:
            time_window = current_time_window(time_policy)
            effective_max_send_per_cycle = time_window_max_send(args.max_send_per_cycle, time_window, time_policy_enabled)
            for row, text, digest in eligible_drafts(
                draft_path,
                state_path,
                effective_max_send_per_cycle,
                quality_gate_enabled,
                quality_report_path,
                quality_summary_path,
                args.daily_send_limit,
                args.token_cooldown_minutes,
                as_bool(args.source_daily_caps),
                time_policy_enabled,
                time_window,
                rate_limit_report_path,
                rate_limit_summary_path,
            ):
                draft_id = str(row.get("draft_id", "")).strip()
                candidate_id = str(row.get("candidate_id", "")).strip()
                status = "dry_run"
                error = ""
                telegram_message_id = ""
                telegram_chat_id = ""
                try:
                    if args.send:
                        result = send_message(token, chat_id, text)
                        telegram_message_id = str(result.get("message_id", "") or "")
                        result_chat = result.get("chat", {}) if isinstance(result.get("chat", {}), dict) else {}
                        telegram_chat_id = str(result_chat.get("id", "") or chat_id)
                        status = "sent"
                        total_sent += 1
                        cycle_sent += 1
                    else:
                        log_line(log_path, f"dry_run_candidate draft_id={draft_id} candidate_id={candidate_id}")
                except Exception as exc:
                    status = "failed"
                    error = str(exc)[:300]
                    total_failed += 1
                    cycle_failed += 1
                append_row(
                    state_path,
                    {
                        "sent_at_china": china_now(),
                        "draft_id": draft_id,
                        "candidate_id": candidate_id,
                        "event_type": str(row.get("event_type", "") or "").strip(),
                        "asset_symbol": str(row.get("asset_symbol", "") or "").strip(),
                        "amount_usd": str(row.get("amount_usd", "") or "").strip(),
                        "severity_tier": severity_tier(row),
                        "telegram_chat_id": telegram_chat_id,
                        "telegram_message_id": telegram_message_id,
                        "text_hash": digest,
                        "status": status,
                        "error": error,
                    },
                    SENT_COLUMNS,
                )
                if args.send:
                    time.sleep(1.0)
        else:
            total_failed += 1
            cycle_failed += 1

        summarize_followups(args, log_path)

        write_rows(
            summary_path,
            [
                {
                    "status": "running" if args.max_cycles == 0 or cycles < args.max_cycles else "complete",
                    "mode": mode,
                    "cycles": cycles,
                    "total_sent": total_sent,
                    "total_failed": total_failed,
                    "last_cycle_sent": cycle_sent,
                    "last_cycle_failed": cycle_failed,
                    "updated_at_china": china_now(),
                }
            ],
            ["status", "mode", "cycles", "total_sent", "total_failed", "last_cycle_sent", "last_cycle_failed", "updated_at_china"],
        )
        log_line(log_path, f"cycle_complete cycle={cycles} sent={cycle_sent} failed={cycle_failed}")

        if args.max_cycles and cycles >= args.max_cycles:
            break
        time.sleep(max(10, args.interval_seconds))

    return 0 if total_failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
