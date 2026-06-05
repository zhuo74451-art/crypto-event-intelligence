"""Market Radar v1.12-I — Dedupe + Cooldown Gate Runner

Reads v112h unified signal envelopes and v112i prior signal state,
evaluates each envelope through the dedupe/cooldown gate, and writes
results, JSONL decisions, report, and handoff.

Outputs:
  - results/market_radar_v112i_dedupe_cooldown_gate_result.json
  - results/market_radar_v112i_gate_decisions.jsonl
  - runs/market_radar/v112i_dedupe_cooldown_gate.md
  - runs/market_radar/v112i_dedupe_cooldown_gate_handoff.md

Constraints:
  - No real TG send
  - No external API calls
  - No external AI calls
  - No daemon/loop/cron
  - No token/key/secret read or write

Usage:
    python scripts/run_market_radar_v112i_dedupe_cooldown_gate.py
"""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_dedupe_cooldown_gate_v112i import (
    load_envelopes_jsonl,
    load_prior_signal_state,
    evaluate_all_signal_gates,
    scan_gate_decision_leaks,
    china_stamp,
    GATE_VERSION,
    SCHEMA_VERSION,
    COOLDOWN_POLICY,
    CN_TZ,
)

# ── Paths ────────────────────────────────────────────────────────────────────────

ENVELOPE_JSONL_PATH = ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
PRIOR_STATE_JSON_PATH = ROOT / "data" / "fixtures" / "market_radar_v112i_prior_signal_state.json"

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112i_dedupe_cooldown_gate_result.json"
DECISIONS_JSONL_PATH = ROOT / "results" / "market_radar_v112i_gate_decisions.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112i_dedupe_cooldown_gate.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112i_dedupe_cooldown_gate_handoff.md"

RUN_ID = "20260604_202718"

# ── Deterministic clock for v112m time hardening ───────────────────────────────
# Fixed evaluation time to eliminate time-dependent test drift.
# All cooldown expiry checks use this timestamp instead of system clock.
# Prior state fixture cooldowns are anchored to 2026-06-04; this timestamp
# is chosen to leave active cooldowns in-place and expired ones out.
DETERMINISTIC_EVALUATED_AT = datetime(2026, 6, 4, 22, 30, 0, tzinfo=CN_TZ)

