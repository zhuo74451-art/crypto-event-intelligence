import argparse
import csv
import html
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
CN_TZ = timezone(timedelta(hours=8))


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and optionally send a China-time TG intelligence digest.")
    parser.add_argument("--sent-state", default=str(ROOT / "data" / "tg_live_sent_state.csv"))
    parser.add_argument("--alert-ledger", default=str(ROOT / "data" / "tg_alert_ledger.csv"))
    parser.add_argument("--long-short-output", default=str(ROOT / "data" / "binance_long_short_snapshot.csv"))
    parser.add_argument("--long-short-summary", default=str(ROOT / "results" / "v08_binance_long_short_summary.csv"))
    parser.add_argument("--performance-report", default=str(ROOT / "results" / "v08_tg_live_performance_report.md"))
    parser.add_argument("--followup-summary", default=str(ROOT / "results" / "v08_tg_alert_followup_summary.csv"))
    parser.add_argument("--decision-log", default=str(ROOT / "data" / "tg_radar_decision_log.csv"))
    parser.add_argument("--evidence-snippets", default=str(ROOT / "data" / "tg_evidence_snippets.csv"))
    parser.add_argument("--market-state-output", default=str(ROOT / "results" / "v14_market_state_snapshot.csv"))
    parser.add_argument("--market-state-summary", default=str(ROOT / "results" / "v14_market_state_snapshot_summary.csv"))
    parser.add_argument("--market-state-markdown", default=str(ROOT / "results" / "v14_market_state_snapshot.md"))
    parser.add_argument("--market-first-screen", default=str(ROOT / "results" / "v14_market_state_first_screen.md"))
    parser.add_argument("--market-first-screen-summary", default=str(ROOT / "results" / "v14_market_state_first_screen_summary.csv"))
    parser.add_argument("--percentile-alerts", default=str(ROOT / "results" / "v15_percentile_alerts.json"))
    parser.add_argument("--etf-context-summary", default=str(ROOT / "results" / "v14_etf_daily_digest_with_context_summary.csv"))
    parser.add_argument("--hyperliquid-context-summary", default=str(ROOT / "results" / "v14_hyperliquid_snapshot_v2_summary.csv"))
    parser.add_argument("--hyperliquid-liquidation-wall-summary", default=str(ROOT / "results" / "v15_hyperliquid_liquidation_wall_summary.csv"))
    parser.add_argument("--cex-netflow-baseline-summary", default=str(ROOT / "results" / "v081_cex_netflow_baseline_summary.csv"))
    parser.add_argument("--cex-netflow-baseline-by-pair", default=str(ROOT / "results" / "v081_cex_netflow_baseline_by_pair.csv"))
    parser.add_argument("--hyperliquid-readiness", default=str(ROOT / "results" / "v14_hyperliquid_baseline_readiness.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v08_tg_morning_digest.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v08_tg_morning_digest_summary.csv"))
    parser.add_argument("--sent-digest-state", default=str(ROOT / "data" / "tg_digest_sent_state.csv"))
    parser.add_argument("--digest-label", default="morning", choices=["morning", "noon", "evening", "custom"])
    parser.add_argument("--digest-title", default="")
    parser.add_argument("--window-end-hour", type=int, default=8)
    parser.add_argument("--window-hours", type=int, default=12)
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--token-env", default="TELEGRAM_BOT_TOKEN")
    parser.add_argument("--chat-id-env", default="TELEGRAM_PUBLISH_CHAT_IDS")
    parser.add_argument("--load-local-secrets", default="true")
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_now() -> datetime:
    return datetime.now(CN_TZ).replace(microsecond=0)


def china_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC+8")


def digest_window(end_hour: int, hours: int) -> tuple[datetime, datetime]:
    now = china_now()
    end = now.replace(hour=max(0, min(23, end_hour)), minute=0, second=0, microsecond=0)
    if now < end:
        end -= timedelta(days=1)
    start = end - timedelta(hours=max(1, hours))
    return start, end


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return {}


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_china_time(value: str) -> datetime | None:
    raw = str(value or "").strip().replace(" UTC+8", "")
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=CN_TZ)
        except ValueError:
            continue
    return None


def rows_in_window(rows: list[dict], field: str, start: datetime, end: datetime) -> list[dict]:
    output = []
    for row in rows:
        dt = parse_china_time(str(row.get(field, "") or ""))
        if dt and start <= dt < end:
            output.append(row)
    return output


def ledger_rows_in_window(rows: list[dict], start: datetime, end: datetime) -> list[dict]:
    output = []
    for row in rows:
        if str(row.get("send_status", "") or "").strip() not in {"sent", "dry_run"}:
            continue
        dt = parse_china_time(str(row.get("published_at_china", "") or row.get("created_at_china", "") or ""))
        if not dt or not (start <= dt < end):
            continue
        output.append(
            {
                "alert_id": row.get("alert_id") or "",
                "sent_at_china": row.get("published_at_china") or row.get("created_at_china") or "",
                "event_type": row.get("event_type") or row.get("source_type") or "unknown",
                "asset_symbol": row.get("asset_symbol") or "unknown",
                "amount_usd": row.get("magnitude_usd") or "",
                "severity_tier": row.get("confidence_bucket") or "",
                "source_type": row.get("source_type") or "",
                "alert_text": row.get("alert_text") or "",
            }
        )
    return output


