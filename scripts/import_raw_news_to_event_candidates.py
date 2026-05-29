import argparse
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd

try:
    from utils.time_utils import parse_any_time_to_utc_iso, utc_iso_to_china_iso
except ModuleNotFoundError:
    from scripts.utils.time_utils import parse_any_time_to_utc_iso, utc_iso_to_china_iso


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_COLUMNS = [
    "candidate_id",
    "raw_id",
    "raw_published_at",
    "published_at",
    "published_at_utc",
    "published_at_china",
    "raw_source_published_at",
    "source_published_at_utc",
    "source_published_at_china",
    "source_timezone",
    "source_timezone_assumption",
    "source_lag_minutes",
    "backtest_time",
    "backtest_time_utc",
    "backtest_time_china",
    "backtest_time_basis",
    "time_timezone_assumption",
    "time_parse_status",
    "time_parse_flags",
    "title",
    "content",
    "source",
    "url",
    "candidate_asset_symbol",
    "candidate_binance_spot_symbol",
    "candidate_binance_futures_symbol",
    "candidate_event_type",
    "candidate_event_subtype",
    "candidate_direction_hint",
    "candidate_importance",
    "event_scope",
    "asset_confidence",
    "time_confidence",
    "needs_review",
    "review_decision",
    "review_notes",
    "quality_flags",
]

ASSET_KEYWORDS = {
    "BTC": ["bitcoin", "btc", "比特币"],
    "ETH": ["ethereum", "eth", "以太坊"],
    "SOL": ["solana", "sol", "索拉纳"],
    "XRP": ["xrp", "ripple", "瑞波"],
    "DOGE": ["dogecoin", "doge", "狗狗币"],
    "LINK": ["chainlink", "link"],
    "AVAX": ["avalanche", "avax"],
    "BNB": ["bnb", "binance coin", "币安币"],
}

MARKET_WIDE_KEYWORDS = [
    "cpi",
    "ppi",
    "fed",
    "fomc",
    "rate",
    "利率",
    "美联储",
    "非农",
    "美元",
    "纳斯达克",
    "原油",
    "关税",
    "战争",
    "特朗普",
]

EVENT_RULES = [
    ("hack_security", "exploit_or_theft", "risk", ["hack", "hacked", "exploit", "attack", "stolen", "vulnerability", "phishing", "drained", "breach", "compromised", "tornado cash", "攻击", "被盗", "漏洞", "钓鱼"]),
    ("token_unlock", "unlock_or_supply", "risk", ["token unlock", "tokens unlock", "unlock alert", "unlock cliff", "vesting unlock", "escrow unlock", "代币解锁", "解锁代币", "解锁预警", "代币释放", "归属解锁"]),
    ("halving", "halving", "observe", ["halving", "减半"]),
    (
        "network_upgrade",
        "upgrade_or_fork",
        "observe",
        ["upgrade", "mainnet", "dencun", "fork", "hard fork", "升级", "主网", "分叉"],
    ),
    ("macro", "macro_event", "observe", MARKET_WIDE_KEYWORDS),
    (
        "staking_governance",
        "staking_or_governance",
        "observe",
        ["staking", "stake", "governance", "proposal", "vote", "质押", "治理", "提案", "投票"],
    ),
    (
        "institutional_flow",
        "etf_or_fund_flow",
        "observe",
        [
            "etf",
            "strategy",
            "microstrategy",
            "fund issuer",
            "issuer",
            "inflow",
            "outflow",
            "fund",
            "现货 etf",
            "现货ETF",
            "机构",
            "买入",
            "流入",
        ],
    ),
    (
        "whale_position",
        "whale_wallet_position",
        "observe",
        ["whale", "巨鲸", "地址", "钱包", "多单", "空单", "清算", "持仓"],
    ),
    ("exchange_listing", "listing_delisting", "observe", ["listing", "delisting", "上线", "上架", "下架"]),
]

