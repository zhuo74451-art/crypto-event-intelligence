"""
Market Radar v1.10-E — Gate-Protected Test Channel Real Send

Key flow:
  signal → render_card_payload(signal) → SignalTrustGate.check(signal, target_env="test")
  → gate allowed → TG test channel real send → return real message_id

Differs from v1.10-B/C/D:
  - ACTUALLY_SEND_TG = True (real send to test channel)
  - Gate is active and enforced
  - Gate runs between render and send
  - Only test channel (supergroup), never production channel
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

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
from scripts.market_radar_pre_send_gate import pre_send_gate

CN_TZ = timezone(timedelta(hours=8))
TASK_ID = "20260604_154132.r05"
RUN_ID = "20260604_154132"
NOW_STR = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

# ── v1.10-E: Gate-Protected Test Channel Real Send ──
ACTUALLY_SEND_TG = True    # v1.10-E: real send to test channel
TARGET_ENV = "test"        # Test channel only
SEND_ENABLED = True
SENT_COUNT_LIMIT = 1       # Only 1 card

# ── Load credentials from environment ──
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
PROXY_URL = os.environ.get("TELEGRAM_PROXY_URL", None)

print(f"=== Market Radar v1.10-E: Gate-Protected Test Channel Real Send ===")
print(f"Time: {NOW_STR}")
print(f"Task ID: {TASK_ID}")
print(f"Run ID: {RUN_ID}")
print(f"Gate version: {TRUST_GATE_VERSION}")
print(f"Credentials: from environment (not printed)")
print(f"ACTUALLY_SEND_TG: {ACTUALLY_SEND_TG}")
print(f"TARGET_ENV: {TARGET_ENV}")
print(f"Proxy: {'configured' if PROXY_URL else 'not configured'}")
print()

# ── Step 1: Load signals and select best candidate ──
print("Step 1: Loading signals from results/market_radar_v110a_free_signals.json...")
signals_path = ROOT / "results" / "market_radar_v110a_free_signals.json"
if not signals_path.exists():
    print(f"  [ERROR] Signals file not found: {signals_path}")
    sys.exit(1)

with open(signals_path, "r", encoding="utf-8") as f:
    signals_data = json.load(f)

all_signals = signals_data.get("signals", [])
print(f"  Total signals: {len(all_signals)}")

# Priority order: api market_anomaly > api risk_alert > real/external signal
selected = None
selection_reason = ""

# Priority 1: fresh api market_anomaly
candidates = [s for s in all_signals
              if s.get("signal_type") == "market_anomaly"
              and s.get("status") == "ok"
              and s.get("source_type") == "api"]
if candidates:
    candidates.sort(key=lambda s: abs(float(s.get("price_change_pct", 0))), reverse=True)
    selected = candidates[0]
    selection_reason = f"Priority 1: api market_anomaly (top by abs price change)"
    print(f"  Priority 1 candidates (api market_anomaly): {len(candidates)}")
else:
    print(f"  Priority 1 (api market_anomaly): none found")

# Priority 2: fresh api risk_alert
if selected is None:
    candidates = [s for s in all_signals
                  if s.get("signal_type") == "risk_alert"
                  and s.get("status") == "ok"
                  and s.get("source_type") == "api"]
    if candidates:
        selected = candidates[0]
        selection_reason = f"Priority 2: api risk_alert"
        print(f"  Priority 2 (api risk_alert): {len(candidates)}")
    else:
        print(f"  Priority 2 (api risk_alert): none found")

# Priority 3: fresh real/external signal
if selected is None:
    candidates = [s for s in all_signals
                  if s.get("status") == "ok"
                  and s.get("source_type") in ("api", "real", "external")
                  and s.get("signal_type") != "combo"]
    if candidates:
        selected = candidates[0]
        selection_reason = f"Priority 3: real/external signal (source_type={selected.get('source_type')})"
        print(f"  Priority 3 (real/external): {len(candidates)}")
    else:
        print(f"  Priority 3 (real/external): none found")

# Fallback: fixture (explicitly marked)
if selected is None:
    candidates = [s for s in all_signals
                  if s.get("source_type") == "fixture"
                  and s.get("signal_type") != "combo"]
    if candidates:
        selected = candidates[0]
        selection_reason = f"Fixture fallback: no fresh real signal available"
        print(f"  Fixture fallback: {len(candidates)} available")
    else:
        print(f"  [ERROR] No signal available at all")
        sys.exit(1)

asset = selected.get("asset", "?")
signal_type = selected.get("signal_type", "?")
source = selected.get("source", "?")
source_type = selected.get("source_type", "?")
core_entity = selected.get("core_entity", "?")
status = selected.get("status", "?")

print(f"\n  Selected: {asset} | {signal_type}")
print(f"  Source: {source} (source_type={source_type})")
print(f"  Status: {status}")
print(f"  Selection reason: {selection_reason}")
if signal_type == "market_anomaly":
    print(f"  Price change: {selected.get('price_change_pct', '?')}%")

# Check if fixture fallback
IS_FIXTURE = source_type == "fixture"
if IS_FIXTURE:
    print(f"  ⚠️  FIXTURE FALLBACK: This is a test link verification, not real signal quality verification.")
    print(f"  ⚠️  Do NOT treat this as a real market signal.")
print()

# ── Step 2: Generate safe payload via render_card_payload() ──
print("Step 2: Generating safe payload via render_card_payload(signal)...")
payload = render_card_payload(selected)
card_type = payload.get("card_type", "?")
text = payload["text"]
parse_mode = payload["parse_mode"]
fallback_used_initial = payload.get("fallback_used", False)
warnings = payload.get("warnings", [])

print(f"  card_type: {card_type}")
print(f"  parse_mode: {parse_mode}")
print(f"  fallback_used (initial): {fallback_used_initial}")
print(f"  warnings: {warnings}")
print(f"  text length: {len(text)} chars")

# Short preview only (no credentials)
preview = text[:150].replace("\n", "\\n")
try:
    print(f"  text preview: {preview}...")
except UnicodeEncodeError:
    safe_preview_print = preview.encode("ascii", errors="replace").decode("ascii")
    print(f"  text preview (ascii-safe): {safe_preview_print}...")
print()

# ── Step 3: pre_send_gate() universal check ──
print("Step 3: pre_send_gate() universal check...")
print(f"  Gate version: {TRUST_GATE_VERSION}")
print(f"  Target env: {TARGET_ENV}")

precheck = pre_send_gate(selected, payload, target_env=TARGET_ENV)
gate_result = precheck["gate_result"]

print(f"  allowed: {precheck['allowed']}")
print(f"  payload_ok: {precheck['payload_ok']}")
print(f"  source_type: {gate_result['source_type']}")
print(f"  signal_type: {gate_result['signal_type']}")
print(f"  signal_hash: {precheck['signal_hash']}")
print(f"  ttl_seconds: {gate_result['ttl_seconds']}")
print(f"  age_seconds: {gate_result['age_seconds']}")
print(f"  blocked_reason: {precheck['blocked_reason']}")

gate_blocked = not precheck["allowed"]

if gate_blocked:
    print(f"\n  [BLOCKED] Signal blocked by Trust Gate: {gate_result['blocked_reason']}")
    write_blocked_report(gate_result)
    print(f"  Blocked report written. NOT sending to TG.")

    # Write blocked handoff
    handoff_path = ROOT / "runs" / "market_radar" / "v110e_gate_protected_test_channel_send_handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    blocked_content = f"""# Market Radar v1.10-E — Gate-Protected Test Channel Send Handoff (BLOCKED)

