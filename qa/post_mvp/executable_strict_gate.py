"""Executable Strict Gate — shared gate logic for production QA + mutation tests.

All functions are pure, deterministic, and return structured GateViolation lists.
No file I/O beyond reading provided data structures.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass
class GateViolation:
    code: str
    path_or_ref: str
    message: str
    severity: str = "ERROR"  # ERROR | WARNING
    rule_id: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# Credential Scan
# ═══════════════════════════════════════════════════════════════════════════

CREDENTIAL_PATTERNS: list[tuple[str, str, str]] = [
    (r"api_key\s*=\s*[\"']sk-", "API_KEY", "Hardcoded API key (sk- pattern)"),
    (r"api_secret\s*=\s*[\"'][^\"']+[\"']", "API_SECRET", "Hardcoded API secret"),
    (r"private_key\b\s*[=:]\s*[\"'](?!.*placeholder)", "PRIVATE_KEY", "Hardcoded private key"),
    (r"bearer_token\b\s*[=:]\s*[\"'][^\"']+[\"']", "BEARER_TOKEN", "Hardcoded bearer token"),
    (r"webhook_token\b\s*[=:]\s*[\"'][^\"']+[\"']", "WEBHOOK_TOKEN", "Hardcoded webhook token"),
    (r"signing_key\b\s*[=:]\s*[\"'][^\"']+[\"']", "SIGNING_KEY", "Hardcoded signing key"),
    (r"seed.?phrase\b\s*[=:]\s*[\"']\w{10,}", "SEED_PHRASE", "Hardcoded seed phrase"),
    (r"mnemonic\b\s*[=:]\s*[\"']\w{10,}", "MNEMONIC", "Hardcoded mnemonic"),
    (r"password\s*=\s*[\"'][^\"']{8,}[\"']", "PASSWORD", "Hardcoded password (8+ chars)"),
]

SCAN_ROOTS = ("market_radar/", "scripts/", "qa/", "config/")
SCAN_EXTS = (".py", ".json", ".yaml", ".yml", ".toml", ".env", ".ini", ".cfg")

# Files that define detection patterns — not actual credentials
PATTERN_DEFINITION_FILES = {
    # Scripts with test/configuration password entries (not real credentials)
    "scripts/test_market_radar_v112w_whale_position_live_source_plan.py",
    "scripts/test_market_radar_v112x_hyperliquid_one_shot_readonly_dryrun.py",

    "qa/mvpplus/qa_core.py",
    "qa/post_mvp/fault_corpus.py",
    "qa/post_mvp/executable_strict_gate.py",
}


def scan_credentials(
    repo_root: str,
    tracked_files: Sequence[str],
) -> list[GateViolation]:
    """Scan git-tracked files for hardcoded credentials.

    Args:
        repo_root: Absolute path to repository root.
        tracked_files: List of relative file paths from git ls-files.

    Returns:
        List of GateViolation for each credential found.
    """
    violations: list[GateViolation] = []
    for rel_path in tracked_files:
        if not any(rel_path.startswith(r) for r in SCAN_ROOTS):
            continue
        if not rel_path.endswith(SCAN_EXTS):
            continue
        if rel_path in PATTERN_DEFINITION_FILES:
            continue
        full_path = os.path.join(repo_root, rel_path)
        try:
            with open(full_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (FileNotFoundError, IOError):
            continue
        for pattern, code, desc in CREDENTIAL_PATTERNS:
            if re.search(pattern, content):
                violations.append(GateViolation(
                    code=code, path_or_ref=rel_path,
                    message=f"{desc} in {rel_path}",
                    severity="ERROR", rule_id="CREDENTIAL_HARDCODED",
                ))
    return violations


# ═══════════════════════════════════════════════════════════════════════════
# Runtime Artifact Validation
# ═══════════════════════════════════════════════════════════════════════════

FORBIDDEN_FILENAMES = {
    "state.db", "run_live.json", "live_market_response.json",
    "live_whale_response.json", "feed_cursor.json", "workbench_live.html",
}

# Hard-forbidden — rejected even in fixture/schema/evidence/candidate dirs
HARD_FORBIDDEN_BASENAMES = {"STOP", "feed_cursor.json"}
HARD_FORBIDDEN_EXTENSIONS = (".db", ".sqlite", ".sqlite3", ".lock")

# Runtime name patterns — only allowed in specific roots + exact_allowlist
RUNTIME_NAME_PATTERNS: list[tuple[str, str]] = [
    (r"^run_\d*.*\.json$", "run_*.json"),
    (r"^market_\d*.*\.json$", "market_*.json"),
    (r"^whale_\d*.*\.json$", "whale_*.json"),
    (r"^workbench.*\.html$", "workbench*.html"),
    (r"^live_.*response.*\.json$", "live_*response*.json"),
    (r"^raw_.*response.*\.json$", "raw_*response*.json"),
]


def validate_runtime_artifacts(
    tracked_files: Sequence[str],
    exact_allowlist: set[str] | None = None,
    fixture_roots: tuple[str, ...] = ("tests/",),
    schema_roots: tuple[str, ...] = ("schemas/",),
    evidence_roots: tuple[str, ...] = ("artifacts/evidence/",),
    candidate_roots: tuple[str, ...] = ("artifacts/candidate/", "data/fixtures/"),
) -> list[GateViolation]:
    """Validate that no runtime artifacts are tracked in git.

    Rules:
    1. Hard-forbidden basenames/extensions rejected ANYWHERE (db, lock, STOP, feed_cursor)
    2. Runtime name patterns rejected by default, allowed only in fixture/schema/evidence/candidate
    3. Exact allowlist can exempt specific historic files from rule #2 (NOT rule #1)
    """
    if exact_allowlist is None:
        exact_allowlist = set()
    violations: list[GateViolation] = []

    def _in_allowed_root(path: str) -> bool:
        # Precise fixture check: must contain /fixtures/ subdirectory
        if "/fixtures/" in path:
            return True
        # Schema, evidence, candidate — prefix check
        for root in (schema_roots + evidence_roots + candidate_roots):
            if path.startswith(root):
                return True
        return False

    for rel_path in tracked_files:
        basename = os.path.basename(rel_path)

        # Rule 1: Hard-forbidden — fail ANYWHERE, even with exact_allowlist
        if basename in HARD_FORBIDDEN_BASENAMES:
            violations.append(GateViolation(
                code="RUNTIME_ARTIFACT_FORBIDDEN", path_or_ref=rel_path,
                message=f"Hard-forbidden file (rejected anywhere): {rel_path}",
                severity="ERROR", rule_id="RUNTIME_ARTIFACT_FORBIDDEN",
            ))
            continue

        if rel_path.endswith(HARD_FORBIDDEN_EXTENSIONS):
            violations.append(GateViolation(
                code="RUNTIME_ARTIFACT_FORBIDDEN", path_or_ref=rel_path,
                message=f"Hard-forbidden extension (rejected anywhere): {rel_path}",
                severity="ERROR", rule_id="RUNTIME_ARTIFACT_FORBIDDEN",
            ))
            continue

        # Check exact allowlist for remaining checks
        if rel_path in exact_allowlist:
            continue

        # Rule 2: Runtime name patterns — only in allowed roots
        import re as _re
        matched_pattern = None
        for pattern, desc in RUNTIME_NAME_PATTERNS:
            if _re.search(pattern, basename):
                matched_pattern = desc
                break

        if matched_pattern:
            if not _in_allowed_root(rel_path):
                violations.append(GateViolation(
                    code="RUNTIME_ARTIFACT_PATTERN", path_or_ref=rel_path,
                    message=f"Runtime artifact pattern '{matched_pattern}' outside allowed root: {rel_path}",
                    severity="ERROR", rule_id="RUNTIME_ARTIFACT_PATTERN",
                ))

    return violations


# ═══════════════════════════════════════════════════════════════════════════
# Owned Paths Validation
# ═══════════════════════════════════════════════════════════════════════════


def validate_owned_paths(
    changed_files: Sequence[str],
    allowed_roots: tuple[str, ...] = ("qa/post_mvp/", "tests/post_mvp/independent_qa/",
                                        "scripts/post_mvp/qa/", "docs/qa/"),
    allowed_exact: set[str] | None = None,
) -> list[GateViolation]:
    """Validate that only owned paths are modified.

    Args:
        changed_files: List of changed file paths.
        allowed_roots: Directory prefixes that are owned.
        allowed_exact: Exact file paths that are owned.

    Returns:
        List of GateViolation for each unowned file.
    """
    if allowed_exact is None:
        allowed_exact = set()
    violations: list[GateViolation] = []
    for f in changed_files:
        if not f:
            continue
        if f in allowed_exact:
            continue
        if any(f.startswith(r) for r in allowed_roots):
            continue
        violations.append(GateViolation(
            code="OWNED_PATH_VIOLATION", path_or_ref=f,
            message=f"Change outside owned paths: {f}",
            severity="ERROR", rule_id="OWNED_PATH_VIOLATION",
        ))
    return violations


# ═══════════════════════════════════════════════════════════════════════════
# Frozen Ref Validation
# ═══════════════════════════════════════════════════════════════════════════


def validate_frozen_refs(
    actual_refs: Mapping[str, str],
    expected_refs: Mapping[str, str],
) -> list[GateViolation]:
    """Validate that frozen refs haven't changed.

    Args:
        actual_refs: Dict mapping ref name -> current SHA.
        expected_refs: Dict mapping ref name -> expected SHA.

    Returns:
        List of GateViolation for each changed ref.
    """
    violations: list[GateViolation] = []
    for ref, expected_sha in expected_refs.items():
        actual_sha = actual_refs.get(ref, "")
        if actual_sha != expected_sha:
            violations.append(GateViolation(
                code="FROZEN_REF_CHANGED", path_or_ref=ref,
                message=f"{ref}: expected {expected_sha[:12]}, got {actual_sha[:12]}",
                severity="ERROR", rule_id="FROZEN_REF_CHANGED",
            ))
    return violations


# ═══════════════════════════════════════════════════════════════════════════
# XSS Corpus Validation
# ═══════════════════════════════════════════════════════════════════════════

XSS_REQUIRED_TYPES: set[str] = {
    "SCRIPT_TAG", "IMG_ONERROR", "SVG_ONLOAD",
    "JAVASCRIPT_URL", "ATTRIBUTE_INJECTION",
}

XSS_TYPE_MAP: dict[str, tuple[str, ...]] = {
    "SCRIPT_TAG": ("<script", "<Script", "<SCRIPT"),
    "IMG_ONERROR": ("onerror=", "onError="),
    "SVG_ONLOAD": ("<svg", "onload="),
    "JAVASCRIPT_URL": ("javascript:", "javaScript:"),
    "ATTRIBUTE_INJECTION": ('" onmouseover=', '" onfocus=', "onfocus=", "onmouseover="),
    "ENCODED_PAYLOAD": ("&#", "&lt;", "&gt;"),
    "MARKDOWN_HTML_MIXED": ("[", "](", "javascript:"),
}


def validate_xss_corpus(
    cases: Sequence[Mapping[str, Any]],
    required_types: set[str] | None = None,
) -> list[GateViolation]:
    """Validate XSS corpus has required distinct attack types.

    Args:
        cases: List of case dicts with 'tags' and 'description' keys.
        required_types: Set of required XSS type identifiers.

    Returns:
        List of GateViolation for missing types or insufficient coverage.
    """
    if required_types is None:
        required_types = XSS_REQUIRED_TYPES
    violations: list[GateViolation] = []

    # Check total count
    xss_cases = [c for c in cases if "xss" in str(c.get("tags", [])).lower()]
    if len(xss_cases) < 5:
        violations.append(GateViolation(
            code="XSS_INSUFFICIENT_COUNT", path_or_ref="corpus",
            message=f"Only {len(xss_cases)} XSS cases, need ≥5",
            severity="ERROR", rule_id="XSS_INSUFFICIENT_COUNT",
        ))

    # Check distinct types
    found_types = set()
    for case in xss_cases:
        desc = str(case.get("description", ""))
        # Extract all string values from fixture recursively
        fixture = case.get("fixture", {})
        if isinstance(fixture, dict):
            for v in fixture.values():
                if isinstance(v, str):
                    desc += " " + v
                elif isinstance(v, dict):
                    for v2 in v.values():
                        if isinstance(v2, str):
                            desc += " " + v2
        elif isinstance(fixture, str):
            desc += " " + fixture
        for type_name, patterns in XSS_TYPE_MAP.items():
            if any(p in desc for p in patterns):
                found_types.add(type_name)

    missing = required_types - found_types
    if missing:
        violations.append(GateViolation(
            code="XSS_MISSING_TYPES", path_or_ref="corpus",
            message=f"Missing XSS types: {missing}. Found: {found_types}",
            severity="ERROR", rule_id="XSS_MISSING_TYPES",
        ))

    return violations


# ═══════════════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════════════

import os  # noqa: E402 — needed by scan_credentials
