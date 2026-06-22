from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..contracts.source import SourceContract
from ..contracts.raw_document import RawDocument
from ..contracts.observation import NormalizedObservation
from ..contracts.timestamps import FiveTimestamps, TimestampEvidence, TimestampQuality, utc_now
from ..contracts.errors import AcquisitionError, AcquisitionErrorCode
from .base import BaseAcquisitionAdapter, AcquisitionAdapterResult
from ..transport.http_client import AcqHttpClient


class StaticHtmlAdapter(BaseAcquisitionAdapter):
    """Adapter for static HTML pages.

    Fetches a single HTML page using the transport's http_client.
    Returns one observation with extracted metadata (timestamps, title from HTML).
    """

    def __init__(self, contract: SourceContract, http_client: AcqHttpClient | None = None):
        super().__init__(contract)
        self._http_client = http_client or AcqHttpClient()

    def fetch(self, max_items: int = 10) -> AcquisitionAdapterResult:
        result = AcquisitionAdapterResult(source_id=self.source_id)
        now = utc_now()

        url = getattr(self.contract, 'url', '') or ''
        if not url:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.PARSE_ERROR,
                message="No URL configured for static HTML adapter",
                source_id=self.source_id,
            ))
            return result

        try:
            response = self._http_client.get(url)
        except AcquisitionError as exc:
            result.errors.append(exc)
            return result
        except Exception as exc:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.HTTP_CLIENT_ERROR,
                message=str(exc),
                source_id=self.source_id,
                url=url,
            ))
            return result

        if response.status != 200:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.HTTP_CLIENT_ERROR,
                message=f"HTTP {response.status} for static HTML page",
                source_id=self.source_id,
                url=url,
                http_status=response.status,
            ))
            return result

        try:
            html_content = response.body.decode(response.encoding or "utf-8")
        except UnicodeDecodeError as exc:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.INVALID_ENCODING,
                message=f"Failed to decode HTML: {exc}",
                source_id=self.source_id,
                url=url,
            ))
            return result

        # Extract <title> from HTML
        title = self._extract_title(html_content)

        # Try to extract date from common HTML metadata patterns
        published_dt = self._extract_date(html_content)

        timestamps = self._make_timestamps(published=published_dt)

        raw_doc_id = str(uuid.uuid4())
        raw_doc = RawDocument(
            raw_document_id=raw_doc_id,
            source_id=self.source_id,
            source_event_id=url,
            canonical_url=url,
            retrieved_url=url,
            http_status=response.status,
            content_type=response.headers.get("content-type", "text/html"),
            encoding=response.encoding,
            timestamps=timestamps,
            payload_size=len(response.body),
        )

        observation = NormalizedObservation(
            observation_id=str(uuid.uuid4()),
            source_id=self.source_id,
            source_event_id=url,
            title=title,
            summary=title,
            body_text=html_content[:10000],  # Truncate very large pages
            content_type="text/html",
            timestamps=timestamps,
            raw_document_ref=raw_doc_id,
            text_length=len(html_content),
        )

        result.raw_documents.append(raw_doc)
        result.observations.append(observation)

        return result

    @staticmethod
    def _extract_title(html: str) -> str:
        """Extract the <title> content from an HTML string."""
        match = re.search(
            r'<title[^>]*>(.*?)</title>',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            title = match.group(1).strip()
            # Decode common HTML entities
            title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"").replace("&#39;", "'")
            return title
        return ""

    @staticmethod
    def _extract_date(html: str) -> datetime | None:
        """Try to extract a date from HTML meta tags or common patterns."""
        # Look for <meta name="date" content="...">
        match = re.search(
            r'<meta\s+[^>]*name=["\']date["\'][^>]*content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            try:
                return datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Look for <meta property="article:published_time" content="...">
        match = re.search(
            r'<meta\s+[^>]*property=["\']article:published_time["\'][^>]*content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            try:
                return datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Look for <time datetime="...">
        match = re.search(
            r'<time\s+[^>]*datetime=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            try:
                return datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        return None
