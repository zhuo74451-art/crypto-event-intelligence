"""BLS Public Data API v1 adapter."""

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

SOURCE_ID = "bls_labor_statistics"

BLS_CONTRACT = SourceContract(
    source_id=SOURCE_ID,
    display_name="BLS Labor Statistics",
    category=SourceCategory.MACRO,
    authority="U.S. Bureau of Labor Statistics",
    primary_url="https://api.bls.gov/publicAPI/v1/timeseries/data/",
    fallback_urls=[],
    transport=Transport.HTTPS_POST,
    content_type="application/json",
    timeout_seconds=30,
    max_response_bytes=5 * 1024 * 1024,
    parser_version="1",
)

DEFAULT_SERIES = ["CUUR0000SA0", "LNS14000000", "CES0000000001"]


def _fetch_bls(series_ids, timeout, max_bytes):
    payload = _json.dumps({
        "seriesid": series_ids,
        "startyear": "2024",
        "endyear": "2026",
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    start = time.monotonic()
    try:
        resp = requests.post(
            BLS_CONTRACT.primary_url,
            data=payload,
            headers=headers,
            timeout=timeout,
        )
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


def _validate_bls_response(raw):
    try:
        data = _json.loads(raw)
    except _json.JSONDecodeError as exc:
        return None, "malformed_json: " + str(exc)
    if not isinstance(data, dict):
        return None, "top_level_not_an_object"
    status = data.get("status", "")
    if status != "REQUEST_SUCCEEDED":
        return None, "bls_status_error: " + status + " - " + data.get("message", "")
    results = data.get("Results", {})
    if not isinstance(results, dict):
        return None, "Results_not_an_object"
    series = results.get("series", [])
    if not isinstance(series, list):
        return None, "series_not_a_list"
    if not series:
        return None, "empty_series_list"
    return data, None


def _build_observations(data, source_id, selected_url, retrieved_at, content_sha256, limit, artifact_path):
    obs_list = []
    results = data.get("Results", {})
    series_list = results.get("series", [])
    count = 0
    for series in series_list:
        sid = series.get("seriesID", "UNKNOWN")
        raw_data = series.get("data", [])
        if not raw_data:
            continue
        sorted_data = sorted(
            raw_data,
            key=lambda x: (x.get("year", ""), x.get("period", "")),
            reverse=True,
        )
        for record in sorted_data[:limit]:
            year = record.get("year", "")
            period = record.get("period", "")
            period_name = record.get("periodName", "")
            value = record.get("value", "")
            footnotes = record.get("footnotes", [])
            if period and period.startswith("M"):
                month = period[1:]
                event_time = f"{year}-{month.zfill(2)}-01T00:00:00+00:00"
            elif period == "Q01":
                event_time = f"{year}-01-01T00:00:00+00:00"
            elif period == "Q02":
                event_time = f"{year}-04-01T00:00:00+00:00"
            elif period == "Q03":
                event_time = f"{year}-07-01T00:00:00+00:00"
            elif period == "Q04":
                event_time = f"{year}-10-01T00:00:00+00:00"
            else:
                event_time = f"{year}-01-01T00:00:00+00:00"
            record_key = f"{sid}:{year}:{period}"
            obs_id = deterministic_observation_id(source_id, record_key, event_time)
            provenance = {
                "source_id": source_id, "selected_url": selected_url,
                "retrieved_at": retrieved_at, "content_sha256": content_sha256,
                "raw_artifact_path": artifact_path, "record_key": record_key,
                "series_id": sid, "year": year, "period": period,
                "period_name": period_name, "value": value,
                "footnotes": str(footnotes),
            }
            obs_list.append(ObservationStub(
                observation_id=obs_id, source_id=source_id,
                title=f"BLS {sid}: {period_name} {year} = {value}",
                description=f"Series {sid} ({period_name} {year}): {value}",
                event_time=event_time, observed_at=retrieved_at,
                raw_provenance=provenance, affected_assets=[],
            ))
            count += 1
            if count >= limit:
                break
        if count >= limit:
            break
    return obs_list


def acquire_bls(limit=20, timeout=None, series_ids=None, output_dir=None, replay_file=None, **kwargs):
    timeout_val = timeout or BLS_CONTRACT.timeout_seconds
    series = series_ids or DEFAULT_SERIES
    retrieved_at = utc_now()

    if replay_file:
        from pathlib import Path as _Path
        p = _Path(replay_file)
        raw = p.read_bytes()
        http_status = 200
        latency_ms = 0.0
        content_type = "application/json"
        error = ""
    else:
        raw, http_status, latency_ms, content_type, error = _fetch_bls(
            series, timeout_val, BLS_CONTRACT.max_response_bytes
        )

    content_sha256 = sha256_of_bytes(raw) if raw else ""
    parsed = None
    parse_err = None
    if raw is not None:
        parsed, parse_err = _validate_bls_response(raw)

    if parsed is None:
        status = SourceStatus.UNAVAILABLE
        if parse_err and ("malformed_json" in parse_err or "bls_status_error" in parse_err):
            status = SourceStatus.SCHEMA_INVALID
    elif error:
        status = SourceStatus.UNAVAILABLE
    else:
        status = SourceStatus.HEALTHY

    meta = FetchMetadata(
        source_id=SOURCE_ID, attempted_urls=[BLS_CONTRACT.primary_url],
        selected_url=BLS_CONTRACT.primary_url,
        http_status=http_status, content_type=content_type,
        bytes_received=len(raw) if raw else 0, latency_ms=latency_ms,
        retrieved_at=retrieved_at, content_sha256=content_sha256,
        fallback_used=False,
        error_code="" if status == SourceStatus.HEALTHY else (parse_err or error or "unavailable"),
        error_message=error or (parse_err or ""),
    )

    health = SourceHealth.from_metadata(meta, status)

    observations = _build_observations(
        parsed, SOURCE_ID, BLS_CONTRACT.primary_url, retrieved_at,
        content_sha256, limit,
        f"sources/{SOURCE_ID}/raw_response.json",
    ) if parsed else []

    artifact = RawEvidenceArtifact(
        source_id=SOURCE_ID,
        relative_path=f"sources/{SOURCE_ID}/raw_response.json",
        bytes_written=len(raw) if raw else 0,
        content_sha256=content_sha256,
        content_type=content_type,
        retrieved_at=retrieved_at,
    )

    errs = []
    if error: errs.append(error)
    if parse_err: errs.append(parse_err)

    return AcquisitionResult(
        source_id=SOURCE_ID, contract=BLS_CONTRACT,
        health=health, fetch_metadata=meta, artifact=artifact,
        observations=observations, raw_bytes=raw, errors=errs,
    )
