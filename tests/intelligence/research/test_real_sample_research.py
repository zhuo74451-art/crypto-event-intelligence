#!/usr/bin/env python3
"""
Real Sample Integration Test — runs the pipeline with ≥30 real macro events
from Lane A. Per §39, this is a temporary real integration sample.
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
SAMPLE_LABEL = "temporary_real_integration_sample"


def run_real_sample(events_limit: int = 100, claims_target: int = 200):
    """Load real events, run pipeline, report results."""
    sys.path.insert(0, PROJECT_ROOT)

    from market_radar.intelligence.integration.adapters.lane_a_adapter import (
        load_lane_a_events, events_to_claims, get_event_summary,
    )
    from market_radar.intelligence.research.evidence_graph import EvidenceGraph, EvidenceNode, EvidenceEdge
    from market_radar.intelligence.research.conflict_engine import ConflictEngine
    from market_radar.intelligence.research.candidate_compiler import CandidateCompiler
    from market_radar.intelligence.research.contracts import (
        ResearchClaimV1, EvidenceEdgeV1, ResearchDossierV1, _utc_now,
    )
    from market_radar.intelligence.research.failure_registry import FailureRegistry

    print(f"[real-sample] Loading {events_limit} real events from Lane A...")
    events = load_lane_a_events(limit=events_limit)
    summary = get_event_summary(events)
    print(f"[real-sample] Summary: {json.dumps(summary, indent=2)}")

    print(f"[real-sample] Generating claims...")
    claims = events_to_claims(events, max_claims=claims_target)
    print(f"[real-sample] Generated {len(claims)} claims")

    # Build evidence edges from real events
    edges = []
    for i, claim in enumerate(claims):
        edge = EvidenceEdgeV1(
            claim_id=claim.claim_id,
            evidence_role="supporting" if claim.claim_status in ("supported", "observed") else "opposing",
            source_lane="lane_a",
            source_artifact_path=f"macro_release_events_v1.jsonl",
            source_record_id=f"event_{i % len(events) if events else i}",
            observed_at_utc=_utc_now(),
            available_at_utc=_utc_now(),
            evidence_type="macro_event",
            supports=claim.claim_status in ("supported", "observed"),
            contradicts=claim.claim_status in ("contradicted",),
            qualifies=claim.claim_status == "contested",
        )
        edges.append(edge)

    # Build evidence graph
    graph = EvidenceGraph()
    for claim in claims[:50]:  # Limit graph nodes for performance
        node = EvidenceNode(
            node_type="research_claim",
            content_key=claim.claim_key or claim.claim_id,
            label=f"{claim.subject} → {claim.object}",
            source_lane="lane_e",
            properties={"claim_id": claim.claim_id, "status": claim.claim_status},
        )
        graph.add_node(node)

    # Detect conflicts
    engine = ConflictEngine()
    conflicts = engine.process_claims(claims)
    print(f"[real-sample] Detected {len(conflicts)} conflict sets")

    # Compile candidates
    compiler = CandidateCompiler()
    for claim in claims:
        if claim.claim_status in ("supported", "contested", "observed"):
            compiler.propose_from_claim(claim)
    for cs in engine.get_all_conflict_sets():
        compiler.propose_from_conflict(cs)
    candidates = compiler.get_all_candidates()
    print(f"[real-sample] Compiled {len(candidates)} candidates")

    # Build dossiers
    dossiers = []
    for candidate in candidates[:15]:
        d = ResearchDossierV1(
            subject_type="candidate",
            subject_id=candidate.candidate_id,
            candidate_status=candidate.candidate_status,
            current_claims=candidate.source_claim_ids,
        )
        dossiers.append(d)
    print(f"[real-sample] Built {len(dossiers)} dossiers")

    # Count opposing edges
    opposing = sum(1 for e in edges if e.contradicts)

    result = {
        "sample_label": SAMPLE_LABEL,
        "total_events_loaded": len(events),
        "claims_generated": len(claims),
        "evidence_edges": len(edges),
        "opposing_edges": opposing,
        "conflict_sets": len(conflicts),
        "candidates": len(candidates),
        "dossiers": len(dossiers),
        "event_families": summary["event_families"],
        "pit_quality": summary["pit_quality"],
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Run Real Sample Integration Test")
    parser.add_argument("--events", type=int, default=100, help="Number of real events to load")
    parser.add_argument("--target-claims", type=int, default=200)
    parser.add_argument("--output", default="data/intelligence/integration/reports/END_TO_END_RUN_REPORT_V1.md")
    args = parser.parse_args()

    result = run_real_sample(events_limit=args.events, claims_target=args.target_claims)
    print(json.dumps(result, indent=2))

    # Write report
    lines = [
        "# End-to-End Real Sample Report V1",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        f"**Sample Label**: {SAMPLE_LABEL}",
        "",
        "## Results",
        "",
        f"- **Real Events Loaded**: {result['total_events_loaded']}",
        f"- **Claims Generated**: {result['claims_generated']}",
        f"- **Evidence Edges**: {result['evidence_edges']}",
        f"- **Opposing Edges**: {result['opposing_edges']}",
        f"- **Conflict Sets**: {result['conflict_sets']}",
        f"- **Candidates**: {result['candidates']}",
        f"- **Dossiers**: {result['dossiers']}",
        "",
        "## Event Families",
        "",
    ]
    for fam, cnt in result.get("event_families", {}).items():
        lines.append(f"- {fam}: {cnt}")
    lines.append("")
    lines.append("**Note**: This is a temporary real integration sample (§39).")
    lines.append("Full integration requires all four producers locked and merged.")

    output_path = os.path.join(PROJECT_ROOT, args.output)
    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nReport written to {output_path}")

    from datetime import datetime, timezone


if __name__ == "__main__":
    main()
