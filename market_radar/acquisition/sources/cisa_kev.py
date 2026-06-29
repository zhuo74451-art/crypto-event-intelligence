"""CISA Known Exploited Vulnerabilities (KEV) adapter."""
from __future__ import annotations
import json as _json
import time
from typing import Any, Dict, List, Optional, Tuple
import requests
from market_radar.acquisition.contracts import (
    AcquisitionResult, AuthMode, FetchMetadata, ObservationStub,
    RawEvidenceArtifact, SourceCategory, SourceContract, SourceHealth,
    SourceStatus, Transport, deterministic_observation_id,
    sha256_of_bytes, utc_now,
)

CISA_CONTRACT = SourceContract(
    source_id="cisa_kev",
    display_name="CISA Known Exploited Vulnerabilities",
    category=SourceCategory.SECURITY,
    authority="CISA",
    primary_url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
    fallback_urls=["https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json"],
    transport=Transport.HTTPS_GET,
    content_type="application/json",
    auth_mode=AuthMode.NONE,
    timeout_seconds=30,
    max_response_bytes=10*1024*1024,
    parser_version="1",
)

REQUIRED_TOP_LEVEL = {"title", "catalogVersion", "dateReleased", "count", "vulnerabilities"}
REQUIRED_RECORD_FIELDS = {"cveID", "vendorProject", "product", "vulnerabilityName", "dateAdded", "shortDescription", "requiredAction", "dueDate", "knownRansomwareCampaignUse", "notes"}

def _fetch_url(url, timeout, max_bytes):
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

def _validate_json_structure(raw):
    try:
        data = _json.loads(raw)
    except _json.JSONDecodeError as exc:
        return None, "malformed_json: " + str(exc)
    if not isinstance(data, dict):
        return None, "top_level_not_an_object"
    missing = REQUIRED_TOP_LEVEL - set(data.keys())
    if missing:
        return None, "missing_top_level_keys: " + str(sorted(missing))
    vulns = data.get("vulnerabilities", [])
    if not isinstance(vulns, list):
        return None, "vulnerabilities_not_a_list"
    for i, record in enumerate(vulns):
        if not isinstance(record, dict):
            return None, "vulnerability_" + str(i) + "_not_an_object"
        rec_missing = REQUIRED_RECORD_FIELDS - set(record.keys())
        if rec_missing:
            return None, "vulnerability_" + str(i) + "_missing_fields: " + str(sorted(rec_missing))
    return data, None

def _normalise_date(date_str):
    if date_str and "T" not in date_str:
        return date_str + "T00:00:00+00:00"
    return date_str

def _build_observations(data, source_id, selected_url, retrieved_at, content_sha256, limit, fallback_used, artifact_path):
    vulns = sorted(data.get("vulnerabilities", []), key=lambda v: v.get("dateAdded", ""), reverse=True)[:limit]
    obs_list = []
    for v in vulns:
        cve_id = v.get("cveID", "UNKNOWN")
        vname = v.get("vulnerabilityName", "")
        obs_id = deterministic_observation_id(source_id, cve_id, v.get("dateAdded", ""))
        provenance = {
            "source_id": source_id, "selected_url": selected_url,
            "catalog_version": data.get("catalogVersion", ""),
            "catalog_released_at": data.get("dateReleased", ""),
            "retrieved_at": retrieved_at, "content_sha256": content_sha256,
            "raw_artifact_path": artifact_path, "fallback_used": fallback_used,
            "record_key": cve_id,
        }
        obs_list.append(ObservationStub(
            observation_id=obs_id, source_id=source_id,
            title="CISA KEV: " + vname,
            description=v.get("shortDescription", ""),
            event_time=_normalise_date(v.get("dateAdded", "")),
            observed_at=retrieved_at, raw_provenance=provenance, affected_assets=[],
        ))
    return obs_list

