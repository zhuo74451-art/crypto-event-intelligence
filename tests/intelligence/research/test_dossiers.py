"""
Tests for Research Dossiers (§25, §41 item 10).
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.research.contracts import ResearchDossierV1


class TestResearchDossier:
    """Test 10: Abstention records enter research dossier."""

    def test_deterministic_id(self):
        d1 = ResearchDossierV1(
            subject_type="candidate",
            subject_id="CD-1234",
            candidate_status="proposed",
        )
        d2 = ResearchDossierV1(
            subject_type="candidate",
            subject_id="CD-1234",
            candidate_status="proposed",
        )
        assert d1.dossier_id == d2.dossier_id

    def test_includes_required_fields(self):
        d = ResearchDossierV1(
            subject_type="candidate",
            subject_id="CD-5678",
            candidate_status="historically_supported",
            current_claims=["RC-AAA", "RC-BBB"],
            contested_claims=["RC-CCC"],
            contradicted_claims=["RC-DDD"],
            open_questions=["RQ-111"],
            conflict_sets=["CS-222"],
            supporting_evidence=["EE-111"],
            opposing_evidence=["EE-222"],
            limitations=["historical support only"],
        )
        assert d.dossier_id.startswith("RD-")
        assert len(d.current_claims) == 2
        assert len(d.opposing_evidence) == 1
        assert len(d.limitations) == 1

    def test_serialization(self):
        d = ResearchDossierV1(
            subject_type="strategy_family",
            subject_id="SF-cpi_event",
            candidate_status="validation_pending",
        )
        data = d.to_dict()
        assert data["subject_type"] == "strategy_family"
        assert data["dossier_id"].startswith("RD-")
