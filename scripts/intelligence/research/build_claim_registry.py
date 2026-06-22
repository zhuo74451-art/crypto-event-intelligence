#!/usr/bin/env python3
"""
Build Claim Registry — generates research claims from locked producer artifacts.
Standalone script for independent execution.
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


def main():
    parser = argparse.ArgumentParser(description="Build Research Claim Registry")
    parser.add_argument("--claims-output", default="data/intelligence/research/claims/research_claims_v1.jsonl")
    parser.add_argument("--source", default="internal_pipeline")
    args = parser.parse_args()

    # Delegate to internal pipeline
    from market_radar.intelligence.integration.internal_pipeline import InternalPipeline

    pipeline = InternalPipeline(
        producer_locks_path="docs/execution/lane_e/PRODUCER_LOCKS.yaml",
        output_dir="data/intelligence/integration",
        research_output_dir="data/intelligence/research",
    )
    result = pipeline.run()

    print(f"Claims built: {result.get('claims', 0)}")
    print(f"Output: {args.claims_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
