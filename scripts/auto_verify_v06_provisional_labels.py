import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Conservatively auto-verify provisional labels and emit a mandatory audit sample."
    )
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_auto_verify_summary.csv"))
    parser.add_argument("--audit-output", default=str(ROOT / "data" / "v06_auto_verify_audit_sample.csv"))
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


def should_auto_verify(row: pd.Series) -> tuple[bool, str]:
    decision = lower(row.get("manual_decision", ""))
    event_scope = lower(row.get("event_scope", ""))
    event_type = lower(row.get("manual_event_type_l1", "") or row.get("event_type_l1", ""))
    route = lower(row.get("manual_channel_route", "") or row.get("channel_route", ""))
    confidence = to_num(row.get("auto_label_confidence", ""))
    relevance = to_num(row.get("relevance_score_realtime", ""))
    flags = lower(row.get("relevance_flags", ""))
    asset = as_str(row.get("manual_primary_asset_symbol", "") or row.get("primary_asset_symbol", "") or row.get("candidate_asset_symbol", ""))

    # Case A: low-value discard style rows (safe for auto confirmation)
    if (
        decision == "discard"
        and confidence >= 0.85
        and relevance <= 70
        and event_scope in {"unknown", "multi_asset"}
        and (not asset or "missing_asset" in flags)
    ):
        return True, "discard_low_relevance_missing_asset"

    # Case B: strong single-asset publish-review style rows (still conservative)
    if (
        decision in {"approve_publish", "keep_review"}
        and confidence >= 0.95
        and event_scope == "single_asset"
        and asset
        and event_type not in {"other", ""}
        and route in {"alpha_candidate", "macro_policy", "unsupported_research", "research_only"}
    ):
        return True, "single_asset_high_confidence"

    return False, ""


def sample_audit(df: pd.DataFrame, size: int) -> pd.DataFrame:
    provisional = df[df["label_origin"].astype(str).str.lower() == "auto_provisional"].copy()
    if provisional.empty:
        return provisional.head(0)
    # deterministic ordering for reproducibility
    provisional = provisional.sort_values(by=["candidate_id"], kind="mergesort")
    return provisional.head(max(1, size)).copy()


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
    for col in ["manual_review_required", "label_origin", "manual_notes"]:
        if col not in df.columns:
            df[col] = ""

    provisional_mask = df["label_origin"].astype(str).str.lower() == "auto_provisional"
    provisional = df[provisional_mask].copy()
    auto_verified_count = 0

    for idx, row in provisional.iterrows():
        ok, reason = should_auto_verify(row)
        if not ok:
            continue
        existing_note = as_str(df.at[idx, "manual_notes"])
        tag = f"auto_verified({reason})"
        df.at[idx, "manual_notes"] = tag if not existing_note else f"{existing_note} | {tag}"
        df.at[idx, "manual_review_required"] = "false"
        df.at[idx, "label_origin"] = "auto_verified"
        auto_verified_count += 1

    audit_df = sample_audit(df, args.audit_size)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    audit_df.to_csv(audit_output, index=False)

    remaining_provisional = int((df["label_origin"].astype(str).str.lower() == "auto_provisional").sum())
    pd.DataFrame(
        [
            {
                "total_rows": int(len(df)),
                "provisional_before": int(len(provisional)),
                "auto_verified_rows_in_run": int(auto_verified_count),
                "provisional_remaining_after_run": remaining_provisional,
                "audit_sample_rows": int(len(audit_df)),
            }
        ]
    ).to_csv(summary_path, index=False)

    logging.info("wrote updated sheet to %s", output_path)
    logging.info("wrote auto-verify summary to %s", summary_path)
    logging.info("wrote audit sample to %s", audit_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
