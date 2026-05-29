import argparse
import csv
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CN_TZ = timezone(timedelta(hours=8))


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


COLUMNS = [
    "priority_rank",
    "priority_bucket",
    "priority_score",
    "asset_symbol",
    "event_type",
    "source_type",
    "sent_at_china",
    "amount_usd",
    "confidence",
    "title",
    "priority_reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prioritize TG digest events into top-watch and other-dynamic buckets.")
    parser.add_argument("--alert-ledger", default=str(ROOT / "data" / "tg_alert_ledger.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_prioritized_events.csv"))
    parser.add_argument("--today-focus-output", default=str(ROOT / "results" / "v14_today_focus_events.csv"))
    parser.add_argument("--other-events-output", default=str(ROOT / "results" / "v14_other_events.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_prioritized_events.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_prioritized_events_summary.csv"))
    parser.add_argument("--window-end-hour", type=int, default=20)
    parser.add_argument("--window-hours", type=int, default=8)
    parser.add_argument("--top-limit", type=int, default=3)
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


def china_now() -> datetime:
    return datetime.now(CN_TZ).replace(microsecond=0)


def china_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC+8")


def digest_window(end_hour: int, hours: int) -> tuple[datetime, datetime]:
    now = china_now()
    end = now.replace(hour=max(0, min(23, end_hour)), minute=0, second=0, microsecond=0)
    if now < end:
        end -= timedelta(days=1)
    return end - timedelta(hours=max(1, hours)), end


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


def safe_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def compact(value: str, limit: int = 90) -> str:
    text = " ".join(str(value or "").split())
    return text[: limit - 1] + "…" if len(text) > limit else text


def user_text(value: str) -> str:
    text = str(value or "")
    for old, new in {
        "多头拥挤": "多头集中度过高",
        "空头拥挤": "空头集中度过高",
        "资金费率偏离": "资金费率异常",
        "价格下跌但持仓上升": "价格回调但持仓增加",
    }.items():
        text = text.replace(old, new)
    return text


def priority(row: dict) -> tuple[float, str]:
    event_type = str(row.get("event_type") or row.get("source_type") or "").strip()
    asset = str(row.get("asset_symbol") or "").strip().upper()
    source = str(row.get("source_type") or "").strip()
    amount = safe_float(row.get("magnitude_usd") or row.get("amount_usd"))
    text = str(row.get("alert_text") or "")
    score = 0.0
    reasons = []
    event_weights = {
        "hack_security": 10,
        "stablecoin_flow": 8,
        "cex_netflow": 8,
        "institutional_flow": 8,
        "whale_position": 7,
        "market_structure": 7,
        "liquidation": 7,
        "funding_rate": 6,
        "token_unlock": 4,
    }
    weight = event_weights.get(event_type, 3)
    score += weight
    reasons.append(f"事件类型+{weight}")
    if asset in {"BTC", "ETH"}:
        score += 4
        reasons.append("核心资产+4")
    elif asset in {"SOL", "BNB", "XRP", "DOGE"}:
        score += 2
        reasons.append("主流资产+2")
    if amount >= 100_000_000:
        score += 4
        reasons.append("金额过亿+4")
    elif amount >= 10_000_000:
        score += 2
        reasons.append("金额过千万+2")
    if source in {"hyperliquid", "stablecoin_flow", "cex_netflow", "long_short"}:
        score += 1
        reasons.append("结构化来源+1")
    if any(key in text for key in ["静态大仓位", "静态背景", "未见明显变化"]):
        score -= 3
        reasons.append("静态信息-3")
    return score, ";".join(reasons)


def is_today_focus(score: float, row: dict) -> bool:
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


def render_markdown(rows: list[dict], start: datetime, end: datetime, top_limit: int) -> str:
    top = [row for row in rows if row["priority_bucket"] == "top_watch"]
    other = [row for row in rows if row["priority_bucket"] == "other_dynamic"]
    lines = [
        "# v14 事件优先级审计",
        "",
        f"- 时间窗口：{china_iso(start)} 至 {china_iso(end)}",
        f"- 今日最值得关注：{len(top)} 条",
        f"- 其他动态：{len(other)} 条",
        "",
        "## 今日最值得关注",
    ]
    if not top:
        lines.append("- 暂无。")
    for row in top[:top_limit]:
        lines.append(f"- {row['asset_symbol']}｜{row['event_type']}｜分数 {row['priority_score']}｜{row['title']}")
    lines.extend(["", "## 其他动态"])
    if not other:
        lines.append("- 暂无。")
    for row in other[:10]:
        lines.append(f"- {row['asset_symbol']}｜{row['event_type']}｜分数 {row['priority_score']}｜{row['title']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    start, end = digest_window(args.window_end_hour, args.window_hours)
    candidates = []
    for row in read_rows(normalize_path(args.alert_ledger)):
        if str(row.get("send_status", "") or "").strip() not in {"sent", "dry_run"}:
            continue
        dt = parse_china_time(str(row.get("published_at_china") or row.get("created_at_china") or ""))
        if not dt or not (start <= dt < end):
            continue
        score, reason = priority(row)
        candidates.append((score, reason, row))
    candidates.sort(key=lambda item: item[0], reverse=True)
    output = []
    focus_seen = 0
    for index, (score, reason, row) in enumerate(candidates, start=1):
        focus = is_today_focus(score, row) and focus_seen < args.top_limit
        if focus:
            focus_seen += 1
        bucket = "top_watch" if focus else "other_dynamic"
        output.append(
            {
                "priority_rank": index,
                "priority_bucket": bucket,
                "priority_score": f"{score:.2f}",
                "asset_symbol": row.get("asset_symbol") or "",
                "event_type": row.get("event_type") or row.get("source_type") or "unknown",
                "source_type": row.get("source_type") or "",
                "sent_at_china": row.get("published_at_china") or row.get("created_at_china") or "",
                "amount_usd": row.get("magnitude_usd") or row.get("amount_usd") or "",
                "confidence": row.get("confidence_bucket") or "",
                "title": compact(user_text(row.get("alert_text") or "")),
                "priority_reason": reason,
            }
        )
    write_rows(normalize_path(args.output), output, COLUMNS)
    write_rows(normalize_path(args.today_focus_output), [row for row in output if row["priority_bucket"] == "top_watch"], COLUMNS)
    write_rows(normalize_path(args.other_events_output), [row for row in output if row["priority_bucket"] == "other_dynamic"], COLUMNS)
    normalize_path(args.markdown_output).write_text(render_markdown(output, start, end, args.top_limit), encoding="utf-8")
    counts = Counter(row["priority_bucket"] for row in output)
    summary = {
        "window_start_china": china_iso(start),
        "window_end_china": china_iso(end),
        "input_rows": len(output),
        "top_watch_count": counts.get("top_watch", 0),
        "other_dynamic_count": counts.get("other_dynamic", 0),
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"prioritized_rows={len(output)} top_watch={summary['top_watch_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
