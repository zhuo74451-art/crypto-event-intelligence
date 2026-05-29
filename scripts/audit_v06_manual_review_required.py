import argparse
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TARGET_RATE = 0.085


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit v0.6 manual_review_required rows and summarize failure modes.")
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_review_required_audit.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_manual_review_required_summary.csv"))
    parser.add_argument("--report", default=str(ROOT / "results" / "v06_manual_review_required_report.md"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def text(row: pd.Series, column: str) -> str:
    return str(row.get(column, "") or "").strip()


def lower(row: pd.Series, column: str) -> str:
    return text(row, column).lower()


def numeric(row: pd.Series, column: str) -> float:
    value = pd.to_numeric(row.get(column, ""), errors="coerce")
    if pd.isna(value):
        return 0.0
    return float(value)


def classify(row: pd.Series) -> list[str]:
    flags: list[str] = []
    event_scope = lower(row, "event_scope")
    event_type = lower(row, "manual_event_type_l1") or lower(row, "event_type_l1")
    asset = text(row, "manual_primary_asset_symbol") or text(row, "primary_asset_symbol") or text(row, "candidate_asset_symbol")
    confidence = numeric(row, "auto_label_confidence")
    label_origin = lower(row, "label_origin")
    route = lower(row, "manual_channel_route") or lower(row, "channel_route")

    if confidence < 0.75:
        flags.append("low_ai_confidence")
    if event_scope in {"unknown", "multi_asset"}:
        flags.append("scope_ambiguous")
    if not asset:
        flags.append("asset_missing")
    if event_type in {"other", "other_review", ""}:
        flags.append("taxonomy_ambiguous")
    if route in {"macro_policy", "research_only"}:
        flags.append(f"route_{route}")
    if label_origin == "auto_provisional":
        flags.append("auto_provisional_needs_audit")
    if label_origin == "auto_medium_conf_review_required":
        flags.append("medium_confidence_review")
    return flags or ["needs_policy_review"]


def build_report(audit: pd.DataFrame, summary: pd.DataFrame) -> str:
    total = int(summary.iloc[0]["manual_review_required_rows"]) if not summary.empty else 0
    top_modes = []
    if not audit.empty:
        counter: Counter[str] = Counter()
        for raw in audit["review_failure_modes"].fillna(""):
            for item in str(raw).split(","):
                item = item.strip()
                if item:
                    counter[item] += 1
        top_modes = counter.most_common(10)

    lines = [
        "# v0.6 Manual Review Required Audit",
        "",
        f"manual_review_required_rows: {total}",
        "",
        "## Top Failure Modes",
        "",
        "| mode | count |",
        "|---|---:|",
    ]
    if top_modes:
        for mode, count in top_modes:
            lines.append(f"| {mode} | {count} |")
    else:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- These rows should not block AI-first development by default.",
            "- They should be used as audit/holdout examples and rule-improvement input.",
            "- TG draft generation remains delayed until the stricter direction gate passes.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    report_path = normalize_path(args.report)

    if not input_path.exists():
        print(f"input not found: {input_path}")
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    if "manual_review_required" not in df.columns:
        audit = df.head(0).copy()
    else:
        audit = df[df["manual_review_required"].astype(str).str.lower().eq("true")].copy()

    if not audit.empty:
        audit["review_failure_modes"] = [",".join(classify(row)) for _, row in audit.iterrows()]
        audit["review_failure_primary"] = audit["review_failure_modes"].str.split(",").str[0]
    else:
        audit["review_failure_modes"] = []
        audit["review_failure_primary"] = []

    total_rows = len(df)
    review_rows = len(audit)
    summary = pd.DataFrame(
        [
            {
                "total_rows": total_rows,
                "manual_review_required_rows": review_rows,
                "manual_review_required_rate": round(review_rows / total_rows, 4) if total_rows else 0,
                "target_rate": TARGET_RATE,
                "status": "pass" if total_rows and review_rows / total_rows <= TARGET_RATE else "fail",
            }
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(output_path, index=False)
    summary.to_csv(summary_path, index=False)
    report_path.write_text(build_report(audit, summary), encoding="utf-8")
    print(f"wrote audit rows to {output_path}")
    print(f"wrote summary to {summary_path}")
    print(f"wrote report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
