import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-close low-risk unlabeled rows (mostly other_review discard) with audit sampling."
    )
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_auto_close_summary.csv"))
    parser.add_argument("--audit-output", default=str(ROOT / "data" / "v06_auto_close_audit_sample.csv"))
    parser.add_argument("--audit-size", type=int, default=20)
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


def to_num(value: object, default: float = 0.0) -> float:
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        return default
    return float(num)


def low_risk_mask(df: pd.DataFrame) -> pd.Series:
    manual_blank = df["manual_decision"].astype(str).str.strip() == ""
    source_ok = df["label_source"].astype(str).str.lower().eq("other_review")
    publish_discard = df["publish_decision"].astype(str).str.lower().eq("discard")
    event_other = df["event_type_l1"].astype(str).str.lower().isin({"other_review", "other"})
    route_ok = df["channel_route"].astype(str).str.lower().eq("research_only")
    scope_unknown = df["event_scope"].astype(str).str.lower().eq("unknown")
    conf_low = pd.to_numeric(df.get("auto_label_confidence", ""), errors="coerce").fillna(0).le(0.70)
    score_low = pd.to_numeric(df.get("relevance_score_realtime", ""), errors="coerce").fillna(0).le(62)
    return manual_blank & source_ok & publish_discard & event_other & route_ok & scope_unknown & conf_low & score_low


def add_note(existing: str, tag: str) -> str:
    existing = as_str(existing)
    return tag if not existing else f"{existing} | {tag}"


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
    for col in ["manual_decision", "manual_event_type_l1", "manual_event_type_l2", "manual_primary_asset_symbol", "manual_channel_route", "manual_useful_for_research", "manual_notes", "manual_review_required", "label_origin"]:
        if col not in df.columns:
            df[col] = ""

    mask = low_risk_mask(df)
    selected = df[mask].copy()
    changed = 0
    for idx, row in selected.iterrows():
        df.at[idx, "manual_decision"] = "discard"
        df.at[idx, "manual_event_type_l1"] = as_str(row.get("event_type_l1", "")) or "other_review"
        df.at[idx, "manual_event_type_l2"] = as_str(row.get("event_type_l2", ""))
        df.at[idx, "manual_primary_asset_symbol"] = as_str(row.get("primary_asset_symbol", "") or row.get("candidate_asset_symbol", ""))
        df.at[idx, "manual_channel_route"] = as_str(row.get("channel_route", ""))
        df.at[idx, "manual_useful_for_research"] = "no"
        df.at[idx, "manual_review_required"] = "false"
        df.at[idx, "label_origin"] = "auto_closed_low_risk"
        df.at[idx, "manual_notes"] = add_note(row.get("manual_notes", ""), f"auto_closed_low_risk(conf={to_num(row.get('auto_label_confidence', ''), 0):.2f})")
        changed += 1

    audit_df = selected.sort_values(by=["candidate_id"], kind="mergesort").head(max(1, args.audit_size)).copy()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    audit_df.to_csv(audit_output, index=False)
    pd.DataFrame(
        [
            {
                "total_rows": int(len(df)),
                "selected_low_risk_rows": int(len(selected)),
                "auto_closed_rows_in_run": int(changed),
                "audit_sample_rows": int(len(audit_df)),
            }
        ]
    ).to_csv(summary_path, index=False)
    logging.info("wrote updated sheet to %s", output_path)
    logging.info("wrote auto-close summary to %s", summary_path)
    logging.info("wrote auto-close audit sample to %s", audit_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
