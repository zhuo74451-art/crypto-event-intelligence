import argparse
import csv
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
SPAM_TERMS = ["moon", "100x", "gem", "pump", "lambo", "airdrop soon", "暴涨", "百倍", "冲", "喊单"]
CRYPTO_RELEVANCE_TERMS = [
    "btc", "bitcoin", "eth", "ethereum", "sol", "xrp", "bnb", "hype", "usdt", "usdc",
    "crypto", "token", "chain", "on-chain", "blockchain", "wallet", "exchange", "binance",
    "coinbase", "hyperliquid", "defi", "dex", "cex", "staking", "airdrop", "tvl", "etf",
    "perp", "futures", "stablecoin", "比特币", "以太坊", "加密", "代币", "链上", "钱包",
    "交易所", "币安", "稳定币", "现货ETF", "巨鲸", "合约", "清算",
]
OFF_TOPIC_TERMS = [
    "iran", "以色列", "伊朗", "日本央行", "黄金t+d", "白银t+d", "港股", "三星", "原油",
    "unsc", "pentagon", "taiwan arms", "la paz", "cartel", "芬太尼", "保险集团", "服务器项目",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grade uncategorized/other candidate quality before spending more taxonomy effort.")
    parser.add_argument("--input", default=str(ROOT / "data" / "event_candidates_real_2000_older_v12_reclassified.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v13_other_quality_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v13_other_quality_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v13_other_quality_report.md"))
    parser.add_argument("--similarity-threshold", type=float, default=0.80)
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


def source_id(row: dict) -> str:
    source = str(row.get("source") or "unknown").strip().lower()
    author = str(row.get("author") or "").strip().lower()
    if author:
        return f"{source}:{author}"[:120]
    return source or "unknown"


def token_set(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", str(text).lower()) if len(tok) >= 2}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def emoji_like_ratio(text: str) -> float:
    if not text:
        return 0.0
    non_word = sum(1 for ch in text if not ch.isalnum() and not ch.isspace() and ch not in "，。！？,.!?;:：-_/()（）[]【】")
    return non_word / max(len(text), 1)


def special_char_ratio(text: str) -> float:
    if not text:
        return 0.0
    special = sum(1 for ch in text if not ch.isalnum() and not ch.isspace())
    return special / max(len(text), 1)


def text_quality(title: str, content: str) -> tuple[int, list[str]]:
    score = 100
    flags = []
    text = f"{title} {content}".lower()
    if len(str(title).strip()) < 10:
        score -= 30
        flags.append("short_title")
    if emoji_like_ratio(title) > 0.30:
        score -= 20
        flags.append("emoji_heavy")
    if special_char_ratio(title) > 0.35:
        score -= 20
        flags.append("special_char_heavy")
    if any(term in text for term in SPAM_TERMS):
        score -= 30
        flags.append("spam_keyword")
    if len(str(content).strip()) < 20:
        score -= 20
        flags.append("thin_content")
    if len(str(content).strip()) > 4000:
        score -= 10
        flags.append("scraped_long_body")
    return max(score, 0), flags


def source_quality(source: str, counts: Counter, uncategorized_counts: Counter) -> int:
    total = counts.get(source, 0)
    uncategorized = uncategorized_counts.get(source, 0)
    if total <= 0:
        return 50
    ratio = uncategorized / total
    score = 100
    if uncategorized >= 20 and ratio >= 0.70:
        score -= 60
    elif uncategorized >= 10 and ratio >= 0.50:
        score -= 40
    elif ratio >= 0.50:
        score -= 20
    return max(score, 0)


def timeliness_score(row: dict) -> tuple[int, list[str]]:
    flags = []
    lag_raw = str(row.get("source_lag_minutes") or "").strip()
    if not lag_raw:
        return 70, ["missing_source_lag"]
    try:
        lag = abs(float(lag_raw))
    except ValueError:
        return 70, ["bad_source_lag"]
    if lag > 7 * 24 * 60:
        flags.append("very_late_source_time")
        return 0, flags
    if lag > 3 * 24 * 60:
        flags.append("late_source_time")
        return 50, flags
    if lag > 6 * 60:
        flags.append("source_lag_over_6h")
        return 70, flags
    return 100, flags


def relevance_score(row: dict) -> tuple[int, list[str]]:
    flags = []
    title = str(row.get("title") or "")
    content = str(row.get("content") or "")
    text = f"{title} {content}".lower()
    asset = str(row.get("candidate_asset_symbol") or "").strip()
    source = str(row.get("source") or "").lower()
    score = 100
    if not asset:
        score -= 35
        flags.append("missing_asset")
    if not any(term.lower() in text for term in CRYPTO_RELEVANCE_TERMS):
        score -= 45
        flags.append("low_crypto_relevance")
    if any(term.lower() in text for term in OFF_TOPIC_TERMS):
        score -= 30
        flags.append("off_topic_macro_or_politics")
    if source == "news:jin10" and not asset:
        score -= 20
        flags.append("macro_wire_without_asset")
    return max(score, 0), flags


def grade(overall: float) -> str:
    if overall < 30:
        return "garbage"
    if overall < 60:
        return "low"
    return "potential"


def grade_with_hard_rules(overall: float, flags: list[str]) -> str:
    flag_set = set(flags)
    if {"missing_asset", "low_crypto_relevance"}.issubset(flag_set):
        return "garbage"
    if "off_topic_macro_or_politics" in flag_set and "missing_asset" in flag_set:
        return "garbage"
    if {"emoji_heavy", "thin_content"}.issubset(flag_set):
        return "garbage"
    return grade(overall)


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.input))
    uncategorized = [
        row for row in rows
        if str(row.get("v12_event_type") or row.get("candidate_event_type") or "").strip() in {"uncategorized", "other"}
        and str(row.get("v12_event_subtype") or row.get("candidate_event_subtype") or "").strip() in {"uncategorized", "needs_taxonomy_review", ""}
    ]
    all_source_counts = Counter(source_id(row) for row in rows)
    other_source_counts = Counter(source_id(row) for row in uncategorized)
    tokenized = [token_set(row.get("title", "")) for row in uncategorized]
    duplicate_flags = [False] * len(uncategorized)
    duplicate_counts = [0] * len(uncategorized)
    for i in range(len(uncategorized)):
        for j in range(i + 1, len(uncategorized)):
            sim = jaccard(tokenized[i], tokenized[j])
            if sim >= args.similarity_threshold:
                duplicate_flags[i] = True
                duplicate_flags[j] = True
                duplicate_counts[i] += 1
                duplicate_counts[j] += 1

    output = []
    for idx, row in enumerate(uncategorized):
        sid = source_id(row)
        sq = source_quality(sid, all_source_counts, other_source_counts)
        tq, text_flags = text_quality(row.get("title", ""), row.get("content", ""))
        ts, time_flags = timeliness_score(row)
        dq = 40 if duplicate_flags[idx] else 100
        rs, relevance_flags = relevance_score(row)
        overall = round(sq * 0.20 + tq * 0.25 + ts * 0.15 + dq * 0.15 + rs * 0.25, 2)
        flags = [*text_flags, *time_flags, *relevance_flags]
        if duplicate_flags[idx]:
            flags.append("potential_duplicate")
        item_grade = grade_with_hard_rules(overall, flags)
        output.append(
            {
                "candidate_id": row.get("candidate_id", ""),
                "raw_id": row.get("raw_id", ""),
                "source_id": sid,
                "title": row.get("title", ""),
                "candidate_asset_symbol": row.get("candidate_asset_symbol", ""),
                "source_quality_score": sq,
                "text_quality_score": tq,
                "timeliness_score": ts,
                "duplicate_score": dq,
                "relevance_score": rs,
                "duplicate_count": duplicate_counts[idx],
                "overall_quality": overall,
                "grade": item_grade,
                "recommended_action": "archive" if item_grade == "garbage" else "review_later" if item_grade == "low" else "continue_classify",
                "quality_flags": ",".join(flags),
            }
        )

    fields = list(output[0].keys()) if output else ["candidate_id"]
    write_rows(normalize_path(args.output), output, fields)

    summary = []
    for grade_name, items in sorted(defaultdict(list, {g: [row for row in output if row["grade"] == g] for g in ["garbage", "low", "potential"]}).items()):
        if not items:
            continue
        summary.append(
            {
                "generated_at_china": china_stamp(),
                "grade": grade_name,
                "count": len(items),
                "ratio": round(len(items) / len(output), 4) if output else 0.0,
                "avg_overall_quality": round(sum(float(row["overall_quality"]) for row in items) / len(items), 2),
                "action": "archive" if grade_name == "garbage" else "manual_review" if grade_name == "low" else "continue_classify",
            }
        )
    write_rows(normalize_path(args.summary), summary, list(summary[0].keys()) if summary else ["grade"])

    low_sources = []
    for sid, count in other_source_counts.most_common(20):
        low_sources.append(
            {
                "source_id": sid,
                "uncategorized_count": count,
                "total_count": all_source_counts.get(sid, 0),
                "uncategorized_ratio": round(count / all_source_counts.get(sid, 1), 4),
            }
        )
    lines = [
        "# v13 Other Quality Report",
        "",
        f"- generated_at_china: {china_stamp()}",
        f"- uncategorized_rows: {len(output)}",
        "",
        "## Grade Summary",
        "",
        "| grade | count | ratio | avg_quality | action |",
        "|---|---:|---:|---:|---|",
    ]
    for row in summary:
        lines.append(f"| {row['grade']} | {row['count']} | {row['ratio']} | {row['avg_overall_quality']} | {row['action']} |")
    lines.extend(["", "## Top Uncategorized Sources", "", "| source_id | uncategorized | total | ratio |", "|---|---:|---:|---:|"])
    for row in low_sources[:10]:
        lines.append(f"| {row['source_id']} | {row['uncategorized_count']} | {row['total_count']} | {row['uncategorized_ratio']} |")
    for grade_name in ["garbage", "low", "potential"]:
        lines.extend(["", f"## {grade_name} Examples", "", "| candidate_id | source | quality | flags | title |", "|---|---|---:|---|---|"])
        for row in [item for item in output if item["grade"] == grade_name][:5]:
            title = str(row.get("title", "")).replace("|", "\\|")[:120]
            lines.append(f"| {row['candidate_id']} | {row['source_id']} | {row['overall_quality']} | {row['quality_flags']} | {title} |")
    lines.append("")
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"uncategorized_rows={len(output)}")
    print(Counter(row["grade"] for row in output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
