import argparse
import logging
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export older real news using an explicit remote time field.")
    parser.add_argument("--time-field", default="published_at")
    parser.add_argument("--days-ago-min", type=float, default=7)
    parser.add_argument("--days-ago-max", type=float, default=365)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--output", default=str(ROOT / "data" / "raw_news_real_10k_365d_v2.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_real_news_export_v2_summary.csv"))
    parser.add_argument("--remote", default="root@43.98.174.247")
    parser.add_argument("--remote-db", default="/opt/x-monitor/shared/data/tweets.db")
    parser.add_argument("--table", default="tweets")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--scan-limit", type=int, default=50000)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def build_remote_script(args: argparse.Namespace) -> str:
    return f"""
import csv
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

DB_PATH = {args.remote_db!r}
TABLE = {args.table!r}
TIME_FIELD = {args.time_field!r}
LIMIT = {int(args.limit)}
SCAN_LIMIT = {int(args.scan_limit)}
DAYS_MIN = {float(args.days_ago_min)}
DAYS_MAX = {float(args.days_ago_max)}
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
newer_bound = now - timedelta(days=DAYS_MIN)
older_bound = now - timedelta(days=DAYS_MAX)
items = []
for row in rows:
    dt = parse_time(row[TIME_FIELD])
    if not dt or dt > newer_bound or dt < older_bound:
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
    raw_id = clean(row['tweet_id'] if 'tweet_id' in row.keys() else row['id'] if 'id' in row.keys() else '')
    url = clean(row['article_url'] if 'article_url' in row.keys() else '')
    if not url and 'canonical_url' in row.keys():
        url = clean(row['canonical_url'])
    items.append((dt, {{
        'raw_id': raw_id,
        'published_at': dt.replace(microsecond=0).isoformat().replace('+00:00','Z'),
        'source_published_at': dt.replace(microsecond=0).isoformat().replace('+00:00','Z'),
        'source_timezone': 'UTC',
        'title': title,
        'content': content,
        'source': clean(row['source'] if 'source' in row.keys() else ''),
        'url': url,
        'language': '',
        'author': clean(row['author'] if 'author' in row.keys() else row['author_username'] if 'author_username' in row.keys() else ''),
        'category': clean(row['hermes_category'] if 'hermes_category' in row.keys() else row['content_type'] if 'content_type' in row.keys() else ''),
        'tags': clean(row['content_type'] if 'content_type' in row.keys() else row['hermes_category'] if 'hermes_category' in row.keys() else ''),
    }}))

items.sort(key=lambda item: item[0], reverse=True)
writer = csv.DictWriter(sys.stdout, fieldnames=COLUMNS, lineterminator='\\n')
writer.writeheader()
for _, row in items[:LIMIT]:
    writer.writerow(row)
"""


def write_summary(path: Path, output_path: Path, stdout: bytes, args: argparse.Namespace) -> None:
    rows = max(0, stdout.decode("utf-8", errors="ignore").count("\n") - 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "metric,value\n"
        f"time_field,{args.time_field}\n"
        f"days_ago_min,{args.days_ago_min}\n"
        f"days_ago_max,{args.days_ago_max}\n"
        f"limit,{args.limit}\n"
        f"scan_limit,{args.scan_limit}\n"
        f"line_count_estimate,{rows}\n"
        f"output,{output_path}\n",
        encoding="utf-8-sig",
    )


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    output_path = normalize_path(args.output)
    if args.days_ago_min < 0 or args.days_ago_max <= args.days_ago_min:
        logging.error("--days-ago-max must be greater than --days-ago-min")
        return 1
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", args.remote, "python3", "-"],
        input=build_remote_script(args).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=args.timeout,
    )
    if result.returncode != 0:
        sys.stderr.buffer.write(result.stderr)
        return result.returncode
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result.stdout)
    write_summary(normalize_path(args.summary), output_path, result.stdout, args)
    logging.info("wrote export to %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
