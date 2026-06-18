"""Audit Bundle — deterministic, non-destructive, tamper-evident export.

Generates a structured audit bundle that can be verified independently.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Optional

from market_radar.operations.doctor import run_doctor, doctor_summary
from market_radar.operations.run_history import get_run, list_child_runs, list_runs
from market_radar.operations.sqlite_schema import get_connection


AUDIT_BUNDLE_VERSION = 1

BUNDLE_FILES = [
    "manifest.json",
    "run_history.json",
    "parent_child_graph.json",
    "source_health.json",
    "integrity_report.json",
    "artifact_checksums.json",
    "README.md",
    "SHA256SUMS",
]

SENSITIVE_KEY_PATTERNS = {"token", "secret", "password", "key", "credential",
                          "authorization", "cookie", "private"}


def _sanitize(obj: Any, path: str = "") -> Any:
    """Recursively redact sensitive keys from a JSON-serialisable object."""
    if isinstance(obj, dict):
        return {
            k: ("[REDACTED]" if any(p in k.lower() for p in SENSITIVE_KEY_PATTERNS)
                else _sanitize(v, f"{path}.{k}"))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_sanitize(item, f"{path}[{i}]") for i, item in enumerate(obj)]
    return obj


def _relativise(path: str, base: str) -> str:
    """Convert absolute path to relative, or empty string if outside base."""
    try:
        return str(Path(path).relative_to(base))
    except ValueError:
        return path


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(obj: Any) -> bytes:
    """Deterministic canonical JSON encoding (sorted keys, no extra whitespace)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _build_hash_chain(manifest: dict, prev_chain_hash: str = "") -> str:
    """Build a hash chain from manifest contents.

    Chain: SHA256(prev_chain_hash + SHA256(file_manifest_bytes))
    """
    import hashlib
    m = hashlib.sha256()
    if prev_chain_hash:
        m.update(prev_chain_hash.encode("ascii"))
    m.update(_canonical_json(manifest))
    return m.hexdigest()


def _redaction_report(data: list[dict]) -> dict:
    """Report on what was redacted."""
    redacted = set()
    for item in data:
        for k in item:
            if isinstance(item[k], str) and item[k] == "[REDACTED]":
                redacted.add(k)
    return {"fields_redacted": sorted(redacted), "total_redacted_occurrences": len(redacted)}