def acquire_cisa_kev(limit=20, timeout=None, output_dir=None, replay_file=None, **kwargs):
    contract = CISA_CONTRACT
    timeout = timeout or contract.timeout_seconds
    source_id = contract.source_id
    retrieved_at = utc_now()
    
    # Replay mode: load from fixture file, zero HTTP
    if replay_file:
        from pathlib import Path as _Path
        p = _Path(replay_file)
        raw = p.read_bytes()
        http_status = 200
        latency_ms = 0.0
        content_type = "application/json"
        error = ""
        selected_url = contract.primary_url
        fallback_used = False
        attempted = [selected_url]
        parsed, parse_err = _validate_json_structure(raw)
        if parsed is None:
            status = SourceStatus.SCHEMA_INVALID
        else:
            status = SourceStatus.HEALTHY
        content_sha256 = sha256_of_bytes(raw)
        _finish_from_replay = True
    else:
        _finish_from_replay = False
        urls_to_try = [contract.primary_url] + contract.fallback_urls
        attempted = []
        raw = None; http_status = 0; latency_ms = 0.0; content_type = ""; error = ""
        selected_url = ""; parsed = None; parse_err = None; fallback_used = False

    if _finish_from_replay:
        meta = FetchMetadata(source_id=source_id,
            attempted_urls=attempted, selected_url=selected_url,
            http_status=http_status, content_type=content_type,
            bytes_received=len(raw) if raw else 0, latency_ms=latency_ms,
            retrieved_at=retrieved_at, content_sha256=content_sha256,
            fallback_used=fallback_used,
            error_code="" if parsed else (parse_err or error or "unavailable"),
            error_message=error or (parse_err or ""))
        health = SourceHealth.from_metadata(meta, status)
        observations = []
        if parsed is not None:
            observations = _build_observations(parsed, source_id, selected_url,
                retrieved_at, content_sha256, limit, fallback_used,
                "sources/" + source_id + "/raw_response.json")
        artifact = RawEvidenceArtifact(source_id=source_id,
            relative_path="sources/" + source_id + "/raw_response.json",
            bytes_written=len(raw) if raw else 0, content_sha256=content_sha256,
            content_type=content_type, retrieved_at=retrieved_at)
        errors = []
        if error: errors.append(error)
        if parse_err: errors.append(parse_err)
        return AcquisitionResult(source_id=source_id, contract=contract, health=health,
            fetch_metadata=meta, artifact=artifact, observations=observations,
            raw_bytes=raw, errors=errors)
    
    # Live mode: HTTP requests
    for url in urls_to_try:
        attempted.append(url)
        raw, http_status, latency_ms, content_type, error = _fetch_url(url, timeout, contract.max_response_bytes)
        selected_url = url
        if url != contract.primary_url:
            fallback_used = True
        if raw is None:
            continue
        parsed, parse_err = _validate_json_structure(raw)
        if parse_err is None:
            break
        if url == urls_to_try[-1]:
            break
    if parsed is None:
        status = SourceStatus.UNAVAILABLE
        if parse_err and "malformed_json" in parse_err:
            status = SourceStatus.SCHEMA_INVALID
        content_sha256 = sha256_of_bytes(raw) if raw else ""
    else:
        content_sha256 = sha256_of_bytes(raw) if raw else ""
        if error:
            status = SourceStatus.UNAVAILABLE
        elif fallback_used:
            status = SourceStatus.DEGRADED
        else:
            status = SourceStatus.HEALTHY
    meta = FetchMetadata(source_id=source_id,
        attempted_urls=attempted, selected_url=selected_url,
        http_status=http_status, content_type=content_type,
        bytes_received=len(raw) if raw else 0, latency_ms=latency_ms,
        retrieved_at=retrieved_at, content_sha256=content_sha256,
        fallback_used=fallback_used,
        error_code="" if parsed else (parse_err or error or "unavailable"),
        error_message=error or (parse_err or ""))
    health = SourceHealth.from_metadata(meta, status)
    observations = []
    if parsed is not None:
        observations = _build_observations(parsed, source_id, selected_url,
            retrieved_at, content_sha256, limit, fallback_used,
            "sources/" + source_id + "/raw_response.json")
    artifact = RawEvidenceArtifact(source_id=source_id,
        relative_path="sources/" + source_id + "/raw_response.json",
        bytes_written=len(raw) if raw else 0, content_sha256=content_sha256,
        content_type=content_type, retrieved_at=retrieved_at)
    errors = []
    if error: errors.append(error)
    if parse_err: errors.append(parse_err)
    return AcquisitionResult(source_id=source_id, contract=contract, health=health,
        fetch_metadata=meta, artifact=artifact, observations=observations,
        raw_bytes=raw, errors=errors)
