import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill remaining unlabeled rows with suggested labels while forcing manual_review_required=true."
    )
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_auto_fill_unlabeled_summary.csv"))
    parser.add_argument("--audit-output", default=str(ROOT / "data" / "v06_auto_fill_unlabeled_audit_sample.csv"))
    parser.add_argument("--audit-size", type=int, default=20)
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def as_str(value: object) -> str:
    return str(value if value is not None else "").strip()


def append_note(existing: object, note: str) -> str:
    base = as_str(existing)
    return note if not base else f"{base} | {note}"


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    audit_output = normalize_path(args.audit_output)

    if not input_path.exists():
        logging.error("input not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    required_cols = [
        "manual_decision",
        "manual_event_type_l1",
        "manual_event_type_l2",
        "manual_primary_asset_symbol",
        "manual_channel_route",
        "manual_useful_for_research",
        "manual_notes",
        "manual_review_required",
        "label_origin",
        "suggested_manual_decision",
        "suggested_manual_event_type_l1",
        "suggested_manual_event_type_l2",
        "suggested_manual_primary_asset_symbol",
        "suggested_manual_channel_route",
        "suggested_manual_useful_for_research",
        "auto_label_confidence",
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    unlabeled = df["manual_decision"].astype(str).str.strip().eq("")
    has_suggestion = df["suggested_manual_decision"].astype(str).str.strip().ne("")
    candidate_mask = unlabeled & has_suggestion
    candidates = df[candidate_mask].copy()

    filled_count = 0
    for idx, row in candidates.iterrows():
        decision = as_str(row.get("suggested_manual_decision", ""))
        if not decision:
            continue
        df.at[idx, "manual_decision"] = decision
        df.at[idx, "manual_event_type_l1"] = as_str(row.get("suggested_manual_event_type_l1", ""))
        df.at[idx, "manual_event_type_l2"] = as_str(row.get("suggested_manual_event_type_l2", ""))
        df.at[idx, "manual_primary_asset_symbol"] = as_str(row.get("suggested_manual_primary_asset_symbol", ""))
        df.at[idx, "manual_channel_route"] = as_str(row.get("suggested_manual_channel_route", ""))
        df.at[idx, "manual_useful_for_research"] = as_str(row.get("suggested_manual_useful_for_research", ""))
        conf = as_str(row.get("auto_label_confidence", ""))
        note = f"auto_fill_unlabeled(conf={conf or 'n/a'})"
        df.at[idx, "manual_notes"] = append_note(row.get("manual_notes", ""), note)
        df.at[idx, "manual_review_required"] = "true"
        df.at[idx, "label_origin"] = "auto_medium_conf_review_required"
        filled_count += 1

    audit_df = candidates.sort_values(by=["candidate_id"], kind="mergesort").head(max(1, args.audit_size)).copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    audit_df.to_csv(audit_output, index=False)

    unlabeled_after = int(df["manual_decision"].astype(str).str.strip().eq("").sum())
    pd.DataFrame(
        [
            {
                "total_rows": int(len(df)),
                "candidates_unlabeled_with_suggestion": int(len(candidates)),
                "auto_filled_rows_in_run": int(filled_count),
                "unlabeled_rows_after_run": unlabeled_after,
                "audit_sample_rows": int(len(audit_df)),
            }
        ]
    ).to_csv(summary_path, index=False)

    logging.info("wrote updated sheet to %s", output_path)
    logging.info("wrote summary to %s", summary_path)
    logging.info("wrote audit sample to %s", audit_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
