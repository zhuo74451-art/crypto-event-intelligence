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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a concise Hyperliquid public market-structure card.")
    parser.add_argument("--input", default=str(ROOT / "data" / "hyperliquid" / "market_meta_snapshot.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v15_hyperliquid_market_meta_card.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v15_hyperliquid_market_meta_card_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def yi(value: Any) -> str:
    return f"{safe_float(value) / 100_000_000:.2f} 亿美元"


def pct(value: Any) -> str:
    number = safe_float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.2f}%"


def funding(value: Any) -> str:
    return f"{safe_float(value) * 100:.4f}%"


def funding_annualized(value: Any) -> str:
    return f"{safe_float(value) * 3 * 365 * 100:.2f}%"


def latest_previous_by_asset(rows: list[dict]) -> dict[str, dict]:
    by_asset: dict[str, list[dict]] = {}
    for row in rows:
        asset = str(row.get("asset_symbol") or "").strip().upper()
        if asset:
            by_asset.setdefault(asset, []).append(row)
    output = {}
    for asset, asset_rows in by_asset.items():
        ordered = sorted(asset_rows, key=lambda row: str(row.get("observed_at_utc") or ""))
        if len(ordered) >= 2:
            output[asset] = ordered[-2]
    return output


def change_pct(current: Any, previous: Any) -> float:
    prev = safe_float(previous)
    cur = safe_float(current)
    return (cur / prev - 1.0) * 100 if prev > 0 else 0.0


def main() -> int:
    args = parse_args()
    rows = [row for row in read_rows(normalize_path(args.input)) if row.get("quality_status") == "ok"]
    history_rows = read_rows(ROOT / "data" / "hyperliquid" / "market_meta_history.csv")
    previous = latest_previous_by_asset(history_rows)
    oi_anomalies = []
    volume_anomalies = []
    for row in rows:
        prev = previous.get(str(row.get("asset_symbol") or "").upper(), {})
        oi_change = change_pct(row.get("open_interest_usd"), prev.get("open_interest_usd"))
        volume_change = change_pct(row.get("day_volume_usd"), prev.get("day_volume_usd"))
        row["open_interest_change_pct_since_prev"] = f"{oi_change:.4f}"
        row["day_volume_change_pct_since_prev"] = f"{volume_change:.4f}"
        if abs(oi_change) >= 5:
            oi_anomalies.append(row)
        if abs(volume_change) >= 50:
            volume_anomalies.append(row)
    top_funding = sorted(rows, key=lambda row: abs(safe_float(row.get("funding_rate"))), reverse=True)[:3]

    lines = ["# Hyperliquid 官方市场结构快照", ""]
    if not rows:
        lines.append("- 暂无可用官方市场快照。")
    else:
        observed = rows[0].get("observed_at_china", "-")
        lines.append(f"- 时间：{observed}")
        lines.append(f"- 覆盖：{len(rows)} 个永续合约，数据来自 Hyperliquid 官方公开 Info API。")
        lines.append("")
        lines.append("## 持仓异动")
        if not oi_anomalies:
            lines.append("- 暂无达到 5% 阈值的 OI 异动；静态 OI 排名不单独推送。")
        for row in sorted(oi_anomalies, key=lambda item: abs(safe_float(item.get("open_interest_change_pct_since_prev"))), reverse=True)[:5]:
            lines.append(
                f"- {row.get('asset_symbol')}｜OI {pct(row.get('open_interest_change_pct_since_prev'))}｜当前 {yi(row.get('open_interest_usd'))}｜24h价格 {pct(row.get('price_change_pct_24h'))}"
            )
        lines.append("")
        lines.append("## 成交异动")
        if not volume_anomalies:
            lines.append("- 暂无达到 50% 阈值的成交额异动；静态成交排名不单独推送。")
        for row in sorted(volume_anomalies, key=lambda item: abs(safe_float(item.get("day_volume_change_pct_since_prev"))), reverse=True)[:5]:
            lines.append(f"- {row.get('asset_symbol')}｜成交额 {pct(row.get('day_volume_change_pct_since_prev'))}｜当前 {yi(row.get('day_volume_usd'))}")
        lines.append("")
        lines.append("## 费率偏离")
        for row in top_funding:
            lines.append(f"- {row.get('asset_symbol')}｜资金费率 {funding(row.get('funding_rate'))}/8h（年化 {funding_annualized(row.get('funding_rate'))}）｜24h {pct(row.get('price_change_pct_24h'))}")
        lines.append("")
        lines.append("说明：这是 Hyperliquid 官方公开市场结构数据，不包含第三方估算清算热力图，不构成任何交易建议。")

    output = normalize_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {
        "rows": len(rows),
        "oi_anomaly_count": len(oi_anomalies),
        "volume_anomaly_count": len(volume_anomalies),
        "top_funding_asset": top_funding[0].get("asset_symbol", "") if top_funding else "",
        "status": "pass" if rows else "warning",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"hyperliquid_market_meta_card rows={len(rows)} status={summary['status']}")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
