import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the next minimal-manual labeling batch from v0.6 label sheet.")
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_label_batch.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_labeling_batch_summary.csv"))
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--review-required-quota", type=int, default=10)
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


def series_or_blank(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column].fillna("")
    return pd.Series([""] * len(df), index=df.index)


def add_priority_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["manual_filled"] = series_or_blank(out, "manual_decision").astype(str).str.strip() != ""
    out["auto_apply"] = series_or_blank(out, "auto_label_apply").astype(str).str.lower() == "true"
    out["auto_conf"] = pd.to_numeric(series_or_blank(out, "auto_label_confidence"), errors="coerce").fillna(0.0)
    out["relevance_score"] = pd.to_numeric(series_or_blank(out, "relevance_score_realtime"), errors="coerce").fillna(0.0)
    out["event_scope_norm"] = series_or_blank(out, "event_scope").astype(str).str.lower()
    out["event_type_norm"] = series_or_blank(out, "event_type_l1").astype(str).str.lower()
    out["label_source_norm"] = series_or_blank(out, "label_source").astype(str).str.lower()
    out["review_required"] = series_or_blank(out, "manual_review_required").astype(str).str.lower() == "true"
    out["label_origin_norm"] = series_or_blank(out, "label_origin").astype(str).str.lower()
    out["asset_missing"] = (
        series_or_blank(out, "primary_asset_symbol").astype(str).str.strip().eq("")
        & series_or_blank(out, "candidate_asset_symbol").astype(str).str.strip().eq("")
    )

    # Higher score = should be reviewed first.
    priority = pd.Series(0, index=out.index, dtype=float)
    priority += (~out["auto_apply"]).astype(float) * 40
    priority += (out["auto_conf"] < 0.8).astype(float) * 20
    priority += out["event_scope_norm"].isin({"multi_asset", "unknown"}).astype(float) * 18
    priority += out["event_type_norm"].isin({"other", ""}).astype(float) * 15
    priority += (out["label_source_norm"] == "other_review").astype(float) * 10
    priority += out["asset_missing"].astype(float) * 20
    priority += out["review_required"].astype(float) * 16
    priority += (out["label_origin_norm"] == "auto_provisional").astype(float) * 10
    priority += (100 - out["relevance_score"].clip(0, 100)) * 0.05
    out["review_priority_score"] = priority.round(2)

    focus = []
    for _, row in out.iterrows():
        reasons = []
        if not row["auto_apply"]:
            reasons.append("no_auto_apply")
        if row["auto_conf"] < 0.8:
            reasons.append("low_confidence")
        if row["event_scope_norm"] in {"multi_asset", "unknown"}:
            reasons.append(row["event_scope_norm"])
        if row["event_type_norm"] in {"other", ""}:
            reasons.append("taxonomy_unclear")
        if row["asset_missing"]:
            reasons.append("missing_asset")
        if row["review_required"]:
            reasons.append("manual_review_required")
        if row["label_origin_norm"] == "auto_provisional":
            reasons.append("auto_provisional")
        focus.append(",".join(reasons) if reasons else "sanity_check")
    out["review_focus"] = focus
    return out


def build_summary(df: pd.DataFrame, batch: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "total_rows": int(len(df)),
                "manual_labeled_rows": int(df["manual_filled"].sum()),
                "manual_unlabeled_rows": int((~df["manual_filled"]).sum()),
                "auto_apply_rows": int(df["auto_apply"].sum()),
                "auto_apply_unlabeled_rows": int((df["auto_apply"] & ~df["manual_filled"]).sum()),
                "manual_review_required_rows": int(df["review_required"].sum()),
                "selected_batch_size": int(len(batch)),
                "selected_publish_review": int((batch["label_source_norm"] == "publish_review").sum()) if not batch.empty else 0,
                "selected_other_review": int((batch["label_source_norm"] == "other_review").sum()) if not batch.empty else 0,
                "selected_discard_audit": int((batch["label_source_norm"] == "discard_audit").sum()) if not batch.empty else 0,
                "selected_multi_or_unknown_scope": int(batch["event_scope_norm"].isin({"multi_asset", "unknown"}).sum()) if not batch.empty else 0,
                "selected_manual_review_required": int(batch["review_required"].sum()) if not batch.empty else 0,
            }
        ]
    )


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
    enriched = add_priority_features(df)
    review_pool = enriched[(~enriched["manual_filled"]) | (enriched["review_required"])].copy()
    review_pool = review_pool.sort_values(
        by=["review_priority_score", "auto_conf", "relevance_score"],
        ascending=[False, True, False],
        kind="mergesort",
    )
    batch_size = max(1, args.batch_size)
    quota = max(0, min(args.review_required_quota, batch_size))
    rr_pool = review_pool[review_pool["review_required"]].copy()
    rr_take = rr_pool.head(quota)
    selected_ids = set(rr_take.index.tolist())
    remainder = review_pool[~review_pool.index.isin(selected_ids)].head(max(0, batch_size - len(rr_take)))
    batch = pd.concat([rr_take, remainder], axis=0).head(batch_size).copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    batch.to_csv(output_path, index=False)
    build_summary(enriched, batch).to_csv(summary_path, index=False)
    logging.info("wrote next labeling batch (%s rows) to %s", len(batch), output_path)
    logging.info("wrote batch summary to %s", summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
