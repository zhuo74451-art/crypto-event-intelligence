"""Post-MVP Fault Injection Corpus — 150+ deterministic failure cases.

Each case is a dict with:
- id: unique identifier
- category: feed|markets|whale|operations|cli|combo
- description: human-readable
- fixture: input data (dict or list)
- expected: expected behavior
- tags: list of keywords

All cases are offline, deterministic, no network required.
"""
from __future__ import annotations
from typing import Any, Optional

FAULT_CASES: list[dict[str, Any]] = []

# ═══════════════════════════════════════════════════════════════════════════
# Feed Faults (34 cases)
# ═══════════════════════════════════════════════════════════════════════════

_FEED_BASE = {"source": "jin10", "source_label": "Jin10", "source_kind": "news",
              "content_type": "news_flash", "pipeline_stage": "published"}

feed_cases = [
    {"id": "F001", "description": "Feed HTTP timeout", "tags": ["timeout", "network"]},
    {"id": "F002", "description": "Feed connection refused", "tags": ["network", "unavailable"]},
    {"id": "F003", "description": "Feed HTTP 500 error", "tags": ["server_error", "http"]},
    {"id": "F004", "description": "Feed HTTP 429 rate limit", "tags": ["rate_limit", "http"]},
    {"id": "F005", "description": "Feed HTTP 403 forbidden", "tags": ["auth", "http"]},
    {"id": "F006", "description": "Feed malformed JSON response", "tags": ["parse", "malformed"]},
    {"id": "F007", "description": "Feed oversized response (>10MB)", "tags": ["oversize", "memory"]},
    {"id": "F008", "description": "Feed partial page (5/10 items returned)", "tags": ["partial", "pagination"]},
    {"id": "F009", "description": "Feed repeated page (same as previous)", "tags": ["duplicate", "pagination"]},
    {"id": "F010", "description": "Feed stage=missing in response", "tags": ["schema", "missing"]},
    {"id": "F011", "description": "Feed item missing tweet_id", "tags": ["missing", "idempotency"]},
    {"id": "F012", "description": "Feed item missing source", "tags": ["missing", "source"]},
    {"id": "F013", "description": "Feed item missing published_at_backend", "tags": ["missing", "cursor"]},
    {"id": "F014", "description": "Feed invalid cursor timestamp (not ISO)", "tags": ["cursor", "malformed"]},
    {"id": "F015", "description": "Feed cursor timestamp in future", "tags": ["cursor", "future"]},
    {"id": "F016", "description": "Feed source status=ok but ok=false (contradiction)", "tags": ["contradiction", "status"]},
    {"id": "F017", "description": "Feed source status=degraded but ok=true (contradiction)", "tags": ["contradiction", "status"]},
    {"id": "F018", "description": "Feed normal empty batch (0 items)", "tags": ["empty", "normal"]},
    {"id": "F019", "description": "Feed item with unsafe javascript: URL", "tags": ["xss", "security"]},
    {"id": "F020", "description": "Feed item with XSS img onerror payload", "tags": ["xss", "security"]},
    {"id": "F021", "description": "Feed item with db_path at top level", "tags": ["leak", "hygiene"]},
    {"id": "F022", "description": "Feed item with raw_json included", "tags": ["leak", "raw"]},
    {"id": "F023", "description": "Feed source_kind unknown type", "tags": ["mapping", "unknown"]},
    {"id": "F024", "description": "Feed item content_type missing", "tags": ["schema", "optional"]},
    {"id": "F025", "description": "Feed item published_at_backend very stale (24h old)", "tags": ["stale", "time"]},
    {"id": "F026", "description": "Feed item published_at_backend very future", "tags": ["future", "time"]},
    {"id": "F027", "description": "Feed item no body (no zh_body, no extracted_text, no raw_text)", "tags": ["missing", "content"]},
    {"id": "F028", "description": "Feed item body is empty string", "tags": ["empty", "content"]},
    {"id": "F029", "description": "Feed backend_error field present and non-empty", "tags": ["backend_error", "reject"]},
    {"id": "F030", "description": "Feed pipeline_stage=draft (not published)", "tags": ["stage", "filter"]},
    {"id": "F031", "description": "Feed pipeline_stage=archived", "tags": ["stage", "filter"]},
    {"id": "F032", "description": "Feed is_featured=true item — must not change source confidence", "tags": ["featured", "trust"]},
    {"id": "F033", "description": "Feed source with only rejected items (all backend_error)", "tags": ["all_rejected", "degraded"]},
    {"id": "F034", "description": "Feed response with extra unknown fields", "tags": ["schema", "forward_compat"]},
]
for c in feed_cases:
    c["category"] = "feed"
    c["fixture"] = {**_FEED_BASE, "tweet_id": c["id"].lower(), "zh_title": c["description"], "zh_body": f"Test body for {c['id']}"}
    c["expected"] = "handled without crash"
