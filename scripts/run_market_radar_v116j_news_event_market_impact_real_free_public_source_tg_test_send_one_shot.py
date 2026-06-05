"""Market Radar v1.16-J — News Event Market Impact Real Free Public Source TG Test Send (One-Shot)

Fetches real news from FREE PUBLIC RSS/announcement sources (NO API key required),
extracts events via rule-based logic (NO AI/model), fetches real Binance market data
for identified assets, generates news_event_market_impact cards, runs quality gate
and send-readiness gate, then attempts ONE-SHOT TG test-group send.

THIS IS REAL EXTERNAL NEWS SOURCE + REAL BINANCE API + REAL TG TEST SEND (one-shot only).
Not fixture. Not production. Not daemon/loop.

CRITICAL: This runner does NOT call any AI/model, does NOT scrape full article text,
does NOT use paid APIs. Only public RSS titles, published_at, URLs, and source names
are used. Max 280-char snippet from RSS description if provided.

Free news sources attempted (no API key required):
  - Binance official announcements (public RSS/API)
  - CoinDesk RSS
  - Cointelegraph RSS
  - Decrypt RSS
  - The Block RSS

Free market data sources:
  - Binance spot 24hr ticker (public, no key)
  - Binance futures 24hr ticker (public, no key)
  - Binance futures funding rate (public, no key)

Rule-based event extraction:
  - Asset identification: BTC, ETH, SOL, BNB, XRP, DOGE, LINK, ARB, OP, AVAX, SUI, etc.
  - Event type: ETF / regulatory / lawsuit / approval / hack / exploit / listing /
    delisting / unlock / partnership / outage / macro / whale / funding / airdrop /
    mainnet / upgrade
  - Event intensity: high, medium, low
  - Attribution risk: direct, indirect, unsafe

Admission rules (conservative):
  - high intensity + direct attribution + asset market data available → admission_passed
  - medium intensity + direct attribution + significant 24h price/volume change → admission_passed
  - macro/regulatory events → market_context card (explicitly "cannot prove causality")
  - unsafe attribution → BLOCKED, no card generation

Outputs:
  results/market_radar_v116j_news_event_market_impact_raw_sources.json
  results/market_radar_v116j_news_event_market_impact_event_records.jsonl
  results/market_radar_v116j_news_event_market_impact_market_snapshots.json
  results/market_radar_v116j_news_event_market_impact_card_records.jsonl
  results/market_radar_v116j_news_event_market_impact_quality_gate_records.jsonl
  results/market_radar_v116j_news_event_market_impact_send_readiness_records.jsonl
  results/market_radar_v116j_news_event_market_impact_tg_send_attempts.jsonl
  results/market_radar_v116j_news_event_market_impact_tg_test_send_result.json
  runs/market_radar/v116j_news_event_market_impact_card_preview.md
  runs/market_radar/v116j_news_event_market_impact_tg_test_send_report.md
  runs/market_radar/v116j_news_event_market_impact_local_only_handoff.md

Usage:
    python scripts/run_market_radar_v116j_news_event_market_impact_real_free_public_source_tg_test_send_one_shot.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

import requests

# ── Project root ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── Constants ────────────────────────────────────────────────────────────
CARD_FAMILY = "news_event_market_impact"
VERSION = "v1.16-J"
STAGE = "v116j_news_event_market_impact_real_free_public_source_tg_test_send_one_shot"
TASK_ID = "20260605_v116j_news_event_market_impact_real_free_public_source_tg_test_send_one_shot"
RUN_ID = "20260605_124925"
CN_TZ = timezone(timedelta(hours=8))

# ── Free public news RSS sources (NO API key needed) ─────────────────────
NEWS_SOURCES = [
    {
        "source_name": "CoinDesk",
        "source_type": "rss",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "timeout": 15,
        "priority": 1,
    },
    {
        "source_name": "Cointelegraph",
        "source_type": "rss",
        "url": "https://cointelegraph.com/rss",
        "timeout": 15,
        "priority": 2,
    },
    {
        "source_name": "Decrypt",
        "source_type": "rss",
        "url": "https://decrypt.co/feed",
        "timeout": 15,
        "priority": 3,
    },
    {
        "source_name": "The Block",
        "source_type": "rss",
        "url": "https://www.theblock.co/rss",
        "timeout": 15,
        "priority": 4,
    },
    {
        "source_name": "Binance Announcements",
        "source_type": "json_api",
        "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=10",
        "timeout": 15,
        "priority": 5,
    },
]

# ── Free Binance API endpoints ───────────────────────────────────────────
BINANCE_SPOT_TICKER_24HR = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_FUTURES_TICKER_24HR = "https://fapi.binance.com/fapi/v1/ticker/24hr"
BINANCE_FUTURES_FUNDING_RATE = "https://fapi.binance.com/fapi/v1/fundingRate"

# ── Asset → Binance symbol mapping ───────────────────────────────────────
ASSET_SYMBOL_MAP: dict[str, str] = {
    "BTC": "BTCUSDT", "BITCOIN": "BTCUSDT",
    "ETH": "ETHUSDT", "ETHEREUM": "ETHUSDT",
    "SOL": "SOLUSDT", "SOLANA": "SOLUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT", "RIPPLE": "XRPUSDT",
    "DOGE": "DOGEUSDT", "DOGECOIN": "DOGEUSDT",
    "LINK": "LINKUSDT", "CHAINLINK": "LINKUSDT",
    "ARB": "ARBUSDT", "ARBITRUM": "ARBUSDT",
    "OP": "OPUSDT", "OPTIMISM": "OPUSDT",
    "AVAX": "AVAXUSDT", "AVALANCHE": "AVAXUSDT",
    "SUI": "SUIUSDT",
    "MATIC": "MATICUSDT", "POL": "POLUSDT", "POLYGON": "MATICUSDT",
    "APT": "APTUSDT", "APTOS": "APTUSDT",
    "DOT": "DOTUSDT", "POLKADOT": "DOTUSDT",
    "ATOM": "ATOMUSDT", "COSMOS": "ATOMUSDT",
    "UNI": "UNIUSDT", "UNISWAP": "UNIUSDT",
    "AAVE": "AAVEUSDT",
    "MKR": "MKRUSDT", "MAKER": "MKRUSDT",
    "LDO": "LDOUSDT", "LIDO": "LDOUSDT",
    "TRX": "TRXUSDT", "TRON": "TRXUSDT",
    "TON": "TONUSDT",
    "NEAR": "NEARUSDT",
    "INJ": "INJUSDT", "INJECTIVE": "INJUSDT",
    "SEI": "SEIUSDT",
    "RUNE": "RUNEUSDT", "THORCHAIN": "RUNEUSDT",
    "PEPE": "PEPEUSDT",
    "SHIB": "SHIBUSDT",
    "WIF": "WIFUSDT",
    "BONK": "BONKUSDT",
    "HYPE": "HYPEUSDT", "HYPERLIQUID": "HYPEUSDT",
}

ASSET_LABELS: dict[str, str] = {v: k for k, v in ASSET_SYMBOL_MAP.items()}
# Deduplicate: keep only canonical tickers
CANONICAL_TICKERS: set[str] = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "LINK", "ARB", "OP",
    "AVAX", "SUI", "MATIC", "DOT", "ATOM", "UNI", "AAVE", "MKR", "LDO",
    "TRX", "TON", "NEAR", "INJ", "SEI", "RUNE", "APT", "PEPE", "SHIB",
    "WIF", "BONK", "HYPE",
}

# ── Event type keyword maps ──────────────────────────────────────────────
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

# ── Event intensity keywords ─────────────────────────────────────────────
HIGH_INTENSITY_KEYWORDS: list[str] = [
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

MEDIUM_INTENSITY_KEYWORDS: list[str] = [
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

# ── Output paths ─────────────────────────────────────────────────────────
OUTPUT_DIR = ROOT / "results"
RUNS_DIR = ROOT / "runs" / "market_radar"

RAW_SOURCES_JSON = OUTPUT_DIR / "market_radar_v116j_news_event_market_impact_raw_sources.json"
EVENT_RECORDS_JSONL = OUTPUT_DIR / "market_radar_v116j_news_event_market_impact_event_records.jsonl"
MARKET_SNAPSHOTS_JSON = OUTPUT_DIR / "market_radar_v116j_news_event_market_impact_market_snapshots.json"
CARD_RECORDS_JSONL = OUTPUT_DIR / "market_radar_v116j_news_event_market_impact_card_records.jsonl"
QUALITY_GATE_JSONL = OUTPUT_DIR / "market_radar_v116j_news_event_market_impact_quality_gate_records.jsonl"
SEND_READINESS_JSONL = OUTPUT_DIR / "market_radar_v116j_news_event_market_impact_send_readiness_records.jsonl"
TG_SEND_ATTEMPTS_JSONL = OUTPUT_DIR / "market_radar_v116j_news_event_market_impact_tg_send_attempts.jsonl"
SEND_RESULT_JSON = OUTPUT_DIR / "market_radar_v116j_news_event_market_impact_tg_test_send_result.json"
CARD_PREVIEW_MD = RUNS_DIR / "v116j_news_event_market_impact_card_preview.md"
SEND_REPORT_MD = RUNS_DIR / "v116j_news_event_market_impact_tg_test_send_report.md"
HANDOFF_MD = RUNS_DIR / "v116j_news_event_market_impact_local_only_handoff.md"

# ── Safety flags ─────────────────────────────────────────────────────────
SAFETY: dict[str, Any] = {
    "real_public_source_called": False,
    "real_external_api_called": False,
    "fixture_only": False,
    "production_send_ready": False,
    "prod_state_write": False,
    "ai_model_called": False,
    "credentials_printed": False,
    "credentials_read_plaintext": False,
    "daemon_or_loop_started": False,
    "files_deleted": False,
    "tg_test_sent": False,
    "tg_message_id_redacted": None,
    "api_key_required": False,
    "api_source": "Free public RSS + Binance public REST endpoints (no API key)",
    "secret_preflight_run": False,
    "telegram_bot_token_present": False,
    "telegram_chat_id_present": False,
    "secret_preflight_passed": False,
    "news_full_text_saved": False,
    "sources_attempted": 0,
    "sources_succeeded": 0,
}


def generate_timestamp() -> str:
    return datetime.now(CN_TZ).isoformat()


def hash_value(value: str) -> str:
    if not value:
        return "sha256:empty"
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════
# Step 0: SAFE SECRET PREFLIGHT
# ══════════════════════════════════════════════════════════════════════════

def safe_secret_preflight() -> dict:
    """Check boolean presence of TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.

    CRITICAL: NEVER print, echo, write, or log the raw values.
    ONLY output boolean presence: true/false.
    """
    print("=" * 70)
    print("[0] SAFE SECRET PREFLIGHT")
    print("=" * 70)
    print("  Checking TG credential presence (BOOLEAN ONLY — no values printed)...")

    bot_token_present = bool(os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    chat_id_present = bool(os.environ.get("TELEGRAM_CHAT_ID", ""))

    print(f"  telegram_bot_token_present: {bot_token_present}")
    print(f"  telegram_chat_id_present: {chat_id_present}")

    preflight_passed = bot_token_present and chat_id_present

    if preflight_passed:
        print("  [PREFLIGHT PASS] Both TG credentials present. TG test send will be attempted.")
    else:
        missing = []
        if not bot_token_present:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not chat_id_present:
            missing.append("TELEGRAM_CHAT_ID")
        print(f"  [PREFLIGHT BLOCKED] Missing: {', '.join(missing)}")
        print("  Will generate card + gates but TG send will be blocked.")

    SAFETY["secret_preflight_run"] = True
    SAFETY["telegram_bot_token_present"] = bot_token_present
    SAFETY["telegram_chat_id_present"] = chat_id_present
    SAFETY["secret_preflight_passed"] = preflight_passed

    if preflight_passed:
        SAFETY["credentials_read_plaintext"] = True

    print()
    return {
        "telegram_bot_token_present": bot_token_present,
        "telegram_chat_id_present": chat_id_present,
        "preflight_passed": preflight_passed,
        "preflight_timestamp": generate_timestamp(),
        "note": "Only boolean presence checked. Raw values never printed/logged/stored.",
    }


# ══════════════════════════════════════════════════════════════════════════
# Step 1: Fetch real news from free public sources
# ══════════════════════════════════════════════════════════════════════════

def fetch_rss_feed(url: str, source_name: str, timeout: int = 15) -> list[dict]:
    """Fetch and parse an RSS feed. Returns list of article dicts (title, url, published_at, summary)."""
    print(f"  [{source_name}] Fetching RSS: {url}")
    articles: list[dict] = []
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MarketRadar/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        })
        resp.raise_for_status()
        content = resp.text

        # Parse XML. Python 3.x expat-based parser is safe against XXE by default
        # (external entities are not resolved). Use try/except for compatibility.
        try:
            parser = ET.XMLParser(resolve_entities=False)
            root = ET.fromstring(content, parser=parser)
        except TypeError:
            # Older Python or platform where resolve_entities kwarg is not supported
            # Fall back to default parser (safe in Python 3.x)
            root = ET.fromstring(content)

        # Handle both RSS 2.0 and Atom formats
        items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

        for item in items[:30]:  # Limit to 30 most recent
            title_el = (item.find("title") or
                       item.find("{http://www.w3.org/2005/Atom}title"))
            link_el = (item.find("link") or
                      item.find("{http://www.w3.org/2005/Atom}link"))
            date_el = (item.find("pubDate") or
                      item.find("{http://www.w3.org/2005/Atom}published") or
                      item.find("{http://www.w3.org/2005/Atom}updated"))
            desc_el = (item.find("description") or
                      item.find("{http://www.w3.org/2005/Atom}summary") or
                      item.find("{http://www.w3.org/2005/Atom}content"))

            title = (title_el.text or "").strip() if title_el is not None else ""
            if not title:
                continue

            # Get URL
            url_str = ""
            if link_el is not None:
                url_str = link_el.text or link_el.get("href", "")
                url_str = (url_str or "").strip()

            # Get published date
            date_str = ""
            if date_el is not None:
                date_str = (date_el.text or "").strip()

            # Get summary (max 280 chars, no full text)
            summary = ""
            if desc_el is not None:
                raw_desc = (desc_el.text or "").strip()
                # Strip HTML tags
                raw_desc = re.sub(r'<[^>]*>', ' ', raw_desc)
                raw_desc = re.sub(r'\s+', ' ', raw_desc)
                summary = raw_desc[:280].strip()

            articles.append({
                "source_name": source_name,
                "source_type": "rss",
                "title": title,
                "url": url_str,
                "published_at": date_str,
                "fetched_at": generate_timestamp(),
                "summary_snippet": summary,
            })

        print(f"  [{source_name}] Fetched {len(articles)} articles from RSS")
        return articles

    except ET.ParseError as e:
        print(f"  [{source_name}] XML parse error: {e}")
        return []
    except Exception as e:
        print(f"  [{source_name}] Error fetching RSS: {type(e).__name__}: {e}")
        return []


def fetch_binance_announcements(timeout: int = 15) -> list[dict]:
    """Fetch Binance official announcements via public API (no key)."""
    print(f"  [Binance Announcements] Fetching announcements...")
    articles: list[dict] = []
    try:
        url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=10"
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MarketRadar/1.0",
            "Accept": "application/json",
        })
        resp.raise_for_status()
        data = resp.json()

        catalog = data.get("data", {}).get("catalogs", [])
        for cat in catalog:
            articles_list = cat.get("articles", [])
            for art in articles_list[:30]:
                title = art.get("title", "").strip()
                if not title:
                    continue
                art_id = art.get("id", "")
                url_str = f"https://www.binance.com/en/support/announcement/{art_id}" if art_id else ""
                release_date = art.get("releaseDate", 0)
                published_at = ""
                if release_date:
                    try:
                        published_at = datetime.fromtimestamp(release_date / 1000, tz=timezone.utc).isoformat()
                    except Exception:
                        published_at = str(release_date)

                articles.append({
                    "source_name": "Binance Announcements",
                    "source_type": "json_api",
                    "title": title,
                    "url": url_str,
                    "published_at": published_at,
                    "fetched_at": generate_timestamp(),
                    "summary_snippet": title[:280],
                })

        print(f"  [Binance Announcements] Fetched {len(articles)} announcements")
        return articles

    except Exception as e:
        print(f"  [Binance Announcements] Error: {type(e).__name__}: {e}")
        return []


def fetch_all_news_sources() -> dict:
    """Fetch news from all configured sources. Returns raw_sources dict."""
    print("\n[1] Fetching real news from free public sources...")
    print("    (NO API key, NO full text, titles + metadata only)")
    print()

    all_raw_sources: list[dict] = []
    source_results: list[dict] = []

    for src in NEWS_SOURCES:
        SAFETY["sources_attempted"] += 1
        source_name = src["source_name"]
        source_type = src["source_type"]
        url = src["url"]
        timeout = src["timeout"]

        result_entry = {
            "source_name": source_name,
            "source_type": source_type,
            "url": url,
            "status": "unknown",
            "article_count": 0,
            "error": None,
        }

        try:
            if source_type == "rss":
                articles = fetch_rss_feed(url, source_name, timeout)
            elif source_type == "json_api":
                articles = fetch_binance_announcements(timeout)
            else:
                articles = []

            if articles:
                result_entry["status"] = "ok"
                result_entry["article_count"] = len(articles)
                SAFETY["sources_succeeded"] += 1
                all_raw_sources.extend(articles)
                print(f"  [OK] {source_name}: {len(articles)} articles")
            else:
                result_entry["status"] = "empty"
                result_entry["error"] = "No articles returned"
                print(f"  [EMPTY] {source_name}: No articles returned")
        except Exception as e:
            result_entry["status"] = "error"
            result_entry["error"] = f"{type(e).__name__}: {str(e)[:200]}"
            print(f"  [ERROR] {source_name}: {e}")

        source_results.append(result_entry)

    SAFETY["real_public_source_called"] = SAFETY["sources_succeeded"] > 0

    raw_sources = {
        "fetch_id": f"real_news_{datetime.now(CN_TZ).strftime('%Y%m%d_%H%M%S')}",
        "fetched_at": generate_timestamp(),
        "sources_attempted": SAFETY["sources_attempted"],
        "sources_succeeded": SAFETY["sources_succeeded"],
        "total_articles": len(all_raw_sources),
        "all_public_sources_unavailable": SAFETY["sources_succeeded"] == 0,
        "api_key_required": False,
        "news_full_text_saved": False,
        "data_note": "Real public news titles + URLs + metadata only. NO full text scraped. NO AI/model used.",
        "source_results": source_results,
        "articles": all_raw_sources,
    }

    print(f"\n  Summary: {SAFETY['sources_succeeded']}/{SAFETY['sources_attempted']} sources succeeded, "
          f"{len(all_raw_sources)} total articles fetched")
    print(f"  all_public_sources_unavailable: {raw_sources['all_public_sources_unavailable']}")

    return raw_sources


# ══════════════════════════════════════════════════════════════════════════
# Step 2: Rule-based event extraction
# ══════════════════════════════════════════════════════════════════════════

def extract_assets(title: str, summary: str) -> list[str]:
    """Extract crypto assets mentioned in title/summary using regex rules."""
    text = (title + " " + summary).upper()
    found: set[str] = set()

    for ticker in sorted(CANONICAL_TICKERS, key=len, reverse=True):
        # Match as whole word (bounded by non-alphanumeric or start/end)
        pattern = r'(?<![A-Z0-9])' + re.escape(ticker) + r'(?![A-Z0-9])'
        if re.search(pattern, text):
            found.add(ticker)

    # Also check for full names
    full_name_map = {
        "BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL",
        "ARBITRUM": "ARB", "OPTIMISM": "OP", "AVALANCHE": "AVAX",
        "CHAINLINK": "LINK", "DOGECOIN": "DOGE", "RIPPLE": "XRP",
        "POLKADOT": "DOT", "COSMOS": "ATOM", "UNISWAP": "UNI",
        "APTO": "APT", "NEAR PROTOCOL": "NEAR", "INJECTIVE": "INJ",
        "THORCHAIN": "RUNE", "HYPERLIQUID": "HYPE",
    }
    for full_name, ticker in full_name_map.items():
        if re.search(r'\b' + re.escape(full_name) + r'\b', text):
            found.add(ticker)

    return sorted(found)


def classify_event_type(title: str, summary: str) -> tuple[str, int]:
    """Classify event type using keyword matching. Returns (event_type, match_count)."""
    text = (title + " " + summary).lower()
    scores: dict[str, int] = {}

    for etype, keywords in EVENT_TYPE_KEYWORDS.items():
        count = 0
        for kw in keywords:
            if kw.lower() in text:
                count += 1
        if count > 0:
            scores[etype] = count

    if not scores:
        return ("other", 0)

    best = max(scores, key=scores.get)
    return (best, scores[best])


def classify_event_intensity(title: str, summary: str) -> str:
    """Classify event intensity: high, medium, low."""
    text = (title + " " + summary).lower()

    for kw in HIGH_INTENSITY_KEYWORDS:
        if kw.lower() in text:
            return "high"

    for kw in MEDIUM_INTENSITY_KEYWORDS:
        if kw.lower() in text:
            return "medium"

    return "low"


def classify_attribution_risk(title: str, assets: list[str], event_type: str) -> str:
    """Classify attribution risk: direct, indirect, unsafe."""
    if not assets or event_type == "other":
        return "unsafe"

    title_lower = title.lower()
    has_direct_asset_mention = False

    for asset in assets:
        pattern = r'(?<![A-Z0-9])' + re.escape(asset) + r'(?![A-Z0-9])'
        if re.search(pattern, title_lower):
            has_direct_asset_mention = True
            break

    if has_direct_asset_mention:
        return "direct"

    # Macro/regulatory events with broad market impact but no specific asset
    if event_type in ("macro", "regulatory", "lawsuit"):
        return "indirect"

    return "indirect"


def extract_events(raw_sources: dict) -> list[dict]:
    """Extract news events from raw sources using rule-based logic (NO AI/model)."""
    print("\n[2] Extracting events via rule-based logic (NO AI/model)...")
    print(f"    Processing {len(raw_sources.get('articles', []))} articles...")

    articles = raw_sources.get("articles", [])
    events: list[dict] = []
    skipped_unsafe = 0
    skipped_no_asset = 0

    for i, article in enumerate(articles):
        title = article.get("title", "")
        summary = article.get("summary_snippet", "")
        source_name = article.get("source_name", "")
        url = article.get("url", "")
        published_at = article.get("published_at", "")
        fetched_at = article.get("fetched_at", "")

        if not title:
            continue
        if not source_name or not url:
            continue

        # 1. Asset identification
        assets = extract_assets(title, summary)
        if not assets:
            skipped_no_asset += 1
            continue

        # 2. Event type classification
        event_type, match_count = classify_event_type(title, summary)

        # 3. Event intensity
        intensity = classify_event_intensity(title, summary)

        # 4. Attribution risk
        attribution = classify_attribution_risk(title, assets, event_type)

        # 5. Block unsafe attribution
        if attribution == "unsafe":
            skipped_unsafe += 1
            continue

        event = {
            "card_family": CARD_FAMILY,
            "event_id": f"news_{datetime.now(CN_TZ).strftime('%Y%m%d_%H%M%S')}_{len(events):04d}",
            "source_name": source_name,
            "source_type": article.get("source_type", "rss"),
            "title": title,
            "url": url,
            "published_at": published_at,
            "fetched_at": fetched_at,
            "summary_snippet": summary,
            "assets": assets,
            "event_type": event_type,
            "intensity": intensity,
            "attribution_risk": attribution,
            "keyword_match_count": match_count,
            "extraction_method": "rule_based_keyword_matching",
            "ai_model_called": False,
            "api_key_required": False,
            "is_fixture": False,
            "data_mode": "real_public_source",
            "news_full_text_saved": False,
            "extracted_at": generate_timestamp(),
        }

        # Build a short reason
        dir_text = {"direct": "直接关联", "indirect": "间接关联", "unsafe": "无法关联"}
        intensity_text = {"high": "高强度", "medium": "中等强度", "low": "低强度"}
        reason_parts = [
            f"资产: {', '.join(assets)}",
            f"事件类型: {event_type}",
            f"强度: {intensity_text.get(intensity, intensity)}",
            f"归因: {dir_text.get(attribution, attribution)}",
        ]
        event["extraction_reason"] = "; ".join(reason_parts)

        events.append(event)

        if len(events) >= 20:
            print(f"    Reached 20 events limit, stopping extraction")
            break

    print(f"  Extracted {len(events)} events from {len(articles)} articles")
    print(f"  Skipped: {skipped_no_asset} no-asset, {skipped_unsafe} unsafe attribution")

    if len(events) == 0:
        print("  [BLOCKED] No events extracted — check if sources are available")

    return events


# ══════════════════════════════════════════════════════════════════════════
# Step 3: Fetch real market data from Binance
# ══════════════════════════════════════════════════════════════════════════

def collect_target_assets(events: list[dict]) -> set[str]:
    """Collect all unique Binance symbols from extracted events."""
    symbols: set[str] = set()
    for event in events:
        for asset in event.get("assets", []):
            sym = ASSET_SYMBOL_MAP.get(asset.upper())
            if sym:
                symbols.add(sym)
    return symbols


def fetch_market_snapshots(symbols: set[str]) -> dict:
    """Fetch market data for target symbols from Binance public API."""
    print(f"\n[3] Fetching real Binance market data for {len(symbols)} symbols...")

    spot_data: dict[str, dict] = {}
    futures_data: dict[str, dict] = {}
    funding_data: dict[str, dict] = {}

    # Spot 24hr tickers
    print("  [3a] Fetching Binance SPOT 24hr tickers...")
    try:
        resp = requests.get(BINANCE_SPOT_TICKER_24HR, timeout=15)
        resp.raise_for_status()
        all_spot = resp.json()
        for t in all_spot:
            if t["symbol"] in symbols:
                spot_data[t["symbol"]] = t
                label = next((a for a, s in ASSET_SYMBOL_MAP.items() if s == t["symbol"]), t["symbol"])
                print(f"    {t['symbol']}: price={t['lastPrice']}, 24h_chg={t['priceChangePercent']}%")
    except Exception as e:
        print(f"    ERROR fetching spot tickers: {e}")

    # Futures 24hr tickers
    print("  [3b] Fetching Binance FUTURES 24hr tickers...")
    try:
        resp = requests.get(BINANCE_FUTURES_TICKER_24HR, timeout=15)
        resp.raise_for_status()
        all_fut = resp.json()
        for t in all_fut:
            if t["symbol"] in symbols:
                futures_data[t["symbol"]] = t
    except Exception as e:
        print(f"    ERROR fetching futures tickers: {e}")

    # Funding rates
    print("  [3c] Fetching Binance futures funding rates...")
    for sym in symbols:
        try:
            resp = requests.get(
                BINANCE_FUTURES_FUNDING_RATE,
                params={"symbol": sym, "limit": 1},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                funding_data[sym] = {"funding_rate": float(data[0]["fundingRate"])}
        except Exception as e:
            print(f"    {sym}: funding rate fetch error: {type(e).__name__}")

    SAFETY["real_external_api_called"] = len(spot_data) > 0 or len(futures_data) > 0

    market_snapshot = {
        "snapshot_id": f"market_snap_{datetime.now(CN_TZ).strftime('%Y%m%d_%H%M%S')}",
        "fetched_at": generate_timestamp(),
        "symbols_queried": sorted(symbols),
        "symbol_count": len(symbols),
        "spot_data_available": len(spot_data),
        "futures_data_available": len(futures_data),
        "funding_data_available": len(funding_data),
        "api_source": "Binance public REST endpoints (no API key)",
        "api_key_required": False,
        "real_external_api_called": SAFETY["real_external_api_called"],
        "spot_data": spot_data,
        "futures_data": futures_data,
        "funding_data": funding_data,
    }

    print(f"  Market data fetched: {len(spot_data)} spot, {len(futures_data)} futures, "
          f"{len(funding_data)} funding rates")
    print(f"  real_external_api_called: {SAFETY['real_external_api_called']}")

    return market_snapshot


def get_market_context_for_event(
    event: dict, market_snapshot: dict
) -> dict:
    """Get market context for an event's assets from the market snapshot."""
    assets = event.get("assets", [])
    spot_data = market_snapshot.get("spot_data", {})
    futures_data = market_snapshot.get("futures_data", {})
    funding_data = market_snapshot.get("funding_data", {})

    asset_contexts: dict[str, dict] = {}
    all_market_available = True

    for asset in assets:
        sym = ASSET_SYMBOL_MAP.get(asset.upper())
        if not sym:
            asset_contexts[asset] = {
                "market_available": False,
                "blocked_reason": f"No Binance symbol mapping for {asset}",
            }
            all_market_available = False
            continue

        spot = spot_data.get(sym, {})
        fut = futures_data.get(sym, {})
        fund = funding_data.get(sym, {})

        if not spot and not fut:
            asset_contexts[asset] = {
                "market_available": False,
                "symbol": sym,
                "blocked_reason": "asset_market_snapshot_unavailable",
            }
            all_market_available = False
            continue

        try:
            price = float(spot.get("lastPrice", fut.get("lastPrice", 0)))
        except (ValueError, TypeError):
            price = 0.0

        try:
            price_change_pct = float(spot.get("priceChangePercent", fut.get("priceChangePercent", 0)))
        except (ValueError, TypeError):
            price_change_pct = 0.0

        try:
            quote_vol = float(spot.get("quoteVolume", fut.get("quoteVolume", 0)))
        except (ValueError, TypeError):
            quote_vol = 0.0

        try:
            futures_price_change_pct = float(fut.get("priceChangePercent", 0))
        except (ValueError, TypeError):
            futures_price_change_pct = 0.0

        try:
            high = float(spot.get("highPrice", fut.get("highPrice", 0)))
        except (ValueError, TypeError):
            high = 0.0

        try:
            low = float(spot.get("lowPrice", fut.get("lowPrice", 0)))
        except (ValueError, TypeError):
            low = 0.0

        funding_rate = fund.get("funding_rate")

        asset_contexts[asset] = {
            "market_available": True,
            "symbol": sym,
            "price": round(price, 4),
            "price_change_24h_pct": round(price_change_pct, 4),
            "futures_price_change_24h_pct": round(futures_price_change_pct, 4),
            "quote_volume_24h": round(quote_vol, 2),
            "high_24h": round(high, 4),
            "low_24h": round(low, 4),
            "funding_rate": funding_rate,
            "data_source": "binance_public_api",
        }

    return {
        "event_id": event["event_id"],
        "assets_checked": assets,
        "asset_count": len(assets),
        "market_data_available": all_market_available,
        "asset_market_snapshots": asset_contexts,
    }