def decision_rows_in_window(rows: list[dict], start: datetime, end: datetime) -> list[dict]:
    output = []
    for row in rows:
        if str(row.get("decision", "") or "").strip() != "filtered_digest_only":
            continue
        dt = parse_china_time(str(row.get("decided_at_china", "") or ""))
        if dt and start <= dt < end:
            output.append(row)
    return output


def safe_float(value) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def amount_cn(value) -> str:
    number = safe_float(value)
    if number >= 100_000_000:
        return f"{number / 100_000_000:.2f} 亿美元"
    if number >= 10_000:
        return f"{number / 10_000:.2f} 万美元"
    if number:
        return f"{number:.2f} 美元"
    return "-"


def compact_text(value: str, limit: int = 110) -> str:
    text = " ".join(str(value or "").replace("\r", "\n").split())
    return text[: limit - 1] + "…" if len(text) > limit else text


def user_text(value: str) -> str:
    text = str(value or "")
    replacements = {
        "多头拥挤": "多头集中度过高",
        "空头拥挤": "空头集中度过高",
        "资金费率偏离": "资金费率异常",
        "价格下跌但持仓上升": "价格回调但持仓增加",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def severity_cn(value: str) -> str:
    mapping = {
        "critical": "极高",
        "high": "高",
        "medium": "中",
        "low": "低",
        "sample": "样本",
    }
    return mapping.get(str(value or "").strip().lower(), str(value or "-"))


def load_local_secrets(env: dict, enabled: str) -> dict:
    if str(enabled).strip().lower() not in {"1", "true", "yes", "y"}:
        return env
    path = ROOT / "config" / "local_secrets.ps1"
    if not path.exists():
        return env
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for name in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_PUBLISH_CHAT_IDS"]:
        match = re.search(r"\$env:" + re.escape(name) + r"\s*=\s*['\"]([^'\"]+)['\"]", text)
        if match:
            env[name] = match.group(1).strip()
    return env


def run_long_short(output: Path, summary: Path) -> None:
    cmd = [
        sys.executable,
        "scripts/watch_binance_long_short_ratios.py",
        "--output",
        str(output),
        "--summary",
        str(summary),
        "--period",
        "1h",
        "--limit",
        "2",
    ]
    subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace", check=False, capture_output=True)


def run_market_state(output: Path, summary: Path, markdown_output: Path, long_short_output: Path) -> None:
    cmd = [
        sys.executable,
        "scripts/build_market_state_snapshot.py",
        "--output",
        str(output),
        "--summary",
        str(summary),
        "--markdown-output",
        str(markdown_output),
        "--long-short-input",
        str(long_short_output),
    ]
    subprocess.run(cmd, cwd=ROOT, text=True, check=False, capture_output=True)


def run_market_first_screen(output: Path, summary: Path, window_end_hour: int, window_hours: int) -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/events/prioritize_events.py",
            "--window-end-hour",
            str(window_end_hour),
            "--window-hours",
            str(window_hours),
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        capture_output=True,
    )
    subprocess.run([sys.executable, "scripts/reporting/generate_etf_summary.py"], cwd=ROOT, text=True, encoding="utf-8", errors="replace", check=False, capture_output=True)
    subprocess.run([sys.executable, "scripts/market/build_derivatives_history_percentiles.py"], cwd=ROOT, text=True, encoding="utf-8", errors="replace", check=False, capture_output=True)
    subprocess.run([sys.executable, "scripts/market/generate_percentile_alerts.py"], cwd=ROOT, text=True, encoding="utf-8", errors="replace", check=False, capture_output=True)
    subprocess.run([sys.executable, "scripts/reporting/generate_alert_headline.py"], cwd=ROOT, text=True, encoding="utf-8", errors="replace", check=False, capture_output=True)
    cmd = [
        sys.executable,
        "scripts/reporting/generate_market_state_summary.py",
        "--output",
        str(output),
        "--summary",
        str(summary),
    ]
    subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace", check=False, capture_output=True)


def latest_digest_sent(state_path: Path, digest_date: str, digest_label: str) -> bool:
    rows = read_rows(state_path)
    return any(
        str(row.get("digest_date_china", "")) == digest_date
        and str(row.get("digest_label", "")) == digest_label
        and str(row.get("status", "")) == "sent"
        for row in rows
    )


def append_digest_state(path: Path, row: dict) -> None:
    rows = read_rows(path)
    rows.append(row)
    write_rows(
        path,
        rows,
        ["sent_at_china", "digest_date_china", "digest_label", "telegram_chat_id", "telegram_message_id", "status", "error"],
    )


