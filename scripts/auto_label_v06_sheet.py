import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

MANUAL_COLUMNS = [
    "manual_decision",
    "manual_event_type_l1",
    "manual_event_type_l2",
    "manual_primary_asset_symbol",
    "manual_channel_route",
    "manual_useful_for_research",
    "manual_notes",
]

SUGGESTION_COLUMNS = [
    "suggested_manual_decision",
    "suggested_manual_event_type_l1",
    "suggested_manual_event_type_l2",
    "suggested_manual_primary_asset_symbol",
    "suggested_manual_channel_route",
    "suggested_manual_useful_for_research",
    "auto_label_confidence",
    "auto_label_reasons",
    "auto_label_apply",
    "auto_prefilled",
    "manual_review_required",
    "label_origin",
]

HIGH_CONFIDENCE = 0.9


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI-assisted pre-label for v0.6 manual sheet. Adds suggested labels and optionally fills high-confidence rows."
    )
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_auto_label_summary.csv"))
    parser.add_argument("--apply-high-confidence", action="store_true")
    parser.add_argument("--min-confidence", type=float, default=HIGH_CONFIDENCE)
    parser.add_argument("--apply-provisional", action="store_true", help="Fill remaining unlabeled rows with provisional labels above threshold.")
    parser.add_argument("--provisional-min-confidence", type=float, default=0.75)
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def as_str(value: object) -> str:
    return str(value if value is not None else "").strip()


def lower(value: object) -> str:
    return as_str(value).lower()


def is_blank(value: object) -> bool:
    return as_str(value) == ""


def suggest_decision(row: pd.Series) -> tuple[str, float, list[str]]:
    score = 0.45
    reasons: list[str] = []
    route = lower(row.get("channel_route", ""))
    event_l1 = lower(row.get("event_type_l1", ""))
    event_scope = lower(row.get("event_scope", ""))
    publish_decision = lower(row.get("publish_decision", ""))
    asset = as_str(row.get("primary_asset_symbol", "") or row.get("candidate_asset_symbol", ""))
    flags = lower(row.get("relevance_flags", ""))
    discard_reason = lower(row.get("discard_reason", ""))
    source = lower(row.get("label_source", ""))
    relevance_score = pd.to_numeric(row.get("relevance_score_realtime", ""), errors="coerce")

    if publish_decision == "discard":
        score += 0.35
        reasons.append("publish_decision=discard")
    elif publish_decision == "human_review":
        score += 0.2
        reasons.append("publish_decision=human_review")

    if route in {"alpha_candidate", "macro_policy"}:
        score += 0.2
        reasons.append(f"channel_route={route}")
    elif route in {"unsupported_research", "research_only"}:
        score += 0.1
        reasons.append(f"channel_route={route}")

    if event_l1 and event_l1 != "other":
        score += 0.15
        reasons.append("event_type_l1_specific")
    elif event_l1 == "other":
        score -= 0.1
        reasons.append("event_type_l1=other")

    if event_scope == "single_asset":
        score += 0.1
        reasons.append("single_asset_scope")
    elif event_scope in {"multi_asset", "unknown"}:
        score -= 0.1
        reasons.append(f"event_scope={event_scope}")

    if asset:
        score += 0.1
        reasons.append("asset_present")
    else:
        score -= 0.2
        reasons.append("asset_missing")

    if pd.notna(relevance_score):
        if relevance_score >= 80:
            score += 0.1
            reasons.append("relevance_score>=80")
        elif relevance_score < 60:
            score -= 0.1
            reasons.append("relevance_score<60")

    if "missing_asset" in flags or "unsupported_asset" in discard_reason:
        score -= 0.2
        reasons.append("asset_quality_risk")

    if source == "other_review":
        score -= 0.05
        reasons.append("other_review_source")

    score = max(0.0, min(1.0, round(score, 2)))

    if publish_decision == "discard":
        decision = "discard"
    elif event_l1 == "other":
        decision = "fix_taxonomy"
    elif route in {"alpha_candidate", "macro_policy"}:
        decision = "approve_publish"
    else:
        decision = "keep_review"
    return decision, score, reasons


