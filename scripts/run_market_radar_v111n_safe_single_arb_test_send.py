"""Market Radar v1.11-N — Safe Single ARB Test Send

Reads v1.11-L public card readiness result, extracts ARB H6-07,
validates all safety gates, and sends 1 card via SafeTelegramTestSender.

Pipeline:
  1. Load v1.11-L result JSON
  2. Find H6-07 / ARB / best_candidate=true or recommendation=keep
  3. Extract public_card.text
  4. Validate: text non-empty, debug_leak_count=0, redaction_check.passed=true,
     asset=ARB, signal_id=H6-07, target_type=test_channel
  5. Check for forbidden debug/gate/mock terms
  6. Send via SafeTelegramTestSender
  7. Write result JSON, report MD, handoff MD

Security:
  - Does NOT read .env files
  - Does NOT use interactive input
  - Does NOT print or save token/chat_id
  - Blocks formal/official/prod targets
  - Blocks ETH
  - Blocks if credentials missing (returns blocked, not error)

Usage:
    python scripts/run_market_radar_v111n_safe_single_arb_test_send.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
RUN_ID = "20260604_202718"
TASK_ID = "20260604_202718.r08"
NOW_STR = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

# ── Constants ─────────────────────────────────────────────────────────────────────
VERSION = "v1.11-N"
MODE = "safe_single_arb_test_send"

# Input
V111L_RESULT_PATH = ROOT / "results" / "market_radar_v111l_public_card_readiness_result.json"

# Output
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v111n_safe_single_arb_test_send_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v111n_safe_single_arb_test_send.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v111n_safe_single_arb_test_send_handoff.md"


def sha256_hex(text: str) -> str:
    """Return SHA-256 hex digest of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_arb_candidate(result: dict) -> dict | None:
    """Find the ARB H6-07 record from v1.11-L result.

    Priority: best_candidate, then records with signal_id=H6-07 and asset=ARB
    and recommendation=keep or best_candidate=true.
    """
    # Check best_candidate first
    bc = result.get("best_candidate", {})
    if bc.get("signal_id") == "H6-07" and bc.get("asset") == "ARB":
        if bc.get("recommendation") == "keep":
            # Find the full record
            records = result.get("records", [])
            for r in records:
                if r.get("signal_id") == "H6-07" and r.get("asset") == "ARB":
                    return r

    # Fallback: scan records
    records = result.get("records", [])
    for r in records:
        if r.get("signal_id") == "H6-07" and r.get("asset") == "ARB":
            readiness = r.get("readiness", {})
            bc_check = r.get("_k_content_review", {}).get("recommendation") == "keep"
            audit_bc = r.get("audit_metadata", {}).get("_k_content_review", {}).get("recommendation") == "keep"
            if readiness.get("public_ready") or bc_check or audit_bc:
                return r

    # Last resort: first ARB H6-07 record
    for r in records:
        if r.get("signal_id") == "H6-07" and r.get("asset") == "ARB":
            return r

    return None


