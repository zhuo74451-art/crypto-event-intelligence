# Market Radar v1.16-A — Five Card Family Coverage Status Audit

**Generated**: 2026-06-05 09:50:33 UTC+8
**Version**: v1.16-A

---

## Conclusion

**Conclusion: Five card families are NOT yet all real-E2E passed. Unless every family has real input, card generation, preview, quality gate, send-readiness gate, and non-fixture workflow evidence, the system is not fully production-ready.**

## Summary

| Metric | Value |
|--------|-------|
| Expected card families | 5 |
| Discovered card families | 5 |
| Card family name source | market_radar_card_type_registry_v112a |
| Coverage audit status | complete |
| Router/gate passed | 5 |
| Local preview passed | 2 |
| Fixture E2E passed | 1 |
| Real E2E passed | 0 |
| TG test group ready | 0 |
| Production send ready | 0 |
| Families with unknown status | 0 |
| Families with blocked status | 1 |
| Gap backlog items | 21 |
| Audit result | **passed_with_gaps** |

## Coverage Matrix

| # | Card Family | Current Stage | Router | Input Data | Preview | Quality Gate | Fixture E2E | Real E2E | TG Test | Prod Send |
|---|-------------|---------------|--------|------------|---------|-------------|-------------|----------|---------|-----------|
| 1 | `price_oi_volume_anomaly` | **fixture_preview** | passed | partial | fixture_only | not_found | not_started | not_started | not_allowed | not_allowed |
| 2 | `whale_position_alert` | **fixture_e2e_passed_real_blocked** | passed | partial | passed | passed | passed | blocked | blocked | not_allowed |
| 3 | `liquidation_pressure` | **fixture_preview** | passed | partial | fixture_only | not_found | not_started | not_started | not_allowed | not_allowed |
| 4 | `multi_asset_market_sync` | **local_preview_passed** | passed | partial | passed | not_found | not_started | not_started | not_allowed | not_allowed |
| 5 | `news_event_market_impact` | **fixture_preview** | passed | partial | fixture_only | not_found | not_started | not_started | not_allowed | not_allowed |

## Distinction: Four Types of 'Passed'

| Pass Type | Definition | Count |
|-----------|-----------|-------|
| `router_only_passed` | Card type registered, schema/admission/block rules defined, router classifies correctly | 5 |
| `local_preview_passed` | Real/local data feed generates valid public preview cards | 2 |
| `fixture_e2e_passed` | Fixture workbook passes all gates (intake→scoring→adjudication→workflow) in replay | 1 |
| `real_e2e_passed` | Real operator evidence passes all gates, real labels ready for upgrade | 0 |

> ⚠ **Critical**: `router_only_passed` ≠ `real_e2e_passed`. 
> `fixture_e2e_passed` ≠ `real_e2e_passed`. 
> Fixture replay is a DRY-RUN; real addresses require real operator evidence.

## Per-Family Coverage Details

### price_oi_volume_anomaly

- **Current Stage**: `fixture_preview`
- **Name Source**: market_radar_card_type_registry_v112a
- **Router Test**: passed — Card type registered in v112a registry, validated in v112e unified pipeline, and samples exist in v112a fixture. Shared router/gate artifacts: registry, card_router, v112e pipeline, v112n master dryrun.
- **Input Data**: partial — Both fixture data and local enrichment / live source data found. Fixture: 2 files. Real/local: 2 files.
- **Card Generation**: not_found — No card generation artifacts found.
- **Preview**: fixture_only — Preview artifacts found (2 evidence files) but all use fixture data. No real/local data pipeline for preview.
- **Quality Gate**: not_found — No quality gate artifacts found.
- **Send Readiness**: not_started — No send readiness artifacts found.
- **Fixture E2E**: not_started — No fixture positive path verification artifacts found.
- **Real E2E**: not_started — No real E2E artifacts found. This card family has not reached real E2E stage.
- **TG Test Group**: not_allowed — No TG test group send evidence. TG send is not allowed without explicit send-readiness gate pass.
- **Production Send**: not_allowed — Production send is not allowed per safety boundary.
- **Blocked Reason**: Card family not yet advanced to real E2E stage.
- **Next Task**: Advance price_oi_volume_anomaly from fixture-only preview to local/real data feed (adapter pipeline).

