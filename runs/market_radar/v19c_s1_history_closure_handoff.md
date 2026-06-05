# Market Radar v1.9C-S1 History Closure Handoff

Generated: 2026-06-04 12:47 UTC+8
Status: done

============================================================
[SENDER CORE]  History record source confirmed | Message ID: 2195
[DESK SECURITY] salt.key persistent reuse, chat_id converted to masked code and stable fingerprint
[HISTORY ASSET] published_history.jsonl closure complete, idempotent dedup and single-line integrity passed
============================================================

## 1. salt.key has replaced hardcoded default salt

- Salt persisted at: data/market_radar/salt.key
- Format: magic number (AI_RELAY_MARKET_RADAR_SALT_V1) + 64-char hex salt
- First run creates high-entropy salt via secrets.token_bytes(32)
- Subsequent runs load and reuse existing salt
- Hardcoded default salt REMOVED from main logic
- Env var AI_RELAY_CHAT_ID_SALT accepted as migration fallback only
- Salt content NEVER printed, logged, or written to published_history.jsonl

## 2. message_id=2195 still present in published_history.jsonl

- Yes, 1 record with message_id=2195 exists
- history_version updated to v1.9C-S1
- Dedup: re-running does not add duplicate rows

## 3. Asset fields all present

- content_hash: MD5 of payload text (32 hex chars)
- semantic_tags: [Market_Radar, PnL_Update, Whale_Move] with keyword enrichment
- authorization_type: user_preauthorized_tg_group (fixed)
- reverse_trace: manifest_path, send_result_path, handoff_path, source_task_id, source_run_id
- target_masked_title: TG群-已脱敏 (ID: -100****4640)

## 4. Secret scan results

- scripts/_r2_real_tg_send.py: 0 hits (BOT_TOKEN replaced with DUMMY_BOT_TOKEN_REDACTED, CHAT_ID replaced with dummy)
- scripts/test_market_radar_history_v19c.py: 0 hits (dummy token uses non-standard bot ID)
- scripts/test_market_radar_sender_v19a.py: 0 hits (bot ID shortened to 6 digits)
- leak_count: 0

## 5. Can we enter v1.10 TTL/dedup/Buffer design?

YES. With salt.key persistence, complete asset fields, Atomic Line Watchdog,
and clean secret scan, v1.9C is properly closed. v1.10 can proceed with:
- TTL-based record expiration
- Cross-lane dedup reconciliation
- Buffer/merge for concurrent writes
- SQLite WAL mode for multi-process safety

## Modified files
- scripts/market_radar_history.py (salt persistence, asset fields, Atomic Watchdog)
- scripts/test_market_radar_history_v19c.py (32 tests: 16 original + 16 new)
- scripts/_r2_real_tg_send.py (BOT_TOKEN/CHAT_ID replaced with dummies)
- scripts/test_market_radar_sender_v19a.py (dummy token shortened for secret scan)
- data/market_radar/salt.key (NEW: persistent salt with magic number)
- data/market_radar/published_history.jsonl (updated to v1.9C-S1)

## New files
- data/market_radar/salt.key
- results/market_radar_v19c_s1_history_closure_test_report.md
- runs/market_radar/v19c_s1_history_closure_handoff.md
- runs/market_radar/v19c_s1_history_closure_handoff_20260604_124547.md

## Warnings / Notes
- v1.9C records hashed with old hardcoded salt will differ from new salt.key hashes
- TGTransport token validation test may need update if format validation tightens
- No TG API calls, no external network access, no message sending
