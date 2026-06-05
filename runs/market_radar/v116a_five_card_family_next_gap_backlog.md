# Market Radar v1.16-A — Next Gap Backlog

**Generated**: 2026-06-05 09:50:33 UTC+8
**Backlog items**: 21

## Priority Order

1. Complete card family discovery & naming
2. Build real input data pipelines for missing families
3. Generate local previews for fixture-only families
4. Apply quality gates (dedupe/cooldown/debug leak/secret leak)
5. Create fixture positive path E2E gate replays
6. Collect real operator evidence for real E2E
7. TG test readiness (LAST, after all prior gates)

## Backlog Items

| # | Card Family | Gap Type | Current Stage | Target Stage | Risk | Blocked By | Suggested Task ID |
|---|-------------|----------|---------------|--------------|------|------------|-------------------|
| 1 | `price_oi_volume_anomaly` | preview | `fixture_preview` | `local_preview_passed` | high | missing_input_data | `v116a_gap_001` |
| 2 | `price_oi_volume_anomaly` | quality_gate | `fixture_preview` | `quality_gate_passed` | medium | missing_preview | `v116a_gap_002` |
| 3 | `price_oi_volume_anomaly` | fixture_positive_path | `fixture_preview` | `fixture_e2e_passed` | medium | missing_input_data_or_preview | `v116a_gap_003` |
| 4 | `price_oi_volume_anomaly` | real_e2e | `fixture_preview` | `real_e2e_passed` | high | Card family not yet advanced to real E2E stage. | `v116a_gap_004` |
| 5 | `price_oi_volume_anomaly` | tg_test_group | `fixture_preview` | `tg_test_ready` | low | real_e2e_not_passed | `v116a_gap_005` |
| 6 | `whale_position_alert` | real_e2e | `fixture_e2e_passed_real_blocked` | `real_e2e_passed` | high | Real operator workbook has empty fields for all 4 addresses. Requires real operator evidence collection (v115O preflight) before gate rerun. | `v116a_gap_006` |
| 7 | `whale_position_alert` | tg_test_group | `fixture_e2e_passed_real_blocked` | `tg_test_ready` | low | real_e2e_not_passed | `v116a_gap_007` |
| 8 | `liquidation_pressure` | preview | `fixture_preview` | `local_preview_passed` | high | missing_input_data | `v116a_gap_008` |
| 9 | `liquidation_pressure` | quality_gate | `fixture_preview` | `quality_gate_passed` | medium | missing_preview | `v116a_gap_009` |
| 10 | `liquidation_pressure` | fixture_positive_path | `fixture_preview` | `fixture_e2e_passed` | medium | missing_input_data_or_preview | `v116a_gap_010` |
| 11 | `liquidation_pressure` | real_e2e | `fixture_preview` | `real_e2e_passed` | high | Card family not yet advanced to real E2E stage. | `v116a_gap_011` |
| 12 | `liquidation_pressure` | tg_test_group | `fixture_preview` | `tg_test_ready` | low | real_e2e_not_passed | `v116a_gap_012` |
| 13 | `multi_asset_market_sync` | quality_gate | `local_preview_passed` | `quality_gate_passed` | medium | missing_preview | `v116a_gap_013` |
| 14 | `multi_asset_market_sync` | fixture_positive_path | `local_preview_passed` | `fixture_e2e_passed` | medium | missing_input_data_or_preview | `v116a_gap_014` |
| 15 | `multi_asset_market_sync` | real_e2e | `local_preview_passed` | `real_e2e_passed` | high | Card family not yet advanced to real E2E stage. | `v116a_gap_015` |
| 16 | `multi_asset_market_sync` | tg_test_group | `local_preview_passed` | `tg_test_ready` | low | real_e2e_not_passed | `v116a_gap_016` |
| 17 | `news_event_market_impact` | preview | `fixture_preview` | `local_preview_passed` | high | missing_input_data | `v116a_gap_017` |
| 18 | `news_event_market_impact` | quality_gate | `fixture_preview` | `quality_gate_passed` | medium | missing_preview | `v116a_gap_018` |
| 19 | `news_event_market_impact` | fixture_positive_path | `fixture_preview` | `fixture_e2e_passed` | medium | missing_input_data_or_preview | `v116a_gap_019` |
| 20 | `news_event_market_impact` | real_e2e | `fixture_preview` | `real_e2e_passed` | high | Card family not yet advanced to real E2E stage. | `v116a_gap_020` |
| 21 | `news_event_market_impact` | tg_test_group | `fixture_preview` | `tg_test_ready` | low | real_e2e_not_passed | `v116a_gap_021` |

