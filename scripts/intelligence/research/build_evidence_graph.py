#!/usr/bin/env python3
"""Build evidence graph — wrapper that delegates to evidence_graph module."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.research.evidence_graph import EvidenceGraph
print("Evidence graph builder loaded. Use internal_pipeline.py for full pipeline.")
