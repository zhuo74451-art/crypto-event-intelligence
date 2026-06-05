"""Market Radar v1.12-D — News Event Market Impact Local Feed Adapter

Provides a local news event normalization layer, rule-based classifier,
affected-assets extractor, market impact direction judgement, valid/blocked
decision, public card renderer, and debug/internal leak checker — all from
local fixtures without any external API or AI model calls.

Design principle:
  Read fixture → Normalize → Classify → Extract assets → Judge impact →
  Render public card → Check for leaks → Validate → Output.

Classes:
  NewsEvent              — normalized input record
  NewsEventSignal        — processed signal ready for card rendering

Functions:
  load_fixture(path) → list[dict]
  normalize_news_event(raw) → NewsEvent
  classify_news_event(event) → str
  extract_affected_assets(event) → list[str]
  judge_impact_direction(event, category) → str
  decide_valid_blocked(event, category) → tuple[bool, str]
  render_news_public_card(event, category, assets, direction) → str
  check_public_debug_leak(text) → list[str]
  process_news_event(raw) → dict

Security:
  - Does NOT read / print / save any token, chat_id, key, cookie, or password.
  - Does NOT access environment variables for credentials.
  - Does NOT make network calls.
  - Does NOT call any external AI service or language model.
  - Does NOT send Telegram messages.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

VERSION = "v1.12-D"
MODE = "news_event_market_impact_local_feed"

CN_TZ = timezone(timedelta(hours=8))

# ══════════════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════════════

# Category rule classification keywords
CATEGORY_RULES: dict[str, dict] = {
    "etf_flow": {
        "keywords": ["ETF", "etf", "inflows", "outflows", "基金", "资金流入",
                      "资金流出", "净流入", "净流出", "AUM", "流入", "流出",
                      "ETF净流入", "ETF净流出"],
        "priority": 1,
        "description": "ETF / 基金资金流向",
    },
    "regulation_policy": {
        "keywords": ["SEC", "CFTC", "监管", "法规", "政策", "合规", "KYC", "AML",
                      "ban", "禁止", "approve", "批准", "立法", "议会", "国会",
                      "regulatory", "regulation", "policy", "政府", "央行",
                      "central bank", "senate", "congress", "parliament"],
        "priority": 2,
        "description": "监管 / 政策动态",
    },
    "security_exploit": {
        "keywords": ["hack", "exploit", "漏洞", "攻击", "被盗", "盗取", "drain",
                      "安全事件", "bridge", "跨链桥", "盗", "compromise",
                      "phishing", "钓鱼", "rug", "scam", "fraud", "欺诈",
                      "attacker", "stolen", "breach"],
        "priority": 3,
        "description": "安全漏洞 / 攻击事件",
    },
    "exchange_event": {
        "keywords": ["listing", "delisting", "上币", "下架", "上线", "下币",
                      "Binance", "Coinbase", "OKX", "Bybit", "Kraken",
                      "交易所", "trading pair", "交易对", "suspension",
                      "暂停", "resume", "恢复", "halt"],
        "priority": 4,
        "description": "交易所上币 / 下架 / 事件",
    },
    "macro_liquidity": {
        "keywords": ["Fed", "FOMC", "CPI", "PPI", "GDP", "interest rate",
                      "利率", "加息", "降息", "通胀", "inflation",
                      "DXY", "美元", "国债", "treasury", "liquid",
                      "流动性", "QE", "QT", "缩表", "央行", "macro",
                      "宏观经济", "非农", "就业", "PMI", "ISM",
                      "ECB", "BOJ", "PBOC", "降准", "降息"],
        "priority": 5,
        "description": "宏观 / 流动性事件",
    },
    "project_update": {
        "keywords": ["upgrade", "升级", "fork", "分叉", "mainnet", "主网",
                      "testnet", "测试网", "roadmap", "路线图", "launch",
                      "发布", "release", "治理", "governance", "proposal",
                      "提案", "DAO", "community", "社区", "airdrop",
                      "空投", "tokenomics", "代币经济"],
        "priority": 6,
        "description": "项目进展 / 升级",
    },
}

# Asset name → ticker mapping (case-insensitive matching)
ASSET_NAME_MAP: dict[str, str] = {
    # Major cryptocurrencies
    "bitcoin": "BTC",
    "btc": "BTC",
    "ethereum": "ETH",
    "eth": "ETH",
    "ether": "ETH",
    "solana": "SOL",
    "sol": "SOL",
    "binance": "BNB",
    "bnb": "BNB",
    "binance coin": "BNB",
    "ripple": "XRP",
    "xrp": "XRP",
    "arbitrum": "ARB",
    "arb": "ARB",
    "optimism": "OP",
    "op": "OP",
    "hyperliquid": "HYPE",
    "hype": "HYPE",
    "tether": "USDT",
    "usdt": "USDT",
    "circle": "USDC",
    "usdc": "USDC",
    "usd coin": "USDC",
    # Additional common tokens
    "matic": "MATIC",
    "polygon": "MATIC",
    "avalanche": "AVAX",
    "avax": "AVAX",
    "cardano": "ADA",
    "ada": "ADA",
    "dogecoin": "DOGE",
    "doge": "DOGE",
    "chainlink": "LINK",
    "link": "LINK",
    "uniswap": "UNI",
    "uni": "UNI",
    "aave": "AAVE",
    "maker": "MKR",
    "mkr": "MKR",
    "sui": "SUI",
    "aptos": "APT",
    "apt": "APT",
    "near": "NEAR",
    "near protocol": "NEAR",
    "cosmos": "ATOM",
    "atom": "ATOM",
    "dot": "DOT",
    "polkadot": "DOT",
}

# Ticker list for direct matching in text
KNOWN_TICKERS = sorted(
    ["BTC", "ETH", "SOL", "BNB", "XRP", "ARB", "OP", "HYPE", "USDT", "USDC",
     "MATIC", "AVAX", "ADA", "DOGE", "LINK", "UNI", "AAVE", "MKR", "SUI",
     "APT", "ATOM", "DOT", "NEAR", "FIL", "LTC", "BCH", "TRX", "ETC"],
    key=len, reverse=True  # Match longer tickers first to avoid partial matches
)

# Forbidden terms in public output
PUBLIC_FORBIDDEN_TERMS = [
    "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
    "payload_render", "format_check", "content_quality",
    "debug", "internal", "trace", "fixture", "secret",
    "api_key", "chat_id", "password",
    "价值:", "冷却:", "pre_send:", "allow", "upgrade_override",
    "not_reached", "mock_sent", "mock_message_id",
    "gate_decision", "score↑", "blocked_by", "gate_version",
    "factor_hits", "block_reason", "block_rules", "block_triggered",
    "admission_result",
    # Extra: local absolute paths
    "C:\\Users", "C:\\Program", "D:\\", "/home/", "/Users/",
]


# ══════════════════════════════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class NewsEvent:
    """Normalized news event record."""
    event_id: str = ""
    published_at: str = ""
    source: str = ""
    headline: str = ""
    body: str = ""
    url: str = ""
    raw_assets: list[str] = field(default_factory=list)
    data_mode: str = "fixture"
    is_fixture: bool = True
    event_type: str = "其他"  # From registry schema
    trading_relevance: str = "待评估"
    already_priced: str = "未知"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NewsEventSignal:
    """Processed news event signal ready for card rendering."""
    event_id: str = ""
    published_at: str = ""
    source: str = ""
    headline: str = ""
    body: str = ""
    url: str = ""
    category: str = "unknown"
    affected_assets: list[str] = field(default_factory=list)
    impact_direction: str = "neutral"  # bullish | bearish | neutral
    valid: bool = False
    blocked: bool = True
    block_reason: str = ""
    data_mode: str = "fixture"
    is_fixture: bool = True
    live_ready: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["affected_assets"] = self.affected_assets  # ensure list
        return d


# ══════════════════════════════════════════════════════════════════════════════════════
# Fixture Loading
# ══════════════════════════════════════════════════════════════════════════════════════

def load_fixture(fixture_path: str | Path | None = None) -> list[dict]:
    """Load the v112d news event fixture JSON.

    Args:
        fixture_path: Path to fixture file. If None, uses default path.

    Returns:
        List of raw event dicts from the fixture.
    """
    if fixture_path is None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "data" / "fixtures" / "market_radar_v112d_news_events.json"
        )
    else:
        fixture_path = Path(fixture_path)

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("news_events", [])


# ══════════════════════════════════════════════════════════════════════════════════════
# Normalize
# ══════════════════════════════════════════════════════════════════════════════════════

def normalize_news_event(raw: dict) -> NewsEvent:
    """Normalize a raw news event dict into a NewsEvent.

    Handles multiple field name conventions from different fixture formats.
    """
    def _s(key, default=""):
        val = raw.get(key, default)
        if val is None:
            return default
        return str(val).strip()

    event_id = _s("event_id", raw.get("sample_id", ""))
    published_at = _s("published_at", "")
    source = _s("source", "")
    headline = _s("headline", "")
    # Body can come from body, summary, or description fields
    body = _s("body", _s("summary", _s("description", "")))
    url = _s("url", "")

    # raw_assets can be a list or comma-separated string
    raw_assets_val = raw.get("raw_assets", [])
    if isinstance(raw_assets_val, str):
        raw_assets = [a.strip() for a in raw_assets_val.split(",") if a.strip()]
    elif isinstance(raw_assets_val, list):
        raw_assets = [str(a).strip() for a in raw_assets_val if str(a).strip()]
    else:
        raw_assets = []

    data_mode = _s("data_mode", "fixture")
    is_fixture = raw.get("is_fixture", True)
    if isinstance(is_fixture, str):
        is_fixture = is_fixture.lower() in ("true", "1", "yes")
    event_type = _s("event_type", "其他")
    trading_relevance = _s("trading_relevance", "待评估")
    already_priced = _s("already_priced", "未知")

    return NewsEvent(
        event_id=event_id,
        published_at=published_at,
        source=source,
        headline=headline,
        body=body,
        url=url,
        raw_assets=raw_assets,
        data_mode=data_mode,
        is_fixture=is_fixture,
        event_type=event_type,
        trading_relevance=trading_relevance,
        already_priced=already_priced,
    )


# ══════════════════════════════════════════════════════════════════════════════════════
# Rule-Based Classifier
# ══════════════════════════════════════════════════════════════════════════════════════

def classify_news_event(event: NewsEvent) -> str:
    """Rule-based news event category classification.

    Scans headline + body text against keyword rules for each category.
    Categories are checked in priority order — first match wins.

    Returns one of:
      etf_flow, regulation_policy, security_exploit, exchange_event,
      macro_liquidity, project_update, unknown
    """
    text = f"{event.headline} {event.body}".lower()

    # Check categories in priority order (use word-boundary matching for all)
    sorted_categories = sorted(CATEGORY_RULES.items(), key=lambda x: x[1]["priority"])

    for cat_name, cat_def in sorted_categories:
        for kw in cat_def["keywords"]:
            kw_lower = kw.lower()
            # Use word boundary for all keywords to avoid false positives
            # (e.g., "flow" should not match inside "outflow", "volume" in generic text)
            if re.search(r'\b' + re.escape(kw_lower) + r'\b', text):
                return cat_name

    # If headline/body mention specific exchanges by name, classify as exchange_event
    exchange_names = ["binance", "coinbase", "okx", "bybit", "kraken", "upbit",
                      "gate.io", "kucoin", "huobi", "bitget", "bitfinex"]
    for ex in exchange_names:
        if ex in text:
            return "exchange_event"

    # If event_type from registry schema is populated, try mapping
    if event.event_type:
        type_lower = event.event_type.strip().lower()
        mapping = {
            "etf": "etf_flow",
            "监管": "regulation_policy",
            "政策": "regulation_policy",
            "安全": "security_exploit",
            "事故": "security_exploit",
            "上线": "exchange_event",
            "交易所": "exchange_event",
            "宏观": "macro_liquidity",
            "技术": "project_update",
            "合作": "project_update",
        }
        for ch_key, ch_cat in mapping.items():
            if ch_key in type_lower or ch_key in event.event_type:
                return ch_cat

    return "unknown"


# ══════════════════════════════════════════════════════════════════════════════════════
# Affected Assets Extraction
# ══════════════════════════════════════════════════════════════════════════════════════

def extract_affected_assets(event: NewsEvent) -> list[str]:
    """Extract affected asset tickers from the news event.

    Uses:
      1. raw_assets if present (pre-specified)
      2. Ticker pattern matching in headline + body
      3. Asset name → ticker mapping for full names like "Bitcoin" → "BTC"

    Returns a deduplicated list of uppercase tickers.
    """
    assets: set[str] = set()

    # 1. From raw_assets
    for ra in event.raw_assets:
        ticker = _resolve_ticker(ra)
        if ticker:
            assets.add(ticker)

    # 2. Direct ticker pattern matching in headline + body
    text = f"{event.headline} {event.body}"
    for ticker in KNOWN_TICKERS:
        # Match ticker as a word boundary (e.g. "BTC" but not "WBTC" unless WBTC is known)
        pattern = re.compile(r'\b' + re.escape(ticker) + r'\b', re.IGNORECASE)
        if pattern.search(text):
            assets.add(ticker)

    # 3. Asset name mapping
    text_lower = text.lower()
    for name, ticker in ASSET_NAME_MAP.items():
        # Only map names with 3+ chars to avoid false positives on short strings
        if len(name) >= 3 and name in text_lower:
            assets.add(ticker)

    # 4. Special case: "DeFi" mentions → add ETH as affected
    if re.search(r'\bdefi\b', text_lower):
        assets.add("ETH")

    return sorted(assets)


def _resolve_ticker(raw: str) -> str | None:
    """Resolve a raw asset name/string to a standard ticker."""
    raw_upper = raw.strip().upper()
    # If it's already a known ticker, return directly
    if raw_upper in set(ASSET_NAME_MAP.values()):
        return raw_upper
    # If it's a known asset name, map it
    if raw_upper in ASSET_NAME_MAP:
        return ASSET_NAME_MAP[raw_upper]
    # Try lower case
    raw_lower = raw.strip().lower()
    if raw_lower in ASSET_NAME_MAP:
        return ASSET_NAME_MAP[raw_lower]
    # If it looks like a ticker (2-5 uppercase letters/digits), accept it
    if re.match(r'^[A-Z]{2,5}[0-9]?$', raw_upper):
        return raw_upper
    return None


# ══════════════════════════════════════════════════════════════════════════════════════
# Impact Direction Judgement
# ══════════════════════════════════════════════════════════════════════════════════════

def judge_impact_direction(event: NewsEvent, category: str) -> str:
    """Judge the market impact direction based on category and content analysis.

    Returns: 'bullish' | 'bearish' | 'neutral'
    """
    text = (f"{event.headline} {event.body}").lower()

    # ── Category-based default direction ─────────────────────────────────
    category_defaults: dict[str, str] = {
        "etf_flow": "bullish",        # ETF flows generally bullish by default
        "regulation_policy": "bearish",  # Most regulation news is restrictive
        "security_exploit": "bearish",   # Exploits are negative
        "exchange_event": "bullish",     # Listings generally bullish
        "macro_liquidity": "neutral",    # Depends on specifics
        "project_update": "neutral",
        "unknown": "neutral",
    }
    base_direction = category_defaults.get(category, "neutral")

    # ── Override based on explicit sentiment indicators ───────────────────

    # Bullish indicators
    bullish_terms = [
        "bullish", "surge", "soar", "rocket", "gain", "rally", "rise",
        "涨", "上涨", "暴涨", "利好", "积极", "正面",
        "approve", "批准", "inflow", "流入", "rate cut", "降息",
        "listing", "上线", "partnership", "合作", "adopt", "采用",
        "QE", "量化宽松", "launch", "发布",
    ]
    # Bearish indicators
    bearish_terms = [
        "bearish", "crash", "dump", "drop", "plunge", "fall", "decline",
        "跌", "下跌", "暴跌", "利空", "负面", "消极",
        "reject", "拒绝", "deny", "outflow", "流出", "rate hike", "加息",
        "delisting", "下架", "ban", "禁止", "crackdown", "打压",
        "hack", "攻击", "exploit", "漏洞", "drain", "被盗",
        "liquidate", "清算", "collapse", "崩溃",
    ]

    bullish_count = sum(1 for t in bullish_terms if t in text)
    bearish_count = sum(1 for t in bearish_terms if t in text)

    # ── Override direction ──────────────────────────────────────────────
    if bullish_count > bearish_count:
        return "bullish"
    elif bearish_count > bullish_count:
        return "bearish"
    else:
        return base_direction


# ══════════════════════════════════════════════════════════════════════════════════════
# Valid / Blocked Decision
# ══════════════════════════════════════════════════════════════════════════════════════

def decide_valid_blocked(
    event: NewsEvent,
    category: str,
    affected_assets: list[str],
) -> tuple[bool, str]:
    """Decide whether a news event should be valid or blocked.

    Returns:
        (is_valid: bool, block_reason: str)
        If is_valid=False, block_reason explains why.
    """
    reasons: list[str] = []

    # 1. Missing event_id or headline
    if not event.event_id or not event.headline:
        reasons.append("缺少事件 ID 或标题")

    # 2. Trading relevance is none / very low
    if event.trading_relevance in ("无", "极低", "none"):
        reasons.append(f"交易相关性为「{event.trading_relevance}」")

    # 3. Already fully priced
    if event.already_priced in ("已定价", "fully priced"):
        reasons.append("事件已被市场完全定价")

    # 4. No affected assets found
    if len(affected_assets) == 0:
        reasons.append("无法提取受影响资产")

    # 5. Category is unknown and no clear affected assets
    if category == "unknown" and len(affected_assets) == 0:
        reasons.append("分类未知且无明确受影响资产")

    if reasons:
        return False, "；".join(reasons)

    return True, ""


# ══════════════════════════════════════════════════════════════════════════════════════
# Public Card Renderer
# ══════════════════════════════════════════════════════════════════════════════════════

def render_news_public_card(
    event: NewsEvent,
    category: str,
    affected_assets: list[str],
    impact_direction: str,
) -> str:
    """Render a clean public card for the news event.

    The output MUST NOT contain any debug, internal, fixture, secret, token,
    api_key, chat_id, password, or local absolute path references.

    Args:
        event: Normalized news event.
        category: Classified category.
        affected_assets: List of asset tickers.
        impact_direction: bullish / bearish / neutral.

    Returns:
        Multi-line public card text.
    """
    # ── Category display ──────────────────────────────────────────────────
    category_display: dict[str, str] = {
        "etf_flow": "ETF资金流向",
        "regulation_policy": "监管政策",
        "security_exploit": "安全事件",
        "exchange_event": "交易所事件",
        "macro_liquidity": "宏观流动性",
        "project_update": "项目进展",
        "unknown": "其他",
    }

    category_icons: dict[str, str] = {
        "etf_flow": "📊",
        "regulation_policy": "🏛️",
        "security_exploit": "🔒",
        "exchange_event": "🏦",
        "macro_liquidity": "🌍",
        "project_update": "🔧",
        "unknown": "📰",
    }

    direction_icons: dict[str, str] = {
        "bullish": "🟢",
        "bearish": "🔴",
        "neutral": "🟡",
    }
    direction_labels: dict[str, str] = {
        "bullish": "偏多",
        "bearish": "偏空",
        "neutral": "中性",
    }

    cat_display = category_display.get(category, "其他")
    cat_icon = category_icons.get(category, "📰")
    dir_icon = direction_icons.get(impact_direction, "🟡")
    dir_label = direction_labels.get(impact_direction, "中性")

    # ── Build card ────────────────────────────────────────────────────────
    lines = [
        f"{cat_icon} 新闻事件｜{event.headline}",
        "",
        f"{dir_icon} 市场影响方向：{dir_label}",
        "",
        f"{event.event_type}类型事件，影响 {' / '.join(affected_assets) if affected_assets else '待确认'}。",
        "",
    ]

    # Key fields
    lines.append(f"● 事件分类：{cat_display}")
    lines.append(f"● 受影响资产：{', '.join(affected_assets) if affected_assets else '待确认'}")
    if event.source:
        lines.append(f"● 来源：{event.source}")
    if event.published_at:
        lines.append(f"● 发布时间：{event.published_at}")
    lines.append(f"● 交易相关性：{event.trading_relevance}")
    lines.append(f"● 是否已被定价：{event.already_priced}")
    lines.append("")

    # Links
    primary_asset = affected_assets[0] if affected_assets else ""
    if primary_asset:
        lines.append(f"🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query={primary_asset}) / [DexScreener](https://dexscreener.com/search?q={primary_asset})")
        lines.append("")

    if event.url:
        lines.append(f"📎 原文链接：{event.url}")
        lines.append("")

    lines.append("⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════════════
# Debug / Internal Leak Check
# ══════════════════════════════════════════════════════════════════════════════════════

def check_public_debug_leak(text: str) -> list[str]:
    """Check rendered public card text for forbidden internal/debug/secret terms.

    Also checks for local absolute path patterns.

    Args:
        text: The public card text to check.

    Returns:
        List of forbidden terms/patterns found.
    """
    found: list[str] = []
    text_lower = text.lower()

    # Check forbidden terms
    for term in PUBLIC_FORBIDDEN_TERMS:
        if term.lower() in text_lower:
            found.append(term)

    # Check for local paths more thoroughly
    path_patterns = [
        r'[A-Za-z]:\\(?:Users|Program|Windows|tmp|var|home|etc|opt|dev)',
        r'/(?:home|Users|tmp|var|etc|opt|dev)/',
    ]
    for pat in path_patterns:
        if re.search(pat, text, re.IGNORECASE):
            found.append(f"local_path_pattern:{pat}")

    return found


# ══════════════════════════════════════════════════════════════════════════════════════
# End-to-End Processing
# ══════════════════════════════════════════════════════════════════════════════════════

def process_news_event(raw: dict) -> dict:
    """End-to-end processing of a single raw news event dict.

    Pipeline:
      normalize → classify → extract assets → judge impact →
      decide valid/blocked → render public card → check leaks

    Args:
        raw: Raw event dict from fixture (can be the wrapper or the inner signal).

    Returns:
        Dict with all processing results suitable for the runner.
    """
    sample_id = raw.get("sample_id", "unknown")
    data_mode = raw.get("data_mode", "fixture")

    # Extract the signal (fixture wraps signal inside a wrapper with expected fields)
    signal_raw = raw.get("signal", raw)

    # 1. Normalize
    event = normalize_news_event(signal_raw)
    if not event.event_id:
        event.event_id = sample_id

    # 2. Classify
    category = classify_news_event(event)

    # 3. Extract affected assets
    affected_assets = extract_affected_assets(event)

    # 4. Judge impact direction
    impact_direction = judge_impact_direction(event, category)

    # 5. Decide valid / blocked
    is_valid, block_reason = decide_valid_blocked(event, category, affected_assets)

    # 6. Render public card (only for valid events)
    public_card = ""
    debug_leak_terms: list[str] = []
    if is_valid:
        public_card = render_news_public_card(event, category, affected_assets, impact_direction)
        debug_leak_terms = check_public_debug_leak(public_card)

    # 7. Build signal
    signal = NewsEventSignal(
        event_id=event.event_id,
        published_at=event.published_at,
        source=event.source,
        headline=event.headline,
        body=event.body[:200] if event.body else "",
        url=event.url,
        category=category,
        affected_assets=affected_assets,
        impact_direction=impact_direction,
        valid=is_valid,
        blocked=not is_valid,
        block_reason=block_reason,
        data_mode=data_mode,
        is_fixture=True,
        live_ready=False,
    )

    return {
        "sample_id": sample_id,
        "data_mode": data_mode,
        "valid": is_valid,
        "blocked": not is_valid,
        "block_reason": block_reason,
        "category": category,
        "affected_assets": affected_assets,
        "impact_direction": impact_direction,
        "public_card": public_card,
        "public_card_length": len(public_card),
        "debug_leak_terms": debug_leak_terms,
        "debug_leak_free": len(debug_leak_terms) == 0,
        "signal": signal.to_dict(),
        "live_ready": False,
    }


def china_stamp() -> str:
    """Return current time in UTC+8 format."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