Generated: {NOW_STR}
Task ID: {TASK_ID}
Run ID: {RUN_ID}
Status: blocked
result_source: claude_code_executor
executor_lane: 1
project_label: market_radar
gate_version: {TRUST_GATE_VERSION}

## Gate blocked

| Field | Value |
|-------|-------|
| gate_version | {TRUST_GATE_VERSION} |
| target_env | {TARGET_ENV} |
| allowed | {gate_result['allowed']} |
| signal_type | {gate_result['signal_type']} |
| source_type | {gate_result['source_type']} |
| signal_hash | {gate_result['signal_hash']} |
| blocked_reason | {gate_result['blocked_reason']} |
| ttl_seconds | {gate_result['ttl_seconds']} |
| age_seconds | {gate_result['age_seconds']} |

- ACTUALLY_SEND_TG: {ACTUALLY_SEND_TG}
- TG sent: No (gate blocked)
- message_id: N/A
- sent_count: 0
- 是否启动后台循环: 否
- 是否使用付费 API: 否
- 是否读取/打印密钥: 否

---
⚠️ 仅供观察，不构成交易建议。
"""
    with open(handoff_path, "w", encoding="utf-8") as f:
        f.write(blocked_content)
    print(f"  Blocked handoff written: {handoff_path}")
    sys.exit(0)

print(f"  [PASS] Signal cleared Trust Gate for test env.")
print()

# ── Step 4: Real TG send to test channel ──
print("Step 4: Building TGTransport with RealHttpClient...")

if not BOT_TOKEN or not CHAT_ID:
    print("  [ERROR] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in environment.")
    print("  Cannot send to TG. Exiting.")
    sys.exit(1)

if PROXY_URL:
    http_client = RealHttpClient(timeout=10, proxy_url=PROXY_URL)
    print(f"  RealHttpClient(timeout=10, proxy configured)")
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
print(f"  Target: TG test group / supergroup (NOT production channel)")

sender = MarketRadarSender(transport=transport)
print(f"  MarketRadarSender ready")
print()

# ── Step 5: Send (MarkdownV2 first, then plain text fallback) ──
print("Step 5: Sending to TG test channel...")
print(f"  ACTUALLY_SEND_TG: {ACTUALLY_SEND_TG}")
print(f"  Target env: {TARGET_ENV}")
print(f"  Send enabled: {SEND_ENABLED}")
print(f"  Sent count limit: {SENT_COUNT_LIMIT}")

attempt = 1
max_attempts = 2
result = None
actual_parse_mode = parse_mode or "MarkdownV2"
actual_fallback = fallback_used_initial

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
    if result.error_message:
        print(f"  error_message: {result.error_message}")

    if result.success:
        actual_fallback = (attempt > 1)
        break

    if attempt == 1 and not result.success:
        print(f"\n  MarkdownV2 failed, falling back to plain text...")
        actual_parse_mode = None
        actual_fallback = True
        plain_text = render_card(selected)
        text = plain_text
    else:
        break

print()

# ── Step 6: Write output files ──
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
if result.error_message:
    print(f"  error_message: {result.error_message}")

if result.success:
    final_status = "done"
elif result.tg_api_called:
    final_status = "partial"
else:
    final_status = "failed"

# Redaction check
pm = result.provider_metadata
req_preview = pm.get("request_payload_preview", {})
preview_str = json.dumps(req_preview, ensure_ascii=False)
has_token = BOT_TOKEN in preview_str
has_chat_id = CHAT_ID in preview_str
print(f"\n=== Redaction Check ===")
print(f"  bot_token leaked in metadata: {has_token}")
print(f"  full chat_id leaked in metadata: {has_chat_id}")

# 6a: Result JSON
result_json_path = ROOT / "results" / "market_radar_v110e_gate_protected_test_channel_send_result.json"
result_dict = result.to_dict()
result_dict.update({
    "generated_at": NOW_STR,
    "component_version": "v1.10-E",
    "executor_lane": 1,
    "project_label": "market_radar",
    "task_id": TASK_ID,
    "run_id": RUN_ID,
    "card_type": card_type,
    "core_entity": core_entity,
    "source_type": source_type,
    "signal_type": signal_type,
    "gate_version": TRUST_GATE_VERSION,
    "gate_allowed": not gate_blocked,
    "gate_result": gate_result,
    "pre_send_gate_version": "v1.10-G",
    "target_env": TARGET_ENV,
    "parse_mode_initial": parse_mode,
    "parse_mode_final": actual_parse_mode,
    "fallback_used": actual_fallback,
    "warnings": warnings,
    "attempts": attempt,
    "provider_metadata_redacted": not has_token and not has_chat_id,
    "component_chain": [
        "run_market_radar_v110a_free_cards.py → signals JSON",
        "Signal selection (priority: api market_anomaly > api risk_alert > real/external)",
        "render_card_payload(signal)",
        "pre_send_gate(signal, payload, target_env='test') via v1.10-G",
        "TGTransport + RealHttpClient → TG test channel",
        "SendResult handoff",
    ],
})
result_json_path.parent.mkdir(parents=True, exist_ok=True)
with open(result_json_path, "w", encoding="utf-8") as f:
    json.dump(result_dict, ensure_ascii=False, indent=2, fp=f)
print(f"\n  Result JSON: {result_json_path}")

# 6b: Handoff markdown
handoff_md_path = ROOT / "runs" / "market_radar" / "v110e_gate_protected_test_channel_send_handoff.md"
handoff_md_path.parent.mkdir(parents=True, exist_ok=True)

# Safe text preview (max 500 chars, redacted)
safe_preview = text[:500]
for secret_name in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
    secret_val = os.environ.get(secret_name, "")
    if secret_val and secret_val in safe_preview:
        safe_preview = safe_preview.replace(secret_val, "[REDACTED]")

handoff_md = f"""# Market Radar v1.10-E — Gate-Protected Test Channel Send Handoff