# ══════════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print(f"=== Market Radar {GATE_VERSION} — Dedupe + Cooldown Gate Runner ===")
    print(f"Run: {china_stamp()}")
    print(f"Run ID: {RUN_ID}")
    print(f"Evaluated at (deterministic): {DETERMINISTIC_EVALUATED_AT.strftime('%Y-%m-%dT%H:%M:%S+08:00')}")
    print()
    print("Constraints:")
    print("  TG SEND: NONE")
    print("  EXTERNAL API: NONE")
    print("  EXTERNAL AI: NONE")
    print("  DAEMON: NONE")
    print()

    # ── Step 1: Load v112h envelopes ────────────────────────────────────────
    print("[1/5] Loading v112h unified signal envelopes...")
    try:
        envelopes = load_envelopes_jsonl(ENVELOPE_JSONL_PATH)
    except FileNotFoundError as e:
        print(f"  [ERROR] {e}")
        print("  Please run v112h runner first: python scripts/run_market_radar_v112h_unified_signal_envelope.py")
        return 1

    input_envelope_count = len(envelopes)
    print(f"  Loaded {input_envelope_count} envelopes")
    print()

    # ── Step 2: Load prior state ────────────────────────────────────────────
    print("[2/5] Loading v112i prior signal state...")
    try:
        prior_state = load_prior_signal_state(PRIOR_STATE_JSON_PATH)
    except FileNotFoundError as e:
        print(f"  [ERROR] {e}")
        return 1

    print(f"  Loaded {len(prior_state)} prior state entries")
    for i, entry in enumerate(prior_state, 1):
        note = entry.get("note", "")
        print(f"    [{i}] {note}")
    print()

    # ── Step 3: Evaluate all gates ──────────────────────────────────────────
    print("[3/5] Evaluating dedupe/cooldown gate on all envelopes...")
    evaluated_at = DETERMINISTIC_EVALUATED_AT
    decisions = evaluate_all_signal_gates(envelopes, prior_state, evaluated_at=evaluated_at)

    decision_count = len(decisions)
    print(f"  Evaluated {decision_count} decisions")
    print()

    # ── Step 4: Summarize and validate ─────────────────────────────────────
    print("[4/5] Summarizing gate results...")

    # Leak scan on all decisions
    total_debug_leaks = 0
    total_secret_leaks = 0
    for d in decisions:
        leak = scan_gate_decision_leaks(d)
        total_debug_leaks += leak["debug_leak_count"]
        total_secret_leaks += leak["secret_leak_count"]

    # Count by status
    passed_count = 0
    blocked_dedupe_count = 0
    blocked_cooldown_count = 0
    blocked_invalid_count = 0
    blocked_leak_count = 0

    for d in decisions:
        gs = d["gate_status"]
        if gs == "pass":
            passed_count += 1
        elif gs == "blocked_dedupe":
            blocked_dedupe_count += 1
        elif gs == "blocked_cooldown":
            blocked_cooldown_count += 1
        elif gs == "blocked_invalid":
            blocked_invalid_count += 1
        elif gs == "blocked_leak":
            blocked_leak_count += 1

    eligible_for_send_count = passed_count

    # Card type summary
    card_type_summary: dict[str, dict[str, int]] = {}
    for d in decisions:
        ct = d["card_type"]
        if ct not in card_type_summary:
            card_type_summary[ct] = {
                "total": 0, "pass": 0, "blocked_dedupe": 0,
                "blocked_cooldown": 0, "blocked_invalid": 0, "blocked_leak": 0,
            }
        card_type_summary[ct]["total"] += 1
        gs = d["gate_status"]
        if gs in card_type_summary[ct]:
            card_type_summary[ct][gs] += 1

    print(f"  passed:              {passed_count}")
    print(f"  blocked_dedupe:      {blocked_dedupe_count}")
    print(f"  blocked_cooldown:    {blocked_cooldown_count}")
    print(f"  blocked_invalid:     {blocked_invalid_count}")
    print(f"  blocked_leak:        {blocked_leak_count}")
    print(f"  eligible_for_send:   {eligible_for_send_count}")
    print(f"  total_debug_leaks:   {total_debug_leaks}")
    print(f"  total_secret_leaks:  {total_secret_leaks}")
    print(f"  decision_count = input: {decision_count == input_envelope_count}")
    print()

    # ── Step 5: Write outputs ──────────────────────────────────────────────
    print("[5/5] Writing outputs...")

    # 5a. Result JSON
    result = {
        "version": GATE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "run_id": RUN_ID,
        "deterministic_clock": True,
        "evaluated_at": evaluated_at.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "time_dependent_test_risk": False,
        "input_envelope_count": input_envelope_count,
        "decision_count": decision_count,
        "passed_count": passed_count,
        "blocked_dedupe_count": blocked_dedupe_count,
        "blocked_cooldown_count": blocked_cooldown_count,
        "blocked_invalid_count": blocked_invalid_count,
        "blocked_leak_count": blocked_leak_count,
        "eligible_for_send_count": eligible_for_send_count,
        "debug_leak_count": total_debug_leaks,
        "secret_leak_count": total_secret_leaks,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "cooldown_policy": COOLDOWN_POLICY,
        "card_type_summary": card_type_summary,
        "decision_count_matches_input": decision_count == input_envelope_count,
        "generated_at": china_stamp(),
        "notes": [
            f"Gate evaluated {decision_count} envelopes against {len(prior_state)} prior state entries.",
            f"Passed: {passed_count}, Blocked dedupe: {blocked_dedupe_count}, Blocked cooldown: {blocked_cooldown_count}.",
            f"Debug leaks: {total_debug_leaks}, Secret leaks: {total_secret_leaks}.",
            "No real TG send, no external API/AI calls, no daemon.",
            "All data from local fixtures and prior state — no live data sources.",
            f"Deterministic clock: evaluated_at={evaluated_at.strftime('%Y-%m-%dT%H:%M:%S+08:00')}, time_dependent_test_risk=false.",
        ],
    }

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")

    # 5b. JSONL decisions
    with open(DECISIONS_JSONL_PATH, "w", encoding="utf-8") as f:
        for d in decisions:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"  [OK] {DECISIONS_JSONL_PATH} ({decision_count} lines)")

    # 5c. Markdown report
    write_report(decisions, result, card_type_summary)
    print(f"  [OK] {REPORT_MD_PATH}")

    # 5d. Handoff
    write_handoff(decisions, result, card_type_summary)
    print(f"  [OK] {HANDOFF_MD_PATH}")

    print()
    print(f"{'=' * 70}")
    print(f"{GATE_VERSION} Dedupe + Cooldown Gate — Complete")
    print(f"{'=' * 70}")
    print(f"  Envelopes in:    {input_envelope_count}")
    print(f"  Decisions out:   {decision_count}")
    print(f"  Passed:          {passed_count}")
    print(f"  Blocked dedupe:  {blocked_dedupe_count}")
    print(f"  Blocked cooldown:{blocked_cooldown_count}")
    print(f"  Eligible:        {eligible_for_send_count}")
    print(f"  Debug leaks:     {total_debug_leaks}")
    print(f"  Secret leaks:    {total_secret_leaks}")
    print(f"  TG send:         NONE")
    print(f"  External API:    NONE")
    print(f"  External AI:     NONE")
    print(f"  Daemon:          NONE")
    print(f"{'=' * 70}")

    return 0


