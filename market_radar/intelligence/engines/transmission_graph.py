"""Transmission Graph Engine V1 — path finding, cycle detection, analysis."""

from __future__ import annotations

from typing import Optional

from ..contracts.transmission import TransmissionGraph, TransmissionEdge, TransmissionNode
from ..errors.codes import IntelligenceError, ErrorCode


class TransmissionGraphEngineV1:
    """Operations on transmission graphs."""

    def __init__(self, graph: Optional[TransmissionGraph] = None):
        self.graph = graph or TransmissionGraph(graph_id="default")

    def add_node(self, node: TransmissionNode) -> None:
        if node.node_id in self.graph.nodes:
            raise IntelligenceError(
                ErrorCode.DUPLICATE_NODE,
                f"Node {node.node_id} already exists",
            )
        self.graph.add_node(node)

    def remove_node(self, node_id: str) -> None:
        self.graph.remove_node(node_id)

    def add_edge(self, edge: TransmissionEdge) -> None:
        if edge.edge_id in self.graph.edges:
            raise ValueError(f"Edge {edge.edge_id} already exists")
        self.graph.add_edge(edge)

    def remove_edge(self, edge_id: str) -> None:
        self.graph.remove_edge(edge_id)

    def find_paths(self, source: str, target: str,
                   max_depth: Optional[int] = None) -> list[list[str]]:
        """Find all paths between two nodes."""
        if source not in self.graph.nodes:
            raise IntelligenceError(ErrorCode.MISSING_NODE, f"Source {source} not in graph")
        if target not in self.graph.nodes:
            raise IntelligenceError(ErrorCode.MISSING_NODE, f"Target {target} not in graph")

        depth = max_depth if max_depth is not None else self.graph.max_path_depth
        paths = self.graph.find_paths(source, target, depth)

        if not paths:
            return []

        return paths

    def detect_cycles(self) -> list[list[str]]:
        """Detect cycles in the graph (ignoring declared reflexive edges)."""
        cycles = []
        visited = set()
        rec_stack = set()
        parent: dict[str, Optional[str]] = {}

        def dfs(node: str):
            visited.add(node)
            rec_stack.add(node)
            for edge in self.graph.get_outgoing(node):
                # Skip declared reflexive edges
                if edge.reflexive and edge.target_node == node:
                    continue
                if edge.target_node not in visited:
                    parent[edge.target_node] = node
                    dfs(edge.target_node)
                elif edge.target_node in rec_stack:
                    # Found a cycle — reconstruct it
                    cycle = []
                    curr = node
                    while curr != edge.target_node:
                        cycle.append(curr)
                        curr = parent.get(curr, "")
                        if not curr:
                            break
                    cycle.append(edge.target_node)
                    cycle.append(node)
                    cycle.reverse()
                    if cycle not in cycles:
                        cycles.append(cycle)
            rec_stack.remove(node)

        for nid in self.graph.node_ids:
            if nid not in visited:
                dfs(nid)

        return cycles

    def orphans(self) -> list[str]:
        """Find orphan nodes (no incoming or outgoing edges)."""
        return self.graph.orphan_nodes()

    def edges_without_evidence(self) -> list[str]:
        """Find edges lacking evidence references."""
        return self.graph.edges_without_evidence()

    def conflict_signs(self) -> list[dict]:
        """Find edges between same nodes with conflicting signs."""
        return self.graph.detect_conflict_signs()

    def get_outgoing(self, node_id: str) -> list[TransmissionEdge]:
        if node_id not in self.graph.nodes:
            raise IntelligenceError(ErrorCode.MISSING_NODE, f"Node {node_id} not in graph")
        return self.graph.get_outgoing(node_id)

    def get_incoming(self, node_id: str) -> list[TransmissionEdge]:
        if node_id not in self.graph.nodes:
            raise IntelligenceError(ErrorCode.MISSING_NODE, f"Node {node_id} not in graph")
        return self.graph.get_incoming(node_id)
