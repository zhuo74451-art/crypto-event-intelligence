import argparse
import csv
from pathlib import Path


REVIEW_FIELDS = [
    "reviewer_decision",
    "reviewer_usefulness",
    "reviewer_issue_type",
    "reviewer_notes",
    "approved_text",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply compact TG draft review packet fields back to the main draft CSV.")
    parser.add_argument("--drafts", default="data/tg_drafts_v06_private_pilot.csv")
    parser.add_argument("--packet", default="data/tg_draft_review_packet.csv")
    parser.add_argument("--output", default="data/tg_drafts_v06_private_pilot.csv")
    parser.add_argument("--summary", default="results/tg_draft_review_packet_apply_summary.csv")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def norm(value: str) -> str:
    return str(value or "").strip()


def draft_status_from_decision(decision: str, current: str) -> str:
    decision = decision.lower()
    if decision in {"approve", "approved", "publish"}:
        return "approved"
    if decision in {"reject", "rejected", "discard"}:
        return "rejected"
    if decision in {"edit", "needs_edit", "fix"}:
        return "needs_edit"
    return current or "pending_review"


def main() -> None:
    args = parse_args()
    drafts_path = Path(args.drafts)
    packet_path = Path(args.packet)
    output_path = Path(args.output)
    summary_path = Path(args.summary)

    drafts = read_rows(drafts_path)
    packet_rows = read_rows(packet_path)
    packet_by_candidate = {
        norm(row.get("candidate_id")): row for row in packet_rows if norm(row.get("candidate_id"))
    }

    updated_rows = 0
    updated_fields = 0
    for row in drafts:
        packet = packet_by_candidate.get(norm(row.get("candidate_id")))
        if not packet:
            continue
        row_updated = False
        for field in REVIEW_FIELDS:
            new_value = norm(packet.get(field))
            if new_value and new_value != norm(row.get(field)):
                row[field] = new_value
                updated_fields += 1
                row_updated = True
        if row_updated:
            row["draft_status"] = draft_status_from_decision(
                norm(row.get("reviewer_decision")), norm(row.get("draft_status"))
            )
            updated_rows += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(drafts[0].keys()) if drafts else []
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(drafts)

    summary = {
        "draft_rows": len(drafts),
        "packet_rows": len(packet_rows),
        "matched_packet_rows": sum(1 for row in drafts if norm(row.get("candidate_id")) in packet_by_candidate),
        "updated_rows": updated_rows,
        "updated_fields": updated_fields,
        "status": "pass",
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    print(f"draft_rows={len(drafts)}")
    print(f"packet_rows={len(packet_rows)}")
    print(f"updated_rows={updated_rows}")
    print(f"updated_fields={updated_fields}")
    print(f"wrote_output={output_path}")
    print(f"wrote_summary={summary_path}")


if __name__ == "__main__":
    main()
