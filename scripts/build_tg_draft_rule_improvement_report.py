import argparse
import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


RULE_HINTS = {
    "duplicate_or_stale": {
        "rule_area": "dedup",
        "recommended_action": "Strengthen title/entity/time-window dedup before draft generation.",
    },
    "too_generic": {
        "rule_area": "relevance",
        "recommended_action": "Require concrete metric, actor, amount, protocol action, or official announcement for project_business/research_only drafts.",
    },
    "not_price_relevant": {
        "rule_area": "channel_route",
        "recommended_action": "Route marketing/adoption/card stories to research_only or reject unless tied to measurable asset flow or major listed asset impact.",
    },
    "factual_issue": {
        "rule_area": "content_quality",
        "recommended_action": "Reject or needs_edit when title/content is truncated or missing key facts.",
    },
    "asset_issue": {
        "rule_area": "entity",
        "recommended_action": "Improve primary asset/entity extraction before draft generation.",
    },
    "time_issue": {
        "rule_area": "time",
        "recommended_action": "Audit source time/backtest time and downgrade stale items.",
    },
    "tone_issue": {
        "rule_area": "copy",
        "recommended_action": "Clean promotional or hype language before draft approval.",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build rule-improvement report from AI-reviewed TG draft failures.")
    parser.add_argument("--input", default=str(ROOT / "data" / "tg_drafts_v06_private_pilot.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "tg_draft_rule_improvement_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_draft_rule_improvement_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "tg_draft_rule_improvement_report.md"))
    return parser.parse_args()


def norm(value: str) -> str:
    return str(value or "").strip()


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_report_rows(rows: list[dict]) -> list[dict]:
    report = []
    for row in rows:
        status = norm(row.get("draft_status")).lower()
        usefulness = norm(row.get("reviewer_usefulness")).lower()
        issue_type = norm(row.get("reviewer_issue_type")).lower() or "none"
        if status not in {"rejected", "needs_edit"} and usefulness != "noise" and issue_type == "none":
            continue
        hint = RULE_HINTS.get(
            issue_type,
            {
                "rule_area": "review",
                "recommended_action": "Inspect this failure pattern and decide whether it needs a rule.",
            },
        )
        report.append(
            {
                "draft_id": row.get("draft_id", ""),
                "candidate_id": row.get("candidate_id", ""),
                "asset_symbol": row.get("asset_symbol", ""),
                "event_type": row.get("event_type", ""),
                "channel_route": row.get("channel_route", ""),
                "title": row.get("title", ""),
                "draft_status": row.get("draft_status", ""),
                "reviewer_usefulness": row.get("reviewer_usefulness", ""),
                "reviewer_issue_type": issue_type,
                "reviewer_notes": row.get("reviewer_notes", ""),
                "rule_area": hint["rule_area"],
                "recommended_action": hint["recommended_action"],
            }
        )
    return report


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, report_rows: list[dict], summary: dict, issue_counts: Counter, area_counts: Counter) -> None:
    lines = [
        "# TG Draft Rule Improvement Report",
        "",
        "This report converts AI-reviewed rejected/noisy drafts into local rule-improvement candidates.",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Issue Types", "", "| issue_type | count |", "|---|---:|"])
    for key, value in issue_counts.most_common():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Rule Areas", "", "| rule_area | count |", "|---|---:|"])
    for key, value in area_counts.most_common():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Rows", "", "| draft | issue | area | action | title |", "|---|---|---|---|---|"])
    for row in report_rows:
        title = norm(row["title"]).replace("|", "\\|")[:120]
        action = norm(row["recommended_action"]).replace("|", "\\|")
        lines.append(
            f"| {row['draft_id']} | {row['reviewer_issue_type']} | {row['rule_area']} | {action} | {title} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    rows = read_rows(Path(args.input))
    report_rows = build_report_rows(rows)
    issue_counts = Counter(row["reviewer_issue_type"] for row in report_rows)
    area_counts = Counter(row["rule_area"] for row in report_rows)
    summary = {
        "input_rows": len(rows),
        "rule_improvement_rows": len(report_rows),
        "top_issue_type": issue_counts.most_common(1)[0][0] if issue_counts else "",
        "top_issue_count": issue_counts.most_common(1)[0][1] if issue_counts else 0,
        "top_rule_area": area_counts.most_common(1)[0][0] if area_counts else "",
        "top_rule_area_count": area_counts.most_common(1)[0][1] if area_counts else 0,
        "status": "review" if report_rows else "pass",
    }
    fieldnames = [
        "draft_id",
        "candidate_id",
        "asset_symbol",
        "event_type",
        "channel_route",
        "title",
        "draft_status",
        "reviewer_usefulness",
        "reviewer_issue_type",
        "reviewer_notes",
        "rule_area",
        "recommended_action",
    ]
    write_csv(Path(args.output), report_rows, fieldnames)
    write_csv(Path(args.summary), [summary], list(summary.keys()))
    write_markdown(Path(args.markdown_output), report_rows, summary, issue_counts, area_counts)
    print(f"input_rows={len(rows)}")
    print(f"rule_improvement_rows={len(report_rows)}")
    print(f"wrote_output={args.output}")
    print(f"wrote_summary={args.summary}")


if __name__ == "__main__":
    main()
