import argparse
import csv
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


COLUMNS = [
    "asset_symbol",
    "price_change_pct_24h",
    "open_interest_change_pct_24h",
    "funding_rate",
    "quadrant",
    "quadrant_label",
    "plain_explanation",
    "risk_level",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify price/open-interest quadrant for market-state rows.")
    parser.add_argument("--market-state", default=str(ROOT / "results" / "v14_market_state_snapshot.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_price_oi_quadrant.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_price_oi_quadrant_summary.csv"))
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


def classify(price_change: float, oi_change: float, funding_rate: float) -> tuple[str, str, str, str]:
    funding_pct = funding_rate * 100
    if abs(price_change) < 0.5 and abs(oi_change) < 1.0:
        return "neutral", "价格和持仓变化不明显", "市场结构暂时平稳，优先观察后续放量或资金费率变化。", "低"
    if price_change > 0 and oi_change > 0:
        if funding_pct > 0.01:
            return "Q1_overheated", "上涨增仓，但多头成本偏高", "价格上涨且新仓增加，说明资金正在进入；资金费率偏高时，需要警惕短期过热。", "中"
        return "Q1_healthy", "上涨增仓，结构相对健康", "价格上涨且持仓增加，说明有新资金参与；若资金费率中性，结构相对健康。", "中"
    if price_change > 0 and oi_change <= 0:
        return "Q2_deleveraging_up", "上涨减仓", "价格上涨但持仓减少，可能是空头止损或多头获利了结，上涨动能可能变弱。", "中"
    if price_change < 0 and oi_change < 0:
        return "Q3_deleveraging_down", "下跌减仓", "价格下跌且持仓减少，可能是多头止损或空头获利了结，下跌动能可能逐步释放。", "中"
    if price_change < 0 and oi_change >= 0:
        if funding_rate < 0:
            return "Q4_short_building", "回调增仓，空头占优", "价格回调但持仓增加，且资金费率为负，说明空头可能在增加，短期波动风险上升。", "中"
        return "Q4_disagreement", "回调增仓，市场分歧加大", "价格回调但持仓增加，说明新仓还在进场；可能是抄底资金，也可能是对冲或空头加仓。", "中"
    return "neutral", "结构不明确", "价格和持仓组合暂时没有清晰含义。", "低"


def main() -> int:
    args = parse_args()
    rows = []
    for row in read_rows(normalize_path(args.market_state)):
        if str(row.get("quality_status", "")).lower() != "ok":
            continue
        price = safe_float(row.get("price_change_pct_24h"))
        oi = safe_float(row.get("open_interest_change_pct_24h"))
        funding = safe_float(row.get("funding_rate"))
        quadrant, label, explanation, risk = classify(price, oi, funding)
        rows.append(
            {
                "asset_symbol": row.get("asset_symbol", ""),
                "price_change_pct_24h": row.get("price_change_pct_24h", ""),
                "open_interest_change_pct_24h": row.get("open_interest_change_pct_24h", ""),
                "funding_rate": row.get("funding_rate", ""),
                "quadrant": quadrant,
                "quadrant_label": label,
                "plain_explanation": explanation,
                "risk_level": risk,
            }
        )
    write_rows(normalize_path(args.output), rows, COLUMNS)
    counts = {}
    for row in rows:
        counts[row["quadrant"]] = counts.get(row["quadrant"], 0) + 1
    summary = {"rows": len(rows), "quadrant_counts": ";".join(f"{k}:{v}" for k, v in sorted(counts.items())), "status": "pass" if rows else "warning"}
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"quadrant_rows={len(rows)}")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
