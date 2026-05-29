import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply stricter candidate identification gates and compare garbage reduction.")
    parser.add_argument("--candidates", default=str(ROOT / "data" / "event_candidates_real_2000_older_v12_reclassified.csv"))
    parser.add_argument("--other-quality", default=str(ROOT / "results" / "v13_other_quality_report.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "event_candidates_real_2000_older_tightened.csv"))
    parser.add_argument("--comparison", default=str(ROOT / "results" / "v13_rule_tightening_comparison.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v13_rule_tightening_report.md"))
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


def has_symbol(row: dict) -> bool:
    return bool(str(row.get("candidate_asset_symbol") or "").strip())


def event_type(row: dict) -> str:
    return str(row.get("v12_event_type") or row.get("candidate_event_type") or "other").strip()


def subtype(row: dict) -> str:
    return str(row.get("v12_event_subtype") or row.get("candidate_event_subtype") or "").strip()


def strict_decision(row: dict, garbage_ids: set[str]) -> tuple[str, str]:
    cid = str(row.get("candidate_id") or "").strip()
    etype = event_type(row)
    flags = str(row.get("quality_flags") or "")
    text = f"{row.get('title','')} {row.get('content','')}".lower()
    if cid in garbage_ids:
        return "archive", "other_quality_garbage"
    if "missing_asset" in flags and etype in {"other", "uncategorized"}:
        return "archive", "missing_asset_uncategorized"
    if etype in {"other", "uncategorized"} and not has_symbol(row):
        return "archive", "unknown_without_asset"
    if etype == "macro" and not has_symbol(row):
        return "archive", "pure_macro_without_asset"
    if any(term in text for term in ["招聘", "会议召开", "conference", "hiring", "podcast"]) and not has_symbol(row):
        return "archive", "industry_admin_news"
    if etype in {"hack_security", "institutional_flow", "exchange_listing", "token_unlock", "stablecoin_flow"}:
        return "keep", "protected_valid_event_type"
    if has_symbol(row) and etype not in {"other", "uncategorized"}:
        return "keep", "explicit_asset_and_type"
    if subtype(row) and subtype(row) not in {"needs_taxonomy_review", "uncategorized"} and has_symbol(row):
        return "keep", "explicit_asset_and_subtype"
    return "review", "strict_gate_review"


def main() -> int:
    args = parse_args()
    candidates = read_rows(normalize_path(args.candidates))
    quality_rows = read_rows(normalize_path(args.other_quality))
    garbage_ids = {str(row.get("candidate_id") or row.get("event_id") or "").strip() for row in quality_rows if str(row.get("grade") or "").strip() == "garbage"}
    output = []
    for row in candidates:
        decision, reason = strict_decision(row, garbage_ids)
        item = dict(row)
        item["v13_strict_candidate_decision"] = decision
        item["v13_strict_candidate_reason"] = reason
        if decision == "archive":
            item["needs_review"] = "false"
        output.append(item)
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["candidate_id"])

    before_counts = Counter(event_type(row) for row in candidates)
    decision_counts = Counter(row["v13_strict_candidate_decision"] for row in output)
    kept_or_review = [row for row in output if row["v13_strict_candidate_decision"] != "archive"]
    after_counts = Counter(event_type(row) for row in kept_or_review)
    comparison = [
        {
            "generated_at_china": china_stamp(),
            "metric": "total_candidates",
            "before": len(candidates),
            "after": len(kept_or_review),
            "delta": len(kept_or_review) - len(candidates),
            "note": "strict archive removes low-quality unknown candidates",
        },
        {
            "generated_at_china": china_stamp(),
            "metric": "archive_count",
            "before": 0,
            "after": decision_counts.get("archive", 0),
            "delta": decision_counts.get("archive", 0),
            "note": "rows marked archive by v13 strict gate",
        },
        {
            "generated_at_china": china_stamp(),
            "metric": "other_uncategorized_count",
            "before": before_counts.get("other", 0) + before_counts.get("uncategorized", 0),
            "after": after_counts.get("other", 0) + after_counts.get("uncategorized", 0),
            "delta": after_counts.get("other", 0) + after_counts.get("uncategorized", 0) - before_counts.get("other", 0) - before_counts.get("uncategorized", 0),
            "note": "unknown bucket after strict gate",
        },
        {
            "generated_at_china": china_stamp(),
            "metric": "protected_valid_event_count",
            "before": sum(1 for row in candidates if event_type(row) in {"hack_security", "institutional_flow", "exchange_listing", "token_unlock", "stablecoin_flow"}),
            "after": sum(1 for row in kept_or_review if event_type(row) in {"hack_security", "institutional_flow", "exchange_listing", "token_unlock", "stablecoin_flow"}),
            "delta": 0,
            "note": "protected types should not be harmed by garbage gate",
        },
    ]
    write_rows(normalize_path(args.comparison), comparison, list(comparison[0].keys()))
    lines = [
        "# v13 Rule Tightening Report",
        "",
        f"- generated_at_china: {china_stamp()}",
        f"- input_candidates: {len(candidates)}",
        f"- archive_count: {decision_counts.get('archive', 0)}",
        f"- keep_count: {decision_counts.get('keep', 0)}",
        f"- review_count: {decision_counts.get('review', 0)}",
        "",
        "| metric | before | after | delta | note |",
        "|---|---:|---:|---:|---|",
    ]
    for row in comparison:
        lines.append(f"| {row['metric']} | {row['before']} | {row['after']} | {row['delta']} | {row['note']} |")
    lines.append("")
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"input_candidates={len(candidates)}")
    print(f"archive_count={decision_counts.get('archive', 0)}")
    print(f"output={normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
