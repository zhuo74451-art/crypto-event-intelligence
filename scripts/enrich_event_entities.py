import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


EVENT_L1_RULES = [
    ("regulation_macro", "bitcoin_reserve_policy", ["strategic bitcoin reserve", "bitcoin reserve", "比特币储备"]),
    ("onchain_data", "wallet_metric", ["santiment", "glassnode", "持有至少", "钱包数量", "large wallets", "wallets surge"]),
    ("onchain_data", "protocol_metric", ["defillama", "messari", "tvl", "链上应用", "协议收入"]),
    # "洗钱" 从 legal_enforcement 移至 hack_security：黑客事件标题常出现"铸造XXX并洗钱"，
    # 应分类为 hack_security 而非执法事件；DOJ 执法有 "司法部"/"被判"/"庞氏" 等关键词兜底
    ("legal_enforcement", "fraud_or_enforcement", ["ponzi", "scam", "fraud", "庞氏", "骗局", "bounty", "赏金", "司法部", "被判"]),
    # "洗钱" + "tornado cash"：黑客资金流出路径的强信号词
    ("hack_security", "exploit_or_theft", ["hack", "hacked", "exploit", "攻击", "被盗", "漏洞", "钓鱼", "黑客", "tornado cash", "洗钱"]),
    ("exchange_listing", "listing_delisting", ["listing", "delisting", "上线", "上架", "下架", "list "]),
    ("institutional_flow", "etf_or_fund_flow", ["bitwise", "blackrock", "fidelity", "strategy", "microstrategy", "saylor", "etf", "fund issuer", "issuer", "inflow", "outflow", "fund"]),
    ("token_supply", "unlock_or_supply", ["token unlock", "tokens unlock", "unlock alert", "vesting unlock", "cliff unlock", "escrow unlock", "代币解锁", "解锁代币", "解锁预警", "代币释放", "归属解锁", "mint", "burn", "铸造", "销毁"]),
    ("network_upgrade", "upgrade_or_fork", ["upgrade", "mainnet", "fork", "hard fork", "dencun", "升级", "主网", "分叉"]),
    (
        "whale_position",
        "whale_wallet_position",
        [
            "whale",
            "巨鲸",
            "地址",
            "钱包",
            "多单",
            "空单",
            "清算",
            "持仓",
            "liquidation",
            "聪明钱",
            "开多",
            "开空",
            "做多",   # 补充：中文多头动词，与"开多/多单"是同义表述
            "做空",   # 补充：中文空头动词，与"开空/空单"是同义表述
            "加仓",
            "滚仓",
            "转入",
            "转出",
            "充值",
            "存入",
            "多签",
            "项目方",
        ],
    ),
    ("project_business", "payment_adoption", ["crypto card", "加密卡", "实体加密卡", "custody", "保管服务", "托管"]),
    ("regulation_macro", "license", ["bitlicense", "牌照", "license"]),
    ("institutional_flow", "etf_or_fund_flow", ["etf", "strategy", "microstrategy", "saylor", "inflow", "outflow", "fund", "blackrock", "fidelity", "机构", "流入"]),
    ("regulation_macro", "regulation", ["sec", "cftc", "监管", "lawsuit", "诉讼", "clarity act", "法案", "market-structure bill"]),
    ("regulation_macro", "macro", ["cpi", "ppi", "fed", "fomc", "rate", "利率", "美联储", "非农", "美元", "纳斯达克", "原油", "关税"]),
    ("stablecoin_flow", "stablecoin", ["stablecoin", "stablecoins", "稳定币"]),
    ("project_business", "rwa_tokenization", ["rwa", "tokenized", "tokenization", "代币化"]),
    ("project_business", "foundation_team", ["foundation", "基金会", "resign", "离职"]),
    ("market_structure", "price_market_structure", ["resistance", "support", "profit taking", "breakout", "支撑", "阻力", "获利了结"]),
]

