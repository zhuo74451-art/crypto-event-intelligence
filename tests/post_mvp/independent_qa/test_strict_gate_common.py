"""Executable Strict Gate — production + mutation tests all calling common gate module."""
import json, os, sys, unittest, subprocess, tempfile, hashlib, re, shutil

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, PROJ)

from qa.post_mvp.executable_strict_gate import (
    GateViolation, scan_credentials, validate_runtime_artifacts,
    validate_owned_paths, validate_frozen_refs, validate_xss_corpus,
    FORBIDDEN_FILENAMES, XSS_REQUIRED_TYPES,
)
from qa.post_mvp.fault_corpus import FAULT_CASES

REPAIR_BASE = "b608dc36f472b9b59b7a2f1c3dfeb86a2863fa3d"
CANDIDATE_SHA = "9637a47249dde006f07c22c37002cb98ff6e168e"
MAIN_SHA = "a8fd827e0d4b7426326238e9d8e0be456e2474bd"


class GateTestBase(unittest.TestCase):
    def assert_violation(self, violations, rule_id=None, code=None):
        for v in violations:
            if rule_id and v.rule_id == rule_id:
                return
            if code and v.code == code:
                return
        raise AssertionError(f"No violation: rule_id={rule_id}, code={code}. Found: {[(x.code,x.rule_id) for x in violations]}")

    def assert_clean(self, violations):
        if violations:
            raise AssertionError(f"Unexpected violations: {[(v.code, v.path_or_ref, v.message[:40]) for v in violations]}")

    def make_repo(self, files):
        td = tempfile.mkdtemp()
        for path, content in files.items():
            fp = os.path.join(td, path)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "w") as f:
                f.write(content)
        subprocess.run(["git", "init"], capture_output=True, cwd=td)
        subprocess.run(["git", "add", "-A"], capture_output=True, cwd=td)
        r = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=td)
        return td, r.stdout.strip().split("\n")

    def clean(self, td):
        try:
            shutil.rmtree(td, ignore_errors=True)
        except Exception:
            pass


class TestCredentialsGate(GateTestBase):
    def test_finds_api_key(self):
        td, files = self.make_repo({"scripts/c.py": 'api_key = "sk-test"'})
        try:
            self.assert_violation(scan_credentials(td, files), code="API_KEY")
        finally:
            self.clean(td)

    def test_finds_private_key(self):
        td, files = self.make_repo({"scripts/k.py": 'private_key = "0xabc"'})
        try:
            self.assert_violation(scan_credentials(td, files), code="PRIVATE_KEY")
        finally:
            self.clean(td)

    def test_finds_bearer(self):
        td, files = self.make_repo({"scripts/a.py": 'bearer_token = "xyz"'})
        try:
            self.assert_violation(scan_credentials(td, files), code="BEARER_TOKEN")
        finally:
            self.clean(td)

    def test_skips_pattern_files(self):
        td, files = self.make_repo({"qa/mvpplus/qa_core.py": 'private_key = "x"'})
        try:
            self.assert_clean(scan_credentials(td, files))
        finally:
            self.clean(td)

    def test_real_repo_clean(self):
        r = subprocess.run(["git", "ls-files"], cwd=PROJ, capture_output=True, text=True)
        v = scan_credentials(PROJ, r.stdout.strip().split("\n"))
        safe = {"qa/mvpplus/qa_core.py", "qa/post_mvp/fault_corpus.py", "qa/post_mvp/executable_strict_gate.py"}
        real = [x for x in v if x.path_or_ref not in safe]
        self.assert_clean(real)