def top_rows(rows: list[dict], limit: int = 6) -> list[dict]:
    return sorted(rows, key=event_priority_score, reverse=True)[:limit]


def event_priority_score(row: dict) -> float:
    event_type = str(row.get("event_type") or "").strip()
    asset = str(row.get("asset_symbol") or "").strip().upper()
    source = str(row.get("source_type") or "").strip()
    text = str(row.get("alert_text") or "")
    amount = safe_float(row.get("amount_usd"))
    score = 0.0
    event_weights = {
        "stablecoin_flow": 8,
        "cex_netflow": 8,
        "whale_position": 7,
        "market_structure": 7,
        "hack_security": 10,
        "institutional_flow": 8,
        "token_unlock": 4,
        "funding_rate": 6,
        "liquidation": 7,
    }
    score += event_weights.get(event_type, 3)
    if asset in {"BTC", "ETH"}:
        score += 4
    elif asset in {"SOL", "BNB", "XRP", "DOGE"}:
        score += 2
    if amount >= 100_000_000:
        score += 4
    elif amount >= 10_000_000:
        score += 2
    if source in {"hyperliquid", "stablecoin_flow", "cex_netflow", "long_short"}:
        score += 1
    if any(key in text for key in ["静态大仓位", "静态背景", "未见明显变化"]):
        score -= 3
    return score


def is_today_focus_event(row: dict) -> bool:
    score = event_priority_score(row)
    event_type = str(row.get("event_type") or row.get("source_type") or "").strip()
    text = str(row.get("alert_text") or "")
    if score >= 8:
        return True
    if 6 <= score < 8:
        if event_type in {"market_structure", "funding_rate_extreme", "cex_netflow_extreme"}:
            return True
        if event_type == "token_unlock" and any(key in text for key in ["今日", "今天", "当日", "明日", "明天"]):
            return True
    return False


def summarize_sent(sent_rows: list[dict]) -> dict:
    return {
        "sent_count": len(sent_rows),
        "event_types": Counter(str(row.get("event_type", "") or "unknown") for row in sent_rows),
        "assets": Counter(str(row.get("asset_symbol", "") or "unknown") for row in sent_rows),
        "severity": Counter(str(row.get("severity_tier", "") or "unknown") for row in sent_rows),
        "sources": Counter(str(row.get("source_type", "") or "unknown") for row in sent_rows),
    }


def render_counter(counter: Counter, empty: str = "无") -> str:
    if not counter:
        return empty
    return "，".join(f"{key} {value}" for key, value in counter.most_common(4))


def evidence_lookup(rows: list[dict]) -> dict:
    lookup = {}
    for row in rows:
        alert_id = str(row.get("alert_id", "") or "").strip()
        if alert_id:
            lookup[alert_id] = row
        key = (
            str(row.get("asset_symbol", "") or "").strip().upper(),
            str(row.get("event_type", "") or "").strip(),
            str(row.get("source_type", "") or "").strip(),
        )
        if any(key):
            lookup[key] = row
    return lookup


def row_evidence(row: dict, lookup: dict) -> tuple[str, str]:
    found = lookup.get(str(row.get("alert_id", "") or "").strip())
    if not found:
        key = (
            str(row.get("asset_symbol", "") or "").strip().upper(),
            str(row.get("event_type", "") or "").strip(),
            str(row.get("source_type", "") or "").strip(),
        )
        found = lookup.get(key)
    if not found:
        return "", ""
    return str(found.get("evidence_snippet", "") or "").strip(), str(found.get("caution_snippet", "") or "").strip()


def render_long_short(rows: list[dict]) -> list[str]:
    ok_rows = [row for row in rows if str(row.get("quality_status", "")).lower() in {"ok", "partial"}]
    ok_rows = [
        row
        for row in ok_rows
        if safe_float(row.get("top_position_long_short_ratio")) >= 2.0
        or (0 < safe_float(row.get("top_position_long_short_ratio")) <= 0.5)
    ]
    ok_rows = sorted(ok_rows, key=lambda row: safe_float(row.get("crowding_score")), reverse=True)
    if not ok_rows:
        return ["- 暂无达到极端阈值的大户多空比结构。"]
    lines = []
    for row in ok_rows[:2]:
        asset = row.get("asset_symbol", "")
        pos = row.get("top_position_long_short_ratio", "")
        global_acc = row.get("global_account_long_short_ratio", "")
        taker = row.get("taker_buy_sell_ratio", "")
        bias = row.get("crowding_bias", "")
        if bias == "多头拥挤":
            plain = "多头集中度过高"
            explanation = "若价格反向波动，需警惕集中平仓。"
        elif bias == "空头拥挤":
            plain = "空头集中度过高"
            explanation = "若价格反向波动，需警惕集中回补。"
        else:
            plain = "多空结构相对均衡"
            explanation = "暂未看到明显单边集中。"
        lines.append(
            f"- {asset}: {plain}；大户仓位多空比 {pos or '-'}，全市场账户比 {global_acc or '-'}，主动买卖比 {taker or '-'}。{explanation}"
        )
    return lines


