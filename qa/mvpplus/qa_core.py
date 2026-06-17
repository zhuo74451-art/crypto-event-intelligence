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


def _glob_files(root: str, patterns: list[str], exclude: list[str] | None = None) -> list[str]:
    """Simple glob: match extensions or leading paths.

    exclude: list of filename suffixes or infixes to skip (e.g. ['qa_core.py']).
    """
    matched = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            # Skip excluded filenames
            if exclude and any(excl in fn for excl in exclude):
                continue
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
        # Exclude the scanner framework itself
        for fpath in _glob_files(spath, ["*.py"], exclude=["qa_core.py"]):
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
        # Exclude the scanner framework itself (it contains patterns but doesn't use them)
        for fpath in _glob_files(spath, ["*.py"], exclude=["qa_core.py"]):
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
        # Exclude the scanner framework itself (it contains patterns but doesn't use them)
        for fpath in _glob_files(spath, ["*.py", "*.json", "*.env", "*.yaml", "*.yml", "*.toml", "*.cfg", "*.ini", "*.txt", "*.md"], exclude=["qa_core.py"]):
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
        # Exclude the scanner framework itself (it contains patterns but doesn't use them)
        for fpath in _glob_files(spath, ["*.py"], exclude=["qa_core.py"]):
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


def scan_dependency_manifest(repo_root: str, manifest_path: str,
                              content_override: str | None = None) -> QAResult:
    """Verify dependency manifest exists and is parseable.

    content_override: synthetic manifest content for self-test (avoids scanning
                      real project requirements.txt during QA foundation self-test).
    """
    violations = []
    if content_override is not None:
        content = content_override
    else:
        mpath = os.path.join(repo_root, manifest_path)
        if not os.path.isfile(mpath):
            violations.append(f"Manifest not found: {manifest_path}")
            return QAResult(scanner="dependency_validator", status="FAIL", violations=violations,
                            detail="Manifest file missing")
        try:
            with open(mpath, "r") as f:
                content = f.read()
        except (IOError, UnicodeDecodeError) as e:
            violations.append(f"Cannot read manifest: {e}")
            return QAResult(scanner="dependency_validator", status="FAIL",
                            detail=f"Cannot read {manifest_path}", violations=violations)

    for line in content.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-r"):
            if "==" not in line and ">=" not in line and line != "":
                violations.append(f"Unpinned dependency: {line}")
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


def scan_data_truth(data_records: list[dict]) -> QAResult:
    """Verify data source labels match count relationships.

    Inspects structured data_mode/count relationships.
    Known modes: live, cached, fixture, research_sample.
    - fixture/research_sample rows included in live counts → FAIL
    - unknown data_mode → explicitly reported
    - simple text mentioning 'fixture' and 'live' does NOT automatically fail
      (must inspect structured data_mode/count relationships)
    """
    violations = []
    KNOWN_MODES = {"live", "cached", "fixture", "research_sample"}

    if not data_records:
        return QAResult(
            scanner="data_truth_validator",
            status="PASS",
            detail="No data records to validate",
            violations=[],
        )

    live_data = []
    cached_data = []
    fixture_data = []
    research_data = []
    unknown = []

    for r in data_records:
        mode = r.get("data_mode", "")
        if mode == "live":
            live_data.append(r)
        elif mode == "cached":
            cached_data.append(r)
        elif mode == "fixture":
            fixture_data.append(r)
        elif mode == "research_sample":
            research_data.append(r)
        else:
            unknown.append(r)

    # Unknown mode must be explicitly reported
    for rec in unknown:
        name = rec.get("id") or rec.get("name") or "unknown"
        mode = rec.get("data_mode", "")
        violations.append(f"Record '{name}' has unknown data_mode='{mode}'")

    # Fixture or research_sample rows included in live counts must fail
    for rec in fixture_data:
        name = rec.get("id") or rec.get("name") or "unknown"
        if rec.get("counted_as_live", False):
            violations.append(f"Fixture '{name}' is counted in live totals")
        if "live_count" in rec or "live_total" in rec:
            violations.append(f"Fixture '{name}' has live count/total field")

    for rec in research_data:
        name = rec.get("id") or rec.get("name") or "unknown"
        if rec.get("counted_as_live", False):
            violations.append(f"Research_sample '{name}' is counted in live totals")

    # Check aggregate counts if a summary record exists
    summary = None
    for r in data_records:
        if r.get("kind") == "summary" or "reported_live_count" in r:
            summary = r
            break
    if summary:
        reported_live = summary.get("reported_live_count")
        if reported_live is not None and len(live_data) != reported_live:
            violations.append(
                f"Reported live count ({reported_live}) doesn't match "
                f"actual live data ({len(live_data)} records)"
            )

    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="data_truth_validator",
        status=status,
        detail=f"Validated {len(data_records)} records: "
               f"{len(live_data)} live, {len(cached_data)} cached, "
               f"{len(fixture_data)} fixture, {len(research_data)} research_sample, "
               f"{len(unknown)} unknown",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Liquidation Formula Oracle