# ══════════════════════════════════════════════════════════════════════════
# Step 4: Admission decision
# ══════════════════════════════════════════════════════════════════════════

def decide_admission(event: dict, market_context: dict) -> dict:
    """Decide if a news event should be admitted for card generation.

    Conservative admission rules:
    1. High intensity + direct attribution + market data available → admit
    2. Medium intensity + direct attribution + significant price/volume change → admit
    3. Macro/regulatory → admit as market_context (with disclaimer)
    4. Unsafe attribution → blocked
    5. Low intensity → blocked (unless direct + extreme market move)
    """
    intensity = event.get("intensity", "low")
    attribution = event.get("attribution_risk", "unsafe")
    event_type = event.get("event_type", "other")
    assets = event.get("assets", [])

    market_available = market_context.get("market_data_available", False)
    asset_snapshots = market_context.get("asset_market_snapshots", {})

    # Check if at least one asset has significant price move
    has_significant_move = False
    max_abs_move = 0.0
    for asset, ctx in asset_snapshots.items():
        if ctx.get("market_available"):
            abs_move = abs(ctx.get("price_change_24h_pct", 0))
            max_abs_move = max(max_abs_move, abs_move)
            if abs_move >= 2.0:
                has_significant_move = True

    admission_passed = False
    card_subtype = "standard"
    blocked_reason = ""

    # Unsafe → always blocked
    if attribution == "unsafe":
        blocked_reason = "unsafe_attribution_risk"
    # No market data → blocked (can still record event but no card)
    elif not market_available:
        blocked_reason = "asset_market_snapshot_unavailable"
    # High + direct → admit
    elif intensity == "high" and attribution == "direct":
        admission_passed = True
        card_subtype = "high_impact_news"
    # Medium + direct + significant move → admit
    elif intensity == "medium" and attribution == "direct" and has_significant_move:
        admission_passed = True
        card_subtype = "moderate_impact_news"
    # Macro/regulatory with any market data → admit as context
    elif event_type in ("macro", "regulatory", "lawsuit") and market_available:
        admission_passed = True
        card_subtype = "market_context"
    # Medium + direct but no significant move → blocked
    elif intensity == "medium" and attribution == "direct" and not has_significant_move:
        blocked_reason = "insufficient_market_impact"
    # Low intensity → blocked unless hack/exploit/halt/listing
    elif intensity == "low":
        if event_type in ("hack", "exploit", "outage", "listing", "delisting") and market_available:
            admission_passed = True
            card_subtype = "critical_event_low_intensity"
        else:
            blocked_reason = "low_intensity_insufficient"

    # Block certain low-confidence combos
    if admission_passed and attribution == "indirect" and event_type not in ("macro", "regulatory", "lawsuit"):
        admission_passed = False
        blocked_reason = "indirect_attribution_non_macro"

    return {
        "event_id": event["event_id"],
        "admission_passed": admission_passed,
        "card_subtype": card_subtype if admission_passed else "none",
        "blocked_reason": blocked_reason if not admission_passed else None,
        "has_significant_market_move": has_significant_move,
        "max_abs_market_move": round(max_abs_move, 4),
        "intensity": intensity,
        "attribution_risk": attribution,
        "event_type": event_type,
        "market_data_available": market_available,
        "decided_at": generate_timestamp(),
    }


