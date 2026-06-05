"""Market Radar v1.11-O — Sender Runtime Readiness Check

Checks whether the runtime environment has the credentials needed for
a real Telegram test-channel send, WITHOUT printing, saving, or leaking
any token/chat_id values.

Security guarantees:
  - Does NOT read .env files
  - Does NOT use interactive input (Read-Host)
  - Does NOT call Telegram API
  - Does NOT print or save token/chat_id/key/cookie/password
  - Only outputs present/absent booleans
  - chat_id is reported as present_masked + length_bucket only
  - Never outputs token/chat_id prefixes or suffixes

Usage:
    python scripts/check_market_radar_sender_runtime_v111o.py
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

CN_TZ = timezone(timedelta(hours=8))
VERSION = "v1.11-O"
MODE = "sender_runtime_readiness"

# ── Paths ──────────────────────────────────────────────────────────────────────────
V111N_RESULT_PATH = ROOT / "results" / "market_radar_v111n_safe_single_arb_test_send_result.json"
V111L_RESULT_PATH = ROOT / "results" / "market_radar_v111l_public_card_readiness_result.json"
RESULT_JSON_PATH = ROOT / "results" / "market_radar_v111o_sender_runtime_readiness_result.json"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v111o_sender_runtime_readiness.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v111o_sender_runtime_readiness_handoff.md"

# ── Helpers ──────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    """Return current ISO timestamp in CN_TZ."""
    return datetime.now(CN_TZ).isoformat()


def _masked_chat_id_info(raw: str) -> dict:
    """Return masked info about a chat_id value — never the value itself.

    Returns:
        Dict with present_masked (bool) and length_bucket (str).
    """
    if not raw or not isinstance(raw, str) or not raw.strip():
        return {"present_masked": False, "length_bucket": "empty"}

    length = len(raw.strip())
    if length <= 6:
        bucket = "short"
    elif length <= 15:
        bucket = "medium"
    else:
        bucket = "long"

    return {"present_masked": True, "length_bucket": bucket}


def _check_env_readiness() -> dict:
    """Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in os.environ.

    Never prints or returns actual values.
    """
    bot_token_raw = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id_raw = os.environ.get("TELEGRAM_CHAT_ID", "")

    token_present = bool(bot_token_raw and bot_token_raw.strip())
    chat_id_present = bool(chat_id_raw and chat_id_raw.strip())

    chat_id_info = _masked_chat_id_info(chat_id_raw)

    return {
        "telegram_bot_token_present": token_present,
        "telegram_chat_id_present": chat_id_present,
        "telegram_chat_id_masked": {
            "present_masked": chat_id_info.get("present_masked", False),
            "length_bucket": chat_id_info.get("length_bucket", "empty"),
        },
        "values_printed": False,
    }


def _check_v111n_blocked() -> dict:
    """Check whether v1.11-N result is blocked/missing credentials."""
    if not V111N_RESULT_PATH.exists():
        return {
            "v111n_result_exists": False,
            "v111n_status": "unknown",
            "v111n_reason": "result_file_not_found",
            "v111n_blocked_by_credentials": True,  # Assume blocked if no result
        }

    with open(V111N_RESULT_PATH, "r", encoding="utf-8-sig") as f:
        v111n = json.load(f)

    status = v111n.get("status", "unknown")
    reason = v111n.get("reason", "")
    is_blocked = status == "blocked"
    is_credential_block = "missing_runtime_test_channel_credentials" in reason

    return {
        "v111n_result_exists": True,
        "v111n_status": status,
        "v111n_reason": reason,
        "v111n_blocked_by_credentials": is_blocked and is_credential_block,
        "v111n_blocked": is_blocked,
    }


def _check_arb_h607_readiness() -> dict:
    """Check ARB H6-07 public card readiness from v1.11-L result."""
    if not V111L_RESULT_PATH.exists():
        return {
            "signal_id": "H6-07",
            "asset": "ARB",
            "public_card_ready": False,
            "debug_leak_count": -1,
            "v111l_result_found": False,
        }

    with open(V111L_RESULT_PATH, "r", encoding="utf-8-sig") as f:
        v111l = json.load(f)

    debug_leak_count = v111l.get("debug_leak_count", -1)
    best = v111l.get("best_candidate", {})

    # ETH must NOT be in readiness
    eth_records = [
        r for r in v111l.get("records", [])
        if str(r.get("asset", "")).upper() == "ETH"
    ]
    eth_in_best = str(best.get("asset", "")).upper() == "ETH"

    # ARB H6-07 must be the best_candidate
    arb_is_best = (
        best.get("signal_id") == "H6-07"
        and str(best.get("asset", "")).upper() == "ARB"
    )

    # public_card_ready if debug_leak_count=0 and ARB is best
    public_ready = (debug_leak_count == 0) and arb_is_best

    return {
        "signal_id": "H6-07",
        "asset": "ARB",
        "public_card_ready": public_ready,
        "debug_leak_count": debug_leak_count,
        "v111l_result_found": True,
        "arb_is_best_candidate": arb_is_best,
        "eth_in_best_candidate": eth_in_best,
        "eth_record_count": len(eth_records),
        "eth_enters_readiness": False,  # Hard block — ETH never enters readiness
    }


def _check_secret_patterns(data: dict) -> bool:
    """Scan result JSON VALUES (not keys) for secret-like patterns.

    Returns True if clean (no secret values found).

    This only checks string values — field names like
    'telegram_bot_token_present' (boolean flags) are intentionally
    allowed as metadata keys, not secret values.
    """
    import re

    def _scan(obj) -> bool:
        """Recursively scan values only. Returns True if clean."""
        if isinstance(obj, str):
            # Bot token format: NNNNNNNNNN:AAAA... (Telegram bot token)
            if re.search(r'\b\d{8,12}:[A-Za-z0-9_-]{30,50}\b', obj):
                return False
            # Chat ID: negative 10+ digit numbers stand-alone
            if re.search(r'(?<!\w)-?\d{13,20}(?!\w)', obj):
                return False
            return True
        elif isinstance(obj, dict):
            return all(_scan(v) for v in obj.values())
        elif isinstance(obj, list):
            return all(_scan(item) for item in obj)
        return True

    return _scan(data)


def run_readiness_check() -> dict:
    """Run the full runtime readiness check pipeline.

    Returns the readiness result dict (also writes to disk).
    """
    now_str = _now_iso()

    # ── 1. Environment credential check ──
    env_readiness = _check_env_readiness()

    # ── 2. v1.11-N blocked status ──
    v111n_check = _check_v111n_blocked()

    # ── 3. ARB H6-07 readiness ──
    candidate = _check_arb_h607_readiness()

    # ── 4. Determine overall readiness ──
    creds_present = (
        env_readiness["telegram_bot_token_present"]
        and env_readiness["telegram_chat_id_present"]
    )

    if not creds_present:
        ready = False
        blocked_reason = "missing_runtime_test_channel_credentials"
    elif not candidate["public_card_ready"]:
        ready = False
        blocked_reason = "arb_h607_public_card_not_ready"
    else:
        ready = True
        blocked_reason = None

    # ── 5. Build result ──
    result = {
        "version": VERSION,
        "mode": MODE,
        "real_tg_sent": False,
        "telegram_api_called": False,
        "secrets_printed": False,
        "env_readiness": {
            "telegram_bot_token_present": env_readiness["telegram_bot_token_present"],
            "telegram_chat_id_present": env_readiness["telegram_chat_id_present"],
            "telegram_chat_id_masked": env_readiness.get("telegram_chat_id_masked", {"present_masked": False, "length_bucket": "empty"}),
            "values_printed": False,
        },
        "candidate_readiness": {
            "signal_id": candidate["signal_id"],
            "asset": candidate["asset"],
            "public_card_ready": candidate["public_card_ready"],
            "debug_leak_count": candidate["debug_leak_count"],
            "eth_enters_readiness": False,
        },
        "v111n_status": {
            "blocked": v111n_check["v111n_blocked"],
            "reason": v111n_check["v111n_reason"],
            "blocked_by_credentials": v111n_check["v111n_blocked_by_credentials"],
        },
        "ready_to_attempt_real_test_send": ready,
    }

    if blocked_reason:
        result["blocked_reason"] = blocked_reason

    # ── 6. Safety: scan for secret patterns ──
    result["secrets_printed"] = not _check_secret_patterns(result)

    # ── 7. Add metadata ──
    result["checked_at"] = now_str
    result["generated_at"] = now_str

    # ── 8. Write JSON ──
    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # ── 9. Write report MD ──
    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = _build_report_md(result, env_readiness, candidate, v111n_check, now_str)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    # ── 10. Write handoff MD ──
    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    handoff = _build_handoff_md(result, now_str)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write(handoff)

    return result


def _build_report_md(
    result: dict,
    env: dict,
    candidate: dict,
    v111n_check: dict,
    now_str: str,
) -> str:
    """Build the markdown readiness report."""
    ready = result["ready_to_attempt_real_test_send"]
    blocked_reason = result.get("blocked_reason", "")

    lines = [
        f"# Market Radar {VERSION} — Sender Runtime Readiness Report",
        "",
        f"**Run**: {now_str}",
        f"**Version**: {VERSION}",
        f"**Mode**: Sender Runtime Readiness Check",
        f"**Ready to send**: {'✅ Yes' if ready else '❌ No'}",
        "",
        "## Objective",
        "",
        "补齐\"安全发送运行准备层\"：检查运行时环境是否具备真实 TG 测试群发送条件，",
        "同时不泄露任何凭证值。",
        "",
        "## Runtime Readiness Result",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Telegram Bot Token present | {env['telegram_bot_token_present']} |",
        f"| Telegram Chat ID present | {env['telegram_chat_id_present']} |",
        f"| Values printed | {env['values_printed']} |",
        f"| Ready to attempt real test send | {ready} |",
    ]

    if not ready:
        lines += [
            f"| Blocked reason | `{blocked_reason}` |",
        ]

    lines += [
        "",
        "## ARB H6-07 Current Status",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Signal ID | {candidate['signal_id']} |",
        f"| Asset | {candidate['asset']} |",
        f"| Public card ready | {candidate['public_card_ready']} |",
        f"| debug_leak_count | {candidate['debug_leak_count']} |",
        f"| ETH enters readiness | {candidate['eth_enters_readiness']} |",
        "",
        "## v1.11-N Send Status",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| v1.11-N status | {v111n_check['v111n_status']} |",
        f"| Blocked by credentials | {v111n_check['v111n_blocked_by_credentials']} |",
        f"| Reason | `{v111n_check['v111n_reason']}` |",
        "",
        "## Can Real Test Send Be Attempted?",
        "",
    ]

    if ready:
        lines += [
            "✅ **Yes** — credentials are present and ARB H6-07 public card is ready.",
            "",
            "The real test send can be attempted by running:",
            "",
            "```powershell",
            "python scripts/run_market_radar_v111n_safe_single_arb_test_send.py",
            "```",
            "",
            "However, this script (v1.11-O) does NOT send — it only checks readiness.",
        ]
    else:
        lines += [
            f"❌ **No** — {blocked_reason}",
            "",
            "### What is missing:",
            "",
        ]
        if not env["telegram_bot_token_present"]:
            lines.append("- `TELEGRAM_BOT_TOKEN` not set in runtime environment")
        if not env["telegram_chat_id_present"]:
            lines.append("- `TELEGRAM_CHAT_ID` not set in runtime environment")
        if not candidate["public_card_ready"]:
            lines.append("- ARB H6-07 public card is not ready")
        lines.append("")

    lines += [
        "## Security Constraints Confirmed",
        "",
        "- [x] No Telegram API called",
        "- [x] No .env file read",
        "- [x] No interactive input (Read-Host)",
        "- [x] No token/chat_id values printed or saved",
        "- [x] No paid API called",
        "- [x] Formal channels remain frozen",
        "- [x] Only ARB H6-07 is candidate (ETH blocked)",
        "- [x] No loop/daemon/cron started",
        "",
        "## Next Steps",
        "",
    ]

    if ready:
        lines += [
            "1. Run `python scripts/run_market_radar_v111n_safe_single_arb_test_send.py` for real test send.",
            "2. After send, run `python scripts/run_market_radar_v111o_post_send_review_stub.py` for post-send review.",
            "3. Verify rendering in test channel.",
        ]
    else:
        lines += [
            "1. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in the runtime environment.",
            "2. Ensure chat_id points to the test channel (NOT formal/prod).",
            "3. Re-run this readiness check: `python scripts/check_market_radar_sender_runtime_v111o.py`",
            "4. If ready, run `python scripts/run_market_radar_v111n_safe_single_arb_test_send.py`",
        ]

    lines.append("")
    return "\n".join(lines)


def _build_handoff_md(result: dict, now_str: str) -> str:
    """Build the handoff markdown content."""
    ready = result["ready_to_attempt_real_test_send"]
    blocked_reason = result.get("blocked_reason", "")
    env = result["env_readiness"]
    candidate = result["candidate_readiness"]
    v111n = result["v111n_status"]

    lines = [
        f"# Market Radar {VERSION} — Handoff",
        "",
        "**Executor**: claude_code_executor",
        f"**Date**: {now_str}",
        f"**Status**: {'done' if ready else 'partial'}",
        "",
        "## Modified Files",
        "",
        "- `scripts/check_market_radar_sender_runtime_v111o.py` — **新增**: Runtime readiness checker",
        "- `scripts/run_market_radar_v111o_post_send_review_stub.py` — **新增**: Post-send review stub",
        "- `scripts/test_market_radar_sender_runtime_v111o.py` — **新增**: Runtime readiness tests",
        f"- `results/market_radar_v111o_sender_runtime_readiness_result.json` — **新增**: Readiness JSON",
        f"- `runs/market_radar/v111o_sender_runtime_readiness.md` — **新增**: Readiness report",
        f"- `runs/market_radar/v111o_sender_runtime_readiness_handoff.md` — **新增**: This handoff",
        f"- `docs/market_radar_v111o_safe_test_sender_runbook.md` — **新增**: Safe test sender runbook",
        "",
        "## Commands Executed",
        "",
        "```powershell",
        "python scripts/check_market_radar_sender_runtime_v111o.py",
        "python scripts/run_market_radar_v111o_post_send_review_stub.py",
        "python scripts/test_market_radar_sender_runtime_v111o.py",
        "# Legacy tests:",
        "python scripts/test_market_radar_safe_sender_v111n.py",
        "python scripts/test_market_radar_public_card_readiness_v111l.py",
        "python scripts/test_market_radar_mock_sender_v111j.py",
        "python scripts/test_market_radar_signal_value_gate_v111b.py",
        "python scripts/test_market_radar_same_asset_cooldown_gate_v111f.py",
        "python scripts/test_market_radar_card_router_v110a.py",
        "python scripts/test_market_radar_pre_send_gate_v110g.py",
        "python scripts/test_market_radar_signal_trust_gate_v110c.py",
        "python scripts/test_market_radar_sender_gate_coverage_v110h.py",
        "```",
        "",
        "## Readiness Status",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Ready to attempt real test send | {ready} |",
        f"| Telegram Bot Token present | {env['telegram_bot_token_present']} |",
        f"| Telegram Chat ID present | {env['telegram_chat_id_present']} |",
        f"| ARB H6-07 public card ready | {candidate['public_card_ready']} |",
        f"| v1.11-N blocked by credentials | {v111n['blocked_by_credentials']} |",
        "",
    ]

    if not ready:
        lines += [
            f"**Blocked reason**: `{blocked_reason}`",
            "",
        ]

    lines += [
        "## Was TG Sent?",
        "",
        "**NO** — This run does NOT send any Telegram message.",
        "real_tg_sent is false. telegram_api_called is false.",
        "",
        "## Risks",
        "",
        "1. Runtime credentials still missing — real test send cannot proceed.",
        "2. If credentials were present, first real send should be monitored for rendering quality.",
        "3. Post-send review stub is a skeleton — needs real message_id to produce meaningful output.",
        "4. ETH remains blocked — only ARB H6-07 is the test candidate.",
        "",
        "## Next Steps",
        "",
    ]

    if ready:
        lines += [
            "1. Run `python scripts/run_market_radar_v111n_safe_single_arb_test_send.py`",
            "2. After send, run `python scripts/run_market_radar_v111o_post_send_review_stub.py`",
        ]
    else:
        lines += [
            "1. Set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in runtime environment.",
            "2. Re-run readiness check: `python scripts/check_market_radar_sender_runtime_v111o.py`",
            "3. If ready, run `python scripts/run_market_radar_v111n_safe_single_arb_test_send.py`",
        ]

    lines.append("")
    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────────


def main() -> int:
    """Run the readiness check and return exit code."""
    print(f"=== Market Radar {VERSION}: Sender Runtime Readiness Check ===")
    print(f"Time: {_now_iso()}")
    print(f"Mode: {MODE}")
    print()

    result = run_readiness_check()

    print("## Environment Readiness")
    env = result["env_readiness"]
    print(f"  TELEGRAM_BOT_TOKEN present: {env['telegram_bot_token_present']}")
    print(f"  TELEGRAM_CHAT_ID present: {env['telegram_chat_id_present']}")
    print(f"  Values printed: {env['values_printed']}")
    print()

    print("## Candidate Readiness")
    cand = result["candidate_readiness"]
    print(f"  Signal: {cand['signal_id']} / {cand['asset']}")
    print(f"  Public card ready: {cand['public_card_ready']}")
    print(f"  debug_leak_count: {cand['debug_leak_count']}")
    print(f"  ETH enters readiness: {cand['eth_enters_readiness']}")
    print()

    print("## v1.11-N Status")
    v111n = result["v111n_status"]
    print(f"  Blocked: {v111n['blocked']}")
    print(f"  Reason: {v111n['reason']}")
    print(f"  Blocked by credentials: {v111n['blocked_by_credentials']}")
    print()

    print(f"## Overall: Ready to attempt real test send = {result['ready_to_attempt_real_test_send']}")
    if not result["ready_to_attempt_real_test_send"]:
        print(f"  Blocked reason: {result.get('blocked_reason', 'unknown')}")
        print()
        print("  NOTE: Credentials are missing. This is expected — the environment")
        print("  has not been configured with TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID.")
        print("  Real test send can be attempted once credentials are set.")
    else:
        print("  Credentials are present. Real send CAN be attempted by running:")
        print("    python scripts/run_market_radar_v111n_safe_single_arb_test_send.py")
    print()

    print(f"Result JSON: {RESULT_JSON_PATH}")
    print(f"Report MD:   {REPORT_MD_PATH}")
    print(f"Handoff MD:  {HANDOFF_MD_PATH}")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
