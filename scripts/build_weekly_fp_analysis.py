import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build weekly false-positive/false-negative analysis from offline validation monitors.")
    parser.add_argument("--monitor", default=str(ROOT / "results" / "v14_false_positive_monitor_summary.csv"))
    parser.add_argument("--by-reason", default=str(ROOT / "results" / "v14_false_positive_monitor_by_reason.csv"))
    parser.add_argument("--fn-review", default=str(ROOT / "results" / "v14_false_negative_case_review.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_weekly_fp_analysis.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_weekly_fp_analysis_summary.csv"))
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


def write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def safe_float_pct(value: str) -> float:
    text = str(value or "").strip().replace("%", "")
    try:
        return float(text)
    except Exception:
        return 0.0


def render(summary: dict, by_reason: list[dict], fn_rows: list[dict]) -> str:
    lines = [
        "# v14 Weekly FP/FN Analysis",
        "",
        f"生成时间：中国时间 {summary['generated_at_china']}",
        "",
        "## 指标",
        "",
        f"- FP率：{summary['false_positive_rate']}（目标 {summary['target_false_positive_rate']}）",
        f"- FN率：{summary['false_negative_rate']}（目标 {summary['target_false_negative_rate']}）",
        f"- Precision：{summary['precision']}（目标 {summary['target_precision']}）",
        f"- Recall：{summary['recall']}（目标 {summary['target_recall']}）",
        f"- 状态：{summary['analysis_status']}",
        "",
        "## 误判原因",
        "",
        "| type | reason | count | next action |",
        "|---|---|---:|---|",
    ]
    for row in by_reason:
        reason = row.get("reason", "")
        action = "补充识别规则" if row.get("error_type") == "false_positive" else "补充交叉验证证据"
        lines.append(f"| {row.get('error_type','')} | {reason} | {row.get('count','')} | {action} |")
    lines.extend(["", "## FN复查结论", ""])
    for row in fn_rows:
        lines.append(f"- {row.get('event_id','')}：{row.get('review_action','')}｜{row.get('evidence_requirement','')}｜{row.get('title','')}")
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "- 不直接放宽 source_basis。",
            "- 先增加结构化证据字段和交叉验证来源，再决定是否提高 Recall。",
            "- FP 目标小于 5%，当前未达标时保持 review，不进入正式放量。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    monitor = (read_rows(normalize_path(args.monitor)) or [{}])[-1]
    by_reason = read_rows(normalize_path(args.by_reason))
    fn_rows = read_rows(normalize_path(args.fn_review))
    fp_rate = safe_float_pct(monitor.get("false_positive_rate"))
    fn_rate = safe_float_pct(monitor.get("false_negative_rate"))
    precision = float(monitor.get("precision") or 0)
    recall = float(monitor.get("recall") or 0)
    analysis_status = "pass" if fp_rate < 5 and fn_rate < 10 and precision >= 0.85 and recall >= 0.85 else "review"
    summary = {
        "generated_at_china": china_stamp(),
        "false_positive_rate": monitor.get("false_positive_rate", ""),
        "false_negative_rate": monitor.get("false_negative_rate", ""),
        "precision": monitor.get("precision", ""),
        "recall": monitor.get("recall", ""),
        "target_false_positive_rate": monitor.get("target_false_positive_rate", "<5%"),
        "target_false_negative_rate": monitor.get("target_false_negative_rate", "<10%"),
        "target_precision": monitor.get("target_precision", ">=0.8500"),
        "target_recall": monitor.get("target_recall", ">=0.8500"),
        "fn_review_rows": len(fn_rows),
        "reason_rows": len(by_reason),
        "analysis_status": analysis_status,
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    normalize_path(args.output).write_text(render(summary, by_reason, fn_rows), encoding="utf-8")
    print(f"analysis_status={analysis_status}")
    print(f"fn_review_rows={len(fn_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