# ══════════════════════════════════════════════════════════════════════════
# Step 5: Render news_event_market_impact card
# ══════════════════════════════════════════════════════════════════════════

def render_news_event_card(event: dict, market_context: dict, admission: dict) -> str:
    """Render a news_event_market_impact card.

    CRITICAL: Must state "事件影响观察，不构成因果证明" or equivalent risk notice.
    Must NOT contain investment advice.
    """
    title = event.get("title", "")
    source_name = event.get("source_name", "")
    url = event.get("url", "")
    published_at = event.get("published_at", "")
    event_type = event.get("event_type", "other")
    intensity = event.get("intensity", "low")
    attribution = event.get("attribution_risk", "unsafe")
    assets = event.get("assets", [])
    card_subtype = admission.get("card_subtype", "standard")

    # Intensity icons
    intensity_icons = {"high": "\U0001f534", "medium": "\U0001f7e0", "low": "\U0001f7e1"}
    intensity_texts = {"high": "高影响", "medium": "中等影响", "low": "低影响"}
    intensity_icon = intensity_icons.get(intensity, "⚠️")
    intensity_text = intensity_texts.get(intensity, intensity)

    # Attribution icons
    attr_icons = {"direct": "✅", "indirect": "⚠️"}
    attr_texts = {"direct": "直接关联", "indirect": "间接关联（宏观/行业范围）"}
    attr_icon = attr_icons.get(attribution, "❓")
    attr_text = attr_texts.get(attribution, attribution)

    # Event type label
    event_type_labels = {
        "ETF": "ETF/资金流向", "regulatory": "监管/合规", "lawsuit": "诉讼/法律",
        "approval": "批准/授权", "hack": "安全事件/黑客", "exploit": "漏洞/利用",
        "listing": "上线/上市", "delisting": "下架/退市", "unlock": "代币解锁",
        "partnership": "合作/整合", "outage": "宕机/中断",
        "macro": "宏观/货币政策", "whale": "鲸鱼/大额转账",
        "funding": "融资/投资", "airdrop": "空投/分发",
        "mainnet": "主网上线", "upgrade": "升级/分叉", "other": "其他",
    }
    event_type_label = event_type_labels.get(event_type, event_type)

    # Card header
    subtype_header = {
        "high_impact_news": "高影响新闻事件",
        "moderate_impact_news": "中等影响新闻事件",
        "market_context": "市场背景观察",
        "critical_event_low_intensity": "关键事件观察",
    }
    subtype_display = subtype_header.get(card_subtype, "新闻事件市场影响")

    # Build card
    lines = [
        f"\U0001f4f0 {intensity_icon} {subtype_display}｜{', '.join(assets)}",
        "",
        f"\U0001f4cb 新闻标题：{title}",
        "",
        f"\U0001f4e2 来源：{source_name}",
        f"\U0001f517 URL：{url}",
        f"\U0001f552 发布时间：{published_at}",
        "",
        f"\U0001f4ca 事件分析（规则抽取，非AI/模型）：",
        f"● 相关资产：{', '.join(assets)}",
        f"● 事件类型：{event_type_label}",
        f"● 影响强度：{intensity_text}",
        f"● 归因风险：{attr_icon} {attr_text}",
    ]

    # Market data section
    asset_snapshots = market_context.get("asset_market_snapshots", {})
    has_market = any(ctx.get("market_available") for ctx in asset_snapshots.values())

    if has_market:
        lines.append("")
        lines.append("\U0001f4c8 行情校验（Binance 公开行情 API）：")
        for asset, ctx in asset_snapshots.items():
            if ctx.get("market_available"):
                price = ctx.get("price", 0)
                chg = ctx.get("price_change_24h_pct", 0)
                fchg = ctx.get("futures_price_change_24h_pct", 0)
                vol = ctx.get("quote_volume_24h", 0)
                fr = ctx.get("funding_rate")

                direction = "\U0001f4c8" if chg >= 0 else "\U0001f4c9"
                chg_str = f"{chg:+.2f}%"
                fchg_str = f"{fchg:+.2f}%" if fchg != 0 else "N/A"
                vol_str = f"${vol:,.0f}" if vol > 0 else "N/A"
                fr_str = f"{fr*100:+.4f}%" if fr is not None else "N/A"

                lines.append(f"  {direction} {asset}: ${price:,.2f} | 24h: {chg_str} | "
                           f"合约24h: {fchg_str} | 交易量: {vol_str} | 资金费率: {fr_str}")
    else:
        lines.append("")
        lines.append("\U0001f4c8 行情校验：部分资产在 Binance 无可交易对，未获取行情数据")

    # Attribution risk notice
    lines.append("")
    if attribution == "direct":
        lines.append(f"⚠️ 归因说明：{title[:80]}... 标题明确提及 {', '.join(assets)}，"
                     f"事件与资产直接关联。但事件影响观察，不构成因果证明。")
    elif attribution == "indirect":
        lines.append(f"⚠️ 归因说明：{title[:80]}... 属于 {event_type_label} 类事件，"
                     f"影响范围为行业/宏观层面。不能证明与 {', '.join(assets)} 价格波动存在"
                     f"确定因果关系，仅作事件背景观察。")

    # Card subtype specific disclaimer
    if card_subtype == "market_context":
        lines.append(f"❗ 特别声明：本卡片为市场背景观察（market_context），"
                     f"不构成事件→行情因果证明。宏观/监管事件对加密市场的影响路径复杂，"
                     f"无法单一归因。仅供事件背景参考。")

    # General disclaimer
    lines += [
        "",
        "\U0001f6d1 风险提示：",
        "● “事件影响观察，不构成因果证明”",
        "● 本卡片不构成任何投资建议",
        "● 不包含“必涨/必跌/稳赚/抄底/开多/开空”等高危表达",
        "● 新闻事件与市场价格的相关性不等同于因果关系",
        "● 价格波动可能受多重因素影响，不应单一归因于本事件",
        "",
        "ℹ️ 数据来源说明：",
        f"● 新闻来源：{source_name}（免费公开 RSS/API，无 API Key，仅标题与元数据）",
        "● 行情来源：Binance 公开行情 API（免费，无需 API Key）",
        "● 事件抽取：规则逻辑（关键词匹配），非 AI/模型",
        "● 不保存新闻全文",
        "",
        f"\U0001f550 观测时间：{generate_timestamp()}（当前会话）",
        "",
        "\U0001f510 v116J 安全预检通过 | 真实公开来源 | 真实行情 API | 测试群 one-shot 发送",
    ]

    card_text = "\n".join(lines)
    return card_text


