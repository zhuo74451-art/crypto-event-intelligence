import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic edge cases for v0.6 intake QA.")
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_synthetic_edge_cases.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_synthetic_edge_cases_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def rows() -> list[dict]:
    base = {
        "source": "synthetic:v06_edge",
        "published_at_china": "2026-05-27 12:00:00 UTC+8",
        "published_at_utc": "2026-05-27T04:00:00Z",
        "manual_review_required": "true",
        "label_origin": "synthetic_edge_case",
    }
    cases = [
        ("syn_001", "CPI hotter than expected pressures all risk assets", "macro_policy", "", "market_wide", "discard", "macro_no_asset"),
        ("syn_002", "SEC approves spot Ethereum ETF rule change", "macro_policy", "ETH", "single_asset", "approve_publish", "explicit_eth_not_btc"),
        ("syn_003", "Whale opens large HYPE short on Hyperliquid", "unsupported_research", "HYPE", "single_asset", "keep_review", "unsupported_but_relevant"),
        ("syn_004", "Protocol pauses eBTC market after abnormal borrow activity", "alpha_candidate", "BTC", "single_asset", "approve_publish", "soft_hack_signal"),
        ("syn_005", "Bitcoin price retests key moving average", "research_only", "BTC", "single_asset", "discard", "generic_price_recap"),
        ("syn_006", "Binance adds new DYOR dashboard", "research_only", "", "market_wide", "discard", "product_announcement_low_alpha"),
        ("syn_007", "US Treasury sanctions crypto mixer tied to exploit", "macro_policy", "", "market_wide", "approve_publish", "legal_enforcement_macro"),
        ("syn_008", "Solana mainnet upgrade scheduled for next week", "research_only", "SOL", "single_asset", "keep_review", "network_upgrade_future"),
        ("syn_009", "Stablecoin issuer mints 1B USDT on Tron", "alpha_candidate", "USDT", "single_asset", "approve_publish", "stablecoin_flow"),
        ("syn_010", "Article footer lists BTC ETH SOL DOGE prices", "research_only", "", "unknown", "discard", "scraped_footer_noise"),
        ("syn_011", "Token unlock for XRP escrow releases 1B XRP", "alpha_candidate", "XRP", "single_asset", "approve_publish", "token_supply_unlock"),
        ("syn_012", "Iran football team arrives in Turkey", "research_only", "", "unknown", "discard", "non_crypto_noise"),
        ("syn_013", "MicroStrategy buys additional BTC", "macro_policy", "BTC", "single_asset", "approve_publish", "institutional_btc_flow"),
        ("syn_014", "Multiple assets rally after Fed rate decision", "macro_policy", "", "market_wide", "keep_review", "market_wide_macro"),
        ("syn_015", "Bridge exploit drains funds then attacker uses Tornado Cash", "alpha_candidate", "", "multi_asset", "approve_publish", "hack_asset_unknown"),
    ]
    output = []
    for candidate_id, title, route, asset, scope, expected_decision, expected_mode in cases:
        row = dict(base)
        row.update(
            {
                "candidate_id": candidate_id,
                "title": title,
                "content": title,
                "manual_channel_route": route,
                "manual_primary_asset_symbol": asset,
                "event_scope": scope,
                "expected_manual_decision": expected_decision,
                "expected_failure_mode": expected_mode,
            }
        )
        output.append(row)
    return output


def main() -> int:
    args = parse_args()
    output = normalize_path(args.output)
    summary = normalize_path(args.summary)
    df = pd.DataFrame(rows())
    output.parent.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    pd.DataFrame(
        [
            {
                "synthetic_edge_cases": len(df),
                "unique_expected_modes": int(df["expected_failure_mode"].nunique()),
                "manual_review_required_rows": int((df["manual_review_required"] == "true").sum()),
            }
        ]
    ).to_csv(summary, index=False)
    print(f"wrote synthetic edge cases to {output}")
    print(f"wrote summary to {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
