#!/usr/bin/env python3
"""One-shot acquisition pilot — runs once, no daemon, no paid APIs, no notifications."""
import argparse
import json
import os
import sys
import time

_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from market_radar.acquisition.contracts import (
    SourceContract, AuthorityTier, SourceRole,
    RawDocument, NormalizedObservation,
    FiveTimestamps, TimestampEvidence, TimestampQuality,
)
from market_radar.acquisition.contracts.timestamps import utc_now
from market_radar.acquisition.evidence.hashing import compute_content_hash


def load_registry():
    from market_radar.acquisition.registry.source_loader import SourceLoader
    from market_radar.acquisition.registry.source_registry import SourceRegistry
    yaml_path = os.path.join(_project_root, "market_radar", "acquisition", "registry", "default_sources.yaml")
    loader = SourceLoader()
    contracts = loader.load_from_yaml(yaml_path)
    registry = SourceRegistry()
    for c in contracts:
        registry.register(c)
    print(f"  Loaded {len(contracts)} source contracts")
    return registry


def run_dry_run_pilot(max_items, output_dir):
    registry = load_registry()
    all_raw, all_obs = [], []
    source_results = {}
    errors = []

    fixture_contracts = [
        SourceContract(source_id="sec-edgar", source_name="SEC EDGAR",
            authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
            roles=(SourceRole.AUTHORITATIVE_EVIDENCE, SourceRole.DISCOVERY),
            primary_method="fixture"),
        SourceContract(source_id="federal-register", source_name="Federal Register",
            authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
            roles=(SourceRole.AUTHORITATIVE_EVIDENCE,),
            primary_method="fixture"),
        SourceContract(source_id="federal-reserve-press", source_name="Fed Press",
            authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
            roles=(SourceRole.AUTHORITATIVE_EVIDENCE,),
            primary_method="fixture"),
        SourceContract(source_id="github-releases", source_name="GitHub Releases",
            authority_tier=AuthorityTier.PRIMARY_OFFICIAL,
            roles=(SourceRole.DISCOVERY,),
            primary_method="fixture"),
    ]

    output_dir = os.path.abspath(output_dir)
    for d in [output_dir, os.path.join(output_dir, "raw"), os.path.join(output_dir, "observations")]:
        os.makedirs(d, exist_ok=True)

    for contract in fixture_contracts:
        sid = contract.source_id
        print(f"\n  [{sid}] Generating fixture observations...")
        now = utc_now()
        source_results[sid] = {"attempted": True, "successful": True, "count": 0}
        for i in range(max_items):
            doc_id = f"fixture-{sid}-{i+1}"
            event_id = f"event-{i+1}"
            raw = RawDocument(
                raw_document_id=doc_id, source_id=sid,
                source_event_id=event_id,
                canonical_url=f"https://fixture.example.com/{sid}/{i+1}",
                retrieved_url=f"https://fixture.example.com/{sid}/{i+1}",
                http_status=200, content_type="application/json",
                encoding="utf-8",
                timestamps=FiveTimestamps(
                    published_at=TimestampEvidence(now, TimestampQuality.EXPLICIT_SOURCE),
                    first_seen_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
                    retrieved_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
                ),
                payload_size=100,
                content_hash=compute_content_hash(json.dumps({"id": event_id}).encode()),
                extraction_status="extracted",
            )
            all_raw.append(raw)
            obs = NormalizedObservation(
                observation_id=doc_id, source_id=sid,
                source_event_id=event_id,
                authority_tier=AuthorityTier.PRIMARY_OFFICIAL.value,
                title=f"Fixture Observation {i+1} from {sid}",
                summary=f"Fixture observation for {sid}",
                body_text=f"This is fixture observation {i+1}.",
                language="en",
                timestamps=FiveTimestamps(
                    published_at=TimestampEvidence(now, TimestampQuality.EXPLICIT_SOURCE),
                    first_seen_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
                    retrieved_at=TimestampEvidence(now, TimestampQuality.RETRIEVAL_ONLY),
                ),
                raw_document_ref=doc_id, content_hash=raw.content_hash,
                extraction_quality="complete",
            )
            all_obs.append(obs)
            source_results[sid]["count"] += 1
        print(f"    Generated {source_results[sid]['count']} observations")

    manifest = {
        "pilot_version": "1.0.0", "dry_run": True,
        "mode": "knowledge_as_known_then",
        "generated_at": utc_now().isoformat(),
        "sources_attempted": len(fixture_contracts),
        "sources_successful": sum(1 for s in source_results.values() if s["successful"]),
        "total_raw_documents": len(all_raw),
        "total_observations": len(all_obs),
        "source_results": source_results,
        "errors": errors,
        "paid_apis_used": False,
        "background_processes": False,
        "notifications_sent": False,
        "archive_services_used": False,
        "credentials_used": False,
    }
    for raw in all_raw:
        p = os.path.join(output_dir, "raw", f"{raw.raw_document_id}.json")
        with open(p, "w") as f:
            json.dump(raw.to_dict(), f, indent=2, default=str)
    for obs in all_obs:
        p = os.path.join(output_dir, "observations", f"{obs.observation_id}.json")
        with open(p, "w") as f:
            json.dump(obs.to_dict(), f, indent=2, default=str)
    with open(os.path.join(output_dir, "pilot_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"\n  Pilot manifest saved")
    return manifest


def run_live_pilot(max_items, output_dir, no_notify, no_archive):
    print("  Live mode not fully implemented — falling back to dry-run")
    return run_dry_run_pilot(max_items, output_dir)


def main():
    parser = argparse.ArgumentParser(description="Run one-shot acquisition pilot")
    parser.add_argument("--output-dir", default="artifacts/acquisition_pilot_v1")
    parser.add_argument("--no-notify", action="store_true", default=True)
    parser.add_argument("--no-archive-service", action="store_true", default=True)
    parser.add_argument("--max-items-per-source", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("Acquisition Pilot v1 — One-Shot Run")
    print("=" * 60)
    print(f"  Mode: {'DRY RUN (fixtures)' if args.dry_run else 'LIVE'}")
    print(f"  Output: {args.output_dir}")
    start = time.time()
    if args.dry_run:
        manifest = run_dry_run_pilot(args.max_items_per_source, args.output_dir)
    else:
        manifest = run_live_pilot(args.max_items_per_source, args.output_dir,
                                  args.no_notify, args.no_archive_service)
    elapsed = time.time() - start
    print(f"\n  Sources attempted: {manifest['sources_attempted']}")
    print(f"  Sources successful: {manifest['sources_successful']}")
    print(f"  Raw documents: {manifest['total_raw_documents']}")
    print(f"  Observations: {manifest['total_observations']}")
    print(f"  Errors: {len(manifest['errors'])}")
    print(f"  Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