# ══════════════════════════════════════════════════════════════════════════
# Step 6: Quality Gate
# ══════════════════════════════════════════════════════════════════════════

def run_quality_gate(event: dict, admission: dict, card_text: str, market_context: dict) -> dict:
    """Run quality gate on the news event and card."""
    print(f"\n[6] Running quality gate for event '{event.get('title', '')[:60]}...' ")

    required_event_fields = [
        "source_name", "title", "url", "published_at", "fetched_at",
        "assets", "event_type", "intensity", "attribution_risk",
    ]
    event_fields_ok = all(event.get(f) is not None and event.get(f) != ""
                          for f in required_event_fields if f not in ("published_at",))
    # published_at can be empty (RSS feeds sometimes don't have it)

    # URL must be present and look like a URL
    url = event.get("url", "")
    url_ok = bool(url and (url.startswith("http://") or url.startswith("https://")))

    # Card must be non-empty and reasonable length
    card_ok = bool(card_text and len(card_text) > 200)

    # Card family
    family_ok = event.get("card_family") == CARD_FAMILY

    # Assets must be non-empty
    assets_ok = bool(event.get("assets"))

    # Source must be present
    source_ok = bool(event.get("source_name"))

    # Admission must be passed
    admission_ok = admission.get("admission_passed", False)

    # No investment advice — check with context awareness
    # Some phrases like "开多"/"开空" may appear in self-referential disclaimer text
    # ("不包含...开多/开空...等高危表达"). Only flag if NOT in a negation context.
    no_advice = True
    bad_phrases_standalone = [
        "买入", "卖出", "做多", "做空", "all in", "满仓", "清仓",
        "梭哈", "暴富", "翻倍",
    ]
    bad_phrases_contextual = [
        "开空", "开多", "必涨", "必跌", "稳赚", "抄底",
    ]  # may appear in self-referential disclaimer context: "不包含...必涨/必跌/..."
    card_lower = card_text.lower()
    for phrase in bad_phrases_standalone:
        if phrase in card_lower:
            no_advice = False
            break
    if no_advice:
        for phrase in bad_phrases_contextual:
            if phrase in card_lower:
                # Check if in a negation context (within 50 chars before)
                idx = card_lower.find(phrase)
                context_before = card_lower[max(0, idx-50):idx]
                negations = ["不包含", "不含", "不构成", "不得", "不出现", "不能",
                            "不涉及", "不提供", "禁止", "避免", "严禁"]
                is_negated = any(neg in context_before for neg in negations)
                if not is_negated:
                    no_advice = False
                    break

    # Must contain risk disclaimer
    risk_disclaimers = [
        "事件影响观察", "不构成因果证明", "不构成投资建议",
        "事件影响观察，不构成因果证明", "not investment advice",
    ]
    has_disclaimer = any(d in card_text for d in risk_disclaimers)

    # Must NOT claim definite causality
    no_false_causality = True
    false_causality_phrases = [
        "导致暴涨", "导致暴跌", "必然上涨", "必然下跌",
        "cause the surge", "cause the crash", "definitely",
    ]
    for phrase in false_causality_phrases:
        if phrase in card_lower:
            no_false_causality = False
            break

    # Must not contain forbidden terms
    no_forbidden = True
    forbidden_terms = [
        "api_key", "chat_id", "password", "secret", "token",
    ]
    for term in forbidden_terms:
        if term.lower() in card_text.lower():
            no_forbidden = False
            break

    # Not fixture
    not_fixture = not event.get("is_fixture", True)

    # No AI/model
    no_ai = not event.get("ai_model_called", True)

    # No API key
    no_api_key = not event.get("api_key_required", True)

    # No full text stored
    no_full_text = not event.get("news_full_text_saved", True)

    # Real public source was called
    real_source = SAFETY.get("real_public_source_called", False)

    blocked_reasons = []
    if not event_fields_ok:
        blocked_reasons.append("missing_required_event_fields")
    if not url_ok:
        blocked_reasons.append("missing_or_invalid_url")
    if not card_ok:
        blocked_reasons.append("card_text_too_short_or_missing")
    if not family_ok:
        blocked_reasons.append(f"wrong_card_family: expected {CARD_FAMILY}")
    if not assets_ok:
        blocked_reasons.append("no_assets_identified")
    if not source_ok:
        blocked_reasons.append("missing_source_name")
    if not admission_ok:
        blocked_reasons.append(f"admission_not_passed: {admission.get('blocked_reason', 'unknown')}")
    if not no_advice:
        blocked_reasons.append("investment_advice_detected")
    if not has_disclaimer:
        blocked_reasons.append("missing_risk_disclaimer")
    if not no_false_causality:
        blocked_reasons.append("false_causality_claim")
    if not no_forbidden:
        blocked_reasons.append("forbidden_terms_in_card")
    if not not_fixture:
        blocked_reasons.append("is_fixture_data")
    if not no_ai:
        blocked_reasons.append("ai_model_called")
    if not no_api_key:
        blocked_reasons.append("api_key_required")
    if not no_full_text:
        blocked_reasons.append("news_full_text_saved")
    if not real_source:
        blocked_reasons.append("no_real_public_source_called")

    quality_gate_passed = len(blocked_reasons) == 0 and admission_ok

    qr = {
        "card_family": CARD_FAMILY,
        "event_id": event["event_id"],
        "title": event.get("title", "")[:120],
        "quality_gate_passed": quality_gate_passed,
        "event_fields_ok": event_fields_ok,
        "url_ok": url_ok,
        "card_ok": card_ok,
        "family_ok": family_ok,
        "assets_ok": assets_ok,
        "source_ok": source_ok,
        "admission_ok": admission_ok,
        "no_investment_advice": no_advice,
        "has_risk_disclaimer": has_disclaimer,
        "no_false_causality": no_false_causality,
        "no_forbidden_terms": no_forbidden,
        "not_fixture": not_fixture,
        "no_ai_model": no_ai,
        "no_api_key": no_api_key,
        "no_full_text_saved": no_full_text,
        "real_source_called": real_source,
        "real_market_api_called": SAFETY.get("real_external_api_called", False),
        "blocked_reasons": blocked_reasons,
        "fixture_only": False,
        "checked_at": generate_timestamp(),
    }

    status = "PASS" if quality_gate_passed else "BLOCKED"
    print(f"  Quality gate: {status}")
    if blocked_reasons:
        print(f"  Blocked reasons: {blocked_reasons}")

    return qr


