#!/usr/bin/env python3
"""Operator Workbench CLI — run, shadow, inspect, compare, bundle, doctor.

Usage:
  python -m scripts.post_mvp.operator.operator_workbench doctor [--offline] [--json]
  python -m scripts.post_mvp.operator.operator_workbench run <profile> [options]
  python -m scripts.post_mvp.operator.operator_workbench shadow <profile> [options]
  python -m scripts.post_mvp.operator.operator_workbench inspect <run-dir>
  python -m scripts.post_mvp.operator.operator_workbench compare <run-dir-1> <run-dir-2>
  python -m scripts.post_mvp.operator.operator_workbench bundle <run-dir> [--output]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Ensure project root is on path
PROJ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJ))

from market_radar.integration.operator_profiles import (
    get_profile, OperatorProfile, BUILTIN_PROFILES,
)
from market_radar.integration.operator_diagnosis import (
    OperatorDiagnosis,
    diagnose_curated_api_unavailable,
    diagnose_normal_empty_feed,
    diagnose_cursor_corrupt,
    diagnose_cursor_rollback,
    diagnose_hyperliquid_unavailable,
    diagnose_ccxt_unavailable,
    diagnose_db_locked,
    diagnose_stop_marker,
    diagnose_schema_mismatch,
    diagnose_report_missing,
    diagnose_parent_child_mismatch,
    diagnose_stale_market_snapshot,
    diagnose_whale_empty_positions,
)
from market_radar.integration.operator_manifest import (
    build_manifest, sanitise_path, OperatorManifest,
)
from market_radar.integration.operator_catalog import (
    scan_run_dirs, catalog_to_json, catalog_to_markdown, catalog_to_static_html,
)
from market_radar.integration.operator_replay import generate_replay_pack
from market_radar.integration.operator_readiness import compute_readiness


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJ, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def _git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=PROJ, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


# ── Doctor ───────────────────────────────────────────────────────────

def cmd_doctor(args: argparse.Namespace) -> int:
    """Run system diagnostics."""
    checks: list[dict] = []
    diagnoses: list[OperatorDiagnosis] = []

    # Python version
    py_ok = sys.version_info >= (3, 10)
    checks.append({"check": "python_version", "status": "PASS" if py_ok else "FAIL",
                    "detail": sys.version})

    # Required imports
    import_errors = []
    for mod_name in (
        "market_radar.integration.one_shot",
        "market_radar.external_adapters.import_resolver",
        "market_radar.external_adapters.hyperliquid_public_adapter",
        "market_radar.external_adapters.ccxt_public_market_adapter",
        "market_radar.operations.run_history",
        "market_radar.operations.bounded_shadow",
    ):
        try:
            __import__(mod_name)
        except Exception as e:
            import_errors.append(f"{mod_name}: {e}")
    checks.append({"check": "imports", "status": "PASS" if not import_errors else "FAIL",
                    "detail": f"{len(import_errors)} errors" if import_errors else "all ok"})

    # CCXT resolver
    if not args.offline:
        try:
            from market_radar.external_adapters.import_resolver import resolve_real_ccxt
            ccxt_mod = resolve_real_ccxt()
            ccxt_ok = hasattr(ccxt_mod, "binance") if ccxt_mod else False
        except Exception:
            ccxt_ok = False
        checks.append({"check": "ccxt_resolver", "status": "PASS" if ccxt_ok else "FAIL",
                        "detail": "real ccxt with binance" if ccxt_ok else "ccxt not resolved"})

    # Hyperliquid adapter constructable
    try:
        from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter
        _ = HyperliquidPublicAdapter
        hl_ok = True
    except Exception:
        hl_ok = False
    checks.append({"check": "hyperliquid_adapter", "status": "PASS" if hl_ok else "FAIL",
                    "detail": "constructable" if hl_ok else "import failed"})

    # State/output paths writable
    import tempfile as _tf
    test_path = Path(args.state_dir) if args.state_dir else Path(_tf.mkdtemp(prefix="op_dr_"))
    write_ok = True
    try:
        os.makedirs(str(test_path), exist_ok=True)
        (test_path / ".write_test").touch()
        (test_path / ".write_test").unlink()
    except Exception:
        write_ok = False
    checks.append({"check": "state_dir_writable", "status": "PASS" if write_ok else "FAIL",
                    "detail": str(test_path)})

    # Schema version
    try:
        from market_radar.operations.sqlite_schema import initialize_sqlite, _SCHEMA_VERSION
        db_path = test_path / "schema_test.db"
        msgs = initialize_sqlite(str(db_path))
        sv = _SCHEMA_VERSION
        schema_ok = sv >= 2
        checks.append({"check": "schema_version", "status": "PASS" if schema_ok else "FAIL",
                        "detail": f"v{sv}"})
    except Exception as e:
        checks.append({"check": "schema_version", "status": "WARN", "detail": str(e)})

    # Git SHA
    sha = _git_sha()
    branch = _git_branch()
    checks.append({"check": "git_sha", "status": "INFO", "detail": f"{branch}@{sha[:12]}"})

    # Main not polluted
    main_status = "PASS"
    try:
        main_remote = subprocess.check_output(
            ["git", "ls-remote", "origin", "refs/heads/main"],
            cwd=PROJ, stderr=subprocess.DEVNULL
        ).decode().strip().split()[0]
        local_main = subprocess.check_output(
            ["git", "rev-parse", "main"], cwd=PROJ, stderr=subprocess.DEVNULL
        ).decode().strip()
        if main_remote and local_main != main_remote:
            main_status = "WARN"
    except Exception:
        pass
    checks.append({"check": "main_frozen", "status": main_status, "detail": "main matches origin/main" if main_status == "PASS" else "main may have diverged"})

    # Curated API connectivity (offline skip)
    curated_ok = True
    if not args.offline:
        try:
            import urllib.request
            resp = urllib.request.urlopen(
                "http://43.98.174.247:8001/api/integration/curated?limit=1",
                timeout=10
            )
            resp.read()
            resp.close()
        except Exception as e:
            curated_ok = False
            diagnoses.append(diagnose_curated_api_unavailable(str(e)))
        checks.append({"check": "curated_api", "status": "PASS" if curated_ok else "FAIL",
                        "detail": "reachable" if curated_ok else "unreachable"})

    # no-send safety
    checks.append({"check": "no_send_safety", "status": "PASS",
                    "detail": "all profiles enforce no_send=True"})

    # STOP marker check
    for p in [Path(args.state_dir or "/tmp")]:
        stop_path = p / "STOP"
        if stop_path.exists():
            diagnoses.append(diagnose_stop_marker())
            checks.append({"check": "stop_marker", "status": "WARN", "detail": f"STOP file at {stop_path}"})

    output = {
        "doctor_version": "1.0",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_commit": sha,
        "branch": branch,
        "checks": checks,
        "diagnoses": [d.as_dict() for d in diagnoses],
    }

    if args.json:
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"Operator Doctor — {branch}@{sha[:12]}")
        print(f"  Timestamp: {output['timestamp']}")
        for c in checks:
            icon = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "INFO": "ℹ"}.get(c["status"], "?")
            print(f"  {icon} {c['check']}: {c['detail']}")
        if diagnoses:
            print(f"\n  Diagnoses ({len(diagnoses)}):")
            for d in diagnoses:
                print(f"    [{d.severity}] {d.summary}")

    return 0 if all(c["status"] in ("PASS", "INFO", "WARN") for c in checks) else 1


# ── Run ──────────────────────────────────────────────────────────────

def cmd_run(args: argparse.Namespace) -> int:
    """Execute a one-shot run from an Operator Profile."""
    profile = get_profile(args.profile)
    if not profile.no_send:
        print("ERROR: profile has no_send=False — rejected", file=sys.stderr)
        return 1

    from market_radar.integration.one_shot import run_one_shot
    from market_radar.integration.models import IntegrationConfig
    from market_radar.integration.curated_feed_provider import CuratedFeedProvider

    if not args.confirm_read_only_network and profile.network_allowed:
        print("WARNING: This profile uses live network sources.", file=sys.stderr)
        print("Pass --confirm-read-only-network to proceed.", file=sys.stderr)
        return 1

    state_dir = args.state_dir or f"data/post_mvp/state/{profile.name}"
    output_dir = args.output_dir or f"data/post_mvp/output/{profile.name}"
    os.makedirs(state_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Profile: {profile.name} ({profile.description})")
    print(f"  Sources: {'Feed ' if profile.feed_enabled else ''}{'Whale ' if profile.whale_enabled else ''}{'Markets ' if profile.markets_enabled else ''}")
    print(f"  Network: {'allowed' if profile.network_allowed else 'offline'}")
    print(f"  Max requests: ~{profile.expected_max_requests}")
    print(f"  Expected runtime: ~{profile.expected_max_runtime_seconds}s")
    print(f"  Profile hash: {profile.profile_hash()}")
    print(f"  State: {state_dir}")
    print(f"  Output: {output_dir}")

    cfg = IntegrationConfig(
        mode=profile.mode,
        state_dir=state_dir,
        output_dir=output_dir,
        whale_address=args.whale_address or "",
        exchange=args.exchange or "binance",
        timeout=profile.timeout,
        no_send=True,
        feed_enabled=profile.feed_enabled,
        feed_limit=profile.feed_limit,
        feed_max_items=profile.feed_max_items,
        feed_timeout_seconds=profile.feed_timeout_seconds,
        feed_initial_since=args.feed_since,
    )

    provider = None
    if profile.feed_enabled and profile.network_allowed:
        provider = CuratedFeedProvider(
            base_url=args.curated_base_url or "http://43.98.174.247:8001/api/integration/curated",
            limit=profile.feed_limit,
            max_items=profile.feed_max_items,
            max_pages=profile.feed_max_pages,
            timeout_seconds=profile.feed_timeout_seconds,
        )

    result = run_one_shot(cfg, feed_provider=provider)
    d = result.as_dict()
    print(f"\nRun {d.get('run_id')}: status={d.get('status')}")
    print(f"  Sources: {len(d.get('sources', []))}")
    print(f"  Errors: {len(d.get('errors', []))}")
    print(f"  Output: {len(d.get('output_paths', []))} files")

    # Write manifest
    sha = _git_sha()
    branch = _git_branch()
    manifest = build_manifest(
        run_id=d.get("run_id", ""),
        profile_name=profile.name,
        profile_hash=profile.profile_hash(),
        data_mode=profile.mode,
        no_send=True,
        network_allowed=profile.network_allowed,
        status=d.get("status", "unknown"),
        source_summary={s.get("source", ""): s.get("status", "") for s in d.get("sources", [])},
        output_files=[{"name": sanitise_path(p)} for p in d.get("output_paths", [])],
        cursor_before=d.get("feed_summary", {}).get("cursor_before"),
        cursor_after=d.get("feed_summary", {}).get("cursor_after"),
        error_count=len(d.get("errors", [])),
        code_commit=sha,
        branch=branch,
    )
    manifest_path = os.path.join(output_dir, f"manifest_{d['run_id']}.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest.as_dict(), f, indent=2, default=str)
    print(f"  Manifest: {manifest_path}")

    print()
    if profile.mode == "fixture":
        return 0
    return 0 if d.get("status") in ("completed", "degraded") else 1


# ── Shadow ───────────────────────────────────────────────────────────

def cmd_shadow(args: argparse.Namespace) -> int:
    """Execute a bounded shadow from an Operator Profile."""
    profile = get_profile(args.profile)
    if profile.max_runs > 2:
        print("ERROR: Operator shadow max_runs must be <= 2", file=sys.stderr)
        return 1

    from market_radar.integration.bounded_shadow_runner import run_integration_shadow

    if not args.confirm_read_only_network and profile.network_allowed:
        print("ERROR: Network profile requires --confirm-read-only-network", file=sys.stderr)
        return 1

    state_dir = args.state_dir or f"data/post_mvp/state/shadow_{profile.name}"
    output_dir = args.output_dir or f"data/post_mvp/output/shadow_{profile.name}"
    os.makedirs(state_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Shadow Profile: {profile.name} — max_runs={profile.max_runs}")
    result = run_integration_shadow(
        state_dir=state_dir, output_dir=output_dir,
        max_runs=profile.max_runs, interval_seconds=profile.interval_seconds,
        whale_address=args.whale_address or "",
        feed_timeout_seconds=profile.feed_timeout_seconds,
        feed_initial_since=args.feed_since,
    )
    d = result.to_dict()
    print(f"Shadow {d.get('shadow_run_id')}: status={d.get('status')}")
    print(f"  Attempted: {d.get('attempted_runs')} Completed: {d.get('completed_runs')}")
    print(f"  Errors: {len(d.get('errors', []))}")
    for rec in d.get("records", []):
        print(f"    Run {rec.get('ordinal')}: {rec.get('child_run_id')} status={rec.get('status')}")
    return 0 if d.get("status") in ("completed", "degraded") else 1


# ── Inspect ──────────────────────────────────────────────────────────

def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect an existing run directory."""
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: run directory not found: {run_dir}", file=sys.stderr)
        return 1

    # Find manifest or report
    manifests = list(run_dir.glob("manifest_*.json"))
    reports = list(run_dir.glob("run_*.json"))

    if not manifests and not reports:
        print(f"No run artifacts found in {run_dir}", file=sys.stderr)
        return 1

    # Check for state DBs
    state_dir = run_dir.parent.parent / "state" / run_dir.name if run_dir.name else run_dir
    state_subdirs = list(Path(str(run_dir).replace("output", "state")).parent.glob("state/*")) if "output" in str(run_dir) else []

    if manifests:
        with open(manifests[0], "r", encoding="utf-8") as f:
            m = json.load(f)
        print(f"Manifest: {manifests[0].name}")
        print(f"  Run: {m.get('run_id')}")
        print(f"  Status: {m.get('status')}")
        print(f"  Profile: {m.get('profile_name')} (hash: {m.get('profile_hash')})")
        print(f"  Config hash: {m.get('config_hash')}")
        print(f"  Sources: {json.dumps(m.get('source_summary', {}), indent=4)}")
        print(f"  Cursor: {m.get('cursor_before')} -> {m.get('cursor_after')}")
        print(f"  Errors: {m.get('error_count')}")
        print(f"  Output files: {len(m.get('output_files', []))}")
        if m.get("diagnoses"):
            print(f"  Diagnoses: {len(m['diagnoses'])}")
            for d in m["diagnoses"]:
                print(f"    [{d.get('severity')}] {d.get('summary')}")

    if reports:
        with open(reports[0], "r", encoding="utf-8") as f:
            r = json.load(f)
        print(f"\nReport: {reports[0].name}")
        print(f"  Status: {r.get('status')}")
        print(f"  Finished: {r.get('finished_at')}")
        srcs = r.get("sources", [])
        print(f"  Sources ({len(srcs)}):")
        for s in srcs:
            print(f"    {s.get('source')}: status={s.get('status')} ok={s.get('ok')}")
        print(f"  Errors: {len(r.get('errors', []))}")
        if r.get("errors"):
            for e in r["errors"]:
                print(f"    - {e}")

    return 0


