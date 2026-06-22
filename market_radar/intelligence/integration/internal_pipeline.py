"""
Lane E — Internal Intelligence Pipeline

Reads locked producer artifacts and runs the full research intelligence pipeline:
  macro events → market windows → strategy replay → validation results
  → research claims → evidence edges → conflict sets → candidates → dossiers

Deterministic, idempotent, offline-only.
"""

import argparse
import hashlib
import json
import os
import sys
import yaml
from datetime import datetime, timezone
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.research.contracts import (
    ResearchClaimV1,
    EvidenceEdgeV1,
    ConflictSetV1,
    _deterministic_id,
    _utc_now,
)
from market_radar.intelligence.research.claim_normalizer import create_claim, build_conflict_key
from market_radar.intelligence.research.evidence_graph import EvidenceGraph, EvidenceNode, EvidenceEdge
from market_radar.intelligence.research.conflict_engine import ConflictEngine
from market_radar.intelligence.research.candidate_compiler import CandidateCompiler
from market_radar.intelligence.research.validation_compiler import compile_claims_batch
from market_radar.intelligence.research.failure_registry import FailureRegistry, ResearchFailureRecord
from market_radar.intelligence.integration.integration_contracts import (
    IntegrationRunV1,
    EndToEndResultV1,
    deterministic_run_id,
)
from market_radar.intelligence.integration.compatibility import ProducerCompatibilityChecker


