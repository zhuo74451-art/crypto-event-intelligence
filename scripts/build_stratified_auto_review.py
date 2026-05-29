import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PREFERRED_TYPES = [
    "whale_position",
    "institutional_flow",
    "token_unlock",
    "hack_security",
    "exchange_listing",
    "network_upgrade",
    "halving",
    "staking_governance",
    "macro",
    "other",
]
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
    parser = argparse.ArgumentParser(description="Build a stratified mature auto-review file.")
    parser.add_argument(
        "--input", default=str(ROOT / "data" / "event_candidates_real_mature_review_suggested.csv")
    )
    parser.add_argument(
        "--output", default=str(ROOT / "data" / "event_candidates_real_mature_review_auto50.csv")
    )
    parser.add_argument(
        "--summary", default=str(ROOT / "results" / "v042_stratified_selection_summary.csv")
    )
    parser.add_argument("--limit", type=int, default=50)
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def has_flag(row: pd.Series, flag: str) -> bool:
    return flag in [part.strip() for part in str(row.get("quality_flags", "")).split(",") if part.strip()]


def eligible(row: pd.Series) -> bool:
    if str(row.get("is_mature_72h", "")).strip().lower() != "true":
        return False
    if str(row.get("suggested_review_decision", "")).strip() not in {"include", "fix"}:
        return False
    if has_flag(row, "missing_asset") or has_flag(row, "time_parse_failed"):
        return False
    if str(row.get("candidate_asset_symbol", "")).strip() == "":
        return False
    if (
        str(row.get("candidate_binance_spot_symbol", "")).strip() == ""
        and str(row.get("candidate_binance_futures_symbol", "")).strip() == ""
    ):
        return False
    if str(row.get("backtest_time_utc", "")).strip() == "":
        return False
    score = float(row.get("auto_quality_score", 0) or 0)
    if str(row.get("event_scope", "")).strip() == "multi_asset" and score < 90:
        return False
    return True


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    if df.empty:
        selected = df.copy()
    else:
        df["auto_quality_score_num"] = pd.to_numeric(df["auto_quality_score"], errors="coerce").fillna(-9999)
        pool = df[df.apply(eligible, axis=1)].copy()
        pool = pool.sort_values(["auto_quality_score_num", "event_age_hours"], ascending=[False, False])
        selected_parts = []
        selected_ids = set()

        # First pass: take the strongest one from each non-macro type.
        for event_type in [t for t in PREFERRED_TYPES if t != "macro"]:
            group = pool[(pool["candidate_event_type"] == event_type) & (~pool["candidate_id"].isin(selected_ids))]
            if not group.empty and len(selected_ids) < args.limit:
                chosen = group.head(1)
                selected_parts.append(chosen)
                selected_ids.update(chosen["candidate_id"].tolist())

        # Second pass: fill by score while respecting macro cap.
        for _, row in pool[~pool["candidate_id"].isin(selected_ids)].iterrows():
            if len(selected_ids) >= args.limit:
                break
            event_type = row.get("candidate_event_type", "")
            current_type_count = sum(
                int((part["candidate_event_type"] == event_type).sum()) for part in selected_parts
            )
            if current_type_count >= TYPE_CAPS.get(event_type, 5):
                continue
            selected_parts.append(pd.DataFrame([row]))
            selected_ids.add(row["candidate_id"])

        selected = pd.concat(selected_parts, ignore_index=True) if selected_parts else pool.head(0).copy()

    selected = selected.head(args.limit).copy()
    selected["review_decision"] = "include"
    selected = selected.drop(columns=["auto_quality_score_num"], errors="ignore")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(output_path, index=False)

    rows = []
    if selected.empty:
        rows.append(
            {
                "event_type": "TOTAL",
                "selected_count": 0,
                "eligible_count": 0,
                "type_cap": "",
                "limit": args.limit,
            }
        )
    else:
        eligible_count = int(df[df.apply(eligible, axis=1)].shape[0]) if not df.empty else 0
        counts = selected["candidate_event_type"].value_counts().to_dict()
        rows.append(
            {
                "event_type": "TOTAL",
                "selected_count": len(selected),
                "eligible_count": eligible_count,
                "type_cap": "",
                "limit": args.limit,
            }
        )
        for event_type, count in sorted(counts.items()):
            rows.append(
                {
                    "event_type": event_type,
                    "selected_count": int(count),
                    "eligible_count": int(((df["candidate_event_type"] == event_type) & df.apply(eligible, axis=1)).sum()),
                    "type_cap": TYPE_CAPS.get(event_type, 5),
                    "limit": args.limit,
                }
            )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(summary_path, index=False)
    print(f"selected_count={len(selected)}")
    logging.info("wrote stratified auto review to %s", output_path)
    logging.info("wrote selection summary to %s", summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