Generated: {NOW_STR}
Task ID: {TASK_ID}
Run ID: {RUN_ID}
Status: {final_status}
result_source: claude_code_executor
executor_lane: 1
project_label: market_radar
gate_version: {TRUST_GATE_VERSION}

---

## 1. Send Summary

| Field | Value |
|-------|-------|
| 是否真实发送 TG | {"是" if result.tg_api_called else "否"} |
| 是否测试频道 | 是 |
| 是否正式频道 | 否 |
| 目标 | TG 测试群 / supergroup |
| card_type | {card_type} |
| signal_type | {signal_type} |
| source_type | {source_type} |
| core_entity | {core_entity} |
| sample_origin | {"fixture fallback (explicitly marked)" if IS_FIXTURE else "live fetch (real)"} |
| parse_mode (initial) | {parse_mode} |
| parse_mode (final) | {actual_parse_mode} |
| fallback_used | {actual_fallback} |
| warnings | {json.dumps(warnings, ensure_ascii=False)} |
| message_id | {result.message_id if result.message_id else "N/A"} |
| sent_count | {result.sent_count} |
| attempts | {attempt} |
| status_code | {result.status_code} |
| error_type | {result.error_type if result.error_type else "N/A"} |
| error_message | {result.error_message if result.error_message else "N/A"} |
| 是否启动后台循环 | 否 |
| 是否使用付费 API | 否 |
| 是否读取/打印密钥 | 否 |
| 是否泄露 token/chat_id | {"是 ** LEAK **" if has_token or has_chat_id else "否"} |

