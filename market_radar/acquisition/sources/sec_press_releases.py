"""SEC Press Releases adapter.

Feed:  https://www.sec.gov/news/pressreleases.rss

Rules
-----
- Uses Python stdlib XML parser (ElementTree).
- Does NOT scrape individual article bodies.
- Issues exactly one HTTP GET per run.
- Requires a compliant User-Agent via ``MARKET_SIGNAL_SEC_USER_AGENT``
  env var or ``--sec-user-agent`` CLI flag.
- Without a User-Agent the health is ``configuration_required`` and
  no live request is made; replay tests still pass.
- Malformed XML, empty feeds, and missing dates produce auditable
  error states (no silent drop).
"""

from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from market_radar.acquisition.contracts import (
    AcquisitionResult,
    AuthMode,
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

# ── Source contract ──────────────────────────────────────────────────────────

SEC_CONTRACT = SourceContract(
    source_id="sec_press_releases",
    display_name="SEC Press Releases",
    category=SourceCategory.REGULATORY,
    authority="U.S. Securities and Exchange Commission",
    primary_url="https://www.sec.gov/news/pressreleases.rss",
    fallback_urls=[],
    transport=Transport.HTTPS_GET,
    content_type="application/rss+xml",
    auth_mode=AuthMode.USER_AGENT,
    timeout_seconds=30,
    max_response_bytes=5 * 1024 * 1024,
    parser_version="1",
)

ENV_USER_AGENT = "MARKET_SIGNAL_SEC_USER_AGENT"
_REQUIRED_RSS_ITEM_FIELDS = {"title", "link", "guid", "pubDate", "description"}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _resolve_user_agent(cli_user_agent: Optional[str] = None) -> Optional[str]:
    """Return User-Agent from CLI arg, env var, or ``None``."""
    if cli_user_agent:
        return cli_user_agent
    return os.environ.get(ENV_USER_AGENT)


def _parse_rss_date(date_str: str) -> Optional[str]:
    """Parse RFC 822 RSS date to ISO 8601 with timezone, or ``None``."""
    if not date_str:
        return None
    # Try common RSS date formats
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


# ── Core fetch & parse ───────────────────────────────────────────────────────


def _fetch_rss(
    url: str,
    timeout: int,
    max_bytes: int,
    user_agent: Optional[str],
) -> Tuple[Optional[bytes], int, float, str, str]:
    """Fetch RSS feed.  Returns (raw_bytes, http_status, latency_ms, content_type, error)."""
    headers = {}
    if user_agent:
        headers["User-Agent"] = user_agent
    start = time.monotonic()
    try:
        resp = requests.get(url, timeout=timeout, headers=headers)
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


def _parse_rss_items(raw: bytes) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """Parse RSS XML and extract items.  Returns (items, error)."""
    try:
        tree = ET.ElementTree(ET.fromstring(raw))
    except ET.ParseError as exc:
        return [], f"malformed_xml: {exc}"
    root = tree.getroot()
    # RSS 2.0: /rss/channel/item
    items = []
    for item in root.findall(".//item"):
        entry: Dict[str, str] = {}
        for field in _REQUIRED_RSS_ITEM_FIELDS:
            el = item.find(field)
            entry[field] = el.text or "" if el is not None else ""
        items.append(entry)
    if not items:
        return [], "empty_feed_no_items"
    # Check for missing pubDate
    missing_dates = [it.get("guid", "?") for it in items if not it.get("pubDate")]
    if missing_dates:
        return [], f"missing_pubDate_on_items: {missing_dates[:3]}"
    return items, None


# ── Observation generation ───────────────────────────────────────────────────


def _build_observations(
    items: List[Dict[str, str]],
    source_id: str,
    selected_url: str,
    retrieved_at: str,
    content_sha256: str,
    limit: int,
    artifact_path: str,
) -> List[ObservationStub]:
    """Build up to *limit* observations from parsed RSS items."""
    out: List[ObservationStub] = []
    for item in items[:limit]:
        guid = item.get("guid", item.get("link", "unknown"))
        pub_date_iso = _parse_rss_date(item.get("pubDate", ""))
        event_time = pub_date_iso or retrieved_at
        obs_id = deterministic_observation_id(source_id, guid, event_time)
        provenance = {
            "source_id": source_id,
            "selected_url": selected_url,
            "retrieved_at": retrieved_at,
            "content_sha256": content_sha256,
            "raw_artifact_path": artifact_path,
            "record_key": guid,
            "feed_link": item.get("link", ""),
        }
        out.append(ObservationStub(
            observation_id=obs_id,
            source_id=source_id,
            title=item.get("title", ""),
            description=item.get("description", ""),
            event_time=event_time,
            observed_at=retrieved_at,
            raw_provenance=provenance,
            affected_assets=[],
        ))
    return out


# ── Main entry point ─────────────────────────────────────────────────────────


def acquire_sec_press_releases(
    limit: int = 20,
    timeout: Optional[int] = None,
    user_agent: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> AcquisitionResult:
    """Execute one SEC Press Releases acquisition cycle.

    Parameters
    ----------
    limit:
        Maximum observations to emit.
    timeout:
        Per-request timeout in seconds (defaults to contract value).
    user_agent:
        Compliant User-Agent string.  Falls back to env var
        ``MARKET_SIGNAL_SEC_USER_AGENT``.  When neither is set the
        health is ``configuration_required`` and no live request is made.

    Returns
    -------
    AcquisitionResult
    """
    contract = SEC_CONTRACT
    timeout = timeout or contract.timeout_seconds
    source_id = contract.source_id
    retrieved_at = utc_now()

    ua = _resolve_user_agent(user_agent)
    if not ua:
        # No User-Agent configured — cannot make a compliant request
        meta = FetchMetadata(
            source_id=source_id,
            attempted_urls=[],
            selected_url="",
            http_status=0,
            content_type="",
            bytes_received=0,
            latency_ms=0.0,
            retrieved_at=retrieved_at,
            content_sha256="",
            fallback_used=False,
            error_code="configuration_required",
            error_message=f"Set {ENV_USER_AGENT} or pass --sec-user-agent",
        )
        health = SourceHealth.from_metadata(meta, SourceStatus.CONFIGURATION_REQUIRED)
        artifact = RawEvidenceArtifact(
            source_id=source_id,
            relative_path="",
            bytes_written=0,
            content_sha256="",
            content_type="",
            retrieved_at=retrieved_at,
        )
        return AcquisitionResult(
            source_id=source_id,
            contract=contract,
            health=health,
            fetch_metadata=meta,
            artifact=artifact,
            observations=[],
            raw_bytes=None,
            errors=["configuration_required: no User-Agent"],
        )

    # Fetch
    raw, http_status, latency_ms, content_type, error = _fetch_rss(
        contract.primary_url, timeout, contract.max_response_bytes, ua
    )
    attempted_urls = [contract.primary_url]

    # Parse
    items: List[Dict[str, str]] = []
    parse_err: Optional[str] = None
    if raw is not None:
        items, parse_err = _parse_rss_items(raw)

    # Determine health
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
        source_id=source_id,
        attempted_urls=attempted_urls,
        selected_url=contract.primary_url,
        http_status=http_status,
        content_type=content_type,
        bytes_received=len(raw) if raw else 0,
        latency_ms=latency_ms,
        retrieved_at=retrieved_at,
        content_sha256=content_sha256,
        fallback_used=False,
        error_code="" if status == SourceStatus.HEALTHY else (parse_err or error or "unavailable"),
        error_message=error or (parse_err or ""),
    )
    health = SourceHealth.from_metadata(meta, status)

    observations = _build_observations(
        items, source_id, contract.primary_url, retrieved_at,
        content_sha256, limit,
        f"sources/{source_id}/raw_response.xml",
    ) if items else []

    artifact = RawEvidenceArtifact(
        source_id=source_id,
        relative_path=f"sources/{source_id}/raw_response.xml",
        bytes_written=len(raw) if raw else 0,
        content_sha256=content_sha256,
        content_type=content_type,
        retrieved_at=retrieved_at,
    )

    errs: List[str] = []
    if error: errs.append(error)
    if parse_err: errs.append(parse_err)

    return AcquisitionResult(
        source_id=source_id,
        contract=contract,
        health=health,
        fetch_metadata=meta,
        artifact=artifact,
        observations=observations,
        raw_bytes=raw,
        errors=errs,
    )
