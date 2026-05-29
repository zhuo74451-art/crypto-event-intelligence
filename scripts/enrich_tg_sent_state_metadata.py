import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METADATA_COLUMNS = [
    "event_type",
    "asset_symbol",
    "amount_usd",
    "severity_tier",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill missing metadata in TG sent-state rows from local TG draft CSV files.")
    parser.add_argument("--sent-state", default=str(ROOT / "data" / "tg_live_sent_state.csv"))
    parser.add_argument("--draft-glob", default="data/tg_drafts*.csv")
    parser.add_argument("--output", default="", help="Default overwrites --sent-state after creating a .bak copy.")
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_tg_sent_state_metadata_enrichment_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


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


def nonblank(value) -> bool:
    return str(value or "").strip() != ""


def build_draft_index(pattern: str) -> tuple[dict[str, dict], dict[str, dict], int]:
    by_candidate = {}
    by_draft = {}
    count = 0
    for path in ROOT.glob(pattern):
        for row in read_rows(path):
            count += 1
            candidate_id = str(row.get("candidate_id", "") or "").strip()
            draft_id = str(row.get("draft_id", "") or "").strip()
            if candidate_id:
                by_candidate[candidate_id] = row
            if draft_id:
                by_draft[draft_id] = row
    return by_candidate, by_draft, count


def merged_fieldnames(rows: list[dict]) -> list[str]:
    existing = list(rows[0].keys()) if rows else []
    for column in METADATA_COLUMNS:
        if column not in existing:
            existing.append(column)
    return existing


def main() -> int:
    args = parse_args()
    sent_path = normalize_path(args.sent_state)
    output_path = normalize_path(args.output) if args.output else sent_path
    rows = read_rows(sent_path)
    by_candidate, by_draft, draft_count = build_draft_index(args.draft_glob)

    updated_rows = 0
    updated_fields = 0
    unresolved_rows = 0
    for row in rows:
        source = by_candidate.get(str(row.get("candidate_id", "") or "").strip())
        if not source:
            source = by_draft.get(str(row.get("draft_id", "") or "").strip())
        if not source:
            if any(not nonblank(row.get(column)) for column in METADATA_COLUMNS):
                unresolved_rows += 1
            continue

        row_changed = False
        for column in METADATA_COLUMNS:
            if not nonblank(row.get(column)) and nonblank(source.get(column)):
                row[column] = str(source.get(column, "") or "").strip()
                row_changed = True
                updated_fields += 1
        if row_changed:
            updated_rows += 1

    if output_path == sent_path and sent_path.exists():
        backup_path = sent_path.with_suffix(sent_path.suffix + ".bak")
        backup_path.write_text(sent_path.read_text(encoding="utf-8-sig"), encoding="utf-8")
    write_rows(output_path, rows, merged_fieldnames(rows))

    summary = {
        "sent_state_rows": len(rows),
        "draft_rows_indexed": draft_count,
        "updated_rows": updated_rows,
        "updated_fields": updated_fields,
        "unresolved_rows": unresolved_rows,
        "output": str(output_path),
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"updated_rows={updated_rows}")
    print(f"unresolved_rows={unresolved_rows}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
