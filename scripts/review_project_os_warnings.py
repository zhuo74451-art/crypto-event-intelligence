import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review Project OS non-blocking warning items.")
    parser.add_argument("--input", default=str(ROOT / "results" / "project_os_validation_report.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_project_os_warning_review.csv"))
    parser.add_argument("--md-output", default=str(ROOT / "results" / "v14_project_os_warning_review.md"))
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


def classify(row: dict) -> dict:
    check = str(row.get("check") or "")
    actual = str(row.get("actual") or "")
    if check == "review_dashboard_items":
        return {
            "risk_level": "low",
            "blocking": "false",
            "owner_action": "保留为项目看板待办；不阻断 ETF/Hyperliquid 早晚报候选试运行。",
            "reason": "这是积压工作数量，不是安全、密钥或发布链路错误。",
        }
    if check == "pending_decision_items":
        return {
            "risk_level": "medium",
            "blocking": "false",
            "owner_action": "继续按最新 Claude 复审结果执行；历史建议队列不作为当前上线阻断项。",
            "reason": f"存在 {actual} 条历史建议，数量大但由当前复审闭环接管。",
        }
    return {
        "risk_level": "review",
        "blocking": "false",
        "owner_action": "查看证据文件，必要时进入下一轮任务。",
        "reason": "未识别的 review 项。",
    }


def render(rows: list[dict]) -> str:
    lines = [
        "# v14 Project OS Warning Review",
        "",
        f"生成时间：中国时间 {china_stamp()}",
        "",
        "| area | check | actual | risk | blocking | action |",
        "|---|---|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('area','')} | {row.get('check','')} | {row.get('actual','')} | {row.get('risk_level','')} | {row.get('blocking','')} | {row.get('owner_action','')} |"
        )
    lines.extend(["", "结论：当前 review 项不是密钥泄露、SQL 注入、线上写入或交易相关风险，不阻断早晚报候选试运行。"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    rows = []
    for row in read_rows(normalize_path(args.input)):
        if str(row.get("status") or "").lower() != "review":
            continue
        item = dict(row)
        item.update(classify(row))
        rows.append(item)
    fields = list(rows[0].keys()) if rows else ["area", "check", "actual", "risk_level", "blocking", "owner_action", "reason"]
    write_rows(normalize_path(args.output), rows, fields)
    normalize_path(args.md_output).write_text(render(rows), encoding="utf-8")
    print(f"review_items={len(rows)}")
    print(f"blocking_items={sum(1 for row in rows if row.get('blocking') == 'true')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