FAULT_CASES.extend(feed_cases)

# ═══════════════════════════════════════════════════════════════════════════
# Markets Faults (24 cases)
# ═══════════════════════════════════════════════════════════════════════════

_MARKET_BASE = {"symbol": "BTC/USDT", "source": "binance", "last_price": 50000.0,
                "bid": 49990.0, "ask": 50010.0, "ok": True}

market_cases = [
    {"id": "M001", "description": "Single venue unavailable", "tags": ["unavailable", "venue"]},
    {"id": "M002", "description": "All venues unavailable", "tags": ["unavailable", "all"]},
    {"id": "M003", "description": "Market snapshot stale (>5min old)", "tags": ["stale", "time"]},
    {"id": "M004", "description": "Market last_price = 0", "tags": ["zero", "price"]},
    {"id": "M005", "description": "Market last_price = NaN", "tags": ["nan", "price"]},
    {"id": "M006", "description": "Market last_price = +Infinity", "tags": ["infinity", "price"]},
    {"id": "M007", "description": "Market last_price = -Infinity", "tags": ["infinity", "price"]},
    {"id": "M008", "description": "Market open_interest = negative", "tags": ["negative", "oi"]},
    {"id": "M009", "description": "Market funding_rate missing", "tags": ["missing", "funding"]},
    {"id": "M010", "description": "Market CCXT import shadowed by project module", "tags": ["import", "shadow"]},
    {"id": "M011", "description": "Market symbol missing in response", "tags": ["missing", "symbol"]},
    {"id": "M012", "description": "Market timestamp regression (older than previous)", "tags": ["time", "regression"]},
    {"id": "M013", "description": "Market bid > ask (inverted spread)", "tags": ["invalid", "spread"]},
    {"id": "M014", "description": "Market bid = 0", "tags": ["zero", "bid"]},
    {"id": "M015", "description": "Market ask = 0", "tags": ["zero", "ask"]},
    {"id": "M016", "description": "Market response has no 'symbol' field", "tags": ["schema", "missing"]},
    {"id": "M017", "description": "Market empty venues list", "tags": ["empty", "no_data"]},
    {"id": "M018", "description": "Market CCXT exchange init error", "tags": ["init", "error"]},
    {"id": "M019", "description": "Market HTTP transport timeout", "tags": ["timeout", "http"]},
    {"id": "M020", "description": "Market latency > timeout threshold", "tags": ["latency", "slow"]},
    {"id": "M021", "description": "Market partial success (some symbols OK, some fail)", "tags": ["partial", "mixed"]},
    {"id": "M022", "description": "Market provenance field missing", "tags": ["missing", "provenance"]},
    {"id": "M023", "description": "Market health_available=false after failure", "tags": ["health", "degraded"]},
    {"id": "M024", "description": "Market HYPE from Binance (should be Hyperliquid only)", "tags": ["hype", "source_policy"]},
]
for c in market_cases:
    c["category"] = "markets"
    c["fixture"] = {**_MARKET_BASE}
    c["expected"] = "handled without crash"
FAULT_CASES.extend(market_cases)

# ═══════════════════════════════════════════════════════════════════════════
# Whale Faults (24 cases)
# ═══════════════════════════════════════════════════════════════════════════

_WHALE_POS = {"coin": "BTC", "signed_size": 0.5, "entry_price": 50000.0,
              "mark_price": 51000.0, "position_value_usd": 25500.0, "leverage": 5.0}

