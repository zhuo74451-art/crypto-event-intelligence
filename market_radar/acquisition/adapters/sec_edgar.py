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


class SecEdgarAdapter(BaseAcquisitionAdapter):
    """Adapter for SEC EDGAR company submissions JSON endpoint."""

    BASE_URL = "https://data.sec.gov/submissions"

    def __init__(self, contract: SourceContract, http_client: AcqHttpClient | None = None):
        super().__init__(contract)
        self._http_client = http_client or AcqHttpClient()

    def fetch(self, max_items: int = 10) -> AcquisitionAdapterResult:
        result = AcquisitionAdapterResult(source_id=self.source_id)

        cik = getattr(self.contract, 'cik', '') or ''
        if not cik:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.PARSE_ERROR,
                message="No CIK configured for SEC EDGAR adapter",
                source_id=self.source_id,
            ))
            return result

        cik_padded = str(cik).zfill(10)
        url = f"{self.BASE_URL}/CIK{cik_padded}.json"

        email = getattr(self.contract, 'email', '') or ''
        user_agent = f"Sample Company Name AdminContact@<sample.com> {email}".strip()
        if email:
            user_agent = f"Sample Company Name {email}"
        else:
            user_agent = "SampleCompanyName/1.0 (admin@example.com)"

        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }

        try:
            response = self._http_client.get(url, headers=headers)
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
                message=f"HTTP {response.status} from SEC EDGAR",
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
                message=f"Failed to parse SEC EDGAR JSON: {exc}",
                source_id=self.source_id,
                url=url,
            ))
            return result

        raw_payload_ref = f"sec_edgar_{cik}_{uuid.uuid4().hex[:8]}"

        filings = data.get("filings", {}).get("recent", {})
        accession_numbers = filings.get("accessionNumber", [])
        filing_dates = filings.get("filingDate", [])
        primary_documents = filings.get("primaryDocument", [])
        form_types = filings.get("form", [])
        primary_descriptions = filings.get("primaryDocDescription", [])

        count = min(max_items, len(accession_numbers))

        now = utc_now()

        for i in range(count):
            accession = accession_numbers[i] if i < len(accession_numbers) else str(uuid.uuid4())
            accession_clean = accession.replace("-", "")
            filing_date_str = filing_dates[i] if i < len(filing_dates) else ""
            primary_doc = primary_documents[i] if i < len(primary_documents) else ""
            form_type = form_types[i] if i < len(form_types) else ""
            description = primary_descriptions[i] if i < len(primary_descriptions) else ""

            # Parse filing date
            published_dt = None
            if filing_date_str:
                try:
                    published_dt = datetime.strptime(filing_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass

            doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{primary_doc}" if primary_doc else url

            timestamps = self._make_timestamps(published=published_dt)

            raw_doc_id = str(uuid.uuid4())
            raw_doc = RawDocument(
                raw_document_id=raw_doc_id,
                source_id=self.source_id,
                source_event_id=accession,
                canonical_url=doc_url,
                retrieved_url=url,
                http_status=response.status,
                content_type="application/json",
                encoding="utf-8",
                timestamps=timestamps,
                raw_payload_ref=raw_payload_ref,
            )

            title = f"{form_type} - {description}" if description else form_type

            observation = NormalizedObservation(
                observation_id=str(uuid.uuid4()),
                source_id=self.source_id,
                source_event_id=accession,
                title=title,
                summary=description or "",
                body_text=json.dumps({
                    "form_type": form_type,
                    "primary_document": primary_doc,
                    "filing_date": filing_date_str,
                    "description": description,
                }),
                content_type="application/json",
                timestamps=timestamps,
                raw_document_ref=raw_doc_id,
                text_length=len(description) if description else 0,
            )

            result.raw_documents.append(raw_doc)
            result.observations.append(observation)

        return result
