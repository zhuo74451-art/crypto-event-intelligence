from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..contracts.source import SourceContract
from ..contracts.raw_document import RawDocument
from ..contracts.observation import NormalizedObservation
from ..contracts.timestamps import FiveTimestamps, TimestampEvidence, TimestampQuality, utc_now
from ..contracts.errors import AcquisitionError, AcquisitionErrorCode
from .base import BaseAcquisitionAdapter, AcquisitionAdapterResult


class RssAdapter(BaseAcquisitionAdapter):
    """Adapter for RSS/Atom feeds using the feedparser library."""

    def __init__(self, contract: SourceContract):
        super().__init__(contract)

    def fetch(self, max_items: int = 10) -> AcquisitionAdapterResult:
        try:
            import feedparser
        except ImportError:
            raise ImportError(
                "The 'feedparser' library is required for RSS/Atom feeds. "
                "Install it with: pip install feedparser"
            )

        result = AcquisitionAdapterResult(source_id=self.source_id)
        url = getattr(self.contract, 'url', '') or getattr(self.contract, 'feed_url', '') or ''
        if not url:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.PARSE_ERROR,
                message="No URL configured for RSS feed",
                source_id=self.source_id,
            ))
            return result

        try:
            parsed = feedparser.parse(url)
        except Exception as exc:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.HTTP_CLIENT_ERROR,
                message=f"Failed to fetch/parse RSS feed: {exc}",
                source_id=self.source_id,
                url=url,
            ))
            return result

        if parsed.bozo and not parsed.entries:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.PARSE_ERROR,
                message=f"Feed parse error (bozo): {parsed.bozo_exception}",
                source_id=self.source_id,
                url=url,
            ))
            return result

        seen_guids: set[str] = set()
        for i, entry in enumerate(parsed.entries):
            if i >= max_items:
                break

            guid = self._get_guid(entry)
            if guid in seen_guids:
                continue
            seen_guids.add(guid)

            raw_doc_id = str(uuid.uuid4())
            now = utc_now()

            published_dt = self._parse_datetime(entry.get("published_parsed"))
            updated_dt = self._parse_datetime(entry.get("updated_parsed"))

            timestamps = self._make_timestamps(
                published=published_dt,
                updated=updated_dt,
            )

            link = entry.get("link", "")
            title = entry.get("title", "")
            summary = entry.get("summary", "")

            raw_doc = RawDocument(
                raw_document_id=raw_doc_id,
                source_id=self.source_id,
                source_event_id=guid,
                canonical_url=link,
                retrieved_url=url,
                content_type="application/rss+xml",
                encoding="utf-8",
                timestamps=timestamps,
            )

            observation = NormalizedObservation(
                observation_id=str(uuid.uuid4()),
                source_id=self.source_id,
                source_event_id=guid,
                title=title,
                summary=summary,
                body_text=summary,
                content_type="text",
                timestamps=timestamps,
                raw_document_ref=raw_doc_id,
                text_length=len(summary) if summary else 0,
            )

            result.raw_documents.append(raw_doc)
            result.observations.append(observation)

        return result

    def _get_guid(self, entry) -> str:
        """Extract a stable unique identifier from an RSS entry."""
        guid = entry.get("id") or entry.get("guid") or entry.get("link")
        if guid:
            return str(guid)
        return str(uuid.uuid4())

    @staticmethod
    def _parse_datetime(struct_time) -> datetime | None:
        """Convert a time.struct_time from feedparser to a datetime."""
        if struct_time is None:
            return None
        try:
            from calendar import timegm
            ts = timegm(struct_time)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None
