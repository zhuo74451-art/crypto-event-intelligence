import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


ACTION_RULES = {
    "stratified_selected_count": {
        "owner": "claude_product",
        "requires_claude": "yes",
        "can_do_locally": "no",
        "next_step": "Decide whether to relax event_type caps or improve scarce event-type classification first. Do not change caps locally without direction approval.",
        "evidence_file": "results/v043_stratified_selection_diagnostics.md",
    },
    "v043_selected_v06_discard_rows": {
        "owner": "local_research",
        "requires_claude": "no",
        "can_do_locally": "yes",
        "next_step": "Treat v043 backtest as historical baseline and inspect discarded selected rows before using it as current evidence.",
        "evidence_file": "results/v043_selection_vs_v06_relevance_audit.md",
    },
    "v043_selected_v06_discard_rate": {
        "owner": "local_research",
        "requires_claude": "no",
        "can_do_locally": "yes",
        "next_step": "Use v0.6-filtered preview rather than old v043 selection for any future clean backtest branch.",
        "evidence_file": "results/v043_selection_vs_v06_relevance_audit.md",
    },
    "v043_safe_as_current_evidence": {
        "owner": "local_research",
        "requires_claude": "no",
        "can_do_locally": "yes",
        "next_step": "Keep v043 labeled as historical_baseline_only until a v0.6-filtered clean sample is approved and backtested.",
        "evidence_file": "results/v043_selection_vs_v06_relevance_audit.md",
    },
    "v06_preview_asset_high_risk": {
        "owner": "local_rules_then_claude",
        "requires_claude": "partial",
        "can_do_locally": "partial",
        "next_step": "Apply only obvious dictionary/rule fixes; route protocol exploit and multi-chain policy questions to Claude/product direction.",
        "evidence_file": "results/v06_filtered_preview_asset_attribution_audit.md",
    },
    "v06_entity_protocol_exploit_policy_rows": {
        "owner": "claude_product",
        "requires_claude": "yes",
        "can_do_locally": "no",
        "next_step": "Define primary-asset policy for exploit rows that mix protocol, chain, minted asset, stolen asset, and returned asset.",
        "evidence_file": "results/v06_entity_rule_review_packet.md",
    },
    "ready_for_statistical_conclusions": {
        "owner": "local_research_then_claude",
        "requires_claude": "partial",
        "can_do_locally": "partial",
        "next_step": "Do not cite event-type performance as a product conclusion; use the readiness report to decide what local cleanup remains and what needs Claude/product approval.",
        "evidence_file": "results/backtest_readiness_report.md",
    },
    "backtest_readiness_review_count": {
        "owner": "local_research_then_claude",
        "requires_claude": "partial",
        "can_do_locally": "partial",
        "next_step": "Reduce local data-quality review items where possible; route policy-level blockers to Claude/product direction.",
        "evidence_file": "results/backtest_readiness_report.md",
    },
    "pending_claude_decision_items": {
        "owner": "project_direction",
        "requires_claude": "yes",
        "can_do_locally": "no",
        "next_step": "Send docs/CLAUDE_NEXT_PROMPT.md, then convert accepted recommendations into docs/DECISIONS.md before implementation.",
        "evidence_file": "docs/CLAUDE_DECISION_REVIEW.md",
    },
    "project_os_validation_review_count": {
        "owner": "project_os",
        "requires_claude": "no",
        "can_do_locally": "yes",
        "next_step": "Keep review items visible; do not treat Project OS validation review rows as blocking failures.",
        "evidence_file": "results/project_os_validation_report.md",
    },
    "other_review_keep_review_count": {
        "owner": "local_rules",
        "requires_claude": "no",
        "can_do_locally": "yes",
        "next_step": "Inspect the remaining keep_review rows from the other_review split and convert recurring patterns into explicit taxonomy/entity rules.",
        "evidence_file": "results/v06_other_review_reason_summary.md",
    },
    "daily_private_pilot_status": {
        "owner": "local_rules",
        "requires_claude": "no",
        "can_do_locally": "yes",
        "next_step": "Inspect AI-reviewed draft issue types and rejected rows, then tighten local entity/taxonomy/source rules before expanding the pilot.",
        "evidence_file": "results/daily_private_pilot_report.md",
    },
    "private_pilot_draft_count": {
        "owner": "local_rules",
        "requires_claude": "no",
        "can_do_locally": "yes",
        "next_step": "Keep the first private-pilot queue intentionally small after prefilter tightening; expand only by adding higher-quality sources or eligible event types, not by relaxing noise filters.",
        "evidence_file": "results/daily_private_pilot_report.md",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an actionable queue from dashboard review metrics.")
    parser.add_argument("--metrics", default=str(ROOT / "results" / "project_dashboard_metrics.csv"))
    parser.add_argument("--csv-output", default=str(ROOT / "data" / "project_review_action_queue.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "project_review_action_summary.csv"))
    parser.add_argument("--md-output", default=str(ROOT / "docs" / "PROJECT_REVIEW_ACTIONS.md"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def build_rows(metrics: pd.DataFrame) -> list[dict]:
    if metrics.empty or "status" not in metrics.columns:
        return []
    review_rows = metrics[metrics["status"].astype(str).str.lower().eq("review")].copy()
    rows = []
    for _, item in review_rows.iterrows():
        metric = str(item.get("metric", ""))
        if metric == "review_action_unknown_rules":
            continue
        rule = ACTION_RULES.get(
            metric,
            {
                "owner": "unknown",
                "requires_claude": "unknown",
                "can_do_locally": "unknown",
                "next_step": "Review metric and add an explicit action rule if it remains recurring.",
                "evidence_file": "docs/PROJECT_DASHBOARD.md",
            },
        )
        rows.append(
            {
                "action_id": f"review_{metric}",
                "area": item.get("area", ""),
                "metric": metric,
                "current_value": item.get("value", ""),
                "target": item.get("target", ""),
                "owner": rule["owner"],
                "requires_claude": rule["requires_claude"],
                "can_do_locally": rule["can_do_locally"],
                "next_step": rule["next_step"],
                "evidence_file": rule["evidence_file"],
                "status": "open",
            }
        )
    return rows


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Project Review Actions",
        "",
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
        "",
        "This queue turns dashboard `review` metrics into explicit next actions. It does not approve product-direction changes.",
        "",
    ]
    if not rows:
        lines.append("No dashboard review actions are currently open.")
        return "\n".join(lines) + "\n"

    df = pd.DataFrame(rows)
    lines.extend(["## Counts", "", "| field | value |", "|---|---:|"])
    lines.append(f"| open_actions | {len(df)} |")
    lines.append(f"| requires_claude_yes | {int(df['requires_claude'].eq('yes').sum())} |")
    lines.append(f"| can_do_locally_yes | {int(df['can_do_locally'].eq('yes').sum())} |")

    lines.extend(
        [
            "",
            "## Actions",
            "",
            "| action_id | owner | value | next_step | evidence |",
            "|---|---|---:|---|---|",
        ]
    )
    for row in rows:
        next_step = str(row["next_step"]).replace("|", "\\|")
        lines.append(
            f"| `{row['action_id']}` | {row['owner']} | {row['current_value']} | {next_step} | `{row['evidence_file']}` |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    metrics_path = normalize_path(args.metrics)
    csv_output = normalize_path(args.csv_output)
    summary_output = normalize_path(args.summary)
    md_output = normalize_path(args.md_output)

    rows = build_rows(safe_read_csv(metrics_path))
    df = pd.DataFrame(rows)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_output, index=False)

    if df.empty:
        summary = {
            "open_action_count": 0,
            "requires_claude_yes_count": 0,
            "can_do_locally_yes_count": 0,
            "unknown_rule_count": 0,
            "status": "pass",
        }
    else:
        summary = {
            "open_action_count": len(df),
            "requires_claude_yes_count": int(df["requires_claude"].eq("yes").sum()),
            "can_do_locally_yes_count": int(df["can_do_locally"].eq("yes").sum()),
            "unknown_rule_count": int(df["owner"].eq("unknown").sum()),
            "status": "pass" if int(df["owner"].eq("unknown").sum()) == 0 else "review",
        }
    pd.DataFrame([summary]).to_csv(summary_output, index=False)
    md_output.write_text(render_markdown(rows), encoding="utf-8")
    print(f"wrote project review action queue to {csv_output}")
    print(f"wrote project review action summary to {summary_output}")
    print(f"wrote project review action markdown to {md_output}")
    return 0 if summary["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
