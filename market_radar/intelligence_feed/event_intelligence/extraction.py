"""Deterministic entity/asset/topic extraction — rules only, no LLM.

Rules:
  - Asset matching via symbol/full-name dictionary
  - Entity matching via keyword patterns
  - Topic matching via keyword groups
  - Anti-patterns prevent false positives
"""
from __future__ import annotations
import re
from typing import Optional

from .models import Asset, Entity, Topic, ExtractionResult

# ── Asset Dictionary ───────────────────────────────────────────────────────────

ASSET_MAP: dict[str, tuple[str, str]] = {
    # symbol -> (full_name, regex_pattern)
    "BTC": ("Bitcoin", r"\b(?:bitcoin|btc)\b"),
    "ETH": ("Ethereum", r"\b(?:ethereum|eth)\b"),
    "SOL": ("Solana", r"\b(?:solana|sol)\b"),
    "HYPE": ("Hyperliquid", r"\b(?:hyperliquid|hype)\b"),
    "USDT": ("Tether", r"\b(?:tether|usdt)\b"),
    "USDC": ("USD Coin", r"\b(?:usd coin|usdc)\b"),
    "BNB": ("BNB", r"\b(?:bnb)\b"),
    "XRP": ("XRP", r"\b(?:xrp|ripple)\b"),
    "ADA": ("Cardano", r"\b(?:cardano|ada)\b"),
    "DOGE": ("Dogecoin", r"\b(?:dogecoin|doge)\b"),
    "AVAX": ("Avalanche", r"\b(?:avalanche|avax)\b"),
    "DOT": ("Polkadot", r"\b(?:polkadot|dot)\b"),
    "MATIC": ("Polygon", r"\b(?:polygon|matic)\b"),
    "LINK": ("Chainlink", r"\b(?:chainlink|link)\b"),
    "UNI": ("Uniswap", r"\b(?:uniswap|uni)\b"),
}

# Anti-patterns: words that look like tickers but aren't
_ANTI_TICKER = {"HODL", "ATH", "ATHS", "ETF", "DEX", "CEX", "KYC", "AML",
                "API", "UI", "AI", "GDP", "YTD", "TVL", "NFT", "DeFi"}

_ENTITY_PATTERNS: list[tuple[str, str, float]] = [
    # (entity_type, regex_pattern, confidence)
    ("exchange", r"\b(?:binance|coinbase|kraken|okx|bybit|bitfinex|huobi|gate\.io)\b", 0.9),
    ("protocol", r"\b(?:uniswap|aave|compound|curve|maker|sushi|pancakeswap|hyperliquid|dydx)\b", 0.85),
    ("regulator", r"\b(?:sec|cf tc|esma|fca|finma|mas|fsa|banque de france|bafin)\b", 0.9),
    ("foundation", r"\b(?:ethereum foundation|solana foundation|hyper foundation|cardano foundation)\b", 0.85),
    ("company", r"\b(?:microstrategy|tesla|microsoft|blackrock|fidelity|grayscale|coinbase)\b", 0.8),
    ("country", r"\b(?:china|usa|united states|eu|european union|japan|south korea|singapore|russia|uk)\b", 0.7),
    ("person", r"\b(?:cbdc|trump|biden|powell|gresham|saylor)\b", 0.5),
]

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "listing": ["list", "listed", "listing", "new trading pair", "will list", "to list", "listing on"],
    "delisting": ["delist", "delisting", "remove", "removal", "suspended trading"],
    "exploit": ["hack", "hacked", "exploit", "exploited", "breach", "compromised", "attack", "drain", "stolen"],
    "security": ["vulnerability", "bug", "patch", "audit", "security flaw", "update"],
    "regulation": ["regulat", "sec", "cf tc", "compliant", "compliance", "license", "registered"],
    "macro": ["fed", "federal reserve", "rate cut", "rate hike", "inflation", "cpi", "ppi", "gdp",
              "central bank", "monetary policy", "treasury", "bond", "yield", "recession"],
    "etf": ["etf", "exchange-traded fund", "etf inflow", "etf outflow", "spot etf"],
    "stablecoin": ["stablecoin", "usdt", "usdc", "dai", "depeg", "de-pegged", "reserve"],
    "token_unlock": ["unlock", "token unlock", "vesting", "cliff", "release of tokens"],
    "governance": ["governance", "proposal", "vote", "voting", "dao", "snapshot"],
    "outage": ["outage", "down", "offline", "halt", "halted", "maintenance", "degraded"],
    "whale": ["whale", "large holder", "accumulat", "dump", "wallet mov", "whale alert", "large transaction"],
    "funding": ["funding", "raise", "raised", "fundraising", "investment", "round", "seed", "series"],
    "derivatives": ["funding rate", "open interest", "liquidation", "long", "short", "perpetual", "futures"],
    "liquidation": ["liquidation", "liquidated", "long squeeze", "short squeeze"],
    "partnership": ["partnership", "partner", "collaboration", "integrate", "integration", "alliance"],
    "product_launch": ["launch", "goes live", "went live", "mainnet", "testnet", "released"],
}

# Severity scores by topic
TOPIC_SEVERITY: dict[str, float] = {
    "exploit": 90.0, "security": 80.0, "liquidation": 70.0,
    "regulation": 65.0, "delisting": 60.0, "outage": 55.0,
    "stablecoin": 50.0, "etf": 45.0, "whale": 40.0,
    "listing": 35.0, "macro": 30.0, "funding": 25.0,
    "partnership": 20.0, "product_launch": 20.0, "governance": 15.0,
    "token_unlock": 30.0, "derivatives": 25.0,
}


class ExtractionEngine:
    """Deterministic extraction of assets, entities, and topics from text."""

    def __init__(self):
        self._compiled_assets: dict[str, re.Pattern] = {}
        for sym, (name, pat) in ASSET_MAP.items():
            self._compiled_assets[sym] = re.compile(pat, re.IGNORECASE)

    def extract(self, title: str = "", body: str = "", source_label: str = "") -> ExtractionResult:
        text = f"{title} {body}"
        text_lower = text.lower()

        assets = self._extract_assets(text_lower)
        entities = self._extract_entities(text_lower)
        topics = self._extract_topics(text_lower)

        return ExtractionResult(assets=assets, entities=entities, topics=topics)

    def _extract_assets(self, text: str) -> list[Asset]:
        found: dict[str, Asset] = {}
        for sym, (full_name, pat) in ASSET_MAP.items():
            if re.search(pat, text, re.IGNORECASE):
                # Anti-pattern check: standalone ticker in non-ticker context
                if sym in _ANTI_TICKER and not re.search(rf"\b{sym}\b", text):
                    continue
                found[sym] = Asset(symbol=sym, full_name=full_name, confidence=0.9)
        return list(found.values())

    def _extract_entities(self, text: str) -> list[Entity]:
        found: list[Entity] = []
        seen: set[str] = set()
        for etype, pat, conf in _ENTITY_PATTERNS:
            for m in re.finditer(pat, text, re.IGNORECASE):
                name = m.group(0).strip().title()
                if name.lower() not in seen:
                    seen.add(name.lower())
                    found.append(Entity(name=name, entity_type=etype, confidence=conf))
        return found

    def _extract_topics(self, text: str) -> list[Topic]:
        found: list[Topic] = []
        for topic, keywords in _TOPIC_KEYWORDS.items():
            for kw in keywords:
                if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
                    found.append(Topic(topic=topic, confidence=0.8))
                    break
        return found
