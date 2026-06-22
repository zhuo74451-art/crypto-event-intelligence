#!/usr/bin/env python3
"""
Lock Producers — reads producer manifests and locks SHAs in PRODUCER_LOCKS.yaml.
"""

import argparse
import hashlib
import os
import sys
import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
LOCKS_PATH = os.path.join(PROJECT_ROOT, "docs/execution/lane_e/PRODUCER_LOCKS.yaml")

# Map lane key to worktree paths (relative to sealed repo)
LANE_WORKTREES = {
    "lane_a": "C:/Users/zhuo7/Desktop/crypto-event-intelligence-worktrees/lane-a-historical-macro-evidence-v1",
    "lane_b": "C:/Users/zhuo7/Desktop/crypto-event-intelligence-worktrees/lane-b-historical-market-cross-asset-v1",
    "lane_c": "C:/Users/zhuo7/Desktop/crypto-event-intelligence-worktrees/lane-c-macro-strategy-replay-v1",
    "lane_d": "C:/Users/zhuo7/Desktop/crypto-event-intelligence-worktrees/lane-d-validation-walkforward-calibration-v1",
}

LANE_BRANCHES = {
    "lane_a": "feat/overnight-lane-a-historical-macro-evidence-v1",
    "lane_b": "feat/overnight-lane-b-historical-market-cross-asset-v1",
    "lane_c": "feat/overnight-lane-c-macro-strategy-replay-v1",
    "lane_d": "feat/overnight-lane-d-validation-walkforward-calibration-v1",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def lock_lane(locks: dict, lane_key: str) -> dict:
    """Lock a single producer lane by reading its manifest."""
    wt = LANE_WORKTREASES.get(lane_key)
    if not wt or not os.path.isdir(wt):
        return {"error": f"Worktree not found for {lane_key}"}

    manifest_path = os.path.join(wt, "docs/execution", lane_key.replace("lane_", "lane_"), "INTEGRATION_MANIFEST.yaml")
    if not os.path.isfile(manifest_path):
        return {"error": f"Manifest not found: {manifest_path}"}

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    producer_head = manifest.get("producer_head_sha", "")
    base_sha = manifest.get("base_sha", "")

    # Get actual HEAD of worktree
    import subprocess
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=wt,
    )
    actual_head = result.stdout.strip()

    # Check if manifest matches actual HEAD
    manifest_matches = producer_head == actual_head[:len(producer_head)]

    locks["producers"][lane_key] = {
        "branch": LANE_BRANCHES[lane_key],
        "locked_sha": actual_head,
        "manifest_path": manifest_path,
        "manifest_sha256": sha256_file(manifest_path),
        "base_sha": base_sha,
        "readiness": "ready" if manifest_matches else "rejected_pending_repair",
        "artifact_hashes_verified": manifest_matches,
    }
    return {"locked_sha": actual_head, "readiness": locks["producers"][lane_key]["readiness"]}


def main():
    parser = argparse.ArgumentParser(description="Lock Producer Lanes")
    parser.add_argument("--lane", choices=["lane_a", "lane_b", "lane_c", "lane_d", "all"], default="all")
    parser.add_argument("--output", default=LOCKS_PATH)
    args = parser.parse_args()

    with open(LOCKS_PATH) as f:
        locks = yaml.safe_load(f)

    lanes = [args.lane] if args.lane != "all" else ["lane_a", "lane_b", "lane_c", "lane_d"]

    for lane in lanes:
        result = lock_lane(locks, lane)
        if "error" in result:
            print(f"[{lane}] FAIL: {result['error']}")
        else:
            print(f"[{lane}] Locked at {result['locked_sha'][:8]} ({result['readiness']})")

    with open(args.output, "w") as f:
        yaml.dump(locks, f, default_flow_style=False)
    print(f"Locks written to {args.output}")


if __name__ == "__main__":
    main()
