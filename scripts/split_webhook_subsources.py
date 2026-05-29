import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split webhook source into sub-sources and score each child source.")
    parser.add_argument("--candidates", default=str(ROOT / "data" / "event_candidates_real_5000_older_7_365d_mature_tightened.csv"))
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_500_price_backfill.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "source_scores_v14_webhook_split.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_webhook_split_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_webhook_split_report.md"))
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


def safe_float(value) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def event_type(row: dict) -> str:
    return str(row.get("v12_event_type") or row.get("candidate_event_type") or row.get("event_type") or "unknown")


def domain_from_url(url: str) -> str:
    try:
        host = urlparse(str(url or "")).netloc.lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def infer_subsource(row: dict) -> str:
    source = str(row.get("source") or "").strip()
    if source and source != "webhook":
        return source
    text = f"{row.get('title','')} {row.get('content','')} {row.get('url','')} {row.get('author','')} {row.get('category','')}".lower()
    domain = domain_from_url(row.get("url", ""))
    if "binance" in text or "binance.com" in domain:
        return "webhook_binance"
    if "okx" in text or "okx.com" in domain:
        return "webhook_okx"
    if "bybit" in text or "bybit.com" in domain:
        return "webhook_bybit"
    if "kucoin" in text or "kucoin.com" in domain:
        return "webhook_kucoin"
    if "coindesk" in text or "coindesk.com" in domain:
        return "webhook_coindesk"
    if "cointelegraph" in text or "cointelegraph.com" in domain:
        return "webhook_cointelegraph"
    if "decrypt" in text or "decrypt.co" in domain:
        return "webhook_decrypt"
    if "watcher.guru" in text or "watcherguru" in text:
        return "webhook_watcherguru"
    if "吴说" in text or "wublockchain" in text:
        return "webhook_wublockchain"
    if "币界网" in text:
        return "webhook_bijie"
    if re.search(r"\betf\b|blackrock|fidelity", text):
        return "webhook_etf_news"
    if re.search(r"hack|exploit|漏洞|被盗|攻击", text):
        return "webhook_security_news"
    return "webhook_unknown"


def score_row(candidate_count: int, backtested_count: int, avg_24h: float, win_rate: float, unknown_ratio: float) -> tuple[int, str]:
    score = 0
    reasons = []
    if candidate_count >= 20:
        score += 15
        reasons.append("candidate_count>=20")
    if backtested_count >= 10:
        score += 20
        reasons.append("backtested_count>=10")
    if avg_24h >= 0.01:
        score += 20
        reasons.append("avg_24h>=1pct")
    if win_rate >= 0.60:
        score += 20
        reasons.append("win_rate>=60")
    if unknown_ratio <= 0.30:
        score += 15
        reasons.append("unknown_ratio<=30")
    if unknown_ratio > 0.50:
        score -= 35
        reasons.append("unknown_ratio>50_penalty")
    if candidate_count < 5:
        score -= 20
        reasons.append("tiny_source_penalty")
    return max(0, min(100, score)), ",".join(reasons)


def action_for(score: int) -> tuple[str, int, int]:
    if score < 30:
        return "block", 0, 0
    if score < 50:
        return "throttle", 1, 2
    if score < 70:
        return "validate", 2, 5
    return "trust", 3, 10


def main() -> int:
    args = parse_args()
    candidates = read_rows(normalize_path(args.candidates))
    backfill = read_rows(normalize_path(args.backfill))
    lookup = {str(row.get("candidate_id") or row.get("event_id") or ""): row for row in candidates}
    cand_groups = defaultdict(list)
    for row in candidates:
        sub = infer_subsource(row)
        cand_groups[sub].append(row)
    bf_groups = defaultdict(list)
    for row in backfill:
        cid = str(row.get("event_id") or "")
        source_row = lookup.get(cid, row)
        sub = infer_subsource(source_row)
        bf_groups[sub].append(row)
    output = []
    for sub in sorted(set(cand_groups) | set(bf_groups)):
        cand = cand_groups.get(sub, [])
        bf = bf_groups.get(sub, [])
        returns = [safe_float(row.get("abnormal_vs_btc_24h")) for row in bf]
        returns = [value for value in returns if value is not None]
        avg_24h = sum(returns) / len(returns) if returns else 0.0
        win_rate = sum(1 for value in returns if value > 0) / len(returns) if returns else 0.0
        unknown_count = sum(1 for row in cand if event_type(row) in {"other", "uncategorized"})
        unknown_ratio = unknown_count / len(cand) if cand else 1.0
        score, reasons = score_row(len(cand), len(bf), avg_24h, win_rate, unknown_ratio)
        if sub == "webhook_unknown":
            score = min(score, 20)
            reasons = (reasons + ",forced_unknown_cap").strip(",")
        if sub == "tg:HyperInsight":
            score = min(score, 25)
            reasons = (reasons + ",known_hype_contamination_cap").strip(",")
        if len(bf) < 20:
            score = min(score, 55)
            reasons = (reasons + ",low_backtest_count_cap").strip(",")
        action, max_per_digest, max_per_hour = action_for(score)
        output.append(
            {
                "generated_at_china": china_stamp(),
                "subsource": sub,
                "candidate_count": len(cand),
                "backtested_count": len(bf),
                "unknown_ratio": round(unknown_ratio, 4),
                "avg_abnormal_vs_btc_24h": round(avg_24h, 6),
                "win_rate_vs_btc_24h": round(win_rate, 4),
                "score": score,
                "score_reasons": reasons,
                "recommended_action": action,
                "max_per_digest": max_per_digest,
                "max_per_hour": max_per_hour,
            }
        )
    output.sort(key=lambda row: (-row["score"], -row["backtested_count"], row["subsource"]))
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["subsource"])
    summary = {
        "generated_at_china": china_stamp(),
        "subsource_count": len(output),
        "score_gt_50_count": sum(1 for row in output if row["score"] > 50),
        "webhook_unknown_count": next((row["candidate_count"] for row in output if row["subsource"] == "webhook_unknown"), 0),
        "block_count": sum(1 for row in output if row["recommended_action"] == "block"),
        "output": str(normalize_path(args.output)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    lines = [
        "# v14 Webhook Subsource Split",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- subsource_count: {summary['subsource_count']}",
        f"- score_gt_50_count: {summary['score_gt_50_count']}",
        f"- webhook_unknown_count: {summary['webhook_unknown_count']}",
        "",
        "| subsource | candidates | backtested | unknown_ratio | avg_24h | win_rate | score | action |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in output:
        lines.append(
            f"| {row['subsource']} | {row['candidate_count']} | {row['backtested_count']} | {row['unknown_ratio']} | "
            f"{row['avg_abnormal_vs_btc_24h']} | {row['win_rate_vs_btc_24h']} | {row['score']} | {row['recommended_action']} |"
        )
    normalize_path(args.markdown_output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"subsource_count={len(output)}")
    print(f"score_gt_50_count={summary['score_gt_50_count']}")
    print(f"webhook_unknown_count={summary['webhook_unknown_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
