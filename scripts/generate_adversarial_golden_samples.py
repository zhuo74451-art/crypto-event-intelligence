import argparse
import csv
import importlib.util
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


FIELDS = [
    "event_id",
    "event_time_utc",
    "title",
    "content",
    "event_subtype",
    "asset_symbol",
    "source",
    "source_tier",
    "event_time_anchor",
    "observable_impact_type",
    "verification_url",
    "price_in_1h",
    "expected_publishable",
    "blind_label_publishable",
    "boundary_case",
    "conflict_type",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate adversarial golden samples for publishable criteria validation.")
    parser.add_argument("--output", default=str(ROOT / "data" / "v14_adversarial_golden_events.csv"))
    parser.add_argument("--validation-output", default=str(ROOT / "results" / "v14_adversarial_golden_validation.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_adversarial_golden_validation_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def load_criteria_module():
    path = ROOT / "scripts" / "define_publishable_event_criteria.py"
    spec = importlib.util.spec_from_file_location("criteria", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def row(
    idx: int,
    title: str,
    subtype: str,
    asset: str,
    source: str,
    source_tier: str,
    event_time_anchor: str,
    observable: str,
    expected: bool,
    blind: bool | None = None,
    price_in_1h: float = 0.0,
    boundary: bool = False,
    conflict: str = "",
    notes: str = "",
) -> dict:
    day = 1 + (idx % 24)
    return {
        "event_id": f"adv_{idx:03d}",
        "event_time_utc": f"2026-04-{day:02d}T12:00:00Z",
        "title": title,
        "content": f"{title}. Adversarial validation sample for publishable gating.",
        "event_subtype": subtype,
        "asset_symbol": asset,
        "source": source,
        "source_tier": source_tier,
        "event_time_anchor": event_time_anchor,
        "observable_impact_type": observable,
        "verification_url": "https://example.com/validation",
        "price_in_1h": str(price_in_1h),
        "expected_publishable": "true" if expected else "false",
        "blind_label_publishable": "true" if (expected if blind is None else blind) else "false",
        "boundary_case": "true" if boundary else "false",
        "conflict_type": conflict,
        "notes": notes,
    }


def build_samples() -> list[dict]:
    samples: list[dict] = []
    i = 1

    publishable = [
        ("Binance announces emergency listing halt for ABC after contract risk", "exchange_halt", "ABC", "binance", "official", "announcement_timestamp", "exchange_halt"),
        ("Aave governance executes parameter change reducing LTV for CRV collateral", "governance", "AAVE", "aave_official", "official", "execution_timestamp", "protocol_parameter_change"),
        ("Tether treasury mints 1B USDT on Ethereum with transaction hash", "stablecoin_supply_or_flow", "USDT", "etherscan", "onchain_verified", "block_timestamp", "large_confirmed_flow"),
        ("USDC depegs after issuer confirms banking exposure", "stablecoin_supply_or_flow", "USDC", "circle_official", "official", "statement_timestamp", "depeg"),
        ("Major exchange pauses SOL withdrawals citing network incident", "exchange_halt", "SOL", "binance", "official", "status_page_timestamp", "withdrawal_pause"),
        ("Curve pool exploit drains funds from CRV pools with attacker address", "exploit_or_theft", "CRV", "peckshield", "onchain_or_security_research", "tx_timestamp", "exploit_loss"),
        ("Ronin bridge exploit confirmed with attacker address and stolen funds", "exploit_or_theft", "RON", "slowmist", "onchain_or_security_research", "tx_timestamp", "exploit_loss"),
        ("Coinbase announces official listing for NEWCOIN with trading time", "exchange_listing", "NEW", "coinbase", "official", "listing_time", "official_listing"),
        ("Protocol mainnet hard fork activated at block height", "upgrade_or_fork", "ETH", "ethereum_official", "official", "activation_block_time", "large_operational_change"),
        ("Large liquidations force close whale ETH position on Hyperliquid", "whale_position", "ETH", "hyperliquid", "onchain_verified", "event_timestamp", "forced_liquidation"),
        ("MakerDAO executes emergency debt ceiling parameter change", "governance", "MKR", "maker_official", "official", "execution_timestamp", "protocol_parameter_change"),
        ("OKX announces delisting of TOKEN perpetual contracts", "exchange_listing", "TOKEN", "okx", "official", "announcement_timestamp", "official_listing"),
        ("Lending protocol disables borrowing after oracle malfunction", "exchange_halt", "LEND", "official_status", "official", "status_page_timestamp", "withdrawal_pause"),
        ("Bridge exploit drains 45M with verified attacker transaction", "exploit_or_theft", "BRG", "zachxbt", "onchain_or_security_research", "tx_timestamp", "exploit_loss"),
        ("Exchange confirms bankruptcy filing with court case number", "bankruptcy", "EXCH", "court_filing", "court_or_regulatory_filing", "court_filing_timestamp", "bankruptcy_filing"),
    ]
    for item in publishable:
        samples.append(row(i, *item, expected=True))
        i += 1

    # Expected publishable by product judgment, but the current rules should miss some because source or subtype is not explicit enough.
    false_negative_pressure = [
        ("Trusted media reports exchange wallet freeze confirmed by three users", "exchange_halt", "BTC", "news:reputable_wire", "trusted_media", "publish_timestamp", "withdrawal_pause", "trusted_media_confirmed_but_source_gate_blocks"),
        ("Research desk publishes signed proof of exploit loss before official post", "exploit_or_theft", "ALT", "news:research_desk", "trusted_media", "publish_timestamp", "exploit_loss", "source_tier_boundary"),
        ("ETF issuer files urgent amendment changing creation basket mechanics", "etf_or_fund_flow", "BTC", "news:sec_filing_tracker", "trusted_media", "filing_timestamp", "large_operational_change", "regulatory_source_not_whitelisted"),
        ("Stablecoin issuer transaction observed by public dashboard before explorer label", "stablecoin_supply_or_flow", "USDT", "news:onchain_dashboard", "trusted_media", "dashboard_timestamp", "large_confirmed_flow", "source_basis_boundary"),
        ("Protocol emergency shutdown reported by verified founder account", "exchange_halt", "DEF", "x_verified_founder", "community_or_unknown", "post_timestamp", "protocol_shutdown", "founder_source_boundary"),
    ]
    for offset, (title, subtype, asset, source, tier, anchor, observable, conflict) in enumerate(false_negative_pressure):
        blind = False if offset in {1, 4} else True
        samples.append(row(i, title, subtype, asset, source, tier, anchor, observable, True, blind=blind, boundary=True, conflict=conflict))
        i += 1

    rejected = [
        ("ETF executive says Bitcoin may rise this year", "etf_or_fund_flow", "BTC", "news:interview", "trusted_media", "publish_timestamp", "rumor"),
        ("Developer SDK release improves wallet integration", "upgrade_or_fork", "SDK", "official_blog", "official", "release_timestamp", "maintenance_notice"),
        ("Validator deadline reminder for optional software update", "upgrade_or_fork", "ATOM", "official_blog", "official", "announcement_timestamp", "maintenance_notice"),
        ("Small internal exchange transfer of 200K USDT", "stablecoin_supply_or_flow", "USDT", "etherscan", "onchain_verified", "block_timestamp", "small_internal_transfer"),
        ("KOL claims whale may buy BTC soon", "whale_position", "BTC", "x_kol", "community_or_unknown", "post_timestamp", "rumor"),
        ("Old exploit recap from last week resurfaces", "exploit_or_theft", "ALT", "slowmist", "onchain_or_security_research", "publish_timestamp", "exploit_loss"),
        ("Protocol posts educational article about governance", "governance", "GOV", "official_blog", "official", "publish_timestamp", "maintenance_notice"),
        ("Exchange announces website maintenance window", "exchange_halt", "BNB", "binance", "official", "announcement_timestamp", "maintenance_notice"),
        ("No-loss phishing warning without transaction evidence", "exploit_or_theft", "ABC", "certik", "onchain_or_security_research", "publish_timestamp", "soft_security_warning_without_loss"),
        ("ETF analyst commentary without actual flow data", "etf_or_fund_flow", "BTC", "news:media", "trusted_media", "publish_timestamp", "rumor"),
        ("Unclear wallet movement between unknown addresses", "stablecoin_supply_or_flow", "USDT", "etherscan", "onchain_verified", "block_timestamp", "unclear_flow_direction"),
        ("Low liquidity token listing on minor venue", "exchange_listing", "MICRO", "official_exchange", "official", "listing_time", "official_listing"),
        ("Protocol temperature check opens non-binding vote", "governance", "DAO", "official_forum", "official", "proposal_timestamp", "temperature_check"),
        ("Minor TVL dashboard change under reporting threshold", "governance", "DEFI", "official_dashboard", "official", "dashboard_timestamp", "small_tvl_change"),
        ("Price already moved 8 percent before announcement", "exchange_listing", "FAST", "coinbase", "official", "listing_time", "official_listing"),
    ]
    for item in rejected:
        title, subtype, asset, source, tier, anchor, observable = item
        price_in = 0.08 if "already moved" in title else 0.0
        boundary = any(term in title.lower() for term in ["low liquidity", "unclear", "already moved", "no-loss"])
        conflict = "threshold_boundary" if boundary else ""
        notes = "low-liquidity boundary" if "Low liquidity" in title else ""
        blind = True if "Unclear wallet movement" in title else False
        samples.append(row(i, title, subtype, asset, source, tier, anchor, observable, False, blind=blind, price_in_1h=price_in, boundary=boundary, conflict=conflict, notes=notes))
        i += 1

    # Hard boundary/conflict cases. Some are deliberately ambiguous to avoid a fake 100% score.
    boundary_cases = [
        ("Official listing but market cap is tiny and venue liquidity is weak", "exchange_listing", "TINY", "coinbase", "official", "listing_time", "official_listing", False, "threshold_boundary"),
        ("Official exploit post says suspected loss but no transaction hash yet", "exploit_or_theft", "BUG", "official_blog", "official", "post_timestamp", "exploit_loss", False, "evidence_missing_boundary"),
        ("Large USDT transfer from treasury to Binance but direction later reversed", "stablecoin_supply_or_flow", "USDT", "etherscan", "onchain_verified", "block_timestamp", "large_confirmed_flow", False, "direction_conflict"),
        ("Mainnet hard fork activated but only affects test validator tooling", "upgrade_or_fork", "ALT", "official_blog", "official", "activation_time", "large_operational_change", False, "impact_scope_conflict"),
        ("Exchange pauses withdrawals for one low volume token", "exchange_halt", "MICRO", "binance", "official", "status_timestamp", "withdrawal_pause", False, "liquidity_threshold_boundary"),
        ("Whale liquidation above threshold but account is known market maker hedge", "whale_position", "ETH", "hyperliquid", "onchain_verified", "event_timestamp", "forced_liquidation", False, "hedge_context_conflict"),
        ("ETF net outflow large but due to holiday settlement catch-up", "etf_or_fund_flow", "BTC", "farside", "onchain_or_security_research", "data_timestamp", "large_confirmed_flow", False, "calendar_effect_conflict"),
        ("Official governance execution changes collateral factor by 1 percent", "governance", "AAVE", "aave_official", "official", "execution_timestamp", "protocol_parameter_change", False, "magnitude_threshold_boundary"),
        ("Bridge exploit confirmed for non-tradable governance side token", "exploit_or_theft", "SIDE", "slowmist", "onchain_or_security_research", "tx_timestamp", "exploit_loss", False, "asset_mapping_conflict"),
        ("Emergency oracle pause blocks major lending market withdrawals", "exchange_halt", "LEND", "official_status", "official", "status_timestamp", "withdrawal_pause", True, "multi_condition_conflict"),
        ("Court filing confirms asset freeze but token already halted", "bankruptcy", "HALT", "court_filing", "court_or_regulatory_filing", "court_filing_timestamp", "bankruptcy_filing", False, "price_already_untradable"),
        ("Stablecoin depeg official update during banking incident", "stablecoin_supply_or_flow", "USDC", "circle_official", "official", "statement_timestamp", "depeg", True, "multi_condition_conflict"),
        ("CEX delisting notice with 12 hours lead time for liquid perpetual", "exchange_listing", "PERP", "okx", "official", "announcement_timestamp", "official_listing", True, "event_time_boundary"),
        ("Security firm confirms exploit amount after price fell 12 percent", "exploit_or_theft", "ALT", "peckshield", "onchain_or_security_research", "tx_timestamp", "exploit_loss", False, "price_in_boundary"),
        ("Protocol shutdown confirmed by multisig transaction", "exchange_halt", "DEF", "etherscan", "onchain_verified", "block_timestamp", "protocol_shutdown", True, "source_impact_boundary"),
        ("ETF daily flow is 96th percentile but from normal month-end rebalance", "etf_or_fund_flow", "BTC", "farside", "onchain_or_security_research", "data_timestamp", "large_confirmed_flow", False, "calendar_effect_conflict"),
        ("Official hard fork completed with fee market change", "upgrade_or_fork", "ETH", "ethereum_official", "official", "activation_time", "large_operational_change", True, "impact_scope_boundary"),
        ("Whale adds large isolated short within 3 percent of liquidation", "whale_position", "BTC", "hyperliquid", "onchain_verified", "event_timestamp", "forced_liquidation", True, "risk_threshold_boundary"),
        ("Regulator files emergency injunction against exchange operations", "regulation", "BNB", "court_filing", "court_or_regulatory_filing", "filing_timestamp", "exchange_halt", True, "source_impact_boundary"),
        ("Unverified screenshot claims exchange insolvency", "bankruptcy", "EXCH", "telegram_forward", "community_or_unknown", "post_timestamp", "rumor", False, "source_quality_boundary"),
        ("Official listing notice for token already active on major perpetual venues", "exchange_listing", "DUP", "coinbase", "official", "listing_time", "official_listing", False, "market_already_available"),
        ("Official parameter execution only affects deprecated isolated lending market", "governance", "AAVE", "aave_official", "official", "execution_timestamp", "protocol_parameter_change", False, "deprecated_market_scope"),
        ("Bridge exploit confirmed but affected asset is an unlisted NFT collection", "exploit_or_theft", "NFT", "slowmist", "onchain_or_security_research", "tx_timestamp", "exploit_loss", False, "asset_mapping_conflict_residual"),
        ("Large stablecoin treasury flow later identified as exchange inventory rebalancing", "stablecoin_supply_or_flow", "USDT", "etherscan", "onchain_verified", "block_timestamp", "large_confirmed_flow", False, "inventory_rebalance_residual"),
        ("Whale forced liquidation belongs to same-wallet collateral rotation", "whale_position", "ETH", "hyperliquid", "onchain_verified", "event_timestamp", "forced_liquidation", False, "collateral_rotation_residual"),
    ]
    for title, subtype, asset, source, tier, anchor, observable, expected, conflict in boundary_cases:
        price_in = 0.12 if "price fell 12" in title else 0.0
        blind = expected
        if conflict in {"calendar_effect_conflict", "hedge_context_conflict", "magnitude_threshold_boundary"}:
            blind = False
        samples.append(row(i, title, subtype, asset, source, tier, anchor, observable, expected, blind=blind, price_in_1h=price_in, boundary=True, conflict=conflict))
        i += 1

    return samples


def bool_value(value: str) -> bool:
    return str(value or "").strip().lower() == "true"


def cohen_kappa(a: list[bool], b: list[bool]) -> float:
    if not a or len(a) != len(b):
        return 0.0
    n = len(a)
    observed = sum(1 for x, y in zip(a, b) if x == y) / n
    pa_true = sum(a) / n
    pb_true = sum(b) / n
    expected = pa_true * pb_true + (1 - pa_true) * (1 - pb_true)
    if expected == 1:
        return 1.0
    return (observed - expected) / (1 - expected)


def validate(samples: list[dict]) -> tuple[list[dict], dict]:
    criteria = load_criteria_module()
    rows = []
    for sample in samples:
        short = {"short_price_in_flag": "pass", "price_in_1h": sample.get("price_in_1h", "")}
        result = criteria.evaluate(sample, {sample["event_id"]: short})
        expected = bool_value(sample["expected_publishable"])
        actual = bool_value(result.get("criteria_passed"))
        rows.append(
            {
                **sample,
                "actual_publishable": "true" if actual else "false",
                "validation_status": "pass" if actual == expected else "fail",
                "criteria_block_reason": result.get("criteria_block_reason", ""),
                "computed_source_tier": result.get("source_tier", ""),
            }
        )

    expected_positive = [row for row in rows if bool_value(row["expected_publishable"])]
    predicted_positive = [row for row in rows if bool_value(row["actual_publishable"])]
    true_positive = [row for row in rows if bool_value(row["expected_publishable"]) and bool_value(row["actual_publishable"])]
    false_positive = [row for row in rows if not bool_value(row["expected_publishable"]) and bool_value(row["actual_publishable"])]
    false_negative = [row for row in rows if bool_value(row["expected_publishable"]) and not bool_value(row["actual_publishable"])]
    rejection_reasons = Counter(
        reason
        for row in rows
        for reason in str(row.get("criteria_block_reason") or "").split(",")
        if reason and reason != "pass"
    )
    expected_labels = [bool_value(row["expected_publishable"]) for row in rows]
    blind_labels = [bool_value(row["blind_label_publishable"]) for row in rows]
    summary = {
        "generated_at_china": china_stamp(),
        "sample_count": len(rows),
        "expected_publishable_rows": len(expected_positive),
        "actual_publishable_rows": len(predicted_positive),
        "recall": round(len(true_positive) / len(expected_positive), 4) if expected_positive else 0.0,
        "precision_estimate": round(len(true_positive) / len(predicted_positive), 4) if predicted_positive else 0.0,
        "false_positive_rows": len(false_positive),
        "false_negative_rows": len(false_negative),
        "boundary_case_count": sum(1 for row in rows if bool_value(row["boundary_case"])),
        "multi_condition_conflict_count": sum(1 for row in rows if row.get("conflict_type")),
        "cohen_kappa_expected_vs_blind": round(cohen_kappa(expected_labels, blind_labels), 4),
        "top_rejection_reasons": ";".join(f"{k}:{v}" for k, v in rejection_reasons.most_common(8)),
        "status": "pass",
    }
    return rows, summary


def main() -> int:
    args = parse_args()
    samples = build_samples()
    write_rows(normalize_path(args.output), samples, FIELDS)
    validation_rows, summary = validate(samples)
    write_rows(normalize_path(args.validation_output), validation_rows, list(validation_rows[0].keys()) if validation_rows else FIELDS)
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"sample_count={summary['sample_count']}")
    print(f"boundary_case_count={summary['boundary_case_count']}")
    print(f"recall={summary['recall']}")
    print(f"precision_estimate={summary['precision_estimate']}")
    print(f"cohen_kappa_expected_vs_blind={summary['cohen_kappa_expected_vs_blind']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
