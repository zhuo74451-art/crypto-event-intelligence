import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build approved-only local TG draft pool from AI-reviewed drafts.")
    parser.add_argument("--input", default="data/tg_drafts_v06_private_pilot.csv")
    parser.add_argument("--output", default="data/tg_drafts_v06_approved_pool.csv")
    parser.add_argument("--summary", default="results/tg_draft_approved_pool_summary.csv")
    parser.add_argument("--markdown-output", default="results/tg_draft_approved_pool.md")
    return parser.parse_args()


def norm(value: str) -> str:
    return str(value or "").strip().lower()


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def is_approved(row: dict) -> bool:
    return (
        norm(row.get("draft_status")) == "approved"
        and norm(row.get("reviewer_decision")) in {"approve", "approved", "publish"}
        and norm(row.get("auto_send_enabled")) == "false"
    )


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict]) -> None:
    lines = [
        "# Approved TG Draft Pool",
        "",
        "Approved local drafts only. This file does not send messages.",
        "",
        f"- approved_count: {len(rows)}",
        "- auto_send_enabled: false",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row.get('draft_id')} / {row.get('candidate_id')}",
                "",
                f"- asset: {row.get('asset_symbol')}",
                f"- event_type: {row.get('event_type')}",
                f"- route: {row.get('channel_route')}",
                f"- ai_note: {row.get('reviewer_notes')}",
                "",
                "```text",
                row.get("approved_text") or row.get("draft_text", ""),
                "```",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    rows = read_rows(Path(args.input))
    approved = [row for row in rows if is_approved(row)]
    fieldnames = list(rows[0].keys()) if rows else []
    write_rows(Path(args.output), approved, fieldnames)
    summary = {
        "input_rows": len(rows),
        "approved_rows": len(approved),
        "rejected_rows": sum(1 for row in rows if norm(row.get("draft_status")) == "rejected"),
        "needs_edit_rows": sum(1 for row in rows if norm(row.get("draft_status")) == "needs_edit"),
        "auto_send_enabled_count": sum(1 for row in approved if norm(row.get("auto_send_enabled")) == "true"),
        "status": "pass",
    }
    with Path(args.summary).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    write_markdown(Path(args.markdown_output), approved)
    print(f"input_rows={len(rows)}")
    print(f"approved_rows={len(approved)}")
    print(f"wrote_output={args.output}")


if __name__ == "__main__":
    main()
