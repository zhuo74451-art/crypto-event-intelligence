# Baseline Test Status V1

## Capture Metadata

```yaml
captured_at: 2026-06-22T03:00:00Z
base_sha: fc9b76f8a3cfc84bc384b145bd93dda41006e68f
python_version: 3.12.10
pytest_version: 9.1.0
platform: win32
```

## Commands

```bash
python -X utf8 -m pytest tests/ -q
```

## Results

Note: Full suite contains ~2000+ tests and some test files cause hanging/infinite loops when run together. Results below are per-file captures.

### Test Files and Results

| Directory / File | Passed | Failed | Skipped | Notes |
|---|---|---|---|---|
| tests/test_cn_number_formatters.py | 1 | 0 | 0 | |
| tests/test_event_price_backfill_v1.py | 57 | 0 | 0 | |
| tests/test_position_pnl_consistency.py | 1 | 0 | 0 | |
| tests/test_signal_spine_core.py | 63 | 0 | 0 | |
| tests/test_signal_spine_integration.py | 30 | 0 | 0 | |
| tests/test_signal_spine_io_v1.py | 31 | 0 | 0 | 50 subtests passed |
| tests/test_week1_price_providers_v1.py | 50 | 0 | 0 | |
| tests/mvpplus/adapters/ | 96 | 0 | 0 | |
| tests/mvpplus/feeds_market_ui/ | 170 | 0 | 0 | |
| tests/mvpplus/independent_qa/ | 88 | 2 | 0 | |
| tests/mvpplus/integration/ | 122 | 0 | 0 | |
| tests/mvpplus/operations/ | 150 | 1 | 0 | test_concurrent_writers_unique_tmp (flaky) |
| tests/mvpplus/whale_domain/ | 127 | 0 | 1 | |
| tests/post_mvp/event_intelligence/ | 1253 | 0 | 0 | |
| tests/post_mvp/market_resilience/ | partial | 1 | 0 | test_alternating_adapters_20_times hangs |
| tests/post_mvp/operations/ | partial | 0 | 0 | hangs when run with others |
| tests/post_mvp/operator/ | 103 | 0 | 0 | |
| tests/post_mvp/telegram/ | 54 | 1 | 0 | |
| tests/post_mvp/whale_intelligence/ | 241 | 0 | 2 | |

### Confirmed Failure Node IDs

1. `tests/mvpplus/independent_qa/test_qa_foundation.py::TestForbiddenImports::test_clean_import_passes`
   - AssertionError: `'FAIL' != 'PASS'` — forbidden_imports scanner found violations in clean file
   - Root cause: scanner scans the entire scan path, not just the temp file

2. `tests/mvpplus/independent_qa/test_qa_foundation.py::TestCredentialScanner::test_clean_file_passes`
   - AssertionError: `'FAIL' != 'PASS'` — credential scanner found violations in clean file
   - Root cause: scanner hits real project files beyond the temp file

3. `tests/mvpplus/operations/test_atomic_json.py::TestAtomicJson::test_concurrent_writers_unique_tmp`
   - OSError: concurrent atomic write retries exhausted (Windows race condition)
   - This is a pre-existing flaky test on Windows

4. `tests/post_mvp/telegram/test_tg_renderer_hardening.py::TestErrorDesensitization::test_2_http_error_safe_summary`
   - AssertionError: `'http_status' not found in '{"ok": false, "description": "URLError: URLError"}'`
   - Root cause: error summary JSON lacks `http_status` key from URLError vs HTTPError

5. `tests/post_mvp/market_resilience/test_market_resilience.py::TestExtendedImportIsolation::test_alternating_adapters_20_times`
   - Hangs indefinitely — import isolation test with subprocess looping

### Verdict

- All failures are pre-existing in baseline SHA
- `test_concurrent_writers_unique_tmp` is a flaky Windows race condition
- `test_alternating_adapters_20_times` hangs due to infinite subprocess loop
- None of these are caused by deleted old documentation
- All are genuine pre-existing test issues unrelated to the intelligence kernel
- No tests will be skipped, xfailed, or deleted by this work order

### Final Rule

```
final_failure_node_ids ⊆ baseline_failure_node_ids
```
