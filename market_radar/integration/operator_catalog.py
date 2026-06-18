"""Operator Run Catalog — local read-only scan of multiple run manifests.

No server, no daemon. Outputs JSON, Markdown, or static HTML.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def scan_run_dirs(
    root_dirs: list[str],
    max_manifests: int = 100,
    status_filter: Optional[str] = None,
    profile_filter: Optional[str] = None,
    source_filter: Optional[str] = None,
) -> list[dict]:
    """Scan directories for operator_manifest files and return sorted catalog.

    Args:
        root_dirs: List of root directories to scan recursively.
        max_manifests: Maximum number of manifests to return.
        status_filter: Optional filter by run status.
        profile_filter: Optional filter by profile name.
        source_filter: Optional filter by source name (checks source_summary keys).

    Returns:
        List of manifest dicts sorted by started_at descending.
    """
    manifests: list[dict] = []

    for root_dir in root_dirs:
        base = Path(root_dir)
        if not base.is_dir():
            continue
        for root, dirs, files in os.walk(str(base)):
            for fname in files:
                if fname.startswith("manifest_") and fname.endswith(".json"):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception:
                        continue
                    if not isinstance(data, dict):
                        continue
                    # Apply filters
                    if status_filter and data.get("status") != status_filter:
                        continue
                    if profile_filter and data.get("profile_name") != profile_filter:
                        continue
                    if source_filter:
                        srcs = data.get("source_summary", {})
                        if source_filter not in srcs:
                            continue
                    # Add file metadata
                    data["_file_path"] = fpath
                    manifests.append(data)
                    if len(manifests) >= max_manifests:
                        break
            if len(manifests) >= max_manifests:
                break

    # Sort by started_at descending (most recent first)
    manifests.sort(key=lambda m: m.get("started_at", ""), reverse=True)
    return manifests[:max_manifests]


def catalog_to_json(manifests: list[dict]) -> str:
    """Format catalog as JSON."""
    return json.dumps(manifests, indent=2, default=str)


def catalog_to_markdown(manifests: list[dict]) -> str:
    """Format catalog as Markdown."""
    lines = ["# Operator Run Catalog", "", f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}", ""]
    if not manifests:
        lines.append("_No runs found._")
        return "\n".join(lines)

    lines.append(f"**{len(manifests)} run(s)**")
    lines.append("")
    lines.append("| Run ID | Status | Profile | Started | Sources | Cursor | Errors |")
    lines.append("|--------|--------|---------|---------|---------|--------|--------|")
    for m in manifests:
        rid = m.get("run_id", "?")[:16]
        status = m.get("status", "?")
        profile = m.get("profile_name", "?")
        started = (m.get("started_at") or "?")[:19]
        src_count = len(m.get("source_summary", {}))
        cursor = (m.get("cursor_after") or "?")[:10]
        errs = m.get("error_count", 0)
        lines.append(f"| {rid} | {status} | {profile} | {started} | {src_count} | {cursor} | {errs} |")
    return "\n".join(lines)


def catalog_to_static_html(manifests: list[dict]) -> str:
    """Format catalog as minimal static HTML."""
    rows = ""
    for m in manifests:
        rid = m.get("run_id", "?")[:16]
        status = m.get("status", "?")
        profile = m.get("profile_name", "?")
        started = (m.get("started_at") or "?")[:19]
        src_count = len(m.get("source_summary", {}))
        cursor = (m.get("cursor_after") or "?")[:10]
        errs = m.get("error_count", 0)
        rows += f"<tr><td>{rid}</td><td>{status}</td><td>{profile}</td><td>{started}</td><td>{src_count}</td><td>{cursor}</td><td>{errs}</td></tr>\n"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Operator Run Catalog</title>
<style>body{{font-family:sans-serif;margin:20px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:8px;text-align:left}}th{{background:#f5f5f5}}</style>
</head>
<body>
<h1>Operator Run Catalog</h1>
<p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} | {len(manifests)} run(s)</p>
<table>
<tr><th>Run ID</th><th>Status</th><th>Profile</th><th>Started</th><th>Sources</th><th>Cursor</th><th>Errors</th></tr>
{rows}</table>
</body>
</html>"""
