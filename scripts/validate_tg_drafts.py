import argparse
import csv
import re
from pathlib import Path


PROHIBITED_PATTERNS = [
    r"建议\s*(买入|卖出|做多|做空|开多|开空|加仓|减仓|止盈|止损)",
    r"(买入|卖出|做多|做空|开多|开空)\s*信号",
    r"(buy now|sell now|go long|go short|open long|open short|take profit|stop loss|entry price)",
]

REQUIRED_FIELDS = [
    "draft_id",
    "candidate_id",
    "published_at_china",
    "asset_symbol",
    "event_type",
    "channel_route",
    "draft_text",
    "draft_status",
    "auto_send_enabled",
]

VALID_DRAFT_STATUSES = {"pending_review", "approved", "rejected", "needs_edit", "ready"}
RISK_NOTE_FRAGMENTS = {"不构成交易建议", "不构成任何交易建议"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate local TG draft queue safety and completeness.")
    parser.add_argument("--input", default="data/tg_drafts_v06_private_pilot.csv")
    parser.add_argument("--output", default="results/tg_draft_validation_report.csv")
    parser.add_argument("--summary", default="results/tg_draft_validation_summary.csv")
    parser.add_argument("--markdown-output", default="results/tg_draft_validation_report.md")
    return parser.parse_args()


def norm(value: str) -> str:
    return str(value or "").strip()


def validate_row(row: dict) -> dict:
    flags = []
    for field in REQUIRED_FIELDS:
        if not norm(row.get(field)):
            flags.append(f"missing_{field}")

    if norm(row.get("auto_send_enabled")).lower() != "false":
        flags.append("auto_send_enabled_not_false")

    if norm(row.get("draft_status")).lower() not in VALID_DRAFT_STATUSES:
        flags.append("invalid_draft_status")

    draft_text = norm(row.get("draft_text"))
    for pattern in PROHIBITED_PATTERNS:
        if re.search(pattern, draft_text, flags=re.IGNORECASE):
            flags.append("prohibited_recommendation_language")
            break

    if not any(fragment in draft_text for fragment in RISK_NOTE_FRAGMENTS):
        flags.append("missing_risk_note")

    status = "fail" if any(flag in flags for flag in ["auto_send_enabled_not_false", "prohibited_recommendation_language"]) else "pass"
    if status == "pass" and flags:
        status = "warning"

    return {
        "draft_id": norm(row.get("draft_id")),
        "candidate_id": norm(row.get("candidate_id")),
        "asset_symbol": norm(row.get("asset_symbol")),
        "event_type": norm(row.get("event_type")),
        "draft_status": norm(row.get("draft_status")),
        "validation_status": status,
        "validation_flags": ",".join(flags),
    }


def write_markdown(path: Path, rows: list[dict], summary: dict) -> None:
    lines = [
        "# TG Draft Validation Report",
        "",
        "This validates local draft safety only. It does not send messages or approve publishing.",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| {key} | {value} |")
    issues = [row for row in rows if row["validation_status"] != "pass"]
    lines.extend(["", "## Issues", ""])
    if not issues:
        lines.append("No draft validation issues.")
    else:
        lines.extend(["| draft_id | candidate_id | status | flags |", "|---|---|---|---|"])
        for row in issues:
            lines.append(
                f"| {row['draft_id']} | {row['candidate_id']} | {row['validation_status']} | {row['validation_flags']} |"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    rows = list(csv.DictReader(input_path.open("r", encoding="utf-8-sig", newline="")))
    report_rows = [validate_row(row) for row in rows]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "draft_id",
        "candidate_id",
        "asset_symbol",
        "event_type",
        "draft_status",
        "validation_status",
        "validation_flags",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    fail_count = sum(1 for row in report_rows if row["validation_status"] == "fail")
    warning_count = sum(1 for row in report_rows if row["validation_status"] == "warning")
    pass_count = sum(1 for row in report_rows if row["validation_status"] == "pass")
    summary = {
        "total_drafts": len(report_rows),
        "pass_count": pass_count,
        "warning_count": warning_count,
        "fail_count": fail_count,
        "auto_send_enabled_count": sum(1 for row in rows if norm(row.get("auto_send_enabled")).lower() == "true"),
        "status": "pass" if fail_count == 0 else "fail",
    }

    summary_path = Path(args.summary)
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    write_markdown(Path(args.markdown_output), report_rows, summary)
    print(f"total_drafts={len(report_rows)}")
    print(f"fail_count={fail_count}")
    print(f"warning_count={warning_count}")
    print(f"wrote_report={output_path}")
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