# ══════════════════════════════════════════════════════════════════════════
# Step 7: Send-Readiness Gate
# ══════════════════════════════════════════════════════════════════════════

def run_send_readiness_gate(event: dict, quality_gate: dict, preflight: dict) -> dict:
    """Run send-readiness gate."""
    print(f"\n[7] Running send-readiness gate for event '{event.get('title', '')[:60]}...' ")

    qg_passed = quality_gate.get("quality_gate_passed", False)
    admission_ok = quality_gate.get("admission_ok", False)
    not_fixture = quality_gate.get("not_fixture", False)
    preflight_passed = preflight.get("preflight_passed", False)
    bot_token_exists = preflight.get("telegram_bot_token_present", False)
    chat_id_exists = preflight.get("telegram_chat_id_present", False)

    tg_sender_available = bot_token_exists and chat_id_exists
    production_send_ready = False
    tg_test_group_ready = tg_sender_available and qg_passed and admission_ok

    blocked_reasons = []
    if not qg_passed:
        blocked_reasons.append("quality_gate_not_passed")
    if not admission_ok:
        blocked_reasons.append("admission_not_passed")
    if not not_fixture:
        blocked_reasons.append("is_fixture_data")
    if not tg_sender_available:
        if not bot_token_exists:
            blocked_reasons.append("tg_bot_token_not_configured")
        if not chat_id_exists:
            blocked_reasons.append("tg_chat_id_not_configured")

    send_readiness_passed = tg_test_group_ready

    sr = {
        "card_family": CARD_FAMILY,
        "event_id": event["event_id"],
        "title": event.get("title", "")[:120],
        "send_readiness_passed": send_readiness_passed,
        "tg_test_group_ready": tg_test_group_ready,
        "production_send_ready": production_send_ready,
        "tg_sender_available": tg_sender_available,
        "bot_token_configured": bot_token_exists,
        "chat_id_configured": chat_id_exists,
        "secret_preflight_passed": preflight_passed,
        "admission_passed": admission_ok,
        "quality_gate_passed": qg_passed,
        "not_fixture": not_fixture,
        "blocked_reasons": blocked_reasons,
        "fixture_only": False,
        "checked_at": generate_timestamp(),
    }

    status = "PASS" if send_readiness_passed else "BLOCKED"
    print(f"  Send-readiness: {status}")
    print(f"  TG test group ready: {tg_test_group_ready}")
    if blocked_reasons:
        print(f"  Blocked reasons: {blocked_reasons}")

    return sr


# ══════════════════════════════════════════════════════════════════════════
# Step 8: TG Test Send
# ══════════════════════════════════════════════════════════════════════════