### whale_position_alert

- **Current Stage**: `fixture_e2e_passed_real_blocked`
- **Name Source**: market_radar_card_type_registry_v112a
- **Router Test**: passed — Card type registered in v112a registry, validated in v112e unified pipeline, and samples exist in v112a fixture. Shared router/gate artifacts: registry, card_router, v112e pipeline, v112n master dryrun.
- **Input Data**: partial — Both fixture data and local enrichment / live source data found. Fixture: 26 files. Real/local: 31 files.
- **Card Generation**: passed — Card generation artifacts found. Family-specific: 3 files.
- **Preview**: passed — Preview cards generated via local feed/enrichment pipeline. 16 evidence files. Non-fallback preview with real/local data enrichment.
- **Quality Gate**: passed — Quality gate artifacts found: 15 files.
- **Send Readiness**: partial — Send readiness artifacts found: 5 files. All marked dry_run_only, no real send ready.
- **Fixture E2E**: passed — v115Q fixture E2E gate replay: 4 fixture rows, 4 workflow-ready. All gates (intake→scoring→adjudication→workflow) replayed successfully. THIS IS FIXTURE ONLY — not real address verification.
- **Real E2E**: blocked — v115R real workbook submission validator: 4/4 blocked. Real workbook fields are empty (TEST_ONLY placeholder). No real operator evidence submitted. Safe rerun not allowed. Next gate command order enforced.
- **TG Test Group**: blocked — TG test copy template gate exists (v115c/d) but real send is blocked. No actual TG message was sent.
- **Production Send**: not_allowed — Production send is not allowed per safety boundary.
- **Blocked Reason**: Real operator workbook has empty fields for all 4 addresses. Requires real operator evidence collection (v115O preflight) before gate rerun.
- **Next Task**: Complete real operator workbook for whale_position_alert addresses (v115O preflight), then rerun gates.

### liquidation_pressure

- **Current Stage**: `fixture_preview`
- **Name Source**: market_radar_card_type_registry_v112a
- **Router Test**: passed — Card type registered in v112a registry, validated in v112e unified pipeline, and samples exist in v112a fixture. Shared router/gate artifacts: registry, card_router, v112e pipeline, v112n master dryrun.
- **Input Data**: partial — Both fixture data and local enrichment / live source data found. Fixture: 1 files. Real/local: 6 files.
- **Card Generation**: passed — Card generation artifacts found. Family-specific: 0 files.
- **Preview**: fixture_only — Preview artifacts found (5 evidence files) but all use fixture data. No real/local data pipeline for preview.
- **Quality Gate**: not_found — No quality gate artifacts found.
- **Send Readiness**: not_started — No send readiness artifacts found.
- **Fixture E2E**: not_started — No fixture positive path verification artifacts found.
- **Real E2E**: not_started — No real E2E artifacts found. This card family has not reached real E2E stage.
- **TG Test Group**: not_allowed — No TG test group send evidence. TG send is not allowed without explicit send-readiness gate pass.
- **Production Send**: not_allowed — Production send is not allowed per safety boundary.
- **Blocked Reason**: Card family not yet advanced to real E2E stage.
- **Next Task**: Advance liquidation_pressure from fixture-only preview to local/real data feed (adapter pipeline).

### multi_asset_market_sync

