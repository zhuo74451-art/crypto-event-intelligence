"""Test V3 manifest Git object hashes match blob content."""
import hashlib, subprocess, sys, os, json, yaml

ARTIFACT_COMMIT = "da98a83fc8072f1411749412d159b34c77937b19"
MANIFEST_PATH = "docs/execution/lane_c/PILOT_V2_INTEGRATION_MANIFEST.yaml"

def git_blob_sha(path):
    raw = subprocess.check_output([
        "git", "cat-file", "blob", f"{ARTIFACT_COMMIT}:{path}"
    ])
    return hashlib.sha256(raw).hexdigest()


class TestManifestGitObjectHashes:

    def setup_method(self):
        with open(MANIFEST_PATH) as f:
            self.manifest = yaml.safe_load(f)

    def test_manifest_uses_correct_artifact_commit(self):
        impl_sha = self.manifest.get("artifact_implementation_sha", "")
        assert impl_sha == ARTIFACT_COMMIT, f"Expected {ARTIFACT_COMMIT}, got {impl_sha}"

    def test_no_stale_b7_references(self):
        impl_sha = self.manifest.get("artifact_implementation_sha", "")
        assert "b7adb0ff" not in impl_sha, "Stale b7adb0 ref in implementation sha"
        assert impl_sha.count("b7adb0ff") == 0

    def test_all_artifact_hashes_match_git_objects(self):
        outputs = self.manifest.get("outputs", {})
        mismatches = []
        for key, info in outputs.items():
            path = info.get("path", "")
            manifest_hash = info.get("sha256", "")
            try:
                git_hash = git_blob_sha(path)
                if git_hash != manifest_hash:
                    mismatches.append(f"{key}: manifest={manifest_hash[:16]} git={git_hash[:16]}")
            except subprocess.CalledProcessError:
                mismatches.append(f"{key}: git blob not found")
        assert len(mismatches) == 0, f"Hash mismatches: {mismatches}"

    def test_all_record_counts_match(self):
        outputs = self.manifest.get("outputs", {})
        mismatches = []
        for key, info in outputs.items():
            path = info.get("path", "")
            manifest_count = info.get("record_count", 0)
            try:
                if path.endswith(".sqlite") or path.endswith(".db") or path.endswith(".pdf"):
                    continue
                raw = subprocess.check_output(["git", "cat-file", "blob", f"{ARTIFACT_COMMIT}:{path}"])
                text = raw.decode("utf-8").strip()
                if path.endswith(".jsonl"):
                    actual = len(text.splitlines()) if text else 0
                else:
                    actual = 1 if text else 0
                if actual != manifest_count and path.endswith(".jsonl"):
                    mismatches.append(f"{key}: manifest={manifest_count}, actual={actual}")
            except subprocess.CalledProcessError:
                pass
        assert len(mismatches) == 0, f"Record count mismatches: {mismatches}"

    def test_decision_seal_present(self):
        outputs = self.manifest.get("outputs", {})
        assert "decision_seal" in outputs, "decision_seal missing from outputs"
        d = outputs["decision_seal"]
        assert d["record_count"] == 1

    def test_sqlite_index_present(self):
        outputs = self.manifest.get("outputs", {})
        assert "sqlite_index" in outputs, "sqlite_index missing from outputs"

    def test_audit_outputs_present(self):
        audit = self.manifest.get("audit_outputs", {})
        assert "integrity_audit" in audit, "integrity_audit missing"
        assert "integrity_audit_md" in audit, "integrity_audit_md missing"