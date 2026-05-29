import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review adversarial false-negative cases without loosening source gates blindly.")
    parser.add_argument("--input", default=str(ROOT / "results" / "v14_adversarial_golden_validation.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_false_negative_case_review.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_false_negative_case_review_summary.csv"))
    parser.add_argument("--md-output", default=str(ROOT / "results" / "v14_false_negative_case_review.md"))
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


def review_action(row: dict) -> tuple[str, str, str]:
    conflict = str(row.get("conflict_type") or "")
    source_tier = str(row.get("source_tier") or "")
    subtype = str(row.get("event_subtype") or "")
    if source_tier == "trusted_media":
        if subtype == "exploit_or_theft":
            return (
                "require_cross_validation",
                "trusted_media_security_with_signed_proof",
                "可信媒体安全事件不能直接放开；只有出现链上交易哈希、官方确认或安全机构二次确认时进入候选。",
            )
        if subtype in {"exchange_halt", "stablecoin_supply_or_flow", "etf_or_fund_flow"}:
            return (
                "require_structured_evidence",
                "trusted_media_market_structure_event",
                "可信媒体市场结构事件需要结构化证据字段，例如官方公告链接、SEC/交易所文件、链上交易或数据表来源。",
            )
    if "founder" in conflict:
        return (
            "require_official_identity_mapping",
            "verified_founder_boundary",
            "创始人账号可作为线索，但需要先进入官方实体映射表；未映射前不放开发布。",
        )
    return ("manual_rule_review", "unclassified_false_negative", "保留为规则复查样本，不直接放宽。")


def render(rows: list[dict], summary: dict) -> str:
    lines = [
        "# v14 False Negative Case Review",
        "",
        f"生成时间：中国时间 {summary['generated_at_china']}",
        "",
        f"- false_negative_count：{summary['false_negative_count']}",
        f"- dominant_block_reason：{summary['dominant_block_reason']}",
        f"- recommended_policy：不直接放宽 source_basis；增加交叉验证字段后再放开。",
        "",
        "| event_id | source_tier | subtype | action | evidence_requirement | title |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        title = str(row.get("title", "")).replace("|", "\\|")
        lines.append(
            f"| {row['event_id']} | {row['source_tier']} | {row['event_subtype']} | {row['review_action']} | {row['evidence_requirement']} | {title} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    source_rows = read_rows(normalize_path(args.input))
    output = []
    reasons = Counter()
    actions = Counter()
    for row in source_rows:
        if not truthy(row.get("expected_publishable")) or truthy(row.get("actual_publishable")):
            continue
        action, requirement, note = review_action(row)
        reasons[str(row.get("criteria_block_reason") or "")] += 1
        actions[action] += 1
        output.append(
            {
                "event_id": row.get("event_id", ""),
                "source_tier": row.get("source_tier", ""),
                "event_subtype": row.get("event_subtype", ""),
                "criteria_block_reason": row.get("criteria_block_reason", ""),
                "conflict_type": row.get("conflict_type", ""),
                "review_action": action,
                "evidence_requirement": requirement,
                "policy_note": note,
                "title": row.get("title", ""),
            }
        )
    summary = {
        "generated_at_china": china_stamp(),
        "false_negative_count": len(output),
        "dominant_block_reason": reasons.most_common(1)[0][0] if reasons else "",
        "action_distribution": ";".join(f"{key}:{value}" for key, value in actions.most_common()),
        "status": "review" if output else "pass",
    }
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["event_id"])
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    normalize_path(args.md_output).write_text(render(output, summary), encoding="utf-8")
    print(f"false_negative_count={summary['false_negative_count']}")
    print(f"status={summary['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