- **Current Stage**: `local_preview_passed`
- **Name Source**: market_radar_card_type_registry_v112a
- **Router Test**: passed — Card type registered in v112a registry, validated in v112e unified pipeline, and samples exist in v112a fixture. Shared router/gate artifacts: registry, card_router, v112e pipeline, v112n master dryrun.
- **Input Data**: partial — Both fixture data and local enrichment / live source data found. Fixture: 1 files. Real/local: 5 files.
- **Card Generation**: not_found — No card generation artifacts found.
- **Preview**: passed — Preview cards generated via local feed/enrichment pipeline. 3 evidence files. Non-fallback preview with real/local data enrichment.
- **Quality Gate**: not_found — No quality gate artifacts found.
- **Send Readiness**: not_started — No send readiness artifacts found.
- **Fixture E2E**: not_started — No fixture positive path verification artifacts found.
- **Real E2E**: not_started — No real E2E artifacts found. This card family has not reached real E2E stage.
- **TG Test Group**: not_allowed — No TG test group send evidence. TG send is not allowed without explicit send-readiness gate pass.
- **Production Send**: not_allowed — Production send is not allowed per safety boundary.
- **Blocked Reason**: Card family not yet advanced to real E2E stage.
- **Next Task**: Add quality gate (dedupe/cooldown/debug leak/secret leak) for multi_asset_market_sync.

### news_event_market_impact

- **Current Stage**: `fixture_preview`
- **Name Source**: market_radar_card_type_registry_v112a
- **Router Test**: passed — Card type registered in v112a registry, validated in v112e unified pipeline, and samples exist in v112a fixture. Shared router/gate artifacts: registry, card_router, v112e pipeline, v112n master dryrun.
- **Input Data**: partial — Both fixture data and local enrichment / live source data found. Fixture: 1 files. Real/local: 9 files.
- **Card Generation**: not_found — No card generation artifacts found.
- **Preview**: fixture_only — Preview artifacts found (4 evidence files) but all use fixture data. No real/local data pipeline for preview.
- **Quality Gate**: not_found — No quality gate artifacts found.
- **Send Readiness**: not_started — No send readiness artifacts found.
- **Fixture E2E**: not_started — No fixture positive path verification artifacts found.
- **Real E2E**: not_started — No real E2E artifacts found. This card family has not reached real E2E stage.
- **TG Test Group**: not_allowed — No TG test group send evidence. TG send is not allowed without explicit send-readiness gate pass.
- **Production Send**: not_allowed — Production send is not allowed per safety boundary.
- **Blocked Reason**: Card family not yet advanced to real E2E stage.
- **Next Task**: Advance news_event_market_impact from fixture-only preview to local/real data feed (adapter pipeline).

## Whale Position Alert — Special Note

- **whale_position_alert current stage**: `fixture_e2e_passed_real_blocked`
- **Fixture E2E passed**: `True`
- **Real E2E passed**: `False`
- **Blocked reason**: Real operator workbook has empty fields for all 4 addresses. Requires real operator evidence collection (v115O preflight) before gate rerun.

> **Key finding**: whale_position_alert is the ONLY card family with a completed fixture E2E gate replay (v115Q: 4/4 fixture rows pass intake→scoring→adjudication→workflow). However, real E2E remains BLOCKED because the real operator workbook (v115F) has empty fields for all 4 addresses. The fixture replay PROVES the gate logic works; it does NOT prove real address verification has been performed.

## TG / Production Send Status

| Send Type | Status | Evidence |
|-----------|--------|----------|
| TG test group | **not_allowed** | No card family has passed all prior gates required for TG test send. |
| Production send | **not_allowed** | Production send is blocked per safety boundary. No production send evidence exists. |

> ⚠ **Safety**: TG test group send and production send are NOT allowed 
> until real E2E is passed for the target card family AND all prior gates 
> (intake, scoring, adjudication, workflow upgrade, send-readiness) are green.

## Safety Constraints (All Verified)

| Constraint | Status |
|------------|--------|
| real_send_candidate_generated | false |
| tg_sent | false |
| prod_state_write | false |
| external_api_called | false |
| credentials_read | false |
| ai_model_called | false |
| files_deleted | false |
| historical_artifacts_modified | false |