PROTOCOL_INCIDENT_TERMS = [
    "abnormal",
    "anomaly",
    "incident",
    "paused",
    "pause",
    "suspended",
    "suspend",
    "halted",
    "halt",
    "market paused",
    "temporarily paused",
    "\u5f02\u5e38",
    "\u6682\u505c",
    "\u4e2d\u6b62",
    "\u98ce\u9669\u63d0\u793a",
]
PROTOCOL_INCIDENT_CONTEXT_TERMS = [
    "curvance",
    "echo",
    "ebtc",
    "protocol",
    "market",
    "pool",
    "vault",
    "lending",
    "defi",
    "\u534f\u8bae",
    "\u5e02\u573a",
    "\u501f\u8d37",
    "\u6d41\u52a8\u6027",
]

GENERIC_PRICE_TERMS = ["price slips", "price drops", "price rises", "上涨", "下跌", "跌破", "突破"]
DIGEST_TITLE_TERMS = ["星球早讯", "今日新闻摘要", "夜盘主力合约收盘", "早讯", "晚报"]
AI_ONLY_TERMS = ["gpt", "gemini", "openai", "cursor", "claude", "swe-bench", "colossus", "ai云", "算力限额"]
OPINION_TERMS = [
    "i sincerely questioned",
    "be patient",
    "the lesson",
    "what to expect",
    "analyst predicts",
    "price forecast",
    "price prediction",
    "我认为",
    "观点",
    # 中文分析/预测类表述：Delphi Digital / 机构研报类文章的典型句式
    "表现可能优于",
    "或继续上升",
    "预计将",
    "历史上通常对应",
    "maps out",          # "Analyst Maps Out XRP's Next Big Move" 类标题
    "next big move",
    "disclaimer: the opinions expressed",
]
GENERIC_MARKET_COMMENTARY_TERMS = [
    "liquidations everywhere",
    "volume spiking",
    "markets went down",
    "weekly candles",
    "monthly candles",
    "ultimate area of accumulation",
]
SCRAPED_FOOTER_TERMS = [
    "bitcoin news price businesses acceptance technology investment regulation reviews",
    "editorial process",
    "privacy policy",
    "this website uses cookies",
    "all rights reserved",
    # 赞助/PR 文章声明：crypto.news 等媒体的第三方广告内容都带此 disclosure
    "this content is provided by a third party",
    "does not represent investment advice",
    "the content and materials featured on this page are for educational purposes only",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich event candidates with entities and v0.6 taxonomy.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "data" / "event_candidates_real_500_older_review_suggested.csv"),
    )
    parser.add_argument("--entity-dictionary", default=str(ROOT / "data" / "entity_dictionary.csv"))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "event_candidates_v06_enriched.csv"))
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def split_aliases(value: str) -> list[str]:
    return [part.strip() for part in str(value).split("|") if part.strip()]


def is_ascii_token(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9$._-]+", value))


def alias_matches(text_upper: str, text_lower: str, alias: str) -> bool:
    alias = alias.strip()
    if not alias:
        return False
    if is_ascii_token(alias):
        token = alias.upper().lstrip("$")
        return re.search(rf"(?<![A-Z0-9])\$?{re.escape(token)}(?![A-Z0-9])", text_upper) is not None
    return alias.lower() in text_lower


def load_dictionary(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"entity dictionary not found: {path}")
    df = pd.read_csv(path, dtype=str).fillna("")
    required = {"entity_id", "entity_type", "canonical_symbol", "canonical_name", "aliases", "market_scope"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"entity dictionary missing columns: {sorted(missing)}")
    return df


def load_symbol_map(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str).fillna("")
    rows: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        asset = str(row.get("asset_symbol", "")).strip().upper()
        if not asset:
            continue
        rows[asset] = {
            "binance_spot_symbol": str(row.get("binance_spot_symbol", "")).strip().upper(),
            "binance_futures_symbol": str(row.get("binance_futures_symbol", "")).strip().upper(),
        }
    return rows


def detect_entities(text: str, dictionary: pd.DataFrame) -> list[dict]:
    text_upper = text.upper()
    text_lower = text.lower()
    matches = []
    for _, row in dictionary.iterrows():
        aliases = split_aliases(row.get("aliases", ""))
        matched_aliases = [alias for alias in aliases if alias_matches(text_upper, text_lower, alias)]
        if not matched_aliases:
            continue
        matches.append(
            {
                "entity_id": row["entity_id"],
                "entity_type": row["entity_type"],
                "canonical_symbol": row["canonical_symbol"],
                "canonical_name": row["canonical_name"],
                "market_scope": row["market_scope"],
                "matched_aliases": matched_aliases,
            }
        )
    return matches


