"""GitHub Releases API adapter."""

from __future__ import annotations

import json as _json
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from market_radar.acquisition.contracts import (
    AcquisitionResult,
    FetchMetadata,
    ObservationStub,
    RawEvidenceArtifact,
    SourceCategory,
    SourceContract,
    SourceHealth,
    SourceStatus,
    Transport,
    deterministic_observation_id,
    sha256_of_bytes,
    utc_now,
)

SOURCE_ID = "github_releases"

RELEASES_CONTRACT = SourceContract(
    source_id=SOURCE_ID,
    display_name="GitHub Releases (configured repos)",
    category=SourceCategory.SOFTWARE_RELEASE,
    authority="GitHub",
    primary_url="https://api.github.com/repos/bitcoin/bitcoin/releases",
    fallback_urls=[],
    transport=Transport.HTTPS_GET,
    content_type="application/json",
    timeout_seconds=30,
    max_response_bytes=5 * 1024 * 1024,
    parser_version="1",
)

DEFAULT_REPOS = [
    "bitcoin/bitcoin",
    "ethereum/go-ethereum",
]


def _fetch_releases(repo, timeout, max_bytes):
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {"Accept": "application/vnd.github.v3+json"}
    start = time.monotonic()
    try:
        resp = requests.get(url, timeout=timeout, headers=headers)
        latency_ms = (time.monotonic() - start) * 1000.0
        body = resp.content[:max_bytes]
        return body, resp.status_code, latency_ms, resp.headers.get("Content-Type", ""), "", dict(resp.headers)
    except requests.exceptions.Timeout:
        latency_ms = (time.monotonic() - start) * 1000.0
        return None, 0, latency_ms, "", "timeout", {}
    except requests.exceptions.RequestException as exc:
        latency_ms = (time.monotonic() - start) * 1000.0
        return None, 0, latency_ms, "", str(exc), {}


def _validate_releases_response(raw):
    try:
        data = _json.loads(raw)
    except _json.JSONDecodeError as exc:
        return None, "malformed_json: " + str(exc)
    if not isinstance(data, list):
        return None, "response_not_a_list"
    return data, None


def _build_observations(data, source_id, repo, selected_url, retrieved_at, content_sha256, limit, artifact_path, rate_limit_headers):
    obs_list = []
    count = 0
    for release in data:
        if release.get("draft", False):
            continue
        tag = release.get("tag_name", "UNKNOWN")
        name = release.get("name", "") or tag
        published_at = release.get("published_at", "")
        updated_at = release.get("updated_at", "")
        html_url = release.get("html_url", "")
        prerelease = release.get("prerelease", False)
        release_id = str(release.get("id", ""))

        event_time = published_at or updated_at
        if not event_time:
            continue

        record_key = f"{repo}:{release_id}"
        obs_id = deterministic_observation_id(source_id, record_key, event_time)
        provenance = {
            "source_id": source_id, "selected_url": selected_url,
            "retrieved_at": retrieved_at, "content_sha256": content_sha256,
            "raw_artifact_path": artifact_path, "record_key": record_key,
            "repo": repo, "tag": tag, "release_id": release_id,
            "html_url": html_url, "prerelease": str(prerelease),
            "published_at": published_at, "updated_at": updated_at,
            "x_ratelimit_limit": rate_limit_headers.get("X-RateLimit-Limit", ""),
            "x_ratelimit_remaining": rate_limit_headers.get("X-RateLimit-Remaining", ""),
            "x_ratelimit_reset": rate_limit_headers.get("X-RateLimit-Reset", ""),
        }
        obs_list.append(ObservationStub(
            observation_id=obs_id, source_id=source_id,
            title=f"Release {repo}: {tag}",
            description=f"{repo} release {tag}: {name} (prerelease={prerelease})",
            event_time=event_time, observed_at=retrieved_at,
            raw_provenance=provenance, affected_assets=[],
        ))
        count += 1
        if count >= limit:
            break
    return obs_list


