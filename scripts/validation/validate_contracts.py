#!/usr/bin/env python
"""
Validate validation contracts — import and structural checks.
"""

import sys


def validate_imports():
    """Check all validation modules import cleanly."""
    modules = [
        "market_radar.validation.contracts.common",
        "market_radar.validation.contracts.dataset",
        "market_radar.validation.contracts.event",
        "market_radar.validation.contracts.label",
        "market_radar.validation.contracts.split",
        "market_radar.validation.contracts.prediction",
        "market_radar.validation.contracts.evaluation",
        "market_radar.validation.contracts.experiment",
        "market_radar.validation.contracts.calibration",
        "market_radar.validation.contracts.baseline",
        "market_radar.validation.contracts.report",
        "market_radar.validation.contracts.errors",
        "market_radar.validation.point_in_time.availability",
        "market_radar.validation.point_in_time.revision_guard",
        "market_radar.validation.point_in_time.leakage_detector",
        "market_radar.validation.datasets.builder",
        "market_radar.validation.labels.return_labels",
        "market_radar.validation.splits.chronological",
        "market_radar.validation.splits.purged",
        "market_radar.validation.splits.walk_forward",
        "market_radar.validation.baselines.neutral",
        "market_radar.validation.metrics.classification",
        "market_radar.validation.metrics.abstention",
        "market_radar.validation.calibration.protocols",
        "market_radar.validation.evaluation.bootstrap",
        "market_radar.validation.evaluation.multiple_testing",
        "market_radar.validation.experiments.registry",
    ]

    failures = []
    for mod_name in modules:
        try:
            __import__(mod_name)
            print(f"  [OK] {mod_name}")
        except Exception as e:
            print(f"  [FAIL] {mod_name}: {e}")
            failures.append(mod_name)

    if failures:
        print(f"\n{len(failures)} module(s) failed to import")
        return False
    return True


def main():
    print("Validating validation contracts...")
    ok = validate_imports()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
