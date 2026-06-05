# Market Radar Sender v1.9A — Test Report

Generated: 2026-06-04 11:17:44 UTC+8
Component: scripts/market_radar_sender.py

## Results

| # | Test | Status | Detail |
|---|---|---|---|
| 1 | 1.Normal dry-run pass | [PASS] PASS | sent_count=1, gates=9 passed |
| 2 | 2.max_send_count enforcement | [PASS] PASS | Correctly blocked: Send limit reached: sent_count=1 >= max_send_count=1 |
| 3 | 3.blocked=true rejection | [PASS] PASS | Correctly blocked when blocked=true |
| 4 | 4.leak_count > 0 rejection | [PASS] PASS | Correctly blocked on leak_count=2 |
| 5 | 5.full_address_count > 0 rejection | [PASS] PASS | Correctly blocked on full_address_count=1 |
| 6 | 6.No external interface calls | [PASS] PASS | Verified 0 external calls, result status=done |
| 7 | 7.Empty candidate rejection | [PASS] PASS | Correctly raised ValueError on empty markdown |
| 8 | 8.Missing preview report | [PASS] PASS | Correctly raised FileNotFoundError |
| 9 | 9.Handoff output format | [PASS] PASS | All 16 required fields present |
| 10 | 10.Full address detection | [PASS] PASS | Correctly detected full address in candidate MD |
| 11 | 10.Short address passes gate | [PASS] PASS | Correctly allows short address (0x082e...ca88) |
| 12 | 11.Schema file readable | [PASS] PASS | strict_core=12 fields, flexible_payload=8 fields |
| 13 | 12.Full manifest passes | [PASS] PASS | Validated OK, 8 flexible-payload warnings |
| 14 | 13.Missing Strict Core rejects | [PASS] PASS | ValueError raised for missing 'artifact_id': Strict Core fields missing from manifest: ['artifact_id']. These fields are required by schema v1.9A-s1. See schemas/market_radar_v19.json for field definitions. |
| 15 | 13.Missing Strict Core (2nd field) rejects | [PASS] PASS | ValueError for 'full_address_count' |
| 16 | 14.Missing Flexible Payload warns | [PASS] PASS | 8 warnings for 8 missing flexible fields |

## Summary

- **Total**: 16
- **Passed**: 16
- **Failed**: 0
- **Skipped**: 0

## Safety Verification

| Check | Status |
|---|---|
| TG API called | No |
| Messages sent | No |
| Loop started | No |
| Sensitive info printed | No |
| External network calls | No |
| Remote DB written | No |
| Archive scripts modified | No |
| Candidate card modified | No |

## Test Environment

- Python: 3.14.3 (tags/v3.14.3:323c59a, Feb  3 2026, 16:04:56) [MSC v.1944 64 bit (AMD64)]
- Root: C:\Users\PC\Desktop\Projects\事件情报系统
- Platform: win32