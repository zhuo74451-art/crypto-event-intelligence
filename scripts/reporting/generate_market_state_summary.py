import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a concise plain-Chinese market-state first-screen block.")
    parser.add_argument("--market-state", default=str(ROOT / "results" / "v14_market_state_snapshot.csv"))
    parser.add_argument("--market-summary", default=str(ROOT / "results" / "v14_market_state_snapshot_summary.csv"))
    parser.add_argument("--focus-assets", default=str(ROOT / "results" / "v14_focus_assets.csv"))
    parser.add_argument("--quadrants", default=str(ROOT / "results" / "v14_price_oi_quadrant.csv"))
    parser.add_argument("--derivatives-summary", default=str(ROOT / "results" / "v14_derivatives_history_percentiles_summary.csv"))
    parser.add_argument("--percentile-alerts", default=str(ROOT / "results" / "v15_percentile_alerts.json"))
    parser.add_argument("--etf-summary-md", default=str(ROOT / "results" / "v14_etf_plain_summary.md"))
    parser.add_argument("--alert-headline", default=str(ROOT / "results" / "v14_market_alert_headline.txt"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_market_state_first_screen.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_market_state_first_screen_summary.csv"))
    parser.add_argument("--run-dependencies", default="true")
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


def funding_label(rate: float) -> str:
    pct_value = rate * 100
    if abs(rate) < 0.0002:
        return f"{pct_value:.4f}%（中性）"
    if rate >= 0.0008:
        return f"{pct_value:.4f}%（偏高）"
    if rate <= -0.0008:
        return f"{pct_value:.4f}%（偏低）"
    return f"{pct_value:.4f}%（接近中性）"


def funding_percentile_text(asset: str, rate: float, percentile: Any) -> str:
    pct_value = safe_float(percentile)
    if not pct_value:
        return ""
    side = "多头" if rate >= 0 else "空头"
    if pct_value >= 95:
        desc = f"{side}持仓成本处于历史极高位"
    elif pct_value >= 90:
        desc = f"{side}持仓成本处于历史高位"
    elif pct_value <= 5:
        desc = f"{side}持仓成本处于历史极低位"
    elif pct_value <= 10:
        desc = f"{side}持仓成本处于历史低位"
    else:
        return ""
    return f"• {asset} 资金费率 {rate * 100:.4f}%（90日分位 {pct_value:.1f}%，{desc}）。"


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace").strip()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return {}


def run_step(args: list[str]) -> None:
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def maybe_run_dependencies(enabled: str) -> None:
    if str(enabled).strip().lower() not in {"1", "true", "yes", "y"}:
        return
    run_step(["scripts/market/select_focus_assets.py"])
    run_step(["scripts/market/classify_price_oi_quadrant.py"])
    run_step(["scripts/market/build_derivatives_history_percentiles.py"])
    run_step(["scripts/market/generate_percentile_alerts.py"])
    run_step(["scripts/reporting/generate_etf_summary.py"])


def row_by_asset(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("asset_symbol") or "").upper(): row for row in rows}


def render(args: argparse.Namespace) -> tuple[str, dict]:
    market_rows = read_rows(normalize_path(args.market_state))
    market_by_asset = row_by_asset(market_rows)
    summary_rows = read_rows(normalize_path(args.market_summary))
    market_summary = summary_rows[-1] if summary_rows else {}
    focus_rows = [row for row in read_rows(normalize_path(args.focus_assets)) if str(row.get("selected", "")).lower() == "true"]
    quad_by_asset = row_by_asset(read_rows(normalize_path(args.quadrants)))
    deriv_by_asset = row_by_asset(read_rows(normalize_path(args.derivatives_summary)))
    percentile_alerts = load_json(normalize_path(args.percentile_alerts))
    etf_text = load_text(normalize_path(args.etf_summary_md))

    btc = market_by_asset.get("BTC", {})
    eth = market_by_asset.get("ETH", {})
    btc_deriv = deriv_by_asset.get("BTC", {})
    eth_deriv = deriv_by_asset.get("ETH", {})
    focus_assets = [row.get("asset_symbol") for row in focus_rows]
    non_major_focus = [asset for asset in focus_assets if asset not in {"BTC", "ETH"}]

    if safe_float(btc.get("price_change_pct_24h")) < -1 and safe_float(eth.get("price_change_pct_24h")) < -1:
        broad = "主流资产普遍回调"
    elif safe_float(btc.get("price_change_pct_24h")) > 1 and safe_float(eth.get("price_change_pct_24h")) > 1:
        broad = "主流资产普遍反弹"
    else:
        broad = "主流资产分化"

    lines = [
        f"• BTC {pct(btc.get('price_change_pct_24h'))}（持仓 {pct(btc.get('open_interest_change_pct_24h'))}），ETH {pct(eth.get('price_change_pct_24h'))}（持仓 {pct(eth.get('open_interest_change_pct_24h'))}）：{broad}。",
    ]
    shown_funding_assets = set()
    for asset, row, deriv in [("BTC", btc, btc_deriv), ("ETH", eth, eth_deriv)]:
        funding_line = funding_percentile_text(asset, safe_float(row.get("funding_rate")), deriv.get("funding_abs_percentile_90d"))
        if funding_line:
            lines.append(funding_line)
            shown_funding_assets.add(asset)
    if non_major_focus:
        lines.append(f"• 焦点资产：{', '.join(non_major_focus[:3])} 触发主流/异常阈值；小市值资产未达极端阈值不进首屏。")
    for alert in percentile_alerts.get("frontpage_alerts", [])[:2]:
        if alert.get("alert_type") == "oi_change_percentile":
            lines.append(f"• 持仓异常：{alert.get('asset_symbol')} 24h变化分位 {alert.get('percentile')}%（{alert.get('interpretation')}）。")
        elif alert.get("alert_type") == "funding_rate_percentile":
            if str(alert.get("asset_symbol") or "").upper() in shown_funding_assets:
                continue
            lines.append(f"• 费率异常：{alert.get('asset_symbol')} 资金费率处于90日 {alert.get('percentile')}% 分位。")
    btc_price = safe_float(btc.get("price_change_pct_24h"))
    eth_price = safe_float(eth.get("price_change_pct_24h"))
    btc_oi = safe_float(btc.get("open_interest_change_pct_24h"))
    eth_oi = safe_float(eth.get("open_interest_change_pct_24h"))
    if (btc_price < 0 or eth_price < 0) and (btc_oi > 0 or eth_oi > 0):
        lines.append("• 结构解读：价格回调 + 持仓增加 = 新仓进场（可能抄底，也可能空头加仓）。")
    else:
        btc_quad = quad_by_asset.get("BTC", {}).get("plain_explanation", "")
        eth_quad = quad_by_asset.get("ETH", {}).get("plain_explanation", "")
        if btc_quad or eth_quad:
            explanation = (btc_quad or eth_quad).replace("；若资金费率中性，结构相对健康", "")
            lines.append(f"• 结构解读：{explanation}")

    headline = load_text(normalize_path(args.alert_headline))
    if headline and not ("ETF" in headline and etf_text):
        lines.insert(0, f"• {headline}")

    if etf_text:
        etf_lines = [line for line in etf_text.splitlines() if line.strip()]
        selected_etf_lines = []
        for line in etf_lines:
            if "现货 ETF" in line and ("极端" in line or "分位" in line) and len(selected_etf_lines) < 1:
                selected_etf_lines.append(line)
        lines.extend(selected_etf_lines or etf_lines[:2])
    lines = lines[:8]
    text = "\n".join(lines)
    summary = {
        "line_count": len(lines),
        "focus_assets": ";".join(asset for asset in focus_assets if asset),
        "btc_price_change_pct_24h": btc.get("price_change_pct_24h", ""),
        "eth_price_change_pct_24h": eth.get("price_change_pct_24h", ""),
        "etf_loaded": "true" if etf_text else "false",
        "derivatives_percentiles_loaded": "true" if deriv_by_asset else "false",
        "percentile_alerts_loaded": "true" if percentile_alerts else "false",
        "status": "pass" if btc and eth else "warning",
    }
    return text, summary


def main() -> int:
    args = parse_args()
    maybe_run_dependencies(args.run_dependencies)
    text, summary = render(args)
    normalize_path(args.output).parent.mkdir(parents=True, exist_ok=True)
    normalize_path(args.output).write_text(text + "\n", encoding="utf-8")
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"market_first_screen_status={summary['status']} lines={summary['line_count']}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
