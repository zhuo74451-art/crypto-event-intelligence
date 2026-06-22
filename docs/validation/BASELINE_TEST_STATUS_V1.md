# Baseline Test Status V1

## Environment

| Field | Value |
|-------|-------|
| Python | 3.12.10 |
| pytest | 9.1.0 |
| Platform | Windows |
| Started | 2026-06-22 |
| Command | `python -X utf8 -m pytest tests/mvpplus/ tests/post_mvp/ tests/strategies/ [root tests]` |

## Results

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| tests/mvpplus/ | 749 | 7 | 1 |
| tests/post_mvp/ | 1931 | 1 | 2 |
| tests/strategies/ + root | 233 | 0 | 0 |
| **Total** | **2913** | **8** | **3** |

## Failure Node IDs

### Group 1: QA Foundation Checks (test_qa_foundation.py)
All 7 failures are in `tests/mvpplus/independent_qa/test_qa_foundation.py`:

1. `TestForbiddenImports::test_clean_import_passes`
   - **Error:** `AssertionError: 'FAIL' != 'PASS'`
   - **Reason:** Import scanner found violations or scanning mechanism changed
   - **Recurrence:** Stable

2. `TestCredentialScanner::test_clean_file_passes`
   - **Error:** `AssertionError: 'FAIL' != 'PASS'`
   - **Reason:** Credential scanner found violations
   - **Recurrence:** Stable

3. `TestSyntheticSafeTargetPass::test_clean_file_no_credentials`
   - **Error:** `AssertionError: 'FAIL' != 'PASS'`
   - **Reason:** Synthetic credential check failed
   - **Recurrence:** Stable

4. `TestSyntheticSafeTargetPass::test_clean_file_no_forbidden_import`
   - **Error:** `AssertionError: 'FAIL' != 'PASS'`
   - **Reason:** Synthetic forbidden import check failed
   - **Recurrence:** Stable

5. `TestSyntheticSafeTargetPass::test_clean_file_no_send`
   - **Error:** `AssertionError: 'FAIL' != 'PASS'`
   - **Reason:** Synthetic "no send" check failed
   - **Recurrence:** Stable

6. `TestSyntheticSafeTargetPass::test_clean_file_no_trading`
   - **Error:** `AssertionError: 'FAIL' != 'PASS'`
   - **Reason:** Synthetic "no trading" check failed
   - **Recurrence:** Stable

7. `TestSyntheticSafeTargetPass::test_clean_html_passes`
   - **Error:** `AssertionError: 'FAIL' != 'PASS'`
   - **Reason:** Synthetic HTML scanning check failed
   - **Recurrence:** Stable

### Group 2: Telegram Renderer (test_tg_renderer_hardening.py)

8. `TestErrorDesensitization::test_2_http_error_safe_summary`
   - **Error:** `AssertionError: 'http_status' not found in '{"ok": false, "description": "URLError: URLError"}'`
   - **Reason:** HTTP error desensitization format changed
   - **Recurrence:** Stable

## Stability Assessment

All 8 failures are **stable failures** (not flaky). They represent QA scanner rule violations and a desensitization format change — not regressions from this workbench task.

## Constraint

```text
final_failure_node_ids ⊆ baseline_failure_node_ids
```

No new failures may be introduced by this workbench implementation.