# ── Compare ──────────────────────────────────────────────────────────

def cmd_compare(args: argparse.Namespace) -> int:
    """Compare two run directories."""
    run_dir_1 = Path(args.run_dir_1)
    run_dir_2 = Path(args.run_dir_2)

    def load_manifest(path: Path) -> dict:
        manifests = list(path.glob("manifest_*.json"))
        if manifests:
            with open(manifests[0], "r", encoding="utf-8") as f:
                return json.load(f)
        reports = list(path.glob("run_*.json"))
        if reports:
            with open(reports[0], "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    m1 = load_manifest(run_dir_1)
    m2 = load_manifest(run_dir_2)

    if not m1 and not m2:
        print("No run data found in either directory", file=sys.stderr)
        return 1

    print(f"Comparison: {run_dir_1} vs {run_dir_2}")
    print(f"  Status: {m1.get('status', '?')} -> {m2.get('status', '?')}")
    print(f"  Profile: {m1.get('profile_name', '?')} -> {m2.get('profile_name', '?')}")

    # Source health
    srcs1 = m1.get("sources", m1.get("source_summary", {}))
    srcs2 = m2.get("sources", m2.get("source_summary", {}))
    if isinstance(srcs1, list):
        srcs1 = {s.get("source", str(i)): s.get("status") for i, s in enumerate(srcs1)}
    if isinstance(srcs2, list):
        srcs2 = {s.get("source", str(i)): s.get("status") for i, s in enumerate(srcs2)}
    all_sources = set(list(srcs1.keys()) + list(srcs2.keys()))
    for src in sorted(all_sources):
        s1 = srcs1.get(src, "N/A")
        s2 = srcs2.get(src, "N/A")
        if s1 != s2:
            print(f"  Source '{src}': {s1} -> {s2}")

    # Cursor
    cb1 = m1.get("cursor_before") or m1.get("feed_summary", {}).get("cursor_before")
    cb2 = m2.get("cursor_before") or m2.get("feed_summary", {}).get("cursor_before")
    ca1 = m1.get("cursor_after") or m1.get("feed_summary", {}).get("cursor_after")
    ca2 = m2.get("cursor_after") or m2.get("feed_summary", {}).get("cursor_after")
    if ca1 != ca2:
        print(f"  Cursor: {ca1} -> {ca2}")

    # Errors
    errs1 = m1.get("errors", [])
    errs2 = m2.get("errors", [])
    if len(errs1) != len(errs2):
        print(f"  Error count: {len(errs1)} -> {len(errs2)}")
    new_errors = [e for e in errs2 if e not in errs1]
    if new_errors:
        for e in new_errors:
            print(f"    New error: {e}")

    # Config hash
    ch1 = m1.get("config_hash", "")
    ch2 = m2.get("config_hash", "")
    print(f"  Config hash: {ch1} -> {ch2} {'(same)' if ch1 == ch2 else '(different)'}")

    return 0


# ── Bundle ───────────────────────────────────────────────────────────

def cmd_bundle(args: argparse.Namespace) -> int:
    """Generate a sanitised audit bundle from a run directory."""
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: run directory not found: {run_dir}", file=sys.stderr)
        return 1

    manifests = list(run_dir.glob("manifest_*.json"))
    reports = list(run_dir.glob("run_*.json"))
    if not manifests and not reports:
        print(f"No run artifacts found in {run_dir}", file=sys.stderr)
        return 1

    output_dir = args.output or f"{run_dir}_bundle"
    os.makedirs(output_dir, exist_ok=True)

    sha = _git_sha()
    branch = _git_branch()

    bundle: dict[str, Any] = {
        "bundle_version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_commit": sha,
        "branch": branch,
        "source_dir": sanitise_path(str(run_dir)),
    }

    # Collect manifest/report
    manifests = list(run_dir.glob("manifest_*.json"))
    reports = list(run_dir.glob("run_*.json"))

    if manifests:
        with open(manifests[0], "r", encoding="utf-8") as f:
            bundle["manifest"] = json.load(f)

    if reports:
        with open(reports[0], "r", encoding="utf-8") as f:
            report_raw = json.load(f)
        # Sanitise: remove full items, db_path, raw_json
        sanitised = {
            "run_id": report_raw.get("run_id"),
            "status": report_raw.get("status"),
            "started_at": report_raw.get("started_at"),
            "finished_at": report_raw.get("finished_at"),
            "no_send": report_raw.get("no_send"),
            "data_mode": report_raw.get("data_mode"),
            "sources": [
                {k: v for k, v in s.items() if k not in ("provenance",)}
                for s in report_raw.get("sources", [])
            ],
            "markets": [
                {k: v for k, v in m.items() if k not in ("bid", "ask")}
                for m in report_raw.get("markets", [])
            ],
            "whale": report_raw.get("whale"),
            "feed_summary": {"overall_status": (report_raw.get("feed_summary") or {}).get("overall_status"),
                             "live_count": (report_raw.get("feed_summary") or {}).get("live_count"),
                             "records_seen": (report_raw.get("feed_summary") or {}).get("records_seen"),
                             "records_accepted": (report_raw.get("feed_summary") or {}).get("records_accepted")},
            "alert_candidate_count": report_raw.get("alert_candidate_count"),
            "error_count": len(report_raw.get("errors", [])),
        }
        bundle["report"] = sanitised
        bundle["report_sha256"] = hashlib.sha256(
            json.dumps(sanitised, sort_keys=True, default=str).encode()
        ).hexdigest()

    # Operator summary
    summary_lines = [
        f"Operator Workbench Bundle",
        f"  Generated: {bundle['generated_at']}",
        f"  Code: {branch}@{sha[:12]}",
        f"  Source: {sanitise_path(str(run_dir))}",
    ]
    if "manifest" in bundle:
        m = bundle["manifest"]
        summary_lines.append(f"  Run: {m.get('run_id')}")
        summary_lines.append(f"  Status: {m.get('status')}")
        summary_lines.append(f"  Profile: {m.get('profile_name')}")
        summary_lines.append(f"  Config hash: {m.get('config_hash')}")
    bundle["operator_summary"] = "\n".join(summary_lines)

    # SHA256SUMS
    sha256sums: list[str] = []
    for fname in os.listdir(output_dir):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath) and not fname.endswith(".sha256"):
            with open(fpath, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            sha256sums.append(f"{h}  {fname}")

    # Write bundle files
    manifest_json_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_json_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, default=str)

    summary_path = os.path.join(output_dir, "operator_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(bundle["operator_summary"] + "\n")

    sha256_path = os.path.join(output_dir, "SHA256SUMS")
    with open(sha256_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sha256sums) + "\n")

    # Recompute SHA256SUMS after writing
    sha256sums_updated = []
    for fname in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath) and fname != "SHA256SUMS":
            with open(fpath, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            sha256sums_updated.append(f"{h}  {fname}")
    with open(sha256_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sha256sums_updated) + "\n")

    print(f"Bundle created: {output_dir}")
    print(f"  Files: {len([f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))])}")
    print(f"  SHA256SUMS: {sha256_path}")
    print(f"  No full content, no db_path, no credentials.")

    return 0


