import argparse
import csv
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
HEAD_ISSUERS = ["blackrock", "fidelity", "ishares", "grayscale", "bitwise", "ark", "vaneck"]
ETF_CONTEXT_TERMS = [
    "etf",
    "fund",
    "funds",
    "inflow",
    "inflows",
    "outflow",
    "outflows",
    "aum",
    "holdings",
    "issuer",
    "filed",
    "filing",
    "amended",
    "application",
    "trust",
    "balance sheet",
    "buyback",
]
STRICT_ETF_CONTEXT_TERMS = [
    "etf",
    "fund",
    "funds",
    "issuer",
    "filed",
    "filing",
    "amended",
    "application",
    "trust",
    "aum",
    "assets under management",
]
NEGATIVE_CONTEXT_TERMS = [
    "space economy",
    "ipo playbook",
    "supply chain stocks",
    "passive income",
    "cloud mining",
    "meme coin",
    "airdrop",
    "bug bounty",
]
KNOWN_ASSET_SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "LINK", "AVAX", "HYPE", "AAVE"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter ETF/fund flow events by amount and issuer quality.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_500_price_backfill.csv"))
    parser.add_argument("--flow-subtypes", default=str(ROOT / "data" / "v14_flow_event_subtypes.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "etf_fund_flow_filtered.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_etf_fund_flow_filter_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_etf_fund_flow_filter_report.md"))
    parser.add_argument("--min-flow-usd", type=float, default=50_000_000)
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


def index_by(rows: list[dict], field: str) -> dict[str, dict]:
    return {str(row.get(field) or "").strip(): row for row in rows if str(row.get(field) or "").strip()}


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


def extract_amount(text: str) -> float:
    values = []
    for match in re.finditer(r"\$\s*([0-9]+(?:\.[0-9]+)?)\s*(m|million|b|billion)?", text, re.I):
        window = text[max(0, match.start() - 80) : match.end() + 80].lower()
        if not any(term in window for term in ETF_CONTEXT_TERMS):
            continue
        number = float(match.group(1))
        unit = (match.group(2) or "").lower()
        if unit in {"m", "million"}:
            number *= 1_000_000
        elif unit in {"b", "billion"}:
            number *= 1_000_000_000
        values.append(number)
    for match in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*(万美元|亿美元|万\s*美元|亿\s*美元)", text, re.I):
        number = float(match.group(1))
        if "亿" in match.group(2):
            number *= 100_000_000
        else:
            number *= 10_000
        values.append(number)
    return max(values) if values else 0.0


def issuer_hits(text: str) -> list[str]:
    hits = []
    for issuer in HEAD_ISSUERS:
        if re.search(rf"(?<![a-z0-9]){re.escape(issuer)}(?![a-z0-9])", text, re.I):
            hits.append(issuer)
    return hits


def has_etf_context(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in ETF_CONTEXT_TERMS)


def has_strict_etf_context(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in STRICT_ETF_CONTEXT_TERMS)


def is_negative_context(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in NEGATIVE_CONTEXT_TERMS)


def explicit_title_asset(title: str) -> str:
    for symbol in KNOWN_ASSET_SYMBOLS:
        if re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", title.upper()):
            return symbol
    return ""


def main() -> int:
    args = parse_args()
    rows = [
        row
        for row in read_rows(normalize_path(args.backfill))
        if str(row.get("event_subtype") or row.get("event_type") or "") == "etf_or_fund_flow"
    ]
    flow_subtypes = index_by(read_rows(normalize_path(args.flow_subtypes)), "event_id")
    output = []
    for row in rows:
        event_id = str(row.get("event_id") or "").strip()
        flow = flow_subtypes.get(event_id, {})
        refined_subtype = str(flow.get("refined_subtype") or flow.get("v14_flow_subtype") or "")
        text = f"{row.get('title','')} {row.get('content','')}".lower()
        title_text = str(row.get("title", "") or "").lower()
        title_asset = explicit_title_asset(str(row.get("title", "")))
        row_asset = str(row.get("asset_symbol") or "").upper()
        asset_mismatch = bool(title_asset and row_asset and title_asset != row_asset)
        amount = extract_amount(text)
        issuer_hit = ",".join(issuer_hits(text))
        context_ok = has_etf_context(text) and not is_negative_context(text)
        strict_context_ok = has_strict_etf_context(text) and not is_negative_context(text)
        title_strict_context_ok = has_strict_etf_context(title_text)
        keep = refined_subtype == "etf_creation_redemption" and context_ok and title_strict_context_ok and not asset_mismatch and (
            amount >= args.min_flow_usd or (bool(issuer_hit) and strict_context_ok)
        )
        item = dict(row)
        item["parsed_flow_amount_usd"] = round(amount, 2)
        item["head_issuer_hit"] = issuer_hit
        item["etf_context_ok"] = "true" if context_ok else "false"
        item["strict_etf_context_ok"] = "true" if strict_context_ok else "false"
        item["title_strict_etf_context_ok"] = "true" if title_strict_context_ok else "false"
        item["title_asset_hint"] = title_asset
        item["asset_mismatch"] = "true" if asset_mismatch else "false"
        item["refined_flow_subtype"] = refined_subtype
        item["flow_direction"] = flow.get("flow_direction", "")
        item["flow_data_source"] = flow.get("data_source", "")
        item["v14_etf_filter_decision"] = "keep" if keep else "archive"
        item["v14_etf_filter_reason"] = (
            "creation_redemption_amount_or_head_issuer_with_etf_context" if keep else "not_creation_redemption_or_missing_context"
        )
        output.append(item)
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["event_id"])
    kept = [row for row in output if row["v14_etf_filter_decision"] == "keep"]
    values = [safe_float(row.get("abnormal_vs_btc_24h")) for row in kept]
    values = [value for value in values if value is not None]
    summary = {
        "generated_at_china": china_stamp(),
        "input_rows": len(rows),
        "kept_rows": len(kept),
        "archived_rows": len(output) - len(kept),
        "avg_abnormal_vs_btc_24h_kept": round(sum(values) / len(values), 6) if values else 0.0,
        "win_rate_vs_btc_24h_kept": round(sum(1 for value in values if value > 0) / len(values), 4) if values else 0.0,
        "status": "pass" if len(kept) >= 20 else "warning",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    lines = [
        "# v14 ETF/Fund Flow Filter",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- input_rows: {summary['input_rows']}",
        f"- kept_rows: {summary['kept_rows']}",
        f"- avg_24h_kept: {summary['avg_abnormal_vs_btc_24h_kept']}",
        f"- win_rate_24h_kept: {summary['win_rate_vs_btc_24h_kept']}",
        "",
        "| decision | amount_usd | issuer | abnormal_24h | title |",
        "|---|---:|---|---:|---|",
    ]
    for row in output[:80]:
        title = str(row.get("title", "")).replace("|", "\\|")[:140]
        lines.append(f"| {row['v14_etf_filter_decision']} | {row['parsed_flow_amount_usd']} | {row['head_issuer_hit']} | {row.get('abnormal_vs_btc_24h','')} | {title} |")
    normalize_path(args.markdown_output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"input_rows={len(rows)}")
    print(f"kept_rows={len(kept)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
