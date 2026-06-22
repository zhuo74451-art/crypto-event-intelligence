#!/usr/bin/env python3
"""Build conflict sets — wrapper that delegates to conflict_engine."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.research.conflict_engine import ConflictEngine
print("Conflict set builder loaded. Use internal_pipeline.py for full pipeline.")
