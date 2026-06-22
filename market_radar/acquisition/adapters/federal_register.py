from __future__ import annotations
import json
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


class FederalRegisterAdapter(BaseAcquisitionAdapter):
    """Adapter for the Federal Register API v1 documents endpoint."""

    BASE_URL = "https://www.federalregister.gov/api/v1/documents.json"

    def __init__(self, contract: SourceContract, http_client: AcqHttpClient | None = None):
        super().__init__(contract)
        self._http_client = http_client or AcqHttpClient()

    def fetch(self, max_items: int = 10) -> AcquisitionAdapterResult:
        result = AcquisitionAdapterResult(source_id=self.source_id)
        now = utc_now()

        # Build query parameters from contract or defaults
        params = {}
        daily_jr = getattr(self.contract, 'daily_journal', None)
        if daily_jr:
            params["daily_journal"] = daily_jr

        conditions = getattr(self.contract, 'conditions', None)
        if conditions:
            params["conditions"] = conditions

        url = self.BASE_URL
        if params:
            import urllib.parse
            url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

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
                message=f"HTTP {response.status} from Federal Register API",
                source_id=self.source_id,
                url=url,
                http_status=response.status,
            ))
            return result

        try:
            data = json.loads(response.body.decode(response.encoding or "utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.PARSE_ERROR,
                message=f"Failed to parse Federal Register JSON: {exc}",
                source_id=self.source_id,
                url=url,
            ))
            return result

        documents = data.get("results", [])
        total_pages = data.get("total_pages", 1)
        current_page = data.get("current_page", 1)

        for i, doc in enumerate(documents):
            if i >= max_items:
                break

            document_number = doc.get("document_number", "") or str(uuid.uuid4())
            title = doc.get("title", "")
            abstract = doc.get("abstract", "")
            agency_names = doc.get("agency_names", [])
            html_url = doc.get("html_url", "")
            pdf_url = doc.get("pdf_url", "")
            publication_date_str = doc.get("publication_date", "")
            effective_on_date_str = doc.get("effective_on_date", "")

            published_dt = self._parse_date(publication_date_str)
            effective_dt = self._parse_date(effective_on_date_str)

            timestamps = self._make_timestamps(
                published=published_dt,
                effective=effective_dt,
            )

            raw_doc_id = str(uuid.uuid4())
            raw_doc = RawDocument(
                raw_document_id=raw_doc_id,
                source_id=self.source_id,
                source_event_id=document_number,
                canonical_url=html_url or url,
                retrieved_url=url,
                http_status=response.status,
                content_type="application/json",
                encoding="utf-8",
                timestamps=timestamps,
            )

            body_text = json.dumps({
                "document_number": document_number,
                "agency_names": agency_names,
                "html_url": html_url,
                "pdf_url": pdf_url,
                "publication_date": publication_date_str,
                "effective_on_date": effective_on_date_str,
            })

            summary_parts = []
            if agency_names:
                summary_parts.append(f"Agencies: {', '.join(agency_names)}")
            if abstract:
                summary_parts.append(abstract)

            observation = NormalizedObservation(
                observation_id=str(uuid.uuid4()),
                source_id=self.source_id,
                source_event_id=document_number,
                title=title,
                summary=" | ".join(summary_parts) if summary_parts else "",
                body_text=body_text,
                content_type="application/json",
                timestamps=timestamps,
                raw_document_ref=raw_doc_id,
                text_length=len(abstract) if abstract else 0,
            )

            result.raw_documents.append(raw_doc)
            result.observations.append(observation)

        # Store pagination info
        if current_page < total_pages:
            result.raw_documents.append(RawDocument(
                raw_document_id=str(uuid.uuid4()),
                source_id=self.source_id,
                source_event_id="__pagination__",
                canonical_url=url,
                retrieved_url=url,
                http_status=response.status,
                content_type="application/json",
                encoding="utf-8",
                timestamps=self._make_timestamps(),
                raw_payload_ref=json.dumps({
                    "pagination": {
                        "current_page": current_page,
                        "total_pages": total_pages,
                        "next_page": current_page + 1,
                    }
                }),
            ))

        return result

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            try:
                return datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                return None
