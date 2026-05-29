import argparse
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

TYPE_CAPS = {
    "macro": 10,
    "whale_position": 10,
    "institutional_flow": 10,
    "hack_security": 8,
    "exchange_listing": 8,
    "token_unlock": 8,
    "network_upgrade": 8,
    "halving": 5,
    "staking_governance": 5,
    "other": 5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose why a stratified auto50 sample did or did not fill.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "data" / "event_candidates_real_500_older_mature_review_suggested.csv"),
    )
    parser.add_argument(
        "--selected",
        default=str(ROOT / "data" / "event_candidates_real_500_older_mature_review_auto50.csv"),
    )
    parser.add_argument(
        "--summary-output",
        default=str(ROOT / "results" / "v043_stratified_selection_diagnostics.csv"),
    )
    parser.add_argument(
        "--report",
        default=str(ROOT / "results" / "v043_stratified_selection_diagnostics.md"),
    )
    parser.add_argument(
        "--examples-output",
        default=str(ROOT / "results" / "v043_stratified_selection_blocked_examples.csv"),
    )
    parser.add_argument("--limit", type=int, default=50)
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


def split_flags(value: object) -> set[str]:
    return {part.strip() for part in str(value or "").split(",") if part.strip()}


def has_binance_symbol(row: pd.Series) -> bool:
    return bool(str(row.get("candidate_binance_spot_symbol", "")).strip()) or bool(
        str(row.get("candidate_binance_futures_symbol", "")).strip()
    )


def score(row: pd.Series) -> float:
    value = pd.to_numeric(row.get("auto_quality_score", ""), errors="coerce")
    if pd.isna(value):
        return -9999.0
    return float(value)


def block_reasons(row: pd.Series) -> list[str]:
    reasons: list[str] = []
    flags = split_flags(row.get("quality_flags", ""))
    if str(row.get("is_mature_72h", "")).strip().lower() != "true":
        reasons.append("not_mature_72h")
    if str(row.get("suggested_review_decision", "")).strip() not in {"include", "fix"}:
        reasons.append("suggested_exclude")
    if "missing_asset" in flags:
        reasons.append("missing_asset_flag")
    if "time_parse_failed" in flags:
        reasons.append("time_parse_failed")
    if not str(row.get("candidate_asset_symbol", "")).strip():
        reasons.append("missing_asset_symbol")
    if not has_binance_symbol(row):
        reasons.append("missing_binance_symbol")
    if not str(row.get("backtest_time_utc", "")).strip():
        reasons.append("missing_backtest_time_utc")
    if str(row.get("event_scope", "")).strip() == "multi_asset" and score(row) < 90:
        reasons.append("multi_asset_score_below_90")
    return reasons


def is_eligible(row: pd.Series) -> bool:
    return not block_reasons(row)