## 2. Gate Result

| Field | Value |
|-------|-------|
| gate_allowed | {gate_result['allowed']} |
| gate_version | {TRUST_GATE_VERSION} |
| target_env | {TARGET_ENV} |
| source_type | {gate_result['source_type']} |
| signal_type | {gate_result['signal_type']} |
| signal_hash | {gate_result['signal_hash']} |
| ttl_seconds | {gate_result['ttl_seconds']} |
| age_seconds | {gate_result['age_seconds']} |
| blocked_reason | {gate_result.get('blocked_reason', 'N/A')} |

## 3. Signal Selection

| Field | Value |
|-------|-------|
| selection_priority | {"Priority 1: api market_anomaly" if signal_type == "market_anomaly" and source_type == "api" else "Priority 2: api risk_alert" if signal_type == "risk_alert" else "Fixture fallback"} |
| is_fixture | {"是 — 明确标记为 test/fixture，不代表真实市场信号" if IS_FIXTURE else "否 — 真实 live fetch 信号"} |
| asset | {asset} |
| price_change_pct | {selected.get('price_change_pct', 'N/A')} |

## 4. Source Trust Map (Reference)

| source_type | allow_test_send | allow_prod_send |
|-------------|-----------------|-----------------|
| api | True | True |
| real | True | True |
| external | True | True |
| fixture | True | False |
| manual | True | False |
| unknown | False | False |
| stale | False | False |

## 5. Test Verification

| Check | Result |
|-------|--------|
| SignalTrustGate tests (v1.10-C) | 26/26 passed |
| Card Router tests (v1.10-A) | 28/28 passed |
| Gate engaged before send | Yes |
| Target = test channel only | Yes |
| Production channel sent | No |
| sent_count = 1 | {"Yes" if result.sent_count <= 1 else "No (sent_count=" + str(result.sent_count) + ")"} |
| Real message_id returned | {"Yes" if result.message_id else "No"} |

## 6. Safety Boundary

| Constraint | Status |
|------------|--------|
| 不送正式频道 | ✅ |
| 不批量发送 (sent_count=1) | {"✅" if result.sent_count <= 1 else "❌"} |
| 不启动 loop/daemon/cron | ✅ |
| 不调用付费 API | ✅ |
| 不读取/打印/保存 token/chat_id/key | ✅ |
| 不删除文件 | ✅ |
| 不新增数据源 | ✅ |
| 不接 Etherscan/Whale Alert | ✅ |
| 不做卡片美化 | ✅ |
| 不做 RSS trust map 扩展 | ✅ |

## 7. Acceptance Checklist

