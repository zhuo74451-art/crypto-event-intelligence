import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Release low-risk manual_review_required rows using Claude-approved rules.")
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--released-output", default=str(ROOT / "data" / "v06_manual_review_released_rows.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_manual_review_release_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def as_bool_true(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().eq("true")


def add_note(existing: object, tag: str) -> str:
    text = str(existing or "").strip()
    return tag if not text else f"{text} | {tag}"


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    released_output = normalize_path(args.released_output)
    summary_path = normalize_path(args.summary)

    if not input_path.exists():
        print(f"input not found: {input_path}")
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    for col in ["manual_review_required", "label_origin", "manual_decision", "manual_channel_route", "event_scope", "auto_label_confidence", "manual_notes"]:
        if col not in df.columns:
            df[col] = ""

    conf = pd.to_numeric(df["auto_label_confidence"], errors="coerce").fillna(0)
    manual_required = as_bool_true(df["manual_review_required"])

    # Claude-approved conservative release:
    # auto_provisional + high-confidence discard + non-macro research route.
    release_mask = (
        manual_required
        & df["label_origin"].eq("auto_provisional")
        & conf.ge(0.95)
        & df["manual_decision"].eq("discard")
        & df["manual_channel_route"].isin(["research_only", "unsupported_research"])
        & ~df["manual_channel_route"].eq("macro_policy")
    )

    released = df[release_mask].copy()
    for idx in df[release_mask].index:
        df.at[idx, "manual_review_required"] = "false"
        df.at[idx, "label_origin"] = "auto_released_low_risk"
        df.at[idx, "manual_notes"] = add_note(df.at[idx, "manual_notes"], "manual_review_released_by_claude_rule")

    remaining = int(as_bool_true(df["manual_review_required"]).sum())
    total = len(df)
    summary = pd.DataFrame(
        [
            {
                "total_rows": total,
                "released_rows": int(len(released)),
                "manual_review_required_remaining": remaining,
                "manual_review_required_rate": round(remaining / total, 4) if total else 0,
                "target_rate": 0.10,
                "status": "pass" if total and remaining / total <= 0.10 else "fail",
            }
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    released_output.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    released.to_csv(released_output, index=False)
    summary.to_csv(summary_path, index=False)
    print(f"released {len(released)} rows")
    print(f"wrote updated sheet to {output_path}")
    print(f"wrote summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