def infer_taxonomy(title_lower: str, text_lower: str, current_type: str) -> tuple[str, str]:
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
        return "token_supply", "unlock_or_supply"
    if any(term in text_lower for term in PROTOCOL_INCIDENT_TERMS) and any(
        term in text_lower for term in PROTOCOL_INCIDENT_CONTEXT_TERMS
    ):
        return "hack_security", "protocol_incident"
    for l1, l2, keywords in EVENT_L1_RULES:
        if any(keyword.lower() in title_lower for keyword in keywords):
            return l1, l2
    for l1, l2, keywords in EVENT_L1_RULES:
        if any(keyword.lower() in text_lower for keyword in keywords):
            return l1, l2
    if current_type and current_type != "other":
        mapping = {
            "macro": ("regulation_macro", "macro"),
            "token_unlock": ("token_supply", "unlock_or_supply"),
        }
        return mapping.get(current_type, (current_type, current_type))
    return "other_review", "needs_taxonomy_review"


def choose_primary_entity(matches: list[dict], candidate_asset: str, title: str) -> dict | None:
    assets = [m for m in matches if m["entity_type"] == "asset"]
    title_upper = str(title).upper()
    title_assets = []
    for entity in assets:
        aliases = entity.get("matched_aliases", [])
        positions = []
        for alias in aliases:
            token = alias.upper().lstrip("$")
            pos = title_upper.find(token)
            if pos >= 0:
                positions.append(pos)
        if positions:
            title_assets.append((min(positions), entity))
    if title_assets:
        return sorted(title_assets, key=lambda item: item[0])[0][1]

    candidate_asset = str(candidate_asset).strip().upper()
    if candidate_asset:
        for entity in assets:
            if entity["canonical_symbol"].upper() == candidate_asset:
                return entity
    if assets:
        return assets[0]
    for preferred in ["project", "org", "data_source", "regulator", "macro", "exchange", "sector", "actor"]:
        for entity in matches:
            if entity["entity_type"] == preferred:
                return entity
    return matches[0] if matches else None


def entity_quality(matches: list[dict], primary: dict | None, row: pd.Series) -> tuple[int, list[str]]:
    flags = []
    if not matches:
        return 0, ["no_entity_detected"]
    score = 40
    if primary:
        score += 20
        if primary["entity_type"] == "asset":
            score += 25
        elif primary["entity_type"] in {"org", "regulator", "macro"}:
            score += 15
    asset_count = sum(1 for m in matches if m["entity_type"] == "asset")
    if asset_count > 1:
        score -= 20
        flags.append("multiple_assets_detected")
    if str(row.get("candidate_asset_symbol", "")).strip() and primary and primary["entity_type"] == "asset":
        if primary["canonical_symbol"].upper() != str(row.get("candidate_asset_symbol", "")).strip().upper():
            flags.append("candidate_asset_mismatch")
            score -= 15
    return max(0, min(score, 100)), flags


def join_values(values: Iterable[str]) -> str:
    return "|".join([str(value) for value in values if str(value).strip()])


def symbol_info(symbol_map: dict[str, dict[str, str]], asset: str) -> dict[str, str]:
    return symbol_map.get(str(asset).strip().upper(), {"binance_spot_symbol": "", "binance_futures_symbol": ""})


