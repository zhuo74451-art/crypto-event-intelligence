import argparse
import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only diagnosis of remote SQLite time fields.")
    parser.add_argument("--remote", default="root@43.98.174.247")
    parser.add_argument("--remote-db", default="/opt/x-monitor/shared/data/tweets.db")
    parser.add_argument("--table", default="tweets")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--output", default=str(ROOT / "data" / "time_field_diagnosis.csv"))
    parser.add_argument("--sample-output", default=str(ROOT / "data" / "time_field_sample_rows.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_time_field_diagnosis.md"))
    parser.add_argument("--timeout", type=int, default=180)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def remote_script(db_path: str, table: str, limit: int) -> str:
    return f"""
import csv
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

DB_PATH = {db_path!r}
TABLE = {table!r}
LIMIT = {int(limit)}

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
            dt = parsedate_to_datetime(raw)
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def qident(name):
    return '"' + str(name).replace('"', '""') + '"'

conn = sqlite3.connect('file:' + DB_PATH + '?mode=ro', uri=True)
conn.row_factory = sqlite3.Row
cols = [row['name'] for row in conn.execute('PRAGMA table_info(' + qident(TABLE) + ')')]
time_cols = [c for c in cols if any(k in c.lower() for k in ['time', 'date', 'created', 'updated', 'published', 'received'])]
if not time_cols:
    time_cols = cols
select_cols = list(dict.fromkeys(time_cols + [c for c in ['tweet_id','id','title','zh_title','en_title','text','source','author_username','article_url','canonical_url'] if c in cols]))
sql = 'SELECT ' + ', '.join(qident(c) for c in select_cols) + ' FROM ' + qident(TABLE) + ' LIMIT ' + str(LIMIT)
rows = conn.execute(sql).fetchall()
conn.close()

summary_rows = []
for col in time_cols:
    parsed = []
    nonblank = 0
    months = Counter()
    examples = []
    for row in rows:
        value = row[col] if col in row.keys() else ''
        if str(value or '').strip():
            nonblank += 1
        dt = parse_time(value)
        if dt:
            parsed.append(dt)
            months[dt.strftime('%Y-%m')] += 1
            if len(examples) < 3:
                examples.append(str(value))
    span_days = 0
    if len(parsed) >= 2:
        span_days = round((max(parsed) - min(parsed)).total_seconds() / 86400, 4)
    summary_rows.append({{
        'field': col,
        'sample_rows': len(rows),
        'nonblank_count': nonblank,
        'parseable_count': len(parsed),
        'parseable_ratio': round(len(parsed) / len(rows), 4) if rows else 0,
        'min_utc': min(parsed).replace(microsecond=0).isoformat().replace('+00:00','Z') if parsed else '',
        'max_utc': max(parsed).replace(microsecond=0).isoformat().replace('+00:00','Z') if parsed else '',
        'span_days': span_days,
        'month_count': len(months),
        'top_months': ';'.join(f'{{k}}:{{v}}' for k,v in months.most_common(12)),
        'examples': ' | '.join(examples),
    }})

writer = csv.DictWriter(sys.stdout, fieldnames=['record_type','field','sample_rows','nonblank_count','parseable_count','parseable_ratio','min_utc','max_utc','span_days','month_count','top_months','examples'])
writer.writeheader()
for row in summary_rows:
    out = {{'record_type': 'summary'}}
    out.update(row)
    writer.writerow(out)
writer.writerow({{'record_type':'__SAMPLE_ROWS__'}})
sample_fields = ['record_type'] + select_cols
writer = csv.DictWriter(sys.stdout, fieldnames=sample_fields, extrasaction='ignore')
writer.writeheader()
for row in rows[:50]:
    out = {{'record_type': 'sample'}}
    for col in select_cols:
        value = row[col]
        out[col] = '' if value is None else str(value).replace('\\x00','').strip()
    writer.writerow(out)
"""


def split_combined_csv(data: bytes, output: Path, sample_output: Path) -> None:
    text = data.decode("utf-8", errors="replace")
    marker = "\n__SAMPLE_ROWS__"
    if marker not in text:
        output.write_text(text, encoding="utf-8-sig")
        sample_output.write_text("", encoding="utf-8-sig")
        return
    first, rest = text.split(marker, 1)
    output.write_text(first + "\n", encoding="utf-8-sig")
    sample_text = rest
    if sample_text.startswith(","):
        sample_text = sample_text[1:]
    sample_output.write_text(sample_text.lstrip("\n"), encoding="utf-8-sig")


def render_markdown(summary_path: Path, output_path: Path) -> None:
    rows = []
    with summary_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("record_type") == "summary":
                rows.append(row)
    rows.sort(key=lambda row: (float(row.get("span_days") or 0), float(row.get("parseable_ratio") or 0)), reverse=True)
    lines = [
        "# v14 Time Field Diagnosis",
        "",
        "| field | parseable_ratio | span_days | min_utc | max_utc | month_count | top_months |",
        "|---|---:|---:|---|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('field','')} | {row.get('parseable_ratio','')} | {row.get('span_days','')} | "
            f"{row.get('min_utc','')} | {row.get('max_utc','')} | {row.get('month_count','')} | {row.get('top_months','')} |"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_path = normalize_path(args.output)
    sample_output = normalize_path(args.sample_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", args.remote, "python3", "-"],
        input=remote_script(args.remote_db, args.table, args.limit).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=args.timeout,
    )
    if result.returncode != 0:
        sys.stderr.buffer.write(result.stderr)
        return result.returncode
    split_combined_csv(result.stdout, output_path, sample_output)
    render_markdown(output_path, normalize_path(args.markdown_output))
    print(f"wrote_summary={output_path}")
    print(f"wrote_sample={sample_output}")
    print(f"wrote_markdown={normalize_path(args.markdown_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
