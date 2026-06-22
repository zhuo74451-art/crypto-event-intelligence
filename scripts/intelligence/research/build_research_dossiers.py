#!/usr/bin/env python3
"""Build research dossiers — wrapper that delegates to contracts."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.research.contracts import ResearchDossierV1
print("Research dossier builder loaded. Use internal_pipeline.py for full pipeline.")
