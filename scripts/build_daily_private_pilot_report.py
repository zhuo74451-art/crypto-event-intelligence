import argparse
import csv
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a one-page daily private-pilot operations report.")
    parser.add_argument("--drafts", default=str(ROOT / "data" / "tg_drafts_v06_private_pilot.csv"))
    parser.add_argument("--validation", default=str(ROOT / "results" / "tg_draft_validation_summary.csv"))
    parser.add_argument("--feedback", default=str(ROOT / "results" / "tg_draft_feedback_summary.csv"))
    parser.add_argument("--other-review", default=str(ROOT / "results" / "v06_other_review_reason_summary.csv"))
    parser.add_argument("--prefilter", default=str(ROOT / "results" / "tg_draft_prefilter_summary.csv"))
    parser.add_argument("--approved-pool", default=str(ROOT / "results" / "tg_draft_approved_pool_summary.csv"))
    parser.add_argument("--dashboard", default=str(ROOT / "results" / "project_dashboard_metrics.csv"))
    parser.add_argument("--claude-backlog", default=str(ROOT / "docs" / "CLAUDE_QUESTION_BACKLOG.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "daily_private_pilot_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "daily_private_pilot_report.md"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def first_row(path: Path) -> dict:
    rows = read_rows(path)
    return rows[0] if rows else {}


def count_open_claude_questions(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 4 and cells[0].isdigit() and cells[3].lower() == "open":
            count += 1
    return count


def as_int(row: dict, key: str, default: int = 0) -> int:
    try:
        return int(float(str(row.get(key, "") or default)))
    except ValueError:
        return default


def as_float(row: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(str(row.get(key, "") or default))
    except ValueError:
        return default


def value_counts(rows: list[dict], field: str) -> Counter:
    return Counter(str(row.get(field, "") or "(blank)").strip() for row in rows)


def dashboard_review_metrics(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if str(row.get("status", "")).lower() in {"fail", "blocked", "review", "ready"}
    ]


def build_summary(args: argparse.Namespace) -> tuple[dict, list[dict], list[dict]]:
    drafts = read_rows(normalize_path(args.drafts))
    validation = first_row(normalize_path(args.validation))
    feedback = first_row(normalize_path(args.feedback))
    other_review = first_row(normalize_path(args.other_review))
    prefilter = first_row(normalize_path(args.prefilter))
    approved_pool = first_row(normalize_path(args.approved_pool))
    dashboard_rows = read_rows(normalize_path(args.dashboard))
    claude_open = count_open_claude_questions(normalize_path(args.claude_backlog))
    review_rows = dashboard_review_metrics(dashboard_rows)
    fail_blocked = [
        row for row in review_rows if str(row.get("status", "")).lower() in {"fail", "blocked"}
    ]

    total_drafts = len(drafts)
    reviewed_count = as_int(feedback, "reviewed_count")
    validation_fail_count = as_int(validation, "fail_count")
    auto_send_enabled_count = as_int(validation, "auto_send_enabled_count")
    other_keep_review = as_int(other_review, "keep_review_count")
    useful_count = as_int(feedback, "useful_or_interesting_count")
    issue_count = as_int(feedback, "issue_count")
    review_completion_rate = as_float(feedback, "review_completion_rate")

    if fail_blocked or validation_fail_count or auto_send_enabled_count:
        status = "blocked"
        next_action = "Fix draft validation/security failures before reviewing or posting any draft."
    elif total_drafts == 0:
        status = "blocked"
        next_action = "Generate private-pilot drafts."
    elif reviewed_count < min(10, total_drafts):
        status = "ready_for_review"
        next_action = "Review at least 10 drafts and fill reviewer_decision/usefulness/issue fields."
    elif issue_count > 2:
        status = "needs_rule_cleanup"
        next_action = "Inspect repeated draft issues and update entity/taxonomy/source rules."
    else:
        status = "pilot_signal_ready"
        next_action = "Use feedback summary to decide whether to expand the private pilot sample."

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC+8"),
        "status": status,
        "total_drafts": total_drafts,
        "reviewed_count": reviewed_count,
        "review_completion_rate": round(review_completion_rate, 4),
        "useful_or_interesting_count": useful_count,
        "issue_count": issue_count,
        "validation_fail_count": validation_fail_count,
        "auto_send_enabled_count": auto_send_enabled_count,
        "other_review_keep_review_count": other_keep_review,
        "prefilter_input_rows": as_int(prefilter, "input_rows"),
        "prefilter_pass_rows": as_int(prefilter, "pass_rows"),
        "prefilter_reject_rows": as_int(prefilter, "reject_rows"),
        "approved_pool_rows": as_int(approved_pool, "approved_rows"),
        "dashboard_fail_or_blocked_count": len(fail_blocked),
        "dashboard_review_or_ready_count": len(review_rows),
        "claude_open_questions": claude_open,
        "claude_threshold": 20,
        "next_action": next_action,
    }
    return summary, drafts, review_rows


def write_summary(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)


def render_table_counts(title: str, counts: Counter) -> list[str]:
    lines = ["", f"## {title}", "", "| value | count |", "|---|---:|"]
    for value, count in counts.most_common():
        lines.append(f"| {value} | {count} |")
    return lines


def write_markdown(path: Path, summary: dict, drafts: list[dict], review_rows: list[dict]) -> None:
    lines = [
        "# Daily Private Pilot Report",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "## Status",
        "",
        f"- status: `{summary['status']}`",
        f"- next_action: {summary['next_action']}",
        f"- total_drafts: {summary['total_drafts']}",
        f"- reviewed_count: {summary['reviewed_count']}",
        f"- validation_fail_count: {summary['validation_fail_count']}",
        f"- auto_send_enabled_count: {summary['auto_send_enabled_count']}",
        f"- claude_open_questions: {summary['claude_open_questions']}/{summary['claude_threshold']}",
        "",
        "## Private Pilot Metrics",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key in [
        "review_completion_rate",
        "useful_or_interesting_count",
        "issue_count",
        "other_review_keep_review_count",
        "prefilter_input_rows",
        "prefilter_pass_rows",
        "prefilter_reject_rows",
        "approved_pool_rows",
        "dashboard_fail_or_blocked_count",
        "dashboard_review_or_ready_count",
    ]:
        lines.append(f"| {key} | {summary[key]} |")

    lines.extend(render_table_counts("Draft Event Types", value_counts(drafts, "event_type")))
    lines.extend(render_table_counts("Draft Routes", value_counts(drafts, "channel_route")))
    lines.extend(render_table_counts("Draft Review Status", value_counts(drafts, "draft_status")))

    lines.extend(["", "## Dashboard Review Items", ""])
    if not review_rows:
        lines.append("No review/ready/fail/blocked dashboard items.")
    else:
        lines.extend(["| area | metric | value | status |", "|---|---|---:|---|"])
        for row in review_rows:
            lines.append(
                f"| {row.get('area', '')} | {row.get('metric', '')} | {row.get('value', '')} | {row.get('status', '')} |"
            )

    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- No Telegram API call.",
            "- No auto-send.",
            "- No trading advice.",
            "- No buy/sell/long/short recommendation language.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    summary, drafts, review_rows = build_summary(args)
    write_summary(normalize_path(args.summary), summary)
    write_markdown(normalize_path(args.markdown_output), summary, drafts, review_rows)
    print(f"status={summary['status']}")
    print(f"total_drafts={summary['total_drafts']}")
    print(f"reviewed_count={summary['reviewed_count']}")
    print(f"validation_fail_count={summary['validation_fail_count']}")
    print(f"wrote_summary={args.summary}")
    print(f"wrote_markdown={args.markdown_output}")


if __name__ == "__main__":
    main()
