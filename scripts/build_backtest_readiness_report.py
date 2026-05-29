import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a concise backtest readiness and conclusion-safety report.")
    parser.add_argument("--output", default=str(ROOT / "results" / "backtest_readiness_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "backtest_readiness_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "backtest_readiness_report.md"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def first_row(path: Path) -> dict:
    df = read_csv(path)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def as_int(value: object, default: int = 0) -> int:
    try:
        if value in {"", None}:
            return default
        return int(float(str(value)))
    except Exception:
        return default


def count_value(path: Path, column: str, value: str) -> int:
    df = read_csv(path)
    if df.empty or column not in df.columns:
        return 0
    return int(df[column].astype(str).eq(value).sum())


def status_row(
    area: str,
    check: str,
    actual: object,
    required: str,
    status: str,
    evidence: str,
    implication: str,
    owner_class: str,
    blocker_type: str,
    next_action: str,
) -> dict:
    return {
        "area": area,
        "check": check,
        "actual": actual,
        "required": required,
        "status": status,
        "evidence": evidence,
        "implication": implication,
        "owner_class": owner_class,
        "blocker_type": blocker_type,
        "next_action": next_action,
    }


def build_rows() -> list[dict]:
    v043 = first_row(ROOT / "results" / "v043_selection_vs_v06_relevance_summary.csv")
    v06_preview = first_row(ROOT / "results" / "v06_filtered_mature_sample_preview_summary.csv")
    asset_audit = first_row(ROOT / "results" / "v06_filtered_preview_asset_attribution_summary.csv")
    clean_preview = first_row(ROOT / "results" / "v06_clean_low_risk_preview_summary.csv")
    entity_packet = first_row(ROOT / "results" / "v06_entity_rule_review_packet_summary.csv")

    low_risk_backfill_ok = count_value(ROOT / "results" / "v06_clean_low_risk_preview_event_price_backfill.csv", "status", "ok")
    low_risk_quality_pass = count_value(
        ROOT / "results" / "v06_clean_low_risk_preview_event_quality_report.csv", "quality_status", "pass"
    )

    rows = [
        status_row(
            "v043",
            "historical_sample_current_evidence",
            v043.get("safe_to_use_as_current_evidence", "missing"),
            "yes",
            "review" if v043.get("safe_to_use_as_current_evidence") == "no" else "pass",
            "results/v043_selection_vs_v06_relevance_summary.csv",
            "v043 backtest remains historical_baseline_only until a v0.6-filtered clean sample is approved.",
            "local_research",
            "historical_baseline",
            "Keep v043 out of current claims; use v0.6-filtered branches for future clean runs.",
        ),
        status_row(
            "v043",
            "v06_discard_contamination",
            v043.get("v06_discard_rows", "missing"),
            "0",
            "review" if as_int(v043.get("v06_discard_rows")) else "pass",
            "results/v043_selection_vs_v06_relevance_audit.md",
            "Rows discarded by current relevance scoring cannot support current event-type conclusions.",
            "local_research",
            "sample_contamination",
            "Inspect discarded v043 rows only as historical contamination evidence.",
        ),
        status_row(
            "v06_preview",
            "filtered_preview_selected_count",
            v06_preview.get("selected_count", "missing"),
            "50 desired",
            "pass" if as_int(v06_preview.get("selected_count")) >= 50 else "review",
            "results/v06_filtered_mature_sample_preview_summary.csv",
            "Preview has enough rows for pipeline planning, not for final statistical claims.",
            "local_research",
            "sample_size",
            "Use this preview for planning after attribution cleanup, not as conclusion evidence.",
        ),
        status_row(
            "v06_preview",
            "asset_high_risk_rows",
            asset_audit.get("high_risk_rows", "missing"),
            "0 before clean backtest",
            "review" if as_int(asset_audit.get("high_risk_rows")) else "pass",
            "results/v06_filtered_preview_asset_attribution_audit.md",
            "High-risk attribution rows should be fixed or excluded before a clean backtest branch.",
            "local_rules_then_claude",
            "asset_attribution",
            "Apply obvious dictionary/symbol fixes locally; send policy rows to Claude/product.",
        ),
        status_row(
            "v06_preview",
            "protocol_policy_rows",
            entity_packet.get("count", "missing"),
            "0 unresolved policy rows",
            "review" if as_int(entity_packet.get("count")) else "pass",
            "results/v06_entity_rule_review_packet.md",
            "Protocol exploit and multi-chain policy rows require Claude/product direction before automatic fixes.",
            "claude_product",
            "policy_decision",
            "Ask Claude/product for protocol exploit and multi-chain attribution policy.",
        ),
        status_row(
            "v06_low_risk",
            "low_risk_preview_rows",
            clean_preview.get("selected_low_risk_rows", "missing"),
            ">=50 for real sample, current is sanity-check",
            "review" if as_int(clean_preview.get("selected_low_risk_rows")) < 50 else "pass",
            "results/v06_clean_low_risk_preview_summary.csv",
            "Low-risk subset is useful for sanity-checking the pipeline, not for statistical conclusions.",
            "local_research",
            "sample_size",
            "Use as sanity-check only; grow clean sample after attribution policy is settled.",
        ),
        status_row(
            "v06_low_risk",
            "low_risk_backfill_ok_rows",
            low_risk_backfill_ok,
            "matches low-risk preview rows",
            "pass" if low_risk_backfill_ok and low_risk_backfill_ok == as_int(clean_preview.get("selected_low_risk_rows")) else "review",
            "results/v06_clean_low_risk_preview_event_price_backfill.csv",
            "Confirms the low-risk preview rows can be converted into price-backed events.",
            "local_research",
            "pipeline_health",
            "Keep as green sanity-check evidence.",
        ),
        status_row(
            "v06_low_risk",
            "low_risk_quality_pass_rows",
            low_risk_quality_pass,
            "matches low-risk preview rows",
            "pass" if low_risk_quality_pass and low_risk_quality_pass == as_int(clean_preview.get("selected_low_risk_rows")) else "review",
            "results/v06_clean_low_risk_preview_event_quality_report.csv",
            "Confirms the low-risk preview backfill has no quality failures.",
            "local_research",
            "pipeline_health",
            "Keep as green quality evidence.",
        ),
    ]
    return rows


def render_markdown(rows: list[dict], summary: dict) -> str:
    lines = [
        "# Backtest Readiness Report",
        "",
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
        "",
        f"overall_conclusion_status: {summary['overall_conclusion_status']}",
        f"review_count: {summary['review_count']}",
        f"local_review_count: {summary['local_review_count']}",
        f"claude_review_count: {summary['claude_review_count']}",
        f"mixed_local_claude_review_count: {summary['mixed_local_claude_review_count']}",
        f"pass_count: {summary['pass_count']}",
        "",
        "## Interpretation",
        "",
        "- `ready_for_statistical_conclusions=no` means do not cite event-type performance as a product conclusion.",
        "- `v043` remains a historical baseline because current v0.6 relevance scoring discards some selected rows.",
        "- `v06_low_risk` is a pipeline sanity-check branch only; its sample is intentionally small.",
        "",
        "| area | check | actual | required | status | owner | blocker_type | next_action |",
        "|---|---|---:|---|---|---|---|---|",
    ]
    for row in rows:
        next_action = str(row["next_action"]).replace("|", "/")
        lines.append(
            f"| {row['area']} | {row['check']} | {row['actual']} | {row['required']} | {row['status']} | {row['owner_class']} | {row['blocker_type']} | {next_action} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    rows = build_rows()
    review_count = sum(1 for row in rows if row["status"] == "review")
    pass_count = sum(1 for row in rows if row["status"] == "pass")
    local_review_count = sum(
        1 for row in rows if row["status"] == "review" and str(row.get("owner_class", "")) == "local_research"
    )
    claude_review_count = sum(
        1 for row in rows if row["status"] == "review" and str(row.get("owner_class", "")) == "claude_product"
    )
    mixed_review_count = sum(
        1 for row in rows if row["status"] == "review" and "then_claude" in str(row.get("owner_class", ""))
    )
    summary = {
        "overall_conclusion_status": "not_ready" if review_count else "ready",
        "ready_for_statistical_conclusions": "no" if review_count else "yes",
        "review_count": review_count,
        "local_review_count": local_review_count,
        "claude_review_count": claude_review_count,
        "mixed_local_claude_review_count": mixed_review_count,
        "pass_count": pass_count,
        "total_checks": len(rows),
    }

    output = normalize_path(args.output)
    summary_output = normalize_path(args.summary)
    markdown_output = normalize_path(args.markdown_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(rows).to_csv(output, index=False)
    pd.DataFrame([summary]).to_csv(summary_output, index=False)
    markdown_output.write_text(render_markdown(rows, summary), encoding="utf-8")
    print(f"wrote readiness report to {output}")
    print(f"wrote readiness summary to {summary_output}")
    print(f"wrote readiness markdown to {markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
