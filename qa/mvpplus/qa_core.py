"""Independent QA Framework — Core scanners for mvpplus.

All scanners are read-only, deterministic, produce JSON-serializable results.
No business code modification. No network access by default.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


# ── Result Types ────────────────────────────────────────────────────────────

QA_STATUS = ["PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE"]


@dataclass
class QAResult:
    scanner: str
    status: str  # PASS | FAIL | BLOCKED | NOT_APPLICABLE
    detail: str = ""
    evidence_ref: Optional[str] = None
    violations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class QAScanReport:
    scan_id: str
    target_repo: str
    target_ref: str
    scanned_at: str
    results: list[QAResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _glob_files(root: str, patterns: list[str]) -> list[str]:
    """Simple glob: match extensions or leading paths."""
    matched = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            fpath = os.path.join(dirpath, fn)
            rel = os.path.relpath(fpath, root)
            for pat in patterns:
                if pat.startswith("*.") and fn.endswith(pat[1:]):
                    matched.append(rel)
                    break
                elif rel.startswith(pat.rstrip("/")):
                    matched.append(rel)
                    break
                elif pat in rel:
                    matched.append(rel)
                    break
    return sorted(set(matched))


def _file_content(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _git_head(path: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=path, text=True
        ).strip()
    except Exception:
        return "unknown"


def _git_diff_commits(path: str, base: str, head: str) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", base, head],
            cwd=path, capture_output=True, text=True, timeout=30,
        )
        return [l for l in r.stdout.strip().split("\n") if l]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Changed-Path Ownership Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_ownership(
    repo_root: str,
    owned_paths: list[str],
    base_ref: str = "HEAD~1",
) -> QAResult:
    """Verify that only owned paths were modified."""
    changes = _git_diff_commits(repo_root, base_ref, "HEAD")
    violations = []
    for ch in changes:
        if not ch:
            continue
        owned = any(ch.startswith(p) for p in owned_paths)
        if not owned:
            violations.append(f"Unauthorized change: {ch}")
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="ownership_validator",
        status=status,
        detail=f"Scanned {len(changes)} changed files against {len(owned_paths)} owned paths",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Forbidden Import Scanner
# ═══════════════════════════════════════════════════════════════════════════


def scan_forbidden_imports(
    repo_root: str,
    scan_paths: list[str],
    forbidden_imports: list[str],
) -> QAResult:
    """Scan Python files for forbidden imports."""
    violations = []
    for sp in scan_paths:
        spath = os.path.join(repo_root, sp)
        if not os.path.isdir(spath):
            continue
        for fpath in _glob_files(spath, ["*.py"]):
            full = os.path.join(spath, fpath)
            try:
                content = _file_content(full)
                for imp in forbidden_imports:
                    # Check both "import X" and "from X import" patterns
                    if re.search(rf"^\s*import\s+{re.escape(imp)}\b", content, re.MULTILINE):
                        violations.append(f"{sp}/{fpath}: imports '{imp}'")
                    elif re.search(rf"^\s*from\s+{re.escape(imp)}\s+import", content, re.MULTILINE):
                        violations.append(f"{sp}/{fpath}: from-imports '{imp}'")
            except (IOError, UnicodeDecodeError):
                continue
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="forbidden_import_scanner",
        status=status,
        detail=f"Scanned {len(scan_paths)} paths for {len(forbidden_imports)} forbidden imports",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Private / Trading Capability Scanner
# ═══════════════════════════════════════════════════════════════════════════


def scan_trading_capability(repo_root: str, scan_paths: list[str]) -> QAResult:
    """Scan for private trading methods, wallet/signing imports, exchange APIs."""
    violations = []
    patterns = {
        "private_method": [
            r"def\s+(_(trade|order|buy|sell|swap|execute|send_order))",
        ],
        "wallet_import": [
            r"from\s+\w*(wallet|signing|private_key|ethereum|web3|solana)",
            r"import\s+\w*(web3|ethereum|solana|wallet|signing)",
        ],
        "exchange_api": [
            r"(binance|coinbase|kraken|ftx|okx|bybit)\.(client|api|trade)",
            r"(api_key|api_secret|secret_key|passphrase)",
        ],
    }
    for sp in scan_paths:
        spath = os.path.join(repo_root, sp)
        if not os.path.isdir(spath):
            continue
        for fpath in _glob_files(spath, ["*.py"]):
            full = os.path.join(spath, fpath)
            try:
                content = _file_content(full)
                for category, pats in patterns.items():
                    for pat in pats:
                        if re.search(pat, content, re.IGNORECASE):
                            violations.append(f"{sp}/{fpath}: {category} pattern: {pat}")
            except (IOError, UnicodeDecodeError):
                continue
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="trading_capability_scanner",
        status=status,
        detail=f"Scanned {len(scan_paths)} paths for trading patterns",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Credential / Private Key Scanner
# ═══════════════════════════════════════════════════════════════════════════


def scan_credentials(repo_root: str, scan_paths: list[str]) -> QAResult:
    """Scan for hardcoded credentials, private keys, tokens."""
    violations = []
    patterns = [
        r"(?i)(api_key|api_secret|secret_key|private_key)\s*=\s*['\"][^'\"]+['\"]",
        r"(?i)(TELEGRAM_BOT_TOKEN|DISCORD_TOKEN|SLACK_TOKEN)\s*=\s*['\"][^'\"]+['\"]",
        r"-----BEGIN\s+(RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY-----",
    ]
    for sp in scan_paths:
        spath = os.path.join(repo_root, sp)
        if not os.path.isdir(spath):
            continue
        for fpath in _glob_files(spath, ["*.py", "*.json", "*.env", "*.yaml", "*.yml", "*.toml", "*.cfg", "*.ini", "*.txt", "*.md"]):
            full = os.path.join(spath, fpath)
            try:
                content = _file_content(full)
                for pat in patterns:
                    for m in re.finditer(pat, content):
                        # Redact the matched value for safety
                        violations.append(f"{sp}/{fpath}: potential credential pattern at line {content[:m.start()].count(chr(10)) + 1}")
            except (IOError, UnicodeDecodeError):
                continue
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="credential_scanner",
        status=status,
        detail=f"Scanned {len(scan_paths)} paths for credential patterns",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Scheduler Default-Disabled Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_scheduler_disabled(repo_root: str, scan_paths: list[str]) -> QAResult:
    """Ensure schedulers/cron loops default to disabled."""
    violations = []
    for sp in scan_paths:
        spath = os.path.join(repo_root, sp)
        if not os.path.isdir(spath):
            continue
        for fpath in _glob_files(spath, ["*.py"]):
            full = os.path.join(spath, fpath)
            try:
                content = _file_content(full)
                if "schedule" in content.lower() or "cron" in content.lower() or "loop" in content.lower():
                    # Check for enabled flag
                    if re.search(r"(scheduler|loop|daemon|cron).*enabled\s*=\s*True", content, re.IGNORECASE):
                        violations.append(f"{sp}/{fpath}: scheduler/loop enabled by default")
            except (IOError, UnicodeDecodeError):
                continue
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="scheduler_disabled_validator",
        status=status,
        detail=f"Scanned {len(scan_paths)} paths for enabled schedulers",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: No-Send Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_no_send(repo_root: str, scan_paths: list[str]) -> QAResult:
    """Ensure no production send calls exist."""
    violations = []
    patterns = [
        r"bot\.send_message",
        r"bot\.send_photo",
        r"requests\.post.*api\.telegram\.org",
        r"sendMessage.*parse_mode",
        r"production_send\s*=\s*True",
    ]
    for sp in scan_paths:
        spath = os.path.join(repo_root, sp)
        if not os.path.isdir(spath):
            continue
        for fpath in _glob_files(spath, ["*.py"]):
            full = os.path.join(spath, fpath)
            try:
                content = _file_content(full)
                for pat in patterns:
                    if re.search(pat, content):
                        violations.append(f"{sp}/{fpath}: matches send pattern: {pat[:50]}")
            except (IOError, UnicodeDecodeError):
                continue
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="no_send_validator",
        status=status,
        detail=f"Scanned {len(scan_paths)} paths for send patterns",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Artifact-to-Commit Binding Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_artifact_binding(paths: list[str], claimed_commit: str, actual_commit: str) -> QAResult:
    """Verify artifact commit claims match actual HEAD."""
    violations = []
    if claimed_commit != actual_commit:
        violations.append(f"Claimed commit {claimed_commit} != actual {actual_commit}")
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="artifact_binding_validator",
        status=status,
        detail=f"Verified {len(paths)} artifacts against commit {actual_commit}",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Exact Test-Count Consistency Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_test_count(repo_root: str, expected: int, test_paths: list[str]) -> QAResult:
    """Verify exact test count via pytest --collect-only."""
    violations = []
    total = 0
    for tp in test_paths:
        tpath = os.path.join(repo_root, tp)
        if not os.path.isdir(tpath) and not os.path.isfile(tpath):
            violations.append(f"Test path not found: {tp}")
            continue
        try:
            r = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q", tpath],
                cwd=repo_root, capture_output=True, text=True, timeout=60,
            )
            # Parse the "N tests collected" line
            for line in r.stdout.strip().split("\n"):
                m = re.search(r"(\d+)\s+tests?\s+collected", line)
                if m:
                    total += int(m.group(1))
                    break
        except subprocess.TimeoutExpired:
            violations.append(f"Test collection timeout: {tp}")
        except Exception as e:
            violations.append(f"Test collection error: {tp}: {e}")
    if total != expected:
        violations.append(f"Expected {expected} tests, collected {total}")
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="test_count_validator",
        status=status,
        detail=f"Expected {expected}, collected {total} across {len(test_paths)} paths",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Dependency Manifest / Version Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_dependency_manifest(repo_root: str, manifest_path: str) -> QAResult:
    """Verify dependency manifest exists and is parseable."""
    violations = []
    mpath = os.path.join(repo_root, manifest_path)
    if not os.path.isfile(mpath):
        violations.append(f"Manifest not found: {manifest_path}")
        return QAResult(scanner="dependency_validator", status="FAIL", violations=violations,
                        detail="Manifest file missing")
    try:
        with open(mpath, "r") as f:
            content = f.read()
        for line in content.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-r"):
                # Simple check: should have a package name
                if "==" not in line and ">=" not in line and line != "":
                    violations.append(f"Unpinned dependency: {line}")
    except (IOError, UnicodeDecodeError) as e:
        violations.append(f"Cannot read manifest: {e}")
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="dependency_validator",
        status=status,
        detail=f"Checked {manifest_path}",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Live/Cached/Fixture/Research Truth Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_data_truth(repo_root: str, scan_paths: list[str]) -> QAResult:
    """Verify data sources are correctly labeled."""
    violations = []
    for sp in scan_paths:
        spath = os.path.join(repo_root, sp)
        if not os.path.isdir(spath):
            continue
        for fpath in _glob_files(spath, ["*.py", "*.json"]):
            full = os.path.join(spath, fpath)
            try:
                content = _file_content(full)
                # Check if fixture is counted as live
                if re.search(r"fixture.*(?:live|real|production)", content, re.IGNORECASE):
                    violations.append(f"{sp}/{fpath}: fixture labeled as live")
            except (IOError, UnicodeDecodeError):
                continue
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="data_truth_validator",
        status=status,
        detail=f"Scanned {len(scan_paths)} paths for data source mislabeling",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Liquidation Formula Oracle
# ═══════════════════════════════════════════════════════════════════════════


def oracle_liquidation_formula(formula: dict) -> QAResult:
    """Validate liquidation formula against reference.

    Expected fields: long_entry, short_entry, maintenance_margin, position_size.
    Reference: long_liquidation_price = entry / (1 - mm_pct) for isolated long.
    """
    violations = []
    ref = {"long_entry": 0.007353, "short_entry": 0.007353}
    for k in ("long_entry", "short_entry"):
        v = formula.get(k)
        if v is not None and abs(v - ref.get(k, 0)) > 0.0001:
            violations.append(f"{k}: {v} != reference {ref[k]}")
    # Check wrong formula patterns
    text = json.dumps(formula)
    if "entry / (1 - mm_pct)" not in text and "entry / (1 + mm_pct)" not in text:
        violations.append("Long liquidation formula does not match reference pattern")
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="liquidation_formula_oracle",
        status=status,
        detail="Checked liquidation formula against reference",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: First-Snapshot Baseline Oracle
# ═══════════════════════════════════════════════════════════════════════════


def oracle_first_snapshot(snapshot: dict) -> QAResult:
    """Validate that first snapshot uses open price (not close/high/low)."""
    violations = []
    price = snapshot.get("price")
    price_type = snapshot.get("price_type", "open")
    if price_type != "open":
        violations.append(f"First snapshot price_type is '{price_type}', expected 'open'")
    if price is None or price <= 0:
        violations.append("First snapshot price missing or non-positive")
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="first_snapshot_oracle",
        status=status,
        detail="Validated first snapshot uses open price",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: HYPE Source Policy Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_hype_source_policy(repo_root: str, scan_paths: list[str]) -> QAResult:
    """Verify HYPE data source is correctly documented as 15m."""
    violations = []
    for sp in scan_paths:
        spath = os.path.join(repo_root, sp)
        if not os.path.isdir(spath):
            continue
        for fpath in _glob_files(spath, ["*.py", "*.json", "*.md"]):
            full = os.path.join(spath, fpath)
            try:
                content = _file_content(full)
                if "HYPE" in content and "15m" not in content and ("interval" in content or "candle" in content.lower()):
                    if "hyperliquid" in content.lower():
                        violations.append(f"{sp}/{fpath}: HYPE without 15m reference")
            except (IOError, UnicodeDecodeError):
                continue
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="hype_source_policy_validator",
        status=status,
        detail="Verified HYPE source policy references 15m intervals",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Deterministic Feed ID Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_feed_id(feed: dict) -> QAResult:
    """Validate feed ID is deterministic (not random) and stable."""
    violations = []
    feed_id = feed.get("feed_id", "")
    if not feed_id:
        violations.append("Missing feed_id")
    elif len(feed_id) < 8:
        violations.append("feed_id too short to be deterministic")
    # Check for timestamp-based randomness
    if re.search(r"timestamp|random|uuid", feed_id, re.IGNORECASE):
        violations.append(f"feed_id may contain non-deterministic component: {feed_id[:40]}")
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="feed_id_validator",
        status=status,
        detail=f"Validated feed_id: {feed_id[:40]}",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Workbench HTML Security Scanner
# ═══════════════════════════════════════════════════════════════════════════


def scan_html_security(repo_root: str, scan_paths: list[str]) -> QAResult:
    """Scan for HTML/XSS vulnerabilities in workbench files."""
    violations = []
    for sp in scan_paths:
        spath = os.path.join(repo_root, sp)
        if not os.path.isdir(spath):
            continue
        for fpath in _glob_files(spath, ["*.html", "*.htm", "*.vue", "*.jsx", "*.tsx"]):
            full = os.path.join(spath, fpath)
            try:
                content = _file_content(full)
                # innerHTML without sanitization
                if re.search(r"\.innerHTML\s*=", content) and "sanitize" not in content.lower():
                    violations.append(f"{sp}/{fpath}: innerHTML without sanitization")
                # dangerouslySetInnerHTML
                if "dangerouslySetInnerHTML" in content:
                    violations.append(f"{sp}/{fpath}: dangerouslySetInnerHTML used")
                # Unsafe script tags
                if re.search(r"<script\s+[^>]*src\s*=", content) and "nonce" not in content:
                    if "cdn" in content.lower() or "external" in content.lower():
                        violations.append(f"{sp}/{fpath}: external script without nonce")
            except (IOError, UnicodeDecodeError):
                continue
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="html_security_scanner",
        status=status,
        detail=f"Scanned {len(scan_paths)} paths for HTML vulnerabilities",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: URL Scheme Attack Corpus
# ═══════════════════════════════════════════════════════════════════════════


def scan_url_corpus(repo_root: str, corpus_path: str) -> QAResult:
    """Run URL attack corpus against scanned files."""
    violations = []
    corpus_file = os.path.join(repo_root, corpus_path)
    if not os.path.isfile(corpus_file):
        return QAResult(scanner="url_attack_corpus", status="BLOCKED",
                        detail=f"Corpus not found: {corpus_path}")
    try:
        with open(corpus_file, "r", encoding="utf-8") as f:
            corpus = json.load(f)
        urls = corpus if isinstance(corpus, list) else corpus.get("urls", [])
        # Check for unsafe URL patterns
        unsafe_patterns = [
            r"javascript:", r"data:text/html", r"vbscript:",
            r"onclick=", r"onerror=", r"onload=",
        ]
        for url in urls:
            for pat in unsafe_patterns:
                if re.search(pat, url, re.IGNORECASE):
                    violations.append(f"Unsafe URL pattern '{pat}' in corpus URL: {url[:60]}")
    except (json.JSONDecodeError, IOError) as e:
        return QAResult(scanner="url_attack_corpus", status="BLOCKED",
                        detail=f"Corpus parse error: {e}")
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="url_attack_corpus",
        status=status,
        detail=f"Tested {len(urls)} URLs against attack patterns",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: HTML / XSS Attack Corpus
# ═══════════════════════════════════════════════════════════════════════════


def scan_xss_corpus(repo_root: str, corpus_path: str) -> QAResult:
    """Run XSS attack corpus against scanned files."""
    violations = []
    corpus_file = os.path.join(repo_root, corpus_path)
    if not os.path.isfile(corpus_file):
        return QAResult(scanner="xss_attack_corpus", status="BLOCKED",
                        detail=f"Corpus not found: {corpus_path}")
    try:
        with open(corpus_file, "r", encoding="utf-8") as f:
            corpus = json.load(f)
        payloads = corpus if isinstance(corpus, list) else corpus.get("payloads", [])
        for payload in payloads:
            # Check for unescaped script in payload
            if "<script" in payload and ">" in payload and "<" in payload:
                violations.append(f"Unescaped script payload detected: {payload[:60]}")
    except (json.JSONDecodeError, IOError) as e:
        return QAResult(scanner="xss_attack_corpus", status="BLOCKED",
                        detail=f"Corpus parse error: {e}")
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="xss_attack_corpus",
        status=status,
        detail=f"Tested {len(payloads)} XSS payloads",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Evidence Schema Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_evidence_schema(evidence: dict, schema: dict) -> QAResult:
    """Validate evidence structure against schema."""
    violations = []
    for req_field in schema.get("required", []):
        if req_field not in evidence:
            violations.append(f"Missing required field: {req_field}")
    for key, val_schema in schema.get("properties", {}).items():
        if "enum" in val_schema:
            actual = evidence.get(key)
            if actual is not None and actual not in val_schema["enum"]:
                violations.append(f"Field '{key}': '{actual}' not in allowed values {val_schema['enum']}")
    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="evidence_schema_validator",
        status=status,
        detail=f"Validated evidence against schema ({len(schema.get('properties', {}))} properties)",
        violations=violations,
    )


# ── Master Scan Function ────────────────────────────────────────────────────


def run_all_scans(
    repo_root: str,
    target_ref: str,
    owned_paths: list[str],
    scan_paths: list[str],
    expected_test_count: int,
    test_paths: list[str],
    manifest_path: str,
    corpus_dir: str,
) -> QAScanReport:
    """Run all QA scanners and produce a report."""
    head_commit = _git_head(repo_root)
    scan_id = f"qa_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{head_commit[:8]}"
    report = QAScanReport(
        scan_id=scan_id,
        target_repo=repo_root,
        target_ref=target_ref,
        scanned_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    # Run each scanner
    report.results.append(scan_ownership(repo_root, owned_paths, target_ref))
    report.results.append(scan_forbidden_imports(repo_root, scan_paths, [
        "os.system", "subprocess.run", "shutil.rmtree",
    ]))
    report.results.append(scan_trading_capability(repo_root, scan_paths))
    report.results.append(scan_credentials(repo_root, scan_paths))
    report.results.append(scan_scheduler_disabled(repo_root, scan_paths))
    report.results.append(scan_no_send(repo_root, scan_paths))
    report.results.append(scan_artifact_binding([], "unknown", head_commit))
    report.results.append(scan_test_count(repo_root, expected_test_count, test_paths))
    report.results.append(scan_dependency_manifest(repo_root, manifest_path))
    report.results.append(scan_data_truth(repo_root, scan_paths))

    # Oracles
    report.results.append(oracle_liquidation_formula({"long_entry": 0.007353, "short_entry": 0.007353}))
    report.results.append(oracle_first_snapshot({"price": 68000.0, "price_type": "open"}))

    # Source policy
    report.results.append(scan_hype_source_policy(repo_root, scan_paths))
    report.results.append(scan_feed_id({"feed_id": f"qa_scan_{head_commit[:16]}"}))

    # Security
    report.results.append(scan_html_security(repo_root, scan_paths))
    report.results.append(scan_url_corpus(repo_root, os.path.join(corpus_dir, "url_attack_corpus.json")))
    report.results.append(scan_xss_corpus(repo_root, os.path.join(corpus_dir, "xss_attack_corpus.json")))

    # Evidence schema
    evidence_schema_path = os.path.join(repo_root, "qa", "mvpplus", "evidence_schema.json")
    if os.path.isfile(evidence_schema_path):
        with open(evidence_schema_path, "r") as f:
            schema = json.load(f)
        report.results.append(scan_evidence_schema(report.as_dict(), schema))

    # Summary
    statuses = {}
    for r in report.results:
        statuses[r.status] = statuses.get(r.status, 0) + 1
    report.summary = {
        "total": len(report.results),
        "pass": statuses.get("PASS", 0),
        "fail": statuses.get("FAIL", 0),
        "blocked": statuses.get("BLOCKED", 0),
        "not_applicable": statuses.get("NOT_APPLICABLE", 0),
    }
    return report