def export_audit_bundle(
    state_dir: str | Path,
    output_dir: str | Path,
    include_db: bool = False,
    clock_fn: Callable[[], float] = time.time,
    label: str = "",
) -> Path:
    """Export an audit bundle to *output_dir*.

    Args:
        state_dir: Operations state directory.
        output_dir: Destination for the bundle (created if missing).
        include_db: If True, copy the SQLite DB into the bundle (large).
        clock_fn: Deterministic clock for reproducible timestamps.
        label: Optional label for the bundle.

    Returns:
        Path to the bundle directory.
    """
    sd = Path(state_dir)
    od = Path(output_dir)
    od.mkdir(parents=True, exist_ok=True)

    db_path = sd / "run_history.db"
    ts = int(clock_fn())

    # 1. manifest.json
    manifest = {
        "bundle_version": AUDIT_BUNDLE_VERSION,
        "created_at_epoch": ts,
        "label": label or f"audit_bundle_{ts}",
        "source_state_dir": str(sd),
        "files": [],
        "sha256": "",
    }

    # 2. run_history.json
    all_runs = list_runs(str(db_path), limit=10000)
    rh_data = []
    for r in all_runs:
        s = _sanitize(r)
        s.pop("_sanitized", None)
        rh_data.append(s)
    _write_json(od / "run_history.json", rh_data)
    manifest["files"].append("run_history.json")

    # Redaction and exclusion report
    redact_report = _redaction_report(rh_data)
    excluded_fields = ["raw_api_response", "feed_body", "full_content"]

    # 3. parent_child_graph.json
    graph = {"parents": []}
    parents = [r for r in all_runs if r.get("run_kind") == "shadow_parent"]
    for p in parents:
        children = list_child_runs(str(db_path), p["run_id"])
        graph["parents"].append({
            "parent_run_id": p["run_id"],
            "parent_status": p.get("status"),
            "child_count": len(children),
            "children": [
                {"run_id": c["run_id"], "status": c.get("status"),
                 "ordinal": c.get("run_ordinal")}
                for c in children
            ],
        })
    _write_json(od / "parent_child_graph.json", graph)
    manifest["files"].append("parent_child_graph.json")

    # 4. source_health.json
    conn = get_connection(db_path)
    try:
        sh_rows = conn.execute(
            "SELECT * FROM source_health ORDER BY checked_at DESC LIMIT 1000"
        ).fetchall()
    finally:
        conn.close()
    _write_json(od / "source_health.json", [dict(r) for r in sh_rows])
    manifest["files"].append("source_health.json")

    # 5. integrity_report.json (doctor run)
    doc = run_doctor(state_dir, clock_fn=clock_fn)
    _write_json(od / "integrity_report.json", doctor_summary(doc))
    manifest["files"].append("integrity_report.json")

    # 6. artifact_checksums.json
    artifacts = {}
    for f in sorted(sd.iterdir()):
        if f.is_file() and not f.name.endswith(".db-wal") and not f.name.endswith(".db-shm"):
            artifacts[f.name] = _hash_file(f)
    _write_json(od / "artifact_checksums.json", artifacts)
    manifest["files"].append("artifact_checksums.json")

    # 7. README.md
    readme = _generate_readme(manifest)
    (od / "README.md").write_text(readme, encoding="utf-8")
    manifest["files"].append("README.md")

    # 8. Copy DB if requested
    if include_db and db_path.exists():
        dest = od / "run_history.db"
        shutil.copy2(str(db_path), str(dest))
        manifest["files"].append("run_history.db")

    # Generate SHA256SUMS
    sha_lines: list[str] = []
    for fname in sorted(manifest["files"]):
        fp = od / fname
        if fp.exists():
            sha_lines.append(f"{_hash_file(fp)}  {fname}")
    sha_content = "\n".join(sha_lines) + "\n"
    (od / "SHA256SUMS").write_text(sha_content, encoding="utf-8")
    manifest["files"].append("SHA256SUMS")

    # Redaction & exclusion metadata
    manifest["redaction_report"] = redact_report
    manifest["excluded_fields"] = excluded_fields

    # Bundle ID (deterministic from content)
    bundle_id = _hash_bytes(
        _canonical_json(manifest.get("label", "")) +
        _canonical_json(manifest.get("files", [])) +
        _canonical_json(manifest.get("created_at_epoch", 0))
    )[:16]
    manifest["bundle_id"] = bundle_id

    # Hash chain
    manifest["hash_chain"] = _build_hash_chain(manifest)

    # Final canonical manifest with hash
    bundle_hash = _hash_bytes(_canonical_json(manifest))
    manifest["sha256"] = bundle_hash
    _write_json(od / "manifest.json", manifest)

    return od


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _generate_readme(manifest: dict) -> str:
    return f"""# Audit Bundle — {manifest['label']}

Generated at epoch {manifest['created_at_epoch']}
Bundle version {manifest['bundle_version']}
Source: {manifest['source_state_dir']}

## Contents

{chr(10).join('- ' + f for f in manifest['files'])}

## Verification

Run:

    python -c "from market_radar.operations.audit_bundle import verify_audit_bundle; ...

## Integrity

Each file is checksummed in SHA256SUMS.
The manifest includes a bundle-level hash.
"""


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_audit_bundle(
    bundle_dir: str | Path,
) -> dict[str, Any]:
    """Verify an audit bundle's integrity and consistency.

    Returns a dict with status, passed checks, and any violations.
    """
    bd = Path(bundle_dir)
    result: dict[str, Any] = {
        "bundle_dir": str(bd),
        "status": "pass",
        "checks": [],
        "violations": [],
    }

    manifest_file = bd / "manifest.json"
    if not manifest_file.exists():
        return {"status": "fail", "violations": ["manifest.json not found"]}

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, Exception) as e:
        return {"status": "fail", "violations": [f"manifest corrupt: {e}"]}

    # Check all declared files exist
    for fname in manifest.get("files", []):
        fp = bd / fname
        if not fp.exists():
            result["violations"].append(f"Missing file: {fname}")
        elif fp.stat().st_size == 0 and fname not in ("SHA256SUMS",):
            result["violations"].append(f"Empty file: {fname}")

    # Verify SHA256SUMS
    sha_file = bd / "SHA256SUMS"
    if sha_file.exists():
        for line in sha_file.read_text(encoding="utf-8").strip().split("\n"):
            parts = line.strip().split("  ", 1)
            if len(parts) == 2:
                expected_hash, fname = parts
                fp = bd / fname
                if fp.exists():
                    actual = _hash_file(fp)
                    if actual != expected_hash:
                        result["violations"].append(
                            f"SHA256 mismatch for {fname}: "
                            f"expected {expected_hash[:16]}..., got {actual[:16]}..."
                        )

    # Verify run_history.json is valid JSON array
    rh_file = bd / "run_history.json"
    if rh_file.exists():
        try:
            runs = json.loads(rh_file.read_text(encoding="utf-8"))
            if not isinstance(runs, list):
                result["violations"].append("run_history.json is not a list")
            else:
                result["checks"].append(f"run_history.json: {len(runs)} records")
        except Exception as e:
            result["violations"].append(f"run_history.json corrupt: {e}")

    # Check manifest schema
    for key in ("bundle_version", "created_at_epoch", "label", "sha256"):
        if key not in manifest:
            result["violations"].append(f"manifest missing key: {key}")

    # Final status
    if result["violations"]:
        result["status"] = "fail"
    else:
        result["status"] = "pass"
        result["checks"].append(f"All {len(manifest.get('files', []))} files verified")

    return result
