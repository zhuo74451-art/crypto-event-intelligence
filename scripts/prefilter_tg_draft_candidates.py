import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


GENERIC_PATTERNS = [
    "spoke to",
    "explains how",
    "could make",
    "quietly building",
    "not just a",
    "what .* is .* building",
]

MARKETING_PATTERNS = [
    "physical crypto card",
    "实体加密卡",
    "dogecoin主题",
    "主题",
]

LOW_IMPACT_NEWS_PATTERNS = [
    "revenue hits",
    "wins new york bitlicense",
    "warns us crypto market-structure bill could",
    "could 'fail'",
    "质押比例上升",
    "长期持有者信心",
    "研究员",
    "宣布离职",
    "researchers resign",
]

CONCRETE_PATTERNS = [
    r"\$?\d+(?:\.\d+)?\s?(m|b|k|million|billion|万|亿|枚|eth|btc|usdt|usd)",
    r"net flow",
    r"tvl",
    r"revenue",
    r"returned",
    r"归还",
    r"增持",
    r"流入",
    r"流出",
    r"持有",
    r"wallet",
    r"liquidation",
    r"short position",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local prefilter for TG draft candidates before any Claude review.")
    parser.add_argument("--input", default=str(ROOT / "data" / "event_candidates_v06_clean_low_risk_preview.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "event_candidates_v06_tg_prefilter_pass.csv"))
    parser.add_argument("--rejects-output", default=str(ROOT / "data" / "event_candidates_v06_tg_prefilter_rejects.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "tg_draft_prefilter_summary.csv"))
    parser.add_argument("--max-per-key", type=int, default=1)
    parser.add_argument("--min-title-len", type=int, default=20)
    return parser.parse_args()


def norm(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def value(row: dict, *names: str) -> str:
    for name in names:
        item = str(row.get(name, "") or "").strip()
        if item:
            return item
    return ""


def event_key(row: dict) -> str:
    asset = value(row, "effective_asset_symbol", "primary_asset_symbol", "candidate_asset_symbol")
    event_type = value(row, "event_type_l1", "candidate_event_type", "event_type")
    title = norm(value(row, "title"))
    compact_title = re.sub(r"https?://\S+", "", title)
    compact_title = re.sub(r"[^a-z0-9\u4e00-\u9fff$#]+", " ", compact_title)
    tokens = compact_title.split()
    short = " ".join(tokens[:8])
    if "bitwise" in compact_title and "hype" in compact_title:
        short = "bitwise hype"
    if "revolut" in compact_title and "crypto card" in compact_title:
        short = "revolut crypto card"
    if "ethereum foundation" in compact_title and "researcher" in compact_title:
        short = "ethereum foundation researcher resign"
    return f"{asset}|{event_type}|{short}"


def has_concrete_signal(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in CONCRETE_PATTERNS)


def reject_reason(row: dict, seen_counts: dict[str, int], max_per_key: int, min_title_len: int) -> str:
    title = value(row, "title")
    content = value(row, "content")
    text = norm(f"{title}\n{content}")
    key = event_key(row)

    if len(title.strip()) < min_title_len:
        return "too_short_title"
    if title.rstrip().lower().endswith((" with", " and", " to", " for", " of", "在", "与", "及")) and len(content) < len(title) + 40:
        return "truncated_or_incomplete"
    if seen_counts[key] >= max_per_key:
        return "duplicate_prefilter"
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in LOW_IMPACT_NEWS_PATTERNS):
        return "low_impact_or_too_generic_news"
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in MARKETING_PATTERNS):
        return "marketing_or_adoption_weak_signal"
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in MARKETING_PATTERNS) and not has_concrete_signal(text):
        return "marketing_or_adoption_weak_signal"
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in GENERIC_PATTERNS) and not has_concrete_signal(text):
        return "too_generic_without_concrete_signal"
    if value(row, "event_type_l1") in {"project_business", "stablecoin_flow"} and not has_concrete_signal(text):
        return "weak_research_only_without_metric"
    return ""


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    rows = list(csv.DictReader(input_path.open("r", encoding="utf-8-sig", newline="")))
    fieldnames = list(rows[0].keys()) if rows else []
    reject_fieldnames = fieldnames + ["tg_prefilter_status", "tg_prefilter_reason", "tg_prefilter_event_key"]

    pass_rows = []
    reject_rows = []
    seen_counts: dict[str, int] = defaultdict(int)
    reason_counts: dict[str, int] = defaultdict(int)

    for row in rows:
        key = event_key(row)
        reason = reject_reason(row, seen_counts, args.max_per_key, args.min_title_len)
        if reason:
            item = dict(row)
            item["tg_prefilter_status"] = "reject"
            item["tg_prefilter_reason"] = reason
            item["tg_prefilter_event_key"] = key
            reject_rows.append(item)
            reason_counts[reason] += 1
            continue
        seen_counts[key] += 1
        item = dict(row)
        pass_rows.append(item)

    write_rows(Path(args.output), pass_rows, fieldnames)
    write_rows(Path(args.rejects_output), reject_rows, reject_fieldnames)

    summary = {
        "input_rows": len(rows),
        "pass_rows": len(pass_rows),
        "reject_rows": len(reject_rows),
        "reject_rate": round(len(reject_rows) / len(rows), 4) if rows else 0,
        "top_reject_reason": max(reason_counts, key=reason_counts.get) if reason_counts else "",
        "top_reject_count": max(reason_counts.values()) if reason_counts else 0,
        "status": "pass",
    }
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    print(f"input_rows={len(rows)}")
    print(f"pass_rows={len(pass_rows)}")
    print(f"reject_rows={len(reject_rows)}")
    print(f"wrote_output={args.output}")
    print(f"wrote_rejects={args.rejects_output}")


if __name__ == "__main__":
    main()
