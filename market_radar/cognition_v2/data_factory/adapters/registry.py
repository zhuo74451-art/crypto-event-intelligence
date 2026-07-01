"""Concrete public-source acquisition adapters for the data factory.

C02: Real finite adapters for official public sources.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from market_radar.cognition_v2.data_factory.acquisition import AcquisitionAdapter
from market_radar.cognition_v2.data_factory.contracts import RawIntakeRecord


class HttpAdapter(AcquisitionAdapter):
    """Base HTTP adapter with rate limiting, retry and timeout."""

    def __init__(
        self,
        base_url: str,
        rate_limit_per_second: float = 5.0,
        request_timeout: int = 30,
        retry_limit: int = 3,
        parser_version: str = "1.0",
    ):
        self.base_url = base_url
        self._min_interval = 1.0 / max(rate_limit_per_second, 0.1)
        self._timeout = request_timeout
        self._retry_limit = retry_limit
        self._parser_version = parser_version
        self._last_request_time = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

    def _fetch_url(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> Tuple[int, bytes]:
        """Fetch a URL with rate limiting and retry. Returns (status, body)."""
        if headers is None:
            headers = {
                "User-Agent": "cognition-data-factory/1.0 (research; contact@example.com)",
                "Accept": "application/json, text/html, text/plain",
            }
        last_error = None
        for attempt in range(self._retry_limit + 1):
            self._rate_limit()
            try:
                req = Request(url, headers=headers)
                resp = urlopen(req, timeout=self._timeout)
                body = resp.read()
                self._last_request_time = time.time()
                return (resp.status, body)
            except Exception as e:
                last_error = e
                if attempt < self._retry_limit:
                    time.sleep(1.0 * (2 ** attempt))
        raise last_error  # type: ignore

    def _make_intake(
        self, source_id: str, url: str, body: str
    ) -> RawIntakeRecord:
        import hashlib
        return RawIntakeRecord(
            intake_id=hashlib.sha256(
                f"{source_id}:{url}:{time.time()}".encode()
            ).hexdigest()[:32],
            source_id=source_id,
            source_url=url,
            raw_body=body[:5000],
            retrieved_at=datetime.now(timezone.utc),
            parser_version=self._parser_version,
        )

    def fetch_page(
        self, source_id, start_time, end_time,
        page_size=50, page_token=None,
    ) -> Tuple[List[RawIntakeRecord], Optional[str]]:
        raise NotImplementedError


class SecEdgarAdapter(HttpAdapter):
    """SEC EDGAR adapter for regulatory filings."""

    def __init__(self):
        super().__init__(
            base_url="https://www.sec.gov/cgi-bin/browse-edgar",
            rate_limit_per_second=10.0, request_timeout=30,
            parser_version="sec-edgar-1.0",
        )

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        params = {
            "action": "getcurrent",
            "output": "atom",
            "count": str(page_size),
        }
        if page_token:
            params["start"] = page_token
        url = f"{self.base_url}?{urlencode(params)}"
        try:
            status, body = self._fetch_url(url)
            text = body.decode("utf-8", errors="replace")
            records = [self._make_intake(source_id, url, text)]
            next_token = str(int(page_token or 0) + page_size) if len(text) > 100 else None
            return records, next_token
        except Exception as e:
            return [], None


class FederalReserveAdapter(HttpAdapter):
    """Federal Reserve press releases and speeches."""

    def __init__(self):
        super().__init__(
            base_url="https://www.federalreserve.gov/api/",
            rate_limit_per_second=10.0,
            parser_version="fed-1.0",
        )

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        url = f"{self.base_url}pressreleases?from={start_time.strftime('%Y-%m-%d')}&to={end_time.strftime('%Y-%m-%d')}&size={page_size}"
        if page_token:
            url += f"&fromId={page_token}"
        try:
            status, body = self._fetch_url(url)
            text = body.decode("utf-8", errors="replace")
            records = [self._make_intake(source_id, url, text)]
            return records, None  # single page for pilot
        except Exception as e:
            return [], None


class BLSAdapter(HttpAdapter):
    """Bureau of Labor Statistics economic releases."""

    def __init__(self):
        super().__init__(
            base_url="https://www.bls.gov/news.release/",
            rate_limit_per_second=10.0,
            parser_version="bls-1.0",
        )

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        url = self.base_url
        try:
            status, body = self._fetch_url(url)
            text = body.decode("utf-8", errors="replace")
            records = [self._make_intake(source_id, url, text)]
            return records, None
        except Exception as e:
            return [], None


class GitHubAdvisoryAdapter(HttpAdapter):
    """GitHub Security Advisories — public API."""

    def __init__(self):
        super().__init__(
            base_url="https://api.github.com/advisories",
            rate_limit_per_second=5.0,
            parser_version="gh-advisory-1.0",
        )

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        params = {"per_page": str(page_size), "type": "reviewed", "direction": "desc"}
        if page_token:
            params["after"] = page_token
        url = f"{self.base_url}?{urlencode(params)}"
        try:
            status, body = self._fetch_url(url)
            text = body.decode("utf-8", errors="replace")
            records = [self._make_intake(source_id, url, text)]
            return records, None
        except Exception as e:
            return [], None


class NVDAdapter(HttpAdapter):
    """NVD — National Vulnerability Database."""

    def __init__(self):
        super().__init__(
            base_url="https://services.nvd.nist.gov/rest/json/cves/2.0",
            rate_limit_per_second=5.0,
            parser_version="nvd-cve-1.0",
        )

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        params = {
            "pubStartDate": start_time.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "pubEndDate": end_time.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "resultsPerPage": str(page_size),
        }
        if page_token:
            params["startIndex"] = page_token
        url = f"{self.base_url}?{urlencode(params)}"
        try:
            status, body = self._fetch_url(url)
            text = body.decode("utf-8", errors="replace")
            records = [self._make_intake(source_id, url, text)]
            return records, None
        except Exception as e:
            return [], None


class CISAAdapter(HttpAdapter):
    """CISA Cybersecurity Alerts."""

    def __init__(self):
        super().__init__(
            base_url="https://www.cisa.gov/news-events/cybersecurity-advisories",
            rate_limit_per_second=5.0,
            parser_version="cisa-1.0",
        )

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        url = self.base_url
        try:
            status, body = self._fetch_url(url)
            text = body.decode("utf-8", errors="replace")
            records = [self._make_intake(source_id, url, text)]
            return records, None
        except Exception as e:
            return [], None


class BinanceMarketAdapter(HttpAdapter):
    """Binance public market data — outcome prices (klines)."""

    def __init__(self):
        super().__init__(
            base_url="https://api.binance.com/api/v3/klines",
            rate_limit_per_second=20.0,
            parser_version="binance-klines-1.0",
        )

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=500, page_token=None):
        """Fetch 1h klines for BTCUSDT."""
        interval = "1h"
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        params = {
            "symbol": "BTCUSDT",
            "interval": interval,
            "startTime": str(start_ms),
            "endTime": str(end_ms),
            "limit": str(page_size),
        }
        url = f"{self.base_url}?{urlencode(params)}"
        try:
            status, body = self._fetch_url(url)
            text = body.decode("utf-8", errors="replace")
            records = [self._make_intake(source_id, url, text)]
            return records, None
        except Exception as e:
            return [], None


class CoinbaseMarketAdapter(HttpAdapter):
    """Coinbase public market data — fallback outcome prices."""

    def __init__(self):
        super().__init__(
            base_url="https://api.exchange.coinbase.com/products/BTC-USD/candles",
            rate_limit_per_second=10.0,
            parser_version="coinbase-candles-1.0",
        )

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=300, page_token=None):
        params = {
            "granularity": "3600",  # 1h
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        }
        url = f"{self.base_url}?{urlencode(params)}"
        try:
            status, body = self._fetch_url(url)
            text = body.decode("utf-8", errors="replace")
            records = [self._make_intake(source_id, url, text)]
            return records, None
        except Exception as e:
            return [], None


ADAPTER_REGISTRY: Dict[str, HttpAdapter] = {
    "sec-edgar": SecEdgarAdapter(),
    "cftc-enforcement": HttpAdapter(
        base_url="https://www.cftc.gov/cpenforcement",
        rate_limit_per_second=5.0,
        parser_version="cftc-1.0",
    ),
    "federal-reserve": FederalReserveAdapter(),
    "bls-economic-releases": BLSAdapter(),
    "github-security-advisories": GitHubAdvisoryAdapter(),
    "nvd-nist": NVDAdapter(),
    "cisa-alerts": CISAAdapter(),
    "binance-public": BinanceMarketAdapter(),
    "coinbase-public": CoinbaseMarketAdapter(),
}


def get_adapter(source_id: str) -> Optional[HttpAdapter]:
    return ADAPTER_REGISTRY.get(source_id)
