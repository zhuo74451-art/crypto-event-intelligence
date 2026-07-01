"""pytest conftest: add project root to sys.path for imports."""
import os
import sys

# Add project root so experiments/stage2_foundation_spike/* is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