def suggest_useful(decision: str) -> str:
    return "no" if decision == "discard" else "yes"


def suggest_row(row: pd.Series) -> dict:
    decision, confidence, reasons = suggest_decision(row)
    event_l1 = as_str(row.get("event_type_l1", ""))
    event_l2 = as_str(row.get("event_type_l2", ""))
    asset = as_str(row.get("primary_asset_symbol", "") or row.get("candidate_asset_symbol", ""))
    channel_route = as_str(row.get("channel_route", ""))

    risk_reasons = {"event_scope=multi_asset", "event_scope=unknown", "event_type_l1=other", "asset_missing"}
    allow_apply = confidence >= HIGH_CONFIDENCE and not any(reason in risk_reasons for reason in reasons)

    return {
        "suggested_manual_decision": decision,
        "suggested_manual_event_type_l1": event_l1,
        "suggested_manual_event_type_l2": event_l2,
        "suggested_manual_primary_asset_symbol": asset,
        "suggested_manual_channel_route": channel_route,
        "suggested_manual_useful_for_research": suggest_useful(decision),
        "auto_label_confidence": confidence,
        "auto_label_reasons": ",".join(reasons),
        "auto_label_apply": "true" if allow_apply else "false",
    }


def apply_prefill(df: pd.DataFrame, min_confidence: float) -> tuple[pd.DataFrame, int]:
    updated = df.copy()
    prefilled_count = 0

    for idx, row in updated.iterrows():
        if lower(row.get("auto_label_apply", "")) != "true":
            continue
        confidence = pd.to_numeric(row.get("auto_label_confidence", ""), errors="coerce")
        if pd.isna(confidence) or confidence < min_confidence:
            continue
        if not is_blank(row.get("manual_decision", "")):
            continue

        updated.at[idx, "manual_decision"] = as_str(row.get("suggested_manual_decision", ""))
        updated.at[idx, "manual_event_type_l1"] = as_str(row.get("suggested_manual_event_type_l1", ""))
        updated.at[idx, "manual_event_type_l2"] = as_str(row.get("suggested_manual_event_type_l2", ""))
        updated.at[idx, "manual_primary_asset_symbol"] = as_str(row.get("suggested_manual_primary_asset_symbol", ""))
        updated.at[idx, "manual_channel_route"] = as_str(row.get("suggested_manual_channel_route", ""))
        updated.at[idx, "manual_useful_for_research"] = as_str(row.get("suggested_manual_useful_for_research", ""))
        existing_note = as_str(row.get("manual_notes", ""))
        auto_note = f"auto_prefill(conf={confidence:.2f})"
        updated.at[idx, "manual_notes"] = auto_note if not existing_note else f"{existing_note} | {auto_note}"
        updated.at[idx, "auto_prefilled"] = "true"
        updated.at[idx, "manual_review_required"] = "false"
        updated.at[idx, "label_origin"] = "auto_high_confidence"
        prefilled_count += 1

    return updated, prefilled_count


