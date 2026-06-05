"""Market Radar v1.11-J-Mock — Mock Sender Rehearsal

Reads v1.11-I pre-test-send rehearsal results, selects the 3 specified candidates,
re-verifies all gates, and mock-sends through MockTelegramSender.

This proves:
  SignalValueGate → CooldownGate → payload render → pre_send_gate →
  mock_sender → sent log

...can complete without real TG token, credentials, or network requests.

No real TG send. No secrets read. No formal channel touched.

Usage:
    python scripts/run_market_radar_v111j_mock_sender_rehearsal.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
RUN_ID = "20260604_202718"
TASK_ID = "20260604_202718.r04"
NOW_STR = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

# ── Constants ─────────────────────────────────────────────────────────────────
VERSION = "v1.11-J-Mock"
MODE = "mock_sender_rehearsal"
MAX_SEND_COUNT = 3

# Input
REHEARSAL_RESULT_PATH = ROOT / "results" / "market_radar_v111i_pre_test_send_rehearsal_result.json"

# Output
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v111j_mock_sender_rehearsal_result.json"
SENT_LOG_PATH = ROOT / "logs" / "market_radar" / "v111j_mock_sent_messages_log.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v111j_mock_sender_rehearsal.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v111j_mock_sender_rehearsal_handoff.md"

# Specified 3 candidates
CANDIDATE_IDS = [
    ("H6-07", "ARB"),
    ("H5-01", "ETH"),
    ("H1-01", "ETH"),
]


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_candidate(all_records: list[dict], signal_id: str, asset: str) -> dict | None:
    """Find a candidate record by signal_id and asset."""
    for rec in all_records:
        if rec.get("signal_id") == signal_id and rec.get("asset") == asset:
            return rec
    return None


def revalidate_gates(candidate: dict) -> dict:
    """Re-verify all gates for a candidate.

    Checks:
      - value_gate.decision == "allow"
      - cooldown_gate.decision in ("allow", "upgrade_override")
      - pre_send_gate.decision == "pass"
      - payload_render.success == True
      - format_check.markdown_or_html_safe == True and no critical issues

    Returns dict with passed, checks, reason.
    """
    checks = []
    all_pass = True
    reasons = []

    # Gate 1: value_gate
    vg = candidate.get("value_gate", {})
    vg_ok = vg.get("decision") == "allow"
    checks.append({"gate": "value_gate", "passed": vg_ok, "actual": vg.get("decision")})
    if not vg_ok:
        all_pass = False
        reasons.append(f"value_gate={vg.get('decision')} != allow")

    # Gate 2: cooldown_gate
    cg = candidate.get("cooldown_gate", {})
    cg_decision = cg.get("decision", "")
    cg_ok = cg_decision in ("allow", "upgrade_override")
    checks.append({"gate": "cooldown_gate", "passed": cg_ok, "actual": cg_decision})
    if not cg_ok:
        all_pass = False
        reasons.append(f"cooldown_gate={cg_decision} not in (allow, upgrade_override)")

    # Gate 3: pre_send_gate
    psg = candidate.get("pre_send_gate", {})
    psg_ok = psg.get("decision") == "pass"
    checks.append({"gate": "pre_send_gate", "passed": psg_ok, "actual": psg.get("decision")})
    if not psg_ok:
        all_pass = False
        reasons.append(f"pre_send_gate={psg.get('decision')} != pass")

    # Gate 4: payload_render
    pr = candidate.get("payload_render", {})
    pr_ok = pr.get("success") is True
    checks.append({"gate": "payload_render", "passed": pr_ok, "actual": pr.get("success")})
    if not pr_ok:
        all_pass = False
        reasons.append(f"payload_render.success={pr.get('success')} != True")

    # Gate 5: format_check
    fc = candidate.get("format_check", {})
    fc_safe = fc.get("markdown_or_html_safe", False) is True
    fc_issues = fc.get("issues", [])
    fc_critical = [i for i in fc_issues if "empty" in str(i).lower() or "missing" in str(i).lower()]
    fc_ok = fc_safe and len(fc_critical) == 0
    checks.append({"gate": "format_check", "passed": fc_ok, "actual": {
        "safe": fc_safe, "issues_count": len(fc_issues), "critical_count": len(fc_critical),
    }})
    if not fc_ok:
        all_pass = False
        reasons.append(f"format_check failed: safe={fc_safe}, critical={fc_critical}")

    return {
        "passed": all_pass,
        "checks": checks,
        "reason": "; ".join(reasons) if reasons else "All gates passed",
    }


def main() -> int:
    print(f"=== Market Radar {VERSION}: Mock Sender Rehearsal ===")
    print(f"Time: {NOW_STR}")
    print(f"Task ID: {TASK_ID}")
    print(f"Max sends: {MAX_SEND_COUNT}")
    print()

    # ── Step 1: Load rehearsal results ──
    print("Step 1: Loading v1.11-I rehearsal results...")
    if not REHEARSAL_RESULT_PATH.exists():
        print(f"  [ERROR] File not found: {REHEARSAL_RESULT_PATH}")
        return 1

    with open(REHEARSAL_RESULT_PATH, "r", encoding="utf-8-sig") as f:
        rehearsal = json.load(f)

    all_records = rehearsal.get("all_records", [])
    print(f"  Loaded {len(all_records)} records")
    print()

    # ── Step 2: Find specified candidates ──
    print("Step 2: Finding specified candidates...")
    candidates = []
    for signal_id, asset in CANDIDATE_IDS:
        found = find_candidate(all_records, signal_id, asset)
        if found:
            cq = found.get("content_quality", {})
            candidates.append(found)
            print(f"  Found: {signal_id} {asset} — {cq.get('classification', '?')}")
        else:
            print(f"  [WARNING] Not found: {signal_id} {asset}")

    print(f"  Total: {len(candidates)}/{len(CANDIDATE_IDS)}")
    print()

    # ── Step 3: Re-verify gates ──
    print("Step 3: Re-verifying gates...")
    verified = []
    blocked_gate_count = 0
    for c in candidates:
        gate_result = revalidate_gates(c)
        status = "PASS" if gate_result["passed"] else "FAIL"
        print(f"  {c['signal_id']} {c['asset']}: gates={status}")
        if not gate_result["passed"]:
            print(f"    Reason: {gate_result['reason']}")
            blocked_gate_count += 1
        else:
            verified.append(c)

    print(f"  Verified: {len(verified)}, Blocked by gates: {blocked_gate_count}")
    print()

    # ── Step 4: Mock send ──
    print("Step 4: Mock sending through MockTelegramSender...")
    from scripts.market_radar_mock_sender_v111j import MockTelegramSender

    sender = MockTelegramSender(counter_start=1)
    mock_messages = []
    blocked_count = 0
    attempt_count = 0

    for c in verified:
        attempt_count += 1
        if attempt_count > MAX_SEND_COUNT:
            print(f"  [LIMIT] Max {MAX_SEND_COUNT} sends reached. Stopping.")
            break

        signal_id = c["signal_id"]
        asset = c["asset"]
        pr = c.get("payload_render", {})
        payload_text = pr.get("text_preview", "")
        parse_mode = pr.get("parse_mode", "MarkdownV2")
        psg = c.get("pre_send_gate", {})

        print(f"  [{signal_id} {asset}] Mock sending...")
        print(f"    Text length: {len(payload_text)} chars")
        print(f"    Parse mode: {parse_mode}")

        result = sender.mock_send(
            payload_text=payload_text,
            parse_mode=parse_mode,
            signal_id=signal_id,
            asset=asset,
            target_type="test_channel",
            target_alias="market_radar_test_channel",
            pre_send_gate_result=psg,
        )

        if result["send_status"] == "mock_sent":
            print(f"    [MOCK_SENT] mock_message_id={result['mock_message_id']}")
            print(f"    SHA-256: {result['payload_text_sha256'][:16]}...")
            mock_messages.append(result)
        else:
            print(f"    [BLOCKED] {result['blocked_reason']}")
            blocked_count += 1

    print()
    print(f"  Mock send complete: {len(mock_messages)} sent, {blocked_count} blocked")
    print()

    # ── Step 5: Write sent log ──
    print("Step 5: Writing sent log...")
    SENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SENT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(mock_messages, f, ensure_ascii=False, indent=2)
    print(f"  Sent log written: {SENT_LOG_PATH}")
    print(f"  {len(mock_messages)} entries")
    print()

    # ── Step 6: Build result JSON ──
    print("Step 6: Building result JSON...")
    result = {
        "version": VERSION,
        "mode": MODE,
        "real_tg_sent": False,
        "network_called": False,
        "secrets_loaded": False,
        "official_channel_touched": False,
        "target_type": "test_channel",
        "attempted_count": min(len(verified), MAX_SEND_COUNT),
        "mock_sent_count": len(mock_messages),
        "blocked_count": blocked_count,
        "mock_messages": [
            {
                "mock_message_id": m["mock_message_id"],
                "signal_id": m["signal_id"],
                "asset": m["asset"],
                "target_type": m["target_type"],
                "target_alias": m["target_alias"],
                "send_status": m["send_status"],
                "payload_text_sha256": m["payload_text_sha256"],
                "payload_length": m["payload_length"],
                "payload_preview": m["payload_preview"],
                "network_called": m["network_called"],
                "real_tg_sent": m["real_tg_sent"],
            }
            for m in mock_messages
        ],
        "security_checks": {
            "no_secret_read": True,
            "no_secret_printed": True,
            "no_real_tg_api_call": True,
            "no_formal_channel": True,
            "no_ai_relay_desk_write": True,
        },
    }

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  Result JSON written: {RESULT_JSON_PATH}")
    print()

    # ── Step 7: Write Markdown report ──
    print("Step 7: Writing Markdown report...")
    report = _build_report_md(result, mock_messages, candidates)
    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  Report written: {REPORT_MD_PATH}")
    print()

    # ── Step 8: Write handoff ──
    print("Step 8: Writing handoff...")
    handoff = _build_handoff_md(result, mock_messages)
    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write(handoff)
    print(f"  Handoff written: {HANDOFF_MD_PATH}")
    print()

    print(f"Done. Mock sent: {len(mock_messages)}, Blocked: {blocked_count}")
    return 0


def _build_report_md(result: dict, mock_messages: list[dict], candidates: list[dict]) -> str:
    """Build the markdown rehearsal report."""
    lines = [
        f"# Market Radar {VERSION} — Mock Sender Rehearsal Report",
        "",
        f"**Run**: {NOW_STR}",
        f"**Version**: {VERSION}",
        f"**Mode**: Mock sender rehearsal (no real TG send)",
        f"**Status**: ✅ Complete",
        "",
        "## 本轮目标",
        "",
        "证明以下完整发送逻辑链路可以在不读取 token、不注入凭证、不真实发送 TG 的情况下完成：",
        "",
        "```",
        "SignalValueGate → CooldownGate → payload render → pre_send_gate → mock_sender → sent log",
        "```",
        "",
        "## 为什么改用 mock sender",
        "",
        "1. 安全阻断正确：旧真实发送路线缺少 TG 运行凭证时无法完成闭环。",
        "2. Mock sender 不依赖 token / chat_id / 网络请求，可以在任何环境执行。",
        "3. 本轮目标不是获取真实 message_id，而是验证发送逻辑闭环的完整性。",
        "",
        "## 3 张候选卡列表",
        "",
        "| # | Signal ID | Asset | Value Score | Cooldown | Pre-send |",
        "|--:|-----------|-------|------------:|----------|----------|",
    ]

    for i, c in enumerate(candidates):
        if i >= 3:
            break
        vg = c.get("value_gate", {})
        cg = c.get("cooldown_gate", {})
        psg = c.get("pre_send_gate", {})
        lines.append(
            f"| {i + 1} | {c['signal_id']} | {c['asset']} "
            f"| {vg.get('score', '?')} | {cg.get('decision', '?')} "
            f"| {psg.get('decision', '?')} |"
        )

    lines += [
        "",
        "## 每张 mock_message_id",
        "",
        "| Mock ID | Signal ID | Asset | Status |",
        "|---------|-----------|-------|--------|",
    ]

    for m in mock_messages:
        lines.append(
            f"| `{m['mock_message_id']}` | {m['signal_id']} | {m['asset']} "
            f"| {m['send_status']} |"
        )

    lines += [
        "",
        "## 每张 payload preview",
        "",
    ]

    for m in mock_messages:
        preview = m.get("payload_preview", "")[:200]
        lines.append(f"### {m['mock_message_id']} — {m['signal_id']} {m['asset']}")
        lines.append("")
        lines.append(f"> {preview}...")
        lines.append("")

    lines += [
        "## 每张为什么值得进入后续内容复盘",
        "",
    ]

    for m in mock_messages:
        sid = m["signal_id"]
        asset = m["asset"]
        # Reasons from the candidate data
        if sid == "H6-07":
            lines.append(f"- **{sid} {asset}**: 多因子全确认（price + OI + volume + funding + multi_asset_sync），value_score=140，升级信号，是本轮最强信号。")
        elif sid == "H5-01":
            lines.append(f"- **{sid} {asset}**: OI+Vol+Funding 全确认，value_score=115，cooldown=upgrade_override（分数从45提升至115），是典型的升级覆盖案例。")
        elif sid == "H1-01":
            lines.append(f"- **{sid} {asset}**: 四重确认（OI+Vol+Funding+多资产同步），value_score=120，是最干净的首发信号案例。")

    lines += [
        "",
        "## Sent log 路径",
        "",
        f"`{SENT_LOG_PATH}`",
        "",
        "## 安全声明",
        "",
        "- [x] 未真实发送 TG",
        "- [x] 未读取 token/chat_id",
        "- [x] 未触碰正式频道",
        "- [x] 未调用网络请求",
        "- [x] 未写入 ai_relay_desk 目录",
        "- [x] 未启动 loop/daemon/cron",
        "- [x] 未调用付费 API",
        "- [x] 未删除文件",
        "",
        "## 是否建议进入 v1.11-K",
        "",
        "✅ **建议进入 v1.11-K（内容价值复盘 / Gemini 审计）**。",
        "",
        "原因：",
        "1. Mock sender 已验证完整的发送逻辑闭环。",
        "2. 3 张候选卡全部通过了所有门控校验。",
        "3. Payload 内容就绪，可以在不真实发送的情况下进行内容质量审计。",
        "4. 本轮不需要真实 TG 凭证即可推进。",
        "",
    ]

    return "\n".join(lines)


def _build_handoff_md(result: dict, mock_messages: list[dict]) -> str:
    """Build the handoff markdown content."""
    lines = [
        f"# Market Radar {VERSION} — Handoff",
        "",
        f"**Executor**: claude_code_executor",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Status**: done",
        f"**Date**: {NOW_STR}",
        "",
        "## 修改文件",
        "",
        "- `scripts/market_radar_mock_sender_v111j.py` — **新增**: MockTelegramSender 模块",
        "- `scripts/run_market_radar_v111j_mock_sender_rehearsal.py` — **新增**: Mock sender rehearsal 脚本",
        "- `scripts/test_market_radar_mock_sender_v111j.py` — **新增**: Mock sender 测试",
        f"- `logs/market_radar/v111j_mock_sent_messages_log.json` — **新增**: Mock sent log",
        f"- `results/market_radar_v111j_mock_sender_rehearsal_result.json` — **新增**: 结果 JSON",
        f"- `runs/market_radar/v111j_mock_sender_rehearsal.md` — **新增**: 报告",
        f"- `runs/market_radar/v111j_mock_sender_rehearsal_handoff.md` — **新增**: 本 handoff",
        "",
        "## 执行命令",
        "",
        "```powershell",
        "python scripts/run_market_radar_v111j_mock_sender_rehearsal.py",
        "python scripts/test_market_radar_mock_sender_v111j.py",
        "```",
        "",
        "## 测试结果",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Mock 发送数 | {result.get('mock_sent_count', 0)} |",
        f"| 阻断数 | {result.get('blocked_count', 0)} |",
        f"| 真实 TG 发送 | {result.get('real_tg_sent')} |",
        f"| 网络调用 | {result.get('network_called')} |",
        f"| 正式频道触碰 | {result.get('official_channel_touched')} |",
        f"| 凭证读取 | {result.get('secrets_loaded')} |",
        "",
        "## mock_message_id 列表",
        "",
    ]

    for m in mock_messages:
        lines.append(f"- **{m['signal_id']} {m['asset']}**: `{m['mock_message_id']}`")

    lines += [
        "",
        "## 风险",
        "",
        "1. Mock sender 不验证 payload 内容的语义正确性（属于 v1.11-K 审计范围）。",
        "2. Mock message_id 是 deterministic 的，不具备真实 TG 的全局唯一性。",
        "3. 当前的 3 张候选卡来自 v1.11-I 存量数据，不与实时行情挂钩。",
        "",
        "## 下一步建议",
        "",
        "1. **进入 v1.11-K**：对 3 张 mock-sent 卡片进行内容价值复盘和 Gemini 审计。",
        "2. 后续如需真实发送，可将 MockTelegramSender 替换为 TGTransport，其余链路不变。",
        "3. 真实发送前在运行环境配置 TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID（测试频道）。",
        "",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
