import argparse
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))

ACTIVE_EXPLOIT_PATTERNS = [
    r"\bexploited\b",
    r"\bexploit\b",
    r"\bhacked\b",
    r"\bdrained\b",
    r"\bstolen\b",
    r"\breentrancy\b",
    r"\bprivate key\b",
    r"\brug pull\b",
    r"被攻击",
    r"遭攻击",
    r"被盗",
    r"盗取",
    r"攻击者",
    r"漏洞利用",
    r"合约漏洞",
]
SECURITY_DISCLOSURE_PATTERNS = [
    r"\bvulnerability\b",
    r"\bsecurity patch\b",
    r"\bdisclosed\b",
    r"\bpatched\b",
    r"\bfixed\b",
    r"漏洞披露",
    r"安全更新",
    r"修复",
]
FUND_RECOVERY_PATTERNS = [
    r"\brecovered\b",
    r"\brecovery\b",
    r"\bfrozen\b",
    r"\bbitfinex\b",
    r"\bmt\.?gox\b",
    r"追回",
    r"冻结",
    r"返还",
]
REGULATORY_PATTERNS = [
    r"\bofac\b",
    r"\bsanction",
    r"\bindicted\b",
    r"\bcharged\b",
    r"\bdoj\b",
    r"制裁",
    r"起诉",
    r"司法部",
]
PROTOCOL_PAUSE_PATTERNS = [
    r"\bpaused\b",
    r"\bsuspended\b",
    r"\bhalted\b",
    r"\bincident\b",
    r"\babnormal\b",
    r"暂停",
    r"异常",
    r"中止",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and split hack_security candidates/backfill rows.")
    parser.add_argument("--candidates", default=str(ROOT / "data" / "event_candidates_real_2000_older_review.csv"))
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_200_price_backfill.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v12_hack_classification_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v12_hack_classification_summary.csv"))
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


def safe_float(value) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def matched(patterns: list[str], text: str) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, flags=re.I)]


def classify(title: str, content: str) -> tuple[str, str]:
    text = f"{title} {content}"
    lower = text.lower()
    if re.search(r"\battacking\s+(ripple|bitcoin|ethereum|crypto|market|policy|bill|act|trump|iran)\b", lower):
        return "hack_unclear", "generic_attack_language"
    hits = matched(FUND_RECOVERY_PATTERNS, text)
    if hits:
        return "fund_recovery", ",".join(hits)[:200]
    hits = matched(ACTIVE_EXPLOIT_PATTERNS, text)
    if hits:
        return "active_exploit", ",".join(hits)[:200]
    hits = matched(SECURITY_DISCLOSURE_PATTERNS, text)
    if hits:
        return "security_disclosure", ",".join(hits)[:200]
    hits = matched(REGULATORY_PATTERNS, text)
    if hits:
        return "regulatory_enforcement", ",".join(hits)[:200]
    hits = matched(PROTOCOL_PAUSE_PATTERNS, text)
    if hits:
        return "protocol_pause", ",".join(hits)[:200]
    return "hack_unclear", ""


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def main() -> int:
    args = parse_args()
    candidates = read_rows(normalize_path(args.candidates))
    backfill = read_rows(normalize_path(args.backfill))
    candidate_lookup = {str(row.get("candidate_id") or row.get("event_id") or "").strip(): row for row in candidates}
    rows = []
    grouped_returns: dict[str, list[float]] = defaultdict(list)
    for row in backfill:
        if str(row.get("event_type") or "").strip() != "hack_security" and str(row.get("event_subtype") or "").strip() != "exploit_or_theft":
            continue
        event_id = str(row.get("event_id") or "").strip()
        source = candidate_lookup.get(event_id, row)
        subtype, reason = classify(source.get("title", row.get("title", "")), source.get("content", row.get("content", "")))
        ret24 = safe_float(row.get("abnormal_vs_btc_24h") or row.get("abnormal_primary_24h"))
        if ret24 is not None:
            grouped_returns[subtype].append(ret24)
        rows.append(
            {
                "event_id": event_id,
                "asset_symbol": row.get("asset_symbol", ""),
                "source": row.get("source", ""),
                "title": row.get("title", ""),
                "hack_subtype": subtype,
                "matched_reason": reason,
                "abnormal_vs_btc_24h": row.get("abnormal_vs_btc_24h", ""),
                "status": row.get("status", ""),
            }
        )
    write_rows(normalize_path(args.output), rows, ["event_id", "asset_symbol", "source", "title", "hack_subtype", "matched_reason", "abnormal_vs_btc_24h", "status"])
    counts = Counter(row["hack_subtype"] for row in rows)
    summary = []
    for subtype, count in counts.most_common():
        values = grouped_returns.get(subtype, [])
        win_rate = sum(1 for value in values if value > 0) / len(values) if values else 0.0
        summary.append(
            {
                "generated_at_china": china_stamp(),
                "hack_subtype": subtype,
                "sample_count": count,
                "computed_24h_count": len(values),
                "avg_abnormal_vs_btc_24h": round(sum(values) / len(values), 6) if values else 0.0,
                "win_rate_vs_btc_24h": round(win_rate, 4) if values else 0.0,
                "routing_hint": "boost_candidate" if subtype == "active_exploit" and len(values) >= 10 and win_rate > 0.6 else "digest_or_collect_more",
            }
        )
    write_rows(normalize_path(args.summary), summary, list(summary[0].keys()) if summary else ["hack_subtype"])
    print(f"hack_rows={len(rows)}")
    print(dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
