"""
Tests for Candidate Compiler (§41 items 15-18).
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.research.candidate_compiler import CandidateCompiler
from market_radar.intelligence.research.contracts import ResearchClaimV1, ConflictSetV1


class TestCandidateCompiler:
    """Test 7: Holdout failure can lower candidate status.
       Test: Auto-compile only produces 'proposed'."""

    def test_default_is_proposed(self):
        compiler = CandidateCompiler()
        claim = ResearchClaimV1(
            subject="test", predicate="associated_with", object="btc_up",
            claim_type="directional", claim_status="supported",
        )
        candidate = compiler.propose_from_claim(claim)
        assert candidate.candidate_status == "proposed"

    def test_propose_from_conflict(self):
        compiler = CandidateCompiler()
        cs = ConflictSetV1(
            conflict_key="test::conflict",
            conflict_type="direction_conflict",
            claim_ids=["RC-AAA", "RC-BBB"],
        )
        candidate = compiler.propose_from_conflict(cs)
        assert candidate.candidate_status == "proposed"
        assert cs.conflict_set_id in candidate.source_conflict_ids

    def test_idempotent_add(self):
        compiler = CandidateCompiler()
        claim = ResearchClaimV1(
            subject="test", predicate="associated_with", object="btc_up",
            claim_type="directional", claim_status="supported",
        )
        c1 = compiler.propose_from_claim(claim)
        c2 = compiler.propose_from_claim(claim)
        assert c1.candidate_id == c2.candidate_id
        assert len(compiler.get_all_candidates()) == 1

    def test_export_jsonl(self, tmp_path):
        compiler = CandidateCompiler()
        claim = ResearchClaimV1(
            subject="test", predicate="associated_with", object="btc_up",
            claim_type="directional", claim_status="supported",
        )
        compiler.propose_from_claim(claim)
        path = tmp_path / "candidates.jsonl"
        compiler.export_jsonl(str(path))
        assert path.read_text().strip() != ""