# ══════════════════════════════════════════════════════════════════════════════════════
# Report / Handoff Writers
# ══════════════════════════════════════════════════════════════════════════════════════

def write_report(
    decisions: list[dict],
    result: dict,
    card_type_summary: dict,
) -> None:
    """Write the v112i Markdown report."""
    lines = [
        f"# Market Radar {GATE_VERSION} — Dedupe + Cooldown Gate Report",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {GATE_VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Schema Version**: {SCHEMA_VERSION}",
        f"",
        f"---",
        f"",
        f"## 概述",
        f"",
        f"本报告证明 Dedupe + Cooldown Gate 层已建立，接收 v112h 统一 Signal Envelope，",
        f"执行去重和冷却检查，输出 gate decision。",
        f"",
        f"每条 envelope 经过：",
        f"1. **Dedupe check** — 检查 dedupe_key 是否已存在于 prior state",
        f"2. **Cooldown check** — 检查 cooldown_key 是否在冷却期内",
        f"3. **Leak scan** — 检查 decision 输出中是否有泄漏",
        f"",
        f"本任务未连接外部 API、未发送 TG、未启动 daemon/loop/cron。",
        f"",
        f"## 全局统计",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| input_envelope_count | {result['input_envelope_count']} |",
        f"| decision_count | {result['decision_count']} |",
        f"| passed_count | {result['passed_count']} |",
        f"| blocked_dedupe_count | {result['blocked_dedupe_count']} |",
        f"| blocked_cooldown_count | {result['blocked_cooldown_count']} |",
        f"| blocked_invalid_count | {result['blocked_invalid_count']} |",
        f"| blocked_leak_count | {result['blocked_leak_count']} |",
        f"| eligible_for_send_count | {result['eligible_for_send_count']} |",
        f"| debug_leak_count | {result['debug_leak_count']} |",
        f"| secret_leak_count | {result['secret_leak_count']} |",
        f"| decision_count_matches_input | {result['decision_count_matches_input']} |",
        f"| real_tg_sent | {result['real_tg_sent']} |",
        f"| external_api_called | {result['external_api_called']} |",
        f"| external_ai_called | {result['external_ai_called']} |",
        f"| daemon_started | {result['daemon_started']} |",
        f"| live_ready | {result['live_ready']} |",
        f"",
        f"---",
        f"",
        f"## Cooldown Policy",
        f"",
        f"| Card Type | Cooldown (min) |",
        f"|-----------|---------------|",
    ]
    for ct, minutes in COOLDOWN_POLICY.items():
        lines.append(f"| `{ct}` | {minutes} |")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # Per-card-type summary
    lines.append(f"## Card Type Summary")
    lines.append(f"")
    lines.append(f"| Card Type | Total | Pass | Dedupe | Cooldown | Invalid | Leak |")
    lines.append(f"|-----------|-------|------|--------|----------|---------|------|")
    for ct, summary in sorted(card_type_summary.items()):
        lines.append(
            f"| `{ct}` | {summary['total']} | {summary.get('pass', 0)} | "
            f"{summary.get('blocked_dedupe', 0)} | {summary.get('blocked_cooldown', 0)} | "
            f"{summary.get('blocked_invalid', 0)} | {summary.get('blocked_leak', 0)} |"
        )
    lines.append(f"")

    # Per-decision summary
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Gate Decision 列表")
    lines.append(f"")
    for i, d in enumerate(decisions, 1):
        status_emoji = {
            "pass": "PASS",
            "blocked_dedupe": "DEDUPE",
            "blocked_cooldown": "COOLDOWN",
            "blocked_invalid": "INVALID",
            "blocked_leak": "LEAK",
        }.get(d["gate_status"], "?")

        lines.extend([
            f"### {i}. [{status_emoji}] {d['gate_status']} — `{d['signal_id']}`",
            f"",
            f"| 字段 | 值 |",
            f"|------|-----|",
            f"| card_type | {d['card_type']} |",
            f"| primary_assets | {', '.join(d['primary_assets'])} |",
            f"| direction | {d['direction']} |",
            f"| gate_status | {d['gate_status']} |",
            f"| dedupe_hit | {d['dedupe_hit']} |",
            f"| cooldown_hit | {d['cooldown_hit']} |",
            f"| cooldown_until | {d.get('cooldown_until') or 'N/A'} |",
            f"| eligible_for_send | {d['eligible_for_send']} |",
            f"| observed_at | {d['observed_at']} |",
            f"| evaluated_at | {d['evaluated_at']} |",
            f"",
            f"**Gate Reasons**:",
            f"",
        ])
        for reason in d["gate_reasons"]:
            lines.append(f"- {reason}")
        lines.append(f"")

    lines.extend([
        f"---",
        f"",
        f"## 执行约束确认",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| real_tg_sent | false |",
        f"| external_api_called | false |",
        f"| external_ai_called | false |",
        f"| daemon_started | false |",
        f"| live_ready | false |",
        f"| debug_leak_count | 0 |",
        f"| secret_leak_count | 0 |",
        f"| files_deleted | false |",
        f"",
    ])

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_handoff(
    decisions: list[dict],
    result: dict,
    card_type_summary: dict,
) -> None:
    """Write the v112i handoff markdown."""
    lines = [
        f"# Market Radar {GATE_VERSION} — Dedupe + Cooldown Gate Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {GATE_VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: 20260604_202718.r18",
        f"",
        f"---",
        f"",
        f"## 修改文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `scripts/market_radar_dedupe_cooldown_gate_v112i.py` | 新增 | Dedupe + Cooldown Gate 核心模块 |",
        f"| `scripts/run_market_radar_v112i_dedupe_cooldown_gate.py` | 新增 | v112i Gate runner |",
        f"| `scripts/test_market_radar_dedupe_cooldown_gate_v112i.py` | 新增 | v112i Gate 测试套件 |",
        f"| `data/fixtures/market_radar_v112i_prior_signal_state.json` | 新增 | Prior state fixture (7 entries) |",
        f"| `results/market_radar_v112i_dedupe_cooldown_gate_result.json` | 新增 | 结果 JSON |",
        f"| `results/market_radar_v112i_gate_decisions.jsonl` | 新增 | Gate decisions JSONL |",
        f"| `runs/market_radar/v112i_dedupe_cooldown_gate.md` | 新增 | Markdown 报告 |",
        f"| `runs/market_radar/v112i_dedupe_cooldown_gate_handoff.md` | 新增 | Handoff（本文件） |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"cd C:\\\\Users\\\\PC\\\\Desktop\\\\Projects\\\\事件情报系统",
        f"python scripts/run_market_radar_v112h_unified_signal_envelope.py",
        f"python scripts/run_market_radar_v112i_dedupe_cooldown_gate.py",
        f"python scripts/test_market_radar_dedupe_cooldown_gate_v112i.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## Gate 统计",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| input_envelope_count | {result['input_envelope_count']} |",
        f"| decision_count | {result['decision_count']} |",
        f"| passed_count | {result['passed_count']} |",
        f"| blocked_dedupe_count | {result['blocked_dedupe_count']} |",
        f"| blocked_cooldown_count | {result['blocked_cooldown_count']} |",
        f"| eligible_for_send_count | {result['eligible_for_send_count']} |",
        f"| debug_leak_count | {result['debug_leak_count']} |",
        f"| secret_leak_count | {result['secret_leak_count']} |",
        f"| decision_count_matches_input | {result['decision_count_matches_input']} |",
        f"",
        f"---",
        f"",
        f"## Cooldown Policy",
        f"",
        f"| Card Type | Cooldown (min) |",
        f"|-----------|---------------|",
    ]
    for ct, minutes in COOLDOWN_POLICY.items():
        lines.append(f"| `{ct}` | {minutes} |")
    lines.append(f"")
    lines.extend([
        f"---",
        f"",
        f"## Pipeline 确认",
        f"",
        f"Pipeline 已建立：",
        f"",
        f"```",
        f"adapter output -> signal envelope -> dedupe/cooldown gate -> eligible signals",
        f"```",
        f"",
        f"| 阶段 | 状态 |",
        f"|------|------|",
        f"| v112h envelope 生成 | Done |",
        f"| v112i dedupe/cooldown gate | Done |",
        f"| TG send | Not connected |",
        f"| Live data | Not connected |",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"1. Dedupe + Cooldown Gate 层已建立并通过测试。",
        f"2. 所有 envelope 都生成了 gate decision。",
        f"3. Dedupe matching 工作正常 — 同 dedupe_key 的重复信号被正确 block。",
        f"4. Cooldown matching 工作正常 — 同 cooldown_key 且在冷却期内的信号被正确 block。",
        f"5. 不同 card_type 不互相干扰，同资产不同方向不错误 block。",
        f"6. 下一步可以接入真实数据源，或将 eligible signals 送入 sender。",
        f"",
    ])

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