def render_digest_only_rows(rows: list[dict]) -> list[str]:
    if not rows:
        return ["- 暂无盘中转入早午晚报的静态背景。"]
    sorted_rows = sorted(rows, key=lambda row: safe_float(row.get("final_priority")), reverse=True)
    lines = []
    seen = set()
    for row in sorted_rows:
        key = str(row.get("item_key") or row.get("text") or "")
        if key in seen:
            continue
        seen.add(key)
        asset = row.get("asset", "") or "-"
        source = row.get("source_type", "") or "-"
        reason = row.get("decision_reason", "") or row.get("policy_reason_cn", "") or "静态背景，盘中降噪"
        text = compact_text(row.get("text", ""), 96)
        lines.append(f"- {asset}｜{source}｜{text}｜{compact_text(reason, 48)}")
        if len(lines) >= 5:
            break
    return lines or ["- 暂无盘中转入早午晚报的静态背景。"]


def latest_row(rows: list[dict]) -> dict:
    return rows[-1] if rows else {}


def signed_yi(value) -> str:
    number = safe_float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number / 100_000_000:.2f} 亿美元"


def amount_yi(value) -> str:
    number = safe_float(value)
    return f"{number / 100_000_000:.2f} 亿美元"


def bool_cn(value) -> str:
    return "是" if str(value).strip().lower() == "true" else "否"


def baseline_cn(value: str) -> str:
    mapping = {
        "ok": "完整基线",
        "partial_baseline_less_than_24h": "不足24小时基线",
        "missing_previous_snapshot": "暂无基线",
    }
    return mapping.get(str(value or ""), str(value or "-"))


def baseline_status_cn(value: str) -> str:
    mapping = {
        "ready": "可用",
        "needs_more_history": "样本不足",
        "beta_partial": "Beta",
        "missing": "缺失",
        "review": "需复查",
        "pass": "通过",
    }
    return mapping.get(str(value or ""), str(value or "-"))


def render_cex_baseline(summary: dict, pairs: list[dict]) -> list[str]:
    if not summary:
        return ["CEX净流｜暂无滚动基线，单笔大额暂不放大解释。"]
    if str(summary.get("status") or "") != "ready":
        return [
            "CEX净流｜"
            f"样本积累中，仅供背景参考；当前样本 {summary.get('baseline_rows','-')} 条，"
            f"可用交易所/资产对 {summary.get('ready_pairs','-')}/{summary.get('entity_asset_pairs','-')}。"
        ]
    lines = [
        "CEX净流｜"
        f"基线状态 {baseline_status_cn(summary.get('status'))}，"
        f"样本 {summary.get('baseline_rows','-')} 条，"
        f"可用交易所/资产对 {summary.get('ready_pairs','-')}/{summary.get('entity_asset_pairs','-')}，"
        f"最大样本 {summary.get('max_pair_samples','-')}/{summary.get('min_samples','-')}。"
    ]
    top = []
    for row in pairs[:3]:
        top.append(f"{row.get('entity','-')}-{row.get('asset_symbol','-')}:{row.get('sample_count','-')}条")
    if top:
        lines.append("CEX基线Top｜" + "；".join(top))
    return lines


def render_daily_context(
    digest_label: str,
    etf: dict,
    hyperliquid: dict,
    cex_summary: dict,
    cex_pairs: list[dict],
    hyperliquid_readiness: dict,
    liquidation_wall: dict,
) -> list[str]:
    lines = []
    if etf:
        lines.append(
            "ETF｜"
            f"{etf.get('latest_date','-')} 净流 {signed_yi(etf.get('latest_total_net_flow_usd'))}，"
            f"90日分位 {etf.get('abs_percentile_90d','-')}%，"
            f"阈值 {etf.get('adjusted_abs_percentile_threshold','-')} 分位，"
            f"月末/季末窗口 {bool_cn(etf.get('calendar_effect_window',''))}。"
        )
        top = str(etf.get("top_3_etf_by_share") or "").strip()
        if top:
            lines.append(f"ETF Top3｜{compact_text(top, 120)}")
    if hyperliquid and digest_label == "morning":
        lines.append(
            "Hyperliquid｜"
            f"监控仓位 {amount_yi(hyperliquid.get('total_position_value_usd'))}，"
            f"市场占比 {hyperliquid.get('market_share_pct','-')}%，"
            f"多空比 {hyperliquid.get('non_hype_long_short_ratio','-')}:1（不含HYPE），"
            f"含HYPE {hyperliquid.get('long_short_ratio','-')}:1，"
            f"HYPE占比 {hyperliquid.get('hype_position_share_pct','-')}%。"
        )
        lines.append(
            f"清算风险｜价格需反向变动 <10% 触发清算：{hyperliquid.get('near_liquidation_10pct_count','-')} 个；"
            f"基线：{baseline_cn(hyperliquid.get('baseline_status',''))}（{hyperliquid.get('baseline_age_hours','-')}h）。"
        )
    elif hyperliquid and safe_float(hyperliquid.get("near_liquidation_10pct_count")) > 0:
        lines.append(
            f"Hyperliquid清算风险｜价格需反向变动 <10% 触发清算：{hyperliquid.get('near_liquidation_10pct_count','-')} 个；"
            f"基线：{baseline_cn(hyperliquid.get('baseline_status',''))}。"
        )
    if liquidation_wall:
        radar_count = int(safe_float(liquidation_wall.get("radar_count")))
        digest_count = int(safe_float(liquidation_wall.get("digest_count")))
        if radar_count or digest_count:
            lines.append(
                "近爆仓墙｜"
                f"盘中雷达 {radar_count} 条，摘要关注 {digest_count} 条；"
                "口径为已监控 Hyperliquid 大户仓位。"
            )
        elif digest_label in {"morning", "evening"}:
            lines.append("近爆仓墙｜当前无 10% 内监控仓位，盘中不单独刷屏。")
    if hyperliquid_readiness:
        lines.append(
            "Hyperliquid就绪度｜"
            f"{baseline_status_cn(hyperliquid_readiness.get('readiness_status'))}；"
            f"{hyperliquid_readiness.get('digest_label','-')}；"
            f"{hyperliquid_readiness.get('next_action','-')}"
        )
    lines.extend(render_cex_baseline(cex_summary, cex_pairs))
    return [f"- {line}" for line in lines] if lines else ["- 暂无 ETF / Hyperliquid / CEX 日频背景。"]


