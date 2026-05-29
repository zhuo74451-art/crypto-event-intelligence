import argparse
import csv
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze and rule-split needs_taxonomy_review rows.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_500_price_backfill.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "needs_taxonomy_review_samples.csv"))
    parser.add_argument("--reclassified-output", default=str(ROOT / "data" / "taxonomy_review_reclassified.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_needs_taxonomy_review_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_needs_taxonomy_review_report.md"))
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


def safe_float(value) -> float:
    try:
        return float(str(value or "").strip() or 0)
    except ValueError:
        return 0.0


def classify(row: dict) -> tuple[str, str]:
    text = f"{row.get('title','')} {row.get('content','')}".lower()
    if re.search(r"policy|policymaker|sen\.|senator|warren|occ|charter|政策|参议员|监管|合规", text):
        return "regulatory_or_policy_context", "policy_or_regulatory_context"
    if re.search(r"ltv|restored|parameter|参数|恢复", text):
        return "protocol_parameter_update", "parameter_update_keyword"
    if re.search(r"transferred from|deposited|deposit|kraken|aave|转入|转出|存入", text):
        return "large_transfer_or_deposit", "transfer_or_deposit_keyword"
    if re.search(r"performance update|index|涨超|普涨|leads index|指数", text):
        return "market_index_update", "index_or_market_update"
    if re.search(r"partnered|unified access|partnership|合作|接入", text):
        return "institutional_partnership", "partnership_keyword"
    if re.search(r"projected to plunge|plunge below|跌破|下跌", text):
        return "negative_market_commentary", "negative_prediction_language"
    if re.search(r"tickets|available|活动|门票", text):
        return "event_promotion", "event_promotion_keyword"
    if re.search(r"formally verify|code|defi projects|验证代码|代码", text):
        return "developer_security_commentary", "developer_security_keyword"
    if re.search(r"on @solana|on solana|try solana|solana defi|sidechains/l|生态", text):
        return "ecosystem_commentary", "ecosystem_commentary_keyword"
    if re.search(r"undervalued|altseason|opportunities|all-time high|all time|hodlers|largest return|no bullshit|patriotic wave|叙事|机会", text):
        return "social_sentiment_commentary", "social_or_sentiment_language"
    if re.search(r"made \$|down nearly|short|long|wallet linked|bought|holder|address|钱包|地址|买入|空单|多单|浮盈|浮亏", text):
        return "influencer_or_wallet_position", "pnl_or_wallet_position"
    if re.search(r"flips|valuation|市值|fdv|fully diluted", text):
        return "market_comparison", "valuation_or_market_comparison"
    if re.search(r"\blisting\b|上线|上币|上架|launchpool|launchpad", text):
        return "listing_announcement", "listing_or_launch_keyword"
    if re.search(r"\btvl\b|total value locked|锁仓|总锁仓", text):
        return "tvl_milestone", "tvl_keyword"
    if re.search(r"\bpartnership\b|合作|integrat|集成", text):
        return "ecosystem_partnership", "partnership_or_integration"
    if re.search(r"\btreasury\b|foundation|基金会|储备", text):
        return "foundation_treasury", "foundation_or_treasury"
    if re.search(r"\brwa\b|tokenization|代币化|real world asset", text):
        return "rwa_tokenization", "rwa_keyword"
    if re.search(r"\bmainnet\b|upgrade|升级|主网", text):
        return "network_upgrade", "upgrade_keyword"
    if re.search(r"zk|circuit|verifier|代码|source code|源码", text):
        return "technical_infrastructure", "technical_infra_keyword"
    return "needs_taxonomy_review", "no_rule_match"


def main() -> int:
    args = parse_args()
    rows = [
        row
        for row in read_rows(normalize_path(args.backfill))
        if str(row.get("event_subtype") or row.get("event_type") or "") == "needs_taxonomy_review"
    ]
    rows.sort(key=lambda row: safe_float(row.get("abnormal_vs_btc_24h")), reverse=True)
    write_rows(normalize_path(args.output), rows, list(rows[0].keys()) if rows else ["event_id"])
    reclassified = []
    for row in rows:
        new_type, reason = classify(row)
        item = dict(row)
        item["v14_taxonomy_event_subtype"] = new_type
        item["v14_taxonomy_reason"] = reason
        reclassified.append(item)
    write_rows(normalize_path(args.reclassified_output), reclassified, list(reclassified[0].keys()) if reclassified else ["event_id"])
    counts = Counter(row["v14_taxonomy_event_subtype"] for row in reclassified)
    summary_rows = []
    for subtype, count in counts.most_common():
        values = [safe_float(row.get("abnormal_vs_btc_24h")) for row in reclassified if row["v14_taxonomy_event_subtype"] == subtype]
        summary_rows.append(
            {
                "generated_at_china": china_stamp(),
                "v14_taxonomy_event_subtype": subtype,
                "sample_count": count,
                "avg_abnormal_vs_btc_24h": round(sum(values) / len(values), 6) if values else 0.0,
                "win_rate_vs_btc_24h": round(sum(1 for value in values if value > 0) / len(values), 4) if values else 0.0,
            }
        )
    write_rows(normalize_path(args.summary), summary_rows, list(summary_rows[0].keys()) if summary_rows else ["v14_taxonomy_event_subtype"])
    lines = [
        "# v14 Needs Taxonomy Review",
        "",
        f"- generated_at_china: {china_stamp()}",
        f"- input_rows: {len(rows)}",
        f"- remaining_needs_taxonomy_review: {counts.get('needs_taxonomy_review', 0)}",
        "",
        "## Reclassified Summary",
        "",
        "| subtype | samples | avg_24h | win_rate_24h |",
        "|---|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(f"| {row['v14_taxonomy_event_subtype']} | {row['sample_count']} | {row['avg_abnormal_vs_btc_24h']} | {row['win_rate_vs_btc_24h']} |")
    lines.extend(["", "## Top 10", "", "| event_id | asset | abnormal_24h | title |", "|---|---|---:|---|"])
    for row in rows[:10]:
        title = str(row.get("title", "")).replace("|", "\\|")[:140]
        lines.append(f"| {row.get('event_id','')} | {row.get('asset_symbol','')} | {row.get('abnormal_vs_btc_24h','')} | {title} |")
    lines.extend(["", "## Bottom 10", "", "| event_id | asset | abnormal_24h | title |", "|---|---|---:|---|"])
    for row in rows[-10:]:
        title = str(row.get("title", "")).replace("|", "\\|")[:140]
        lines.append(f"| {row.get('event_id','')} | {row.get('asset_symbol','')} | {row.get('abnormal_vs_btc_24h','')} | {title} |")
    normalize_path(args.markdown_output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"input_rows={len(rows)}")
    print(f"remaining_needs_taxonomy_review={counts.get('needs_taxonomy_review', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