class TestArtifactGate(GateTestBase):
    def test_hard_forbidden_db_in_fixtures(self):
        """*.db rejected even in fixture dir."""
        self.assert_violation(validate_runtime_artifacts(["tests/x/fixtures/state.db"]), rule_id="RUNTIME_ARTIFACT_FORBIDDEN")

    def test_hard_forbidden_sqlite_in_schemas(self):
        self.assert_violation(validate_runtime_artifacts(["schemas/state.sqlite"]), rule_id="RUNTIME_ARTIFACT_FORBIDDEN")

    def test_hard_forbidden_db_in_evidence(self):
        self.assert_violation(validate_runtime_artifacts(["artifacts/evidence/state.db"]), rule_id="RUNTIME_ARTIFACT_FORBIDDEN")

    def test_hard_forbidden_lock_in_candidate(self):
        self.assert_violation(validate_runtime_artifacts(["artifacts/candidate/state.lock"]), rule_id="RUNTIME_ARTIFACT_FORBIDDEN")

    def test_hard_forbidden_feed_cursor_in_fixtures(self):
        self.assert_violation(validate_runtime_artifacts(["data/fixtures/feed_cursor.json"]), rule_id="RUNTIME_ARTIFACT_FORBIDDEN")

    def test_rejects_run_live(self):
        self.assert_violation(validate_runtime_artifacts(["results/run_live.json"]), rule_id="RUNTIME_ARTIFACT_PATTERN")

    def test_rejects_feed_cursor(self):
        self.assert_violation(validate_runtime_artifacts(["runs/feed_cursor.json"]), rule_id="RUNTIME_ARTIFACT_FORBIDDEN")

    def test_rejects_state_db(self):
        self.assert_violation(validate_runtime_artifacts(["data/state.db"]), rule_id="RUNTIME_ARTIFACT_FORBIDDEN")

    def test_rejects_live_market(self):
        self.assert_violation(validate_runtime_artifacts(["logs/live_market_response.json"]), rule_id="RUNTIME_ARTIFACT_PATTERN")

    def test_rejects_workbench_live(self):
        self.assert_violation(validate_runtime_artifacts(["output/workbench_live.html"]), rule_id="RUNTIME_ARTIFACT_PATTERN")

    
    def test_runtime_pattern_run_json(self):
        self.assert_violation(validate_runtime_artifacts(["results/run_001.json"]), rule_id="RUNTIME_ARTIFACT_PATTERN")

    def test_runtime_pattern_whale_json(self):
        self.assert_violation(validate_runtime_artifacts(["results/whale_positions.json"]), rule_id="RUNTIME_ARTIFACT_PATTERN")

    def test_runtime_pattern_market_json(self):
        self.assert_violation(validate_runtime_artifacts(["logs/market_snapshot.json"]), rule_id="RUNTIME_ARTIFACT_PATTERN")

    def test_runtime_pattern_workbench_html(self):
        self.assert_violation(validate_runtime_artifacts(["output/workbench_report.html"]), rule_id="RUNTIME_ARTIFACT_PATTERN")

    def test_runtime_pattern_live_response(self):
        self.assert_violation(validate_runtime_artifacts(["data/live_market_response.json"]), rule_id="RUNTIME_ARTIFACT_PATTERN")
    def test_rejects_stop(self):
        self.assert_violation(validate_runtime_artifacts(["STOP"]), rule_id="RUNTIME_ARTIFACT_FORBIDDEN")

    def test_accepts_fixture(self):
        self.assert_clean(validate_runtime_artifacts(["tests/x/fixtures/data.json"]))

    def test_accepts_schema(self):
        self.assert_clean(validate_runtime_artifacts(["schemas/ev.json"]))

    def test_accepts_evidence(self):
        self.assert_clean(validate_runtime_artifacts(["artifacts/evidence/w6_test.json"]))

    def test_accepts_manifest(self):
        self.assert_clean(validate_runtime_artifacts(["artifacts/candidate/m.json"], candidate_roots=("artifacts/candidate/",)))


