"""Main HTTP client for acquisition."""

from __future__ import annotations
import time
from pathlib import Path
from typing import Any

import httpx

from .response import HttpResponse, redact_headers, SAFE_HEADERS
from ..contracts.errors import AcquisitionError, AcquisitionErrorCode

_SUPPORTED_CONTENT_TYPES = frozenset({
    "text/html",
    "application/json",
    "application/xml",
    "text/xml",
    "application/rss+xml",
    "application/atom+xml",
    "text/plain",
    "application/pdf",
})


def _is_supported_content_type(content_type: str) -> bool:
    ct = content_type.strip().lower().split(";")[0].strip()
    if ct in _SUPPORTED_CONTENT_TYPES:
        return True
    if ct.startswith("text/"):
        return True
    return False


def _detect_encoding(content_type: str) -> str:
    """Extract charset from Content-Type header, default to utf-8."""
    for part in content_type.lower().split(";"):
        part = part.strip()
        if part.startswith("charset="):
            return part.split("=", 1)[1].strip()
    return "utf-8"
class AcqHttpClient:
    """HTTP client for document acquisition with safety limits."""

    def __init__(
        self,
        default_timeout: float = 30.0,
        max_redirects: int = 10,
        max_payload_bytes: int = 50_000_000,
        user_agent: str = "CryptoMarketCognition-Acquisition/1.0",
        fixture_mode: bool = False,
        fixture_base_path: str | None = None,
    ) -> None:
        self._default_timeout = default_timeout
        self._max_redirects = max_redirects
        self._max_payload_bytes = max_payload_bytes
        self._user_agent = user_agent
        self._fixture_mode = fixture_mode
        self._fixture_base_path = Path(fixture_base_path) if fixture_base_path else None

    def get(
        self,
        url: str,
        headers: dict | None = None,
        timeout: float | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> HttpResponse:
        if self._fixture_mode:
            return self._get_from_fixture(url, headers, etag, last_modified)

        request_headers = {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/json,application/xml,*/*",
        }
        if headers:
            request_headers.update(headers)
        if etag:
            request_headers["If-None-Match"] = etag
        if last_modified:
            request_headers["If-Modified-Since"] = last_modified

        effective_timeout = timeout if timeout is not None else self._default_timeout

        with httpx.Client(
            timeout=httpx.Timeout(effective_timeout),
            follow_redirects=False,
        ) as client:
            start = time.monotonic()
            try:
                response = client.get(
                    url,
                    headers=request_headers,
                    follow_redirects=False,
                )
            except httpx.TimeoutException as exc:
                code = AcquisitionErrorCode.HTTP_TIMEOUT
                raise AcquisitionError(
                    code=code,
                    message=str(exc),
                    url=url,
                ) from exc
            except httpx.ConnectError as exc:
                raise AcquisitionError(
                    code=AcquisitionErrorCode.CONNECT_TIMEOUT,
                    message=str(exc),
                    url=url,
                ) from exc
            except httpx.RemoteProtocolError as exc:
                raise AcquisitionError(
                    code=AcquisitionErrorCode.TLS_ERROR,
                    message=str(exc),
                    url=url,
                ) from exc
            except Exception as exc:
                raise AcquisitionError(
                    code=AcquisitionErrorCode.HTTP_CLIENT_ERROR,
                    message=str(exc),
                    url=url,
                ) from exc

            elapsed_ms = (time.monotonic() - start) * 1000

            # Handle redirects manually
            redirect_count = 0
            while response.status_code in (301, 302, 303, 307, 308):
                redirect_count += 1
                if redirect_count > self._max_redirects:
                    raise AcquisitionError(
                        code=AcquisitionErrorCode.REDIRECT_LOOP,
                        message=f"Too many redirects ({redirect_count})",
                        url=url,
                        http_status=response.status_code,
                    )
                location = response.headers.get("Location")
                if not location:
                    break
                try:
                    response = client.get(
                        location,
                        headers=request_headers,
                        follow_redirects=False,
                    )
                except Exception as exc:
                    raise AcquisitionError(
                        code=AcquisitionErrorCode.HTTP_CLIENT_ERROR,
                        message=str(exc),
                        url=location,
                    ) from exc

            # Enforce max payload size
            body = response.content
            if len(body) > self._max_payload_bytes:
                raise AcquisitionError(
                    code=AcquisitionErrorCode.PAYLOAD_TOO_LARGE,
                    message=f"Payload {len(body)} bytes exceeds limit {self._max_payload_bytes}",
                    url=url,
                    http_status=response.status_code,
                )

            # Content-type sanity check
            raw_ct = response.headers.get("Content-Type", "")
            if raw_ct and not _is_supported_content_type(raw_ct):
                raise AcquisitionError(
                    code=AcquisitionErrorCode.UNSUPPORTED_CONTENT_TYPE,
                    message=f"Unsupported content type: {raw_ct}",
                    url=url,
                    http_status=response.status_code,
                )

            encoding = _detect_encoding(raw_ct) if raw_ct else "utf-8"
            safe_headers = redact_headers(dict(response.headers))
            response_etag = response.headers.get("ETag", "")
            response_last_modified = response.headers.get("Last-Modified", "")

            return HttpResponse(
                status=response.status_code,
                headers=safe_headers,
                body=body,
                encoding=encoding,
                elapsed_ms=elapsed_ms,
                from_cache=False,
                etag=response_etag,
                last_modified=response_last_modified,
            )

    def _get_from_fixture(
        self,
        url: str,
        headers: dict | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> HttpResponse:
        """Read a fixture file instead of making a network call."""
        if self._fixture_base_path is None:
            raise AcquisitionError(
                code=AcquisitionErrorCode.HTTP_CLIENT_ERROR,
                message="Fixture mode enabled but no fixture_base_path provided",
                url=url,
            )
        import hashlib
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        fixture_file = self._fixture_base_path / f"{key}.bin"
        if not fixture_file.exists():
            raise AcquisitionError(
                code=AcquisitionErrorCode.HTTP_CLIENT_ERROR,
                message=f"Fixture not found: {fixture_file}",
                url=url,
            )
        body = fixture_file.read_bytes()
        meta_file = self._fixture_base_path / f"{key}.json"
        headers_dict: dict = {}
        encoding = "utf-8"
        if meta_file.exists():
            import json
            try:
                meta = json.loads(meta_file.read_text("utf-8"))
                headers_dict = meta.get("headers", {})
                encoding = meta.get("encoding", "utf-8")
            except Exception:
                pass
        safe_headers = redact_headers(headers_dict)
        return HttpResponse(
            status=200,
            headers=safe_headers,
            body=body,
            encoding=encoding,
            elapsed_ms=0.0,
            from_cache=False,
        )