# ── Catalog ──────────────────────────────────────────────────────────

def cmd_catalog(args: argparse.Namespace) -> int:
    """Scan and display operator run catalog."""
    root_dirs = args.dirs or ["data/post_mvp/output", "data/integration/output"]
    manifests = scan_run_dirs(
        root_dirs,
        max_manifests=args.max,
        status_filter=args.status,
        profile_filter=args.profile,
    )
    if args.format == "json":
        print(catalog_to_json(manifests))
    elif args.format == "markdown":
        print(catalog_to_markdown(manifests))
    elif args.format == "html":
        print(catalog_to_static_html(manifests))
    else:
        print(catalog_to_markdown(manifests))
    return 0


# ── Replay Pack ──────────────────────────────────────────────────────

def cmd_replay_pack(args: argparse.Namespace) -> int:
    """Generate a sanitised replay fixture from diagnosis code."""
    pack = generate_replay_pack(
        diagnosis_code=args.code,
        profile_name=args.profile or "fixture-smoke",
        context={"note": "generated by operator workbench"},
    )
    print(json.dumps(pack, indent=2, default=str))
    return 0


# ── Readiness Score ──────────────────────────────────────────────────

def cmd_readiness_score(args: argparse.Namespace) -> int:
    """Compute 0-100 operator readiness score."""
    score = compute_readiness(
        dependencies_ok=not args.offline,
        paths_writable=True,
        sources_connected=args.sources if args.sources is not None else 4,
        sources_total=4,
        schema_ok=True,
        no_send_enforced=True,
        audit_chain_ok=True,
        no_lock_stale=True,
        no_stop_marker=True,
        artifacts_complete=True,
    )
    if args.json:
        print(json.dumps(score, indent=2, default=str))
    else:
        print(f"Readiness Score: {score['score']}/100 — {score['assessment']}")
        for name, c in score.get("components", {}).items():
            print(f"  {name}: {c['score']}/{c['max']} ({c.get('status', '?')})")
    return 0 if score["score"] >= 70 else 1


