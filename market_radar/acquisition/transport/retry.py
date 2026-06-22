"""Retry with exponential backoff and jitter."""

from __future__ import annotations
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class RetryPolicy:
    """Policy controlling retry behaviour."""
    max_retries: int = 3
    base_delay: float = 1.5
    max_delay: float = 10.0
    jitter: float = 0.1
    retriable_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
    )


# ── helpers ──────────────────────────────────────────────────────────

def is_retriable(error_code: str, http_status: int | None = None) -> bool:
    """Return True if the error is likely retriable."""
    if http_status is not None and http_status in {429, 500, 502, 503, 504}:
        return True
    retriable_codes = {
        "RATE_LIMITED", "HTTP_TIMEOUT", "HTTP_SERVER_ERROR",
        "CONNECT_TIMEOUT", "READ_TIMEOUT", "DNS_ERROR", "TLS_ERROR",
    }
    return error_code.upper() in retriable_codes


def parse_retry_after(header_value: str | None) -> float | None:
    """Parse Retry-After header (seconds integer or HTTP-date)."""
    if not header_value:
        return None
    # Try integer seconds first
    try:
        return float(int(header_value.strip()))
    except (ValueError, TypeError):
        pass
    # Try HTTP-date format (simple heuristic)
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(header_value.strip())
        now = time.time()
        retry = dt.timestamp()
        if retry > now:
            return retry - now
        return 0.0
    except Exception:
        return None


# ── handler ──────────────────────────────────────────────────────────

class RetryHandler:
    """Executes a callable with retry logic."""

    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self.policy = policy or RetryPolicy()

    def execute(self, fn: Callable[[], Any]) -> Any:
        """Call fn up to max_retries times. Returns fn result on success, raises last error on exhaustion."""
        last_exc: Exception | None = None
        for attempt in range(self.policy.max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                last_exc = exc
                if attempt < self.policy.max_retries:
                    delay = min(
                        self.policy.base_delay * (2 ** attempt),
                        self.policy.max_delay,
                    )
                    jitter = random.uniform(-self.policy.jitter, self.policy.jitter)
                    delay = max(0, delay + jitter)
                    time.sleep(delay)
        if last_exc is not None:
            raise last_exc
