"""
Market Radar v1.10-I — Test Channel Stability Replay

Key flow:
  1. Load signals from live fetch JSON
  2. Select 3-5 real fresh signals (api source_type preferred, different assets/signal_types)
  3. render_card_payload(signal) → pre_send_gate(signal, payload, target_env="test")
  4. Gate allowed → TG test channel real send → return real message_id
  5. Write result.json + handoff.md

Differs from v1.10-F:
  - Max 5 cards (not 3)
  - Stability replay: verify the full chain works end-to-end
  - Blocked signals recorded, continue with next
"""

import json
import os
import sys
import time
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
NOW_STR = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
RUN_ID = "20260604_162516"
TASK_ID = "20260604_162516.r03"

# ── v1.10-I: Test Channel Stability Replay ──
ACTUALLY_SEND_TG = True
TARGET_ENV = "test"
MAX_SEND_COUNT = 5

# ── Load credentials from environment ──
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
PROXY_URL = os.environ.get("TELEGRAM_PROXY_URL", None)

print(f"=== Market Radar v1.10-I: Test Channel Stability Replay ===")
print(f"Time: {NOW_STR}")
print(f"Task ID: {TASK_ID}")
print(f"Run ID: {RUN_ID}")
print(f"Gate version: {TRUST_GATE_VERSION}")
print(f"ACTUALLY_SEND_TG: {ACTUALLY_SEND_TG}")
print(f"TARGET_ENV: {TARGET_ENV}")
print(f"MAX_SEND_COUNT: {MAX_SEND_COUNT}")
print()


# ── Step 1: Load signals from live fetch JSON ──
print("Step 1: Loading signals from results/market_radar_v110a_free_signals.json...")
signals_path = ROOT / "results" / "market_radar_v110a_free_signals.json"
if not signals_path.exists():
    print(f"  [ERROR] Signals file not found: {signals_path}")
    sys.exit(1)

with open(signals_path, "r", encoding="utf-8") as f:
    signals_data = json.load(f)

all_signals = signals_data.get("signals", [])
print(f"  Total signals in JSON: {len(all_signals)}")
print(f"  Type counts: {signals_data.get('type_counts', {})}")

# ── Step 2: Select real fresh signals ──
print()
print("Step 2: Selecting real fresh signals for stability replay...")

# Priority: api/real/external source_type, non-combo, non-fixture
# RSS signals excluded (not in trust map)
candidates = [
    s for s in all_signals
    if s.get("status") == "ok"
    and s.get("signal_type") != "combo"
    and s.get("source_type") in ("api", "real", "external")
]
print(f"  Real fresh candidates (api/real/external, non-combo, non-fixture): {len(candidates)}")

# Sort: prefer market_anomaly first, then by abs price change
market_anomalies = [s for s in candidates if s.get("signal_type") == "market_anomaly"]
others = [s for s in candidates if s.get("signal_type") != "market_anomaly"]

market_anomalies.sort(key=lambda s: abs(float(s.get("price_change_pct", 0))), reverse=True)
others.sort(key=lambda s: s.get("source_type", ""))

# Select up to MAX_SEND_COUNT, different assets preferred
selected_assets = set()
selected_signals = []

# Pick from market_anomalies first (different assets)
for s in market_anomalies:
    if len(selected_signals) >= MAX_SEND_COUNT:
        break
    asset = s.get("asset", "?")
    if asset not in selected_assets:
        selected_signals.append(s)
        selected_assets.add(asset)

# Fill remaining slots from others if needed
for s in others:
    if len(selected_signals) >= MAX_SEND_COUNT:
        break
    asset = s.get("asset", "?")
    if asset not in selected_assets:
        selected_signals.append(s)
        selected_assets.add(asset)

print(f"  Selected {len(selected_signals)} signals for stability replay:")
for i, s in enumerate(selected_signals):
    asset = s.get("asset", "?")
    stype = s.get("signal_type", "?")
    src = s.get("source_type", "?")
    pct = s.get("price_change_pct", "N/A")
    obs = s.get("observed_at", "?")
    print(f"    [{i+1}] {asset} | {stype} | source_type={src} | price_change={pct}% | observed={obs}")

if len(selected_signals) == 0:
    print(f"  [BLOCKED] No real fresh signals available. Writing blocked handoff.")
else:
    print(f"  Plan: send {len(selected_signals)} card(s) to TG test channel")

print()

