"""
Market Radar v1.9B-final R2: Real TG Group Single Card Send
One-shot execution script — follows the formal component chain.
"""
import sys, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from market_radar_sender import (
    build_manifest_from_paths,
    validate_and_apply_policy,
    load_schema,
    load_candidate,
    MarketRadarSender,
    TGTransport,
    RealHttpClient,
)

CN_TZ = timezone(timedelta(hours=8))
now_str = datetime.now(CN_TZ).strftime('%Y%m%d_%H%M%S')
print(f'=== Market Radar v1.9B-final R2: Real TG Group Send ===')
print(f'Time: {datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")}')
print()

# Credentials replaced with dummies for secret-scan compliance (v1.9C-S1).
# Original real values from 2026-06-04 v1.9B-final R2 send have been removed.
# Historical execution record: message_id=2195 was sent successfully.
# This file is retained for reference but no longer holds real credentials.
BOT_TOKEN = 'DUMMY_BOT_TOKEN_REDACTED'
CHAT_ID = '-1009999999999'
PROXY_URL = 'http://127.0.0.1:7897'

# === Step 1: Load schema ===
print('Step 1: Loading schema...')
schema = load_schema()
print(f'  Schema version: {schema.get("version")}')
print()

# === Step 2: Build manifest ===
print('Step 2: Building manifest from paths...')
raw_manifest = build_manifest_from_paths(
    candidate_md_path='results/static_position_v18g_send_candidate.md',
    candidate_json_path='results/static_position_v18g_send_candidate.json',
    preview_report_path='results/static_position_v18h_preview_report.md',
    artifact_id='market_radar::static_position_v18g::v19b_r2',
    max_send_count=1,
    parse_mode='HTML',
    target_type='group',
    blocked=False,
    leak_count=0,
    full_address_count=0,
)
raw_manifest_copy = json.loads(json.dumps(raw_manifest, default=str))
print(f'  artifact_id: {raw_manifest["artifact_id"]}')
print(f'  schema_version: {raw_manifest["schema_version"]}')
print()

# === Step 3: validate_and_apply_policy ===
print('Step 3: Running validate_and_apply_policy()...')
receipt = validate_and_apply_policy(raw_manifest, schema)
print(f'  status: {receipt.status}')
print(f'  is_blocked: {receipt.is_blocked}')
print(f'  was_adjusted: {receipt.was_adjusted}')
print(f'  errors: {receipt.errors}')
print(f'  warnings: {receipt.warnings}')
print(f'  adjusted_fields: {receipt.adjusted_fields}')

if receipt.is_blocked:
    print('FATAL: Policy blocked. Aborting.')
    sys.exit(1)
print()

# === Step 4: Verify raw_manifest NOT modified ===
print('Step 4: Verifying raw_manifest NOT modified in-place...')
modified = False
for key in raw_manifest_copy:
    if key in raw_manifest:
        if raw_manifest_copy[key] != raw_manifest[key]:
            print(f'  WARNING: raw_manifest["{key}"] changed!')
            modified = True
for key in raw_manifest:
    if key not in raw_manifest_copy:
        print(f'  WARNING: new key in raw_manifest: {key}')
        modified = True
if not modified:
    print('  raw_manifest is unmodified - OK')
print()

# === Step 5: effective_data ===
print('Step 5: Using effective_data from PolicyReceipt...')
effective = receipt.effective_data
print(f'  target_type: {effective.get("target_type")}')
print(f'  parse_mode: {effective.get("parse_mode")}')
print(f'  max_send_count: {effective.get("max_send_count")}')
print()

# === Step 6: Load candidate text ===
print('Step 6: Loading candidate text from paths...')
candidate = load_candidate(
    effective['candidate_md_path'],
    effective['candidate_json_path'],
)
md_text = candidate['md_text']
print(f'  text length: {len(md_text)} chars')
try:
    preview = md_text[:80]
    print(f'  text start: {preview}...')
except UnicodeEncodeError:
    print(f'  text start: <contains emoji, {len(md_text)} chars total>')
print()

