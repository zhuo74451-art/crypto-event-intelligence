import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a lightweight user-experience audit for recent TG drafts or sent alerts.")
    parser.add_argument("--drafts", default=str(ROOT / "data" / "tg_drafts_v07_watcher_private_pilot.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v08_tg_user_experience_audit.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_tg_user_experience_audit_summary.csv"))
    parser.add_argument("--limit", type=int, default=10)
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


def has_chinese(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(text or ""))


def score_row(row: dict) -> dict:
    text = str(row.get("draft_text", "") or row.get("approved_text", "") or "")
    title = str(row.get("title", "") or "")
    flags = []
    if not has_chinese(text):
        flags.append("missing_chinese")
    if len(text) > 1800:
        flags.append("too_long")
    if "时间" not in text and "UTC+8" not in text:
        flags.append("missing_china_time")
    if "解读" not in text and "Context" not in text and "原因" not in text:
        flags.append("missing_context")
    if "仅作链上情报" not in text and "不构成" not in text:
        flags.append("missing_disclaimer")
    if not str(row.get("asset_symbol", "") or "").strip():
        flags.append("missing_asset")
    if not str(row.get("event_type", "") or "").strip():
        flags.append("missing_event_type")
    status = "pass" if not flags else "review"
    return {
        "draft_id": row.get("draft_id", ""),
        "candidate_id": row.get("candidate_id", ""),
        "asset_symbol": row.get("asset_symbol", ""),
        "event_type": row.get("event_type", ""),
        "title": title[:120],
        "ux_status": status,
        "ux_flags": ",".join(flags),
        "text_length": len(text),
    }


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.drafts))[: args.limit]
    audit_rows = [score_row(row) for row in rows]
    pass_count = sum(1 for row in audit_rows if row["ux_status"] == "pass")
    review_count = len(audit_rows) - pass_count
    summary = {
        "audited_rows": len(audit_rows),
        "pass_count": pass_count,
        "review_count": review_count,
        "status": "pass" if review_count == 0 else "review",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    lines = [
        "# v0.8 TG User Experience Audit",
        "",
        "This is a user-view check: readability, China time, context, and disclaimer. It is not user reaction tracking.",
        "",
        f"- audited_rows: {len(audit_rows)}",
        f"- pass_count: {pass_count}",
        f"- review_count: {review_count}",
        "",
        "| draft_id | asset | event_type | status | flags | title |",
        "|---|---|---|---|---|---|",
    ]
    for row in audit_rows:
        title = str(row["title"]).replace("|", "\\|")
        lines.append(
            f"| `{row['draft_id']}` | {row['asset_symbol']} | {row['event_type']} | {row['ux_status']} | {row['ux_flags']} | {title} |"
        )
    lines.extend(
        [
            "",
            "## User-View Bar",
            "",
            "- Lead with Chinese.",
            "- Show China time.",
            "- Explain why the alert matters in one short block.",
            "- Keep realtime alerts short; move context into digests.",
            "- Do not ask users to react as a quality signal.",
            "",
        ]
    )
    output_path = normalize_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"audited_rows={len(audit_rows)}")
    print(f"review_count={review_count}")
    print(f"wrote_report={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