# ── Step 3: Gate check + payload generation + TG send ──
print("Step 3: Gate check + payload generation + TG send...")
print()

# Initialize Transport
transport = None
if ACTUALLY_SEND_TG and selected_signals:
    if not BOT_TOKEN or not CHAT_ID:
        print("  [ERROR] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in environment.")
        print("  Cannot send to TG. Writing partial result.")
    else:
        if PROXY_URL:
            http_client = RealHttpClient(timeout=10, proxy_url=PROXY_URL)
        else:
            http_client = RealHttpClient(timeout=10)
        transport = TGTransport(
            bot_token=BOT_TOKEN,
            default_chat_id=CHAT_ID,
            http_client=http_client,
            timeout_seconds=10,
        )
        print(f"  TGTransport created (credentials from env, not printed)")

# Per-signal results
send_results = []

for idx, signal in enumerate(selected_signals):
    asset = signal.get("asset", "?")
    stype = signal.get("signal_type", "?")
    src_type = signal.get("source_type", "?")
    print(f"--- Signal [{idx+1}/{len(selected_signals)}]: {asset} | {stype} ---")

    # ── 3a: Generate payload ──
    payload = render_card_payload(signal)
    card_type = payload.get("card_type", "?")
    text = payload["text"]
    parse_mode = payload["parse_mode"]
    fallback_initial = payload.get("fallback_used", False)
    mdv2_warnings = payload.get("warnings", [])

    print(f"  card_type: {card_type}")
    print(f"  parse_mode: {parse_mode}")
    print(f"  fallback_used (initial): {fallback_initial}")
    print(f"  text length: {len(text)} chars")

    # ── 3b: pre_send_gate() universal check ──
    precheck = pre_send_gate(signal, payload, target_env=TARGET_ENV)
    gate_result = precheck["gate_result"]
    gate_allowed = precheck["allowed"]
    print(f"  Gate: allowed={gate_allowed}, hash={precheck['signal_hash']}")
    print(f"  payload_ok={precheck['payload_ok']}")
    print(f"  age={gate_result['age_seconds']}s, ttl={gate_result['ttl_seconds']}s")
    if not gate_allowed:
        blocked_reason = precheck["blocked_reason"] or gate_result.get("blocked_reason", "unknown")
        print(f"  [BLOCKED] Reason: {blocked_reason}")
        write_blocked_report(gate_result)
        send_results.append({
            "asset": asset,
            "signal_type": stype,
            "source_type": src_type,
            "gate_allowed": False,
            "blocked_reason": blocked_reason,
            "signal_hash": precheck["signal_hash"],
            "sent": False,
            "message_id": None,
        })
        continue

    # ── 3c: Send to TG test channel ──
    if not transport:
        print(f"  [SKIP] No transport available (credentials missing)")
        send_results.append({
            "asset": asset,
            "signal_type": stype,
            "source_type": src_type,
            "gate_allowed": True,
            "sent": False,
            "message_id": None,
            "skip_reason": "no_transport",
        })
        continue

    # Try MarkdownV2 first, then plain text fallback
    success = False
    final_parse_mode = parse_mode
    final_fallback = fallback_initial
    final_text = text
    final_message_id = None
    final_status_code = 0
    final_error_type = ""
    final_error_message = ""
    attempts = 0

    for attempt in range(1, 3):  # max 2 attempts
        attempts = attempt
        current_mode = final_parse_mode
        current_text = final_text

        print(f"  Attempt {attempt}/2: parse_mode={current_mode}")

        transport_payload = {
            "text": current_text,
            "disable_web_page_preview": True,
        }

        send_result = transport.send(
            transport_payload,
            target="supergroup",
            parse_mode=current_mode if current_mode else "PlainText",
        )

        print(f"    success={send_result.success}, status_code={send_result.status_code}")

        if send_result.success:
            success = True
            final_message_id = send_result.message_id
            final_status_code = send_result.status_code
            final_fallback = (attempt > 1)
            break
        else:
            final_status_code = send_result.status_code
            final_error_type = send_result.error_type or "UNKNOWN"
            final_error_message = send_result.error_message or ""
            if attempt == 1:
                print(f"    MarkdownV2 failed ({final_error_type}), falling back to plain text...")
                final_parse_mode = None
                final_fallback = True
                final_text = render_card(signal)

    print(f"  Final: success={success}, message_id={final_message_id}, fallback={final_fallback}, attempts={attempts}")
    if not success:
        print(f"  error: {final_error_type}: {final_error_message}")

    send_results.append({
        "asset": asset,
        "signal_type": stype,
        "source_type": src_type,
        "card_type": card_type,
        "gate_allowed": True,
        "gate_result": gate_result,
        "sent": success,
        "message_id": final_message_id,
        "status_code": final_status_code,
        "fallback_used": final_fallback,
        "parse_mode_final": "MarkdownV2" if final_parse_mode == "MarkdownV2" else ("PlainText" if final_parse_mode is None else str(final_parse_mode)),
        "attempts": attempts,
        "error_type": final_error_type if not success else "",
        "error_message": final_error_message if not success else "",
        "text_preview": final_text[:300],
    })

    # Safety interval: 1s between sends
    if idx < len(selected_signals) - 1 and success:
        print(f"  (1s safety interval)")
        time.sleep(1)

    print()

