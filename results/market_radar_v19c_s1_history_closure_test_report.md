# Market Radar v1.9C-S1 History Closure Test Report

Generated: 2026-06-04 12:47 UTC+8

## Test Summary

| Metric | Value |
|--------|-------|
| Total tests | 32 |
| Passed | 32 |
| Failed | 0 |
| Status | PASS |

## Test Categories

### Original v1.9C Tests (16 tests) - All pass
1. Build history record / 2. Chat ID redacted / 3. No leak / 4. Write succeeds
5. Dedup same message / 6. Different coexist / 7. Dedup artifact+msg / 8. Deep redact
9. Bot token redact / 10. is_duplicate / 11. requirements / 12. Hash deterministic
13. Mask chat_id / 14. Hash+masked in record / 15. No leak / 16. Extract chat_id

### v1.9C-S1 New Tests (16 tests) - All pass
17. salt.key created / 18. salt.key reused / 19. hash stable / 20. target_masked_title
21. content_hash / 22. semantic_tags / 23. authorization_type / 24. reverse_trace
25. Watchdog normal / 26. Watchdog newline repair / 27. Watchdog single-line
28. Watchdog no dupes / 29. salt not leaked / 30. newline repair logic
31. verify last line / 32. verify_salt_file

## Secret Scan Results

| File | Hits | Status |
|------|------|--------|
| scripts/_r2_real_tg_send.py | 0 | CLEAN |
| scripts/test_market_radar_history_v19c.py | 0 | CLEAN |
| scripts/test_market_radar_sender_v19a.py | 0 | CLEAN |

leak_count: 0

## Asset Field Verification
- content_hash: PRESENT (32-char MD5)
- semantic_tags: PRESENT (Market_Radar + keyword enrichment)
- authorization_type: PRESENT (user_preauthorized_tg_group)
- reverse_trace: PRESENT (manifest, send_result, handoff, task_id, run_id)
- target_masked_title: PRESENT (human-readable with mask)
- target_id_hash: PRESENT (64-char SHA-256)
- target_id_masked: PRESENT (-100****4640)

## Requirements
- requests>=2.28.0: CONFIRMED
- No duplicate: CONFIRMED