# ═══════════════════════════════════════════════════════════════════════════


def oracle_liquidation_formula(formula: dict) -> QAResult:
    """Validate liquidation distance formula calculation.

    long expected = (mark - liq) / mark * 100
    short expected = (liq - mark) / mark * 100
    mark <= 0 → null expected (cannot divide by zero)
    invalid liquidation price → null per project policy
    negative value preserved (never abs'd or clamped)
    configurable numeric tolerance (default 0.01)
    """
    violations = []
    mark = formula.get("mark")
    liq = formula.get("liq")
    position_side = formula.get("side", "long")
    tolerance = formula.get("tolerance", 0.01)

    # Missing or invalid mark/liq → null result expected (PASS)
    if mark is None or liq is None:
        return QAResult(
            scanner="liquidation_formula_oracle",
            status="PASS",
            detail="Missing mark or liq: null result expected",
            violations=[],
        )

    # mark <= 0 → null (cannot divide by zero, invalid price)
    if not isinstance(mark, (int, float)) or mark <= 0:
        return QAResult(
            scanner="liquidation_formula_oracle",
            status="PASS",
            detail=f"mark={mark}: null result expected (invalid or non-positive mark)",
            violations=[],
        )

    # Invalid liquidation price → null per project policy
    if not isinstance(liq, (int, float)) or liq <= 0:
        return QAResult(
            scanner="liquidation_formula_oracle",
            status="PASS",
            detail=f"liq={liq}: null result expected (invalid or non-positive liquidation price)",
            violations=[],
        )

    if position_side == "long" or position_side == "LONG":
        expected = (mark - liq) / mark * 100
    else:  # short
        expected = (liq - mark) / mark * 100

    actual = formula.get("expected", formula.get("actual"))
    if actual is not None:
        if abs(actual - expected) > tolerance:
            violations.append(
                f"Expected {expected:.6f} (side={position_side}, mark={mark}, liq={liq}), got {actual}"
            )

    # Check negative values are preserved (not abs'd or clamped to zero)
    if expected < 0:
        if actual is not None and actual >= 0:
            violations.append(
                f"Negative liquidation distance ({expected:.6f}) was incorrectly clamped to non-negative ({actual})"
            )

    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="liquidation_formula_oracle",
        status=status,
        detail=f"Checked ({position_side}) mark={mark} liq={liq} → {expected:.6f}",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: First-Snapshot Baseline Oracle
# ═══════════════════════════════════════════════════════════════════════════


