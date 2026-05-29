import argparse
import csv
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize local TG draft pilot review feedback.")
    parser.add_argument("--input", default="data/tg_drafts_v06_private_pilot.csv")
    parser.add_argument("--summary", default="results/tg_draft_feedback_summary.csv")
    parser.add_argument("--markdown-output", default="results/tg_draft_feedback_summary.md")
    return parser.parse_args()


def norm(value: str) -> str:
    return str(value or "").strip().lower()


def count_field(rows: list[dict], field: str) -> Counter:
    return Counter(norm(row.get(field)) or "missing" for row in rows)


def write_csv(path: Path, metrics: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics.keys()))
        writer.writeheader()
        writer.writerow(metrics)


def write_markdown(path: Path, metrics: dict, counters: dict[str, Counter]) -> None:
    lines = [
        "# TG Draft Feedback Summary",
        "",
        "This report summarizes local draft review only. It does not imply auto-send approval.",
        "",
        "## Metrics",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key, value in metrics.items():
        lines.append(f"| {key} | {value} |")
    for name, counter in counters.items():
        lines.extend(["", f"## {name}", "", "| value | count |", "|---|---:|"])
        for key, value in counter.most_common():
            lines.append(f"| {key} | {value} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    rows = list(csv.DictReader(input_path.open("r", encoding="utf-8-sig", newline="")))

    reviewed = [row for row in rows if norm(row.get("reviewer_decision"))]
    useful = [row for row in rows if norm(row.get("reviewer_usefulness")) in {"useful", "actionable", "interesting"}]
    issue_rows = [row for row in rows if norm(row.get("reviewer_issue_type")) not in {"", "none", "missing"}]
    approved = [row for row in rows if norm(row.get("reviewer_decision")) in {"approve", "approved", "publish"}]
    rejected = [row for row in rows if norm(row.get("reviewer_decision")) in {"reject", "rejected", "discard"}]

    total = len(rows)
    reviewed_count = len(reviewed)
    metrics = {
        "total_drafts": total,
        "reviewed_count": reviewed_count,
        "missing_review_count": total - reviewed_count,
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "useful_or_interesting_count": len(useful),
        "issue_count": len(issue_rows),
        "review_completion_rate": round(reviewed_count / total, 4) if total else 0,
        "approval_rate_reviewed": round(len(approved) / reviewed_count, 4) if reviewed_count else 0,
        "useful_rate_total": round(len(useful) / total, 4) if total else 0,
        "issue_rate_reviewed": round(len(issue_rows) / reviewed_count, 4) if reviewed_count else 0,
        "auto_send_enabled_count": sum(1 for row in rows if norm(row.get("auto_send_enabled")) == "true"),
        "status": "ready_for_review" if total and reviewed_count == 0 else "review_in_progress",
    }

    counters = {
        "reviewer_decision": count_field(rows, "reviewer_decision"),
        "reviewer_usefulness": count_field(rows, "reviewer_usefulness"),
        "reviewer_issue_type": count_field(rows, "reviewer_issue_type"),
        "event_type": count_field(rows, "event_type"),
        "channel_route": count_field(rows, "channel_route"),
    }

    write_csv(Path(args.summary), metrics)
    write_markdown(Path(args.markdown_output), metrics, counters)
    print(f"total_drafts={total}")
    print(f"reviewed_count={reviewed_count}")
    print(f"wrote_summary={args.summary}")
    print(f"wrote_markdown={args.markdown_output}")


if __name__ == "__main__":
    main()