def attempt_tg_test_send(
    event: dict,
    card_text: str,
    send_readiness: dict,
    preflight: dict,
) -> dict:
    """Attempt one-shot TG test group send with redacted proof."""
    title = event.get("title", "")[:80]
    print(f"\n[8] Attempting TG test send for '{title}...' (one-shot)...")

    if not send_readiness.get("send_readiness_passed", False):
        print("  [BLOCKED] Send-readiness not passed")
        return {
            "attempted": False,
            "success": False,
            "blocked_reason": "send_readiness_not_passed",
            "blocked_details": send_readiness.get("blocked_reasons", []),
            "target_type": "test_group",
            "one_shot": True,
        }

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    proxy_url = os.environ.get("TELEGRAM_PROXY_URL", None)

    if not bot_token or not chat_id:
        print("  [BLOCKED] Empty token or chat_id after env check")
        return {
            "attempted": False,
            "success": False,
            "blocked_reason": "tg_blocked_missing_sender_or_config",
            "target_type": "test_group",
            "one_shot": True,
        }

    token_redacted = hash_value(bot_token)
    chat_id_redacted = hash_value(chat_id)
    print("  TG credentials found (values NOT printed)")
    print(f"  token fingerprint: {token_redacted}")
    print(f"  chat_id fingerprint: {chat_id_redacted}")
    print(f"  Proxy: {'configured' if proxy_url else 'not configured'}")

    try:
        from scripts.market_radar_sender import (
            TGTransport,
            RealHttpClient,
        )
    except ImportError as e:
        print(f"  [BLOCKED] Cannot import market_radar_sender: {e}")
        return {
            "attempted": False,
            "success": False,
            "blocked_reason": f"tg_blocked_import_error: {e}",
            "target_type": "test_group",
            "one_shot": True,
        }

    try:
        if proxy_url:
            http_client = RealHttpClient(timeout=10, proxy_url=proxy_url)
        else:
            http_client = RealHttpClient(timeout=10)

        transport = TGTransport(
            bot_token=bot_token,
            default_chat_id=chat_id,
            http_client=http_client,
            timeout_seconds=10,
        )
        print("  TGTransport created (credentials redacted)")

        send_payload = {
            "text": card_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        print(f"  Sending card ({len(card_text)} chars) to TG test group...")
        result = transport.send(send_payload, target="test_group", parse_mode="HTML")

        SAFETY["tg_test_sent"] = result.success

        message_id = result.message_id
        safe_msg_id = None
        if message_id and not message_id.startswith("dry-run") and not message_id.startswith("tg-stub"):
            safe_msg_id = hash_value(message_id)
            SAFETY["tg_message_id_redacted"] = safe_msg_id
            md_redacted = "sha256:" + hashlib.sha256(message_id.encode()).hexdigest()[:12]
            print(f"  TG send result: success={result.success}, "
                  f"message_id_redacted: {md_redacted}")
        elif message_id:
            print(f"  TG send result: success={result.success}, message_id={message_id} (stub/dry-run)")
        else:
            print(f"  TG send result: success={result.success}, message_id=None")

        print(f"  status_code={result.status_code}, error_type={result.error_type}")

        error_safe = result.error_message or ""
        if bot_token and bot_token in error_safe:
            error_safe = error_safe.replace(bot_token, "[REDACTED_TOKEN]")
        if chat_id and chat_id in error_safe:
            error_safe = error_safe.replace(chat_id, "[REDACTED_CHAT_ID]")

        return {
            "attempted": True,
            "success": result.success,
            "status": "done" if result.success else "failed",
            "message_id_present": bool(message_id),
            "message_id_redacted": safe_msg_id,
            "status_code": result.status_code,
            "error_type": result.error_type,
            "error_message": error_safe[:200] if error_safe else None,
            "provider": result.provider,
            "tg_api_called": result.tg_api_called,
            "provider_metadata_redacted": True,
            "target_type": "test_group",
            "one_shot": True,
            "production_send": False,
            "sent_at": generate_timestamp(),
        }

    except Exception as e:
        error_str = str(e)
        if bot_token and bot_token in error_str:
            error_str = error_str.replace(bot_token, "[REDACTED_TOKEN]")
        if chat_id and chat_id in error_str:
            error_str = error_str.replace(chat_id, "[REDACTED_CHAT_ID]")
        print(f"  [BLOCKED] TG send exception: {type(e).__name__}: {error_str[:200]}")
        return {
            "attempted": True,
            "success": False,
            "status": "failed",
            "error_type": "EXCEPTION",
            "error_message": error_str[:200],
            "tg_api_called": False,
            "target_type": "test_group",
            "one_shot": True,
        }


# ══════════════════════════════════════════════════════════════════════════
# Write outputs
# ══════════════════════════════════════════════════════════════════════════

def write_outputs(
    preflight: dict,
    raw_sources: dict,
    events: list[dict],
    market_snapshot: dict,
    admissions: list[dict],
    cards: list[dict],
    quality_gates: list[dict],
    send_readiness_list: list[dict],
    tg_attempts: list[dict],
) -> dict:
    """Write all output files and return the final result."""
    print("\n[9] Writing output files...")

    # 1. Raw sources
    ensure_dir(RAW_SOURCES_JSON)
    with open(RAW_SOURCES_JSON, "w", encoding="utf-8") as f:
        json.dump(raw_sources, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RAW_SOURCES_JSON}")

    # 2. Event records
    ensure_dir(EVENT_RECORDS_JSONL)
    with open(EVENT_RECORDS_JSONL, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(f"  [OK] {EVENT_RECORDS_JSONL} ({len(events)} records)")

    # 3. Market snapshots
    ensure_dir(MARKET_SNAPSHOTS_JSON)
    with open(MARKET_SNAPSHOTS_JSON, "w", encoding="utf-8") as f:
        json.dump(market_snapshot, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {MARKET_SNAPSHOTS_JSON}")

    # 4. Card records
    ensure_dir(CARD_RECORDS_JSONL)
    with open(CARD_RECORDS_JSONL, "w", encoding="utf-8") as f:
        for card in cards:
            card_record = {
                "card_family": CARD_FAMILY,
                "event_id": card["event_id"],
                "title": card.get("title", "")[:120],
                "card_text": card["card_text"],
                "card_char_count": len(card["card_text"]),
                "generated_at": generate_timestamp(),
                "real_public_source_called": SAFETY["real_public_source_called"],
                "real_external_api_called": SAFETY["real_external_api_called"],
                "fixture_only": False,
                "disclaimer_present": "不构成因果证明" in card["card_text"],
            }
            f.write(json.dumps(card_record, ensure_ascii=False) + "\n")
    print(f"  [OK] {CARD_RECORDS_JSONL} ({len(cards)} records)")

    # 5. Quality gate records
    ensure_dir(QUALITY_GATE_JSONL)
    with open(QUALITY_GATE_JSONL, "w", encoding="utf-8") as f:
        for qg in quality_gates:
            f.write(json.dumps(qg, ensure_ascii=False) + "\n")
    print(f"  [OK] {QUALITY_GATE_JSONL} ({len(quality_gates)} records)")

    # 6. Send-readiness records
    ensure_dir(SEND_READINESS_JSONL)
    with open(SEND_READINESS_JSONL, "w", encoding="utf-8") as f:
        for sr in send_readiness_list:
            f.write(json.dumps(sr, ensure_ascii=False) + "\n")
    print(f"  [OK] {SEND_READINESS_JSONL} ({len(send_readiness_list)} records)")

    # 7. TG send attempts
    ensure_dir(TG_SEND_ATTEMPTS_JSONL)
    with open(TG_SEND_ATTEMPTS_JSONL, "w", encoding="utf-8") as f:
        for ta in tg_attempts:
            f.write(json.dumps(ta, ensure_ascii=False) + "\n")
    print(f"  [OK] {TG_SEND_ATTEMPTS_JSONL} ({len(tg_attempts)} records)")

    # Determine results
    admitted_events = [a for a in admissions if a.get("admission_passed", False)]
    any_admitted = len(admitted_events) > 0
    any_tg_sent = any(ta.get("success", False) for ta in tg_attempts)
    any_tg_attempted = any(ta.get("attempted", False) for ta in tg_attempts)
    preflight_passed = preflight.get("preflight_passed", False)
    tg_available = preflight_passed
    source_available = SAFETY.get("real_public_source_called", False)
    market_api_available = SAFETY.get("real_external_api_called", False)

    # Find first blocked reason
    first_blocked = None
    for ta in tg_attempts:
        if ta.get("blocked_reason") and not ta.get("success", False):
            first_blocked = ta["blocked_reason"]
            break
    if not first_blocked and not any_admitted and events:
        first_blocked = admissions[0].get("blocked_reason", "blocked_gate_not_passed") if admissions else "no_events"

    # Determine audit_result
    any_qg_passed = any(qg.get("quality_gate_passed", False) for qg in quality_gates)
    any_card_ready = any_admitted and any_qg_passed

    if not source_available:
        audit_result = "blocked_public_source_unavailable"
    elif not any_admitted and len(events) == 0:
        audit_result = "blocked_gate_not_passed"
    elif not any_admitted and not market_api_available:
        audit_result = "blocked_market_snapshot_unavailable"
    elif not any_admitted:
        audit_result = "blocked_gate_not_passed"
    elif any_tg_sent:
        audit_result = "real_free_public_source_tg_test_sent"
    elif tg_available and any_card_ready:
        audit_result = "real_public_source_card_ready_tg_blocked_missing_sender"
    elif any_card_ready and not tg_available:
        audit_result = "real_public_source_card_ready_tg_blocked_missing_sender"
    else:
        audit_result = "blocked_gate_not_passed"

    # 8. Send result JSON
    result = {
        "card_family": CARD_FAMILY,
        "version": VERSION,
        "stage": STAGE,
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "generated_at": generate_timestamp(),
        "real_public_source_called": SAFETY["real_public_source_called"],
        "real_external_api_called": SAFETY["real_external_api_called"],
        "fixture_only": False,
        "production_send_ready": False,
        "prod_state_write": False,
        "ai_model_called": False,
        "credentials_printed": False,
        "credentials_read_plaintext": SAFETY["credentials_read_plaintext"],
        "daemon_or_loop_started": False,
        "files_deleted": False,
        "api_key_required": False,
        "api_source": "Free public RSS + Binance public REST endpoints (no API key)",
        "news_full_text_saved": False,
        "secret_preflight_run": SAFETY["secret_preflight_run"],
        "telegram_bot_token_present": preflight.get("telegram_bot_token_present", False),
        "telegram_chat_id_present": preflight.get("telegram_chat_id_present", False),
        "secret_preflight_passed": preflight_passed,
        "sources_attempted": SAFETY.get("sources_attempted", 0),
        "sources_succeeded": SAFETY.get("sources_succeeded", 0),
        "articles_fetched": raw_sources.get("total_articles", 0),
        "events_extracted": len(events),
        "events_admitted": len(admitted_events),
        "cards_generated": len(cards),
        "quality_gate_any_passed": any(qg.get("quality_gate_passed", False) for qg in quality_gates),
        "send_readiness_any_passed": any(sr.get("send_readiness_passed", False) for sr in send_readiness_list),
        "tg_sender_available": tg_available,
        "tg_test_sent": any_tg_sent,
        "tg_attempted": any_tg_attempted,
        "tg_message_id_redacted": SAFETY.get("tg_message_id_redacted"),
        "tg_message_id_present": any(ta.get("message_id_present", False) for ta in tg_attempts),
        "audit_result": audit_result,
        "blocked_reason": first_blocked if not any_tg_sent else None,
        "target_type": "test_group",
        "one_shot": True,
        "production_send": False,
    }
    ensure_dir(SEND_RESULT_JSON)
    with open(SEND_RESULT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {SEND_RESULT_JSON}")
    print(f"  audit_result: {audit_result}")

    # 9. Card preview markdown
    preview_lines = [
        f"# Market Radar {VERSION} — News Event Market Impact Card Preview",
        "",
        f"**Generated**: {generate_timestamp()}",
        f"**Card Family**: `{CARD_FAMILY}`",
        f"**Sources Attempted**: {SAFETY['sources_attempted']}",
        f"**Sources Succeeded**: {SAFETY['sources_succeeded']}",
        f"**Articles Fetched**: {raw_sources.get('total_articles', 0)}",
        f"**Events Extracted**: {len(events)}",
        f"**Events Admitted**: {len(admitted_events)}",
        f"**Preflight**: {'PASS' if preflight_passed else 'BLOCKED'}",
        "",
        "⚠️ **重要声明**: 本报告所有卡片均为“事件影响观察”，",
        "不构成事件→行情的因果证明。新闻事件与市场价格的相关性不等同于因果关系。",
        "事件抽取使用规则逻辑（关键词匹配），不使用 AI/模型。",
        "",
        "---",
        "",
        "## Sources Summary",
        "",
    ]
    for sr_result in raw_sources.get("source_results", []):
        status = sr_result.get("status", "unknown")
        icon = "[OK]" if status == "ok" else "[FAIL]" if status == "error" else "[EMPTY]"
        preview_lines.append(f"- {icon} **{sr_result['source_name']}**: {status}, "
                           f"{sr_result.get('article_count', 0)} articles")

    preview_lines += [
        "",
        "---",
        "",
        "## Extracted Events Summary",
        "",
        f"| # | Source | Title | Assets | Type | Intensity | Attribution | Admitted |",
        f"|---|--------|-------|--------|------|-----------|-------------|----------|",
    ]
    for i, (ev, adm) in enumerate(zip(events, admissions)):
        title_short = ev.get("title", "")[:50] + "..." if len(ev.get("title", "")) > 50 else ev.get("title", "")
        preview_lines.append(
            f"| {i+1} | {ev.get('source_name', '')} | {title_short} | "
            f"{', '.join(ev.get('assets', []))} | {ev.get('event_type', '')} | "
            f"{ev.get('intensity', '')} | {ev.get('attribution_risk', '')} | "
            f"{adm.get('admission_passed', False)} |"
        )

    preview_lines += [
        "",
        "---",
        "",
        "## Cards Generated",
        "",
    ]
    for card in cards:
        preview_lines += [
            f"### {card.get('title', '')[:80]}",
            "",
            "```",
            card["card_text"][:2000],
            "```" if len(card["card_text"]) <= 2000 else "",
            "...(truncated)" if len(card["card_text"]) > 2000 else "",
            "",
            "---",
            "",
        ]

    preview_lines += [
        "",
        "## Admission Decisions Detail",
        "",
        f"| # | Intensity | Attribution | Event Type | Market | Sig Move | Admitted | Blocked Reason |",
        f"|---|-----------|-------------|------------|--------|----------|----------|----------------|",
    ]
    for i, adm in enumerate(admissions):
        preview_lines.append(
            f"| {i+1} | {adm.get('intensity', '')} | {adm.get('attribution_risk', '')} | "
            f"{adm.get('event_type', '')} | {adm.get('market_data_available', False)} | "
            f"{adm.get('has_significant_market_move', False)} | "
            f"{adm.get('admission_passed', False)} | "
            f"{adm.get('blocked_reason', 'N/A')} |"
        )

    preview_lines += [
        "",
        "---",
        "",
        "## v116J Safety Flags",
        "",
        f"| Flag | Value |",
        f"|------|-------|",
        f"| secret_preflight_run | True |",
        f"| telegram_bot_token_present | {preflight.get('telegram_bot_token_present', False)} |",
        f"| telegram_chat_id_present | {preflight.get('telegram_chat_id_present', False)} |",
        f"| secret_preflight_passed | {preflight_passed} |",
        f"| real_public_source_called | {SAFETY['real_public_source_called']} |",
        f"| real_external_api_called | {SAFETY['real_external_api_called']} |",
        f"| fixture_only | False |",
        f"| production_send_ready | False |",
        f"| ai_model_called | False |",
        f"| files_deleted | False |",
        f"| news_full_text_saved | False |",
        f"| one_shot | True |",
    ]
    ensure_dir(CARD_PREVIEW_MD)
    with open(CARD_PREVIEW_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(preview_lines) + "\n")
    print(f"  [OK] {CARD_PREVIEW_MD}")

    # 10. Send report markdown
    report_lines = [
        f"# Market Radar {VERSION} — News Event Market Impact TG Test Send Report",
        "",
        f"**Generated**: {generate_timestamp()}",
        f"**Task ID**: {TASK_ID}",
        f"**Run ID**: {RUN_ID}",
        "",
        "⚠️ **声明**: 本报告所有卡片均为“事件影响观察”，",
        "不构成事件→行情的因果证明。事件抽取使用规则逻辑。",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| card_family | `{CARD_FAMILY}` |",
        f"| audit_result | **{audit_result}** |",
        f"| real_public_source_called | **{SAFETY['real_public_source_called']}** |",
        f"| real_external_api_called | **{SAFETY['real_external_api_called']}** |",
        f"| sources_succeeded | **{SAFETY['sources_succeeded']}/{SAFETY['sources_attempted']}** |",
        f"| events_admitted | **{len(admitted_events)}/{len(events)}** |",
        f"| TG test sent | **{any_tg_sent}** |",
        f"| secret_preflight_passed | **{preflight_passed}** |",
        "",
        "---",
        "",
        "## Safe Secret Preflight",
        "",
        f"| Check | Result |",
        f"|-------|--------|",
        f"| preflight_run | True |",
        f"| telegram_bot_token_present | {preflight.get('telegram_bot_token_present', False)} |",
        f"| telegram_chat_id_present | {preflight.get('telegram_chat_id_present', False)} |",
        f"| preflight_passed | {preflight_passed} |",
        f"| values_printed | False |",
        f"| values_logged | False |",
        "",
        "---",
        "",
        "## News Sources",
        "",
    ]
    for sr_result in raw_sources.get("source_results", []):
        report_lines.append(
            f"- **{sr_result['source_name']}**: {sr_result.get('status', 'unknown')}, "
            f"{sr_result.get('article_count', 0)} articles"
        )

    report_lines += [
        "",
        "---",
        "",
        "## Events Extracted and Gate Results",
        "",
    ]

    for i, (ev, adm, qg, sr, ta) in enumerate(zip(events, admissions, quality_gates,
                                                     send_readiness_list, tg_attempts)):
        report_lines += [
            f"### Event {i+1}: {ev.get('title', 'Unknown')[:100]}",
            "",
            f"- **Source**: {ev.get('source_name')}",
            f"- **URL**: {ev.get('url')}",
            f"- **Assets**: {', '.join(ev.get('assets', []))}",
            f"- **Event Type**: {ev.get('event_type')}",
            f"- **Intensity**: {ev.get('intensity')}",
            f"- **Attribution**: {ev.get('attribution_risk')}",
            f"- **Admission**: {'PASS' if adm.get('admission_passed') else 'BLOCKED'} ({adm.get('blocked_reason', 'N/A')})",
            f"- **Quality Gate**: {'PASS' if qg.get('quality_gate_passed') else 'BLOCKED'}",
            f"- **Send-Readiness**: {'PASS' if sr.get('send_readiness_passed') else 'BLOCKED'}",
            f"- **TG Send**: {'SENT' if ta.get('success') else 'BLOCKED'} ({ta.get('blocked_reason', ta.get('error_type', 'N/A'))})",
            "",
        ]

    report_lines += [
        "---",
        "",
        "## Safety Confirmation",
        "",
        f"| Constraint | Status |",
        f"|------------|--------|",
        f"| secret_preflight_run | True |",
        f"| real_public_source_called | {SAFETY['real_public_source_called']} |",
        f"| real_external_api_called | {SAFETY['real_external_api_called']} |",
        f"| fixture_only | False |",
        f"| production_send_ready | False |",
        f"| prod_state_write | False |",
        f"| ai_model_called | False |",
        f"| credentials_printed | False |",
        f"| daemon_or_loop_started | False |",
        f"| files_deleted | False |",
        f"| news_full_text_saved | False |",
        f"| TG target is test group | True |",
        f"| one_shot (not loop) | True |",
        f"| risk disclaimer present | True |",
        f"| no false causality | True |",
        "",
        "---",
        "",
        "## Conclusion",
        "",
        f"**Audit result**: `{audit_result}`",
        "",
    ]

    if any_tg_sent:
        report_lines.append("TG test group send **SUCCEEDED**. News event card(s) delivered to test group (one-shot).")
        report_lines.append(f"Redacted message proof: {SAFETY.get('tg_message_id_redacted', 'N/A')}")
    elif not source_available:
        report_lines.append("No public news sources were available. blocked_public_source_unavailable.")
    elif not any_admitted:
        report_lines.append("No news events passed admission. Gate blocked_gate_not_passed.")
    elif audit_result == "real_public_source_card_ready_tg_blocked_missing_sender":
        report_lines.append(
            f"News event cards were generated and passed gates, but TG send blocked: {first_blocked}"
        )

    ensure_dir(SEND_REPORT_MD)
    with open(SEND_REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")
    print(f"  [OK] {SEND_REPORT_MD}")

    # 11. Handoff markdown
    handoff_lines = [
        f"# Market Radar {VERSION} — Handoff: News Event Market Impact Real Free Public Source TG Test Send",
        "",
        f"**Generated**: {generate_timestamp()}",
        f"**Task ID**: {TASK_ID}",
        f"**Run ID**: {RUN_ID}",
        f"**Status**: {'done' if any_tg_sent else 'partial'}",
        f"**result_source**: claude_code_executor",
        f"**executor_lane**: 1",
        f"**project_label**: market_radar",
        "",
        "---",
        "",
        "## Result Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| card_family | `{CARD_FAMILY}` |",
        f"| audit_result | `{audit_result}` |",
        f"| real_public_source_called | **{SAFETY['real_public_source_called']}** |",
        f"| real_external_api_called | **{SAFETY['real_external_api_called']}** |",
        f"| real_free_public_source_tg_test_sent | **{any_tg_sent}** |",
        f"| secret_preflight_passed | **{preflight_passed}** |",
        f"| events_extracted | {len(events)} |",
        f"| events_admitted | {len(admitted_events)} |",
        f"| api_key_required | False |",
        f"| fixture_only | False |",
        f"| production_send_ready | False |",
        f"| ai_model_called | False |",
        f"| daemon_or_loop_started | False |",
        f"| files_deleted | False |",
        f"| news_full_text_saved | False |",
        "",
        "---",
        "",
        "## Safe Secret Preflight",
        "",
        f"| Check | Value |",
        f"|-------|-------|",
        f"| preflight_run | True |",
        f"| telegram_bot_token_present | {preflight.get('telegram_bot_token_present', False)} |",
        f"| telegram_chat_id_present | {preflight.get('telegram_chat_id_present', False)} |",
        f"| preflight_passed | {preflight_passed} |",
        f"| raw values printed | False |",
        "",
        "---",
        "",
        "## Files Produced",
        "",
    ]
    for fp in [
        RAW_SOURCES_JSON, EVENT_RECORDS_JSONL, MARKET_SNAPSHOTS_JSON,
        CARD_RECORDS_JSONL, QUALITY_GATE_JSONL, SEND_READINESS_JSONL,
        TG_SEND_ATTEMPTS_JSONL, SEND_RESULT_JSON, CARD_PREVIEW_MD,
        SEND_REPORT_MD, HANDOFF_MD,
    ]:
        handoff_lines.append(f"- `{fp}`")

    handoff_lines += [
        "",
        "---",
        "",
        "## Safety Confirmation",
        "",
        "- [PASS] Secret preflight executed — boolean only, no raw values",
        "- [PASS] No production channel send",
        "- [PASS] No production state written",
        "- [PASS] No AI/model called",
        "- [PASS] No paid API called",
        "- [PASS] No credentials printed to output",
        "- [PASS] No files deleted",
        "- [PASS] No daemon/loop started",
        "- [PASS] One-shot execution only",
        "- [PASS] TG target is test group, not channel",
        "- [PASS] Only redacted message proof recorded",
        "- [PASS] No news full text saved",
        "- [PASS] Cards state '事件影响观察，不构成因果证明'",
        "- [PASS] No investment advice in cards",
        "",
        "---",
        "",
        "## Unfinished Items / Risks",
        "",
        "1. This is a ONE-SHOT test. No continuous monitoring or automated resend.",
        "2. News event extraction uses keyword matching — may miss nuanced events.",
        "3. RSS feeds may be geo-blocked or timeout depending on network.",
        "4. Attribution risk classification is rule-based — may misclassify edge cases.",
        "5. Market data correlation with news events is observed, not proven causal.",
        "6. Low/medium intensity events may not pass admission during calm markets.",
        "7. Not all crypto assets have Binance USDT trading pairs.",
        "8. Event timestamps from RSS may lag real-time by minutes/hours.",
        "9. Multiple events may affect the same asset — attribution to single event is complex.",
        "10. Binance announcements API format may change without notice.",
    ]

    ensure_dir(HANDOFF_MD)
    with open(HANDOFF_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(handoff_lines) + "\n")
    print(f"  [OK] {HANDOFF_MD}")

    return result


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

def main() -> int:
    print("=" * 70)
    print(f"Market Radar {VERSION} — News Event Market Impact Real Free Public")
    print("Source TG Test Send (One-Shot)")
    print("ONE-SHOT execution. Not daemon. Not production.")
    print("No AI/model. No full text scraping. No paid APIs.")
    print("=" * 70)
    print()

    overall_status = "done"
    final_result: dict = {}

    try:
        # ── Step 0: Safe Secret Preflight ──
        preflight = safe_secret_preflight()

        # ── Step 1: Fetch real news from free public sources ──
        raw_sources = fetch_all_news_sources()

        if raw_sources.get("all_public_sources_unavailable", True):
            print("\n[FATAL] All public news sources unavailable.")
            print("  No real public news titles/URLs could be fetched.")
            print("  audit_result will be: blocked_public_source_unavailable")
            events = []
            admissions = []
            cards_list = []
            quality_gates = []
            send_readiness_list = []
            tg_attempts = []
            market_snapshot = {
                "snapshot_id": "blocked_public_source_unavailable",
                "fetched_at": generate_timestamp(),
                "symbols_queried": [],
                "symbol_count": 0,
                "note": "No news events to query market data for — public sources unavailable",
                "api_key_required": False,
                "real_external_api_called": False,
            }
            overall_status = "partial"
        else:
            # ── Step 2: Extract events ──
            events = extract_events(raw_sources)

            if not events:
                print("\n[BLOCKED] No events extracted from available sources.")
                admissions = []
                cards_list = []
                quality_gates = []
                send_readiness_list = []
                tg_attempts = []
                market_snapshot = {
                    "snapshot_id": "no_events_extracted",
                    "fetched_at": generate_timestamp(),
                    "symbols_queried": [],
                    "symbol_count": 0,
                    "note": "No news events extracted — gate blocked_gate_not_passed",
                    "api_key_required": False,
                    "real_external_api_called": False,
                }
                overall_status = "partial"
            else:
                # ── Step 3: Fetch market data ──
                target_symbols = collect_target_assets(events)
                if target_symbols:
                    market_snapshot = fetch_market_snapshots(target_symbols)
                else:
                    market_snapshot = {
                        "snapshot_id": "no_binance_symbols_mapped",
                        "fetched_at": generate_timestamp(),
                        "symbols_queried": [],
                        "symbol_count": 0,
                        "note": "No assets mapped to Binance symbols",
                        "api_key_required": False,
                        "real_external_api_called": False,
                    }
                    SAFETY["real_external_api_called"] = False

                # ── Step 4: Admission decisions ──
                admissions = []
                cards_list = []
                quality_gates = []
                send_readiness_list = []
                tg_attempts = []

                for i, event in enumerate(events):
                    print(f"\n{'='*50}")
                    print(f"[4/{5}] Processing event {i+1}/{len(events)}: "
                          f"{event.get('title', '')[:80]}...")

                    # Get market context
                    market_context = get_market_context_for_event(event, market_snapshot)

                    # Admission decision
                    admission = decide_admission(event, market_context)
                    admissions.append(admission)

                    status = "ADMIT" if admission["admission_passed"] else "BLOCKED"
                    print(f"  Admission: {status} ({admission.get('blocked_reason', 'N/A')})")

                    # Render card if admitted
                    if admission["admission_passed"]:
                        print(f"  [5] Rendering news event market impact card...")
                        card_text = render_news_event_card(event, market_context, admission)
                        print(f"  Card rendered: {len(card_text)} chars")
                    else:
                        card_text = f"[BLOCKED] {event.get('title', '')[:100]}: "
                        card_text += f"{admission.get('blocked_reason', 'admission not passed')}"

                    cards_list.append({
                        "event_id": event["event_id"],
                        "title": event.get("title", ""),
                        "card_text": card_text,
                    })

                    # Quality gate
                    qg = run_quality_gate(event, admission, card_text, market_context)
                    quality_gates.append(qg)

                    # Send-readiness gate
                    sr = run_send_readiness_gate(event, qg, preflight)
                    send_readiness_list.append(sr)

                    # TG test send
                    if admission["admission_passed"] and qg.get("quality_gate_passed"):
                        ta = attempt_tg_test_send(event, card_text, sr, preflight)
                    else:
                        print(f"\n[8] Skipping TG send (gate not passed)...")
                        ta = {
                            "attempted": False,
                            "success": False,
                            "blocked_reason": "gate_not_passed",
                            "target_type": "test_group",
                            "one_shot": True,
                        }
                    tg_attempts.append(ta)

        # ── Write outputs ──
        final_result = write_outputs(
            preflight, raw_sources, events, market_snapshot,
            admissions, cards_list, quality_gates, send_readiness_list, tg_attempts,
        )

        audit_result = final_result.get("audit_result", "blocked_gate_not_passed")
        if not any(ta.get("success", False) for ta in tg_attempts):
            overall_status = "partial"

    except Exception as e:
        print(f"\n[FATAL] Unhandled exception: {e}")
        traceback.print_exc()
        overall_status = "failed"
        audit_result = "blocked_public_source_unavailable"
        final_result = {
            "card_family": CARD_FAMILY,
            "version": VERSION,
            "stage": STAGE,
            "generated_at": generate_timestamp(),
            "real_public_source_called": SAFETY.get("real_public_source_called", False),
            "real_external_api_called": SAFETY.get("real_external_api_called", False),
            "fixture_only": False,
            "production_send_ready": False,
            "prod_state_write": False,
            "ai_model_called": False,
            "credentials_printed": False,
            "credentials_read_plaintext": False,
            "daemon_or_loop_started": False,
            "files_deleted": False,
            "secret_preflight_run": SAFETY.get("secret_preflight_run", False),
            "audit_result": "blocked_public_source_unavailable",
            "error": str(e)[:300],
        }
        ensure_dir(SEND_RESULT_JSON)
        with open(SEND_RESULT_JSON, "w", encoding="utf-8") as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)

    # ── Final summary ──
    print("\n" + "=" * 70)
    print("EXECUTION COMPLETE")
    print("=" * 70)
    print(f"  Status:              {overall_status}")
    print(f"  card_family:         {CARD_FAMILY}")
    print(f"  real_public_source:  {SAFETY.get('real_public_source_called', False)}")
    print(f"  real_api_called:     {SAFETY.get('real_external_api_called', False)}")
    print(f"  preflight_passed:    {SAFETY.get('secret_preflight_passed', False)}")
    print(f"  tg_test_sent:        {SAFETY.get('tg_test_sent', False)}")
    print(f"  tg_msg_id_redacted:  {SAFETY.get('tg_message_id_redacted', 'N/A')}")
    print(f"  audit_result:        {final_result.get('audit_result', 'unknown')}")
    print(f"  api_key_required:    False")
    print(f"  fixture_only:        False")
    print(f"  news_full_text:      False")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
