import argparse
import logging
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export older real news from the configured remote SQLite source.")
    parser.add_argument("--days-ago-min", type=float, default=7)
    parser.add_argument("--days-ago-max", type=float, default=90)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--output", default=str(ROOT / "data" / "raw_news_real_500_older.csv"))
    parser.add_argument("--remote", default="root@43.98.174.247")
    parser.add_argument("--remote-db", default="/opt/x-monitor/shared/data/tweets.db")
    parser.add_argument("--timeout", type=int, default=120)
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def build_remote_script(days_min: float, days_max: float, limit: int, db_path: str) -> str:
    return f"""
import csv
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

DB_PATH = {db_path!r}
LIMIT = {int(limit)}
DAYS_MIN = {float(days_min)}
DAYS_MAX = {float(days_max)}
COLUMNS = ['raw_id','published_at','title','content','source','url','language','author','category','tags']

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
    return str(value).replace('\\x00', '').strip()

conn = sqlite3.connect('file:' + DB_PATH + '?mode=ro', uri=True)
conn.row_factory = sqlite3.Row
sql = \"\"\"
SELECT tweet_id, author_username, text, tweet_created_at, received_at, source,
       zh_title, zh_body, en_title, en_body, zh_short_title, hermes_category,
       content_type, article_url, canonical_url, title, published_at, author,
       raw_text, extracted_text
FROM tweets
WHERE COALESCE(published_at, tweet_created_at, received_at) IS NOT NULL
\"\"\"
rows = conn.execute(sql).fetchall()
conn.close()

now = datetime.now(timezone.utc)
newer_bound = now - timedelta(days=DAYS_MIN)
older_bound = now - timedelta(days=DAYS_MAX)
items = []
for row in rows:
    raw_time = row['published_at'] or row['tweet_created_at'] or row['received_at']
    dt = parse_time(raw_time)
    if not dt or dt > newer_bound or dt < older_bound:
        continue
    title = clean(row['title'] or row['zh_title'] or row['en_title'] or row['zh_short_title'] or '')
    content = clean(row['extracted_text'] or row['raw_text'] or row['zh_body'] or row['en_body'] or row['text'] or '')
    if not title and content:
        title = content[:120]
    if not content:
        content = title
    items.append((dt, {{
        'raw_id': clean(row['tweet_id']),
        'published_at': dt.replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        'title': title,
        'content': content,
        'source': clean(row['source']),
        'url': clean(row['article_url'] or row['canonical_url']),
        'language': '',
        'author': clean(row['author'] or row['author_username']),
        'category': clean(row['hermes_category'] or row['content_type']),
        'tags': clean(row['content_type'] or row['hermes_category']),
    }}))

items.sort(key=lambda item: item[0], reverse=True)
writer = csv.DictWriter(sys.stdout, fieldnames=COLUMNS, lineterminator='\\n')
writer.writeheader()
for _, row in items[:LIMIT]:
    writer.writerow(row)
"""


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    output_path = normalize_path(args.output)
    if args.days_ago_min < 0 or args.days_ago_max <= args.days_ago_min:
        logging.error("--days-ago-max must be greater than --days-ago-min")
        return 1

    remote_script = build_remote_script(args.days_ago_min, args.days_ago_max, args.limit, args.remote_db)
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", args.remote, "python3", "-"],
        input=remote_script.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=args.timeout,
    )
    if result.returncode != 0:
        sys.stderr.buffer.write(result.stderr)
        return result.returncode

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result.stdout)
    row_count = max(0, result.stdout.count(b"\n") - 1)
    logging.info("wrote %s rows to %s", row_count, output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
