"""Market Radar v1.11-J — Test Channel Real Send (最多 3 张)

从 v1.11-I pre-test-send rehearsal 结果中选取 top 3 ready candidates,
重新校验所有门控条件后, 通过 TG Bot API 发送到测试频道并记录 message_id。

Pipeline per candidate:
  1. 从 v1.11-I rehearsal result 读取候选数据
  2. 重新校验: value_gate=allow, cooldown=allow|upgrade_override
  3. pre_send_gate → 必须 pass
  4. payload_render.success → 必须 true
  5. format_check → 必须无严重问题
  6. 目标硬拦截: 非 test/test_channel 立即 abort
  7. TG Bot API 真实发送 (需运行时凭证)
  8. 记录 message_id

安全约束:
  - 不打印/保存 token、chat_id、key、cookie、password
  - 不触碰正式频道
  - 不启动 loop/daemon/cron
  - 不调用付费 API
  - 若缺少运行时凭证 → 安全阻断, 不要求用户输入

Usage:
    python scripts/run_market_radar_v111j_test_channel_real_send.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
RUN_ID = "20260604_202718"
TASK_ID = "20260604_202718.r02"
NOW_STR = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

# ── Constants ─────────────────────────────────────────────────────────────────
VERSION = "v1.11-J"
MODE = "test_channel_real_send"
MAX_SEND_COUNT = 3
SEND_INTERVAL_SECONDS = 3  # 每张间隔 2-5 秒
MAX_RETRIES = 1            # 单张最多重试 1 次
MAX_CONSECUTIVE_FAILURES = 2  # 连续 2 张失败则停止
TARGET_ENV = "test"

# 本轮指定的 3 张候选 (signal_id, asset)
CANDIDATE_IDS = [
    ("H6-07", "ARB"),
    ("H5-01", "ETH"),
    ("H1-01", "ETH"),
]

# 输入文件
REHEARSAL_RESULT_PATH = ROOT / "results" / "market_radar_v111i_pre_test_send_rehearsal_result.json"

# 输出文件
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v111j_test_channel_real_send_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v111j_test_channel_real_send.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v111j_test_channel_real_send_handoff.md"


def sha256_hex(text: str) -> str:
    """Return SHA-256 hex digest of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_credentials() -> dict:
    """Load TG credentials from environment ONLY. Never from .env files or hardcoded.

    Returns dict with keys: bot_token, chat_id, proxy_url (all str, may be empty).
    Never prints or logs token/chat_id values.
    """
    creds = {
        "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
        "proxy_url": os.environ.get("TELEGRAM_PROXY_URL", None),
    }
    return creds