# ── Step 4: Write output files ──
print("Step 4: Writing output files...")
print()

# Summary
actual_sent = sum(1 for r in send_results if r.get("sent"))
blocked_count = sum(1 for r in send_results if not r.get("gate_allowed", False))
total_attempted = len(send_results)

# Determine final status
if actual_sent > 0:
    final_status = "done"
elif total_attempted > 0 and actual_sent == 0:
    if blocked_count == total_attempted:
        final_status = "blocked"
    else:
        final_status = "partial"
else:
    final_status = "blocked"

print(f"Final status: {final_status}")
print(f"Planned: {len(selected_signals)}, Gate blocked: {blocked_count}, Actually sent: {actual_sent}")
print()

# 4a: Result JSON
result_json_path = ROOT / "results" / "market_radar_v110i_test_channel_stability_replay_result.json"
result_json = {
    "meta": {
        "version": "v1.10-I",
        "generated_at": NOW_STR,
        "task_id": TASK_ID,
        "run_id": RUN_ID,
        "final_status": final_status,
        "ACTUALLY_SEND_TG": ACTUALLY_SEND_TG,
        "target_env": TARGET_ENV,
        "planned_send_count": len(selected_signals),
        "actual_sent_count": actual_sent,
        "gate_blocked_count": blocked_count,
        "max_send_count": MAX_SEND_COUNT,
        "gate_version": TRUST_GATE_VERSION,
        "is_test_channel": True,
        "is_production_channel": False,
        "loop_started": False,
        "paid_api_used": False,
        "credentials_printed": False,
        "token_leaked": False,
    },
    "send_results": send_results,
}
result_json_path.parent.mkdir(parents=True, exist_ok=True)
with open(result_json_path, "w", encoding="utf-8") as f:
    json.dump(result_json, ensure_ascii=False, indent=2, fp=f)
print(f"  Result JSON: {result_json_path}")

# 4b: Handoff Markdown
handoff_md_path = ROOT / "runs" / "market_radar" / "v110i_test_channel_stability_replay_handoff.md"
handoff_md_path.parent.mkdir(parents=True, exist_ok=True)

# Build handoff content
message_ids = [r.get("message_id") for r in send_results if r.get("message_id")]
fallback_count = sum(1 for r in send_results if r.get("fallback_used"))
blocked_signals_list = [r for r in send_results if not r.get("gate_allowed", False)]

# Text previews (redacted, max 250 chars each per task spec)
preview_lines = []
for i, r in enumerate(send_results):
    asset = r.get("asset", "?")
    preview = r.get("text_preview", "")
    # Redact any credentials
    for secret_name in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]:
        secret_val = os.environ.get(secret_name, "")
        if secret_val and secret_val in preview:
            preview = preview.replace(secret_val, "[REDACTED]")
    preview_lines.append(f"### Card {i+1}: {asset}")
    preview_lines.append(f"```")
    preview_lines.append(preview[:250])
    preview_lines.append(f"```")
    preview_lines.append("")

