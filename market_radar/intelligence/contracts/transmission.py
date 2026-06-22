"""Transmission graph contracts — nodes, edges, and the graph structure."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .common import ContractBase


class NodeType(str, Enum):
    EVENT = "event"
    POLICY = "policy"
    MACRO_VARIABLE = "macro_variable"
    MARKET_STRUCTURE = "market_structure"
    FLOW = "flow"
    ASSET = "asset"
    SECTOR = "sector"
    ENTITY = "entity"
    NARRATIVE = "narrative"
    RISK_FACTOR = "risk_factor"
    OUTCOME = "outcome"


class EdgeSign(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"


@dataclass
class TransmissionNode(ContractBase):
    """A node in the transmission graph."""
    contract_name: str = "TransmissionNode"
    schema_version: str = "1.0.0"

    node_id: str = ""
    node_type: NodeType = NodeType.EVENT
    label: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.node_type, str):
            self.node_type = NodeType(self.node_type)


@dataclass
class TransmissionEdge(ContractBase):
    """A directed edge in the transmission graph."""
    contract_name: str = "TransmissionEdge"
    schema_version: str = "1.0.0"

    edge_id: str = ""
    source_node: str = ""
    target_node: str = ""
    mechanism: str = ""
    sign: EdgeSign = EdgeSign.UNKNOWN
    lag_min: Optional[int] = None
    lag_max: Optional[int] = None
    conditions: dict[str, Any] = field(default_factory=dict)
    valid_regimes: list[str] = field(default_factory=list)
    invalid_regimes: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    strength_status: str = "unverified"
    reflexive: bool = False

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.sign, str):
            self.sign = EdgeSign(self.sign)


@dataclass
class TransmissionGraph(ContractBase):
    """A directed multi-graph for transmission path analysis.

    This is a lightweight in-memory graph — no external graph DB required.
    Supports:
    - Add/remove nodes and edges
    - Path finding with depth limits
    - Cycle detection (reflexive loops must be explicitly declared)
    - Conflict sign detection
    - Orphan node detection
    """
    contract_name: str = "TransmissionGraph"
    schema_version: str = "1.0.0"

    graph_id: str = ""
    nodes: dict[str, TransmissionNode] = field(default_factory=dict)
    edges: dict[str, TransmissionEdge] = field(default_factory=dict)
    max_path_depth: int = 10

    def __post_init__(self):
        super().__post_init__()
        if self.nodes:
            converted = {}
            for k, v in self.nodes.items():
                if isinstance(v, dict):
                    converted[k] = TransmissionNode(**v)
                else:
                    converted[k] = v
            self.nodes = converted
        if self.edges:
            converted = {}
            for k, v in self.edges.items():
                if isinstance(v, dict):
                    converted[k] = TransmissionEdge(**v)
                else:
                    converted[k] = v
            self.edges = converted

    @property
    def node_ids(self) -> list[str]:
        return list(self.nodes.keys())

    @property
    def edge_ids(self) -> list[str]:
        return list(self.edges.keys())

    def add_node(self, node: TransmissionNode) -> None:
        self.nodes[node.node_id] = node

    def remove_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)
        to_remove = [eid for eid, e in self.edges.items()
                     if e.source_node == node_id or e.target_node == node_id]
        for eid in to_remove:
            self.edges.pop(eid, None)

    def add_edge(self, edge: TransmissionEdge) -> None:
        if edge.source_node not in self.nodes:
            raise ValueError(f"Source node {edge.source_node} not in graph")
        if edge.target_node not in self.nodes:
            raise ValueError(f"Target node {edge.target_node} not in graph")
        if not edge.reflexive and edge.source_node == edge.target_node:
            raise ValueError(f"Self-loop on {edge.source_node} requires reflexive=True")
        self.edges[edge.edge_id] = edge

    def remove_edge(self, edge_id: str) -> None:
        self.edges.pop(edge_id, None)

    def get_outgoing(self, node_id: str) -> list[TransmissionEdge]:
        return [e for e in self.edges.values() if e.source_node == node_id]

    def get_incoming(self, node_id: str) -> list[TransmissionEdge]:
        return [e for e in self.edges.values() if e.target_node == node_id]

    def find_paths(self, source: str, target: str,
                   max_depth: Optional[int] = None) -> list[list[str]]:
        """Find all paths from source to target (no cycles)."""
        if max_depth is None:
            max_depth = self.max_path_depth
        paths = []
        visited = {source}

        def dfs(current: str, path: list[str]):
            if len(path) > max_depth:
                return
            if current == target:
                paths.append(path.copy())
                return
            for edge in self.get_outgoing(current):
                if edge.target_node not in visited:
                    visited.add(edge.target_node)
                    path.append(edge.target_node)
                    dfs(edge.target_node, path)
                    path.pop()
                    visited.remove(edge.target_node)

        dfs(source, [source])
        return paths

    def detect_conflict_signs(self) -> list[dict]:
        """Find pairs of edges between the same nodes with conflicting signs."""
        conflicts = []
        edges_by_pair: dict[tuple[str, str], list[TransmissionEdge]] = {}
        for e in self.edges.values():
            key = (e.source_node, e.target_node)
            edges_by_pair.setdefault(key, []).append(e)
        for pair, edges in edges_by_pair.items():
            signs = set(e.sign.value for e in edges)
            if EdgeSign.POSITIVE.value in signs and EdgeSign.NEGATIVE.value in signs:
                conflicts.append({
                    "pair": pair,
                    "edge_ids": [e.edge_id for e in edges],
                    "signs": list(signs),
                })
        return conflicts

    def orphan_nodes(self) -> list[str]:
        """Find nodes with no incoming or outgoing edges."""
        connected = set()
        for e in self.edges.values():
            connected.add(e.source_node)
            connected.add(e.target_node)
        return [nid for nid in self.nodes if nid not in connected]

    def edges_without_evidence(self) -> list[str]:
        """Find edges that have no evidence references."""
        return [e.edge_id for e in self.edges.values() if not e.evidence_refs]
