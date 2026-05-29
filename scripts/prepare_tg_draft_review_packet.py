import argparse
import csv
from pathlib import Path


REVIEW_COLUMNS = [
    "draft_id",
    "candidate_id",
    "published_at_china",
    "asset_symbol",
    "event_type_label",
    "channel_route",
    "confidence_label",
    "strength_stars",
    "title",
    "draft_text",
    "reviewer_decision",
    "reviewer_usefulness",
    "reviewer_issue_type",
    "reviewer_notes",
    "approved_text",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a compact review packet for local TG drafts.")
    parser.add_argument("--input", default="data/tg_drafts_v06_private_pilot.csv")
    parser.add_argument("--output", default="data/tg_draft_review_packet.csv")
    parser.add_argument("--markdown-output", default="results/tg_draft_review_packet.md")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--only-pending", action="store_true")
    return parser.parse_args()


def norm(value: str) -> str:
    return str(value or "").strip()


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def select_rows(rows: list[dict], limit: int, only_pending: bool) -> list[dict]:
    selected = []
    for row in rows:
        if only_pending and norm(row.get("draft_status")).lower() != "pending_review":
            continue
        selected.append({column: row.get(column, "") for column in REVIEW_COLUMNS})
        if limit and len(selected) >= limit:
            break
    return selected


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict]) -> None:
    lines = [
        "# TG Draft Review Packet",
        "",
        "Fill review fields in the CSV packet, then copy them back to the main draft CSV or use it as review notes.",
        "",
        "Allowed values:",
        "",
        "- reviewer_decision: approve, edit, reject",
        "- reviewer_usefulness: useful, interesting, noise",
        "- reviewer_issue_type: none, factual_issue, asset_issue, time_issue, tone_issue, not_price_relevant",
        "",
        f"- packet_rows: {len(rows)}",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row.get('draft_id')} / {row.get('candidate_id')}",
                "",
                f"- asset: {row.get('asset_symbol')}",
                f"- event_type: {row.get('event_type_label')}",
                f"- route: {row.get('channel_route')}",
                f"- confidence: {row.get('confidence_label')}",
                "",
                "```text",
                row.get("draft_text", ""),
                "```",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    rows = read_rows(Path(args.input))
    selected = select_rows(rows, args.limit, args.only_pending)
    write_csv(Path(args.output), selected)
    write_markdown(Path(args.markdown_output), selected)
    print(f"input_rows={len(rows)}")
    print(f"packet_rows={len(selected)}")
    print(f"wrote_output={args.output}")
    print(f"wrote_markdown={args.markdown_output}")


if __name__ == "__main__":
    main()
