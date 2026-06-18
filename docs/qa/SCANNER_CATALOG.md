# Scanner Catalog — mvpplus QA

| # | Scanner | Function | Checks |
|---|---------|----------|--------|
| 1 | Ownership Validator | `scan_ownership` | Changed files are within owned paths |
| 2 | Forbidden Import Scanner | `scan_forbidden_imports` | No dangerous imports (os.system, subprocess.run, etc.) |
| 3 | Trading Capability Scanner | `scan_trading_capability` | No private trade methods, wallet imports, exchange APIs |
| 4 | Credential Scanner | `scan_credentials` | No hardcoded API keys, private keys, tokens |
| 5 | Scheduler Disabled Validator | `scan_scheduler_disabled` | Schedulers/cron default to disabled |
| 6 | No-Send Validator | `scan_no_send` | No production send calls (Telegram, etc.) |
| 7 | Artifact Binding Validator | `scan_artifact_binding` | Evidence commit claims match HEAD |
| 8 | Test Count Validator | `scan_test_count` | Exact test count via pytest --collect-only |
| 9 | Dependency Validator | `scan_dependency_manifest` | Manifest exists, dependencies pinned |
| 10 | Data Truth Validator | `scan_data_truth` | Fixture/live data not mislabeled |
| 11 | Liquidation Formula Oracle | `oracle_liquidation_formula` | Long/short formula matches reference |
| 12 | First Snapshot Oracle | `oracle_first_snapshot` | First snapshot uses open price |
| 13 | HYPE Source Policy Validator | `scan_hype_source_policy` | HYPE references include 15m |
| 14 | Feed ID Validator | `scan_feed_id` | Feed IDs are deterministic |
| 15 | HTML Security Scanner | `scan_html_security` | No innerHTML without sanitization |
| 16 | URL Attack Corpus | `scan_url_corpus` | URL corpus against attack patterns |
| 17 | XSS Attack Corpus | `scan_xss_corpus` | XSS corpus against script patterns |
| 18 | Evidence Schema Validator | `scan_evidence_schema` | Evidence structure matches schema |
