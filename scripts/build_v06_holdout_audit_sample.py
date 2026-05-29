import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a deterministic v0.6 holdout/audit sample.")
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_holdout_audit_sample.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_holdout_audit_sample_summary.csv"))
    parser.add_argument("--size", type=int, default=100)
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)

    if not input_path.exists():
        print(f"input not found: {input_path}")
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    if df.empty:
        sample = df
    else:
        required = df[df.get("manual_review_required", "").astype(str).str.lower().eq("true")].copy()
        rest = df[~df.index.isin(required.index)].copy()
        sort_cols = [col for col in ["manual_decision", "manual_event_type_l1", "candidate_id"] if col in df.columns]
        if sort_cols:
            required = required.sort_values(sort_cols, kind="mergesort")
            rest = rest.sort_values(sort_cols, kind="mergesort")
        sample = pd.concat([required, rest], ignore_index=True).head(max(1, args.size))
    sample = sample.copy()
    sample["holdout_audit_required"] = "true"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(output_path, index=False)
    pd.DataFrame(
        [
            {
                "sample_rows": int(len(sample)),
                "target_rows": int(args.size),
                "manual_review_required_rows_in_sample": int(
                    sample.get("manual_review_required", pd.Series("", index=sample.index))
                    .astype(str)
                    .str.lower()
                    .eq("true")
                    .sum()
                ),
            }
        ]
    ).to_csv(summary_path, index=False)
    print(f"wrote holdout sample to {output_path}")
    print(f"wrote summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
