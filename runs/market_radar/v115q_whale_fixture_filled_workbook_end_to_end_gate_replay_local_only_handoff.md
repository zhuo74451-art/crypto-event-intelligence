# v115Q Whale Fixture End-to-End Gate Replay — Handoff

**Generated**: 2026-06-05T09:30:00+08:00

## Execution Summary

| stage | v115q_whale_fixture_filled_workbook_end_to_end_gate_replay_local_only |
| version | v115Q |
| description | Fixture-only end-to-end gate replay for 4 whale addresses using v115P fixture filled workbook. Replays intake → scoring → adjudication → workflow gates in enforced order. All evidence is TEST_ONLY synthetic. No real label upgrades. THIS IS A FIXTURE — no real address verification has been performed. |
| fixture_rows | 4 |
| fixture_intake_replay_records | 4 |
| fixture_scoring_replay_records | 4 |
| fixture_adjudication_replay_records | 4 |
| fixture_workflow_replay_decisions | 4 |
| fixture_intake_ready_count | 4 |
| fixture_scoring_passed_count | 4 |
| fixture_adjudication_ready_count | 4 |
| fixture_workflow_ready_count | 4 |
| fixture_upgrade_preview_allowed_count | 4 |
| low_unknown_fixture_workflow_ready_count | 2 |
| medium_fixture_workflow_ready_count | 2 |
| manual_attribution_fixture_ready_count | 2 |
| corroboration_fixture_ready_count | 2 |
| real_workbook_rows | 4 |
| real_workbook_sha256_before | `5accb61ded189c02...` |
| real_workbook_sha256_after | `5accb61ded189c02...` |
| real_workbook_modified | False |
| real_label_upgrade_performed | False |
| real_send_candidate_generated | False |
| send_ready | False |
| tg_test_group_ready | False |
| tg_sent | False |
| prod_state_write | False |
| external_api_called | False |
| credentials_read | False |
| fixture_only | True |
| next_gate_command_order_enforced | True |
| generated_at | 2026-06-05T09:30:00+08:00 |

## Output Files

| File | Path |
|------|------|
| Intake replay JSONL | `results/market_radar_v115q_whale_fixture_intake_replay_records.jsonl` |
| Scoring replay JSONL | `results/market_radar_v115q_whale_fixture_scoring_replay_records.jsonl` |
| Adjudication replay JSONL | `results/market_radar_v115q_whale_fixture_adjudication_replay_records.jsonl` |
| Workflow replay JSONL | `results/market_radar_v115q_whale_fixture_workflow_replay_decisions.jsonl` |
| Result JSON | `results/market_radar_v115q_whale_fixture_end_to_end_gate_replay_result.json` |
| Report MD | `runs/market_radar/v115q_whale_fixture_filled_workbook_end_to_end_gate_replay.md` |
| Report CSV | `runs/market_radar/v115q_whale_fixture_filled_workbook_end_to_end_gate_replay.csv` |
| Handoff MD | `runs/market_radar/v115q_whale_fixture_filled_workbook_end_to_end_gate_replay_local_only_handoff.md` |

## Safety Status

- ✅ No real workbook modified
- ✅ No real label upgrade performed
- ✅ No real send candidate generated
- ✅ No TG sent — `tg_sent: false`
- ✅ No TG test group delivery — `tg_test_group_ready: false`
- ✅ No production state written
- ✅ No external API called
- ✅ No credentials read
- ✅ Fixture only — all evidence values marked TEST_ONLY
- ✅ Gate command order enforced

## Warnings

1. **FIXTURE ONLY.** All evidence values are synthetic TEST_ONLY placeholders.
2. **Do NOT treat fixture replay pass as real address pass.**
3. **Real v115F workbook is still blocked.** Operator must fill with real evidence.
4. **Medium confidence labels still cannot go to TG test group.**
5. **Low/unknown whales still require real manual attribution.**
6. **TG test group delivery remains disabled for all 4 addresses.**
7. **Real label upgrade has NOT been performed for any address.**
