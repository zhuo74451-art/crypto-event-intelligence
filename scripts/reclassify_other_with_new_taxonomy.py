import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


RULES = [
    ("regulatory_action", "regulatory_or_compliance", ["sec", "cftc", "regulatory", "regulation", "compliance", "lawsuit", "settlement", "fine", "监管", "合规", "诉讼", "起诉", "罚款"]),
    ("tokenomics_change", "burn_buyback_emission", ["burn", "buyback", "emission", "inflation", "token supply", "销毁", "回购", "通胀", "排放"]),
    ("ecosystem_partnership", "partnership_or_integration", ["partnership", "partnered", "integration", "integrates", "collaborate", "合作", "集成", "整合"]),
    ("product_launch", "product_or_feature_launch", ["launch", "release", "debut", "rolls out", "introduces", "推出", "发布", "上线"]),
    ("community_governance", "community_or_dao_vote", ["proposal", "vote", "governance", "dao", "community", "提案", "投票", "治理", "社区"]),
    ("market_sentiment", "analyst_opinion_or_prediction", ["analyst", "prediction", "forecast", "outlook", "price target", "bullish", "bearish", "分析师", "预测", "看涨", "看跌"]),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reclassify candidate_event_type=other with v12 taxonomy rules.")
    parser.add_argument("--input", default=str(ROOT / "data" / "event_candidates_real_2000_older_review.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "event_candidates_real_2000_older_v12_reclassified.csv"))
    parser.add_argument("--report", default=str(ROOT / "results" / "v12_other_reclassification_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v12_other_reclassification_summary.csv"))
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


def match_rule(title: str, content: str) -> tuple[str, str, str]:
    text = f"{title} {content}".lower()
    for event_type, subtype, keywords in RULES:
        if any(keyword.lower() in text for keyword in keywords):
            return event_type, subtype, ",".join(keyword for keyword in keywords if keyword.lower() in text)[:200]
    return "uncategorized", "uncategorized", ""


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.input))
    output = []
    report_rows = []
    before_other = 0
    after_uncategorized = 0
    for row in rows:
        item = dict(row)
        current_type = str(row.get("candidate_event_type") or "").strip()
        current_subtype = str(row.get("candidate_event_subtype") or "").strip()
        if current_type == "other":
            before_other += 1
            event_type, subtype, matched = match_rule(row.get("title", ""), row.get("content", ""))
            item["v12_event_type"] = event_type
            item["v12_event_subtype"] = subtype
            item["v12_reclassify_reason"] = matched
            if event_type == "uncategorized":
                after_uncategorized += 1
        else:
            item["v12_event_type"] = current_type
            item["v12_event_subtype"] = current_subtype or current_type
            item["v12_reclassify_reason"] = "already_classified"
        output.append(item)

    fields = list(rows[0].keys()) if rows else []
    for field in ["v12_event_type", "v12_event_subtype", "v12_reclassify_reason"]:
        if field not in fields:
            fields.append(field)
    write_rows(normalize_path(args.output), output, fields)

    counts = Counter(row.get("v12_event_type", "") for row in output if str(row.get("candidate_event_type") or "") == "other")
    for event_type, count in counts.most_common():
        report_rows.append(
            {
                "v12_event_type": event_type,
                "row_count": count,
                "share_of_original_other": round(count / before_other, 4) if before_other else 0.0,
            }
        )
    write_rows(normalize_path(args.report), report_rows, ["v12_event_type", "row_count", "share_of_original_other"])
    summary = {
        "status": "pass",
        "generated_at_china": china_stamp(),
        "input_rows": len(rows),
        "original_other_count": before_other,
        "reclassified_count": before_other - after_uncategorized,
        "uncategorized_count": after_uncategorized,
        "uncategorized_ratio": round(after_uncategorized / before_other, 4) if before_other else 0.0,
        "output": str(normalize_path(args.output)),
        "report": str(normalize_path(args.report)),
    }
    if before_other and after_uncategorized / before_other >= 0.10:
        summary["status"] = "warning"
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"original_other_count={before_other}")
    print(f"uncategorized_count={after_uncategorized}")
    print(f"status={summary['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
