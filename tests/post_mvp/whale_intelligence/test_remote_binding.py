"""Remote binding verification — absolute path scan, mapping audit, SHA checks.

Ensures the branch is free of local absolute references and that the
corpus contract is clean before remote binding.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V2_RUNNER = ROOT / "tests" / "post_mvp" / "whale_intelligence" / "test_whale_replay_corpus_v2.py"
V2_CORPUS = ROOT / "tests" / "mvpplus" / "whale_domain" / "fixtures" / "whale_replay_corpus_v2.json"
V1_CORPUS = ROOT / "tests" / "mvpplus" / "whale_domain" / "fixtures" / "whale_replay_corpus_v1.json"
GEN_SCRIPT = ROOT / "tests" / "mvpplus" / "whale_domain" / "fixtures" / "gen_v2_corpus.py"
EVIDENCE_R05 = ROOT / "artifacts" / "evidence" / "w2_post_mvp_whale_portfolio_intelligence_r05.json"


class TestAbsolutePathScan(unittest.TestCase):
    """No local absolute paths in owned source files."""

    OWNED_EXTS = (".py", ".md", ".json")
    OWNED_DIRS = [
        "tests/post_mvp/whale_intelligence",
        "tests/mvpplus/whale_domain/fixtures",
        "docs/whale_intelligence",
    ]
    FORBIDDEN_PATTERNS = [
        "C:\\Users\\",
        "C:\\tmp\\",
        "/home/",
        "/Users/",
    ]

    def _check_file(self, path: Path, label: str):
        if not path.exists():
            return  # evidence may not exist yet
        content = path.read_text(encoding="utf-8", errors="replace")
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern in content:
                # Find the exact line
                for i, line in enumerate(content.split("\n"), 1):
                    if pattern in line:
                        self.fail(
                            f"{label}:{i}: absolute path '{pattern}' found:\n  {line.strip()}"
                        )

    def test_v2_runner_no_absolute_paths(self):
        self._check_file(V2_RUNNER, "test_whale_replay_corpus_v2.py")

    def test_v2_corpus_no_absolute_paths(self):
        self._check_file(V2_CORPUS, "whale_replay_corpus_v2.json")

    def test_v1_corpus_no_absolute_paths(self):
        self._check_file(V1_CORPUS, "whale_replay_corpus_v1.json")

    def test_generator_no_absolute_paths(self):
        self._check_file(GEN_SCRIPT, "gen_v2_corpus.py")


class TestCorpusContract(unittest.TestCase):
    """Corpus structure and case coverage."""

    def test_v2_case_ids_c101_to_c171(self):
        with open(V2_CORPUS, "r", encoding="utf-8") as f:
            corpus = json.load(f)
        cases = corpus.get("cases", [])
        ids = [c["case_id"] for c in cases]
        self.assertEqual(len(ids), 71, "V2 must have 71 cases")
        expected = [f"C{i}" for i in range(101, 172)]
        self.assertEqual(ids, expected, "V2 case IDs must be C101–C171")

    def test_v1_case_count(self):
        with open(V1_CORPUS, "r", encoding="utf-8") as f:
            corpus = json.load(f)
        self.assertEqual(len(corpus.get("cases", [])), 30)

    def test_v2_risk_rules_use_full_rule_ids(self):
        """Corpus must use full rule_ids like PR1_HIGH_GROSS_EXPOSURE, not short codes."""
        with open(V2_CORPUS, "r", encoding="utf-8") as f:
            corpus = json.load(f)
        for case in corpus["cases"]:
            for rule in case.get("expected_risk_rules", []):
                self.assertIn(
                    "_", rule,
                    f"{case['case_id']}: rule '{rule}' looks like a short code, "
                    f"expected full rule_id like PR1_HIGH_GROSS_EXPOSURE",
                )


class TestNoMappingConstants(unittest.TestCase):
    """Runner must NOT contain old mapping dicts."""

    FORBIDDEN_MAPPINGS = [
        "CORPUS_RULE_TO_FINDING_PREFIX",
        "CORPUS_CHANGE_TO_CODE",
        "CORPUS_ACTION_TO_CODE",
    ]

    def test_no_mapping_constants_in_runner(self):
        content = V2_RUNNER.read_text(encoding="utf-8")
        for const in self.FORBIDDEN_MAPPINGS:
            self.assertNotIn(
                const, content,
                f"Mapping constant '{const}' must be removed from runner",
            )


class TestEvidenceSHA(unittest.TestCase):
    """Evidence tested_commit must be a real SHA, not placeholder or self."""

    def setUp(self):
        if not EVIDENCE_R05.exists():
            self.skipTest("R05 evidence not yet created")

    def test_tested_commit_not_placeholder(self):
        with open(EVIDENCE_R05, "r", encoding="utf-8") as f:
            ev = json.load(f)
        tc = ev.get("tested_commit", "")
        self.assertNotEqual(tc, "", "tested_commit must not be empty")
        self.assertNotEqual(tc, "HEAD", "tested_commit must not be 'HEAD'")
        self.assertNotIn("PLACEHOLDER", tc.upper(),
                         "tested_commit must not contain PLACEHOLDER")
        self.assertEqual(len(tc), 40, "tested_commit must be a 40-char SHA")

    def test_tested_commit_not_self(self):
        """tested_commit must not equal the evidence commit itself."""
        import subprocess
        with open(EVIDENCE_R05, "r", encoding="utf-8") as f:
            ev = json.load(f)
        tc = ev.get("tested_commit", "")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=ROOT,
        ).stdout.strip()
        self.assertNotEqual(
            tc, head,
            "tested_commit must not equal the evidence commit (HEAD)",
        )


if __name__ == "__main__":
    unittest.main()
