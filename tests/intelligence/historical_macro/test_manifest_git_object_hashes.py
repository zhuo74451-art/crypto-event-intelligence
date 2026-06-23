"""Test that manifest artifact hashes and counts match git object bytes."""
import hashlib, os, subprocess, yaml

MANIFEST_PATH = "docs/execution/lane_a/INTEGRATION_MANIFEST.yaml"
IMPLEMENTATION_COMMIT = "6f0848537ca5a5f7c257fb6c67c5d87e202d7d69"

ARTIFACTS = {
    "release_events": "data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl",
    "release_observations": "data/intelligence/historical_macro/normalized/macro_release_observations_v1.jsonl",
    "source_snapshots": "data/intelligence/historical_macro/normalized/macro_source_snapshots_v1.jsonl",
}


def _get_git_blob(path):
    """Get raw bytes of a file from git object store at the implementation commit."""
    try:
        return subprocess.check_output(
            ["git", "cat-file", "blob", f"{IMPLEMENTATION_COMMIT}:{path}"],
        )
    except subprocess.CalledProcessError:
        return None


def _load_manifest():
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f)


class TestManifestGitObjectHashes:
    def test_hash_basis_is_git_object(self):
        manifest = _load_manifest()
        assert "file_hashes" in manifest
        fh = manifest["file_hashes"]
        assert fh.get("hash_basis") == "git_object_bytes", f"Wrong hash_basis: {fh.get('hash_basis')}"
        assert fh.get("hash_basis_commit") == IMPLEMENTATION_COMMIT, f"Wrong basis commit"

    def test_release_events_hash_matches(self):
        manifest = _load_manifest()
        raw = _get_git_blob(ARTIFACTS["release_events"])
        assert raw is not None, "Cannot read git blob for release_events"
        actual_sha = hashlib.sha256(raw).hexdigest()
        manifest_sha = manifest.get("file_hashes", {}).get("release_events", {}).get("sha256", "")
        assert actual_sha == manifest_sha, f"release_events hash mismatch: git={actual_sha} manifest={manifest_sha}"

    def test_release_observations_hash_matches(self):
        manifest = _load_manifest()
        raw = _get_git_blob(ARTIFACTS["release_observations"])
        assert raw is not None
        actual_sha = hashlib.sha256(raw).hexdigest()
        manifest_sha = manifest.get("file_hashes", {}).get("release_observations", {}).get("sha256", "")
        assert actual_sha == manifest_sha

    def test_source_snapshots_hash_matches(self):
        manifest = _load_manifest()
        raw = _get_git_blob(ARTIFACTS["source_snapshots"])
        assert raw is not None
        actual_sha = hashlib.sha256(raw).hexdigest()
        manifest_sha = manifest.get("file_hashes", {}).get("source_snapshots", {}).get("sha256", "")
        assert actual_sha == manifest_sha

    def test_release_events_count_matches(self):
        manifest = _load_manifest()
        raw = _get_git_blob(ARTIFACTS["release_events"])
        assert raw is not None
        count = sum(1 for line in raw.split(b"\n") if line.strip())
        manifest_count = manifest.get("file_hashes", {}).get("release_events", {}).get("record_count", 0)
        assert count == manifest_count, f"release_events count: git={count} manifest={manifest_count}"

    def test_release_observations_count_matches(self):
        manifest = _load_manifest()
        raw = _get_git_blob(ARTIFACTS["release_observations"])
        assert raw is not None
        count = sum(1 for line in raw.split(b"\n") if line.strip())
        manifest_count = manifest.get("file_hashes", {}).get("release_observations", {}).get("record_count", 0)
        assert count == manifest_count

    def test_source_snapshots_count_matches(self):
        manifest = _load_manifest()
        raw = _get_git_blob(ARTIFACTS["source_snapshots"])
        assert raw is not None
        count = sum(1 for line in raw.split(b"\n") if line.strip())
        manifest_count = manifest.get("file_hashes", {}).get("source_snapshots", {}).get("record_count", 0)
        assert count == manifest_count
