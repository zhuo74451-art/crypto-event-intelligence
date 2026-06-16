"""MVP+ Lane 3 — Market Context Provider.

Fetches spot market data for BTC, ETH, SOL, HYPE from Binance public API.
No API key required.

Output: list[MarketContext] per sealed contract.

Design:
  - One-shot: single fetch, no daemon/cron
  - Free public APIs only (Binance REST, no auth)
  - Per-symbol graceful degradation
  - HYPE may not be on Binance — gracefully fails with degraded status
  - No secret/credential handling
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from market_radar.shared.contracts import (
    MarketContext,
    MarketDataSource,
    SourceHealth,
    SourceStatus,
    DegradedInfo,
)

# ── Constants ─────────────────────────────────────────────────────────────────

BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"
USER_AGENT = "MVPPlus-L3-MarketContext/1.0 (read-only; public data)"
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 15
VERSION = "mvp+v1.0-l3"

# Primary symbols to track
TARGET_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_get_json(url: str, timeout: int = 15) -> Optional[dict | list]:
    """Simple HTTP GET → JSON. Uses urllib (no external deps)."""
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
        return json.loads(data)
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError):
        return None


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


@dataclass
class L3Result:
    """Aggregated result from a single L3 run."""
    contexts: list[MarketContext] = field(default_factory=list)
    source_health: list[SourceHealth] = field(default_factory=list)
    total_requested: int = 0
    total_succeeded: int = 0
    total_failed: int = 0
    run_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "lane": "L3",
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_requested": self.total_requested,
            "total_succeeded": self.total_succeeded,
            "total_failed": self.total_failed,
            "context_count": len(self.contexts),
            "error": self.error,
        }


def run() -> L3Result:
    """Fetch market context for all tracked symbols from Binance public API.

    Returns:
        L3Result with MarketContext per symbol and per-symbol SourceHealth.
    """
    run_id = uuid.uuid4().hex[:12]
    started_at = _utc_now()

    contexts: list[MarketContext] = []
    health: list[SourceHealth] = []
    succeeded = 0
    failed = 0
    overall_error: Optional[str] = None

    observed_at = _utc_now()

    try:
        raw_data = _http_get_json(BINANCE_TICKER_URL + "?symbols=" + json.dumps(TARGET_SYMBOLS, separators=(",", ":")))

        if raw_data is None or not isinstance(raw_data, list):
            # Fallback: fetch all tickers and filter
            all_data = _http_get_json(BINANCE_TICKER_URL)
            if all_data is None or not isinstance(all_data, list):
                overall_error = "Binance API unavailable"
                # Return degraded contexts for all symbols
                for sym in TARGET_SYMBOLS:
                    base = sym.replace("USDT", "")
                    contexts.append(MarketContext(
                        symbol=base,
                        price=0.0,
                        observed_at=observed_at,
                        data_origin="degraded",
                        source=MarketDataSource.DEGRADED,
                    ))
                    health.append(SourceHealth(
                        source_name=f"binance:{sym}",
                        source_group="market",
                        status=SourceStatus.FAILED,
                        last_error_at=observed_at,
                        error_count=1,
                        degraded_info=DegradedInfo(
                            error_type="HTTP_FAILURE",
                            occurred_at=observed_at,
                            retryable=True,
                            message_summary="Binance 24hr ticker API returned no data",
                        ),
                    ))
                    failed += 1

                completed_at = _utc_now()
                return L3Result(
                    contexts=contexts, source_health=health,
                    total_requested=len(TARGET_SYMBOLS),
                    total_succeeded=0, total_failed=len(TARGET_SYMBOLS),
                    run_id=run_id, started_at=started_at,
                    completed_at=completed_at, error=overall_error,
                )

            # Filter to our targets
            raw_list = [item for item in all_data if isinstance(item, dict) and item.get("symbol") in TARGET_SYMBOLS]
        else:
            raw_list = raw_data

        # Build a symbol → data map
        data_map: dict[str, dict] = {}
        for item in raw_list:
            if isinstance(item, dict):
                sym = item.get("symbol", "")
                data_map[sym] = item

        for sym in TARGET_SYMBOLS:
            base = sym.replace("USDT", "")
            item = data_map.get(sym)

            if item is None:
                # Symbol not found (likely HYPE not on Binance)
                contexts.append(MarketContext(
                    symbol=base,
                    price=0.0,
                    observed_at=observed_at,
                    data_origin="degraded",
                    source=MarketDataSource.DEGRADED,
                ))
                health.append(SourceHealth(
                    source_name=f"binance:{sym}",
                    source_group="market",
                    status=SourceStatus.DEGRADED,
                    last_error_at=observed_at,
                    error_count=1,
                    degraded_info=DegradedInfo(
                        error_type="SYMBOL_NOT_FOUND",
                        occurred_at=observed_at,
                        retryable=True,
                        message_summary=f"{sym} not found on Binance (may not be listed)",
                    ),
                ))
                failed += 1
                continue

            # Parse data
            ctx = MarketContext(
                symbol=base,
                price=_safe_float(item.get("lastPrice")) or 0.0,
                price_change_24h_pct=_safe_float(item.get("priceChangePercent")),
                volume_24h=_safe_float(item.get("quoteVolume")),
                high_24h=_safe_float(item.get("highPrice")),
                low_24h=_safe_float(item.get("lowPrice")),
                source=MarketDataSource.BINANCE_SPOT,
                observed_at=observed_at,
                data_origin="live",
            )
            contexts.append(ctx)
            health.append(SourceHealth(
                source_name=f"binance:{sym}",
                source_group="market",
                status=SourceStatus.OK,
                last_success_at=observed_at,
                success_count=1,
                error_count=0,
                latency_ms=0.0,
            ))
            succeeded += 1

    except Exception as e:
        overall_error = f"Unexpected error in L3: {type(e).__name__}: {e}"
        for sym in TARGET_SYMBOLS:
            base = sym.replace("USDT", "")
            contexts.append(MarketContext(
                symbol=base, price=0.0, observed_at=observed_at,
                data_origin="degraded", source=MarketDataSource.DEGRADED,
            ))
            health.append(SourceHealth(
                source_name=f"binance:{sym}", source_group="market",
                status=SourceStatus.FAILED,
                last_error_at=observed_at, error_count=1,
                degraded_info=DegradedInfo(
                    error_type="UNEXPECTED_ERROR",
                    occurred_at=observed_at, retryable=True,
                    message_summary=f"L3 error: {type(e).__name__}",
                ),
            ))
            failed += 1

    completed_at = _utc_now()
    return L3Result(
        contexts=contexts, source_health=health,
        total_requested=len(TARGET_SYMBOLS),
        total_succeeded=succeeded, total_failed=failed,
        run_id=run_id, started_at=started_at,
        completed_at=completed_at, error=overall_error,
    )


def main():
    """CLI entry: run L3 once and print summary."""
    result = run()
    print(f"L3 Run: {result.run_id}")
    print(f"  Status: {result.total_succeeded}/{result.total_requested} symbols succeeded")
    for ctx in result.contexts:
        d = ctx.as_dict()
        print(f"    {d['symbol']:5s} | ${d['price']:>8,.2f} | chg={d.get('price_change_24h_pct') or 'N/A':>8s} | "
              f"vol={d.get('volume_24h') or 'N/A'}")
    if result.error:
        print(f"  ERROR: {result.error}")
    return 0 if result.total_failed == 0 else 1


if __name__ == "__main__":
    main()