## Detailed Tasks

### v116a_gap_001 — price_oi_volume_anomaly: preview

- **Current Stage**: `fixture_preview`
- **Target Stage**: `local_preview_passed`
- **Risk Level**: high
- **Blocked By**: missing_input_data
- **Task**: Generate local preview cards for price_oi_volume_anomaly with real/enriched data.

### v116a_gap_002 — price_oi_volume_anomaly: quality_gate

- **Current Stage**: `fixture_preview`
- **Target Stage**: `quality_gate_passed`
- **Risk Level**: medium
- **Blocked By**: missing_preview
- **Task**: Run dedupe/cooldown/debug leak/secret leak gates for price_oi_volume_anomaly previews.

### v116a_gap_003 — price_oi_volume_anomaly: fixture_positive_path

- **Current Stage**: `fixture_preview`
- **Target Stage**: `fixture_e2e_passed`
- **Risk Level**: medium
- **Blocked By**: missing_input_data_or_preview
- **Task**: Create fixture workbook and run E2E gate replay for price_oi_volume_anomaly.

### v116a_gap_004 — price_oi_volume_anomaly: real_e2e

- **Current Stage**: `fixture_preview`
- **Target Stage**: `real_e2e_passed`
- **Risk Level**: high
- **Blocked By**: Card family not yet advanced to real E2E stage.
- **Task**: Card family not yet advanced to real E2E stage.

### v116a_gap_005 — price_oi_volume_anomaly: tg_test_group

- **Current Stage**: `fixture_preview`
- **Target Stage**: `tg_test_ready`
- **Risk Level**: low
- **Blocked By**: real_e2e_not_passed
- **Task**: Complete all prior gates before TG test group readiness for price_oi_volume_anomaly.

### v116a_gap_006 — whale_position_alert: real_e2e

- **Current Stage**: `fixture_e2e_passed_real_blocked`
- **Target Stage**: `real_e2e_passed`
- **Risk Level**: high
- **Blocked By**: Real operator workbook has empty fields for all 4 addresses. Requires real operator evidence collection (v115O preflight) before gate rerun.
- **Task**: Real operator workbook has empty fields for all 4 addresses. Requires real operator evidence collection (v115O preflight) before gate rerun.

### v116a_gap_007 — whale_position_alert: tg_test_group

- **Current Stage**: `fixture_e2e_passed_real_blocked`
- **Target Stage**: `tg_test_ready`
- **Risk Level**: low
- **Blocked By**: real_e2e_not_passed
- **Task**: Complete all prior gates before TG test group readiness for whale_position_alert.

### v116a_gap_008 — liquidation_pressure: preview

- **Current Stage**: `fixture_preview`
- **Target Stage**: `local_preview_passed`
- **Risk Level**: high
- **Blocked By**: missing_input_data
- **Task**: Generate local preview cards for liquidation_pressure with real/enriched data.

### v116a_gap_009 — liquidation_pressure: quality_gate

- **Current Stage**: `fixture_preview`
- **Target Stage**: `quality_gate_passed`
- **Risk Level**: medium
- **Blocked By**: missing_preview
- **Task**: Run dedupe/cooldown/debug leak/secret leak gates for liquidation_pressure previews.