def enrich_row(row: pd.Series, dictionary: pd.DataFrame, symbol_map: dict[str, dict[str, str]]) -> dict:
    title = str(row.get("title", ""))
    content = str(row.get("content", ""))
    focused_content = content[:1500]
    text = f"{title} {focused_content}"
    text_lower = text.lower()
    matches = detect_entities(text, dictionary)
    primary = choose_primary_entity(matches, row.get("candidate_asset_symbol", ""), title)
    score, flags = entity_quality(matches, primary, row)
    event_type_l1, event_type_l2 = infer_taxonomy(title.lower(), text_lower, str(row.get("candidate_event_type", "")).strip())

    if event_type_l1 == "other_review":
        flags.append("other_review")
    if any(term in text_lower for term in GENERIC_PRICE_TERMS):
        flags.append("possible_price_recap")
    if any(term in title for term in DIGEST_TITLE_TERMS):
        flags.append("digest_or_market_recap")
    title_lower = title.lower()
    if any(term in title_lower for term in AI_ONLY_TERMS):
        has_crypto_in_title = any(
            term in title_lower
            for term in ["crypto", "bitcoin", "ethereum", "blockchain", "token", "wallet", "加密", "比特币", "以太坊", "链上", "代币", "钱包"]
        )
        if not has_crypto_in_title:
            flags.append("ai_only_non_crypto")
    combined_lower = f"{title_lower} {focused_content.lower()}"
    if any(term in combined_lower for term in OPINION_TERMS):
        flags.append("opinion_or_analysis")
    if any(term in combined_lower for term in GENERIC_MARKET_COMMENTARY_TERMS):
        flags.append("generic_market_commentary")
    if any(term in combined_lower for term in SCRAPED_FOOTER_TERMS):
        flags.append("scraped_footer_noise")

    primary_asset_symbol = ""
    if primary and primary["entity_type"] == "asset":
        primary_asset_symbol = primary["canonical_symbol"].upper()
    elif any(m["entity_type"] == "asset" for m in matches):
        primary_asset_symbol = str(row.get("candidate_asset_symbol", "")).strip().upper()
    candidate_asset = str(row.get("candidate_asset_symbol", "")).strip().upper()
    effective_asset_symbol = primary_asset_symbol or candidate_asset
    primary_symbols = symbol_info(symbol_map, primary_asset_symbol) if primary_asset_symbol else {
        "binance_spot_symbol": "",
        "binance_futures_symbol": "",
    }
    effective_symbols = symbol_info(symbol_map, effective_asset_symbol) if effective_asset_symbol else {
        "binance_spot_symbol": "",
        "binance_futures_symbol": "",
    }
    if not effective_symbols["binance_spot_symbol"] and not effective_symbols["binance_futures_symbol"]:
        if not primary_asset_symbol or primary_asset_symbol == candidate_asset:
            effective_symbols = {
                "binance_spot_symbol": str(row.get("candidate_binance_spot_symbol", "")).strip().upper(),
                "binance_futures_symbol": str(row.get("candidate_binance_futures_symbol", "")).strip().upper(),
            }

    result = row.to_dict()
    result.update(
        {
            "detected_entities": join_values([m["entity_id"] for m in matches]),
            "detected_entity_names": join_values([m["canonical_name"] for m in matches]),
            "primary_entity": primary["entity_id"] if primary else "",
            "primary_entity_type": primary["entity_type"] if primary else "",
            "primary_asset_symbol": primary_asset_symbol,
            "primary_binance_spot_symbol": primary_symbols["binance_spot_symbol"],
            "primary_binance_futures_symbol": primary_symbols["binance_futures_symbol"],
            "effective_asset_symbol": effective_asset_symbol,
            "effective_binance_spot_symbol": effective_symbols["binance_spot_symbol"],
            "effective_binance_futures_symbol": effective_symbols["binance_futures_symbol"],
            "entity_quality_score": score,
            "entity_flags": ",".join(dict.fromkeys(flags)),
            "event_type_l1": event_type_l1,
            "event_type_l2": event_type_l2,
        }
    )
    return result


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    dictionary_path = normalize_path(args.entity_dictionary)
    symbol_map_path = normalize_path(args.symbol_map)
    output_path = normalize_path(args.output)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1
    dictionary = load_dictionary(dictionary_path)
    symbol_map = load_symbol_map(symbol_map_path)
    df = pd.read_csv(input_path, dtype=str).fillna("")
    enriched = pd.DataFrame([enrich_row(row, dictionary, symbol_map) for _, row in df.iterrows()])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(output_path, index=False)
    logging.info("wrote %s enriched candidates to %s", len(enriched), output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
