"""Tests for transmission graph engine."""

import pytest
from market_radar.intelligence.contracts.transmission import (
    TransmissionNode, TransmissionEdge, TransmissionGraph,
    NodeType, EdgeSign,
)
from market_radar.intelligence.engines.transmission_graph import TransmissionGraphEngineV1
from market_radar.intelligence.errors.codes import IntelligenceError, ErrorCode


def make_graph():
    engine = TransmissionGraphEngineV1()
    engine.add_node(TransmissionNode(node_id="n1", node_type=NodeType.EVENT, label="Event"))
    engine.add_node(TransmissionNode(node_id="n2", node_type=NodeType.MACRO_VARIABLE, label="Macro"))
    engine.add_node(TransmissionNode(node_id="n3", node_type=NodeType.ASSET, label="Asset"))
    engine.add_node(TransmissionNode(node_id="n4", node_type=NodeType.SECTOR, label="Sector"))
    engine.add_edge(TransmissionEdge(edge_id="e1", source_node="n1", target_node="n2",
                                      sign=EdgeSign.POSITIVE, mechanism="impact"))
    engine.add_edge(TransmissionEdge(edge_id="e2", source_node="n2", target_node="n3",
                                      sign=EdgeSign.NEGATIVE, mechanism="correlation"))
    return engine


class TestTransmissionGraph:
    def test_single_path(self):
        engine = make_graph()
        paths = engine.find_paths("n1", "n3")
        assert len(paths) == 1
        assert paths[0] == ["n1", "n2", "n3"]

    def test_no_path_returns_empty(self):
        engine = make_graph()
        paths = engine.find_paths("n1", "n4")
        assert len(paths) == 0

    def test_orphan_detection(self):
        engine = TransmissionGraphEngineV1()
        engine.add_node(TransmissionNode(node_id="orphan", node_type=NodeType.EVENT, label="Orphan"))
        orphans = engine.orphans()
        assert "orphan" in orphans

    def test_edge_without_evidence(self):
        engine = make_graph()
        no_ev = engine.edges_without_evidence()
        assert len(no_ev) == 2

    def test_add_duplicate_node_raises(self):
        engine = TransmissionGraphEngineV1()
        engine.add_node(TransmissionNode(node_id="n1", node_type=NodeType.EVENT, label="A"))
        with pytest.raises(IntelligenceError):
            engine.add_node(TransmissionNode(node_id="n1", node_type=NodeType.ASSET, label="B"))

    def test_path_depth_limit(self):
        engine = TransmissionGraphEngineV1()
        for i in range(10):
            engine.add_node(TransmissionNode(node_id=f"n{i}", node_type=NodeType.EVENT, label=f"N{i}"))
        for i in range(9):
            engine.add_edge(TransmissionEdge(edge_id=f"e{i}", source_node=f"n{i}", target_node=f"n{i+1}",
                                              sign=EdgeSign.POSITIVE))
        paths = engine.find_paths("n0", "n9", max_depth=3)
        assert len(paths) == 0

    def test_conflict_sign_detection(self):
        engine = TransmissionGraphEngineV1()
        engine.add_node(TransmissionNode(node_id="n1", node_type=NodeType.EVENT, label="A"))
        engine.add_node(TransmissionNode(node_id="n2", node_type=NodeType.ASSET, label="B"))
        engine.add_edge(TransmissionEdge(edge_id="e1", source_node="n1", target_node="n2",
                                          sign=EdgeSign.POSITIVE))
        engine.add_edge(TransmissionEdge(edge_id="e2", source_node="n1", target_node="n2",
                                          sign=EdgeSign.NEGATIVE))
        conflicts = engine.conflict_signs()
        assert len(conflicts) == 1
        assert conflicts[0]["pair"] == ("n1", "n2")

    def test_self_loop_requires_reflexive(self):
        engine = TransmissionGraphEngineV1()
        engine.add_node(TransmissionNode(node_id="n1", node_type=NodeType.NARRATIVE, label="Loop"))
        with pytest.raises(ValueError, match="reflexive"):
            engine.add_edge(TransmissionEdge(edge_id="e1", source_node="n1", target_node="n1",
                                              sign=EdgeSign.POSITIVE))

    def test_reflexive_self_loop_allowed(self):
        engine = TransmissionGraphEngineV1()
        engine.add_node(TransmissionNode(node_id="n1", node_type=NodeType.NARRATIVE, label="Reflexive"))
        engine.add_edge(TransmissionEdge(edge_id="e1", source_node="n1", target_node="n1",
                                          sign=EdgeSign.POSITIVE, reflexive=True))
        assert engine.graph.edge_ids == ["e1"]

    def test_remove_node_removes_edges(self):
        engine = make_graph()
        engine.remove_node("n2")
        assert "n2" not in engine.graph.nodes
        assert len(engine.graph.edges) == 0

    def test_multi_path(self):
        engine = TransmissionGraphEngineV1()
        engine.add_node(TransmissionNode(node_id="n1", node_type=NodeType.EVENT, label="Start"))
        engine.add_node(TransmissionNode(node_id="n2", node_type=NodeType.MACRO_VARIABLE, label="Mid A"))
        engine.add_node(TransmissionNode(node_id="n3", node_type=NodeType.FLOW, label="Mid B"))
        engine.add_node(TransmissionNode(node_id="n4", node_type=NodeType.ASSET, label="End"))
        engine.add_edge(TransmissionEdge(edge_id="e1", source_node="n1", target_node="n2", sign=EdgeSign.POSITIVE))
        engine.add_edge(TransmissionEdge(edge_id="e2", source_node="n1", target_node="n3", sign=EdgeSign.POSITIVE))
        engine.add_edge(TransmissionEdge(edge_id="e3", source_node="n2", target_node="n4", sign=EdgeSign.POSITIVE))
        engine.add_edge(TransmissionEdge(edge_id="e4", source_node="n3", target_node="n4", sign=EdgeSign.POSITIVE))
        paths = engine.find_paths("n1", "n4")
        assert len(paths) == 2
