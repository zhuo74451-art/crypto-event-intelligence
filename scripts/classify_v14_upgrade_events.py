import argparse
import csv
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
TOP_CHAIN_ASSETS = {"ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "ARB", "OP", "SUI", "APT"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify upgrade_or_fork rows into publishable upgrade subtypes.")
    parser.add_argument("--backfill", default=str(ROOT / "results" / "v08_historical_replay_non_benchmark_alt_500_price_backfill.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v14_upgrade_events.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_upgrade_events_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v14_upgrade_events_report.md"))
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


def has_exact_time(text: str) -> bool:
    lower = text.lower()
    if re.search(r"\b\d{4}-\d{1,2}-\d{1,2}\b", lower):
        return True
    if re.search(r"\bmay\s+\d{1,2}\b|\bjune\s+\d{1,2}\b|\bjuly\s+\d{1,2}\b", lower):
        return True
    return any(term in lower for term in ["deadline", "activation", "goes live", "is now live", "上线", "已上线", "截止", "激活"])


def classify(row: dict) -> dict:
    title = str(row.get("title") or "")
    content = str(row.get("content") or "")
    text = f"{title} {content}"
    asset = str(row.get("asset_symbol") or "").strip().upper()
    lower = text.lower()
    blocks = []
    upgrade_type = "unclear_upgrade"
    route = "block"

    if has_any(lower, ["price rally", "roadmap to", "market cap", "revenue", "clarity act", "analyst", "prediction", "meme", "airdrop", "价格", "预测"]):
        blocks.append("market_or_price_article_not_upgrade")
    if has_any(lower, ["sdk", "plugin", "wallet plugin", "developer", "开发者"]):
        upgrade_type = "sdk_or_tooling_update"
    elif has_any(lower, ["hard fork", "fork", "amendment activation", "validator deadline", "upgrade deadline", "分叉"]):
        upgrade_type = "hard_fork_or_consensus_upgrade"
    elif has_any(lower, ["mainnet", "goes live", "is now live", "主网", "已上线"]):
        upgrade_type = "mainnet_upgrade"
    elif has_any(lower, ["testnet", "sepolia", "holesky", "测试网"]):
        upgrade_type = "testnet_upgrade"
    elif has_any(lower, ["protocol upgrade", "contract upgrade", "合约升级", "协议升级"]):
        upgrade_type = "protocol_upgrade"

    exact_time = has_exact_time(title)
    top_asset = asset in TOP_CHAIN_ASSETS
    if not blocks:
        if upgrade_type in {"hard_fork_or_consensus_upgrade", "mainnet_upgrade"} and exact_time and top_asset:
            route = "digest"
        elif upgrade_type == "protocol_upgrade" and top_asset and exact_time:
            route = "digest"
        elif upgrade_type in {"testnet_upgrade", "sdk_or_tooling_update"} and top_asset and exact_time:
            route = "background"
        else:
            blocks.append("missing_top_asset_exact_time_or_upgrade_type")

    return {
        "event_id": row.get("event_id", ""),
        "asset_symbol": asset,
        "upgrade_type": upgrade_type,
        "upgrade_route": route,
        "upgrade_has_exact_time": "true" if exact_time else "false",
        "upgrade_top_asset": "true" if top_asset else "false",
        "upgrade_block_reason": ",".join(blocks) if blocks else "pass",
        "title": title,
    }


def render_report(rows: list[dict], summary: dict) -> str:
    counts = Counter(row["upgrade_route"] for row in rows)
    lines = [
        "# v14 Upgrade Event Classification",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- input_rows: {summary['input_rows']}",
        f"- digest_rows: {summary['digest_rows']}",
        f"- background_rows: {summary['background_rows']}",
        f"- block_rows: {summary['block_rows']}",
        "",
        "## Route Counts",
        "",
    ]
    for route, count in counts.most_common():
        lines.append(f"- {route}: {count}")
    lines.extend(["", "## Samples", "", "| route | type | asset | reason | title |", "|---|---|---|---|---|"])
    for row in rows[:50]:
        title = str(row.get("title") or "").replace("|", "\\|")[:120]
        lines.append(f"| {row['upgrade_route']} | {row['upgrade_type']} | {row['asset_symbol']} | {row['upgrade_block_reason']} | {title} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    source_rows = [row for row in read_rows(normalize_path(args.backfill)) if str(row.get("event_subtype") or "") == "upgrade_or_fork"]
    output = [classify(row) for row in source_rows]
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["event_id"])
    summary = {
        "generated_at_china": china_stamp(),
        "input_rows": len(output),
        "digest_rows": sum(1 for row in output if row["upgrade_route"] == "digest"),
        "background_rows": sum(1 for row in output if row["upgrade_route"] == "background"),
        "block_rows": sum(1 for row in output if row["upgrade_route"] == "block"),
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    normalize_path(args.markdown_output).write_text(render_report(output, summary), encoding="utf-8")
    print(f"input_rows={summary['input_rows']}")
    print(f"digest_rows={summary['digest_rows']}")
    print(f"background_rows={summary['background_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
