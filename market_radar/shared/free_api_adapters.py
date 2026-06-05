"""Market Radar v117 — Free API Adapters (Shared Pipeline).

Real free-data adapters that call public APIs without requiring any API key.

Priority: multi_asset_market_sync via Binance public REST API (no auth).

All adapters:
  - Do NOT require API keys
  - Do NOT use paid APIs
  - Output clear failure reasons on error
  - Do NOT masquerade API failure as pass
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from market_radar.shared.models import (
    CardFamily,
    DataSourceType,
    NormalizedSignal,
    china_now,
    PIPELINE_VERSION,
)
from market_radar.shared.adapter_contract import SignalAdapter

CN_TZ = timezone(timedelta(hours=8))

# ── Binance public endpoints (no API key needed) ────────────────────────────

BINANCE_SPOT_TICKER_24HR = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_OPEN_INTEREST = "https://fapi.binance.com/fapi/v1/openInterest"
BINANCE_FUNDING_RATE = "https://fapi.binance.com/fapi/v1/fundingRate"
BINANCE_LONG_SHORT_RATIO = "https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio"

TARGET_SYMBOLS_SPOT = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

USER_AGENT = "MarketRadar-v117/1.0 (shared pipeline; one-shot; no-key public data)"


def _http_get_json(url: str, timeout: int = 15) -> dict | list:
    """Simple HTTP GET → JSON. Uses urllib (no external deps)."""
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8")
    return json.loads(data)


# ═══════════════════════════════════════════════════════════════════════════
# Multi-Asset Market Sync — Real Binance Public API Adapter
# ═══════════════════════════════════════════════════════════════════════════


class MultiAssetMarketSyncFreeApiAdapter(SignalAdapter):
    """Fetch BTC/ETH/SOL 24hr tickers from Binance public REST.

    No API key required. Uses Binance's public /api/v3/ticker/24hr endpoint.
    """

    def __init__(self):
        super().__init__(
            card_family=CardFamily.MULTI_ASSET_MARKET_SYNC,
            source_type=DataSourceType.FREE_PUBLIC_API,
        )

    def fetch(self) -> NormalizedSignal:
        """Fetch 24hr tickers and produce a NormalizedSignal."""
        risk_notes: list[str] = []
        source_refs: list[str] = []
        assets: list[dict] = []
        api_success = False
        fetch_error: Optional[str] = None

        # Attempt to fetch from Binance public API
        try:
            tickers_raw = _http_get_json(BINANCE_SPOT_TICKER_24HR, timeout=15)
            source_refs.append("binance_public_api:/api/v3/ticker/24hr")
            api_success = True

            # Index by symbol for fast lookup
            ticker_map: dict[str, dict] = {}
            for t in tickers_raw:
                if isinstance(t, dict):
                    sym = t.get("symbol", "")
                    ticker_map[sym] = t

            for sym in TARGET_SYMBOLS_SPOT:
                t = ticker_map.get(sym)
                if t:
                    assets.append({
                        "symbol": sym,
                        "price": float(t.get("lastPrice", 0)),
                        "price_change_pct": float(t.get("priceChangePercent", 0)),
                        "volume_24h": float(t.get("quoteVolume", 0)),
                        "high_24h": float(t.get("highPrice", 0)),
                        "low_24h": float(t.get("lowPrice", 0)),
                        "trades_count": int(t.get("count", 0)),
                    })
                else:
                    risk_notes.append(f"Symbol {sym} not found in Binance ticker response")

            if not assets:
                fetch_error = "No target asset data found in Binance response"
                risk_notes.append(fetch_error)

        except (URLError, HTTPError, OSError, ValueError) as e:
            fetch_error = f"Binance API call failed: {type(e).__name__}: {e}"
            risk_notes.append(fetch_error)
        except Exception as e:
            fetch_error = f"Unexpected error during Binance fetch: {type(e).__name__}: {e}"
            risk_notes.append(fetch_error)

        # Build correlation/sync observation if we have data
        sync_observation = ""
        correlation_score = 0.0
        if len(assets) >= 2:
            changes = [a["price_change_pct"] for a in assets]
            # Simple heuristic: same-sign changes → positive sync
            signs = [1 if c > 0 else -1 if c < 0 else 0 for c in changes]
            if all(s == signs[0] for s in signs) and signs[0] != 0:
                correlation_score = 0.8
                direction = "bullish" if signs[0] > 0 else "bearish"
                sync_observation = f"All monitored assets showing {direction} alignment (corr≈{correlation_score:.2f})"
            else:
                correlation_score = 0.3
                # Check for rotation pattern
                btc_change = changes[0] if len(changes) > 0 else 0
                alt_changes = changes[1:] if len(changes) > 1 else []
                if btc_change < 0 and any(c > 0 for c in alt_changes):
                    sync_observation = "BTC weakness + alt strength — possible risk-on rotation"
                elif btc_change > 0 and all(c < 0 for c in alt_changes):
                    sync_observation = "BTC strength + alt weakness — possible risk-off rotation"
                else:
                    sync_observation = f"Mixed signals across monitored assets (corr≈{correlation_score:.2f})"

        return NormalizedSignal(
            source_type=self.source_type,
            card_family=self.card_family,
            asset_or_topic="/".join(TARGET_SYMBOLS_SPOT),
            timestamp=china_now(),
            metrics={
                "assets": assets,
                "asset_count": len(assets),
                "correlation_score": correlation_score,
                "sync_observation": sync_observation,
                "api_success": api_success,
                "fetch_error": fetch_error,
            },
            source_refs=source_refs,
            risk_notes=risk_notes,
            pipeline_version=PIPELINE_VERSION,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Price/OI/Volume Anomaly — Binance Public + OI API (no key)
# ═══════════════════════════════════════════════════════════════════════════


class PriceOIVolumeAnomalyFreeApiAdapter(SignalAdapter):
    """Fetch price + OI data from Binance public endpoints.

    Combines spot 24hr ticker (price/volume) with futures open interest.
    No API key required.
    """

    def __init__(self):
        super().__init__(
            card_family=CardFamily.PRICE_OI_VOLUME_ANOMALY,
            source_type=DataSourceType.FREE_PUBLIC_API,
        )

    def fetch(self) -> NormalizedSignal:
        """Fetch BTC/ETH/SOL price data + OI and detect anomalies."""
        risk_notes: list[str] = []
        source_refs: list[str] = []
        signals: list[dict] = []
        api_success = False
        fetch_error: Optional[str] = None

        try:
            tickers_raw = _http_get_json(BINANCE_SPOT_TICKER_24HR, timeout=15)
            source_refs.append("binance_public_api:/api/v3/ticker/24hr")
            api_success = True

            ticker_map: dict[str, dict] = {}
            for t in tickers_raw:
                if isinstance(t, dict):
                    ticker_map[t.get("symbol", "")] = t

            for sym in TARGET_SYMBOLS_SPOT:
                t = ticker_map.get(sym)
                if not t:
                    risk_notes.append(f"Symbol {sym} not found in Binance tickers")
                    continue

                price_change = float(t.get("priceChangePercent", 0))
                volume = float(t.get("quoteVolume", 0))
                price = float(t.get("lastPrice", 0))

                # Try to get OI for the perpetual futures pair
                oi_current: Optional[float] = None
                oi_error: Optional[str] = None
                try:
                    oi_url = f"{BINANCE_OPEN_INTEREST}?symbol={sym}"
                    oi_resp = _http_get_json(oi_url, timeout=10)
                    oi_current = float(oi_resp.get("openInterest", 0))
                    source_refs.append(f"binance_public_api:openInterest({sym})")
                except Exception as e:
                    oi_error = f"OI unavailable: {type(e).__name__}"

                # Determine anomaly
                is_price_up = price_change > 0
                is_large_move = abs(price_change) > 5.0
                is_extreme_move = abs(price_change) > 10.0

                confirm_factors = []
                if abs(price_change) > 3.0:
                    confirm_factors.append("price_move_significant")
                if volume > 5_000_000_000:
                    confirm_factors.append("volume_spike")
                if oi_current and oi_current > 1_000_000_000:
                    confirm_factors.append("oi_elevated")

                anomaly_type = "normal"
                if is_extreme_move and len(confirm_factors) >= 2:
                    anomaly_type = "extreme"
                elif is_large_move and len(confirm_factors) >= 1:
                    anomaly_type = "notable"

                admission_passed = anomaly_type in ("extreme", "notable") and len(confirm_factors) >= 1

                signals.append({
                    "symbol": sym,
                    "price": price,
                    "price_change_24h_pct": price_change,
                    "quote_volume_24h": volume,
                    "open_interest_current": oi_current,
                    "oi_history_missing": oi_error is not None,
                    "oi_error": oi_error,
                    "anomaly_type": anomaly_type,
                    "confirmation_factors": confirm_factors,
                    "admission_passed": admission_passed,
                })

            if not signals:
                fetch_error = "No asset signals could be generated"

        except (URLError, HTTPError, OSError, ValueError) as e:
            fetch_error = f"Binance API call failed: {type(e).__name__}: {e}"
            risk_notes.append(fetch_error)
        except Exception as e:
            fetch_error = f"Unexpected error: {type(e).__name__}: {e}"
            risk_notes.append(fetch_error)

        # Pick the primary asset (first with strongest signal)
        primary_asset = signals[0]["symbol"] if signals else "BTCUSDT"
        primary_signal = signals[0] if signals else {}

        return NormalizedSignal(
            source_type=self.source_type,
            card_family=self.card_family,
            asset_or_topic=primary_asset,
            timestamp=china_now(),
            metrics={
                "primary_asset": primary_asset,
                "signals": signals,
                "signal_count": len(signals),
                "api_success": api_success,
                "fetch_error": fetch_error,
            },
            source_refs=source_refs,
            risk_notes=risk_notes,
            pipeline_version=PIPELINE_VERSION,
        )


# ═══════════════════════════════════════════════════════════════════════════
# News Event Market Impact — Real Free Public Source Adapter
# ═══════════════════════════════════════════════════════════════════════════

# Free public RSS/news sources (NO API key needed)
NEWS_RSS_SOURCES = [
    {
        "source_name": "CoinDesk",
        "source_type": "rss",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "timeout": 15,
    },
    {
        "source_name": "Cointelegraph",
        "source_type": "rss",
        "url": "https://cointelegraph.com/rss",
        "timeout": 15,
    },
    {
        "source_name": "Decrypt",
        "source_type": "rss",
        "url": "https://decrypt.co/feed",
        "timeout": 15,
    },
    {
        "source_name": "The Block",
        "source_type": "rss",
        "url": "https://www.theblock.co/rss",
        "timeout": 15,
    },
    {
        "source_name": "Binance Announcements",
        "source_type": "json_api",
        "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=10",
        "timeout": 15,
    },
]

# Rule-based event type keyword maps (NO AI/model — deterministic keyword matching)
EVENT_TYPE_KEYWORDS: dict[str, list[str]] = {
    "ETF": ["etf", "exchange-traded fund", "bitcoin etf", "eth etf", "spot etf",
            "etf inflow", "etf outflow", "etf approval", "etf filing"],
    "regulatory": ["regulation", "regulatory", "sec", "cftc", "esma", "compliant",
                   "compliance", "kyc", "aml", "license", "licensed", "registered"],
    "lawsuit": ["lawsuit", "sue", "sued", "court", "judge", "ruling", "settlement",
                "legal action", "prosecut", "indictment", "criminal", "fine"],
    "approval": ["approval", "approved", "green light", "authorized", "granted"],
    "hack": ["hack", "hacked", "exploit", "exploited", "breach", "compromised",
             "attack", "drain", "stolen"],
    "exploit": ["exploit", "vulnerability", "bug", "patch", "audit", "security flaw"],
    "listing": ["listing", "listed", "list", "launch", "new trading pair",
                "will list", "to list", "listing on"],
    "delisting": ["delist", "delisting", "remove", "removal", "suspended trading"],
    "unlock": ["unlock", "token unlock", "vesting", "cliff", "release of tokens"],
    "partnership": ["partnership", "partner", "collaboration", "integrate",
                    "integration", "alliance", "join forces"],
    "outage": ["outage", "down", "offline", "halt", "halted", "suspend",
               "suspended", "maintenance", "degraded"],
    "macro": ["fed", "federal reserve", "rate cut", "rate hike", "inflation",
              "cpi", "ppi", "gdp", "unemployment", "dxy", "dollar index",
              "central bank", "ecb", "boj", "pbo", "monetary policy",
              "treasury", "bond", "yield", "recession", "stimulus"],
    "whale": ["whale", "large holder", "accumulat", "dump", "transfer",
              "wallet mov", "whale alert", "large transaction"],
    "funding": ["funding", "raise", "raised", "fundraising", "investment",
                "round", "seed", "series", "vc", "venture", "backing", "invested"],
    "airdrop": ["airdrop", "claim", "distribution", "giveaway", "free token"],
    "mainnet": ["mainnet", "launch", "goes live", "went live", "live on mainnet"],
    "upgrade": ["upgrade", "fork", "hard fork", "soft fork", "eip", "bip", "sip",
                "proposal", "improvement proposal", "testnet"],
}

HIGH_INTENSITY_KEYWORDS = [
    "crash", "crashes", "plunge", "plunges", "plummet", "plummets",
    "surge", "surges", "soar", "soars", "skyrocket", "rallies hard",
    "halt", "halts", "suspend", "suspends", "freeze", "freezes",
    "drain", "drains", "exploit", "exploits", "hack", "hacked",
    "stolen", "breach", "bankruptcy", "collapse", "collapses",
    "emergency", "critical", "severe", "ban", "bans", "banning",
    "lawsuit", "sued", "indictment", "arrested", "raid",
    "billion", "billions", "record high", "record low",
    "delist", "delisting", "liquidated", "liquidation cascade",
    "approve etf", "etf approved", "etf rejected",
    "rate cut 50", "rate hike 50", "emergency meeting",
]

MEDIUM_INTENSITY_KEYWORDS = [
    "rise", "rises", "fall", "falls", "drop", "drops",
    "gain", "gains", "lose", "loses", "decline", "declines",
    "jump", "jumps", "rebound", "rebounds", "rally", "rallies",
    "warn", "warns", "warning", "cautious", "concern",
    "propose", "proposes", "proposed", "bill", "legislation",
    "file", "files", "filing", "lawsuit", "investigation",
    "list", "lists", "listing", "will list",
    "million", "millions", "funding", "raised",
    "partnership", "integrate", "integration",
    "upgrade", "hard fork", "soft fork",
    "unlock", "vesting", "supply increase",
    "volatility", "volatile", "uncertainty",
    "cpi", "ppi", "fed chair", "powell",
]

# Asset tickers to detect in news titles
CANONICAL_TICKERS = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "LINK", "ARB", "OP",
    "AVAX", "SUI", "MATIC", "DOT", "ATOM", "UNI", "AAVE", "MKR", "LDO",
    "TRX", "TON", "NEAR", "INJ", "SEI", "RUNE", "APT", "PEPE", "SHIB",
    "WIF", "BONK", "HYPE",
}

ASSET_NAME_MAP = {
    "BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL",
    "ARBITRUM": "ARB", "OPTIMISM": "OP", "AVALANCHE": "AVAX",
    "CHAINLINK": "LINK", "DOGECOIN": "DOGE", "RIPPLE": "XRP",
    "POLKADOT": "DOT", "COSMOS": "ATOM", "UNISWAP": "UNI",
    "APTOS": "APT", "NEAR PROTOCOL": "NEAR", "INJECTIVE": "INJ",
    "THORCHAIN": "RUNE", "HYPERLIQUID": "HYPE",
}


def _classify_event_intensity(title: str) -> str:
    """Rule-based intensity classification (NO AI/model)."""
    text = title.lower()
    for kw in HIGH_INTENSITY_KEYWORDS:
        if kw.lower() in text:
            return "high"
    for kw in MEDIUM_INTENSITY_KEYWORDS:
        if kw.lower() in text:
            return "medium"
    return "low"


def _classify_event_type(title: str) -> str:
    """Rule-based event type classification (NO AI/model)."""
    text = title.lower()
    scores = {}
    for etype, keywords in EVENT_TYPE_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw.lower() in text)
        if count > 0:
            scores[etype] = count
    if not scores:
        return "other"
    return max(scores, key=scores.get)


def _extract_assets_from_title(title: str) -> list[str]:
    """Extract crypto asset tickers from news title using regex (NO AI/model)."""
    text = title.upper()
    found = set()
    for ticker in sorted(CANONICAL_TICKERS, key=len, reverse=True):
        pattern = r'(?<![A-Z0-9])' + re.escape(ticker) + r'(?![A-Z0-9])'
        if re.search(pattern, text):
            found.add(ticker)
    for full_name, ticker in ASSET_NAME_MAP.items():
        if re.search(r'\b' + re.escape(full_name) + r'\b', text):
            found.add(ticker)
    return sorted(found)


class NewsEventMarketImpactFreePublicSourceAdapter(SignalAdapter):
    """Fetch news from free public RSS/API sources + Binance market data.

    Combines real public news titles/URLs from CoinDesk, Cointelegraph,
    Decrypt, The Block, and Binance Announcements with Binance market
    data for identified crypto assets.

    NO API key required. NO AI/model used. Rule-based extraction only.

    Output card family: news_event_market_impact
    observation_only = True
    not_causal_proof = True

    v117F: fetch() caches its result to prevent duplicate market API calls.
    The first call triggers real external fetches; subsequent calls within
    the same adapter instance return the cached result. Diagnostics MUST
    be extracted from the returned NormalizedSignal.metrics — never by
    calling fetch() again.
    """

    def __init__(self):
        super().__init__(
            card_family=CardFamily.NEWS_EVENT_MARKET_IMPACT,
            source_type=DataSourceType.FREE_PUBLIC_SOURCE,
        )
        # v117F: Fetch-once guard — prevent duplicate market/API calls
        self._fetch_count: int = 0
        self._cached_signal: Optional[NormalizedSignal] = None
        self._last_fetch_ts: Optional[str] = None

    def _fetch_rss(self, url: str, source_name: str, timeout: int = 15) -> list[dict]:
        """Fetch and parse an RSS feed. Returns list of article dicts."""
        import xml.etree.ElementTree as ET

        articles = []
        try:
            req = Request(url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            })
            with urlopen(req, timeout=timeout) as resp:
                content = resp.read().decode("utf-8", errors="replace")

            try:
                parser = ET.XMLParser(resolve_entities=False)
                root = ET.fromstring(content, parser=parser)
            except TypeError:
                root = ET.fromstring(content)

            items = root.findall(".//item") or root.findall(
                ".//{http://www.w3.org/2005/Atom}entry"
            )

            for item in items[:30]:
                # v117F: Explicit is not None to avoid XML element truth value
                # DeprecationWarning in Python 3.12+
                title_el = item.find("title")
                if title_el is None:
                    title_el = item.find("{http://www.w3.org/2005/Atom}title")
                link_el = item.find("link")
                if link_el is None:
                    link_el = item.find("{http://www.w3.org/2005/Atom}link")
                title = (title_el.text or "").strip() if title_el is not None else ""
                if not title:
                    continue
                url_str = ""
                if link_el is not None:
                    url_str = link_el.text or link_el.get("href", "")
                    url_str = (url_str or "").strip()

                articles.append({
                    "source_name": source_name,
                    "source_domain": source_name.lower().replace(" ", "") + ".com",
                    "title": title,
                    "url": url_str,
                    "extraction_method": "rule_based_rss_parse",
                })
            return articles
        except Exception:
            return articles

    def _fetch_binance_announcements(self, timeout: int = 15) -> list[dict]:
        """Fetch Binance announcement titles via public API (no key)."""
        articles = []
        try:
            url = (
                "https://www.binance.com/bapi/composite/v1/public/cms/"
                "article/list/query?type=1&pageNo=1&pageSize=10"
            )
            data = _http_get_json(url, timeout=timeout)
            catalog = data.get("data", {}).get("catalogs", [])
            for cat in catalog:
                for art in cat.get("articles", [])[:30]:
                    title = art.get("title", "").strip()
                    if not title:
                        continue
                    art_id = art.get("id", "")
                    url_str = (
                        f"https://www.binance.com/en/support/announcement/{art_id}"
                        if art_id else ""
                    )
                    articles.append({
                        "source_name": "Binance Announcements",
                        "source_domain": "binance.com",
                        "title": title,
                        "url": url_str,
                        "extraction_method": "rule_based_json_api",
                    })
            return articles
        except Exception:
            return articles

    def _fetch_all_news(self) -> tuple[list[dict], dict]:
        """Fetch news from all configured free public sources.

        Returns (articles_list, sources_status_dict).
        """
        all_articles = []
        sources_status = {"attempted": 0, "succeeded": 0, "sources": []}

        for src in NEWS_RSS_SOURCES:
            sources_status["attempted"] += 1
            source_name = src["source_name"]
            url = src["url"]
            timeout = src["timeout"]
            source_type = src["source_type"]

            try:
                if source_type == "rss":
                    articles = self._fetch_rss(url, source_name, timeout)
                elif source_type == "json_api":
                    articles = self._fetch_binance_announcements(timeout)
                else:
                    articles = []

                if articles:
                    sources_status["succeeded"] += 1
                    sources_status["sources"].append({
                        "source_name": source_name,
                        "source_domain": source_name.lower().replace(" ", "") + ".com",
                        "status": "ok",
                        "article_count": len(articles),
                    })
                    all_articles.extend(articles)
                else:
                    sources_status["sources"].append({
                        "source_name": source_name,
                        "status": "empty",
                        "article_count": 0,
                    })
            except Exception as e:
                sources_status["sources"].append({
                    "source_name": source_name,
                    "status": "error",
                    "error": f"{type(e).__name__}: {e}",
                    "article_count": 0,
                })

        return all_articles, sources_status

    def fetch(self) -> NormalizedSignal:
        """Fetch real news from public sources, extract events, combine with
        Binance market data, and return a NormalizedSignal for the shared pipeline.

        NEVER raises — errors become risk_notes.

        v117F: First call performs real external fetches. Subsequent calls return
        the cached signal to prevent duplicate Binance API calls. Diagnostics
        MUST be extracted from the returned NormalizedSignal.metrics, NOT by
        calling fetch() again for reporting.
        """
        # v117F: Fetch-once guard — return cached signal on subsequent calls
        if self._fetch_count > 0 and self._cached_signal is not None:
            return self._cached_signal

        self._fetch_count += 1
        risk_notes = []
        source_refs = []
        fetch_time = china_now()

        # ── 1. Fetch news from public sources ──
        all_articles, sources_status = self._fetch_all_news()
        sources_succeeded = sources_status["succeeded"]
        all_sources_unavailable = sources_succeeded == 0

        if all_sources_unavailable:
            risk_notes.append("blocked_no_relevant_news_event: all public news sources unavailable")
            signal = NormalizedSignal(
                source_type=self.source_type,
                card_family=self.card_family,
                asset_or_topic="news_event_market_impact",
                timestamp=fetch_time,
                metrics={
                    "source_name": "multiple_free_public_sources",
                    "title": "",
                    "url": "",
                    "event_type": "none",
                    "intensity": "low",
                    "attribution_risk": "unsafe",
                    "extraction_method": "rule_based_no_events",
                    "assets_affected": [],
                    "market_snapshot": {},
                    "observation_only": True,
                    "not_causal_proof": True,
                    "all_public_sources_unavailable": True,
                    "sources_attempted": sources_status["attempted"],
                    "sources_succeeded": 0,
                    "articles_fetched": 0,
                    "event_extracted": False,
                    "market_api_success": False,
                    "market_fetch_attempted": False,
                    "fetch_count": self._fetch_count,
                },
                source_refs=["free_public_source:none_available"],
                risk_notes=risk_notes,
                pipeline_version=PIPELINE_VERSION,
            )
            self._cached_signal = signal
            self._last_fetch_ts = fetch_time
            return signal

        source_refs.append(f"free_public_source:{sources_succeeded}_sources_{len(all_articles)}_articles")

        # ── 2. Extract events from article titles (rule-based, NO AI) ──
        events_extracted = []
        for article in all_articles:
            title = article.get("title", "")
            if not title:
                continue
            assets = _extract_assets_from_title(title)
            if not assets:
                continue
            event_type = _classify_event_type(title)
            intensity = _classify_event_intensity(title)
            attribution = "direct" if assets else "unsafe"
            if attribution == "unsafe":
                continue

            events_extracted.append({
                "title": title,
                "url": article.get("url", ""),
                "source_name": article.get("source_name", ""),
                "source_domain": article.get("source_domain", ""),
                "assets_affected": assets,
                "event_type": event_type,
                "intensity": intensity,
                "attribution_risk": attribution,
                "extraction_method": "rule_based_keyword_matching",
            })

        has_events = len(events_extracted) > 0

        if not has_events:
            risk_notes.append("blocked_no_relevant_news_event: no events extracted from available articles")
            signal = NormalizedSignal(
                source_type=self.source_type,
                card_family=self.card_family,
                asset_or_topic="news_event_market_impact",
                timestamp=fetch_time,
                metrics={
                    "source_name": "multiple_free_public_sources",
                    "title": "",
                    "url": "",
                    "event_type": "none",
                    "intensity": "low",
                    "attribution_risk": "unsafe",
                    "extraction_method": "rule_based_no_events",
                    "assets_affected": [],
                    "market_snapshot": {},
                    "observation_only": True,
                    "not_causal_proof": True,
                    "all_public_sources_unavailable": False,
                    "sources_attempted": sources_status["attempted"],
                    "sources_succeeded": sources_succeeded,
                    "articles_fetched": len(all_articles),
                    "event_extracted": False,
                    "events_found": 0,
                    "market_api_success": False,
                    "market_fetch_attempted": False,
                    "fetch_count": self._fetch_count,
                },
                source_refs=source_refs + [
                    f"free_public_source:{s.get('source_name')}"
                    for s in sources_status.get("sources", [])
                    if s.get("status") == "ok"
                ],
                risk_notes=risk_notes,
                pipeline_version=PIPELINE_VERSION,
            )
            self._cached_signal = signal
            self._last_fetch_ts = fetch_time
            return signal

        # ── 3. Fetch market data for affected assets (Binance free API) ──
        all_assets = set()
        for ev in events_extracted:
            for a in ev["assets_affected"]:
                all_assets.add(a)

        # Map to Binance symbols
        asset_symbol_map = {a: f"{a}USDT" for a in all_assets if f"{a}USDT" in TARGET_SYMBOLS_SPOT
                          or f"{a}USDT" in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                                            "DOGEUSDT", "LINKUSDT", "ARBUSDT", "OPUSDT", "AVAXUSDT",
                                            "SUIUSDT", "DOTUSDT", "ATOMUSDT", "UNIUSDT", "AAVEUSDT",
                                            "TRXUSDT", "TONUSDT", "NEARUSDT", "INJUSDT", "APTUSDT"]}
        # Ensure at least BTC/ETH/SOL if no assets mapped
        if not asset_symbol_map:
            asset_symbol_map = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}

        market_snapshot = {}
        market_api_success = False
        try:
            tickers_raw = _http_get_json(BINANCE_SPOT_TICKER_24HR, timeout=15)
            source_refs.append("binance_public_api:/api/v3/ticker/24hr")
            market_api_success = True

            ticker_map = {}
            for t in tickers_raw:
                if isinstance(t, dict):
                    ticker_map[t.get("symbol", "")] = t

            for asset, symbol in asset_symbol_map.items():
                t = ticker_map.get(symbol)
                if t:
                    market_snapshot[asset] = {
                        "symbol": symbol,
                        "price": float(t.get("lastPrice", 0)),
                        "price_change_pct": float(t.get("priceChangePercent", 0)),
                        "volume_24h": float(t.get("quoteVolume", 0)),
                        "data_source": "binance_public_rest",
                    }
        except Exception as e:
            risk_notes.append(f"Binance market data fetch failed: {type(e).__name__}: {e}")

        # ── 4. Select primary event (highest intensity + most assets) ──
        intensity_rank = {"high": 3, "medium": 2, "low": 1}
        ranked = sorted(
            events_extracted,
            key=lambda e: (
                intensity_rank.get(e["intensity"], 0),
                len(e.get("assets_affected", [])),
            ),
            reverse=True,
        )
        primary = ranked[0]

        # ── 5. Build NormalizedSignal ──
        event_title = primary["title"]
        event_url = primary["url"]
        source_name = primary["source_name"]
        source_domain = primary["source_domain"]
        event_type = primary["event_type"]
        intensity = primary["intensity"]
        attr_risk = primary["attribution_risk"]
        assets_affected = primary["assets_affected"]

        # Clean title for safety (no investment advice terms)
        # Already rule-based extraction — no AI model involved
        risk_notes.append("event_extraction: rule_based_keyword_matching — NO AI/model")
        risk_notes.append("not_causal_proof: event observed alongside market data, not causal")
        risk_notes.append(f"sources: {sources_succeeded}/{sources_status['attempted']} succeeded, "
                         f"{len(all_articles)} articles, {len(events_extracted)} events extracted")
        risk_notes.append(f"observation_only=true: do NOT interpret as causal prediction")

        if attr_risk == "indirect":
            risk_notes.append("attribution_risk=indirect: event may affect markets broadly, "
                            "cannot attribute specific asset moves")

        signal = NormalizedSignal(
            source_type=self.source_type,
            card_family=self.card_family,
            asset_or_topic=", ".join(assets_affected[:5]),
            timestamp=fetch_time,
            metrics={
                "source_name": source_name,
                "source_domain": source_domain,
                "title": event_title,
                "url": event_url,
                "event_type": event_type,
                "intensity": intensity,
                "attribution_risk": attr_risk,
                "extraction_method": "rule_based_keyword_matching",
                "assets_affected": assets_affected,
                "market_snapshot": market_snapshot,
                "observation_only": True,
                "not_causal_proof": True,
                "all_public_sources_unavailable": False,
                "sources_attempted": sources_status["attempted"],
                "sources_succeeded": sources_succeeded,
                "articles_fetched": len(all_articles),
                "events_found": len(events_extracted),
                "event_extracted": True,
                "primary_event_ranked": True,
                "market_api_success": market_api_success,
                "market_fetch_attempted": True,
                "fetch_count": self._fetch_count,
                "sources_detail": [
                    s for s in sources_status.get("sources", []) if s.get("status") == "ok"
                ],
            },
            source_refs=source_refs + [
                f"free_public_source:{s.get('source_name')}"
                for s in sources_status.get("sources", [])
                if s.get("status") == "ok"
            ],
            risk_notes=risk_notes,
            pipeline_version=PIPELINE_VERSION,
        )
        # v117F: Cache result to prevent duplicate API calls
        self._cached_signal = signal
        self._last_fetch_ts = fetch_time
        return signal


# ═══════════════════════════════════════════════════════════════════════════
# Adapter Registry
# ═══════════════════════════════════════════════════════════════════════════

REAL_FREE_API_ADAPTERS: dict[str, type[SignalAdapter]] = {
    CardFamily.MULTI_ASSET_MARKET_SYNC.value: MultiAssetMarketSyncFreeApiAdapter,
    CardFamily.PRICE_OI_VOLUME_ANOMALY.value: PriceOIVolumeAnomalyFreeApiAdapter,
    CardFamily.NEWS_EVENT_MARKET_IMPACT.value: NewsEventMarketImpactFreePublicSourceAdapter,
}


def create_real_free_api_adapter(card_family: str | CardFamily) -> Optional[SignalAdapter]:
    """Factory: create a real free API adapter for the given card family.

    Returns None if no real adapter is implemented for this family.
    """
    if isinstance(card_family, CardFamily):
        card_family = card_family.value
    adapter_cls = REAL_FREE_API_ADAPTERS.get(card_family)
    if adapter_cls is None:
        return None
    return adapter_cls()
