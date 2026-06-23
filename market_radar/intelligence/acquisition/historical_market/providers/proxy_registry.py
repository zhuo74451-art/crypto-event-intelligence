"""Proxy registry — declares instrument proxy mappings.

When exact market data is not available, proxy instruments are used.
All proxies must be explicitly declared and never masked as exact.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Proxy instrument definitions
# ---------------------------------------------------------------------------
# Format: proxy_instrument_id -> {
#     "proxy_for": original_target,
#     "canonical_name": human-readable,
#     "reason": why proxy is used,
#     "quality": data quality grade,
# }

PROXY_REGISTRY: dict[str, dict[str, str]] = {
    "fred_vix": {
        "proxy_for": "cboe_vix",
        "canonical_name": "CBOE Volatility Index (VIX) via FRED",
        "reason": "FRED's VIXCLS is the official CBOE VIX closing value",
        "quality": "exact_public_api_retrieval",
        "notes": "VIX closing values, not intraday. Use for daily event analysis only.",
    },
}

# Cross-asset instruments that are exact (not proxy)
EXACT_INSTRUMENTS: dict[str, dict[str, str]] = {
    "fred_us10y_yield": {
        "canonical_name": "US 10-Year Treasury Yield",
        "source": "FRED DGS10",
        "notes": "Daily closing yield from FRED. Exact public dataset.",
    },
    "fred_us2y_yield": {
        "canonical_name": "US 2-Year Treasury Yield",
        "source": "FRED DGS2",
        "notes": "Daily closing yield from FRED. Exact public dataset.",
    },
    "fred_us30y_yield": {
        "canonical_name": "US 30-Year Treasury Yield",
        "source": "FRED DGS30",
        "notes": "Daily closing yield from FRED. Exact public dataset.",
    },
    "yahoo_sp500_index": {
        "canonical_name": "S&P 500 Index",
        "source": "Yahoo Finance ^GSPC",
        "notes": "Daily OHLC from Yahoo Finance.",
    },
    "yahoo_nasdaq_composite": {
        "canonical_name": "NASDAQ Composite Index",
        "source": "Yahoo Finance ^IXIC",
        "notes": "Daily OHLC from Yahoo Finance.",
    },
    "yahoo_gold_futures": {
        "canonical_name": "Gold Futures",
        "source": "Yahoo Finance GC=F",
        "notes": "Daily OHLC. Proxy for spot gold.",
        "proxy_for": "spot_gold",
    },
    "yahoo_us_dollar_index": {
        "canonical_name": "US Dollar Index (DXY)",
        "source": "Yahoo Finance DX-Y.NYB",
        "notes": "Daily OHLC. ICE US Dollar Index.",
    },
    "yahoo_silver_futures": {
        "canonical_name": "Silver Futures",
        "source": "Yahoo Finance SI=F",
        "notes": "Daily OHLC. Proxy for spot silver.",
        "proxy_for": "spot_silver",
    },
    "yahoo_wti_crude": {
        "canonical_name": "WTI Crude Oil Futures",
        "source": "Yahoo Finance CL=F",
        "notes": "Daily OHLC.",
    },
}


def get_proxy_info(instrument_id: str) -> dict[str, str]:
    """Return proxy info for an instrument, or empty dict if exact."""
    return PROXY_REGISTRY.get(instrument_id, {})


def is_proxy(instrument_id: str) -> bool:
    """Check if an instrument is a proxy."""
    return instrument_id in PROXY_REGISTRY


def get_instrument_metadata(instrument_id: str) -> dict[str, str]:
    """Get full metadata for a registered instrument."""
    result = EXACT_INSTRUMENTS.get(instrument_id, {})
    proxy_info = PROXY_REGISTRY.get(instrument_id, {})
    return {**result, **proxy_info}


def get_all_registered_instruments() -> list[dict[str, Any]]:
    """Return all registered instruments with metadata."""
    items = []
    for inst_id, meta in EXACT_INSTRUMENTS.items():
        items.append({"instrument_id": inst_id, **meta, "exact_or_proxy": "exact"})
    for inst_id, meta in PROXY_REGISTRY.items():
        items.append({"instrument_id": inst_id, **meta, "exact_or_proxy": "proxy"})
    return items
