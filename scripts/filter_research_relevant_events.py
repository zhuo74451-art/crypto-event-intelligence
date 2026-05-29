import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

HIGH_IMPACT_TYPES = {
    "hack_security": 80,
    "legal_enforcement": 55,
    "onchain_data": 70,
    "whale_position": 75,
    "institutional_flow": 70,
    "exchange_listing": 75,
    "token_supply": 70,
    "network_upgrade": 65,
    "stablecoin_flow": 70,
    "regulation_macro": 65,
    "market_structure": 45,
    "project_business": 55,
    "other_review": 20,
}

REVIEWABLE_UNSUPPORTED_TYPES = {
    "hack_security",
    "onchain_data",
    "whale_position",
    "institutional_flow",
    "exchange_listing",
    "token_supply",
    "network_upgrade",
    "project_business",
}

SOURCE_BASE = {
    "webhook": 65,
    "news:cointelegraph": 70,
    "news:cryptonews": 65,
    "tg:": 45,
}

DISCARD_REASONS = [
    "time_parse_failed",
    "missing_entity",
    "unsupported_asset",
    "duplicate_non_primary",
    "generic_price_recap",
    "other_review",
    "low_certainty",
    "low_relevance",
    "low_crypto_relevance",
    "digest_or_market_recap",
    "ai_only_non_crypto",
    "opinion_or_analysis",
    "scraped_footer_noise",
    "generic_market_commentary",
]

PRIMARY_REASON_PRIORITY = [
    "time_parse_failed",
    "scraped_footer_noise",
    "ai_only_non_crypto",
    "low_crypto_relevance",
    "missing_entity",
    "unsupported_asset",
    "duplicate_non_primary",
    "generic_price_recap",
    "generic_market_commentary",
    "opinion_or_analysis",
    "other_review",
    "low_certainty",
    "low_relevance",
]

