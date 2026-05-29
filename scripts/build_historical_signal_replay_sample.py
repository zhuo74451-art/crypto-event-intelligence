import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a historical replay review sample from older mature event candidates.")
    parser.add_argument("--input", default=str(ROOT / "data" / "event_candidates_real_500_older_mature_review_suggested.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "event_candidates_v08_historical_replay_200.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_historical_replay_sample_summary.csv"))
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--mode", choices=["broad", "conservative", "non_btc_single_asset", "non_benchmark_alt"], default="broad")
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def has_flag(row: pd.Series, flag: str) -> bool:
    return flag in [part.strip() for part in str(row.get("quality_flags", "")).split(",") if part.strip()]


def nonblank(value) -> bool:
    return str(value or "").strip() != ""


def base_eligible(row: pd.Series) -> bool:
    if str(row.get("v13_strict_candidate_decision", "")).strip().lower() == "archive":
        return False
    if str(row.get("is_mature_72h", "")).strip().lower() not in {"true", "1", "yes"}:
        return False
    if str(row.get("time_parse_status", "")).strip().lower() != "ok":
        return False
    if has_flag(row, "missing_asset") or has_flag(row, "time_parse_failed"):
        return False
    if not nonblank(row.get("candidate_asset_symbol", "")):
        return False
    if not nonblank(row.get("backtest_time_utc", "")):
        return False
    if not (nonblank(row.get("candidate_binance_spot_symbol", "")) or nonblank(row.get("candidate_binance_futures_symbol", ""))):
        return False
    if str(row.get("suggested_review_decision", "")).strip().lower() not in {"include", "fix"}:
        return False
    return True


def conservative_eligible(row: pd.Series) -> bool:
    if not base_eligible(row):
        return False
    score = float(row.get("auto_quality_score", 0) or 0)
    if score < 85:
        return False
    if str(row.get("event_scope", "")).strip() not in {"single_asset", "market_wide"}:
        return False
    if str(row.get("candidate_event_type", "")).strip() == "other":
        return False
    return True


def non_btc_single_asset_eligible(row: pd.Series) -> bool:
    if not base_eligible(row):
        return False
    asset = str(row.get("candidate_asset_symbol", "") or "").strip().upper()
    if asset in {"BTC", "ETH"}:
        return False
    if str(row.get("event_scope", "")).strip() != "single_asset":
        return False
    if str(row.get("candidate_event_type", "")).strip() in {"macro", "other"}:
        return False
    return True


def non_benchmark_alt_eligible(row: pd.Series) -> bool:
    if not base_eligible(row):
        return False
    asset = str(row.get("candidate_asset_symbol", "") or "").strip().upper()
    if asset in {"BTC", "ETH", "USDT", "USDC"}:
        return False
    subtype = str(row.get("candidate_event_subtype") or row.get("v12_event_subtype") or "").strip()
    if asset == "HYPE" and subtype in {"whale_wallet_position", "whale_position"}:
        return False
    event_type = str(row.get("candidate_event_type", "") or "").strip()
    if event_type == "macro":
        return False
    if has_flag(row, "missing_symbol") or has_flag(row, "unsupported_symbol"):
        return False
    return True


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)

    df = pd.read_csv(input_path, dtype=str).fillna("")
    df["auto_quality_score_num"] = pd.to_numeric(df.get("auto_quality_score", 0), errors="coerce").fillna(-9999)
    if args.mode == "non_btc_single_asset":
        pool = df[df.apply(non_btc_single_asset_eligible, axis=1)].copy()
    elif args.mode == "non_benchmark_alt":
        pool = df[df.apply(non_benchmark_alt_eligible, axis=1)].copy()
    elif args.mode == "conservative":
        pool = df[df.apply(conservative_eligible, axis=1)].copy()
    else:
        pool = df[df.apply(base_eligible, axis=1)].copy()

    pool = pool.sort_values(
        ["auto_quality_score_num", "event_age_hours", "candidate_event_type", "candidate_id"],
        ascending=[False, False, True, True],
    )
    selected = pool.head(args.limit).copy()
    selected["review_decision"] = "include"
    selected["historical_replay_mode"] = args.mode
    selected = selected.drop(columns=["auto_quality_score_num"], errors="ignore")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(output_path, index=False)

    rows = [
        {
            "metric": "total_input_rows",
            "value": len(df),
        },
        {
            "metric": "eligible_rows",
            "value": len(pool),
        },
        {
            "metric": "selected_rows",
            "value": len(selected),
        },
        {
            "metric": "limit",
            "value": args.limit,
        },
        {
            "metric": "mode",
            "value": args.mode,
        },
    ]
    for event_type, count in selected.get("candidate_event_type", pd.Series(dtype=str)).value_counts().items():
        rows.append({"metric": f"selected_event_type:{event_type}", "value": int(count)})
    for asset, count in selected.get("candidate_asset_symbol", pd.Series(dtype=str)).value_counts().head(20).items():
        rows.append({"metric": f"selected_asset:{asset}", "value": int(count)})

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(summary_path, index=False)
    print(f"eligible_rows={len(pool)}")
    print(f"selected_rows={len(selected)}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
