import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HORIZONS = ["1h", "4h", "24h", "72h"]


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


SUMMARY_COLUMNS = [
    "status",
    "generated_at_china",
    "outcome_rows",
    "published_rows",
    "skipped_rows",
    "partial_rows",
    "ok_rows",
    "computed_1h",
    "computed_4h",
    "computed_24h",
    "computed_72h",
    "best_event_type_24h",
    "worst_event_type_24h",
    "output",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Chinese TG alert quality report from evaluated outcomes.")
    parser.add_argument("--input", default=str(ROOT / "data" / "tg_alert_outcomes.csv"))
    parser.add_argument("--ledger", default=str(ROOT / "data" / "tg_alert_ledger.csv"))
    parser.add_argument("--hypothesis-registry", default=str(ROOT / "data" / "event_hypothesis_registry.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "tg_alert_quality_daily.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_alert_quality_daily_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_stamp() -> str:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


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


def safe_float(value) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return math.nan


def pct(value: float) -> str:
    if math.isnan(value):
        return "-"
    return f"{value * 100:.2f}%"


def avg(values: list[float]) -> float:
    clean = [value for value in values if not math.isnan(value)]
    if not clean:
        return math.nan
    return sum(clean) / len(clean)


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return ["暂无数据。"]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def group_metric(rows: list[dict], group_key: str, horizon: str) -> list[list[str]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        key = str(row.get(group_key) or "unknown")
        value = safe_float(row.get(f"abnormal_primary_{horizon}"))
        if not math.isnan(value):
            grouped[key].append(value)
    result = []
    for key, values in sorted(grouped.items(), key=lambda item: avg(item[1]), reverse=True):
        win_rate = sum(1 for value in values if value > 0) / len(values)
        result.append([key, str(len(values)), pct(avg(values)), pct(win_rate)])
    return result


def best_worst_event_type(rows: list[dict], horizon: str) -> tuple[str, str]:
    metrics = group_metric(rows, "event_subtype", horizon)
    if not metrics:
        return "", ""
    return metrics[0][0], metrics[-1][0]


def top_events(rows: list[dict], horizon: str, reverse: bool, limit: int = 5) -> list[list[str]]:
    usable = []
    for row in rows:
        value = safe_float(row.get(f"abnormal_primary_{horizon}"))
        if not math.isnan(value):
            usable.append((value, row))
    usable.sort(key=lambda item: item[0], reverse=reverse)
    out = []
    for value, row in usable[:limit]:
        text = str(row.get("alert_text") or "").replace("\n", " / ")
        if len(text) > 44:
            text = text[:41] + "..."
        out.append([pct(value), row.get("asset_symbol", ""), row.get("event_subtype", ""), text])
    return out


def count_by(rows: list[dict], key: str) -> list[list[str]]:
    counts = Counter(str(row.get(key) or "unknown") for row in rows)
    return [[name, str(count)] for name, count in counts.most_common()]


def hypothesis_rows(outcome_rows: list[dict], registry_rows: list[dict]) -> list[list[str]]:
    present = Counter(str(row.get("event_subtype") or "unknown") for row in outcome_rows)
    registry = {str(row.get("event_subtype") or ""): row for row in registry_rows}
    rows = []
    for subtype, count in present.most_common():
        item = registry.get(subtype, {})
        hypothesis = str(item.get("hypothesis_cn") or "未登记").replace("|", "｜")
        if len(hypothesis) > 54:
            hypothesis = hypothesis[:51] + "..."
        rows.append([subtype, str(count), str(item.get("tg_priority") or "-"), hypothesis])
    return rows


def main() -> int:
    args = parse_args()
    outcome_rows = read_rows(normalize_path(args.input))
    ledger_rows = read_rows(normalize_path(args.ledger))
    registry_rows = read_rows(normalize_path(args.hypothesis_registry))
    status_counts = Counter(row.get("quality_status", "") for row in outcome_rows)
    computed_counts = {
        horizon: sum(1 for row in outcome_rows if str(row.get(f"abnormal_primary_{horizon}") or "").strip())
        for horizon in HORIZONS
    }
    event_type_24_best, event_type_24_worst = best_worst_event_type(outcome_rows, "24h")

    lines = [
        "# TG 情报质量日报",
        "",
        f"- 生成时间：{china_stamp()}",
        f"- 情报账本总数：{len(ledger_rows)}",
        f"- 已评价记录：{len(outcome_rows)}",
        "",
        "## 总览",
        "",
        f"- 完整评价：{status_counts.get('ok', 0)}",
        f"- 部分评价：{status_counts.get('partial', 0)}",
        f"- 跳过/错误：{status_counts.get('skipped', 0) + status_counts.get('error', 0)}",
        f"- 1h 可计算：{computed_counts['1h']}",
        f"- 4h 可计算：{computed_counts['4h']}",
        f"- 24h 可计算：{computed_counts['24h']}",
        f"- 72h 可计算：{computed_counts['72h']}",
        "",
        "## 样本结构",
        "",
        *table(["事件子类型", "数量"], count_by(outcome_rows, "event_subtype")),
        "",
        "## 当前样本对应的事件假设",
        "",
        *table(["事件子类型", "数量", "TG优先级", "待验证假设"], hypothesis_rows(outcome_rows, registry_rows)),
        "",
        "## 按事件子类型看 4h 主 benchmark 异常收益",
        "",
        *table(["事件子类型", "样本数", "平均异常收益", "正收益比例"], group_metric(outcome_rows, "event_subtype", "4h")),
        "",
        "## 按事件子类型看 24h 主 benchmark 异常收益",
        "",
        *table(["事件子类型", "样本数", "平均异常收益", "正收益比例"], group_metric(outcome_rows, "event_subtype", "24h")),
        "",
        "## 按是否提前反应看 4h",
        "",
        *table(["提前反应状态", "样本数", "平均异常收益", "正收益比例"], group_metric(outcome_rows, "priced_in_flag", "4h")),
        "",
        "## 按 BTC 14日趋势看 4h",
        "",
        *table(["市场趋势", "样本数", "平均异常收益", "正收益比例"], group_metric(outcome_rows, "btc_regime_trend_14d", "4h")),
        "",
        "## 按 BTC 7日波动看 4h",
        "",
        *table(["波动状态", "样本数", "平均异常收益", "正收益比例"], group_metric(outcome_rows, "btc_regime_vol_7d", "4h")),
        "",
        "## 24h 表现最好事件",
        "",
        *table(["异常收益", "资产", "子类型", "内容"], top_events(outcome_rows, "24h", True)),
        "",
        "## 24h 表现最差事件",
        "",
        *table(["异常收益", "资产", "子类型", "内容"], top_events(outcome_rows, "24h", False)),
        "",
        "## 读法",
        "",
        "- 主 benchmark 会按资产自动选择：BTC 事件默认相对 ETH；ETH 和小币默认相对 BTC。",
        "- `partial` 通常表示情报太新，4h/24h/72h 还没到。",
        "- `priced_in_flag` 用来识别发布前是否已经明显反应，避免把滞后快讯误当有效信号。",
        "- BTC 市场趋势和波动状态用于粗分市场环境，后续会验证哪些事件类型只在特定环境有效。",
        "- 本报告只用于市场结构观察和研究复盘，不构成任何交易建议。",
        "",
    ]
    output_path = normalize_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "status": "pass",
        "generated_at_china": china_stamp(),
        "outcome_rows": str(len(outcome_rows)),
        "published_rows": str(len(ledger_rows)),
        "skipped_rows": str(status_counts.get("skipped", 0) + status_counts.get("error", 0)),
        "partial_rows": str(status_counts.get("partial", 0)),
        "ok_rows": str(status_counts.get("ok", 0)),
        "computed_1h": str(computed_counts["1h"]),
        "computed_4h": str(computed_counts["4h"]),
        "computed_24h": str(computed_counts["24h"]),
        "computed_72h": str(computed_counts["72h"]),
        "best_event_type_24h": event_type_24_best,
        "worst_event_type_24h": event_type_24_worst,
        "output": str(output_path),
    }
    write_rows(normalize_path(args.summary), [summary], SUMMARY_COLUMNS)
    print(f"wrote TG alert quality report to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
