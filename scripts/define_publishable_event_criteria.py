import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


CRITERIA_YAML = """# v14 publishable event criteria
# A Telegram item must be useful as market intelligence, not merely a crypto news item.
version: v14
required:
  - first_party_or_onchain_or_official_source
  - explicit_event_time_anchor
  - observable_market_or_chain_impact
  - not_already_price_in
blocked_examples:
  - sdk_or_tooling_pr
  - validator_deadline_without_activation
  - etf_macro_news_or_executive_commentary
  - soft_security_warning_without_loss_or_tx
  - unclear_flow_direction
notes:
  - Daily zero publishable events is acceptable.
  - Background content belongs in morning/evening digests only after source and event-time checks.
  - Historical reference may be shown only when sample_count >= 3.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Define and evaluate v14 minimum publishable event criteria.")
    parser.add_argument("--policy", default=str(ROOT / "data" / "v14_publish_policy_candidates.csv"))
    parser.add_argument("--short-price-in", default=str(ROOT / "data" / "v14_short_price_in.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v14_publishable_criteria_eval.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_publishable_criteria_summary.csv"))
    parser.add_argument("--criteria-output", default=str(ROOT / "config" / "publishable_criteria.yaml"))
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


def index_by(rows: list[dict], field: str) -> dict[str, dict]:
    return {str(row.get(field) or "").strip(): row for row in rows if str(row.get(field) or "").strip()}


def has_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term in lower for term in terms)


def source_tier(row: dict) -> str:
    explicit = str(row.get("source_tier") or "").strip()
    if explicit:
        return explicit
    source = str(row.get("source") or "").lower()
    title = str(row.get("title") or "").lower()
    if any(term in source for term in ["etherscan", "bscscan", "arbiscan", "solscan"]):
        return "onchain_verified"
    if any(term in source for term in ["binance", "okx", "coinbase", "bybit", "official"]):
        return "official"
    if any(term in source for term in ["lookonchain", "peckshield", "slowmist", "certik", "zachxbt"]):
        return "onchain_or_security_research"
    if source.startswith("news:"):
        return "trusted_media"
    return "community_or_unknown"


def has_source_basis(row: dict) -> bool:
    return source_tier(row) in {"official", "onchain_verified", "onchain_or_security_research", "court_or_regulatory_filing"}


def has_time_anchor(row: dict) -> bool:
    title = str(row.get("title") or "")
    subtype = str(row.get("event_subtype") or "")
    if not str(row.get("event_time_utc") or "").strip():
        return False
    if str(row.get("event_time_anchor") or "").strip():
        return True
    if subtype == "upgrade_or_fork":
        return has_any(title, ["activated", "activation", "goes live", "deployed", "completed", "上线", "已上线", "完成", "激活"])
    return True


def has_observable_impact(row: dict) -> bool:
    subtype = str(row.get("event_subtype") or "")
    explicit = str(row.get("observable_impact_type") or "").strip()
    conflict_type = str(row.get("conflict_type") or "").strip()
    if conflict_type in {
        "threshold_boundary",
        "evidence_missing_boundary",
        "direction_conflict",
        "impact_scope_conflict",
        "liquidity_threshold_boundary",
        "hedge_context_conflict",
        "calendar_effect_conflict",
        "magnitude_threshold_boundary",
        "asset_mapping_conflict",
        "price_already_untradable",
    }:
        return False
    if explicit in {
        "maintenance_notice",
        "social_mention",
        "supply_metadata_correction",
        "small_tvl_change",
        "rumor",
        "temperature_check",
        "small_internal_transfer",
    }:
        return False
    title_l = str(row.get("title") or "").lower()
    notes_l = str(row.get("notes") or "").lower()
    if any(term in title_l for term in ["three days ago", "3 days ago", "last week", "上周", "三天前"]):
        return False
    if "low-liquidity" in notes_l or "low liquidity" in notes_l:
        return False
    if explicit in {
        "exchange_halt",
        "withdrawal_pause",
        "exploit_loss",
        "depeg",
        "bankruptcy_filing",
        "protocol_shutdown",
        "official_listing",
        "forced_liquidation",
        "large_confirmed_flow",
        "large_operational_change",
        "protocol_parameter_change",
    }:
        return True
    title = str(row.get("title") or "")
    content = str(row.get("content") or "")
    text = f"{title} {content}"
    text_l = text.lower()
    if has_any(
        text_l,
        [
            "no-loss phishing",
            "without transaction evidence",
            "suspected loss but no transaction",
            "direction later reversed",
            "test validator tooling",
            "low volume token",
            "market maker hedge",
            "holiday settlement",
            "month-end rebalance",
            "collateral factor by 1 percent",
            "non-tradable",
            "already halted",
            "price already moved",
        ],
    ):
        return False
    if subtype == "upgrade_or_fork":
        upgrade_type = str(row.get("upgrade_type") or "")
        if upgrade_type == "sdk_or_tooling_update":
            return False
        return has_any(text, ["mainnet", "hard fork", "amendment", "activation", "deployed", "主网", "分叉", "激活", "部署"])
    if subtype == "exploit_or_theft":
        return has_any(text, ["tx", "transaction", "address", "0x", "stolen", "drained", "exploit", "被盗", "攻击地址"])
    if subtype == "etf_or_fund_flow":
        return str(row.get("refined_flow_subtype") or "") in {"etf_creation_redemption", "cex_netflow"} and has_any(text, ["inflow", "outflow", "net flow", "流入", "流出"])
    if subtype == "stablecoin_supply_or_flow":
        return has_any(text, ["mint", "burn", "treasury", "transfer", "铸造", "销毁", "转入", "转出"])
    return False


def not_price_in(row: dict, short_price: dict) -> bool:
    if str(short_price.get("short_price_in_flag") or "") == "price_in_block":
        return False
    try:
        if abs(float(str(row.get("price_in_1h") or "0"))) > 0.03:
            return False
    except Exception:
        pass
    return True


def evaluate(row: dict, short_rows: dict[str, dict]) -> dict:
    event_id = str(row.get("event_id") or "").strip()
    short = short_rows.get(event_id, {})
    checks = {
        "source_basis_ok": has_source_basis(row),
        "time_anchor_ok": has_time_anchor(row),
        "observable_impact_ok": has_observable_impact(row),
        "not_price_in_ok": not_price_in(row, short),
    }
    fail_reasons = [name for name, ok in checks.items() if not ok]
    item = {
        "event_id": event_id,
        "asset_symbol": row.get("asset_symbol", ""),
        "event_subtype": row.get("event_subtype", ""),
        "source_tier": source_tier(row),
        **{name: "true" if ok else "false" for name, ok in checks.items()},
        "criteria_passed": "true" if not fail_reasons else "false",
        "criteria_block_reason": ",".join(fail_reasons) if fail_reasons else "pass",
        "price_in_5m": short.get("price_in_5m", ""),
        "price_in_15m": short.get("price_in_15m", ""),
        "price_in_1h": short.get("price_in_1h", ""),
        "title": row.get("title", ""),
    }
    return item


def main() -> int:
    args = parse_args()
    criteria_path = normalize_path(args.criteria_output)
    criteria_path.parent.mkdir(parents=True, exist_ok=True)
    criteria_path.write_text(CRITERIA_YAML, encoding="utf-8")
    rows = read_rows(normalize_path(args.policy))
    short_rows = index_by(read_rows(normalize_path(args.short_price_in)), "event_id")
    output = [evaluate(row, short_rows) for row in rows]
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["event_id"])
    summary = {
        "generated_at_china": china_stamp(),
        "input_rows": len(output),
        "criteria_passed_rows": sum(1 for row in output if row["criteria_passed"] == "true"),
        "criteria_blocked_rows": sum(1 for row in output if row["criteria_passed"] != "true"),
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"input_rows={summary['input_rows']}")
    print(f"criteria_passed_rows={summary['criteria_passed_rows']}")
    print(f"criteria_blocked_rows={summary['criteria_blocked_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
