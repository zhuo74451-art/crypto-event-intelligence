import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check v0.6 gate for TG draft pilot. This does not enable auto-send.")
    parser.add_argument("--label-summary", default=str(ROOT / "results" / "v06_manual_label_eval_summary.csv"))
    parser.add_argument("--label-sheet", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--time-summary", default=str(ROOT / "results" / "v043_time_provenance_summary.csv"))
    parser.add_argument("--relevance-summary", default=str(ROOT / "results" / "v06_relevance_filter_summary.csv"))
    parser.add_argument("--synthetic-summary", default=str(ROOT / "results" / "v06_synthetic_edge_cases_summary.csv"))
    parser.add_argument("--secret-summary", default=str(ROOT / "results" / "secret_leak_summary.csv"))
    parser.add_argument("--failure-modes-doc", default=str(ROOT / "docs" / "V06_REVIEW_FAILURE_MODES.md"))
    parser.add_argument("--rollback-doc", default=str(ROOT / "docs" / "V06_ROLLBACK_WORKFLOW.md"))
    parser.add_argument("--audit-files", nargs="*", default=[
        str(ROOT / "data" / "v06_auto_verify_audit_sample.csv"),
        str(ROOT / "data" / "v06_auto_close_audit_sample.csv"),
        str(ROOT / "data" / "v06_auto_fill_unlabeled_audit_sample.csv"),
        str(ROOT / "data" / "v06_holdout_audit_sample.csv"),
    ])
    parser.add_argument("--output", default=str(ROOT / "results" / "v06_tg_pilot_gate_report.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v06_tg_pilot_gate_report.md"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def first_row(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        return df.iloc[0].to_dict() if not df.empty else {}
    except Exception:
        return {}


def int_value(value: object, default: int = 0) -> int:
    try:
        text = str(value).strip()
        if text == "":
            return default
        return int(float(text))
    except Exception:
        return default


def float_value(value: object, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
        if text == "":
            return default
        return float(text)
    except Exception:
        return default


def manual_review_required(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
    except Exception:
        return 0
    if "manual_review_required" not in df.columns:
        return 0
    return int(df["manual_review_required"].astype(str).str.lower().eq("true").sum())


def audit_rows(paths: list[str]) -> int:
    total = 0
    for raw in paths:
        path = normalize_path(raw)
        if not path.exists():
            continue
        try:
            total += len(pd.read_csv(path, dtype=str))
        except Exception:
            continue
    return total


def doc_has_sections(path: Path, required_sections: list[str]) -> bool:
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except Exception:
        return False
    return all(section.lower() in text for section in required_sections)


def build_rows(args: argparse.Namespace) -> list[dict]:
    label = first_row(normalize_path(args.label_summary))
    time_summary = first_row(normalize_path(args.time_summary))
    relevance = first_row(normalize_path(args.relevance_summary))
    synthetic = first_row(normalize_path(args.synthetic_summary))
    secret_summary = first_row(normalize_path(args.secret_summary))
    sheet_path = normalize_path(args.label_sheet)

    labeled_rows = int_value(label.get("labeled_rows"))
    fp_count = int_value(label.get("false_positive_review_count"))
    total_rows = max(int_value(label.get("total_rows")), 1)
    false_positive_rate = fp_count / total_rows
    manual_queue = manual_review_required(sheet_path)
    audits = audit_rows(args.audit_files)
    timezone_fail = int_value(time_summary.get("fail_count"))
    auto_publish = int_value(relevance.get("auto_publish_count"))
    synthetic_rows = int_value(synthetic.get("synthetic_edge_cases"))
    secret_leaks = int_value(secret_summary.get("leak_count"))
    failure_doc_ok = doc_has_sections(
        normalize_path(args.failure_modes_doc),
        ["## Failure Modes", "## Rules Not To Add Yet", "## Regression Cases"],
    )
    rollback_doc_ok = doc_has_sections(
        normalize_path(args.rollback_doc),
        ["## Rollback Triggers", "## Rollback Steps", "## Current Non-Negotiables"],
    )

    manual_rate = manual_queue / total_rows

    checks = [
        ("labeled_rows", labeled_rows, ">=201", labeled_rows >= 201),
        ("manual_review_required_rate", round(manual_rate, 4), "<=0.085", manual_rate <= 0.085),
        ("audit_sample_rows", audits, ">=200", audits >= 200),
        ("synthetic_edge_cases", synthetic_rows, ">=15", synthetic_rows >= 15),
        ("false_positive_rate", round(false_positive_rate, 4), "<=0.02", false_positive_rate <= 0.02),
        ("timezone_fail_count", timezone_fail, "0", timezone_fail == 0),
        ("auto_publish_count", auto_publish, "0", auto_publish == 0),
        ("secret_leak_count", secret_leaks, "0", secret_leaks == 0),
        ("review_failure_modes_doc", "present" if failure_doc_ok else "missing/incomplete", "required sections", failure_doc_ok),
        ("rollback_workflow_doc", "present" if rollback_doc_ok else "missing/incomplete", "required sections", rollback_doc_ok),
    ]
    return [
        {
            "gate": name,
            "actual": actual,
            "required": required,
            "status": "pass" if ok else "fail",
        }
        for name, actual, required, ok in checks
    ]


def render_markdown(rows: list[dict]) -> str:
    overall = "pass" if all(row["status"] == "pass" for row in rows) else "fail"
    lines = [
        "# v0.6 TG Draft Pilot Gate",
        "",
        f"overall_status: {overall}",
        "",
        "| gate | actual | required | status |",
        "|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(f"| {row['gate']} | {row['actual']} | {row['required']} | {row['status']} |")
    lines.extend([
        "",
        "Scope:",
        "",
        "- This is the stricter gate from `results/v06_claude_next_engineering_direction.md`.",
        "- Passing allows TG draft generator work only, not auto-send.",
        "- It does not allow trading advice.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    rows = build_rows(args)
    output = normalize_path(args.output)
    markdown_output = normalize_path(args.markdown_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    markdown_output.write_text(render_markdown(rows), encoding="utf-8")
    print(f"wrote gate report to {output}")
    print(f"wrote gate markdown to {markdown_output}")
    return 0 if all(row["status"] == "pass" for row in rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