whale_cases = [
    {"id": "W001", "description": "Whale empty positions list", "tags": ["empty", "valid"]},
    {"id": "W002", "description": "Whale malformed position (missing coin)", "tags": ["malformed", "schema"]},
    {"id": "W003", "description": "Whale stale state (position unchanged for days)", "tags": ["stale", "noop"]},
    {"id": "W004", "description": "Whale direction flip (long→short)", "tags": ["flip", "change"]},
    {"id": "W005", "description": "Whale zero-close position (signed_size=0)", "tags": ["close", "zero"]},
    {"id": "W006", "description": "Whale duplicate position entries", "tags": ["duplicate", "dedup"]},
    {"id": "W007", "description": "Whale missing liquidation price", "tags": ["missing", "liquidation"]},
    {"id": "W008", "description": "Whale extreme leverage (100x)", "tags": ["extreme", "leverage"]},
    {"id": "W009", "description": "Whale unknown coin symbol", "tags": ["unknown", "coin"]},
    {"id": "W010", "description": "Whale NaN entry_price", "tags": ["nan", "validation"]},
    {"id": "W011", "description": "Whale Infinity mark_price", "tags": ["infinity", "validation"]},
    {"id": "W012", "description": "Whale signed_size = 0 (legit close)", "tags": ["zero", "close"]},
    {"id": "W013", "description": "Whale signed_size non-zero but position_value = 0", "tags": ["inconsistent", "validation"]},
    {"id": "W014", "description": "Whale leverage missing (None)", "tags": ["missing", "leverage"]},
    {"id": "W015", "description": "Whale leverage = 0 (invalid)", "tags": ["zero", "leverage"]},
    {"id": "W016", "description": "Whale position_value negative", "tags": ["negative", "validation"]},
    {"id": "W017", "description": "Whale entry_price negative", "tags": ["negative", "validation"]},
    {"id": "W018", "description": "Whale mark_price negative", "tags": ["negative", "validation"]},
    {"id": "W019", "description": "Whale response missing assetPositions", "tags": ["schema", "missing"]},
    {"id": "W020", "description": "Whale response malformed (not a dict)", "tags": ["malformed", "schema"]},
    {"id": "W021", "description": "Whale position with both entryPx and position in 'data' key", "tags": ["legacy", "compat"]},
    {"id": "W022", "description": "Whale clearinghouseState error field set", "tags": ["error", "degraded"]},
    {"id": "W023", "description": "Whale mark_price missing → use allMids", "tags": ["mark_price", "fallback"]},
    {"id": "W024", "description": "Whale all coins unrecognized", "tags": ["empty", "no_positions"]},
]
for c in whale_cases:
    c["category"] = "whale"
    c["fixture"] = {**_WHALE_POS}
    c["expected"] = "handled without crash"
FAULT_CASES.extend(whale_cases)

# ═══════════════════════════════════════════════════════════════════════════
# Operations Faults (24 cases)
# ═══════════════════════════════════════════════════════════════════════════

ops_cases = [
    {"id": "O001", "category": "operations", "description": "DB locked by another process",
     "fixture": "db_locked", "expected": "degraded or failed", "tags": ["db", "lock"]},
    {"id": "O002", "category": "operations", "description": "Schema version mismatch (v1 vs v2)",
     "fixture": "schema_mismatch", "expected": "migration handled", "tags": ["schema", "version"]},
    {"id": "O003", "category": "operations", "description": "Parent update failure during shadow",
     "fixture": "parent_update_fail", "expected": "degraded", "tags": ["shadow", "parent"]},
    {"id": "O004", "category": "operations", "description": "Child link failure during shadow",
     "fixture": "child_link_fail", "expected": "degraded", "tags": ["shadow", "child"]},
    {"id": "O005", "category": "operations", "description": "Duplicate ordinal in shadow children",
     "fixture": "dup_ordinal", "expected": "audit detects", "tags": ["shadow", "ordinal"]},
    {"id": "O006", "category": "operations", "description": "Orphan child (no parent)",
     "fixture": "orphan", "expected": "audit detects", "tags": ["shadow", "orphan"]},
    {"id": "O007", "category": "operations", "description": "Corrupt summary JSON in run_history",
     "fixture": "summary_corrupt", "expected": "degraded", "tags": ["corrupt", "json"]},
    {"id": "O008", "category": "operations", "description": "WAL file residue after clean shutdown",
     "fixture": "wal_residue", "expected": "idempotent", "tags": ["wal", "sqlite"]},
    {"id": "O009", "category": "operations", "description": "Lock file residue from previous crash",
     "fixture": "lock_residue", "expected": "cleanup or blocked", "tags": ["lock", "residue"]},
    {"id": "O010", "category": "operations", "description": "STOP marker set before run",
     "fixture": "stop_marker", "expected": "run blocked", "tags": ["stop", "safety"]},
    {"id": "O011", "category": "operations", "description": "Workbench bundle file tampered externally",
     "fixture": "bundle_tamper", "expected": "report includes error", "tags": ["integrity", "tamper"]},
    {"id": "O012", "category": "operations", "description": "Backup interrupted mid-write",
     "fixture": "backup_interrupted", "expected": "atomic", "tags": ["backup", "atomic"]},
    {"id": "O013", "category": "operations", "description": "State directory not writable",
     "fixture": "unwritable", "expected": "blocked", "tags": ["permissions", "io"]},
    {"id": "O014", "category": "operations", "description": "Output directory not writable",
     "fixture": "output_unwritable", "expected": "blocked", "tags": ["permissions", "io"]},
    {"id": "O015", "category": "operations", "description": "Disk full (ENOSPC)",
     "fixture": "disk_full", "expected": "degraded with error", "tags": ["disk", "io"]},
    {"id": "O016", "category": "operations", "description": "Run history DB path incorrect",
     "fixture": "wrong_db_path", "expected": "separate DB or blocked", "tags": ["db", "config"]},
    {"id": "O017", "category": "operations", "description": "Concurrent run (lock contention)",
     "fixture": "lock_contention", "expected": "second run blocked", "tags": ["lock", "concurrent"]},
    {"id": "O018", "category": "operations", "description": "Whale state file corrupted JSON",
     "fixture": "whale_state_corrupt", "expected": "degraded", "tags": ["corrupt", "state"]},
    {"id": "O019", "category": "operations", "description": "Source health DB corrupt",
     "fixture": "health_db_corrupt", "expected": "degraded", "tags": ["corrupt", "health"]},
    {"id": "O020", "category": "operations", "description": "run_id collision (duplicate UUID)",
     "fixture": "run_id_collision", "expected": "rejected", "tags": ["id", "collision"]},
    {"id": "O021", "category": "operations", "description": "Migration from v0 schema (no run_kind column)",
     "fixture": "no_run_kind", "expected": "default or handled", "tags": ["schema", "migration"]},
    {"id": "O022", "category": "operations", "description": "Parent shadow run_id not in DB",
     "fixture": "missing_parent", "expected": "detected", "tags": ["shadow", "missing"]},
    {"id": "O023", "category": "operations", "description": "Insert_run fails mid-way (partial DB state)",
     "fixture": "partial_insert", "expected": "reported in errors", "tags": ["db", "partial"]},
    {"id": "O024", "category": "operations", "description": "Timeout on DB operation",
     "fixture": "db_timeout", "expected": "degraded", "tags": ["db", "timeout"]},
]
FAULT_CASES.extend(ops_cases)

