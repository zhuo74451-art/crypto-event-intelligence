#!/usr/bin/env python3
"""
Repository Test Matrix Runner
==============================
Runs pytest on multiple test shards with per-shard timeout,
captures pass/fail/skip/xfail/error counts and failed node IDs,
and outputs structured JSON and Markdown reports.

Usage:
    python scripts/run_repository_test_matrix.py
        --repo-root /path/to/repo
        --output-json results/report.json
        --output-md results/report.md
        --per-shard-timeout-seconds 600
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ShardResult:
    """Aggregated test results for a single shard."""
    shard_name: str
    test_path: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    xfailed: int = 0
    xpassed: int = 0
    errors: int = 0
    total: int = 0
    duration_seconds: float = 0.0
    timed_out: bool = False
    return_code: Optional[int] = None
    failed_node_ids: List[str] = field(default_factory=list)
    warning_lines: List[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.timed_out:
            return "TIMEOUT"
        if self.return_code is None:
            return "UNKNOWN"
        if self.return_code == 0:
            return "PASS"
        if self.return_code == 1:
            return "FAIL"
        if self.return_code == 5:
            return "NO_TESTS_COLLECTED"
        return f"EXIT_{self.return_code}"


@dataclass
class MatrixReport:
    """Top-level report encompassing all shards."""
    generated_at: str = ""
    repo_root: str = ""
    per_shard_timeout_seconds: int = 0
    total_duration_seconds: float = 0.0
    grand_passed: int = 0
    grand_failed: int = 0
    grand_skipped: int = 0
    grand_xfailed: int = 0
    grand_xpassed: int = 0
    grand_errors: int = 0
    grand_total: int = 0
    shards: List[ShardResult] = field(default_factory=list)

    @property
    def overall_status(self) -> str:
        if not self.shards:
            return "NO_SHARDS"
        if any(s.timed_out for s in self.shards):
            return "TIMEOUT"
        if all(s.return_code == 0 for s in self.shards):
            return "PASS"
        return "FAIL"


# ---------------------------------------------------------------------------
# Pytest output parser
# ---------------------------------------------------------------------------

# Patterns to capture the summary line at the end of a pytest run.
# Examples:
#   "== 3 passed, 2 skipped, 1 xfailed in 0.42s =="
#   "== 1 failed, 2 passed in 5.21s =="
#   "== 2 passed, 1 error in 3.10s =="
#   "== 1 passed, 1 xpassed in 0.80s =="
#   "== no tests collected in 0.00s =="

_SHORT_SUMMARY_RE = re.compile(
    r"^=+\s+"
    r"(?P<parts>.+?)"
    r"\s+in\s+(?P<duration>[\d.]+)s\s+=+$"
)

_FAILED_NODE_RE = re.compile(
    r"^(FAILED|ERROR)\s+(.+)$"
)

_WARNING_RE = re.compile(
    r"^=++\s+(?:[Ww]arnings summary|warnings)\s+---+$"
)


def _parse_short_summary(line: str) -> Optional[Dict[str, int]]:
    """Parse a pytest short summary line into a dict of counts."""
    m = _SHORT_SUMMARY_RE.match(line.strip())
    if not m:
        return None
    parts_str = m.group("parts").strip()
    # parts_str looks like: "3 passed, 2 skipped, 1 xfailed"
    counts: Dict[str, int] = {}
    for chunk in parts_str.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        # "no tests collected" is special
        if "no tests collected" in chunk:
            return {"no_tests_collected": 1}
        # "3 passed", "1 error", "2 skipped", "1 xfailed", "1 xpassed", "1 failed"
        tokens = chunk.split()
        if len(tokens) < 2:
            continue
        try:
            value = int(tokens[0])
        except ValueError:
            continue
        key = tokens[1].lower().rstrip(".")
        counts[key] = counts.get(key, 0) + value
    return counts


def _parse_failed_node(line: str) -> Optional[str]:
    """If line starts with FAILED or ERROR, extract the node ID."""
    m = _FAILED_NODE_RE.match(line.strip())
    if m:
        return m.group(2).strip()
    return None


def parse_pytest_output(
    stdout: str,
    stderr: str,
) -> tuple[Dict[str, int], List[str], List[str]]:
    """
    Parse combined stdout/stderr from a pytest invocation.

    Returns:
        (counts_dict, failed_node_ids, warning_lines)
    """
    counts: Dict[str, int] = {}
    failed_ids: List[str] = []
    warnings: List[str] = []

    lines = (stdout + "\n" + stderr).splitlines()

    in_warning_block = False
    for line in lines:
        stripped = line.strip()

        # Detect warning block start
        if _WARNING_RE.match(stripped):
            in_warning_block = True
            continue
        # End of warning block is the next "=------" line or empty line
        if in_warning_block:
            if stripped.startswith("==") or stripped == "":
                in_warning_block = False
            else:
                warnings.append(stripped)
                continue

        # Parse summary line (look for the short summary at the end)
        parsed = _parse_short_summary(stripped)
        if parsed is not None:
            counts = parsed
            continue

        # Parse failed / error node IDs
        node_id = _parse_failed_node(stripped)
        if node_id is not None:
            failed_ids.append(node_id)

    return counts, failed_ids, warnings


# ---------------------------------------------------------------------------
# Shard runner
# ---------------------------------------------------------------------------

def run_shard(
    shard_name: str,
    test_path: str,
    repo_root: Path,
    timeout_seconds: int,
    pytest_args: List[str] = None,
) -> ShardResult:
    """Run a single pytest shard and return structured results."""
    result = ShardResult(shard_name=shard_name, test_path=test_path)

    cwd = repo_root.resolve()
    cmd = [
        sys.executable, "-m", "pytest",
        str(test_path),
        "-v",
        "--tb=short",
        "--no-header",
    ]
    if pytest_args:
        cmd.extend(pytest_args)

    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        result.return_code = proc.returncode
    except subprocess.TimeoutExpired:
        result.timed_out = True
        result.return_code = -1
        duration = time.monotonic() - start
        result.duration_seconds = round(duration, 2)
        return result
    except Exception as exc:
        result.return_code = -2
        result.warning_lines.append(f"Subprocess exception: {exc}")
        duration = time.monotonic() - start
        result.duration_seconds = round(duration, 2)
        return result

    duration = time.monotonic() - start
    result.duration_seconds = round(duration, 2)

    # Parse output
    counts, failed_ids, warnings = parse_pytest_output(proc.stdout, proc.stderr)
    result.failed_node_ids = failed_ids
    result.warning_lines = warnings

    # Map parsed counts to named fields
    if "no_tests_collected" in counts:
        result.total = 0
    else:
        result.passed = counts.get("passed", 0)
        result.failed = counts.get("failed", 0)
        result.skipped = counts.get("skipped", 0)
        result.xfailed = counts.get("xfailed", 0)
        result.xpassed = counts.get("xpassed", 0)
        result.errors = counts.get("error", 0)
        result.total = (
            result.passed
            + result.failed
            + result.skipped
            + result.xfailed
            + result.xpassed
            + result.errors
        )

    return result


# ---------------------------------------------------------------------------
# Shard definitions
# ---------------------------------------------------------------------------

def build_shard_definitions(repo_root: Path) -> List[tuple[str, str]]:
    """
    Return list of (shard_name, relative_test_path) pairs.

    The 'empty' shard name signals that we pass the directory path directly;
    we use descriptive names so the report is readable.
    """
    # Root-level test files (those directly under tests/*.py)
    root_tests = sorted(
        p.name
        for p in (repo_root / "tests").iterdir()
        if p.is_file() and p.suffix == ".py"
    )

    shards: List[tuple[str, str]] = [
        ("intelligence", "tests/intelligence/"),
        ("mvpplus", "tests/mvpplus/"),
        ("post_mvp_event_intelligence", "tests/post_mvp/event_intelligence/"),
        ("post_mvp_market_resilience", "tests/post_mvp/market_resilience/"),
        ("post_mvp_operations", "tests/post_mvp/operations/"),
        ("post_mvp_operator", "tests/post_mvp/operator/"),
        ("post_mvp_telegram", "tests/post_mvp/telegram/"),
        ("post_mvp_whale_intelligence", "tests/post_mvp/whale_intelligence/"),
        ("strategies", "tests/strategies/"),
    ]

    # Add root-level test files as a single shard
    if root_tests:
        # Pass the directory + all root test files explicitly
        root_path = "tests/"
        shards.append(("tests_root", root_path))

    return shards


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_json_report(report: MatrixReport) -> str:
    """Serialize the report to a pretty-printed JSON string."""
    return json.dumps(asdict(report), indent=2, ensure_ascii=False, default=str)


def format_markdown_report(report: MatrixReport) -> str:
    """Render the report as a Markdown table + summary."""
    lines: List[str] = []
    lines.append("# Test Matrix Report")
    lines.append("")
    lines.append(f"- **Generated at**: {report.generated_at}")
    lines.append(f"- **Repo root**: `{report.repo_root}`")
    lines.append(f"- **Per-shard timeout**: {report.per_shard_timeout_seconds}s")
    lines.append(f"- **Total wall time**: {report.total_duration_seconds:.2f}s")
    lines.append(f"- **Overall status**: **{report.overall_status}**")
    lines.append("")

    # Grand totals
    lines.append("## Grand Totals")
    lines.append("")
    lines.append(
        f"| Passed | Failed | Skipped | XFailed | XPassed | Errors | Total |"
    )
    lines.append(
        f"|-------:|-------:|--------:|--------:|--------:|-------:|------:|"
    )
    lines.append(
        f"| {report.grand_passed} | {report.grand_failed} | {report.grand_skipped} "
        f"| {report.grand_xfailed} | {report.grand_xpassed} | {report.grand_errors} "
        f"| {report.grand_total} |"
    )
    lines.append("")

    # Shard table
    lines.append("## Shard Breakdown")
    lines.append("")
    header = (
        "| Shard | Status | Passed | Failed | Skipped | XFailed | XPassed | Errors "
        "| Total | Duration (s) |"
    )
    sep = (
        "|------|-------:|-------:|-------:|--------:|--------:|-------:|------:"
        "|-------------:|"
    )
    lines.append(header)
    lines.append(sep)

    for shard in report.shards:
        status_tag = _status_badge(shard.status)
        lines.append(
            f"| {shard.shard_name} | {status_tag} "
            f"| {shard.passed} | {shard.failed} | {shard.skipped} "
            f"| {shard.xfailed} | {shard.xpassed} | {shard.errors} "
            f"| {shard.total} | {shard.duration_seconds:.2f} |"
        )
    lines.append("")

    # Shard details – timed out shards
    timed_out_shards = [s for s in report.shards if s.timed_out]
    if timed_out_shards:
        lines.append("## ⏱ Timed Out Shards")
        lines.append("")
        for shard in timed_out_shards:
            lines.append(f"- **{shard.shard_name}** (`{shard.test_path}`)")
        lines.append("")

    # Shard details – failed node IDs
    shards_with_failures = [s for s in report.shards if s.failed_node_ids]
    if shards_with_failures:
        lines.append("## ❌ Failed / Error Node IDs")
        lines.append("")
        for shard in shards_with_failures:
            lines.append(f"### {shard.shard_name}")
            lines.append("")
            for nid in shard.failed_node_ids:
                lines.append(f"- `{nid}`")
            lines.append("")

    # Shard details – warnings
    shards_with_warnings = [s for s in report.shards if s.warning_lines]
    if shards_with_warnings:
        lines.append("## ⚠️ Warnings")
        lines.append("")
        for shard in shards_with_warnings:
            lines.append(f"### {shard.shard_name}")
            lines.append("")
            for w in shard.warning_lines[:20]:  # cap per shard
                lines.append(f"- {w}")
            if len(shard.warning_lines) > 20:
                lines.append(f"- *… and {len(shard.warning_lines) - 20} more*")
            lines.append("")

    return "\n".join(lines)


def _status_badge(status: str) -> str:
    badges = {
        "PASS": "✅ PASS",
        "FAIL": "❌ FAIL",
        "TIMEOUT": "⏱ TIMEOUT",
        "NO_TESTS_COLLECTED": "⚠️ EMPTY",
    }
    return badges.get(status, f"❓ {status}")


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pytest test matrix over repository shards."
    )
    parser.add_argument(
        "--repo-root",
        required=True,
        help="Absolute or relative path to the repository root.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Path to write the JSON report (relative to repo-root, or absolute).",
    )
    parser.add_argument(
        "--output-md",
        default="",
        help="Path to write the Markdown report (relative to repo-root, or absolute).",
    )
    parser.add_argument(
        "--per-shard-timeout-seconds",
        type=int,
        default=600,
        help="Timeout per shard in seconds (default 600).",
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Additional arguments forwarded to pytest (use -- to separate).",
    )
    return parser.parse_args(argv)


def _resolve_output_path(path_str: str, repo_root: Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return repo_root / p


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.is_dir():
        print(f"ERROR: --repo-root '{repo_root}' is not a valid directory.", file=sys.stderr)
        return 1

    # Resolve output paths
    output_json = _resolve_output_path(args.output_json, repo_root) if args.output_json else None
    output_md = _resolve_output_path(args.output_md, repo_root) if args.output_md else None

    # Ensure parent directories exist
    for p in (output_json, output_md):
        if p is not None:
            p.parent.mkdir(parents=True, exist_ok=True)

    timeout = args.per_shard_timeout_seconds
    pytest_extra = args.pytest_args or []

    # Build shard list
    shard_defs = build_shard_definitions(repo_root)
    print(f"Test matrix: {len(shard_defs)} shard(s)")
    print(f"Timeout per shard: {timeout}s")
    print()

    report = MatrixReport(
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        repo_root=str(repo_root),
        per_shard_timeout_seconds=timeout,
    )

    overall_start = time.monotonic()

    for idx, (shard_name, test_path) in enumerate(shard_defs, start=1):
        print(f"[{idx}/{len(shard_defs)}] Running shard '{shard_name}' ({test_path}) ...", end="")
        sys.stdout.flush()

        shard_result = run_shard(
            shard_name=shard_name,
            test_path=test_path,
            repo_root=repo_root,
            timeout_seconds=timeout,
            pytest_args=pytest_extra,
        )
        report.shards.append(shard_result)

        if shard_result.timed_out:
            print(f" TIMEOUT ({shard_result.duration_seconds:.2f}s)")
        else:
            print(f" done ({shard_result.duration_seconds:.2f}s, return_code={shard_result.return_code})")

        # Accumulate grand totals
        report.grand_passed += shard_result.passed
        report.grand_failed += shard_result.failed
        report.grand_skipped += shard_result.skipped
        report.grand_xfailed += shard_result.xfailed
        report.grand_xpassed += shard_result.xpassed
        report.grand_errors += shard_result.errors
        report.grand_total += shard_result.total

    report.total_duration_seconds = round(time.monotonic() - overall_start, 2)

    print()
    print(f"Total wall time: {report.total_duration_seconds:.2f}s")
    print(f"Overall status:  {report.overall_status}")
    print()

    # Write JSON report
    if output_json:
        json_content = format_json_report(report)
        output_json.write_text(json_content, encoding="utf-8")
        print(f"JSON report written to {output_json}")

    # Write Markdown report
    if output_md:
        md_content = format_markdown_report(report)
        output_md.write_text(md_content, encoding="utf-8")
        print(f"Markdown report written to {output_md}")

    return 0 if report.overall_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