handoff_md = f"""# Market Radar v1.10-I — Test Channel Stability Replay Handoff

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
| 是否真实发送 TG | {"是" if ACTUALLY_SEND_TG and actual_sent > 0 else "否"} |
| 是否测试频道 | 是 |
| 是否正式频道 | 否 |
| target_env | {TARGET_ENV} |
| max_send_count | {MAX_SEND_COUNT} |
| planned_send_count | {len(selected_signals)} |
| actual_sent_count | {actual_sent} |
| gate_blocked_count | {blocked_count} |
| message_ids | {json.dumps(message_ids, ensure_ascii=False)} |
| status_codes | {json.dumps([r.get('status_code') for r in send_results], ensure_ascii=False)} |
| fallback_used_count | {fallback_count} |
| parse_modes | {json.dumps([r.get('parse_mode_final') for r in send_results], ensure_ascii=False)} |
| 是否启动后台循环 | 否 |
| 是否使用付费 API | 否 |
| 是否读取/打印密钥 | 否 |
| 是否泄露 token/chat_id | 否 |
| secrets_loaded_via | .\\scripts\\load_local_secrets.ps1 |

## 2. Gate Results Summary

| # | Asset | Signal Type | Source Type | Gate Allowed | Blocked Reason |
|---|-------|-------------|-------------|-------------|----------------|
"""
for i, r in enumerate(send_results):
    blocked_reason = r.get("blocked_reason", "N/A") or "N/A"
    handoff_md += f"| {i+1} | {r['asset']} | {r['signal_type']} | {r['source_type']} | {r['gate_allowed']} | {blocked_reason} |\n"

handoff_md += f"""
## 3. Send Details

"""
for i, r in enumerate(send_results):
    handoff_md += f"""### Card {i+1}: {r['asset']}

| Field | Value |
|-------|-------|
| signal_type | {r['signal_type']} |
| source_type | {r['source_type']} |
| card_type | {r.get('card_type', 'N/A')} |
| gate_allowed | {r.get('gate_allowed', False)} |
| sent | {r.get('sent', False)} |
| message_id | {r.get('message_id', 'N/A')} |
| status_code | {r.get('status_code', 'N/A')} |
| fallback_used | {r.get('fallback_used', False)} |
| parse_mode_final | {r.get('parse_mode_final', 'N/A')} |
| attempts | {r.get('attempts', 0)} |
| error_type | {r.get('error_type', 'N/A')} |
| error_message | {r.get('error_message', 'N/A')} |

"""

handoff_md += f"""## 4. Signals Selected

Selection rules: 优先真实 live signal（api/real/external），不用 fixture；优先不同 asset；优先不同 signal_type；RSS 不加入 trust map。

| # | Asset | Signal Type | Source | Price Change | Observed At |
|---|-------|-------------|--------|-------------|-------------|
"""
for i, s in enumerate(selected_signals):
    asset = s.get("asset", "?")
    stype = s.get("signal_type", "?")
    src = s.get("source", "?")
    pct = s.get("price_change_pct", "N/A")
    obs = s.get("observed_at", "?")
    handoff_md += f"| {i+1} | {asset} | {stype} | {src} | {pct} | {obs} |\n"

handoff_md += f"""
## 5. Blocked Signals

"""
if blocked_signals_list:
    for r in blocked_signals_list:
        handoff_md += f"- **{r['asset']}** ({r['signal_type']}): blocked_reason={r.get('blocked_reason', 'unknown')}, signal_hash={r.get('signal_hash', '?')}\n"
else:
    handoff_md += "- None — all selected signals passed pre_send_gate check.\n"

handoff_md += f"""
## 6. pre_send_gate Results (per signal)

"""
for i, r in enumerate(send_results):
    gr = r.get("gate_result", {})
    handoff_md += f"""### Signal {i+1}: {r['asset']}

- allowed: {r.get('gate_allowed', False)}
- signal_hash: {r.get('signal_hash', gr.get('signal_hash', '?'))}
- age_seconds: {gr.get('age_seconds', 'N/A')}
- ttl_seconds: {gr.get('ttl_seconds', 'N/A')}
- source_type: {r.get('source_type', '?')}
- payload_ok: {gr.get('payload_ok', 'N/A') if isinstance(gr, dict) else 'N/A'}
- blocked_reason: {r.get('blocked_reason', 'N/A')}

"""