def apply_provisional_prefill(df: pd.DataFrame, min_confidence: float) -> tuple[pd.DataFrame, int]:
    updated = df.copy()
    provisional_count = 0

    for idx, row in updated.iterrows():
        if not is_blank(row.get("manual_decision", "")):
            continue
        confidence = pd.to_numeric(row.get("auto_label_confidence", ""), errors="coerce")
        if pd.isna(confidence) or confidence < min_confidence:
            continue

        updated.at[idx, "manual_decision"] = as_str(row.get("suggested_manual_decision", ""))
        updated.at[idx, "manual_event_type_l1"] = as_str(row.get("suggested_manual_event_type_l1", ""))
        updated.at[idx, "manual_event_type_l2"] = as_str(row.get("suggested_manual_event_type_l2", ""))
        updated.at[idx, "manual_primary_asset_symbol"] = as_str(row.get("suggested_manual_primary_asset_symbol", ""))
        updated.at[idx, "manual_channel_route"] = as_str(row.get("suggested_manual_channel_route", ""))
        updated.at[idx, "manual_useful_for_research"] = as_str(row.get("suggested_manual_useful_for_research", ""))
        existing_note = as_str(row.get("manual_notes", ""))
        auto_note = f"auto_provisional(conf={confidence:.2f})"
        updated.at[idx, "manual_notes"] = auto_note if not existing_note else f"{existing_note} | {auto_note}"
        updated.at[idx, "manual_review_required"] = "true"
        updated.at[idx, "label_origin"] = "auto_provisional"
        provisional_count += 1
    return updated, provisional_count


def build_summary(df: pd.DataFrame, prefilled_count: int, provisional_count: int) -> pd.DataFrame:
    confidence = pd.to_numeric(df.get("auto_label_confidence", pd.Series([], dtype=float)), errors="coerce")
    apply_mask = df.get("auto_label_apply", pd.Series("", index=df.index)).astype(str).str.lower() == "true"
    labeled_mask = df.get("manual_decision", pd.Series("", index=df.index)).astype(str).str.strip() != ""
    review_required_mask = df.get("manual_review_required", pd.Series("", index=df.index)).astype(str).str.lower() == "true"
    return pd.DataFrame(
        [
            {
                "total_rows": int(len(df)),
                "suggest_ready_rows": int(apply_mask.sum()),
                "avg_auto_label_confidence": round(float(confidence.mean()), 4) if not confidence.dropna().empty else "",
                "auto_prefilled_rows_in_run": int(prefilled_count),
                "auto_provisional_rows_in_run": int(provisional_count),
                "manual_labeled_rows_after_run": int(labeled_mask.sum()),
                "manual_unlabeled_rows_after_run": int((~labeled_mask).sum()),
                "manual_review_required_rows_after_run": int(review_required_mask.sum()),
                "suggest_decision_approve_publish": int((df["suggested_manual_decision"] == "approve_publish").sum()) if "suggested_manual_decision" in df.columns else 0,
                "suggest_decision_keep_review": int((df["suggested_manual_decision"] == "keep_review").sum()) if "suggested_manual_decision" in df.columns else 0,
                "suggest_decision_fix_taxonomy": int((df["suggested_manual_decision"] == "fix_taxonomy").sum()) if "suggested_manual_decision" in df.columns else 0,
                "suggest_decision_discard": int((df["suggested_manual_decision"] == "discard").sum()) if "suggested_manual_decision" in df.columns else 0,
            }
        ]
    )


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            df[column] = ""
    return df


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    if not input_path.exists():
        logging.error("input not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    df = ensure_columns(df, MANUAL_COLUMNS + SUGGESTION_COLUMNS)

    suggested_rows = [suggest_row(row) for _, row in df.iterrows()]
    suggested_df = pd.DataFrame(suggested_rows)
    for column in suggested_df.columns:
        df[column] = suggested_df[column]

    prefilled_count = 0
    provisional_count = 0
    if args.apply_high_confidence:
        df, prefilled_count = apply_prefill(df, args.min_confidence)
    else:
        df["auto_prefilled"] = "false"
    if "manual_review_required" not in df.columns:
        df["manual_review_required"] = ""
    if "label_origin" not in df.columns:
        df["label_origin"] = ""

    if args.apply_provisional:
        df, provisional_count = apply_provisional_prefill(df, args.provisional_min_confidence)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    build_summary(df, prefilled_count, provisional_count).to_csv(summary_path, index=False)
    logging.info("wrote suggested label sheet to %s", output_path)
    logging.info("wrote summary to %s", summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
