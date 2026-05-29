import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh docs/PROJECT_STATE.md from latest local outputs.")
    parser.add_argument("--output", default=str(ROOT / "docs" / "PROJECT_STATE.md"))
    return parser.parse_args()


def read_count(path: Path) -> int | str:
    if not path.exists():
        return "missing"
    try:
        return len(pd.read_csv(path, dtype=str))
    except Exception:
        return "unreadable"


def first_row(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        return df.iloc[0].to_dict() if len(df) else {}
    except Exception:
        return {}


def metric_value(path: Path, metric: str, default: str = "missing") -> str:
    if not path.exists():
        return default
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        if {"metric", "value"}.issubset(df.columns):
            match = df[df["metric"] == metric]
            if len(match):
                return str(match.iloc[0]["value"])
    except Exception:
        return default
    return default


def group_counts(path: Path, column: str) -> dict:
    if not path.exists():
        return {}
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        if column not in df.columns:
            return {}
        return df[column].value_counts().to_dict()
    except Exception:
        return {}


def sum_column_where(path: Path, where_column: str, where_value: str, sum_column: str) -> str:
    if not path.exists():
        return "missing"
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        if where_column not in df.columns or sum_column not in df.columns:
            return "missing"
        match = df[df[where_column].astype(str) == where_value]
        if not len(match):
            return "0"
        return str(int(pd.to_numeric(match[sum_column], errors="coerce").fillna(0).sum()))
    except Exception:
        return "unreadable"


def manual_review_required_count(path: Path) -> int | str:
    if not path.exists():
        return "missing"
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        if "manual_review_required" not in df.columns:
            return 0
        return int(df["manual_review_required"].astype(str).str.lower().eq("true").sum())
    except Exception:
        return "unreadable"


def fmt_counts(counts: dict) -> str:
    if not counts:
        return "- none"
    return "\n".join([f"- {key or '(blank)'}: {value}" for key, value in counts.items()])


def build_state() -> str:
    candidates = ROOT / "data" / "event_candidates_real_500_older_review.csv"
    auto50 = ROOT / "data" / "event_candidates_real_500_older_mature_review_auto50.csv"
    backfill = ROOT / "results" / "v043_older_mature50_event_price_backfill.csv"
    quality = ROOT / "results" / "v043_older_mature50_event_quality_report.csv"
    label_sheet = ROOT / "data" / "v06_manual_label_sheet.csv"
    claude_index = ROOT / "results" / "claude_response_index.csv"
    claude_decision_queue = ROOT / "data" / "claude_decision_review_queue.csv"
    time_summary = first_row(ROOT / "results" / "v043_time_provenance_summary.csv")
    label_summary = first_row(ROOT / "results" / "v06_manual_label_eval_summary.csv")
    auto_label_summary = first_row(ROOT / "results" / "v06_auto_label_summary.csv")
    auto_verify_summary = first_row(ROOT / "results" / "v06_auto_verify_summary.csv")
    auto_close_summary = first_row(ROOT / "results" / "v06_auto_close_summary.csv")
    auto_fill_summary = first_row(ROOT / "results" / "v06_auto_fill_unlabeled_summary.csv")
    manual_review_summary = first_row(ROOT / "results" / "v06_manual_review_required_summary.csv")
    secret_summary = first_row(ROOT / "results" / "secret_leak_summary.csv")
    project_os_validation = first_row(ROOT / "results" / "project_os_validation_summary.csv")
    command_registry = first_row(ROOT / "results" / "command_registry_summary.csv")
    review_actions = first_row(ROOT / "results" / "project_review_action_summary.csv")
    environment_summary = first_row(ROOT / "results" / "local_environment_summary.csv")
    artifact_manifest = first_row(ROOT / "results" / "artifact_manifest_summary.csv")
    v07_watchlist_validation = first_row(ROOT / "results" / "v07_watchlist_validation_summary.csv")
    v07_watcher_run = first_row(ROOT / "results" / "v07_first_hand_watcher_run_summary.csv")
    v07_watcher_normalization = first_row(ROOT / "results" / "v07_watcher_normalization_summary.csv")
    v07_tg_validation = first_row(ROOT / "results" / "tg_drafts_v07_watcher_validation_summary.csv")
    v08_long_short = first_row(ROOT / "results" / "v08_binance_long_short_summary.csv")
    v08_morning_digest = first_row(ROOT / "results" / "v08_tg_morning_digest_summary.csv")
    v08_noon_digest = first_row(ROOT / "results" / "v08_tg_noon_digest_summary.csv")
    v08_evening_digest = first_row(ROOT / "results" / "v08_tg_evening_digest_summary.csv")
    v08_rate_limit = first_row(ROOT / "results" / "v08_tg_rate_limit_summary.csv")
    v08_followup = first_row(ROOT / "results" / "v08_tg_alert_followup_summary.csv")
    v08_source_usefulness = first_row(ROOT / "results" / "v08_tg_source_usefulness_summary.csv")
    v08_quality_loop = first_row(ROOT / "results" / "v08_tg_quality_loop_summary.csv")
    v14_webhook_split = first_row(ROOT / "results" / "v14_webhook_split_summary.csv")
    v14_taxonomy = first_row(ROOT / "results" / "v14_needs_taxonomy_review_summary.csv")
    v14_etf = first_row(ROOT / "results" / "v14_etf_fund_flow_filter_summary.csv")
    v14_flow_split = first_row(ROOT / "results" / "v14_flow_event_subtypes_summary.csv")
    v14_exploit = first_row(ROOT / "results" / "v14_active_exploit_amount_verification_summary.csv")
    v14_short_price_in = first_row(ROOT / "results" / "v14_short_price_in_summary.csv")
    v14_upgrade = first_row(ROOT / "results" / "v14_upgrade_events_summary.csv")
    v14_criteria = first_row(ROOT / "results" / "v14_publishable_criteria_summary.csv")
    v14_security_ingest = first_row(ROOT / "results" / "v14_security_alert_ingest_summary.csv")
    v14_etf_daily = first_row(ROOT / "results" / "v14_etf_daily_digest_summary.csv")
    v14_first_hand = first_row(ROOT / "results" / "v14_first_hand_publish_candidates_summary.csv")
    v14_criteria_validation = first_row(ROOT / "results" / "v14_publishable_criteria_validation_summary.csv")
    v14_e2e_preview = first_row(ROOT / "results" / "v14_e2e_publish_preview_summary.csv")
    v14_hyperliquid_snapshot = first_row(ROOT / "results" / "v14_hyperliquid_snapshot_summary.csv")
    v14_market_state = first_row(ROOT / "results" / "v14_market_state_snapshot_summary.csv")
    v14_focus_assets = first_row(ROOT / "results" / "v14_focus_assets_summary.csv")
    v14_first_screen = first_row(ROOT / "results" / "v14_market_state_first_screen_summary.csv")
    v14_deriv_rows = read_count(ROOT / "results" / "v14_derivatives_history_percentiles_summary.csv")
    v14_prefilter = first_row(ROOT / "results" / "v14_prefilter_summary.csv")
    v14_composer = first_row(ROOT / "results" / "v14_composer_scores_summary.csv")
    v14_policy = first_row(ROOT / "results" / "v14_publish_policy_summary.csv")
    v14_digest = first_row(ROOT / "results" / "v14_digest_preview_summary.csv")
    v08_replay_broad_summary = ROOT / "results" / "v08_historical_replay_broad_200_sample_summary.csv"
    v08_replay_conservative_summary = ROOT / "results" / "v08_historical_replay_conservative_120_sample_summary.csv"
    v08_replay_non_btc_summary = ROOT / "results" / "v08_historical_replay_non_btc_single_asset_200_sample_summary.csv"
    selection_v06_summary = first_row(ROOT / "results" / "v043_selection_vs_v06_relevance_summary.csv")
    v06_filtered_preview = first_row(ROOT / "results" / "v06_filtered_mature_sample_preview_summary.csv")
    v06_asset_audit = first_row(ROOT / "results" / "v06_filtered_preview_asset_attribution_summary.csv")
    v06_clean_preview = first_row(ROOT / "results" / "v06_clean_low_risk_preview_summary.csv")
    v06_low_risk_backfill = ROOT / "results" / "v06_clean_low_risk_preview_event_price_backfill.csv"
    v06_low_risk_quality = ROOT / "results" / "v06_clean_low_risk_preview_event_quality_report.csv"
    fix_plan_summary = first_row(ROOT / "results" / "v06_asset_attribution_fix_plan_summary.csv")
    entity_packet_summary = first_row(ROOT / "results" / "v06_entity_rule_review_packet_summary.csv")
    backtest_readiness = first_row(ROOT / "results" / "backtest_readiness_summary.csv")
    tg_gate_rows = pd.DataFrame()
    tg_gate_path = ROOT / "results" / "v06_tg_pilot_gate_report.csv"
    if tg_gate_path.exists():
        try:
            tg_gate_rows = pd.read_csv(tg_gate_path, dtype=str).fillna("")
        except Exception:
            tg_gate_rows = pd.DataFrame()
    if tg_gate_rows.empty:
        tg_gate_status = "missing"
    else:
        tg_gate_status = "pass" if tg_gate_rows["status"].eq("pass").all() else "fail"

    return f"""# Project State

Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}

## Current Version

Current active layer: v0.8 Telegram live intelligence pilot plus v0.6/v0.7 data-quality foundations.

The project has working local pipelines for:

- Raw news normalization.
- Event candidate import.
- Symbol/entity/taxonomy enrichment.
- Candidate relevance scoring.
- Mature candidate filtering.
- Stratified auto-review sampling.
- Binance price backfill.
- BTC/ETH abnormal return calculation.
- Backfill quality validation.
- Price source validation.
- Time provenance auditing.
- Claude consultation prompt generation.
- Manual label evaluation.
- First-hand watcher alerts for curated Ethereum addresses and stablecoin mint/burn.
- Watcher alert normalization into the existing event/backtest and TG draft preview schemas.
- Telegram live monitor with quality gates, rate limits, and China-time send windows.
- Scheduled China-time morning/noon/evening digests.
- CEX netflow rolling baseline context.
- Hyperliquid large-position state-change tracking.
- Binance USD-M long/short ratio snapshots for digest context.
- Binance USD-M market-state snapshots for price, volume, open-interest, funding, and crowding context.

## v0.8 Telegram Intelligence Pilot

```text
live_monitor: deployed on server systemd service
time_policy_file: config/tg_send_time_policy.csv
latest_time_window: {v08_rate_limit.get('time_window', 'missing')}
time_policy_enabled: {v08_rate_limit.get('time_policy_enabled', 'missing')}
morning_digest_status: {v08_morning_digest.get('status', 'missing')}
noon_digest_status: {v08_noon_digest.get('status', 'missing')}
evening_digest_status: {v08_evening_digest.get('status', 'missing')}
long_short_status: {v08_long_short.get('status', 'missing')}
long_short_top_crowded_asset: {v08_long_short.get('top_crowded_asset', 'missing')}
long_short_top_crowded_bias: {v08_long_short.get('top_crowded_bias', 'missing')}
market_state_status: {v14_market_state.get('status', 'missing')}
market_state_coverage: {v14_market_state.get('ok_rows', 'missing')}/{v14_market_state.get('watchlist_rows', 'missing')}
market_state_btc_24h: {v14_market_state.get('btc_price_change_pct_24h', 'missing')}%
market_state_eth_24h: {v14_market_state.get('eth_price_change_pct_24h', 'missing')}%
market_state_top_price_move: {v14_market_state.get('top_price_move_asset', 'missing')} {v14_market_state.get('top_price_move_pct_24h', 'missing')}%
market_state_top_oi_change: {v14_market_state.get('top_oi_change_asset', 'missing')} {v14_market_state.get('top_oi_change_pct_24h', 'missing')}%
market_state_focus_assets: {v14_focus_assets.get('selected_assets', 'missing')}
market_state_first_screen_status: {v14_first_screen.get('status', 'missing')}
market_state_first_screen_lines: {v14_first_screen.get('line_count', 'missing')}
derivatives_history_percentile_rows: {v14_deriv_rows}
quality_loop_first_step_status: {v08_quality_loop.get('status', 'missing')}
followup_4h_rows: {v08_followup.get('computable_4h_rows', 'missing')}
followup_24h_rows: {v08_followup.get('computable_24h_rows', 'missing')}
source_usefulness_sent_count: {v08_source_usefulness.get('sent_count', 'missing')}
source_usefulness_source_count: {v08_source_usefulness.get('source_count', 'missing')}
source_usefulness_basis: sent alerts plus 4h/24h follow-up only
historical_replay_broad_selected_rows: {metric_value(v08_replay_broad_summary, 'selected_rows')}
historical_replay_conservative_selected_rows: {metric_value(v08_replay_conservative_summary, 'selected_rows')}
historical_replay_non_btc_single_asset_selected_rows: {metric_value(v08_replay_non_btc_summary, 'selected_rows')}
historical_replay_broad_summary: results/v08_historical_replay_broad_200_findings.md
historical_replay_conservative_summary: results/v08_historical_replay_conservative_120_findings.md
historical_replay_non_btc_single_asset_summary: results/v08_historical_replay_non_btc_single_asset_200_findings.md
server_schedule: morning around 08:30, noon around 12:30, evening around 20:30 China time
interpretation: the live TG surface is running; next work is proving signal usefulness, separating BTC/macro pollution, and reducing noisy sources, not expanding every possible feed.
```

## v14 Claude-Directed Quality Fixes

```text
status: intraday radar remains paused until data-quality gates pass
time_field_diagnosis: results/v14_time_field_diagnosis.md
webhook_subsource_count: {v14_webhook_split.get('subsource_count', 'missing')}
webhook_source_score_gt_50_count: {v14_webhook_split.get('score_gt_50_count', 'missing')}
needs_taxonomy_review_remaining: {sum_column_where(ROOT / 'results' / 'v14_needs_taxonomy_review_summary.csv', 'v14_taxonomy_event_subtype', 'needs_taxonomy_review', 'sample_count')}
etf_fund_flow_kept_rows: {v14_etf.get('kept_rows', 'missing')}
etf_fund_flow_archived_rows: {v14_etf.get('archived_rows', 'missing')}
flow_split_etf_specific_rows: {v14_flow_split.get('etf_specific_rows', 'missing')}
flow_split_etf_creation_redemption_rows: {v14_flow_split.get('etf_creation_redemption_rows', 'missing')}
flow_split_etf_macro_news_rows: {v14_flow_split.get('etf_macro_news_rows', 'missing')}
flow_split_institutional_disclosure_rows: {v14_flow_split.get('institutional_disclosure_rows', 'missing')}
flow_split_cex_netflow_rows: {v14_flow_split.get('cex_netflow_rows', 'missing')}
flow_split_unclear_rows: {v14_flow_split.get('unclear_rows', 'missing')}
active_exploit_rows: {v14_exploit.get('active_exploit_rows', 'missing')}
active_exploit_urgent_eligible_count: {v14_exploit.get('urgent_eligible_count', 'missing')}
short_price_in_pass_rows: {v14_short_price_in.get('pass_rows', 'missing')}
short_price_in_block_rows: {v14_short_price_in.get('price_in_block_rows', 'missing')}
upgrade_digest_rows: {v14_upgrade.get('digest_rows', 'missing')}
upgrade_background_rows: {v14_upgrade.get('background_rows', 'missing')}
upgrade_block_rows: {v14_upgrade.get('block_rows', 'missing')}
publishable_criteria_passed_rows: {v14_criteria.get('criteria_passed_rows', 'missing')}
publishable_criteria_blocked_rows: {v14_criteria.get('criteria_blocked_rows', 'missing')}
security_alert_ingest_status: {v14_security_ingest.get('status', 'missing')}
security_alert_normalized_rows: {v14_security_ingest.get('normalized_rows', 'missing')}
etf_daily_rows: {v14_etf_daily.get('rows', 'missing')}
etf_daily_latest_date: {v14_etf_daily.get('latest_date', 'missing')}
etf_daily_latest_total_net_flow_usd: {v14_etf_daily.get('latest_total_net_flow_usd', 'missing')}
etf_daily_publishable: {v14_etf_daily.get('publishable_daily_digest', 'missing')}
first_hand_input_rows: {v14_first_hand.get('input_rows', 'missing')}
first_hand_intraday_candidate_rows: {v14_first_hand.get('intraday_candidate_rows', 'missing')}
first_hand_digest_candidate_rows: {v14_first_hand.get('digest_candidate_rows', 'missing')}
first_hand_daily_digest_candidate_rows: {v14_first_hand.get('daily_digest_candidate_rows', 'missing')}
first_hand_archived_rows: {v14_first_hand.get('archived_rows', 'missing')}
publishable_criteria_golden_rows: {v14_criteria_validation.get('golden_rows', 'missing')}
publishable_criteria_validation_failed_rows: {v14_criteria_validation.get('failed_rows', 'missing')}
e2e_preview_etf_publishable: {v14_e2e_preview.get('etf_publishable', 'missing')}
e2e_preview_first_hand_publishable_rows: {v14_e2e_preview.get('first_hand_publishable_rows', 'missing')}
e2e_latency_sla_pass: {v14_e2e_preview.get('latency_sla_pass', 'missing')}
hyperliquid_snapshot_position_count: {v14_hyperliquid_snapshot.get('position_count', 'missing')}
hyperliquid_snapshot_total_position_value_usd: {v14_hyperliquid_snapshot.get('total_position_value_usd', 'missing')}
hyperliquid_snapshot_near_liquidation_value_usd: {v14_hyperliquid_snapshot.get('near_liquidation_value_usd', 'missing')}
prefilter_passed_rows: {v14_prefilter.get('passed_rows', 'missing')}
prefilter_blocked_rows: {v14_prefilter.get('blocked_rows', 'missing')}
composer_gate_passed_count: {v14_composer.get('gate_passed_count', 'missing')}
composer_digest_candidate_count: {v14_composer.get('pass_digest_count', 'missing')}
composer_interrupt_candidate_count: {v14_composer.get('interrupt_candidate_count', 'missing')}
composer_review_count: {v14_composer.get('review_count', 'missing')}
composer_block_count: {v14_composer.get('block_count', 'missing')}
publish_policy_digest_rows: {v14_policy.get('digest_rows', 'missing')}
publish_policy_interrupt_rows: {v14_policy.get('interrupt_rows', 'missing')}
publish_policy_block_rows: {v14_policy.get('block_rows', 'missing')}
strict_digest_security_rows: {v14_digest.get('security_rows', 'missing')}
strict_digest_fund_flow_rows: {v14_digest.get('fund_flow_rows', 'missing')}
strict_digest_upgrade_rows: {v14_digest.get('upgrade_rows', 'missing')}
publish_policy_report: results/v14_publish_policy_report.md
composer_report: results/v14_composer_scores_report.md
digest_preview: results/v14_digest_preview.md
interpretation: only morning/evening digest-style output is allowed from this branch; rows failing source score, amount context, taxonomy, or asset-consistency checks stay out of Telegram.
```

## v0.7 First-Hand Watcher MVP

```text
plan: docs/V07_FIRST_HAND_INTEL_PLAN.md
watchlist_validation_status: {v07_watchlist_validation.get('status', 'missing')}
watchlist_fail_count: {v07_watchlist_validation.get('fail_count', 'missing')}
address_alert_rows: {v07_watcher_run.get('address_alert_rows', 'missing')}
stablecoin_alert_rows: {v07_watcher_run.get('stablecoin_alert_rows', 'missing')}
deduped_alert_rows: {v07_watcher_run.get('deduped_alert_rows', 'missing')}
event_rows: {v07_watcher_run.get('event_rows', 'missing')}
tg_draft_rows: {v07_watcher_run.get('tg_draft_rows', 'missing')}
tg_draft_validation_status: {v07_tg_validation.get('status', 'missing')}
tg_draft_validation_fail_count: {v07_tg_validation.get('fail_count', 'missing')}
normalization_status: {v07_watcher_normalization.get('status', 'missing')}
report: results/v07_watcher_daily_report.md
interpretation: local first-hand watcher MVP is dry-run/live-ready; it does not call Telegram unless the explicit TG test sender is run with --send.
```

## Latest Stable Real Run

Dataset:

```text
data/raw_news_real_500_older.csv
```

Latest v043 result:

```text
candidates: {read_count(candidates)}
stratified selected: {read_count(auto50)}
backfill rows: {read_count(backfill)}
quality rows: {read_count(quality)}
```

Stratified selection diagnostics:

```text
diagnostic_report: results/v043_stratified_selection_diagnostics.md
selected_rows: {read_count(auto50)}
underfill_reason: capped macro/other/hack_security plus scarce eligible non-macro event types
policy_note: do not relax event_type caps without Claude/product approval
```

v043 selection vs v0.6 relevance audit:

```text
audit_report: results/v043_selection_vs_v06_relevance_audit.md
v06_human_review_rows: {selection_v06_summary.get('v06_human_review_rows', 'missing')}
v06_discard_rows: {selection_v06_summary.get('v06_discard_rows', 'missing')}
v06_discard_rate: {selection_v06_summary.get('v06_discard_rate', 'missing')}
safe_to_use_as_current_evidence: {selection_v06_summary.get('safe_to_use_as_current_evidence', 'missing')}
recommended_use: {selection_v06_summary.get('recommended_use', 'missing')}
clean_sample_next_step: {selection_v06_summary.get('clean_sample_next_step', 'missing')}
interpretation: existing v043 backtest is a historical baseline, not the cleanest current sample
```

v0.6-filtered mature sample preview:

```text
preview_report: results/v06_filtered_mature_sample_preview.md
preview_file: data/event_candidates_v06_filtered_mature_review_auto50_preview.csv
eligible_count: {v06_filtered_preview.get('eligible_count', 'missing')}
selected_count: {v06_filtered_preview.get('selected_count', 'missing')}
status: preview only; does not overwrite v043 outputs and does not run backtest
```

v0.6 preview asset attribution audit:

```text
audit_report: results/v06_filtered_preview_asset_attribution_audit.md
high_risk_rows: {v06_asset_audit.get('high_risk_rows', 'missing')}
medium_risk_rows: {v06_asset_audit.get('medium_risk_rows', 'missing')}
low_risk_rows: {v06_asset_audit.get('low_risk_rows', 'missing')}
interpretation: preview still needs asset attribution cleanup before a clean backtest branch
```

v0.6 clean low-risk preview:

```text
preview_report: results/v06_clean_low_risk_preview.md
preview_file: data/event_candidates_v06_clean_low_risk_preview.csv
selected_low_risk_rows: {v06_clean_preview.get('selected_low_risk_rows', 'missing')}
excluded_medium_risk_rows: {v06_clean_preview.get('excluded_medium_risk_rows', 'missing')}
excluded_high_risk_rows: {v06_clean_preview.get('excluded_high_risk_rows', 'missing')}
interpretation: safe sanity-check subset only; too small for statistical conclusions
```

v0.6 clean low-risk preview backtest:

```text
runner: scripts/run_v06_clean_low_risk_preview_backtest.py
events_file: data/events_v06_clean_low_risk_preview.csv
backfill_rows: {read_count(v06_low_risk_backfill)}
quality_rows: {read_count(v06_low_risk_quality)}
findings: results/v06_clean_low_risk_preview_backtest_findings.md
interpretation: sanity-check only; does not replace v043 historical outputs
```

Backtest readiness:

```text
report: results/backtest_readiness_report.md
overall_conclusion_status: {backtest_readiness.get('overall_conclusion_status', 'missing')}
ready_for_statistical_conclusions: {backtest_readiness.get('ready_for_statistical_conclusions', 'missing')}
review_count: {backtest_readiness.get('review_count', 'missing')}
local_review_count: {backtest_readiness.get('local_review_count', 'missing')}
claude_review_count: {backtest_readiness.get('claude_review_count', 'missing')}
mixed_local_claude_review_count: {backtest_readiness.get('mixed_local_claude_review_count', 'missing')}
interpretation: if not ready, do not cite event-type performance as a product conclusion
```

v0.6 asset attribution fix plan:

```text
fix_plan_report: results/v06_asset_attribution_fix_plan.md
top_action: {fix_plan_summary.get('recommended_action', 'missing')}
top_action_count: {fix_plan_summary.get('count', 'missing')}
interpretation: non-destructive plan for fixing or excluding high/medium attribution-risk rows
```

v0.6 entity rule review packet:

```text
entity_review_report: results/v06_entity_rule_review_packet.md
top_review_type: {entity_packet_summary.get('entity_review_type', 'missing')}
top_review_count: {entity_packet_summary.get('count', 'missing')}
interpretation: protocol exploit primary-asset policy needs direction before automatic fixes
```

Backfill status:

```text
{fmt_counts(group_counts(backfill, 'status'))}
```

Quality status:

```text
{fmt_counts(group_counts(quality, 'quality_status'))}
```

Latest time audit:

```text
total_rows: {time_summary.get('total_rows', 'missing')}
pass: {time_summary.get('pass_count', 'missing')}
warning: {time_summary.get('warning_count', 'missing')}
fail: {time_summary.get('fail_count', 'missing')}
price_kline_lag_out_of_range_count: {time_summary.get('price_kline_lag_out_of_range_count', 'missing')}
```

Manual label status:

```text
total_rows: {label_summary.get('total_rows', 'missing')}
labeled_rows: {label_summary.get('labeled_rows', 'missing')}
label_coverage_pct: {label_summary.get('label_coverage_pct', 'missing')}
auto_prefilled_rows: {label_summary.get('auto_prefilled_rows', 'missing')}
error_rows: {label_summary.get('error_rows', 'missing')}
```

Auto-label assist status:

```text
suggest_ready_rows: {auto_label_summary.get('suggest_ready_rows', 'missing')}
avg_auto_label_confidence: {auto_label_summary.get('avg_auto_label_confidence', 'missing')}
auto_prefilled_rows_in_run: {auto_label_summary.get('auto_prefilled_rows_in_run', 'missing')}
auto_provisional_rows_in_run: {auto_label_summary.get('auto_provisional_rows_in_run', 'missing')}
manual_review_required_rows_after_run: {auto_label_summary.get('manual_review_required_rows_after_run', 'missing')}
manual_unlabeled_rows_after_run: {auto_label_summary.get('manual_unlabeled_rows_after_run', 'missing')}
```

Auto-verify status:

```text
auto_verified_rows_in_run: {auto_verify_summary.get('auto_verified_rows_in_run', 'missing')}
provisional_remaining_after_run: {auto_verify_summary.get('provisional_remaining_after_run', 'missing')}
audit_sample_rows: {auto_verify_summary.get('audit_sample_rows', 'missing')}
```

Auto-close status:

```text
auto_closed_rows_in_run: {auto_close_summary.get('auto_closed_rows_in_run', 'missing')}
selected_low_risk_rows: {auto_close_summary.get('selected_low_risk_rows', 'missing')}
audit_sample_rows: {auto_close_summary.get('audit_sample_rows', 'missing')}
```

Auto-fill unlabeled status:

```text
auto_filled_rows_in_run: {auto_fill_summary.get('auto_filled_rows_in_run', 'missing')}
unlabeled_rows_after_run: {auto_fill_summary.get('unlabeled_rows_after_run', 'missing')}
audit_sample_rows: {auto_fill_summary.get('audit_sample_rows', 'missing')}
manual_review_required_rows_current: {manual_review_required_count(label_sheet)}
```

Manual review audit:

```text
manual_review_required_rows: {manual_review_summary.get('manual_review_required_rows', 'missing')}
manual_review_required_rate: {manual_review_summary.get('manual_review_required_rate', 'missing')}
status: {manual_review_summary.get('status', 'missing')}
```

TG pilot gate:

```text
gate_report: results/v06_tg_pilot_gate_report.md
current_status: {tg_gate_status}
```

Secret leak scan:

```text
secret_leak_count: {secret_summary.get('leak_count', 'missing')}
status: {secret_summary.get('status', 'missing')}
report: results/secret_leak_report.md
```

Project OS validation:

```text
overall_status: {project_os_validation.get('overall_status', 'missing')}
blocking_or_fail_count: {project_os_validation.get('blocking_or_fail_count', 'missing')}
review_count: {project_os_validation.get('review_count', 'missing')}
report: results/project_os_validation_report.md
```

Local environment:

```text
overall_status: {environment_summary.get('overall_status', 'missing')}
fail_count: {environment_summary.get('fail_count', 'missing')}
python_version: {environment_summary.get('python_version', 'missing')}
report: results/local_environment_report.md
```

Command registry:

```text
command_count: {command_registry.get('command_count', 'missing')}
missing_script_count: {command_registry.get('missing_script_count', 'missing')}
status: {command_registry.get('status', 'missing')}
doc: docs/COMMAND_REGISTRY.md
```

Review action queue:

```text
open_action_count: {review_actions.get('open_action_count', 'missing')}
requires_claude_yes_count: {review_actions.get('requires_claude_yes_count', 'missing')}
can_do_locally_yes_count: {review_actions.get('can_do_locally_yes_count', 'missing')}
unknown_rule_count: {review_actions.get('unknown_rule_count', 'missing')}
doc: docs/PROJECT_REVIEW_ACTIONS.md
```

Artifact manifest:

```text
artifact_count: {artifact_manifest.get('artifact_count', 'missing')}
required_artifact_count: {artifact_manifest.get('required_artifact_count', 'missing')}
missing_required_count: {artifact_manifest.get('missing_required_count', 'missing')}
stale_required_count: {artifact_manifest.get('stale_required_count', 'missing')}
status: {artifact_manifest.get('status', 'missing')}
doc: docs/ARTIFACT_MANIFEST.md
```

Claude consultation archive:

```text
indexed_response_files: {read_count(claude_index)}
index_doc: docs/CLAUDE_RESPONSE_INDEX.md
decision_review_items: {read_count(claude_decision_queue)}
decision_review_doc: docs/CLAUDE_DECISION_REVIEW.md
rule: accepted direction changes must be copied into docs/DECISIONS.md before implementation
```

## Key Output Files

```text
data/event_candidates_real_500_older_review.csv
data/event_candidates_real_500_older_review_suggested.csv
data/event_candidates_real_500_older_mature_review_auto50.csv
data/events_real_500_older_mature_50.csv
data/v06_manual_label_sheet.csv
results/v043_older_mature50_event_price_backfill.csv
results/v043_older_mature50_event_quality_report.csv
results/v043_time_provenance_report.csv
results/v043_time_provenance_summary.csv
results/v06_auto_label_summary.csv
results/v06_auto_verify_summary.csv
results/v06_auto_close_summary.csv
results/v06_auto_fill_unlabeled_summary.csv
results/v06_manual_review_required_summary.csv
results/v06_tg_pilot_gate_report.md
results/v06_manual_label_eval_summary.csv
results/v06_manual_label_eval_errors.csv
results/claude_response_index.csv
results/secret_leak_report.md
results/project_os_validation_report.md
results/project_os_validation_summary.csv
results/local_environment_report.md
results/command_registry.csv
docs/COMMAND_REGISTRY.md
docs/ARTIFACT_MANIFEST.md
data/events_v06_clean_low_risk_preview.csv
results/v06_clean_low_risk_preview_event_price_backfill.csv
results/v06_clean_low_risk_preview_event_quality_report.csv
results/v06_clean_low_risk_preview_backtest_findings.md
results/backtest_readiness_report.md
data/project_review_action_queue.csv
docs/PROJECT_REVIEW_ACTIONS.md
data/claude_decision_review_queue.csv
```

## Current Bottleneck

The system can process historical news, generate first-hand alerts, send Telegram messages, and produce scheduled digests. The current bottleneck is no longer infrastructure. The bottleneck is data quality: source trust, taxonomy clarity, amount/context verification, asset attribution, and enough historical coverage across regimes.

Before scaling alert volume:

- Keep `secret_leak_count = 0`.
- Keep intraday radar paused until Claude-defined quality gates pass.
- Keep live alerts focused on rare, quality-gated first-hand events, not dense observation boards.
- Keep stablecoin, ETF/fund flow, long/short, and security items primarily as digest/context signals unless they pass explicit amount, source, and context gates.
- Measure post-alert follow-up movement and historical replay behavior before adding more sources.
- Avoid turning broad market/news items into high-frequency real-time noise.
- Keep all wording as intelligence/research context, not trading advice.

## Current Engineering Focus

1. Keep applying Claude v14 quality fixes one by one: source split, taxonomy cleanup, ETF/fund-flow context, exploit amount verification, and digest-only routing.
2. Build a cleaner morning/evening digest from strict quality-gated rows before restarting any intraday board.
3. Solve historical coverage/regime limits by finding a better older event source or proving the current database is too sparse.
4. Keep historical backtest/data-quality tools available, but do not treat small-sample event_type performance as a product conclusion.
5. Consult Claude before direction-level changes such as new source tiers, publishing policy, source expansion, or taxonomy changes.
"""


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_state(), encoding="utf-8")
    print(f"wrote project state to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
