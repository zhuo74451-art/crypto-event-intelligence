# Market Radar Sender v1.9A-S1 — Schema Contract Test Report

Generated: 2026-06-04 11:17:44 UTC+8
Component: scripts/market_radar_sender.py (v1.9A + v1.9A-S1)

## Schema Contract

| Item | Value |
|---|---|
| Schema path | schemas/market_radar_v19.json |
| Strict Core fields | 12 |
| Flexible Payload fields | 8 |
| Sample manifest | results/market_radar_v19_manifest_sample.json |

## Results

| # | Test | Status | Detail |
|---|---|---|---|
| 1 | Normal dry-run pass | PASS | sent_count=1, gates=9 passed |
| 2 | max_send_count enforcement | PASS | Correctly blocked: sent_count >= max_send_count |
| 3 | blocked=true rejection | PASS | Correctly blocked when blocked=true |
| 4 | leak_count > 0 rejection | PASS | Correctly blocked on leak_count=2 |
| 5 | full_address_count > 0 rejection | PASS | Correctly blocked on full_address_count=1 |
| 6 | No external interface calls | PASS | Verified 0 external calls |
| 7 | Empty candidate rejection | PASS | Correctly raised ValueError |
| 8 | Missing preview report | PASS | Correctly raised FileNotFoundError |
| 9 | Handoff output format | PASS | All 16 required fields present |
| 10 | Full address detection | PASS | Correctly detected full address |
| 10a | Short address passes gate | PASS | Correctly allows short address |
| 11 | Schema file readable | PASS | strict_core=12, flexible_payload=8 |
| 12 | Full manifest passes | PASS | Validated OK, 8 flexible-payload warnings |
| 13 | Missing Strict Core rejects | PASS | ValueError for missing 'artifact_id' |
| 13a | Missing Strict Core (2nd) | PASS | ValueError for 'full_address_count' |
| 14 | Missing Flexible Payload warns | PASS | 8 warnings for 8 missing flexible fields |

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
| Schema loaded from local file only | Yes |

## Schema Contract Verification

| Check | Status |
|---|---|
| Schema JSON parseable | Yes |
| Strict Core: 12 fields defined | Yes |
| Flexible Payload: 8 fields defined | Yes |
| Strict Core missing → ValueError | Yes |
| Flexible Payload missing → Warning only | Yes |
| Schema functions exported from sender | Yes |

## Test Environment

- Python: 3.14
- Root: C:\Users\PC\Desktop\Projects\事件情报系统
- Platform: win32
