import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

TYPE_CAPS = {
    "regulation_macro": 10,
    "macro": 10,
    "whale_position": 10,
    "institutional_flow": 10,
    "hack_security": 8,
    "exchange_listing": 8,
    "token_supply": 8,
    "token_unlock": 8,
    "network_upgrade": 8,
    "halving": 5,
    "staking_governance": 5,
    "onchain_data": 8,
    "stablecoin_flow": 5,
    "project_business": 5,
    "legal_enforcement": 5,
    "market_structure": 3,
    "other_review": 0,
    "other": 0,
}

PREFERRED_TYPES = [
    "whale_position",
    "hack_security",
    "institutional_flow",
    "onchain_data",
    "token_supply",
    "network_upgrade",
    "exchange_listing",
    "stablecoin_flow",
    "staking_governance",
    "legal_enforcement",
    "project_business",
    "regulation_macro",
    "market_structure",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a non-destructive v0.6-filtered mature sample preview for backtest planning."
    )
    parser.add_argument(
        "--mature-input",
        default=str(ROOT / "data" / "event_candidates_real_500_older_mature_review_suggested.csv"),
    )
    parser.add_argument(
        "--v06-scored",
        default=str(ROOT / "data" / "event_candidates_v06_relevance_scored.csv"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "event_candidates_v06_filtered_mature_review_auto50_preview.csv"),
    )
    parser.add_argument(
        "--summary",
        default=str(ROOT / "results" / "v06_filtered_mature_sample_preview_summary.csv"),
    )
    parser.add_argument(
        "--report",
        default=str(ROOT / "results" / "v06_filtered_mature_sample_preview.md"),
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


def has_binance_symbol(row: pd.Series) -> bool:
    return bool(str(row.get("effective_binance_spot_symbol", "") or row.get("candidate_binance_spot_symbol", "")).strip()) or bool(
        str(row.get("effective_binance_futures_symbol", "") or row.get("candidate_binance_futures_symbol", "")).strip()
    )


def eligible(row: pd.Series) -> bool:
    if str(row.get("is_mature_72h", "")).strip().lower() != "true":
        return False
    if str(row.get("publish_decision", "")).strip() != "human_review":
        return False
    if str(row.get("effective_asset_symbol", "") or row.get("candidate_asset_symbol", "")).strip() == "":
        return False
    if not has_binance_symbol(row):
        return False
    if str(row.get("backtest_time_utc", "")).strip() == "":
        return False
    if str(row.get("time_parse_status", "")).strip() == "failed":
        return False
    event_type = str(row.get("event_type_l1", "")).strip() or str(row.get("candidate_event_type", "")).strip()
    if TYPE_CAPS.get(event_type, 5) <= 0:
        return False
    return True


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(-9999)


def selected_type_count(parts: list[pd.DataFrame], event_type: str) -> int:
    total = 0
    for part in parts:
        if "v06_stratify_type" in part.columns:
            total += int(part["v06_stratify_type"].eq(event_type).sum())
    return total


def render_report(summary: pd.DataFrame, selected: pd.DataFrame, limit: int) -> str:
    total = summary[summary["event_type"].eq("TOTAL")].iloc[0].to_dict() if not summary.empty else {}
    lines = [
        "# v0.6-Filtered Mature Sample Preview",
        "",
        f"selected_count: {total.get('selected_count', 0)}",
        f"eligible_count: {total.get('eligible_count', 0)}",
        f"limit: {limit}",
        "",
        "## Interpretation",
        "",
        "- This is a preview only. It does not overwrite v043 outputs.",
        "- It uses v0.6 `publish_decision=human_review` as an additional quality filter.",
        "- It is meant to estimate whether a cleaner backtest sample is available before changing the main pipeline.",
        "",
        "## By v0.6 Event Type",
        "",
        "| event_type | selected | eligible | cap |",
        "|---|---:|---:|---:|",
    ]
    for _, row in summary[~summary["event_type"].eq("TOTAL")].iterrows():
        lines.append(f"| {row['event_type']} | {row['selected_count']} | {row['eligible_count']} | {row['type_cap']} |")

    lines.extend(["", "## Selected Preview", "", "| candidate_id | event_type | asset | route | title |", "|---|---|---|---|---|"])
    if selected.empty:
        lines.append("| none |  |  |  |  |")
    else:
        for _, row in selected.head(30).iterrows():
            title = str(row.get("title", "")).replace("|", "/").replace("\n", " ")[:120]
            lines.append(
                f"| {row.get('candidate_id', '')} | {row.get('v06_stratify_type', '')} | {row.get('effective_asset_symbol', '') or row.get('candidate_asset_symbol', '')} | {row.get('channel_route', '')} | {title} |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    mature_path = normalize_path(args.mature_input)
    scored_path = normalize_path(args.v06_scored)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    report_path = normalize_path(args.report)

    mature = read_csv(mature_path)
    scored = read_csv(scored_path)
    if mature.empty:
        print(f"mature input missing or empty: {mature_path}")
        return 1
    if scored.empty:
        print(f"v06 scored input missing or empty: {scored_path}")
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
        "tradability_tier",
        "primary_asset_symbol",
        "primary_binance_spot_symbol",
        "primary_binance_futures_symbol",
        "effective_asset_symbol",
        "effective_binance_spot_symbol",
        "effective_binance_futures_symbol",
    ]
    available_cols = [col for col in v06_cols if col in scored.columns]
    merged = mature.merge(scored[available_cols], on="candidate_id", how="left", suffixes=("", "_v06"))
    merged["v06_stratify_type"] = merged.get("event_type_l1", "").replace("", pd.NA).fillna(merged.get("candidate_event_type", ""))
    merged["eligible_v06_filtered"] = [eligible(row) for _, row in merged.iterrows()]
    if "relevance_score_realtime" in merged.columns:
        merged["_relevance"] = numeric(merged["relevance_score_realtime"])
    else:
        merged["_relevance"] = -9999
    if "auto_quality_score" in merged.columns:
        merged["_quality"] = numeric(merged["auto_quality_score"])
    else:
        merged["_quality"] = -9999
    if "event_age_hours" in merged.columns:
        merged["_age"] = numeric(merged["event_age_hours"])
    else:
        merged["_age"] = -9999

    pool = merged[merged["eligible_v06_filtered"]].copy()
    pool = pool.sort_values(["_relevance", "_quality", "_age"], ascending=[False, False, False])

    selected_parts: list[pd.DataFrame] = []
    selected_ids: set[str] = set()

    for event_type in PREFERRED_TYPES:
        group = pool[pool["v06_stratify_type"].eq(event_type) & ~pool["candidate_id"].isin(selected_ids)]
        if not group.empty and len(selected_ids) < args.limit:
            chosen = group.head(1)
            selected_parts.append(chosen)
            selected_ids.update(chosen["candidate_id"].astype(str).tolist())

    for _, row in pool[~pool["candidate_id"].isin(selected_ids)].iterrows():
        if len(selected_ids) >= args.limit:
            break
        event_type = str(row.get("v06_stratify_type", ""))
        cap = TYPE_CAPS.get(event_type, 5)
        if selected_type_count(selected_parts, event_type) >= cap:
            continue
        selected_parts.append(pd.DataFrame([row]))
        selected_ids.add(str(row["candidate_id"]))

    selected = pd.concat(selected_parts, ignore_index=True) if selected_parts else pool.head(0).copy()
    selected = selected.head(args.limit).drop(columns=["_relevance", "_quality", "_age"], errors="ignore")
    if "effective_asset_symbol" in selected.columns:
        effective_asset = selected["effective_asset_symbol"].astype(str).str.strip()
        mask = effective_asset.ne("")
        selected.loc[mask, "candidate_asset_symbol"] = effective_asset[mask]
        for target, source in [
            ("candidate_binance_spot_symbol", "effective_binance_spot_symbol"),
            ("candidate_binance_futures_symbol", "effective_binance_futures_symbol"),
        ]:
            if source in selected.columns:
                selected.loc[mask, target] = selected.loc[mask, source].astype(str).str.strip()
    selected["review_decision"] = "include"
    selected["v06_filtered_preview"] = "true"

    rows = [
        {
            "event_type": "TOTAL",
            "selected_count": int(len(selected)),
            "eligible_count": int(len(pool)),
            "type_cap": "",
            "limit": args.limit,
        }
    ]
    for event_type in sorted(set(merged["v06_stratify_type"].astype(str))):
        if TYPE_CAPS.get(event_type, 5) <= 0:
            continue
        rows.append(
            {
                "event_type": event_type,
                "selected_count": int(selected["v06_stratify_type"].eq(event_type).sum()) if not selected.empty else 0,
                "eligible_count": int(pool["v06_stratify_type"].eq(event_type).sum()) if not pool.empty else 0,
                "type_cap": TYPE_CAPS.get(event_type, 5),
                "limit": args.limit,
            }
        )
    summary = pd.DataFrame(rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(output_path, index=False)
    summary.to_csv(summary_path, index=False)
    report_path.write_text(render_report(summary, selected, args.limit), encoding="utf-8")
    print(f"selected_count={len(selected)}")
    print(f"eligible_count={len(pool)}")
    print(f"wrote preview sample to {output_path}")
    print(f"wrote summary to {summary_path}")
    print(f"wrote report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
