from __future__ import annotations

import time
from typing import Optional, Tuple

from ..transport.http_client import AcqHttpClient


class AvailabilityChecker:
    """Checks URL availability via the transport layer's ``AcqHttpClient``."""

    def __init__(self, client: Optional[AcqHttpClient] = None) -> None:
        self._client = client or AcqHttpClient(default_timeout=30.0)

    def check_url(
        self,
        url: str,
        timeout: float = 10.0,
    ) -> Tuple[bool, Optional[int], float]:
        """Return ``(available, http_status, elapsed_seconds)``.

        Parameters
        ----------
        url : str
            The URL to check.
        timeout : float
            Request timeout in seconds (default 10.0).

        Returns
        -------
        tuple[bool, int | None, float]
            ``available`` is ``True`` for any 2xx status.
            ``http_status`` is the HTTP status code, or ``None`` on error.
            ``elapsed_seconds`` is wall-clock time taken (seconds).
        """
        start = time.monotonic()
        try:
            response = self._client.get(url, timeout=timeout)
            elapsed = time.monotonic() - start
            available = 200 <= response.status < 300
            return (available, response.status, round(elapsed, 4))
        except Exception:
            elapsed = time.monotonic() - start
            return (False, None, round(elapsed, 4))
