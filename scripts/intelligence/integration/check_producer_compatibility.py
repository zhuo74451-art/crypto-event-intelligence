#!/usr/bin/env python3
"""Check producer compatibility — delegates to ProducerCompatibilityChecker."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from market_radar.intelligence.integration.compatibility import ProducerCompatibilityChecker
print("Producer compatibility checker loaded. Use run_integration_gates.py for full check.")
