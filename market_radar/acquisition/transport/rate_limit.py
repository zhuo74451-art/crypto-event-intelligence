"""Token bucket rate limiter — thread-safe."""

from __future__ import annotations
import threading
import time


class RateLimiter:
    """Token bucket rate limiter with burst support."""

    def __init__(self, rate_per_second: float = 1.0, max_burst: int = 5) -> None:
        self.rate = rate_per_second
        self.max_burst = max_burst
        self._tokens = float(max_burst)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.max_burst, self._tokens + elapsed * self.rate)
        self._last_refill = now

    def acquire(self, amount: int = 1) -> bool:
        """Block until tokens are available, then return True."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= amount:
                    self._tokens -= amount
                    return True
                deficit = amount - self._tokens
                wait = deficit / self.rate if self.rate > 0 else 0.1
            time.sleep(wait)

    def try_acquire(self, amount: int = 1) -> bool:
        """Non-blocking: return True if tokens available, else False."""
        with self._lock:
            self._refill()
            if self._tokens >= amount:
                self._tokens -= amount
                return True
            return False
