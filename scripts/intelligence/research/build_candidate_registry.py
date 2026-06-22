#!/usr/bin/env python3
"""Build candidate registry — wrapper that delegates to candidate_compiler."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.research.candidate_compiler import CandidateCompiler
print("Candidate registry builder loaded. Use internal_pipeline.py for full pipeline.")