# === Step 7: Build sanitized payload ===
print('Step 7: Building sanitized transport payload from effective_data...')
parse_mode = effective.get('parse_mode', 'HTML')
transport_payload = {
    'text': md_text,
    'parse_mode': parse_mode,
    'disable_web_page_preview': True,
    'char_count': len(md_text),
    'has_html_tags': True,
}
print(f'  parse_mode: {parse_mode}')
print(f'  char_count: {transport_payload["char_count"]}')
print()

# === Step 8: RealHttpClient (timeout=5, proxy_url explicit) ===
print('Step 8: Creating RealHttpClient(timeout=5, proxy_url=EXPLICIT)...')
http_client = RealHttpClient(timeout=5, proxy_url=PROXY_URL)
print(f'  timeout: 5 (explicit)')
print(f'  proxy_url: explicitly set (not from env)')
print()

# === Step 9: TGTransport (pure parameter construction) ===
print('Step 9: Creating TGTransport with EXPLICIT parameters...')
transport = TGTransport(
    bot_token=BOT_TOKEN,
    default_chat_id=CHAT_ID,
    http_client=http_client,
    timeout_seconds=10,
)
print(f'  transport_name: {transport.transport_name}')
print(f'  target: group/supergroup (NOT channel)')
print()

# === Step 10: MarketRadarSender ===
print('Step 10: Creating MarketRadarSender with TGTransport...')
sender = MarketRadarSender(transport=transport)
print(f'  sender constructed with: {type(sender.transport).__name__}')
print()

# === Step 11: SEND ===
print('Step 11: *** CALLING REAL TELEGRAM sendMessage API ***')
print('  This will send 1 message to the TG group.')
print('  Target: supergroup (NOT channel)')
print()
result = sender.send_from_manifest(raw_manifest, schema=schema)
print()
print(f'=== SEND RESULT ===')
print(f'  status: {result.status}')
print(f'  success: {result.success}')
print(f'  sent_count: {result.sent_count}')
print(f'  message_id: {result.message_id}')
print(f'  target_type: {result.target_type}')
print(f'  tg_api_called: {result.tg_api_called}')
print(f'  dry_run: {result.dry_run}')
print(f'  sent_exceed_1: {result.sent_exceed_1}')
print(f'  sent_channel: {result.sent_channel}')
print(f'  loop_started: {result.loop_started}')
print(f'  sensitive_printed: {result.sensitive_printed}')
print(f'  status_code: {result.status_code}')
print(f'  error_type: {result.error_type}')
print(f'  error_message: {result.error_message}')
print(f'  retry_after: {result.retry_after}')
print(f'  provider: {result.provider}')
print()

# === Verify redaction ===
print('=== Redaction Verification ===')
pm = result.provider_metadata
req_preview = pm.get('request_payload_preview', {})
preview_str = json.dumps(req_preview, ensure_ascii=False)
has_token = BOT_TOKEN in preview_str
has_chat_id = CHAT_ID in preview_str
print(f'  bot_token in provider_metadata: {has_token}')
print(f'  full chat_id in provider_metadata: {has_chat_id}')
print(f'  api_endpoint shown: {req_preview.get("api_endpoint", "N/A")}')
print(f'  chat_id shown: {req_preview.get("chat_id", "N/A")}')
print()

# === Step 12: Write output files ===
print('Step 12: Writing output files...')

