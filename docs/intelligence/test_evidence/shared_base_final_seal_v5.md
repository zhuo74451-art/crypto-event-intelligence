# Shared Base Final Seal V5 — Test Matrix Results

## Summary

| Test Suite | Passed | Failed | Notes |
|------------|--------|--------|-------|
| Intelligence | 206 | 0 | All kernel tests |
| Golden Cases | 8 | 0 | G1-G8 strict assertions |
| Precision Patch | 7 | 0 | Mixed cluster, quality, ARB-011 |
| Seal Checks | 24 | 0 | Semantic verification checks |
| Full Repository | 3119 | 8 | Pre-existing baseline failures only |

## Failed Node IDs (all pre-existing baseline)

```
tests/mvpplus/independent_qa/test_qa_foundation.py::TestForbiddenImports::test_clean_import_passes
tests/mvpplus/independent_qa/test_qa_foundation.py::TestCredentialScanner::test_clean_file_passes
tests/mvpplus/independent_qa/test_qa_foundation.py::TestSyntheticSafeTargetPass::test_clean_file_no_credentials
tests/mvpplus/independent_qa/test_qa_foundation.py::TestSyntheticSafeTargetPass::test_clean_file_no_forbidden_import
tests/mvpplus/independent_qa/test_qa_foundation.py::TestSyntheticSafeTargetPass::test_clean_file_no_send
tests/mvpplus/independent_qa/test_qa_foundation.py::TestSyntheticSafeTargetPass::test_clean_file_no_trading
tests/mvpplus/independent_qa/test_qa_foundation.py::TestSyntheticSafeTargetPass::test_clean_html_passes
tests/post_mvp/telegram/test_tg_renderer_hardening.py::TestErrorDesensitization::test_2_http_error_safe_summary
```

## New Failures: None
## New Timeouts: None
