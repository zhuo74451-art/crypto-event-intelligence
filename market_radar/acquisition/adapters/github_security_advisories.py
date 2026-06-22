from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from ..contracts.source import SourceContract
from ..contracts.raw_document import RawDocument
from ..contracts.observation import NormalizedObservation
from ..contracts.timestamps import FiveTimestamps, TimestampEvidence, TimestampQuality, utc_now
from ..contracts.errors import AcquisitionError, AcquisitionErrorCode
from .base import BaseAcquisitionAdapter, AcquisitionAdapterResult
from ..transport.http_client import AcqHttpClient


class GitHubSecurityAdvisoriesAdapter(BaseAcquisitionAdapter):
    """Adapter for GitHub Security Advisories API.

    Uses https://api.github.com/advisories public API or
    /repos/{owner}/{repo}/security-advisories for repository-scoped advisories.
    Maps: ghsa_id -> source_event_id, cve_id, severity, published_at, updated_at,
    summary, description, cvss_score, cwe_ids, vulnerabilities (list of affected packages).
    Does NOT convert severity to market direction.
    """

    GLOBAL_URL = "https://api.github.com/advisories"
    REPO_URL = "https://api.github.com/repos"

    def __init__(self, contract: SourceContract, http_client: AcqHttpClient | None = None):
        super().__init__(contract)
        self._http_client = http_client or AcqHttpClient()

    def fetch(self, max_items: int = 10) -> AcquisitionAdapterResult:
        result = AcquisitionAdapterResult(source_id=self.source_id)
        now = utc_now()

        owner = getattr(self.contract, 'owner', '') or ''
        repo = getattr(self.contract, 'repo', '') or ''

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "CryptoMarketCognition-Acquisition/1.0",
        }

        gh_token = getattr(self.contract, 'token', '') or getattr(self.contract, 'github_token', '') or ''
        if gh_token:
            headers["Authorization"] = f"Bearer {gh_token}"

        # Use repo-scoped URL if owner/repo provided, otherwise global
        if owner and repo:
            url = f"{self.REPO_URL}/{owner}/{repo}/security-advisories"
        else:
            url = self.GLOBAL_URL

        per_page = min(max_items, 100)
        url_with_params = f"{url}?per_page={per_page}"

        try:
            response = self._http_client.get(url_with_params, headers=headers)
        except AcquisitionError as exc:
            result.errors.append(exc)
            return result
        except Exception as exc:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.HTTP_CLIENT_ERROR,
                message=str(exc),
                source_id=self.source_id,
                url=url_with_params,
            ))
            return result

        if response.status != 200:
            if response.status == 403:
                result.errors.append(AcquisitionError(
                    code=AcquisitionErrorCode.RATE_LIMITED,
                    message="GitHub API rate limit exceeded",
                    source_id=self.source_id,
                    url=url_with_params,
                    http_status=403,
                ))
            else:
                result.errors.append(AcquisitionError(
                    code=AcquisitionErrorCode.HTTP_CLIENT_ERROR,
                    message=f"HTTP {response.status} from GitHub Advisories API",
                    source_id=self.source_id,
                    url=url_with_params,
                    http_status=response.status,
                ))
            return result

        try:
            advisories = json.loads(response.body.decode(response.encoding or "utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.PARSE_ERROR,
                message=f"Failed to parse GitHub advisories JSON: {exc}",
                source_id=self.source_id,
                url=url_with_params,
            ))
            return result

        if not isinstance(advisories, list):
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.PARSE_ERROR,
                message="Expected a list of advisories from GitHub API",
                source_id=self.source_id,
                url=url_with_params,
            ))
            return result

        for i, advisory in enumerate(advisories):
            if i >= max_items:
                break

            ghsa_id = advisory.get("ghsa_id", "") or str(uuid.uuid4())
            cve_id = advisory.get("cve_id") or advisory.get("cve_id", "")
            severity = advisory.get("severity", "")
            summary = advisory.get("summary", "")
            description = advisory.get("description", "")
            cvss_score = advisory.get("cvss_score") or advisory.get("cvss", {}).get("score")
            cwe_ids = advisory.get("cwe_ids", []) or [cwe.get("cwe_id", "") for cwe in advisory.get("cwes", [])]
            vulnerabilities = advisory.get("vulnerabilities", []) or advisory.get("vulnerabilities", {})
            published_at_str = advisory.get("published_at", "")
            updated_at_str = advisory.get("updated_at", "")
            html_url = advisory.get("html_url", "") or advisory.get("url", "")

            published_dt = self._parse_datetime(published_at_str)
            updated_dt = self._parse_datetime(updated_at_str)

            timestamps = self._make_timestamps(
                published=published_dt,
                updated=updated_dt,
            )

            raw_doc_id = str(uuid.uuid4())
            raw_doc = RawDocument(
                raw_document_id=raw_doc_id,
                source_id=self.source_id,
                source_event_id=ghsa_id,
                canonical_url=html_url or url_with_params,
                retrieved_url=url_with_params,
                http_status=response.status,
                content_type="application/json",
                encoding="utf-8",
                timestamps=timestamps,
            )

            body_text = json.dumps({
                "ghsa_id": ghsa_id,
                "cve_id": cve_id,
                "severity": severity,
                "cvss_score": cvss_score,
                "cwe_ids": cwe_ids,
                "vulnerabilities": vulnerabilities,
            })

            observation = NormalizedObservation(
                observation_id=str(uuid.uuid4()),
                source_id=self.source_id,
                source_event_id=ghsa_id,
                title=summary,
                summary=summary,
                body_text=body_text,
                content_type="application/json",
                timestamps=timestamps,
                raw_document_ref=raw_doc_id,
                text_length=len(description) if description else 0,
            )

            result.raw_documents.append(raw_doc)
            result.observations.append(observation)

        return result

    @staticmethod
    def _parse_datetime(dt_str: str) -> datetime | None:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