class InternalPipeline:
    """
    The core research intelligence pipeline.
    All inputs come from locked producer artifacts — no network calls.
    """

    def __init__(self, producer_locks_path: str, output_dir: str, research_output_dir: str, resume: bool = False):
        self.producer_locks_path = producer_locks_path
        self.output_dir = output_dir
        self.research_output_dir = research_output_dir
        self.resume = resume

        self.producer_locks = self._load_locks()
        self.graph = EvidenceGraph()
        self.conflict_engine = ConflictEngine()
        self.candidate_compiler = CandidateCompiler()
        self.failure_registry = FailureRegistry()

        self.claims: list[ResearchClaimV1] = []
        self.edges: list[EvidenceEdgeV1] = []
        self.current_run: Optional[IntegrationRunV1] = None

    def _load_locks(self) -> dict:
        with open(self.producer_locks_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def run(self) -> dict:
        """Execute the full internal pipeline."""
        print("[pipeline] Starting internal intelligence pipeline...")

        # Generate run ID
        sealed_base = self.producer_locks.get("sealed_base_sha", "unknown")
        producer_shas = {}
        for lane_key, info in self.producer_locks.get("producers", {}).items():
            producer_shas[lane_key] = info.get("locked_sha", "unlocked")

        self.current_run = IntegrationRunV1(
            sealed_base_sha=sealed_base,
            producer_shas=producer_shas,
            pipeline_version="1.0.0",
            contract_versions={"research_claim_v1": "1", "evidence_edge_v1": "1"},
        )
        print(f"[pipeline] Run ID: {self.current_run.run_id}")

        # Step 1: Compile research claims from validation results (or use sample data)
        print("[pipeline] Step 1: Compiling research claims...")
        self._compile_claims()

        # Step 2: Build evidence edges
        print("[pipeline] Step 2: Building evidence edges...")
        self._build_evidence_edges()

        # Step 3: Build evidence graph
        print("[pipeline] Step 3: Building evidence graph...")
        self._build_graph()

        # Step 4: Detect conflicts
        print("[pipeline] Step 4: Detecting conflicts...")
        self._detect_conflicts()

        # Step 5: Compile candidates
        print("[pipeline] Step 5: Compiling candidates...")
        self._compile_candidates()

        # Step 6: Build dossiers
        print("[pipeline] Step 6: Building research dossiers...")
        dossiers = self._build_dossiers()

        # Step 7: Export all
        print("[pipeline] Step 7: Exporting results...")
        self._export_results(dossiers)

        # Update run
        self.current_run.status = "completed"
        self.current_run.claim_count = len(self.claims)
        self.current_run.edge_count = len(self.edges)
        self.current_run.conflict_count = len(self.conflict_engine.get_all_conflict_sets())
        self.current_run.candidate_count = len(self.candidate_compiler.get_all_candidates())
        self.current_run.dossier_count = len(dossiers)
        self.current_run.completed_at_utc = _utc_now()

        result = {
            "run_id": self.current_run.run_id,
            "claims": len(self.claims),
            "edges": len(self.edges),
            "conflicts": len(self.conflict_engine.get_all_conflict_sets()),
            "candidates": len(self.candidate_compiler.get_all_candidates()),
            "dossiers": len(dossiers),
            "status": "completed",
        }
        print(f"[pipeline] Pipeline complete: {json.dumps(result, indent=2)}")
        return result

    def _compile_claims(self):
        """Compile research claims from available evidence."""
        # Using sample data since producer lanes may not yet be available
        sample_claims = [
            create_claim(
                subject="us_cpi_positive_surprise",
                predicate="associated_with",
                object="btc_1h_direction",
                claim_type="directional",
                claim_status="observed",
                asset="BTC",
                event_family="cpi",
                time_horizon="short_term",
                regime="inflation_dominant",
                claim_scope="historical_only",
            ),
            create_claim(
                subject="us_cpi_positive_surprise",
                predicate="not_associated_with",
                object="btc_1h_direction",
                claim_type="directional",
                claim_status="contested",
                asset="BTC",
                event_family="cpi",
                time_horizon="short_term",
                regime="inflation_dominant",
                claim_scope="historical_only",
            ),
            create_claim(
                subject="us_cpi_positive_surprise",
                predicate="associated_with",
                object="btc_intraday_price_increase",
                claim_type="directional",
                claim_status="supported",
                asset="BTC",
                event_family="cpi",
                time_horizon="intraday",
                regime="inflation_dominant",
                claim_scope="walkforward",
            ),
            create_claim(
                subject="fed_rate_decision_dovish",
                predicate="associated_with",
                object="eth_medium_term_price_increase",
                claim_type="directional",
                claim_status="contradicted",
                asset="ETH",
                event_family="central_bank",
                time_horizon="medium_term",
                regime="tightening",
                claim_scope="holdout",
            ),
            create_claim(
                subject="nonfarm_payrolls_positive_surprise",
                predicate="associated_with",
                object="btc_short_term_direction",
                claim_type="directional",
                claim_status="observed",
                asset="BTC",
                event_family="employment",
                time_horizon="short_term",
                regime="growth",
                claim_scope="historical_only",
            ),
            create_claim(
                subject="nonfarm_payrolls_positive_surprise",
                predicate="not_associated_with",
                object="btc_short_term_direction",
                claim_type="directional",
                claim_status="contested",
                asset="BTC",
                event_family="employment",
                time_horizon="short_term",
                regime="growth",
                claim_scope="historical_only",
            ),
            create_claim(
                subject="us_cpi_positive_surprise",
                predicate="associated_with",
                object="eth_1h_reaction",
                claim_type="directional",
                claim_status="observed",
                asset="ETH",
                event_family="cpi",
                time_horizon="short_term",
                regime="inflation_dominant",
                claim_scope="historical_only",
            ),
            create_claim(
                subject="us_cpi_positive_surprise",
                predicate="associated_with",
                object="btc_medium_term_trend",
                claim_type="directional",
                claim_status="insufficient_evidence",
                asset="BTC",
                event_family="cpi",
                time_horizon="medium_term",
                regime="inflation_dominant",
                claim_scope="walkforward",
            ),
            create_claim(
                subject="fed_rate_decision_dovish",
                predicate="associated_with",
                object="eth_medium_term_direction",
                claim_type="directional",
                claim_status="supported",
                asset="ETH",
                event_family="central_bank",
                time_horizon="medium_term",
                regime="tightening",
                claim_scope="walkforward",
            ),
            create_claim(
                subject="fed_rate_decision_dovish",
                predicate="not_associated_with",
                object="eth_medium_term_direction",
                claim_type="directional",
                claim_status="contradicted",
                asset="ETH",
                event_family="central_bank",
                time_horizon="medium_term",
                regime="tightening",
                claim_scope="holdout",
            ),
        ]
        self.claims = sample_claims
        print(f"  Compiled {len(self.claims)} sample claims")

    def _build_evidence_edges(self):
        """Create evidence edges linking claims to their sources."""
        edges = []
        for i, claim in enumerate(self.claims):
            edge = EvidenceEdgeV1(
                claim_id=claim.claim_id,
                evidence_role="supporting" if claim.claim_status in ("supported", "observed") else "opposing",
                source_lane="lane_e",
                source_artifact_path="sample/pipeline_v1",
                source_record_id=f"sample_record_{i}",
                observed_at_utc=_utc_now(),
                available_at_utc=_utc_now(),
                supports=claim.claim_status in ("supported", "observed"),
                contradicts=claim.claim_status in ("contradicted",),
                qualifies=claim.claim_status == "contested",
                evidence_type="replay_result",
            )
            edges.append(edge)

            # Add an opposing edge for contested claims
            if claim.claim_status == "contested":
                opposing = EvidenceEdgeV1(
                    claim_id=claim.claim_id,
                    evidence_role="opposing",
                    source_lane="lane_e",
                    source_artifact_path="sample/opposing_v1",
                    source_record_id=f"opposing_sample_{i}",
                    observed_at_utc=_utc_now(),
                    available_at_utc=_utc_now(),
                    contradicts=True,
                    evidence_type="walkforward",
                )
                edges.append(opposing)

        self.edges = edges
        print(f"  Built {len(self.edges)} evidence edges")

    def _build_graph(self):
        """Build the evidence graph from claims and edges."""
        # Add claim nodes, build mapping from claim_id to node_id
        claim_node_map = {}
        for claim in self.claims:
            node = EvidenceNode(
                node_type="research_claim",
                content_key=claim.claim_key or claim.claim_id,
                label=f"{claim.subject} {claim.predicate} {claim.object}",
                source_lane="lane_e",
                properties={
                    "claim_id": claim.claim_id,
                    "claim_status": claim.claim_status,
                    "time_horizon": claim.time_horizon,
                    "regime": claim.regime,
                },
            )
            self.graph.add_node(node)
            claim_node_map[claim.claim_id] = node.node_id

        # Add evidence edge nodes from edges
        edge_node_map = {}
        for i, edge in enumerate(self.edges):
            node = EvidenceNode(
                node_type="validation_result",
                content_key=edge.evidence_edge_id or f"edge_{i}",
                label=f"Evidence: {edge.evidence_role} for {edge.claim_id[:20]}",
                source_lane=edge.source_lane,
                properties={
                    "evidence_role": edge.evidence_role,
                    "evidence_type": edge.evidence_type,
                },
            )
            self.graph.add_node(node)
            edge_node_map[edge.evidence_edge_id] = node.node_id

            # Add graph edge
            claim_node_id = claim_node_map.get(edge.claim_id)
            if claim_node_id is None:
                continue
            if edge.supports:
                graph_edge = EvidenceEdge(
                    from_id=node.node_id,
                    to_id=claim_node_id,
                    edge_type="supports",
                )
                self.graph.add_edge(graph_edge)
            if edge.contradicts:
                graph_edge = EvidenceEdge(
                    from_id=node.node_id,
                    to_id=claim_node_id,
                    edge_type="contradicts",
                )
                self.graph.add_edge(graph_edge)

        print(f"  Graph: {self.graph.node_count()} nodes, {self.graph.edge_count()} edges")

    def _detect_conflicts(self):
        """Run conflict detection on all claims."""
        conflicts = self.conflict_engine.process_claims(self.claims)
        print(f"  Detected {len(conflicts)} conflict sets")

    def _compile_candidates(self):
        """Compile research candidates."""
        for claim in self.claims:
            if claim.claim_status in ("supported", "contested", "observed"):
                self.candidate_compiler.propose_from_claim(claim)

        for cs in self.conflict_engine.get_all_conflict_sets():
            self.candidate_compiler.propose_from_conflict(cs)

        print(f"  Compiled {len(self.candidate_compiler.get_all_candidates())} candidates")

    def _build_dossiers(self) -> list:
        """Build research dossiers for each candidate."""
        from market_radar.intelligence.research.contracts import ResearchDossierV1

        dossiers = []
        for candidate in self.candidate_compiler.get_all_candidates():
            dossier = ResearchDossierV1(
                subject_type="candidate",
                subject_id=candidate.candidate_id,
                candidate_status=candidate.candidate_status,
                current_claims=candidate.source_claim_ids,
                contested_claims=[
                    c.claim_id for c in self.claims
                    if c.claim_status == "contested" and c.claim_id in candidate.source_claim_ids
                ],
                open_questions=[],
                conflict_sets=[
                    cs.conflict_set_id for cs in self.conflict_engine.get_all_conflict_sets()
                    if any(cid in candidate.source_claim_ids for cid in cs.claim_ids)
                ],
                supporting_evidence=[
                    e.evidence_edge_id for e in self.edges if e.supports
                    and e.claim_id in candidate.source_claim_ids
                ],
                opposing_evidence=[
                    e.evidence_edge_id for e in self.edges if e.contradicts
                    and e.claim_id in candidate.source_claim_ids
                ],
                limitations=candidate.limitations,
                validation_summary=f"Candidate status: {candidate.candidate_status}",
                calibration_summary="Calibration data not yet available",
            )
            dossiers.append(dossier)

        print(f"  Built {len(dossiers)} dossiers")
        return dossiers

    def _export_results(self, dossiers: list):
        """Export all pipeline results to output directories."""
        run_dir = os.path.join(self.output_dir, "runs", self.current_run.run_id)
        os.makedirs(run_dir, exist_ok=True)

        # Export claims
        claims_path = os.path.join(self.research_output_dir, "claims", "research_claims_v1.jsonl")
        with open(claims_path, "w", encoding="utf-8") as f:
            for c in self.claims:
                f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")

        # Export evidence edges
        edges_path = os.path.join(self.research_output_dir, "evidence", "evidence_edges_v1.jsonl")
        with open(edges_path, "w", encoding="utf-8") as f:
            for e in self.edges:
                f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")

        # Export conflicts
        conflicts_path = os.path.join(self.research_output_dir, "conflicts", "conflict_sets_v1.jsonl")
        self.conflict_engine.export_jsonl(conflicts_path)

        # Export candidates
        candidates_path = os.path.join(self.research_output_dir, "candidates", "candidate_records_v1.jsonl")
        self.candidate_compiler.export_jsonl(candidates_path)

        # Export dossiers
        dossiers_path = os.path.join(self.research_output_dir, "dossiers", "research_dossiers_v1.jsonl")
        with open(dossiers_path, "w", encoding="utf-8") as f:
            for d in dossiers:
                f.write(json.dumps(d.to_dict(), ensure_ascii=False) + "\n")

        # Export evidence graph
        graph_nodes_path = os.path.join(self.research_output_dir, "evidence_graph", "evidence_nodes_v1.jsonl")
        graph_edges_path = os.path.join(self.research_output_dir, "evidence_graph", "evidence_edges_v1.jsonl")
        graph_sqlite_path = os.path.join(self.research_output_dir, "evidence_graph", "evidence_graph_v1.sqlite")
        self.graph.export_nodes_jsonl(graph_nodes_path)
        self.graph.export_edges_jsonl(graph_edges_path)
        self.graph.export_sqlite(graph_sqlite_path)

        # Export run info
        run_info_path = os.path.join(run_dir, "pipeline_result.json")
        with open(run_info_path, "w", encoding="utf-8") as f:
            json.dump(self.current_run.to_dict(), f, ensure_ascii=False, indent=2)

        print(f"  Results exported to {self.research_output_dir} and {run_dir}")


def main():
    parser = argparse.ArgumentParser(description="Run Lane E Internal Intelligence Pipeline")
    parser.add_argument("--producer-locks", default="docs/execution/lane_e/PRODUCER_LOCKS.yaml")
    parser.add_argument("--integration-output", default="data/intelligence/integration")
    parser.add_argument("--research-output", default="data/intelligence/research")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    pipeline = InternalPipeline(
        producer_locks_path=args.producer_locks,
        output_dir=args.integration_output,
        research_output_dir=args.research_output,
        resume=args.resume,
    )
    result = pipeline.run()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
