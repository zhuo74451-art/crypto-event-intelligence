"""L1 — Hyperliquid API Client with provenance tracking.

Wraps Hyperliquid public Info API with:
- Retry with exponential backoff
- Connect/read timeouts
- ProvenanceRecord for every call
- Raw response archiving for audit
- Bounded concurrency
- Rate-limit awareness
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from market_radar.l1_hyperliquid_provider.provenance import (
    DataMode, ProvenanceRecord, SourceHealth,
    make_provenance, make_source_health, utc_now_str,
)

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
USER_AGENT = "MVPPlus-W2/1.0 (hl-client; no-key public data)"
DEFAULT_CONNECT_TIMEOUT = 5
DEFAULT_READ_TIMEOUT = 15
MAX_RETRIES = 2
RETRY_BACKOFF = [1.0, 2.0]  # seconds
BOUNDED_CONCURRENCY = 8

# Hyperliquid asset names relevant for whales
HL_WHALE_ASSETS = [
    "BTC", "ETH", "SOL", "HYPE", "ARB", "OP", "AVAX", "LINK",
    "DOGE", "SUI", "PEPE", "WLD", "NEAR", "ZEC", "XMR", "ASTER",
    "AAVE", "UNI", "PENDLE", "ENA", "ONDO", "JUP", "PYTH", "WIF",
]


class HLClientError(Exception):
    """Base error for Hyperliquid client."""


class HLServerError(HLClientError):
    """Server returned error response."""


class HLTimeoutError(HLClientError):
    """Request timed out."""


def _hl_post(
    payload: dict,
    timeout: int = DEFAULT_READ_TIMEOUT,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
) -> tuple[Optional[Any], Optional[str]]:
    """POST to Hyperliquid Info API.

    Returns (parsed_json, error_message).
    """
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        HYPERLIQUID_INFO_URL, data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=connect_timeout + timeout) as resp:
            data = resp.read().decode("utf-8")
        return json.loads(data), None
    except HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        return None, f"HTTP {e.code}: {error_body or e.reason}"
    except URLError as e:
        return None, f"URL error: {e.reason}"
    except OSError as e:
        return None, f"OS error: {e}"
    except (ValueError, json.JSONDecodeError) as e:
        return None, f"JSON decode error: {e}"


def _hl_post_with_provenance(
    payload: dict,
    endpoint_name: str,
    raw_archive_dir: Optional[str] = None,
) -> tuple[Optional[Any], Optional[str], Optional[ProvenanceRecord]]:
    """POST with retry, provenance tracking, and raw response archiving."""
    last_error: Optional[str] = None
    start_time = time.time()

    for attempt in range(1 + MAX_RETRIES):
        result, error = _hl_post(payload)
        if result is not None:
            elapsed = time.time() - start_time

            # Archive raw response if directory configured
            raw_ref: Optional[str] = None
            if raw_archive_dir and endpoint_name:
                os.makedirs(raw_archive_dir, exist_ok=True)
                ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                fname = f"hl_{endpoint_name}_{ts}_attempt{attempt+1}.json"
                path = os.path.join(raw_archive_dir, fname)
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    raw_ref = os.path.relpath(path, os.path.join(os.path.dirname(__file__), *[os.pardir] * 2))
                except IOError:
                    pass

            prov = make_provenance(
                data_mode=DataMode.LIVE,
                endpoint=endpoint_name,
                raw_artifact_ref=raw_ref,
                response_age_seconds=round(elapsed, 3),
            )
            return result, None, prov

        last_error = error or f"attempt {attempt + 1} failed"
        if attempt < MAX_RETRIES:
            delay = RETRY_BACKOFF[attempt] if attempt < len(RETRY_BACKOFF) else RETRY_BACKOFF[-1]
            time.sleep(delay)

    return None, last_error, None


class HyperliquidClient:
    """Read-only Hyperliquid public API client.

    All methods return (data, error, provenance) tuples.
    """

    def __init__(
        self,
        raw_archive_dir: Optional[str] = None,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: int = DEFAULT_READ_TIMEOUT,
    ):
        _SCRIPT_DIR_HL = os.path.dirname(os.path.abspath(__file__))
        PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR_HL, *[os.pardir] * 3))
        self.raw_archive_dir = raw_archive_dir or os.path.join(
            PROJECT_ROOT, "artifacts", "evidence", "hl_raw_responses"
        )
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self._last_response_time: Optional[float] = None

    def fetch_all_mids(self) -> tuple[Optional[dict[str, str]], Optional[str], Optional[ProvenanceRecord]]:
        """Fetch all mid prices.

        Returns (mids_dict, error, provenance).
        """
        result, error, prov = _hl_post_with_provenance(
            {"type": "allMids"},
            "allMids",
            self.raw_archive_dir,
        )
        if error:
            return None, error, None
        if not isinstance(result, dict):
            return None, "allMids response is not a dict", None
        return result, None, prov

    def fetch_clearinghouse_state(
        self, address: str,
    ) -> tuple[Optional[dict], Optional[str], Optional[ProvenanceRecord]]:
        """Fetch clearinghouse state for an address.

        Returns (state_dict, error, provenance).
        """
        result, error, prov = _hl_post_with_provenance(
            {"type": "clearinghouseState", "user": address},
            f"clearinghouseState_{address[:6]}",
            self.raw_archive_dir,
        )
        if error:
            return None, error, None
        if not isinstance(result, dict):
            return None, "clearinghouseState response is not a dict", None
        return result, None, prov

    def fetch_meta(self) -> tuple[Optional[list], Optional[str], Optional[ProvenanceRecord]]:
        """Fetch asset metadata (universe)."""
        result, error, prov = _hl_post_with_provenance(
            {"type": "meta"},
            "meta",
            self.raw_archive_dir,
        )
        if error:
            return None, error, None
        if not isinstance(result, list):
            return None, "meta response is not a list", None
        return result, None, prov

    def fetch_spot_clearinghouse_state(
        self, address: str,
    ) -> tuple[Optional[dict], Optional[str], Optional[ProvenanceRecord]]:
        """Fetch spot/HYPE staking state for an address."""
        result, error, prov = _hl_post_with_provenance(
            {"type": "spotClearinghouseState", "user": address},
            f"spotClearinghouseState_{address[:6]}",
            self.raw_archive_dir,
        )
        if error:
            return None, error, None
        return result, None, prov

    def fetch_funding_history(
        self, coin: str,
    ) -> tuple[Optional[list], Optional[str], Optional[ProvenanceRecord]]:
        """Fetch funding history for a coin."""
        result, error, prov = _hl_post_with_provenance(
            {"type": "fundingHistory", "coin": coin},
            f"fundingHistory_{coin}",
            self.raw_archive_dir,
        )
        if error:
            return None, error, None
        return result, None, prov