class TestOwnedPathsGate(GateTestBase):
    def test_rejects_candidate_path(self):
        self.assert_violation(validate_owned_paths(["market_radar/x.py"]), rule_id="OWNED_PATH_VIOLATION")

    def test_accepts_qa_path(self):
        self.assert_clean(validate_owned_paths(["qa/post_mvp/x.py"]))

    def test_w6_paths_from_repair(self):
        r = subprocess.run(["git", "diff", "--name-only", REPAIR_BASE + "..HEAD"], cwd=PROJ, capture_output=True, text=True)
        v = validate_owned_paths(r.stdout.strip().split("\n"))
        non_evidence = [x for x in v if "evidence" not in x.path_or_ref]
        self.assert_clean(non_evidence)


class TestFrozenRefsGate(GateTestBase):
    W1_SHA = "22c088d7c7e9f77336056674248a539fdfa936d8"
    W2_SHA = "25bddbfb994c851845eef4940338897094ccade7"
    W3_SHA = "97e7310098a19ca11a7f28545e2d0a2cae89820f"
    W4_SHA = "a9b04727bcea77c69524d6c1225933df2c86045f"
    W5_SHA = "633606614695940f02a83bd0fce7695dbb469a65"

    refs = {
        "main": MAIN_SHA,
        "workbench/post-mvp-integration-candidate-v1": CANDIDATE_SHA,
        "workbench/post-mvp-whale-portfolio-intelligence-v1": W2_SHA,
        "workbench/post-mvp-event-clustering-v1": W3_SHA,
        "workbench/post-mvp-market-resilience-v1": W4_SHA,
        "workbench/post-mvp-ops-audit-recovery-v1": W5_SHA,
        "workbench/post-mvp-operator-workbench-v1": W1_SHA,
    }
    def test_candidate_main_unchanged(self):
        r = subprocess.run(["git", "ls-remote", "origin",
                          "refs/heads/main",
                          "refs/heads/workbench/post-mvp-integration-candidate-v1",
                          "refs/heads/workbench/post-mvp-whale-portfolio-intelligence-v1",
                          "refs/heads/workbench/post-mvp-event-clustering-v1",
                          "refs/heads/workbench/post-mvp-market-resilience-v1",
                          "refs/heads/workbench/post-mvp-ops-audit-recovery-v1",
                          "refs/heads/workbench/post-mvp-operator-workbench-v1"], capture_output=True, text=True, cwd=PROJ)
        actual = {}
        for line in r.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                ref = parts[1].replace("refs/heads/", "")
                actual[ref] = parts[0]
        self.assert_clean(validate_frozen_refs(actual, {"main": MAIN_SHA, "workbench/post-mvp-integration-candidate-v1": CANDIDATE_SHA,}))

    def test_detects_change(self):
        self.assert_violation(validate_frozen_refs({"main": "0"*40}, {"main": MAIN_SHA}), rule_id="FROZEN_REF_CHANGED")


class TestXssGate(GateTestBase):
    def test_corpus_ok(self):
        self.assert_clean(validate_xss_corpus(FAULT_CASES))

    def test_detects_insufficient(self):
        self.assert_violation(validate_xss_corpus([]), rule_id="XSS_INSUFFICIENT_COUNT")


