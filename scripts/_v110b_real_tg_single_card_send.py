"""
Market Radar v1.10-B — Real TG Test Group Single Card Send
v1.10-C update: SignalTrustGate wired before TG send.

Follows the existing TGTransport / RealHttpClient / MarketRadarSender component chain.
Uses render_card_payload(signal) for safe payload generation.
MarkdownV2 first, fallback to plain text on failure (max 1 retry).

v1.10-C Gate: SignalTrustGate.check() runs between render_card_payload() and TG send.
If gate blocks, sends STOP and writes blocked report.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Handle Windows console encoding for emoji
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_card_router import (
    classify_signal_type,
    render_card,
    render_card_payload,
    render_error_card,
)
from scripts.market_radar_sender import (
    MarketRadarSender,
    TGTransport,
    RealHttpClient,
)
from scripts.market_radar_signal_trust_gate import (
    SignalTrustGate,
    write_blocked_report,
    GATE_VERSION as TRUST_GATE_VERSION,
)

CN_TZ = timezone(timedelta(hours=8))
TASK_ID = "20260604_154132.r01"
RUN_ID = "20260604_154132"
NOW_STR = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

# ── v1.10-C: Signal Trust Gate control ──
ACTUALLY_SEND_TG = False   # v1.10-C: gate verification only, no real send
TARGET_ENV = "test"        # Default target env for gate check

# ── Load credentials from environment (set by load_local_secrets.ps1) ──
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
PROXY_URL = os.environ.get("TELEGRAM_PROXY_URL", None)

if not BOT_TOKEN or not CHAT_ID:
    print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in environment.")
    print("Run load_local_secrets.ps1 first to set these variables.")
    sys.exit(1)

# ── Helper functions ────────────────────────────────────────────────────────
def _write_blocked_handoff(reason: str):
    """Write a blocked handoff when no signal is available."""
    handoff_path = ROOT / "runs" / "market_radar" / "v110b_real_tg_single_card_handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""# Market Radar v1.10-B — Blocked Handoff

Generated: {NOW_STR}
Status: blocked
Reason: {reason}
"""
    with open(handoff_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Blocked handoff written: {handoff_path}")


def _write_gate_handoff(signal: dict, payload: dict, gate_result: dict, gate_blocked: bool):
    """Write v1.10-C gate check handoff (no TG send)."""
    handoff_path = ROOT / "runs" / "market_radar" / "v110c_signal_trust_gate_handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)

    status_str = "blocked" if gate_blocked else "passed"
    card_type = payload.get("card_type", "?")
    text = payload.get("text", "")
    asset = signal.get("asset", "?")
    source = signal.get("source", "?")

    safe_preview = text[:300] if text else ""

    content = f"""# Market Radar v1.10-C — Signal Trust Gate Handoff

Generated: {NOW_STR}
Task ID: {TASK_ID}
Run ID: {RUN_ID}
Status: gate_{status_str}
result_source: claude_code_executor
gate_version: {TRUST_GATE_VERSION}
executor_lane: 1
project_label: market_radar

---

## 1. Gate Check Summary

| Field | Value |
|-------|-------|
| Gate 是否实现 | 是 |
| 是否接入发送前检查 | 是 |
| Gate 接入位置 | render_card_payload(signal) 之后、TG send 之前 |
| 是否修改 live fetch | 否 |
| 是否真实发送 TG | 否 (ACTUALLY_SEND_TG=False) |
| 是否启动后台循环 | 否 |
| 是否使用付费 API | 否 |
| 是否读取/打印密钥 | 否 |

## 2. Gate Result

| Field | Value |
|-------|-------|
| allowed | {gate_result['allowed']} |
| source_type | {gate_result['source_type']} |
| signal_type | {gate_result['signal_type']} |
| signal_hash | {gate_result['signal_hash']} |
| ttl_seconds | {gate_result['ttl_seconds']} |
| age_seconds | {gate_result['age_seconds']} |
| blocked_reason | {gate_result.get('blocked_reason', 'N/A')} |
| target_env | {gate_result['target_env']} |
| checked_at | {gate_result.get('checked_at', 'N/A')} |

## 3. Signal Info

| Field | Value |
|-------|-------|
| asset | {asset} |
| source | {source} |
| card_type | {card_type} |

## 4. Source Trust Map Summary

| source_type | allow_test_send | allow_prod_send |
|-------------|-----------------|-----------------|
| api | True | True |
| real | True | True |
| external | True | True |
| fixture | True | False |
| manual | True | False |
| unknown | False | False |
| stale | False | False |

## 5. TTL Rules Summary

| signal_type | ttl_seconds |
|-------------|-------------|
| market_anomaly | 900 (15 min) |
| whale / whale_transfer | 3600 (60 min) |
| onchain / onchain_position | 3600 (60 min) |
| news / news_event | 21600 (6 hours) |
| macro | 21600 (6 hours) |
| position | 1800 (30 min) |
| liquidation | 1800 (30 min) |
| combo | 1800 (30 min) |
| risk_alert | 900 (15 min) |
| unknown | 0 (block immediately) |

## 6. Blocked Report

- Path: runs/market_radar/v110c_signal_trust_gate_blocked_report.jsonl
- Fields: gate_version, signal_id, signal_hash, signal_type, source_type, generated_at, checked_at, ttl_seconds, age_seconds, blocked_reason, target_env
- No token/key/cookie/password/chat_id in report

## 7. Card Text Preview (max 300 chars)

```
{safe_preview}
```

---

## 8. Unfinished Items / Risks

{"- Signal was blocked by Trust Gate. Reason: " + str(gate_result.get('blocked_reason')) if gate_blocked else "- None — gate passed successfully."}
- TG send was NOT attempted (v1.10-C is gate verification only).
- Next step (v1.10-D): re-enable TG send with gate active.
- No live fetch modified. No sender refactored.

---

⚠️ 仅供观察，不构成交易建议。
"""
    with open(handoff_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Gate handoff written: {handoff_path}")


print(f"=== Market Radar v1.10-C: Signal Trust Gate Verification ===")
print(f"Time: {NOW_STR}")
print(f"Task ID: {TASK_ID}")
print(f"Credentials: from environment (not printed)")
print(f"Proxy: {'configured' if PROXY_URL else 'not configured'}")
print()

# ── Step 1: Select the real market_anomaly signal ──
print("Step 1: Loading signals and selecting market_anomaly card...")
signals_path = ROOT / "results" / "market_radar_v110a_free_signals.json"
with open(signals_path, "r", encoding="utf-8") as f:
    signals_data = json.load(f)

all_signals = signals_data.get("signals", [])

# Select standalone market_anomaly signals with status=ok and source_type=api
candidates = []
for s in all_signals:
    st = s.get("signal_type", "")
    status = s.get("status", "")
    source_type = s.get("source_type", "")
    if st == "market_anomaly" and status == "ok" and source_type == "api":
        candidates.append(s)

if not candidates:
    print("  [BLOCKED] No real market_anomaly signal found with source_type=api")
    # Write blocked handoff
    _write_blocked_handoff("No real market_anomaly signal with source_type=api available")
    sys.exit(0)

# Sort by abs(price_change_pct) descending — pick most impactful
candidates.sort(key=lambda s: abs(float(s.get("price_change_pct", 0))), reverse=True)
selected = candidates[0]

asset = selected.get("asset", "?")
price_change = selected.get("price_change_pct", 0)
source = selected.get("source", "?")
source_type = selected.get("source_type", "?")
core_entity = selected.get("core_entity", "?")

print(f"  Selected: {asset} market_anomaly")
print(f"  Price change: {price_change}%")
print(f"  Source: {source} (type={source_type})")
print(f"  Status: {selected.get('status')}")
print()

# ── Step 2: Generate safe payload via render_card_payload() ──
print("Step 2: Generating safe payload via render_card_payload(signal)...")
payload = render_card_payload(selected)
card_type = payload.get("card_type", "?")
text = payload["text"]
parse_mode = payload["parse_mode"]
fallback_used = payload.get("fallback_used", False)
warnings = payload.get("warnings", [])

print(f"  card_type: {card_type}")
print(f"  parse_mode: {parse_mode}")
print(f"  fallback_used (initial): {fallback_used}")
print(f"  warnings: {warnings}")
print(f"  text length: {len(text)} chars")
# Preview (safe, no credentials)
preview = text[:200].replace("\n", "\\n")
try:
    print(f"  text preview: {preview}...")
except UnicodeEncodeError:
    # Fall back to ASCII-safe preview
    safe_preview_print = preview.encode("ascii", errors="replace").decode("ascii")
    print(f"  text preview (ascii-safe): {safe_preview_print}...")
print()

# ── Step 2.5 (v1.10-C): Signal Trust Gate — last check before TG send ──
print("Step 2.5: SignalTrustGate check (v1.10-c)...")
print(f"  Gate version: {TRUST_GATE_VERSION}")
print(f"  Target env: {TARGET_ENV}")

gate = SignalTrustGate()
gate_result = gate.check(selected, target_env=TARGET_ENV)

print(f"  allowed: {gate_result['allowed']}")
print(f"  source_type: {gate_result['source_type']}")
print(f"  signal_type: {gate_result['signal_type']}")
print(f"  signal_hash: {gate_result['signal_hash']}")
print(f"  ttl_seconds: {gate_result['ttl_seconds']}")
print(f"  age_seconds: {gate_result['age_seconds']}")
print(f"  blocked_reason: {gate_result['blocked_reason']}")

gate_blocked = not gate_result["allowed"]

if gate_blocked:
    print(f"\n  [BLOCKED] Signal blocked by Trust Gate: {gate_result['blocked_reason']}")
    write_blocked_report(gate_result)
    print(f"  Blocked report written.")

    if not ACTUALLY_SEND_TG:
        print(f"  v1.10-C dry-run: gate blocked signal, no TG send attempted.")
        # Still write result but with gate_blocked status
        gate_blocked_result = {
            "status": "blocked",
            "gate_blocked": True,
            "gate_result": gate_result,
            "actually_send_tg": False,
            "gate_version": TRUST_GATE_VERSION,
            "component_version": "v1.10-C",
        }
        # Write gate-only result and exit
        _write_gate_handoff(selected, payload, gate_result, gate_blocked=True)
        print()
        print("=" * 60)
        print(f"=== v1.10-C GATE CHECK COMPLETE (BLOCKED) ===")
        print(f"Signal blocked by Trust Gate — no TG send attempted.")
        print(f"Gate version: {TRUST_GATE_VERSION}")
        print("AI_RELAY_SUMMARY:" + json.dumps(gate_blocked_result, ensure_ascii=False))
        sys.exit(0)
    else:
        print(f"  ACTUALLY_SEND_TG=True but gate blocked — exiting.")
        sys.exit(1)
else:
    print(f"  [PASS] Signal cleared Trust Gate.")

if not ACTUALLY_SEND_TG:
    print(f"  v1.10-C dry-run: gate passed, but TG send disabled (ACTUALLY_SEND_TG=False).")
    print(f"  Recording gate-pass result without sending.")
    _write_gate_handoff(selected, payload, gate_result, gate_blocked=False)
    print()
    print("=" * 60)
    print(f"=== v1.10-C GATE CHECK COMPLETE (PASSED, NO TG SEND) ===")
    print(f"Signal Trust Gate: PASSED")
    print(f"TG send: NOT attempted (Gate verification mode)")
    print(f"Gate version: {TRUST_GATE_VERSION}")
    gate_pass_result = {
        "status": "done",
        "gate_blocked": False,
        "gate_result": gate_result,
        "actually_send_tg": False,
        "gate_version": TRUST_GATE_VERSION,
        "component_version": "v1.10-C",
    }
    print("AI_RELAY_SUMMARY:" + json.dumps(gate_pass_result, ensure_ascii=False))
    sys.exit(0)
print()

# ── Step 3: Build transport ──
print("Step 3: Building TGTransport with RealHttpClient...")

if PROXY_URL:
    http_client = RealHttpClient(timeout=10, proxy_url=PROXY_URL)
    print(f"  RealHttpClient(timeout=10, proxy_url=EXPLICIT)")
else:
    http_client = RealHttpClient(timeout=10)
    print(f"  RealHttpClient(timeout=10, no proxy)")

transport = TGTransport(
    bot_token=BOT_TOKEN,
    default_chat_id=CHAT_ID,
    http_client=http_client,
    timeout_seconds=10,
)
print(f"  TGTransport created (credentials from env, not printed)")
print(f"  Target: test group / supergroup (NOT channel)")
print()

sender = MarketRadarSender(transport=transport)
print(f"  MarketRadarSender ready")
print()

# ── Step 4: Send (MarkdownV2 first) ──
print("Step 4: Sending with MarkdownV2...")
send_payload = {
    "text": text,
    "parse_mode": parse_mode or "MarkdownV2",
    "disable_web_page_preview": True,
}

# Use TGTransport.send() directly for single-card send
attempt = 1
max_attempts = 2  # 1 MarkdownV2 + 1 plain text fallback
result = None
actual_parse_mode = parse_mode or "MarkdownV2"
actual_fallback = fallback_used

for attempt in range(1, max_attempts + 1):
    current_parse_mode = actual_parse_mode
    current_text = text

    print(f"\n  --- Attempt {attempt}/{max_attempts} ---")
    print(f"  parse_mode: {current_parse_mode}")

    transport_payload = {
        "text": current_text,
        "disable_web_page_preview": True,
    }

    result = transport.send(
        transport_payload,
        target="supergroup",
        parse_mode=current_parse_mode,
    )

    print(f"  success: {result.success}")
    print(f"  status: {result.status}")
    print(f"  status_code: {result.status_code}")
    print(f"  error_type: {result.error_type}")
    print(f"  error_message: {result.error_message}")

    if result.success:
        actual_fallback = (attempt > 1)
        break

    # If MarkdownV2 failed, try plain text
    if attempt == 1 and not result.success:
        print(f"\n  MarkdownV2 failed, falling back to plain text...")
        actual_parse_mode = None  # Plain text
        actual_fallback = True
        # Use unescaped plain text directly (original render before MarkdownV2 escaping)
        plain_text = render_card(selected)
        text = plain_text
    else:
        # Second attempt failed too — stop
        break

print()

# ── Step 5: Record results ──
print("=" * 60)
print(f"=== SEND RESULT ===")
print(f"  success: {result.success}")
print(f"  sent_count: {result.sent_count}")
print(f"  message_id: {result.message_id}")
print(f"  tg_api_called: {result.tg_api_called}")
print(f"  target_type: {result.target_type}")
print(f"  sent_channel: {result.sent_channel}")
print(f"  sent_exceed_1: {result.sent_exceed_1}")
print(f"  loop_started: {result.loop_started}")
print(f"  sensitive_printed: {result.sensitive_printed}")
print(f"  status_code: {result.status_code}")
print(f"  error_type: {result.error_type}")
print(f"  error_message: {result.error_message}")
print(f"  retry_after: {result.retry_after}")
print(f"  provider: {result.provider}")
print(f"  attempts: {attempt}")
print(f"  fallback_used: {actual_fallback}")
print(f"  card_type: {card_type}")
print(f"  core_entity: {core_entity}")
print(f"  source_type: {source_type}")
print()

# ── Redaction verification ──
pm = result.provider_metadata
req_preview = pm.get("request_payload_preview", {})
preview_str = json.dumps(req_preview, ensure_ascii=False)
has_token = BOT_TOKEN in preview_str
has_chat_id = CHAT_ID in preview_str
print(f"=== Redaction Check ===")
print(f"  bot_token leaked in metadata: {has_token}")
print(f"  full chat_id leaked in metadata: {has_chat_id}")
print()

# ── Step 6: Write output files ──
print("Step 6: Writing output files...")

# Determine status
if result.success:
    final_status = "done"
elif result.tg_api_called:
    final_status = "partial"
else:
    final_status = "failed"

# 6a: Send result JSON
result_json_path = ROOT / "results" / "market_radar_v110b_real_tg_send_result.json"
result_dict = result.to_dict()
result_dict.update({
    "generated_at": NOW_STR,
    "component_version": "v1.10-B",
    "executor_lane": 1,
    "project_label": "market_radar",
    "task_id": TASK_ID,
    "run_id": RUN_ID,
    "card_type": card_type,
    "core_entity": core_entity,
    "source_type": source_type,
    "parse_mode_initial": parse_mode,
    "parse_mode_final": actual_parse_mode,
    "fallback_used": actual_fallback,
    "warnings": warnings,
    "attempts": attempt,
    "provider_metadata_redacted": not has_token and not has_chat_id,
    "component_chain": [
        "render_card_payload()",
        "TGTransport.send()",
        "RealHttpClient",
        "SendResult",
    ],
})
result_json_path.parent.mkdir(parents=True, exist_ok=True)
with open(result_json_path, "w", encoding="utf-8") as f:
    json.dump(result_dict, ensure_ascii=False, indent=2, fp=f)
print(f"  Written: {result_json_path}")

# 6b: Handoff markdown (for AI Relay Desk)
handoff_md_path = ROOT / "runs" / "market_radar" / "v110b_real_tg_single_card_handoff.md"
handoff_md_path.parent.mkdir(parents=True, exist_ok=True)

# Safe text preview (max 500 chars, no credentials)
safe_preview = text[:500]
# Double check no secrets in preview
for secret_name in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
    secret_val = os.environ.get(secret_name, "")
    if secret_val and secret_val in safe_preview:
        safe_preview = safe_preview.replace(secret_val, "[REDACTED]")

handoff_md = f"""# Market Radar v1.10-B — Real TG Test Group Single Card Send Handoff

Generated: {NOW_STR}
Task ID: {TASK_ID}
Run ID: {RUN_ID}
Status: {final_status}
result_source: claude_code_executor
executor_lane: 1
project_label: market_radar

---

## 1. Send Summary

| Field | Value |
|-------|-------|
| 是否真实发送 TG | {"是" if result.tg_api_called else "否"} |
| blocked 原因 | {"N/A" if result.tg_api_called else (result.error_message or "No real signal available")} |
| 目标 | TG 测试群 / supergroup |
| 是否正式频道 | 否 |
| card_type | {card_type} |
| core_entity | {core_entity} |
| source_type | {source_type} |
| parse_mode (initial) | {parse_mode} |
| parse_mode (final) | {actual_parse_mode} |
| fallback_used | {actual_fallback} |
| warnings | {json.dumps(warnings, ensure_ascii=False)} |
| message_id | {result.message_id if result.message_id else "N/A"} |
| sent_count | {result.sent_count} |
| attempts | {attempt} |
| 是否使用付费 API | 否 |
| 是否启动后台循环 | 否 |
| 是否读取/打印密钥 | 否 |
| 是否泄露 token | {"是 ** LEAK **" if has_token else "否"} |
| status_code | {result.status_code} |
| error_type | {result.error_type if result.error_type else "N/A"} |
| error_message | {result.error_message if result.error_message else "N/A"} |

---

## 2. Component Chain

| Step | Component | Used |
|------|-----------|------|
| 1 | Live fetch (run_market_radar_v110a_free_cards.py) | Yes |
| 2 | Signal selection (market_anomaly, source_type=api) | Yes |
| 3 | render_card_payload(signal) | Yes |
| 4 | TGTransport + RealHttpClient | Yes |
| 5 | MarketRadarSender | Indirect (TGTransport.send() used directly) |
| 6 | MarkdownV2 → Plain Text fallback | {"Triggered" if actual_fallback else "Not triggered"} |
| 7 | Redaction verification | {"PASS" if not has_token and not has_chat_id else "FAIL"} |

---

## 3. Safety Boundary Verification

| Constraint | Status |
|------------|--------|
| Sent to channel | No (target is supergroup/test group) |
| Sent > 1 message | No (sent_count = {result.sent_count}) |
| Loop/daemon/cron started | No |
| Token/chat_id printed in output | No |
| Full API URL printed | No |
| Remote DB written | No |
| Production written | No |
| Paid API called | No |
| Files deleted | No |
| New sender architecture added | No (reused TGTransport) |
| Env vars used for credentials | Yes (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) |
| provider_metadata redacted | {"Yes" if not has_token and not has_chat_id else "** LEAK **"} |

---

## 4. Acceptance Checklist

| Item | Status |
|------|--------|
| TG 测试群真实收到 1 张 Market Radar 卡片 | {"Yes" if result.success else "No"} |
| 真实 message_id 返回 | {"Yes" if result.message_id else "No"} |
| 发送路径使用 render_card_payload(signal) | Yes |
| 发送参数使用 payload["text"] 和 payload["parse_mode"] | Yes |
| fallback 触发时记录 fallback_used=True | {"Yes" if actual_fallback else "N/A (fallback not triggered)"} |
| 不泄露任何密钥或完整 chat_id | {"Yes" if not has_token and not has_chat_id else "No"} |
| 不发正式频道 | Yes |
| 不启动后台循环 | Yes |
| 生成完整 handoff 文件 | Yes |

---

## 5. 发送文本预览 (max 500 chars)

```
{safe_preview}
```

---

## 6. 下一步建议

{"- TG test group send successful with message_id={result.message_id}. Next: validate the card formatting in the TG group (MarkdownV2 rendering, link clickability, emoji display)." if result.success else "- Send failed. Diagnose error: " + str(result.error_type) + " - " + str(result.error_message) + ". Check bot token validity and chat membership."}

---

## 7. Unfinished Items / Risks

{"- None" if result.success else "- Send failed with error_type=" + str(result.error_type) + ": " + str(result.error_message)}
- This is a single-card test send. Full batch sending is NOT enabled.
- MarkdownV2 escaping for Telegram special characters is handled by escape_markdown_v2().
- No bulk send, no loop, no daemon — one-shot execution complete.

---
⚠️ 仅供观察，不构成交易建议。
"""

with open(handoff_md_path, "w", encoding="utf-8") as f:
    f.write(handoff_md)
print(f"  Written: {handoff_md_path}")

# 6c: Also write timestamped copy
handoff_ts_path = ROOT / "runs" / "market_radar" / f"v110b_real_tg_single_card_handoff_{RUN_ID}.md"
with open(handoff_ts_path, "w", encoding="utf-8") as f:
    f.write(handoff_md)
print(f"  Written: {handoff_ts_path}")

print()
print("=" * 60)
print(f"=== v1.10-B EXECUTION COMPLETE ===")
print(f"Final status: {final_status}")
print(f"Success: {result.success}")
print(f"Message ID: {result.message_id}")
print(f"Fallback used: {actual_fallback}")
print(f"TG API called: {result.tg_api_called}")

# Output JSON summary for AI Relay Desk
summary = {
    "status": final_status,
    "success": result.success,
    "sent_count": result.sent_count,
    "message_id": result.message_id,
    "target_type": result.target_type,
    "tg_api_called": result.tg_api_called,
    "sent_channel": result.sent_channel,
    "sent_exceed_1": result.sent_exceed_1,
    "loop_started": result.loop_started,
    "sensitive_printed": result.sensitive_printed,
    "card_type": card_type,
    "core_entity": core_entity,
    "source_type": source_type,
    "parse_mode_initial": parse_mode,
    "parse_mode_final": actual_parse_mode,
    "fallback_used": actual_fallback,
    "warnings": warnings,
    "error_type": result.error_type,
    "error_message": result.error_message,
    "provider_metadata_redacted": not has_token and not has_chat_id,
    "attempts": attempt,
}
print("AI_RELAY_SUMMARY:" + json.dumps(summary, ensure_ascii=False))