def render_report(total_rows: int, selected_rows: int, limit: int, by_type: pd.DataFrame, blockers: Counter) -> str:
    underfill = max(limit - selected_rows, 0)
    lines = [
        "# Stratified Selection Diagnostics",
        "",
        f"input_rows: {total_rows}",
        f"selected_rows: {selected_rows}",
        f"target_limit: {limit}",
        f"underfill: {underfill}",
        "",
        "## Interpretation",
        "",
    ]
    if underfill:
        lines.extend(
            [
                "- The sample did not reach the requested limit.",
                "- This is expected when high-volume categories are capped and smaller categories have too few eligible rows.",
                "- Do not relax caps automatically without a product decision; otherwise macro/other can dominate the sample again.",
            ]
        )
    else:
        lines.append("- The sample reached the requested limit.")

    lines.extend(["", "## By Event Type", "", "| event_type | total | eligible | selected | cap | unused_eligible_after_cap |", "|---|---:|---:|---:|---:|---:|"])
    for _, row in by_type.iterrows():
        lines.append(
            f"| {row['event_type']} | {row['total_count']} | {row['eligible_count']} | {row['selected_count']} | {row['type_cap']} | {row['unused_eligible_after_cap']} |"
        )

    lines.extend(["", "## Top Block Reasons", "", "| reason | count |", "|---|---:|"])
    if blockers:
        for reason, count in blockers.most_common(12):
            lines.append(f"| {reason} | {count} |")
    else:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Next Safe Actions",
            "",
            "1. Improve classification for scarce event types before changing caps.",
            "2. Keep macro capped unless Claude approves a separate macro stream.",
            "3. Split `other` before allowing it to fill more backtest slots.",
            "4. Add source/entity rules for unsupported but relevant assets instead of faking Binance symbols.",
            "5. Inspect `results/v043_stratified_selection_blocked_examples.csv` for scarce event-type examples.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_examples(df: pd.DataFrame) -> pd.DataFrame:
    interesting_types = {
        "whale_position",
        "exchange_listing",
        "institutional_flow",
        "network_upgrade",
        "token_unlock",
        "staking_governance",
        "halving",
        "hack_security",
    }
    cols = [
        "candidate_id",
        "candidate_event_type",
        "suggested_review_decision",
        "candidate_asset_symbol",
        "candidate_binance_spot_symbol",
        "candidate_binance_futures_symbol",
        "event_scope",
        "auto_quality_score",
        "eligible_for_stratified",
        "block_reasons",
        "title",
        "source",
    ]
    available_cols = [col for col in cols if col in df.columns]
    examples = df[
        df.get("candidate_event_type", pd.Series(dtype=str)).astype(str).isin(interesting_types)
        & ~df["eligible_for_stratified"]
    ].copy()
    if "auto_quality_score" in examples.columns:
        examples["_score"] = pd.to_numeric(examples["auto_quality_score"], errors="coerce").fillna(-9999)
        examples = examples.sort_values(["candidate_event_type", "_score"], ascending=[True, False])
    return examples[available_cols].head(120)


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    selected_path = normalize_path(args.selected)
    summary_output = normalize_path(args.summary_output)
    report_path = normalize_path(args.report)
    examples_output = normalize_path(args.examples_output)

    df = read_csv(input_path)
    selected = read_csv(selected_path)
    if df.empty:
        print(f"input empty or missing: {input_path}")
        return 1

    selected_ids = set(selected.get("candidate_id", pd.Series(dtype=str)).astype(str))
    df = df.copy()
    df["eligible_for_stratified"] = [is_eligible(row) for _, row in df.iterrows()]
    df["block_reasons"] = [",".join(block_reasons(row)) for _, row in df.iterrows()]
    df["selected_for_auto50"] = df["candidate_id"].astype(str).isin(selected_ids)

    blockers: Counter[str] = Counter()
    for raw in df.loc[~df["eligible_for_stratified"], "block_reasons"]:
        for reason in str(raw).split(","):
            if reason:
                blockers[reason] += 1

    rows = []
    event_types = sorted(set(df.get("candidate_event_type", pd.Series(dtype=str)).astype(str)))
    for event_type in event_types:
        group = df[df["candidate_event_type"].astype(str).eq(event_type)]
        eligible_count = int(group["eligible_for_stratified"].sum())
        selected_count = int(group["selected_for_auto50"].sum())
        cap = TYPE_CAPS.get(event_type, 5)
        rows.append(
            {
                "event_type": event_type or "(blank)",
                "total_count": int(len(group)),
                "eligible_count": eligible_count,
                "selected_count": selected_count,
                "type_cap": cap,
                "unused_eligible_after_cap": max(eligible_count - selected_count, 0),
                "cap_binding": "true" if eligible_count > selected_count and selected_count >= cap else "false",
            }
        )

    by_type = pd.DataFrame(rows).sort_values(["selected_count", "eligible_count", "total_count"], ascending=False)

    summary_output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    examples_output.parent.mkdir(parents=True, exist_ok=True)
    by_type.to_csv(summary_output, index=False)
    build_examples(df).to_csv(examples_output, index=False)
    report_path.write_text(render_report(len(df), len(selected), args.limit, by_type, blockers), encoding="utf-8")
    print(f"wrote diagnostics summary to {summary_output}")
    print(f"wrote diagnostics report to {report_path}")
    print(f"wrote blocked examples to {examples_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
