#!/usr/bin/env python3
"""Compute git-object-based SHA256 hashes for manifest artifacts."""
import argparse, hashlib, subprocess, sys

def compute_hash(commit_sha, repo_path, artifact_path):
    try:
        raw = subprocess.check_output(["git","cat-file","blob",f"{commit_sha}:{artifact_path}"], cwd=repo_path)
    except subprocess.CalledProcessError as e:
        return {"path":artifact_path,"error":str(e),"sha256":None,"byte_count":0,"line_count":0}
    sha = hashlib.sha256(raw).hexdigest()
    lines = sum(1 for line in raw.split(b"\n") if line.strip())
    return {"path":artifact_path,"sha256":sha,"byte_count":len(raw),"line_count":lines}

def main():
    parser = argparse.ArgumentParser(description="Compute git-object hashes for manifest artifacts")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--paths", nargs="*", default=[
        "data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl",
        "data/intelligence/historical_macro/normalized/macro_release_observations_v1.jsonl",
        "data/intelligence/historical_macro/normalized/macro_source_snapshots_v1.jsonl",
    ])
    args = parser.parse_args()
    print(f"Hash basis: git object bytes from commit {args.commit}\n")
    for path in args.paths:
        r = compute_hash(args.commit, args.repo, path)
        if r["sha256"]:
            print(f"Artifact: {r['path']}\n  SHA256: {r['sha256']}\n  Bytes:  {r['byte_count']}\n  Lines:  {r['line_count']}\n")
        else:
            print(f"Artifact: {r['path']}\n  ERROR: {r['error']}\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