def pct_cn(value) -> str:
    number = safe_float(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.2f}%"


def render_market_state(summary: dict, rows: list[dict]) -> list[str]:
    if not summary:
        return ["- 暂无市场状态快照。"]
    lines = [
        "市场概览｜"
        f"覆盖 {summary.get('ok_rows','-')}/{summary.get('watchlist_rows','-')} 个合约，"
        f"BTC 24h {pct_cn(summary.get('btc_price_change_pct_24h'))}，"
        f"ETH 24h {pct_cn(summary.get('eth_price_change_pct_24h'))}，"
        f"持仓合计 {amount_yi(summary.get('total_open_interest_usd'))}，"
        f"24h成交 {amount_yi(summary.get('total_quote_volume_usd_24h'))}。"
    ]
    top_price_asset = summary.get("top_price_move_asset", "")
    if top_price_asset:
        lines.append(
            "波动最大｜"
            f"{top_price_asset} 24h {pct_cn(summary.get('top_price_move_pct_24h'))}；"
            f"持仓变化最高 {summary.get('top_oi_change_asset','-')} {pct_cn(summary.get('top_oi_change_pct_24h'))}。"
        )
    if safe_float(summary.get("funding_extreme_count")) or safe_float(summary.get("crowding_extreme_count")):
        lines.append(
            "结构偏离｜"
            f"资金费率偏离 {summary.get('funding_extreme_count','0')} 个"
            f"（{summary.get('funding_extreme_assets','') or '-'}）；"
            f"多空拥挤 {summary.get('crowding_extreme_count','0')} 个"
            f"（{summary.get('crowding_extreme_assets','') or '-'}）。"
        )
    active_rows = sorted(
        [row for row in rows if str(row.get("quality_status", "")).lower() == "ok"],
        key=lambda row: (
            abs(safe_float(row.get("price_change_pct_24h"))),
            abs(safe_float(row.get("open_interest_change_pct_24h"))),
            abs(safe_float(row.get("funding_rate"))),
        ),
        reverse=True,
    )
    for row in active_rows[:3]:
        lines.append(
            "焦点资产｜"
            f"{row.get('asset_symbol','-')}：价格 {pct_cn(row.get('price_change_pct_24h'))}，"
            f"持仓 {pct_cn(row.get('open_interest_change_pct_24h'))}，"
            f"资金费率 {safe_float(row.get('funding_rate')) * 100:.4f}%；"
            f"{compact_text(row.get('market_state_reason',''), 60)}"
        )
    return [f"- {line}" for line in lines]


def render_market_first_screen(path: Path, fallback_summary: dict, fallback_rows: list[dict]) -> list[str]:
    if path.exists():
        text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
        if text:
            return [line if line.startswith("• ") else f"• {line}" for line in text.splitlines() if line.strip()]
    return render_market_state(fallback_summary, fallback_rows)


def render_percentile_watchlist(percentile_alerts: dict, limit: int = 2) -> list[str]:
    rows = []
    for item in percentile_alerts.get("watchlist_alerts", [])[:limit]:
        asset = str(item.get("asset_symbol") or "-").upper()
        percentile = item.get("percentile", "-")
        price_change_1h = pct_cn(item.get("price_change_pct_1h"))
        price_change = pct_cn(item.get("price_change_pct_24h"))
        interpretation = compact_text(str(item.get("interpretation") or ""), 90)
        alert_type = str(item.get("alert_type") or "percentile_alert")
        label = "资金费率分位" if alert_type == "funding_price_confirmation" else "结构分位"
        rows.append(f"- {asset}｜{label} {percentile}%｜1h {price_change_1h}｜24h {price_change}｜{interpretation}")
    return rows


