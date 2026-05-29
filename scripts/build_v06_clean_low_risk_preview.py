import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a clean low-risk v0.6 preview subset.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "results" / "v06_filtered_preview_asset_attribution_audit.csv"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "event_candidates_v06_clean_low_risk_preview.csv"),
    )
    parser.add_argument(
        "--summary",
        default=str(ROOT / "results" / "v06_clean_low_risk_preview_summary.csv"),
    )
    parser.add_argument(
        "--report",
        default=str(ROOT / "results" / "v06_clean_low_risk_preview.md"),
    )
    parser.add_argument("--limit", type=int, default=50)
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def render_report(clean: pd.DataFrame, summary: pd.DataFrame) -> str:
    first = summary.iloc[0].to_dict() if not summary.empty else {}
    lines = [
        "# v0.6 Clean Low-Risk Preview",
        "",
        f"input_rows: {first.get('input_rows', 0)}",
        f"selected_low_risk_rows: {first.get('selected_low_risk_rows', 0)}",
        f"excluded_medium_risk_rows: {first.get('excluded_medium_risk_rows', 0)}",
        f"excluded_high_risk_rows: {first.get('excluded_high_risk_rows', 0)}",
        "",
        "## Interpretation",
        "",
        "- This file is a conservative preview subset only.",
        "- It excludes medium/high asset-attribution risk rows.",
        "- It is too small for statistical event-type conclusions.",
        "- It can be used as a sanity-check sample before deciding whether to build a v0.6-filtered backtest branch.",
        "",
        "## By Event Type",
        "",
        "| event_type | count |",
        "|---|---:|",
    ]
    if clean.empty:
        lines.append("| none | 0 |")
    else:
        for event_type, count in clean["v06_stratify_type"].value_counts().items():
            lines.append(f"| {event_type} | {int(count)} |")

    lines.extend(["", "## By Asset", "", "| asset | count |", "|---|---:|"])
    if clean.empty:
        lines.append("| none | 0 |")
    else:
        for asset, count in clean["candidate_asset_symbol"].value_counts().items():
            lines.append(f"| {asset} | {int(count)} |")

    lines.extend(["", "## Selected Rows", "", "| candidate_id | event_type | asset | route | title |", "|---|---|---|---|---|"])
    if clean.empty:
        lines.append("| none |  |  |  |  |")
    else:
        for _, row in clean.iterrows():
            title = str(row.get("title", "")).replace("|", "/").replace("\n", " ")[:120]
            lines.append(
                f"| {row.get('candidate_id', '')} | {row.get('v06_stratify_type', '')} | {row.get('candidate_asset_symbol', '')} | {row.get('channel_route', '')} | {title} |"
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
    if "asset_attribution_risk" not in df.columns:
        print("input missing asset_attribution_risk")
        return 1

    clean = df[df["asset_attribution_risk"].eq("low")].copy()
    if "relevance_score_realtime" in clean.columns:
        clean["_score"] = pd.to_numeric(clean["relevance_score_realtime"], errors="coerce").fillna(-9999)
        clean = clean.sort_values(["_score", "candidate_id"], ascending=[False, True])
    clean = clean.head(args.limit).drop(columns=["_score"], errors="ignore")
    clean["review_decision"] = "include"
    clean["v06_clean_low_risk_preview"] = "true"

    summary = pd.DataFrame(
        [
            {
                "input_rows": int(len(df)),
                "selected_low_risk_rows": int(len(clean)),
                "excluded_medium_risk_rows": int(df["asset_attribution_risk"].eq("medium").sum()),
                "excluded_high_risk_rows": int(df["asset_attribution_risk"].eq("high").sum()),
                "limit": args.limit,
                "status": "preview_only",
            }
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(output_path, index=False)
    summary.to_csv(summary_path, index=False)
    report_path.write_text(render_report(clean, summary), encoding="utf-8")
    print(f"selected_low_risk_rows={len(clean)}")
    print(f"wrote clean preview to {output_path}")
    print(f"wrote summary to {summary_path}")
    print(f"wrote report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
