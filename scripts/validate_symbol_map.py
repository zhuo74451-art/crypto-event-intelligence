import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
SPOT_EXCHANGE_INFO = "https://api.binance.com/api/v3/exchangeInfo"
FUTURES_EXCHANGE_INFO = "https://fapi.binance.com/fapi/v1/exchangeInfo"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate symbol_map.csv against public Binance exchangeInfo endpoints.")
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "symbol_map_market_validation.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "symbol_map_market_validation_summary.csv"))
    parser.add_argument("--report", default=str(ROOT / "results" / "symbol_map_market_validation.md"))
    parser.add_argument("--timeout", type=int, default=10)
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def fetch_symbols(url: str, timeout: int) -> set[str]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    return {str(item.get("symbol", "")).upper() for item in payload.get("symbols", [])}


def render_report(rows: pd.DataFrame, summary: dict) -> str:
    lines = [
        "# Symbol Map Market Validation",
        "",
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
        "",
        f"symbol_count: {summary['symbol_count']}",
        f"spot_mismatch_count: {summary['spot_mismatch_count']}",
        f"futures_mismatch_count: {summary['futures_mismatch_count']}",
        f"status: {summary['status']}",
        "",
        "This check uses public Binance exchangeInfo endpoints only. It does not require API keys and does not place orders.",
        "",
        "| asset | spot | spot_exists | futures | futures_exists | status |",
        "|---|---|---|---|---|---|",
    ]
    for _, row in rows.iterrows():
        lines.append(
            f"| {row['asset_symbol']} | {row['binance_spot_symbol']} | {row['spot_exists']} | {row['binance_futures_symbol']} | {row['futures_exists']} | {row['status']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    symbol_map_path = normalize_path(args.symbol_map)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    report_path = normalize_path(args.report)

    if not symbol_map_path.exists():
        print(f"symbol map not found: {symbol_map_path}")
        return 1

    symbol_map = pd.read_csv(symbol_map_path, dtype=str).fillna("")
    spot_symbols = fetch_symbols(SPOT_EXCHANGE_INFO, args.timeout)
    futures_symbols = fetch_symbols(FUTURES_EXCHANGE_INFO, args.timeout)

    rows = []
    for _, row in symbol_map.iterrows():
        asset = str(row.get("asset_symbol", "")).strip().upper()
        spot = str(row.get("binance_spot_symbol", "")).strip().upper()
        futures = str(row.get("binance_futures_symbol", "")).strip().upper()
        spot_exists = "blank" if not spot else ("yes" if spot in spot_symbols else "no")
        futures_exists = "blank" if not futures else ("yes" if futures in futures_symbols else "no")
        status = "pass" if spot_exists != "no" and futures_exists != "no" else "fail"
        rows.append(
            {
                "asset_symbol": asset,
                "binance_spot_symbol": spot,
                "spot_exists": spot_exists,
                "binance_futures_symbol": futures,
                "futures_exists": futures_exists,
                "status": status,
            }
        )

    df = pd.DataFrame(rows)
    spot_mismatch_count = int(df["spot_exists"].eq("no").sum())
    futures_mismatch_count = int(df["futures_exists"].eq("no").sum())
    summary = {
        "symbol_count": int(len(df)),
        "spot_mismatch_count": spot_mismatch_count,
        "futures_mismatch_count": futures_mismatch_count,
        "status": "pass" if spot_mismatch_count == 0 and futures_mismatch_count == 0 else "fail",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    pd.DataFrame([summary]).to_csv(summary_path, index=False)
    report_path.write_text(render_report(df, summary), encoding="utf-8")
    print(f"wrote symbol validation to {output_path}")
    print(f"wrote summary to {summary_path}")
    print(f"wrote report to {report_path}")
    return 0 if summary["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