def render_position_structure_risks(sent_rows: list[dict], evidence: dict, limit: int = 3) -> tuple[list[str], list[dict]]:
    ranked = sorted(sent_rows, key=event_priority_score, reverse=True)
    selected = [
        row
        for row in ranked
        if str(row.get("event_type") or row.get("source_type") or "").strip() in {"market_structure", "whale_position", "hyperliquid", "long_short"}
        and is_today_focus_event(row)
    ][:limit]
    lines = []
    for row in selected:
        event_type = row.get("event_type", "") or "unknown"
        asset = row.get("asset_symbol", "") or "-"
        severity = severity_cn(row.get("severity_tier", "") or "-")
        text = compact_text(user_text(row.get("alert_text", "")), 84)
        ev, caution = row_evidence(row, evidence)
        lines.append("- " + "｜".join([f"{asset}", f"{event_type}", f"置信 {severity}", text]))
        if ev:
            lines.append(f"  依据：{compact_text(ev, 110)}")
        if caution:
            lines.append(f"  提醒：{compact_text(caution, 70)}")
    return lines or ["- 该窗口没有达到阈值的持仓结构风险。"], selected


def title_for(label: str, override: str) -> str:
    if override.strip():
        return override.strip()
    return {
        "morning": "早间加密事件情报摘要",
        "noon": "午间加密事件情报摘要",
        "evening": "晚间加密事件情报摘要",
    }.get(label, "加密事件情报摘要")


def overview_heading(label: str) -> str:
    return {
        "morning": "昨夜概览",
        "noon": "上午概览",
        "evening": "日内概览",
    }.get(label, "窗口概览")


def source_quality_note(source_type: str) -> str:
    notes = {
        "hyperliquid": "仓位类信号优先看仓位变化、接近清算和资金费率，不把静态大仓位直接当结论。",
        "long_short": "多空比只表示拥挤结构，必须结合价格、成交和后续回看，不单独解释方向。",
        "token_unlock": "解锁是静态供给背景，盘中只保留临近或异常放大的项目，重复信息进入早午晚报。",
        "stablecoin_flow": "稳定币流动只表示资金迁移，需要结合交易所净流入/链上路径复核。",
        "cex_netflow": "交易所净流入需要滚动基线，否则单笔大额无法判断异常程度。",
    }
    return notes.get(source_type, "该来源仍在积累样本，暂不做强结论。")