OTHER_SPLIT_RULES = [
    ("stablecoin_flow", "stablecoin_supply_or_flow", "observe", ["stablecoin", "stablecoins", "usdt", "usdc", "tether", "circle", "mint", "burn"]),
    ("project_business", "rwa_tokenization", "observe", ["rwa", "tokenized", "tokenization", "real world asset", "treasury product"]),
    ("project_business", "payment_or_card_adoption", "observe", ["crypto card", "visa", "mastercard", "payment", "payments", "checkout", "merchant"]),
    ("project_business", "custody_or_institutional_product", "observe", ["custody", "custodian", "prime broker", "oms", "institutional product"]),
    ("onchain_data", "protocol_metric", "observe", ["tvl", "defillama", "protocol revenue", "active addresses", "wallets", "on-chain activity"]),
    ("market_structure", "price_market_structure", "observe", ["breakout", "support", "resistance", "open interest", "funding rate", "liquidations", "volume spike"]),
    ("project_business", "foundation_team", "observe", ["foundation", "team resign", "resigns", "leadership", "governance foundation"]),
    ("ai_infra", "ai_compute_or_model", "observe", ["openai", "claude", "gemini", "cursor", "datadog", "benchmark", "ai model"]),
]

HACK_CONTEXT_FALSE_POSITIVES = [
    "hack recovery",
    "bitfinex hack recovery",
    "2016 bitfinex hack",
    "hack funds recovered",
    "recovered from the hack",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert raw news exports into reviewable event candidates."
    )
    parser.add_argument("--input", default=str(ROOT / "data" / "raw_news_export_template.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "event_candidates_review.csv"))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--source-timezone-rules", default=str(ROOT / "data" / "source_timezone_rules.csv"))
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_symbol_map(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        logging.warning("symbol map not found: %s", path)
        return {}
    df = pd.read_csv(path, dtype=str).fillna("")
    result: Dict[str, Dict[str, str]] = {}
    for _, row in df.iterrows():
        asset = str(row.get("asset_symbol", "")).strip().upper()
        if not asset:
            continue
        result[asset] = {
            "binance_spot_symbol": str(row.get("binance_spot_symbol", "")).strip().upper(),
            "binance_futures_symbol": str(row.get("binance_futures_symbol", "")).strip().upper(),
        }
    return result


def load_source_timezone_rules(path: Path) -> List[dict]:
    if not path.exists():
        logging.warning("source timezone rules not found: %s", path)
        return []
    df = pd.read_csv(path, dtype=str).fillna("")
    rules: List[dict] = []
    for _, row in df.iterrows():
        pattern = str(row.get("source_pattern", "")).strip().lower()
        timezone_name = str(row.get("default_timezone", "")).strip()
        if pattern and timezone_name:
            rules.append({"pattern": pattern, "timezone": timezone_name})
    return rules


def infer_source_timezone(source: str, explicit_timezone: str, rules: List[dict]) -> Tuple[str, str]:
    explicit_timezone = str(explicit_timezone).strip()
    if explicit_timezone:
        return explicit_timezone, "source_timezone_field"
    source_lower = str(source).strip().lower()
    for rule in rules:
        if rule["pattern"] in source_lower:
            return rule["timezone"], f"source_rule:{rule['pattern']}"
    return "Asia/Shanghai", "default_china"


def contains_any(text_lower: str, keywords: List[str]) -> bool:
    return any(keyword.lower() in text_lower for keyword in keywords)


def keyword_pattern(keyword: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9]+", keyword):
        return rf"(?<![A-Z0-9]){re.escape(keyword.upper())}(?![A-Z0-9])"
    return re.escape(keyword)


def detect_assets(text: str, symbol_map: Dict[str, Dict[str, str]]) -> List[str]:
    found: Set[str] = set()
    text_upper = text.upper()
    text_lower = text.lower()

    for asset, keywords in ASSET_KEYWORDS.items():
        for keyword in keywords:
            target_text = text_upper if re.fullmatch(r"[A-Za-z0-9]+", keyword) else text_lower
            target_keyword = keyword.upper() if re.fullmatch(r"[A-Za-z0-9]+", keyword) else keyword.lower()
            if re.search(keyword_pattern(target_keyword), target_text):
                found.add(asset)
                break

    for asset in symbol_map:
        if re.search(rf"(?<![A-Z0-9]){re.escape(asset)}(?![A-Z0-9])", text_upper):
            found.add(asset)

    return sorted(found)


def infer_event_type(title_lower: str, content_lower: str) -> Tuple[str, str, str, bool]:
    text_lower = f"{title_lower} {content_lower}"
    token_unlock_negative_context = [
        "解锁gpt",
        "实时语音",
        "释放被冻结资金",
        "解除制裁",
        "战略石油储备",
        "释放储备",
        "释放人质",
        "释放压力",
        "release hostages",
        "strategic petroleum reserve",
        "frozen funds",
        "sanctions relief",
    ]
    token_unlock_positive_context = [
        "token unlock",
        "tokens unlock",
        "unlock alert",
        "vesting unlock",
        "cliff unlock",
        "escrow unlock",
        "代币解锁",
        "解锁代币",
        "解锁预警",
        "代币释放",
        "归属解锁",
    ]
    if any(term in text_lower for term in token_unlock_positive_context) and not any(
        term in text_lower for term in token_unlock_negative_context
    ):
        return "token_unlock", "unlock_or_supply", "risk", False

    # Prefer title matches. Article bodies often contain old background facts
    # such as "Bitfinex hack recovery"; those should not hijack the event type.
    for event_type, event_subtype, direction_hint, keywords in EVENT_RULES:
        if contains_any(title_lower, keywords):
            return event_type, event_subtype, direction_hint, False

    if not any(term in content_lower for term in HACK_CONTEXT_FALSE_POSITIVES):
        hack_rule = EVENT_RULES[0]
        if contains_any(content_lower, hack_rule[3]):
            return hack_rule[0], hack_rule[1], hack_rule[2], False

    for event_type, event_subtype, direction_hint, keywords in EVENT_RULES[1:]:
        if contains_any(content_lower, keywords):
            return event_type, event_subtype, direction_hint, False

    for event_type, event_subtype, direction_hint, keywords in OTHER_SPLIT_RULES:
        if contains_any(title_lower, keywords) or contains_any(content_lower, keywords):
            return event_type, event_subtype, direction_hint, False

    return "other", "needs_taxonomy_review", "observe", True


def parse_time_fields(raw_value: str, default_timezone: str = "Asia/Shanghai") -> Tuple[str, str, str, str, str, str, str]:
    parsed = parse_any_time_to_utc_iso(raw_value, default_timezone=default_timezone)
    if not parsed:
        return "", "", "", "", f"{default_timezone}_for_naive_time", "failed", "time_parse_failed"
    flags = []
    if str(raw_value).strip() != parsed:
        flags.append("normalized_time")
    if parsed > datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"):
        flags.append("future_published_at")
    china = utc_iso_to_china_iso(parsed)
    return parsed, china, parsed, china, f"{default_timezone}_for_naive_time", "ok", ",".join(flags)


def parse_optional_source_time(raw_value: str, default_timezone: str) -> Tuple[str, str, str]:
    raw_value = str(raw_value).strip()
    if not raw_value:
        return "", "", ""
    parsed = parse_any_time_to_utc_iso(raw_value, default_timezone=default_timezone)
    if not parsed:
        return "", "", "source_time_parse_failed"
    return parsed, utc_iso_to_china_iso(parsed), ""


def iso_to_dt(value: str):
    value = str(value).strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def build_candidate(row: pd.Series, idx: int, symbol_map: Dict[str, Dict[str, str]], timezone_rules: List[dict]) -> dict:
    title = str(row.get("title", "")).strip()
    content = str(row.get("content", "")).strip()
    raw_published_at = str(row.get("published_at", "")).strip()
    source_timezone, source_timezone_assumption = infer_source_timezone(
        row.get("source", ""),
        row.get("source_timezone", ""),
        timezone_rules,
    )
    raw_source_published_at = first_source_time = ""
    for source_time_column in ["source_published_at", "source_time", "original_published_at"]:
        if str(row.get(source_time_column, "")).strip():
            first_source_time = str(row.get(source_time_column, "")).strip()
            break
    raw_source_published_at = first_source_time
    source_published_at_utc, source_published_at_china, source_time_flag = parse_optional_source_time(
        raw_source_published_at,
        source_timezone,
    )
    (
        published_at_utc,
        published_at_china,
        backtest_time_utc,
        backtest_time_china,
        time_timezone_assumption,
        time_parse_status,
        time_parse_flags,
    ) = parse_time_fields(raw_published_at)
    title_lower = title.lower()
    content_lower = f"{content} {row.get('tags', '')}".lower()
    text = f"{title} {content} {row.get('tags', '')}"
    text_lower = text.lower()
    flags: List[str] = []

    if time_parse_status == "failed":
        flags.append("time_parse_failed")
    if source_time_flag:
        flags.append(source_time_flag)
    if "future_published_at" in time_parse_flags:
        flags.append("future_published_at")

    assets = detect_assets(text, symbol_map)
    is_market_wide = contains_any(text_lower, MARKET_WIDE_KEYWORDS)
    event_type, event_subtype, direction_hint, unknown_type = infer_event_type(title_lower, content_lower)

    if len(assets) > 1:
        event_scope = "multi_asset"
        candidate_asset = assets[0]
        asset_confidence = "low"
        flags.append("multi_asset")
        needs_review = True
    elif len(assets) == 1:
        event_scope = "market_wide" if is_market_wide and event_type == "macro" else "single_asset"
        candidate_asset = assets[0]
        asset_confidence = "high"
        needs_review = unknown_type or is_market_wide
    elif is_market_wide:
        event_scope = "market_wide"
        candidate_asset = "BTC"
        asset_confidence = "medium"
        needs_review = True
    else:
        event_scope = "unknown"
        candidate_asset = ""
        asset_confidence = "low"
        flags.append("missing_asset")
        needs_review = True

    if is_market_wide:
        flags.append("market_wide_event")
    if unknown_type:
        flags.append("unknown_event_type")
    if time_parse_status == "failed":
        needs_review = True

    mapped = symbol_map.get(candidate_asset, {})
    source_lag_minutes = ""
    published_dt = iso_to_dt(published_at_utc)
    source_dt = iso_to_dt(source_published_at_utc)
    if published_dt and source_dt:
        source_lag_minutes = round((published_dt - source_dt).total_seconds() / 60, 2)
        if abs(float(source_lag_minutes)) > 30:
            flags.append("source_time_lag_over_30m")
        if abs(float(source_lag_minutes)) > 360:
            flags.append("source_time_lag_over_6h")

    return {
        "candidate_id": f"cand_{idx + 1:05d}",
        "raw_id": row.get("raw_id", ""),
        "raw_published_at": raw_published_at,
        "published_at": published_at_china,
        "published_at_utc": published_at_utc,
        "published_at_china": published_at_china,
        "raw_source_published_at": raw_source_published_at,
        "source_published_at_utc": source_published_at_utc,
        "source_published_at_china": source_published_at_china,
        "source_timezone": source_timezone,
        "source_timezone_assumption": source_timezone_assumption,
        "source_lag_minutes": source_lag_minutes,
        "backtest_time": backtest_time_china,
        "backtest_time_utc": backtest_time_utc,
        "backtest_time_china": backtest_time_china,
        "backtest_time_basis": "published_at",
        "time_timezone_assumption": time_timezone_assumption,
        "time_parse_status": time_parse_status,
        "time_parse_flags": time_parse_flags,
        "title": title,
        "content": content,
        "source": row.get("source", ""),
        "url": row.get("url", ""),
        "candidate_asset_symbol": candidate_asset,
        "candidate_binance_spot_symbol": mapped.get("binance_spot_symbol", ""),
        "candidate_binance_futures_symbol": mapped.get("binance_futures_symbol", ""),
        "candidate_event_type": event_type,
        "candidate_event_subtype": event_subtype,
        "candidate_direction_hint": direction_hint,
        "candidate_importance": 4 if event_type in {"hack_security", "institutional_flow", "macro"} else 3,
        "event_scope": event_scope,
        "asset_confidence": asset_confidence,
        "time_confidence": "high" if time_parse_status == "ok" else "low",
        "needs_review": str(needs_review).lower(),
        "review_decision": "",
        "review_notes": "",
        "quality_flags": ",".join(dict.fromkeys(flags)),
    }


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    symbol_map_path = normalize_path(args.symbol_map)
    source_timezone_rules_path = normalize_path(args.source_timezone_rules)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    raw = pd.read_csv(input_path, dtype=str).fillna("")
    if args.limit and args.limit > 0:
        raw = raw.head(args.limit)

    symbol_map = load_symbol_map(symbol_map_path)
    timezone_rules = load_source_timezone_rules(source_timezone_rules_path)
    rows = [build_candidate(row, idx, symbol_map, timezone_rules) for idx, row in raw.iterrows()]
    output = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    ensure_parent(output_path)
    output.to_csv(output_path, index=False)
    logging.info("wrote %s candidates to %s", len(output), output_path)
    logging.info("manual review required before building events_raw_50.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