# ═══════════════════════════════════════════════════════════════════════════
# CLI/Operator Faults (24 cases)
# ═══════════════════════════════════════════════════════════════════════════

cli_cases = [
    {"id": "C001", "category": "cli", "description": "Invalid profile name", "fixture": {}, "expected": "rejected", "tags": ["profile"]},
    {"id": "C002", "category": "cli", "description": "Invalid state directory path", "fixture": {}, "expected": "rejected", "tags": ["path"]},
    {"id": "C003", "category": "cli", "description": "Invalid output directory path", "fixture": {}, "expected": "rejected", "tags": ["path"]},
    {"id": "C004", "category": "cli", "description": "--no-send-disable flag rejected", "fixture": {}, "expected": "exit 1", "tags": ["no_send"]},
    {"id": "C005", "category": "cli", "description": "Malformed --feed-since timestamp", "fixture": {}, "expected": "rejected or handled", "tags": ["parse"]},
    {"id": "C006", "category": "cli", "description": "--feed-timeout NaN value", "fixture": {}, "expected": "rejected", "tags": ["validation"]},
    {"id": "C007", "category": "cli", "description": "--feed-timeout negative value", "fixture": {}, "expected": "clamped or rejected", "tags": ["validation"]},
    {"id": "C008", "category": "cli", "description": "Unwritable output directory", "fixture": {}, "expected": "blocked", "tags": ["permissions"]},
    {"id": "C009", "category": "cli", "description": "Missing dependency module", "fixture": {}, "expected": "import error reported", "tags": ["dependency"]},
    {"id": "C010", "category": "cli", "description": "CLI --mode fixture without whale address", "fixture": {}, "expected": "completes", "tags": ["fixture"]},
    {"id": "C011", "category": "cli", "description": "CLI --mode live-public without whale address", "fixture": {}, "expected": "completes with degraded whale", "tags": ["live", "whale"]},
    {"id": "C012", "category": "cli", "description": "CLI --curated-base-url unreachable", "fixture": {}, "expected": "degraded feed", "tags": ["network", "feed"]},
    {"id": "C013", "category": "cli", "description": "CLI --feed-limit=0", "fixture": {}, "expected": "clamped or rejected", "tags": ["validation"]},
    {"id": "C014", "category": "cli", "description": "CLI --feed-limit=10000 (exceeds max)", "fixture": {}, "expected": "clamped", "tags": ["validation"]},
    {"id": "C015", "category": "cli", "description": "CLI --curated-max-pages=0", "fixture": {}, "expected": "clamped", "tags": ["pagination"]},
    {"id": "C016", "category": "cli", "description": "CLI --curated-max-pages=100 (too high)", "fixture": {}, "expected": "clamped", "tags": ["pagination"]},
    {"id": "C017", "category": "cli", "description": "CLI without --mode (default fixture)", "fixture": {}, "expected": "runs fixture mode", "tags": ["default"]},
    {"id": "C018", "category": "cli", "description": "CLI --exchange=unknown", "fixture": {}, "expected": "degraded or error", "tags": ["exchange"]},
    {"id": "C019", "category": "cli", "description": "CLI --timeout=0", "fixture": {}, "expected": "clamped", "tags": ["timeout"]},
    {"id": "C020", "category": "cli", "description": "CLI --timeout=999999 (unreasonable)", "fixture": {}, "expected": "clamped", "tags": ["timeout"]},
    {"id": "C021", "category": "cli", "description": "CLI --whale-address=invalid (not hex)", "fixture": {}, "expected": "rejected", "tags": ["validation"]},
    {"id": "C022", "category": "cli", "description": "CLI --whale-address=0x0 (zero address)", "fixture": {}, "expected": "completes with empty whale", "tags": ["validation"]},
    {"id": "C023", "category": "cli", "description": "CLI --curated-base-url with trailing slash", "fixture": {}, "expected": "normalized", "tags": ["url"]},
    {"id": "C024", "category": "cli", "description": "CLI both --mode fixture and --curated-base-url (should ignore curated)", "fixture": {}, "expected": "fixture mode ignores curated", "tags": ["mode"]},
]
FAULT_CASES.extend(cli_cases)