def render_markdown(
    title: str,
    digest_label: str,
    start: datetime,
    end: datetime,
    sent_rows: list[dict],
    long_short_rows: list[dict],
    digest_only_rows: list[dict],
    followup_summary: dict,
    evidence_rows: list[dict],
    etf_context: dict,
    hyperliquid_context: dict,
    cex_summary: dict,
    cex_pairs: list[dict],
    hyperliquid_readiness: dict,
    liquidation_wall: dict,
    market_state_summary: dict,
    market_state_rows: list[dict],
    market_first_screen_path: Path,
    percentile_alerts: dict,
) -> str:
    stats = summarize_sent(sent_rows)
    severity_counter = Counter({severity_cn(key): value for key, value in stats["severity"].items()})
    evidence = evidence_lookup(evidence_rows)
    top_sources = [source for source, _ in stats["sources"].most_common(3)]
    lines = [
        f"# {title}",
        "",
        f"时间窗口：{china_iso(start)} 至 {china_iso(end)}",
        "",
        f"## {overview_heading(digest_label)}",
        "",
        f"- 已发布有效情报：{stats['sent_count']} 条",
        f"- 事件类型：{render_counter(stats['event_types'])}",
        f"- 相关资产：{render_counter(stats['assets'])}",
        f"- 置信分布：{render_counter(severity_counter)}",
        "",
        "## 市场状态",
        "",
        *render_market_first_screen(market_first_screen_path, market_state_summary, market_state_rows),
        "",
        "## 价格与费率异常",
        "",
    ]

    percentile_focus_lines = render_percentile_watchlist(percentile_alerts)
    if percentile_focus_lines:
        lines.extend(percentile_focus_lines)
    else:
        lines.append("- 该窗口没有达到阈值的价格/费率异常。")

    lines.extend(["", "## 持仓结构风险", ""])
    position_risk_lines, position_risk_rows = render_position_structure_risks(sent_rows, evidence)
    lines.extend(position_risk_lines)

    if sent_rows:
        ranked_sent_rows = sorted(sent_rows, key=event_priority_score, reverse=True)
        top_event_rows = [
            row
            for row in ranked_sent_rows
            if is_today_focus_event(row)
            and row not in position_risk_rows
            and str(row.get("event_type") or row.get("source_type") or "").strip() not in {"market_structure", "whale_position", "hyperliquid", "long_short"}
        ][:3]
        if top_event_rows:
            lines.extend(["", "## 事件关注", ""])
        for row in top_event_rows:
            event_type = row.get("event_type", "") or "unknown"
            asset = row.get("asset_symbol", "") or "-"
            amount = amount_cn(row.get("amount_usd"))
            severity = severity_cn(row.get("severity_tier", "") or "-")
            text = compact_text(user_text(row.get("alert_text", "")), 80)
            ev, caution = row_evidence(row, evidence)
            parts = [f"{asset}｜{event_type}", f"金额 {amount}", f"置信 {severity}", f"时间 {row.get('sent_at_china', '')}"]
            if text:
                parts.append(text)
            lines.append("- " + "｜".join(parts))
            if ev:
                lines.append(f"  依据：{compact_text(ev, 120)}")
            if caution:
                lines.append(f"  提醒：{compact_text(caution, 80)}")
        other_rows = [row for row in ranked_sent_rows if row not in top_event_rows and row not in position_risk_rows]
        if other_rows:
            lines.extend(["", "## 其他动态", ""])
            for row in top_rows(other_rows, 6):
                asset = row.get("asset_symbol", "") or "-"
                event_type = row.get("event_type", "") or "unknown"
                text = compact_text(user_text(row.get("alert_text", "")), 86)
                lines.append(f"- {asset}｜{event_type}｜{text}")

    lines.extend(
        [
            "",
            "## 结构信号",
            "",
            *render_long_short(long_short_rows),
            "",
            "## 日频背景",
            "",
            *render_daily_context(digest_label, etf_context, hyperliquid_context, cex_summary, cex_pairs, hyperliquid_readiness, liquidation_wall),
            "",
            "## 背景信息",
            "",
            *render_digest_only_rows(digest_only_rows),
            "",
            "## 质量回看",
            "",
            f"- 4h 可计算样本：{followup_summary.get('computable_4h_rows', '-')}",
            f"- 24h 可计算样本：{followup_summary.get('computable_24h_rows', '-')}",
            f"- follow-up 回填行数：{followup_summary.get('backfill_rows', '-')}",
            "",
            "## 来源质量提醒",
            "",
            *(f"- {source}：{source_quality_note(source)}" for source in top_sources),
            *([] if top_sources else ["- 暂无来源质量样本。"]),
            "",
            "## 说明",
            "",
            "- 这是事件情报和市场结构摘要，不构成任何交易建议。",
            "- 大户多空比来自公开衍生品市场数据，只表示仓位/账户结构，不代表方向结论。",
        ]
    )
    return "\n".join(lines) + "\n"


def markdown_to_tg_html(markdown: str) -> str:
    lines = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        if line.startswith("# "):
            lines.append(f"<b>{html.escape(line[2:])}</b>")
        elif line.startswith("## "):
            lines.append(f"\n<b>{html.escape(line[3:])}</b>")
        elif line.startswith("- "):
            lines.append("• " + html.escape(line[2:]))
        elif line.startswith("  "):
            lines.append("  " + html.escape(line.strip()))
        else:
            lines.append(html.escape(line))
    return "\n".join(lines).strip()


