import argparse
import csv
from collections import Counter
from pathlib import Path


RULES = [
    (
        "reject_generic_price_recap",
        [
            "falls below",
            "breaks above",
            "突破",
            "现报",
            "24h跌幅",
            "24h涨幅",
            "usdt，24h",
            "hodl",
        ],
    ),
    (
        "reject_industry_meta_or_career_content",
        [
            "如何进入 web3",
            "进入 web3 行业",
            "行业的强周期",
            "主动学习能力",
            "雇主极为看重",
            "youtube 频道",
        ],
    ),
    (
        "reject_opinion_or_kol_thesis",
        [
            "which side are you on",
            "market sleeping",
            "not a coincidence",
            "under the hood",
            "one war",
            "how the hell",
        ],
    ),
    (
        "review_onchain_transfer",
        [
            "transferred from unknown wallet",
            "transferred from unknown",
            "unknown wallet to",
            "wallet to #aave",
        ],
    ),
    (
        "review_btc_treasury_company",
        [
            "bitcoin treasury company",
            "buy 72 #bitcoin",
            "增持5枚btc",
            "总持有量达到",
            "oranjebtc",
        ],
    ),
    (
        "reject_non_crypto_health_weather_local",
        [
            "weather",
            "wildfire",
            "earthquake",
            "tick invasion",
            "scientists warn",
            "evacuated",
            "local police",
        ],
    ),
    (
        "reject_geopolitics_no_crypto_angle",
        [
            "iran",
            "israel",
            "drone",
            "strike",
            "war",
            "missile",
            "ceasefire",
            "tariff",
            "trump says",
        ],
    ),
    (
        "reject_equity_company_no_crypto_angle",
        [
            "meta",
            "layoffs",
            "nvidia",
            "tesla",
            "apple",
            "microsoft",
            "amazon",
            "earnings",
            "stock",
        ],
    ),
    (
        "reject_tradfi_marketing_or_ad",
        [
            "financial professionals only",
            "advisors use models",
            "learn how our models",
            "portfolio management",
            "wealth grows",
        ],
    ),
    (
        "reject_social_noise_or_contextless",
        [
            "ask him if",
            "nuts that this is possible",
            "renaissance https://",
            "https://t.co/",
        ],
    ),
    (
        "review_crypto_entity_missing",
        [
            "crypto",
            "blockchain",
            "bitcoin",
            "ethereum",
            "solana",
            "stablecoin",
            "defi",
            "token",
            "wallet",
            "exchange",
            "etf",
        ],
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split v0.6 other_review rows into explicit review/reject reasons.")
    parser.add_argument("--input", default="data/event_candidates_v06_other_review_queue.csv")
    parser.add_argument("--output", default="data/event_candidates_v06_other_review_classified.csv")
    parser.add_argument("--summary", default="results/v06_other_review_reason_summary.csv")
    parser.add_argument("--markdown-output", default="results/v06_other_review_reason_summary.md")
    return parser.parse_args()


def text_blob(row: dict) -> str:
    return f"{row.get('title', '')}\n{row.get('content', '')}".lower()


def classify(row: dict) -> tuple[str, str, str]:
    blob = text_blob(row)
    matched = []
    for reason, keywords in RULES:
        if any(keyword.lower() in blob for keyword in keywords):
            matched.append(reason)

    for reason in ["review_onchain_transfer", "review_btc_treasury_company"]:
        if reason in matched:
            return reason, "keep_review", "concrete_crypto_or_onchain_event"

    for reason in matched:
        if reason.startswith("reject_"):
            return reason, "auto_discard_candidate", "explicit_non_crypto_or_contextless_rule"

    if "review_crypto_entity_missing" in matched:
        return "review_crypto_entity_missing", "keep_review", "crypto_keyword_without_clean_entity"

    if not str(row.get("primary_asset_symbol", "") or "").strip():
        return "reject_missing_entity_low_crypto_relevance", "auto_discard_candidate", "missing_entity_no_crypto_keyword"

    return "review_taxonomy_gap", "keep_review", "entity_or_taxonomy_needs_rule"


def write_summary(path: Path, markdown_path: Path, rows: list[dict]) -> None:
    total = len(rows)
    reason_counts = Counter(row["other_review_reason"] for row in rows)
    action_counts = Counter(row["other_review_action"] for row in rows)
    auto_discard = action_counts.get("auto_discard_candidate", 0)
    keep_review = action_counts.get("keep_review", 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        fieldnames = [
            "total_other_review_rows",
            "auto_discard_candidate_count",
            "keep_review_count",
            "auto_discard_candidate_rate",
            "top_reason",
            "top_reason_count",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        top_reason, top_count = reason_counts.most_common(1)[0] if reason_counts else ("", 0)
        writer.writerow(
            {
                "total_other_review_rows": total,
                "auto_discard_candidate_count": auto_discard,
                "keep_review_count": keep_review,
                "auto_discard_candidate_rate": round(auto_discard / total, 4) if total else 0,
                "top_reason": top_reason,
                "top_reason_count": top_count,
            }
        )

    lines = [
        "# v0.6 Other Review Reason Summary",
        "",
        "This is a rule-based split of the `other_review` bucket. It does not mutate the source queue.",
        "",
        f"- total_other_review_rows: {total}",
        f"- auto_discard_candidate_count: {auto_discard}",
        f"- keep_review_count: {keep_review}",
        "",
        "## Reasons",
        "",
        "| reason | count |",
        "|---|---:|",
    ]
    for reason, count in reason_counts.most_common():
        lines.append(f"| {reason} | {count} |")
    lines.extend(["", "## Actions", "", "| action | count |", "|---|---:|"])
    for action, count in action_counts.most_common():
        lines.append(f"| {action} | {count} |")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    rows = list(csv.DictReader(input_path.open("r", encoding="utf-8-sig", newline="")))
    out_rows = []
    for row in rows:
        reason, action, evidence = classify(row)
        item = dict(row)
        item["other_review_reason"] = reason
        item["other_review_action"] = action
        item["other_review_reason_evidence"] = evidence
        out_rows.append(item)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(out_rows[0].keys()) if out_rows else []
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    write_summary(Path(args.summary), Path(args.markdown_output), out_rows)
    print(f"input_rows={len(rows)}")
    print(f"wrote_output={output_path}")
    print(f"wrote_summary={args.summary}")


if __name__ == "__main__":
    main()
