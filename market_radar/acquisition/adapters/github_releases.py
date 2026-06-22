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


class GitHubReleasesAdapter(BaseAcquisitionAdapter):
    """Adapter for GitHub Releases API.

    Uses https://api.github.com/repos/{owner}/{repo}/releases public API.
    Maps: id -> source_event_id, tag_name, published_at, body, prerelease, draft, html_url.
    Supports filtering of draft/prerelease releases.
    """

    BASE_URL = "https://api.github.com/repos"

    def __init__(self, contract: SourceContract, http_client: AcqHttpClient | None = None):
        super().__init__(contract)
        self._http_client = http_client or AcqHttpClient()

    def fetch(self, max_items: int = 10) -> AcquisitionAdapterResult:
        result = AcquisitionAdapterResult(source_id=self.source_id)
        now = utc_now()

        owner = getattr(self.contract, 'owner', '') or ''
        repo = getattr(self.contract, 'repo', '') or ''
        if not owner or not repo:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.PARSE_ERROR,
                message="GitHub owner and repo must be configured",
                source_id=self.source_id,
            ))
            return result

        url = f"{self.BASE_URL}/{owner}/{repo}/releases"

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "CryptoMarketCognition-Acquisition/1.0",
        }

        token = getattr(self.contract, 'token', '') or getattr(self.contract, 'github_token', '') or ''
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Per_page parameter for max_items
        per_page = min(max_items, 100)
        url_with_params = f"{url}?per_page={per_page}"

        include_drafts = getattr(self.contract, 'include_drafts', False)
        include_prereleases = getattr(self.contract, 'include_prereleases', True)

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
                    message="GitHub API rate limit exceeded (60/hr unauthenticated)",
                    source_id=self.source_id,
                    url=url_with_params,
                    http_status=403,
                ))
            elif response.status == 404:
                result.errors.append(AcquisitionError(
                    code=AcquisitionErrorCode.HTTP_CLIENT_ERROR,
                    message=f"Repository not found: {owner}/{repo}",
                    source_id=self.source_id,
                    url=url_with_params,
                    http_status=404,
                ))
            else:
                result.errors.append(AcquisitionError(
                    code=AcquisitionErrorCode.HTTP_CLIENT_ERROR,
                    message=f"HTTP {response.status} from GitHub API",
                    source_id=self.source_id,
                    url=url_with_params,
                    http_status=response.status,
                ))
            return result

        try:
            releases = json.loads(response.body.decode(response.encoding or "utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.PARSE_ERROR,
                message=f"Failed to parse GitHub releases JSON: {exc}",
                source_id=self.source_id,
                url=url_with_params,
            ))
            return result

        if not isinstance(releases, list):
            result.errors.append(AcquisitionError(
                code=AcquisitionErrorCode.PARSE_ERROR,
                message="Expected a list of releases from GitHub API",
                source_id=self.source_id,
                url=url_with_params,
            ))
            return result

        for i, release in enumerate(releases):
            if i >= max_items:
                break

            is_draft = release.get("draft", False)
            is_prerelease = release.get("prerelease", False)

            if is_draft and not include_drafts:
                continue
            if is_prerelease and not include_prereleases:
                continue

            release_id = str(release.get("id", ""))
            tag_name = release.get("tag_name", "")
            published_at_str = release.get("published_at", "")
            body = release.get("body", "")
            html_url = release.get("html_url", "")
            name = release.get("name", "") or tag_name

            published_dt = None
            if published_at_str:
                try:
                    published_dt = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            timestamps = self._make_timestamps(published=published_dt)

            raw_doc_id = str(uuid.uuid4())
            raw_doc = RawDocument(
                raw_document_id=raw_doc_id,
                source_id=self.source_id,
                source_event_id=release_id,
                canonical_url=html_url or url_with_params,
                retrieved_url=url_with_params,
                http_status=response.status,
                content_type="application/json",
                encoding="utf-8",
                timestamps=timestamps,
            )

            body_text = json.dumps({
                "tag_name": tag_name,
                "draft": is_draft,
                "prerelease": is_prerelease,
                "html_url": html_url,
            })

            observation = NormalizedObservation(
                observation_id=str(uuid.uuid4()),
                source_id=self.source_id,
                source_event_id=release_id,
                title=name,
                summary=body[:500] if body else "",
                body_text=body_text,
                content_type="application/json",
                timestamps=timestamps,
                raw_document_ref=raw_doc_id,
                text_length=len(body) if body else 0,
            )

            result.raw_documents.append(raw_doc)
            result.observations.append(observation)

        return result