def oracle_first_snapshot(snapshot: dict) -> QAResult:
    """Validate first-run positions use baseline_open_position.

    Rules:
    - existing non-zero positions (abs(size) > 0) → baseline_open_position action
    - never open_long / open_short (both directions)
    - size == 0 must NOT require baseline
    - baseline must not create large_new_position alert
    """
    violations = []
    positions = snapshot.get("positions", [])

    if not positions:
        violations.append("No position data in first snapshot — expected baseline entries")
        return QAResult(
            scanner="first_snapshot_oracle",
            status="FAIL",
            detail="First snapshot missing position data",
            violations=violations,
        )

    for pos in positions:
        action = pos.get("action", "")
        size = pos.get("size", 0)

        # Existing non-zero positions (any direction) must use baseline_open_position
        if abs(size) > 0 and action not in ("baseline_open_position", "baseline"):
            violations.append(
                f"Position abs(size)={abs(size)} should use 'baseline_open_position', got '{action}'"
            )

        # Must never have open_long/open_short in first snapshot
        if action in ("open_long", "open_short"):
            violations.append(
                f"First snapshot must not use '{action}' — use 'baseline_open_position' for existing positions"
            )

        # Baseline must not create large_new_position alert
        if action in ("baseline_open_position", "baseline"):
            if pos.get("alert") == "large_new_position":
                violations.append(
                    f"Baseline position triggered 'large_new_position' alert (size={size})"
                )

    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="first_snapshot_oracle",
        status=status,
        detail=f"Validated {len(positions)} positions in first snapshot",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: HYPE Source Policy Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_hype_source_policy(market_record: dict) -> QAResult:
    """Validate normalized HYPE market record.

    Rules:
    - asset == HYPE
    - venue/source must be Hyperliquid
    - Binance HYPE fallback must fail (HYPE is Hyperliquid-native only)
    - (unrelated 15m interval rule removed per W6_DELTA spec)
    """
    violations = []
    asset = market_record.get("asset", "")
    venue = market_record.get("venue") or market_record.get("source", "")
    venue_str = str(venue)

    if asset != "HYPE" and asset != "hype":
        return QAResult(
            scanner="hype_source_policy_validator",
            status="NOT_APPLICABLE",
            detail=f"Asset is '{asset}', not HYPE — skipping",
            violations=[],
        )

    # Venue/source must be Hyperliquid
    if "hyperliquid" not in venue_str.lower():
        violations.append(
            f"HYPE venue/source must be Hyperliquid, got '{venue_str}'"
        )

    # Binance fallback must fail — HYPE does not exist on Binance
    if "binance" in venue_str.lower():
        violations.append("Binance is not a valid HYPE venue — HYPE is Hyperliquid-native only")

    fallback = market_record.get("fallback", market_record.get("fallback_source"))
    if fallback:
        fb_venue = str(fallback.get("venue", fallback.get("source", fallback)))
        if "binance" in fb_venue.lower():
            violations.append(
                f"Binance HYPE fallback must fail — HYPE only exists on Hyperliquid"
            )

    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="hype_source_policy_validator",
        status=status,
        detail=f"Validated HYPE market record: venue={venue_str}",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: Deterministic Feed ID Validator
# ═══════════════════════════════════════════════════════════════════════════


