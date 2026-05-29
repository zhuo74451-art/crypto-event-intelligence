import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Move macro market-wide asset-missing rows to macro_holdout queue.")
    parser.add_argument("--input", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--holdout-output", default=str(ROOT / "data" / "v06_macro_holdout_queue.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_macro_holdout_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def blank(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().eq("")


def add_note(existing: object, tag: str) -> str:
    text = str(existing or "").strip()
    return tag if not text else f"{text} | {tag}"


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    holdout_output = normalize_path(args.holdout_output)
    summary_path = normalize_path(args.summary)

    if not input_path.exists():
        print(f"input not found: {input_path}")
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    for col in ["manual_review_required", "manual_channel_route", "manual_primary_asset_symbol", "primary_asset_symbol", "candidate_asset_symbol", "event_scope", "manual_notes", "label_origin", "review_queue"]:
        if col not in df.columns:
            df[col] = ""

    manual_required = df["manual_review_required"].astype(str).str.lower().eq("true")
    route_macro = df["manual_channel_route"].eq("macro_policy")
    asset_missing = blank(df["manual_primary_asset_symbol"]) & blank(df["primary_asset_symbol"]) & blank(df["candidate_asset_symbol"])
    scope_market = df["event_scope"].isin(["market_wide", "unknown"])
    move_mask = manual_required & route_macro & asset_missing & scope_market

    moved = df[move_mask].copy()
    tag = "macro_bypass_v0.6"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for idx in df[move_mask].index:
        df.at[idx, "manual_review_required"] = "false"
        df.at[idx, "review_queue"] = "macro_holdout"
        df.at[idx, "label_origin"] = "macro_holdout_v06"
        df.at[idx, "manual_notes"] = add_note(df.at[idx, "manual_notes"], f"{tag}({timestamp})")

    moved = df[move_mask].copy()
    remaining = int(df["manual_review_required"].astype(str).str.lower().eq("true").sum())
    total = len(df)
    summary = pd.DataFrame(
        [
            {
                "total_rows": total,
                "moved_to_macro_holdout": int(len(moved)),
                "manual_review_required_remaining": remaining,
                "manual_review_required_rate": round(remaining / total, 4) if total else 0,
                "status": "pass" if total and remaining / total <= 0.10 else "fail",
            }
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    holdout_output.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    moved.to_csv(holdout_output, index=False)
    summary.to_csv(summary_path, index=False)
    print(f"moved {len(moved)} rows to macro_holdout")
    print(f"wrote summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