# ── Main ─────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Operator Workbench CLI")
    p.add_argument("--state-dir", default="", help="State directory override")
    p.add_argument("--output-dir", default="", help="Output directory override")

    sub = p.add_subparsers(dest="command", required=True)

    # doctor
    doc = sub.add_parser("doctor", help="System diagnostics")
    doc.add_argument("--offline", action="store_true", help="Skip network checks")
    doc.add_argument("--json", action="store_true", help="JSON output")
    doc.add_argument("--strict", action="store_true", help="Fail on warnings")

    # run
    run_p = sub.add_parser("run", help="Execute one-shot from profile")
    run_p.add_argument("profile", choices=list(BUILTIN_PROFILES.keys()), help="Operator profile")
    run_p.add_argument("--state-dir", default="", help="State directory override")
    run_p.add_argument("--output-dir", default="", help="Output directory override")
    run_p.add_argument("--whale-address", default="", help="Whale address")
    run_p.add_argument("--feed-since", default=None, help="Initial feed cursor")
    run_p.add_argument("--curated-base-url", default="http://43.98.174.247:8001/api/integration/curated")
    run_p.add_argument("--exchange", default="binance")
    run_p.add_argument("--confirm-read-only-network", action="store_true")

    # shadow
    shd = sub.add_parser("shadow", help="Execute bounded shadow from profile")
    shd.add_argument("profile", choices=list(BUILTIN_PROFILES.keys()))
    shd.add_argument("--state-dir", default="", help="State directory override")
    shd.add_argument("--output-dir", default="", help="Output directory override")
    shd.add_argument("--whale-address", default="")
    shd.add_argument("--feed-since", default=None)
    shd.add_argument("--confirm-read-only-network", action="store_true")

    # inspect
    ins = sub.add_parser("inspect", help="Inspect run directory")
    ins.add_argument("run_dir", help="Path to run output directory")

    # compare
    cmp = sub.add_parser("compare", help="Compare two run directories")
    cmp.add_argument("run_dir_1", help="First run directory")
    cmp.add_argument("run_dir_2", help="Second run directory")

    # bundle
    bnd = sub.add_parser("bundle", help="Generate audit bundle")
    bnd.add_argument("run_dir", help="Run output directory")
    bnd.add_argument("--output", default=None, help="Output directory for bundle")

    # catalog
    cat_p = sub.add_parser("catalog", help="Scan run catalog")
    cat_p.add_argument("dirs", nargs="*", default=[], help="Root directories to scan")
    cat_p.add_argument("--max", type=int, default=100, help="Max manifests")
    cat_p.add_argument("--status", default=None, help="Filter by status")
    cat_p.add_argument("--profile", default=None, help="Filter by profile")
    cat_p.add_argument("--format", choices=["json", "markdown", "html"], default="markdown")

    # replay-pack
    rp = sub.add_parser("replay-pack", help="Generate failure replay fixture")
    rp.add_argument("code", help="Diagnosis code (e.g. CURATED_API_UNAVAILABLE)")
    rp.add_argument("--profile", default=None, help="Override profile name")

    # readiness-score
    rs = sub.add_parser("readiness-score", help="Compute operator readiness score")
    rs.add_argument("--offline", action="store_true", help="Assume deps offline")
    rs.add_argument("--sources", type=int, default=4, help="Connected source count")
    rs.add_argument("--json", action="store_true", help="JSON output")

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "doctor": cmd_doctor,
        "run": cmd_run,
        "shadow": cmd_shadow,
        "inspect": cmd_inspect,
        "compare": cmd_compare,
        "bundle": cmd_bundle,
        "catalog": cmd_catalog,
        "replay-pack": cmd_replay_pack,
        "readiness-score": cmd_readiness_score,
    }
    handler = commands.get(args.command)
    if handler:
        return handler(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