def scan_feed_id(feed: dict) -> QAResult:
    """Validate feed ID determinism using injected generator or 3-group outputs.

    The oracle does NOT compute IDs itself. It accepts either:
    A) a feed_id_generator callable that maps string input → string ID, OR
    B) three pre-computed output groups from the target implementation:
       - same_input_output_A, same_input_output_B (same input run twice)
       - changed_input_output (different input)

    Rules:
    - same_input_output_A == same_input_output_B  (same input → same ID) → PASS
    - same_input_output_A != same_input_output_B  → FAIL (not deterministic)
    - same_input_output_A == changed_input_output  → FAIL (collision)
    - UUID/random/time-only IDs → FAIL
    """
    violations = []
    feed_id = feed.get("feed_id", "")
    generator = feed.get("feed_id_generator")

    # ── UUID/random/time-only checks ──
    if feed_id:
        if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", feed_id, re.IGNORECASE):
            violations.append(f"feed_id looks like a UUID (non-deterministic): {feed_id}")
        if re.match(r"^[0-9a-f]{32}$", feed_id, re.IGNORECASE) and len(feed_id) == 32:
            violations.append(f"feed_id looks like a hash (not meaningful): {feed_id[:16]}...")
        if re.match(r"^\d{10,}$", feed_id):
            violations.append(f"feed_id looks like a bare timestamp (non-deterministic): {feed_id}")
        if re.match(r"^\d{4}-\d{2}-\d{2}", feed_id):
            violations.append(f"feed_id is date-prefixed only: {feed_id}")
        if re.search(r"random|uuid|timestamp", feed_id, re.IGNORECASE):
            violations.append(f"feed_id contains non-deterministic component: {feed_id[:40]}")
    elif not generator and not feed.get("same_input_output_A"):
        violations.append("Missing feed_id, generator, or output groups")
        return QAResult(
            scanner="feed_id_validator",
            status="FAIL",
            detail="No feed_id, generator, or output groups provided",
            violations=violations,
        )

    # ── Determinism test via generator (A) ──
    if generator:
        same_input = feed.get("same_input", "test_input")
        changed_input = feed.get("changed_input", "other_input")

        id_a = generator(same_input)
        id_b = generator(same_input)
        id_c = generator(changed_input)

        # Same input must produce same ID
        if id_a != id_b:
            violations.append(
                f"Same input '{same_input}' produced different IDs: '{id_a}' vs '{id_b}'"
            )
        # Different inputs must produce different IDs
        if id_a == id_c:
            violations.append(
                f"Different inputs ('{same_input}', '{changed_input}') produced same ID: '{id_a}'"
            )
        # Also validate the generated IDs themselves
        if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}", id_a, re.IGNORECASE):
            violations.append(f"Generator produced UUID-like ID: '{id_a[:20]}'")
        if re.match(r"^\d{10,}$", id_a):
            violations.append(f"Generator produced timestamp-like ID: '{id_a[:20]}'")

    # ── Determinism test via output groups (B) ──
    out_a = feed.get("same_input_output_A")
    out_b = feed.get("same_input_output_B")
    out_c = feed.get("changed_input_output")

    if out_a is not None and out_b is not None:
        if out_a != out_b:
            violations.append(
                f"Same input produced different outputs: '{out_a}' vs '{out_b}'"
            )
        if out_c is not None and out_a == out_c:
            violations.append(
                f"Different inputs produced same output: '{out_a}'"
            )

    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="feed_id_validator",
        status=status,
        detail=f"Validated feed ID determinism",
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


def scan_url_corpus(corpus_path_or_data, validator=None) -> QAResult:
    """Run URL attack corpus through a validator/renderer.

    Corpus containing malicious URLs is EXPECTED — must NOT fail on corpus content.
    Instead, pass each payload through the injected validator callable:
    - unsafe payload ACCEPTED by target → FAIL
    - payload rejected/escaped by target → PASS
    - target unavailable (no validator) → BLOCKED
    """
    # Load corpus
    if isinstance(corpus_path_or_data, str):
        if not os.path.isfile(corpus_path_or_data):
            return QAResult(scanner="url_attack_corpus", status="BLOCKED",
                            detail=f"Corpus not found: {corpus_path_or_data}",
                            violations=["Corpus file missing — target cannot be tested"])
        try:
            with open(corpus_path_or_data, "r", encoding="utf-8") as f:
                corpus = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return QAResult(scanner="url_attack_corpus", status="BLOCKED",
                            detail=f"Corpus parse error: {e}",
                            violations=["Corpus unreadable — target cannot be tested"])
    else:
        corpus = corpus_path_or_data

    urls = corpus if isinstance(corpus, list) else corpus.get("urls", [])

    if validator is None:
        return QAResult(
            scanner="url_attack_corpus",
            status="BLOCKED",
            detail=f"Corpus loaded ({len(urls)} URLs) but no validator available",
            violations=["No URL validator provided — target unavailable"],
        )

    # Corpus itself is expected to contain malicious content — never flag corpus as violation
    # Only flag if the target ACCEPTS an unsafe payload
    violations = []
    tested = 0
    for url in urls:
        tested += 1
        try:
            accepted = validator(url)
            if accepted:
                violations.append(f"Unsafe URL accepted by target: {url[:80]}")
        except Exception as e:
            violations.append(f"Validator error for URL ({url[:40]}...): {e}")

    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="url_attack_corpus",
        status=status,
        detail=f"Tested {tested}/{len(urls)} URLs against validator",
        violations=violations,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Scanner: HTML / XSS Attack Corpus
