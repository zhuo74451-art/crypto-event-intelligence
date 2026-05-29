# v0.6 TG Draft Pilot Gate

overall_status: pass

| gate | actual | required | status |
|---|---:|---:|---|
| labeled_rows | 201 | >=201 | pass |
| manual_review_required_rate | 0.0647 | <=0.085 | pass |
| audit_sample_rows | 230 | >=200 | pass |
| synthetic_edge_cases | 15 | >=15 | pass |
| false_positive_rate | 0.0 | <=0.02 | pass |
| timezone_fail_count | 0 | 0 | pass |
| auto_publish_count | 0 | 0 | pass |
| secret_leak_count | 0 | 0 | pass |
| review_failure_modes_doc | present | required sections | pass |
| rollback_workflow_doc | present | required sections | pass |

Scope:

- This is the stricter gate from `results/v06_claude_next_engineering_direction.md`.
- Passing allows TG draft generator work only, not auto-send.
- It does not allow trading advice.
