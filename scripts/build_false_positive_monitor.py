import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build offline false-positive/false-negative monitor from adversarial validation.")
    parser.add_argument("--input", default=str(ROOT / "results" / "v14_adversarial_golden_validation.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_false_positive_monitor.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_false_positive_monitor_summary.csv"))
    parser.add_argument("--md-output", default=str(ROOT / "results" / "v14_false_positive_monitor.md"))
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


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() == "true"


def classify_error(row: dict) -> str:
    expected = truthy(row.get("expected_publishable"))
    actual = truthy(row.get("actual_publishable"))
    if expected and actual:
        return "true_positive"
    if (not expected) and (not actual):
        return "true_negative"
    if (not expected) and actual:
        return "false_positive"
    return "false_negative"


def error_reason(row: dict, error_type: str) -> str:
    conflict = str(row.get("conflict_type") or "").strip()
    block = str(row.get("criteria_block_reason") or "").strip()
    observable = str(row.get("observable_impact_type") or "").strip()
    if error_type == "false_positive":
        return conflict or observable or "unknown_false_positive"
    if error_type == "false_negative":
        return block or "unknown_false_negative"
    return "ok"


def render_md(rows: list[dict], summary: dict, by_reason: list[dict]) -> str:
    lines = [
        "# v14 False Positive Monitor",
        "",
        f"生成时间：中国时间 {summary['generated_at_china']}",
        "",
        "## 总览",
        "",
        f"- 样本数：{summary['sample_count']}",
        f"- 假阳性：{summary['false_positive_count']}（{summary['false_positive_rate']}）",
        f"- 假阴性：{summary['false_negative_count']}（{summary['false_negative_rate']}）",
        f"- Precision：{summary['precision']}",
        f"- Recall：{summary['recall']}",
        f"- 状态：{summary['status']}",
        "",
        "## 主要误判原因",
        "",
        "| type | reason | count |",
        "|---|---|---:|",
    ]
    for row in by_reason:
        lines.append(f"| {row['error_type']} | {row['reason']} | {row['count']} |")
    lines.extend(["", "## 待优先查看样本", ""])
    for row in rows:
        if row["error_type"] in {"false_positive", "false_negative"}:
            lines.append(f"- {row['error_type']}｜{row['event_id']}｜{row['reason']}｜{row.get('title','')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    source_rows = read_rows(normalize_path(args.input))
    output = []
    counts = Counter()
    reason_counts = Counter()
    for row in source_rows:
        err = classify_error(row)
        reason = error_reason(row, err)
        counts[err] += 1
        if err in {"false_positive", "false_negative"}:
            reason_counts[(err, reason)] += 1
        output.append(
            {
                "event_id": row.get("event_id", ""),
                "error_type": err,
                "reason": reason,
                "event_subtype": row.get("event_subtype", ""),
                "source_tier": row.get("source_tier", ""),
                "observable_impact_type": row.get("observable_impact_type", ""),
                "conflict_type": row.get("conflict_type", ""),
                "criteria_block_reason": row.get("criteria_block_reason", ""),
                "title": row.get("title", ""),
            }
        )
    total = len(output)
    tp = counts["true_positive"]
    fp = counts["false_positive"]
    fn = counts["false_negative"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    fp_rate = fp / total if total else 0.0
    fn_rate = fn / total if total else 0.0
    status = "pass" if fp_rate < 0.05 and fn_rate < 0.10 and precision >= 0.85 and recall >= 0.85 else "review"
    summary = {
        "generated_at_china": china_stamp(),
        "sample_count": total,
        "true_positive_count": tp,
        "true_negative_count": counts["true_negative"],
        "false_positive_count": fp,
        "false_negative_count": fn,
        "false_positive_rate": f"{fp_rate:.2%}",
        "false_negative_rate": f"{fn_rate:.2%}",
        "precision": f"{precision:.4f}",
        "recall": f"{recall:.4f}",
        "target_false_positive_rate": "<5%",
        "target_false_negative_rate": "<10%",
        "target_precision": ">=0.8500",
        "target_recall": ">=0.8500",
        "status": status,
    }
    by_reason = [
        {"error_type": key[0], "reason": key[1], "count": value}
        for key, value in reason_counts.most_common()
    ]
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["event_id"])
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    reason_path = normalize_path(args.output).with_name("v14_false_positive_monitor_by_reason.csv")
    write_rows(reason_path, by_reason, ["error_type", "reason", "count"])
    normalize_path(args.md_output).write_text(render_md(output, summary, by_reason), encoding="utf-8")
    print(f"sample_count={summary['sample_count']}")
    print(f"false_positive_count={summary['false_positive_count']}")
    print(f"false_negative_count={summary['false_negative_count']}")
    print(f"status={summary['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