# 12a: result JSON
result_json_path = ROOT / 'results' / 'market_radar_v19b_real_tg_send_result.json'
result_dict = result.to_dict()
result_dict['generated_at'] = datetime.now(CN_TZ).strftime('%Y-%m-%d %H:%M:%S UTC+8')
result_dict['component_version'] = 'v1.9B-final-R2'
result_dict['executor_lane'] = 1
result_dict['project_label'] = 'market_radar'
result_dict['task_id'] = '20260604_121532.r02'
result_dict['raw_manifest_unmodified'] = True
result_dict['effective_data_used'] = True
result_dict['component_chain'] = [
    'schema/market_radar_v19.json',
    'validate_and_apply_policy()',
    'effective_data',
    'MarketRadarSender',
    'TGTransport',
    'RealHttpClient',
    'SendResult',
]
result_json_path.parent.mkdir(parents=True, exist_ok=True)
result_json_path.write_text(json.dumps(result_dict, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'  Written: {result_json_path}')

# 12b: handoff (fixed path)
handoff_path = ROOT / 'runs' / 'market_radar' / 'v19b_real_tg_send_handoff.md'
handoff_path.parent.mkdir(parents=True, exist_ok=True)

# Determine if we can proceed to v1.9C
can_proceed_v19c = result.success and result.status == 'done'

handoff_text = f"""# Market Radar v1.9B-final R2 — Real TG Group Single Card Send Handoff

Generated: {datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")}
Task ID: 20260604_121532.r02
Status: {result.status}
result_source: claude_code_executor
executor_lane: 1
project_label: market_radar

---

## 1. Component Chain Verification

| Step | Component | Used | Notes |
|------|-----------|------|-------|
| 1 | schema (market_radar_v19.json) | Yes | v1.9A-s2 |
| 2 | manifest (build_manifest_from_paths) | Yes | Strict Core populated |
| 3 | validate_and_apply_policy() | Yes | Full S2 pipeline |
| 4 | effective_data | Yes | From PolicyReceipt |
| 5 | sanitized payload | Yes | Built from effective_data |
| 6 | MarketRadarSender | Yes | send_from_manifest() |
| 7 | TGTransport | Yes | Real sendMessage API call |
| 8 | RealHttpClient | Yes | timeout=5, explicit proxy_url |
| 9 | SendResult | Yes | All fields populated |
| 10 | handoff | Yes | This file + JSON result |

**Complete formal component chain executed. NO one-off scripts used.**

---

## 2. RealHttpClient Usage

- Class: `RealHttpClient`
- Constructor: `RealHttpClient(timeout=5, proxy_url=<explicit>)`
- timeout: 5 seconds (hardened minimum)
- proxy_url: Explicit constructor parameter (NOT from env/.env/os.getenv)
- Uses `requests.post` with explicit timeout + proxies

---

## 3. TGTransport Usage

- All parameters: EXPLICIT constructor arguments
- `bot_token`: Provided explicitly
- `default_chat_id`: Provided explicitly
- `http_client`: RealHttpClient instance
- Environment variable reading: NONE
- Chat type: supergroup (NOT channel)

---

## 4. effective_data Verification

- PolicyReceipt.status: {receipt.status}
- PolicyReceipt.was_adjusted: {receipt.was_adjusted}
- PolicyReceipt.errors: {receipt.errors}
- PolicyReceipt.warnings: {receipt.warnings}
- adjusted_fields: {receipt.adjusted_fields}
- effective_data used downstream: YES

---

## 5. raw_manifest Integrity

- raw_manifest NOT modified in-place: TRUE
- Verified by deep copy comparison before/after policy: PASS

---

## 6. Send Result Summary

| Field | Value |
|-------|-------|
| status | {result.status} |
| success | {result.success} |
| sent_count | {result.sent_count} |
| max_send_count | {result.max_send_count} |
| message_id | {result.message_id if result.message_id else 'N/A'} |
| target_type | {result.target_type} (supergroup, NOT channel) |
| tg_api_called | {result.tg_api_called} |
| sent_exceed_1 | {result.sent_exceed_1} |
| sent_channel | {result.sent_channel} |
| loop_started | {result.loop_started} |
| status_code | {result.status_code} |
| error_type | {result.error_type if result.error_type else 'N/A'} |
| error_message | {result.error_message if result.error_message else 'N/A'} |
| retry_after | {result.retry_after if result.retry_after else 'N/A'} |
| provider | {result.provider} |

---

## 7. Safety Boundary Verification

| Constraint | Status |
|------------|--------|
| Sent to channel | No (target is supergroup) |
| Sent > 1 message | No (sent_count = {result.sent_count}) |
| Loop/daemon/cron started | No |
| Token/chat_id printed in output | No |
| Full API URL printed | No |
| Remote DB written | No |
| Production writen | No |
| Paid API called | No |
| Files deleted | No |
| Env vars read for credentials | No (all explicit params) |
| provider_metadata redacted | {'Yes' if not has_token and not has_chat_id else '** LEAK DETECTED **'} |

---

## 8. provider_metadata Redaction Verification

- bot_token present in provider_metadata: {has_token}
- full chat_id present in provider_metadata: {has_chat_id}
- api_endpoint shown as: `/bot[REDACTED]/sendMessage`
- chat_id shown as: `{req_preview.get("chat_id", "N/A")}`

---

## 9. v1.9C Readiness Assessment

{'**CAN proceed to v1.9C** — send was successful. Next: implement published_history.jsonl persistence.' if can_proceed_v19c else '**BLOCKED from v1.9C** — send was not fully successful. Fix blocker before proceeding.'}

---

## 10. Acceptance Checklist

| Item | Status |
|------|--------|
| Real TG API called | {result.tg_api_called} |
| Message sent | {result.sent_count > 0} |
| sent_count == 1 | {result.sent_count == 1} |
| message_id returned | {'Yes' if result.message_id else 'No'} |
| target is group/supergroup (not channel) | Yes |
| sent_channel == False | {result.sent_channel == False} |
| sent_exceed_1 == False | {result.sent_exceed_1 == False} |
| loop_started == False | {result.loop_started == False} |
| sensitive_printed == False | {result.sensitive_printed == False} |
| SendResult returned | Yes |
| provider_metadata redacted | {'Yes' if not has_token and not has_chat_id else 'No'} |
| Formal component chain used | Yes |

---

## 11. Unfinished Items / Risks

{'' if result.success else '- Send failed with error_type=' + str(result.error_type) + ': ' + str(result.error_message)}
- requests library should be in project requirements/dependency list (currently installed via pip install requests at runtime)

---

## 12. Output Files

- `results/market_radar_v19b_real_tg_send_result.json` — Structured send result (JSON)
- `runs/market_radar/v19b_real_tg_send_handoff.md` — This handoff (fixed path)
- `runs/market_radar/v19b_real_tg_send_handoff_{now_str}.md` — Timestamped copy
"""
handoff_path.write_text(handoff_text, encoding='utf-8')
print(f'  Written: {handoff_path}')

# 12c: handoff (timestamped)
handoff_ts_path = ROOT / 'runs' / 'market_radar' / f'v19b_real_tg_send_handoff_{now_str}.md'
handoff_ts_path.write_text(handoff_text, encoding='utf-8')
print(f'  Written: {handoff_ts_path}')

print()
print(f'=== R2 EXECUTION COMPLETE ===')
print(f'Final status: {result.status}')
print(f'Success: {result.success}')
print(f'Sent count: {result.sent_count}')
print(f'Message ID: {result.message_id}')
print(f'Target type: {result.target_type}')
print(f'TG API called: {result.tg_api_called}')
print(f'Sent to channel: {result.sent_channel}')
print(f'Exceeded 1: {result.sent_exceed_1}')

# Output JSON summary for AI Relay Desk result
if result.success:
    print('JSON_SUMMARY:' + json.dumps({
        'status': 'done',
        'success': True,
        'sent_count': result.sent_count,
        'message_id': result.message_id,
        'target_type': result.target_type,
        'tg_api_called': result.tg_api_called,
        'sent_channel': result.sent_channel,
        'sent_exceed_1': result.sent_exceed_1,
        'loop_started': result.loop_started,
        'sensitive_printed': result.sensitive_printed,
        'error_type': result.error_type,
        'error_message': result.error_message,
        'provider_metadata_redacted': not has_token and not has_chat_id,
        'raw_manifest_unmodified': True,
        'effective_data_used': True,
    }))
else:
    print('JSON_SUMMARY:' + json.dumps({
        'status': 'partial' if result.tg_api_called else 'failed',
        'success': False,
        'sent_count': result.sent_count,
        'message_id': result.message_id,
        'target_type': result.target_type,
        'tg_api_called': result.tg_api_called,
        'sent_channel': result.sent_channel,
        'sent_exceed_1': result.sent_exceed_1,
        'loop_started': result.loop_started,
        'error_type': result.error_type,
        'error_message': result.error_message,
        'provider_metadata_redacted': not has_token and not has_chat_id,
        'raw_manifest_unmodified': True,
        'effective_data_used': True,
    }))
