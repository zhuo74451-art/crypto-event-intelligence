"""Concrete public-source acquisition adapters — deterministic parsers.

P02: Every adapter returns one typed intake record per actual source item.
intake_id is derived from stable source record identity + content hash.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from market_radar.cognition_v2.data_factory.acquisition import AcquisitionAdapter
from market_radar.cognition_v2.data_factory.contracts import RawIntakeRecord


def _deterministic_intake_id(source_id: str, record_key: str, content_hash: str) -> str:
    """Deterministic intake ID from stable identity — never uses current time."""
    return hashlib.sha256(
        f"{source_id}:{record_key}:{content_hash}".encode()
    ).hexdigest()[:32]


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


class HttpAdapter(AcquisitionAdapter):
    """Base HTTP adapter with rate limiting, retry and timeout."""

    def __init__(
        self,
        base_url: str,
        rate_limit_per_second: float = 5.0,
        request_timeout: int = 30,
        retry_limit: int = 3,
        parser_version: str = "1.0",
        adapter_version: str = "1.0",
    ):
        self.base_url = base_url
        self._min_interval = 1.0 / max(rate_limit_per_second, 0.1)
        self._timeout = request_timeout
        self._retry_limit = retry_limit
        self._parser_version = parser_version
        self._adapter_version = adapter_version
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
        self, source_id: str, url: str, body: str, record_key: str
    ) -> RawIntakeRecord:
        c_hash = _content_hash(body[:5000])
        return RawIntakeRecord(
            intake_id=_deterministic_intake_id(source_id, record_key, c_hash),
            source_id=source_id,
            source_url=url,
            raw_body=body[:5000],
            retrieved_at=datetime.now(timezone.utc),
            parser_version=self._parser_version,
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        """Extract individual intake records from response body. Override in subclasses."""
        raise NotImplementedError

    def fetch_page(
        self, source_id, start_time, end_time,
        page_size=50, page_token=None,
    ) -> Tuple[List[RawIntakeRecord], Optional[str]]:
        raise NotImplementedError


class SecEdgarAdapter(HttpAdapter):
    """SEC EDGAR — parse individual filing entries from Atom feed."""

    def __init__(self):
        super().__init__(
            base_url="https://www.sec.gov/cgi-bin/browse-edgar",
            rate_limit_per_second=10.0, request_timeout=30,
            parser_version="sec-edgar-1.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        # Parse <entry> elements from Atom feed
        entries = re.findall(r'<entry>(.*?)</entry>', text, re.DOTALL)
        for entry in entries:
            title_m = re.search(r'<title[^>]*>(.*?)</title>', entry, re.DOTALL)
            link_m = re.search(r'<link[^>]*href="([^"]+)"', entry)
            date_m = re.search(r'<updated>(.*?)</updated>', entry)
            title = title_m.group(1).strip() if title_m else "untitled"
            link = link_m.group(1) if link_m else self.base_url
            date = date_m.group(1) if date_m else ""
            body_text = f"Title: {title}\nDate: {date}\nLink: {link}"
            records.append(self._make_intake(
                source_id, link, body_text, f"sec-{_content_hash(title)[:16]}"
            ))
        return records

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        params = {
            "action": "getcurrent", "output": "atom",
            "count": str(page_size),
        }
        if page_token:
            params["start"] = page_token
        url = f"{self.base_url}?{urlencode(params)}"
        status, body = self._fetch_url(url)
        records = self._extract_items(body, source_id)
        next_token = str(int(page_token or 0) + page_size) if len(records) == page_size else None
        return records, next_token


class FederalReserveAdapter(HttpAdapter):
    """Federal Reserve — parse press release items."""

    def __init__(self):
        super().__init__(
            base_url="https://www.federalreserve.gov/api",
            rate_limit_per_second=10.0,
            parser_version="fed-1.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
            items = data.get("items", data.get("results", []))
        except (json.JSONDecodeError, TypeError):
            items = []
        for item in items:
            title = item.get("title", item.get("name", "untitled"))
            link = item.get("url", item.get("link", self.base_url))
            date = item.get("date", item.get("published", ""))
            body_text = f"Title: {title}\nDate: {date}"
            records.append(self._make_intake(
                source_id, link, body_text, f"fed-{_content_hash(title)[:16]}"
            ))
        return records

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        url = (f"{self.base_url}/pressreleases?"
               f"from={start_time.strftime('%Y-%m-%d')}&"
               f"to={end_time.strftime('%Y-%m-%d')}&size={page_size}")
        status, body = self._fetch_url(url)
        return self._extract_items(body, source_id), None


class BLSAdapter(HttpAdapter):
    """BLS — parse economic release items from HTML."""

    def __init__(self):
        super().__init__(
            base_url="https://www.bls.gov/news.release/",
            rate_limit_per_second=10.0,
            parser_version="bls-1.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        links = re.findall(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', text, re.DOTALL)
        for href, label in links:
            label = re.sub(r'<[^>]+>', '', label).strip()
            if not label or len(label) < 5:
                continue
            full_url = href if href.startswith("http") else f"{self.base_url}{href}"
            records.append(self._make_intake(
                source_id, full_url, f"Release: {label}", f"bls-{_content_hash(label)[:16]}"
            ))
        return records

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        status, body = self._fetch_url(self.base_url)
        return self._extract_items(body, source_id), None


class GitHubAdvisoryAdapter(HttpAdapter):
    """GitHub Security Advisories — parse individual advisories."""

    def __init__(self):
        super().__init__(
            base_url="https://api.github.com/advisories",
            rate_limit_per_second=5.0,
            parser_version="gh-advisory-1.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        try:
            advisories = json.loads(text)
        except json.JSONDecodeError:
            return records
        if not isinstance(advisories, list):
            return records
        for adv in advisories:
            gh_id = adv.get("ghsa_id", adv.get("id", "unknown"))
            summary = adv.get("summary", adv.get("description", ""))
            html_url = adv.get("html_url", adv.get("url", ""))
            published = adv.get("published_at", "")
            body_text = f"GHSA: {gh_id}\nSummary: {summary}\nPublished: {published}"
            records.append(self._make_intake(
                source_id, html_url, body_text, gh_id
            ))
        return records

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        url = f"{self.base_url}?per_page={page_size}&type=reviewed&direction=desc"
        if page_token:
            url += f"&after={page_token}"
        status, body = self._fetch_url(url)
        return self._extract_items(body, source_id), None


class NVDAdapter(HttpAdapter):
    """NVD — parse individual CVE items."""

    def __init__(self):
        super().__init__(
            base_url="https://services.nvd.nist.gov/rest/json/cves/2.0",
            rate_limit_per_second=5.0,
            parser_version="nvd-cve-1.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return records
        vulns = data.get("vulnerabilities", [])
        for vuln in vulns:
            cve = vuln.get("cve", {})
            cve_id = cve.get("id", "unknown")
            desc = ""
            for d in cve.get("descriptions", []):
                if d.get("lang") == "en":
                    desc = d.get("value", "")
                    break
            body_text = f"CVE: {cve_id}\nDescription: {desc[:500]}"
            records.append(self._make_intake(
                source_id, f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                body_text, cve_id
            ))
        return records

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
        status, body = self._fetch_url(url)
        return self._extract_items(body, source_id), None


class CISAAdapter(HttpAdapter):
    """CISA — parse individual advisory entries."""

    def __init__(self):
        super().__init__(
            base_url="https://www.cisa.gov/news-events/cybersecurity-advisories",
            rate_limit_per_second=5.0,
            parser_version="cisa-1.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        items = re.findall(
            r'<article[^>]*>.*?<h3[^>]*><a\s+href="([^"]+)"[^>]*>(.*?)</a>.*?</article>',
            text, re.DOTALL
        )
        for href, title in items:
            title = re.sub(r'<[^>]+>', '', title).strip()
            full_url = href if href.startswith("http") else f"https://www.cisa.gov{href}"
            records.append(self._make_intake(
                source_id, full_url, f"CISA Advisory: {title}",
                f"cisa-{_content_hash(title)[:16]}"
            ))
        return records

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        status, body = self._fetch_url(self.base_url)
        return self._extract_items(body, source_id), None


class BinanceMarketAdapter(HttpAdapter):
    """Binance klines — OHLCV outcome data, individual bars."""

    def __init__(self):
        super().__init__(
            base_url="https://api.binance.com/api/v3/klines",
            rate_limit_per_second=20.0,
            parser_version="binance-klines-1.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        try:
            klines = json.loads(text)
        except json.JSONDecodeError:
            return records
        for k in klines:
            ts = int(k[0])
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            bar_key = f"binance-BTCUSDT-{ts // 3600000}"
            body_text = json.dumps({
                "open": k[1], "high": k[2], "low": k[3],
                "close": k[4], "volume": k[5], "time": dt.isoformat(),
            }, sort_keys=True)
            records.append(self._make_intake(
                source_id, f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={ts}",
                body_text, bar_key
            ))
        return records

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=500, page_token=None):
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        params = {
            "symbol": "BTCUSDT", "interval": "1h",
            "startTime": str(start_ms), "endTime": str(end_ms),
            "limit": str(page_size),
        }
        url = f"{self.base_url}?{urlencode(params)}"
        status, body = self._fetch_url(url)
        return self._extract_items(body, source_id), None


class CoinbaseMarketAdapter(HttpAdapter):
    """Coinbase candles — fallback OHLCV outcome data."""

    def __init__(self):
        super().__init__(
            base_url="https://api.exchange.coinbase.com/products/BTC-USD/candles",
            rate_limit_per_second=10.0,
            parser_version="coinbase-candles-1.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        try:
            candles = json.loads(text)
        except json.JSONDecodeError:
            return records
        for c in candles:
            ts = int(c[0])
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            bar_key = f"coinbase-BTCUSD-{ts // 3600}"
            body_text = json.dumps({
                "low": c[1], "high": c[2], "open": c[3],
                "close": c[4], "volume": c[5], "time": dt.isoformat(),
            }, sort_keys=True)
            records.append(self._make_intake(
                source_id, f"https://api.exchange.coinbase.com/products/BTC-USD/candles?start={dt.isoformat()}",
                body_text, bar_key
            ))
        return records

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=300, page_token=None):
        params = {
            "granularity": "3600",
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        }
        url = f"{self.base_url}?{urlencode(params)}"
        status, body = self._fetch_url(url)
        return self._extract_items(body, source_id), None


ADAPTER_REGISTRY: Dict[str, HttpAdapter] = {
    "sec-edgar": SecEdgarAdapter(),
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
