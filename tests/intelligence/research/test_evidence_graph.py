"""
Tests for Evidence Graph (§41 items 5, 14, 19).
"""

import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.research.evidence_graph import (
    EvidenceGraph, EvidenceNode, EvidenceEdge,
    VALID_NODE_TYPES, VALID_EDGE_TYPES,
)


class TestEvidenceNode:
    def test_deterministic_id(self):
        n1 = EvidenceNode(node_type="research_claim", content_key="test::key", label="Test Node")
        n2 = EvidenceNode(node_type="research_claim", content_key="test::key", label="Test Node")
        assert n1.node_id == n2.node_id

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            EvidenceNode(node_type="invalid_type", content_key="x", label="x")

    def test_all_valid_types(self):
        for t in VALID_NODE_TYPES:
            n = EvidenceNode(node_type=t, content_key=f"test_{t}", label=t)
            assert n.node_type == t


class TestEvidenceEdge:
    def test_deterministic_id(self):
        n1 = EvidenceNode(node_type="research_claim", content_key="a", label="A")
        n2 = EvidenceNode(node_type="research_claim", content_key="b", label="B")
        e1 = EvidenceEdge(from_id=n1.node_id, to_id=n2.node_id, edge_type="supports")
        e2 = EvidenceEdge(from_id=n1.node_id, to_id=n2.node_id, edge_type="supports")
        assert e1.edge_id == e2.edge_id

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            EvidenceEdge(from_id="N-A", to_id="N-B", edge_type="invalid_type")


class TestEvidenceGraph:
    def test_add_node_idempotent(self):
        g = EvidenceGraph()
        n = EvidenceNode(node_type="research_claim", content_key="test", label="Test")
        g.add_node(n)
        g.add_node(n)  # Second add should be no-op
        assert g.node_count() == 1

    def test_add_edge_requires_nodes(self):
        g = EvidenceGraph()
        e = EvidenceEdge(from_id="N-NONEXISTENT", to_id="N-OTHER", edge_type="supports")
        with pytest.raises(ValueError):
            g.add_edge(e)

    def test_supports_and_contradicts(self):
        g = EvidenceGraph()
        claim = EvidenceNode(node_type="research_claim", content_key="claim_1", label="CPI -> BTC up")
        ev1 = EvidenceNode(node_type="validation_result", content_key="ev_1", label="Supports")
        ev2 = EvidenceNode(node_type="validation_result", content_key="ev_2", label="Contradicts")
        g.add_node(claim)
        g.add_node(ev1)
        g.add_node(ev2)

        g.add_edge(EvidenceEdge(from_id=ev1.node_id, to_id=claim.node_id, edge_type="supports"))
        g.add_edge(EvidenceEdge(from_id=ev2.node_id, to_id=claim.node_id, edge_type="contradicts"))

        assert len(g.get_supporting_edges(claim.node_id)) == 1
        assert len(g.get_contradicting_edges(claim.node_id)) == 1

    def test_export_jsonl(self):
        g = EvidenceGraph()
        n = EvidenceNode(node_type="research_claim", content_key="export_test", label="Export Test")
        g.add_node(n)

        with tempfile.NamedTemporaryFile(mode="r", suffix=".jsonl", delete=False) as f:
            nodes_path = f.name
        with tempfile.NamedTemporaryFile(mode="r", suffix=".jsonl", delete=False) as f:
            edges_path = f.name

        try:
            g.export_nodes_jsonl(nodes_path)
            g.export_edges_jsonl(edges_path)

            with open(nodes_path) as f:
                lines = f.readlines()
            assert len(lines) == 1
        finally:
            os.unlink(nodes_path)
            os.unlink(edges_path)

    def test_export_sqlite(self):
        g = EvidenceGraph()
        n = EvidenceNode(node_type="research_claim", content_key="sqlite_test", label="SQLite Test")
        g.add_node(n)

        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name

        try:
            g.export_sqlite(db_path)
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM evidence_nodes")
            assert cur.fetchone()[0] == 1
            conn.close()
        finally:
            os.unlink(db_path)