CRYPTO_RELEVANT_ENTITY_TYPES = {"asset", "exchange", "regulator", "sector", "product", "actor", "project", "org"}
CRYPTO_RELEVANT_TERMS = [
    "crypto",
    "bitcoin",
    "ethereum",
    "blockchain",
    "token",
    "stablecoin",
    "defi",
    "btc",
    "eth",
    "sol",
    "链上",
    "加密",
    "比特币",
    "以太坊",
    "稳定币",
    "交易所",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score event candidates for research relevance and publishing.")
    parser.add_argument("--input", default=str(ROOT / "data" / "event_candidates_v06_deduped.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "event_candidates_v06_relevance_scored.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_relevance_filter_summary.csv"))
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def number(value, default=0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


def source_quality(source: str) -> int:
    source = str(source).strip().lower()
    for prefix, score in SOURCE_BASE.items():
        if source.startswith(prefix):
            return score
    if source:
        return 55
    return 25


def market_cap_tier_score(asset: str) -> int:
    asset = str(asset).strip().upper()
    if asset in {"BTC", "ETH"}:
        return 90
    if asset in {"SOL", "BNB", "XRP"}:
        return 75
    if asset in {"DOGE", "ADA", "LINK", "AVAX"}:
        return 65
    if asset:
        return 45
    return 20


def benchmark_policy(asset: str, scope: str) -> tuple[str, str]:
    asset = str(asset).strip().upper()
    scope = str(scope).strip()
    if scope == "market_wide":
        return "market_wide_separate", "market_wide_events_need_separate_evaluation"
    if asset == "BTC":
        return "ETHUSDT", "btc_event_uses_eth_or_market_basket"
    if asset == "ETH":
        return "BTCUSDT", "eth_event_uses_btc_or_market_basket"
    if asset:
        return "BTC_ETH_BLEND", "token_event_uses_blended_btc_eth"
    return "", "missing_asset_no_benchmark"


def tradability_tier(row: pd.Series, asset: str, scope: str, has_symbol: bool) -> tuple[str, str]:
    event_type = str(row.get("event_type_l1", "")).strip()
    event_l2 = str(row.get("event_type_l2", "")).strip()
    title = str(row.get("title", "")).lower()

    if event_type in {"whale_position", "hack_security", "exchange_listing", "token_supply", "onchain_data"} and asset and has_symbol:
        return "T1", "direct_asset_event_with_price"
    if event_type == "regulation_macro" or scope == "market_wide":
        return "T2", "market_wide_or_policy_event"
    if event_type in {"project_business", "legal_enforcement"} or event_l2 in {"payment_adoption", "license"}:
        return "T3", "indirect_or_research_only"
    if asset and not has_symbol:
        return "T4", "unsupported_asset_research_only"
    if any(term in title for term in ["miner", "mining", "data center", "super factory", "矿工", "矿企"]):
        return "T3", "miner_equity_or_infrastructure"
    return "T3", "default_research_only"


def channel_route(tier: str, event_type: str) -> str:
    if tier == "T1":
        return "alpha_candidate"
    if tier == "T2":
        return "macro_policy"
    if tier == "T4":
        return "unsupported_research"
    if event_type in {"project_business", "legal_enforcement"}:
        return "research_only"
    return "research_only"


def primary_reason(denies: list[str]) -> tuple[str, str]:
    unique = list(dict.fromkeys(denies))
    for reason in PRIMARY_REASON_PRIORITY:
        if reason in unique:
            secondary = ",".join([item for item in unique if item != reason])
            return reason, secondary
    if unique:
        return unique[0], ",".join(unique[1:])
    return "", ""


def is_reviewable_unsupported_asset(row: pd.Series, event_type: str, asset: str, scope: str) -> bool:
    if not asset or scope == "market_wide":
        return False
    if event_type not in REVIEWABLE_UNSUPPORTED_TYPES:
        return False
    flags = ",".join(
        [
            str(row.get("quality_flags", "")),
            str(row.get("entity_flags", "")),
            str(row.get("time_parse_flags", "")),
        ]
    )
    if "time_parse_failed" in flags or str(row.get("time_parse_status", "")).strip() == "failed":
        return False
    entity_score = number(row.get("entity_quality_score", 0), 0)
    confidence = str(row.get("asset_confidence", "")).strip().lower()
    return entity_score >= 50 or confidence in {"medium", "high"}


def hard_denies(row: pd.Series) -> list[str]:
    denies = []
    flags = ",".join(
        [
            str(row.get("quality_flags", "")),
            str(row.get("entity_flags", "")),
            str(row.get("time_parse_flags", "")),
        ]
    )
    entity = str(row.get("primary_entity", "")).strip()
    asset = str(row.get("effective_asset_symbol", "") or row.get("primary_asset_symbol", "") or row.get("candidate_asset_symbol", "")).strip()
    scope = str(row.get("event_scope", "")).strip()
    spot = str(row.get("effective_binance_spot_symbol", "") or row.get("candidate_binance_spot_symbol", "")).strip()
    futures = str(row.get("effective_binance_futures_symbol", "") or row.get("candidate_binance_futures_symbol", "")).strip()
    has_symbol = bool(spot or futures)
    text = f"{row.get('title', '')} {str(row.get('content', ''))[:800]}".lower()
    entity_types = set(str(row.get("primary_entity_type", "")).split("|"))
    detected_entities = str(row.get("detected_entities", ""))

    if str(row.get("time_parse_status", "")).strip() == "failed" or "time_parse_failed" in flags:
        denies.append("time_parse_failed")
    if not entity and not asset and scope != "market_wide":
        denies.append("missing_entity")
    if asset and not spot and not futures and scope != "market_wide":
        denies.append("unsupported_asset")
    if str(row.get("is_cluster_primary", "true")).lower() != "true":
        denies.append("duplicate_non_primary")
    if "possible_price_recap" in flags and str(row.get("event_type_l1", "")) == "market_structure":
        denies.append("generic_price_recap")
    if "digest_or_market_recap" in flags:
        denies.append("digest_or_market_recap")
    if "ai_only_non_crypto" in flags:
        denies.append("ai_only_non_crypto")
    if "opinion_or_analysis" in flags:
        denies.append("opinion_or_analysis")
    if "scraped_footer_noise" in flags:
        denies.append("scraped_footer_noise")
    if "generic_market_commentary" in flags:
        denies.append("generic_market_commentary")
    title = str(row.get("title", "")).lower()
    has_catalyst_word = any(
        term in title
        for term in [
            "hack",
            "exploit",
            "etf",
            "sec",
            "cftc",
            "whale",
            "wallet",
            "unlock",
            "listing",
            "fund",
            "flow",
            "链上",
            "巨鲸",
            "钱包",
            "黑客",
            "攻击",
            "监管",
            "解锁",
            "上线",
            "项目方",
            "多签",
            "转入",
            "转出",
        ]
    )
    pure_price_pattern = (
        "24h" in title
        or "usdt" in title
        or "突破" in title
        or "跌幅" in title
        or "涨幅" in title
        or "收窄" in title
        or "price slips" in title
        or "price drops" in title
        or "analyst predicts" in title
        or "price forecast" in title
    )
    if not has_catalyst_word and pure_price_pattern:
        denies.append("generic_price_recap")
    if str(row.get("event_type_l1", "")) == "other_review":
        denies.append("other_review")
    has_crypto_term = any(term in text for term in CRYPTO_RELEVANT_TERMS)
    has_crypto_entity = any(
        marker in detected_entities
        for marker in [
            "asset_",
            "exchange_",
            "project_",
            "org_sec",
            "org_cftc",
            "entity_etf",
            "entity_stablecoin",
            "entity_rwa",
            "entity_defi",
            "entity_whale",
        ]
    )
    if not has_crypto_term and not has_crypto_entity:
        denies.append("low_crypto_relevance")
    return denies


def score_row(row: pd.Series) -> dict:
    event_type = str(row.get("event_type_l1", "") or row.get("candidate_event_type", "")).strip()
    asset = str(row.get("effective_asset_symbol", "") or row.get("primary_asset_symbol", "") or row.get("candidate_asset_symbol", "")).strip().upper()
    scope = str(row.get("event_scope", "")).strip()
    spot = str(row.get("effective_binance_spot_symbol", "") or row.get("candidate_binance_spot_symbol", "")).strip()
    futures = str(row.get("effective_binance_futures_symbol", "") or row.get("candidate_binance_futures_symbol", "")).strip()
    has_symbol = bool(spot or futures)

    impact_score = HIGH_IMPACT_TYPES.get(event_type, 35)
    if scope == "single_asset":
        impact_score += 10
    elif scope == "multi_asset":
        impact_score -= 10

    certainty_score = source_quality(row.get("source", ""))
    certainty_score += min(number(row.get("source_count", 1), 1) - 1, 4) * 5
    if str(row.get("asset_confidence", "")) == "high":
        certainty_score += 10
    if str(row.get("time_parse_status", "")) == "ok":
        certainty_score += 10

    timeliness_score = 80 if str(row.get("time_parse_status", "")) == "ok" else 20
    entity_quality_score = number(row.get("entity_quality_score", 0), 0)
    source_count_score = min(number(row.get("source_count", 1), 1) * 20, 100)
    price_corroboration_score = ""

    relevance = (
        0.30 * max(0, min(impact_score, 100))
        + 0.25 * max(0, min(certainty_score, 100))
        + 0.20 * max(0, min(source_count_score, 100))
        + 0.15 * max(0, min(timeliness_score, 100))
        + 0.10 * max(0, min(entity_quality_score, 100))
    )

    denies = hard_denies(row)
    relevance_flags = []
    if "unsupported_asset" in denies and is_reviewable_unsupported_asset(row, event_type, asset, scope):
        denies = [reason for reason in denies if reason != "unsupported_asset"]
        relevance_flags.append("unsupported_asset_research_only")
    if certainty_score < 35:
        denies.append("low_certainty")

    benchmark, benchmark_reason = benchmark_policy(asset, scope)
    tier, tier_reason = tradability_tier(row, asset, scope, has_symbol)
    route = channel_route(tier, event_type)

    if denies:
        decision = "discard"
        priority = "discard"
    elif tier == "T4" and relevance >= 50:
        decision = "human_review"
        priority = "medium"
    elif relevance >= 82:
        decision = "human_review"
        priority = "high"
    elif relevance >= 58:
        decision = "human_review"
        priority = "medium"
    else:
        decision = "discard"
        priority = "low"
        denies.append("low_relevance")

    primary, secondary = primary_reason(denies)
    return {
        "impact_score": round(max(0, min(impact_score, 100)), 2),
        "certainty_score": round(max(0, min(certainty_score, 100)), 2),
        "timeliness_score": round(max(0, min(timeliness_score, 100)), 2),
        "source_count_score": round(max(0, min(source_count_score, 100)), 2),
        "market_cap_tier_score": market_cap_tier_score(asset),
        "price_corroboration_score": price_corroboration_score,
        "relevance_score_realtime": round(relevance, 2),
        "relevance_score_retrospective": "",
        "publish_decision": decision,
        "discard_reason": ",".join(dict.fromkeys(denies)),
        "relevance_flags": ",".join(dict.fromkeys(relevance_flags)),
        "primary_discard_reason": primary,
        "secondary_discard_reasons": secondary,
        "research_priority": priority,
        "tradability_tier": tier,
        "tradability_tier_reason": tier_reason,
        "channel_route": route,
        "recommended_benchmark": benchmark,
        "benchmark_reason": benchmark_reason,
    }


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    flag_series = (
        df.get("discard_reason", pd.Series("", index=df.index)).astype(str)
        + ","
        + df.get("relevance_flags", pd.Series("", index=df.index)).astype(str)
    )
    row = {
        "total": int(len(df)),
        "auto_publish_count": int((df["publish_decision"] == "auto_publish").sum()),
        "human_review_count": int((df["publish_decision"] == "human_review").sum()),
        "discard_count": int((df["publish_decision"] == "discard").sum()),
        "other_review_count": int((df.get("event_type_l1", "") == "other_review").sum()),
        "duplicate_non_primary_count": int(df.get("discard_reason", pd.Series("", index=df.index)).astype(str).str.contains("duplicate_non_primary").sum()),
        "missing_entity_count": int(df.get("discard_reason", pd.Series("", index=df.index)).astype(str).str.contains("missing_entity").sum()),
        "unsupported_asset_count": int(flag_series.str.contains("unsupported_asset").sum()),
        "unsupported_research_count": int((df.get("channel_route", "") == "unsupported_research").sum()),
        "t1_count": int((df.get("tradability_tier", "") == "T1").sum()),
        "t2_count": int((df.get("tradability_tier", "") == "T2").sum()),
        "t3_count": int((df.get("tradability_tier", "") == "T3").sum()),
        "t4_count": int((df.get("tradability_tier", "") == "T4").sum()),
    }
    return pd.DataFrame([row])


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    score_df = pd.DataFrame([score_row(row) for _, row in df.iterrows()])
    output = pd.concat([df.reset_index(drop=True), score_df], axis=1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)

    summary = build_summary(output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_path, index=False)
    logging.info("wrote relevance scored candidates to %s", output_path)
    logging.info("wrote summary to %s", summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
