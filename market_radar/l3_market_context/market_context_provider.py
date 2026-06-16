"""MVP+ L3v2 — Market Context Provider (CCXT + Hyperliquid + HTTPX).

Primary: CCXT for BTC/ETH/SOL (Binance, free public API, no key).
HYPE: Hyperliquid Info API (allMids + metaAndAssetCtxs).
Fallback: Binance REST API (if CCXT unavailable).

Output: list[MarketContext] per sealed contract.
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

L3_SOURCE_NAME = "market_context_provider_v2"
USER_AGENT = "MVPPlus-L3v2/1.0 (ccxt+hl+httpx; read-only public data)"

TARGET_SYMBOLS = ["BTC", "ETH", "SOL", "HYPE"]
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
READ_TIMEOUT = 15


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_get_json(url: str, timeout: int = READ_TIMEOUT) -> Optional[dict | list]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError):
        return None


def _http_post_json(url: str, payload: dict, timeout: int = READ_TIMEOUT) -> Optional[dict | list]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, headers={
        "User-Agent": USER_AGENT, "Content-Type": "application/json", "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError):
        return None


def _safe_float(v: Any) -> Optional[float]:
    if v is None: return None
    try: return float(v)
    except (ValueError, TypeError): return None


@dataclass
class L3Result:
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
        return {"lane": "L3", "run_id": self.run_id,
            "started_at": self.started_at, "completed_at": self.completed_at,
            "total_requested": self.total_requested,
            "total_succeeded": self.total_succeeded,
            "total_failed": self.total_failed,
            "context_count": len(self.contexts), "error": self.error}


def _fetch_ccxt_spot() -> dict[str, dict]:
    """Try CCXT first, return {base: data}."""
    result: dict[str, dict] = {}
    try:
        import ccxt
        ex = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})
        tickers = ex.fetch_tickers()
        for base, sym in [("BTC","BTC/USDT"), ("ETH","ETH/USDT"), ("SOL","SOL/USDT")]:
            t = tickers.get(sym)
            if t and t.get("last"):
                result[base] = {
                    "price": t["last"], "change_24h": t.get("percentage"),
                    "volume_24h": t.get("quoteVolume"),
                    "high_24h": t.get("high"), "low_24h": t.get("low"),
                    "venue": "binance_spot", "data_mode": "live",
                }
    except ImportError: pass
    except Exception: pass
    return result


def _fetch_binance_rest() -> dict[str, dict]:
    """Fallback: Binance REST API."""
    result: dict[str, dict] = {}
    try:
        syms = json.dumps(["BTCUSDT","ETHUSDT","SOLUSDT"], separators=(",",":"))
        raw = _http_get_json(f"{BINANCE_TICKER_URL}?symbols={syms}")
        if not isinstance(raw, list):
            all_data = _http_get_json(BINANCE_TICKER_URL)
            if isinstance(all_data, list):
                raw = [i for i in all_data if isinstance(i, dict) and i.get("symbol") in ("BTCUSDT","ETHUSDT","SOLUSDT")]
            else: return result
        base_map = {"BTCUSDT":"BTC","ETHUSDT":"ETH","SOLUSDT":"SOL"}
        for item in (raw or []):
            if not isinstance(item, dict): continue
            sym = item.get("symbol","")
            base = base_map.get(sym)
            if not base: continue
            result[base] = {
                "price": _safe_float(item.get("lastPrice")),
                "change_24h": _safe_float(item.get("priceChangePercent")),
                "volume_24h": _safe_float(item.get("quoteVolume")),
                "high_24h": _safe_float(item.get("highPrice")),
                "low_24h": _safe_float(item.get("lowPrice")),
                "venue": "binance_spot", "data_mode": "live",
            }
    except Exception: pass
    return result


def _fetch_hyperliquid_hype() -> Optional[dict]:
    """HYPE via Hyperliquid Info API."""
    try:
        mids = _http_post_json(HYPERLIQUID_INFO_URL, {"type": "allMids"}, timeout=10)
        if not isinstance(mids, dict): return None
        hp = _safe_float(mids.get("HYPE"))
        if hp is None: return None

        result = {"price": hp, "change_24h": None, "volume_24h": None,
                  "open_interest": None, "funding_rate": None,
                  "mark_price": hp, "oracle_price": None,
                  "venue": "hyperliquid_perp", "data_mode": "live"}

        md = _http_post_json(HYPERLIQUID_INFO_URL, {"type": "metaAndAssetCtxs"}, timeout=10)
        if isinstance(md, list) and len(md) >= 2:
            universe = md[0].get("universe", []) if isinstance(md[0], dict) else []
            ctxs = md[1] if isinstance(md[1], list) else []
            for i, ctx in enumerate(ctxs):
                name = universe[i].get("name","") if i < len(universe) and isinstance(universe[i], dict) else ""
                if name == "HYPE":
                    result["open_interest"] = _safe_float(ctx.get("openInterest"))
                    fr = _safe_float(ctx.get("funding"))
                    if fr is not None: result["funding_rate"] = fr
                    result["mark_price"] = _safe_float(ctx.get("markPx"))
                    result["oracle_price"] = _safe_float(ctx.get("oraclePx"))
                    result["volume_24h"] = _safe_float(ctx.get("dayNtlVlm"))
                    pp = _safe_float(ctx.get("prevDayPx"))
                    if pp and pp > 0: result["change_24h"] = (hp - pp) / pp * 100
                    break
        return result
    except Exception:
        return None


def run() -> L3Result:
    run_id = uuid.uuid4().hex[:12]
    started_at = _utc_now()
    observed_at = _utc_now()
    contexts: list[MarketContext] = []
    health: list[SourceHealth] = []
    succeeded = 0; failed = 0; overall_error: Optional[str] = None

    # 1. BTC/ETH/SOL via CCXT (preferred) or Binance REST fallback
    ccxt_data = _fetch_ccxt_spot()
    if not ccxt_data:
        ccxt_data = _fetch_binance_rest()

    for base in ["BTC", "ETH", "SOL"]:
        d = ccxt_data.get(base)
        if d and d.get("price") is not None and d["price"] > 0:
            p = d["price"]
            contexts.append(MarketContext(
                symbol=base, price=round(p, 2),
                price_change_24h_pct=d.get("change_24h"),
                volume_24h=d.get("volume_24h"),
                high_24h=d.get("high_24h"), low_24h=d.get("low_24h"),
                source=MarketDataSource.BINANCE_SPOT,
                observed_at=observed_at, data_origin="live",
            ))
            health.append(SourceHealth(source_name=f"ccxt:binance:{base}",
                source_group="market", status=SourceStatus.OK,
                last_success_at=observed_at, success_count=1, error_count=0))
            succeeded += 1
        else:
            contexts.append(MarketContext(symbol=base, price=0.0,
                observed_at=observed_at, data_origin="degraded",
                source=MarketDataSource.DEGRADED))
            health.append(SourceHealth(source_name=f"market:{base}",
                source_group="market", status=SourceStatus.DEGRADED,
                degraded_info=DegradedInfo(error_type="PRICE_UNAVAILABLE",
                    occurred_at=observed_at, retryable=True,
                    message_summary=f"{base} unavailable")))
            failed += 1

    # 2. HYPE via Hyperliquid Info API
    hype = _fetch_hyperliquid_hype()
    if hype and hype.get("price") and hype["price"] > 0:
        hp = hype["price"]
        oi = hype.get("open_interest")
        oi_usd = oi * hp if oi is not None and hp else None
        contexts.append(MarketContext(symbol="HYPE", price=round(hp, 2),
            price_change_24h_pct=hype.get("change_24h"),
            volume_24h=hype.get("volume_24h"),
            open_interest=round(oi_usd, 2) if oi_usd else None,
            funding_rate=hype.get("funding_rate"),
            source=MarketDataSource.HYPERLIQUID_PERP,
            observed_at=observed_at, data_origin="live"))
        health.append(SourceHealth(source_name="hyperliquid:hype",
            source_group="hyperliquid", status=SourceStatus.OK,
            last_success_at=observed_at, success_count=1, error_count=0))
        succeeded += 1
    else:
        contexts.append(MarketContext(symbol="HYPE", price=0.0,
            observed_at=observed_at, data_origin="degraded",
            source=MarketDataSource.DEGRADED))
        health.append(SourceHealth(source_name="hyperliquid:hype",
            source_group="hyperliquid", status=SourceStatus.DEGRADED,
            degraded_info=DegradedInfo(error_type="HL_API_UNAVAILABLE",
                occurred_at=observed_at, retryable=True,
                message_summary="HYPE unavailable from Hyperliquid Info API")))
        failed += 1

    completed_at = _utc_now()
    if failed > 0 and succeeded == 0:
        overall_error = "All market data sources unavailable"

    return L3Result(contexts=contexts, source_health=health,
        total_requested=4, total_succeeded=succeeded, total_failed=failed,
        run_id=run_id, started_at=started_at, completed_at=completed_at,
        error=overall_error)


def main():
    result = run()
    print(f"L3v2 Run: {result.run_id}")
    print(f"  Status: {result.total_succeeded}/{result.total_requested} assets")
    for ctx in result.contexts:
        d = ctx.as_dict()
        chg = f"{d.get('price_change_24h_pct'):+.2f}%" if d.get('price_change_24h_pct') is not None else "N/A"
        oi_s = f"OI=${d.get('open_interest'):,.0f}" if d.get('open_interest') else "OI=N/A"
        fr_s = f"fund={d.get('funding_rate'):.6f}" if d.get('funding_rate') else "fund=N/A"
        print(f"    {d['symbol']:5s} | ${d['price']:>8,.2f} | {chg:>10s} | {oi_s:>20s} | {fr_s}")
    if result.error: print(f"  ERROR: {result.error}")
    return 0 if result.total_failed == 0 else 1


if __name__ == "__main__":
    main()