### v116a_gap_010 — liquidation_pressure: fixture_positive_path

- **Current Stage**: `fixture_preview`
- **Target Stage**: `fixture_e2e_passed`
- **Risk Level**: medium
- **Blocked By**: missing_input_data_or_preview
- **Task**: Create fixture workbook and run E2E gate replay for liquidation_pressure.

### v116a_gap_011 — liquidation_pressure: real_e2e

- **Current Stage**: `fixture_preview`
- **Target Stage**: `real_e2e_passed`
- **Risk Level**: high
- **Blocked By**: Card family not yet advanced to real E2E stage.
- **Task**: Card family not yet advanced to real E2E stage.

### v116a_gap_012 — liquidation_pressure: tg_test_group

- **Current Stage**: `fixture_preview`
- **Target Stage**: `tg_test_ready`
- **Risk Level**: low
- **Blocked By**: real_e2e_not_passed
- **Task**: Complete all prior gates before TG test group readiness for liquidation_pressure.

### v116a_gap_013 — multi_asset_market_sync: quality_gate

- **Current Stage**: `local_preview_passed`
- **Target Stage**: `quality_gate_passed`
- **Risk Level**: medium
- **Blocked By**: missing_preview
- **Task**: Run dedupe/cooldown/debug leak/secret leak gates for multi_asset_market_sync previews.

### v116a_gap_014 — multi_asset_market_sync: fixture_positive_path

- **Current Stage**: `local_preview_passed`
- **Target Stage**: `fixture_e2e_passed`
- **Risk Level**: medium
- **Blocked By**: missing_input_data_or_preview
- **Task**: Create fixture workbook and run E2E gate replay for multi_asset_market_sync.

### v116a_gap_015 — multi_asset_market_sync: real_e2e

- **Current Stage**: `local_preview_passed`
- **Target Stage**: `real_e2e_passed`
- **Risk Level**: high
- **Blocked By**: Card family not yet advanced to real E2E stage.
- **Task**: Card family not yet advanced to real E2E stage.

### v116a_gap_016 — multi_asset_market_sync: tg_test_group

- **Current Stage**: `local_preview_passed`
- **Target Stage**: `tg_test_ready`
- **Risk Level**: low
- **Blocked By**: real_e2e_not_passed
- **Task**: Complete all prior gates before TG test group readiness for multi_asset_market_sync.

### v116a_gap_017 — news_event_market_impact: preview

- **Current Stage**: `fixture_preview`
- **Target Stage**: `local_preview_passed`
- **Risk Level**: high
- **Blocked By**: missing_input_data
- **Task**: Generate local preview cards for news_event_market_impact with real/enriched data.

### v116a_gap_018 — news_event_market_impact: quality_gate

- **Current Stage**: `fixture_preview`
- **Target Stage**: `quality_gate_passed`
- **Risk Level**: medium
- **Blocked By**: missing_preview
- **Task**: Run dedupe/cooldown/debug leak/secret leak gates for news_event_market_impact previews.

### v116a_gap_019 — news_event_market_impact: fixture_positive_path

- **Current Stage**: `fixture_preview`
- **Target Stage**: `fixture_e2e_passed`
- **Risk Level**: medium
- **Blocked By**: missing_input_data_or_preview
- **Task**: Create fixture workbook and run E2E gate replay for news_event_market_impact.

### v116a_gap_020 — news_event_market_impact: real_e2e

- **Current Stage**: `fixture_preview`
- **Target Stage**: `real_e2e_passed`
- **Risk Level**: high
- **Blocked By**: Card family not yet advanced to real E2E stage.
- **Task**: Card family not yet advanced to real E2E stage.

### v116a_gap_021 — news_event_market_impact: tg_test_group

- **Current Stage**: `fixture_preview`
- **Target Stage**: `tg_test_ready`
- **Risk Level**: low
- **Blocked By**: real_e2e_not_passed
- **Task**: Complete all prior gates before TG test group readiness for news_event_market_impact.