def send_message(token: str, chat_id: str, text: str) -> dict:
    session = requests.Session()
    session.trust_env = False
    response = session.post(
        TELEGRAM_API.format(token=token),
        json={"chat_id": chat_id, "text": text[:3900], "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=20,
    )
    payload = response.json()
    if response.status_code >= 300 or not payload.get("ok"):
        raise RuntimeError(f"telegram send failed: http={response.status_code}; body={str(payload)[:240]}")
    result = payload.get("result", {})
    return result if isinstance(result, dict) else {}


def main() -> int:
    args = parse_args()
    long_short_output = normalize_path(args.long_short_output)
    long_short_summary = normalize_path(args.long_short_summary)
    run_long_short(long_short_output, long_short_summary)
    market_state_output = normalize_path(args.market_state_output)
    market_state_summary_path = normalize_path(args.market_state_summary)
    market_state_markdown = normalize_path(args.market_state_markdown)
    market_first_screen = normalize_path(args.market_first_screen)
    market_first_screen_summary = normalize_path(args.market_first_screen_summary)
    run_market_state(market_state_output, market_state_summary_path, market_state_markdown, long_short_output)
    run_market_first_screen(market_first_screen, market_first_screen_summary, args.window_end_hour, args.window_hours)

    start, end = digest_window(args.window_end_hour, args.window_hours)
    digest_date = end.strftime("%Y-%m-%d")
    digest_title = title_for(args.digest_label, args.digest_title)
    ledger_rows = ledger_rows_in_window(read_rows(normalize_path(args.alert_ledger)), start, end)
    sent_rows = ledger_rows or rows_in_window(read_rows(normalize_path(args.sent_state)), "sent_at_china", start, end)
    long_short_rows = read_rows(long_short_output)
    digest_only_rows = decision_rows_in_window(read_rows(normalize_path(args.decision_log)), start, end)
    followup_rows = read_rows(normalize_path(args.followup_summary))
    followup_summary = followup_rows[-1] if followup_rows else {}
    evidence_rows = read_rows(normalize_path(args.evidence_snippets))
    etf_context = latest_row(read_rows(normalize_path(args.etf_context_summary)))
    hyperliquid_context = latest_row(read_rows(normalize_path(args.hyperliquid_context_summary)))
    cex_summary = latest_row(read_rows(normalize_path(args.cex_netflow_baseline_summary)))
    cex_pairs = read_rows(normalize_path(args.cex_netflow_baseline_by_pair))
    hyperliquid_readiness = latest_row(read_rows(normalize_path(args.hyperliquid_readiness)))
    liquidation_wall = latest_row(read_rows(normalize_path(args.hyperliquid_liquidation_wall_summary)))
    market_state_summary = latest_row(read_rows(market_state_summary_path))
    market_state_rows = read_rows(market_state_output)
    percentile_alerts = read_json(normalize_path(args.percentile_alerts))
    markdown = render_markdown(
        digest_title,
        args.digest_label,
        start,
        end,
        sent_rows,
        long_short_rows,
        digest_only_rows,
        followup_summary,
        evidence_rows,
        etf_context,
        hyperliquid_context,
        cex_summary,
        cex_pairs,
        hyperliquid_readiness,
        liquidation_wall,
        market_state_summary,
        market_state_rows,
        market_first_screen,
        percentile_alerts,
    )

    output_path = normalize_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    summary = {
        "generated_at_china": china_iso(china_now()),
        "digest_label": args.digest_label,
        "window_start_china": china_iso(start),
        "window_end_china": china_iso(end),
        "sent_rows_in_window": len(sent_rows),
        "ledger_rows_in_window": len(ledger_rows),
        "long_short_rows": len(long_short_rows),
        "digest_only_rows": len(digest_only_rows),
        "evidence_rows": len(evidence_rows),
        "etf_context_loaded": "true" if etf_context else "false",
        "hyperliquid_context_loaded": "true" if hyperliquid_context else "false",
        "cex_baseline_loaded": "true" if cex_summary else "false",
        "hyperliquid_readiness_loaded": "true" if hyperliquid_readiness else "false",
        "hyperliquid_liquidation_wall_loaded": "true" if liquidation_wall else "false",
        "market_state_loaded": "true" if market_state_summary else "false",
        "market_state_rows": len(market_state_rows),
        "market_first_screen_loaded": "true" if market_first_screen.exists() else "false",
        "percentile_watchlist_count": len(percentile_alerts.get("watchlist_alerts", [])) if percentile_alerts else 0,
        "send_mode": "send" if args.send else "dry_run",
        "status": "pass",
        "message": "ok",
    }

    if args.send:
        env = load_local_secrets(os.environ.copy(), args.load_local_secrets)
        token = env.get(args.token_env, "").strip()
        chat_id = env.get(args.chat_id_env, "").strip()
        state_path = normalize_path(args.sent_digest_state)
        if latest_digest_sent(state_path, digest_date, args.digest_label) and not args.force:
            summary["status"] = "skipped"
            summary["message"] = "digest_already_sent"
        elif not token or not chat_id:
            summary["status"] = "fail"
            summary["message"] = "missing_telegram_env"
        else:
            try:
                result = send_message(token, chat_id, markdown_to_tg_html(markdown))
                result_chat = result.get("chat", {}) if isinstance(result.get("chat", {}), dict) else {}
                append_digest_state(
                    state_path,
                    {
                        "sent_at_china": china_iso(china_now()),
                        "digest_date_china": digest_date,
                        "digest_label": args.digest_label,
                        "telegram_chat_id": str(result_chat.get("id", "") or chat_id),
                        "telegram_message_id": str(result.get("message_id", "") or ""),
                        "status": "sent",
                        "error": "",
                    },
                )
            except Exception as exc:
                summary["status"] = "fail"
                summary["message"] = str(exc)[:240]

    write_rows(
        normalize_path(args.summary),
        [summary],
        [
            "generated_at_china",
            "digest_label",
            "window_start_china",
            "window_end_china",
            "sent_rows_in_window",
            "ledger_rows_in_window",
            "long_short_rows",
            "digest_only_rows",
            "evidence_rows",
            "etf_context_loaded",
            "hyperliquid_context_loaded",
            "cex_baseline_loaded",
            "hyperliquid_readiness_loaded",
            "hyperliquid_liquidation_wall_loaded",
            "market_state_loaded",
            "market_state_rows",
            "market_first_screen_loaded",
            "percentile_watchlist_count",
            "send_mode",
            "status",
            "message",
        ],
    )

    print(f"digest_label={args.digest_label}")
    print(f"sent_rows_in_window={len(sent_rows)}")
    print(f"long_short_rows={len(long_short_rows)}")
    print(f"evidence_rows={len(evidence_rows)}")
    print(f"status={summary['status']}")
    print(f"wrote_output={output_path}")
    return 0 if summary["status"] in {"pass", "skipped"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