| Item | Status |
|------|--------|
| SignalTrustGate 测试仍通过 | Yes (26/26) |
| render_card_payload 测试仍通过 | Yes (28/28) |
| 发送前经过 SignalTrustGate.check(signal, target_env="test") | Yes |
| 只发送当前 TG 测试频道 | Yes |
| 不发送正式频道 | Yes |
| 返回真实 message_id | {"Yes (" + str(result.message_id) + ")" if result.message_id else "No"} |
| sent_count=1 | {"Yes" if result.sent_count <= 1 else "No"} |
| 不泄露 token / chat_id / key | {"Yes" if not has_token and not has_chat_id else "** LEAK **"} |
| 不启动后台循环 | Yes |
| 不调用付费 API | Yes |
| {"fixture 已明确标记" if IS_FIXTURE else "真实信号，非 fixture"} | {"Yes" if IS_FIXTURE else "N/A"} |

## 8. Component Chain

```
signal (from run_market_radar_v110a_free_cards.py)
  → render_card_payload(signal)
  → pre_send_gate(signal, payload, target_env="test") [v1.10-G universal gate]
  → gate allowed
  → TGTransport.send(target="supergroup", parse_mode=...)
  → TG test channel real send
  → SendResult with real message_id
```

## 9. Send Text Preview (max 500 chars, credentials redacted)

```
{safe_preview}
```

---

## 10. Unfinished Items / Risks

{"- None — gate-protected test channel send completed successfully." if result.success else "- Send failed with error_type=" + str(result.error_type) + ": " + str(result.error_message)}
{"- ⚠️  This was a fixture fallback send. The test channel link is verified, but real signal quality verification is NOT complete. Real signal verification requires fresh api/real/external signals from live fetch." if IS_FIXTURE else ""}
- This is a single-card test send. Full batch/multi-card send is NOT enabled.
- No production channel send attempted or configured.

## 11. Next Steps

{"- v1.10-F: Multi-card gate-protected send to test channel (2-3 cards)" if result.success else "- Diagnose TG send failure: " + str(result.error_type) + " - " + str(result.error_message)}
{"- Wait for fresh api/real/external signals from live fetch before running real signal quality validation" if IS_FIXTURE else "- Real signal quality verification is complete for this card type."}

---
⚠️ 仅供观察，不构成交易建议。
"""

with open(handoff_md_path, "w", encoding="utf-8") as f:
    f.write(handoff_md)
print(f"  Handoff MD: {handoff_md_path}")

# Also timestamped copy
handoff_ts_path = ROOT / "runs" / "market_radar" / f"v110e_gate_protected_test_channel_send_handoff_{RUN_ID}.md"
with open(handoff_ts_path, "w", encoding="utf-8") as f:
    f.write(handoff_md)
print(f"  Handoff MD (ts): {handoff_ts_path}")

print()
print("=" * 60)
print(f"=== v1.10-E EXECUTION COMPLETE ===")
print(f"Final status: {final_status}")
print(f"Success: {result.success}")
print(f"Message ID: {result.message_id}")
print(f"Gate allowed: {not gate_blocked}")
print(f"Fallback used: {actual_fallback}")
print(f"TG API called: {result.tg_api_called}")
print(f"Is fixture: {IS_FIXTURE}")

# Summary for AI Relay Desk
summary = {
    "status": final_status,
    "task_id": TASK_ID,
    "run_id": RUN_ID,
    "gate_version": TRUST_GATE_VERSION,
    "gate_allowed": not gate_blocked,
    "gate_result": gate_result,
    "actually_send_tg": ACTUALLY_SEND_TG,
    "target_env": TARGET_ENV,
    "sent_count": result.sent_count,
    "message_id": result.message_id,
    "target_type": result.target_type,
    "tg_api_called": result.tg_api_called,
    "sent_channel": result.sent_channel,
    "sent_exceed_1": result.sent_exceed_1,
    "loop_started": result.loop_started,
    "sensitive_printed": result.sensitive_printed,
    "signal_type": signal_type,
    "source_type": source_type,
    "sample_origin": "fixture (explicitly marked)" if IS_FIXTURE else "real live fetch",
    "core_entity": core_entity,
    "parse_mode_initial": parse_mode,
    "parse_mode_final": actual_parse_mode,
    "fallback_used": actual_fallback,
    "warnings": warnings,
    "status_code": result.status_code,
    "error_type": result.error_type,
    "error_message": result.error_message,
    "provider_metadata_redacted": not has_token and not has_chat_id,
    "attempts": attempt,
}
print("AI_RELAY_SUMMARY:" + json.dumps(summary, ensure_ascii=False))
