import argparse
import csv
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split mixed etf_or_fund_flow rows into ETF, CEX netflow, and institutional subtypes.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_500_price_backfill.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v14_flow_event_subtypes.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_flow_event_subtypes_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_flow_event_subtypes_report.md"))
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


def has_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def has_word(text: str, word: str) -> bool:
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", text.lower()))


def flow_direction(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ["outflow", "outflows", "redemption", "redemptions", "withdraws", "withdrawal", "liquidates", "cuts", "清仓", "流出", "赎回"]):
        return "outflow"
    if any(term in lower for term in ["inflow", "inflows", "creation", "creations", "buy", "buys", "adds", "accumulates", "流入", "申购", "买入", "增持"]):
        return "inflow"
    return "neutral"


def classify_flow(title: str, content: str) -> tuple[str, str, str, str, str]:
    text = f"{title} {content}".lower()
    title_l = title.lower()
    etf_terms = ["etf", "exchange-traded fund", "spot fund", "trust"]
    filing_terms = ["filing", "filed", "files", "amended", "application", "registration", "withdraws", "withdrawal", "sec", "提交", "申请", "修正文件"]
    creation_terms = ["creation", "redemption", "inflow", "inflows", "outflow", "outflows", "net flow", "net inflow", "net outflow", "aum", "assets under management", "share", "shares", "申购", "赎回", "流入", "流出"]
    cex_terms = ["binance", "coinbase", "bybit", "okx", "kraken", "bitfinex", "exchange inflow", "exchange outflow", "deposit", "withdrawal", "withdraw"]
    institution_terms = ["goldman", "blackrock", "fidelity", "ishares", "grayscale", "bitwise", "vaneck", "ark", "strategy", "microstrategy", "treasury", "balance sheet", "13f", "holdings"]
    onchain_terms = ["wallet", "address", "transaction", "tx", "blockchain", "on-chain", "链上", "地址", "交易哈希", "转入", "转出"]

    title_has_etf = has_any(title_l, etf_terms)
    text_has_etf = has_any(text, etf_terms)
    has_filing = has_any(text, filing_terms)
    has_creation = has_any(text, creation_terms)
    has_cex = has_any(text, cex_terms)
    has_institution = has_any(text, institution_terms)
    has_onchain = has_any(text, onchain_terms)
    direction = flow_direction(text)

    if text_has_etf and has_filing:
        return "etf_macro_news", direction, "news", "high" if title_has_etf else "medium", "etf_filing_or_application"
    if text_has_etf and has_creation and not has_filing:
        return "etf_creation_redemption", direction, "filing_or_fund_flow", "high" if title_has_etf else "medium", "etf_creation_redemption_context"
    if has_cex and (has_creation or has_onchain) and not title_has_etf:
        return "cex_netflow", direction, "on-chain", "medium", "cex_exchange_flow_context"
    if has_institution and has_any(text, ["13f", "holdings", "position", "exposure", "liquidates", "cuts", "balance sheet", "treasury", "disclosed", "filing"]):
        return "institutional_disclosure", direction, "filing", "medium", "institutional_disclosure_context"
    if has_word(text, "fund") and has_creation:
        return "flow_unclear", direction, "news", "low", "generic_fund_flow_without_specific_context"
    return "flow_unclear", "neutral", "unknown", "low", "insufficient_specific_context"


def render_report(rows: list[dict], summary: dict) -> str:
    counts = Counter(row["v14_flow_subtype"] for row in rows)
    lines = [
        "# v14 Flow Event Subtype Split",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- input_rows: {summary['input_rows']}",
        f"- etf_specific_rows: {summary['etf_specific_rows']}",
        f"- cex_netflow_rows: {summary['cex_netflow_rows']}",
        f"- unclear_rows: {summary['unclear_rows']}",
        "",
        "## Counts",
        "",
    ]
    for name, count in counts.most_common():
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Samples", "", "| subtype | confidence | asset | source | title |", "|---|---|---|---|---|"])
    for row in rows[:40]:
        title = str(row.get("title") or "").replace("|", "\\|")[:120]
        lines.append(f"| {row['v14_flow_subtype']} | {row['v14_flow_subtype_confidence']} | {row.get('asset_symbol','')} | {row.get('source','')} | {title} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    rows = [
        row for row in read_rows(normalize_path(args.backfill))
        if str(row.get("event_subtype") or "") == "etf_or_fund_flow"
    ]
    output = []
    for row in rows:
        subtype, direction, data_source, confidence, reason = classify_flow(str(row.get("title") or ""), str(row.get("content") or ""))
        item = dict(row)
        item["refined_subtype"] = subtype
        item["flow_direction"] = direction
        item["data_source"] = data_source
        item["subtype_confidence"] = confidence
        item["v14_flow_subtype"] = subtype
        item["v14_flow_subtype_confidence"] = confidence
        item["v14_flow_subtype_reason"] = reason
        item["v14_flow_publish_family"] = "etf_fund" if subtype == "etf_creation_redemption" else subtype
        output.append(item)
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["event_id"])
    summary = {
        "generated_at_china": china_stamp(),
        "input_rows": len(output),
        "etf_specific_rows": sum(1 for row in output if row["refined_subtype"] in {"etf_creation_redemption", "etf_macro_news", "institutional_disclosure"}),
        "etf_creation_redemption_rows": sum(1 for row in output if row["refined_subtype"] == "etf_creation_redemption"),
        "etf_macro_news_rows": sum(1 for row in output if row["refined_subtype"] == "etf_macro_news"),
        "institutional_disclosure_rows": sum(1 for row in output if row["refined_subtype"] == "institutional_disclosure"),
        "cex_netflow_rows": sum(1 for row in output if row["refined_subtype"] == "cex_netflow"),
        "unclear_rows": sum(1 for row in output if row["v14_flow_subtype"] == "flow_unclear"),
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    normalize_path(args.markdown_output).write_text(render_report(output, summary), encoding="utf-8")
    print(f"input_rows={len(output)}")
    print(f"etf_specific_rows={summary['etf_specific_rows']}")
    print(f"cex_netflow_rows={summary['cex_netflow_rows']}")
    print(f"unclear_rows={summary['unclear_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
