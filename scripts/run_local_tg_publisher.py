"""
Local TG Publisher — v16 Event Cards to Telegram Bridge.

Reads config from environment or config/local_tg_publisher.env.
Runs the v16 pipeline (build_raw → aggregate → render) on each cycle,
then sends new cards to Telegram with dedup, rate limiting, and logging.

Default: DRY_RUN=true (preview only, no actual TG send).

Usage:
    python scripts/run_local_tg_publisher.py                 # dry-run (default)
    python scripts/run_local_tg_publisher.py --dry-run false  # real send
    python scripts/run_local_tg_publisher.py --once           # single cycle, then exit
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import os
import sqlite3
import subprocess
import sys
import time
import traceback
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

# ── telegram API ────────────────────────────────────────────
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# ── banned content keywords (trading advice filter) ─────────
BANNED_KEYWORDS = [
    "买入", "卖出", "做多", "做空", "开仓", "止盈", "止损",
    "建议入场", "建议出场", "追涨", "杀跌", "抄底", "逃顶",
    "all in", "满仓", "空仓", "杠杆", "合约建议",
]

# ── required disclaimer ─────────────────────────────────────
DISCLAIMER = "⚠️ 仅作市场结构与链上情报观察，不构成任何交易建议。"


# ═══════════════════════════════════════════════════════════════
# config loading
# ═══════════════════════════════════════════════════════════════

def load_env_config(env_path: str | None = None) -> dict[str, str]:
    """Load config from a .env file (KEY=VALUE lines) into a dict.
    Does NOT modify os.environ — returns a dict so values are never
    leaked into subprocess environments.
    """
    cfg: dict[str, str] = {}
    paths = []
    if env_path:
        paths.append(Path(env_path))
    paths.append(ROOT / "config" / "local_tg_publisher.env")

    for p in paths:
        if not p.exists():
            continue
        for raw in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            cfg[k] = v
    return cfg


def get_config(env_path: str | None = None) -> dict[str, Any]:
    """Merge .env file + os.environ (os.environ takes precedence)."""
    cfg = load_env_config(env_path)
    for k in cfg:
        if k in os.environ:
            cfg[k] = os.environ[k]
    return cfg


# ═══════════════════════════════════════════════════════════════
# logging
# ═══════════════════════════════════════════════════════════════

def log_path(cfg: dict[str, Any]) -> Path:
    p = cfg.get("LOG_PATH", "")
    if p:
        return Path(p) if Path(p).is_absolute() else ROOT / p
    return ROOT / "logs" / "local_tg_publisher.log"


def ensure_log_dir(lp: Path) -> None:
    lp.parent.mkdir(parents=True, exist_ok=True)


def write_log(lp: Path, level: str, message: str) -> None:
    ts = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    line = f"[{ts}] [{level}] {message}"
    ensure_log_dir(lp)
    with lp.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


# ═══════════════════════════════════════════════════════════════
# SQLite state
# ═══════════════════════════════════════════════════════════════

def state_db_path(cfg: dict[str, Any]) -> Path:
    p = cfg.get("STATE_DB_PATH", "")
    if p:
        return Path(p) if Path(p).is_absolute() else ROOT / p
    return ROOT / "data" / "local_tg_publisher_state.sqlite"


def init_state_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent_events (
            event_id       TEXT NOT NULL,
            content_hash   TEXT NOT NULL,
            sent_at        TEXT NOT NULL,
            telegram_chat_id TEXT NOT NULL DEFAULT '',
            telegram_msg_id TEXT NOT NULL DEFAULT '',
            status         TEXT NOT NULL DEFAULT 'sent',
            error          TEXT NOT NULL DEFAULT '',
            card_title     TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (event_id, telegram_chat_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cycle_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at     TEXT NOT NULL,
            finished_at    TEXT NOT NULL,
            signals_built  INTEGER NOT NULL DEFAULT 0,
            events_agg     INTEGER NOT NULL DEFAULT 0,
            cards_rendered INTEGER NOT NULL DEFAULT 0,
            cards_sent     INTEGER NOT NULL DEFAULT 0,
            cards_skipped  INTEGER NOT NULL DEFAULT 0,
            dry_run        INTEGER NOT NULL DEFAULT 1,
            error          TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.commit()
    return conn


def is_already_sent(conn: sqlite3.Connection, content_hash: str, chat_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sent_events WHERE content_hash = ? AND telegram_chat_id = ? AND status = 'sent'",
        (content_hash, chat_id),
    ).fetchone()
    return row is not None


def record_send(conn: sqlite3.Connection, event_id: str, content_hash: str,
                chat_id: str, msg_id: str, status: str, error: str, title: str) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO sent_events
           (event_id, content_hash, sent_at, telegram_chat_id, telegram_msg_id, status, error, card_title)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (event_id, content_hash, datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8"),
         chat_id, msg_id, status, error, title),
    )
    conn.commit()


# ═══════════════════════════════════════════════════════════════
# v16 pipeline
# ═══════════════════════════════════════════════════════════════

def run_v16_pipeline(cfg: dict[str, Any]) -> tuple[bool, str, int, int, int]:
    """Run the v16 three-step pipeline. Returns (ok, output, signals, events, cards)."""
    py = sys.executable
    steps = [
        ("build_raw_signals", [py, str(ROOT / "scripts" / "build_raw_signals.py")]),
        ("aggregate_signals", [py, str(ROOT / "scripts" / "aggregate_signals_to_events.py")]),
        ("render_cards", [py, str(ROOT / "scripts" / "render_asset_event_cards.py")]),
    ]
    last_output = ""
    signals_count = 0
    events_count = 0
    cards_count = 0

    for name, cmd in steps:
        result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                                text=True, encoding="utf-8", errors="replace",
                                timeout=300)
        last_output = (result.stdout + "\n" + result.stderr).strip()
        if result.returncode != 0:
            return False, f"{name} failed (exit={result.returncode}):\n{last_output[-500:]}", 0, 0, 0
        # Extract counts from output
        if name == "build_raw_signals":
            for line in result.stdout.splitlines():
                if "Total signals:" in line:
                    try:
                        signals_count = int(line.split(":")[-1].strip())
                    except ValueError:
                        pass
        elif name == "aggregate_signals":
            for line in result.stdout.splitlines():
                if "Aggregated events:" in line:
                    try:
                        events_count = int(line.split(":")[-1].strip())
                    except ValueError:
                        pass
        elif name == "render_cards":
            for line in result.stdout.splitlines():
                if "Asset cards summary:" in line:
                    cards_count = 1  # signal that it ran

    # Read summary for card count
    summary_path = ROOT / "results" / "v16_asset_event_cards_summary.csv"
    if summary_path.exists():
        try:
            with summary_path.open("r", encoding="utf-8-sig") as fh:
                rows = list(csv.DictReader(fh))
                if rows:
                    cards_count = int(rows[0].get("card_count", cards_count))
        except Exception:
            pass

    return True, last_output, signals_count, events_count, cards_count


# ═══════════════════════════════════════════════════════════════
# card parsing
# ═══════════════════════════════════════════════════════════════

def parse_cards_from_md(md_path: Path) -> list[dict[str, str]]:
    """Parse v16_asset_event_cards.md into individual card dicts."""
    if not md_path.exists():
        return []

    text = md_path.read_text(encoding="utf-8")
    cards: list[dict[str, str]] = []
    current_card: dict[str, str] | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## ") and "资产动态" in line:
            # Save previous card
            if current_card and current_lines:
                current_card["body"] = "\n".join(current_lines)
                cards.append(current_card)
            # Start new card
            current_card = {"title": line.lstrip("# ").strip()}
            current_lines = []
        elif current_card is not None:
            current_lines.append(line)

    # Save last card
    if current_card and current_lines:
        current_card["body"] = "\n".join(current_lines)
        cards.append(current_card)

    return cards


def card_to_tg_html(card: dict[str, str]) -> str:
    """Convert one card dict into a Telegram HTML message string."""
    title = card.get("title", "资产动态")
    body = card.get("body", "")

    # Extract key fields from body
    lines = body.splitlines()
    window = ""
    signal_info = ""
    strength = ""
    sections: dict[str, list[str]] = {}
    current_section = "_header"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("时间窗口："):
            window = stripped
        elif stripped.startswith("信号数量："):
            signal_info = stripped
        elif stripped.startswith("综合强度："):
            strength = stripped
        elif stripped.startswith("### "):
            current_section = stripped.lstrip("# ").strip()
            sections[current_section] = []
        elif stripped.startswith("> ⚠️"):
            sections.setdefault("disclaimer", []).append(stripped.lstrip("> "))
        elif stripped.startswith("- "):
            sections.setdefault(current_section, []).append(stripped)
        elif stripped.startswith("---"):
            continue
        elif stripped:
            sections.setdefault(current_section, []).append(stripped)

    # Build HTML message
    parts = [f"<b>{html.escape(title)}</b>", ""]
    if window:
        parts.append(f"<i>{html.escape(window)}</i>")
    if signal_info:
        parts.append(html.escape(signal_info))
    if strength:
        parts.append(html.escape(strength))
    parts.append("")

    # What happened
    if "发生了什么" in sections:
        parts.append("<b>发生了什么</b>")
        for item in sections["发生了什么"][:3]:
            parts.append(html.escape(item))
        parts.append("")

    # Why important
    if "为什么重要" in sections:
        parts.append("<b>为什么重要</b>")
        for item in sections["为什么重要"][:2]:
            parts.append(html.escape(item))
        parts.append("")

    # Observation points
    if "观察点" in sections:
        parts.append("<b>观察点</b>")
        for item in sections["观察点"][:3]:
            parts.append(html.escape(item))
        parts.append("")

    parts.append(DISCLAIMER)
    return "\n".join(parts)


def filter_trading_content(text: str) -> tuple[bool, list[str]]:
    """Check if text contains banned trading-advice keywords.
    Returns (is_clean, list_of_hits).
    """
    hits = [kw for kw in BANNED_KEYWORDS if kw in text]
    return len(hits) == 0, hits


# ═══════════════════════════════════════════════════════════════
# telegram send
# ═══════════════════════════════════════════════════════════════

def send_telegram_message(token: str, chat_id: str, text: str,
                          dry_run: bool = True) -> tuple[str, str]:
    """Send a message via Telegram Bot API.
    Returns (message_id_or_empty, error_or_empty).
    If dry_run=True, returns ("dry_run", "") without calling API.
    """
    if dry_run:
        return "dry_run", ""

    if not token or not chat_id:
        return "", "missing token or chat_id"

    # Final trading-content check
    is_clean, hits = filter_trading_content(text)
    if not is_clean:
        return "", f"blocked: trading keywords found: {hits}"

    payload = {
        "chat_id": chat_id,
        "text": text,
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
        return "", f"HTTP {e.code}: {err_body[:200]}"
    except Exception as e:
        return "", str(e)[:200]

    try:
        import json
        result = json.loads(body)
        if result.get("ok"):
            msg_id = str(result["result"].get("message_id", ""))
            return msg_id, ""
        return "", f"API error: {body[:200]}"
    except Exception:
        return "", f"parse error: {body[:200]}"


# ═══════════════════════════════════════════════════════════════
# main loop
# ═══════════════════════════════════════════════════════════════

def run_once(cfg: dict[str, Any], conn: sqlite3.Connection, lp: Path) -> dict[str, int]:
    """Execute one cycle. Returns summary counts."""
    dry_run = str(cfg.get("DRY_RUN", "true")).strip().lower() in ("true", "1", "yes", "y")
    max_send = int(cfg.get("MAX_SEND_PER_CYCLE", "3"))
    token = cfg.get("TELEGRAM_BOT_TOKEN", "")
    chat_ids_raw = cfg.get("TELEGRAM_CHAT_ID", "")
    chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()] if chat_ids_raw else []

    started = datetime.now(CN_TZ)
    write_log(lp, "INFO", f"=== Cycle start (dry_run={dry_run}) ===")

    # Step 1: run v16 pipeline
    write_log(lp, "INFO", "Running v16 pipeline...")
    ok, output, sig_count, ev_count, card_count = run_v16_pipeline(cfg)
    if not ok:
        write_log(lp, "ERROR", f"Pipeline failed: {output}")
        return {"signals": sig_count, "events": ev_count, "cards": card_count, "sent": 0, "skipped": 0}

    write_log(lp, "INFO", f"Pipeline ok: {sig_count} signals, {ev_count} events, {card_count} cards")

    # Step 2: parse cards
    md_path = ROOT / "results" / "v16_asset_event_cards.md"
    cards = parse_cards_from_md(md_path)
    write_log(lp, "INFO", f"Parsed {len(cards)} cards from {md_path}")

    if not cards:
        write_log(lp, "INFO", "No cards to send")
        conn.execute(
            "INSERT INTO cycle_log (started_at, finished_at, signals_built, events_agg, cards_rendered, cards_sent, cards_skipped, dry_run, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (started.strftime("%Y-%m-%d %H:%M:%S UTC+8"),
             datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8"),
             sig_count, ev_count, card_count, 0, 0, int(dry_run), ""),
        )
        conn.commit()
        return {"signals": sig_count, "events": ev_count, "cards": card_count, "sent": 0, "skipped": len(cards)}

    # Step 3: dedup, rate-limit, send
    sent_count = 0
    skipped_count = 0
    for card in cards:
        tg_text = card_to_tg_html(card)
        content_hash = hashlib.sha256(tg_text.encode("utf-8")).hexdigest()

        event_id = card.get("title", content_hash[:16])
        card_title = card.get("title", "")[:120]

        for chat_id in chat_ids:
            if is_already_sent(conn, content_hash, chat_id):
                write_log(lp, "DEBUG", f"Dedup skip: {card_title[:60]} (chat={chat_id[-8:]})")
                skipped_count += 1
                continue

            if sent_count >= max_send:
                write_log(lp, "INFO", f"Rate limit reached ({max_send}/cycle), {len(cards) - sent_count} remaining")
                skipped_count += 1
                continue

            if dry_run:
                write_log(lp, "DRYRUN", f"Would send to {chat_id[-8:]}: {card_title[:60]}")
                record_send(conn, event_id, content_hash, chat_id, "dry_run",
                            "dry_run", "", card_title)
                sent_count += 1
            else:
                msg_id, error = send_telegram_message(token, chat_id, tg_text, dry_run=False)
                if error:
                    write_log(lp, "ERROR", f"Send failed to {chat_id[-8:]}: {error}")
                    record_send(conn, event_id, content_hash, chat_id, "",
                                "failed", error, card_title)
                    skipped_count += 1
                else:
                    write_log(lp, "SENT", f"msg_id={msg_id} to {chat_id[-8:]}: {card_title[:60]}")
                    record_send(conn, event_id, content_hash, chat_id, msg_id,
                                "sent", "", card_title)
                    sent_count += 1

    # Step 4: cycle log
    finished = datetime.now(CN_TZ)
    conn.execute(
        "INSERT INTO cycle_log (started_at, finished_at, signals_built, events_agg, cards_rendered, cards_sent, cards_skipped, dry_run, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (started.strftime("%Y-%m-%d %H:%M:%S UTC+8"),
         finished.strftime("%Y-%m-%d %H:%M:%S UTC+8"),
         sig_count, ev_count, card_count, sent_count, skipped_count, int(dry_run), ""),
    )
    conn.commit()

    write_log(lp, "INFO", f"=== Cycle complete: sent={sent_count} skipped={skipped_count} ===")
    return {"signals": sig_count, "events": ev_count, "cards": card_count,
            "sent": sent_count, "skipped": skipped_count}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Local TG Publisher — v16 Event Cards to Telegram Bridge")
    parser.add_argument("--env", type=str, default=None,
                        help="Path to .env file (default: config/local_tg_publisher.env)")
    parser.add_argument("--dry-run", type=str, default=None,
                        help="Override DRY_RUN setting (true/false)")
    parser.add_argument("--once", action="store_true",
                        help="Run a single cycle then exit")
    parser.add_argument("--interval", type=int, default=None,
                        help="Override POLL_INTERVAL_SECONDS")
    parser.add_argument("--max-send", type=int, default=None,
                        help="Override MAX_SEND_PER_CYCLE")
    args = parser.parse_args()

    cfg = get_config(args.env)

    # CLI overrides
    if args.dry_run is not None:
        cfg["DRY_RUN"] = args.dry_run
    if args.interval is not None:
        cfg["POLL_INTERVAL_SECONDS"] = str(args.interval)
    if args.max_send is not None:
        cfg["MAX_SEND_PER_CYCLE"] = str(args.max_send)

    dry_run = str(cfg.get("DRY_RUN", "true")).strip().lower() in ("true", "1", "yes", "y")
    interval = int(cfg.get("POLL_INTERVAL_SECONDS", "60"))
    max_send = int(cfg.get("MAX_SEND_PER_CYCLE", "3"))
    token = cfg.get("TELEGRAM_BOT_TOKEN", "")
    chat_ids_raw = cfg.get("TELEGRAM_CHAT_ID", "")
    chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()] if chat_ids_raw else []

    lp = log_path(cfg)
    ensure_log_dir(lp)

    # Startup banner
    write_log(lp, "INFO", "=" * 60)
    write_log(lp, "INFO", "Local TG Publisher starting")
    write_log(lp, "INFO", f"  DRY_RUN: {dry_run}")
    write_log(lp, "INFO", f"  Interval: {interval}s")
    write_log(lp, "INFO", f"  Max send/cycle: {max_send}")
    write_log(lp, "INFO", f"  Chat IDs: {[c[-8:] for c in chat_ids] if chat_ids else '(none)'}")
    write_log(lp, "INFO", f"  Token set: {bool(token)}")
    write_log(lp, "INFO", f"  Log: {lp}")
    write_log(lp, "INFO", f"  State DB: {state_db_path(cfg)}")

    # Validate before starting
    if not dry_run:
        if not token:
            write_log(lp, "FATAL", "TELEGRAM_BOT_TOKEN not set. Cannot send. Use DRY_RUN=true for preview.")
            return 1
        if not chat_ids:
            write_log(lp, "FATAL", "TELEGRAM_CHAT_ID not set. Cannot send. Use DRY_RUN=true for preview.")
            return 1
        write_log(lp, "WARN", "*** REAL SEND MODE — messages will be sent to Telegram! ***")
        write_log(lp, "WARN", f"*** Target chat(s): {[c[-8:] for c in chat_ids]} ***")

    # Init state
    db_path = state_db_path(cfg)
    conn = init_state_db(db_path)

    try:
        if args.once:
            write_log(lp, "INFO", "Running single cycle (--once)")
            result = run_once(cfg, conn, lp)
            write_log(lp, "INFO", f"Single cycle done: {result}")
            return 0

        write_log(lp, "INFO", f"Entering loop (Ctrl+C to stop)")
        while True:
            try:
                run_once(cfg, conn, lp)
            except Exception as e:
                write_log(lp, "ERROR", f"Cycle error: {e}\n{traceback.format_exc()[-500:]}")
            time.sleep(interval)
    except KeyboardInterrupt:
        write_log(lp, "INFO", "Received Ctrl+C, shutting down")
    finally:
        conn.close()
        write_log(lp, "INFO", "Publisher stopped")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