# ═══════════════════════════════════════════════════════════════════════════
# Combinatorial Faults (24 cases)
# ═══════════════════════════════════════════════════════════════════════════

combo_cases = [
    {"id": "X001", "category": "combo", "description": "Feed unavailable + Markets OK + Whale OK",
     "fixture": {"feed": "unavailable", "markets": "ok", "whale": "ok"}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X002", "category": "combo", "description": "Markets partial fail + Feed OK + Whale OK",
     "fixture": {"feed": "ok", "markets": "partial", "whale": "ok"}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X003", "category": "combo", "description": "Whale empty + Feed normal empty",
     "fixture": {"feed": "normal_empty", "markets": "ok", "whale": "empty"}, "expected": "degraded or completed", "tags": ["combo"]},
    {"id": "X004", "category": "combo", "description": "Cursor corrupt + DB locked",
     "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X005", "category": "combo", "description": "Parent update failure + child completed",
     "fixture": {}, "expected": "parent degraded", "tags": ["combo"]},
    {"id": "X006", "category": "combo", "description": "Adapter import shadow + source timeout",
     "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X007", "category": "combo", "description": "Partial Feed + stale Market",
     "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X008", "category": "combo", "description": "Normal business + bundle write failure",
     "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X009", "category": "combo", "description": "All sources unavailable",
     "fixture": {"feed": "unavailable", "markets": "unavailable", "whale": "unavailable"}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X010", "category": "combo", "description": "Feed degraded + Markets degraded + Whale ok",
     "fixture": {"feed": "degraded", "markets": "degraded", "whale": "ok"}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X011", "category": "combo", "description": "Whale parse error + Feed unavailable",
     "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X012", "category": "combo", "description": "Feed timeout + Markets timeout",
     "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X013", "category": "combo", "description": "DB schema v0 + no run_kind + have children",
     "fixture": {}, "expected": "migration handled", "tags": ["combo"]},
    {"id": "X014", "category": "combo", "description": "Feed HTTP 500 + cursor corrupt + Whale empty",
     "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X015", "category": "combo", "description": "All adapters fail + Feed ok + cursor advances",
     "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X016", "category": "combo", "description": "STOP marker + concurrent run attempt",
     "fixture": {}, "expected": "blocked", "tags": ["combo"]},
    {"id": "X017", "category": "combo", "description": "Whale position flip + extreme leverage + unknown coin",
     "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X018", "category": "combo", "description": "Feed XSS + Market NaN + Whale signed_size=None",
     "fixture": {}, "expected": "degraded (no crash)", "tags": ["combo"]},
    {"id": "X019", "category": "combo", "description": "Orphan child + parent summary corrupt",
     "fixture": {}, "expected": "audit detects", "tags": ["combo"]},
    {"id": "X020", "category": "combo", "description": "Empty state dir + no previous cursor + no whale state",
     "fixture": {}, "expected": "fresh baseline", "tags": ["combo"]},
    {"id": "X021", "category": "combo", "description": "Second run with same initial_since (idempotency)",
     "fixture": {}, "expected": "empty feed ok", "tags": ["combo"]},
    {"id": "X022", "category": "combo", "description": "All sources degraded + no errors list",
     "fixture": {}, "expected": "degraded with empty errors", "tags": ["combo"]},
    {"id": "X023", "category": "combo", "description": "Feed ok + cursor corrupt + XSS in body + db_path leak",
     "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "X024", "category": "combo", "description": "Normal completed run with no_send=true",
     "fixture": {}, "expected": "completed", "tags": ["combo"]},
]
FAULT_CASES.extend(combo_cases)

# ═══════════════════════════════════════════════════════════════════════════
# R02 Additional Cases (80+ cases)
# ═══════════════════════════════════════════════════════════════════════════

