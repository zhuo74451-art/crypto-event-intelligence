"""
Evidence Graph — directed evidence dependency graph.

Nodes represent entities from the full intelligence pipeline.
Edges represent relationships (supports, contradicts, qualifies, etc.).
The graph is persisted as JSONL node/edge files and an SQLite database.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


VALID_NODE_TYPES = [
    "event", "source_snapshot", "macro_release", "consensus", "revision",
    "market_window", "market_label", "strategy_instance", "hypothesis",
    "kernel_ruling", "validation_result", "calibration_artifact",
    "failed_experiment", "research_claim", "candidate",
]

VALID_EDGE_TYPES = [
    "derived_from", "supports", "contradicts", "qualifies", "invalidates",
    "depends_on", "shares_origin_with", "supersedes", "validated_by",
    "calibrated_by", "failed_under",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _node_id(node_type: str, content_key: str) -> str:
    h = hashlib.sha256(f"{node_type}::{content_key}".encode("utf-8")).hexdigest()[:16].upper()
    return f"N-{h}"


def _edge_id(from_id: str, to_id: str, edge_type: str) -> str:
    h = hashlib.sha256(f"{from_id}::{to_id}::{edge_type}".encode("utf-8")).hexdigest()[:16].upper()
    return f"E-{h}"


@dataclass
class EvidenceNode:
    node_type: str
    content_key: str
    label: str
    source_lane: str = "unknown"

    properties: dict = field(default_factory=dict)
    producer_sha: Optional[str] = None
    observed_at_utc: Optional[str] = None

    node_id: Optional[str] = None
    created_at_utc: Optional[str] = None

    def __post_init__(self):
        if self.node_type not in VALID_NODE_TYPES:
            raise ValueError(f"Invalid node type: {self.node_type}")
        if self.node_id is None:
            self.node_id = _node_id(self.node_type, self.content_key)
        if self.created_at_utc is None:
            self.created_at_utc = _utc_now()

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class EvidenceEdge:
    from_id: str
    to_id: str
    edge_type: str

    weight: float = 1.0
    properties: dict = field(default_factory=dict)
    source_artifact: Optional[str] = None

    edge_id: Optional[str] = None
    created_at_utc: Optional[str] = None

    def __post_init__(self):
        if self.edge_type not in VALID_EDGE_TYPES:
            raise ValueError(f"Invalid edge type: {self.edge_type}")
        if self.edge_id is None:
            self.edge_id = _edge_id(self.from_id, self.to_id, self.edge_type)
        if self.created_at_utc is None:
            self.created_at_utc = _utc_now()

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class EvidenceGraph:
    """
    Directed evidence graph. Persisted as JSONL + SQLite.
    """

    def __init__(self, sqlite_path: Optional[str] = None):
        self._nodes: dict[str, EvidenceNode] = {}
        self._edges: dict[str, EvidenceEdge] = {}
        self._sqlite_path = sqlite_path

    def add_node(self, node: EvidenceNode):
        if node.node_id in self._nodes:
            return  # Idempotent
        self._nodes[node.node_id] = node

    def add_edge(self, edge: EvidenceEdge):
        if edge.edge_id in self._edges:
            return  # Idempotent
        if edge.from_id not in self._nodes:
            raise ValueError(f"from_id {edge.from_id} not in graph")
        if edge.to_id not in self._nodes:
            raise ValueError(f"to_id {edge.to_id} not in graph")
        self._edges[edge.edge_id] = edge

    def get_node(self, node_id: str) -> Optional[EvidenceNode]:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[EvidenceEdge]:
        return self._edges.get(edge_id)

    def get_supporting_edges(self, node_id: str) -> list[EvidenceEdge]:
        return [e for e in self._edges.values()
                if e.to_id == node_id and e.edge_type == "supports"]

    def get_contradicting_edges(self, node_id: str) -> list[EvidenceEdge]:
        return [e for e in self._edges.values()
                if e.to_id == node_id and e.edge_type == "contradicts"]

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def export_nodes_jsonl(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            for node in self._nodes.values():
                f.write(node.to_json() + "\n")

    def export_edges_jsonl(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            for edge in self._edges.values():
                f.write(edge.to_json() + "\n")

    def export_sqlite(self, path: Optional[str] = None):
        path = path or self._sqlite_path
        if path is None:
            raise ValueError("No SQLite path provided")
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS evidence_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                content_key TEXT NOT NULL,
                label TEXT NOT NULL,
                source_lane TEXT,
                properties TEXT,
                producer_sha TEXT,
                observed_at_utc TEXT,
                created_at_utc TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS evidence_edges (
                edge_id TEXT PRIMARY KEY,
                from_id TEXT NOT NULL,
                to_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                properties TEXT,
                source_artifact TEXT,
                created_at_utc TEXT,
                FOREIGN KEY (from_id) REFERENCES evidence_nodes(node_id),
                FOREIGN KEY (to_id) REFERENCES evidence_nodes(node_id)
            )
        """)
        for node in self._nodes.values():
            cur.execute(
                "INSERT OR IGNORE INTO evidence_nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    node.node_id, node.node_type, node.content_key, node.label,
                    node.source_lane, json.dumps(node.properties),
                    node.producer_sha, node.observed_at_utc, node.created_at_utc,
                ),
            )
        for edge in self._edges.values():
            cur.execute(
                "INSERT OR IGNORE INTO evidence_edges VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    edge.edge_id, edge.from_id, edge.to_id, edge.edge_type,
                    edge.weight, json.dumps(edge.properties),
                    edge.source_artifact, edge.created_at_utc,
                ),
            )
        conn.commit()
        conn.close()