class TestMutationGate(GateTestBase):
    def test_api_key_nested(self):
        td, f = self.make_repo({"scripts/deep/c.py": 'api_key = "sk-test"'})
        try: self.assert_violation(scan_credentials(td, f), code="API_KEY")
        finally: self.clean(td)

    def test_private_key_deep(self):
        td, f = self.make_repo({"market_radar/deep/k.py": 'private_key = "0xabc"'})
        try: self.assert_violation(scan_credentials(td, f), code="PRIVATE_KEY")
        finally: self.clean(td)

    def test_bearer_token(self):
        td, f = self.make_repo({"scripts/a.py": 'bearer_token = "xyz"'})
        try: self.assert_violation(scan_credentials(td, f), code="BEARER_TOKEN")
        finally: self.clean(td)

    def test_run_live_rejected(self):
        self.assert_violation(validate_runtime_artifacts(["results/run_live.json"]), rule_id="RUNTIME_ARTIFACT_PATTERN")

    def test_feed_cursor_rejected(self):
        self.assert_violation(validate_runtime_artifacts(["runs/feed_cursor.json"]), rule_id="RUNTIME_ARTIFACT_FORBIDDEN")

    def test_state_db_rejected(self):
        self.assert_violation(validate_runtime_artifacts(["data/state.db"]), rule_id="RUNTIME_ARTIFACT_FORBIDDEN")

    def test_fixture_accepted(self):
        self.assert_clean(validate_runtime_artifacts(["tests/x/fixtures/data.json"]))

    def test_schema_accepted(self):
        self.assert_clean(validate_runtime_artifacts(["schemas/x.json"]))

    def test_evidence_accepted(self):
        self.assert_clean(validate_runtime_artifacts(["artifacts/evidence/w6_test.json"]))

    def test_manifest_accepted(self):
        self.assert_clean(validate_runtime_artifacts(["artifacts/candidate/m.json"], candidate_roots=("artifacts/candidate/",)))

    def test_owned_path_rejects_candidate(self):
        self.assert_violation(validate_owned_paths(["market_radar/x.py"]), rule_id="OWNED_PATH_VIOLATION")

    def test_frozen_ref_detected(self):
        self.assert_violation(validate_frozen_refs({"main": "0"*40}, {"main": MAIN_SHA}), rule_id="FROZEN_REF_CHANGED")

    def test_xss_insufficient(self):
        self.assert_violation(validate_xss_corpus([]), rule_id="XSS_INSUFFICIENT_COUNT")

    def test_negative_temp_repo_run_live(self):
        td, f = self.make_repo({"results/run_live.json": "{}"})
        try: self.assert_violation(validate_runtime_artifacts(f), rule_id="RUNTIME_ARTIFACT_PATTERN")
        finally: self.clean(td)

    def test_negative_temp_repo_secret(self):
        td, f = self.make_repo({"scripts/deep/s.py": 'api_key = "sk-test"'})
        try: self.assert_violation(scan_credentials(td, f), code="API_KEY")
        finally: self.clean(td)

    def test_positive_fixture_accepted(self):
        td, f = self.make_repo({"tests/fixtures/x.json": "{}"})
        try: self.assert_clean(validate_runtime_artifacts(f))
        finally: self.clean(td)

    def test_positive_evidence_accepted(self):
        td, f = self.make_repo({"artifacts/evidence/w6.json": "{}"})
        try: self.assert_clean(validate_runtime_artifacts(f))
        finally: self.clean(td)


class TestSafetyRemaining(unittest.TestCase):
    def test_no_send_in_qa_no_scanner(self):
        r = subprocess.run(["git", "ls-files", "qa/"], cwd=PROJ, capture_output=True, text=True)
        for fn in r.stdout.strip().split("\n"):
            if not fn.endswith(".py") or "test_" in fn or fn.endswith("qa_core.py"):
                continue
            fp = os.path.join(PROJ, fn)
            if not os.path.isfile(fp):
                continue
            with open(fp) as f:
                for i, line in enumerate(f, 1):
                    if re.search(r"bot\.send_message|send_photo|telegram\.Bot|webhook\.post", line):
                        if not line.strip().startswith("#"):
                            self.fail(f"{fn}:{i}: send pattern")

    def test_evidence_valid_json(self):
        ev = os.path.join(PROJ, "artifacts", "evidence")
        if os.path.isdir(ev):
            for fn in os.listdir(ev):
                if fn.endswith(".json"):
                    with open(os.path.join(ev, fn)) as f:
                        self.assertIsInstance(json.load(f), dict)

    def test_evidence_no_bom(self):
        ev = os.path.join(PROJ, "artifacts", "evidence")
        if os.path.isdir(ev):
            for fn in os.listdir(ev):
                if fn.endswith(".json"):
                    with open(os.path.join(ev, fn), "rb") as f:
                        self.assertNotEqual(f.read(3), b"\xef\xbb\xbf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
