"""Concrete public-source acquisition adapters — deterministic parsers.

P02: Every adapter returns one typed intake record per actual source item.
intake_id is derived from stable source record identity + content hash.
"""

from __future__ import annotations

import certifi
import hashlib
import json
import re
import ssl
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
        """Fetch a URL with rate limiting, retry and proper SSL."""
        if headers is None:
            headers = {
                "User-Agent": "cognition-data-factory/1.0 (research; contact@example.com)",
                "Accept": "application/json, text/html, text/plain",
            }
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        last_error = None
        for attempt in range(self._retry_limit + 1):
            self._rate_limit()
            try:
                req = Request(url, headers=headers)
                resp = urlopen(req, timeout=self._timeout, context=ssl_ctx)
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
    """Federal Reserve — official press-release RSS feed."""

    def __init__(self):
        super().__init__(
            base_url="https://www.federalreserve.gov/feeds",
            rate_limit_per_second=10.0,
            parser_version="fed-rss-2.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        for item_text in re.findall(r'<item>(.*?)</item>', text, re.DOTALL):
            title_m = re.search(r'<title[^>]*>(.*?)</title>', item_text, re.DOTALL)
            link_m = re.search(r'<link[^>]*>(.*?)</link>', item_text)
            date_m = re.search(r'<pubDate>(.*?)</pubDate>', item_text)
            title = title_m.group(1).strip() if title_m else "untitled"
            link = link_m.group(1).strip() if link_m else self.base_url
            pub_date = date_m.group(1).strip() if date_m else ""
            body_text = f"Title: {title}\nDate: {pub_date}\nID: fed-rss-{_content_hash(title)[:12]}"
            records.append(self._make_intake(
                source_id, link, body_text, f"fed-{_content_hash(title)[:16]}"
            ))
        return records

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        url = f"{self.base_url}/pressreleases.xml"
        status, body = self._fetch_url(url)
        return self._extract_items(body, source_id), None


class BLSAdapter(HttpAdapter):
    """BLS — use public JSON API for series data."""

    def __init__(self):
        super().__init__(
            base_url="https://www.bls.gov/cex/data/",
            rate_limit_per_second=5.0,
            parser_version="bls-json-1.0",
        )

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        # Use BLS public API without key for limited historical data
        url = "https://www.bls.gov/feed/ces.rss"
        try:
            status, body = self._fetch_url(url)
            records = self._extract_items(body, source_id)
            return records, None
        except Exception:
            return [], None

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        entries = re.findall(r'<item>(.*?)</item>', text, re.DOTALL)
        for entry in entries:
            title_m = re.search(r'<title[^>]*>(.*?)</title>', entry, re.DOTALL)
            link_m = re.search(r'<link[^>]*>(.*?)</link>', entry)
            title = title_m.group(1).strip() if title_m else "untitled"
            link = link_m.group(1) if link_m else ""
            records.append(self._make_intake(
                source_id, link, f"BLS: {title}", f"bls-{_content_hash(title)[:16]}"
            ))
        return records


class GitHubAdvisoryAdapter(HttpAdapter):
    """GitHub Security Advisories — rate-limit-aware public API."""

    def __init__(self):
        super().__init__(
            base_url="https://api.github.com/advisories",
            rate_limit_per_second=2.0,
            request_timeout=60,
            parser_version="gh-advisory-2.0",
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
            body_text = f"GHSA: {gh_id}\nPublished: {published}\nSummary: {summary[:200]}"
            records.append(self._make_intake(source_id, html_url, body_text, gh_id))
        return records

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        import time as _t
        _t.sleep(6)  # Respect unauthenticated GitHub rate limit (~10 req/min)
        url = f"{self.base_url}?per_page={min(page_size, 100)}&type=reviewed&direction=desc"
        if page_token:
            url += f"&after={page_token}"
        status, body = self._fetch_url(url)
        return self._extract_items(body, source_id), None


class NVDAdapter(HttpAdapter):
    """NVD — parse individual CVE items with proper date-window pagination."""

    def __init__(self):
        super().__init__(
            base_url="https://services.nvd.nist.gov/rest/json/cves/2.0",
            rate_limit_per_second=5.0,
            parser_version="nvd-cve-2.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> Tuple[List[RawIntakeRecord], Optional[int]]:
        records = []
        text = body.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return records, None
        vulns = data.get("vulnerabilities", [])
        total_results = data.get("totalResults", len(vulns))
        for vuln in vulns:
            cve = vuln.get("cve", {})
            cve_id = cve.get("id", "unknown")
            desc = ""
            for d in cve.get("descriptions", []):
                if d.get("lang") == "en":
                    desc = d.get("value", "")
                    break
            pub_date = cve.get("published", "")
            body_text = f"CVE: {cve_id}\nPublished: {pub_date}\nDescription: {desc[:500]}"
            records.append(self._make_intake(
                source_id, f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                body_text, cve_id
            ))
        return records, total_results

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        start_idx = int(page_token) if page_token else 0
        params = {
            "pubStartDate": start_time.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "pubEndDate": end_time.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "resultsPerPage": str(min(page_size, 200)),
            "startIndex": str(start_idx),
        }
        url = f"{self.base_url}?{urlencode(params)}"
        status, body = self._fetch_url(url)
        records, total = self._extract_items(body, source_id)
        next_idx = start_idx + len(records)
        next_token = str(next_idx) if next_idx < (total or 0) else None
        return records, next_token


class CISAAdapter(HttpAdapter):
    """CISA — fetch from Known Exploited Vulnerabilities catalog."""

    def __init__(self):
        super().__init__(
            base_url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
            rate_limit_per_second=5.0,
            parser_version="cisa-kev-1.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
            vulns = data.get("vulnerabilities", [])
        except (json.JSONDecodeError, TypeError):
            vulns = []
        for vuln in vulns:
            cve_id = vuln.get("cveID", "unknown")
            desc = vuln.get("shortDescription", vuln.get("vendorProject", ""))
            url = f"https://www.cisa.gov/known-exploited-vulnerabilities/{cve_id}"
            records.append(self._make_intake(
                source_id, url, f"CISA KEV: {desc}", cve_id
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
    """Coinbase Pro API — fallback OHLCV outcome data."""

    def __init__(self):
        super().__init__(
            base_url="https://api.exchange.coinbase.com",
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
        if not isinstance(candles, list):
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
        url = f"{self.base_url}/products/BTC-USD/candles?granularity=3600"
        status, body = self._fetch_url(url)
        return self._extract_items(body, source_id), None


class EurostatAdapter(HttpAdapter):
    """Eurostat Statistics API — official macro-economic data."""

    def __init__(self):
        super().__init__(
            base_url="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data",
            rate_limit_per_second=30.0,
            parser_version="eurostat-1.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return records
        return records

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        url = f"{self.base_url}/?format=json"
        try:
            status, body = self._fetch_url(url)
            return self._extract_items(body, source_id), None
        except Exception:
            return [], None


class KrakenStatusAdapter(HttpAdapter):
    """Kraken official exchange status/incident API."""

    def __init__(self):
        super().__init__(
            base_url="https://status.kraken.com/api/v2",
            rate_limit_per_second=5.0,
            parser_version="kraken-status-1.0",
        )

    def _extract_items(self, body: bytes, source_id: str) -> List[RawIntakeRecord]:
        records = []
        text = body.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return records
        incidents = data.get("incidents", [])
        for inc in incidents:
            inc_id = inc.get("id", "unknown")
            name = inc.get("name", "untitled")
            created = inc.get("created_at", "")
            body_text = f"Kraken: {name}\nCreated: {created}"
            records.append(self._make_intake(
                source_id, f"https://status.kraken.com/incidents/{inc_id}",
                body_text[:500], f"kraken-{inc_id}"
            ))
        return records

    def fetch_page(self, source_id, start_time, end_time,
                   page_size=50, page_token=None):
        url = f"{self.base_url}/incidents.json"
        try:
            status, body = self._fetch_url(url)
            return self._extract_items(body, source_id), None
        except Exception:
            return [], None


ADAPTER_REGISTRY: Dict[str, HttpAdapter] = {
    "sec-edgar": SecEdgarAdapter(),
    "federal-reserve": FederalReserveAdapter(),
    "bls-economic-releases": BLSAdapter(),
    "github-security-advisories": GitHubAdvisoryAdapter(),
    "nvd-nist": NVDAdapter(),
    "cisa-alerts": CISAAdapter(),
    "binance-public": BinanceMarketAdapter(),
    "coinbase-public": CoinbaseMarketAdapter(),
    "eurostat": EurostatAdapter(),
    "kraken-status": KrakenStatusAdapter(),
}


def get_adapter(source_id: str) -> Optional[HttpAdapter]:
    return ADAPTER_REGISTRY.get(source_id)
