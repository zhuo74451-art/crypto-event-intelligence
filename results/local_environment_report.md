# Local Environment Report

Last updated: 2026-05-29 12:52:17 UTC+8

overall_status: pass
fail_count: 0

| check | actual | expected | status | notes |
|---|---|---|---|---|
| python_version | 3.11.9 | >=3.10 | pass |  |
| platform | Windows-10-10.0.26200-SP0 | Windows-compatible local shell | info |  |
| project_root | C:\Users\PC\Desktop\Projects\事件情报系统 | resolved | pass |  |
| dir_data | present | present | pass |  |
| dir_docs | present | present | pass |  |
| dir_results | present | present | pass |  |
| dir_scripts | present | present | pass |  |
| package_pandas | 3.0.3 | installed | pass |  |
| package_requests | 2.33.1 | installed | pass |  |
| requirements_txt | present | present | pass |  |
| requirements_declares_required_packages | all declared | all declared | pass |  |
| openrouter_api_key_env | set | set only when querying Claude | info | Missing is acceptable for local offline gate runs. |
