import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Release high-confidence macro discard rows from the manual review queue."
    )
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--released-output", default=str(ROOT / "data" / "v06_macro_discard_released_rows.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_macro_discard_release_summary.csv"))
    parser.add_argument("--min-confidence", type=float, default=0.95)
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


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
    required_cols = [
        "manual_review_required",
        "manual_decision",
        "manual_channel_route",
        "event_scope",
        "auto_label_confidence",
        "label_origin",
        "manual_notes",
        "review_queue",
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    conf = pd.to_numeric(df["auto_label_confidence"], errors="coerce").fillna(0.0)
    manual_required = df["manual_review_required"].astype(str).str.lower().eq("true")
    release_mask = (
        manual_required
        & df["manual_decision"].eq("discard")
        & df["manual_channel_route"].eq("macro_policy")
        & df["event_scope"].isin(["multi_asset", "market_wide"])
        & conf.ge(args.min_confidence)
    )

    released = df[release_mask].copy()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tag = f"macro_discard_released_v0.6({timestamp})"

    for idx in df[release_mask].index:
        df.at[idx, "manual_review_required"] = "false"
        df.at[idx, "review_queue"] = "macro_discard_audit"
        df.at[idx, "label_origin"] = "auto_released_macro_discard_v06"
        df.at[idx, "manual_notes"] = add_note(df.at[idx, "manual_notes"], tag)

    remaining = int(df["manual_review_required"].astype(str).str.lower().eq("true").sum())
    total = len(df)
    summary = pd.DataFrame(
        [
            {
                "total_rows": total,
                "released_rows": int(len(released)),
                "manual_review_required_remaining": remaining,
                "manual_review_required_rate": round(remaining / total, 4) if total else 0,
                "target_rate": 0.085,
                "status": "pass" if total and remaining / total <= 0.085 else "fail",
            }
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    released_output.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    released.to_csv(released_output, index=False)
    summary.to_csv(summary_path, index=False)
    print(f"released {len(released)} macro discard rows")
    print(f"wrote updated sheet to {output_path}")
    print(f"wrote released rows to {released_output}")
    print(f"wrote summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