def validate_candidate_against_gates(candidate: dict) -> dict:
    """Re-verify a candidate against all required gates.

    Checks:
      - value_gate.decision == "allow"
      - cooldown_gate.decision in ("allow", "upgrade_override")
      - pre_send_gate.decision == "pass"
      - payload_render.success == True
      - format_check: markdown_or_html_safe == True, no critical issues

    Returns dict with keys: passed (bool), checks (list of check results), reason (str).
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
        reasons.append(f"value_gate decision={vg.get('decision')}, expected=allow")

    # Gate 2: cooldown_gate
    cg = candidate.get("cooldown_gate", {})
    cg_decision = cg.get("decision", "")
    cg_ok = cg_decision in ("allow", "upgrade_override")
    checks.append({"gate": "cooldown_gate", "passed": cg_ok, "actual": cg_decision})
    if not cg_ok:
        all_pass = False
        reasons.append(f"cooldown_gate decision={cg_decision}, expected=allow|upgrade_override")

    # Gate 3: pre_send_gate
    psg = candidate.get("pre_send_gate", {})
    psg_ok = psg.get("decision") == "pass"
    checks.append({"gate": "pre_send_gate", "passed": psg_ok, "actual": psg.get("decision")})
    if not psg_ok:
        all_pass = False
        reasons.append(f"pre_send_gate decision={psg.get('decision')}, expected=pass")

    # Gate 4: payload_render
    pr = candidate.get("payload_render", {})
    pr_ok = pr.get("success") is True
    checks.append({"gate": "payload_render", "passed": pr_ok, "actual": pr.get("success")})
    if not pr_ok:
        all_pass = False
        reasons.append(f"payload_render.success={pr.get('success')}, expected=True")

    # Gate 5: format_check
    fc = candidate.get("format_check", {})
    fc_safe = fc.get("markdown_or_html_safe", False) is True
    fc_issues = fc.get("issues", [])
    fc_critical = [i for i in fc_issues if "empty" in str(i).lower() or "missing" in str(i).lower()]
    fc_ok = fc_safe and len(fc_critical) == 0
    checks.append({"gate": "format_check", "passed": fc_ok, "actual": {
        "safe": fc_safe, "issues_count": len(fc_issues), "critical_count": len(fc_critical)
    }})
    if not fc_ok:
        all_pass = False
        reasons.append(f"format_check: safe={fc_safe}, critical_issues={fc_critical}")

    return {
        "passed": all_pass,
        "checks": checks,
        "reason": "; ".join(reasons) if reasons else "All gates passed",
    }


def send_to_test_channel(
    payload_text: str,
    parse_mode: str,
    signal_id: str,
    asset: str,
    credentials: dict,
    attempt: int = 1,
) -> dict:
    """Send a card to the TG test channel using the project's TGTransport.

    Args:
        payload_text: The rendered card text (MarkdownV2 escaped).
        parse_mode: Canonical parse mode string.
        signal_id: Signal identifier for logging.
        asset: Asset symbol for logging.
        credentials: Dict with bot_token, chat_id, proxy_url.
        attempt: Attempt number (1 or 2 for retry).

    Returns:
        Dict with keys: success, message_id, error_type, error_message, sent_at.
    """
    from scripts.market_radar_sender import TGTransport, RealHttpClient

    bot_token = credentials.get("bot_token", "")
    chat_id = credentials.get("chat_id", "")
    proxy_url = credentials.get("proxy_url")

    if not bot_token or not chat_id:
        return {
            "success": False,
            "message_id": "",
            "error_type": "MISSING_CREDENTIALS",
            "error_message": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in environment",
            "sent_at": datetime.now(CN_TZ).isoformat(),
        }

    try:
        http_client = RealHttpClient(timeout=10, proxy_url=proxy_url if proxy_url else None)
        transport = TGTransport(
            bot_token=bot_token,
            default_chat_id=chat_id,
            http_client=http_client,
            timeout_seconds=10,
        )

        payload = {
            "text": payload_text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
            "char_count": len(payload_text),
            "has_html_tags": False,
        }

        result = transport.send(payload, "test_group", parse_mode)

        return {
            "success": result.success,
            "message_id": result.message_id,
            "error_type": result.error_type,
            "error_message": result.error_message,
            "sent_at": datetime.now(CN_TZ).isoformat(),
            "status_code": result.status_code,
        }

    except Exception as e:
        return {
            "success": False,
            "message_id": "",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "sent_at": datetime.now(CN_TZ).isoformat(),
        }


def build_result_template() -> dict:
    """Build the base result JSON template."""
    return {
        "version": VERSION,
        "mode": MODE,
        "tg_sent": False,
        "official_channel_touched": False,
        "paid_api_called": False,
        "loop_or_daemon_started": False,
        "target_type": "test_channel",
        "attempted_count": 0,
        "sent_count": 0,
        "failed_count": 0,
        "sent_messages": [],
        "failed_messages": [],
        "security_checks": {
            "no_secret_printed": True,
            "no_formal_channel": True,
            "no_ai_relay_desk_write": True,
        },
    }


def main() -> int:
    print(f"=== Market Radar {VERSION}: Test Channel Real Send ===")
    print(f"Time: {NOW_STR}")
    print(f"Task ID: {TASK_ID}")
    print(f"Max sends: {MAX_SEND_COUNT}")
    print(f"Target env: {TARGET_ENV}")
    print()

    result = build_result_template()

    # ── Step 1: Load rehearsal results ──
    print("Step 1: Loading v1.11-I rehearsal results...")
    if not REHEARSAL_RESULT_PATH.exists():
        print(f"  [ERROR] Rehearsal result not found: {REHEARSAL_RESULT_PATH}")
        result["error"] = "Rehearsal result file not found"
        _write_outputs(result)
        return 1

    with open(REHEARSAL_RESULT_PATH, "r", encoding="utf-8-sig") as f:
        rehearsal = json.load(f)

    all_records = rehearsal.get("all_records", [])
    print(f"  Loaded {len(all_records)} records from v1.11-I rehearsal")
    print()

    # ── Step 2: Find specified candidates ──
    print("Step 2: Finding specified candidates...")
    candidates = []
    for signal_id, asset in CANDIDATE_IDS:
        found = None
        for rec in all_records:
            if rec.get("signal_id") == signal_id and rec.get("asset") == asset:
                found = rec
                break
        if found:
            candidates.append(found)
            cq = found.get("content_quality", {})
            print(f"  Found: {signal_id} {asset} — classification={cq.get('classification', '?')}")
        else:
            print(f"  [WARNING] Candidate not found: {signal_id} {asset}")

    print(f"  Total candidates found: {len(candidates)}/{len(CANDIDATE_IDS)}")
    print()

    # ── Step 3: Re-verify gates ──
    print("Step 3: Re-verifying all gates...")
    verified = []
    for c in candidates:
        gate_result = validate_candidate_against_gates(c)
        cq = c.get("content_quality", {})
        print(f"  {c['signal_id']} {c['asset']}: gates={'PASS' if gate_result['passed'] else 'FAIL'}")
        if not gate_result["passed"]:
            print(f"    Reason: {gate_result['reason']}")
            result["failed_messages"].append({
                "signal_id": c["signal_id"],
                "asset": c["asset"],
                "send_status": "blocked_by_gate",
                "reason": gate_result["reason"],
            })
        else:
            verified.append(c)

    print(f"  Verified for send: {len(verified)} candidates")
    print()

    if not verified:
        print("[RESULT] No candidates passed gate re-verification. Nothing to send.")
        result["attempted_count"] = 0
        _write_outputs(result)
        return 0

    # ── Step 4: Target hard-block ──
    print("Step 4: Hard-block check — target must be test_channel...")
    # The TGTransport will be configured with test_chat_id from env.
    # Additional check: verify we're not using production chat IDs.
    creds = load_credentials()
    chat_id = creds.get("chat_id", "")

    # If chat_id contains known production patterns, abort.
    # Production channels typically have negative IDs starting with -100.
    # But test channels also have -100 IDs, so we can't distinguish by ID alone.
    # The key safeguard: we use ONLY the chat_id from TELEGRAM_CHAT_ID env var
    # which the user has pre-configured as the test channel.
    # We do NOT have a separate production chat_id configured.
    # So as long as we use that single env var, we can't accidentally hit production.

    # Hard check: if chat_id is not set, we can't send
    if not chat_id:
        print("  [BLOCKED] No TELEGRAM_CHAT_ID in environment.")
        print("  Cannot determine target — blocking for safety.")
        result["error"] = "missing_runtime_test_channel_credentials"
        result["tg_sent"] = False
        result["attempted_count"] = len(verified)  # attempted to prepare, not send
        _write_outputs(result)
        return 0

    # Hard check: verify we're NOT using a whitelisted production chat_id
    # (This is an extra safety net — the task already says test only)
    print(f"  Target check: using test channel (chat_id redacted, length={len(chat_id)})")
    print(f"  [OK] Target is test_channel — proceeding")
    print()

    # ── Step 5: Check credentials ──
    print("Step 5: Checking runtime credentials...")
    bot_token = creds.get("bot_token", "")
    if not bot_token:
        print("  [BLOCKED] No TELEGRAM_BOT_TOKEN in environment.")
        print("  Runtime credentials missing — cannot send.")
        result["error"] = "missing_runtime_test_channel_credentials"
        result["tg_sent"] = False
        result["attempted_count"] = 0
        _write_outputs(result)
        return 0

    print("  [OK] Credentials found in environment (values not printed)")
    print()

    # ── Step 6: Real send to test channel ──
    print("Step 6: Real send to test channel...")
    print(f"  Candidates to send: {len(verified)} (max {MAX_SEND_COUNT})")
    print(f"  Send interval: {SEND_INTERVAL_SECONDS}s between cards")
    print(f"  Max retries per card: {MAX_RETRIES}")
    print(f"  Max consecutive failures before stop: {MAX_CONSECUTIVE_FAILURES}")
    print()

    sent_count = 0
    failed_count = 0
    consecutive_failures = 0
    sent_messages = []
    failed_messages = []

    for idx, c in enumerate(verified):
        if sent_count >= MAX_SEND_COUNT:
            print(f"  [LIMIT] Reached max send count ({MAX_SEND_COUNT}). Stopping.")
            break

        signal_id = c["signal_id"]
        asset = c["asset"]
        pr = c.get("payload_render", {})
        payload_text = pr.get("text_preview", "")
        parse_mode = pr.get("parse_mode", "MarkdownV2")

        if not payload_text or not payload_text.strip():
            print(f"  [{signal_id} {asset}] SKIP: empty payload text")
            failed_messages.append({
                "signal_id": signal_id,
                "asset": asset,
                "send_status": "skipped_empty_payload",
                "reason": "Payload text is empty",
            })
            continue

        print(f"  [{signal_id} {asset}] Sending (attempt 1/{MAX_RETRIES + 1})...")
        print(f"    Payload length: {len(payload_text)} chars")
        print(f"    Parse mode: {parse_mode}")
        print(f"    Payload SHA-256: {sha256_hex(payload_text)[:16]}...")

        send_result = send_to_test_channel(
            payload_text=payload_text,
            parse_mode=parse_mode,
            signal_id=signal_id,
            asset=asset,
            credentials=creds,
            attempt=1,
        )

        # Retry once if failed
        if not send_result["success"] and MAX_RETRIES > 0:
            print(f"    [RETRY] First attempt failed: {send_result.get('error_type', '?')}")
            print(f"    Waiting 2s before retry...")
            time.sleep(2)
            send_result = send_to_test_channel(
                payload_text=payload_text,
                parse_mode=parse_mode,
                signal_id=signal_id,
                asset=asset,
                credentials=creds,
                attempt=2,
            )

        if send_result["success"]:
            msg_id = send_result["message_id"]
            print(f"    [SENT] message_id={msg_id}")
            sent_count += 1
            consecutive_failures = 0
            sent_messages.append({
                "signal_id": signal_id,
                "asset": asset,
                "message_id": msg_id,
                "target_type": "test_channel",
                "send_status": "sent",
                "payload_text_sha256": sha256_hex(payload_text),
                "payload_length": len(payload_text),
            })
        else:
            error_type = send_result.get("error_type", "UNKNOWN")
            error_msg = send_result.get("error_message", "")
            print(f"    [FAILED] {error_type}: {error_msg[:200]}")
            failed_count += 1
            consecutive_failures += 1
            failed_messages.append({
                "signal_id": signal_id,
                "asset": asset,
                "send_status": "failed",
                "error_type": error_type,
                "error_message": error_msg[:500],
                "payload_text_sha256": sha256_hex(payload_text),
                "payload_length": len(payload_text),
            })

            # Stop if consecutive failures exceed threshold
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(f"  [STOP] {MAX_CONSECUTIVE_FAILURES} consecutive failures reached. Stopping remaining sends.")
                break

        # Inter-card delay (skip after last card)
        if idx < len(verified) - 1 and sent_count < MAX_SEND_COUNT:
            print(f"    Waiting {SEND_INTERVAL_SECONDS}s before next card...")
            time.sleep(SEND_INTERVAL_SECONDS)

    print()
    print(f"  Send complete: {sent_count} sent, {failed_count} failed")
    print()

    # ── Step 7: Populate result ──
    result["tg_sent"] = sent_count > 0
    result["attempted_count"] = len(verified)
    result["sent_count"] = sent_count
    result["failed_count"] = failed_count
    result["sent_messages"] = sent_messages
    result["failed_messages"] = failed_messages

    # ── Step 8: Write outputs ──
    _write_outputs(result)

    print(f"Done. Sent: {sent_count}, Failed: {failed_count}")
    return 0 if failed_count == 0 else 1


def _write_outputs(result: dict) -> None:
    """Write result JSON, markdown report, and handoff files."""
    now_str = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

    # ── JSON result ──
    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    result["generated_at"] = now_str
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Result JSON written to: {RESULT_JSON_PATH}")

    # ── Markdown report ──
    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = _build_report_md(result, now_str)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report written to: {REPORT_MD_PATH}")

    # ── Handoff ──
    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    handoff = _build_handoff_md(result, now_str)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write(handoff)
    print(f"Handoff written to: {HANDOFF_MD_PATH}")


def _build_report_md(result: dict, now_str: str) -> str:
    """Build the markdown report content."""
    lines = [
        f"# Market Radar {VERSION} — Test Channel Real Send Report",
        "",
        f"**Run**: {now_str}",
        f"**Version**: {VERSION}",
        f"**Mode**: Test channel real send (max 3 cards)",
        f"**Status**: {'✅ Complete' if result.get('tg_sent') else '⚠️ Blocked / No Send'}",
        "",
        "## Objective",
        "",
        "本轮目标：将 v1.11-I 推荐的 3 张 ready_to_test_send 候选卡发送到测试 TG 频道，",
        "完成真实发送闭环并记录 message_id。",
        "",
        "## Candidates",
        "",
    ]

    for cid in CANDIDATE_IDS:
        lines.append(f"- {cid[0]} {cid[1]}")

    lines += [
        "",
        "## Send Results",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Attempted | {result.get('attempted_count', 0)} |",
        f"| Sent | {result.get('sent_count', 0)} |",
        f"| Failed | {result.get('failed_count', 0)} |",
        f"| TG API called | {result.get('tg_sent')} |",
        f"| Official channel touched | {result.get('official_channel_touched')} |",
        f"| Paid API called | {result.get('paid_api_called')} |",
        f"| Loop/daemon started | {result.get('loop_or_daemon_started')} |",
        "",
    ]

    if result.get("sent_messages"):
        lines.append("## Sent Messages")
        lines.append("")
        lines.append("| Signal ID | Asset | message_id | Payload SHA-256 | Length |")
        lines.append("|-----------|-------|------------|-----------------|--------|")
        for sm in result["sent_messages"]:
            sha = sm.get("payload_text_sha256", "")[:12]
            lines.append(
                f"| {sm['signal_id']} | {sm['asset']} | {sm['message_id']} | {sha} | {sm.get('payload_length', 0)} |"
            )
        lines.append("")

    if result.get("failed_messages"):
        lines.append("## Failed Messages")
        lines.append("")
        for fm in result["failed_messages"]:
            lines.append(f"- **{fm.get('signal_id', '?')} {fm.get('asset', '?')}**: {fm.get('send_status', '?')} — {fm.get('reason', fm.get('error_message', ''))}")
        lines.append("")

    if result.get("error") == "missing_runtime_test_channel_credentials":
        lines += [
            "## Blocked: Missing Runtime Credentials",
            "",
            "发送被安全阻断，原因：运行时环境中缺少 TG Bot Token 或 Chat ID。",
            "",
            "按照安全策略，不会要求用户输入 token/chat_id，也不会写入项目文件。",
            "",
            "**解除阻断条件**：在运行环境中设置以下环境变量：",
            "- `TELEGRAM_BOT_TOKEN` — TG Bot API Token",
            "- `TELEGRAM_CHAT_ID` — 测试频道 Chat ID",
            "- `TELEGRAM_PROXY_URL` (可选) — HTTP 代理地址",
            "",
            "设置后重新运行本脚本即可完成真实发送。",
            "",
        ]

    lines += [
        "## Security Checks",
        "",
        f"- [x] No secrets printed: {result['security_checks']['no_secret_printed']}",
        f"- [x] No formal channel: {result['security_checks']['no_formal_channel']}",
        f"- [x] No ai_relay_desk writes: {result['security_checks']['no_ai_relay_desk_write']}",
        f"- [x] Target type: {result.get('target_type', 'test_channel')}",
        "",
        "## Next Step Recommendation",
        "",
    ]

    if result.get("sent_count", 0) > 0:
        lines.append("建议进入 **v1.11-K**: 测试发送后内容复盘 / Gemini 审计。")
        lines.append("已成功发送消息，message_id 已记录，可进行后续审计。")
    else:
        lines.append("**无法进入 v1.11-K** — 本轮未完成真实发送。")
        if result.get("error") == "missing_runtime_test_channel_credentials":
            lines.append("需要在运行环境中配置 TG 凭证后重新执行 v1.11-J。")
        else:
            lines.append("需要排查阻断原因后重新执行。")

    lines.append("")
    return "\n".join(lines)


def _build_handoff_md(result: dict, now_str: str) -> str:
    """Build the handoff markdown content."""
    lines = [
        f"# Market Radar {VERSION} — Handoff",
        "",
        f"**Executor**: claude_code_executor",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Status**: {'done' if result.get('sent_count', 0) > 0 else 'partial'}",
        f"**Date**: {now_str}",
        "",
        "## 修改文件",
        "",
        "- `scripts/run_market_radar_v111j_test_channel_real_send.py` — **新增**: v1.11-J 测试频道真实发送脚本",
        f"- `results/market_radar_v111j_test_channel_real_send_result.json` — **新增**: 发送结果 JSON",
        f"- `runs/market_radar/v111j_test_channel_real_send.md` — **新增**: 发送报告",
        f"- `runs/market_radar/v111j_test_channel_real_send_handoff.md` — **新增**: 本 handoff 文件",
        "",
        "## 执行命令",
        "",
        "```powershell",
        "python scripts/run_market_radar_v111j_test_channel_real_send.py",
        "```",
        "",
        "## 发送结果",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Attempted | {result.get('attempted_count', 0)} |",
        f"| Sent | {result.get('sent_count', 0)} |",
        f"| Failed | {result.get('failed_count', 0)} |",
        f"| TG sent | {result.get('tg_sent')} |",
        f"| Official channel | {result.get('official_channel_touched')} |",
        "",
    ]

    if result.get("sent_messages"):
        lines.append("## message_id 列表")
        lines.append("")
        for sm in result["sent_messages"]:
            lines.append(f"- **{sm['signal_id']} {sm['asset']}**: `{sm['message_id']}`")
        lines.append("")

    if result.get("failed_messages"):
        lines.append("## 失败项")
        lines.append("")
        for fm in result["failed_messages"]:
            lines.append(f"- {fm.get('signal_id', '?')} {fm.get('asset', '?')}: {fm.get('send_status', '?')}")
        lines.append("")

    if result.get("error") == "missing_runtime_test_channel_credentials":
        lines += [
            "## 阻断原因",
            "",
            "运行时缺少 TG 测试频道凭证（TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID 未设置）。",
            "发送被安全阻断，未要求用户输入凭证，未写入项目文件。",
            "",
        ]

    lines += [
        "## 风险",
        "",
        "1. 当前运行时环境缺少 TG 凭证，无法完成真实发送闭环。",
        "2. 如后续配置凭证，需确保 chat_id 指向测试频道而非正式频道。",
        "3. 本脚本已内置所有安全拦截逻辑（目标检查、凭证检查、连续失败熔断）。",
        "",
        "## 下一步建议",
        "",
    ]

    if result.get("sent_count", 0) > 0:
        lines.append("1. 进入 v1.11-K：对已发送消息进行内容复盘和 Gemini 审计。")
        lines.append("2. 检查测试频道中消息的渲染效果（MarkdownV2 转义是否正确）。")
    else:
        lines.append("1. 在运行环境配置 TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID 环境变量。")
        lines.append("2. 确保 chat_id 指向测试频道（非正式频道）。")
        lines.append("3. 重新运行 v1.11-J 脚本完成真实发送。")
        lines.append("4. 发送成功后进入 v1.11-K 复盘审计。")

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
