"""Congress.gov RSS source family adapter."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from datetime import datetime
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


FEED_DEFS: List[Dict[str, Any]] = [
    {"feed_id": "presented_to_president", "display_name": "Congress to President", "url": "https://www.congress.gov/rss/presented-to-president.xml"},
    {"feed_id": "house_floor_today", "display_name": "House Floor Today", "url": "https://www.congress.gov/rss/house-floor-today.xml"},
    {"feed_id": "senate_floor_today", "display_name": "Senate Floor Today", "url": "https://www.congress.gov/rss/senate-floor-today.xml"},
]

SOURCE_ID = "congress_legislation_activity"

CONGRESS_CONTRACT = SourceContract(
    source_id=SOURCE_ID,
    display_name="Congress.gov Legislation Activity",
    category=SourceCategory.LEGISLATIVE,
    authority="U.S. Congress",
    primary_url=FEED_DEFS[0]["url"],
    fallback_urls=[],
    transport=Transport.HTTPS_GET,
    content_type="application/rss+xml",
    timeout_seconds=30,
    max_response_bytes=5 * 1024 * 1024,
    parser_version="1",
)

_REQUIRED_RSS_ITEM_FIELDS = {"title", "link", "guid", "pubDate", "description"}


def _parse_rss_date(date_str):
    if not date_str:
        return None
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.isoformat()
        except ValueError:
            continue
    return None


def _fetch_feed(url, timeout, max_bytes):
    start = time.monotonic()
    try:
        resp = requests.get(url, timeout=timeout)
        latency_ms = (time.monotonic() - start) * 1000.0
        if resp.status_code >= 400:
            return None, resp.status_code, latency_ms, resp.headers.get("Content-Type", ""), ""
        body = resp.content[:max_bytes]
        return body, resp.status_code, latency_ms, resp.headers.get("Content-Type", ""), ""
    except requests.exceptions.Timeout:
        latency_ms = (time.monotonic() - start) * 1000.0
        return None, 0, latency_ms, "", "timeout"
    except requests.exceptions.RequestException as exc:
        latency_ms = (time.monotonic() - start) * 1000.0
        return None, 0, latency_ms, "", str(exc)


def _parse_rss_items(raw):
    try:
        tree = ET.ElementTree(ET.fromstring(raw))
    except ET.ParseError as exc:
        return [], f"malformed_xml: {exc}"
    root = tree.getroot()
    items = []
    for item in root.findall(".//item"):
        entry = {}
        for field in _REQUIRED_RSS_ITEM_FIELDS:
            el = item.find(field)
            entry[field] = el.text or "" if el is not None else ""
        items.append(entry)
    if not items:
        return [], "empty_feed_no_items"
    missing_dates = [it.get("guid", "?") for it in items if not it.get("pubDate")]
    if missing_dates:
        return [], f"missing_pubDate_on_items: {missing_dates[:3]}"
    return items, None


def _build_observations(items, source_id, feed_id, feed_url, retrieved_at, content_sha256, limit, artifact_path):
    out = []
    for item in items[:limit]:
        guid = item.get("guid", item.get("link", "unknown"))
        pub_date_iso = _parse_rss_date(item.get("pubDate", ""))
        event_time = pub_date_iso or retrieved_at
        obs_id = deterministic_observation_id(source_id, f"{feed_id}:{guid}", event_time)
        provenance = {
            "source_id": source_id, "feed_id": feed_id, "feed_url": feed_url,
            "selected_url": feed_url, "retrieved_at": retrieved_at,
            "content_sha256": content_sha256, "raw_artifact_path": artifact_path,
            "record_key": f"{feed_id}:{guid}", "feed_link": item.get("link", ""),
        }
        out.append(ObservationStub(
            observation_id=obs_id, source_id=source_id,
            title=f"[{feed_id}] {item.get('title', '')}",
            description=item.get("description", ""),
            event_time=event_time, observed_at=retrieved_at,
            raw_provenance=provenance, affected_assets=[],
        ))
    return out


def acquire_congress(limit=20, timeout=None, output_dir=None):
    timeout_val = timeout or CONGRESS_CONTRACT.timeout_seconds
    retrieved_at = utc_now()

    all_results = []
    all_observations = []
    overall_errors = []

    for feed_def in FEED_DEFS:
        feed_id = feed_def["feed_id"]
        url = feed_def["url"]

        raw, http_status, latency_ms, content_type, error = _fetch_feed(
            url, timeout_val, CONGRESS_CONTRACT.max_response_bytes
        )

        items = []
        parse_err = None
        if raw is not None:
            items, parse_err = _parse_rss_items(raw)

        content_sha256 = sha256_of_bytes(raw) if raw else ""

        if raw is None:
            status = SourceStatus.UNAVAILABLE
        elif parse_err and "malformed_xml" in parse_err:
            status = SourceStatus.SCHEMA_INVALID
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
            error_code="" if status == SourceStatus.HEALTHY else (parse_err or error or "unavailable"),
            error_message=error or (parse_err or ""),
        )

        health = SourceHealth.from_metadata(meta, status)

        feed_obs = _build_observations(
            items, SOURCE_ID, feed_id, url, retrieved_at,
            content_sha256, limit,
            f"sources/{SOURCE_ID}/{feed_id}_raw_response.xml",
        ) if items else []

        artifact = RawEvidenceArtifact(
            source_id=SOURCE_ID,
            relative_path=f"sources/{SOURCE_ID}/{feed_id}_raw_response.xml",
            bytes_written=len(raw) if raw else 0,
            content_sha256=content_sha256,
            content_type=content_type,
            retrieved_at=retrieved_at,
        )

        errs = []
        if error:
            errs.append(error)
        if parse_err:
            errs.append(parse_err)

        all_results.append(AcquisitionResult(
            source_id=SOURCE_ID, contract=CONGRESS_CONTRACT,
            health=health, fetch_metadata=meta, artifact=artifact,
            observations=feed_obs, raw_bytes=raw, errors=errs,
        ))
        all_observations.extend(feed_obs)
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

    first = all_results[0]
    merged_raw = b""
    for r in all_results:
        if r.raw_bytes is not None:
            merged_raw += r.raw_bytes
    if merged_raw == b"":
        merged_raw = None

    overall_health = SourceHealth(
        source_id=SOURCE_ID, status=overall_status,
        attempted_urls=[fd["url"] for fd in FEED_DEFS],
        selected_url=",".join([fd["url"] for fd in FEED_DEFS]),
        http_status=0, content_type="application/rss+xml",
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
        content_type="application/rss+xml",
        retrieved_at=retrieved_at,
    )

    return AcquisitionResult(
        source_id=SOURCE_ID, contract=CONGRESS_CONTRACT,
        health=overall_health, fetch_metadata=first.fetch_metadata,
        artifact=overall_artifact, observations=all_observations,
        raw_bytes=merged_raw, errors=overall_errors,
    )
