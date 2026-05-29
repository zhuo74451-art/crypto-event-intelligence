# Claude Response Index

Last updated: 2026-05-29 12:52:19 UTC+8

This index tracks local Claude responses stored under `results/`. It does not mark advice as accepted; accepted project decisions still belong in `docs/DECISIONS.md`.

## Counts

| response_type | count |
|---|---:|
| next_consultation | 30 |
| other | 9 |
| manual_reduction | 2 |
| macro_holdout | 1 |
| release_rules | 1 |
| engineering_direction | 1 |
| question_backlog | 1 |
| tg_pilot | 1 |

## Latest Responses

| file | type | modified_at_china | title |
|---|---|---|---|
| `results\v15_claude_liquidation_whale_onchain_review.md` | next_consultation | 2026-05-29 12:52:15 | Claude Response |
| `results\v15_claude_hyperliquid_after_impl_review.md` | next_consultation | 2026-05-29 12:20:52 | Claude Response |
| `results\v15_claude_tg_digest_hyperliquid_review.md` | next_consultation | 2026-05-29 12:09:56 | Claude Response |
| `results\v14_claude_derivatives_percentile_review.md` | next_consultation | 2026-05-28 23:01:02 | Claude Response |
| `results\v14_claude_after_p0_p1_review.md` | next_consultation | 2026-05-28 22:45:55 | Claude Response |
| `results\v14_claude_market_state_next_review.md` | next_consultation | 2026-05-28 22:35:17 | Claude Response |
| `results\v14_claude_next_public_data_tasks.md` | other | 2026-05-28 22:23:07 | v14 系统上线评估：综合审查意见 |
| `results\v14_claude_next_data_layer_review.md` | other | 2026-05-28 22:18:58 | 综合审查意见：v14 系统上线评估 |
| `results\v14_claude_next_user_value_review.md` | other | 2026-05-28 22:15:28 | 综合审查意见：v14 系统上线评估 |
| `results\v14_claude_digest_integration_review.md` | other | 2026-05-28 22:11:10 | 验证报告综合审查意见 |
| `results\v14_claude_gate_next_review.md` | other | 2026-05-28 22:02:21 | 验证报告审查意见 |
| `results\v14_claude_three_task_followup_review.md` | other | 2026-05-28 21:59:12 | 验证报告总结 |

## Operating Rule

- Store raw Claude responses in `results/`.
- Run `python scripts/index_claude_responses.py` after adding a response.
- Convert accepted recommendations into `docs/DECISIONS.md` before changing product direction.
- Do not treat unreviewed Claude text as implementation authority.
