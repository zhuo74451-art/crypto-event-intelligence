"""Pilot runner — orchestrates source acquisition and output generation.

This module conforms to ``RunnerProtocol`` so it can be executed via
``market_radar.operations.run_once.run_once``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from market_radar.acquisition.contracts import (
    AcquisitionResult,
    ObservationStub,
)
from market_radar.acquisition.evidence import build_evidence_entries
from market_radar.acquisition.storage import (
    write_evidence_manifest,
    write_fetch_metadata,
    write_observations,
    write_raw_evidence,
    write_run_manifest,
    write_source_health,
    write_telemetry,
)
from market_radar.operations.runner_protocol import InjectedRunner
from market_radar.operations.run_once import run_once
from market_radar.shared.models import (
    DataQuality,
    DataSourceType,
    EvidenceLink,
    Observation,
    ObservationStatus,
    sha256_short,
)


# Source registry — maps source_id to acquisition function
SOURCE_REGISTRY: Dict[str, Any] = {}


def _import_sources():
    """Lazy-import to avoid circular dependencies."""
    from market_radar.acquisition.sources.cisa_kev import acquire_cisa_kev
    from market_radar.acquisition.sources.sec_press_releases import (
        acquire_sec_press_releases,
    )
    from market_radar.acquisition.sources.congress import acquire_congress
    SOURCE_REGISTRY["cisa"] = acquire_cisa_kev
    SOURCE_REGISTRY["sec"] = acquire_sec_press_releases
    SOURCE_REGISTRY["congress"] = acquire_congress


def run_pilot(context: dict[str, Any]) -> dict[str, Any]:
    """Execute a Pilot acquisition run.

    Expected context keys:
    - sources: list of source IDs (e.g. ``["cisa", "sec"]``)
    - limit: max observations per source
    - timeout: per-request timeout
    - sec_user_agent: User-Agent for SEC (optional)
    - output_dir: output directory path (string)
    - mode: ``"replay"`` or ``"live"``
    """
    _import_sources()

    config = context.get("config", {})
    run_id = context.get("run_id", "unknown")
    started_at = context.get("started_at", datetime.now(timezone.utc).isoformat())
    mode = config.get("mode", "replay")
    source_ids: List[str] = config.get("sources", ["cisa", "sec"])
    limit = config.get("limit", 20)
    timeout = config.get("timeout")
    sec_user_agent = config.get("sec_user_agent")
    output_dir_str = config.get("output_dir", "")

    output_root = Path(output_dir_str) if output_dir_str else Path.cwd() / "results" / "source_evidence_pilot" / run_id

    results: List[AcquisitionResult] = []
    errors: List[str] = []
    total_observations = 0

    output_root.mkdir(parents=True, exist_ok=True)
    write_telemetry(output_root, "run_started", {"run_id": run_id, "mode": mode, "sources": source_ids})

    for sid in source_ids:
        acquire_fn = SOURCE_REGISTRY.get(sid)
        if not acquire_fn:
            errors.append(f"unknown_source: {sid}")
            continue

        write_telemetry(output_root, "source_acquisition_started", {"source_id": sid})
        try:
            kwargs = {"limit": limit, "timeout": timeout}
            if sid == "sec":
                kwargs["user_agent"] = sec_user_agent
            result = acquire_fn(**kwargs)
            results.append(result)
            total_observations += len(result.observations)

            # Write raw evidence bytes
            write_raw_evidence(output_root, result.source_id, result.raw_bytes, result.artifact)

            # Write fetch metadata
            write_fetch_metadata(output_root, result.fetch_metadata.to_dict())

            # Write source health
            write_source_health(output_root, result.health.to_dict())

            # Convert ObservationStub to full Observation before persisting
            observations = [
                observation_stub_to_observation(s)
                for s in result.observations
            ]

            # Write observations (as Observation dicts)
            if observations:
                write_observations(output_root, observations)

            # Build and write evidence manifest
            entries = build_evidence_entries(
                result.source_id,
                result.observations,
                result.artifact.relative_path,
                result.artifact.content_sha256,
            )
            if entries:
                write_evidence_manifest(output_root, entries)

            write_telemetry(output_root, "source_acquisition_completed", {
                "source_id": sid,
                "status": result.health.status.value,
                "observations": len(result.observations),
                "errors": len(result.errors),
            })

            if result.errors:
                errors.extend(result.errors)
        except Exception as exc:
            errors.append(f"{sid}_exception: {exc}")
            write_telemetry(output_root, "source_acquisition_failed", {
                "source_id": sid,
                "error": str(exc),
            })

    completed_at = datetime.now(timezone.utc).isoformat()
    status = "ok" if not errors else "degraded" if len(errors) < len(source_ids) else "failed"

    write_run_manifest(output_root, run_id, source_ids, started_at, completed_at, status)
    write_telemetry(output_root, "run_completed", {
        "run_id": run_id,
        "status": status,
        "total_observations": total_observations,
        "sources_attempted": len(source_ids),
        "sources_with_errors": len(errors),
    })

    return {
        "status": status,
        "run_id": run_id,
        "output_dir": str(output_root),
        "total_observations": total_observations,
        "source_ids": source_ids,
        "errors": errors,
        "started_at": started_at,
        "completed_at": completed_at,
    }




def observation_stub_to_observation(
    stub: ObservationStub,
    data_quality: DataQuality = DataQuality.UNVERIFIED,
    ingestion_status: ObservationStatus = ObservationStatus.RAW,
) -> Observation:
    """Convert an ``ObservationStub`` to a full ``Observation``.

    Source-evidence fields from the acquisition adapter are preserved in
    ``raw_provenance``, ``evidence``, ``source_refs``, and
    ``normalized_payload`` so the existing ``shared.models.Observation``
    contract is satisfied without modifying that module.
    """
    # Build evidence links from stub provenance
    evidence_links: list[EvidenceLink] = []
    rp = stub.raw_provenance
    if rp.get("content_sha256"):
        evidence_links.append(EvidenceLink(
            ref=sha256_short(rp["content_sha256"]),
            source=stub.source_id,
            timestamp=stub.observed_at,
            description=f"Raw evidence SHA-256: {rp['content_sha256'][:16]}...",
            ref_type="observation",
        ))
    if rp.get("selected_url"):
        evidence_links.append(EvidenceLink(
            ref=sha256_short(rp["selected_url"]),
            source=stub.source_id,
            timestamp=stub.observed_at,
            description=f"Source URL: {rp['selected_url']}",
            ref_type="observation",
        ))
    if rp.get("catalog_version"):
        evidence_links.append(EvidenceLink(
            ref=rp.get("catalog_version", ""),
            source=stub.source_id,
            timestamp=stub.observed_at,
            description=f"Catalog version: {rp.get('catalog_version', '')}",
            ref_type="observation",
        ))

    # Construct observation fingerprint (source-specific dedup)
    assets_str = ",".join(sorted(stub.affected_assets)) if stub.affected_assets else ""
    fp_raw = f"{stub.source_id}:{stub.title}:{assets_str}"
    observation_fingerprint = sha256_short(fp_raw, n=12)

    # Source refs from provenance
    source_refs = [rp.get("selected_url", ""), rp.get("raw_artifact_path", "")]
    source_refs = [s for s in source_refs if s]

    return Observation(
        observation_id=stub.observation_id,
        source=stub.source_id,
        source_type=DataSourceType.FREE_PUBLIC_API,
        observed_at=stub.observed_at,
        event_time=stub.event_time,
        affected_assets=list(stub.affected_assets),
        normalized_payload={
            "title": stub.title,
            "description": stub.description,
            "event_time": stub.event_time,
        },
        raw_provenance=dict(stub.raw_provenance),
        evidence=evidence_links,
        data_quality=data_quality,
        observation_fingerprint=observation_fingerprint,
        event_dedup_key=observation_fingerprint,
        ingestion_status=ingestion_status,
        source_refs=source_refs,
        risk_notes=[],
    )


def create_pilot_runner(
    sources: Optional[List[str]] = None,
    limit: int = 20,
    timeout: Optional[int] = None,
    sec_user_agent: Optional[str] = None,
    output_dir: Optional[str] = None,
    mode: str = "replay",
) -> InjectedRunner:
    """Create a ``RunnerProtocol``-compliant runner for the Pilot."""
    config = {
        "sources": sources or ["cisa", "sec"],
        "limit": limit,
        "timeout": timeout,
        "sec_user_agent": sec_user_agent,
        "output_dir": output_dir or "",
        "mode": mode,
    }
    return InjectedRunner(
        label="SourceEvidencePilot",
        fn=lambda ctx: run_pilot({**ctx, "config": {**ctx.get("config", {}), **config}}),
    )
