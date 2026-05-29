import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate one-line market abnormality headline for TG first screen.")
    parser.add_argument("--market-state", default=str(ROOT / "results" / "v14_market_state_snapshot.csv"))
    parser.add_argument("--etf-summary", default=str(ROOT / "results" / "v14_etf_plain_summary.csv"))
    parser.add_argument("--prioritized-events", default=str(ROOT / "results" / "v14_prioritized_events.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_market_alert_headline.txt"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_market_alert_headline_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def pct(value: Any) -> str:
    number = safe_float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.2f}%"


def by_asset(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("asset_symbol") or "").strip().upper(): row for row in rows}


def main() -> int:
    args = parse_args()
    market = by_asset(read_rows(normalize_path(args.market_state)))
    etf_rows = read_rows(normalize_path(args.etf_summary))
    events = read_rows(normalize_path(args.prioritized_events))
    triggers = []

    for asset in ("BTC", "ETH"):
        row = market.get(asset, {})
        price = safe_float(row.get("price_change_pct_24h"))
        funding = safe_float(row.get("funding_rate")) * 100
        if abs(price) > 5:
            triggers.append(f"{asset} 24h {pct(price)}")
        if abs(funding) > 0.03:
            triggers.append(f"{asset} 资金费率 {funding:.4f}%")

    etf = etf_rows[-1] if etf_rows else {}
    etf_flow = safe_float(etf.get("latest_total_net_flow_usd"))
    if abs(etf_flow) > 500_000_000:
        direction = "净流入" if etf_flow > 0 else "净流出"
        triggers.append(f"BTC ETF {direction} {abs(etf_flow) / 100_000_000:.2f} 亿美元")
    if safe_float(etf.get("abs_percentile_90d")) >= 95:
        triggers.append(f"ETF 资金流达到90日极端分位 {safe_float(etf.get('abs_percentile_90d')):.1f}%")

    top_events = [row for row in events if row.get("priority_bucket") == "top_watch"]
    high_top = [row for row in top_events if safe_float(row.get("priority_score")) >= 8]
    if len(top_events) >= 2 and high_top:
        assets = "/".join(row.get("asset_symbol", "") for row in top_events[:3] if row.get("asset_symbol"))
        triggers.append(f"今日重点事件 {len(top_events)} 条（{assets}）")

    if triggers:
        text = "今日市场异常：" + "；".join(triggers[:3]) + "。"
        status = "alert"
    else:
        text = "今日市场无显著异常，常规监控。"
        status = "normal"
    normalize_path(args.output).parent.mkdir(parents=True, exist_ok=True)
    normalize_path(args.output).write_text(text + "\n", encoding="utf-8")
    summary = {"headline": text, "trigger_count": len(triggers), "triggers": "|".join(triggers), "status": status}
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
