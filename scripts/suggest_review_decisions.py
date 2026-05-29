import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Suggest review decisions for event candidates.")
    parser.add_argument("--input", default=str(ROOT / "data" / "event_candidates_real_200_review.csv"))
    parser.add_argument(
        "--output", default=str(ROOT / "data" / "event_candidates_real_200_review_suggested.csv")
    )
    parser.add_argument("--summary", default=str(ROOT / "results" / "v041_review_suggestion_summary.csv"))
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def truthy_number(value, default=0) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def flags(row: pd.Series) -> List[str]:
    return [part.strip() for part in str(row.get("quality_flags", "")).split(",") if part.strip()]


def score_candidate(row: pd.Series) -> Tuple[int, str]:
    score = 0
    reasons: List[str] = []
    quality_flags = flags(row)
    asset = str(row.get("candidate_asset_symbol", "")).strip()
    spot = str(row.get("candidate_binance_spot_symbol", "")).strip()
    futures = str(row.get("candidate_binance_futures_symbol", "")).strip()
    event_type = str(row.get("candidate_event_type", "")).strip()
    scope = str(row.get("event_scope", "")).strip()
    asset_confidence = str(row.get("asset_confidence", "")).strip()
    time_confidence = str(row.get("time_confidence", "")).strip()
    time_status = str(row.get("time_parse_status", "")).strip()
    title = str(row.get("title", "")).strip()
    content = str(row.get("content", "")).strip()

    if asset:
        score += 25
        reasons.append("has_asset")
    else:
        score -= 40
        reasons.append("missing_asset")

    if spot or futures:
        score += 20
        reasons.append("has_binance_symbol")
    else:
        score -= 25
        reasons.append("missing_symbol")

    if time_status == "ok":
        score += 20
        reasons.append("time_ok")

    if event_type != "other":
        score += 20
        reasons.append("typed_event")
    else:
        score -= 20
        reasons.append("unknown_event_type")

    if scope == "single_asset":
        score += 15
        reasons.append("single_asset")
    elif scope == "multi_asset":
        score -= 20
        reasons.append("multi_asset")
    elif scope == "unknown":
        score -= 30
        reasons.append("unknown_scope")

    if asset_confidence == "high":
        score += 10
        reasons.append("asset_confidence_high")

    if time_confidence == "high":
        score += 10
        reasons.append("time_confidence_high")

    if truthy_number(row.get("candidate_importance", ""), 0) >= 4:
        score += 10
        reasons.append("importance_ge_4")

    if "missing_asset" in quality_flags:
        score -= 40
        reasons.append("flag_missing_asset")
    if "time_parse_failed" in quality_flags:
        score -= 100
        reasons.append("flag_time_parse_failed")

    if len(title + content) < 20:
        score -= 20
        reasons.append("too_short")

    return score, ",".join(reasons)


def decision_from_score(score: int) -> str:
    if score >= 70:
        return "include"
    if score >= 40:
        return "fix"
    return "exclude"


def priority_from_score(score: int) -> str:
    if score >= 85:
        return "high"
    if score >= 70:
        return "medium"
    if score >= 40:
        return "low"
    return "drop"


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    quality_flags = df.get("quality_flags", pd.Series("", index=df.index)).fillna("").astype(str)
    row = {
        "total": int(len(df)),
        "suggest_include_count": int((df["suggested_review_decision"] == "include").sum()),
        "suggest_fix_count": int((df["suggested_review_decision"] == "fix").sum()),
        "suggest_exclude_count": int((df["suggested_review_decision"] == "exclude").sum()),
        "high_priority_count": int((df["review_priority"] == "high").sum()),
        "medium_priority_count": int((df["review_priority"] == "medium").sum()),
        "low_priority_count": int((df["review_priority"] == "low").sum()),
        "drop_count": int((df["review_priority"] == "drop").sum()),
        "missing_asset_count": int(quality_flags.str.contains(r"(?:^|,)missing_asset(?:,|$)", regex=True).sum()),
        "missing_symbol_count": int(
            (
                (df.get("candidate_binance_spot_symbol", pd.Series("", index=df.index)).fillna("").astype(str).str.strip() == "")
                & (df.get("candidate_binance_futures_symbol", pd.Series("", index=df.index)).fillna("").astype(str).str.strip() == "")
            ).sum()
        ),
        "unknown_event_type_count": int((df.get("candidate_event_type", "") == "other").sum()),
        "multi_asset_count": int((df.get("event_scope", "") == "multi_asset").sum()),
        "market_wide_count": int((df.get("event_scope", "") == "market_wide").sum()),
    }
    return pd.DataFrame([row])


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
    scores = df.apply(score_candidate, axis=1)
    df["auto_quality_score"] = [score for score, _reason in scores]
    df["suggested_reason"] = [reason for _score, reason in scores]
    df["suggested_review_decision"] = df["auto_quality_score"].apply(decision_from_score)
    df["review_priority"] = df["auto_quality_score"].apply(priority_from_score)

    ensure_parent(output_path)
    df.to_csv(output_path, index=False)

    summary = build_summary(df)
    ensure_parent(summary_path)
    summary.to_csv(summary_path, index=False)
    logging.info("wrote suggested review file to %s", output_path)
    logging.info("wrote summary to %s", summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
