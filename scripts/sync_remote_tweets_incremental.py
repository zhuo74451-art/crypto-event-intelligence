"""
Sync remote tweets.db incrementally to local CSV.

Uses the proven v2 exporter remote-query pattern:
  SSH + SQLite mode=ro + time-window filter via Python.

Usage:
    python scripts/sync_remote_tweets_incremental.py --dry-run --limit 20 --lookback-minutes 1440
    python scripts/sync_remote_tweets_incremental.py --limit 20 --lookback-minutes 1440
"""

import argparse
import csv
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

DEFAULT_REMOTE = "root@43.98.174.247"
DEFAULT_REMOTE_DB = "/opt/x-monitor/shared/data/tweets.db"
DEFAULT_TABLE = "tweets"
DEFAULT_TIME_FIELD = "published_at"

CSV_COLUMNS = [
    "raw_id", "published_at", "source_published_at", "source_timezone",
    "title", "content", "source", "url", "language", "author", "category", "tags",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Incremental remote tweets.db -> local CSV sync (v2 logic).")
    p.add_argument("--remote", default=DEFAULT_REMOTE)
    p.add_argument("--remote-db", default=DEFAULT_REMOTE_DB)
    p.add_argument("--table", default=DEFAULT_TABLE)
    p.add_argument("--time-field", default=DEFAULT_TIME_FIELD)
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--lookback-minutes", type=int, default=120)
    p.add_argument("--scan-limit", type=int, default=5000)
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--output", default=str(ROOT / "data" / "raw_news_live_incremental.csv"))
    p.add_argument("--state", default=str(ROOT / "data" / "remote_tweets_sync_state.sqlite"))
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def china_now() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


# ── local state DB ──────────────────────────────────────────

def init_state(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            last_synced_at  TEXT NOT NULL,
            row_count       INTEGER NOT NULL DEFAULT 0,
            newest_time     TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_ids (
            raw_id          TEXT PRIMARY KEY,
            content_hash    TEXT NOT NULL,
            first_seen_at   TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def load_seen_ids(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT raw_id FROM seen_ids").fetchall()
    return {r[0] for r in rows}


def save_state(conn: sqlite3.Connection, row_count: int, newest_time: str, new_ids: set[str]) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO sync_state (id, last_synced_at, row_count, newest_time) VALUES (1, ?, ?, ?)",
        (china_now(), row_count, newest_time),
    )
    for raw_id in new_ids:
        conn.execute(
            "INSERT OR IGNORE INTO seen_ids (raw_id, content_hash, first_seen_at) VALUES (?, ?, ?)",
            (raw_id, hashlib.sha256(raw_id.encode()).hexdigest()[:16], china_now()),
        )
    conn.commit()


# ── remote script (v2 proven pattern) ───────────────────────

def build_remote_script(args: argparse.Namespace, seen_ids: set[str]) -> str:
    """Build inline Python using v2 exporter's proven query + time-filter logic."""
    ids_json = json.dumps(sorted(seen_ids)[-3000:])
    return f"""
import csv
import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

DB_PATH = {args.remote_db!r}
TABLE = {args.table!r}
TIME_FIELD = {args.time_field!r}
LIMIT = {int(args.limit)}
SCAN_LIMIT = {int(args.scan_limit)}
LOOKBACK_MIN = {int(args.lookback_minutes)}
SEEN_IDS = set(json.loads({ids_json!r}))
COLUMNS = ['raw_id','published_at','source_published_at','source_timezone','title','content','source','url','language','author','category','tags']

def parse_time(value):
    raw = str(value or '').strip()
    if not raw:
        return None
    try:
        if raw.endswith('Z'):
            raw = raw[:-1] + '+00:00'
        dt = datetime.fromisoformat(raw)
    except Exception:
        try:
            dt = parsedate_to_datetime(str(value))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def clean(value):
    if value is None:
        return ''
    return str(value).replace('\\x00','').strip()

def qident(name):
    return '"' + str(name).replace('"', '""') + '"'

conn = sqlite3.connect('file:' + DB_PATH + '?mode=ro', uri=True)
conn.row_factory = sqlite3.Row
cols = [row['name'] for row in conn.execute('PRAGMA table_info(' + qident(TABLE) + ')')]
if TIME_FIELD not in cols:
    raise SystemExit('time field not found: ' + TIME_FIELD)
select_cols = [c for c in [
    'tweet_id','id','author_username','text','tweet_created_at','received_at','source',
    'zh_title','zh_body','en_title','en_body','zh_short_title','hermes_category',
    'content_type','article_url','canonical_url','title','published_at','author',
    'raw_text','extracted_text', TIME_FIELD
] if c in cols]
sql = (
    'SELECT ' + ', '.join(qident(c) for c in dict.fromkeys(select_cols)) +
    ' FROM ' + qident(TABLE) +
    ' WHERE ' + qident(TIME_FIELD) + ' IS NOT NULL' +
    ' ORDER BY ' + qident(TIME_FIELD) + ' DESC LIMIT ' + str(SCAN_LIMIT)
)
rows = conn.execute(sql).fetchall()
conn.close()

now = datetime.now(timezone.utc)
newer_bound = now  # accept up to now
older_bound = now - timedelta(minutes=LOOKBACK_MIN)
items = []
newest_time = ''
for row in rows:
    dt = parse_time(row[TIME_FIELD])
    if not dt or dt > newer_bound or dt < older_bound:
        continue
    raw_id = clean(row['tweet_id'] if 'tweet_id' in row.keys() else (row['id'] if 'id' in row.keys() else ''))
    if raw_id and raw_id in SEEN_IDS:
        continue
    title = clean(row['title'] if 'title' in row.keys() else '')
    if not title:
        for col in ['zh_title','en_title','zh_short_title']:
            if col in row.keys() and clean(row[col]):
                title = clean(row[col])
                break
    content = ''
    for col in ['extracted_text','raw_text','zh_body','en_body','text']:
        if col in row.keys() and clean(row[col]):
            content = clean(row[col])
            break
    if not title and content:
        title = content[:120]
    if not content:
        content = title
    url = clean(row['article_url'] if 'article_url' in row.keys() else '')
    if not url and 'canonical_url' in row.keys():
        url = clean(row['canonical_url'])
    ts = dt.replace(microsecond=0).isoformat().replace('+00:00','Z')
    items.append((dt, {{
        'raw_id': raw_id,
        'published_at': ts,
        'source_published_at': ts,
        'source_timezone': 'UTC',
        'title': title,
        'content': content,
        'source': clean(row['source'] if 'source' in row.keys() else ''),
        'url': url,
        'language': '',
        'author': clean((row['author'] if 'author' in row.keys() else '') or (row['author_username'] if 'author_username' in row.keys() else '')),
        'category': clean((row['hermes_category'] if 'hermes_category' in row.keys() else '') or (row['content_type'] if 'content_type' in row.keys() else '')),
        'tags': clean((row['content_type'] if 'content_type' in row.keys() else '') or (row['hermes_category'] if 'hermes_category' in row.keys() else '')),
    }}))
    if not newest_time or dt.isoformat() > newest_time:
        newest_time = dt.isoformat()

items.sort(key=lambda item: item[0], reverse=True)
limited = items[:LIMIT]

writer = csv.DictWriter(sys.stdout, fieldnames=COLUMNS, lineterminator='\\n')
writer.writeheader()
for _, row in limited:
    writer.writerow(row)

# Metadata marker
print(f'\\n__SYNC_META__ count={{len(limited)}} newest={{newest_time or "none"}} ids={{json.dumps([r["raw_id"] for r in [item[1] for item in limited]])}}')
"""


# ── main ─────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    dry = args.dry_run
    output_path = Path(args.output)
    state_path = Path(args.state)

    conn = init_state(state_path)
    seen_ids = load_seen_ids(conn)

    label = "DRY-RUN" if dry else "LIVE"
    print(f"[{label}] Lookback: {args.lookback_minutes}min | Limit: {args.limit} | Seen IDs: {len(seen_ids)}")

    # Build and send remote script via SSH
    script = build_remote_script(args, seen_ids)
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", args.remote, "python3", "-"],
        input=script.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=args.timeout,
    )

    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace")
        print(f"ERROR: SSH failed (exit={result.returncode})")
        if "Permission denied" in stderr_text:
            print("  SSH key not accepted. Check ssh-agent or ~/.ssh/config.")
        elif "Could not resolve hostname" in stderr_text:
            print("  Cannot reach remote host. Check VPN/network.")
        else:
            print(f"  stderr: {stderr_text[:300]}")
        conn.close()
        return 1

    stdout_text = result.stdout.decode("utf-8", errors="replace")

    # Split CSV body from metadata marker
    csv_text = stdout_text
    meta = {}
    marker = "\n__SYNC_META__"
    if marker in stdout_text:
        csv_text, meta_part = stdout_text.split(marker, 1)
        for piece in meta_part.strip().split():
            if "=" in piece:
                k, v = piece.split("=", 1)
                meta[k] = v

    data_lines = [l for l in csv_text.strip().splitlines() if l.strip()]
    new_count = max(0, len(data_lines) - 1)  # minus header

    # Show preview titles
    if new_count > 0:
        reader = csv.DictReader(data_lines)
        titles = []
        for r in reader:
            t = r.get("title", "")[:80]
            if t:
                titles.append(t)
        print(f"  Fetched: {new_count} new tweets")
        for i, t in enumerate(titles[:3], 1):
            print(f"  [{i}] {t}")
        if len(titles) > 3:
            print(f"  ... and {len(titles) - 3} more")
    else:
        print("  Fetched: 0 new tweets (none in window or all already seen)")

    if dry:
        print("[DRY-RUN] State NOT updated, CSV NOT written.")
    else:
        if new_count > 0:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(csv_text.strip() + "\n", encoding="utf-8-sig")
            new_ids = set()
            if data_lines:
                for r in csv.DictReader(data_lines):
                    rid = r.get("raw_id", "")
                    if rid:
                        new_ids.add(rid)
            newest = meta.get("newest", "")
            save_state(conn, new_count, newest, new_ids)
            print(f"  Wrote {new_count} rows to {output_path}")
            print(f"  State updated: seen_ids={len(seen_ids) + len(new_ids)}")
        else:
            print("  0 new rows, state unchanged.")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