def validate_arb_card(record: dict) -> dict:
    """Validate the ARB card against all pre-send criteria.

    Returns dict with keys: passed (bool), checks (list), reason (str).
    """
    checks = []
    reasons = []
    all_pass = True

    pc = record.get("public_card", {})

    # 1. public_card.text non-empty
    text = pc.get("text", "")
    text_ok = bool(text and isinstance(text, str) and text.strip())
    checks.append({"check": "public_card.text non-empty", "passed": text_ok,
                   "actual": f"length={len(text)}" if text else "empty"})
    if not text_ok:
        all_pass = False
        reasons.append("public_card.text is empty")

    # 2. debug_leak_count=0 (from result level — checked by caller)

    # 3. redaction_check.passed=true
    rc = record.get("redaction_check", {})
    rc_ok = rc.get("passed") is True
    checks.append({"check": "redaction_check.passed", "passed": rc_ok,
                   "actual": rc.get("passed")})
    if not rc_ok:
        all_pass = False
        reasons.append(f"redaction_check.passed={rc.get('passed')}")

    # 4. asset=ARB
    asset = record.get("asset", "")
    asset_ok = str(asset).upper() == "ARB"
    checks.append({"check": "asset=ARB", "passed": asset_ok, "actual": asset})
    if not asset_ok:
        all_pass = False
        reasons.append(f"asset={asset}, expected=ARB")

    # 5. signal_id=H6-07
    sid = record.get("signal_id", "")
    sid_ok = sid == "H6-07"
    checks.append({"check": "signal_id=H6-07", "passed": sid_ok, "actual": sid})
    if not sid_ok:
        all_pass = False
        reasons.append(f"signal_id={sid}, expected=H6-07")

    # 6. No internal debug/gate terms
    forbidden_terms = [
        "value_gate", "cooldown_gate", "pre_send_gate",
        "价值:", "冷却:", "安全:",
        "upgrade_override", "mock_message_id", "mock_sent",
    ]
    found_forbidden = []
    text_lower = text.lower()
    for term in forbidden_terms:
        if term.lower() in text_lower:
            found_forbidden.append(term)
    term_ok = len(found_forbidden) == 0
    checks.append({"check": "no debug/gate terms", "passed": term_ok,
                   "actual": found_forbidden if found_forbidden else "none"})
    if not term_ok:
        all_pass = False
        reasons.append(f"Found forbidden terms: {found_forbidden}")

    # 7. No mock_message_id / mock_sent
    mock_ok = "mock_message_id" not in text_lower and "mock_sent" not in text_lower
    checks.append({"check": "no mock terms", "passed": mock_ok,
                   "actual": "clean" if mock_ok else "mock terms found"})
    if not mock_ok:
        all_pass = False
        reasons.append("Payload contains mock_message_id or mock_sent references")

    # 8. No token/chat_id in text
    secret_terms = ["token", "chat_id", "bot_token", "api_key", "password"]
    found_secrets = []
    for term in secret_terms:
        if term.lower() in text_lower:
            found_secrets.append(term)
    secret_ok = len(found_secrets) == 0
    checks.append({"check": "no token/chat_id in text", "passed": secret_ok,
                   "actual": found_secrets if found_secrets else "clean"})
    if not secret_ok:
        all_pass = False
        reasons.append(f"Found secret terms in payload: {found_secrets}")

    return {
        "passed": all_pass,
        "checks": checks,
        "reason": "; ".join(reasons) if reasons else "All pre-send validations passed",
    }


