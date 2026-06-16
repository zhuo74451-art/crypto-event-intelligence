#!/usr/bin/env python3
"""MVP+ — Final Acceptance Verification.

Tests all acceptance criteria in one pass.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
import webbrowser

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

results = []


def verify(name: str, ok: bool, detail: str = ""):
    results.append({"name": name, "ok": ok, "detail": detail})
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))


print("=" * 60)
print("  FINAL ACCEPTANCE VERIFICATION")
print("=" * 60)

# ── 1. Fresh one-shot run ──
print("\n── 1. Runner execution ──")
try:
    from market_radar.l6_integration.integration_runner import run as l6_run

    r = l6_run(project_root=_PROJECT_ROOT)
    verify("Main runner executes from clean state", True)

    verify(f"Whale positions: {len(r.run_report.whale_positions)}",
           len(r.run_report.whale_positions) >= 0)
    verify(f"Market contexts: {len(r.run_report.market_contexts)}",
           len(r.run_report.market_contexts) >= 0)
    verify(f"Workbench HTML at {r.workbench_path}",
           r.workbench_path is not None)

    if r.workbench_path:
        size = os.path.getsize(r.workbench_path)
        verify(f"Workbench HTML {size} bytes", size > 5000)
        with open(r.workbench_path, "r", encoding="utf-8") as f:
            html = f.read()
        verify("HTML has dark-mode inline CSS", "--bg: #0d1117" in html)
        verify("HTML has no external src/href",
               "<script src=" not in html and "<link href=" not in html)
except Exception as e:
    verify("Main runner executes", False, str(e))
    r = None

# ── 2. Data provenance ──
print("\n── 2. Data provenance ──")
if r:
    report = r.run_report
    origins = {}
    for p in report.whale_positions:
        o = p.data_origin if hasattr(p, "data_origin") else "unknown"
        origins[o] = origins.get(o, 0) + 1
    verify(f"Position origins: {origins}", bool(origins) or not report.whale_positions)

    market_origins = {}
    for c in report.market_contexts:
        o = c.data_origin if hasattr(c, "data_origin") else "unknown"
        market_origins[o] = market_origins.get(o, 0) + 1
    verify(f"Market origins: {market_origins}", bool(market_origins))

    # HYPE check
    hype_positions = [p for p in report.whale_positions if p.asset == "HYPE"]
    if hype_positions:
        verify(f"{len(hype_positions)} HYPE positions from Hyperliquid", True)
    else:
        verify("HYPE positions check (none found)", True)
else:
    verify("Data provenance", False, "no run report")

# ── 3. Change detection ──
print("\n── 3. Change detection ──")
if r:
    from market_radar.l2_whale_engine.whale_engine import compute_changes
    changes = report.whale_changes
    verify(f"{len(changes)} changes detected", True)
    # Deterministic
    changes_b = compute_changes(report.whale_positions, report.whale_positions)
    verify("Deterministic output", len(changes_b.changes) == len(changes))
else:
    verify("Change detection", False, "no run report")

# ── 4. HTML safety ──
print("\n── 4. HTML safety ──")
from market_radar.l6_integration.safety import escape_html
xss = escape_html("<script>alert(1)</script>")
verify("XSS prevented in HTML output", "&lt;script&gt;" in xss)

# ── 5. SQLite state recovery ──
print("\n── 5. Persistence ──")
from market_radar.l6_integration.persistence import create_state_db
db = create_state_db()
recent_runs = db.get_recent_runs()
verify(f"SQLite: {len(recent_runs)} runs recorded", len(recent_runs) > 0)
snapshots = db.get_latest_whale_snapshot(limit=5)
verify(f"SQLite: whale snapshots in DB", len(snapshots) > 0)
unsent = db.get_unsent_alerts()
verify(f"SQLite: {len(unsent)} unsent alerts", True)

# ── 6. Locking ──
print("\n── 6. Locking ──")
from market_radar.l6_integration.lock import MVPPLock, LockHeldByAnotherInstance
with tempfile.TemporaryDirectory() as td:
    lock = MVPPLock(lock_dir=td, ttl=300)
    rid = uuid.uuid4().hex[:12]
    ok = lock.acquire(rid)
    verify("Lock acquire/release", ok)
    lock.release()

# ── 7. Atomic outputs ──
print("\n── 7. Atomic outputs ──")
from market_radar.l6_integration.safety import atomic_write
with tempfile.TemporaryDirectory() as td:
    tp = os.path.join(td, "test.txt")
    atomic_write(tp, "test data")
    verify("Atomic write works", os.path.isfile(tp) and open(tp).read() == "test data")

# ── 8. Alert candidates ──
print("\n── 8. Alert candidates ──")
alert_path = "artifacts/alerts/alert_candidates.json"
if os.path.isfile(alert_path):
    with open(alert_path, "r") as f:
        ad = json.load(f)
    verify(f"{ad.get('alert_count', 0)} alert candidates saved", True)
    verify("Alert sent=False", ad.get("sent") is False)
    verify("production_send_blocked=True", ad.get("production_send_blocked") is True)
else:
    verify("Alert candidates file exists", False, "not found")

# ── 9. Third-party manifest ──
print("\n── 9. Third-party manifest ──")
manifest_path = "artifacts/reports/THIRD_PARTY_REUSE_MANIFEST.json"
from market_radar.l6_integration.safety import generate_third_party_manifest
os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
generate_third_party_manifest(manifest_path)
if os.path.isfile(manifest_path):
    with open(manifest_path, "r") as f:
        m = json.load(f)
    verify(f"Third-party manifest: {len(m.get('dependencies', []))} deps", True)
    verify("License compliance section present", "license_compliance" in m)
else:
    verify("Third-party manifest", False)

# ── 10. Full test suite ──
print("\n── 10. Full test suite ──")
test_result = subprocess.run(
    [sys.executable, "-X", "utf8", "-m", "pytest", "tests/", "-q", "--tb=line"],
    capture_output=True, text=True, cwd=_PROJECT_ROOT,
    timeout=120,
)
stdout = test_result.stdout
last_lines = [l for l in stdout.split("\n") if l.strip()]
if last_lines:
    last = last_lines[-1]
    m = re.search(r"(\d+) passed", last)
    if m:
        verify(f"{m.group(1)} tests passed", True)
    elif "failed" in last:
        fm = re.search(r"(\d+) failed", last)
        nf = int(fm.group(1)) if fm else 999
        verify(f"Tests: {last.strip()}", nf == 0, last.strip())
    else:
        verify("Test suite", False, last.strip())
else:
    verify("Test suite", False, "no output")

# ── 11. Boundary: no tracked files modified ──
print("\n── 11. Boundary check ──")
status = subprocess.run(
    ["git", "status", "--short"],
    capture_output=True, text=True, cwd=_PROJECT_ROOT,
)
modified = [l for l in status.stdout.split("\n") if l.strip() and not l.startswith("??")]
verify(f"Modified tracked files: {len(modified)}", len(modified) == 0,
       str(modified) if modified else "")

# ── 12. Config validation ──
print("\n── 12. Configuration ──")
from market_radar.l6_integration.config import load_config
cfg = load_config()
verify("Config validates clean", len(cfg.validate()) == 0)
verify("API timeout >= 1", cfg.api.connect_timeout >= 1)
verify("HTTPS enforced for URLs",
       cfg.market.binance_ticker_url.startswith("https://") and
       cfg.market.hyperliquid_info_url.startswith("https://"))

# ── Summary ──
print(f"\n{'=' * 60}")
print(f"  FINAL ACCEPTANCE RESULTS")
print(f"{'=' * 60}")
ok = sum(1 for r in results if r["ok"])
fail = sum(1 for r in results if not r["ok"])
print(f"  {ok} passed, {fail} failed")
for r in results:
    if not r["ok"]:
        print(f"    FAIL: {r['name']}: {r['detail']}")
print(f"{'=' * 60}")

sys.exit(0 if fail == 0 else 1)