def acquire_github_releases(limit=20, timeout=None, repos=None, output_dir=None):
    timeout_val = timeout or RELEASES_CONTRACT.timeout_seconds
    repo_list = repos or DEFAULT_REPOS
    retrieved_at = utc_now()

    all_results = []
    all_observations = []
    overall_errors = []

    for repo in repo_list:
        url = f"https://api.github.com/repos/{repo}/releases"
        raw, http_status, latency_ms, content_type, error, resp_headers = _fetch_releases(
            repo, timeout_val, RELEASES_CONTRACT.max_response_bytes
        )

        content_sha256 = sha256_of_bytes(raw) if raw else ""
        parsed = None
        parse_err = None
        if raw is not None:
            parsed, parse_err = _validate_releases_response(raw)

        if raw is None:
            status = SourceStatus.UNAVAILABLE
        elif parse_err and "malformed_json" in parse_err:
            status = SourceStatus.SCHEMA_INVALID
        elif 403 == http_status:
            status = SourceStatus.UNAVAILABLE
        elif 404 == http_status:
            status = SourceStatus.UNAVAILABLE
        elif 429 == http_status:
            status = SourceStatus.UNAVAILABLE
        elif parse_err:
            status = SourceStatus.UNAVAILABLE
        elif error:
            status = SourceStatus.UNAVAILABLE
        else:
            status = SourceStatus.HEALTHY

        meta = FetchMetadata(
            source_id=SOURCE_ID, attempted_urls=[url], selected_url=url,
            http_status=http_status, content_type=content_type,
            bytes_received=len(raw) if raw else 0, latency_ms=latency_ms,
            retrieved_at=retrieved_at, content_sha256=content_sha256,
            fallback_used=False,
            error_code="" if status == SourceStatus.HEALTHY else (parse_err or error or f"http_{http_status}"),
            error_message=error or (parse_err or ""),
        )

        health = SourceHealth.from_metadata(meta, status)

        releases = _build_observations(
            parsed, SOURCE_ID, repo, url, retrieved_at,
            content_sha256, limit,
            f"sources/{SOURCE_ID}/{repo.replace('/', '_')}_raw_response.json",
            resp_headers,
        ) if parsed and isinstance(parsed, list) else []

        artifact = RawEvidenceArtifact(
            source_id=SOURCE_ID,
            relative_path=f"sources/{SOURCE_ID}/{repo.replace('/', '_')}_raw_response.json",
            bytes_written=len(raw) if raw else 0,
            content_sha256=content_sha256,
            content_type=content_type,
            retrieved_at=retrieved_at,
        )

        errs = []
        if error: errs.append(error)
        if parse_err: errs.append(parse_err)

        all_results.append(AcquisitionResult(
            source_id=SOURCE_ID, contract=RELEASES_CONTRACT,
            health=health, fetch_metadata=meta, artifact=artifact,
            observations=releases, raw_bytes=raw, errors=errs,
        ))
        all_observations.extend(releases)
        overall_errors.extend(errs)

    statuses = [r.health.status for r in all_results]
    if all(s == SourceStatus.HEALTHY for s in statuses):
        overall_status = SourceStatus.HEALTHY
    elif any(s == SourceStatus.SCHEMA_INVALID for s in statuses):
        overall_status = SourceStatus.SCHEMA_INVALID
    elif any(s == SourceStatus.UNAVAILABLE for s in statuses):
        overall_status = SourceStatus.UNAVAILABLE
    else:
        overall_status = SourceStatus.DEGRADED

    first = all_results[0] if all_results else None
    merged_raw = b""
    for r in all_results:
        if r.raw_bytes is not None:
            merged_raw += r.raw_bytes
    if merged_raw == b"":
        merged_raw = None

    overall_health = SourceHealth(
        source_id=SOURCE_ID, status=overall_status,
        attempted_urls=[f"https://api.github.com/repos/{r}/releases" for r in repo_list],
            selected_url=",".join([f"https://api.github.com/repos/{r}/releases" for r in repo_list]),
        http_status=0, content_type="application/json",
        bytes_received=sum(r.health.bytes_received for r in all_results),
        latency_ms=sum(r.health.latency_ms for r in all_results),
        retrieved_at=retrieved_at,
        content_sha256=sha256_of_bytes(merged_raw) if merged_raw else "",
        fallback_used=False,
        error_code="" if overall_status == SourceStatus.HEALTHY else ",".join(overall_errors),
        error_message="; ".join(overall_errors) if overall_errors else "",
    )

    overall_artifact = RawEvidenceArtifact(
        source_id=SOURCE_ID,
        relative_path=f"sources/{SOURCE_ID}/",
        bytes_written=sum(r.artifact.bytes_written for r in all_results),
        content_sha256=overall_health.content_sha256,
        content_type="application/json",
        retrieved_at=retrieved_at,
    )

    return AcquisitionResult(
        source_id=SOURCE_ID, contract=RELEASES_CONTRACT,
        health=overall_health,
        fetch_metadata=first.fetch_metadata if first else FetchMetadata(source_id=SOURCE_ID),
        artifact=overall_artifact, observations=all_observations,
        raw_bytes=merged_raw, errors=overall_errors,
    )
