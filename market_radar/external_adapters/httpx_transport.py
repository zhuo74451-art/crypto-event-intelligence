"""HTTPX Transport — reusable synchronous public-data HTTP transport.

Provides bounded retry, deterministic error objects, JSON validation,
HTTPS allowlist, and dependency injection for testability.

Explicit connect / read / write / pool timeout configuration.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib.parse import urlparse

import httpx


# ── Constants ──

DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 30.0
DEFAULT_WRITE_TIMEOUT = 10.0
DEFAULT_POOL_TIMEOUT = 5.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.5
HTTPS_ALLOWLIST = {"api.hyperliquid.xyz", "api.binance.com", "www.okx.com", "api.bybit.com"}
USER_AGENT = "CryptoEventIntelligence-MVPPlus-Adapter/1.0"

RETRIABLE_STATUSES = {429, 500, 502, 503, 504}


# ── Error & Result Types ──


@dataclass
class TransportError:
    """Structured error from a transport operation."""
    kind: str  # network | timeout | http | json | allowlist
    message: str
    status_code: Optional[int] = None
    detail: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class TransportResult:
    """Result of a transport GET or POST call."""
    ok: bool
    data: Optional[Any] = None
    error: Optional[TransportError] = None
    status_code: Optional[int] = None
    attempts: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "data": self.data,
            "error": self.error.as_dict() if self.error else None,
            "status_code": self.status_code,
            "attempts": self.attempts,
        }


# ── Retry decision ──


def _is_retriable(status_code: Optional[int], exc: Optional[Exception]) -> bool:
    if exc is not None:
        return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError,
                                httpx.ConnectError))
    if status_code is not None and status_code in RETRIABLE_STATUSES:
        return True
    return False


# ── Main Transport ──


class HttpxTransport:
    """Reusable synchronous public-data HTTP transport.

    Usage:
        transport = HttpxTransport()
        result = transport.get("https://api.binance.com/api/v3/ping")
        print(result.ok, result.data)
    """

    def __init__(
        self,
        client: Optional[httpx.Client] = None,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
        read_timeout: float = DEFAULT_READ_TIMEOUT,
        write_timeout: float = DEFAULT_WRITE_TIMEOUT,
        pool_timeout: float = DEFAULT_POOL_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
        https_allowlist: Optional[set[str]] = None,
    ):
        self._connect_timeout = max(0.5, min(connect_timeout, 120.0))
        self._read_timeout = max(1.0, min(read_timeout, 120.0))
        self._write_timeout = max(0.5, min(write_timeout, 120.0))
        self._pool_timeout = max(0.5, min(pool_timeout, 30.0))
        self._max_retries = max(1, min(max_retries, 10))
        self._backoff_base = backoff_base
        self._https_allowlist = https_allowlist or HTTPS_ALLOWLIST
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(
                connect=self._connect_timeout,
                read=self._read_timeout,
                write=self._write_timeout,
                pool=self._pool_timeout,
            ),
            headers={"User-Agent": USER_AGENT},
        )

    # ── Context manager ──

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self) -> None:
        self._client.close()

    # ── Allowlist check ──

    def _check_allowlist(self, url: str) -> Optional[TransportError]:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if parsed.scheme != "https":
            return TransportError("allowlist", f"non-HTTPS scheme: {parsed.scheme}")
        if host not in self._https_allowlist:
            return TransportError("allowlist", f"host not allowed: {host}")
        return None

    # ── GET ──

    def get(self, url: str) -> TransportResult:
        err = self._check_allowlist(url)
        if err:
            return TransportResult(ok=False, error=err)
        return self._request("GET", url)

    # ── POST ──

    def post(self, url: str, json_body: Any = None) -> TransportResult:
        err = self._check_allowlist(url)
        if err:
            return TransportResult(ok=False, error=err)
        return self._request("POST", url, json=json_body)

    # ── Core request with retry ──

    def _request(self, method: str, url: str, **kwargs) -> TransportResult:
        last_error: Optional[TransportError] = None
        last_status: Optional[int] = None
        attempts = 0

        for attempt in range(1, self._max_retries + 1):
            attempts = attempt
            try:
                resp = self._client.request(method, url, **kwargs)
                last_status = resp.status_code

                # Non-retriable client error (ordinary 4xx)
                if 400 <= resp.status_code < 500 and resp.status_code not in RETRIABLE_STATUSES:
                    return TransportResult(
                        ok=False,
                        error=TransportError("http", f"HTTP {resp.status_code}", status_code=resp.status_code),
                        status_code=resp.status_code,
                        attempts=attempt,
                    )

                # Retriable status
                if resp.status_code in RETRIABLE_STATUSES:
                    if attempt < self._max_retries:
                        _backoff(attempt, self._backoff_base)
                        continue
                    return TransportResult(
                        ok=False,
                        error=TransportError("http", f"HTTP {resp.status_code} exhausted retries",
                                             status_code=resp.status_code),
                        status_code=resp.status_code,
                        attempts=attempt,
                    )

                # Success (2xx)
                try:
                    data = resp.json()
                except json.JSONDecodeError as e:
                    return TransportResult(
                        ok=False,
                        error=TransportError("json", f"invalid JSON: {e}"),
                        status_code=resp.status_code,
                        attempts=attempt,
                    )

                return TransportResult(ok=True, data=data, status_code=resp.status_code, attempts=attempt)

            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                last_error = TransportError("network", f"{type(e).__name__}: {e}")
                if attempt < self._max_retries:
                    _backoff(attempt, self._backoff_base)
                else:
                    return TransportResult(ok=False, error=last_error, attempts=attempt)

            except httpx.HTTPError as e:
                return TransportResult(
                    ok=False,
                    error=TransportError("http", f"{type(e).__name__}: {e}"),
                    attempts=attempt,
                )

        return TransportResult(ok=False, error=last_error, attempts=attempts)


def _backoff(attempt: int, base: float) -> None:
    delay = base ** attempt
    time.sleep(min(delay, 10.0))