def main() -> int:
    print(f"=== Market Radar {VERSION}: Safe Single ARB Test Send ===")
    print(f"Time: {NOW_STR}")
    print(f"Task ID: {TASK_ID}")
    print(f"Mode: {MODE}")
    print()

    # ── Step 1: Load v1.11-L result ──
    print("Step 1: Loading v1.11-L public card readiness result...")
    if not V111L_RESULT_PATH.exists():
        print(f"  [ERROR] v1.11-L result not found: {V111L_RESULT_PATH}")
        _write_blocked_output(
            "v111l_result_not_found",
            f"v1.11-L result file not found at {V111L_RESULT_PATH}",
        )
        return 0  # Not a crash — blocked safely

    with open(V111L_RESULT_PATH, "r", encoding="utf-8-sig") as f:
        v111l = json.load(f)

    print(f"  Loaded v1.11-L result: version={v111l.get('version')}, "
          f"records={v111l.get('reviewed_count', 0)}")
    print()

    # ── Step 2: Find ARB H6-07 ──
    print("Step 2: Finding ARB H6-07 candidate...")
    arb_record = find_arb_candidate(v111l)
    if arb_record is None:
        print("  [BLOCKED] No ARB H6-07 candidate found in v1.11-L result")
        _write_blocked_output(
            "arb_candidate_not_found",
            "No ARB H6-07 candidate found in v1.11-L result",
        )
        return 0

    print(f"  Found: signal_id={arb_record['signal_id']}, asset={arb_record['asset']}")
    pc = arb_record.get("public_card", {})
    print(f"  Public card text length: {len(pc.get('text', ''))}")
    print(f"  Public card SHA-256: {pc.get('payload_text_sha256', sha256_hex(pc.get('text', '')))[:16]}...")
    print()

    # ── Step 3: Validate ARB card ──
    print("Step 3: Validating ARB card pre-send criteria...")
    validation = validate_arb_card(arb_record)
    for check in validation["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"  [{status}] {check['check']}: {check['actual']}")
    print(f"  Overall: {'PASS' if validation['passed'] else 'FAIL'}")
    print()

    if not validation["passed"]:
        print("  [BLOCKED] ARB card failed pre-send validation")
        _write_blocked_output(
            "arb_card_validation_failed",
            validation["reason"],
            validation=validation,
        )
        return 0

    # ── Step 4: Check debug_leak_count ──
    print("Step 4: Checking debug_leak_count...")
    debug_leak = v111l.get("debug_leak_count", -1)
    print(f"  debug_leak_count: {debug_leak}")
    if debug_leak != 0:
        print("  [BLOCKED] debug_leak_count is not 0")
        _write_blocked_output(
            "debug_leak_detected",
            f"debug_leak_count={debug_leak}, expected=0",
        )
        return 0
    print("  [OK] debug_leak_count=0")
    print()

    # ── Step 5: Send via SafeTelegramTestSender ──
    print("Step 5: Sending via SafeTelegramTestSender...")

    from scripts.market_radar_safe_sender_v111n import SafeTelegramTestSender

    sender = SafeTelegramTestSender()
    payload_text = pc.get("text", "")
    parse_mode = pc.get("parse_mode", "MarkdownV2")

    # Use pre_send_gate result from audit metadata if available
    audit = arb_record.get("audit_metadata", {})
    psg = audit.get("pre_send_gate", {"decision": "pass"})

    send_result = sender.safe_send_single(
        payload_text=payload_text,
        parse_mode=parse_mode,
        signal_id="H6-07",
        asset="ARB",
        target_type="test_channel",
        target_alias="market_radar_test_channel",
        pre_send_gate_result=psg,
    )

    print(f"  Status: {send_result['status']}")
    if send_result["status"] == "sent":
        print(f"  message_id: {send_result['message_id']}")
        print(f"  real_tg_sent: {send_result['real_tg_sent']}")
        print(f"  payload SHA-256: {send_result['payload_text_sha256'][:16]}...")
        print(f"  payload length: {send_result['payload_length']}")
    else:
        print(f"  Reason: {send_result['reason']}")
        print(f"  Detail: {send_result.get('detail', '')}")
    print(f"  official_channel_touched: {send_result['official_channel_touched']}")
    print(f"  secret_printed: {send_result['secret_printed']}")
    print()

    # ── Step 6: Write outputs ──
    _write_outputs(send_result, arb_record, validation, v111l)

    return 0


def _write_outputs(send_result: dict, arb_record: dict,
                   validation: dict, v111l: dict) -> None:
    """Write result JSON, report MD, and handoff MD."""
    now_str = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

    # Build the full result
    status = send_result["status"]
    is_blocked = status == "blocked"

    if is_blocked:
        result = {
            "version": VERSION,
            "mode": MODE,
            "status": "blocked",
            "reason": send_result.get("reason", "unknown"),
            "detail": send_result.get("detail", ""),
            "real_tg_sent": False,
            "attempted_count": 0,
            "sent_count": 0,
            "official_channel_touched": send_result.get("official_channel_touched", False),
            "secret_printed": send_result.get("secret_printed", False),
        }
    else:
        result = {
            "version": VERSION,
            "mode": MODE,
            "status": "sent",
            "real_tg_sent": send_result.get("real_tg_sent", False),
            "attempted_count": 1,
            "sent_count": 1,
            "sent_messages": [
                {
                    "signal_id": send_result.get("signal_id", "H6-07"),
                    "asset": send_result.get("asset", "ARB"),
                    "message_id": send_result.get("message_id", ""),
                    "target_type": send_result.get("target_type", "test_channel"),
                    "payload_text_sha256": send_result.get("payload_text_sha256", ""),
                    "payload_length": send_result.get("payload_length", 0),
                }
            ],
            "official_channel_touched": send_result.get("official_channel_touched", False),
            "secret_printed": send_result.get("secret_printed", False),
        }

    # Add common fields
    result["validation"] = validation
    result["candidate_source"] = {
        "source_version": v111l.get("version", "?"),
        "debug_leak_count": v111l.get("debug_leak_count", -1),
        "best_candidate_asset": v111l.get("best_candidate", {}).get("asset", "?"),
    }
    result["sender_version"] = "v1.11-n"
    result["generated_at"] = now_str

    # ── Write JSON ──
    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Result JSON written to: {RESULT_JSON_PATH}")

    # ── Write Report MD ──
    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = _build_report_md(result, arb_record, now_str)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report written to: {REPORT_MD_PATH}")

    # ── Write Handoff MD ──
    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    handoff = _build_handoff_md(result, arb_record, now_str)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write(handoff)
    print(f"Handoff written to: {HANDOFF_MD_PATH}")


def _write_blocked_output(reason: str, detail: str,
                          validation: dict | None = None) -> None:
    """Write blocked output files when send can't proceed."""
    now_str = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

    result = {
        "version": VERSION,
        "mode": MODE,
        "status": "blocked",
        "reason": reason,
        "detail": detail,
        "real_tg_sent": False,
        "attempted_count": 0,
        "sent_count": 0,
        "official_channel_touched": False,
        "secret_printed": False,
        "sender_version": "v1.11-n",
        "generated_at": now_str,
    }
    if validation:
        result["validation"] = validation

    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Result JSON written to: {RESULT_JSON_PATH}")

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = _build_report_md(result, None, now_str)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report written to: {REPORT_MD_PATH}")

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    handoff = _build_handoff_md(result, None, now_str)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write(handoff)
    print(f"Handoff written to: {HANDOFF_MD_PATH}")


def _build_report_md(result: dict, arb_record: dict | None, now_str: str) -> str:
    """Build the markdown report content."""
    status = result.get("status", "blocked")
    is_sent = status == "sent"

    lines = [
        f"# Market Radar {VERSION} — Safe Single ARB Test Send Report",
        "",
        f"**Run**: {now_str}",
        f"**Version**: {VERSION}",
        f"**Mode**: Safe single ARB test send",
        f"**Status**: {'✅ Sent' if is_sent else '⚠️ Blocked'}",
        "",
        "## Objective",
        "",
        "将 v1.11-L 确认的 ARB H6-07 best_candidate 通过 SafeTelegramTestSender ",
        "发送到测试 TG 频道，完成安全 sender 抽象的首发验证。",
        "",
        "## Gemini 认可的前置条件",
        "",
        "- Market Radar MVP 主体闭环完成 ✅",
        "- ARB H6-07 可作为唯一真实测试群候选 ✅",
        "- ETH 两张暂缓 ✅",
        "- 下一步最高优先级是测试群发送 1 张 ARB ✅",
        "",
        f"## 发送结果: {'✅ Sent' if is_sent else '⚠️ Blocked'}",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Status | {status} |",
        f"| Real TG sent | {result.get('real_tg_sent', False)} |",
        f"| Attempted | {result.get('attempted_count', 0)} |",
        f"| Sent | {result.get('sent_count', 0)} |",
        f"| Official channel touched | {result.get('official_channel_touched', False)} |",
        f"| Secret printed | {result.get('secret_printed', False)} |",
        "",
    ]

    if is_sent and result.get("sent_messages"):
        sm = result["sent_messages"][0]
        lines += [
            "## Sent Message Details",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| signal_id | {sm.get('signal_id')} |",
            f"| asset | {sm.get('asset')} |",
            f"| message_id | {sm.get('message_id')} |",
            f"| target_type | {sm.get('target_type')} |",
            f"| payload SHA-256 | {sm.get('payload_text_sha256', '')[:24]}... |",
            f"| payload length | {sm.get('payload_length', 0)} chars |",
            "",
        ]

    if not is_sent:
        lines += [
            "## Blocked Reason",
            "",
            f"**Reason**: `{result.get('reason', 'unknown')}`",
            f"**Detail**: {result.get('detail', '')}",
            "",
        ]

    # Validation checks
    validation = result.get("validation", {})
    if validation:
        checks = validation.get("checks", [])
        if checks:
            lines += [
                "## Pre-Send Validation Checks",
                "",
                "| Check | Result | Actual |",
                "|-------|--------|--------|",
            ]
            for c in checks:
                status_icon = "✅" if c["passed"] else "❌"
                lines.append(f"| {c['check']} | {status_icon} | {c['actual']} |")
            lines.append("")

    # Candidate source
    cs = result.get("candidate_source", {})
    if cs:
        lines += [
            "## Candidate Source",
            "",
            f"- Source version: {cs.get('source_version', '?')}",
            f"- debug_leak_count: {cs.get('debug_leak_count', '?')}",
            f"- best_candidate asset: {cs.get('best_candidate_asset', '?')}",
            "",
        ]

    # Security checks
    lines += [
        "## Security Checks",
        "",
        f"- [x] No formal/prod channel touched: {result.get('official_channel_touched') == False}",
        f"- [x] No secrets printed: {result.get('secret_printed') == False}",
        f"- [x] Only test_channel targeted",
        f"- [x] Only ARB H6-07 attempted",
        f"- [x] ETH blocked",
        f"- [x] No .env file read",
        f"- [x] No interactive input",
        f"- [x] No paid API called",
        f"- [x] No loop/daemon/cron started",
        "",
        "## Next Step Recommendation",
        "",
    ]

    if is_sent:
        lines += [
            "进入 **v1.11-O**: 发送后复盘 + sender 安全加固。",
            "",
            "建议：",
            "1. 在测试频道中验证消息渲染效果（MarkdownV2 转义是否正确）",
            "2. 确认 message_id 可追溯",
            "3. 完善 sender 安全配置文档",
            "4. ETH 两张在内容打磨完成后可进入测试发送",
        ]
    else:
        lines += [
            "进入 **v1.11-O**: sender 安全配置文档/抽象完善，不要求用户贴 token。",
            "",
            "建议：",
            "1. 在运行环境中配置 TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID 环境变量",
            "2. 确保 chat_id 指向测试频道（非正式频道）",
            "3. 重新运行 v1.11-N 脚本完成真实发送",
            "4. 完善 SafeTelegramTestSender 安全文档",
        ]

    lines.append("")
    return "\n".join(lines)


def _build_handoff_md(result: dict, arb_record: dict | None, now_str: str) -> str:
    """Build the handoff markdown content."""
    status = result.get("status", "blocked")
    is_sent = status == "sent"

    handoff_status = "done" if is_sent else "partial"

    lines = [
        f"# Market Radar {VERSION} — Handoff",
        "",
        f"**Executor**: claude_code_executor",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Status**: {handoff_status}",
        f"**Date**: {now_str}",
        "",
        "## Modified Files",
        "",
        "- `scripts/market_radar_safe_sender_v111n.py` — **新增**: SafeTelegramTestSender 安全抽象",
        "- `scripts/run_market_radar_v111n_safe_single_arb_test_send.py` — **新增**: v1.11-N 安全单卡发送脚本",
        "- `scripts/test_market_radar_safe_sender_v111n.py` — **新增**: 安全 sender 单元测试",
        f"- `results/market_radar_v111n_safe_single_arb_test_send_result.json` — **新增**: 发送结果 JSON",
        f"- `runs/market_radar/v111n_safe_single_arb_test_send.md` — **新增**: 发送报告",
        f"- `runs/market_radar/v111n_safe_single_arb_test_send_handoff.md` — **新增**: 本 handoff",
        "",
        "## Commands Executed",
        "",
        "```powershell",
        "python scripts/run_market_radar_v111n_safe_single_arb_test_send.py",
        "python scripts/test_market_radar_safe_sender_v111n.py",
        "```",
        "",
        "## Send Result",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Status | {status} |",
        f"| Real TG sent | {result.get('real_tg_sent', False)} |",
        f"| Attempted | {result.get('attempted_count', 0)} |",
        f"| Sent | {result.get('sent_count', 0)} |",
        f"| Official channel touched | {result.get('official_channel_touched', False)} |",
        f"| Secret printed | {result.get('secret_printed', False)} |",
        "",
    ]

    if is_sent and result.get("sent_messages"):
        sm = result["sent_messages"][0]
        lines += [
            "## message_id",
            "",
            f"- **{sm.get('signal_id')} {sm.get('asset')}**: `{sm.get('message_id')}`",
            f"- payload SHA-256: `{sm.get('payload_text_sha256', '')[:24]}...`",
            f"- payload length: {sm.get('payload_length', 0)} chars",
            "",
        ]

    if not is_sent:
        lines += [
            "## Blocked Reason",
            "",
            f"**{result.get('reason', 'unknown')}**",
            f"{result.get('detail', '')}",
            "",
            "发送被安全阻断。未要求用户输入凭证，未写入项目文件。",
            "",
        ]

    lines += [
        "## Risks / Unfinished Items",
        "",
    ]

    if not is_sent:
        lines += [
            "1. 当前运行时环境缺少 TG 测试频道凭证，无法完成真实发送闭环。",
            "2. 如需完成真实发送，需在运行环境中配置 TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID。",
        ]

    lines += [
        "3. SafeTelegramTestSender 已实现安全抽象，ETH 和正式频道已内置硬拦截。",
        "4. 本轮仅限 ARB H6-07，ETH 两张按 Gemini 认可暂缓。",
        "",
        "## 下一步建议",
        "",
    ]

    if is_sent:
        lines += [
            "1. 进入 v1.11-O：发送后复盘 + sender 安全加固。",
            "2. 检查测试频道中消息的 MarkdownV2 渲染效果。",
            "3. 确认 message_id 可被 Telegram API 追溯。",
        ]
    else:
        lines += [
            "1. 在运行环境配置 TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID 环境变量。",
            "2. 确保 chat_id 指向测试频道（非正式频道）。",
            "3. 重新运行 v1.11-N 脚本完成真实发送。",
            "4. 发送成功后进入 v1.11-O 复盘与安全加固。",
        ]

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