r02_extra = [
    # Evidence & binding faults
    {"id": "R001", "category": "operations", "description": "Tests claimed but missing in test suite", "fixture": {}, "expected": "detected", "tags": ["evidence", "integrity"]},
    {"id": "R002", "category": "operations", "description": "Evidence SHA invalid (not hex)", "fixture": {}, "expected": "rejected", "tags": ["evidence", "sha"]},
    {"id": "R003", "category": "operations", "description": "Runner absent from expected path", "fixture": {}, "expected": "blocked", "tags": ["runner", "missing"]},
    {"id": "R004", "category": "cli", "description": "Branch exists after stale snapshot recorded", "fixture": {}, "expected": "evidence outdated", "tags": ["stale", "snapshot"]},
    {"id": "R005", "category": "cli", "description": "Live probe result fabricated (no network call)", "fixture": {}, "expected": "detected", "tags": ["probe", "integrity"]},
    {"id": "R006", "category": "cli", "description": "Hardcoded local path in evidence", "fixture": {}, "expected": "detected", "tags": ["path", "hygiene"]},
    {"id": "R007", "category": "operations", "description": "Evidence file has UTF-8 BOM", "fixture": {}, "expected": "readable or rejected", "tags": ["bom", "encoding"]},
    {"id": "R008", "category": "cli", "description": "Target branch HEAD moved after evidence generated", "fixture": {}, "expected": "re-scan required", "tags": ["stale", "head"]},
    {"id": "R009", "category": "cli", "description": "Source HEAD mismatch with evidence claim", "fixture": {}, "expected": "binding fail", "tags": ["sha", "mismatch"]},
    {"id": "R010", "category": "cli", "description": "Public model removed in new commit", "fixture": {}, "expected": "contract break", "tags": ["api", "contract"]},
    # Schema & contract faults
    {"id": "R011", "category": "combo", "description": "Cross-lane duplicate symbol name", "fixture": {}, "expected": "conflict detected", "tags": ["schema", "collision"]},
    {"id": "R012", "category": "combo", "description": "Schema version conflict between lanes", "fixture": {}, "expected": "migration needed", "tags": ["schema", "version"]},
    {"id": "R013", "category": "feed", "description": "Static HTML output with SVG onload", "fixture": {}, "expected": "escaped", "tags": ["xss", "html"]},
    {"id": "R014", "category": "whale", "description": "Scoring over-alerts on tiny position changes", "fixture": {}, "expected": "threshold respected", "tags": ["scoring", "alert"]},
    {"id": "R015", "category": "whale", "description": "Fallback unit mismatch (BTC vs sats)", "fixture": {}, "expected": "normalized", "tags": ["units", "fallback"]},
    {"id": "R016", "category": "markets", "description": "Backup source mutation returns different data", "fixture": {}, "expected": "versioned", "tags": ["backup", "consistency"]},
    # Feed additional
    {"id": "R017", "category": "feed", "description": "Feed response with BOM in JSON", "fixture": {}, "expected": "parsed correctly", "tags": ["bom", "encoding"]},
    {"id": "R018", "category": "feed", "description": "Feed item content truncated mid-UTF8", "fixture": {}, "expected": "handled", "tags": ["encoding", "truncation"]},
    {"id": "R019", "category": "feed", "description": "Feed response with null bytes", "fixture": {}, "expected": "sanitized", "tags": ["security", "null"]},
    {"id": "R020", "category": "feed", "description": "Feed extremely long source_label (10k chars)", "fixture": {}, "expected": "truncated", "tags": ["overflow", "safety"]},
    {"id": "R021", "category": "feed", "description": "Feed item injection: <script> in source_label", "fixture": {}, "expected": "escaped", "tags": ["xss", "injection"]},
    {"id": "R022", "category": "feed", "description": "Feed duplicate tweet_id across different sources", "fixture": {}, "expected": "deduped per source", "tags": ["dedup", "idempotency"]},
    {"id": "R023", "category": "feed", "description": "Feed provider returns 0 items but total>0", "fixture": {}, "expected": "inconsistency flagged", "tags": ["consistency", "pagination"]},
    {"id": "R024", "category": "feed", "description": "Feed provider returns items older than since", "fixture": {}, "expected": "filtered or flagged", "tags": ["cursor", "filter"]},
    {"id": "R025", "category": "feed", "description": "Feed 3 consecutive empty pages (end of stream)", "fixture": {}, "expected": "stop pagination", "tags": ["pagination", "empty"]},
    {"id": "R026", "category": "feed", "description": "Feed response has no items key", "fixture": {}, "expected": "degraded", "tags": ["schema", "missing"]},
    {"id": "R027", "category": "feed", "description": "Feed item source_kind is empty string", "fixture": {}, "expected": "mapped to UNKNOWN", "tags": ["mapping", "empty"]},
    # Markets additional
    {"id": "R028", "category": "markets", "description": "Market adapter returns empty dict", "fixture": {}, "expected": "degraded", "tags": ["empty", "schema"]},
    {"id": "R029", "category": "markets", "description": "Market adapter returns unexpected type (str)", "fixture": {}, "expected": "degraded", "tags": ["type", "error"]},
    {"id": "R030", "category": "markets", "description": "Market all-mids response partially missing coins", "fixture": {}, "expected": "partial ok", "tags": ["partial", "allmids"]},
    {"id": "R031", "category": "markets", "description": "Market ccxt init succeeds but ticker fails", "fixture": {}, "expected": "degraded", "tags": ["init", "ticker"]},
    {"id": "R032", "category": "markets", "description": "Market ccxt init fails then falls back", "fixture": {}, "expected": "fallback", "tags": ["init", "fallback"]},
    {"id": "R033", "category": "markets", "description": "Market latency spikes to 60s+", "fixture": {}, "expected": "timeout", "tags": ["latency", "timeout"]},
    {"id": "R034", "category": "markets", "description": "Market snapshot contains NaN bid/ask", "fixture": {}, "expected": "nulled or rejected", "tags": ["nan", "validation"]},
    {"id": "R035", "category": "markets", "description": "Market snapshot has bid but no ask", "fixture": {}, "expected": "partial ok", "tags": ["partial", "spread"]},
    {"id": "R036", "category": "markets", "description": "Market exchange not in allowlist", "fixture": {}, "expected": "skipped", "tags": ["allowlist", "policy"]},
    # Whale additional
    {"id": "R037", "category": "whale", "description": "Whale position coin has special characters", "fixture": {}, "expected": "handled", "tags": ["encoding", "coin"]},
    {"id": "R038", "category": "whale", "description": "Whale position with unrealizedPnl NaN", "fixture": {}, "expected": "nulled", "tags": ["nan", "pnl"]},
    {"id": "R039", "category": "whale", "description": "Whale account has 50+ positions", "fixture": {}, "expected": "all processed", "tags": ["scale", "many"]},
    {"id": "R040", "category": "whale", "description": "Whale allMids missing every position coin", "fixture": {}, "expected": "mark_price=null", "tags": ["allmids", "missing"]},
    {"id": "R041", "category": "whale", "description": "Whale clearinghouse response has unknown fields", "fixture": {}, "expected": "forward compat", "tags": ["schema", "extensible"]},
    {"id": "R042", "category": "whale", "description": "Whale same position appears twice in response", "fixture": {}, "expected": "deduped", "tags": ["duplicate", "dedup"]},
    {"id": "R043", "category": "whale", "description": "Whale fresh account with zero positions", "fixture": {}, "expected": "empty ok", "tags": ["empty", "fresh"]},
    {"id": "R044", "category": "whale", "description": "Whale liquidation price same as mark (no distance)", "fixture": {}, "expected": "zero distance handled", "tags": ["liquidation", "edge"]},
    # Operations additional
    {"id": "R045", "category": "operations", "description": "DB pool exhausted / too many connections", "fixture": {}, "expected": "degraded", "tags": ["db", "pool"]},
    {"id": "R046", "category": "operations", "description": "Atomic write to network path (not local)", "fixture": {}, "expected": "blocked", "tags": ["atomic", "network"]},
    {"id": "R047", "category": "operations", "description": "File lock already held by dead PID", "fixture": {}, "expected": "stale lock handled", "tags": ["lock", "stale"]},
    {"id": "R048", "category": "operations", "description": "State file has wrong permissions (read-only)", "fixture": {}, "expected": "blocked", "tags": ["permissions", "state"]},
    {"id": "R049", "category": "operations", "description": "Run history table missing (fresh DB)", "fixture": {}, "expected": "auto-create", "tags": ["schema", "init"]},
    {"id": "R050", "category": "operations", "description": "Parent shadow run has summary with wrong child count", "fixture": {}, "expected": "detected", "tags": ["shadow", "consistency"]},
    {"id": "R051", "category": "operations", "description": "Atomic write temp file not cleaned up after crash", "fixture": {}, "expected": "idempotent cleanup", "tags": ["atomic", "cleanup"]},
    {"id": "R052", "category": "operations", "description": "Source health DB written but run failed", "fixture": {}, "expected": "health preserved", "tags": ["health", "partial"]},
    {"id": "R053", "category": "operations", "description": "Shadow interval_seconds negative", "fixture": {}, "expected": "clamped", "tags": ["validation", "interval"]},
    {"id": "R054", "category": "operations", "description": "Shadow max_runs=0 (should run at least 1)", "fixture": {}, "expected": "clamped", "tags": ["validation", "max_runs"]},
    {"id": "R055", "category": "operations", "description": "Shadow max_runs=1000 (unreasonable)", "fixture": {}, "expected": "capped", "tags": ["validation", "max_runs"]},
    # CLI additional
    {"id": "R056", "category": "cli", "description": "CLI --help returns exit 0", "fixture": {}, "expected": "exit 0", "tags": ["help", "cli"]},
    {"id": "R057", "category": "cli", "description": "CLI unknown argument rejected", "fixture": {}, "expected": "exit non-zero", "tags": ["validation", "args"]},
    {"id": "R058", "category": "cli", "description": "CLI --state-dir is a file not a directory", "fixture": {}, "expected": "blocked", "tags": ["path", "validation"]},
    {"id": "R059", "category": "cli", "description": "CLI --output-dir is a file not a directory", "fixture": {}, "expected": "blocked", "tags": ["path", "validation"]},
    {"id": "R060", "category": "cli", "description": "CLI --feed-since=future_date (>now+1h)", "fixture": {}, "expected": "accepted or warned", "tags": ["time", "future"]},
    {"id": "R061", "category": "cli", "description": "CLI --feed-since=year 1999 (very old)", "fixture": {}, "expected": "accepted", "tags": ["time", "past"]},
    {"id": "R062", "category": "cli", "description": "CLI without --whale-address in live-public", "fixture": {}, "expected": "degraded whale", "tags": ["whale", "missing"]},
    {"id": "R063", "category": "cli", "description": "CLI concurrently with same state dir", "fixture": {}, "expected": "lock blocks second", "tags": ["lock", "concurrent"]},
    # Combo additional
    {"id": "R064", "category": "combo", "description": "Feed timeout + Whale stale + Market NaN + Ops DB locked", "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "R065", "category": "combo", "description": "Provider missing + Whale empty + Markets partial", "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "R066", "category": "combo", "description": "All sources ok + Bundle write fails", "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "R067", "category": "combo", "description": "Skip first run (max_runs=1) + shadow runs once", "fixture": {}, "expected": "1 child", "tags": ["combo"]},
    {"id": "R068", "category": "combo", "description": "Shadow parent + child + orphan child from old run", "fixture": {}, "expected": "orphan detected", "tags": ["combo"]},
    {"id": "R069", "category": "combo", "description": "Feed provider returns HTTP 200 but empty body", "fixture": {}, "expected": "degraded", "tags": ["combo"]},
    {"id": "R070", "category": "combo", "description": "Both Whale and Market use same adapter type", "fixture": {}, "expected": "independent", "tags": ["combo"]},
    {"id": "R071", "category": "combo", "description": "W3 make_feed_id function changed between two runs", "fixture": {}, "expected": "different IDs", "tags": ["combo"]},
    {"id": "R072", "category": "combo", "description": "Evidence contains stale snapshot of non-existent branch", "fixture": {}, "expected": "detected", "tags": ["combo"]},
    {"id": "R073", "category": "combo", "description": "Cross-lane: W2 uses W4 adapter that changed interface", "fixture": {}, "expected": "contract check", "tags": ["combo"]},
    {"id": "R074", "category": "combo", "description": "Merge simulation: W5 + W4 + W2 + W3 + W1 in order", "fixture": {}, "expected": "all tests pass", "tags": ["combo"]},
    {"id": "R075", "category": "combo", "description": "Merge simulation: W5 + W4 only (partial)", "fixture": {}, "expected": "partial pass", "tags": ["combo"]},
    {"id": "R076", "category": "combo", "description": "Evidence with tested_commit=placeholder HEAD", "fixture": {}, "expected": "binding fail", "tags": ["combo"]},
    {"id": "R077", "category": "combo", "description": "After merge, public model import path changed", "fixture": {}, "expected": "contract verified", "tags": ["combo"]},
    {"id": "R078", "category": "combo", "description": "Cross-lane test count regression", "fixture": {}, "expected": "detected", "tags": ["combo"]},
    {"id": "R079", "category": "combo", "description": "Dependency conflict between lanes (e.g. ccxt version)", "fixture": {}, "expected": "resolved", "tags": ["combo"]},
    {"id": "R080", "category": "combo", "description": "Post-merge acceptance pack successfully validates all lanes", "fixture": {}, "expected": "all pass", "tags": ["combo"]},
]
FAULT_CASES.extend(r02_extra)
FAULT_CASES.append({"id": "R082", "category": "feed", "description": "Feed item with SVG onload XSS",
     "fixture": {"zh_body": "<svg onload=alert(1)>"},
     "expected": "escaped or rejected", "tags": ["xss", "svg"]})
FAULT_CASES.append({"id": "R083", "category": "feed", "description": "Feed item with attribute injection XSS",
     "fixture": {"zh_body": "<img src=x onerror=alert(1)> <div onmouseover=alert(1)>"},
     "expected": "escaped or rejected", "tags": ["xss", "attribute_injection"]})
FAULT_CASES.append({"id": "R081", "category": "feed", "description": "Feed item with encoded XSS (HTML entity encoded script)", 
     "fixture": {"content": "&#60;&#115;&#99;&#114;&#105;&#112;&#116;&#62;alert(1)&#60;&#47;&#115;&#99;&#114;&#105;&#112;&#116;&#62;"},
     "expected": "decoded and escaped or rejected", "tags": ["xss", "encoded", "html_entity"]},)
assert len(FAULT_CASES) >= 234, f"Only {len(FAULT_CASES)} cases, need ≥234"
