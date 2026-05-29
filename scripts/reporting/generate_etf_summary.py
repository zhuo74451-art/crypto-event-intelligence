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
    parser = argparse.ArgumentParser(description="Generate a plain-Chinese ETF flow summary for TG digest first screen.")
    parser.add_argument("--summary-input", default=str(ROOT / "results" / "v14_etf_daily_digest_with_context_summary.csv"))
    parser.add_argument("--eth-input", default=str(ROOT / "data" / "eth_etf_flows_farside.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_etf_plain_summary.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_etf_plain_summary.csv"))
    parser.add_argument("--concentration-output", default=str(ROOT / "results" / "v14_etf_concentration_interpretation.txt"))
    parser.add_argument("--eth-display-threshold-usd", type=float, default=50_000_000)
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


def latest_completed(rows: list[dict]) -> dict:
    for row in rows:
        if abs(safe_float(row.get("total_net_flow_usd"))) > 0:
            return row
    return rows[0] if rows else {}


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


def signed_yi(value: Any) -> str:
    number = safe_float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number / 100_000_000:.2f} 亿美元"


def flow_label(percentile: float, flow_usd: float) -> str:
    if flow_usd == 0:
        return "中性"
    if percentile >= 95:
        return "极端"
    if percentile >= 75:
        return "偏强" if flow_usd > 0 else "偏弱"
    if percentile >= 50:
        return "中等偏上"
    if percentile >= 25:
        return "中性"
    return "偏低"


def etf_percentile(rows: list[dict], latest: dict) -> float:
    current = abs(safe_float(latest.get("total_net_flow_usd")))
    sample = [abs(safe_float(row.get("total_net_flow_usd"))) for row in rows if abs(safe_float(row.get("total_net_flow_usd"))) > 0][:90]
    if not sample:
        return 0.0
    return round(sum(1 for value in sample if value <= current) / len(sample) * 100, 1)


def bool_cn(value: str) -> str:
    return "是" if str(value).strip().lower() == "true" else "否"


def parse_top3(raw: str) -> dict[str, tuple[float, float]]:
    output = {}
    for part in str(raw or "").split(";"):
        bits = [item.strip() for item in part.split(":")]
        if len(bits) < 3:
            continue
        try:
            output[bits[0].upper()] = (float(bits[1]), float(bits[2].replace("pp", "")))
        except Exception:
            continue
    return output


def concentration_interpretation(raw: str) -> str:
    top = parse_top3(raw)
    ibit_share, ibit_delta = top.get("IBIT", (0.0, 0.0))
    gbtc_share, gbtc_delta = top.get("GBTC", (0.0, 0.0))
    fbtc_share, fbtc_delta = top.get("FBTC", (0.0, 0.0))
    notes = []
    if ibit_delta > 10 and gbtc_delta < 0:
        notes.append("资金从老基金流向头部新基金，偏正常轮动。")
    elif ibit_delta > 10 and gbtc_delta >= 0:
        notes.append("资金份额集中到头部基金，市场偏好明确。")
    elif ibit_delta < -5:
        notes.append("IBIT 份额下降，头部基金份额被稀释，需关注资金分散。")
    if fbtc_delta < -5:
        notes.append("FBTC 份额明显下降，可能存在相对赎回或资金转移压力。")
    if not notes and raw:
        notes.append("ETF 份额结构未见极端变化。")
    return "；".join(note.rstrip("。") for note in notes) + ("。" if notes else "")


def render(row: dict, eth_rows: list[dict], eth_threshold: float) -> tuple[str, dict]:
    if not row:
        summary = {"status": "missing", "line_count": 1, "flow_label": "missing"}
        return "• ETF：暂无可用 ETF 日频数据，可能是休市或数据未刷新。", summary
    latest_flow = safe_float(row.get("latest_total_net_flow_usd"))
    percentile = safe_float(row.get("abs_percentile_90d"))
    label = flow_label(percentile, latest_flow)
    top = str(row.get("top_3_etf_by_share") or "").strip()
    concentration_note = concentration_interpretation(top)
    lines = [
        f"• BTC 现货 ETF：{row.get('latest_date','-')} 净流 {signed_yi(latest_flow)}（90日分位 {percentile:.1f}%，{label}）",
    ]
    eth_latest = latest_completed(eth_rows)
    eth_flow = safe_float(eth_latest.get("total_net_flow_usd"))
    eth_percentile = etf_percentile(eth_rows, eth_latest) if eth_latest else 0.0
    eth_label = flow_label(eth_percentile, eth_flow)
    if eth_latest and abs(eth_flow) >= eth_threshold:
        lines.append(
            f"• ETH 现货 ETF：{eth_latest.get('date','-')} 净流 {signed_yi(eth_flow)}（90日分位 {eth_percentile:.1f}%，{eth_label}）"
        )
    if top:
        lines.append(f"• ETF 集中度：{top[:90]}")
        if concentration_note:
            lines.append(f"• 集中度解释：{concentration_note}")
    if str(row.get("calendar_effect_window", "")).strip():
        lines.append(f"• 日历因素：月末/季末窗口 {bool_cn(row.get('calendar_effect_window'))}，异常阈值 {row.get('adjusted_abs_percentile_threshold','-')} 分位")
    if latest_flow < 0:
        interpretation = "资金净流出较大时，先看是否为月末/季末调仓，再看是否连续多日流出。"
    elif latest_flow > 0:
        interpretation = "资金净流入时，优先观察是否连续，单日流入不单独代表趋势。"
    else:
        interpretation = "ETF 资金流向中性，暂不放大解释。"
    lines.append(f"• 解读：{interpretation}")
    summary = {
        "status": "pass",
        "latest_date": row.get("latest_date", ""),
        "latest_total_net_flow_usd": f"{latest_flow:.2f}",
        "abs_percentile_90d": f"{percentile:.2f}",
        "flow_label": label,
        "eth_latest_date": eth_latest.get("date", "") if eth_latest else "",
        "eth_latest_total_net_flow_usd": f"{eth_flow:.2f}" if eth_latest else "",
        "eth_abs_percentile_90d": f"{eth_percentile:.2f}" if eth_latest else "",
        "eth_displayed": "true" if eth_latest and abs(eth_flow) >= eth_threshold else "false",
        "concentration_interpretation": concentration_note,
        "line_count": len(lines),
    }
    return "\n".join(lines), summary


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.summary_input))
    eth_rows = read_rows(normalize_path(args.eth_input))
    text, summary = render(rows[-1] if rows else {}, eth_rows, args.eth_display_threshold_usd)
    normalize_path(args.output).parent.mkdir(parents=True, exist_ok=True)
    normalize_path(args.output).write_text(text + "\n", encoding="utf-8")
    normalize_path(args.concentration_output).write_text(str(summary.get("concentration_interpretation") or "暂无 ETF 集中度解释。") + "\n", encoding="utf-8")
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"etf_plain_status={summary['status']}")
    return 0 if summary["status"] in {"pass", "missing"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
