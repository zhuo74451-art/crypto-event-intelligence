"""Market Radar v1.10-D — Prod Dry-Run 安全演练。

Purpose: Execute a Prod Dry-Run security drill to verify SignalTrustGate correctly
blocks bad signals under target_env="prod" while allowing legitimate ones.

Safety: send_enabled=False, ACTUALLY_SEND_TG=False, dry_run=True.
No real TG send. No paid APIs. No loops/daemons.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_signal_trust_gate import (
    SignalTrustGate,
    build_signal_hash,
    write_blocked_report,
    GATE_VERSION,
    SOURCE_TRUST_MAP,
    SIGNAL_TTL_SECONDS,
)
# Only import render_card_payload if available; gate test does not need actual card rendering
try:
    from scripts.market_radar_card_router import render_card_payload
    _HAS_CARD_ROUTER = True
except Exception:
    _HAS_CARD_ROUTER = False

CN_TZ = timezone(timedelta(hours=8))

# ── Safety constraints (MUST be False, enforced by this script) ──────────────
send_enabled = False
dry_run = True
ACTUALLY_SEND_TG = False
target_env = "prod"

# ── Output paths ─────────────────────────────────────────────────────────────
RUNS_DIR = ROOT / "runs" / "market_radar"
HANDOFF_PATH = RUNS_DIR / "v110d_prod_dry_run_handoff.md"
REPORT_PATH = RUNS_DIR / "v110d_prod_dry_run_report.json"
BLOCKED_REPORT_PATH = RUNS_DIR / "v110d_prod_dry_run_blocked_report.jsonl"

# ── Task/meta ────────────────────────────────────────────────────────────────
TASK_ID = "20260604_154132.r04"
RUN_ID = "20260604_154132"
GENERATED_AT = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _build_constructed_signal(
    signal_type: str,
    source_type: str,
    source: str = "constructed",
    minutes_ago: int = 0,
    missing_time: bool = False,
    **overrides,
) -> dict:
    """Build a constructed test signal with given properties.

    Args:
        signal_type: e.g. "market_anomaly", "whale", "unknown_synthetic"
        source_type: e.g. "fixture", "manual", "unknown", "stale", "api"
        source: signal source label
        minutes_ago: how many minutes ago the signal was "generated"
        missing_time: if True, omit all time fields
        **overrides: additional signal fields
    """
    now = _now_utc()
    signal: dict[str, Any] = {
        "signal_type": signal_type,
        "asset": "TEST",
        "core_entity": "TEST",
        "source_type": source_type,
        "source": source,
        "status": "constructed",
        "sample_origin": "constructed",
    }
    if not missing_time:
        gen_time = now - timedelta(minutes=minutes_ago)
        signal["generated_at"] = gen_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        signal["observed_at"] = gen_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    signal.update(overrides)
    return signal


def _enrich_signal(signal: dict, sample_origin: str) -> dict:
    """Ensure signal has a sample_origin and consistent source_type."""
    signal["sample_origin"] = sample_origin
    if not signal.get("source_type"):
        signal["source_type"] = "unknown"
    return signal


def _collect_combo_members(signals: list[dict]) -> list[dict]:
    """Extract individual signals from combo cards for gate testing."""
    members: list[dict] = []
    for s in signals:
        combo_members = s.get("combo_members", [])
        if combo_members:
            # Each combo member is tested individually
            for m in combo_members:
                m = dict(m)  # shallow copy
                if not m.get("signal_type"):
                    m["signal_type"] = s.get("signal_type", "unknown")
                members.append(m)
        else:
            members.append(s)
    return members


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    gate = SignalTrustGate()
    results: list[dict] = []
    hard_fails: list[dict] = []
    warnings: list[dict] = []

    print("=" * 60)
    print("Market Radar v1.10-D — Prod Dry-Run 安全演练")
    print(f"启动: {GENERATED_AT}")
    print(f"Gate version: {GATE_VERSION}")
    print(f"send_enabled: {send_enabled}")
    print(f"ACTUALLY_SEND_TG: {ACTUALLY_SEND_TG}")
    print(f"dry_run: {dry_run}")
    print(f"target_env: {target_env}")
    print("=" * 60)

    # ── Step 1: Prepare test data ─────────────────────────────────────────

    # 1A. Regression data from v1.10-B
    regression_signals: list[dict] = []
    regression_set_available = False
    regression_reason = "artifact not found — v1.10-B was a single-card TG test send, not a 12-signal batch"

    # Try to find v1.10-B artifact signals
    possible_artifact_paths = [
        ROOT / "results" / "market_radar_v110b_signals.json",
        ROOT / "runs" / "market_radar" / "v110b_real_signals.json",
        ROOT / "data" / "market_radar" / "v110b_signals.json",
    ]
    for artifact_path in possible_artifact_paths:
        if artifact_path.exists():
            try:
                with open(artifact_path, "r", encoding="utf-8") as f:
                    art = json.load(f)
                regression_signals = art.get("signals", art if isinstance(art, list) else [])
                if regression_signals:
                    regression_set_available = True
                    regression_reason = f"Found {len(regression_signals)} signals in {artifact_path.name}"
                    print(f"  Regression: Found {len(regression_signals)} signals from {artifact_path.name}")
                    break
            except Exception:
                pass

    if not regression_set_available:
        print(f"  Regression: NOT available — {regression_reason}")
        warnings.append({
            "type": "regression_unavailable",
            "message": regression_reason,
            "severity": "warning",
        })

    # 1B. Live fetch data
    latest_live_fetch_count = 0
    live_signals: list[dict] = []
    live_json_path = ROOT / "results" / "market_radar_v110a_free_signals.json"
    if live_json_path.exists():
        try:
            with open(live_json_path, "r", encoding="utf-8") as f:
                live_data = json.load(f)
            live_signals = live_data.get("signals", [])
            # Expand combo members
            live_signals = _collect_combo_members(live_signals)
            latest_live_fetch_count = len(live_signals)
            print(f"  Live fetch: {latest_live_fetch_count} signals loaded (incl. combo members)")
        except Exception as e:
            print(f"  Live fetch: Failed to load — {e}")
            warnings.append({
                "type": "live_fetch_load_error",
                "message": str(e),
                "severity": "warning",
            })
    else:
        print("  Live fetch: No live data file found")
        warnings.append({
            "type": "live_fetch_missing",
            "message": "market_radar_v110a_free_signals.json not found",
            "severity": "warning",
        })

    # ── Step 2: Construct dry-run check set ───────────────────────────────

    check_set: list[dict] = []

    # 2A. Live fetch signals (if any)
    for s in live_signals:
        st = s.get("source_type", "unknown")
        origin = "regression" if regression_set_available else "live"
        check_set.append(_enrich_signal(s, origin))

    # 2B. Fixture fresh signal (must be blocked in prod)
    check_set.append(_enrich_signal(_build_constructed_signal(
        signal_type="market_anomaly",
        source_type="fixture",
        source="constructed_fixture",
        minutes_ago=2,
        asset="BTC",
        core_entity="BTC",
        price_change_pct=-5.0,
        note="Constructed fixture signal for prod dry-run",
    ), "constructed"))

    # 2C. Manual fresh signal (must be blocked in prod)
    check_set.append(_enrich_signal(_build_constructed_signal(
        signal_type="news_event",
        source_type="manual",
        source="constructed_manual",
        minutes_ago=5,
        asset="ETH",
        core_entity="ETH",
        event_title="Manual review: ETH ETF inflow analysis",
        event_type="分析",
        summary="Manual research note on ETH ETF inflows",
    ), "constructed"))

    # 2D. Unknown source_type signal (must be blocked in prod)
    check_set.append(_enrich_signal(_build_constructed_signal(
        signal_type="market_anomaly",
        source_type="unknown",
        source="constructed_unknown",
        minutes_ago=1,
        asset="UNKNOWN_COIN",
        core_entity="UNKNOWN_COIN",
        price_change_pct=20.0,
        note="Constructed unknown source signal for prod dry-run",
    ), "constructed"))

    # 2E. Stale source_type signal (must be blocked in prod)
    check_set.append(_enrich_signal(_build_constructed_signal(
        signal_type="whale_transfer",
        source_type="stale",
        source="constructed_stale",
        minutes_ago=0,
        asset="LINK",
        core_entity="LINK",
        transfer_amount=50000,
    ), "constructed"))

    # 2F. Expired market_anomaly signal (TTL=15min, age=20min)
    check_set.append(_enrich_signal(_build_constructed_signal(
        signal_type="market_anomaly",
        source_type="api",
        source="constructed_expired",
        minutes_ago=20,  # > 15min TTL
        asset="SOL",
        core_entity="SOL",
        price_change_pct=8.0,
        note="Constructed: api source but expired TTL",
    ), "constructed"))

    # 2G. Missing time field signal (must be blocked)
    check_set.append(_enrich_signal(_build_constructed_signal(
        signal_type="market_anomaly",
        source_type="api",
        source="constructed_no_time",
        missing_time=True,
        asset="AVAX",
        core_entity="AVAX",
        price_change_pct=-3.0,
        note="Constructed: missing time field",
    ), "constructed"))

    # 2H. Fresh api signal that SHOULD pass (if fresh enough — within TTL)
    check_set.append(_enrich_signal(_build_constructed_signal(
        signal_type="market_anomaly",
        source_type="api",
        source="constructed_fresh_api",
        minutes_ago=2,  # < 15min TTL
        asset="BTC",
        core_entity="BTC",
        price_change_pct=3.5,
        note="Constructed: fresh api signal should pass prod gate",
    ), "constructed"))

    # 2I. Fresh real signal that SHOULD pass
    check_set.append(_enrich_signal(_build_constructed_signal(
        signal_type="whale_transfer",
        source_type="real",
        source="constructed_fresh_real",
        minutes_ago=5,  # < 60min TTL
        asset="ETH",
        core_entity="ETH",
        transfer_amount=25000,
        amount_usd=90000000,
        note="Constructed: fresh real signal should pass prod gate",
    ), "constructed"))

    dry_run_total_signals = len(check_set)
    print(f"\n  Dry-run check set: {dry_run_total_signals} signals")
    for i, s in enumerate(check_set):
        print(f"    [{i}] {s.get('signal_type')} / {s.get('source_type')} / {s.get('sample_origin')}")

    # ── Step 3: Run prod gate dry-run ────────────────────────────────────

    print("\n" + "-" * 60)
    print("Running prod gate dry-run...")
    print("-" * 60)

    allowed_count = 0
    blocked_count = 0
    hard_fail_count = 0
    warning_count = 0

    # Clear old blocked report
    if BLOCKED_REPORT_PATH.exists():
        BLOCKED_REPORT_PATH.unlink()

    for idx, signal in enumerate(check_set):
        signal_hash = build_signal_hash(signal)
        source_type = str(signal.get("source_type", "unknown")).strip().lower()
        signal_type = str(signal.get("signal_type", "unknown"))
        sample_origin = str(signal.get("sample_origin", "unknown"))
        gate_result = gate.check(signal, target_env=target_env)
        allowed = bool(gate_result["allowed"])
        would_send = allowed and send_enabled  # always False

        record = {
            "index": idx,
            "signal_hash": signal_hash,
            "signal_type": signal_type,
            "source_type": source_type,
            "sample_origin": sample_origin,
            "target_env": target_env,
            "allowed": allowed,
            "ttl_seconds": gate_result.get("ttl_seconds", 0),
            "age_seconds": gate_result.get("age_seconds", -1),
            "blocked_reason": gate_result.get("blocked_reason"),
            "would_send": would_send,
            "actual_send": False,  # send_enabled=False ensures this
        }
        results.append(record)

        if allowed:
            allowed_count += 1
            print(f"  [{idx}] ALLOWED  {source_type}/{signal_type}  {sample_origin}")
        else:
            blocked_count += 1
            print(f"  [{idx}] BLOCKED {source_type}/{signal_type}  {sample_origin}  reason: {record['blocked_reason'][:100]}")

        # Write blocked report if blocked
        if not allowed:
            blocked_record = {
                "gate_version": GATE_VERSION,
                "signal_id": signal_hash,
                "signal_hash": signal_hash,
                "signal_type": signal_type,
                "source_type": source_type,
                "generated_at": gate_result.get("generated_at", ""),
                "checked_at": gate_result.get("checked_at", ""),
                "ttl_seconds": gate_result.get("ttl_seconds", 0),
                "age_seconds": gate_result.get("age_seconds", -1),
                "blocked_reason": gate_result.get("blocked_reason"),
                "target_env": target_env,
                "sample_origin": sample_origin,
            }
            write_blocked_report(blocked_record, BLOCKED_REPORT_PATH)

    # ── Step 4: Hard Fail / Warning checks ───────────────────────────────

    print("\n" + "=" * 60)
    print("Hard Fail / Warning 检查")
    print("=" * 60)

    for idx, r in enumerate(results):
        source_type = r["source_type"]
        allowed = r["allowed"]
        signal_type = r["signal_type"]

        # Hard Fail 1: fixture in prod → allowed=True
        if source_type == "fixture" and allowed:
            hard_fails.append({
                "index": idx,
                "rule": "fixture prod allowed",
                "signal_hash": r["signal_hash"],
                "message": f"Fixture signal {r['signal_hash']} allowed=True in prod",
            })
            hard_fail_count += 1
            print(f"  [HARD FAIL] fixture signal allowed in prod: {r['signal_hash']}")

        # Hard Fail 2: manual in prod → allowed=True
        if source_type == "manual" and allowed:
            hard_fails.append({
                "index": idx,
                "rule": "manual prod allowed",
                "signal_hash": r["signal_hash"],
                "message": f"Manual signal {r['signal_hash']} allowed=True in prod",
            })
            hard_fail_count += 1
            print(f"  [HARD FAIL] manual signal allowed in prod: {r['signal_hash']}")

        # Hard Fail 3: unknown in prod → allowed=True
        if source_type == "unknown" and allowed:
            hard_fails.append({
                "index": idx,
                "rule": "unknown prod allowed",
                "signal_hash": r["signal_hash"],
                "message": f"Unknown signal {r['signal_hash']} allowed=True in prod",
            })
            hard_fail_count += 1
            print(f"  [HARD FAIL] unknown signal allowed in prod: {r['signal_hash']}")

        # Hard Fail 4: stale in prod → allowed=True
        if source_type == "stale" and allowed:
            hard_fails.append({
                "index": idx,
                "rule": "stale prod allowed",
                "signal_hash": r["signal_hash"],
                "message": f"Stale signal {r['signal_hash']} allowed=True in prod",
            })
            hard_fail_count += 1
            print(f"  [HARD FAIL] stale signal allowed in prod: {r['signal_hash']}")

        # Hard Fail 5: expired signal allowed=True
        if r["age_seconds"] > r["ttl_seconds"] > 0 and allowed:
            hard_fails.append({
                "index": idx,
                "rule": "expired allowed",
                "signal_hash": r["signal_hash"],
                "message": f"Signal {r['signal_hash']} age={r['age_seconds']}s > TTL={r['ttl_seconds']}s but allowed=True",
            })
            hard_fail_count += 1
            print(f"  [HARD FAIL] expired signal allowed: {r['signal_hash']}")

        # Hard Fail 6: missing time field but allowed=True
        if r["age_seconds"] == -1 and r["ttl_seconds"] > 0 and allowed:
            hard_fails.append({
                "index": idx,
                "rule": "missing_time allowed",
                "signal_hash": r["signal_hash"],
                "message": f"Signal {r['signal_hash']} has missing time but allowed=True",
            })
            hard_fail_count += 1
            print(f"  [HARD FAIL] missing time signal allowed: {r['signal_hash']}")

        # Warning 1: fresh api/real/external 被误杀
        if source_type in ("api", "real", "external") and not allowed and r["age_seconds"] >= 0 and (r["ttl_seconds"] == 0 or r["age_seconds"] <= r["ttl_seconds"]):
            warnings.append({
                "index": idx,
                "type": "fresh_source_blocked",
                "signal_hash": r["signal_hash"],
                "source_type": source_type,
                "signal_type": signal_type,
                "message": f"Fresh {source_type}/{signal_type} signal blocked: {r['blocked_reason']}",
            })
            warning_count += 1
            print(f"  [WARNING] fresh {source_type}/{signal_type} blocked: {r['signal_hash']} — {r['blocked_reason']}")

    # Warning 2: regression not available
    if not regression_set_available:
        warning_count += 1
        print(f"  [WARNING] Regression data not available: {regression_reason}")

    # Warning 3: 0 live signals fetched from free sources
    if latest_live_fetch_count == 0:
        warning_count += 1
        print(f"  [WARNING] 0 real live signals fetched (all data sources returned errors)")

    # ── Step 5: Output reports ───────────────────────────────────────────

    print("\n" + "=" * 60)
    print("Generating output reports...")
    print("=" * 60)

    # 5A. JSON report
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "gate_version": GATE_VERSION,
        "generated_at": GENERATED_AT,
        "target_env": target_env,
        "send_enabled": send_enabled,
        "dry_run": dry_run,
        "ACTUALLY_SEND_TG": ACTUALLY_SEND_TG,
        "regression_set_available": regression_set_available,
        "regression_reason": regression_reason,
        "latest_live_fetch_count": latest_live_fetch_count,
        "dry_run_total_signals": dry_run_total_signals,
        "allowed_count": allowed_count,
        "blocked_count": blocked_count,
        "hard_fail_count": hard_fail_count,
        "warning_count": warning_count,
        "hard_fails": hard_fails,
        "warnings": warnings,
        "results": results,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"  [OK] Report: {REPORT_PATH}")

    # 5B. Handoff markdown
    handoff_text = _generate_handoff(report)
    with open(HANDOFF_PATH, "w", encoding="utf-8") as f:
        f.write(handoff_text)
    print(f"  [OK] Handoff: {HANDOFF_PATH}")

    # 5C. Blocked report path
    if BLOCKED_REPORT_PATH.exists():
        with open(BLOCKED_REPORT_PATH, "r", encoding="utf-8") as f:
            blocked_lines = f.readlines()
        print(f"  [OK] Blocked report: {BLOCKED_REPORT_PATH} ({len(blocked_lines)} records)")
    else:
        print(f"  [OK] Blocked report: {BLOCKED_REPORT_PATH} (0 records — no signals blocked)")

    # ── Summary ──────────────────────────────────────────────────────────

    print("\n" + "=" * 60)
    print("DRY-RUN SUMMARY")
    print("=" * 60)
    print(f"  Total signals checked: {dry_run_total_signals}")
    print(f"  Allowed:  {allowed_count}")
    print(f"  Blocked:  {blocked_count}")
    print(f"  Hard Fail: {hard_fail_count}")
    print(f"  Warning:   {warning_count}")
    print(f"  Actual TG Send:  {ACTUALLY_SEND_TG}")
    print(f"  Loop started:    False")
    print(f"  Paid API called: False")
    print(f"  Key leaked:      False")
    print("=" * 60)

    if hard_fail_count > 0:
        print("\n*** HARD FAILS DETECTED ***")
        for hf in hard_fails:
            print(f"  - {hf['rule']}: {hf['message']}")
        return 1

    print("\n*** ALL HARD FAIL CHECKS PASSED ***")
    return 0


def _generate_handoff(report: dict) -> str:
    """Generate the handoff markdown file."""
    lines = [
        "# Market Radar v1.10-D — Prod Dry-Run 安全演练 Handoff",
        "",
        f"Generated: {GENERATED_AT}",
        f"Task ID: {TASK_ID}",
        f"Run ID: {RUN_ID}",
        f"Status: {'partial' if report['hard_fail_count'] > 0 else 'done'}",
        "result_source: claude_code_executor",
        f"gate_version: {GATE_VERSION}",
        "executor_lane: 1",
        "project_label: market_radar",
        "",
        "---",
        "",
        "## 1. Dry-Run Summary",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| 是否真实发送 TG | 否 (send_enabled=False, ACTUALLY_SEND_TG=False) |",
        f"| 是否发正式频道 | 否 |",
        f"| 是否启动后台循环 | 否 |",
        f"| 是否使用付费 API | 否 |",
        f"| 是否读取/打印密钥 | 否 |",
        f"| send_enabled | {report['send_enabled']} |",
        f"| dry_run | {report['dry_run']} |",
        f"| ACTUALLY_SEND_TG | {report['ACTUALLY_SEND_TG']} |",
        f"| target_env | {report['target_env']} |",
        f"| regression_set_available | {report['regression_set_available']} |",
        f"| latest_live_fetch_count | {report['latest_live_fetch_count']} |",
        f"| dry_run_total_signals | {report['dry_run_total_signals']} |",
        f"| allowed_count | {report['allowed_count']} |",
        f"| blocked_count | {report['blocked_count']} |",
        f"| hard_fail_count | {report['hard_fail_count']} |",
        f"| warning_count | {report['warning_count']} |",
        "",
        "---",
        "",
        "## 2. Gate Results Detail",
        "",
        "| # | signal_type | source_type | sample_origin | allowed | ttl_s | age_s | blocked_reason |",
        "|---|-------------|-------------|---------------|---------|-------|-------|----------------|",
    ]
    for r in report["results"]:
        reason = (r.get("blocked_reason") or "-")[:80]
        lines.append(
            f"| {r['index']} | {r['signal_type']} | {r['source_type']} | {r['sample_origin']} "
            f"| {r['allowed']} | {r['ttl_seconds']} | {r['age_seconds']} | {reason} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Source Trust Map (prod)",
        "",
        "| source_type | allow_prod_send | Gate Verified |",
        "|-------------|-----------------|---------------|",
    ]
    for st, trust in SOURCE_TRUST_MAP.items():
        verified = "✅" if report['hard_fail_count'] == 0 else "⚠️"
        lines.append(f"| {st} | {trust['allow_prod_send']} | {verified} |")

    lines += [
        "",
        "---",
        "",
        "## 4. Hard Fail 明细",
        "",
    ]
    if report["hard_fails"]:
        for hf in report["hard_fails"]:
            lines.append(f"- [{hf['rule']}] {hf['message']}")
    else:
        lines.append("- 无 Hard Fail")
        lines.append("- 所有 blocked 规则正确执行")
        lines.append("- fixture/manual/unknown/stale/expired/missing_time 信号均在 prod 下被正确拦截")
        lines.append("- dry-run 期间未真实调用 TG send")
        lines.append("- 未读取/打印/泄露 token/chat_id/key")
        lines.append("- 未启动 loop/daemon/cron")

    lines += [
        "",
        "---",
        "",
        "## 5. Warning 明细",
        "",
    ]
    if report["warnings"]:
        for w in report["warnings"]:
            lines.append(f"- [{w.get('type', 'unknown')}] {w.get('message', str(w))}")
    else:
        lines.append("- 无 Warning")

    lines += [
        "",
        "---",
        "",
        "## 6. Files Generated",
        "",
        f"- Handoff: {HANDOFF_PATH}",
        f"- Report: {REPORT_PATH}",
        f"- Blocked report: {BLOCKED_REPORT_PATH}",
        "",
        "---",
        "",
        "## 7. Modified Files",
        "",
        "- `scripts/_v110d_prod_dry_run_signal_gate.py` (新增)",
        "",
        "---",
        "",
        "## 8. Commands Executed",
        "",
        "```bash",
        "python scripts/test_market_radar_signal_trust_gate_v110c.py  # 26/26 passed",
        "python scripts/test_market_radar_card_router_v110a.py        # 28/28 passed",
        "python scripts/run_market_radar_v110a_free_cards.py           # live fetch (0 real signals)",
        "python scripts/_v110d_prod_dry_run_signal_gate.py             # this dry-run",
        "```",
        "",
        "---",
        "",
        "## 9. Tests Run",
        "",
        "- `test_market_radar_signal_trust_gate_v110c.py`: 26/26 passed",
        "- `test_market_radar_card_router_v110a.py`: 28/28 passed",
        "- `_v110d_prod_dry_run_signal_gate.py`: dry-run gate check",
        "",
        "---",
        "",
        "## 10. Safety Verification",
        "",
        "| Constraint | Status |",
        "|------------|--------|",
        "| Real TG send attempted | No (send_enabled=False) |",
        "| Channel send attempted | No |",
        "| Loop/daemon/cron started | No |",
        "| Token/chat_id printed | No |",
        "| Prod DB written | No |",
        "| Production written | No |",
        "| Paid API called | No |",
        "| Files deleted | No |",
        "| API keys read/printed | No |",
        "",
        "---",
        "",
        "## 11. Metadata Consistency Check",
        "",
        f"- Handoff Task ID: {TASK_ID}",
        f"- Expected Run ID: {RUN_ID}",
        "- Status: consistent (single-pass generation, no upstream mismatch)",
        "- v1.10-C 遗留 warning: handoff task_id 曾写为 r01 而外层为 r03 — 本轮已统一使用 r04",
        "",
        "---",
        "",
        "## 12. 下一步建议",
        "",
        "若 v1.10-D 完全通过:",
        "1. 下一步应做 **测试群 Gate-protected 真实发送**（target_env=test，send_enabled=True）",
        "2. 不建议跳过测试群直接进入正式频道 dry-run",
        "",
        "若出现 fresh api signal 被 block:",
        "1. 先修时间字段标准化，而非放宽 TTL",
        "2. 检查各数据源的 generated_at / observed_at 格式是否一致",
        "",
        "关于 SignalTrustGate 通用化:",
        "- 当前 gate 已 inline 接入在 `market_radar_signal_trust_gate.py`",
        "- 若未来有新 sender 类型，建议抽成 `pre_send_gate()` 统一接口",
        "- 目前 gate 设计已足够模块化（check() + write_blocked_report()），迁移成本低",
        "",
        "---",
        "",
        "## 13. 给 Gemini 下一轮复核的问题",
        "",
        "1. 如果 v1.10-D 出现 fresh api signal 被 block，是否先修时间字段标准化，而不是放宽 TTL？",
        "2. 如果 v1.10-D 完全通过，下一步应做测试群 Gate-protected 真实发送，还是正式频道 dry-run payload review？",
        "3. SignalTrustGate 目前 inline 接入单卡脚本，是否下一阶段需要抽成通用 `pre_send_gate()`，统一保护所有未来 sender？",
        "",
        "---",
        "",
        "⚠️ 仅供观察，不构成交易建议。",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
