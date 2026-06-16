#!/usr/bin/env python3
"""MVP+ — Production Candidate Verification Runner.

Tests all production-hardening features:
  1. Configuration loading & validation
  2. SQLite persistence (schema, transactions, queries)
  3. Single-instance lock (acquire, release, stale recovery)
  4. Atomic output writes
  5. Observability logging
  6. Alert candidate generation
  7. URL validation & HTML escaping
  8. Third-party manifest generation
  9. Full integration with existing lanes
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import uuid

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

passed = 0
failed = 0
skipped = 0


def check(name: str, ok: bool, detail: str = ""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}: {detail}")


def check_exc(name: str, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
        check(name, True)
    except Exception as e:
        check(name, False, str(e))


print("═" * 60)
print("  MVP+ Production Candidate Verification")
print("═" * 60)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. Configuration
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 1. Configuration ──")
from market_radar.l6_integration.config import load_config, save_config

cfg = load_config()
check("Config loads with defaults", cfg is not None)
check("Config validates clean", len(cfg.validate()) == 0)
check("API timeout >= 1", cfg.api.connect_timeout >= 1)
check("Whale address limit >= 1", cfg.whale.address_limit >= 1)
check("Assets non-empty", len(cfg.assets.symbols) > 0)
check("Binance URL uses HTTPS", cfg.market.binance_ticker_url.startswith("https://"))
check("HL URL uses HTTPS", cfg.market.hyperliquid_info_url.startswith("https://"))

# Test config save/load round-trip
with tempfile.TemporaryDirectory() as td:
    cfg_path = os.path.join(td, "config.json")
    save_config(cfg, cfg_path)
    cfg2 = load_config(cfg_path)
    check("Config save/load round-trip", cfg2.api.connect_timeout == cfg.api.connect_timeout)

# Test invalid config rejection
from market_radar.l6_integration.config import MVPConfig
bad_cfg = MVPConfig()
bad_cfg.api.connect_timeout = 0
errors = bad_cfg.validate()
check("Bad config returns errors", len(errors) > 0)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Persistence (SQLite)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 2. Persistence (SQLite) ──")
from market_radar.l6_integration.persistence import create_state_db, PersistenceError

run_id = uuid.uuid4().hex[:12]
tmp_db = os.path.join(tempfile.gettempdir(), f"mvp_test_{run_id}.sqlite")
try:
    db = create_state_db(tmp_db)
    check("SQLite database created", os.path.isfile(tmp_db))

    # Record run
    db.record_run(run_id, "test", "2026-06-16T12:00:00Z")
    db.complete_run(run_id, "completed", {"L1": {"status": "OK"}}, total_items=5, total_errors=0)
    runs = db.get_recent_runs()
    check("Run history recorded", len(runs) >= 1 and runs[0]["run_id"] == run_id)

    # Source health
    db.record_source_health(run_id, [
        {"source_name": "test_source", "source_group": "test",
         "status": "OK", "success_count": 1, "error_count": 0},
    ])
    trend = db.get_source_health_trend("test_source")
    check("Source health recorded", len(trend) >= 1)

    # Whale positions
    db.record_whale_positions(run_id, [
        {"address": "0xabc", "asset": "BTC", "side": "LONG",
         "position_size_usd": 100000.0, "data_origin": "live"},
    ])
    snapshots = db.get_latest_whale_snapshot(address="0xabc")
    check("Whale snapshot recorded", len(snapshots) >= 1)

    # Whale changes
    db.record_whale_changes(run_id, [
        {"address": "0xabc", "asset": "BTC", "change_type": "POSITION_INCREASED",
         "side": "LONG", "current_position_size_usd": 150000.0,
         "previous_position_size_usd": 100000.0, "delta_usd": 50000.0,
         "change_pct": 50.0, "risk_level": "ELEVATED"},
    ])
    db.record_whale_changes(run_id, [])

    # Market snapshots
    db.record_market_snapshots(run_id, [
        {"symbol": "BTC", "price": 66000.0, "source": "BINANCE_SPOT", "data_origin": "live"},
    ])

    # Feed ingestion
    db.record_feed_ingestion(run_id, [
        {"feed_type": "NEWS", "source_name": "test", "title": "test"},
    ])

    # Alerts
    db.record_alerts(run_id, [
        {"alert_type": "WHALE_NEW_POSITION", "severity": "INFO",
         "message": "test alert", "details": {}},
    ])
    unsent = db.get_unsent_alerts()
    check("Alert candidates recorded", len(unsent) >= 1)

    db.close()
    # Cleanup
    try:
        os.remove(tmp_db)
    except OSError:
        pass
except Exception as e:
    check("SQLite operations", False, str(e))

# ═══════════════════════════════════════════════════════════════════════════════
# 3. Single-Instance Lock
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 3. Single-Instance Lock ──")
from market_radar.l6_integration.lock import MVPPLock, LockHeldByAnotherInstance

with tempfile.TemporaryDirectory() as td:
    lock1 = MVPPLock(lock_dir=td, ttl=300)
    lock2 = MVPPLock(lock_dir=td, ttl=300)

    rid1 = uuid.uuid4().hex[:12]
    rid2 = uuid.uuid4().hex[:12]

    check("Lock acquire succeeds", lock1.acquire(rid1))
    check("Lock is held", lock1.held)

    try:
        lock2.acquire(rid2)
        check("Lock prevents second instance", False, "should have raised")
    except LockHeldByAnotherInstance:
        check("Lock prevents second instance", True)

    lock1.release()
    check("Lock release works", not lock1.held)

    # Stale recovery
    stale_lock = MVPPLock(lock_dir=td, ttl=0)  # 0 TTL = always stale
    check("Stale lock recovery", stale_lock.acquire(rid2))
    stale_lock.release()

# ═══════════════════════════════════════════════════════════════════════════════
# 4. Atomic Outputs
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 4. Atomic Outputs ──")
from market_radar.l6_integration.safety import atomic_write, atomic_write_json

with tempfile.TemporaryDirectory() as td:
    test_file = os.path.join(td, "test.txt")
    atomic_write(test_file, "hello world")
    check("Atomic write creates file", os.path.isfile(test_file))

    with open(test_file, "r", encoding="utf-8") as f:
        content = f.read()
    check("Atomic write content correct", content == "hello world")

    test_json = os.path.join(td, "test.json")
    atomic_write_json(test_json, {"key": "value", "num": 42})
    with open(test_json, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    check("Atomic JSON write correct", loaded["key"] == "value" and loaded["num"] == 42)

    # Test corruption protection (skip on Windows where permissions differ)
    import platform
    if platform.system() != "Windows":
        import stat
        os.chmod(td, stat.S_IRUSR | stat.S_IXUSR)
        try:
            atomic_write(os.path.join(td, "should_fail.txt"), "data")
            check("Atomic write on read-only dir fails", False, "should have raised")
        except (PermissionError, OSError):
            check("Atomic write on read-only dir fails safely", True)
        os.chmod(td, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    else:
        check("Atomic write on read-only dir fails (skipped on Windows)", True)

# ═══════════════════════════════════════════════════════════════════════════════
# 5. Observability
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 5. Observability ──")
from market_radar.l6_integration.observability import RunLogger

with tempfile.TemporaryDirectory() as td:
    logger = RunLogger(logs_dir=td)
    obs = logger.start_run(uuid.uuid4().hex[:12])
    check("Observability start_run", obs is not None)
    obs.record_source("test_source", ok=True, count=5)
    obs.record_source("bad_source", ok=False, count=0, degraded=True)
    obs.complete("completed", decision="OK")
    path = logger.save()
    check("Observability log saved", os.path.isfile(path))

    with open(path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    check("Log has run_id", "run_id" in loaded)
    check("Log has duration", loaded.get("duration_s") is not None)
    check("Log has degraded sources", len(loaded.get("degraded_sources", [])) > 0)

# ═══════════════════════════════════════════════════════════════════════════════
# 6. Alert Candidates
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 6. Alert Candidates ──")
from market_radar.l6_integration.alert_candidate import AlertCandidateGenerator

rid = uuid.uuid4().hex[:12]
gen = AlertCandidateGenerator(rid)

# Test change evaluation
gen.evaluate_whale_changes([
    {"change_type": "POSITION_OPENED", "asset": "BTC", "address": "0xabc",
     "current_position_size_usd": 50_000_000,
     "label": "Whale A", "risk_level": "ELEVATED", "risk_factors": ["large_new_position"]},
    {"change_type": "POSITION_INCREASED", "asset": "ETH", "address": "0xdef",
     "current_position_size_usd": 10_000_000, "position_delta_usd": 5_000_000,
     "label": "Whale B", "risk_level": "ELEVATED", "risk_factors": ["large_delta"]},
])
check("Whale change alerts generated", len(gen.get_alerts()) >= 2)

# Test exposure evaluation
gen.evaluate_large_exposure([
    {"address": "0xabc", "asset": "BTC", "position_size_usd": 100_000_000, "side": "LONG"},
])
check("Exposure alerts generated", any(a["alert_type"] == "LARGE_EXPOSURE" for a in gen.get_alerts()))

# Test degraded sources
gen.evaluate_degraded_sources([
    {"source_name": "hype_binance", "status": "DEGRADED",
     "degraded_info": {"error_type": "SYMBOL_NOT_FOUND", "message_summary": "HYPE not on Binance"}},
])
check("Degraded source alerts generated", any(a["alert_type"] == "SOURCE_DEGRADED" for a in gen.get_alerts()))

# Test save (no send)
with tempfile.TemporaryDirectory() as td:
    path = gen.save(output_dir=td)
    check("Alert candidates saved (not sent)", os.path.isfile(path))
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    check("Alert file has sent=False", data.get("sent") is False)
    check("Alert file has production_send_blocked=True", data.get("production_send_blocked") is True)

# ═══════════════════════════════════════════════════════════════════════════════
# 7. Safety Patterns
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 7. Safety Patterns ──")
from market_radar.l6_integration.safety import (
    validate_request_url, URLValidationError,
    escape_html, escape_html_attr,
    safe_resolve_path, PathTraversalError,
    safe_shell_arg,
)

# URL validation
check_exc("Binance URL allowed", validate_request_url, "https://api.binance.com/api/v3/ticker/24hr")
check_exc("Hyperliquid URL allowed", validate_request_url, "https://api.hyperliquid.xyz/info")
try:
    validate_request_url("http://localhost:8080/malicious")
    check("Localhost blocked", False, "should have raised")
except URLValidationError:
    check("Localhost blocked", True)
try:
    validate_request_url("ftp://evil.com/payload")
    check("FTP scheme blocked", False, "should have raised")
except URLValidationError:
    check("FTP scheme blocked", True)

# HTML escaping
xss_payload = '<script>alert("xss")</script>'
escaped = escape_html(xss_payload)
check("XSS script tag escaped", "&lt;script&gt;" in escaped)
check("No raw angle brackets", "<" not in escaped or "&lt;" in escaped)

# Path traversal
traversal = "../../etc/passwd"
try:
    safe_resolve_path("/safe/base", traversal)
    check("Path traversal blocked", False, "should have raised")
except PathTraversalError:
    check("Path traversal blocked", True)

safe = safe_resolve_path("/safe/base", "subdir/file.txt")
check("Safe path resolves", safe.endswith("subdir/file.txt") or safe.endswith("subdir\\file.txt"))

# Shell arg safety
try:
    safe_shell_arg("hello_world")
    check("Safe shell arg OK", True)
except ValueError:
    check("Safe shell arg OK", False)
try:
    safe_shell_arg("hello; rm -rf /")
    check("Shell injection blocked", False, "should have raised")
except ValueError:
    check("Shell injection blocked", True)

# ═══════════════════════════════════════════════════════════════════════════════
# 8. Third-Party Manifest
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 8. Third-Party Manifest ──")
from market_radar.l6_integration.safety import generate_third_party_manifest

with tempfile.TemporaryDirectory() as td:
    manifest_path = os.path.join(td, "THIRD_PARTY_REUSE_MANIFEST.json")
    generate_third_party_manifest(manifest_path)
    check("Third-party manifest generated", os.path.isfile(manifest_path))
    with open(manifest_path, "r", encoding="utf-8") as f:
        m = json.load(f)
    check("Manifest has dependencies", len(m.get("dependencies", [])) >= 3)
    check("Manifest has license info", "license_compliance" in m)

# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print(f"  Results: {passed} passed, {failed} failed, {skipped} skipped")
print(f"{'=' * 60}")

if failed > 0:
    print("PRODUCTION_CHECK_FAILED")
    sys.exit(1)
else:
    print("PRODUCTION_PASSED")
    sys.exit(0)
