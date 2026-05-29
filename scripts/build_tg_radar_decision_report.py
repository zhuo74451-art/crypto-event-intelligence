import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


DECISION_CN = {
    "selected": "已进入盘中雷达",
    "filtered_digest_only": "静态背景转早晚报",
    "suppressed_cooldown": "冷却期内不重复发",
    "not_selected_capacity": "名额不足未入选",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a readable report from tg_radar_decision_log.csv.")
    parser.add_argument("--decision-log", default=str(ROOT / "data" / "tg_radar_decision_log.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "tg_radar_decision_report.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_radar_decision_report_summary.csv"))
    parser.add_argument("--lookback-hours", type=float, default=24)
    parser.add_argument("--top-n", type=int, default=12)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_now() -> datetime:
    return datetime.now(CHINA_TZ).replace(microsecond=0)


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_china_time(value: str) -> datetime | None:
    text = (value or "").strip().replace(" UTC+8", "")
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=CHINA_TZ)
        except ValueError:
            pass
    return None


def to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def count_by(rows: list[dict], field: str) -> Counter:
    return Counter((row.get(field) or "unknown").strip() or "unknown" for row in rows)


def compact_text(text: str, limit: int = 120) -> str:
    one_line = " ".join((text or "").replace("\r", "\n").split())
    return one_line[: limit - 1] + "…" if len(one_line) > limit else one_line


def format_count_lines(counter: Counter, label_map: dict[str, str] | None = None) -> list[str]:
    lines = []
    for key, count in counter.most_common():
        label = label_map.get(key, key) if label_map else key
        lines.append(f"- {label}: {count}")
    return lines or ["- 无"]


def make_tuning_notes(rows: list[dict], decision_counts: Counter, policy_counts: Counter) -> list[str]:
    notes = []
    total = max(len(rows), 1)
    cooldown_ratio = decision_counts.get("suppressed_cooldown", 0) / total
    digest_ratio = decision_counts.get("filtered_digest_only", 0) / total
    capacity_ratio = decision_counts.get("not_selected_capacity", 0) / total
    selected_ratio = decision_counts.get("selected", 0) / total

    if selected_ratio == 0 and rows:
        notes.append("本轮没有新内容进入盘中雷达，优先检查冷却期、静态背景过滤和候选源数量。")
    if cooldown_ratio >= 0.35:
        notes.append("冷却过滤占比较高，说明去重在生效；只有当漏掉明显新变化时，才需要缩短冷却。")
    if digest_ratio >= 0.25 or policy_counts.get("digest_only", 0) >= 2:
        notes.append("静态背景被转入早晚报，符合盘中雷达要减少重复背景噪音的方向。")
    if capacity_ratio >= 0.25:
        notes.append("名额不足未入选较多，后续应优先提高强动态信号权重，而不是简单扩大版面。")
    if policy_counts.get("downrank", 0) >= 2:
        notes.append("历史/实时表现较弱的重复类型已被降权，后续要观察是否误伤高质量突发。")
    if not notes:
        notes.append("本轮决策结构正常，继续积累样本后再调整权重。")
    return notes


def build_report(rows: list[dict], args: argparse.Namespace) -> tuple[str, dict]:
    now = china_now()
    cutoff = now - timedelta(hours=args.lookback_hours)
    scoped = []
    for row in rows:
        parsed = parse_china_time(row.get("decided_at_china", ""))
        if parsed is None or parsed >= cutoff:
            scoped.append(row)

    decision_counts = count_by(scoped, "decision")
    source_counts = count_by(scoped, "source_type")
    policy_counts = count_by(scoped, "policy_action")
    repeat_counts = count_by(scoped, "repeat_group")

    by_decision: dict[str, list[dict]] = defaultdict(list)
    for row in scoped:
        by_decision[(row.get("decision") or "unknown").strip() or "unknown"].append(row)

    def sort_key(row: dict) -> float:
        return to_float(row.get("final_priority", "0"))

    lines = [
        "# 盘中雷达决策报表",
        "",
        f"- 生成时间: {now.strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
        f"- 统计窗口: 最近 {args.lookback_hours:g} 小时",
        f"- 候选决策数: {len(scoped)}",
        "",
        "## 决策分布",
        *format_count_lines(decision_counts, DECISION_CN),
        "",
        "## 来源分布",
        *format_count_lines(source_counts),
        "",
        "## 策略动作分布",
        *format_count_lines(policy_counts),
        "",
        "## 重复类型分布",
        *format_count_lines(repeat_counts),
        "",
        "## 被过滤/降噪的重点候选",
    ]

    filtered = [
        row
        for row in scoped
        if (row.get("decision") or "") in {"filtered_digest_only", "suppressed_cooldown", "not_selected_capacity"}
    ]
    filtered = sorted(filtered, key=sort_key, reverse=True)[: args.top_n]
    if not filtered:
        lines.append("- 无")
    else:
        for idx, row in enumerate(filtered, start=1):
            decision = row.get("decision") or "unknown"
            reason_parts = [
                row.get("decision_reason") or "",
                row.get("policy_reason_cn") or "",
                row.get("dynamic_boost_reason") or "",
            ]
            reason = "；".join(part for part in reason_parts if part).strip("；") or "未记录原因"
            asset = row.get("asset") or "UNKNOWN"
            source = row.get("source_type") or "unknown"
            priority = row.get("final_priority") or ""
            lines.append(
                f"{idx}. [{DECISION_CN.get(decision, decision)}] {asset} / {source} / 优先级 {priority} - {compact_text(row.get('text', ''))}"
            )
            lines.append(f"   - 原因: {compact_text(reason, 160)}")

    selected = sorted(by_decision.get("selected", []), key=sort_key, reverse=True)[: args.top_n]
    lines.extend(["", "## 本轮进入雷达的候选"])
    if not selected:
        lines.append("- 无")
    else:
        for idx, row in enumerate(selected, start=1):
            asset = row.get("asset") or "UNKNOWN"
            source = row.get("source_type") or "unknown"
            priority = row.get("final_priority") or ""
            lines.append(f"{idx}. {asset} / {source} / 优先级 {priority} - {compact_text(row.get('text', ''))}")

    lines.extend(["", "## 调参观察", *[f"- {note}" for note in make_tuning_notes(scoped, decision_counts, policy_counts)]])
    lines.extend(["", "提示: 本报表只用于解释信息筛选与降噪，不构成任何交易建议。", ""])

    summary = {
        "status": "ok",
        "generated_at_china": now.strftime("%Y-%m-%d %H:%M:%S UTC+8"),
        "lookback_hours": args.lookback_hours,
        "decision_rows": len(scoped),
        "selected_count": decision_counts.get("selected", 0),
        "filtered_digest_only_count": decision_counts.get("filtered_digest_only", 0),
        "suppressed_cooldown_count": decision_counts.get("suppressed_cooldown", 0),
        "not_selected_capacity_count": decision_counts.get("not_selected_capacity", 0),
        "unknown_decision_count": decision_counts.get("unknown", 0),
        "source_type_count": len(source_counts),
        "policy_action_count": len(policy_counts),
        "top_source_type": source_counts.most_common(1)[0][0] if source_counts else "",
        "top_policy_action": policy_counts.most_common(1)[0][0] if policy_counts else "",
    }
    return "\n".join(lines), summary


def write_summary(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)


def main() -> int:
    args = parse_args()
    decision_log = normalize_path(args.decision_log)
    output = normalize_path(args.output)
    summary_path = normalize_path(args.summary)

    rows = read_rows(decision_log)
    report, summary = build_report(rows, args)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    summary["output"] = str(output)
    summary["decision_log"] = str(decision_log)
    write_summary(summary_path, summary)
    print(f"wrote decision report to {output}")
    print(f"wrote summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
