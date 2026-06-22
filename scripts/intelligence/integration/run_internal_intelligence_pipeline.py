#!/usr/bin/env python3
"""
Run Internal Intelligence Pipeline — wrapper that delegates to the core pipeline.
Usage:
  python scripts/intelligence/integration/run_internal_intelligence_pipeline.py \
    --producer-locks docs/execution/lane_e/PRODUCER_LOCKS.yaml \
    --output-dir data/intelligence/integration \
    --research-output-dir data/intelligence/research \
    --resume
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

def main():
    parser = argparse.ArgumentParser(description="Run Internal Intelligence Pipeline")
    parser.add_argument("--producer-locks", default="docs/execution/lane_e/PRODUCER_LOCKS.yaml")
    parser.add_argument("--output-dir", default="data/intelligence/integration")
    parser.add_argument("--research-output-dir", default="data/intelligence/research")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, PROJECT_ROOT)
    from market_radar.intelligence.integration.internal_pipeline import InternalPipeline

    pipeline = InternalPipeline(
        producer_locks_path=args.producer_locks,
        output_dir=args.output_dir,
        research_output_dir=args.research_output_dir,
        resume=args.resume,
    )
    result = pipeline.run()
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