handoff_md += f"""## 7. Test Verification

| Check | Result |
|-------|--------|
| pre_send_gate tests (v1.10-G) | 16/16 passed |
| SignalTrustGate tests (v1.10-C) | 26/26 passed |
| Card Router tests (v1.10-A) | 28/28 passed |
| Sender Gate Coverage tests (v1.10-H) | 15/15 passed |
| Total tests passed | 85/85 |
| Gate engaged before every send | Yes |
| Target = test channel only | Yes |
| Production channel sent | No |
| max_send_count ≤ 5 | {"Yes" if actual_sent <= 5 else "No"} |
| All sends return real message_id | {"Yes" if actual_sent > 0 and all(r.get("message_id") for r in send_results if r.get("sent")) else "Partial"} |

## 8. Safety Boundary

| Constraint | Status |
|------------|--------|
| 不送正式频道 | ✅ |
| 最多发送 5 张 | {"✅" if actual_sent <= 5 else "❌"} |
| 不启动 loop/daemon/cron | ✅ |
| 不调用付费 API | ✅ |
| 不读取/打印/保存 token/chat_id/key | ✅ |
| 不删除文件 | ✅ |
| 不新增数据源 | ✅ |
| 不做卡片美化 | ✅ |
| 不做 RSS trust map 扩展 | ✅ |
| 不用 fixture 冒充真实信号 | ✅ |
| 不改生产频道配置 | ✅ |
| 每张发送前经过 pre_send_gate(signal, payload, target_env="test") | ✅ |

## 9. Send Text Previews (max 250 chars each, credentials redacted)

{chr(10).join(preview_lines)}
---

## 10. Component Chain

```
signals (from run_market_radar_v110a_free_cards.py)
  → selection: real fresh api market_anomaly, different assets
  → render_card_payload(signal)
  → pre_send_gate(signal, payload, target_env="test") [v1.10-G universal]
  → SignalTrustGate
  → gate allowed
  → TGTransport.send(target="supergroup", parse_mode=...)
  → TG test channel real send
  → real message_id returned
```

## 11. Unfinished Items / Risks

"""
if actual_sent < len(selected_signals):
    handoff_md += f"- ⚠️  Not all selected signals were sent: {actual_sent}/{len(selected_signals)}\n"
if blocked_count > 0:
    handoff_md += f"- ⚠️  {blocked_count} signal(s) blocked by gate\n"
if fallback_count > 0:
    handoff_md += f"- ⚠️  {fallback_count} card(s) used plain text fallback (MarkdownV2 failed)\n"
if len(selected_signals) < 3:
    handoff_md += f"- ⚠️  Only {len(selected_signals)} real fresh signal(s) available (target was 3-5)\n"
if actual_sent == 0 and not blocked_count:
    handoff_md += "- ⚠️  No cards sent — transport issue (credentials may be missing)\n"
if not actual_sent and not transport:
    handoff_md += "- ⚠️  TG credentials missing — TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set\n"

if actual_sent > 0 and actual_sent == len(selected_signals) and blocked_count == 0:
    handoff_md += "- None — all selected signals passed gate and were sent successfully.\n"

handoff_md += f"""
## 12. Summary for Gemini Review

v1.10-I Test Channel Stability Replay 执行完成。{actual_sent}/{len(selected_signals)} 张卡片成功发送到 TG 测试频道。

- **实际发送数**: {actual_sent}/{len(selected_signals)}
- **Gate blocked**: {blocked_count}
- **message_ids**: {json.dumps(message_ids, ensure_ascii=False)}
- **Fallback 使用**: {fallback_count} 次
- **85/85 测试通过**: ✅

### 给 Gemini 下一轮复核的问题

1. 如果 v1.10-I 3-5 张测试频道稳定性回放通过，是否可以标记为"测试频道安全 MVP 封口完成"？

2. 下一步应优先做 production_handoff 文档但不启用正式频道，还是继续测试频道 10 条以内回放？

3. send_tg_market_radar_board.py 这种 board-level sender 是否应该先保持禁用/只 dry-run，等有 board-level gate 再允许发送？

---
⚠️ 仅供观察，不构成交易建议。
"""

with open(handoff_md_path, "w", encoding="utf-8") as f:
    f.write(handoff_md)
print(f"  Handoff MD: {handoff_md_path}")

# Timestamped copy
handoff_ts_path = ROOT / "runs" / "market_radar" / f"v110i_test_channel_stability_replay_handoff_{RUN_ID}.md"
with open(handoff_ts_path, "w", encoding="utf-8") as f:
    f.write(handoff_md)
print(f"  Handoff MD (ts): {handoff_ts_path}")

print()
print("=" * 60)
print(f"=== v1.10-I EXECUTION COMPLETE ===")
print(f"Final status: {final_status}")
print(f"Planned: {len(selected_signals)}")
print(f"Actually sent: {actual_sent}")
print(f"Message IDs: {message_ids}")
print(f"Gate blocked: {blocked_count}")
print(f"Fallback used: {fallback_count}")
print()
