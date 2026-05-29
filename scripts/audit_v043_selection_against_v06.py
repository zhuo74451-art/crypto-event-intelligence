import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit v043 stratified selection against v0.6 relevance decisions.")
    parser.add_argument(
        "--selected",
        default=str(ROOT / "data" / "event_candidates_real_500_older_mature_review_auto50.csv"),
    )
    parser.add_argument(
        "--v06-scored",
        default=str(ROOT / "data" / "event_candidates_v06_relevance_scored.csv"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "v043_selection_vs_v06_relevance_audit.csv"),
    )
    parser.add_argument(
        "--summary",
        default=str(ROOT / "results" / "v043_selection_vs_v06_relevance_summary.csv"),
    )
    parser.add_argument(
        "--discard-breakdown",
        default=str(ROOT / "results" / "v043_selection_vs_v06_discard_breakdown.csv"),
    )
    parser.add_argument(
        "--event-type-impact",
        default=str(ROOT / "results" / "v043_selection_vs_v06_event_type_impact.csv"),
    )
    parser.add_argument(
        "--report",
        default=str(ROOT / "results" / "v043_selection_vs_v06_relevance_audit.md"),
    )
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str).fillna("")


def group_count(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return pd.DataFrame(columns=[column, "count"])
    counts = df[column].astype(str).replace("", "(blank)").value_counts().reset_index()
    counts.columns = [column, "count"]
    return counts


def event_type_impact(audit: pd.DataFrame) -> pd.DataFrame:
    if audit.empty:
        return pd.DataFrame()
    group_col = "candidate_event_type"
    rows = []
    for event_type, group in audit.groupby(group_col, dropna=False):
        selected_count = int(len(group))
        discard_count = int(group["publish_decision"].eq("discard").sum())
        human_review_count = int(group["publish_decision"].eq("human_review").sum())
        rows.append(
            {
                "candidate_event_type": event_type or "(blank)",
                "selected_count": selected_count,
                "v06_human_review_count": human_review_count,
                "v06_discard_count": discard_count,
                "v06_discard_rate": round(discard_count / selected_count, 4) if selected_count else 0,
            }
        )
    return pd.DataFrame(rows).sort_values(["v06_discard_count", "selected_count"], ascending=[False, False])


def render_report(audit: pd.DataFrame, summary: dict, discard_breakdown: pd.DataFrame, impact: pd.DataFrame) -> str:
    lines = [
        "# v043 Selection vs v0.6 Relevance Audit",
        "",
        f"selected_rows: {summary['selected_rows']}",
        f"matched_v06_rows: {summary['matched_v06_rows']}",
        f"v06_human_review_rows: {summary['v06_human_review_rows']}",
        f"v06_discard_rows: {summary['v06_discard_rows']}",
        f"v06_discard_rate: {summary['v06_discard_rate']}",
        f"safe_to_use_as_current_evidence: {summary['safe_to_use_as_current_evidence']}",
        f"recommended_use: {summary['recommended_use']}",
        "",
        "## Interpretation",
        "",
    ]
    if summary["v06_discard_rows"]:
        lines.extend(
            [
                "- The older v043 stratified selection includes rows that v0.6 relevance scoring would discard.",
                "- Treat the existing v043 mature50 backtest as a historical baseline, not the cleanest current sample.",
                "- Do not overwrite the historical v043 outputs; build a new v06-filtered sample if direction approves.",
                "- Any event-type conclusion from v043 should mention the discard contamination rate.",
            ]
        )
    else:
        lines.append("- The v043 selected sample is consistent with v0.6 relevance scoring.")

    lines.extend(
        [
            "",
            "## Discard Reason Breakdown",
            "",
            "| primary_discard_reason | count |",
            "|---|---:|",
        ]
    )
    if discard_breakdown.empty:
        lines.append("| none | 0 |")
    else:
        for _, row in discard_breakdown.iterrows():
            lines.append(f"| {row.get('primary_discard_reason', '')} | {row.get('count', 0)} |")

    lines.extend(
        [
            "",
            "## Event Type Impact",
            "",
            "| candidate_event_type | selected_count | v06_discard_count | v06_discard_rate |",
            "|---|---:|---:|---:|",
        ]
    )
    if impact.empty:
        lines.append("| none | 0 | 0 | 0 |")
    else:
        for _, row in impact.iterrows():
            lines.append(
                f"| {row.get('candidate_event_type', '')} | {row.get('selected_count', 0)} | {row.get('v06_discard_count', 0)} | {row.get('v06_discard_rate', 0)} |"
            )

    lines.extend(["", "## v06 Discarded Selected Rows", "", "| candidate_id | candidate_event_type | v06_type | primary_discard_reason | title |", "|---|---|---|---|---|"])
    discarded = audit[audit["publish_decision"].eq("discard")].copy()
    if discarded.empty:
        lines.append("| none |  |  |  |  |")
    else:
        for _, row in discarded.head(30).iterrows():
            title = str(row.get("title", "")).replace("|", "/").replace("\n", " ")[:120]
            lines.append(
                f"| {row.get('candidate_id', '')} | {row.get('candidate_event_type', '')} | {row.get('event_type_l1', '')}/{row.get('event_type_l2', '')} | {row.get('primary_discard_reason', '')} | {title} |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    selected_path = normalize_path(args.selected)
    scored_path = normalize_path(args.v06_scored)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    discard_breakdown_path = normalize_path(args.discard_breakdown)
    event_type_impact_path = normalize_path(args.event_type_impact)
    report_path = normalize_path(args.report)

    selected = read_csv(selected_path)
    scored = read_csv(scored_path)
    if selected.empty:
        print(f"selected file missing or empty: {selected_path}")
        return 1
    if scored.empty:
        print(f"v06 scored file missing or empty: {scored_path}")
        return 1
    if "candidate_id" not in selected.columns or "candidate_id" not in scored.columns:
        print("candidate_id column missing")
        return 1

    v06_cols = [
        "candidate_id",
        "publish_decision",
        "discard_reason",
        "primary_discard_reason",
        "channel_route",
        "event_type_l1",
        "event_type_l2",
        "entity_flags",
        "relevance_score_realtime",
    ]
    available_v06_cols = [col for col in v06_cols if col in scored.columns]
    audit = selected.merge(scored[available_v06_cols], on="candidate_id", how="left", suffixes=("", "_v06"))
    matched = audit["publish_decision"].astype(str).str.strip().ne("")
    discarded = audit["publish_decision"].eq("discard")
    human_review = audit["publish_decision"].eq("human_review")
    selected_rows = int(len(audit))
    summary = {
        "selected_rows": selected_rows,
        "matched_v06_rows": int(matched.sum()),
        "v06_human_review_rows": int(human_review.sum()),
        "v06_discard_rows": int(discarded.sum()),
        "v06_missing_rows": int((~matched).sum()),
        "v06_discard_rate": round(int(discarded.sum()) / selected_rows, 4) if selected_rows else 0,
    }
    summary["safe_to_use_as_current_evidence"] = "no" if summary["v06_discard_rows"] else "yes"
    summary["recommended_use"] = (
        "historical_baseline_only"
        if summary["v06_discard_rows"]
        else "current_relevance_consistent"
    )
    summary["clean_sample_next_step"] = (
        "use_v06_filtered_preview_after_asset_attribution_cleanup"
        if summary["v06_discard_rows"]
        else "optional_rebacktest"
    )
    discard_breakdown = group_count(audit[audit["publish_decision"].eq("discard")], "primary_discard_reason")
    impact = event_type_impact(audit)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    discard_breakdown_path.parent.mkdir(parents=True, exist_ok=True)
    event_type_impact_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(output_path, index=False)
    pd.DataFrame([summary]).to_csv(summary_path, index=False)
    discard_breakdown.to_csv(discard_breakdown_path, index=False)
    impact.to_csv(event_type_impact_path, index=False)
    report_path.write_text(render_report(audit, summary, discard_breakdown, impact), encoding="utf-8")
    print(f"wrote audit to {output_path}")
    print(f"wrote summary to {summary_path}")
    print(f"wrote discard breakdown to {discard_breakdown_path}")
    print(f"wrote event type impact to {event_type_impact_path}")
    print(f"wrote report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