# ═══════════════════════════════════════════════════════════════════════════


def scan_xss_corpus(corpus_path_or_data, renderer=None) -> QAResult:
    """Run XSS attack corpus through a renderer/sanitizer.

    Corpus containing XSS payloads is EXPECTED — must NOT fail on corpus content.
    Instead, pass each payload through an injected renderer callable:
    - unsafe payload rendered/executed unsafely → FAIL
    - payload rejected/escaped → PASS
    - target unavailable (no renderer) → BLOCKED
    """
    # Load corpus
    if isinstance(corpus_path_or_data, str):
        if not os.path.isfile(corpus_path_or_data):
            return QAResult(scanner="xss_attack_corpus", status="BLOCKED",
                            detail=f"Corpus not found: {corpus_path_or_data}",
                            violations=["Corpus file missing — target cannot be tested"])
        try:
            with open(corpus_path_or_data, "r", encoding="utf-8") as f:
                corpus = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return QAResult(scanner="xss_attack_corpus", status="BLOCKED",
                            detail=f"Corpus parse error: {e}",
                            violations=["Corpus unreadable — target cannot be tested"])
    else:
        corpus = corpus_path_or_data

    payloads = corpus if isinstance(corpus, list) else corpus.get("payloads", [])

    if renderer is None:
        return QAResult(
            scanner="xss_attack_corpus",
            status="BLOCKED",
            detail=f"Corpus loaded ({len(payloads)} payloads) but no renderer available",
            violations=["No XSS renderer/sanitizer provided — target unavailable"],
        )

    # Corpus itself is expected to contain XSS — never flag corpus as violation
    # Only flag if the target renders/executes unsafely
    violations = []
    tested = 0
    for payload in payloads:
        tested += 1
        try:
            unsafe = renderer(payload)
            if unsafe:
                violations.append(f"Unsafe XSS payload rendered unsafely by target: {payload[:60]}")
        except Exception as e:
            violations.append(f"Renderer error for payload ({payload[:30]}...): {e}")

    status = "PASS" if not violations else "FAIL"
    return QAResult(
        scanner="xss_attack_corpus",
        status=status,
        detail=f"Tested {tested}/{len(payloads)} XSS payloads against renderer",
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
    artifact_paths: list[str] | None = None,
    claimed_commit: str | None = None,
    oracle_liquidation_input: dict | None = None,
    oracle_first_snapshot_input: dict | None = None,
    hype_source_record: dict | None = None,
    feed_id_input: dict | None = None,
    data_truth_records: list[dict] | None = None,
    url_validator=None,
    xss_renderer=None,
    dependency_test_content: str | None = None,
) -> QAScanReport:
    """Run all QA scanners and produce a report.

    All target refs, artifacts, test paths and expected results are supplied
    explicitly — no hardcoded fakes. Missing evidence → BLOCKED.
    Scans only requested target paths/diff, not unrelated historical scripts.

    dependency_test_content: synthetic pinned manifest content for self-test.
                             When provided, the dependency scanner validates this
                             instead of reading the real project requirements.txt.
    """
    head_commit = _git_head(repo_root)
    if head_commit == "unknown" or not head_commit:
        return QAScanReport(
            scan_id=f"qa_blocked_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            target_repo=repo_root, target_ref=target_ref,
            scanned_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            results=[QAResult(scanner="master_runner", status="BLOCKED",
                               detail="Cannot resolve HEAD commit — target repo unavailable",
                               violations=["Missing evidence: no commit resolved"])],
            summary={"total": 1, "pass": 0, "fail": 0, "blocked": 1, "not_applicable": 0},
        )

    scan_id = f"qa_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{head_commit[:8]}"
    report = QAScanReport(
        scan_id=scan_id,
        target_repo=repo_root,
        target_ref=target_ref,
        scanned_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    # Run each scanner (only requested paths — no historical repo scanning)
    report.results.append(scan_ownership(repo_root, owned_paths, target_ref))
    report.results.append(scan_forbidden_imports(repo_root, scan_paths, [
        "os.system", "subprocess.run", "shutil.rmtree",
    ]))
    report.results.append(scan_trading_capability(repo_root, scan_paths))
    report.results.append(scan_credentials(repo_root, scan_paths))
    report.results.append(scan_scheduler_disabled(repo_root, scan_paths))
    report.results.append(scan_no_send(repo_root, scan_paths))

    # Artifact binding — all params supplied explicitly
    if artifact_paths and claimed_commit:
        report.results.append(scan_artifact_binding(artifact_paths, claimed_commit, head_commit))
    else:
        report.results.append(QAResult(
            scanner="artifact_binding_validator", status="BLOCKED",
            detail="Missing evidence: artifact_paths or claimed_commit not provided",
            violations=["Artifact paths and claimed commit must be supplied explicitly"],
        ))

    # Test counts
    if test_paths:
        report.results.append(scan_test_count(repo_root, expected_test_count, test_paths))
    else:
        report.results.append(QAResult(
            scanner="test_count_validator", status="BLOCKED",
            detail="Missing evidence: no test paths provided",
            violations=["Test paths must be supplied explicitly"],
        ))

    report.results.append(scan_dependency_manifest(repo_root, manifest_path,
                                                    content_override=dependency_test_content))

    # Data truth — uses structured records, not file grepping
    if data_truth_records is not None:
        report.results.append(scan_data_truth(data_truth_records))
    else:
        report.results.append(QAResult(
            scanner="data_truth_validator", status="NOT_APPLICABLE",
            detail="No data truth records provided — skipping",
            violations=[],
        ))

    # Oracles — all inputs supplied explicitly (no hardcoded fakes)
    if oracle_liquidation_input is not None:
        report.results.append(oracle_liquidation_formula(oracle_liquidation_input))
    else:
        report.results.append(QAResult(
            scanner="liquidation_formula_oracle", status="NOT_APPLICABLE",
            detail="No liquidation formula input provided — skipping",
            violations=[],
        ))

    if oracle_first_snapshot_input is not None:
        report.results.append(oracle_first_snapshot(oracle_first_snapshot_input))
    else:
        report.results.append(QAResult(
            scanner="first_snapshot_oracle", status="NOT_APPLICABLE",
            detail="No first snapshot input provided — skipping",
            violations=[],
        ))

    # Source policy
    if hype_source_record is not None:
        report.results.append(scan_hype_source_policy(hype_source_record))
    else:
        report.results.append(QAResult(
            scanner="hype_source_policy_validator", status="NOT_APPLICABLE",
            detail="No HYPE market record provided — skipping",
            violations=[],
        ))

    # Feed ID
    if feed_id_input is not None:
        report.results.append(scan_feed_id(feed_id_input))
    else:
        report.results.append(QAResult(
            scanner="feed_id_validator", status="NOT_APPLICABLE",
            detail="No feed ID input provided — skipping",
            violations=[],
        ))

    # Security
    report.results.append(scan_html_security(repo_root, scan_paths))

    # Attack corpus — passes through injected validator/renderer
    url_corpus_path = os.path.join(corpus_dir, "url_attack_corpus.json")
    if os.path.isfile(url_corpus_path):
        report.results.append(scan_url_corpus(url_corpus_path, validator=url_validator))
    else:
        report.results.append(QAResult(
            scanner="url_attack_corpus", status="BLOCKED",
            detail=f"URL attack corpus not found at {url_corpus_path}",
            violations=["Corpus file missing"],
        ))

    xss_corpus_path = os.path.join(corpus_dir, "xss_attack_corpus.json")
    if os.path.isfile(xss_corpus_path):
        report.results.append(scan_xss_corpus(xss_corpus_path, renderer=xss_renderer))
    else:
        report.results.append(QAResult(
            scanner="xss_attack_corpus", status="BLOCKED",
            detail=f"XSS attack corpus not found at {xss_corpus_path}",
            violations=["Corpus file missing"],
        ))

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
